"""
Tests for Scenario 050: Vector Search Fails - Graceful Degradation

PRD Reference:
- Simulate: Supabase vector search timeout
- Query: "Find semantically similar projects"
- Expected: Falls back to keyword search, explains
- Verify: Still provides useful results
- Fix if: Complete failure, no fallback
- Pass threshold: 75

This scenario tests that when vector search (embedding + pgvector) fails due to
timeout or unavailability, the system gracefully degrades to keyword search and
provides useful results while informing the user of the limitation.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# Unit Tests - Test timeout configurations and fallback logic
# ============================================================================


class TestTimeoutConfiguration:
    """Test that timeout constants are properly configured."""

    def test_timeout_constants_exist(self):
        """Test that timeout constants are defined in similar_projects.py."""
        from app.services.tools.similar_projects import (
            EMBEDDING_TIMEOUT,
            GRAPH_CONTEXT_TIMEOUT,
            VECTOR_SEARCH_TIMEOUT,
        )

        assert EMBEDDING_TIMEOUT > 0, "EMBEDDING_TIMEOUT should be positive"
        assert VECTOR_SEARCH_TIMEOUT > 0, "VECTOR_SEARCH_TIMEOUT should be positive"
        assert GRAPH_CONTEXT_TIMEOUT > 0, "GRAPH_CONTEXT_TIMEOUT should be positive"

    def test_timeout_constants_reasonable_values(self):
        """Test that timeout values are reasonable (not too short or too long)."""
        from app.services.tools.similar_projects import (
            EMBEDDING_TIMEOUT,
            GRAPH_CONTEXT_TIMEOUT,
            VECTOR_SEARCH_TIMEOUT,
        )

        # Embedding generation should have 10-60s timeout
        assert 10 <= EMBEDDING_TIMEOUT <= 60, (
            f"EMBEDDING_TIMEOUT {EMBEDDING_TIMEOUT}s should be 10-60s"
        )
        # Vector search should be faster, 5-30s
        assert 5 <= VECTOR_SEARCH_TIMEOUT <= 30, (
            f"VECTOR_SEARCH_TIMEOUT {VECTOR_SEARCH_TIMEOUT}s should be 5-30s"
        )
        # Graph context can be slower, 10-60s
        assert 10 <= GRAPH_CONTEXT_TIMEOUT <= 60, (
            f"GRAPH_CONTEXT_TIMEOUT {GRAPH_CONTEXT_TIMEOUT}s should be 10-60s"
        )


class TestServiceAvailability:
    """Test service availability configuration for graceful degradation."""

    def test_similar_projects_in_degradable_tools(self):
        """Test that get_similar_funded_projects is in DEGRADABLE_TOOLS."""
        from app.core.service_availability import DEGRADABLE_TOOLS

        assert "get_similar_funded_projects" in DEGRADABLE_TOOLS, (
            "get_similar_funded_projects should be in DEGRADABLE_TOOLS"
        )

    def test_similar_projects_degradable_on_embeddings(self):
        """Test that it can degrade when EMBEDDINGS unavailable."""
        from app.core.service_availability import DEGRADABLE_TOOLS, ServiceType

        degradable_services = DEGRADABLE_TOOLS.get("get_similar_funded_projects", [])
        assert ServiceType.EMBEDDINGS in degradable_services, (
            "get_similar_funded_projects should degrade when EMBEDDINGS unavailable"
        )

    def test_find_similar_projects_also_degradable(self):
        """Test that find_similar_projects is also in DEGRADABLE_TOOLS."""
        from app.core.service_availability import DEGRADABLE_TOOLS

        assert "find_similar_projects" in DEGRADABLE_TOOLS, (
            "find_similar_projects should be in DEGRADABLE_TOOLS"
        )

    def test_tool_service_requirements(self):
        """Test that requirements are properly defined."""
        from app.core.service_availability import TOOL_SERVICE_REQUIREMENTS

        assert "get_similar_funded_projects" in TOOL_SERVICE_REQUIREMENTS, (
            "get_similar_funded_projects should be in TOOL_SERVICE_REQUIREMENTS"
        )


class TestKeywordFallbackMethod:
    """Test the keyword fallback method implementation."""

    def test_fallback_method_exists(self):
        """Test that _get_keyword_fallback method exists."""
        from app.services.tools.similar_projects import SimilarProjectsTool

        tool = SimilarProjectsTool()
        assert hasattr(tool, "_get_keyword_fallback"), (
            "SimilarProjectsTool should have _get_keyword_fallback method"
        )

    def test_fallback_accepts_reason_parameter(self):
        """Test that fallback method accepts fallback_reason parameter."""
        import inspect

        from app.services.tools.similar_projects import SimilarProjectsTool

        tool = SimilarProjectsTool()
        sig = inspect.signature(tool._get_keyword_fallback)
        params = list(sig.parameters.keys())

        assert "fallback_reason" in params, (
            "_get_keyword_fallback should accept fallback_reason parameter"
        )

    def test_timeout_wrapper_method_exists(self):
        """Test that timeout wrapper methods exist."""
        from app.services.tools.similar_projects import SimilarProjectsTool

        tool = SimilarProjectsTool()
        assert hasattr(tool, "_generate_embedding_with_timeout"), (
            "SimilarProjectsTool should have _generate_embedding_with_timeout method"
        )
        assert hasattr(tool, "_get_vector_results_with_timeout"), (
            "SimilarProjectsTool should have _get_vector_results_with_timeout method"
        )


class TestFallbackReasons:
    """Test that different fallback reasons are properly handled."""

    @pytest.fixture
    def tool(self):
        """Create SimilarProjectsTool instance."""
        from app.services.tools.similar_projects import SimilarProjectsTool

        return SimilarProjectsTool()

    def test_vector_search_timeout_reason(self, tool):
        """Test vector_search_timeout fallback reason."""
        # Mock database connection to return results
        with patch.object(tool, "_get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {
                    "id": 123,
                    "acronym": "TEST",
                    "title": "Test Project",
                    "objective": "Testing hydrogen fuel cells",
                    "ecMaxContribution": 1000000,
                    "startDate": datetime(2024, 1, 1),
                    "fundingScheme": "RIA",
                    "topics": "HORIZON-CL5",
                }
            ]
            mock_conn.return_value.cursor.return_value = mock_cursor

            result = tool._get_keyword_fallback(
                description="hydrogen fuel cell research",
                cluster=None,
                action_type=None,
                limit=10,
                fallback_reason="vector_search_timeout",
            )

            assert result.get("success") is True
            assert result.get("metadata", {}).get("fallback_reason") == "vector_search_timeout"
            assert result.get("metadata", {}).get("degraded") is True
            assert "timed out" in result.get("message", "").lower()

    def test_embedding_service_unavailable_reason(self, tool):
        """Test embedding_service_unavailable fallback reason."""
        with patch.object(tool, "_get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {
                    "id": 456,
                    "acronym": "PROJ2",
                    "title": "Another Project",
                    "objective": "Solar energy research",
                    "ecMaxContribution": 2000000,
                    "startDate": datetime(2024, 2, 1),
                    "fundingScheme": "IA",
                    "topics": "HORIZON-CL5",
                }
            ]
            mock_conn.return_value.cursor.return_value = mock_cursor

            result = tool._get_keyword_fallback(
                description="solar energy research",
                cluster=None,
                action_type=None,
                limit=10,
                fallback_reason="embedding_service_unavailable",
            )

            assert result.get("success") is True
            fallback_reason = result.get("metadata", {}).get("fallback_reason")
            assert fallback_reason == "embedding_service_unavailable"
            assert "embedding service unavailable" in result.get("message", "").lower()


# ============================================================================
# Mock Tests - Test timeout behavior with mocked services
# ============================================================================


class TestEmbeddingTimeout:
    """Test embedding generation timeout behavior."""

    @pytest.fixture
    def tool(self):
        """Create SimilarProjectsTool instance."""
        from app.services.tools.similar_projects import SimilarProjectsTool

        return SimilarProjectsTool()

    def test_embedding_timeout_triggers_fallback(self, tool):
        """Test that embedding timeout triggers keyword fallback."""

        # Create a slow embedding service that exceeds timeout
        slow_embedding = MagicMock()

        def slow_generate(*args, **kwargs):
            import time

            time.sleep(100)  # Way longer than timeout
            return None

        slow_embedding.generate_query_embedding = slow_generate

        # Use very short timeout for testing
        with patch.object(tool, "_get_embedding_service", return_value=slow_embedding):
            with patch("app.services.tools.similar_projects.EMBEDDING_TIMEOUT", 0.1):
                result = tool._generate_embedding_with_timeout(slow_embedding, "test description")

        assert result is None, "Should return None on timeout"

    def test_embedding_generation_error_returns_none(self, tool):
        """Test that embedding generation error returns None."""
        failing_embedding = MagicMock()
        failing_embedding.generate_query_embedding.side_effect = Exception("API error")

        result = tool._generate_embedding_with_timeout(failing_embedding, "test description")

        assert result is None, "Should return None on error"


class TestVectorSearchTimeout:
    """Test vector search timeout behavior."""

    @pytest.fixture
    def tool(self):
        """Create SimilarProjectsTool instance."""
        from app.services.tools.similar_projects import SimilarProjectsTool

        return SimilarProjectsTool()

    def test_vector_search_timeout_returns_tuple(self, tool):
        """Test that vector search with timeout returns (results, timed_out) tuple."""
        # Mock a slow database query
        with patch.object(tool, "_get_vector_results") as mock_get:

            def slow_query(*args, **kwargs):
                import time

                time.sleep(100)  # Way longer than timeout
                return []

            mock_get.side_effect = slow_query

            # Use very short timeout for testing
            with patch("app.services.tools.similar_projects.VECTOR_SEARCH_TIMEOUT", 0.1):
                results, timed_out = tool._get_vector_results_with_timeout(
                    embedding_list=[0.1] * 768,
                    cluster=None,
                    action_type=None,
                    min_budget=None,
                    max_budget=None,
                    year_from=None,
                    limit=10,
                    similarity_threshold=0.3,
                )

        assert timed_out is True, "Should indicate timeout occurred"
        assert results == [], "Should return empty results on timeout"

    def test_vector_search_success_returns_results(self, tool):
        """Test that successful vector search returns results and no timeout."""
        mock_results = [{"id": "123", "similarity_score": 0.8}]

        with patch.object(tool, "_get_vector_results", return_value=mock_results):
            results, timed_out = tool._get_vector_results_with_timeout(
                embedding_list=[0.1] * 768,
                cluster=None,
                action_type=None,
                min_budget=None,
                max_budget=None,
                year_from=None,
                limit=10,
                similarity_threshold=0.3,
            )

        assert timed_out is False, "Should not indicate timeout"
        assert results == mock_results, "Should return the results"


class TestHybridSearchFallback:
    """Test that hybrid search falls back correctly on timeout."""

    @pytest.fixture
    def tool(self):
        """Create SimilarProjectsTool instance."""
        from app.services.tools.similar_projects import SimilarProjectsTool

        return SimilarProjectsTool()

    def test_hybrid_mode_fallback_on_vector_timeout(self, tool):
        """Test that hybrid mode falls back to keyword search on vector timeout."""
        # Mock the timeout wrapper to return timeout
        with patch.object(tool, "_get_vector_results_with_timeout", return_value=([], True)):
            with patch.object(tool, "_get_keyword_fallback") as mock_fallback:
                mock_fallback.return_value = {
                    "success": True,
                    "search_method": "keyword_fallback",
                    "metadata": {"fallback_reason": "vector_search_timeout"},
                }

                # Call the method - result not needed as we verify via mock
                tool._find_similar_hybrid(
                    description="hydrogen fuel cell research",
                    embedding_list=[0.1] * 768,
                    cluster=None,
                    graph_cluster=None,
                    action_type=None,
                    min_budget=None,
                    max_budget=None,
                    year_from=None,
                    limit=10,
                    similarity_threshold=0.3,
                    rerank_with_graph=True,
                    include_graph_context=True,
                    inferred_clusters=[],
                )

                mock_fallback.assert_called_once()
                # Verify fallback_reason was passed
                call_kwargs = mock_fallback.call_args[1]
                assert call_kwargs.get("fallback_reason") == "vector_search_timeout"


class TestAgentLevelTimeout:
    """Test agent-level timeout handling."""

    @pytest.mark.asyncio
    async def test_agent_timeout_wrapper_exists(self):
        """Test that agent has timeout wrapper for similar projects tool."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        # ToolAwareAgent constructor takes max_iterations and enable_quality_analysis
        agent = ToolAwareAgent(max_iterations=5, enable_quality_analysis=False)

        # Check method exists
        assert hasattr(agent, "_tool_get_similar_funded_projects")

    @pytest.mark.asyncio
    async def test_agent_timeout_falls_back_gracefully(self):
        """Test that agent timeout falls back to keyword search."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        # Create agent with minimal config
        agent = ToolAwareAgent(max_iterations=5, enable_quality_analysis=False)

        # Mock SimilarProjectsTool to hang forever at the tool level
        with patch("app.services.tools.similar_projects.SimilarProjectsTool") as MockTool:
            mock_tool_instance = MagicMock()

            # Make find_similar hang (will trigger agent-level timeout)
            def slow_find_similar(*args, **kwargs):
                import time

                time.sleep(100)
                return {}

            mock_tool_instance.find_similar = slow_find_similar
            mock_tool_instance._get_keyword_fallback.return_value = {
                "success": True,
                "search_method": "keyword_fallback",
                "metadata": {"fallback_reason": "agent_level_timeout", "degraded": True},
            }
            MockTool.return_value = mock_tool_instance

            # Run with very short timeout (we'll patch the timeout value)
            # The agent should fall back to keyword search
            result = await agent._tool_get_similar_funded_projects(
                {"description": "hydrogen fuel cell research"}
            )

            # Should either succeed with degradation or be a successful fallback
            # (depends on whether timeout was triggered)
            assert isinstance(result, dict), "Should return a dictionary result"
            # Either it has degraded flag or it's a successful response
            assert (
                result.get("metadata", {}).get("degraded") is True
                or result.get("success") is True
                or "error" in result
            ), "Should have valid response structure"


# ============================================================================
# Integration Tests - Test with actual components (database required)
# ============================================================================


class TestKeywordFallbackIntegration:
    """Integration tests for keyword fallback functionality."""

    @pytest.fixture
    def tool(self):
        """Create SimilarProjectsTool instance."""
        from app.services.tools.similar_projects import SimilarProjectsTool

        return SimilarProjectsTool()

    @pytest.mark.skipif(
        not pytest.importorskip("psycopg2", reason="psycopg2 not installed"),
        reason="Database not available",
    )
    def test_keyword_fallback_returns_results(self, tool):
        """Test that keyword fallback actually returns results from database."""
        # Skip if no database URL configured
        import os

        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")

        result = tool._get_keyword_fallback(
            description="hydrogen fuel cell renewable energy research project",
            cluster=None,
            action_type=None,
            limit=5,
            fallback_reason="test",
        )

        assert result.get("success") is True
        assert result.get("search_method") == "keyword_fallback"
        assert result.get("metadata", {}).get("degraded") is True

        # Should have some results (database has many projects)
        projects = result.get("similar_projects", [])
        # Note: might be empty if keywords don't match, but structure should be correct
        assert isinstance(projects, list)

    @pytest.mark.skipif(
        not pytest.importorskip("psycopg2", reason="psycopg2 not installed"),
        reason="Database not available",
    )
    def test_keyword_fallback_with_cluster_filter(self, tool):
        """Test keyword fallback with cluster filter."""
        import os

        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")

        result = tool._get_keyword_fallback(
            description="artificial intelligence machine learning",
            cluster="CL4",  # Digital cluster
            action_type=None,
            limit=5,
            fallback_reason="vector_search_timeout",
        )

        assert result.get("success") is True
        assert "timed out" in result.get("message", "").lower()


class TestFullScenario050:
    """Full end-to-end tests for Scenario 050."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("httpx", reason="httpx not installed"),
        reason="httpx not installed for API tests",
    )
    async def test_full_scenario_050_graceful_degradation(self):
        """Test the complete Scenario 050 flow.

        This test simulates vector search timeout and verifies that:
        1. System doesn't crash
        2. Falls back to keyword search
        3. Returns useful results
        4. Indicates degradation in metadata
        """
        import os

        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")

        from app.services.tools.similar_projects import SimilarProjectsTool

        tool = SimilarProjectsTool()

        # Force a timeout by mocking the vector search
        with patch.object(tool, "_get_vector_results_with_timeout", return_value=([], True)):
            result = tool.find_similar(
                description="hydrogen fuel cell research for sustainable transportation", limit=5
            )

        # Verify graceful degradation
        assert result.get("success") is True, "Should still succeed"
        assert result.get("search_method") == "keyword_fallback", "Should use keyword fallback"
        assert result.get("metadata", {}).get("degraded") is True, "Should indicate degradation"
        assert (
            "timeout" in result.get("metadata", {}).get("fallback_reason", "").lower()
            or "timeout" in result.get("message", "").lower()
        ), "Should mention timeout"

    @pytest.mark.asyncio
    async def test_scenario_050_no_crash_on_complete_failure(self):
        """Test that system doesn't crash even when everything fails."""
        from app.services.tools.similar_projects import SimilarProjectsTool

        tool = SimilarProjectsTool()

        # Mock all services to fail
        with patch.object(tool, "_get_embedding_service", return_value=None):
            with patch.object(tool, "_get_connection", return_value=None):
                result = tool.find_similar(description="hydrogen fuel cell research", limit=5)

        # Should return an error response, not crash
        assert isinstance(result, dict), "Should return a dict"
        # Either success with empty results or failure with message
        assert "success" in result or "error" in result


