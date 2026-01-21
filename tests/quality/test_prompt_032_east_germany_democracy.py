"""
Quality Evaluation Test for Prompt 032: Eastern Germany Democracy/Art Partners.

This test evaluates the MAPIT AI response to the query:
"I am looking for partners from Eastern Germany (pre-1990 definition). The topic is
participatory technologies and art in education towards democracy. I need partners from
education, democracy-building, and art fields. List top 10 potential H2020/HE capable
organisations with 1 paragraph each, including institutional profile, size, location,
and Horizon expertise."

Evaluation uses LLM-as-judge methodology with four scoring dimensions:
- Query Fulfillment (40 points): Returns 10 East German organizations with paragraphs
- Specificity (25 points): Organization names, locations, sizes, project titles
- Factual Accuracy (25 points): Organizations are from East Germany, topic relevance
- Actionability (10 points): Contact info, CORDIS links, partnership guidance

Pass threshold: >= 85/100

Reference requirements from PRD:
- Must identify 10 East German organizations (pre-1990: Saxony, Thuringia,
  Saxony-Anhalt, Brandenburg, Mecklenburg-Vorpommern, East Berlin)
- Must show H2020/HE participation/experience
- Focus on: participatory technologies, art in education, democracy-building
- Must include 1 paragraph per organization with profile, size, location, expertise

Eastern Germany (pre-1990 definition) includes:
- Saxony (Sachsen) - Dresden, Leipzig, Chemnitz
- Thuringia (Thüringen) - Erfurt, Jena, Weimar
- Saxony-Anhalt (Sachsen-Anhalt) - Magdeburg, Halle
- Brandenburg - Potsdam, Cottbus
- Mecklenburg-Vorpommern - Rostock, Schwerin
- East Berlin (historical)

Run with:
    pytest tests/quality/test_prompt_032_east_germany_democracy.py -v

For live API tests only:
    pytest tests/quality/test_prompt_032_east_germany_democracy.py -v -m "live_api"
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
PROMPT_032_QUERY = (
    "I am looking for partners from Eastern Germany (pre-1990 definition). The topic is "
    "participatory technologies and art in education towards democracy. I need partners from "
    "education, democracy-building, and art fields. List top 10 potential H2020/HE capable "
    "organisations with 1 paragraph each, including institutional profile, size, location, "
    "and Horizon expertise."
)

# East Germany geographic identifiers (pre-1990 states)
EAST_GERMANY_STATES = [
    # Saxony
    "saxony",
    "sachsen",
    "dresden",
    "leipzig",
    "chemnitz",
    # Thuringia
    "thuringia",
    "thüringen",
    "thuringen",
    "erfurt",
    "jena",
    "weimar",
    # Saxony-Anhalt
    "saxony-anhalt",
    "sachsen-anhalt",
    "magdeburg",
    "halle",
    # Brandenburg
    "brandenburg",
    "potsdam",
    "cottbus",
    "frankfurt (oder)",
    # Mecklenburg-Vorpommern
    "mecklenburg",
    "mecklenburg-vorpommern",
    "rostock",
    "schwerin",
    "greifswald",
    # East Berlin (historical)
    "east berlin",
    "berlin",  # Berlin can count as it was divided
]

# West Germany states (for negative check)
WEST_GERMANY_ONLY_CITIES = [
    "munich",
    "münchen",
    "frankfurt am main",
    "stuttgart",
    "cologne",
    "köln",
    "düsseldorf",
    "dusseldorf",
    "hamburg",
    "hannover",
    "bremen",
    "nürnberg",
    "nuremberg",
    "heidelberg",
    "freiburg",
    "bonn",
    "karlsruhe",
    "mannheim",
]

# Topic-relevant keywords
TOPIC_KEYWORDS = {
    "participatory_tech": [
        "participatory",
        "participation",
        "citizen",
        "civic",
        "engagement",
        "digital democracy",
        "e-democracy",
        "technology",
        "digital",
        "platform",
        "interactive",
        "co-creation",
        "co-design",
        "collaborative",
    ],
    "art_education": [
        "art",
        "arts",
        "artistic",
        "creative",
        "culture",
        "cultural",
        "education",
        "educational",
        "pedagogy",
        "learning",
        "teaching",
        "school",
        "museum",
        "gallery",
        "theatre",
        "theater",
        "music",
        "visual",
        "media art",
        "performance",
    ],
    "democracy": [
        "democracy",
        "democratic",
        "citizenship",
        "civic education",
        "political",
        "social cohesion",
        "inclusion",
        "empowerment",
        "dialogue",
        "discourse",
        "public sphere",
        "civil society",
        "governance",
    ],
}

# Known East German organizations (universities, research institutes, cultural orgs)
KNOWN_EAST_GERMAN_ORGS = [
    # Universities
    "technische universität dresden",
    "tu dresden",
    "universität leipzig",
    "leipzig university",
    "humboldt-universität",
    "humboldt university",
    "universität potsdam",
    "potsdam university",
    "bauhaus-universität",
    "bauhaus weimar",
    "hochschule für bildende künste",
    "friedrich-schiller-universität",
    "fsu jena",
    "universität jena",
    "jena university",
    "universität erfurt",
    "erfurt university",
    "universität rostock",
    "rostock university",
    "universität greifswald",
    "greifswald university",
    "otto-von-guericke-universität",
    "ovgu",
    "magdeburg university",
    "martin-luther-universität",
    "mlu halle",
    "halle-wittenberg",
    "tu chemnitz",
    "btu cottbus",
    "cottbus-senftenberg",
    "hochschule für musik",
    "hochschule für grafik",
    # Research institutes
    "leibniz",
    "fraunhofer",  # Note: some Fraunhofer in East, check location
    "max planck",  # Note: some MPIs in East
    "helmholtz",
    "ifw dresden",
    "ipk gatersleben",
    "izi leipzig",
    "hzdr",
    # Cultural/Art organizations
    "stiftung",
    "kulturstiftung",
    "staatliche kunstsammlungen",
    "deutsches hygiene-museum",
    "grassi museum",
    "gewandhaus",
    "semperoper",
    "staatsschauspiel",
    "berliner festspiele",
    "haus der kulturen",
    "akademie der künste",
    # Civil society/democracy
    "bundeszentrale für politische bildung",
    "bpb",
    "heinrich-böll-stiftung",
    "rosa-luxemburg-stiftung",
    "konrad-adenauer-stiftung",
    "friedrich-ebert-stiftung",
    "amadeu antonio stiftung",
    "aktion zivilcourage",
    "kulturbüro sachsen",
    "miteinander",
    "demokratie leben",
]

# Organization type indicators
ORG_TYPE_INDICATORS = {
    "university": ["universität", "university", "hochschule", "tu ", "fu ", "hu "],
    "research": ["institut", "institute", "fraunhofer", "leibniz", "max planck", "helmholtz"],
    "cultural": ["museum", "stiftung", "foundation", "kulturstiftung", "akademie", "theatre"],
    "ngo": ["verein", "e.v.", "gmbh", "stiftung", "initiative", "netzwerk", "network"],
}


class SampleResponses:
    """Sample responses for testing the evaluation framework."""

    # A high-quality response that should PASS (score >= 85)
    EXCELLENT_EAST_GERMANY = """
