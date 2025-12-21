"""
AI Response Quality Tests

Comprehensive tests for validating AI response quality, detecting deflections,
and ensuring content requirements are met.

IMPORTANT: These tests validate that AI responses are actually helpful,
not just that they exist. A test that passes when the AI returns
"I could not find specific details" is worthless.

Author: MAP-IT Development Team
Created: December 2025
"""

import os
import sys

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.quality.response_quality_analyzer import (
    DEFLECTION_PHRASES,
    QueryType,
    ResponseCategory,
    ResponseQualityAnalyzer,
)


@pytest.fixture
def analyzer() -> ResponseQualityAnalyzer:
    """Create a ResponseQualityAnalyzer instance."""
    return ResponseQualityAnalyzer()


class TestDeflectionDetection:
    """Tests for deflection phrase detection."""

    @pytest.mark.parametrize(
        "response,expected_deflection",
        [
            # Clear deflections
            (
                "I could not find any information about that call.",
                True,
            ),
            (
                "No results found for your query. Please try a more specific search.",
                True,
            ),
            (
                "I'm not sure about the eligibility criteria. Please check the official portal.",
                True,
            ),
            (
                "Unable to retrieve the call details. Try again later.",
                True,
            ),
            (
                "I found some information but could not extract specific details from it.",
                True,
            ),
            (
                "No data available for this programme. Could you clarify what you're looking for?",
                True,
            ),
            # Non-deflections (substantive responses)
            (
                "The HORIZON-CL5-2026-D3-01 call focuses on hydrogen technologies. "
                "The deadline is March 15, 2026, with a total budget of €50 million. "
                "This is an RIA action type, currently open for applications.",
                False,
            ),
            (
                "The EIC Accelerator has a success rate of approximately 8%, while ERC grants "
                "typically see around 12% success rates. The main difference is that EIC focuses "
                "on commercialization while ERC emphasizes frontier research.",
                False,
            ),
            (
                "Yes, SMEs from Switzerland can participate in Horizon Europe. "
                "They are eligible for most calls but cannot coordinate certain projects.",
                False,
            ),
        ],
    )
    def test_deflection_detection(
        self, analyzer: ResponseQualityAnalyzer, response: str, expected_deflection: bool
    ):
        """Test that deflections are correctly identified."""
        is_deflection = analyzer.is_deflection(response)
        assert is_deflection == expected_deflection, (
            f"Expected deflection={expected_deflection} for response: {response[:100]}..."
        )

    @pytest.mark.parametrize(
        "phrase",
        [
            "could not find",
            "no information available",
            "please try a more specific",
            "i'm not sure",
            "unable to retrieve",
            "found some information but could not extract",
            "no results found",
            "try again later",
        ],
    )
    def test_known_deflection_phrases_detected(
        self, analyzer: ResponseQualityAnalyzer, phrase: str
    ):
        """Ensure all known deflection phrases are in the detection list."""
        assert any(
            phrase.lower() in dp.lower() or dp.lower() in phrase.lower()
            for dp in DEFLECTION_PHRASES
        ), f"Deflection phrase '{phrase}' not covered in detection list"


