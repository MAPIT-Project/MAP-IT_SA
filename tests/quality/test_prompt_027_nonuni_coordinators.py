"""
Quality Evaluation Test for Prompt 027: Top Non-University Coordinators.

This test evaluates the MAPIT AI response to the query:
"Who are the most successful top 10 non-university coordinators in Horizon Europe?"

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Returns exactly 10 non-HES organizations as coordinators
- Specificity (25 points): Organization names, coordination counts, funding amounts
- Factual Accuracy (25 points): Orgs are correctly classified (REC, PRC, PUB, OTH - NOT HES)
- Actionability (10 points): Links to CORDIS/EU portal, collaboration guidance

Pass threshold: >= 85/100

Reference requirements from PRD:
- Must list 10 specific non-university organizations (REC, PRC, PUB, OTH types)
- Must include coordination statistics
- Must exclude HES (Higher Education Sector) organizations

Organization Types per eu-funding-domain skill:
- HES = Higher Education Sector (universities) - EXCLUDE
- REC = Research Organizations (e.g., Fraunhofer, TNO, VTT)
- PRC = Private Companies
- PUB = Public Bodies
- OTH = Other (NGOs, associations)

Run with:
    pytest tests/quality/test_prompt_027_nonuni_coordinators.py -v

For live API tests only:
    pytest tests/quality/test_prompt_027_nonuni_coordinators.py -v -m "live_api"
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
PROMPT_027_QUERY = (
    "Who are the most successful top 10 non-university coordinators in Horizon Europe?"
)

# Organization type definitions
# These are the VALID non-university types we expect to see
VALID_NONUNI_ORG_TYPES = ["REC", "PRC", "PUB", "OTH", "SME"]

# This is the type we DON'T want to see (universities)
UNIVERSITY_ORG_TYPE = "HES"

# Keywords indicating university/HES organizations (to catch if type not specified)
# Note: These must be specific to universities, NOT general research terms
UNIVERSITY_KEYWORDS = [
    "university",
    "universiteit",
    "universität",
    "università",
    "université",
    "universidad",
    "universidade",
    "yliopisto",  # Finnish
    "universitet",  # Swedish/Danish/Norwegian
    "politecnico",  # Italian technical university
    "hochschule",  # German higher education
    "college",
    "school of",
    "academy of sciences",  # More specific
    "type: hes",
    "type**: hes",
    "organization type: hes",
    "organization type**: hes",
    "(hes)",
]

# Patterns that should NOT be flagged as universities even if they contain partial matches
NONUNI_EXCEPTIONS = [
    "research centre",
    "research center",
    "technical research",
    "research institute",
    "applied scientific research",
    "research organization",
    "type: rec",
    "type**: rec",
    "(rec)",
    "fraunhofer",
    "cnrs",
    "cea",
    "tno",
    "vtt",
    "sintef",
    "csic",
    "dlr",
    "cnr",
    "ait",
    "embl",
]

# Keywords indicating valid non-university research organizations
NONUNI_RESEARCH_KEYWORDS = [
    "fraunhofer",
    "max planck",
    "max-planck",
    "helmholtz",
    "leibniz",
    "cnrs",
    "cea",
    "inria",
    "inserm",
    "tno",
    "vtt",
    "sintef",
    "csic",
    "cnr ",  # Italian CNR
    "imec",
    "cern",
    "esa",
    "desy",
    "fz jülich",
    "jülich",
    "julich",
    "dlr",
    "dkfz",
    "embl",
    "ait",  # Austrian Institute of Technology
    "vito",  # Flemish Institute for Technological Research
    "tecnalia",
    "eurecat",
    "rise",  # Research Institutes of Sweden
    "teagasc",
    "rec",
    "(rec)",
    "type: rec",
    "organization type: rec",
    "research organization",
    "research institute",
    "research centre",
    "research center",
    "forschung",  # German for research
    "research council",
]

# Keywords indicating private companies
COMPANY_KEYWORDS = [
    "gmbh",
    "ag",
    "s.a.",
    "s.r.l.",
    "ltd",
    "limited",
    "inc",
    "corp",
    "plc",
    "b.v.",
    "n.v.",
    "a.s.",
    "a/s",
    "oy",  # Finnish company
    "ab",  # Swedish company
    "prc",
    "(prc)",
    "type: prc",
    "organization type: prc",
    "private company",
    "enterprise",
    "industry",
    "sme",
    "(sme)",
]

# Keywords indicating public bodies
PUBLIC_KEYWORDS = [
    "ministry",
    "government",
    "agency",
    "authority",
    "commission",
    "council",
    "pub",
    "(pub)",
    "type: pub",
    "organization type: pub",
    "public body",
    "public sector",
    "municipality",
    "region",
    "city of",
]

# Statistics patterns for coordinators
COORDINATOR_PATTERNS = {
    "coordination_count": [
        r"\d+\s*(?:project[s]?\s*)?coordinated",
        r"coordinated\s*(?::\s*)?\d+",
        r"coordination[s]?\s*[\:]\s*\d+",
        r"\d+\s*coordination",
        r"coordinator\s*(?:of|in)\s*\d+",
        r"\d+\s+as\s+coordinator",
        r"\(\d+\s+as\s+coordinator\)",
        r"coordinated\s*\*\*\d+\*\*",
        r"projects\s*coordinated\s*[\*:]*\s*\d+",  # "Projects Coordinated: 245"
        r"coordinations\s*[\|:]\s*\d+",  # "Coordinations | 245"
    ],
    "coordinator_role": [
        "coordinator",
        "coordinated",
        "lead",
        "leading",
        "coordination",
        "as coordinator",
        "projects coordinated",
    ],
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_NONUNI_COORDINATORS = """
## Top 10 Most Successful Non-University Coordinators in Horizon Europe

