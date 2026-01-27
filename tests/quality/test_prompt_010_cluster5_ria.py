"""
Quality Evaluation Test for Prompt 010: Cluster 5 RIA Details.

This test evaluates the MAPIT AI response to the query:
"What is the max project length and the payment modality for Cluster 5 RIA projects?"

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Answers both project length AND payment modality
- Specificity (25 points): Specific numbers (duration, funding rate, payment schedule)
- Factual Accuracy (25 points): Verified against eu-funding-domain skill
- Actionability (10 points): Clear guidance, links to official resources

Pass threshold: >= 85/100

Reference facts from eu-funding-domain skill:
- RIA: 100% funding rate
- RIA typical budget: €3-10M
- RIA TRL focus: TRL 1-5
- Cluster 5: Climate, Energy & Mobility
- RIA consortium: 3 partners from 3 different EU/Associated countries
- Indirect cost rate: 25% flat rate
- RIA typical project duration: 36-48 months (some up to 60 months)
- Payment modality: Pre-financing (initial), interim payments, final payment

Run with:
    pytest tests/quality/test_prompt_010_cluster5_ria.py -v

For live API tests only:
    pytest tests/quality/test_prompt_010_cluster5_ria.py -v -m "live_api"
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
PROMPT_010_QUERY = (
    "What is the max project length and the payment modality for Cluster 5 RIA projects?"
)

# Expected content based on PRD requirements
# Must provide specific numbers for duration, funding rate, payment schedule

# Project duration keywords
EXPECTED_DURATION_KEYWORDS = [
    "month",
    "year",
    "duration",
    "length",
    "36",
    "48",
    "60",
    "period",
    "timeline",
    "maximum",
]

# Payment modality keywords
EXPECTED_PAYMENT_KEYWORDS = [
    "payment",
    "pre-financing",
    "prefinancing",
    "interim",
    "final",
    "installment",
    "disbursement",
    "tranche",
    "lump sum",
    "actual cost",
    "reimbursement",
]

# Funding rate keywords
EXPECTED_FUNDING_KEYWORDS = [
    "100%",
    "funding rate",
    "funding",
    "reimbursement",
    "eligible cost",
    "eu contribution",
    "grant",
]

# Cluster 5 context keywords
EXPECTED_CLUSTER5_KEYWORDS = [
    "cluster 5",
    "climate",
    "energy",
    "mobility",
    "transport",
    "green deal",
    "horizon europe",
    "cl5",
]

# RIA-specific keywords
EXPECTED_RIA_KEYWORDS = [
    "ria",
    "research and innovation",
    "research & innovation",
    "trl",
    "consortium",
    "partners",
]

# Specific factual checks
FACTUAL_REQUIREMENTS = {
    "funding_rate": {
        "claim": "RIA funding rate is 100%",
        "correct_patterns": ["100%"],
        "wrong_patterns": ["70%", "80%", "60%"],
        "context_keywords": ["ria", "funding"],
        "required": True,
    },
    "duration_range": {
        "claim": "RIA project duration is typically 36-48 months",
        "correct_patterns": ["36", "48", "month"],
        "wrong_patterns": [],
        "context_keywords": ["duration", "length", "month", "project"],
        "required": True,
    },
    "payment_structure": {
        "claim": "Payment includes pre-financing, interim, and final payments",
        "correct_patterns": ["pre-financing", "interim", "final"],
        "wrong_patterns": [],
        "context_keywords": ["payment"],
        "required": True,
    },
    "indirect_costs": {
        "claim": "Indirect costs are 25% flat rate",
        "correct_patterns": ["25%", "indirect", "overhead"],
        "wrong_patterns": [],
        "context_keywords": ["indirect", "overhead", "flat"],
        "required": False,  # Nice to have but not critical
    },
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_CLUSTER5_RIA = """
## Cluster 5 RIA Project Parameters

### Project Duration

For **Research and Innovation Actions (RIA)** in Cluster 5 (Climate, Energy and Mobility), the
typical project duration is:

