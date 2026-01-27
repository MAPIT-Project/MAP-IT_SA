"""
Test Scenario 006: Organization Project Search

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 006
Query: "What projects has Fraunhofer participated in?"
Expected: List of projects with Fraunhofer as partner/coordinator
Verify: Organization name matching works, role info correct
Pass threshold: 80

This test verifies that the system properly searches for organization projects:
- Uses find_organization_projects tool
- Returns projects where the organization participated
- Shows coordinator vs participant role
- Includes project titles, budgets, CORDIS links
- Supports partial organization name matching
"""

import re

import httpx
import pytest


class TestScenario006OrganizationProjectSearch:
    """Test suite for Scenario 006: Organization Project Search."""

    BASE_URL = "http://localhost:8000"
    QUERY = "What projects has Fraunhofer participated in?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(600000, 699999)

    @pytest.mark.asyncio
    async def test_returns_organization_projects(self, conversation_id):
        """Test that the query returns projects for the organization."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200, f"API returned {response.status_code}"
            result = response.json()

            response_text = result.get("response", "")

            # Should find projects for Fraunhofer
            assert "project" in response_text.lower(), "Response should mention projects"
            assert "fraunhofer" in response_text.lower(), "Response should mention Fraunhofer"

    @pytest.mark.asyncio
    async def test_uses_find_organization_projects_tool(self, conversation_id):
        """Test that find_organization_projects tool is used."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            metadata = result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Should use find_organization_projects tool
            org_tool_used = any("organization_projects" in str(t).lower() for t in tools_used)
            assert org_tool_used, f"Should use find_organization_projects tool, got: {tools_used}"

    @pytest.mark.asyncio
    async def test_includes_project_titles(self, conversation_id):
        """Test that response includes project titles."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should have project titles (marked with bold ** or with acronyms)
            has_projects = (
                "**" in response_text
                or re.search(r"\*\*[A-Z]+\*\*", response_text)  # Acronym pattern
                or "- " in response_text  # List format
            )
            assert has_projects, "Response should include project titles"

    @pytest.mark.asyncio
    async def test_includes_cordis_links(self, conversation_id):
        """Test that response includes CORDIS links."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should link to CORDIS
            assert "cordis.europa.eu" in response_text.lower(), (
                "Response should include CORDIS links"
            )

    @pytest.mark.asyncio
    async def test_includes_budget_information(self, conversation_id):
        """Test that response includes budget information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should have budget information (EUR, €, or M for million)
            budget_indicators = ["€", "EUR", "budget", "M)", "million"]
            has_budget = any(ind in response_text for ind in budget_indicators)
            assert has_budget, "Response should include budget information"

    @pytest.mark.asyncio
    async def test_shows_role_information(self, conversation_id):
        """Test that response shows coordinator vs participant role."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should show role info (coordinator, participant, or sections for each)
            role_indicators = [
                "coordinator",
                "participant",
                "coordinated",
                "as coordinator",
                "as participant",
            ]
            has_role = any(ind.lower() in response_text.lower() for ind in role_indicators)
            assert has_role, "Response should include role information"

    @pytest.mark.asyncio
    async def test_returns_multiple_projects(self, conversation_id):
        """Test that response returns multiple projects."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            metadata = result.get("metadata", {})
            reasoning_steps = metadata.get("reasoning_steps", [])

            # Should have found multiple projects
            for step in reasoning_steps:
                observation = step.get("observation", "")
                if "project" in observation.lower():
                    # Extract count from observation like "Found 20 project(s)"
                    match = re.search(r"Found (\d+) project", observation)
                    if match:
                        count = int(match.group(1))
                        assert count >= 3, f"Should find at least 3 projects, found {count}"
                        return

            # Alternative: count CORDIS links in response
            response_text = result.get("response", "")
            cordis_links = re.findall(r"cordis\.europa\.eu/project/id/\d+", response_text)
            assert len(cordis_links) >= 3, (
                f"Should find at least 3 projects, found {len(cordis_links)}"
            )

    @pytest.mark.asyncio
    async def test_includes_funding_scheme(self, conversation_id):
        """Test that response includes funding scheme information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should have funding scheme info (RIA, IA, MSCA, ERC, etc.)
            funding_schemes = [
                "HORIZON-RIA",
                "HORIZON-IA",
                "HORIZON-ERC",
                "HORIZON-TMA-MSCA",
                "HORIZON-EIC",
                "RIA",
                "IA",
                "MSCA",
                "ERC",
            ]
            has_scheme = any(scheme in response_text for scheme in funding_schemes)
            assert has_scheme, "Response should include funding scheme information"

    @pytest.mark.asyncio
    async def test_quality_score_passes_threshold(self, conversation_id):
        """Test that quality analysis reports passing score."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            metadata = result.get("metadata", {})
            quality_analysis = metadata.get("quality_analysis", {})

            # Quality score should be available
            assert "score" in quality_analysis, "Response should include quality score"

            # Quality score should meet threshold
            score = quality_analysis.get("score", 0)
            assert score >= self.PASS_THRESHOLD, (
                f"Quality score {score} should be >= {self.PASS_THRESHOLD}"
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

            result = response.json()

            # Should not have error in response
            assert "error" not in result, f"Response should not have error: {result.get('error')}"

            response_text = result.get("response", "")
            # Should not have generic error messages
            assert not any(
                phrase.lower() in response_text.lower()
                for phrase in ["error occurred", "I apologize", "something went wrong"]
            ), "Response should not contain error messages"

    @pytest.mark.asyncio
    async def test_includes_summary_statistics(self, conversation_id):
        """Test that response includes summary statistics."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should have summary statistics (total projects, total budget, etc.)
            summary_indicators = [
                "total",
                "summary",
                "projects found",
                "total budget",
                "funding types",
            ]
            has_summary = any(ind.lower() in response_text.lower() for ind in summary_indicators)
            assert has_summary, "Response should include summary statistics"


class TestOrganizationNameMatching:
    """Test organization name matching capabilities."""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(610000, 619999)

    @pytest.mark.asyncio
    async def test_partial_name_matching(self, conversation_id):
        """Test that partial organization names work (e.g., 'Fraunhofer' vs full name)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "Show me projects by Fraunhofer", "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should find projects
            assert "project" in response_text.lower(), "Should find projects for partial name"
            assert "no projects found" not in response_text.lower(), (
                "Should not fail to find projects"
            )

    @pytest.mark.asyncio
    async def test_abbreviation_matching(self, conversation_id):
        """Test that abbreviations work (e.g., CNRS, TUM)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "What projects has CNRS participated in?", "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should find projects for CNRS
            assert "project" in response_text.lower(), "Should find projects for abbreviation"

    @pytest.mark.asyncio
    async def test_max_planck_projects(self, conversation_id):
        """Test that Max Planck Institute projects are found."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "Find projects by Max Planck", "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should find projects
            assert "project" in response_text.lower(), "Should find Max Planck projects"
            assert "max planck" in response_text.lower(), "Response should mention Max Planck"
