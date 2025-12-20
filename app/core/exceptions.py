"""
Global Exception Framework for MAP-IT

Provides structured exceptions with actionable error codes, user-friendly messages,
and detailed context for debugging. All exceptions can be serialized to JSON
for API responses.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class MapItError(Exception):
    """
    Base exception for all MAP-IT errors.

    All exceptions include:
    - error_code: Machine-readable code for client handling
    - message: Human-readable error description
    - details: Additional context for debugging
    - recoverable: Whether the operation can be retried
    - http_status: Suggested HTTP status code for API responses
    """

    def __init__(
        self,
        message: str,
        error_code: str = "MAPIT_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        http_status: int = 500
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.recoverable = recoverable
        self.http_status = http_status
        self.timestamp = datetime.now(timezone.utc).isoformat()
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp
        }

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


# ============================================================================
# SERVICE AVAILABILITY EXCEPTIONS
# ============================================================================

class ServiceUnavailableError(MapItError):
    """External service is unavailable (database, API, etc.)."""

    def __init__(
        self,
        message: str,
        service_name: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=f"{service_name.upper()}_UNAVAILABLE" if service_name else "SERVICE_UNAVAILABLE",
            details={"service": service_name, **(details or {})},
            recoverable=True,
            http_status=503
        )
        self.service_name = service_name


class Neo4jUnavailableError(ServiceUnavailableError):
    """Neo4j graph database is unavailable."""

    def __init__(self, message: str = "Graph database is temporarily unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, service_name="neo4j", details=details)


class PostgresUnavailableError(ServiceUnavailableError):
    """PostgreSQL database is unavailable."""

    def __init__(self, message: str = "Database is temporarily unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, service_name="postgres", details=details)


class RedisUnavailableError(ServiceUnavailableError):
    """Redis cache is unavailable."""

    def __init__(self, message: str = "Cache service is temporarily unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, service_name="redis", details=details)


class EmbeddingServiceUnavailableError(ServiceUnavailableError):
    """Embedding generation service is unavailable."""

    def __init__(self, message: str = "Embedding service is temporarily unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, service_name="embedding", details=details)


class AIProviderUnavailableError(ServiceUnavailableError):
    """AI provider (Gemini, OpenAI, etc.) is unavailable."""

    def __init__(
        self,
        message: str = "AI provider is temporarily unavailable",
        provider: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            service_name=provider or "ai_provider",
            details={"provider": provider, **(details or {})}
        )


class ExternalAPIUnavailableError(ServiceUnavailableError):
    """External API (EU Portal, etc.) is unavailable."""

    def __init__(
        self,
        message: str = "External API is temporarily unavailable",
        api_name: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            service_name=api_name or "external_api",
            details={"api": api_name, **(details or {})}
        )


# ============================================================================
# DATA EXCEPTIONS
# ============================================================================

class DataNotFoundError(MapItError):
    """Requested data was not found."""

    def __init__(
        self,
        message: str,
        resource_type: str = None,
        resource_id: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=f"{resource_type.upper()}_NOT_FOUND" if resource_type else "NOT_FOUND",
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
                **(details or {})
            },
            recoverable=False,
            http_status=404
        )


class CallNotFoundError(DataNotFoundError):
    """Funding call not found."""

    def __init__(self, call_id: str, message: str = None):
        super().__init__(
            message=message or f"Funding call '{call_id}' not found",
            resource_type="call",
            resource_id=call_id
        )


class ProjectNotFoundError(DataNotFoundError):
    """Project not found."""

    def __init__(self, project_id: str, message: str = None):
        super().__init__(
            message=message or f"Project '{project_id}' not found",
            resource_type="project",
            resource_id=project_id
        )


class ConversationNotFoundError(DataNotFoundError):
    """Conversation not found."""

    def __init__(self, conversation_id: str, message: str = None):
        super().__init__(
            message=message or f"Conversation '{conversation_id}' not found",
            resource_type="conversation",
            resource_id=conversation_id
        )


class ProposalSessionNotFoundError(DataNotFoundError):
    """Proposal session not found."""

    def __init__(self, session_id: str, message: str = None):
        super().__init__(
            message=message or f"Proposal session '{session_id}' not found",
            resource_type="proposal_session",
            resource_id=session_id
        )


class DocumentNotFoundError(DataNotFoundError):
    """Document not found."""

    def __init__(self, document_id: str, message: str = None):
        super().__init__(
            message=message or f"Document '{document_id}' not found",
            resource_type="document",
            resource_id=document_id
        )


# ============================================================================
# VALIDATION EXCEPTIONS
# ============================================================================

class ValidationError(MapItError):
    """Input validation failed."""

    def __init__(
        self,
        message: str,
        field: str = None,
        value: Any = None,
        constraints: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={
                "field": field,
                "value": str(value)[:100] if value is not None else None,
                "constraints": constraints,
                **(details or {})
            },
            recoverable=False,
            http_status=422
        )


class InvalidInputError(ValidationError):
    """Input data is invalid."""

    def __init__(self, message: str, field: str = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, field=field, details=details)


class MissingFieldError(ValidationError):
    """Required field is missing."""

    def __init__(self, field: str, message: str = None):
        super().__init__(
            message=message or f"Required field '{field}' is missing",
            field=field
        )


class InvalidFormatError(ValidationError):
    """Field format is invalid."""

    def __init__(self, field: str, expected_format: str, message: str = None):
        super().__init__(
            message=message or f"Field '{field}' has invalid format. Expected: {expected_format}",
            field=field,
            constraints={"expected_format": expected_format}
        )


# ============================================================================
# RATE LIMITING EXCEPTIONS
# ============================================================================

class RateLimitError(MapItError):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = None,
        limit_type: str = None,  # "minute", "hour", "day"
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="RATE_LIMITED",
            details={
                "retry_after_seconds": retry_after,
                "limit_type": limit_type,
                **(details or {})
            },
            recoverable=True,
            http_status=429
        )
        self.retry_after = retry_after


class APIRateLimitError(RateLimitError):
    """External API rate limit exceeded."""

    def __init__(
        self,
        api_name: str,
        retry_after: int = None,
        message: str = None
    ):
        super().__init__(
            message=message or f"Rate limit exceeded for {api_name}",
            retry_after=retry_after,
            details={"api": api_name}
        )


# ============================================================================
# TIMEOUT EXCEPTIONS
# ============================================================================

class TimeoutError(MapItError):
    """Operation timed out."""

    def __init__(
        self,
        message: str = "Operation timed out",
        operation: str = None,
        timeout_seconds: float = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="TIMEOUT",
            details={
                "operation": operation,
                "timeout_seconds": timeout_seconds,
                **(details or {})
            },
            recoverable=True,
            http_status=504
        )


class LLMTimeoutError(TimeoutError):
    """LLM call timed out."""

    def __init__(self, provider: str = None, timeout_seconds: float = None):
        super().__init__(
            message=f"LLM call timed out after {timeout_seconds}s" if timeout_seconds else "LLM call timed out",
            operation="llm_call",
            timeout_seconds=timeout_seconds,
            details={"provider": provider}
        )


class ToolExecutionTimeoutError(TimeoutError):
    """Tool execution timed out."""

    def __init__(self, tool_name: str, timeout_seconds: float = None):
        super().__init__(
            message=f"Tool '{tool_name}' execution timed out",
            operation=f"tool:{tool_name}",
            timeout_seconds=timeout_seconds,
            details={"tool": tool_name}
        )


class DatabaseTimeoutError(TimeoutError):
    """Database query timed out."""

    def __init__(self, operation: str = None, timeout_seconds: float = None):
        super().__init__(
            message="Database query timed out",
            operation=operation or "database_query",
            timeout_seconds=timeout_seconds
        )


# ============================================================================
# TOOL EXCEPTIONS
# ============================================================================

class ToolExecutionError(MapItError):
    """Tool failed to execute."""

    def __init__(
        self,
        message: str,
        tool_name: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="TOOL_EXECUTION_ERROR",
            details={"tool": tool_name, **(details or {})},
            recoverable=True,
            http_status=500
        )


class ToolNotFoundError(MapItError):
    """Requested tool does not exist."""

    def __init__(self, tool_name: str):
        super().__init__(
            message=f"Tool '{tool_name}' not found",
            error_code="TOOL_NOT_FOUND",
            details={"tool": tool_name},
            recoverable=False,
            http_status=400
        )


class ToolValidationError(MapItError):
    """Tool arguments are invalid."""

    def __init__(
        self,
        message: str,
        tool_name: str = None,
        invalid_args: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="TOOL_VALIDATION_ERROR",
            details={
                "tool": tool_name,
                "invalid_arguments": invalid_args,
                **(details or {})
            },
            recoverable=False,
            http_status=400
        )


# ============================================================================
# AGENT EXCEPTIONS
# ============================================================================

class AgentError(MapItError):
    """Agent processing error."""

    def __init__(
        self,
        message: str,
        error_code: str = "AGENT_ERROR",
        iteration: int = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            details={"iteration": iteration, **(details or {})},
            recoverable=True,
            http_status=500
        )


class AgentMaxIterationsError(AgentError):
    """Agent reached maximum iterations without sufficient results."""

    def __init__(self, max_iterations: int, last_score: float = None):
        super().__init__(
            message=f"Agent reached maximum iterations ({max_iterations}) without finding sufficient results",
            error_code="AGENT_MAX_ITERATIONS",
            iteration=max_iterations,
            details={"max_iterations": max_iterations, "last_score": last_score}
        )


class AgentPlanningError(AgentError):
    """Agent failed to create a valid plan."""

    def __init__(self, message: str = "Agent failed to create a query plan", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AGENT_PLANNING_ERROR",
            details=details
        )


# ============================================================================
# CIRCUIT BREAKER EXCEPTIONS
# ============================================================================

class CircuitBreakerOpenError(MapItError):
    """Circuit breaker is open - service calls are blocked."""

    def __init__(
        self,
        circuit_name: str,
        recovery_time: int = None,
        message: str = None
    ):
        super().__init__(
            message=message or f"Service '{circuit_name}' is temporarily unavailable (circuit breaker open)",
            error_code="CIRCUIT_BREAKER_OPEN",
            details={
                "circuit": circuit_name,
                "recovery_time_seconds": recovery_time
            },
            recoverable=True,
            http_status=503
        )


# ============================================================================
# AUTHENTICATION/AUTHORIZATION EXCEPTIONS
# ============================================================================

class AuthenticationError(MapItError):
    """Authentication failed."""

    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_REQUIRED",
            details=details,
            recoverable=False,
            http_status=401
        )


class InvalidTokenError(AuthenticationError):
    """Token is invalid or expired."""

    def __init__(self, reason: str = None):
        super().__init__(
            message=f"Invalid or expired token: {reason}" if reason else "Invalid or expired token",
            details={"reason": reason}
        )


class AuthorizationError(MapItError):
    """Authorization failed - insufficient permissions."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_roles: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_FAILED",
            details={
                "required_roles": required_roles,
                **(details or {})
            },
            recoverable=False,
            http_status=403
        )


