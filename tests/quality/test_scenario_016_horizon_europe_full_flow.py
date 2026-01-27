"""
Scenario 016: Horizon Europe Full Flow
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "I'm a university wanting to do AI research. What Horizon Europe options do I have?"
Expected: Eligibility confirmed, relevant calls listed, application guidance
Verify: Complete flow works end-to-end
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario016HorizonEuropeFullFlow:
    """Test Horizon Europe full flow for university AI research."""

    BASE_URL = "http://localhost:8000"
    QUERY = "I'm a university wanting to do AI research. What Horizon Europe options do I have?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(160000, 169999)

    @pytest.mark.asyncio
    async def test_confirms_university_eligibility(self, conversation_id):
        """Test that response confirms universities are eligible for Horizon Europe."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should confirm eligibility or show calls (implicit eligibility)
            # Universities are core participants in Horizon Europe
            eligibility_indicators = [
                "eligible",
                "can apply",
                "can participate",
                "universities",
                "higher education",
                "research institution",
                "university",
                "academic",
                "ria",  # Research and Innovation Action - universities are key
                "erc",  # European Research Council - for researchers
                "msca",  # Marie Curie - for researchers
            ]

            # Or if they show calls with application links, that implies eligibility
            has_eligibility = any(ind in response_text for ind in eligibility_indicators)

            # Showing funding calls also implies eligibility
            call_indicators = ["call", "deadline", "apply", "funding", "budget"]
            has_calls = sum(1 for ind in call_indicators if ind in response_text) >= 3

            assert has_eligibility or has_calls, (
                "Response should confirm university eligibility or show applicable calls"
            )

    @pytest.mark.asyncio
    async def test_lists_ai_relevant_calls(self, conversation_id):
        """Test that response lists AI-relevant funding calls."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should contain AI-related content
            ai_indicators = [
                "ai",
                "artificial intelligence",
                "machine learning",
                "deep learning",
                "robotics",
                "digital",
                "generative",
            ]

            has_ai_content = any(ind in response_text for ind in ai_indicators)

            assert has_ai_content, "Response should list AI-relevant funding options"

    @pytest.mark.asyncio
    async def test_includes_funding_calls(self, conversation_id):
        """Test that response includes specific funding calls."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain call IDs (HORIZON-xxx format)
            call_pattern = r"HORIZON-[A-Z0-9\-]+"
            calls_found = re.findall(call_pattern, response_text, re.IGNORECASE)

            # Should have at least some calls
            assert len(calls_found) >= 1, f"Should list specific calls. Found: {calls_found}"

    @pytest.mark.asyncio
    async def test_includes_deadlines(self, conversation_id):
        """Test that response includes deadlines for calls."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain deadline information
            deadline_indicators = [
                r"deadline",
                r"\d{1,2}\s+\w+\s+2026",  # Date format like "26 February 2026"
                r"\d{4}-\d{2}-\d{2}",  # ISO format
                r"due\s+date",
                r"closes",
                r"closing",
            ]

            has_deadline = any(
                re.search(pattern, response_text, re.IGNORECASE) for pattern in deadline_indicators
            )

            assert has_deadline, "Response should include deadlines"

    @pytest.mark.asyncio
    async def test_includes_application_guidance(self, conversation_id):
        """Test that response includes application guidance."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should contain application guidance
            guidance_indicators = [
                "how to apply",
                "apply",
                "register",
                "portal",
                "next steps",
                "submit",
                "eligibility",
                "partner",
                "consortium",
                "application",
            ]

            guidance_found = sum(1 for g in guidance_indicators if g in response_text)

            assert guidance_found >= 2, (
                f"Response should include application guidance. Found {guidance_found} indicators"
            )

    @pytest.mark.asyncio
    async def test_includes_apply_links(self, conversation_id):
        """Test that response includes links to apply."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain EU portal links
            link_indicators = [
                "ec.europa.eu",
                "https://",
                "funding-tenders",
            ]

            has_links = any(ind in response_text for ind in link_indicators)

            assert has_links, "Response should include application links"

    @pytest.mark.asyncio
    async def test_uses_search_funding_calls_tool(self, conversation_id):
        """Test that search_funding_calls tool is used."""
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
            reasoning_steps = metadata.get("reasoning_steps", [])

            # Check for funding call search tool
            has_call_search = any("search_funding_calls" in str(t) for t in tools_used)
            has_call_in_reasoning = any("search_funding_calls" in str(s) for s in reasoning_steps)

            assert has_call_search or has_call_in_reasoning, (
                f"Expected search_funding_calls tool. Tools: {tools_used}"
            )

    @pytest.mark.asyncio
    async def test_references_horizon_europe(self, conversation_id):
        """Test that response references Horizon Europe programme."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should reference Horizon Europe
            horizon_indicators = ["horizon europe", "horizon-europe", "horizon", "eic", "erc"]

            has_horizon = any(ind in response_text for ind in horizon_indicators)

            assert has_horizon, "Response should reference Horizon Europe"

    @pytest.mark.asyncio
    async def test_includes_budget_information(self, conversation_id):
        """Test that response includes budget/funding information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain budget/funding info
            budget_indicators = [
                r"eur\s*\d",
                r"\d+\s*million",
                r"€\s*\d",
                r"budget",
                r"funding",
            ]

            has_budget = any(
                re.search(pattern, response_text, re.IGNORECASE) for pattern in budget_indicators
            )

            assert has_budget, "Response should include budget information"

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

            error_indicators = [
                "error occurred",
                "failed to",
                "unable to",
                "something went wrong",
                "i cannot",
                "no calls found",
                "no funding found",
            ]

            has_error = any(ind in response_text for ind in error_indicators)

            assert not has_error, "Response should not contain error messages"

    @pytest.mark.asyncio
    async def test_response_length_appropriate(self, conversation_id):
        """Test that response has appropriate length for a comprehensive answer."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should be substantial but not overwhelming
            assert len(response_text) >= 500, f"Response too short: {len(response_text)} chars"
            assert len(response_text) <= 15000, f"Response too long: {len(response_text)} chars"

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
            # - Eligibility confirmed (10 pts)
            eligibility_terms = ["eligible", "can apply", "can participate", "universities"]
            if any(t in text_lower for t in eligibility_terms):
                score += 10
            elif "call" in text_lower and "apply" in text_lower:
                score += 7  # Implicit eligibility through showing applicable calls

            # - AI-relevant calls listed (15 pts)
            ai_terms = ["ai", "artificial intelligence", "machine learning", "digital"]
            ai_found = sum(1 for t in ai_terms if t in text_lower)
            if ai_found >= 2:
                score += 15
            elif ai_found >= 1:
                score += 10

            # - Multiple options shown (15 pts)
            call_pattern = r"HORIZON-[A-Z0-9\-]+"
            calls_found = len(re.findall(call_pattern, response_text, re.IGNORECASE))
            if calls_found >= 5:
                score += 15
            elif calls_found >= 3:
                score += 12
            elif calls_found >= 1:
                score += 8

            # Specificity (25 points)
            # - Specific call IDs (10 pts) - already counted above
            if calls_found >= 3:
                score += 10
            elif calls_found >= 1:
                score += 5

            # - Deadlines included (8 pts)
            deadline_patterns = [r"\d{1,2}\s+\w+\s+2026", r"deadline", r"closing"]
            if any(re.search(p, response_text, re.IGNORECASE) for p in deadline_patterns):
                score += 8

            # - Budget information (7 pts)
            if re.search(r"eur\s*\d|\d+\s*million|budget", response_text, re.IGNORECASE):
                score += 7

            # Factual Accuracy (25 points)
            # - Horizon Europe reference (10 pts)
            if "horizon europe" in text_lower:
                score += 10
            elif "horizon" in text_lower:
                score += 6

            # - No wrong programme info (10 pts)
            wrong_info = ["horizon 2020 calls", "fp7 calls", "h2020"]
            if not any(w in text_lower for w in wrong_info):
                score += 10

            # - Correct call format (5 pts)
            if re.search(r"HORIZON-[A-Z]{2,4}-\d{4}", response_text, re.IGNORECASE):
                score += 5

            # Actionability (10 points)
            # - Application guidance (5 pts)
            action_terms = ["next steps", "how to apply", "register", "portal"]
            if sum(1 for t in action_terms if t in text_lower) >= 2:
                score += 5
            elif sum(1 for t in action_terms if t in text_lower) >= 1:
                score += 3

            # - Links provided (5 pts)
            if "ec.europa.eu" in response_text or "https://" in response_text:
                score += 5

            assert score >= self.PASS_THRESHOLD, (
                f"Quality score {score} is below threshold {self.PASS_THRESHOLD}"
            )

    @pytest.mark.asyncio
    async def test_full_scenario_integration(self, conversation_id):
        """Full integration test for Scenario 016."""
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
            assert len(response_text) > 500, f"Response too short: {len(response_text)} chars"

            # Must have AI content
            assert any(t in text_lower for t in ["ai", "artificial intelligence", "digital"]), (
                "Missing AI content"
            )

            # Must have Horizon Europe reference
            assert "horizon" in text_lower, "Missing Horizon Europe reference"

            # Must have funding calls
            call_pattern = r"HORIZON-[A-Z0-9\-]+"
            calls_found = re.findall(call_pattern, response_text, re.IGNORECASE)
            assert len(calls_found) >= 1, f"Should list specific calls. Found: {calls_found}"

            # Must have application guidance
            guidance_terms = ["apply", "portal", "submit", "register", "next steps"]
            has_guidance = sum(1 for t in guidance_terms if t in text_lower) >= 2
            assert has_guidance, "Missing application guidance"

            # Metadata should indicate success
            tools_used = metadata.get("tools_used", [])
            assert len(tools_used) >= 1, f"Expected tools to be used. Tools: {tools_used}"

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

            # Should have structured elements
            structure_indicators = [
                r"\*\*.*\*\*",  # Bold text
                r"^\s*[-*\u2022\d+\.]\s+",  # List items
                r"---",  # Separators
                r"###?\s+",  # Headers
            ]

            structure_found = sum(
                1
                for pattern in structure_indicators
                if re.search(pattern, response_text, re.MULTILINE)
            )

            assert structure_found >= 2, (
                f"Response should be well-structured. Found: {structure_found}"
            )
