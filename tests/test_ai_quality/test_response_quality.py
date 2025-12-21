"""
AI Response Quality Tests - Comprehensive Test Suite.

This module tests the ResponseQualityAnalyzer with 25+ queries covering:
- 5 specific call ID queries
- 5 programme comparison queries
- 5 eligibility/FAQ queries
- 3 budget benchmark queries
- 3 partner discovery queries
- 2 project search queries
- 2 consortium pattern queries

CRITICAL: Tests that pass when AI returns deflection phrases like
"I could not find specific details" are WORTHLESS. These tests
ensure the quality analyzer catches such failures.

Run with: pytest tests/test_ai_quality/test_response_quality.py -v
"""

import os
import sys
from typing import Any

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.quality.response_quality_analyzer import (
    ContentRequirement,
    QualityAnalysis,
    ResponseCategory,
    ResponseQualityAnalyzer,
)


class TestResponseQualityAnalyzer:
    """Tests for the ResponseQualityAnalyzer class."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create a fresh analyzer instance for each test."""
        return ResponseQualityAnalyzer()

    # =========================================================================
    # Basic Functionality Tests
    # =========================================================================

    def test_analyzer_initialization(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that analyzer initializes with all deflection patterns."""
        assert len(analyzer.DEFLECTION_PHRASES) > 30
        assert len(analyzer._deflection_patterns) > 0
        assert analyzer.MIN_SUBSTANTIVE_LENGTH == 200

    def test_empty_response_detection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that empty responses are properly detected."""
        analysis = analyzer.analyze(
            query="What is RIA?",
            response=""
        )
        assert analysis.category == ResponseCategory.EMPTY
        assert analysis.score == 0

    def test_short_response_detection(self, analyzer: ResponseQualityAnalyzer) -> None:
        """Test that very short responses are penalized."""
        analysis = analyzer.analyze(
            query="What is RIA?",
            response="RIA stands for Research and Innovation Action."
        )
        assert analysis.score < 70
        assert analysis.response_length < analyzer.MIN_SUBSTANTIVE_LENGTH

    # =========================================================================
    # Deflection Detection Tests
    # =========================================================================

    @pytest.mark.parametrize("deflection_phrase", [
        "I could not find specific information about this topic.",
        "Unfortunately, I couldn't find any results for your query.",
        "No information available for this search.",
        "I'm not sure about the details. Please try a more specific query.",
        "Unable to retrieve the requested information.",
        "I found some information but could not extract specific details.",
        "No results found for your query.",
        "I don't have access to that information.",
        "Please rephrase your question to be more specific.",
    ])
    def test_deflection_phrase_detection(
        self, analyzer: ResponseQualityAnalyzer, deflection_phrase: str
    ) -> None:
        """Test that deflection phrases are properly detected."""
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=deflection_phrase
        )
        assert len(analysis.deflection_phrases_found) > 0
        assert analysis.category == ResponseCategory.DEFLECTION
        assert analysis.score < 50

    def test_multiple_deflections_compound_penalty(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test that multiple deflection phrases result in larger penalty."""
        response_with_many_deflections = """
        I could not find specific information about this call.
        No results found in our database.
        I'm not sure about the deadline.
        Please try again later.
        """
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response=response_with_many_deflections
        )
        assert len(analysis.deflection_phrases_found) >= 3
        assert analysis.score < 30

    # =========================================================================
    # Call Search Quality Tests (5 queries)
    # =========================================================================

    @pytest.mark.parametrize("query,good_response,expected_elements", [
        (
            "Tell me about HORIZON-CL5-2026-D3-01",
            """
            **HORIZON-CL5-2026-D3-01: Advanced Biofuels Research**

            This call focuses on advancing sustainable biofuels technology within Cluster 5.

            **Key Details:**
            - **Call ID:** HORIZON-CL5-2026-D3-01
            - **Type:** RIA (Research and Innovation Action)
            - **Status:** Open
            - **Deadline:** 05 February 2026
            - **Budget:** EUR 20 million
            - **Programme:** Cluster 5 - Climate, Energy and Mobility

            **Scope:** The call addresses competitiveness, energy security, and integration
            aspects of advanced biofuels and renewable fuels for transport.

            **Eligibility:** Consortia of at least 3 independent entities from 3 different
            EU Member States or associated countries.
            """,
            ["call_id", "deadline", "budget", "action_type"],
        ),
        (
            "Find hydrogen funding calls for 2025",
            """
            **Hydrogen Funding Opportunities - 2025**

            I found **8 open funding opportunities** related to hydrogen research:

            **1. HORIZON-CL5-2025-D3-01: Clean Hydrogen Production**
            - Type: RIA
            - Deadline: 15 March 2025
            - Budget: EUR 15 million
            - Status: Open

            **2. HORIZON-CL5-2025-D3-02: Hydrogen Storage Solutions**
            - Type: IA
            - Deadline: 15 March 2025
            - Budget: EUR 25 million
            - Status: Open

            These calls are part of the Cluster 5 work programme focusing on
            decarbonisation of transport and energy systems.
            """,
            ["call_id", "deadline", "budget", "action_type"],
        ),
        (
            "What are open calls in Cluster 4 for digital technology?",
            """
            **Open Calls in Cluster 4 - Digital, Industry and Space**

            Currently, there are **12 open funding opportunities** in Cluster 4:

            **Recent calls include:**

            **HORIZON-CL4-2025-DIGITAL-01: AI and Robotics**
            - Type: RIA
            - Status: Open
            - Deadline: 20 April 2025
            - Budget: EUR 30 million
            - Focus: Advancing trustworthy AI and robotics technologies

            **HORIZON-CL4-2025-DATA-01: Data Spaces**
            - Type: IA
            - Status: Open
            - Deadline: 20 April 2025
            - Budget: EUR 25 million

            Cluster 4 supports Europe's digital transformation and industrial competitiveness.
            """,
            ["call_id", "deadline", "budget"],
        ),
        (
            "HORIZON-CL1-2025-HEALTH-01 call details",
            """
            **HORIZON-CL1-2025-HEALTH-01: Precision Medicine**

            **Call Information:**
            - **Call ID:** HORIZON-CL1-2025-HEALTH-01
            - **Programme:** Cluster 1 - Health
            - **Type:** RIA (Research and Innovation Action)
            - **Status:** Upcoming
            - **Opening Date:** 15 January 2025
            - **Deadline:** 15 May 2025
            - **Budget:** EUR 40 million

            **Scope:**
            This call focuses on advancing precision medicine approaches through
            integration of multi-omics data, AI-driven diagnostics, and personalized
            treatment strategies.

            **Expected Impact:**
            - Improved early diagnosis of chronic diseases
            - Development of targeted therapies
            - Reduction in healthcare costs
            """,
            ["call_id", "deadline", "budget", "action_type", "status"],
        ),
        (
            "Show me EIC Accelerator calls",
            """
            **EIC Accelerator Funding Opportunities**

            The EIC Accelerator supports high-impact innovations with:

            **Current Call:** EIC-ACCELERATOR-2025
            - **Type:** Blended finance (grant + equity)
            - **Status:** Open
            - **Deadline:** Cut-off 1: 12 March 2025, Cut-off 2: 15 October 2025
            - **Grant component:** Up to EUR 2.5 million
            - **Equity component:** Up to EUR 15 million
            - **Total budget:** EUR 1.2 billion for 2025

            **Eligibility:**
            - Single SMEs (or consortia for Open calls)
            - Technology Readiness Level 5-8
            - High-growth potential

            **Success rate:** Approximately 8% of applications receive funding.
            """,
            ["call_id", "deadline", "budget"],
        ),
    ])
    def test_call_search_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        good_response: str,
        expected_elements: list[str],
    ) -> None:
        """Test that good call search responses score high."""
        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
            query_type="call_search",
        )
        assert analysis.score >= 70, f"Score {analysis.score} < 70 for query: {query}"
        assert analysis.category in [ResponseCategory.COMPLETE, ResponseCategory.PARTIAL]
        assert len(analysis.deflection_phrases_found) == 0

    # =========================================================================
    # Programme Comparison Quality Tests (5 queries)
    # =========================================================================

    @pytest.mark.parametrize("query,good_response,expected_elements", [
        (
            "Compare EIC Accelerator vs ERC grants",
            """
            **Comparison: EIC Accelerator vs ERC Grants**

            | Aspect | EIC Accelerator | ERC Grants |
            |--------|-----------------|------------|
            | **Focus** | Market-ready innovations | Frontier research |
            | **Success Rate** | ~8% | ~12-15% |
            | **Funding** | Up to EUR 17.5M (grant + equity) | Up to EUR 2.5M (StG) - EUR 10M (AdG) |
            | **Applicants** | SMEs | Individual researchers |
            | **TRL** | 5-8 | 1-4 |

            **Key Differences:**
            - EIC focuses on commercialization while ERC focuses on scientific excellence
            - EIC is primarily for companies, ERC for researchers at host institutions
            - EIC includes equity investment, ERC is grant-only

            **When to choose which:**
            - Choose EIC if you have a ready-to-market innovation
            - Choose ERC if conducting groundbreaking fundamental research
            """,
            ["EIC", "ERC", "success rate", "comparison"],
        ),
        (
            "What's the difference between RIA and IA projects?",
            """
            **Research and Innovation Action (RIA) vs Innovation Action (IA)**

            **RIA - Research and Innovation Action:**
            - Focus: Establishing new knowledge and exploring feasibility
            - Funding rate: 100% of eligible costs
            - TRL range: Typically 2-5
            - Typical budget: EUR 3-6 million per project
            - Output: Publications, patents, prototypes

            **IA - Innovation Action:**
            - Focus: Demonstration, piloting, market replication
            - Funding rate: 70% (100% for non-profit)
            - TRL range: Typically 5-8
            - Typical budget: EUR 5-15 million per project
            - Output: Pilots, demonstrators, market uptake

            **Main difference:** RIA is for earlier-stage research, while IA is for
            bringing mature technologies to market. The funding rate also differs.
            """,
            ["RIA", "IA", "difference", "funding"],
        ),
        (
            "Compare MSCA and Widening participation",
            """
            **MSCA vs Widening Participation: A Comparison**

            **Marie Sklodowska-Curie Actions (MSCA):**
            - Purpose: Researcher mobility and career development
            - Focus: Training, international collaboration
            - Types: Doctoral Networks, Postdoctoral Fellowships, Staff Exchanges
            - Budget 2021-2027: EUR 6.6 billion
            - Success rate: ~15-25% depending on action type

            **Widening Participation:**
            - Purpose: Spreading excellence across Europe
            - Focus: Less research-intensive countries
            - Types: Teaming, Twinning, ERA Chairs, Hop On
            - Budget 2021-2027: EUR 3.3 billion
            - Target: Countries with low R&I performance

            **Key difference:** MSCA focuses on researcher development regardless
            of geography, while Widening specifically targets underrepresented regions.
            """,
            ["MSCA", "Widening", "comparison", "difference"],
        ),
        (
            "How does Horizon Europe compare to previous FP7?",
            """
            **Horizon Europe vs FP7: Framework Programme Evolution**

            | Feature | FP7 (2007-2013) | Horizon Europe (2021-2027) |
            |---------|-----------------|---------------------------|
            | **Budget** | EUR 50.5 billion | EUR 95.5 billion |
            | **Structure** | 4 programmes | 3 pillars |
            | **Missions** | Not included | 5 EU Missions |
            | **EIC** | Not included | European Innovation Council |
            | **Partnerships** | Joint Technology Initiatives | European Partnerships |

            **Key improvements in Horizon Europe:**
            1. Nearly double the budget of FP7
            2. Simplified application process
            3. Mission-oriented approach for societal challenges
            4. Dedicated innovation pillar (EIC)
            5. Better synergies with other EU programmes

            While FP7 laid important groundwork, Horizon Europe represents a more
            integrated and impactful approach to EU research funding.
            """,
            ["Horizon Europe", "FP7", "comparison", "budget"],
        ),
        (
            "ERC Starting Grant vs Consolidator Grant comparison",
            """
            **ERC Starting Grant vs Consolidator Grant**

            **Starting Grant (StG):**
            - Target: 2-7 years post-PhD
            - Funding: Up to EUR 1.5 million (+ EUR 1M hosting top-up)
            - Duration: 5 years
            - Success rate 2023: 14.2%
            - Applications: ~3,500/year

            **Consolidator Grant (CoG):**
            - Target: 7-12 years post-PhD
            - Funding: Up to EUR 2 million (+ EUR 1M hosting top-up)
            - Duration: 5 years
            - Success rate 2023: 13.8%
            - Applications: ~2,500/year

            **Main differences:**
            1. Career stage requirement (StG earlier, CoG more established)
            2. Higher funding ceiling for CoG
            3. Expectation of track record differs

            Both emphasize scientific excellence and frontier research, with
            the main distinction being career stage requirements.
            """,
            ["Starting Grant", "Consolidator", "ERC", "success rate"],
        ),
    ])
    def test_comparison_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        good_response: str,
        expected_elements: list[str],
    ) -> None:
        """Test that good comparison responses score high."""
        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
            query_type="comparison",
        )
        assert analysis.score >= 70, f"Score {analysis.score} < 70 for query: {query}"
        assert analysis.category in [ResponseCategory.COMPLETE, ResponseCategory.PARTIAL]

    # =========================================================================
    # FAQ/Eligibility Quality Tests (5 queries)
    # =========================================================================

    @pytest.mark.parametrize("query,good_response,expected_elements", [
        (
            "Can SMEs apply to Horizon Europe RIA calls?",
            """
            **Yes, SMEs can apply to Horizon Europe RIA calls.**

            SMEs are eligible to participate in Research and Innovation Actions and can:

            1. **Participate as partners** in consortia alongside universities and
               research institutes
            2. **Coordinate projects** as the lead organization
            3. **Receive 100% funding** for eligible costs (same as other participants)

            **Requirements:**
            - Must be legally established in an EU Member State or associated country
            - Must meet the EU SME definition (< 250 employees, < EUR 50M turnover)
            - Consortium must include at least 3 independent entities from 3 countries

            **Additional benefits for SMEs:**
            - Access to SME-specific evaluation criteria (impact on growth)
            - Dedicated SME support services
            - Potential innovation services support

            For SME-focused funding, also consider the EIC Accelerator and
            EIC Pathfinder Open calls.
            """,
            ["yes", "eligible", "SME", "RIA"],
        ),
        (
            "What is the minimum consortium size for Horizon Europe?",
            """
            **Minimum Consortium Requirements for Horizon Europe**

            The standard minimum requirement for most Horizon Europe calls is:

            **3-3-3 Rule:**
            - At least **3 independent legal entities**
            - From at least **3 different EU Member States or associated countries**
            - Each entity must be independent from the others

            **Exceptions:**

            | Action Type | Minimum Requirement |
            |-------------|---------------------|
            | RIA/IA (standard) | 3 entities, 3 countries |
            | CSA | 1 entity |
            | ERC Grants | 1 Principal Investigator |
            | MSCA Postdoctoral | 1 researcher + 1 host |
            | EIC Pathfinder | 3 entities, 3 countries |
            | EIC Accelerator | 1 SME (or consortium for Open) |

            Always check the specific call requirements as some may have
            higher minimums or additional conditions.
            """,
            ["minimum", "consortium", "3", "entities"],
        ),
        (
            "Can Swiss organizations participate in Horizon Europe?",
            """
            **Switzerland and Horizon Europe Participation**

            As of 2024, Switzerland is a **non-associated third country** for
            Horizon Europe, which means:

            **Current Status:**
            - Swiss entities **can participate** in most collaborative projects
            - They are **NOT automatically eligible** for EU funding
            - Swiss government provides **matching funding** for successful projects
            - Coordination is **not allowed** for most calls

            **Eligible Participation:**
            - Pillar 2 (Global Challenges) - with Swiss funding
            - ERC grants - Swiss funded
            - MSCA - Swiss funded

            **Not Eligible:**
            - Classified/security-sensitive calls
            - Some EIC programmes

            **Important:** Switzerland is negotiating association, so status may change.
            Check the EC Funding & Tenders Portal for current eligibility per call.
            """,
            ["Switzerland", "participate", "eligible", "funding"],
        ),
        (
            "What is the TRL requirement for EIC Accelerator?",
            """
            **EIC Accelerator TRL Requirements**

            The EIC Accelerator supports innovations at:

            **Technology Readiness Level (TRL): 5 to 8**

            - **TRL 5:** Technology validated in relevant environment
            - **TRL 6:** Technology demonstrated in relevant environment
            - **TRL 7:** System prototype demonstration in operational environment
            - **TRL 8:** System complete and qualified

            **What this means:**
            - Must have moved beyond lab research (TRL 1-4)
            - Must have demonstrated proof of concept
            - Should have validation data from relevant environment
            - Product/service should be close to market deployment

            **Not suitable if:**
            - Still in fundamental research stage
            - No prototype or demonstration exists
            - Product already at TRL 9 (commercially available)

            For earlier-stage innovations, consider EIC Pathfinder (TRL 1-4).
            """,
            ["TRL", "EIC Accelerator", "5", "8"],
        ),
        (
            "How does indirect cost calculation work in Horizon Europe?",
            """
            **Indirect Costs in Horizon Europe**

            Horizon Europe uses a **flat rate** for indirect costs:

            **Flat Rate: 25% of eligible direct costs**

            **Calculation:**
            - Indirect costs = 25% x (Total eligible direct costs - subcontracting costs)
            - Subcontracting is excluded from the base

            **What counts as indirect costs:**
            - Rent and utilities
            - Administrative staff
            - Office supplies
            - IT infrastructure
            - Insurance
            - General services

            **Example:**
            - Direct costs (excluding subcontracting): EUR 800,000
            - Subcontracting: EUR 100,000
            - Indirect costs: 25% x EUR 800,000 = EUR 200,000
            - Total eligible costs: EUR 1,100,000

            **Note:** Unlike FP7, there is no actual cost option - the 25% flat
            rate applies to all beneficiaries regardless of organization type.
            """,
            ["indirect", "25%", "flat rate", "calculation"],
        ),
    ])
    def test_faq_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        good_response: str,
        expected_elements: list[str],
    ) -> None:
        """Test that good FAQ responses score high."""
        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
            query_type="faq",
        )
        assert analysis.score >= 70, f"Score {analysis.score} < 70 for query: {query}"
        assert analysis.category in [ResponseCategory.COMPLETE, ResponseCategory.PARTIAL]

    # =========================================================================
    # Budget Benchmark Quality Tests (3 queries)
    # =========================================================================

    @pytest.mark.parametrize("query,good_response,expected_elements", [
        (
            "What is typical budget for Horizon Europe RIA in Cluster 5?",
            """
            **Typical RIA Budget in Cluster 5 (Climate, Energy and Mobility)**

            Based on analysis of 496 funded projects:

            **Budget Statistics:**
            - **Average budget:** EUR 5.2 million
            - **Median budget:** EUR 4.8 million
            - **Range:** EUR 2.0 - 12.0 million
            - **Most common:** EUR 4-6 million (45% of projects)

            **Budget Breakdown (typical):**
            | Category | Percentage |
            |----------|------------|
            | Personnel | 45-55% |
            | Equipment | 10-15% |
            | Travel | 5-8% |
            | Subcontracting | 10-20% |
            | Other costs | 15-25% |

            **Consortium context:**
            - Average partners: 12-15 organizations
            - Average countries: 8-10 Member States
            - Coordinator typically: 15-20% of budget

            For more specific guidance, check the call text for indicative budget.
            """,
            ["average", "budget", "million", "Cluster 5"],
        ),
        (
            "Budget benchmark for health research projects",
            """
            **Budget Benchmarks for Cluster 1 - Health Research**

            Analyzing 324 funded health projects:

            **By Action Type:**

            | Type | Average Budget | Range |
            |------|---------------|-------|
            | RIA | EUR 6.8 million | EUR 3-15M |
            | IA | EUR 9.2 million | EUR 5-25M |
            | CSA | EUR 2.1 million | EUR 0.5-4M |

            **Per Organization Type (RIA average):**
            - Universities (HES): EUR 450,000
            - Research centers (REC): EUR 520,000
            - Industry/SME (PRC): EUR 380,000
            - Public bodies (PUB): EUR 280,000

            **Key observations:**
            - Clinical trial projects tend to have higher budgets
            - Regulatory work can increase subcontracting costs
            - Patient engagement activities should be budgeted

            **Recommendation:** Budget 15-20% for project management and
            dissemination activities.
            """,
            ["average", "budget", "health", "million"],
        ),
        (
            "How much should I budget for an AI project?",
            """
            **Budget Guidelines for AI/Digital Research Projects**

            Based on Cluster 4 (Digital, Industry and Space) funded projects:

            **Typical Budgets:**
            - **RIA projects:** EUR 4-7 million average
            - **IA projects:** EUR 6-12 million average
            - **Large-scale pilots:** EUR 10-20 million

            **AI-Specific Considerations:**

            **Computing costs:**
            - Cloud computing: EUR 200,000-500,000 (can be higher for large models)
            - Consider including HPC access costs

            **Data costs:**
            - Data acquisition: EUR 100,000-300,000
            - Data annotation: EUR 50,000-150,000

            **Equipment:**
            - GPUs/specialized hardware: EUR 100,000-400,000

            **Personnel breakdown:**
            - Senior researchers: 30-40%
            - Engineers/developers: 40-50%
            - Project management: 10-15%

            **Budget per partner (typical):**
            - Average: EUR 350,000-600,000 per organization
            """,
            ["budget", "AI", "average", "computing"],
        ),
    ])
    def test_budget_benchmark_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        good_response: str,
        expected_elements: list[str],
    ) -> None:
        """Test that good budget benchmark responses score high."""
        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
            query_type="budget_benchmark",
        )
        assert analysis.score >= 70, f"Score {analysis.score} < 70 for query: {query}"
        assert analysis.category in [ResponseCategory.COMPLETE, ResponseCategory.PARTIAL]

    # =========================================================================
    # Partner Discovery Quality Tests (3 queries)
    # =========================================================================

    @pytest.mark.parametrize("query,good_response,expected_elements", [
        (
            "Find German SMEs with hydrogen experience",
            """
            **German SMEs with Hydrogen Research Experience**

            I found **15 organizations** matching your criteria:

            **Top Experienced Partners:**

            **1. Hydrogenious LOHC Technologies GmbH**
            - Location: Erlangen, Germany
            - Type: SME (PRC)
            - Hydrogen projects: 8
            - Coordination experience: 3 projects
            - Expertise: Hydrogen storage and transport

            **2. H2 PowerTech GmbH**
            - Location: Munich, Germany
            - Type: SME (PRC)
            - Hydrogen projects: 6
            - Coordination experience: 2 projects
            - Expertise: Fuel cell development

            **3. AquaVentus Industries GmbH**
            - Location: Hamburg, Germany
            - Type: SME (PRC)
            - Hydrogen projects: 5
            - Expertise: Offshore hydrogen production

            **Network statistics:**
            - Average project participation: 4.5 projects
            - Strong collaboration with: Fraunhofer institutes, TU Munich
            - Typical role: Technology development partner
            """,
            ["Germany", "SME", "hydrogen", "experience"],
        ),
        (
            "Find partners for renewable energy project in Spain",
            """
            **Spanish Renewable Energy Research Partners**

            Found **22 organizations** with renewable energy expertise:

            **Universities:**

            **1. Universidad Politecnica de Madrid (UPM)**
            - Renewable projects: 45
            - Coordination: 12 projects
            - Strengths: Solar, wind, grid integration

            **2. Universitat Politecnica de Catalunya (UPC)**
            - Renewable projects: 38
            - Coordination: 8 projects
            - Strengths: Offshore wind, marine energy

            **Research Centers:**

            **3. CENER - National Renewable Energy Centre**
            - Renewable projects: 52
            - Coordination: 15 projects
            - Strengths: Testing facilities, certification

            **4. IREC - Catalonia Institute for Energy Research**
            - Renewable projects: 41
            - Coordination: 9 projects
            - Strengths: Bioenergy, solar thermal

            **SMEs:**

            **5. Acciona Energia**
            - Renewable projects: 28
            - Type: Large enterprise
            - Strengths: Wind, solar, demonstration projects
            """,
            ["Spain", "renewable", "energy", "partner"],
        ),
        (
            "Organizations with AI experience in healthcare",
            """
            **AI in Healthcare: Experienced Research Partners**

            Found **34 organizations** with AI/healthcare expertise:

            **Top Partners by Project Count:**

            **1. Philips Research**
            - Country: Netherlands
            - AI/Health projects: 28
            - Coordination: 8
            - Focus: Medical imaging AI, diagnostics

            **2. Fraunhofer MEVIS**
            - Country: Germany
            - AI/Health projects: 24
            - Coordination: 6
            - Focus: Medical image analysis, clinical decision support

            **3. INSERM**
            - Country: France
            - AI/Health projects: 32
            - Coordination: 11
            - Focus: Predictive models, genomics AI

            **4. University of Oxford (Big Data Institute)**
            - Country: UK (Associated)
            - AI/Health projects: 22
            - Focus: Machine learning for health

            **5. Karolinska Institute**
            - Country: Sweden
            - AI/Health projects: 19
            - Focus: Clinical AI, precision medicine

            **Common collaboration patterns:**
            - Consortia typically include 2-3 hospitals for validation
            - Data providers paired with AI developers
            """,
            ["AI", "healthcare", "organization", "experience"],
        ),
    ])
    def test_partner_discovery_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        good_response: str,
        expected_elements: list[str],
    ) -> None:
        """Test that good partner discovery responses score high."""
        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
            query_type="partner_discovery",
        )
        assert analysis.score >= 70, f"Score {analysis.score} < 70 for query: {query}"
        assert analysis.category in [ResponseCategory.COMPLETE, ResponseCategory.PARTIAL]

    # =========================================================================
    # Project Search Quality Tests (2 queries)
    # =========================================================================

    @pytest.mark.parametrize("query,good_response,expected_elements", [
        (
            "Find quantum computing projects in Horizon Europe",
            """
            **Quantum Computing Projects in Horizon Europe**

            Found **47 funded projects** in quantum computing:

            **Featured Projects:**

            **1. QUCATS - Quantum Computing At The Service**
            - Acronym: QUCATS
            - Budget: EUR 7.2 million
            - Duration: 2023-2027
            - Coordinator: TU Delft (Netherlands)
            - Partners: 12 from 8 countries
            - Focus: Quantum algorithms for industrial optimization

            **2. OpenSuperQ Plus**
            - Budget: EUR 20 million (Flagship)
            - Duration: 2021-2025
            - Coordinator: Forschungszentrum Julich (Germany)
            - Partners: 28
            - Focus: Building a full-stack quantum computer

            **3. QUBITS4MED**
            - Budget: EUR 4.5 million
            - Duration: 2024-2028
            - Coordinator: University of Vienna (Austria)
            - Focus: Quantum computing for drug discovery

            **Statistics:**
            - Total funding: EUR 285 million
            - Average project size: EUR 6.1 million
            - Main countries: Germany, Netherlands, France
            """,
            ["quantum", "project", "budget", "coordinator"],
        ),
        (
            "Find projects similar to green hydrogen production",
            """
            **Green Hydrogen Production: Related Funded Projects**

            Found **38 similar projects** in hydrogen production:

            **Top Matches by Relevance:**

            **1. H2FUTURE**
            - Budget: EUR 18 million
            - Coordinator: Verbund AG (Austria)
            - Objective: World's largest green hydrogen pilot at steel plant
            - Key results: 6 MW electrolyzer demonstrated

            **2. DJEWELS**
            - Budget: EUR 7.5 million
            - Coordinator: Shell (Netherlands)
            - Objective: Green hydrogen production cost reduction
            - Focus: Electrolyzer efficiency improvements

            **3. GREENH2ATLANTIC**
            - Budget: EUR 30 million
            - Coordinator: EDP (Portugal)
            - Objective: 100 MW offshore green hydrogen plant
            - Status: Under implementation

            **Research trends:**
            - Electrolyzer efficiency: 25 projects
            - Cost reduction: 20 projects
            - Industrial integration: 18 projects
            - Offshore production: 8 projects
            """,
            ["hydrogen", "project", "budget", "production"],
        ),
    ])
    def test_project_search_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        good_response: str,
        expected_elements: list[str],
    ) -> None:
        """Test that good project search responses score high."""
        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
            query_type="project_search",
        )
        assert analysis.score >= 70, f"Score {analysis.score} < 70 for query: {query}"
        assert analysis.category in [ResponseCategory.COMPLETE, ResponseCategory.PARTIAL]

    # =========================================================================
    # Consortium Pattern Quality Tests (2 queries)
    # =========================================================================

    @pytest.mark.parametrize("query,good_response,expected_elements", [
        (
            "What is typical consortium size for Health IAs?",
            """
            **Consortium Patterns for Health Innovation Actions (IA)**

            Analysis of 89 funded Cluster 1 Innovation Actions:

            **Consortium Size:**
            - **Average partners:** 18.5 organizations
            - **Range:** 8 to 42 partners
            - **Most common:** 12-20 partners (65% of projects)

            **Country Distribution:**
            - **Average countries:** 11.2 Member States
            - **Range:** 5 to 20 countries
            - **Associated countries:** Average 2-3 per project

            **Organization Type Distribution:**
            | Type | Percentage | Average Count |
            |------|------------|---------------|
            | Universities (HES) | 35% | 6.5 |
            | Research Centers (REC) | 25% | 4.6 |
            | Hospitals | 18% | 3.3 |
            | Industry (PRC) | 15% | 2.8 |
            | Other (PUB/OTH) | 7% | 1.3 |

            **Key patterns:**
            - Successful IAs include 3-5 clinical validation sites
            - Patient organizations increasingly included
            - Regulatory experts common in later-stage projects
            """,
            ["consortium", "partners", "average", "countries"],
        ),
        (
            "Show consortium patterns for energy research projects",
            """
            **Consortium Patterns in Cluster 5 - Energy Research**

            Analysis of 245 funded energy projects:

            **Overall Statistics:**
            - **Average consortium size:** 15.2 partners
            - **Median:** 14 partners
            - **Average countries:** 9.4 EU Member States

            **By Action Type:**

            | Type | Avg Partners | Avg Countries | Avg Budget |
            |------|--------------|---------------|------------|
            | RIA | 12.8 | 8.5 | EUR 5.2M |
            | IA | 18.6 | 10.2 | EUR 9.8M |
            | CSA | 8.2 | 6.1 | EUR 2.1M |

            **Successful Coordinator Profile:**
            - Top coordinator countries: Germany (28%), France (15%), Spain (12%)
            - Coordinator type: 45% research institutes, 35% universities
            - Average coordinator share: 18% of budget

            **Industry Participation:**
            - 78% of projects include industry partners
            - Average 3-4 companies per consortium
            - SME participation: 2.1 SMEs average
            """,
            ["consortium", "partners", "average", "energy"],
        ),
    ])
    def test_consortium_patterns_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        good_response: str,
        expected_elements: list[str],
    ) -> None:
        """Test that good consortium pattern responses score high."""
        analysis = analyzer.analyze(
            query=query,
            response=good_response,
            expected_elements=expected_elements,
            query_type="consortium_patterns",
        )
        assert analysis.score >= 70, f"Score {analysis.score} < 70 for query: {query}"
        assert analysis.category in [ResponseCategory.COMPLETE, ResponseCategory.PARTIAL]

    # =========================================================================
    # Bad Response Detection Tests
    # =========================================================================

    @pytest.mark.parametrize("query,bad_response,max_acceptable_score", [
        (
            "Tell me about HORIZON-CL5-2026-D3-01",
            "I could not find specific information about this call.",
            50,
        ),
        (
            "Compare EIC vs ERC",
            "I'm not sure about the differences. Please try a more specific query.",
            40,
        ),
        (
            "Find hydrogen partners",
            "No results found.",
            40,  # Even short deflections score low
        ),
        (
            "What is the budget for RIA projects?",
            "I don't have access to that information.",
            40,
        ),
        (
            "Show me open calls",
            "Unable to retrieve funding call information at this time.",
            40,
        ),
    ])
    def test_bad_response_detection(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        bad_response: str,
        max_acceptable_score: int,
    ) -> None:
        """Test that bad/deflection responses score low."""
        analysis = analyzer.analyze(query=query, response=bad_response)
        assert analysis.score <= max_acceptable_score, (
            f"Bad response scored {analysis.score}, should be <= {max_acceptable_score}"
        )
        assert analysis.category == ResponseCategory.DEFLECTION or analysis.score < 50

    # =========================================================================
    # Tool Result Validation Tests
    # =========================================================================

    def test_tool_result_validation_success(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test validation of successful tool results."""
        tool_result = {
            "success": True,
            "calls_found": 5,
            "calls": [{"call_id": "HORIZON-CL5-2025-D3-01", "title": "Test"}],
        }
        is_valid, issues = analyzer.validate_tool_response(
            "search_funding_calls", tool_result
        )
        assert is_valid
        assert len(issues) == 0

    def test_tool_result_validation_empty(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test validation of empty tool results."""
        tool_result = {
            "success": True,
            "calls_found": 0,
            "calls": [],
        }
        is_valid, issues = analyzer.validate_tool_response(
            "search_funding_calls", tool_result
        )
        assert not is_valid
        assert "No funding calls found" in issues[0]

    def test_tool_result_validation_error(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test validation of tool error results."""
        tool_result = {
            "error": "Database connection failed",
        }
        is_valid, issues = analyzer.validate_tool_response(
            "search_funding_calls", tool_result
        )
        assert not is_valid
        assert "error" in issues[0].lower()

    def test_analyze_with_tools_missing_expected(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test analysis when expected tools were not called."""
        analysis = analyzer.analyze_with_tools(
            query="Compare EIC vs ERC",
            response="EIC and ERC are different programmes.",
            tool_results={},
            expected_tools=["get_programme_statistics", "compare_programmes"],
        )
        assert "tool:get_programme_statistics" in analysis.missing_elements
        assert "tool:compare_programmes" in analysis.missing_elements

    # =========================================================================
    # Query Type Detection Tests
    # =========================================================================

    @pytest.mark.parametrize("query,expected_type", [
        ("Tell me about HORIZON-CL5-2026-D3-01", "call_search"),
        ("Find open funding calls", "call_search"),
        ("Compare EIC vs ERC", "comparison"),
        ("What's the difference between RIA and IA", "comparison"),
        ("Find quantum computing projects", "project_search"),
        ("Can SMEs apply to Horizon Europe?", "faq"),
        ("What is the minimum consortium size?", "faq"),
        ("What's typical budget for RIA?", "budget_benchmark"),
        ("Find partners for hydrogen research", "partner_discovery"),
        ("Typical consortium size for Health IAs?", "consortium_patterns"),
    ])
    def test_query_type_detection(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        expected_type: str,
    ) -> None:
        """Test that query types are correctly detected."""
        detected_type = analyzer._detect_query_type(query)
        assert detected_type == expected_type, (
            f"Query '{query}' detected as '{detected_type}', expected '{expected_type}'"
        )

    # =========================================================================
    # Content Requirement Tests
    # =========================================================================

    def test_content_requirement_matches(self) -> None:
        """Test ContentRequirement pattern matching."""
        req = ContentRequirement(
            name="budget",
            patterns=[r"eur\s*\d+", r"\d+\s*million"],
        )
        assert req.matches("Budget: EUR 5 million")
        assert req.matches("The project has EUR 5000000")
        assert not req.matches("No budget information")

    def test_quality_analysis_is_acceptable(self) -> None:
        """Test QualityAnalysis.is_acceptable() method."""
        good_analysis = QualityAnalysis(
            score=85,
            category=ResponseCategory.COMPLETE,
            confidence=0.9,
        )
        assert good_analysis.is_acceptable(min_score=70)
        assert good_analysis.is_acceptable(min_score=85)
        assert not good_analysis.is_acceptable(min_score=90)

        deflection_analysis = QualityAnalysis(
            score=75,
            category=ResponseCategory.DEFLECTION,
            confidence=0.9,
        )
        # Even with high score, deflection is not acceptable
        assert not deflection_analysis.is_acceptable(min_score=70)

    def test_quality_analysis_to_dict(self) -> None:
        """Test QualityAnalysis serialization."""
        analysis = QualityAnalysis(
            score=80,
            category=ResponseCategory.COMPLETE,
            confidence=0.85,
            missing_elements=["element1"],
            deflection_phrases_found=[],
            recommendations=["Good response"],
        )
        result = analysis.to_dict()
        assert result["score"] == 80
        assert result["category"] == "complete"
        assert result["confidence"] == 0.85
        assert "timestamp" in result


# ============================================================================
# Integration Tests
# ============================================================================

class TestResponseQualityIntegration:
    """Integration tests for the quality analyzer with realistic scenarios."""

    @pytest.fixture
    def analyzer(self) -> ResponseQualityAnalyzer:
        """Create a fresh analyzer instance."""
        return ResponseQualityAnalyzer()

    def test_full_analysis_with_tool_results(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test complete analysis including tool results."""
        query = "Find hydrogen funding calls"
        response = """
        I found **5 funding opportunities** for hydrogen research:

        **1. HORIZON-CL5-2025-D3-01: Clean Hydrogen Production**
        - Type: RIA
        - Deadline: 15 March 2025
        - Budget: EUR 15 million
        - Status: Open

        **2. HORIZON-CL5-2025-D3-02: Hydrogen Storage**
        - Type: IA
        - Deadline: 15 March 2025
        - Budget: EUR 25 million
        - Status: Open
        """
        tool_results = {
            "search_funding_calls": {
                "success": True,
                "calls_found": 5,
                "calls": [
                    {"call_id": "HORIZON-CL5-2025-D3-01", "title": "Test"}
                ],
            }
        }

        analysis = analyzer.analyze_with_tools(
            query=query,
            response=response,
            tool_results=tool_results,
            expected_tools=["search_funding_calls"],
        )

        assert analysis.score >= 70
        assert analysis.category == ResponseCategory.COMPLETE
        assert len(analysis.deflection_phrases_found) == 0
        assert "tool:search_funding_calls" not in analysis.missing_elements

    def test_partial_response_with_some_elements(
        self, analyzer: ResponseQualityAnalyzer
    ) -> None:
        """Test response that has some but not all required elements."""
        query = "Tell me about HORIZON-CL5-2026-D3-01"
        response = """
        This call is part of Cluster 5 and focuses on sustainable energy research.
        The action type is RIA (Research and Innovation Action).
        Consortium requirements follow standard Horizon Europe rules.
        """
        # Missing: deadline, budget, specific call ID, status

        analysis = analyzer.analyze(
            query=query,
            response=response,
            query_type="call_search",
        )

        assert analysis.category in [ResponseCategory.PARTIAL, ResponseCategory.COMPLETE]
        assert len(analysis.missing_elements) > 0  # Some elements missing
        assert analysis.score < 90  # Not perfect score