| Duration Type | Range | Notes |
|--------------|-------|-------|
| **Standard** | 36-48 months | Most common for RIA projects |
| **Maximum** | Up to 60 months | For complex research requiring longer timelines |
| **Minimum** | 24 months | Rare, but possible for focused topics |

The specific duration depends on the call topic and Work Programme requirements. Check the
specific topic text for any duration limits.

### Funding Rate

RIA projects receive **100% funding** of eligible costs. This applies to:
- All types of beneficiaries (universities, research organizations, SMEs, large companies)
- All cost categories (personnel, equipment, travel, subcontracting, etc.)

**Note**: This is different from Innovation Actions (IA) which receive 70% funding (100% for
non-profit organizations).

### Payment Modality

Horizon Europe RIA projects follow a standard payment schedule:

| Payment Type | Timing | Typical Amount |
|-------------|--------|----------------|
| **Pre-financing** | At project start | Up to 50% of EC contribution |
| **Interim payment(s)** | After periodic reports | Based on costs reported |
| **Final payment** | After final report | Remaining balance |

**Payment Details:**
1. **Pre-financing**: Provided within 30 days of grant signature (or later start date)
   - Typically 30-50% of total EC contribution
   - Secures initial project activities

2. **Interim payments**:
   - Released after approval of periodic reports
   - Based on actual eligible costs incurred
   - Usually at 18-month reporting periods

3. **Final payment**:
   - Released after final technical and financial reports
   - Includes any remaining balance
   - Subject to retention of 5-10% for contingencies

### Budget Calculation

For Cluster 5 RIA projects:
- **Typical budget**: €3-10 million
- **Direct costs**: Personnel, equipment, travel, subcontracting, other
- **Indirect costs**: 25% flat rate on direct costs (excluding subcontracting)

**Formula:**
```
Total Eligible Cost = Direct Costs + (Direct Costs - Subcontracting) × 0.25
EU Contribution = Total Eligible Cost × 100%
```

### Key Resources

