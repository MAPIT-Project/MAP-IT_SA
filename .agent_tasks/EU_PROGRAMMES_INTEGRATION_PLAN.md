# EU Funding Programmes Integration Plan

## Current State

The system currently supports **Horizon Europe** (including ERC, EIC, MSCA) which is the EU's flagship R&I programme with €95.5 billion budget. However, there are **many other EU programmes** that researchers, universities, and organizations can apply to.

## Programmes to Integrate

### Priority 1: High-Value Research & Innovation Programmes

| Programme | Budget (2021-2027) | Target Users | Call ID Pattern |
|-----------|-------------------|--------------|-----------------|
| **Erasmus+** | €26.2 billion | Universities, Education, Training, Youth | `ERASMUS-*` |
| **Digital Europe** | €7.59 billion | Tech companies, Digital skills, AI, Cybersecurity | `DIGITAL-*` |
| **LIFE Programme** | €5.4 billion | Environment, Climate, Energy transition | `LIFE-*` |
| **Creative Europe** | €2.44 billion | Cultural/Creative industries, Media | `CREA-*` |
| **EU4Health** | €5.3 billion | Health sector, Research orgs | `EU4H-*` |

### Priority 2: Infrastructure & Regional Programmes

| Programme | Budget | Target Users | Call ID Pattern |
|-----------|--------|--------------|-----------------|
| **Connecting Europe Facility** | €33.7 billion | Infrastructure, Transport, Energy, Digital | `CEF-*` |
| **European Social Fund+** | €99.26 billion | Employment, Skills, Social inclusion | `ESF-*` |
| **ERDF** | ~€226 billion | Regional development, SMEs | `ERDF-*` |
| **InvestEU** | €26 billion | Investment, Finance | `INVESTEU-*` |

### Priority 3: Specialized Programmes

| Programme | Budget | Target Users | Call ID Pattern |
|-----------|--------|--------------|-----------------|
| **European Defence Fund** | €7.95 billion | Defence industry | `EDF-*` |
| **CERV** | €1.55 billion | Civil society, Democracy | `CERV-*` |
| **Single Market Programme** | €4.2 billion | SMEs, Consumer protection | `SMP-*` |
| **Innovation Fund** | €38 billion | Net-zero technologies | `INNOVFUND-*` |

---

## Technical Integration Plan

### Phase 1: Unified Call Search API (Week 1-2)

The EU Funding & Tenders Portal uses a **single API** for ALL programmes:

```
API Endpoint: https://api.tech.ec.europa.eu/search-api/prod/rest/search
API Key: SEDIA
```

#### 1.1 Create Multi-Programme Call Service

**File:** `app/services/eu_programmes_call_service.py`

```python
class EUProgrammesCallService:
    """
    Unified service for searching funding calls across ALL EU programmes.
    Uses the EU Funding & Tenders Portal SEDIA API.
    """

    PROGRAMME_CODES = {
        # Priority 1
        'HORIZON': '43108390',  # Horizon Europe
        'ERASMUS': '43108476',  # Erasmus+ 2021-2027
        'DIGITAL': '43251567',  # Digital Europe Programme
        'LIFE': '43108406',     # LIFE Programme
        'CREA': '43108391',     # Creative Europe
        'EU4H': '43252405',     # EU4Health

        # Priority 2
        'CEF': '43108365',      # Connecting Europe Facility
        'ESF': '...',           # European Social Fund+

        # Priority 3
        'EDF': '43298916',      # European Defence Fund
        'CERV': '43251589',     # Citizens, Equality, Rights and Values
        'SMP': '43251447',      # Single Market Programme
        'INNOVFUND': '...',     # Innovation Fund
    }

    def search_calls(
        self,
        keywords: str,
        programmes: List[str] = None,  # Filter by programme(s)
        status: str = 'open',
        deadline_from: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search funding calls across multiple EU programmes.

        Args:
            keywords: Search terms
            programmes: List of programme codes (e.g., ['HORIZON', 'ERASMUS'])
                       None = search all programmes
            status: 'open', 'forthcoming', 'closed', or 'all'
            deadline_from: ISO date string
            limit: Max results
        """
        pass
```

#### 1.2 Update Constants Module

**Add to:** `app/core/constants.py`

