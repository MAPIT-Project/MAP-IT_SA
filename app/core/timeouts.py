"""
Centralized Timeout Configuration for MAP-IT

Provides consistent timeout handling across all services to prevent
request hangs and ensure responsive failure.
"""

import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TimeoutConfig:
    """
    Centralized timeout configuration for all MAP-IT operations.

    Usage:
        from app.core.timeouts import TimeoutConfig

        # Get timeout for an operation
        timeout = TimeoutConfig.LLM_CALL_TIMEOUT

        # Use with asyncio
        result = await asyncio.wait_for(
            some_async_operation(),
            timeout=TimeoutConfig.DATABASE_QUERY_TIMEOUT
        )
    """

    # =========================================================================
    # API LAYER TIMEOUTS
    # =========================================================================

    # Maximum time for an entire synchronous API request
    REQUEST_TIMEOUT: float = 120.0  # 2 minutes

    # Maximum time for streaming API requests
    STREAM_TIMEOUT: float = 300.0  # 5 minutes

    # Timeout for SSE keepalive (how often to send heartbeat)
    SSE_KEEPALIVE_TIMEOUT: float = 15.0

    # =========================================================================
    # SERVICE LAYER TIMEOUTS
    # =========================================================================

    # Single LLM call (Gemini, OpenAI, etc.)
    LLM_CALL_TIMEOUT: float = 60.0  # 1 minute

    # LLM streaming response timeout (time between tokens)
    LLM_STREAM_TIMEOUT: float = 30.0

    # Single tool execution
    TOOL_EXECUTION_TIMEOUT: float = 30.0  # 30 seconds

    # Complex tool (e.g., multi-step search)
    COMPLEX_TOOL_TIMEOUT: float = 60.0  # 1 minute

    # Database queries
    DATABASE_QUERY_TIMEOUT: float = 10.0  # 10 seconds

    # Complex database queries (aggregations, joins)
    DATABASE_COMPLEX_QUERY_TIMEOUT: float = 30.0

    # External API calls (EU Portal, etc.)
    EXTERNAL_API_TIMEOUT: float = 15.0

    # Neo4j graph queries
    GRAPH_QUERY_TIMEOUT: float = 15.0

    # Vector similarity search
    VECTOR_SEARCH_TIMEOUT: float = 10.0

    # Embedding generation
    EMBEDDING_TIMEOUT: float = 30.0

    # =========================================================================
    # AGENT TIMEOUTS
    # =========================================================================

    # Single agent iteration (think + act + observe)
    AGENT_ITERATION_TIMEOUT: float = 45.0

    # Total agent processing time (all iterations)
    AGENT_TOTAL_TIMEOUT: float = 180.0  # 3 minutes

    # Agent planning phase
    AGENT_PLANNING_TIMEOUT: float = 30.0

    # Agent evaluation phase
    AGENT_EVALUATION_TIMEOUT: float = 20.0

    # =========================================================================
    # CONNECTION TIMEOUTS
    # =========================================================================

    # Database connection acquisition
    DB_CONNECTION_TIMEOUT: float = 5.0

    # Redis connection timeout
    REDIS_CONNECTION_TIMEOUT: float = 3.0

    # Neo4j connection timeout
    NEO4J_CONNECTION_TIMEOUT: float = 5.0

    # HTTP client connection timeout
    HTTP_CONNECTION_TIMEOUT: float = 10.0

    # HTTP read timeout
    HTTP_READ_TIMEOUT: float = 30.0

    # =========================================================================
    # PROPOSAL WRITING TIMEOUTS
    # =========================================================================

    # Section generation timeout
    SECTION_GENERATION_TIMEOUT: float = 120.0  # 2 minutes

    # Proposal evaluation timeout
    PROPOSAL_EVALUATION_TIMEOUT: float = 90.0

    # Document export timeout
    EXPORT_TIMEOUT: float = 60.0


