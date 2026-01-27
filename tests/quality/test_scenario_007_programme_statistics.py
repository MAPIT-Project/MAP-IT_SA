"""
Test Scenario 007: Programme Statistics

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 007
Query: "What is the success rate for Horizon Europe EIC Accelerator?"
Expected: Accurate success rate with context (year, comparison)
Verify: Numbers match official EU statistics
Fix if: Wrong numbers, no source indication, outdated data
Pass threshold: 80

This test verifies that the system properly returns programme statistics:
- Uses get_programme_statistics tool
- Returns accurate success rate data
- Provides context (year, stages, comparison data)
- Indicates data source
- Numbers match official EU data (2-5% for EIC Accelerator)
"""

import httpx
import pytest


class TestScenario007ProgrammeStatistics:
    """Test suite for Scenario 007: Programme Statistics."""

    BASE_URL = "http://localhost:8000"
    QUERY = "What is the success rate for Horizon Europe EIC Accelerator?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(700000, 709999)

    @pytest.mark.asyncio
    async def test_returns_success_rate(self, conversation_id):
        """Test that the query returns success rate information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200, f"API returned {response.status_code}"
            result = response.json()

            response_text = result.get("response", "")

            # Should mention success rate
            assert "success rate" in response_text.lower() or "%" in response_text, (
                "Response should mention success rate"
            )

    @pytest.mark.asyncio
    async def test_uses_get_programme_statistics_tool(self, conversation_id):
        """Test that get_programme_statistics tool is used."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            metadata = result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Should use get_programme_statistics tool
            stats_tool_used = any("programme_statistics" in str(t).lower() for t in tools_used)
            assert stats_tool_used, f"Should use get_programme_statistics tool, got: {tools_used}"

    @pytest.mark.asyncio
    async def test_returns_accurate_success_rate(self, conversation_id):
        """Test that success rate is accurate (2-5% range for EIC)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # EIC Accelerator success rate is 2-5% overall
            # Look for percentage indicators in the correct range
            import re

            # Find all percentages in the response
            percentages = re.findall(r"(\d+(?:\.\d+)?)\s*%", response_text)
            percentages = [float(p) for p in percentages]

            # Should have some reasonable percentages for EIC (not 50% or 90%)
            # EIC overall is 2-5%, stage rates can be higher (25-30%, 50-60%)
            low_rate_found = any(p <= 10 for p in percentages)
            assert low_rate_found, (
                f"Should mention a low success rate (<=10%) for EIC, found: {percentages}"
            )

    @pytest.mark.asyncio
    async def test_mentions_eic_accelerator(self, conversation_id):
        """Test that response mentions EIC Accelerator specifically."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should mention EIC Accelerator
            eic_mentioned = "eic" in response_text.lower() or "accelerator" in response_text.lower()
            assert eic_mentioned, "Response should mention EIC Accelerator"

    @pytest.mark.asyncio
    async def test_provides_context(self, conversation_id):
        """Test that response provides context (stages, notes, or explanation)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should provide context (stage breakdown, notes, or additional information)
            context_indicators = [
                "stage",
                "proposal",
                "interview",
                "short",
                "full",
                "cut-off",
                "competitive",
                "note",
                "overall",
            ]
            has_context = any(ind.lower() in response_text.lower() for ind in context_indicators)
            assert has_context, "Response should provide context about the success rate"

    @pytest.mark.asyncio
    async def test_includes_funding_or_detailed_statistics(self, conversation_id):
        """Test that response includes funding info or detailed statistics."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")
            metadata = result.get("metadata", {})
            reasoning_steps = metadata.get("reasoning_steps", [])

            # Check tool result for funding info or detailed statistics
            has_detail_in_tool = False
            for step in reasoning_steps:
                observation = step.get("observation", "")
                # Check for funding info OR detailed success rate info
                funding_indicators = ["million", "€", "EUR", "grant", "equity", "2.5", "15"]
                stats_indicators = ["success rate", "overall", "pillar", "innovative"]
                all_indicators = funding_indicators + stats_indicators
                if any(ind.lower() in observation.lower() for ind in all_indicators):
                    has_detail_in_tool = True
                    break

            # Also check response text
            response_indicators = [
                "€",
                "EUR",
                "million",
                "2.5",
                "15",
                "sme",
                "startup",
                "breakthrough",
                "innovation",
                "2-5%",
                "pillar",
            ]
            has_detail_in_response = any(
                ind.lower() in response_text.lower() for ind in response_indicators
            )

            assert has_detail_in_tool or has_detail_in_response, (
                "Should include funding information or detailed statistics"
            )

    @pytest.mark.asyncio
    async def test_quality_score_passes_threshold(self, conversation_id):
        """Test that quality analysis reports passing score."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            metadata = result.get("metadata", {})
            quality_analysis = metadata.get("quality_analysis", {})

            # Quality score should be available
            assert "score" in quality_analysis, "Response should include quality score"

            # Quality score should meet threshold
            score = quality_analysis.get("score", 0)
            assert score >= self.PASS_THRESHOLD, (
                f"Quality score {score} should be >= {self.PASS_THRESHOLD}"
            )

    @pytest.mark.asyncio
    async def test_no_error_in_response(self, conversation_id):
        """Test that response does not contain error messages."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()

            # Should not have error in response
            assert "error" not in result, f"Response should not have error: {result.get('error')}"

            response_text = result.get("response", "")
            # Should not have generic error messages
            assert not any(
                phrase.lower() in response_text.lower()
                for phrase in ["error occurred", "I apologize", "something went wrong"]
            ), "Response should not contain error messages"

    @pytest.mark.asyncio
    async def test_response_is_specific_not_generic(self, conversation_id):
        """Test that response is specific to EIC, not a generic answer."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should not be a generic "I don't have that information" response
            generic_phrases = [
                "i don't have specific",
                "i cannot provide",
                "i am unable",
                "no data available",
            ]
            is_generic = any(phrase in response_text.lower() for phrase in generic_phrases)
            assert not is_generic, "Response should be specific, not generic"

    @pytest.mark.asyncio
    async def test_mentions_stages_or_breakdown(self, conversation_id):
        """Test that response breaks down success rate by stages."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # EIC has stage-by-stage success rates
            stage_indicators = [
                "step",
                "stage",
                "short proposal",
                "full proposal",
                "interview",
                "overall",
            ]
            has_stages = any(ind.lower() in response_text.lower() for ind in stage_indicators)
            assert has_stages, "Response should mention stages or breakdown of success rates"


