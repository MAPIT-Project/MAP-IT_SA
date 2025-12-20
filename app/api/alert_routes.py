"""
Saved Searches and Alerts API Routes.

Provides endpoints for:
- Creating, reading, updating, deleting saved searches
- Running saved searches on-demand
- Managing alert configurations
- Viewing user statistics
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.alerts.saved_search_service import (
    AlertChannel,
    AlertConfig,
    AlertFrequency,
    SavedSearchService,
    SearchType,
    get_saved_search_service,
)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# =============================================================================
# Request/Response Models
# =============================================================================


class AlertConfigRequest(BaseModel):
    """Alert configuration request."""
    enabled: bool = False
    frequency: str = Field("daily", pattern="^(immediate|daily|weekly)$")
    channel: str = Field("email", pattern="^(email|webhook|both)$")
    email: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    min_results_to_alert: int = Field(1, ge=1, le=100)


class CreateSavedSearchRequest(BaseModel):
    """Request to create a saved search."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    search_type: str = Field(..., pattern="^(calls|projects|partners)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    alert_config: Optional[AlertConfigRequest] = None


class UpdateSavedSearchRequest(BaseModel):
    """Request to update a saved search."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    parameters: Optional[Dict[str, Any]] = None
    alert_config: Optional[AlertConfigRequest] = None
    is_active: Optional[bool] = None


class SavedSearchResponse(BaseModel):
    """Saved search response."""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    search_type: str
    parameters: Dict[str, Any]
    alert_config: Dict[str, Any]
    created_at: str
    updated_at: str
    last_run: Optional[str]
    is_active: bool
    run_count: int
    alert_count: int


class SearchResultResponse(BaseModel):
    """Search execution result response."""
    search_id: str
    result_count: int
    new_count: int
    execution_time_ms: float
    executed_at: str
    results: List[Dict[str, Any]]
    new_results: List[Dict[str, Any]]


class UserStatsResponse(BaseModel):
    """User statistics response."""
    total_searches: int
    active_searches: int
    inactive_searches: int
    total_runs: int
    total_alerts_sent: int
    by_type: Dict[str, int]


# =============================================================================
# Helper Functions
# =============================================================================


def _convert_alert_config(config: Optional[AlertConfigRequest]) -> Optional[AlertConfig]:
    """Convert request model to service model."""
    if not config:
        return None

    return AlertConfig(
        enabled=config.enabled,
        frequency=AlertFrequency(config.frequency),
        channel=AlertChannel(config.channel),
        email=config.email,
        webhook_url=config.webhook_url,
        webhook_secret=config.webhook_secret,
        min_results_to_alert=config.min_results_to_alert,
    )


def _search_to_response(search) -> SavedSearchResponse:
    """Convert SavedSearch to response model."""
    data = search.to_dict()
    return SavedSearchResponse(
        id=data["id"],
        user_id=data["user_id"],
        name=data["name"],
        description=data["description"],
        search_type=data["search_type"],
        parameters=data["parameters"],
        alert_config=data["alert_config"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        last_run=data["last_run"],
        is_active=data["is_active"],
        run_count=data["run_count"],
        alert_count=data["alert_count"],
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint for alerts service.

    Returns:
        Service health status
    """
    return {
        "status": "healthy",
        "service": "alerts",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_search(
    request: CreateSavedSearchRequest,
    user_id: str = Query(..., description="User ID"),
):
    """
    Create a new saved search.

    Args:
        request: Search configuration
        user_id: User ID (from auth in production)

    Returns:
        Created saved search
    """
    service = get_saved_search_service()

    search = await service.create_search(
        user_id=user_id,
        name=request.name,
        search_type=SearchType(request.search_type),
        parameters=request.parameters,
        description=request.description,
        alert_config=_convert_alert_config(request.alert_config),
    )

    return _search_to_response(search)


@router.get("", response_model=List[SavedSearchResponse])
async def list_saved_searches(
    user_id: str = Query(..., description="User ID"),
    search_type: Optional[str] = Query(None, pattern="^(calls|projects|partners)$"),
    active_only: bool = Query(True, description="Only return active searches"),
):
    """
    List all saved searches for a user.

    Args:
        user_id: User ID
        search_type: Filter by search type
        active_only: Only return active searches

    Returns:
        List of saved searches
    """
    service = get_saved_search_service()

    searches = await service.get_user_searches(
        user_id=user_id,
        search_type=SearchType(search_type) if search_type else None,
        active_only=active_only,
    )

    return [_search_to_response(s) for s in searches]


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: str = Query(..., description="User ID"),
):
    """
    Get saved search statistics for a user.

    Args:
        user_id: User ID

    Returns:
        User statistics
    """
    service = get_saved_search_service()
    stats = await service.get_user_stats(user_id)

    return UserStatsResponse(
        total_searches=stats["total_searches"],
        active_searches=stats["active_searches"],
        inactive_searches=stats["inactive_searches"],
        total_runs=stats["total_runs"],
        total_alerts_sent=stats["total_alerts_sent"],
        by_type=stats["by_type"],
    )


@router.get("/{search_id}", response_model=SavedSearchResponse)
async def get_saved_search(
    search_id: str,
):
    """
    Get a saved search by ID.

    Args:
        search_id: Search ID

    Returns:
        Saved search

    Raises:
        404: Search not found
    """
    service = get_saved_search_service()
    search = await service.get_search(search_id)

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search {search_id} not found",
        )

    return _search_to_response(search)


@router.patch("/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: str,
    request: UpdateSavedSearchRequest,
):
    """
    Update a saved search.

    Args:
        search_id: Search ID
        request: Update fields

    Returns:
        Updated saved search

    Raises:
        404: Search not found
    """
    service = get_saved_search_service()

    search = await service.update_search(
        search_id=search_id,
        name=request.name,
        description=request.description,
        parameters=request.parameters,
        alert_config=_convert_alert_config(request.alert_config),
        is_active=request.is_active,
    )

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search {search_id} not found",
        )

    return _search_to_response(search)


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: str,
    permanent: bool = Query(False, description="Permanently delete instead of soft delete"),
):
    """
    Delete a saved search.

    Args:
        search_id: Search ID
        permanent: If True, permanently delete; otherwise soft delete

    Raises:
        404: Search not found
    """
    service = get_saved_search_service()

    if permanent:
        success = await service.hard_delete_search(search_id)
    else:
        success = await service.delete_search(search_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search {search_id} not found",
        )


@router.post("/{search_id}/run", response_model=SearchResultResponse)
async def run_saved_search(
    search_id: str,
):
    """
    Run a saved search immediately.

    Args:
        search_id: Search ID

    Returns:
        Search results

    Raises:
        404: Search not found
    """
    service = get_saved_search_service()
    search = await service.get_search(search_id)

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search {search_id} not found",
        )

    result = await service.run_search(search)

    return SearchResultResponse(
        search_id=result.search_id,
        result_count=result.result_count,
        new_count=result.new_count,
        execution_time_ms=result.execution_time_ms,
        executed_at=result.executed_at.isoformat(),
        results=result.results,
        new_results=result.new_results,
    )


@router.post("/process-alerts")
async def process_alerts(
    frequency: Optional[str] = Query(None, pattern="^(immediate|daily|weekly)$"),
):
    """
    Manually trigger alert processing.

    This endpoint is typically called by Celery periodic tasks,
    but can be triggered manually for testing.

    Args:
        frequency: Optional frequency filter

    Returns:
        Processing summary
    """
    service = get_saved_search_service()

    freq = AlertFrequency(frequency) if frequency else None
    result = await service.process_alerts(freq)

    return result