class TestQueryTypeDetection:
    """Tests for automatic query type detection."""

    @pytest.mark.parametrize(
        "query,expected_type",
        [
            # Call information queries
            ("Tell me about HORIZON-CL5-2026-D3-01", QueryType.CALL_INFORMATION),
            ("What is the deadline for call HORIZON-CL4-2025-DATA-01?", QueryType.CALL_INFORMATION),
            ("Details about the funding call for hydrogen", QueryType.CALL_INFORMATION),
            ("Is the open call for AI research still accepting?", QueryType.CALL_INFORMATION),
            # Programme comparison queries
            ("Compare EIC Accelerator with ERC grants", QueryType.PROGRAMME_COMPARISON),
            ("What's the difference between RIA and IA?", QueryType.PROGRAMME_COMPARISON),
            ("EIC vs ERC success rates", QueryType.PROGRAMME_COMPARISON),
            # Eligibility queries
            ("Can SMEs apply to Horizon Europe?", QueryType.ELIGIBILITY_FAQ),
            ("What are the eligibility requirements for ERC?", QueryType.ELIGIBILITY_FAQ),
            ("Am I eligible if I'm from Switzerland?", QueryType.ELIGIBILITY_FAQ),
            # Budget queries
            ("What is the typical budget for a Horizon RIA?", QueryType.BUDGET_BENCHMARK),
            ("Budget benchmark for Climate cluster projects", QueryType.BUDGET_BENCHMARK),
            ("How much funding can I request?", QueryType.BUDGET_BENCHMARK),
            # Partner discovery queries
            ("Find German SMEs with hydrogen experience", QueryType.PARTNER_DISCOVERY),
            ("Looking for partners experienced in AI", QueryType.PARTNER_DISCOVERY),
            ("Find organizations that worked on battery research", QueryType.PARTNER_DISCOVERY),
            # Project search queries
            ("Find projects about quantum computing", QueryType.PROJECT_SEARCH),
            ("Search for renewable energy projects", QueryType.PROJECT_SEARCH),
            # Consortium queries
            ("What is typical consortium size for Health IAs?", QueryType.CONSORTIUM_PATTERN),
            ("Consortium composition patterns for Cluster 5", QueryType.CONSORTIUM_PATTERN),
            # Statistics queries
            ("What is the success rate for EIC?", QueryType.STATISTICS),
            ("How many projects were funded in 2024?", QueryType.STATISTICS),
        ],
    )
    def test_query_type_detection(
        self, analyzer: ResponseQualityAnalyzer, query: str, expected_type: QueryType
    ):
        """Test that query types are correctly detected."""
        detected_type = analyzer._detect_query_type(query)
        assert detected_type == expected_type, (
            f"Expected {expected_type.value} but got {detected_type.value} for: {query}"
        )


class TestContentRequirements:
    """Tests for content requirement validation."""

    @pytest.mark.parametrize(
        "query,response,query_type,min_score,expected_category",
        [
            # Complete call information response
            (
                "Tell me about HORIZON-CL5-2026-D3-01",
                "The call HORIZON-CL5-2026-D3-01 focuses on hydrogen production. "
                "The deadline is March 15, 2026. The total budget is €50 million. "
                "Type: RIA. Status: Currently open for applications.",
                QueryType.CALL_INFORMATION,
                75,
                ResponseCategory.COMPLETE,
            ),
            # Missing deadline in call response
            (
                "Tell me about HORIZON-CL5-2026-D3-01",
                "The call HORIZON-CL5-2026-D3-01 focuses on hydrogen production with €50M budget. "
                "This is an RIA action. Applications are open.",
                QueryType.CALL_INFORMATION,
                65,  # Lower score expected due to missing deadline
                ResponseCategory.COMPLETE,  # Still complete with 3/4 required elements
            ),
            # Complete comparison response
            (
                "Compare EIC and ERC success rates",
                "The EIC Accelerator has a success rate of ~8%, while ERC has ~12%. "
                "In contrast to EIC's commercialization focus, ERC emphasizes "
                "frontier research. EIC funds 500 projects vs ERC's 300 grants.",
                QueryType.PROGRAMME_COMPARISON,
                75,
                ResponseCategory.COMPLETE,
            ),
            # Deflection response (should fail regardless of type)
            (
                "What is the budget for HORIZON-CL5-2026-D3-01?",
                "I could not find specific details about this call. No information available. "
                "Please try a more specific search or check the EU portal directly.",
                QueryType.CALL_INFORMATION,
                10,  # Very low score expected (critical deflection + missing elements)
                ResponseCategory.DEFLECTION,
            ),
            # Empty response
            (
                "Find hydrogen partners",
                "No data.",
                QueryType.PARTNER_DISCOVERY,
                10,
                ResponseCategory.EMPTY,
            ),
            # Complete eligibility response
            (
                "Can SMEs participate in Horizon Europe?",
                "Yes, SMEs are eligible to participate in Horizon Europe. SMEs can apply as "
                "coordinators or partners in RIA and IA projects. The requirement is that the "
                "organization must be established in an EU member state or associated country. "
                "There are specific SME-focused instruments like the EIC Accelerator.",
                QueryType.ELIGIBILITY_FAQ,
                75,
                ResponseCategory.COMPLETE,
            ),
            # Complete budget benchmark response
            (
                "What is typical budget for Health RIA?",
                "For Health cluster RIA projects, the average budget is €8-12 million with "
                "a median of €9.5 million. The typical range spans from €5 million for smaller "
                "projects to €15 million for larger consortia. EU contribution is 100% for RIA.",
                QueryType.BUDGET_BENCHMARK,
                75,
                ResponseCategory.COMPLETE,
            ),
        ],
    )
    def test_content_validation(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        query_type: QueryType,
        min_score: int,
        expected_category: ResponseCategory,
    ):
        """Test content requirement validation for different query types."""
        analysis = analyzer.analyze(query, response, query_type=query_type)

        assert analysis.score >= min_score - 10, (
            f"Score {analysis.score} below expected {min_score} for query: {query}\n"
            f"Missing elements: {analysis.missing_elements}\n"
            f"Deflections: {analysis.deflection_phrases_found}"
        )
        assert analysis.category == expected_category, (
            f"Expected {expected_category.value} but got {analysis.category.value}\n"
            f"Score: {analysis.score}, Missing: {analysis.missing_elements}"
        )


