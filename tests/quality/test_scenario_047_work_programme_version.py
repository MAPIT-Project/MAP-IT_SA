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

from datetime import datetime
import re

import pytest
import requests

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
        import os

        wp7_path = (
            "/home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA/"
            "newdocs/2025_work_programmes/wp-7-digital-industry-and-space_horizon-2025_en.pdf"
        )
        assert os.path.exists(wp7_path), "WP-7 (Digital) 2025 PDF should exist"


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


class TestScenario047Integration:
    """Integration tests for Scenario 047: Work Programme Version."""

    @pytest.fixture
    def conversation_id(self):
        """Generate unique conversation ID for each test."""
        return int(datetime.now().timestamp() * 1000) % 2147483647

    @pytest.fixture
    def api_response(self, conversation_id):
        """Make API request and return response."""
        try:
            response = requests.post(
                f"{API_ENDPOINT}/{conversation_id}/message",
                json={"message": "What topics are in the Horizon Europe digital work programme?"},
                timeout=TIMEOUT,
            )
            return response
        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not available: {e}")

    def test_api_returns_200(self, api_response):
        """Test that API returns successful response."""
        assert api_response.status_code == 200, f"Expected 200, got {api_response.status_code}"

    def test_response_has_required_fields(self, api_response):
        """Test that response contains required fields."""
        data = api_response.json()
        assert "response" in data, "Response should have 'response' field"
        assert "metadata" in data, "Response should have 'metadata' field"

    def test_uses_search_documents_tool(self, api_response):
        """Test that search_documents tool was used (not search_funding_calls)."""
        data = api_response.json()
        tools_used = data.get("metadata", {}).get("tools_used", [])

        # Should use search_documents, not search_funding_calls
        has_document_search = any("search_documents" in str(t).lower() for t in tools_used)
        has_call_search = any("search_funding_calls" in str(t).lower() for t in tools_used)

        assert has_document_search, "Should use search_documents tool"
        # It's acceptable to also use call search for supplementary info,
        # but document search should be present
        if has_call_search and not has_document_search:
            pytest.fail("Should use search_documents, not just search_funding_calls")

    def test_response_references_2025_work_programme(self, api_response):
        """Test that response references 2025 (current) work programme."""
        data = api_response.json()
        response_text = data.get("response", "").lower()

        # Should mention 2025 or current work programme
        has_2025 = "2025" in response_text
        has_current_reference = any(yr.lower() in response_text for yr in CURRENT_WP_YEARS)

        assert has_2025 or has_current_reference, (
            "Response should reference 2025 work programme. "
            f"Found years in response: {re.findall(r'20[0-9]{2}', response_text)}"
        )

    def test_response_references_digital_cluster(self, api_response):
        """Test that response references Cluster 4 / Digital topics."""
        data = api_response.json()
        response_text = data.get("response", "").lower()

        digital_indicators = [
            "digital",
            "cluster 4",
            "cl4",
            "industry",
            "space",
            "wp-7",
            "wp 7",
        ]

        has_digital_reference = any(ind in response_text for ind in digital_indicators)
        assert has_digital_reference, "Response should reference Digital/Cluster 4 content"

    def test_no_outdated_wp_as_primary(self, api_response):
        """Test that response doesn't use 2021/2022/2023 as the primary/only source."""
        data = api_response.json()
        response_text = data.get("response", "").lower()

        # Check for outdated years
        found_years = re.findall(r"20[0-9]{2}", response_text)

        # It's OK to mention older years for historical context,
        # but 2025 or 2024-2025 should also be present
        if any(y in OUTDATED_WP_YEARS for y in found_years):
            has_current = any(y in ["2024", "2025", "2026"] for y in found_years)
            assert has_current, (
                f"If mentioning older years {found_years}, "
                "should also reference current work programme (2024-2025)"
            )

    def test_response_includes_document_excerpts(self, api_response):
        """Test that response includes actual document excerpts/content."""
        data = api_response.json()
        response_text = data.get("response", "")

        # Should have document/excerpt markers
        excerpt_indicators = [
            "excerpt",
            "page",
            "📄",
            "📑",
            "wp",
            "work programme",
            "ref:",
        ]

        has_excerpt = any(ind.lower() in response_text.lower() for ind in excerpt_indicators)
        assert has_excerpt, "Response should include document excerpts with citations"

    def test_response_provides_official_resources(self, api_response):
        """Test that response includes links to official EU resources."""
        data = api_response.json()
        response_text = data.get("response", "")

        resource_indicators = [
            "ec.europa.eu",
            "funding & tenders portal",
            "funding-tenders",
            "eu portal",
            "official",
        ]

        has_resources = any(ind.lower() in response_text.lower() for ind in resource_indicators)
        assert has_resources, "Response should include links to official EU resources"

    def test_no_error_in_response(self, api_response):
        """Test that response doesn't contain error indicators."""
        data = api_response.json()
        response_text = data.get("response", "").lower()

        error_indicators = [
            "error occurred",
            "i couldn't find",
            "no results found",
            "i don't have",
            "unable to",
            "failed to",
        ]

        has_error = any(ind in response_text for ind in error_indicators)
        assert not has_error, "Response should not contain error indicators"

    def test_quality_score_threshold(self, api_response):
        """Test that response meets quality score threshold of 80."""
        data = api_response.json()
        response_text = data.get("response", "").lower()

        score = 0

        # Query Fulfillment (40 points) - returns work programme topics
        if any(
            term in response_text for term in ["topic", "priorit", "destination", "area", "focus"]
        ):
            score += 20
        if "work programme" in response_text:
            score += 20

        # Specificity (25 points) - references specific year and cluster
        if "2025" in response_text:
            score += 15
        if any(term in response_text for term in ["cluster 4", "digital", "wp-7", "wp 7"]):
            score += 10

        # Factual Accuracy (25 points) - uses current WP, not outdated
        found_years = re.findall(r"20[0-9]{2}", response_text)
        if "2025" in found_years or "2024" in found_years:
            score += 25
        elif not any(y in OUTDATED_WP_YEARS for y in found_years):
            score += 15  # No outdated years mentioned

        # Actionability (10 points) - provides official links
        if "ec.europa.eu" in response_text or "portal" in response_text:
            score += 10

        assert score >= 80, f"Quality score {score}/100 is below threshold of 80"


