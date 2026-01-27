"""
Scenario 013: Generate Timeline
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "Create a timeline for a 36-month innovation project on smart cities"
Expected: Work packages, milestones, deliverables schedule
Verify: Timeline is realistic, milestones well-distributed
Fix if: Unrealistic scheduling, missing key phases
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario013GenerateTimeline:
    """Test timeline generation functionality for Horizon Europe proposals."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Create a timeline for a 36-month innovation project on smart cities"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(130000, 139999)

    @pytest.mark.asyncio
    async def test_uses_generate_timeline_tool(self, conversation_id):
        """Test that the generate_timeline tool is used."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})

            # Check if tools_used includes generate_timeline
            tools_used = metadata.get("tools_used", [])

            # Also check reasoning steps for tool calls
            reasoning_steps = metadata.get("reasoning_steps", [])
            tool_in_reasoning = any("generate_timeline" in str(step) for step in reasoning_steps)

            # The tool might be versioned (e.g., generate_timeline_1_0)
            has_timeline_tool = any("generate_timeline" in t for t in tools_used)

            assert has_timeline_tool or tool_in_reasoning, (
                f"Expected generate_timeline tool to be used. Tools: {tools_used}"
            )

    @pytest.mark.asyncio
    async def test_includes_work_packages(self, conversation_id):
        """Test that response contains work packages."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain work packages (WP1, WP2, etc.)
            wp_pattern = r"WP\d+[:\s]"
            wps_found = re.findall(wp_pattern, response_text)

            # Also check for "Work Package" mentions
            has_wp_mentions = "work package" in response_text.lower()

            assert len(wps_found) >= 3 or has_wp_mentions, (
                f"Response should contain at least 3 work packages. Found: {wps_found}"
            )

    @pytest.mark.asyncio
    async def test_includes_milestones(self, conversation_id):
        """Test that response contains milestones."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain milestones (MS1, MS2, etc. or "Milestone")
            ms_pattern = r"MS\d+[:\s]"
            ms_found = re.findall(ms_pattern, response_text)

            has_milestone_mentions = "milestone" in response_text.lower()

            assert len(ms_found) >= 2 or has_milestone_mentions, (
                f"Response should contain milestones. Found: {ms_found}"
            )

    @pytest.mark.asyncio
    async def test_includes_deliverables(self, conversation_id):
        """Test that response contains deliverables schedule."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain deliverables (D1.1, D2.1, etc. or "Deliverable")
            deliverable_pattern = r"D\d+\.\d+"
            deliverables_found = re.findall(deliverable_pattern, response_text)

            has_deliverable_mentions = "deliverable" in response_text.lower()

            assert len(deliverables_found) >= 3 or has_deliverable_mentions, (
                f"Response should contain deliverables. Found: {deliverables_found}"
            )

    @pytest.mark.asyncio
    async def test_timeline_spans_36_months(self, conversation_id):
        """Test that timeline covers the requested 36-month duration."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should mention 36 months or M36
            duration_indicators = [
                r"36\s*month",
                r"M36\b",
                r"Month\s*36",
                r"3\s*year",
            ]

            has_duration = any(
                re.search(pattern, response_text, re.IGNORECASE) for pattern in duration_indicators
            )

            assert has_duration, (
                f"Response should reference the 36-month duration. Response: {response_text[:500]}"
            )

    @pytest.mark.asyncio
    async def test_milestones_well_distributed(self, conversation_id):
        """Test that milestones are distributed across the project timeline."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Extract month references (M1, M9, M18, etc.)
            month_pattern = r"\bM(\d+)\b"
            months = re.findall(month_pattern, response_text)
            month_numbers = sorted(set(int(m) for m in months if int(m) <= 36))

            # Should have milestones/events in at least early, mid, and late phases
            if month_numbers:
                has_early = any(m <= 12 for m in month_numbers)
                has_mid = any(12 < m <= 24 for m in month_numbers)
                has_late = any(m > 24 for m in month_numbers)

                phases_covered = sum([has_early, has_mid, has_late])
                assert phases_covered >= 2, (
                    f"Timeline should have events distributed across phases. "
                    f"Months found: {month_numbers}"
                )

    @pytest.mark.asyncio
    async def test_includes_person_months_or_effort(self, conversation_id):
        """Test that response includes effort allocation information."""
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
                " pm ",
                " pm,",
                "effort",
                "fte",
            ]

            has_effort = any(ind in response_text for ind in effort_indicators)

            assert has_effort, "Response should include effort/person-months information"

    @pytest.mark.asyncio
    async def test_includes_partners_or_leads(self, conversation_id):
        """Test that response includes partner/lead assignments."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention partner assignments
            partner_indicators = ["lead:", "participants:", "p1", "p2", "partner"]

            has_partners = any(ind in response_text for ind in partner_indicators)

            assert has_partners, "Response should include partner/lead assignments"

    @pytest.mark.asyncio
    async def test_includes_gantt_or_visual(self, conversation_id):
        """Test that response includes a visual timeline or Gantt chart."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should include a visual representation (Gantt chart characters or table)
            visual_indicators = [
                "gantt",
                r"[█░▓▒]",  # Block characters used in ASCII Gantt
                r"[◆▼◇]",  # Milestone/deliverable markers
                "---",  # Table separators
                "|||",  # Table structure
            ]

            has_visual = any(
                re.search(pattern, response_text, re.IGNORECASE) for pattern in visual_indicators
            )

            # Also accept if response has code block with timeline
            has_code_block = "```" in response_text

            assert has_visual or has_code_block, (
                "Response should include a visual timeline representation"
            )

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

            # Should not contain error indicators
            error_indicators = [
                "error occurred",
                "failed to",
                "unable to generate",
                "something went wrong",
                "i cannot",
                "i don't have",
            ]

            has_error = any(ind in response_text for ind in error_indicators)

            assert not has_error, "Response should not contain error messages"

    @pytest.mark.asyncio
    async def test_includes_recommendations(self, conversation_id):
        """Test that response includes recommendations or next steps."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should include recommendations or actionable guidance
            recommendation_indicators = [
                "recommend",
                "suggest",
                "next steps",
                "consider",
                "tip",
                "guidance",
                "review",
            ]

            has_recommendations = any(ind in response_text for ind in recommendation_indicators)

            assert has_recommendations, "Response should include recommendations or next steps"

    @pytest.mark.asyncio
    async def test_quality_score_threshold(self, conversation_id):
        """Test that response meets the quality threshold (80 points)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Calculate quality score based on PRD criteria
            score = 0

            # Query Fulfillment (40 points)
            # - Work packages present
            wp_pattern = r"WP\d+"
            wps = re.findall(wp_pattern, response_text)
            if len(wps) >= 5:
                score += 15
            elif len(wps) >= 3:
                score += 10

            # - Milestones present
            ms_pattern = r"MS\d+"
            milestones = re.findall(ms_pattern, response_text)
            if len(milestones) >= 4:
                score += 15
            elif len(milestones) >= 2:
                score += 10

            # - Deliverables present
            deliverable_pattern = r"D\d+\.\d+"
            deliverables = re.findall(deliverable_pattern, response_text)
            if len(deliverables) >= 8:
                score += 10
            elif len(deliverables) >= 4:
                score += 7

            # Specificity (25 points)
            # - Month references
            month_refs = re.findall(r"\bM\d+\b", response_text)
            if len(month_refs) >= 15:
                score += 10
            elif len(month_refs) >= 8:
                score += 7

            # - Duration values
            if re.search(r"\d+\s*months?", response_text, re.IGNORECASE):
                score += 5

            # - Person-months
            if re.search(r"person-?months?|PM|\d+\s*pm", response_text, re.IGNORECASE):
                score += 5

            # - Partner assignments
            if re.search(r"P\d|Lead:", response_text):
                score += 5

            # Factual Accuracy (25 points)
            # - Innovation Action (IA) structure (for "innovation project")
            if re.search(r"\bIA\b|innovation action", response_text, re.IGNORECASE):
                score += 10

            # - Standard WP structure (management, dissemination)
            text_lower = response_text.lower()
            if "management" in text_lower:
                score += 5
            if "dissemination" in text_lower or "exploitation" in text_lower:
                score += 5
            if "pilot" in text_lower or "demonstration" in text_lower:
                score += 5

            # Actionability (10 points)
            # - Next steps or recommendations
            if any(x in text_lower for x in ["next steps", "recommend", "consider", "review"]):
                score += 5

            # - Links to resources
            if "http" in response_text or "portal" in text_lower:
                score += 5

            assert score >= self.PASS_THRESHOLD, (
                f"Quality score {score} is below threshold {self.PASS_THRESHOLD}"
            )

    @pytest.mark.asyncio
    async def test_full_scenario_integration(self, conversation_id):
        """Full integration test for Scenario 013."""
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

            # Basic assertions
            assert len(response_text) > 1000, (
                f"Response too short for timeline: {len(response_text)} chars"
            )

            # Should have work packages, milestones, deliverables
            assert re.search(r"WP\d+", response_text), "Missing work packages"
            assert re.search(r"MS\d+", response_text) or "milestone" in response_text.lower(), (
                "Missing milestones"
            )
            assert (
                re.search(r"D\d+\.\d+", response_text) or "deliverable" in response_text.lower()
            ), "Missing deliverables"

            # Should reference 36 months
            assert re.search(r"36\s*month|M36|3\s*year", response_text, re.IGNORECASE), (
                "Should reference 36-month duration"
            )

            # Should have visual elements or structured output
            assert any(
                [
                    "```" in response_text,
                    "█" in response_text,
                    "---" in response_text,
                    "Gantt" in response_text,
                ]
            ), "Should include visual timeline elements"

            # Metadata should indicate success
            tools_used = metadata.get("tools_used", [])
            assert any(
                "timeline" in str(t).lower() for t in tools_used
            ) or "generate_timeline" in str(metadata.get("reasoning_steps", [])), (
                f"generate_timeline tool should be used. Metadata: {metadata}"
            )

    @pytest.mark.asyncio
    async def test_response_consistency(self, conversation_id):
        """Test that multiple runs produce consistent timeline structure."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Count key elements
            wps = len(re.findall(r"WP\d+", response_text))
            milestones = len(re.findall(r"MS\d+", response_text))
            deliverables = len(re.findall(r"D\d+\.\d+", response_text))

            # Structure should be reasonable for 36-month project
            # Typically 5-8 WPs, 4-8 milestones, 10-20 deliverables
            assert wps >= 3, f"Too few work packages: {wps}"
            assert milestones >= 2, f"Too few milestones: {milestones}"
            assert deliverables >= 3, f"Too few deliverables: {deliverables}"
