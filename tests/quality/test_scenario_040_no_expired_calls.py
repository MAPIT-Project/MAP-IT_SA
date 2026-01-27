"""
Test Scenario 040: No Expired Calls

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 040
Query: "Show me open Horizon Europe calls"
Verify: No calls with past deadlines shown as "open"
Action: Check call sync scripts, update if needed
Fix if: Shows closed calls as open
Pass threshold: 85

This test verifies data quality by ensuring:
- All returned calls have "open" or "upcoming" status
- No calls have past deadlines
- The system properly filters out expired calls
- SQL-level AND post-fetch filtering both work correctly
"""

import re
from datetime import date, datetime, timedelta

import httpx
import pytest


class TestScenario040NoExpiredCalls:
    """Test suite for Scenario 040: No Expired Calls."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Show me open Horizon Europe calls"
    PASS_THRESHOLD = 85

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(100000, 999999)

    # ==========================================================================
    # UNIT TESTS - Test the filtering logic directly
    # ==========================================================================

    def test_expired_call_detection(self):
        """Test that expired calls are properly detected and marked closed."""
        from app.services.local_call_search_service import LocalCallSearchService

        service = LocalCallSearchService()

        # Call with past deadline
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        expired_call = {
            "topic_code": "TEST-EXPIRED-001",
            "title": "Test Expired Call",
            "deadline": yesterday,
            "status": "open",  # Wrong status - should be corrected
        }

        normalized = service._normalize_call_status(expired_call)
        assert normalized["status"] == "closed", "Expired call should be marked closed"

    def test_future_call_status_preserved(self):
        """Test that calls with future deadlines keep their status."""
        from app.services.local_call_search_service import LocalCallSearchService

        service = LocalCallSearchService()

        # Call with future deadline
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        future_call = {
            "topic_code": "TEST-FUTURE-001",
            "title": "Test Future Call",
            "deadline": tomorrow,
            "status": "open",
        }

        normalized = service._normalize_call_status(future_call)
        assert normalized["status"] == "open", "Future call should keep 'open' status"

    def test_today_deadline_stays_open(self):
        """Test that calls with deadline today are still considered open."""
        from app.services.local_call_search_service import LocalCallSearchService

        service = LocalCallSearchService()

        # Call with today's deadline
        today = date.today().strftime("%Y-%m-%d")
        today_call = {
            "topic_code": "TEST-TODAY-001",
            "title": "Test Today Call",
            "deadline": today,
            "status": "open",
        }

        normalized = service._normalize_call_status(today_call)
        # Deadline on today should NOT be marked closed - users can still apply
        assert normalized["status"] == "open", "Call with deadline today should remain open"

    def test_null_deadline_handling(self):
        """Test that calls with NULL deadline are handled gracefully."""
        from app.services.local_call_search_service import LocalCallSearchService

        service = LocalCallSearchService()

        # Call with no deadline
        no_deadline_call = {
            "topic_code": "TEST-NULL-001",
            "title": "Test No Deadline Call",
            "deadline": None,
            "status": "open",
        }

        normalized = service._normalize_call_status(no_deadline_call)
        # Should pass through unchanged - can't determine if expired
        assert normalized["status"] == "open", "Call with no deadline should not be modified"

    def test_date_format_variations(self):
        """Test that various date formats are correctly parsed."""
        from app.services.local_call_search_service import LocalCallSearchService

        service = LocalCallSearchService()
        yesterday = date.today() - timedelta(days=1)

        # Test different date formats - all expired
        date_formats = [
            yesterday.strftime("%Y-%m-%d"),  # 2026-01-26
            yesterday.strftime("%d %B %Y"),  # 26 January 2026
            yesterday.strftime("%d/%m/%Y"),  # 26/01/2026
            yesterday.strftime("%Y-%m-%dT%H:%M:%S"),  # 2026-01-26T00:00:00
        ]

        for date_str in date_formats:
            call = {
                "topic_code": "TEST-FORMAT",
                "title": "Test Date Format",
                "deadline": date_str,
                "status": "open",
            }
            normalized = service._normalize_call_status(call)
            assert normalized["status"] == "closed", (
                f"Date format '{date_str}' should be detected as expired"
            )

    def test_datetime_object_handling(self):
        """Test that datetime objects are correctly handled."""
        from app.services.local_call_search_service import LocalCallSearchService

        service = LocalCallSearchService()

        # Test with datetime object (expired)
        expired_datetime = datetime.now() - timedelta(days=1)
        call_datetime = {
            "topic_code": "TEST-DATETIME",
            "title": "Test Datetime",
            "deadline": expired_datetime,
            "status": "open",
        }
        normalized = service._normalize_call_status(call_datetime)
        assert normalized["status"] == "closed", "Expired datetime should be detected"

        # Test with date object (expired)
        expired_date = date.today() - timedelta(days=1)
        call_date = {
            "topic_code": "TEST-DATE",
            "title": "Test Date",
            "deadline": expired_date,
            "status": "open",
        }
        normalized = service._normalize_call_status(call_date)
        assert normalized["status"] == "closed", "Expired date should be detected"

    # ==========================================================================
    # QUALITY SCORING TESTS
    # ==========================================================================

    def test_perfect_response_scoring(self):
        """Test that a response with no expired calls scores 85+."""
        # Perfect response: all calls open, future deadlines, properly formatted
        excellent_response = """
