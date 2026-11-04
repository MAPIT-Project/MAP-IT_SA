"""Proposal provider wiring with mocked inference. No CLI or external API calls."""

import asyncio
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def proposal_modules(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "default_ai_provider", "codex")
    monkeypatch.setattr(settings, "ai_step_providers", {})
    monkeypatch.setattr(settings, "codex_enabled", True)
    monkeypatch.setattr(settings, "gemini_api_key", None)
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "openrouter_api_key", None)
    modules = {
        name: importlib.import_module("app.services.proposal_writing." + name)
        for name in (
            "proposal_ai_service",
            "ai_providers.multi_provider_service",
            "ai_providers.text_model_provider",
            "call_understanding_service",
            "draft_generator",
            "comprehensive_reviewer",
        )
    }
    return settings, modules


def mock_model(text="synthetic result"):
    response = SimpleNamespace(text=text, model_name="reported-model", usage={"total_tokens": 9})
    return SimpleNamespace(
        provider="codex",
        model_name=None,
        generate_content_async=AsyncMock(return_value=response),
    )


@pytest.mark.asyncio
async def test_default_codex_proposal_needs_no_api_keys(proposal_modules, monkeypatch):
    _, modules = proposal_modules
    bridge = modules["ai_providers.text_model_provider"]
    model = mock_model()
    factory = Mock(return_value=model)
    monkeypatch.setattr(bridge, "create_text_model", factory)
    service = modules["proposal_ai_service"].ProposalAIService()

    assert await service.generate_text("synthetic prompt") == "synthetic result"
    assert service.get_status() == {"codex": "available"}
    assert service._multi_provider.enable_fallback is False
    assert [provider.name for provider in service._multi_provider.providers] == ["codex"]
    factory.assert_called_once_with("proposal_generation", provider="codex")


@pytest.mark.asyncio
async def test_bridge_keeps_reported_model_and_usage(proposal_modules, monkeypatch):
    _, modules = proposal_modules
    bridge = modules["ai_providers.text_model_provider"]
    monkeypatch.setattr(bridge, "create_text_model", Mock(return_value=mock_model()))
    response = await bridge.TextModelProvider("codex").generate_text("synthetic")
    assert response.provider == "codex"
    assert response.model == "reported-model"
    assert response.usage == {"total_tokens": 9}


@pytest.mark.asyncio
async def test_bridge_passes_structured_schema(proposal_modules, monkeypatch):
    _, modules = proposal_modules
    bridge = modules["ai_providers.text_model_provider"]
    model = mock_model('{"score": 3}')
    monkeypatch.setattr(bridge, "create_text_model", Mock(return_value=model))
    schema = {"type": "object", "properties": {"score": {"type": "integer"}}}
    result = await bridge.TextModelProvider("codex").generate_structured("synthetic", schema)
    assert result == {"score": 3}
    assert model.generate_content_async.call_args.kwargs["generation_config"] == {
        "temperature": 0.3,
        "response_mime_type": "application/json",
        "response_schema": schema,
    }


@pytest.mark.asyncio
async def test_bridge_stream_yields_completed_message(proposal_modules, monkeypatch):
    _, modules = proposal_modules
    bridge = modules["ai_providers.text_model_provider"]
    model = mock_model()

    async def completed_chunks():
        yield SimpleNamespace(text="complete synthetic message")

    model.generate_content_async.return_value = completed_chunks()
    monkeypatch.setattr(bridge, "create_text_model", Mock(return_value=model))
    chunks = [chunk async for chunk in bridge.TextModelProvider("codex").generate_stream("prompt")]
    assert chunks == ["complete synthetic message"]
    assert model.generate_content_async.call_args.kwargs["stream"] is True


def test_codex_init_failure_never_initializes_gemini(proposal_modules, monkeypatch):
    settings, modules = proposal_modules
    monkeypatch.setattr(settings, "gemini_api_key", "dummy-paid-key")
    monkeypatch.setattr(settings, "openai_api_key", "dummy-paid-key")
    bridge = modules["ai_providers.text_model_provider"]
    monkeypatch.setattr(bridge, "create_text_model", Mock(side_effect=RuntimeError("CLI missing")))
    multi = modules["ai_providers.multi_provider_service"]
    gemini = Mock(side_effect=AssertionError("paid provider must not initialize"))
    openai = Mock(side_effect=AssertionError("paid provider must not initialize"))
    monkeypatch.setattr(multi, "GeminiProvider", gemini)
    monkeypatch.setattr(multi, "OpenAIProvider", openai)
    service = modules["proposal_ai_service"].ProposalAIService()
    fallback = Mock(side_effect=AssertionError("Gemini fallback must not initialize"))
    monkeypatch.setattr(service, "_init_fallback_gemini", fallback)

    with pytest.raises(RuntimeError, match="CLI missing"):
        service.get_status()
    gemini.assert_not_called()
    openai.assert_not_called()
    fallback.assert_not_called()


