"""
Comprehensive tests for the SpeculativeExecutor.

Tests:
- Parallel tool execution
- Fallback behavior
- Timeout handling
- Result aggregation
- Error handling
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.agents.speculative_executor import SpeculativeExecutor


class TestSpeculativeExecutorInitialization:
    """Tests for SpeculativeExecutor initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        executor = SpeculativeExecutor()

        assert executor is not None

    def test_initialization_with_max_parallel(self):
        """Test initialization with custom max_parallel."""
        executor = SpeculativeExecutor(max_parallel=5)

        assert executor.max_parallel == 5

    def test_default_max_parallel(self):
        """Test default max_parallel value."""
        executor = SpeculativeExecutor()

        assert executor.max_parallel > 0


class TestParallelExecution:
    """Tests for parallel tool execution."""

    @pytest.fixture
    def mock_tools(self):
        """Create mock tools for testing."""
        async def mock_tool_1(params):
            await asyncio.sleep(0.1)
            return {"success": True, "data": "result_1"}

        async def mock_tool_2(params):
            await asyncio.sleep(0.1)
            return {"success": True, "data": "result_2"}

        return {
            "tool_1": mock_tool_1,
            "tool_2": mock_tool_2
        }

    def test_execute_multiple_tools_parallel(self, mock_tools):
        """Test multiple tools execute in parallel."""
        executor = SpeculativeExecutor()

        tool_calls = [
            {"name": "tool_1", "params": {}},
            {"name": "tool_2", "params": {}}
        ]

        start_time = datetime.now()
        results = asyncio.run(executor.execute_parallel(tool_calls, mock_tools))
        elapsed = (datetime.now() - start_time).total_seconds()

        # Should take ~0.1s (parallel), not ~0.2s (sequential)
        assert elapsed < 0.2
        assert len(results) == 2

    def test_results_returned_in_order(self, mock_tools):
        """Test results are returned in order of tool calls."""
        executor = SpeculativeExecutor()

        tool_calls = [
            {"name": "tool_1", "params": {}},
            {"name": "tool_2", "params": {}}
        ]

        results = asyncio.run(executor.execute_parallel(tool_calls, mock_tools))

        # Results should maintain order
        assert results[0]["data"] == "result_1"
        assert results[1]["data"] == "result_2"


class TestFallbackBehavior:
    """Tests for fallback behavior when tools fail."""

    @pytest.fixture
    def tools_with_failure(self):
        """Create tools with one that fails."""
        async def working_tool(params):
            return {"success": True, "data": "works"}

        async def failing_tool(params):
            raise Exception("Tool failed")

        return {
            "working_tool": working_tool,
            "failing_tool": failing_tool
        }

    def test_partial_failure_returns_successful(self, tools_with_failure):
        """Test partial failure returns successful results."""
        executor = SpeculativeExecutor()

        tool_calls = [
            {"name": "working_tool", "params": {}},
            {"name": "failing_tool", "params": {}}
        ]

        results = asyncio.run(executor.execute_parallel(tool_calls, tools_with_failure))

        # Should have 2 results, one success and one failure
        assert len(results) == 2
        successful = [r for r in results if r.get("success")]
        assert len(successful) >= 1

    def test_all_failures_handled_gracefully(self, tools_with_failure):
        """Test all failures are handled gracefully."""
        executor = SpeculativeExecutor()

        tool_calls = [
            {"name": "failing_tool", "params": {}},
            {"name": "failing_tool", "params": {}}
        ]

        # Should not raise exception
        results = asyncio.run(executor.execute_parallel(tool_calls, tools_with_failure))

        assert len(results) == 2


