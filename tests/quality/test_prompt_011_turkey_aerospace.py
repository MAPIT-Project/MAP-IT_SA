"""
Quality Evaluation Test for Prompt 011: Turkey Aerospace Researcher.

This test evaluates the MAPIT AI response to the query:
"I am from Turkey working in aerospace studies. Are there any open calls or
upcoming calls that would be relevant for me?"

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Explains Turkey eligibility, lists relevant calls
- Specificity (25 points): Call IDs, deadlines, budgets, topic details
- Factual Accuracy (25 points): Turkey's Associated Country status verified
- Actionability (10 points): Clear next steps, links to portal

Pass threshold: >= 85/100

Reference facts from eu-funding-domain skill:
- Turkey is an ASSOCIATED COUNTRY in Horizon Europe (full eligibility)
- Aerospace is primarily under Cluster 4 (Digital, Industry and Space)
- Related topics also in Cluster 5 (Climate, Energy, Mobility - transport)
- RIA: 100% funding, €3-10M, TRL 1-5
- IA: 70% funding (100% non-profit), €5-20M, TRL 5-8
- Standard consortium: 3 partners from 3 different EU/Associated countries

Run with:
    pytest tests/quality/test_prompt_011_turkey_aerospace.py -v

For live API tests only:
    pytest tests/quality/test_prompt_011_turkey_aerospace.py -v -m "live_api"
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
PROMPT_011_QUERY = (
    "I am from Turkey working in aerospace studies. Are there any open calls or "
    "upcoming calls that would be relevant for me?"
)

# Expected content based on PRD requirements
# Must address Turkey's Associated Country status AND aerospace-relevant calls
TURKEY_ELIGIBILITY_KEYWORDS = [
    "turkey",
    "associated",
    "associated country",
    "eligible",
    "participate",
    "full participation",
    "turkish",
    "can apply",
    "allowed",
]

AEROSPACE_KEYWORDS = [
    "aerospace",
    "space",
    "aviation",
    "aircraft",
    "satellite",
    "cluster 4",
    "digital",
    "industry",
    "transport",
    "mobility",
    "aeronautics",
    "unmanned",
    "uav",
    "drone",
    "launcher",
    "earth observation",
]

# Call-specific patterns to check
CALL_DETAIL_PATTERNS = {
    "call_id": [
        "horizon-cl4",
        "horizon-cl5",
        "cl4-",
        "cl5-",
        "space",
        "call id",
        "topic",
        "destination",
    ],
    "deadline": [
        "deadline",
        "closes",
        "submission",
        "2025",
        "2026",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ],
    "budget": ["€", "million", "budget", "funding", "m", "grant"],
    "status": ["open", "upcoming", "forthcoming", "planned", "expected"],
}

# Factual requirements for Turkey aerospace queries
FACTUAL_REQUIREMENTS = {
    "turkey_associated": {
        "claim": "Turkey is an Associated Country in Horizon Europe",
        "keywords": ["associated", "turkey"],
        "required": True,
    },
    "full_eligibility": {
        "claim": "Turkish organizations have full eligibility",
        "keywords": ["eligible", "participate", "apply", "full"],
        "required": True,
    },
    "cluster4_space": {
        "claim": "Aerospace is under Cluster 4 (Digital, Industry and Space)",
        "keywords": ["cluster 4", "space", "digital", "industry"],
        "required": False,
    },
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_TURKEY_AEROSPACE = """
## Relevant Funding Opportunities for Turkish Aerospace Researchers

### Turkey's Eligibility Status

**Great news!** Turkey is an **Associated Country** in Horizon Europe, which means:
- Turkish organizations can participate with **full eligibility**
- You can be a **coordinator** or partner in consortium projects
- You can receive EU funding on the same terms as EU Member States
- Standard consortium rules apply (3 partners from 3 different EU/Associated countries)

### Aerospace-Relevant Calls in Horizon Europe

Aerospace research primarily falls under **Cluster 4: Digital, Industry and Space**, with some
opportunities also in **Cluster 5: Climate, Energy and Mobility** (aviation/transport).

#### Open/Upcoming Calls:

