# Changelog Since Commit 672e870

**Date**: January 2, 2026
**Commits analyzed**: 672e87059bde7515dbce798f49d0e112c325e7d4 → HEAD (3b2673b)

---

## Summary

20 commits adding **7 new tools** and **3 new programme extractors** to MAPIT AI, expanding the system from 20 to 27 tools.

---

## New Features

### 1. Multi-Programme Search Tool (3 new tools)

**Purpose**: Search across ALL 6 EU funding programmes (~€150B total) in a single query - the key differentiator for MAPIT AI.

| Tool | Description |
|------|-------------|
| `search_all_programmes` | Cross-programme keyword search with relevance scoring |
| `recommend_programmes` | AI-powered programme recommendations based on project description |
| `get_programme_info` | Get detailed programme information |

**Programmes supported**:
| Programme | Budget | Focus |
|-----------|--------|-------|
| Horizon Europe | €95.5B | Research & Innovation |
| Erasmus+ | €26.2B | Education, Training, Youth, Sport |
| Creative Europe | €2.44B | Culture & Media |
| EU4Health | €5.3B | Health & Crisis Preparedness |
| Digital Europe | €7.5B | Digital Transformation |
| LIFE | €5.4B | Environment & Climate |

**Files**:
- `app/services/tools/multi_programme_search.py`

---

### 2. New Programme Call Extractors

Three new extractors to support additional EU funding programmes:

| Extractor | Programme | Features |
|-----------|-----------|----------|
| `ErasmusPlusExtractor` | Erasmus+ | 27 action types (KA1, KA2, KA3, Jean Monnet, Sport), ECHE requirements, lump sum funding |
| `CreativeEuropeExtractor` | Creative Europe | Culture & Media strands, co-production support |
| `EU4HealthExtractor` | EU4Health | Pandemic preparedness, AMR, cancer initiatives |

**Files**:
- `app/services/call_extractors/erasmus_plus.py`
- `app/services/call_extractors/creative_europe.py`
- `app/services/call_extractors/eu4health.py`

---

### 3. Proposal Quality Scoring Tool (3 new tools)

**Purpose**: Evaluate proposals using EU Horizon Europe evaluation criteria.

| Tool | Description | Scale |
|------|-------------|-------|
| `score_proposal_section` | Evaluate individual sections (excellence/impact/implementation) | 0-5 |
| `score_full_proposal` | Evaluate complete proposals with all three sections | 0-15 |
| `quick_quality_check` | Fast quality indicators for drafts | Quality level |

**Features**:
- EU evaluation criteria (Excellence, Impact, Implementation)
- Quality level classification (EXCELLENT → WEAK)
- Funding probability estimation
- Improvement suggestions with expected score increase
- Fallback rule-based scoring when AI unavailable

**Thresholds**:
- Section threshold: 3.0/5.0
- Overall threshold: 10.0/15.0

**Files**:
- `app/services/tools/proposal_quality_scorer.py`

---

### 4. Budget Validation Tool (1 new tool)

**Purpose**: Validate Horizon Europe proposal budgets against EU funding rules before submission.

| Tool | Description |
|------|-------------|
| `validate_budget` | Check funding rates, cost categories, consortium requirements, budget ranges |

**Validation checks**:
- **Funding rates** by action type (RIA: 100%, IA: 70% for-profit, ERC: 100%, etc.)
- **Cost category constraints** (personnel, equipment, travel, subcontracting)
- **Indirect costs** verification (25% flat rate)
- **Consortium requirements** (min partners, countries, coordinator share)
- **Budget range** validation by action type
- **Duration constraints**

**Issue severity levels**:
- `CRITICAL` - Will disqualify proposal
- `HIGH` - Likely evaluator concern
- `MEDIUM` - Suboptimal but acceptable
- `LOW` - Suggestion for improvement

**Files**:
- `app/services/tools/budget_validator.py`

---

## Manual Testing Instructions

### Prerequisites

Ensure Docker services are running:
```bash
docker compose up -d
```

Verify services are healthy:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

### Test via V3 Conversation API

**Base URL**: `http://localhost:8000/api/v3/conversation`

#### Test 1: Multi-Programme Search
```bash
curl -X POST "http://localhost:8000/api/v3/conversation/test-001/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find funding opportunities for renewable energy research across all EU programmes"
  }'
```

**Expected**: Results grouped by programme with relevance scores.

#### Test 2: Programme Recommendations
```bash
curl -X POST "http://localhost:8000/api/v3/conversation/test-002/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What EU programmes would be best for a university developing AI tools for early cancer detection?"
  }'
```

