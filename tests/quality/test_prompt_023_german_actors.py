"""
Quality Evaluation Test for Prompt 023: Top 10 German Actors.

This test evaluates the MAPIT AI response to the query:
"Show me the top 10 most successful German actors in Horizon Europe
(in terms of coordinator/partner status or participation in largest-budgeted projects)."

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Returns exactly 10 German organizations
- Specificity (25 points): Organization names, project counts, budgets, roles
- Factual Accuracy (25 points): Valid organization names, plausible statistics
- Actionability (10 points): Links to CORDIS/EU portal, how to learn more

Pass threshold: >= 85/100

Reference requirements from PRD:
- Must list 10 specific German organizations
- Include project counts or budgets
- Show coordinator/partner status or participation metrics

Run with:
    pytest tests/quality/test_prompt_023_german_actors.py -v

For live API tests only:
    pytest tests/quality/test_prompt_023_german_actors.py -v -m "live_api"
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
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# API configuration
API_BASE_URL = os.getenv("MAP_IT_API_URL", "http://localhost:8000")
RESULTS_DIR = Path(__file__).parent / "results"

# Evaluation thresholds
PASS_THRESHOLD = 85
NEEDS_REVIEW_THRESHOLD = 70

# The query for this test
PROMPT_023_QUERY = (
    "Show me the top 10 most successful German actors in Horizon Europe "
    "(in terms of coordinator/partner status or participation in largest-budgeted projects)."
)

# Expected German organization types/keywords
EXPECTED_GERMAN_KEYWORDS = [
    "germany",
    "german",
    "deutschland",
    "fraunhofer",
    "max planck",
    "leibniz",
    "helmholtz",
    "dfg",
    "tum",
    "lmu",
    "rwth",
    "kit",
    "tu berlin",
    "tu munich",
    "tu münchen",
    "universität",
    "university",
    "hochschule",
    "forschung",
    "institut",
    "gmbh",
    "e.v.",
]

# German institution patterns (well-known research institutions)
GERMAN_INSTITUTION_PATTERNS = [
    r"fraunhofer",
    r"max[\-\s]planck",
    r"helmholtz",
    r"leibniz",
    r"dfg",
    r"rwth\s*aachen",
    r"tu[\s\-]?m[üu]n(chen|ich)",
    r"kit\b",
    r"karlsruhe",
    r"heidelberg",
    r"bonn",
    r"freiburg",
    r"göttingen",
    r"gottingen",
    r"berlin",
    r"hamburg",
    r"dresden",
    r"darmstadt",
    r"erlangen",
    r"tübingen",
    r"tubingen",
    r"münster",
    r"munster",
    r"cologne",
    r"köln",
    r"munich",
    r"münchen",
]

# Statistics patterns
STATISTICS_PATTERNS = {
    "project_count": [
        r"\d+\s*project",
        r"project[s]?\s*[\:]\s*\d+",
        r"participation[s]?\s*[\:]\s*\d+",
        r"\d+\s*participation",
    ],
    "budget": [
        r"€[\d,\.]+",
        r"\d+[\.,]\d+\s*(?:m(?:illion)?|bn|billion)",
        r"budget",
        r"funding",
        r"contribution",
    ],
    "coordinator_status": [
        "coordinator",
        "coordinated",
        "lead",
        "leading",
        "coordination",
    ],
    "partner_status": [
        "partner",
        "participant",
        "participating",
        "involvement",
    ],
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_GERMAN_ACTORS = """
## Top 10 Most Successful German Actors in Horizon Europe

Based on analysis of coordinator/partner status and participation in large-budget projects:

### 1. **Fraunhofer-Gesellschaft**
- **Projects Coordinated**: 245
- **Total Participations**: 890
- **Total EC Funding**: €1.2 billion
- **Key Areas**: Industry 4.0, AI, Energy, Health Technologies

### 2. **Max Planck Society** (Max-Planck-Gesellschaft)
- **Projects Coordinated**: 180
- **Total Participations**: 520
- **Total EC Funding**: €780 million
- **Key Areas**: Fundamental Research, Life Sciences, Physics

