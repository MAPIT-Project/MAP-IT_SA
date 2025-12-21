"""
AI Response Quality Test Suite

Tests that AI responses meet quality standards and don't contain deflection phrases.
This suite tests the ResponseQualityAnalyzer's ability to detect:
- Deflection phrases ("I could not find", etc.)
- Missing required elements (deadline, budget, type for calls)
- Low-quality responses (too short, generic)

The tests are designed to catch lazy or unhelpful AI responses.
"""

import os
import sys
from typing import List, Optional

import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.quality.response_quality_analyzer import (
    QualityAnalysis,
    ResponseCategory,
    ResponseQualityAnalyzer,
)


@pytest.fixture
def analyzer():
    """Create a ResponseQualityAnalyzer instance."""
    return ResponseQualityAnalyzer()


# =============================================================================
# DEFLECTION DETECTION TESTS
# =============================================================================


class TestDeflectionDetection:
    """Tests for detecting deflection phrases in AI responses."""

    @pytest.mark.parametrize(
        "response,expected_deflection_count,expected_category",
        [
            # Clear deflection responses
            (
                "I could not find any information about that topic. "
                "Please try a more specific query.",
                2,
                ResponseCategory.DEFLECTION,
            ),
            (
                "No results found. I am not sure about the answer to your question.",
                2,
                ResponseCategory.DEFLECTION,
            ),
            (
                "I was unable to retrieve the information you requested. "
                "No data available for this query.",
                2,
                ResponseCategory.DEFLECTION,
            ),
            (
                "Unfortunately, I could not find relevant information. "
                "The search returned no matching results.",
                2,
                ResponseCategory.DEFLECTION,
            ),
            # Single deflection phrase (still flagged if short)
            (
                "I could not find specific details about that call.",
                1,
                ResponseCategory.DEFLECTION,
            ),
            # Good responses (no deflection)
            (
                "The HORIZON-CL5-2026-D3-01 call focuses on hydrogen technologies. "
                "The deadline is February 2026 with a budget of EUR 20 million. "
                "This is a RIA type call and is currently open for applications.",
                0,
                ResponseCategory.COMPLETE,
            ),
        ],
        ids=[
            "double_deflection_1",
            "double_deflection_2",
            "double_deflection_3",
            "double_deflection_4",
            "single_deflection_short",
            "good_response_no_deflection",
        ],
    )
    def test_deflection_detection(
        self,
        analyzer: ResponseQualityAnalyzer,
        response: str,
        expected_deflection_count: int,
        expected_category: ResponseCategory,
    ):
        """Test detection of deflection phrases."""
        analysis = analyzer.analyze("Tell me about funding calls", response)

        assert len(analysis.deflection_phrases_found) >= expected_deflection_count, (
            f"Expected at least {expected_deflection_count} deflection phrases, "
            f"found {len(analysis.deflection_phrases_found)}: {analysis.deflection_phrases_found}"
        )

        if expected_category == ResponseCategory.DEFLECTION:
            assert analysis.category == ResponseCategory.DEFLECTION, (
                f"Expected DEFLECTION category but got {analysis.category}"
            )
            assert analysis.score < 50, (
                f"Deflection response should score below 50, got {analysis.score}"
            )


# =============================================================================
# CALL QUERY TESTS (5 queries)
# =============================================================================


