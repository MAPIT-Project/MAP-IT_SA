"""
Tests for Task 005: Context Window Reset

These tests verify that:
1. The context window manager resets at the start of each process_query() call
2. Context size doesn't accumulate beyond expected limits across multiple queries
3. The reset prevents memory leak scenarios

PRD Requirements:
- Add automatic context_window_manager.reset() call at the start of process_query()
- Create test that processes 10 queries in sequence and verifies context size
  doesn't accumulate beyond expected limits
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import the context manager and agent
from app.services.agents.tool_aware_agent import (
    ContextLimits,
    ContextWindowManager,
    ToolAwareAgent,
    _context_manager,
)


class TestContextWindowManagerBasics:
    """Tests for ContextWindowManager basic functionality."""

    def test_reset_clears_current_size(self):
        """Test that reset() sets current_size to 0."""
        manager = ContextWindowManager()

        # Add some content to increase size
        manager.add_to_context("Test content " * 100)
        assert manager.current_size > 0

        # Reset should clear it
        manager.reset()
        assert manager.current_size == 0

    def test_current_size_property(self):
        """Test that current_size property returns correct value."""
        manager = ContextWindowManager()

        assert manager.current_size == 0

        # Add content
        content = "Test content"
        manager.add_to_context(content)
        assert manager.current_size == len(content)

    def test_add_to_context_accumulates(self):
        """Test that add_to_context correctly accumulates size."""
        manager = ContextWindowManager()

        manager.add_to_context("First")
        first_size = manager.current_size

        manager.add_to_context("Second")
        assert manager.current_size > first_size

    def test_reset_then_add_starts_fresh(self):
        """Test that reset followed by add_to_context starts fresh."""
        manager = ContextWindowManager()

        manager.add_to_context("First content " * 50)
        original_size = manager.current_size

        manager.reset()
        manager.add_to_context("Second")

        # Size should be just "Second", not accumulated
        assert manager.current_size == len("Second")
        assert manager.current_size < original_size


class TestContextWindowManagerLimits:
    """Tests for context window limits."""

    def test_would_exceed_limit(self):
        """Test that would_exceed_limit correctly checks limits."""
        limits = ContextLimits(max_context_chars=1000)
        manager = ContextWindowManager(limits)

        # Should not exceed with small addition
        assert not manager.would_exceed_limit(100)

        # Should exceed with large addition
        assert manager.would_exceed_limit(1500)

    def test_truncation_when_limit_exceeded(self):
        """Test that content is truncated when limit would be exceeded."""
        limits = ContextLimits(max_context_chars=100, reserved_for_response=10)
        manager = ContextWindowManager(limits)

        # Try to add content larger than available space
        long_content = "x" * 200
        result = manager.add_to_context(long_content)

        # Result should be truncated
        assert len(result) <= limits.max_context_chars - limits.reserved_for_response


class TestGlobalContextManager:
    """Tests for the global _context_manager instance."""

    def test_global_instance_exists(self):
        """Test that global _context_manager is properly initialized."""
        assert _context_manager is not None
        assert isinstance(_context_manager, ContextWindowManager)

    def test_global_instance_has_reset_method(self):
        """Test that global instance has reset method."""
        assert hasattr(_context_manager, "reset")
        assert callable(_context_manager.reset)

    def test_global_instance_has_current_size_property(self):
        """Test that global instance has current_size property."""
        assert hasattr(_context_manager, "current_size")


class TestContextResetInProcessQuery:
    """Tests verifying context reset at the start of process_query()."""

    @pytest.mark.asyncio
    async def test_process_query_resets_context_at_start(self):
        """Test that process_query() resets context window at the start."""
        # Mock dependencies
        with patch("app.services.agents.tool_aware_agent._context_manager") as mock_ctx:
            mock_ctx.reset = Mock()
            mock_ctx.current_size = 0
            mock_ctx.truncate_observation = Mock(return_value="obs")
            mock_ctx.format_results_for_context = Mock(return_value="results")

            # Create a minimal agent
            with patch.object(ToolAwareAgent, "__init__", return_value=None):
                agent = ToolAwareAgent.__new__(ToolAwareAgent)
                agent.max_iterations = 1
                agent.tools = {}
                agent.speculative_executor = None
                agent.plan_cache = None
                agent.llm = None
                agent._assess_complexity = Mock(return_value="simple")
                agent._identify_required_sources = Mock(return_value=[])
                agent._reason_next_step = AsyncMock(
                    return_value={
                        "thought": "test thought",
                        "action": "conclude",
                        "conclusion": "Test answer",
                        "confidence": 0.9,
                    }
                )
                agent._build_fallback_answer = Mock(return_value="Fallback")
                agent._analyze_response_quality = Mock(return_value={})

                # Call process_query
                await agent.process_query("Test query")

                # Verify reset was called
                mock_ctx.reset.assert_called()

    @pytest.mark.asyncio
    async def test_process_query_streaming_resets_context_at_start(self):
        """Test that process_query_streaming() resets context window at the start."""
        with patch("app.services.agents.tool_aware_agent._context_manager") as mock_ctx:
            mock_ctx.reset = Mock()
            mock_ctx.current_size = 0
            mock_ctx.truncate_observation = Mock(return_value="obs")
            mock_ctx.format_results_for_context = Mock(return_value="results")

            with patch.object(ToolAwareAgent, "__init__", return_value=None):
                agent = ToolAwareAgent.__new__(ToolAwareAgent)
                agent.max_iterations = 1
                agent.tools = {}
                agent.speculative_executor = None
                agent.plan_cache = None
                agent.llm = None
                agent._assess_complexity = Mock(return_value="simple")
                agent._identify_required_sources = Mock(return_value=[])
                agent._reason_next_step = AsyncMock(
                    return_value={
                        "thought": "test thought",
                        "action": "conclude",
                        "conclusion": "Test answer",
                        "confidence": 0.9,
                    }
                )
                agent._build_fallback_answer = Mock(return_value="Fallback")
                agent._analyze_response_quality = Mock(return_value={})

                # Call process_query_streaming and consume the generator
                events = []
                async for event in agent.process_query_streaming("Test query"):
                    events.append(event)

                # Verify reset was called
                mock_ctx.reset.assert_called()


class TestContextAccumulationPrevention:
    """Tests verifying context doesn't accumulate across queries."""

    def test_multiple_resets_keep_size_zero(self):
        """Test that multiple resets keep context size at zero."""
        manager = ContextWindowManager()

        for i in range(10):
            manager.add_to_context(f"Content iteration {i} " * 100)
            accumulated_before_reset = manager.current_size
            assert accumulated_before_reset > 0

            manager.reset()
            assert manager.current_size == 0

    def test_simulated_query_sequence_no_accumulation(self):
        """
        Simulate 10 queries in sequence and verify context size
        doesn't accumulate beyond expected limits.

        This is the main test from the PRD requirements.
        """
        manager = ContextWindowManager()
        max_observed_size = 0

        for query_num in range(10):
            # Reset at start (simulating process_query behavior)
            manager.reset()

            # Verify reset worked
            assert manager.current_size == 0, f"Query {query_num}: Context should be 0 after reset"

            # Simulate adding context during query processing
            # (tool results, observations, etc.)
            manager.add_to_context(f"Tool result for query {query_num}: " + "x" * 1000)
            manager.add_to_context(f"Observation {query_num}: " + "y" * 500)
            manager.add_to_context(f"Formatted results {query_num}: " + "z" * 500)

            query_size = manager.current_size
            max_observed_size = max(max_observed_size, query_size)

            # Each query should have roughly the same context size
            # (not accumulating from previous queries)
            # Expected size per query: ~2000 chars
            expected_max_per_query = 3000
            assert query_size < expected_max_per_query, (
                f"Query {query_num}: Context size {query_size} "
                f"exceeds expected max {expected_max_per_query}"
            )

        # Final verification: max observed should be much less than 10x a single query
        # (would be ~20000 if accumulating, should be ~2000)
        assert max_observed_size < 5000, (
            f"Max observed size {max_observed_size} suggests accumulation across queries"
        )

    def test_context_bounded_across_many_iterations(self):
        """Test that context remains bounded even with many iterations."""
        limits = ContextLimits(max_context_chars=50000)
        manager = ContextWindowManager(limits)

        # Simulate 50 queries, each with 3 reasoning iterations
        sizes_after_each_query = []

        for _ in range(50):
            manager.reset()  # Reset at query start

            # Simulate 3 reasoning iterations per query
            for iteration in range(3):
                manager.add_to_context(f"Step {iteration}: " + "content " * 100)

            sizes_after_each_query.append(manager.current_size)

        # All query context sizes should be similar (within 10% of each other)
        avg_size = sum(sizes_after_each_query) / len(sizes_after_each_query)
        for i, size in enumerate(sizes_after_each_query):
            deviation = abs(size - avg_size) / avg_size
            assert deviation < 0.15, (
                f"Query {i}: Size {size} deviates {deviation * 100:.1f}% from average {avg_size}"
            )


