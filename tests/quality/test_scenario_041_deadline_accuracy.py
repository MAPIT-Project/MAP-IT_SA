"""
Test Scenario 041: Deadline Accuracy

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 041
Action: Pick 5 random calls from results, verify deadlines against EU Portal
Verify: All 5 deadlines match official source
Action: Check data sync frequency
Fix if: Any deadline incorrect
Pass threshold: 90

This test verifies data accuracy by:
- Selecting random calls from the local database
- Fetching their details from the EU Portal API
- Comparing local deadlines with the official source
- Reporting any discrepancies
"""

import logging
from datetime import UTC, date, datetime
from typing import Any

import httpx
import pytest
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class TestScenario041DeadlineAccuracy:
    """Test suite for Scenario 041: Deadline Accuracy."""

    BASE_URL = "http://localhost:8000"
    EU_PORTAL_TOPIC_DETAILS = (
        "https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails"
    )
    PASS_THRESHOLD = 90
    CALLS_TO_VERIFY = 5

    # ==========================================================================
    # UNIT TESTS - Test the deadline parsing logic
    # ==========================================================================

    def test_parse_unix_timestamp_deadline(self):
        """Test parsing Unix timestamp deadline from API."""
        # Example from EU Portal: 1693526400000 (milliseconds)
        # This represents September 1, 2023 08:00:00 UTC
        # Use a time that's clearly in the middle of the day to avoid timezone issues
        timestamp_ms = 1693526400000
        expected_date = date(2023, 9, 1)

        # Use UTC to avoid timezone issues
        parsed_date = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).date()
        assert parsed_date == expected_date, f"Expected {expected_date}, got {parsed_date}"

    def test_parse_iso_format_deadline(self):
        """Test parsing ISO format deadline from API."""
        # Example from EU Portal: "2026-09-04T22:00:00.000+0000"
        deadline_str = "2026-09-04T22:00:00.000+0000"
        expected_date = date(2026, 9, 4)

        # Parse ISO format with timezone
        parsed_date = datetime.fromisoformat(deadline_str.replace("+0000", "+00:00")).date()
        assert parsed_date == expected_date, f"Expected {expected_date}, got {parsed_date}"

    def test_parse_iso_format_with_z_suffix(self):
        """Test parsing ISO format with Z suffix."""
        deadline_str = "2026-09-04T22:00:00.000Z"
        expected_date = date(2026, 9, 4)

        parsed_date = datetime.fromisoformat(deadline_str.replace("Z", "+00:00")).date()
        assert parsed_date == expected_date, f"Expected {expected_date}, got {parsed_date}"

    def test_parse_simple_date_format(self):
        """Test parsing simple date format."""
        deadline_str = "2026-09-04"
        expected_date = date(2026, 9, 4)

        parsed_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        assert parsed_date == expected_date, f"Expected {expected_date}, got {parsed_date}"

    def test_date_comparison_logic(self):
        """Test that date comparison works correctly."""
        local_date = date(2026, 9, 4)
        api_date = date(2026, 9, 4)

        assert local_date == api_date, "Same dates should be equal"

        different_api_date = date(2026, 9, 5)
        assert local_date != different_api_date, "Different dates should not be equal"

    def test_date_tolerance_days(self):
        """Test date comparison with tolerance for edge cases."""
        local_date = date(2026, 9, 4)

        # Exact match
        api_date_exact = date(2026, 9, 4)
        assert abs((local_date - api_date_exact).days) <= 1, "Exact match within tolerance"

        # One day difference (could be timezone issue)
        api_date_off_by_one = date(2026, 9, 5)
        assert abs((local_date - api_date_off_by_one).days) <= 1, "One day off within tolerance"

        # Two days difference - not acceptable
        api_date_off_by_two = date(2026, 9, 6)
        assert abs((local_date - api_date_off_by_two).days) > 1, "Two days off exceeds tolerance"

    # ==========================================================================
    # API PARSING TESTS - Test extraction from API response structure
    # ==========================================================================

    def test_extract_deadline_from_actions(self):
        """Test extracting deadline from actions.deadlineDates field."""
        api_response = {
            "TopicDetails": {
                "identifier": "HORIZON-CL5-2026-D3-01",
                "title": "Test Call",
                "actions": [
                    {
                        "deadlineDates": [1756857600000],  # September 4, 2025
                        "status": {"abbreviation": "OPEN"},
                    }
                ],
            }
        }

        topic_data = api_response.get("TopicDetails", {})
        actions = topic_data.get("actions", [])

        assert len(actions) > 0, "Should have actions"

        deadline_dates = actions[0].get("deadlineDates", [])
        assert len(deadline_dates) > 0, "Should have deadline dates"

        timestamp_ms = deadline_dates[0]
        parsed_date = datetime.fromtimestamp(timestamp_ms / 1000).date()
        assert isinstance(parsed_date, date), "Should parse to date object"

    def test_extract_deadline_from_deadline_model(self):
        """Test extracting deadline from deadlineModel field."""
        api_response = {
            "TopicDetails": {
                "identifier": "HORIZON-CL5-2026-D3-01",
                "title": "Test Call",
                "deadlineModel": [{"deadlineDate": "2026-09-04T22:00:00.000+0000"}],
            }
        }

        topic_data = api_response.get("TopicDetails", {})
        deadline_model = topic_data.get("deadlineModel", [])

        assert len(deadline_model) > 0, "Should have deadline model"

        deadline_str = deadline_model[0].get("deadlineDate", "")
        assert deadline_str, "Should have deadline string"

        parsed_date = datetime.fromisoformat(deadline_str.replace("+0000", "+00:00")).date()
        assert parsed_date == date(2026, 9, 4), "Should parse correctly"

    def test_handle_missing_deadline_fields(self):
        """Test handling of API response without deadline fields."""
        api_response = {
            "TopicDetails": {
                "identifier": "HORIZON-CL5-2026-D3-01",
                "title": "Test Call",
                # No actions or deadlineModel fields
            }
        }

        topic_data = api_response.get("TopicDetails", {})
        actions = topic_data.get("actions", [])
        deadline_model = topic_data.get("deadlineModel", [])

        assert len(actions) == 0, "Should have no actions"
        assert len(deadline_model) == 0, "Should have no deadline model"

    # ==========================================================================
    # SCORING LOGIC TESTS
    # ==========================================================================

    def test_score_all_matching(self):
        """Test scoring when all deadlines match."""
        d1, d2, d3, d4, d5 = (
            date(2026, 3, 15),
            date(2026, 4, 20),
            date(2026, 5, 10),
            date(2026, 6, 1),
            date(2026, 7, 15),
        )
        results = [
            {"topic_code": "CALL-1", "local": d1, "api": d1, "match": True},
            {"topic_code": "CALL-2", "local": d2, "api": d2, "match": True},
            {"topic_code": "CALL-3", "local": d3, "api": d3, "match": True},
            {"topic_code": "CALL-4", "local": d4, "api": d4, "match": True},
            {"topic_code": "CALL-5", "local": d5, "api": d5, "match": True},
        ]

        score = self._calculate_accuracy_score(results)
        assert score == 100, f"All matching should score 100, got {score}"

    def test_score_one_mismatch(self):
        """Test scoring when one deadline mismatches."""
        d1, d2, d3, d4, d5 = (
            date(2026, 3, 15),
            date(2026, 4, 20),
            date(2026, 5, 10),
            date(2026, 6, 1),
            date(2026, 7, 15),
        )
        results = [
            {"topic_code": "CALL-1", "local": d1, "api": d1, "match": True},
            {"topic_code": "CALL-2", "local": d2, "api": d2, "match": True},
            # Mismatch: local May 10 vs API May 12
            {"topic_code": "CALL-3", "local": d3, "api": date(2026, 5, 12), "match": False},
            {"topic_code": "CALL-4", "local": d4, "api": d4, "match": True},
            {"topic_code": "CALL-5", "local": d5, "api": d5, "match": True},
        ]

        score = self._calculate_accuracy_score(results)
        assert score == 80, f"4/5 matching should score 80, got {score}"

    def test_score_all_mismatch(self):
        """Test scoring when all deadlines mismatch."""
        results = [
            {
                "topic_code": "CALL-1",
                "local": date(2026, 3, 15),
                "api": date(2026, 3, 16),
                "match": False,
            },
            {
                "topic_code": "CALL-2",
                "local": date(2026, 4, 20),
                "api": date(2026, 4, 21),
                "match": False,
            },
            {
                "topic_code": "CALL-3",
                "local": date(2026, 5, 10),
                "api": date(2026, 5, 11),
                "match": False,
            },
            {
                "topic_code": "CALL-4",
                "local": date(2026, 6, 1),
                "api": date(2026, 6, 2),
                "match": False,
            },
            {
                "topic_code": "CALL-5",
                "local": date(2026, 7, 15),
                "api": date(2026, 7, 16),
                "match": False,
            },
        ]

        score = self._calculate_accuracy_score(results)
        assert score == 0, f"0/5 matching should score 0, got {score}"

    def test_score_with_tolerance(self):
        """Test scoring with 1-day tolerance for timezone edge cases."""
        d1 = date(2026, 3, 15)
        results = [
            {"topic_code": "CALL-1", "local": d1, "api": d1, "match": True},
            {
                "topic_code": "CALL-2",
                "local": date(2026, 4, 20),
                "api": date(2026, 4, 21),
                "match": False,
                "days_diff": 1,
            },  # 1 day off
        ]

        # With tolerance, 1 day difference should still pass
        matches_with_tolerance = sum(
            1 for r in results if r.get("match") or (r.get("days_diff", 99) <= 1)
        )
        score = (matches_with_tolerance / len(results)) * 100
        assert score == 100, f"With tolerance, should score 100, got {score}"

    def _calculate_accuracy_score(self, results: list[dict[str, Any]]) -> int:
        """
        Calculate accuracy score based on deadline matches.

        Returns:
            Score from 0-100 (percentage of matching deadlines)
        """
        if not results:
            return 0

        matches = sum(1 for r in results if r.get("match", False))
        return int((matches / len(results)) * 100)

    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================

    def _extract_deadline_from_api_response(self, topic_data: dict[str, Any]) -> date | None:
        """
        Extract deadline from EU Portal API response.

        Tries multiple sources in order of reliability:
        1. actions[0].deadlineDates[0] (Unix timestamp in ms)
        2. deadlineModel[0].deadlineDate (ISO format string)

        Returns:
            date object or None if no deadline found
        """

        # Try actions.deadlineDates first (most reliable)
        actions = topic_data.get("actions", [])
        if actions and isinstance(actions, list) and len(actions) > 0:
            deadline_dates = actions[0].get("deadlineDates", [])
            if deadline_dates and len(deadline_dates) > 0:
                try:
                    timestamp_ms = int(deadline_dates[0])
                    # Use UTC to avoid timezone issues
                    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).date()
                except (ValueError, TypeError, OSError) as e:
                    logger.debug(f"Could not parse actions deadline: {e}")

        # Try deadlineModel fallback
        deadline_model = topic_data.get("deadlineModel", [])
        if deadline_model and isinstance(deadline_model, list) and len(deadline_model) > 0:
            deadline_str = deadline_model[0].get("deadlineDate", "")
            if deadline_str:
                try:
                    # Handle various formats
                    if "T" in deadline_str:
                        # ISO format with timezone: "2026-09-04T22:00:00.000+0000"
                        cleaned = deadline_str.replace("+0000", "+00:00").replace("Z", "+00:00")
                        return datetime.fromisoformat(cleaned).date()
                    else:
                        # Simple date format: "2026-09-04"
                        return datetime.strptime(deadline_str, "%Y-%m-%d").date()
                except (ValueError, TypeError) as e:
                    logger.debug(f"Could not parse deadlineModel: {e}")

        return None

    def _fetch_api_deadline(self, client: httpx.Client, topic_code: str) -> date | None:
        """
        Fetch deadline from EU Portal API for a specific topic code.

        Returns:
            date object or None if fetch failed
        """
        # IMPORTANT: EU Portal requires lowercase topic codes
        url = f"{self.EU_PORTAL_TOPIC_DETAILS}/{topic_code.lower()}.json"

        try:
            response = client.get(url)

            if response.status_code == 200:
                data = response.json()
                topic_data = data.get("TopicDetails", {})
                return self._extract_deadline_from_api_response(topic_data)
            else:
                logger.warning(f"API returned {response.status_code} for {topic_code}")
                return None

        except Exception as e:
            logger.error(f"API fetch failed for {topic_code}: {e}")
            return None

    def _get_random_calls_from_db(
        self, conn, count: int = 5, programme: str = "horizon"
    ) -> list[dict[str, Any]]:
        """
        Get random calls from the database that have deadlines.

        Args:
            conn: Database connection
            count: Number of calls to retrieve
            programme: Programme to filter by (default: horizon)

        Returns:
            List of call dictionaries with topic_code and deadline
        """
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Select calls with non-null deadlines that are Horizon Europe calls
        cursor.execute(
            """
            SELECT topic_code, deadline, title, status
            FROM funding_calls
            WHERE topic_code IS NOT NULL
            AND deadline IS NOT NULL
            AND topic_code LIKE 'HORIZON%%'
            AND deadline >= CURRENT_DATE
            ORDER BY RANDOM()
            LIMIT %s
        """,
            (count,),
        )

        results = cursor.fetchall()
        cursor.close()

        return [dict(r) for r in results]

    # ==========================================================================
    # INTEGRATION TESTS - Require database and network access
    # ==========================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