class TestCallQueries:
    """Tests for call-related query responses."""

    @pytest.mark.parametrize(
        "query,response,min_score,expected_elements",
        [
            # Query 1: Specific call ID
            (
                "Tell me about HORIZON-CL5-2026-D3-01",
                """**HORIZON-CL5-2026-D3-01** - Competitiveness and Integration of Biofuels

**Type:** RIA (Research and Innovation Action)
**Status:** Open
**Deadline:** 05 February 2026
**Budget:** EUR 20.00 million
**Programme:** Cluster 5 - Climate, Energy and Mobility

**Scope:**
This topic focuses on advanced biofuels and renewable fuels for sustainable transport.

**Apply:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/""",
                75,
                ["deadline", "budget", "type", "status"],
            ),
            # Query 2: Call search by topic
            (
                "Find hydrogen funding calls in 2025",
                """I found **8 funding opportunities** for hydrogen in 2025:

1. **Hydrogen Valley Scale-up**
   - Call ID: HORIZON-JTI-CLEANH2-2025-01
   - Type: IA
   - Status: Open
   - Deadline: March 2025
   - Budget: EUR 15 million

2. **Green Hydrogen Production**
   - Call ID: HORIZON-CL5-2025-D3-02
   - Type: RIA
   - Status: Upcoming
   - Deadline: April 2025
   - Budget: EUR 25 million""",
                75,
                ["deadline", "budget", "type"],
            ),
            # Query 3: Call deadline query
            (
                "What is the deadline for HORIZON-CL4-2025-DATA-01?",
                """The deadline for **HORIZON-CL4-2025-DATA-01** is **18 March 2025** at 17:00 CET.

This is a two-stage submission process:
- Stage 1 deadline: 18 March 2025
- Stage 2 deadline: 18 September 2025 (for successful Stage 1 applicants)

The call is currently **Open** for Stage 1 submissions.

**Type:** RIA (Research and Innovation Action)
**Budget:** EUR 8 million per project""",
                75,
                ["deadline", "status"],
            ),
            # Query 4: Call budget query
            (
                "What is the budget for EIC Accelerator 2025?",
                """The **EIC Accelerator 2025** has a total budget of approximately **EUR 1.6 billion**.

**Call Status:** Open
**Deadline:** Rolling submissions with cut-offs in January and June 2025

Individual grants can range from:
- Grant only: up to EUR 2.5 million
- Blended finance: up to EUR 2.5 million grant + EUR 15 million equity

The 2025 work programme allocates:
- EUR 675 million for the first cut-off (January 2025)
- EUR 675 million for the second cut-off (June 2025)
- EUR 250 million for challenges and strategic priorities

**Type:** IA (Innovation Action with equity component)""",
                75,
                ["budget"],
            ),
            # Query 5: Call type and eligibility
            (
                "What type of call is HORIZON-MSCA-2025-DN-01?",
                """**HORIZON-MSCA-2025-DN-01** is a **Marie Curie Doctoral Networks** call.

**Type:** MSCA (Marie Sklodowska-Curie Actions)
**Action Type:** Doctoral Networks (DN)
**Status:** Open
**Deadline:** 27 November 2025

**Eligibility:**
- Academic institutions, research organizations, and non-academic sectors
- Network of minimum 3 beneficiaries from 3 different EU Member States/Associated Countries
- Doctoral candidates: Early-stage researchers without PhD

**Funding:** Up to EUR 360,000 per researcher-month""",
                75,
                ["type", "status", "deadline"],
            ),
        ],
        ids=[
            "call_1_specific_id",
            "call_2_hydrogen_search",
            "call_3_deadline_query",
            "call_4_budget_query",
            "call_5_type_eligibility",
        ],
    )
    def test_call_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        min_score: int,
        expected_elements: List[str],
    ):
        """Test that call responses contain required elements."""
        analysis = analyzer.validate_call_response(response)

        assert analysis.score >= min_score, (
            f"Score {analysis.score} below minimum {min_score}. "
            f"Missing: {analysis.missing_elements}"
        )

        assert analysis.category != ResponseCategory.DEFLECTION, (
            f"Response flagged as deflection: {analysis.deflection_phrases_found}"
        )

        # Check that expected elements are NOT in missing_elements
        response_lower = response.lower()
        for element in expected_elements:
            assert element in response_lower or element not in analysis.missing_elements, (
                f"Expected element '{element}' should be present or recognized"
            )


# =============================================================================
# PROGRAMME COMPARISON TESTS (5 queries)
# =============================================================================


