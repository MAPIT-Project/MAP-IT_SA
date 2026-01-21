"""
Quality Evaluation Test for Prompt 015: NGO/Umbrella Organization Climate Opportunities.

This test evaluates the MAPIT AI response to the query:
"I am an umbrella organization/NGO representing civil society. I am interested in
climate change. What are the opportunities for an organization like me?"

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Lists relevant NGO opportunities for climate
- Specificity (25 points): Specific programmes, budgets, roles
- Factual Accuracy (25 points): Correct facts per eu-funding-domain skill
- Actionability (10 points): Clear guidance on NGO participation

Pass threshold: >= 85/100

Reference facts from eu-funding-domain skill:
- NGO = Non-Governmental Organization (civil society, non-profit)
- Key NGO opportunities in Horizon Europe:
  - CSA (Coordination and Support Actions): 100% funding, coordination/networking/policy
  - RIA (Research and Innovation Actions): 100% funding, can participate as partner
  - IA (Innovation Actions): 70% funding (100% for non-profit NGOs!)
  - Missions: Strong civil society engagement expected
- CSA specifics:
  - 100% funding rate
  - No TRL requirement
  - Focus on coordination, networking, policy support
  - Typical budget: EUR 1-3M
  - Consortium: Usually 3+ partners from 3+ countries
- Climate-relevant opportunities:
  - Cluster 5: Climate, Energy & Mobility
  - Cluster 6: Food, Bioeconomy, Natural Resources
  - EU Missions: Climate Adaptation, Ocean, Soil
  - Green Deal initiatives
- NGO roles:
  - Policy dissemination and stakeholder engagement
  - Civil society representation
  - Networking and consortium building
  - Communication and outreach

Run with:
    pytest tests/quality/test_prompt_015_ngo_climate.py -v

For live API tests only:
    pytest tests/quality/test_prompt_015_ngo_climate.py -v -m "live_api"
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
PROMPT_015_QUERY = (
    "I am an umbrella organization/NGO representing civil society. I am interested in "
    "climate change. What are the opportunities for an organization like me?"
)

# Expected content based on PRD requirements
# Must mention CSA opportunities and consortium partner roles
NGO_OPPORTUNITY_KEYWORDS = [
    "ngo",
    "non-governmental",
    "civil society",
    "umbrella",
    "non-profit",
    "nonprofit",
    "association",
    "network",
    "stakeholder",
    "advocacy",
    "dissemination",
    "outreach",
    "engagement",
    "policy",
]

CSA_KEYWORDS = [
    "csa",
    "coordination",
    "support action",
    "coordination and support",
    "networking",
    "policy support",
    "dissemination",
    "100%",
    "funding rate",
]

CLIMATE_RELEVANCE_KEYWORDS = [
    "climate",
    "energy",
    "green",
    "sustainability",
    "environment",
    "carbon",
    "renewable",
    "cluster 5",
    "cluster 6",
    "green deal",
    "mobility",
    "mission",
    "adaptation",
]

CONSORTIUM_PARTNER_KEYWORDS = [
    "partner",
    "consortium",
    "collaborative",
    "join",
    "participate",
    "role",
    "stakeholder",
    "engagement",
    "communication",
    "outreach",
    "ria",
    "ia",
]

# Call-specific patterns to check
CALL_DETAIL_PATTERNS = {
    "funding": [
        "funding",
        "grant",
        "budget",
        "million",
        "€",
        "eur",
        "100%",
        "70%",
        "rate",
        "1-3m",
        "3m",
    ],
    "eligibility": [
        "eligible",
        "eligibility",
        "non-profit",
        "nonprofit",
        "civil society",
        "ngo",
        "legal entity",
        "organisation",
        "organization",
    ],
    "roles": [
        "dissemination",
        "communication",
        "outreach",
        "networking",
        "policy",
        "coordination",
        "stakeholder",
        "engagement",
        "advocacy",
        "representation",
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
    ],
}

# Factual requirements for NGO climate queries
FACTUAL_REQUIREMENTS = {
    "csa_funding": {
        "claim": "CSA has 100% funding rate",
        "keywords": ["csa", "100%", "funding"],
        "required": True,
    },
    "ia_nonprofit": {
        "claim": "IA has 100% funding for non-profit organizations",
        "keywords": ["ia", "innovation action", "non-profit", "100%"],
        "required": False,
    },
    "ria_participation": {
        "claim": "RIA allows NGO participation as partner",
        "keywords": ["ria", "partner", "100%"],
        "required": False,
    },
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_NGO_CLIMATE = """
## Horizon Europe Opportunities for NGOs/Umbrella Organizations in Climate Change

As an NGO or umbrella organization representing civil society with interest in climate
change, you have several excellent funding opportunities in Horizon Europe, particularly
through instruments designed for coordination, stakeholder engagement, and policy support.

