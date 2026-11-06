"""Framework integration with synthetic models and tools; no external inference or data."""

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import FunctionModel

from app.core.config import settings
from app.services.agents.framework import runtime
from app.services.agents.framework.tool_schemas import input_model_for
from app.services.agents.proposal_aware_agent import ProposalAwareAgent
from app.services.agents.tool_aware_agent import ToolAwareAgent
from app.services.agents.tool_registry import AgentPlan, Tool, ToolCall, ToolCategory
from app.services.ai.factory import provider_scope, resolve_provider


class SearchArguments(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    limit: int = Field(ge=1, le=10)


def owner_with_tool(proposal=False):
    cls = ProposalAwareAgent if proposal else ToolAwareAgent
    owner = cls.__new__(cls)
    owner.tools = {
        "synthetic_search": Tool(
            "synthetic_search",
            "Search synthetic records.",
            ToolCategory.PROJECTS,
            {"limit": "Result count"},
            input_model=SearchArguments,
        )
    }
    owner.llm = SimpleNamespace(model_name="synthetic-model")
    owner.max_iterations = 5
    owner.plan_cache = None
    owner.speculative_executor = None
    owner.analytics = None
    owner._select_knowledge_sections = Mock(return_value="Synthetic funding knowledge")
    owner._reset_generation_metadata()
    if proposal:
        owner.session_manager = None
    return owner


def plan():
    return AgentPlan("Synthetic query", "simple", [])


def tool_returns(messages):
    return [
        part
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    ]


def final(info, answer="Answer grounded in the synthetic tool result."):
    return ModelResponse(
        [ToolCallPart(info.output_tools[0].name, {"answer": answer, "confidence": 0.9})],
        model_name="synthetic-reported-model",
    )


def use_model(monkeypatch, respond):
    @asynccontextmanager
    async def selected(step, model_hint=None):
        yield FunctionModel(respond), resolve_provider(step)

    monkeypatch.setattr(runtime, "model_for_step", selected)


@pytest.mark.asyncio
async def test_framework_auth_failure_is_safe_and_does_not_execute_tools(monkeypatch):
    owner = owner_with_tool()
    owner.llm.provider = "gemini"
    owner._execute_tool_calls = AsyncMock()

    def respond(messages, info):
        raise RuntimeError("API_KEY_INVALID private uploaded document and secret-value")

    use_model(monkeypatch, respond)
    current = plan()
    count, results = await runtime.run_agent_loop(owner, "Test", "", current)
    assert count == 1
    assert results == {}
    assert "authentication failed" in current.error
    assert "private" not in current.error
    assert "secret-value" not in current.error
    assert current.final_answer is None
    assert current.confidence == 0
    owner._execute_tool_calls.assert_not_awaited()


@pytest.mark.asyncio
async def test_framework_runs_validated_tool_and_preserves_events(monkeypatch):
    owner = owner_with_tool()
    owner._execute_tool_calls = AsyncMock(
        return_value=[
            ToolCall(
                "synthetic_search",
                {"limit": 2},
                result={"projects": [{"id": "synthetic"}]},
                success=True,
            )
        ]
    )

    def respond(messages, info):
        if tool_returns(messages):
            return final(info)
        return ModelResponse([ToolCallPart("synthetic_search", {"limit": 2})])

    use_model(monkeypatch, respond)
    events = []

    async def emit(event):
        events.append(event)

    current = plan()
    count, results = await runtime.run_agent_loop(owner, "Synthetic query", "", current, emit)
    assert count == 2
    assert current.framework == "pydantic"
    assert current.error is None
    assert current.confidence == 0.9
    assert "synthetic_search_1_1" in results
    assert [event["type"] for event in events] == [
        "agent_thinking",
        "agent_thinking",
        "tool_call",
        "tool_result",
        "agent_thinking",
        "agent_thinking",
    ]
    assert owner._generation_metadata()["reasoning_provider"] == "gemini"
    owner._execute_tool_calls.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("selected", ["openai", "openrouter", "gemini"])
async def test_native_api_models_complete_same_tool_round_trip(monkeypatch, selected):
    import pydantic_ai.providers.google
    import pydantic_ai.providers.openai
    from google.genai import types as google_types
    from openai.types.chat import ChatCompletion

    owner = owner_with_tool()
    owner.llm = SimpleNamespace(model_name=None)
    owner._execute_tool_calls = AsyncMock(
        return_value=[
            ToolCall("synthetic_search", {"limit": 2}, result={"records": 2}, success=True)
        ]
    )
    monkeypatch.setattr(settings, f"{selected}_api_key", f"dummy-{selected}")
    if selected == "gemini":
        real_provider = pydantic_ai.providers.google.GoogleProvider(api_key="dummy-gemini")

        def response(name, arguments):
            return google_types.GenerateContentResponse(
                candidates=[
                    google_types.Candidate(
                        content=google_types.Content(
                            role="model",
                            parts=[
                                google_types.Part(
                                    function_call=google_types.FunctionCall(
                                        name=name, args=arguments
                                    )
                                )
                            ],
                        ),
                        finish_reason="STOP",
                    )
                ],
                model_version="synthetic-gemini-version",
            )

        create = AsyncMock(
            side_effect=[
                response("synthetic_search", {"limit": 2}),
                response(
                    "final_result",
                    {"answer": "The synthetic source returned two records.", "confidence": 0.9},
                ),
            ]
        )
        monkeypatch.setattr(real_provider.client.aio.models, "generate_content", create)
        monkeypatch.setattr(
            pydantic_ai.providers.google, "GoogleProvider", Mock(return_value=real_provider)
        )
    else:
        real_provider = pydantic_ai.providers.openai.OpenAIProvider(
            api_key=f"dummy-{selected}", base_url="https://example.invalid/v1"
        )

        def response(name, arguments):
            import json

            return ChatCompletion.model_validate(
                {
                    "id": "synthetic-response",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "synthetic-api-version",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": f"synthetic-{name}",
                                        "type": "function",
                                        "function": {
                                            "name": name,
                                            "arguments": json.dumps(arguments),
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                }
            )

        create = AsyncMock(
            side_effect=[
                response("synthetic_search", {"limit": 2}),
                response(
                    "final_result",
                    {"answer": "The synthetic source returned two records.", "confidence": 0.9},
                ),
            ]
        )
        monkeypatch.setattr(real_provider.client.chat.completions, "create", create)
        monkeypatch.setattr(
            pydantic_ai.providers.openai, "OpenAIProvider", Mock(return_value=real_provider)
        )
    with provider_scope(selected):
        current = plan()
        count, results = await runtime.run_agent_loop(owner, "Synthetic query", "", current)
        assert count == 2
        assert current.error is None
        assert current.final_answer == "The synthetic source returned two records."
        assert len(results) == 1
        assert owner._generation_metadata()["ai_provider"] == selected
    owner._execute_tool_calls.assert_awaited_once()
    assert create.await_count == 2


@pytest.mark.asyncio
async def test_invalid_arguments_retry_before_tool_executes(monkeypatch):
    owner = owner_with_tool()
    owner._execute_tool_calls = AsyncMock(
        return_value=[
            ToolCall("synthetic_search", {"limit": 2}, result={"records": 2}, success=True)
        ]
    )
    invalid_was_rejected = False

    def respond(messages, info):
        nonlocal invalid_was_rejected
        returned = tool_returns(messages)
        if any(part.outcome == "success" for part in returned):
            return final(info)
        retry = any(part.outcome == "retried" for part in returned) or any(
            isinstance(part, RetryPromptPart)
            for message in messages
            if isinstance(message, ModelRequest)
            for part in message.parts
        )
        if retry:
            invalid_was_rejected = True
            assert owner._execute_tool_calls.await_count == 0
            return ModelResponse([ToolCallPart("synthetic_search", {"limit": 2})])
        return ModelResponse([ToolCallPart("synthetic_search", {"limit": "lots"})])

    use_model(monkeypatch, respond)
    current = plan()
    await runtime.run_agent_loop(owner, "Synthetic query", "", current)
    assert invalid_was_rejected
    assert current.error is None
    assert owner._execute_tool_calls.await_count == 1
    assert owner._execute_tool_calls.call_args.args[0][0]["parameters"] == {"limit": 2}


@pytest.mark.asyncio
async def test_base_agent_accepts_context_without_legacy_model(monkeypatch):
    owner = owner_with_tool()
    owner.llm = None
    use_model(monkeypatch, lambda messages, info: final(info))
    current = plan()
    await runtime.run_agent_loop(
        owner, "Synthetic query", "", current, proposal_context="Quoted proposal data"
    )
    assert current.error is None
    assert current.final_answer


@pytest.mark.asyncio
async def test_empty_dispatch_result_is_reported_as_tool_failure(monkeypatch):
    owner = owner_with_tool()
    owner._execute_tool_calls = AsyncMock(return_value=[])

    def respond(messages, info):
        returned = tool_returns(messages)
        if returned:
            assert returned[-1].content == {"error": "Tool dispatcher returned no result"}
            return final(info, "The tool returned no result.")
        return ModelResponse([ToolCallPart("synthetic_search", {"limit": 2})])

    use_model(monkeypatch, respond)
    events = []

    async def emit(event):
        events.append(event)

    current = plan()
    _, results = await runtime.run_agent_loop(owner, "Synthetic query", "", current, emit)
    assert current.error is None
    assert results == {}
    result_event = next(event for event in events if event["type"] == "tool_result")
    assert result_event["success"] is False


@pytest.mark.asyncio
async def test_execution_error_is_not_recorded_as_success(monkeypatch):
    owner = owner_with_tool()
    owner._execute_tool_calls = AsyncMock(
        return_value=[
            ToolCall(
                "synthetic_search",
                {"limit": 2},
                result={"error": "Synthetic source unavailable"},
                success=True,
            )
        ]
    )

    def respond(messages, info):
        returned = tool_returns(messages)
        if returned:
            assert returned[-1].content["error"] == "Synthetic source unavailable"
            return final(info, "The synthetic source is unavailable.")
        return ModelResponse([ToolCallPart("synthetic_search", {"limit": 2})])

    use_model(monkeypatch, respond)
    current = plan()
    _, results = await runtime.run_agent_loop(owner, "Synthetic query", "", current)
    assert results == {}
    assert current.reasoning_steps[0].tool_calls[0].success is False
    assert "unavailable" in current.final_answer


@pytest.mark.asyncio
async def test_framework_request_limit_retains_results(monkeypatch):
    owner = owner_with_tool()
    owner.max_iterations = 2
    owner._execute_tool_calls = AsyncMock(
        side_effect=lambda specs: [
            ToolCall(
                "synthetic_search", specs[0]["parameters"], result={"records": 2}, success=True
            )
        ]
    )
    use_model(
        monkeypatch,
        lambda messages, info: ModelResponse([ToolCallPart("synthetic_search", {"limit": 2})]),
    )
    current = plan()
    count, results = await runtime.run_agent_loop(owner, "Synthetic query", "", current)
    assert count == 2
    assert len(results) == 2
    assert current.final_answer is None
    assert current.error == "Agent execution limit reached"


@pytest.mark.asyncio
async def test_framework_cancellation_reaches_model(monkeypatch):
    owner = owner_with_tool()
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def respond(messages, info):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    use_model(monkeypatch, respond)
    task = asyncio.create_task(runtime.run_agent_loop(owner, "Synthetic query", "", plan()))
    await asyncio.wait_for(started.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_concurrent_requests_keep_provider_and_conversation_state(monkeypatch):
    monkeypatch.setattr(settings, "codex_enabled", True)
    owner = owner_with_tool()
    reached = 0
    gate = asyncio.Event()

    async def execute(specs):
        nonlocal reached
        reached += 1
        if reached == 2:
            gate.set()
        await gate.wait()
        return [
            ToolCall(
                "synthetic_search",
                specs[0]["parameters"],
                result={"conversation": owner._conversation_id},
                success=True,
            )
        ]

    owner._execute_tool_calls = execute

    def respond(messages, info):
        if tool_returns(messages):
            return final(info)
        return ModelResponse([ToolCallPart("synthetic_search", {"limit": 1})])

    use_model(monkeypatch, respond)

    async def infer(provider, conversation):
        with provider_scope(provider):
            owner._conversation_id = conversation
            owner._reset_generation_metadata()
            _, results = await runtime.run_agent_loop(owner, "Synthetic", "", plan())
            return next(iter(results.values()))["conversation"], owner._generation_metadata()[
                "ai_provider"
            ]

    assert await asyncio.wait_for(asyncio.gather(infer("gemini", 11), infer("codex", 22)), 3) == [
        (11, "gemini"),
        (22, "codex"),
    ]


@pytest.mark.asyncio
async def test_proposal_stream_keeps_section_update_contract(monkeypatch):
    owner = owner_with_tool(proposal=True)
    owner._framework_proposal_guidance = Mock(return_value="OFFICIAL_TARGET_GUIDANCE")
    owner.tools = {
        "generate_section_draft": Tool(
            "generate_section_draft",
            "Generate synthetic section.",
            ToolCategory.DOCUMENTS,
            {"section_id": "Section ID", "call_id": "Call ID"},
        )
    }
    owner._execute_tool_calls_with_proposal = AsyncMock(
        return_value=[
            ToolCall(
                "generate_section_draft",
                {"section_id": "excellence.objectives", "call_id": "SYNTHETIC"},
                result={"section_id": "excellence.objectives", "content": "Synthetic draft"},
                success=True,
            )
        ]
    )

    def respond(messages, info):
        assert "OFFICIAL_TARGET_GUIDANCE" in str(messages)
        if tool_returns(messages):
            return final(info, "The synthetic objectives section was generated.")
        return ModelResponse(
            [
                ToolCallPart(
                    "generate_section_draft",
                    {"section_id": "excellence.objectives", "call_id": "SYNTHETIC"},
                )
            ]
        )

    use_model(monkeypatch, respond)
    current = plan()
    from datetime import datetime

    events = [
        event
        async for event in owner._framework_proposal_stream(
            "Generate objectives",
            "",
            "Synthetic proposal context",
            current,
            "writing",
            datetime.now(),
        )
    ]
    kinds = [event["type"] for event in events]
    assert (
        kinds.index("tool_result") < kinds.index("section_update") < kinds.index("agent_complete")
    )
    assert (
        next(event for event in events if event["type"] == "section_update")["content"]
        == "Synthetic draft"
    )
    assert events[-1]["result"]["sections_affected"] == ["excellence.objectives"]
    assert events[-1]["result"]["agent_framework"] == "pydantic"


def test_all_registered_tools_have_closed_schemas():
    research = ToolAwareAgent.__new__(ToolAwareAgent)
    research.tools = {}
    research._init_tools()
    proposal = ProposalAwareAgent.__new__(ProposalAwareAgent)
    proposal.tools = research.tools.copy()
    proposal._init_proposal_tools()
    assert len(research.tools) == 42
    assert len(proposal.tools) == 52
    for definition in proposal.tools.values():
        model = input_model_for(definition)
        assert model.model_json_schema()["additionalProperties"] is False


def test_typed_inputs_reject_bad_types_and_keep_dispatch_defaults():
    research = ToolAwareAgent.__new__(ToolAwareAgent)
    research.tools = {}
    research._init_tools()
    search = input_model_for(research.tools["search_projects"])
    with pytest.raises(ValidationError):
        search.model_validate({"limit": "lots"})
    with pytest.raises(ValidationError):
        search.model_validate({"limit": 2, "shell": "anything"})
    budget = input_model_for(research.tools["calculate_budget"])
    assert budget.model_validate({}).model_dump(exclude_unset=True) == {}
    validation = input_model_for(research.tools["validate_budget"])
    assert validation.model_validate({"total_cost": -1.0, "eu_contribution": 2.0}).total_cost == -1


def test_disabled_smart_routing_sets_model_in_new_request_context(monkeypatch):
    monkeypatch.setattr(settings, "ai_step_providers", {})
    monkeypatch.setattr(settings, "default_ai_provider", "gemini")
    owner = owner_with_tool()
    owner.smart_model_routing = False
    owner.llm_flash = SimpleNamespace(model_name="synthetic-flash")
    owner.llm_pro = None
    owner.llm = None
    owner._select_model_for_query("analysis", "Synthetic request")
    assert owner.llm is owner.llm_flash
    assert owner._active_model_name == "synthetic-flash"