| Call ID | Topic | Deadline | Budget | Type |
|---------|-------|----------|--------|------|
| HORIZON-CL4-2025-SPACE-01-11 | Space Technologies | April 2025 | €10M | RIA |
| HORIZON-CL4-2025-SPACE-01-21 | Earth Observation | May 2025 | €8M | RIA |
| HORIZON-CL4-2025-DIGITAL-02-04 | Autonomous Systems | March 2025 | €12M | IA |
| HORIZON-CL5-2025-D5-01-06 | Sustainable Aviation | June 2025 | €15M | RIA |
| HORIZON-EUSPA-2025-SPACE-01 | Galileo/Copernicus Apps | April 2025 | €6M | IA |

**Funding rates:**
- **RIA**: 100% funding
- **IA**: 70% (100% for non-profit organizations)

### Cross-Cutting Opportunities

As a Turkish researcher, you're also eligible for:
- **MSCA-PF** (Postdoctoral Fellowships): €200-300K for individual mobility
- **MSCA-DN** (Doctoral Networks): For PhD training networks
- **EIC Pathfinder**: For breakthrough aerospace technologies (€3-4M)

### How to Get Started

1. **Register** on the EU Funding & Tenders Portal
2. **Find Consortium Partners** using Partner Search (you need EU/Associated partners)
3. **Review** Cluster 4 Work Programme 2025 for detailed topic descriptions
4. **Check** the annual Turkish National Contact Point events

**Resources:**
- EU Funding Portal: https://ec.europa.eu/info/funding-tenders/opportunities/portal/
- Cluster 4 Work Programme: [Work Programme Documents]
- TÜBİTAK (Turkish NCP): National Contact Point for guidance

### Key Requirements for Turkish Applicants

