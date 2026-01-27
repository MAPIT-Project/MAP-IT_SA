"""
Retry Utilities

Decorators for automatic retry with exponential backoff.
"""

import asyncio
import functools
import logging
import random
import time
from collections.abc import Callable
from typing import Any

from .exceptions import ProposalWritingError, RateLimitError

logger = logging.getLogger(__name__)


def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (
        ProposalWritingError,
        ConnectionError,
        asyncio.TimeoutError
    ),
    on_retry: Callable[[Exception, int], None] | None = None
):
    """
    Async retry decorator with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delays
        retryable_exceptions: Tuple of exceptions to retry
        on_retry: Callback function called on each retry

    Usage:
        @async_retry(max_retries=3)
        async def my_function():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except retryable_exceptions as e:
                    last_exception = e

                    # Check if exception is recoverable
                    if isinstance(e, ProposalWritingError) and not e.recoverable:
                        raise

                    # Don't retry on last attempt
                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    # Calculate delay
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    # Add jitter
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    # Special handling for rate limits
                    if isinstance(e, RateLimitError) and e.details.get("retry_after"):
                        delay = max(delay, e.details["retry_after"])

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )

                    # Call retry callback
                    if on_retry:
                        on_retry(e, attempt)

                    await asyncio.sleep(delay)

            # Should not reach here, but just in case
            raise last_exception

        return wrapper
    return decorator


def sync_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)
):
    """Synchronous retry decorator."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    # Check if exception is recoverable
                    if isinstance(e, ProposalWritingError) and not e.recoverable:
                        raise

                    if attempt == max_retries:
                        raise

                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}), retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern for preventing cascading failures.

    States:
    - CLOSED: Normal operation
    - OPEN: Failing fast, not making calls
    - HALF_OPEN: Testing if service recovered
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._failures = 0
        self._last_failure_time = 0.0
        self._state = self.CLOSED
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = self.HALF_OPEN
                self._half_open_calls = 0

        return self._state

    def record_success(self):
        """Record a successful call."""
        self._failures = 0
        if self._state == self.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = self.CLOSED
                logger.info("Circuit breaker closed after successful half-open calls")

    def record_failure(self):
        """Record a failed call."""
        self._failures += 1
        self._last_failure_time = time.time()

        if self._failures >= self.failure_threshold:
            self._state = self.OPEN
            logger.warning(f"Circuit breaker opened after {self._failures} failures")

    def can_execute(self) -> bool:
        """Check if a call can be made."""
        state = self.state

        if state == self.CLOSED:
            return True
        elif state == self.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls
        else:  # OPEN
            return False

    def reset(self):
        """Reset the circuit breaker to closed state."""
        self._failures = 0
        self._state = self.CLOSED
        self._half_open_calls = 0
        logger.info("Circuit breaker reset to closed state")

    def __repr__(self) -> str:
        return f"CircuitBreaker(state={self.state}, failures={self._failures})"


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return delay


# Default configurations for different scenarios
AGGRESSIVE_RETRY = RetryConfig(max_retries=5, base_delay=0.5, max_delay=10.0)
STANDARD_RETRY = RetryConfig(max_retries=3, base_delay=1.0, max_delay=30.0)
GENTLE_RETRY = RetryConfig(max_retries=2, base_delay=2.0, max_delay=60.0)
