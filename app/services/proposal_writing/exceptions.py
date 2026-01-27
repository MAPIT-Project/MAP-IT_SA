"""
Custom Exceptions for Proposal Writing

Structured exceptions with context for better error handling.
"""

from typing import Any


class ProposalWritingError(Exception):
    """Base exception for proposal writing errors."""

    def __init__(
        self,
        message: str,
        code: str = "PROPOSAL_ERROR",
        details: dict[str, Any] | None = None,
        recoverable: bool = True,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.recoverable = recoverable
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
        }


class AIGenerationError(ProposalWritingError):
    """Error during AI content generation."""

    def __init__(
        self,
        message: str,
        provider: str = None,
        prompt_length: int = None,
        details: dict[str, Any] = None,
    ):
        super().__init__(
            message=message,
            code="AI_GENERATION_ERROR",
            details={"provider": provider, "prompt_length": prompt_length, **(details or {})},
            recoverable=True,
        )


class CallAnalysisError(ProposalWritingError):
    """Error analyzing call documents."""

    def __init__(self, message: str, call_id: str = None, details: dict[str, Any] = None):
        super().__init__(
            message=message,
            code="CALL_ANALYSIS_ERROR",
            details={"call_id": call_id, **(details or {})},
            recoverable=True,
        )


class DatabaseError(ProposalWritingError):
    """Database operation error."""

    def __init__(self, message: str, operation: str = None, details: dict[str, Any] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details={"operation": operation, **(details or {})},
            recoverable=True,
        )


class ValidationError(ProposalWritingError):
    """Input validation error."""

    def __init__(self, message: str, field: str = None, details: dict[str, Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, **(details or {})},
            recoverable=False,
        )


class RateLimitError(ProposalWritingError):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str,
        provider: str = None,
        retry_after: int = None,
        details: dict[str, Any] = None,
    ):
        super().__init__(
            message=message,
            code="RATE_LIMIT_ERROR",
            details={"provider": provider, "retry_after": retry_after, **(details or {})},
            recoverable=True,
        )


class ProposalTimeoutError(ProposalWritingError):
    """Operation timed out."""

    def __init__(
        self,
        message: str,
        operation: str = None,
        timeout_seconds: int = None,
        details: dict[str, Any] = None,
    ):
        super().__init__(
            message=message,
            code="TIMEOUT_ERROR",
            details={"operation": operation, "timeout_seconds": timeout_seconds, **(details or {})},
            recoverable=True,
        )


class ProviderUnavailableError(ProposalWritingError):
    """AI provider is unavailable."""

    def __init__(self, message: str, provider: str = None, details: dict[str, Any] = None):
        super().__init__(
            message=message,
            code="PROVIDER_UNAVAILABLE",
            details={"provider": provider, **(details or {})},
            recoverable=True,
        )


class TemplateError(ProposalWritingError):
    """Error with proposal template."""

    def __init__(self, message: str, template_id: str = None, details: dict[str, Any] = None):
        super().__init__(
            message=message,
            code="TEMPLATE_ERROR",
            details={"template_id": template_id, **(details or {})},
            recoverable=False,
        )
