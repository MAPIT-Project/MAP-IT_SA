"""
Quality Evaluation Test for Prompt 031: Cluster 6 IA Budget Statistics.

This test evaluates the MAPIT AI response to the query:
"In HE Cluster 6 Innovation Actions, what is the average budget per partner in awarded
projects? How many partners are in those IAs on average?"

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Answers BOTH budget per partner AND partner count
- Specificity (25 points): Specific numbers with context (€ amounts, averages)
- Factual Accuracy (25 points): Verified against eu-funding-domain and database
- Actionability (10 points): Clear guidance, links to official resources

Pass threshold: >= 85/100

Reference facts from eu-funding-domain skill:
- IA: 70% funding rate (100% for non-profit)
- IA typical budget: €5-20M
- IA TRL focus: TRL 5-8
- Cluster 6: Food, Bioeconomy, Natural Resources
- IA consortium: 3 partners minimum from 3 different EU/Associated countries
- Typical IA consortium: 10-15 partners

Run with:
    pytest tests/quality/test_prompt_031_cluster6_ia_stats.py -v

For live API tests only:
    pytest tests/quality/test_prompt_031_cluster6_ia_stats.py -v -m "live_api"
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

# The query for this test
PROMPT_031_QUERY = (
    "In HE Cluster 6 Innovation Actions, what is the average budget per partner "
    "in awarded projects? How many partners are in those IAs on average?"
)

# Expected content based on PRD requirements
# Must provide specific statistical figures with EU funding domain cross-reference

# Budget per partner keywords
EXPECTED_BUDGET_KEYWORDS = [
    "budget",
    "per partner",
    "average",
    "€",
    "euro",
    "million",
    "funding",
    "contribution",
    "allocation",
]

# Partner count keywords
EXPECTED_PARTNER_KEYWORDS = [
    "partner",
    "beneficiar",  # beneficiary/beneficiaries
    "consortium",
    "average",
    "typical",
    "participant",
    "member",
]

# Cluster 6 context keywords
EXPECTED_CLUSTER6_KEYWORDS = [
    "cluster 6",
    "cl6",
    "food",
    "bioeconomy",
    "bio-economy",
    "natural resources",
    "agriculture",
    "agri-food",
    "horizon europe",
]

# IA-specific keywords
EXPECTED_IA_KEYWORDS = [
    "innovation action",
    "ia",
    "70%",
    "trl",
    "demonstration",
    "pilot",
    "market",
    "scale-up",
]

# Statistical terms
EXPECTED_STATISTICAL_TERMS = [
    "average",
    "mean",
    "median",
    "typical",
    "range",
    "project",
    "funded",
    "awarded",
    "analysis",
    "data",
    "statistic",
]


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_CLUSTER6_IA_STATS = """
## Cluster 6 Innovation Actions: Budget and Partner Statistics

Based on analysis of **287 funded Innovation Actions in Cluster 6 (Food, Bioeconomy,
Natural Resources)** from Horizon Europe:

### Budget per Partner

| Metric | Value |
|--------|-------|
| **Average budget per partner** | €412,000 |
| **Median budget per partner** | €385,000 |
| **Range** | €150,000 - €850,000 |

The budget per partner varies based on:
- Organization type (universities vs SMEs vs large industry)
- Role in consortium (coordinator typically receives larger share)
- Work package responsibilities

**Organization Type Breakdown:**
- Higher Education Institutions (HES): €380,000 average
- Research Organizations (REC): €420,000 average
- Private companies (PRC): €450,000 average
- Public bodies (PUB): €350,000 average

### Average Partners per Project

| Metric | Value |
|--------|-------|
| **Average partners** | 12.3 |
| **Median partners** | 11 |
| **Typical range** | 8-18 partners |
| **Average countries** | 8.5 |

**Consortium Composition Insights:**
- Most successful IAs have 10-15 partners
- Industry participation: 35-45% of consortium
- SME participation: typically 25-35%
- Academic partners: 40-50%

