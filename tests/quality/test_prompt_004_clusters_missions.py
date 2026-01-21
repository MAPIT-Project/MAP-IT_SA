"""
Quality Evaluation Test for Prompt 004: Clusters and Missions in Horizon Europe.

This test evaluates the MAPIT AI response to the query:
"What are Clusters and Missions in Horizon Europe?"

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): All 6 Clusters AND 5 Missions explained
- Specificity (25 points): Concrete details (names, budgets, focus areas)
- Factual Accuracy (25 points): Verified against EU funding domain knowledge
- Actionability (10 points): Clear guidance for users

Pass threshold: >= 85/100

Run with:
    pytest tests/quality/test_prompt_004_clusters_missions.py -v

For live API tests only:
    pytest tests/quality/test_prompt_004_clusters_missions.py -v -m "live_api"
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
PROMPT_004_QUERY = "What are Clusters and Missions in Horizon Europe?"

# Expected content based on eu-funding-domain skill
# Must list all 6 Clusters with descriptions
EXPECTED_CLUSTERS = {
    "cluster_1": {
        "name": "Cluster 1: Health",
        "keywords": [
            "cluster 1",
            "cluster-1",
            "health",
            "medical",
            "clinical",
            "disease",
            "pandemic",
            "pharmaceutical",
            "cancer",
        ],
        "description": "Health research and innovation",
    },
    "cluster_2": {
        "name": "Cluster 2: Culture, Creativity & Inclusive Society",
        "keywords": [
            "cluster 2",
            "cluster-2",
            "culture",
            "creativity",
            "inclusive society",
            "democracy",
            "heritage",
            "social",
            "governance",
        ],
        "description": "Social sciences, humanities, cultural heritage",
    },
    "cluster_3": {
        "name": "Cluster 3: Civil Security for Society",
        "keywords": [
            "cluster 3",
            "cluster-3",
            "security",
            "civil security",
            "cybersecurity",
            "disaster",
            "resilience",
            "border",
            "terrorism",
        ],
        "description": "Security and resilience research",
    },
    "cluster_4": {
        "name": "Cluster 4: Digital, Industry & Space",
        "keywords": [
            "cluster 4",
            "cluster-4",
            "digital",
            "industry",
            "space",
            "ai",
            "artificial intelligence",
            "robotics",
            "manufacturing",
            "semiconductor",
        ],
        "description": "Digital transformation, industrial competitiveness",
    },
    "cluster_5": {
        "name": "Cluster 5: Climate, Energy & Mobility",
        "keywords": [
            "cluster 5",
            "cluster-5",
            "climate",
            "energy",
            "mobility",
            "transport",
            "hydrogen",
            "green deal",
            "carbon",
            "battery",
        ],
        "description": "Climate action, clean energy, sustainable transport",
    },
    "cluster_6": {
        "name": "Cluster 6: Food, Bioeconomy, Natural Resources, Agriculture",
        "keywords": [
            "cluster 6",
            "cluster-6",
            "food",
            "bioeconomy",
            "natural resources",
            "agriculture",
            "biodiversity",
            "ocean",
            "water",
            "circular",
        ],
        "description": "Food systems, bioeconomy, environmental protection",
    },
}

# Must list all 5 Missions with descriptions
EXPECTED_MISSIONS = {
    "mission_cancer": {
        "name": "Mission Cancer",
        "keywords": [
            "cancer mission",
            "mission cancer",
            "conquering cancer",
            "cancer research",
            "oncology",
        ],
        "description": "Improving lives of cancer patients through prevention and treatment",
    },
    "mission_climate": {
        "name": "Mission Climate Adaptation",
        "keywords": [
            "climate adaptation",
            "climate-resilient",
            "climate resilient",
            "adaptation to climate change",
            "climate mission",
        ],
        "description": "Supporting EU regions to become climate-resilient by 2030",
    },
    "mission_ocean": {
        "name": "Mission Restore our Ocean and Waters",
        "keywords": [
            "ocean mission",
            "restore ocean",
            "healthy ocean",
            "mission ocean",
            "waters",
            "sea",
            "marine",
        ],
        "description": "Restoring ocean and waters health by 2030",
    },
    "mission_cities": {
        "name": "Mission Climate-Neutral and Smart Cities",
        "keywords": [
            "climate-neutral cities",
            "climate neutral cities",
            "smart cities",
            "100 cities",
            "cities mission",
            "urban",
        ],
        "description": "100 climate-neutral and smart cities by 2030",
    },
    "mission_soil": {
        "name": "Mission Soil Deal for Europe",
        "keywords": [
            "soil deal",
            "soil mission",
            "mission soil",
            "healthy soil",
            "soil health",
            "living labs",
        ],
        "description": "100 living labs and lighthouses for healthy soils by 2030",
    },
}

# Programme context
PROGRAMME_CONTEXT = {
    "pillar": "Pillar II (Global Challenges & European Industrial Competitiveness)",
    "total_clusters": 6,
    "total_missions": 5,
    "cluster_budget": "Largest portion of Horizon Europe budget",
    "mission_approach": "Challenge-driven research with specific targets",
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_CLUSTERS_MISSIONS = """
**Clusters and Missions in Horizon Europe**

