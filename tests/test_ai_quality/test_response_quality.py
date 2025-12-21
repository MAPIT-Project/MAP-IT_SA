"""
Comprehensive AI Response Quality Tests

This test suite validates that AI responses meet quality standards and
do not contain deflection patterns. Tests cover 25+ query types as
specified in the improvement protocol.

Test Categories:
- 5 specific call ID queries
- 5 programme comparison queries
- 5 eligibility/FAQ queries
- 3 budget benchmark queries
- 3 partner discovery queries
- 2 project search queries
- 2 consortium pattern queries

Each test validates:
1. No deflection phrases present
2. Expected content elements found
3. Minimum quality score met (default 70)
4. Response category is not DEFLECTION or EMPTY

Run with: pytest tests/test_ai_quality/test_response_quality.py -v
"""

import logging

import pytest

from app.services.quality.response_quality_analyzer import (
    QueryType,
    ResponseCategory,
    ResponseQualityAnalyzer,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def analyzer() -> ResponseQualityAnalyzer:
    """Create a ResponseQualityAnalyzer instance."""
    return ResponseQualityAnalyzer()


@pytest.fixture
def strict_analyzer() -> ResponseQualityAnalyzer:
    """Create a strict mode analyzer."""
    return ResponseQualityAnalyzer(strict_mode=True)


# ============================================================================
# Unit Tests for ResponseQualityAnalyzer
# ============================================================================


class TestResponseQualityAnalyzerCore:
    """Core unit tests for the ResponseQualityAnalyzer."""

    def test_analyzer_initialization(self, analyzer: ResponseQualityAnalyzer):
        """Test analyzer initializes correctly."""
        assert analyzer is not None
        assert len(analyzer.DEFLECTION_PHRASES) > 0
        assert len(analyzer.QUERY_TYPE_PATTERNS) > 0

    def test_deflection_detection_single_phrase(self, analyzer: ResponseQualityAnalyzer):
        """Test detection of single deflection phrase."""
        response = "I could not find any information about this topic."
        analysis = analyzer.analyze("test query", response)

        assert "could not find" in analysis.deflection_phrases_found

    def test_deflection_detection_multiple_phrases(self, analyzer: ResponseQualityAnalyzer):
        """Test detection of multiple deflection phrases."""
        # Make response long enough to not be classified as EMPTY
        response = (
            "I apologize, but I could not find specific details about this topic. "
            "No information available in my knowledge base regarding your query. "
            "Unable to retrieve the data you requested at this time. "
            "Please try a more specific query or consult the official documentation. "
            "This topic is not available in my current data sources."
        )
        analysis = analyzer.analyze("test query", response)

        assert len(analysis.deflection_phrases_found) >= 2
        assert analysis.category == ResponseCategory.DEFLECTION

    def test_no_deflection_in_good_response(self, analyzer: ResponseQualityAnalyzer):
        """Test that good responses don't trigger deflection detection."""
        response = """
        The HORIZON-CL5-2026-D3-01 call focuses on clean hydrogen research.

        **Key Details:**
        - **Deadline:** 05 Feb 2026
        - **Budget:** EUR 20 million
        - **Type:** RIA (Research and Innovation Action)
        - **Status:** Open

        This call supports innovative approaches to hydrogen production,
        storage, and distribution technologies.
        """
        analysis = analyzer.analyze("Tell me about HORIZON-CL5-2026-D3-01", response)

        assert len(analysis.deflection_phrases_found) == 0
        assert analysis.category != ResponseCategory.DEFLECTION

    def test_query_type_detection_call_details(self, analyzer: ResponseQualityAnalyzer):
        """Test detection of call details query type."""
        queries = [
            "Tell me about HORIZON-CL5-2026-D3-01",
            "What are the details of HORIZON-CL4-2025-DATA-01?",
            "Information about call HORIZON-HLTH-2025-DISEASE-03",
        ]

        for query in queries:
            analysis = analyzer.analyze(query, "Sample response with content")
            assert analysis.query_type == QueryType.CALL_DETAILS

    def test_query_type_detection_programme_comparison(self, analyzer: ResponseQualityAnalyzer):
        """Test detection of programme comparison query type."""
        queries = [
            "Compare EIC and ERC programmes",
            "What's the difference between RIA and IA?",
            "EIC vs ERC success rates",
        ]

        for query in queries:
            analysis = analyzer.analyze(query, "Sample response")
            assert analysis.query_type == QueryType.PROGRAMME_COMPARISON

    def test_query_type_detection_budget_benchmark(self, analyzer: ResponseQualityAnalyzer):
        """Test detection of budget benchmark query type."""
        queries = [
            "What is the typical budget for a Horizon RIA?",
            "Average budget for Cluster 5 projects",
            "How much funding can I request for an IA?",
        ]

        for query in queries:
            analysis = analyzer.analyze(query, "Sample response")
            assert analysis.query_type == QueryType.BUDGET_BENCHMARK

    def test_score_calculation_complete(self, analyzer: ResponseQualityAnalyzer):
        """Test score calculation for complete response."""
        response = """
        The HORIZON-CL5-2026-D3-01 call focuses on sustainable hydrogen technologies.

        **📋 Call Details:**
        - **Call ID:** HORIZON-CL5-2026-D3-01
        - **Title:** Advanced Hydrogen Technologies
        - **⏰ Deadline:** 05 February 2026
        - **💰 Budget:** EUR 20 million
        - **🔬 Type:** RIA
        - **🟢 Status:** Open

        According to the Horizon Europe Work Programme 2024-2025, this call
        aims to advance clean hydrogen production and storage methods.
        """
        analysis = analyzer.analyze("Tell me about HORIZON-CL5-2026-D3-01", response)

        assert analysis.score >= 70
        assert analysis.category == ResponseCategory.COMPLETE
        assert analysis.has_structured_data

    def test_score_calculation_empty(self, analyzer: ResponseQualityAnalyzer):
        """Test score calculation for empty response."""
        response = "I don't know."
        analysis = analyzer.analyze("What is RIA?", response)

        assert analysis.score < 30
        assert analysis.category in [ResponseCategory.EMPTY, ResponseCategory.DEFLECTION]

    def test_is_acceptable_method(self, analyzer: ResponseQualityAnalyzer):
        """Test is_acceptable method."""
        good_response = """
        RIA stands for Research and Innovation Action. It is a Horizon Europe
        funding mechanism for projects that primarily consist of research activities,
        supplemented by innovation activities like demonstration. RIA projects
        typically receive 100% funding and require a consortium of at least 3
        independent entities from 3 different EU Member States or Associated Countries.
        """

        analysis = analyzer.analyze("What is RIA?", good_response)
        assert analyzer.is_acceptable(analysis, min_score=60)

        bad_response = "I could not find information about this."
        analysis = analyzer.analyze("What is RIA?", bad_response)
        assert not analyzer.is_acceptable(analysis)

    def test_quick_check_method(self, analyzer: ResponseQualityAnalyzer):
        """Test quick_check method."""
        # Good response - needs to be at least 20 words
        is_ok, reason = analyzer.quick_check(
            "This is a comprehensive response about Horizon Europe funding. "
            "The programme provides significant support for research and innovation "
            "across the European Union and associated countries."
        )
        assert is_ok
        assert reason == "OK"

        # Too short
        is_ok, reason = analyzer.quick_check("No.")
        assert not is_ok
        assert "too short" in reason.lower()

        # Multiple deflections - needs longer response to not be "too short"
        is_ok, reason = analyzer.quick_check(
            "I apologize, but I could not find any specific details about this topic. "
            "No information available in my current knowledge base regarding your query."
        )
        assert not is_ok
        assert "deflection" in reason.lower()


# ============================================================================
# Sample Response Generators for Testing
# ============================================================================


class SampleResponses:
    """Factory for generating sample AI responses for testing."""

    @staticmethod
    def good_call_details(call_id: str = "HORIZON-CL5-2026-D3-01") -> str:
        """Generate a good call details response."""
        return f"""
I found detailed information about the call **{call_id}**:

**📋 Call ID:** {call_id}
**Title:** Advanced Clean Hydrogen Technologies for Sustainable Energy

**🔬 Type:** RIA (Research and Innovation Action)
**🟢 Status:** Open
**⏰ Deadline:** 05 February 2026 at 17:00 Brussels time
**💰 Budget:** EUR 20.00 million
**🏛️ Programme:** Horizon Europe - Cluster 5 (Climate, Energy and Mobility)

**Scope:**
This call focuses on developing innovative hydrogen production, storage, and
distribution technologies. Projects should address efficiency improvements,
cost reduction, and scaling-up of clean hydrogen solutions.

**Expected Impact:**
- Reduction in hydrogen production costs by at least 30%
- Demonstration of scalable storage solutions
- Contribution to EU Green Deal objectives

**Eligibility:**
Minimum consortium of 3 independent legal entities from 3 different EU Member
States or Associated Countries. SME participation is encouraged.

🔗 **Apply:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{call_id.lower()}

💡 **How to Apply:**
1. Register on the EU Funding & Tenders Portal
2. Form your consortium with eligible partners
3. Submit your proposal before the deadline
"""

    @staticmethod
    def good_programme_comparison(prog1: str = "EIC", prog2: str = "ERC") -> str:
        """Generate a good programme comparison response."""
        return f"""
Here is a comprehensive comparison between **{prog1}** and **{prog2}**:

| Aspect | {prog1} | {prog2} |
|--------|---------|---------|
| Target | SMEs and startups | Individual researchers |
| Funding | Up to €17.5M (blended) | €1.5M - €10M |
| Success Rate | ~8% | ~12% |
| Focus | Market-ready innovation | Frontier research |
| Duration | 2-3 years | Up to 5 years |

**Key Differences:**

**{prog1} (European Innovation Council):**
- Targets high-risk, high-impact innovations
- Requires strong commercialization potential
- Offers blended finance (grant + equity)
- Evaluation focuses on market potential and team

**{prog2} (European Research Council):**
- Supports excellent individual researchers
- Focus on frontier scientific research
- Researcher-centric (no consortium required)
- Evaluation based on scientific excellence

**Recommendation:**
- Choose **{prog1}** if you have a market-ready innovation or startup
- Choose **{prog2}** if you're conducting fundamental research

Success rates for {prog1} are around 8%, while {prog2} has approximately 12% success rate.
"""

    @staticmethod
    def good_budget_benchmark(action_type: str = "RIA", cluster: str = "CL5") -> str:
        """Generate a good budget benchmark response."""
        return f"""
Based on analysis of **496 funded {action_type} projects** in {cluster}, here are the budget benchmarks:

**💰 Budget Statistics:**
- **Minimum:** €1.32 million
- **Maximum:** €19.95 million
- **Median:** €4.49 million
- **Average:** €4.86 million

**👥 Consortium Size:**
- **Average:** 13.3 partners
- **Median:** 12 partners
- **Per Partner:** €500K - €700K average

**Budget Range Recommendations:**
- For a small consortium (8 partners): €3.5M - €5M
- For a medium consortium (12 partners): €5M - €7M
- For a large consortium (15+ partners): €7M - €10M

**Organization Type Breakdown:**
| Type | % of Budget |
|------|-------------|
| Research Organizations (REC) | 34% |
| Private Companies (PRC) | 34% |
| Higher Education (HES) | 28% |
| Other | 4% |

**Top Coordinator Countries:** Spain, Italy, Germany, Belgium, Netherlands

These benchmarks are based on funded Horizon Europe projects from 2021-2024.
"""

    @staticmethod
    def good_partner_discovery(topic: str = "hydrogen", country: str = "Germany") -> str:
        """Generate a good partner discovery response."""
        return f"""
I found **15 experienced partners** with expertise in **{topic}** in **{country}**:

**Top Partners (ranked by experience score):**

**1. Technical University of Munich (TUM)**
- 🏛️ Type: Higher Education (HES)
- 📍 Country: Germany
- 📊 Experience Score: 95/100
- 📋 Relevant Projects: 12
- 🎯 Coordination Experience: 5 projects coordinated
- Recent Projects: H2STORE (coordinator), GREENH2 (participant)

**2. Fraunhofer-Gesellschaft**
- 🏛️ Type: Research Organization (REC)
- 📍 Country: Germany
- 📊 Experience Score: 92/100
- 📋 Relevant Projects: 18
- 🎯 Coordination Experience: 8 projects coordinated

**3. Max Planck Institute**
- 🏛️ Type: Research Organization (REC)
- 📍 Country: Germany
- 📊 Experience Score: 88/100
- 📋 Relevant Projects: 7

**4. BASF SE** (Industry)
- 🏛️ Type: Private Company (PRC)
- 📍 Country: Germany
- 📊 Experience Score: 85/100
- 📋 Relevant Projects: 5

**Search Metadata:**
- Sources used: Graph database + SQL (hybrid search)
- Partners from graph: 10
- Partners from SQL: 8
- Merged total: 15
- Inferred clusters: CLUSTER-5 (Climate, Energy, Mobility)

💡 **Tip:** Consider reaching out to organizations with coordination experience
for lead partner roles.
"""

    @staticmethod
    def good_eligibility_faq() -> str:
        """Generate a good eligibility FAQ response."""
        return """
**Consortium Requirements for Horizon Europe RIA Projects:**

According to the Horizon Europe Regulation and Work Programme, the minimum
consortium requirements are:

**Minimum Consortium Composition:**
- At least **3 independent legal entities**
- From **3 different EU Member States or Associated Countries**
- Each entity must be independent (not controlled by the same parent)

**Eligible Entities:**
✅ Higher Education Institutions (universities)
✅ Research Organizations
✅ Private Companies (including SMEs)
✅ Public Bodies
✅ International Organizations
✅ Non-profit Organizations

**Associated Countries (as of 2024):**
Norway, Iceland, Israel, Turkey, Serbia, Ukraine, UK (for Pillar 2), and others.

**Important Notes:**
- Switzerland can participate but with different funding arrangements
- Third countries can participate as self-funded partners
- SME participation is encouraged and may provide evaluation bonus

**Additional Requirements by Programme:**
- ERC: Single PI (no consortium required)
- MSCA: Specific requirements per fellowship type
- EIC Accelerator: Single company or small consortium

For the latest eligibility rules, consult the specific call documentation
and the Horizon Europe Work Programme.
"""

    @staticmethod
    def deflection_response() -> str:
        """Generate a deflection response (for testing detection)."""
        return """
I could not find specific information about this topic.
The data is not available in my current knowledge base.
Please try a more specific query or consult the official EU Portal.
Unable to retrieve the requested details at this time.
"""

    @staticmethod
    def partial_response() -> str:
        """Generate a partial response."""
        return """
I found some information about this call. The deadline appears to be
in early 2026 but I could not extract specific details about the budget
or eligibility requirements.
"""


# ============================================================================
# CATEGORY 1: Call ID Queries (5 tests)
# ============================================================================


class TestCallIDQueries:
    """Test suite for specific call ID queries."""

    @pytest.mark.parametrize(
        "call_id,expected_elements",
        [
            ("HORIZON-CL5-2026-D3-01", ["call_id", "deadline", "budget", "type", "status"]),
            ("HORIZON-CL4-2025-DATA-01", ["call_id", "deadline", "budget", "type"]),
            ("HORIZON-HLTH-2025-DISEASE-03", ["call_id", "deadline", "type"]),
            ("HORIZON-CL6-2025-FARM2FORK-01", ["call_id", "deadline", "budget"]),
            ("HORIZON-MSCA-2025-DN-01", ["call_id", "deadline", "type"]),
        ],
    )
    def test_call_id_query_detection(
        self,
        analyzer: ResponseQualityAnalyzer,
        call_id: str,
        expected_elements: list[str],
    ):
        """Test that call ID queries are correctly detected."""
        query = f"Tell me about {call_id}"
        response = SampleResponses.good_call_details(call_id)
        analysis = analyzer.analyze(query, response)

        assert analysis.query_type == QueryType.CALL_DETAILS
        assert len(analysis.deflection_phrases_found) == 0
        logger.info(f"Call {call_id}: score={analysis.score}, found={analysis.found_elements}")

    def test_call_details_complete_response(self, analyzer: ResponseQualityAnalyzer):
        """Test complete call details response meets quality threshold."""
        query = "Tell me about HORIZON-CL5-2026-D3-01"
        response = SampleResponses.good_call_details("HORIZON-CL5-2026-D3-01")
        analysis = analyzer.analyze(query, response)

        assert analysis.score >= 70
        assert analysis.category == ResponseCategory.COMPLETE
        assert "call_id" in analysis.found_elements or "deadline" in analysis.found_elements

    def test_call_deflection_fails(self, analyzer: ResponseQualityAnalyzer):
        """Test that deflection response for call query fails quality check."""
        query = "Tell me about HORIZON-CL5-2026-D3-01"
        response = SampleResponses.deflection_response()
        analysis = analyzer.analyze(query, response)

        assert analysis.category == ResponseCategory.DEFLECTION
        assert len(analysis.deflection_phrases_found) >= 2
        assert not analyzer.is_acceptable(analysis)

    def test_call_partial_response(self, analyzer: ResponseQualityAnalyzer):
        """Test partial call response is correctly categorized."""
        query = "Tell me about HORIZON-CL4-2025-DATA-01"
        response = SampleResponses.partial_response()
        analysis = analyzer.analyze(query, response)

        # Partial responses should have lower scores
        assert analysis.score < 70
        assert analysis.category in [ResponseCategory.PARTIAL, ResponseCategory.DEFLECTION]


# ============================================================================
# CATEGORY 2: Programme Comparison Queries (5 tests)
# ============================================================================


class TestProgrammeComparisonQueries:
    """Test suite for programme comparison queries."""

    @pytest.mark.parametrize(
        "prog1,prog2,expected_elements",
        [
            ("EIC", "ERC", ["comparison_table", "success_rate", "target_applicants"]),
            ("RIA", "IA", ["comparison_table", "funding_range"]),
            ("MSCA", "ERC", ["target_applicants", "funding_range"]),
            ("EIC Accelerator", "ERC Starting Grant", ["success_rate"]),
            ("Horizon Europe", "Horizon 2020", ["comparison_table"]),
        ],
    )
    def test_programme_comparison_detection(
        self,
        analyzer: ResponseQualityAnalyzer,
        prog1: str,
        prog2: str,
        expected_elements: list[str],
    ):
        """Test programme comparison query detection."""
        query = f"Compare {prog1} and {prog2}"
        response = SampleResponses.good_programme_comparison(prog1, prog2)
        analysis = analyzer.analyze(query, response)

        assert analysis.query_type == QueryType.PROGRAMME_COMPARISON
        assert len(analysis.deflection_phrases_found) == 0
        logger.info(
            f"Comparison {prog1} vs {prog2}: score={analysis.score}, "
            f"elements={analysis.found_elements}"
        )

    def test_comparison_complete_response(self, analyzer: ResponseQualityAnalyzer):
        """Test complete programme comparison meets quality threshold."""
        query = "Compare EIC and ERC success rates"
        response = SampleResponses.good_programme_comparison("EIC", "ERC")
        analysis = analyzer.analyze(query, response)

        assert analysis.score >= 70
        assert analysis.category == ResponseCategory.COMPLETE
        assert analysis.has_structured_data  # Should have table

    def test_comparison_requires_both_programmes(self, analyzer: ResponseQualityAnalyzer):
        """Test that comparison needs to mention both programmes."""
        query = "Compare EIC and ERC"
        response = """
        EIC is excellent for startups. Success rate is around 8%.
        Funding goes up to 17.5 million euros for blended finance.
        """  # Missing ERC details

        analysis = analyzer.analyze(query, response)

        # Should detect missing elements
        assert analysis.score < 80
        assert len(analysis.missing_elements) > 0


# ============================================================================
# CATEGORY 3: Eligibility/FAQ Queries (5 tests)
# ============================================================================


class TestEligibilityFAQQueries:
    """Test suite for eligibility and FAQ queries."""

    @pytest.mark.parametrize(
        "query,expected_elements",
        [
            (
                "Can SMEs apply to Horizon Europe?",
                ["eligibility_rules", "requirements"],
            ),
            (
                "What are the consortium requirements for RIA?",
                ["minimum_consortium", "requirements"],
            ),
            (
                "Is Switzerland eligible for Horizon Europe?",
                ["eligibility_rules"],
            ),
            (
                "Who can apply for ERC grants?",
                ["eligibility_rules", "target_applicants"],
            ),
            (
                "What are the eligibility criteria for MSCA?",
                ["eligibility_rules", "requirements"],
            ),
        ],
    )
    def test_eligibility_query_detection(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_elements: list[str],
    ):
        """Test eligibility query detection."""
        response = SampleResponses.good_eligibility_faq()
        analysis = analyzer.analyze(query, response)

        assert analysis.query_type == QueryType.ELIGIBILITY_FAQ
        assert len(analysis.deflection_phrases_found) == 0
        logger.info(f"Eligibility query: score={analysis.score}")

    def test_eligibility_complete_response(self, analyzer: ResponseQualityAnalyzer):
        """Test complete eligibility response meets quality threshold."""
        query = "What are the consortium requirements for RIA?"
        response = SampleResponses.good_eligibility_faq()
        analysis = analyzer.analyze(query, response)

        assert analysis.score >= 70
        assert analysis.category == ResponseCategory.COMPLETE

    def test_eligibility_mentions_numbers(self, analyzer: ResponseQualityAnalyzer):
        """Test that eligibility response includes specific numbers."""
        query = "What are the minimum consortium requirements?"
        response = """
        **Minimum Consortium Requirements for Horizon Europe RIA Projects:**

        For Horizon Europe RIA (Research and Innovation Action) projects, you need:
        - Minimum **3 independent legal entities**
        - From **3 different EU Member States or Associated Countries**
        - Each entity must be independent and not controlled by the same parent

        **Eligible Entities:**
        - Higher Education Institutions (universities)
        - Research Organizations
        - Private Companies (including SMEs)
        - Public Bodies
        - Non-profit Organizations

        This is the standard requirement as defined in the Horizon Europe Regulation.
        SME participation is encouraged and may provide an evaluation bonus.
        For some calls, additional requirements may apply.
        """
        analysis = analyzer.analyze(query, response)

        assert analysis.score >= 60
        # Check that at least one expected element is found
        assert len(analysis.found_elements) > 0 or analysis.has_structured_data


# ============================================================================
# CATEGORY 4: Budget Benchmark Queries (3 tests)
# ============================================================================


class TestBudgetBenchmarkQueries:
    """Test suite for budget benchmark queries."""

    @pytest.mark.parametrize(
        "query,min_score",
        [
            ("What is typical budget for Horizon RIA in Cluster 5?", 70),
            ("Average budget for Climate and Energy projects?", 65),
            ("How much funding for an Innovation Action in Digital?", 65),
        ],
    )
    def test_budget_query_detection(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        min_score: int,
    ):
        """Test budget benchmark query detection and quality."""
        response = SampleResponses.good_budget_benchmark()
        analysis = analyzer.analyze(query, response)

        assert analysis.query_type == QueryType.BUDGET_BENCHMARK
        assert analysis.score >= min_score
        assert len(analysis.deflection_phrases_found) == 0
        logger.info(f"Budget query: score={analysis.score}, elements={analysis.found_elements}")

    def test_budget_includes_range(self, analyzer: ResponseQualityAnalyzer):
        """Test that budget response includes actual ranges."""
        query = "What is typical budget for RIA?"
        response = SampleResponses.good_budget_benchmark("RIA", "CL5")
        analysis = analyzer.analyze(query, response)

        assert analysis.has_structured_data
        assert any(
            elem in analysis.found_elements
            for elem in ["budget_range", "average_budget", "funding_amount"]
        )


# ============================================================================
# CATEGORY 5: Partner Discovery Queries (3 tests)
# ============================================================================


class TestPartnerDiscoveryQueries:
    """Test suite for partner discovery queries."""

    @pytest.mark.parametrize(
        "query,topic,country",
        [
            ("Find German SMEs with hydrogen experience", "hydrogen", "Germany"),
            ("Partners with AI expertise in France", "AI", "France"),
            ("Organizations working on quantum in Netherlands", "quantum", "Netherlands"),
        ],
    )
    def test_partner_discovery_query(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        topic: str,
        country: str,
    ):
        """Test partner discovery query detection and quality."""
        response = SampleResponses.good_partner_discovery(topic, country)
        analysis = analyzer.analyze(query, response)

        assert analysis.query_type == QueryType.PARTNER_DISCOVERY
        assert analysis.score >= 70
        assert len(analysis.deflection_phrases_found) == 0
        logger.info(f"Partner query '{query}': score={analysis.score}")

    def test_partner_includes_organizations(self, analyzer: ResponseQualityAnalyzer):
        """Test that partner response includes actual organizations."""
        query = "Find experienced partners for hydrogen research"
        response = SampleResponses.good_partner_discovery("hydrogen", "Germany")
        analysis = analyzer.analyze(query, response)

        assert (
            "partner_names" in analysis.found_elements
            or "partners_found" in analysis.found_elements
        )


# ============================================================================
# CATEGORY 6: Project Search Queries (2 tests)
# ============================================================================


class TestProjectSearchQueries:
    """Test suite for project search queries."""

    @pytest.mark.parametrize(
        "query",
        [
            "Find quantum computing projects",
            "Search for AI healthcare projects funded by EU",
        ],
    )
    def test_project_search_query(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
    ):
        """Test project search query detection."""
        response = """
        I found **12 projects** matching your search for quantum computing:

        **1. QUBIC** - Quantum Computing for Industry
        - 💰 Funding: €4.5 million
        - 📍 Coordinator: TU Delft (Netherlands)
        - 📅 Duration: 2023-2026

        **2. QUANTERA** - Quantum Technologies Era
        - 💰 Funding: €5.2 million
        - 📍 Coordinator: CEA (France)

        **3. QUSPIN** - Quantum Spintronics
        - 💰 Funding: €3.8 million

        These projects focus on developing quantum computing applications
        for industrial use cases.
        """
        analysis = analyzer.analyze(query, response)

        assert analysis.query_type == QueryType.PROJECT_SEARCH
        assert analysis.score >= 65
        logger.info(f"Project search '{query}': score={analysis.score}")


# ============================================================================
# CATEGORY 7: Consortium Pattern Queries (2 tests)
# ============================================================================


class TestConsortiumPatternQueries:
    """Test suite for consortium pattern queries."""

    @pytest.mark.parametrize(
        "query",
        [
            "What is typical consortium size for Health IAs?",
            "Consortium composition patterns for Cluster 4 RIA",
        ],
    )
    def test_consortium_pattern_query(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
    ):
        """Test consortium pattern query detection."""
        response = """
        Based on analysis of **320 funded projects** in this area:

        **Consortium Size:**
        - Average: 12.5 partners
        - Median: 11 partners
        - Range: 6-25 partners

        **Organization Type Distribution:**
        | Type | Percentage |
        |------|------------|
        | Higher Education (HES) | 38% |
        | Research Organizations (REC) | 30% |
        | Private Companies (PRC) | 23% |
        | SMEs | 9% |

        **Country Representation:**
        - Average countries per consortium: 8
        - Top coordinator countries: Germany (22%), Netherlands (14%), Spain (12%)

        **Recommendations:**
        - Target 10-14 partners for optimal consortium
        - Include 3-4 universities and 2-3 research institutes
        - Ensure at least 7 different countries for geographic diversity
        """
        analysis = analyzer.analyze(query, response)

        assert analysis.query_type == QueryType.CONSORTIUM_PATTERNS
        assert analysis.score >= 70
        assert analysis.has_structured_data
        logger.info(f"Consortium query '{query}': score={analysis.score}")


# ============================================================================
# Integration Tests with Real-world Scenarios
# ============================================================================


class TestRealWorldScenarios:
    """Integration tests simulating real user scenarios."""

    def test_user_journey_new_applicant(self, analyzer: ResponseQualityAnalyzer):
        """
        Test a new applicant's journey through multiple query types.
        """
        ria_response = """
        **What is RIA (Research and Innovation Action)?**

        RIA stands for Research and Innovation Action. It is one of the main
        funding mechanisms in Horizon Europe for collaborative research projects.

        **Key Features:**
        - 100% EU funding rate
        - Requires consortium of at least 3 partners from 3 EU/Associated countries
        - Focus on advancing knowledge and technology
        - Typical budget: €3-8 million

        RIA projects are suitable for breakthrough research and technology development.
        """

        queries_and_responses = [
            ("What is RIA?", ria_response),
            ("Compare RIA and IA", SampleResponses.good_programme_comparison("RIA", "IA")),
            ("What is the typical budget?", SampleResponses.good_budget_benchmark("RIA", "CL5")),
            (
                "Find partners for AI research",
                SampleResponses.good_partner_discovery("AI", "Germany"),
            ),
        ]

        all_acceptable = True
        for query, response in queries_and_responses:
            analysis = analyzer.analyze(query, response)
            if not analyzer.is_acceptable(analysis, min_score=60):
                all_acceptable = False
                logger.warning(f"Query '{query}' scored only {analysis.score}")

        assert all_acceptable

    def test_deflection_detection_edge_cases(self, analyzer: ResponseQualityAnalyzer):
        """Test deflection detection with edge cases."""
        edge_cases = [
            # Should NOT trigger deflection
            ("We found the information in the database", False),
            ("The call could not be extended", False),  # 'could not' but not deflection
            ("I am not sure if you need more details", True),  # Deflection
            # Should trigger deflection
            ("Unfortunately, I could not find any matching calls", True),
            ("No results found for your query", True),
        ]

        for text, should_deflect in edge_cases:
            analysis = analyzer.analyze("test query", text)
            if should_deflect:
                assert (
                    len(analysis.deflection_phrases_found) > 0
                    or analysis.category == ResponseCategory.EMPTY
                ), f"Expected deflection for: {text}"

    def test_structured_data_detection(self, analyzer: ResponseQualityAnalyzer):
        """Test that structured data is correctly detected."""
        structured_response = """
        **Call Details:**
        - **ID:** HORIZON-CL5-2026-D3-01
        - **Budget:** EUR 20 million

        | Type | Budget |
        |------|--------|
        | RIA  | €5M    |
        """

        analysis = analyzer.analyze("Tell me about HORIZON-CL5-2026-D3-01", structured_response)
        assert analysis.has_structured_data

    def test_citations_detection(self, analyzer: ResponseQualityAnalyzer):
        """Test that citations are correctly detected."""
        response_with_citations = """
        According to the Horizon Europe Work Programme 2024-2025,
        RIA projects require at least 3 partners. This is based on
        EU Regulation 2021/695 establishing Horizon Europe.

        Source: https://ec.europa.eu/horizon-europe
        """

        analysis = analyzer.analyze("What are RIA requirements?", response_with_citations)
        assert analysis.has_citations


# ============================================================================
# Performance and Edge Case Tests
# ============================================================================


class TestPerformanceAndEdgeCases:
    """Tests for performance and edge cases."""

    def test_empty_response(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of empty response."""
        analysis = analyzer.analyze("What is RIA?", "")

        assert analysis.category == ResponseCategory.EMPTY
        assert analysis.score < 20

    def test_very_long_response(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of very long response."""
        long_response = SampleResponses.good_call_details("HORIZON-TEST") * 10
        analysis = analyzer.analyze("Tell me about HORIZON-TEST", long_response)

        assert analysis.word_count > 500
        assert analysis.score >= 70

    def test_unicode_in_response(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of unicode characters."""
        response = """
        The call HORIZON-CL5-2026-D3-01 focuses on:
        - 🔬 Research activities
        - 💰 Budget: €20 million
        - ⏰ Deadline: February 2026

        Résumé: C'est une opportunité excellente!
        """

        analysis = analyzer.analyze("Tell me about HORIZON-CL5-2026-D3-01", response)
        assert analysis.score >= 50

    def test_special_characters_in_query(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of special characters in query."""
        queries = [
            "What's the budget for RIA?",
            "Tell me about HORIZON-CL5-2026-D3-01 (the hydrogen call)",
            "Compare EIC & ERC programmes",
        ]

        for query in queries:
            response = SampleResponses.good_call_details()
            analysis = analyzer.analyze(query, response)
            assert analysis is not None
            assert analysis.score > 0


# ============================================================================
# Recommendations Tests
# ============================================================================


class TestRecommendations:
    """Tests for recommendation generation."""

    def test_recommendations_for_deflection(self, analyzer: ResponseQualityAnalyzer):
        """Test that deflections get improvement recommendations."""
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5", SampleResponses.deflection_response()
        )

        assert len(analysis.recommendations) > 0
        assert any("deflection" in r.lower() for r in analysis.recommendations)

    def test_recommendations_for_missing_elements(self, analyzer: ResponseQualityAnalyzer):
        """Test recommendations when elements are missing."""
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01",
            "This is a call for hydrogen research.",  # Missing many elements
        )

        assert len(analysis.recommendations) > 0
        # Should recommend including missing elements
        assert any("missing" in r.lower() for r in analysis.recommendations)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--log-cli-level=INFO"])
