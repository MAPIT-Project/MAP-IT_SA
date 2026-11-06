"""Regressions exposed by source-backed contracts, with offline source boundaries."""

from unittest.mock import MagicMock

import pytest

from app.services.tools.call_history import CallHistoryTool
from app.services.tools.proposal_quality_scorer import quick_quality_check_execute


@pytest.mark.parametrize("strict", [True, False])
def test_sql_only_call_history_preserves_keyword_matching_mode(strict):
    tool = CallHistoryTool.__new__(CallHistoryTool)
    tool._graph_service = None
    connection = MagicMock()
    tool._get_connection = MagicMock(return_value=connection)
    tool._get_calls_history_sql = MagicMock(return_value=[])
    tool._get_timeline_aggregates_sql = MagicMock(
        return_value={
            2024: {"projects_funded": 2, "total_funding": 1200000, "calls": 0},
        }
    )
    tool._get_funded_projects_sql = MagicMock(return_value=[])

    result = tool.analyze_history(
        keywords="hydrogen",
        year_from=2024,
        year_to=2024,
        strict_match=strict,
        limit=7,
        include_projects=True,
    )

    assert result["success"] is True
    assert result["metadata"]["search_type"] == "sql_only"
    assert result["projects_funded"] == 2
    assert result["total_funding_allocated"] == 1200000
    tool._get_calls_history_sql.assert_called_once_with(
        None,
        None,
        "hydrogen",
        2024,
        2024,
        None,
        7,
        strict_match=strict,
    )
    tool._get_timeline_aggregates_sql.assert_called_once_with(
        None,
        None,
        "hydrogen",
        2024,
        2024,
        strict_match=strict,
    )
    tool._get_funded_projects_sql.assert_called_once_with(
        None,
        None,
        "hydrogen",
        2024,
        2024,
        7,
        strict_match=strict,
    )
    connection.close.assert_called_once()


def test_strict_call_history_matches_short_keywords_at_word_boundaries():
    tool = CallHistoryTool.__new__(CallHistoryTool)
    strict_where, strict_params = tool._build_where_clause(
        None,
        None,
        "AI",
        None,
        None,
        strict_match=True,
    )
    broad_where, broad_params = tool._build_where_clause(
        None,
        None,
        "AI",
        None,
        None,
        strict_match=False,
    )
    assert "title ~* %s" in strict_where
    assert strict_params == [r"\mAI\M", r"\mAI\M"]
    assert "title ILIKE %s" in broad_where
    assert broad_params == ["%AI%", "%AI%"]


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["", " ", "\n\t\r", "\u2003\u00a0"])
async def test_empty_draft_never_receives_a_positive_quality_score(text):
    result = await quick_quality_check_execute(text=text, context="objectives")
    assert result["success"] is True
    assert result["quality_estimate"] == 0.0
    assert result["quality_level"] == "weak"
    assert result["indicators"]["word_count"] == 0
    assert result["suggestions"]


@pytest.mark.asyncio
async def test_nonempty_draft_retains_the_existing_quick_quality_rubric():
    result = await quick_quality_check_execute("Objective: reach 95% accuracy. Test it.")
    assert result["quality_estimate"] == 2.8
    assert result["indicators"]["has_structure"] is True
    assert result["indicators"]["has_quantification"] is True
