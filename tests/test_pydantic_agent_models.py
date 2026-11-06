"""Provider interchangeability and Codex model-protocol tests with synthetic responses."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from pydantic_ai.messages import ModelRequest, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.tools import ToolDefinition

from app.core.config import settings
from app.services.agents.framework import models
from app.services.ai.factory import provider_scope
from app.services.ai.types import TextResponse


def test_full_tool_catalog_can_validate_budget_calls_with_root_schema_references():
    from app.services.agents.framework.tool_schemas import input_model_for
    from app.services.agents.tool_aware_agent import ToolAwareAgent
    from app.services.ai.structured import omit_optional_nulls, validate_json

    owner = ToolAwareAgent.__new__(ToolAwareAgent)
    owner.tools = {}
    owner._init_tools()
    schema = models._decision_schema(
        [
            ToolDefinition(
                name=name, parameters_json_schema=input_model_for(definition).model_json_schema()
            )
            for name, definition in owner.tools.items()
        ],
        False,
    )
    payload = {
        "tool_calls": [
            {
                "name": "calculate_budget",
                "arguments": {
                    "action_type": "RIA",
                    "target_budget": 5000000,
                    "duration_months": 36,
                    "num_partners": 5,
                },
            },
            {
                "name": "validate_budget",
                "arguments": {
                    "total_cost": 1000000,
                    "eu_contribution": 1100000,
                    "action_type": "RIA",
                },
            },
        ],
        "text": None,
    }
    cleaned = omit_optional_nulls(payload, schema)
    assert validate_json(json.dumps(cleaned), schema) == payload


def parameters():
    return ModelRequestParameters(
        function_tools=[
            ToolDefinition(
                name="synthetic_search",
                parameters_json_schema={
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                    "required": ["limit"],
                    "additionalProperties": False,
                },
            )
        ],
        output_tools=[
            ToolDefinition(
                name="final_result",
                parameters_json_schema={
                    "type": "object",
                    "properties": {"answer": {"type": "string"}},
                    "required": ["answer"],
                    "additionalProperties": False,
                },
                kind="output",
            )
        ],
        output_mode="tool",
        allow_text_output=False,
    )


def transport(response):
    return SimpleNamespace(
        model_name="synthetic-codex-model",
        generate_content_async=AsyncMock(
            return_value=TextResponse(
                json.dumps(response),
                "codex",
                "synthetic-codex-model",
                {"input_tokens": 3, "output_tokens": 2},
            )
        ),
    )


@pytest.mark.asyncio
async def test_codex_maps_tool_calls_results_and_final_output():
    cli = transport(
        {"tool_calls": [{"name": "synthetic_search", "arguments": {"limit": 2}}], "text": None}
    )
    model = models.CodexAgentModel(cli)
    request = ModelRequest([UserPromptPart("Synthetic request")])
    first = await model.request([request], None, parameters())
    assert isinstance(first.parts[0], ToolCallPart)
    assert first.parts[0].tool_name == "synthetic_search"
    assert first.parts[0].args == {"limit": 2}
    assert first.provider_name == "codex"
    assert first.model_name == "synthetic-codex-model"
    assert first.usage.input_tokens == 3

    cli.generate_content_async.return_value = TextResponse(
        json.dumps(
            {
                "tool_calls": [
                    {"name": "final_result", "arguments": {"answer": "Synthetic answer"}}
                ],
                "text": None,
            }
        ),
        "codex",
        None,
    )
    returned = ModelRequest(
        [ToolReturnPart("synthetic_search", {"records": 2}, first.parts[0].tool_call_id)]
    )
    second = await model.request([request, first, returned], None, parameters())
    assert second.parts[0].tool_name == "final_result"
    assert second.model_name is None
    prompt = cli.generate_content_async.call_args.args[0]
    assert first.parts[0].tool_call_id in prompt
    assert '"records": 2' in prompt
    schema = cli.generate_content_async.call_args.kwargs["generation_config"]["response_schema"]
    assert schema["properties"]["tool_calls"]["minItems"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "decision",
    [
        {"tool_calls": [{"name": "shell", "arguments": {}}], "text": None},
        {
            "tool_calls": [{"name": "synthetic_search", "arguments": {"limit": "lots"}}],
            "text": None,
        },
        {"tool_calls": [], "text": "Bypass required final schema"},
    ],
)
async def test_codex_rejects_unknown_tools_invalid_args_and_unpermitted_text(decision):
    model = models.CodexAgentModel(transport(decision))
    with pytest.raises(ValueError):
        await model.request([ModelRequest([UserPromptPart("Synthetic")])], None, parameters())


@pytest.mark.asyncio
async def test_codex_cancellation_is_not_swallowed():
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def pending(*args, **kwargs):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    cli = SimpleNamespace(model_name=None, generate_content_async=pending)
    task = asyncio.create_task(
        models.CodexAgentModel(cli).request(
            [ModelRequest([UserPromptPart("Synthetic")])], None, parameters()
        )
    )
    await asyncio.wait_for(started.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled.is_set()


@pytest.mark.asyncio
@pytest.mark.parametrize("selected", ["openai", "openrouter", "gemini"])
async def test_api_provider_selection_uses_explicit_keys_and_closes_client(monkeypatch, selected):
    import pydantic_ai.models.google
    import pydantic_ai.models.openai
    import pydantic_ai.providers.google
    import pydantic_ai.providers.openai

    monkeypatch.setattr(settings, f"{selected}_api_key", f"dummy-{selected}-key")
    client = SimpleNamespace(close=AsyncMock())
    constructor = Mock(return_value=SimpleNamespace(client=client))
    native_model = Mock(return_value="synthetic-native-model")
    if selected == "gemini":
        client.close = Mock()
        client.aio = SimpleNamespace(aclose=AsyncMock())
        instance = MagicMock(client=client)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock()
        constructor.return_value = instance
        monkeypatch.setattr(pydantic_ai.providers.google, "GoogleProvider", constructor)
        monkeypatch.setattr(pydantic_ai.models.google, "GoogleModel", native_model)
    else:
        monkeypatch.setattr(pydantic_ai.providers.openai, "OpenAIProvider", constructor)
        monkeypatch.setattr(pydantic_ai.models.openai, "OpenAIChatModel", native_model)
    with provider_scope(selected):
        async with models.model_for_step(model_hint="gemini-synthetic-pro") as (model, provider):
            assert provider == selected
            assert model == "synthetic-native-model"
    assert constructor.call_args.kwargs["api_key"] == f"dummy-{selected}-key"
    if selected == "gemini":
        assert native_model.call_args.args[0] == "gemini-synthetic-pro"
        client.aio.aclose.assert_awaited_once()
        client.close.assert_called_once()
        instance.__aexit__.assert_awaited_once()
    else:
        assert native_model.call_args.args[0] == getattr(settings, f"{selected}_model")
        if selected == "openrouter":
            assert constructor.call_args.kwargs["base_url"] == settings.openrouter_base_url
        client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_codex_selection_needs_no_api_keys_or_api_fallback(monkeypatch):
    monkeypatch.setattr(settings, "codex_enabled", True)
    for name in ("gemini", "openai", "openrouter"):
        monkeypatch.setattr(settings, f"{name}_api_key", None)
    cli = SimpleNamespace(model_name=None)
    constructor = Mock(return_value=cli)
    monkeypatch.setattr(models, "CodexTextModel", constructor)
    with provider_scope("codex"):
        async with models.model_for_step() as (model, provider):
            assert provider == "codex"
            assert isinstance(model, models.CodexAgentModel)
            assert model.transport is cli
    constructor.assert_called_once_with(settings)