class TestComparisonQueries:
    """Tests for programme comparison query responses."""

    @pytest.mark.parametrize(
        "programme_a,programme_b,response,min_score",
        [
            # Query 1: EIC vs ERC
            (
                "EIC",
                "ERC",
                """**Comparing EIC Accelerator vs ERC Grants:**

| Aspect | EIC Accelerator | ERC Grants |
|--------|-----------------|------------|
| Success Rate | ~8% | ~12-15% |
| Target | SMEs & Startups | Individual Researchers |
| Funding | Up to EUR 17.5M (grant+equity) | Up to EUR 2.5M (Starting) |
| Focus | Market-ready innovation | Frontier research |
| TRL | 5-9 (close to market) | 1-4 (early stage) |

**Key Differences:**
- EIC focuses on commercialization while ERC supports basic research
- EIC requires business plan; ERC evaluates scientific excellence
- EIC has equity component; ERC is grant-only""",
                75,
            ),
            # Query 2: RIA vs IA
            (
                "RIA",
                "IA",
                """**Research and Innovation Actions (RIA) vs Innovation Actions (IA):**

**RIA (Research and Innovation Actions):**
- Focus: Generating new knowledge, exploring feasibility
- TRL: Typically 2-5 (research to prototype)
- Funding rate: 100% of eligible costs
- Typical budget: EUR 3-5 million

**IA (Innovation Actions):**
- Focus: Plans, designs for new products/services
- TRL: Typically 5-8 (demonstration to pre-commercial)
- Funding rate: 70% (100% for non-profit)
- Typical budget: EUR 5-15 million

The main difference is that RIA focuses on earlier-stage research while IA is closer to market deployment.""",
                75,
            ),
            # Query 3: Cluster 4 vs Cluster 5
            (
                "Cluster 4",
                "Cluster 5",
                """**Horizon Europe Cluster 4 vs Cluster 5 Comparison:**

**Cluster 4 - Digital, Industry and Space:**
- Budget: EUR 15.3 billion (2021-2027)
- Focus: AI, cybersecurity, advanced manufacturing, space
- Success rate: ~15%
- Average grant size: EUR 4.2 million

**Cluster 5 - Climate, Energy and Mobility:**
- Budget: EUR 15.1 billion (2021-2027)
- Focus: Climate science, clean energy, smart transport
- Success rate: ~13%
- Average grant size: EUR 5.1 million

Both clusters have similar budgets, but Cluster 5 projects tend to be larger due to the infrastructure-heavy nature of energy and mobility research.""",
                75,
            ),
            # Query 4: MSCA vs ERC for researchers
            (
                "MSCA",
                "ERC",
                """**Marie Curie (MSCA) vs ERC for Early Career Researchers:**

**MSCA Postdoctoral Fellowships:**
- For: Researchers with PhD, seeking international mobility
- Duration: 1-2 years
- Monthly allowance: ~EUR 5,000
- Focus: Research training and career development
- Success rate: ~15%

**ERC Starting Grant:**
- For: Researchers 2-7 years post-PhD
- Duration: Up to 5 years
- Budget: Up to EUR 1.5 million
- Focus: Independent research programme
- Success rate: ~12%

MSCA is better for mobility and training, whereas ERC is better for establishing an independent research programme.""",
                75,
            ),
            # Query 5: National vs EU funding
            (
                "national funding",
                "EU funding",
                """**National Funding vs EU Horizon Europe Funding:**

| Aspect | National Funding | EU Funding (Horizon Europe) |
|--------|------------------|------------------------------|
| Competition | Country-level | Europe-wide |
| Collaboration | Optional | Required (usually 3+ countries) |
| Budget | Varies by country | EUR 95.5 billion total |
| Success rate | 20-40% typically | 12-18% for most calls |
| Admin burden | Lower | Higher |

**When to choose EU funding:**
- International collaboration is beneficial
- Larger project scope needed
- Access to European networks and infrastructure

**When to choose national funding:**
- Faster decision process
- Simpler administration
- Local focus sufficient""",
                75,
            ),
        ],
        ids=[
            "comparison_1_eic_vs_erc",
            "comparison_2_ria_vs_ia",
            "comparison_3_cluster4_vs_cluster5",
            "comparison_4_msca_vs_erc",
            "comparison_5_national_vs_eu",
        ],
    )
    def test_comparison_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        programme_a: str,
        programme_b: str,
        response: str,
        min_score: int,
    ):
        """Test that comparison responses contain both programmes and comparative language."""
        analysis = analyzer.validate_comparison_response(response, programme_a, programme_b)

        assert analysis.score >= min_score, (
            f"Score {analysis.score} below minimum {min_score}. "
            f"Missing: {analysis.missing_elements}"
        )

        assert analysis.category != ResponseCategory.DEFLECTION, (
            f"Comparison flagged as deflection: {analysis.deflection_phrases_found}"
        )


# =============================================================================
# FAQ/ELIGIBILITY TESTS (5 queries)
# =============================================================================


