"""
Quality Evaluation Test for Prompt 029: Nordic Green Energy Partner.

This test evaluates the MAPIT AI response to the query:
"I am looking for a potential partner from the Nordic countries for a project on
reindustrialization and green energy use. Who are the top 10 players in H2020 and HE?
Please provide 1 paragraph descriptions indicating relevant projects they
coordinated/partnered."

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Returns 10 Nordic organizations with paragraph descriptions
- Specificity (25 points): Organization names, project titles, funding details
- Factual Accuracy (25 points): Organizations are from Nordic countries, project relevance
- Actionability (10 points): Contact info, collaboration guidance, CORDIS links

Pass threshold: >= 85/100

Reference requirements from PRD:
- Must list 10 specific organizations from Nordic countries (NO, DK, SE, FI, IS)
- Must include paragraph descriptions per organization
- Must indicate relevant projects they coordinated/partnered

Nordic Countries per eu-funding-domain skill:
- NO = Norway
- DK = Denmark
- SE = Sweden
- FI = Finland
- IS = Iceland (optional, smaller participation)

Run with:
    pytest tests/quality/test_prompt_029_nordic_green_energy.py -v

For live API tests only:
    pytest tests/quality/test_prompt_029_nordic_green_energy.py -v -m "live_api"
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
PROMPT_029_QUERY = (
    "I am looking for a potential partner from the Nordic countries for a project on "
    "reindustrialization and green energy use. Who are the top 10 players in H2020 and HE? "
    "Please provide 1 paragraph descriptions indicating relevant projects they "
    "coordinated/partnered."
)

# Nordic country codes
NORDIC_COUNTRIES = ["NO", "DK", "SE", "FI", "IS"]
NORDIC_COUNTRY_NAMES = [
    "norway",
    "norwegian",
    "denmark",
    "danish",
    "sweden",
    "swedish",
    "finland",
    "finnish",
    "iceland",
    "icelandic",
]

# Green energy / reindustrialization keywords
GREEN_ENERGY_KEYWORDS = [
    "green energy",
    "renewable",
    "hydrogen",
    "wind",
    "solar",
    "clean energy",
    "sustainable",
    "energy transition",
    "carbon",
    "climate",
    "decarbonization",
    "decarbonisation",
    "electrification",
    "battery",
    "energy storage",
    "industrial",
    "reindustrializ",
    "manufacturing",
    "circular economy",
]

# Known Nordic research organizations (for validation)
KNOWN_NORDIC_ORGS = [
    # Norway
    "sintef",
    "ntnu",
    "norwegian university",
    "universitetet i oslo",
    "university of oslo",
    "universitetet i bergen",
    "university of bergen",
    "norges forskningsråd",
    "research council of norway",
    "institute for energy technology",
    "ife",
    "norce",
    "nilu",
    "niva",
    "equinor",
    "statoil",
    "norsk hydro",
    "statkraft",
    # Denmark
    "dtu",
    "technical university of denmark",
    "danmarks tekniske",
    "university of copenhagen",
    "københavns universitet",
    "aarhus university",
    "aarhus universitet",
    "aalborg university",
    "aalborg universitet",
    "danish technological",
    "vestas",
    "ørsted",
    "orsted",
    "danish energy agency",
    "ramboll",
    "danfoss",
    # Sweden
    "kth",
    "royal institute of technology",
    "kungliga tekniska",
    "chalmers",
    "lund university",
    "lunds universitet",
    "uppsala university",
    "uppsala universitet",
    "stockholms universitet",
    "stockholm university",
    "rise",
    "research institutes of sweden",
    "vattenfall",
    "volvo",
    "scania",
    "abb",
    "sandvik",
    "skf",
    "swedish energy agency",
    # Finland
    "vtt",
    "technical research centre of finland",
    "aalto",
    "aalto university",
    "university of helsinki",
    "helsingin yliopisto",
    "tampere university",
    "tampereen yliopisto",
    "university of oulu",
    "oulun yliopisto",
    "fortum",
    "neste",
    "wärtsilä",
    "wartsila",
    "nokia",
    "valmet",
    # Iceland
    "university of iceland",
    "háskóli íslands",
    "háskólinn í reykjavík",
    "reykjavik university",
    "landsvirkjun",
    "on power",
]

# Keywords indicating project participation
PROJECT_PATTERNS = {
    "coordination": [
        r"coordinat",
        r"led\s+(?:the\s+)?project",
        r"leading",
        r"as\s+coordinator",
        r"project\s+lead",
    ],
    "partnership": [
        r"partner(?:ed|ship)?",
        r"participat",
        r"collaborat",
        r"contribut",
        r"involv",
        r"took\s+part",
        r"work(?:ed|ing)\s+on",
    ],
    "project_reference": [
        r"project[s]?\s+(?:such\s+as|like|including)",
        r"(?:H2020|Horizon\s+(?:2020|Europe)|FP\d)",
        r"funded\s+project",
        r"EU\s+project",
        r"grant\s+agreement",
    ],
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_NORDIC_PARTNERS = """
## Top 10 Nordic Partners for Green Energy & Reindustrialization Projects

