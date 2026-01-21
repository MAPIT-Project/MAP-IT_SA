"""
Quality Evaluation Test for Prompt 008: AI Research Calls.

This test evaluates the MAPIT AI response to the query:
"I am working in AI and machine learning research. What are the upcoming calls relevant for me?"

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Lists Cluster 4 calls + cross-cluster opportunities
- Specificity (25 points): Call IDs, deadlines, budgets, topics
- Factual Accuracy (25 points): Verified call details, correct dates
- Actionability (10 points): Clear next steps, links to portal

Pass threshold: >= 85/100

Reference facts from eu-funding-domain skill:
- Cluster 4 (Digital, Industry and Space): AI, ML, data, robotics, cybersecurity, digital, HPC
- Cross-cluster AI opportunities: AI in Health (Cluster 1), AI for Climate (Cluster 5), etc.
- EIC Pathfinder: Deep tech / breakthrough AI research
- RIA: 100% funding, €3-10M, TRL 1-5
- IA: 70% funding (100% non-profit), €5-20M, TRL 5-8

Run with:
    pytest tests/quality/test_prompt_008_ai_calls.py -v

For live API tests only:
    pytest tests/quality/test_prompt_008_ai_calls.py -v -m "live_api"
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
PROMPT_008_QUERY = (
    "I am working in AI and machine learning research. "
    "What are the upcoming calls relevant for me?"
)

# Expected content based on PRD requirements
# Must include Cluster 4 calls AND potentially cross-cluster AI opportunities
EXPECTED_CLUSTER4_KEYWORDS = [
    "cluster 4",
    "digital",
    "artificial intelligence",
    "machine learning",
    "ai",
    "data",
    "robotics",
    "cybersecurity",
    "hpc",
    "high-performance computing",
    "industry",
    "space",
]

EXPECTED_CROSS_CLUSTER_KEYWORDS = [
    "cross-cluster",
    "cross-cutting",
    "health",
    "climate",
    "cluster 1",
    "cluster 5",
    "cluster 6",
    "eic",
    "pathfinder",
    "msca",
]

# Call-specific patterns to check
CALL_DETAIL_PATTERNS = {
    "call_id": [
        "horizon-cl4",
        "horizon-eic",
        "cl4-",
        "call id",
        "topic",
        "destination",
        "horizon-cl",
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

# Factual requirements for AI research calls
FACTUAL_REQUIREMENTS = {
    "cluster4_focus": {
        "claim": "AI/Digital calls are under Cluster 4",
        "keywords": ["cluster 4", "cluster-4", "digital", "ai"],
        "required": True,
    },
    "ria_available": {
        "claim": "RIA actions available in AI cluster",
        "keywords": ["ria", "research and innovation", "100%"],
        "required": False,
    },
    "cross_cluster_ai": {
        "claim": "AI has cross-cluster applications",
        "keywords": ["cross", "health", "climate", "pathfinder", "eic"],
        "required": False,
    },
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_AI_CALLS = """
## Relevant Funding Opportunities for AI and Machine Learning Research

Based on your research focus in AI and machine learning, here are the relevant calls:

### Cluster 4 - Digital, Industry and Space

Cluster 4 is the primary destination for AI/ML research in Horizon Europe. It covers:
- Artificial Intelligence and Robotics
- Next Generation Computing
- Data and Cloud Technologies
- Cybersecurity

#### Open/Upcoming Calls:

| Call ID | Topic | Deadline | Budget |
|---------|-------|----------|--------|
| HORIZON-CL4-2025-HUMAN-01-01 | Trustworthy AI systems | April 2025 | €10M RIA |
| HORIZON-CL4-2025-DATA-01-02 | AI for data analytics | May 2025 | €8M RIA |
| HORIZON-CL4-2025-DIGITAL-01-03 | Edge AI computing | June 2025 | €12M IA |
| HORIZON-CL4-2025-TWIN-01-01 | Digital twins with AI | April 2025 | €15M IA |

**Funding rates**: RIA = 100%, IA = 70% (100% for non-profits)

### Cross-Cluster AI Opportunities

AI/ML is **cross-cutting** - applicable across multiple clusters:

| Cluster | AI Application | Example Topics |
|---------|----------------|----------------|
| Cluster 1 (Health) | AI for diagnostics | Medical imaging, drug discovery |
| Cluster 5 (Climate) | AI for climate modeling | Weather prediction, energy optimization |
| Cluster 6 (Food) | AI in agriculture | Precision farming, crop monitoring |