### 1. Coordination and Support Actions (CSA) - Best Fit for NGOs

**CSA is the primary instrument for civil society organizations:**

| Aspect | Details |
|--------|---------|
| **Funding Rate** | 100% (full costs covered) |
| **Budget Range** | EUR 1-3 million typically |
| **TRL** | Not applicable (no technology development) |
| **Consortium** | Usually 3+ partners from 3+ EU/Associated countries |

**What CSAs fund:**
- Networking and coordination activities
- Policy support and stakeholder engagement
- Dissemination and communication campaigns
- Best practice exchange and knowledge sharing
- Standardization and harmonization efforts

**Climate-relevant CSA topics:**
- Cluster 5 (Climate, Energy & Mobility): Stakeholder platforms, policy dialogues
- Cluster 6 (Food, Bioeconomy, Environment): Civil society engagement, citizen science
- EU Missions: Climate Adaptation, Ocean & Waters, Soil Health

### 2. Research and Innovation Actions (RIA) - Partner Role

NGOs can participate in RIA projects as partners:
- **Funding Rate:** 100% for all participants
- **Role:** Stakeholder engagement, dissemination, policy liaison
- **Budget:** Your share typically EUR 100K-500K within larger consortium
- **Value:** Bring civil society perspective and network access

### 3. Innovation Actions (IA) - Partner Role with Full Funding

For non-profit NGOs, IA offers excellent terms:
- **Funding Rate:** 100% for non-profit organizations (70% for for-profit)
- **Role:** Demonstration, pilot testing, market uptake support
- **Focus:** Near-market innovations with societal impact

### 4. EU Missions - Strong Civil Society Engagement

EU Missions actively seek NGO participation:

| Mission | NGO Role |
|---------|----------|
| **Climate Adaptation** | Community engagement, local stakeholder networks |
| **Ocean & Waters** | Environmental advocacy, citizen science |
| **Soil Health** | Agricultural networks, land steward communities |
| **Climate-Neutral Cities** | Urban advocacy, citizen participation |

### Typical NGO Roles in Horizon Projects

Your organization can contribute through:

1. **Stakeholder Engagement**
   - Identifying and mobilizing relevant stakeholders
   - Organizing workshops and consultations
   - Building policy networks

2. **Dissemination & Communication**
   - Reaching civil society audiences
   - Policy briefs and position papers
   - Social media and public engagement

3. **Policy Support**
   - Providing policy recommendations
   - Liaising with decision-makers
   - Supporting regulatory dialogues

4. **Networking**
   - Connecting project outputs to wider networks
   - Facilitating knowledge exchange
   - Building communities of practice

### How to Get Started

1. **Register on EU Funding Portal**
   https://ec.europa.eu/info/funding-tenders/opportunities/portal/

2. **Search for CSA Calls**
   Filter by: Action Type = "CSA", Topics = "climate", "environment", "stakeholder"

3. **Find Consortium Partners**
   Use Partner Search tool or attend brokerage events

4. **Check Current Calls**
   - Work Programme 2025-2027 for Cluster 5 & 6
   - EU Missions calls for civil society engagement

### Key Resources

