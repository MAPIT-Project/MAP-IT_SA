"""
Scenario 027: Multi-Programme Search
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "Find all EU funding for sustainable agriculture across all programmes"
Expected: Results from LIFE, Horizon, potentially Erasmus+ (education)
Verify: Multiple programmes searched, relevant results
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario027MultiProgrammeSearch:
    """Test multi-programme search for sustainable agriculture funding."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Find all EU funding for sustainable agriculture across all programmes"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(270000, 279999)

    @pytest.mark.asyncio
    async def test_searches_multiple_programmes(self, conversation_id):
        """Test that response mentions searching across multiple EU programmes."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention searching across programmes
            programme_indicators = [
                "programmes searched",
                "across",
                "multiple programmes",
                "all programmes",
                "horizon europe",
            ]

            has_multi_programme = any(ind in response_text for ind in programme_indicators)
            assert has_multi_programme, "Response should indicate multiple programmes were searched"

    @pytest.mark.asyncio
    async def test_includes_horizon_europe(self, conversation_id):
        """Test that Horizon Europe is included in search results."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention Horizon Europe
            has_horizon = "horizon" in response_text or "🔬" in response_text
            assert has_horizon, "Response should include Horizon Europe programme"

    @pytest.mark.asyncio
    async def test_returns_relevant_results(self, conversation_id):
        """Test that results are relevant to sustainable agriculture."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should have agriculture/food-related results
            relevance_indicators = [
                "agri",
                "food",
                "farm",
                "soil",
                "bioeconomy",
                "agroecolog",
                "rural",
                "sustainable",
            ]

            has_relevant = any(ind in response_text for ind in relevance_indicators)
            assert has_relevant, "Results should be relevant to sustainable agriculture"

    @pytest.mark.asyncio
    async def test_includes_call_details(self, conversation_id):
        """Test that response includes call details (IDs, deadlines)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should include call topic codes (HORIZON-XX format)
            has_call_codes = bool(re.search(r"HORIZON-[A-Z0-9-]+", response_text, re.IGNORECASE))
            assert has_call_codes, "Response should include call topic codes"

    @pytest.mark.asyncio
    async def test_includes_eu_portal_links(self, conversation_id):
        """Test that response includes EU Funding Portal links."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should include EU Portal links
            has_portal_link = (
                "funding-tenders" in response_text
                or "ec.europa.eu" in response_text
                or "eu portal" in response_text
            )
            assert has_portal_link, "Response should include EU Funding Portal links"

    @pytest.mark.asyncio
    async def test_mentions_status(self, conversation_id):
        """Test that response mentions call status (open/upcoming)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention status
            status_indicators = ["open", "upcoming", "status", "🟢", "🔵"]

            has_status = any(ind in response_text for ind in status_indicators)
            assert has_status, "Response should mention call status"

    @pytest.mark.asyncio
    async def test_provides_actionable_guidance(self, conversation_id):
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

            # Should provide guidance
            guidance_indicators = [
                "next step",
                "register",
                "eligibility",
                "partner",
                "portal",
                "review",
            ]

            has_guidance = any(ind in response_text for ind in guidance_indicators)
            assert has_guidance, "Response should provide actionable guidance"

    @pytest.mark.asyncio
    async def test_shows_result_count(self, conversation_id):
        """Test that response shows how many results were found."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention number of results found
            count_indicators = [
                "found",
                r"\d+ funding",
                r"\d+ opportunit",
                r"\d+ call",
                r"\d+ result",
            ]

            has_count = any(
                re.search(ind, response_text) if "\\" in ind else ind in response_text
                for ind in count_indicators
            )
            assert has_count, "Response should indicate number of results found"

    @pytest.mark.asyncio
    async def test_uses_search_all_programmes_tool(self, conversation_id):
        """Test that the search_all_programmes tool is used."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            # Use streaming endpoint to capture metadata
            collected_events = []
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message/stream",
                json={"message": self.QUERY, "user_id": 1},
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        collected_events.append(line[6:])

            # Check for tool call in events
            has_tool_call = any("search_all_programmes" in event for event in collected_events)
            assert has_tool_call, (
                "search_all_programmes tool should be called for cross-programme search"
            )

    @pytest.mark.asyncio
    async def test_quality_score_meets_threshold(self, conversation_id):
        """Test that response quality score meets the pass threshold (80)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            # Use streaming endpoint to get quality analysis
            collected_events = []
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message/stream",
                json={"message": self.QUERY, "user_id": 1},
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        collected_events.append(line[6:])

            # Find quality analysis in complete event
            import json

            quality_score = None
            for event in collected_events:
                try:
                    data = json.loads(event)
                    if data.get("type") == "complete":
                        quality_analysis = data.get("metadata", {}).get("quality_analysis", {})
                        quality_score = quality_analysis.get("score")
                        break
                except json.JSONDecodeError:
                    continue

            assert quality_score is not None, "Quality score should be available"
            assert quality_score >= self.PASS_THRESHOLD, (
                f"Quality score {quality_score} below threshold {self.PASS_THRESHOLD}"
            )

    @pytest.mark.asyncio
    async def test_no_deflection_phrases(self, conversation_id):
        """Test that response doesn't contain deflection phrases."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should NOT contain deflection phrases
            deflection_phrases = [
                "couldn't extract specific details",
                "please try a more specific",
                "i don't have enough information",
                "i'm not sure",
            ]

            for phrase in deflection_phrases:
                assert phrase not in response_text, (
                    f"Response should not contain deflection phrase: '{phrase}'"
                )

    @pytest.mark.asyncio
    async def test_mentions_programme_list(self, conversation_id):
        """Test that response lists programmes that were searched."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should list searched programmes
            programmes = [
                "horizon",
                "erasmus",
                "creative europe",
                "eu4health",
                "digital europe",
                "life",
            ]

            # Should mention at least 3 programmes
            mentioned = sum(1 for p in programmes if p in response_text)
            assert mentioned >= 3, f"Response should list searched programmes (found {mentioned})"

    @pytest.mark.asyncio
    async def test_handles_comma_separated_keywords(self, conversation_id):
        """Test that comma-separated keywords work correctly."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            # Query that typically results in comma-separated keywords
            query = "Find EU funding for agriculture, food systems, and soil health"

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": query, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should return results (not empty)
            has_results = (
                "found" in response_text and "funding" in response_text
            ) or "horizon" in response_text
            assert has_results, "Query with comma-separated keywords should return results"
