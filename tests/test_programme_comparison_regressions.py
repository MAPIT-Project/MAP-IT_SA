"""Historical comparisons: real arithmetic and SQL, mocked external boundaries."""

import json
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.agents.tool_executors import ToolExecutorsMixin
from app.services.agents.tool_registry import ToolRegistryMixin
from app.services.tools.budget_benchmark import BudgetBenchmarkTool
from app.services.tools.funding_cohorts import programme_predicate, year_bounds
from app.services.tools.programme_statistics import (
    compare_programmes_execute,
    get_programme_statistics_execute,
)


def benchmark_tool():
    tool = BudgetBenchmarkTool.__new__(BudgetBenchmarkTool)
    tool._graph_service = MagicMock()
    tool._get_connection = MagicMock()
    cursor = tool._get_connection.return_value.cursor.return_value
    cursor.fetchone.return_value = {
        "project_count": 2,
        "total_funding": 5_000_000,
        "avg_budget": 2_500_000,
        "median_budget": 2_500_000,
        "min_budget": 2_000_000,
        "max_budget": 3_000_000,
        "avg_partners": 1,
        "median_partners": 1,
        "avg_per_partner": 2_500_000,
        "min_partners": 1,
        "max_partners": 1,
        "std_dev": 500_000,
    }
    cursor.fetchall.return_value = []
    return tool, cursor


@pytest.mark.parametrize(
    "programme,positive,negative",
    [
        ("ERC Advanced Grant", "ERC-2023-ADG", "ERC-2023-STG"),
        ("ERC Starting Grant", "ERC-2024-STG", "ERC-2024-ADG"),
        (
            "EIC Accelerator",
            "HORIZON-EIC-2024-ACCELERATOROPEN-01",
            "HORIZON-EIC-2024-PATHFINDEROPEN-01",
        ),
    ],
)
def test_scheme_matches_broad_cordis_rows_by_specific_call_topic(programme, positive, negative):
    sql, (_, pattern) = programme_predicate(programme)
    assert "p.topics ~* %s" in sql
    assert re.search(pattern, positive, re.I)
    assert not re.search(pattern, negative, re.I)


@pytest.mark.parametrize("action", ["RIA", "IA", "CSA"])
def test_existing_programme_action_names_still_filter_their_own_scheme(action):
    _, (pattern, _) = programme_predicate(action)
    assert re.search(pattern, f"HORIZON-{action}")
    if action == "IA":
        assert not re.search(pattern, "HORIZON-RIA")


@pytest.mark.parametrize("programme", ["EIC Accelerator", "ERC Advanced Grant"])
def test_filtered_benchmark_preserves_year_and_scheme_without_graph_fusion(programme):
    tool, cursor = benchmark_tool()
    result = tool.get_benchmark(programme=programme, year_from=2023, year_to=2025)
    assert result["statistics"]["total_eu_contribution"]["average"] == 2_500_000
    assert result["query_params"]["year_from"] == 2023
    assert result["query_params"]["year_to"] == 2025
    assert result["metadata"]["year_basis"] == "project_start_year"
    assert result["metadata"]["sources_used"] == ["sql"]
    tool._graph_service.get_budget_statistics.assert_not_called()
    for call in cursor.execute.call_args_list:
        sql, params = call.args
        assert 'EXTRACT(YEAR FROM p."startDate") >= %s' in sql
        assert 'EXTRACT(YEAR FROM p."startDate") <= %s' in sql
        assert 'fundingScheme" ~* %s' in sql
        assert params[-2:] == [2023, 2025]


def test_existing_eic_cluster_alias_becomes_a_programme_filter():
    tool, cursor = benchmark_tool()
    result = tool.get_benchmark(cluster="EIC", year=2024)
    assert result["query_params"]["programme"] == "EIC"
    assert cursor.execute.call_args_list[0].args[1][-2:] == [2024, 2024]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cluster": "unknown scheme"},
        {"programme": "ERC Mystery Grant"},
        {"year": 2024, "year_from": 2023},
        {"year_from": 2025, "year_to": 2023},
        {"cluster": "EIC", "programme": "ERC"},
        {"year": True},
    ],
)
def test_invalid_scope_fails_before_queries(kwargs):
    tool, _ = benchmark_tool()
    with pytest.raises(ValueError):
        tool.get_benchmark(**kwargs)
    tool._get_connection.assert_not_called()


def test_missing_source_does_not_substitute_hardcoded_budget():
    tool, _ = benchmark_tool()
    tool._get_connection.return_value = None
    result = tool.get_benchmark(programme="ERC Advanced Grant", year=2024)
    assert result["success"] is False
    assert result["statistics"] == {"projects_analyzed": 0}
    assert result["recommendations"] == {}
    assert "fallback_estimates" not in json.dumps(result)


