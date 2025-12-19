"""
Result Caching Service

Caches expensive query results (statistics, benchmarks, project searches)
in Redis to reduce database load and improve response times.

Key Features:
- Type-specific TTLs (statistics cached longer than searches)
- Cache invalidation patterns
- Compression for large results
- Cache statistics and monitoring
"""

import hashlib
import json
import logging
import zlib
from datetime import timedelta
from typing import Any, Dict, Optional, List, Callable
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)


# Cache TTLs by result type (in seconds)
CACHE_TTLS = {
    # Statistics - rarely change, cache longer
    "programme_statistics": timedelta(hours=24),
    "country_statistics": timedelta(hours=24),
    "cluster_statistics": timedelta(hours=24),

    # Benchmarks - moderate change rate
    "budget_benchmark": timedelta(hours=12),
    "consortium_patterns": timedelta(hours=12),
    "call_history": timedelta(hours=12),

    # Search results - change more frequently
    "funding_calls": timedelta(hours=1),  # Deadlines change
    "projects": timedelta(hours=6),
    "similar_projects": timedelta(hours=6),
    "experienced_partners": timedelta(hours=6),

    # Documents - rarely change
    "documents": timedelta(hours=24),

    # Default
    "default": timedelta(hours=1),
}


class ResultCache:
    """Cache for expensive query results."""

    def __init__(self, redis_client=None, compression_threshold: int = 10000):
        """
        Initialize the result cache.

        Args:
            redis_client: Redis client instance. If None, caching is disabled.
            compression_threshold: Compress results larger than this (bytes)
        """
        self.redis = redis_client
        self.prefix = "result:"
        self.compression_threshold = compression_threshold
        self.enabled = redis_client is not None

        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "errors": 0,
        }

        if self.enabled:
            logger.info("✅ Result cache initialized with Redis")
        else:
            logger.warning("⚠️ Result cache disabled (no Redis client)")

    def _make_key(self, query_type: str, params: Dict) -> str:
        """
        Generate cache key from query type and parameters.

        Args:
            query_type: Type of query (e.g., "programme_statistics", "projects")
            params: Query parameters

        Returns:
            Redis cache key
        """
        # Sort keys for deterministic hashing
        param_str = json.dumps(params, sort_keys=True, default=str)
        hash_val = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        return f"{self.prefix}{query_type}:{hash_val}"

    def _get_ttl(self, query_type: str) -> int:
        """Get TTL in seconds for a query type."""
        ttl = CACHE_TTLS.get(query_type, CACHE_TTLS["default"])
        return int(ttl.total_seconds())

    def _compress(self, data: bytes) -> bytes:
        """Compress data using zlib."""
        return zlib.compress(data, level=6)

    def _decompress(self, data: bytes) -> bytes:
        """Decompress zlib-compressed data."""
        return zlib.decompress(data)

    def _serialize(self, result: Any) -> bytes:
        """
        Serialize result to bytes, with optional compression.

        Returns tuple of (data, compressed_flag)
        """
        json_str = json.dumps(result, default=str)
        data = json_str.encode('utf-8')

        if len(data) > self.compression_threshold:
            compressed = self._compress(data)
            # Only use compression if it actually reduces size
            if len(compressed) < len(data):
                return b'1' + compressed  # Prefix with compression flag

        return b'0' + data  # Prefix with no-compression flag

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize result from bytes."""
        flag = data[0:1]
        payload = data[1:]

        if flag == b'1':
            # Decompress
            payload = self._decompress(payload)

        return json.loads(payload.decode('utf-8'))

    async def get(
        self,
        query_type: str,
        params: Dict
    ) -> Optional[Any]:
        """
        Get cached result.

        Args:
            query_type: Type of query
            params: Query parameters

        Returns:
            Cached result or None if not found
        """
        if not self.enabled:
            return None

        try:
            key = self._make_key(query_type, params)
            cached = self.redis.get(key)

            if cached:
                result = self._deserialize(cached)
                self.stats["hits"] += 1
                logger.debug(f"✅ Cache HIT for {query_type}")
                return result

            self.stats["misses"] += 1
            logger.debug(f"❌ Cache MISS for {query_type}")
            return None

        except Exception as e:
            self.stats["errors"] += 1
            logger.warning(f"Cache get error for {query_type}: {e}")
            return None

    async def set(
        self,
        query_type: str,
        params: Dict,
        result: Any,
        ttl: Optional[timedelta] = None
    ) -> bool:
        """
        Cache a result.

        Args:
            query_type: Type of query
            params: Query parameters
            result: Result to cache
            ttl: Optional custom TTL (uses type-specific TTL if not provided)

        Returns:
            True if cached successfully
        """
        if not self.enabled:
            return False

        try:
            key = self._make_key(query_type, params)
            data = self._serialize(result)
            ttl_seconds = int(ttl.total_seconds()) if ttl else self._get_ttl(query_type)

            self.redis.setex(key, ttl_seconds, data)
            self.stats["sets"] += 1

            logger.debug(f"✅ Cached {query_type} (TTL: {ttl_seconds}s, size: {len(data)} bytes)")
            return True

        except Exception as e:
            self.stats["errors"] += 1
            logger.warning(f"Cache set error for {query_type}: {e}")
            return False

    async def invalidate(
        self,
        query_type: str,
        params: Dict
    ) -> bool:
        """
        Invalidate a cached result.

        Args:
            query_type: Type of query
            params: Query parameters

        Returns:
            True if deleted, False otherwise
        """
        if not self.enabled:
            return False

        try:
            key = self._make_key(query_type, params)
            deleted = self.redis.delete(key)
            if deleted:
                logger.info(f"🗑️ Invalidated cache for {query_type}")
            return deleted > 0

        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
            return False

    async def invalidate_type(self, query_type: str) -> int:
        """
        Invalidate all cached results of a specific type.

        Args:
            query_type: Type of query to invalidate

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            pattern = f"{self.prefix}{query_type}:*"
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(f"🗑️ Invalidated {deleted} {query_type} cache entries")
                return deleted
            return 0

        except Exception as e:
            logger.warning(f"Cache type invalidation error: {e}")
            return 0

    async def clear_all(self) -> int:
        """
        Clear all cached results.

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            keys = self.redis.keys(f"{self.prefix}*")
            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(f"🗑️ Cleared all {deleted} cache entries")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        result = {
            "enabled": self.enabled,
            **self.stats,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
        }

        if self.enabled:
            try:
                # Get cache size info
                keys = self.redis.keys(f"{self.prefix}*")
                result["cached_entries"] = len(keys) if keys else 0

                # Get memory usage estimate (if available)
                memory_usage = 0
                for key in (keys or [])[:100]:  # Sample first 100
                    try:
                        mem = self.redis.memory_usage(key)
                        if mem:
                            memory_usage += mem
                    except:
                        pass

                if memory_usage > 0:
                    result["memory_usage_bytes"] = memory_usage
                    if len(keys) > 100:
                        # Extrapolate for all keys
                        result["estimated_total_memory_bytes"] = int(memory_usage * len(keys) / 100)

            except Exception as e:
                result["stats_error"] = str(e)

        return result

    def reset_stats(self):
        """Reset cache statistics."""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "errors": 0,
        }


def cached_result(
    query_type: str,
    ttl: Optional[timedelta] = None,
    key_params: Optional[List[str]] = None
):
    """
    Decorator to cache function results.

    Args:
        query_type: Type of query for TTL selection
        ttl: Optional custom TTL
        key_params: List of parameter names to use for cache key
                   (if None, uses all kwargs)

    Usage:
        @cached_result("programme_statistics")
        async def get_programme_statistics(programme: str) -> Dict:
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache instance (should be passed in kwargs or available globally)
            cache = kwargs.pop('_cache', None)

            if cache is None or not cache.enabled:
                return await func(*args, **kwargs)

            # Build cache key params
            if key_params:
                cache_params = {k: kwargs.get(k) for k in key_params if k in kwargs}
            else:
                cache_params = dict(kwargs)

            # Try to get from cache
            cached = await cache.get(query_type, cache_params)
            if cached is not None:
                return cached

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await cache.set(query_type, cache_params, result, ttl)

            return result

        return wrapper
    return decorator


# Global cache instance (initialized lazily)
_global_cache: Optional[ResultCache] = None


def get_result_cache() -> ResultCache:
    """Get or create the global result cache instance."""
    global _global_cache

    if _global_cache is None:
        # Try to get Redis client
        try:
            import redis
            import os

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            client = redis.from_url(redis_url, decode_responses=False)
            # Test connection
            client.ping()
            _global_cache = ResultCache(client)
        except Exception as e:
            logger.warning(f"⚠️ Could not connect to Redis for result cache: {e}")
            _global_cache = ResultCache(None)  # Disabled cache

    return _global_cache


def invalidate_cache_on_update(query_types: List[str]):
    """
    Decorator to invalidate cache when data is updated.

    Args:
        query_types: List of query types to invalidate

    Usage:
        @invalidate_cache_on_update(["projects", "similar_projects"])
        async def update_project(project_id: str, data: dict):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Invalidate caches after successful update
            cache = get_result_cache()
            for query_type in query_types:
                await cache.invalidate_type(query_type)

            return result
        return wrapper
    return decorator
