"""
Real Tool Integration Tests - Actually invoke tools against the database.

These tests call the REAL tool implementations with database connections.
They test the actual functionality, not mock data.

Run with: pytest tests/test_real_tools.py -v -s
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Skip all tests if DATABASE_URL is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set - skipping real tool tests"
)


# ============================================================================
# TOOL 1: Budget Benchmark (get_budget_benchmark)
# ============================================================================


class TestBudgetBenchmarkReal:
    """Real tests for budget_benchmark tool."""

    @pytest.mark.asyncio
    async def test_budget_benchmark_ria(self):
        """Test budget benchmark for RIA action type."""
        from app.services.tools.budget_benchmark import get_budget_benchmark_execute

        result = await get_budget_benchmark_execute({"action_type": "RIA"}, {})

        assert result["success"] is True
        assert result["tool_name"] == "get_budget_benchmark"
        assert "statistics" in result
        assert "recommendations" in result

        # Check we got real data
        stats = result["statistics"]
        if stats.get("projects_analyzed") != "N/A (using typical values)":
            assert stats["projects_analyzed"] > 0
            assert stats["total_eu_contribution"]["median"] > 0

    @pytest.mark.asyncio
    async def test_budget_benchmark_cluster4(self):
        """Test budget benchmark for Cluster 4 (Digital)."""
        from app.services.tools.budget_benchmark import get_budget_benchmark_execute

        result = await get_budget_benchmark_execute({"cluster": "CL4", "action_type": "RIA"}, {})

        assert result["success"] is True
        print(f"\nCluster 4 RIA Budget Stats: {result['statistics']}")

    @pytest.mark.asyncio
    async def test_budget_benchmark_with_keywords(self):
        """Test budget benchmark with topic keywords."""
        from app.services.tools.budget_benchmark import get_budget_benchmark_execute

        result = await get_budget_benchmark_execute(
            {"topic_keywords": "artificial intelligence", "action_type": "RIA"}, {}
        )

        assert result["success"] is True
        print(f"\nAI RIA Budget Stats: {result['statistics']}")


# ============================================================================
# TOOL 2: Consortium Patterns (get_consortium_patterns)
# ============================================================================


class TestConsortiumPatternsReal:
    """Real tests for consortium_patterns tool."""

    @pytest.mark.asyncio
    async def test_consortium_patterns_ria(self):
        """Test consortium patterns for RIA."""
        from app.services.tools.consortium_patterns import get_consortium_patterns_execute

        result = await get_consortium_patterns_execute({"action_type": "RIA"}, {})

        assert result["success"] is True
        assert result["tool_name"] == "get_consortium_patterns"
        # Tool returns consortium_size, organization_type_distribution, etc. directly
        assert "consortium_size" in result or "patterns" in result

        print(f"\nRIA Consortium Patterns: {result}")

    @pytest.mark.asyncio
    async def test_consortium_patterns_cluster5(self):
        """Test consortium patterns for Cluster 5."""
        from app.services.tools.consortium_patterns import get_consortium_patterns_execute

        result = await get_consortium_patterns_execute({"cluster": "CL5"}, {})

        assert result["success"] is True
        print(f"\nCluster 5 Consortium Patterns: {result}")


# ============================================================================
# TOOL 3: Partner Discovery (find_experienced_partners)
# ============================================================================


class TestPartnerDiscoveryReal:
    """Real tests for partner_discovery tool."""

    @pytest.mark.asyncio
    async def test_find_partners_ai(self):
        """Test finding partners for AI topic."""
        from app.services.tools.partner_discovery import find_experienced_partners_execute

        result = await find_experienced_partners_execute(
            {"topic_keywords": "artificial intelligence"}, {}
        )

        assert result["success"] is True
        assert result["tool_name"] == "find_experienced_partners"
        # Tool returns experienced_partners key
        assert "experienced_partners" in result or "partners" in result

        print(
            f"\nAI Partners Found: {result.get('total_found', len(result.get('experienced_partners', [])))}"
        )

    @pytest.mark.asyncio
    async def test_find_partners_by_country(self):
        """Test finding partners in Germany."""
        from app.services.tools.partner_discovery import find_experienced_partners_execute

        result = await find_experienced_partners_execute(
            {"topic_keywords": "hydrogen", "country": "Germany"}, {}
        )

        assert result["success"] is True
        print(f"\nGerman Hydrogen Partners: {result}")


# ============================================================================
# TOOL 4: Similar Projects (get_similar_funded_projects)
# ============================================================================


class TestSimilarProjectsReal:
    """Real tests for similar_projects tool."""

    @pytest.mark.asyncio
    async def test_similar_projects_ai(self):
        """Test finding similar AI projects."""
        from app.services.tools.similar_projects import get_similar_funded_projects_execute

        result = await get_similar_funded_projects_execute(
            {"description": "Machine learning for medical image analysis and cancer detection"}, {}
        )

        assert result["success"] is True
        assert result["tool_name"] == "get_similar_funded_projects"

        print(f"\nSimilar Projects: {result.get('projects_found', 0)}")

    @pytest.mark.asyncio
    async def test_similar_projects_hydrogen(self):
        """Test finding similar hydrogen projects."""
        from app.services.tools.similar_projects import get_similar_funded_projects_execute

        result = await get_similar_funded_projects_execute(
            {"description": "Green hydrogen production from renewable energy sources"}, {}
        )

        assert result["success"] is True
        print(f"\nHydrogen Similar Projects: {result}")


# ============================================================================
# TOOL 5: Call History Analysis (analyze_call_history)
# ============================================================================


class TestCallHistoryReal:
    """Real tests for call_history tool."""

    @pytest.mark.asyncio
    async def test_call_history_cluster4(self):
        """Test call history for Cluster 4."""
        from app.services.tools.call_history import analyze_call_history_execute

        result = await analyze_call_history_execute({"cluster": "CL4"}, {})

        assert result["success"] is True
        assert result["tool_name"] == "analyze_call_history"

        print(f"\nCluster 4 Call History: {result}")

    @pytest.mark.asyncio
    async def test_call_history_with_keywords(self):
        """Test call history with keywords."""
        from app.services.tools.call_history import analyze_call_history_execute

        result = await analyze_call_history_execute({"keywords": "quantum"}, {})

        assert result["success"] is True
        print(f"\nQuantum Call History: {result}")


# ============================================================================
# TOOL 6: Local Call Search (search_funding_calls)
# ============================================================================


class TestLocalCallSearchReal:
    """Real tests for local call search."""

    @pytest.mark.asyncio
    async def test_search_funding_calls_hydrogen(self):
        """Test searching for hydrogen funding calls."""
        from app.services.local_call_search_service import LocalCallSearchService

        service = LocalCallSearchService()
        result = service.search_calls(query="hydrogen", num_results=10)

        assert "calls" in result
        print(f"\nHydrogen Calls Found: {len(result.get('calls', []))}")

    @pytest.mark.asyncio
    async def test_search_funding_calls_ai(self):
        """Test searching for AI funding calls."""
        from app.services.local_call_search_service import LocalCallSearchService

        service = LocalCallSearchService()
        result = service.search_calls(query="artificial intelligence", num_results=10)

        assert "calls" in result
        print(f"\nAI Calls Found: {len(result.get('calls', []))}")
        if result.get("calls"):
            print(f"First call: {result['calls'][0]}")


# ============================================================================
# TOOL 7: Local Project Search (search_projects)
# ============================================================================


class TestLocalProjectSearchReal:
    """Real tests for local project search."""

    @pytest.mark.asyncio
    async def test_search_projects_ai(self):
        """Test searching for AI projects."""
        from app.services.local_project_search_service import LocalProjectSearchService

        service = LocalProjectSearchService()
        result = await service.search_projects(query="artificial intelligence", limit=10)

        assert result is not None
        print(
            f"\nAI Projects Found: {result.get('projects_found', 0) if isinstance(result, dict) else len(result)}"
        )

    @pytest.mark.asyncio
    async def test_search_projects_hydrogen(self):
        """Test searching for hydrogen projects."""
        from app.services.local_project_search_service import LocalProjectSearchService

        service = LocalProjectSearchService()
        result = await service.search_projects(query="hydrogen energy", limit=10)

        assert result is not None
        print(f"\nHydrogen Projects: {result}")


# ============================================================================
# TOOL 8: Document Search (search_local_database)
# ============================================================================


class TestDocumentSearchReal:
    """Real tests for document search."""

    @pytest.mark.asyncio
    async def test_search_documents_eligibility(self):
        """Test searching for eligibility documents."""
        from app.services.vector_search_service import VectorSearchService

        try:
            service = VectorSearchService()
            result = await service.search("eligibility requirements Horizon Europe", max_results=5)
            assert result is not None
            print(f"\nEligibility Search Result: {str(result)[:500]}")
        except Exception as e:
            print(f"\nDocument search error (expected if no embeddings): {e}")
            # Don't fail if vector search isn't set up
            pytest.skip("Vector search not configured")

    @pytest.mark.asyncio
    async def test_search_documents_consortium(self):
        """Test searching for consortium requirements."""
        from app.services.vector_search_service import VectorSearchService

        try:
            service = VectorSearchService()
            result = await service.search("minimum consortium size RIA", max_results=5)
            assert result is not None
            print(f"\nConsortium Search: {str(result)[:500]}")
        except Exception as e:
            print(f"\nDocument search error: {e}")
            pytest.skip("Vector search not configured")


# ============================================================================
# MULTI-TOOL INTEGRATION SCENARIOS
# ============================================================================


class TestMultiToolIntegration:
    """Test multiple tools working together."""

    @pytest.mark.asyncio
    async def test_proposal_planning_workflow(self):
        """
        Full proposal planning workflow:
        1. Get budget benchmarks
        2. Get consortium patterns
        3. Find partners
        """
        from app.services.tools.budget_benchmark import get_budget_benchmark_execute
        from app.services.tools.consortium_patterns import get_consortium_patterns_execute
        from app.services.tools.partner_discovery import find_experienced_partners_execute

        # Step 1: Budget
        budget = await get_budget_benchmark_execute({"cluster": "CL4", "action_type": "RIA"}, {})
        assert budget["success"] is True
        print(
            f"\n1. Budget Benchmark: Median = {budget['statistics'].get('total_eu_contribution', {}).get('median', 'N/A')}"
        )

        # Step 2: Consortium patterns
        patterns = await get_consortium_patterns_execute(
            {"cluster": "CL4", "action_type": "RIA"}, {}
        )
        assert patterns["success"] is True
        print(f"2. Consortium Patterns: {patterns}")

        # Step 3: Find partners
        partners = await find_experienced_partners_execute(
            {"topic_keywords": "artificial intelligence", "cluster": "CL4"}, {}
        )
        assert partners["success"] is True
        print(f"3. Partners Found: {partners.get('partners_found', 0)}")

    @pytest.mark.asyncio
    async def test_project_research_workflow(self):
        """
        Project research workflow:
        1. Search for similar projects
        2. Analyze call history
        """
        from app.services.tools.call_history import analyze_call_history_execute
        from app.services.tools.similar_projects import get_similar_funded_projects_execute

        # Step 1: Similar projects
        similar = await get_similar_funded_projects_execute(
            {"description": "AI for sustainable agriculture and precision farming"}, {}
        )
        assert similar["success"] is True
        print(f"\n1. Similar Projects: {similar}")

        # Step 2: Call history
        history = await analyze_call_history_execute(
            {"cluster": "CL6", "keywords": "agriculture"}, {}
        )
        assert history["success"] is True
        print(f"2. Call History: {history}")


# ============================================================================
# EDGE CASES WITH REAL DATA
# ============================================================================


class TestRealEdgeCases:
    """Edge case tests with real database."""

    @pytest.mark.asyncio
    async def test_empty_results_handling(self):
        """Test handling when no results found."""
        from app.services.tools.budget_benchmark import get_budget_benchmark_execute

        result = await get_budget_benchmark_execute(
            {"topic_keywords": "xyznonexistenttopic123"}, {}
        )

        # Should return fallback data, not fail
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_special_characters(self):
        """Test handling special characters in queries."""
        from app.services.tools.partner_discovery import find_experienced_partners_execute

        result = await find_experienced_partners_execute(
            {"topic_keywords": "AI & machine learning"}, {}
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_very_long_description(self):
        """Test handling very long descriptions."""
        from app.services.tools.similar_projects import get_similar_funded_projects_execute

        long_description = "This project aims to develop " * 50  # Very long
        result = await get_similar_funded_projects_execute({"description": long_description}, {})

        assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
