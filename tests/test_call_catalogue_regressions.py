"""Call discovery regressions: no real providers, network or database required."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import numpy as np
import pytest

from app.services.call_catalog import CallCatalog, parse_portal_result
from app.services.call_query import effective_status, keyword_predicate, query_groups, query_year
from app.services.embedding_service import EmbeddingService
from app.services.tools.call_search import search_funding_calls_execute
from app.services.agents.framework.call_context import compact_call_context
from app.services.cache.speculative_executor import SpeculativeExecutor
from app.services.call_enrichment_service import CallEnrichmentService


def portal_topic(**changes):
    metadata = {
        "identifier": ["HORIZON-HLTH-2027-02-TOOL-01-two-stage"],
        "title": ["Predictive biomarkers using artificial intelligence"],
        "description": ["<p>Clinical AI research &amp; validation.</p>"],
        "keywords": ["Health", "Artificial intelligence"],
        "status": ["31094502"],
        "startDate": ["2026-10-29T00:00:00.000+0000"],
        "deadlineDate": ["2027-09-16", "2027-02-17"],
    }
    metadata.update(changes)
    return {"metadata": metadata}


@pytest.mark.parametrize(
    "query",
    [
        "zoek calls op AI & Health",
        "AI healthcare",
        "kunstmatige intelligentie en zorg",
        "find funding calls for artificial intelligence in health 2027",
    ],
)
def test_cross_domain_query_keeps_two_concepts(query):
    groups = query_groups(query)
    assert len(groups) == 2
    assert "artificial intelligence" in groups[0]
    assert "clinical" in groups[1]


def test_user_punctuation_never_becomes_tsquery_syntax_or_sql():
    sql, values = keyword_predicate("AI & Health'); DROP TABLE funding_calls; --")
    assert "DROP TABLE" not in sql
    assert all("\\m" in v and "\\M" in v for v in values)
    assert "\\mai\\M" in values
    assert "\\martificial\\ intelligence\\M" in values
    assert query_year("AI health 2027") == 2027
    assert query_year("AI health 2026-2027") is None


def test_parse_source_dates_preserves_first_stage_and_year():
    row = parse_portal_result(portal_topic())
    assert row["call_year"] == 2027
    assert row["cluster"] == "CL1"
    assert row["programme"] == "horizon_europe"
    assert row["opening_date"] == date(2026, 10, 29)
    assert row["deadline"] == date(2027, 2, 17)
    assert row["second_stage_deadline"] == date(2027, 9, 16)
    assert "<p>" not in row["scope"]
    assert "Clinical AI research & validation" in row["scope"]
    assert row["portal_url"].endswith("HORIZON-HLTH-2027-02-TOOL-01-TWO-STAGE")


def test_portal_actions_override_search_summary_dates():
    import json

    row = parse_portal_result(
        portal_topic(
            actions=[
                json.dumps(
                    [
                        {
                            "plannedOpeningDate": "2026-11-01",
                            "deadlineDates": ["2027-01-15", "2027-09-01"],
                            "types": [
                                {"typeOfAction": "HORIZON-RIA Research and Innovation Actions"}
                            ],
                        }
                    ]
                )
            ]
        )
    )
    assert row["deadline"] == date(2027, 1, 15)
    assert row["second_stage_deadline"] == date(2027, 9, 1)
    assert row["action_type"] == "RIA"


def test_unknown_or_missing_source_metadata_is_not_invented():
    assert parse_portal_result({}) is None
    assert parse_portal_result(portal_topic(status=["unexpected"])) is None
    assert parse_portal_result(portal_topic(identifier=["NOT-A-PROGRAMME-2027"])) is None


@pytest.mark.parametrize(
    "stored,opening,deadline,expected",
    [
        ("open", "2027-06-03", "2027-09-16", "upcoming"),
        ("upcoming", "2026-10-29", "2027-02-17", "open"),
        ("open", None, "2026-01-06", "closed"),
        ("closed", "2026-10-29", "2027-02-17", "closed"),
    ],
)
def test_dates_are_authoritative_without_reopening_closed_topics(
    stored, opening, deadline, expected
):
    assert (
        effective_status(
            {"status": stored, "opening_date": opening, "deadline": deadline},
            today=date(2026, 11, 8),
        )
        == expected
    )


def response(data, status=200):
    return httpx.Response(status, json=data, request=httpx.Request("POST", "https://example.test"))


def test_partial_refresh_cannot_touch_database_or_freshness_marker():
    client = MagicMock()
    client.post.side_effect = [
        response({"totalResults": 101, "results": [portal_topic()] * 100}),
        response({"error": "temporary outage"}, 503),
    ]
    with patch("app.services.call_catalog.psycopg2.connect") as connect:
        with pytest.raises(httpx.HTTPStatusError):
            CallCatalog("unused", client=client).sync()
        connect.assert_not_called()


@pytest.mark.parametrize(
    "data",
    [
        {"totalResults": 0, "results": []},
        {"totalResults": 1, "results": []},
        {"totalResults": 101, "results": [portal_topic()]},
    ],
)
def test_empty_or_truncated_snapshot_is_rejected(data):
    client = MagicMock()
    client.post.return_value = response(data)
    with patch("app.services.call_catalog.psycopg2.connect") as connect:
        with pytest.raises(ValueError):
            CallCatalog("unused", client=client).sync(max_pages=1)
        connect.assert_not_called()


def test_successful_refresh_is_one_transaction_and_deduplicates_topic_versions():
    client = MagicMock()
    older = portal_topic(title=["Old title"], esDA_IngestDate=["2026-01-01"])
    newer = portal_topic(title=["New official title"], esDA_IngestDate=["2026-10-29"])
    client.post.return_value = response({"totalResults": 2, "results": [older, newer]})
    connection = MagicMock()
    with (
        patch("app.services.call_catalog.psycopg2.connect", return_value=connection),
        patch("app.services.call_catalog.execute_values") as upsert,
        patch.object(CallCatalog, "health", return_value={"stale": False}),
    ):
        result = CallCatalog("unused", client=client).sync()
    assert result["topics_synced"] == 1
    assert len(upsert.call_args.args[2]) == 1
    assert upsert.call_args.args[2][0][2] == "New official title"
    connection.close.assert_called_once()


@pytest.mark.asyncio
async def test_default_discovery_includes_open_and_upcoming_with_coverage():
    fake = SimpleNamespace(
        _db_url="unused",
        search_calls=MagicMock(
            return_value={
                "success": True,
                "calls": [
                    {"topic_code": "OPEN", "status": "open", "call_year": 2027},
                    {"topic_code": "UPCOMING", "status": "upcoming", "call_year": 2027},
                    {"topic_code": "CLOSED", "status": "closed", "call_year": 2027},
                ],
            }
        ),
    )
    with (
        patch("app.services.local_call_search_service.LocalCallSearchService", return_value=fake),
        patch.object(CallCatalog, "health", return_value={"stale": True}),
    ):
        result = await search_funding_calls_execute("AI & Health 2027")
    assert result["calls_found"] == 2
    assert {c["call_id"] for c in result["calls"]} == {"OPEN", "UPCOMING"}
    assert result["limitations"]
    assert fake.search_calls.call_args.kwargs["year_filter"] == "2027"
    assert fake.search_calls.call_args.kwargs["status_filter"] is None


@pytest.mark.asyncio
async def test_failure_is_not_reported_as_successful_zero_hits():
    fake = SimpleNamespace(
        _db_url="unused",
        search_calls=MagicMock(
            return_value={
                "success": False,
                "error": "database unavailable",
                "calls": [],
            }
        ),
    )
    with (
        patch("app.services.local_call_search_service.LocalCallSearchService", return_value=fake),
        patch.object(CallCatalog, "health", return_value={"stale": True}),
    ):
        result = await search_funding_calls_execute("AI health")
    assert result["success"] is False
    assert result["error"] == "database unavailable"
    assert result["limitations"]


def test_zero_embedding_is_not_a_working_provider():
    service = EmbeddingService.__new__(EmbeddingService)
    service.embedding_dimension = 3
    assert not service.validate_embedding(np.zeros(3))
    assert not service.validate_embedding(np.full(3, np.nan))
    assert not service.validate_embedding(np.zeros((3, 3)))
    assert service.validate_embedding(np.array([0.1, 0.2, 0.3]))


def test_topic_missing_from_active_snapshot_is_unverified_not_claimed_cancelled():
    call = {
        "status": "open",
        "opening_date": "2026-10-01",
        "deadline": "2027-09-16",
        "metadata": {"portal_missing_from_snapshot": True},
    }
    assert effective_status(call, today=date(2026, 11, 8)) == "unknown"
    assert call["status"] == "open"  # Historical source status is preserved.
    assert (
        effective_status(
            {"status": "unknown", "opening_date": "2026-10-01"}, today=date(2026, 11, 8)
        )
        == "unknown"
    )


def test_call_context_keeps_all_shortlisted_identifiers_when_scopes_are_huge():
    import json

    calls = [
        {
            "call_id": f"TOPIC-{i}",
            "title": f"AI health topic {i}",
            "scope": "Long official scope. " * 2000,
            "deadline": "2027-02-17",
            "status": "open",
            "url": f"https://ec.europa.eu/topic/{i}",
        }
        for i in range(8)
    ]
    original = {
        "calls": calls,
        "calls_found": 8,
        "catalogue": {"stale": False},
        "limitations": ["Source limitation to preserve"],
    }
    context = compact_call_context(original, 6000)
    assert len(json.dumps(context)) <= 6000
    assert [c["call_id"] for c in context["calls"]] == [f"TOPIC-{i}" for i in range(8)]
    assert context["catalogue"] == {"stale": False}
    assert context["limitations"]
    assert len(original["calls"][0]["scope"]) > 6000  # Full API result is not mutated.


def test_speculative_search_preserves_short_acronym_and_requested_year():
    executor = SpeculativeExecutor.__new__(SpeculativeExecutor)
    params = executor._generate_default_params(
        "search_funding_calls", "zoek calls op AI & Health 2027"
    )
    assert params == {"keywords": "ai health", "year": 2027}
    assert executor._params_compatible(
        "search_funding_calls",
        params,
        {"keywords": "artificial intelligence healthcare", "year": 2027},
    )
    for changed in ({"status": "open"}, {"year": 2026}, {"cluster": "CL1"}, {"keywords": "health"}):
        assert not executor._params_compatible(
            "search_funding_calls", params, {**params, **changed}
        )


def test_semantic_fallback_applies_year_cluster_and_status_before_limit():
    from app.services.local_call_search_service import LocalCallSearchService

    service = LocalCallSearchService.__new__(LocalCallSearchService)
    service._db_url = "unused"
    service._semantic_search_available = True
    service._embedding_service = SimpleNamespace(
        generate_query_embedding=lambda q: np.array([0.1, 0.2, 0.3]),
        validate_embedding=lambda e: True,
    )
    conn = MagicMock()
    conn.cursor.return_value.fetchall.return_value = []
    with patch("app.services.local_call_search_service.psycopg2.connect", return_value=conn):
        service._search_semantic_calls(
            "AI health",
            year_filter=2027,
            cluster="CL1",
            action_type="RIA",
            status_filter="upcoming",
        )
    sql, values = conn.cursor.return_value.execute.call_args.args
    assert "call_year = %s" in sql and "cluster = %s" in sql and "action_type = %s" in sql
    assert 2027 in values and "CL1" in values and "RIA" in values and "upcoming" in values
    assert sql.count("%s") == len(values)


@pytest.mark.parametrize("returned", ["OTHER-TOPIC-2027", "HORIZON-HLTH-2027-02-TOOL-01"])
def test_point_lookup_never_uses_an_unrelated_or_parent_topic(returned):
    service = CallEnrichmentService("unused")
    service._client = MagicMock()
    service._client.post.return_value = response({"results": [portal_topic(identifier=[returned])]})
    assert service._fetch_via_search_api("HORIZON-HLTH-2027-02-TOOL-01-TWO-STAGE") is None


def test_detail_cache_retains_programme_and_year_without_emptying_existing_scope():
    conn = MagicMock()
    service = CallEnrichmentService("unused")
    with patch("app.services.call_enrichment_service.psycopg2.connect", return_value=conn):
        assert service._cache_call("DIGITAL-2027-AI-01", {"status": "upcoming", "title": "AI"})
    sql, values = conn.cursor.return_value.execute.call_args.args
    assert sql.count("%s") == len(values)
    assert values[0] == "digital_europe" and values[-1] == 2027
    assert "NULLIF(EXCLUDED.scope, '')" in sql
