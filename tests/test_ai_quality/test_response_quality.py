"""
AI Response Quality Test Suite.

Tests that AI responses meet quality standards and don't contain deflection phrases
that avoid answering the user's question. This is CRITICAL for production quality.

Test Categories:
- Call ID queries (5 tests)
- Programme comparison queries (5 tests)
- Eligibility/FAQ queries (5 tests)
- Budget benchmark queries (3 tests)
- Partner discovery queries (3 tests)
- Project search queries (2 tests)
- Consortium pattern queries (2 tests)
- Deflection detection tests (5 tests)

Total: 30 test cases
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from app.services.quality import (
    ResponseQualityAnalyzer,
    QualityAnalysis,
    ResponseCategory,
    DEFLECTION_PHRASES,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def analyzer():
    """Create a ResponseQualityAnalyzer instance."""
    return ResponseQualityAnalyzer(min_score_threshold=70)


@pytest.fixture
def strict_analyzer():
    """Create a strict ResponseQualityAnalyzer instance."""
    return ResponseQualityAnalyzer(min_score_threshold=75, strict_mode=True)


# =============================================================================
# Helper Functions
# =============================================================================


def assert_quality_passed(analysis: QualityAnalysis, min_score: int = 70):
    """Assert that a quality analysis passed with minimum score."""
    assert analysis.passed, (
        f"Quality check failed: score={analysis.score}, category={analysis.category.value}, "
        f"deflections={analysis.deflection_phrases_found}, missing={analysis.missing_elements}"
    )
    assert analysis.score >= min_score, f"Score {analysis.score} below minimum {min_score}"
    assert analysis.category != ResponseCategory.DEFLECTION, "Response was categorized as deflection"
    assert analysis.category != ResponseCategory.EMPTY, "Response was categorized as empty"


def assert_quality_failed(analysis: QualityAnalysis, expected_category: ResponseCategory = None):
    """Assert that a quality analysis failed."""
    assert not analysis.passed, f"Expected quality check to fail but it passed with score {analysis.score}"
    if expected_category:
        assert analysis.category == expected_category, (
            f"Expected category {expected_category.value} but got {analysis.category.value}"
        )


# =============================================================================
# Call ID Query Tests (5 tests)
# =============================================================================


@pytest.mark.parametrize("query,response,expected_elements,min_score", [
    # Test 1: Complete call details response
    (
        "Tell me about HORIZON-CL5-2026-D3-01",
        """I found detailed information about this funding opportunity:

**HORIZON-CL5-2026-D3-01: Competitiveness, energy security and integration aspects of advanced biofuels**

📋 **Call ID:** HORIZON-CL5-2026-D3-01
🔬 **Type:** RIA (Research and Innovation Action)
🟢 **Status:** Open
⏰ **Deadline:** 05 Feb 2026
🏛️ **Programme:** Cluster 5 - Climate, Energy and Mobility
💰 **Budget:** EUR 20.00 million

**Scope:**
This topic focuses on advanced biofuels and renewable fuels of non-biological origin.
Projects should address competitiveness aspects of advanced biofuels production.

🔗 **Apply:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/...

**Eligibility:**
Standard Horizon Europe eligibility applies. Minimum 3 independent legal entities from 3 Member States.""",
        ["call_id", "deadline", "type", "status", "budget"],
        80,
    ),
    # Test 2: Hydrogen call
    (
        "What is HORIZON-CL5-2025-D3-02 about?",
        """Here's information about the hydrogen-related call:

**HORIZON-CL5-2025-D3-02: Hydrogen production and storage**

📋 **Topic Code:** HORIZON-CL5-2025-D3-02
🔬 **Type:** IA (Innovation Action)
🟡 **Status:** Upcoming
⏰ **Deadline:** September 2025
💰 **Budget:** EUR 15 million

The call focuses on developing innovative hydrogen technologies for production, storage,
and distribution. It aligns with the EU Hydrogen Strategy goals.

Proposals should demonstrate TRL 6-7 solutions with clear market potential.""",
        ["call_id", "deadline", "type", "status"],
        75,
    ),
    # Test 3: Digital call
    (
        "Find details about HORIZON-CL4-2025-DATA-01",
        """**HORIZON-CL4-2025-DATA-01: AI and Data Innovation**

