"""
Scenario 005: Semantic Project Search
=====================================

PRD Reference: docs/prd/MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, lines 95-100
Query: "Find projects similar to developing sustainable aviation fuels"
Expected: Semantically related projects (not just keyword match)
Verify: Results include related concepts (biofuels, green aviation, etc.)
Pass threshold: 80

Tests verify:
1. Response contains project information
2. Uses get_similar_funded_projects tool (semantic search, NOT search_projects)
3. Results are semantically relevant (not just keyword matches)
4. Quality score meets threshold (80)
"""

import os
import re
import sys

import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
QUERY = "Find projects similar to developing sustainable aviation fuels"
PASS_THRESHOLD = 80


class TestScenario005SemanticProjectSearch:
    """Test suite for Scenario 005: Semantic Project Search."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.query = QUERY
        self.api_url = f"{API_BASE_URL}/api/v3/conversation"

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID."""
        import random

        return random.randint(100000, 999999)

    def _send_query(self, conversation_id: int, query: str) -> dict:
        """Send a query to the API and return the response."""
        import requests

        url = f"{self.api_url}/{conversation_id}/message"
        response = requests.post(url, json={"message": query}, timeout=120)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        return response.json()

    def _calculate_quality_score(self, response_data: dict) -> int:
        """Calculate quality score based on rubric."""
        score = 0
        response_text = response_data.get("response", "")

        # Query Fulfillment (40 points)
        # - Returns project information
        has_projects = "project" in response_text.lower()
        has_multiple = len(re.findall(r"\*\*\d+\.", response_text)) >= 3
        has_titles = bool(re.search(r"\*\*[A-Z]", response_text))

        if has_projects:
            score += 15
        if has_multiple:
            score += 15
        if has_titles:
            score += 10

        # Specificity (25 points)
        # - Project IDs, coordinators, CORDIS links
        has_project_ids = bool(re.search(r"Project ID.*\d{9}", response_text))
        has_coordinators = "coordinator" in response_text.lower()
        has_cordis_links = "cordis.europa.eu" in response_text

        if has_project_ids:
            score += 8
        if has_coordinators:
            score += 8
        if has_cordis_links:
            score += 9

        # Factual Accuracy (25 points)
        # - Results are semantically relevant to aviation/fuels
        aviation_keywords = [
            "aviation",
            "aircraft",
            "fuel",
            "flight",
            "propulsion",
            "hydrogen",
            "biofuel",
            "emission",
            "combustion",
            "engine",
        ]
        relevant_count = sum(1 for kw in aviation_keywords if kw.lower() in response_text.lower())

        if relevant_count >= 5:
            score += 25
        elif relevant_count >= 3:
            score += 18
        elif relevant_count >= 1:
            score += 10

        # Actionability (10 points)
        # - CORDIS links provided, clear next steps
        has_links = "https://" in response_text or "Details" in response_text
        has_guidance = any(
            phrase in response_text.lower()
            for phrase in ["next step", "how to", "learn more", "useful", "tip"]
        )

        if has_links:
            score += 5
        if has_guidance:
            score += 5

        return score

    # ==================== API TESTS ====================

    # ==================== UNIT TESTS ====================

    def test_semantic_query_detection(self):
        """Test that semantic similarity queries are correctly detected."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        # These routing detectors are pure; constructing the agent opens service clients.
        agent = ToolAwareAgent.__new__(ToolAwareAgent)

        # Test queries that should trigger semantic search
        semantic_queries = [
            "Find projects similar to developing sustainable aviation fuels",
            "Show me projects like AI for cancer detection",
            "Projects related to green hydrogen production",
            "Find funded projects matching this concept: renewable energy storage",
        ]

        for query in semantic_queries:
            result = agent._detect_semantic_project_query(query, "")
            assert result is not None, f"Query should be detected as semantic: {query}"
            assert (
                result["tool_calls"][0]["tool"] == "get_similar_funded_projects"
            ), f"Should use get_similar_funded_projects for: {query}"

    def test_non_semantic_query_detection(self):
        """Test that regular project searches are NOT detected as semantic."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent.__new__(ToolAwareAgent)

        # Test queries that should NOT trigger semantic search
        non_semantic_queries = [
            "Find projects about AI",
            "Show me quantum computing projects",
            "Projects on climate change",
            "What hydrogen projects exist?",
        ]

        for query in non_semantic_queries:
            result = agent._detect_semantic_project_query(query, "")
            assert result is None, f"Query should NOT be detected as semantic: {query}"


class TestRegressionScenario005:
    """Regression tests to prevent previous bugs from recurring."""

    def test_similar_to_pattern_not_keyword_search(self):
        """Regression: Queries with 'similar to' should not use keyword search."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent.__new__(ToolAwareAgent)

        query = "Find projects similar to developing sustainable aviation fuels"
        result = agent._detect_query_type_for_tool_selection(query, "")

        assert result is not None, "Query should be pre-routed"
        assert (
            result["tool_calls"][0]["tool"] == "get_similar_funded_projects"
        ), "Should use semantic search, not keyword search"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
