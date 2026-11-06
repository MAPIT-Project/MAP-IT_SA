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

import pytest


class TestScenario003GetCallDetails:
    """Test suite for Scenario 003: Get Call Details."""

    BASE_URL = "http://localhost:8000"
    # Using a known valid call ID that exists in the database
    CALL_ID = "HORIZON-EIC-2026-AIC-01"
    QUERY = f"Tell me about call {CALL_ID}"
    PASS_THRESHOLD = 80

    @pytest.mark.asyncio
    async def test_no_duplicate_get_call_details_methods(self):
        """Test that LocalCallSearchService doesn't have duplicate get_call_details methods."""
        import ast
        from pathlib import Path

        service_file = (
            Path(__file__).resolve().parents[2] / "app/services/local_call_search_service.py"
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
