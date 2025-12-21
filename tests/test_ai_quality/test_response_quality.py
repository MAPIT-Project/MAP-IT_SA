"""
Comprehensive AI Response Quality Tests

This test suite validates that AI responses meet quality standards
and do not contain deflection patterns. It tests various query types
with both positive and negative test cases.

Tests are organized by:
1. Deflection Detection Tests
2. Element Completeness Tests
3. Quality Scoring Tests
4. Query Type Specific Tests (call info, project info, comparisons, etc.)
5. Edge Cases and Error Handling
"""

import pytest

from app.services.quality.response_quality_analyzer import (
    QualityAnalysis,
    ResponseCategory,
    ResponseQualityAnalyzer,
)


class TestDeflectionDetection:
    """Tests for deflection phrase detection."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    @pytest.mark.parametrize(
        "response,expected_deflections",
        [
            # Clear deflection phrases
            (
                "I could not find specific information about this call.",
                ["could not find"],
            ),
            (
                "No information available for HORIZON-CL5-2026-D3-01.",
                ["no information available"],
            ),
            (
                "I am not sure about the deadline for this call.",
                ["I am not sure"],
            ),
            (
                "Unable to retrieve the budget information at this time.",
                ["unable to retrieve"],
            ),
            (
                "I found some information but could not extract specific details.",
                ["found some information but", "could not extract specific details"],
            ),
            # Multiple deflection phrases
            (
                "I could not find information and I am not sure about the details. "
                "Please try a more specific query.",
                ["could not find", "I am not sure", "please try a more specific"],
            ),
            # No deflection
            (
                "The call HORIZON-CL5-2026-D3-01 has a deadline of 05 Feb 2026 "
                "with a budget of EUR 20 million.",
                [],
            ),
        ],
    )
    def test_deflection_phrase_detection(
        self,
        analyzer: ResponseQualityAnalyzer,
        response: str,
        expected_deflections: list[str],
    ) -> None:
        """Test that deflection phrases are correctly detected."""
        analysis = analyzer.analyze(
            query="Tell me about this call",
            response=response,
            query_type="call_info",
        )

        # Check that expected deflections were found
        for expected in expected_deflections:
            assert any(
                expected.lower() in found.lower() for found in analysis.deflection_phrases_found
            ), f"Expected deflection '{expected}', got {analysis.deflection_phrases_found}"

        # If we expected deflections, category should reflect that
        if expected_deflections:
            assert analysis.category in [
                ResponseCategory.DEFLECTION,
                ResponseCategory.PARTIAL,
            ]
            assert analysis.score < 80

    @pytest.mark.parametrize(
        "response,should_detect_evasion",
        [
            # Evasion patterns
            (
                "You should try checking the official EU funding portal for details.",
                True,
            ),
            (
                "I recommend checking the European Commission website.",
                True,
            ),
            (
                "For more information, visit the official portal.",
                True,
            ),
            # Not evasion
            (
                "The RIA project has 15 partners from 8 countries. "
                "The total budget is EUR 5 million.",
                False,
            ),
        ],
    )
    def test_evasion_pattern_detection(
        self,
        analyzer: ResponseQualityAnalyzer,
        response: str,
        should_detect_evasion: bool,
    ) -> None:
        """Test that evasion patterns are detected."""
        analysis = analyzer.analyze(
            query="What is the budget?",
            response=response,
            query_type="general_faq",
        )

        has_evasion = len(analysis.deflection_phrases_found) > 0

        if should_detect_evasion:
            assert has_evasion, f"Expected evasion but none found in: {response}"
        else:
            assert not has_evasion, f"Unexpected evasion found: {analysis.deflection_phrases_found}"


class TestElementCompleteness:
    """Tests for checking required elements in responses."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    def test_call_info_complete_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that a complete call info response scores high."""
        response = """
        **HORIZON-CL5-2026-D3-01 - Advanced Biofuels**

        - **Type:** RIA (Research and Innovation Action)
        - **Status:** Open
        - **Deadline:** 05 February 2026
        - **Budget:** EUR 20.00 million

        **Scope:** This topic focuses on developing advanced biofuels
        for sustainable transportation. Projects should demonstrate
        innovative conversion technologies.

        **Apply:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/
        """

        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=response,
            query_type="call_info",
            expected_elements=["deadline", "budget", "type", "status"],
        )

        assert analysis.category == ResponseCategory.COMPLETE
        assert analysis.score >= 80
        assert len(analysis.missing_elements) == 0

    def test_call_info_incomplete_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that an incomplete call info response is detected."""
        response = """
        **HORIZON-CL5-2026-D3-01 - Advanced Biofuels**

        This is a call about biofuels. I'm not sure about the specific details.
        """

        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=response,
            query_type="call_info",
            expected_elements=["deadline", "budget", "type", "status"],
        )

        assert analysis.category in [ResponseCategory.PARTIAL, ResponseCategory.DEFLECTION]
        assert analysis.score < 70
        assert len(analysis.missing_elements) > 0

    def test_project_info_elements(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test project info element detection."""
        response = """
        **Project: GREENTECH**

        **Objective:** This project aims to develop sustainable technologies
        for renewable energy integration in urban environments.

        **Participants:**
        - Technical University of Munich (Coordinator)
        - Fraunhofer Institute
        - CNRS (France)

        **Budget:** EUR 4.5 million over 48 months
        """

        analysis = analyzer.analyze(
            query="Tell me about GREENTECH project",
            response=response,
            query_type="project_info",
            expected_elements=["title", "objective", "participants"],
        )

        assert analysis.category == ResponseCategory.COMPLETE
        assert analysis.score >= 75
        assert "objective" not in analysis.missing_elements
        assert "participants" not in analysis.missing_elements


