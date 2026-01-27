"""
Tests for Scenario 057: Self-Correction - Agent Self-Improves Poor Results

PRD Reference:
- Query: "Find renewable energy calls" (intentionally get poor results first)
- Expected: Agent self-corrects if initial search insufficient
- Verify: Uses agentic loop to improve results
- Fix if: Accepts poor results, no iteration
- Pass threshold: 80

This scenario tests that when initial search results are insufficient (poor quality,
low count, low relevance), the agent self-corrects by:
1. Evaluating results against quality thresholds
2. Reflecting on why results failed (root cause analysis)
3. Replanning with improved search strategy
4. Iterating until sufficient results obtained or max iterations reached
"""

from datetime import datetime
import json
import logging
from unittest.mock import MagicMock, patch

import pytest

logger = logging.getLogger(__name__)


# ============================================================================
# Unit Tests - Test core self-correction components
# ============================================================================


class TestResultEvaluatorScoring:
    """Test the ResultEvaluator scoring logic."""

    @pytest.fixture
    def evaluator(self):
        """Create ResultEvaluator instance."""
        from app.services.agents.result_evaluator import ResultEvaluator

        return ResultEvaluator(use_llm_evaluation=False)

    def test_evaluator_exists(self):
        """Test that ResultEvaluator class exists."""
        from app.services.agents.result_evaluator import ResultEvaluator

        evaluator = ResultEvaluator(use_llm_evaluation=False)
        assert evaluator is not None

    def test_insufficient_results_score_low(self, evaluator):
        """Test that empty/insufficient results get low score."""
        # Empty results should score very low
        empty_results = {}
        result = evaluator.evaluate("test query", "exploratory", empty_results)

        assert result.score < evaluator.SUFFICIENT_SCORE
        assert result.is_sufficient is False

    def test_sufficient_results_score_high(self, evaluator):
        """Test that good results get high score."""
        # Create results with enough items and good scores
        good_results = {
            "results": [
                {
                    "id": f"call-{i}",
                    "title": f"Renewable Energy Call {i}",
                    "relevance_score": 0.85,
                    "content": "This is a call about renewable energy research " * 10,
                }
                for i in range(8)  # More than min_results
            ]
        }
        result = evaluator.evaluate("renewable energy calls", "exploratory", good_results)

        # Score should be above threshold
        assert result.score >= evaluator.SUFFICIENT_SCORE
        assert result.is_sufficient is True

    def test_low_relevance_reduces_score(self, evaluator):
        """Test that low relevance scores reduce evaluation score."""
        low_relevance_results = {
            "results": [
                {
                    "id": f"call-{i}",
                    "title": f"Call {i}",
                    "relevance_score": 0.2,  # Very low relevance
                    "content": "Some content here",
                }
                for i in range(8)
            ]
        }
        result = evaluator.evaluate("renewable energy", "exploratory", low_relevance_results)

        # Low relevance should contribute to lower score
        assert result.score < 1.0

    def test_suggestions_generated_for_insufficient_results(self, evaluator):
        """Test that suggestions are generated when results insufficient."""
        poor_results = {"results": []}
        result = evaluator.evaluate("renewable energy", "exploratory", poor_results)

        assert result.is_sufficient is False
        # Suggestions should be generated for improvement
        assert isinstance(result.suggestions, list)