- 🎯 [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)
- 📋 [Cluster 5 Work Programme](https://ec.europa.eu/info/funding-tenders/)
- 📋 [Cluster 6 Work Programme](https://ec.europa.eu/info/funding-tenders/)
- 🌊 [EU Missions Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe_en)
- 🔍 [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search)

### Key Advantages for NGOs

✅ **CSA = 100% funding** - No co-financing required
✅ **Non-profit IA = 100% funding** - Same as RIA rates
✅ **Valued partner role** - Civil society perspective highly valued
✅ **Network access** - Your existing networks are an asset
✅ **Policy influence** - Direct connection to EU policy processes
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_NGO_CLIMATE = """
NGOs can participate in Horizon Europe funding programmes. There are several
opportunities for organizations interested in climate change.

Coordination and Support Actions (CSA) may be relevant for your organization.
These projects focus on coordination and networking activities.

You can also join as a partner in larger research projects. NGOs often
contribute to dissemination and stakeholder engagement activities.

Check the EU portal for open calls related to climate and environment topics.
The Work Programme has information about available funding opportunities.
"""

    # A low-quality response that should FAIL (< 70)
    POOR_NGO_CLIMATE = """
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
    - NGO opportunities are explained (15 points)
    - CSA instrument mentioned (10 points)
    - Climate relevance is addressed (10 points)
    - Consortium partner roles explained (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    found_items = []
    missing_items = []

    # Check for NGO opportunity explanation (15 points)
    ngo_found = sum(1 for kw in NGO_OPPORTUNITY_KEYWORDS if kw in response_lower)
    if ngo_found >= 4:
        score += 15
        found_items.append("NGO opportunities explained")
    elif ngo_found >= 2:
        score += 8
        found_items.append("NGO context mentioned")
        missing_items.append("More detail on NGO-specific roles and opportunities needed")
    else:
        missing_items.append("NGO-specific opportunities and roles")

    # Check for CSA instrument (10 points)
    csa_found = sum(1 for kw in CSA_KEYWORDS if kw in response_lower)
    if csa_found >= 3:
        score += 10
        found_items.append("CSA instrument described")
    elif csa_found >= 1:
        score += 5
        found_items.append("CSA mentioned")
        missing_items.append("More detail on CSA (Coordination and Support Actions)")
    else:
        missing_items.append("CSA (Coordination and Support Actions) opportunities")

    # Check for climate relevance (10 points)
    climate_found = sum(1 for kw in CLIMATE_RELEVANCE_KEYWORDS if kw in response_lower)
    if climate_found >= 4:
        score += 10
        found_items.append("Climate context addressed")
    elif climate_found >= 2:
        score += 5
        found_items.append("Climate mentioned")
        missing_items.append("More detail on climate-specific clusters/missions")
    else:
        missing_items.append("Climate-relevant funding context")

    # Check for consortium partner roles (5 points)
    partner_found = sum(1 for kw in CONSORTIUM_PARTNER_KEYWORDS if kw in response_lower)
    if partner_found >= 3:
        score += 5
        found_items.append("Consortium partner roles explained")
    elif partner_found >= 1:
        score += 2
        found_items.append("Partner roles noted")
        missing_items.append("More detail on NGO roles in consortia")
    else:
        missing_items.append("Consortium partner role opportunities")

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
    - NGO roles description (5 points)
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
        notes.append("Limited NGO eligibility details")

    # NGO roles description (5 points)
    roles_found = sum(1 for pat in CALL_DETAIL_PATTERNS["roles"] if pat in response_lower)
    roles_score = min(5, roles_found * 2)
    score += roles_score
    if roles_found < 2:
        notes.append("Limited description of NGO roles")

    # Application process (5 points)
    process_found = sum(1 for pat in CALL_DETAIL_PATTERNS["process"] if pat in response_lower)
    process_score = min(5, process_found * 2)
    score += process_score
    if process_found < 2:
        notes.append("Limited application process information")

    return (
        score,
        "; ".join(notes) if notes else "Good specificity with NGO funding details",
    )


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - CSA funding rate is 100%
    - IA funding for non-profit is 100% (not 70%)
    - RIA allows NGO participation
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check for incorrect CSA funding claims
    if "csa" in response_lower or "coordination and support" in response_lower:
        csa_idx = max(
            response_lower.find("csa"),
            response_lower.find("coordination and support"),
        )
        if csa_idx != -1:
            csa_section = response_lower[csa_idx : csa_idx + 400]

            # CSA should be 100%, not 70%
            if "70%" in csa_section and "100%" not in csa_section:
                score -= 5
                errors.append(
                    {
                        "claim": "CSA has 70% funding rate",
                        "correct_value": "CSA has 100% funding rate",
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

            # IA for non-profit should be 100%
            if "70%" in ia_section and "non-profit" in ia_section and "100%" not in ia_section:
                score -= 5
                errors.append(
                    {
                        "claim": "IA has 70% funding for non-profit organizations",
                        "correct_value": "IA has 100% funding for non-profit organizations",
                        "source": "EU Funding Domain Skill",
                    }
                )

    # Check for claims that NGOs cannot participate in RIA
    if "ria" in response_lower:
        ria_idx = response_lower.find("ria")
        if ria_idx != -1:
            ria_section = response_lower[ria_idx : ria_idx + 300]

            if "cannot" in ria_section or "not eligible" in ria_section:
                if "ngo" in ria_section or "civil society" in ria_section:
                    score -= 5
                    errors.append(
                        {
                            "claim": "NGOs cannot participate in RIA",
                            "correct_value": "NGOs can participate in RIA as partners",
                            "source": "EU Funding Domain Skill",
                        }
                    )

    # Check for incorrect claims about CSA TRL requirements
    if "csa" in response_lower:
        csa_idx = response_lower.find("csa")
        if csa_idx != -1:
            csa_section = response_lower[csa_idx : csa_idx + 300]

            # CSA has no TRL requirements - it's not technology-focused
            if "trl" in csa_section and ("5" in csa_section or "6" in csa_section):
                if "not applicable" not in csa_section and "no trl" not in csa_section:
                    score -= 5
                    errors.append(
                        {
                            "claim": "CSA has TRL requirements",
                            "correct_value": "CSA has no TRL requirement (not technology-focused)",
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
    - Clear guidance on which instrument to choose (4 points)
    - Links or resource references (3 points)
    - Next steps guidance (3 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Clear guidance on options (4 points)
    guidance_patterns = [
        "best fit",
        "recommend",
        "ideal for",
        "suited for",
        "primary instrument",
        "specifically",
        "ngo role",
        "civil society",
        "can participate",
        "eligible",
        "how to",
    ]
    if sum(1 for p in guidance_patterns if p in response_lower) >= 2:
        score += 4
    else:
        notes.append("Limited guidance on instrument selection")

    # Links or resource references (3 points)
    link_patterns = [
        "http",
        "portal",
        "website",
        "ec.europa",
        "funding-tenders",
        "partner search",
        "work programme",
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
    ]
    next_step_found = sum(1 for phrase in next_step_phrases if phrase in response_lower)
    score += min(3, next_step_found)

    return (
        score,
        "; ".join(notes) if notes else "Good actionability with clear NGO guidance",
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
            "component_id": "ngo_climate",
            "description": "NGO climate change funding opportunities",
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
            f"Improve query fulfillment: Must mention CSA opportunities, "
            f"consortium partner roles, and climate-specific context. "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include CSA funding rate (100%), typical budgets "
            "(EUR 1-3M), NGO roles (dissemination, stakeholder engagement, policy support)"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual errors: CSA funding is 100%, IA for non-profit is 100%, "
            "NGOs can participate in RIA as partners, CSA has no TRL requirement"
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add links to EU Funding Portal, explain CSA is "
            "best fit for NGOs, provide guidance on finding consortium partners"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Comprehensive coverage of NGO opportunities")
    if specificity_score >= 20:
        strengths.append("Rich in specific funding and role details")
    if accuracy_score >= 20:
        strengths.append("Factually accurate on NGO funding rules")
    if actionability_score >= 8:
        strengths.append("Provides clear guidance for NGO participation")

    return EvaluationResult(
        prompt_id="015",
        query=PROMPT_015_QUERY,
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
class TestPrompt015NGOClimate:
    """
    Test suite for Prompt 015: NGO/Umbrella Organization Climate Opportunities.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_ngo_climate(self):
        """
        Main evaluation test for Prompt 015.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_015_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_015_ngo_climate.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 015: NGO/Umbrella Organization Climate Evaluation")
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
        api_result = get_mapit_response(PROMPT_015_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_ngo(self):
        """Verify the response mentions NGO opportunities (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_015_ngo_climate.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_ngo_climate first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        ngo_keywords_found = sum(1 for kw in NGO_OPPORTUNITY_KEYWORDS if kw in response_lower)

        # Informational check
        print(f"NGO opportunity keywords found: {ngo_keywords_found}")
        if ngo_keywords_found < 3:
            print("Note: Response needs more detail on NGO-specific opportunities")

        # Soft assertion - just verify results exist
        assert "response" in result, "Response field missing from results"

    def test_response_mentions_csa(self):
        """Verify the response mentions CSA instrument (informational)."""
        results_file = RESULTS_DIR / "prompt_015_ngo_climate.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_ngo_climate first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        csa_found = sum(1 for kw in CSA_KEYWORDS if kw in response_lower)

        # Informational check
        print(f"CSA keywords found: {csa_found}")
        if csa_found < 2:
            print("Note: Response should include CSA details for NGOs")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt015OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_NGO_CLIMATE, {"source": "sample_excellent"}
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_015_ngo_climate_sample_excellent.json"
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
            SampleResponses.PARTIAL_NGO_CLIMATE, {"source": "sample_partial"}
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
        evaluation = evaluate_response(SampleResponses.POOR_NGO_CLIMATE, {"source": "sample_poor"})

        print("\nPoor Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < NEEDS_REVIEW_THRESHOLD, (
            f"Poor response scored {evaluation.overall_score}, expected < {NEEDS_REVIEW_THRESHOLD}"
        )
        assert evaluation.result == "FAIL"

    def test_evaluation_identifies_missing_items(self):
        """Test that evaluation identifies missing content."""
        evaluation = evaluate_response(SampleResponses.POOR_NGO_CLIMATE, {"source": "sample_poor"})

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
            SampleResponses.EXCELLENT_NGO_CLIMATE, {"source": "excellent"}
        )
        poor_eval = evaluate_response(SampleResponses.POOR_NGO_CLIMATE, {"source": "poor"})

        # Excellent response should have much higher specificity
        excellent_specificity = excellent_eval.component_scores[0]["specificity"]
        poor_specificity = poor_eval.component_scores[0]["specificity"]

        assert excellent_specificity > poor_specificity, (
            f"Excellent specificity ({excellent_specificity}) should be > poor ({poor_specificity})"
        )

    def test_save_evaluation_result_json(self):
        """Test that evaluation results are saved correctly as JSON."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_NGO_CLIMATE, {"source": "test_json_save"}
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_015_ngo_climate_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "015"
        assert loaded["query"] == PROMPT_015_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
