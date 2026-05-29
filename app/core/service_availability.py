"""
Service Availability Checker for Graceful Degradation.

Provides real-time service availability checking with caching,
enabling the agent to adapt its tool selection based on available services.

Implements Priority 1.3 from IMPROVEMENT_ROADMAP.md
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Service Definitions
# ============================================================================


class ServiceType(str, Enum):
    """Types of services that can be checked."""

    POSTGRES = "postgres"
    NEO4J = "neo4j"
    REDIS = "redis"
    GEMINI = "gemini"
    EMBEDDINGS = "embeddings"
    SUPABASE = "supabase"
    EU_PORTAL_API = "eu_portal_api"  # EU Funding & Tenders Portal API


class AvailabilityStatus(str, Enum):
    """Service availability status."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class ServiceStatus:
    """Status of a single service."""

    service: ServiceType
    status: AvailabilityStatus
    last_check: datetime
    latency_ms: float | None = None
    error_message: str | None = None
    consecutive_failures: int = 0

    @property
    def is_available(self) -> bool:
        """Check if service is usable."""
        return self.status in [AvailabilityStatus.AVAILABLE, AvailabilityStatus.DEGRADED]


@dataclass
class ServiceAvailability:
    """Overall service availability context."""

    services: dict[ServiceType, ServiceStatus] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def postgres_available(self) -> bool:
        return self._is_available(ServiceType.POSTGRES)

    @property
    def neo4j_available(self) -> bool:
        return self._is_available(ServiceType.NEO4J)

    @property
    def redis_available(self) -> bool:
        return self._is_available(ServiceType.REDIS)

    @property
    def embeddings_available(self) -> bool:
        return self._is_available(ServiceType.EMBEDDINGS)

    @property
    def gemini_available(self) -> bool:
        return self._is_available(ServiceType.GEMINI)

    def _is_available(self, service_type: ServiceType) -> bool:
        status = self.services.get(service_type)
        return status.is_available if status else False

    def to_dict(self) -> dict[str, bool]:
        """Convert to simple availability dictionary for tool filtering."""
        return {
            "postgres": self.postgres_available,
            "neo4j": self.neo4j_available,
            "redis": self.redis_available,
            "embeddings": self.embeddings_available,
            "gemini": self.gemini_available,
        }


# ============================================================================
# Tool-Service Mapping
# ============================================================================

# Maps tools to their required services
TOOL_SERVICE_REQUIREMENTS: dict[str, list[ServiceType]] = {
    # Statistics tools - prefer Neo4j but can fall back to SQL
    "get_programme_statistics": [ServiceType.POSTGRES],  # Neo4j optional, SQL fallback
    "get_country_statistics": [ServiceType.POSTGRES],  # Neo4j optional, SQL fallback
    "compare_programmes": [ServiceType.NEO4J],
    # Document tools - need PostgreSQL/Supabase
    "search_documents": [ServiceType.POSTGRES],
    # Call tools - primarily PostgreSQL
    "search_funding_calls": [ServiceType.POSTGRES],
    "get_call_details": [ServiceType.POSTGRES],
    # Project tools - PostgreSQL, optionally Neo4j and embeddings
    "search_projects": [ServiceType.POSTGRES],  # Can work without Neo4j
    "get_project_details": [ServiceType.POSTGRES],
    "find_similar_projects": [ServiceType.POSTGRES],  # Fallback to keyword if no embeddings
    "find_semantically_similar_projects": [ServiceType.POSTGRES, ServiceType.EMBEDDINGS],
    "find_organization_projects": [ServiceType.POSTGRES],
    "get_collaboration_network": [ServiceType.NEO4J],
    "search_by_cluster": [ServiceType.POSTGRES],
    # Hybrid tools - can work with partial services
    "get_budget_benchmark": [ServiceType.POSTGRES],  # Graph optional
    "get_consortium_patterns": [ServiceType.POSTGRES],  # Graph optional
    "find_experienced_partners": [ServiceType.POSTGRES],  # Graph optional
    "get_similar_funded_projects": [ServiceType.POSTGRES, ServiceType.EMBEDDINGS],
    "analyze_call_history": [ServiceType.POSTGRES],  # Graph optional
    # Proposal tools
    "calculate_budget": [ServiceType.POSTGRES],
    "generate_timeline": [ServiceType.POSTGRES],
}