**Expected**: Ranked recommendations with Horizon Europe and EU4Health likely at top.

#### Test 3: Budget Validation
```bash
curl -X POST "http://localhost:8000/api/v3/conversation/test-003/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you validate my budget? Total cost 4 million euros, EU contribution 4 million, RIA action type, 36 months duration, 8 partners"
  }'
```

**Expected**: Compliance score, passed checks, and any issues identified.

#### Test 4: Proposal Quality Check
```bash
curl -X POST "http://localhost:8000/api/v3/conversation/test-004/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Score this excellence section: Our project aims to advance the state of the art in renewable energy storage. The methodology combines electrochemical analysis with machine learning optimization. We will achieve breakthrough performance in battery efficiency exceeding current lithium-ion technology by 40%."
  }'
```

**Expected**: Score (0-5), quality level, strengths, weaknesses, improvement suggestions.

#### Test 5: Programme Info (Erasmus+)
```bash
curl -X POST "http://localhost:8000/api/v3/conversation/test-005/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about the Erasmus+ programme - what action types are available?"
  }'
```

**Expected**: Detailed info about Erasmus+ including KA1, KA2, KA3 action types.

#### Test 6: Streaming Response
```bash
curl -X POST "http://localhost:8000/api/v3/conversation/test-006/message/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Search for open health funding calls across all programmes"
  }'
```

**Expected**: SSE stream with tool_call, tool_result, and token events.

---

### Run Integration Tests

```bash
# Run all new tool tests
pytest tests/test_new_tools_integration.py -v

# Run specific test classes
pytest tests/test_new_tools_integration.py::TestMultiProgrammeSearchConfiguration -v
pytest tests/test_new_tools_integration.py::TestBudgetValidation -v
pytest tests/test_new_tools_integration.py::TestProposalSectionScoring -v
pytest tests/test_new_tools_integration.py::TestToolAwareAgentIntegration -v
```

---

### Test Tool Functions Directly (Python)

```python
# Start Python shell
python3

# Test multi-programme search
from app.services.tools.multi_programme_search import (
    search_all_programmes_execute,
    get_programme_recommendations_execute,
    get_programme_info_execute
)

# Search across all programmes
result = search_all_programmes_execute(keywords="renewable energy", status="open")
print(f"Found {result['total_results']} results")
print(f"Programmes with results: {result['programmes_with_results']}")

# Get programme recommendations
result = get_programme_recommendations_execute(
    description="Student mobility programme between European universities",
    organization_type="university"
)
for rec in result['recommendations'][:3]:
    print(f"  {rec['programme_icon']} {rec['programme_name']}: {rec['reasons']}")

# Get programme info
result = get_programme_info_execute(programme='erasmus_plus')
print(f"Programme: {result['info']['name']}")
print(f"Budget: {result['info']['budget']}")
print(f"Focus: {result['info']['focus']}")
```

```python
# Test budget validation
from app.services.tools.budget_validator import validate_budget_execute

# Valid RIA budget
result = validate_budget_execute(
    total_cost=4_000_000,
    eu_contribution=4_000_000,
    action_type='RIA',
    duration_months=36,
    num_partners=8
)
print(f"Valid: {result['valid']}")
print(f"Compliance Score: {result['compliance_score']}/100")
print(f"Summary: {result['summary']}")

# Test with issues (insufficient partners)
result = validate_budget_execute(
    total_cost=4_000_000,
    eu_contribution=4_000_000,
    action_type='RIA',
    num_partners=2  # Below minimum of 3
)
print(f"Valid: {result['valid']}")
print(f"Critical issues: {result['critical_count']}")
for issue in result['issues']:
    print(f"  [{issue['level']}] {issue['message']}")
```

```python
# Test proposal quality scoring
import asyncio
from app.services.tools.proposal_quality_scorer import (
    quick_quality_check_execute,
    score_proposal_section_execute
)

# Quick quality check
result = asyncio.run(quick_quality_check_execute(
    text="Our project aims to develop innovative solutions for climate monitoring using AI.",
    context="objectives"
))
print(f"Quality estimate: {result['quality_estimate']}/5.0")
print(f"Quality level: {result['quality_level']}")
print(f"Suggestions: {result['suggestions']}")

# Full section scoring
result = asyncio.run(score_proposal_section_execute(
    content="""Our project aims to advance the state of the art in renewable energy storage.
    The methodology combines electrochemical analysis with machine learning optimization.
    We will achieve breakthrough performance in battery efficiency exceeding current
    lithium-ion technology by 40%. Our interdisciplinary approach brings together
    materials science, AI, and chemical engineering expertise.""",
    section_type="excellence",
    action_type="RIA"
))
print(f"Score: {result['score']}/5.0")
print(f"Quality level: {result['quality_level']}")
print(f"Threshold met: {result['threshold_met']}")
```

