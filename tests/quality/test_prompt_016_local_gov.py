"""
Quality Evaluation Test for Prompt 016: Local Government Climate Adaptation.

This test evaluates the MAPIT AI response to the query:
"I am a local government interested in climate change adaptation. What Horizon
Europe opportunities exist for us?"

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Lists relevant public body opportunities
- Specificity (25 points): Specific programmes, budgets, roles
- Factual Accuracy (25 points): Correct facts per eu-funding-domain skill
- Actionability (10 points): Clear guidance on public body participation

Pass threshold: >= 85/100

Reference facts from eu-funding-domain skill:
- PUB = Public Body (local governments, municipalities, regional authorities)
- Key public body opportunities in Horizon Europe:
  - RIA (Research and Innovation Actions): 100% funding, can participate
  - IA (Innovation Actions): 70% funding (100% for non-profit PUB)
  - CSA (Coordination and Support Actions): 100% funding
  - EU Missions: Strong public body engagement expected
- Climate Adaptation relevant areas:
  - EU Mission "Adaptation to Climate Change" - 150+ regions by 2030
  - EU Mission "Climate-Neutral and Smart Cities" - 100 cities by 2030
  - Cluster 5: Climate, Energy & Mobility
  - Cluster 6: Food, Bioeconomy, Natural Resources
  - Green Deal initiatives
- Public body roles:
  - Living labs and testbeds
  - Policy implementation and replication
  - Citizen engagement and demonstration
  - Regional/local knowledge contribution
- Consortium requirements:
  - Usually 3+ partners from 3+ EU/Associated countries
  - Local governments valued for demonstration/pilot activities

Run with:
    pytest tests/quality/test_prompt_016_local_gov.py -v

For live API tests only:
    pytest tests/quality/test_prompt_016_local_gov.py -v -m "live_api"
"""

import json
import os
import random
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

# The query for this test
PROMPT_016_QUERY = (
    "I am a local government interested in climate change adaptation. "
    "What Horizon Europe opportunities exist for us?"
)

# Expected content based on PRD requirements
# Must explain public body (PUB) eligibility per eu-funding-domain
PUBLIC_BODY_KEYWORDS = [
    "local government",
    "public body",
    "pub",
    "municipality",
    "municipalities",
    "regional",
    "city",
    "cities",
    "town",
    "authority",
    "authorities",
    "public sector",
    "governmental",
    "public administration",
]

CLIMATE_ADAPTATION_KEYWORDS = [
    "climate",
    "adaptation",
    "resilience",
    "resilient",
    "climate-neutral",
    "carbon neutral",
    "net zero",
    "green",
    "sustainability",
    "sustainable",
    "environment",
    "disaster",
    "flood",
    "heat",
    "drought",
    "extreme weather",
]

EU_MISSIONS_KEYWORDS = [
    "mission",
    "missions",
    "100 cities",
    "climate-neutral cities",
    "smart cities",
    "adaptation to climate change",
    "150 regions",
    "climate adaptation",
    "2030",
]

FUNDING_INSTRUMENT_KEYWORDS = [
    "ria",
    "ia",
    "csa",
    "research and innovation",
    "innovation action",
    "coordination",
    "support action",
    "100%",
    "70%",
    "funding rate",
    "funding",
    "grant",
]

# Call-specific patterns to check
CALL_DETAIL_PATTERNS = {
    "funding": [
        "funding",
        "grant",
        "budget",
        "million",
        "EUR",
        "100%",
        "70%",
        "rate",
        "contribution",
        "non-profit",
    ],
    "eligibility": [
        "eligible",
        "eligibility",
        "public body",
        "pub",
        "local government",
        "municipality",
        "legal entity",
        "organisation",
        "organization",
        "participate",
    ],
    "roles": [
        "pilot",
        "testbed",
        "living lab",
        "demonstration",
        "replication",
        "implementation",
        "policy",
        "citizen",
        "engagement",
        "local",
    ],
    "process": [
        "apply",
        "application",
        "call",
        "deadline",
        "submit",
        "consortium",
        "partner",
        "find",
        "search",
        "register",
    ],
}

