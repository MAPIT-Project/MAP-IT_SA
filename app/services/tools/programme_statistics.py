"""Programme statistics with explicit source, cohort and year semantics."""

import asyncio
import logging
from typing import Any

from .funding_cohorts import programme_code, year_bounds
from .published_programme_statistics import published_statistics

logger = logging.getLogger(__name__)

# Map programme names to cluster codes (Neo4j uses CLUSTER-X format)
CLUSTER_MAP: dict[str, str] = {
    "cluster 5": "CLUSTER-5",
    "cluster-5": "CLUSTER-5",
    "cl5": "CLUSTER-5",
    "climate": "CLUSTER-5",
    "energy": "CLUSTER-5",
    "mobility": "CLUSTER-5",
    "cluster 4": "CLUSTER-4",
    "cluster-4": "CLUSTER-4",
    "cl4": "CLUSTER-4",
    "digital": "CLUSTER-4",
    "industry": "CLUSTER-4",
    "space": "CLUSTER-4",
    "cluster 6": "CLUSTER-6",
    "cluster-6": "CLUSTER-6",
    "cl6": "CLUSTER-6",
    "food": "CLUSTER-6",
    "bioeconomy": "CLUSTER-6",
    "agriculture": "CLUSTER-6",
    "cluster 1": "CLUSTER-1",
    "cluster-1": "CLUSTER-1",
    "cl1": "CLUSTER-1",
    "health": "CLUSTER-1",
    "cluster 2": "CLUSTER-2",
    "cluster-2": "CLUSTER-2",
    "cl2": "CLUSTER-2",
    "culture": "CLUSTER-2",
    "creativity": "CLUSTER-2",
    "cluster 3": "CLUSTER-3",
    "cluster-3": "CLUSTER-3",
    "cl3": "CLUSTER-3",
    "security": "CLUSTER-3",
}


async def get_programme_statistics_execute(
    programme: str,
    metric: str | None = None,
    year: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict[str, Any]:
    """Return cited call-year statistics or clearly scoped local project aggregates."""
    try:
        first, last = year_bounds(year, year_from, year_to)
        if metric not in {None, "success_rate", "avg_funding", "participation"}:
            raise ValueError(f"Unsupported statistics metric: {metric!r}")
        name = programme.lower().strip()
        cluster = next((code for key, code in CLUSTER_MAP.items() if key in name), None)
        if cluster is None:
            code = programme_code(programme)
            published = published_statistics(code, first, last)
            if published["available_years"]:
                return {
                    "success": True,
                    "programme": programme,
                    "programme_code": code,
                    "statistics": published,
                    "source": published["source"],
                }
            from .budget_benchmark import BudgetBenchmarkTool

            benchmark = await asyncio.to_thread(
                BudgetBenchmarkTool().get_benchmark,
                programme=code,
                year_from=first,
                year_to=last,
            )
            return {
                "success": True,
                "programme": programme,
                "programme_code": code,
                "statistics": {"success_rates": None, "annual": []},
                "budget_details": benchmark,
                "source": "local_funded_projects",
                "limitations": [
                    "No cited submitted-application counts for this scheme; success rate unavailable.",
                    "Local budget sample uses project start year, not call or award year.",
                    "For ERC Advanced Grant or EIC Accelerator select that specific scheme.",
                ],
            }
        if first is not None or last is not None:
            from .budget_benchmark import BudgetBenchmarkTool

            benchmark = await asyncio.to_thread(
                BudgetBenchmarkTool().get_benchmark,
                cluster=cluster,
                year_from=first,
                year_to=last,
            )
            return {
                "success": True,
                "programme": programme,
                "cluster_code": cluster,
                "statistics": benchmark["statistics"],
                "budget_details": benchmark,
                "source": benchmark["metadata"]["statistics_source"],
                "success_rates": None,
                "year_basis": "project_start_year",
            }
        from ..data_intelligence.graph_service import GraphSearchService

        graph = GraphSearchService()
        result = await asyncio.to_thread(graph.get_cluster_statistics, cluster)
        budget = await asyncio.to_thread(graph.get_budget_statistics, cluster)
        return {
            "success": True,
            "programme": programme,
            "cluster_code": cluster,
            "statistics": result,
            "budget_details": budget,
            "source": "neo4j_graph",
            "success_rates": None,
            "limitations": [
                "Local funded projects, all start years; not application success rates."
            ],
        }
    except Exception as exc:
        logger.warning("Programme statistics unavailable (%s)", type(exc).__name__)
        return {"success": False, "error": str(exc)}


async def compare_programmes_execute(
    programme_a: str,
    programme_b: str,
    year: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    metrics: list[str] | None = None,
) -> dict[str, Any]:
    """Use exactly the same source and filters as individual programme queries."""
    if metrics and set(metrics) - {"success_rate", "avg_funding", "participation"}:
        return {"success": False, "error": "Unsupported comparison metric"}
    results = await asyncio.gather(
        *(
            get_programme_statistics_execute(
                programme,
                year=year,
                year_from=year_from,
                year_to=year_to,
            )
            for programme in (programme_a, programme_b)
        )
    )
    return {
        "success": all(result.get("success", False) for result in results),
        "comparison": dict(zip((programme_a, programme_b), results, strict=True)),
        "requested_metrics": metrics,
        "limitations": [
            "EIC full-proposal selections and ERC submitted-proposal selections use different stages.",
            "EIC announced support includes equity; ERC announced support is grant funding.",
        ],
    }
