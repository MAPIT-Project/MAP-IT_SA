"""
Scenario 029: Comparison + Recommendation
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "Compare RIA and IA funding. Which is better for a TRL 4 project?"
Expected: Comparison table, clear recommendation with reasoning
Verify: Accurate comparison, sound recommendation
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario029ComparisonRecommendation:
    """Test RIA vs IA comparison with TRL 4 recommendation."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Compare RIA and IA funding. Which is better for a TRL 4 project?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(290000, 299999)

    @pytest.mark.asyncio
    async def test_mentions_both_action_types(self, conversation_id):
        """Test that response mentions both RIA and IA."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention both action types
            has_ria = "ria" in response_text or "research and innovation action" in response_text
            has_ia = " ia " in response_text or "innovation action" in response_text

            assert has_ria, "Response should mention RIA (Research and Innovation Action)"
            assert has_ia, "Response should mention IA (Innovation Action)"

    @pytest.mark.asyncio
    async def test_explains_trl_differences(self, conversation_id):
        """Test that response explains TRL (Technology Readiness Level) differences."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should explain TRL ranges
            trl_indicators = [
                "trl",
                "technology readiness",
                "maturity",
                "prototype",
                "trl 2-5",
                "trl 5-8",
            ]

            has_trl_info = any(ind in response_text for ind in trl_indicators)
            assert has_trl_info, "Response should explain TRL or technology maturity differences"

    @pytest.mark.asyncio
    async def test_provides_funding_rate_comparison(self, conversation_id):
        """Test that response compares funding rates (100% vs 70%)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention funding rate differences
            funding_indicators = [
                "100%",
                "70%",
                "funding rate",
                "full funding",
                "co-funding",
            ]

            has_funding = any(ind in response_text for ind in funding_indicators)
            assert has_funding, "Response should mention funding rates (100% for RIA, 70% for IA)"

    @pytest.mark.asyncio
    async def test_provides_trl4_specific_recommendation(self, conversation_id):
        """Test that response provides a clear recommendation for TRL 4."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should provide guidance for TRL 4 projects
            # TRL 4 is at the boundary - RIA covers TRL 2-5, IA covers TRL 5-8
            # Expected recommendation: RIA (since TRL 4 is more research-stage)
            recommendation_indicators = [
                "trl 4",
                "trl 2-4",
                "trl 2-5",
                "recommend",
                "suitable",
                "better for",
                "choose ria",
                "ria is",
                "ria would",
            ]

            has_recommendation = any(ind in response_text for ind in recommendation_indicators)
            assert has_recommendation, "Response should provide a recommendation for TRL 4 projects"

    @pytest.mark.asyncio
    async def test_structured_comparison(self, conversation_id):
        """Test that response provides a structured comparison (table, headers, lists)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should have some structure (table, headers, or clear sections)
            structure_indicators = [
                "|",  # Table
                "##",  # Headers
                "**ria**",  # Bold section
                "**ia**",  # Bold section
                "1.",  # Numbered list
                "- ",  # Bullet points
            ]

            has_structure = any(ind in response_text.lower() for ind in structure_indicators)
            assert has_structure, "Response should be structured (table, headers, or lists)"

    @pytest.mark.asyncio
    async def test_compares_focus_areas(self, conversation_id):
        """Test that response compares research vs demonstration focus."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # RIA = research/knowledge focus
            research_indicators = [
                "research",
                "knowledge",
                "exploring",
                "feasibility",
                "concept",
            ]
            has_research = any(ind in response_text for ind in research_indicators)

            # IA = demonstration/pilot focus
            demo_indicators = [
                "demonstrat",
                "pilot",
                "validat",
                "deploy",
                "scale",
            ]
            has_demo = any(ind in response_text for ind in demo_indicators)

            assert has_research, "Response should mention RIA's research focus"
            assert has_demo, "Response should mention IA's demonstration focus"

    @pytest.mark.asyncio
    async def test_mentions_budget_ranges(self, conversation_id):
        """Test that response mentions typical budget ranges."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention budget figures
            budget_indicators = [
                "€",
                "million",
                "budget",
                "eur",
                "3-15",
                "5-20",
                "€3",
                "€5",
            ]

            has_budget = any(ind in response_text for ind in budget_indicators)
            assert has_budget, "Response should mention typical budget ranges"

    @pytest.mark.asyncio
    async def test_provides_actionable_next_steps(self, conversation_id):
        """Test that response provides actionable next steps."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should include actionable guidance
            action_indicators = [
                "portal",
                "work programme",
                "check",
                "assess",
                "review",
                "next step",
                "ncp",
                "national contact",
                "cordis",
            ]

            action_count = sum(1 for ind in action_indicators if ind in response_text)
            assert action_count >= 2, "Response should provide at least 2 actionable next steps"

    @pytest.mark.asyncio
    async def test_decision_criteria_provided(self, conversation_id):
        """Test that response provides clear decision criteria."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should provide criteria for choosing
            criteria_indicators = [
                "choose ria",
                "choose ia",
                "when to",
                "if you",
                "if your",
                "situation",
                "depends on",
                "criteria",
            ]

            has_criteria = any(ind in response_text for ind in criteria_indicators)
            assert has_criteria, "Response should provide decision criteria for choosing"

    @pytest.mark.asyncio
    async def test_uses_built_in_guidance(self, conversation_id):
        """Test that comparison uses built-in guidance (no incorrect tool calls)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Comparison should be comprehensive even without tool calls
            essential_elements = 0
            if "ria" in response_text:
                essential_elements += 1
            if " ia " in response_text or "innovation action" in response_text:
                essential_elements += 1
            if any(w in response_text for w in ["trl", "100%", "70%"]):
                essential_elements += 1
            if any(w in response_text for w in ["research", "demonstrat"]):
                essential_elements += 1

            assert essential_elements >= 3, (
                f"Response should cover essential comparison elements. Found: {essential_elements}"
            )

    @pytest.mark.asyncio
    async def test_no_incorrect_programme_references(self, conversation_id):
        """Test that response doesn't incorrectly reference unrelated programmes."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should NOT primarily use unrelated programme tools
            unrelated_tools = [
                "erasmus",
                "creative_europe",
                "eu4health",
                "life",
            ]
            has_unrelated = any(
                any(ut in tool.lower() for ut in unrelated_tools) for tool in tools_used
            )

            # It's OK if response mentions Horizon Europe context
            assert not has_unrelated, f"Should not use unrelated tools. Tools used: {tools_used}"

    @pytest.mark.asyncio
    async def test_overall_score_meets_threshold(self, conversation_id):
        """Test that overall quality score meets the 80 threshold."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            score = 0

            # Query Fulfillment (40 points) - Both action types compared with clear guidance
            query_fulfillment = 0
            if "ria" in response_text:
                query_fulfillment += 10  # RIA mentioned
            if " ia " in response_text or "innovation action" in response_text:
                query_fulfillment += 10  # IA mentioned
            trl_terms = ["trl", "maturity", "prototype", "research", "demonstrat"]
            if any(w in response_text for w in trl_terms):
                query_fulfillment += 10  # TRL/focus difference explained
            guidance_terms = ["choose", "recommend", "suitable", "better", "depends"]
            if any(w in response_text for w in guidance_terms):
                query_fulfillment += 10  # Provides recommendation
            score += min(query_fulfillment, 40)

            # Specificity (25 points) - Concrete details
            specificity = 0
            if any(w in response_text for w in ["100%", "70%"]):
                specificity += 10  # Funding rates
            if re.search(r"trl\s*\d|trl\s*[2-9]|trl 2-5|trl 5-8", response_text):
                specificity += 8  # TRL levels mentioned
            if any(w in response_text for w in ["€", "million", "budget"]):
                specificity += 7  # Budget figures
            score += min(specificity, 25)

            # Factual Accuracy (25 points) - Correct information
            factual = 0
            # RIA is for research (TRL 2-5, 100% funding)
            if any(w in response_text for w in ["research", "knowledge", "feasibility"]):
                factual += 8
            if "100%" in response_text:
                factual += 5
            # IA is for demonstration (TRL 5-8, 70% funding)
            if any(w in response_text for w in ["demonstrat", "pilot", "validat"]):
                factual += 7
            if "70%" in response_text:
                factual += 5
            score += min(factual, 25)

            # Actionability (10 points) - Clear next steps
            actionability = 0
            action_terms = ["portal", "work programme", "check", "ncp", "cordis", "next step"]
            action_count = sum(1 for t in action_terms if t in response_text)
            if action_count >= 2:
                actionability += 10
            elif action_count >= 1:
                actionability += 5
            score += actionability

            print("\n=== Scenario 029 Score Breakdown ===")
            print(f"Query Fulfillment: {min(query_fulfillment, 40)}/40")
            print(f"Specificity: {min(specificity, 25)}/25")
            print(f"Factual Accuracy: {min(factual, 25)}/25")
            print(f"Actionability: {actionability}/10")
            print(f"TOTAL: {score}/100")
            print(f"Threshold: {self.PASS_THRESHOLD}")
            print(f"Response preview: {response_text[:500]}...")

            assert score >= self.PASS_THRESHOLD, (
                f"Score {score} below threshold {self.PASS_THRESHOLD}. "
                f"Response: {response_text[:500]}..."
            )