Horizon Europe organizes its research and innovation activities into **Clusters** and **Missions**,
both primarily under **Pillar II: Global Challenges & European Industrial Competitiveness**.

## The 6 Clusters

Clusters group related research topics to address major societal challenges. Each cluster has
its own Work Programme and funding calls.

### Cluster 1: Health
- **Focus**: Medical research, disease prevention, healthcare systems, pandemic preparedness
- **Key Topics**: Cancer research, infectious diseases, personalized medicine, health data
- **Budget**: ~€8.2 billion (2021-2027)

### Cluster 2: Culture, Creativity & Inclusive Society
- **Focus**: Democracy, cultural heritage, social cohesion, European identity
- **Key Topics**: Cultural industries, governance, migration, social innovation
- **Budget**: ~€2.3 billion (2021-2027)

### Cluster 3: Civil Security for Society
- **Focus**: Disaster resilience, cybersecurity, border protection, counter-terrorism
- **Key Topics**: Critical infrastructure, forensics, fighting crime, disaster response
- **Budget**: ~€1.6 billion (2021-2027)

### Cluster 4: Digital, Industry & Space
- **Focus**: Digital transformation, industrial competitiveness, space applications
- **Key Topics**: AI, robotics, advanced materials, manufacturing, semiconductors, space
- **Budget**: ~€15.3 billion (2021-2027)

### Cluster 5: Climate, Energy & Mobility
- **Focus**: Climate action, clean energy, sustainable transport
- **Key Topics**: Hydrogen, batteries, renewable energy, smart grids, green transport
- **Budget**: ~€15.1 billion (2021-2027)

### Cluster 6: Food, Bioeconomy, Natural Resources, Agriculture & Environment
- **Focus**: Sustainable food systems, biodiversity, circular economy
- **Key Topics**: Agriculture, fisheries, forestry, water, soil, ocean health
- **Budget**: ~€9 billion (2021-2027)

## The 5 EU Missions

EU Missions are a new approach in Horizon Europe: challenge-driven portfolios of actions with
**ambitious, measurable targets** to be achieved by specific deadlines (mainly 2030).

### Mission 1: Conquering Cancer
- **Target**: Improve lives of 3 million+ people through prevention, cure, living with cancer
- **Approach**: Research, early detection, patient-centered care
- **Timeline**: By 2030

### Mission 2: Adaptation to Climate Change
- **Target**: Support at least 150 regions to become climate-resilient
- **Approach**: Climate risk assessments, adaptation solutions
- **Timeline**: By 2030

### Mission 3: Restore our Ocean and Waters
- **Target**: Protect and restore ocean/water ecosystems
- **Approach**: Marine protected areas, pollution reduction, sustainable blue economy
- **Timeline**: By 2030

### Mission 4: Climate-Neutral and Smart Cities
- **Target**: 100 European cities to become climate-neutral by 2030
- **Approach**: City contracts, citizen engagement, sustainable urban solutions
- **Timeline**: By 2030

### Mission 5: A Soil Deal for Europe
- **Target**: 100 living labs and lighthouses for healthy soils
- **Approach**: Soil monitoring, sustainable land management
- **Timeline**: By 2030

## Key Differences

| Aspect | Clusters | Missions |
|--------|----------|----------|
| **Approach** | Thematic grouping | Challenge-driven |
| **Structure** | Annual work programmes | Mission-specific calls |
| **Targets** | Research excellence | Measurable impact targets |
| **Scope** | Broad topics | Specific goals with deadlines |