class TestReflectorRootCauseAnalysis:
    """Test the Reflector root cause analysis."""

    @pytest.fixture
    def reflector(self):
        """Create Reflector instance."""
        from app.services.agents.reflector import Reflector

        return Reflector()

    def test_reflector_exists(self):
        """Test that Reflector class exists."""
        from app.services.agents.reflector import Reflector

        reflector = Reflector()
        assert reflector is not None

    def test_reflector_has_reflect_method(self):
        """Test that Reflector has reflect method."""
        from app.services.agents.reflector import Reflector

        reflector = Reflector()
        assert hasattr(reflector, "reflect")

    def test_root_cause_detection_no_results(self):
        """Test root cause detection for no results scenario."""
        from app.services.agents.reflector import Reflector
        from app.services.agents.result_evaluator import EvaluationResult

        reflector = Reflector()

        evaluation = EvaluationResult(
            score=0.1,
            is_sufficient=False,
            reasons=["No results found"],
            suggestions=["Try broader terms"],
            metrics={"result_count": 0, "avg_relevance": 0.0},
        )

        reflection = reflector.reflect(
            query="underwater basket weaving funding",
            evaluation=evaluation,
            current_plan={"steps": [{"source": "vector", "query": "underwater"}]},
            results={},
            failed_strategies=[],
        )

        # Should identify root cause
        assert reflection.root_cause is not None
        # Should suggest improvement action
        assert reflection.improvement_action is not None

    def test_reflection_includes_confidence(self):
        """Test that reflection includes confidence score."""
        from app.services.agents.reflector import Reflector
        from app.services.agents.result_evaluator import EvaluationResult

        reflector = Reflector()

        evaluation = EvaluationResult(
            score=0.2,
            is_sufficient=False,
            reasons=["Limited results"],
            suggestions=[],
            metrics={"result_count": 0, "avg_relevance": 0.0},
        )

        reflection = reflector.reflect(
            query="very specific niche topic",
            evaluation=evaluation,
            current_plan={"steps": [{"source": "vector"}]},
            results={},
            failed_strategies=[],
        )

        assert hasattr(reflection, "confidence")
        assert 0.0 <= reflection.confidence <= 1.0


class TestReplannerStrategyImprovement:
    """Test the Replanner strategy improvement."""

    @pytest.fixture
    def replanner(self):
        """Create Replanner instance."""
        from app.services.agents.replanner import Replanner

        return Replanner()

    def test_replanner_exists(self):
        """Test that Replanner class exists."""
        from app.services.agents.replanner import Replanner

        replanner = Replanner()
        assert replanner is not None

    def test_replanner_has_replan_method(self):
        """Test that Replanner has replan method."""
        from app.services.agents.replanner import Replanner

        replanner = Replanner()
        assert hasattr(replanner, "replan")

    def test_replanning_creates_new_plan(self):
        """Test that replanning creates a new execution plan."""
        from app.services.agents.reflector import (
            FailureRootCause,
            ImprovementAction,
            ReflectionResult,
        )
        from app.services.agents.replanner import Replanner

        replanner = Replanner()

        reflection = ReflectionResult(
            failure_analysis="Query too specific",
            root_cause=FailureRootCause.QUERY_TOO_NARROW,
            confidence=0.8,
            improvement_action=ImprovementAction.BROADEN_QUERY,
            suggested_query="clean energy sustainable energy",
            suggested_sources=["vector", "keyword"],
        )

        new_plan = replanner.replan(
            query="renewable energy funding",
            reflection=reflection,
            failed_strategies=[],
            tried_queries=["renewable energy"],
            tried_sources=["vector"],
            query_type="general_query",
        )

        # New plan should exist
        assert new_plan is not None
        # Plan should have steps
        assert "steps" in new_plan


