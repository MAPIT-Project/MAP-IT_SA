"""Refresh the local call catalogue from the official EU Funding & Tenders API.

No AI credentials are needed. A failed/incomplete download never marks the catalogue
fresh, and records are upserted rather than deleting document-derived information.
"""

import json
import logging
import math
import re
from contextlib import closing
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser

import httpx
import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json, execute_values

from .call_query import as_date, effective_status

logger = logging.getLogger(__name__)
SOURCE = "eu_funding_tenders"


def restrict_sync_state(cursor):
    """Supabase default grants must not let visitors forge source freshness."""
    cursor.execute("REVOKE ALL ON funding_call_sync_state FROM PUBLIC")
    cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")
    for (role,) in cursor.fetchall():
        cursor.execute(
            sql.SQL("REVOKE ALL ON funding_call_sync_state FROM {}").format(sql.Identifier(role))
        )


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value) -> str:
    parser = _Text()
    parser.feed(str(value or ""))
    return " ".join(unescape(" ".join(parser.parts)).split())


def programme_for_topic(code: str) -> str | None:
    code = code.upper()
    return next(
        (
            name
            for prefixes, name in (
                (("HORIZON-", "ERC-", "H2020-"), "horizon_europe"),
                (("DIGITAL-",), "digital_europe"),
                (("EU4H-", "EU4HEALTH-"), "eu4health"),
                (("ERASMUS-",), "erasmus"),
                (("CREA-",), "creative_europe"),
                (("LIFE-",), "life"),
            )
            if code.startswith(prefixes)
        ),
        None,
    )


def parse_portal_result(result: dict) -> dict | None:
    metadata = result.get("metadata") or {}

    def first(key, default=""):
        value = metadata.get(key, default)
        return (value[0] if value else default) if isinstance(value, list) else value

    code = str(first("identifier")).upper().strip()
    programme = programme_for_topic(code)
    if not programme or not re.fullmatch(r"[A-Z0-9-]+", code):
        return None
    title = plain_text(first("title") or result.get("content"))
    if not title:
        return None
    year = re.search(r"\b(20\d{2})\b", code)
    description = plain_text(
        first("description") or first("topicDescription") or result.get("summary")
    )
    keywords = metadata.get("keywords") or []
    if not isinstance(keywords, list):
        keywords = [keywords]
    # Subject keywords are authoritative source metadata, useful when a short title
    # does not spell out the medical/AI domain. Keep them searchable and attributed.
    scope = description
    if keywords:
        scope += "\nSource keywords: " + "; ".join(plain_text(k) for k in keywords)
    status = {"31094501": "upcoming", "31094502": "open", "31094503": "closed"}.get(
        str(first("status")), "unknown"
    )
    if status == "unknown":
        return None
    openings = as_date(first("startDate"))
    raw_deadlines = metadata.get("deadlineDate") or []
    if not isinstance(raw_deadlines, list):
        raw_deadlines = [raw_deadlines]
    deadlines = sorted(filter(None, [as_date(d) for d in raw_deadlines]))
    # Store the first-stage deadline separately from the second stage. A later
    # invitation-only deadline must not make an expired first stage look open.
    deadline = deadlines[0] if deadlines else None
    action_type = None
    try:
        actions = json.loads(first("actions", "[]"))
        if actions:
            action = actions[0]
            openings = as_date(action.get("plannedOpeningDate")) or openings
            action_dates = sorted(filter(None, map(as_date, action.get("deadlineDates", []))))
            if action_dates:
                deadlines, deadline = action_dates, action_dates[0]
            action_types = action.get("types") or []
            if action_types:
                match = re.search(
                    r"\b(?:RIA|IA|CSA|COFUND|PCP|PPI)\b", action_types[0].get("typeOfAction", "")
                )
                action_type = match.group() if match else None
    except (ValueError, TypeError, AttributeError):
        logger.warning("Malformed portal action metadata for %s", code)
    cluster = None
    if programme == "horizon_europe":
        match = re.search(r"-(CL[1-6])-", code)
        cluster = match.group(1) if match else ("CL1" if "-HLTH-" in code else None)
    row = {
        "programme": programme,
        "topic_code": code,
        "title": title,
        "scope": scope.strip(),
        "call_year": int(year.group(1)) if year else None,
        "opening_date": openings,
        "deadline": deadline,
        "second_stage_deadline": deadlines[1] if len(deadlines) > 1 else None,
        "status": status,
        "cluster": cluster,
        "action_type": action_type,
        "portal_url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/"
        + code,
        "source_updated_at": str(first("esDA_IngestDate")),
    }
    row["status"] = effective_status(row)
    return row


