"""Read-only, public-source inventory for the authenticated data dashboard.

No document text, local file paths, credentials, users or conversation data is
returned. General and call-specific copies are joined only by an explicit parent
ID or matching file hash; the UI calls these records, not unique source PDFs.
"""

import asyncio
from contextlib import closing
from datetime import datetime, timezone
import re
from urllib.parse import urlsplit

import psycopg2

from app.services.document_trust import public_source_searchable
from psycopg2.extras import RealDictCursor

PROGRAMMES = {
    "horizon_europe": "Horizon Europe",
    "erasmus": "Erasmus+",
    "creative_europe": "Creative Europe",
    "eu4health": "EU4Health",
    "digital_europe": "Digital Europe",
    "life": "LIFE",
    "euratom": "Euratom",
    "shared": "EU-wide / shared",
    "unassigned": "Unassigned",
}


def public_url(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme == "https"
            and parsed.hostname
            and (parsed.hostname == "europa.eu" or parsed.hostname.endswith(".europa.eu"))
            and not parsed.username
            and not parsed.password
            and parsed.port in (None, 443)
        ):
            return value
    except ValueError:
        pass
    return None


def document_programme(row):
    metadata = row.get("metadata") or {}
    title = (row.get("title") or "").lower()
    url = (row.get("source_url") or "").lower()
    if "/common/" in url or re.search(
        r"\bgdpr\b|general data protection|artificial intelligence act|european health data space",
        title,
    ):
        return "shared"
    explicit = metadata.get("programme", "").lower().replace("-", "_")
    aliases = {
        "horizon": "horizon_europe",
        "erasmus+": "erasmus",
        "creative europe": "creative_europe",
        "digital europe": "digital_europe",
    }
    explicit = aliases.get(explicit, explicit)
    if explicit in PROGRAMMES:
        return explicit
    text = title + " " + url
    patterns = [
        ("erasmus", r"erasmus"),
        ("creative_europe", r"creative[ _-]europe|\bcrea\b"),
        ("eu4health", r"eu4health"),
        ("digital_europe", r"digital[ _-]europe"),
        ("life", r"\blife\b"),
        ("euratom", r"euratom"),
        ("horizon_europe", r"horizon|\beic\b|\berc\b|\bmsca\b|\bhe\b"),
    ]
    for programme, pattern in patterns:
        if re.search(pattern, text):
            return programme
    return "unassigned"


def document_inventory(general, shared):
    entries = []
    by_parent = {}
    by_hash = {}
    for store, rows in [("general", general), ("call_library", shared)]:
        for raw in rows:
            row = dict(raw)
            metadata = row.get("metadata") or {}
            status = row.get("status") or "active"
            if metadata.get("superseded_by") or metadata.get("retrieval_status") == "quarantined":
                status = "archived"
            elif metadata.get("review_state") == "pending" or (
                status == "active" and not public_source_searchable(metadata)
            ):
                status = "pending_review"
            parent = str(metadata.get("horizon_document_id") or "")
            existing = by_parent.get(parent) if store == "call_library" and parent else None
            source_hash = row.get("file_hash")
            # Do not join separate revisions/statuses based on titles alone.
            if existing is None and source_hash:
                existing = by_hash.get((source_hash, status))
            if existing is not None:
                existing["stores"].append(store)
                existing["chunks"] += int(row.get("chunks") or 0)
                continue
            provenance = metadata.get("provenance") or {}
            entry = {
                "id": str(row["id"]),
                "title": row.get("title") or "Untitled document",
                "programme": document_programme(row),
                "type": row.get("document_type") or "document",
                "year": row.get("programme_year"),
                "version": row.get("version"),
                "status": status,
                "chunks": int(row.get("chunks") or 0),
                "source_url": public_url(row.get("source_url")),
                "source_status": provenance.get("status") or "source_not_verified",
                "source_warning": provenance.get("warning") or (
                    (metadata.get("origin_quarantine") or {}).get("reason")
                    if metadata.get("retrieval_status") == "quarantined" else None
                ),
                "updated_at": row.get("last_updated"),
                "stores": [store],
            }
            entries.append(entry)
            if store == "general":
                by_parent[str(row["id"])] = entry
            if source_hash:
                by_hash[(source_hash, status)] = entry
    entries.sort(key=lambda x: (x["programme"], x["title"].casefold(), str(x["year"] or "")))
    summary = []
    for key, label in PROGRAMMES.items():
        documents = [d for d in entries if d["programme"] == key]
        summary.append(
            {
                "id": key,
                "name": label,
                "records": len(documents),
                "searchable": sum(d["status"] == "active" and d["chunks"] > 0 for d in documents),
                "pending": sum(d["status"] == "pending_review" for d in documents),
                "archived": sum(d["status"] == "archived" for d in documents),
            }
        )
    return {
        "status": "available",
        "records": len(entries),
        "searchable": sum(d["status"] == "active" and d["chunks"] > 0 for d in entries),
        "pending": sum(d["status"] == "pending_review" for d in entries),
        "archived": sum(d["status"] == "archived" for d in entries),
        "programmes": summary,
        "documents": entries,
        "note": "Stored document records and editions, not a count of unique PDFs. Explicitly linked copies in the two search libraries are combined. Unassigned legacy records remain visible.",
    }


