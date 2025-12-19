"""
Health Check Routes for MAP-IT

Provides comprehensive health checks for all services including:
- PostgreSQL database
- Neo4j graph database
- Redis cache
- AI providers (Gemini)
- Embedding service

Supports Kubernetes readiness/liveness probes.
"""

from fastapi import APIRouter, Response
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
import logging
import os
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["health"])


# ============================================================================
# HEALTH CHECK RESULT TYPES
# ============================================================================

class ServiceHealth:
    """Represents the health status of a single service."""

    def __init__(
        self,
        name: str,
        status: str,  # "healthy", "degraded", "unhealthy"
        latency_ms: Optional[float] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.status = status
        self.latency_ms = latency_ms
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "status": self.status,
        }
        if self.latency_ms is not None:
            result["latency_ms"] = round(self.latency_ms, 2)
        if self.message:
            result["message"] = self.message
        if self.details:
            result["details"] = self.details
        return result


# ============================================================================
# SERVICE HEALTH CHECKS
# ============================================================================

async def check_postgres() -> ServiceHealth:
    """Check PostgreSQL database connectivity and health."""
    start = time.time()
    try:
        from ..core.config import settings

        if not settings.use_local_db or not settings.database_url:
            return ServiceHealth(
                name="postgres",
                status="healthy",
                message="Not configured (disabled)"
            )

        import psycopg2

        conn = psycopg2.connect(settings.database_url, connect_timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()

        # Get connection count
        cursor.execute("""
            SELECT count(*)
            FROM pg_stat_activity
            WHERE datname = current_database()
        """)
        connection_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        latency = (time.time() - start) * 1000

        return ServiceHealth(
            name="postgres",
            status="healthy",
            latency_ms=latency,
            details={"active_connections": connection_count}
        )

    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.error(f"PostgreSQL health check failed: {e}")
        return ServiceHealth(
            name="postgres",
            status="unhealthy",
            latency_ms=latency,
            message=str(e)
        )


async def check_neo4j() -> ServiceHealth:
    """Check Neo4j graph database connectivity and health."""
    start = time.time()
    try:
        from ..core.neo4j_config import Neo4jConnection

        db = Neo4jConnection()
        if db.test_connection():
            latency = (time.time() - start) * 1000

            # Get basic stats
            try:
                stats = db.get_database_stats()
                details = {
                    "total_nodes": stats.get("total_nodes"),
                    "total_relationships": stats.get("total_relationships")
                }
            except:
                details = {}

            return ServiceHealth(
                name="neo4j",
                status="healthy",
                latency_ms=latency,
                details=details
            )
        else:
            latency = (time.time() - start) * 1000
            return ServiceHealth(
                name="neo4j",
                status="unhealthy",
                latency_ms=latency,
                message="Connection test failed"
            )

    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.error(f"Neo4j health check failed: {e}")
        return ServiceHealth(
            name="neo4j",
            status="unhealthy",
            latency_ms=latency,
            message=str(e)
        )


async def check_redis() -> ServiceHealth:
    """Check Redis cache connectivity."""
    start = time.time()
    try:
        from ..core.config import settings
        import redis

        redis_url = settings.redis_url or "redis://localhost:6379/0"

        r = redis.from_url(redis_url, socket_timeout=5)
        r.ping()

        # Get info
        info = r.info()
        latency = (time.time() - start) * 1000

        return ServiceHealth(
            name="redis",
            status="healthy",
            latency_ms=latency,
            details={
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "redis_version": info.get("redis_version")
            }
        )

    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.warning(f"Redis health check failed: {e}")
        return ServiceHealth(
            name="redis",
            status="degraded",  # Redis failure is not critical
            latency_ms=latency,
            message=str(e)
        )


async def check_gemini() -> ServiceHealth:
    """Check Gemini AI provider availability."""
    start = time.time()
    try:
        from ..core.config import settings

        if not settings.gemini_api_key:
            return ServiceHealth(
                name="gemini",
                status="healthy",
                message="Not configured"
            )

        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)

        # Quick model test - just list models to verify API key works
        models = list(genai.list_models())
        latency = (time.time() - start) * 1000

        return ServiceHealth(
            name="gemini",
            status="healthy",
            latency_ms=latency,
            details={"available_models": len(models)}
        )

    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.error(f"Gemini health check failed: {e}")
        return ServiceHealth(
            name="gemini",
            status="unhealthy",
            latency_ms=latency,
            message=str(e)
        )


async def check_embedding_service() -> ServiceHealth:
    """Check embedding generation service availability."""
    start = time.time()
    try:
        from ..core.config import settings

        if not settings.vector_search_enabled or not settings.effective_embedding_api_key:
            return ServiceHealth(
                name="embeddings",
                status="healthy",
                message="Not configured"
            )

        from ..services.embedding_service import EmbeddingService

        embedder = EmbeddingService()
        if embedder.test_embedding_generation():
            latency = (time.time() - start) * 1000
            return ServiceHealth(
                name="embeddings",
                status="healthy",
                latency_ms=latency,
                details={"model": settings.embedding_model}
            )
        else:
            latency = (time.time() - start) * 1000
            return ServiceHealth(
                name="embeddings",
                status="degraded",
                latency_ms=latency,
                message="Test generation failed"
            )

    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.error(f"Embedding service health check failed: {e}")
        return ServiceHealth(
            name="embeddings",
            status="degraded",  # Embedding failure allows fallback to keyword search
            latency_ms=latency,
            message=str(e)
        )


