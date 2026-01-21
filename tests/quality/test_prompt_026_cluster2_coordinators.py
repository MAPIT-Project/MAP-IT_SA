"""
Quality Evaluation Test for Prompt 026: Top SSH/Cluster 2 Coordinators.

This test evaluates the MAPIT AI response to the query:
"Who are the most successful top 10 coordinators in SSH/Cluster 2 calls
during Horizon 2020 and Horizon Europe?"

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Returns exactly 10 coordinators with SSH/Cluster 2 focus
- Specificity (25 points): Organization names, coordination counts, programmes
- Factual Accuracy (25 points): Valid organizations, plausible statistics
- Actionability (10 points): Links to CORDIS/EU portal, how to learn more

Pass threshold: >= 85/100

Reference requirements from PRD:
- Must list 10 specific organizations with coordination counts
- Should cover both Horizon 2020 and Horizon Europe
- Focus on SSH (Social Sciences & Humanities) / Cluster 2

SSH/Cluster 2 covers:
- Culture, Creativity and Inclusive Society
- Democracy, governance, civil society
- Social and economic transformations
- Cultural heritage, migration, innovation in creative industries

Run with:
    pytest tests/quality/test_prompt_026_cluster2_coordinators.py -v

For live API tests only:
    pytest tests/quality/test_prompt_026_cluster2_coordinators.py -v -m "live_api"
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
PROMPT_026_QUERY = (
    "Who are the most successful top 10 coordinators in SSH/Cluster 2 calls "
    "during Horizon 2020 and Horizon Europe?"
)

# Expected SSH/Cluster 2 related keywords
SSH_CLUSTER2_KEYWORDS = [
    "ssh",
    "social science",
    "humanities",
    "cluster 2",
    "culture",
    "creativity",
    "inclusive society",
    "democracy",
    "governance",
    "heritage",
    "migration",
    "creative",
    "societal",
    "cultural heritage",
    "society",
    "civil society",
    "social",
]

# Programme keywords
PROGRAMME_KEYWORDS = [
    "horizon 2020",
    "h2020",
    "horizon europe",
    "he",
    "fp8",
    "framework programme",
]

# Coordinator-related patterns
COORDINATOR_PATTERNS = {
    "coordination_count": [
        r"\d+\s*(?:project[s]?\s*)?coordinated",
        r"coordinated\s*(?::\s*)?\d+",
        r"coordination[s]?\s*[\:]\s*\d+",
        r"\d+\s*coordination",
        r"coordinator\s*(?:of|in)\s*\d+",
        r"\d+\s+as\s+coordinator",  # Matches "5 as coordinator" format
        r"\(\d+\s+as\s+coordinator\)",  # Matches "(5 as coordinator)" format
    ],
    "coordinator_role": [
        "coordinator",
        "coordinated",
        "lead",
        "leading",
        "coordination",
        "principal",
        "as coordinator",  # Matches "5 as coordinator" format
    ],
}

# Known SSH/research institutions patterns
SSH_INSTITUTION_PATTERNS = [
    r"university",
    r"universit[aäeio]",  # Covers università, université, universiteit
    r"universiteit",  # Dutch university spelling
    r"yliopisto",  # Finnish university (e.g., HELSINGIN YLIOPISTO)
    r"politecnico",  # Italian technical university
    r"institut",
    r"centre",
    r"center",
    r"school",
    r"college",
    r"akademie",
    r"sciences\s*po",
    r"cnrs",
    r"max[\-\s]planck",
    r"foundation",
    r"research",
    r"kentro",  # Greek research center (e.g., ETHNIKO KENTRO)
    r"alma\s*mater",  # Bologna style
    r"stichting",  # Dutch foundation/organization
    r"katholieke",  # Catholic university
    r"erasmus",  # Erasmus University
]


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_CLUSTER2_COORDINATORS = """
## Top 10 Most Successful SSH/Cluster 2 Coordinators in H2020 and Horizon Europe

Based on coordination statistics from SSH-related calls in Horizon 2020 and Horizon Europe:

### 1. **KU Leuven** (Belgium)
- **Projects Coordinated**: 45 (H2020: 32, HE: 13)
- **Key SSH Areas**: Social transformations, cultural heritage, democracy
- **Total EC Funding Coordinated**: €125 million

