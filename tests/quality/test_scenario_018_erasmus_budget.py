"""
Scenario 018: Erasmus+ Budget
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "Calculate budget for sending 15 students from Spain to Germany for 4 months"
Expected: Unit costs, travel band, organizational support, total
Verify: Uses Erasmus+ lump sum model correctly
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario018ErasmusBudget:
    """Test Erasmus+ budget calculation for student mobility."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Calculate budget for sending 15 students from Spain to Germany for 4 months"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(180000, 189999)

    @pytest.mark.asyncio
    async def test_returns_total_budget(self, conversation_id):
        """Test that response includes a total budget amount."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should include a total budget amount
            total_indicators = [
                "total",
                "€",
                "eur",
                "grant amount",
            ]

            has_total = any(ind in response_text for ind in total_indicators)
            assert has_total, "Response should include a total budget amount"

            # Should include a specific monetary value
            money_pattern = r"(€[\d,\.]+|[\d,\.]+\s*€|[\d,\.]+\s*eur)"
            has_money = re.search(money_pattern, response_text, re.IGNORECASE)
            assert has_money, "Response should include specific monetary values"

    @pytest.mark.asyncio
    async def test_includes_unit_costs(self, conversation_id):
        """Test that response includes unit cost breakdown."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should include unit cost indicators
            unit_cost_indicators = [
                "unit cost",
                "travel",
                "individual support",
                "daily",
                "allowance",
            ]

            has_unit_costs = sum(1 for ind in unit_cost_indicators if ind in response_text) >= 2
            assert has_unit_costs, "Response should include at least 2 unit cost categories"

    @pytest.mark.asyncio
    async def test_mentions_travel_band(self, conversation_id):
        """Test that response mentions travel distance band."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention travel band/distance
            travel_band_indicators = [
                "distance band",
                "travel band",
                "km",
                "1500",
                "2000",
                "band",
            ]

            has_travel_band = any(ind in response_text for ind in travel_band_indicators)
            assert has_travel_band, "Response should mention travel distance band"

    @pytest.mark.asyncio
    async def test_includes_organizational_support(self, conversation_id):
        """Test that response includes organizational support costs."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should include organizational support
            org_support_indicators = [
                "organizational support",
                "organisational support",
                "org support",
                "admin",
                "per-participant",
            ]

            has_org_support = any(ind in response_text for ind in org_support_indicators)
            assert has_org_support, "Response should include organizational support costs"

    @pytest.mark.asyncio
    async def test_uses_erasmus_budget_tool(self, conversation_id):
        """Test that the Erasmus+ budget tool is called."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Should use calculate_erasmus_budget tool
            erasmus_budget_tools = [
                t for t in tools_used if "erasmus" in t.lower() and "budget" in t.lower()
            ]
            assert len(erasmus_budget_tools) > 0, (
                f"Should use Erasmus budget tool, but got: {tools_used}"
            )

    @pytest.mark.asyncio
    async def test_mentions_student_mobility(self, conversation_id):
        """Test that response correctly identifies this as student mobility."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention student mobility
            mobility_indicators = [
                "student mobility",
                "ka1",
                "key action 1",
                "mobility",
                "participants",
            ]

            has_mobility = any(ind in response_text for ind in mobility_indicators)
            assert has_mobility, "Response should mention student mobility context"

    @pytest.mark.asyncio
    async def test_includes_spain_to_germany_context(self, conversation_id):
        """Test that response includes Spain to Germany travel context."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention origin and destination
            assert "spain" in response_text, "Response should mention Spain as origin"
            assert "germany" in response_text, "Response should mention Germany as destination"

    @pytest.mark.asyncio
    async def test_includes_participant_count(self, conversation_id):
        """Test that response includes the participant count."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should mention 15 participants
            assert "15" in response_text, "Response should mention 15 participants"

    @pytest.mark.asyncio
    async def test_includes_duration(self, conversation_id):
        """Test that response includes the duration (4 months)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention 4 months or 120 days
            duration_indicators = [
                "4 month",
                "120 day",
                "~4 month",
            ]

            has_duration = any(ind in response_text for ind in duration_indicators)
            assert has_duration, "Response should mention duration (4 months or 120 days)"

    @pytest.mark.asyncio
    async def test_provides_next_steps(self, conversation_id):
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

            # Should provide actionable guidance
            action_indicators = [
                "next steps",
                "programme guide",
                "national agency",
                "erasmus-plus.ec.europa.eu",
                "distance calculator",
            ]

            has_actions = sum(1 for ind in action_indicators if ind in response_text) >= 2
            assert has_actions, "Response should provide at least 2 actionable next steps"

    @pytest.mark.asyncio
    async def test_overall_score_meets_threshold(self, conversation_id):
        """Test that the overall response score meets the pass threshold."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()
            metadata = result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            score = 0

            # Query Fulfillment (40 points)
            if "€" in response_text or "eur" in response_text:
                score += 15  # Has budget amount
            if "total" in response_text:
                score += 10  # Has total
            if "travel" in response_text:
                score += 8  # Has travel costs
            if "individual support" in response_text or "allowance" in response_text:
                score += 7  # Has individual support

            # Specificity (25 points)
            if any(t for t in tools_used if "erasmus" in t.lower() and "budget" in t.lower()):
                score += 10  # Used correct tool
            if "15" in response_text:
                score += 5  # Has participant count
            if "spain" in response_text and "germany" in response_text:
                score += 5  # Has origin/destination
            if "km" in response_text or "distance band" in response_text:
                score += 5  # Has travel band

            # Factual Accuracy (25 points)
            if "unit cost" in response_text or "lump sum" in response_text:
                score += 10  # Correct funding model
            has_org_support = (
                "organizational support" in response_text
                or "organisational support" in response_text
            )
            if has_org_support:
                score += 8  # Has org support
            if "4 month" in response_text or "120 day" in response_text:
                score += 7  # Correct duration

            # Actionability (10 points)
            if "next steps" in response_text:
                score += 5
            if "programme guide" in response_text or "national agency" in response_text:
                score += 5

            assert score >= self.PASS_THRESHOLD, (
                f"Score {score} is below threshold {self.PASS_THRESHOLD}"
            )

    @pytest.mark.asyncio
    async def test_returns_valid_json_response(self, conversation_id):
        """Test that the API returns a valid JSON response with expected fields."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()

            # Should have required fields
            assert "response" in result, "Response should contain 'response' field"
            assert "metadata" in result, "Response should contain 'metadata' field"
            assert len(result.get("response", "")) > 0, "Response should not be empty"

    @pytest.mark.asyncio
    async def test_no_horizon_europe_confusion(self, conversation_id):
        """Test that response doesn't confuse with Horizon Europe budget models."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should NOT contain Horizon Europe-specific budget terms
            horizon_budget_indicators = [
                "ria funding",
                "ia funding",
                "csa funding",
                "horizon europe budget",
                "personnel costs",
                "indirect costs",
                "equipment costs",
            ]

            has_horizon_budget = any(ind in response_text for ind in horizon_budget_indicators)
            assert not has_horizon_budget, (
                "Response should not confuse Erasmus+ with Horizon Europe budget model"
            )

    @pytest.mark.asyncio
    async def test_uses_erasmus_lump_sum_model(self, conversation_id):
        """Test that response uses Erasmus+ lump sum/unit cost model."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should use Erasmus+ funding model terminology
            erasmus_model_indicators = [
                "unit cost",
                "lump sum",
                "funding model",
                "daily allowance",
                "per-participant",
            ]

            has_erasmus_model = any(ind in response_text for ind in erasmus_model_indicators)
            assert has_erasmus_model, "Response should use Erasmus+ lump sum/unit cost model"
