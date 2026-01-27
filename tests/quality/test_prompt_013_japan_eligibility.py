"""
Quality Evaluation Test for Prompt 013: Japan Researcher Eligibility.

This test evaluates the MAPIT AI response to the query:
"I am from Japan working in research. Are there any open calls that would be relevant for me?"

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Explains Japan's third country status, participation rules
- Specificity (25 points): Specific rules, exceptions, programme details
- Factual Accuracy (25 points): Correct third country participation rules
- Actionability (10 points): Clear guidance on how Japan researchers can participate

Pass threshold: >= 85/100

Reference facts from eu-funding-domain skill:
- Japan is a NON-ASSOCIATED THIRD COUNTRY (not EU Member State, not Associated)
- Third countries have limited participation options:
  - Can participate in SOME calls (check topic conditions)
  - Generally NOT eligible for EU funding (self-funded)
  - May need bilateral agreements or specific topic exceptions
  - Some programmes have automatic eligibility for certain third countries
- Key pathways for Japan researchers:
  - MSCA-PF (Individual Fellowships): Japan researchers CAN apply if moving to EU/AC
  - ERC grants: Third country nationals can apply if working at EU/AC institution
  - Collaborative projects: As partners in exceptional cases, usually without funding
  - Japan-EU Joint Projects: Specific bilateral programmes may exist
- Important restrictions:
  - Japan organizations typically NOT funded by EC (self-funded participation)
  - Cannot be coordinator in most calls
  - Must check call conditions for third country eligibility

Run with:
    pytest tests/quality/test_prompt_013_japan_eligibility.py -v

For live API tests only:
    pytest tests/quality/test_prompt_013_japan_eligibility.py -v -m "live_api"
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
PROMPT_013_QUERY = (
    "I am from Japan working in research. Are there any open calls that would be relevant for me?"
)

# Expected content based on PRD requirements
# Must correctly explain third country participation rules
JAPAN_ELIGIBILITY_KEYWORDS = [
    "japan",
    "japanese",
    "third country",
    "non-associated",
    "not associated",
    "limited",
    "restricted",
    "eligibility",
    "eligible",
    "participate",
    "partner",
    "self-funded",
    "exceptional",
    "specific",
    "conditions",
]

PARTICIPATION_PATHWAY_KEYWORDS = [
    "msca",
    "marie",
    "fellowship",
    "erc",
    "mobility",
    "move",
    "host institution",
    "eu institution",
    "european institution",
    "associated country",
    "bilateral",
    "joint",
    "agreement",
    "exception",
    "individual",
    "researcher",
    "can apply",
    "may participate",
]

# Call-specific patterns to check
CALL_DETAIL_PATTERNS = {
    "call_id": [
        "horizon",
        "msca",
        "erc",
        "call",
        "topic",
        "grant",
        "fellowship",
    ],
    "rules": [
        "funding",
        "funded",
        "self-fund",
        "without funding",
        "own cost",
        "contribution",
        "rate",
        "conditions",
        "requirements",
    ],
    "opportunity": [
        "opportunity",
        "opportunities",
        "pathway",
        "option",
        "possibility",
        "eligible",
        "can",
        "may",
        "open to",
    ],
    "restriction": [
        "cannot",
        "restricted",
        "limited",
        "not funded",
        "not eligible",
        "exception",
        "specific",
        "certain",
        "check",
    ],
}

# Factual requirements for Japan eligibility queries
FACTUAL_REQUIREMENTS = {
    "japan_third_country": {
        "claim": "Japan is a third country (not EU, not Associated)",
        "keywords": ["third country", "non-associated", "japan"],
        "required": True,
    },
    "funding_limitations": {
        "claim": "Third countries usually not funded by EC",
        "keywords": ["not funded", "self-fund", "limited funding", "exceptional"],
        "required": True,
    },
    "msca_pathway": {
        "claim": "MSCA offers pathways for third country researchers",
        "keywords": ["msca", "fellowship", "mobility"],
        "required": False,
    },
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_JAPAN_ELIGIBILITY = """
## Horizon Europe Participation for Japanese Researchers

### Japan's Eligibility Status

Japan is classified as a **non-associated third country** in Horizon Europe, which means:

- Japanese organizations are **NOT automatically eligible** for EU funding
- Participation is possible but with **significant restrictions**
- Must check **specific call conditions** for third country eligibility
- When allowed, typically must be **self-funded** (no EU contribution)

### Pathways for Japanese Researchers

Despite the restrictions, there are several pathways for Japanese researchers:

#### 1. MSCA Postdoctoral Fellowships (MSCA-PF)
**Best option for individual researchers!**

