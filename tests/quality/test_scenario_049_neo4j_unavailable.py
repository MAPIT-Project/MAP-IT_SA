"""Country-statistics degradation through current tools, plus opt-in live checks."""

import asyncio
import sys
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.tools import country_statistics as country_tool


@pytest.fixture
def graph_factory(monkeypatch):
    factory = MagicMock()
    monkeypatch.setitem(
        sys.modules,
        "app.services.data_intelligence.graph_service",
        SimpleNamespace(GraphSearchService=factory),
    )
    return factory


@pytest.fixture
def sql_fallback(monkeypatch):
    fallback = AsyncMock(
        return_value={
            "top_organizations": [{"name": "Synthetic organization"}],
            "organization_count": 1,
            "project_count": 50,
            "total_funding": 500000,
            "eligibility": {"is_eligible": True},
        }
    )
    monkeypatch.setattr(country_tool, "_get_country_stats_sql", fallback)
    return fallback


def test_country_statistics_declares_degradation_sources():
    from app.core.service_availability import (
        DEGRADABLE_TOOLS,
        TOOL_SERVICE_REQUIREMENTS,
        ServiceType,
    )

    assert ServiceType.NEO4J in DEGRADABLE_TOOLS["get_country_statistics"]
    assert ServiceType.POSTGRES in TOOL_SERVICE_REQUIREMENTS["get_country_statistics"]
    assert ServiceType.NEO4J in DEGRADABLE_TOOLS["get_programme_statistics"]


def test_country_eligibility_sets_are_disjoint():
    assert len(country_tool.EU_MEMBERS) == 27
    assert {"DE", "FR", "IT", "NL"} <= country_tool.EU_MEMBERS
    assert {"NO", "CH", "GB"} <= country_tool.ASSOCIATED_COUNTRIES
    assert not country_tool.EU_MEMBERS & country_tool.ASSOCIATED_COUNTRIES
    assert "IN" not in country_tool.EU_MEMBERS | country_tool.ASSOCIATED_COUNTRIES


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "country, code",
    [
        ("Germany", "DE"),
        ("French", "FR"),
        ("Italy", "IT"),
        ("Spanish", "ES"),
        ("Netherlands", "NL"),
        ("Poland", "PL"),
        ("Switzerland", "CH"),
        ("Norway", "NO"),
        ("de", "DE"),
    ],
)
async def test_country_name_and_adjective_resolution(country, code, graph_factory, sql_fallback):
    graph_factory.side_effect = ConnectionError("Synthetic graph unavailable")
    result = await country_tool.get_country_statistics_execute(country)
    assert result["country_code"] == code
    sql_fallback.assert_awaited_once_with(code)


@pytest.mark.asyncio
async def test_graph_success_does_not_call_sql(graph_factory, sql_fallback):
    graph = graph_factory.return_value
    graph.check_country_eligibility.return_value = {"is_eligible": True}
    graph.get_top_organizations.return_value = [{"name": "Synthetic graph organization"}]
    result = await country_tool.get_country_statistics_execute("Germany")
    assert result["success"] is True
    assert result["source"] == "neo4j_graph"
    assert result["metadata"] == {
        "sources_used": ["neo4j"],
        "search_type": "graph",
        "degraded": False,
    }
    graph.check_country_eligibility.assert_called_once_with("DE")
    sql_fallback.assert_not_awaited()


@pytest.mark.asyncio
async def test_graph_connection_failure_uses_current_sql_fallback(graph_factory, sql_fallback):
    graph_factory.side_effect = ConnectionError("Synthetic graph unavailable")
    result = await country_tool.get_country_statistics_execute("DE")
    assert result["success"] is True
    assert result["source"] == "sql_fallback"
    assert result["project_count"] == 50
    assert result["metadata"]["degraded"] is True
    assert result["metadata"]["sources_used"] == ["postgresql"]
    assert "temporarily unavailable" in result["metadata"]["limitation"]
    sql_fallback.assert_awaited_once_with("DE")


