"""Provider API compatibility and status tests; all network clients are mocked."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api import health_routes
from app.core.config import settings
from app.services.ai.codex import CodexError, CodexTextModel
from app.services.ai.factory import APITextModel


def api_response(text="synthetic", model="reported-model"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        model=model, usage=None,
    )


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_api_sync_text_and_json(provider, monkeypatch):
    import openai

    client = MagicMock()
    client.chat.completions.create.return_value = api_response('{"answer":7}')
    constructor = MagicMock()
    constructor.return_value.__enter__.return_value = client
    monkeypatch.setattr(openai, "OpenAI", constructor)
    model = APITextModel(provider, "configured-model", api_key="dummy-provider-key")
    response = model.generate_content("synthetic", generation_config={
        "response_schema": {"type": "object", "properties": {"answer": {"type": "integer"}}},
        "temperature": 0.3, "max_output_tokens": 30,
    })
    assert response.provider == provider
    assert response.model_name == "reported-model"
    assert response.text == '{"answer":7}'
    arguments = client.chat.completions.create.call_args.kwargs
    assert arguments["model"] == "configured-model"
    assert arguments["max_tokens"] == 30
    assert arguments["response_format"] == {"type": "json_object"}
    assert constructor.call_args.kwargs["api_key"] == "dummy-provider-key"
    if provider == "openrouter":
        assert constructor.call_args.kwargs["base_url"] == settings.openrouter_base_url


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["openai", "openrouter"])
async def test_api_async_text_and_stream(provider, monkeypatch):
    import openai

    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=api_response())
    constructor = MagicMock()
    constructor.return_value.__aenter__ = AsyncMock(return_value=client)
    constructor.return_value.__aexit__ = AsyncMock()
    monkeypatch.setattr(openai, "AsyncOpenAI", constructor)
    model = APITextModel(provider, "configured-model", api_key="dummy-key")
    response = await model.generate_content_async("synthetic")
    assert response.text == "synthetic"

    stream = MagicMock()
    stream.__aiter__.return_value = [SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="chunk"))], model="stream-model",
    )]
    stream.close = AsyncMock()
    client.chat.completions.create.return_value = stream
    result = await model.generate_content_async("synthetic", stream=True)
    chunks = [chunk async for chunk in result]
    assert chunks[0].text == "chunk"
    assert chunks[0].model_name == "stream-model"
    stream.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_codex_status_uses_local_login_check_without_gemini(monkeypatch):
    monkeypatch.setattr(settings, "default_ai_provider", "codex")
    monkeypatch.setattr(settings, "ai_step_providers", {})
    monkeypatch.setattr(settings, "codex_enabled", True)
    monkeypatch.setattr(settings, "gemini_api_key", None)
    check = AsyncMock()
    monkeypatch.setattr(CodexTextModel, "check_available", check)
    gemini = AsyncMock()
    monkeypatch.setattr(health_routes, "check_gemini", gemini)
    status = await health_routes.check_text_provider()
    assert status.name == "codex"
    assert status.status == "healthy"
    assert status.details["inference_checked"] is False
    check.assert_awaited_once()
    gemini.assert_not_called()


@pytest.mark.asyncio
async def test_codex_status_reports_login_or_cli_error(monkeypatch):
    monkeypatch.setattr(settings, "default_ai_provider", "codex")
    monkeypatch.setattr(settings, "ai_step_providers", {})
    monkeypatch.setattr(settings, "codex_enabled", True)
    monkeypatch.setattr(CodexTextModel, "check_available", AsyncMock(side_effect=CodexError("CLI missing")))
    status = await health_routes.check_text_provider()
    assert status.name == "codex"
    assert status.status == "unhealthy"
    assert status.message == "CLI missing"
