"""
Project-related API endpoints.
"""

import logging
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends, status

from app.models.project import (
    ProjectSearchRequest,
    ProjectSearchResponse,
    ProjectSummary,
    ProjectDetail,
    ProjectDetailWithResults,
    Publication,
    Deliverable,
    ProjectImpactMetrics,
)
from app.services.data.cordis_repository import CordisProjectRepository, CordisProjectDTO
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])


def get_repository() -> CordisProjectRepository:
    """
    Dependency to get the CORDIS project repository.

    Returns:
        CordisProjectRepository instance

    Raises:
        HTTPException: If database configuration is missing
    """
    settings = get_settings()
    if not settings.database.url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured"
        )
    try:
        return CordisProjectRepository(settings.database.url)
    except Exception as e:
        logger.error(f"Failed to create repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )


def dto_to_summary(dto: CordisProjectDTO) -> ProjectSummary:
    """Convert a CordisProjectDTO to ProjectSummary."""
    return ProjectSummary(
        id=dto.id,
        rcn=dto.rcn,
        title=dto.title,
        acronym=dto.acronym,
        objective=dto.objective[:500] + "..." if len(dto.objective) > 500 else dto.objective,
        start_date=dto.start_date,
        end_date=dto.end_date,
        total_cost=dto.total_cost,
        ec_max_contribution=dto.ec_max_contribution,
        status=dto.status,
        framework_programme=dto.framework_programme,
        participant_count=dto.participant_count,
        country_count=dto.country_count,
        coordinator_name=dto.coordinator_name,
        coordinator_country=dto.coordinator_country,
        relevance_score=dto.relevance_score
    )


def dto_to_detail(dto: CordisProjectDTO) -> ProjectDetail:
    """Convert a CordisProjectDTO to ProjectDetail."""
    return ProjectDetail(
        id=dto.id,
        rcn=dto.rcn,
        title=dto.title,
        acronym=dto.acronym,
        objective=dto.objective,
        start_date=dto.start_date,
        end_date=dto.end_date,
        total_cost=dto.total_cost,
        ec_max_contribution=dto.ec_max_contribution,
        status=dto.status,
        framework_programme=dto.framework_programme,
        funding_scheme=dto.funding_scheme,
        legal_basis=dto.legal_basis,
        topics=dto.topics,
        grant_doi=dto.grant_doi,
        participant_count=dto.participant_count,
        country_count=dto.country_count,
        sme_count=dto.sme_count,
        coordinator_name=dto.coordinator_name,
        coordinator_country=dto.coordinator_country,
        participant_names=dto.participant_names,
        participant_countries=dto.participant_countries,
        participant_cities=dto.participant_cities,
        total_ec_contribution=dto.total_ec_contribution,
        nuts_codes=dto.nuts_codes,
        activity_types=dto.activity_types,
        relevance_score=dto.relevance_score
    )


@router.post(
    "/search",
    response_model=ProjectSearchResponse,
    summary="Search Projects",
    description="Search CORDIS projects with full-text and structured filters"
)
async def search_projects(
    request: ProjectSearchRequest,
    repo: CordisProjectRepository = Depends(get_repository)
) -> ProjectSearchResponse:
    """
    Search for CORDIS projects.

    Args:
        request: Search request with queries and optional filters

    Returns:
        ProjectSearchResponse with matching projects and metadata
    """
    start_time = time.time()

    # Build filters dict
    filters = None
    if request.filters:
        filters = {}
        if request.filters.programme:
            filters['programme'] = request.filters.programme
        if request.filters.date_start or request.filters.date_end:
            filters['date_range'] = {}
            if request.filters.date_start:
                filters['date_range']['start'] = request.filters.date_start.isoformat()
            if request.filters.date_end:
                filters['date_range']['end'] = request.filters.date_end.isoformat()
        if request.filters.budget_min is not None or request.filters.budget_max is not None:
            filters['budget_range'] = {}
            if request.filters.budget_min is not None:
                filters['budget_range']['min'] = request.filters.budget_min
            if request.filters.budget_max is not None:
                filters['budget_range']['max'] = request.filters.budget_max
        if request.filters.countries:
            filters['countries'] = [c.lower() for c in request.filters.countries]

    try:
        projects, total_count = repo.search_projects(
            queries=request.queries,
            filters=filters,
            limit=request.limit,
            offset=request.offset
        )

        elapsed_ms = (time.time() - start_time) * 1000

        return ProjectSearchResponse(
            projects=[dto_to_summary(p) for p in projects],
            total_count=total_count,
            limit=request.limit,
            offset=request.offset,
            query_time_ms=round(elapsed_ms, 2)
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search operation failed"
        )


@router.get(
    "/search",
    response_model=ProjectSearchResponse,
    summary="Search Projects (GET)",
    description="Search CORDIS projects using query parameters"
)
async def search_projects_get(
    q: str = Query(..., min_length=2, description="Search query"),
    programme: Optional[str] = Query(None, description="Framework programme filter"),
    countries: Optional[str] = Query(None, description="Comma-separated country codes"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    repo: CordisProjectRepository = Depends(get_repository)
) -> ProjectSearchResponse:
    """
    Search for CORDIS projects using GET parameters.

    Simpler alternative to POST endpoint for basic searches.
    """
    start_time = time.time()

    filters = None
    if programme or countries:
        filters = {}
        if programme:
            filters['programme'] = programme
        if countries:
            filters['countries'] = [c.strip().lower() for c in countries.split(',')]

    try:
        projects, total_count = repo.search_projects(
            queries=[q],
            filters=filters,
            limit=limit,
            offset=offset
        )

        elapsed_ms = (time.time() - start_time) * 1000

        return ProjectSearchResponse(
            projects=[dto_to_summary(p) for p in projects],
            total_count=total_count,
            limit=limit,
            offset=offset,
            query_time_ms=round(elapsed_ms, 2)
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search operation failed"
        )


@router.get(
    "/{project_id}",
    response_model=ProjectDetailWithResults,
    summary="Get Project Details",
    description="Get detailed information about a specific project"
)
async def get_project(
    project_id: str,
    include_publications: bool = Query(True, description="Include publications"),
    include_deliverables: bool = Query(True, description="Include deliverables"),
    repo: CordisProjectRepository = Depends(get_repository)
) -> ProjectDetailWithResults:
    """
    Get detailed information about a specific project.

    Args:
        project_id: CORDIS project ID
        include_publications: Whether to include publications
        include_deliverables: Whether to include deliverables

    Returns:
        ProjectDetailWithResults with full project information
    """
    try:
        dto = repo.get_project_by_id(project_id)
        if not dto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        detail = dto_to_detail(dto)

        # Get publications if requested
        publications = []
        if include_publications:
            pub_data = repo.get_project_publications(project_id)
            publications = [
                Publication(**pub) for pub in pub_data
            ]

        # Get deliverables if requested
        deliverables = []
        if include_deliverables:
            del_data = repo.get_project_deliverables(project_id)
            deliverables = [
                Deliverable(**d) for d in del_data
            ]

        # Get impact metrics
        metrics_data = repo.get_project_impact_metrics(project_id)
        impact_metrics = ProjectImpactMetrics(**metrics_data)

        return ProjectDetailWithResults(
            **detail.model_dump(),
            publications=publications,
            deliverables=deliverables,
            impact_metrics=impact_metrics
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project"
        )