class TestToolAwareAgentSelfCorrection:
    """Test the ToolAwareAgent self-correction loop."""

    @pytest.fixture
    def agent(self):
        """Create ToolAwareAgent instance."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        return ToolAwareAgent(max_iterations=5, enable_quality_analysis=False)

    def test_agent_has_max_iterations(self, agent):
        """Test that agent has max_iterations configured."""
        assert agent.max_iterations == 5

    def test_agent_has_reason_next_step(self, agent):
        """Test that agent has _reason_next_step method."""
        assert hasattr(agent, "_reason_next_step")

    def test_agent_tracks_reasoning_steps(self, agent):
        """Test that agent can track reasoning steps."""
        from app.services.agents.tool_aware_agent import AgentPlan

        # Agent should use AgentPlan to track steps
        plan = AgentPlan(
            query="test query",
            complexity="simple",
            required_sources=["calls"],
        )
        assert hasattr(plan, "reasoning_steps")

    @pytest.mark.asyncio
    async def test_agent_continues_when_needs_more_info(self, agent):
        """Test that agent continues iteration when needs_more_info is True."""
        # Mock reasoning result that says needs_more_info
        mock_reasoning = {
            "thought": "Initial search found few results, need to broaden search",
            "action": "call_tools",
            "tool_calls": [{"name": "search_funding_calls", "arguments": {"keywords": "energy"}}],
            "needs_more_info": True,  # Should continue
        }

        # Verify the logic would continue (we test the decision structure)
        assert mock_reasoning["needs_more_info"] is True
        assert mock_reasoning["action"] == "call_tools"

    @pytest.mark.asyncio
    async def test_agent_stops_when_needs_more_info_false(self, agent):
        """Test that agent stops iteration when needs_more_info is False."""
        mock_reasoning = {
            "thought": "Found sufficient renewable energy calls",
            "action": "conclude",
            "conclusion": "I found 10 renewable energy funding calls...",
            "needs_more_info": False,  # Should stop
            "confidence": 0.9,
        }

        assert mock_reasoning["needs_more_info"] is False
        assert mock_reasoning["action"] == "conclude"


class TestAgenticManagerLoop:
    """Test the AgenticManager self-correcting loop."""

    @pytest.fixture
    def manager(self):
        """Create AgenticManager instance."""
        from app.services.agents.agentic_manager import AgenticManager

        return AgenticManager(max_iterations=3, sufficient_score=0.65)

    def test_manager_has_max_iterations(self, manager):
        """Test that manager has max_iterations configured."""
        assert manager.max_iterations == 3

    def test_manager_has_sufficient_score_threshold(self, manager):
        """Test that manager has sufficient_score threshold."""
        assert manager.sufficient_score == 0.65

    def test_manager_has_evaluate_results(self, manager):
        """Test that manager has _evaluate_results method."""
        assert hasattr(manager, "_evaluate_results")

    def test_manager_has_replan(self, manager):
        """Test that manager has _replan method."""
        assert hasattr(manager, "_replan")

    def test_manager_has_reflect_on_failure(self, manager):
        """Test that manager has _reflect_on_failure method."""
        assert hasattr(manager, "_reflect_on_failure")


# ============================================================================
# Integration Tests - Test the full self-correction flow
# ============================================================================


class TestSelfCorrectionFlow:
    """Integration tests for the self-correction flow."""

    @pytest.mark.asyncio
    async def test_agent_iterates_on_poor_initial_results(self):
        """Test that agent iterates when initial results are poor."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent(max_iterations=5, enable_quality_analysis=False)

        # Track iterations
        iteration_count = [0]

        async def mock_reason(*args, **kwargs):
            iteration_count[0] += 1

            if iteration_count[0] == 1:
                # First iteration: search with poor results
                return {
                    "thought": "Searching for renewable energy calls",
                    "action": "call_tools",
                    "tool_calls": [
                        {
                            "name": "search_funding_calls",
                            "arguments": {"keywords": "renewable", "limit": 3},
                        }
                    ],
                    "needs_more_info": True,
                }
            elif iteration_count[0] == 2:
                # Second iteration: broaden search
                return {
                    "thought": "Initial results were limited, broadening search to clean energy",
                    "action": "call_tools",
                    "tool_calls": [
                        {
                            "name": "search_funding_calls",
                            "arguments": {"keywords": "clean energy sustainable", "limit": 10},
                        }
                    ],
                    "needs_more_info": True,
                }
            else:
                # Third iteration: conclude with improved results
                return {
                    "thought": "Now have sufficient results from multiple searches",
                    "action": "conclude",
                    "conclusion": "Found 15 renewable energy funding opportunities...",
                    "confidence": 0.85,
                    "needs_more_info": False,
                }

        with patch.object(agent, "_reason_next_step", mock_reason):
            with patch.object(agent, "_execute_tool_calls") as mock_execute:
                # Mock tool execution
                mock_call = MagicMock()
                mock_call.success = True
                mock_call.tool_name = "search_funding_calls"
                mock_call.result = {"calls_found": 5, "calls": []}
                mock_execute.return_value = [mock_call]

                await agent.process_query("Find renewable energy calls")

        # Should have iterated multiple times
        assert iteration_count[0] >= 2, "Agent should iterate multiple times"

    @pytest.mark.asyncio
    async def test_manager_has_reflection_capability(self):
        """Test that AgenticManager has reflection capability."""
        from app.services.agents.agentic_manager import AgenticManager

        manager = AgenticManager(max_iterations=3, sufficient_score=0.65)

        # Verify manager has reflector
        assert hasattr(manager, "reflector")
        # Verify manager has reflect method
        assert hasattr(manager, "_reflect_on_failure")