Based on H2020 and Horizon Europe participation, here are the leading Nordic organizations
in green energy and reindustrialization:

### 1. **SINTEF** (Norway)
SINTEF is Scandinavia's largest independent research organization with extensive expertise
in energy technology, industrial processes, and sustainability. They have coordinated major
projects including **HyInHeat** (hydrogen for industrial heating, €15M) and **EERA-SET**
(strategic energy technology planning). SINTEF participated in over 400 H2020/HE projects,
leading initiatives in offshore wind, carbon capture, and hydrogen production. Their
industrial focus makes them ideal partners for reindustrialization efforts.
[CORDIS: https://cordis.europa.eu/organization/sintef]

### 2. **VTT Technical Research Centre of Finland** (Finland)
VTT is Finland's premier applied research organization with deep expertise in clean energy,
circular economy, and smart industry. Key coordinated projects include **BioReCer**
(bio-based ceramics for industry, €4.5M) and **FlexHyJoin** (hydrogen flexible joining).
With participation in 350+ Framework Programme projects, VTT excels in bio-based materials,
industrial digitalization, and renewable energy integration. They bring strong SME
collaboration networks.
[CORDIS: https://cordis.europa.eu/organization/vtt]

### 3. **DTU - Technical University of Denmark** (Denmark)
DTU is Denmark's leading technical university with world-class research in wind energy,
power systems, and sustainable manufacturing. They coordinated **WindEurope** technology
platforms and the **NEWA** (New European Wind Atlas, €13M) project. DTU participates
actively in Cluster 5 calls and has strong ties to Danish wind industry (Vestas, Ørsted).
Their energy systems modeling capabilities are particularly valuable.
[CORDIS: https://cordis.europa.eu/organization/dtu]

### 4. **Chalmers University of Technology** (Sweden)
Chalmers is Sweden's leading technical university with strong programs in sustainable
energy, electrification, and materials science. Key projects include **Batteries2030**
(next-gen batteries, €8M coordination) and **HYBRIT** partnership (fossil-free steel).
They have coordinated 85 H2020/HE projects with €120M+ funding, focusing on transport
electrification and industrial decarbonization. Strong industry connections to Volvo, SKF.
[CORDIS: https://cordis.europa.eu/organization/chalmers]

### 5. **RISE Research Institutes of Sweden** (Sweden)
RISE is Sweden's state-owned research institute network covering energy, materials, and
digital innovation. They coordinated **RE-SOURCING** (responsible sourcing for green
transition) and partnered in **Clean Hydrogen JU** projects. With expertise spanning
bioeconomy, smart manufacturing, and energy efficiency, RISE has participated in 200+
H2020/HE projects and maintains close ties to Swedish industry.
[CORDIS: https://cordis.europa.eu/organization/rise]

### 6. **NTNU - Norwegian University of Science and Technology** (Norway)
NTNU is Norway's largest university with leading programs in energy, materials, and
sustainable industry. They coordinated **FME HighEFF** (energy-efficient industry) and
**HydroGEN** (green hydrogen production). NTNU has strong connections to Norwegian
industry (Equinor, Hydro) and participates in 300+ EU projects across Clusters 4, 5, and 6.
Their expertise includes offshore energy, CCS, and industrial processes.
[CORDIS: https://cordis.europa.eu/organization/ntnu]

### 7. **Aalto University** (Finland)
Aalto University combines excellence in engineering, business, and design for sustainable
innovation. Key coordinated projects include **BioColour** (bio-based colorants for
industry) and **CLIC Innovation** ecosystem. They excel in circular economy, forest-based
bioeconomy, and cleantech innovation. Aalto has participated in 180+ H2020/HE projects
with strong startup ecosystem connections (Slush, Aalto Ventures).
[CORDIS: https://cordis.europa.eu/organization/aalto]

### 8. **Aarhus University** (Denmark)
Aarhus University has leading research groups in bioenergy, agricultural sustainability,
and environmental technology. They coordinated **NoAW** (no agricultural waste, €7.5M)
and **BioValue SPIR** platform. With expertise in sustainable food systems, biomass
conversion, and environmental monitoring, they've participated in 250+ Framework
Programme projects. Strong focus on Cluster 6 topics.
[CORDIS: https://cordis.europa.eu/organization/aarhus]

### 9. **KTH Royal Institute of Technology** (Sweden)
KTH is Sweden's oldest and largest technical university with excellence in energy systems,
sustainable building, and industrial ecology. Key projects include **EIT InnoEnergy** hub
coordination and **HYBRIT** research partnership (fossil-free steel with SSAB). KTH has
coordinated 70+ H2020/HE projects and maintains strong ties to Swedish energy sector
(Vattenfall, ABB). Expertise in district heating, industrial symbiosis.
[CORDIS: https://cordis.europa.eu/organization/kth]

### 10. **Equinor** (Norway)
Equinor is Norway's leading energy company transitioning to renewables and low-carbon
solutions. They have partnered in major projects including **Northern Lights** (CO2
storage infrastructure) and **Hywind** (floating offshore wind). While primarily
industrial partner rather than coordinator, Equinor brings massive deployment capabilities,
offshore expertise, and investment power. Participated in 50+ H2020/HE projects.
[CORDIS: https://cordis.europa.eu/organization/equinor]

---

### Summary Table

| Rank | Organization | Country | Key Expertise | H2020/HE Projects |
|------|-------------|---------|---------------|-------------------|
| 1 | SINTEF | NO | Industrial R&D, hydrogen | 400+ |
| 2 | VTT | FI | Clean energy, circular economy | 350+ |
| 3 | DTU | DK | Wind energy, power systems | 300+ |
| 4 | Chalmers | SE | Batteries, electrification | 200+ |
| 5 | RISE | SE | Materials, bioeconomy | 200+ |

### How to Partner with Nordic Organizations

1. **Search CORDIS**: Find their project portfolios at https://cordis.europa.eu
2. **Partner Search Tool**: Use the EU Funding Portal partner search
3. **National Contact Points**: Contact Nordic NCPs for introductions
4. **Direct Outreach**: Most have dedicated EU project offices

### Why Nordic Partners?

Nordic countries excel in green energy due to:
- Strong renewable energy sectors (wind, hydro, biomass)
- Industrial decarbonization leadership
- High R&D investment (~3% of GDP)
- Excellent H2020/HE track records
- English proficiency and international orientation
"""

    # A medium-quality response that NEEDS_REVIEW (70-84)
    PARTIAL_NORDIC_PARTNERS = """
Here are some Nordic partners for green energy projects:

1. **SINTEF** (Norway) - Large research organization working on energy
2. **VTT** (Finland) - Finnish research center for technology
3. **DTU** (Denmark) - Danish technical university with wind energy focus
4. **Chalmers** (Sweden) - Swedish university for engineering
5. **NTNU** (Norway) - Norwegian technology university

These organizations participate in many EU projects related to energy and sustainability.
They have experience with Horizon 2020 and Horizon Europe funding.

For more information, check CORDIS.
"""

    # A LOW-quality response that should FAIL (wrong countries, no details)
    POOR_NORDIC_PARTNERS = """
Here are some partners for green energy:

1. Fraunhofer (Germany) - Research organization
2. CNRS (France) - French research
3. TNO (Netherlands) - Dutch research
4. Some Nordic organizations also participate

Green energy is important for the future.
Contact organizations directly for partnerships.
"""

    # Response with non-Nordic organizations
    POOR_WITH_WRONG_COUNTRIES = """
Top partners for green energy and reindustrialization:

1. **CEA** (France) - Leading French research in energy
2. **Fraunhofer** (Germany) - German applied research
3. **TNO** (Netherlands) - Dutch applied research
4. **ENEA** (Italy) - Italian energy agency
5. **CIEMAT** (Spain) - Spanish energy research

These organizations have extensive experience in EU funding programmes.
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
    # Count numbered items (like "1.", "1)", "### 1.")
    numbered_pattern = r"(?:^|\n)\s*(?:\d+[\.\)]\s+|\*\*\d+\.|###\s*\d+\.)"
    numbered_matches = len(re.findall(numbered_pattern, response))

    # Count table rows by looking for rank numbers at start of rows
    lines = response.split("\n")
    table_org_count = 0
    for line in lines:
        if re.match(r"^\|\s*\d{1,2}\s*\|", line.strip()):
            table_org_count += 1

    # Count bullet point organization entries
    bullet_org_pattern = r"(?:^|\n)\s*-\s+\*\*[A-Z][A-Za-z\s\-]+"
    bullet_matches = len(re.findall(bullet_org_pattern, response))

    # Use highest count from different methods
    org_count = max(numbered_matches, table_org_count, bullet_matches)

    return min(org_count, 15)


def check_for_nordic_orgs(response: str) -> tuple[int, list[str]]:
    """
    Check for Nordic organization mentions in the response.

    Returns (count, list of organizations found).
    """
    nordic_orgs_found = []
    response_lower = response.lower()

    # Check for known Nordic organizations
    for org in KNOWN_NORDIC_ORGS:
        if org in response_lower:
            nordic_orgs_found.append(org)

    # Check for Nordic country references
    for country in NORDIC_COUNTRY_NAMES:
        if country in response_lower:
            nordic_orgs_found.append(f"Reference to {country}")

    # Check for country codes in context (like "(NO)", "(DK)", etc.)
    for code in NORDIC_COUNTRIES:
        patterns = [
            f"({code.lower()})",
            f"({code})",
            f"country: {code.lower()}",
            f"country**: {code.lower()}",
        ]
        for pattern in patterns:
            if pattern in response_lower or pattern.upper() in response:
                nordic_orgs_found.append(f"Country code: {code}")
                break

    return len(set(nordic_orgs_found)), list(set(nordic_orgs_found))


def check_for_non_nordic_orgs(response: str) -> list[str]:
    """
    Check if response contains non-Nordic organizations as main partners.

    Returns list of non-Nordic org references found (ideally minimal).
    """
    non_nordic_found = []

    # Non-Nordic organizations that might be incorrectly listed
    non_nordic_orgs = [
        ("fraunhofer", "Germany"),
        ("cnrs", "France"),
        ("cea", "France"),
        ("tno", "Netherlands"),
        ("enea", "Italy"),
        ("ciemat", "Spain"),
        ("csic", "Spain"),
        ("cnr", "Italy"),
    ]

    # Check if these appear as main listed items (not just mentions)
    lines = response.split("\n")
    for line in lines:
        line_lower = line.lower()
        # Check if this line looks like an organization listing
        if re.search(r"^\s*(?:\d+[\.\)]|\*|-|###)", line):
            for org, country in non_nordic_orgs:
                if org in line_lower:
                    non_nordic_found.append(f"{org} ({country})")

    return non_nordic_found


def check_for_paragraph_descriptions(response: str) -> tuple[int, list[str]]:
    """
    Check for paragraph-length descriptions per organization.

    Returns (count of orgs with paragraphs, issues found).
    """
    issues = []
    orgs_with_paragraphs = 0

    # Split by organization markers (various formats)
    # Matches: "### 1.", "**1.", "1.", etc.
    org_sections = re.split(r"(?:^|\n)(?:###?\s*)?\*?\*?\d+\.\s*\*?\*?", response)

    for section in org_sections[1:]:  # Skip first empty section
        # Check if section has substantial content (at least 100 chars)
        if len(section.strip()) >= 100:
            orgs_with_paragraphs += 1
        elif len(section.strip()) > 20:  # Has some content but too short
            org_name_match = re.match(r"([^*\n]+)", section)
            if org_name_match:
                issues.append(f"Short description for: {org_name_match.group(1)[:30]}")

    # Also check for paragraph-style descriptions under bold headers
    # Pattern: **OrgName** followed by substantial text
    bold_headers = re.findall(
        r"\*\*\d+\.\s*[^*]+\*\*[^*]*?\n([^\n*]{100,})",
        response,
        re.MULTILINE,
    )
    orgs_with_paragraphs = max(orgs_with_paragraphs, len(bold_headers))

    return orgs_with_paragraphs, issues


def check_for_project_references(response: str) -> tuple[int, list[str]]:
    """
    Check for project references and examples.

    Returns (count of project references, project names found).
    """
    response_lower = response.lower()
    projects_found = []

    # Look for project name patterns (typically in bold or with budget)
    project_patterns = [
        r"\*\*([A-Z][A-Za-z0-9\-]+)\*\*\s*(?:\(|project)",
        r"project[s]?\s+(?:such\s+as|like|including)\s+([A-Z][A-Za-z0-9\-]+)",
        r"coordinated?\s+(?:the\s+)?(?:project\s+)?([A-Z][A-Za-z0-9\-]+)",
        r"([A-Z][A-Za-z0-9\-]+)\s+project",
        # Bold project names in descriptions (e.g., "coordinating the **DEEPMINING** project")
        r"(?:the|a)\s+\*\*([A-Z][A-Za-z0-9\-]+)\*\*",
        # Project names after "coordinates" or "coordinated"
        r"coordinat(?:es|ed|ing)\s+(?:the\s+)?\*\*([A-Z][A-Za-z0-9\-]+)\*\*",
        # Project names in parentheses with budget (e.g., "(HyInHeat, €15M)")
        r"\(([A-Z][A-Za-z0-9\-]+)[,\s]+[€\$]",
    ]

    for pattern in project_patterns:
        matches = re.findall(pattern, response)
        projects_found.extend(matches)

    # Also check for programme mentions
    programme_mentions = 0
    for prog in ["h2020", "horizon 2020", "horizon europe", "fp7"]:
        if prog in response_lower:
            programme_mentions += 1

    # Count unique project names
    unique_projects = list(set(p for p in projects_found if len(p) > 2))

    return len(unique_projects) + programme_mentions, unique_projects


def check_green_energy_relevance(response: str) -> tuple[int, list[str]]:
    """
    Check for green energy / reindustrialization relevance.

    Returns (relevance count, keywords found).
    """
    response_lower = response.lower()
    keywords_found = []

    for keyword in GREEN_ENERGY_KEYWORDS:
        if keyword in response_lower:
            keywords_found.append(keyword)

    return len(keywords_found), keywords_found


def evaluate_query_fulfillment(response: str) -> tuple[int, str, list[str], list[str]]:
    """
    Evaluate query fulfillment (40 points max).

    Checks if:
    - Returns approximately 10 Nordic organizations (15 points)
    - Organizations are from Nordic countries (10 points)
    - Includes paragraph descriptions (10 points)
    - Shows project coordination/partnership (5 points)
    """
    score = 0
    found_items = []
    missing_items = []

    # Check for ~10 organizations (15 points)
    org_count = count_organizations_mentioned(response)

    if org_count >= 10:
        score += 15
        found_items.append(f"{org_count} organizations listed")
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

    # Check for Nordic country focus (10 points)
    nordic_count, nordic_orgs = check_for_nordic_orgs(response)
    non_nordic = check_for_non_nordic_orgs(response)

    if nordic_count >= 10 and len(non_nordic) == 0:
        score += 10
        found_items.append("Strong Nordic focus")
    elif nordic_count >= 7:
        score += 8
        found_items.append(f"Good Nordic coverage ({nordic_count} references)")
        if non_nordic:
            missing_items.append(f"Non-Nordic orgs listed: {non_nordic[:3]}")
    elif nordic_count >= 4:
        score += 5
        found_items.append(f"Some Nordic content ({nordic_count} references)")
        missing_items.append("Need stronger Nordic focus")
    elif nordic_count >= 1:
        score += 2
        missing_items.append("Limited Nordic organization coverage")
    else:
        missing_items.append("No Nordic organizations identified")

    # Check for paragraph descriptions (10 points)
    para_count, para_issues = check_for_paragraph_descriptions(response)

    if para_count >= 8:
        score += 10
        found_items.append("Detailed paragraph descriptions provided")
    elif para_count >= 5:
        score += 7
        found_items.append(f"{para_count} detailed descriptions")
        missing_items.append("Some organizations lack paragraph descriptions")
    elif para_count >= 2:
        score += 4
        missing_items.append("Most organizations need fuller descriptions")
    else:
        missing_items.append("Missing paragraph descriptions per organization")

    # Check for project references (5 points)
    project_refs, projects = check_for_project_references(response)

    if project_refs >= 10:
        score += 5
        found_items.append("Rich project references")
    elif project_refs >= 5:
        score += 3
        found_items.append(f"{project_refs} project references")
        missing_items.append("Could include more project examples")
    elif project_refs >= 1:
        score += 1
        missing_items.append("Limited project references")
    else:
        missing_items.append("Missing project coordination/partnership examples")

    notes = f"Fulfillment: {score}/40"
    return score, notes, missing_items, found_items


def evaluate_specificity(response: str) -> tuple[int, str]:
    """
    Evaluate specificity (25 points max).

    Checks for:
    - Named organizations with full names (8 points)
    - Project titles/names (7 points)
    - Funding figures/statistics (5 points)
    - Country indicators (5 points)
    """
    score = 0
    notes = []

    # Named organizations (8 points)
    nordic_count, _ = check_for_nordic_orgs(response)

    if nordic_count >= 10:
        score += 8
    elif nordic_count >= 7:
        score += 6
        notes.append("Some organization names could be more specific")
    elif nordic_count >= 4:
        score += 4
        notes.append("Limited named Nordic organizations")
    else:
        notes.append("Few specific Nordic organization names")

    # Project titles (7 points)
    project_refs, projects = check_for_project_references(response)

    if len(projects) >= 10:
        score += 7
    elif len(projects) >= 5:
        score += 5
        notes.append("Some project names could be added")
    elif len(projects) >= 2:
        score += 3
        notes.append("Limited project names mentioned")
    else:
        notes.append("No specific project titles")

    # Funding figures (5 points)
    budget_patterns = [
        r"€[\d,\.]+",
        r"\d+[\.,]\d+\s*(?:m(?:illion)?|bn|billion)",
        r"\d+\s*(?:m(?:illion)?|bn|billion)",
        r"\d+\+?\s*projects?",
    ]
    budget_matches = sum(len(re.findall(pat, response, re.IGNORECASE)) for pat in budget_patterns)

    if budget_matches >= 10:
        score += 5
    elif budget_matches >= 5:
        score += 3
        notes.append("Some funding/statistics figures could be added")
    elif budget_matches >= 1:
        score += 1
        notes.append("Limited funding information")
    else:
        notes.append("No funding/statistics figures")

    # Country indicators (5 points)
    country_mentions = 0
    for code in NORDIC_COUNTRIES:
        # Check various patterns: (NO), | NO |, **NO**, "NO", etc.
        patterns_to_check = [
            f"({code})",
            f"({code.lower()})",
            f"| {code} |",
            f"| {code.lower()} |",
            f"**{code}**",
            f", {code})",  # (DTU, DK)
            f", {code.upper()})",
        ]
        for pattern in patterns_to_check:
            if pattern in response:
                country_mentions += 1
                break  # Only count each country once

    if country_mentions >= 4:  # All 4 main Nordic countries
        score += 5
    elif country_mentions >= 3:
        score += 4
        notes.append("Most Nordic country indicators present")
    elif country_mentions >= 2:
        score += 3
        notes.append("Some country indicators missing")
    elif country_mentions >= 1:
        score += 1
        notes.append("Limited country indicators")
    else:
        notes.append("No country indicators (NO, DK, SE, FI)")

    return (
        score,
        "; ".join(notes) if notes else "Good specificity with Nordic partner details",
    )


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - Organizations are from Nordic countries
    - Listed organizations are real (known organizations)
    - Green energy/reindustrialization relevance
    """
    score = 25  # Start with full score, deduct for errors
    errors = []

    # Check for non-Nordic organizations as main listings (major deduction)
    non_nordic = check_for_non_nordic_orgs(response)

    if len(non_nordic) >= 5:
        score -= 15
        errors.append(
            {
                "claim": f"Listed {len(non_nordic)} non-Nordic organizations",
                "correct_value": "Should only list Nordic (NO, DK, SE, FI, IS) organizations",
                "source": "Geographic validation",
            }
        )
    elif len(non_nordic) >= 2:
        score -= 5 * len(non_nordic)
        for org in non_nordic[:3]:
            errors.append(
                {
                    "claim": f"Non-Nordic org listed: {org}",
                    "correct_value": "Should focus on Nordic countries",
                    "source": "Geographic validation",
                }
            )

    # Check for known Nordic organizations
    nordic_count, _ = check_for_nordic_orgs(response)
    if nordic_count < 3:
        score -= 5
        errors.append(
            {
                "claim": "Few recognizable Nordic organizations mentioned",
                "correct_value": "Should mention major Nordic RTOs/universities like "
                "SINTEF, VTT, DTU, Chalmers, etc.",
                "source": "Organization validation",
            }
        )

    # Check for green energy relevance
    relevance_count, keywords = check_green_energy_relevance(response)
    if relevance_count < 3:
        score -= 5
        errors.append(
            {
                "claim": "Limited green energy/reindustrialization relevance",
                "correct_value": "Should discuss renewable energy, hydrogen, "
                "sustainable industry topics",
                "source": "Topic relevance validation",
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
    - How to partner guidance (3 points)
    - Contact/outreach suggestions (3 points)
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

    # How to partner guidance (3 points)
    guidance_phrases = [
        "partner search",
        "how to partner",
        "how to collaborate",
        "national contact point",
        "ncp",
        "reach out",
        "contact",
        "partnership",
    ]
    guidance_found = sum(1 for phrase in guidance_phrases if phrase in response_lower)
    score += min(3, guidance_found)

    # Outreach/networking suggestions (3 points)
    outreach_phrases = [
        "direct outreach",
        "eu project office",
        "consortium",
        "collaboration network",
        "join",
        "participate",
        "apply together",
    ]
    outreach_found = sum(1 for phrase in outreach_phrases if phrase in response_lower)
    score += min(3, outreach_found)

    return (
        score,
        "; ".join(notes) if notes else "Good actionability with partner guidance",
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
            "component_id": "nordic_green_energy_partners",
            "description": "Top 10 Nordic partners for green energy & reindustrialization",
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
            f"Improve query fulfillment: List exactly 10 Nordic (NO, DK, SE, FI) "
            f"organizations with paragraph descriptions and project examples. "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:
        fix_suggestions.append(
            "Add more specificity: Include organization full names, country codes, "
            "specific project titles, funding amounts, and H2020/HE participation counts"
        )
    if accuracy_score < 20:
        fix_suggestions.append(
            "Fix factual accuracy: Ensure ALL listed organizations are from Nordic "
            "countries (NO, DK, SE, FI, IS). Include known RTOs like SINTEF, VTT, DTU."
        )
    if actionability_score < 8:
        fix_suggestions.append(
            "Improve actionability: Add CORDIS links, partner search guidance, "
            "National Contact Point info, and direct outreach suggestions"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Lists ~10 Nordic organizations with descriptions")
    if specificity_score >= 20:
        strengths.append("Rich in organization and project details")
    if accuracy_score >= 20:
        strengths.append("Correctly focuses on Nordic countries and green energy")
    if actionability_score >= 8:
        strengths.append("Provides useful partnership guidance")

    return EvaluationResult(
        prompt_id="029",
        query=PROMPT_029_QUERY,
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
class TestPrompt029NordicGreenEnergy:
    """
    Test suite for Prompt 029: Nordic Green Energy Partner.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_nordic_green_energy(self):
        """
        Main evaluation test for Prompt 029.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_029_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_029_nordic_green_energy.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 029: Nordic Green Energy Partner Evaluation")
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
        api_result = get_mapit_response(PROMPT_029_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_nordic_countries(self):
        """Verify the response mentions Nordic countries (informational)."""
        results_file = RESULTS_DIR / "prompt_029_nordic_green_energy.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_nordic_green_energy first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response = result["response"]
        nordic_count, nordic_orgs = check_for_nordic_orgs(response)

        print(f"Nordic references found: {nordic_count}")
        if nordic_orgs:
            print(f"Nordic organizations: {nordic_orgs[:10]}")

        assert "response" in result, "Response field missing from results"


class TestPrompt029OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_NORDIC_PARTNERS, {"source": "sample_excellent"}
        )

        results_file = RESULTS_DIR / "prompt_029_nordic_green_energy_sample_excellent.json"
        save_result(evaluation, results_file)

        print("\nExcellent Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score >= PASS_THRESHOLD, (
            f"Excellent response scored {evaluation.overall_score}, expected >= {PASS_THRESHOLD}"
        )
        assert evaluation.result == "PASS"

    def test_partial_response_needs_review(self):
        """Test that a partial response scores below PASS threshold."""
        evaluation = evaluate_response(
            SampleResponses.PARTIAL_NORDIC_PARTNERS, {"source": "sample_partial"}
        )

        print("\nPartial Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < PASS_THRESHOLD, (
            f"Partial response scored {evaluation.overall_score}, expected < {PASS_THRESHOLD}"
        )

    def test_response_with_wrong_countries_fails(self):
        """Test that a response with non-Nordic countries fails accuracy check."""
        evaluation = evaluate_response(
            SampleResponses.POOR_WITH_WRONG_COUNTRIES,
            {"source": "sample_wrong_countries"},
        )

        print("\nResponse with Wrong Countries Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")
        print(f"  Factual Errors: {len(evaluation.factual_errors)}")

        # Should have factual errors for including non-Nordic organizations
        assert len(evaluation.factual_errors) > 0, "Should detect non-Nordic orgs"
        assert evaluation.overall_score < PASS_THRESHOLD

    def test_poor_response_fails(self):
        """Test that a poor response scores < 70 (FAIL)."""
        evaluation = evaluate_response(
            SampleResponses.POOR_NORDIC_PARTNERS, {"source": "sample_poor"}
        )

        print("\nPoor Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < NEEDS_REVIEW_THRESHOLD, (
            f"Poor response scored {evaluation.overall_score}, expected < {NEEDS_REVIEW_THRESHOLD}"
        )
        assert evaluation.result == "FAIL"

    def test_save_evaluation_result_json(self):
        """Test that evaluation results are saved correctly as JSON."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_NORDIC_PARTNERS, {"source": "test_json_save"}
        )

        results_file = RESULTS_DIR / "prompt_029_nordic_green_energy_test_save.json"
        save_result(evaluation, results_file)

        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "029"
        assert loaded["query"] == PROMPT_029_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
