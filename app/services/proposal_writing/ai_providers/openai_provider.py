"""
OpenAI Provider

AI provider implementation for OpenAI GPT models.
"""

import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

from .base import BaseAIProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """OpenAI GPT provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # Lazy import to avoid requiring openai if not used
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=config.api_key)
            self._available = True
        except ImportError:
            logger.warning("OpenAI package not installed. OpenAI provider unavailable.")
            self._available = False
            self.client = None

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> ProviderResponse:
        """Generate text using OpenAI."""

        if not self._available or not self.client:
            raise RuntimeError("OpenAI client not available")

        start_time = time.time()

        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )

            self.mark_success()

            return ProviderResponse(
                text=response.choices[0].message.content,
                provider="openai",
                model=self.config.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                latency_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            self.mark_failure()
            logger.error(f"OpenAI generation failed: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        temperature: float = 0.3
    ) -> dict[str, Any]:
        """Generate structured JSON using OpenAI."""

        if not self._available or not self.client:
            raise RuntimeError("OpenAI client not available")

        try:
            # OpenAI supports JSON mode
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that outputs valid JSON."
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nRespond with JSON matching this schema: {json.dumps(schema)}"
                    }
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )

            self.mark_success()
            return json.loads(response.choices[0].message.content)

        except Exception as e:
            self.mark_failure()
            logger.error(f"OpenAI structured generation failed: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream text generation."""

        if not self._available or not self.client:
            raise RuntimeError("OpenAI client not available")

        try:
            stream = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            self.mark_success()

        except Exception as e:
            self.mark_failure()
            logger.error(f"OpenAI stream failed: {e}")
            raise

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._available and super().is_available()