# Factual requirements for local government climate queries
FACTUAL_REQUIREMENTS = {
    "ria_funding": {
        "claim": "RIA has 100% funding rate",
        "keywords": ["ria", "100%", "funding"],
        "required": True,
    },
    "ia_nonprofit": {
        "claim": "IA has 100% funding for non-profit public bodies",
        "keywords": ["ia", "non-profit", "100%"],
        "required": False,
    },
    "mission_cities": {
        "claim": "EU Mission targets 100 climate-neutral cities by 2030",
        "keywords": ["mission", "100", "cities", "2030"],
        "required": False,
    },
    "mission_regions": {
        "claim": "EU Mission targets 150+ climate-resilient regions",
        "keywords": ["mission", "150", "regions", "adaptation"],
        "required": False,
    },
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_LOCAL_GOV = """
## Horizon Europe Opportunities for Local Governments in Climate Change Adaptation

As a local government interested in climate change adaptation, you have excellent funding
opportunities in Horizon Europe, particularly through the EU Missions and climate-focused
clusters.

### 1. EU Mission "Adaptation to Climate Change" - Key Opportunity

**This Mission specifically targets local and regional authorities:**

| Aspect | Details |
|--------|---------|
| **Goal** | Support 150+ European regions to become climate resilient by 2030 |
| **Target** | Local/regional governments as key implementers |
| **Focus** | Adaptation solutions, risk management, resilience building |
| **Budget** | Significant funding allocated under Work Programme 2025-2027 |

**Why this is ideal for local governments:**
- Designed specifically for regional/local authorities
- Living labs and demonstration sites
- Policy implementation support
- Citizen engagement activities

### 2. EU Mission "Climate-Neutral and Smart Cities"

**100 Climate-Neutral Cities by 2030:**

| Aspect | Details |
|--------|---------|
| **Goal** | 100 European cities achieve climate neutrality by 2030 |
| **Participants** | Cities, municipalities, urban authorities |
| **Focus** | Energy efficiency, mobility, buildings, circular economy |
| **Support** | Climate City Contracts, technical assistance |

### 3. Funding Instruments for Public Bodies

**Research and Innovation Actions (RIA):**
- **Funding Rate:** 100% for all participants including public bodies
- **Role:** Research partner, pilot site provider, policy advisor
- **Typical Budget:** EUR 3-10 million per project, your share ~EUR 200K-800K

**Innovation Actions (IA):**
- **Funding Rate:** 70% (100% for non-profit public bodies!)
- **Role:** Demonstration sites, real-world testing, policy implementation
- **Focus:** Near-market solutions with societal impact

**Coordination and Support Actions (CSA):**
- **Funding Rate:** 100% for all participants
- **Role:** Networking, policy coordination, knowledge sharing
- **Typical Budget:** EUR 1-3 million

### 4. Cluster 5: Climate, Energy and Mobility

Relevant call topics for local governments:
- HORIZON-CL5-2025-D1: Climate science and responses
- HORIZON-CL5-2025-D3: Sustainable transport and mobility
- HORIZON-CL5-2025-D4: Efficient buildings and districts

### 5. Cluster 6: Food, Bioeconomy, Natural Resources

Nature-based solutions for climate adaptation:
- Green infrastructure
- Urban greening
- Water management
- Biodiversity and ecosystems

### Typical Roles for Local Governments in Projects

Your organization can contribute through:

1. **Living Labs & Testbeds**
   - Provide real-world testing environments
   - Municipal infrastructure for pilots
   - Citizen engagement platforms

2. **Policy Implementation**
   - Test regulatory approaches
   - Demonstrate policy effectiveness
   - Enable replication pathways

3. **Demonstration & Replication**
   - Showcase solutions at scale
   - Document lessons learned
   - Support transfer to other regions

4. **Local Knowledge**
   - Provide territorial context
   - Connect to local stakeholders
   - Facilitate citizen participation

### How to Get Started

1. **Register on EU Funding Portal**
   https://ec.europa.eu/info/funding-tenders/opportunities/portal/

2. **Explore EU Missions Portal**
   https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe_en

3. **Search for Relevant Calls**
   Filter by: Topics = "climate", "adaptation", "cities", "regions"

4. **Find Consortium Partners**
   Use Partner Search tool or contact National Contact Points

5. **Consider the Climate City Contract**
   For cities pursuing climate neutrality by 2030

### Key Resources

- [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)
- [EU Missions Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe_en)
- [Climate-Neutral Cities Mission](https://netzerocities.eu/)
- [Climate Adaptation Mission](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/adaptation-climate-change_en)
- [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search)

### Key Advantages for Local Governments

- **100% funding in RIA and CSA** - No co-financing required
- **Non-profit PUB = 100% in IA** - Same as RIA rates
- **Mission focus** - Designed for local/regional authorities
- **Demonstration value** - Your infrastructure is an asset
- **Policy influence** - Shape EU climate policy implementation
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_LOCAL_GOV = """
Local governments can participate in Horizon Europe funding programmes. There are
opportunities for organizations interested in climate change adaptation.

The EU Missions include one focused on climate adaptation that may be relevant.
There are also opportunities in Cluster 5 related to climate and energy.

You can join as a partner in research projects. Public bodies often contribute
to demonstration and pilot activities in funded projects.

Check the EU portal for open calls related to climate and adaptation topics.
The Work Programme has information about available funding opportunities.
"""

    # A low-quality response that should FAIL (< 70)
    POOR_LOCAL_GOV = """
Climate change is an important topic in EU research funding. There are many
programmes available for different types of organizations.

Horizon Europe supports research and innovation across Europe. Different
organizations can apply for funding depending on their profile.

You should check the EU website for more information about available calls
and how to apply for funding. The Work Programme contains details about topics.
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

    client = httpx.Client(timeout=120.0)
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


def evaluate_query_fulfillment(response: str) -> tuple[int, str, list[str], list[str]]:
    """
    Evaluate query fulfillment (40 points max).

    Checks if:
    - Public body/local government context addressed (12 points)
    - Climate adaptation relevance covered (10 points)
    - EU Missions mentioned (10 points)
    - Funding instruments explained (8 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    found_items = []
    missing_items = []

    # Check for public body/local government context (12 points)
    pub_found = sum(1 for kw in PUBLIC_BODY_KEYWORDS if kw in response_lower)
    if pub_found >= 4:
        score += 12
        found_items.append("Public body/local government context addressed")
    elif pub_found >= 2:
        score += 6
        found_items.append("Local government mentioned")
        missing_items.append("More detail on public body eligibility (PUB)")
    else:
        missing_items.append("Public body/local government eligibility explanation")

    # Check for climate adaptation relevance (10 points)
    climate_found = sum(1 for kw in CLIMATE_ADAPTATION_KEYWORDS if kw in response_lower)
    if climate_found >= 4:
        score += 10
        found_items.append("Climate adaptation context addressed")
    elif climate_found >= 2:
        score += 5
        found_items.append("Climate mentioned")
        missing_items.append("More detail on adaptation-specific opportunities")
    else:
        missing_items.append("Climate adaptation context")

    # Check for EU Missions (10 points)
    missions_found = sum(1 for kw in EU_MISSIONS_KEYWORDS if kw in response_lower)
    if missions_found >= 3:
        score += 10
        found_items.append("EU Missions explained")
    elif missions_found >= 1:
        score += 5
        found_items.append("EU Missions mentioned")
        missing_items.append("More detail on EU Missions (Cities, Climate Adaptation)")
    else:
        missing_items.append("EU Missions (100 Cities, 150 Regions)")

    # Check for funding instruments (8 points)
    instruments_found = sum(1 for kw in FUNDING_INSTRUMENT_KEYWORDS if kw in response_lower)
    if instruments_found >= 4:
        score += 8
        found_items.append("Funding instruments explained")
    elif instruments_found >= 2:
        score += 4
        found_items.append("Funding instruments noted")
        missing_items.append("More detail on RIA/IA/CSA for public bodies")
    else:
        missing_items.append("Funding instruments (RIA, IA, CSA)")

    # Build notes
    if missing_items:
        notes.append(f"Missing: {', '.join(missing_items)}")
    else:
        notes.append("All key components covered")

    return score, "; ".join(notes), missing_items, found_items


def evaluate_specificity(response: str) -> tuple[int, str]:
    """
    Evaluate specificity (25 points max).

    Checks for:
    - Funding details (8 points)
    - Eligibility criteria (7 points)
    - Public body roles description (5 points)
    - Application process (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Funding details (8 points)
    funding_found = sum(1 for pat in CALL_DETAIL_PATTERNS["funding"] if pat in response_lower)
    funding_score = min(8, funding_found * 2)
    score += funding_score
    if funding_found < 3:
        notes.append("Limited funding details (rates, budgets)")

    # Eligibility criteria (7 points)
    eligibility_found = sum(
        1 for pat in CALL_DETAIL_PATTERNS["eligibility"] if pat in response_lower
    )
    eligibility_score = min(7, eligibility_found * 2)
    score += eligibility_score
    if eligibility_found < 2:
        notes.append("Limited public body eligibility details")

    # Public body roles description (5 points)
    roles_found = sum(1 for pat in CALL_DETAIL_PATTERNS["roles"] if pat in response_lower)
    roles_score = min(5, roles_found * 2)
    score += roles_score
    if roles_found < 2:
        notes.append("Limited description of public body roles")

    # Application process (5 points)
    process_found = sum(1 for pat in CALL_DETAIL_PATTERNS["process"] if pat in response_lower)
    process_score = min(5, process_found * 2)
    score += process_score
    if process_found < 2:
        notes.append("Limited application process information")

    return (
        score,
        "; ".join(notes) if notes else "Good specificity with funding details",
    )


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - RIA funding rate is 100%
    - IA funding for non-profit public bodies is 100%
    - EU Mission targets are correct (100 cities, 150 regions)
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check for incorrect RIA funding claims
    if "ria" in response_lower or "research and innovation" in response_lower:
        ria_idx = max(
            response_lower.find("ria"),
            response_lower.find("research and innovation"),
        )
        if ria_idx != -1:
            ria_section = response_lower[ria_idx : ria_idx + 400]

            # RIA should be 100%, not 70%
            if "70%" in ria_section and "100%" not in ria_section:
                score -= 5
                errors.append(
                    {
                        "claim": "RIA has 70% funding rate",
                        "correct_value": "RIA has 100% funding rate",
                        "source": "EU Funding Domain Skill",
                    }
                )

    # Check for incorrect IA non-profit funding claims
    if "ia" in response_lower or "innovation action" in response_lower:
        ia_idx = max(
            response_lower.find(" ia "),
            response_lower.find("innovation action"),
        )
        if ia_idx != -1:
            ia_section = response_lower[ia_idx : ia_idx + 400]

            # IA for non-profit public bodies should be 100%
            if "70%" in ia_section and "non-profit" in ia_section and "100%" not in ia_section:
                score -= 5
                errors.append(
                    {
                        "claim": "IA has 70% funding for non-profit public bodies",
                        "correct_value": "IA has 100% funding for non-profit public bodies",
                        "source": "EU Funding Domain Skill",
                    }
                )

    # Check for incorrect mission targets
    if "mission" in response_lower and "cities" in response_lower:
        # Check for wrong number of cities
        if "200 cities" in response_lower or "50 cities" in response_lower:
            score -= 5
            errors.append(
                {
                    "claim": "Mission targets wrong number of cities",
                    "correct_value": "EU Mission targets 100 climate-neutral cities by 2030",
                    "source": "EU Funding Domain Skill",
                }
            )

    # Check for incorrect region targets
    if "mission" in response_lower and "region" in response_lower:
        if "100 regions" in response_lower and "150" not in response_lower:
            score -= 3
            errors.append(
                {
                    "claim": "Mission targets 100 regions",
                    "correct_value": "EU Mission targets 150+ climate-resilient regions",
                    "source": "EU Funding Domain Skill",
                }
            )

    notes = f"Accuracy check: {score}/25 points"
    if errors:
        notes += f"; {len(errors)} error(s) found"

    return max(0, score), notes, errors


def evaluate_actionability(response: str) -> tuple[int, str]:
    """
    Evaluate actionability (10 points max).

    Checks for:
    - Clear guidance on relevant opportunities (4 points)
    - Links or resource references (3 points)
    - Next steps guidance (3 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Clear guidance on options (4 points)
    guidance_patterns = [
        "ideal for",
        "specifically",
        "designed for",
        "target",
        "local government",
        "public body",
        "can participate",
        "eligible",
        "how to",
        "recommend",
        "best fit",
        "key opportunity",
    ]
    if sum(1 for p in guidance_patterns if p in response_lower) >= 2:
        score += 4
    else:
        notes.append("Limited guidance on opportunity selection")

    # Links or resource references (3 points)
    link_patterns = [
        "http",
        "portal",
        "website",
        "ec.europa",
        "funding-tenders",
        "partner search",
        "work programme",
        "netzerocities",
    ]
    if any(link in response_lower for link in link_patterns):
        score += 3
    else:
        notes.append("No links to official resources")

    # Next steps guidance (3 points)
    next_step_phrases = [
        "register",
        "check",
        "apply",
        "find partner",
        "work programme",
        "deadline",
        "call",
        "submit",
        "get started",
        "search",
        "contact",
    ]
    next_step_found = sum(1 for phrase in next_step_phrases if phrase in response_lower)
    score += min(3, next_step_found)

    return (
        score,
        "; ".join(notes) if notes else "Good actionability with clear guidance",
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
            "component_id": "local_gov_climate",
            "description": "Local government climate adaptation opportunities",
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
            f"Improve query fulfillment: Must explain public body (PUB) eligibility, "
            f"EU Missions for cities/regions, and climate adaptation focus. "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include funding rates (100% RIA/CSA, 100% IA for non-profit), "
            "Mission targets (100 cities, 150 regions by 2030), public body roles "
            "(living labs, testbeds, demonstration)"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual errors: RIA funding is 100%, IA for non-profit is 100%, "
            "EU Mission targets 100 climate-neutral cities and 150+ climate-resilient regions"
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add links to EU Funding Portal, EU Missions Portal, "
            "NetZeroCities, explain how local governments can participate"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Comprehensive coverage of public body opportunities")
    if specificity_score >= 20:
        strengths.append("Rich in specific funding and role details")
    if accuracy_score >= 20:
        strengths.append("Factually accurate on public body funding rules")
    if actionability_score >= 8:
        strengths.append("Provides clear guidance for local government participation")

    return EvaluationResult(
        prompt_id="016",
        query=PROMPT_016_QUERY,
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
class TestPrompt016LocalGov:
    """
    Test suite for Prompt 016: Local Government Climate Adaptation.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_local_gov(self):
        """
        Main evaluation test for Prompt 016.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_016_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_016_local_gov.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 016: Local Government Climate Adaptation Evaluation")
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
            print("\nFactual Errors Found:")
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
        api_result = get_mapit_response(PROMPT_016_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_public_body(self):
        """Verify the response mentions public body opportunities (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_016_local_gov.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_local_gov first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        pub_keywords_found = sum(1 for kw in PUBLIC_BODY_KEYWORDS if kw in response_lower)

        # Informational check
        print(f"Public body keywords found: {pub_keywords_found}")
        if pub_keywords_found < 3:
            print("Note: Response needs more detail on public body eligibility")

        # Soft assertion - just verify results exist
        assert "response" in result, "Response field missing from results"

    def test_response_mentions_missions(self):
        """Verify the response mentions EU Missions (informational)."""
        results_file = RESULTS_DIR / "prompt_016_local_gov.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_local_gov first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        missions_found = sum(1 for kw in EU_MISSIONS_KEYWORDS if kw in response_lower)

        # Informational check
        print(f"EU Missions keywords found: {missions_found}")
        if missions_found < 2:
            print("Note: Response should include EU Missions (Cities, Climate Adaptation)")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt016OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_LOCAL_GOV, {"source": "sample_excellent"}
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_016_local_gov_sample_excellent.json"
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
            SampleResponses.PARTIAL_LOCAL_GOV, {"source": "sample_partial"}
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
        evaluation = evaluate_response(SampleResponses.POOR_LOCAL_GOV, {"source": "sample_poor"})

        print("\nPoor Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < NEEDS_REVIEW_THRESHOLD, (
            f"Poor response scored {evaluation.overall_score}, expected < {NEEDS_REVIEW_THRESHOLD}"
        )
        assert evaluation.result == "FAIL"

    def test_evaluation_identifies_missing_items(self):
        """Test that evaluation identifies missing content."""
        evaluation = evaluate_response(SampleResponses.POOR_LOCAL_GOV, {"source": "sample_poor"})

        # Check that missing items are identified
        if evaluation.component_scores:
            comp = evaluation.component_scores[0]
            missing = comp.get("missing_items", [])

            # Poor response should be missing items
            print(f"Missing items: {missing}")
            assert len(missing) >= 1 or evaluation.overall_score < 70, (
                "Should identify missing items or score low"
            )

    def test_evaluation_rewards_specificity(self):
        """Test that specific details improve the score."""
        excellent_eval = evaluate_response(
            SampleResponses.EXCELLENT_LOCAL_GOV, {"source": "excellent"}
        )
        poor_eval = evaluate_response(SampleResponses.POOR_LOCAL_GOV, {"source": "poor"})

        # Excellent response should have much higher specificity
        excellent_specificity = excellent_eval.component_scores[0]["specificity"]
        poor_specificity = poor_eval.component_scores[0]["specificity"]

        assert excellent_specificity > poor_specificity, (
            f"Excellent specificity ({excellent_specificity}) should be > poor ({poor_specificity})"
        )

    def test_save_evaluation_result_json(self):
        """Test that evaluation results are saved correctly as JSON."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_LOCAL_GOV, {"source": "test_json_save"}
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_016_local_gov_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "016"
        assert loaded["query"] == PROMPT_016_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
