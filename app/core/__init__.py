"""
Core application configuration, settings, and infrastructure.

This module provides:
- Configuration management (config.py)
- Custom exceptions (exceptions.py)
- Timeout configuration (timeouts.py)
- Retry utilities (retry.py)
- Circuit breaker pattern (circuit_breaker.py)
- Database connection pool (database.py)
- Service availability checking (service_availability.py)
- Neo4j connection management (neo4j_config.py)
- Application dependencies (dependencies.py)
- Conversation locking (conversation_lock.py) - prevents race conditions
- Atomic storage (atomic_storage.py) - ensures message consistency
"""

from .config import settings
from .exceptions import (
    MapItError,
    ServiceUnavailableError,
    DataNotFoundError,
    ValidationError,
    RateLimitError,
    TimeoutError,
    ToolExecutionError,
    AgentError,
    CircuitBreakerOpenError,
    AuthenticationError,
    AuthorizationError,
)
from .timeouts import TimeoutConfig, with_timeout, timeout_decorator
from .retry import (
    async_retry,
    sync_retry,
    RetryConfig,
    STANDARD_RETRY,
    AGGRESSIVE_RETRY,
    GENTLE_RETRY,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    get_circuit_breaker,
    get_neo4j_circuit,
    get_gemini_circuit,
    get_eu_portal_circuit,
)
from .conversation_lock import (
    ConversationLockManager,
    get_conversation_lock,
)
from .atomic_storage import (
    AtomicMessageStorage,
    StorageResult,
    get_atomic_storage,
)

__all__ = [
    # Config
    "settings",
    # Exceptions
    "MapItError",
    "ServiceUnavailableError",
    "DataNotFoundError",
    "ValidationError",
    "RateLimitError",
    "TimeoutError",
    "ToolExecutionError",
    "AgentError",
    "CircuitBreakerOpenError",
    "AuthenticationError",
    "AuthorizationError",
    # Timeouts
    "TimeoutConfig",
    "with_timeout",
    "timeout_decorator",
    # Retry
    "async_retry",
    "sync_retry",
    "RetryConfig",
    "STANDARD_RETRY",
    "AGGRESSIVE_RETRY",
    "GENTLE_RETRY",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    "get_circuit_breaker",
    "get_neo4j_circuit",
    "get_gemini_circuit",
    "get_eu_portal_circuit",
    # Conversation Locking
    "ConversationLockManager",
    "get_conversation_lock",
    # Atomic Storage
    "AtomicMessageStorage",
    "StorageResult",
    "get_atomic_storage",
]