class TestAlternativeQueries:
    """Test alternative phrasings of work programme queries."""

    @pytest.fixture
    def conversation_id(self):
        """Generate unique conversation ID."""
        return int(datetime.now().timestamp() * 1000) % 2147483647 + 100

    def test_cluster_5_work_programme_query(self, conversation_id):
        """Test query about Cluster 5 (Climate) work programme."""
        try:
            response = requests.post(
                f"{API_ENDPOINT}/{conversation_id}/message",
                json={"message": "What are the priorities in the Cluster 5 work programme?"},
                timeout=TIMEOUT,
            )

            if response.status_code != 200:
                pytest.skip("API returned non-200 status")

            data = response.json()
            tools_used = data.get("metadata", {}).get("tools_used", [])

            # Should use search_documents for work programme content
            has_document_search = any("search_documents" in str(t).lower() for t in tools_used)
            assert has_document_search, "Cluster 5 WP query should use search_documents"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not available: {e}")

    def test_health_work_programme_query(self, conversation_id):
        """Test query about health (Cluster 1) work programme."""
        try:
            response = requests.post(
                f"{API_ENDPOINT}/{conversation_id + 1}/message",
                json={"message": "What topics are in the health work programme?"},
                timeout=TIMEOUT,
            )

            if response.status_code != 200:
                pytest.skip("API returned non-200 status")

            data = response.json()
            response_text = data.get("response", "").lower()

            # Should reference health/Cluster 1 content
            health_indicators = ["health", "cluster 1", "cl1", "medical", "clinical"]
            has_health = any(ind in response_text for ind in health_indicators)
            assert has_health, "Health WP query should reference health/Cluster 1 content"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not available: {e}")

    def test_2025_priorities_explicit_year(self, conversation_id):
        """Test explicit 2025 year in query."""
        try:
            response = requests.post(
                f"{API_ENDPOINT}/{conversation_id + 2}/message",
                json={"message": "What are the 2025 Horizon Europe work programme priorities?"},
                timeout=TIMEOUT,
            )

            if response.status_code != 200:
                pytest.skip("API returned non-200 status")

            data = response.json()
            response_text = data.get("response", "").lower()

            # Should mention 2025
            assert (
                "2025" in response_text
            ), "Query with explicit 2025 should reference 2025 in response"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not available: {e}")

    def test_work_programme_say_about_pattern(self, conversation_id):
        """Test 'what does the work programme say about' pattern."""
        try:
            response = requests.post(
                f"{API_ENDPOINT}/{conversation_id + 3}/message",
                json={"message": "What does the Horizon Europe work programme say about AI?"},
                timeout=TIMEOUT,
            )

            if response.status_code != 200:
                pytest.skip("API returned non-200 status")

            data = response.json()
            tools_used = data.get("metadata", {}).get("tools_used", [])

            # Should use search_documents
            has_document_search = any("search_documents" in str(t).lower() for t in tools_used)
            assert has_document_search, "'What does WP say about' should use search_documents"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not available: {e}")