```python
# EU Funding Programmes Configuration
EU_PROGRAMMES = {
    'HORIZON': {
        'code': '43108390',
        'name': 'Horizon Europe',
        'short_name': 'Horizon Europe',
        'budget': 95_500_000_000,
        'period': '2021-2027',
        'call_pattern': r'^HORIZON-',
        'categories': ['research', 'innovation', 'erc', 'eic', 'msca'],
    },
    'ERASMUS': {
        'code': '43108476',
        'name': 'Erasmus+',
        'short_name': 'Erasmus+',
        'budget': 26_200_000_000,
        'period': '2021-2027',
        'call_pattern': r'^ERASMUS-',
        'categories': ['education', 'training', 'youth', 'sport'],
    },
    'DIGITAL': {
        'code': '43251567',
        'name': 'Digital Europe Programme',
        'short_name': 'Digital Europe',
        'budget': 7_590_000_000,
        'period': '2021-2027',
        'call_pattern': r'^DIGITAL-',
        'categories': ['digital', 'ai', 'cybersecurity', 'skills'],
    },
    'LIFE': {
        'code': '43108406',
        'name': 'LIFE Programme',
        'short_name': 'LIFE',
        'budget': 5_400_000_000,
        'period': '2021-2027',
        'call_pattern': r'^LIFE-',
        'categories': ['environment', 'climate', 'energy', 'nature'],
    },
    'CREA': {
        'code': '43108391',
        'name': 'Creative Europe',
        'short_name': 'Creative Europe',
        'budget': 2_440_000_000,
        'period': '2021-2027',
        'call_pattern': r'^CREA-',
        'categories': ['culture', 'media', 'creative', 'arts'],
    },
    'EU4H': {
        'code': '43252405',
        'name': 'EU4Health Programme',
        'short_name': 'EU4Health',
        'budget': 5_300_000_000,
        'period': '2021-2027',
        'call_pattern': r'^EU4H-',
        'categories': ['health', 'pandemic', 'healthcare'],
    },
    'CEF': {
        'code': '43108365',
        'name': 'Connecting Europe Facility',
        'short_name': 'CEF',
        'budget': 33_700_000_000,
        'period': '2021-2027',
        'call_pattern': r'^CEF-',
        'categories': ['infrastructure', 'transport', 'energy', 'digital'],
    },
    'EDF': {
        'code': '43298916',
        'name': 'European Defence Fund',
        'short_name': 'EDF',
        'budget': 7_950_000_000,
        'period': '2021-2027',
        'call_pattern': r'^EDF-',
        'categories': ['defence', 'security', 'technology'],
    },
    'CERV': {
        'code': '43251589',
        'name': 'Citizens, Equality, Rights and Values',
        'short_name': 'CERV',
        'budget': 1_550_000_000,
        'period': '2021-2027',
        'call_pattern': r'^CERV-',
        'categories': ['democracy', 'rights', 'equality', 'civil'],
    },
    'SMP': {
        'code': '43251447',
        'name': 'Single Market Programme',
        'short_name': 'Single Market',
        'budget': 4_200_000_000,
        'period': '2021-2027',
        'call_pattern': r'^SMP-',
        'categories': ['sme', 'market', 'competition', 'consumer'],
    },
}
```

### Phase 2: Programme-Specific Knowledge (Week 2-3)

#### 2.1 Programme-Specific Built-in Knowledge

**Add to ToolAwareAgent's BUILT_IN_KNOWLEDGE:**

```markdown
## Other EU Funding Programmes

### Erasmus+ (€26.2B, 2021-2027)
**Focus:** Education, training, youth, sport
**Key Actions:**
- KA1: Learning Mobility (student/staff exchanges)
- KA2: Cooperation Partnerships (institutional projects)
- KA3: Policy Reform Support
**Typical Consortium:** 3+ partners from 3+ Programme Countries
**Funding Rate:** 80% (lump sum model)

### Digital Europe Programme (€7.59B, 2021-2027)
**Focus:** Digital transformation, AI, cybersecurity
**Priorities:**
1. Supercomputing
2. Artificial Intelligence
3. Cybersecurity
4. Advanced Digital Skills
5. Digital Transformation
**Typical Grant:** €1-10M depending on topic

### LIFE Programme (€5.4B, 2021-2027)
**Focus:** Environment and climate action
**Sub-programmes:**
- Nature & Biodiversity
- Circular Economy & Quality of Life
- Climate Change Mitigation & Adaptation
- Clean Energy Transition
**Funding Rate:** 60-95% depending on project type

### Creative Europe (€2.44B, 2021-2027)
**Focus:** Cultural and creative sectors
**Strands:**
- CULTURE: Cooperation projects, platforms, networks
- MEDIA: Audiovisual sector support
- CROSS-SECTORAL: Innovation, media literacy
**Funding Rate:** 60-80%

### EU4Health (€5.3B, 2021-2027)
**Focus:** Health crisis preparedness and systems
**Objectives:**
- Disease prevention & health promotion
- Cross-border health threats
- Medicines, devices & crisis-relevant products
- Healthcare systems resilience
```

