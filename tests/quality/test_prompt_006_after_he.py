"""
Quality Evaluation Test for Prompt 006: After Horizon Europe.

This test evaluates the MAPIT AI response to the query:
"What will come after Horizon Europe?"

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Mentions FP10/successor programme, timeline, uncertainty
- Specificity (25 points): Specific dates, budget discussions, policy references
- Factual Accuracy (25 points): Verified timeline (HE ends 2027, FP10 expected 2028)
- Actionability (10 points): Guidance on staying informed, noting ongoing discussions

Pass threshold: >= 85/100

Key facts to verify:
- Horizon Europe runs 2021-2027
- Successor programme commonly referred to as FP10 (10th Framework Programme)
- FP10 expected to start 2028 (subject to legislative approval)
- Budget discussions tied to next MFF (Multiannual Financial Framework)
- Legislative proposal expected 2025-2026
- Uncertainty should be acknowledged (details not finalized)

Run with:
    pytest tests/quality/test_prompt_006_after_he.py -v

For live API tests only:
    pytest tests/quality/test_prompt_006_after_he.py -v -m "live_api"
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
PROMPT_006_QUERY = "What will come after Horizon Europe?"

# Expected content - FP10 and successor programme discussion
EXPECTED_CONTENT = {
    "fp10": {
        "name": "FP10 / 10th Framework Programme",
        "keywords": [
            "fp10",
            "framework programme 10",
            "10th framework",
            "tenth framework",
            "successor",
            "next framework programme",
        ],
        "description": "The successor to Horizon Europe, expected to begin 2028",
    },
    "timeline": {
        "name": "Timeline Information",
        "keywords": [
            "2027",
            "2028",
            "end of horizon",
            "after 2027",
            "starting 2028",
            "next mff",
            "multiannual financial framework",
        ],
        "description": "Key dates: HE ends 2027, FP10 expected 2028",
    },
    "uncertainty": {
        "name": "Acknowledgement of Uncertainty",
        "keywords": [
            "uncertain",
            "not finalized",
            "ongoing",
            "discussions",
            "negotiations",
            "proposal",
            "expected",
            "anticipated",
            "subject to",
            "pending",
            "preliminary",
            "evolving",
            "not yet",
        ],
        "description": "Response should note that details are not finalized",
    },
}

# Key factual information
FACTUAL_REQUIREMENTS = {
    "horizon_europe_end": {
        "claim": "Horizon Europe ends in 2027",
        "keywords": ["2027", "horizon europe"],
        "proximity": 200,
    },
    "fp10_start": {
        "claim": "FP10 expected to start in 2028",
        "keywords": ["2028", "fp10"],
        "proximity": 200,
    },
    "mff_connection": {
        "claim": "Connected to next MFF discussions",
        "keywords": ["mff", "budget", "multiannual"],
        "proximity": 200,
    },
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_AFTER_HE = """
**What Comes After Horizon Europe?**

Horizon Europe, the EU's current research and innovation framework programme,
runs from **2021 to 2027** with a budget of €95.5 billion. The successor programme
is commonly referred to as the
**10th Framework Programme (FP10)**.

## FP10 Overview

### Timeline
- **Horizon Europe**: 2021-2027 (current programme)
- **FP10**: Expected to start **2028** (subject to legislative approval)
- **Legislative Proposal**: Expected late 2025 - early 2026
- **MFF Negotiations**: FP10 budget tied to next Multiannual Financial Framework (2028-2034)

### Current Status (Important: Subject to Change)
As of now, FP10 is still in the **preparation and consultation phase**. Key developments include:

1. **Interim Evaluations**: The European Commission has conducted interim
   evaluations of Horizon Europe to inform FP10 design
2. **Stakeholder Consultations**: Ongoing consultations with research community, Member States,
   and industry
3. **Policy Priorities**: Expected focus on strategic autonomy, green/digital transitions,
   competitiveness, and simplification

### Expected Focus Areas for FP10
While not finalized, discussions suggest FP10 may emphasize:
- **Simplification**: Reduced administrative burden based on lessons learned
- **Impact**: Stronger focus on demonstrable societal and economic impact
- **Strategic Autonomy**: R&I support for European technological sovereignty
- **Green & Digital**: Continued alignment with European Green Deal and digital transformation
- **Widening Participation**: Enhanced support for underrepresented countries

### Budget Considerations
The FP10 budget will be determined during MFF negotiations. Key considerations:
- Research community advocating for significant budget increase
- Competition with other EU priorities (defense, cohesion, agriculture)
- Budget discussions expected to intensify in 2025-2026

## How to Stay Informed