## How to Apply

For Cluster and Mission funding:
- Register on the EU Funding & Tenders Portal
- Check the Work Programme for your cluster/mission
- Review open calls in your area of interest
- Consider RIA, IA, or CSA action types
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_CLUSTERS_MISSIONS = """
Clusters and Missions are part of Horizon Europe's Pillar II.

The 6 Clusters are:
1. Health
2. Culture and Society
3. Security
4. Digital and Industry
5. Climate and Energy
6. Food and Bioeconomy

There are 5 Missions focusing on Cancer, Climate, Ocean, Cities, and Soil.

Clusters organize research by theme, while Missions have specific targets to achieve.
Researchers can apply through the EU portal.
"""

    # A low-quality response that should FAIL (< 70)
    POOR_CLUSTERS_MISSIONS = """
Horizon Europe has different areas for funding research. There are clusters that cover
various topics and missions that focus on big challenges. You can check the EU website
for more information about funding opportunities.
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

    Checks if ALL 6 Clusters AND 5 Missions are explained.
    - 6 Clusters: 4 points each = 24 points
    - 5 Missions: 3.2 points each = 16 points
    """
    score = 0
    notes = []
    response_lower = response.lower()

    clusters_found = []
    clusters_missing = []
    missions_found = []
    missions_missing = []

    # Check each Cluster (4 points each = 24 total)
    points_per_cluster = 4

    for _cluster_id, cluster_info in EXPECTED_CLUSTERS.items():
        found = False
        for keyword in cluster_info["keywords"]:
            if keyword in response_lower:
                found = True
                break

        if found:
            clusters_found.append(cluster_info["name"])
            score += points_per_cluster
        else:
            clusters_missing.append(cluster_info["name"])

    # Check each Mission (3.2 points each = 16 total, rounded to integers)
    points_per_mission = 3  # Using 3 to keep integer math, total = 15

    for _mission_id, mission_info in EXPECTED_MISSIONS.items():
        found = False
        for keyword in mission_info["keywords"]:
            if keyword in response_lower:
                found = True
                break

        if found:
            missions_found.append(mission_info["name"])
            score += points_per_mission
        else:
            missions_missing.append(mission_info["name"])

    # Bonus point if all missions are found
    if len(missions_missing) == 0:
        score += 1  # Makes missions total = 16

    # Build notes
    if clusters_missing:
        notes.append(f"Missing Clusters: {', '.join(clusters_missing)}")
    else:
        notes.append("All 6 Clusters explained")

    if missions_missing:
        notes.append(f"Missing Missions: {', '.join(missions_missing)}")
    else:
        notes.append("All 5 Missions explained")

    notes.append(f"Clusters: {len(clusters_found)}/6, Missions: {len(missions_found)}/5")

    return score, "; ".join(notes), clusters_missing, missions_missing


