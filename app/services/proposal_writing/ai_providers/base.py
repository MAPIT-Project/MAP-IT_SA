"""
Base AI Provider Interface

Abstract base class and common types for AI providers.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ProviderStatus(Enum):
    """Provider availability status."""
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class ProviderResponse:
    """Standardized response from any provider."""
    text: str
    provider: str
    model: str
    usage: dict[str, int]  # tokens used
    latency_ms: float


@dataclass
class ProviderConfig:
    """Configuration for a provider."""
    name: str
    api_key: str
    model: str
    max_retries: int = 3
    timeout_seconds: int = 60
    rate_limit_backoff: float = 2.0


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.status = ProviderStatus.AVAILABLE
        self._consecutive_failures = 0

    @property
    def name(self) -> str:
        return self.config.name

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> ProviderResponse:
        """Generate free-form text."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        temperature: float = 0.3
    ) -> dict[str, Any]:
        """Generate structured JSON output."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream text generation."""
        pass

    def mark_failure(self):
        """Mark a failure for this provider."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= 3:
            self.status = ProviderStatus.ERROR

    def mark_success(self):
        """Mark a success for this provider."""
        self._consecutive_failures = 0
        self.status = ProviderStatus.AVAILABLE

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.status == ProviderStatus.AVAILABLE

    def reset(self):
        """Reset provider status."""
        self._consecutive_failures = 0
        self.status = ProviderStatus.AVAILABLE
