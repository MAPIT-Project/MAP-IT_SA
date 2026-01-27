"""
Audit API Routes.

Provides endpoints for:
- Querying audit trails
- Viewing user activity
- Security event monitoring
- Audit statistics
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query, status
from pydantic import BaseModel

from app.services.audit.audit_service import AuditEventType, get_audit_service

router = APIRouter(prefix="/api/audit", tags=["audit"])


# =============================================================================
# Response Models
# =============================================================================


class AuditEventResponse(BaseModel):
    """Audit event response."""

    event_id: str
    event_type: str
    action: str
    timestamp: str
    user_id: str | None
    organization_id: str | None
    resource_type: str | None
    resource_id: str | None
    resource_name: str | None
    ip_address: str | None
    success: bool
    error_message: str | None
    duration_ms: float | None
    details: dict[str, Any]


class AuditTrailResponse(BaseModel):
    """Audit trail query response."""

    events: list[dict[str, Any]]
    total_count: int
    has_more: bool


class UserActivityResponse(BaseModel):
    """User activity summary response."""

    user_id: str
    period_days: int
    total_events: int
    event_counts: dict[str, Any]


class AuditStatsResponse(BaseModel):
    """Audit statistics response."""

    period_days: int
    total_events: int
    unique_users: int
    failed_events: int
    auth_events: int
    query_events: int
    proposal_events: int
    avg_duration_ms: float | None
    top_users: list[dict[str, Any]]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/trail", response_model=AuditTrailResponse)
async def get_audit_trail(
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    event_type: str | None = Query(None, description="Filter by event type"),
    start_time: datetime | None = Query(None, description="Start of time range"),
    end_time: datetime | None = Query(None, description="End of time range"),
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """
    Query audit events.

    Retrieves audit events matching the specified filters.
    By default, returns events from the last 7 days.
    """
    service = get_audit_service()

    # Default time range if not specified
    if not start_time:
        start_time = datetime.now(UTC) - timedelta(days=days)
    if not end_time:
        end_time = datetime.now(UTC)

    # Parse event types
    event_types = None
    if event_type:
        try:
            event_types = [AuditEventType(event_type)]
        except ValueError:
            pass

    events = await service.get_audit_trail(
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        event_types=event_types,
        start_time=start_time,
        end_time=end_time,
        limit=limit + 1,  # Get one extra to check has_more
        offset=offset,
    )

    has_more = len(events) > limit
    if has_more:
        events = events[:limit]

    return AuditTrailResponse(
        events=events,
        total_count=len(events),
        has_more=has_more,
    )


@router.get("/trail/{resource_type}/{resource_id}")
async def get_resource_audit_trail(
    resource_type: str,
    resource_id: str,
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Get audit trail for a specific resource.

    Useful for tracking all operations on a specific
    conversation, proposal, or other resource.
    """
    service = get_audit_service()

    events = await service.get_audit_trail(
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )

    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "events": events,
        "total_count": len(events),
    }


@router.get("/user/{user_id}/activity", response_model=UserActivityResponse)
async def get_user_activity(
    user_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days"),
):
    """
    Get activity summary for a user.

    Returns aggregated counts of different event types
    for the specified user.
    """
    service = get_audit_service()
    activity = await service.get_user_activity(user_id, days=days)

    return UserActivityResponse(
        user_id=activity.get("user_id", user_id),
        period_days=activity.get("period_days", days),
        total_events=activity.get("total_events", 0),
        event_counts=activity.get("event_counts", {}),
    )


@router.get("/user/{user_id}/events")
async def get_user_events(
    user_id: str,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Get recent events for a specific user.

    Returns detailed event records for the user.
    """
    service = get_audit_service()

    events = await service.get_audit_trail(
        user_id=user_id,
        start_time=datetime.now(UTC) - timedelta(days=days),
        limit=limit,
        offset=offset,
    )

    return {
        "user_id": user_id,
        "period_days": days,
        "events": events,
        "total_count": len(events),
    }


@router.get("/security")
async def get_security_events(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Get recent security-related events.

    Includes authentication attempts, failed logins,
    admin actions, and rate limit violations.
    """
    service = get_audit_service()
    events = await service.get_security_events(hours=hours, limit=limit)

    # Group by severity
    failed_logins = [e for e in events if e.get("event_type") == "auth.login_failed"]
    rate_limits = [e for e in events if e.get("event_type") == "system.rate_limit"]
    admin_actions = [e for e in events if e.get("event_type", "").startswith("admin.")]

    return {
        "period_hours": hours,
        "total_events": len(events),
        "summary": {
            "failed_logins": len(failed_logins),
            "rate_limit_violations": len(rate_limits),
            "admin_actions": len(admin_actions),
        },
        "events": events,
    }


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days"),
):
    """
    Get audit system statistics.

    Returns aggregated statistics including event counts,
    unique users, and performance metrics.
    """
    service = get_audit_service()
    stats = await service.get_statistics(days=days)

    return AuditStatsResponse(
        period_days=stats.get("period_days", days),
        total_events=stats.get("total_events", 0),
        unique_users=stats.get("unique_users", 0),
        failed_events=stats.get("failed_events", 0),
        auth_events=stats.get("auth_events", 0),
        query_events=stats.get("query_events", 0),
        proposal_events=stats.get("proposal_events", 0),
        avg_duration_ms=stats.get("avg_duration_ms"),
        top_users=stats.get("top_users", []),
    )


@router.get("/event-types")
async def get_event_types():
    """
    Get list of available audit event types.

    Useful for building filters in dashboards.
    """
    return {
        "event_types": [
            {
                "value": e.value,
                "name": e.name,
                "category": e.value.split(".")[0],
            }
            for e in AuditEventType
        ]
    }


@router.post("/cleanup")
async def cleanup_old_events(
    retention_days: int = Query(90, ge=30, le=365, description="Days to retain"),
):
    """
    Cleanup old audit events.

    Deletes audit events older than the specified retention period.
    Requires admin privileges in production.
    """
    service = get_audit_service()
    deleted_count = await service.cleanup_old_events(retention_days)

    return {
        "success": True,
        "deleted_count": deleted_count,
        "retention_days": retention_days,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint for audit service."""
    service = get_audit_service()

    # Flush any pending events
    await service.flush()

    return {
        "status": "healthy",
        "service": "audit",
        "buffer_size": len(service._buffer),
        "timestamp": datetime.now(UTC).isoformat(),
    }
