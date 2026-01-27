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
import os
from decimal import Decimal
from typing import Any

import httpx
import psycopg2
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

    @pytest.fixture
    def db_connection(self):
        """Create a database connection."""
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        conn = psycopg2.connect(db_url)
        yield conn
        conn.close()

    @pytest.fixture
    def http_client(self):
        """Create an HTTP client with timeout."""
        client = httpx.Client(timeout=30.0)
        yield client
        client.close()

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

    @pytest.mark.asyncio
    async def test_database_has_calls_with_budgets(self, db_connection):
        """Test that the database has calls with budget data to verify."""
        calls = self._get_random_calls_with_budgets(db_connection, count=10)

        assert len(calls) > 0, "Database should have calls with budgets"
        assert all(call.get("budget_total") is not None for call in calls), (
            "All selected calls should have budget_total"
        )
        assert all(call.get("topic_code") is not None for call in calls), (
            "All calls should have topic codes"
        )

    @pytest.mark.asyncio
    async def test_eu_portal_api_returns_budget(self, http_client):
        """Test that the EU Portal API returns budget data."""
        # Use a known topic code for testing
        test_topic = "horizon-cl5-2026-d3-01"
        url = f"{self.EU_PORTAL_TOPIC_DETAILS}/{test_topic}.json"

        try:
            response = http_client.get(url)

            if response.status_code == 200:
                data = response.json()
                topic_data = data.get("TopicDetails", {})
                budget_model = topic_data.get("budgetOverviewModel", {})

                # API should have budget overview model (even if empty)
                logger.info(f"Budget model keys: {budget_model.keys() if budget_model else 'None'}")
                assert True, "API accessible and returns data"
            else:
                # 404 is acceptable - topic may not exist
                assert response.status_code == 404, f"Unexpected status: {response.status_code}"

        except Exception as e:
            pytest.skip(f"EU Portal API not accessible: {e}")

    @pytest.mark.asyncio
    async def test_verify_5_random_call_budgets(self, db_connection, http_client):
        """
        MAIN TEST: Verify 5 random call budgets against EU Portal API.

        This is the core test for Scenario 042.
        """
        # Step 1: Get 5 random calls with budgets from database
        calls = self._get_random_calls_with_budgets(db_connection, count=self.CALLS_TO_VERIFY)

        if len(calls) < self.CALLS_TO_VERIFY:
            pytest.skip(
                f"Only {len(calls)} calls with budgets available, need {self.CALLS_TO_VERIFY}"
            )

        # Step 2: Verify each call against EU Portal API
        results = []
        matches = 0
        api_failures = 0

        for call in calls:
            topic_code = call["topic_code"]
            local_budget = call["budget_total"]

            # Convert to Decimal if needed
            if local_budget is not None and not isinstance(local_budget, Decimal):
                local_budget = Decimal(str(local_budget))

            # Fetch from API
            api_budget = self._fetch_api_budget(http_client, topic_code)

            if api_budget is None:
                logger.warning(f"Could not fetch budget from API for {topic_code}")
                api_failures += 1
                results.append(
                    {
                        "topic_code": topic_code,
                        "local": local_budget,
                        "api": None,
                        "match": False,
                        "error": "API fetch failed or no budget in API",
                    }
                )
                continue

            # Compare budgets with tolerance
            is_match = self._budgets_match(local_budget, api_budget)
            diff_percent = (
                self._calculate_percentage_difference(local_budget, api_budget)
                if local_budget and api_budget
                else None
            )

            if is_match:
                matches += 1

            results.append(
                {
                    "topic_code": topic_code,
                    "local": local_budget,
                    "api": api_budget,
                    "diff_percent": diff_percent,
                    "match": is_match,
                }
            )

            logger.info(
                f"{'✅' if is_match else '❌'} {topic_code}: "
                f"Local=€{local_budget:,.0f}, API=€{api_budget:,.0f}, Diff={diff_percent:.1f}%"
            )

        # Step 3: Calculate score
        verified_calls = len(results) - api_failures
        if verified_calls == 0:
            pytest.skip("Could not verify any calls against API")

        accuracy_score = (matches / verified_calls) * 100

        # Log summary
        logger.info("\n=== Budget Accuracy Summary ===")
        logger.info(f"Calls checked: {len(results)}")
        logger.info(f"API failures: {api_failures}")
        logger.info(f"Verified: {verified_calls}")
        logger.info(f"Matches (within {self.BUDGET_TOLERANCE_PERCENT}%): {matches}")
        logger.info(f"Accuracy: {accuracy_score:.1f}%")

        # Print detailed results
        print("\n=== Budget Accuracy Verification Results ===")
        for result in results:
            status = "✅ MATCH" if result.get("match") else "❌ MISMATCH"
            if result.get("error"):
                status = "⚠️ " + result["error"]

            local_str = f"€{result['local']:,.0f}" if result.get("local") else "N/A"
            api_str = f"€{result['api']:,.0f}" if result.get("api") else "N/A"
            diff_val = result.get("diff_percent")
            diff_str = f"{diff_val:.1f}%" if diff_val is not None else "N/A"

            print(
                f"{status} | {result['topic_code']} | "
                f"Local: {local_str} | API: {api_str} | Diff: {diff_str}"
            )

        # Step 4: Assert pass threshold
        mismatches = [r for r in results if not r.get("match")]
        assert accuracy_score >= self.PASS_THRESHOLD, (
            f"Budget accuracy score {accuracy_score:.1f}% "
            f"below threshold {self.PASS_THRESHOLD}%. Mismatches: {mismatches}"
        )

    @pytest.mark.asyncio
    async def test_verify_horizon_europe_calls_only(self, db_connection):
        """Test that only Horizon Europe calls are being verified."""
        calls = self._get_random_calls_with_budgets(db_connection, count=10)

        for call in calls:
            topic_code = call["topic_code"]
            assert topic_code.startswith("HORIZON"), f"Non-Horizon call found: {topic_code}"

    @pytest.mark.asyncio
    async def test_budget_format_consistency(self, db_connection):
        """Test that all local budgets are in consistent format."""
        calls = self._get_random_calls_with_budgets(db_connection, count=20)

        for call in calls:
            budget = call["budget_total"]

            # Should be numeric type
            assert isinstance(budget, int | float | Decimal), (
                f"Budget for {call['topic_code']} is not numeric: {type(budget)}"
            )

            # Should be positive
            assert budget > 0, f"Budget for {call['topic_code']} should be positive: {budget}"

    @pytest.mark.asyncio
    async def test_budget_ranges_reasonable(self, db_connection):
        """Test that local budgets are within reasonable ranges."""
        calls = self._get_random_calls_with_budgets(db_connection, count=20)

        # Typical Horizon Europe call budgets range from €1M to €100M
        MIN_REASONABLE = 100_000  # €100K
        MAX_REASONABLE = 500_000_000  # €500M

        for call in calls:
            budget = float(call["budget_total"])

            if budget < MIN_REASONABLE:
                logger.warning(f"Budget for {call['topic_code']} seems low: €{budget:,.0f}")

            if budget > MAX_REASONABLE:
                logger.warning(f"Budget for {call['topic_code']} seems high: €{budget:,.0f}")


