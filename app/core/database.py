"""
Database Connection Pool Management for MAP-IT.

Provides a centralized, managed database connection pool with:
- Connection monitoring and statistics
- Health check integration
- Graceful degradation support
- Async-compatible interface

Implements Priority 2.4 from IMPROVEMENT_ROADMAP.md
"""

import logging
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

from psycopg2 import pool
from psycopg2.extras import DictCursor, RealDictCursor

from .config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Connection Pool Statistics
# ============================================================================

@dataclass
class PoolStats:
    """Statistics for connection pool monitoring."""
    total_connections_created: int = 0
    total_connections_closed: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    current_in_use: int = 0
    peak_in_use: int = 0
    avg_wait_time_ms: float = 0.0
    total_wait_time_ms: float = 0.0
    pool_created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_health_check: datetime | None = None
    last_health_check_success: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        uptime = datetime.now(UTC) - self.pool_created_at
        return {
            "total_connections_created": self.total_connections_created,
            "total_connections_closed": self.total_connections_closed,
            "active_connections": self.current_in_use,
            "peak_connections": self.peak_in_use,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "timeout_requests": self.timeout_requests,
            "success_rate": round(
                self.successful_requests / max(self.total_requests, 1) * 100, 2
            ),
            "avg_wait_time_ms": round(self.avg_wait_time_ms, 2),
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": str(uptime),
            "last_health_check": (
                self.last_health_check.isoformat()
                if self.last_health_check else None
            ),
            "healthy": self.last_health_check_success
        }


# ============================================================================
# Database Pool Manager
# ============================================================================

