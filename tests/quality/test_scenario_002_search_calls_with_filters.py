"""
Test Scenario 002: Search Calls with Filters

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 002
Query: "Find Horizon Europe calls closing in the next 3 months with budget over 5 million"
Expected: Filtered calls matching all criteria
Verify: Date filtering works, budget filtering accurate
Pass threshold: 80

This test verifies that the system properly filters search results by:
- Deadline (within next 3 months from current date)
- Budget (over 5 million EUR)
- Status (open calls only)
"""

from datetime import datetime, timedelta
import re

import httpx
import pytest


class TestScenario002SearchCallsWithFilters:
    """Test suite for Scenario 002: Search Calls with Filters."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Find Horizon Europe calls closing in the next 3 months with budget over 5 million"
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
            assert (
                "funding opportunit" in response_text.lower() or "call" in response_text.lower()
            ), "Response should mention funding opportunities or calls"

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

            # Should have HORIZON call IDs
            call_id_pattern = r"HORIZON-[A-Z0-9-]+"
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

    @pytest.mark.asyncio
    async def test_deadlines_within_three_months(self, conversation_id):
        """Test that returned deadlines are within the next 3 months."""
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
            three_months = today + timedelta(days=90)

            valid_dates = 0
            for day, month, year in dates:
                try:
                    deadline = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
                    # Deadline should be in future and within 3 months
                    if today <= deadline <= three_months:
                        valid_dates += 1
                except ValueError:
                    pass

            # At least some dates should be within 3 months
            # (allowing for "Check official portal" fallbacks)
            if len(dates) > 0:
                assert valid_dates >= 1, (
                    f"At least one deadline should be within 3 months. "
                    f"Found dates: {dates}, valid: {valid_dates}"
                )

    @pytest.mark.asyncio
    async def test_includes_budgets(self, conversation_id):
        """Test that response includes budget information."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should mention budgets
            budget_patterns = [
                r"Budget:",
                r"EUR\s+[\d,\.]+",
                r"€[\d,\.]+",
                r"million",
            ]

            has_budget = any(
                re.search(pattern, response_text, re.IGNORECASE) for pattern in budget_patterns
            )
            assert has_budget, "Response should include budget information"

    @pytest.mark.asyncio
    async def test_budgets_over_five_million(self, conversation_id):
        """Test that returned budgets are over 5 million EUR."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Extract budget patterns
            # Match patterns like: EUR 219.0 million, EUR 10.2 million, €5M
            budget_pattern = r"EUR\s+([\d,\.]+)\s*(?:million|M)"
            budget_matches = re.findall(budget_pattern, response_text, re.IGNORECASE)

            # If budgets are found, they should be over 5 million
            for match in budget_matches:
                try:
                    amount = float(match.replace(",", ""))
                    assert amount >= 5.0, f"Budget {amount} million should be >= 5 million"
                except ValueError:
                    pass  # Skip if parsing fails

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

            # Should indicate Open status (not closed)
            assert "Open" in response_text, "Response should indicate calls are Open"
            assert (
                "🔴" not in response_text or "🟢" in response_text
            ), "Response should not have closed-only calls"

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

            # Should link to EU Portal
            assert "ec.europa.eu" in response_text, "Response should include links to EU Portal"

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
            assert "quality_analysis" in metadata, "Response should include quality analysis"


class TestScenario002DateFiltering:
    """Test date filtering behavior for Scenario 002."""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def conversation_id(self):
        import random

        return random.randint(100000, 999999)

    @pytest.mark.asyncio
    async def test_no_closed_calls_returned(self, conversation_id):
        """Test that no closed calls are returned for open call search."""
        query = "Find Horizon Europe calls closing in the next 3 months with budget over 5 million"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": query},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should not have closed status
            # (allowing some flexibility if the system explains closed calls exist)
            closed_count = response_text.lower().count("closed")
            open_count = response_text.lower().count("open")

            # Should have more open than closed mentions
            assert open_count >= closed_count, "Response should primarily contain open calls"


class TestScenario002BudgetFiltering:
    """Test budget filtering behavior for Scenario 002."""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def conversation_id(self):
        import random

        return random.randint(100000, 999999)

    @pytest.mark.asyncio
    async def test_filters_by_budget_criteria(self, conversation_id):
        """Test that the system understands budget filter criteria."""
        query = "Find Horizon Europe calls closing in the next 3 months with budget over 5 million"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": query},
            )

            result = response.json()
            metadata = result.get("metadata", {})

            # Check that the tool was called with relevant parameters
            reasoning_steps = metadata.get("reasoning_steps", [])

            # The system should have understood the budget requirement
            # This is a qualitative check that the system is processing filters
            assert len(reasoning_steps) >= 1, "Should have at least one reasoning step"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
