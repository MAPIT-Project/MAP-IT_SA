"""
Scenario 022: EU4Health Topics
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "What EU4Health priorities focus on cancer?"
Expected: Europe's Beating Cancer Plan actions, specific calls
Verify: Cancer-specific EU4Health info
Pass threshold: 80
"""

import httpx
import pytest


class TestScenario022EU4HealthTopics:
    """Test EU4Health topics/priorities query for cancer."""

    BASE_URL = "http://localhost:8000"
    QUERY = "What EU4Health priorities focus on cancer?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(220000, 229999)

    @pytest.mark.asyncio
    async def test_mentions_cancer(self, conversation_id):
        """Test that response mentions cancer."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention cancer
            assert "cancer" in response_text, "Response should mention cancer"

    @pytest.mark.asyncio
    async def test_mentions_beating_cancer_plan(self, conversation_id):
        """Test that response mentions Europe's Beating Cancer Plan."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention Europe's Beating Cancer Plan
            cancer_plan_indicators = [
                "beating cancer plan",
                "cancer plan",
                "europe's beating cancer",
            ]

            has_cancer_plan = any(ind in response_text for ind in cancer_plan_indicators)
            assert has_cancer_plan, "Response should mention Europe's Beating Cancer Plan"

    @pytest.mark.asyncio
    async def test_mentions_prevention(self, conversation_id):
        """Test that response mentions disease prevention."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention prevention (cancer prevention is a key EU4Health priority)
            prevention_indicators = [
                "prevention",
                "screening",
                "early detection",
            ]

            has_prevention = any(ind in response_text for ind in prevention_indicators)
            assert has_prevention, "Response should mention prevention or screening"

    @pytest.mark.asyncio
    async def test_mentions_eu4health_programme(self, conversation_id):
        """Test that response confirms it's about EU4Health."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention EU4Health
            eu4health_indicators = [
                "eu4health",
                "eu 4 health",
            ]

            has_eu4health = any(ind in response_text for ind in eu4health_indicators)
            assert has_eu4health, "Response should confirm it's about EU4Health programme"

    @pytest.mark.asyncio
    async def test_uses_correct_tool(self, conversation_id):
        """Test that the correct tool is used for EU4Health topics."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Should use search_eu4health_templates tool
            has_eu4health_tool = any("eu4health" in tool.lower() for tool in tools_used)
            assert has_eu4health_tool, f"Should use EU4Health tool, got: {tools_used}"

    @pytest.mark.asyncio
    async def test_provides_actionable_next_steps(self, conversation_id):
        """Test that response provides actionable next steps."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should provide next steps
            actionable_indicators = [
                "next steps",
                "annual work programme",
                "funding & tenders portal",
                "funding portal",
                "hadea",
            ]

            has_actionable = any(ind in response_text for ind in actionable_indicators)
            assert has_actionable, "Response should provide actionable next steps"

    @pytest.mark.asyncio
    async def test_provides_links(self, conversation_id):
        """Test that response provides relevant links."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain URLs/links
            has_links = "http" in response_text or "https" in response_text
            assert has_links, "Response should contain links to resources"

    @pytest.mark.asyncio
    async def test_no_confusion_with_other_programmes(self, conversation_id):
        """Test that response doesn't confuse EU4Health with other programmes."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should NOT primarily mention other programmes
            # (Some mentions of Horizon Europe health research are OK for context)
            # The response should be clearly about EU4Health
            eu4health_count = response_text.count("eu4health")
            horizon_count = response_text.count("horizon europe")

            # EU4Health should be mentioned more or other programmes shouldn't dominate
            if horizon_count > 0:
                assert (
                    eu4health_count >= horizon_count
                ), "Response should primarily focus on EU4Health, not Horizon Europe"

    @pytest.mark.asyncio
    async def test_mentions_specific_cancer_priorities(self, conversation_id):
        """Test that response mentions specific cancer-related priorities."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention at least one specific cancer priority
            cancer_priorities = [
                "screening",
                "early detection",
                "cancer prevention",
                "cancer research",
                "cancer survivors",
                "inequalities",
                "cancer care",
                "ncd",
                "non-communicable",
            ]

            found_priorities = [p for p in cancer_priorities if p in response_text]
            assert (
                len(found_priorities) >= 2
            ), f"Response should mention at least 2 cancer priorities, found: {found_priorities}"

    @pytest.mark.asyncio
    async def test_response_is_well_structured(self, conversation_id):
        """Test that response is well-structured with headings or bullet points."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should have some structure (headers, bullets, or bold text)
            has_structure = any(
                [
                    "**" in response_text,  # Bold
                    "##" in response_text,  # Headers
                    "- " in response_text,  # Bullets
                    "• " in response_text,  # Bullets
                ]
            )
            assert has_structure, "Response should be well-structured with formatting"

    @pytest.mark.asyncio
    async def test_response_minimum_length(self, conversation_id):
        """Test that response is comprehensive (not too short)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should be a comprehensive response
            assert (
                len(response_text) >= 500
            ), f"Response should be comprehensive (500+ chars), got {len(response_text)}"

    @pytest.mark.asyncio
    async def test_overall_quality_score(self, conversation_id):
        """Test overall quality score based on multiple criteria."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            score = 0

            # Query Fulfillment (40 points)
            # - Mentions cancer (10)
            if "cancer" in response_text:
                score += 10
            # - Mentions EU4Health priorities (15)
            if "eu4health" in response_text and any(
                p in response_text for p in ["prevention", "priorities", "plan"]
            ):
                score += 15
            # - Mentions specific cancer plan actions (15)
            if any(
                p in response_text
                for p in ["screening", "early detection", "cancer research", "survivors"]
            ):
                score += 15

            # Specificity (25 points)
            # - Mentions Europe's Beating Cancer Plan (10)
            if "beating cancer" in response_text or "cancer plan" in response_text:
                score += 10
            # - Mentions PREVENTION strand (8)
            if "prevention" in response_text:
                score += 8
            # - Mentions specific priorities/calls (7)
            if any(p in response_text for p in ["ncd", "non-communicable", "health promotion"]):
                score += 7

            # Factual Accuracy (25 points)
            # - EU4Health is the correct programme (10)
            if "eu4health" in response_text:
                score += 10
            # - Cancer is in PREVENTION strand (10)
            if "prevention" in response_text and "cancer" in response_text:
                score += 10
            # - No factual errors (5) - assume correct if other checks pass
            if score >= 40:
                score += 5

            # Actionability (10 points)
            # - Provides next steps (5)
            if "next steps" in response_text or "annual work programme" in response_text:
                score += 5
            # - Provides links (5)
            if "http" in result.get("response", ""):
                score += 5

            assert (
                score >= self.PASS_THRESHOLD
            ), f"Quality score {score} below threshold {self.PASS_THRESHOLD}"
