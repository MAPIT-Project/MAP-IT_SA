"""Call retrieval regressions without embeddings, external HTTP or real databases."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.local_call_search_service import LocalCallSearchService
from app.services.tools.multi_programme_search import MultiProgrammeSearchTool
from tests.tool_scenarios.transport import ReadConnection


def test_structured_calls_remain_available_without_embedding_key():
    connection = MagicMock()
    connection.cursor.return_value.fetchone.side_effect = [(True,), (2758,), (0,)]
    with (
        patch("psycopg2.connect", return_value=connection),
        patch(
            "app.services.local_call_search_service.VectorSearchService",
            side_effect=ValueError("No embedding key"),
        ),
        patch.dict(
            "sys.modules",
            {
                "app.services.data_intelligence.graph_service": SimpleNamespace(
                    GraphSearchService=MagicMock(side_effect=RuntimeError("No graph"))
                )
            },
        ),
    ):
        service = LocalCallSearchService()
    assert service._available is True
    assert service._structured_available is True
    assert service.vector_service is None


def test_open_multi_programme_query_checks_actual_dates():
    service = MultiProgrammeSearchTool.__new__(MultiProgrammeSearchTool)
    query, parameters = service._build_programme_query(
        "horizon_europe", "", "open", None, None, 10, False
    )
    assert "deadline >= CURRENT_DATE" in query
    assert "opening_date IS NULL OR opening_date <= CURRENT_DATE" in query
    assert "open" in parameters
    assert "WHEN opening_date > CURRENT_DATE THEN 'upcoming'" in query
    assert "horizon_europe" in parameters


def test_psql_bridge_restores_native_dates():
    from datetime import date

    cursor = ReadConnection(lambda query: [{"deadline": "2026-12-17"}]).cursor()
    cursor.execute("SELECT deadline FROM funding_calls")
    assert cursor.fetchone() == (date(2026, 12, 17),)


@pytest.mark.asyncio
async def test_missing_compliance_service_never_claims_compliant():
    from app.services.tools.proposal_tools import ProposalToolExecutor

    executor = ProposalToolExecutor()
    with patch.object(executor, "_get_service", return_value=None):
        result = await executor.execute_tool(
            "check_compliance", {"section_id": "excellence.objectives"}
        )
    assert result["compliant"] is None
    assert result["success"] is False
    assert result["checks_passed"] == 0
    assert result["error"]
