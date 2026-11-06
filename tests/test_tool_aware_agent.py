"""V3 agent integration with synthetic inference and mocked service boundaries.

The real constructor, framework loop, tool dispatcher, response metadata and
quality analyzer execute. Redis, analytics and paid model APIs never execute.
"""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from app.core.config import settings
from app.services.agents.framework import runtime
from app.services.agents.query_preprocessing import LongQueryResult
from app.services.agents.tool_aware_agent import ToolAwareAgent

ANSWER = (
    "Horizon Europe funds research and innovation. The synthetic source identifies "
    "HORIZON-CL5-2026-D3-01 as a hydrogen research call."
)


@pytest.fixture(autouse=True)
def isolated_agent_services(monkeypatch):
    """Stub external construction without replacing the constructor being tested."""

    def init_llm(owner):
        owner.llm_provider = "gemini"
        owner.smart_model_routing = False
        owner.llm_flash = SimpleNamespace(provider="gemini", model_name="synthetic-model")
        owner.llm_pro = None
        owner.llm_response = owner.llm_flash
        owner.llm_preprocessing = None
        owner.llm = owner.llm_flash

    def init_cache(owner):
        owner.plan_cache = None
        owner._redis_client = None

    monkeypatch.setattr(ToolAwareAgent, "_init_llm", init_llm)
    monkeypatch.setattr(ToolAwareAgent, "_init_cache", init_cache)
    monkeypatch.setattr(
        ToolAwareAgent, "_init_analytics", lambda owner: setattr(owner, "analytics", None)
    )
    monkeypatch.setattr(
        ToolAwareAgent,
        "_init_speculative_executor",
        lambda owner: setattr(owner, "speculative_executor", None),
    )
    monkeypatch.setattr(settings, "agent_framework", "pydantic")
    monkeypatch.setattr(settings, "default_ai_provider", "gemini")
    monkeypatch.setattr(settings, "ai_step_providers", {})


