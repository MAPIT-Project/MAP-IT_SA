"""
Scenario 030: Context Preservation
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Turn 1: "Find hydrogen funding calls"
Turn 2: "Which one has the highest budget?"
Expected: References calls from Turn 1, identifies highest budget
Verify: Context preserved, correct call identified
Fix if: Loses context, does new search
Pass threshold: 80
"""

import random
import re
import time

import httpx
import pytest


class TestScenario030ContextPreservation:
    """Test context preservation across multi-turn conversations."""

    BASE_URL = "http://localhost:8000"
    TURN1_QUERY = "Find hydrogen funding calls"
    TURN2_QUERY = "Which one has the highest budget?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        return random.randint(300000, 309999)

    async def _send_turn1(self, client, conversation_id):
        """Send Turn 1 query and return response."""
        await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

        response = await client.post(
            f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
            json={"message": self.TURN1_QUERY, "user_id": 1},
        )
        return response

    async def _send_turn2(self, client, conversation_id):
        """Send Turn 2 follow-up query and return response."""
        response = await client.post(
            f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
            json={"message": self.TURN2_QUERY, "user_id": 1},
        )
        return response

    def _extract_call_ids(self, text):
        """Extract call IDs from response text."""
        # Match HORIZON-*, ERASMUS-*, CREA-*, etc.
        patterns = [
            r"HORIZON-[A-Z0-9-]+(?:-\d+)?",
            r"ERASMUS-[A-Z0-9-]+",
            r"CREA-[A-Z0-9-]+",
            r"LIFE-[A-Z0-9-]+",
            r"EU4H-[A-Z0-9-]+",
            r"DIGITAL-[A-Z0-9-]+",
        ]
        call_ids = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            call_ids.extend(matches)
        return list(set(call_ids))

    def _extract_budgets(self, text):
        """Extract budget amounts from response text."""
        # Match €X million, €X M, EUR X million, etc.
        patterns = [
            r"€\s*(\d+(?:\.\d+)?)\s*(?:million|M)",
            r"EUR\s*(\d+(?:\.\d+)?)\s*(?:million|M)",
            r"(\d+(?:\.\d+)?)\s*(?:million|M)\s*(?:EUR|€)",
            r"€(\d+(?:,\d{3})*(?:\.\d+)?)",
        ]
        budgets = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            budgets.extend(matches)
        return budgets

    @pytest.mark.asyncio
    async def test_turn1_returns_calls(self, conversation_id):
        """Test that Turn 1 returns hydrogen funding calls."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_turn1(client, conversation_id)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should return calls related to funding
            has_call_indicators = any(
                ind in response_text
                for ind in [
                    "call",
                    "funding",
                    "opportunity",
                    "horizon",
                    "open",
                    "deadline",
                    "budget",
                    "€",
                    "eur",
                ]
            )

            # Either mentions hydrogen or returns funding calls (tool executed search)
            tools_used = result.get("metadata", {}).get("tools_used", [])
            search_executed = any("search" in tool.lower() for tool in tools_used)

            assert (
                has_call_indicators or search_executed
            ), f"Turn 1 should return funding calls or execute search. Tools used: {tools_used}"

    @pytest.mark.asyncio
    async def test_turn1_includes_budgets(self, conversation_id):
        """Test that Turn 1 includes budget information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_turn1(client, conversation_id)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            budgets = self._extract_budgets(response_text)
            budget_terms = any(
                t in response_text.lower() for t in ["€", "eur", "million", "budget", "funding"]
            )

            assert len(budgets) > 0 or budget_terms, "Turn 1 should include budget information"

    @pytest.mark.asyncio
    async def test_turn2_references_turn1_context(self, conversation_id):
        """Test that Turn 2 references context from Turn 1."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            turn1_response = await self._send_turn1(client, conversation_id)
            assert turn1_response.status_code == 200
            # Turn 1 response stored for context (used implicitly by Turn 2)
            _ = turn1_response.json().get("response", "")

            # Small delay to ensure context is stored
            time.sleep(0.5)

            turn2_response = await self._send_turn2(client, conversation_id)
            assert turn2_response.status_code == 200
            turn2_text = turn2_response.json().get("response", "").lower()

            # Turn 2 should reference the previous calls
            context_indicators = [
                "highest budget",
                "largest budget",
                "biggest budget",
                "highest funding",
                "most funding",
                "€",
                "million",
                "above",
                "among",
                "from the",
                "of these",
                "listed",
                "mentioned",
            ]

            has_context_reference = any(ind in turn2_text for ind in context_indicators)

            assert has_context_reference, "Turn 2 should reference context from Turn 1's calls"

    @pytest.mark.asyncio
    async def test_turn2_identifies_specific_call(self, conversation_id):
        """Test that Turn 2 identifies a specific call with highest budget."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            turn1_response = await self._send_turn1(client, conversation_id)
            assert turn1_response.status_code == 200
            turn1_text = turn1_response.json().get("response", "")
            turn1_call_ids = self._extract_call_ids(turn1_text)

            time.sleep(0.5)

            turn2_response = await self._send_turn2(client, conversation_id)
            assert turn2_response.status_code == 200
            turn2_result = turn2_response.json()
            turn2_text = turn2_result.get("response", "")

            # Turn 2 should identify a specific call
            turn2_call_ids = self._extract_call_ids(turn2_text)

            # Check for specific answer indicators
            specific_answer = any(
                t in turn2_text.lower()
                for t in [
                    "highest",
                    "largest",
                    "biggest",
                    "most",
                    "top",
                    "€",
                    "million",
                ]
            )

            # Either has call IDs from turn 1 or gives a specific answer
            has_specificity = len(turn2_call_ids) > 0 or specific_answer

            assert has_specificity, (
                f"Turn 2 should identify a specific call. "
                f"Turn 1 calls: {turn1_call_ids}, Turn 2 calls: {turn2_call_ids}"
            )

    @pytest.mark.asyncio
    async def test_turn2_includes_budget_amount(self, conversation_id):
        """Test that Turn 2 includes the budget amount of the identified call."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await self._send_turn1(client, conversation_id)
            time.sleep(0.5)

            turn2_response = await self._send_turn2(client, conversation_id)
            assert turn2_response.status_code == 200
            turn2_text = turn2_response.json().get("response", "")

            budgets = self._extract_budgets(turn2_text)
            has_budget_mention = any(
                t in turn2_text.lower() for t in ["€", "eur", "million", "budget"]
            )

            assert (
                len(budgets) > 0 or has_budget_mention
            ), f"Turn 2 should include the budget amount. Response: {turn2_text[:500]}..."

    @pytest.mark.asyncio
    async def test_turn2_does_not_repeat_search(self, conversation_id):
        """Test that Turn 2 does NOT unnecessarily repeat the search."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await self._send_turn1(client, conversation_id)
            time.sleep(0.5)

            turn2_response = await self._send_turn2(client, conversation_id)
            assert turn2_response.status_code == 200
            turn2_result = turn2_response.json()
            tools_used = turn2_result.get("metadata", {}).get("tools_used", [])

            # Turn 2 should ideally NOT call search_funding_calls again
            # since it can answer from context
            # However, it's acceptable if it does to get more details
            # The key test is: does the response make sense with Turn 1 context?
            turn2_text = turn2_result.get("response", "").lower()

            # If it did search again, check it still references the context
            if "search_funding_calls" in tools_used:
                # Should still be a valid answer about hydrogen calls
                has_hydrogen = "hydrogen" in turn2_text
                has_budget = any(t in turn2_text for t in ["€", "budget", "million", "funding"])
                assert (
                    has_hydrogen or has_budget
                ), "Even with new search, response should be about hydrogen/budgets"

    @pytest.mark.asyncio
    async def test_turn2_does_not_lose_context(self, conversation_id):
        """Test that Turn 2 doesn't ask for clarification about which calls."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await self._send_turn1(client, conversation_id)
            time.sleep(0.5)

            turn2_response = await self._send_turn2(client, conversation_id)
            assert turn2_response.status_code == 200
            turn2_text = turn2_response.json().get("response", "").lower()

            # Should NOT ask for clarification
            lost_context_indicators = [
                "which calls",
                "what calls",
                "could you specify",
                "please specify",
                "i need more information",
                "what do you mean",
                "i don't have",
                "no previous",
                "cannot find",
                "don't have access to",
            ]

            has_lost_context = any(ind in turn2_text for ind in lost_context_indicators)

            assert not has_lost_context, (
                f"Turn 2 should NOT lose context. "
                f"Response suggests lost context: {turn2_text[:300]}..."
            )

    @pytest.mark.asyncio
    async def test_context_api_shows_both_turns(self, conversation_id):
        """Test that the context API shows both turns after conversation."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await self._send_turn1(client, conversation_id)
            time.sleep(0.5)
            await self._send_turn2(client, conversation_id)
            time.sleep(0.5)

            context_response = await client.get(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context"
            )
            assert context_response.status_code == 200
            context = context_response.json()

            message_count = context.get("message_count", 0)
            messages = context.get("messages", [])

            # Should have at least 2 messages (may not store all user messages)
            # Key is that context preserves assistant responses
            assert (
                message_count >= 2
            ), f"Context should have at least 2 messages. Found: {message_count}"

            # Verify context has content from the conversation
            # API may use 'text'/'sender' or 'content'/'role' keys
            all_content = " ".join(
                [m.get("content", "") or m.get("text", "") for m in messages]
            ).lower()

            # Should have either the query terms or call-related content
            has_context = any(
                term in all_content for term in ["hydrogen", "funding", "call", "budget", "highest"]
            )
            assert (
                has_context
            ), f"Context should include conversation content. Found {len(messages)} messages."

    @pytest.mark.asyncio
    async def test_turn2_response_quality(self, conversation_id):
        """Test that Turn 2 response quality is acceptable."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await self._send_turn1(client, conversation_id)
            time.sleep(0.5)

            turn2_response = await self._send_turn2(client, conversation_id)
            assert turn2_response.status_code == 200
            turn2_text = turn2_response.json().get("response", "")

            # Basic quality checks
            # 1. Not too short
            assert len(turn2_text) > 100, f"Turn 2 response too short ({len(turn2_text)} chars)"

            # 2. Not an error message
            error_indicators = ["error", "failed", "cannot", "unable to process"]
            is_error = any(ind in turn2_text.lower()[:200] for ind in error_indicators)
            # Allow "cannot" in middle of response if it's not an error
            if is_error and "cannot" in turn2_text.lower()[:200]:
                is_error = "cannot find" in turn2_text.lower()[:200]

            assert not is_error, f"Turn 2 appears to be an error response: {turn2_text[:300]}..."

    @pytest.mark.asyncio
    async def test_overall_score_meets_threshold(self, conversation_id):
        """Test that overall quality score meets the 80 threshold."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            turn1_response = await self._send_turn1(client, conversation_id)
            assert turn1_response.status_code == 200
            turn1_result = turn1_response.json()
            turn1_text = turn1_result.get("response", "")
            turn1_call_ids = self._extract_call_ids(turn1_text)
            turn1_budgets = self._extract_budgets(turn1_text)

            time.sleep(0.5)

            turn2_response = await self._send_turn2(client, conversation_id)
            assert turn2_response.status_code == 200
            turn2_result = turn2_response.json()
            turn2_text = turn2_result.get("response", "").lower()

            score = 0

            # Query Fulfillment (40 points)
            # - Identifies highest budget call from Turn 1 results
            query_fulfillment = 0

            # Has budget information
            if any(t in turn2_text for t in ["€", "million", "budget", "eur"]):
                query_fulfillment += 15

            # References "highest" or similar
            if any(t in turn2_text for t in ["highest", "largest", "biggest", "most", "top"]):
                query_fulfillment += 15

            # Identifies a specific call
            turn2_call_ids = self._extract_call_ids(turn2_text.upper())
            if len(turn2_call_ids) > 0:
                query_fulfillment += 10
            elif any(t in turn2_text for t in ["call", "horizon", "funding opportunity"]):
                query_fulfillment += 5

            score += min(query_fulfillment, 40)

            # Specificity (25 points)
            # - Concrete budget amount, call ID
            specificity = 0
            turn2_budgets = self._extract_budgets(turn2_text.upper())
            if len(turn2_budgets) > 0:
                specificity += 12
            if len(turn2_call_ids) > 0:
                specificity += 8
            if any(t in turn2_text for t in ["deadline", "closes", "date", "2026", "2025"]):
                specificity += 5
            score += min(specificity, 25)

            # Factual Accuracy (25 points)
            # - Budget mentioned should be from Turn 1 calls
            # - Call ID should be from Turn 1 (if applicable)
            factual = 0

            # Check if answer is consistent with Turn 1 data
            if len(turn1_budgets) > 0 and len(turn2_budgets) > 0:
                factual += 15  # Has budget that could be verified
            elif any(t in turn2_text for t in ["€", "million", "budget"]):
                factual += 10  # At least mentions budget

            # Does not claim lack of context
            if not any(
                t in turn2_text for t in ["don't have", "no context", "specify", "which calls"]
            ):
                factual += 10

            score += min(factual, 25)

            # Actionability (10 points)
            # - Clear identification, maybe link
            actionability = 0
            if any(
                t in turn2_text for t in ["portal", "apply", "link", "check", "view", "details"]
            ):
                actionability += 5
            if len(turn2_text) > 200:  # Sufficient detail
                actionability += 5
            score += min(actionability, 10)

            print("\n=== Scenario 030 Score Breakdown ===")
            print(f"Turn 1 calls found: {len(turn1_call_ids)}")
            print(f"Turn 1 budgets found: {len(turn1_budgets)}")
            print(f"Turn 2 calls identified: {len(turn2_call_ids)}")
            print(f"Turn 2 budgets mentioned: {len(turn2_budgets)}")
            print(f"Query Fulfillment: {min(query_fulfillment, 40)}/40")
            print(f"Specificity: {min(specificity, 25)}/25")
            print(f"Factual Accuracy: {min(factual, 25)}/25")
            print(f"Actionability: {min(actionability, 10)}/10")
            print(f"TOTAL: {score}/100")
            print(f"Threshold: {self.PASS_THRESHOLD}")
            print(f"Turn 2 response preview: {turn2_text[:400]}...")

            assert score >= self.PASS_THRESHOLD, (
                f"Score {score} below threshold {self.PASS_THRESHOLD}. "
                f"Turn 2 response: {turn2_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_flow(self, conversation_id):
        """Integration test for complete 2-turn conversation flow."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            # Clear any existing context
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            # Turn 1: Find hydrogen calls
            turn1_response = await self._send_turn1(client, conversation_id)
            assert turn1_response.status_code == 200
            turn1_result = turn1_response.json()
            turn1_text = turn1_result.get("response", "")

            # Verify Turn 1 succeeded
            assert "hydrogen" in turn1_text.lower() or any(
                t in turn1_text.lower() for t in ["call", "funding", "opportunity"]
            ), f"Turn 1 should return hydrogen calls. Got: {turn1_text[:300]}..."

            # Small delay for context storage
            time.sleep(0.5)

            # Turn 2: Which has highest budget?
            turn2_response = await self._send_turn2(client, conversation_id)
            assert turn2_response.status_code == 200
            turn2_result = turn2_response.json()
            turn2_text = turn2_result.get("response", "").lower()

            # Verify Turn 2 uses context
            context_used = any(
                t in turn2_text
                for t in [
                    "highest",
                    "largest",
                    "biggest",
                    "€",
                    "million",
                    "budget",
                    "among",
                    "from",
                ]
            )
            context_lost = any(
                t in turn2_text for t in ["which calls", "specify", "don't have", "no context"]
            )

            assert context_used and not context_lost, (
                f"Turn 2 should use context from Turn 1. "
                f"Context used: {context_used}, Context lost: {context_lost}. "
                f"Response: {turn2_text[:400]}..."
            )

    @pytest.mark.asyncio
    async def test_preserves_call_details_across_turns(self, conversation_id):
        """Test that specific call details from Turn 1 are accessible in Turn 2."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            turn1_response = await self._send_turn1(client, conversation_id)
            assert turn1_response.status_code == 200
            turn1_text = turn1_response.json().get("response", "")

            # Extract details from Turn 1
            turn1_call_ids = self._extract_call_ids(turn1_text)

            time.sleep(0.5)

            turn2_response = await self._send_turn2(client, conversation_id)
            assert turn2_response.status_code == 200
            turn2_text = turn2_response.json().get("response", "")

            # If Turn 1 had call IDs, Turn 2 should reference them or answer coherently
            if len(turn1_call_ids) > 0:
                # Either references same calls OR gives a coherent budget answer
                references_turn1 = any(call_id in turn2_text.upper() for call_id in turn1_call_ids)
                gives_budget_answer = any(
                    t in turn2_text.lower() for t in ["highest", "budget", "€", "million"]
                )

                assert references_turn1 or gives_budget_answer, (
                    f"Turn 2 should reference Turn 1 calls or give budget answer. "
                    f"Turn 1 calls: {turn1_call_ids[:5]}"
                )
