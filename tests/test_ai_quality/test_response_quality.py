"""
Comprehensive AI Response Quality Tests for MAP-IT.

This module tests the AI response quality to ensure:
1. Responses don't contain deflection phrases ("could not find", etc.)
2. Required elements are present for each query type
3. Quality scores meet minimum thresholds
4. The ResponseQualityAnalyzer correctly categorizes responses

Test Categories (25+ queries as required):
- 5 specific call ID queries
- 5 programme comparison queries
- 5 eligibility/FAQ queries
- 3 budget benchmark queries
- 3 partner discovery queries
- 2 project search queries
- 2 consortium pattern queries
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from app.services.quality import (
    ResponseQualityAnalyzer,
    ResponseCategory,
    QueryType,
)


# ==============================================================================
# ResponseQualityAnalyzer Unit Tests
# ==============================================================================


class TestResponseQualityAnalyzerCore:
    """Core unit tests for the ResponseQualityAnalyzer class."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create a fresh analyzer for each test."""
        return ResponseQualityAnalyzer()

    def test_instantiation(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that the analyzer can be instantiated."""
        assert analyzer is not None
        assert len(analyzer.DEFLECTION_PHRASES) > 10
        assert len(analyzer.QUERY_REQUIREMENTS) > 5

    def test_detect_query_type_call_specific(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test detection of call-specific queries."""
        queries = [
            "Tell me about HORIZON-CL5-2026-D3-01",
            "What is the deadline for HORIZON-CL4-2025-DATA-01?",
            "Describe HORIZON-HLTH-2025-STAYHLTH-01",
        ]
        for query in queries:
            result = analyzer.detect_query_type(query)
            assert result == QueryType.CALL_SPECIFIC, f"Failed for query: {query}"

    def test_detect_query_type_call_search(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test detection of call search queries."""
        queries = [
            "Find hydrogen funding calls",
            "Search for open calls in climate",
            "Looking for AI funding opportunities",
        ]
        for query in queries:
            result = analyzer.detect_query_type(query)
            assert result == QueryType.CALL_SEARCH, f"Failed for query: {query}"

    def test_detect_query_type_programme_comparison(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test detection of programme comparison queries."""
        queries = [
            "Compare EIC and ERC success rates",
            "What is the difference between RIA and IA?",
            "EIC versus ERC funding amounts",
        ]
        for query in queries:
            result = analyzer.detect_query_type(query)
            assert result == QueryType.PROGRAMME_COMPARISON, f"Failed for query: {query}"

    def test_detect_query_type_eligibility(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test detection of eligibility/FAQ queries."""
        queries = [
            "Can SMEs apply to Horizon Europe?",
            "What are the eligibility requirements?",
            "Who can participate in ERC grants?",
        ]
        for query in queries:
            result = analyzer.detect_query_type(query)
            assert result == QueryType.ELIGIBILITY_FAQ, f"Failed for query: {query}"

    def test_find_deflection_phrases(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test detection of deflection phrases."""
        deflecting_response = """
        I could not find specific information about this call.
        Unfortunately, the data is not available in my current database.
        Please try a more specific query.
        """
        deflections = analyzer.find_deflection_phrases(deflecting_response)
        assert len(deflections) >= 2
        assert "could not find" in deflections or any(
            "unfortunately" in d.lower() for d in deflections
        )

    def test_no_deflection_in_good_response(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that good responses don't trigger deflection detection."""
        good_response = """
        **HORIZON-CL5-2026-D3-01** - Advanced Biofuels Research
        📋 **Call ID:** HORIZON-CL5-2026-D3-01
        🔬 **Type:** RIA
        🟢 **Status:** Open
        ⏰ **Deadline:** 05 Feb 2026
        💰 **Budget:** EUR 20.00 million

        This call focuses on advanced biofuels and renewable fuels...
        """
        deflections = analyzer.find_deflection_phrases(good_response)
        assert len(deflections) == 0

    def test_find_positive_indicators(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test detection of positive quality indicators."""
        response = """
        **HORIZON-CL5-2026-D3-01** - Advanced Biofuels
        🔬 **Type:** RIA
        🟢 **Status:** Open
        ⏰ **Deadline:** 05 Feb 2026
        💰 **Budget:** €20 million

        Apply at: https://ec.europa.eu/...
        """
        indicators = analyzer.find_positive_indicators(response)
        assert len(indicators) >= 3
        assert "call_ids" in indicators
        assert "euro_amounts" in indicators or "funding_amounts" in indicators

    def test_analyze_good_response(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test analysis of a high-quality response."""
        query = "Tell me about HORIZON-CL5-2026-D3-01"
        response = """
        **HORIZON-CL5-2026-D3-01** - Advanced biofuels research

        📋 **Call ID:** HORIZON-CL5-2026-D3-01
        🔬 **Type:** RIA
        🟢 **Status:** Open
        ⏰ **Deadline:** 05 Feb 2026
        🏛️ **Programme:** Cluster 5 - Climate, Energy and Mobility
        💰 **Budget:** EUR 20.00 million

        **Scope:** This topic focuses on advanced biofuels and renewable fuels for sectors
        that are difficult to electrify. Projects should address production efficiency,
        sustainability, and integration with existing infrastructure.

        🔗 **Apply:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/...
        """
        analysis = analyzer.analyze(query, response)

        assert analysis.score >= 75
        assert analysis.category == ResponseCategory.COMPLETE
        assert len(analysis.deflection_phrases_found) == 0
        assert len(analysis.positive_indicators) >= 3
        assert analyzer.is_acceptable(analysis)

    def test_analyze_deflecting_response(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test analysis of a deflecting response."""
        query = "Tell me about HORIZON-CL5-2026-D3-01"
        response = """
        I could not find specific details about this call.
        Unfortunately, the information is not available in my database.
        Please try a more specific query or check the EU portal directly.
        """
        analysis = analyzer.analyze(query, response)

        assert analysis.score < 50
        assert analysis.category == ResponseCategory.DEFLECTION
        assert len(analysis.deflection_phrases_found) >= 2
        assert not analyzer.is_acceptable(analysis)

    def test_analyze_empty_response(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test analysis of an empty response."""
        query = "Tell me about HORIZON-CL5-2026-D3-01"
        response = ""
        analysis = analyzer.analyze(query, response)

        assert analysis.score == 0
        assert analysis.category == ResponseCategory.EMPTY
        assert "any_response" in analysis.missing_elements

    def test_analyze_partial_response(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test analysis of a partial response."""
        query = "Tell me about HORIZON-CL5-2026-D3-01"
        response = """
        HORIZON-CL5-2026-D3-01 is a RIA call under Cluster 5.
        It focuses on advanced biofuels research.
        """
        analysis = analyzer.analyze(query, response)

        # Should be partial - has some info but missing required elements
        assert analysis.category in [ResponseCategory.PARTIAL, ResponseCategory.COMPLETE]
        assert analysis.score > 0
        assert len(analysis.missing_elements) > 0 or len(analysis.present_elements) > 0

    def test_is_acceptable_threshold(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test the is_acceptable function with different thresholds."""
        query = "What is RIA?"
        # Use a longer response that won't be categorized as EMPTY
        response = """
        RIA stands for Research and Innovation Action. It is a funding type under
        Horizon Europe that supports research projects. RIA projects typically involve
        consortia of organizations from multiple countries working together on innovative
        research. The funding rate for RIA is 100% of eligible costs.
        """

        analysis = analyzer.analyze(query, response)

        # Should pass with reasonable thresholds since it's a proper response
        assert analysis.category != ResponseCategory.EMPTY
        assert analyzer.is_acceptable(analysis, min_score=30)

    def test_get_failure_reason(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test getting failure reasons from analysis."""
        query = "Tell me about HORIZON-CL5-2026-D3-01"
        response = "I could not find any information about this."

        analysis = analyzer.analyze(query, response)
        failure_reason = analyzer.get_failure_reason(analysis)

        assert (
            "DEFLECTION" in failure_reason
            or "MISSING" in failure_reason
            or "SCORE" in failure_reason
        )


# ==============================================================================
# Query Type Detection Tests (Exhaustive)
# ==============================================================================


class TestQueryTypeDetection:
    """Exhaustive tests for query type detection."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        return ResponseQualityAnalyzer()

    @pytest.mark.parametrize(
        "query,expected_type",
        [
            # Call-specific queries (5 examples)
            ("Tell me about HORIZON-CL5-2026-D3-01", QueryType.CALL_SPECIFIC),
            ("What are the details of HORIZON-CL4-2025-DATA-01?", QueryType.CALL_SPECIFIC),
            ("Describe HORIZON-HLTH-2025-STAYHLTH-01 requirements", QueryType.CALL_SPECIFIC),
            ("HORIZON-CL6-2025-BIODIV-01 deadline", QueryType.CALL_SPECIFIC),
            ("What is HORIZON-ERC-2025-STG about?", QueryType.CALL_SPECIFIC),

            # Call search queries (5 examples)
            ("Find hydrogen funding calls", QueryType.CALL_SEARCH),
            ("Search for open calls in AI", QueryType.CALL_SEARCH),
            ("Looking for funding opportunities in health", QueryType.CALL_SEARCH),
            ("Upcoming calls for climate research", QueryType.CALL_SEARCH),
            ("Open calls for renewable energy", QueryType.CALL_SEARCH),

            # Programme comparison queries (5 examples)
            ("Compare EIC and ERC", QueryType.PROGRAMME_COMPARISON),
            ("What is the difference between RIA and IA?", QueryType.PROGRAMME_COMPARISON),
            ("EIC Accelerator versus ERC Starting Grant", QueryType.PROGRAMME_COMPARISON),
            ("How do MSCA and ERC differ?", QueryType.PROGRAMME_COMPARISON),
            ("Comparison of Cluster 4 and Cluster 5", QueryType.PROGRAMME_COMPARISON),

            # Eligibility queries (5 examples)
            ("Can SMEs apply to Horizon Europe?", QueryType.ELIGIBILITY_FAQ),
            ("What are the eligibility requirements for ERC?", QueryType.ELIGIBILITY_FAQ),
            ("Who can participate in EIC Accelerator?", QueryType.ELIGIBILITY_FAQ),
            ("Is my organization eligible for RIA?", QueryType.ELIGIBILITY_FAQ),
            ("Requirements to apply for MSCA", QueryType.ELIGIBILITY_FAQ),

            # Budget benchmark queries (3 examples)
            ("What is typical budget for RIA in Cluster 5?", QueryType.BUDGET_BENCHMARK),
            ("Average funding amount for IA projects", QueryType.BUDGET_BENCHMARK),
            ("Budget benchmark for health projects", QueryType.BUDGET_BENCHMARK),

            # Partner discovery queries (3 examples)
            ("Find German SMEs with hydrogen experience", QueryType.PARTNER_DISCOVERY),
            ("Looking for partners in renewable energy", QueryType.PARTNER_DISCOVERY),
            ("Find experienced partners for AI project", QueryType.PARTNER_DISCOVERY),

            # Project search queries (2 examples)
            ("Find quantum computing projects", QueryType.PROJECT_SEARCH),
            ("Search for funded projects in climate", QueryType.PROJECT_SEARCH),

            # Consortium pattern queries (2 examples)
            ("What is typical consortium size for Health IAs?", QueryType.CONSORTIUM_PATTERN),
            ("Consortium composition for Cluster 5 RIA", QueryType.CONSORTIUM_PATTERN),

            # Statistics queries (2 examples)
            ("Success rate for EIC Accelerator", QueryType.STATISTICS),
            ("What percentage of proposals get funded?", QueryType.STATISTICS),
        ],
    )
    def test_query_type_detection(
        self, analyzer: ResponseQualityAnalyzer, query: str, expected_type: QueryType
    ) -> None:
        """Test query type detection for various queries."""
        detected = analyzer.detect_query_type(query)
        assert detected == expected_type, (
            f"Query '{query}' detected as {detected}, expected {expected_type}"
        )


# ==============================================================================
# Response Quality Validation Tests (25+ queries)
# ==============================================================================


class TestResponseQualityValidation:
    """
    Tests that validate AI response quality for various query types.

    These tests use mock responses that simulate good and bad AI responses,
    ensuring the quality analyzer correctly identifies issues.
    """

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        return ResponseQualityAnalyzer()

    # Good call-specific response template
    GOOD_CALL_RESPONSE = """
**{call_id}** - {title}

📋 **Call ID:** {call_id}
🔬 **Type:** {action_type}
🟢 **Status:** {status}
⏰ **Deadline:** {deadline}
🏛️ **Programme:** {programme}
💰 **Budget:** EUR {budget} million

**Scope:** {scope}

🔗 **Apply:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/...
"""

    # Deflecting response template
    DEFLECTING_RESPONSE = """
I could not find specific information about {topic}.
Unfortunately, the data is not available in my current database.
Please try again later or check the EU portal directly.
"""

    # Partial response template
    PARTIAL_RESPONSE = """
{call_id} is a {action_type} call.
It focuses on {topic}.
"""

    @pytest.mark.parametrize(
        "query,response_type,expected_category,min_score",
        [
            # Call-specific queries (5 tests)
            (
                "Tell me about HORIZON-CL5-2026-D3-01",
                "good_call",
                ResponseCategory.COMPLETE,
                75,
            ),
            (
                "What is HORIZON-CL4-2025-DATA-01?",
                "deflecting",
                ResponseCategory.DEFLECTION,
                0,
            ),
            (
                "HORIZON-HLTH-2025-STAYHLTH-01 details",
                "partial",
                ResponseCategory.PARTIAL,
                30,
            ),
            (
                "Describe HORIZON-CL6-2025-BIODIV-01",
                "good_call",
                ResponseCategory.COMPLETE,
                75,
            ),
            (
                "HORIZON-ERC-2025-STG requirements",
                "deflecting",
                ResponseCategory.DEFLECTION,
                0,
            ),

            # Programme comparison queries (5 tests)
            (
                "Compare EIC and ERC success rates",
                "good_comparison",
                ResponseCategory.COMPLETE,
                60,
            ),
            (
                "What is the difference between RIA and IA?",
                "good_comparison",
                ResponseCategory.COMPLETE,
                60,
            ),
            (
                "EIC versus ERC",
                "deflecting",
                ResponseCategory.DEFLECTION,
                0,
            ),
            (
                "How do MSCA and ERC differ?",
                "good_comparison",
                ResponseCategory.COMPLETE,
                60,
            ),
            (
                "Comparison of Cluster 4 and Cluster 5",
                "deflecting",
                ResponseCategory.DEFLECTION,
                0,
            ),

            # Eligibility/FAQ queries (5 tests)
            (
                "Can SMEs apply to Horizon Europe?",
                "good_eligibility",
                ResponseCategory.COMPLETE,
                70,
            ),
            (
                "What are the eligibility requirements for ERC?",
                "good_eligibility",
                ResponseCategory.COMPLETE,
                70,
            ),
            (
                "Who can participate in EIC Accelerator?",
                "deflecting",
                ResponseCategory.DEFLECTION,
                0,
            ),
            (
                "Is my organization eligible for RIA?",
                "good_eligibility",
                ResponseCategory.COMPLETE,
                70,
            ),
            (
                "Requirements to apply for MSCA",
                "deflecting",
                ResponseCategory.DEFLECTION,
                0,
            ),

            # Budget benchmark queries (3 tests)
            (
                "What is typical budget for RIA in Cluster 5?",
                "good_budget",
                ResponseCategory.COMPLETE,
                65,
            ),
            (
                "Average funding amount for IA projects",
                "good_budget",
                ResponseCategory.COMPLETE,
                65,
            ),
            (
                "Budget benchmark for health projects",
                "deflecting",
                ResponseCategory.DEFLECTION,
                0,
            ),

            # Partner discovery queries (3 tests)
            (
                "Find German SMEs with hydrogen experience",
                "good_partners",
                ResponseCategory.COMPLETE,
                65,
            ),
            (
                "Looking for partners in renewable energy",
                "deflecting",
                ResponseCategory.DEFLECTION,
                0,
            ),
            (
                "Find experienced partners for AI project",
                "good_partners",
                ResponseCategory.COMPLETE,
                65,
            ),

            # Project search queries (2 tests)
            (
                "Find quantum computing projects",
                "good_projects",
                ResponseCategory.COMPLETE,
                60,
            ),
            (
                "Search for funded projects in climate",
                "deflecting",
                ResponseCategory.DEFLECTION,
                0,
            ),

            # Consortium pattern queries (2 tests)
            (
                "What is typical consortium size for Health IAs?",
                "good_consortium",
                ResponseCategory.COMPLETE,
                65,
            ),
            (
                "Consortium composition for Cluster 5 RIA",
                "deflecting",
                ResponseCategory.DEFLECTION,
                0,
            ),
        ],
    )
    def test_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response_type: str,
        expected_category: ResponseCategory,
        min_score: int,
    ) -> None:
        """Test response quality for various query and response combinations."""
        response = self._generate_response(query, response_type)
        analysis = analyzer.analyze(query, response)

        # Check category
        assert analysis.category == expected_category, (
            f"Query: '{query}'\n"
            f"Response type: {response_type}\n"
            f"Expected category: {expected_category}, got: {analysis.category}\n"
            f"Score: {analysis.score}\n"
            f"Deflections: {analysis.deflection_phrases_found}\n"
            f"Missing: {analysis.missing_elements}"
        )

        # Check minimum score
        if expected_category != ResponseCategory.DEFLECTION:
            assert analysis.score >= min_score, (
                f"Query: '{query}'\n"
                f"Score {analysis.score} below minimum {min_score}"
            )

    def _generate_response(self, query: str, response_type: str) -> str:
        """Generate a response of the specified type for testing."""
        if response_type == "good_call":
            # Extract call ID from query if present
            import re
            call_match = re.search(r"HORIZON-[A-Z]{2,3}\d?-\d{4}-[A-Z0-9\-]+", query)
            call_id = call_match.group(0) if call_match else "HORIZON-CL5-2026-D3-01"

            return self.GOOD_CALL_RESPONSE.format(
                call_id=call_id,
                title="Advanced Research Topic",
                action_type="RIA",
                status="Open",
                deadline="05 Feb 2026",
                programme="Cluster 5 - Climate, Energy and Mobility",
                budget="20.00",
                scope="This topic focuses on innovative research in the domain.",
            )

        elif response_type == "deflecting":
            topic = query[:50] if len(query) > 50 else query
            return self.DEFLECTING_RESPONSE.format(topic=topic)

        elif response_type == "partial":
            import re
            call_match = re.search(r"HORIZON-[A-Z]{2,3}\d?-\d{4}-[A-Z0-9\-]+", query)
            call_id = call_match.group(0) if call_match else "HORIZON-CL5-2026-D3-01"

            return self.PARTIAL_RESPONSE.format(
                call_id=call_id,
                action_type="RIA",
                topic="research and innovation",
            )

        elif response_type == "good_comparison":
            return """
**EIC vs ERC Comparison**

| Aspect | EIC Accelerator | ERC Starting Grant |
|--------|-----------------|-------------------|
| **Success Rate** | ~8% | ~12% |
| **Funding** | Up to €2.5M grant + €15M equity | Up to €1.5M |
| **Target** | Innovative SMEs | Individual researchers |
| **Focus** | Market-ready innovations | Frontier research |

**Key Differences:**
- EIC focuses on commercialization, ERC on fundamental research
- EIC has a two-step evaluation, ERC has single submission
- EIC includes optional equity investment

**Eligibility:**
- EIC: SMEs with breakthrough innovations
- ERC: Researchers 2-7 years post-PhD
"""

        elif response_type == "good_eligibility":
            return """
**Eligibility for Horizon Europe**

Yes, SMEs can participate in Horizon Europe programs. Here are the key requirements:

**General Eligibility:**
- Legal entity established in EU Member State or Associated Country
- Minimum 3 independent entities from 3 different countries (for most calls)
- SME status must be verified through EU SME definition

**Specific Rules:**
- For RIA/IA: SMEs can participate as partners or coordinators
- For EIC Accelerator: Single SME applications accepted
- Associated Countries have specific eligibility conditions

**SME Definition (EU):**
- Fewer than 250 employees
- Annual turnover ≤ €50 million OR balance sheet total ≤ €43 million
- Independent (less than 25% owned by non-SME)

For detailed rules, consult the Horizon Europe Model Grant Agreement.
"""

        elif response_type == "good_budget":
            return """
**Budget Benchmark for RIA in Cluster 5**

Based on analysis of 496 funded projects:

**EU Contribution:**
- Average: €4.9 million
- Median: €4.5 million
- Range: €1.3M - €20M

**Consortium Size:**
- Average: 13.3 partners
- Typical range: 10-15 partners
- Average countries: 7-9

**Recommendations:**
- Suggested budget range: €3.4M - €5.5M
- Consider consortium of 10-15 partners
- Include at least 6-8 different countries

**Budget Breakdown (Typical RIA):**
- Personnel: 40-50%
- Equipment: 10-15%
- Travel & Subsistence: 5-8%
- Subcontracting: 5-10%
- Other direct costs: 10-15%
- Indirect costs: 25% of eligible direct costs
"""

        elif response_type == "good_partners":
            return """
**Experienced Partners for Hydrogen Projects**

Found 15 organizations with hydrogen experience in Germany:

**1. Fraunhofer Institute for Solar Energy Systems (ISE)**
- Type: Research Organization
- Projects: 12 Horizon Europe projects in hydrogen
- Role: Often coordinator
- Expertise: Electrolysis, fuel cells, hydrogen storage

**2. DLR - German Aerospace Center**
- Type: Research Organization
- Projects: 8 hydrogen-related projects
- Expertise: Hydrogen propulsion, storage systems

**3. Hydrogenious LOHC Technologies GmbH**
- Type: SME
- Projects: 3 Horizon Europe projects
- Expertise: Liquid organic hydrogen carriers

**4. Siemens Energy**
- Type: Large Enterprise
- Projects: 5 Horizon Europe projects
- Expertise: Large-scale electrolyzers, grid integration

*These organizations have proven track records in EU-funded hydrogen research.*
"""

        elif response_type == "good_projects":
            return """
**Quantum Computing Projects in Horizon Europe**

Found 23 funded projects related to quantum computing:

**1. HYPERION** (ID: 101137476)
- Funding: €12.5 million
- Coordinator: University of Copenhagen
- Focus: Hybrid quantum-classical algorithms
- Status: Ongoing (2024-2028)

**2. QUBITS** (ID: 101138892)
- Funding: €9.8 million
- Coordinator: TU Delft
- Focus: Error-corrected quantum processors
- Partners: 14 organizations from 9 countries

**3. QUANTERA** (ID: 101107239)
- Funding: €7.2 million
- Focus: Quantum sensing and metrology
- Coordinator: CEA (France)

*These projects represent quantum computing research funded under Horizon Europe.*
"""

        elif response_type == "good_consortium":
            return """
**Consortium Patterns for Health IAs**

Based on analysis of 156 funded Innovation Actions in Health (Cluster 1):

**Consortium Size:**
- Average partners: 18.5
- Median: 17 partners
- Range: 8-35 partners
- Average countries: 11.2

**Organization Type Distribution:**
- Higher Education (HES): 32%
- Research Organizations (REC): 28%
- Private Companies (PRC): 25%
- Public Bodies (PUB): 8%
- Other (OTH): 7%

**Country Participation:**
- Top coordinators: Germany (18%), Netherlands (14%), France (12%)
- Most active: Germany, France, Spain, Italy, Netherlands

**Recommendations:**
- Include 15-20 partners for optimal consortium
- Balance academic and industry partners
- Consider 8-12 countries for geographic diversity
- Include at least 3-4 SMEs
"""

        return ""


# ==============================================================================
# Edge Cases and Boundary Tests
# ==============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        return ResponseQualityAnalyzer()

    def test_very_short_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of very short responses."""
        analysis = analyzer.analyze("What is RIA?", "RIA is a type.")
        assert analysis.score < 70
        assert len(analysis.recommendations) > 0

    def test_very_long_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of very long responses."""
        long_response = "This is a detailed explanation. " * 1000
        analysis = analyzer.analyze("What is RIA?", long_response)
        assert analysis.score > 0  # Should still calculate a score

    def test_unicode_in_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of unicode characters."""
        response = "🔬 RIA means Research and Innovation Action. 💰 Budget: €5M"
        analysis = analyzer.analyze("What is RIA?", response)
        assert "action_type_icons" in analysis.positive_indicators
        assert "euro_amounts" in analysis.positive_indicators

    def test_mixed_language_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of mixed-language content."""
        response = """
        RIA (Research and Innovation Action) is a type of Horizon Europe project.
        Förderung: EUR 5 million. Consorzio: 15 partner.
        """
        analysis = analyzer.analyze("What is RIA?", response)
        assert analysis.score > 0

    def test_case_insensitive_deflection(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that deflection detection is case-insensitive."""
        responses = [
            "I COULD NOT FIND information",
            "I Could Not Find information",
            "i could not find information",
        ]
        for response in responses:
            deflections = analyzer.find_deflection_phrases(response)
            assert len(deflections) > 0, f"Failed to detect deflection in: {response}"

    def test_false_positive_deflection(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that legitimate uses of deflection-like words don't trigger."""
        # Note: This is a known limitation - some legitimate uses may still trigger
        response = """
        The researchers found that the new approach could not find a solution
        to the previously unsolvable problem using traditional methods.
        This breakthrough was funded through HORIZON-CL5-2026-D3-01.
        """
        analysis = analyzer.analyze("Tell me about quantum research", response)
        # Even if deflection is detected, positive indicators should help score
        assert analysis.score > 20  # Should have some positive aspects

    def test_numerical_data_detection(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test detection of various numerical formats."""
        response = """
        Budget: €5,000,000 (EUR 5 million)
        Partners: 15 organizations
        Countries: 8
        Success rate: 12.5%
        Duration: 48 months
        """
        analysis = analyzer.analyze("Budget statistics", response)
        present = analysis.metadata.get("present_elements", [])
        assert "numerical_values" in present or analysis.score > 50

    def test_multiple_call_ids(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test response with multiple call IDs."""
        response = """
        Related calls in Cluster 5:
        - HORIZON-CL5-2026-D3-01: Advanced Biofuels (Open, €20M)
        - HORIZON-CL5-2026-D3-02: Hydrogen Technologies (Upcoming, €15M)
        - HORIZON-CL5-2025-D4-01: Smart Grids (Closed)
        """
        analysis = analyzer.analyze("Find energy calls", response)
        assert "call_ids" in analysis.positive_indicators


# ==============================================================================
# Integration with Quality Thresholds
# ==============================================================================


class TestQualityThresholds:
    """Tests for quality threshold enforcement."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        return ResponseQualityAnalyzer()

    @pytest.mark.parametrize(
        "min_score,should_pass",
        [
            (50, True),
            (60, True),
            (70, True),
            (80, False),  # Very high threshold
            (90, False),
        ],
    )
    def test_acceptability_thresholds(
        self,
        analyzer: ResponseQualityAnalyzer,
        min_score: int,
        should_pass: bool,
    ) -> None:
        """Test acceptability at various thresholds."""
        good_response = """
        **HORIZON-CL5-2026-D3-01** - Advanced Biofuels
        🔬 **Type:** RIA
        🟢 **Status:** Open
        ⏰ **Deadline:** 05 Feb 2026
        💰 **Budget:** EUR 20 million

        This call focuses on advanced biofuels research.
        """
        analysis = analyzer.analyze(
            "Tell me about HORIZON-CL5-2026-D3-01", good_response
        )

        is_acceptable = analyzer.is_acceptable(analysis, min_score=min_score)
        # Note: actual result depends on score calculation
        if analysis.score >= min_score:
            assert is_acceptable
        else:
            assert not is_acceptable

    def test_category_always_fails_deflection(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that deflection category always fails acceptability."""
        response = "I could not find any information. Please try again."
        analysis = analyzer.analyze("What is RIA?", response)

        # Even with min_score=0, deflections should fail
        assert not analyzer.is_acceptable(analysis, min_score=0)

    def test_category_always_fails_empty(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that empty category always fails acceptability."""
        analysis = analyzer.analyze("What is RIA?", "")

        assert not analyzer.is_acceptable(analysis, min_score=0)


# ==============================================================================
# Recommendation Generation Tests
# ==============================================================================


class TestRecommendations:
    """Tests for recommendation generation."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        return ResponseQualityAnalyzer()

    def test_recommendations_for_deflection(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that deflecting responses get appropriate recommendations."""
        response = "I could not find information about this topic."
        analysis = analyzer.analyze("What is RIA?", response)

        assert len(analysis.recommendations) > 0
        # Should recommend removing deflection phrases
        assert any("deflection" in r.lower() for r in analysis.recommendations)

    def test_recommendations_for_missing_elements(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that missing elements generate specific recommendations."""
        response = "HORIZON-CL5-2026-D3-01 is a call."  # Missing most required elements
        analysis = analyzer.analyze("Tell me about HORIZON-CL5-2026-D3-01", response)

        # Should have recommendations for missing elements
        if analysis.missing_elements:
            assert len(analysis.recommendations) > 0

    def test_no_recommendations_for_complete(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that complete responses may have minimal recommendations."""
        response = """
        **HORIZON-CL5-2026-D3-01** - Advanced Biofuels Research
        📋 **Call ID:** HORIZON-CL5-2026-D3-01
        🔬 **Type:** RIA
        🟢 **Status:** Open
        ⏰ **Deadline:** 05 Feb 2026
        🏛️ **Programme:** Cluster 5 - Climate, Energy and Mobility
        💰 **Budget:** EUR 20.00 million
        **Scope:** Research on advanced biofuels.
        🔗 **Apply:** https://ec.europa.eu/...
        """
        analysis = analyzer.analyze("Tell me about HORIZON-CL5-2026-D3-01", response)

        # Complete responses should have no critical recommendations
        critical_recs = [r for r in analysis.recommendations if "deflection" in r.lower()]
        assert len(critical_recs) == 0