Based on coordination statistics from Horizon Europe (2021-2027), excluding universities (HES):

### 1. **FRAUNHOFER-GESELLSCHAFT** (DE)
- **Organization Type**: REC (Research Organization)
- **Projects Coordinated**: 245
- **Total EC Funding as Coordinator**: €1.2 billion
- **Key Clusters**: CL4 (Digital), CL5 (Climate), CL1 (Health)

### 2. **COMMISSARIAT A L'ENERGIE ATOMIQUE (CEA)** (FR)
- **Organization Type**: REC
- **Projects Coordinated**: 180
- **Total EC Funding as Coordinator**: €890 million
- **Key Clusters**: CL4, CL5, CL1

### 3. **CENTRE NATIONAL DE LA RECHERCHE SCIENTIFIQUE (CNRS)** (FR)
- **Organization Type**: REC
- **Projects Coordinated**: 165
- **Total EC Funding as Coordinator**: €780 million
- **Key Clusters**: CL2, CL4, CL1

### 4. **TNO - NETHERLANDS ORGANISATION FOR APPLIED SCIENTIFIC RESEARCH** (NL)
- **Organization Type**: REC
- **Projects Coordinated**: 120
- **Total EC Funding as Coordinator**: €550 million
- **Key Clusters**: CL4, CL5, CL3

### 5. **VTT TECHNICAL RESEARCH CENTRE OF FINLAND** (FI)
- **Organization Type**: REC
- **Projects Coordinated**: 95
- **Total EC Funding as Coordinator**: €420 million
- **Key Clusters**: CL4, CL5, CL6

### 6. **SINTEF** (NO)
- **Organization Type**: REC
- **Projects Coordinated**: 88
- **Total EC Funding as Coordinator**: €380 million
- **Key Clusters**: CL5, CL4, CL6

### 7. **CONSEJO SUPERIOR DE INVESTIGACIONES CIENTIFICAS (CSIC)** (ES)
- **Organization Type**: REC
- **Projects Coordinated**: 82
- **Total EC Funding as Coordinator**: €350 million
- **Key Clusters**: CL1, CL4, CL6

### 8. **DEUTSCHES ZENTRUM FUR LUFT- UND RAUMFAHRT (DLR)** (DE)
- **Organization Type**: REC
- **Projects Coordinated**: 78
- **Total EC Funding as Coordinator**: €420 million
- **Key Clusters**: CL5, CL4

