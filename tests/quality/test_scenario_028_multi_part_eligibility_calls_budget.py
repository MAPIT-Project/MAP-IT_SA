"""
Test Scenario 028: Multi-Part Question - Eligibility + Calls + Budget

This scenario tests handling of complex multi-part queries that ask about:
1. Eligibility (SME eligibility for EIC Accelerator)
2. Deadlines (when to apply)
3. Budget (what funding can be requested)

Quality Scoring (100 points):
- Query Fulfillment (40 points): All three parts answered
- Specificity (25 points): Concrete details (numbers, dates, requirements)
- Factual Accuracy (25 points): Correct EU funding information
- Actionability (10 points): Clear next steps for user

Pass threshold: 80 points
"""

import json
import random

import aiohttp
import pytest


class TestScenario028MultiPartEligibilityCallsBudget:
    """Test multi-part query handling: Eligibility + Calls + Budget."""

    BASE_URL = "http://localhost:8000"
    PRIMARY_QUERY = (
        "I'm an SME from Netherlands. Am I eligible for EIC Accelerator? "
        "What's the deadline? What budget can I request?"
    )

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        return random.randint(100000, 999999)

    async def send_query(self, conversation_id: int, query: str) -> dict:
        """Send a query and collect the streaming response."""
        url = f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message/stream"

        full_response = ""
        tools_used = []

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"message": query}) as response:
                if response.status != 200:
                    text = await response.text()
                    return {
                        "error": True,
                        "status": response.status,
                        "text": text,
                        "response": "",
                        "tools_used": [],
                    }

                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "token":
                                full_response += data.get("content", "")
                            elif data.get("type") == "tool_call":
                                tools_used.append(data.get("tool"))
                        except json.JSONDecodeError:
                            pass

        return {
            "error": False,
            "response": full_response,
            "tools_used": tools_used,
        }

    def score_response(self, response: str, query_context: dict = None) -> dict:
        """Score the response based on PRD criteria."""
        response_lower = response.lower()

        # Part 1: Eligibility (13/40 points)
        has_eligibility = any(x in response_lower for x in ["eligible", "eligibility", "sme"])
        has_eligibility_details = any(
            x in response_lower
            for x in [
                "organization type",
                "< 250",
                "250 employee",
                "sme definition",
                "eu member state",
            ]
        )

        # Part 2: Deadline (13/40 points)
        has_deadline = any(
            x in response_lower
            for x in ["deadline", "cut-off", "march 2026", "october 2026", "2026"]
        )
        has_deadline_details = "cut-off" in response_lower or any(
            month in response_lower for month in ["march", "october"]
        )

        # Part 3: Budget (14/40 points)
        has_budget = any(
            x in response_lower for x in ["budget", "million", "eur", "€", "grant", "equity"]
        )
        has_budget_details = (
            "2.5" in response_lower or "15 million" in response_lower or "equity" in response_lower
        )

        # Check for EIC-specific content
        has_eic_content = any(
            x in response_lower for x in ["eic", "accelerator", "european innovation council"]
        )

        # Query Fulfillment (40 points): All parts answered
        query_fulfillment = 0
        if has_eligibility:
            query_fulfillment += 13
        if has_deadline:
            query_fulfillment += 13
        if has_budget:
            query_fulfillment += 14

        # Specificity (25 points): Concrete details
        specificity = 0
        if has_eligibility_details:
            specificity += 8
        if has_deadline_details:
            specificity += 8
        if has_budget_details:
            specificity += 9

        # Factual Accuracy (25 points): Correct EU funding information
        factual_accuracy = 0
        if has_eic_content:
            factual_accuracy += 10
        # Check for correct Netherlands context
        if "netherlands" in response_lower or "eu member state" in response_lower:
            factual_accuracy += 5
        # Check for correct EIC grant amount (€2.5M)
        if "2.5" in response_lower and "million" in response_lower:
            factual_accuracy += 10

        # Actionability (10 points): Clear next steps
        actionability = 0
        if "next step" in response_lower:
            actionability += 5
        if any(x in response_lower for x in ["portal", "ncp", "ec.europa.eu", "eic.ec"]):
            actionability += 5

        total_score = query_fulfillment + specificity + factual_accuracy + actionability

        return {
            "total_score": total_score,
            "query_fulfillment": query_fulfillment,
            "specificity": specificity,
            "factual_accuracy": factual_accuracy,
            "actionability": actionability,
            "passed": total_score >= 80,
            "details": {
                "has_eligibility": has_eligibility,
                "has_eligibility_details": has_eligibility_details,
                "has_deadline": has_deadline,
                "has_deadline_details": has_deadline_details,
                "has_budget": has_budget,
                "has_budget_details": has_budget_details,
                "has_eic_content": has_eic_content,
            },
        }

    # ==================== Core Scenario Tests ====================

    @pytest.mark.asyncio
    async def test_primary_scenario_sme_netherlands_eic(self, conversation_id):
        """Test the primary scenario: SME from Netherlands asking about EIC Accelerator."""
        query = self.PRIMARY_QUERY

        result = await self.send_query(conversation_id, query)
        assert not result.get("error"), f"Query failed: {result}"

        response = result["response"]
        score = self.score_response(response)

        assert score["passed"], (
            f"Score {score['total_score']}/100 below threshold 80. " f"Details: {score['details']}"
        )

    @pytest.mark.asyncio
    async def test_eic_eligibility_only(self, conversation_id):
        """Test EIC eligibility question alone."""
        query = "Am I eligible for EIC Accelerator as an SME?"

        result = await self.send_query(conversation_id, query)
        assert not result.get("error"), f"Query failed: {result}"

        response = result["response"]
        response_lower = response.lower()

        # Should contain eligibility information
        assert any(
            x in response_lower for x in ["eligible", "eligibility", "sme"]
        ), "Response should address eligibility"
        assert any(
            x in response_lower for x in ["eic", "accelerator"]
        ), "Response should mention EIC Accelerator"

    @pytest.mark.asyncio
    async def test_eic_deadline_only(self, conversation_id):
        """Test EIC deadline question alone."""
        query = "What's the deadline for EIC Accelerator?"

        result = await self.send_query(conversation_id, query)
        assert not result.get("error"), f"Query failed: {result}"

        response = result["response"]
        response_lower = response.lower()

        # Should contain deadline information
        assert any(
            x in response_lower for x in ["deadline", "cut-off", "2026", "march", "october"]
        ), "Response should address deadlines"

    @pytest.mark.asyncio
    async def test_eic_budget_only(self, conversation_id):
        """Test EIC budget question alone."""
        query = "What budget can I request for EIC Accelerator?"

        result = await self.send_query(conversation_id, query)
        assert not result.get("error"), f"Query failed: {result}"

        response = result["response"]
        response_lower = response.lower()

        # Should contain budget information
        assert any(
            x in response_lower for x in ["budget", "grant", "equity", "million", "€"]
        ), "Response should address budget"
        assert "2.5" in response_lower, "Response should mention €2.5M grant amount"

    # ==================== Variant Query Tests ====================

    @pytest.mark.asyncio
    async def test_variant_german_sme(self, conversation_id):
        """Test variant: SME from Germany."""
        query = (
            "We are a German SME. Can we apply for EIC Accelerator? "
            "What's the budget and deadline?"
        )

        result = await self.send_query(conversation_id, query)
        assert not result.get("error"), f"Query failed: {result}"

        response = result["response"]
        response_lower = response.lower()

        assert "eic" in response_lower or "accelerator" in response_lower
        assert any(
            x in response_lower for x in ["eligible", "eligibility", "eu member state", "germany"]
        )

    @pytest.mark.asyncio
    async def test_variant_startup_eligibility(self, conversation_id):
        """Test variant: Startup asking about EIC."""
        query = "Is my startup eligible for EIC Accelerator? How much funding can I get?"

        result = await self.send_query(conversation_id, query)
        assert not result.get("error"), f"Query failed: {result}"

        response = result["response"]
        response_lower = response.lower()

        assert any(x in response_lower for x in ["eligible", "eligibility", "sme", "startup"])
        assert any(x in response_lower for x in ["budget", "grant", "million", "€"])

    @pytest.mark.asyncio
    async def test_variant_associated_country(self, conversation_id):
        """Test variant: Associated country (Israel)."""
        query = "Can an SME from Israel apply for EIC Accelerator? What's available?"

        result = await self.send_query(conversation_id, query)
        assert not result.get("error"), f"Query failed: {result}"

        response = result["response"]
        response_lower = response.lower()

        # Should address eligibility and mention associated country status
        assert any(x in response_lower for x in ["eligible", "eligibility", "associated", "israel"])

    # ==================== Specificity Tests ====================

    @pytest.mark.asyncio
    async def test_contains_sme_definition(self, conversation_id):
        """Test that response contains EU SME definition criteria."""
        query = self.PRIMARY_QUERY

        result = await self.send_query(conversation_id, query)
        response = result["response"]
        response_lower = response.lower()

        # Should contain SME definition criteria
        assert any(
            x in response_lower for x in ["250 employee", "< 250", "€50 million", "turnover"]
        ), "Response should include SME definition criteria"

    @pytest.mark.asyncio
    async def test_contains_specific_deadline(self, conversation_id):
        """Test that response contains specific deadline dates."""
        query = self.PRIMARY_QUERY

        result = await self.send_query(conversation_id, query)
        response = result["response"]
        response_lower = response.lower()

        # Should contain specific deadline dates
        assert any(
            month in response_lower for month in ["march", "october"]
        ), "Response should include specific deadline months"
        assert "2026" in response_lower, "Response should include year 2026"

    @pytest.mark.asyncio
    async def test_contains_budget_amounts(self, conversation_id):
        """Test that response contains specific budget amounts."""
        query = self.PRIMARY_QUERY

        result = await self.send_query(conversation_id, query)
        response = result["response"]
        response_lower = response.lower()

        # Should contain specific budget amounts
        assert "2.5" in response_lower, "Response should mention €2.5M grant"
        assert (
            any(x in response_lower for x in ["15 million", "15m", "€15"])
            or "equity" in response_lower
        ), "Response should mention equity component"

    # ==================== Actionability Tests ====================

    @pytest.mark.asyncio
    async def test_contains_next_steps(self, conversation_id):
        """Test that response contains actionable next steps."""
        query = self.PRIMARY_QUERY

        result = await self.send_query(conversation_id, query)
        response = result["response"]
        response_lower = response.lower()

        # Should contain next steps section
        assert "next step" in response_lower, "Response should include 'Next Steps' section"

    @pytest.mark.asyncio
    async def test_contains_useful_links(self, conversation_id):
        """Test that response contains useful links."""
        query = self.PRIMARY_QUERY

        result = await self.send_query(conversation_id, query)
        response = result["response"]
        response_lower = response.lower()

        # Should contain relevant links
        assert any(
            x in response_lower for x in ["ec.europa.eu", "eic.ec", "portal", "ncp"]
        ), "Response should include relevant links"

    # ==================== Edge Case Tests ====================

    @pytest.mark.asyncio
    async def test_not_routed_to_erasmus(self, conversation_id):
        """Test that EIC query is NOT routed to Erasmus+ tools."""
        query = self.PRIMARY_QUERY

        result = await self.send_query(conversation_id, query)
        response = result["response"]
        response_lower = response.lower()

        # Should NOT contain Erasmus+ content
        assert (
            "erasmus" not in response_lower or "eic" in response_lower
        ), "Response should not be about Erasmus+ for an EIC query"

    @pytest.mark.asyncio
    async def test_handles_eic_with_horizon_mention(self, conversation_id):
        """Test that Horizon Europe + EIC query works correctly."""
        query = (
            "Can my SME apply for Horizon Europe EIC Accelerator? "
            "What's the deadline and budget?"
        )

        result = await self.send_query(conversation_id, query)
        assert not result.get("error"), f"Query failed: {result}"

        response = result["response"]
        response_lower = response.lower()

        assert any(
            x in response_lower for x in ["eic", "accelerator"]
        ), "Response should address EIC Accelerator"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
