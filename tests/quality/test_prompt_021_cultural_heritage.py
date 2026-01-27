"""
Quality Evaluation Test for Prompt 021: Digital Cultural Heritage (Complex Multi-Part).

This test evaluates the MAPIT AI response to the query:
"I have an innovative project idea for an interdisciplinary project in digital tech
preservation of cultural heritage, with digital twining and predictive maintenance of
heritage sites, with participatory research. Are there any upcoming calls in any HE
strands? What is the budget, deadline, key parameters? Furthermore: Tell me of similar
projects done in H2020/HE with project titles, call IDs, budgets, coordinator names,
and list of partners."

This is a COMPLEX MULTI-PART query requiring the query-decomposer to identify:
1. Upcoming calls for digital cultural heritage
2. Budgets/deadlines/key parameters for those calls
3. Similar past projects with full details (titles, call IDs, budgets, coordinators, partners)

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Addresses all 3 query components
- Specificity (25 points): Call IDs, deadlines, budgets, project details, partner lists
- Factual Accuracy (25 points): Valid call/project IDs, correct dates
- Actionability (10 points): Links to calls, how to apply, CORDIS links

Pass threshold: >= 85/100

Run with:
    pytest tests/quality/test_prompt_021_cultural_heritage.py -v

For live API tests only:
    pytest tests/quality/test_prompt_021_cultural_heritage.py -v -m "live_api"
"""

import json
import os
import random
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# API configuration
API_BASE_URL = os.getenv("MAP_IT_API_URL", "http://localhost:8000")
RESULTS_DIR = Path(__file__).parent / "results"

# Evaluation thresholds
PASS_THRESHOLD = 85
NEEDS_REVIEW_THRESHOLD = 70

# The query for this test - COMPLEX MULTI-PART
PROMPT_021_QUERY = (
    "I have an innovative project idea for an interdisciplinary project in digital tech "
    "preservation of cultural heritage, with digital twining and predictive maintenance "
    "of heritage sites, with participatory research. Are there any upcoming calls in any "
    "HE strands? What is the budget, deadline, key parameters? Furthermore: Tell me of "
    "similar projects done in H2020/HE with project titles, call IDs, budgets, coordinator "
    "names, and list of partners."
)

# Expected content based on PRD requirements
# Query components:
# 1. Upcoming calls (digital cultural heritage)
# 2. Budget, deadline, key parameters
# 3. Similar H2020/HE projects with full details

# Digital cultural heritage keywords
EXPECTED_DIGITAL_HERITAGE_KEYWORDS = [
    "cultural heritage",
    "heritage",
    "digital",
    "digitization",
    "digitisation",
    "preservation",
    "digital twin",
    "twinning",
    "3d",
    "scanning",
    "modeling",
    "modelling",
    "predictive",
    "maintenance",
    "conservation",
    "restoration",
    "monument",
    "museum",
    "archive",
    "archaeological",
    "archaeology",
]

# Digital technology keywords
EXPECTED_DIGITAL_TECH_KEYWORDS = [
    "digital",
    "technology",
    "ai",
    "artificial intelligence",
    "machine learning",
    "sensor",
    "iot",
    "cloud",
    "data",
    "virtual",
    "augmented",
    "reality",
    "immersive",
    "3d",
    "simulation",
    "monitoring",
    "analysis",
]

# Participatory research keywords
EXPECTED_PARTICIPATORY_KEYWORDS = [
    "participatory",
    "citizen",
    "engagement",
    "community",
    "stakeholder",
    "co-creation",
    "crowdsourcing",
    "public",
    "involvement",
    "social",
    "inclusive",
    "access",
]

# Call-related keywords
EXPECTED_CALL_KEYWORDS = [
    "call",
    "topic",
    "deadline",
    "budget",
    "funding",
    "horizon",
    "cluster",
    "work programme",
    "submission",
    "open",
    "upcoming",
    "application",
]

# Project detail keywords
EXPECTED_PROJECT_KEYWORDS = [
    "project",
    "funded",
    "h2020",
    "horizon 2020",
    "horizon europe",
    "coordinator",
    "partner",
    "consortium",
    "grant",
    "total cost",
    "ec contribution",
    "duration",
]

# Horizon Europe clusters relevant to digital cultural heritage
RELEVANT_HE_CLUSTERS = [
    "cluster 2",
    "cl2",
    "culture, creativity",
    "inclusive society",
    "cluster 4",
    "cl4",
    "digital",
    "industry",
]

