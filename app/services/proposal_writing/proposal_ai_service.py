"""
Proposal AI Service

Unified AI service for proposal writing with multi-provider support and structured outputs.
"""

import json
import logging
import os
from collections.abc import AsyncGenerator, Callable
from typing import Any

logger = logging.getLogger(__name__)


class ProposalAIService:
    """
    AI service for proposal writing with multi-provider support.

    Features:
    - Guaranteed JSON responses via structured output modes
    - Multi-provider support with automatic fallback
    - Automatic retry on failures
    - Consistent temperature settings for different tasks
    """

    def __init__(self, primary_provider: str = "gemini", enable_fallback: bool = True):
        self._primary_provider = primary_provider
        self._enable_fallback = enable_fallback
        self._multi_provider = None

        # Lazy initialization to avoid import errors if providers aren't available
        self._initialized = False

    def _ensure_initialized(self):
        """Lazily initialize the multi-provider service."""
        if self._initialized:
            return

        try:
            from .ai_providers.multi_provider_service import MultiProviderAIService

            self._multi_provider = MultiProviderAIService(
                primary_provider=self._primary_provider, enable_fallback=self._enable_fallback
            )
            self._initialized = True
            provider = self._multi_provider.get_primary_provider()
            logger.info(f"ProposalAIService initialized with provider: {provider}")
        except Exception as e:
            logger.warning(f"Failed to initialize multi-provider service: {e}")
            # Fall back to direct Gemini usage
            self._init_fallback_gemini()
            self._initialized = True

    def _init_fallback_gemini(self):
        """Initialize fallback direct Gemini connection."""
        import google.generativeai as genai

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self._fallback_model = genai.GenerativeModel("gemini-2.0-flash-lite")
        self._multi_provider = None
        logger.info("Using fallback direct Gemini connection")

    async def generate_structured(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.3,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """
        Generate a structured JSON response from the LLM.

        Args:
            prompt: The prompt to send
            response_schema: JSON schema for the expected response
            temperature: LLM temperature (lower = more deterministic)
            max_retries: Number of retries on failure

        Returns:
            Parsed JSON response matching the schema
        """
        self._ensure_initialized()

        if self._multi_provider:
            return await self._multi_provider.generate_structured(
                prompt=prompt,
                schema=response_schema,
                temperature=temperature,
                max_retries=max_retries,
            )
        else:
            # Fallback to direct Gemini
            return await self._fallback_structured(
                prompt, response_schema, temperature, max_retries
            )

    async def _fallback_structured(
        self, prompt: str, response_schema: dict[str, Any], temperature: float, max_retries: int
    ) -> dict[str, Any]:
        """Fallback structured generation using direct Gemini."""
        current_prompt = prompt
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                response = self._fallback_model.generate_content(
                    current_prompt,
                    generation_config={
                        "response_mime_type": "application/json",
                        "response_schema": response_schema,
                        "temperature": temperature,
                    },
                )

                result = json.loads(response.text)
                logger.debug(f"Fallback structured generation successful on attempt {attempt + 1}")
                return result

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"JSON parse error (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    json_note = "\n\nIMPORTANT: Return ONLY valid JSON."
                    current_prompt = prompt + json_note

            except Exception as e:
                last_error = e
                logger.error(f"Generation error (attempt {attempt + 1}): {e}")
                if attempt >= max_retries:
                    break

        raise RuntimeError(f"Failed to generate structured response: {last_error}")

    async def generate_text(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000
    ) -> str:
        """
        Generate free-form text response.
        Use for draft generation where structure isn't needed.

        Args:
            prompt: The prompt to send
            temperature: LLM temperature (higher = more creative)
            max_tokens: Maximum output tokens

        Returns:
            Generated text string
        """
        self._ensure_initialized()

        if self._multi_provider:
            response = await self._multi_provider.generate_text(
                prompt=prompt, temperature=temperature, max_tokens=max_tokens
            )
            return response.text
        else:
            # Fallback to direct Gemini
            response = self._fallback_model.generate_content(
                prompt,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            )
            return response.text

    async def generate_stream(
        self, prompt: str, temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        Stream text generation.

        Args:
            prompt: The prompt to send
            temperature: LLM temperature

        Yields:
            Text chunks as they are generated
        """
        self._ensure_initialized()

        if self._multi_provider:
            async for chunk in self._multi_provider.generate_stream(
                prompt=prompt, temperature=temperature
            ):
                yield chunk
        else:
            # Fallback to direct Gemini
            response = self._fallback_model.generate_content(
                prompt, generation_config={"temperature": temperature}, stream=True
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text

    async def generate_with_fallback(
        self,
        prompt: str,
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.3,
        fallback_fn: Callable | None = None,
    ) -> dict[str, Any]:
        """
        Generate with automatic fallback to a provided function on failure.

        Args:
            prompt: The prompt to send
            response_schema: Optional JSON schema for structured output
            temperature: LLM temperature
            fallback_fn: Function to call if AI generation fails

        Returns:
            Either AI response or fallback result
        """
        try:
            if response_schema:
                return await self.generate_structured(
                    prompt=prompt, response_schema=response_schema, temperature=temperature
                )
            else:
                text = await self.generate_text(prompt=prompt, temperature=temperature)
                return {"text": text}

        except Exception as e:
            logger.warning(f"AI generation failed, using fallback: {e}")
            if fallback_fn:
                return fallback_fn()
            raise

    def get_status(self) -> dict[str, str]:
        """Get provider status."""
        self._ensure_initialized()
        if self._multi_provider:
            return self._multi_provider.get_provider_status()
        return {"fallback_gemini": "active"}