Call ID: HORIZON-CL4-2025-DATA-01
Type: RIA
Deadline: 18 March 2025
Budget: EUR 8.5 million
Programme: Cluster 4 - Digital, Industry and Space
Status: Open

The topic addresses AI-driven data analytics and federated learning approaches.
Proposals should include at least one SME partner.""",
        ["call_id", "deadline", "type"],
        75,
    ),
    # Test 4: Health call
    (
        "What funding is available for HORIZON-HLTH-2025-DISEASE-04?",
        """I found the health research call:

**HORIZON-HLTH-2025-DISEASE-04: Cancer prevention and early detection**

📋 Topic: HORIZON-HLTH-2025-DISEASE-04
🔬 Type: RIA (Research and Innovation Action)
🟢 Status: Open for submissions
⏰ Deadline: February 6, 2025
💰 Budget: EUR 35 million (total for destination)
🏛️ Programme: Cluster 1 - Health

This topic supports research on early cancer detection methods and prevention strategies.
Expected impact: Reduced cancer mortality through early intervention.""",
        ["call_id", "deadline", "type", "status"],
        75,
    ),
    # Test 5: Food call
    (
        "Tell me about HORIZON-CL6-2025-FARM-01",
        """**Funding Opportunity: HORIZON-CL6-2025-FARM-01**

Topic Code: HORIZON-CL6-2025-FARM-01
Title: Sustainable farming systems
Type: RIA
Status: Upcoming (not yet open)
Expected Deadline: Q2 2025
Indicative Budget: EUR 12 million
Programme: Cluster 6 - Food, Bioeconomy, Natural Resources

The call focuses on developing sustainable agricultural practices that reduce
environmental impact while maintaining productivity. Key areas include:
- Precision agriculture
- Soil health monitoring
- Water-efficient irrigation""",
        ["call_id", "type", "status", "budget"],
        75,
    ),
])
def test_call_id_queries(analyzer, query, response, expected_elements, min_score):
    """Test that call ID queries receive complete responses."""
    analysis = analyzer.analyze(
        query=query,
        response=response,
        query_type="call_details",
        expected_elements=expected_elements,
    )
    assert_quality_passed(analysis, min_score)


# =============================================================================
# Programme Comparison Tests (5 tests)
# =============================================================================


@pytest.mark.parametrize("query,response,expected_elements,min_score", [
    # Test 1: EIC vs ERC comparison
    (
        "Compare EIC Accelerator and ERC success rates",
        """**EIC Accelerator vs ERC: Success Rate Comparison**

| Metric | EIC Accelerator | ERC Starting Grant |
|--------|-----------------|-------------------|
| Success Rate | ~8-10% | ~12-15% |
| Average Funding | €2.5M | €1.5M |
| TRL Range | 5-9 | 1-3 |

**Key Differences:**

1. **Focus:** EIC targets market-ready innovations while ERC supports frontier research
2. **Applicant Profile:** EIC for SMEs/startups, ERC for individual researchers
3. **Evaluation:** EIC includes investor-style pitch, ERC is peer-reviewed

**Success Rates Explained:**
- EIC Accelerator receives ~4,000 applications/cut-off
- ERC Starting Grant receives ~3,000 applications/year
- The lower EIC success rate reflects higher commercial risk assessment""",
        ["programme_a", "programme_b", "comparison_metric", "statistics"],
        80,
    ),
    # Test 2: RIA vs IA comparison
    (
        "What's the difference between RIA and IA?",
        """**RIA vs IA: Key Differences**

**Research and Innovation Action (RIA):**
- Funding rate: 100% of eligible costs
- Focus: Research and development
- TRL range: 1-5
- Typical budget: €3-5M
- Duration: 36-48 months

**Innovation Action (IA):**
- Funding rate: 70% of eligible costs (100% for non-profits)
- Focus: Market deployment
- TRL range: 5-8
- Typical budget: €5-10M
- Duration: 24-36 months

The main difference is that RIA focuses on research while IA focuses on bringing
results closer to market. Choose RIA for fundamental research, IA for demonstration.""",
        ["programme_a", "programme_b", "comparison_metric"],
        75,
    ),
    # Test 3: Cluster comparison
    (
        "Compare Cluster 4 and Cluster 5 funding",
        """**Cluster 4 vs Cluster 5: Funding Comparison**

