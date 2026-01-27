"""
Audit Service.

Provides comprehensive audit logging for:
- All API operations (CRUD)
- Authentication events
- Admin actions
- Data access patterns
- Compliance reporting

Features:
- Buffered writes for performance
- Structured logging for SIEM integration
- Query interface for audit trails
- Retention policies
"""

import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

# Configure structured logger for audit events
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Standard logger
logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    TOKEN_REFRESH = "auth.token_refresh"
    API_KEY_CREATED = "auth.api_key_created"
    API_KEY_REVOKED = "auth.api_key_revoked"

    # Conversation/Query
    QUERY_STARTED = "query.started"
    QUERY_COMPLETED = "query.completed"
    QUERY_FAILED = "query.failed"
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_DELETED = "conversation.deleted"

    # Proposal
    PROPOSAL_CREATED = "proposal.created"
    PROPOSAL_UPDATED = "proposal.updated"
    PROPOSAL_DELETED = "proposal.deleted"
    PROPOSAL_EXPORTED = "proposal.exported"
    PROPOSAL_REVIEWED = "proposal.reviewed"
    SECTION_GENERATED = "proposal.section_generated"

    # Search & Data Access
    CALL_SEARCH = "search.calls"
    PROJECT_SEARCH = "search.projects"
    PARTNER_SEARCH = "search.partners"
    DOCUMENT_SEARCH = "search.documents"
    DATA_EXPORTED = "data.exported"

    # Saved Searches & Alerts
    SAVED_SEARCH_CREATED = "saved_search.created"
    SAVED_SEARCH_UPDATED = "saved_search.updated"
    SAVED_SEARCH_DELETED = "saved_search.deleted"
    ALERT_SENT = "alert.sent"

    # Collaboration
    COLLAB_JOINED = "collaboration.joined"
    COLLAB_LEFT = "collaboration.left"
    SECTION_LOCKED = "collaboration.section_locked"
    SECTION_UNLOCKED = "collaboration.section_unlocked"

    # Admin Actions
    ADMIN_USER_CREATED = "admin.user_created"
    ADMIN_USER_UPDATED = "admin.user_updated"
    ADMIN_USER_DELETED = "admin.user_deleted"
    ADMIN_SETTINGS_CHANGED = "admin.settings_changed"
    ADMIN_MIGRATION_RUN = "admin.migration_run"

    # System Events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    RATE_LIMIT_EXCEEDED = "system.rate_limit"


class AuditAction(str, Enum):
    """CRUD actions for audit events."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"


@dataclass
class AuditEvent:
    """An audit event record."""

    event_id: str
    event_type: AuditEventType
    action: AuditAction
    timestamp: datetime

    # Actor information
    user_id: str | None = None
    organization_id: str | None = None
    session_id: str | None = None

    # Resource information
    resource_type: str | None = None
    resource_id: str | None = None
    resource_name: str | None = None

    # Request information
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    endpoint: str | None = None
    http_method: str | None = None

    # Outcome
    success: bool = True
    error_message: str | None = None
    error_code: str | None = None

    # Additional context
    details: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Performance
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "action": self.action.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "session_id": self.session_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "endpoint": self.endpoint,
            "http_method": self.http_method,
            "success": self.success,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "details": self.details,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
        }

    def to_log_record(self) -> dict[str, Any]:
        """Convert to structured log record for SIEM."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "action": self.action.value,
            "timestamp": self.timestamp.isoformat() + "Z",
            "actor": {
                "user_id": self.user_id,
                "organization_id": self.organization_id,
                "ip_address": self.ip_address,
                "user_agent": self.user_agent,
            },
            "resource": {
                "type": self.resource_type,
                "id": self.resource_id,
                "name": self.resource_name,
            },
            "request": {
                "id": self.request_id,
                "endpoint": self.endpoint,
                "method": self.http_method,
            },
            "outcome": {
                "success": self.success,
                "error_message": self.error_message,
                "error_code": self.error_code,
                "duration_ms": self.duration_ms,
            },
            "context": self.details,
        }