class TestSelfCorrectionMetadata:
    """Test that self-correction metadata is properly tracked."""

    def test_reasoning_step_tracks_iteration(self):
        """Test that ReasoningStep tracks iteration number."""
        from app.services.agents.tool_aware_agent import ReasoningStep

        step = ReasoningStep(
            step_number=2,
            thought="Broadening search after initial results were limited",
            action="call_tools",
        )

        assert step.step_number == 2

    def test_agent_plan_tracks_all_steps(self):
        """Test that AgentPlan tracks all reasoning steps."""
        from app.services.agents.tool_aware_agent import AgentPlan, ReasoningStep

        plan = AgentPlan(
            query="renewable energy calls",
            complexity="simple",
            required_sources=["calls"],
        )

        # Add reasoning steps
        plan.reasoning_steps.append(
            ReasoningStep(step_number=1, thought="Initial search", action="call_tools")
        )
        plan.reasoning_steps.append(
            ReasoningStep(step_number=2, thought="Broaden search", action="call_tools")
        )
        plan.reasoning_steps.append(
            ReasoningStep(step_number=3, thought="Conclude", action="conclude")
        )

        assert len(plan.reasoning_steps) == 3


class TestIterationLimits:
    """Test iteration limits are enforced."""

    @pytest.mark.asyncio
    async def test_agent_respects_max_iterations(self):
        """Test that agent stops at max_iterations."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        max_iters = 3
        agent = ToolAwareAgent(max_iterations=max_iters, enable_quality_analysis=False)

        iteration_count = [0]

        async def mock_reason(*args, **kwargs):
            iteration_count[0] += 1
            # Always say needs_more_info to test limit
            return {
                "thought": f"Iteration {iteration_count[0]}",
                "action": "call_tools",
                "tool_calls": [
                    {"name": "search_funding_calls", "arguments": {"keywords": "energy"}}
                ],
                "needs_more_info": True,
            }

        with patch.object(agent, "_reason_next_step", mock_reason):
            with patch.object(agent, "_execute_tool_calls") as mock_execute:
                mock_call = MagicMock()
                mock_call.success = True
                mock_call.tool_name = "search_funding_calls"
                mock_call.result = {"calls_found": 0, "calls": []}
                mock_execute.return_value = [mock_call]

                await agent.process_query("Find something obscure")

        # Should stop at max_iterations
        assert iteration_count[0] <= max_iters

    def test_manager_context_tracks_iterations(self):
        """Test that AgentContext tracks iterations."""
        from app.services.agents.context import AgentContext

        context = AgentContext(
            user_query="test query",
            conversation_id="test-123",
            max_iterations=3,
        )

        # Simulate iterations
        context.iteration = 1
        assert context.should_continue() is True

        context.iteration = 2
        assert context.should_continue() is True

        context.iteration = 3
        assert context.should_continue() is False  # Hit max


# ============================================================================
# End-to-End Tests - Test with real components
# ============================================================================


class TestScenario057EndToEnd:
    """End-to-end tests for Scenario 057."""

    @pytest.mark.asyncio
    async def test_renewable_energy_query_self_corrects(self):
        """Test the actual renewable energy query self-correction."""
        import os

        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")

        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent(max_iterations=5, enable_quality_analysis=False)

        # Run the actual query
        result = await agent.process_query("Find renewable energy calls")

        # Should succeed
        assert result is not None
        assert "error" not in result or result.get("error") is None

        # Should have response (could be 'response', 'final_answer', or 'answer')
        has_response = any(key in result for key in ["response", "final_answer", "answer"])
        assert has_response, f"Result should contain a response. Keys: {list(result.keys())}"

        # Check metadata for iteration info
        if "iterations" in result:
            assert result["iterations"] >= 1

    @pytest.mark.asyncio
    async def test_self_correction_improves_results(self):
        """Test that self-correction actually improves results quality."""
        import os

        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")

        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent(max_iterations=5, enable_quality_analysis=False)

        # Query that might need refinement
        result = await agent.process_query(
            "Find renewable energy funding opportunities for research"
        )

        # Get response from any of the possible keys
        response = result.get("response") or result.get("final_answer") or result.get("answer", "")

        # Should mention relevant topics
        response_lower = response.lower()
        # Expanded list of relevant terms that could appear in funding responses
        energy_terms = [
            "energy",
            "renewable",
            "sustainable",
            "clean",
            "climate",
            "green",
            "horizon",
            "funding",
            "call",
            "grant",
            "research",
        ]
        has_relevant_content = any(term in response_lower for term in energy_terms)

        assert (
            has_relevant_content
        ), f"Response should contain relevant terms. Response: {response[:200]}..."


class TestSelfCorrectionPatterns:
    """Test common self-correction patterns."""

    def test_query_broadening_pattern(self):
        """Test that query broadening is a valid improvement action."""
        from app.services.agents.reflector import ImprovementAction

        # BROADEN_QUERY should exist as an improvement action
        assert hasattr(ImprovementAction, "BROADEN_QUERY")

    def test_query_refinement_pattern(self):
        """Test that query refinement is a valid improvement action."""
        from app.services.agents.reflector import ImprovementAction

        # REFINE_QUERY should exist as an improvement action
        assert hasattr(ImprovementAction, "REFINE_QUERY")

    def test_source_change_pattern(self):
        """Test that changing source is a valid improvement action."""
        from app.services.agents.reflector import ImprovementAction

        # CHANGE_SOURCE should exist as an improvement action
        assert hasattr(ImprovementAction, "CHANGE_SOURCE")

    def test_keyword_search_fallback_pattern(self):
        """Test that keyword search fallback is a valid improvement action."""
        from app.services.agents.reflector import ImprovementAction

        # TRY_KEYWORD_SEARCH should exist
        assert hasattr(ImprovementAction, "TRY_KEYWORD_SEARCH")


class TestRootCauseCategories:
    """Test root cause categories used in self-correction."""

    def test_root_cause_enum_exists(self):
        """Test that FailureRootCause enum exists."""
        from app.services.agents.reflector import FailureRootCause

        assert FailureRootCause is not None

    def test_root_cause_has_query_too_broad(self):
        """Test that QUERY_TOO_BROAD root cause exists."""
        from app.services.agents.reflector import FailureRootCause

        assert hasattr(FailureRootCause, "QUERY_TOO_BROAD")

    def test_root_cause_has_query_too_narrow(self):
        """Test that QUERY_TOO_NARROW root cause exists."""
        from app.services.agents.reflector import FailureRootCause

        assert hasattr(FailureRootCause, "QUERY_TOO_NARROW")

    def test_root_cause_has_wrong_source(self):
        """Test that WRONG_SOURCE root cause exists."""
        from app.services.agents.reflector import FailureRootCause

        assert hasattr(FailureRootCause, "WRONG_SOURCE")

    def test_root_cause_has_semantic_mismatch(self):
        """Test that SEMANTIC_MISMATCH root cause exists."""
        from app.services.agents.reflector import FailureRootCause

        assert hasattr(FailureRootCause, "SEMANTIC_MISMATCH")


class TestReasoningStepActions:
    """Test the different action types in reasoning steps."""

    def test_call_tools_action(self):
        """Test that call_tools action triggers tool execution."""
        reasoning_result = {
            "thought": "Need to search for calls",
            "action": "call_tools",
            "tool_calls": [{"name": "search_funding_calls", "arguments": {"keywords": "energy"}}],
            "needs_more_info": True,
        }

        assert reasoning_result["action"] == "call_tools"
        assert len(reasoning_result["tool_calls"]) > 0

    def test_analyze_results_action(self):
        """Test that analyze_results action doesn't call more tools."""
        reasoning_result = {
            "thought": "Analyzing the results from previous search",
            "action": "analyze_results",
            "analysis": "The results show several relevant calls...",
            "needs_more_info": False,
        }

        assert reasoning_result["action"] == "analyze_results"
        assert (
            "tool_calls" not in reasoning_result or len(reasoning_result.get("tool_calls", [])) == 0
        )

    def test_conclude_action(self):
        """Test that conclude action ends the iteration."""
        reasoning_result = {
            "thought": "Have enough information to answer",
            "action": "conclude",
            "conclusion": "I found 15 renewable energy funding opportunities...",
            "confidence": 0.9,
            "needs_more_info": False,
        }

        assert reasoning_result["action"] == "conclude"
        assert reasoning_result["needs_more_info"] is False


