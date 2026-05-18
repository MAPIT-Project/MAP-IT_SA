# Task 04: Error Handling & Async Fixes

> **Phase:** 0 - Foundation Fixes
> **Priority:** P0 (Production Blocker)
> **Estimated Effort:** 3-4 hours
> **Status:** Not Started
> **Depends On:** Tasks 01-03

---

## Problem Statement

The current codebase has inconsistent async patterns and limited error handling:

1. **Async/Await Inconsistencies**
   - Functions marked `async` but containing blocking calls
   - Mixed sync/async patterns

2. **No Retry Logic**
   - Single failures crash the entire operation
   - No exponential backoff

3. **Poor Error Messages**
   - Generic "Error generating draft" messages
   - No context about what failed

4. **Connection Pool Issues**
   - Some endpoints create new pools instead of reusing
   - Potential resource leaks

---

## Solution

Implement:
1. Consistent async patterns
2. Retry decorators with exponential backoff
3. Custom exceptions with context
4. Connection pool management
5. Graceful degradation

---

## Implementation

### Step 1: Create Custom Exceptions

**File:** `app/services/proposal_writing/exceptions.py`

```python
"""
Custom Exceptions for Proposal Writing

Structured exceptions with context for better error handling.
"""

from typing import Dict, Any, Optional


class ProposalWritingError(Exception):
    """Base exception for proposal writing errors."""

    def __init__(
        self,
        message: str,
        code: str = "PROPOSAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.recoverable = recoverable
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable
        }


class AIGenerationError(ProposalWritingError):
    """Error during AI content generation."""

    def __init__(
        self,
        message: str,
        provider: str = None,
        prompt_length: int = None,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            code="AI_GENERATION_ERROR",
            details={
                "provider": provider,
                "prompt_length": prompt_length,
                **(details or {})
            },
            recoverable=True
        )


class CallAnalysisError(ProposalWritingError):
    """Error analyzing call documents."""

    def __init__(
        self,
        message: str,
        call_id: str = None,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            code="CALL_ANALYSIS_ERROR",
            details={"call_id": call_id, **(details or {})},
            recoverable=True
        )


class DatabaseError(ProposalWritingError):
    """Database operation error."""

    def __init__(
        self,
        message: str,
        operation: str = None,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details={"operation": operation, **(details or {})},
            recoverable=True
        )


class ValidationError(ProposalWritingError):
    """Input validation error."""

    def __init__(
        self,
        message: str,
        field: str = None,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, **(details or {})},
            recoverable=False
        )


class RateLimitError(ProposalWritingError):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str,
        provider: str = None,
        retry_after: int = None,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            code="RATE_LIMIT_ERROR",
            details={
                "provider": provider,
                "retry_after": retry_after,
                **(details or {})
            },
            recoverable=True
        )


class TimeoutError(ProposalWritingError):
    """Operation timed out."""

    def __init__(
        self,
        message: str,
        operation: str = None,
        timeout_seconds: int = None,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            code="TIMEOUT_ERROR",
            details={
                "operation": operation,
                "timeout_seconds": timeout_seconds,
                **(details or {})
            },
            recoverable=True
        )
```

---

### Step 2: Create Retry Decorator

**File:** `app/services/proposal_writing/retry.py`

