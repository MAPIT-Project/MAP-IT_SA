"""Self-correction through the current V3 Pydantic AI model/tool protocol.

The removed evaluator/reflector/replanner classes are no longer application
components. These tests check feedback and evidence retrieval in the active loop.
"""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel, ConfigDict
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from app.services.agents.framework import runtime
from app.services.agents.tool_aware_agent import ToolAwareAgent
from app.services.agents.tool_registry import AgentPlan, Tool, ToolCall, ToolCategory


class SearchArguments(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    query: str


@pytest.fixture
def agent():
    owner = ToolAwareAgent.__new__(ToolAwareAgent)
    owner.llm = SimpleNamespace(model_name="synthetic-model")
    owner.max_iterations = 5
    owner.plan_cache = None
    owner.speculative_executor = None
    owner.analytics = None
    owner._select_knowledge_sections = Mock(return_value="Synthetic source knowledge")
    owner._reset_generation_metadata()
    owner.tools = {
        "synthetic_search": Tool(
            "synthetic_search",
            "Search a synthetic evidence source.",
            ToolCategory.PROJECTS,
            {"query": "Search terms"},
            input_model=SearchArguments,
        )
    }
    return owner


def returned_parts(messages):
    return [
        part
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    ]


def final(info, answer):
    return ModelResponse(
        [ToolCallPart(info.output_tools[0].name, {"answer": answer, "confidence": 0.8})]
    )


def selected_model(monkeypatch, respond):
    @asynccontextmanager
    async def model(step, model_hint=None):
        yield FunctionModel(respond), "gemini"

    monkeypatch.setattr(runtime, "model_for_step", model)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "initial,refined",
    [
        ("hydrogen fuel cell consortium offshore Europe 2099", "hydrogen"),
        ("energy", "hydrogen fuel cells"),
        ("climate research", "renewable energy projects"),
    ],
)
async def test_empty_results_can_trigger_refined_search(monkeypatch, agent, initial, refined):
    def execute(specs):
        params = specs[0]["parameters"]
        records = [] if params["query"] == initial else [{"id": "SYNTHETIC-1"}]
        return [ToolCall("synthetic_search", params, result={"records": records}, success=True)]

    agent._execute_tool_calls = AsyncMock(side_effect=execute)

    def respond(messages, info):
        returned = returned_parts(messages)
        if not returned:
            return ModelResponse([ToolCallPart("synthetic_search", {"query": initial})])
        if len(returned) == 1:
            assert returned[-1].content == {"records": []}
            return ModelResponse([ToolCallPart("synthetic_search", {"query": refined})])
        assert returned[-1].content["records"] == [{"id": "SYNTHETIC-1"}]
        return final(info, "The refined search found SYNTHETIC-1.")

    selected_model(monkeypatch, respond)
    plan = AgentPlan("Find relevant projects", "simple", [])
    count, results = await runtime.run_agent_loop(agent, plan.query, "", plan)
    assert count == 3
    assert plan.error is None
    assert plan.final_answer == "The refined search found SYNTHETIC-1."
    assert agent._execute_tool_calls.await_count == 2
    assert [
        entry.args[0][0]["parameters"]["query"]
        for entry in agent._execute_tool_calls.await_args_list
    ] == [
        initial,
        refined,
    ]
    assert len(results) == 2


@pytest.mark.asyncio
async def test_failed_tool_feedback_allows_an_alternative_query(monkeypatch, agent):
    agent._execute_tool_calls = AsyncMock(
        side_effect=[
            [
                ToolCall(
                    "synthetic_search",
                    {"query": "original"},
                    success=False,
                    error="Synthetic timeout",
                )
            ],
            [
                ToolCall(
                    "synthetic_search",
                    {"query": "alternative"},
                    success=True,
                    result={"id": "recovered"},
                )
            ],
        ]
    )

    def respond(messages, info):
        returned = returned_parts(messages)
        if not returned:
            return ModelResponse([ToolCallPart("synthetic_search", {"query": "original"})])
        if len(returned) == 1:
            assert returned[0].content == {"error": "Synthetic timeout"}
            return ModelResponse([ToolCallPart("synthetic_search", {"query": "alternative"})])
        return final(info, "The alternative source returned recovered.")

    selected_model(monkeypatch, respond)
    plan = AgentPlan("Find relevant projects", "simple", [])
    _, results = await runtime.run_agent_loop(agent, plan.query, "", plan)
    assert plan.error is None
    assert len(results) == 1
    assert list(results.values()) == [{"id": "recovered"}]
    assert plan.reasoning_steps[0].tool_calls[0].success is False
    assert plan.reasoning_steps[1].tool_calls[0].success is True


@pytest.mark.asyncio
async def test_validation_feedback_corrects_arguments_before_dispatch(monkeypatch, agent):
    agent._execute_tool_calls = AsyncMock(
        return_value=[
            ToolCall(
                "synthetic_search", {"query": "hydrogen"}, result={"records": []}, success=True
            )
        ]
    )

    def respond(messages, info):
        returned = returned_parts(messages)
        if any(part.outcome == "success" for part in returned):
            return final(info, "No synthetic records matched hydrogen.")
        if returned:
            assert returned[-1].outcome == "retried"
            assert agent._execute_tool_calls.await_count == 0
            return ModelResponse([ToolCallPart("synthetic_search", {"query": "hydrogen"})])
        return ModelResponse([ToolCallPart("synthetic_search", {"query": 123})])

    selected_model(monkeypatch, respond)
    plan = AgentPlan("Search projects", "simple", [])
    await runtime.run_agent_loop(agent, plan.query, "", plan)
    assert plan.error is None
    assert agent._execute_tool_calls.await_count == 1
    assert agent._execute_tool_calls.await_args.args[0][0]["parameters"] == {"query": "hydrogen"}


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 2, 3])
async def test_repeated_searches_stop_at_request_limit(monkeypatch, agent, limit):
    agent.max_iterations = limit
    agent._execute_tool_calls = AsyncMock(
        return_value=[
            ToolCall(
                "synthetic_search", {"query": "hydrogen"}, result={"records": []}, success=True
            )
        ]
    )
    selected_model(
        monkeypatch,
        lambda messages, info: ModelResponse(
            [ToolCallPart("synthetic_search", {"query": "hydrogen"})]
        ),
    )
    plan = AgentPlan("Search projects", "simple", [])
    count, _ = await runtime.run_agent_loop(agent, plan.query, "", plan)
    assert count == limit
    assert agent._execute_tool_calls.await_count == limit
    assert plan.error == "Agent execution limit reached"
    assert plan.final_answer is None


@pytest.mark.asyncio
async def test_final_answer_stops_iteration(monkeypatch, agent):
    agent._execute_tool_calls = AsyncMock()
    selected_model(
        monkeypatch, lambda messages, info: final(info, "No retrieval is needed for this greeting.")
    )
    plan = AgentPlan("Hello", "simple", [])
    count, _ = await runtime.run_agent_loop(agent, plan.query, "", plan)
    assert count == 1
    assert plan.error is None
    agent._execute_tool_calls.assert_not_awaited()
