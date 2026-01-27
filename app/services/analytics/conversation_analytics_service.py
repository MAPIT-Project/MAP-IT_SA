"""
Conversation Analytics Service

Logs all conversation messages and responses to Supabase for analytics,
quality monitoring, and iterative improvement.
"""

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from psycopg2 import pool
from psycopg2.extras import Json, RealDictCursor

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class ConversationEvent:
    """Single conversation message/response event."""

    conversation_id: int
    question: str
    response: str | None = None
    tools_used: list[str] | None = None
    confidence: float | None = None
    response_time_ms: int | None = None
    metadata: dict[str, Any] | None = field(default_factory=dict)
    user_id: int = 1
    session_id: str | None = None
    status: str = "completed"
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    message_id: str | None = None

    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        if self.started_at is None:
            self.started_at = datetime.now()


class ConversationAnalyticsService:
    """Service for logging and analyzing conversation data."""

    _instance = None
    _pool = None

    def __new__(cls):
        """Singleton pattern for shared connection pool."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the analytics service."""
        if self._initialized:
            return

        self.db_url = os.getenv("DATABASE_URL")
        self.buffer: list[ConversationEvent] = []
        self.buffer_size = 10  # Batch write every 10 events
        self.flush_interval = 30  # Or every 30 seconds
        self.last_flush = datetime.now()
        self.enabled = bool(self.db_url)

        if self.enabled:
            try:
                self._init_pool()
                logger.info("Conversation analytics service initialized")
            except Exception as e:
                logger.warning(f"Conversation analytics service disabled: {e}")
                self.enabled = False

        self._initialized = True

    def _init_pool(self):
        """Initialize database connection pool."""
        if ConversationAnalyticsService._pool is None:
            ConversationAnalyticsService._pool = pool.SimpleConnectionPool(1, 5, self.db_url)

    def _get_connection(self):
        """Get a connection from the pool."""
        if ConversationAnalyticsService._pool:
            return ConversationAnalyticsService._pool.getconn()
        return None

    def _return_connection(self, conn):
        """Return a connection to the pool."""
        if ConversationAnalyticsService._pool and conn:
            ConversationAnalyticsService._pool.putconn(conn)

    def log_conversation(
        self,
        conversation_id: int,
        question: str,
        response: str,
        tools_used: list[str] | None = None,
        confidence: float | None = None,
        response_time_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: int = 1,
        session_id: str | None = None,
        status: str = "completed",
        error_message: str | None = None,
    ) -> str | None:
        """
        Log a conversation event synchronously.

        Returns the message_id if successful, None otherwise.
        """
        if not self.enabled:
            logger.debug("Analytics disabled, skipping log")
            return None

        event = ConversationEvent(
            conversation_id=conversation_id,
            question=question,
            response=response,
            tools_used=tools_used or [],
            confidence=confidence,
            response_time_ms=response_time_ms,
            metadata=metadata or {},
            user_id=user_id,
            session_id=session_id,
            status=status,
            error_message=error_message,
            completed_at=datetime.now(),
        )

        return self._write_event(event)

    async def log_conversation_async(
        self,
        conversation_id: int,
        question: str,
        response: str,
        tools_used: list[str] | None = None,
        confidence: float | None = None,
        response_time_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: int = 1,
        session_id: str | None = None,
        status: str = "completed",
        error_message: str | None = None,
    ) -> str | None:
        """
        Log a conversation event asynchronously (non-blocking).

        Returns the message_id if successful, None otherwise.
        """
        if not self.enabled:
            return None

        event = ConversationEvent(
            conversation_id=conversation_id,
            question=question,
            response=response,
            tools_used=tools_used or [],
            confidence=confidence,
            response_time_ms=response_time_ms,
            metadata=metadata or {},
            user_id=user_id,
            session_id=session_id,
            status=status,
            error_message=error_message,
            completed_at=datetime.now(),
        )

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._write_event, event)

    def _write_event(self, event: ConversationEvent) -> str | None:
        """Write a single event to the database."""
        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                logger.warning("No database connection available")
                return None

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversation_analytics (
                        conversation_id,
                        user_id,
                        message_id,
                        question,
                        response,
                        tools_used,
                        confidence,
                        response_time_ms,
                        started_at,
                        completed_at,
                        metadata,
                        session_id,
                        status,
                        error_message
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING id
                """,
                    (
                        event.conversation_id,
                        event.user_id,
                        event.message_id,
                        event.question,
                        event.response,
                        event.tools_used,
                        event.confidence,
                        event.response_time_ms,
                        event.started_at,
                        event.completed_at,
                        Json(event.metadata),
                        event.session_id,
                        event.status,
                        event.error_message,
                    ),
                )

                cur.fetchone()
                conn.commit()

                logger.debug(f"Logged conversation event: {event.message_id}")
                return event.message_id

        except Exception as e:
            logger.error(f"Failed to log conversation: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            self._return_connection(conn)

    def get_recent_analytics(self, hours: int = 24) -> dict[str, Any]:
        """Get analytics summary for recent conversations."""
        if not self.enabled:
            return {"error": "Analytics disabled"}

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return {"error": "No database connection"}

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_messages,
                        COUNT(DISTINCT conversation_id) as unique_conversations,
                        COUNT(DISTINCT user_id) as unique_users,
                        ROUND(AVG(confidence)::numeric, 3) as avg_confidence,
                        ROUND(AVG(response_time_ms)::numeric, 0) as avg_response_time_ms,
                        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
                        SUM(CASE WHEN confidence >= 0.7 THEN 1 ELSE 0 END) as high_confidence,
                        SUM(CASE WHEN confidence >= 0.4 AND confidence < 0.7 THEN 1 ELSE 0 END) as medium_confidence,
                        SUM(CASE WHEN confidence < 0.4 OR confidence IS NULL THEN 1 ELSE 0 END) as low_confidence
                    FROM conversation_analytics
                    WHERE created_at > NOW() - INTERVAL '%s hours'
                """,
                    (hours,),
                )

                summary = dict(cur.fetchone())

                # Get tool usage breakdown
                cur.execute(
                    """
                    SELECT
                        tool_name,
                        COUNT(*) as usage_count
                    FROM conversation_analytics,
                         LATERAL unnest(tools_used) as tool_name
                    WHERE created_at > NOW() - INTERVAL '%s hours'
                    GROUP BY tool_name
                    ORDER BY usage_count DESC
                    LIMIT 20
                """,
                    (hours,),
                )

                summary["tool_usage"] = {
                    row["tool_name"]: row["usage_count"] for row in cur.fetchall()
                }

                return summary

        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {"error": str(e)}
        finally:
            self._return_connection(conn)

    def get_low_confidence_conversations(
        self, threshold: float = 0.4, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get recent conversations with low confidence for review."""
        if not self.enabled:
            return []

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return []

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        conversation_id,
                        question,
                        response,
                        tools_used,
                        confidence,
                        response_time_ms,
                        created_at
                    FROM conversation_analytics
                    WHERE confidence < %s OR confidence IS NULL
                    ORDER BY created_at DESC
                    LIMIT %s
                """,
                    (threshold, limit),
                )

                return [dict(row) for row in cur.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get low confidence conversations: {e}")
            return []
        finally:
            self._return_connection(conn)

    def search_conversations(
        self,
        query: str | None = None,
        conversation_id: int | None = None,
        min_confidence: float | None = None,
        max_confidence: float | None = None,
        tools_filter: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Search and filter conversation analytics."""
        if not self.enabled:
            return []

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return []

            conditions = []
            params = []

            if query:
                conditions.append(
                    "to_tsvector('english', question) @@ plainto_tsquery('english', %s)"
                )
                params.append(query)

            if conversation_id:
                conditions.append("conversation_id = %s")
                params.append(conversation_id)

            if min_confidence is not None:
                conditions.append("confidence >= %s")
                params.append(min_confidence)

            if max_confidence is not None:
                conditions.append("confidence <= %s")
                params.append(max_confidence)

            if tools_filter:
                conditions.append("tools_used && %s")
                params.append(tools_filter)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            params.extend([limit, offset])

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT
                        id,
                        conversation_id,
                        user_id,
                        question,
                        response,
                        tools_used,
                        confidence,
                        response_time_ms,
                        status,
                        created_at,
                        metadata
                    FROM conversation_analytics
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """,
                    params,
                )

                return [dict(row) for row in cur.fetchall()]

        except Exception as e:
            logger.error(f"Failed to search conversations: {e}")
            return []
        finally:
            self._return_connection(conn)

    def export_conversations(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        format: str = "json",
    ) -> list[dict[str, Any]]:
        """Export conversations for analysis."""
        if not self.enabled:
            return []

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return []

            conditions = []
            params = []

            if start_date:
                conditions.append("created_at >= %s")
                params.append(start_date)

            if end_date:
                conditions.append("created_at <= %s")
                params.append(end_date)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT
                        id,
                        conversation_id,
                        user_id,
                        message_id,
                        question,
                        response,
                        tools_used,
                        confidence,
                        response_time_ms,
                        status,
                        error_message,
                        metadata,
                        created_at
                    FROM conversation_analytics
                    WHERE {where_clause}
                    ORDER BY created_at ASC
                """,
                    params,
                )

                results = [dict(row) for row in cur.fetchall()]

                # Convert datetime objects to ISO strings for JSON serialization
                for row in results:
                    if row.get("created_at"):
                        row["created_at"] = row["created_at"].isoformat()

                return results

        except Exception as e:
            logger.error(f"Failed to export conversations: {e}")
            return []
        finally:
            self._return_connection(conn)


# Singleton instance
_analytics_service = None


def get_conversation_analytics_service() -> ConversationAnalyticsService:
    """Get the singleton conversation analytics service instance."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = ConversationAnalyticsService()
    return _analytics_service
