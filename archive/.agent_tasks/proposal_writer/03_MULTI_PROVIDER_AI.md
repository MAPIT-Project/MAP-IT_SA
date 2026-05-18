# Task 03: Multi-Provider AI Support

> **Phase:** 0 - Foundation Fixes
> **Priority:** P0 (Production Blocker)
> **Estimated Effort:** 3-4 hours
> **Status:** Not Started
> **Depends On:** Task 02

---

## Problem Statement

The proposal writing services only use Gemini with no fallback. If Gemini is:
- Rate limited
- Temporarily unavailable
- Returns errors

The entire proposal writing feature fails completely.

### Current Code Pattern
```python
# Every service does this:
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
self.model = genai.GenerativeModel('gemini-flash-lite-latest')

# No fallback, no retry, no alternatives
response = self.model.generate_content(prompt)
```

---

## Solution: Provider Abstraction Layer

Create a unified AI service that:
1. Supports multiple providers (Gemini, OpenAI, Anthropic)
2. Automatically falls back on failures
3. Handles rate limiting with exponential backoff
4. Provides consistent interface across providers
5. Supports both text and structured JSON outputs

---

## Implementation

### Step 1: Create Provider Interface

**File:** `app/services/proposal_writing/ai_providers/base.py`

```python
"""
Base AI Provider Interface
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum


class ProviderStatus(Enum):
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
    usage: Dict[str, int]  # tokens used
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
        schema: Dict[str, Any],
        temperature: float = 0.3
    ) -> Dict[str, Any]:
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
```

---

### Step 2: Implement Gemini Provider

**File:** `app/services/proposal_writing/ai_providers/gemini_provider.py`

```python
"""
Google Gemini Provider
"""

import logging
import time
import json
from typing import Dict, Any, AsyncGenerator
import google.generativeai as genai

from .base import BaseAIProvider, ProviderConfig, ProviderResponse, ProviderStatus

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
            except:
                pass
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
```

---

### Step 3: Implement OpenAI Provider

**File:** `app/services/proposal_writing/ai_providers/openai_provider.py`

```python
"""
OpenAI Provider
"""

import logging
import time
import json
from typing import Dict, Any, AsyncGenerator
from openai import AsyncOpenAI

from .base import BaseAIProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """OpenAI GPT provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(api_key=config.api_key)

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> ProviderResponse:
        """Generate text using OpenAI."""

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
        schema: Dict[str, Any],
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Generate structured JSON using OpenAI."""

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
```

---

### Step 4: Create Multi-Provider Service

**File:** `app/services/proposal_writing/ai_providers/multi_provider_service.py`