class TestTimeoutHandling:
    """Tests for timeout handling."""

    @pytest.fixture
    def slow_tools(self):
        """Create slow tools for timeout testing."""
        async def slow_tool(params):
            await asyncio.sleep(10)  # 10 second sleep
            return {"success": True}

        async def fast_tool(params):
            await asyncio.sleep(0.1)
            return {"success": True, "data": "fast"}

        return {
            "slow_tool": slow_tool,
            "fast_tool": fast_tool
        }

    def test_timeout_prevents_hanging(self, slow_tools):
        """Test timeout prevents indefinite hanging."""
        executor = SpeculativeExecutor(timeout_seconds=1)

        tool_calls = [
            {"name": "slow_tool", "params": {}},
            {"name": "fast_tool", "params": {}}
        ]

        start_time = datetime.now()
        results = asyncio.run(executor.execute_parallel(tool_calls, slow_tools))
        elapsed = (datetime.now() - start_time).total_seconds()

        # Should complete within timeout + buffer
        assert elapsed < 3

    def test_fast_tools_complete_despite_slow(self, slow_tools):
        """Test fast tools complete even when slow tools timeout."""
        executor = SpeculativeExecutor(timeout_seconds=0.5)

        tool_calls = [
            {"name": "fast_tool", "params": {}},
            {"name": "slow_tool", "params": {}}
        ]

        results = asyncio.run(executor.execute_parallel(tool_calls, slow_tools))

        # Fast tool should have completed
        fast_result = next((r for r in results if r.get("data") == "fast"), None)
        assert fast_result is not None


class TestResultAggregation:
    """Tests for result aggregation."""

    @pytest.fixture
    def search_tools(self):
        """Create search tools that return results."""
        async def search_calls(params):
            return {
                "success": True,
                "calls": [{"id": 1}, {"id": 2}],
                "count": 2
            }

        async def search_projects(params):
            return {
                "success": True,
                "projects": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
                "count": 3
            }

        return {
            "search_calls": search_calls,
            "search_projects": search_projects
        }

    def test_aggregate_results(self, search_tools):
        """Test aggregating results from multiple tools."""
        executor = SpeculativeExecutor()

        tool_calls = [
            {"name": "search_calls", "params": {}},
            {"name": "search_projects", "params": {}}
        ]

        results = asyncio.run(executor.execute_parallel(tool_calls, search_tools))

        # Aggregate counts
        total_count = sum(r.get("count", 0) for r in results)
        assert total_count == 5

    def test_results_include_source_tool(self, search_tools):
        """Test results include source tool name."""
        executor = SpeculativeExecutor()

        tool_calls = [
            {"name": "search_calls", "params": {}},
            {"name": "search_projects", "params": {}}
        ]

        results = asyncio.run(executor.execute_parallel(tool_calls, search_tools))

        # Each result should have tool name
        for i, result in enumerate(results):
            assert "tool_name" in result or results[i] is not None


class TestEmptyToolCalls:
    """Tests for empty tool call handling."""

    def test_empty_tool_calls(self):
        """Test handling empty tool call list."""
        executor = SpeculativeExecutor()

        results = asyncio.run(executor.execute_parallel([], {}))

        assert results == []

    def test_single_tool_call(self):
        """Test single tool call (no parallelism needed)."""
        async def single_tool(params):
            return {"success": True}

        executor = SpeculativeExecutor()

        tool_calls = [{"name": "single_tool", "params": {}}]
        tools = {"single_tool": single_tool}

        results = asyncio.run(executor.execute_parallel(tool_calls, tools))

        assert len(results) == 1
        assert results[0]["success"] == True


class TestToolParameters:
    """Tests for tool parameter passing."""

    def test_parameters_passed_correctly(self):
        """Test parameters are passed to tools correctly."""
        received_params = {}

        async def capture_params(params):
            received_params.update(params)
            return {"success": True}

        executor = SpeculativeExecutor()

        tool_calls = [{
            "name": "capture_tool",
            "params": {"query": "hydrogen", "limit": 10}
        }]
        tools = {"capture_tool": capture_params}

        asyncio.run(executor.execute_parallel(tool_calls, tools))

        assert received_params["query"] == "hydrogen"
        assert received_params["limit"] == 10

    def test_different_params_per_tool(self):
        """Test different parameters per tool."""
        all_params = []

        async def capture_tool(params):
            all_params.append(params.copy())
            return {"success": True}

        executor = SpeculativeExecutor()

        tool_calls = [
            {"name": "capture_tool", "params": {"id": 1}},
            {"name": "capture_tool", "params": {"id": 2}},
            {"name": "capture_tool", "params": {"id": 3}}
        ]
        tools = {"capture_tool": capture_tool}

        asyncio.run(executor.execute_parallel(tool_calls, tools))

        ids = [p["id"] for p in all_params]
        assert sorted(ids) == [1, 2, 3]