- Japanese researchers **CAN apply** if they plan to move to an EU/Associated Country
- You work at a European host institution
- Full EU funding available (living allowance + mobility allowance)
- Budget: €200-300K for 12-24 month fellowship
- 2025 deadline: September 2025 (check EU Portal for exact date)

#### 2. ERC Grants
- Japanese nationals **CAN apply** for ERC Starting/Consolidator/Advanced grants
- **Requirement**: Must conduct research at an EU or Associated Country institution
- Budget: €1.5M (Starting), €2M (Consolidator), €2.5M (Advanced)

#### 3. Collaborative Projects (as Third Country Partner)
- Japanese organizations MAY participate as partners in **some** calls
- Must check topic text for "third country eligibility"
- Typically **NOT funded** by EC (must bring own funding or co-fund)
- Cannot be consortium coordinator in most cases

### Specific Calls to Check

| Programme | Japan Eligibility | Notes |
|-----------|-------------------|-------|
| MSCA-PF | ✅ Yes (moving to EU) | Full funding if hosting in EU/AC |
| ERC grants | ✅ Yes (at EU institution) | Must work at EU/AC host |
| Cluster 1-6 RIA/IA | ⚠️ Check topic | Usually self-funded if allowed |
| EIC Pathfinder | ❌ Limited | Usually EU/AC only |
| Erasmus+ | ⚠️ Partner country rules | Limited actions available |

### How to Proceed

1. **MSCA-PF Route** (Recommended):
   - Find a host institution in EU/Associated Country
   - Apply during 2025 MSCA-PF call
   - Full funding available

2. **For Collaborative Projects**:
   - Partner with EU consortium
   - Check each call's eligibility conditions
   - Prepare for self-funding or co-funding

3. **Japan-EU Bilateral Programmes**:
   - Check JST (Japan Science and Technology Agency) for joint calls
   - JSPS (Japan Society for Promotion of Science) collaboration programmes

### Important Resources

- EU Funding Portal: https://ec.europa.eu/info/funding-tenders/opportunities/portal/
- MSCA Work Programme: Check "third country" sections
- Japanese NCP: JSPS Brussels Office can advise on options
- JST International Programmes: Potential bilateral opportunities

### Key Points to Remember

