"""Independent funding-data evidence, without application/tool imports or model calls.

The live runner can query its existing local PostgreSQL container without reading
an application DSN or credential files. Every query runs in a read-only
transaction. Expectations are derived from source rows, never from a tool result.
"""

import json
import re
import subprocess
from collections.abc import Callable
from decimal import Decimal
from typing import Any

Rows = list[dict[str, Any]]
Reader = Callable[[str], Rows]
SEARCH_FUNCTIONS = frozenset({"hybrid_search", "search_documents", "keyword_search"})

# This evaluation reads the funding corpus only. Conversation/session/profile
# records are outside its source of truth and must never enter model prompts.
FUNDING_RELATIONS = SEARCH_FUNCTIONS | frozenset(
    {
        "projects",
        "organizations",
        "funding_calls",
        "horizon_documents",
        "document_chunks",
        "project_embeddings",
        "information_schema.tables",
    }
)
READ_FUNCTIONS = SEARCH_FUNCTIONS | frozenset(
    {
        "count",
        "sum",
        "min",
        "max",
        "avg",
        "round",
        "percentile_cont",
        "cast",
        "stddev",
        "coalesce",
        "nullif",
        "greatest",
        "least",
        "abs",
        "floor",
        "ceil",
        "lower",
        "upper",
        "replace",
        "regexp_replace",
        "regexp_split_to_array",
        "split_part",
        "left",
        "right",
        "length",
        "char_length",
        "btrim",
        "trim",
        "substring",
        "concat",
        "concat_ws",
        "to_char",
        "extract",
        "date_part",
        "age",
        "array",
        "array_agg",
        "array_length",
        "cardinality",
        "unnest",
        "string_agg",
        "json_agg",
        "jsonb_agg",
        "json_build_object",
        "jsonb_build_object",
        "row_to_json",
        "to_json",
        "to_jsonb",
        "to_tsvector",
        "to_tsquery",
        "plainto_tsquery",
        "phraseto_tsquery",
        "websearch_to_tsquery",
        "ts_rank",
        "ts_rank_cd",
        # SQL syntax that resembles a function call in this deliberately small lexer.
        "as",
        "in",
        "exists",
        "not",
        "and",
        "or",
        "filter",
        "group",
        "over",
        "values",
        "select",
        "where",
        "on",
        "case",
        "when",
        "then",
        "else",
        "any",
        "all",
        "from",
        "join",
        "having",
    }
)


class OracleUnavailable(RuntimeError):
    """Source evidence could not be read; no model request should follow."""


class OraclePrerequisiteError(RuntimeError):
    """A selected scenario's known source evidence is missing."""