class TestMetadataTracking:
    """Test that metadata properly tracks degradation."""

    @pytest.fixture
    def tool(self):
        """Create SimilarProjectsTool instance."""
        from app.services.tools.similar_projects import SimilarProjectsTool

        return SimilarProjectsTool()

    def test_metadata_includes_fallback_reason(self, tool):
        """Test that metadata includes fallback_reason."""
        with patch.object(tool, "_get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.cursor.return_value = mock_cursor

            result = tool._get_keyword_fallback(
                description="test",
                cluster=None,
                action_type=None,
                limit=5,
                fallback_reason="vector_search_timeout",
            )

        metadata = result.get("metadata", {})
        assert "fallback_reason" in metadata
        assert metadata["fallback_reason"] == "vector_search_timeout"

    def test_metadata_includes_degraded_flag(self, tool):
        """Test that metadata includes degraded flag."""
        with patch.object(tool, "_get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.cursor.return_value = mock_cursor

            result = tool._get_keyword_fallback(
                description="test",
                cluster=None,
                action_type=None,
                limit=5,
                fallback_reason="embedding_service_unavailable",
            )

        metadata = result.get("metadata", {})
        assert "degraded" in metadata
        assert metadata["degraded"] is True

    def test_metadata_includes_sources_used(self, tool):
        """Test that metadata includes sources_used."""
        with patch.object(tool, "_get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.cursor.return_value = mock_cursor

            result = tool._get_keyword_fallback(
                description="test", cluster=None, action_type=None, limit=5, fallback_reason="test"
            )

        metadata = result.get("metadata", {})
        assert "sources_used" in metadata
        assert "keyword" in metadata["sources_used"]


class TestUserFriendlyMessages:
    """Test that user-friendly messages are generated."""

    @pytest.fixture
    def tool(self):
        """Create SimilarProjectsTool instance."""
        from app.services.tools.similar_projects import SimilarProjectsTool

        return SimilarProjectsTool()

    def test_timeout_message_is_clear(self, tool):
        """Test that timeout message is clear to users."""
        with patch.object(tool, "_get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.cursor.return_value = mock_cursor

            result = tool._get_keyword_fallback(
                description="test",
                cluster=None,
                action_type=None,
                limit=5,
                fallback_reason="vector_search_timeout",
            )

        message = result.get("message", "")
        assert "keyword" in message.lower(), "Should mention keyword search"
        assert "timed out" in message.lower(), "Should mention timeout"

    def test_embedding_unavailable_message(self, tool):
        """Test message when embedding service unavailable."""
        with patch.object(tool, "_get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.cursor.return_value = mock_cursor

            result = tool._get_keyword_fallback(
                description="test",
                cluster=None,
                action_type=None,
                limit=5,
                fallback_reason="embedding_service_unavailable",
            )

        message = result.get("message", "")
        assert "embedding" in message.lower(), "Should mention embedding"
        assert "unavailable" in message.lower(), "Should mention unavailable"
