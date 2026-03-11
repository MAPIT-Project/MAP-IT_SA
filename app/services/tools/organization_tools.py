"""
Organization Tools for Horizon Europe.

Provides standalone execute functions for organization-related tool operations:
- get_organization_stats_execute: Aggregate statistics for an organization
  (project count, coordinator count, total funding) via Neo4j graph with SQL fallback.
- find_organization_projects_execute: Find all projects an organization participated in
  using Neo4j graph database with parallel count and project queries.
- get_collaboration_network_execute: Get collaboration network showing which organizations
  partner together using Neo4j graph database.

All functions use lazy imports to avoid circular dependencies and neo4j package shadowing.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def get_organization_stats_execute(org_name: str) -> dict:
    """
    Get aggregate statistics for an organization.

    Tries Neo4j graph service first (get_organization_profile), then falls back
    to SQL using CordisProjectRepository with expanded org name search terms.

    Args:
        org_name: Organization name to look up.

    Returns:
        Dict with name, country, project_count, coordinator_count, total_funding,
        and source indicator ('neo4j_graph' or 'postgresql').
    """
    try:
        if not org_name:
            return {"error": "organization_name is required"}

        # Try graph service first (may not be available)
        try:
            from ..data_intelligence.graph_service import GraphSearchService

            graph = GraphSearchService()
            profile = await asyncio.to_thread(graph.get_organization_profile, org_name)
            if profile:
                return {
                    "name": profile.get("name"),
                    "short_name": profile.get("short_name"),
                    "country": profile.get("country"),
                    "entity_type": profile.get("entity_type"),
                    "entity_type_name": profile.get("entity_type_name"),
                    "project_count": profile.get("project_count", 0),
                    "coordinator_count": profile.get("coordinations", 0),
                    "total_funding": profile.get("total_funding", 0),
                    "active_clusters": profile.get("active_clusters", []),
                    "recent_projects": profile.get("recent_projects", []),
                    "source": "neo4j_graph",
                }
        except Exception as graph_err:
            logger.warning(
                f"Graph service unavailable for org stats, using SQL fallback: {graph_err}"
            )

        # Fallback: use SQL count with expanded search terms
        from ..data.cordis_repository import CordisProjectRepository
        from ..data_intelligence.org_name_utils import (
            expand_org_search_terms as _expand_org_search_terms,
        )

        logger.info(f"\U0001f4ca SQL fallback for org stats: {org_name}")
        repo = CordisProjectRepository()
        conn = None
        try:
            conn = repo.db_pool.getconn()
            cursor = conn.cursor()

            search_terms = _expand_org_search_terms(org_name)
            row = None
            for term in search_terms:
                cursor.execute(
                    """
                    SELECT
                        name,
                        country,
                        COUNT(DISTINCT "projectID") as project_count,
                        COUNT(DISTINCT CASE WHEN role = 'coordinator' THEN "projectID" END) as coordinator_count,
                        COALESCE(SUM("ecContribution"), 0) as total_funding
                    FROM organizations
                    WHERE name ILIKE %s
                    GROUP BY name, country
                    ORDER BY project_count DESC
                    LIMIT 1
                    """,
                    (f"%{term}%",),
                )
                row = cursor.fetchone()
                if row:
                    break
            cursor.close()

            if row:
                logger.info(
                    f"\u2705 SQL org stats found: {row[0]} - {row[2]} projects, {row[3]} coordinations"
                )
                return {
                    "name": row[0],
                    "country": row[1],
                    "project_count": row[2],
                    "coordinator_count": row[3],
                    "total_funding": float(row[4]) if row[4] else 0,
                    "source": "postgresql",
                }

            logger.warning(f"\u274c Organization not found in SQL: {org_name}")
            return {
                "error": f"Organization not found: {org_name}",
                "suggestion": "Try using the full official name of the organization",
            }
        finally:
            if conn:
                repo.db_pool.putconn(conn)

    except Exception as e:
        logger.error(f"Get organization stats error: {e}")
        return {"error": str(e)}


async def find_organization_projects_execute(org_name: str, role: str | None = None) -> dict:
    """
    Find all projects an organization participated in.

    Uses Neo4j GraphSearchService with parallel calls to get total count,
    coordinator count, and project results simultaneously.

    Args:
        org_name: Organization name to search for.
        role: Optional role filter (e.g. 'coordinator', 'participant').

    Returns:
        Dict with organization, role_filter, projects list, count,
        total_project_count, coordinator_count, and optional note.
    """
    try:
        from ..data_intelligence.graph_service import GraphSearchService

        graph = GraphSearchService()

        if not org_name:
            return {"error": "organization_name is required", "projects": []}

        # Get true total count (no limit) and coordinator count in parallel
        total_count, coordinator_count, results = await asyncio.gather(
            asyncio.to_thread(
                graph.get_organization_project_count, organization_name=org_name, role=None
            ),
            asyncio.to_thread(
                graph.get_organization_project_count,
                organization_name=org_name,
                role="coordinator",
            ),
            asyncio.to_thread(
                graph.find_projects_by_organization,
                organization_name=org_name,
                role=role,
                limit=100,
            ),
        )

        return {
            "organization": org_name,
            "role_filter": role,
            "projects": results,
            "count": len(results),
            "total_project_count": total_count,
            "coordinator_count": coordinator_count,
            "note": f"Showing {len(results)} of {total_count} total projects"
            if len(results) < total_count
            else None,
        }
    except Exception as e:
        logger.error(f"Organization projects search error: {e}")
        return {"error": str(e), "projects": []}


async def get_collaboration_network_execute(org_name: str) -> dict:
    """
    Get collaboration network for an organization.

    Uses Neo4j GraphSearchService.get_organization_collaboration_network
    via asyncio.to_thread delegation.

    Args:
        org_name: Organization name to look up the collaboration network for.

    Returns:
        Dict with collaboration network data (partners, shared projects, etc.).
    """
    try:
        from ..data_intelligence.graph_service import GraphSearchService

        graph = GraphSearchService()

        if not org_name:
            return {"error": "organization_name is required", "partners": []}

        result = await asyncio.to_thread(
            graph.get_organization_collaboration_network,
            organization_name=org_name,
            depth=1,
            limit=30,
        )

        return result
    except Exception as e:
        logger.error(f"Collaboration network error: {e}")
        return {"error": str(e), "partners": []}