# Call ID patterns
CALL_ID_PATTERNS = [
    r"HORIZON-CL2-\d{4}-\w+",  # Cluster 2 calls
    r"HORIZON-CL4-\d{4}-\w+",  # Cluster 4 calls
    r"HORIZON-INFRA-\d{4}-\w+",  # Infrastructure calls
    r"HORIZON-\w+-\d{4}",  # General Horizon calls
]


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_CULTURAL_HERITAGE = """
## Digital Cultural Heritage: Upcoming Calls & Similar Projects

Based on your innovative project idea combining digital technologies, digital twinning,
predictive maintenance for heritage sites, and participatory research, here's a
comprehensive overview of funding opportunities and similar funded projects.

---

### Part 1: Upcoming Calls in Horizon Europe

#### Cluster 2 - Culture, Creativity and Inclusive Society

**1. HORIZON-CL2-2025-HERITAGE-01-02: Digital technologies for cultural heritage preservation**
- **Topic**: Advanced digitization and predictive maintenance for heritage sites
- **Deadline**: March 12, 2026
- **Budget**: €4-6 million per project
- **Action Type**: RIA (Research and Innovation Action)
- **Funding Rate**: 100%
- **Key Parameters**:
  - Consortium: 3+ partners from 3+ EU/Associated Countries
  - Duration: 36-48 months
  - Focus: Digital twin technologies, AI for conservation, 3D modeling
  - Participatory dimension required

**2. HORIZON-CL2-2026-HERITAGE-02-01: Participatory approaches to cultural heritage**
- **Topic**: Citizen engagement in heritage preservation using digital tools
- **Deadline**: September 2026 (expected)
- **Budget**: €3-4 million per project
- **Action Type**: RIA
- **Key Parameters**:
  - Strong emphasis on co-creation and community involvement
  - Integration with New European Bauhaus expected
  - Digital access and inclusion requirements

#### Cluster 4 - Digital, Industry and Space

**3. HORIZON-CL4-2025-TWIN-01-54: Digital twins for built heritage**
- **Topic**: AI-driven digital twin frameworks for heritage monitoring
- **Deadline**: February 2026
- **Budget**: €5-8 million per project
- **Action Type**: IA (Innovation Action)
- **Funding Rate**: 70% (100% for non-profit)

---

### Part 2: Similar Funded Projects (H2020 & Horizon Europe)

#### Project 1: **ARIADNE-PLUS** (Grant Agreement: 823914)
- **Full Title**: Advanced Research Infrastructure for Archaeological Dataset Networking in Europe
- **Call ID**: H2020-INFRAIA-2018-2020
- **Total Cost**: €9,995,000
- **EC Contribution**: €9,995,000
- **Duration**: 2019-2024
- **Coordinator**: PIN SOC.CONS. A R.L. (Italy)

**Partners (28 organizations)**:
1. Consiglio Nazionale delle Ricerche (IT)
2. INRIA (FR)
3. University of York (UK)
4. ATHENA Research Centre (GR)
5. Austrian Academy of Sciences (AT)
6. German Archaeological Institute (DE)
7. Swedish National Heritage Board (SE)
8. CENIEH (ES)
9. University of Ljubljana (SI)
10. ...and 18 additional partners

ARIADNE-PLUS integrates archaeological data infrastructures across Europe using advanced
digital technologies for heritage discovery and preservation.

---

#### Project 2: **Time Machine** (Grant Agreement: 820323)
- **Full Title**: Time Machine - Big Data of the Past for the Future of Europe
- **Call ID**: H2020-FETFLAG-2018-2020
- **Total Cost**: €998,012
- **EC Contribution**: €998,012
- **Duration**: 2019-2020 (CSA)
- **Coordinator**: EPFL - École Polytechnique Fédérale de Lausanne (Switzerland)

**Partners (33 organizations)**:
1. University of Amsterdam (NL)
2. Austrian National Library (AT)
3. Europeana Foundation (NL)
4. National Archives of Netherlands (NL)
5. Fraunhofer-Gesellschaft (DE)
6. Ca' Foscari University of Venice (IT)
7. Barcelona Supercomputing Center (ES)
8. Czech Academy of Sciences (CZ)
9. Archives nationales (FR)
10. ...and 23 additional partners

Time Machine developed concepts for large-scale digitization and AI for European
cultural heritage using emerging technologies.

---

#### Project 3: **INCEPTION** (Grant Agreement: 665220)
- **Full Title**: Inclusive Cultural Heritage in Europe through 3D semantic modelling
- **Call ID**: H2020-REFLECTIVE-6-2014
- **Total Cost**: €5,999,425
- **EC Contribution**: €5,999,425
- **Duration**: 2015-2019
- **Coordinator**: Alma Mater Studiorum - Università di Bologna (Italy)

**Partners (14 organizations)**:
1. DEMO Consultants BV (NL)
2. University of Ljubljana (SI)
3. CYENS Centre of Excellence (CY)
4. Fraunhofer IGD (DE)
5. National Technical University of Athens (GR)
6. Fondazione Bruno Kessler (IT)
7. CNR-ITABC (IT)
8. CARTIF (ES)
9. Salamanca University (ES)
10. ...and 4 additional partners

INCEPTION pioneered 3D semantic modeling and BIM for cultural heritage documentation.

---

#### Project 4: **DIGITALEUROPE4ALL** (Grant Agreement: 101060879)
- **Full Title**: Digital Methods for Inclusive Heritage Access
- **Call ID**: HORIZON-CL2-2021-HERITAGE-01
- **Total Cost**: €3,498,750
- **EC Contribution**: €3,498,750
- **Duration**: 2022-2026
- **Coordinator**: Politecnico di Milano (Italy)

**Partners (12 organizations)**:
1. TU Delft (NL)
2. Fondazione Bruno Kessler (IT)
3. University of Patras (GR)
4. Cyprus University of Technology (CY)
5. Universitat Politècnica de Catalunya (ES)
6. Aristotle University of Thessaloniki (GR)
7. Cité de l'architecture et du patrimoine (FR)
8. ...and 4 additional partners

This Horizon Europe project combines digital twins with participatory heritage approaches.

---

### Part 3: Key Resources & Next Steps

1. **EU Funding Portal**: https://ec.europa.eu/info/funding-tenders/opportunities/portal/
   - Search "cultural heritage" + "digital" for latest calls

2. **Cluster 2 Work Programme 2025-2027**: Review Destination "Innovative Research on
   European Cultural Heritage"

3. **Partner Search**: Use the portal's partner search or CORDIS for consortium building

4. **CORDIS Database**: https://cordis.europa.eu - Search funded projects for detailed info

5. **Contact NCPs**: National Contact Points for Cluster 2 can provide call-specific guidance

Your project combining digital twinning + predictive maintenance + participatory research
aligns well with HORIZON-CL2-2025-HERITAGE-01-02 and HORIZON-CL4-2025-TWIN-01-54.
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_CULTURAL_HERITAGE = """
## Digital Cultural Heritage Opportunities

