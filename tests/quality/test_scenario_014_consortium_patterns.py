"""
Scenario 014: Consortium Patterns
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "What consortium composition works best for health research projects?"
Expected: Typical size, org type mix, country distribution
Verify: Patterns based on real successful projects
Fix if: Generic advice not backed by data
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario014ConsortiumPatterns:
    """Test consortium patterns functionality for Horizon Europe proposals."""

    BASE_URL = "http://localhost:8000"
    QUERY = "What consortium composition works best for health research projects?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(140000, 149999)

    @pytest.mark.asyncio
    async def test_uses_consortium_patterns_tool(self, conversation_id):
        """Test that the get_consortium_patterns tool is used."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})

            # Check if tools_used includes consortium_patterns
            tools_used = metadata.get("tools_used", [])

            # Also check reasoning steps for tool calls
            reasoning_steps = metadata.get("reasoning_steps", [])
            tool_in_reasoning = any("consortium_patterns" in str(step) for step in reasoning_steps)

            # The tool might be versioned (e.g., get_consortium_patterns_1_0)
            has_consortium_tool = any("consortium_patterns" in t for t in tools_used)

            assert (
                has_consortium_tool or tool_in_reasoning
            ), f"Expected consortium_patterns tool to be used. Tools: {tools_used}"

    @pytest.mark.asyncio
    async def test_includes_consortium_size(self, conversation_id):
        """Test that response contains consortium size information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should contain consortium size (partners, avg, average)
            size_indicators = [
                "partner",
                "consortium size",
                "organizations",
                "members",
                "average",
            ]

            has_size = any(ind in response_text for ind in size_indicators)

            assert has_size, "Response should contain consortium size information"

    @pytest.mark.asyncio
    async def test_includes_numeric_values(self, conversation_id):
        """Test that response contains specific numeric values for consortium data."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain numeric values (e.g., "16 partners", "8 countries")
            numbers_found = re.findall(r"\d+\.?\d*", response_text)

            assert (
                len(numbers_found) >= 5
            ), f"Response should contain specific numeric values. Found: {len(numbers_found)}"

    @pytest.mark.asyncio
    async def test_includes_org_type_breakdown(self, conversation_id):
        """Test that response contains organization type breakdown."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should contain organization types
            org_types = [
                "university",
                "universities",
                "research",
                "sme",
                "industry",
                "hospital",
                "public",
                "hes",
                "rec",
                "prc",
                "pub",
            ]

            org_types_found = sum(1 for t in org_types if t in response_text)

            assert org_types_found >= 2, (
                f"Response should contain organization type breakdown. "
                f"Types found: {org_types_found}"
            )

    @pytest.mark.asyncio
    async def test_includes_country_distribution(self, conversation_id):
        """Test that response contains country distribution information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain country-related information
            country_indicators = [
                "countr",  # country, countries
                r"\b(FR|DE|NL|BE|ES|IT|SE|AT|DK|FI)\b",  # Country codes
                "member state",
                "associated",
                "geographic",
            ]

            has_countries = any(
                re.search(pattern, response_text, re.IGNORECASE) for pattern in country_indicators
            )

            assert has_countries, "Response should contain country distribution information"

    @pytest.mark.asyncio
    async def test_based_on_real_projects(self, conversation_id):
        """Test that patterns are based on real project data (not generic advice)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should reference actual data or projects
            data_indicators = [
                r"\d+\s*projects?",  # e.g., "412 projects"
                r"analysis|analyzed",
                r"based on",
                r"data shows|data indicates",
                r"funded projects",
                r"cluster\s*\d|cluster-\d",  # Cluster references
                r"\(N\s*=\s*\d+\)",  # Statistical notation
            ]

            has_data_basis = any(
                re.search(pattern, response_text, re.IGNORECASE) for pattern in data_indicators
            )

            assert has_data_basis, (
                "Response should be based on real project data, not generic advice. "
                "Should reference analyzed projects or data."
            )

    @pytest.mark.asyncio
    async def test_includes_coordinator_info(self, conversation_id):
        """Test that response includes information about coordinators."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should contain coordinator information
            coordinator_indicators = [
                "coordinator",
                "coordinating",
                "lead",
                "top coordinators",
            ]

            has_coordinator = any(ind in response_text for ind in coordinator_indicators)

            assert has_coordinator, "Response should include coordinator information"

    @pytest.mark.asyncio
    async def test_includes_health_specific_guidance(self, conversation_id):
        """Test that response is tailored to health research projects."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should be specific to health/Cluster 1
            health_indicators = [
                "health",
                "cluster 1",
                "clinical",
                "medical",
                "patient",
                "hospital",
                "pharmaceutical",
                "biomedical",
            ]

            health_refs_found = sum(1 for h in health_indicators if h in response_text)

            assert health_refs_found >= 2, (
                f"Response should be tailored to health research. "
                f"Health references found: {health_refs_found}"
            )

    @pytest.mark.asyncio
    async def test_includes_percentage_breakdown(self, conversation_id):
        """Test that response includes percentage breakdown of consortium composition."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain percentages (e.g., "30%", "25 - 35%")
            percentage_pattern = r"\d+\s*%|\d+\s*-\s*\d+\s*%"
            percentages_found = re.findall(percentage_pattern, response_text)

            assert (
                len(percentages_found) >= 2
            ), f"Response should include percentage breakdown. Found: {percentages_found}"

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
                "unable to",
                "something went wrong",
                "i cannot",
                "i don't have",
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
                "next steps",
                "recommend",
                "suggest",
                "ensure",
                "find",
                "verify",
                "register",
                "identify",
            ]

            action_found = sum(1 for a in action_indicators if a in response_text)

            assert (
                action_found >= 2
            ), f"Response should include actionable guidance. Action items found: {action_found}"

    @pytest.mark.asyncio
    async def test_includes_real_organization_names(self, conversation_id):
        """Test that response includes real organization names as examples."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should include real organization names (common health research coordinators)
            org_patterns = [
                r"INSERM",
                r"KAROLINSKA",
                r"CHARITE",
                r"ERASMUS",
                r"MAX PLANCK",
                r"CNRS",
                r"FRAUNHOFER",
                r"LEUVEN",
                r"UNIVERSITY",
                r"INSTITUT",
            ]

            orgs_found = sum(
                1 for pattern in org_patterns if re.search(pattern, response_text, re.IGNORECASE)
            )

            assert (
                orgs_found >= 2
            ), f"Response should include real organization names. Found: {orgs_found}"

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
            text_lower = response_text.lower()

            # Calculate quality score based on PRD criteria
            score = 0

            # Query Fulfillment (40 points)
            # - Consortium size present
            if re.search(r"\d+\s*partners?", response_text, re.IGNORECASE):
                score += 15
            elif "size" in text_lower or "partners" in text_lower:
                score += 8

            # - Organization type mix present
            org_types = ["university", "research", "sme", "hospital", "public"]
            if sum(1 for t in org_types if t in text_lower) >= 3:
                score += 15
            elif sum(1 for t in org_types if t in text_lower) >= 2:
                score += 10

            # - Country distribution present
            if re.search(
                r"countr|member state|\b(FR|DE|NL|BE|ES|IT)\b",
                response_text,
                re.IGNORECASE,
            ):
                score += 10

            # Specificity (25 points)
            # - Numeric values (specific numbers, percentages)
            percentages = re.findall(r"\d+\s*%", response_text)
            if len(percentages) >= 4:
                score += 10
            elif len(percentages) >= 2:
                score += 6

            # - Project count reference
            if re.search(r"\d+\s*projects?", response_text, re.IGNORECASE):
                score += 8

            # - Real organization names
            org_patterns = ["inserm", "karolinska", "charite", "erasmus", "leuven"]
            if sum(1 for o in org_patterns if o in text_lower) >= 2:
                score += 7
            elif sum(1 for o in org_patterns if o in text_lower) >= 1:
                score += 4

            # Factual Accuracy (25 points)
            # - Health/Cluster 1 specific
            health_terms = ["health", "cluster 1", "clinical", "patient", "medical"]
            if sum(1 for h in health_terms if h in text_lower) >= 3:
                score += 15
            elif sum(1 for h in health_terms if h in text_lower) >= 2:
                score += 10

            # - Realistic consortium size (10-25 for health projects)
            size_match = re.search(r"(\d+\.?\d*)\s*partners", response_text, re.IGNORECASE)
            if size_match:
                size = float(size_match.group(1))
                if 10 <= size <= 25:
                    score += 10
                elif 8 <= size <= 30:
                    score += 5

            # Actionability (10 points)
            # - Next steps or recommendations
            action_terms = ["next steps", "recommend", "ensure", "verify", "find"]
            if sum(1 for a in action_terms if a in text_lower) >= 2:
                score += 5

            # - Links or portal references
            if "http" in response_text or "portal" in text_lower:
                score += 5

            assert (
                score >= self.PASS_THRESHOLD
            ), f"Quality score {score} is below threshold {self.PASS_THRESHOLD}"

    @pytest.mark.asyncio
    async def test_full_scenario_integration(self, conversation_id):
        """Full integration test for Scenario 014."""
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
            text_lower = response_text.lower()

            # Basic assertions
            assert (
                len(response_text) > 500
            ), f"Response too short for consortium patterns: {len(response_text)} chars"

            # Should have consortium size
            assert (
                "partner" in text_lower or "size" in text_lower
            ), "Missing consortium size information"

            # Should have organization types
            org_types = ["university", "research", "sme", "hospital", "public"]
            assert (
                sum(1 for t in org_types if t in text_lower) >= 2
            ), "Missing organization type breakdown"

            # Should reference project data
            assert re.search(
                r"\d+\s*projects?|analysis|cluster\s*1", response_text, re.IGNORECASE
            ), "Should be based on real project data"

            # Should have coordinator info
            assert (
                "coordinator" in text_lower or "lead" in text_lower
            ), "Missing coordinator information"

            # Metadata should indicate success
            tools_used = metadata.get("tools_used", [])
            assert any(
                "consortium_patterns" in str(t).lower() for t in tools_used
            ) or "consortium_patterns" in str(
                metadata.get("reasoning_steps", [])
            ), f"consortium_patterns tool should be used. Metadata: {metadata}"

    @pytest.mark.asyncio
    async def test_response_structure(self, conversation_id):
        """Test that response has a well-organized structure."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should have structured elements (headers, tables, lists)
            structure_indicators = [
                r"###?\s+",  # Markdown headers
                r"\|.*\|",  # Table rows
                r"^\s*[-*•]\s+",  # List items
                r"\d+\.\s+",  # Numbered lists
            ]

            structure_found = sum(
                1
                for pattern in structure_indicators
                if re.search(pattern, response_text, re.MULTILINE)
            )

            assert (
                structure_found >= 2
            ), f"Response should be well-structured. Structure elements: {structure_found}"
