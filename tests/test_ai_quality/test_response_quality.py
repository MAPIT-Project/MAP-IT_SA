"""Comprehensive tests for AI response quality analysis.

This module tests the ResponseQualityAnalyzer to ensure it correctly:
- Detects deflection patterns in AI responses
- Validates required content elements are present
- Calculates appropriate quality scores
- Categorizes responses correctly

The tests cover 25+ query types across different categories:
- Call ID queries (5)
- Programme comparison queries (5)
- Eligibility/FAQ queries (5)
- Budget benchmark queries (3)
- Partner discovery queries (3)
- Project search queries (2)
- Consortium pattern queries (2)
"""

import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from app.services.quality import (
    QualityAnalysis,
    QueryType,
    ResponseCategory,
    ResponseQualityAnalyzer,
    get_analyzer,
)


class TestResponseQualityAnalyzerUnit:
    """Unit tests for ResponseQualityAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create a fresh analyzer instance for each test."""
        return ResponseQualityAnalyzer()

    # ==================== Deflection Detection Tests ====================

    def test_detects_could_not_find_deflection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of 'could not find' deflection phrase."""
        response = "I could not find any specific information about this call."
        analysis = analyzer.analyze("Tell me about HORIZON-CL5-2026-D3-01", response)

        assert "could not find" in analysis.deflection_phrases_found
        assert analysis.category == ResponseCategory.DEFLECTION
        assert analysis.score < 50

    def test_detects_no_results_found_deflection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of 'no results found' deflection phrase."""
        response = (
            "No results found for your query. I was unable to retrieve any data. "
            "Please try a different search."
        )
        analysis = analyzer.analyze("Find hydrogen funding calls", response)

        assert "no results found" in analysis.deflection_phrases_found
        assert analysis.category == ResponseCategory.DEFLECTION

    def test_detects_multiple_deflections(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of multiple deflection phrases in one response."""
        response = (
            "I could not find specific information about this topic. "
            "Unfortunately, I was not able to locate relevant data. "
            "The search returned no results matching your query."
        )
        analysis = analyzer.analyze("What are the eligibility requirements?", response)

        assert len(analysis.deflection_phrases_found) >= 2
        assert analysis.category == ResponseCategory.DEFLECTION
        assert analysis.score <= 35  # Score is penalized but capped at minimum
        assert analysis.confidence >= 0.9

    def test_detects_subtle_deflection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of subtle deflection phrases."""
        response = (
            "I found some information but could not extract specific details "
            "about the budget requirements for this call."
        )
        analysis = analyzer.analyze("What is the budget for CL5 calls?", response)

        assert "found some information but" in analysis.deflection_phrases_found

    def test_does_not_flag_genuine_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that genuine responses are not flagged as deflections."""
        response = """
        The HORIZON-CL5-2026-D3-01 call focuses on advanced biofuels.

        **Key Details:**
        - **Type:** RIA (Research and Innovation Action)
        - **Deadline:** February 5, 2026
        - **Budget:** EUR 20 million
        - **Status:** Open for submissions

        This call aims to improve competitiveness and energy security through
        advanced biofuel research.
        """
        analysis = analyzer.analyze("Tell me about HORIZON-CL5-2026-D3-01", response)

        assert len(analysis.deflection_phrases_found) == 0
        assert analysis.category in [ResponseCategory.COMPLETE, ResponseCategory.PARTIAL]
        assert analysis.score >= 70

    # ==================== Query Type Detection Tests ====================

    def test_detects_call_details_query_type(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of call details query type."""
        query = "Tell me about HORIZON-CL5-2026-D3-01"
        detected = analyzer._detect_query_type(query)
        assert detected == QueryType.CALL_DETAILS

    def test_detects_call_search_query_type(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of call search query type."""
        query = "Find open funding calls for hydrogen research"
        detected = analyzer._detect_query_type(query)
        assert detected == QueryType.CALL_SEARCH

    def test_detects_project_search_query_type(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of project search query type."""
        query = "Find funded projects about quantum computing"
        detected = analyzer._detect_query_type(query)
        assert detected == QueryType.PROJECT_SEARCH

    def test_detects_comparison_query_type(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of programme comparison query type."""
        query = "Compare EIC Accelerator vs ERC success rates"
        detected = analyzer._detect_query_type(query)
        assert detected == QueryType.PROGRAMME_COMPARISON

    def test_detects_budget_query_type(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of budget benchmark query type."""
        query = "What is the typical budget for a Cluster 5 RIA project?"
        detected = analyzer._detect_query_type(query)
        assert detected == QueryType.BUDGET_BENCHMARK

    def test_detects_partner_query_type(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of partner discovery query type."""
        query = "Find German SMEs with experience in hydrogen fuel cells"
        detected = analyzer._detect_query_type(query)
        assert detected == QueryType.PARTNER_DISCOVERY

    def test_detects_consortium_query_type(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of consortium patterns query type."""
        query = "What is the typical consortium size for Health IAs?"
        detected = analyzer._detect_query_type(query)
        assert detected == QueryType.CONSORTIUM_PATTERNS

    def test_detects_eligibility_query_type(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of eligibility FAQ query type."""
        query = "Can SMEs apply to LIFE Programme?"
        detected = analyzer._detect_query_type(query)
        assert detected == QueryType.ELIGIBILITY_FAQ

    # ==================== Empty Response Tests ====================

    def test_empty_response_returns_zero_score(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that empty responses receive zero score."""
        analysis = analyzer.analyze("Tell me about RIA grants", "")

        assert analysis.score == 0
        assert analysis.category == ResponseCategory.EMPTY
        assert "any_content" in analysis.missing_elements

    def test_whitespace_only_response_returns_zero_score(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that whitespace-only responses receive zero score."""
        analysis = analyzer.analyze("Tell me about RIA grants", "   \n\t  ")

        assert analysis.score == 0
        assert analysis.category == ResponseCategory.EMPTY

    def test_very_short_response_penalized(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that very short responses are penalized."""
        # For call details, minimum is 300 chars
        short_response = "This is a call about hydrogen."
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01",
            short_response,
            query_type=QueryType.CALL_DETAILS,
        )

        assert analysis.score < 80  # Penalized for being too short

    # ==================== Required Content Tests ====================

    def test_call_details_missing_budget(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test detection of missing budget in call details."""
        response = """
        HORIZON-CL5-2026-D3-01 is a Research and Innovation Action (RIA).
        The deadline for submission is February 5, 2026.
        This call focuses on advanced biofuels and renewable energy.
        """
        # No budget information
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01",
            response,
            query_type=QueryType.CALL_DETAILS,
        )

        assert "budget" in analysis.missing_elements

    def test_call_details_complete_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test complete call details response is properly scored."""
        response = """
        HORIZON-CL5-2026-D3-01: Advanced Biofuels for Energy Security

        **Call Details:**
        - **Type:** RIA (Research and Innovation Action)
        - **Deadline:** February 5, 2026
        - **Budget:** EUR 20 million
        - **Status:** Open

        This call focuses on improving competitiveness and energy security through
        advanced biofuel technologies. Proposals should address innovative production
        methods and demonstrate potential for scale-up.
        """
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01",
            response,
            query_type=QueryType.CALL_DETAILS,
        )

        assert analysis.score >= 75
        assert analysis.category == ResponseCategory.COMPLETE
        assert len(analysis.missing_elements) == 0

    # ==================== Tool Result Validation Tests ====================

    def test_validate_empty_call_search_result(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test validation of empty call search results."""
        tool_result = {"calls": [], "calls_found": 0}
        is_valid, issues = analyzer.validate_tool_result("search_funding_calls", tool_result)

        assert not is_valid
        assert any("no results" in issue.lower() for issue in issues)

    def test_validate_error_in_tool_result(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test validation of tool result with error."""
        tool_result = {"error": "Neo4j connection failed"}
        is_valid, issues = analyzer.validate_tool_result("get_budget_benchmark", tool_result)

        assert not is_valid
        assert any("error" in issue.lower() for issue in issues)

    def test_validate_missing_hybrid_metadata(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test validation of hybrid tool missing sources_used metadata."""
        tool_result = {
            "statistics": {"avg_budget": 5000000},
            "metadata": {},  # Missing sources_used
        }
        is_valid, issues = analyzer.validate_tool_result("get_budget_benchmark", tool_result)

        assert not is_valid
        assert any("sources_used" in issue for issue in issues)

    def test_validate_complete_budget_benchmark_result(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test validation of complete budget benchmark result."""
        tool_result = {
            "statistics": {"avg_budget": 5000000, "median_budget": 4500000},
            "metadata": {"sources_used": ["graph", "sql"], "search_type": "hybrid"},
        }
        is_valid, issues = analyzer.validate_tool_result("get_budget_benchmark", tool_result)

        assert is_valid
        assert len(issues) == 0

    def test_validate_partner_discovery_no_partners(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test validation of partner discovery with no partners found."""
        tool_result = {"experienced_partners": [], "total_found": 0}
        is_valid, issues = analyzer.validate_tool_result("find_experienced_partners", tool_result)

        assert not is_valid
        assert any("partner" in issue.lower() for issue in issues)

    # ==================== Combined Analysis Tests ====================

    def test_analyze_with_tools_penalizes_failed_tools(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that failed tool results reduce overall quality score."""
        response = "I searched for hydrogen calls but found limited results."
        tool_results = {
            "search_funding_calls": {"calls": [], "calls_found": 0},
        }

        analysis = analyzer.analyze_with_tools(
            query="Find hydrogen funding calls",
            response=response,
            tools_used=["search_funding_calls"],
            tool_results=tool_results,
        )

        assert analysis.score < 70  # Penalized for empty tool results

    def test_analyze_with_tools_accepts_successful_results(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that successful tool results maintain quality score."""
        response = """
        I found 15 open funding opportunities for hydrogen research:

        1. HORIZON-CL5-2026-D3-01: Advanced Biofuels
           - Type: RIA
           - Deadline: February 2026
           - Budget: EUR 20M

        2. HORIZON-CL5-2025-D5-02: Hydrogen Production
           - Type: IA
           - Deadline: September 2025
           - Budget: EUR 15M
        """
        tool_results = {
            "search_funding_calls": {
                "calls": [{"id": "HORIZON-CL5-2026-D3-01"}],
                "calls_found": 15,
            },
        }

        analysis = analyzer.analyze_with_tools(
            query="Find hydrogen funding calls",
            response=response,
            tools_used=["search_funding_calls"],
            tool_results=tool_results,
        )

        assert analysis.score >= 70

    # ==================== Quality Analysis Object Tests ====================

    def test_quality_analysis_is_acceptable(self) -> None:
        """Test QualityAnalysis.is_acceptable() method."""
        high_quality = QualityAnalysis(
            score=85,
            category=ResponseCategory.COMPLETE,
            confidence=0.9,
        )
        assert high_quality.is_acceptable(min_score=75)

        low_quality = QualityAnalysis(
            score=40,
            category=ResponseCategory.PARTIAL,
            confidence=0.8,
        )
        assert not low_quality.is_acceptable(min_score=75)

        deflection = QualityAnalysis(
            score=30,
            category=ResponseCategory.DEFLECTION,
            confidence=0.95,
        )
        assert not deflection.is_acceptable(min_score=25)  # Deflections never acceptable

    def test_quality_analysis_to_dict(self) -> None:
        """Test QualityAnalysis serialization to dictionary."""
        analysis = QualityAnalysis(
            score=75,
            category=ResponseCategory.COMPLETE,
            confidence=0.9,
            missing_elements=["budget"],
            deflection_phrases_found=[],
            recommendations=["Add budget details"],
            query_type=QueryType.CALL_DETAILS,
        )

        result = analysis.to_dict()

        assert result["score"] == 75
        assert result["category"] == "complete"
        assert result["confidence"] == 0.9
        assert result["query_type"] == "call_details"
        assert result["is_acceptable"] is True

    # ==================== Singleton Tests ====================

    def test_get_analyzer_returns_same_instance(self) -> None:
        """Test that get_analyzer() returns the same instance."""
        analyzer1 = get_analyzer()
        analyzer2 = get_analyzer()

        assert analyzer1 is analyzer2


class TestResponseQualityParametrized:
    """Parametrized tests covering 25+ query types as specified in PRIMARY GOAL."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    # ==================== 5 Call ID Queries ====================

    @pytest.mark.parametrize(
        "query,expected_elements,min_score",
        [
            pytest.param(
                "Tell me about HORIZON-CL5-2026-D3-01",
                ["deadline", "budget", "action_type", "call_identifier"],
                75,
                id="call_biofuels",
            ),
            pytest.param(
                "What is HORIZON-CL4-2025-HUMAN-01?",
                ["deadline", "budget", "action_type"],
                75,
                id="call_human_ai",
            ),
            pytest.param(
                "Details about HORIZON-CL6-2025-FARM2FORK-01",
                ["deadline", "budget", "action_type"],
                75,
                id="call_food",
            ),
            pytest.param(
                "Explain HORIZON-HLTH-2025-DISEASE-07",
                ["deadline", "budget", "action_type"],
                75,
                id="call_health",
            ),
            pytest.param(
                "Information on EIC-2025-ACCELERATOR-01",
                ["deadline", "budget"],
                75,
                id="call_eic",
            ),
        ],
    )
    def test_call_details_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_elements: list[str],
        min_score: int,
    ) -> None:
        """Test that call details responses meet quality requirements."""
        # This is a GOOD response that should pass
        good_response = f"""
        Based on my search for {query}, here are the key details:

        **Call Information:**
        - **Call ID:** HORIZON-CL5-2026-D3-01
        - **Type:** RIA (Research and Innovation Action)
        - **Deadline:** February 5, 2026 at 17:00 Brussels time
        - **Budget:** EUR 20.00 million total
        - **Status:** Currently Open

        **Scope:**
        This call focuses on advancing research in renewable energy and
        sustainable technologies. Proposals should demonstrate innovation
        and potential for real-world impact.

        **How to Apply:**
        Submit your proposal through the EU Funding & Tenders Portal.
        """

        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
        )

        assert analysis.score >= min_score, (
            f"Good response should score >= {min_score}, got {analysis.score}. "
            f"Missing: {analysis.missing_elements}"
        )
        assert analysis.category != ResponseCategory.DEFLECTION, (
            f"Good response flagged as deflection: {analysis.deflection_phrases_found}"
        )

    @pytest.mark.parametrize(
        "query,bad_response,should_fail",
        [
            pytest.param(
                "Tell me about HORIZON-CL5-2026-D3-01",
                "I could not find specific details about this call.",
                True,
                id="deflection_could_not_find",
            ),
            pytest.param(
                "What is HORIZON-CL4-2025-HUMAN-01?",
                "Unfortunately, I was unable to retrieve information about this topic.",
                True,
                id="deflection_unable_to_retrieve",
            ),
            pytest.param(
                "Details about HORIZON-CL6-2025-FARM2FORK-01",
                "No results found for this search. Please try again.",
                True,
                id="deflection_no_results",
            ),
        ],
    )
    def test_call_details_deflection_detection(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        bad_response: str,
        should_fail: bool,
    ) -> None:
        """Test that deflection responses are correctly identified."""
        analysis = analyzer.analyze(query=query, response=bad_response)

        if should_fail:
            assert not analysis.is_acceptable(min_score=50), (
                f"Deflection response should fail quality check. "
                f"Score: {analysis.score}, Category: {analysis.category}"
            )
            assert len(analysis.deflection_phrases_found) > 0, (
                "Deflection phrases should be detected"
            )

    # ==================== 5 Programme Comparison Queries ====================

    @pytest.mark.parametrize(
        "query,expected_elements,min_score",
        [
            pytest.param(
                "Compare EIC Accelerator vs ERC success rates",
                ["comparison_language", "metric"],
                75,
                id="compare_eic_erc",
            ),
            pytest.param(
                "What's the difference between RIA and IA grants?",
                ["comparison_language"],
                75,
                id="compare_ria_ia",
            ),
            pytest.param(
                "Compare Cluster 4 vs Cluster 5 funding amounts",
                ["comparison_language", "metric"],
                75,
                id="compare_clusters",
            ),
            pytest.param(
                "How do MSCA and ERC differ for researchers?",
                ["comparison_language"],
                75,
                id="compare_msca_erc",
            ),
            pytest.param(
                "Horizon Europe vs previous FP7 success rates",
                ["comparison_language", "metric"],
                75,
                id="compare_h2020_fp7",
            ),
        ],
    )
    def test_comparison_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_elements: list[str],
        min_score: int,
    ) -> None:
        """Test that comparison responses meet quality requirements."""
        good_response = """
        Here's a comparison of the two programmes:

        **EIC Accelerator vs ERC Comparison:**

        | Aspect | EIC Accelerator | ERC |
        |--------|-----------------|-----|
        | Success Rate | ~8% | ~12% |
        | Funding Range | €0.5M - €17.5M | €1.5M - €10M |
        | Target | SMEs & Startups | Individual researchers |
        | Focus | Market deployment | Frontier research |

        **Key Differences:**
        - EIC focuses on bringing innovations to market
        - ERC emphasizes groundbreaking scientific research
        - EIC requires a company structure
        - ERC is for individual principal investigators

        Both programmes are highly competitive with rigorous evaluation.
        """

        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
        )

        assert analysis.score >= min_score
        assert analysis.category != ResponseCategory.DEFLECTION

    # ==================== 5 Eligibility/FAQ Queries ====================

    @pytest.mark.parametrize(
        "query,expected_elements,min_score",
        [
            pytest.param(
                "Can SMEs apply to LIFE Programme?",
                [],
                70,
                id="sme_eligibility",
            ),
            pytest.param(
                "Are UK organizations eligible for Horizon Europe?",
                [],
                70,
                id="uk_eligibility",
            ),
            pytest.param(
                "What are the consortium requirements for RIA?",
                [],
                70,
                id="consortium_requirements",
            ),
            pytest.param(
                "Can non-profit organizations coordinate projects?",
                [],
                70,
                id="nonprofit_coordination",
            ),
            pytest.param(
                "Is my university eligible as third country partner?",
                [],
                70,
                id="third_country",
            ),
        ],
    )
    def test_eligibility_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_elements: list[str],
        min_score: int,
    ) -> None:
        """Test that eligibility FAQ responses meet quality requirements."""
        good_response = """
        Yes, SMEs can apply to the LIFE Programme!

        **Eligibility Requirements:**
        - SMEs from EU member states are fully eligible
        - Associated countries may also participate
        - Both single applicants and consortia are welcome

        **Specific Conditions:**
        - For Standard Action Projects: consortia of at least 2 entities
        - For Strategic Nature/Integrated Projects: larger partnerships required
        - SMEs may benefit from higher co-financing rates in certain cases

        **Key Points:**
        - Registration in the EU Participant Portal is required
        - Legal entity validation must be completed before applying
        - Check specific call conditions for any additional requirements
        """

        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
        )

        assert analysis.score >= min_score

    # ==================== 3 Budget Benchmark Queries ====================

    @pytest.mark.parametrize(
        "query,expected_elements,min_score",
        [
            pytest.param(
                "What is typical budget for Horizon RIA in Cluster 5?",
                ["budget_figure", "statistical_term"],
                75,
                id="budget_cluster5_ria",
            ),
            pytest.param(
                "Average funding for Digital Europe projects",
                ["budget_figure", "statistical_term"],
                75,
                id="budget_digital_europe",
            ),
            pytest.param(
                "How much funding do Health IAs typically receive?",
                ["budget_figure", "statistical_term"],
                75,
                id="budget_health_ia",
            ),
        ],
    )
    def test_budget_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_elements: list[str],
        min_score: int,
    ) -> None:
        """Test that budget benchmark responses meet quality requirements."""
        good_response = """
        Based on analysis of 496 funded projects in Cluster 5:

        **Budget Statistics for Cluster 5 RIA Projects:**
        - **Average budget:** EUR 4.9 million
        - **Median budget:** EUR 4.5 million
        - **Typical range:** EUR 3.4M - EUR 5.5M
        - **Minimum observed:** EUR 1.3 million
        - **Maximum observed:** EUR 20 million

        **Consortium Size Context:**
        - Average partners: 13-15 organizations
        - Average countries: 7-9 EU member states

        **Recommendations:**
        For a competitive Cluster 5 RIA proposal, target a budget in the
        EUR 4-5 million range with approximately 12-15 consortium partners.
        """

        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
        )

        assert analysis.score >= min_score
        assert len(analysis.deflection_phrases_found) == 0

    # ==================== 3 Partner Discovery Queries ====================

    @pytest.mark.parametrize(
        "query,expected_elements,min_score",
        [
            pytest.param(
                "Find German SMEs with hydrogen experience",
                ["organization", "experience"],
                75,
                id="partner_german_hydrogen",
            ),
            pytest.param(
                "Research institutions in France for AI projects",
                ["organization"],
                75,
                id="partner_france_ai",
            ),
            pytest.param(
                "Find experienced coordinators in renewable energy",
                ["organization", "experience"],
                75,
                id="partner_coordinators",
            ),
        ],
    )
    def test_partner_discovery_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_elements: list[str],
        min_score: int,
    ) -> None:
        """Test that partner discovery responses meet quality requirements."""
        good_response = """
        I found 47 organizations matching your criteria:

        **Top Experienced Partners:**

        1. **Fraunhofer-Gesellschaft** (Germany)
           - Type: Research Organization
           - Projects: 15 in hydrogen/fuel cells
           - Track Record Score: 0.92

        2. **DLR - German Aerospace Center** (Germany)
           - Type: Research Organization
           - Projects: 12 in clean energy
           - Coordination Experience: 5 projects

        3. **HydrogenPro GmbH** (Germany)
           - Type: SME
           - Projects: 8 hydrogen-related
           - Specialization: Electrolyzer technology

        These organizations have demonstrated expertise and successful
        participation in Horizon Europe projects.
        """

        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
        )

        assert analysis.score >= min_score

    # ==================== 2 Project Search Queries ====================

    @pytest.mark.parametrize(
        "query,expected_elements,min_score",
        [
            pytest.param(
                "Find quantum computing projects in Horizon Europe",
                ["project_indication"],
                75,
                id="project_quantum",
            ),
            pytest.param(
                "Show funded projects on sustainable agriculture",
                ["project_indication", "organization"],
                75,
                id="project_agriculture",
            ),
        ],
    )
    def test_project_search_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_elements: list[str],
        min_score: int,
    ) -> None:
        """Test that project search responses meet quality requirements."""
        good_response = """
        I found 23 funded quantum computing projects:

        **Selected Projects:**

        1. **QUBIC** (Project ID: 101000001)
           - Funding: EUR 4.5 million
           - Partners: 12 organizations from 8 countries
           - Coordinator: TU Delft (Netherlands)
           - Focus: Quantum error correction

        2. **QuantumCircuits** (Project ID: 101000002)
           - Funding: EUR 6.2 million
           - Partners: 15 organizations
           - Coordinator: ETH Zurich (Switzerland)
           - Focus: Superconducting quantum processors

        These projects represent significant EU investment in quantum technologies.
        """

        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
        )

        assert analysis.score >= min_score

    # ==================== 2 Consortium Pattern Queries ====================

    @pytest.mark.parametrize(
        "query,expected_elements,min_score",
        [
            pytest.param(
                "What is typical consortium size for Health IAs?",
                ["consortium_term", "pattern_term"],
                75,
                id="consortium_health_ia",
            ),
            pytest.param(
                "Average number of partners in Cluster 4 projects",
                ["consortium_term", "pattern_term"],
                75,
                id="consortium_cluster4",
            ),
        ],
    )
    def test_consortium_pattern_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_elements: list[str],
        min_score: int,
    ) -> None:
        """Test that consortium pattern responses meet quality requirements."""
        good_response = """
        Analysis of Health Innovation Actions (IAs):

        **Consortium Size Patterns:**
        - **Average partners:** 12.5 organizations
        - **Average countries:** 8.2 EU member states
        - **Typical range:** 8-18 partners

        **Organization Type Distribution:**
        - Higher Education (HES): 35%
        - Research Organizations (REC): 28%
        - Private Companies (PRC): 22%
        - Other (OTH): 15%

        **Successful Consortium Templates:**
        - Most successful IAs have a balanced mix of academia and industry
        - Coordinators are typically large research universities
        - SME participation around 25-30% is common
        """

        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
        )

        assert analysis.score >= min_score


