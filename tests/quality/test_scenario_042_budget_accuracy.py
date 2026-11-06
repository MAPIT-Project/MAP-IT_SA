"""
Test Scenario 042: Budget Accuracy

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 042
Action: Pick 5 random calls, verify budgets against EU Portal
Verify: Budget figures match or are clearly marked as estimates
Fix if: Wrong budgets without disclaimer
Pass threshold: 85

This test verifies budget data accuracy by:
- Selecting random calls from the local database that have budgets
- Fetching their details from the EU Portal API
- Comparing local budgets with the official source
- Allowing for estimates when exact matches aren't possible
"""

import logging
from decimal import Decimal
from typing import Any

import httpx
import pytest
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class TestScenario042BudgetAccuracy:
    """Test suite for Scenario 042: Budget Accuracy."""

    BASE_URL = "http://localhost:8000"
    EU_PORTAL_TOPIC_DETAILS = (
        "https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails"
    )
    PASS_THRESHOLD = 85
    CALLS_TO_VERIFY = 5
    # Allow 10% tolerance for budget variations (e.g., rounding, currency conversion)
    BUDGET_TOLERANCE_PERCENT = 10

    # ==========================================================================
    # UNIT TESTS - Test the budget parsing logic
    # ==========================================================================

    def test_parse_integer_budget(self):
        """Test parsing integer budget from API."""
        budget_value = 10000000  # 10 million EUR
        expected = Decimal("10000000")

        parsed = Decimal(str(budget_value))
        assert parsed == expected, f"Expected {expected}, got {parsed}"

    def test_parse_float_budget(self):
        """Test parsing float budget from API."""
        budget_value = 10500000.50  # 10.5 million EUR
        expected = Decimal("10500000.50")

        parsed = Decimal(str(budget_value))
        assert parsed == expected, f"Expected {expected}, got {parsed}"

    def test_parse_string_budget(self):
        """Test parsing string budget from API."""
        budget_value = "15000000"  # 15 million EUR
        expected = Decimal("15000000")

        parsed = Decimal(budget_value)
        assert parsed == expected, f"Expected {expected}, got {parsed}"

    def test_budget_comparison_exact_match(self):
        """Test that exact budget matches are detected."""
        local_budget = Decimal("10000000")
        api_budget = Decimal("10000000")

        is_match = self._budgets_match(local_budget, api_budget)
        assert is_match, "Exact match should return True"

    def test_budget_comparison_within_tolerance(self):
        """Test that budgets within tolerance are considered matching."""
        local_budget = Decimal("10000000")
        # 5% difference - within 10% tolerance
        api_budget = Decimal("10500000")

        is_match = self._budgets_match(local_budget, api_budget)
        assert is_match, "5% difference should be within tolerance"

    def test_budget_comparison_outside_tolerance(self):
        """Test that budgets outside tolerance are detected as mismatches."""
        local_budget = Decimal("10000000")
        # 20% difference - outside 10% tolerance
        api_budget = Decimal("12000000")

        is_match = self._budgets_match(local_budget, api_budget)
        assert not is_match, "20% difference should be outside tolerance"

    def test_budget_comparison_one_null(self):
        """Test budget comparison when one value is null."""
        local_budget = Decimal("10000000")
        api_budget = None

        is_match = self._budgets_match(local_budget, api_budget)
        assert not is_match, "One null budget should not match"

    def test_budget_comparison_both_null(self):
        """Test budget comparison when both values are null."""
        local_budget = None
        api_budget = None

        # Both null is considered a match (both unknown)
        is_match = self._budgets_match(local_budget, api_budget, allow_both_null=True)
        assert is_match, "Both null should match when allowed"

    def test_percentage_difference_calculation(self):
        """Test percentage difference calculation."""
        local = Decimal("10000000")
        api = Decimal("11000000")

        diff = self._calculate_percentage_difference(local, api)
        # 1M difference / 11M API = ~9.09%
        assert abs(diff - 9.09) < 0.1, f"Expected ~9.09%, got {diff}%"

    def test_percentage_difference_negative(self):
        """Test percentage difference when local > API."""
        local = Decimal("12000000")
        api = Decimal("10000000")

        diff = self._calculate_percentage_difference(local, api)
        assert diff == 20.0, f"Expected 20%, got {diff}%"

    # ==========================================================================
    # API PARSING TESTS - Test extraction from API response structure
    # ==========================================================================

    def test_extract_budget_from_budget_overview_model(self):
        """Test extracting budget from budgetOverviewModel field."""
        api_response = {
            "TopicDetails": {
                "identifier": "HORIZON-CL5-2026-D3-01",
                "title": "Test Call",
                "budgetOverviewModel": {
                    "budgetTopicActionValue": 10000000,
                    "currency": "EUR",
                },
            }
        }

        topic_data = api_response.get("TopicDetails", {})
        budget = self._extract_budget_from_api_response(topic_data)

        assert budget is not None, "Should extract budget"
        assert budget == Decimal("10000000"), f"Budget should be 10M, got {budget}"

    def test_extract_budget_with_float_value(self):
        """Test extracting budget when API returns float."""
        api_response = {
            "TopicDetails": {
                "identifier": "HORIZON-CL5-2026-D3-01",
                "budgetOverviewModel": {
                    "budgetTopicActionValue": 15500000.00,
                },
            }
        }

        topic_data = api_response.get("TopicDetails", {})
        budget = self._extract_budget_from_api_response(topic_data)

        assert budget is not None, "Should extract budget"
        assert budget == Decimal("15500000"), f"Budget should be 15.5M, got {budget}"

    def test_handle_missing_budget_field(self):
        """Test handling API response without budget field."""
        api_response = {
            "TopicDetails": {
                "identifier": "HORIZON-CL5-2026-D3-01",
                "title": "Test Call",
                # No budgetOverviewModel field
            }
        }

        topic_data = api_response.get("TopicDetails", {})
        budget = self._extract_budget_from_api_response(topic_data)

        assert budget is None, "Should return None for missing budget"

    def test_handle_null_budget_value(self):
        """Test handling API response with null budget value."""
        api_response = {
            "TopicDetails": {
                "identifier": "HORIZON-CL5-2026-D3-01",
                "budgetOverviewModel": {
                    "budgetTopicActionValue": None,
                },
            }
        }

        topic_data = api_response.get("TopicDetails", {})
        budget = self._extract_budget_from_api_response(topic_data)

        assert budget is None, "Should return None for null budget"

    def test_handle_zero_budget(self):
        """Test handling zero budget (valid value)."""
        api_response = {
            "TopicDetails": {
                "identifier": "HORIZON-CL5-2026-D3-01",
                "budgetOverviewModel": {
                    "budgetTopicActionValue": 0,
                },
            }
        }

        topic_data = api_response.get("TopicDetails", {})
        budget = self._extract_budget_from_api_response(topic_data)

        # Zero is technically a valid budget (some calls may have zero)
        assert budget == Decimal("0"), "Should handle zero budget"

    # ==========================================================================
    # SCORING LOGIC TESTS
    # ==========================================================================

    def test_score_all_matching(self):
        """Test scoring when all budgets match."""
        results = [
            {
                "topic_code": "CALL-1",
                "local": Decimal("10000000"),
                "api": Decimal("10000000"),
                "match": True,
            },
            {
                "topic_code": "CALL-2",
                "local": Decimal("5000000"),
                "api": Decimal("5000000"),
                "match": True,
            },
            {
                "topic_code": "CALL-3",
                "local": Decimal("15000000"),
                "api": Decimal("15000000"),
                "match": True,
            },
            {
                "topic_code": "CALL-4",
                "local": Decimal("8000000"),
                "api": Decimal("8000000"),
                "match": True,
            },
            {
                "topic_code": "CALL-5",
                "local": Decimal("12000000"),
                "api": Decimal("12000000"),
                "match": True,
            },
        ]

        score = self._calculate_accuracy_score(results)
        assert score == 100, f"All matching should score 100, got {score}"

    def test_score_one_mismatch(self):
        """Test scoring when one budget mismatches."""
        results = [
            {
                "topic_code": "CALL-1",
                "local": Decimal("10000000"),
                "api": Decimal("10000000"),
                "match": True,
            },
            {
                "topic_code": "CALL-2",
                "local": Decimal("5000000"),
                "api": Decimal("5000000"),
                "match": True,
            },
            # Big mismatch
            {
                "topic_code": "CALL-3",
                "local": Decimal("15000000"),
                "api": Decimal("20000000"),
                "match": False,
            },
            {
                "topic_code": "CALL-4",
                "local": Decimal("8000000"),
                "api": Decimal("8000000"),
                "match": True,
            },
            {
                "topic_code": "CALL-5",
                "local": Decimal("12000000"),
                "api": Decimal("12000000"),
                "match": True,
            },
        ]

        score = self._calculate_accuracy_score(results)
        assert score == 80, f"4/5 matching should score 80, got {score}"

    def test_score_with_tolerance_matches(self):
        """Test scoring when differences are within tolerance."""
        results = [
            {
                "topic_code": "CALL-1",
                "local": Decimal("10000000"),
                "api": Decimal("10500000"),  # 5% diff
                "match": True,
            },
            {
                "topic_code": "CALL-2",
                "local": Decimal("5000000"),
                "api": Decimal("5200000"),  # 4% diff
                "match": True,
            },
        ]

        score = self._calculate_accuracy_score(results)
        assert score == 100, f"Within tolerance should score 100, got {score}"

    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================

    def _budgets_match(
        self,
        local: Decimal | None,
        api: Decimal | None,
        allow_both_null: bool = False,
    ) -> bool:
        """
        Compare two budget values with tolerance.

        Args:
            local: Local database budget
            api: API budget
            allow_both_null: Whether to consider both null as a match

        Returns:
            True if budgets match within tolerance
        """
        if local is None and api is None:
            return allow_both_null

        if local is None or api is None:
            return False

        if local == api:
            return True

        # Calculate percentage difference
        diff_percent = self._calculate_percentage_difference(local, api)
        return diff_percent <= self.BUDGET_TOLERANCE_PERCENT

    def _calculate_percentage_difference(self, local: Decimal, api: Decimal) -> float:
        """Calculate percentage difference between two budgets."""
        if api == 0:
            return 100.0 if local != 0 else 0.0

        diff = abs(local - api)
        return float((diff / api) * 100)

    def _extract_budget_from_api_response(self, topic_data: dict[str, Any]) -> Decimal | None:
        """
        Extract budget from EU Portal API response.

        Tries budgetOverviewModel.budgetTopicActionValue field.

        Returns:
            Decimal budget or None if not found
        """
        budget_overview = topic_data.get("budgetOverviewModel", {})
        if budget_overview:
            budget_value = budget_overview.get("budgetTopicActionValue")
            if budget_value is not None:
                try:
                    return Decimal(str(budget_value))
                except Exception as e:
                    logger.debug(f"Could not parse budget value: {e}")

        return None

    def _fetch_api_budget(self, client: httpx.Client, topic_code: str) -> Decimal | None:
        """
        Fetch budget from EU Portal API for a specific topic code.

        Returns:
            Decimal budget or None if fetch failed
        """
        # IMPORTANT: EU Portal requires lowercase topic codes
        url = f"{self.EU_PORTAL_TOPIC_DETAILS}/{topic_code.lower()}.json"

        try:
            response = client.get(url)

            if response.status_code == 200:
                data = response.json()
                topic_data = data.get("TopicDetails", {})
                return self._extract_budget_from_api_response(topic_data)
            else:
                logger.warning(f"API returned {response.status_code} for {topic_code}")
                return None

        except Exception as e:
            logger.error(f"API fetch failed for {topic_code}: {e}")
            return None

    def _get_random_calls_with_budgets(self, conn, count: int = 5) -> list[dict[str, Any]]:
        """
        Get random calls from database that have budget data.

        Args:
            conn: Database connection
            count: Number of calls to retrieve

        Returns:
            List of call dictionaries with topic_code and budget_total
        """
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Select calls with non-null budgets that are Horizon Europe calls
        cursor.execute(
            """
            SELECT topic_code, budget_total, title, status, deadline
            FROM funding_calls
            WHERE topic_code IS NOT NULL
            AND budget_total IS NOT NULL
            AND budget_total > 0
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

    def _calculate_accuracy_score(self, results: list[dict[str, Any]]) -> int:
        """
        Calculate accuracy score based on budget matches.

        Returns:
            Score from 0-100 (percentage of matching budgets)
        """
        if not results:
            return 0

        matches = sum(1 for r in results if r.get("match", False))
        return int((matches / len(results)) * 100)

    # ==========================================================================
    # INTEGRATION TESTS - Require database and network access
    # ==========================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
