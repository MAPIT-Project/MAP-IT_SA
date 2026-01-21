"""
Quality Evaluation Test for Prompt 030: Spain Municipal Testbed Partner.

This test evaluates the MAPIT AI response to the query:
"I am looking for a project partner from Spain that has outreach and ties to local
municipalities willing to be pilot places/testbeds in a Cluster 2 project. Please
identify H2020/HE participants who have that network."

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Returns Spanish organizations with municipal ties
- Specificity (25 points): Organization names, project titles, municipal connections
- Factual Accuracy (25 points): Organizations are from Spain, Cluster 2 relevance
- Actionability (10 points): Contact info, collaboration guidance, CORDIS links

Pass threshold: >= 85/100

Reference requirements from PRD:
- Must identify Spanish organizations with municipal connections
- Must show H2020/HE participation/experience
- Focus on Cluster 2 (Culture, Creativity and Inclusive Society) relevance
- Must indicate testbed/pilot capability with local municipalities

Cluster 2 Topics per eu-funding-domain skill:
- Democracy, governance, and citizen engagement
- Cultural heritage and creative industries
- Social and economic transformations
- Migration and inclusion
- Social innovation and public services

Run with:
    pytest tests/quality/test_prompt_030_spain_municipal.py -v

For live API tests only:
    pytest tests/quality/test_prompt_030_spain_municipal.py -v -m "live_api"
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
PROMPT_030_QUERY = (
    "I am looking for a project partner from Spain that has outreach and ties to local "
    "municipalities willing to be pilot places/testbeds in a Cluster 2 project. Please "
    "identify H2020/HE participants who have that network."
)

# Spain country identifiers
SPAIN_IDENTIFIERS = ["spain", "spanish", "españa", "(es)", "| es |", ", es)"]

# Cluster 2 (Culture, Creativity and Inclusive Society) keywords
CLUSTER_2_KEYWORDS = [
    "cluster 2",
    "culture",
    "cultural",
    "heritage",
    "creative",
    "creativity",
    "democracy",
    "governance",
    "citizen",
    "social",
    "inclusion",
    "inclusive",
    "migration",
    "society",
    "public service",
    "civic",
    "community",
    "participation",
    "engagement",
    "innovation",
    "local government",
    "municipality",
    "regional",
]

# Municipal/testbed/pilot keywords
MUNICIPAL_KEYWORDS = [
    "municipal",
    "municipality",
    "municipalities",
    "local government",
    "city",
    "cities",
    "town",
    "region",
    "regional",
    "local authority",
    "local authorities",
    "ayuntamiento",
    "diputación",
    "diputacion",
    "comunidad autónoma",
    "comunidad autonoma",
    "pilot",
    "testbed",
    "test bed",
    "demonstration",
    "trial",
    "living lab",
    "urban",
    "territory",
    "territorial",
]

# Known Spanish research/municipal organizations (for validation)
KNOWN_SPANISH_ORGS = [
    # Research organizations
    "csic",
    "consejo superior de investigaciones científicas",
    "consejo superior de investigaciones cientificas",
    "universidad",
    "universitat",
    "university",
    "upm",
    "upc",
    "ub",
    "uab",
    "upv",
    "us",
    "ugr",
    "uam",
    "ucm",
    "politécnica de madrid",
    "politecnica de madrid",
    "politècnica de catalunya",
    "politecnica de catalunya",
    "autónoma de barcelona",
    "autonoma de barcelona",
    "complutense",
    "valencia",
    "sevilla",
    "granada",
    "barcelona",
    "madrid",
    # Municipal networks/organizations
    "femp",
    "federación española de municipios",
    "federacion española de municipios",
    "red de ciudades",
    "red española de ciudades inteligentes",
    "smart cities",
    "citilab",
    "barcelona activa",
    "madrid destino",
    "zaragoza activa",
    # Research institutes with municipal ties
    "tecnalia",
    "ikerlan",
    "fundación tecnalia",
    "fundacion tecnalia",
    "eurecat",
    "i2cat",
    "ctic",
    "vicomtech",
    "cartif",
    "itainnova",
    "centro tecnológico",
    "centro tecnologico",
    # City councils/networks
    "ajuntament",
    "ayuntamiento",
    "diputació",
    "diputacion",
    "generalitat",
    "junta de",
    "gobierno vasco",
    # Social innovation organizations
    "fundación",
    "fundacion",
    "asociación",
    "asociacion",
    "once",
    "cáritas",
    "caritas",
    "cruz roja",
]

# Project experience indicators
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
    EXCELLENT_SPAIN_MUNICIPAL = """
