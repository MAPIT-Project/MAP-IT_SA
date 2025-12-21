"""
Comprehensive AI Response Quality Tests

This test suite validates that AI responses meet quality standards and
provides meaningful, actionable information to users.

Key testing principles:
1. A response that exists is NOT enough - it must be useful
2. Deflection phrases ("I could not find", "no information available") are failures
3. Responses must contain required content elements for each query type
4. Quality scores must meet minimum thresholds (75+)

Run with: pytest tests/test_ai_quality/test_response_quality.py -v --tb=short
"""

import os
import sys
from typing import List, Optional

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.quality.response_quality_analyzer import (
    ContentRequirement,
    QualityAnalysis,
    QueryType,
    ResponseCategory,
    ResponseQualityAnalyzer,
)


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def analyzer() -> ResponseQualityAnalyzer:
    """Create a ResponseQualityAnalyzer instance."""
    return ResponseQualityAnalyzer()


# ============================================================================
# TEST RESPONSES - GOOD EXAMPLES
# ============================================================================


class GoodResponses:
    """Collection of high-quality response examples."""

    CALL_INFO_COMPLETE = """
    Here are the details for **HORIZON-CL5-2026-D3-01**:

    **Competitiveness, energy security and integration aspects of advanced biofuels**

    - **Call ID:** HORIZON-CL5-2026-D3-01
    - **Type:** RIA (Research and Innovation Action)
    - **Status:** Open
    - **Deadline:** 05 February 2026 17:00:00 (Brussels time)
    - **Programme:** Cluster 5 - Climate, Energy and Mobility
    - **Budget:** EUR 20.00 million

    **Scope:**
    This topic focuses on advanced biofuels and renewable fuels production technologies.
    It addresses the need for sustainable alternatives to fossil fuels in the transport sector.

    **Apply:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/HORIZON-CL5-2026-D3-01

    **How to Apply:**
    1. Register on the EU Funding & Tenders Portal
    2. Create or join a consortium with at least 3 partners from 3 EU countries
    3. Submit your proposal before the deadline
    """

    CALL_SEARCH_MULTIPLE = """
    I found **8 funding opportunities** for hydrogen research:

    **1. Hydrogen production technologies**
    - **Call ID:** HORIZON-CL5-2026-D3-02-01
    - **Type:** RIA
    - **Status:** Open
    - **Deadline:** 05 February 2026
    - **Budget:** EUR 15.00 million

    **2. Hydrogen storage solutions**
    - **Call ID:** HORIZON-CL5-2026-D3-02-02
    - **Type:** IA
    - **Status:** Upcoming
    - **Deadline:** 15 April 2026
    - **Budget:** EUR 25.00 million

    **3. Fuel cell applications**
    - **Call ID:** HORIZON-CL5-2026-D3-02-03
    - **Type:** RIA
    - **Status:** Open
    - **Deadline:** 05 February 2026
    - **Budget:** EUR 18.00 million

    All these calls are part of Cluster 5 - Climate, Energy and Mobility.
    """

    PROJECT_SEARCH = """
    I found **15 funded projects** related to quantum computing:

    **1. QUANTUMHPC** (Germany)
    - Funding: EUR 4.5 million
    - Duration: 2023-2027
    - Focus: Quantum algorithms for high-performance computing

    **2. QUSIM** (Netherlands)
    - Funding: EUR 3.8 million
    - Duration: 2022-2026
    - Focus: Quantum simulation for materials science

    **3. EURQCI** (France)
    - Funding: EUR 5.2 million
    - Duration: 2023-2027
    - Focus: European quantum communication infrastructure

    These projects are funded under Cluster 4 - Digital, Industry and Space.
    Source: CORDIS database.
    """

    PROGRAMME_COMPARISON = """
    Here's a comparison of **EIC Accelerator** vs **ERC Grants**:

    | Aspect | EIC Accelerator | ERC Grants |
    |--------|-----------------|------------|
    | Target | SMEs and startups | Individual researchers |
    | Funding | Up to EUR 17.5M (blended) | EUR 1.5M - 10M |
    | Success Rate | ~8% | ~12% |
    | Duration | 2-3 years | 5 years |
    | Evaluation | Innovation & market | Scientific excellence |

    **Key Differences:**
    - EIC focuses on market-ready innovation with equity investment options
    - ERC focuses on frontier research with scientific excellence as the main criterion
    - EIC requires a business plan, ERC requires a research proposal
    - EIC allows consortium applications, ERC is individual researcher only

    **Recommendation:**
    Choose EIC Accelerator if you have a market-ready product/technology.
    Choose ERC if you're conducting fundamental research with breakthrough potential.
    """

    ELIGIBILITY_CLEAR = """
    **Yes, Swiss organizations can participate in Horizon Europe funding calls.**

    Switzerland has the status of an Associated Country (since January 2024), which means:

    - Swiss entities can participate as full partners in collaborative projects (RIA, IA, CSA)
    - Swiss coordinators are eligible in most calls
    - Swiss participants receive funding directly from SERI (Swiss State Secretariat)

    **Requirements:**
    - Minimum 3 independent legal entities from 3 different EU Member States or Associated Countries
    - At least one partner must be from an EU Member State
    - Swiss partners count towards the minimum requirements

    **Note:** Some specific calls (e.g., EIC Accelerator) may have additional restrictions.
    Check the specific call conditions for details.

    Source: Horizon Europe Work Programme 2024-2025, Article 23.
    """

    BUDGET_BENCHMARK = """
    **Budget Benchmarks for RIA Projects in Cluster 5 (Climate, Energy, Mobility):**

    Based on analysis of **496 funded projects**:

    | Metric | Value |
    |--------|-------|
    | Average EU Contribution | EUR 4.9 million |
    | Median EU Contribution | EUR 4.5 million |
    | Minimum | EUR 1.3 million |
    | Maximum | EUR 20 million |
    | Average per Partner | EUR 490,000 |

    **Consortium Size:**
    - Average partners: 13.3
    - Median partners: 12
    - Recommended range: 10-15 partners

    **Budget by Organization Type:**
    - Research Institutes (REC): 34%
    - Private Companies (PRC): 34%
    - Universities (HES): 28%
    - Other: 4%

    **Recommendations:**
    - Target EUR 4-6 million for a typical RIA
    - Budget EUR 400-600K per partner
    - Include 10-15 partners from at least 7 countries
    """

    PARTNER_DISCOVERY = """
    I found **15 experienced partners** for hydrogen fuel cell research in Germany:

    **Top Organizations:**

    1. **Fraunhofer Institute for Solar Energy Systems (ISE)**
       - Country: Germany
       - Type: Research Institute (REC)
       - Experience: 45 Horizon projects, 12 as coordinator
       - Expertise: Hydrogen production, fuel cells, energy storage

    2. **Forschungszentrum Juelich**
       - Country: Germany
       - Type: Research Institute (REC)
       - Experience: 38 Horizon projects
       - Expertise: Electrochemistry, hydrogen storage

    3. **Technical University of Munich**
       - Country: Germany
       - Type: University (HES)
       - Experience: 52 Horizon projects
       - Expertise: Fuel cell technology, automotive applications

    All partners have proven track records in hydrogen-related EU projects.
    Data source: CORDIS database and Neo4j collaboration network.
    """

    CONSORTIUM_PATTERNS = """
    **Consortium Patterns for Health IA Projects:**

    Analysis of **320 funded projects** shows:

    **Size:**
    - Average consortium size: 12.5 partners
    - Median: 11 partners
    - Optimal range: 10-15 partners

    **Organization Type Distribution:**
    - Universities (HES): 35%
    - Research Institutes (REC): 28%
    - Private Companies (PRC): 22%
    - SMEs: 10%
    - Other (Hospitals, NGOs): 5%

    **Geographic Diversity:**
    - Average countries: 8.2
    - Minimum required: 3
    - Recommended: 7-10 countries

    **Top Coordinator Countries:**
    1. Germany (22%)
    2. Netherlands (15%)
    3. France (12%)

    **Recommendations:**
    - Include 3-4 universities and 2-3 research institutes
    - Add 2-3 industrial partners for impact demonstration
    - Ensure at least 7 different EU Member States
    """


