"""
Scenario 009: Find Partners by Expertise
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "Find experienced partners for a hydrogen fuel cell project"
Expected: Organizations with relevant project history
Verify: Partners have actual hydrogen/fuel cell experience
Fix if: Irrelevant partners, missing experience data
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario009FindPartnersByExpertise:
    """Test partner discovery by expertise functionality."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Find experienced partners for a hydrogen fuel cell project"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(900000, 909999)

    @pytest.mark.asyncio
    async def test_returns_partner_organizations(self, conversation_id):
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

            # Should contain organization names (look for common research organization indicators)
            org_indicators = [
                "fraunhofer",
                "cnrs",
                "cea",
                "dlr",
                "vtt",
                "sintef",
                "rise",
                "university",
                "institut",
                "center",
                "centre",
            ]
            has_orgs = any(ind in response_text.lower() for ind in org_indicators)

            assert has_orgs, "Response should contain organization names"

    @pytest.mark.asyncio
    async def test_uses_find_experienced_partners_tool(self, conversation_id):
        """Test that the find_experienced_partners tool is used."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})

            # Check if tools_used includes find_experienced_partners
            tools_used = metadata.get("tools_used", [])

            # Also check reasoning steps for tool calls
            reasoning_steps = metadata.get("reasoning_steps", [])
            tool_in_reasoning = any(
                "find_experienced_partners" in str(step) for step in reasoning_steps
            )

            # The tool might be versioned (e.g., find_experienced_partners_1_0)
            has_partner_tool = any("find_experienced_partners" in t for t in tools_used)

            assert (
                has_partner_tool or tool_in_reasoning
            ), f"Expected find_experienced_partners tool to be used. Tools: {tools_used}"

    @pytest.mark.asyncio
    async def test_includes_project_counts(self, conversation_id):
        """Test that response includes project count data for partners."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention projects
            project_indicators = ["projects", "project", "participated", "coordinated"]
            has_projects = any(ind in response_text for ind in project_indicators)

            # Should have numbers (project counts)
            numbers = re.findall(r"\d+", response_text)

            assert has_projects, "Response should mention projects"
            assert len(numbers) >= 3, "Response should include numerical data for multiple partners"

    @pytest.mark.asyncio
    async def test_includes_funding_amounts(self, conversation_id):
        """Test that response includes funding amount data."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should mention funding amounts
            funding_indicators = [
                "EUR",
                "€",
                "funding",
                "million",
                "contribution",
            ]
            has_funding = any(ind.lower() in response_text.lower() for ind in funding_indicators)

            assert has_funding, "Response should include funding information"

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

            # Also check for country names
            country_names = ["germany", "france", "finland", "sweden", "netherlands"]
            has_country_names = any(name in response_text.lower() for name in country_names)

            assert (
                len(country_codes) >= 3 or has_country_names
            ), "Response should include country codes or names for partners"

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
                "REC",
                "HES",
                "PRC",
                "research center",
                "research centre",
                "higher education",
                "university",
                "company",
                "industry",
                "private company",
            ]
            has_org_type = any(ind.lower() in response_text.lower() for ind in org_type_indicators)

            assert has_org_type, "Response should include organization type information"

    @pytest.mark.asyncio
    async def test_includes_example_projects(self, conversation_id):
        """Test that response includes example project names."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should include project acronyms (all caps words that look like project names)
            # Project acronyms are typically 3-10 uppercase letters/numbers
            project_pattern = r"\b[A-Z][A-Z0-9]{2,9}\b"
            potential_projects = re.findall(project_pattern, response_text)

            # Filter out common non-project words
            exclude_words = {"EUR", "REC", "HES", "PRC", "PUB", "OTH", "THE", "AND", "FOR"}
            project_acronyms = [p for p in potential_projects if p not in exclude_words]

            # Also check for "example projects" or "coordinator" indicators
            has_project_context = any(
                ind in response_text.lower()
                for ind in ["example", "coordinator", "participant", "project"]
            )

            assert (
                len(project_acronyms) >= 3 or has_project_context
            ), "Response should include example project names"

    @pytest.mark.asyncio
    async def test_partners_relevant_to_hydrogen(self, conversation_id):
        """Test that returned partners are relevant to hydrogen/fuel cells."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # The query topic should be referenced
            topic_indicators = ["hydrogen", "fuel cell", "energy", "clean energy", "fuel"]
            has_topic = any(ind in response_text for ind in topic_indicators)

            assert has_topic, "Response should reference the hydrogen/fuel cell topic"

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
            assert (
                quality_score >= self.PASS_THRESHOLD
            ), f"Quality score {quality_score} below threshold {self.PASS_THRESHOLD}"

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
                "could not",
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
                "portal",
                "contact",
                "verify",
                "search",
                "partner search",
                "eu funding",
                "next step",
            ]
            has_action = any(ind in response_text for ind in action_indicators)

            assert has_action, "Response should include actionable guidance"

    @pytest.mark.asyncio
    async def test_returns_multiple_partners(self, conversation_id):
        """Test that response returns multiple partner options."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Count partners using various format patterns
            # Pattern 1: Numbered list items like "1.", "2.", etc.
            numbered_items = len(re.findall(r"\n\d+\.", response_text))
            # Pattern 2: Markdown headers with numbers like "### 1."
            header_items = len(re.findall(r"###\s+\d+\.", response_text))
            # Pattern 3: Bold numbers like "**1."
            star_items = len(re.findall(r"\*\*\d+\.", response_text))
            # Pattern 4: Table rows with rank numbers like "| 1 |" or "| 2 |"
            table_rows = len(re.findall(r"\|\s*\d+\s*\|", response_text))
            # Pattern 5: Organization names in bold (typically used in lists)
            bold_orgs = len(re.findall(r"\*\*[A-Z][A-Z\s]+\*\*", response_text))

            total_items = max(numbered_items, header_items, star_items, table_rows, bold_orgs)

            assert (
                total_items >= 5
            ), f"Response should list at least 5 partners, found {total_items}"


class TestFindPartnersOtherDomains:
    """Test partner discovery for other research domains."""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(910000, 919999)

    @pytest.mark.asyncio
    async def test_ai_machine_learning_partners(self, conversation_id):
        """Test finding partners for AI/ML projects."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={
                    "message": "Find experienced partners for an artificial intelligence project",
                    "user_id": 1,
                },
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should find AI-related partners
            assert "projects" in response_text, "Should mention project experience"
            has_orgs = any(
                ind in response_text
                for ind in ["fraunhofer", "cnrs", "university", "institut", "research"]
            )
            assert has_orgs, "Should list organizations with AI experience"

    @pytest.mark.asyncio
    async def test_health_biomedical_partners(self, conversation_id):
        """Test finding partners for health/biomedical projects."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={
                    "message": "Find partners experienced in cancer research for a new project",
                    "user_id": 1,
                },
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should find health-related partners
            has_health_orgs = any(
                ind in response_text
                for ind in ["hospital", "university", "medical", "research", "institut"]
            )
            assert has_health_orgs, "Should list organizations with health/cancer experience"

    @pytest.mark.asyncio
    async def test_climate_sustainability_partners(self, conversation_id):
        """Test finding partners for climate/sustainability projects."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={
                    "message": "Find experienced partners for a climate change adaptation project",
                    "user_id": 1,
                },
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should find climate-related partners
            assert "projects" in response_text, "Should mention project experience"
            # Should have some numbers indicating project counts
            has_numbers = bool(re.search(r"\d+", response_text))
            assert has_numbers, "Should include numerical data about partner experience"