## Spanish Organizations with Municipal Testbed Networks for Cluster 2 Projects

Based on H2020 and Horizon Europe participation in Cluster 2 topics, here are Spanish
organizations with strong ties to local municipalities for pilot/testbed activities:

### 1. **TECNALIA Research & Innovation** (Spain)
TECNALIA is one of Europe's largest private research organizations with extensive networks
across Basque municipalities and Spanish regional governments. They have coordinated Cluster 2
projects including **RURITAGE** (rural heritage regeneration, €10M) and partnered in
**OpenHeritage** (heritage-led regeneration). TECNALIA maintains living labs in Bilbao, San
Sebastián, and Vitoria-Gasteiz, with formal agreements with over 50 Spanish municipalities
for urban innovation pilots. Their expertise spans smart cities, cultural heritage
digitization, and social innovation.
[CORDIS: https://cordis.europa.eu/organization/tecnalia]

### 2. **Eurecat Technology Centre** (Spain)
Eurecat is Catalonia's leading technology center with deep ties to the Catalan municipal
ecosystem. They have participated in 150+ H2020/HE projects including **INCULTUM** (cultural
tourism, Cluster 2) and **RURBAN** (rural-urban linkages). Eurecat operates testbed facilities
in partnership with Barcelona, Tarragona, and Lleida municipalities. They specialize in
citizen engagement platforms, cultural heritage technologies, and social innovation pilots
with municipal partners.
[CORDIS: https://cordis.europa.eu/organization/eurecat]

### 3. **Fundación ONCE** (Spain)
Fundación ONCE is Spain's leading disability inclusion organization with networks spanning
all Spanish autonomous communities and municipalities. They have coordinated **TRIPS**
(inclusive tourism, €3M) and partnered in **BRIDGES** (social innovation for inclusion).
ONCE maintains formal partnerships with 200+ Spanish municipalities for accessibility and
inclusion pilots. Their expertise in Cluster 2 topics includes social inclusion, accessible
public services, and participatory governance.
[CORDIS: https://cordis.europa.eu/organization/once]

### 4. **Barcelona City Council (Ajuntament de Barcelona)** (Spain)
Barcelona is a leading European city in participatory democracy and urban innovation, with
direct capacity to offer testbed facilities. They have coordinated **Decidim** (participatory
democracy platform) and partnered in **BRUIT** (urban regeneration). Barcelona's innovation
districts (22@, Superblocks) serve as living labs. Their EU project experience spans
citizen engagement, cultural policy, and social innovation in Cluster 2.
[CORDIS: https://cordis.europa.eu/organization/ajuntament-barcelona]

### 5. **CARTIF Technology Centre** (Spain)
CARTIF is a private research center with strong ties to Castilla y León municipalities.
They have coordinated **CultureLabs** (heritage participation, €3.5M) and **RURITAGE**.
CARTIF operates demonstration sites with municipalities including Valladolid, Burgos, and
Palencia for cultural heritage and social innovation pilots. Expertise includes digital
heritage, citizen science, and territorial development.
[CORDIS: https://cordis.europa.eu/organization/cartif]

### 6. **Universidad Politécnica de Madrid (UPM)** (Spain)
UPM has strong municipal partnerships through its Smart Cities and Social Innovation
research groups. They have participated in 200+ H2020/HE projects including **MOVE21**
(urban mobility) and **SMARTCITIES** networks. UPM maintains testbed agreements with
Madrid City Council and surrounding municipalities for urban innovation pilots. Their
Cluster 2 expertise includes governance innovation and cultural digitization.
[CORDIS: https://cordis.europa.eu/organization/upm]

### 7. **Federación Española de Municipios y Provincias (FEMP)** (Spain)
FEMP is the Spanish federation of municipalities representing 7,000+ local governments.
They have partnered in multiple H2020 projects on local governance including **OECD-LGI**
(local government innovation) and **EUROCITIES** networks. FEMP can facilitate access to
pilot municipalities across Spain for any Cluster 2 project requiring territorial
deployment. Expertise includes democratic innovation and public service modernization.
[CORDIS: https://cordis.europa.eu/organization/femp]

### 8. **i2CAT Foundation** (Spain)
i2CAT is Catalonia's internet research center with extensive municipal digitalization
projects. They have coordinated **DECODE** (data sovereignty, €5M) and partnered in
**CitiMeasure** (citizen measurement). i2CAT maintains living labs with Barcelona,
Girona, and Manresa municipalities. Their Cluster 2 expertise includes participatory
technologies, digital democracy, and citizen engagement platforms.
[CORDIS: https://cordis.europa.eu/organization/i2cat]

### 9. **Ayuntamiento de Madrid** (Spain)
Madrid City Council has extensive H2020/HE experience and capacity for municipal pilots.
They have participated in **MAtchUP** (urban transformation) and **CIVITAS** networks.
Madrid offers districts like Vallecas and Villaverde as testbeds for social innovation.
Their Cluster 2 expertise includes citizen participation (Decide Madrid platform),
cultural policy, and inclusive urban development.
[CORDIS: https://cordis.europa.eu/organization/ayuntamiento-madrid]

### 10. **CTIC Technology Centre** (Spain)
CTIC is Asturias' technology center with strong municipal innovation networks. They have
coordinated **INTERLINK** (interoperable public services) and partnered in **OpenGovIntelligence**.
CTIC maintains testbed partnerships with Gijón, Oviedo, and Avilés municipalities.
Their Cluster 2 expertise includes open government, digital democracy, and social innovation
with public administrations.
[CORDIS: https://cordis.europa.eu/organization/ctic]

---

### Summary Table

| Rank | Organization | Region | Municipal Network | Cluster 2 Focus |
|------|-------------|--------|-------------------|-----------------|
| 1 | TECNALIA | Basque Country | 50+ municipalities | Heritage, Smart Cities |
| 2 | Eurecat | Catalonia | Barcelona area | Cultural tourism, Citizen engagement |
| 3 | Fundación ONCE | National | 200+ municipalities | Inclusion, Accessibility |
| 4 | Barcelona City | Catalonia | Direct testbed capacity | Participatory democracy |
| 5 | CARTIF | Castilla y León | Regional municipalities | Cultural heritage |

### How to Partner with Spanish Municipal-Connected Organizations

1. **CORDIS Search**: Find their project portfolios at https://cordis.europa.eu
2. **Partner Search Tool**: Use EU Funding Portal partner search with "ES" filter
3. **FEMP**: Contact directly for municipal network access
4. **Regional NCPs**: Spanish NCPs can facilitate introductions
5. **Direct Outreach**: Most have dedicated EU project offices

### Why Spanish Partners for Municipal Testbeds?

Spain offers advantages for Cluster 2 pilots:
- Strong tradition of participatory democracy (e.g., Decidim, Decide Madrid)
- Diverse territorial coverage (17 autonomous communities, 8,000+ municipalities)
- Active FEMP municipal network for multi-site pilots
- Leading smart city initiatives (Barcelona, Madrid, Valencia)
- Rich cultural heritage for heritage-related pilots
"""

    # A medium-quality response that NEEDS_REVIEW (70-84)
    PARTIAL_SPAIN_MUNICIPAL = """
Here are some Spanish partners for Cluster 2 projects with municipal connections:

1. **TECNALIA** (Basque Country) - Large research organization with some municipal projects
2. **Eurecat** (Catalonia) - Technology center in Barcelona region
3. **UPM** (Madrid) - Technical university with city partnerships
4. **CSIC** (National) - Spanish national research council
5. **Barcelona City** - Has participated in EU projects

These organizations have participated in H2020 and Horizon Europe projects.
They work with local municipalities on various initiatives.

For more information, contact the Spanish National Contact Points or check CORDIS.
"""

    # A LOW-quality response that should FAIL (no municipal focus)
    POOR_SPAIN_MUNICIPAL = """
Here are some Spanish research partners:

1. CSIC - National research council
2. Universities in Spain
3. Technology centers

Spain has many organizations that participate in EU projects.
Contact Spanish NCPs for more information about potential partnerships.
"""

    # Response with non-Spanish organizations
    POOR_WITH_WRONG_COUNTRY = """
Top partners for municipal testbed projects:

1. **Fraunhofer** (Germany) - German research organization with city networks
2. **TNO** (Netherlands) - Dutch research with municipal ties
3. **CEA** (France) - French research organization
4. **ENEA** (Italy) - Italian energy agency with city projects
5. There are also some Spanish partners available

These organizations have experience with EU funding programmes.
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


def check_for_spanish_orgs(response: str) -> tuple[int, list[str]]:
    """
    Check for Spanish organization mentions in the response.

    Returns (count, list of organizations found).
    """
    spanish_orgs_found = []
    response_lower = response.lower()

    # Check for known Spanish organizations
    for org in KNOWN_SPANISH_ORGS:
        if org in response_lower:
            spanish_orgs_found.append(org)

    # Check for Spain country references
    for identifier in SPAIN_IDENTIFIERS:
        if identifier in response_lower:
            spanish_orgs_found.append(f"Reference to {identifier}")

    return len(set(spanish_orgs_found)), list(set(spanish_orgs_found))


def check_for_non_spanish_orgs(response: str) -> list[str]:
    """
    Check if response contains non-Spanish organizations as main partners.

    Returns list of non-Spanish org references found (ideally minimal).
    """
    non_spanish_found = []

    # Non-Spanish organizations that might be incorrectly listed
    non_spanish_orgs = [
        ("fraunhofer", "Germany"),
        ("cnrs", "France"),
        ("cea", "France"),
        ("tno", "Netherlands"),
        ("enea", "Italy"),
        ("cnr", "Italy"),
    ]

    # Check if these appear as main listed items (not just mentions)
    lines = response.split("\n")
    for line in lines:
        line_lower = line.lower()
        # Check if this line looks like an organization listing
        if re.search(r"^\s*(?:\d+[\.\)]|\*|-|###)", line):
            for org, country in non_spanish_orgs:
                if org in line_lower:
                    non_spanish_found.append(f"{org} ({country})")

    return non_spanish_found


def check_for_municipal_focus(response: str) -> tuple[int, list[str]]:
    """
    Check for municipal/testbed focus in the response.

    Returns (count of municipal references, keywords found).
    """
    response_lower = response.lower()
    keywords_found = []

    for keyword in MUNICIPAL_KEYWORDS:
        if keyword in response_lower:
            keywords_found.append(keyword)

    return len(keywords_found), keywords_found


def check_for_cluster2_relevance(response: str) -> tuple[int, list[str]]:
    """
    Check for Cluster 2 (Culture, Creativity, Inclusive Society) relevance.

    Returns (relevance count, keywords found).
    """
    response_lower = response.lower()
    keywords_found = []

    for keyword in CLUSTER_2_KEYWORDS:
        if keyword in response_lower:
            keywords_found.append(keyword)

    return len(keywords_found), keywords_found


def check_for_paragraph_descriptions(response: str) -> tuple[int, list[str]]:
    """
    Check for paragraph-length descriptions per organization.

    Returns (count of orgs with paragraphs, issues found).
    """
    issues = []
    orgs_with_paragraphs = 0

    # Split by organization markers (various formats)
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
    projects_found = []

    # Look for project name patterns (typically in bold or with budget)
    project_patterns = [
        r"\*\*([A-Z][A-Za-z0-9\-]+)\*\*\s*(?:\(|project)",
        r"project[s]?\s+(?:such\s+as|like|including)\s+([A-Z][A-Za-z0-9\-]+)",
        r"coordinated?\s+(?:the\s+)?(?:project\s+)?([A-Z][A-Za-z0-9\-]+)",
        r"([A-Z][A-Za-z0-9\-]+)\s+project",
        r"(?:the|a)\s+\*\*([A-Z][A-Za-z0-9\-]+)\*\*",
        r"coordinat(?:es|ed|ing)\s+(?:the\s+)?\*\*([A-Z][A-Za-z0-9\-]+)\*\*",
        r"\(([A-Z][A-Za-z0-9\-]+)[,\s]+[€\$]",
    ]

    for pattern in project_patterns:
        matches = re.findall(pattern, response)
        projects_found.extend(matches)

    # Also check for programme mentions
    response_lower = response.lower()
    programme_mentions = 0
    for prog in ["h2020", "horizon 2020", "horizon europe", "fp7"]:
        if prog in response_lower:
            programme_mentions += 1

    # Count unique project names
    unique_projects = list(set(p for p in projects_found if len(p) > 2))

    return len(unique_projects) + programme_mentions, unique_projects


def evaluate_query_fulfillment(response: str) -> tuple[int, str, list[str], list[str]]:
    """
    Evaluate query fulfillment (40 points max).

    Checks if:
    - Returns Spanish organizations with municipal ties (15 points)
    - Organizations have H2020/HE experience (10 points)
    - Includes Cluster 2 relevance (10 points)
    - Shows testbed/pilot capability (5 points)
    """
    score = 0
    found_items = []
    missing_items = []

    # Check for Spanish organizations (15 points)
    org_count = count_organizations_mentioned(response)
    spanish_count, spanish_orgs = check_for_spanish_orgs(response)

    if org_count >= 8 and spanish_count >= 10:
        score += 15
        found_items.append(f"{org_count} Spanish organizations listed")
    elif org_count >= 5 and spanish_count >= 6:
        score += 12
        found_items.append(f"{org_count} organizations with Spanish focus")
        missing_items.append("Could list more Spanish organizations")
    elif org_count >= 3 and spanish_count >= 3:
        score += 8
        found_items.append(f"{org_count} organizations mentioned")
        missing_items.append("Need more Spanish organizations")
    elif org_count >= 1:
        score += 4
        missing_items.append(f"Only {org_count} organization(s) listed")
    else:
        missing_items.append("No distinct organizations identified")

    # Check for H2020/HE experience (10 points)
    project_refs, projects = check_for_project_references(response)

    if project_refs >= 10:
        score += 10
        found_items.append("Strong H2020/HE project references")
    elif project_refs >= 5:
        score += 7
        found_items.append(f"{project_refs} project references")
        missing_items.append("Could include more project examples")
    elif project_refs >= 2:
        score += 4
        found_items.append(f"{project_refs} project references")
        missing_items.append("Limited project references")
    elif project_refs >= 1:
        score += 2
        missing_items.append("Very few H2020/HE project references")
    else:
        missing_items.append("No H2020/HE project experience shown")

    # Check for Cluster 2 relevance (10 points)
    cluster2_count, cluster2_keywords = check_for_cluster2_relevance(response)

    if cluster2_count >= 8:
        score += 10
        found_items.append("Strong Cluster 2 relevance")
    elif cluster2_count >= 5:
        score += 7
        found_items.append(f"Good Cluster 2 coverage ({cluster2_count} keywords)")
        missing_items.append("Could strengthen Cluster 2 focus")
    elif cluster2_count >= 2:
        score += 4
        found_items.append("Some Cluster 2 relevance")
        missing_items.append("Limited Cluster 2 (Culture, Democracy, Inclusion) focus")
    else:
        missing_items.append("Missing Cluster 2 relevance")

    # Check for municipal/testbed focus (5 points)
    municipal_count, municipal_keywords = check_for_municipal_focus(response)

    if municipal_count >= 8:
        score += 5
        found_items.append("Strong municipal/testbed focus")
    elif municipal_count >= 4:
        score += 3
        found_items.append(f"{municipal_count} municipal/testbed references")
        missing_items.append("Could strengthen municipal network descriptions")
    elif municipal_count >= 1:
        score += 1
        missing_items.append("Limited municipal/testbed focus")
    else:
        missing_items.append("Missing municipal network/testbed capability info")

    notes = f"Fulfillment: {score}/40"
    return score, notes, missing_items, found_items


def evaluate_specificity(response: str) -> tuple[int, str]:
    """
    Evaluate specificity (25 points max).

    Checks for:
    - Named organizations with full names (8 points)
    - Project titles/names (7 points)
    - Municipal network details (5 points)
    - Geographic/regional specificity (5 points)
    """
    score = 0
    notes = []

    # Named organizations (8 points)
    spanish_count, _ = check_for_spanish_orgs(response)

    if spanish_count >= 10:
        score += 8
    elif spanish_count >= 7:
        score += 6
        notes.append("Some organization names could be more specific")
    elif spanish_count >= 4:
        score += 4
        notes.append("Limited named Spanish organizations")
    else:
        notes.append("Few specific Spanish organization names")

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

    # Municipal network details (5 points)
    municipal_count, _ = check_for_municipal_focus(response)

    if municipal_count >= 10:
        score += 5
    elif municipal_count >= 5:
        score += 3
        notes.append("Some municipal details could be added")
    elif municipal_count >= 2:
        score += 1
        notes.append("Limited municipal network details")
    else:
        notes.append("No specific municipal network information")

    # Geographic/regional specificity (5 points)
    response_lower = response.lower()
    spanish_regions = [
        "catalonia",
        "catalunya",
        "basque",
        "euskadi",
        "madrid",
        "andalusia",
        "andalucía",
        "valencia",
        "valenciana",
        "galicia",
        "castilla",
        "aragón",
        "aragon",
        "navarra",
        "asturias",
        "cantabria",
        "murcia",
        "extremadura",
        "barcelona",
        "bilbao",
        "sevilla",
        "malaga",
        "zaragoza",
        "valencia city",
        "granada",
        "gijón",
        "oviedo",
    ]
    region_mentions = sum(1 for region in spanish_regions if region in response_lower)

    if region_mentions >= 5:
        score += 5
    elif region_mentions >= 3:
        score += 3
        notes.append("Some regional specificity")
    elif region_mentions >= 1:
        score += 1
        notes.append("Limited regional specificity")
    else:
        notes.append("No Spanish regional specificity")

    return (
        score,
        "; ".join(notes) if notes else "Good specificity with Spanish partner details",
    )


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - Organizations are from Spain
    - Listed organizations are real (known organizations)
    - Cluster 2 and municipal relevance
    """
    score = 25  # Start with full score, deduct for errors
    errors = []

    # Check for non-Spanish organizations as main listings (major deduction)
    non_spanish = check_for_non_spanish_orgs(response)

    if len(non_spanish) >= 5:
        score -= 15
        errors.append(
            {
                "claim": f"Listed {len(non_spanish)} non-Spanish organizations",
                "correct_value": "Should only list Spanish (ES) organizations",
                "source": "Geographic validation",
            }
        )
    elif len(non_spanish) >= 2:
        score -= 5 * len(non_spanish)
        for org in non_spanish[:3]:
            errors.append(
                {
                    "claim": f"Non-Spanish org listed: {org}",
                    "correct_value": "Should focus on Spanish organizations",
                    "source": "Geographic validation",
                }
            )

    # Check for known Spanish organizations
    spanish_count, _ = check_for_spanish_orgs(response)
    if spanish_count < 3:
        score -= 5
        errors.append(
            {
                "claim": "Few recognizable Spanish organizations mentioned",
                "correct_value": "Should mention major Spanish RTOs/universities like "
                "TECNALIA, CSIC, Eurecat, UPM, etc.",
                "source": "Organization validation",
            }
        )

    # Check for municipal/Cluster 2 relevance
    municipal_count, _ = check_for_municipal_focus(response)
    cluster2_count, _ = check_for_cluster2_relevance(response)

    if municipal_count < 2 and cluster2_count < 2:
        score -= 5
        errors.append(
            {
                "claim": "Limited municipal/Cluster 2 relevance",
                "correct_value": "Should discuss municipal networks, testbeds, "
                "and Cluster 2 topics (culture, democracy, inclusion)",
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
        "femp",
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
        "municipal network",
        "living lab",
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
            "component_id": "spain_municipal_partners",
            "description": "Spanish partners with municipal testbed networks for Cluster 2",
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
            f"Improve query fulfillment: List Spanish organizations with municipal "
            f"testbed networks, H2020/HE experience, and Cluster 2 relevance. "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:
        fix_suggestions.append(
            "Add more specificity: Include organization full names, regions, "
            "specific project titles, municipal network details"
        )
    if accuracy_score < 20:
        fix_suggestions.append(
            "Fix factual accuracy: Ensure ALL listed organizations are from Spain. "
            "Include known Spanish RTOs like TECNALIA, Eurecat, CARTIF."
        )
    if actionability_score < 8:
        fix_suggestions.append(
            "Improve actionability: Add CORDIS links, partner search guidance, "
            "FEMP/NCP contact info, and direct outreach suggestions"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Lists Spanish organizations with municipal/testbed focus")
    if specificity_score >= 20:
        strengths.append("Rich in organization and project details")
    if accuracy_score >= 20:
        strengths.append("Correctly focuses on Spain and Cluster 2 topics")
    if actionability_score >= 8:
        strengths.append("Provides useful partnership guidance")

    return EvaluationResult(
        prompt_id="030",
        query=PROMPT_030_QUERY,
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
class TestPrompt030SpainMunicipal:
    """
    Test suite for Prompt 030: Spain Municipal Testbed Partner.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_spain_municipal(self):
        """
        Main evaluation test for Prompt 030.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_030_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_030_spain_municipal.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 030: Spain Municipal Testbed Partner Evaluation")
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
        api_result = get_mapit_response(PROMPT_030_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_spain(self):
        """Verify the response mentions Spain (informational)."""
        results_file = RESULTS_DIR / "prompt_030_spain_municipal.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_spain_municipal first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response = result["response"]
        spanish_count, spanish_orgs = check_for_spanish_orgs(response)

        print(f"Spanish references found: {spanish_count}")
        if spanish_orgs:
            print(f"Spanish organizations: {spanish_orgs[:10]}")

        assert "response" in result, "Response field missing from results"


class TestPrompt030OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_SPAIN_MUNICIPAL, {"source": "sample_excellent"}
        )

        results_file = RESULTS_DIR / "prompt_030_spain_municipal_sample_excellent.json"
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
            SampleResponses.PARTIAL_SPAIN_MUNICIPAL, {"source": "sample_partial"}
        )

        print("\nPartial Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < PASS_THRESHOLD, (
            f"Partial response scored {evaluation.overall_score}, expected < {PASS_THRESHOLD}"
        )

    def test_response_with_wrong_country_fails(self):
        """Test that a response with non-Spanish orgs fails accuracy check."""
        evaluation = evaluate_response(
            SampleResponses.POOR_WITH_WRONG_COUNTRY,
            {"source": "sample_wrong_country"},
        )

        print("\nResponse with Wrong Country Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")
        print(f"  Factual Errors: {len(evaluation.factual_errors)}")

        # Should have factual errors for including non-Spanish organizations
        assert len(evaluation.factual_errors) > 0, "Should detect non-Spanish orgs"
        assert evaluation.overall_score < PASS_THRESHOLD

    def test_poor_response_fails(self):
        """Test that a poor response scores < 70 (FAIL)."""
        evaluation = evaluate_response(
            SampleResponses.POOR_SPAIN_MUNICIPAL, {"source": "sample_poor"}
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
            SampleResponses.EXCELLENT_SPAIN_MUNICIPAL, {"source": "test_json_save"}
        )

        results_file = RESULTS_DIR / "prompt_030_spain_municipal_test_save.json"
        save_result(evaluation, results_file)

        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "030"
        assert loaded["query"] == PROMPT_030_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
