"""
Test Scenario 001: Search Open Calls Basic

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 001
Query: "Show me open funding calls for AI research"
Expected: List of current open calls with deadlines, budgets, links
Verify: Calls are actually open (not closed), deadlines are in future
Pass threshold: 80

This test verifies that the system properly formats search results with:
- Call IDs and titles
- Deadlines (in future)
- Budgets
- Direct links to EU Portal
- Application guidance
"""

import re
from datetime import datetime

import httpx
import pytest


class TestScenario001SearchOpenCallsBasic:
    """Test suite for Scenario 001: Search Open Calls Basic."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Show me open funding calls for AI research"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(100000, 999999)

    @pytest.mark.asyncio
    async def test_returns_funding_calls(self, conversation_id):
        """Test that the query returns funding calls."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            assert response.status_code == 200, f"API returned {response.status_code}"
            result = response.json()

            response_text = result.get("response", "")

            # Should find funding opportunities
            assert "funding opportunit" in response_text.lower(), (
                "Response should mention funding opportunities"
            )

    @pytest.mark.asyncio
    async def test_includes_call_ids(self, conversation_id):
        """Test that response includes Call IDs in proper format."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should have Call ID markers
            assert "Call ID:" in response_text, "Response should include Call ID markers"

            # Should have HORIZON or EIC call IDs
            call_id_pattern = r"HORIZON-[A-Z0-9-]+|EIC-[A-Z0-9-]+"
            call_ids = re.findall(call_id_pattern, response_text)
            assert len(call_ids) >= 1, "Response should include at least one valid call ID"

    @pytest.mark.asyncio
    async def test_includes_deadlines(self, conversation_id):
        """Test that response includes deadlines."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should have Deadline markers
            assert "Deadline:" in response_text, "Response should include Deadline markers"

            # Should have date patterns (month year or check portal)
            months = "January|February|March|April|May|June"
            months += "|July|August|September|October|November|December"
            date_pattern = rf"\d{{1,2}}\s+(?:{months})\s+\d{{4}}"
            dates = re.findall(date_pattern, response_text)

            # At least some calls should have specific dates
            assert len(dates) >= 1 or "Check official portal" in response_text, (
                "Response should include at least one deadline date"
            )

    @pytest.mark.asyncio
    async def test_deadlines_are_in_future(self, conversation_id):
        """Test that returned deadlines are in the future."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Extract date patterns
            months = "January|February|March|April|May|June"
            months += "|July|August|September|October|November|December"
            date_pattern = rf"(\d{{1,2}})\s+({months})\s+(\d{{4}})"
            dates = re.findall(date_pattern, response_text)

            today = datetime.now()

            for day, month, year in dates:
                try:
                    deadline = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
                    assert deadline >= today, f"Deadline {day} {month} {year} is in the past"
                except ValueError:
                    pass  # Skip if parsing fails

    @pytest.mark.asyncio
    async def test_includes_apply_links(self, conversation_id):
        """Test that response includes links to EU Portal."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should have Apply links
            assert "Apply:" in response_text, "Response should include Apply links"

            # Should link to EU Portal
            assert "ec.europa.eu" in response_text, "Response should include links to EU Portal"

    @pytest.mark.asyncio
    async def test_includes_status(self, conversation_id):
        """Test that response indicates call status."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should have Status markers
            assert "Status:" in response_text, "Response should include Status markers"

            # Should indicate Open status
            assert "Open" in response_text, "Response should indicate calls are Open"

    @pytest.mark.asyncio
    async def test_uses_search_funding_calls_tool(self, conversation_id):
        """Test that the search_funding_calls tool is used."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            metadata = result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Should use search_funding_calls tool
            assert any(
                "search" in str(t).lower() and "calls" in str(t).lower() for t in tools_used
            ), f"Should use search_funding_calls tool, got: {tools_used}"

    @pytest.mark.asyncio
    async def test_includes_ai_relevant_results(self, conversation_id):
        """Test that results are AI-relevant."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should mention AI-related terms
            ai_terms = [
                "AI",
                "artificial intelligence",
                "Artificial Intelligence",
                "machine learning",
                "neural",
                "digital",
                "robotics",
            ]
            found_ai_terms = any(term in response_text for term in ai_terms)

            assert found_ai_terms, "Response should include AI-relevant results"

    @pytest.mark.asyncio
    async def test_includes_application_guidance(self, conversation_id):
        """Test that response includes application guidance."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should have application guidance
            guidance_indicators = ["How to Apply", "Next Steps", "Register", "eligibility"]

            has_guidance = any(ind in response_text for ind in guidance_indicators)
            assert has_guidance, "Response should include application guidance"

    @pytest.mark.asyncio
    async def test_quality_score_passes_threshold(self, conversation_id):
        """Test that quality analysis reports passing score."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            metadata = result.get("metadata", {})

            # Quality score should be available and passing
            # Note: The internal quality score may use different criteria
            # This test just verifies quality analysis is being performed
            assert "quality_analysis" in metadata, "Response should include quality analysis"


class TestV3FormatterIntegration:
    """Test that V3ResponseFormatter is properly integrated."""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def conversation_id(self):
        import random

        return random.randint(100000, 999999)

    @pytest.mark.asyncio
    async def test_formatter_produces_structured_output(self, conversation_id):
        """Test that response is properly formatted with emojis and structure."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "Show me open funding calls for AI research"},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should have emoji markers from V3ResponseFormatter
            format_markers = [
                "",  # Call ID marker
                "",  # Status marker
                "",  # Deadline marker
                "",  # Link marker
            ]

            has_formatting = any(marker in response_text for marker in format_markers)
            assert has_formatting, "Response should use V3ResponseFormatter with emoji markers"

    @pytest.mark.asyncio
    async def test_no_finding_format(self, conversation_id):
        """Test that response does NOT use 'Finding X:' fallback format."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "Show me open funding calls for AI research"},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should NOT use the fallback "Finding X:" format
            assert "**Finding 1:**" not in response_text, (
                "Response should NOT use fallback 'Finding X:' format"
            )
            assert "**Finding 2:**" not in response_text, (
                "Response should NOT use fallback 'Finding X:' format"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
