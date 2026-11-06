"""Evaluation planning and stop behavior using mocked source rows, no live inference."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from scripts.evaluate_tools import evaluate, provider_failed, selected_contracts


@pytest.mark.asyncio
async def test_plan_has_complete_inventory_without_constructing_agent(monkeypatch, tmp_path):
    import scripts.evaluate_tools as runner

    facts = {
        "catalog_counts": [{"projects": 1}],
        "reference_project": [{"project_id": "101137586"}],
    }
    monkeypatch.setattr(runner, "discover_ground_truth", lambda reader: facts)
    construct = Mock(side_effect=AssertionError("Planning cannot start an agent"))
    monkeypatch.setattr(runner, "make_agent", construct)
    args = SimpleNamespace(
        mode="plan",
        model="synthetic",
        effort="high",
        container="unused-test-container",
        case=None,
        scenario=None,
        output=tmp_path / "unused.json",
    )
    result = await evaluate(args)
    assert len(result["cases"]) == 52
    assert len(result["scenarios"]) == 10
    assert result["usage"] == {"attempts": 0}
    construct.assert_not_called()


@pytest.mark.parametrize(
    "error,stops",
    [
        ("Codex CLI exited with status 1", True),
        ("Codex CLI timed out", True),
        ("Agent execution limit reached", False),
        (None, False),
    ],
)
def test_provider_failure_stops_subsequent_scenarios(error, stops):
    assert provider_failed(SimpleNamespace(error=error)) is stops


def test_questions_preflight_only_the_tools_required_by_selected_scenarios():
    cases = [SimpleNamespace(id=name, tool=name) for name in ("lookup", "search", "unrelated")]
    scenarios = [SimpleNamespace(expected_tools=("lookup", "search"))]
    selected = selected_contracts(cases, scenarios, SimpleNamespace(mode="questions", case=None))
    assert [case.id for case in selected] == ["lookup", "search"]
    assert (
        selected_contracts(cases, scenarios, SimpleNamespace(mode="contracts", case=None)) == cases
    )


def test_explicit_contract_selection_is_not_silently_expanded():
    cases = [SimpleNamespace(id=name, tool=name) for name in ("lookup", "search")]
    assert selected_contracts(cases, [], SimpleNamespace(mode="questions", case=["search"])) == [
        cases[1]
    ]


@pytest.mark.parametrize(
    "diagnostic,category",
    [
        (b"Usage limit reached: private token", "usage_limit"),
        (b"error sending request: private request data", "connectivity"),
        (b"invalid_json_schema: private prompt", "structured_output"),
        (b"arbitrary private SDK payload", "unclassified"),
    ],
)
def test_cli_failure_categories_never_expose_diagnostics(diagnostic, category):
    from app.services.ai.codex import CodexTextModel

    assert CodexTextModel._failure_category(b"", diagnostic) == category
