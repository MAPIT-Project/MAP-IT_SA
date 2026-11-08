"""Regressions discovered in the November 2026 live readiness check."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import psycopg2
import pytest

from app.services.local_project_search_service import LocalProjectSearchService
from app.services.project_coverage import (
    describe_coverage,
    project_database_coverage,
    coverage_note,
)
from app.services.agents.framework.evidence import unavailable_evidence, evidence_failure_answer
from app.services.agents.tool_registry import ToolCall


@pytest.mark.parametrize("name", ["Horizon Europe", "HORIZON_EUROPE", "horizon-europe", "HORIZON"])
def test_explicit_framework_name_does_not_exclude_all_projects(name):
    service = LocalProjectSearchService.__new__(LocalProjectSearchService)
    filters, terms = service._parse_query("AI healthcare", {"programme": name})
    assert filters["programme"] == "HORIZON"
    assert "ai" in terms and "healthcare" in terms


def test_old_source_date_is_not_presented_as_import_date():
    result = describe_coverage(
        13865, 89348, datetime(2024, 9, 19), ["HORIZON"], today=date(2026, 11, 8)
    )
    assert result["status"] == "older_source_snapshot"
    assert result["import_date"] is None
    assert result["organization_participation_rows"] == 89348
    assert "2024-09-19" in coverage_note(result)


def test_recent_record_does_not_prove_complete_corpus():
    result = describe_coverage(1, 3, datetime(2026, 11, 8), ["HORIZON"], today=date(2026, 11, 8))
    assert result["status"] == "coverage_unverified"
    assert "not a complete live" in result["warning"]


def test_coverage_database_failure_does_not_leak_connection_details():
    with patch(
        "app.services.project_coverage.psycopg2.connect",
        side_effect=psycopg2.OperationalError("secret connection string"),
    ):
        result = project_database_coverage()
    assert result["status"] == "unavailable"
    assert "secret" not in str(result)


@pytest.mark.asyncio
async def test_partner_dispatch_preserves_requested_programme():
    from tests.tool_scenarios.environment import make_agent

    agent = make_agent()
    tool = MagicMock()
    tool.find_partners.return_value = {"partners": []}
    with patch("app.services.tools.partner_discovery.PartnerDiscoveryTool", return_value=tool):
        await agent._tool_find_experienced_partners(
            {"topic_keywords": "AI healthcare", "programme": "HORIZON"}
        )
    assert tool.find_partners.call_args.kwargs["programme"] == "HORIZON"


def test_failed_and_empty_retrieval_cannot_be_treated_as_evidence():
    calls = [
        ToolCall("get_call_details", {}, success=False, error="not found"),
        ToolCall("search_documents", {}, success=True, result={"documents": []}),
    ]
    assert unavailable_evidence(calls)
    assert "niet verifiëren" in evidence_failure_answer("Wat is de deadline?")
    assert "does not prove" in evidence_failure_answer("What is the deadline?")


def test_zero_count_statistic_and_usable_excerpt_are_not_discarded():
    assert not unavailable_evidence(
        [ToolCall("get_country_statistics", {}, success=True, result={"project_count": 0})]
    )
    assert not unavailable_evidence(
        [
            ToolCall(
                "search_documents",
                {},
                success=True,
                result={"documents": [{"content": "Retrieved rule"}]},
            )
        ]
    )
    assert not unavailable_evidence([])


def test_recorded_import_date_requires_matching_verified_snapshot():
    from app.services.project_coverage import apply_snapshot_provenance

    coverage = describe_coverage(
        24471, 151627, datetime(2026, 11, 7, 19, 55, 38), ["HORIZON"], today=date(2026, 11, 8)
    )
    metadata = {
        **{
            k: coverage[k]
            for k in (
                "projects_indexed",
                "organization_participation_rows",
                "latest_record_source_update",
            )
        },
        "verified": True,
        "programme": "HORIZON",
        "import_date": "2026-11-08T22:15:00+00:00",
        "verified_at": "2026-11-08T22:25:00+00:00",
        "source_sha256": "a" * 64,
        "source_project_count": 24470,
    }
    result = apply_snapshot_provenance(coverage, metadata)
    assert result["status"] == "verified_snapshot"
    assert result["import_date"].startswith("2026-11-08")
    assert "geïmporteerd op 2026-11-08" in coverage_note(result)
    assert (
        apply_snapshot_provenance(coverage, {**metadata, "projects_indexed": 1})["import_date"]
        is None
    )
    older = {**coverage, "status": "older_source_snapshot"}
    assert apply_snapshot_provenance(older, metadata)["status"] == "older_source_snapshot"


def test_failed_verification_cannot_publish_snapshot_metadata(tmp_path):
    from app.services.project_coverage import write_snapshot_provenance

    target = tmp_path / "snapshot.json"
    with pytest.raises(ValueError, match="complete successful"):
        write_snapshot_provenance({"complete": False}, "2026-11-08T22:15:00+00:00", target)
    assert not target.exists()


def test_coverage_footer_uses_english_for_english_demo_questions():
    from app.services.agents.framework.evidence import is_dutch_query

    data = {
        "latest_record_source_update": "2026-11-07T19:55:38",
        "import_date": "2026-11-08T22:15:33+00:00",
    }
    assert "Data coverage" in coverage_note(
        data, english=not is_dutch_query("Which Dutch organisations have experience?")
    )
    assert "Datadekking" in coverage_note(
        data, english=not is_dutch_query("Welke Nederlandse organisaties hebben ervaring?")
    )
