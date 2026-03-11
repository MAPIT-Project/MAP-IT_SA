"""
Project Discovery Tools for Horizon Europe.

Provides standalone execute functions for project discovery operations:
- find_similar_projects_execute: Find projects similar to a given project by topic,
  consortium, or cluster using Neo4j graph database.
- find_semantically_similar_execute: Find projects semantically similar using AI
  vector embeddings (768-dim, Google text-embedding-004) via LocalProjectSearchService.
- search_by_cluster_execute: Find projects in a specific Horizon Europe research cluster
  (e.g., Climate, Health, Digital) using LocalProjectSearchService relationship search.

All functions use lazy imports to avoid circular dependencies and neo4j package shadowing.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def find_similar_projects_execute(project_id: str, similarity_type: str = "topic") -> dict:
    """
    Find projects similar to a given project.

    Uses Neo4j GraphSearchService.find_similar_projects via asyncio.to_thread.

    Args:
        project_id: The project ID or acronym to find similar projects for.
        similarity_type: Type of similarity to search by ('topic', 'consortium', 'cluster').

    Returns:
        Dict with reference_project, similarity_type, similar_projects list, and count.
    """
    try:
        from ..data_intelligence.graph_service import GraphSearchService

        graph = GraphSearchService()

        if not project_id:
            return {"error": "project_id is required", "projects": []}

        results = await asyncio.to_thread(
            graph.find_similar_projects,
            project_id=project_id,
            similarity_type=similarity_type,
            limit=10,
        )

        return {
            "reference_project": project_id,
            "similarity_type": similarity_type,
            "similar_projects": results,
            "count": len(results),
        }
    except Exception as e:
        logger.error(f"Similar projects search error: {e}")
        return {"error": str(e), "projects": []}


async def find_semantically_similar_execute(project_id: str, limit: int = 10) -> dict:
    """
    Find semantically similar projects using vector embeddings.

    Uses LocalProjectSearchService.find_similar_projects_by_embedding for
    semantic similarity search based on project objectives and descriptions.

    Args:
        project_id: The project ID or acronym to find semantically similar projects for.
        limit: Maximum number of similar projects to return (default: 10).

    Returns:
        Dict with similar projects found via embedding-based similarity search.
    """
    try:
        from ..local_project_search_service import LocalProjectSearchService

        if not project_id:
            return {"error": "project_id is required", "projects": []}

        service = LocalProjectSearchService()
        result = await service.find_similar_projects_by_embedding(
            project_id=project_id, limit=limit
        )

        return result
    except Exception as e:
        logger.error(f"Semantic similarity search error: {e}")
        return {"error": str(e), "projects": []}


async def search_by_cluster_execute(cluster: str) -> dict:
    """
    Search projects in a specific Horizon Europe research cluster.

    Uses LocalProjectSearchService.search_projects_by_relationship to find
    projects belonging to a given cluster. The cluster parameter should already
    be extracted/normalized by the caller (e.g., _extract_cluster_param in
    tool_executors.py).

    Args:
        cluster: Cluster identifier (e.g., 'CLUSTER-1', 'CL5', 'Health', 'Digital').

    Returns:
        Dict with projects found in the specified cluster.
    """
    try:
        from ..local_project_search_service import LocalProjectSearchService

        service = LocalProjectSearchService()

        if not cluster:
            return {"error": "cluster parameter is required", "projects": []}

        result = await service.search_projects_by_relationship(
            relationship_type="cluster", entity_value=cluster, limit=15
        )

        return result
    except Exception as e:
        logger.error(f"Cluster search error: {e}")
        return {"error": str(e), "projects": []}