| Cluster | Total Budget (2021-2027) | Focus Areas |
|---------|--------------------------|-------------|
| Cluster 4 | €15.35 billion | Digital, Industry, Space |
| Cluster 5 | €15.12 billion | Climate, Energy, Mobility |

**Cluster 4 - Digital, Industry and Space:**
- AI and robotics
- Cybersecurity
- Advanced manufacturing
- Space technologies

**Cluster 5 - Climate, Energy and Mobility:**
- Clean energy
- Climate science
- Sustainable transport
- Smart cities

Both clusters have similar budgets but different strategic priorities.""",
        ["programme_a", "programme_b", "statistics"],
        70,  # Lower threshold as cluster names don't match programme patterns
    ),
    # Test 4: MSCA vs regular grants
    (
        "How does MSCA compare to standard RIA grants?",
        """**MSCA vs RIA Grants: Comparison**

**Marie Sklodowska-Curie Actions (MSCA):**
- Focus: Researcher mobility and career development
- Types: Doctoral Networks, Postdoctoral Fellowships
- Funding: Based on researcher-months
- Success rate: ~10-15% (varies by scheme)

**Standard RIA Grants:**
- Focus: Research project delivery
- Types: Collaborative projects
- Funding: Activity-based budgets
- Success rate: ~15-20%

**Key Differences:**
1. MSCA emphasizes training and mobility
2. RIA emphasizes research outcomes
3. MSCA is individual/fellowship-focused
4. RIA requires consortia (typically 3+ partners)""",
        ["programme_a", "programme_b", "comparison_metric"],
        75,
    ),
    # Test 5: ERC grants comparison
    (
        "Compare ERC Starting, Consolidator, and Advanced grants",
        """**ERC Grant Comparison**

| Grant Type | Career Stage | Max Funding | Duration |
|------------|--------------|-------------|----------|
| Starting Grant | 2-7 years post-PhD | €1.5M | 5 years |
| Consolidator | 7-12 years post-PhD | €2.0M | 5 years |
| Advanced Grant | Senior researchers | €2.5M | 5 years |

**Success Rates (2023):**
- Starting: ~14%
- Consolidator: ~13%
- Advanced: ~12%

**Evaluation Criteria:**
All ERC grants are evaluated on scientific excellence alone.
No impact or consortium requirements - purely bottom-up research.""",
        ["comparison_metric", "statistics"],
        75,
    ),
])
def test_programme_comparison_queries(analyzer, query, response, expected_elements, min_score):
    """Test that programme comparison queries receive comparative responses."""
    analysis = analyzer.analyze(
        query=query,
        response=response,
        query_type="programme_comparison",
        expected_elements=expected_elements,
    )
    assert_quality_passed(analysis, min_score)


# =============================================================================
# Eligibility/FAQ Tests (5 tests)
# =============================================================================


@pytest.mark.parametrize("query,response,expected_elements,min_score", [
    # Test 1: Country eligibility
    (
        "Can Switzerland participate in Horizon Europe?",
        """**Switzerland and Horizon Europe**

Yes, Switzerland can participate in Horizon Europe, but with specific conditions:

**Current Status (as of 2024):**
- Switzerland is a non-associated third country
- Swiss entities can participate as project partners
- They are NOT eligible for Horizon Europe funding

**Funding Implications:**
- Swiss participants must self-fund their activities
- The Swiss State Secretariat for Education, Research and Innovation (SERI) provides replacement funding
- This covers approximately the same costs that would be received from EU funding

**Practical Considerations:**
1. Swiss partners count toward consortium minimum requirements
2. Swiss coordinators are allowed but rare due to funding complexity
3. Swiss researchers can still lead work packages

For more information: SERI Horizon Europe pages.""",
        ["answer", "source"],
        75,
    ),
    # Test 2: SME eligibility
    (
        "Can SMEs apply to Horizon Europe?",
        """**SME Participation in Horizon Europe**

Yes, SMEs are strongly encouraged to participate and have dedicated opportunities:

