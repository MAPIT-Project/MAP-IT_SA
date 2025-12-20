"""
Analytics Dashboard API Routes

Provides comprehensive analytics endpoints for monitoring system usage,
performance, and quality metrics.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

from app.services.analytics.tool_analytics_service import get_analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Database connection pool for analytics queries
_analytics_pool = None


def _get_pool():
    """Get or create the analytics database pool."""
    global _analytics_pool
    if _analytics_pool is None:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            try:
                _analytics_pool = pool.SimpleConnectionPool(1, 5, db_url)
            except Exception as e:
                logger.error(f"Failed to create analytics pool: {e}")
    return _analytics_pool


def _get_connection():
    """Get a connection from the pool."""
    p = _get_pool()
    if p:
        return p.getconn()
    return None


def _put_connection(conn):
    """Return a connection to the pool."""
    p = _get_pool()
    if p and conn:
        p.putconn(conn)


# Response Models
class UsageMetrics(BaseModel):
    total_queries: int
    unique_conversations: int
    queries_per_day: Dict[str, int]
    peak_hour: int
    avg_queries_per_conversation: float


class PerformanceMetrics(BaseModel):
    avg_response_time_ms: float
    p95_response_time_ms: float
    error_rate: float
    tool_success_rates: Dict[str, float]


class ContentMetrics(BaseModel):
    top_queries: List[Dict[str, Any]]
    top_tools: List[Dict[str, Any]]
    popular_clusters: List[Dict[str, Any]]
    popular_countries: List[Dict[str, Any]]


class ProposalMetrics(BaseModel):
    sessions_created: int
    sections_generated: int
    avg_completion_rate: float
    exports_generated: int


class FeedbackMetrics(BaseModel):
    avg_rating: float
    rating_distribution: Dict[int, int]
    total_feedback_count: int
    improvement_suggestions: List[str]


class AnalyticsOverview(BaseModel):
    period: Dict[str, Any]
    usage: UsageMetrics
    performance: PerformanceMetrics
    content: ContentMetrics
    proposals: ProposalMetrics
    feedback: FeedbackMetrics


class TrendPoint(BaseModel):
    date: str
    value: float


class TrendResponse(BaseModel):
    metric: str
    granularity: str
    data: List[TrendPoint]


@router.get("/overview")
async def get_analytics_overview(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
) -> Dict[str, Any]:
    """
    Get comprehensive system analytics overview.

    Returns usage, performance, content, proposal, and feedback metrics
    for the specified time period.
    """
    conn = None
    try:
        conn = _get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Usage metrics
        usage = await _get_usage_metrics(cursor, start_date, days)

        # Performance metrics
        performance = await _get_performance_metrics(cursor, start_date)

        # Content metrics
        content = await _get_content_metrics(cursor, start_date)

        # Proposal metrics
        proposals = await _get_proposal_metrics(cursor, start_date)

        # Feedback metrics
        feedback = await _get_feedback_metrics(cursor, start_date)

        cursor.close()

        return {
            "period": {
                "days": days,
                "start_date": start_date.isoformat(),
                "end_date": datetime.now(timezone.utc).isoformat()
            },
            "usage": usage,
            "performance": performance,
            "content": content,
            "proposals": proposals,
            "feedback": feedback,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analytics overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _put_connection(conn)


@router.get("/tools")
async def get_tool_analytics(
    hours: int = Query(24, ge=1, le=720, description="Hours to analyze")
) -> Dict[str, Any]:
    """
    Get detailed tool usage analytics.

    Includes per-tool performance metrics, success rates, and latency distributions.
    """
    analytics_service = get_analytics_service()

    # Get performance from analytics service
    performance = analytics_service.get_tool_performance(hours)

    # Get slow tools
    slow_tools = analytics_service.get_slow_tools(threshold_ms=2000)

    # Get tool combinations
    combinations = analytics_service.get_popular_tool_combinations(min_occurrences=3)

    # Get session metrics (in-memory)
    session_metrics = analytics_service.get_session_metrics()

    return {
        "period_hours": hours,
        "tool_performance": performance.get("tools", []),
        "slow_tools": slow_tools,
        "popular_combinations": combinations.get("combinations", []),
        "current_session": session_metrics,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/trends")
async def get_metric_trends(
    metric: str = Query(..., description="Metric to trend: queries, response_time, error_rate, feedback"),
    granularity: str = Query("day", pattern="^(hour|day|week|month)$", description="Time granularity"),
    days: int = Query(90, ge=1, le=365, description="Number of days")
) -> Dict[str, Any]:
    """
    Get metric trends over time.

    Supports various metrics with configurable time granularity.
    """
    conn = None
    try:
        conn = _get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Map granularity to PostgreSQL date_trunc
        granularity_map = {
            "hour": "hour",
            "day": "day",
            "week": "week",
            "month": "month"
        }

        trunc = granularity_map.get(granularity, "day")

        if metric == "queries":
            cursor.execute("""
                SELECT
                    DATE_TRUNC(%s, timestamp) as period,
                    COUNT(*) as value
                FROM tool_usage_analytics
                WHERE timestamp > %s
                GROUP BY period
                ORDER BY period
            """, (trunc, start_date))

        elif metric == "response_time":
            cursor.execute("""
                SELECT
                    DATE_TRUNC(%s, timestamp) as period,
                    ROUND(AVG(execution_time_ms)::numeric, 0) as value
                FROM tool_usage_analytics
                WHERE timestamp > %s
                GROUP BY period
                ORDER BY period
            """, (trunc, start_date))

        elif metric == "error_rate":
            cursor.execute("""
                SELECT
                    DATE_TRUNC(%s, timestamp) as period,
                    ROUND((SUM(CASE WHEN NOT success THEN 1 ELSE 0 END)::float /
                           NULLIF(COUNT(*), 0) * 100)::numeric, 2) as value
                FROM tool_usage_analytics
                WHERE timestamp > %s
                GROUP BY period
                ORDER BY period
            """, (trunc, start_date))

        elif metric == "feedback":
            cursor.execute("""
                SELECT
                    DATE_TRUNC(%s, created_at) as period,
                    ROUND(AVG(rating)::numeric, 2) as value
                FROM response_feedback
                WHERE created_at > %s
                GROUP BY period
                ORDER BY period
            """, (trunc, start_date))
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown metric: {metric}. Supported: queries, response_time, error_rate, feedback"
            )

        results = cursor.fetchall()
        cursor.close()

        data = [
            {
                "date": row["period"].isoformat() if row["period"] else None,
                "value": float(row["value"]) if row["value"] else 0
            }
            for row in results
        ]

        return {
            "metric": metric,
            "granularity": granularity,
            "days": days,
            "data": data,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _put_connection(conn)


@router.get("/queries/popular")
async def get_popular_queries(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """Get most popular query patterns."""
    conn = None
    try:
        conn = _get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        cursor.execute("""
            SELECT
                query_hash,
                COUNT(*) as occurrence_count,
                ROUND(AVG(execution_time_ms)::numeric, 0) as avg_time_ms,
                ROUND((SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) * 100)::numeric, 1) as success_rate
            FROM tool_usage_analytics
            WHERE timestamp > %s AND query_hash IS NOT NULL
            GROUP BY query_hash
            ORDER BY occurrence_count DESC
            LIMIT %s
        """, (start_date, limit))

        results = cursor.fetchall()
        cursor.close()

        return {
            "period_days": days,
            "popular_queries": [dict(r) for r in results],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get popular queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _put_connection(conn)


@router.get("/health")
async def analytics_health() -> Dict[str, Any]:
    """Check analytics service health."""
    analytics_service = get_analytics_service()

    return {
        "status": "healthy" if analytics_service.enabled else "disabled",
        "buffer_size": len(analytics_service.buffer),
        "last_flush": analytics_service.last_flush.isoformat(),
        "session_tools_tracked": len(analytics_service.session_metrics),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Helper functions
async def _get_usage_metrics(cursor, start_date: datetime, days: int) -> Dict[str, Any]:
    """Get usage metrics from database."""
    try:
        # Total queries
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM tool_usage_analytics
            WHERE timestamp > %s
        """, (start_date,))
        total = cursor.fetchone()["total"] or 0

        # Unique conversations
        cursor.execute("""
            SELECT COUNT(DISTINCT conversation_id) as unique_convos
            FROM tool_usage_analytics
            WHERE timestamp > %s AND conversation_id IS NOT NULL
        """, (start_date,))
        unique_convos = cursor.fetchone()["unique_convos"] or 0

        # Queries per day
        cursor.execute("""
            SELECT
                DATE(timestamp) as day,
                COUNT(*) as count
            FROM tool_usage_analytics
            WHERE timestamp > %s
            GROUP BY day
            ORDER BY day
        """, (start_date,))
        queries_per_day = {
            str(row["day"]): row["count"]
            for row in cursor.fetchall()
        }

        # Peak hour
        cursor.execute("""
            SELECT
                EXTRACT(HOUR FROM timestamp) as hour,
                COUNT(*) as count
            FROM tool_usage_analytics
            WHERE timestamp > %s
            GROUP BY hour
            ORDER BY count DESC
            LIMIT 1
        """, (start_date,))
        peak_result = cursor.fetchone()
        peak_hour = int(peak_result["hour"]) if peak_result else 0

        return {
            "total_queries": total,
            "unique_conversations": unique_convos,
            "queries_per_day": queries_per_day,
            "peak_hour": peak_hour,
            "avg_queries_per_conversation": round(total / max(unique_convos, 1), 2)
        }
    except Exception as e:
        logger.error(f"Failed to get usage metrics: {e}")
        return {
            "total_queries": 0,
            "unique_conversations": 0,
            "queries_per_day": {},
            "peak_hour": 0,
            "avg_queries_per_conversation": 0
        }