class AuditService:
    """Service for comprehensive audit logging."""

    # Buffer settings
    BUFFER_SIZE = 100
    FLUSH_INTERVAL_SECONDS = 5

    # Retention settings
    RETENTION_DAYS = 90

    def __init__(self, db_pool=None, redis_client=None):
        """
        Initialize the audit service.

        Args:
            db_pool: PostgreSQL connection pool
            redis_client: Redis client for buffering
        """
        self.db_pool = db_pool
        self.redis = redis_client

        # In-memory buffer for batch writes
        self._buffer: deque[AuditEvent] = deque(maxlen=self.BUFFER_SIZE)
        self._last_flush = datetime.now(UTC)
        self._flush_lock = asyncio.Lock()

    # =========================================================================
    # Event Logging
    # =========================================================================

    async def log_event(self, event: AuditEvent):
        """
        Log an audit event.

        Events are buffered and written in batches for performance.
        High-priority events (errors, auth) are written immediately.
        """
        # Log to structured logger for SIEM
        self._log_to_siem(event)

        # Add to buffer
        self._buffer.append(event)

        # Check if we should flush
        should_flush = (
            len(self._buffer) >= self.BUFFER_SIZE
            or (datetime.now(UTC) - self._last_flush).seconds >= self.FLUSH_INTERVAL_SECONDS
            or self._is_high_priority(event)
        )

        if should_flush:
            await self.flush()

    def _is_high_priority(self, event: AuditEvent) -> bool:
        """Check if event is high priority and should be flushed immediately."""
        high_priority_types = {
            AuditEventType.LOGIN,
            AuditEventType.LOGIN_FAILED,
            AuditEventType.ADMIN_USER_DELETED,
            AuditEventType.ADMIN_SETTINGS_CHANGED,
            AuditEventType.SYSTEM_ERROR,
            AuditEventType.RATE_LIMIT_EXCEEDED,
        }
        return event.event_type in high_priority_types or not event.success

    def _log_to_siem(self, event: AuditEvent):
        """Log event in structured format for SIEM ingestion."""
        audit_logger.info(
            json.dumps(event.to_log_record()),
            extra={
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "user_id": event.user_id,
                "success": event.success,
            },
        )

    async def flush(self):
        """Flush buffered events to database."""
        async with self._flush_lock:
            if not self._buffer:
                return

            events = list(self._buffer)
            self._buffer.clear()
            self._last_flush = datetime.now(UTC)

        if self.db_pool:
            await self._write_to_db(events)

    async def _write_to_db(self, events: list[AuditEvent]):
        """Write events to database."""
        if not self.db_pool or not events:
            return

        query = """
            INSERT INTO audit_events (
                event_id, event_type, action, timestamp,
                user_id, organization_id, session_id,
                resource_type, resource_id, resource_name,
                ip_address, user_agent, request_id, endpoint, http_method,
                success, error_message, error_code,
                details, metadata, duration_ms
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        try:
            with self.db_pool.get_connection() as conn:
                with conn.cursor() as cur:
                    for event in events:
                        cur.execute(
                            query,
                            (
                                event.event_id,
                                event.event_type.value,
                                event.action.value,
                                event.timestamp,
                                event.user_id,
                                event.organization_id,
                                event.session_id,
                                event.resource_type,
                                event.resource_id,
                                event.resource_name,
                                event.ip_address,
                                event.user_agent,
                                event.request_id,
                                event.endpoint,
                                event.http_method,
                                event.success,
                                event.error_message,
                                event.error_code,
                                json.dumps(event.details),
                                json.dumps(event.metadata),
                                event.duration_ms,
                            ),
                        )
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to write audit events: {e}")

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def log_query(
        self,
        user_id: str,
        conversation_id: str,
        query: str,
        tools_used: list[str],
        duration_ms: float,
        success: bool = True,
        error: str | None = None,
        request=None,
    ):
        """Log a conversation query event."""
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=AuditEventType.QUERY_COMPLETED if success else AuditEventType.QUERY_FAILED,
            action=AuditAction.EXECUTE,
            timestamp=datetime.now(UTC),
            user_id=user_id,
            session_id=conversation_id,
            resource_type="conversation",
            resource_id=conversation_id,
            success=success,
            error_message=error,
            duration_ms=duration_ms,
            details={
                "query_length": len(query),
                "query_preview": query[:100] + "..." if len(query) > 100 else query,
                "tools_used": tools_used,
                "tool_count": len(tools_used),
            },
        )

        if request:
            event.ip_address = self._get_client_ip(request)
            event.user_agent = request.headers.get("user-agent", "")[:256]
            event.endpoint = str(request.url.path)
            event.http_method = request.method

        await self.log_event(event)

    async def log_auth_event(
        self,
        event_type: AuditEventType,
        user_id: str | None,
        success: bool = True,
        error: str | None = None,
        request=None,
        details: dict | None = None,
    ):
        """Log an authentication event."""
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            action=AuditAction.LOGIN if "login" in event_type.value else AuditAction.LOGOUT,
            timestamp=datetime.now(UTC),
            user_id=user_id,
            resource_type="auth",
            success=success,
            error_message=error,
            details=details or {},
        )

        if request:
            event.ip_address = self._get_client_ip(request)
            event.user_agent = request.headers.get("user-agent", "")[:256]
            event.endpoint = str(request.url.path)
            event.http_method = request.method

        await self.log_event(event)

    async def log_proposal_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        session_id: str,
        proposal_title: str = None,
        section_id: str = None,
        action: AuditAction = AuditAction.UPDATE,
        details: dict | None = None,
        request=None,
    ):
        """Log a proposal-related event."""
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            action=action,
            timestamp=datetime.now(UTC),
            user_id=user_id,
            session_id=session_id,
            resource_type="proposal",
            resource_id=session_id,
            resource_name=proposal_title,
            details={
                "section_id": section_id,
                **(details or {}),
            },
        )

        if request:
            event.ip_address = self._get_client_ip(request)
            event.user_agent = request.headers.get("user-agent", "")[:256]

        await self.log_event(event)

    async def log_search_event(
        self,
        search_type: str,
        user_id: str,
        query_params: dict[str, Any],
        result_count: int,
        duration_ms: float,
        request=None,
    ):
        """Log a search event."""
        event_type_map = {
            "calls": AuditEventType.CALL_SEARCH,
            "projects": AuditEventType.PROJECT_SEARCH,
            "partners": AuditEventType.PARTNER_SEARCH,
            "documents": AuditEventType.DOCUMENT_SEARCH,
        }

        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type_map.get(search_type, AuditEventType.DOCUMENT_SEARCH),
            action=AuditAction.READ,
            timestamp=datetime.now(UTC),
            user_id=user_id,
            resource_type="search",
            duration_ms=duration_ms,
            details={
                "search_type": search_type,
                "query_params": query_params,
                "result_count": result_count,
            },
        )

        if request:
            event.ip_address = self._get_client_ip(request)
            event.user_agent = request.headers.get("user-agent", "")[:256]

        await self.log_event(event)

    async def log_admin_action(
        self,
        event_type: AuditEventType,
        admin_user_id: str,
        target_user_id: str | None = None,
        action: AuditAction = AuditAction.UPDATE,
        details: dict | None = None,
        request=None,
    ):
        """Log an admin action."""
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            action=action,
            timestamp=datetime.now(UTC),
            user_id=admin_user_id,
            resource_type="admin",
            resource_id=target_user_id,
            details=details or {},
        )

        if request:
            event.ip_address = self._get_client_ip(request)
            event.user_agent = request.headers.get("user-agent", "")[:256]

        await self.log_event(event)

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check X-Forwarded-For header
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to client host
        return request.client.host if request.client else "unknown"

    # =========================================================================
    # Query Interface
    # =========================================================================

    async def get_audit_trail(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        user_id: str | None = None,
        event_types: list[AuditEventType] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Query audit events.

        Args:
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            user_id: Filter by user ID
            event_types: Filter by event types
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of audit events
        """
        if not self.db_pool:
            return []

        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []

        if resource_type:
            query += " AND resource_type = %s"
            params.append(resource_type)

        if resource_id:
            query += " AND resource_id = %s"
            params.append(resource_id)

        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)

        if event_types:
            placeholders = ",".join(["%s"] * len(event_types))
            query += f" AND event_type IN ({placeholders})"
            params.extend([e.value for e in event_types])

        if start_time:
            query += " AND timestamp >= %s"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= %s"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        events = []
        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                for row in rows:
                    events.append(dict(zip(columns, row, strict=False)))

        return events

    async def get_user_activity(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get activity summary for a user."""
        if not self.db_pool:
            return {}

        start_time = datetime.now(UTC) - timedelta(days=days)

        query = """
            SELECT
                event_type,
                COUNT(*) as count,
                MAX(timestamp) as last_occurrence
            FROM audit_events
            WHERE user_id = %s AND timestamp >= %s
            GROUP BY event_type
            ORDER BY count DESC
        """

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (user_id, start_time))
                rows = cur.fetchall()

        activity = {
            "user_id": user_id,
            "period_days": days,
            "event_counts": {},
            "total_events": 0,
        }

        for row in rows:
            activity["event_counts"][row[0]] = {
                "count": row[1],
                "last_occurrence": row[2].isoformat() if row[2] else None,
            }
            activity["total_events"] += row[1]

        return activity

    async def get_security_events(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get recent security-related events."""
        security_types = [
            AuditEventType.LOGIN,
            AuditEventType.LOGIN_FAILED,
            AuditEventType.LOGOUT,
            AuditEventType.API_KEY_CREATED,
            AuditEventType.API_KEY_REVOKED,
            AuditEventType.RATE_LIMIT_EXCEEDED,
            AuditEventType.ADMIN_USER_DELETED,
            AuditEventType.ADMIN_SETTINGS_CHANGED,
        ]

        return await self.get_audit_trail(
            event_types=security_types,
            start_time=datetime.now(UTC) - timedelta(hours=hours),
            limit=limit,
        )

    # =========================================================================
    # Maintenance
    # =========================================================================

    async def cleanup_old_events(self, retention_days: int | None = None):
        """Delete audit events older than retention period."""
        if not self.db_pool:
            return 0

        days = retention_days or self.RETENTION_DAYS
        cutoff = datetime.now(UTC) - timedelta(days=days)

        query = "DELETE FROM audit_events WHERE timestamp < %s"

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (cutoff,))
                deleted = cur.rowcount
                conn.commit()

        logger.info(f"Cleaned up {deleted} audit events older than {days} days")
        return deleted

    async def get_statistics(self, days: int = 30) -> dict[str, Any]:
        """Get audit statistics."""
        if not self.db_pool:
            return {}

        start_time = datetime.now(UTC) - timedelta(days=days)

        stats_query = """
            SELECT
                COUNT(*) as total_events,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(*) FILTER (WHERE success = false) as failed_events,
                COUNT(*) FILTER (WHERE event_type LIKE 'auth.%%') as auth_events,
                COUNT(*) FILTER (WHERE event_type LIKE 'query.%%') as query_events,
                COUNT(*) FILTER (WHERE event_type LIKE 'proposal.%%') as proposal_events,
                AVG(duration_ms) FILTER (WHERE duration_ms IS NOT NULL) as avg_duration_ms
            FROM audit_events
            WHERE timestamp >= %s
        """

        top_users_query = """
            SELECT user_id, COUNT(*) as event_count
            FROM audit_events
            WHERE timestamp >= %s AND user_id IS NOT NULL
            GROUP BY user_id
            ORDER BY event_count DESC
            LIMIT 10
        """

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(stats_query, (start_time,))
                stats_row = cur.fetchone()

                cur.execute(top_users_query, (start_time,))
                top_users = cur.fetchall()

        return {
            "period_days": days,
            "total_events": stats_row[0] or 0,
            "unique_users": stats_row[1] or 0,
            "failed_events": stats_row[2] or 0,
            "auth_events": stats_row[3] or 0,
            "query_events": stats_row[4] or 0,
            "proposal_events": stats_row[5] or 0,
            "avg_duration_ms": float(stats_row[6]) if stats_row[6] else None,
            "top_users": [{"user_id": row[0], "event_count": row[1]} for row in top_users],
        }


# Singleton instance
_audit_service: AuditService | None = None


def get_audit_service(
    db_pool=None,
    redis_client=None,
) -> AuditService:
    """Get or create the AuditService singleton."""
    global _audit_service

    if _audit_service is None:
        _audit_service = AuditService(
            db_pool=db_pool,
            redis_client=redis_client,
        )

    return _audit_service