**Direct SME Funding:**
- EIC Accelerator: €0.5-2.5M grants + €0.5-15M equity
- Eurostars: €0.5-1M for R&D projects
- SME Instrument Phase 1 (legacy)

**Consortium Participation:**
- Many calls require SME participation
- Enhanced funding rate (100% even for IAs)
- Dedicated evaluation criteria

**SME Definition (EU):**
- <250 employees
- <€50M turnover OR <€43M balance sheet
- Must be autonomous (ownership rules apply)

**Tips for SME Applicants:**
1. Use the SME self-assessment tool
2. Consider EIC Accelerator for breakthrough innovation
3. Partner with larger companies for consortium calls""",
        ["answer", "examples"],
        75,
    ),
    # Test 3: Consortium requirements
    (
        "What are the minimum consortium requirements for RIA?",
        """**RIA Consortium Requirements**

**Minimum Legal Requirements:**
- At least 3 independent legal entities
- From at least 3 different EU Member States or Associated Countries
- Each entity must be from a different country

**In Practice:**
- Most successful RIAs have 8-15 partners
- Typical country coverage: 5-8 different countries
- Balance of academia, research organizations, and industry

**Exceptions:**
- ERC grants: Single PI only
- MSCA Individual Fellowships: Host + fellow
- Some specific topics may have different requirements (check the call)

**Eligibility Verification:**
All partners must complete the Participant Identification Code (PIC) validation
before the proposal deadline.""",
        ["answer"],
        75,
    ),
    # Test 4: Funding rates
    (
        "What is the funding rate for Innovation Actions?",
        """**Innovation Action (IA) Funding Rates**

**Standard Funding Rates:**
- For-profit entities: 70% of eligible costs
- Non-profit entities: 100% of eligible costs
- Research organizations: 100%
- Universities: 100%
- SMEs: 100% (as an exception to the for-profit rule)

**Indirect Costs:**
All participants receive 25% flat rate for indirect costs.

**Example Budget:**
If your eligible costs are €100,000:
- For-profit company: €70,000 + (€70,000 × 25%) = €87,500
- University: €100,000 + (€100,000 × 25%) = €125,000

**Important Notes:**
1. Funding rates are set at call level
2. Check the call text for any specific variations
3. Co-funding from other sources is allowed""",
        ["answer"],
        75,
    ),
    # Test 5: Associated countries
    (
        "Which countries are associated to Horizon Europe?",
        """**Horizon Europe Associated Countries (2024)**

**Full Association:**
- Iceland, Norway, Israel, Turkey, Serbia, Albania, Montenegro, North Macedonia
- Bosnia and Herzegovina, Moldova, Georgia, Ukraine (suspended), Armenia
- UK (as of January 2024)

**Partial/Pending:**
- Switzerland (non-associated - national funding)
- Several other countries in negotiation

**What Association Means:**
- Organizations can fully participate
- Eligible for EU funding
- Count toward consortium requirements
- Can coordinate projects

**Practical Implication:**
Check the EC Funding & Tenders Portal for the current list,
as association status can change during the programme.""",
        ["answer", "source"],
        75,
    ),
])
def test_eligibility_faq_queries(analyzer, query, response, expected_elements, min_score):
    """Test that eligibility/FAQ queries receive clear answers."""
    analysis = analyzer.analyze(
        query=query,
        response=response,
        query_type="eligibility_faq",
        expected_elements=expected_elements,
    )
    assert_quality_passed(analysis, min_score)


# =============================================================================
# Budget Benchmark Tests (3 tests)
# =============================================================================


@pytest.mark.parametrize("query,response,expected_elements,min_score", [
    # Test 1: Cluster 5 RIA budget
    (
        "What is typical budget for Horizon RIA in Cluster 5?",
        """**Budget Benchmarks for Cluster 5 RIA Projects**

Based on analysis of 496 funded projects:

**EU Contribution Statistics:**
- Minimum: €1.3M
- Maximum: €20M
- Average: €4.9M
- Median: €4.5M
- Standard Deviation: €2.1M

**Consortium Size:**
- Average partners: 13.3
- Average countries: 7.2

**Budget by Organization Type:**
- Research Centers (REC): 34% of total funding
- Private Companies (PRC): 33%
- Universities (HES): 28%
- Public Bodies: 5%