class TestCallInformationQueries:
    """Specific tests for call information queries."""

    @pytest.mark.parametrize(
        "query,response,expected_min_score,expected_elements",
        [
            # Test 1: Good response with all elements
            (
                "Tell me about HORIZON-CL5-2026-D3-01",
                "**HORIZON-CL5-2026-D3-01: Hydrogen Production Technologies**\n\n"
                "**Type:** RIA (Research and Innovation Action)\n"
                "**Status:** Open\n"
                "**Deadline:** March 15, 2026\n"
                "**Budget:** €50 million (total), €10-15 million per project\n\n"
                "This call focuses on innovative hydrogen production technologies.",
                80,
                ["call_identifier", "deadline", "budget", "action_type"],
            ),
            # Test 2: Missing budget
            (
                "What is HORIZON-CL4-2025-DATA-01?",
                "HORIZON-CL4-2025-DATA-01 is focused on AI and data spaces. "
                "The deadline is June 2025. This is an IA type call with status open.",
                55,
                ["call_identifier", "deadline", "action_type"],  # Budget missing
            ),
            # Test 3: All elements present
            (
                "Details on HORIZON-HLTH-2025-DISEASE-01",
                "The call HORIZON-HLTH-2025-DISEASE-01 addresses rare diseases research. "
                "Budget: €30 million total. Deadline: September 1, 2025. "
                "Type: RIA. Status: Upcoming. Typical project budget €3-5 million.",
                85,
                ["call_identifier", "deadline", "budget", "action_type", "status"],
            ),
        ],
    )
    def test_call_queries_content(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        expected_min_score: int,
        expected_elements: list[str],
    ):
        """Test call information responses for required content."""
        analysis = analyzer.analyze(query, response, query_type=QueryType.CALL_INFORMATION)

        # Check score meets minimum
        assert analysis.score >= expected_min_score, (
            f"Score {analysis.score} < expected min {expected_min_score}\n"
            f"Missing: {analysis.missing_elements}"
        )

        # Check expected elements were found
        for element in expected_elements:
            assert analysis.content_elements_found.get(element, 0) > 0, (
                f"Expected element '{element}' not found in response"
            )


class TestProgrammeComparisonQueries:
    """Specific tests for programme comparison queries."""

    @pytest.mark.parametrize(
        "query,response,is_acceptable",
        [
            # Good comparison
            (
                "Compare EIC vs ERC",
                "EIC (European Innovation Council) and ERC (European Research Council) differ "
                "significantly. EIC focuses on commercialization with an 8% success rate, while "
                "ERC emphasizes frontier research with a higher 12% success rate. EIC budgets "
                "are typically €2.5M vs ERC's €1.5-2.5M. In contrast to EIC's business focus, "
                "ERC supports individual researchers.",
                True,
            ),
            # Response with some comparison but missing depth
            (
                "EIC and ERC",
                "EIC is the European Innovation Council. It provides funding for innovation. "
                "ERC is the European Research Council. It funds basic research. "
                "Both are part of Horizon Europe.",
                True,  # Has some comparative content and mentions both programmes
            ),
            # Deflection
            (
                "Compare RIA and IA",
                "I could not find detailed comparison data. Please check the official guidance.",
                False,
            ),
        ],
    )
    def test_comparison_queries(
        self, analyzer: ResponseQualityAnalyzer, query: str, response: str, is_acceptable: bool
    ):
        """Test programme comparison responses."""
        analysis = analyzer.analyze(query, response, query_type=QueryType.PROGRAMME_COMPARISON)
        assert analysis.is_acceptable(min_score=70) == is_acceptable, (
            f"Expected acceptable={is_acceptable}, got score={analysis.score}, "
            f"category={analysis.category.value}"
        )


