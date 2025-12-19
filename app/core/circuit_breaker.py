"""
Circuit Breaker Pattern Implementation for MAP-IT

Prevents cascading failures by temporarily blocking calls to failing services.
Implements the standard circuit breaker states: CLOSED, OPEN, HALF_OPEN.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any, Optional, Dict
import logging
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, calls pass through
    OPEN = "open"          # Circuit tripped, calls are blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0  # Calls rejected while circuit open
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_state_change: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 3  # Successes in half-open before closing
    recovery_timeout: int = 60  # Seconds before trying half-open
    half_open_max_calls: int = 3  # Max calls in half-open state
    failure_rate_threshold: float = 0.5  # Alternative: trip on failure rate
    window_size: int = 10  # Number of calls for failure rate calculation


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    Usage:
        # Create circuit breaker for a service
        neo4j_circuit = CircuitBreaker(
            name="neo4j",
            failure_threshold=5,
            recovery_timeout=60
        )

        # Use with async functions
        result = await neo4j_circuit.call(async_function, arg1, arg2)

        # Check state
        if neo4j_circuit.is_available():
            # Service might be available
            pass
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            recovery_timeout=recovery_timeout
        )
        self.expected_exception = expected_exception

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._lock = Lock()
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def stats(self) -> CircuitStats:
        """Get circuit statistics."""
        return self._stats

    def is_available(self) -> bool:
        """Check if the circuit allows calls (not fully open)."""
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        if self._state == CircuitState.OPEN:
            return self._should_attempt_reset()
        return False

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try resetting (half-open)."""
        if not self._stats.last_failure_time:
            return True

        recovery_time = timedelta(seconds=self.config.recovery_timeout)
        return datetime.now() - self._stats.last_failure_time > recovery_time

    def _transition_to(self, new_state: CircuitState):
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._stats.last_state_change = datetime.now()

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0

        logger.info(
            f"Circuit '{self.name}' transitioned: {old_state.value} -> {new_state.value}"
        )

    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            self._stats.total_calls += 1
            self._stats.successful_calls += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = datetime.now()

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._stats.consecutive_successes >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def _on_failure(self, exception: Exception):
        """Handle failed call."""
        with self._lock:
            self._stats.total_calls += 1
            self._stats.failed_calls += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = datetime.now()

            if self._state == CircuitState.HALF_OPEN:
                # Failure in half-open -> back to open
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._stats.consecutive_failures >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
                    logger.warning(
                        f"Circuit '{self.name}' opened after "
                        f"{self._stats.consecutive_failures} consecutive failures"
                    )

    async def call(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result from the function

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Original exception: If function fails
        """
        # Check if call should be allowed
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN)
            else:
                self._stats.rejected_calls += 1
                from .exceptions import CircuitBreakerOpenError
                raise CircuitBreakerOpenError(
                    circuit_name=self.name,
                    recovery_time=self._time_until_recovery()
                )

        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.config.half_open_max_calls:
                self._stats.rejected_calls += 1
                from .exceptions import CircuitBreakerOpenError
                raise CircuitBreakerOpenError(
                    circuit_name=self.name,
                    recovery_time=10,  # Short wait for half-open limit
                    message=f"Circuit '{self.name}' is in half-open state with max calls reached"
                )
            self._half_open_calls += 1

        # Execute the function
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(e)
            raise

    def _time_until_recovery(self) -> int:
        """Calculate seconds until recovery attempt."""
        if not self._stats.last_failure_time:
            return 0

        elapsed = (datetime.now() - self._stats.last_failure_time).total_seconds()
        remaining = self.config.recovery_timeout - elapsed
        return max(0, int(remaining))

    def reset(self):
        """Manually reset the circuit breaker to closed state."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._stats.consecutive_failures = 0
            self._stats.consecutive_successes = 0
            self._half_open_calls = 0
            logger.info(f"Circuit '{self.name}' manually reset")

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the circuit breaker."""
        return {
            "name": self.name,
            "state": self._state.value,
            "stats": {
                "total_calls": self._stats.total_calls,
                "successful_calls": self._stats.successful_calls,
                "failed_calls": self._stats.failed_calls,
                "rejected_calls": self._stats.rejected_calls,
                "consecutive_failures": self._stats.consecutive_failures,
                "consecutive_successes": self._stats.consecutive_successes,
                "last_failure": self._stats.last_failure_time.isoformat() if self._stats.last_failure_time else None,
                "last_success": self._stats.last_success_time.isoformat() if self._stats.last_success_time else None,
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "recovery_timeout": self.config.recovery_timeout,
            },
            "time_until_recovery": self._time_until_recovery() if self._state == CircuitState.OPEN else None
        }


# ============================================================================
# GLOBAL CIRCUIT BREAKERS
# ============================================================================

# Circuit breakers for external services
# These are instantiated lazily to avoid import-time errors

_circuit_breakers: Dict[str, CircuitBreaker] = {}
_circuit_lock = Lock()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
) -> CircuitBreaker:
    """
    Get or create a named circuit breaker.

    Args:
        name: Unique name for the circuit breaker
        failure_threshold: Failures before opening (only used on creation)
        recovery_timeout: Seconds before recovery attempt (only used on creation)
        expected_exception: Exception type that triggers failure (only used on creation)

    Returns:
        CircuitBreaker instance
    """
    with _circuit_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception
            )
        return _circuit_breakers[name]


# Pre-configured circuit breakers for common services
def get_neo4j_circuit() -> CircuitBreaker:
    """Get circuit breaker for Neo4j."""
    return get_circuit_breaker(
        name="neo4j",
        failure_threshold=5,
        recovery_timeout=60
    )


def get_gemini_circuit() -> CircuitBreaker:
    """Get circuit breaker for Gemini API."""
    return get_circuit_breaker(
        name="gemini",
        failure_threshold=3,
        recovery_timeout=30
    )


def get_eu_portal_circuit() -> CircuitBreaker:
    """Get circuit breaker for EU Portal API."""
    return get_circuit_breaker(
        name="eu_portal",
        failure_threshold=3,
        recovery_timeout=120
    )


def get_embedding_circuit() -> CircuitBreaker:
    """Get circuit breaker for embedding service."""
    return get_circuit_breaker(
        name="embedding",
        failure_threshold=3,
        recovery_timeout=60
    )


def get_all_circuit_statuses() -> Dict[str, Dict[str, Any]]:
    """Get status of all circuit breakers."""
    return {name: cb.get_status() for name, cb in _circuit_breakers.items()}


def reset_all_circuits():
    """Reset all circuit breakers to closed state."""
    for cb in _circuit_breakers.values():
        cb.reset()
    logger.info("All circuit breakers reset")


# ============================================================================
# DECORATOR FOR CIRCUIT BREAKER
# ============================================================================

def with_circuit_breaker(
    circuit_name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
):
    """
    Decorator to wrap async functions with a circuit breaker.

    Usage:
        @with_circuit_breaker("neo4j", failure_threshold=5)
        async def query_neo4j(query: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            circuit = get_circuit_breaker(
                name=circuit_name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception
            )
            return await circuit.call(func, *args, **kwargs)
        return wrapper
    return decorator