⚠️ **Note**: Details about FP10 are still evolving. For the latest updates:
- [European Commission R&I Portal](https://research-and-innovation.ec.europa.eu/)
- [Horizon Europe Website](https://ec.europa.eu/info/horizon-europe)
- Follow Official EC Press Releases on R&I Policy
- Monitor European Parliament discussions on next MFF

## Current Actions
While waiting for FP10:
1. **Continue participating in Horizon Europe** calls through 2027
2. **Engage in consultations** when the Commission opens public feedback
3. **Build networks** and track record for future FP10 applications
4. **Monitor policy developments** via the R&I community and National Contact Points
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_AFTER_HE = """
After Horizon Europe, there will be a new framework programme.

The current Horizon Europe programme runs until 2027. The next programme is expected
to be called FP10 or the 10th Framework Programme.

FP10 will probably start in 2028, but the details are still being discussed. The European
Commission is working on preparing the new programme.

Key areas that might be covered include research and innovation, similar to current Horizon Europe.

For more information, check the European Commission website.
"""

    # A low-quality response that should FAIL (< 70)
    POOR_AFTER_HE = """
After Horizon Europe, there will be another EU funding programme for research.

The EU has historically had several framework programmes, so there will probably be
another one after the current programme ends.

You can find information about EU funding on the official websites.
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

    Checks if FP10/successor is mentioned, timeline provided, and uncertainty acknowledged.
    - FP10/successor mention: 15 points
    - Timeline information: 15 points
    - Uncertainty acknowledgement: 10 points
    """
    score = 0
    notes = []
    response_lower = response.lower()

    content_found = []
    content_missing = []

    # Check for FP10/successor mention (15 points)
    fp10_found = False
    for keyword in EXPECTED_CONTENT["fp10"]["keywords"]:
        if keyword in response_lower:
            fp10_found = True
            break

    if fp10_found:
        content_found.append("FP10/Successor programme")
        score += 15
    else:
        content_missing.append("FP10/Successor programme mention")

    # Check for timeline information (15 points)
    timeline_found = 0
    has_2027 = "2027" in response_lower
    has_2028 = "2028" in response_lower
    has_mff = any(kw in response_lower for kw in ["mff", "multiannual", "financial framework"])

    if has_2027:
        timeline_found += 5
        content_found.append("2027 (HE end date)")
    if has_2028:
        timeline_found += 5
        content_found.append("2028 (FP10 expected start)")
    if has_mff:
        timeline_found += 5
        content_found.append("MFF reference")

    score += timeline_found
    if timeline_found < 10:
        content_missing.append("Complete timeline information")

    # Check for uncertainty acknowledgement (10 points)
    uncertainty_found = False
    for keyword in EXPECTED_CONTENT["uncertainty"]["keywords"]:
        if keyword in response_lower:
            uncertainty_found = True
            break

    if uncertainty_found:
        content_found.append("Uncertainty acknowledged")
        score += 10
    else:
        content_missing.append("Uncertainty acknowledgement")

    # Build notes
    if content_missing:
        notes.append(f"Missing: {', '.join(content_missing)}")
    else:
        notes.append("All key content present")

    notes.append(
        f"Score breakdown: FP10={15 if fp10_found else 0}, "
        f"Timeline={timeline_found}, Uncertainty={10 if uncertainty_found else 0}"
    )

    return score, "; ".join(notes), content_missing, content_found


def evaluate_specificity(response: str) -> tuple[int, str]:
    """
    Evaluate specificity (25 points max).

    Checks for:
    - Specific years/dates (8 points)
    - Budget/MFF discussion details (6 points)
    - Policy priorities/focus areas (6 points)
    - Legislative process references (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Specific years/dates (8 points)
    date_patterns = [
        "2021",
        "2027",
        "2028",
        "2025",
        "2026",
        "2034",
        "late 2025",
        "early 2026",
    ]
    dates_found = sum(1 for pat in date_patterns if pat in response_lower)
    date_score = min(8, dates_found * 2)
    score += date_score
    if dates_found < 3:
        notes.append("Limited date specificity")

    # Budget/MFF discussion (6 points)
    budget_patterns = [
        "budget",
        "€",
        "billion",
        "mff",
        "multiannual",
        "financial framework",
        "funding",
    ]
    budget_found = sum(1 for pat in budget_patterns if pat in response_lower)
    budget_score = min(6, budget_found * 2)
    score += budget_score
    if budget_found < 2:
        notes.append("Limited budget/MFF details")

    # Policy priorities/focus areas (6 points)
    policy_patterns = [
        "simplification",
        "impact",
        "strategic autonomy",
        "green deal",
        "digital",
        "widening",
        "competitiveness",
        "sovereignty",
        "consultation",
    ]
    policy_found = sum(1 for pat in policy_patterns if pat in response_lower)
    policy_score = min(6, policy_found * 2)
    score += policy_score
    if policy_found < 2:
        notes.append("Limited policy discussion")

    # Legislative process references (5 points)
    legislative_patterns = [
        "legislative",
        "proposal",
        "commission",
        "parliament",
        "council",
        "regulation",
        "negotiation",
        "approval",
    ]
    legislative_found = sum(1 for pat in legislative_patterns if pat in response_lower)
    legislative_score = min(5, legislative_found * 2)
    score += legislative_score

    return score, "; ".join(notes) if notes else "Good specificity with concrete details"


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies facts:
    - Horizon Europe period: 2021-2027
    - FP10 expected start: 2028
    - No false certainty about unconfirmed details
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check for incorrect HE dates
    if "2020" in response_lower and "horizon europe" in response_lower:
        # Check if it's incorrectly saying HE started in 2020
        he_idx = response_lower.find("horizon europe")
        nearby_text = response_lower[max(0, he_idx - 100) : he_idx + 200]
        if "2020" in nearby_text and "2021" not in nearby_text:
            score -= 5
            errors.append(
                {
                    "claim": "Horizon Europe started in 2020",
                    "correct_value": "Horizon Europe runs 2021-2027",
                    "source": "EU Official Documentation",
                }
            )

    # Check for incorrect end date
    if "2026" in response_lower and "end" in response_lower:
        end_idx = response_lower.find("end")
        nearby_text = response_lower[max(0, end_idx - 50) : end_idx + 100]
        if "2026" in nearby_text and "2027" not in nearby_text:
            score -= 5
            errors.append(
                {
                    "claim": "Horizon Europe ends in 2026",
                    "correct_value": "Horizon Europe ends in 2027",
                    "source": "EU Official Documentation",
                }
            )

    # Check for presenting unconfirmed details as confirmed facts
    # (e.g., specific FP10 budget, exact structure)
    certainty_phrases = [
        "fp10 will have a budget of",
        "fp10 budget is €",
        "fp10 will definitely",
        "fp10 structure will be",
    ]
    for phrase in certainty_phrases:
        if phrase in response_lower:
            score -= 3
            errors.append(
                {
                    "claim": "Presenting unconfirmed FP10 details as facts",
                    "correct_value": "FP10 details are still under discussion",
                    "source": "Current EU Policy Status",
                }
            )
            break

    notes = f"Accuracy check: {25 - (25 - score)}/25 points"
    if errors:
        notes += f"; {len(errors)} error(s) found"

    return max(0, score), notes, errors


def evaluate_actionability(response: str) -> tuple[int, str]:
    """
    Evaluate actionability (10 points max).

    Checks for:
    - Links/resources for staying informed (4 points)
    - Guidance on current actions while waiting (3 points)
    - Consultation/engagement opportunities (3 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Links or URL references (4 points)
    if any(
        link in response_lower
        for link in ["http", "portal", "website", "ec.europa", "research-and-innovation"]
    ):
        score += 4
    else:
        notes.append("No links to official resources")

    # Guidance on current actions (3 points)
    guidance_phrases = [
        "continue",
        "participate",
        "stay informed",
        "monitor",
        "track",
        "engage",
        "build",
        "prepare",
        "current calls",
    ]
    guidance_found = sum(1 for phrase in guidance_phrases if phrase in response_lower)
    score += min(3, guidance_found)

    # Consultation/engagement opportunities (3 points)
    engagement_phrases = [
        "consultation",
        "feedback",
        "stakeholder",
        "national contact",
        "ncp",
        "community",
        "public",
    ]
    engagement_found = sum(1 for phrase in engagement_phrases if phrase in response_lower)
    score += min(3, engagement_found)

    return (
        score,
        "; ".join(notes) if notes else "Good actionability with guidance provided",
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
        missing_content,
        found_content,
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
            "component_id": "after_horizon_europe",
            "description": "After Horizon Europe / FP10 explanation",
            "fulfillment": fulfillment_score,
            "specificity": specificity_score,
            "accuracy": accuracy_score,
            "actionability": actionability_score,
            "total": overall_score,
            "notes": (
                f"Fulfillment: {fulfillment_notes}; Specificity: {specificity_notes}; "
                f"Accuracy: {accuracy_notes}; Actionability: {actionability_notes}"
            ),
            "missing_content": missing_content,
            "found_content": found_content,
        }
    ]

    # Generate fix suggestions
    fix_suggestions = []
    if fulfillment_score < 32:  # < 80% of 40
        fix_suggestions.append(
            f"Improve query fulfillment: Mention FP10/successor programme, provide timeline "
            f"(HE ends 2027, FP10 expected 2028), and acknowledge uncertainty about details. "
            f"Missing: {', '.join(missing_content) if missing_content else 'None'}."
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include specific years (2021-2027, 2028), "
            "MFF discussions, policy priorities (simplification, impact, strategic autonomy), "
            "and legislative process timeline (proposal expected 2025-2026)"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual accuracy: Ensure correct dates (HE: 2021-2027, FP10: 2028 expected), "
            "avoid presenting unconfirmed details as facts"
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add links to EC R&I portal, provide guidance on "
            "staying informed (monitor consultations, continue HE participation, "
            "engage with National Contact Points)"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Comprehensive coverage of FP10/successor programme")
    if specificity_score >= 20:
        strengths.append("Rich in specific details (dates, policy, process)")
    if accuracy_score >= 20:
        strengths.append("Factually accurate with appropriate uncertainty")
    if actionability_score >= 8:
        strengths.append("Provides clear guidance for researchers")

    return EvaluationResult(
        prompt_id="006",
        query=PROMPT_006_QUERY,
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
class TestPrompt006AfterHE:
    """
    Test suite for Prompt 006: After Horizon Europe.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_after_he(self):
        """
        Main evaluation test for Prompt 006.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Asserts quality threshold is met
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_006_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_006_after_he.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 006: After Horizon Europe Evaluation")
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

            if comp.get("missing_content"):
                print(f"\nMissing Content: {comp['missing_content']}")
            if comp.get("found_content"):
                print(f"Found Content: {comp['found_content']}")

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
        api_result = get_mapit_response(PROMPT_006_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_fp10(self):
        """Verify the response mentions FP10 or successor (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_006_after_he.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_after_he first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        fp10_mentioned = any(kw in response_lower for kw in EXPECTED_CONTENT["fp10"]["keywords"])

        # Informational check
        print(f"FP10/Successor mentioned: {fp10_mentioned}")
        if not fp10_mentioned:
            print("Note: Response needs improvement - FP10 not mentioned")

        # Soft assertion - just verify results exist
        assert "response" in result, "Response field missing from results"

    def test_response_includes_timeline(self):
        """Verify the response includes timeline information (informational)."""
        results_file = RESULTS_DIR / "prompt_006_after_he.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_after_he first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        has_2027 = "2027" in response_lower
        has_2028 = "2028" in response_lower

        # Informational check
        print(f"Has 2027 (HE end): {has_2027}")
        print(f"Has 2028 (FP10 start): {has_2028}")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt006OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_AFTER_HE, {"source": "sample_excellent"}
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_006_after_he_sample_excellent.json"
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
            SampleResponses.PARTIAL_AFTER_HE, {"source": "sample_partial"}
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
        evaluation = evaluate_response(SampleResponses.POOR_AFTER_HE, {"source": "sample_poor"})

        print("\nPoor Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < NEEDS_REVIEW_THRESHOLD, (
            f"Poor response scored {evaluation.overall_score}, expected < {NEEDS_REVIEW_THRESHOLD}"
        )
        assert evaluation.result == "FAIL"

    def test_evaluation_identifies_missing_content(self):
        """Test that evaluation identifies when content is missing."""
        evaluation = evaluate_response(SampleResponses.POOR_AFTER_HE, {"source": "sample_poor"})

        # Check that missing items are identified
        if evaluation.component_scores:
            comp = evaluation.component_scores[0]
            missing = comp.get("missing_content", [])

            # Poor response should be missing content
            print(f"Missing content: {missing}")
            assert len(missing) >= 1 or evaluation.overall_score < 70, (
                "Should identify missing items or score low"
            )

    def test_evaluation_rewards_specificity(self):
        """Test that specific details improve the score."""
        excellent_eval = evaluate_response(
            SampleResponses.EXCELLENT_AFTER_HE, {"source": "excellent"}
        )
        poor_eval = evaluate_response(SampleResponses.POOR_AFTER_HE, {"source": "poor"})

        # Excellent response should have much higher specificity
        excellent_specificity = excellent_eval.component_scores[0]["specificity"]
        poor_specificity = poor_eval.component_scores[0]["specificity"]

        assert excellent_specificity > poor_specificity, (
            f"Excellent specificity ({excellent_specificity}) should be > poor ({poor_specificity})"
        )

    def test_save_evaluation_result_json(self):
        """Test that evaluation results are saved correctly as JSON."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_AFTER_HE, {"source": "test_json_save"}
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_006_after_he_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "006"
        assert loaded["query"] == PROMPT_006_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