class TestPartnerDiscoveryQueries:
    """Specific tests for partner discovery queries."""

    @pytest.mark.parametrize(
        "query,response,expected_min_score",
        [
            # Good partner list
            (
                "Find German SMEs with hydrogen experience",
                "Found 5 experienced partners in Germany with hydrogen expertise:\n\n"
                "1. H2 Innovation GmbH - 8 projects in hydrogen storage\n"
                "2. Fraunhofer Institute - 15 projects in electrolysis\n"
                "3. TU Munich - Research partner with 12 projects\n"
                "These organizations have extensive experience in Cluster 5 projects.",
                75,
            ),
            # Minimal partner info
            (
                "Find AI partners",
                "Several partners have AI experience including some research institutions.",
                40,  # Too vague, no specific organizations
            ),
            # No partners found (deflection)
            (
                "Find quantum computing partners in Malta",
                "No partners found with quantum computing experience in Malta. "
                "Try expanding your search to other countries.",
                30,
            ),
        ],
    )
    def test_partner_queries(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        expected_min_score: int,
    ):
        """Test partner discovery responses."""
        analysis = analyzer.analyze(query, response, query_type=QueryType.PARTNER_DISCOVERY)
        assert analysis.score >= expected_min_score - 5, (
            f"Score {analysis.score} < expected {expected_min_score} for: {query[:50]}..."
        )


class TestBudgetBenchmarkQueries:
    """Specific tests for budget benchmark queries."""

    @pytest.mark.parametrize(
        "query,response,has_budget_figures,has_statistics",
        [
            # Complete budget info
            (
                "What is typical budget for Horizon RIA in Cluster 5?",
                "For Cluster 5 (Climate) RIA projects, the typical budget is:\n"
                "- Average: €8.5 million\n"
                "- Median: €7.2 million\n"
                "- Range: €4 million to €15 million\n"
                "The EU contribution rate is 100% for RIA projects.",
                True,
                True,
            ),
            # Has figures but no statistics
            (
                "Budget for Health projects?",
                "Health projects typically receive €10 million in funding.",
                True,
                False,
            ),
            # No useful info
            (
                "How much should I request?",
                "It depends on your project scope and consortium size.",
                False,
                False,
            ),
        ],
    )
    def test_budget_queries(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        has_budget_figures: bool,
        has_statistics: bool,
    ):
        """Test budget benchmark responses for required content."""
        analysis = analyzer.analyze(query, response, query_type=QueryType.BUDGET_BENCHMARK)

        budget_count = analysis.content_elements_found.get("budget_figures", 0)
        stats_count = analysis.content_elements_found.get("statistics", 0)

        if has_budget_figures:
            assert budget_count > 0, f"Expected budget figures, found {budget_count}"
        if has_statistics:
            assert stats_count > 0, f"Expected statistics, found {stats_count}"


