"""
Google Gemini Provider

AI provider implementation for Google Gemini models.
"""

import logging
import time
import json
from typing import Dict, Any, AsyncGenerator

import google.generativeai as genai

from .base import BaseAIProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        genai.configure(api_key=config.api_key)
        self.model = genai.GenerativeModel(config.model)

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> ProviderResponse:
        """Generate text using Gemini."""

        start_time = time.time()

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens
                }
            )

            self.mark_success()

            return ProviderResponse(
                text=response.text,
                provider="gemini",
                model=self.config.model,
                usage={"total_tokens": len(prompt.split()) + len(response.text.split())},
                latency_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            self.mark_failure()
            logger.error(f"Gemini generation failed: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Generate structured JSON using Gemini's JSON mode."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": schema,
                    "temperature": temperature
                }
            )

            self.mark_success()
            return json.loads(response.text)

        except json.JSONDecodeError as e:
            logger.warning(f"Gemini returned invalid JSON: {e}")
            # Try to extract JSON from response
            try:
                text = response.text
                # Find JSON in response
                start = text.find('{')
                end = text.rfind('}') + 1
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

    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream text generation."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"temperature": temperature},
                stream=True
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

            self.mark_success()

        except Exception as e:
            self.mark_failure()
            logger.error(f"Gemini stream failed: {e}")
            raise
