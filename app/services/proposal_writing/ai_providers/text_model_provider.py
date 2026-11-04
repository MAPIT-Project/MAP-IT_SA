"""Bridge the shared text model factory into the proposal provider interface."""

import json
import time
from collections.abc import AsyncGenerator
from typing import Any

from app.services.ai.factory import create_text_model

from .base import BaseAIProvider, ProviderConfig, ProviderResponse


class TextModelProvider(BaseAIProvider):
    """Codex and OpenRouter use the same routing and adapters as chat and services."""

    def __init__(self, provider: str, step: str = "proposal_generation"):
        self.model = create_text_model(step, provider=provider)
        super().__init__(ProviderConfig(name=provider, api_key="", model=self.model.model_name))

    async def generate_text(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000
    ) -> ProviderResponse:
        start = time.monotonic()
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            )
            self.mark_success()
            return ProviderResponse(
                text=response.text,
                provider=self.name,
                model=response.model_name,
                usage=response.usage,
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except Exception:
            self.mark_failure()
            raise

    async def generate_structured(
        self, prompt: str, schema: dict[str, Any], temperature: float = 0.3
    ) -> dict[str, Any]:
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                    "response_schema": schema,
                },
            )
            result = json.loads(response.text)
            self.mark_success()
            return result
        except Exception:
            self.mark_failure()
            raise

    async def generate_stream(
        self, prompt: str, temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        try:
            chunks = await self.model.generate_content_async(
                prompt, generation_config={"temperature": temperature}, stream=True
            )
            # Codex emits a completed-message chunk. Callers keep their existing event format.
            async for chunk in chunks:
                if chunk.text:
                    yield chunk.text
            self.mark_success()
        except Exception:
            self.mark_failure()
            raise