# ============================================================================
# TEST RESPONSES - BAD EXAMPLES (DEFLECTIONS)
# ============================================================================


class BadResponses:
    """Collection of poor quality response examples that should fail."""

    DEFLECTION_CRITICAL = """
    I apologize, but I could not find any specific information about that call.
    Please try a more specific search term or check the EU Portal directly.
    Try again later when our database is updated.
    """

    DEFLECTION_MAJOR = """
    I found some information but could not extract specific details about the deadline
    or budget for HORIZON-CL5-2026-D3-01. The call appears to be related to energy
    research but I don't have access to the current status.
    """

    DEFLECTION_NO_INFO = """
    No information available for this query. The search returned no matching results.
    I don't have access to the specific call details you're looking for.
    """

    TOO_SHORT = """
    Yes, calls are available. Check the portal.
    """

    EMPTY_CONTENT = """
    I understand you're asking about funding calls. Let me know if you have
    any other questions.
    """

    VAGUE_ANSWER = """
    There are many funding opportunities in Horizon Europe. The programme offers
    various types of grants and funding mechanisms. You should explore the
    EU Funding & Tenders Portal for more information about specific calls.
    """

    PARTIAL_WITH_DEFLECTION = """
    I found information about HORIZON-CL5-2026-D3-01, but unfortunately I cannot
    provide the specific deadline or budget information as the database is currently
    unavailable. Here's what I know:

    This is a Research and Innovation Action (RIA) under Cluster 5.

    I'm sorry but I don't have the exact budget figures at this time.
    """