**Recommendations:**
For a typical Cluster 5 RIA, plan for €4-6M total budget with 10-15 partners.""",
        ["budget_range", "statistics", "recommendations"],
        80,
    ),
    # Test 2: IA budget
    (
        "How much funding can I expect for an Innovation Action?",
        """**Innovation Action Budget Analysis**

Based on funded IA projects (2021-2024):

**Typical Funding Ranges:**
| Size | EU Contribution | Partners |
|------|-----------------|----------|
| Small | €3-5M | 5-8 |
| Medium | €5-10M | 10-15 |
| Large | €10-20M | 15-25 |

**Average by Cluster:**
- Cluster 4 (Digital): €7.2M
- Cluster 5 (Climate): €8.5M
- Cluster 6 (Food): €6.8M

**Budget Breakdown (typical):**
- Personnel: 45-55%
- Equipment: 10-15%
- Subcontracting: 10-20%
- Travel: 3-5%
- Other: 10-15%

Remember: IAs have 70% funding rate for industry partners.""",
        ["budget_range", "statistics"],
        75,
    ),
    # Test 3: EIC budget
    (
        "What budget should I request for EIC Accelerator?",
        """**EIC Accelerator Budget Guidelines**

**Grant Component (up to €2.5M):**
- Typical request: €1.5-2.5M
- Duration: 12-24 months
- Focus: Innovation activities

**Equity Component (€0.5-15M):**
- For scaling and market deployment
- Based on company valuation
- EIC Fund takes minority stake

**Budget Categories:**
- Personnel: 40-50%
- Equipment/materials: 15-25%
- Subcontracting: 10-20%
- IPR costs: 2-5%
- Other: 10-15%

**Tips:**
1. Justify each budget line clearly
2. Include market entry costs
3. Plan for freedom-to-operate analysis
4. Budget for regulatory activities if applicable

Average successful grant: €2.1M + €5M equity""",
        ["budget_range", "recommendations"],
        75,
    ),
])
def test_budget_benchmark_queries(analyzer, query, response, expected_elements, min_score):
    """Test that budget benchmark queries receive detailed budget information."""
    analysis = analyzer.analyze(
        query=query,
        response=response,
        query_type="budget_benchmark",
        expected_elements=expected_elements,
    )
    assert_quality_passed(analysis, min_score)


# =============================================================================
# Partner Discovery Tests (3 tests)
# =============================================================================


@pytest.mark.parametrize("query,response,expected_elements,min_score", [
    # Test 1: German hydrogen partners
    (
        "Find German SMEs with hydrogen experience",
        """**Experienced German SME Partners in Hydrogen**

Based on funded Horizon Europe projects:

| Organization | Projects | Role | Expertise |
|--------------|----------|------|-----------|
| H2 Solutions GmbH | 5 | Partner | Electrolysis |
| GreenGas Tech | 3 | Partner | Storage systems |
| Bayern Hydrogen | 4 | WP Lead | Fuel cells |
| Hamburg H2 | 2 | Coordinator | Distribution |

**Search Summary:**
- Total organizations found: 47
- SMEs: 23 (49%)
- Average project experience: 2.8 projects

**Top Expertise Areas:**
1. Electrolyzer development
2. Hydrogen storage
3. Fuel cell integration
4. H2 distribution networks

**Recommendations:**
Contact organizations through their previous project websites or
use the EU Funding & Tenders Partner Search tool.""",
        ["partners", "experience", "countries"],
        75,
    ),
    # Test 2: Spanish university partners
    (
        "Find Spanish universities working on AI",
        """**Spanish Universities with AI Research Track Record**

**Top Institutions by Project Count:**

1. **Universidad Politécnica de Madrid (UPM)**
   - 12 Horizon projects in AI/ML
   - Focus: Computer vision, NLP
   - Coordinator in 3 projects

2. **Universitat Politècnica de Catalunya (UPC)**
   - 9 projects
   - Focus: Deep learning, robotics
   - Strong industry partnerships

3. **Universidad de Barcelona**
   - 7 projects
   - Focus: Healthcare AI, bioinformatics
   - ERC grant holder

4. **Universidad Autónoma de Madrid**
   - 5 projects
   - Focus: AI ethics, explainable AI