---

## Commit History

| Commit | Description |
|--------|-------------|
| `3b2673b` | del ralphloop |
| `300e186` | Add integration tests for new tools (#8) |
| `f7d3bae` | Add budget validation tool (#7) |
| `ad7b325` | Add proposal quality scoring tool (#6) |
| `1ec7a92` | Integrate multi-programme tools into ToolAwareAgent (#5) |
| `065af0d` | feat: Add multi-programme search tool for unified EU funding discovery |
| `543746e` | feat: Add EU4Health Programme call extractor |
| `e53ae92` | feat: Add Creative Europe Programme call extractor |
| `e39c62c` | feat: Add Erasmus+ Programme call extractor |
| `c971c1c` | Add live AI response quality integration tests (#26) |
| `4af4a12` | Integrate ResponseQualityAnalyzer into ToolAwareAgent |
| `a928640` | test (#14) |
| `11c9e12` | Update SHARED_TASK_NOTES.md for Iteration 3 progress (#13) |
| `bf72653` | Add comprehensive integration tests for enterprise API routes (#12) |
| `93942cc` | Fix all failing tests and add type safety (#11) |
| `31b2a22` | Register enterprise route modules in main application (#10) |
| `28f084b` | celery removed |
| `61e842c` | Add enterprise features: saved searches, collaboration, audit, multi-tenancy |
| `1d39c29` | Add enterprise features: analytics API, AI proposal reviewer, auth, rate limiting |
| `76d1cf5` | Add feature completeness infrastructure (Priority 4) (#7) |
| `d60165a` | Add performance optimization infrastructure (Priority 3) (#6) |

---

## Document Ingestion Status

### Current State (as of January 2, 2026)

| Programme | Documents | Chunks | Funding Calls | Status |
|-----------|-----------|--------|---------------|--------|
| **Horizon Europe** | 115 PDFs | 36,577 | 2,270 | ✅ Fully ingested |
| **Erasmus+** | 0 | 0 | 0 | ❌ Needs documents |
| **Creative Europe** | 0 | 0 | 0 | ❌ Needs documents |
| **EU4Health** | 0 | 0 | 0 | ❌ Needs documents |
| **Digital Europe** | 0 | 0 | 0 | ❌ Needs documents |
| **LIFE** | 0 | 0 | 0 | ❌ Needs documents |

### What's Been Ingested (Horizon Europe Only)

Located in `newdocs/`:
- **2025 Work Programmes** (13 PDFs): Health, Digital, Climate, Food, Culture, Security, etc.
- **EIC Work Programme 2026** (1 PDF)
- **ERC Work Programme 2026** (2 PDFs)
- **Grant Agreements & Contracts** (5 PDFs): MGA templates, FPA
- **Guidance Documents** (17 PDFs): AGA, Programme Guide, LEAR rules, etc.
- **Simplified Cost Decisions** (10 PDFs): Lump sum, unit costs
- **Templates & Forms** (70+ files): Application forms, evaluation forms, audit templates

---

### Documents Needed for New Programmes

#### 1. Erasmus+ (€26.2B) - PRIORITY HIGH

| Document | Download URL |
|----------|--------------|
| **Erasmus+ Programme Guide 2025** | https://erasmus-plus.ec.europa.eu/programme-guide/erasmusplus-programme-guide |
| **Annual Work Programme 2025** | https://erasmus-plus.ec.europa.eu/document/erasmus-annual-work-programme-2025 |
| **Erasmus+ Grant Agreements** | https://erasmus-plus.ec.europa.eu/resources-and-tools/documents-for-applicants |
| **National Agency Guides** | Check your country's National Agency website |

**Key Action Types to Cover**:
- KA1: Learning Mobility (Higher Ed, VET, School, Adult, Youth)
- KA2: Cooperation Partnerships, Capacity Building
- KA3: Policy Development
- Jean Monnet Actions
- Sport Actions

#### 2. Creative Europe (€2.44B)

| Document | Download URL |
|----------|--------------|
| **Creative Europe Programme Guide** | https://creative-europe.ec.europa.eu/resources |
| **CULTURE Strand Guidelines** | https://creative-europe.ec.europa.eu/calls/culture-calls |
| **MEDIA Strand Guidelines** | https://creative-europe.ec.europa.eu/calls/media-calls |
| **Cross-sectoral Guidelines** | https://creative-europe.ec.europa.eu/calls/cross-sectoral-calls |

**Strands to Cover**:
- Culture: Cooperation projects, European networks, platforms
- MEDIA: Development, distribution, festivals, networks
- Cross-sectoral: Labs, media literacy, news

#### 3. EU4Health (€5.3B) - PRIORITY HIGH (health sector)

| Document | Download URL |
|----------|--------------|
| **EU4Health Work Programme 2025** | https://health.ec.europa.eu/funding/eu4health-programme-2021-2027/eu4health-work-programmes_en |
| **EU4Health Programme Guidelines** | https://health.ec.europa.eu/funding/eu4health-programme-2021-2027_en |
| **HaDEA Call Documents** | https://hadea.ec.europa.eu/calls-proposals_en |

**Priority Areas to Cover**:
- Europe's Beating Cancer Plan
- Pharmaceutical Strategy
- European Health Data Space
- HERA (Health Emergency Preparedness)
- AMR Action Plan

#### 4. Digital Europe (€7.5B)

| Document | Download URL |
|----------|--------------|
| **Digital Europe Work Programme 2025-2027** | https://digital-strategy.ec.europa.eu/en/activities/work-programmes-digital |
| **DEP Programme Guidelines** | https://digital-strategy.ec.europa.eu/en/activities/digital-programme |

**Priorities to Cover**:
- High Performance Computing (HPC)
- Artificial Intelligence
- Cybersecurity
- Advanced Digital Skills
- Digital Transformation (EDIHs)

#### 5. LIFE Programme (€5.4B)

| Document | Download URL |
|----------|--------------|
| **LIFE Work Programme 2024-2027** | https://cinea.ec.europa.eu/programmes/life/life-calls-proposals_en |
| **LIFE Programme Guidelines** | https://cinea.ec.europa.eu/programmes/life_en |

**Sub-programmes to Cover**:
- Nature & Biodiversity
- Circular Economy & Quality of Life
- Climate Change Mitigation & Adaptation
- Clean Energy Transition

---

### Document Ingestion Instructions

After downloading documents, place them in appropriate directories:

```bash
# Create directories for new programmes
mkdir -p newdocs/erasmus_plus
mkdir -p newdocs/creative_europe
mkdir -p newdocs/eu4health
mkdir -p newdocs/digital_europe
mkdir -p newdocs/life_programme
```

Then run the ingestion script:

```bash
# Ingest new documents (adjust script as needed)
python scripts/ingest_newdocs.py --programme erasmus_plus
python scripts/ingest_newdocs.py --programme creative_europe
python scripts/ingest_newdocs.py --programme eu4health
```

**Note**: The extractors (`app/services/call_extractors/*.py`) are already implemented and ready to process these documents once downloaded.

---

### Quick Reference: Official Programme Portals

| Programme | Portal | Call Search |
|-----------|--------|-------------|
| Horizon Europe | [Research & Innovation Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/) | [Open Calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search) |
| Erasmus+ | [Erasmus+ Portal](https://erasmus-plus.ec.europa.eu/) | [Call Documents](https://erasmus-plus.ec.europa.eu/programme-guide) |
| Creative Europe | [Creative Europe Portal](https://creative-europe.ec.europa.eu/) | [Funding Opportunities](https://creative-europe.ec.europa.eu/calls) |
| EU4Health | [EU4Health Portal](https://health.ec.europa.eu/funding/eu4health-programme-2021-2027_en) | [HaDEA Calls](https://hadea.ec.europa.eu/calls-proposals_en) |
| Digital Europe | [Digital Strategy Portal](https://digital-strategy.ec.europa.eu/en/activities/digital-programme) | [Funding Calls](https://digital-strategy.ec.europa.eu/en/funding) |
| LIFE | [LIFE Programme Portal](https://cinea.ec.europa.eu/programmes/life_en) | [CINEA Calls](https://cinea.ec.europa.eu/programmes/life/life-calls-proposals_en) |

---

## Tool Count

| Category | Before | After |
|----------|--------|-------|
| Statistics Tools | 2 | 2 |
| Comparison Tools | 1 | 1 |
| Document Tools | 1 | 1 |
| Call Tools | 2 | 2 |
| Project Tools | 7 | 7 |
| Proposal Support Tools | 5 | 5 |
| Proposal Planning Tools | 2 | 2 |
| **Multi-Programme Tools** | 0 | **3** |
| **Proposal Quality Tools** | 0 | **3** |
| **Budget Validation Tool** | 0 | **1** |
| **Total** | **20** | **27** |