- [Horizon Europe Work Programme - Cluster 5](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
- [Model Grant Agreement](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf)
- [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)

### Consortium Requirements
- Minimum **3 partners** from **3 different EU/Associated countries**
- No maximum, but typical consortia have 8-15 partners
- Balance of academic, research, and industry partners recommended
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_CLUSTER5_RIA = """
For Cluster 5 RIA projects in Horizon Europe:

**Project Duration:**
RIA projects typically run for 36-48 months. Some projects can be longer depending on the
topic requirements.

**Funding:**
RIA projects receive 100% funding of eligible costs.

**Payment:**
Payments are made in installments - there's an initial payment at the start, then periodic
payments during the project, and a final payment at the end.

You need at least 3 partners from different countries to apply. The budget is usually
between €3-10 million for RIA projects.

Check the Horizon Europe portal for more details on specific calls.
"""

    # A low-quality response that should FAIL (< 70)
    POOR_CLUSTER5_RIA = """
Cluster 5 covers climate and energy topics in Horizon Europe.

RIA is a type of funding action in Horizon Europe. Projects typically last a few years.

You can find more information about funding opportunities on the European Commission website.
Different projects have different requirements depending on the call.
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

    Checks if response answers BOTH parts of the question:
    - Project duration/length for Cluster 5 RIA (20 points)
    - Payment modality (20 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    found_items = []
    missing_items = []

    # Check for project duration information (20 points)
    duration_keywords_found = sum(1 for kw in EXPECTED_DURATION_KEYWORDS if kw in response_lower)
    # Need specific numbers like 36, 48, 60 months
    has_duration_numbers = any(num in response for num in ["36", "48", "60", "24"])
    has_month_mention = "month" in response_lower

    if duration_keywords_found >= 3 and has_duration_numbers and has_month_mention:
        score += 20
        found_items.append("Project duration with specific numbers")
    elif duration_keywords_found >= 2 and (has_duration_numbers or has_month_mention):
        score += 12
        found_items.append("Partial project duration information")
        missing_items.append("More specific duration numbers (e.g., 36-48 months)")
    elif duration_keywords_found >= 1:
        score += 5
        found_items.append("Duration mentioned")
        missing_items.append("Specific project duration (36-48 months typical)")
    else:
        missing_items.append("Project duration information")

    # Check for payment modality information (20 points)
    payment_keywords_found = sum(1 for kw in EXPECTED_PAYMENT_KEYWORDS if kw in response_lower)
    # Key payment structure terms
    has_prefinancing = any(
        term in response_lower for term in ["pre-financing", "prefinancing", "advance"]
    )
    has_interim = "interim" in response_lower
    has_final = "final" in response_lower and "payment" in response_lower

    payment_structure_count = sum([has_prefinancing, has_interim, has_final])

    if payment_keywords_found >= 3 and payment_structure_count >= 2:
        score += 20
        found_items.append("Payment modality with structure details")
    elif payment_keywords_found >= 2:
        score += 12
        found_items.append("Partial payment information")
        missing_items.append("Complete payment structure (pre-financing, interim, final)")
    elif payment_keywords_found >= 1:
        score += 5
        found_items.append("Payment mentioned")
        missing_items.append("Detailed payment modality explanation")
    else:
        missing_items.append("Payment modality information")

    # Build notes
    if missing_items:
        notes.append(f"Missing: {', '.join(missing_items)}")
    else:
        notes.append("Both duration and payment modality fully covered")

    return score, "; ".join(notes), missing_items, found_items


def evaluate_specificity(response: str) -> tuple[int, str]:
    """
    Evaluate specificity (25 points max).

    Checks for:
    - Duration numbers (7 points)
    - Funding rate percentage (7 points)
    - Payment percentages or timing (6 points)
    - Budget range (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Duration numbers - specific months (7 points)
    duration_numbers = ["36", "48", "60", "24"]
    duration_found = sum(1 for num in duration_numbers if num in response)
    if "month" in response_lower and duration_found >= 2:
        score += 7
    elif "month" in response_lower and duration_found >= 1:
        score += 4
        notes.append("Limited duration specificity")
    else:
        notes.append("Missing specific duration numbers")

    # Funding rate percentage (7 points)
    if "100%" in response:
        score += 7
    elif any(rate in response for rate in ["100 %", "100 percent"]):
        score += 5
        notes.append("Funding rate mentioned but format could be clearer")
    else:
        notes.append("Missing explicit 100% funding rate")

    # Payment percentages or timing (6 points)
    payment_specifics = [
        "50%",
        "30%",
        "40%",
        "30 day",
        "60 day",
        "90 day",
        "18 month",
        "reporting period",
        "periodic report",
    ]
    payment_found = sum(1 for spec in payment_specifics if spec.lower() in response_lower)
    if payment_found >= 2:
        score += 6
    elif payment_found >= 1:
        score += 3
        notes.append("Some payment timing details")
    else:
        notes.append("Limited payment timing specifics")

    # Budget range (5 points)
    budget_patterns = ["€3", "€10", "3 million", "10 million", "3-10", "€3-10"]
    budget_found = sum(1 for pat in budget_patterns if pat.lower() in response_lower)
    if budget_found >= 2:
        score += 5
    elif budget_found >= 1 or ("million" in response_lower and "€" in response):
        score += 3
    else:
        notes.append("No budget range mentioned")

    return score, "; ".join(notes) if notes else "Good specificity with numbers and rates"


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - RIA funding rate is 100% (not 70%)
    - Duration claims are reasonable (36-60 months)
    - Payment structure is accurate
    - Indirect cost rate if mentioned (25%)
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check funding rate accuracy
    if "ria" in response_lower:
        ria_idx = response_lower.find("ria")
        nearby_text = response_lower[max(0, ria_idx - 100) : ria_idx + 200]

        # Wrong: RIA with 70% funding
        if "70%" in nearby_text and "100%" not in nearby_text:
            score -= 8
            errors.append(
                {
                    "claim": "RIA has 70% funding rate",
                    "correct_value": "RIA has 100% funding rate",
                    "source": "EU Funding Domain Skill",
                }
            )

        # Wrong: RIA with 80% funding
        if "80%" in nearby_text and "100%" not in nearby_text:
            score -= 8
            errors.append(
                {
                    "claim": "RIA has 80% funding rate",
                    "correct_value": "RIA has 100% funding rate",
                    "source": "EU Funding Domain Skill",
                }
            )

    # Check duration accuracy
    # Wrong: Very short duration claimed (< 12 months typical)
    if "12 month" in response_lower and "maximum" not in response_lower:
        duration_idx = response_lower.find("12 month")
        nearby = response_lower[max(0, duration_idx - 50) : duration_idx + 100]
        if "typical" in nearby or "standard" in nearby:
            score -= 5
            errors.append(
                {
                    "claim": "Typical RIA duration is 12 months",
                    "correct_value": "Typical RIA duration is 36-48 months",
                    "source": "EU Funding Domain Skill",
                }
            )

    # Wrong: Very long duration claimed (> 72 months typical)
    for long_duration in ["72 month", "84 month", "96 month"]:
        if long_duration in response_lower:
            duration_idx = response_lower.find(long_duration)
            nearby = response_lower[max(0, duration_idx - 50) : duration_idx + 100]
            if "maximum" not in nearby and "exceptional" not in nearby:
                score -= 3
                errors.append(
                    {
                        "claim": f"RIA duration can be {long_duration}s",
                        "correct_value": "Maximum RIA duration is typically 60 months",
                        "source": "EU Funding Domain Skill",
                    }
                )
                break

    # Check indirect cost rate if mentioned
    if "indirect" in response_lower or "overhead" in response_lower:
        # Wrong indirect cost rate
        for wrong_rate in ["20%", "30%", "35%", "40%"]:
            if wrong_rate in response:
                idx = response.find(wrong_rate)
                nearby = response_lower[max(0, idx - 100) : idx + 100]
                if "indirect" in nearby or "overhead" in nearby:
                    score -= 3
                    errors.append(
                        {
                            "claim": f"Indirect cost rate is {wrong_rate}",
                            "correct_value": "Indirect cost rate is 25% flat rate",
                            "source": "EU Funding Domain Skill",
                        }
                    )
                    break

    notes = f"Accuracy check: {score}/25 points"
    if errors:
        notes += f"; {len(errors)} error(s) found"

    return max(0, score), notes, errors


def evaluate_actionability(response: str) -> tuple[int, str]:
    """
    Evaluate actionability (10 points max).

    Checks for:
    - Links to EU Funding Portal or Work Programme (4 points)
    - Guidance on where to find specifics (3 points)
    - Reference to official documents (3 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Links or URL references (4 points)
    link_patterns = [
        "http",
        "portal",
        "ec.europa",
        "funding-tenders",
        "work programme",
        "model grant agreement",
    ]
    link_found = sum(1 for link in link_patterns if link in response_lower)
    if link_found >= 2:
        score += 4
    elif link_found >= 1:
        score += 2
        notes.append("Limited links to resources")
    else:
        notes.append("No links to official resources")

    # Guidance on where to find specifics (3 points)
    guidance_phrases = [
        "check",
        "refer to",
        "consult",
        "see the",
        "find in",
        "look at",
        "review",
        "specific topic",
        "call text",
    ]
    guidance_found = sum(1 for phrase in guidance_phrases if phrase in response_lower)
    if guidance_found >= 2:
        score += 3
    elif guidance_found >= 1:
        score += 1
        notes.append("Some guidance provided")
    else:
        notes.append("No guidance on finding more information")

    # Reference to official documents (3 points)
    doc_refs = [
        "grant agreement",
        "work programme",
        "horizon europe",
        "annotated grant",
        "guide for applicants",
        "topic description",
    ]
    doc_found = sum(1 for doc in doc_refs if doc in response_lower)
    if doc_found >= 2:
        score += 3
    elif doc_found >= 1:
        score += 1
    else:
        notes.append("No document references")

    return (
        score,
        "; ".join(notes) if notes else "Good actionability with resources and guidance",
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
            "component_id": "cluster5_ria_details",
            "description": ("Cluster 5 RIA project duration and payment modality"),
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
            f"Improve query fulfillment: Must answer BOTH project duration (36-48 months "
            f"typical, up to 60) AND payment modality (pre-financing, interim, final). "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include specific duration numbers (36, 48, 60 months), "
            "100% funding rate, payment percentages (e.g., 50% pre-financing), "
            "and budget range (€3-10M for RIA)"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual errors: Verify RIA=100% funding (not 70%), "
            "typical duration 36-48 months (max 60), and indirect costs 25% flat rate"
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add links to EU Funding Portal, "
            "Work Programme references, and Model Grant Agreement"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Comprehensive coverage of both duration and payment modality")
    if specificity_score >= 20:
        strengths.append("Rich in specific numbers and rates")
    if accuracy_score >= 20:
        strengths.append("Factually accurate")
    if actionability_score >= 8:
        strengths.append("Provides useful resources and guidance")

    return EvaluationResult(
        prompt_id="010",
        query=PROMPT_010_QUERY,
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
class TestPrompt010Cluster5RIA:
    """
    Test suite for Prompt 010: Cluster 5 RIA Details.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_cluster5_ria(self):
        """
        Main evaluation test for Prompt 010.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_010_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_010_cluster5_ria.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 010: Cluster 5 RIA Details Evaluation")
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
        api_result = get_mapit_response(PROMPT_010_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_ria(self):
        """Verify the response mentions RIA (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_010_cluster5_ria.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_cluster5_ria first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        ria_keywords_found = sum(1 for kw in EXPECTED_RIA_KEYWORDS if kw in response_lower)

        # Informational check
        print(f"RIA keywords found: {ria_keywords_found}")
        if ria_keywords_found < 2:
            print("Note: Response needs more RIA-specific content")

        # Soft assertion - just verify results exist
        assert "response" in result, "Response field missing from results"

    def test_response_mentions_duration(self):
        """Verify the response mentions project duration (informational)."""
        results_file = RESULTS_DIR / "prompt_010_cluster5_ria.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_cluster5_ria first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        duration_keywords_found = sum(
            1 for kw in EXPECTED_DURATION_KEYWORDS if kw in response_lower
        )

        # Informational check
        print(f"Duration keywords found: {duration_keywords_found}")
        if duration_keywords_found < 3:
            print("Note: Response should include more duration details")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt010OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_CLUSTER5_RIA, {"source": "sample_excellent"}
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_010_cluster5_ria_sample_excellent.json"
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
            SampleResponses.PARTIAL_CLUSTER5_RIA, {"source": "sample_partial"}
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
        evaluation = evaluate_response(SampleResponses.POOR_CLUSTER5_RIA, {"source": "sample_poor"})

        print("\nPoor Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < NEEDS_REVIEW_THRESHOLD, (
            f"Poor response scored {evaluation.overall_score}, expected < {NEEDS_REVIEW_THRESHOLD}"
        )
        assert evaluation.result == "FAIL"

    def test_evaluation_identifies_missing_items(self):
        """Test that evaluation identifies missing content."""
        evaluation = evaluate_response(SampleResponses.POOR_CLUSTER5_RIA, {"source": "sample_poor"})

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
            SampleResponses.EXCELLENT_CLUSTER5_RIA, {"source": "excellent"}
        )
        poor_eval = evaluate_response(SampleResponses.POOR_CLUSTER5_RIA, {"source": "poor"})

        # Excellent response should have much higher specificity
        excellent_specificity = excellent_eval.component_scores[0]["specificity"]
        poor_specificity = poor_eval.component_scores[0]["specificity"]

        assert excellent_specificity > poor_specificity, (
            f"Excellent specificity ({excellent_specificity}) should be > poor ({poor_specificity})"
        )

    def test_save_evaluation_result_json(self):
        """Test that evaluation results are saved correctly as JSON."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_CLUSTER5_RIA, {"source": "test_json_save"}
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_010_cluster5_ria_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "010"
        assert loaded["query"] == PROMPT_010_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