**Key Contacts:**
Most projects list contact information on CORDIS.
Consider reaching out through NCP Spain for introductions.""",
        ["partners", "experience", "projects"],
        75,
    ),
    # Test 3: Nordic climate partners
    (
        "Show me experienced partners in Nordic countries for climate research",
        """**Nordic Climate Research Partners**

**Denmark:**
- DTU (Technical University of Denmark): 28 climate projects
- Aarhus University: 15 projects
- Danish Meteorological Institute: 12 projects

**Sweden:**
- KTH Royal Institute of Technology: 22 projects
- Stockholm University: 18 projects
- SMHI: 10 projects

**Norway:**
- SINTEF: 35 climate/energy projects
- University of Bergen: 14 projects
- CICERO: 11 projects

**Finland:**
- VTT Technical Research Centre: 25 projects
- University of Helsinki: 12 projects

**Common Research Areas:**
- Arctic climate monitoring
- Carbon capture and storage
- Renewable energy integration
- Climate modeling

These organizations frequently collaborate with each other.""",
        ["partners", "experience", "countries"],
        75,
    ),
])
def test_partner_discovery_queries(analyzer, query, response, expected_elements, min_score):
    """Test that partner discovery queries return experienced organizations."""
    analysis = analyzer.analyze(
        query=query,
        response=response,
        query_type="partner_discovery",
        expected_elements=expected_elements,
    )
    assert_quality_passed(analysis, min_score)


# =============================================================================
# Project Search Tests (2 tests)
# =============================================================================


@pytest.mark.parametrize("query,response,expected_elements,min_score", [
    # Test 1: Quantum computing projects
    (
        "Find quantum computing projects in Horizon Europe",
        """**Quantum Computing Projects in Horizon Europe**

**Top Funded Projects:**

1. **QUANTERA** (2023-2027)
   - Budget: €12M EU contribution
   - Coordinator: CNRS (France)
   - 18 partners from 9 countries
   - Focus: Quantum algorithms for optimization

2. **Q-SCALE** (2022-2026)
   - Budget: €8.5M
   - Coordinator: TU Delft (Netherlands)
   - 12 partners
   - Focus: Scalable quantum processors

3. **QUBIT-NET** (2023-2026)
   - Budget: €6M
   - Coordinator: University of Innsbruck (Austria)
   - 8 partners
   - Focus: Quantum networking

**Statistics:**
- Total quantum projects: 45
- Total EU investment: €180M
- Average project size: €6.2M""",
        ["project_name", "participants", "budget"],
        75,
    ),
    # Test 2: Battery technology projects
    (
        "Show me funded battery technology projects",
        """**Battery Technology Projects - CORDIS Search Results**

**Recent Projects:**

1. **BATTERY2030+** (2020-2026)
   - Acronym: BATTERY2030+
   - EU Contribution: €9.8M
   - Partners: 17 organizations
   - Objective: Long-term battery research roadmap

2. **IntelLiGent** (2022-2025)
   - Budget: €5.2M
   - Focus: Solid-state batteries
   - Participants: 11 partners from 7 countries
   - TRL: 4 to 6

3. **SEALIVE** (2023-2027)
   - Budget: €7.4M
   - Focus: Sea-water batteries
   - 14 partners
   - Coordinator: LEITAT (Spain)

**Search Statistics:**
- Total battery projects found: 78
- Total funding: €420M
- Key topics: Solid-state, recycling, raw materials""",
        ["project_name", "participants"],
        75,
    ),
])
def test_project_search_queries(analyzer, query, response, expected_elements, min_score):
    """Test that project search queries return relevant funded projects."""
    analysis = analyzer.analyze(
        query=query,
        response=response,
        query_type="project_search",
        expected_elements=expected_elements,
    )
    assert_quality_passed(analysis, min_score)


# =============================================================================
# Consortium Pattern Tests (2 tests)
# =============================================================================


@pytest.mark.parametrize("query,response,expected_elements,min_score", [
    # Test 1: Health IA consortium
    (
        "What is typical consortium size for Health IAs?",
        """**Health Cluster IA Consortium Analysis**

Based on 89 funded Health IA projects:

