"""
Project Search Executor for CORDIS projects.

Provides local project search functionality using multi-source search
(PostgreSQL + Neo4j + Vector embeddings). Supports filtering by country,
programme, and sorting. Includes auto-partner-fetch logic when the user
query mentions partners/consortium and the result limit is small.

Extracted from the inline _tool_search_projects method in tool_executors.py.
"""

import logging

logger = logging.getLogger(__name__)


async def search_projects_execute(
    keywords: str,
    country: str | None = None,
    programme: str | None = None,
    sort_by: str | None = None,
    limit: int = 100,
    user_query: str = "",
) -> dict:
    """
    Search CORDIS projects using the LOCAL database (PostgreSQL + Neo4j + Vector).

    Args:
        keywords: Search keywords for project discovery.
        country: Optional country filter (ISO code or name).
        programme: Optional programme filter (e.g., 'HORIZON-RIA').
        sort_by: Optional sort field: 'relevance', 'ec_contribution',
                 'total_cost', or 'start_date'.
        limit: Maximum number of results to return.
        user_query: The original user query text, used to detect if the user
                    wants partner information (replaces self._current_query).

    Returns:
        dict with keys: projects (list), total_found (int), sources (list).
        On error: dict with keys: error (str), projects (list).
    """
    try:
        from ..local_project_search_service import LocalProjectSearchService

        if isinstance(limit, str):
            try:
                limit = int(limit)
            except ValueError:
                limit = 100
        # Always fetch a large pool for best ranking (display limit is applied later)
        limit = max(limit, 100)

        # Build the full query including country if provided
        # Let the LocalProjectSearchService handle country extraction from natural language
        query = keywords
        if country:
            query = f"{keywords} {country}"

        # Build explicit filters for programme only
        filters = {}
        if programme:
            filters["programme"] = programme.upper()

        # Use local search service - it will parse country from query
        service = LocalProjectSearchService()
        results = await service.search_projects(
            query=query,
            filters=filters if filters else None,
            limit=limit,
            sort_by=sort_by,
        )

        projects = results.get("projects", [])

        # Auto-fetch partners when limit is small and user query mentions partners/consortium
        user_query_lower = (user_query or "").lower()
        wants_partners = any(
            kw in user_query_lower for kw in ["partner", "consortium", "participant", "member"]
        )
        if wants_partners and limit <= 5 and projects:
            logger.info(
                f"🔗 Auto-fetching partners for {len(projects)} projects (user asked for partners)"
            )
            from ..data.cordis_repository import CordisProjectRepository

            repo = CordisProjectRepository()
            for proj in projects:
                pid = proj.get("id") or proj.get("project_id")
                if pid:
                    try:
                        partners = repo.get_project_partners(str(pid))
                        if partners:
                            proj["partners"] = partners
                            proj["partner_count"] = len(partners)
                            coordinator = next(
                                (p for p in partners if p.get("role") == "coordinator"), None
                            )
                            if coordinator:
                                proj["coordinator_name"] = coordinator.get("name", "")
                    except Exception as pe:
                        logger.warning(f"Failed to fetch partners for {pid}: {pe}")

        return {
            "projects": projects,
            "total_found": results.get("total_found", 0),
            "sources": results.get("sources_used", []),
        }
    except Exception as e:
        logger.error(f"Project search error: {e}")
        return {"error": str(e), "projects": []}
