"""
Scenario 032: Topic Refinement
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Turn 1: "Find AI funding opportunities"
Turn 2: "Actually, I'm interested in AI for healthcare specifically"
Expected: Refined search for AI+healthcare
Verify: Incorporates refinement, relevant results
Fix if: Ignores refinement, repeats generic AI
Pass threshold: 80
"""

import random
import re

import pytest


class TestScenario032TopicRefinement:
    """Test topic refinement across multi-turn conversations."""

    BASE_URL = "http://localhost:8000"
    TURN1_QUERY = "Find AI funding opportunities"
    TURN2_QUERY = "Actually, I'm interested in AI for healthcare specifically"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        return random.randint(320000, 329999)

    async def _send_turn1(self, client, conversation_id):
        """Send Turn 1 query and return response."""
        await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

        response = await client.post(
            f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
            json={"message": self.TURN1_QUERY, "user_id": 1},
        )
        return response

    async def _send_turn2(self, client, conversation_id):
        """Send Turn 2 follow-up query and return response."""
        response = await client.post(
            f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
            json={"message": self.TURN2_QUERY, "user_id": 1},
        )
        return response

    def _extract_call_ids(self, text):
        """Extract call IDs from response text."""
        patterns = [
            r"HORIZON-[A-Z0-9-]+(?:-\d+)?",
            r"ERASMUS-[A-Z0-9-]+",
            r"CREA-[A-Z0-9-]+",
            r"LIFE-[A-Z0-9-]+",
            r"EU4H-[A-Z0-9-]+",
            r"DIGITAL-[A-Z0-9-]+",
        ]
        call_ids = []
        for pattern in patterns:
            matches = re.findall(pattern, text.upper())
            call_ids.extend(matches)
        return list(set(call_ids))

    def _has_healthcare_terms(self, text):
        """Check if text contains healthcare-related terms."""
        healthcare_terms = [
            "health",
            "healthcare",
            "medical",
            "clinical",
            "medicine",
            "patient",
            "hospital",
            "disease",
            "diagnostic",
            "therapeut",
            "pharma",
            "biomedic",
            "patholog",
            "oncolog",
            "cancer",
            "treatment",
            "drug",
            "biosensor",
            "genome",
            "genomic",
            "personalized medicine",
            "precision medicine",
            "medical imaging",
            "health data",
            "e-health",
            "ehealth",
            "mhealth",
            "telemedicine",
            "cluster 1",  # Horizon Europe Health cluster
        ]
        text_lower = text.lower()
        return any(term in text_lower for term in healthcare_terms)

    def _has_ai_terms(self, text):
        """Check if text contains AI-related terms."""
        ai_terms = [
            "ai",
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "neural network",
            "algorithm",
            "data science",
            "predictive",
            "automated",
            "intelligent",
        ]
        text_lower = text.lower()
        return any(term in text_lower for term in ai_terms)

    @pytest.mark.asyncio
    async def test_topic_refinement_detection_unit(self):
        """Unit test for the _detect_topic_refinement_query function."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        # Create agent instance for testing
        agent = ToolAwareAgent.__new__(ToolAwareAgent)

        # Mock context after Turn 1
        context = """PREVIOUS CONVERSATION:
----------------------------------------
USER: Find AI funding opportunities
ASSISTANT: I found **9 funding opportunities** matching your search for AI-related calls...

**Horizon Europe Calls:**
| Call ID | Title | Deadline | Budget |
|---------|-------|----------|--------|
| HORIZON-EIC-2026-AIC-01 | AI Robotics | 2026-04-15 | EUR 219M |
..."""

        query = "Actually, I'm interested in AI for healthcare specifically"

        result = agent._detect_topic_refinement_query(query, context)

        # Verify detection works
        assert result is not None, "Should detect topic refinement"
        assert result.get("action") == "call_tools", "Should have call_tools action"

        tool_calls = result.get("tool_calls", [])
        assert len(tool_calls) == 1, "Should have one tool call"

        params = tool_calls[0].get("parameters", {})
        keywords = params.get("keywords", "").lower()
        cluster = params.get("cluster", "")

        # Should have combined keywords
        assert "ai" in keywords, f"Keywords should include 'ai', got: {keywords}"
        assert "healthcare" in keywords, f"Keywords should include 'healthcare', got: {keywords}"

        # Should have Health cluster filter (database uses CL1 not HLTH)
        assert cluster == "CL1", f"Should filter by CL1 cluster, got: {cluster}"

        # Should NOT have noise words
        assert "specifically" not in keywords, f"Should not include 'specifically': {keywords}"

    @pytest.mark.asyncio
    async def test_refinement_patterns_detected(self):
        """Test that various refinement patterns are detected correctly."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent.__new__(ToolAwareAgent)

        context = """PREVIOUS CONVERSATION:
----------------------------------------
USER: Find renewable energy projects
ASSISTANT: I found 10 projects on renewable energy..."""

        test_cases = [
            ("More specifically, I want transportation applications", "transport", "CL5"),
            ("Actually, focus on maritime shipping", "maritime", "CL5"),
            ("But for agricultural use", "agricultural", "CL6"),
            ("I'm particularly interested in medical applications", "medical", "CL1"),
            ("Instead, show me manufacturing applications", "manufacturing", "CL4"),
        ]

        for query, expected_keyword, expected_cluster in test_cases:
            result = agent._detect_topic_refinement_query(query, context)
            assert result is not None, f"Should detect refinement for: {query}"

            params = result.get("tool_calls", [{}])[0].get("parameters", {})
            keywords = params.get("keywords", "").lower()
            cluster = params.get("cluster", "")

            assert (
                expected_keyword in keywords
            ), f"Keywords should include '{expected_keyword}' for query '{query}', got: {keywords}"
            assert (
                cluster == expected_cluster
            ), f"Cluster should be '{expected_cluster}' for query '{query}', got: {cluster}"