class TestQualityScoring:
    """Tests for quality scoring algorithm."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    def test_perfect_score(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that ideal response gets high score."""
        response = """
        The EIC Accelerator has a success rate of approximately 8%, making it
        one of the most competitive EU funding programmes. The average grant
        size is EUR 2.5 million for the grant component, with additional
        equity investment of up to EUR 15 million available.

        Key eligibility requirements:
        - Single SME or small mid-cap (up to 500 employees)
        - Breakthrough innovation with high market potential
        - Disruptive technology or business model

        The 2024 cut-off dates are: March 13, June 5, and October 2.
        """

        analysis = analyzer.analyze(
            query="What is EIC Accelerator success rate?",
            response=response,
            query_type="general_faq",
        )

        assert analysis.score >= 80
        assert analysis.category == ResponseCategory.COMPLETE
        assert analysis.is_acceptable()

    def test_deflection_reduces_score(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that deflection significantly reduces score."""
        response = """
        I could not find specific success rate information for EIC Accelerator.
        You should try checking the official EC website for the latest statistics.
        """

        analysis = analyzer.analyze(
            query="What is EIC Accelerator success rate?",
            response=response,
            query_type="general_faq",
        )

        assert analysis.score < 50
        assert analysis.category == ResponseCategory.DEFLECTION
        assert not analysis.is_acceptable()

    def test_short_response_penalty(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that very short responses are penalized."""
        response = "Yes, SMEs can apply to Horizon Europe."

        analysis = analyzer.analyze(
            query="Can SMEs apply to Horizon Europe?",
            response=response,
            query_type="general_faq",
        )

        assert analysis.score < 80
        assert analysis.metadata["is_too_short"]

    def test_empty_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that empty responses get zero score."""
        analysis = analyzer.analyze(
            query="What is the deadline?",
            response="",
            query_type="call_info",
        )

        assert analysis.score == 0
        assert analysis.category == ResponseCategory.EMPTY

    def test_error_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that error responses are categorized correctly."""
        response = "An error occurred while processing your request. Service unavailable."

        analysis = analyzer.analyze(
            query="Tell me about the call",
            response=response,
            query_type="call_info",
        )

        assert analysis.category == ResponseCategory.ERROR
        assert analysis.score == 0


class TestCallInfoQueries:
    """Tests for call information query responses."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    @pytest.mark.parametrize(
        "query,response,expected_min_score,expected_elements_present",
        [
            # Complete call info
            (
                "Tell me about HORIZON-CL5-2026-D3-01",
                """
                **HORIZON-CL5-2026-D3-01**

                - Type: RIA (Research and Innovation Action)
                - Status: Open
                - Deadline: 05 February 2026
                - Budget: EUR 20 million

                This call focuses on advanced biofuels for sustainable transport.
                """,
                75,
                ["type", "status", "deadline", "budget"],
            ),
            # Missing budget
            (
                "Tell me about HORIZON-CL4-2025-DATA-01",
                """
                **HORIZON-CL4-2025-DATA-01**

                - Type: IA (Innovation Action)
                - Status: Upcoming
                - Deadline: 15 September 2025

                Focus on data spaces for European industry.
                """,
                60,
                ["type", "status", "deadline"],
            ),
            # Hydrogen call
            (
                "Tell me about hydrogen funding calls",
                """
                There are 5 open calls related to hydrogen in Horizon Europe:

                1. **HORIZON-CL5-2025-D3-01** - Green hydrogen production
                   - Type: RIA
                   - Deadline: March 2025
                   - Budget: EUR 15M

                2. **HORIZON-CL5-2025-D3-02** - Hydrogen storage
                   - Type: IA
                   - Deadline: March 2025
                   - Budget: EUR 12M
                """,
                70,
                ["type", "deadline"],
            ),
        ],
    )
    def test_call_info_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        expected_min_score: int,
        expected_elements_present: list[str],
    ) -> None:
        """Test call information response quality."""
        analysis = analyzer.analyze(
            query=query,
            response=response,
            query_type="call_info",
            expected_elements=expected_elements_present,
        )

        assert analysis.score >= expected_min_score, (
            f"Score {analysis.score} below minimum {expected_min_score}. "
            f"Missing: {analysis.missing_elements}"
        )

        # Verify expected elements are detected
        for element in expected_elements_present:
            assert element not in analysis.missing_elements, (
                f"Element '{element}' expected but listed as missing"
            )


class TestProjectQueries:
    """Tests for project search and info query responses."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    @pytest.mark.parametrize(
        "query,response,expected_min_score",
        [
            # Complete project info
            (
                "Find quantum computing projects",
                """
                Found 25 funded projects related to quantum computing:

                1. **QUSPIN** - Quantum Spintronic Devices
                   - Objective: Develop quantum spintronic devices for computing
                   - Partners: TU Munich (coord), CEA, Imec
                   - Budget: EUR 4.2 million
                   - Duration: 48 months (2022-2026)

                2. **QUANTERA** - Quantum Computing Algorithms
                   - Objective: Research novel quantum algorithms
                   - Partners: University of Vienna, ETH Zurich
                   - Budget: EUR 3.8 million
                """,
                70,
            ),
            # Hydrogen projects
            (
                "Show hydrogen research projects in Germany",
                """
                Found 18 hydrogen projects with German participants:

                1. **H2FUTURE** - Green Hydrogen from Renewables
                   - Coordinator: Voestalpine Stahl
                   - German partners: Siemens Energy, TU Dresden
                   - Funding: EUR 17.8 million

                2. **HYDRASOL** - Solar Hydrogen Production
                   - Partners include Max Planck Institute
                   - Focus: Thermochemical water splitting
                """,
                70,
            ),
        ],
    )
    def test_project_search_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        expected_min_score: int,
    ) -> None:
        """Test project search response quality."""
        analysis = analyzer.analyze(
            query=query,
            response=response,
            query_type="project_info",
        )

        assert analysis.score >= expected_min_score, (
            f"Score {analysis.score} below minimum {expected_min_score}. "
            f"Issues: {analysis.recommendations}"
        )
        assert analysis.category != ResponseCategory.DEFLECTION


