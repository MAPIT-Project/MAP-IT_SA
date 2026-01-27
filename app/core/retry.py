"""
Retry Utilities for MAP-IT

Provides async retry logic with exponential backoff, jitter,
and configurable retry strategies for different operation types.
"""

import asyncio
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True  # Add random jitter to prevent thundering herd
    jitter_factor: float = 0.5  # Max jitter as fraction of delay


# Predefined retry configurations
AGGRESSIVE_RETRY = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0
)

STANDARD_RETRY = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0
)

GENTLE_RETRY = RetryConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0
)

# Service-specific configurations
LLM_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0
)

EXTERNAL_API_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=15.0,
    exponential_base=2.0
)


def calculate_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """
    Calculate the delay before the next retry attempt.

    Uses exponential backoff with optional jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    # Exponential backoff
    delay = min(
        config.base_delay * (config.exponential_base ** attempt),
        config.max_delay
    )

    # Add jitter if enabled
    if config.jitter:
        jitter_range = delay * config.jitter_factor
        delay = delay + random.uniform(-jitter_range, jitter_range)
        delay = max(0.1, delay)  # Ensure minimum delay

    return delay


def should_retry(
    exception: Exception,
    retryable_exceptions: tuple[type[Exception], ...],
    attempt: int,
    max_attempts: int
) -> bool:
    """
    Determine if an operation should be retried.

    Args:
        exception: The exception that was raised
        retryable_exceptions: Tuple of exception types that are retryable
        attempt: Current attempt number
        max_attempts: Maximum number of attempts

    Returns:
        True if operation should be retried
    """
    if attempt >= max_attempts - 1:
        return False

    return isinstance(exception, retryable_exceptions)


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    config: RetryConfig | None = None,
    on_retry: Callable[[Exception, int], None] | None = None
):
    """
    Async retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exception types to retry on
        config: Optional RetryConfig to use instead of individual params
        on_retry: Optional callback called on each retry (exception, attempt)

    Usage:
        @async_retry(max_attempts=3, retryable_exceptions=(ConnectionError, TimeoutError))
        async def fetch_data():
            ...

        @async_retry(config=LLM_RETRY_CONFIG)
        async def call_llm():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Use config if provided, otherwise use individual params
            cfg = config or RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base
            )

            last_exception = None

            for attempt in range(cfg.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == cfg.max_attempts - 1:
                        # Last attempt, don't retry
                        logger.error(
                            f"{func.__name__} failed after {cfg.max_attempts} attempts: {e}"
                        )
                        raise

                    # Calculate delay
                    delay = calculate_delay(attempt, cfg)

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{cfg.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )

                    # Call on_retry callback if provided
                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception:
                            pass  # Don't let callback errors affect retry logic

                    await asyncio.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def sync_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    config: RetryConfig | None = None
):
    """
    Synchronous retry decorator with exponential backoff.

    Same interface as async_retry but for synchronous functions.
    """
    import time

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cfg = config or RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base
            )

            last_exception = None

            for attempt in range(cfg.max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == cfg.max_attempts - 1:
                        logger.error(
                            f"{func.__name__} failed after {cfg.max_attempts} attempts: {e}"
                        )
                        raise

                    delay = calculate_delay(attempt, cfg)
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{cfg.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)

            if last_exception:
                raise last_exception

        return wrapper
    return decorator


class RetryContext:
    """
    Context manager for retry operations with state tracking.

    Usage:
        async with RetryContext(config=STANDARD_RETRY) as retry:
            while retry.should_continue():
                try:
                    result = await some_operation()
                    retry.success()
                    break
                except Exception as e:
                    await retry.handle_error(e)
    """

    def __init__(
        self,
        config: RetryConfig = None,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,)
    ):
        self.config = config or STANDARD_RETRY
        self.retryable_exceptions = retryable_exceptions
        self.attempt = 0
        self.succeeded = False
        self.last_exception: Exception | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def should_continue(self) -> bool:
        """Check if more retry attempts are available."""
        return self.attempt < self.config.max_attempts and not self.succeeded

    async def handle_error(self, exception: Exception):
        """Handle an error and wait before retrying."""
        self.last_exception = exception

        if not isinstance(exception, self.retryable_exceptions):
            raise exception

        if self.attempt >= self.config.max_attempts - 1:
            raise exception

        delay = calculate_delay(self.attempt, self.config)
        logger.warning(
            f"Retry attempt {self.attempt + 1}/{self.config.max_attempts} failed: {exception}. "
            f"Retrying in {delay:.2f}s"
        )

        await asyncio.sleep(delay)
        self.attempt += 1

    def success(self):
        """Mark the operation as successful."""
        self.succeeded = True


async def retry_with_fallback(
    primary_func: Callable,
    fallback_func: Callable,
    primary_retries: int = 2,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    fallback_on_timeout: bool = True
) -> Any:
    """
    Try primary function with retries, then fall back to secondary function.

    Args:
        primary_func: Primary async function to try
        fallback_func: Fallback async function if primary fails
        primary_retries: Number of retries for primary function
        retryable_exceptions: Exceptions that trigger retry/fallback
        fallback_on_timeout: Whether to fall back on timeout errors

    Returns:
        Result from either primary or fallback function

    Usage:
        result = await retry_with_fallback(
            primary_func=lambda: search_with_embeddings(query),
            fallback_func=lambda: search_with_keywords(query),
            primary_retries=2
        )
    """
    # Add timeout exceptions if needed
    exceptions = retryable_exceptions
    if fallback_on_timeout:
        exceptions = exceptions + (asyncio.TimeoutError,)

    # Try primary with retries
    last_exception = None
    for attempt in range(primary_retries):
        try:
            return await primary_func()
        except exceptions as e:
            last_exception = e
            if attempt < primary_retries - 1:
                delay = calculate_delay(attempt, STANDARD_RETRY)
                logger.warning(f"Primary function failed, retrying in {delay:.2f}s: {e}")
                await asyncio.sleep(delay)

    # Primary failed, try fallback
    logger.warning(f"Primary function failed after {primary_retries} attempts, using fallback")
    try:
        return await fallback_func()
    except Exception as e:
        logger.error(f"Fallback function also failed: {e}")
        # Re-raise the original exception from primary
        raise last_exception or e


# Common retryable exceptions
NETWORK_EXCEPTIONS = (
    ConnectionError,
    ConnectionRefusedError,
    ConnectionResetError,
    TimeoutError,
    asyncio.TimeoutError,
)

DATABASE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
)

API_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)