class CallCatalog:
    def __init__(self, db_url: str, client=None):
        self.db_url = db_url
        self.client = client

    def health(self) -> dict:
        try:
            with closing(psycopg2.connect(self.db_url, connect_timeout=5)) as conn, conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*), max(call_year) FROM funding_calls")
                    count, latest_year = cur.fetchone()
                    cur.execute("SELECT to_regclass('public.funding_call_sync_state')")
                    last_sync = None
                    if cur.fetchone()[0]:
                        cur.execute(
                            "SELECT last_success FROM funding_call_sync_state WHERE source = %s",
                            (SOURCE,),
                        )
                        row = cur.fetchone()
                        last_sync = row[0] if row else None
            stale = not last_sync or datetime.now(timezone.utc) - last_sync > timedelta(hours=24)
            return {
                "source": SOURCE,
                "calls_indexed": count,
                "latest_call_year": latest_year,
                "last_successful_sync": last_sync.isoformat() if last_sync else None,
                "stale": stale,
                "status": "degraded" if stale else "healthy",
            }
        except psycopg2.Error as exc:
            logger.warning("Call catalogue health unavailable (%s)", type(exc).__name__)
            return {"source": SOURCE, "stale": True, "status": "unavailable"}

    def _download(self, client, max_pages: int) -> list[dict]:
        from ..core.config import settings

        query = {
            "bool": {
                "must": [
                    {"terms": {"type": ["1", "2", "8"]}},
                    {"terms": {"status": ["31094501", "31094502"]}},
                ]
            }
        }
        rows, expected = [], None
        for page in range(1, max_pages + 1):
            response = client.post(
                settings.eu_portal_base_url,
                params={"apiKey": "SEDIA", "text": "***", "pageSize": 100, "pageNumber": page},
                files={
                    "query": ("blob", json.dumps(query), "application/json"),
                    "languages": ("blob", '["en"]', "application/json"),
                    "sort": ("blob", '{"field":"identifier","order":"ASC"}', "application/json"),
                },
            )
            response.raise_for_status()
            data = response.json()
            batch = data.get("results")
            if not isinstance(batch, list) or "totalResults" not in data:
                raise ValueError("EU Portal returned an invalid search response")
            if expected is None:
                expected = int(data["totalResults"])
                if expected <= 0 or math.ceil(expected / 100) > max_pages:
                    raise ValueError("EU Portal snapshot empty or exceeds configured page limit")
            if not batch:
                raise ValueError("EU Portal pagination ended before the complete snapshot")
            rows.extend(batch)
            if page >= math.ceil(expected / 100):
                if len(rows) < expected:
                    raise ValueError("EU Portal snapshot is incomplete")
                return rows
        raise ValueError("EU Portal snapshot exceeded page limit")

    def sync(self, max_pages: int = 100) -> dict:
        # All HTTP completes before any catalogue rows or freshness markers change.
        if self.client is not None:
            raw = self._download(self.client, max_pages)
        else:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                raw = self._download(client, max_pages)
        calls = {}
        for result in raw:
            row = parse_portal_result(result)
            if row and (
                row["topic_code"] not in calls
                or row["source_updated_at"] > calls[row["topic_code"]]["source_updated_at"]
            ):
                calls[row["topic_code"]] = row
        if not calls:
            raise ValueError("EU Portal response contained no recognised programme topics")
        with closing(psycopg2.connect(self.db_url, connect_timeout=5)) as conn, conn:
            with conn.cursor() as cur:
                # Bound write time and serialize concurrent scheduled/manual refreshes.
                cur.execute("SET LOCAL statement_timeout = '120s'")
                cur.execute("SELECT pg_advisory_xact_lock(73417721)")
                cur.execute("""CREATE TABLE IF NOT EXISTS funding_call_sync_state (
                    source text PRIMARY KEY, last_success timestamptz NOT NULL,
                    topics_synced integer NOT NULL, records_downloaded integer NOT NULL)""")
                restrict_sync_state(cur)
                execute_values(
                    cur,
                    """INSERT INTO funding_calls
                    (programme, topic_code, title, scope, call_year, opening_date, deadline,
                     second_stage_deadline, status, cluster, action_type, portal_url, metadata)
                    VALUES %s ON CONFLICT (topic_code) DO UPDATE SET
                    programme = EXCLUDED.programme, title = EXCLUDED.title,
                    scope = CASE WHEN length(EXCLUDED.scope) > length(COALESCE(funding_calls.scope, ''))
                        THEN EXCLUDED.scope ELSE funding_calls.scope END,
                    call_year = COALESCE(EXCLUDED.call_year, funding_calls.call_year),
                    opening_date = COALESCE(EXCLUDED.opening_date, funding_calls.opening_date),
                    deadline = COALESCE(EXCLUDED.deadline, funding_calls.deadline),
                    second_stage_deadline = COALESCE(EXCLUDED.second_stage_deadline, funding_calls.second_stage_deadline),
                    status = EXCLUDED.status,
                    cluster = COALESCE(EXCLUDED.cluster, funding_calls.cluster),
                    action_type = COALESCE(EXCLUDED.action_type, funding_calls.action_type),
                    portal_url = EXCLUDED.portal_url,
                    metadata = COALESCE(funding_calls.metadata, '{}'::jsonb) || EXCLUDED.metadata,
                    updated_at = NOW()""",
                    [
                        (
                            c["programme"],
                            c["topic_code"],
                            c["title"],
                            c["scope"],
                            c["call_year"],
                            c["opening_date"],
                            c["deadline"],
                            c["second_stage_deadline"],
                            c["status"],
                            c["cluster"],
                            c["action_type"],
                            c["portal_url"],
                            Json(
                                {
                                    "catalog_source": SOURCE,
                                    "portal_synced_at": datetime.now(timezone.utc).isoformat(),
                                    "portal_source_updated_at": c["source_updated_at"],
                                    "portal_missing_from_snapshot": False,
                                }
                            ),
                        )
                        for c in calls.values()
                    ],
                )
                # An old portal topic absent from this complete active snapshot is
                # not verified available. Exclude it from discovery without claiming
                # cancellation/deletion. A later snapshot can restore it explicitly.
                cur.execute(
                    """UPDATE funding_calls SET metadata = COALESCE(metadata, '{}'::jsonb)
                        || '{"portal_missing_from_snapshot": true}'::jsonb
                        WHERE metadata->>'catalog_source' = %s
                        AND status IN ('open', 'upcoming')
                        AND NOT (topic_code = ANY(%s))""",
                    (SOURCE, list(calls)),
                )
                # Correct stale labels deterministically, without inferring deletion
                # or cancellation merely because a topic disappeared from a page.
                cur.execute(
                    "UPDATE funding_calls SET status = 'closed' WHERE deadline < CURRENT_DATE AND status <> 'closed'"
                )
                cur.execute(
                    """INSERT INTO funding_call_sync_state VALUES (%s, NOW(), %s, %s)
                    ON CONFLICT (source) DO UPDATE SET last_success = EXCLUDED.last_success,
                    topics_synced = EXCLUDED.topics_synced, records_downloaded = EXCLUDED.records_downloaded""",
                    (SOURCE, len(calls), len(raw)),
                )
        return {"topics_synced": len(calls), "records_downloaded": len(raw), **self.health()}