class TestFAQQueries:
    """Tests for FAQ and eligibility query responses."""

    @pytest.mark.parametrize(
        "query,response,min_score,expected_patterns",
        [
            # Query 1: SME eligibility
            (
                "Can SMEs apply to Horizon Europe?",
                """**Yes, SMEs can apply to Horizon Europe!**

SMEs are strongly encouraged to participate:
- **Dedicated budget:** At least EUR 4 billion specifically for SMEs
- **EIC Accelerator:** SME-focused funding up to EUR 2.5 million grant + EUR 15 million equity
- **Higher funding rates:** SMEs receive 70% funding in Innovation Actions (vs standard 70%)

**How to participate:**
1. Join a consortium as a partner
2. Apply as coordinator (for EIC Accelerator)
3. Participate through cascade funding via established projects

**Requirements:**
- Fewer than 250 employees
- Annual turnover ≤ EUR 50 million or balance sheet ≤ EUR 43 million
- Independent (not majority-owned by larger company)""",
                75,
                ["sme", "horizon", "apply", "funding"],
            ),
            # Query 2: Associated country participation
            (
                "Can Switzerland participate in Horizon Europe?",
                """**Switzerland's Horizon Europe Status:**

As of 2024, Switzerland is a **Non-Associated Third Country**, meaning:

**What Swiss organizations CAN do:**
- Join consortia as partners (self-funded)
- Lead projects (but without EU coordination funding)
- Access some calls open to third countries

**What they CANNOT do:**
- Receive EU funding directly
- Access EIC and ERC programs
- Count towards minimum consortium requirements

**Swiss government compensation:**
The Swiss State Secretariat for Education, Research and Innovation (SERI) provides replacement funding for Swiss participants.

**Future outlook:**
Negotiations for full association are ongoing, pending resolution of broader EU-Swiss relations.""",
                75,
                ["switzerland", "horizon", "third country"],
            ),
            # Query 3: Consortium requirements
            (
                "What are the minimum consortium requirements for Horizon Europe?",
                """**Minimum Consortium Requirements:**

For most Horizon Europe calls:

**Standard requirement (RIA, IA):**
- Minimum **3 independent legal entities**
- From **3 different EU Member States or Associated Countries**
- At least 1 must be from an EU Member State

**Exceptions:**
- ERC grants: Single researcher/institution
- MSCA Postdoctoral: Individual fellowship
- EIC Accelerator: Single SME
- Coordination and Support Actions: May require only 1 entity

**Country eligibility:**
- 27 EU Member States
- 16+ Associated Countries (Norway, Israel, etc.)
- Third countries (case-by-case)

**Tips:**
- Diverse consortia (geography, expertise) score better
- Include end-users and industry partners for impact""",
                75,
                ["minimum", "consortium", "countries", "member states"],
            ),
            # Query 4: What is RIA
            (
                "What is RIA in Horizon Europe?",
                """**RIA - Research and Innovation Action**

RIA is one of the main funding instruments in Horizon Europe:

**Purpose:**
- Establish new knowledge and/or explore feasibility of new technology
- Typical TRL range: 2-5 (basic research to prototype)

**Funding:**
- **100% funding rate** for all participants
- Typical budget: EUR 3-6 million
- Duration: 36-48 months typically

**Activities covered:**
- Research and development
- Technology validation
- Small-scale prototyping
- Testing and demonstration

**Examples:**
- Developing new materials for batteries
- Novel AI algorithms for healthcare
- Climate modeling research

**Different from IA:**
RIA focuses on earlier-stage research, while Innovation Actions (IA) focus on demonstration and deployment at 70% funding rate.""",
                75,
                ["ria", "research", "innovation", "funding"],
            ),
            # Query 5: How to apply
            (
                "How do I apply for Horizon Europe funding?",
                """**Step-by-Step Guide to Applying for Horizon Europe:**

**1. Find the Right Call**
- Use the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- Filter by topic, deadline, and programme
- Read the Work Programme for your cluster

**2. Build Your Consortium**
- Minimum 3 partners from 3 EU/Associated Countries (for most calls)
- Use partner search tools on the Portal
- Attend networking events and brokerage sessions

**3. Prepare Your Proposal**
- Part A: Administrative forms and budget
- Part B: Technical proposal (Excellence, Impact, Implementation)
- Follow the template strictly - no page limit violations!

**4. Submit Before Deadline**
- Register all partners on the Portal first
- Submit at least 24 hours early
- Keep the submission number

**Timeline:**
- Call publication → Deadline: typically 3-4 months
- Evaluation: 3-5 months
- Grant preparation: 3 months
- Project start: ~9-12 months from call deadline""",
                75,
                ["apply", "portal", "proposal", "consortium"],
            ),
        ],
        ids=[
            "faq_1_sme_eligibility",
            "faq_2_switzerland_participation",
            "faq_3_consortium_requirements",
            "faq_4_what_is_ria",
            "faq_5_how_to_apply",
        ],
    )
    def test_faq_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        min_score: int,
        expected_patterns: List[str],
    ):
        """Test that FAQ responses are complete and informative."""
        analysis = analyzer.analyze(query, response)

        assert analysis.score >= min_score, (
            f"Score {analysis.score} below minimum {min_score}. "
            f"Deflections: {analysis.deflection_phrases_found}. "
            f"Missing: {analysis.missing_elements}"
        )

        assert analysis.category not in [ResponseCategory.DEFLECTION, ResponseCategory.EMPTY], (
            f"FAQ response categorized as {analysis.category}"
        )

        # Check expected patterns are present
        response_lower = response.lower()
        for pattern in expected_patterns:
            assert pattern in response_lower, (
                f"Expected pattern '{pattern}' not found in response"
            )