# ============================================================================
# UNIT TESTS - ResponseQualityAnalyzer
# ============================================================================


class TestResponseQualityAnalyzerBasics:
    """Test basic functionality of ResponseQualityAnalyzer."""

    def test_analyzer_initialization(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that analyzer initializes correctly."""
        assert analyzer is not None
        assert len(analyzer._compiled_deflection_patterns) > 0
        assert len(analyzer._compiled_query_patterns) > 0

    def test_query_type_detection_call_info(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test query type detection for call info queries."""
        queries = [
            "Tell me about HORIZON-CL5-2026-D3-01",
            "What is the deadline for HORIZON-CL5-2026-D3-01?",
            "Details for call HORIZON-CL4-2025-DATA-01",
        ]
        for query in queries:
            detected = analyzer._detect_query_type(query)
            assert detected == QueryType.CALL_INFO, f"Failed for: {query}"

    def test_query_type_detection_call_search(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test query type detection for call search queries."""
        queries = [
            "Find hydrogen funding calls",
            "Search for open calls in energy",
            "Looking for funding opportunities in AI",
        ]
        for query in queries:
            detected = analyzer._detect_query_type(query)
            assert detected == QueryType.CALL_SEARCH, f"Failed for: {query}"

    def test_query_type_detection_comparison(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test query type detection for comparison queries."""
        queries = [
            "Compare EIC vs ERC success rates",
            "What's the difference between RIA and IA?",
            "EIC Accelerator compared to ERC grants",
        ]
        for query in queries:
            detected = analyzer._detect_query_type(query)
            assert detected == QueryType.PROGRAMME_COMPARISON, f"Failed for: {query}"

    def test_deflection_detection_critical(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of critical deflection phrases."""
        phrases, severity = analyzer._detect_deflections(BadResponses.DEFLECTION_CRITICAL)
        assert severity == "critical"
        assert len(phrases) > 0

    def test_deflection_detection_major(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of major deflection phrases."""
        phrases, severity = analyzer._detect_deflections(BadResponses.DEFLECTION_MAJOR)
        assert severity in ("major", "critical")
        assert len(phrases) > 0

    def test_deflection_detection_none(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that good responses have no deflection."""
        phrases, severity = analyzer._detect_deflections(GoodResponses.CALL_INFO_COMPLETE)
        assert severity == "none"
        assert len(phrases) == 0


# ============================================================================
# QUALITY ANALYSIS TESTS - GOOD RESPONSES
# ============================================================================


class TestGoodResponseQuality:
    """Test that good responses receive high quality scores."""

    def test_complete_call_info(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test analysis of a complete call info response."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=GoodResponses.CALL_INFO_COMPLETE,
        )

        assert analysis.category == ResponseCategory.COMPLETE
        assert analysis.score >= 80
        assert "call_identifier" in analysis.present_elements
        assert "deadline" in analysis.present_elements
        assert analysis.deflection_severity == "none"
        assert analyzer.is_acceptable(analysis)

    def test_call_search_multiple(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test analysis of a call search response with multiple results."""
        analysis = analyzer.analyze(
            query="Find hydrogen funding calls",
            response=GoodResponses.CALL_SEARCH_MULTIPLE,
        )

        assert analysis.category in (ResponseCategory.COMPLETE, ResponseCategory.PARTIAL)
        assert analysis.score >= 75
        assert analysis.deflection_severity == "none"
        assert analyzer.is_acceptable(analysis)

    def test_project_search(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test analysis of a project search response."""
        analysis = analyzer.analyze(
            query="Find quantum computing projects",
            response=GoodResponses.PROJECT_SEARCH,
        )

        assert analysis.score >= 75
        assert analysis.deflection_severity == "none"
        assert analyzer.is_acceptable(analysis)

    def test_programme_comparison(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test analysis of a programme comparison response."""
        analysis = analyzer.analyze(
            query="Compare EIC Accelerator vs ERC grants",
            response=GoodResponses.PROGRAMME_COMPARISON,
        )

        assert analysis.category == ResponseCategory.COMPLETE
        assert analysis.score >= 80
        assert "comparison_elements" in analysis.present_elements
        assert analysis.has_structured_data
        assert analyzer.is_acceptable(analysis)

    def test_eligibility_answer(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test analysis of an eligibility FAQ response."""
        analysis = analyzer.analyze(
            query="Can Swiss organizations participate in Horizon Europe?",
            response=GoodResponses.ELIGIBILITY_CLEAR,
        )

        assert analysis.score >= 80
        assert "clear_answer" in analysis.present_elements
        assert analysis.has_citations
        assert analyzer.is_acceptable(analysis)

    def test_budget_benchmark(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test analysis of a budget benchmark response."""
        analysis = analyzer.analyze(
            query="What is typical budget for Horizon RIA in Cluster 5?",
            response=GoodResponses.BUDGET_BENCHMARK,
        )

        assert analysis.category == ResponseCategory.COMPLETE
        assert analysis.score >= 80
        assert "budget_figures" in analysis.present_elements
        assert "statistics" in analysis.present_elements
        assert analysis.has_structured_data
        assert analyzer.is_acceptable(analysis)

    def test_partner_discovery(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test analysis of a partner discovery response."""
        analysis = analyzer.analyze(
            query="Find German organizations with hydrogen experience",
            response=GoodResponses.PARTNER_DISCOVERY,
        )

        assert analysis.score >= 75
        assert "partners_found" in analysis.present_elements
        assert analyzer.is_acceptable(analysis)

    def test_consortium_patterns(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test analysis of a consortium patterns response."""
        analysis = analyzer.analyze(
            query="What is typical consortium size for Health IAs?",
            response=GoodResponses.CONSORTIUM_PATTERNS,
        )

        assert analysis.score >= 75
        assert "consortium_size" in analysis.present_elements
        assert analysis.has_structured_data
        assert analyzer.is_acceptable(analysis)


# ============================================================================
# QUALITY ANALYSIS TESTS - BAD RESPONSES
# ============================================================================


class TestBadResponseQuality:
    """Test that bad responses are correctly identified and scored low."""

    def test_critical_deflection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that critical deflections are identified."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=BadResponses.DEFLECTION_CRITICAL,
        )

        assert analysis.category == ResponseCategory.DEFLECTION
        assert analysis.score < 30
        assert analysis.deflection_severity == "critical"
        assert not analyzer.is_acceptable(analysis)
        assert len(analysis.deflection_phrases_found) > 0

    def test_major_deflection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that major deflections are identified."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=BadResponses.DEFLECTION_MAJOR,
        )

        assert analysis.category == ResponseCategory.DEFLECTION
        assert analysis.score < 50
        assert analysis.deflection_severity in ("major", "critical")
        assert not analyzer.is_acceptable(analysis)

    def test_no_info_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that 'no information' responses fail."""
        analysis = analyzer.analyze(
            query="Find hydrogen funding calls",
            response=BadResponses.DEFLECTION_NO_INFO,
        )

        assert analysis.category == ResponseCategory.DEFLECTION
        assert analysis.score < 30
        assert not analyzer.is_acceptable(analysis)

    def test_too_short_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that too short responses fail."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=BadResponses.TOO_SHORT,
        )

        assert analysis.category in (ResponseCategory.EMPTY, ResponseCategory.PARTIAL)
        assert analysis.score < 50
        assert not analyzer.is_acceptable(analysis)

    def test_empty_content(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that empty/generic responses fail."""
        analysis = analyzer.analyze(
            query="What's the deadline for HORIZON-CL5-2026-D3-01?",
            response=BadResponses.EMPTY_CONTENT,
        )

        assert analysis.score < 50
        assert not analyzer.is_acceptable(analysis)

    def test_vague_answer(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that vague answers without specifics fail."""
        analysis = analyzer.analyze(
            query="Find hydrogen funding calls",
            response=BadResponses.VAGUE_ANSWER,
        )

        assert analysis.score < 70
        # May be partial but not complete
        assert analysis.category != ResponseCategory.COMPLETE
        assert not analyzer.is_acceptable(analysis, min_score=75)

    def test_partial_with_deflection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that partial responses with deflection are penalized."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=BadResponses.PARTIAL_WITH_DEFLECTION,
        )

        assert analysis.score < 70
        assert analysis.deflection_severity in ("minor", "major", "critical")
        assert not analyzer.is_acceptable(analysis, min_score=75)


# ============================================================================
# PARAMETRIZED TESTS - COMPREHENSIVE QUERY COVERAGE
# ============================================================================


# Test data: (query, expected_elements, min_score, expected_category)
COMPREHENSIVE_TEST_QUERIES = [
    # Call information queries (5)
    (
        "Tell me about HORIZON-CL5-2026-D3-01",
        ["call_identifier", "deadline", "budget", "action_type"],
        75,
        QueryType.CALL_INFO,
    ),
    (
        "What is HORIZON-CL4-2025-DATA-01?",
        ["call_identifier", "status"],
        75,
        QueryType.CALL_INFO,
    ),
    (
        "Details for call HORIZON-HLTH-2025-DISEASE-01",
        ["call_identifier", "deadline"],
        75,
        QueryType.CALL_INFO,
    ),
    (
        "When is the deadline for HORIZON-CL6-2026-FARM-01?",
        ["deadline"],
        75,
        QueryType.CALL_INFO,
    ),
    (
        "What's the budget for HORIZON-EIC-2025-ACCELERATOR?",
        ["budget"],
        75,
        QueryType.CALL_INFO,
    ),
    # Programme comparison queries (5)
    (
        "Compare EIC Accelerator with ERC grants",
        ["comparison_elements", "specific_metrics"],
        75,
        QueryType.PROGRAMME_COMPARISON,
    ),
    (
        "What's the difference between RIA and IA projects?",
        ["comparison_elements"],
        75,
        QueryType.PROGRAMME_COMPARISON,
    ),
    (
        "EIC vs ERC - which has better success rate?",
        ["comparison_elements"],
        75,
        QueryType.PROGRAMME_COMPARISON,
    ),
    (
        "Compare MSCA Individual Fellowships with ERC Starting Grant",
        ["comparison_elements"],
        75,
        QueryType.PROGRAMME_COMPARISON,
    ),
    (
        "Horizon Europe RIA compared to IA in terms of funding",
        ["comparison_elements", "specific_metrics"],
        75,
        QueryType.PROGRAMME_COMPARISON,
    ),
    # Eligibility/FAQ queries (5)
    (
        "Can SMEs apply to Horizon Europe?",
        ["clear_answer", "requirements"],
        75,
        QueryType.ELIGIBILITY_FAQ,
    ),
    (
        "Are UK organizations eligible for Horizon Europe?",
        ["clear_answer"],
        75,
        QueryType.ELIGIBILITY_FAQ,
    ),
    (
        "What are the consortium requirements for RIA?",
        ["requirements", "specific_rules"],
        75,
        QueryType.ELIGIBILITY_FAQ,
    ),
    (
        "Can a single organization apply to Horizon Europe?",
        ["clear_answer"],
        75,
        QueryType.ELIGIBILITY_FAQ,
    ),
    (
        "Who can be a coordinator in Horizon Europe?",
        ["clear_answer", "requirements"],
        75,
        QueryType.ELIGIBILITY_FAQ,
    ),
    # Budget benchmark queries (3)
    (
        "What is typical budget for Horizon Europe RIA in Cluster 5?",
        ["budget_figures", "statistics"],
        75,
        QueryType.BUDGET_BENCHMARK,
    ),
    (
        "Average funding for IA projects in digital cluster",
        ["budget_figures"],
        75,
        QueryType.BUDGET_BENCHMARK,
    ),
    (
        "Budget per partner for a typical Health RIA",
        ["budget_figures"],
        75,
        QueryType.BUDGET_BENCHMARK,
    ),
    # Partner discovery queries (3)
    (
        "Find German SMEs with hydrogen experience",
        ["partners_found", "country_info"],
        75,
        QueryType.PARTNER_DISCOVERY,
    ),
    (
        "Organizations in France with AI track record",
        ["partners_found", "experience_indicators"],
        75,
        QueryType.PARTNER_DISCOVERY,
    ),
    (
        "Universities with climate research expertise",
        ["partners_found"],
        75,
        QueryType.PARTNER_DISCOVERY,
    ),
    # Project search queries (2)
    (
        "Find quantum computing projects",
        ["projects_found"],
        75,
        QueryType.PROJECT_SEARCH,
    ),
    (
        "CORDIS projects about renewable energy",
        ["projects_found", "project_names"],
        75,
        QueryType.PROJECT_SEARCH,
    ),
    # Consortium patterns queries (2)
    (
        "What is typical consortium size for Health IAs?",
        ["consortium_size"],
        75,
        QueryType.CONSORTIUM_PATTERNS,
    ),
    (
        "How many partners do successful RIAs have?",
        ["consortium_size"],
        75,
        QueryType.CONSORTIUM_PATTERNS,
    ),
]


class TestComprehensiveQueryCoverage:
    """Comprehensive test coverage for various query types."""

    @pytest.mark.parametrize(
        "query,expected_elements,min_score,query_type",
        COMPREHENSIVE_TEST_QUERIES,
        ids=[q[0][:50] for q in COMPREHENSIVE_TEST_QUERIES],
    )
    def test_query_type_detection(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_elements: List[str],
        min_score: int,
        query_type: QueryType,
    ) -> None:
        """Test that query types are correctly detected."""
        detected = analyzer._detect_query_type(query)
        assert detected == query_type, f"Expected {query_type}, got {detected} for: {query}"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of empty response."""
        analysis = analyzer.analyze(query="Test query", response="")
        assert analysis.category == ResponseCategory.EMPTY
        assert analysis.score < 20

    def test_very_short_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of very short response."""
        analysis = analyzer.analyze(query="Test query", response="No.")
        assert analysis.score < 30

    def test_very_long_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of very long response."""
        long_response = GoodResponses.CALL_INFO_COMPLETE * 10
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=long_response,
        )
        assert analysis.score >= 75  # Should still be acceptable

    def test_response_with_special_characters(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of responses with special characters."""
        response = """
        Budget: €5,000,000 (EUR 5M)
        Organizations: Fraunhofer, CNRS, TU München
        Topics: AI & ML, CO₂ reduction
        """
        analysis = analyzer.analyze(
            query="Budget for RIA",
            response=response,
        )
        assert analysis.query_type in (QueryType.BUDGET_BENCHMARK, QueryType.GENERAL_FAQ)

    def test_multilingual_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of multilingual content."""
        response = """
        The Horizon Europe programme (Programme Horizon Europe in French) offers
        funding opportunities (Förderungsmöglichkeiten in German) across Europe.
        Budget: EUR 10 million. Deadline: 15 March 2025.
        """
        analysis = analyzer.analyze(
            query="Tell me about Horizon calls",
            response=response,
        )
        # Should handle multilingual content gracefully
        assert analysis.score > 0


# ============================================================================
# CONTENT REQUIREMENT TESTS
# ============================================================================


class TestContentRequirements:
    """Test content requirement detection."""

    def test_call_info_requirements(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that call info requirements are properly checked."""
        # Response missing deadline
        response_no_deadline = """
        HORIZON-CL5-2026-D3-01 is a Research and Innovation Action (RIA)
        with a budget of EUR 10 million. The call is currently open.
        """
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=response_no_deadline,
        )
        # Should detect missing deadline
        assert "deadline" in analysis.missing_elements or analysis.score < 90

    def test_budget_info_detection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test budget information detection."""
        # Use longer responses that won't be categorized as EMPTY
        responses_with_budget = [
            "The budget for this RIA project is EUR 10 million total. This includes personnel costs, equipment, and subcontracting. The average per partner is around 1.25M EUR.",
            "Total funding available: €5.5M for this call. The budget breakdown includes 40% for personnel, 30% for equipment, and 30% for other costs.",
            "The budget is 15M EUR for the entire consortium. With 12 partners, this averages to approximately €1.25 million per partner.",
            "Up to 20 million euros is available for this Innovation Action. The typical budget range for similar projects is €15-25 million.",
        ]
        for response in responses_with_budget:
            analysis = analyzer.analyze(
                query="What is typical budget for Horizon Europe RIA?",
                response=response,
                query_type=QueryType.BUDGET_BENCHMARK,
            )
            # Budget figures should be detected
            assert "budget_figures" in analysis.present_elements or analysis.content_coverage > 0

    def test_deadline_detection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test deadline detection in various formats."""
        responses_with_deadline = [
            "Deadline: 15 March 2025",
            "Submit before 2025-03-15",
            "The deadline is 15 Mar 2025",
            "Applications due February 2025",
        ]
        for response in responses_with_deadline:
            analysis = analyzer.analyze(
                query="When is the deadline?",
                response=response,
                query_type=QueryType.CALL_INFO,
            )
            assert "deadline" in analysis.present_elements


# ============================================================================
# DEFLECTION PATTERN TESTS
# ============================================================================


class TestDeflectionPatterns:
    """Test detection of various deflection patterns."""

    DEFLECTION_SAMPLES = [
        ("I could not find information about that topic.", "major"),
        ("No results found for your query.", "major"),
        ("I'm sorry, but I don't have access to that information.", "major"),
        ("Please try a more specific search.", "major"),
        ("The database is currently unavailable.", "critical"),
        ("I apologize, but I cannot provide that information.", "major"),
        ("Unfortunately, this is outside my knowledge.", "major"),
    ]

    @pytest.mark.parametrize(
        "response,expected_severity",
        DEFLECTION_SAMPLES,
        ids=[s[0][:40] for s in DEFLECTION_SAMPLES],
    )
    def test_deflection_severity(
        self,
        analyzer: ResponseQualityAnalyzer,
        response: str,
        expected_severity: str,
    ) -> None:
        """Test that deflection severities are correctly identified."""
        phrases, severity = analyzer._detect_deflections(response)
        assert severity in (expected_severity, "critical")
        assert len(phrases) > 0


# ============================================================================
# QUALITY INDICATOR TESTS
# ============================================================================


class TestQualityIndicators:
    """Test quality indicator detection."""

    def test_structured_data_detection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test structured data detection."""
        structured_responses = [
            "- Item 1\n- Item 2\n- Item 3",
            "1. First\n2. Second\n3. Third",
            "| Col1 | Col2 |\n|------|------|\n| A | B |",
            "**Header:** Value",
        ]
        for response in structured_responses:
            assert analyzer._has_structured_data(response), f"Failed for: {response}"

    def test_citation_detection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test citation detection."""
        cited_responses = [
            "According to the Horizon Europe Work Programme...",
            "Source: EU Funding Portal",
            "Based on Article 23 of the regulation...",
            "The Work Programme 2024 states that...",
        ]
        for response in cited_responses:
            assert analyzer._has_citations(response), f"Failed for: {response}"

    def test_actionable_info_detection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test actionable information detection."""
        actionable_responses = [
            "Apply at https://ec.europa.eu/portal",
            "Deadline: 15 March 2025",
            "Step 1: Register on the portal",
            "Submit your proposal before...",
        ]
        for response in actionable_responses:
            assert analyzer._has_actionable_info(response), f"Failed for: {response}"


# ============================================================================
# REPORT GENERATION TESTS
# ============================================================================


class TestReportGeneration:
    """Test report generation functionality."""

    def test_format_report(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that reports are properly formatted."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=GoodResponses.CALL_INFO_COMPLETE,
        )
        report = analyzer.format_report(analysis)

        assert "Response Quality Report" in report
        assert "Score:" in report
        assert "Content Analysis:" in report
        assert "Quality Indicators:" in report

    def test_report_includes_recommendations(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that poor responses include recommendations."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=BadResponses.DEFLECTION_CRITICAL,
        )
        report = analyzer.format_report(analysis)

        assert "Recommendations:" in report


# ============================================================================
# INTEGRATION-STYLE TESTS
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_analyze_batch_of_responses(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test analyzing a batch of responses."""
        # Tuple: (name, query, response, should_pass)
        responses = [
            ("Good call info", "Tell me about HORIZON-CL5-2026-D3-01", GoodResponses.CALL_INFO_COMPLETE, True),
            ("Critical deflection", "Tell me about HORIZON-CL5-2026-D3-01", BadResponses.DEFLECTION_CRITICAL, False),
            ("Good comparison", "Compare EIC vs ERC", GoodResponses.PROGRAMME_COMPARISON, True),
            ("Too short", "Tell me about the call", BadResponses.TOO_SHORT, False),
        ]

        for name, query, response, should_pass in responses:
            analysis = analyzer.analyze(
                query=query,
                response=response,
            )
            is_acceptable = analyzer.is_acceptable(analysis, min_score=75)
            assert is_acceptable == should_pass, f"Failed for: {name} (score={analysis.score}, category={analysis.category})"

    def test_quality_threshold_enforcement(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that quality thresholds are properly enforced."""
        # Good response should pass at 75
        good_analysis = analyzer.analyze(
            query="Compare EIC vs ERC",
            response=GoodResponses.PROGRAMME_COMPARISON,
        )
        assert analyzer.is_acceptable(good_analysis, min_score=75)
        assert analyzer.is_acceptable(good_analysis, min_score=80)

        # Bad response should fail at 75
        bad_analysis = analyzer.analyze(
            query="Tell me about the call",
            response=BadResponses.DEFLECTION_MAJOR,
        )
        assert not analyzer.is_acceptable(bad_analysis, min_score=75)
        assert not analyzer.is_acceptable(bad_analysis, min_score=50)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
