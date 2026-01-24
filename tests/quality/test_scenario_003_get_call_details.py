"""
Test Scenario 003: Get Call Details

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 003
Query: "Tell me about call HORIZON-EIC-2026-AIC-01"
Expected: Full call details - title, deadline, budget, scope, eligibility
Verify: Data matches EU Portal
Pass threshold: 80

This test verifies that the system properly retrieves and displays:
- Call ID and title
- Deadline for applications
- Budget information
- Scope and objectives
- Eligibility requirements (if available)
"""

import re

import httpx
import pytest


class TestScenario003GetCallDetails:
    """Test suite for Scenario 003: Get Call Details."""

    BASE_URL = "http://localhost:8000"
    # Using a known valid call ID that exists in the database
    CALL_ID = "HORIZON-EIC-2026-AIC-01"
    QUERY = f"Tell me about call {CALL_ID}"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(100000, 999999)

    @pytest.mark.asyncio
    async def test_returns_call_details(self, conversation_id):
        """Test that the query returns call details."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            assert response.status_code == 200, f"API returned {response.status_code}"
            result = response.json()

            response_text = result.get("response", "")

            # Should mention the call ID
            assert (
                self.CALL_ID in response_text or "EIC" in response_text
            ), "Response should reference the call ID or programme"

    @pytest.mark.asyncio
    async def test_includes_call_title(self, conversation_id):
        """Test that response includes the call title."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should include the title or relevant keywords from it
            assert any(
                keyword in response_text.lower()
                for keyword in ["physical ai", "robotics", "embodied", "accelerating"]
            ), "Response should include call title or related keywords"

    @pytest.mark.asyncio
    async def test_uses_get_call_details_tool(self, conversation_id):
        """Test that the get_call_details tool is used."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            tools_used = result.get("metadata", {}).get("tools_used", [])

            # Should use get_call_details tool
            assert any(
                "get_call_details" in tool for tool in tools_used
            ), f"Should use get_call_details tool, got: {tools_used}"

    @pytest.mark.asyncio
    async def test_includes_scope_or_description(self, conversation_id):
        """Test that response includes scope/objective information."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should include substantive content about the call
            assert len(response_text) > 500, "Response should provide detailed information"

            # Should mention objectives or scope
            assert any(
                keyword in response_text.lower()
                for keyword in ["objective", "scope", "aim", "goal", "focus", "challenge"]
            ), "Response should include scope or objectives"

    @pytest.mark.asyncio
    async def test_quality_score_meets_threshold(self, conversation_id):
        """Test that the quality score meets the passing threshold."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            quality_score = result.get("metadata", {}).get("quality_analysis", {}).get("score", 0)

            assert (
                quality_score >= self.PASS_THRESHOLD
            ), f"Quality score {quality_score} is below threshold {self.PASS_THRESHOLD}"

    @pytest.mark.asyncio
    async def test_no_deflection_or_error(self, conversation_id):
        """Test that response doesn't contain deflection or error messages."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "").lower()

            # Should not contain deflection phrases
            deflection_phrases = [
                "i couldn't find",
                "no information",
                "not found",
                "please try a more specific",
                "i don't have information",
            ]
            for phrase in deflection_phrases:
                assert phrase not in response_text, f"Response contains deflection: '{phrase}'"

    @pytest.mark.asyncio
    async def test_includes_trl_or_technology_level(self, conversation_id):
        """Test that response mentions TRL or technology readiness level."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # EIC calls typically specify TRL requirements
            assert (
                "TRL" in response_text or "technology readiness" in response_text.lower()
            ), "Response should mention TRL for EIC calls"

    @pytest.mark.asyncio
    async def test_includes_stages_or_phases(self, conversation_id):
        """Test that response describes the challenge stages."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY},
            )

            result = response.json()
            response_text = result.get("response", "")

            # This is a two-stage challenge
            assert (
                "stage" in response_text.lower()
            ), "Response should mention the two-stage structure of this challenge"

    @pytest.mark.asyncio
    async def test_service_returns_budget(self):
        """Test that LocalCallSearchService returns budget for this call."""
        import sys

        sys.path.insert(0, "/home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA")

        from app.services.local_call_search_service import LocalCallSearchService

        service = LocalCallSearchService()
        result = service.get_call_details(self.CALL_ID)

        assert result is not None, "Service should return call details"
        assert result.get("budget") is not None, "Service should return budget"
        assert "million" in result.get("budget", "").lower() or "EUR" in result.get(
            "budget", ""
        ), f"Budget should be formatted, got: {result.get('budget')}"

    @pytest.mark.asyncio
    async def test_service_returns_deadline(self):
        """Test that LocalCallSearchService returns deadline for this call."""
        import sys

        sys.path.insert(0, "/home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA")

        from app.services.local_call_search_service import LocalCallSearchService

        service = LocalCallSearchService()
        result = service.get_call_details(self.CALL_ID)

        assert result is not None, "Service should return call details"
        assert result.get("deadline") is not None, "Service should return deadline"
        # Deadline should be in a readable format
        assert re.search(
            r"\d{1,2}\s+\w+\s+\d{4}", result.get("deadline", "")
        ), f"Deadline should be formatted like '26 February 2026', got: {result.get('deadline')}"

    @pytest.mark.asyncio
    async def test_service_returns_status(self):
        """Test that LocalCallSearchService returns status for this call."""
        import sys

        sys.path.insert(0, "/home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA")

        from app.services.local_call_search_service import LocalCallSearchService

        service = LocalCallSearchService()
        result = service.get_call_details(self.CALL_ID)

        assert result is not None, "Service should return call details"
        assert result.get("status") is not None, "Service should return status"
        assert result.get("status") in [
            "open",
            "upcoming",
            "closed",
        ], f"Status should be valid, got: {result.get('status')}"

    @pytest.mark.asyncio
    async def test_no_duplicate_get_call_details_methods(self):
        """Test that LocalCallSearchService doesn't have duplicate get_call_details methods."""
        import ast
        from pathlib import Path

        service_file = Path(
            "/home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA/app/services/local_call_search_service.py"
        )
        content = service_file.read_text()
        tree = ast.parse(content)

        method_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_call_details":
                method_count += 1

        assert method_count == 1, (
            f"LocalCallSearchService should have exactly 1 get_call_details method, "
            f"found {method_count}"
        )