async def check_supabase() -> ServiceHealth:
    """Check Supabase connection."""
    start = time.time()
    try:
        from ..core.config import settings

        if not settings.use_supabase:
            return ServiceHealth(
                name="supabase",
                status="healthy",
                message="Not configured"
            )

        from ..services.supabase_client import SupabaseVectorStore

        supabase = SupabaseVectorStore()
        if supabase.test_connection():
            latency = (time.time() - start) * 1000
            return ServiceHealth(
                name="supabase",
                status="healthy",
                latency_ms=latency
            )
        else:
            latency = (time.time() - start) * 1000
            return ServiceHealth(
                name="supabase",
                status="unhealthy",
                latency_ms=latency,
                message="Connection test failed"
            )

    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.error(f"Supabase health check failed: {e}")
        return ServiceHealth(
            name="supabase",
            status="unhealthy",
            latency_ms=latency,
            message=str(e)
        )


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("")
@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check for all services.

    Returns detailed status of all dependencies including:
    - PostgreSQL (critical)
    - Neo4j (critical for statistics)
    - Redis (cache, non-critical)
    - Gemini AI (critical for responses)
    - Embedding service (non-critical, fallback available)
    - Supabase (if configured)

    Response includes overall status:
    - "healthy": All services operational
    - "degraded": Some non-critical services unavailable
    - "unhealthy": Critical services unavailable
    """
    from ..core.config import settings

    # Run all health checks in parallel
    checks = await asyncio.gather(
        check_postgres(),
        check_neo4j(),
        check_redis(),
        check_gemini(),
        check_embedding_service(),
        check_supabase(),
        return_exceptions=True
    )

    # Process results
    services = {}
    for check in checks:
        if isinstance(check, Exception):
            logger.error(f"Health check raised exception: {check}")
            continue
        if isinstance(check, ServiceHealth):
            services[check.name] = check.to_dict()

    # Determine overall status
    # Critical services: postgres (if enabled), gemini
    critical_services = []
    if settings.use_local_db:
        critical_services.append("postgres")
    if settings.gemini_api_key:
        critical_services.append("gemini")

    critical_healthy = all(
        services.get(svc, {}).get("status") in ["healthy", "Not configured"]
        for svc in critical_services
    )

    all_healthy = all(
        s.get("status") == "healthy"
        for s in services.values()
    )

    if all_healthy:
        overall_status = "healthy"
    elif critical_healthy:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "services": services,
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": "docker" if settings.docker_env else "local"
    }


@router.get("/ready")
async def readiness_check(response: Response) -> Dict[str, Any]:
    """
    Kubernetes readiness probe.

    Checks if the application can serve traffic.
    Only checks critical dependencies (PostgreSQL if enabled).

    Returns 200 if ready, 503 if not ready.
    """
    from ..core.config import settings

    ready = True
    checks = {}

    # Check PostgreSQL if enabled
    if settings.use_local_db:
        postgres_health = await check_postgres()
        checks["postgres"] = postgres_health.status
        if postgres_health.status == "unhealthy":
            ready = False

    # Check at least one AI provider
    if settings.gemini_api_key:
        gemini_health = await check_gemini()
        checks["gemini"] = gemini_health.status
        if gemini_health.status == "unhealthy":
            ready = False

    if not ready:
        response.status_code = 503

    return {
        "ready": ready,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes liveness probe.

    Simple check to verify the application is alive and responding.
    Does not check dependencies - only that the process is running.

    Returns 200 if alive.
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/dependencies")
async def dependencies_status() -> Dict[str, Any]:
    """
    Detailed dependency status for monitoring dashboards.

    Returns comprehensive information about each service including:
    - Connection status
    - Latency
    - Resource usage
    - Configuration details
    """
    from ..core.config import settings

    # Run all checks
    checks = await asyncio.gather(
        check_postgres(),
        check_neo4j(),
        check_redis(),
        check_gemini(),
        check_embedding_service(),
        check_supabase(),
        return_exceptions=True
    )

    dependencies = {}
    for check in checks:
        if isinstance(check, ServiceHealth):
            dependencies[check.name] = {
                **check.to_dict(),
                "critical": check.name in ["postgres", "gemini"],
                "fallback_available": check.name in ["neo4j", "redis", "embeddings"]
            }

    return {
        "dependencies": dependencies,
        "configuration": {
            "database_enabled": settings.use_local_db,
            "supabase_enabled": settings.use_supabase,
            "vector_search_enabled": settings.vector_search_enabled,
            "ai_provider": settings.default_ai_provider
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics")
async def health_metrics() -> Dict[str, Any]:
    """
    Health metrics for Prometheus/monitoring systems.

    Returns metrics in a format suitable for monitoring:
    - Service status (1=healthy, 0.5=degraded, 0=unhealthy)
    - Latencies
    - Resource counts
    """
    # Run quick checks
    checks = await asyncio.gather(
        check_postgres(),
        check_neo4j(),
        check_redis(),
        return_exceptions=True
    )

    metrics = {
        "mapit_health_status": 1.0,  # Will be updated based on checks
        "services": {}
    }

    status_values = {"healthy": 1.0, "degraded": 0.5, "unhealthy": 0.0}

    overall_min = 1.0
    for check in checks:
        if isinstance(check, ServiceHealth):
            status_value = status_values.get(check.status, 0.0)
            overall_min = min(overall_min, status_value)
            metrics["services"][check.name] = {
                "status": status_value,
                "latency_ms": check.latency_ms or 0
            }

    metrics["mapit_health_status"] = overall_min
    metrics["timestamp"] = datetime.utcnow().isoformat()

    return metrics
