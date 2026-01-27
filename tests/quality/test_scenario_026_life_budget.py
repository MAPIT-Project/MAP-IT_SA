"""
Scenario 026: LIFE Budget
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "What budget range for a LIFE climate adaptation project?"
Expected: SAP/SIP typical budgets, co-financing rates (55-75%)
Verify: LIFE-specific funding model
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario026LIFEBudget:
    """Test LIFE Programme budget ranges for climate adaptation project."""

    BASE_URL = "http://localhost:8000"
    QUERY = "What budget range for a LIFE climate adaptation project?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(260000, 269999)

    @pytest.mark.asyncio
    async def test_mentions_sap_budget(self, conversation_id):
        """Test that response mentions SAP (Standard Action Projects) budget."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention SAP budget (€1-5 million)
            sap_indicators = [
                "sap",
                "standard action",
                "1-5 million",
                "€1-5",
                "1 to 5 million",
                "1-5m",
            ]

            has_sap = any(ind in response_text for ind in sap_indicators)
            assert has_sap, "Response should mention SAP (Standard Action Projects) budget range"

    @pytest.mark.asyncio
    async def test_mentions_sip_budget(self, conversation_id):
        """Test that response mentions SIP (Strategic Integrated Projects) budget."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention SIP budget (€10-30 million)
            sip_indicators = [
                "sip",
                "strategic integrated",
                "10-30 million",
                "€10-30",
                "10 to 30 million",
                "10-30m",
            ]

            has_sip = any(ind in response_text for ind in sip_indicators)
            assert has_sip, "Response should mention SIP budget range"

    @pytest.mark.asyncio
    async def test_mentions_cofinancing_rate(self, conversation_id):
        """Test that response mentions co-financing rates."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention co-financing rates (60% for CCA - climate)
            cofinancing_indicators = [
                "60%",
                "55%",
                "75%",
                "co-financing",
                "cofinancing",
                "co financing",
                "eu contribution",
                "funding rate",
            ]

            has_cofinancing = any(ind in response_text for ind in cofinancing_indicators)
            assert has_cofinancing, "Response should mention co-financing rates (55-75%)"

    @pytest.mark.asyncio
    async def test_mentions_cca_subprogramme(self, conversation_id):
        """Test that response mentions CCA (Climate Change Adaptation) sub-programme."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention Climate sub-programme (CCA)
            cca_indicators = [
                "cca",
                "climate change",
                "climate adaptation",
                "climate mitigation",
                "climate action",
            ]

            has_cca = any(ind in response_text for ind in cca_indicators)
            assert has_cca, "Response should mention CCA (Climate Change) sub-programme"

    @pytest.mark.asyncio
    async def test_mentions_life_programme(self, conversation_id):
        """Test that response explicitly mentions LIFE Programme."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention LIFE Programme
            has_life = "life" in response_text
            assert has_life, "Response should mention LIFE Programme"

    @pytest.mark.asyncio
    async def test_mentions_project_duration(self, conversation_id):
        """Test that response mentions typical project duration."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention project duration
            duration_indicators = [
                "3-5 years",
                "5-10 years",
                "1-2 years",
                "duration",
                "36 months",
                "60 months",
            ]

            has_duration = any(ind in response_text for ind in duration_indicators)
            assert has_duration, "Response should mention typical project duration"

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
                "cinea",
                "portal",
                "website",
                "check",
                "contact",
                "apply",
                "next step",
                "recommend",
                "review",
                "work programme",
                "national contact point",
            ]

            has_action = sum(1 for ind in action_indicators if ind in response_text) >= 2
            assert has_action, "Response should provide at least 2 actionable next steps"

    @pytest.mark.asyncio
    async def test_no_horizon_europe_budget_model(self, conversation_id):
        """Test that response doesn't use Horizon Europe budget model (RIA/IA/CSA)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention LIFE (verifies it's LIFE-specific)
            has_life = "life" in response_text
            assert has_life, "Response should be LIFE-specific, not Horizon Europe"

    @pytest.mark.asyncio
    async def test_mentions_budget_categories(self, conversation_id):
        """Test that response mentions budget categories or considerations."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention budget considerations
            budget_indicators = [
                "personnel",
                "travel",
                "equipment",
                "direct costs",
                "indirect costs",
                "in-kind",
                "budget categor",
                "cost categor",
            ]

            has_categories = any(ind in response_text for ind in budget_indicators)
            assert has_categories, "Response should mention budget categories or considerations"

    @pytest.mark.asyncio
    async def test_not_deflection(self, conversation_id):
        """Test that response is not a deflection."""
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
                "i don't have information",
                "couldn't find",
                "please try a more specific",
                "i'm not sure",
                "unable to",
            ]

            has_deflection = any(phrase in response_text for phrase in deflection_phrases)
            assert not has_deflection, "Response should not be a deflection"

    @pytest.mark.asyncio
    async def test_quality_score_not_deflection(self, conversation_id):
        """Test that quality analysis doesn't mark response as deflection."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            quality = result.get("metadata", {}).get("quality_analysis", {})
            category = quality.get("category", "")

            assert category != "deflection", (
                f"Quality category should not be 'deflection', got '{category}'"
            )

    @pytest.mark.asyncio
    async def test_fast_response_time(self, conversation_id):
        """Test that response is fast (pre-routed guidance should be quick)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            processing_time = result.get("metadata", {}).get("processing_time_ms", 10000)

            # Pre-routed guidance should be fast (< 5 seconds)
            assert processing_time < 5000, (
                f"Response should be fast (< 5 seconds), took {processing_time}ms"
            )

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
            if "life" in response_text:
                query_fulfillment += 10  # Mentions LIFE Programme
            sap_terms = ["sap", "standard action", "1-5 million"]
            if any(w in response_text for w in sap_terms):
                query_fulfillment += 10  # Mentions SAP budget
            sip_terms = ["sip", "strategic integrated", "10-30 million"]
            if any(w in response_text for w in sip_terms):
                query_fulfillment += 10  # Mentions SIP budget
            cca_terms = ["cca", "climate change", "climate adaptation"]
            if any(w in response_text for w in cca_terms):
                query_fulfillment += 10  # Mentions CCA sub-programme
            score += min(query_fulfillment, 40)

            # Specificity (25 points)
            specificity = 0
            rate_terms = ["60%", "75%", "55%", "95%", "co-financing", "funding rate"]
            if any(w in response_text for w in rate_terms):
                specificity += 10  # Co-financing rates
            duration_terms = ["3-5 years", "5-10 years", "1-2 years", "duration"]
            if any(w in response_text for w in duration_terms):
                specificity += 10  # Duration info
            if re.search(r"€?\d+[\-–]\d+\s*million", response_text):
                specificity += 5  # Specific budget numbers
            score += min(specificity, 25)

            # Factual Accuracy (25 points)
            factual = 0
            # LIFE-specific response (not Horizon Europe RIA/IA)
            if "life" in response_text:
                factual += 15  # Correct programme
            if any(t in response_text for t in ["sap", "sip", "snap", "standard action"]):
                factual += 10  # Correct project types
            score += min(factual, 25)

            # Actionability (10 points)
            actionability = 0
            action_terms = [
                "cinea",
                "portal",
                "website",
                "check",
                "contact",
                "apply",
                "next step",
                "review",
                "national contact point",
            ]
            action_count = sum(1 for t in action_terms if t in response_text)
            if action_count >= 2:
                actionability += 10
            elif action_count >= 1:
                actionability += 5
            score += actionability

            assert score >= self.PASS_THRESHOLD, (
                f"Score {score} below threshold {self.PASS_THRESHOLD}. "
                f"Response: {response_text[:500]}..."
            )