class TestComparisonQueries:
    """Tests for programme comparison query responses."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    @pytest.mark.parametrize(
        "query,response,expected_min_score",
        [
            # EIC vs ERC comparison
            (
                "Compare EIC Accelerator and ERC Starting Grant",
                """
                **EIC Accelerator vs ERC Starting Grant Comparison**

                | Aspect | EIC Accelerator | ERC Starting Grant |
                |--------|-----------------|-------------------|
                | Target | SMEs, start-ups | Individual researchers |
                | Funding | Up to EUR 17.5M | Up to EUR 1.5M |
                | Success Rate | ~8% | ~10-15% |
                | Focus | Market innovation | Frontier research |
                | Duration | Up to 24 months | 5 years |

                **Key Differences:**
                - EIC focuses on commercialization while ERC supports basic research
                - EIC requires SME status, ERC requires 2-7 years post-PhD
                """,
                75,
            ),
            # RIA vs IA comparison
            (
                "Compare RIA and IA grant types",
                """
                **RIA (Research and Innovation Action) vs IA (Innovation Action)**

                **RIA:**
                - Focus: Research activities closer to TRL 2-5
                - Funding rate: 100%
                - Typical consortium: 10-15 partners

                **IA:**
                - Focus: Closer-to-market activities (TRL 5-8)
                - Funding rate: 70% (100% for non-profits)
                - Typical consortium: 8-12 partners

                The main difference is TRL level and commercialization focus.
                """,
                75,
            ),
        ],
    )
    def test_comparison_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        expected_min_score: int,
    ) -> None:
        """Test comparison response quality."""
        analysis = analyzer.analyze(
            query=query,
            response=response,
            query_type="programme_comparison",
        )

        assert analysis.score >= expected_min_score, (
            f"Score {analysis.score} below minimum {expected_min_score}. "
            f"Issues: {analysis.recommendations}"
        )
        assert analysis.category in [ResponseCategory.COMPLETE, ResponseCategory.PARTIAL]


class TestBudgetBenchmarkQueries:
    """Tests for budget benchmark query responses."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    @pytest.mark.parametrize(
        "query,response,expected_min_score",
        [
            # Complete budget benchmark
            (
                "What is typical budget for Horizon RIA in Cluster 5?",
                """
                **Budget Benchmark for Cluster 5 RIA Projects**

                Based on 496 funded projects analyzed:

                - **Average Budget:** EUR 4.9 million
                - **Median Budget:** EUR 4.5 million
                - **Range:** EUR 1.3M - EUR 20M
                - **Typical Consortium Size:** 12-15 partners

                **Budget by Organization Type:**
                - Research organizations (REC): 34%
                - Private companies (PRC): 34%
                - Higher education (HES): 28%

                **Recommendation:** Target EUR 3.5M - 5.5M for competitive proposals.
                """,
                75,
            ),
            # Health cluster benchmark
            (
                "Budget benchmark for Health IA projects",
                """
                **Health Cluster IA Budget Statistics**

                Analyzed 280 funded IA projects in Cluster 1 (Health):

                - Average EU contribution: EUR 5.2 million
                - Most common range: EUR 4-6 million
                - Consortium average: 14 partners from 9 countries

                **Note:** Health IAs tend to be larger due to clinical trials.
                """,
                70,
            ),
        ],
    )
    def test_budget_benchmark_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        expected_min_score: int,
    ) -> None:
        """Test budget benchmark response quality."""
        analysis = analyzer.analyze(
            query=query,
            response=response,
            query_type="budget_benchmark",
            expected_elements=["budget_range", "source_count"],
        )

        assert analysis.score >= expected_min_score, (
            f"Score {analysis.score} below minimum {expected_min_score}. "
            f"Issues: {analysis.recommendations}"
        )