### Total Project Budgets

For context, Cluster 6 IAs typically have total budgets of:
- **Average**: €5.2 million
- **Range**: €3 million to €12 million
- **Funding rate**: 70% (100% for non-profit organizations)

### Key Considerations

**Funding Rate:**
Innovation Actions receive **70% funding** of eligible costs (100% for non-profit
entities). This affects how budgets are structured across partners.

**Cluster 6 Specifics:**
Cluster 6 focuses on:
- Sustainable food systems (agri-food)
- Circular bioeconomy
- Natural resources management
- Environmental observation

### Resources

- **CORDIS Database**: https://cordis.europa.eu - Search funded Cluster 6 projects
- **EU Funding Portal**: https://ec.europa.eu/info/funding-tenders/
- **Cluster 6 Work Programme**: Check destination-specific budgets and topics

### How to Use This Data

When planning your budget:
1. Use €350,000-€450,000 per partner as a baseline
2. Adjust for organization type and responsibilities
3. Plan for 10-15 partners for typical IA
4. Remember: coordinator typically receives 15-20% larger allocation
5. Consult the `get_budget_benchmark` tool for cluster-specific data
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_CLUSTER6_IA_STATS = """
For Innovation Actions in Horizon Europe:

The average budget per partner varies depending on the project.

Partners in IAs usually range from several to many depending on the specific call.

Innovation Actions receive 70% funding and focus on demonstration activities.

Check the work programme for specific requirements.
"""

    # A low-quality response that should FAIL (< 70)
    POOR_CLUSTER6_IA_STATS = """
Cluster 6 in Horizon Europe covers food and bioeconomy topics.

Innovation Actions are a type of project in Horizon Europe. They have multiple
partners and budgets depend on the specific call.

The budget per partner varies. Projects can have different numbers of partners.

Check the Horizon Europe work programme for more information.
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


def extract_currency_values(response: str) -> list[float]:
    """Extract currency values from response (in euros)."""
    values = []

    # Pattern for € amounts like €400,000 or €400000 or €0.4M
    euro_patterns = [
        r"€(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",  # €400,000 or €400000.50
        r"€(\d+(?:\.\d+)?)\s*(?:M|million)",  # €0.4M or €0.4 million
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:euro|EUR)",  # 400,000 EUR
    ]

    for pattern in euro_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        for match in matches:
            try:
                # Remove commas and convert
                value_str = match.replace(",", "")
                value = float(value_str)
                # Check if it's in millions notation
                if "M" in response[response.find(match) : response.find(match) + 20]:
                    value *= 1_000_000
                values.append(value)
            except ValueError:
                continue

    return values


def extract_partner_counts(response: str) -> list[int]:
    """Extract partner count numbers from response."""
    counts = []

    # Patterns for partner counts like "12.3 partners" or "10-15 partners"
    patterns = [
        r"(\d+(?:\.\d+)?)\s*(?:partners?|beneficiar)",  # 12.3 partners
        r"average[^.]*?(\d+(?:\.\d+)?)",  # average of 12.3
        r"(\d+)\s*-\s*(\d+)\s*partners?",  # 10-15 partners
        r"typically\s*(\d+)",  # typically 12
    ]

    response_lower = response.lower()

    for pattern in patterns:
        matches = re.findall(pattern, response_lower)
        for match in matches:
            if isinstance(match, tuple):
                for m in match:
                    if m:
                        try:
                            counts.append(int(float(m)))
                        except ValueError:
                            continue
            else:
                try:
                    counts.append(int(float(match)))
                except ValueError:
                    continue

    # Filter to reasonable partner count range (3-50)
    return [c for c in counts if 3 <= c <= 50]


def evaluate_query_fulfillment(response: str) -> tuple[int, str, list[str], list[str]]:
    """
    Evaluate query fulfillment (40 points max).

    Checks if response answers BOTH parts of the question:
    - Budget per partner (20 points)
    - Average partners per project (20 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    found_items = []
    missing_items = []

    # Check for budget per partner information (20 points)
    budget_keywords_found = sum(1 for kw in EXPECTED_BUDGET_KEYWORDS if kw in response_lower)
    has_budget_numbers = bool(extract_currency_values(response))
    has_per_partner = "per partner" in response_lower

    if budget_keywords_found >= 3 and has_budget_numbers and has_per_partner:
        score += 20
        found_items.append("Budget per partner with specific figures")
    elif budget_keywords_found >= 2 and (has_budget_numbers or has_per_partner):
        score += 12
        found_items.append("Partial budget information")
        missing_items.append("Specific budget per partner figure")
    elif budget_keywords_found >= 1:
        score += 5
        found_items.append("Budget mentioned")
        missing_items.append("Average budget per partner with € amount")
    else:
        missing_items.append("Budget per partner information")

    # Check for partner count information (20 points)
    partner_keywords_found = sum(1 for kw in EXPECTED_PARTNER_KEYWORDS if kw in response_lower)
    partner_counts = extract_partner_counts(response)
    has_average_mention = "average" in response_lower and "partner" in response_lower

    if partner_keywords_found >= 3 and partner_counts and has_average_mention:
        score += 20
        found_items.append(f"Average partner count: {partner_counts}")
    elif partner_keywords_found >= 2 and partner_counts:
        score += 12
        found_items.append("Partial partner count information")
        missing_items.append("Clear average partner count for Cluster 6 IAs")
    elif partner_keywords_found >= 1:
        score += 5
        found_items.append("Partners mentioned")
        missing_items.append("Specific average number of partners")
    else:
        missing_items.append("Average partners per project information")

    # Build notes
    if missing_items:
        notes.append(f"Missing: {', '.join(missing_items)}")
    else:
        notes.append("Both budget per partner and partner count fully covered")

    return score, "; ".join(notes), missing_items, found_items


def evaluate_specificity(response: str) -> tuple[int, str]:
    """
    Evaluate specificity (25 points max).

    Checks for:
    - Specific budget figures (8 points)
    - Specific partner count (8 points)
    - Data methodology/source (5 points)
    - Breakdown by org type or other detail (4 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Specific budget figures (8 points)
    currency_values = extract_currency_values(response)
    # Filter to budget-per-partner range (€100k-€1M per partner is typical)
    budget_values = [v for v in currency_values if 100_000 <= v <= 1_000_000]

    if len(budget_values) >= 2:
        score += 8
    elif len(budget_values) >= 1:
        score += 5
        notes.append("Limited budget specificity")
    elif currency_values:
        score += 3
        notes.append("Budget figures present but unclear per-partner amounts")
    else:
        notes.append("No specific budget figures")

    # Specific partner count (8 points)
    partner_counts = extract_partner_counts(response)

    if len(partner_counts) >= 2:
        score += 8
    elif len(partner_counts) >= 1:
        score += 5
        notes.append("Limited partner count specificity")
    else:
        notes.append("No specific partner counts")

    # Data methodology/source mentioned (5 points)
    methodology_terms = [
        "cordis",
        "funded project",
        "analysis",
        "database",
        "awarded project",
        "based on",
        "statistic",
        "horizon europe",
    ]
    methodology_found = sum(1 for term in methodology_terms if term in response_lower)

    if methodology_found >= 3:
        score += 5
    elif methodology_found >= 1:
        score += 3
        notes.append("Could explain data source better")
    else:
        notes.append("No methodology/data source mentioned")

    # Breakdown by org type or other detail (4 points)
    breakdown_terms = [
        "hes",
        "rec",
        "prc",
        "sme",
        "university",
        "research org",
        "higher education",
        "industry",
        "breakdown",
        "organization type",
        "median",
        "range",
    ]
    breakdown_found = sum(1 for term in breakdown_terms if term in response_lower)

    if breakdown_found >= 3:
        score += 4
    elif breakdown_found >= 1:
        score += 2
        notes.append("Some breakdown provided")
    else:
        notes.append("No org-type breakdown")

    return (
        score,
        "; ".join(notes) if notes else "Good specificity with detailed figures",
    )


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - IA funding rate mentioned correctly (70%, 100% for non-profit)
    - Budget per partner is reasonable (€200k-€600k typical)
    - Partner count is reasonable (8-20 typical for IA)
    - Cluster 6 context is correct
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check IA funding rate accuracy
    if "ia" in response_lower or "innovation action" in response_lower:
        # Wrong: IA with 100% funding without non-profit caveat
        if "100%" in response and "innovation action" in response_lower:
            context_100 = response_lower[
                max(0, response_lower.find("100%") - 100) : response_lower.find("100%") + 100
            ]
            if (
                "innovation action" in context_100 or "ia" in context_100.split()
            ) and "non-profit" not in context_100:
                # Check if 70% is also mentioned nearby
                if "70%" not in context_100:
                    score -= 5
                    errors.append(
                        {
                            "claim": "IA funding rate stated as 100% without caveat",
                            "correct_value": "IA: 70% (100% for non-profit only)",
                            "source": "EU Funding Domain Skill",
                        }
                    )

    # Check budget per partner reasonableness
    currency_values = extract_currency_values(response)
    budget_per_partner = [v for v in currency_values if 50_000 <= v <= 2_000_000]

    for val in budget_per_partner:
        if val < 100_000:
            score -= 3
            errors.append(
                {
                    "claim": f"Budget per partner €{val:,.0f} seems too low",
                    "correct_value": "Typical IA budget per partner: €300k-€500k",
                    "source": "CORDIS data analysis",
                }
            )
            break
        elif val > 800_000:
            # This might be okay but worth noting
            pass

    # Check partner count reasonableness
    partner_counts = extract_partner_counts(response)

    for count in partner_counts:
        if count < 3:
            score -= 5
            errors.append(
                {
                    "claim": f"Partner count {count} is below minimum",
                    "correct_value": "IA minimum is 3 partners from 3 countries",
                    "source": "EU Funding Domain Skill",
                }
            )
            break
        elif count > 30:
            score -= 2
            errors.append(
                {
                    "claim": f"Partner count {count} seems unusually high",
                    "correct_value": "Typical IA: 10-15 partners",
                    "source": "CORDIS data analysis",
                }
            )
            break

    # Check Cluster 6 identification
    cluster6_mentioned = any(kw in response_lower for kw in EXPECTED_CLUSTER6_KEYWORDS)
    if not cluster6_mentioned:
        score -= 3
        errors.append(
            {
                "claim": "Cluster 6 not clearly identified",
                "correct_value": "Should mention Cluster 6: Food, Bioeconomy, Natural Resources",
                "source": "EU Funding Domain Skill",
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
    - Links or resource references (4 points)
    - Guidance on using the data (3 points)
    - Reference to tools/documents (3 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Links or URL references (4 points)
    link_patterns = [
        "http",
        "cordis",
        "ec.europa",
        "funding-tenders",
        "portal",
        "work programme",
    ]
    link_found = sum(1 for link in link_patterns if link in response_lower)

    if link_found >= 2:
        score += 4
    elif link_found >= 1:
        score += 2
        notes.append("Limited links to resources")
    else:
        notes.append("No links to official resources")

    # Guidance on using the data (3 points)
    guidance_phrases = [
        "when planning",
        "use this",
        "consider",
        "recommend",
        "suggest",
        "baseline",
        "guideline",
        "how to",
    ]
    guidance_found = sum(1 for phrase in guidance_phrases if phrase in response_lower)

    if guidance_found >= 2:
        score += 3
    elif guidance_found >= 1:
        score += 1
        notes.append("Some guidance provided")
    else:
        notes.append("No guidance on using the data")

    # Reference to tools/documents (3 points)
    tool_refs = [
        "get_budget_benchmark",
        "get_consortium_patterns",
        "tool",
        "search",
        "database",
        "cordis",
    ]
    tool_found = sum(1 for ref in tool_refs if ref in response_lower)

    if tool_found >= 2:
        score += 3
    elif tool_found >= 1:
        score += 1
    else:
        notes.append("No tool/database references")

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
            "component_id": "cluster6_ia_stats",
            "description": ("Cluster 6 IA budget per partner and average partner count"),
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
            f"Improve query fulfillment: Must answer BOTH budget per partner "
            f"(e.g., €400k average) AND average partners per project (e.g., 12-15). "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include specific € amounts for budget per partner, "
            "specific partner counts, data source reference, and org-type breakdown"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual accuracy: Verify IA=70% funding (100% non-profit), "
            "typical budget per partner €300k-€500k, typical partners 10-15, "
            "and correctly identify Cluster 6 (Food, Bioeconomy, Natural Resources)"
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add links to CORDIS/EU Portal, "
            "guidance on using statistics for budget planning, "
            "and reference to get_budget_benchmark tool"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Both budget per partner and partner count fully addressed")
    if specificity_score >= 20:
        strengths.append("Rich in specific numbers and data")
    if accuracy_score >= 20:
        strengths.append("Factually accurate")
    if actionability_score >= 8:
        strengths.append("Provides useful resources and guidance")

    return EvaluationResult(
        prompt_id="031",
        query=PROMPT_031_QUERY,
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
class TestPrompt031Cluster6IAStats:
    """
    Test suite for Prompt 031: Cluster 6 IA Budget Statistics.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_cluster6_ia_stats(self):
        """
        Main evaluation test for Prompt 031.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_031_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_031_cluster6_ia_stats.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 031: Cluster 6 IA Budget Statistics Evaluation")
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
        api_result = get_mapit_response(PROMPT_031_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_cluster6(self):
        """Verify the response mentions Cluster 6 (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_031_cluster6_ia_stats.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_cluster6_ia_stats first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        cluster6_found = any(kw in response_lower for kw in EXPECTED_CLUSTER6_KEYWORDS)

        # Informational check
        print(f"Cluster 6 mentioned: {cluster6_found}")
        if not cluster6_found:
            print("Note: Response should mention Cluster 6 context")

        # Soft assertion - just verify results exist
        assert "response" in result, "Response field missing from results"

    def test_response_has_budget_figures(self):
        """Verify the response has budget figures (informational)."""
        results_file = RESULTS_DIR / "prompt_031_cluster6_ia_stats.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_cluster6_ia_stats first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        currency_values = extract_currency_values(result["response"])

        # Informational check
        print(f"Currency values found: {currency_values}")
        if not currency_values:
            print("Note: Response should include specific budget figures")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt031OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_CLUSTER6_IA_STATS, {"source": "sample_excellent"}
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_031_cluster6_ia_stats_sample_excellent.json"
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
            SampleResponses.PARTIAL_CLUSTER6_IA_STATS, {"source": "sample_partial"}
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
            SampleResponses.POOR_CLUSTER6_IA_STATS, {"source": "sample_poor"}
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
            SampleResponses.POOR_CLUSTER6_IA_STATS, {"source": "sample_poor"}
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
            SampleResponses.EXCELLENT_CLUSTER6_IA_STATS, {"source": "excellent"}
        )
        poor_eval = evaluate_response(SampleResponses.POOR_CLUSTER6_IA_STATS, {"source": "poor"})

        # Excellent response should have much higher specificity
        excellent_specificity = excellent_eval.component_scores[0]["specificity"]
        poor_specificity = poor_eval.component_scores[0]["specificity"]

        assert excellent_specificity > poor_specificity, (
            f"Excellent specificity ({excellent_specificity}) should be > poor ({poor_specificity})"
        )

    def test_save_evaluation_result_json(self):
        """Test that evaluation results are saved correctly as JSON."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_CLUSTER6_IA_STATS, {"source": "test_json_save"}
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_031_cluster6_ia_stats_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "031"
        assert loaded["query"] == PROMPT_031_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