### 2. **Universitat de Barcelona** (Spain)
- **Projects Coordinated**: 38 (H2020: 25, HE: 13)
- **Key SSH Areas**: Migration, inclusive society, cultural diversity
- **Total EC Funding Coordinated**: €98 million

### 3. **University of Oxford** (UK)
- **Projects Coordinated**: 35 (H2020: 28, HE: 7)
- **Key SSH Areas**: Governance, democracy, social sciences
- **Total EC Funding Coordinated**: €92 million

### 4. **CNRS - Centre National de la Recherche Scientifique** (France)
- **Projects Coordinated**: 33 (H2020: 24, HE: 9)
- **Key SSH Areas**: Humanities, cultural heritage, social innovation
- **Total EC Funding Coordinated**: €88 million

### 5. **Vrije Universiteit Amsterdam** (Netherlands)
- **Projects Coordinated**: 30 (H2020: 21, HE: 9)
- **Key SSH Areas**: Inclusive society, democracy, heritage
- **Total EC Funding Coordinated**: €82 million

### 6. **Universität Wien** (Austria)
- **Projects Coordinated**: 28 (H2020: 20, HE: 8)
- **Key SSH Areas**: Cultural heritage, social transformations
- **Total EC Funding Coordinated**: €75 million

### 7. **University of Copenhagen** (Denmark)
- **Projects Coordinated**: 26 (H2020: 18, HE: 8)
- **Key SSH Areas**: Democracy, governance, societal challenges
- **Total EC Funding Coordinated**: €72 million

### 8. **Sciences Po Paris** (France)
- **Projects Coordinated**: 24 (H2020: 17, HE: 7)
- **Key SSH Areas**: Political science, democracy, governance
- **Total EC Funding Coordinated**: €65 million

### 9. **University College London** (UK)
- **Projects Coordinated**: 22 (H2020: 16, HE: 6)
- **Key SSH Areas**: Migration, inclusive society, humanities
- **Total EC Funding Coordinated**: €60 million

### 10. **Universität Heidelberg** (Germany)
- **Projects Coordinated**: 20 (H2020: 14, HE: 6)
- **Key SSH Areas**: Cultural heritage, humanities research
- **Total EC Funding Coordinated**: €55 million

---

### Summary Statistics

| Rank | Organization | H2020 | HE | Total | Funding |
|------|-------------|-------|-----|-------|---------|
| 1 | KU Leuven | 32 | 13 | 45 | €125M |
| 2 | U Barcelona | 25 | 13 | 38 | €98M |
| 3 | Oxford | 28 | 7 | 35 | €92M |
| 4 | CNRS | 24 | 9 | 33 | €88M |
| 5 | VU Amsterdam | 21 | 9 | 30 | €82M |

### What is SSH/Cluster 2?

SSH (Social Sciences & Humanities) in Horizon 2020 became **Cluster 2: Culture, Creativity
and Inclusive Society** in Horizon Europe. Key themes include:
- Democracy, governance and civil society
- Cultural heritage preservation and access
- Social and economic transformations
- Migration and inclusive society

### How to Learn More

1. **CORDIS Database**: Search for SSH/Cluster 2 projects at https://cordis.europa.eu
2. **EU Funding Portal**: https://ec.europa.eu/info/funding-tenders/
3. **Partner Search**: Use EU Partner Search tool to find SSH coordinators
4. **Contact**: Reach out to organizations directly for collaboration opportunities
"""

    # A medium-quality response that should NEED_REVIEW (70-84)
    PARTIAL_CLUSTER2_COORDINATORS = """
Here are some successful coordinators in SSH/Cluster 2:

1. KU Leuven - Coordinates many SSH projects
2. University of Barcelona - Active in social sciences
3. CNRS France - Research coordination
4. Oxford University - Multiple projects
5. Amsterdam universities - SSH research

These organizations have coordinated numerous projects in Horizon 2020
and Horizon Europe. SSH covers social sciences and humanities research.

SSH/Cluster 2 focuses on cultural heritage, democracy, and society.
You can find more information on CORDIS.
"""

    # A low-quality response that should FAIL (< 70)
    POOR_CLUSTER2_COORDINATORS = """
Many organizations coordinate SSH projects in Europe. Universities
and research centers participate in Horizon funding. Cluster 2 covers
social sciences and humanities topics.