#### 2.2 Programme Detection in Intent Classifier

**Update:** `app/services/unified_intent_classifier.py`

```python
PROGRAMME_KEYWORDS = {
    'HORIZON': ['horizon', 'horizon europe', 'h2020', 'erc', 'eic', 'msca'],
    'ERASMUS': ['erasmus', 'education', 'student exchange', 'learning mobility', 'ka1', 'ka2'],
    'DIGITAL': ['digital europe', 'digitalization', 'ai programme', 'cybersecurity funding'],
    'LIFE': ['life programme', 'life funding', 'environment funding', 'climate action'],
    'CREA': ['creative europe', 'media funding', 'culture funding', 'audiovisual'],
    'EU4H': ['eu4health', 'health programme', 'pandemic preparedness'],
    'CEF': ['connecting europe', 'infrastructure funding', 'transport funding'],
    'EDF': ['defence fund', 'defense funding', 'military research'],
    'CERV': ['citizens rights', 'democracy funding', 'values programme'],
}

def detect_programme(query: str) -> List[str]:
    """Detect which EU programme(s) a query relates to."""
    query_lower = query.lower()
    detected = []
    for programme, keywords in PROGRAMME_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            detected.append(programme)
    return detected or ['HORIZON']  # Default to Horizon Europe
```

### Phase 3: New Tools for Multi-Programme Search (Week 3-4)

#### 3.1 Add New Tools to ToolAwareAgent

```python
# New tool: search_eu_programmes
self.register_tool(Tool(
    name="search_eu_programmes",
    description="Search for funding calls across ALL EU programmes (Horizon Europe, Erasmus+, Digital Europe, LIFE, Creative Europe, EU4Health, etc.)",
    category=ToolCategory.CALLS,
    parameters={
        "keywords": "Search keywords",
        "programmes": "Optional: List of programmes to search (e.g., ['ERASMUS', 'LIFE']). Default: all",
        "status": "Optional: 'open', 'forthcoming', 'closed', or 'all'. Default: 'open'",
        "limit": "Optional: Max results. Default: 20"
    },
    examples=[
        "search_eu_programmes(keywords='climate education', programmes=['ERASMUS', 'LIFE'])",
        "search_eu_programmes(keywords='AI cybersecurity', programmes=['DIGITAL', 'HORIZON'])",
        "search_eu_programmes(keywords='biodiversity')",  # Searches all programmes
    ]
))

# New tool: get_programme_info
self.register_tool(Tool(
    name="get_programme_info",
    description="Get detailed information about a specific EU funding programme (budget, eligibility, key actions, typical grants)",
    category=ToolCategory.DOCUMENTS,
    parameters={
        "programme": "Programme code: HORIZON, ERASMUS, DIGITAL, LIFE, CREA, EU4H, CEF, EDF, CERV, SMP"
    },
    examples=[
        "get_programme_info(programme='ERASMUS')",
        "get_programme_info(programme='DIGITAL')",
    ]
))

# New tool: recommend_programmes
self.register_tool(Tool(
    name="recommend_programmes",
    description="Get programme recommendations based on project description and organization type",
    category=ToolCategory.DOCUMENTS,
    parameters={
        "project_description": "Brief description of the project idea",
        "organization_type": "Optional: 'university', 'research', 'sme', 'ngo', 'public_body'",
        "focus_areas": "Optional: List of focus areas like ['climate', 'digital', 'education']"
    },
    examples=[
        "recommend_programmes(project_description='AI for climate prediction', organization_type='university')",
        "recommend_programmes(project_description='Student exchange platform', focus_areas=['education', 'digital'])",
    ]
))
```

### Phase 4: Database Schema Updates (Week 4)

#### 4.1 Update funding_calls Table

