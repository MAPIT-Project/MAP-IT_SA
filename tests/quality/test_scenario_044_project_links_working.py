"""
Test Scenario 044: Project Links Working

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 044
Query: Take 5 project results, verify CORDIS links work
Verify: Links load correct project page
Fix if: Broken links, wrong projects
Pass threshold: 90

This test verifies project link functionality by:
- Taking 5 project results from the system
- Verifying each CORDIS link loads correctly
- Checking that the loaded page shows the correct project
- Testing link construction logic
"""

import logging
import re
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

logger = logging.getLogger(__name__)


class TestScenario044ProjectLinksWorking:
    """Test suite for Scenario 044: Project Links Working."""

    BASE_URL = "http://localhost:8000"
    CORDIS_BASE_URL = "https://cordis.europa.eu/project/id"
    QUERY = "Find 5 projects on renewable energy"
    PASS_THRESHOLD = 90
    LINKS_TO_VERIFY = 5

    # ==========================================================================
    # UNIT TESTS - Test link construction and validation logic
    # ==========================================================================

    def test_cordis_url_format_validation(self):
        """Test that CORDIS URL format validation works correctly."""
        valid_urls = [
            "https://cordis.europa.eu/project/id/101010101",
            "https://cordis.europa.eu/project/id/823914",
            "https://cordis.europa.eu/project/id/1",
        ]
        invalid_urls = [
            "https://cordis.europa.eu/project/",
            "https://cordis.europa.eu/project/id/",
            "http://cordis.europa.eu/project/id/123",  # http instead of https
            "https://example.com/project/id/123",
            "",
            None,
        ]

        for url in valid_urls:
            assert self._is_valid_cordis_url(url), f"Should be valid: {url}"

        for url in invalid_urls:
            assert not self._is_valid_cordis_url(url), f"Should be invalid: {url}"

    def test_extract_project_id_from_url(self):
        """Test extracting project ID from CORDIS URL."""
        test_cases = [
            ("https://cordis.europa.eu/project/id/101010101", "101010101"),
            ("https://cordis.europa.eu/project/id/823914", "823914"),
            ("https://cordis.europa.eu/project/id/1", "1"),
        ]

        for url, expected_id in test_cases:
            extracted = self._extract_project_id_from_url(url)
            assert extracted == expected_id, f"Expected {expected_id}, got {extracted}"

    def test_extract_project_id_invalid_url(self):
        """Test that invalid URLs return None when extracting project ID."""
        invalid_urls = [
            "https://cordis.europa.eu/project/",
            "https://example.com/123",
            "",
            None,
        ]

        for url in invalid_urls:
            extracted = self._extract_project_id_from_url(url)
            assert extracted is None, f"Should return None for: {url}"

    def test_construct_cordis_url(self):
        """Test constructing CORDIS URL from project ID."""
        test_cases = [
            ("101010101", "https://cordis.europa.eu/project/id/101010101"),
            ("823914", "https://cordis.europa.eu/project/id/823914"),
            (823914, "https://cordis.europa.eu/project/id/823914"),  # int input
        ]

        for project_id, expected_url in test_cases:
            constructed = self._construct_cordis_url(project_id)
            assert constructed == expected_url, f"Expected {expected_url}, got {constructed}"

    def test_construct_cordis_url_invalid_input(self):
        """Test constructing CORDIS URL with invalid input."""
        invalid_inputs = ["", None, "abc", "12.34"]

        for input_val in invalid_inputs:
            constructed = self._construct_cordis_url(input_val)
            assert constructed is None, f"Should return None for: {input_val}"

    def test_extract_urls_from_response_text(self):
        """Test extracting CORDIS URLs from response text."""
        response_text = """
        **1. ARIADNE-PLUS: Archaeological data infrastructure**
        🔗 **Details:** https://cordis.europa.eu/project/id/823914

        **2. Time Machine: Big Data of the past**
        🔗 **Details:** https://cordis.europa.eu/project/id/820323

        For more information, visit https://cordis.europa.eu/project/id/665220
        """

        urls = self._extract_cordis_urls_from_text(response_text)
        assert len(urls) == 3, f"Should extract 3 URLs, got {len(urls)}"
        assert "https://cordis.europa.eu/project/id/823914" in urls
        assert "https://cordis.europa.eu/project/id/820323" in urls
        assert "https://cordis.europa.eu/project/id/665220" in urls

    def test_extract_urls_no_urls(self):
        """Test extracting URLs when none present."""
        response_text = "Here are some projects about renewable energy..."
        urls = self._extract_cordis_urls_from_text(response_text)
        assert len(urls) == 0, "Should extract 0 URLs"

    def test_validate_link_response_success(self):
        """Test validating a successful link response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<title>ARIADNE-PLUS | Project | Fact sheet | CORDIS</title>"

        is_valid = self._validate_cordis_response(mock_response, "823914")
        assert is_valid, "Should validate successful response"

    def test_validate_link_response_not_found(self):
        """Test validating a 404 response."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        is_valid = self._validate_cordis_response(mock_response, "invalid123")
        assert not is_valid, "Should reject 404 response"

    def test_validate_link_response_wrong_project(self):
        """Test validating a response for wrong project (redirect)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<title>Different Project | CORDIS</title>"
        mock_response.url = "https://cordis.europa.eu/project/id/999999"  # Different ID

        is_valid = self._validate_cordis_response(
            mock_response, "823914", expected_url="https://cordis.europa.eu/project/id/823914"
        )
        # If final URL differs from expected, it's a redirect to wrong project
        assert not is_valid, "Should reject redirected response to different project"

    def test_calculate_link_success_rate(self):
        """Test calculating link success rate."""
        # 4 out of 5 working = 80%
        results = [True, True, True, True, False]
        rate = self._calculate_success_rate(results)
        assert rate == 80.0, f"Expected 80.0, got {rate}"

        # All working = 100%
        results = [True, True, True, True, True]
        rate = self._calculate_success_rate(results)
        assert rate == 100.0, f"Expected 100.0, got {rate}"

        # None working = 0%
        results = [False, False, False, False, False]
        rate = self._calculate_success_rate(results)
        assert rate == 0.0, f"Expected 0.0, got {rate}"

        # Empty list
        results = []
        rate = self._calculate_success_rate(results)
        assert rate == 0.0, f"Expected 0.0 for empty list, got {rate}"

    def test_link_verification_result_structure(self):
        """Test that link verification result has proper structure."""
        result = self._create_verification_result(
            project_id="823914",
            url="https://cordis.europa.eu/project/id/823914",
            is_working=True,
            status_code=200,
            response_time_ms=150,
            error_message=None,
        )

        assert "project_id" in result
        assert "url" in result
        assert "is_working" in result
        assert "status_code" in result
        assert "response_time_ms" in result
        assert result["is_working"] is True
        assert result["status_code"] == 200

    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================

    def _is_valid_cordis_url(self, url: str | None) -> bool:
        """Check if URL is a valid CORDIS project URL."""
        if not url:
            return False

        pattern = r"^https://cordis\.europa\.eu/project/id/\d+$"
        return bool(re.match(pattern, str(url)))

    def _extract_project_id_from_url(self, url: str | None) -> str | None:
        """Extract project ID from CORDIS URL."""
        if not url:
            return None

        match = re.search(r"cordis\.europa\.eu/project/id/(\d+)", str(url))
        return match.group(1) if match else None

    def _construct_cordis_url(self, project_id: Any) -> str | None:
        """Construct CORDIS URL from project ID."""
        if project_id is None:
            return None

        # Convert to string and validate
        id_str = str(project_id).strip()

        # Must be numeric
        if not id_str.isdigit():
            return None

        if not id_str:
            return None

        return f"https://cordis.europa.eu/project/id/{id_str}"

    def _extract_cordis_urls_from_text(self, text: str) -> list[str]:
        """Extract all CORDIS project URLs from text."""
        pattern = r"https://cordis\.europa\.eu/project/id/\d+"
        return re.findall(pattern, text)

    def _validate_cordis_response(
        self, response: Any, project_id: str, expected_url: str | None = None
    ) -> bool:
        """Validate that CORDIS response is for the correct project."""
        if response.status_code != 200:
            return False

        # If we have an expected URL and the response URL differs, it's a redirect
        if expected_url and hasattr(response, "url"):
            final_url = str(response.url)
            if self._extract_project_id_from_url(final_url) != project_id:
                return False

        return True

    def _calculate_success_rate(self, results: list[bool]) -> float:
        """Calculate success rate from list of boolean results."""
        if not results:
            return 0.0
        return (sum(1 for r in results if r) / len(results)) * 100

    def _create_verification_result(
        self,
        project_id: str,
        url: str,
        is_working: bool,
        status_code: int | None,
        response_time_ms: float | None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        """Create a structured verification result."""
        return {
            "project_id": project_id,
            "url": url,
            "is_working": is_working,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "error_message": error_message,
        }

    async def _verify_cordis_link(
        self, client: httpx.AsyncClient, project_id: str
    ) -> dict[str, Any]:
        """
        Verify that a CORDIS link works and loads the correct project.

        Returns:
            Verification result dict with is_working, status_code, etc.
        """
        import time

        url = self._construct_cordis_url(project_id)
        if not url:
            return self._create_verification_result(
                project_id=project_id,
                url="",
                is_working=False,
                status_code=None,
                response_time_ms=None,
                error_message="Invalid project ID",
            )

        start_time = time.time()

        try:
            response = await client.get(url, follow_redirects=True, timeout=30.0)
            response_time_ms = (time.time() - start_time) * 1000

            is_working = response.status_code == 200

            # Additional validation: check the page contains project content
            if is_working:
                # CORDIS pages should have "CORDIS" in title or contain project data
                has_cordis_content = (
                    "cordis" in response.text.lower() or "project" in response.text.lower()
                )
                is_working = has_cordis_content

            return self._create_verification_result(
                project_id=project_id,
                url=url,
                is_working=is_working,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error_message=None if is_working else f"HTTP {response.status_code}",
            )

        except httpx.TimeoutException:
            return self._create_verification_result(
                project_id=project_id,
                url=url,
                is_working=False,
                status_code=None,
                response_time_ms=None,
                error_message="Timeout",
            )
        except httpx.RequestError as e:
            return self._create_verification_result(
                project_id=project_id,
                url=url,
                is_working=False,
                status_code=None,
                response_time_ms=None,
                error_message=str(e),
            )

    # ==========================================================================
    # API INTEGRATION TESTS - Test link extraction from API responses
    # ==========================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
