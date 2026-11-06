"""Read-only DB-API bridge for actual tools, with no application credentials.

Only the transport is replaced: SQL from the real repositories executes against
the funding database through a local psql client. This is not a simulated tool
response. Source-oracle SQL is separate from the tool's SQL.
"""

import re
from collections import namedtuple
from contextlib import ExitStack, contextmanager
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from .oracles import OraclePrerequisiteError

Column = namedtuple("Column", "name type_code display_size internal_size precision scale null_ok")


def bind_query(query, parameters):
    from psycopg2.extensions import adapt

    if not isinstance(query, str):
        raise ValueError("Scenario transport accepts SQL strings only")
    values = iter(parameters or [])

    def substitute(match):
        if match.group() == "%%":
            return "%"
        try:
            value = next(values)
        except StopIteration:
            raise ValueError("Missing SQL parameter") from None
        return adapt(value).getquoted().decode("utf-8")

    result = re.sub(r"%%|%s", substitute, query)
    if next(values, None) is not None:
        raise ValueError("Unused SQL parameters")
    return result


class ReadCursor:
    def __init__(self, reader, dictionary=False):
        self.reader = reader
        self.dictionary = dictionary
        self.rows = []
        self.position = 0
        self.description = None
        self.rowcount = -1

    def execute(self, query, parameters=None):
        records = self.reader(bind_query(query, parameters))
        # psql JSON represents dates as strings; restore native DB-API date values
        # so production isinstance(date) branches observe the same data types.
        for row in records:
            for key, value in row.items():
                if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    row[key] = date.fromisoformat(value)
                elif isinstance(value, str) and re.fullmatch(
                    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2}|Z)?", value
                ):
                    row[key] = datetime.fromisoformat(value)
        self.description = (
            [Column(key, None, None, None, None, None, None) for key in records[0]]
            if records
            else []
        )
        self.rows = records if self.dictionary else [tuple(row.values()) for row in records]
        self.position = 0
        self.rowcount = len(records)

    def fetchone(self):
        if self.position == len(self.rows):
            return None
        row = self.rows[self.position]
        self.position += 1
        return row

    def fetchall(self):
        rows = self.rows[self.position :]
        self.position = len(self.rows)
        return rows

    def fetchmany(self, size=1):
        rows = self.rows[self.position : self.position + size]
        self.position += len(rows)
        return rows

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ReadConnection:
    def __init__(self, reader):
        self.reader = reader
        self.closed = False

    def cursor(self, *args, cursor_factory=None, **kwargs):
        return ReadCursor(self.reader, dictionary=cursor_factory is not None)

    def commit(self):
        # Every SELECT has already completed in a rolled-back read-only transaction.
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True

    def set_session(self, *args, readonly=True, **kwargs):
        if not readonly:
            raise ValueError("Scenario connections are read-only")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ReadPool:
    def __init__(self, reader):
        self.reader = reader

    def getconn(self):
        return ReadConnection(self.reader)

    def putconn(self, connection):
        connection.close()

    def closeall(self):
        pass


class ReadSearchClient:
    """Execute only the application's three existing search RPCs, inside read-only SQL."""

    def __init__(self, reader):
        self.reader = reader

    def rpc(self, name, parameters):
        schemas = {
            "hybrid_search": {"query_embedding", "query_text", "match_count", "vector_weight"},
            "search_documents": {
                "query_embedding",
                "match_threshold",
                "match_count",
                "filter_document_type",
                "filter_year",
            },
            "keyword_search": {"query_text", "limit_count", "filter_document_type", "filter_year"},
        }
        if name not in schemas or set(parameters) - schemas[name]:
            raise OraclePrerequisiteError("Unsupported read-only search RPC or arguments")
        values = []
        arguments = []
        for key, value in parameters.items():
            if key == "query_embedding":
                import numpy as np

                vector = np.asarray(value, dtype=float)
                if vector.shape != (3072,) or not np.isfinite(vector).all() or not np.any(vector):
                    raise ValueError("Search requires a valid 3072-dimensional embedding")
                value = "[" + ",".join(str(number) for number in vector) + "]"
                arguments.append(f"{key} => %s::vector")
            else:
                arguments.append(f"{key} => %s")
            values.append(value)
        sql = bind_query(f"SELECT * FROM public.{name}({', '.join(arguments)})", values)
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=self.reader(sql)))


def unavailable(*args, **kwargs):
    raise OraclePrerequisiteError("This evaluation has no network/graph/embedding transport")


@contextmanager
def funding_transport(reader, embedding_allowance=None):
    """Keep tools on funding SELECTs and deny external HTTP/graph/embedding calls."""
    import google.generativeai as genai
    import psycopg2
    import psycopg2.pool

    original_embed_content = genai.embed_content

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(psycopg2, "connect", lambda *a, **k: ReadConnection(reader))
        )
        for name in ("ThreadedConnectionPool", "SimpleConnectionPool"):
            stack.enter_context(patch.object(psycopg2.pool, name, lambda *a, **k: ReadPool(reader)))
        for target in (
            "requests.sessions.Session.request",
            "httpx.Client.send",
            "httpx.AsyncClient.send",
            "httpx2.Client.send",
            "httpx2.AsyncClient.send",
            "google.generativeai.embed_content",
            "google.generativeai.embed_content_async",
            "google.generativeai.GenerativeModel.generate_content",
            "google.generativeai.GenerativeModel.generate_content_async",
        ):
            stack.enter_context(patch(target, side_effect=unavailable))
        if embedding_allowance is not None:
            from app.services.embedding_service import EmbeddingService

            # The pre-patch SDK function is captured separately below. The
            # actual embedder and vector service still execute application code.
            sdk_call = original_embed_content
            generate = EmbeddingService.generate_query_embedding
            stack.enter_context(
                patch.object(
                    EmbeddingService,
                    "generate_query_embedding",
                    lambda owner, text: embedding_allowance.query(owner, text, generate, sdk_call),
                )
            )
            stack.enter_context(
                patch(
                    "app.services.supabase_client.create_client",
                    lambda *a, **k: ReadSearchClient(reader),
                )
            )
        # Importing the graph implementation can load unrelated drivers; report
        # the missing capability rather than silently fabricate graph statistics.
        stack.enter_context(
            patch.dict(
                "sys.modules",
                {
                    "app.services.data_intelligence.graph_service": SimpleNamespace(
                        GraphSearchService=unavailable
                    ),
                    "app.core.neo4j_config": SimpleNamespace(Neo4jConnection=unavailable),
                },
            )
        )
        yield
