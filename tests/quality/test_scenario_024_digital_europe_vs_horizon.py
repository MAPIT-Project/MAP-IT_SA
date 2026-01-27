"""
Scenario 024: Digital Europe vs Horizon Europe Comparison
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "Should I apply to Digital Europe or Horizon Europe for an AI project?"
Expected: Clear comparison - deployment vs research, TRL differences
Verify: Accurate differentiation, correct guidance
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario024DigitalEuropeVsHorizon:
    """Test Digital Europe vs Horizon Europe comparison."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Should I apply to Digital Europe or Horizon Europe for an AI project?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(240000, 249999)

    @pytest.mark.asyncio
    async def test_mentions_both_programmes(self, conversation_id):
        """Test that response mentions both programmes."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention both programmes
            has_digital_europe = "digital europe" in response_text
            has_horizon = "horizon europe" in response_text or "horizon" in response_text

            assert has_digital_europe, "Response should mention Digital Europe"
            assert has_horizon, "Response should mention Horizon Europe"

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

            # Should explain TRL differences
            trl_indicators = [
                "trl",
                "technology readiness",
                "maturity",
                "deployment",
                "research",
                "near-market",
                "ready to deploy",
                "r&d",
            ]

            has_trl_info = any(ind in response_text for ind in trl_indicators)
            assert has_trl_info, "Response should explain TRL or technology maturity differences"

    @pytest.mark.asyncio
    async def test_explains_focus_differences(self, conversation_id):
        """Test that response explains deployment vs research focus."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Digital Europe = deployment focus
            deployment_indicators = [
                "deployment",
                "deploy",
                "scaling",
                "scale",
                "capacity",
                "infrastructure",
            ]
            has_deployment = any(ind in response_text for ind in deployment_indicators)

            # Horizon Europe = research/innovation focus
            research_indicators = [
                "research",
                "r&d",
                "innovation",
                "novel",
                "breakthrough",
                "development",
            ]
            has_research = any(ind in response_text for ind in research_indicators)

            assert has_deployment, "Response should mention Digital Europe's deployment focus"
            assert has_research, "Response should mention Horizon Europe's research focus"

    @pytest.mark.asyncio
    async def test_mentions_funding_differences(self, conversation_id):
        """Test that response mentions funding rate differences."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention funding information
            funding_indicators = [
                "funding",
                "budget",
                "%",
                "rate",
                "euro",
                "billion",
                "100%",
                "70%",
                "50%",
            ]

            has_funding = any(ind in response_text for ind in funding_indicators)
            assert has_funding, "Response should mention funding rates or budgets"

    @pytest.mark.asyncio
    async def test_provides_ai_specific_guidance(self, conversation_id):
        """Test that response provides AI-specific guidance."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should provide AI-specific guidance
            ai_indicators = [
                " ai ",
                "artificial intelligence",
                "ai factory",
                "ai factories",
                "tef",
                "testing facility",
                "experimentation",
                "cluster 4",
                "digital",
            ]

            has_ai_guidance = any(ind in response_text for ind in ai_indicators)
            assert has_ai_guidance, "Response should provide AI-specific guidance"

    @pytest.mark.asyncio
    async def test_provides_clear_recommendation(self, conversation_id):
        """Test that response provides clear guidance on which to choose."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should provide guidance on choosing
            guidance_indicators = [
                "choose",
                "select",
                "if your",
                "if you",
                "depends",
                "consider",
                "recommend",
                "best suited",
                "better for",
                "suitable",
            ]

            has_guidance = any(ind in response_text for ind in guidance_indicators)
            assert has_guidance, "Response should provide guidance on which programme to choose"

    @pytest.mark.asyncio
    async def test_structured_comparison(self, conversation_id):
        """Test that response provides a structured comparison."""
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
                "**digital europe**",  # Bold section
                "**horizon europe**",  # Bold section
                "1.",  # Numbered list
                "- ",  # Bullet points
            ]

            has_structure = any(ind in response_text.lower() for ind in structure_indicators)
            assert has_structure, "Response should be structured (table, headers, or lists)"

    @pytest.mark.asyncio
    async def test_mentions_programme_budgets(self, conversation_id):
        """Test that response mentions programme budgets."""
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
            # Digital Europe: ~€7.5B, Horizon Europe: ~€95.5B
            budget_indicators = [
                "7.5",
                "7,5",
                "95.5",
                "95,5",
                "billion",
                "€",
                "eur",
            ]

            has_budget = any(ind in response_text for ind in budget_indicators)
            assert has_budget, "Response should mention programme budget figures"

    @pytest.mark.asyncio
    async def test_actionable_next_steps(self, conversation_id):
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
                "website",
                "call",
                "apply",
                "check",
                "contact",
                "next step",
                "hadea",
                "ncp",
                "national contact",
            ]

            action_count = sum(1 for ind in action_indicators if ind in response_text)
            assert action_count >= 2, "Response should provide at least 2 actionable next steps"

    @pytest.mark.asyncio
    async def test_no_programme_confusion(self, conversation_id):
        """Test that response doesn't confuse with unrelated programmes."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should NOT primarily use Erasmus+, Creative Europe, or EU4Health tools
            unrelated_tools = [
                "erasmus",
                "creative_europe",
                "eu4health",
            ]
            has_unrelated = any(
                any(ut in tool.lower() for ut in unrelated_tools) for tool in tools_used
            )

            # It's OK if response mentions other programmes, but shouldn't use their tools
            assert not has_unrelated, f"Should not use unrelated tools. Tools used: {tools_used}"

    @pytest.mark.asyncio
    async def test_uses_guidance_not_tools_for_comparison(self, conversation_id):
        """Test that comparison uses built-in guidance (programme comparison is factual)."""
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
            # (built-in guidance should provide accurate information)
            essential_elements = 0
            if "digital europe" in response_text:
                essential_elements += 1
            if "horizon europe" in response_text or "horizon" in response_text:
                essential_elements += 1
            if any(w in response_text for w in ["trl", "deployment", "research"]):
                essential_elements += 1
            if any(w in response_text for w in ["funding", "budget", "%"]):
                essential_elements += 1

            assert essential_elements >= 3, (
                f"Response should cover essential comparison elements. Found: {essential_elements}"
            )

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

            # Query Fulfillment (40 points) - Both programmes compared with clear guidance
            query_fulfillment = 0
            if "digital europe" in response_text:
                query_fulfillment += 10  # Digital Europe mentioned
            if "horizon europe" in response_text or "horizon" in response_text:
                query_fulfillment += 10  # Horizon Europe mentioned
            trl_terms = ["trl", "deployment", "research", "maturity", "ready"]
            if any(w in response_text for w in trl_terms):
                query_fulfillment += 10  # TRL/focus difference explained
            guidance_terms = ["choose", "if your", "depends", "recommend", "consider"]
            if any(w in response_text for w in guidance_terms):
                query_fulfillment += 10  # Provides guidance
            score += min(query_fulfillment, 40)

            # Specificity (25 points) - Concrete details
            specificity = 0
            if any(w in response_text for w in ["7.5", "7,5", "95.5", "95,5"]):
                specificity += 10  # Budget figures
            if any(w in response_text for w in ["100%", "70%", "50%"]):
                specificity += 10  # Funding rates
            if re.search(r"trl\s*\d|trl\s*[2-9]", response_text):
                specificity += 5  # TRL levels mentioned
            score += min(specificity, 25)

            # Factual Accuracy (25 points) - Correct information
            factual = 0
            # Digital Europe is deployment-focused
            if any(w in response_text for w in ["deployment", "deploy", "capacity"]):
                factual += 10
            # Horizon Europe is research-focused
            if any(w in response_text for w in ["research", "innovation", "r&d"]):
                factual += 10
            # AI-specific context addressed
            if any(w in response_text for w in [" ai ", "artificial intelligence", "ai factory"]):
                factual += 5
            score += min(factual, 25)

            # Actionability (10 points) - Clear next steps
            actionability = 0
            action_terms = ["portal", "website", "check", "contact", "apply", "next step", "hadea"]
            action_count = sum(1 for t in action_terms if t in response_text)
            if action_count >= 2:
                actionability += 10
            elif action_count >= 1:
                actionability += 5
            score += actionability

            assert score >= self.PASS_THRESHOLD, (
                f"Score {score} below threshold {self.PASS_THRESHOLD}. "
                f"Response: {response_text[:500]}..."
            )