@pytest.mark.asyncio
async def test_codex_runtime_failure_never_calls_paid_provider(proposal_modules, monkeypatch):
    settings, modules = proposal_modules
    monkeypatch.setattr(settings, "gemini_api_key", "dummy-paid-key")
    bridge = modules["ai_providers.text_model_provider"]
    model = mock_model()
    model.generate_content_async.side_effect = RuntimeError("synthetic Codex error")
    monkeypatch.setattr(bridge, "create_text_model", Mock(return_value=model))
    multi = modules["ai_providers.multi_provider_service"]
    paid = Mock(side_effect=AssertionError("paid provider must not initialize"))
    monkeypatch.setattr(multi, "GeminiProvider", paid)
    service = multi.MultiProviderAIService()

    with pytest.raises(RuntimeError, match="synthetic Codex error"):
        await service.generate_text("synthetic", max_retries=1)
    paid.assert_not_called()
    assert service.get_primary_provider() == "codex"


@pytest.mark.asyncio
async def test_direct_proposal_services_use_named_steps_and_async_calls(
    proposal_modules, monkeypatch
):
    _, modules = proposal_modules
    model = mock_model('{"main_topic": "Synthetic topic", "confidence": 0.8}')
    factory = Mock(return_value=model)
    for name in ("call_understanding_service", "draft_generator", "comprehensive_reviewer"):
        monkeypatch.setattr(modules[name], "create_text_model", factory)
    understanding = modules["call_understanding_service"].CallUnderstandingService()
    draft = modules["draft_generator"].ProposalDraftGenerator(None, None)
    reviewer = modules["comprehensive_reviewer"].ComprehensiveReviewer()

    assert reviewer.model is model
    assert {call.args[0] for call in factory.call_args_list} == {
        "call_understanding", "proposal_draft", "proposal_review"
    }
    result = await understanding.understand_call("HORIZON-CL4-SYNTHETIC", call_text="Synthetic call")
    assert result.topic == "Synthetic topic"
    model.generate_content_async.return_value = SimpleNamespace(text="Improved synthetic draft")
    assert await draft.improve_draft("original", "improve", "SYNTHETIC", "excellence") == "Improved synthetic draft"
    assert model.generate_content_async.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("default", "overrides", "explicit"),
    [
        ("gemini", {"proposal_quality": "codex"}, None),
        ("gemini", {"proposal_quality": "openai"}, "codex"),
    ],
)
async def test_proposal_step_and_explicit_selection(
    proposal_modules, monkeypatch, default, overrides, explicit
):
    settings, modules = proposal_modules
    monkeypatch.setattr(settings, "default_ai_provider", default)
    monkeypatch.setattr(settings, "ai_step_providers", overrides)
    bridge = modules["ai_providers.text_model_provider"]
    factory = Mock(return_value=mock_model())
    monkeypatch.setattr(bridge, "create_text_model", factory)
    service = modules["proposal_ai_service"].ProposalAIService(
        primary_provider=explicit, step="proposal_quality"
    )

    assert await service.generate_text("synthetic") == "synthetic result"
    factory.assert_called_once_with("proposal_quality", provider="codex")
    assert service.get_status() == {"codex": "available"}


def test_gemini_default_stays_gemini(proposal_modules, monkeypatch):
    settings, modules = proposal_modules
    monkeypatch.setattr(settings, "default_ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "dummy-key")
    multi = modules["ai_providers.multi_provider_service"]
    provider = SimpleNamespace(name="gemini")
    gemini = Mock(return_value=provider)
    monkeypatch.setattr(multi, "GeminiProvider", gemini)
    service = multi.MultiProviderAIService(enable_fallback=False)

    assert service.get_primary_provider() == "gemini"
    assert gemini.call_args.args[0].model == settings.gemini_model


@pytest.mark.asyncio
async def test_cached_proposal_service_obeys_each_request_scope(proposal_modules, monkeypatch):
    from app.services.ai.factory import provider_scope

    _, modules = proposal_modules
    bridge = modules["ai_providers.text_model_provider"]

    def create_model(step, provider):
        async def generate(*args, **kwargs):
            await asyncio.sleep(0)
            return SimpleNamespace(text=provider, model_name=None, usage={})

        return SimpleNamespace(model_name=None, generate_content_async=generate)

    factory = Mock(side_effect=create_model)
    monkeypatch.setattr(bridge, "create_text_model", factory)
    service = modules["proposal_ai_service"].ProposalAIService()

    async def generate_as(provider):
        with provider_scope(provider):
            return await service.generate_text("synthetic")

    assert await generate_as("codex") == "codex"
    assert await generate_as("openrouter") == "openrouter"
    assert await asyncio.gather(generate_as("codex"), generate_as("openrouter")) == [
        "codex", "openrouter"
    ]
    assert [call.kwargs["provider"] for call in factory.call_args_list] == [
        "codex", "openrouter", "codex", "openrouter"
    ]


@pytest.mark.parametrize("selection", ["invalid-step", "disabled-codex"])
def test_bad_proposal_selection_fails_at_construction(proposal_modules, monkeypatch, selection):
    settings, modules = proposal_modules
    service_class = modules["proposal_ai_service"].ProposalAIService
    if selection == "invalid-step":
        with pytest.raises(ValueError, match="Unsupported AI step"):
            service_class(step="not-a-step")
    else:
        monkeypatch.setattr(settings, "codex_enabled", False)
        with pytest.raises(ValueError, match="CODEX_ENABLED"):
            service_class()