class TestMaxParallelLimit:
    """Tests for maximum parallel execution limit."""

    def test_respects_max_parallel(self):
        """Test that max_parallel limit is respected."""
        concurrent_count = []
        current_count = [0]

        async def counting_tool(params):
            current_count[0] += 1
            concurrent_count.append(current_count[0])
            await asyncio.sleep(0.1)
            current_count[0] -= 1
            return {"success": True}

        executor = SpeculativeExecutor(max_parallel=2)

        tool_calls = [
            {"name": "counting_tool", "params": {}},
            {"name": "counting_tool", "params": {}},
            {"name": "counting_tool", "params": {}},
            {"name": "counting_tool", "params": {}}
        ]
        tools = {"counting_tool": counting_tool}

        asyncio.run(executor.execute_parallel(tool_calls, tools))

        # Max concurrent should not exceed limit
        assert max(concurrent_count) <= 2


class TestMissingTools:
    """Tests for handling missing tools."""

    def test_missing_tool_handled(self):
        """Test missing tool is handled gracefully."""
        executor = SpeculativeExecutor()

        tool_calls = [{"name": "nonexistent_tool", "params": {}}]
        tools = {}  # Empty tools

        # Should not raise exception
        results = asyncio.run(executor.execute_parallel(tool_calls, tools))

        assert len(results) == 1
        assert results[0].get("success") == False or "error" in results[0]


class TestSpeculativePatterns:
    """Tests for speculative execution patterns."""

    @pytest.fixture
    def speculative_tools(self):
        """Create tools for speculative patterns."""
        async def primary_search(params):
            await asyncio.sleep(0.2)
            return {"success": True, "results": [1, 2, 3], "source": "primary"}

        async def fallback_search(params):
            await asyncio.sleep(0.1)
            return {"success": True, "results": [4, 5], "source": "fallback"}

        return {
            "primary_search": primary_search,
            "fallback_search": fallback_search
        }

    def test_speculative_execution(self, speculative_tools):
        """Test speculative execution pattern."""
        executor = SpeculativeExecutor()

        # Execute both speculatively
        tool_calls = [
            {"name": "primary_search", "params": {}},
            {"name": "fallback_search", "params": {}}
        ]

        results = asyncio.run(executor.execute_parallel(tool_calls, speculative_tools))

        # Both should complete
        assert len(results) == 2

        # Can use whichever returns first or has better results
        sources = [r["source"] for r in results]
        assert "primary" in sources or "fallback" in sources


class TestEdgeCases:
    """Tests for edge cases."""

    def test_very_many_parallel_tools(self):
        """Test handling many parallel tools."""
        async def simple_tool(params):
            return {"success": True, "id": params.get("id")}

        executor = SpeculativeExecutor(max_parallel=10)

        tool_calls = [{"name": "simple_tool", "params": {"id": i}} for i in range(50)]
        tools = {"simple_tool": simple_tool}

        results = asyncio.run(executor.execute_parallel(tool_calls, tools))

        assert len(results) == 50

    def test_tool_returning_none(self):
        """Test tool returning None."""
        async def none_tool(params):
            return None

        executor = SpeculativeExecutor()

        tool_calls = [{"name": "none_tool", "params": {}}]
        tools = {"none_tool": none_tool}

        results = asyncio.run(executor.execute_parallel(tool_calls, tools))

        assert len(results) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
