"""
Global Error Handlers for MAP-IT API

Provides consistent error response formatting across all endpoints,
with user-friendly suggestions and proper HTTP status codes.
"""

from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Dict, Any

from ..core.exceptions import (
    MapItError,
    get_user_suggestion,
    get_http_status,
    ValidationError as MapItValidationError,
    ServiceUnavailableError,
    DataNotFoundError,
    RateLimitError,
    TimeoutError as MapItTimeoutError,
    AuthenticationError,
    AuthorizationError,
    CircuitBreakerOpenError,
)

logger = logging.getLogger(__name__)


def format_error_response(
    error_code: str,
    message: str,
    details: Dict[str, Any] = None,
    suggestion: str = None,
    recoverable: bool = True,
    request_id: str = None
) -> Dict[str, Any]:
    """
    Format a consistent error response.

    Args:
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Additional error context
        suggestion: User-friendly suggestion for resolution
        recoverable: Whether the operation can be retried
        request_id: Request ID for tracking

    Returns:
        Formatted error response dictionary
    """
    response = {
        "error": error_code,
        "message": message,
        "recoverable": recoverable,
    }

    if suggestion:
        response["suggestion"] = suggestion

    if details:
        response["details"] = details

    if request_id:
        response["request_id"] = request_id

    return response


async def mapit_exception_handler(request: Request, exc: MapItError) -> JSONResponse:
    """
    Handle all MAP-IT custom exceptions.

    Provides consistent error responses with appropriate HTTP status codes,
    error codes, and user-friendly suggestions.
    """
    # Log the error with context
    logger.error(
        f"MapItError: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True if exc.http_status >= 500 else False
    )

    # Get user-friendly suggestion
    suggestion = get_user_suggestion(exc.error_code)

    # Get request ID if available (could be set by middleware)
    request_id = getattr(request.state, "request_id", None)

    return JSONResponse(
        status_code=exc.http_status,
        content=format_error_response(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details if exc.details else None,
            suggestion=suggestion,
            recoverable=exc.recoverable,
            request_id=request_id
        ),
        headers=_get_error_headers(exc)
    )


def _get_error_headers(exc: MapItError) -> Dict[str, str]:
    """Get additional headers for error responses."""
    headers = {}

    # Add Retry-After header for rate limit errors
    if isinstance(exc, RateLimitError) and exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)

    # Add WWW-Authenticate header for auth errors
    if isinstance(exc, AuthenticationError):
        headers["WWW-Authenticate"] = "Bearer"

    return headers if headers else None


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle standard HTTP exceptions with consistent formatting.
    """
    # Map common HTTP status codes to error codes
    error_code_mapping = {
        400: "BAD_REQUEST",
        401: "AUTHENTICATION_REQUIRED",
        403: "AUTHORIZATION_FAILED",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        408: "REQUEST_TIMEOUT",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }

    error_code = error_code_mapping.get(exc.status_code, "HTTP_ERROR")

    logger.warning(
        f"HTTPException: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            error_code=error_code,
            message=str(exc.detail) if exc.detail else f"HTTP {exc.status_code} error",
            suggestion=get_user_suggestion(error_code),
            recoverable=exc.status_code >= 500 or exc.status_code == 429
        )
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors with detailed field information.
    """
    # Extract validation error details
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        f"Validation error: {len(errors)} field(s) invalid",
        extra={
            "errors": errors,
            "path": request.url.path,
            "method": request.method,
        }
    )

    return JSONResponse(
        status_code=422,
        content=format_error_response(
            error_code="VALIDATION_ERROR",
            message=f"Request validation failed: {len(errors)} error(s)",
            details={"validation_errors": errors},
            suggestion="Please check your input and ensure all required fields are provided in the correct format.",
            recoverable=False
        )
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions as a fallback.

    This handler catches any exception not caught by more specific handlers.
    It logs the full exception for debugging while returning a safe message to users.
    """
    # Log the full exception for debugging
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        }
    )

    # Check if this is a known Python exception that we can handle better
    error_code = "INTERNAL_ERROR"
    message = "An unexpected error occurred"
    suggestion = "Please try again. If the problem persists, contact support."

    # Handle specific Python exceptions
    if isinstance(exc, ConnectionError):
        error_code = "CONNECTION_ERROR"
        message = "Failed to connect to a required service"
        suggestion = "Please try again in a few moments."
    elif isinstance(exc, TimeoutError):
        error_code = "TIMEOUT"
        message = "The operation timed out"
        suggestion = "Try a simpler query or try again later."
    elif isinstance(exc, PermissionError):
        error_code = "PERMISSION_ERROR"
        message = "Permission denied"
        suggestion = "Check your permissions or contact support."
    elif isinstance(exc, ValueError):
        error_code = "VALUE_ERROR"
        message = "Invalid value provided"
        suggestion = "Please check your input values."

    return JSONResponse(
        status_code=500,
        content=format_error_response(
            error_code=error_code,
            message=message,
            suggestion=suggestion,
            recoverable=True
        )
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI application.

    This function should be called during app initialization to set up
    consistent error handling across all endpoints.

    Usage:
        from app.api.error_handlers import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
    """
    # Register MapItError handler for all custom exceptions
    app.add_exception_handler(MapItError, mapit_exception_handler)

    # Register handlers for specific exception subclasses
    # (FastAPI matches the most specific handler)
    app.add_exception_handler(ServiceUnavailableError, mapit_exception_handler)
    app.add_exception_handler(DataNotFoundError, mapit_exception_handler)
    app.add_exception_handler(RateLimitError, mapit_exception_handler)
    app.add_exception_handler(MapItTimeoutError, mapit_exception_handler)
    app.add_exception_handler(AuthenticationError, mapit_exception_handler)
    app.add_exception_handler(AuthorizationError, mapit_exception_handler)
    app.add_exception_handler(CircuitBreakerOpenError, mapit_exception_handler)

    # Override default HTTP and validation exception handlers
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Catch-all for unhandled exceptions
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Registered global exception handlers")


# ============================================================================
# MIDDLEWARE FOR REQUEST CONTEXT
# ============================================================================

import uuid
from starlette.middleware.base import BaseHTTPMiddleware


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request context (ID, timing) for error tracking.
    """

    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Add timing
        import time
        start_time = time.time()

        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log request duration for slow requests
        duration = time.time() - start_time
        if duration > 5.0:  # Log requests taking more than 5 seconds
            logger.warning(
                f"Slow request: {request.method} {request.url.path} took {duration:.2f}s",
                extra={"request_id": request_id, "duration": duration}
            )

        return response


def register_middleware(app: FastAPI) -> None:
    """
    Register middleware for error handling support.

    Usage:
        from app.api.error_handlers import register_middleware

        app = FastAPI()
        register_middleware(app)
    """
    app.add_middleware(RequestContextMiddleware)
    logger.info("Registered request context middleware")