class TestPartnerDiscoveryQueries:
    """Tests for partner discovery query responses."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    @pytest.mark.parametrize(
        "query,response,expected_min_score",
        [
            # Complete partner discovery
            (
                "Find German SMEs with hydrogen experience",
                """
                **Partner Discovery: German SMEs with Hydrogen Experience**

                Found 47 organizations matching your criteria:

                **Top Recommendations:**

                1. **H2 TechSolutions GmbH** (Stuttgart)
                   - 5 Horizon projects, EUR 12M total funding
                   - Experience: Fuel cell development, electrolyzer systems
                   - Previous roles: Coordinator in 2 projects

                2. **Greenhydrogen AG** (Munich)
                   - 3 Horizon projects as partner
                   - Expertise: Green hydrogen production, PEM technology
                   - Connected to major research networks

                3. **Elektrolysebau GmbH** (Hamburg)
                   - 4 projects, strong in CLUSTER-5 calls
                   - Focus: Industrial-scale electrolyzers
                """,
                75,
            ),
            # French research partners
            (
                "Find experienced partners for AI project in France",
                """
                **French AI Research Partners**

                Found 35 organizations with AI expertise in France:

                1. **INRIA** - Top AI research institute
                   - 45+ Horizon projects coordinated
                   - Expertise: Machine learning, robotics, NLP

                2. **CEA List** - Applied AI research
                   - Strong track record in industrial AI
                   - 28 Horizon participations

                3. **Institut Pasteur** - AI for healthcare
                   - Specialized in biomedical AI
                   - Partner in 15 health AI projects
                """,
                75,
            ),
        ],
    )
    def test_partner_discovery_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        expected_min_score: int,
    ) -> None:
        """Test partner discovery response quality."""
        analysis = analyzer.analyze(
            query=query,
            response=response,
            query_type="partner_discovery",
            expected_elements=["partners_found", "experience_info"],
        )

        assert analysis.score >= expected_min_score, (
            f"Score {analysis.score} below minimum {expected_min_score}. "
            f"Issues: {analysis.recommendations}"
        )


class TestFAQQueries:
    """Tests for general FAQ query responses."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    @pytest.mark.parametrize(
        "query,response,expected_min_score",
        [
            # Eligibility question
            (
                "Can SMEs apply to LIFE Programme?",
                """
                Yes, SMEs can apply to the LIFE Programme. Here are the key points:

                **Eligibility Requirements:**
                - Legal entities established in EU Member States
                - Must be properly registered as an SME (< 250 employees)
                - Can participate as coordinator or partner

                **Types of LIFE calls open to SMEs:**
                - Standard Action Projects (SAPs)
                - Strategic Integrated Projects (SIPs)
                - Technical Assistance Projects

                **Funding rates:**
                - Standard: 60-75% of eligible costs
                - Non-profit organizations: up to 95%

                SMEs often participate in consortia with larger organizations
                or environmental NGOs.
                """,
                75,
            ),
            # Consortium requirements
            (
                "What are the minimum consortium requirements for RIA?",
                """
                **RIA Consortium Requirements**

                For Research and Innovation Actions (RIA) in Horizon Europe:

                **Minimum Requirements:**
                - At least 3 independent legal entities
                - From at least 3 different EU Member States or Associated Countries

                **Typical Successful Consortia:**
                - 10-15 partners on average
                - Mix of academia, research centers, and industry
                - Geographic balance across Europe

                **Exceptions:**
                - ERC grants: Single PI applications
                - MSCA: May have different requirements
                - Some topics specify different minimums

                **Tip:** Check the specific call topic for any additional requirements.
                """,
                75,
            ),
        ],
    )
    def test_faq_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        expected_min_score: int,
    ) -> None:
        """Test FAQ response quality."""
        analysis = analyzer.analyze(
            query=query,
            response=response,
            query_type="general_faq",
        )

        assert analysis.score >= expected_min_score, (
            f"Score {analysis.score} below minimum {expected_min_score}. "
            f"Issues: {analysis.recommendations}"
        )
        assert analysis.category != ResponseCategory.DEFLECTION


