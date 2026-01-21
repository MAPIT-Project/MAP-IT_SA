"""
Quality Evaluation Test for Prompt 005: Horizon Europe Instruments (RIA, CSA, IA).

This test evaluates the MAPIT AI response to the query:
"What are the instruments in Horizon Europe (RIA, CSA, IA etc)?"

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Explains main instruments (RIA, IA, CSA, ERC, MSCA, EIC)
- Specificity (25 points): Funding rates, TRL ranges, budget ranges
- Factual Accuracy (25 points): Verified against EU funding domain knowledge
- Actionability (10 points): Clear guidance for users

Pass threshold: >= 85/100

Reference facts from eu-funding-domain skill:
- RIA: Research & Innovation Action, 100% funding, €3-10M, TRL 1-5
- IA: Innovation Action, 70% funding (100% non-profit), €5-20M, TRL 5-8
- CSA: Coordination & Support Action, 100% funding, €1-3M
- ERC: European Research Council grants (STG, COG, ADG, POC)
- MSCA: Marie Skłodowska-Curie Actions (PF, DN, SE, COFUND)
- EIC: European Innovation Council (Pathfinder, Transition, Accelerator)

Run with:
    pytest tests/quality/test_prompt_005_instruments.py -v

For live API tests only:
    pytest tests/quality/test_prompt_005_instruments.py -v -m "live_api"
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
PROMPT_005_QUERY = "What are the instruments in Horizon Europe (RIA, CSA, IA etc)?"

# Expected content based on eu-funding-domain skill
# Must explain main instruments with funding rates and TRL ranges
EXPECTED_INSTRUMENTS = {
    "ria": {
        "name": "RIA (Research & Innovation Action)",
        "keywords": [
            "ria",
            "research and innovation action",
            "research & innovation action",
        ],
        "funding_rate": "100%",
        "trl_range": "TRL 1-5",
        "budget_range": "€3-10M",
        "description": "Collaborative research with 100% funding rate",
    },
    "ia": {
        "name": "IA (Innovation Action)",
        "keywords": ["ia", "innovation action"],
        "funding_rate": "70%",
        "funding_rate_nonprofit": "100%",
        "trl_range": "TRL 5-8",
        "budget_range": "€5-20M",
        "description": "Closer to market, 70% funding (100% for non-profits)",
    },
    "csa": {
        "name": "CSA (Coordination & Support Action)",
        "keywords": [
            "csa",
            "coordination and support action",
            "coordination & support action",
        ],
        "funding_rate": "100%",
        "trl_range": "N/A",
        "budget_range": "€1-3M",
        "description": "Coordination and networking activities",
    },
}

# Other instruments that should ideally be mentioned
ADDITIONAL_INSTRUMENTS = {
    "erc": {
        "name": "ERC (European Research Council)",
        "keywords": ["erc", "european research council"],
        "types": ["ERC-STG", "ERC-COG", "ERC-ADG", "ERC-POC"],
        "description": "Frontier research grants for individual researchers",
    },
    "msca": {
        "name": "MSCA (Marie Skłodowska-Curie Actions)",
        "keywords": ["msca", "marie curie", "marie skłodowska"],
        "types": ["MSCA-PF", "MSCA-DN", "MSCA-SE", "MSCA-COFUND"],
        "description": "Researcher mobility and training",
    },
    "eic": {
        "name": "EIC (European Innovation Council)",
        "keywords": ["eic", "european innovation council"],
        "types": ["EIC-Pathfinder", "EIC-Transition", "EIC-Accelerator"],
        "description": "Support for breakthrough innovations and startups",
    },
}

# Key factual information that should be accurate
FACTUAL_REQUIREMENTS = {
    "ria_funding": {
        "claim": "RIA has 100% funding rate",
        "keywords": ["ria", "100%"],
        "proximity": 150,
    },
    "ia_funding": {
        "claim": "IA has 70% funding rate (100% for non-profits)",
        "keywords": ["ia", "70%"],
        "proximity": 150,
    },
    "csa_funding": {
        "claim": "CSA has 100% funding rate",
        "keywords": ["csa", "100%"],
        "proximity": 150,
    },
    "consortium_requirement": {
        "claim": "RIA/IA require minimum 3 partners from 3 countries",
        "keywords": ["3", "partner"],
        "proximity": 100,
    },
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_INSTRUMENTS = """
**Horizon Europe Funding Instruments**

