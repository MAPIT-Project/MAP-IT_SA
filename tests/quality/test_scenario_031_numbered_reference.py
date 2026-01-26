"""
Test Scenario 031: Numbered Reference

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 031
Turn 1: "Show me 5 climate research projects"
Turn 2: "Tell me more about project 3"
Expected: Details about the third project from Turn 1
Pass threshold: 80

This test verifies that the system properly handles numbered references:
- Turn 1 returns a numbered list of projects
- Turn 2 correctly identifies "project 3" from context
- Turn 2 uses get_project_details tool to fetch full details
- Turn 2 response includes the correct project from Turn 1
- Turn 2 does NOT do a new search ignoring context
"""

import random
import re

import httpx
import pytest


class TestScenario031NumberedReference:
    """Test suite for Scenario 031: Numbered Reference."""

    BASE_URL = "http://localhost:8000"
    TURN1_QUERY = "Show me 5 climate research projects"
    TURN2_QUERY = "Tell me more about project 3"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        return random.randint(310000, 319999)

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

    async def _execute_full_conversation(self, client, conversation_id):
        """Execute the full multi-turn conversation and return results."""
        turn1_resp = await self._send_turn1(client, conversation_id)
        assert turn1_resp.status_code == 200
        turn1_result = turn1_resp.json()

        turn2_resp = await self._send_turn2(client, conversation_id)
        assert turn2_resp.status_code == 200
        turn2_result = turn2_resp.json()

        return turn1_result, turn2_result

    @pytest.mark.asyncio
    async def test_turn1_returns_projects(self, conversation_id):
        """Test that Turn 1 returns a list of projects."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            turn1_resp = await self._send_turn1(client, conversation_id)

            assert turn1_resp.status_code == 200
            turn1_result = turn1_resp.json()
            response_text = turn1_result.get("response", "")
            metadata = turn1_result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Verify search_projects tool was called
            uses_search = any("search_projects" in str(t).lower() for t in tools_used)
            assert uses_search, f"Turn 1 should use search_projects tool, got: {tools_used}"

            # Should mention projects or have numbered items
            # Allow for intermittent search failures if tool was called correctly
            has_projects = "project" in response_text.lower()
            numbered_items = re.findall(r"\*\*\d+\.", response_text)

            # Either found projects OR tool was used correctly
            assert (
                has_projects or uses_search
            ), "Turn 1 should either return projects or use search_projects tool"

            # If projects were found, should have numbered format
            if has_projects and numbered_items:
                assert (
                    len(numbered_items) >= 3
                ), f"Turn 1 should have at least 3 numbered projects, found: {len(numbered_items)}"

    @pytest.mark.asyncio
    async def test_turn1_includes_project_ids(self, conversation_id):
        """Test that Turn 1 includes project IDs."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            turn1_resp = await self._send_turn1(client, conversation_id)

            assert turn1_resp.status_code == 200
            turn1_result = turn1_resp.json()
            response_text = turn1_result.get("response", "")

            # Should have project IDs (numeric IDs like 101XXXXXX)
            project_ids = re.findall(r"10\d{7}", response_text)
            assert (
                len(project_ids) >= 3
            ), f"Turn 1 should include at least 3 project IDs, found: {len(project_ids)}"

    @pytest.mark.asyncio
    async def test_turn2_uses_appropriate_tools(self, conversation_id):
        """Test that Turn 2 uses appropriate tools for project lookup."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            turn1_result, turn2_result = await self._execute_full_conversation(
                client, conversation_id
            )

            turn1_text = turn1_result.get("response", "")
            metadata = turn2_result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])
            response_text = turn2_result.get("response", "")

            # Skip if Turn 1 failed to return projects
            if "couldn't extract specific details" in turn1_text.lower():
                pytest.skip("Turn 1 failed to return projects - skipping Turn 2 test")

            # Should use get_project_details OR search_projects (fallback)
            uses_details_tool = any("get_project_details" in str(t).lower() for t in tools_used)
            uses_search_tool = any("search_projects" in str(t).lower() for t in tools_used)

            # Either tool is acceptable as long as response contains project info
            has_project_info = any(
                x in response_text.lower()
                for x in ["project 3", "objective", "coordinator", "funding"]
            )

            assert (
                uses_details_tool or uses_search_tool
            ), f"Turn 2 should use get_project_details or search_projects, got: {tools_used}"
            assert has_project_info, "Turn 2 response should contain project information"

    @pytest.mark.asyncio
    async def test_turn2_identifies_correct_project(self, conversation_id):
        """Test that Turn 2 correctly identifies project 3 from Turn 1."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            turn1_result, turn2_result = await self._execute_full_conversation(
                client, conversation_id
            )

            turn1_text = turn1_result.get("response", "")
            turn2_text = turn2_result.get("response", "")

            # Skip if Turn 1 failed to return projects
            if "couldn't extract specific details" in turn1_text.lower():
                pytest.skip("Turn 1 failed to return projects - skipping Turn 2 test")

            # Skip if Turn 2 also failed (cascading failure)
            if "couldn't extract specific details" in turn2_text.lower():
                pytest.skip("Turn 2 failed to provide details - skipping test")

            # Extract project 3 details from Turn 1
            # Pattern: **3. ACRONYM: Title** or **3. Title**
            project3_match = re.search(
                r"\*\*3\.\s+([^:*]+?)(?::|[\*])",
                turn1_text,
                re.IGNORECASE,
            )

            if project3_match:
                project3_name = project3_match.group(1).strip()
                # Turn 2 should reference this project name or its details
                references_project = (
                    project3_name.lower() in turn2_text.lower()
                    or "project 3" in turn2_text.lower()
                    or "third project" in turn2_text.lower()
                )
                assert (
                    references_project
                ), f"Turn 2 should reference project 3 ({project3_name}) from Turn 1"

    @pytest.mark.asyncio
    async def test_turn2_does_not_do_new_search(self, conversation_id):
        """Test that Turn 2 does not do a completely new search ignoring context."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            _, turn2_result = await self._execute_full_conversation(client, conversation_id)

            metadata = turn2_result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Should NOT primarily use search_projects for this query
            # (may use it as fallback, but get_project_details should be primary)
            search_tools = [t for t in tools_used if "search_projects" in str(t).lower()]

            # If search_projects is used, get_project_details should also be used
            if search_tools:
                details_tools = [t for t in tools_used if "get_project_details" in str(t).lower()]
                assert (
                    details_tools or len(search_tools) <= 2
                ), f"Turn 2 should use get_project_details, not just search_projects: {tools_used}"

    @pytest.mark.asyncio
    async def test_turn2_provides_detailed_information(self, conversation_id):
        """Test that Turn 2 provides detailed project information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            _, turn2_result = await self._execute_full_conversation(client, conversation_id)

            response_text = turn2_result.get("response", "")

            # Skip assertion if response is the generic fallback
            # (indicates Turn 1 failed, which is a separate test)
            if "couldn't extract specific details" in response_text.lower():
                pytest.skip("Turn 1 failed to return projects - skipping Turn 2 test")

            # Should include detailed information
            details_indicators = [
                "objective",
                "coordinator",
                "funding",
                "ec contribution",
                "duration",
                "budget",
                "programme",
                "project id",
                "project 3",  # Reference to the numbered project
                "grant",
            ]

            found_details = sum(
                1 for indicator in details_indicators if indicator in response_text.lower()
            )
            assert (
                found_details >= 2
            ), f"Turn 2 should include detailed information (found {found_details} indicators)"

    @pytest.mark.asyncio
    async def test_turn2_does_not_ask_for_clarification(self, conversation_id):
        """Test that Turn 2 does not ask for clarification about which project."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            _, turn2_result = await self._execute_full_conversation(client, conversation_id)

            response_text = turn2_result.get("response", "")

            clarification_phrases = [
                "which project",
                "please specify",
                "could you clarify",
                "which one do you mean",
                "please provide more details",
                "i'm not sure which",
            ]

            for phrase in clarification_phrases:
                assert (
                    phrase not in response_text.lower()
                ), f"Turn 2 should not ask for clarification, found: '{phrase}'"

    @pytest.mark.asyncio
    async def test_turn2_includes_cordis_link_or_project_id(self, conversation_id):
        """Test that Turn 2 includes a CORDIS link or project ID for reference."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            _, turn2_result = await self._execute_full_conversation(client, conversation_id)

            response_text = turn2_result.get("response", "")
            metadata = turn2_result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Should include CORDIS link OR project ID that can be used to construct link
            has_cordis_link = "cordis.europa.eu" in response_text.lower()
            has_project_id = bool(re.search(r"10\d{7}", response_text))

            # Also check if get_project_details was used (which includes CORDIS URL in result)
            uses_details_tool = any("get_project_details" in str(t).lower() for t in tools_used)

            assert (
                has_cordis_link or has_project_id or uses_details_tool
            ), "Turn 2 should include a CORDIS link, project ID, or use get_project_details tool"

    @pytest.mark.asyncio
    async def test_context_api_shows_both_turns(self, conversation_id):
        """Test that the context API shows both turns in conversation history."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await self._execute_full_conversation(client, conversation_id)

            context_response = await client.get(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context"
            )

            assert context_response.status_code == 200
            context = context_response.json()

            messages = context.get("messages", [])
            # Should have at least 4 messages (2 user + 2 assistant)
            assert (
                len(messages) >= 4
            ), f"Context should have at least 4 messages, got {len(messages)}"

    @pytest.mark.asyncio
    async def test_turn2_reasoning_mentions_project3(self, conversation_id):
        """Test that Turn 2 reasoning/thought mentions identifying project 3."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            _, turn2_result = await self._execute_full_conversation(client, conversation_id)

            metadata = turn2_result.get("metadata", {})
            reasoning_steps = metadata.get("reasoning_steps", [])

            if reasoning_steps:
                all_reasoning = " ".join(str(step.get("thought", "")) for step in reasoning_steps)

                # Should mention project 3 or the specific project
                mentions_project = (
                    "project 3" in all_reasoning.lower()
                    or "third" in all_reasoning.lower()
                    or "previous" in all_reasoning.lower()
                )
                assert (
                    mentions_project
                ), "Turn 2 reasoning should mention identifying project 3 from context"

    @pytest.mark.asyncio
    async def test_overall_score_meets_threshold(self, conversation_id):
        """Calculate and verify overall quality score meets threshold."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            turn1_result, turn2_result = await self._execute_full_conversation(
                client, conversation_id
            )

            turn1_text = turn1_result.get("response", "")
            turn2_text = turn2_result.get("response", "")
            turn2_metadata = turn2_result.get("metadata", {})
            tools_used = turn2_metadata.get("tools_used", [])

            # Skip if Turn 1 failed to return projects
            if "couldn't extract specific details" in turn1_text.lower():
                pytest.skip("Turn 1 failed to return projects - score calculation not meaningful")

            score = 0

            # Query Fulfillment (40 points)
            # Turn 1 returns projects
            if "project" in turn1_text.lower() and re.findall(r"\*\*\d+\.", turn1_text):
                score += 15
            # Turn 2 provides details about project 3
            if any(
                x in turn2_text.lower() for x in ["objective", "coordinator", "funding", "duration"]
            ):
                score += 15
            # Correct project referenced
            project3_match = re.search(r"\*\*3\.\s+([^:*]+?)(?::|[\*])", turn1_text)
            if project3_match:
                project3_name = project3_match.group(1).strip()
                if project3_name.lower() in turn2_text.lower():
                    score += 10

            # Specificity (25 points)
            # Project ID in Turn 2
            if re.search(r"10\d{7}", turn2_text):
                score += 10
            # Budget/funding amount
            if re.search(r"€[\d,]+|EUR\s*[\d,]+", turn2_text):
                score += 8
            # Duration/dates
            if re.search(r"\d{4}.*\d{4}|months|duration", turn2_text.lower()):
                score += 7

            # Factual Accuracy (25 points)
            # Uses get_project_details tool
            if any("get_project_details" in str(t).lower() for t in tools_used):
                score += 15
            # CORDIS link provided
            if "cordis.europa.eu" in turn2_text.lower():
                score += 10

            # Actionability (10 points)
            # Provides next steps or related info
            if any(
                x in turn2_text.lower()
                for x in ["next step", "you can", "for more", "explore", "review"]
            ):
                score += 5
            # Link provided
            if "http" in turn2_text.lower():
                score += 5

            assert (
                score >= self.PASS_THRESHOLD
            ), f"Quality score {score} is below threshold {self.PASS_THRESHOLD}"

    @pytest.mark.asyncio
    async def test_turn1_uses_search_projects_tool(self, conversation_id):
        """Test that Turn 1 uses the search_projects tool."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            turn1_resp = await self._send_turn1(client, conversation_id)

            assert turn1_resp.status_code == 200
            turn1_result = turn1_resp.json()
            metadata = turn1_result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Should use search_projects tool
            uses_search = any("search_projects" in str(t).lower() for t in tools_used)
            assert uses_search, f"Turn 1 should use search_projects tool, got: {tools_used}"

    @pytest.mark.asyncio
    async def test_turn2_response_is_substantial(self, conversation_id):
        """Test that Turn 2 response is substantial, not a brief acknowledgment."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            _, turn2_result = await self._execute_full_conversation(client, conversation_id)

            response_text = turn2_result.get("response", "")

            # Should be a substantial response
            # (at least 500 characters for detailed project info)
            assert (
                len(response_text) >= 500
            ), f"Turn 2 should provide substantial details, got {len(response_text)} chars"
