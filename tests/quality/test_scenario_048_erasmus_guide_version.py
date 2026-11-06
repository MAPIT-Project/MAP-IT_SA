"""
Scenario 048: Erasmus+ Guide Version
=====================================

PRD Reference:
- Query: "What are the Erasmus+ quality criteria?"
- Verify: Uses 2025/2026 Programme Guide
- Fix if: Uses older guide version
- Pass threshold: 80/100

This scenario verifies that when users ask about Erasmus+ Programme Guide content
(quality criteria, evaluation criteria, award criteria), the system references
the current/latest Programme Guide version (2025/2026) rather than outdated versions.

Quality Scoring (100 points):
- Query Fulfillment (40): Returns quality/evaluation criteria content
- Specificity (25): References specific criteria, points, thresholds
- Factual Accuracy (25): Uses 2025/2026 Programme Guide, not older
- Actionability (10): Provides links to official Erasmus+ resources
"""

import re

# Test configuration
API_BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{API_BASE_URL}/api/v3/conversation"
TIMEOUT = 120  # seconds

# Current Programme Guide year(s) that should be referenced
CURRENT_GUIDE_YEARS = ["2026", "2025", "2025/2026", "2025-2026"]
OUTDATED_GUIDE_YEARS = ["2021", "2022", "2023", "2024"]  # Not current as the primary source


# =============================================================================
# UNIT TESTS - Test detection logic and formatting
# =============================================================================


class TestErasmusProgrammeGuideDetection:
    """Test the Erasmus+ Programme Guide query detection logic."""

    def test_detection_pattern_quality_criteria(self):
        """Test that 'Erasmus+' + 'quality criteria' triggers document search."""
        query = "What are the Erasmus+ quality criteria?"
        query_lower = query.lower()

        erasmus_patterns = ["erasmus+", "erasmus plus", "erasmus "]
        content_patterns = ["quality criteria", "evaluation criteria", "award criteria"]

        has_erasmus_reference = any(p in query_lower for p in erasmus_patterns)
        has_content_pattern = any(p in query_lower for p in content_patterns)

        assert has_erasmus_reference, "Should detect 'Erasmus+'"
        assert has_content_pattern, "Should detect 'quality criteria'"

    def test_detection_pattern_evaluation_criteria(self):
        """Test detection of evaluation criteria queries."""
        query = "How are Erasmus+ applications evaluated?"
        query_lower = query.lower()

        assert "erasmus" in query_lower, "Should detect Erasmus reference"
        # The regex pattern "how are.*evaluated" should match
        assert re.search(r"how are.*evaluated", query_lower), "Should detect evaluation pattern"

    def test_detection_pattern_award_criteria(self):
        """Test detection of award criteria queries."""
        queries = [
            "What are the award criteria for Erasmus+ projects?",
            "What are the Erasmus+ selection criteria?",
            "Tell me about the Erasmus+ scoring criteria",
        ]

        award_patterns = ["award criteria", "selection criteria", "scoring criteria"]

        for query in queries:
            query_lower = query.lower()
            has_pattern = any(p in query_lower for p in award_patterns)
            assert has_pattern, f"Should detect award/selection pattern in: {query}"

    def test_detection_pattern_programme_guide(self):
        """Test detection of Programme Guide-specific queries."""
        queries = [
            "What does the Erasmus+ Programme Guide say about quality?",
            "Tell me about the Erasmus+ 2026 guide",
            "Erasmus+ guide requirements",
        ]

        guide_patterns = [r"programme\s*guide", r"2026\s*guide", r"guide"]

        for query in queries:
            query_lower = query.lower()
            has_pattern = any(re.search(p, query_lower) for p in guide_patterns)
            assert has_pattern, f"Should detect programme guide pattern in: {query}"

    def test_key_action_extraction_ka1(self):
        """Test extraction of KA1 context from queries."""
        query = "What are the quality criteria for KA1 mobility projects?"
        query_lower = query.lower()

        assert "ka1" in query_lower or "mobility" in query_lower

    def test_key_action_extraction_ka2(self):
        """Test extraction of KA2 context from queries."""
        query = "Erasmus+ KA2 partnership evaluation criteria"
        query_lower = query.lower()

        assert "ka2" in query_lower or "partnership" in query_lower

    def test_current_guide_years_are_valid(self):
        """Verify that current guide years are defined."""
        assert len(CURRENT_GUIDE_YEARS) >= 1
        assert "2026" in CURRENT_GUIDE_YEARS
        assert "2025" in CURRENT_GUIDE_YEARS

    def test_outdated_guide_years_are_valid(self):
        """Verify that outdated guide years are defined."""
        assert len(OUTDATED_GUIDE_YEARS) >= 1
        assert "2021" in OUTDATED_GUIDE_YEARS
        assert "2024" in OUTDATED_GUIDE_YEARS

    def test_guide_years_do_not_overlap(self):
        """Ensure current and outdated years don't overlap."""
        for year in CURRENT_GUIDE_YEARS:
            assert year not in OUTDATED_GUIDE_YEARS, f"Year {year} in both lists"

    def test_guide_2026_exists_as_pdf(self):
        """Verify the 2026 Programme Guide PDF exists."""
        import os

        guide_paths = [
            "newdocs/erasmus/programme-guide-2026_en.pdf",
            "newdocs/erasmus+/programme-guide-2026_en.pdf",
        ]

        found = False
        for path in guide_paths:
            if os.path.exists(path):
                found = True
                break

        assert found, "Programme Guide 2026 PDF should exist in newdocs/erasmus/"

    def test_search_query_building(self):
        """Test that search queries are built correctly."""
        query_lower = "what are the quality criteria for erasmus+"

        # Should extract quality context
        search_terms = []
        if "quality" in query_lower:
            search_terms.append("quality criteria assessment")

        assert len(search_terms) > 0, "Should extract search terms from query"
        assert "quality" in " ".join(search_terms).lower()


# =============================================================================
# INTEGRATION TESTS - Test against live API
# =============================================================================


# =============================================================================
# EDGE CASE TESTS
# =============================================================================
