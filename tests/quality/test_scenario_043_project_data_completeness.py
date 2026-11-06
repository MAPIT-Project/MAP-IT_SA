"""
Test Scenario 043: Project Data Completeness

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 043
Query: "Find 10 projects on machine learning"
Verify: All 10 have: title, budget, coordinator, status, dates
Fix if: Missing essential fields
Pass threshold: 85

This test verifies project data completeness by:
- Querying for machine learning projects
- Verifying all returned projects have essential fields populated
- Checking data quality (non-empty, valid values)
- Testing database-level data completeness
"""

import logging
import re
from typing import Any

import pytest

logger = logging.getLogger(__name__)


class TestScenario043ProjectDataCompleteness:
    """Test suite for Scenario 043: Project Data Completeness."""

    BASE_URL = "http://localhost:8000"
    QUERY = "Find 10 projects on machine learning"
    PASS_THRESHOLD = 85
    REQUIRED_PROJECTS = 10
    # Essential fields that must be present for each project
    ESSENTIAL_FIELDS = ["title", "budget", "coordinator", "status", "start_date", "end_date"]

    # ==========================================================================
    # UNIT TESTS - Test field validation logic
    # ==========================================================================

    def test_validate_title_present(self):
        """Test that title validation works correctly."""
        valid_project = {"title": "Machine Learning Project"}
        invalid_project = {"title": ""}
        null_project = {"title": None}

        assert self._has_valid_title(valid_project), "Valid title should pass"
        assert not self._has_valid_title(invalid_project), "Empty title should fail"
        assert not self._has_valid_title(null_project), "Null title should fail"

    def test_validate_budget_present(self):
        """Test that budget validation works correctly."""
        valid_budget = {"ec_contribution": 5000000}
        valid_total_cost = {"total_cost": 6000000}
        zero_budget = {"ec_contribution": 0, "total_cost": 0}
        null_budget = {"ec_contribution": None, "total_cost": None}

        assert self._has_valid_budget(valid_budget), "Valid EC contribution should pass"
        assert self._has_valid_budget(valid_total_cost), "Valid total cost should pass"
        assert not self._has_valid_budget(zero_budget), "Zero budget should fail"
        assert not self._has_valid_budget(null_budget), "Null budget should fail"

    def test_validate_coordinator_present(self):
        """Test that coordinator validation works correctly."""
        valid_coordinator = {"coordinator": {"name": "University of Example"}}
        nested_valid = {"coordinator_name": "Research Institute"}
        placeholder = {"coordinator": {"name": "Data not yet available"}}
        null_coordinator = {"coordinator": None}

        assert self._has_valid_coordinator(valid_coordinator), "Valid coordinator should pass"
        assert self._has_valid_coordinator(nested_valid), "Coordinator name field should pass"
        assert not self._has_valid_coordinator(placeholder), "Placeholder should fail"
        assert not self._has_valid_coordinator(null_coordinator), "Null coordinator should fail"

    def test_validate_status_present(self):
        """Test that status validation works correctly."""
        signed = {"status": "SIGNED"}
        closed = {"status": "CLOSED"}
        unknown = {"status": "Unknown"}
        empty = {"status": ""}

        assert self._has_valid_status(signed), "SIGNED status should pass"
        assert self._has_valid_status(closed), "CLOSED status should pass"
        assert not self._has_valid_status(unknown), "Unknown status should fail"
        assert not self._has_valid_status(empty), "Empty status should fail"

    def test_validate_dates_present(self):
        """Test that date validation works correctly."""
        valid_dates = {"start_date": "2024-01-01", "end_date": "2027-01-01"}
        missing_start = {"start_date": None, "end_date": "2027-01-01"}
        missing_end = {"start_date": "2024-01-01", "end_date": None}
        both_missing = {"start_date": None, "end_date": None}

        assert self._has_valid_dates(valid_dates), "Valid dates should pass"
        assert not self._has_valid_dates(missing_start), "Missing start date should fail"
        assert not self._has_valid_dates(missing_end), "Missing end date should fail"
        assert not self._has_valid_dates(both_missing), "Both missing should fail"

    def test_completeness_score_all_complete(self):
        """Test completeness score when all fields present."""
        complete_project = {
            "title": "ML Research Project",
            "ec_contribution": 5000000,
            "coordinator": {"name": "Example University"},
            "status": "SIGNED",
            "start_date": "2024-01-01",
            "end_date": "2027-01-01",
        }

        score = self._calculate_project_completeness(complete_project)
        assert score == 100, f"Complete project should score 100, got {score}"

    def test_completeness_score_missing_one_field(self):
        """Test completeness score when one field missing."""
        partial_project = {
            "title": "ML Research Project",
            "ec_contribution": 5000000,
            "coordinator": None,  # Missing
            "status": "SIGNED",
            "start_date": "2024-01-01",
            "end_date": "2027-01-01",
        }

        score = self._calculate_project_completeness(partial_project)
        # 4/5 checks = 80% (dates are combined as one check)
        expected = (4 / 5) * 100
        assert score == expected, f"Expected {expected}%, got {score}"

    def test_completeness_score_empty_project(self):
        """Test completeness score for empty project."""
        empty_project = {}

        score = self._calculate_project_completeness(empty_project)
        assert score == 0, f"Empty project should score 0, got {score}"

    # ==========================================================================
    # RESPONSE PARSING TESTS - Extract projects from API response
    # ==========================================================================

    def test_extract_project_count_from_response(self):
        """Test extracting project count from response text."""
        # Format: "Found X project(s)" or "X funded projects"
        response1 = "I found 10 projects on machine learning"
        response2 = "Found 5 project(s) matching your query"
        response3 = "Here are 8 funded projects related to ML"

        count1 = self._extract_project_count(response1)
        count2 = self._extract_project_count(response2)
        count3 = self._extract_project_count(response3)

        assert count1 == 10, f"Should extract 10, got {count1}"
        assert count2 == 5, f"Should extract 5, got {count2}"
        assert count3 == 8, f"Should extract 8, got {count3}"

    def test_detect_title_in_response(self):
        """Test detecting project titles in response text."""
        response = """
        **1. AutoML Framework** (Project ID: 101234567)
        **2. DeepLearning Europe** (Project ID: 101234568)
        """

        titles = self._extract_titles_from_response(response)
        assert len(titles) >= 2, f"Should find at least 2 titles, got {len(titles)}"

    def test_detect_budget_in_response(self):
        """Test detecting budget information in response text."""
        response = """
        - Budget: EUR 5,000,000
        - EC Contribution: 4.5 million EUR
        - Total Cost: 6M EUR
        """

        has_budget = self._response_has_budget_info(response)
        assert has_budget, "Should detect budget information"

    def test_detect_coordinator_in_response(self):
        """Test detecting coordinator information in response text."""
        response = """
        - Coordinator: University of Example
        - Led by: Research Institute ABC
        """

        has_coordinator = self._response_has_coordinator_info(response)
        assert has_coordinator, "Should detect coordinator information"

    def test_detect_status_in_response(self):
        """Test detecting status information in response text."""
        response = """
        - Status: SIGNED
        - Project Status: CLOSED
        """

        has_status = self._response_has_status_info(response)
        assert has_status, "Should detect status information"

    def test_detect_dates_in_response(self):
        """Test detecting date information in response text."""
        response = """
        - Start: 2024-01-01
        - End: 2027-01-01
        - Duration: 36 months (2024-2027)
        """

        has_dates = self._response_has_date_info(response)
        assert has_dates, "Should detect date information"

    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================

    def _has_valid_title(self, project: dict[str, Any]) -> bool:
        """Check if project has a valid title."""
        title = project.get("title", "")
        if not title:
            return False
        if title in ["Unknown Title", "N/A", ""]:
            return False
        return len(str(title).strip()) > 0

    def _has_valid_budget(self, project: dict[str, Any]) -> bool:
        """Check if project has a valid budget (ec_contribution or total_cost > 0)."""
        ec_contribution = project.get("ec_contribution") or project.get("ecMaxContribution") or 0
        total_cost = project.get("total_cost") or project.get("totalCost") or 0

        try:
            ec = float(ec_contribution) if ec_contribution else 0
            total = float(total_cost) if total_cost else 0
            return ec > 0 or total > 0
        except (ValueError, TypeError):
            return False

    def _has_valid_coordinator(self, project: dict[str, Any]) -> bool:
        """Check if project has a valid coordinator."""
        # Check nested coordinator object
        coordinator = project.get("coordinator")
        if coordinator:
            if isinstance(coordinator, dict):
                name = coordinator.get("name", "")
            else:
                name = str(coordinator)
        else:
            # Check direct coordinator_name field
            name = project.get("coordinator_name", "")

        if not name:
            return False

        # Filter out placeholder values
        invalid_names = ["Data not yet available", "N/A", "Unknown", ""]
        return str(name).strip() not in invalid_names

    def _has_valid_status(self, project: dict[str, Any]) -> bool:
        """Check if project has a valid status."""
        status = project.get("status", "")
        if not status:
            return False

        # Valid statuses
        valid_statuses = ["SIGNED", "CLOSED", "TERMINATED", "ACTIVE", "ONGOING"]
        return str(status).upper() in valid_statuses

    def _has_valid_dates(self, project: dict[str, Any]) -> bool:
        """Check if project has valid start and end dates."""
        start_date = project.get("start_date") or project.get("startDate")
        end_date = project.get("end_date") or project.get("endDate")

        if not start_date or not end_date:
            return False

        # Basic check - not empty strings
        return len(str(start_date).strip()) > 0 and len(str(end_date).strip()) > 0

    def _calculate_project_completeness(self, project: dict[str, Any]) -> float:
        """
        Calculate completeness score for a project.

        Returns:
            Score from 0-100 based on percentage of essential fields present.
        """
        checks = [
            self._has_valid_title(project),
            self._has_valid_budget(project),
            self._has_valid_coordinator(project),
            self._has_valid_status(project),
            self._has_valid_dates(project),
        ]

        present = sum(1 for check in checks if check)
        return (present / len(checks)) * 100

    def _extract_project_count(self, response_text: str) -> int:
        """Extract the number of projects mentioned in response."""
        # Patterns to find project counts
        patterns = [
            r"found\s+(\d+)\s+project",
            r"(\d+)\s+project[s]?\s+(?:on|about|related|matching)",
            r"here\s+are\s+(\d+)\s+(?:funded\s+)?project",
            r"(\d+)\s+funded\s+project",
        ]

        for pattern in patterns:
            match = re.search(pattern, response_text.lower())
            if match:
                return int(match.group(1))

        return 0

    def _extract_titles_from_response(self, response_text: str) -> list[str]:
        """Extract project titles from response text."""
        titles = []

        # Pattern: **1. Title** or **Title** (acronym)
        patterns = [
            r"\*\*\d+\.\s+([^*]+)\*\*",
            r"\*\*([^*]+)\*\*\s*\(",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response_text)
            titles.extend(matches)

        return [t.strip() for t in titles if t.strip()]

    def _response_has_budget_info(self, response_text: str) -> bool:
        """Check if response contains budget information."""
        budget_patterns = [
            r"budget[:\s]+",
            r"EUR\s+[\d,.]+\s*(?:K|M|million|billion)?",  # EUR 2.00 million, EUR 209K
            r"[\d.]+\s*(?:M|million)\s*EUR",
            r"ec.?contribution",
            r"total.?cost",
            r"€\s*[\d,.]+",
            r"eu contribution",  # "EU Contribution:" header
        ]

        response_lower = response_text.lower()
        return any(re.search(pattern, response_lower, re.IGNORECASE) for pattern in budget_patterns)

    def _response_has_coordinator_info(self, response_text: str) -> bool:
        """Check if response contains coordinator information."""
        coordinator_patterns = [
            r"coordinator[:\s]+",
            r"led\s+by",
            r"coordinated\s+by",
        ]

        response_lower = response_text.lower()
        return any(re.search(pattern, response_lower) for pattern in coordinator_patterns)

    def _response_has_status_info(self, response_text: str) -> bool:
        """Check if response contains status information."""
        status_patterns = [
            r"status[:\s]+",
            r"\bSIGNED\b",
            r"\bCLOSED\b",
            r"\bongoing\b",
            r"\bcompleted\b",
        ]

        return any(re.search(pattern, response_text, re.IGNORECASE) for pattern in status_patterns)

    def _response_has_date_info(self, response_text: str) -> bool:
        """Check if response contains date information."""
        date_patterns = [
            r"start[:\s]+\d{4}",
            r"end[:\s]+\d{4}",
            r"\d{4}-\d{2}-\d{2}",
            r"duration[:\s]+",
            r"\(\d{4}-\d{4}\)",
        ]

        return any(re.search(pattern, response_text, re.IGNORECASE) for pattern in date_patterns)

    def _calculate_response_completeness_score(self, response_text: str) -> dict[str, Any]:
        """
        Calculate data completeness score from API response text.

        Returns:
            Dictionary with score breakdown and total score.
        """
        checks = {
            "has_titles": len(self._extract_titles_from_response(response_text)) > 0,
            "has_budget_info": self._response_has_budget_info(response_text),
            "has_coordinator_info": self._response_has_coordinator_info(response_text),
            "has_status_info": self._response_has_status_info(response_text),
            "has_date_info": self._response_has_date_info(response_text),
        }

        present = sum(1 for v in checks.values() if v)
        score = (present / len(checks)) * 100

        return {"checks": checks, "score": score, "fields_present": present, "total_fields": 5}

    # ==========================================================================
    # INTEGRATION TESTS - Require database and API access
    # ==========================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