# =============================================================================
# BUDGET BENCHMARK TESTS (3 queries)
# =============================================================================


class TestBudgetBenchmarkQueries:
    """Tests for budget benchmark query responses."""

    @pytest.mark.parametrize(
        "query,response,min_score",
        [
            # Query 1: RIA budget in Cluster 5
            (
                "What is typical budget for Horizon RIA in Cluster 5?",
                """**Budget Benchmarks for Cluster 5 RIA Projects:**

Based on analysis of **496 funded projects** (2021-2024):

**Total EU Contribution:**
- Minimum: EUR 1.3 million
- Maximum: EUR 20 million
- Average: EUR 4.9 million
- Median: EUR 4.5 million

**Consortium Size:**
- Average: 13.3 partners
- Typical range: 10-18 partners

**Budget by Organization Type:**
- Research Organizations (REC): 34%
- Private Companies (PRC): 33%
- Higher Education (HES): 28%
- Others: 5%

**Recommendation:**
For a typical Cluster 5 RIA, budget between EUR 4-6 million with 12-15 partners.""",
                75,
            ),
            # Query 2: IA budget comparison
            (
                "What budget should I request for an Innovation Action?",
                """**Innovation Action Budget Guidelines:**

**General Benchmarks:**
- Typical range: EUR 5-15 million
- Average: EUR 8 million
- Duration: 36-48 months

**By Cluster:**
| Cluster | Average Budget | Average Partners |
|---------|---------------|-----------------|
| CL4 Digital | EUR 7.5M | 14 |
| CL5 Climate | EUR 9.2M | 16 |
| CL6 Food | EUR 6.8M | 12 |

**Budget Structure:**
- Personnel: 50-60% of budget
- Equipment: 5-10%
- Subcontracting: 10-20%
- Travel: 3-5%
- Other direct costs: 10-15%
- Indirect costs: 25% flat rate

**Tips:**
- Align budget with scale of demonstration
- Justify all costs clearly
- Industry partners can request 70% funding rate""",
                75,
            ),
            # Query 3: Personnel cost benchmarks
            (
                "What are typical personnel costs in EU projects?",
                """**Personnel Cost Benchmarks in Horizon Europe:**

**Daily Rates by Country (EUR):**
| Country | Senior | Mid-level | Junior |
|---------|--------|-----------|--------|
| Germany | 550-700 | 400-550 | 250-350 |
| France | 500-650 | 380-500 | 230-320 |
| Spain | 350-450 | 250-350 | 150-220 |
| Poland | 250-350 | 180-250 | 100-150 |

**Hourly Rates (calculated):**
- Based on 1720 productive hours/year
- Senior researcher: EUR 40-60/hour
- Experienced researcher: EUR 30-45/hour
- Early-stage researcher: EUR 20-30/hour

**Budget Allocation:**
- Personnel typically 50-65% of total project cost
- Include social charges and overheads (25% indirect rate)

**Tips:**
- Use actual payroll data for accuracy
- Consider country-specific labor costs
- Include time for project management (5-10%)""",
                75,
            ),
        ],
        ids=[
            "budget_1_cluster5_ria",
            "budget_2_ia_guidelines",
            "budget_3_personnel_costs",
        ],
    )
    def test_budget_benchmark_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        min_score: int,
    ):
        """Test that budget benchmark responses contain actual statistics."""
        analysis = analyzer.validate_budget_benchmark_response(response)

        assert analysis.score >= min_score, (
            f"Score {analysis.score} below minimum {min_score}. "
            f"Missing: {analysis.missing_elements}"
        )

        # Budget responses should have numbers
        assert analysis.content_metrics.get("has_numbers"), (
            "Budget response should contain numerical data"
        )