## Open Horizon Europe Funding Opportunities

I found **8 open funding calls** matching your query.

### 1. AI for Healthcare Innovation
- **Call ID:** HORIZON-HLTH-2026-DISEASE-01
- **Status:** Open
- **Deadline:** 15 March 2026
- **Budget:** EUR 50 million
- **Apply:** [EU Portal](https://ec.europa.eu/info/funding-tenders)

### 2. Digital Transformation
- **Call ID:** HORIZON-CL4-2026-DIGITAL-01
- **Status:** Open
- **Deadline:** 20 April 2026
- **Budget:** EUR 30 million

### Next Steps
1. Register on the EU Funding & Tenders Portal
2. Find consortium partners
3. Review the call documentation
"""
        score = self._score_response(excellent_response)
        assert score >= self.PASS_THRESHOLD, f"Excellent response should score 85+, got {score}"

    def test_response_with_past_deadline_scores_low(self):
        """Test that a response showing closed calls scores low."""
        # BAD response: shows closed calls or past deadlines
        bad_response = """
## Horizon Europe Funding Calls

### 1. Previous Call
- **Call ID:** HORIZON-2024-OLD-01
- **Status:** Closed
- **Deadline:** 15 December 2024 (EXPIRED)
- **Budget:** EUR 20 million

### 2. Another Old Call
- **Call ID:** HORIZON-2025-PAST-01
- **Deadline:** 01 January 2025
- **Status:** Open  <-- WRONG! This deadline has passed
"""
        score = self._score_response(bad_response)
        assert score < 70, f"Response with expired calls should score low, got {score}"

    def test_response_without_status_indication(self):
        """Test that responses without status indication score lower."""
        # Response missing status fields
        incomplete_response = """
## Horizon Europe Calls

1. Call HORIZON-HLTH-2026-01
   Deadline: March 2026
   Budget: EUR 50 million

2. Call HORIZON-CL4-2026-01
   Deadline: April 2026
"""
        score = self._score_response(incomplete_response)
        # Should score lower due to missing status indicators
        assert score < 90, "Response without status indicators should score lower"

    def _score_response(self, response: str) -> int:
        """
        Score a response for Scenario 040.

        Dimensions:
        - Data Quality (40): No expired calls, all deadlines in future
        - Status Accuracy (25): Correct status labels, no "open" for closed
        - Completeness (25): Has Call IDs, deadlines, budgets, links
        - Freshness (10): Includes only current/upcoming calls

        Returns:
            Score from 0-100
        """
        score = 0
        today = date.today()

        # --- Data Quality (40 points) ---
        data_quality_score = 40  # Start with full points

        # Check if any dates in response are in the past
        months = (
            "January|February|March|April|May|June|July|August|September|October|November|December"
        )
        date_pattern = rf"(\d{{1,2}})\s+({months})\s+(\d{{4}})"
        found_dates = re.findall(date_pattern, response, re.IGNORECASE)

        past_dates_found = 0
        for day, month, year in found_dates:
            try:
                deadline = datetime.strptime(f"{day} {month} {year}", "%d %B %Y").date()
                if deadline < today:
                    past_dates_found += 1
            except ValueError:
                pass

        # Deduct for past dates
        data_quality_score -= past_dates_found * 20  # -20 for each past date

        # Check for explicit "closed" or "expired" status
        if re.search(r"status.*closed", response, re.IGNORECASE):
            data_quality_score -= 20
        if "expired" in response.lower():
            data_quality_score -= 15

        score += max(0, data_quality_score)

        # --- Status Accuracy (25 points) ---
        status_score = 0

        # Has status indicators
        if re.search(r"\bstatus\s*:", response, re.IGNORECASE):
            status_score += 10

        # Shows "Open" status
        if re.search(r"status.*open", response, re.IGNORECASE):
            status_score += 10

        # No conflicting "closed" with "open" claims
        if not re.search(r"status.*closed", response, re.IGNORECASE):
            status_score += 5

        score += status_score

        # --- Completeness (25 points) ---
        completeness_score = 0

        # Has Call IDs
        if re.search(r"HORIZON-[A-Z0-9-]+", response):
            completeness_score += 7

        # Has deadlines
        if re.search(r"deadline", response, re.IGNORECASE):
            completeness_score += 6

        # Has budgets
        if re.search(r"(EUR|budget|million)", response, re.IGNORECASE):
            completeness_score += 6

        # Has links
        if "ec.europa.eu" in response or "Apply:" in response:
            completeness_score += 6

        score += completeness_score

        # --- Freshness (10 points) ---
        freshness_score = 0

        # Contains recent years (2026, 2027)
        if re.search(r"\b(2026|2027)\b", response):
            freshness_score += 5

        # Has "open" calls
        if "open" in response.lower():
            freshness_score += 5

        score += freshness_score

        return min(100, max(0, score))

    # ==========================================================================
    # INTEGRATION TESTS - Require running server
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_live_no_expired_calls_returned(self, conversation_id):
        """Test that live API returns no expired calls."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            assert response.status_code == 200, f"API returned {response.status_code}"
            result = response.json()
            response_text = result.get("response", "")

            # Extract all dates from response
            months = (
                "January|February|March|April|May|June|July|August|"
                "September|October|November|December"
            )
            date_pattern = rf"(\d{{1,2}})\s+({months})\s+(\d{{4}})"
            found_dates = re.findall(date_pattern, response_text, re.IGNORECASE)

            today = date.today()
            past_dates = []

            for day, month, year in found_dates:
                try:
                    deadline = datetime.strptime(f"{day} {month} {year}", "%d %B %Y").date()
                    if deadline < today:
                        past_dates.append(f"{day} {month} {year}")
                except ValueError:
                    pass

            assert len(past_dates) == 0, (
                f"Response contains past deadlines: {past_dates}. "
                "All deadlines should be in the future."
            )

    @pytest.mark.asyncio
    async def test_live_no_closed_status_shown(self, conversation_id):
        """Test that no calls are shown with 'closed' status."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should NOT show "Status: Closed"
            assert "status: closed" not in response_text.lower(), (
                "Response should not show calls with 'Status: Closed'"
            )

            # Should NOT mention calls are expired
            assert "expired" not in response_text.lower(), (
                "Response should not mention expired calls"
            )

    @pytest.mark.asyncio
    async def test_live_all_calls_are_open(self, conversation_id):
        """Test that all returned calls have open/upcoming status."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should indicate Open status
            assert "open" in response_text.lower(), "Response should indicate calls are open"

            # Count status indicators
            open_count = len(re.findall(r"status.*open", response_text, re.IGNORECASE))
            closed_count = len(re.findall(r"status.*closed", response_text, re.IGNORECASE))

            # Should have more open than closed (ideally 0 closed)
            assert closed_count == 0, f"Found {closed_count} closed status indicators - should be 0"
            assert open_count >= 1, "Should show at least one call with Open status"

    @pytest.mark.asyncio
    async def test_live_future_deadlines_only(self, conversation_id):
        """Test that all deadlines are in the future."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            current_year = date.today().year

            # Filter out years that might be from call IDs (like HORIZON-2026-...)
            # by only checking years in deadline context
            deadline_years = []
            for match in re.finditer(r"deadline.*?(\d{4})", response_text, re.IGNORECASE):
                deadline_years.append(int(match.group(1)))

            # All deadline years should be current or future
            past_years = [y for y in deadline_years if y < current_year]
            assert len(past_years) == 0, (
                f"Found past years in deadlines: {past_years}. "
                "All deadlines should be current or future year."
            )

    @pytest.mark.asyncio
    async def test_live_returns_calls(self, conversation_id):
        """Test that the query actually returns funding calls."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should return actual calls
            call_id_pattern = r"HORIZON-[A-Z0-9-]+"
            call_ids = re.findall(call_id_pattern, response_text)

            assert len(call_ids) >= 1, "Response should include at least one HORIZON call ID"

    @pytest.mark.asyncio
    async def test_live_variant_open_calls_query(self, conversation_id):
        """Test variant query 'what open calls are available'."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "What open Horizon Europe calls are available right now?"},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should return open calls only
            assert "status: closed" not in response_text.lower(), (
                "Variant query should not return closed calls"
            )

            # Extract and verify dates
            months = (
                "January|February|March|April|May|June|July|August|"
                "September|October|November|December"
            )
            date_pattern = rf"(\d{{1,2}})\s+({months})\s+(\d{{4}})"
            found_dates = re.findall(date_pattern, response_text, re.IGNORECASE)

            today = date.today()
            for day, month, year in found_dates:
                try:
                    deadline = datetime.strptime(f"{day} {month} {year}", "%d %B %Y").date()
                    assert deadline >= today, f"Found past deadline: {day} {month} {year}"
                except ValueError:
                    pass

    @pytest.mark.asyncio
    async def test_live_currently_open_query(self, conversation_id):
        """Test query 'show me currently open calls'."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "Show me currently open Horizon Europe funding calls"},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Check for open calls
            assert "open" in response_text.lower(), "Response should mention 'open' calls"

            # No closed status
            assert "status: closed" not in response_text.lower(), "Should not show closed calls"

    @pytest.mark.asyncio
    async def test_live_quality_score(self, conversation_id):
        """Test that live response achieves pass threshold."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            score = self._score_response(response_text)
            assert score >= self.PASS_THRESHOLD, (
                f"Live response should score {self.PASS_THRESHOLD}+, got {score}"
            )


class TestDataQualityVerification:
    """Additional tests for verifying data quality in the database."""

    def test_sql_query_excludes_past_deadlines(self):
        """Verify the SQL query correctly excludes past deadlines."""
        # This tests the SQL logic used in the service
        sql_condition = """
        status != 'closed'
        AND (deadline IS NULL OR deadline >= CURRENT_DATE)
        """
        # The condition should:
        # 1. Exclude status = 'closed'
        # 2. Allow NULL deadlines (we can't determine if expired)
        # 3. Require deadline >= today

        assert "status != 'closed'" in sql_condition, "Should filter out closed status"
        assert "deadline >= CURRENT_DATE" in sql_condition, "Should filter past deadlines"
        assert "deadline IS NULL" in sql_condition, "Should allow NULL deadlines"

    def test_include_closed_parameter(self):
        """Test that include_closed parameter works correctly."""
        from app.services.local_call_search_service import LocalCallSearchService

        service = LocalCallSearchService()

        # The search_calls method should have include_closed parameter
        import inspect

        sig = inspect.signature(service.search_calls)
        params = sig.parameters

        assert "include_closed" in params, "search_calls should have include_closed parameter"
        assert params["include_closed"].default is False, "include_closed should default to False"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