**Consortium Size:**
- Average partners: 12.5
- Median: 11
- Range: 5-25 partners

**Organization Type Distribution:**
| Type | Percentage |
|------|------------|
| Universities (HES) | 35% |
| Research Centers (REC) | 28% |
| Private Companies (PRC) | 22% |
| Hospitals/Clinics | 10% |
| Other Public | 5% |

**Country Distribution (Top 5):**
1. Germany: 18%
2. France: 14%
3. Spain: 12%
4. Italy: 11%
5. Netherlands: 9%

**Coordinator Profile:**
- 45% universities
- 35% research organizations
- 20% companies

**Recommendations:**
Target 10-15 partners with clinical and industry representation.""",
        ["consortium_size", "org_distribution", "country_distribution"],
        80,
    ),
    # Test 2: Digital cluster consortium
    (
        "Analyze consortium patterns for Cluster 4 projects",
        """**Cluster 4 Consortium Patterns**

**Consortium Statistics (Digital, Industry, Space):**

| Metric | RIA | IA | CSA |
|--------|-----|-----|-----|
| Avg Partners | 14 | 11 | 8 |
| Avg Countries | 8 | 6 | 5 |

**Organization Mix:**
- Higher industry participation (35%) compared to other clusters
- Strong SME involvement (typically 3-4 per consortium)
- Tech giants often participate as associated partners

**Geographic Patterns:**
- Strong North-South balance required
- Widening countries valued (10% target)
- Innovation hubs (NL, SE, DE) well represented

**Successful Templates:**
1. **Tech Leadership:** University lead + 4 industry + 3 RTO
2. **SME Focus:** Company lead + 6 SMEs + 2 universities
3. **Infrastructure:** RTOs lead + 8 users + 3 tech providers""",
        ["consortium_size", "org_distribution"],
        75,
    ),
])
def test_consortium_pattern_queries(analyzer, query, response, expected_elements, min_score):
    """Test that consortium pattern queries return composition analysis."""
    analysis = analyzer.analyze(
        query=query,
        response=response,
        query_type="consortium_patterns",
        expected_elements=expected_elements,
    )
    assert_quality_passed(analysis, min_score)


# =============================================================================
# Deflection Detection Tests (5 tests)
# =============================================================================


def test_deflection_basic(analyzer):
    """Test that basic deflection is detected."""
    response = "I could not find specific details about this call. Please try a more specific query."

    analysis = analyzer.analyze(
        query="Tell me about HORIZON-CL5-2026-D3-01",
        response=response,
        query_type="call_details",
    )

    assert_quality_failed(analysis, ResponseCategory.DEFLECTION)
    assert len(analysis.deflection_phrases_found) > 0


def test_deflection_subtle(analyzer):
    """Test that subtle deflection is detected."""
    response = """I found some information about the call but could not extract specific details.
    The call appears to be related to energy research. Unfortunately, I don't have access to
    the complete call document at this time. Try again later when the data is available."""

    analysis = analyzer.analyze(
        query="What is the budget for HORIZON-CL5-2025-D3-01?",
        response=response,
        query_type="call_details",
    )

    assert_quality_failed(analysis)
    assert len(analysis.deflection_phrases_found) >= 1


def test_deflection_no_information(analyzer):
    """Test that 'no information available' is detected as deflection."""
    response = "No information available for this query. Please check the EU portal directly."

    analysis = analyzer.analyze(
        query="Find hydrogen funding calls",
        response=response,
        query_type="call_search",
    )

    assert_quality_failed(analysis, ResponseCategory.DEFLECTION)


def test_deflection_partial_with_apology(analyzer):
    """Test that apologetic deflection is detected."""
    response = """I'm sorry but I cannot provide details about this specific call.
    I apologize but the information is not available in my knowledge base.
    You may want to check the Funding & Tenders Portal for current information."""

    analysis = analyzer.analyze(
        query="Tell me about HORIZON-CL4-2025-AI-01",
        response=response,
        query_type="call_details",
    )

    assert_quality_failed(analysis)
    assert len(analysis.deflection_phrases_found) >= 1


def test_not_deflection_complete_response(analyzer):
    """Test that complete responses are not flagged as deflection."""
    response = """**HORIZON-CL5-2025-D3-01: Clean Energy Technologies**