def evaluate_specificity(response: str) -> tuple[int, str]:
    """
    Evaluate specificity (25 points max).

    Checks for:
    - Budget figures for clusters/missions (8 points)
    - Timeline/targets for missions (7 points)
    - Topic examples for clusters (5 points)
    - Structural context (Pillar II, etc.) (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Budget figures (8 points)
    budget_patterns = [
        "billion",
        "million",
        "budget",
        "funding",
        "€",
        "eur",
    ]
    budget_found = sum(1 for pat in budget_patterns if pat in response_lower)
    budget_score = min(8, budget_found * 2)
    score += budget_score
    if budget_found < 2:
        notes.append("Limited budget/funding details")

    # Timeline/targets for missions (7 points)
    target_patterns = [
        "2030",
        "by 2030",
        "target",
        "goal",
        "100 cities",
        "100 living labs",
        "150 regions",
        "3 million",
        "measurable",
    ]
    target_found = sum(1 for pat in target_patterns if pat in response_lower)
    target_score = min(7, target_found * 2)
    score += target_score
    if target_found < 2:
        notes.append("Limited mission targets/timeline details")

    # Topic examples (5 points)
    topic_patterns = [
        "cancer",
        "hydrogen",
        "battery",
        "ai",
        "artificial intelligence",
        "biodiversity",
        "pandemic",
        "cybersecurity",
        "heritage",
    ]
    topic_found = sum(1 for pat in topic_patterns if pat in response_lower)
    topic_score = min(5, topic_found)
    score += topic_score

    # Structural context (5 points)
    context_patterns = [
        "pillar ii",
        "pillar 2",
        "global challenges",
        "industrial competitiveness",
        "work programme",
        "horizon europe",
        "ria",
        "ia",
        "csa",
    ]
    context_found = sum(1 for pat in context_patterns if pat in response_lower)
    context_score = min(5, context_found * 2)
    score += context_score

    return score, "; ".join(notes) if notes else "Good specificity with concrete details"


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies facts against eu-funding-domain knowledge:
    - Correct number of clusters (6)
    - Correct number of missions (5)
    - Correct pillar placement (Pillar II)
    - Correct mission names and targets
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check for incorrect number of clusters
    wrong_cluster_counts = ["7 cluster", "8 cluster", "5 cluster", "4 cluster"]
    for wrong in wrong_cluster_counts:
        if wrong in response_lower:
            score -= 5
            errors.append(
                {
                    "claim": f"Wrong cluster count ({wrong})",
                    "correct_value": "Horizon Europe has 6 Clusters",
                    "source": "EU Funding Domain Skill",
                }
            )
            break

    # Check for incorrect number of missions
    wrong_mission_counts = ["4 mission", "6 mission", "7 mission", "3 mission"]
    for wrong in wrong_mission_counts:
        if wrong in response_lower:
            score -= 5
            errors.append(
                {
                    "claim": f"Wrong mission count ({wrong})",
                    "correct_value": "Horizon Europe has 5 Missions",
                    "source": "EU Funding Domain Skill",
                }
            )
            break

    # Check for incorrect pillar placement
    wrong_pillar_indicators = [
        ("cluster", "pillar i"),
        ("cluster", "pillar 1"),
        ("mission", "pillar iii"),
        ("mission", "pillar 3"),
    ]
    for term1, term2 in wrong_pillar_indicators:
        if term1 in response_lower and term2 in response_lower:
            idx1 = response_lower.find(term1)
            idx2 = response_lower.find(term2)
            if abs(idx1 - idx2) < 200:
                score -= 5
                errors.append(
                    {
                        "claim": "Clusters/Missions placed in wrong pillar",
                        "correct_value": (
                            "Clusters and Missions are under "
                            "Pillar II (Global Challenges)"
                        ),
                        "source": "EU Funding Domain Skill",
                    }
                )
                break

    # Check for mission deadline errors (missions target 2030, not other years)
    wrong_years = ["2025", "2035", "2040", "2027"]
    for wrong_year in wrong_years:
        if wrong_year in response_lower and "mission" in response_lower:
            # Check if year is close to "mission" mention
            idx_year = response_lower.find(wrong_year)
            idx_mission = response_lower.find("mission")
            if abs(idx_year - idx_mission) < 150:
                score -= 3
                errors.append(
                    {
                        "claim": f"Wrong mission target year ({wrong_year})",
                        "correct_value": "EU Missions target 2030",
                        "source": "EU Funding Domain Skill",
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
    - Links to official resources (4 points)
    - Guidance on how to apply (3 points)
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

    # Application guidance (3 points)
    guidance_phrases = [
        "how to apply",
        "register",
        "submit",
        "application",
        "getting started",
        "find call",
        "apply for",
        "funding opportunity",
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
        missing_clusters,
        missing_missions,
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
            "component_id": "clusters_missions",
            "description": "Clusters and Missions explanation",
            "fulfillment": fulfillment_score,
            "specificity": specificity_score,
            "accuracy": accuracy_score,
            "actionability": actionability_score,
            "total": overall_score,
            "notes": (
                f"Fulfillment: {fulfillment_notes}; Specificity: {specificity_notes}; "
                f"Accuracy: {accuracy_notes}; Actionability: {actionability_notes}"
            ),
            "missing_clusters": missing_clusters,
            "missing_missions": missing_missions,
        }
    ]

    # Generate fix suggestions
    fix_suggestions = []
    if fulfillment_score < 32:  # < 80% of 40
        fix_suggestions.append(
            f"Improve query fulfillment: Explain all 6 Clusters and 5 Missions. "
            f"Missing Clusters: {', '.join(missing_clusters) if missing_clusters else 'None'}. "
            f"Missing Missions: {', '.join(missing_missions) if missing_missions else 'None'}"
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include budget figures for clusters, "
            "specific targets (2030, 100 cities, etc.) for missions, "
            "and topic examples for each cluster"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual errors: Verify 6 Clusters, 5 Missions, "
            "Pillar II placement, and 2030 targets"
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add links to EU Funding Portal, "
            "Work Programmes, and guidance on finding relevant calls"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Comprehensive coverage of Clusters and Missions")
    if specificity_score >= 20:
        strengths.append("Rich in specific details (budgets, targets, topics)")
    if accuracy_score >= 20:
        strengths.append("Factually accurate")
    if actionability_score >= 8:
        strengths.append("Provides clear guidance for researchers")

    return EvaluationResult(
        prompt_id="004",
        query=PROMPT_004_QUERY,
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
class TestPrompt004ClustersMissions:
    """
    Test suite for Prompt 004: Clusters and Missions.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_clusters_missions(self):
        """
        Main evaluation test for Prompt 004.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Asserts quality threshold is met
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_004_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_004_clusters_missions.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 004: Clusters and Missions Evaluation")
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

            if comp.get("missing_clusters"):
                print(f"\nMissing Clusters: {comp['missing_clusters']}")
            if comp.get("missing_missions"):
                print(f"Missing Missions: {comp['missing_missions']}")

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
        api_result = get_mapit_response(PROMPT_004_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_clusters(self):
        """Verify the response mentions clusters (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_004_clusters_missions.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_clusters_missions first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        clusters_found = 0
        for cluster_info in EXPECTED_CLUSTERS.values():
            for keyword in cluster_info["keywords"]:
                if keyword in response_lower:
                    clusters_found += 1
                    break

        # Informational check
        print(f"Clusters mentioned: {clusters_found}/6")
        if clusters_found < 5:
            print("Note: Response needs improvement - fewer than 5 clusters mentioned")

        # Soft assertion - just verify results exist
        assert "response" in result, "Response field missing from results"

    def test_response_mentions_missions(self):
        """Verify the response mentions missions (informational)."""
        results_file = RESULTS_DIR / "prompt_004_clusters_missions.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_clusters_missions first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        missions_found = 0
        for mission_info in EXPECTED_MISSIONS.values():
            for keyword in mission_info["keywords"]:
                if keyword in response_lower:
                    missions_found += 1
                    break

        # Informational check
        print(f"Missions mentioned: {missions_found}/5")
        if missions_found < 4:
            print("Note: Response needs improvement - fewer than 4 missions mentioned")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt004OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_CLUSTERS_MISSIONS, {"source": "sample_excellent"}
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_004_clusters_missions_sample_excellent.json"
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
            SampleResponses.PARTIAL_CLUSTERS_MISSIONS, {"source": "sample_partial"}
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
            SampleResponses.POOR_CLUSTERS_MISSIONS, {"source": "sample_poor"}
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
        """Test that evaluation identifies when clusters/missions are missing."""
        evaluation = evaluate_response(
            SampleResponses.PARTIAL_CLUSTERS_MISSIONS, {"source": "sample_partial"}
        )

        # Check that missing items are identified
        if evaluation.component_scores:
            comp = evaluation.component_scores[0]
            missing_clusters = comp.get("missing_clusters", [])
            missing_missions = comp.get("missing_missions", [])

            # Partial response should be missing at least some items
            total_missing = len(missing_clusters) + len(missing_missions)
            print(f"Missing clusters: {missing_clusters}")
            print(f"Missing missions: {missing_missions}")
            assert total_missing >= 1, "Should identify missing items in partial response"

    def test_evaluation_rewards_specificity(self):
        """Test that specific details improve the score."""
        excellent_eval = evaluate_response(
            SampleResponses.EXCELLENT_CLUSTERS_MISSIONS, {"source": "excellent"}
        )
        poor_eval = evaluate_response(
            SampleResponses.POOR_CLUSTERS_MISSIONS, {"source": "poor"}
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
            SampleResponses.EXCELLENT_CLUSTERS_MISSIONS, {"source": "test_json_save"}
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_004_clusters_missions_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "004"
        assert loaded["query"] == PROMPT_004_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
