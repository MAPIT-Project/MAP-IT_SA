"""Request > named step > global text provider selection.

The facade resolves on every invocation so cached application services can serve
concurrent requests with different providers. It never selects a fallback.
"""

import asyncio
import inspect
import json
from contextlib import contextmanager
from contextvars import ContextVar

from app.core.ai_routing import PROVIDERS, TEXT_STEPS
from app.core.config import settings
from app.services.ai.budget import budgeted_inference
from app.services.ai.codex import CodexTextModel
from app.services.ai.structured import validate_json, validate_schema
from app.services.ai.types import TextResponse

_request_provider = ContextVar("mapit_request_ai_provider", default=None)


def resolve_provider(step, provider=None):
    if step not in TEXT_STEPS:
        raise ValueError(f"Unsupported AI step: {step}")
    selected = provider if provider is not None else _request_provider.get()
    if selected is None:
        selected = settings.ai_step_providers.get(step, settings.default_ai_provider)
    if selected not in PROVIDERS:
        raise ValueError(f"Unsupported AI provider: {selected}")
    if selected == "codex" and not settings.codex_enabled:
        raise ValueError("Codex requires local opt-in: set CODEX_ENABLED=true")
    return selected


@contextmanager
def provider_scope(provider):
    if provider is not None and provider not in PROVIDERS:
        raise ValueError(f"Unsupported AI provider: {provider}")
    if provider == "codex" and not settings.codex_enabled:
        raise ValueError("Codex requires local opt-in: set CODEX_ENABLED=true")
    token = _request_provider.set(provider)
    try:
        yield
    finally:
        _request_provider.reset(token)


async def generate_content_async(model, prompt, **kwargs):
    """Native async for adapters; retain compatibility with injected sync models."""
    if (
        isinstance(model, TextModel)
        and "generate_content" in vars(model)
        and "generate_content_async" not in vars(model)
    ):
        return await asyncio.to_thread(model.generate_content, prompt, **kwargs)
    method = getattr(model, "generate_content_async", None)
    if inspect.iscoroutinefunction(method):
        return await method(prompt, **kwargs)
    return await asyncio.to_thread(model.generate_content, prompt, **kwargs)


generate_content = generate_content_async


class APITextModel:
    """OpenAI and OpenRouter behind the same interface used by Gemini callers."""

    def __init__(self, provider, model, api_key=None):
        self.provider = provider
        self.model_name = model
        self.api_key = api_key or getattr(settings, f"{provider}_api_key")
        if not self.api_key:
            raise ValueError(f"{provider.upper()}_API_KEY is required for {provider} generation")

    def _arguments(self, prompt, config, stream):
        config = config or {}
        if not isinstance(config, dict):
            config = {
                key: getattr(config, key, None)
                for key in (
                    "temperature",
                    "max_output_tokens",
                    "response_schema",
                    "response_mime_type",
                )
            }
        schema = config.get("response_schema")
        if schema:
            validate_schema(schema)
            prompt += "\nReturn JSON matching this schema:\n" + json.dumps(schema)
        args = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
        }
        for source, target in (("temperature", "temperature"), ("max_output_tokens", "max_tokens")):
            if config.get(source) is not None:
                args[target] = config[source]
        if schema or config.get("response_mime_type") == "application/json":
            args["response_format"] = {"type": "json_object"}
        return args, config

    def _client_arguments(self):
        args = {"api_key": self.api_key}
        if self.provider == "openrouter":
            args["base_url"] = settings.openrouter_base_url
        return args

    def _response(self, response, config):
        answer = response.choices[0].message.content or ""
        if config.get("response_schema") or config.get("response_mime_type") == "application/json":
            validate_json(answer, config.get("response_schema"))
        usage = response.usage.model_dump() if response.usage else {}
        return TextResponse(answer, self.provider, response.model, usage)

    @budgeted_inference
    def generate_content(self, prompt, generation_config=None, stream=False, **kwargs):
        from openai import OpenAI

        args, config = self._arguments(prompt, generation_config, stream)
        if stream:

            def chunks():
                with OpenAI(**self._client_arguments()) as client:
                    result = client.chat.completions.create(**args)
                    try:
                        for chunk in result:
                            if chunk.choices and chunk.choices[0].delta.content:
                                yield TextResponse(
                                    chunk.choices[0].delta.content, self.provider, chunk.model
                                )
                    finally:
                        result.close()

            return chunks()
        with OpenAI(**self._client_arguments()) as client:
            return self._response(client.chat.completions.create(**args), config)

    @budgeted_inference
    async def generate_content_async(self, prompt, generation_config=None, stream=False, **kwargs):
        from openai import AsyncOpenAI

        args, config = self._arguments(prompt, generation_config, stream)
        if stream:

            async def chunks():
                async with AsyncOpenAI(**self._client_arguments()) as client:
                    result = await client.chat.completions.create(**args)
                    try:
                        async for chunk in result:
                            if chunk.choices and chunk.choices[0].delta.content:
                                yield TextResponse(
                                    chunk.choices[0].delta.content, self.provider, chunk.model
                                )
                    finally:
                        await result.close()

            return chunks()
        async with AsyncOpenAI(**self._client_arguments()) as client:
            return self._response(await client.chat.completions.create(**args), config)


