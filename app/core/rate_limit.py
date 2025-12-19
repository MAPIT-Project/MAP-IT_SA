"""
Rate Limiting Module

Tiered rate limiting based on user subscription tier.
Uses Redis for distributed rate limiting across multiple instances.
"""

import os
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from fastapi import Request, HTTPException, status, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import redis
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a tier."""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_size: int = 10  # Allow short bursts
    concurrent_requests: int = 5  # Max concurrent requests


# Tier configurations
TIER_LIMITS: Dict[str, RateLimitConfig] = {
    "free": RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        requests_per_day=500,
        burst_size=5,
        concurrent_requests=2
    ),
    "basic": RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=600,
        requests_per_day=5000,
        burst_size=15,
        concurrent_requests=5
    ),
    "premium": RateLimitConfig(
        requests_per_minute=200,
        requests_per_hour=2000,
        requests_per_day=20000,
        burst_size=50,
        concurrent_requests=10
    ),
    "enterprise": RateLimitConfig(
        requests_per_minute=1000,
        requests_per_hour=10000,
        requests_per_day=100000,
        burst_size=200,
        concurrent_requests=50
    ),
}


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining_minute: int
    remaining_hour: int
    remaining_day: int
    reset_minute: int  # Seconds until minute limit resets
    reset_hour: int  # Seconds until hour limit resets
    retry_after: Optional[int] = None  # Seconds to wait if blocked
    tier: str = "free"


class RateLimiter:
    """
    Redis-backed rate limiter with tiered limits.

    Uses sliding window algorithm for accurate rate limiting.
    Falls back to in-memory limiting if Redis is unavailable.
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = True

        # In-memory fallback for when Redis is unavailable
        self.memory_store: Dict[str, Dict[str, Any]] = {}

        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Rate limiter initialized with Redis backend")
        except Exception as e:
            logger.warning(f"Redis unavailable for rate limiting, using in-memory: {e}")
            self.redis_client = None

    async def check_rate_limit(
        self,
        identifier: str,
        tier: str = "free"
    ) -> RateLimitResult:
        """
        Check if request is within rate limits.

        Args:
            identifier: Unique identifier (user ID, IP, or API key)
            tier: User's subscription tier

        Returns:
            RateLimitResult with status and remaining quotas
        """
        config = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        now = int(time.time())

        # Time windows
        minute_key = f"rate:{identifier}:minute:{now // 60}"
        hour_key = f"rate:{identifier}:hour:{now // 3600}"
        day_key = f"rate:{identifier}:day:{now // 86400}"

        try:
            if self.redis_client:
                result = await self._check_redis(
                    identifier, config, minute_key, hour_key, day_key, now
                )
            else:
                result = self._check_memory(
                    identifier, config, minute_key, hour_key, day_key, now
                )

            result.tier = tier
            return result

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # On error, allow the request but log it
            return RateLimitResult(
                allowed=True,
                remaining_minute=config.requests_per_minute,
                remaining_hour=config.requests_per_hour,
                remaining_day=config.requests_per_day,
                reset_minute=60,
                reset_hour=3600,
                tier=tier
            )

    async def _check_redis(
        self,
        identifier: str,
        config: RateLimitConfig,
        minute_key: str,
        hour_key: str,
        day_key: str,
        now: int
    ) -> RateLimitResult:
        """Check rate limits using Redis."""
        pipe = self.redis_client.pipeline()

        # Get current counts
        pipe.get(minute_key)
        pipe.get(hour_key)
        pipe.get(day_key)
        pipe.ttl(minute_key)
        pipe.ttl(hour_key)

        results = pipe.execute()

        minute_count = int(results[0] or 0)
        hour_count = int(results[1] or 0)
        day_count = int(results[2] or 0)
        minute_ttl = results[3] if results[3] > 0 else 60
        hour_ttl = results[4] if results[4] > 0 else 3600

        # Check limits
        if minute_count >= config.requests_per_minute:
            return RateLimitResult(
                allowed=False,
                remaining_minute=0,
                remaining_hour=max(0, config.requests_per_hour - hour_count),
                remaining_day=max(0, config.requests_per_day - day_count),
                reset_minute=minute_ttl,
                reset_hour=hour_ttl,
                retry_after=minute_ttl
            )

        if hour_count >= config.requests_per_hour:
            return RateLimitResult(
                allowed=False,
                remaining_minute=0,
                remaining_hour=0,
                remaining_day=max(0, config.requests_per_day - day_count),
                reset_minute=minute_ttl,
                reset_hour=hour_ttl,
                retry_after=hour_ttl
            )

        if day_count >= config.requests_per_day:
            seconds_until_midnight = 86400 - (now % 86400)
            return RateLimitResult(
                allowed=False,
                remaining_minute=0,
                remaining_hour=0,
                remaining_day=0,
                reset_minute=minute_ttl,
                reset_hour=hour_ttl,
                retry_after=seconds_until_midnight
            )

        # Increment counters
        pipe = self.redis_client.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)
        pipe.incr(day_key)
        pipe.expire(day_key, 86400)
        pipe.execute()

        return RateLimitResult(
            allowed=True,
            remaining_minute=config.requests_per_minute - minute_count - 1,
            remaining_hour=config.requests_per_hour - hour_count - 1,
            remaining_day=config.requests_per_day - day_count - 1,
            reset_minute=minute_ttl,
            reset_hour=hour_ttl
        )

    def _check_memory(
        self,
        identifier: str,
        config: RateLimitConfig,
        minute_key: str,
        hour_key: str,
        day_key: str,
        now: int
    ) -> RateLimitResult:
        """Check rate limits using in-memory store (fallback)."""
        # Initialize if needed
        if identifier not in self.memory_store:
            self.memory_store[identifier] = {}

        store = self.memory_store[identifier]

        # Clean old entries
        for key in list(store.keys()):
            if store[key].get("expires", 0) < now:
                del store[key]

        # Get current counts
        minute_count = store.get(minute_key, {}).get("count", 0)
        hour_count = store.get(hour_key, {}).get("count", 0)
        day_count = store.get(day_key, {}).get("count", 0)

        minute_ttl = max(0, store.get(minute_key, {}).get("expires", now + 60) - now)
        hour_ttl = max(0, store.get(hour_key, {}).get("expires", now + 3600) - now)

        # Check limits
        if minute_count >= config.requests_per_minute:
            return RateLimitResult(
                allowed=False,
                remaining_minute=0,
                remaining_hour=max(0, config.requests_per_hour - hour_count),
                remaining_day=max(0, config.requests_per_day - day_count),
                reset_minute=int(minute_ttl),
                reset_hour=int(hour_ttl),
                retry_after=int(minute_ttl)
            )

        if hour_count >= config.requests_per_hour:
            return RateLimitResult(
                allowed=False,
                remaining_minute=0,
                remaining_hour=0,
                remaining_day=max(0, config.requests_per_day - day_count),
                reset_minute=int(minute_ttl),
                reset_hour=int(hour_ttl),
                retry_after=int(hour_ttl)
            )

        if day_count >= config.requests_per_day:
            seconds_until_midnight = 86400 - (now % 86400)
            return RateLimitResult(
                allowed=False,
                remaining_minute=0,
                remaining_hour=0,
                remaining_day=0,
                reset_minute=int(minute_ttl),
                reset_hour=int(hour_ttl),
                retry_after=seconds_until_midnight
            )

        # Increment counters
        store[minute_key] = {
            "count": minute_count + 1,
            "expires": now + 60
        }
        store[hour_key] = {
            "count": hour_count + 1,
            "expires": now + 3600
        }
        store[day_key] = {
            "count": day_count + 1,
            "expires": now + 86400
        }

        return RateLimitResult(
            allowed=True,
            remaining_minute=config.requests_per_minute - minute_count - 1,
            remaining_hour=config.requests_per_hour - hour_count - 1,
            remaining_day=config.requests_per_day - day_count - 1,
            reset_minute=60,
            reset_hour=3600
        )

    def get_tier_limits(self, tier: str) -> Dict[str, int]:
        """Get limits for a tier."""
        config = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        return {
            "requests_per_minute": config.requests_per_minute,
            "requests_per_hour": config.requests_per_hour,
            "requests_per_day": config.requests_per_day,
            "burst_size": config.burst_size,
            "concurrent_requests": config.concurrent_requests
        }


