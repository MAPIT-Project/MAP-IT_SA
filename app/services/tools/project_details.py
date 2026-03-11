"""
Project Details and Partners tools for CORDIS projects.

Provides detailed project lookup by ID or acronym, including full partner
lists, CORDIS URLs, and DOI URLs. Includes multi-fallback resolution logic:
try by ID, then by acronym, then by keyword search.

Extracted from the inline _tool_get_project_details and _tool_get_project_partners
methods in tool_executors.py.
"""

import logging

logger = logging.getLogger(__name__)


async def get_project_details_execute(project_id: str) -> dict:
    """
    Get detailed information about a specific project by ID or acronym.

    Fallback logic:
      1. Try to find the project by numeric ID.
      2. If not found, search by acronym using LocalProjectSearchService.
      3. If still not found, return an error with a suggestion.

    Args:
        project_id: The CORDIS project ID (numeric) or project acronym.

    Returns:
        dict with full project details including partners, CORDIS URL, DOI URL.
        On error: dict with keys: error (str), project (None), suggestion (str).
    """
    try:
        from ..data.cordis_repository import CordisProjectRepository

        if not project_id:
            return {"error": "project_id is required", "project": None}

        repo = CordisProjectRepository()

        # Try to get project by ID first
        project = repo.get_project_by_id(str(project_id))

        if not project:
            # Try search by acronym if ID lookup fails
            from ..local_project_search_service import LocalProjectSearchService

            service = LocalProjectSearchService()
            search_results = await service.search_projects(query=project_id, limit=5)

            # Find exact acronym match
            for p in search_results.get("projects", []):
                if p.get("acronym", "").upper() == project_id.upper():
                    pid = p.get("project_id") or p.get("id")
                    # Get partners for this project
                    partners = repo.get_project_partners(str(pid)) if pid else []
                    # Return this project's details
                    return {
                        "project_id": pid,
                        "rcn": p.get("rcn"),
                        "acronym": p.get("acronym"),
                        "title": p.get("title"),
                        "status": p.get("status"),
                        "objective": p.get("objective"),
                        "start_date": p.get("start_date"),
                        "end_date": p.get("end_date"),
                        "total_cost": p.get("total_cost"),
                        "ec_contribution": p.get("ec_contribution"),
                        "programme": p.get("programme"),
                        "funding_scheme": p.get("funding_scheme"),
                        "topics": p.get("topics"),
                        "coordinator": {
                            "name": p.get("coordinator_name")
                            or p.get("coordinator", {}).get("name"),
                            "country": p.get("coordinator_country")
                            or p.get("coordinator", {}).get("country"),
                        },
                        "participant_count": p.get("participant_count"),
                        "country_count": p.get("country_count"),
                        "partners": partners,
                        "cordis_url": f"https://cordis.europa.eu/project/id/{pid}",
                        "doi_url": f"https://doi.org/10.3030/{pid}" if pid else "",
                    }

            return {
                "error": f"Project not found: {project_id}",
                "project": None,
                "suggestion": "Try searching with search_projects tool using keywords from the project title",
            }

        # Get partners for this project
        partners = repo.get_project_partners(project.id)

        # Convert DTO to dict with full details
        return {
            "project_id": project.id,
            "rcn": project.rcn,
            "acronym": project.acronym,
            "title": project.title,
            "status": project.status,
            "objective": project.objective,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "total_cost": project.total_cost,
            "ec_contribution": project.ec_contribution,
            "programme": project.programme,
            "funding_scheme": project.funding_scheme,
            "topics": project.topics,
            "coordinator": {
                "name": project.coordinator_name,
                "country": project.coordinator_country,
            },
            "participant_count": project.participant_count,
            "country_count": project.country_count,
            "partners": partners,
            "cordis_url": f"https://cordis.europa.eu/project/id/{project.id}",
            "doi_url": f"https://doi.org/10.3030/{project.id}",
        }
    except Exception as e:
        logger.error(f"Get project details error: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e), "project": None}


async def get_project_partners_execute(project_id: str) -> dict:
    """
    Get all partner organizations for a specific project.

    Multi-fallback resolution logic:
      1. Try to find the project by numeric ID.
      2. If not found, try by acronym using CordisProjectRepository.
      3. If still not found, search by keywords using LocalProjectSearchService
         and match on exact acronym.
      4. If project is resolved, fetch and return the full partner list.

    Args:
        project_id: The CORDIS project ID (numeric) or project acronym.

    Returns:
        dict with keys: project_id, project_acronym, project_title,
        coordinator, partner_count, partners (list), doi_url.
        On error: dict with keys: error (str), partners (list), suggestion (str).
    """
    try:
        from ..data.cordis_repository import CordisProjectRepository

        if not project_id:
            return {"error": "project_id is required", "partners": []}

        repo = CordisProjectRepository()

        # Try to get project by ID first
        project = repo.get_project_by_id(str(project_id))

        if not project:
            # Try search by acronym
            project = repo.get_project_by_acronym(str(project_id))

        if not project:
            # Last resort: search by keywords
            from ..local_project_search_service import LocalProjectSearchService

            service = LocalProjectSearchService()
            search_results = await service.search_projects(query=project_id, limit=5)

            for p in search_results.get("projects", []):
                if p.get("acronym", "").upper() == project_id.upper():
                    project_id_found = p.get("id") or p.get("project_id")
                    if project_id_found:
                        project = repo.get_project_by_id(str(project_id_found))
                        break

        if not project:
            return {
                "error": f"Project not found: {project_id}",
                "partners": [],
                "suggestion": "Try using the exact project ID number or acronym",
            }

        # Get partners
        partners = repo.get_project_partners(project.id)

        # Identify coordinator
        coordinator = None
        for p in partners:
            if p.get("role") == "coordinator":
                coordinator = p.get("name")
                break

        return {
            "project_id": project.id,
            "project_acronym": project.acronym,
            "project_title": project.title,
            "coordinator": coordinator,
            "partner_count": len(partners),
            "partners": partners,
            "doi_url": f"https://doi.org/10.3030/{project.id}",
        }
    except Exception as e:
        logger.error(f"Get project partners error: {e}")
        return {"error": str(e), "partners": []}