# ============================================================================
# EMBEDDING EXCEPTIONS
# ============================================================================

class EmbeddingError(MapItError):
    """Error generating or retrieving embeddings."""

    def __init__(
        self,
        message: str,
        content_type: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="EMBEDDING_ERROR",
            details={"content_type": content_type, **(details or {})},
            recoverable=True,
            http_status=500
        )


class EmbeddingGenerationError(EmbeddingError):
    """Failed to generate embeddings."""

    def __init__(self, message: str = "Failed to generate embeddings", model: str = None):
        super().__init__(
            message=message,
            content_type="generation",
            details={"model": model}
        )


# ============================================================================
# CONFIGURATION EXCEPTIONS
# ============================================================================

class ConfigurationError(MapItError):
    """Configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        config_key: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details={"config_key": config_key, **(details or {})},
            recoverable=False,
            http_status=500
        )


class MissingConfigurationError(ConfigurationError):
    """Required configuration is missing."""

    def __init__(self, config_key: str):
        super().__init__(
            message=f"Missing required configuration: {config_key}",
            config_key=config_key
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_user_suggestion(error_code: str) -> str:
    """
    Get a user-friendly suggestion for handling an error.

    Args:
        error_code: The error code from the exception

    Returns:
        A helpful suggestion string for the user
    """
    suggestions = {
        # Service availability
        "NEO4J_UNAVAILABLE": "Graph database is temporarily unavailable. Statistical queries may be limited. Try again in a few minutes.",
        "POSTGRES_UNAVAILABLE": "Database is temporarily unavailable. Please try again in a few minutes.",
        "REDIS_UNAVAILABLE": "Cache service is temporarily unavailable. Responses may be slower than usual.",
        "EMBEDDING_UNAVAILABLE": "Semantic search is temporarily unavailable. Falling back to keyword search.",
        "AI_PROVIDER_UNAVAILABLE": "AI service is temporarily unavailable. Please try again in a few minutes.",
        "EXTERNAL_API_UNAVAILABLE": "External data source is temporarily unavailable. Some information may be outdated.",

        # Data not found
        "CALL_NOT_FOUND": "This call ID was not found. Check the ID format or search for similar calls.",
        "PROJECT_NOT_FOUND": "This project was not found. Try searching with different keywords.",
        "CONVERSATION_NOT_FOUND": "This conversation was not found. It may have expired or been deleted.",
        "PROPOSAL_SESSION_NOT_FOUND": "This proposal session was not found. It may have been deleted.",
        "DOCUMENT_NOT_FOUND": "This document was not found. Check the document ID.",

        # Validation
        "VALIDATION_ERROR": "Please check your input and try again.",

        # Rate limiting
        "RATE_LIMITED": "Too many requests. Please wait before trying again.",

        # Timeout
        "TIMEOUT": "The operation took too long. Try a simpler query or try again later.",

        # Tool errors
        "TOOL_EXECUTION_ERROR": "A tool failed to execute. The system will try alternative approaches.",
        "TOOL_NOT_FOUND": "The requested tool is not available. Please check the tool name.",

        # Agent errors
        "AGENT_ERROR": "The AI agent encountered an issue. Please rephrase your query.",
        "AGENT_MAX_ITERATIONS": "Could not find satisfactory results. Try rephrasing your question.",

        # Circuit breaker
        "CIRCUIT_BREAKER_OPEN": "This service is temporarily unavailable. Please try again later.",

        # Auth
        "AUTHENTICATION_REQUIRED": "Please log in to continue.",
        "AUTHORIZATION_FAILED": "You don't have permission to perform this action.",

        # Default
        "MAPIT_ERROR": "An unexpected error occurred. Please try again."
    }

    return suggestions.get(error_code, suggestions["MAPIT_ERROR"])


def get_http_status(error_code: str) -> int:
    """
    Get the HTTP status code for an error code.

    Args:
        error_code: The error code from the exception

    Returns:
        HTTP status code
    """
    status_mapping = {
        # 4xx Client Errors
        "NOT_FOUND": 404,
        "CALL_NOT_FOUND": 404,
        "PROJECT_NOT_FOUND": 404,
        "CONVERSATION_NOT_FOUND": 404,
        "PROPOSAL_SESSION_NOT_FOUND": 404,
        "DOCUMENT_NOT_FOUND": 404,
        "VALIDATION_ERROR": 422,
        "AUTHENTICATION_REQUIRED": 401,
        "AUTHORIZATION_FAILED": 403,
        "RATE_LIMITED": 429,
        "TOOL_NOT_FOUND": 400,
        "TOOL_VALIDATION_ERROR": 400,

        # 5xx Server Errors
        "SERVICE_UNAVAILABLE": 503,
        "NEO4J_UNAVAILABLE": 503,
        "POSTGRES_UNAVAILABLE": 503,
        "REDIS_UNAVAILABLE": 503,
        "EMBEDDING_UNAVAILABLE": 503,
        "AI_PROVIDER_UNAVAILABLE": 503,
        "EXTERNAL_API_UNAVAILABLE": 503,
        "CIRCUIT_BREAKER_OPEN": 503,
        "TIMEOUT": 504,
        "TOOL_EXECUTION_ERROR": 500,
        "AGENT_ERROR": 500,
        "MAPIT_ERROR": 500,
    }

    return status_mapping.get(error_code, 500)
