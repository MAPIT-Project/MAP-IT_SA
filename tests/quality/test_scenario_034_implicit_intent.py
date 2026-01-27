"""
Scenario 034: Implicit Intent
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "I work at a university and we have an idea about clean energy"
Expected: Understands intent to find funding, offers relevant options
Verify: Correctly interprets as funding search
Fix if: Literal response, misses intent
Pass threshold: 80
"""

import random

import httpx
import pytest


class TestScenario034ImplicitIntent:
    """Test that implicit funding intent queries are correctly interpreted."""

    BASE_URL = "http://localhost:8000"
    PASS_THRESHOLD = 80

    # Various implicit intent queries that indicate interest in funding
    IMPLICIT_INTENT_QUERIES = [
        "I work at a university and we have an idea about clean energy",
        "We're an SME developing AI for healthcare",
        "Our research team is working on quantum computing applications",
        "I'm from a biotech startup focusing on cancer diagnostics",
        "We have expertise in sustainable agriculture",
        "My organization develops robotics for manufacturing",
    ]

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        return random.randint(340000, 349999)

    async def _send_query(self, client, conversation_id, query):
        """Send query and return response."""
        # Clear any existing context
        await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

        response = await client.post(
            f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
            json={"message": query, "user_id": 1},
        )
        return response

    def _understands_funding_intent(self, text):
        """Check if response understands the user wants funding information."""
        funding_indicators = [
            "funding",
            "call",
            "calls",
            "horizon europe",
            "horizon",
            "grant",
            "grants",
            "opportunity",
            "opportunities",
            "programme",
            "program",
            "apply",
            "application",
            "eligible",
            "eligibility",
            "eu funding",
            "european",
            "cluster",
            "ria",
            "ia",
            "eic",
            "msca",
            "budget",
        ]
        text_lower = text.lower()
        count = sum(1 for indicator in funding_indicators if indicator in text_lower)
        return count >= 2  # At least 2 funding-related terms

    def _provides_relevant_options(self, text):
        """Check if response provides relevant funding options."""
        options_indicators = [
            "cluster",
            "call",
            "calls",
            "horizon-",
            "horizon europe",
            "open call",
            "open funding",
            "relevant",
            "match",
            "align",
            "suitable",
            "recommend",
            "suggest",
            "option",
            "options",
            "opportunity",
            "opportunities",
        ]
        text_lower = text.lower()
        count = sum(1 for indicator in options_indicators if indicator in text_lower)
        return count >= 2  # At least 2 option indicators

    def _mentions_research_domain(self, text, domain_keywords):
        """Check if response acknowledges the user's research domain."""
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in domain_keywords)

    def _has_actionable_next_steps(self, text):
        """Check if response provides actionable next steps."""
        action_indicators = [
            "next step",
            "next steps",
            "recommend",
            "suggest",
            "check",
            "visit",
            "apply",
            "explore",
            "consider",
            "portal",
            "ec.europa",
            "eu portal",
            "funding-tenders",
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in action_indicators)

    def _is_not_literal_response(self, text, query):
        """Check that response isn't just a literal interpretation."""
        # Literal responses would just acknowledge what the user said
        # without offering funding guidance
        literal_indicators = [
            "that's great",
            "sounds interesting",
            "good idea",
            "nice project",
            "interesting work",
            "i understand you work at",
            "so you work at",
        ]
        text_lower = text.lower()
        literal_count = sum(1 for ind in literal_indicators if ind in text_lower)

        # Not literal if has funding content
        has_funding = self._understands_funding_intent(text)

        return has_funding or literal_count < 2

    @pytest.mark.asyncio
    async def test_primary_query_understands_funding_intent(self, conversation_id):
        """Test primary query is understood as funding intent."""
        query = "I work at a university and we have an idea about clean energy"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            understands_intent = self._understands_funding_intent(response_text)

            assert understands_intent, (
                f"Response should understand implicit funding intent. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_primary_query_provides_options(self, conversation_id):
        """Test that primary query provides relevant funding options."""
        query = "I work at a university and we have an idea about clean energy"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            provides_options = self._provides_relevant_options(response_text)

            assert provides_options, (
                f"Response should provide relevant funding options. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_primary_query_acknowledges_domain(self, conversation_id):
        """Test that primary query acknowledges the clean energy domain."""
        query = "I work at a university and we have an idea about clean energy"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Check for energy-related acknowledgment
            domain_keywords = ["energy", "clean", "cluster 5", "climate", "renewable"]
            acknowledges_domain = self._mentions_research_domain(response_text, domain_keywords)

            assert acknowledges_domain, (
                f"Response should acknowledge the clean energy domain. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_primary_query_not_literal(self, conversation_id):
        """Test that response isn't just a literal interpretation."""
        query = "I work at a university and we have an idea about clean energy"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            not_literal = self._is_not_literal_response(response_text, query)

            assert not_literal, (
                f"Response should not be a literal interpretation. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_primary_query_has_next_steps(self, conversation_id):
        """Test that response provides actionable next steps."""
        query = "I work at a university and we have an idea about clean energy"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            has_actions = self._has_actionable_next_steps(response_text)

            assert has_actions, (
                f"Response should provide actionable next steps. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_sme_healthcare_implicit_intent(self, conversation_id):
        """Test SME healthcare query is understood as funding intent."""
        query = "We're an SME developing AI for healthcare"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            understands_intent = self._understands_funding_intent(response_text)
            domain_keywords = ["health", "ai", "sme", "cluster 1", "cluster 4", "digital"]
            acknowledges_domain = self._mentions_research_domain(response_text, domain_keywords)

            assert understands_intent, (
                f"Response should understand implicit funding intent. "
                f"Response: {response_text[:500]}..."
            )
            assert acknowledges_domain, (
                f"Response should acknowledge the AI/healthcare domain. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_quantum_computing_implicit_intent(self, conversation_id):
        """Test quantum computing query is understood as funding intent."""
        query = "Our research team is working on quantum computing applications"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            understands_intent = self._understands_funding_intent(response_text)

            assert understands_intent, (
                f"Response should understand implicit funding intent. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_biotech_startup_implicit_intent(self, conversation_id):
        """Test biotech startup query is understood as funding intent."""
        query = "I'm from a biotech startup focusing on cancer diagnostics"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            understands_intent = self._understands_funding_intent(response_text)

            assert understands_intent, (
                f"Response should understand implicit funding intent. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_response_uses_search_tools(self, conversation_id):
        """Test that response uses appropriate search tools."""
        query = "I work at a university and we have an idea about clean energy"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Should use search tools to find relevant funding
            # Tool names may include iteration numbers like "search_funding_calls_1_0"
            search_tools = [
                "search_funding_calls",
                "search_all_programmes",
                "recommend_programmes",
                "search_documents",
            ]
            used_search_tool = any(
                any(tool_used.startswith(search_tool) for search_tool in search_tools)
                for tool_used in tools_used
            )

            assert used_search_tool, (
                f"Response should use search tools. " f"Tools used: {tools_used}"
            )

    @pytest.mark.asyncio
    async def test_response_not_empty(self, conversation_id):
        """Test that response is not empty or minimal."""
        query = "I work at a university and we have an idea about clean energy"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            assert (
                len(response_text) > 200
            ), f"Response should be substantial. Length: {len(response_text)}"

    @pytest.mark.asyncio
    async def test_mentions_horizon_europe(self, conversation_id):
        """Test that response mentions Horizon Europe as the primary programme."""
        query = "I work at a university and we have an idea about clean energy"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")
            text_lower = response_text.lower()

            mentions_horizon = "horizon" in text_lower or "cluster" in text_lower

            assert mentions_horizon, (
                f"Response should mention Horizon Europe or clusters. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_mentions_cluster_5_for_energy(self, conversation_id):
        """Test that response correctly identifies Cluster 5 for clean energy."""
        query = "I work at a university and we have an idea about clean energy"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")
            text_lower = response_text.lower()

            # Cluster 5 covers Climate, Energy and Mobility
            mentions_cluster5 = (
                "cluster 5" in text_lower
                or "cluster-5" in text_lower
                or "cl5" in text_lower
                or ("climate" in text_lower and "energy" in text_lower)
            )

            # Also acceptable if it mentions general energy funding
            mentions_energy_funding = "energy" in text_lower and (
                "funding" in text_lower or "call" in text_lower or "horizon" in text_lower
            )

            assert mentions_cluster5 or mentions_energy_funding, (
                f"Response should identify Cluster 5 or energy funding. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_sustainable_agriculture_implicit_intent(self, conversation_id):
        """Test sustainable agriculture query is understood as funding intent."""
        query = "We have expertise in sustainable agriculture"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            understands_intent = self._understands_funding_intent(response_text)

            assert understands_intent, (
                f"Response should understand implicit funding intent. "
                f"Response: {response_text[:500]}..."
            )

    @pytest.mark.asyncio
    async def test_robotics_manufacturing_implicit_intent(self, conversation_id):
        """Test robotics manufacturing query is understood as funding intent."""
        query = "My organization develops robotics for manufacturing"
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await self._send_query(client, conversation_id, query)

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            understands_intent = self._understands_funding_intent(response_text)

            assert understands_intent, (
                f"Response should understand implicit funding intent. "
                f"Response: {response_text[:500]}..."
            )