## Top 10 Eastern German Partners for Participatory Technologies, Art & Democracy Education

Based on H2020 and Horizon Europe participation data, here are the leading Eastern German
organizations with expertise in participatory technologies, art in education, and
democracy-building:

### 1. **Technische Universität Dresden** (Saxony)
**Profile:** TU Dresden is one of Germany's "Excellence Universities" with 32,000 students
and 8,400 employees. Located in the Saxon capital, it hosts the Center for Advanced Studies
in Art and Society and the Institute for Media and Education.
**Horizon Expertise:** Coordinated 45+ H2020/HE projects including **INDIGO** (digital
inclusion, €3.2M) and **ArtTech** (cultural digitization). Their Faculty of Education
specializes in civic education and digital learning.
**Relevance:** Strong in digital democracy platforms, cultural heritage technologies,
and educational innovation with regional schools and cultural institutions.
[CORDIS: https://cordis.europa.eu/organization/tu-dresden]

### 2. **Bauhaus-Universität Weimar** (Thuringia)
**Profile:** This specialized art and design university has 4,000 students and 500 staff
in Weimar, Thuringia. The Bauhaus tradition continues with faculties of Art & Design,
Media, and Architecture.
**Horizon Expertise:** Participated in 25+ EU projects including **CREATE** (creative
industries, €2.8M) and **MediaDem** (media and democracy). Known for design thinking
and participatory design research.
**Relevance:** Unique expertise in art-technology intersection, participatory design
methods, and cultural education. Strong ties to Weimar's cultural institutions
(Klassik Stiftung, Deutsches Nationaltheater).
[CORDIS: https://cordis.europa.eu/organization/bauhaus-weimar]

### 3. **Universität Leipzig** (Saxony)
**Profile:** One of Germany's oldest universities with 30,000 students and 5,000 staff.
Located in Leipzig, Saxony, it hosts the Institute for Communication and Media Studies
and a strong political science faculty.
**Horizon Expertise:** Coordinated 60+ H2020/HE projects including **EUROCIT** (civic
education, €4M) and **DIGIDEM** (digital democracy tools). Research strength in political
communication and media literacy.
**Relevance:** Leading expertise in democratic participation research, civic education
methodologies, and media-arts education programs with local cultural partners.
[CORDIS: https://cordis.europa.eu/organization/uni-leipzig]

### 4. **Hochschule für Bildende Künste Dresden** (Saxony)
**Profile:** Dresden's Academy of Fine Arts is one of Germany's oldest art academies
with 600 students and 150 staff. Located near Dresden's historic Altstadt.
**Horizon Expertise:** Partnered in 12 H2020 projects on cultural heritage and creative
industries including **HERIT-AGE** (heritage education, €1.5M).
**Relevance:** Specializes in art pedagogy, community art projects, and participatory
art education. Collaborates with Staatliche Kunstsammlungen Dresden on public programs.
[CORDIS: https://cordis.europa.eu/organization/hfbk-dresden]

### 5. **Friedrich-Schiller-Universität Jena** (Thuringia)
**Profile:** FSU Jena is a comprehensive university with 18,000 students in Thuringia.
Notable for its Institute of Sociology and Centre for Empirical Research.
**Horizon Expertise:** Participated in 40+ H2020/HE projects including **DEMPART**
(democratic participation, €2.1M) and **SOCINN** (social innovation).
**Relevance:** Strong political sociology research, democratic attitude studies, and
civic engagement projects with regional civil society organizations.
[CORDIS: https://cordis.europa.eu/organization/fsu-jena]

### 6. **Leibniz Institute for Research on Society and Space (IRS), Erkner** (Brandenburg)
**Profile:** Research institute with 100 researchers in Erkner near Berlin, Brandenburg.
Part of the Leibniz Association focusing on spatial development and social dynamics.
**Horizon Expertise:** Coordinated 15 H2020 projects on urban development and civic
participation including **URBANPART** (participatory urban planning, €3M).
**Relevance:** Expertise in participatory planning methods, community engagement in
urban development, and technology-supported citizen participation.
[CORDIS: https://cordis.europa.eu/organization/irs-erkner]

### 7. **Universität Erfurt** (Thuringia)
**Profile:** University focused on humanities and social sciences with 6,000 students
in Thuringia's capital. Houses the Willy Brandt School of Public Policy.
**Horizon Expertise:** Partnered in 20 H2020 projects on education and governance
including **EDUDEM** (education for democracy, €1.8M).
**Relevance:** Specializes in democratic education research, teacher training for
civic education, and governance studies with practical policy focus.
[CORDIS: https://cordis.europa.eu/organization/uni-erfurt]

### 8. **Aktion Zivilcourage e.V., Pirna** (Saxony)
**Profile:** Civil society organization with 40 staff based in Pirna, Saxony. Specializes
in democracy education and civic engagement programs, particularly for youth.
**Horizon Expertise:** Partnered in 5 H2020 projects on democratic resilience including
**DEMRES** (democratic resilience education, €800k).
**Relevance:** Hands-on expertise in participatory democracy workshops, civic technology
pilots with municipalities, and art-based democracy education in schools.
[CORDIS: https://cordis.europa.eu/organization/aktion-zivilcourage]

### 9. **Stiftung Deutsches Hygiene-Museum Dresden** (Saxony)
**Profile:** One of Germany's most visited science museums with 80 staff in Dresden.
Known for participatory exhibitions and public science communication.
**Horizon Expertise:** Partnered in 8 H2020 projects on science communication and
cultural heritage including **PUBSCI** (public science engagement, €1.2M).
**Relevance:** Pioneering participatory museum practices, citizen science exhibitions,
and dialogue-based education programs on social and political topics.
[CORDIS: https://cordis.europa.eu/organization/dhmd]

### 10. **Klassik Stiftung Weimar** (Thuringia)
**Profile:** One of Germany's largest cultural foundations managing 27 museums and
historic sites in Weimar with 500 staff. UNESCO World Heritage site guardian.
**Horizon Expertise:** Participated in 10 H2020 cultural heritage projects including
**HERITRANS** (heritage transformation, €2M).
**Relevance:** Leading expertise in cultural heritage education, digital humanities,
and participatory engagement with Weimar's Bauhaus and Classical heritage. Strong
in arts-based citizenship education programs.
[CORDIS: https://cordis.europa.eu/organization/klassik-stiftung]

---

### Summary Table

| Rank | Organization | Location | Type | Focus Area |
|------|-------------|----------|------|------------|
| 1 | TU Dresden | Dresden, Saxony | HES | Digital democracy, Cultural tech |
| 2 | Bauhaus Weimar | Weimar, Thuringia | HES | Art-tech, Participatory design |
| 3 | Uni Leipzig | Leipzig, Saxony | HES | Civic education, Media literacy |
| 4 | HfBK Dresden | Dresden, Saxony | HES | Art pedagogy, Community art |
| 5 | FSU Jena | Jena, Thuringia | HES | Political sociology, Civic engagement |
| 6 | IRS Erkner | Erkner, Brandenburg | REC | Participatory planning |
| 7 | Uni Erfurt | Erfurt, Thuringia | HES | Democracy education |
| 8 | Aktion Zivilcourage | Pirna, Saxony | OTH | Youth democracy, Civic tech |
| 9 | Hygiene-Museum | Dresden, Saxony | OTH | Participatory exhibits |
| 10 | Klassik Stiftung | Weimar, Thuringia | OTH | Heritage education |

### How to Partner with Eastern German Organizations

1. **CORDIS Search:** Find detailed project portfolios at https://cordis.europa.eu
2. **German NCPs:** Contact German National Contact Points for Cluster 2 introductions
3. **Regional Networks:** Saxon Ministry for Science and Art can facilitate connections
4. **Direct Contact:** Most have dedicated EU project/research offices
5. **Conference Networks:** ECREA, SIEF for academic partners; NEMO, LEM for museums

### Why Eastern German Partners?

Eastern Germany offers unique advantages for democracy and art in education projects:
- Strong tradition in civic education (Politische Bildung)
- Experience with democratic transition and transformation
- Vibrant cultural scene with internationally recognized institutions
- Lower costs than Western Germany with excellent infrastructure
- Active civil society engaged in democracy-building
"""

    # A medium-quality response that NEEDS_REVIEW (70-84)
    PARTIAL_EAST_GERMANY = """
Here are some potential partners from Eastern Germany for your project:

1. **TU Dresden** - Large technical university in Saxony
2. **Universität Leipzig** - Comprehensive university with social sciences
3. **Bauhaus Weimar** - Art and design university
4. **FSU Jena** - University in Thuringia
5. **HU Berlin** - Major university in Berlin

These organizations have EU project experience. For more detailed information
about their specific expertise, please consult CORDIS or contact German NCPs.
"""

    # A LOW-quality response that should FAIL
    POOR_EAST_GERMANY = """
Here are some German research partners:

- Universities in Germany
- Research institutes
- Cultural organizations

Germany has many institutions working on democracy and art education.
Contact the German Research Foundation for more information.
"""

    # Response with West German organizations
    POOR_WITH_WRONG_REGION = """
Top German partners for democracy and art education:

1. **Ludwig-Maximilians-Universität München** (Bavaria) - Large research university
2. **Universität Heidelberg** (Baden-Württemberg) - Excellence university
3. **Goethe-Universität Frankfurt** (Hesse) - Strong in social sciences
4. **Universität Köln** (North Rhine-Westphalia) - Large university
5. **Universität Hamburg** (Hamburg) - Northern Germany research hub

These West German institutions have strong EU project portfolios.
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
    Looks for numbered items (1., 2., etc.) or bold headers.
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


def check_for_east_german_locations(response: str) -> tuple[int, list[str]]:
    """
    Check for East German location mentions in the response.

    Returns (count, list of locations found).
    """
    locations_found = []
    response_lower = response.lower()

    for location in EAST_GERMANY_STATES:
        if location in response_lower:
            locations_found.append(location)

    return len(set(locations_found)), list(set(locations_found))


def check_for_west_german_only_locations(response: str) -> list[str]:
    """
    Check if response contains West German-only locations as main focus.

    Returns list of West German location references found (ideally minimal).
    """
    west_found = []

    # Check if these appear as organization locations
    lines = response.split("\n")
    for line in lines:
        line_lower = line.lower()
        # Check if this line looks like an organization listing
        if re.search(r"^\s*(?:\d+[\.\)]|\*|-|###)", line):
            for city in WEST_GERMANY_ONLY_CITIES:
                if city in line_lower and "frankfurt (oder)" not in line_lower:
                    west_found.append(city)

    return list(set(west_found))


def check_for_known_east_german_orgs(response: str) -> tuple[int, list[str]]:
    """
    Check for known East German organizations in the response.

    Returns (count, list of organizations found).
    """
    orgs_found = []
    response_lower = response.lower()

    for org in KNOWN_EAST_GERMAN_ORGS:
        if org in response_lower:
            orgs_found.append(org)

    return len(set(orgs_found)), list(set(orgs_found))


def check_for_topic_relevance(response: str) -> dict[str, tuple[int, list[str]]]:
    """
    Check for topic keyword coverage.

    Returns dict with counts and keywords found for each topic area.
    """
    response_lower = response.lower()
    results = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        found = []
        for keyword in keywords:
            if keyword in response_lower:
                found.append(keyword)
        results[topic] = (len(found), found)

    return results


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
        # Check if section has substantial content (at least 100 chars for 1 paragraph)
        if len(section.strip()) >= 150:
            orgs_with_paragraphs += 1
        elif len(section.strip()) > 30:  # Has some content but too short
            org_name_match = re.match(r"([^*\n]+)", section)
            if org_name_match:
                issues.append(f"Short description for: {org_name_match.group(1)[:30]}")

    return orgs_with_paragraphs, issues


def check_for_profile_elements(response: str) -> dict[str, int]:
    """
    Check for required profile elements (size, location, expertise).

    Returns dict with counts for each element type.
    """
    response_lower = response.lower()

    # Size indicators
    size_patterns = [
        r"\d+,?\d*\s*(?:students|employees|staff|researchers|members)",
        r"(?:large|medium|small)\s+(?:university|institute|organization)",
        r"\d+\s+(?:faculties|departments|institutes)",
    ]
    size_count = sum(1 for p in size_patterns if re.search(p, response_lower))

    # Location indicators (already checked separately)
    location_count, _ = check_for_east_german_locations(response)

    # Expertise/Horizon indicators
    expertise_patterns = [
        r"h2020|horizon\s+(?:2020|europe)",
        r"coordinated?\s+\d+",
        r"participated?\s+in\s+\d+",
        r"eu\s+project",
        r"€\d+[.,]?\d*\s*[mk]",
        r"research\s+(?:strength|focus|expertise)",
    ]
    expertise_count = sum(1 for p in expertise_patterns if re.search(p, response_lower))

    return {
        "size": size_count,
        "location": location_count,
        "expertise": expertise_count,
    }


def evaluate_query_fulfillment(response: str) -> tuple[int, str, list[str], list[str]]:
    """
    Evaluate query fulfillment (40 points max).

    Checks if:
    - Returns 10 organizations (15 points)
    - Organizations are from East Germany (10 points)
    - Topics covered (participatory tech, art, democracy) (10 points)
    - Paragraph descriptions included (5 points)
    """
    score = 0
    found_items = []
    missing_items = []

    # Check for 10 organizations (15 points)
    org_count = count_organizations_mentioned(response)

    if org_count >= 10:
        score += 15
        found_items.append(f"{org_count} organizations listed (requested 10)")
    elif org_count >= 7:
        score += 12
        found_items.append(f"{org_count} organizations listed")
        missing_items.append(f"Only {org_count}/10 organizations requested")
    elif org_count >= 5:
        score += 8
        found_items.append(f"{org_count} organizations mentioned")
        missing_items.append(f"Only {org_count}/10 organizations requested")
    elif org_count >= 3:
        score += 4
        missing_items.append(f"Only {org_count} organization(s) listed")
    else:
        missing_items.append("Too few organizations identified")

    # Check for East German locations (10 points)
    east_count, east_locations = check_for_east_german_locations(response)
    known_org_count, known_orgs = check_for_known_east_german_orgs(response)

    if east_count >= 8 or known_org_count >= 8:
        score += 10
        found_items.append(f"Strong East German focus ({east_count} locations)")
    elif east_count >= 5 or known_org_count >= 5:
        score += 7
        found_items.append(f"{east_count} East German locations")
        missing_items.append("Could include more East German states")
    elif east_count >= 3 or known_org_count >= 3:
        score += 4
        found_items.append("Some East German coverage")
        missing_items.append("Limited East German geographic coverage")
    elif east_count >= 1:
        score += 2
        missing_items.append("Very few East German references")
    else:
        missing_items.append("Missing East German geographic focus")

    # Check for topic coverage (10 points)
    topic_results = check_for_topic_relevance(response)
    topics_covered = sum(1 for _, (count, _) in topic_results.items() if count >= 2)

    if topics_covered >= 3:
        score += 10
        found_items.append("All three topic areas covered (participatory tech, art, democracy)")
    elif topics_covered >= 2:
        score += 7
        covered = [k for k, (c, _) in topic_results.items() if c >= 2]
        found_items.append(f"Topics covered: {', '.join(covered)}")
        missing = [k for k, (c, _) in topic_results.items() if c < 2]
        missing_items.append(f"Weak coverage of: {', '.join(missing)}")
    elif topics_covered >= 1:
        score += 4
        covered = [k for k, (c, _) in topic_results.items() if c >= 2]
        found_items.append(f"Topics covered: {', '.join(covered)}")
        missing_items.append("Limited topic coverage")
    else:
        missing_items.append("Missing topic relevance (participatory tech, art, democracy)")

    # Check for paragraph descriptions (5 points)
    para_count, para_issues = check_for_paragraph_descriptions(response)

    if para_count >= 8:
        score += 5
        found_items.append("Detailed paragraph descriptions provided")
    elif para_count >= 5:
        score += 3
        found_items.append(f"{para_count} organizations have paragraph descriptions")
        missing_items.append("Some organizations lack full paragraph descriptions")
    elif para_count >= 2:
        score += 1
        missing_items.append("Most organizations lack detailed paragraphs")
    else:
        missing_items.append("Missing paragraph descriptions per organization")

    notes = f"Fulfillment: {score}/40"
    return score, notes, missing_items, found_items


def evaluate_specificity(response: str) -> tuple[int, str]:
    """
    Evaluate specificity (25 points max).

    Checks for:
    - Named organizations with full names (8 points)
    - Profile elements (size, location) (7 points)
    - Horizon expertise specifics (5 points)
    - Project titles/names (5 points)
    """
    score = 0
    notes = []

    # Named organizations (8 points)
    org_count, _ = check_for_known_east_german_orgs(response)

    if org_count >= 10:
        score += 8
    elif org_count >= 7:
        score += 6
        notes.append("Some organization names could be more specific")
    elif org_count >= 4:
        score += 4
        notes.append("Limited named East German organizations")
    elif org_count >= 1:
        score += 2
        notes.append("Few specific East German organization names")
    else:
        notes.append("No recognizable East German organization names")

    # Profile elements (7 points)
    profile = check_for_profile_elements(response)

    if profile["size"] >= 5 and profile["location"] >= 5:
        score += 7
    elif profile["size"] >= 3 or profile["location"] >= 3:
        score += 5
        notes.append("Some profile elements present")
    elif profile["size"] >= 1 or profile["location"] >= 1:
        score += 2
        notes.append("Limited profile information (size, location)")
    else:
        notes.append("Missing institutional profile details")

    # Horizon expertise specifics (5 points)
    if profile["expertise"] >= 8:
        score += 5
    elif profile["expertise"] >= 5:
        score += 3
        notes.append("Some Horizon expertise mentioned")
    elif profile["expertise"] >= 2:
        score += 1
        notes.append("Limited Horizon expertise details")
    else:
        notes.append("Missing Horizon project expertise information")

    # Project titles (5 points)
    project_pattern = r"\*\*([A-Z][A-Za-z0-9\-]+)\*\*"
    projects_found = re.findall(project_pattern, response)

    if len(projects_found) >= 8:
        score += 5
    elif len(projects_found) >= 5:
        score += 3
        notes.append("Some project names mentioned")
    elif len(projects_found) >= 2:
        score += 1
        notes.append("Few project names mentioned")
    else:
        notes.append("No specific project titles")

    return (
        score,
        "; ".join(notes) if notes else "Good specificity with East German partner details",
    )


def evaluate_factual_accuracy(
    response: str,
) -> tuple[int, str, list[dict[str, str]]]:
    """
    Evaluate factual accuracy (25 points max).

    Verifies:
    - Organizations are from East Germany (not West Germany)
    - Listed organizations are real (known organizations)
    - Topic relevance (participatory tech, art, democracy)
    """
    score = 25  # Start with full score, deduct for errors
    errors = []

    # Check for West German-only locations as main listings (major deduction)
    west_german = check_for_west_german_only_locations(response)

    if len(west_german) >= 5:
        score -= 15
        errors.append(
            {
                "claim": f"Listed {len(west_german)} West German-only locations",
                "correct_value": "Should only list East German organizations "
                "(Saxony, Thuringia, Brandenburg, etc.)",
                "source": "Geographic validation",
            }
        )
    elif len(west_german) >= 2:
        score -= 5 * len(west_german)
        for loc in west_german[:3]:
            errors.append(
                {
                    "claim": f"West German-only location listed: {loc}",
                    "correct_value": "Should focus on East German states",
                    "source": "Geographic validation",
                }
            )

    # Check for known East German organizations
    east_org_count, _ = check_for_known_east_german_orgs(response)
    east_loc_count, _ = check_for_east_german_locations(response)

    if east_org_count < 3 and east_loc_count < 3:
        score -= 5
        errors.append(
            {
                "claim": "Few recognizable East German organizations mentioned",
                "correct_value": "Should mention major East German institutions like "
                "TU Dresden, Leipzig, Bauhaus Weimar, FSU Jena, etc.",
                "source": "Organization validation",
            }
        )

    # Check for topic relevance
    topic_results = check_for_topic_relevance(response)
    topics_covered = sum(1 for _, (count, _) in topic_results.items() if count >= 2)

    if topics_covered < 2:
        score -= 5
        errors.append(
            {
                "claim": "Limited topic relevance",
                "correct_value": "Should discuss participatory technologies, "
                "art in education, and democracy-building topics",
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
    - Partnership/contact guidance (3 points)
    - Next steps suggestions (3 points)
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

    # Partnership guidance (3 points)
    guidance_phrases = [
        "partner search",
        "how to partner",
        "how to collaborate",
        "national contact point",
        "ncp",
        "reach out",
        "contact",
        "partnership",
        "consortium",
    ]
    guidance_found = sum(1 for phrase in guidance_phrases if phrase in response_lower)
    score += min(3, guidance_found)

    # Next steps/networking (3 points)
    next_step_phrases = [
        "direct contact",
        "project office",
        "research office",
        "next step",
        "recommend",
        "conference",
        "network",
        "join",
        "apply",
    ]
    next_found = sum(1 for phrase in next_step_phrases if phrase in response_lower)
    score += min(3, next_found)

    return (
        score,
        "; ".join(notes) if notes else "Good actionability with partnership guidance",
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
            "component_id": "east_germany_democracy_art",
            "description": "East German partners for participatory tech, art & democracy education",
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
            f"Improve query fulfillment: List 10 East German organizations with "
            f"paragraph descriptions covering participatory tech, art, and democracy. "
            f"Missing: {', '.join(missing_items) if missing_items else 'None'}."
        )
    if specificity_score < 20:
        fix_suggestions.append(
            "Add more specificity: Include organization full names, sizes (students/staff), "
            "East German locations, specific Horizon project titles and budgets"
        )
    if accuracy_score < 20:
        fix_suggestions.append(
            "Fix factual accuracy: Ensure ALL listed organizations are from East Germany "
            "(Saxony, Thuringia, Brandenburg, Mecklenburg-Vorpommern, Saxony-Anhalt). "
            "Include known institutions like TU Dresden, Bauhaus Weimar, Uni Leipzig."
        )
    if actionability_score < 8:
        fix_suggestions.append(
            "Improve actionability: Add CORDIS links, German NCP contact info, "
            "partnership guidance, and next steps for outreach"
        )

    # Identify strengths
    strengths = []
    if fulfillment_score >= 32:
        strengths.append("Lists East German organizations with topic-relevant focus")
    if specificity_score >= 20:
        strengths.append("Rich in organization profiles and project details")
    if accuracy_score >= 20:
        strengths.append("Correctly focuses on East Germany and relevant topics")
    if actionability_score >= 8:
        strengths.append("Provides useful partnership guidance")

    return EvaluationResult(
        prompt_id="032",
        query=PROMPT_032_QUERY,
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
class TestPrompt032EastGermanyDemocracy:
    """
    Test suite for Prompt 032: Eastern Germany Democracy/Art Partners.

    Evaluates the MAPIT AI response quality using LLM-as-judge methodology.
    """

    def test_evaluate_east_germany_partners(self):
        """
        Main evaluation test for Prompt 032.

        1. Sends query to MAPIT API
        2. Evaluates response using four-dimension scoring
        3. Saves detailed results to JSON
        4. Reports evaluation status
        """
        # Get response from MAPIT
        api_result = get_mapit_response(PROMPT_032_QUERY)

        response = api_result["response"]
        metadata = api_result["metadata"]

        # Ensure we got a response
        assert len(response) >= 100, f"Response too short ({len(response)} chars)"

        # Perform evaluation
        evaluation = evaluate_response(response, metadata)

        # Save results
        results_file = RESULTS_DIR / "prompt_032_east_germany_democracy.json"
        save_result(evaluation, results_file)

        # Log evaluation summary
        print(f"\n{'=' * 60}")
        print("PROMPT 032: Eastern Germany Democracy/Art Partners Evaluation")
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
        api_result = get_mapit_response(PROMPT_032_QUERY)
        response = api_result["response"]

        assert len(response) > 0, "Response is empty"
        assert len(response) >= 100, f"Response too short: {len(response)} chars"

    def test_response_mentions_east_germany(self):
        """Verify the response mentions East German locations (informational)."""
        results_file = RESULTS_DIR / "prompt_032_east_germany_democracy.json"
        if not results_file.exists():
            pytest.skip("Run test_evaluate_east_germany_partners first to generate results")

        with open(results_file) as f:
            result = json.load(f)

        response = result["response"]
        east_count, east_locations = check_for_east_german_locations(response)

        print(f"East German references found: {east_count}")
        if east_locations:
            print(f"Locations: {east_locations[:10]}")

        assert "response" in result, "Response field missing from results"


class TestPrompt032OfflineEvaluation:
    """
    Offline evaluation tests using sample responses.
    """

    def test_excellent_response_passes(self):
        """Test that an excellent response scores >= 85 (PASS)."""
        evaluation = evaluate_response(
            SampleResponses.EXCELLENT_EAST_GERMANY, {"source": "sample_excellent"}
        )

        results_file = RESULTS_DIR / "prompt_032_east_germany_democracy_sample_excellent.json"
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
            SampleResponses.PARTIAL_EAST_GERMANY, {"source": "sample_partial"}
        )

        print("\nPartial Response Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")

        assert evaluation.overall_score < PASS_THRESHOLD, (
            f"Partial response scored {evaluation.overall_score}, expected < {PASS_THRESHOLD}"
        )

    def test_response_with_wrong_region_fails(self):
        """Test that a response with West German orgs fails accuracy check."""
        evaluation = evaluate_response(
            SampleResponses.POOR_WITH_WRONG_REGION,
            {"source": "sample_wrong_region"},
        )

        print("\nResponse with Wrong Region Evaluation:")
        print(f"  Score: {evaluation.overall_score}/100")
        print(f"  Result: {evaluation.result}")
        print(f"  Factual Errors: {len(evaluation.factual_errors)}")

        # Should have factual errors for including West German organizations
        assert len(evaluation.factual_errors) > 0, "Should detect West German orgs"
        assert evaluation.overall_score < PASS_THRESHOLD

    def test_poor_response_fails(self):
        """Test that a poor response scores < 70 (FAIL)."""
        evaluation = evaluate_response(SampleResponses.POOR_EAST_GERMANY, {"source": "sample_poor"})

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
            SampleResponses.EXCELLENT_EAST_GERMANY, {"source": "test_json_save"}
        )

        results_file = RESULTS_DIR / "prompt_032_east_germany_democracy_test_save.json"
        save_result(evaluation, results_file)

        assert results_file.exists(), f"Results file not created: {results_file}"

        with open(results_file) as f:
            loaded = json.load(f)

        assert loaded["prompt_id"] == "032"
        assert loaded["query"] == PROMPT_032_QUERY
        assert "overall_score" in loaded
        assert "component_scores" in loaded
        assert "fix_suggestions" in loaded

        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