```python
"""
Retry Utilities

Decorators for automatic retry with exponential backoff.
"""

import asyncio
import logging
import functools
from typing import Type, Tuple, Callable, Any
import random

from app.services.proposal_writing.exceptions import (
    ProposalWritingError,
    RateLimitError,
    TimeoutError
)

logger = logging.getLogger(__name__)


def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ProposalWritingError,
        ConnectionError,
        asyncio.TimeoutError
    ),
    on_retry: Callable[[Exception, int], None] = None
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
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Synchronous retry decorator."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import time
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        raise

                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(f"{func.__name__} failed, retrying in {delay:.1f}s")
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
        self._last_failure_time = 0
        self._state = "CLOSED"
        self._half_open_calls = 0

    @property
    def state(self) -> str:
        import time

        if self._state == "OPEN":
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "HALF_OPEN"
                self._half_open_calls = 0

        return self._state

    def record_success(self):
        """Record a successful call."""
        self._failures = 0
        if self._state == "HALF_OPEN":
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = "CLOSED"

    def record_failure(self):
        """Record a failed call."""
        import time

        self._failures += 1
        self._last_failure_time = time.time()

        if self._failures >= self.failure_threshold:
            self._state = "OPEN"

    def can_execute(self) -> bool:
        """Check if a call can be made."""
        state = self.state

        if state == "CLOSED":
            return True
        elif state == "HALF_OPEN":
            return self._half_open_calls < self.half_open_max_calls
        else:  # OPEN
            return False
```

---

### Step 3: Create Database Pool Manager

**File:** `app/services/proposal_writing/db_manager.py`

```python
"""
Database Pool Manager

Centralized connection pool management for proposal writing services.
"""

import logging
import asyncio
from typing import Optional
import asyncpg
import os

logger = logging.getLogger(__name__)


class DatabasePoolManager:
    """
    Singleton database pool manager.

    Ensures all services share the same connection pool.
    """

    _instance = None
    _pool: Optional[asyncpg.Pool] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_pool(self) -> asyncpg.Pool:
        """Get or create the connection pool."""

        if self._pool is None or self._pool._closed:
            async with self._lock:
                # Double-check after acquiring lock
                if self._pool is None or self._pool._closed:
                    self._pool = await self._create_pool()

        return self._pool

    async def _create_pool(self) -> asyncpg.Pool:
        """Create a new connection pool."""

        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            raise RuntimeError("DATABASE_URL not set")

        logger.info("Creating database connection pool")

        pool = await asyncpg.create_pool(
            database_url,
            min_size=5,
            max_size=20,
            max_inactive_connection_lifetime=300,
            command_timeout=60
        )

        return pool

    async def close(self):
        """Close the connection pool."""

        if self._pool and not self._pool._closed:
            await self._pool.close()
            logger.info("Database connection pool closed")


# Global instance
db_manager = DatabasePoolManager()


async def get_db_pool() -> asyncpg.Pool:
    """Get the shared database pool."""
    return await db_manager.get_pool()


async def close_db_pool():
    """Close the shared database pool."""
    await db_manager.close()
```

---

### Step 4: Update Services with Error Handling

**File:** Update `app/services/proposal_writing/draft_generator.py`

```python
# Add imports
from app.services.proposal_writing.exceptions import (
    AIGenerationError,
    CallAnalysisError,
    ValidationError
)
from app.services.proposal_writing.retry import async_retry

class ProposalDraftGenerator:

    @async_retry(max_retries=2, base_delay=1.0)
    async def generate_section_draft(
        self,
        call_id: str,
        section_id: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a draft for a specific proposal section."""

        # Input validation
        if not call_id:
            raise ValidationError("call_id is required", field="call_id")

        if not section_id:
            raise ValidationError("section_id is required", field="section_id")

        valid_sections = [
            "excellence.objectives", "excellence.methodology", "excellence.beyond_sota",
            "impact.pathways", "impact.dissemination",
            "implementation.work_plan", "implementation.consortium"
        ]

        if section_id not in valid_sections:
            raise ValidationError(
                f"Invalid section_id. Must be one of: {valid_sections}",
                field="section_id"
            )

        logger.info(f"Generating draft for {section_id} in call {call_id}")

        try:
            # Get call analysis
            call_analysis = await self._analyze_call_with_retry(call_id)

        except Exception as e:
            raise CallAnalysisError(
                f"Failed to analyze call: {e}",
                call_id=call_id
            )

        try:
            # Generate draft
            prompt = self._build_context_aware_prompt(...)
            response = await self.ai_service.generate_text(prompt)
            draft_text = response

        except Exception as e:
            raise AIGenerationError(
                f"Failed to generate draft: {e}",
                provider="gemini",
                prompt_length=len(prompt) if 'prompt' in locals() else 0
            )

        # Post-processing
        draft_text = self._ensure_eu_alignment_terms(draft_text, section_id, call_analysis['cluster']['code'])

        return {
            "draft_text": draft_text,
            "word_count": len(draft_text.split()),
            # ... rest of response
        }

    @async_retry(max_retries=2)
    async def _analyze_call_with_retry(self, call_id: str) -> Dict[str, Any]:
        """Analyze call with retry logic."""
        return await self.call_understanding.analyze_call(
            call_id=call_id,
            call_text=self._get_call_text(call_id),
            call_title=None
        )
```