```python
"""
Multi-Provider AI Service

Automatically handles provider selection, fallback, and retry logic.
"""

import logging
import os
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator

from .base import BaseAIProvider, ProviderConfig, ProviderResponse, ProviderStatus
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

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
        primary_provider: str = "gemini",
        enable_fallback: bool = True
    ):
        self.enable_fallback = enable_fallback
        self.providers: List[BaseAIProvider] = []

        # Initialize providers based on available API keys
        self._initialize_providers(primary_provider)

    def _initialize_providers(self, primary_provider: str):
        """Initialize available providers."""

        provider_configs = {
            "gemini": {
                "class": GeminiProvider,
                "api_key_env": "GEMINI_API_KEY",
                "default_model": "gemini-2.0-flash-lite"
            },
            "openai": {
                "class": OpenAIProvider,
                "api_key_env": "OPENAI_API_KEY",
                "default_model": "gpt-4-turbo"
            }
        }

        # Initialize primary provider first
        if primary_provider in provider_configs:
            config = provider_configs[primary_provider]
            api_key = os.getenv(config["api_key_env"])

            if api_key:
                provider = config["class"](ProviderConfig(
                    name=primary_provider,
                    api_key=api_key,
                    model=os.getenv(f"{primary_provider.upper()}_MODEL", config["default_model"])
                ))
                self.providers.append(provider)
                logger.info(f"Initialized primary provider: {primary_provider}")

        # Initialize fallback providers
        if self.enable_fallback:
            for name, config in provider_configs.items():
                if name != primary_provider:
                    api_key = os.getenv(config["api_key_env"])
                    if api_key:
                        provider = config["class"](ProviderConfig(
                            name=name,
                            api_key=api_key,
                            model=os.getenv(f"{name.upper()}_MODEL", config["default_model"])
                        ))
                        self.providers.append(provider)
                        logger.info(f"Initialized fallback provider: {name}")

        if not self.providers:
            raise RuntimeError("No AI providers available. Check API keys.")

    def _get_available_providers(self) -> List[BaseAIProvider]:
        """Get list of available providers."""
        return [p for p in self.providers if p.is_available()]

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        max_retries: int = 3
    ) -> ProviderResponse:
        """
        Generate text with automatic fallback.

        Tries primary provider first, then falls back to alternatives.
        """

        available = self._get_available_providers()

        if not available:
            # Reset providers and try again
            for p in self.providers:
                p.status = ProviderStatus.AVAILABLE
            available = self.providers

        last_error = None

        for provider in available:
            for attempt in range(max_retries):
                try:
                    response = await provider.generate_text(
                        prompt=prompt,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    logger.info(f"Generated text using {provider.name} ({response.latency_ms:.0f}ms)")
                    return response

                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"{provider.name} failed (attempt {attempt + 1}/{max_retries}): {e}"
                    )

                    if attempt < max_retries - 1:
                        # Exponential backoff
                        await asyncio.sleep(2 ** attempt)

            # Provider exhausted, try next
            logger.warning(f"Provider {provider.name} exhausted, trying fallback...")

        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.3,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate structured JSON with automatic fallback.
        """

        available = self._get_available_providers()

        if not available:
            for p in self.providers:
                p.status = ProviderStatus.AVAILABLE
            available = self.providers

        last_error = None

        for provider in available:
            for attempt in range(max_retries):
                try:
                    result = await provider.generate_structured(
                        prompt=prompt,
                        schema=schema,
                        temperature=temperature
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
                        await asyncio.sleep(2 ** attempt)

        raise RuntimeError(f"All providers failed for structured generation. Last error: {last_error}")

    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        Stream text generation with fallback.
        """

        available = self._get_available_providers()

        if not available:
            for p in self.providers:
                p.status = ProviderStatus.AVAILABLE
            available = self.providers

        for provider in available:
            try:
                async for chunk in provider.generate_stream(
                    prompt=prompt,
                    temperature=temperature
                ):
                    yield chunk
                return

            except Exception as e:
                logger.warning(f"{provider.name} stream failed: {e}")
                continue

        raise RuntimeError("All providers failed for streaming")

    def get_provider_status(self) -> Dict[str, str]:
        """Get status of all providers."""
        return {p.name: p.status.value for p in self.providers}
```

---

### Step 5: Update ProposalAIService

**File:** `app/services/proposal_writing/proposal_ai_service.py` (update)

```python
"""
Proposal AI Service - Updated to use Multi-Provider
"""

import logging
from typing import Dict, Any, Optional, AsyncGenerator

from app.services.proposal_writing.ai_providers.multi_provider_service import MultiProviderAIService

logger = logging.getLogger(__name__)


class ProposalAIService:
    """
    AI service for proposal writing with multi-provider support.
    """

    def __init__(
        self,
        primary_provider: str = "gemini",
        enable_fallback: bool = True
    ):
        self.multi_provider = MultiProviderAIService(
            primary_provider=primary_provider,
            enable_fallback=enable_fallback
        )

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.3,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response.
        """
        return await self.multi_provider.generate_structured(
            prompt=prompt,
            schema=response_schema,
            temperature=temperature,
            max_retries=max_retries
        )

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        """
        Generate free-form text.
        """
        response = await self.multi_provider.generate_text(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.text

    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        Stream text generation.
        """
        async for chunk in self.multi_provider.generate_stream(
            prompt=prompt,
            temperature=temperature
        ):
            yield chunk

    def get_status(self) -> Dict[str, str]:
        """Get provider status."""
        return self.multi_provider.get_provider_status()
```

---

### Step 6: Create Provider Package

**File:** `app/services/proposal_writing/ai_providers/__init__.py`

```python
"""
AI Providers Package

Multi-provider support for proposal writing AI services.
"""

from .base import BaseAIProvider, ProviderConfig, ProviderResponse, ProviderStatus
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider
from .multi_provider_service import MultiProviderAIService

__all__ = [
    "BaseAIProvider",
    "ProviderConfig",
    "ProviderResponse",
    "ProviderStatus",
    "GeminiProvider",
    "OpenAIProvider",
    "MultiProviderAIService"
]
```

---

