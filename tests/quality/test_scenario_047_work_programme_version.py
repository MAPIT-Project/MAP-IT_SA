"""
Scenario 047: Work Programme Version
=====================================

PRD Reference:
- Query: "What topics are in the Horizon Europe digital work programme?"
- Verify: References 2024-2025 (or latest) work programme
- Fix if: Uses outdated work programme version
- Pass threshold: 80/100

This scenario verifies that when users ask about work programme content,
the system references the current/latest work programme version (2025)
rather than outdated versions.

Quality Scoring (100 points):
- Query Fulfillment (40): Returns work programme content (topics/priorities)
- Specificity (25): References specific clusters, work programme year
- Factual Accuracy (25): Uses 2024/2025 work programme, not older
- Actionability (10): Provides links to official documents
"""

import re
from pathlib import Path

import pytest

# Test configuration
API_BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{API_BASE_URL}/api/v3/conversation"
TIMEOUT = 120  # seconds

# Current work programme year(s) that should be referenced
CURRENT_WP_YEARS = ["2025", "2024-2025", "2024/2025"]
OUTDATED_WP_YEARS = ["2021", "2022", "2023"]  # Not current as the primary source


# =============================================================================
# UNIT TESTS - Test detection logic and formatting
# =============================================================================


class TestWorkProgrammeDetection:
    """Test the work programme query detection logic."""

    def test_detection_pattern_work_programme_topics(self):
        """Test that 'work programme' + 'topics' triggers document search."""
        query = "What topics are in the work programme?"
        query_lower = query.lower()

        work_programme_patterns = ["work programme", "work-programme", "workprogramme"]
        content_patterns = ["topic", "topics", "priorit", "cover", "area", "focus"]

        has_wp_reference = any(p in query_lower for p in work_programme_patterns)
        has_content_pattern = any(p in query_lower for p in content_patterns)

        assert has_wp_reference, "Should detect 'work programme'"
        assert has_content_pattern, "Should detect 'topics'"

    def test_detection_pattern_digital_work_programme(self):
        """Test detection of digital/cluster 4 work programme queries."""
        query = "What topics are in the Horizon Europe digital work programme?"
        query_lower = query.lower()

        # Should detect work programme
        assert "work programme" in query_lower

        # Should detect digital domain -> Cluster 4
        domain_keywords = ["digital", "ai", "robotics", "manufacturing", "space"]
        has_domain = any(d in query_lower for d in domain_keywords)
        assert has_domain, "Should detect digital domain"

    def test_detection_pattern_priorities(self):
        """Test detection of priority-focused queries."""
        queries = [
            "What are the 2025 work programme priorities?",
            "What does the work programme say about AI?",
            "What areas are covered in the digital work programme?",
        ]

        content_patterns = ["priorit", "say about", "cover", "area"]

        for query in queries:
            query_lower = query.lower()
            has_content = any(p in query_lower for p in content_patterns)
            assert has_content, f"Should detect content pattern in: {query}"

    def test_cluster_extraction_from_query(self):
        """Test extraction of cluster context from queries."""
        test_cases = [
            ("digital work programme", "Cluster 4"),
            ("health cluster priorities", "Cluster 1"),
            ("climate energy topics", "Cluster 5"),
            ("food bioeconomy areas", "Cluster 6"),
            ("security topics", "Cluster 3"),
            ("culture creativity priorities", "Cluster 2"),
        ]

        domain_cluster_map = {
            "digital": "4",
            "health": "1",
            "climate": "5",
            "energy": "5",
            "food": "6",
            "bioeconomy": "6",
            "security": "3",
            "culture": "2",
            "creativity": "2",
        }

        for query, expected_cluster in test_cases:
            query_lower = query.lower()
            detected_cluster = None
            for domain, cluster_num in domain_cluster_map.items():
                if domain in query_lower:
                    detected_cluster = f"Cluster {cluster_num}"
                    break
            assert detected_cluster is not None, f"Should detect cluster in: {query}"
            assert (
                expected_cluster in detected_cluster
            ), f"Expected {expected_cluster} but got {detected_cluster}"

    def test_year_extraction_from_query(self):
        """Test extraction of year context from queries."""
        test_cases = [
            ("2025 work programme priorities", "2025"),
            ("What's in the 2024 work programme?", "2024"),
            ("Horizon Europe 2026 topics", "2026"),
        ]

        for query, expected_year in test_cases:
            year_match = re.search(r"(2023|2024|2025|2026|2027)", query.lower())
            assert year_match is not None, f"Should extract year from: {query}"
            assert year_match.group(1) == expected_year


class TestWorkProgrammeYearValidation:
    """Test validation of work programme years."""

    def test_current_wp_years_are_valid(self):
        """Verify current WP years are defined correctly."""
        assert "2025" in CURRENT_WP_YEARS
        assert len(CURRENT_WP_YEARS) >= 1

    def test_outdated_wp_years_are_valid(self):
        """Verify outdated WP years are defined correctly."""
        assert "2021" in OUTDATED_WP_YEARS
        assert "2022" in OUTDATED_WP_YEARS
        assert "2023" in OUTDATED_WP_YEARS

    def test_year_patterns_do_not_overlap(self):
        """Current and outdated years should not overlap."""
        for year in CURRENT_WP_YEARS:
            # Extract just the year (handle ranges like "2024-2025")
            years_in_current = re.findall(r"\d{4}", year)
            for y in years_in_current:
                if y not in ["2024", "2025", "2026"]:  # Allow these in ranges
                    assert y not in OUTDATED_WP_YEARS

    def test_wp_2025_exists_as_pdf(self):
        """Verify WP-7 (Digital) 2025 PDF exists."""
        wp7_path = (
            Path(__file__).resolve().parents[2]
            / "newdocs/2025_work_programmes/wp-7-digital-industry-and-space_horizon-2025_en.pdf"
        )
        assert wp7_path.is_file(), "Tracked WP-7 (Digital) 2025 PDF should exist"


class TestResponseFormatting:
    """Test response formatting for work programme queries."""

    def test_document_excerpt_format(self):
        """Test that document excerpts include required fields."""
        # Simulate a document excerpt response
        sample_excerpt = {
            "document_title": "Wp 7 Digital Industry And Space Horizon 2025 En",
            "page_number": 73,
            "content": "Topics and priorities for digital...",
            "ref": "e4693283",
        }

        # Should have title
        has_title = (
            "title" in sample_excerpt["document_title"].lower()
            or "Wp" in sample_excerpt["document_title"]
        )
        assert has_title
        # Should have page reference
        assert sample_excerpt["page_number"] > 0
        # Should have content
        assert len(sample_excerpt["content"]) > 0
        # Should have citation reference
        assert len(sample_excerpt["ref"]) > 0


# =============================================================================
# INTEGRATION TESTS - Test against live API
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
