"""
AI Response Quality Test Suite.

This module provides comprehensive tests for AI response quality analysis,
ensuring that responses meet quality standards and don't contain deflections.

IMPORTANT: These tests validate the ResponseQualityAnalyzer's ability to:
1. Detect deflection phrases (e.g., "could not find", "no information")
2. Validate content requirements for different query types
3. Score response quality accurately
4. Categorize responses correctly (complete, partial, deflection, empty)

These tests do NOT simply check "response exists" - they validate actual quality.

Run with: pytest tests/test_ai_quality/test_response_quality.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.quality.response_quality_analyzer import (
    QueryType,
    ResponseCategory,
    ResponseQualityAnalyzer,
)

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def analyzer() -> ResponseQualityAnalyzer:
    """Create a ResponseQualityAnalyzer instance for testing."""
    return ResponseQualityAnalyzer()


# ============================================================================
# Sample Responses for Testing
# ============================================================================

class SampleResponses:
    """Collection of sample responses for testing quality analysis."""

    # Good response for call info query
    GOOD_CALL_INFO = """
    I found the funding call **HORIZON-CL5-2026-D3-01**.

    **Call Details:**
    - **Call ID:** HORIZON-CL5-2026-D3-01
    - **Type:** 🔬 RIA (Research and Innovation Action)
    - **Status:** 🟢 Open
    - **Deadline:** 05 February 2026
    - **Budget:** EUR 20 million
    - **Programme:** Cluster 5 - Climate, Energy and Mobility

    **Scope:**
    This call focuses on advanced biofuels and renewable fuels research,
    addressing the competitiveness and energy security aspects of the
    European energy transition.

    **Apply:** https://ec.europa.eu/funding-tenders/...
    """

    # Deflecting response for call info
    DEFLECTING_CALL_INFO = """
    I could not find specific details about that call ID. The information
    is not available in my current data. Please try a more specific search
    or check the EU Funding Portal directly.
    """

    # Partial response for call info (missing key elements)
    PARTIAL_CALL_INFO = """
    I found a call about hydrogen research. It's part of Cluster 5.
    The call focuses on clean energy topics.
    """

    # Good response for programme comparison
    GOOD_PROGRAMME_COMPARISON = """
    **Comparing EIC Accelerator vs ERC Grants:**

    | Aspect | EIC Accelerator | ERC Grants |
    |--------|-----------------|------------|
    | **Target** | SMEs and startups | Individual researchers |
    | **Funding Range** | Up to €17.5M (blended) | €1.5M - €10M |
    | **Success Rate** | ~8% | ~12% |
    | **Focus** | Market-ready innovation | Frontier research |
    | **Duration** | 2-3 years | 5 years |

    **Recommendation:** Choose EIC if you have a market-ready innovation
    or startup. Choose ERC if you're focused on fundamental research.
    EIC offers equity financing plus grants, while ERC is purely grants.
    """

    # Deflecting comparison response
    DEFLECTING_COMPARISON = """
    I am not sure about the exact differences between these programmes.
    The information I have is limited. You should consult the official
    documentation for accurate comparison.
    """

    # Good eligibility FAQ response
    GOOD_ELIGIBILITY = """
    **Can SMEs apply to Horizon Europe RIA grants?**

    Yes, SMEs can absolutely participate in RIA (Research and Innovation Action)
    projects under Horizon Europe.

    **Requirements:**
    - Must be a legal entity established in an EU Member State or Associated Country
    - Minimum consortium requires 3 independent entities from 3 different countries
    - SME-specific eligibility: Must meet the EU SME definition (< 250 employees, ≤ €50M turnover)

    **Benefits for SMEs:**
    - Higher funding rate (up to 100% vs 100% for all in RIA)
    - Access to Innovation Radar and technology transfer
    - Networking with research organizations

    SMEs typically participate as partners, but can also coordinate if they
    have the administrative capacity.
    """

    # Deflecting eligibility response
    DEFLECTING_ELIGIBILITY = """
    I don't have access to the current eligibility requirements.
    Without more information about your specific situation, I cannot answer
    definitively. Please check the official Horizon Europe documentation.
    """

    # Good budget benchmark response
    GOOD_BUDGET_BENCHMARK = """
    **Budget Benchmarks for Cluster 5 RIA Projects:**

    Based on analysis of 496 funded projects in CLUSTER-5 (Climate, Energy, Mobility):

    **Budget Statistics:**
    - **Average EU Contribution:** €4.9 million
    - **Median EU Contribution:** €4.5 million
    - **Range:** €1.3M - €20M
    - **Per Partner Average:** €375,000 - €500,000

    **Consortium Size:**
    - **Average:** 13.3 partners
    - **Median:** 12 partners
    - **Typical Countries:** 7-9

    **Recommendations:**
    - For a standard RIA with 10-12 partners, target €4-6M
    - Budget €400-500K per partner
    - Include contingency of 5-10%

    **Top Coordinator Countries:** Spain, Italy, Germany, France
    """

    # Deflecting budget response
    DEFLECTING_BUDGET = """
    I found some information but could not extract specific details about
    budget benchmarks. The data is unavailable for your specific query.
    """

    # Good partner discovery response
    GOOD_PARTNER_DISCOVERY = """
    **Experienced Partners in Hydrogen Research (Germany):**

    I found 15 organizations with strong hydrogen experience:

    1. **Technical University of Munich (TUM)**
       - Country: Germany (DE)
       - Type: HES (Higher Education)
       - Hydrogen Projects: 12
       - Coordination Experience: 5 projects
       - Relevance Score: 95%

    2. **Fraunhofer ISE**
       - Country: Germany (DE)
       - Type: REC (Research Center)
       - Hydrogen Projects: 18
       - Coordination Experience: 8 projects
       - Relevance Score: 92%

    3. **Forschungszentrum Jülich**
       - Country: Germany (DE)
       - Type: REC
       - Hydrogen Projects: 15
       - Relevance Score: 90%

    These partners have proven track records in Horizon Europe hydrogen projects.
    """

    # Deflecting partner response
    DEFLECTING_PARTNER = """
    Unable to find organizations matching your criteria. The search
    returned no results. Try a different keyword or expand your search.
    """

    # Good project search response
    GOOD_PROJECT_SEARCH = """
    **Quantum Computing Projects in Horizon Europe:**

    Found 8 relevant funded projects:

    1. **QUCATS** - Quantum Computing for Advanced Technologies
       - Funding: €4.5M EC contribution
       - Consortium: 12 partners from 8 countries
       - Status: SIGNED (active)
       - Focus: Quantum algorithms for optimization

    2. **QUANTERA** - Quantum Technologies ERA-NET
       - Funding: €6.2M EC contribution
       - Consortium: 15 partners
       - Focus: Coordinating quantum research across Europe

    3. **QUCHIP** - Quantum Simulation on a Chip
       - Funding: €3.8M EC contribution
       - Focus: Photonic quantum computing

    These projects represent the latest in EU-funded quantum research.
    """

    # Deflecting project response
    DEFLECTING_PROJECT = """
    Query returned empty results. No matching projects found in the
    CORDIS database. My knowledge cutoff may affect these results.
    """

    # Good consortium pattern response
    GOOD_CONSORTIUM_PATTERN = """
    **Typical Consortium Patterns for Health Cluster IAs:**

    Based on 320 funded projects in CLUSTER-1 (Health):

    **Consortium Composition:**
    - **Average Size:** 9.2 partners (median: 8)
    - **Average Countries:** 7.5 (median: 7)

    **Organization Type Distribution:**
    | Type | Percentage | Typical Count |
    |------|------------|---------------|
    | HES (Universities) | 38% | 3-4 partners |
    | REC (Research) | 30% | 2-3 partners |
    | PRC (Industry) | 23% | 2 partners |
    | SME | 9% | 1 partner |

    **Top Coordinator Countries:** Germany (22.5%), Netherlands (14.1%), France (12%)

    **Recommendation:** Target 8-10 partners with 3-4 universities, 2-3
    research institutes, and 2 industry partners for optimal success.
    """

    # Empty response
    EMPTY_RESPONSE = "."

    # Short deflecting response
    SHORT_DEFLECTION = "I cannot answer this question."


# ============================================================================
# Test Class: Deflection Detection
# ============================================================================

class TestDeflectionDetection:
    """Test deflection phrase detection capabilities."""

    @pytest.mark.parametrize("phrase,expected_detected", [
        ("could not find", True),
        ("couldn't find", True),
        ("no information available", True),
        ("I am not sure", True),
        ("I don't have", True),
        ("unable to retrieve", True),
        ("no results found", True),
        ("try again later", True),
        ("could not extract specific details", True),
        ("found some information but", True),
        ("this is a normal sentence", False),
        ("the project was successful", False),
    ])
    def test_deflection_phrase_detection(
        self, analyzer: ResponseQualityAnalyzer, phrase: str, expected_detected: bool
    ):
        """Test individual deflection phrase detection."""
        phrases_found = analyzer._detect_deflection_phrases(phrase.lower())
        assert (len(phrases_found) > 0) == expected_detected

    def test_multiple_deflection_phrases(self, analyzer: ResponseQualityAnalyzer):
        """Test detection of multiple deflection phrases in one response."""
        response = "I could not find the information. I am not sure about the details."
        phrases_found = analyzer._detect_deflection_phrases(response.lower())
        assert len(phrases_found) >= 2

    def test_deflection_in_context(self, analyzer: ResponseQualityAnalyzer):
        """Test deflection detection in full response context."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=SampleResponses.DEFLECTING_CALL_INFO,
        )
        assert analysis.category == ResponseCategory.DEFLECTION
        assert len(analysis.deflection_phrases_found) > 0

    def test_no_deflection_in_good_response(self, analyzer: ResponseQualityAnalyzer):
        """Test that good responses don't trigger deflection detection."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=SampleResponses.GOOD_CALL_INFO,
        )
        assert analysis.category != ResponseCategory.DEFLECTION
        assert len(analysis.deflection_phrases_found) == 0


# ============================================================================
# Test Class: Query Type Inference
# ============================================================================

class TestQueryTypeInference:
    """Test query type inference from user queries."""

    @pytest.mark.parametrize("query,expected_type", [
        ("Tell me about HORIZON-CL5-2026-D3-01", QueryType.CALL_INFO),
        ("What is the HORIZON-CL4-2025-DATA-01 call about?", QueryType.CALL_INFO),
        ("Compare EIC vs ERC", QueryType.PROGRAMME_COMPARISON),
        ("Difference between RIA and IA", QueryType.PROGRAMME_COMPARISON),
        ("Can SMEs apply to Horizon Europe?", QueryType.ELIGIBILITY_FAQ),
        ("Who is eligible for ERC grants?", QueryType.ELIGIBILITY_FAQ),
        ("What is the typical budget for a RIA?", QueryType.BUDGET_BENCHMARK),
        ("Average funding for Cluster 5", QueryType.BUDGET_BENCHMARK),
        ("Find partners with hydrogen experience", QueryType.PARTNER_DISCOVERY),
        ("Organizations working on AI in Germany", QueryType.PARTNER_DISCOVERY),
        ("Find quantum computing projects", QueryType.PROJECT_SEARCH),
        ("Search funded projects about climate", QueryType.PROJECT_SEARCH),
        ("What is the typical consortium size?", QueryType.CONSORTIUM_PATTERN),
        ("How many partners for a Health IA?", QueryType.CONSORTIUM_PATTERN),
        ("What is the success rate for RIA?", QueryType.STATISTICS),
        ("Hello, how are you?", QueryType.GENERAL),
    ])
    def test_query_type_inference(
        self, analyzer: ResponseQualityAnalyzer, query: str, expected_type: QueryType
    ):
        """Test query type inference accuracy."""
        inferred_type = analyzer._infer_query_type(query.lower())
        assert inferred_type == expected_type


# ============================================================================
# Test Class: Content Requirements Validation
# ============================================================================

class TestContentRequirements:
    """Test content requirement checking for different query types."""

    def test_call_info_complete_requirements(self, analyzer: ResponseQualityAnalyzer):
        """Test that complete call info response meets all requirements."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=SampleResponses.GOOD_CALL_INFO,
        )
        assert analysis.query_type == QueryType.CALL_INFO
        assert len(analysis.elements_found) >= 4
        assert "call_id" in analysis.elements_found or "deadline" in analysis.elements_found

    def test_call_info_missing_requirements(self, analyzer: ResponseQualityAnalyzer):
        """Test that partial call info response has missing elements."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=SampleResponses.PARTIAL_CALL_INFO,
        )
        assert len(analysis.missing_elements) > 0

    def test_comparison_complete_requirements(self, analyzer: ResponseQualityAnalyzer):
        """Test that complete comparison response meets requirements."""
        analysis = analyzer.analyze(
            query="Compare EIC vs ERC",
            response=SampleResponses.GOOD_PROGRAMME_COMPARISON,
        )
        assert analysis.query_type == QueryType.PROGRAMME_COMPARISON
        # Good comparison should have most elements
        assert len(analysis.elements_found) >= 2

    def test_eligibility_complete_requirements(self, analyzer: ResponseQualityAnalyzer):
        """Test that complete eligibility response meets requirements."""
        analysis = analyzer.analyze(
            query="Can SMEs apply to RIA?",
            response=SampleResponses.GOOD_ELIGIBILITY,
        )
        assert analysis.query_type == QueryType.ELIGIBILITY_FAQ
        assert analysis.score >= 70


# ============================================================================
# Test Class: Quality Scoring
# ============================================================================

class TestQualityScoring:
    """Test quality scoring accuracy."""

    def test_good_response_high_score(self, analyzer: ResponseQualityAnalyzer):
        """Test that good responses get high scores."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=SampleResponses.GOOD_CALL_INFO,
        )
        assert analysis.score >= 70
        assert analysis.category in [ResponseCategory.COMPLETE, ResponseCategory.PARTIAL]

    def test_deflecting_response_low_score(self, analyzer: ResponseQualityAnalyzer):
        """Test that deflecting responses get low scores."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=SampleResponses.DEFLECTING_CALL_INFO,
        )
        assert analysis.score < 50
        assert analysis.category == ResponseCategory.DEFLECTION

    def test_empty_response_zero_score(self, analyzer: ResponseQualityAnalyzer):
        """Test that empty responses get zero or very low scores."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=SampleResponses.EMPTY_RESPONSE,
        )
        assert analysis.score <= 10
        assert analysis.category == ResponseCategory.EMPTY

    def test_partial_response_medium_score(self, analyzer: ResponseQualityAnalyzer):
        """Test that partial responses get medium scores."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=SampleResponses.PARTIAL_CALL_INFO,
        )
        assert 30 <= analysis.score <= 70

    def test_score_penalizes_deflection_heavily(self, analyzer: ResponseQualityAnalyzer):
        """Test that deflection phrases heavily penalize the score."""
        analysis = analyzer.analyze(
            query="What is the budget for RIA?",
            response=SampleResponses.DEFLECTING_BUDGET,
        )
        assert analysis.score < 50

    def test_score_rewards_complete_elements(self, analyzer: ResponseQualityAnalyzer):
        """Test that having all required elements improves score."""
        analysis = analyzer.analyze(
            query="What is the budget for Cluster 5 RIA?",
            response=SampleResponses.GOOD_BUDGET_BENCHMARK,
        )
        assert analysis.score >= 70


# ============================================================================
# Test Class: Response Categorization
# ============================================================================

class TestResponseCategorization:
    """Test response categorization accuracy."""

    def test_complete_categorization(self, analyzer: ResponseQualityAnalyzer):
        """Test correct categorization of complete responses."""
        analysis = analyzer.analyze(
            query="Find partners with hydrogen experience in Germany",
            response=SampleResponses.GOOD_PARTNER_DISCOVERY,
        )
        assert analysis.category in [ResponseCategory.COMPLETE, ResponseCategory.PARTIAL]

    def test_deflection_categorization(self, analyzer: ResponseQualityAnalyzer):
        """Test correct categorization of deflecting responses."""
        analysis = analyzer.analyze(
            query="Find partners with hydrogen experience",
            response=SampleResponses.DEFLECTING_PARTNER,
        )
        assert analysis.category == ResponseCategory.DEFLECTION

    def test_empty_categorization(self, analyzer: ResponseQualityAnalyzer):
        """Test correct categorization of empty responses."""
        analysis = analyzer.analyze(
            query="Tell me about a call",
            response="",
        )
        assert analysis.category == ResponseCategory.EMPTY

    def test_short_deflection_categorization(self, analyzer: ResponseQualityAnalyzer):
        """Test categorization of short deflecting responses."""
        analysis = analyzer.analyze(
            query="What is the success rate?",
            response=SampleResponses.SHORT_DEFLECTION,
        )
        assert analysis.category in [ResponseCategory.DEFLECTION, ResponseCategory.EMPTY]


# ============================================================================
# Test Class: Comprehensive Query Tests (25+ queries)
# ============================================================================

class TestComprehensiveQueries:
    """
    Comprehensive test suite with 25+ queries covering all query types.

    These tests validate that the analyzer correctly identifies quality issues
    across different types of queries and responses.
    """

    # 5 Call ID Queries
    @pytest.mark.parametrize("query,response,min_score,expected_category", [
        (
            "Tell me about HORIZON-CL5-2026-D3-01",
            SampleResponses.GOOD_CALL_INFO,
            70,
            ResponseCategory.COMPLETE,
        ),
        (
            "What is HORIZON-CL4-2025-DATA-01?",
            SampleResponses.DEFLECTING_CALL_INFO,
            0,
            ResponseCategory.DEFLECTION,
        ),
        (
            "Details for HORIZON-HLTH-2025-DISEASE-01",
            SampleResponses.PARTIAL_CALL_INFO,
            30,
            ResponseCategory.PARTIAL,
        ),
        (
            "HORIZON-CL6-2026-BIODIV-01 scope",
            SampleResponses.GOOD_CALL_INFO,
            70,
            ResponseCategory.COMPLETE,
        ),
        (
            "What is the deadline for HORIZON-EIC-2025-PATHFINDER?",
            SampleResponses.DEFLECTING_CALL_INFO,
            0,
            ResponseCategory.DEFLECTION,
        ),
    ])
    def test_call_id_queries(
        self, analyzer: ResponseQualityAnalyzer, query: str, response: str,
        min_score: int, expected_category: ResponseCategory
    ):
        """Test call ID queries (5 queries)."""
        analysis = analyzer.analyze(query=query, response=response)
        if min_score > 0:
            assert analysis.score >= min_score
        assert analysis.category == expected_category

    # 5 Programme Comparison Queries
    @pytest.mark.parametrize("query,response,min_score,expected_category", [
        (
            "Compare EIC Accelerator vs ERC",
            SampleResponses.GOOD_PROGRAMME_COMPARISON,
            70,
            ResponseCategory.COMPLETE,
        ),
        (
            "Difference between RIA and IA",
            SampleResponses.DEFLECTING_COMPARISON,
            0,
            ResponseCategory.DEFLECTION,
        ),
        (
            "ERC vs MSCA which is better",
            SampleResponses.GOOD_PROGRAMME_COMPARISON,
            70,
            ResponseCategory.COMPLETE,
        ),
        (
            "Compare Horizon Europe with Horizon 2020",
            SampleResponses.DEFLECTING_COMPARISON,
            0,
            ResponseCategory.DEFLECTION,
        ),
        (
            "EIC Pathfinder vs EIC Transition",
            SampleResponses.GOOD_PROGRAMME_COMPARISON,
            65,
            ResponseCategory.COMPLETE,
        ),
    ])
    def test_programme_comparison_queries(
        self, analyzer: ResponseQualityAnalyzer, query: str, response: str,
        min_score: int, expected_category: ResponseCategory
    ):
        """Test programme comparison queries (5 queries)."""
        analysis = analyzer.analyze(query=query, response=response)
        if min_score > 0:
            assert analysis.score >= min_score
        assert analysis.category == expected_category

    # 5 Eligibility/FAQ Queries
    @pytest.mark.parametrize("query,response,min_score,expected_category", [
        (
            "Can SMEs apply to Horizon Europe?",
            SampleResponses.GOOD_ELIGIBILITY,
            70,
            ResponseCategory.COMPLETE,
        ),
        (
            "Who is eligible for ERC grants?",
            SampleResponses.DEFLECTING_ELIGIBILITY,
            0,
            ResponseCategory.DEFLECTION,
        ),
        (
            "Requirements for RIA consortium",
            SampleResponses.GOOD_ELIGIBILITY,
            65,
            ResponseCategory.COMPLETE,
        ),
        (
            "Can US organizations participate?",
            SampleResponses.DEFLECTING_ELIGIBILITY,
            0,
            ResponseCategory.DEFLECTION,
        ),
        (
            "What are the rules for subcontracting?",
            SampleResponses.GOOD_ELIGIBILITY,
            60,
            ResponseCategory.COMPLETE,
        ),
    ])
    def test_eligibility_faq_queries(
        self, analyzer: ResponseQualityAnalyzer, query: str, response: str,
        min_score: int, expected_category: ResponseCategory
    ):
        """Test eligibility/FAQ queries (5 queries)."""
        analysis = analyzer.analyze(query=query, response=response)
        if min_score > 0:
            assert analysis.score >= min_score
        assert analysis.category == expected_category

    # 3 Budget Benchmark Queries
    @pytest.mark.parametrize("query,response,min_score,expected_category", [
        (
            "What is typical budget for Horizon RIA in Cluster 5?",
            SampleResponses.GOOD_BUDGET_BENCHMARK,
            70,
            ResponseCategory.COMPLETE,
        ),
        (
            "Average funding for Health cluster IA",
            SampleResponses.DEFLECTING_BUDGET,
            0,
            ResponseCategory.DEFLECTION,
        ),
        (
            "Budget range for CSA projects",
            SampleResponses.GOOD_BUDGET_BENCHMARK,
            65,
            ResponseCategory.COMPLETE,
        ),
    ])
    def test_budget_benchmark_queries(
        self, analyzer: ResponseQualityAnalyzer, query: str, response: str,
        min_score: int, expected_category: ResponseCategory
    ):
        """Test budget benchmark queries (3 queries)."""
        analysis = analyzer.analyze(query=query, response=response)
        if min_score > 0:
            assert analysis.score >= min_score
        assert analysis.category == expected_category

    # 3 Partner Discovery Queries
    @pytest.mark.parametrize("query,response,min_score,expected_category", [
        (
            "Find German SMEs with hydrogen experience",
            SampleResponses.GOOD_PARTNER_DISCOVERY,
            70,
            ResponseCategory.COMPLETE,
        ),
        (
            "Organizations working on AI in France",
            SampleResponses.DEFLECTING_PARTNER,
            0,
            ResponseCategory.DEFLECTION,
        ),
        (
            "Partners with quantum computing expertise",
            SampleResponses.GOOD_PARTNER_DISCOVERY,
            65,
            ResponseCategory.COMPLETE,
        ),
    ])
    def test_partner_discovery_queries(
        self, analyzer: ResponseQualityAnalyzer, query: str, response: str,
        min_score: int, expected_category: ResponseCategory
    ):
        """Test partner discovery queries (3 queries)."""
        analysis = analyzer.analyze(query=query, response=response)
        if min_score > 0:
            assert analysis.score >= min_score
        assert analysis.category == expected_category

    # 2 Project Search Queries
    @pytest.mark.parametrize("query,response,min_score,expected_category", [
        (
            "Find quantum computing projects",
            SampleResponses.GOOD_PROJECT_SEARCH,
            70,
            ResponseCategory.COMPLETE,
        ),
        (
            "Search for climate adaptation projects",
            SampleResponses.DEFLECTING_PROJECT,
            0,
            ResponseCategory.DEFLECTION,
        ),
    ])
    def test_project_search_queries(
        self, analyzer: ResponseQualityAnalyzer, query: str, response: str,
        min_score: int, expected_category: ResponseCategory
    ):
        """Test project search queries (2 queries)."""
        analysis = analyzer.analyze(query=query, response=response)
        if min_score > 0:
            assert analysis.score >= min_score
        assert analysis.category == expected_category

    # 2 Consortium Pattern Queries
    @pytest.mark.parametrize("query,response,min_score,expected_category", [
        (
            "What is typical consortium size for Health IAs?",
            SampleResponses.GOOD_CONSORTIUM_PATTERN,
            70,
            ResponseCategory.COMPLETE,
        ),
        (
            "Partner mix for Climate cluster RIA",
            SampleResponses.GOOD_CONSORTIUM_PATTERN,
            65,
            ResponseCategory.COMPLETE,
        ),
    ])
    def test_consortium_pattern_queries(
        self, analyzer: ResponseQualityAnalyzer, query: str, response: str,
        min_score: int, expected_category: ResponseCategory
    ):
        """Test consortium pattern queries (2 queries)."""
        analysis = analyzer.analyze(query=query, response=response)
        assert analysis.score >= min_score
        assert analysis.category == expected_category


# ============================================================================
# Test Class: Recommendations
# ============================================================================

class TestRecommendations:
    """Test recommendation generation."""

    def test_deflection_recommendations(self, analyzer: ResponseQualityAnalyzer):
        """Test recommendations for deflecting responses."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=SampleResponses.DEFLECTING_CALL_INFO,
        )
        assert len(analysis.recommendations) > 0
        assert any("deflection" in rec.lower() for rec in analysis.recommendations)

    def test_missing_elements_recommendations(self, analyzer: ResponseQualityAnalyzer):
        """Test recommendations for missing elements."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=SampleResponses.PARTIAL_CALL_INFO,
        )
        if analysis.missing_elements:
            assert any("missing" in rec.lower() for rec in analysis.recommendations)

    def test_empty_recommendations(self, analyzer: ResponseQualityAnalyzer):
        """Test recommendations for empty responses."""
        analysis = analyzer.analyze(
            query="Tell me about a call",
            response=SampleResponses.EMPTY_RESPONSE,
        )
        assert len(analysis.recommendations) > 0


# ============================================================================
# Test Class: Tool Results Validation
# ============================================================================

class TestToolResultsValidation:
    """Test tool results validation."""

    def test_valid_tool_results(self, analyzer: ResponseQualityAnalyzer):
        """Test validation of valid tool results."""
        tool_results = {
            "search_funding_calls": {
                "success": True,
                "calls_found": 5,
                "calls": [{"id": "call1"}, {"id": "call2"}]
            }
        }
        score = analyzer._validate_tool_results(tool_results)
        assert score >= 80

    def test_empty_tool_results(self, analyzer: ResponseQualityAnalyzer):
        """Test validation of empty tool results."""
        tool_results = {
            "search_funding_calls": {
                "success": True,
                "calls_found": 0,
                "calls": []
            }
        }
        score = analyzer._validate_tool_results(tool_results)
        assert score < 100

    def test_failed_tool_results(self, analyzer: ResponseQualityAnalyzer):
        """Test validation of failed tool results."""
        tool_results = {
            "search_funding_calls": {
                "success": False,
                "error": "Database connection failed"
            }
        }
        score = analyzer._validate_tool_results(tool_results)
        assert score < 100


# ============================================================================
# Test Class: Quality Threshold
# ============================================================================

class TestQualityThreshold:
    """Test quality threshold checking."""

    def test_sufficient_quality(self, analyzer: ResponseQualityAnalyzer):
        """Test is_quality_sufficient for good responses."""
        analysis = analyzer.analyze(
            query="What is the budget for RIA?",
            response=SampleResponses.GOOD_BUDGET_BENCHMARK,
        )
        assert analyzer.is_quality_sufficient(analysis, min_score=70)

    def test_insufficient_quality_deflection(self, analyzer: ResponseQualityAnalyzer):
        """Test is_quality_sufficient rejects deflections."""
        analysis = analyzer.analyze(
            query="What is the budget for RIA?",
            response=SampleResponses.DEFLECTING_BUDGET,
        )
        assert not analyzer.is_quality_sufficient(analysis, min_score=70)

    def test_insufficient_quality_empty(self, analyzer: ResponseQualityAnalyzer):
        """Test is_quality_sufficient rejects empty responses."""
        analysis = analyzer.analyze(
            query="Tell me about a call",
            response=SampleResponses.EMPTY_RESPONSE,
        )
        assert not analyzer.is_quality_sufficient(analysis, min_score=70)

    def test_custom_threshold(self, analyzer: ResponseQualityAnalyzer):
        """Test is_quality_sufficient with custom threshold."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=SampleResponses.PARTIAL_CALL_INFO,
        )
        # With low threshold, partial might pass
        result_low = analyzer.is_quality_sufficient(analysis, min_score=30)
        # With high threshold, partial should fail
        result_high = analyzer.is_quality_sufficient(analysis, min_score=80)
        assert result_low != result_high or not result_high