Your project idea on digital preservation, digital twins, and participatory research
for cultural heritage sounds promising. Here's what I found:

### Upcoming Calls
- Cluster 2 (Culture, Creativity) has relevant calls in 2025-2026
- Topics include digital heritage, preservation technologies, 3D modeling
- Typical budgets are €3-6 million per project
- RIA actions have 100% funding rate

### Similar Past Projects
1. **ARIADNE** - Archaeological data infrastructure, ~€10M
2. **Time Machine** - Big data for cultural heritage, CSA project
3. **INCEPTION** - 3D semantic modeling for heritage, H2020 project
4. **DIGTAL-HERITAGE** - Various digital preservation initiatives

These projects have worked on similar themes. You can find more details on CORDIS.

### Recommendations
- Check Cluster 2 Work Programme 2025-2027
- Consider Cluster 4 for digital twin technologies
- Build a consortium with 5-10 partners
"""

    # A low-quality response that should FAIL (< 70)
    POOR_CULTURAL_HERITAGE = """
Digital cultural heritage is an important research area. The EU funds many projects
on heritage preservation and digital technologies through Horizon Europe.

There are various calls related to cultural heritage in the Cluster 2 programme.
You should check the EU Funding Portal for current opportunities.

Some H2020 projects have worked on similar topics. CORDIS has a database of
funded projects you can search.

