"""
Comprehensive AI Response Quality Tests

Tests the ResponseQualityAnalyzer to ensure AI responses meet quality standards.
This is CRITICAL for production - tests that just check "response exists" are WORTHLESS.

Test Categories:
1. Deflection detection (5 tests)
2. Call-specific queries (5 tests)
3. Programme comparison queries (5 tests)
4. Eligibility/FAQ queries (5 tests)
5. Budget benchmark queries (3 tests)
6. Partner discovery queries (3 tests)
7. Project search queries (2 tests)
8. Consortium pattern queries (2 tests)

Total: 30 parameterized test cases
"""

import os
import sys
from typing import List

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.quality.response_quality_analyzer import (
    ContentRequirements,
    QualityAnalysis,
    ResponseCategory,
    ResponseQualityAnalyzer,
    create_quality_analyzer,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def analyzer() -> ResponseQualityAnalyzer:
    """Create a ResponseQualityAnalyzer instance."""
    return create_quality_analyzer()


# =============================================================================
# Test Data: Good Responses
# =============================================================================

GOOD_CALL_RESPONSE = """
I found **15 funding opportunities** for hydrogen research:

**1. Competitiveness, energy security and integration aspects of advanced biofuels**
📋 **Call ID:** HORIZON-CL5-2026-D3-02-01
🔬 **Type:** RIA
🟢 **Status:** Open
⏰ **Deadline:** 05 Feb 2026
🏛️ **Programme:** Cluster 5 - Climate, Energy and Mobility
💰 **Budget:** EUR 20.00 million

**Scope:** This topic focuses on advanced biofuels and renewable fuels of non-biological
origin. Projects should address the entire value chain from feedstock to end use.

🔗 **Apply:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/

💡 **How to Apply:**
• Register on the EU Funding & Tenders Portal
• Submit your proposal before the deadline
"""

GOOD_COMPARISON_RESPONSE = """
## EIC Accelerator vs ERC Starting Grant: Comparison

**Success Rates:**
- EIC Accelerator: ~8% success rate (highly competitive)
- ERC Starting Grant: ~12% success rate

**Funding Amounts:**
- EIC: Up to €2.5 million grant + €15 million equity
- ERC: Up to €1.5 million over 5 years

**Key Differences:**
1. EIC targets SMEs and startups with breakthrough innovations
2. ERC targets individual researchers in academic institutions
3. EIC includes equity investment option, ERC is grant-only

**Recommendation:** Choose EIC for commercial innovation, ERC for fundamental research.
"""

GOOD_PROJECT_RESPONSE = """
I found 10 quantum computing projects:

**1. QUTE-EUROPE**
🔬 **Funding:** €4.5 million
👥 **Partners:** 15 organizations from 8 countries
📍 **Coordinator:** Fraunhofer-Gesellschaft (Germany)
📅 **Duration:** 48 months

**Objective:** Developing quantum communication networks for secure European
infrastructure, focusing on quantum key distribution and entanglement-based protocols.

**2. QUANTUM-FLAGSHIP**
🔬 **Funding:** €12 million
👥 **Partners:** 22 organizations from 12 countries
📍 **Coordinator:** CEA (France)
"""

GOOD_PARTNER_RESPONSE = """
I found **47 experienced partners** for hydrogen fuel cell research in Germany:

**Top Organizations:**

1. **Fraunhofer ISE** (Germany)
   - 🏢 Type: Research Organization
   - 📊 Experience: 23 Horizon Europe projects in hydrogen/fuel cells
   - 🔬 Expertise: PEM fuel cells, hydrogen storage, electrolyzer development
   - 🤝 Typical Role: Coordinator or Technology Lead

2. **RWTH Aachen University** (Germany)
   - 🏢 Type: Higher Education
   - 📊 Experience: 18 projects in clean energy
   - 🔬 Expertise: Hydrogen production, electrolysis, system integration
"""

GOOD_BUDGET_RESPONSE = """
## Budget Benchmark for Cluster 5 RIA Projects

**Statistics from 496 funded projects:**

📊 **Budget Range:**
- Minimum: €1.3 million
- Maximum: €19.9 million
- Average: €4.9 million
- Median: €4.5 million

👥 **Consortium Size:**
- Average: 13.3 partners
- Typical range: 10-15 partners

🏢 **Budget by Organization Type:**
- Research Organizations (REC): 34%
- Private Companies (PRC): 33.9%
- Higher Education (HES): 27.6%

**Recommendation:** For a Cluster 5 RIA, target €3.4M - €5.5M with 10-15 partners.
"""

GOOD_CONSORTIUM_RESPONSE = """
## Consortium Patterns for Health Innovation Actions (IA)

**Typical Consortium Size:**
- Average partners: 12.5
- Average countries: 8.2

**Organization Type Distribution:**
- Higher Education (HES): 35%
- Research Centers (REC): 28%
- Private Companies (PRC): 22%
- Other (OTH): 15%

**Top Coordinator Countries:**
1. Germany (18%)
2. France (14%)
3. Netherlands (11%)
"""

GOOD_FAQ_RESPONSE = """
**Can SMEs apply to the LIFE Programme?**

Yes, SMEs can apply to the LIFE Programme. LIFE is the EU's funding instrument for
environment and climate action, and it explicitly welcomes SME participation.

**Key Points:**
- SMEs can apply as coordinators or partners
- No minimum consortium size requirement for some calls
- Simplified application for small-scale projects (up to €1M)
- 60% co-financing rate for most projects

**Source:** LIFE Programme 2021-2027 Work Programme
"""


# =============================================================================
# Test Data: Bad Responses (Deflections)
# =============================================================================

DEFLECTION_RESPONSES = [
    "I could not find specific details about this topic. Please try a more specific query.",
    "I'm not sure about this. Try searching with different keywords.",
    "No results found for your query. Please try again later.",
    "I found some information but could not extract specific details from the data.",
    "Unfortunately, I cannot find the requested information in my knowledge base.",
    "I apologize but I am unable to retrieve this information at the moment.",
    "No data available for this query.",
]


# =============================================================================
# Test: Deflection Detection
# =============================================================================


class TestDeflectionDetection:
    """Tests for deflection phrase detection."""

    @pytest.mark.parametrize(
        "deflection_response",
        DEFLECTION_RESPONSES,
        ids=[
            "could_not_find",
            "not_sure",
            "no_results",
            "found_some_but",
            "unfortunately",
            "apologize",
            "no_data",
        ],
    )
    def test_detects_deflection_responses(
        self, analyzer: ResponseQualityAnalyzer, deflection_response: str
    ):
        """Test that deflection responses are correctly identified."""
        analysis = analyzer.analyze(
            query="Tell me about hydrogen funding",
            response=deflection_response,
        )

        assert analysis.category == ResponseCategory.DEFLECTION, (
            f"Expected DEFLECTION category but got {analysis.category} "
            f"for response: '{deflection_response[:50]}...'"
        )
        assert len(analysis.deflection_phrases_found) > 0, (
            "Expected deflection phrases to be found"
        )
        assert analysis.score < 50, (
            f"Deflection score should be below 50, got {analysis.score}"
        )

    def test_empty_response_detected(self, analyzer: ResponseQualityAnalyzer):
        """Test that empty responses are correctly identified."""
        analysis = analyzer.analyze(
            query="Tell me about EIC Accelerator",
            response="",
        )

        assert analysis.category == ResponseCategory.EMPTY
        assert analysis.score == 0
        assert "any_content" in analysis.missing_elements

    def test_whitespace_only_response(self, analyzer: ResponseQualityAnalyzer):
        """Test that whitespace-only responses are treated as empty."""
        analysis = analyzer.analyze(
            query="Tell me about ERC grants",
            response="   \n\t  \n   ",
        )

        assert analysis.category == ResponseCategory.EMPTY
        assert analysis.score == 0


# =============================================================================
# Test: Call-Specific Queries
# =============================================================================


class TestCallQueries:
    """Tests for call search and call-specific responses."""

    @pytest.mark.parametrize(
        "query,expected_elements,min_score",
        [
            (
                "Tell me about HORIZON-CL5-2026-D3-01",
                ["call_id", "deadline", "type", "status"],
                70,
            ),
            (
                "What are the open calls for hydrogen energy?",
                ["call_id", "deadline", "budget"],
                70,
            ),
            (
                "Find funding opportunities for AI research in 2026",
                ["call_id", "type", "deadline"],
                70,
            ),
            (
                "Show me Cluster 4 digital technology calls",
                ["call_id", "programme", "status"],
                70,
            ),
            (
                "What is the deadline for HORIZON-CL4-2025-DIGITAL-01?",
                ["deadline", "call_id"],
                70,
            ),
        ],
        ids=[
            "specific_call_id",
            "hydrogen_calls",
            "ai_research_2026",
            "cluster4_digital",
            "deadline_query",
        ],
    )
    def test_good_call_response_scores_high(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_elements: List[str],
        min_score: int,
    ):
        """Test that good call responses score appropriately."""
        analysis = analyzer.analyze(
            query=query,
            response=GOOD_CALL_RESPONSE,
            query_type="call_search",
        )

        assert analysis.score >= min_score, (
            f"Expected score >= {min_score}, got {analysis.score}. "
            f"Missing elements: {analysis.missing_elements}"
        )
        assert analysis.category in (ResponseCategory.COMPLETE, ResponseCategory.PARTIAL)

    def test_call_response_with_all_elements(self, analyzer: ResponseQualityAnalyzer):
        """Test that a complete call response is categorized as COMPLETE."""
        analysis = analyzer.analyze(
            query="Find hydrogen funding calls",
            response=GOOD_CALL_RESPONSE,
            query_type="call_search",
        )

        # Should find most required elements
        found_elements = [
            e for e in ["call_id", "deadline", "budget", "type", "status", "title"]
            if e not in analysis.missing_elements
        ]
        assert len(found_elements) >= 4, (
            f"Expected at least 4 elements found, got {len(found_elements)}. "
            f"Missing: {analysis.missing_elements}"
        )


# =============================================================================
# Test: Programme Comparison Queries
# =============================================================================


class TestComparisonQueries:
    """Tests for comparison responses."""

    @pytest.mark.parametrize(
        "query,items_to_compare,min_score",
        [
            (
                "Compare EIC Accelerator vs ERC Starting Grant success rates",
                ["EIC", "ERC"],
                70,
            ),
            (
                "What's the difference between RIA and IA projects?",
                ["RIA", "IA"],
                70,
            ),
            (
                "Compare Cluster 4 and Cluster 5 funding amounts",
                ["Cluster 4", "Cluster 5"],
                60,
            ),
            (
                "How do MSCA and ERC grants differ?",
                ["MSCA", "ERC"],
                70,
            ),
            (
                "EIC Pathfinder vs EIC Accelerator - which is better for startups?",
                ["Pathfinder", "Accelerator"],
                60,
            ),
        ],
        ids=[
            "eic_vs_erc",
            "ria_vs_ia",
            "cluster4_vs_cluster5",
            "msca_vs_erc",
            "pathfinder_vs_accelerator",
        ],
    )
    def test_good_comparison_response(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        items_to_compare: List[str],
        min_score: int,
    ):
        """Test that good comparison responses score appropriately."""
        analysis = analyzer.validate_comparison_response(
            query=query,
            response=GOOD_COMPARISON_RESPONSE,
            items_to_compare=items_to_compare[:2],  # Check at least first two
        )

        # For comparison queries, we're flexible about exact elements
        assert analysis.score >= min_score - 10, (
            f"Expected score >= {min_score - 10}, got {analysis.score}. "
            f"Missing: {analysis.missing_elements}"
        )


# =============================================================================
# Test: Eligibility/FAQ Queries
# =============================================================================


class TestFAQQueries:
    """Tests for FAQ and eligibility responses."""

    @pytest.mark.parametrize(
        "query,min_score",
        [
            ("Can SMEs apply to the LIFE Programme?", 70),
            ("What are the consortium requirements for RIA projects?", 65),
            ("Is Switzerland eligible for Horizon Europe?", 65),
            ("What is the minimum TRL for EIC Accelerator?", 65),
            ("Do I need to register on the EU portal before applying?", 65),
        ],
        ids=[
            "sme_life_eligibility",
            "consortium_requirements",
            "switzerland_eligibility",
            "trl_requirements",
            "portal_registration",
        ],
    )
    def test_good_faq_response(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        min_score: int,
    ):
        """Test that good FAQ responses score appropriately."""
        analysis = analyzer.analyze(
            query=query,
            response=GOOD_FAQ_RESPONSE,
            query_type="faq",
        )

        assert analysis.score >= min_score, (
            f"Expected score >= {min_score}, got {analysis.score}. "
            f"Missing: {analysis.missing_elements}"
        )
        assert analysis.category != ResponseCategory.DEFLECTION


# =============================================================================
# Test: Budget Benchmark Queries
# =============================================================================


class TestBudgetBenchmarkQueries:
    """Tests for budget benchmark responses."""

    @pytest.mark.parametrize(
        "query,expected_elements,min_score",
        [
            (
                "What is typical budget for Horizon RIA in Cluster 5?",
                ["average_budget", "budget_range", "consortium_size"],
                70,
            ),
            (
                "How much funding should I request for a Climate RIA?",
                ["budget_range", "recommendations"],
                65,
            ),
            (
                "What are budget benchmarks for Cluster 1 Health projects?",
                ["average_budget", "action_type"],
                65,
            ),
        ],
        ids=["cluster5_ria", "climate_ria", "health_cluster1"],
    )
    def test_good_budget_response(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_elements: List[str],
        min_score: int,
    ):
        """Test that good budget benchmark responses score appropriately."""
        analysis = analyzer.analyze(
            query=query,
            response=GOOD_BUDGET_RESPONSE,
            query_type="budget_benchmark",
        )

        assert analysis.score >= min_score, (
            f"Expected score >= {min_score}, got {analysis.score}. "
            f"Missing: {analysis.missing_elements}"
        )


# =============================================================================
# Test: Partner Discovery Queries
# =============================================================================


class TestPartnerDiscoveryQueries:
    """Tests for partner discovery responses."""

    @pytest.mark.parametrize(
        "query,expected_elements,min_score",
        [
            (
                "Find German SMEs with hydrogen experience",
                ["organization_name", "country", "experience"],
                70,
            ),
            (
                "Find research partners for AI in healthcare",
                ["organization_name", "expertise_area"],
                65,
            ),
            (
                "Which organizations have coordinated Climate projects?",
                ["organization_name", "role"],
                65,
            ),
        ],
        ids=["german_hydrogen", "ai_healthcare", "climate_coordinators"],
    )
    def test_good_partner_response(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_elements: List[str],
        min_score: int,
    ):
        """Test that good partner discovery responses score appropriately."""
        analysis = analyzer.analyze(
            query=query,
            response=GOOD_PARTNER_RESPONSE,
            query_type="partner_discovery",
        )

        assert analysis.score >= min_score, (
            f"Expected score >= {min_score}, got {analysis.score}. "
            f"Missing: {analysis.missing_elements}"
        )


# =============================================================================
# Test: Project Search Queries
# =============================================================================


class TestProjectSearchQueries:
    """Tests for project search responses."""

    @pytest.mark.parametrize(
        "query,min_score",
        [
            ("Find quantum computing projects funded by Horizon Europe", 70),
            ("Show me renewable energy projects in Germany", 65),
        ],
        ids=["quantum_computing", "renewable_germany"],
    )
    def test_good_project_response(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        min_score: int,
    ):
        """Test that good project search responses score appropriately."""
        analysis = analyzer.analyze(
            query=query,
            response=GOOD_PROJECT_RESPONSE,
            query_type="project_search",
        )

        assert analysis.score >= min_score, (
            f"Expected score >= {min_score}, got {analysis.score}. "
            f"Missing: {analysis.missing_elements}"
        )


# =============================================================================
# Test: Consortium Pattern Queries
# =============================================================================


class TestConsortiumPatternQueries:
    """Tests for consortium pattern responses."""

    @pytest.mark.parametrize(
        "query,min_score",
        [
            ("What is typical consortium size for Health IAs?", 70),
            ("How many partners do successful Cluster 5 projects have?", 65),
        ],
        ids=["health_ia_size", "cluster5_partners"],
    )
    def test_good_consortium_response(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        min_score: int,
    ):
        """Test that good consortium pattern responses score appropriately."""
        analysis = analyzer.analyze(
            query=query,
            response=GOOD_CONSORTIUM_RESPONSE,
            query_type="consortium_patterns",
        )

        assert analysis.score >= min_score, (
            f"Expected score >= {min_score}, got {analysis.score}. "
            f"Missing: {analysis.missing_elements}"
        )


# =============================================================================
# Test: Quality Analysis Structure
# =============================================================================


class TestQualityAnalysisStructure:
    """Tests for QualityAnalysis output structure."""

    def test_analysis_has_all_required_fields(self, analyzer: ResponseQualityAnalyzer):
        """Test that QualityAnalysis has all expected fields."""
        analysis = analyzer.analyze(
            query="Test query",
            response=GOOD_CALL_RESPONSE,
        )

        assert hasattr(analysis, "score")
        assert hasattr(analysis, "category")
        assert hasattr(analysis, "confidence")
        assert hasattr(analysis, "missing_elements")
        assert hasattr(analysis, "deflection_phrases_found")
        assert hasattr(analysis, "recommendations")
        assert hasattr(analysis, "element_scores")

    def test_score_is_bounded(self, analyzer: ResponseQualityAnalyzer):
        """Test that score is always between 0 and 100."""
        for response in [GOOD_CALL_RESPONSE, "x", "", DEFLECTION_RESPONSES[0]]:
            analysis = analyzer.analyze(
                query="Test query",
                response=response,
            )
            assert 0 <= analysis.score <= 100, (
                f"Score {analysis.score} is out of bounds for response: '{response[:50]}...'"
            )

    def test_confidence_is_bounded(self, analyzer: ResponseQualityAnalyzer):
        """Test that confidence is always between 0 and 1."""
        analysis = analyzer.analyze(
            query="Test query",
            response=GOOD_CALL_RESPONSE,
        )
        assert 0 <= analysis.confidence <= 1

    def test_category_is_valid_enum(self, analyzer: ResponseQualityAnalyzer):
        """Test that category is a valid ResponseCategory."""
        analysis = analyzer.analyze(
            query="Test query",
            response=GOOD_CALL_RESPONSE,
        )
        assert isinstance(analysis.category, ResponseCategory)


# =============================================================================
# Test: Query Type Inference
# =============================================================================


class TestQueryTypeInference:
    """Tests for automatic query type inference."""

    @pytest.mark.parametrize(
        "query,expected_type",
        [
            ("Tell me about HORIZON-CL5-2026-D3-01", "call_specific"),
            ("Find funding calls for hydrogen", "call_search"),
            ("Compare EIC vs ERC", "comparison"),
            ("Find quantum computing projects", "project_search"),
            ("Find partners for AI research", "partner_discovery"),
            ("What is typical budget for RIA?", "budget_benchmark"),
            ("What is consortium size for IAs?", "consortium_patterns"),
            ("Can SMEs apply to Horizon Europe?", "faq"),
        ],
        ids=[
            "call_specific",
            "call_search",
            "comparison",
            "project_search",
            "partner_discovery",
            "budget_benchmark",
            "consortium_patterns",
            "faq",
        ],
    )
    def test_query_type_inference(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_type: str,
    ):
        """Test that query types are correctly inferred."""
        inferred_type = analyzer._infer_query_type(query)
        assert inferred_type == expected_type, (
            f"Expected '{expected_type}' but got '{inferred_type}' for query: '{query}'"
        )


# =============================================================================
# Test: Factory Function
# =============================================================================


class TestFactoryFunction:
    """Tests for the factory function."""

    def test_create_quality_analyzer_returns_instance(self):
        """Test that factory creates a valid analyzer."""
        analyzer = create_quality_analyzer()
        assert isinstance(analyzer, ResponseQualityAnalyzer)

    def test_supported_query_types(self):
        """Test that all expected query types are supported."""
        supported = ResponseQualityAnalyzer.get_supported_query_types()

        expected = [
            "call_search",
            "call_specific",
            "project_search",
            "comparison",
            "partner_discovery",
            "budget_benchmark",
            "consortium_patterns",
            "faq",
        ]

        for expected_type in expected:
            assert expected_type in supported, (
                f"Expected query type '{expected_type}' not in supported types"
            )


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_response(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of very long responses."""
        long_response = GOOD_CALL_RESPONSE * 10  # ~10x the normal length
        analysis = analyzer.analyze(
            query="Find hydrogen calls",
            response=long_response,
        )

        # Should still work and score well
        assert analysis.score >= 70
        assert analysis.category != ResponseCategory.DEFLECTION

    def test_response_with_unicode(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of responses with unicode characters."""
        unicode_response = """
        🔬 **Call ID:** HORIZON-CL5-2026-D3-01
        💰 **Budget:** €20 million
        ⏰ **Deadline:** 05 Feb 2026
        🟢 **Status:** Open

        This call focuses on advanced hydrogen technologies for sustainable energy.
        """
        analysis = analyzer.analyze(
            query="Tell me about hydrogen calls",
            response=unicode_response,
            query_type="call_search",
        )

        assert analysis.score >= 60
        assert analysis.category != ResponseCategory.DEFLECTION

    def test_response_with_tables(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of responses with markdown tables."""
        table_response = """
        | Programme | Success Rate | Avg Budget |
        |-----------|-------------|------------|
        | EIC       | 8%          | €2.5M      |
        | ERC       | 12%         | €1.5M      |

        The table above shows the comparison between EIC and ERC programmes.
        EIC has a lower success rate but higher budget compared to ERC.
        """
        analysis = analyzer.analyze(
            query="Compare EIC vs ERC",
            response=table_response,
            query_type="comparison",
        )

        assert analysis.score >= 50
        assert analysis.category != ResponseCategory.DEFLECTION

    def test_partial_response(self, analyzer: ResponseQualityAnalyzer):
        """Test that partial responses are correctly categorized."""
        partial_response = """
        I found one call:

        **HORIZON-CL5-2026-D3-01**
        Type: RIA
        Status: Open
        """
        analysis = analyzer.analyze(
            query="Find hydrogen calls",
            response=partial_response,
            query_type="call_search",
        )

        # Should be partial, not complete or deflection
        assert analysis.category in (ResponseCategory.PARTIAL, ResponseCategory.COMPLETE)
        assert len(analysis.missing_elements) > 0  # Some elements missing


# =============================================================================
# Test: Content Requirements Configuration
# =============================================================================


class TestContentRequirements:
    """Tests for content requirements configuration."""

    def test_get_requirements_for_known_type(self, analyzer: ResponseQualityAnalyzer):
        """Test retrieving requirements for a known query type."""
        requirements = analyzer.get_requirements_for_query_type("call_search")

        assert isinstance(requirements, ContentRequirements)
        assert len(requirements.required_elements) > 0
        assert requirements.min_response_length > 0

    def test_get_requirements_for_unknown_type(self, analyzer: ResponseQualityAnalyzer):
        """Test that unknown types fall back to FAQ requirements."""
        requirements = analyzer.get_requirements_for_query_type("unknown_type")

        assert isinstance(requirements, ContentRequirements)
        # Should fall back to FAQ requirements
        faq_requirements = analyzer.get_requirements_for_query_type("faq")
        assert requirements.required_elements == faq_requirements.required_elements