---

### Step 5: Add Error Handlers to API

**File:** Update `app/api/proposal_routes.py`

```python
from fastapi import HTTPException
from app.services.proposal_writing.exceptions import (
    ProposalWritingError,
    ValidationError,
    AIGenerationError,
    RateLimitError
)


# Exception handler
@router.exception_handler(ProposalWritingError)
async def proposal_error_handler(request, exc: ProposalWritingError):
    """Handle proposal writing errors."""

    status_code = 500

    if isinstance(exc, ValidationError):
        status_code = 400
    elif isinstance(exc, RateLimitError):
        status_code = 429

    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict()
    )


# Update endpoints to use better error handling
@router.post("/draft/generate")
async def generate_draft(request: GenerateDraftRequest):
    """Generate section draft with proper error handling."""

    try:
        result = await draft_generator.generate_section_draft(
            call_id=request.call_id,
            section_id=request.section_id,
            user_context=request.user_context
        )
        return result

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())

    except RateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail=e.to_dict(),
            headers={"Retry-After": str(e.details.get("retry_after", 60))}
        )

    except AIGenerationError as e:
        # Log full error, return user-friendly message
        logger.error(f"AI generation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "AI_SERVICE_UNAVAILABLE",
                "message": "AI service temporarily unavailable. Please try again.",
                "recoverable": True
            }
        )

    except ProposalWritingError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "recoverable": True
            }
        )
```

---

## Testing Plan

```python
# tests/test_error_handling.py

import pytest
from app.services.proposal_writing.retry import async_retry, CircuitBreaker
from app.services.proposal_writing.exceptions import AIGenerationError

@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    """Test that retry eventually succeeds."""

    call_count = 0

    @async_retry(max_retries=3, base_delay=0.1)
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise AIGenerationError("Temporary failure")
        return "success"

    result = await flaky_function()

    assert result == "success"
    assert call_count == 3

@pytest.mark.asyncio
async def test_retry_raises_after_max_attempts():
    """Test that retry raises after max attempts."""

    @async_retry(max_retries=2, base_delay=0.1)
    async def always_fails():
        raise AIGenerationError("Always fails")

    with pytest.raises(AIGenerationError):
        await always_fails()

def test_circuit_breaker_opens_after_failures():
    """Test circuit breaker opens after threshold."""

    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

    assert cb.state == "CLOSED"

    cb.record_failure()
    cb.record_failure()
    cb.record_failure()

    assert cb.state == "OPEN"
    assert not cb.can_execute()
```

---

## Acceptance Criteria

- [ ] Custom exceptions provide useful context
- [ ] Retry decorator works with exponential backoff
- [ ] Circuit breaker prevents cascading failures
- [ ] Database pool is shared across services
- [ ] API returns appropriate HTTP status codes
- [ ] Error messages are user-friendly
- [ ] Full errors are logged for debugging

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `app/services/proposal_writing/exceptions.py` | CREATE |
| `app/services/proposal_writing/retry.py` | CREATE |
| `app/services/proposal_writing/db_manager.py` | CREATE |
| `app/services/proposal_writing/draft_generator.py` | MODIFY |
| `app/api/proposal_routes.py` | MODIFY |
| `tests/test_error_handling.py` | CREATE |

---

## Next Task

After completing this task, proceed to:
→ **Task 05: Build Proposal Learning Service**