def read_statement(sql: str) -> str:
    """Allow a single internally generated SELECT/WITH statement.

    SQL literals and identifiers may contain semicolons. Statement separators
    outside quotes are rejected so callers cannot end the read-only transaction.
    PostgreSQL additionally rejects mutations inside a WITH expression.
    """
    sql = sql.strip()
    if sql.endswith(";"):
        sql = sql[:-1].rstrip()
    if not re.match(r"(?:SELECT|WITH)\b", sql, re.IGNORECASE):
        raise ValueError("Source evidence accepts SELECT/WITH queries only")
    outside = []
    quote = None
    index = 0
    while index < len(sql):
        char = sql[index]
        if quote:
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    if quote == '"':
                        outside.append('"')
                    index += 2
                    continue
                quote = None
            elif quote == '"':
                outside.append(char)
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == ";" or sql[index : index + 2] in {"--", "/*"} or char == "$":
            raise ValueError("Source evidence requires one uncommented SQL statement")
        else:
            outside.append(char)
        index += 1
    if quote:
        raise ValueError("Source evidence query has an unterminated quoted value")
    structure = "".join(outside)
    if re.search(
        r"\b(?:INSERT|UPDATE|DELETE|MERGE|TRUNCATE|CREATE|ALTER|DROP|COPY|CALL|"
        r"DO|GRANT|REVOKE|INTO|LOCK|RESET|SET)\b",
        structure,
        re.IGNORECASE,
    ):
        raise ValueError("Source evidence cannot mutate database or session state")
    # Source reads never need server file access, remote connections, process
    # cancellation, session mutation, large objects, or advisory locks.
    if re.search(
        r"\b(?:pg_\w+|dblink\w*|lo_\w+|set_config|query_to_xml|"
        r"database_to_xml|schema_to_xml)\s*\(",
        structure,
        re.IGNORECASE,
    ):
        raise ValueError("Source evidence cannot invoke administrative PostgreSQL functions")
    # CTEs may name intermediate result sets, but their own FROM/JOIN sources
    # are checked below too. No arbitrary table-valued function is needed here.
    ctes = set(re.findall(r"\b([a-z_][a-z0-9_]*)\s+AS\s*\(", structure, re.IGNORECASE))
    functions = set(re.findall(r"\b([a-z_][a-z0-9_]*)\s*\(", structure.lower()))
    unknown_functions = functions - READ_FUNCTIONS
    if unknown_functions:
        raise ValueError(
            "Unsupported source query functions: " + ", ".join(sorted(unknown_functions))
        )
    allowed = FUNDING_RELATIONS | {name.lower() for name in ctes}
    tokens = re.findall(r"[a-z_][a-z0-9_]*|[().,]", structure.lower())
    stack = []
    from_depths = set()
    for index, token in enumerate(tokens):
        if token == "(":
            stack.append(tokens[index - 1] if index else "")
        elif token == ")":
            from_depths.discard(len(stack))
            if stack:
                stack.pop()
        elif token in {
            "where",
            "group",
            "order",
            "limit",
            "having",
            "union",
            "except",
            "intersect",
        }:
            from_depths.discard(len(stack))
        elif token in {"from", "join"} or token == "," and len(stack) in from_depths:
            # FROM also appears in EXTRACT and a few scalar SQL expressions.
            if token == "from" and stack and stack[-1] in {"extract", "substring", "trim"}:
                continue
            from_depths.add(len(stack))
            next_index = index + 1
            if next_index >= len(tokens) or tokens[next_index] == "(":
                continue
            relation = tokens[next_index]
            if next_index + 2 < len(tokens) and tokens[next_index + 1] == ".":
                relation += "." + tokens[next_index + 2]
            if relation.startswith("public."):
                relation = relation.removeprefix("public.")
            if relation not in allowed:
                raise ValueError(f"Source evidence cannot read relation: {relation}")
    return sql