# ============================================================================
# Test Class: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_response(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of very long responses."""
        long_response = SampleResponses.GOOD_CALL_INFO * 10
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=long_response,
        )
        assert analysis.score >= 50

    def test_response_with_special_characters(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of responses with special characters."""
        response = "Budget: €5M, Deadline: 2025-03-15, Type: RIA & IA"
        analysis = analyzer.analyze(
            query="Tell me about a call",
            response=response,
        )
        assert analysis is not None

    def test_unicode_response(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of unicode in responses."""
        response = "The project involves Müller GmbH from München, Germany. Budget: €5 million."
        analysis = analyzer.analyze(
            query="Find German partners",
            response=response,
        )
        assert analysis is not None

    def test_none_tool_results(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of None tool results."""
        analysis = analyzer.analyze(
            query="Tell me about a call",
            response=SampleResponses.GOOD_CALL_INFO,
            tool_results=None,
        )
        assert analysis is not None

    def test_empty_query(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of empty query."""
        analysis = analyzer.analyze(
            query="",
            response=SampleResponses.GOOD_CALL_INFO,
        )
        assert analysis is not None


# ============================================================================
# Test Class: Analysis Serialization
# ============================================================================

class TestAnalysisSerialization:
    """Test QualityAnalysis serialization."""

    def test_to_dict(self, analyzer: ResponseQualityAnalyzer):
        """Test conversion to dictionary."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=SampleResponses.GOOD_CALL_INFO,
        )
        d = analysis.to_dict()
        assert "score" in d
        assert "category" in d
        assert "confidence" in d
        assert "query_type" in d
        assert isinstance(d["category"], str)
        assert isinstance(d["query_type"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