def test_empty_cohort_is_distinct_from_source_failure_and_has_no_average():
    tool, cursor = benchmark_tool()
    cursor.fetchone.return_value = {"project_count": 0}
    result = tool.get_benchmark(programme="EIC Accelerator", year=2025)
    assert result["success"] is True
    assert result["statistics"] == {"projects_analyzed": 0}
    assert result["metadata"]["statistics_source"] == "postgresql"


@pytest.mark.asyncio
async def test_exact_three_year_comparison_has_annual_denominators_and_cited_estimates():
    # Official selection-announcement snapshots. No external model or database.
    result = await compare_programmes_execute(
        "EIC Accelerator",
        "ERC Advanced Grant",
        year_from=2023,
        year_to=2025,
    )
    assert result["success"] is True
    expected = {
        "EIC Accelerator": [
            (2758, 172, 1091_000_000),
            (2180, 139, 798_000_000),
            (1882, 101, 697_000_000),
        ],
        "ERC Advanced Grant": [
            (1829, 255, 652_000_000),
            (2534, 281, 721_000_000),
            (3329, 319, 838_000_000),
        ],
    }
    for programme, counts in expected.items():
        stats = result["comparison"][programme]["statistics"]
        assert stats["year_basis"] == "call_or_cutoff_year"
        assert [row["year"] for row in stats["annual"]] == [2023, 2024, 2025]
        for row, (submitted, selected, amount) in zip(stats["annual"], counts, strict=True):
            assert row["submitted_proposals"] == submitted
            assert row["selected_proposals"] == selected
            assert row["selection_rate_percent"] == pytest.approx(
                100 * selected / submitted, abs=0.0001
            )
            assert row["mean_announced_support_eur_approx"] == pytest.approx(
                amount / selected, abs=0.01
            )
            assert all(url.startswith("https://") for url in row["sources"])
        period = stats["period"]
        assert period["selection_rate_percent"] == pytest.approx(
            100 * sum(row[1] for row in counts) / sum(row[0] for row in counts),
            abs=0.0001,
        )
        assert "rounded published totals" in " ".join(stats["limitations"])
    assert "equity" in result["comparison"]["EIC Accelerator"]["statistics"]["funding_basis"]


@pytest.mark.asyncio
async def test_missing_reference_year_is_explicit_and_not_replaced_by_all_years():
    result = await get_programme_statistics_execute(
        "ERC Advanced Grant", year_from=2024, year_to=2026
    )
    assert result["statistics"]["missing_years"] == [2026]
    assert result["statistics"]["period"] is None
    assert [r["year"] for r in result["statistics"]["annual"]] == [2024, 2025]


@pytest.mark.asyncio
async def test_broad_erc_has_no_invented_advanced_grant_rate():
    with (
        patch.object(BudgetBenchmarkTool, "__init__", return_value=None),
        patch.object(
            BudgetBenchmarkTool,
            "get_benchmark",
            return_value={"statistics": {"projects_analyzed": 0}},
        ),
    ):
        result = await get_programme_statistics_execute("ERC", year=2024)
    assert result["statistics"]["success_rates"] is None
    assert result["source"] != "official_ec_data"


@pytest.mark.asyncio
async def test_dispatchers_forward_schema_fields():
    owner = ToolExecutorsMixin()
    params = {
        "programme": "ERC Advanced Grant",
        "year_from": 2023,
        "year_to": 2025,
        "metric": "avg_funding",
    }
    with patch(
        "app.services.tools.programme_statistics.get_programme_statistics_execute",
        new_callable=AsyncMock,
    ) as execute:
        await owner._tool_get_programme_stats(params)
        assert execute.call_args.kwargs == {**params, "year": None}
    with (
        patch.object(BudgetBenchmarkTool, "__init__", return_value=None),
        patch.object(
            BudgetBenchmarkTool,
            "get_benchmark",
            return_value={},
        ) as execute,
    ):
        await owner._tool_get_budget_benchmark(params)
        assert execute.call_args.kwargs["programme"] == params["programme"]
        assert execute.call_args.kwargs["year_from"] == 2023
        assert execute.call_args.kwargs["year_to"] == 2025


def test_registry_exposes_year_ranges_for_both_statistics_entry_points():
    owner = ToolRegistryMixin()
    owner.tools = {}
    owner.register_tool = lambda tool: owner.tools.__setitem__(tool.name, tool)
    owner._init_tools()
    for name in ("get_programme_statistics", "compare_programmes", "get_budget_benchmark"):
        assert {"year_from", "year_to"} <= owner.tools[name].parameters.keys()
    assert "programme" in owner.tools["get_budget_benchmark"].parameters
    assert year_bounds(2024) == (2024, 2024)
