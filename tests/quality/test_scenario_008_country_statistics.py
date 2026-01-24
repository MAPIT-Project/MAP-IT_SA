"""
Scenario 008: Country Statistics
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "How does Germany perform in Horizon Europe compared to France?"
Expected: Comparative stats - projects, funding, success rates
Verify: Data is accurate and comparable
Fix if: Missing comparison, wrong country data
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario008CountryStatistics:
    """Test country comparison statistics functionality."""

    BASE_URL = "http://localhost:8000"
    QUERY = "How does Germany perform in Horizon Europe compared to France?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(800000, 809999)

    @pytest.mark.asyncio
    async def test_returns_comparison_data(self, conversation_id):
        """Test that response contains comparison data for both countries."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Both countries must be mentioned
            assert "germany" in response_text or "de" in response_text
            assert "france" in response_text or "fr" in response_text

    @pytest.mark.asyncio
    async def test_uses_country_statistics_tool(self, conversation_id):
        """Test that the get_country_statistics tool is used."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})

            # Check if tools_used includes get_country_statistics
            tools_used = metadata.get("tools_used", [])

            # Also check reasoning steps for tool calls
            reasoning_steps = metadata.get("reasoning_steps", [])
            tool_in_reasoning = any(
                "get_country_statistics" in str(step) for step in reasoning_steps
            )

            assert (
                "get_country_statistics" in tools_used or tool_in_reasoning
            ), f"Expected get_country_statistics tool to be used. Tools: {tools_used}"

    @pytest.mark.asyncio
    async def test_includes_project_counts(self, conversation_id):
        """Test that response includes project count data for both countries."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention projects
            project_indicators = ["projects", "participations", "project count"]
            has_projects = any(ind in response_text for ind in project_indicators)

            # Should have numbers (project counts)
            numbers = re.findall(r"\d{2,}", response_text)

            assert has_projects, "Response should mention projects"
            assert len(numbers) >= 2, "Response should include numerical data"

    @pytest.mark.asyncio
    async def test_includes_funding_amounts(self, conversation_id):
        """Test that response includes funding amount data."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should mention funding amounts
            funding_indicators = [
                "EUR",
                "€",
                "funding",
                "billion",
                "million",
                "contribution",
            ]
            has_funding = any(ind.lower() in response_text.lower() for ind in funding_indicators)

            assert has_funding, "Response should include funding information"

    @pytest.mark.asyncio
    async def test_provides_comparative_analysis(self, conversation_id):
        """Test that response provides actual comparison, not just separate data."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should include comparison language
            comparison_indicators = [
                "compared",
                "higher",
                "lower",
                "more",
                "less",
                "leads",
                "ahead",
                "behind",
                "vs",
                "versus",
                "difference",
                "+",
                "than",
                "while",
                "whereas",
            ]
            has_comparison = any(ind in response_text for ind in comparison_indicators)

            assert has_comparison, "Response should include comparative analysis"

    @pytest.mark.asyncio
    async def test_includes_organization_data(self, conversation_id):
        """Test that response includes organization statistics or examples."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention organizations or institutional data
            org_indicators = [
                "organization",
                "institution",
                "university",
                "fraunhofer",
                "max planck",
                "cnrs",
                "cea",
                "inria",
                "research center",
                "institut",
            ]
            has_org_info = any(ind in response_text for ind in org_indicators)

            assert has_org_info, "Response should include organization statistics"

    @pytest.mark.asyncio
    async def test_quality_score_passes_threshold(self, conversation_id):
        """Test that quality analysis score meets the threshold."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})

            # Check quality analysis score if available
            quality_analysis = metadata.get("quality_analysis", {})
            quality_score = quality_analysis.get("score", 100)

            # Minimum acceptable score
            assert (
                quality_score >= self.PASS_THRESHOLD
            ), f"Quality score {quality_score} below threshold {self.PASS_THRESHOLD}"

    @pytest.mark.asyncio
    async def test_no_error_in_response(self, conversation_id):
        """Test that response does not contain error messages."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should not contain error indicators
            error_indicators = [
                "error occurred",
                "unable to",
                "could not",
                "failed to",
                "i don't have",
                "no data available",
                "cannot process",
            ]

            has_error = any(ind in response_text for ind in error_indicators)
            assert not has_error, "Response should not contain error messages"

    @pytest.mark.asyncio
    async def test_response_is_specific_not_generic(self, conversation_id):
        """Test that response is specific to Germany and France, not generic."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should have specific numbers (not placeholders)
            has_specific_numbers = bool(re.search(r"\d{3,}", response_text))

            # Should mention specific country-related terms
            specific_terms = [
                "de",
                "fr",
                "german",
                "french",
                "germany",
                "france",
            ]
            country_specific = sum(1 for term in specific_terms if term in response_text.lower())

            assert has_specific_numbers, "Response should have specific numbers"
            assert country_specific >= 2, "Response should be specific to the countries queried"

    @pytest.mark.asyncio
    async def test_includes_actionable_guidance(self, conversation_id):
        """Test that response includes actionable next steps."""
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
                "next step",
                "recommend",
                "suggest",
                "you can",
                "consider",
                "find partner",
                "ncp",
                "national contact",
                "cordis",
                "portal",
            ]
            has_action = any(ind in response_text for ind in action_indicators)

            assert has_action, "Response should include actionable guidance"


class TestCountryStatisticsOtherComparisons:
    """Test country statistics for other country pairs."""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(810000, 819999)

    @pytest.mark.asyncio
    async def test_italy_spain_comparison(self, conversation_id):
        """Test comparison between Italy and Spain."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={
                    "message": "Compare Italy and Spain performance in Horizon Europe",
                    "user_id": 1,
                },
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Both countries mentioned
            assert "italy" in response_text or "it" in response_text
            assert "spain" in response_text or "es" in response_text

    @pytest.mark.asyncio
    async def test_single_country_statistics(self, conversation_id):
        """Test statistics for a single country."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={
                    "message": "What is the Netherlands performance in Horizon Europe?",
                    "user_id": 1,
                },
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Country mentioned
            nl_terms = ["netherlands", "nl", "dutch"]
            assert any(t in response_text for t in nl_terms)

            # Should have statistics
            has_numbers = bool(re.search(r"\d{2,}", response_text))
            assert has_numbers, "Response should include numerical statistics"

    @pytest.mark.asyncio
    async def test_small_country_statistics(self, conversation_id):
        """Test statistics for a smaller EU country."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={
                    "message": "How does Belgium perform in Horizon Europe?",
                    "user_id": 1,
                },
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Country mentioned
            assert "belgium" in response_text or "be" in response_text or "belgian" in response_text

            # Should not have errors
            error_indicators = ["error", "no data", "unavailable"]
            has_error = any(ind in response_text for ind in error_indicators)
            assert not has_error, "Should handle smaller country statistics"
