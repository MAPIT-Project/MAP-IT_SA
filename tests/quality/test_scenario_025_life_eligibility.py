"""
Scenario 025: LIFE Eligibility
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "What LIFE programme options exist for biodiversity conservation NGO?"
Expected: LIFE Nature sub-programme, SAP/SIP options, co-financing
Verify: LIFE-specific info, correct sub-programme
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario025LIFEEligibility:
    """Test LIFE Programme eligibility for biodiversity conservation NGO."""

    BASE_URL = "http://localhost:8000"
    QUERY = "What LIFE programme options exist for biodiversity conservation NGO?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(250000, 259999)

    @pytest.mark.asyncio
    async def test_confirms_eligibility(self, conversation_id):
        """Test that response confirms eligibility for LIFE Programme."""
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
                "available sub-programmes",
                "available subprogrammes",
            ]

            has_eligibility = any(ind in response_text for ind in eligibility_indicators)
            assert has_eligibility, "Response should confirm eligibility for LIFE Programme"

    @pytest.mark.asyncio
    async def test_mentions_nature_subprogramme(self, conversation_id):
        """Test that response mentions Nature and Biodiversity sub-programme."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention Nature and Biodiversity sub-programme (NAT)
            nature_indicators = [
                "nature and biodiversity",
                "nature sub-programme",
                "nature subprogramme",
                "nat",
                "natura 2000",
                "biodiversity sub-programme",
            ]

            has_nature = any(ind in response_text for ind in nature_indicators)
            assert has_nature, "Response should mention Nature and Biodiversity sub-programme"

    @pytest.mark.asyncio
    async def test_mentions_ngo_eligibility(self, conversation_id):
        """Test that response addresses NGO eligibility."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should address NGO eligibility
            ngo_indicators = [
                "ngo",
                "non-governmental",
                "environmental ngo",
                "organization type",
                "organisation type",
            ]

            has_ngo = any(ind in response_text for ind in ngo_indicators)
            assert has_ngo, "Response should address NGO eligibility"

    @pytest.mark.asyncio
    async def test_mentions_funding_rate(self, conversation_id):
        """Test that response mentions funding/co-financing rates."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention funding/co-financing rates (75% for NAT, 60% for others)
            funding_indicators = [
                "75%",
                "60%",
                "95%",
                "co-financing",
                "cofinancing",
                "funding rate",
                "eu contribution",
                "co-financing rate",
            ]

            has_funding = any(ind in response_text for ind in funding_indicators)
            assert has_funding, "Response should mention co-financing rates"

    @pytest.mark.asyncio
    async def test_mentions_project_types(self, conversation_id):
        """Test that response mentions LIFE project types."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention project types (SAP, SIP, SNAP, etc.)
            project_type_indicators = [
                "standard action",
                "sap",
                "strategic integrated",
                "sip",
                "strategic nature",
                "snap",
                "technical assistance",
                "operating grant",
                "project type",
            ]

            has_project_type = any(ind in response_text for ind in project_type_indicators)
            assert has_project_type, "Response should mention LIFE project types (SAP/SIP/SNAP)"

    @pytest.mark.asyncio
    async def test_uses_life_eligibility_tool(self, conversation_id):
        """Test that the LIFE eligibility tool is called."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should use check_life_eligibility tool
            has_life_tool = any("life" in tool.lower() for tool in tools_used)
            assert has_life_tool, (
                f"Should use check_life_eligibility tool. Tools used: {tools_used}"
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
                "cinea",
                "portal",
                "website",
                "check",
                "contact",
                "apply",
                "next step",
                "recommend",
                "review",
                "work programme",
                "national contact point",
            ]

            has_action = sum(1 for ind in action_indicators if ind in response_text) >= 2
            assert has_action, "Response should provide at least 2 actionable next steps"

    @pytest.mark.asyncio
    async def test_mentions_life_programme(self, conversation_id):
        """Test that response explicitly mentions LIFE Programme."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention LIFE Programme
            has_life = "life" in response_text
            assert has_life, "Response should mention LIFE Programme"

    @pytest.mark.asyncio
    async def test_no_horizon_europe_confusion(self, conversation_id):
        """Test that response doesn't confuse LIFE with Horizon Europe."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should use LIFE tool (not primarily Horizon Europe tools)
            has_life_tool = any("life" in tool.lower() for tool in tools_used)

            assert has_life_tool, "Should use LIFE eligibility tool"

    @pytest.mark.asyncio
    async def test_no_erasmus_confusion(self, conversation_id):
        """Test that response doesn't confuse LIFE with Erasmus+."""
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
        """Test that response doesn't confuse LIFE with Creative Europe."""
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
        """Test that response doesn't confuse LIFE with EU4Health."""
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
    async def test_no_digital_europe_confusion(self, conversation_id):
        """Test that response doesn't confuse LIFE with Digital Europe."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should NOT use Digital Europe tools
            has_de_tool = any("digital_europe" in tool.lower() for tool in tools_used)
            assert not has_de_tool, f"Should NOT use Digital Europe tools. Tools used: {tools_used}"

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
            nature_terms = ["nature and biodiversity", "nat", "nature sub-programme", "natura 2000"]
            if any(w in response_text for w in nature_terms):
                query_fulfillment += 10  # Mentions Nature sub-programme
            if any(w in response_text for w in ["ngo", "non-governmental", "environmental ngo"]):
                query_fulfillment += 10  # Addresses NGO context
            if "life" in response_text:
                query_fulfillment += 10  # Mentions LIFE Programme
            score += min(query_fulfillment, 40)

            # Specificity (25 points)
            specificity = 0
            rate_terms = ["75%", "60%", "95%", "co-financing", "funding rate"]
            if any(w in response_text for w in rate_terms):
                specificity += 10  # Co-financing rates
            project_terms = ["sap", "sip", "snap", "standard action", "strategic integrated"]
            if any(w in response_text for w in project_terms):
                specificity += 10  # Mentions project types
            if re.search(r"\d", response_text):
                specificity += 5  # Numeric details
            score += min(specificity, 25)

            # Factual Accuracy (25 points)
            factual = 0
            tools_used = result.get("metadata", {}).get("tools_used", [])
            if any("life" in t.lower() for t in tools_used):
                factual += 15  # Correct tool used
            if "life" in response_text:
                factual += 10  # Correct programme mentioned
            score += min(factual, 25)

            # Actionability (10 points)
            actionability = 0
            action_terms = [
                "cinea",
                "portal",
                "website",
                "check",
                "contact",
                "apply",
                "next step",
                "review",
                "national contact point",
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