```sql
-- Add programme column to funding_calls
ALTER TABLE funding_calls
ADD COLUMN IF NOT EXISTS programme_code VARCHAR(20) DEFAULT 'HORIZON';

-- Add index for programme filtering
CREATE INDEX IF NOT EXISTS idx_funding_calls_programme
ON funding_calls(programme_code);

-- Update existing data
UPDATE funding_calls
SET programme_code =
    CASE
        WHEN topic_code LIKE 'HORIZON-%' THEN 'HORIZON'
        WHEN topic_code LIKE 'ERASMUS-%' THEN 'ERASMUS'
        WHEN topic_code LIKE 'DIGITAL-%' THEN 'DIGITAL'
        WHEN topic_code LIKE 'LIFE-%' THEN 'LIFE'
        WHEN topic_code LIKE 'CREA-%' THEN 'CREA'
        WHEN topic_code LIKE 'EU4H-%' THEN 'EU4H'
        WHEN topic_code LIKE 'CEF-%' THEN 'CEF'
        WHEN topic_code LIKE 'EDF-%' THEN 'EDF'
        WHEN topic_code LIKE 'CERV-%' THEN 'CERV'
        ELSE 'OTHER'
    END
WHERE programme_code IS NULL OR programme_code = '';
```

### Phase 5: UI/UX Enhancements (Week 5)

#### 5.1 Programme Selector in Agent Responses

When the agent detects a multi-programme query, format response with programme sections:

```markdown
## Funding Opportunities Found

### 🔬 Horizon Europe (3 calls)
1. **HORIZON-CL5-2025-D3-01** - Climate AI Applications
   - Deadline: March 2025 | Budget: €15M

### 📚 Erasmus+ (2 calls)
2. **ERASMUS-EDU-2025-PI-FORWARD** - Forward-Looking Projects
   - Deadline: May 2025 | Budget: €1M

### 🌿 LIFE Programme (1 call)
3. **LIFE-2025-SAP-ENV** - Environment Projects
   - Deadline: September 2025 | Budget: €5M
```

---

## Implementation Order

1. **Week 1:** Create `EU_PROGRAMMES` constants and `EUProgrammesCallService`
2. **Week 2:** Add built-in knowledge for all programmes
3. **Week 3:** Implement new tools (`search_eu_programmes`, `get_programme_info`, `recommend_programmes`)
4. **Week 4:** Database schema updates and data migration
5. **Week 5:** Testing and UI formatting improvements

---

## API Integration Details

### EU Funding & Tenders Portal API

**Endpoint:** `https://api.tech.ec.europa.eu/search-api/prod/rest/search`

**Example Query for Erasmus+:**
```python
import requests

params = {
    "apiKey": "SEDIA",
    "text": "***",
    "pageSize": "50",
    "pageNumber": "1"
}

query = {
    "bool": {
        "must": [
            {"terms": {"type": ["1", "2"]}},  # Calls & Topics
            {"terms": {"status": ["31094502"]}},  # Open
            {"term": {"programmePeriod": "2021 - 2027"}},
            {"terms": {"frameworkProgramme": ["43108476"]}}  # Erasmus+ code
        ]
    }
}

response = requests.get(
    "https://api.tech.ec.europa.eu/search-api/prod/rest/search",
    params={**params, "query": json.dumps(query)}
)
```

### Programme Framework Codes (for API queries)

| Programme | Framework Code |
|-----------|---------------|
| Horizon Europe | 43108390 |
| Erasmus+ | 43108476 |
| Digital Europe | 43251567 |
| LIFE | 43108406 |
| Creative Europe | 43108391 |
| EU4Health | 43252405 |
| CEF | 43108365 |
| EDF | 43298916 |
| CERV | 43251589 |
| SMP | 43251447 |

---

## Expected Outcomes

After full integration:

1. **Users can search across 10+ EU programmes** with a single query
2. **Smart programme recommendations** based on project description
3. **Programme-specific guidance** for eligibility, funding rates, consortiums
4. **Unified deadline tracking** across all programmes
5. **Cross-programme opportunity discovery** (e.g., "Find all climate-related funding")

---

## Sources

- [EU Funding Programmes](https://commission.europa.eu/funding-tenders/find-funding/eu-funding-programmes_en)
- [Erasmus+ Funding Portal](https://erasmus-plus.ec.europa.eu/funding-calls)
- [EU Funding & Tenders Portal API](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/apis)
- [Digital Europe Programme](https://digital-strategy.ec.europa.eu/en/activities/digital-programme)
- [LIFE Programme](https://cinea.ec.europa.eu/programmes/life_en)
- [Creative Europe](https://culture.ec.europa.eu/creative-europe)