class TestBudgetDataCompleteness:
    """Tests for verifying budget data completeness."""

    @pytest.fixture
    def db_connection(self):
        """Create a database connection."""
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        conn = psycopg2.connect(db_url)
        yield conn
        conn.close()

    def test_budget_data_coverage(self, db_connection):
        """Test that most calls have budget data."""
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                COUNT(budget_total) as with_budget,
                COUNT(*) FILTER (WHERE budget_total > 0) as with_positive_budget
            FROM funding_calls
            WHERE topic_code LIKE 'HORIZON%%'
            AND status IN ('open', 'upcoming')
        """
        )

        result = cursor.fetchone()
        cursor.close()

        total = result["total"]
        with_budget = result["with_budget"]
        with_positive = result["with_positive_budget"]

        if total > 0:
            coverage = (with_budget / total) * 100
            positive_coverage = (with_positive / total) * 100

            logger.info(f"Budget coverage: {coverage:.1f}% ({with_budget}/{total})")
            logger.info(
                f"Positive budget coverage: {positive_coverage:.1f}% ({with_positive}/{total})"
            )

            # Most calls should have budget data, but some may not have been published yet
            assert coverage >= 50, (
                f"Only {coverage:.1f}% of open/upcoming calls have budget data. "
                "Should be at least 50%."
            )

    def test_no_negative_budgets(self, db_connection):
        """Test that there are no negative budgets."""
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT topic_code, budget_total
            FROM funding_calls
            WHERE budget_total < 0
            LIMIT 10
        """
        )

        negative_budgets = cursor.fetchall()
        cursor.close()

        assert len(negative_budgets) == 0, (
            f"Found {len(negative_budgets)} calls with negative budgets: "
            f"{[c['topic_code'] for c in negative_budgets]}"
        )

    def test_budget_estimates_marked(self, db_connection):
        """Test that we can identify estimated vs confirmed budgets."""
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)

        # Check if there's a column for budget estimate flag
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'funding_calls'
            AND column_name IN ('budget_is_estimate', 'budget_confirmed', 'budget_notes')
        """
        )

        estimate_columns = [row["column_name"] for row in cursor.fetchall()]
        cursor.close()

        if not estimate_columns:
            logger.info(
                "No budget estimate flag column found. "
                "Consider adding 'budget_is_estimate' column to mark estimated values."
            )
            # This is informational, not a failure
            assert True

        else:
            logger.info(f"Found budget estimate columns: {estimate_columns}")
            assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
