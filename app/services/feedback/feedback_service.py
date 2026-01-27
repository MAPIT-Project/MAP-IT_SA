"""
User Feedback Service

Collects and analyzes user feedback on responses
for continuous quality improvement.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class FeedbackSubmission:
    """User feedback submission."""

    conversation_id: str
    rating: int  # 1-5
    feedback_type: str  # 'helpful', 'not_helpful', 'incorrect', 'incomplete', 'other'
    feedback_text: str | None = None
    message_id: str | None = None
    query_text: str | None = None
    response_text: str | None = None
    tools_used: list[str] | None = None
    query_type: str | None = None
    response_time_ms: int | None = None


class FeedbackService:
    """Service for managing user feedback."""

    _instance = None
    _pool = None

    def __new__(cls):
        """Singleton pattern for shared connection pool."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the feedback service."""
        if self._initialized:
            return

        self.db_url = os.getenv("DATABASE_URL")
        self.enabled = bool(self.db_url)

        if self.enabled:
            try:
                self._init_pool()
                logger.info("✅ Feedback service initialized")
            except Exception as e:
                logger.warning(f"⚠️ Feedback service disabled: {e}")
                self.enabled = False

        self._initialized = True

    def _init_pool(self):
        """Initialize database connection pool."""
        if FeedbackService._pool is None:
            FeedbackService._pool = pool.SimpleConnectionPool(1, 5, self.db_url)

    def _get_connection(self):
        """Get a connection from the pool."""
        if FeedbackService._pool:
            return FeedbackService._pool.getconn()
        return None

    def _put_connection(self, conn):
        """Return a connection to the pool."""
        if FeedbackService._pool and conn:
            FeedbackService._pool.putconn(conn)

    async def submit_feedback(self, feedback: FeedbackSubmission) -> dict[str, Any]:
        """Submit user feedback."""
        if not self.enabled:
            return {"success": False, "error": "Feedback service not available"}

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return {"success": False, "error": "Database connection failed"}

            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO response_feedback
                (conversation_id, message_id, query_text, response_text,
                 rating, feedback_type, feedback_text, tools_used,
                 query_type, response_time_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    feedback.conversation_id,
                    feedback.message_id,
                    feedback.query_text,
                    feedback.response_text,
                    feedback.rating,
                    feedback.feedback_type,
                    feedback.feedback_text,
                    feedback.tools_used,
                    feedback.query_type,
                    feedback.response_time_ms,
                ),
            )

            result = cursor.fetchone()
            conn.commit()
            cursor.close()

            logger.info(f"✅ Feedback submitted: id={result[0]}, rating={feedback.rating}")
            return {
                "success": True,
                "feedback_id": result[0],
                "message": "Thank you for your feedback!",
            }

        except Exception as e:
            logger.error(f"Failed to submit feedback: {e}")
            if conn:
                conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            self._put_connection(conn)

    async def get_feedback_summary(self, days: int = 30) -> dict[str, Any]:
        """Get feedback summary for last N days."""
        if not self.enabled:
            return {"error": "Feedback service not available"}

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return {"error": "Database connection failed"}

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Overall metrics
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_feedback,
                    ROUND(AVG(rating)::numeric, 2) as avg_rating,
                    SUM(CASE WHEN feedback_type = 'helpful' THEN 1 ELSE 0 END) as helpful,
                    SUM(CASE WHEN feedback_type = 'not_helpful' THEN 1 ELSE 0 END) as not_helpful,
                    SUM(CASE WHEN feedback_type = 'incorrect' THEN 1 ELSE 0 END) as incorrect,
                    SUM(CASE WHEN feedback_type = 'incomplete' THEN 1 ELSE 0 END) as incomplete,
                    SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive_ratings,
                    SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as negative_ratings
                FROM response_feedback
                WHERE created_at > NOW() - (%s || ' days')::INTERVAL
            """,
                (days,),
            )

            summary = cursor.fetchone()

            # Rating distribution
            cursor.execute(
                """
                SELECT rating, COUNT(*) as count
                FROM response_feedback
                WHERE created_at > NOW() - (%s || ' days')::INTERVAL
                  AND rating IS NOT NULL
                GROUP BY rating
                ORDER BY rating
            """,
                (days,),
            )

            rating_dist = {str(r["rating"]): r["count"] for r in cursor.fetchall()}

            # Tool-specific feedback
            cursor.execute(
                """
                SELECT
                    unnest(tools_used) as tool_name,
                    COUNT(*) as usage_count,
                    ROUND(AVG(rating)::numeric, 2) as avg_rating
                FROM response_feedback
                WHERE created_at > NOW() - (%s || ' days')::INTERVAL
                  AND tools_used IS NOT NULL
                GROUP BY unnest(tools_used)
                ORDER BY usage_count DESC
                LIMIT 10
            """,
                (days,),
            )

            tool_feedback = [dict(r) for r in cursor.fetchall()]

            # Recent low-rated responses (for review)
            cursor.execute(
                """
                SELECT
                    conversation_id,
                    query_text,
                    rating,
                    feedback_type,
                    feedback_text,
                    created_at
                FROM response_feedback
                WHERE rating <= 2
                  AND created_at > NOW() - (%s || ' days')::INTERVAL
                ORDER BY created_at DESC
                LIMIT 10
            """,
                (days,),
            )

            low_rated = [dict(r) for r in cursor.fetchall()]

            cursor.close()

            total = summary["total_feedback"] or 0
            satisfaction_rate = 0
            if total > 0:
                satisfaction_rate = round((summary["positive_ratings"] or 0) / total * 100, 1)

            return {
                "period_days": days,
                "total_feedback": total,
                "avg_rating": float(summary["avg_rating"] or 0),
                "satisfaction_rate": satisfaction_rate,
                "by_type": {
                    "helpful": summary["helpful"] or 0,
                    "not_helpful": summary["not_helpful"] or 0,
                    "incorrect": summary["incorrect"] or 0,
                    "incomplete": summary["incomplete"] or 0,
                },
                "rating_distribution": rating_dist,
                "tool_feedback": tool_feedback,
                "recent_low_rated": low_rated,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get feedback summary: {e}")
            return {"error": str(e)}
        finally:
            self._put_connection(conn)

    async def get_conversation_feedback(self, conversation_id: str) -> list[dict]:
        """Get all feedback for a specific conversation."""
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
                    id, rating, feedback_type, feedback_text,
                    tools_used, created_at
                FROM response_feedback
                WHERE conversation_id = %s
                ORDER BY created_at DESC
            """,
                (conversation_id,),
            )

            results = [dict(r) for r in cursor.fetchall()]
            cursor.close()
            return results

        except Exception as e:
            logger.error(f"Failed to get conversation feedback: {e}")
            return []
        finally:
            self._put_connection(conn)

    async def get_improvement_suggestions(self) -> dict[str, Any]:
        """Analyze feedback to generate improvement suggestions."""
        if not self.enabled:
            return {"error": "Feedback service not available"}

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return {"error": "Database connection failed"}

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Tools with poor ratings
            cursor.execute(
                """
                SELECT
                    unnest(tools_used) as tool_name,
                    COUNT(*) as total_uses,
                    ROUND(AVG(rating)::numeric, 2) as avg_rating,
                    SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as low_ratings
                FROM response_feedback
                WHERE tools_used IS NOT NULL
                  AND created_at > NOW() - INTERVAL '30 days'
                GROUP BY unnest(tools_used)
                HAVING AVG(rating) < 3.5 AND COUNT(*) >= 5
                ORDER BY avg_rating
            """
            )

            underperforming_tools = [dict(r) for r in cursor.fetchall()]

            # Common feedback patterns (from feedback_text)
            cursor.execute(
                """
                SELECT
                    feedback_type,
                    COUNT(*) as count
                FROM response_feedback
                WHERE feedback_type IS NOT NULL
                  AND created_at > NOW() - INTERVAL '30 days'
                GROUP BY feedback_type
                ORDER BY count DESC
            """
            )

            issue_patterns = [dict(r) for r in cursor.fetchall()]

            cursor.close()

            suggestions = []

            # Generate suggestions based on data
            for tool in underperforming_tools:
                suggestions.append(
                    {
                        "type": "tool_improvement",
                        "priority": "high" if tool["avg_rating"] < 3.0 else "medium",
                        "message": f"Tool '{tool['tool_name']}' has low satisfaction (avg: {tool['avg_rating']}). Review tool implementation.",
                        "data": tool,
                    }
                )

            # Check for incomplete issues
            incomplete_issues = next(
                (p for p in issue_patterns if p["feedback_type"] == "incomplete"), None
            )
            if incomplete_issues and incomplete_issues["count"] > 10:
                suggestions.append(
                    {
                        "type": "completeness",
                        "priority": "medium",
                        "message": f"High 'incomplete' feedback ({incomplete_issues['count']}). Consider expanding search depth.",
                        "data": incomplete_issues,
                    }
                )

            return {
                "suggestions": suggestions,
                "underperforming_tools": underperforming_tools,
                "issue_patterns": issue_patterns,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get improvement suggestions: {e}")
            return {"error": str(e)}
        finally:
            self._put_connection(conn)


# Singleton instance
_feedback_service = None


def get_feedback_service() -> FeedbackService:
    """Get the singleton feedback service instance."""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService()
    return _feedback_service