# =============================================================================
# PARTNER DISCOVERY TESTS (3 queries)
# =============================================================================


class TestPartnerDiscoveryQueries:
    """Tests for partner discovery query responses."""

    @pytest.mark.parametrize(
        "query,response,min_score,expected_country",
        [
            # Query 1: German hydrogen partners
            (
                "Find German SMEs with hydrogen experience",
                """**Experienced German SMEs in Hydrogen Research:**

Based on CORDIS project data, here are organizations with strong track records:

1. **HyGear BV** - Germany
   - 5 EU projects (2019-2024)
   - Expertise: Hydrogen generation, storage systems
   - Recent: HYFLEXPOWER (EUR 15M project)

2. **Enapter AG** - Germany
   - 4 EU projects
   - Expertise: AEM electrolyzers
   - Notable: GREEN HYSLAND coordinator

3. **Sunfire GmbH** - Dresden, Germany
   - 8 EU projects
   - Expertise: SOEC technology, Power-to-X
   - Major projects: HYLINK, MultiPLHY

4. **H2FLY GmbH** - Stuttgart, Germany
   - 3 EU projects
   - Expertise: Hydrogen aviation
   - Recent: HEAVEN project

**Recommendation:**
Contact organizations through LinkedIn or their project websites. Check CORDIS for contact details of project coordinators.""",
                75,
                "Germany",
            ),
            # Query 2: AI partners in France
            (
                "Find French partners with AI expertise",
                """**French Organizations with AI Expertise:**

**Research Institutions:**
1. **INRIA** - National Institute for Digital Sciences
   - 50+ Horizon Europe projects
   - Expertise: Machine learning, robotics, data science
   - Key areas: Trustworthy AI, AI for health

2. **CNRS** - National Centre for Scientific Research
   - 100+ AI-related projects
   - Strong in: Computer vision, NLP
   - Numerous labs across France

**Universities:**
3. **Sorbonne University**
   - 30+ AI projects
   - SCAI AI research center
   - Focus: AI + Sciences

4. **Paris-Saclay University**
   - 40+ projects
   - Strong industry partnerships
   - AI safety and ethics

**Industry:**
5. **Thales** - Defense and aerospace
   - AI for autonomous systems
   - Cybersecurity AI

6. **Atos** - IT services
   - Edge AI, quantum computing
   - Digital twins""",
                75,
                "France",
            ),
            # Query 3: Health cluster partners
            (
                "Find partners with clinical trial experience in Cluster 1",
                """**Organizations with Clinical Trial Experience (Cluster 1 - Health):**

**Academic Medical Centers:**
1. **Charité - Berlin** (Germany)
   - 80+ H2020/HE projects
   - Expertise: Large-scale trials, digital health
   - Coordinator experience: 15 projects

2. **Karolinska Institute** (Sweden)
   - 70+ projects
   - Expertise: Precision medicine, cancer trials
   - Strong: Ethics and regulatory expertise

3. **University of Oxford** (UK - via association)
   - 100+ health projects
   - COVID vaccine trials experience
   - MHRA regulatory expertise

**CROs (Contract Research Organizations):**
4. **ECRIN** - European Clinical Research Infrastructure
   - Multinational trial coordination
   - Regulatory support across EU

5. **IQVIA** (multiple EU locations)
   - Real-world evidence
   - Decentralized trial expertise

**Tips for Consortium Building:**
- Include at least 2 clinical sites from different countries
- Consider patient organization involvement
- Include regulatory expertise (EMA experience)""",
                75,
                None,
            ),
        ],
        ids=[
            "partner_1_german_hydrogen",
            "partner_2_french_ai",
            "partner_3_health_clinical",
        ],
    )
    def test_partner_discovery_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        min_score: int,
        expected_country: Optional[str],
    ):
        """Test that partner discovery responses list actual organizations."""
        analysis = analyzer.validate_partner_discovery_response(response, expected_country)

        assert analysis.score >= min_score, (
            f"Score {analysis.score} below minimum {min_score}. "
            f"Missing: {analysis.missing_elements}"
        )

        assert analysis.category != ResponseCategory.DEFLECTION, (
            f"Partner response flagged as deflection"
        )


# =============================================================================
# PROJECT SEARCH TESTS (2 queries)
# =============================================================================