async def _get_performance_metrics(cursor, start_date: datetime) -> Dict[str, Any]:
    """Get performance metrics from database."""
    try:
        cursor.execute("""
            SELECT
                ROUND(AVG(execution_time_ms)::numeric, 0) as avg_time,
                ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms)::numeric, 0) as p95_time,
                ROUND((SUM(CASE WHEN NOT success THEN 1 ELSE 0 END)::float /
                       NULLIF(COUNT(*), 0) * 100)::numeric, 2) as error_rate
            FROM tool_usage_analytics
            WHERE timestamp > %s
        """, (start_date,))
        result = cursor.fetchone()

        # Tool success rates
        cursor.execute("""
            SELECT
                tool_name,
                ROUND((SUM(CASE WHEN success THEN 1 ELSE 0 END)::float /
                       NULLIF(COUNT(*), 0) * 100)::numeric, 1) as success_rate
            FROM tool_usage_analytics
            WHERE timestamp > %s
            GROUP BY tool_name
        """, (start_date,))
        tool_rates = {row["tool_name"]: float(row["success_rate"] or 0) for row in cursor.fetchall()}

        return {
            "avg_response_time_ms": float(result["avg_time"] or 0),
            "p95_response_time_ms": float(result["p95_time"] or 0),
            "error_rate": float(result["error_rate"] or 0),
            "tool_success_rates": tool_rates
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        return {
            "avg_response_time_ms": 0,
            "p95_response_time_ms": 0,
            "error_rate": 0,
            "tool_success_rates": {}
        }


async def _get_content_metrics(cursor, start_date: datetime) -> Dict[str, Any]:
    """Get content metrics from database."""
    try:
        # Top tools
        cursor.execute("""
            SELECT
                tool_name,
                COUNT(*) as usage_count
            FROM tool_usage_analytics
            WHERE timestamp > %s
            GROUP BY tool_name
            ORDER BY usage_count DESC
            LIMIT 10
        """, (start_date,))
        top_tools = [dict(row) for row in cursor.fetchall()]

        # Popular clusters (from parameters if available)
        cursor.execute("""
            SELECT
                parameters->>'cluster' as cluster,
                COUNT(*) as count
            FROM tool_usage_analytics
            WHERE timestamp > %s
              AND parameters IS NOT NULL
              AND parameters->>'cluster' IS NOT NULL
            GROUP BY cluster
            ORDER BY count DESC
            LIMIT 10
        """, (start_date,))
        popular_clusters = [dict(row) for row in cursor.fetchall()]

        # Popular countries
        cursor.execute("""
            SELECT
                parameters->>'country' as country,
                COUNT(*) as count
            FROM tool_usage_analytics
            WHERE timestamp > %s
              AND parameters IS NOT NULL
              AND parameters->>'country' IS NOT NULL
            GROUP BY country
            ORDER BY count DESC
            LIMIT 10
        """, (start_date,))
        popular_countries = [dict(row) for row in cursor.fetchall()]

        return {
            "top_queries": [],  # Would need query logging to implement
            "top_tools": top_tools,
            "popular_clusters": popular_clusters,
            "popular_countries": popular_countries
        }
    except Exception as e:
        logger.error(f"Failed to get content metrics: {e}")
        return {
            "top_queries": [],
            "top_tools": [],
            "popular_clusters": [],
            "popular_countries": []
        }


async def _get_proposal_metrics(cursor, start_date: datetime) -> Dict[str, Any]:
    """Get proposal metrics from database."""
    try:
        # Check if proposal tables exist
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'proposals'
            )
        """)
        if not cursor.fetchone()["exists"]:
            return {
                "sessions_created": 0,
                "sections_generated": 0,
                "avg_completion_rate": 0,
                "exports_generated": 0
            }

        cursor.execute("""
            SELECT COUNT(*) as sessions
            FROM proposals
            WHERE created_at > %s
        """, (start_date,))
        sessions = cursor.fetchone()["sessions"] or 0

        cursor.execute("""
            SELECT COUNT(*) as sections
            FROM proposal_sections
            WHERE created_at > %s
        """, (start_date,))
        sections = cursor.fetchone()["sections"] or 0

        return {
            "sessions_created": sessions,
            "sections_generated": sections,
            "avg_completion_rate": 0,  # Would need completion tracking
            "exports_generated": 0  # Would need export logging
        }
    except Exception as e:
        logger.error(f"Failed to get proposal metrics: {e}")
        return {
            "sessions_created": 0,
            "sections_generated": 0,
            "avg_completion_rate": 0,
            "exports_generated": 0
        }


async def _get_feedback_metrics(cursor, start_date: datetime) -> Dict[str, Any]:
    """Get feedback metrics from database."""
    try:
        # Check if feedback table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'response_feedback'
            )
        """)
        if not cursor.fetchone()["exists"]:
            return {
                "avg_rating": 0,
                "rating_distribution": {},
                "total_feedback_count": 0,
                "improvement_suggestions": []
            }

        cursor.execute("""
            SELECT
                ROUND(AVG(rating)::numeric, 2) as avg_rating,
                COUNT(*) as total
            FROM response_feedback
            WHERE created_at > %s
        """, (start_date,))
        result = cursor.fetchone()

        cursor.execute("""
            SELECT
                rating,
                COUNT(*) as count
            FROM response_feedback
            WHERE created_at > %s
            GROUP BY rating
            ORDER BY rating
        """, (start_date,))
        distribution = {int(row["rating"]): row["count"] for row in cursor.fetchall()}

        return {
            "avg_rating": float(result["avg_rating"] or 0),
            "rating_distribution": distribution,
            "total_feedback_count": result["total"] or 0,
            "improvement_suggestions": []  # Would need AI analysis
        }
    except Exception as e:
        logger.error(f"Failed to get feedback metrics: {e}")
        return {
            "avg_rating": 0,
            "rating_distribution": {},
            "total_feedback_count": 0,
            "improvement_suggestions": []
        }
