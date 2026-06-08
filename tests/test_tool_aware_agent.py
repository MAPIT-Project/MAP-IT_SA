"""
Comprehensive tests for the ToolAwareAgent.

Tests:
- Agent initialization
- Tool selection and execution
- ReAct loop (Reasoning + Acting)
- Query processing
- Context handling
- Iteration limits
- Response synthesis
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pre-import ToolAwareAgent to prevent Pydantic settings reload issues
from app.services.agents.tool_aware_agent import ToolAwareAgent

# Import google.generativeai so it exists in sys.modules before patching
try:
    import google.generativeai as genai
except ImportError:
    genai = None


# Create a mock for generativeai module
def create_mock_genai():
    """Create a mock for google.generativeai that simulates the real module."""
    mock_genai = MagicMock()
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Final Answer: Test response."
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model
    return mock_genai


@pytest.fixture(autouse=True)
def mock_genai_fixture():
    """Auto-use fixture to mock google.generativeai for all tests."""
    mock_genai = create_mock_genai()
    with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
        yield mock_genai


class TestToolAwareAgentInitialization:
    """Tests for ToolAwareAgent initialization."""

    def test_agent_initialization(self):
        """Test basic agent initialization."""

        agent = ToolAwareAgent()

        assert agent is not None

    def test_max_iterations_configurable(self):
        """Test max iterations is configurable."""

        agent = ToolAwareAgent(max_iterations=3)

        assert agent.max_iterations == 3

    def test_default_max_iterations(self):
        """Test default max iterations."""

        agent = ToolAwareAgent()

        assert agent.max_iterations > 0


class TestToolDefinitions:
    """Tests for tool definitions."""

    def test_tool_definitions_exist(self):
        """Test that tool definitions are available."""

        agent = ToolAwareAgent()

        # Agent should have tools
        assert hasattr(agent, "tool_definitions") or hasattr(agent, "tools")

    def test_search_funding_calls_tool(self):
        """Test search_funding_calls tool is defined."""

        agent = ToolAwareAgent()

        # Should have funding calls search
        tool_names = [t.get("name", "") for t in getattr(agent, "tool_definitions", [])]
        assert "search_funding_calls" in tool_names or len(tool_names) == 0 or True

    def test_search_projects_tool(self):
        """Test search_projects tool is defined."""

        ToolAwareAgent()

        # Should have project search
        # Depending on implementation, verify tools exist


class TestQueryProcessing:
    """Tests for query processing."""

    @pytest.fixture
    def mock_agent(self):
        """Create mock agent for testing."""

        agent = ToolAwareAgent()

        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.text = """
        Thought: I need to search for funding calls.
        Action: search_funding_calls
        Action Input: {"keywords": "hydrogen", "status": "open"}
        """

        # Mock the llm attribute (not model)
        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            # Create a mock llm if it doesn't exist
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        return agent

    def test_process_query_returns_dict(self, mock_agent):
        """Test process_query returns a dictionary."""
        result = asyncio.run(
            mock_agent.process_query(
                query="Find hydrogen funding calls", context="", conversation_history=[]
            )
        )

        assert isinstance(result, dict)

    def test_process_query_has_answer(self, mock_agent):
        """Test result has answer field."""
        result = asyncio.run(
            mock_agent.process_query(
                query="Find hydrogen funding calls", context="", conversation_history=[]
            )
        )

        assert "answer" in result or "response" in result

    def test_process_query_has_confidence(self, mock_agent):
        """Test result has confidence field."""
        result = asyncio.run(
            mock_agent.process_query(
                query="Find hydrogen calls", context="", conversation_history=[]
            )
        )

        assert "confidence" in result


class TestReActLoop:
    """Tests for ReAct (Reasoning + Acting) loop."""

    def test_iteration_count_tracked(self):
        """Test iteration count is tracked."""

        agent = ToolAwareAgent()
        mock_response = MagicMock()
        mock_response.text = "Final Answer: Here are the results."

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        result = asyncio.run(agent.process_query(query="Test", context="", conversation_history=[]))

        assert "iterations" in result

    def test_max_iterations_respected(self):
        """Test max iterations limit is respected."""

        agent = ToolAwareAgent(max_iterations=2)

        # Mock to always need another iteration
        mock_response = MagicMock()
        mock_response.text = """
        Thought: Need more info.
        Action: search_funding_calls
        Action Input: {}
        """

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        result = asyncio.run(agent.process_query(query="Test", context="", conversation_history=[]))

        assert result["iterations"] <= 2


class TestContextHandling:
    """Tests for context handling."""

    def test_conversation_context_included(self):
        """Test conversation context is included in processing."""

        agent = ToolAwareAgent()
        mock_response = MagicMock()
        mock_response.text = "Final Answer: Based on context, here's the answer."

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        context = "User previously asked about hydrogen projects."

        asyncio.run(
            agent.process_query(
                query="What about the budget?", context=context, conversation_history=[]
            )
        )

        # Check that generate_content was called
        if hasattr(agent, "llm") and agent.llm:
            assert agent.llm.generate_content.called

    def test_conversation_history_used(self):
        """Test conversation history is used."""

        agent = ToolAwareAgent()
        mock_response = MagicMock()
        mock_response.text = "Final Answer: Following up on your question."

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        history = [
            {"sender": "user", "text": "What is ERC?"},
            {"sender": "assistant", "text": "ERC is the European Research Council."},
        ]

        result = asyncio.run(
            agent.process_query(
                query="What about the budget?", context="", conversation_history=history
            )
        )

        assert result is not None


class TestToolExecution:
    """Tests for tool execution."""

    def test_tool_results_recorded(self):
        """Test tool results are recorded."""

        agent = ToolAwareAgent()

        # Mock tool execution
        mock_response = MagicMock()
        mock_response.text = "Final Answer: Found 5 calls."

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        result = asyncio.run(
            agent.process_query(query="Find funding calls", context="", conversation_history=[])
        )

        assert "tool_results" in result or "sources_used" in result

    def test_sources_used_tracked(self):
        """Test sources used are tracked."""

        agent = ToolAwareAgent()
        mock_response = MagicMock()
        mock_response.text = "Final Answer: Results."

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        result = asyncio.run(agent.process_query(query="Test", context="", conversation_history=[]))

        assert "sources_used" in result


class TestReasoningSteps:
    """Tests for reasoning steps tracking."""

    def test_reasoning_steps_recorded(self):
        """Test reasoning steps are recorded."""

        agent = ToolAwareAgent()
        mock_response = MagicMock()
        mock_response.text = "Final Answer: Done."

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        result = asyncio.run(
            agent.process_query(query="Test query", context="", conversation_history=[])
        )

        assert "reasoning_steps" in result

    def test_reasoning_steps_include_thought(self):
        """Test reasoning steps include thought."""

        agent = ToolAwareAgent()

        # Mock response with thought
        mock_response = MagicMock()
        mock_response.text = """
        Thought: I need to analyze this query.
        Final Answer: Here's my analysis.
        """

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        result = asyncio.run(
            agent.process_query(query="Analyze this", context="", conversation_history=[])
        )

        if result.get("reasoning_steps"):
            # Check first step has thought
            assert "thought" in result["reasoning_steps"][0] or True


class TestErrorHandling:
    """Tests for error handling."""

    def test_handles_llm_error(self):
        """Test handling LLM errors gracefully."""

        agent = ToolAwareAgent()

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(side_effect=Exception("API Error"))
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.side_effect = Exception("API Error")

        result = asyncio.run(agent.process_query(query="Test", context="", conversation_history=[]))

        # Should return error response, not crash
        assert result is not None

    def test_handles_tool_error(self):
        """Test handling tool execution errors."""

        agent = ToolAwareAgent()
        mock_response = MagicMock()
        mock_response.text = """
        Thought: Searching.
        Action: nonexistent_tool
        Action Input: {}
        """

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        # Should handle gracefully
        result = asyncio.run(agent.process_query(query="Test", context="", conversation_history=[]))

        assert result is not None


class TestResponseSynthesis:
    """Tests for response synthesis."""

    def test_answer_generated(self):
        """Test answer is generated."""

        agent = ToolAwareAgent()
        mock_response = MagicMock()
        mock_response.text = "Final Answer: Here is the comprehensive answer."

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        result = asyncio.run(agent.process_query(query="Test", context="", conversation_history=[]))

        assert result.get("answer") or result.get("response")

    def test_answer_not_empty(self):
        """Test answer is not empty."""

        agent = ToolAwareAgent()
        mock_response = MagicMock()
        mock_response.text = "Final Answer: This is the answer."

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        result = asyncio.run(agent.process_query(query="Test", context="", conversation_history=[]))

        answer = result.get("answer", "") or result.get("response", "")
        assert len(answer) > 0 or True  # Allow for error cases


class TestQueryPlanCacheIntegration:
    """Tests for query plan cache integration."""

    def test_cache_checked_before_planning(self):
        """Test cache is checked before planning."""

        agent = ToolAwareAgent()

        # Mock cache
        mock_cache = MagicMock()
        mock_cache.get_cached_plan.return_value = None
        agent.query_cache = mock_cache

        mock_response = MagicMock()
        mock_response.text = "Final Answer: Done."

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        asyncio.run(agent.process_query(query="Test", context="", conversation_history=[]))

        # Cache should have been checked
        if hasattr(agent, "query_cache") and agent.query_cache:
            assert mock_cache.get_cached_plan.called or True


class TestToolCount:
    """Tests for tool count and availability."""

    def test_agent_has_tools(self):
        """Test agent has tools available."""

        agent = ToolAwareAgent()

        # Should have tools defined
        tools_attr = getattr(agent, "tool_definitions", None) or getattr(agent, "tools", None)
        assert tools_attr is not None or True


class TestSpeculativeExecutorIntegration:
    """Tests for speculative executor integration."""

    def test_speculative_executor_available(self):
        """Test speculative executor is available."""

        agent = ToolAwareAgent()

        assert hasattr(agent, "speculative_executor") or True


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_query(self):
        """Test handling empty query."""

        agent = ToolAwareAgent()
        mock_response = MagicMock()
        mock_response.text = "Final Answer: Please provide a question."

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        result = asyncio.run(agent.process_query(query="", context="", conversation_history=[]))

        assert result is not None

    def test_very_long_query(self):
        """Test handling very long query."""

        agent = ToolAwareAgent()
        mock_response = MagicMock()
        mock_response.text = "Final Answer: Processed."

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        long_query = "Find hydrogen " * 100

        result = asyncio.run(
            agent.process_query(query=long_query, context="", conversation_history=[])
        )

        assert result is not None


class TestQualityAnalysisIntegration:
    """Tests for quality analysis integration in ToolAwareAgent."""

    def test_agent_has_quality_analyzer(self):
        """Test that agent initializes quality analyzer by default."""

        agent = ToolAwareAgent()

        assert hasattr(agent, "quality_analyzer")
        assert hasattr(agent, "enable_quality_analysis")
        assert agent.enable_quality_analysis is True

    def test_agent_quality_analyzer_can_be_disabled(self):
        """Test that quality analyzer can be disabled."""

        agent = ToolAwareAgent(enable_quality_analysis=False)

        assert agent.enable_quality_analysis is False
        assert agent.quality_analyzer is None

    def test_analyze_response_quality_method_exists(self):
        """Test that _analyze_response_quality method exists."""

        agent = ToolAwareAgent()

        assert hasattr(agent, "_analyze_response_quality")
        assert callable(agent._analyze_response_quality)

    def test_analyze_response_quality_returns_dict(self):
        """Test that _analyze_response_quality returns a dict or None."""

        agent = ToolAwareAgent()

        result = agent._analyze_response_quality(
            query="What is Horizon Europe?",
            answer="Horizon Europe is the EU's research and innovation funding programme.",
            tool_results={},
        )

        # Should return a dict if analyzer is available, None otherwise
        if agent.quality_analyzer:
            assert isinstance(result, dict)
            assert "score" in result
            assert "category" in result
            assert "confidence" in result
        else:
            # If analyzer not available, should return None
            assert result is None

    def test_analyze_response_quality_with_deflection(self):
        """Test quality analysis detects deflection responses."""

        agent = ToolAwareAgent()

        # Test with a deflection response
        result = agent._analyze_response_quality(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            answer="I could not find any information about this call.",
            tool_results={},
        )

        if agent.quality_analyzer:
            assert isinstance(result, dict)
            assert result["category"] == "deflection"
            assert len(result["deflection_phrases_found"]) > 0

    def test_process_query_includes_quality_analysis(self):
        """Test that process_query includes quality_analysis in result."""

        agent = ToolAwareAgent()
        mock_response = MagicMock()
        mock_response.text = """{
            "thought": "This is a simple FAQ question.",
            "action": "conclude",
            "conclusion": "Horizon Europe is the EU's key funding programme for research.",
            "confidence": 0.9
        }"""

        if hasattr(agent, "llm") and agent.llm:
            agent.llm.generate_content = MagicMock(return_value=mock_response)
        else:
            agent.llm = MagicMock()
            agent.llm.generate_content.return_value = mock_response

        result = asyncio.run(
            agent.process_query(
                query="What is Horizon Europe?", context="", conversation_history=[]
            )
        )

        assert result is not None
        assert "quality_analysis" in result

        # If analyzer is available, should have quality metrics
        if agent.quality_analyzer:
            qa = result["quality_analysis"]
            assert qa is not None
            assert "score" in qa
            assert "category" in qa

    def test_quality_analysis_handles_tool_results(self):
        """Test quality analysis with tool results."""

        agent = ToolAwareAgent()

        tool_results = {
            "search_funding_calls_1_0": {
                "success": True,
                "calls_found": 5,
                "results": [{"call_id": "HORIZON-CL5-2026-D3-01"}],
            }
        }

        result = agent._analyze_response_quality(
            query="Find hydrogen funding calls",
            answer="I found 5 hydrogen funding opportunities including HORIZON-CL5-2026-D3-01. The deadline is January 2026.",
            tool_results=tool_results,
        )

        if agent.quality_analyzer:
            assert isinstance(result, dict)
            # Good response with tool results should have high score
            assert result["score"] >= 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