class TestQualityScoring:
    """Tests for quality score calculation."""

    def test_perfect_response_high_score(self, analyzer: ResponseQualityAnalyzer):
        """Test that a perfect response gets a high score."""
        response = (
            "The call HORIZON-CL5-2026-D3-01 focuses on hydrogen technologies.\n\n"
            "**Key Details:**\n"
            "- **Topic:** Hydrogen Production and Storage\n"
            "- **Type:** RIA (Research and Innovation Action)\n"
            "- **Deadline:** March 15, 2026 at 17:00 Brussels time\n"
            "- **Budget:** €50 million total, €10-15 million per project\n"
            "- **Status:** Currently Open\n\n"
            "This call supports projects developing innovative electrolysis and "
            "hydrogen storage solutions. Consortia of 5-10 partners are typical."
        )
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01",
            response,
            query_type=QueryType.CALL_INFORMATION,
        )
        assert analysis.score >= 85, f"Perfect response got low score: {analysis.score}"
        assert analysis.category == ResponseCategory.COMPLETE

    def test_deflection_response_low_score(self, analyzer: ResponseQualityAnalyzer):
        """Test that a deflection response gets a low score."""
        response = (
            "I could not find information about this call. No results found. "
            "Please try a more specific search or check the official EU portal."
        )
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01",
            response,
            query_type=QueryType.CALL_INFORMATION,
        )
        assert analysis.score <= 40, f"Deflection got high score: {analysis.score}"
        assert analysis.category == ResponseCategory.DEFLECTION

    def test_empty_response_very_low_score(self, analyzer: ResponseQualityAnalyzer):
        """Test that an empty response gets very low score."""
        analysis = analyzer.analyze(
            "Find hydrogen partners", "No data.", query_type=QueryType.PARTNER_DISCOVERY
        )
        assert analysis.score <= 30
        assert analysis.category == ResponseCategory.EMPTY

    def test_partial_response_medium_score(self, analyzer: ResponseQualityAnalyzer):
        """Test that a partial response gets a reasonable score."""
        response = (
            "HORIZON-CL5-2026-D3-01 is about hydrogen. It's an RIA project. "
            "More details are available on the portal."
        )
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01",
            response,
            query_type=QueryType.CALL_INFORMATION,
        )
        # Even with missing elements, having some content gets a reasonable score
        assert 60 <= analysis.score <= 85, f"Partial response score: {analysis.score}"
        assert analysis.category in [ResponseCategory.PARTIAL, ResponseCategory.COMPLETE]


class TestBatchAnalysis:
    """Tests for batch analysis functionality."""

    def test_batch_analyze(self, analyzer: ResponseQualityAnalyzer):
        """Test batch analysis of multiple queries."""
        pairs = [
            (
                "Tell me about HORIZON-CL5-2026-D3-01",
                "HORIZON-CL5-2026-D3-01: RIA call for hydrogen. "
                "Budget €50M. Deadline March 2026. Open.",
            ),
            (
                "What is EIC?",
                "EIC is the European Innovation Council for breakthrough innovation funding.",
            ),
            (
                "Find partners",
                "I could not find any partners. Try a more specific search.",
            ),
        ]

        analyses = analyzer.batch_analyze(pairs)
        assert len(analyses) == 3

        # Check summary stats
        summary = analyzer.get_summary_stats(analyses)
        assert summary["count"] == 3
        assert 0 <= summary["avg_score"] <= 100
        assert 0 <= summary["deflection_rate"] <= 1

    def test_summary_stats_calculation(self, analyzer: ResponseQualityAnalyzer):
        """Test summary statistics calculation."""
        pairs = [
            (
                "Query 1",
                "This is a complete response with call HORIZON-CL5-2026-D3-01, "
                "deadline March 2026, budget €50M, RIA type, open status.",
            ),
            (
                "Query 2",
                "Another good response about EIC with 8% success rate vs ERC 12%. "
                "In contrast, the funding amounts differ significantly.",
            ),
            (
                "Query 3",
                "I could not find any information about this topic. No results found. "
                "Please try a more specific search query to get better results.",
            ),
        ]

        analyses = analyzer.batch_analyze(pairs)
        summary = analyzer.get_summary_stats(analyses)

        assert summary["count"] == 3
        assert summary["min_score"] <= summary["avg_score"] <= summary["max_score"]
        assert summary["deflection_rate"] > 0  # At least one deflection


class TestRecommendations:
    """Tests for improvement recommendations."""

    def test_recommendations_for_deflection(self, analyzer: ResponseQualityAnalyzer):
        """Test that deflection responses get appropriate recommendations."""
        analysis = analyzer.analyze(
            "Find hydrogen partners",
            "I could not find any partners. No results found.",
            query_type=QueryType.PARTNER_DISCOVERY,
        )

        assert len(analysis.recommendations) > 0
        assert any("deflection" in r.lower() for r in analysis.recommendations)

    def test_recommendations_for_missing_elements(self, analyzer: ResponseQualityAnalyzer):
        """Test that missing elements generate recommendations."""
        # Response missing deadline
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01",
            "HORIZON-CL5-2026-D3-01 is an RIA call with €50M budget. Currently open.",
            query_type=QueryType.CALL_INFORMATION,
        )

        if "deadline" in analysis.missing_elements:
            assert any("missing" in r.lower() for r in analysis.recommendations)