class TextModel:
    def __init__(self, step, provider=None, model=None, api_key=None, **kwargs):
        selected = resolve_provider(step, provider)
        self.step = step
        self.explicit_provider = provider
        self.model_hint = model
        self.api_key = api_key
        self._api_key_provider = selected
        self._hint_provider = "gemini" if model and model.startswith("gemini") else selected
        self.kwargs = kwargs
        self._models = {}
        self._last_model = ContextVar(f"mapit_model_{id(self)}", default=None)

    @property
    def provider(self):
        return resolve_provider(self.step, self.explicit_provider)

    def _configured_model(self, provider):
        if provider == "codex":
            return settings.codex_model or None
        if provider == "gemini":
            return (
                self.model_hint
                if self.model_hint and self._hint_provider == provider
                else settings.gemini_model
            )
        if self.model_hint and self._hint_provider == provider:
            return self.model_hint
        return getattr(settings, f"{provider}_model")

    @property
    def model_name(self):
        last = self._last_model.get()
        if last and last[0] == self.provider:
            return last[1]
        return self._configured_model(self.provider)

    def _get_model(self):
        provider = self.provider
        model_name = self._configured_model(provider)
        effort = settings.codex_reasoning_effort if provider == "codex" else None
        key = (provider, model_name, effort)
        if key not in self._models:
            api_key_override = self.api_key if provider == self._api_key_provider else None
            if provider == "codex":
                model = CodexTextModel(settings)
            elif provider == "gemini":
                import google.generativeai as genai

                api_key = api_key_override or settings.gemini_api_key
                if not api_key:
                    raise ValueError("GEMINI_API_KEY is required for Gemini generation")
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(model_name, **self.kwargs)
            else:
                model = APITextModel(provider, model_name, api_key_override)
            self._models[key] = model
        return provider, self._models[key]

    def _record(self, provider, response):
        self._last_model.set(
            (provider, getattr(response, "model_name", None) or self._configured_model(provider))
        )

    @budgeted_inference
    def generate_content(self, prompt, **kwargs):
        provider, model = self._get_model()
        response = model.generate_content(prompt, **kwargs)
        if kwargs.get("stream"):

            def chunks():
                for chunk in response:
                    self._record(provider, chunk)
                    yield chunk

            return chunks()
        self._record(provider, response)
        return response

    @budgeted_inference
    async def generate_content_async(self, prompt, **kwargs):
        provider, model = self._get_model()
        response = await model.generate_content_async(prompt, **kwargs)
        if kwargs.get("stream"):

            async def chunks():
                async for chunk in response:
                    self._record(provider, chunk)
                    yield chunk

            return chunks()
        self._record(provider, response)
        return response


def create_text_model(step, provider=None, model=None, **kwargs):
    return TextModel(step, provider=provider, model=model, **kwargs)
