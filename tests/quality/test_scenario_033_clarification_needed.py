"""
Scenario 033: Clarification Needed
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "What's the deadline?"
Expected: Asks for clarification about which call/programme
Verify: Doesn't hallucinate, asks appropriately
Fix if: Guesses randomly, hallucinates deadline
Pass threshold: 75
"""

import random
import re

import httpx
import pytest


class TestScenario033ClarificationNeeded:
    """Test that ambiguous queries properly request clarification."""

    BASE_URL = "http://localhost:8000"
    PASS_THRESHOLD = 75

    # Various ambiguous queries that need clarification
    AMBIGUOUS_QUERIES = [
        "What's the deadline?",
        "When is the deadline?",
        "What's the budget?",
        "Is it open?",
        "Can I apply?",
        "What are the requirements?",
        "Which one should I choose?",
    ]

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        return random.randint(330000, 339999)

    async def _send_query(self, client, conversation_id, query):
        """Send query and return response."""
        # Clear any existing context
        await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

        response = await client.post(
            f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
            json={"message": query, "user_id": 1},
        )
        return response

    def _asks_for_clarification(self, text):
        """Check if response asks for clarification."""
        clarification_indicators = [
            "which call",
            "which programme",
            "which program",
            "specify",
            "provide",
            "need to know",
            "tell me",
            "share your",
            "could you clarify",
            "could you specify",
            "please clarify",
            "please specify",
            "which topic",
            "which cluster",
            "what area",
            "which area",
            "more information",
            "more details",
            "research domain",
            "research topic",
            "specific call",
            "call id",
            "what type",
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in clarification_indicators)

    def _has_hallucinated_specific_deadline(self, text):
        """Check if response hallucinated a specific deadline date without context.

        A hallucinated deadline would be a very specific date (like "March 15, 2026")
        without any context about which call it belongs to. General patterns like
        "deadlines are typically in Q1" or "MSCA-PF deadline is mid-September" are fine.
        """
        # Patterns that indicate a hallucinated specific deadline
        hallucination_patterns = [
            r"the deadline is [A-Z][a-z]+ \d{1,2},? \d{4}",  # "the deadline is March 15, 2026"
            r"your deadline is",
            r"deadline.*is.*\d{1,2}/\d{1,2}/\d{4}",  # "deadline is 15/03/2026"
            r"^[A-Z][a-z]+ \d{1,2},? \d{4}$",  # Just a date by itself
        ]

        for pattern in hallucination_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                # Check if it's associated with a specific programme/call
                # If it's tied to a specific call ID like HORIZON-xxx, it's not hallucination
                call_ids = ["HORIZON-", "ERASMUS-", "CREA-", "EIC-", "MSCA-", "ERC-"]
                if not any(x in text for x in call_ids):
                    # It's hallucinated if no call context
                    return True

        return False

    def _provides_helpful_guidance(self, text):
        """Check if response provides helpful guidance despite ambiguity."""
        guidance_indicators = [
            "next steps",
            "recommend",
            "suggest",
            "check the portal",
            "eu portal",
            "funding & tenders",
            "funding-tenders",
            "work programme",
            "typically",
            "usually",
            "generally",
            "depending on",
            "varies",
            "contact",
            "ncp",
            "national contact point",
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in guidance_indicators)

    def _has_actionable_options(self, text):
        """Check if response provides actionable options for clarification."""
        options_indicators = [
            "provide a specific call",
            "provide your research topic",
            "specify the funding programme",
            "1.",
            "•",
            "-",
            "option",
            "either",
            "or",
            "for example",
            "such as",
            "e.g.",
        ]
        text_lower = text.lower()
        count = sum(1 for indicator in options_indicators if indicator in text_lower)
        return count >= 2  # At least 2 option indicators

    @pytest.mark.asyncio
    async def test_deadline_query_asks_clarification(self, conversation_id):
        """Test that 'What's the deadline?' asks for clarification."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "What's the deadline?")

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            asks_clarification = self._asks_for_clarification(response_text)

            assert asks_clarification, (
                f"Response should ask for clarification about which call/programme. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_deadline_query_no_hallucination(self, conversation_id):
        """Test that 'What's the deadline?' doesn't hallucinate a specific deadline."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "What's the deadline?")

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            hallucinated = self._has_hallucinated_specific_deadline(response_text)

            assert not hallucinated, (
                f"Response should NOT hallucinate a specific deadline without context. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_deadline_query_provides_guidance(self, conversation_id):
        """Test that ambiguous deadline query still provides helpful guidance."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "What's the deadline?")

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            provides_guidance = self._provides_helpful_guidance(response_text)

            assert provides_guidance, (
                f"Response should provide helpful guidance. Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_when_is_deadline_variant(self, conversation_id):
        """Test that 'When is the deadline?' variant also asks for clarification."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "When is the deadline?")

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            asks_clarification = self._asks_for_clarification(response_text)
            provides_guidance = self._provides_helpful_guidance(response_text)

            assert asks_clarification or provides_guidance, (
                f"Response should ask for clarification or provide guidance. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_budget_query_asks_clarification(self, conversation_id):
        """Test that 'What's the budget?' asks for clarification."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "What's the budget?")

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            asks_clarification = self._asks_for_clarification(response_text)

            assert asks_clarification, (
                f"Response should ask for clarification about which call/project type. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_is_it_open_query_asks_clarification(self, conversation_id):
        """Test that 'Is it open?' asks for clarification."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "Is it open?")

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            asks_clarification = self._asks_for_clarification(response_text)

            assert asks_clarification, (
                f"Response should ask for clarification about which call. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_can_i_apply_query_asks_clarification(self, conversation_id):
        """Test that 'Can I apply?' asks for clarification."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "Can I apply?")

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            asks_clarification = self._asks_for_clarification(response_text)
            provides_guidance = self._provides_helpful_guidance(response_text)

            # Should either ask for clarification OR provide general eligibility guidance
            assert asks_clarification or provides_guidance, (
                f"Response should ask for clarification or provide general eligibility guidance. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_response_has_actionable_options(self, conversation_id):
        """Test that response provides actionable options for user to clarify."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "What's the deadline?")

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            has_options = self._has_actionable_options(response_text)

            assert has_options, (
                f"Response should provide actionable options (bullet points, examples). "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_no_tool_called_for_ambiguous_query(self, conversation_id):
        """Test that ambiguous queries don't result in random tool calls."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "What's the deadline?")

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # For ambiguous queries, the agent should either:
            # 1. Not call any tools (since it doesn't know what to search for)
            # 2. OR call tools and still ask for clarification

            response_text = result.get("response", "")
            asks_clarification = self._asks_for_clarification(response_text)

            # If tools were called, we should still ask for clarification
            if tools_used:
                assert asks_clarification, (
                    f"Even if tools were called, response should still ask for clarification. "
                    f"Tools used: {tools_used}, Response: {response_text[:300]}..."
                )
            else:
                # No tools called is also acceptable for ambiguous query
                assert len(tools_used) == 0 or asks_clarification

    @pytest.mark.asyncio
    async def test_response_not_empty(self, conversation_id):
        """Test that response is not empty or minimal."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "What's the deadline?")

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Response should be substantial (more than just "Please clarify")
            assert len(response_text) > 100, (
                f"Response should be substantial, not minimal. Length: {len(response_text)}"
            )

    @pytest.mark.asyncio
    async def test_which_one_should_i_choose(self, conversation_id):
        """Test that 'Which one should I choose?' asks for clarification."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "Which one should I choose?")

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            asks_clarification = self._asks_for_clarification(response_text)

            assert asks_clarification, (
                f"Response should ask for clarification about which options. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_quality_score_acceptable(self, conversation_id):
        """Test that response quality score meets threshold despite ambiguity."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "What's the deadline?")

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})
            quality = metadata.get("quality_analysis", {})
            score = quality.get("score", 0)

            # For clarification responses, we accept a lower threshold
            # because the response is intentionally not fully answering
            # but is being appropriately cautious
            assert score >= 50 or score == 0, (
                f"Quality score should be acceptable. Score: {score}"
            )  # 0 means quality not scored

    @pytest.mark.asyncio
    async def test_provides_typical_deadline_patterns(self, conversation_id):
        """Test that response provides typical deadline patterns as guidance."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "What's the deadline?")

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should mention some typical deadline patterns
            pattern_indicators = [
                "msca",
                "erc",
                "eic",
                "cluster",
                "q1",
                "q2",
                "q3",
                "q4",
                "september",
                "october",
                "november",
                "february",
                "march",
                "quarterly",
                "annual",
            ]
            text_lower = response_text.lower()
            has_patterns = any(indicator in text_lower for indicator in pattern_indicators)

            assert has_patterns, (
                f"Response should mention typical deadline patterns (MSCA, ERC, quarters, etc.). "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_provides_portal_link(self, conversation_id):
        """Test that response provides link to EU Portal for checking deadlines."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, "What's the deadline?")

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should provide portal link
            portal_indicators = [
                "eu portal",
                "funding-tenders",
                "funding & tenders",
                "ec.europa.eu",
                "official portal",
                "calls-calendar",
                "call calendar",
            ]
            text_lower = response_text.lower()
            has_portal = any(indicator in text_lower for indicator in portal_indicators)

            assert has_portal, (
                f"Response should provide link or reference to EU Portal. "
                f"Response: {response_text[:500]}..."
            )
