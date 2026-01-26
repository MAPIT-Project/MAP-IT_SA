"""
Scenario 019: Creative Europe Eligibility
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "Can a small theater company from Italy apply for Creative Europe funding?"
Expected: Yes for CULTURE strand, cooperation project options, requirements
Verify: CULTURE strand specifics, correct partnership requirements
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario019CreativeEuropeEligibility:
    """Test Creative Europe eligibility for cultural organizations."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Can a small theater company from Italy apply for Creative Europe funding?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(190000, 199999)

    @pytest.mark.asyncio
    async def test_confirms_eligibility(self, conversation_id):
        """Test that response confirms eligibility for Creative Europe."""
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
                "yes",
                "can apply",
                "eligible",
                "can participate",
                "is eligible",
            ]

            has_eligibility = any(ind in response_text for ind in eligibility_indicators)
            assert has_eligibility, "Response should confirm eligibility"

    @pytest.mark.asyncio
    async def test_mentions_culture_strand(self, conversation_id):
        """Test that response mentions the CULTURE strand."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention CULTURE strand
            culture_indicators = [
                "culture strand",
                "culture",
                "cultural",
            ]

            has_culture = any(ind in response_text for ind in culture_indicators)
            assert has_culture, "Response should mention CULTURE strand"

    @pytest.mark.asyncio
    async def test_mentions_cooperation_projects(self, conversation_id):
        """Test that response mentions cooperation projects."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention cooperation projects
            coop_indicators = [
                "cooperation project",
                "coop-small",
                "coop-medium",
                "coop-large",
                "small scale",
                "medium scale",
                "large scale",
                "european cooperation",
            ]

            has_coop = any(ind in response_text for ind in coop_indicators)
            assert has_coop, "Response should mention cooperation projects"

    @pytest.mark.asyncio
    async def test_identifies_italy_eligibility(self, conversation_id):
        """Test that response confirms Italy is an eligible country."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention Italy as eligible
            italy_indicators = [
                "italy",
                "italian",
                "eu member",
                "member state",
                "programme country",
            ]

            has_italy = any(ind in response_text for ind in italy_indicators)
            assert has_italy, "Response should confirm Italy's eligibility"

    @pytest.mark.asyncio
    async def test_uses_creative_europe_eligibility_tool(self, conversation_id):
        """Test that the Creative Europe eligibility tool is called."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should use check_creative_europe_eligibility tool
            has_ce_tool = any("creative_europe_eligibility" in tool for tool in tools_used)
            assert (
                has_ce_tool
            ), f"Should use check_creative_europe_eligibility tool. Tools used: {tools_used}"

    @pytest.mark.asyncio
    async def test_mentions_theater_context(self, conversation_id):
        """Test that response addresses the theater company context."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention cultural organizations or theater context
            theater_indicators = [
                "theater",
                "theatre",
                "cultural organization",
                "cultural organisation",
                "performing arts",
                "small scale",
                "small organization",
                "small organisation",
            ]

            has_theater = any(ind in response_text for ind in theater_indicators)
            assert has_theater, "Response should address theater company context"

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
                "creative europe desk",
                "portal",
                "website",
                "contact",
                "apply",
                "next step",
                "recommend",
                "check",
                "review",
            ]

            has_action = sum(1 for ind in action_indicators if ind in response_text) >= 2
            assert has_action, "Response should provide at least 2 actionable next steps"

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
            if any(w in response_text for w in ["yes", "can apply", "eligible"]):
                query_fulfillment += 15  # Answers yes/no
            if any(w in response_text for w in ["culture", "cultural"]):
                query_fulfillment += 10  # Identifies correct strand
            if any(w in response_text for w in ["cooperation", "coop-small", "small scale"]):
                query_fulfillment += 10  # Mentions project types
            if any(w in response_text for w in ["italy", "italian", "eu member"]):
                query_fulfillment += 5  # Confirms country eligibility
            score += min(query_fulfillment, 40)

            # Specificity (25 points)
            specificity = 0
            if any(w in response_text for w in ["coop-small", "small scale", "small-scale"]):
                specificity += 10  # Specific action type
            if any(w in response_text for w in ["partner", "consortium", "organization"]):
                specificity += 10  # Partnership details
            if re.search(r"\d", response_text):
                specificity += 5  # Numeric details
            score += min(specificity, 25)

            # Factual Accuracy (25 points)
            factual = 0
            tools_used = result.get("metadata", {}).get("tools_used", [])
            if any("creative_europe" in t for t in tools_used):
                factual += 15  # Correct tool used
            if "creative europe" in response_text:
                factual += 10  # Correct programme mentioned
            score += min(factual, 25)

            # Actionability (10 points)
            actionability = 0
            if any(w in response_text for w in ["desk", "portal", "website", "contact"]):
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

    @pytest.mark.asyncio
    async def test_no_horizon_europe_confusion(self, conversation_id):
        """Test that response doesn't confuse Creative Europe with Horizon Europe."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should use Creative Europe tool
            has_ce_tool = any("creative_europe" in tool for tool in tools_used)

            assert has_ce_tool, "Should use Creative Europe eligibility tool"

    @pytest.mark.asyncio
    async def test_no_erasmus_confusion(self, conversation_id):
        """Test that response doesn't confuse Creative Europe with Erasmus+."""
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
            has_erasmus_tool = any("erasmus" in tool for tool in tools_used)
            assert not has_erasmus_tool, f"Should NOT use Erasmus+ tools. Tools used: {tools_used}"

    @pytest.mark.asyncio
    async def test_mentions_creative_europe_programme(self, conversation_id):
        """Test that response explicitly mentions Creative Europe."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention Creative Europe
            has_ce = "creative europe" in response_text
            assert has_ce, "Response should mention Creative Europe programme"

    @pytest.mark.asyncio
    async def test_response_is_programme_specific(self, conversation_id):
        """Test that response is specific to Creative Europe (not generic EU funding)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should include Creative Europe specific terms
            ce_specific_terms = [
                "culture strand",
                "media strand",
                "cooperation project",
                "coop-small",
                "coop-medium",
                "coop-large",
                "creative europe desk",
                "cultural organization",
            ]

            has_specific_terms = any(term in response_text for term in ce_specific_terms)
            assert (
                has_specific_terms
            ), "Response should include Creative Europe-specific terminology"
