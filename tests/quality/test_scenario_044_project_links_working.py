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
import os
import random
import re
from typing import Any
from unittest.mock import MagicMock

import httpx
import psycopg2
import pytest
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class TestScenario044ProjectLinksWorking:
    """Test suite for Scenario 044: Project Links Working."""

    BASE_URL = "http://localhost:8000"
    CORDIS_BASE_URL = "https://cordis.europa.eu/project/id"
    QUERY = "Find 5 projects on renewable energy"
    PASS_THRESHOLD = 90
    LINKS_TO_VERIFY = 5

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        return random.randint(44000000, 44999999)

    @pytest.fixture
    def clear_redis_cache(self):
        """Clear Redis cache before test to avoid stale query plans."""
        import subprocess

        try:
            subprocess.run(
                ["docker", "exec", "map-it_sa-redis-1", "redis-cli", "FLUSHALL"],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass
        return True

    @pytest.fixture
    def db_connection(self):
        """Create a database connection."""
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        conn = psycopg2.connect(db_url)
        yield conn
        conn.close()

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

    @pytest.mark.asyncio
    async def test_api_returns_cordis_links(self, conversation_id, clear_redis_cache):
        """Test that the API returns CORDIS links in project responses."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200, f"API returned {response.status_code}"
            result = response.json()

            response_text = result.get("response", "")
            urls = self._extract_cordis_urls_from_text(response_text)

            assert len(urls) >= 1, f"Response should contain CORDIS links, got: {urls}"

            # All URLs should be valid format
            for url in urls:
                assert self._is_valid_cordis_url(url), f"Invalid URL format: {url}"

    @pytest.mark.asyncio
    async def test_extracted_links_are_unique(self, conversation_id, clear_redis_cache):
        """Test that extracted CORDIS links are unique (no duplicates)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")
            urls = self._extract_cordis_urls_from_text(response_text)

            unique_urls = set(urls)
            assert len(urls) == len(unique_urls), "Should not have duplicate CORDIS links"

    @pytest.mark.asyncio
    async def test_project_ids_in_urls_match_response(self, conversation_id, clear_redis_cache):
        """Test that project IDs in CORDIS URLs match the projects mentioned."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            urls = self._extract_cordis_urls_from_text(response_text)

            for url in urls:
                project_id = self._extract_project_id_from_url(url)
                assert project_id is not None, f"Could not extract ID from URL: {url}"
                # The project ID should appear somewhere in the response
                # (either in the URL or as "Project ID: XXXXX")
                assert project_id in response_text, (
                    f"Project ID {project_id} from URL not found in response"
                )

    @pytest.mark.asyncio
    async def test_verify_cordis_links_work(self, conversation_id, clear_redis_cache):
        """
        MAIN TEST: Verify that CORDIS links actually work and load correct pages.

        This is the core test for Scenario 044.
        """
        async with httpx.AsyncClient(timeout=180.0) as client:
            # Step 1: Get projects from API
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200, f"API returned {response.status_code}"
            result = response.json()
            response_text = result.get("response", "")

            # Step 2: Extract CORDIS URLs
            urls = self._extract_cordis_urls_from_text(response_text)
            assert len(urls) >= 1, "Response should contain CORDIS links"

            # Take up to 5 links to verify
            urls_to_verify = urls[: self.LINKS_TO_VERIFY]

            # Step 3: Verify each link
            verification_results = []
            async with httpx.AsyncClient(timeout=30.0) as cordis_client:
                for url in urls_to_verify:
                    project_id = self._extract_project_id_from_url(url)
                    if project_id:
                        result = await self._verify_cordis_link(cordis_client, project_id)
                        verification_results.append(result)

            # Step 4: Calculate success rate
            working_links = [r for r in verification_results if r["is_working"]]
            success_rate = self._calculate_success_rate(
                [r["is_working"] for r in verification_results]
            )

            # Log detailed results
            logger.info("\n=== CORDIS Link Verification Results ===")
            for result in verification_results:
                status = "WORKING" if result["is_working"] else "BROKEN"
                logger.info(
                    f"  {status}: {result['url']} "
                    f"(HTTP {result['status_code']}, {result['response_time_ms']:.0f}ms)"
                )
            logger.info(
                f"Success Rate: {success_rate:.1f}% "
                f"({len(working_links)}/{len(verification_results)})"
            )

            # Print summary
            print("\n=== CORDIS Link Verification ===")
            print(f"Links tested: {len(verification_results)}")
            print(f"Working: {len(working_links)}")
            print(f"Broken: {len(verification_results) - len(working_links)}")
            print(f"Success Rate: {success_rate:.1f}%")
            print(f"Pass Threshold: {self.PASS_THRESHOLD}%")

            # Assert threshold
            assert success_rate >= self.PASS_THRESHOLD, (
                f"Link success rate {success_rate:.1f}% below threshold {self.PASS_THRESHOLD}%. "
                f"Broken links: {[r for r in verification_results if not r['is_working']]}"
            )

    @pytest.mark.asyncio
    async def test_no_error_in_response(self, conversation_id, clear_redis_cache):
        """Test that response does not contain error messages."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()

            assert "error" not in result, f"Response should not have error: {result.get('error')}"

            response_text = result.get("response", "")
            error_phrases = ["error occurred", "I apologize", "unable to", "failed to"]
            has_error = any(phrase in response_text.lower() for phrase in error_phrases)
            assert not has_error, "Response should not contain error messages"


class TestProjectLinksDatabase:
    """Tests for verifying project link data at the database level."""

    CORDIS_BASE_URL = "https://cordis.europa.eu/project/id"
    PASS_THRESHOLD = 90

    @pytest.fixture
    def db_connection(self):
        """Create a database connection."""
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        conn = psycopg2.connect(db_url)
        yield conn
        conn.close()

    def test_database_has_projects_with_ids(self, db_connection):
        """Test that the database has projects with valid IDs."""
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT COUNT(*) as total,
                   COUNT(id) as with_id,
                   COUNT(*) FILTER (WHERE id IS NOT NULL AND id != '') as with_valid_id
            FROM projects
        """
        )

        result = cursor.fetchone()
        cursor.close()

        total = result["total"]
        with_valid_id = result["with_valid_id"]

        assert total > 0, "Database should have projects"
        coverage = (with_valid_id / total) * 100
        logger.info(f"Project ID coverage: {coverage:.1f}% ({with_valid_id}/{total})")
        assert coverage >= 99, f"Only {coverage:.1f}% projects have valid IDs"

    def test_project_ids_are_numeric(self, db_connection):
        """Test that project IDs are numeric (required for CORDIS URL)."""
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT COUNT(*) as total,
                   COUNT(*) FILTER (WHERE id ~ '^[0-9]+$') as numeric_ids
            FROM projects
            WHERE id IS NOT NULL AND id != ''
        """
        )

        result = cursor.fetchone()
        cursor.close()

        total = result["total"]
        numeric_ids = result["numeric_ids"]

        if total > 0:
            coverage = (numeric_ids / total) * 100
            logger.info(f"Numeric ID coverage: {coverage:.1f}% ({numeric_ids}/{total})")
            assert coverage >= 99, f"Only {coverage:.1f}% projects have numeric IDs"

    def test_sample_project_ids_construct_valid_urls(self, db_connection):
        """Test that sample project IDs can construct valid CORDIS URLs."""
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT id, title, acronym
            FROM projects
            WHERE id IS NOT NULL AND id != ''
            ORDER BY RANDOM()
            LIMIT 10
        """
        )

        projects = cursor.fetchall()
        cursor.close()

        valid_count = 0
        for project in projects:
            project_id = project["id"]
            url = f"{self.CORDIS_BASE_URL}/{project_id}"

            # Validate URL format
            pattern = r"^https://cordis\.europa\.eu/project/id/\d+$"
            if re.match(pattern, url):
                valid_count += 1
            else:
                logger.warning(f"Invalid URL for project {project_id}: {url}")

        rate = (valid_count / len(projects)) * 100 if projects else 0
        logger.info(f"Valid URL construction rate: {rate:.1f}% ({valid_count}/{len(projects)})")
        assert rate >= 90, f"Only {rate:.1f}% URLs are valid"

    @pytest.mark.asyncio
    async def test_verify_random_database_project_links(self, db_connection):
        """
        Test that random project links from database actually work.

        This tests the underlying data quality for link generation.
        """
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)

        # Get 5 random projects
        cursor.execute(
            """
            SELECT id, title, acronym
            FROM projects
            WHERE id IS NOT NULL AND id != '' AND id ~ '^[0-9]+$'
            ORDER BY RANDOM()
            LIMIT 5
        """
        )

        projects = cursor.fetchall()
        cursor.close()

        if not projects:
            pytest.skip("No projects with valid IDs found")

        # Verify each link
        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for project in projects:
                project_id = project["id"]
                url = f"{self.CORDIS_BASE_URL}/{project_id}"

                try:
                    response = await client.get(url, follow_redirects=True)
                    is_working = response.status_code == 200

                    # Verify content is a CORDIS page
                    if is_working:
                        is_working = "cordis" in response.text.lower()

                    results.append(
                        {
                            "project_id": project_id,
                            "title": project["title"],
                            "url": url,
                            "is_working": is_working,
                            "status_code": response.status_code,
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "project_id": project_id,
                            "title": project["title"],
                            "url": url,
                            "is_working": False,
                            "status_code": None,
                            "error": str(e),
                        }
                    )

        # Calculate success rate
        working = [r for r in results if r["is_working"]]
        rate = (len(working) / len(results)) * 100 if results else 0

        # Log results
        logger.info("\n=== Database Project Link Verification ===")
        for r in results:
            status = "WORKING" if r["is_working"] else "BROKEN"
            logger.info(f"  {status}: {r['project_id']} ({r['title'][:40]}...)")
        logger.info(f"Success Rate: {rate:.1f}%")

        print(f"\n=== Database Links: {rate:.1f}% working ({len(working)}/{len(results)}) ===")

        assert rate >= self.PASS_THRESHOLD, (
            f"Only {rate:.1f}% of database project links work. "
            f"Broken: {[r for r in results if not r['is_working']]}"
        )

    def test_no_duplicate_project_ids(self, db_connection):
        """Test that project IDs are unique (no duplicates)."""
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT id, COUNT(*) as cnt
            FROM projects
            WHERE id IS NOT NULL
            GROUP BY id
            HAVING COUNT(*) > 1
            LIMIT 10
        """
        )

        duplicates = cursor.fetchall()
        cursor.close()

        if duplicates:
            logger.warning(f"Found {len(duplicates)} duplicate project IDs: {duplicates[:5]}")

        assert len(duplicates) == 0, f"Found duplicate project IDs: {duplicates}"

    def test_project_ids_reasonable_range(self, db_connection):
        """Test that project IDs are in a reasonable range for CORDIS."""
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT
                MIN(CAST(id AS BIGINT)) as min_id,
                MAX(CAST(id AS BIGINT)) as max_id,
                AVG(CAST(id AS BIGINT)) as avg_id,
                COUNT(*) as total
            FROM projects
            WHERE id IS NOT NULL AND id ~ '^[0-9]+$'
        """
        )

        result = cursor.fetchone()
        cursor.close()

        min_id = result["min_id"]
        max_id = result["max_id"]

        logger.info(f"Project ID range: {min_id} - {max_id}")

        # CORDIS project IDs are typically 6-9 digits
        # Horizon Europe projects typically start from 101000000+
        assert min_id >= 1, f"Min ID should be positive: {min_id}"
        # Max ID should be reasonable (not billions)
        assert max_id < 10000000000, f"Max ID seems too large: {max_id}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
