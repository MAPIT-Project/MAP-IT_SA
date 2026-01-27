"""
Scenario 023: Digital Europe Eligibility
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "Can a cybersecurity startup apply to Digital Europe?"
Expected: Yes, cybersecurity objective details, SME info
Verify: Digital Europe specifics, correct objectives
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario023DigitalEuropeEligibility:
    """Test Digital Europe eligibility for cybersecurity startup."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Can a cybersecurity startup apply to Digital Europe?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(230000, 239999)

    @pytest.mark.asyncio
    async def test_confirms_eligibility(self, conversation_id):
        """Test that response confirms eligibility for Digital Europe."""
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
                "funding opportunities",
                "available objectives",
            ]

            has_eligibility = any(ind in response_text for ind in eligibility_indicators)
            assert has_eligibility, "Response should confirm eligibility for Digital Europe"

    @pytest.mark.asyncio
    async def test_mentions_cybersecurity_objective(self, conversation_id):
        """Test that response mentions Cybersecurity objective."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention Cybersecurity objective
            cyber_indicators = [
                "cybersecurity",
                "cyber security",
                "cyber-security",
                "cybersecurity and trust",
                "eccc",
            ]

            has_cyber = any(ind in response_text for ind in cyber_indicators)
            assert has_cyber, "Response should mention Cybersecurity objective"

    @pytest.mark.asyncio
    async def test_identifies_eligible_objectives(self, conversation_id):
        """Test that response identifies eligible objectives for startups."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Startups are eligible for multiple objectives
            # Response should identify their actual eligible objectives
            eligible_objective_indicators = [
                "cybersecurity",
                "ai",
                "artificial intelligence",
                "hpc",
                "skills",
                "deployment",
                "edih",
                "eligible objectives",
            ]

            has_eligible_objectives = any(
                ind in response_text for ind in eligible_objective_indicators
            )
            assert has_eligible_objectives, "Response should identify eligible objectives"

    @pytest.mark.asyncio
    async def test_mentions_funding_rate(self, conversation_id):
        """Test that response mentions funding rates."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention funding rates (50%)
            funding_indicators = [
                "50%",
                "funding rate",
                "co-financing",
                "cofinancing",
                "eu contribution",
            ]

            has_funding = any(ind in response_text for ind in funding_indicators)
            assert has_funding, "Response should mention funding rates"

    @pytest.mark.asyncio
    async def test_mentions_startup_sme_context(self, conversation_id):
        """Test that response addresses startup/SME context."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention startup/SME context
            startup_indicators = [
                "startup",
                "start-up",
                "sme",
                "small",
                "scaleup",
                "scale-up",
            ]

            has_startup = any(ind in response_text for ind in startup_indicators)
            assert has_startup, "Response should address startup/SME context"

    @pytest.mark.asyncio
    async def test_uses_digital_europe_eligibility_tool(self, conversation_id):
        """Test that the Digital Europe eligibility tool is called."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should use check_digital_europe_eligibility tool
            has_dep_tool = any("digital_europe" in tool.lower() for tool in tools_used)
            assert has_dep_tool, (
                f"Should use check_digital_europe_eligibility tool. Tools used: {tools_used}"
            )

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
    async def test_mentions_digital_europe_programme(self, conversation_id):
        """Test that response explicitly mentions Digital Europe."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention Digital Europe
            has_dep = "digital europe" in response_text
            assert has_dep, "Response should mention Digital Europe programme"

    @pytest.mark.asyncio
    async def test_no_horizon_europe_confusion(self, conversation_id):
        """Test that response doesn't confuse Digital Europe with Horizon Europe."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should use Digital Europe tool (not Horizon Europe tools primarily)
            has_dep_tool = any("digital_europe" in tool.lower() for tool in tools_used)

            assert has_dep_tool, "Should use Digital Europe eligibility tool"

    @pytest.mark.asyncio
    async def test_no_erasmus_confusion(self, conversation_id):
        """Test that response doesn't confuse Digital Europe with Erasmus+."""
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
        """Test that response doesn't confuse Digital Europe with Creative Europe."""
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
    async def test_no_eu4health_confusion(self, conversation_id):
        """Test that response doesn't confuse Digital Europe with EU4Health."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should NOT use EU4Health tools
            has_eu4h_tool = any("eu4health" in tool.lower() for tool in tools_used)
            assert not has_eu4h_tool, f"Should NOT use EU4Health tools. Tools used: {tools_used}"

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
            cyber_terms = ["cybersecurity", "cyber security", "cyber-security"]
            if any(w in response_text for w in cyber_terms):
                query_fulfillment += 10  # Mentions cybersecurity objective
            if any(w in response_text for w in ["startup", "start-up", "sme", "scaleup"]):
                query_fulfillment += 10  # Addresses startup context
            if any(w in response_text for w in ["digital europe"]):
                query_fulfillment += 10  # Mentions Digital Europe
            score += min(query_fulfillment, 40)

            # Specificity (25 points)
            specificity = 0
            if any(w in response_text for w in ["50%", "funding rate", "co-financing"]):
                specificity += 10  # Funding rates
            objective_terms = ["hpc", "ai", "skills", "deployment", "semiconductors"]
            if any(w in response_text for w in objective_terms):
                specificity += 10  # Mentions objectives
            if re.search(r"\d", response_text):
                specificity += 5  # Numeric details
            score += min(specificity, 25)

            # Factual Accuracy (25 points)
            factual = 0
            tools_used = result.get("metadata", {}).get("tools_used", [])
            if any("digital_europe" in t.lower() for t in tools_used):
                factual += 15  # Correct tool used
            if "digital europe" in response_text:
                factual += 10  # Correct programme mentioned
            score += min(factual, 25)

            # Actionability (10 points)
            actionability = 0
            action_terms = [
                "hadea",
                "portal",
                "website",
                "check",
                "contact",
                "apply",
                "next step",
                "review",
            ]
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