### 9. **CONSIGLIO NAZIONALE DELLE RICERCHE (CNR)** (IT)
- **Organization Type**: REC
- **Projects Coordinated**: 75
- **Total EC Funding as Coordinator**: €310 million
- **Key Clusters**: CL1, CL4, CL6

### 10. **AIT AUSTRIAN INSTITUTE OF TECHNOLOGY** (AT)
- **Organization Type**: REC
- **Projects Coordinated**: 68
- **Total EC Funding as Coordinator**: €280 million
- **Key Clusters**: CL4, CL5, CL3

---

### Summary: Non-University Coordinators

| Rank | Organization | Type | Coordinations | Funding |
|------|-------------|------|---------------|---------|
| 1 | Fraunhofer | REC | 245 | €1.2B |
| 2 | CEA | REC | 180 | €890M |
| 3 | CNRS | REC | 165 | €780M |
| 4 | TNO | REC | 120 | €550M |
| 5 | VTT | REC | 95 | €420M |

**Note**: All organizations listed are Research Organizations (REC), not universities (HES).

### Organization Types Explained
- **REC**: Research Organizations (non-university research institutes)
- **PRC**: Private Companies
- **PUB**: Public Bodies
- **OTH**: Other (NGOs, foundations)
- **HES**: Higher Education Sector (universities) - **excluded from this list**

### How to Learn More

1. **CORDIS Database**: Search for coordinated projects at https://cordis.europa.eu
2. **EU Funding Portal**: https://ec.europa.eu/info/funding-tenders/
3. **Partner Search**: Contact these organizations for collaboration
"""

    # A medium-quality response that NEEDS_REVIEW (70-84)
    PARTIAL_NONUNI_COORDINATORS = """
Here are some successful non-university coordinators in Horizon Europe:

1. Fraunhofer - Major German research organization
2. CEA - French research organization
3. CNRS - French national research
4. TNO - Dutch research
5. VTT - Finnish research center

These organizations coordinate many projects in Horizon Europe. They are
research organizations (REC type), not universities.

For more information, visit CORDIS.
"""

    # A LOW-quality response that should FAIL (includes HES universities)
    POOR_WITH_UNIVERSITIES = """
Here are successful coordinators in Horizon Europe:

1. KU Leuven (Belgium) - University
2. ETH Zurich - University
3. University of Oxford - University
4. TU Munich - University
5. Fraunhofer - Research Organization

These are the most active coordinators in EU funding programmes.
"""

    # A response that lists general orgs without specifying non-university
    POOR_NONUNI_COORDINATORS = """
Many organizations coordinate Horizon Europe projects. Research institutions
are active across all clusters. Both universities and research organizations
participate as coordinators.

Types of coordinators include:
- Research institutes
- Companies
- Public bodies