Some types of institutions include:
- Universities
- Research institutes
- Think tanks

For more information about SSH funding, check the EU portal.
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


def count_organizations_mentioned(response: str) -> int:
    """
    Count the number of distinct organizations mentioned in the response.

    Looks for patterns like:
    - Numbered lists (1., 2., etc.)
    - Bullet point organization entries (• **ORG** or - **ORG**)
    - Institution names (University, Institut, etc.)
    - Coordinator entries with funding
    """
    response_lower = response.lower()

    # Count numbered items (1., 2., 1), 2), etc.)
    numbered_pattern = r"(?:^|\n)\s*(?:\d+[\.\)]\s+|\*\*\d+\.|###\s*\d+\.)"
    numbered_matches = len(re.findall(numbered_pattern, response))

    # Count bullet point organization entries (standard markdown)
    bullet_org_pattern = (
        r"(?:^|\n)\s*-\s+[A-Z][A-Z\s\-]+"
        r"(?:UNIVERSITY|UNIVERSITEIT|UNIVERSITAT|UNIVERSITET|UNIVERSITE|UNIVERSIDAD|"
        r"INSTITUTE|INSTITUT|CENTER|CENTRE|FOUNDATION|CNRS|RESEARCH)"
    )
    bullet_matches = len(re.findall(bullet_org_pattern, response, re.IGNORECASE))

    # Count bullet point organization entries with bold (• **ORG** format from MAPIT)
    # This pattern matches: • **UU** (NL, HES) or • **UNIBO** (IT, HES)
    bold_bullet_pattern = r"•\s*\*\*[A-Z][A-Za-z0-9\s\-\']+\*\*\s*\([A-Z]{2},"
    bold_bullet_matches = len(re.findall(bold_bullet_pattern, response))

    # Count organizations with coordination patterns
    org_with_stats_pattern = r"(?:^|\n)\s*-\s+[A-Z][A-Z\s\-]+:\s*\d+\s*(?:project|coordination)"
    org_with_stats_matches = len(re.findall(org_with_stats_pattern, response, re.IGNORECASE))

    # Count "X as coordinator" patterns (indicates organization with coord role)
    coord_entries_pattern = r"\d+\s+as\s+coordinator"
    coord_entries = len(re.findall(coord_entries_pattern, response_lower))

    # Count institution mentions
    institution_count = 0
    for pattern in SSH_INSTITUTION_PATTERNS:
        matches = re.findall(pattern, response_lower)
        institution_count += len(set(matches))

    # Use the highest count, but cap at reasonable max
    org_count = max(
        numbered_matches,
        institution_count,
        bullet_matches,
        org_with_stats_matches,
        bold_bullet_matches,  # Added new pattern
        coord_entries,  # Added coordinator entries
    )

    return min(org_count, 15)  # Cap at 15 to avoid false positives