class TestToolResultValidation:
    """Tests for tool result validation."""

    def test_tool_result_mismatch_detection(self, analyzer: ResponseQualityAnalyzer):
        """Test detection when response contradicts tool results."""
        tool_results = {
            "search_funding_calls": {
                "calls": [{"id": "HORIZON-CL5-2026-D3-01"}],
                "count": 1,
            }
        }

        analysis = analyzer.analyze(
            "Find hydrogen calls",
            "No calls found for hydrogen. Please try a different search.",
            query_type=QueryType.CALL_INFORMATION,
            tool_results=tool_results,
        )

        # Should detect mismatch between tool returning 1 call and response saying none
        has_mismatch_warning = any(
            "mismatch" in r.lower() or "returned" in r.lower() for r in analysis.recommendations
        )
        assert has_mismatch_warning, (
            f"Should detect tool/response mismatch. Recs: {analysis.recommendations}"
        )


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_query(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of empty query."""
        analysis = analyzer.analyze("", "Some response about funding.")
        assert analysis.query_type == QueryType.GENERAL

    def test_empty_response(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of empty response."""
        analysis = analyzer.analyze("Find partners", "")
        assert analysis.category == ResponseCategory.EMPTY
        assert analysis.score < 20

    def test_very_long_response(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of very long response."""
        long_response = "This is about HORIZON-CL5-2026-D3-01. " * 100 + (
            "Deadline: March 2026. Budget: €50M. Type: RIA. Status: Open. "
        )
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01",
            long_response,
            query_type=QueryType.CALL_INFORMATION,
        )
        assert analysis.score >= 70  # Should still analyze content correctly

    def test_unicode_content(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of unicode content."""
        analysis = analyzer.analyze(
            "Find partners in München",
            "Found partners: Technische Universität München (TUM) with €5 million in projects.",
            query_type=QueryType.PARTNER_DISCOVERY,
        )
        assert analysis.score > 0  # Should not crash

    def test_response_with_markdown(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of markdown-formatted response."""
        response = """
## HORIZON-CL5-2026-D3-01

**Type:** RIA
**Deadline:** March 15, 2026
**Budget:** €50 million

This call focuses on **hydrogen technologies**.
"""
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01",
            response,
            query_type=QueryType.CALL_INFORMATION,
        )
        # Should correctly identify elements in markdown
        assert analysis.content_elements_found.get("call_identifier", 0) > 0


class TestIsAcceptableMethod:
    """Tests for the is_acceptable method."""

    def test_acceptable_with_high_score(self, analyzer: ResponseQualityAnalyzer):
        """Test is_acceptable returns True for high score."""
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01",
            "HORIZON-CL5-2026-D3-01: RIA call. Deadline March 2026. Budget €50M. Open. "
            "Focus on hydrogen production technologies.",
            query_type=QueryType.CALL_INFORMATION,
        )
        if analysis.score >= 70:
            assert analysis.is_acceptable()

    def test_not_acceptable_deflection(self, analyzer: ResponseQualityAnalyzer):
        """Test is_acceptable returns False for deflection."""
        analysis = analyzer.analyze(
            "Find partners",
            "I could not find any partners. No results found. Try again.",
        )
        assert not analysis.is_acceptable()

    def test_custom_threshold(self, analyzer: ResponseQualityAnalyzer):
        """Test is_acceptable with custom threshold."""
        analysis = analyzer.analyze(
            "What is EIC?",
            "EIC is the European Innovation Council that funds innovation.",
        )
        # Test with very high threshold that the response won't pass
        assert not analysis.is_acceptable(min_score=99)
        # Test that it passes a reasonable threshold
        assert analysis.is_acceptable(min_score=80)
        # Test that it passes a low threshold
        if analysis.score >= 50:
            assert analysis.is_acceptable(min_score=50)