@pytest.mark.asyncio
async def test_graph_timeout_keeps_event_loop_responsive(monkeypatch, graph_factory, sql_fallback):
    entered = threading.Event()
    release = threading.Event()

    def slow_constructor():
        entered.set()
        release.wait(1)
        return MagicMock()

    graph_factory.side_effect = slow_constructor
    monkeypatch.setattr(country_tool, "NEO4J_TIMEOUT", 0.01)
    task = asyncio.create_task(country_tool.get_country_statistics_execute("Germany"))
    try:
        assert await asyncio.to_thread(entered.wait, 0.5)
        # The constructor is still blocked. The timeout/fallback and unrelated
        # coroutines must still run without waiting for that worker to finish.
        await asyncio.sleep(0.05)
        assert task.done()
        result = await task
        assert result["metadata"]["degradation_reason"] == "timeout"
        assert result["source"] == "sql_fallback"
        sql_fallback.assert_awaited_once_with("DE")
    finally:
        release.set()
        await task


@pytest.mark.asyncio
async def test_both_sources_fail_returns_error(graph_factory, sql_fallback):
    graph_factory.side_effect = ConnectionError("Synthetic graph unavailable")
    sql_fallback.return_value = None
    result = await country_tool.get_country_statistics_execute("Germany")
    assert result["success"] is False
    assert "both graph and SQL" in result["error"]
    assert result["metadata"]["sources_used"] == []


@pytest.mark.asyncio
async def test_unknown_country_has_helpful_message(graph_factory, sql_fallback):
    result = await country_tool.get_country_statistics_execute("Narnia")
    assert result["success"] is False
    assert "could not identify" in result["message"].lower()
    assert "ISO codes" in result["message"]
    graph_factory.assert_not_called()
    sql_fallback.assert_not_awaited()


@pytest.mark.asyncio
async def test_sql_timeout_does_not_block_loop(monkeypatch):
    release = threading.Event()

    def slow_sql(code):
        release.wait(1)
        return {"project_count": 1}

    monkeypatch.setattr(country_tool, "_fetch_country_stats_sql", slow_sql)
    monkeypatch.setattr(country_tool, "SQL_TIMEOUT", 0.01)
    try:
        assert await country_tool._get_country_stats_sql("DE") is None
    finally:
        release.set()


@pytest.mark.asyncio
async def test_sql_fallback_maps_rows_and_closes_resources(monkeypatch):
    import psycopg2

    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.fetchall.return_value = [
        {
            "name": "Synthetic SQL organization",
            "project_count": 3,
            "total_funding": 500,
            "coordinations": 1,
        }
    ]
    cursor.fetchone.return_value = {
        "project_count": 3,
        "total_funding": 500,
        "coordinations": 1,
        "org_count": 1,
    }
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr(psycopg2, "connect", connect)
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy:dummy@invalid/dummy")
    result = await country_tool._get_country_stats_sql("DE")
    assert result["project_count"] == 3
    assert result["top_organizations"][0]["total_funding"] == 500
    assert result["eligibility"]["is_eligible"] is True
    assert all(call.args[1] == ["DE"] for call in cursor.execute.call_args_list)
    assert connect.call_args.kwargs["connect_timeout"] == 10
    assert "statement_timeout=10000" in connect.call_args.kwargs["options"]
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


@pytest.mark.asyncio
async def test_sql_failure_closes_resources(monkeypatch):
    import psycopg2

    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.execute.side_effect = RuntimeError("Synthetic query failure")
    monkeypatch.setattr(psycopg2, "connect", MagicMock(return_value=connection))
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy:dummy@invalid/dummy")
    assert await country_tool._get_country_stats_sql("DE") is None
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


# ============================================================================
# INTEGRATION TESTS - Test with live API (if available)
# ============================================================================


# ============================================================================
# SCENARIO QUALITY TEST - Full end-to-end scenario
# ============================================================================


# ============================================================================
# Test SQL Fallback with Database
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