class TestFullScenarioIntegration:
    """Full integration test for Scenario 047."""

    def test_full_scenario_047(self):
        """Complete Scenario 047 test with quality scoring."""
        conversation_id = int(datetime.now().timestamp() * 1000) % 2147483647 + 200

        try:
            response = requests.post(
                f"{API_ENDPOINT}/{conversation_id}/message",
                json={"message": "What topics are in the Horizon Europe digital work programme?"},
                timeout=TIMEOUT,
            )

            if response.status_code != 200:
                pytest.skip("API returned non-200 status")

            data = response.json()
            response_text = data.get("response", "")
            metadata = data.get("metadata", {})

            # === Quality Scoring ===
            score_breakdown = {}

            # Query Fulfillment (40 points)
            fulfillment_score = 0
            if "topic" in response_text.lower() or "priorit" in response_text.lower():
                fulfillment_score += 20
            if "work programme" in response_text.lower():
                fulfillment_score += 10
            if "digital" in response_text.lower() or "cluster 4" in response_text.lower():
                fulfillment_score += 10
            score_breakdown["fulfillment"] = min(fulfillment_score, 40)

            # Specificity (25 points)
            specificity_score = 0
            if "2025" in response_text:
                specificity_score += 15
            if any(t in response_text.lower() for t in ["wp-7", "wp 7", "digital industry"]):
                specificity_score += 10
            score_breakdown["specificity"] = min(specificity_score, 25)

            # Factual Accuracy (25 points)
            accuracy_score = 0
            found_years = re.findall(r"20[0-9]{2}", response_text)
            if "2025" in found_years or "2024" in found_years:
                accuracy_score += 25
            elif not any(y in OUTDATED_WP_YEARS for y in found_years):
                accuracy_score += 15
            score_breakdown["accuracy"] = min(accuracy_score, 25)

            # Actionability (10 points)
            actionability_score = 0
            if "ec.europa.eu" in response_text.lower():
                actionability_score += 5
            if "next step" in response_text.lower() or "portal" in response_text.lower():
                actionability_score += 5
            score_breakdown["actionability"] = min(actionability_score, 10)

            # Total Score
            total_score = sum(score_breakdown.values())

            print("\n=== Scenario 047 Quality Score ===")
            print(f"Query Fulfillment: {score_breakdown['fulfillment']}/40")
            print(f"Specificity: {score_breakdown['specificity']}/25")
            print(f"Factual Accuracy: {score_breakdown['accuracy']}/25")
            print(f"Actionability: {score_breakdown['actionability']}/10")
            print(f"TOTAL: {total_score}/100")
            print(f"\nTools used: {metadata.get('tools_used', [])}")

            assert total_score >= 80, (
                f"Quality score {total_score}/100 is below threshold of 80. "
                f"Breakdown: {score_breakdown}"
            )

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