# Singleton rate limiter
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get singleton rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.

    Applies rate limits based on user tier from authentication.
    Falls back to IP-based limiting for unauthenticated requests.
    """

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {
        "/api/health",
        "/api/health/live",
        "/api/health/ready",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Get identifier and tier
        identifier, tier = self._get_identifier_and_tier(request)

        # Check rate limit
        rate_limiter = get_rate_limiter()
        result = await rate_limiter.check_rate_limit(identifier, tier)

        if not result.allowed:
            return self._rate_limit_response(result)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(
            TIER_LIMITS.get(tier, TIER_LIMITS["free"]).requests_per_minute
        )
        response.headers["X-RateLimit-Remaining"] = str(result.remaining_minute)
        response.headers["X-RateLimit-Reset"] = str(result.reset_minute)

        return response

    def _get_identifier_and_tier(self, request: Request) -> Tuple[str, str]:
        """Extract identifier and tier from request."""
        # Try to get from authenticated user
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id") and user.id != "anonymous":
            return user.id, getattr(user, "tier", "free")

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}", "free"

    def _rate_limit_response(self, result: RateLimitResult) -> Response:
        """Create rate limit exceeded response."""
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please slow down.",
                "retry_after": result.retry_after,
                "remaining": {
                    "minute": result.remaining_minute,
                    "hour": result.remaining_hour,
                    "day": result.remaining_day
                },
                "tier": result.tier,
                "upgrade_hint": "Upgrade to a higher tier for increased limits."
            },
            headers={
                "Retry-After": str(result.retry_after or 60),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(result.reset_minute)
            }
        )


# Dependency for checking rate limits explicitly
async def check_rate_limit(request: Request) -> RateLimitResult:
    """
    FastAPI dependency for explicit rate limit checking.

    Usage:
        @router.post("/expensive-operation")
        async def expensive_op(limit: RateLimitResult = Depends(check_rate_limit)):
            if not limit.allowed:
                raise HTTPException(429, "Rate limited")
            ...
    """
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        identifier = user.id
        tier = getattr(user, "tier", "free")
    else:
        identifier = f"ip:{request.client.host}" if request.client else "unknown"
        tier = "free"

    rate_limiter = get_rate_limiter()
    result = await rate_limiter.check_rate_limit(identifier, tier)

    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "RATE_LIMIT_EXCEEDED",
                "retry_after": result.retry_after,
                "tier": tier
            },
            headers={"Retry-After": str(result.retry_after or 60)}
        )

    return result


# Special rate limit for expensive operations
async def check_expensive_operation_limit(request: Request) -> RateLimitResult:
    """
    Stricter rate limit for expensive operations.

    Use for operations like AI generation, batch processing, etc.
    """
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        identifier = f"expensive:{user.id}"
        tier = getattr(user, "tier", "free")
    else:
        identifier = f"expensive:ip:{request.client.host}" if request.client else "expensive:unknown"
        tier = "free"

    # Use stricter limits for expensive operations
    expensive_limits = {
        "free": RateLimitConfig(
            requests_per_minute=2,
            requests_per_hour=20,
            requests_per_day=50,
            burst_size=2,
            concurrent_requests=1
        ),
        "basic": RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=500,
            burst_size=5,
            concurrent_requests=2
        ),
        "premium": RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=300,
            requests_per_day=2000,
            burst_size=10,
            concurrent_requests=5
        ),
        "enterprise": RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=1000,
            requests_per_day=10000,
            burst_size=30,
            concurrent_requests=20
        ),
    }

    rate_limiter = get_rate_limiter()

    # Temporarily override limits for this check
    original_limits = TIER_LIMITS.copy()
    TIER_LIMITS.update(expensive_limits)

    try:
        result = await rate_limiter.check_rate_limit(identifier, tier)
    finally:
        TIER_LIMITS.update(original_limits)

    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "EXPENSIVE_OPERATION_RATE_LIMITED",
                "message": "Rate limit exceeded for expensive operations",
                "retry_after": result.retry_after,
                "tier": tier
            },
            headers={"Retry-After": str(result.retry_after or 60)}
        )

    return result