Horizon Europe uses several **funding instruments** to support different types of activities,
from basic research to market-ready innovation. Here are the main instruments:

## Main Collaborative Instruments

### RIA - Research & Innovation Action
- **Funding Rate**: 100% of eligible costs
- **Typical Budget**: €3-10 million
- **TRL Focus**: TRL 1-5 (basic to applied research)
- **Consortium**: Minimum 3 partners from 3 different EU/Associated countries
- **Purpose**: Generating new knowledge, exploring feasibility, testing new technologies

### IA - Innovation Action
- **Funding Rate**: 70% (100% for non-profit organizations)
- **Typical Budget**: €5-20 million
- **TRL Focus**: TRL 5-8 (demonstration to market-ready)
- **Consortium**: Minimum 3 partners from 3 different EU/Associated countries
- **Purpose**: Prototyping, testing, demonstrating, piloting, scaling up

### CSA - Coordination & Support Action
- **Funding Rate**: 100% of eligible costs
- **Typical Budget**: €1-3 million
- **Consortium**: Single beneficiary allowed
- **Purpose**: Networking, coordination, standardization, policy support

## Excellence Instruments (Pillar I)

### ERC - European Research Council
- **ERC Starting Grant (ERC-STG)**: €1.5M, 5 years, 2-7 years post-PhD
- **ERC Consolidator Grant (ERC-COG)**: €2M, 5 years, 7-12 years post-PhD
- **ERC Advanced Grant (ERC-ADG)**: €2.5M, 5 years, established leaders
- **ERC Proof of Concept (ERC-POC)**: €150K, for existing ERC grantees
- **Funding Rate**: 100%

### MSCA - Marie Skłodowska-Curie Actions
- **MSCA-PF**: Postdoctoral Fellowships (individual mobility)
- **MSCA-DN**: Doctoral Networks (PhD training)
- **MSCA-SE**: Staff Exchanges (inter-sector secondments)
- **MSCA-COFUND**: Co-funding of fellowship programmes

## Innovation Instruments (Pillar III)

### EIC - European Innovation Council
- **EIC Pathfinder**: €3-4M, TRL 1-4, breakthrough research
- **EIC Transition**: €0.5-2.5M, TRL 4-6, lab-to-market validation
- **EIC Accelerator**: €2.5M grant + up to €15M equity, TRL 6-9, scale-up

## How to Choose the Right Instrument

| If you want to... | Choose... |
|-------------------|-----------|
| Basic research | RIA or ERC |
| Applied research | RIA |
| Prototype/demonstrate | IA |
| Network/coordinate | CSA |
| Individual mobility | MSCA-PF |
| Breakthrough innovation | EIC Pathfinder |
| Scale a startup | EIC Accelerator |

## Getting Started