def postgres_overview():
    from app.core.config import settings
    from app.services.project_coverage import (
        describe_coverage,
        apply_snapshot_provenance,
        SNAPSHOT_PATH,
    )
    from app.services.call_catalog import CallCatalog
    import json

    with closing(psycopg2.connect(settings.database_url, connect_timeout=5)) as conn:
        conn.set_session(readonly=True, isolation_level="REPEATABLE READ")
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SET LOCAL statement_timeout='8000ms'")
            cursor.execute(
                'SELECT count(*) AS count,max("contentUpdateDate") AS latest,array_agg(DISTINCT "frameworkProgramme") AS programmes FROM projects'
            )
            projects = dict(cursor.fetchone())
            cursor.execute(
                'SELECT count(*) AS participations,count(DISTINCT "organisationID") AS organisations,max("contentUpdateDate") AS latest FROM organizations'
            )
            organisations = dict(cursor.fetchone())
            cursor.execute(
                "SELECT count(*) AS completed FROM project_embeddings WHERE embedding_status='completed' AND combined_embedding IS NOT NULL"
            )
            embeddings = dict(cursor.fetchone())
            cursor.execute("""SELECT d.id,d.title,d.document_type,d.programme_year,d.version,d.status,
                d.source_url,d.file_hash,d.metadata,d.last_updated,coalesce(c.n,0) AS chunks
                FROM horizon_documents d LEFT JOIN (SELECT document_id,count(*) AS n FROM document_chunks GROUP BY document_id) c ON c.document_id=d.id
                WHERE d.created_by IS NULL""")
            general = [dict(row) for row in cursor.fetchall()]
            cursor.execute("""SELECT d.id,d.document_title AS title,d.document_type,
                d.metadata->>'programme_year' AS programme_year,d.document_version AS version,
                'active' AS status,d.document_url AS source_url,d.file_hash,d.metadata,d.last_updated,
                coalesce(c.n,0) AS chunks FROM shared_documents d LEFT JOIN
                (SELECT document_id,count(*) AS n FROM shared_document_chunks GROUP BY document_id) c ON c.document_id=d.id""")
            shared = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                "SELECT count(*) AS records,count(*) FILTER(WHERE embedding IS NOT NULL) AS embedded FROM document_chunks c JOIN horizon_documents d ON d.id=c.document_id WHERE d.created_by IS NULL"
            )
            chunks = dict(cursor.fetchone())
            cursor.execute(
                "SELECT programme,count(*) AS records FROM funding_calls GROUP BY programme ORDER BY count(*) DESC"
            )
            calls = [dict(row) for row in cursor.fetchall()]
    coverage = describe_coverage(
        projects["count"],
        organisations["participations"],
        projects["latest"],
        projects["programmes"],
    )
    try:
        coverage = apply_snapshot_provenance(coverage, json.loads(SNAPSHOT_PATH.read_text()))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        health = CallCatalog(settings.database_url).health()
    except Exception:
        health = {"status": "unavailable", "stale": True}
    return {
        "status": "available",
        "projects": {
            "count": projects["count"],
            "organisations": organisations["organisations"],
            "participations": organisations["participations"],
            "embedded": embeddings["completed"],
            "coverage": coverage,
        },
        "documents": {
            **document_inventory(general, shared),
            "chunks": chunks["records"],
            "embedded_chunks": chunks["embedded"],
        },
        "calls": {"count": sum(r["records"] for r in calls), "programmes": calls, "health": health},
    }


def graph_overview():
    from app.core.neo4j_config import neo4j_db

    # Database count-store queries avoid scanning project text/property payloads.
    nodes = neo4j_db.execute_query("MATCH (n) RETURN count(n) AS count")[0]["count"]
    relationships = neo4j_db.execute_query(
        "MATCH ()-[r]->() RETURN type(r) AS type,count(r) AS count ORDER BY count DESC"
    )
    labels = neo4j_db.execute_query(
        "MATCH (n) UNWIND labels(n) AS label RETURN label,count(*) AS count ORDER BY count DESC"
    )
    return {
        "status": "available",
        "nodes": nodes,
        "connections": sum(r["count"] for r in relationships),
        "relationships": relationships,
        "labels": labels,
        "note": "Connections are stored directed relationships. Collaboration links are derived from recorded project participation; they do not imply current partner availability.",
    }


async def data_overview():
    async def bounded(function, timeout):
        try:
            return await asyncio.wait_for(asyncio.to_thread(function), timeout)
        except Exception:
            return {
                "status": "unavailable",
                "message": "This source could not be checked. Retry to refresh its figures.",
            }

    postgres, graph = await asyncio.gather(
        bounded(postgres_overview, 15), bounded(graph_overview, 10)
    )
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": (
            "available"
            if postgres["status"] == graph["status"] == "available"
            else "partial"
            if "available" in (postgres["status"], graph["status"])
            else "unavailable"
        ),
        "database": postgres,
        "graph": graph,
    }
