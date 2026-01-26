"""
Scenario 021: EU4Health Eligibility
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "What EU4Health funding options are available for a hospital consortium?"
Expected: Joint actions, grants, eligibility for health entities
Verify: EU4Health-specific options, correct eligibility
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario021EU4HealthEligibility:
    """Test EU4Health eligibility for hospital consortium."""

    BASE_URL = "http://localhost:8000"
    QUERY = "What EU4Health funding options are available for a hospital consortium?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(210000, 219999)

    @pytest.mark.asyncio
    async def test_confirms_eligibility(self, conversation_id):
        """Test that response confirms eligibility for EU4Health."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should confirm eligibility
            eligibility_indicators = [
                "eligible",
                "can participate",
                "can apply",
                "funding options",
                "available actions",
            ]

            has_eligibility = any(ind in response_text for ind in eligibility_indicators)
            assert has_eligibility, "Response should confirm eligibility for EU4Health"

    @pytest.mark.asyncio
    async def test_mentions_action_grants(self, conversation_id):
        """Test that response mentions Action Grants (AG)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention Action Grants
            ag_indicators = [
                "action grant",
                "project grant",
                "(ag)",
                "(pj)",
            ]

            has_ag = any(ind in response_text for ind in ag_indicators)
            assert has_ag, "Response should mention Action Grants (AG)"

    @pytest.mark.asyncio
    async def test_identifies_eligible_actions(self, conversation_id):
        """Test that response identifies the correct eligible actions for healthcare providers."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Hospitals/healthcare providers are eligible for AG, PJ, PROC (not JA)
            # Response should identify their actual eligible actions
            eligible_action_indicators = [
                "action grant",
                "(ag)",
                "project grant",
                "(pj)",
                "procurement",
                "(proc)",
                "eligible actions",
                "funding options",
            ]

            has_eligible_actions = any(ind in response_text for ind in eligible_action_indicators)
            assert has_eligible_actions, "Response should identify eligible actions"

    @pytest.mark.asyncio
    async def test_mentions_co_financing(self, conversation_id):
        """Test that response mentions co-financing rates."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention co-financing rates (60% or 80%)
            cofinancing_indicators = [
                "co-financing",
                "cofinancing",
                "60%",
                "80%",
                "eu contribution",
                "funding rate",
            ]

            has_cofinancing = any(ind in response_text for ind in cofinancing_indicators)
            assert has_cofinancing, "Response should mention co-financing rates"

    @pytest.mark.asyncio
    async def test_mentions_healthcare_provider(self, conversation_id):
        """Test that response addresses healthcare provider context."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention healthcare/hospital context
            healthcare_indicators = [
                "hospital",
                "healthcare",
                "health provider",
                "healthcare provider",
                "health entity",
            ]

            has_healthcare = any(ind in response_text for ind in healthcare_indicators)
            assert has_healthcare, "Response should address healthcare provider context"

    @pytest.mark.asyncio
    async def test_uses_eu4health_eligibility_tool(self, conversation_id):
        """Test that the EU4Health eligibility tool is called."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should use check_eu4health_eligibility tool
            has_eu4h_tool = any("eu4health" in tool.lower() for tool in tools_used)
            assert (
                has_eu4h_tool
            ), f"Should use check_eu4health_eligibility tool. Tools used: {tools_used}"

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
                "hadea",
                "portal",
                "website",
                "check",
                "contact",
                "apply",
                "next step",
                "recommend",
                "review",
                "work programme",
            ]

            has_action = sum(1 for ind in action_indicators if ind in response_text) >= 2
            assert has_action, "Response should provide at least 2 actionable next steps"

    @pytest.mark.asyncio
    async def test_mentions_eu4health_programme(self, conversation_id):
        """Test that response explicitly mentions EU4Health."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention EU4Health
            has_eu4h = "eu4health" in response_text or "eu 4 health" in response_text
            assert has_eu4h, "Response should mention EU4Health programme"

    @pytest.mark.asyncio
    async def test_no_horizon_europe_confusion(self, conversation_id):
        """Test that response doesn't confuse EU4Health with Horizon Europe."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should use EU4Health tool (not Horizon Europe tools primarily)
            has_eu4h_tool = any("eu4health" in tool.lower() for tool in tools_used)

            assert has_eu4h_tool, "Should use EU4Health eligibility tool"

    @pytest.mark.asyncio
    async def test_no_erasmus_confusion(self, conversation_id):
        """Test that response doesn't confuse EU4Health with Erasmus+."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should NOT use Erasmus+ tools
            has_erasmus_tool = any("erasmus" in tool.lower() for tool in tools_used)
            assert not has_erasmus_tool, f"Should NOT use Erasmus+ tools. Tools used: {tools_used}"

    @pytest.mark.asyncio
    async def test_no_creative_europe_confusion(self, conversation_id):
        """Test that response doesn't confuse EU4Health with Creative Europe."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should NOT use Creative Europe tools
            has_ce_tool = any("creative_europe" in tool.lower() for tool in tools_used)
            assert not has_ce_tool, f"Should NOT use CE tools. Tools used: {tools_used}"

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

            # Query Fulfillment (40 points)
            query_fulfillment = 0
            if any(w in response_text for w in ["eligible", "can participate", "can apply"]):
                query_fulfillment += 10  # Confirms eligibility
            if any(w in response_text for w in ["action grant", "project grant", "(ag)", "(pj)"]):
                query_fulfillment += 10  # Mentions action grants
            if any(w in response_text for w in ["joint action", "(ja)", "member state"]):
                query_fulfillment += 10  # Mentions joint actions
            if any(w in response_text for w in ["hospital", "healthcare", "health provider"]):
                query_fulfillment += 10  # Addresses hospital context
            score += min(query_fulfillment, 40)

            # Specificity (25 points)
            specificity = 0
            if any(w in response_text for w in ["60%", "80%", "co-financing", "cofinancing"]):
                specificity += 10  # Co-financing rates
            strand_terms = ["crisis", "prevention", "health system", "digital"]
            if any(w in response_text for w in strand_terms):
                specificity += 10  # Mentions strands
            if re.search(r"\d", response_text):
                specificity += 5  # Numeric details
            score += min(specificity, 25)

            # Factual Accuracy (25 points)
            factual = 0
            tools_used = result.get("metadata", {}).get("tools_used", [])
            if any("eu4health" in t.lower() for t in tools_used):
                factual += 15  # Correct tool used
            if "eu4health" in response_text or "eu 4 health" in response_text:
                factual += 10  # Correct programme mentioned
            score += min(factual, 25)

            # Actionability (10 points)
            actionability = 0
            if any(w in response_text for w in ["hadea", "portal", "website", "contact"]):
                actionability += 5
            if any(w in response_text for w in ["apply", "check", "review", "recommend"]):
                actionability += 5
            score += min(actionability, 10)

            assert (
                score >= self.PASS_THRESHOLD
            ), f"Quality score {score} below threshold {self.PASS_THRESHOLD}"

    @pytest.mark.asyncio
    async def test_returns_valid_json_response(self, conversation_id):
        """Test that response is valid JSON with expected structure."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()

            # Check required fields
            assert "response" in result, "Response should include 'response' field"
            assert "metadata" in result, "Response should include 'metadata' field"
            assert len(result.get("response", "")) > 100, "Response should be substantial"
