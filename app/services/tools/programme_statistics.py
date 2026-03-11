"""
Programme Statistics Tool for Horizon Europe.

Provides programme and cluster statistics from the Neo4j graph database,
including success rates, funding amounts, and budget details for Horizon Europe
pillars and clusters.

Handles EIC, ERC, MSCA with hard-coded official EC statistics, and Pillar 2
clusters via Neo4j graph queries.
"""

import asyncio
import logging
from typing import Any

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

# Extended cluster map for compare_programmes (includes action types and pillar programmes)
COMPARE_CLUSTER_MAP: dict[str, str] = {
    **CLUSTER_MAP,
    "eic": "EIC",
    "eic accelerator": "EIC",
    "erc": "ERC",
    "msca": "MSCA",
    "marie curie": "MSCA",
    "ria": "RIA",
    "ia": "IA",
    "csa": "CSA",
}


async def get_programme_statistics_execute(programme: str) -> dict[str, Any]:
    """
    Get programme/cluster statistics from graph DB.

    Handles EIC, ERC, MSCA with hard-coded official EC statistics,
    and Pillar 2 clusters via Neo4j graph queries.

    Args:
        programme: Programme or cluster name (e.g. 'EIC', 'Cluster 5', 'Health').

    Returns:
        Dictionary with programme statistics, funding details, and source info.
    """
    try:
        from ..data_intelligence.graph_service import GraphSearchService

        graph = GraphSearchService()

        programme_lower = programme.lower()

        # Handle EIC/ERC/MSCA separately - these are pillars, not clusters
        # Return known statistics from official EC sources
        if "eic" in programme_lower or "accelerator" in programme_lower:
            return {
                "programme": "EIC Accelerator",
                "programme_type": "Pillar 3 - Innovative Europe",
                "statistics": {
                    "description": "EIC Accelerator supports high-risk, high-impact SMEs and startups with breakthrough innovations",
                    "success_rates": {
                        "overall": "2-5%",
                        "short_proposal_to_full": "~25-30%",
                        "full_proposal_to_interview": "~20-25%",
                        "interview_to_funding": "~50-60%",
                        "note": "Success rates vary by cut-off date and are highly competitive",
                    },
                    "funding": {
                        "grant_only": "Up to \u20ac2.5 million",
                        "blended_finance": "Up to \u20ac2.5M grant + up to \u20ac15M equity",
                        "equity_only": "Up to \u20ac15 million",
                    },
                    "eligibility": "Single SMEs (including startups) from EU/Associated Countries",
                    "trl_range": "TRL 5-9 (close to market)",
                    "evaluation_criteria": [
                        "Excellence (Breakthrough innovation, Technology readiness)",
                        "Impact (Market potential, Scalability, Team capability)",
                        "Implementation (Business plan, Milestones, Resources)",
                        "Level of risk and need for EU support",
                    ],
                },
                "source": "official_ec_data",
            }

        if "erc" in programme_lower:
            return {
                "programme": "European Research Council (ERC)",
                "programme_type": "Pillar 1 - Excellent Science",
                "statistics": {
                    "description": "ERC funds frontier research by individual investigators",
                    "success_rates": {
                        "starting_grant": "~10-15%",
                        "consolidator_grant": "~12-15%",
                        "advanced_grant": "~10-12%",
                        "synergy_grant": "~8-10%",
                        "proof_of_concept": "~35-40%",
                    },
                    "funding": {
                        "starting_grant": "Up to \u20ac1.5M for 5 years",
                        "consolidator_grant": "Up to \u20ac2M for 5 years",
                        "advanced_grant": "Up to \u20ac2.5M for 5 years",
                        "synergy_grant": "Up to \u20ac10M for 6 years (2-4 PIs)",
                    },
                    "eligibility": "Researchers at any career stage hosted by EU/AC institutions",
                    "evaluation_criteria": [
                        "Excellence of the PI (track record, scientific leadership)",
                        "Excellence of the research project (groundbreaking nature, methodology)",
                    ],
                },
                "source": "official_ec_data",
            }

        if "msca" in programme_lower or "marie" in programme_lower or "curie" in programme_lower:
            return {
                "programme": "Marie Sk\u0142odowska-Curie Actions (MSCA)",
                "programme_type": "Pillar 1 - Excellent Science",
                "statistics": {
                    "description": "MSCA supports researcher mobility, training and career development",
                    "success_rates": {
                        "postdoctoral_fellowships": "~12-15%",
                        "doctoral_networks": "~8-12%",
                        "staff_exchanges": "~25-30%",
                        "cofund": "~20-25%",
                        "citizens": "Varied (outreach programme)",
                    },
                    "funding": {
                        "postdoctoral_fellowships": "Living allowance + mobility + research costs",
                        "doctoral_networks": "Up to \u20ac360,000/researcher",
                    },
                    "eligibility": "Researchers at all career stages, with mobility requirements",
                    "evaluation_criteria": [
                        "Excellence (Quality of research/training)",
                        "Impact (Career development, Knowledge transfer)",
                        "Implementation (Work plan, Management)",
                    ],
                },
                "source": "official_ec_data",
            }

        # Try to find a matching cluster code for Pillar 2 clusters
        cluster_code = None
        for key, code in CLUSTER_MAP.items():
            if key in programme_lower:
                cluster_code = code
                break

        # Get cluster statistics from Neo4j
        result = await asyncio.to_thread(graph.get_cluster_statistics, cluster_code)

        if result:
            # Also get budget statistics for more detail
            budget_stats = await asyncio.to_thread(graph.get_budget_statistics, cluster_code)

            # Combine results with clear context to avoid budget confusion
            return {
                "programme": programme,
                "cluster_code": cluster_code,
                "statistics": result,
                "budget_details": budget_stats,
                "source": "neo4j_graph",
                # IMPORTANT: Add programme budget context to avoid LLM confusion
                "programme_context": {
                    "note": "IMPORTANT: The 'total_funding' in statistics is the cumulative amount awarded to PROJECTS in this cluster/area, NOT the overall Horizon Europe budget.",
                    "horizon_europe_total_budget": "\u20ac95.5 billion (2021-2027)",
                    "cluster_funding_note": f"This cluster ({cluster_code}) represents a portion of the overall programme budget.",
                },
            }

        return {
            "message": f"No statistics found for {programme}. Try specific cluster names (e.g., 'Cluster 5 - Climate', 'Health') or programmes (EIC, ERC, MSCA).",
            # Include correct programme budgets to prevent hallucination
            "programme_budget_reference": {
                "Horizon Europe": "\u20ac95.5 billion (2021-2027)",
                "Erasmus+": "\u20ac26.2 billion (2021-2027)",
                "Creative Europe": "\u20ac2.44 billion (2021-2027)",
                "note": "Use these figures when discussing overall programme budgets.",
            },
        }
    except Exception as e:
        logger.error(f"Programme stats error: {e}")
        return {"error": str(e)}