## Testing Plan

### Unit Tests

```python
# tests/test_multi_provider.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.proposal_writing.ai_providers.multi_provider_service import MultiProviderAIService
from app.services.proposal_writing.ai_providers.base import ProviderStatus

@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-key")

@pytest.mark.asyncio
async def test_primary_provider_success(mock_env):
    """Test that primary provider is used when available."""

    with patch('app.services.proposal_writing.ai_providers.gemini_provider.genai'):
        service = MultiProviderAIService(primary_provider="gemini")

        # Mock the generate_text method
        service.providers[0].generate_text = AsyncMock(return_value=MagicMock(
            text="Generated text",
            provider="gemini",
            model="gemini-2.0-flash-lite",
            usage={"total_tokens": 100},
            latency_ms=500
        ))

        response = await service.generate_text("Test prompt")

        assert response.provider == "gemini"
        service.providers[0].generate_text.assert_called_once()

@pytest.mark.asyncio
async def test_fallback_on_primary_failure(mock_env):
    """Test that fallback provider is used when primary fails."""

    with patch('app.services.proposal_writing.ai_providers.gemini_provider.genai'):
        with patch('app.services.proposal_writing.ai_providers.openai_provider.AsyncOpenAI'):
            service = MultiProviderAIService(primary_provider="gemini")

            # Make primary fail
            service.providers[0].generate_text = AsyncMock(side_effect=Exception("Gemini failed"))
            service.providers[0].status = ProviderStatus.ERROR

            # Make fallback succeed
            if len(service.providers) > 1:
                service.providers[1].generate_text = AsyncMock(return_value=MagicMock(
                    text="Fallback text",
                    provider="openai",
                    model="gpt-4-turbo",
                    usage={"total_tokens": 100},
                    latency_ms=600
                ))

                response = await service.generate_text("Test prompt")

                assert response.provider == "openai"

@pytest.mark.asyncio
async def test_retry_with_backoff(mock_env):
    """Test that retries happen with exponential backoff."""

    with patch('app.services.proposal_writing.ai_providers.gemini_provider.genai'):
        service = MultiProviderAIService(primary_provider="gemini", enable_fallback=False)

        call_count = 0

        async def failing_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return MagicMock(
                text="Success",
                provider="gemini",
                model="gemini-2.0-flash-lite",
                usage={"total_tokens": 100},
                latency_ms=500
            )

        service.providers[0].generate_text = failing_then_success

        response = await service.generate_text("Test prompt", max_retries=3)

        assert call_count == 3
        assert response.text == "Success"
```

---

## Configuration

### Environment Variables

```bash
# Primary provider (default: gemini)
AI_PRIMARY_PROVIDER=gemini

# Enable fallback to other providers (default: true)
AI_ENABLE_FALLBACK=true

# Gemini configuration
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.0-flash-lite

# OpenAI configuration (optional fallback)
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4-turbo

# Anthropic configuration (optional fallback)
ANTHROPIC_API_KEY=your_anthropic_key
ANTHROPIC_MODEL=claude-3-sonnet
```

---

## Acceptance Criteria

- [ ] Multi-provider service initializes with available API keys
- [ ] Primary provider is used when available
- [ ] Automatic fallback to secondary providers on failure
- [ ] Exponential backoff on retries
- [ ] Provider health tracking works correctly
- [ ] All existing proposal writing features work with new service
- [ ] Status endpoint shows provider health

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `app/services/proposal_writing/ai_providers/__init__.py` | CREATE |
| `app/services/proposal_writing/ai_providers/base.py` | CREATE |
| `app/services/proposal_writing/ai_providers/gemini_provider.py` | CREATE |
| `app/services/proposal_writing/ai_providers/openai_provider.py` | CREATE |
| `app/services/proposal_writing/ai_providers/multi_provider_service.py` | CREATE |
| `app/services/proposal_writing/proposal_ai_service.py` | MODIFY |
| `tests/test_multi_provider.py` | CREATE |

---

## Future Enhancements

1. **Add Anthropic Provider** - Claude models as additional fallback
2. **Cost Tracking** - Track token usage and costs per provider
3. **Smart Routing** - Route different tasks to best-suited providers
4. **Caching** - Cache responses for identical prompts
5. **Rate Limit Monitoring** - Proactive rate limit management

---

## Next Task

After completing this task, proceed to:
→ **Task 04: Error Handling & Async Fixes**