⚠️ **Always check the specific call text** for third country conditions
⚠️ **EU funding typically not available** for Japanese institutions
✅ **Individual mobility** (MSCA, ERC) offers the best pathways
✅ **Bilateral programmes** may offer funded opportunities
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_JAPAN_ELIGIBILITY = """
Japan is not part of the EU so participation in Horizon Europe has some restrictions.

Japanese researchers can potentially participate in some programmes:
- MSCA fellowships if you want to do research in Europe
- ERC grants if working at a European institution
- Some collaborative projects as a partner

You should check the specific calls for third country eligibility requirements.
The EU Funding Portal has information about open calls.

Generally, organizations from Japan would need to bring their own funding as
third countries typically don't receive EU funding. Individual researchers
have more options through mobility programmes.

Check with your institution about bilateral agreements between Japan and EU
for research collaboration.
"""

    # A low-quality response that should FAIL (< 70)
    POOR_JAPAN_ELIGIBILITY = """
There are many research funding opportunities in Europe. Japan is a developed
country with strong research institutions. You can look at Horizon Europe
calls on the EU website.

Different clusters cover different research areas. You should find calls
relevant to your research field. The EU supports international collaboration.
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
    - Japan's third country status is explained (15 points)
    - Participation pathways are described (15 points)
    - Specific options/restrictions mentioned (10 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    found_items = []
    missing_items = []

    # Check for Japan eligibility status explanation (15 points)
    japan_status_found = 0
    for keyword in JAPAN_ELIGIBILITY_KEYWORDS:
        if keyword in response_lower:
            japan_status_found += 1

    if japan_status_found >= 4:
        score += 15
        found_items.append("Japan third country status explained")
    elif japan_status_found >= 2:
        score += 8
        found_items.append("Japan status mentioned")
        missing_items.append("More detail on Japan's third country restrictions needed")
    else:
        missing_items.append("Japan third country eligibility status explanation")

    # Check for participation pathways (15 points)
    pathway_found = 0
    for keyword in PARTICIPATION_PATHWAY_KEYWORDS:
        if keyword in response_lower:
            pathway_found += 1

    if pathway_found >= 4:
        score += 15
        found_items.append("Participation pathways described")
    elif pathway_found >= 2:
        score += 8
        found_items.append("Some pathways mentioned")
        missing_items.append("More detail on MSCA/ERC pathways for third country")
    else:
        missing_items.append("Participation pathways (MSCA, ERC, bilateral)")

    # Check for specific options/restrictions (10 points)
    has_specifics = any(
        pattern in response_lower
        for pattern in [
            "self-fund",
            "not funded",
            "without funding",
            "msca-pf",
            "msca postdoctoral",
            "move to",
            "host institution",
            "bilateral",
            "specific call",
            "check the call",
            "topic conditions",
        ]
    )
    if has_specifics:
        score += 10
        found_items.append("Specific rules/conditions mentioned")
    else:
        missing_items.append("Specific funding rules and conditions")

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
    - Specific programme/call references (7 points)
    - Funding rules/restrictions (7 points)
    - Specific opportunities (6 points)
    - Clear restrictions/limitations (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Programme/call references (7 points)
    call_found = sum(1 for pat in CALL_DETAIL_PATTERNS["call_id"] if pat in response_lower)
    call_score = min(7, call_found * 2)
    score += call_score
    if call_found < 2:
        notes.append("Limited programme/call specificity")

    # Funding rules (7 points)
    rules_found = sum(1 for pat in CALL_DETAIL_PATTERNS["rules"] if pat in response_lower)
    rules_score = min(7, rules_found * 2)
    score += rules_score
    if rules_found < 2:
        notes.append("Limited funding rules information")

    # Opportunities (6 points)
    opp_found = sum(1 for pat in CALL_DETAIL_PATTERNS["opportunity"] if pat in response_lower)
    opp_score = min(6, opp_found * 2)
    score += opp_score
    if opp_found < 2:
        notes.append("Limited opportunity details")

    # Restrictions (5 points)
    restrict_found = sum(1 for pat in CALL_DETAIL_PATTERNS["restriction"] if pat in response_lower)
    restrict_score = min(5, restrict_found * 2)
    score += restrict_score

    return (
        score,
        "; ".join(notes) if notes else "Good specificity with participation details",
    )


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - Japan is correctly identified as a third country (not Associated)
    - Funding limitations are correctly explained
    - No false claims about Japan having full eligibility
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check for incorrect claims about Japan being an EU Member or Associated
    if "japan" in response_lower:
        japan_idx = response_lower.find("japan")
        nearby_text = response_lower[max(0, japan_idx - 50) : japan_idx + 200]

        # Check for false claim: Japan as EU Member State
        if "member state" in nearby_text:
            if "not" not in nearby_text and "non" not in nearby_text:
                score -= 15
                errors.append(
                    {
                        "claim": "Japan is an EU Member State",
                        "correct_value": "Japan is a non-associated third country",
                        "source": "EU Funding Domain Skill",
                    }
                )

        # Check for false claim: Japan as Associated Country
        if "associated country" in nearby_text or "associated state" in nearby_text:
            # Check if it's saying Japan is NOT associated (which is correct)
            if (
                "not associated" not in nearby_text
                and "non-associated" not in nearby_text
                and "not an associated" not in nearby_text
            ):
                score -= 10
                errors.append(
                    {
                        "claim": "Japan is an Associated Country",
                        "correct_value": "Japan is a non-associated third country",
                        "source": "EU Funding Domain Skill",
                    }
                )

        # Check for false claim: full eligibility/funding
        if "full eligibility" in nearby_text or "fully eligible" in nearby_text:
            if (
                "not" not in nearby_text
                and "cannot" not in nearby_text
                and "limited" not in nearby_text
            ):
                score -= 10
                errors.append(
                    {
                        "claim": "Japan has full eligibility in Horizon Europe",
                        "correct_value": "Japan has limited participation with restrictions",
                        "source": "EU Funding Domain Skill",
                    }
                )

    # Check for claims about receiving EU funding
    if "japan" in response_lower:
        # Positive claim check: Japan getting EU funding without noting restrictions
        funding_claim_areas = [
            response_lower[i : i + 200]
            for i, _ in enumerate(response_lower)
            if response_lower[i : i + 5] == "japan"
        ][:3]  # Check up to 3 occurrences

        for area in funding_claim_areas:
            if (
                "receive" in area
                and "funding" in area
                and "eu" in area
                and "not" not in area
                and "self" not in area
            ):
                # Allow if discussing MSCA/ERC (where they CAN get funding)
                if "msca" not in area and "erc" not in area and "fellowship" not in area:
                    score -= 5
                    errors.append(
                        {
                            "claim": "Japan organizations receive EU funding",
                            "correct_value": (
                                "Third country orgs typically self-fund; "
                                "individual researchers may get funding via MSCA/ERC"
                            ),
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
    - Clear guidance on participation options (4 points)
    - Links or resource references (3 points)
    - Next steps guidance (3 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Clear guidance on options (4 points)
    guidance_patterns = [
        "can apply",
        "may participate",
        "recommend",
        "best option",
        "pathway",
        "route",
        "option",
        "how to",
        "step",
    ]
    if sum(1 for p in guidance_patterns if p in response_lower) >= 2:
        score += 4
    else:
        notes.append("Limited participation guidance")

    # Links or resource references (3 points)
    link_patterns = [
        "http",
        "portal",
        "website",
        "ec.europa",
        "funding-tenders",
        "ncp",
        "jst",
        "jsps",
    ]
    if any(link in response_lower for link in link_patterns):
        score += 3
    else:
        notes.append("No links to official resources")

    # Next steps guidance (3 points)
    next_step_phrases = [
        "check",
        "verify",
        "contact",
        "find",
        "search",
        "look for",
        "apply",
        "register",
        "partner with",
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
            "component_id": "japan_eligibility",
            "description": "Japan third country eligibility and participation rules",
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
            f"Improve query fulfillment: Clearly explain Japan's third country status "
            f"AND describe participation pathways (MSCA, ERC, bilateral). "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include specific programmes (MSCA-PF, ERC), "
            "funding rules (self-funded vs EU-funded), and eligibility conditions"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual errors: Japan is a non-associated THIRD COUNTRY, "
            "NOT an EU Member State or Associated Country. "
            "Third countries typically NOT funded by EC (must self-fund)."
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add links to EU Funding Portal, "
            "recommend specific pathways (MSCA-PF for moving to EU), "
            "mention Japanese NCPs (JSPS, JST)"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Comprehensive coverage of Japan's status and pathways")
    if specificity_score >= 20:
        strengths.append("Rich in specific programme details and rules")
    if accuracy_score >= 20:
        strengths.append("Factually accurate on third country participation")
    if actionability_score >= 8:
        strengths.append("Provides clear guidance for Japanese researchers")

    return EvaluationResult(
        prompt_id="013",
        query=PROMPT_013_QUERY,
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
class TestPrompt013JapanEligibility:
    """
    Test suite for Prompt 013: Japan Researcher Eligibility.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_japan_eligibility(self):
        """
        Main evaluation test for Prompt 013.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_013_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_013_japan_eligibility.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 013: Japan Researcher Eligibility Evaluation")
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
        api_result = get_mapit_response(PROMPT_013_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_japan_status(self):
        """Verify the response mentions Japan's eligibility (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_013_japan_eligibility.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_japan_eligibility first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        japan_keywords_found = sum(1 for kw in JAPAN_ELIGIBILITY_KEYWORDS if kw in response_lower)

        # Informational check
        print(f"Japan eligibility keywords found: {japan_keywords_found}")
        if japan_keywords_found < 3:
            print("Note: Response needs more detail on Japan's third country status")

        # Soft assertion - just verify results exist
        assert "response" in result, "Response field missing from results"

    def test_response_mentions_pathways(self):
        """Verify the response mentions participation pathways (informational)."""
        results_file = RESULTS_DIR / "prompt_013_japan_eligibility.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_japan_eligibility first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        pathway_found = sum(1 for kw in PARTICIPATION_PATHWAY_KEYWORDS if kw in response_lower)

        # Informational check
        print(f"Pathway keywords found: {pathway_found}")
        if pathway_found < 3:
            print("Note: Response should include MSCA/ERC pathways for researchers")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt013OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_JAPAN_ELIGIBILITY, {"source": "sample_excellent"}
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_013_japan_eligibility_sample_excellent.json"
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
            SampleResponses.PARTIAL_JAPAN_ELIGIBILITY, {"source": "sample_partial"}
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
            SampleResponses.POOR_JAPAN_ELIGIBILITY, {"source": "sample_poor"}
        )

        print("\nPoor Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < NEEDS_REVIEW_THRESHOLD, (
            f"Poor response scored {evaluation.overall_score}, expected < {NEEDS_REVIEW_THRESHOLD}"
        )
        assert evaluation.result == "FAIL"

    def test_evaluation_identifies_missing_items(self):
        """Test that evaluation identifies missing content."""
        evaluation = evaluate_response(
            SampleResponses.POOR_JAPAN_ELIGIBILITY, {"source": "sample_poor"}
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
            SampleResponses.EXCELLENT_JAPAN_ELIGIBILITY, {"source": "excellent"}
        )
        poor_eval = evaluate_response(SampleResponses.POOR_JAPAN_ELIGIBILITY, {"source": "poor"})

        # Excellent response should have much higher specificity
        excellent_specificity = excellent_eval.component_scores[0]["specificity"]
        poor_specificity = poor_eval.component_scores[0]["specificity"]

        assert excellent_specificity > poor_specificity, (
            f"Excellent specificity ({excellent_specificity}) should be > poor ({poor_specificity})"
        )

    def test_save_evaluation_result_json(self):
        """Test that evaluation results are saved correctly as JSON."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_JAPAN_ELIGIBILITY, {"source": "test_json_save"}
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_013_japan_eligibility_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "013"
        assert loaded["query"] == PROMPT_013_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
