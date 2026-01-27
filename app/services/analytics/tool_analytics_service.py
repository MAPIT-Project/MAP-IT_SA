"""
Tool Usage Analytics Service

Tracks tool usage patterns, performance, and quality metrics
for optimization and monitoring.
"""

import hashlib
import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class ToolUsageEvent:
    """Single tool usage event."""

    tool_name: str
    parameters: dict[str, Any]
    execution_time_ms: int
    success: bool
    error_message: str | None = None
    result_count: int | None = None
    result_quality_score: float | None = None
    conversation_id: str | None = None
    query_hash: str | None = None
    speculative: bool = False
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ToolAnalyticsService:
    """Service for tracking and analyzing tool usage."""

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
        self.buffer: list[ToolUsageEvent] = []
        self.buffer_size = 50  # Batch write every 50 events
        self.flush_interval = 60  # Or every 60 seconds
        self.last_flush = datetime.now()
        self.enabled = bool(self.db_url)

        # In-memory metrics for real-time stats
        self.session_metrics = defaultdict(
            lambda: {"calls": 0, "successes": 0, "total_time_ms": 0, "speculative_hits": 0}
        )

        if self.enabled:
            try:
                self._init_pool()
                logger.info("✅ Tool analytics service initialized")
            except Exception as e:
                logger.warning(f"⚠️ Tool analytics service disabled: {e}")
                self.enabled = False

        self._initialized = True

    def _init_pool(self):
        """Initialize database connection pool."""
        if ToolAnalyticsService._pool is None:
            ToolAnalyticsService._pool = pool.SimpleConnectionPool(1, 5, self.db_url)

    def _get_connection(self):
        """Get a connection from the pool."""
        if ToolAnalyticsService._pool:
            return ToolAnalyticsService._pool.getconn()
        return None

    def _put_connection(self, conn):
        """Return a connection to the pool."""
        if ToolAnalyticsService._pool and conn:
            ToolAnalyticsService._pool.putconn(conn)

    async def track_tool_usage(self, event: ToolUsageEvent):
        """Track a tool usage event."""
        if not self.enabled:
            return

        # Update in-memory metrics
        self.session_metrics[event.tool_name]["calls"] += 1
        if event.success:
            self.session_metrics[event.tool_name]["successes"] += 1
        self.session_metrics[event.tool_name]["total_time_ms"] += event.execution_time_ms
        if event.speculative:
            self.session_metrics[event.tool_name]["speculative_hits"] += 1

        # Buffer for batch write
        self.buffer.append(event)

        # Flush if buffer full or interval elapsed
        should_flush = (
            len(self.buffer) >= self.buffer_size
            or (datetime.now() - self.last_flush).seconds >= self.flush_interval
        )

        if should_flush:
            await self._flush_buffer()

    async def _flush_buffer(self):
        """Flush buffered events to database."""
        if not self.buffer or not self.enabled:
            return

        events = self.buffer.copy()
        self.buffer.clear()
        self.last_flush = datetime.now()

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return

            cursor = conn.cursor()

            # Batch insert
            insert_sql = """
                INSERT INTO tool_usage_analytics
                (timestamp, conversation_id, query_hash, tool_name, parameters,
                 execution_time_ms, success, error_message, result_count,
                 result_quality_score, speculative)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            for event in events:
                cursor.execute(
                    insert_sql,
                    (
                        event.timestamp,
                        event.conversation_id,
                        event.query_hash,
                        event.tool_name,
                        json.dumps(event.parameters) if event.parameters else None,
                        event.execution_time_ms,
                        event.success,
                        event.error_message,
                        event.result_count,
                        event.result_quality_score,
                        event.speculative,
                    ),
                )

            conn.commit()
            cursor.close()
            logger.debug(f"📊 Flushed {len(events)} tool usage events to database")

        except Exception as e:
            logger.error(f"Failed to flush analytics: {e}")
            if conn:
                conn.rollback()
        finally:
            self._put_connection(conn)

    async def track_tool_sequence(self, tools_used: list[str], total_time_ms: int, success: bool):
        """Track a sequence of tools used together."""
        if not self.enabled or len(tools_used) < 2:
            return

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return

            cursor = conn.cursor()

            # Upsert tool combination
            cursor.execute(
                """
                INSERT INTO tool_combination_analytics
                (tool_sequence, occurrence_count, avg_total_time_ms, success_rate, last_seen)
                VALUES (%s, 1, %s, %s, NOW())
                ON CONFLICT (tool_sequence)
                DO UPDATE SET
                    occurrence_count = tool_combination_analytics.occurrence_count + 1,
                    avg_total_time_ms = (
                        tool_combination_analytics.avg_total_time_ms *
                        tool_combination_analytics.occurrence_count + EXCLUDED.avg_total_time_ms
                    ) / (tool_combination_analytics.occurrence_count + 1),
                    success_rate = (
                        tool_combination_analytics.success_rate *
                        tool_combination_analytics.occurrence_count + EXCLUDED.success_rate
                    ) / (tool_combination_analytics.occurrence_count + 1),
                    last_seen = NOW()
            """,
                (tools_used, total_time_ms, 1.0 if success else 0.0),
            )

            conn.commit()
            cursor.close()

        except Exception as e:
            logger.error(f"Failed to track tool sequence: {e}")
            if conn:
                conn.rollback()
        finally:
            self._put_connection(conn)

    def get_session_metrics(self) -> dict[str, Any]:
        """Get current session metrics (in-memory)."""
        metrics = {}
        for tool_name, data in self.session_metrics.items():
            calls = data["calls"]
            metrics[tool_name] = {
                "total_calls": calls,
                "successful_calls": data["successes"],
                "success_rate": (data["successes"] / calls * 100) if calls > 0 else 0,
                "avg_time_ms": (data["total_time_ms"] / calls) if calls > 0 else 0,
                "speculative_hits": data["speculative_hits"],
            }
        return metrics

    def get_tool_performance(self, hours: int = 24) -> dict[str, Any]:
        """Get tool performance metrics from database."""
        if not self.enabled:
            return {"error": "Analytics not enabled"}

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return {"error": "Database connection failed"}

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                SELECT
                    tool_name,
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_calls,
                    ROUND(AVG(execution_time_ms)::numeric, 0) as avg_time_ms,
                    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms)::numeric, 0) as p95_time_ms,
                    ROUND((SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) * 100)::numeric, 1) as success_rate,
                    SUM(CASE WHEN speculative THEN 1 ELSE 0 END) as speculative_hits
                FROM tool_usage_analytics
                WHERE timestamp > NOW() - (%s || ' hours')::INTERVAL
                GROUP BY tool_name
                ORDER BY total_calls DESC
            """,
                (hours,),
            )

            results = cursor.fetchall()
            cursor.close()

            return {
                "period_hours": hours,
                "tools": [dict(r) for r in results],
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get tool performance: {e}")
            return {"error": str(e)}
        finally:
            self._put_connection(conn)

    def get_popular_tool_combinations(self, min_occurrences: int = 5) -> dict[str, Any]:
        """Get popular tool combinations."""
        if not self.enabled:
            return {"error": "Analytics not enabled"}

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return {"error": "Database connection failed"}

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                SELECT
                    tool_sequence,
                    occurrence_count,
                    ROUND(avg_total_time_ms::numeric, 0) as avg_time_ms,
                    ROUND((success_rate * 100)::numeric, 1) as success_rate,
                    last_seen
                FROM tool_combination_analytics
                WHERE occurrence_count >= %s
                ORDER BY occurrence_count DESC
                LIMIT 20
            """,
                (min_occurrences,),
            )

            results = cursor.fetchall()
            cursor.close()

            return {
                "min_occurrences": min_occurrences,
                "combinations": [dict(r) for r in results],
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get tool combinations: {e}")
            return {"error": str(e)}
        finally:
            self._put_connection(conn)

    def get_slow_tools(self, threshold_ms: int = 2000) -> list[dict]:
        """Get tools that frequently exceed performance threshold."""
        if not self.enabled:
            return []

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return []

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                SELECT
                    tool_name,
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN execution_time_ms > %s THEN 1 ELSE 0 END) as slow_calls,
                    ROUND((SUM(CASE WHEN execution_time_ms > %s THEN 1 ELSE 0 END)::float / COUNT(*) * 100)::numeric, 1) as slow_pct,
                    ROUND(AVG(execution_time_ms)::numeric, 0) as avg_time_ms,
                    ROUND(MAX(execution_time_ms)::numeric, 0) as max_time_ms
                FROM tool_usage_analytics
                WHERE timestamp > NOW() - INTERVAL '7 days'
                GROUP BY tool_name
                HAVING SUM(CASE WHEN execution_time_ms > %s THEN 1 ELSE 0 END) > 0
                ORDER BY slow_pct DESC
            """,
                (threshold_ms, threshold_ms, threshold_ms),
            )

            results = cursor.fetchall()
            cursor.close()

            return [dict(r) for r in results]

        except Exception as e:
            logger.error(f"Failed to get slow tools: {e}")
            return []
        finally:
            self._put_connection(conn)

    async def close(self):
        """Flush remaining events and close."""
        await self._flush_buffer()

    @staticmethod
    def hash_query(query: str) -> str:
        """Generate a hash for a query string."""
        return hashlib.sha256(query.encode()).hexdigest()[:16]


# Singleton instance
_analytics_service = None


def get_analytics_service() -> ToolAnalyticsService:
    """Get the singleton analytics service instance."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = ToolAnalyticsService()
    return _analytics_service
