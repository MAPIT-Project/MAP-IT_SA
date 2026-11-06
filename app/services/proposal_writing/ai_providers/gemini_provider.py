"""
Google Gemini Provider

AI provider implementation for Google Gemini models.
"""

import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

import google.generativeai as genai

from app.services.ai.budget import budgeted_inference, record_inference_response

from .base import BaseAIProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        genai.configure(api_key=config.api_key)
        self.model = genai.GenerativeModel(config.model)

    @budgeted_inference(step="proposal_generation")
    async def generate_text(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000
    ) -> ProviderResponse:
        """Generate text using Gemini."""

        start_time = time.time()

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            )

            reported_usage = record_inference_response(response)
            self.mark_success()

            return ProviderResponse(
                text=response.text,
                provider="gemini",
                model=self.config.model,
                usage=reported_usage or {},
                latency_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            self.mark_failure()
            logger.error(f"Gemini generation failed: {e}")
            raise

    @budgeted_inference(step="proposal_generation")
    async def generate_structured(
        self, prompt: str, schema: dict[str, Any], temperature: float = 0.3
    ) -> dict[str, Any]:
        """Generate structured JSON using Gemini's JSON mode."""

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": schema,
                    "temperature": temperature,
                },
            )

            record_inference_response(response)
            self.mark_success()
            return json.loads(response.text)

        except json.JSONDecodeError as e:
            logger.warning(f"Gemini returned invalid JSON: {e}")
            # Try to extract JSON from response
            try:
                text = response.text
                # Find JSON in response
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(text[start:end])
            except Exception:
                pass
            self.mark_failure()
            raise

        except Exception as e:
            self.mark_failure()
            logger.error(f"Gemini structured generation failed: {e}")
            raise

    @budgeted_inference(step="proposal_generation")
    async def generate_stream(
        self, prompt: str, temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream text generation."""

        try:
            response = await self.model.generate_content_async(
                prompt, generation_config={"temperature": temperature}, stream=True
            )

            async for chunk in response:
                record_inference_response(chunk)
                if chunk.text:
                    yield chunk.text

            record_inference_response(response)
            self.mark_success()

        except Exception as e:
            self.mark_failure()
            logger.error(f"Gemini stream failed: {e}")
            raise