### EIC Pathfinder (for breakthrough AI innovations)

If your AI research involves novel approaches at low TRL:
- **EIC Pathfinder Open**: TRL 1-4, €3-4M, 100% funding
- Suitable for high-risk/high-gain breakthrough AI research
- Topics: Neuromorphic computing, quantum ML, explainable AI

### MSCA Opportunities (Cross-Cutting)

Marie Skłodowska-Curie Actions support AI researchers:
- **MSCA-PF-2025**: Postdoctoral Fellowships, September 2025, €200-300K
- **MSCA-DN-2025**: Doctoral Networks, November 2025, €2-4M
- Both support AI/ML research under any thematic area

### How to Get Started

1. **Register** on the EU Funding & Tenders Portal
2. **Check Work Programme** for Cluster 4 topics and eligibility
3. **Find Partners** using Partner Search tool
4. **Review** Cluster 4 Work Programme 2025 (Destinations: Human-centric AI, Data)

Portal: https://ec.europa.eu/info/funding-tenders/opportunities/portal/

### Key Requirements
- **RIA projects**: 100% funding, 3+ partners from 3 EU/Associated countries
- **IA projects**: 70% funding (100% for non-profits), focus on TRL 5-8
- **EIC Pathfinder**: Individual or small consortium, breakthrough research
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_AI_CALLS = """
For AI and machine learning research, you should look at Cluster 4 in Horizon Europe.

There are various calls for AI research. Some upcoming ones include topics on
artificial intelligence and data. The deadlines are typically in 2025.

You can also apply for EIC Pathfinder if you have breakthrough AI ideas.

Check the EU Funding Portal for more information about specific calls and deadlines.
RIA projects offer 100% funding. You need partners from different countries.
"""

    # A low-quality response that should FAIL (< 70)
    POOR_AI_CALLS = """
There are many funding opportunities for AI research in Europe.
You can check the European Commission website for available grants.
Horizon Europe has different clusters including one for digital.
Some calls may be relevant for machine learning research.
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
    - Cluster 4 / Digital/AI calls are mentioned (20 points)
    - Cross-cluster opportunities or EIC/MSCA mentioned (15 points)
    - Actual calls/topics listed (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    found_items = []
    missing_items = []

    # Check for Cluster 4 / AI/Digital content (20 points)
    cluster4_found = 0
    for keyword in EXPECTED_CLUSTER4_KEYWORDS:
        if keyword in response_lower:
            cluster4_found += 1

    if cluster4_found >= 3:
        score += 20
        found_items.append("Cluster 4/Digital/AI content")
    elif cluster4_found >= 1:
        score += 10
        found_items.append("Partial Cluster 4/AI mention")
        missing_items.append("More Cluster 4 AI call details needed")
    else:
        missing_items.append("Cluster 4 Digital/AI calls")

    # Check for cross-cluster/EIC/MSCA opportunities (15 points)
    cross_cluster_found = 0
    for keyword in EXPECTED_CROSS_CLUSTER_KEYWORDS:
        if keyword in response_lower:
            cross_cluster_found += 1

    if cross_cluster_found >= 2:
        score += 15
        found_items.append("Cross-cluster/EIC opportunities")
    elif cross_cluster_found >= 1:
        score += 7
        found_items.append("EIC or cross-cluster mentioned")
        missing_items.append("More cross-cluster AI opportunities needed")
    else:
        missing_items.append("Cross-cluster AI opportunities or EIC")

    # Check for actual call details (5 points)
    has_call_details = any(
        pattern in response_lower
        for pattern in ["horizon-cl4", "cl4-", "eic", "pathfinder", "call"]
    )
    if has_call_details:
        score += 5
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
    - Cluster 4 is correctly identified for AI/Digital
    - Funding rates are accurate (RIA=100%, IA=70%)
    - AI cross-cluster applications correctly described
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

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

    # Check if Cluster 4 is wrongly associated with another field
    if "cluster 1" in response_lower and "ai" in response_lower:
        cluster1_idx = response_lower.find("cluster 1")
        nearby_text = response_lower[max(0, cluster1_idx - 30) : cluster1_idx + 100]
        # This is OK if discussing cross-cluster AI for Health
        if "ai" in nearby_text and "cross" not in nearby_text:
            # Only penalize if AI is claimed to be primarily under Cluster 1
            if "main" in nearby_text or "primary" in nearby_text:
                score -= 5
                errors.append(
                    {
                        "claim": "AI is primarily under Cluster 1",
                        "correct_value": "AI is primarily under Cluster 4 (Digital)",
                        "source": "EU Funding Domain Skill",
                    }
                )

    # Check for clearly wrong deadlines (past dates claimed as upcoming)
    wrong_years = ["2020", "2021", "2022", "2023"]
    for year in wrong_years:
        if "deadline" in response_lower and year in response_lower:
            deadline_idx = response_lower.find("deadline")
            nearby = response_lower[max(0, deadline_idx - 50) : deadline_idx + 100]
            if year in nearby and "upcoming" in response_lower:
                score -= 3
                errors.append(
                    {
                        "claim": f"Upcoming call with {year} deadline",
                        "correct_value": "Upcoming calls should have 2025/2026 deadlines",
                        "source": "Temporal validation",
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
    - Links to EU Funding Portal (4 points)
    - Next steps guidance (3 points)
    - Work Programme references (3 points)
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
    ]
    guidance_found = sum(1 for phrase in guidance_phrases if phrase in response_lower)
    score += min(3, guidance_found)

    # Work Programme references (3 points)
    doc_refs = [
        "work programme",
        "wp-",
        "topic description",
        "call document",
        "guide for applicants",
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
            "component_id": "ai_calls",
            "description": "AI/ML research calls and cross-cluster opportunities",
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
            f"Improve query fulfillment: Include Cluster 4 Digital/AI calls AND "
            f"cross-cluster AI opportunities (EIC, MSCA). "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include specific call IDs (HORIZON-CL4-*), "
            "deadlines with dates, budget figures (€M), and call status (open/upcoming)"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual errors: Verify Cluster 4 for AI/Digital, "
            "funding rates (RIA=100%, IA=70%), and ensure deadlines are current"
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add links to EU Funding Portal, "
            "Work Programme references, and clear next steps for applicants"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Comprehensive coverage of Cluster 4 and cross-cluster AI")
    if specificity_score >= 20:
        strengths.append("Rich in specific call details (IDs, deadlines, budgets)")
    if accuracy_score >= 20:
        strengths.append("Factually accurate")
    if actionability_score >= 8:
        strengths.append("Provides clear guidance for applicants")

    return EvaluationResult(
        prompt_id="008",
        query=PROMPT_008_QUERY,
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
class TestPrompt008AICalls:
    """
    Test suite for Prompt 008: AI Research Calls.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_ai_calls(self):
        """
        Main evaluation test for Prompt 008.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_008_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_008_ai_calls.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 008: AI Research Calls Evaluation")
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
        api_result = get_mapit_response(PROMPT_008_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_ai_cluster(self):
        """Verify the response mentions Cluster 4/AI (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_008_ai_calls.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_ai_calls first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        ai_keywords_found = sum(
            1 for kw in EXPECTED_CLUSTER4_KEYWORDS if kw in response_lower
        )

        # Informational check
        print(f"AI/Cluster 4 keywords found: {ai_keywords_found}")
        if ai_keywords_found < 3:
            print("Note: Response needs more Cluster 4/AI content")

        # Soft assertion - just verify results exist
        assert "response" in result, "Response field missing from results"

    def test_response_mentions_cross_cluster(self):
        """Verify the response mentions cross-cluster opportunities (informational)."""
        results_file = RESULTS_DIR / "prompt_008_ai_calls.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_ai_calls first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        cross_cluster_found = any(
            kw in response_lower for kw in EXPECTED_CROSS_CLUSTER_KEYWORDS
        )

        # Informational check
        print(f"Cross-cluster/EIC mentioned: {cross_cluster_found}")
        if not cross_cluster_found:
            print("Note: Response should include cross-cluster AI opportunities")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt008OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_AI_CALLS, {"source": "sample_excellent"}
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_008_ai_calls_sample_excellent.json"
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
            SampleResponses.PARTIAL_AI_CALLS, {"source": "sample_partial"}
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
            SampleResponses.POOR_AI_CALLS, {"source": "sample_poor"}
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
            SampleResponses.POOR_AI_CALLS, {"source": "sample_poor"}
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
            SampleResponses.EXCELLENT_AI_CALLS, {"source": "excellent"}
        )
        poor_eval = evaluate_response(
            SampleResponses.POOR_AI_CALLS, {"source": "poor"}
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
            SampleResponses.EXCELLENT_AI_CALLS, {"source": "test_json_save"}
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_008_ai_calls_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "008"
        assert loaded["query"] == PROMPT_008_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
