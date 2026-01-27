"""
Scenario 020: Creative Europe Calls
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "Find open Creative Europe MEDIA calls for film distribution"
Expected: MEDIA strand distribution calls with deadlines
Verify: Calls are MEDIA strand, actually open/upcoming
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario020CreativeEuropeCalls:
    """Test Creative Europe MEDIA call search functionality."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Find open Creative Europe MEDIA calls for film distribution"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(200000, 209999)

    @pytest.mark.asyncio
    async def test_uses_search_funding_calls_tool(self, conversation_id):
        """Test that the search_funding_calls tool is called."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should use search_funding_calls tool
            has_search_tool = any("search_funding_calls" in tool for tool in tools_used)
            assert has_search_tool, (
                f"Should use search_funding_calls tool. Tools used: {tools_used}"
            )

    @pytest.mark.asyncio
    async def test_returns_media_strand_calls(self, conversation_id):
        """Test that response returns MEDIA strand calls."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention CREA-MEDIA call codes
            media_indicators = [
                "crea-media",
                "media strand",
                "media call",
                "media funding",
            ]

            has_media = any(ind in response_text for ind in media_indicators)
            assert has_media, "Response should return MEDIA strand calls"

    @pytest.mark.asyncio
    async def test_includes_call_deadlines(self, conversation_id):
        """Test that response includes call deadlines."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should include deadline information
            deadline_indicators = [
                "deadline",
                "closing",
                "2025",
                "2026",
                "january",
                "february",
                "march",
                "april",
                "may",
                "june",
                "july",
                "august",
                "september",
                "october",
                "november",
                "december",
            ]

            has_deadline = any(ind in response_text.lower() for ind in deadline_indicators)
            assert has_deadline, "Response should include call deadlines"

    @pytest.mark.asyncio
    async def test_includes_call_status(self, conversation_id):
        """Test that response includes call status (open/upcoming)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should include status
            status_indicators = ["open", "upcoming", "status", "available"]

            has_status = any(ind in response_text for ind in status_indicators)
            assert has_status, "Response should include call status"

    @pytest.mark.asyncio
    async def test_includes_distribution_context(self, conversation_id):
        """Test that response addresses distribution/sales context."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention distribution-related terms
            distribution_indicators = [
                "distribution",
                "sales agent",
                "film sales",
                "films on the move",
                "theatrical",
                "cinema",
            ]

            has_distribution = any(ind in response_text for ind in distribution_indicators)
            assert has_distribution, "Response should address distribution context"

    @pytest.mark.asyncio
    async def test_includes_eu_portal_links(self, conversation_id):
        """Test that response includes EU Portal application links."""
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
            portal_indicators = [
                "ec.europa.eu",
                "funding-tenders",
                "portal",
                "apply",
            ]

            has_portal = any(ind in response_text for ind in portal_indicators)
            assert has_portal, "Response should include EU Portal links"

    @pytest.mark.asyncio
    async def test_includes_call_id(self, conversation_id):
        """Test that response includes call IDs/topic codes."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should include CREA call ID pattern
            has_call_id = "CREA-MEDIA" in response_text or "crea-media" in response_text.lower()
            assert has_call_id, "Response should include call IDs (CREA-MEDIA-xxx)"

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
                "apply",
                "register",
                "check",
                "review",
                "portal",
                "eligibility",
                "next step",
                "how to",
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
            tools_used = result.get("metadata", {}).get("tools_used", [])
            if any("search_funding_calls" in t for t in tools_used):
                query_fulfillment += 15  # Used search tool
            if any(w in response_text for w in ["crea-media", "media"]):
                query_fulfillment += 10  # Returns MEDIA calls
            if any(w in response_text for w in ["distribution", "sales agent", "film"]):
                query_fulfillment += 10  # Distribution context
            if any(w in response_text for w in ["open", "upcoming", "status"]):
                query_fulfillment += 5  # Shows status
            score += min(query_fulfillment, 40)

            # Specificity (25 points)
            specificity = 0
            if "crea-media" in response_text:
                specificity += 10  # Specific call code
            if re.search(r"deadline|closing|202[5-6]", response_text):
                specificity += 10  # Deadline info
            month_pattern = r"\d{1,2}\s+(january|february|march|april|may|june)"
            month_pattern += r"|july|august|september|october|november|december"
            if re.search(month_pattern, response_text):
                specificity += 5  # Specific date
            score += min(specificity, 25)

            # Factual Accuracy (25 points)
            factual = 0
            if any("search_funding_calls" in t for t in tools_used):
                factual += 15  # Correct tool used
            if "ec.europa.eu" in response_text or "funding-tenders" in response_text:
                factual += 10  # Correct portal link
            score += min(factual, 25)

            # Actionability (10 points)
            actionability = 0
            if any(w in response_text for w in ["apply", "register"]):
                actionability += 5
            if any(w in response_text for w in ["check", "review", "portal", "eligibility"]):
                actionability += 5
            score += min(actionability, 10)

            assert score >= self.PASS_THRESHOLD, (
                f"Quality score {score} below threshold {self.PASS_THRESHOLD}"
            )

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
    async def test_no_static_guidance_returned(self, conversation_id):
        """Test that actual calls are returned, not static guidance."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])
            response_text = result.get("response", "").lower()

            # Should use search tool, not just return guidance
            has_search_tool = any("search_funding_calls" in tool for tool in tools_used)

            # If no search tool used but has "MEDIA Strand Actions Overview",
            # it's returning static guidance instead of searching
            is_static_guidance = (
                "media strand actions overview" in response_text and not has_search_tool
            )

            assert not is_static_guidance, (
                "Should search for actual calls, not return static guidance"
            )

    @pytest.mark.asyncio
    async def test_call_not_closed(self, conversation_id):
        """Test that returned calls are not closed (open or upcoming)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Check that the response doesn't indicate only closed calls
            closed_only_indicators = [
                "no open calls",
                "all calls are closed",
                "no current calls",
                "no available calls",
            ]

            is_closed_only = any(ind in response_text for ind in closed_only_indicators)

            # Should have found at least upcoming calls
            has_calls = "crea-media" in response_text or "funding opportunit" in response_text

            assert has_calls and not is_closed_only, (
                "Should return open or upcoming calls, not closed"
            )

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
            ce_indicators = [
                "creative europe",
                "crea-media",
                "crea-cult",
            ]

            has_ce = any(ind in response_text for ind in ce_indicators)
            assert has_ce, "Response should mention Creative Europe programme"