class TestProjectSearchQueries:
    """Tests for project search query responses."""

    @pytest.mark.parametrize(
        "query,response,min_score,expected_elements",
        [
            # Query 1: Quantum computing projects
            (
                "Find quantum computing projects in Horizon Europe",
                """**Quantum Computing Projects in Horizon Europe:**

**Major Flagships:**
1. **OPENQKD** - EUR 15 million
   - Coordinator: Austrian Institute of Technology
   - Focus: Quantum key distribution infrastructure
   - 38 partners from 13 countries

2. **MILLENION** - EUR 10 million
   - Coordinator: Alpine Quantum Technologies
   - Focus: Trapped-ion quantum computers
   - Duration: 2021-2024

**Research Projects:**
3. **QUCATS** - Quantum Control
   - EUR 4 million, RIA
   - Novel control techniques for quantum systems

4. **HORIZON-CL4-2023-DIGITAL-EMERGING-01** projects:
   - Multiple quantum sensing projects
   - Total budget: EUR 45 million

**Statistics:**
- 50+ active quantum projects in HE
- Combined funding: EUR 500+ million
- Key countries: DE, FR, AT, NL, IT""",
                75,
                ["quantum", "project", "funding"],
            ),
            # Query 2: Climate adaptation projects
            (
                "Search for climate adaptation projects in Southern Europe",
                """**Climate Adaptation Projects in Southern Europe:**

**Flagship Projects:**
1. **CLIMAS** - Climate Adaptation in Mediterranean
   - EUR 12 million, 2022-2026
   - Coordinator: CMCC (Italy)
   - Focus: Water scarcity, heat waves
   - Partners: Spain, Greece, Portugal, Cyprus

2. **MedCLIMAX** - Mediterranean Climate Extremes
   - EUR 8 million
   - Coordinator: AEMET (Spain)
   - Focus: Extreme weather prediction

**Regional Focus:**
3. **REGILIENCE** - Regional Resilience
   - 14 regions including Andalusia, Sicily, Algarve
   - Practical adaptation measures
   - EUR 6.5 million

4. **LIFE-ADAPT** projects in:
   - Catalonia: Urban heat adaptation
   - Puglia: Agricultural water management
   - Crete: Coastal erosion

**Key Topics:**
- Water management and drought resilience
- Urban cooling and green infrastructure
- Agricultural adaptation
- Forest fire prevention""",
                75,
                ["climate", "adaptation", "project"],
            ),
        ],
        ids=[
            "project_1_quantum_computing",
            "project_2_climate_adaptation",
        ],
    )
    def test_project_search_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        min_score: int,
        expected_elements: List[str],
    ):
        """Test that project search responses contain actual projects."""
        analysis = analyzer.validate_project_response(response, expected_elements)

        assert analysis.score >= min_score, (
            f"Score {analysis.score} below minimum {min_score}"
        )

        # Should mention specific projects
        assert analysis.content_metrics.get("has_numbers"), (
            "Project search should include funding amounts"
        )


# =============================================================================
# CONSORTIUM PATTERN TESTS (2 queries)
# =============================================================================