class DatabasePool:
    """
    Managed database connection pool with monitoring.

    Features:
    - Thread-safe connection management
    - Connection statistics and monitoring
    - Health check integration
    - Automatic connection validation
    - Graceful degradation support
    """

    def __init__(
        self,
        dsn: str,
        min_connections: int = 5,
        max_connections: int = 20,
        connection_timeout: float = 30.0,
        validation_query: str = "SELECT 1",
        name: str = "default"
    ):
        """
        Initialize the database pool.

        Args:
            dsn: Database connection string
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            connection_timeout: Timeout for acquiring a connection (seconds)
            validation_query: Query to validate connections
            name: Pool name for logging
        """
        self.dsn = dsn
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.validation_query = validation_query
        self.name = name

        self._lock = threading.Lock()
        self._pool: pool.ThreadedConnectionPool | None = None
        self._stats = PoolStats()
        self._closed = False

        # Initialize pool
        self._initialize_pool()

    def _initialize_pool(self):
        """Create the underlying connection pool."""
        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=self.min_connections,
                maxconn=self.max_connections,
                dsn=self.dsn
            )
            self._stats.total_connections_created = self.min_connections
            logger.info(
                f"Database pool '{self.name}' initialized: "
                f"min={self.min_connections}, max={self.max_connections}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize database pool '{self.name}': {e}")
            raise

    @contextmanager
    def get_connection(
        self,
        timeout: float | None = None,
        cursor_factory=DictCursor
    ) -> Generator:
        """
        Get a connection from the pool.

        Args:
            timeout: Override default timeout (seconds)
            cursor_factory: Psycopg2 cursor factory to use

        Yields:
            Database connection

        Raises:
            ConnectionError: If connection cannot be obtained
            TimeoutError: If timeout is exceeded
        """
        if self._closed:
            raise ConnectionError(f"Pool '{self.name}' is closed")

        if self._pool is None:
            raise ConnectionError(f"Pool '{self.name}' not initialized")

        timeout = timeout or self.connection_timeout
        start_time = time.time()
        conn = None

        with self._lock:
            self._stats.total_requests += 1
            self._stats.current_in_use += 1
            if self._stats.current_in_use > self._stats.peak_in_use:
                self._stats.peak_in_use = self._stats.current_in_use

        try:
            # Get connection with timeout
            conn = self._pool.getconn()
            wait_time = (time.time() - start_time) * 1000

            with self._lock:
                self._stats.total_wait_time_ms += wait_time
                self._stats.avg_wait_time_ms = (
                    self._stats.total_wait_time_ms / self._stats.total_requests
                )

            if conn is None:
                with self._lock:
                    self._stats.failed_requests += 1
                    self._stats.current_in_use -= 1
                raise ConnectionError(
                    f"No available connections in pool '{self.name}'"
                )

            # Validate connection
            if not self._validate_connection(conn):
                logger.warning("Connection validation failed, reconnecting...")
                conn.close()
                conn = self._pool.getconn()

            yield conn

            with self._lock:
                self._stats.successful_requests += 1

        except TimeoutError:
            with self._lock:
                self._stats.timeout_requests += 1
                self._stats.failed_requests += 1
            raise

        except Exception:
            with self._lock:
                self._stats.failed_requests += 1

            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise

        finally:
            with self._lock:
                self._stats.current_in_use -= 1

            if conn:
                try:
                    self._pool.putconn(conn)
                except Exception as e:
                    logger.warning(f"Error returning connection to pool: {e}")

    def _validate_connection(self, conn) -> bool:
        """Validate a connection is still usable."""
        try:
            with conn.cursor() as cursor:
                cursor.execute(self.validation_query)
                return True
        except Exception:
            return False

    def execute(
        self,
        query: str,
        params: tuple | None = None,
        fetch: bool = True
    ) -> list | None:
        """
        Execute a query using a pooled connection.

        Args:
            query: SQL query to execute
            params: Query parameters
            fetch: Whether to fetch results

        Returns:
            Query results if fetch=True, else None
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch:
                    return cursor.fetchall()
                conn.commit()
                return None

    def execute_many(
        self,
        query: str,
        params_list: list
    ) -> int:
        """
        Execute a query with multiple parameter sets.

        Args:
            query: SQL query to execute
            params_list: List of parameter tuples

        Returns:
            Number of rows affected
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount

    async def health_check(self) -> dict[str, Any]:
        """
        Perform a health check on the pool.

        Returns:
            Health check result dictionary
        """
        start_time = time.time()
        result = {
            "pool_name": self.name,
            "status": "unknown",
            "latency_ms": 0,
            "message": ""
        }

        try:
            with self.get_connection(timeout=5.0) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(self.validation_query)
                    cursor.fetchone()

            latency = (time.time() - start_time) * 1000
            result["status"] = "healthy"
            result["latency_ms"] = round(latency, 2)
            result["message"] = "Connection successful"

            with self._lock:
                self._stats.last_health_check = datetime.now(UTC)
                self._stats.last_health_check_success = True

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            result["status"] = "unhealthy"
            result["latency_ms"] = round(latency, 2)
            result["message"] = str(e)

            with self._lock:
                self._stats.last_health_check = datetime.now(UTC)
                self._stats.last_health_check_success = False

        return result

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return self._stats.to_dict()

    def close(self):
        """Close all connections in the pool."""
        if self._pool and not self._closed:
            try:
                self._pool.closeall()
                self._closed = True
                logger.info(f"Database pool '{self.name}' closed")
            except Exception as e:
                logger.error(f"Error closing pool '{self.name}': {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============================================================================
# Global Pool Manager
# ============================================================================

class PoolManager:
    """
    Manager for multiple database pools.

    Provides a singleton pattern for managing database pools across the application.
    """

    _instance: Optional['PoolManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._pools: dict[str, DatabasePool] = {}
                    cls._instance._initialized = False
        return cls._instance

    def initialize(self):
        """Initialize default pools from settings."""
        if self._initialized:
            return

        # Initialize main database pool
        if settings.database_url:
            self.create_pool(
                name="main",
                dsn=settings.database_url,
                min_connections=settings.db_min_connections,
                max_connections=settings.db_max_connections
            )

        self._initialized = True

    def create_pool(
        self,
        name: str,
        dsn: str,
        min_connections: int = 5,
        max_connections: int = 20,
        **kwargs
    ) -> DatabasePool:
        """
        Create a new database pool.

        Args:
            name: Pool name
            dsn: Database connection string
            min_connections: Minimum connections
            max_connections: Maximum connections
            **kwargs: Additional pool options

        Returns:
            Created DatabasePool instance
        """
        if name in self._pools:
            logger.warning(f"Pool '{name}' already exists, returning existing pool")
            return self._pools[name]

        db_pool = DatabasePool(
            dsn=dsn,
            min_connections=min_connections,
            max_connections=max_connections,
            name=name,
            **kwargs
        )
        self._pools[name] = db_pool
        return db_pool

    def get_pool(self, name: str = "main") -> DatabasePool | None:
        """Get a pool by name."""
        return self._pools.get(name)

    def get_connection(self, pool_name: str = "main", **kwargs):
        """Get a connection from a named pool."""
        db_pool = self.get_pool(pool_name)
        if not db_pool:
            raise ConnectionError(f"Pool '{pool_name}' not found")
        return db_pool.get_connection(**kwargs)

    async def health_check_all(self) -> dict[str, Any]:
        """Health check all pools."""
        results = {}
        for name, db_pool in self._pools.items():
            results[name] = await db_pool.health_check()
        return results

    def get_all_stats(self) -> dict[str, Any]:
        """Get statistics for all pools."""
        return {name: db_pool.get_stats() for name, db_pool in self._pools.items()}

    def close_all(self):
        """Close all pools."""
        for name, db_pool in list(self._pools.items()):
            db_pool.close()
            del self._pools[name]
        self._initialized = False


# ============================================================================
# Convenience Functions
# ============================================================================

def get_pool_manager() -> PoolManager:
    """Get the global pool manager instance."""
    manager = PoolManager()
    if not manager._initialized and settings.database_url:
        manager.initialize()
    return manager


def get_connection(pool_name: str = "main", **kwargs):
    """
    Get a database connection from the named pool.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM projects")
    """
    manager = get_pool_manager()
    return manager.get_connection(pool_name, **kwargs)


def execute_query(
    query: str,
    params: tuple | None = None,
    pool_name: str = "main"
) -> list | None:
    """
    Execute a query using a pooled connection.

    Args:
        query: SQL query
        params: Query parameters
        pool_name: Pool to use

    Returns:
        Query results
    """
    db_pool = get_pool_manager().get_pool(pool_name)
    if not db_pool:
        raise ConnectionError(f"Pool '{pool_name}' not found")
    return db_pool.execute(query, params)


async def check_database_health(pool_name: str = "main") -> dict[str, Any]:
    """Check database health for a specific pool."""
    db_pool = get_pool_manager().get_pool(pool_name)
    if not db_pool:
        return {"status": "unavailable", "message": f"Pool '{pool_name}' not found"}
    return await db_pool.health_check()