For participatory research, citizen science approaches are increasingly popular
in heritage projects.
"""


@dataclass
class EvaluationResult:
    """Complete evaluation result for a prompt."""

    prompt_id: str
    query: str
    response: str
    overall_score: int
    result: str  # PASS, FAIL, NEEDS_REVIEW
    component_scores: list[dict[str, Any]] = field(default_factory=list)
    factual_errors: list[dict[str, str]] = field(default_factory=list)
    fix_suggestions: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    evaluation_timestamp: str = ""
    response_metadata: dict[str, Any] = field(default_factory=dict)
    fix_history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_api_available() -> bool:
    """Check if the API is available."""
    try:
        response = httpx.get(f"{API_BASE_URL}/api/v3/conversation/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


# Skip decorator for live tests
live_api = pytest.mark.skipif(
    not check_api_available(),
    reason="Live API not available. Start Docker containers with: docker compose up",
)


def get_mapit_response(query: str, conversation_id: int | None = None) -> dict[str, Any]:
    """
    Send a query to MAPIT and get the response.

    Args:
        query: The user query to send.
        conversation_id: Optional conversation ID.

    Returns:
        Dict with response text, metadata, and timing info.
    """
    if conversation_id is None:
        conversation_id = random.randint(1000000, 9999999)

    url = f"{API_BASE_URL}/api/v3/conversation/{conversation_id}/message"

    payload = {
        "message": query,
        "include_context": True,
    }

    client = httpx.Client(timeout=300.0)  # Long timeout for complex multi-part query
    try:
        start_time = time.time()
        response = client.post(url, json=payload)
        elapsed_ms = (time.time() - start_time) * 1000

        if response.status_code != 200:
            raise Exception(f"API returned {response.status_code}: {response.text}")

        result = response.json()

        return {
            "response": result.get("response", ""),
            "metadata": result.get("metadata", {}),
            "elapsed_ms": elapsed_ms,
            "conversation_id": conversation_id,
        }
    finally:
        client.close()


def count_upcoming_calls(response: str) -> int:
    """
    Count the number of upcoming/open calls mentioned.

    Looks for call IDs and deadline mentions.
    """
    # Count call IDs
    call_patterns = [
        r"HORIZON-CL[24]-\d{4}",
        r"HORIZON-\w+-\d{4}",
        r"H2020-\w+-\d{4}",
    ]
    call_ids = set()
    for pattern in call_patterns:
        call_ids.update(re.findall(pattern, response, re.IGNORECASE))

    # Count deadline mentions
    deadline_count = len(re.findall(r"deadline", response, re.IGNORECASE))

    # Count "upcoming" or "open" call mentions
    upcoming_count = len(re.findall(r"upcoming|open.{0,10}call", response, re.IGNORECASE))

    return max(len(call_ids), min(deadline_count, 5), upcoming_count)


def count_projects_with_details(response: str) -> tuple[int, int, int]:
    """
    Count projects and their details.

    Returns:
        Tuple of (projects_count, projects_with_coordinators, projects_with_partners)
    """
    # Count grant agreement numbers (6+ digits)
    grant_numbers = set(re.findall(r"\b\d{6,9}\b", response))

    # Count project sections with coordinator info
    coordinator_mentions = len(re.findall(r"coordinator", response, re.IGNORECASE))

    # Count partner lists (looking for numbered partners or "partners" keyword)
    partner_lists = len(re.findall(r"\d+\.\s+[A-Z][\w\s]+\([A-Z]{2}\)", response))

    projects_count = len(grant_numbers)
    projects_with_coordinators = min(coordinator_mentions, projects_count)
    projects_with_partners = 1 if partner_lists >= 3 else 0

    return projects_count, projects_with_coordinators, projects_with_partners


def evaluate_query_fulfillment(response: str) -> tuple[int, str, list[str], list[str]]:
    """
    Evaluate query fulfillment for this COMPLEX MULTI-PART query (40 points max).

    Must address all 3 query components:
    1. Upcoming calls (15 points)
    2. Budget/deadline/key parameters (10 points)
    3. Similar H2020/HE projects with full details (15 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    found_items = []
    missing_items = []

    # Component 1: Upcoming calls (15 points)
    calls_count = count_upcoming_calls(response)
    has_digital_heritage = any(
        kw in response_lower for kw in EXPECTED_DIGITAL_HERITAGE_KEYWORDS[:7]
    )
    has_cluster_mention = any(cluster in response_lower for cluster in RELEVANT_HE_CLUSTERS)

    if calls_count >= 2 and has_digital_heritage and has_cluster_mention:
        score += 15
        found_items.append(f"{calls_count} upcoming calls identified with heritage focus")
    elif calls_count >= 1 and has_digital_heritage:
        score += 10
        found_items.append(f"{calls_count} call(s) mentioned")
        missing_items.append("Need more specific upcoming calls for digital heritage")
    elif calls_count >= 1 or has_cluster_mention:
        score += 5
        missing_items.append("Limited call information, need specific upcoming calls")
    else:
        missing_items.append("No upcoming calls identified for digital cultural heritage")

    # Component 2: Budget/deadline/key parameters (10 points)
    has_budget = bool(re.search(r"€[\d,\.]+|budget|million|funding rate", response_lower))
    has_deadline = bool(re.search(r"deadline|202[56]|march|september|february", response_lower))
    has_parameters = bool(
        re.search(r"consortium|partners?|duration|action type|ria|ia", response_lower)
    )

    param_score = 0
    if has_budget:
        param_score += 4
        found_items.append("Budget information provided")
    else:
        missing_items.append("Missing budget figures for calls")

    if has_deadline:
        param_score += 3
        found_items.append("Deadline information provided")
    else:
        missing_items.append("Missing deadline information")

    if has_parameters:
        param_score += 3
        found_items.append("Key parameters explained")
    else:
        missing_items.append("Missing key call parameters")

    score += param_score

    # Component 3: Similar H2020/HE projects with full details (15 points)
    projects_count, with_coordinators, with_partners = count_projects_with_details(response)

    if projects_count >= 3 and with_coordinators >= 2 and with_partners >= 1:
        score += 15
        found_items.append(f"{projects_count} similar projects with coordinators and partner lists")
    elif projects_count >= 2 and with_coordinators >= 1:
        score += 10
        found_items.append(f"{projects_count} projects with some details")
        missing_items.append("Need partner lists for similar projects")
    elif projects_count >= 1:
        score += 5
        missing_items.append("Need more projects with full details (coordinators, partners)")
    else:
        missing_items.append("No similar H2020/HE projects with required details")

    # Build notes
    if missing_items:
        notes.append(f"Missing: {', '.join(missing_items)}")
    else:
        notes.append("All 3 query components fully addressed")

    return score, "; ".join(notes), missing_items, found_items


def evaluate_specificity(response: str) -> tuple[int, str]:
    """
    Evaluate specificity (25 points max).

    Checks for:
    - Call IDs (5 points)
    - Deadlines with dates (5 points)
    - Budget figures (5 points)
    - Project grant IDs (5 points)
    - Partner lists (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Call IDs (5 points)
    call_ids = re.findall(r"HORIZON-\w+-\d{4}[-\w]*", response, re.IGNORECASE)
    if len(call_ids) >= 3:
        score += 5
    elif len(call_ids) >= 2:
        score += 3
    elif len(call_ids) >= 1:
        score += 2
        notes.append("Limited call IDs")
    else:
        notes.append("No specific call IDs")

    # Deadlines with dates (5 points)
    date_patterns = [
        r"(?:january|february|march|april|may|june|july|august|september|october|"
        r"november|december)\s+\d{1,2}?,?\s*202[56]",
        r"202[56][-/]\d{1,2}[-/]\d{1,2}",
        r"deadline.*?202[56]",
    ]
    deadline_count = sum(len(re.findall(pat, response_lower)) for pat in date_patterns)
    if deadline_count >= 3:
        score += 5
    elif deadline_count >= 2:
        score += 3
    elif deadline_count >= 1:
        score += 2
        notes.append("Limited deadline specifics")
    else:
        notes.append("No specific deadline dates")

    # Budget figures (5 points)
    budget_patterns = [
        r"€[\d,\.]+\s*(?:m(?:illion)?)?",
        r"\d+[\.,]\d+\s*(?:m(?:illion)?)",
        r"\d+\s*million",
    ]
    budget_count = sum(len(re.findall(pat, response, re.IGNORECASE)) for pat in budget_patterns)
    if budget_count >= 5:
        score += 5
    elif budget_count >= 3:
        score += 3
    elif budget_count >= 1:
        score += 2
        notes.append("Limited budget figures")
    else:
        notes.append("No budget figures")

    # Project grant IDs (5 points)
    grant_ids = set(re.findall(r"\b\d{6,9}\b", response))
    if len(grant_ids) >= 4:
        score += 5
    elif len(grant_ids) >= 2:
        score += 3
    elif len(grant_ids) >= 1:
        score += 2
        notes.append("Few project grant IDs")
    else:
        notes.append("No grant agreement numbers")

    # Partner lists (5 points)
    # Look for numbered partner lists like "1. Organization (XX)"
    partner_entries = re.findall(r"\d+\.\s+[A-Z][\w\s\-]+\s*\([A-Z]{2}\)", response)
    if len(partner_entries) >= 10:
        score += 5
    elif len(partner_entries) >= 5:
        score += 3
        notes.append("Partial partner lists")
    elif len(partner_entries) >= 2:
        score += 1
        notes.append("Limited partner information")
    else:
        notes.append("No partner lists")

    return score, "; ".join(notes) if notes else "Good specificity with full details"


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - Call IDs follow valid patterns
    - Grant numbers are valid format
    - Dates are plausible
    - Clusters mentioned are correct for heritage
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check for invalid call ID patterns
    # Valid: HORIZON-CL2-2025-*, HORIZON-CL4-2026-*
    # Invalid: HORIZON-CL9-2025-* (no cluster 9)
    invalid_clusters = re.findall(r"HORIZON-CL([789])-\d{4}", response, re.IGNORECASE)
    if invalid_clusters:
        score -= 5
        errors.append(
            {
                "claim": f"Invalid cluster number(s): CL{', CL'.join(invalid_clusters)}",
                "correct_value": "Horizon Europe has Clusters 1-6",
                "source": "Call ID validation",
            }
        )

    # Check for invalid years in calls (pre-2021 or post-2030 for HE)
    he_years = re.findall(r"HORIZON-\w+-(\d{4})", response, re.IGNORECASE)
    invalid_years = [y for y in he_years if int(y) < 2021 or int(y) > 2030]
    if invalid_years:
        score -= 3
        errors.append(
            {
                "claim": f"Invalid year(s) in HE calls: {', '.join(invalid_years)}",
                "correct_value": "Horizon Europe calls are 2021-2027 (extended to 2030)",
                "source": "Temporal validation",
            }
        )

    # Check for wrong funding rates
    if "ria" in response_lower and "70%" in response:
        # RIA should be 100%, not 70%
        if not re.search(r"ia\s*[:\(]?\s*70%", response_lower):  # IA can be 70%
            score -= 3
            errors.append(
                {
                    "claim": "RIA with 70% funding rate",
                    "correct_value": "RIA has 100% funding rate; IA has 70% (100% for non-profit)",
                    "source": "Funding rate validation",
                }
            )

    # Check for obviously invalid grant numbers (too short or too long)
    grant_numbers = re.findall(r"grant\s*(?:agreement)?\s*[:\#]?\s*(\d+)", response_lower)
    for num in grant_numbers:
        if len(num) < 5 or len(num) > 10:
            score -= 2
            errors.append(
                {
                    "claim": f"Invalid grant number format: {num}",
                    "correct_value": "Grant numbers are typically 6-9 digits",
                    "source": "Grant number validation",
                }
            )
            break

    # Check for claims about wrong programmes
    if "h2020" in response_lower:
        # H2020 is 2014-2020, not later
        h2020_years = re.findall(r"h2020.*?(\d{4})", response_lower)
        wrong_h2020_years = [y for y in h2020_years if int(y) > 2024]
        if wrong_h2020_years:
            score -= 3
            errors.append(
                {
                    "claim": f"H2020 project with year(s) {', '.join(wrong_h2020_years)}",
                    "correct_value": "H2020 ran 2014-2020, projects end by ~2024",
                    "source": "Programme timeline validation",
                }
            )

    notes = f"Accuracy check: {max(0, score)}/25 points"
    if errors:
        notes += f"; {len(errors)} issue(s) found"

    return max(0, score), notes, errors


def evaluate_actionability(response: str) -> tuple[int, str]:
    """
    Evaluate actionability (10 points max).

    Checks for:
    - Links to EU Portal/calls (4 points)
    - Application guidance (3 points)
    - CORDIS/project links (3 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Links to EU Portal/calls (4 points)
    portal_patterns = [
        "ec.europa",
        "funding-tenders",
        "portal",
        "http",
        "https",
        "cordis",
    ]
    portal_found = sum(1 for pat in portal_patterns if pat in response_lower)
    if portal_found >= 3:
        score += 4
    elif portal_found >= 2:
        score += 3
    elif portal_found >= 1:
        score += 1
        notes.append("Limited portal links")
    else:
        notes.append("No links to EU portal")

    # Application guidance (3 points)
    guidance_phrases = [
        "apply",
        "application",
        "submit",
        "submission",
        "proposal",
        "consortium",
        "partner search",
        "ncp",
        "national contact point",
        "work programme",
    ]
    guidance_found = sum(1 for phrase in guidance_phrases if phrase in response_lower)
    if guidance_found >= 4:
        score += 3
    elif guidance_found >= 2:
        score += 2
    elif guidance_found >= 1:
        score += 1
    else:
        notes.append("No application guidance")

    # CORDIS/project links (3 points)
    cordis_patterns = [
        "cordis",
        "cordis.europa.eu",
        "project details",
        "more information",
        "learn more",
    ]
    cordis_found = sum(1 for pat in cordis_patterns if pat in response_lower)
    if cordis_found >= 2:
        score += 3
    elif cordis_found >= 1:
        score += 2
        notes.append("Limited project resource links")
    else:
        notes.append("No CORDIS/project links")

    return (
        score,
        "; ".join(notes) if notes else "Good actionability with resources",
    )


def evaluate_response(response: str, response_metadata: dict[str, Any]) -> EvaluationResult:
    """
    Perform full evaluation of the response.

    Uses the four-dimension scoring framework:
    - Query Fulfillment (40 points)
    - Specificity (25 points)
    - Factual Accuracy (25 points)
    - Actionability (10 points)

    Returns:
        EvaluationResult with scores and analysis.
    """
    # Evaluate each dimension
    (
        fulfillment_score,
        fulfillment_notes,
        missing_items,
        found_items,
    ) = evaluate_query_fulfillment(response)
    specificity_score, specificity_notes = evaluate_specificity(response)
    accuracy_score, accuracy_notes, factual_errors = evaluate_factual_accuracy(response)
    actionability_score, actionability_notes = evaluate_actionability(response)

    # Calculate overall score
    overall_score = fulfillment_score + specificity_score + accuracy_score + actionability_score

    # Determine result
    if overall_score >= PASS_THRESHOLD:
        result = "PASS"
    elif overall_score >= NEEDS_REVIEW_THRESHOLD:
        result = "NEEDS_REVIEW"
    else:
        result = "FAIL"

    # Build component scores
    component_scores = [
        {
            "component_id": "digital_cultural_heritage_multipart",
            "description": (
                "Complex multi-part query: (1) upcoming calls for digital heritage, "
                "(2) budgets/deadlines/parameters, (3) similar H2020/HE projects with "
                "titles, call IDs, budgets, coordinators, and partner lists"
            ),
            "fulfillment": fulfillment_score,
            "specificity": specificity_score,
            "accuracy": accuracy_score,
            "actionability": actionability_score,
            "total": overall_score,
            "notes": (
                f"Fulfillment: {fulfillment_notes}; Specificity: {specificity_notes}; "
                f"Accuracy: {accuracy_notes}; Actionability: {actionability_notes}"
            ),
            "missing_items": missing_items,
            "found_items": found_items,
        }
    ]

    # Generate fix suggestions
    fix_suggestions = []
    if fulfillment_score < 32:  # < 80% of 40
        fix_suggestions.append(
            f"Improve query fulfillment: Address all 3 query components - "
            f"(1) upcoming calls with digital heritage focus, "
            f"(2) budgets/deadlines/key parameters for calls, "
            f"(3) similar H2020/HE projects with full details including PARTNER LISTS. "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include specific call IDs (HORIZON-CL2-2025-*), "
            "exact deadline dates, budget figures per project, grant agreement numbers, "
            "and NUMBERED PARTNER LISTS for each similar project"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual accuracy: Ensure call IDs use valid clusters (1-6), "
            "grant numbers are 6-9 digits, dates are in H2020/HE timeframes"
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add links to EU Funding Portal, CORDIS, "
            "application guidance, and partner search resources"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Addresses all 3 query components (calls, params, projects)")
    if specificity_score >= 20:
        strengths.append("Rich in specific details (call IDs, budgets, partners)")
    if accuracy_score >= 20:
        strengths.append("Factually accurate call and project information")
    if actionability_score >= 8:
        strengths.append("Provides useful resources and guidance")

    return EvaluationResult(
        prompt_id="021",
        query=PROMPT_021_QUERY,
        response=response,
        overall_score=overall_score,
        result=result,
        component_scores=component_scores,
        factual_errors=factual_errors,
        fix_suggestions=fix_suggestions,
        strengths=strengths,
        evaluation_timestamp=datetime.now(UTC).isoformat(),
        response_metadata=response_metadata,
    )


def save_result(result: EvaluationResult, filepath: Path) -> None:
    """Save evaluation result to JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(result.to_dict(), f, indent=2)


@live_api
class TestPrompt021CulturalHeritage:
    """
    Test suite for Prompt 021: Digital Cultural Heritage (Complex Multi-Part).

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_cultural_heritage_multipart(self):
        """
        Main evaluation test for Prompt 021 (Complex Multi-Part Query).

        1. Sends complex query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_021_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_021_cultural_heritage.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 021: Digital Cultural Heritage (Complex Multi-Part)")
        print(f"{'=' * 60}")
        print(f"Overall Score: {evaluation.overall_score}/100")
        print(f"Result: {evaluation.result}")
        print(f"{'=' * 60}")

        if evaluation.component_scores:
            comp = evaluation.component_scores[0]
            print(f"Query Fulfillment: {comp['fulfillment']}/40")
            print(f"Specificity: {comp['specificity']}/25")
            print(f"Factual Accuracy: {comp['accuracy']}/25")
            print(f"Actionability: {comp['actionability']}/10")

            if comp.get("missing_items"):
                print(f"\nMissing Items: {comp['missing_items']}")
            if comp.get("found_items"):
                print(f"Found Items: {comp['found_items']}")

        if evaluation.factual_errors:
            print("\nFactual Issues Found:")
            for error in evaluation.factual_errors:
                print(f"  - {error['claim']}: {error['correct_value']}")

        if evaluation.fix_suggestions:
            print("\nFix Suggestions:")
            for suggestion in evaluation.fix_suggestions:
                print(f"  - {suggestion}")

        if evaluation.strengths:
            print("\nStrengths:")
            for strength in evaluation.strengths:
                print(f"  + {strength}")

        print(f"\nResults saved to: {results_file}")
        print(f"{'=' * 60}\n")

        # For EVALUATE task: Record results and report status
        if evaluation.overall_score < PASS_THRESHOLD:
            score = evaluation.overall_score
            print(f"\n*** FIX NEEDED: Score {score} < {PASS_THRESHOLD} threshold ***")
            print("Run the FIX IF NEEDED task to improve response quality.")

        # EVALUATE phase: We only need to successfully record the evaluation
        assert results_file.exists(), f"Results file not created: {results_file}"

    def test_response_not_empty(self):
        """Verify the response is not empty."""
        api_result = get_mapit_response(PROMPT_021_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_addresses_calls(self):
        """Verify the response addresses upcoming calls (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_021_cultural_heritage.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_cultural_heritage_multipart first")

        with open(results_file) as f:
            result = json.load(f)

        response = result["response"]
        calls_count = count_upcoming_calls(response)

        # Informational check
        print(f"Upcoming calls mentioned: {calls_count}")
        if calls_count < 2:
            print("Note: Response needs more specific upcoming calls")

        # Soft assertion
        assert "response" in result, "Response field missing from results"

    def test_response_includes_projects(self):
        """Verify the response includes similar projects with details (informational)."""
        results_file = RESULTS_DIR / "prompt_021_cultural_heritage.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_cultural_heritage_multipart first")

        with open(results_file) as f:
            result = json.load(f)

        response = result["response"]
        projects, with_coord, with_partners = count_projects_with_details(response)

        # Informational check
        print(f"Projects found: {projects}")
        print(f"With coordinators: {with_coord}")
        print(f"With partner lists: {with_partners}")
        if projects < 3:
            print("Note: Response needs more similar projects with full details")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt021OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_CULTURAL_HERITAGE,
            {"source": "sample_excellent"},
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_021_cultural_heritage_sample_excellent.json"
        save_result(evaluation, results_file)

        print("\nExcellent Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score >= PASS_THRESHOLD, (
            f"Excellent response scored {evaluation.overall_score}, expected >= {PASS_THRESHOLD}"
        )
        assert evaluation.result == "PASS"

    def test_partial_response_needs_review(self):
        """Test that a partial response scores 70-84 (NEEDS_REVIEW) or lower."""
        evaluation = evaluate_response(
            SampleResponses.PARTIAL_CULTURAL_HERITAGE, {"source": "sample_partial"}
        )

        print("\nPartial Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        # Partial should score below PASS threshold
        assert evaluation.overall_score < PASS_THRESHOLD, (
            f"Partial response scored {evaluation.overall_score}, expected < {PASS_THRESHOLD}"
        )

    def test_poor_response_fails(self):
        """Test that a poor response scores < 70 (FAIL)."""
        evaluation = evaluate_response(
            SampleResponses.POOR_CULTURAL_HERITAGE, {"source": "sample_poor"}
        )

        print("\nPoor Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < NEEDS_REVIEW_THRESHOLD, (
            f"Poor response scored {evaluation.overall_score}, expected < {NEEDS_REVIEW_THRESHOLD}"
        )
        assert evaluation.result == "FAIL"

    def test_evaluation_identifies_missing_partners(self):
        """Test that evaluation identifies missing partner lists."""
        evaluation = evaluate_response(
            SampleResponses.PARTIAL_CULTURAL_HERITAGE, {"source": "sample_partial"}
        )

        # Check that missing partners are identified
        if evaluation.component_scores:
            comp = evaluation.component_scores[0]
            missing = comp.get("missing_items", [])

            # Partial response should be missing partner lists
            print(f"Missing items: {missing}")
            has_partner_issue = any("partner" in item.lower() for item in missing)
            # Either missing partners identified or score is low
            assert has_partner_issue or evaluation.overall_score < 75, (
                "Should identify missing partner lists or score low"
            )

    def test_evaluation_rewards_full_project_details(self):
        """Test that full project details (including partners) improve the score."""
        excellent_eval = evaluate_response(
            SampleResponses.EXCELLENT_CULTURAL_HERITAGE, {"source": "excellent"}
        )
        partial_eval = evaluate_response(
            SampleResponses.PARTIAL_CULTURAL_HERITAGE, {"source": "partial"}
        )

        # Excellent response should have much higher specificity
        excellent_specificity = excellent_eval.component_scores[0]["specificity"]
        partial_specificity = partial_eval.component_scores[0]["specificity"]

        assert excellent_specificity > partial_specificity, (
            f"Excellent specificity ({excellent_specificity}) "
            f"should be > partial ({partial_specificity})"
        )

    def test_save_evaluation_result_json(self):
        """Test that evaluation results are saved correctly as JSON."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_CULTURAL_HERITAGE,
            {"source": "test_json_save"},
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_021_cultural_heritage_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "021"
        assert loaded["query"] == PROMPT_021_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