class TestConsortiumPatternQueries:
    """Tests for consortium pattern query responses."""

    @pytest.mark.parametrize(
        "query,response,min_score",
        [
            # Query 1: Health IA consortium patterns
            (
                "What is typical consortium size for Health Innovation Actions?",
                """**Consortium Patterns for Health Innovation Actions:**

Based on 150+ funded Health IA projects (2021-2024):

**Consortium Size:**
- Average: 18 partners
- Median: 16 partners
- Range: 8-35 partners
- Countries: 9-12 typically

**Organization Type Distribution:**
| Type | Percentage | Typical Count |
|------|------------|---------------|
| Higher Education (HES) | 28% | 5 |
| Research Organizations (REC) | 25% | 4-5 |
| Private Companies (PRC) | 32% | 6 |
| Hospitals/Clinical | 10% | 2 |
| Other | 5% | 1 |

**Geographic Distribution:**
- Top coordinator countries: DE, NL, ES, IT, FR
- Strong presence: Nordics for clinical, UK for pharma
- Widening countries: Often 2-3 included

**Recommendations:**
- Include 2-3 clinical sites for health IAs
- Balance research (30%) with industry (35%)
- Include patient organizations for impact""",
                75,
            ),
            # Query 2: Digital cluster consortium
            (
                "What are consortium patterns for Cluster 4 projects?",
                """**Consortium Patterns for Cluster 4 (Digital, Industry, Space):**

**Overall Statistics (800+ projects analyzed):**

**By Action Type:**
| Action | Avg Partners | Avg Countries | Avg Budget |
|--------|-------------|---------------|------------|
| RIA | 12 | 8 | EUR 4.5M |
| IA | 16 | 10 | EUR 9.2M |
| CSA | 8 | 6 | EUR 2.1M |

**Organization Mix:**
- Industry: 40% (higher than other clusters)
- Research: 30%
- Academia: 25%
- Other: 5%

**Success Patterns:**
1. **Diverse expertise** - Mix of AI, cybersecurity, cloud
2. **Industry involvement** - Higher success with industrial leads
3. **SME participation** - ~30% of consortia include SMEs
4. **End-user involvement** - Cities, manufacturers, etc.

**Top Coordinator Countries:**
1. Germany - 22%
2. Spain - 15%
3. Italy - 12%
4. France - 11%
5. Netherlands - 8%

**Tip:** Include technology integrators and demo sites for higher impact scores.""",
                75,
            ),
        ],
        ids=[
            "consortium_1_health_ia",
            "consortium_2_cluster4",
        ],
    )
    def test_consortium_pattern_response_quality(
        self,
        analyzer: ResponseQualityAnalyzer,
        query: str,
        response: str,
        min_score: int,
    ):
        """Test that consortium pattern responses contain statistics."""
        analysis = analyzer.analyze(query, response)

        assert analysis.score >= min_score, (
            f"Score {analysis.score} below minimum {min_score}"
        )

        assert analysis.content_metrics.get("has_numbers"), (
            "Consortium pattern response should include statistics"
        )

        assert analysis.content_metrics.get("has_structured_data"), (
            "Consortium pattern response should have structured data (tables/lists)"
        )


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_response(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of empty response."""
        analysis = analyzer.analyze("What is RIA?", "")

        assert analysis.category == ResponseCategory.EMPTY
        assert analysis.score == 0
        assert analysis.confidence >= 0.9

    def test_very_short_response(self, analyzer: ResponseQualityAnalyzer):
        """Test handling of very short response."""
        # A very short response to a substantive question should score low
        analysis = analyzer.analyze(
            "What is RIA in Horizon Europe and what are the funding rates?",
            "RIA is a type of grant."
        )

        # Short responses to substantive queries should not score high
        assert analysis.score < 60 or len(analysis.missing_elements) > 0, (
            f"Very short response should be penalized. Score: {analysis.score}, "
            f"Missing: {analysis.missing_elements}"
        )

    def test_good_response_with_structure(self, analyzer: ResponseQualityAnalyzer):
        """Test that well-structured responses score high."""
        response = """
        **Research and Innovation Action (RIA)**

        RIA is a funding instrument in Horizon Europe that supports:

        1. **Basic and applied research** - TRL 2-5
        2. **Technology development** - Prototyping and validation
        3. **Knowledge creation** - New scientific discoveries

        **Key Features:**
        - Funding rate: 100%
        - Typical duration: 36-48 months
        - Average budget: EUR 4-5 million

        **Eligibility:**
        - Minimum 3 entities from 3 EU/Associated Countries
        - Academic, research, and industry participation

        For more details, visit the [EC Funding Portal](https://ec.europa.eu/funding).
        """
        analysis = analyzer.analyze("What is RIA?", response)

        assert analysis.score >= 75
        assert analysis.category == ResponseCategory.COMPLETE
        assert analysis.content_metrics.get("has_structured_data")

    def test_is_acceptable_method(self, analyzer: ResponseQualityAnalyzer):
        """Test the is_acceptable convenience method."""
        good_analysis = QualityAnalysis(
            score=80,
            category=ResponseCategory.COMPLETE,
            confidence=0.9,
        )
        assert analyzer.is_acceptable(good_analysis)

        bad_analysis = QualityAnalysis(
            score=40,
            category=ResponseCategory.DEFLECTION,
            confidence=0.9,
        )
        assert not analyzer.is_acceptable(bad_analysis)

    def test_deflection_phrases_comprehensive(self, analyzer: ResponseQualityAnalyzer):
        """Test that all documented deflection phrases are detected."""
        for phrase in ResponseQualityAnalyzer.DEFLECTION_PHRASES[:10]:
            response = f"Some text before. {phrase.capitalize()}. Some text after."
            analysis = analyzer.analyze("test query", response)
            assert phrase in analysis.deflection_phrases_found, (
                f"Phrase '{phrase}' should be detected"
            )