class TestEdgeCasesAndBoundaries:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    def test_response_exactly_at_minimum_length(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test response at exactly the minimum length threshold."""
        # For GENERAL_FAQ, minimum is 100 chars
        response = "A" * 100
        analysis = analyzer.analyze(
            "What is RIA?", response, query_type=QueryType.GENERAL_FAQ
        )

        # Should not be penalized for length
        assert analysis.score > 0

    def test_response_just_below_minimum_length(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test response just below minimum length threshold."""
        response = "A" * 99
        analysis = analyzer.analyze(
            "What is RIA?", response, query_type=QueryType.GENERAL_FAQ
        )

        # Should be penalized for being too short
        assert analysis.score < 100

    def test_mixed_positive_and_deflection_content(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test response with both good content and some deflection phrases."""
        response = """
        HORIZON-CL5-2026-D3-01 is a Research and Innovation Action (RIA).

        **Available Information:**
        - Type: RIA
        - Budget: EUR 20 million
        - Deadline: February 2026

        I could not find the exact submission deadline time, but the call
        is currently open for proposals.
        """
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01", response
        )

        # Should detect the deflection but still have reasonable score
        # because there's substantial good content
        assert "could not find" in analysis.deflection_phrases_found
        # Score should be reduced but not failed entirely
        assert analysis.score > 30

    def test_case_insensitive_deflection_detection(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that deflection detection is case-insensitive."""
        response = "I COULD NOT FIND any specific information about this."
        analysis = analyzer.analyze("Test query", response)

        assert "could not find" in analysis.deflection_phrases_found

    def test_unicode_content_handling(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of unicode characters in responses."""
        response = """
        Budget: EUR 5 million (€5M)
        Deadline: February 2026
        Type: RIA
        Special characters: éàüñ 中文 日本語
        """
        analysis = analyzer.analyze("Tell me about the call", response)

        # Should handle unicode without errors
        assert analysis.score > 0

    def test_markdown_formatting_preserved(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that markdown formatting doesn't affect pattern matching."""
        response = """
        **HORIZON-CL5-2026-D3-01**

        - **Budget:** EUR 20 million
        - **Deadline:** February 5, 2026
        - **Type:** RIA

        _This is emphasized text_
        """
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01",
            response,
            query_type=QueryType.CALL_DETAILS,
        )

        # Should detect all required elements despite markdown
        assert analysis.score >= 70


class TestToolValidationComprehensive:
    """Comprehensive tests for tool result validation."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    @pytest.mark.parametrize(
        "tool_name,tool_result,expected_valid",
        [
            pytest.param(
                "search_funding_calls",
                {"calls": [{"id": "test"}], "calls_found": 1},
                True,
                id="valid_call_search",
            ),
            pytest.param(
                "search_funding_calls",
                {"calls": [], "calls_found": 0},
                False,
                id="empty_call_search",
            ),
            pytest.param(
                "search_projects",
                {"projects": [{"id": "123"}]},
                True,
                id="valid_project_search",
            ),
            pytest.param(
                "search_projects",
                {"projects": []},
                False,
                id="empty_project_search",
            ),
            pytest.param(
                "get_budget_benchmark",
                {
                    "statistics": {"avg": 5000000},
                    "metadata": {"sources_used": ["graph", "sql"]},
                },
                True,
                id="valid_budget_benchmark",
            ),
            pytest.param(
                "get_budget_benchmark",
                {"recommendations": {}},  # Missing statistics
                False,
                id="invalid_budget_benchmark",
            ),
            pytest.param(
                "find_experienced_partners",
                {
                    "experienced_partners": [{"name": "Test"}],
                    "total_found": 1,
                    "metadata": {"sources_used": ["graph", "sql"]},
                },
                True,
                id="valid_partner_discovery",
            ),
            pytest.param(
                "find_experienced_partners",
                {"experienced_partners": []},
                False,
                id="empty_partner_discovery",
            ),
            pytest.param(
                "get_consortium_patterns",
                {
                    "consortium_size": {"avg": 12},
                    "metadata": {"sources_used": ["graph", "sql"]},
                },
                True,
                id="valid_consortium_patterns",
            ),
            pytest.param(
                "get_consortium_patterns",
                {"org_distribution": {}},  # Missing consortium_size
                False,
                id="invalid_consortium_patterns",
            ),
        ],
    )
    def test_tool_result_validation(
        self,
        analyzer: ResponseQualityAnalyzer,
        tool_name: str,
        tool_result: dict,
        expected_valid: bool,
    ) -> None:
        """Parametrized test for tool result validation."""
        is_valid, issues = analyzer.validate_tool_result(tool_name, tool_result)

        assert is_valid == expected_valid, (
            f"Tool {tool_name} validation expected {expected_valid}, "
            f"got {is_valid}. Issues: {issues}"
        )