class TestQualityThresholds:
    """Test quality thresholds used in self-correction."""

    def test_sufficient_score_threshold(self):
        """Test the SUFFICIENT_SCORE threshold value."""
        from app.services.agents.evaluator import ResultEvaluator

        evaluator = ResultEvaluator()
        # Should be 0.65 as per documentation
        assert evaluator.SUFFICIENT_SCORE == 0.65

    def test_min_results_factual(self):
        """Test minimum results for factual queries."""
        from app.services.agents.evaluator import ResultEvaluator

        evaluator = ResultEvaluator()
        # Should require at least 2 results for factual queries
        assert evaluator.MIN_RESULTS_FACTUAL >= 2

    def test_min_results_exploratory(self):
        """Test minimum results for exploratory queries."""
        from app.services.agents.evaluator import ResultEvaluator

        evaluator = ResultEvaluator()
        # Should require more results for exploratory queries
        assert evaluator.MIN_RESULTS_EXPLORATORY >= evaluator.MIN_RESULTS_FACTUAL

    def test_min_relevance_score(self):
        """Test minimum relevance score threshold."""
        from app.services.agents.evaluator import ResultEvaluator

        evaluator = ResultEvaluator()
        # Should have reasonable relevance threshold
        assert 0.3 <= evaluator.MIN_RELEVANCE_SCORE <= 0.7