# Tools that can operate in degraded mode (with reduced functionality)
DEGRADABLE_TOOLS: dict[str, list[ServiceType]] = {
    # These tools can work without Neo4j, using SQL fallbacks
    "get_budget_benchmark": [ServiceType.NEO4J],
    "get_consortium_patterns": [ServiceType.NEO4J],
    "find_experienced_partners": [ServiceType.NEO4J],
    "analyze_call_history": [ServiceType.NEO4J],
    # Statistics tools - can use SQL fallback when Neo4j unavailable
    "get_country_statistics": [ServiceType.NEO4J],
    "get_programme_statistics": [ServiceType.NEO4J],
    # These tools can work without embeddings, using keyword search
    "find_similar_projects": [ServiceType.EMBEDDINGS],
    "get_similar_funded_projects": [ServiceType.EMBEDDINGS],  # Keyword fallback
    "search_projects": [ServiceType.NEO4J, ServiceType.EMBEDDINGS],
    # Call tools - can work without EU Portal API using cached/local data
    "get_call_details": [ServiceType.EU_PORTAL_API],  # Uses cached/local data as fallback
}


# ============================================================================
# Service Availability Checker
# ============================================================================


class ServiceAvailabilityChecker:
    """
    Checks and caches service availability for graceful degradation.

    Features:
    - Parallel health checks for fast response
    - Caching to avoid repeated checks
    - Failure tracking for circuit breaker pattern
    - Tool availability filtering based on service status
    """

    def __init__(self, cache_ttl_seconds: float = 30.0, max_consecutive_failures: int = 3):
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.max_consecutive_failures = max_consecutive_failures
        self._cache: ServiceAvailability | None = None
        self._lock = asyncio.Lock()
        self._failure_counts: dict[ServiceType, int] = {}

    async def check_all_services(self, force_refresh: bool = False) -> ServiceAvailability:
        """
        Check availability of all services.

        Args:
            force_refresh: Bypass cache and check fresh

        Returns:
            ServiceAvailability with status of all services
        """
        async with self._lock:
            # Return cached if still valid
            if not force_refresh and self._cache:
                age = datetime.now(UTC) - self._cache.checked_at
                if age < self.cache_ttl:
                    return self._cache

            # Run all checks in parallel
            checks = await asyncio.gather(
                self._check_postgres(),
                self._check_neo4j(),
                self._check_redis(),
                self._check_embeddings(),
                self._check_gemini(),
                return_exceptions=True,
            )

            services = {}
            for check in checks:
                if isinstance(check, ServiceStatus):
                    services[check.service] = check
                    # Track failures for circuit breaker pattern
                    if check.status == AvailabilityStatus.UNAVAILABLE:
                        self._failure_counts[check.service] = (
                            self._failure_counts.get(check.service, 0) + 1
                        )
                    else:
                        self._failure_counts[check.service] = 0

            self._cache = ServiceAvailability(services=services, checked_at=datetime.now(UTC))

            return self._cache

    async def get_available_tools(
        self, all_tools: list[str], allow_degraded: bool = True
    ) -> list[str]:
        """
        Filter tools based on service availability.

        Args:
            all_tools: List of all tool names
            allow_degraded: Include tools that can work with reduced functionality

        Returns:
            List of tools that can currently be used
        """
        availability = await self.check_all_services()
        available_tools = []

        for tool in all_tools:
            required_services = TOOL_SERVICE_REQUIREMENTS.get(tool, [])

            # Check if all required services are available
            all_available = all(
                availability.services.get(
                    svc,
                    ServiceStatus(
                        service=svc, status=AvailabilityStatus.UNKNOWN, last_check=datetime.now(UTC)
                    ),
                ).is_available
                for svc in required_services
            )

            if all_available:
                available_tools.append(tool)
            elif allow_degraded and tool in DEGRADABLE_TOOLS:
                # Check if the tool can work in degraded mode
                degradable_services = DEGRADABLE_TOOLS[tool]
                essential_services = [s for s in required_services if s not in degradable_services]
                essential_available = all(
                    availability.services.get(
                        svc,
                        ServiceStatus(
                            service=svc,
                            status=AvailabilityStatus.UNKNOWN,
                            last_check=datetime.now(UTC),
                        ),
                    ).is_available
                    for svc in essential_services
                )
                if essential_available:
                    available_tools.append(tool)
                    logger.info(f"Tool '{tool}' available in degraded mode")

        return available_tools

    def get_degradation_notice(self, availability: ServiceAvailability) -> str | None:
        """
        Get a user-friendly notice about degraded functionality.

        Returns:
            Notice string if in degraded mode, None otherwise
        """
        unavailable = []
        degraded = []

        for svc, status in availability.services.items():
            if status.status == AvailabilityStatus.UNAVAILABLE:
                unavailable.append(svc.value)
            elif status.status == AvailabilityStatus.DEGRADED:
                degraded.append(svc.value)

        if not unavailable and not degraded:
            return None

        notices = []
        if unavailable:
            if ServiceType.NEO4J.value in unavailable:
                notices.append("Graph statistics temporarily unavailable")
            if ServiceType.EMBEDDINGS.value in unavailable:
                notices.append("Semantic search using keyword fallback")
            if ServiceType.REDIS.value in unavailable:
                notices.append("Response caching disabled")

        return "; ".join(notices) if notices else None

    # ========================================================================
    # Individual Service Checks
    # ========================================================================

    async def _check_postgres(self) -> ServiceStatus:
        """Check PostgreSQL availability."""
        start = time.time()
        try:
            from .config import settings

            if not settings.database_url:
                return ServiceStatus(
                    service=ServiceType.POSTGRES,
                    status=AvailabilityStatus.UNAVAILABLE,
                    last_check=datetime.now(UTC),
                    error_message="DATABASE_URL not configured",
                )

            import psycopg2

            conn = psycopg2.connect(settings.database_url, connect_timeout=3)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()

            latency = (time.time() - start) * 1000
            return ServiceStatus(
                service=ServiceType.POSTGRES,
                status=AvailabilityStatus.AVAILABLE,
                last_check=datetime.now(UTC),
                latency_ms=latency,
            )

        except Exception as e:
            latency = (time.time() - start) * 1000
            return ServiceStatus(
                service=ServiceType.POSTGRES,
                status=AvailabilityStatus.UNAVAILABLE,
                last_check=datetime.now(UTC),
                latency_ms=latency,
                error_message=str(e),
            )

    async def _check_neo4j(self) -> ServiceStatus:
        """Check Neo4j availability."""
        start = time.time()
        try:
            from .neo4j_config import Neo4jConnection

            db = Neo4jConnection()
            if db.test_connection():
                latency = (time.time() - start) * 1000
                return ServiceStatus(
                    service=ServiceType.NEO4J,
                    status=AvailabilityStatus.AVAILABLE,
                    last_check=datetime.now(UTC),
                    latency_ms=latency,
                )
            else:
                latency = (time.time() - start) * 1000
                return ServiceStatus(
                    service=ServiceType.NEO4J,
                    status=AvailabilityStatus.UNAVAILABLE,
                    last_check=datetime.now(UTC),
                    latency_ms=latency,
                    error_message="Connection test failed",
                )

        except Exception as e:
            latency = (time.time() - start) * 1000
            return ServiceStatus(
                service=ServiceType.NEO4J,
                status=AvailabilityStatus.UNAVAILABLE,
                last_check=datetime.now(UTC),
                latency_ms=latency,
                error_message=str(e),
            )

    async def _check_redis(self) -> ServiceStatus:
        """Check Redis availability."""
        start = time.time()
        try:
            import redis

            from .config import settings

            redis_url = settings.redis_url or "redis://localhost:6379/0"
            r = redis.from_url(redis_url, socket_timeout=2)
            r.ping()

            latency = (time.time() - start) * 1000
            return ServiceStatus(
                service=ServiceType.REDIS,
                status=AvailabilityStatus.AVAILABLE,
                last_check=datetime.now(UTC),
                latency_ms=latency,
            )

        except Exception as e:
            latency = (time.time() - start) * 1000
            return ServiceStatus(
                service=ServiceType.REDIS,
                status=AvailabilityStatus.DEGRADED,  # Redis is non-critical
                last_check=datetime.now(UTC),
                latency_ms=latency,
                error_message=str(e),
            )

    async def _check_embeddings(self) -> ServiceStatus:
        """Check embedding service availability."""
        start = time.time()
        try:
            from .config import settings

            if not settings.vector_search_enabled or not settings.effective_embedding_api_key:
                return ServiceStatus(
                    service=ServiceType.EMBEDDINGS,
                    status=AvailabilityStatus.DEGRADED,
                    last_check=datetime.now(UTC),
                    error_message="Not configured",
                )

            # Quick check - just verify API key works
            from ..services.embedding_service import EmbeddingService

            embedder = EmbeddingService()
            if embedder.test_embedding_generation():
                latency = (time.time() - start) * 1000
                return ServiceStatus(
                    service=ServiceType.EMBEDDINGS,
                    status=AvailabilityStatus.AVAILABLE,
                    last_check=datetime.now(UTC),
                    latency_ms=latency,
                )
            else:
                latency = (time.time() - start) * 1000
                return ServiceStatus(
                    service=ServiceType.EMBEDDINGS,
                    status=AvailabilityStatus.DEGRADED,
                    last_check=datetime.now(UTC),
                    latency_ms=latency,
                    error_message="Test generation failed",
                )

        except Exception as e:
            latency = (time.time() - start) * 1000
            return ServiceStatus(
                service=ServiceType.EMBEDDINGS,
                status=AvailabilityStatus.DEGRADED,  # Embeddings are non-critical
                last_check=datetime.now(UTC),
                latency_ms=latency,
                error_message=str(e),
            )

    async def _check_gemini(self) -> ServiceStatus:
        """Check Gemini AI availability."""
        start = time.time()
        try:
            from .config import settings

            if not settings.gemini_api_key:
                return ServiceStatus(
                    service=ServiceType.GEMINI,
                    status=AvailabilityStatus.UNAVAILABLE,
                    last_check=datetime.now(UTC),
                    error_message="Not configured",
                )

            import google.generativeai as genai

            genai.configure(api_key=settings.gemini_api_key)
            list(genai.list_models())

            latency = (time.time() - start) * 1000
            return ServiceStatus(
                service=ServiceType.GEMINI,
                status=AvailabilityStatus.AVAILABLE,
                last_check=datetime.now(UTC),
                latency_ms=latency,
            )

        except Exception as e:
            latency = (time.time() - start) * 1000
            return ServiceStatus(
                service=ServiceType.GEMINI,
                status=AvailabilityStatus.UNAVAILABLE,
                last_check=datetime.now(UTC),
                latency_ms=latency,
                error_message=str(e),
            )


# ============================================================================
# Global Instance
# ============================================================================

_checker: ServiceAvailabilityChecker | None = None


def get_availability_checker() -> ServiceAvailabilityChecker:
    """Get the global service availability checker."""
    global _checker
    if _checker is None:
        _checker = ServiceAvailabilityChecker()
    return _checker


async def check_services() -> ServiceAvailability:
    """Convenience function to check all services."""
    checker = get_availability_checker()
    return await checker.check_all_services()


async def get_available_tools(all_tools: list[str]) -> list[str]:
    """Convenience function to get available tools."""
    checker = get_availability_checker()
    return await checker.get_available_tools(all_tools)
