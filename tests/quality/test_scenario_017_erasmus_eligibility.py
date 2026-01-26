"""
Scenario 017: Erasmus+ Eligibility
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "Can a vocational school from Poland participate in Erasmus+ mobility?"
Expected: Yes, with KA1 details, accreditation info, National Agency
Verify: Erasmus-specific tools called, accurate eligibility
Pass threshold: 80
"""

import httpx
import pytest


class TestScenario017ErasmusEligibility:
    """Test Erasmus+ eligibility for vocational school from Poland."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Can a vocational school from Poland participate in Erasmus+ mobility?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(170000, 179999)

    @pytest.mark.asyncio
    async def test_confirms_eligibility(self, conversation_id):
        """Test that response confirms vocational school is eligible for Erasmus+."""
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
                "✅",
                "yes",
            ]

            has_eligibility = any(ind in response_text for ind in eligibility_indicators)
            assert has_eligibility, "Response should confirm eligibility for Erasmus+ mobility"

    @pytest.mark.asyncio
    async def test_mentions_ka1_vet(self, conversation_id):
        """Test that response mentions KA1 VET mobility specifically."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention KA1 or VET mobility
            ka1_indicators = [
                "ka1",
                "key action 1",
                "vet mobility",
                "vet_provider",
                "vocational",
            ]

            has_ka1 = any(ind in response_text for ind in ka1_indicators)
            assert has_ka1, "Response should mention KA1 or VET mobility details"

    @pytest.mark.asyncio
    async def test_identifies_poland_as_programme_country(self, conversation_id):
        """Test that response correctly identifies Poland as a Programme Country."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should identify Poland as Programme Country
            assert "poland" in response_text, "Response should mention Poland specifically"

            # Poland is a Programme Country (EU member state)
            programme_country_indicators = [
                "programme country",
                "eu member",
                "member state",
            ]

            has_programme_country = any(
                ind in response_text for ind in programme_country_indicators
            )
            assert has_programme_country, "Response should identify Poland as a Programme Country"

    @pytest.mark.asyncio
    async def test_uses_erasmus_eligibility_tool(self, conversation_id):
        """Test that the Erasmus+ eligibility tool is called."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Should use check_erasmus_eligibility tool
            erasmus_tools = [t for t in tools_used if "erasmus" in t.lower()]
            assert (
                len(erasmus_tools) > 0
            ), f"Should use Erasmus-specific tools, but got: {tools_used}"

    @pytest.mark.asyncio
    async def test_provides_national_agency_info(self, conversation_id):
        """Test that response provides National Agency information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention National Agency
            assert (
                "national agency" in response_text
            ), "Response should mention National Agency for guidance"

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

            # Should provide actionable guidance
            action_indicators = [
                "next steps",
                "programme guide",
                "register",
                "portal",
                "erasmus-plus.ec.europa.eu",
            ]

            has_actions = sum(1 for ind in action_indicators if ind in response_text) >= 2
            assert has_actions, "Response should provide at least 2 actionable next steps"

    @pytest.mark.asyncio
    async def test_does_not_return_third_country_guidance(self, conversation_id):
        """Test that response does NOT incorrectly treat Poland as a third country."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should NOT contain third country content for Poland
            third_country_indicators = [
                "american organizations",
                "third country participation",
                "non-associated third country",
                "self-funded participation",
                "us partner",
                "usa partner",
            ]

            has_third_country = any(ind in response_text for ind in third_country_indicators)
            assert not has_third_country, "Response should NOT treat Poland as a third country"

    @pytest.mark.asyncio
    async def test_not_generic_vet_guidance(self, conversation_id):
        """Test that response is country-specific, not generic VET guidance."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Should use tools, not just return hardcoded guidance
            # Should use tools, not just return hardcoded guidance
            assert len(tools_used) > 0, (
                "Response should use tools for country-specific eligibility, "
                "not just hardcoded guidance"
            )

    @pytest.mark.asyncio
    async def test_overall_score_meets_threshold(self, conversation_id):
        """Test that the overall response score meets the pass threshold."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()
            metadata = result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            score = 0

            # Query Fulfillment (40 points)
            if "eligible" in response_text or "✅" in response_text:
                score += 20
            if "ka1" in response_text or "vet mobility" in response_text:
                score += 10
            if "programme country" in response_text:
                score += 10

            # Specificity (25 points)
            if "poland" in response_text:
                score += 10
            if "vet_provider" in response_text or "vet provider" in response_text:
                score += 10
            if any(t for t in tools_used if "erasmus" in t.lower()):
                score += 5

            # Factual Accuracy (25 points)
            if "programme country" in response_text and "poland" in response_text:
                score += 15
            if "eligible" in response_text and "vet" in response_text:
                score += 10

            # Actionability (10 points)
            if "national agency" in response_text:
                score += 5
            if "programme guide" in response_text or "erasmus-plus.ec.europa.eu" in response_text:
                score += 5

            assert (
                score >= self.PASS_THRESHOLD
            ), f"Score {score} is below threshold {self.PASS_THRESHOLD}"

    @pytest.mark.asyncio
    async def test_returns_valid_json_response(self, conversation_id):
        """Test that the API returns a valid JSON response with expected fields."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()

            # Should have required fields
            assert "response" in result, "Response should contain 'response' field"
            assert "metadata" in result, "Response should contain 'metadata' field"
            assert len(result.get("response", "")) > 0, "Response should not be empty"

    @pytest.mark.asyncio
    async def test_no_hallucinated_calls(self, conversation_id):
        """Test that response doesn't hallucinate non-existent Erasmus+ calls."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Check for hallucinated Horizon Europe call IDs in Erasmus+ context
            import re

            horizon_call_pattern = r"HORIZON-[A-Z]+-\d+-[A-Z0-9-]+"
            horizon_calls = re.findall(horizon_call_pattern, response_text)

            # Erasmus+ queries should not return Horizon Europe call IDs
            # Erasmus+ queries should not return Horizon Europe call IDs
            assert (
                len(horizon_calls) == 0
            ), f"Should not hallucinate Horizon Europe calls for Erasmus+: {horizon_calls}"

    @pytest.mark.asyncio
    async def test_response_mentions_vocation_education_context(self, conversation_id):
        """Test that response addresses vocational education specifically."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should address vocational education
            vet_indicators = [
                "vet",
                "vocational",
                "vet_provider",
                "vocational school",
                "vocational education",
            ]

            has_vet = any(ind in response_text for ind in vet_indicators)
            assert has_vet, "Response should address vocational education context"

    @pytest.mark.asyncio
    async def test_includes_accreditation_info(self, conversation_id):
        """Test that response includes accreditation information for VET mobility."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should include accreditation info
            accreditation_indicators = [
                "accreditation",
                "accredited",
                "multi-annual",
                "simplified access",
            ]

            has_accreditation = any(ind in response_text for ind in accreditation_indicators)
            assert has_accreditation, "Response should include accreditation information"

    @pytest.mark.asyncio
    async def test_mentions_alternative_pathway(self, conversation_id):
        """Test that response mentions alternative pathway (short-term projects)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention alternative pathway for non-accredited orgs
            alternative_indicators = [
                "short-term",
                "alternative",
                "non-accredited",
            ]

            has_alternative = any(ind in response_text for ind in alternative_indicators)
            assert (
                has_alternative
            ), "Response should mention alternative pathway (short-term projects)"

    @pytest.mark.asyncio
    async def test_accreditation_benefits_mentioned(self, conversation_id):
        """Test that response mentions benefits of accreditation."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention benefits of accreditation
            benefits_indicators = [
                "simplified",
                "multi-annual",
                "streamlined",
                "flexibility",
                "benefits",
            ]

            has_benefits = any(ind in response_text for ind in benefits_indicators)
            assert has_benefits, "Response should mention benefits of accreditation"