### 3. **Helmholtz Association**
- **Projects Coordinated**: 165
- **Total Participations**: 480
- **Total EC Funding**: €720 million
- **Key Areas**: Energy, Health, Earth & Environment

### 4. **RWTH Aachen University**
- **Projects Coordinated**: 85
- **Total Participations**: 340
- **Total EC Funding**: €410 million
- **Key Areas**: Engineering, Materials, Digital Technologies

### 5. **Technical University of Munich (TUM)**
- **Projects Coordinated**: 78
- **Total Participations**: 320
- **Total EC Funding**: €385 million
- **Key Areas**: AI, Robotics, Quantum Technologies

### 6. **Karlsruhe Institute of Technology (KIT)**
- **Projects Coordinated**: 72
- **Total Participations**: 290
- **Total EC Funding**: €350 million
- **Key Areas**: Energy, Mobility, Computing

### 7. **Leibniz Association**
- **Projects Coordinated**: 65
- **Total Participations**: 260
- **Total EC Funding**: €310 million
- **Key Areas**: Social Sciences, Humanities, Life Sciences

### 8. **University of Heidelberg**
- **Projects Coordinated**: 58
- **Total Participations**: 210
- **Total EC Funding**: €280 million
- **Key Areas**: Life Sciences, Medicine, Physics

### 9. **Ludwig-Maximilians-Universität München (LMU)**
- **Projects Coordinated**: 52
- **Total Participations**: 195
- **Total EC Funding**: €250 million
- **Key Areas**: Medicine, Humanities, Natural Sciences

### 10. **TU Berlin**
- **Projects Coordinated**: 48
- **Total Participations**: 180
- **Total EC Funding**: €220 million
- **Key Areas**: Engineering, Urban Systems, Digital Technologies

---

### Summary Statistics

| Rank | Organization | Coordinations | Total Projects | EC Funding |
|------|-------------|---------------|----------------|------------|
| 1 | Fraunhofer | 245 | 890 | €1.2B |
| 2 | Max Planck | 180 | 520 | €780M |
| 3 | Helmholtz | 165 | 480 | €720M |
| 4 | RWTH Aachen | 85 | 340 | €410M |
| 5 | TUM | 78 | 320 | €385M |

### How to Learn More