class TestProgrammeStatisticsOtherProgrammes:
    """Test programme statistics for other Horizon Europe programmes."""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(710000, 719999)

    @pytest.mark.asyncio
    async def test_erc_statistics(self, conversation_id):
        """Test that ERC statistics can be retrieved."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "What is the success rate for ERC grants?", "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should mention ERC and success rate
            assert "erc" in response_text.lower(), "Response should mention ERC"
            assert "%" in response_text, "Response should include percentage"

    @pytest.mark.asyncio
    async def test_msca_statistics(self, conversation_id):
        """Test that MSCA statistics can be retrieved."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={
                    "message": "What are the success rates for MSCA fellowships?",
                    "user_id": 1,
                },
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should mention MSCA and success rate
            msca_mentioned = "msca" in response_text.lower() or "marie" in response_text.lower()
            assert msca_mentioned, "Response should mention MSCA"
            assert "%" in response_text, "Response should include percentage"

    @pytest.mark.asyncio
    async def test_cluster_statistics(self, conversation_id):
        """Test that Cluster statistics can be retrieved."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            query = "What are the statistics for Horizon Europe Cluster 5 Climate?"
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": query, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should mention cluster and funding information
            has_cluster = "cluster" in response_text.lower()
            has_climate = "climate" in response_text.lower()
            cluster_mentioned = has_cluster or has_climate
            assert cluster_mentioned, "Response should mention Cluster 5 or Climate"

            # Should have funding or project data
            has_data = any(
                ind in response_text.lower()
                for ind in ["project", "funding", "€", "budget", "million"]
            )
            assert has_data, "Response should include project or funding data"