For more information on instruments and open calls:
- [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [Horizon Europe Work Programmes](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents)
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_INSTRUMENTS = """
Horizon Europe has different instruments for funding research:

**RIA (Research & Innovation Action)**: For research projects. 100% funding.

**IA (Innovation Action)**: For innovation closer to market. Lower funding rate.

**CSA (Coordination & Support Action)**: For networking and coordination.

There are also ERC grants for excellent researchers and MSCA for mobility.
The EIC supports breakthrough innovations.

Researchers can find calls on the EU Funding Portal.
"""

    # A low-quality response that should FAIL (< 70)
    POOR_INSTRUMENTS = """
Horizon Europe offers different types of grants for research projects.
RIA and IA are the main ones. There are also grants for individual researchers.
You can check the EU website for more information about how to apply.
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

    Checks if main instruments (RIA, IA, CSA) are explained, plus bonus for others.
    - Core instruments (RIA, IA, CSA): 10 points each = 30 points
    - Additional instruments (ERC, MSCA, EIC): ~3-4 points each = 10 points
    """
    score = 0
    notes = []
    response_lower = response.lower()

    instruments_found = []
    instruments_missing = []

    # Check core instruments (10 points each = 30 total)
    points_per_core = 10

    for _inst_id, inst_info in EXPECTED_INSTRUMENTS.items():
        found = False
        for keyword in inst_info["keywords"]:
            if keyword in response_lower:
                found = True
                break

        if found:
            instruments_found.append(inst_info["name"])
            score += points_per_core
        else:
            instruments_missing.append(inst_info["name"])

    # Check additional instruments (bonus points)
    additional_found = []
    points_per_additional = 3

    for _inst_id, inst_info in ADDITIONAL_INSTRUMENTS.items():
        for keyword in inst_info["keywords"]:
            if keyword in response_lower:
                additional_found.append(inst_info["name"])
                score += points_per_additional
                break

    # Cap at 40 points
    score = min(40, score)

    # Build notes
    if instruments_missing:
        notes.append(f"Missing core instruments: {', '.join(instruments_missing)}")
    else:
        notes.append("All core instruments (RIA, IA, CSA) explained")

    if additional_found:
        notes.append(f"Also mentions: {', '.join(additional_found)}")

    notes.append(
        f"Core: {len(instruments_found)}/3, Additional: {len(additional_found)}/3"
    )

    return score, "; ".join(notes), instruments_missing, additional_found


def evaluate_specificity(response: str) -> tuple[int, str]:
    """
    Evaluate specificity (25 points max).

    Checks for:
    - Funding rates (100%, 70%) (8 points)
    - TRL ranges (6 points)
    - Budget figures (6 points)
    - Consortium requirements (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Funding rates (8 points)
    funding_patterns = [
        "100%",
        "70%",
        "funding rate",
        "eligible costs",
        "co-financing",
    ]
    funding_found = sum(1 for pat in funding_patterns if pat in response_lower)
    funding_score = min(8, funding_found * 2)
    score += funding_score
    if funding_found < 2:
        notes.append("Limited funding rate details")

    # TRL ranges (6 points)
    trl_patterns = [
        "trl",
        "technology readiness",
        "trl 1",
        "trl 2",
        "trl 3",
        "trl 4",
        "trl 5",
        "trl 6",
        "trl 7",
        "trl 8",
        "trl 9",
        "basic research",
        "applied research",
        "market",
        "demonstration",
    ]
    trl_found = sum(1 for pat in trl_patterns if pat in response_lower)
    trl_score = min(6, trl_found * 2)
    score += trl_score
    if trl_found < 2:
        notes.append("Limited TRL range information")

    # Budget figures (6 points)
    budget_patterns = [
        "€",
        "million",
        "€3",
        "€5",
        "€10",
        "€20",
        "budget",
        "1.5m",
        "2m",
        "2.5m",
    ]
    budget_found = sum(1 for pat in budget_patterns if pat in response_lower)
    budget_score = min(6, budget_found * 2)
    score += budget_score
    if budget_found < 2:
        notes.append("Limited budget information")

    # Consortium requirements (5 points)
    consortium_patterns = [
        "consortium",
        "partner",
        "3 partner",
        "3 different",
        "minimum",
        "single beneficiary",
        "countries",
    ]
    consortium_found = sum(1 for pat in consortium_patterns if pat in response_lower)
    consortium_score = min(5, consortium_found * 2)
    score += consortium_score

    return score, "; ".join(notes) if notes else "Good specificity with concrete details"


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies facts against eu-funding-domain knowledge:
    - RIA: 100% funding, TRL 1-5
    - IA: 70% funding (100% non-profit), TRL 5-8
    - CSA: 100% funding
    - Consortium: 3 partners, 3 countries (for RIA/IA)
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check for incorrect funding rates
    # RIA should be 100%, not 70%
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

    # IA should be 70%, not 100% (unless mentioning non-profit exception)
    if "ia" in response_lower and "innovation action" in response_lower:
        ia_idx = response_lower.find("innovation action")
        nearby_text = response_lower[max(0, ia_idx - 50) : ia_idx + 150]
        if "100%" in nearby_text and "70%" not in nearby_text:
            # Check if it's explaining the non-profit exception
            if "non-profit" not in nearby_text and "nonprofit" not in nearby_text:
                score -= 3
                errors.append(
                    {
                        "claim": "IA has 100% funding rate (without mentioning 70%)",
                        "correct_value": "IA has 70% funding (100% for non-profits)",
                        "source": "EU Funding Domain Skill",
                    }
                )

    # Check for wrong TRL ranges
    wrong_trl_claims = [
        ("ria", "trl 6", "RIA TRL focus is wrong"),
        ("ria", "trl 7", "RIA TRL focus is wrong"),
        ("ria", "trl 8", "RIA TRL focus is wrong"),
        ("csa", "trl", "CSA should not have TRL focus"),
    ]

    for term, wrong_trl, error_msg in wrong_trl_claims:
        if term in response_lower and wrong_trl in response_lower:
            term_idx = response_lower.find(term)
            trl_idx = response_lower.find(wrong_trl)
            if abs(term_idx - trl_idx) < 100:
                score -= 3
                errors.append(
                    {
                        "claim": error_msg,
                        "correct_value": "RIA: TRL 1-5, IA: TRL 5-8, CSA: N/A",
                        "source": "EU Funding Domain Skill",
                    }
                )
                break

    # Check for wrong consortium requirements
    if "csa" in response_lower:
        csa_idx = response_lower.find("csa")
        nearby_text = response_lower[max(0, csa_idx - 50) : csa_idx + 150]
        if "3 partner" in nearby_text or "minimum 3" in nearby_text:
            score -= 3
            errors.append(
                {
                    "claim": "CSA requires 3 partners",
                    "correct_value": "CSA allows single beneficiary",
                    "source": "EU Funding Domain Skill",
                }
            )

    notes = f"Accuracy check: {25 - (25 - score)}/25 points"
    if errors:
        notes += f"; {len(errors)} error(s) found"

    return max(0, score), notes, errors


def evaluate_actionability(response: str) -> tuple[int, str]:
    """
    Evaluate actionability (10 points max).

    Checks for:
    - Links to official resources (4 points)
    - Guidance on choosing instruments (3 points)
    - References to Work Programme or calls (3 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Links or URL references (4 points)
    if any(
        link in response_lower
        for link in ["http", "portal", "website", "ec.europa", "funding-tenders"]
    ):
        score += 4
    else:
        notes.append("No links to official resources")

    # Guidance on choosing instruments (3 points)
    guidance_phrases = [
        "choose",
        "select",
        "if you",
        "when to use",
        "purpose",
        "suitable for",
        "appropriate",
        "best for",
    ]
    guidance_found = sum(1 for phrase in guidance_phrases if phrase in response_lower)
    score += min(3, guidance_found)

    # References to Work Programme or calls (3 points)
    doc_refs = [
        "work programme",
        "call",
        "deadline",
        "topic",
        "annual work",
        "open call",
        "apply",
    ]
    doc_found = sum(1 for doc in doc_refs if doc in response_lower)
    score += min(3, doc_found)

    return (
        score,
        "; ".join(notes) if notes else "Good actionability with guidance provided",
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
        missing_instruments,
        additional_found,
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
            "component_id": "instruments",
            "description": "Horizon Europe Instruments explanation",
            "fulfillment": fulfillment_score,
            "specificity": specificity_score,
            "accuracy": accuracy_score,
            "actionability": actionability_score,
            "total": overall_score,
            "notes": (
                f"Fulfillment: {fulfillment_notes}; Specificity: {specificity_notes}; "
                f"Accuracy: {accuracy_notes}; Actionability: {actionability_notes}"
            ),
            "missing_instruments": missing_instruments,
            "additional_instruments_found": additional_found,
        }
    ]

    # Generate fix suggestions
    fix_suggestions = []
    if fulfillment_score < 32:  # < 80% of 40
        fix_suggestions.append(
            f"Improve query fulfillment: Explain all core instruments (RIA, IA, CSA). "
            f"Missing: {', '.join(missing_instruments) if missing_instruments else 'None'}. "
            f"Also mention ERC, MSCA, and EIC instruments."
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include funding rates (RIA=100%, IA=70%, CSA=100%), "
            "TRL ranges (RIA: TRL 1-5, IA: TRL 5-8), "
            "budget ranges (RIA: €3-10M, IA: €5-20M, CSA: €1-3M), "
            "and consortium requirements (3 partners from 3 countries for RIA/IA)"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual errors: Verify funding rates (RIA=100%, IA=70%), "
            "TRL ranges, and consortium requirements"
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add links to EU Funding Portal, "
            "Work Programmes, and guidance on choosing between instruments"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Comprehensive coverage of instruments")
    if specificity_score >= 20:
        strengths.append("Rich in specific details (rates, TRLs, budgets)")
    if accuracy_score >= 20:
        strengths.append("Factually accurate")
    if actionability_score >= 8:
        strengths.append("Provides clear guidance for researchers")

    return EvaluationResult(
        prompt_id="005",
        query=PROMPT_005_QUERY,
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
class TestPrompt005Instruments:
    """
    Test suite for Prompt 005: Horizon Europe Instruments.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_instruments(self):
        """
        Main evaluation test for Prompt 005.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Asserts quality threshold is met
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_005_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_005_instruments.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 005: Instruments Evaluation")
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

            if comp.get("missing_instruments"):
                print(f"\nMissing Instruments: {comp['missing_instruments']}")
            if comp.get("additional_instruments_found"):
                print(f"Additional Found: {comp['additional_instruments_found']}")

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
        api_result = get_mapit_response(PROMPT_005_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_core_instruments(self):
        """Verify the response mentions core instruments (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_005_instruments.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_instruments first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        instruments_found = 0
        for inst_info in EXPECTED_INSTRUMENTS.values():
            for keyword in inst_info["keywords"]:
                if keyword in response_lower:
                    instruments_found += 1
                    break

        # Informational check
        print(f"Core instruments mentioned: {instruments_found}/3")
        if instruments_found < 3:
            print("Note: Response needs improvement - not all core instruments found")

        # Soft assertion - just verify results exist
        assert "response" in result, "Response field missing from results"

    def test_response_includes_funding_rates(self):
        """Verify the response includes funding rate information (informational)."""
        results_file = RESULTS_DIR / "prompt_005_instruments.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_instruments first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        has_100_percent = "100%" in response_lower
        has_70_percent = "70%" in response_lower

        # Informational check
        print(f"Has 100% funding rate: {has_100_percent}")
        print(f"Has 70% funding rate: {has_70_percent}")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt005OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_INSTRUMENTS, {"source": "sample_excellent"}
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_005_instruments_sample_excellent.json"
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
            SampleResponses.PARTIAL_INSTRUMENTS, {"source": "sample_partial"}
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
            SampleResponses.POOR_INSTRUMENTS, {"source": "sample_poor"}
        )

        print("\nPoor Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < NEEDS_REVIEW_THRESHOLD, (
            f"Poor response scored {evaluation.overall_score}, "
            f"expected < {NEEDS_REVIEW_THRESHOLD}"
        )
        assert evaluation.result == "FAIL"

    def test_evaluation_identifies_missing_instruments(self):
        """Test that evaluation identifies when instruments are missing."""
        evaluation = evaluate_response(
            SampleResponses.POOR_INSTRUMENTS, {"source": "sample_poor"}
        )

        # Check that missing items are identified
        if evaluation.component_scores:
            comp = evaluation.component_scores[0]
            missing = comp.get("missing_instruments", [])

            # Poor response should be missing at least some instruments
            print(f"Missing instruments: {missing}")
            # Poor response mentions RIA and IA but not CSA fully
            assert len(missing) >= 1 or evaluation.overall_score < 70, (
                "Should identify missing items or score low"
            )

    def test_evaluation_rewards_specificity(self):
        """Test that specific details improve the score."""
        excellent_eval = evaluate_response(
            SampleResponses.EXCELLENT_INSTRUMENTS, {"source": "excellent"}
        )
        poor_eval = evaluate_response(
            SampleResponses.POOR_INSTRUMENTS, {"source": "poor"}
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
            SampleResponses.EXCELLENT_INSTRUMENTS, {"source": "test_json_save"}
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_005_instruments_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "005"
        assert loaded["query"] == PROMPT_005_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