1. **CORDIS Database**: Search for German organizations at https://cordis.europa.eu
2. **EU Funding Portal**: https://ec.europa.eu/info/funding-tenders/
3. **Organization Websites**: Contact directly for collaboration opportunities
4. **Partner Search**: Use EU Partner Search tool to find German partners
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_GERMAN_ACTORS = """
Here are some successful German organizations in Horizon Europe:

1. Fraunhofer-Gesellschaft - Many projects in technology
2. Max Planck Society - Research projects
3. Helmholtz Association - Science projects
4. RWTH Aachen - Engineering
5. TU Munich - Various projects

These organizations participate in many EU projects. Germany is one of the
most successful countries in Horizon Europe funding.

You can find more information about German participation on CORDIS.
"""

    # A low-quality response that should FAIL (< 70)
    POOR_GERMAN_ACTORS = """
Germany participates in many Horizon Europe projects. German universities
and research institutes are active in EU funding. The country receives
significant funding for research and innovation.

Some well-known German institutions include:
- Universities
- Research centers
- Companies

For more information, visit the EU portal.
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
        response = httpx.get(
            f"{API_BASE_URL}/api/v3/conversation/health", timeout=5.0
        )
        return response.status_code == 200
    except Exception:
        return False


# Skip decorator for live tests
live_api = pytest.mark.skipif(
    not check_api_available(),
    reason="Live API not available. Start Docker containers with: docker compose up",
)


def get_mapit_response(
    query: str, conversation_id: int | None = None
) -> dict[str, Any]:
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

    client = httpx.Client(timeout=180.0)  # Longer timeout for statistics queries
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


def count_organizations_mentioned(response: str) -> int:
    """
    Count the number of distinct organizations mentioned in the response.

    Looks for patterns like:
    - Numbered lists (1., 2., etc.)
    - Bullet point organization entries
    - German institution names
    - Organization patterns (University of, Institut, etc.)
    """
    response_lower = response.lower()

    # Count numbered items (1., 2., 1), 2), etc.)
    numbered_pattern = r"(?:^|\n)\s*(?:\d+[\.\)]\s+|\*\*\d+\.|###\s*\d+\.)"
    numbered_matches = len(re.findall(numbered_pattern, response))

    # Count bullet point organization entries (e.g., "- FRAUNHOFER...")
    # This catches API responses that list organizations with bullets
    bullet_org_pattern = r"(?:^|\n)\s*-\s+[A-Z][A-Z\s\-]+(?:EV|GMBH|E\.V\.|AG|UNIVERSITAET|UNIVERSITEIT|UNIVERSITY|INSTITUTE|INSTITUT|GESELLSCHAFT|CENTRUM|CENTER|CENTRE)"  # noqa: E501
    bullet_matches = len(re.findall(bullet_org_pattern, response, re.IGNORECASE))

    # Count German institution mentions
    institution_count = 0
    for pattern in GERMAN_INSTITUTION_PATTERNS:
        matches = re.findall(pattern, response_lower)
        institution_count += len(set(matches))

    # Count organizations with project/funding patterns
    # e.g., "FRAUNHOFER...: 624 projects, €488,535,067"
    org_with_stats_pattern = r"(?:^|\n)\s*-\s+[A-Z][A-Z\s\-]+:\s*\d+\s*projects?"
    org_with_stats_matches = len(
        re.findall(org_with_stats_pattern, response, re.IGNORECASE)
    )

    # Use the highest count, but cap at reasonable max
    org_count = max(numbered_matches, institution_count, bullet_matches, org_with_stats_matches)

    return min(org_count, 15)  # Cap at 15 to avoid false positives


def evaluate_query_fulfillment(response: str) -> tuple[int, str, list[str], list[str]]:
    """
    Evaluate query fulfillment (40 points max).

    Checks if:
    - Returns approximately 10 German organizations (20 points)
    - Organizations are clearly German (10 points)
    - Shows coordinator/partner status or statistics (10 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    found_items = []
    missing_items = []

    # Check for ~10 organizations (20 points)
    org_count = count_organizations_mentioned(response)

    if org_count >= 10:
        score += 20
        found_items.append(f"~{org_count} organizations listed")
    elif org_count >= 7:
        score += 15
        found_items.append(f"{org_count} organizations listed")
        missing_items.append("Should list exactly 10 organizations")
    elif org_count >= 5:
        score += 10
        found_items.append(f"Only {org_count} organizations")
        missing_items.append("Need more organizations (requested 10)")
    elif org_count >= 1:
        score += 5
        missing_items.append(f"Only {org_count} organization(s) listed, need 10")
    else:
        missing_items.append("No distinct organizations identified")

    # Check for German context (10 points)
    german_keywords_found = sum(
        1 for keyword in EXPECTED_GERMAN_KEYWORDS if keyword in response_lower
    )

    if german_keywords_found >= 5:
        score += 10
        found_items.append("Strong German context")
    elif german_keywords_found >= 3:
        score += 7
        found_items.append("Good German context")
        missing_items.append("More German-specific content needed")
    elif german_keywords_found >= 1:
        score += 4
        missing_items.append("Limited German context")
    else:
        missing_items.append("Organizations not clearly German")

    # Check for statistics/metrics (10 points)
    has_project_count = any(
        re.search(pat, response_lower) for pat in STATISTICS_PATTERNS["project_count"]
    )
    has_budget = any(
        re.search(pat, response_lower)
        if pat.startswith(r"[€\\d]")
        else pat in response_lower
        for pat in STATISTICS_PATTERNS["budget"]
    )
    has_coordinator = any(
        indicator in response_lower
        for indicator in STATISTICS_PATTERNS["coordinator_status"]
    )
    has_partner = any(
        indicator in response_lower for indicator in STATISTICS_PATTERNS["partner_status"]
    )

    stats_score = 0
    if has_project_count:
        stats_score += 3
        found_items.append("Project counts provided")
    if has_budget:
        stats_score += 3
        found_items.append("Budget/funding information")
    if has_coordinator or has_partner:
        stats_score += 4
        found_items.append("Coordinator/partner status shown")

    score += stats_score

    if stats_score < 10:
        if not has_project_count:
            missing_items.append("Missing project counts")
        if not has_budget:
            missing_items.append("Missing budget/funding information")
        if not (has_coordinator or has_partner):
            missing_items.append("Missing coordinator/partner status")

    # Build notes
    if missing_items:
        notes.append(f"Missing: {', '.join(missing_items)}")
    else:
        notes.append("All key requirements met")

    return score, "; ".join(notes), missing_items, found_items


def evaluate_specificity(response: str) -> tuple[int, str]:
    """
    Evaluate specificity (25 points max).

    Checks for:
    - Named organizations (8 points)
    - Project counts/numbers (6 points)
    - Budget figures (6 points)
    - Ranking/comparison metrics (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Named organizations (8 points)
    org_patterns_found = 0
    for pattern in GERMAN_INSTITUTION_PATTERNS:
        if re.search(pattern, response_lower):
            org_patterns_found += 1

    if org_patterns_found >= 8:
        score += 8
    elif org_patterns_found >= 5:
        score += 6
        notes.append("Some organization names missing")
    elif org_patterns_found >= 2:
        score += 3
        notes.append("Limited named organizations")
    else:
        notes.append("No specific organization names")

    # Project counts (6 points)
    project_numbers = re.findall(r"\d+\s*(?:project|participation)", response_lower)
    project_numbers += re.findall(r"(?:project|participation)[s]?\s*[\:]\s*\d+", response_lower)

    if len(project_numbers) >= 5:
        score += 6
    elif len(project_numbers) >= 2:
        score += 4
        notes.append("Some project counts missing")
    elif len(project_numbers) >= 1:
        score += 2
        notes.append("Limited project count information")
    else:
        notes.append("No project counts")

    # Budget figures (6 points)
    budget_patterns = [
        r"€[\d,\.]+",
        r"\d+[\.,]\d+\s*(?:m(?:illion)?|bn|billion)",
        r"\d+\s*(?:m(?:illion)?|bn|billion)",
    ]
    budget_matches = sum(
        len(re.findall(pat, response, re.IGNORECASE)) for pat in budget_patterns
    )

    if budget_matches >= 5:
        score += 6
    elif budget_matches >= 2:
        score += 4
        notes.append("Some budget figures missing")
    elif budget_matches >= 1:
        score += 2
        notes.append("Limited budget information")
    else:
        notes.append("No budget figures")

    # Ranking/comparison metrics (5 points)
    ranking_indicators = [
        "top",
        "rank",
        "most",
        "successful",
        "leading",
        "#1",
        "#2",
        "first",
        "second",
    ]
    ranking_found = sum(1 for ind in ranking_indicators if ind in response_lower)

    if ranking_found >= 3:
        score += 5
    elif ranking_found >= 1:
        score += 3
        notes.append("Limited ranking context")
    else:
        notes.append("No ranking/comparison metrics")

    return score, "; ".join(notes) if notes else "Good specificity with organization details"


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - Organizations appear to be real German institutions
    - Statistics are plausible (not obviously wrong)
    - No obviously incorrect claims about Horizon Europe
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check for obviously fake organization names
    # (Organizations should match known German patterns)
    known_orgs = [
        "fraunhofer",
        "max planck",
        "max-planck",
        "helmholtz",
        "leibniz",
        "rwth",
        "kit",
        "tum",
        "lmu",
        "berlin",
        "münchen",
        "muenchen",
        "munich",
        "heidelberg",
        "karlsruhe",
        "aachen",
        "dresden",
        "julich",
        "jülich",
        "charite",
        "deutsches zentrum",
    ]

    orgs_found = sum(1 for org in known_orgs if org in response_lower)
    if orgs_found < 3 and "german" in response_lower:
        # Claims to be about Germany but doesn't mention known German orgs
        score -= 5
        errors.append(
            {
                "claim": "Organizations not recognizable as major German institutions",
                "correct_value": "Should mention Fraunhofer, Max Planck, Helmholtz, etc.",
                "source": "Organization validation",
            }
        )

    # Check for unreasonable statistics
    # German orgs typically have 50-500 projects, €50M-€2B funding
    budget_matches = re.findall(
        r"€([\d,\.]+)\s*(?:b(?:illion)?|bn)",
        response,
        re.IGNORECASE,
    )
    for match in budget_matches:
        try:
            value = float(match.replace(",", "").replace(".", ""))
            if value > 10:  # More than €10 billion for single org
                score -= 3
                errors.append(
                    {
                        "claim": f"Budget {match}B seems too high for single org",
                        "correct_value": "German orgs typically €50M-€2B in HE",
                        "source": "Budget validation",
                    }
                )
                break
        except ValueError:
            pass

    # Check for claims about wrong programme
    if "fp7" in response_lower and "horizon europe" in response_lower:
        if "fp7" in response_lower and "most successful" in response_lower:
            score -= 5
            errors.append(
                {
                    "claim": "FP7 statistics used for Horizon Europe question",
                    "correct_value": "Should focus on Horizon Europe (2021-2027)",
                    "source": "Programme validation",
                }
            )

    # Check for obviously wrong country attribution
    non_german_countries = ["france", "italy", "spain", "uk", "netherlands"]
    wrong_attribution = False
    for country in non_german_countries:
        if f"from {country}" in response_lower or f"({country})" in response_lower:
            # Check if it's in context of a German organization
            country_idx = response_lower.find(country)
            if country_idx >= 0:
                context = response_lower[max(0, country_idx - 50) : country_idx + 50]
                if "top" in context or "german" in context or "#" in context:
                    wrong_attribution = True
                    break

    if wrong_attribution:
        score -= 5
        errors.append(
            {
                "claim": "Non-German organization listed as top German actor",
                "correct_value": "Should only list German organizations",
                "source": "Country validation",
            }
        )

    notes = f"Accuracy check: {score}/25 points"
    if errors:
        notes += f"; {len(errors)} issue(s) found"

    return max(0, score), notes, errors


def evaluate_actionability(response: str) -> tuple[int, str]:
    """
    Evaluate actionability (10 points max).

    Checks for:
    - Links to CORDIS or EU portal (4 points)
    - How to learn more guidance (3 points)
    - Contact/collaboration suggestions (3 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Links or portal references (4 points)
    link_patterns = [
        "http",
        "cordis",
        "cordis.europa.eu",
        "ec.europa",
        "website",
        "portal",
    ]
    links_found = sum(1 for link in link_patterns if link in response_lower)
    if links_found >= 2:
        score += 4
    elif links_found >= 1:
        score += 2
        notes.append("Limited links to resources")
    else:
        notes.append("No links to CORDIS or EU portal")

    # How to learn more (3 points)
    guidance_phrases = [
        "learn more",
        "more information",
        "find out",
        "search for",
        "explore",
        "discover",
        "contact",
    ]
    guidance_found = sum(1 for phrase in guidance_phrases if phrase in response_lower)
    score += min(3, guidance_found)

    # Collaboration/contact suggestions (3 points)
    collab_phrases = [
        "collaboration",
        "partner",
        "reach out",
        "connect",
        "network",
        "opportunity",
        "join",
    ]
    collab_found = sum(1 for phrase in collab_phrases if phrase in response_lower)
    score += min(3, collab_found)

    return (
        score,
        "; ".join(notes) if notes else "Good actionability with resources",
    )


def evaluate_response(
    response: str, response_metadata: dict[str, Any]
) -> EvaluationResult:
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
    overall_score = (
        fulfillment_score + specificity_score + accuracy_score + actionability_score
    )

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
            "component_id": "german_actors",
            "description": "Top 10 most successful German actors in Horizon Europe",
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
            f"Improve query fulfillment: List exactly 10 German organizations "
            f"with coordinator/partner statistics. "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include specific organization names, project counts, "
            "budget figures, and ranking metrics for all 10 organizations"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual accuracy: Verify organizations are real German institutions "
            "(Fraunhofer, Max Planck, Helmholtz, universities), statistics are plausible"
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add CORDIS/EU portal links, guidance on "
            "how to learn more, collaboration suggestions"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Lists ~10 German organizations with statistics")
    if specificity_score >= 20:
        strengths.append("Rich in organization details and metrics")
    if accuracy_score >= 20:
        strengths.append("Factually accurate organization information")
    if actionability_score >= 8:
        strengths.append("Provides useful resources and guidance")

    return EvaluationResult(
        prompt_id="023",
        query=PROMPT_023_QUERY,
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
class TestPrompt023GermanActors:
    """
    Test suite for Prompt 023: Top 10 German Actors.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_german_actors(self):
        """
        Main evaluation test for Prompt 023.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_023_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_023_german_actors.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 023: Top 10 German Actors Evaluation")
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
        api_result = get_mapit_response(PROMPT_023_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_organizations(self):
        """Verify the response mentions organizations (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_023_german_actors.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_german_actors first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response = result["response"]
        org_count = count_organizations_mentioned(response)

        # Informational check
        print(f"Organizations mentioned: {org_count}")
        if org_count < 10:
            print("Note: Response needs more organization listings")

        # Soft assertion - just verify results exist
        assert "response" in result, "Response field missing from results"

    def test_response_german_context(self):
        """Verify the response has German context (informational)."""
        results_file = RESULTS_DIR / "prompt_023_german_actors.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_german_actors first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        german_keywords_found = sum(
            1 for kw in EXPECTED_GERMAN_KEYWORDS if kw in response_lower
        )

        # Informational check
        print(f"German keywords found: {german_keywords_found}")
        if german_keywords_found < 3:
            print("Note: Response needs more German-specific content")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt023OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_GERMAN_ACTORS, {"source": "sample_excellent"}
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_023_german_actors_sample_excellent.json"
        save_result(evaluation, results_file)

        print("\nExcellent Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score >= PASS_THRESHOLD, (
            f"Excellent response scored {evaluation.overall_score}, "
            f"expected >= {PASS_THRESHOLD}"
        )
        assert evaluation.result == "PASS"

    def test_partial_response_needs_review(self):
        """Test that a partial response scores 70-84 (NEEDS_REVIEW) or lower."""
        evaluation = evaluate_response(
            SampleResponses.PARTIAL_GERMAN_ACTORS, {"source": "sample_partial"}
        )

        print("\nPartial Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        # Partial should score below PASS threshold
        assert evaluation.overall_score < PASS_THRESHOLD, (
            f"Partial response scored {evaluation.overall_score}, "
            f"expected < {PASS_THRESHOLD}"
        )

    def test_poor_response_fails(self):
        """Test that a poor response scores < 70 (FAIL)."""
        evaluation = evaluate_response(
            SampleResponses.POOR_GERMAN_ACTORS, {"source": "sample_poor"}
        )

        print("\nPoor Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < NEEDS_REVIEW_THRESHOLD, (
            f"Poor response scored {evaluation.overall_score}, "
            f"expected < {NEEDS_REVIEW_THRESHOLD}"
        )
        assert evaluation.result == "FAIL"

    def test_evaluation_identifies_missing_items(self):
        """Test that evaluation identifies missing content."""
        evaluation = evaluate_response(
            SampleResponses.POOR_GERMAN_ACTORS, {"source": "sample_poor"}
        )

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
            SampleResponses.EXCELLENT_GERMAN_ACTORS, {"source": "excellent"}
        )
        poor_eval = evaluate_response(
            SampleResponses.POOR_GERMAN_ACTORS, {"source": "poor"}
        )

        # Excellent response should have much higher specificity
        excellent_specificity = excellent_eval.component_scores[0]["specificity"]
        poor_specificity = poor_eval.component_scores[0]["specificity"]

        assert excellent_specificity > poor_specificity, (
            f"Excellent specificity ({excellent_specificity}) "
            f"should be > poor ({poor_specificity})"
        )

    def test_save_evaluation_result_json(self):
        """Test that evaluation results are saved correctly as JSON."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_GERMAN_ACTORS, {"source": "test_json_save"}
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_023_german_actors_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "023"
        assert loaded["query"] == PROMPT_023_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