@pytest.fixture
def inference(monkeypatch):
    state = SimpleNamespace(answer=ANSWER, tool=None, repeat=False, error=None, messages=[])

    def respond(messages, info):
        state.messages.append(messages)
        if state.error:
            raise state.error
        returned = [
            part
            for message in messages
            if isinstance(message, ModelRequest)
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if state.tool and (state.repeat or not returned):
            return ModelResponse([ToolCallPart(state.tool, {"keywords": "hydrogen"})])
        return ModelResponse(
            [ToolCallPart(info.output_tools[0].name, {"answer": state.answer, "confidence": 0.9})],
            model_name="synthetic-reported-model",
        )

    @asynccontextmanager
    async def selected(step, model_hint=None):
        yield FunctionModel(respond), "gemini"

    monkeypatch.setattr(runtime, "model_for_step", selected)
    return state


@pytest.fixture
def agent(inference):
    return ToolAwareAgent()


class TestToolAwareAgentInitialization:
    def test_agent_initialization(self):
        assert isinstance(ToolAwareAgent(), ToolAwareAgent)

    def test_max_iterations_configurable(self):
        assert ToolAwareAgent(max_iterations=3).max_iterations == 3

    def test_default_max_iterations(self):
        assert ToolAwareAgent().max_iterations == 5


class TestToolDefinitions:
    def test_tool_definitions_exist(self):
        assert len(ToolAwareAgent().tools) == 42

    def test_search_funding_calls_tool(self):
        tool = ToolAwareAgent().tools["search_funding_calls"]
        assert tool.name == "search_funding_calls"
        assert "keywords" in tool.parameters

    def test_search_projects_tool(self):
        tool = ToolAwareAgent().tools["search_projects"]
        assert tool.name == "search_projects"
        assert tool.description


class TestQueryProcessing:
    @pytest.mark.asyncio
    async def test_process_query_returns_dict(self, agent):
        result = await agent.process_query("What is Horizon Europe?")
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["agent_framework"] == "pydantic"
        assert result["agent_error"] is None

    @pytest.mark.asyncio
    async def test_process_query_has_answer(self, agent):
        assert (await agent.process_query("What is Horizon Europe?"))["answer"] == ANSWER

    @pytest.mark.asyncio
    async def test_process_query_has_confidence(self, agent):
        assert (await agent.process_query("What is Horizon Europe?"))["confidence"] == 0.9


class TestReActLoop:
    @pytest.mark.asyncio
    async def test_iteration_count_tracked(self, agent):
        result = await agent.process_query("What is Horizon Europe?")
        assert result["iterations"] == 1
        assert len(result["reasoning_steps"]) == 1

    @pytest.mark.asyncio
    async def test_max_iterations_respected(self, inference):
        inference.tool = "search_funding_calls"
        inference.repeat = True
        owner = ToolAwareAgent(max_iterations=2)
        owner._tool_search_funding_calls = AsyncMock(return_value={"calls": []})
        result = await owner.process_query("Find hydrogen funding calls")
        assert result["iterations"] == 2
        assert result["agent_error"] == "Agent execution limit reached"
        assert owner._tool_search_funding_calls.await_count == 2
        assert result["success"] is False


class TestContextHandling:
    @pytest.mark.asyncio
    async def test_conversation_context_included(self, agent, inference):
        context = "The user is researching synthetic hydrogen projects."
        await agent.process_query("What about the budget?", context=context)
        prompt = str(inference.messages[-1])
        assert context in prompt
        assert "What about the budget?" in prompt

    @pytest.mark.asyncio
    async def test_conversation_history_accepted(self, agent):
        history = [{"sender": "user", "text": "What is ERC?"}]
        result = await agent.process_query(
            "What about the budget?",
            context="The prior topic is ERC.",
            conversation_history=history,
            conversation_id=314,
        )
        assert result["success"] is True
        assert agent._conversation_id == 314
        assert history == [{"sender": "user", "text": "What is ERC?"}]


class TestToolExecution:
    @pytest.mark.asyncio
    async def test_tool_results_recorded(self, agent, inference):
        inference.tool = "search_funding_calls"
        records = {"calls": [{"call_id": "SYNTHETIC-CALL"}]}
        agent._tool_search_funding_calls = AsyncMock(return_value=records)
        result = await agent.process_query("Find hydrogen funding calls")
        assert list(result["tool_results"].values()) == [records]
        agent._tool_search_funding_calls.assert_awaited_once_with({"keywords": "hydrogen"})

    @pytest.mark.asyncio
    async def test_sources_used_tracked(self, agent, inference):
        inference.tool = "search_funding_calls"
        agent._tool_search_funding_calls = AsyncMock(return_value={"calls": []})
        result = await agent.process_query("Find hydrogen funding calls")
        assert result["sources_used"] == ["search_funding_calls_1_1"]
        assert result["reasoning_steps"][0]["tools_called"] == ["search_funding_calls"]


class TestReasoningSteps:
    @pytest.mark.asyncio
    async def test_reasoning_steps_recorded(self, agent):
        result = await agent.process_query("Explain research funding")
        assert result["reasoning_steps"][0]["step"] == 1
        assert result["reasoning_steps"][0]["action"] == "conclude"

    @pytest.mark.asyncio
    async def test_reasoning_steps_include_progress_description(self, agent):
        result = await agent.process_query("Explain research funding")
        assert (
            result["reasoning_steps"][0]["thought"]
            == "The response is ready. No tool results were used."
        )


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_handles_llm_error(self, agent, inference):
        inference.error = RuntimeError("synthetic sensitive request content")
        result = await agent.process_query("Explain research funding")
        assert result["success"] is False
        assert result["agent_error"] == "RuntimeError: agent execution failed"
        assert "sensitive" not in result["agent_error"]

    @pytest.mark.asyncio
    async def test_handles_tool_error(self, agent, inference):
        inference.tool = "search_funding_calls"
        agent._tool_search_funding_calls = AsyncMock(
            side_effect=ValueError("Synthetic tool failed")
        )
        result = await agent.process_query("Find hydrogen funding calls")
        assert result["tool_results"] == {}
        assert result["reasoning_steps"][0]["tool_calls"][0]["success"] is False
        assert result["success"] is True  # Model can explain the tool failure.


class TestResponseSynthesis:
    @pytest.mark.asyncio
    async def test_answer_generated(self, agent):
        assert (await agent.process_query("Explain research funding"))["answer"] == ANSWER

    @pytest.mark.asyncio
    async def test_answer_not_empty(self, agent, inference):
        inference.answer = "A concise synthetic answer."
        result = await agent.process_query("Explain research funding")
        assert result["answer"] == "A concise synthetic answer."
        assert result["success"] is True


class TestQueryPlanCacheIntegration:
    @pytest.mark.asyncio
    async def test_cache_checked_before_planning(self, agent, inference):
        agent.plan_cache = Mock()
        agent.plan_cache.get_cached_plan.return_value = {"hint": "synthetic-plan-marker"}
        await agent.process_query("Explain research funding", context="Prior context")
        agent.plan_cache.get_cached_plan.assert_called_once_with(
            "Explain research funding", "Prior context"
        )
        assert "synthetic-plan-marker" in str(inference.messages[-1])


class TestToolCount:
    def test_agent_has_tools(self):
        assert len(ToolAwareAgent().tools) == 42


class TestSpeculativeExecutorIntegration:
    @pytest.mark.asyncio
    async def test_speculative_executor_available(self, agent):
        executor = Mock()
        executor.start_speculative_execution = AsyncMock(return_value={})
        agent.speculative_executor = executor
        await agent.process_query("Explain research funding")
        executor.start_speculative_execution.assert_awaited_once()
        executor.cancel_unused_speculation.assert_called()


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_query(self, agent, inference):
        inference.answer = "Please provide a question."
        result = await agent.process_query("")
        assert result["answer"] == "Please provide a question."
        assert result["agent_error"] is None

    @pytest.mark.asyncio
    async def test_very_long_query(self, agent, inference, monkeypatch):
        long_query = "Find hydrogen " * 100
        condensed = LongQueryResult(
            original_query=long_query,
            processed_query="Find hydrogen funding",
            was_processed=True,
            query_length=len(long_query),
        )
        monkeypatch.setattr(
            "app.services.agents.tool_aware_agent.preprocess_long_query_async",
            AsyncMock(return_value=condensed),
        )
        result = await agent.process_query(long_query)
        assert result["success"] is True
        assert long_query in str(inference.messages[-1])
        assert "Find hydrogen funding" in str(inference.messages[-1])
        assert result["long_query_metadata"]["original_length"] == len(long_query)


class TestQualityAnalysisIntegration:
    def test_agent_has_quality_analyzer(self):
        agent = ToolAwareAgent()
        assert agent.quality_analyzer is not None
        assert agent.enable_quality_analysis is True

    def test_agent_quality_analyzer_can_be_disabled(self):
        agent = ToolAwareAgent(enable_quality_analysis=False)
        assert agent.enable_quality_analysis is False
        assert agent.quality_analyzer is None

    def test_analyze_response_quality_method_exists(self):
        assert callable(ToolAwareAgent()._analyze_response_quality)

    def test_analyze_response_quality_returns_dict(self, agent):
        result = agent._analyze_response_quality("What is Horizon Europe?", ANSWER, {})
        assert isinstance(result, dict)
        assert {"score", "category", "confidence"} <= result.keys()

    def test_analyze_response_quality_with_deflection(self, agent):
        result = agent._analyze_response_quality(
            "Tell me about HORIZON-CL5-2026-D3-01",
            "I could not find any information about this call.",
            {},
        )
        assert result["category"] == "deflection"
        assert result["deflection_phrases_found"]

    @pytest.mark.asyncio
    async def test_process_query_includes_quality_analysis(self, agent):
        result = await agent.process_query("What is Horizon Europe?")
        assert isinstance(result["quality_analysis"], dict)
        assert {"score", "category"} <= result["quality_analysis"].keys()

    def test_quality_analysis_handles_tool_results(self, agent):
        records = {"search_funding_calls_1_1": {"calls": [{"call_id": "HORIZON-CL5-2026-D3-01"}]}}
        result = agent._analyze_response_quality("Find hydrogen funding calls", ANSWER, records)
        assert result["score"] >= 50
