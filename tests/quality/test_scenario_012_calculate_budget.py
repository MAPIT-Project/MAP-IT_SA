"""
Scenario 012: Calculate Budget
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "Calculate a budget for a 3-year project with 10 partners doing renewable energy research"
Expected: Detailed budget breakdown by category
Verify: Calculations are logical, categories complete
Fix if: Math errors, missing categories, unrealistic totals
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario012CalculateBudget:
    """Test budget calculation functionality for Horizon Europe proposals."""

    BASE_URL = "http://localhost:8000"
    QUERY = (
        "Calculate a budget for a 3-year project with 10 partners "
        "doing renewable energy research"
    )
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(120000, 129999)

    @pytest.mark.asyncio
    async def test_uses_calculate_budget_tool(self, conversation_id):
        """Test that the calculate_budget tool is used."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})

            # Check if tools_used includes calculate_budget
            tools_used = metadata.get("tools_used", [])

            # Also check reasoning steps for tool calls
            reasoning_steps = metadata.get("reasoning_steps", [])
            tool_in_reasoning = any("calculate_budget" in str(step) for step in reasoning_steps)

            # The tool might be versioned (e.g., calculate_budget_1_0)
            has_calc_tool = any("calculate_budget" in t for t in tools_used)

            assert (
                has_calc_tool or tool_in_reasoning
            ), f"Expected calculate_budget tool to be used. Tools: {tools_used}"

    @pytest.mark.asyncio
    async def test_includes_total_budget(self, conversation_id):
        """Test that response contains a total budget amount."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain total budget amount (e.g., "€5.35M" or "5.35 million")
            total_budget_patterns = [
                r"Total\s+(?:Project\s+)?Cost[^\d]*€?[\d.,]+[MK]?",
                r"€[\d.,]+[MK]?\s*total",
                r"total\s+(?:budget|cost)[^\d]*€?[\d.,]+",
            ]

            has_total = any(
                re.search(pattern, response_text, re.IGNORECASE)
                for pattern in total_budget_patterns
            )

            # Also check for any budget amount in millions
            has_budget_amount = bool(re.search(r"€[\d.,]+[MK]", response_text))

            assert (
                has_total or has_budget_amount
            ), f"Response should contain a total budget amount. Response: {response_text[:500]}"

    @pytest.mark.asyncio
    async def test_includes_cost_breakdown_categories(self, conversation_id):
        """Test that response contains cost breakdown by category."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should contain standard Horizon Europe cost categories
            required_categories = ["personnel", "equipment"]
            optional_categories = ["travel", "subcontract", "indirect", "other"]

            found_required = sum(1 for cat in required_categories if cat in response_text)
            found_optional = sum(1 for cat in optional_categories if cat in response_text)

            assert found_required >= 1, (
                f"Response should contain cost category breakdown. "
                f"Expected at least personnel or equipment. Response: {response_text[:500]}"
            )

            # Should have at least 3 categories total for a complete breakdown
            total_categories = found_required + found_optional
            all_categories = required_categories + optional_categories
            found_cats = [c for c in all_categories if c in response_text]
            assert total_categories >= 3, (
                f"Budget breakdown should include at least 3 cost categories. "
                f"Found {total_categories}: {found_cats}"
            )

    @pytest.mark.asyncio
    async def test_budget_breakdown_has_percentages(self, conversation_id):
        """Test that cost breakdown includes percentage allocations."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain percentage values
            percentage_pattern = r"\d+(?:\.\d+)?%"
            percentages = re.findall(percentage_pattern, response_text)

            assert len(percentages) >= 3, (
                f"Budget breakdown should include percentage allocations. "
                f"Found {len(percentages)} percentages"
            )

    @pytest.mark.asyncio
    async def test_includes_per_partner_distribution(self, conversation_id):
        """Test that response includes per-partner budget information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention per-partner distribution
            per_partner_indicators = [
                "per partner",
                "per-partner",
                "each partner",
                "coordinator",
                "average per",
            ]

            has_per_partner = any(ind in response_text for ind in per_partner_indicators)

            assert has_per_partner, "Response should include per-partner budget distribution"

    @pytest.mark.asyncio
    async def test_includes_effort_or_person_months(self, conversation_id):
        """Test that response includes effort/person-months information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention person-months or effort
            effort_indicators = [
                "person-month",
                "person month",
                "pm",
                "effort",
                "fte",
                "full-time",
            ]

            has_effort = any(ind in response_text for ind in effort_indicators)

            assert has_effort, "Response should include effort/person-months information"

    @pytest.mark.asyncio
    async def test_budget_values_are_reasonable(self, conversation_id):
        """Test that calculated budget is within reasonable range for RIA."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Extract budget values in millions
            million_values = re.findall(r"€([\d.,]+)[MK]", response_text)
            million_values += re.findall(r"€([\d.,]+)\s*million", response_text, re.IGNORECASE)

            # Convert to numbers
            numbers = []
            for val in million_values:
                try:
                    num = float(val.replace(",", ""))
                    numbers.append(num)
                except ValueError:
                    continue

            # For 10 partners, 3-year RIA, budget should be €2M-€15M typically
            if numbers:
                # At least one number should be the total budget
                total_candidates = [n for n in numbers if 2 <= n <= 15]
                assert len(total_candidates) > 0, (
                    f"Budget should be in reasonable RIA range (2-15M for 10 partners). "
                    f"Found values: {numbers}"
                )

    @pytest.mark.asyncio
    async def test_includes_funding_rate(self, conversation_id):
        """Test that response mentions the RIA funding rate (100%)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should mention funding rate (typically 100% for RIA)
            funding_rate_indicators = [
                r"100%",
                r"funding rate",
                r"EU contribution",
                r"full\s+funding",
            ]

            has_funding_rate = any(
                re.search(ind, response_text, re.IGNORECASE) for ind in funding_rate_indicators
            )

            assert has_funding_rate, "Response should mention the funding rate"

    @pytest.mark.asyncio
    async def test_includes_eu_contribution(self, conversation_id):
        """Test that response includes EU contribution amount."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention EU contribution
            eu_contribution_indicators = [
                "eu contribution",
                "eu funding",
                "european",
                "grant",
            ]

            has_eu_contribution = any(ind in response_text for ind in eu_contribution_indicators)

            assert has_eu_contribution, "Response should include EU contribution information"

    @pytest.mark.asyncio
    async def test_quality_score_above_threshold(self, conversation_id):
        """Test that response quality score meets threshold."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})

            # Check quality analysis if available
            quality = metadata.get("quality_analysis", {})
            score = quality.get("score", 0)

            # If no quality score, do basic evaluation
            if score == 0:
                response_text = result.get("response", "")
                # Basic scoring based on content
                score = 0

                # Query fulfillment (40 points)
                if re.search(r"€[\d.,]+[MK]?", response_text):  # Has total budget
                    score += 20
                if re.search(r"personnel|equipment", response_text, re.IGNORECASE):  # Has breakdown
                    score += 20

                # Specificity (25 points)
                if re.search(r"\d+(?:\.\d+)?%", response_text):  # Has percentages
                    score += 15
                if re.search(r"person.*month|PM", response_text, re.IGNORECASE):  # Has effort
                    score += 10

                # Factual accuracy (25 points)
                if re.search(r"100%|funding rate", response_text, re.IGNORECASE):  # Correct rate
                    score += 15
                if re.search(r"RIA", response_text):  # Correct context
                    score += 10

                # Actionability (10 points)
                if re.search(r"partner|coordinator", response_text, re.IGNORECASE):
                    score += 10

            assert (
                score >= self.PASS_THRESHOLD
            ), f"Quality score {score} below threshold {self.PASS_THRESHOLD}"

    @pytest.mark.asyncio
    async def test_no_error_messages(self, conversation_id):
        """Test that response doesn't contain error messages."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should not contain error messages
            error_indicators = [
                "error",
                "failed",
                "could not",
                "unable to",
                "not available",
                "no data",
                "search results are not helpful",
            ]

            has_error = any(ind in response_text for ind in error_indicators)

            # Allow some nuanced messages but not hard failures
            if has_error:
                # Check if it's a soft mention vs. actual failure
                hard_failures = ["failed", "error occurred", "unable to calculate"]
                has_hard_failure = any(ind in response_text for ind in hard_failures)
                assert (
                    not has_hard_failure
                ), f"Response contains error messages: {response_text[:300]}"

    @pytest.mark.asyncio
    async def test_includes_recommendations(self, conversation_id):
        """Test that response includes budget recommendations."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should contain recommendations or guidance
            recommendation_indicators = [
                "recommend",
                "suggest",
                "typical",
                "should",
                "consider",
                "next steps",
                "guidance",
            ]

            has_recommendations = any(ind in response_text for ind in recommendation_indicators)

            assert has_recommendations, "Response should include budget recommendations or guidance"

    @pytest.mark.asyncio
    async def test_full_scenario_integration(self, conversation_id):
        """Full integration test for Scenario 012."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")
            metadata = result.get("metadata", {})

            # Comprehensive assertions for PRD requirements
            assertions_passed = []

            # 1. Total budget present
            has_total = bool(re.search(r"€[\d.,]+[MK]", response_text))
            assertions_passed.append(("total_budget", has_total))

            # 2. Category breakdown present
            has_breakdown = bool(re.search(r"personnel|equipment", response_text, re.IGNORECASE))
            assertions_passed.append(("category_breakdown", has_breakdown))

            # 3. Percentages present
            has_percentages = len(re.findall(r"\d+(?:\.\d+)?%", response_text)) >= 3
            assertions_passed.append(("percentages", has_percentages))

            # 4. Per-partner info
            has_per_partner = bool(
                re.search(r"per\s*partner|coordinator", response_text, re.IGNORECASE)
            )
            assertions_passed.append(("per_partner", has_per_partner))

            # 5. Used correct tool
            tools_used = metadata.get("tools_used", [])
            reasoning = metadata.get("reasoning_steps", [])
            has_tool = any("calculate_budget" in str(t) for t in tools_used) or any(
                "calculate_budget" in str(s) for s in reasoning
            )
            assertions_passed.append(("correct_tool", has_tool))

            # 6. Reasonable values (not hallucinated)
            # Extract values in millions (M) - these are the main budget figures
            values_m = re.findall(r"€([\d.,]+)[M]", response_text)
            # Values in K should be < 10000 (i.e., less than 10M)
            values_k = re.findall(r"€([\d.,]+)K", response_text)

            # Check million values are reasonable (0.1M to 100M)
            reasonable_m = all(
                0.1 <= float(v.replace(",", "")) <= 100
                for v in values_m
                if v.replace(",", "").replace(".", "").isdigit()
            )
            # Check K values are reasonable (up to 10000K = 10M)
            reasonable_k = all(
                float(v.replace(",", "")) <= 10000
                for v in values_k
                if v.replace(",", "").replace(".", "").isdigit()
            )
            reasonable = reasonable_m and reasonable_k
            assertions_passed.append(("reasonable_values", reasonable))

            # Report failures
            failures = [name for name, passed in assertions_passed if not passed]
            if failures:
                pytest.fail(
                    f"Scenario 012 failed checks: {failures}\n"
                    f"Response: {response_text[:800]}..."
                )

    @pytest.mark.asyncio
    async def test_math_consistency(self, conversation_id):
        """Test that budget math is internally consistent."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Extract percentages
            percentages = re.findall(r"(\d+(?:\.\d+)?)%", response_text)
            percentage_values = [float(p) for p in percentages if float(p) <= 100]

            # If we have category percentages, they should roughly sum to 100%
            if len(percentage_values) >= 5:
                # Find the likely category percentages (usually between 5% and 60%)
                category_pcts = [p for p in percentage_values if 1 <= p <= 60]
                if len(category_pcts) >= 5:
                    total_pct = sum(category_pcts[:6])  # Take first 6 categories
                    # Allow 95-105% due to rounding
                    assert 95 <= total_pct <= 105, (
                        f"Budget percentages should sum to ~100%, got {total_pct}%. "
                        f"Categories: {category_pcts[:6]}"
                    )