class TestConsortiumPatternQueries:
    """Tests for consortium pattern query responses."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    @pytest.mark.parametrize(
        "query,response,expected_min_score",
        [
            # Health IA consortium patterns
            (
                "What is typical consortium size for Health IAs?",
                """
                **Consortium Patterns for Health Innovation Actions (IAs)**

                Based on analysis of 180 funded Health IA projects:

                **Consortium Size:**
                - Average: 14.5 partners
                - Median: 13 partners
                - Range: 8 to 28 partners

                **Geographic Distribution:**
                - Average 9 countries per consortium
                - Top participating countries: DE, FR, IT, ES, NL

                **Organization Type Distribution:**
                - Higher Education (HES): 32%
                - Research Centers (REC): 28%
                - Private Companies (PRC): 25%
                - Hospitals/Clinics: 10%
                - Other: 5%

                **Coordinator Profile:**
                - 45% University coordinators
                - 30% Research institute coordinators
                - 20% Company coordinators
                - 5% Hospital coordinators
                """,
                75,
            ),
        ],
    )
    def test_consortium_pattern_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        expected_min_score: int,
    ) -> None:
        """Test consortium pattern response quality."""
        analysis = analyzer.analyze(
            query=query,
            response=response,
            query_type="budget_benchmark",  # Similar structure
        )

        assert analysis.score >= expected_min_score


class TestToolResultValidation:
    """Tests for tool result validation."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    def test_tool_success_validation(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that successful tool results don't add issues."""
        response = "Found 15 hydrogen funding calls with details..."
        tool_results = {
            "search_funding_calls": {
                "success": True,
                "calls_found": 15,
                "items": [{"id": "call1"}, {"id": "call2"}],
            }
        }

        analysis = analyzer.analyze(
            query="Find hydrogen calls",
            response=response,
            query_type="call_info",
            tool_results=tool_results,
        )

        assert len(analysis.metadata.get("tool_issues", [])) == 0

    def test_tool_error_validation(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that tool errors are captured."""
        response = "I found some information about calls..."
        tool_results = {
            "search_funding_calls": {
                "success": False,
                "error": "Database connection failed",
            }
        }

        analysis = analyzer.analyze(
            query="Find hydrogen calls",
            response=response,
            query_type="call_info",
            tool_results=tool_results,
        )

        assert len(analysis.metadata.get("tool_issues", [])) > 0

    def test_empty_tool_results(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that empty tool results are flagged."""
        response = "Based on my search, here is what I found..."
        tool_results = {
            "search_projects": {
                "success": True,
                "count": 0,
                "items": [],
            }
        }

        analysis = analyzer.analyze(
            query="Find AI projects",
            response=response,
            query_type="project_info",
            tool_results=tool_results,
        )

        tool_issues = analysis.metadata.get("tool_issues", [])
        assert len(tool_issues) > 0 or analysis.score < 80


class TestBatchAnalysis:
    """Tests for batch analysis functionality."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    def test_batch_analysis(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test batch analysis of multiple responses."""
        items = [
            (
                "What is RIA?",
                "RIA is Research and Innovation Action, a type of Horizon Europe grant.",
                "general_faq",
            ),
            (
                "Find hydrogen calls",
                "I could not find any information about hydrogen calls.",
                "call_info",
            ),
            (
                "EIC success rate?",
                "The EIC Accelerator has approximately 8% success rate.",
                "general_faq",
            ),
        ]

        analyses = analyzer.analyze_batch(items)

        assert len(analyses) == 3
        assert isinstance(analyses[0], QualityAnalysis)

    def test_aggregate_stats(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test aggregate statistics from batch analysis."""
        # Create analyses with known outcomes
        items = [
            ("Q1", "A good complete answer with lots of details.", "general_faq"),
            ("Q2", "I could not find specific information.", "call_info"),
            ("Q3", "Another good answer with details.", "general_faq"),
        ]

        analyses = analyzer.analyze_batch(items)
        stats = analyzer.get_aggregate_stats(analyses)

        assert stats["total_analyzed"] == 3
        assert "average_score" in stats
        assert "acceptable_rate" in stats
        assert "category_distribution" in stats


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create analyzer instance for tests."""
        return ResponseQualityAnalyzer()

    def test_whitespace_only_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of whitespace-only responses."""
        analysis = analyzer.analyze(
            query="What is the deadline?",
            response="   \n\t\n   ",
            query_type="call_info",
        )

        assert analysis.category == ResponseCategory.EMPTY
        assert analysis.score == 0

    def test_very_long_response(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of very long responses."""
        # Generate a long but quality response
        response = (
            """
        The Horizon Europe programme offers extensive funding opportunities.
        """
            * 50
        )  # Repeat to make it very long

        analysis = analyzer.analyze(
            query="Tell me about Horizon Europe",
            response=response,
            query_type="general_faq",
        )

        # Should still analyze correctly
        assert isinstance(analysis.score, int)
        assert 0 <= analysis.score <= 100

    def test_special_characters(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of responses with special characters."""
        response = """
        The budget is €5,000,000.00 (EUR 5M).
        Deadline: 15/03/2025 @ 17:00 CET
        Apply at: https://ec.europa.eu/funding?id=test&param=value#section
        """

        analysis = analyzer.analyze(
            query="Call details?",
            response=response,
            query_type="call_info",
            expected_elements=["budget", "deadline"],
        )

        # Should detect budget and deadline despite special characters
        assert "budget" not in analysis.missing_elements
        assert "deadline" not in analysis.missing_elements

    def test_non_english_content(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test handling of mixed language content."""
        response = """
        Das Projekt GREENENERGY hat ein Budget von EUR 5 Millionen.
        The deadline is 15 February 2025.
        Type: RIA (Research and Innovation Action)
        """

        analysis = analyzer.analyze(
            query="Project details",
            response=response,
            query_type="call_info",
        )

        # Should still detect core elements
        assert isinstance(analysis.score, int)

    def test_confidence_calculation(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test confidence calculation in various scenarios."""
        # Short response
        short_analysis = analyzer.analyze(
            query="What?",
            response="Yes.",
            query_type="general_faq",
        )

        # Long response
        long_response = (
            """
        The EIC Accelerator is the flagship programme of the European Innovation
        Council, designed to support high-impact innovations by SMEs and start-ups.
        """
            * 5
        )

        long_analysis = analyzer.analyze(
            query="What is EIC?",
            response=long_response,
            query_type="general_faq",
        )

        # Confidence should be higher for longer responses (easier to analyze)
        assert long_analysis.confidence >= short_analysis.confidence

    def test_is_acceptable_custom_threshold(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test is_acceptable with custom threshold."""
        response = "A decent but not perfect response with some information."

        analysis = analyzer.analyze(
            query="Test query",
            response=response,
            query_type="general_faq",
        )

        # Test different thresholds
        assert analysis.is_acceptable(min_score=0)  # Always passes with 0
        # May or may not pass with default (70)
        # Should fail with very high threshold
        if analysis.score < 95:
            assert not analysis.is_acceptable(min_score=95)