class DockerPsqlReader:
    """Read a local funding database with the container's own PostgreSQL client."""

    def __init__(self, container: str = "supabase_db_supabase_cli", timeout: float = 15):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", container):
            raise ValueError("Invalid local PostgreSQL container name")
        if not 0 < timeout <= 120:
            raise ValueError("Evidence timeout must be positive and at most 120 seconds")
        self.container = container
        self.timeout = timeout

    def __call__(self, sql: str) -> Rows:
        statement = read_statement(sql)
        request = (
            "BEGIN TRANSACTION READ ONLY;\n"
            "SET LOCAL statement_timeout='10s';\n"
            "SET LOCAL lock_timeout='2s';\n"
            # jsonb sorts object keys. Plain json preserves SQL column order,
            # which the read-only DB-API bridge needs for tuple fetches.
            "SELECT COALESCE(json_agg(row_to_json(source_row)), '[]'::json) "
            f"FROM ({statement}) AS source_row;\nROLLBACK;\n"
        )
        try:
            response = subprocess.run(
                [
                    "docker",
                    "exec",
                    "-i",
                    self.container,
                    "psql",
                    "-X",
                    "-qAt",
                    "-U",
                    "postgres",
                    "-d",
                    "postgres",
                    "-v",
                    "ON_ERROR_STOP=1",
                ],
                input=request,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OracleUnavailable(
                f"Read-only PostgreSQL evidence unavailable ({type(exc).__name__})"
            ) from None
        if response.returncode:
            # Raw database errors can include runtime connection details. Keep
            # the report content-free; the query name identifies the failed case.
            raise OracleUnavailable(
                f"Read-only PostgreSQL query failed (exit {response.returncode})"
            )
        try:
            records = json.loads(response.stdout, parse_float=Decimal)
        except (ValueError, TypeError):
            raise OracleUnavailable("Read-only PostgreSQL returned invalid evidence JSON") from None
        if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
            raise OracleUnavailable("Read-only PostgreSQL evidence must be a list of objects")
        return records


# These identifiers were independently inspected in the existing funding corpus.
# Missing anchors fail a prerequisite; they are never silently substituted with
# whatever an application tool happened to return.
PROJECT_ID = "101137586"
ORGANIZATION_NAME = "TECHNISCHE UNIVERSITAET MUENCHEN"
CALL_ID = "HORIZON-EIC-2026-AIC-01"

SOURCE_QUERIES = {
    "catalog_counts": """
        SELECT CURRENT_DATE AS database_date,
          (SELECT count(*) FROM public.projects) AS projects,
          (SELECT count(*) FROM public.organizations) AS participation_rows,
          (SELECT count(*) FROM public.funding_calls) AS calls,
          (SELECT count(*) FROM public.horizon_documents) AS documents,
          (SELECT count(*) FROM public.document_chunks) AS chunks,
          (SELECT count(*) FROM public.project_embeddings
           WHERE combined_embedding IS NOT NULL) AS embedded_projects
    """,
    "reference_project": """
        SELECT p.id::text AS project_id,p.acronym,p.title,p.status,
          p."startDate" AS start_date,p."endDate" AS end_date,
          p."totalCost" AS total_cost,p."ecMaxContribution" AS eu_contribution,
          p."frameworkProgramme" AS programme,p."fundingScheme" AS funding_scheme,p.topics,
          (SELECT count(*) FROM public.organizations o WHERE o."projectID"=p.id) AS partner_count,
          (SELECT count(DISTINCT country) FROM public.organizations o
           WHERE o."projectID"=p.id) AS country_count,
          (SELECT name FROM public.organizations o WHERE o."projectID"=p.id
           AND role='coordinator' ORDER BY name LIMIT 1) AS coordinator_name,
          (SELECT country FROM public.organizations o WHERE o."projectID"=p.id
           AND role='coordinator' ORDER BY name LIMIT 1) AS coordinator_country
        FROM public.projects p WHERE p.id=101137586
    """,
    "reference_partners": """
        SELECT "projectID"::text AS project_id,name,country,role,
          "activityType" AS org_type,"ecContribution" AS contribution
        FROM public.organizations WHERE "projectID"=101137586
        ORDER BY CASE WHEN role='coordinator' THEN 0 ELSE 1 END,name,country
        LIMIT 100
    """,
    "reference_organization": """
        SELECT name,country,count(DISTINCT "projectID") AS project_count,
          sum(COALESCE("ecContribution",0)) AS total_funding,
          count(*) FILTER(WHERE role='coordinator') AS coordinations
        FROM public.organizations WHERE name='TECHNISCHE UNIVERSITAET MUENCHEN'
        GROUP BY name,country ORDER BY country
    """,
    "organization_projects": """
        SELECT DISTINCT p.id::text AS project_id,p.acronym,p.title,
          p."ecMaxContribution" AS eu_contribution,o.role
        FROM public.projects p JOIN public.organizations o ON o."projectID"=p.id
        WHERE o.name='TECHNISCHE UNIVERSITAET MUENCHEN'
        ORDER BY eu_contribution DESC NULLS LAST,project_id LIMIT 20
    """,
    "organization_collaborations": """
        SELECT partner.name,partner.country,count(DISTINCT partner."projectID") AS shared_projects
        FROM public.organizations partner
        WHERE partner.name<>'TECHNISCHE UNIVERSITAET MUENCHEN' AND EXISTS (
          SELECT 1 FROM public.organizations anchor
          WHERE anchor.name='TECHNISCHE UNIVERSITAET MUENCHEN'
            AND anchor."projectID"=partner."projectID")
        GROUP BY partner.name,partner.country ORDER BY shared_projects DESC,partner.name LIMIT 20
    """,
    "country_statistics": """
        SELECT 'DE' AS country,count(DISTINCT "projectID") AS project_count,
          count(DISTINCT name) AS organization_count,
          sum(COALESCE("ecContribution",0)) AS total_funding
        FROM public.organizations WHERE country='DE'
    """,
    "reference_call": """
        SELECT topic_code,title,programme,opening_date,deadline,status AS stored_status,
          CASE WHEN deadline<CURRENT_DATE THEN 'closed' ELSE lower(status) END AS effective_status,
          budget_total,cluster,action_type,portal_url
        FROM public.funding_calls WHERE topic_code='HORIZON-EIC-2026-AIC-01'
    """,
    "open_calls": """
        SELECT topic_code,title,programme,opening_date,deadline,status AS stored_status,
          'open' AS effective_status,budget_total,cluster,action_type,portal_url
        FROM public.funding_calls WHERE lower(status)='open' AND deadline>=CURRENT_DATE
          AND (opening_date IS NULL OR opening_date<=CURRENT_DATE)
        ORDER BY deadline,topic_code LIMIT 10
    """,
    "programme_calls": """
        SELECT programme,count(*) AS call_count,min(deadline) AS first_deadline,
          max(deadline) AS last_deadline,
          count(*) FILTER(WHERE lower(status)='open' AND deadline>=CURRENT_DATE
            AND (opening_date IS NULL OR opening_date<=CURRENT_DATE)) AS currently_open_count
        FROM public.funding_calls GROUP BY programme ORDER BY programme
    """,
    "document_evidence": """
        SELECT COALESCE(d.metadata->>'programme','horizon_europe') AS programme,
          c.id::text AS chunk_id,d.id::text AS document_id,d.title,c.page_number,
          left(c.content,12000) AS content
        FROM public.document_chunks c JOIN public.horizon_documents d ON d.id=c.document_id
        WHERE c.id IN ('68a532bc-85e9-4d13-9025-beffe61c5d3e',
          '0e3ff26c-ba40-4ea2-b8c7-4f4c6182e64c',
          '223b04be-d95f-4d71-85ed-d3f5216e8707',
          '04e5fb06-7a21-40fe-911c-a53351187e8b')
        ORDER BY programme,chunk_id
    """,
    "horizon_consortium_evidence": """
        SELECT c.id::text AS chunk_id,d.id::text AS document_id,d.title,c.page_number,
          left(c.content,12000) AS content
        FROM public.document_chunks c JOIN public.horizon_documents d ON d.id=c.document_id
        WHERE (d.title ILIKE '%horizon%' OR d.title ILIKE '%grant%agreement%')
          AND c.content ILIKE '%independent%'
          AND regexp_replace(c.content,'[[:space:]]+',' ','g')
              ~* '(three|3) (independent )?(legal )?entities'
          AND (c.content ILIKE '%member state%' OR c.content ILIKE '%associated%')
          AND c.page_number IS NOT NULL
        ORDER BY CASE WHEN d.title ILIKE '%general%annex%' THEN 0 ELSE 1 END,
          length(c.content),c.id LIMIT 20
    """,
    "document_coverage": """
        SELECT COALESCE(d.metadata->>'programme','horizon_europe') AS programme,
          count(DISTINCT d.id) AS documents,count(c.id) AS chunks
        FROM public.horizon_documents d JOIN public.document_chunks c ON c.document_id=d.id
        GROUP BY COALESCE(d.metadata->>'programme','horizon_europe') ORDER BY programme
    """,
    "hydrogen_benchmark": """
        SELECT count(*) AS project_count,min(p."ecMaxContribution") AS min_budget,
          max(p."ecMaxContribution") AS max_budget,avg(p."ecMaxContribution") AS avg_budget,
          sum(p."ecMaxContribution") AS total_funding,
          percentile_cont(0.5) WITHIN GROUP(ORDER BY p."ecMaxContribution") AS median_budget
        FROM public.projects p WHERE p."frameworkProgramme"='HORIZON' AND p.topics ILIKE '%CL5%'
          AND (p.title ILIKE '%hydrogen%' OR p.objective ILIKE '%hydrogen%'
               OR p.topics ILIKE '%hydrogen%')
          AND p."ecMaxContribution">0 AND EXISTS (
            SELECT 1 FROM public.organizations o WHERE o."projectID"=p.id
              AND o."organisationID" IS NOT NULL)
    """,
    "hydrogen_consortia": """
        SELECT count(*) AS project_count,min(partners) AS min_partners,
          max(partners) AS max_partners,avg(partners) AS avg_partners,
          avg(countries) AS avg_countries
        FROM (
          SELECT p.id,count(DISTINCT o."organisationID") AS partners,
            count(DISTINCT o.country) AS countries
          FROM public.projects p JOIN public.organizations o ON o."projectID"=p.id
          WHERE p."frameworkProgramme"='HORIZON' AND p.topics ILIKE '%CL5%'
            AND (p.title ILIKE '%hydrogen%' OR p.objective ILIKE '%hydrogen%')
          GROUP BY p.id HAVING count(DISTINCT o."organisationID")>0
        ) AS consortium
    """,
    "hydrogen_history": """
        SELECT extract(year FROM "startDate")::int AS year,count(*) AS project_count,
          sum("ecMaxContribution") AS total_funding
        FROM public.projects WHERE topics ILIKE '%CLEANH2%' AND "startDate" IS NOT NULL
        GROUP BY extract(year FROM "startDate") ORDER BY year
    """,
    "topic_neighbors": """
        SELECT p.id::text AS project_id,p.acronym,p.title,p.topics,
          p."ecMaxContribution" AS eu_contribution
        FROM public.projects p
        WHERE p.id<>101137586 AND p.topics ILIKE '%HORIZON-JTI-CLEANH2-2023-06-01%'
        ORDER BY p."startDate" DESC,p.id LIMIT 20
    """,
    "semantic_neighbors": """
        SELECT p.id::text AS project_id,p.acronym,p.title,
          1-(candidate.combined_embedding <=> anchor.combined_embedding) AS similarity
        FROM public.project_embeddings candidate
        JOIN public.projects p ON p.id=candidate.project_id
        JOIN public.project_embeddings anchor ON anchor.project_id=101137586
        WHERE candidate.project_id<>anchor.project_id
          AND candidate.combined_embedding IS NOT NULL AND anchor.combined_embedding IS NOT NULL
        ORDER BY candidate.combined_embedding <=> anchor.combined_embedding,p.id LIMIT 5
    """,
    "cluster_projects": """
        SELECT p.id::text AS project_id,p.acronym,p.title,p.topics,
          p."ecMaxContribution" AS eu_contribution
        FROM public.projects p WHERE p."frameworkProgramme"='HORIZON'
          AND p.topics ILIKE '%CL5%'
        ORDER BY p."ecMaxContribution" DESC NULLS LAST,p.id LIMIT 10
    """,
    "cluster_statistics": """
        SELECT CASE WHEN topics ILIKE '%CL4%' THEN 'CL4' ELSE 'CL5' END AS cluster,
          count(*) AS project_count,sum("ecMaxContribution") AS total_funding,
          avg("ecMaxContribution") AS avg_funding
        FROM public.projects WHERE "frameworkProgramme"='HORIZON'
          AND (topics ILIKE '%CL4%' OR topics ILIKE '%CL5%')
        GROUP BY CASE WHEN topics ILIKE '%CL4%' THEN 'CL4' ELSE 'CL5' END
        ORDER BY cluster
    """,
    "experienced_hydrogen_partners": """
        SELECT o.name,o.country,count(DISTINCT p.id) AS project_count,
          count(*) FILTER(WHERE o.role='coordinator') AS coordinations,
          sum(COALESCE(o."ecContribution",0)) AS total_funding
        FROM public.projects p JOIN public.organizations o ON o."projectID"=p.id
        WHERE p."frameworkProgramme" IN ('HORIZON','H2020')
          AND (p.title ILIKE '%hydrogen%' OR p.objective ILIKE '%hydrogen%')
          AND o."organisationID" IS NOT NULL
        GROUP BY o.name,o.country HAVING count(DISTINCT p.id)>=2
        ORDER BY project_count DESC,coordinations DESC,total_funding DESC,o.name LIMIT 20
    """,
    "geographic_coverage": """
        SELECT p.id::text AS project_id,count(DISTINCT o."organisationID") AS partner_count,
          array_agg(DISTINCT o.country) AS countries
        FROM public.projects p JOIN public.organizations o ON o."projectID"=p.id
        WHERE p."frameworkProgramme"='HORIZON' AND p.topics ILIKE '%CL5%'
          AND p.topics NOT ILIKE '%WIDERA%' AND o.country IS NOT NULL
        GROUP BY p.id HAVING count(DISTINCT o."organisationID")>=3
        ORDER BY p.id
    """,
}


def discover_ground_truth(reader: Reader) -> dict[str, Rows]:
    """Collect bounded source facts without querying tools or invoking inference."""
    facts = {}
    for name, sql in SOURCE_QUERIES.items():
        try:
            facts[name] = reader(sql)
        except OracleUnavailable:
            raise OracleUnavailable(f"Source evidence query unavailable: {name}") from None
    return facts


def require_facts(facts: dict[str, Rows], *names: str) -> None:
    """Fail a selected scenario before spending tokens when its evidence is absent."""
    missing = [name for name in names if not facts.get(name)]
    if missing:
        raise OraclePrerequisiteError("Missing source evidence: " + ", ".join(missing))