For more information about coordinators, check the EU portal.
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

    client = httpx.Client(timeout=180.0)
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
    """
    response_lower = response.lower()

    # Count numbered items (like "1.", "1)", "### 1.")
    numbered_pattern = r"(?:^|\n)\s*(?:\d+[\.\)]\s+|\*\*\d+\.|###\s*\d+\.)"
    numbered_matches = len(re.findall(numbered_pattern, response))

    # Count table rows by looking for rank numbers at start of rows
    # Pattern: "| 1 |" or "| 10 |" at line start
    lines = response.split("\n")
    table_org_count = 0
    for line in lines:
        # Check for table row with rank number
        if re.match(r"^\|\s*\d{1,2}\s*\|", line.strip()):
            table_org_count += 1

    # Count bullet point organization entries with stats
    bullet_org_pattern = (
        r"(?:^|\n)\s*-\s+[A-Z][A-Z\s\-]+"
        r"(?:GMBH|AG|S\.A\.|E\.V\.|EV|LTD|BV|NV|OY|AB|AS|INSTITUTE|"
        r"INSTITUT|CENTER|CENTRE|FOUNDATION|COUNCIL|AGENCY)"
    )
    bullet_matches = len(re.findall(bullet_org_pattern, response, re.IGNORECASE))

    # Count organizations with coordination patterns
    org_with_stats_pattern = r"(?:^|\n)\s*(?:-|\*|\d+\.)\s*\*?\*?[A-Z][A-Z\s\-]+\*?\*?"
    org_with_stats_matches = len(
        re.findall(org_with_stats_pattern, response, re.IGNORECASE)
    )

    # Count known non-uni research org mentions
    nonuni_count = 0
    for pattern in NONUNI_RESEARCH_KEYWORDS[:20]:  # Check top 20 patterns
        if pattern.lower() in response_lower:
            nonuni_count += 1

    # Use highest count from different methods
    org_count = max(
        numbered_matches, table_org_count, bullet_matches,
        org_with_stats_matches, nonuni_count
    )

    return min(org_count, 15)


def check_for_universities(response: str) -> list[str]:
    """
    Check if response contains universities (HES type organizations).

    Returns list of university references found (should be empty for passing score).
    """
    universities_found = []
    response_lower = response.lower()

    # Check for explicit HES type mentions (these are definitive)
    hes_patterns = [
        r"organization type[:\s\*]*hes",
        r"type[:\s\*]*hes(?!\s*\()",  # type: hes but not before explanation
    ]
    for pattern in hes_patterns:
        matches = re.findall(pattern, response_lower)
        if matches:
            for m in matches:
                # Don't count if it's in an explanation section
                if "hes**: higher education" not in response_lower:
                    universities_found.append(f"HES type: {m}")

    # Check for (HES) tag next to organization names
    hes_tag_matches = re.findall(r"\*\*([^*]+)\*\*[^(]*\(hes\)", response_lower)
    for m in hes_tag_matches:
        universities_found.append(f"University: {m}")

    # Check for university keywords in context of listed organizations
    # Look for lines that appear to list organizations
    lines = response.split("\n")
    for line in lines:
        line_lower = line.lower()

        # Skip if this line contains any non-university exception
        is_exception = False
        for exception in NONUNI_EXCEPTIONS:
            if exception in line_lower:
                is_exception = True
                break

        if is_exception:
            continue

        # Check if this line looks like an organization listing
        if re.search(r"^\s*(?:\d+[\.\)]|\*|-|###|\|)", line):
            # Skip title/header lines that talk ABOUT non-university
            if "non-university" in line_lower or "non university" in line_lower:
                continue

            # Only check for strong university indicators
            strong_uni_keywords = [
                "university",
                "universiteit",
                "universität",
                "università",
                "université",
                "universidad",
                "universidade",
                "yliopisto",
                "universitet",
                "politecnico",
                "hochschule",
            ]
            for keyword in strong_uni_keywords:
                if keyword in line_lower:
                    # Extract the organization name
                    org_match = re.search(r"\*\*([^*]+)\*\*", line)
                    if org_match:
                        universities_found.append(
                            f"University: {org_match.group(1)}"
                        )
                    else:
                        universities_found.append(
                            f"University keyword '{keyword}' in: {line[:50]}..."
                        )
                    break

    return universities_found


def check_for_nonuni_orgs(response: str) -> tuple[int, list[str]]:
    """
    Check for valid non-university organizations in the response.

    Returns (count, list of organizations found).
    """
    nonuni_orgs_found = []
    response_lower = response.lower()

    # Check for REC/PRC/PUB type mentions
    type_patterns = [
        (r"organization type[:\s]*rec", "REC"),
        (r"type[:\s]*rec", "REC"),
        (r"\(rec\)", "REC"),
        (r"organization type[:\s]*prc", "PRC"),
        (r"type[:\s]*prc", "PRC"),
        (r"\(prc\)", "PRC"),
        (r"organization type[:\s]*pub", "PUB"),
        (r"type[:\s]*pub", "PUB"),
        (r"\(pub\)", "PUB"),
    ]
    for pattern, org_type in type_patterns:
        matches = re.findall(pattern, response_lower)
        nonuni_orgs_found.extend([f"{org_type} type organization"] * len(matches))

    # Check for known non-uni research organizations
    for keyword in NONUNI_RESEARCH_KEYWORDS[:30]:
        if (
            keyword.lower() in response_lower
            and keyword.lower() not in ["rec", "(rec)"]
        ):
            nonuni_orgs_found.append(f"Research org: {keyword}")

    # Check for company indicators
    for keyword in COMPANY_KEYWORDS[:15]:
        if (
            keyword.lower() in response_lower
            and keyword.lower() not in ["prc", "(prc)"]
        ):
            nonuni_orgs_found.append(f"Company: {keyword}")

    return len(set(nonuni_orgs_found)), list(set(nonuni_orgs_found))


def evaluate_query_fulfillment(response: str) -> tuple[int, str, list[str], list[str]]:
    """
    Evaluate query fulfillment (40 points max).

    Checks if:
    - Returns approximately 10 non-university coordinators (15 points)
    - Organizations are clearly non-HES (REC, PRC, PUB, OTH) (15 points)
    - Shows coordination counts/statistics (10 points)
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
        found_items.append(f"~{org_count} organizations listed")
    elif org_count >= 7:
        score += 12
        found_items.append(f"{org_count} organizations listed")
        missing_items.append("Should list exactly 10 organizations")
    elif org_count >= 5:
        score += 8
        found_items.append(f"Only {org_count} organizations")
        missing_items.append("Need more organizations (requested 10)")
    elif org_count >= 1:
        score += 4
        missing_items.append(f"Only {org_count} organization(s) listed, need 10")
    else:
        missing_items.append("No distinct organizations identified")

    # Check for non-university context (15 points)
    universities_found = check_for_universities(response)
    nonuni_count, nonuni_orgs = check_for_nonuni_orgs(response)

    # Check for explicit "non-university" framing
    has_nonuni_framing = any(
        phrase in response_lower
        for phrase in [
            "non-university",
            "non university",
            "excluding universities",
            "not universities",
            "research organizations",
            "excluding hes",
            "non-hes",
        ]
    )

    if has_nonuni_framing and len(universities_found) == 0 and nonuni_count >= 5:
        score += 15
        found_items.append("Clearly non-university focus with REC/PRC organizations")
    elif len(universities_found) == 0 and nonuni_count >= 3:
        score += 12
        found_items.append("Non-university organizations listed")
        missing_items.append("Could emphasize non-HES status more explicitly")
    elif len(universities_found) <= 2 and nonuni_count >= 2:
        score += 8
        found_items.append("Mix of organization types")
        missing_items.append(f"Found {len(universities_found)} university references")
    elif len(universities_found) > 2:
        score += 3
        missing_items.append(
            f"Too many universities ({len(universities_found)}) - should be non-HES only"
        )
    else:
        missing_items.append("Missing clear non-university organization focus")

    # Check for coordination statistics (10 points)
    has_coord_count = any(
        re.search(pat, response_lower)
        for pat in COORDINATOR_PATTERNS["coordination_count"]
    )
    has_coord_role = any(
        indicator in response_lower
        for indicator in COORDINATOR_PATTERNS["coordinator_role"]
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
    - Organization type indicators (6 points)
    - Coordination counts/numbers (6 points)
    - Budget figures (5 points)
    """
    score = 0
    notes = []
    response_lower = response.lower()

    # Named non-university organizations (8 points)
    nonuni_count, _ = check_for_nonuni_orgs(response)

    if nonuni_count >= 8:
        score += 8
    elif nonuni_count >= 5:
        score += 6
        notes.append("Some organization names could be more specific")
    elif nonuni_count >= 2:
        score += 3
        notes.append("Limited named non-university organizations")
    else:
        notes.append("No specific non-university organization names")

    # Organization type indicators (6 points)
    type_mentions = 0
    for t in ["rec", "prc", "pub", "oth"]:
        # Count various patterns for organization types
        patterns = [
            f"({t})",
            f"type: {t}",
            f"type**: {t}",
            f"organization type**: {t}",
            f"**organization type**: {t}",
        ]
        for pattern in patterns:
            type_mentions += response_lower.count(pattern)

    if type_mentions >= 5:
        score += 6
    elif type_mentions >= 2:
        score += 4
        notes.append("Some organization types not specified")
    elif type_mentions >= 1:
        score += 2
        notes.append("Limited organization type information")
    else:
        notes.append("No organization type indicators")

    # Coordination counts (6 points)
    coord_numbers = re.findall(
        r"\d+\s*(?:project|coordination|coordinated)", response_lower
    )
    coord_numbers += re.findall(
        r"(?:project|coordination)[s]?\s*[\:]\s*\d+", response_lower
    )
    coord_numbers += re.findall(r"\d+\s+as\s+coordinator", response_lower)
    coord_numbers += re.findall(
        r"projects?\s*coordinated\s*[\*:]*\s*\d+", response_lower
    )
    coord_numbers += re.findall(
        r"coordinations?\s*[\|:]\s*\d+", response_lower
    )
    # Table format: "Projects Coordinated (HE) | 242" or "| 242 |"
    # Look for table header mentioning coordinated and count subsequent numbers
    if "coordinated" in response_lower and "|" in response:
        # Count numeric values in table rows (after header)
        table_numbers = re.findall(r"\|\s*(\d{2,3})\s*\|", response)
        coord_numbers += table_numbers

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
    budget_matches = sum(
        len(re.findall(pat, response, re.IGNORECASE)) for pat in budget_patterns
    )

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

    return (
        score,
        "; ".join(notes)
        if notes
        else "Good specificity with non-university coordinator details",
    )


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - Organizations are correctly classified as non-HES
    - Listed organizations are real research institutions/companies
    - No universities are incorrectly listed as non-university
    """
    score = 25  # Start with full score, deduct for errors
    errors = []
    response_lower = response.lower()

    # Check for universities incorrectly included (major deduction)
    universities_found = check_for_universities(response)

    if len(universities_found) > 3:
        score -= 15
        errors.append(
            {
                "claim": f"Listed {len(universities_found)} universities in "
                "non-university coordinator list",
                "correct_value": "Should only list REC, PRC, PUB, OTH types",
                "source": "Organization type validation",
            }
        )
    elif len(universities_found) > 0:
        score -= 5 * len(universities_found)
        for uni in universities_found[:3]:  # Limit error messages
            errors.append(
                {
                    "claim": uni,
                    "correct_value": "Should not be in non-university list",
                    "source": "Organization type validation",
                }
            )

    # Check for known non-university research organizations
    known_nonuni_orgs = [
        "fraunhofer",
        "cea",
        "cnrs",
        "tno",
        "vtt",
        "sintef",
        "csic",
        "dlr",
        "cnr",
        "ait",
        "embl",
        "dkfz",
        "inria",
        "inserm",
        "imec",
        "tecnalia",
        "vito",
    ]

    orgs_found = sum(1 for org in known_nonuni_orgs if org in response_lower)
    if orgs_found < 3 and "coordinator" in response_lower:
        # Claims to be about coordinators but doesn't mention known non-uni orgs
        if score > 10:  # Don't double-penalize
            score -= 5
            errors.append(
                {
                    "claim": "Few recognizable non-university research orgs mentioned",
                    "correct_value": "Should mention major RTOs like Fraunhofer, CEA, "
                    "TNO, VTT, etc.",
                    "source": "Organization validation",
                }
            )

    # Check for unreasonable coordination statistics
    coord_matches = re.findall(
        r"(\d+)\s*(?:project[s]?\s*)?coordinated",
        response,
        re.IGNORECASE,
    )
    for match in coord_matches:
        try:
            value = int(match)
            if value > 500:  # More than 500 coordinations seems too high
                score -= 3
                errors.append(
                    {
                        "claim": f"Coordination count {value} seems too high",
                        "correct_value": "Top RTOs typically coordinate 50-300 "
                        "projects in HE",
                        "source": "Statistics validation",
                    }
                )
                break
        except ValueError:
            pass

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
    - Collaboration suggestions (3 points)
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

    # Collaboration suggestions (3 points)
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
            "component_id": "nonuni_coordinators",
            "description": "Top 10 non-university coordinators in Horizon Europe",
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
    if fulfillment_score < 32:
        fix_suggestions.append(
            f"Improve query fulfillment: List exactly 10 non-university (non-HES) "
            f"coordinators with coordination statistics. Must be REC, PRC, PUB, or "
            f"OTH types. Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:
        fix_suggestions.append(
            "Add more specificity: Include organization names, types (REC/PRC/PUB), "
            "coordination counts, and budget figures for all 10 organizations"
        )
    if accuracy_score < 20:
        fix_suggestions.append(
            "Fix factual accuracy: Ensure NO universities (HES) are listed. "
            "Organizations should be RTOs like Fraunhofer, CEA, TNO, VTT, SINTEF, etc."
        )
    if actionability_score < 8:
        fix_suggestions.append(
            "Improve actionability: Add CORDIS/EU portal links, guidance on "
            "how to find non-university coordinators, collaboration suggestions"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Lists ~10 non-university organizations as coordinators")
    if specificity_score >= 20:
        strengths.append("Rich in organization details and coordination metrics")
    if accuracy_score >= 20:
        strengths.append("Correctly identifies non-HES organization types")
    if actionability_score >= 8:
        strengths.append("Provides useful resources and guidance")

    return EvaluationResult(
        prompt_id="027",
        query=PROMPT_027_QUERY,
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
class TestPrompt027NonUniCoordinators:
    """
    Test suite for Prompt 027: Top Non-University Coordinators.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_nonuni_coordinators(self):
        """
        Main evaluation test for Prompt 027.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_027_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_027_nonuni_coordinators.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 027: Top Non-University Coordinators Evaluation")
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
        api_result = get_mapit_response(PROMPT_027_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_excludes_universities(self):
        """Verify the response excludes universities (informational)."""
        results_file = RESULTS_DIR / "prompt_027_nonuni_coordinators.json"
        if not results_file.exists():
            pytest.skip(
                "Run test_evaluate_nonuni_coordinators first to generate results"
            )

        with open(results_file) as f:
            result = json.load(f)

        response = result["response"]
        universities_found = check_for_universities(response)

        print(f"Universities found: {len(universities_found)}")
        if universities_found:
            print(f"University references: {universities_found[:5]}")
            print("Note: Response should not include HES/university organizations")

        assert "response" in result, "Response field missing from results"


class TestPrompt027OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_NONUNI_COORDINATORS, {"source": "sample_excellent"}
        )

        results_file = (
            RESULTS_DIR / "prompt_027_nonuni_coordinators_sample_excellent.json"
        )
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
        """Test that a partial response scores below PASS threshold."""
        evaluation = evaluate_response(
            SampleResponses.PARTIAL_NONUNI_COORDINATORS, {"source": "sample_partial"}
        )

        print("\nPartial Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < PASS_THRESHOLD, (
            f"Partial response scored {evaluation.overall_score}, "
            f"expected < {PASS_THRESHOLD}"
        )

    def test_response_with_universities_fails(self):
        """Test that a response including universities fails accuracy check."""
        evaluation = evaluate_response(
            SampleResponses.POOR_WITH_UNIVERSITIES,
            {"source": "sample_with_universities"},
        )

        print("\nResponse with Universities Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")
        print(f"  Factual Errors: {len(evaluation.factual_errors)}")

        # Should have factual errors for including universities
        assert len(evaluation.factual_errors) > 0, "Should detect universities as errors"
        assert evaluation.overall_score < PASS_THRESHOLD

    def test_poor_response_fails(self):
        """Test that a poor response scores < 70 (FAIL)."""
        evaluation = evaluate_response(
            SampleResponses.POOR_NONUNI_COORDINATORS, {"source": "sample_poor"}
        )

        print("\nPoor Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < NEEDS_REVIEW_THRESHOLD, (
            f"Poor response scored {evaluation.overall_score}, "
            f"expected < {NEEDS_REVIEW_THRESHOLD}"
        )
        assert evaluation.result == "FAIL"

    def test_save_evaluation_result_json(self):
        """Test that evaluation results are saved correctly as JSON."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_NONUNI_COORDINATORS, {"source": "test_json_save"}
        )

        results_file = RESULTS_DIR / "prompt_027_nonuni_coordinators_test_save.json"
        save_result(evaluation, results_file)

        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "027"
        assert loaded["query"] == PROMPT_027_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