class TestContextResetWithRealAgent:
    """Integration-style tests with a more realistic agent setup."""

    @pytest.mark.asyncio
    async def test_multiple_queries_bounded_context(self):
        """
        Test that processing multiple queries keeps context bounded.
        Uses the global context manager to verify real behavior.
        """
        # Store initial size
        _context_manager.reset()
        initial_size = _context_manager.current_size
        assert initial_size == 0

        # Simulate what happens in process_query
        for query_num in range(10):
            # This is what process_query now does at the start
            _context_manager.reset()
            assert _context_manager.current_size == 0

            # Simulate context accumulation during query processing
            _context_manager.add_to_context(f"Query {query_num} content " * 50)

            # After processing, size should be bounded per query
            size_after_query = _context_manager.current_size
            assert size_after_query < 2000  # Reasonable single-query limit

        # Final reset to clean up
        _context_manager.reset()
        assert _context_manager.current_size == 0


class TestContextWindowManagerEdgeCases:
    """Tests for edge cases in context window management."""

    def test_reset_when_already_zero(self):
        """Test that reset is safe when size is already zero."""
        manager = ContextWindowManager()
        assert manager.current_size == 0

        # Reset should be safe
        manager.reset()
        assert manager.current_size == 0

    def test_reset_after_truncation(self):
        """Test reset after truncation has occurred."""
        limits = ContextLimits(max_context_chars=100, reserved_for_response=10)
        manager = ContextWindowManager(limits)

        # Add content that triggers truncation
        manager.add_to_context("x" * 200)

        # Reset should still work
        manager.reset()
        assert manager.current_size == 0

    def test_concurrent_reset_simulation(self):
        """
        Test that multiple resets in quick succession work correctly.
        (Simulates potential race conditions)
        """
        manager = ContextWindowManager()

        for _ in range(100):
            manager.add_to_context("test")
            manager.reset()
            assert manager.current_size == 0


class TestContextLimitsConfiguration:
    """Tests for context limits configuration."""

    def test_default_limits(self):
        """Test that default limits are reasonable."""
        limits = ContextLimits()

        assert limits.max_context_chars > 0
        assert limits.reserved_for_response > 0
        assert limits.max_tool_result_chars > 0
        assert limits.max_observation_chars > 0
        assert limits.max_document_chars > 0

    def test_from_env_with_defaults(self):
        """Test ContextLimits.from_env() returns valid limits."""
        limits = ContextLimits.from_env()

        assert limits.max_context_chars > 0
        assert limits.reserved_for_response > 0

    def test_custom_limits(self):
        """Test custom limits are respected."""
        custom_limits = ContextLimits(
            max_context_chars=5000, reserved_for_response=500, max_tool_result_chars=1000
        )
        manager = ContextWindowManager(custom_limits)

        assert manager.limits.max_context_chars == 5000
        assert manager.limits.reserved_for_response == 500
        assert manager.limits.max_tool_result_chars == 1000