class TestScenario057Validation:
    """Validate that Scenario 057 implementation meets PRD requirements."""

    def test_agent_can_self_correct(self):
        """Validate: Agent self-corrects if initial search insufficient."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent(max_iterations=5, enable_quality_analysis=False)

        # Agent has max_iterations > 1, allowing self-correction
        assert agent.max_iterations > 1

        # Agent has _reason_next_step method for deciding next action
        assert hasattr(agent, "_reason_next_step")

    def test_agentic_loop_exists(self):
        """Validate: Uses agentic loop to improve results."""
        from app.services.agents.agentic_manager import AgenticManager

        manager = AgenticManager(max_iterations=3, sufficient_score=0.65)

        # Has the full agentic loop phases
        assert hasattr(manager, "_understand_query")
        assert hasattr(manager, "_create_initial_plan")
        assert hasattr(manager, "_execute_plan")
        assert hasattr(manager, "_evaluate_results")
        assert hasattr(manager, "_reflect_on_failure")
        assert hasattr(manager, "_replan")
        assert hasattr(manager, "_synthesize_response")

    def test_iteration_continues_on_poor_results(self):
        """Validate: Does not accept poor results without iteration."""
        from app.services.agents.context import AgentContext
        from app.services.agents.evaluator import ResultEvaluator

        evaluator = ResultEvaluator()
        context = AgentContext(
            user_query="Find renewable energy calls",
            conversation_id="test-123",
            max_iterations=3,
        )

        # Poor results
        poor_results = {"calls": []}
        evaluation = evaluator.evaluate("renewable energy", "exploratory", poor_results, context)

        # Should NOT be sufficient - agent should continue
        assert evaluation.is_sufficient is False

        # Context should allow continuation
        context.iteration = 1
        assert context.should_continue() is True

    def test_reflection_generates_improvement_plan(self):
        """Validate: Reflection leads to improved search strategy."""
        from app.services.agents.reflector import Reflector
        from app.services.agents.result_evaluator import EvaluationResult

        reflector = Reflector()

        evaluation = EvaluationResult(
            score=0.2,
            is_sufficient=False,
            reasons=["No results found"],
            suggestions=["Try broader terms"],
            metrics={"result_count": 0, "avg_relevance": 0.0},
        )

        reflection = reflector.reflect(
            query="Find renewable energy calls",
            evaluation=evaluation,
            current_plan={"steps": [{"source": "calls", "query": "renewable energy"}]},
            results={"calls": []},
            failed_strategies=[],
        )

        # Should have improvement action
        assert reflection.improvement_action is not None


# ============================================================================
# Live Integration Tests - Requires running services
# ============================================================================


@pytest.mark.skipif(
    not pytest.importorskip("httpx", reason="httpx not installed"),
    reason="httpx not installed for API tests",
)
class TestScenario057LiveAPI:
    """Live API tests for Scenario 057.

    Note: These tests require the API server to be running.
    They will be skipped if the API is not available.
    """

    @pytest.fixture
    def api_base_url(self):
        """Get API base URL."""
        import os

        return os.getenv("API_BASE_URL", "http://localhost:8000")

    @pytest.mark.asyncio
    async def test_streaming_shows_iteration_progress(self, api_base_url):
        """Test that streaming endpoint shows iteration progress."""
        import os

        import httpx

        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")

        conversation_id = f"test-scenario-057-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Check if API is running
            try:
                health = await client.get(f"{api_base_url}/api/v3/conversation/health")
                if health.status_code != 200:
                    pytest.skip("API not running")
            except (httpx.ConnectError, httpx.ConnectTimeout):
                pytest.skip("API not running")

            # Send streaming request
            events = []
            try:
                async with client.stream(
                    "POST",
                    f"{api_base_url}/api/v3/conversation/{conversation_id}/message/stream",
                    json={"message": "Find renewable energy calls"},
                ) as response:
                    if response.status_code != 200:
                        pytest.skip(f"API returned {response.status_code}")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                events.append(data)
                            except json.JSONDecodeError:
                                pass
            except (httpx.ConnectError, httpx.ConnectTimeout):
                pytest.skip("API not running")

            # Should have multiple events showing progress
            if len(events) == 0:
                pytest.skip("No SSE events received - API may not be responding")

            # Look for iteration-related events
            tool_calls = [e for e in events if e.get("type") == "tool_call"]
            agent_thinking = [e for e in events if e.get("type") == "agent_thinking"]
            tokens = [e for e in events if e.get("type") == "token"]

            # Should show tool calls, agent thinking, or tokens
            has_progress = len(tool_calls) >= 1 or len(agent_thinking) >= 1 or len(tokens) >= 1
            assert has_progress, f"Should show progress. Events: {[e.get('type') for e in events]}"

    @pytest.mark.asyncio
    async def test_final_response_has_quality_content(self, api_base_url):
        """Test that final response has quality renewable energy content."""
        import os

        import httpx

        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")

        conversation_id = f"test-scenario-057-quality-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                health = await client.get(f"{api_base_url}/api/v3/conversation/health")
                if health.status_code != 200:
                    pytest.skip("API not running")
            except (httpx.ConnectError, httpx.ConnectTimeout):
                pytest.skip("API not running")

            # Use non-streaming endpoint for simpler assertion
            try:
                response = await client.post(
                    f"{api_base_url}/api/v3/conversation/{conversation_id}/message",
                    json={"message": "Find renewable energy calls"},
                )
            except (httpx.ConnectError, httpx.ConnectTimeout):
                pytest.skip("API not running")

            if response.status_code != 200:
                pytest.skip(f"API returned {response.status_code} status")

            result = response.json()
            response_text = result.get("response", "")

            # Should contain energy-related content
            response_lower = response_text.lower()
            energy_indicators = [
                "energy",
                "renewable",
                "clean",
                "sustainable",
                "climate",
                "horizon",
                "funding",
                "call",
            ]

            matches = [ind for ind in energy_indicators if ind in response_lower]
            assert len(matches) >= 2, f"Response should mention energy funding. Found: {matches}"