async def with_timeout(
    coro,
    timeout: float,
    error_message: str = "Operation timed out",
    return_on_timeout: Any = None,
    raise_on_timeout: bool = True,
):
    """
    Execute a coroutine with a timeout.

    Args:
        coro: The coroutine to execute
        timeout: Timeout in seconds
        error_message: Custom error message for timeout
        return_on_timeout: Value to return on timeout (if raise_on_timeout=False)
        raise_on_timeout: Whether to raise TimeoutError (default True)

    Returns:
        The result of the coroutine, or return_on_timeout if timed out

    Raises:
        asyncio.TimeoutError: If operation times out and raise_on_timeout=True

    Usage:
        # With exception
        result = await with_timeout(
            fetch_data(),
            timeout=10.0,
            error_message="Failed to fetch data"
        )

        # With fallback value
        result = await with_timeout(
            fetch_data(),
            timeout=10.0,
            return_on_timeout=[],
            raise_on_timeout=False
        )
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except TimeoutError as e:
        logger.warning(f"Timeout after {timeout}s: {error_message}")
        if raise_on_timeout:
            from .exceptions import TimeoutError as MapItTimeoutError

            raise MapItTimeoutError(message=error_message, timeout_seconds=timeout) from e
        return return_on_timeout


def timeout_decorator(seconds: float = None, timeout_type: str = None, error_message: str = None):
    """
    Decorator to add timeout to async functions.

    Args:
        seconds: Explicit timeout in seconds
        timeout_type: Use a predefined timeout from TimeoutConfig
            Options: "llm", "tool", "database", "external_api", "agent"
        error_message: Custom error message

    Usage:
        @timeout_decorator(seconds=30)
        async def my_function():
            ...

        @timeout_decorator(timeout_type="llm")
        async def call_llm():
            ...
    """
    # Get timeout value
    if seconds is not None:
        timeout = seconds
    elif timeout_type:
        timeout_mapping = {
            "llm": TimeoutConfig.LLM_CALL_TIMEOUT,
            "tool": TimeoutConfig.TOOL_EXECUTION_TIMEOUT,
            "database": TimeoutConfig.DATABASE_QUERY_TIMEOUT,
            "external_api": TimeoutConfig.EXTERNAL_API_TIMEOUT,
            "agent": TimeoutConfig.AGENT_ITERATION_TIMEOUT,
            "graph": TimeoutConfig.GRAPH_QUERY_TIMEOUT,
            "vector": TimeoutConfig.VECTOR_SEARCH_TIMEOUT,
            "embedding": TimeoutConfig.EMBEDDING_TIMEOUT,
        }
        timeout = timeout_mapping.get(timeout_type, TimeoutConfig.REQUEST_TIMEOUT)
    else:
        timeout = TimeoutConfig.REQUEST_TIMEOUT

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            msg = error_message or f"{func.__name__} timed out after {timeout}s"
            return await with_timeout(func(*args, **kwargs), timeout=timeout, error_message=msg)

        return wrapper

    return decorator


class TimeoutContext:
    """
    Context manager for operations with timeout.

    Usage:
        async with TimeoutContext(30.0, "Database query") as ctx:
            result = await db.execute(query)

        # Check if timed out
        if ctx.timed_out:
            # Handle timeout
            pass
    """

    def __init__(
        self, timeout: float, operation_name: str = "Operation", raise_on_timeout: bool = True
    ):
        self.timeout = timeout
        self.operation_name = operation_name
        self.raise_on_timeout = raise_on_timeout
        self.timed_out = False
        self._task: asyncio.Task | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is asyncio.TimeoutError:
            self.timed_out = True
            logger.warning(f"Timeout in {self.operation_name} after {self.timeout}s")
            if not self.raise_on_timeout:
                return True  # Suppress the exception
        return False


def get_timeout_for_operation(operation: str) -> float:
    """
    Get the appropriate timeout for a named operation.

    Args:
        operation: Name of the operation

    Returns:
        Timeout in seconds

    Usage:
        timeout = get_timeout_for_operation("llm_call")
    """
    operation_timeouts = {
        # API operations
        "request": TimeoutConfig.REQUEST_TIMEOUT,
        "stream": TimeoutConfig.STREAM_TIMEOUT,
        # Service operations
        "llm_call": TimeoutConfig.LLM_CALL_TIMEOUT,
        "llm_stream": TimeoutConfig.LLM_STREAM_TIMEOUT,
        "tool": TimeoutConfig.TOOL_EXECUTION_TIMEOUT,
        "complex_tool": TimeoutConfig.COMPLEX_TOOL_TIMEOUT,
        "database": TimeoutConfig.DATABASE_QUERY_TIMEOUT,
        "database_complex": TimeoutConfig.DATABASE_COMPLEX_QUERY_TIMEOUT,
        "external_api": TimeoutConfig.EXTERNAL_API_TIMEOUT,
        "graph": TimeoutConfig.GRAPH_QUERY_TIMEOUT,
        "vector_search": TimeoutConfig.VECTOR_SEARCH_TIMEOUT,
        "embedding": TimeoutConfig.EMBEDDING_TIMEOUT,
        # Agent operations
        "agent_iteration": TimeoutConfig.AGENT_ITERATION_TIMEOUT,
        "agent_total": TimeoutConfig.AGENT_TOTAL_TIMEOUT,
        "agent_planning": TimeoutConfig.AGENT_PLANNING_TIMEOUT,
        "agent_evaluation": TimeoutConfig.AGENT_EVALUATION_TIMEOUT,
        # Proposal operations
        "section_generation": TimeoutConfig.SECTION_GENERATION_TIMEOUT,
        "proposal_evaluation": TimeoutConfig.PROPOSAL_EVALUATION_TIMEOUT,
        "export": TimeoutConfig.EXPORT_TIMEOUT,
    }

    return operation_timeouts.get(operation, TimeoutConfig.REQUEST_TIMEOUT)