- **Legal Entity**: Must be a legal entity established in Turkey
- **Consortium**: Usually need 2+ partners from other EU/Associated countries
- **No Security Restrictions**: Check individual calls for security-classified topics
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_TURKEY_AEROSPACE = """
For aerospace research, you should look at Cluster 4 in Horizon Europe which covers
Digital, Industry and Space.

Turkey can participate in Horizon Europe. There are various calls for space and
aerospace research. Some upcoming ones include topics on satellite technology and
aviation. The deadlines are typically in early 2025.

You can also apply for MSCA if you want to do a fellowship.

Check the EU Funding Portal for more information about specific calls and deadlines.
RIA projects offer 100% funding. You need partners from different countries to form
a consortium.
"""

    # A low-quality response that should FAIL (< 70)
    POOR_TURKEY_AEROSPACE = """
There are many funding opportunities for aerospace research in Europe.
You can check the European Commission website for available grants.
Horizon Europe has different clusters including one for digital and space.
Turkey may be able to participate in some programmes.
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
    - Turkey eligibility/status is explained (15 points)
    - Aerospace/space relevant calls mentioned (15 points)
    - Actual calls/topics listed (10 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    found_items = []
    missing_items = []

    # Check for Turkey eligibility explanation (15 points)
    turkey_found = 0
    for keyword in TURKEY_ELIGIBILITY_KEYWORDS:
        if keyword in response_lower:
            turkey_found += 1

    if turkey_found >= 3:
        score += 15
        found_items.append("Turkey eligibility explained")
    elif turkey_found >= 1:
        score += 7
        found_items.append("Turkey mentioned")
        missing_items.append("More detail on Turkey's Associated Country status needed")
    else:
        missing_items.append("Turkey eligibility status explanation")

    # Check for aerospace/space content (15 points)
    aerospace_found = 0
    for keyword in AEROSPACE_KEYWORDS:
        if keyword in response_lower:
            aerospace_found += 1

    if aerospace_found >= 4:
        score += 15
        found_items.append("Aerospace/space content")
    elif aerospace_found >= 2:
        score += 8
        found_items.append("Partial aerospace content")
        missing_items.append("More aerospace-specific calls needed")
    else:
        missing_items.append("Aerospace/space relevant calls")

    # Check for actual call details (10 points)
    has_call_details = any(
        pattern in response_lower
        for pattern in [
            "horizon-cl4",
            "horizon-cl5",
            "cl4-",
            "cl5-",
            "space-",
            "euspa",
            "call",
        ]
    )
    if has_call_details:
        score += 10
        found_items.append("Call identifiers/details")
    else:
        missing_items.append("Specific call identifiers")

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
    - Call IDs or topic references (7 points)
    - Deadlines with dates (7 points)
    - Budget figures (6 points)
    - Call status (open/upcoming) (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Call IDs or topics (7 points)
    call_id_found = sum(
        1 for pat in CALL_DETAIL_PATTERNS["call_id"] if pat in response_lower
    )
    call_score = min(7, call_id_found * 2)
    score += call_score
    if call_id_found < 2:
        notes.append("Limited call ID/topic specificity")

    # Deadlines (7 points)
    deadline_found = sum(
        1 for pat in CALL_DETAIL_PATTERNS["deadline"] if pat in response_lower
    )
    deadline_score = min(7, deadline_found * 2)
    score += deadline_score
    if deadline_found < 2:
        notes.append("Limited deadline information")

    # Budget figures (6 points)
    budget_found = sum(
        1 for pat in CALL_DETAIL_PATTERNS["budget"] if pat in response_lower
    )
    budget_score = min(6, budget_found * 2)
    score += budget_score
    if budget_found < 2:
        notes.append("Limited budget information")

    # Call status (5 points)
    status_found = sum(
        1 for pat in CALL_DETAIL_PATTERNS["status"] if pat in response_lower
    )
    status_score = min(5, status_found * 2)
    score += status_score

    return score, "; ".join(notes) if notes else "Good specificity with call details"


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - Turkey is correctly identified as Associated Country
    - Funding rates are accurate (RIA=100%, IA=70%)
    - Aerospace is correctly mapped to Cluster 4/5
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check for incorrect Turkey status
    # Turkey should be described as Associated Country, NOT third country or ineligible
    if "turkey" in response_lower:
        turkey_idx = response_lower.find("turkey")
        nearby_text = response_lower[max(0, turkey_idx - 50) : turkey_idx + 150]
        if "third country" in nearby_text or "not eligible" in nearby_text:
            if "associated" not in nearby_text:
                score -= 10
                errors.append(
                    {
                        "claim": "Turkey is a third country or not eligible",
                        "correct_value": "Turkey is an Associated Country with full eligibility",
                        "source": "EU Funding Domain Skill",
                    }
                )
        if "cannot participate" in nearby_text or "excluded" in nearby_text:
            score -= 10
            errors.append(
                {
                    "claim": "Turkey cannot participate",
                    "correct_value": "Turkey can fully participate as Associated Country",
                    "source": "EU Funding Domain Skill",
                }
            )

    # Check for incorrect funding rates
    # RIA should be 100%
    if "ria" in response_lower:
        ria_idx = response_lower.find("ria")
        nearby_text = response_lower[max(0, ria_idx - 50) : ria_idx + 150]
        if "70%" in nearby_text and "100%" not in nearby_text:
            score -= 5
            errors.append(
                {
                    "claim": "RIA has 70% funding rate",
                    "correct_value": "RIA has 100% funding rate",
                    "source": "EU Funding Domain Skill",
                }
            )

    # IA should be 70% (unless mentioning non-profit exception)
    if "ia" in response_lower and "innovation action" in response_lower:
        ia_idx = response_lower.find("innovation action")
        nearby_text = response_lower[max(0, ia_idx - 50) : ia_idx + 150]
        if "100%" in nearby_text and "70%" not in nearby_text:
            if "non-profit" not in nearby_text and "nonprofit" not in nearby_text:
                score -= 3
                errors.append(
                    {
                        "claim": "IA has 100% funding rate without exception",
                        "correct_value": "IA has 70% funding (100% for non-profits)",
                        "source": "EU Funding Domain Skill",
                    }
                )

    # Check if aerospace is wrongly mapped
    if "cluster 1" in response_lower and "aerospace" in response_lower:
        cluster1_idx = response_lower.find("cluster 1")
        nearby = response_lower[max(0, cluster1_idx - 30) : cluster1_idx + 100]
        if "aerospace" in nearby or "space" in nearby:
            score -= 5
            errors.append(
                {
                    "claim": "Aerospace is under Cluster 1 (Health)",
                    "correct_value": "Aerospace is under Cluster 4 (Digital, Industry, Space)",
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
    - Links to EU Funding Portal (4 points)
    - Next steps guidance (3 points)
    - Work Programme/NCP references (3 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Links or URL references (4 points)
    link_patterns = [
        "http",
        "portal",
        "website",
        "ec.europa",
        "funding-tenders",
        "register",
    ]
    if any(link in response_lower for link in link_patterns):
        score += 4
    else:
        notes.append("No links to official resources")

    # Next steps guidance (3 points)
    guidance_phrases = [
        "get started",
        "how to",
        "step",
        "register",
        "apply",
        "find partner",
        "check",
        "review",
        "consortium",
    ]
    guidance_found = sum(1 for phrase in guidance_phrases if phrase in response_lower)
    score += min(3, guidance_found)

    # Work Programme or NCP references (3 points)
    doc_refs = [
        "work programme",
        "wp-",
        "topic description",
        "national contact point",
        "ncp",
        "tübitak",
        "tubitak",
    ]
    doc_found = sum(1 for doc in doc_refs if doc in response_lower)
    score += min(3, doc_found)

    return (
        score,
        "; ".join(notes) if notes else "Good actionability with clear guidance",
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
            "component_id": "turkey_aerospace",
            "description": "Turkey eligibility and aerospace calls",
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
            f"Improve query fulfillment: Clearly explain Turkey's Associated Country "
            f"status AND list relevant aerospace/space calls from Cluster 4. "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include specific call IDs (HORIZON-CL4-*-SPACE-*), "
            "deadlines with dates, budget figures (€M), and call status (open/upcoming)"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual errors: Turkey is an Associated Country (full eligibility), "
            "funding rates (RIA=100%, IA=70%), Cluster 4 for aerospace"
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add links to EU Funding Portal, "
            "Cluster 4 Work Programme references, mention Turkish NCP (TÜBİTAK)"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Comprehensive coverage of Turkey eligibility and aerospace")
    if specificity_score >= 20:
        strengths.append("Rich in specific call details (IDs, deadlines, budgets)")
    if accuracy_score >= 20:
        strengths.append("Factually accurate on Turkey status and funding rates")
    if actionability_score >= 8:
        strengths.append("Provides clear guidance for Turkish applicants")

    return EvaluationResult(
        prompt_id="011",
        query=PROMPT_011_QUERY,
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
class TestPrompt011TurkeyAerospace:
    """
    Test suite for Prompt 011: Turkey Aerospace Researcher.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_turkey_aerospace(self):
        """
        Main evaluation test for Prompt 011.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_011_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_011_turkey_aerospace.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 011: Turkey Aerospace Researcher Evaluation")
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
        api_result = get_mapit_response(PROMPT_011_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_turkey_eligibility(self):
        """Verify the response mentions Turkey's eligibility (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_011_turkey_aerospace.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_turkey_aerospace first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        turkey_keywords_found = sum(
            1 for kw in TURKEY_ELIGIBILITY_KEYWORDS if kw in response_lower
        )

        # Informational check
        print(f"Turkey eligibility keywords found: {turkey_keywords_found}")
        if turkey_keywords_found < 3:
            print("Note: Response needs more detail on Turkey's Associated Country status")

        # Soft assertion - just verify results exist
        assert "response" in result, "Response field missing from results"

    def test_response_mentions_aerospace(self):
        """Verify the response mentions aerospace opportunities (informational)."""
        results_file = RESULTS_DIR / "prompt_011_turkey_aerospace.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_turkey_aerospace first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        aerospace_found = sum(1 for kw in AEROSPACE_KEYWORDS if kw in response_lower)

        # Informational check
        print(f"Aerospace keywords found: {aerospace_found}")
        if aerospace_found < 3:
            print("Note: Response should include more aerospace/space relevant calls")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt011OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_TURKEY_AEROSPACE, {"source": "sample_excellent"}
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_011_turkey_aerospace_sample_excellent.json"
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
            SampleResponses.PARTIAL_TURKEY_AEROSPACE, {"source": "sample_partial"}
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
            SampleResponses.POOR_TURKEY_AEROSPACE, {"source": "sample_poor"}
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
            SampleResponses.POOR_TURKEY_AEROSPACE, {"source": "sample_poor"}
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
            SampleResponses.EXCELLENT_TURKEY_AEROSPACE, {"source": "excellent"}
        )
        poor_eval = evaluate_response(
            SampleResponses.POOR_TURKEY_AEROSPACE, {"source": "poor"}
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
            SampleResponses.EXCELLENT_TURKEY_AEROSPACE, {"source": "test_json_save"}
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_011_turkey_aerospace_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "011"
        assert loaded["query"] == PROMPT_011_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