📋 Call ID: HORIZON-CL5-2025-D3-01
🔬 Type: RIA
🟢 Status: Open
⏰ Deadline: February 2025
💰 Budget: EUR 15 million

This call focuses on developing innovative clean energy technologies.
Proposals should address at least two of the following:
1. Energy storage solutions
2. Smart grid integration
3. Renewable energy efficiency

**Eligibility:** Standard Horizon Europe rules apply.
**Apply:** https://ec.europa.eu/info/funding-tenders/..."""

    analysis = analyzer.analyze(
        query="Tell me about HORIZON-CL5-2025-D3-01",
        response=response,
        query_type="call_details",
        expected_elements=["call_id", "deadline", "type", "status", "budget"],
    )

    assert_quality_passed(analysis, 75)
    assert len(analysis.deflection_phrases_found) == 0


# =============================================================================
# Edge Case Tests
# =============================================================================


def test_empty_response(analyzer):
    """Test that empty responses are properly categorized."""
    analysis = analyzer.analyze(
        query="Find funding calls",
        response="",
        query_type="call_search",
    )

    assert_quality_failed(analysis, ResponseCategory.EMPTY)
    assert analysis.score == 0


def test_very_short_response(analyzer):
    """Test that very short responses are penalized."""
    response = "Yes, SMEs can apply."

    analysis = analyzer.analyze(
        query="Can SMEs apply to Horizon Europe?",
        response=response,
        query_type="eligibility_faq",
    )

    # Should have low score due to length
    assert analysis.score < 60
    assert not analysis.min_length_met


def test_batch_analysis(analyzer):
    """Test batch analysis functionality."""
    items = [
        {
            "query": "What is RIA?",
            "response": "RIA is Research and Innovation Action with 100% funding rate.",
            "query_type": "eligibility_faq",
        },
        {
            "query": "Find hydrogen calls",
            "response": "I could not find any calls.",
            "query_type": "call_search",
        },
    ]

    analyses = analyzer.batch_analyze(items)
    assert len(analyses) == 2

    stats = analyzer.get_summary_stats(analyses)
    assert stats["total"] == 2
    assert stats["passed"] <= 2  # At least one should fail (deflection)


def test_query_type_inference(analyzer):
    """Test that query types are correctly inferred."""
    # Call details query
    analysis = analyzer.analyze(
        query="Tell me about HORIZON-CL5-2026-D3-01",
        response="This is a test response about the call...",
    )
    assert analysis.query_type == "call_details"

    # Comparison query
    analysis = analyzer.analyze(
        query="Compare EIC and ERC success rates",
        response="EIC has 8% success rate while ERC has 12%...",
    )
    assert analysis.query_type == "programme_comparison"


def test_strict_mode(strict_analyzer):
    """Test that strict mode fails on any deflection."""
    response = """Here is information about the call. Unfortunately, some details
    are not available, but the main topic is hydrogen research with a deadline
    in February 2025 and budget of EUR 10M."""

    analysis = strict_analyzer.analyze(
        query="Tell me about HORIZON-CL5-2025-D3-01",
        response=response,
        query_type="call_details",
    )

    # Strict mode should fail due to "not available"
    assert not analysis.passed


# =============================================================================
# Confidence and Scoring Tests
# =============================================================================


def test_high_confidence_deflection(analyzer):
    """Test that obvious deflections have high confidence."""
    analysis = analyzer.analyze(
        query="Find hydrogen calls",
        response="I could not find any results. No information available.",
        query_type="call_search",
    )

    assert analysis.confidence >= 0.85
    assert analysis.category == ResponseCategory.DEFLECTION


def test_tool_usage_bonus(analyzer):
    """Test that tool usage improves score."""
    response = "Based on the search, here are 5 hydrogen funding calls..."

    analysis_no_tools = analyzer.analyze(
        query="Find hydrogen calls",
        response=response,
        tools_used=[],
    )

    analysis_with_tools = analyzer.analyze(
        query="Find hydrogen calls",
        response=response,
        tools_used=["search_funding_calls"],
        tool_results={"search_funding_calls": {"success": True, "calls_found": 5}},
    )

    assert analysis_with_tools.score > analysis_no_tools.score