async def compare_programmes_execute(programme_a: str, programme_b: str) -> dict[str, Any]:
    """
    Compare two programmes/clusters side-by-side.

    Uses Neo4j graph database to fetch cluster statistics for both programmes
    and returns a comparison structure.

    Args:
        programme_a: First programme or cluster name.
        programme_b: Second programme or cluster name.

    Returns:
        Dictionary with comparison data for both programmes.
    """
    try:
        from ..data_intelligence.graph_service import GraphSearchService

        graph = GraphSearchService()

        def get_cluster_code(prog: str) -> str | None:
            prog_lower = prog.lower()
            for key, code in COMPARE_CLUSTER_MAP.items():
                if key in prog_lower:
                    return code
            return None

        code_a = get_cluster_code(programme_a)
        code_b = get_cluster_code(programme_b)

        # Get statistics for both
        stats_a = await asyncio.to_thread(graph.get_cluster_statistics, code_a)
        stats_b = await asyncio.to_thread(graph.get_cluster_statistics, code_b)

        return {
            "comparison": {
                programme_a: {
                    "cluster_code": code_a,
                    "statistics": stats_a[0] if stats_a else None,
                },
                programme_b: {
                    "cluster_code": code_b,
                    "statistics": stats_b[0] if stats_b else None,
                },
            },
            "source": "neo4j_graph",
        }
    except Exception as e:
        logger.error(f"Compare programmes error: {e}")
        return {"error": str(e)}
