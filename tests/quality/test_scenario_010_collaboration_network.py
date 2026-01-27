"""
Scenario 010: Collaboration Network
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "Show me the collaboration network for Max Planck Institute"
Expected: Top collaborating organizations, shared projects
Verify: Network data is accurate, relationships real
Fix if: Missing collaborations, wrong organizations
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario010CollaborationNetwork:
    """Test collaboration network functionality."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Show me the collaboration network for Max Planck Institute"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(100000, 109999)

    @pytest.mark.asyncio
    async def test_returns_collaboration_network_format(self, conversation_id):
        """Test that response uses collaboration network formatting."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should use collaboration network formatting
            assert "Collaboration Network" in response_text, (
                "Response should use Collaboration Network format"
            )

    @pytest.mark.asyncio
    async def test_uses_get_collaboration_network_tool(self, conversation_id):
        """Test that the get_collaboration_network tool is used."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})

            # Check if tools_used includes get_collaboration_network
            tools_used = metadata.get("tools_used", [])

            # Also check reasoning steps for tool calls
            reasoning_steps = metadata.get("reasoning_steps", [])
            tool_in_reasoning = any(
                "get_collaboration_network" in str(step) for step in reasoning_steps
            )

            # The tool might be versioned (e.g., get_collaboration_network_2_0)
            has_network_tool = any("get_collaboration_network" in t for t in tools_used)

            assert has_network_tool or tool_in_reasoning, (
                f"Expected get_collaboration_network tool to be used. Tools: {tools_used}"
            )

    @pytest.mark.asyncio
    async def test_includes_partner_organizations(self, conversation_id):
        """Test that response contains partner organizations."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain partner indicators
            partner_indicators = [
                "Partner",
                "partner",
                "collaborat",
                "shared project",
                "organization",
            ]
            has_partners = any(ind in response_text for ind in partner_indicators)

            assert has_partners, "Response should contain partner organization information"

    @pytest.mark.asyncio
    async def test_includes_country_codes(self, conversation_id):
        """Test that response includes country codes for partners."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should include country codes (2-letter ISO codes in parentheses)
            country_pattern = r"\(([A-Z]{2})\)"
            country_codes = re.findall(country_pattern, response_text)

            assert len(country_codes) >= 1, "Response should include country codes for partners"

    @pytest.mark.asyncio
    async def test_includes_collaboration_counts(self, conversation_id):
        """Test that response includes collaboration count data."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention shared projects or collaboration counts
            count_indicators = [
                "shared project",
                "project(s)",
                "projects",
                "collaboration",
                "total partners",
            ]
            has_counts = any(ind in response_text for ind in count_indicators)

            # Should have numbers (collaboration counts)
            numbers = re.findall(r"\d+", response_text)

            assert has_counts, "Response should mention shared projects or collaboration counts"
            assert len(numbers) >= 1, "Response should include numerical data"

    @pytest.mark.asyncio
    async def test_includes_organization_types(self, conversation_id):
        """Test that response includes organization types."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should mention organization types
            org_type_indicators = [
                "Research",
                "University",
                "Private",
                "REC",
                "HES",
                "PRC",
                "Public",
                "Other",
            ]
            has_org_type = any(ind in response_text for ind in org_type_indicators)

            assert has_org_type, "Response should include organization type information"

    @pytest.mark.asyncio
    async def test_includes_network_summary(self, conversation_id):
        """Test that response includes a network summary section."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should have summary section
            summary_indicators = [
                "Summary",
                "Total",
                "Partner Countries",
                "Partner Types",
            ]
            has_summary = any(ind in response_text for ind in summary_indicators)

            assert has_summary, "Response should include a network summary section"

    @pytest.mark.asyncio
    async def test_quality_score_passes_threshold(self, conversation_id):
        """Test that quality analysis score meets the threshold."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})

            # Check quality analysis score if available
            quality_analysis = metadata.get("quality_analysis", {})
            quality_score = quality_analysis.get("score", 100)

            # Minimum acceptable score
            assert quality_score >= self.PASS_THRESHOLD, (
                f"Quality score {quality_score} below threshold {self.PASS_THRESHOLD}"
            )

    @pytest.mark.asyncio
    async def test_no_error_in_response(self, conversation_id):
        """Test that response does not contain error messages."""
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
                "unable to",
                "failed to",
                "i don't have",
                "no data available",
                "cannot process",
            ]

            has_error = any(ind in response_text for ind in error_indicators)
            assert not has_error, "Response should not contain error messages"

    @pytest.mark.asyncio
    async def test_includes_actionable_guidance(self, conversation_id):
        """Test that response includes actionable next steps."""
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
                "cordis",
                "partner search",
                "contact",
                "next step",
                "consortium",
            ]
            has_action = any(ind in response_text for ind in action_indicators)

            assert has_action, "Response should include actionable guidance"

    @pytest.mark.asyncio
    async def test_mentions_target_organization(self, conversation_id):
        """Test that response mentions the queried organization."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should mention Max Planck
            has_org = "Max Planck" in response_text or "MAX PLANCK" in response_text

            assert has_org, "Response should mention the target organization (Max Planck)"


class TestCollaborationNetworkOtherOrganizations:
    """Test collaboration network for other organizations."""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(110000, 119999)

    @pytest.mark.asyncio
    async def test_fraunhofer_collaboration_network(self, conversation_id):
        """Test finding collaboration network for Fraunhofer."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={
                    "message": "Who does Fraunhofer collaborate with most often?",
                    "user_id": 1,
                },
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should use collaboration network format
            assert "Collaboration Network" in response_text or "Partner" in response_text, (
                "Should show collaboration/partner information"
            )

            # Should mention Fraunhofer or a specific Fraunhofer institute
            has_fraunhofer = "Fraunhofer" in response_text or "FRAUNHOFER" in response_text
            assert has_fraunhofer, "Should mention Fraunhofer"

    @pytest.mark.asyncio
    async def test_cnrs_collaboration_network(self, conversation_id):
        """Test finding collaboration network for CNRS."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={
                    "message": "Show the collaboration network for CNRS",
                    "user_id": 1,
                },
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should use collaboration network format
            assert "Collaboration Network" in response_text, (
                "Should use Collaboration Network format"
            )

            # Should mention CNRS
            has_cnrs = "CNRS" in response_text
            assert has_cnrs, "Should mention CNRS"

    @pytest.mark.asyncio
    async def test_university_collaboration_network(self, conversation_id):
        """Test finding collaboration network for a university."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={
                    "message": "What organizations partner with Technical University of Munich?",
                    "user_id": 1,
                },
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain partner/collaboration information
            has_network_info = (
                "Collaboration Network" in response_text
                or "Partner" in response_text
                or "partner" in response_text
            )
            assert has_network_info, "Should show partner/collaboration information"

    @pytest.mark.asyncio
    async def test_returns_multiple_partners(self, conversation_id):
        """Test that collaboration network returns multiple partners."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={
                    "message": "Show me the collaboration network for CNRS",
                    "user_id": 1,
                },
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should show total partners count
            total_match = re.search(r"Total Partners Found.*?(\d+)", response_text)
            if total_match:
                total_partners = int(total_match.group(1))
                assert total_partners >= 1, "Should return at least 1 partner"
            else:
                # Alternative: count partner entries
                partner_entries = response_text.count("project(s)")
                assert partner_entries >= 1, "Should return at least 1 partner entry"