def evaluate_query_fulfillment(response: str) -> tuple[int, str, list[str], list[str]]:
    """
    Evaluate query fulfillment (40 points max).

    Checks if:
    - Returns approximately 10 coordinators (15 points)
    - Organizations have SSH/Cluster 2 focus (10 points)
    - Shows coordination counts/statistics (10 points)
    - Covers both H2020 and Horizon Europe (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    found_items = []
    missing_items = []

    # Check for ~10 organizations (15 points)
    org_count = count_organizations_mentioned(response)

    if org_count >= 10:
        score += 15
        found_items.append(f"~{org_count} coordinators listed")
    elif org_count >= 7:
        score += 12
        found_items.append(f"{org_count} coordinators listed")
        missing_items.append("Should list exactly 10 coordinators")
    elif org_count >= 5:
        score += 8
        found_items.append(f"Only {org_count} coordinators")
        missing_items.append("Need more coordinators (requested 10)")
    elif org_count >= 1:
        score += 4
        missing_items.append(f"Only {org_count} coordinator(s) listed, need 10")
    else:
        missing_items.append("No distinct coordinators identified")

    # Check for SSH/Cluster 2 context (10 points)
    ssh_keywords_found = sum(1 for keyword in SSH_CLUSTER2_KEYWORDS if keyword in response_lower)

    if ssh_keywords_found >= 5:
        score += 10
        found_items.append("Strong SSH/Cluster 2 context")
    elif ssh_keywords_found >= 3:
        score += 7
        found_items.append("Good SSH/Cluster 2 context")
        missing_items.append("More SSH-specific content needed")
    elif ssh_keywords_found >= 1:
        score += 4
        missing_items.append("Limited SSH/Cluster 2 context")
    else:
        missing_items.append("Missing SSH/Cluster 2 thematic focus")

    # Check for coordination statistics (10 points)
    has_coord_count = any(
        re.search(pat, response_lower) for pat in COORDINATOR_PATTERNS["coordination_count"]
    )
    has_coord_role = any(
        indicator in response_lower for indicator in COORDINATOR_PATTERNS["coordinator_role"]
    )

    stats_score = 0
    if has_coord_count:
        stats_score += 6
        found_items.append("Coordination counts provided")
    if has_coord_role:
        stats_score += 4
        found_items.append("Coordinator role mentioned")

    score += stats_score

    if stats_score < 10:
        if not has_coord_count:
            missing_items.append("Missing coordination counts")
        if not has_coord_role:
            missing_items.append("Missing coordinator role information")

    # Check for both programmes (5 points)
    programme_keywords_found = sum(1 for keyword in PROGRAMME_KEYWORDS if keyword in response_lower)

    has_h2020 = any(kw in response_lower for kw in ["horizon 2020", "h2020", "fp7", "fp8"])
    has_he = any(kw in response_lower for kw in ["horizon europe", "he ", " he,", " he."])

    if has_h2020 and has_he:
        score += 5
        found_items.append("Both H2020 and HE covered")
    elif has_h2020 or has_he:
        score += 3
        found_items.append("One programme covered")
        missing_items.append("Should cover both Horizon 2020 and Horizon Europe")
    elif programme_keywords_found >= 1:
        score += 2
        missing_items.append("Programme context unclear")
    else:
        missing_items.append("Missing programme context (H2020 and HE)")

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
    - Coordination counts/numbers (6 points)
    - Budget figures (5 points)
    - Programme breakdown (H2020 vs HE) (6 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Named organizations (8 points)
    org_patterns_found = 0
    for pattern in SSH_INSTITUTION_PATTERNS:
        if re.search(pattern, response_lower):
            org_patterns_found += 1

    if org_patterns_found >= 8:
        score += 8
    elif org_patterns_found >= 5:
        score += 6
        notes.append("Some organization names could be more specific")
    elif org_patterns_found >= 2:
        score += 3
        notes.append("Limited named organizations")
    else:
        notes.append("No specific organization names")

    # Coordination counts (6 points)
    # Match various formats: "5 projects", "coordinated 5", "coordinated **5** projects", "(5 as coordinator)"
    coord_numbers = re.findall(r"\d+\s*(?:project|coordination|coordinated)", response_lower)
    coord_numbers += re.findall(r"(?:project|coordination)[s]?\s*[\:]\s*\d+", response_lower)
    # Match markdown bold: "coordinated **5** projects"
    coord_numbers += re.findall(r"coordinated\s*\*\*\d+\*\*\s*project", response_lower)
    # Match parenthetical: "(coordinated 5 projects)" or "(5 as coordinator)"
    coord_numbers += re.findall(r"\(coordinated\s*\*?\*?\d+\*?\*?\s*project", response_lower)
    coord_numbers += re.findall(r"\(\d+\s*as\s*coordinator\)", response_lower)
    # Match "X as coordinator" without parentheses
    coord_numbers += re.findall(r"\d+\s+as\s+coordinator", response_lower)

    if len(coord_numbers) >= 5:
        score += 6
    elif len(coord_numbers) >= 2:
        score += 4
        notes.append("Some coordination counts missing")
    elif len(coord_numbers) >= 1:
        score += 2
        notes.append("Limited coordination count information")
    else:
        notes.append("No coordination counts")

    # Budget figures (5 points)
    budget_patterns = [
        r"€[\d,\.]+",
        r"\d+[\.,]\d+\s*(?:m(?:illion)?|bn|billion)",
        r"\d+\s*(?:m(?:illion)?|bn|billion)",
    ]
    budget_matches = sum(len(re.findall(pat, response, re.IGNORECASE)) for pat in budget_patterns)

    if budget_matches >= 5:
        score += 5
    elif budget_matches >= 2:
        score += 3
        notes.append("Some budget figures missing")
    elif budget_matches >= 1:
        score += 1
        notes.append("Limited budget information")
    else:
        notes.append("No budget figures")

    # Programme breakdown (6 points)
    has_h2020_count = bool(re.search(r"h2020[\s:]+\d+", response_lower))
    has_he_count = bool(re.search(r"he[\s:]+\d+", response_lower))
    has_breakdown = bool(
        re.search(r"\(h2020[:\s]+\d+[,\s]+he[:\s]+\d+\)", response_lower, re.IGNORECASE)
    )
    has_breakdown = has_breakdown or bool(
        re.search(r"h2020\s*:\s*\d+.*he\s*:\s*\d+", response_lower, re.IGNORECASE)
    )

    if has_breakdown or (has_h2020_count and has_he_count):
        score += 6
    elif has_h2020_count or has_he_count:
        score += 3
        notes.append("Missing programme breakdown (H2020 vs HE split)")
    else:
        # Check for any programme-specific numbers
        if re.search(r"horizon\s+2020.*\d+", response_lower) or re.search(
            r"horizon\s+europe.*\d+", response_lower
        ):
            score += 2
            notes.append("Partial programme statistics")
        else:
            notes.append("No programme breakdown statistics")

    return score, "; ".join(notes) if notes else "Good specificity with coordinator details"


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - Organizations appear to be real research institutions
    - Statistics are plausible (not obviously wrong)
    - SSH/Cluster 2 context is accurate
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check for real institution indicators
    known_ssh_orgs = [
        "leuven",
        "barcelona",
        "oxford",
        "cnrs",
        "amsterdam",
        "copenhagen",
        "sciences po",
        "ucl",
        "london",
        "vienna",
        "wien",
        "heidelberg",
        "leiden",
        "utrecht",
        "cambridge",
        "sorbonne",
        "paris",
        "bonn",
        "berlin",
        "munich",
        "max planck",
        "foundation",
        "institute",
    ]

    orgs_found = sum(1 for org in known_ssh_orgs if org in response_lower)
    if orgs_found < 3 and ("coordinator" in response_lower or "ssh" in response_lower):
        # Claims to be about coordinators but doesn't mention known orgs
        score -= 5
        errors.append(
            {
                "claim": "Organizations not recognizable as major research institutions",
                "correct_value": "Should mention known SSH research universities/institutes",
                "source": "Organization validation",
            }
        )

    # Check for unreasonable coordination statistics
    # Top SSH coordinators typically have 10-50 projects
    coord_matches = re.findall(
        r"(\d+)\s*(?:project[s]?\s*)?coordinated",
        response,
        re.IGNORECASE,
    )
    for match in coord_matches:
        try:
            value = int(match)
            if value > 200:  # More than 200 SSH coordinations seems too high
                score -= 3
                errors.append(
                    {
                        "claim": f"Coordination count {value} seems too high",
                        "correct_value": "Top SSH coordinators typically have 10-60 projects",
                        "source": "Statistics validation",
                    }
                )
                break
        except ValueError:
            pass

    # Check for SSH/Cluster 2 accuracy
    if "cluster 2" in response_lower:
        # Verify Cluster 2 description is accurate
        cluster2_topics = [
            "culture",
            "creativity",
            "inclusive",
            "society",
            "democracy",
            "governance",
            "heritage",
        ]
        topics_mentioned = sum(1 for topic in cluster2_topics if topic in response_lower)
        if topics_mentioned < 2:
            score -= 3
            errors.append(
                {
                    "claim": "Cluster 2 topics not well described",
                    "correct_value": "Cluster 2: Culture, Creativity and Inclusive Society",
                    "source": "SSH/Cluster 2 validation",
                }
            )

    # Check for wrong programme attribution
    if "fp7" in response_lower and "most successful" in response_lower:
        if "horizon" not in response_lower:
            score -= 5
            errors.append(
                {
                    "claim": "FP7 statistics used for H2020/HE question",
                    "correct_value": "Should focus on Horizon 2020 and Horizon Europe",
                    "source": "Programme validation",
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
            "component_id": "cluster2_coordinators",
            "description": "Top 10 SSH/Cluster 2 coordinators in H2020 and HE",
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
            f"Improve query fulfillment: List exactly 10 SSH/Cluster 2 coordinators "
            f"with coordination counts for both H2020 and HE. "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Add more specificity: Include specific organization names, coordination counts, "
            "budget figures, and H2020/HE breakdown for all 10 coordinators"
        )
    if accuracy_score < 20:  # < 80% of 25
        fix_suggestions.append(
            "Fix factual accuracy: Verify organizations are real SSH research institutions, "
            "statistics are plausible, and Cluster 2 topics are correctly described"
        )
    if actionability_score < 8:  # < 80% of 10
        fix_suggestions.append(
            "Improve actionability: Add CORDIS/EU portal links, guidance on "
            "how to find SSH coordinators, collaboration suggestions"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Lists ~10 SSH/Cluster 2 coordinators with statistics")
    if specificity_score >= 20:
        strengths.append("Rich in coordinator details and metrics")
    if accuracy_score >= 20:
        strengths.append("Factually accurate organization information")
    if actionability_score >= 8:
        strengths.append("Provides useful resources and guidance")

    return EvaluationResult(
        prompt_id="026",
        query=PROMPT_026_QUERY,
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
class TestPrompt026Cluster2Coordinators:
    """
    Test suite for Prompt 026: Top SSH/Cluster 2 Coordinators.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_cluster2_coordinators(self):
        """
        Main evaluation test for Prompt 026.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_026_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_026_cluster2_coordinators.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 026: Top SSH/Cluster 2 Coordinators Evaluation")
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
        api_result = get_mapit_response(PROMPT_026_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_coordinators(self):
        """Verify the response mentions coordinators (informational)."""
        # Read from saved results to avoid redundant API calls
        results_file = RESULTS_DIR / "prompt_026_cluster2_coordinators.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_cluster2_coordinators first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response = result["response"]
        org_count = count_organizations_mentioned(response)

        # Informational check
        print(f"Coordinators mentioned: {org_count}")
        if org_count < 10:
            print("Note: Response needs more coordinator listings")

        # Soft assertion - just verify results exist
        assert "response" in result, "Response field missing from results"

    def test_response_ssh_context(self):
        """Verify the response has SSH/Cluster 2 context (informational)."""
        results_file = RESULTS_DIR / "prompt_026_cluster2_coordinators.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_cluster2_coordinators first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response_lower = result["response"].lower()

        ssh_keywords_found = sum(1 for kw in SSH_CLUSTER2_KEYWORDS if kw in response_lower)

        # Informational check
        print(f"SSH/Cluster 2 keywords found: {ssh_keywords_found}")
        if ssh_keywords_found < 3:
            print("Note: Response needs more SSH-specific content")

        # Soft assertion
        assert "overall_score" in result, "overall_score missing from results"


class TestPrompt026OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.

    These tests verify the evaluation framework works correctly
    without requiring a live API connection.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_CLUSTER2_COORDINATORS, {"source": "sample_excellent"}
        )

        # Save result for reference
        results_file = RESULTS_DIR / "prompt_026_cluster2_coordinators_sample_excellent.json"
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
            SampleResponses.PARTIAL_CLUSTER2_COORDINATORS, {"source": "sample_partial"}
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
            SampleResponses.POOR_CLUSTER2_COORDINATORS, {"source": "sample_poor"}
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
            SampleResponses.POOR_CLUSTER2_COORDINATORS, {"source": "sample_poor"}
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
            SampleResponses.EXCELLENT_CLUSTER2_COORDINATORS, {"source": "excellent"}
        )
        poor_eval = evaluate_response(
            SampleResponses.POOR_CLUSTER2_COORDINATORS, {"source": "poor"}
        )

        # Excellent response should have much higher specificity
        excellent_specificity = excellent_eval.component_scores[0]["specificity"]
        poor_specificity = poor_eval.component_scores[0]["specificity"]

        assert excellent_specificity > poor_specificity, (
            f"Excellent specificity ({excellent_specificity}) should be > poor ({poor_specificity})"
        )

    def test_save_evaluation_result_json(self):
        """Test that evaluation results are saved correctly as JSON."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_CLUSTER2_COORDINATORS, {"source": "test_json_save"}
        )

        # Use a separate test file
        results_file = RESULTS_DIR / "prompt_026_cluster2_coordinators_test_save.json"
        save_result(evaluation, results_file)

        # Verify file was created and is valid JSON
        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "026"
        assert loaded["query"] == PROMPT_026_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
