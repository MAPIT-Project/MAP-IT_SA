"""
Multi-Provider AI Service

Automatically handles provider selection, fallback, and retry logic.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from app.core.config import settings
from app.services.ai.factory import resolve_provider

from .base import BaseAIProvider, ProviderConfig, ProviderResponse
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider
from .text_model_provider import TextModelProvider

logger = logging.getLogger(__name__)


class MultiProviderAIService:
    """
    Multi-provider AI service with automatic fallback.

    Features:
    - Primary provider with fallbacks
    - Automatic retry with exponential backoff
    - Provider health tracking
    - Consistent interface across providers
    """

    def __init__(
        self,
        primary_provider: str | None = None,
        enable_fallback: bool = True,
        step: str = "proposal_generation",
    ):
        self.step = step
        primary_provider = resolve_provider(step, primary_provider)
        self.enable_fallback = enable_fallback and primary_provider != "codex"
        self.providers: list[BaseAIProvider] = []

        # Initialize providers based on available API keys
        self._initialize_providers(primary_provider)

    def _initialize_providers(self, primary_provider: str):
        """Initialize available providers."""

        # Codex is an explicit local choice. Initialization and inference failures must
        # never send its prompts to an API provider.
        if primary_provider == "codex":
            self.providers.append(TextModelProvider("codex", step=self.step))
            return

        if primary_provider == "openrouter":
            self.providers.append(TextModelProvider("openrouter", step=self.step))

        provider_configs = {
            "gemini": {
                "class": GeminiProvider,
                "api_key": settings.gemini_api_key,
                "model": settings.gemini_model,
            },
            "openai": {
                "class": OpenAIProvider,
                "api_key": settings.openai_api_key,
                "model": settings.openai_model,
            },
        }

        # Initialize primary provider first
        if primary_provider in provider_configs:
            config = provider_configs[primary_provider]
            api_key = config["api_key"]

            if api_key:
                try:
                    provider = config["class"](
                        ProviderConfig(
                            name=primary_provider,
                            api_key=api_key,
                            model=config["model"],
                        )
                    )
                    self.providers.append(provider)
                    logger.info(f"Initialized primary provider: {primary_provider}")
                except Exception as e:
                    logger.warning(f"Failed to initialize primary provider {primary_provider}: {e}")

        # Initialize fallback providers
        if self.enable_fallback:
            for name, config in provider_configs.items():
                if name != primary_provider:
                    api_key = config["api_key"]
                    if api_key:
                        try:
                            provider = config["class"](
                                ProviderConfig(
                                    name=name,
                                    api_key=api_key,
                                    model=config["model"],
                                )
                            )
                            self.providers.append(provider)
                            logger.info(f"Initialized fallback provider: {name}")
                        except Exception as e:
                            logger.warning(f"Failed to initialize fallback provider {name}: {e}")

        if not self.providers:
            raise RuntimeError("No AI providers available. Check API keys.")

    def _get_available_providers(self) -> list[BaseAIProvider]:
        """Get list of available providers."""
        return [p for p in self.providers if p.is_available()]

    def _reset_providers(self):
        """Reset all provider statuses."""
        for p in self.providers:
            p.reset()

    async def generate_text(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000, max_retries: int = 3
    ) -> ProviderResponse:
        """
        Generate text with automatic fallback.

        Tries primary provider first, then falls back to alternatives.
        """

        available = self._get_available_providers()

        if not available:
            # Reset providers and try again
            self._reset_providers()
            available = self.providers

        last_error = None

        for provider in available:
            for attempt in range(max_retries):
                try:
                    response = await provider.generate_text(
                        prompt=prompt, temperature=temperature, max_tokens=max_tokens
                    )
                    logger.info(
                        f"Generated text using {provider.name} ({response.latency_ms:.0f}ms)"
                    )
                    return response

                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"{provider.name} failed (attempt {attempt + 1}/{max_retries}): {e}"
                    )

                    if attempt < max_retries - 1:
                        # Exponential backoff
                        await asyncio.sleep(2**attempt)

            # Provider exhausted, try next
            logger.warning(f"Provider {provider.name} exhausted, trying fallback...")

        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    async def generate_structured(
        self, prompt: str, schema: dict[str, Any], temperature: float = 0.3, max_retries: int = 3
    ) -> dict[str, Any]:
        """
        Generate structured JSON with automatic fallback.
        """

        available = self._get_available_providers()

        if not available:
            self._reset_providers()
            available = self.providers

        last_error = None

        for provider in available:
            for attempt in range(max_retries):
                try:
                    result = await provider.generate_structured(
                        prompt=prompt, schema=schema, temperature=temperature
                    )
                    logger.info(f"Generated structured output using {provider.name}")
                    return result

                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"{provider.name} structured generation failed "
                        f"(attempt {attempt + 1}/{max_retries}): {e}"
                    )

                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)

        raise RuntimeError(
            f"All providers failed for structured generation. Last error: {last_error}"
        )

    async def generate_stream(
        self, prompt: str, temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        Stream text generation with fallback.
        """

        available = self._get_available_providers()

        if not available:
            self._reset_providers()
            available = self.providers

        for provider in available:
            try:
                async for chunk in provider.generate_stream(prompt=prompt, temperature=temperature):
                    yield chunk
                return

            except Exception as e:
                logger.warning(f"{provider.name} stream failed: {e}")
                continue

        raise RuntimeError("All providers failed for streaming")

    def get_provider_status(self) -> dict[str, str]:
        """Get status of all providers."""
        return {p.name: p.status.value for p in self.providers}

    def get_primary_provider(self) -> str:
        """Get name of primary provider."""
        return self.providers[0].name if self.providers else "none"
