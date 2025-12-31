# MAPIT AI Improvement Log

This log tracks iterative improvements made to MAPIT AI to make it the definitive tool for EU research funding management.

---

## Iteration 1/20 - Erasmus+ Programme Call Extractor

**Date:** 2025-12-31
**Focus Area:** Program Expansion
**Priority Level:** 2

### What was improved
Added comprehensive Erasmus+ Programme call extractor to support the EU's largest education and training funding programme (€26.2B budget).

### Why this was prioritized
Erasmus+ is one of the most important EU funding programmes, frequently requested by research managers and universities. The existing architecture already supported multi-programme extraction via a clean base class, making this a high-impact, low-risk improvement that immediately expands utility to a major new audience.

### What was changed

**New Files:**
- `app/services/call_extractors/erasmus_plus.py` - Complete ErasmusPlusExtractor implementation

**Modified Files:**
- `app/services/call_extractors/__init__.py` - Added ErasmusPlusExtractor to exports and EXTRACTORS dict

**Key Features Implemented:**
1. **Topic Code Recognition:** 7 regex patterns for all Erasmus+ topic code formats
   - Education actions (ERASMUS-EDU-2025-KA1-HED-DEGREE)
   - Sport actions (ERASMUS-SPORT-2025-SSCP)
   - Jean Monnet actions (ERASMUS-JMO-2025-MODULE)
   - Youth actions and virtual exchanges

2. **Action Types:** 27 distinct action types mapped
   - Key Action 1: Learning Mobility (KA1-HED, KA1-VET, KA1-SCH, KA1-ADU, KA1-YOU)
   - Key Action 2: Cooperation (KA2-COOP, KA2-SSP, KA2-CBHE, KA2-ALLIANCES, KA2-COE)
   - Key Action 3: Policy Support (KA3-INC-SOC, KA3-YOUTH-TOG)
   - Jean Monnet: JMO-MODULE, JMO-CHAIR, JMO-COE
   - Sport: SPORT-COOP, SPORT-SSCP, SPORT-EVENT

3. **Erasmus+-Specific Features:**
   - Lump sum/unit cost funding model (vs Horizon Europe's actual cost)
   - Budget ranges per action type
   - Duration ranges per action type
   - Programme Countries vs Partner Countries distinction
   - ECHE (Erasmus Charter for Higher Education) requirements
   - Sector classification (HED, VET, SCH, ADU, YOU, SPORT)

4. **Programme Information Method:** `get_programme_info()` returns comprehensive programme details

### Testing
Verified with inline tests:
- ✅ Basic instantiation
- ✅ get_extractor('erasmus_plus') registry lookup
- ✅ Topic code extraction (3/3 codes found)
- ✅ Full call extraction with metadata
- ✅ Programme info retrieval

### Follow-up items
- [ ] Ingest actual Erasmus+ Programme Guide documents
- [ ] Add Erasmus+ to ToolAwareAgent tool discovery
- [ ] Create search_erasmus_calls tool
- [ ] Add Erasmus+ budget calculation support (lump sum model differs from HE)
- [ ] Test with real-world Erasmus+ call documents

---

## Iteration 2/20 - Creative Europe Programme Call Extractor

**Date:** 2025-12-31
**Focus Area:** Program Expansion
**Priority Level:** 2

### What was improved
Added comprehensive Creative Europe Programme call extractor to support the EU's cultural and creative sectors funding (€2.44B budget).

### Why this was prioritized
Creative Europe supports a different user base from Horizon Europe - cultural organizations, media companies, film producers, and creative industries. This expands MAPIT AI's utility to the arts and culture sector, making it a more comprehensive EU funding tool.

### What was changed

**New Files:**
- `app/services/call_extractors/creative_europe.py` - Complete CreativeEuropeExtractor implementation

**Modified Files:**
- `app/services/call_extractors/__init__.py` - Added CreativeEuropeExtractor to exports

**Key Features Implemented:**
1. **Topic Code Recognition:** 5 regex patterns for Creative Europe formats
   - Culture strand (CREA-CULTURE-2025-COOP-1)
   - MEDIA strand (CREA-MEDIA-2025-DEVSLATE)
   - Cross-sectoral strand (CREA-CROSS-2025-MEDIALITERACY)

2. **Action Types:** 27 distinct action types mapped across 3 strands
   - CULTURE: COOP-1/2/3, PLATF, NET, LIT, CIRC
   - MEDIA: DEVSLATE, DEVSINGLE, DEVVG, TVONLINE, FESTIV, etc.
   - CROSS: MEDIALITERACY, CREATIVELAB, NEWS, MEDIAFREEDOM

3. **Creative Europe-Specific Features:**
   - Variable funding rates by action (60-80%)
   - Consortium requirements per action type
   - Budget ranges per action
   - Duration ranges per action
   - Strand-specific eligibility (cultural orgs, audiovisual, news media)
   - Eligible countries including partial association

4. **Programme Information Method:** `get_programme_info()` returns comprehensive programme details

### Testing
Verified with inline tests:
- ✅ Basic instantiation
- ✅ get_extractor('creative_europe') registry lookup
- ✅ Topic code extraction (3/3 codes found)
- ✅ Full call extraction with correct strand detection
- ✅ Funding rate extraction (80% for COOP-1, 70% for DEVSLATE)
- ✅ CROSS strand correctly identified (not confused with MEDIA)

### Follow-up items
- [ ] Ingest actual Creative Europe Work Programme documents
- [ ] Add Creative Europe to ToolAwareAgent tool discovery
- [ ] Create search_creative_europe_calls tool
- [ ] Add Cultural/MEDIA-specific proposal writing support
- [ ] Test with real-world Creative Europe call documents

---

## Iteration 3/20 - EU4Health Programme Call Extractor

**Date:** 2025-12-31
**Focus Area:** Program Expansion
**Priority Level:** 2

### What was improved
Added comprehensive EU4Health Programme call extractor to support the EU's largest health funding programme (€5.3B budget), created as a response to COVID-19.

### Why this was prioritized
EU4Health is the EU's flagship health programme and critical for healthcare institutions, public health organizations, and health research. Adding it completes coverage of major sector-specific programmes and serves a distinct user base focused on public health, crisis preparedness, and healthcare systems.

### What was changed

**New Files:**
- `app/services/call_extractors/eu4health.py` - Complete EU4HealthExtractor implementation

**Modified Files:**
- `app/services/call_extractors/__init__.py` - Added EU4HealthExtractor to exports

**Key Features Implemented:**
1. **Topic Code Recognition:** 5 regex patterns for EU4Health formats
   - Standard format (EU4H-2025-PJ-01)
   - Full name format (EU4HEALTH-2025-PJ-01)
   - Alternative formats

2. **Action Types:** 18 action types mapped
   - Grants: PJ (Project), OA (Operating), JA (Joint Action), SGA, DA, CSA
   - Procurement: PPI, PCP, FWC, SC
   - Thematic: CANCER, AMR, PHARMA, MH, CRISIS, etc.

3. **EU4Health-Specific Features:**
   - Variable funding rates by action type (60-100%)
   - Joint Action support (requires Member State participation)
   - Priority area classification (Cancer, AMR, Pharma, etc.)
   - Budget ranges per action type
   - Consortium requirements (varies by action type)
   - Eligible entity types specific to health sector

4. **Programme Information Method:** Includes flagship initiatives like Europe's Beating Cancer Plan, HERA, European Health Data Space

### Testing
Verified with inline tests:
- ✅ Basic instantiation
- ✅ get_extractor('eu4health') registry lookup
- ✅ Topic code extraction (3/3 codes found)
- ✅ Full call extraction with correct action types
- ✅ Correct funding rates (60% for PJ/OA, 80% for JA)
- ✅ Programme info with general objectives and flagship initiatives

### Follow-up items
- [ ] Ingest actual EU4Health Work Programme documents
- [ ] Add EU4Health to ToolAwareAgent tool discovery
- [ ] Create search_eu4health_calls tool
- [ ] Add health-specific proposal writing templates
- [ ] Support for Joint Action workflow (Member State participation)

---

## Iteration 4/20 - Multi-Programme Search Tool

**Date:** 2025-12-31
**Focus Area:** Feature Enhancement
**Priority Level:** 3

### What was improved
Added unified multi-programme search tool that enables searching across all 6 EU funding programmes in a single query - the key differentiator for MAPIT AI.

### Why this was prioritized
With 6 programme extractors now available, users need a unified way to discover funding opportunities across all programmes. This is the core value proposition of MAPIT AI - being the single source for all EU funding discovery, not just Horizon Europe.

### What was changed

**New Files:**
- `app/services/tools/multi_programme_search.py` - Complete MultiProgrammeSearchTool implementation

**Modified Files:**
- `app/services/tools/__init__.py` - Added multi-programme search tools to exports

**Key Features Implemented:**
1. **Unified Search:** `search_all_programmes_execute()`
   - Cross-programme keyword search
   - Full-text search with relevance scoring
   - Programme-specific filtering
   - Status and year filtering
   - Results grouped by programme

2. **Programme Recommendations:** `get_programme_recommendations_execute()`
   - AI-powered programme matching based on project description
   - Organization type consideration
   - Scoring with reasoning
   - Top 5 programme recommendations

3. **Programme Information:** `get_programme_info_execute()`
   - Detailed programme information
   - Integration with programme extractors
   - Budget, focus, website, eligibility info

4. **Smart Detection:**
   - Keywords automatically mapped to relevant programmes
   - 60+ programme-specific keywords per programme
   - Detected programmes highlighted in results

**Programme Coverage:**
- Horizon Europe (€95.5B) - 🔬 Research & Innovation
- Erasmus+ (€26.2B) - 🎓 Education, Training, Youth, Sport
- Creative Europe (€2.44B) - 🎨 Culture & Media
- EU4Health (€5.3B) - 🏥 Health & Crisis Preparedness
- Digital Europe (€7.5B) - 💻 Digital Transformation
- LIFE (€5.4B) - 🌍 Environment & Climate

### Testing
Verified with inline tests:
- ✅ Multi-programme search tools import
- ✅ get_programme_info_execute() returns all 6 programmes
- ✅ Specific programme info includes extractor details (e.g., Erasmus+ Key Actions)
- ✅ Programme recommendations work for energy/mobility project
- ✅ Recommendations correctly suggest Horizon Europe for research

### Follow-up items
- [ ] Integrate with ToolAwareAgent for natural language queries
- [ ] Add semantic search across programmes
- [ ] Add deadline-based sorting and filtering
- [ ] Create UI component for programme comparison
- [ ] Add programme eligibility checker tool

---

## Iteration 5/20 - Multi-Programme Tools Integration into ToolAwareAgent

**Date:** 2025-12-31
**Focus Area:** Feature Enhancement
**Priority Level:** 3

### What was improved
Integrated the multi-programme search, recommendation, and information tools directly into ToolAwareAgent, enabling natural language queries across all 6 EU funding programmes.

### Why this was prioritized
With the multi-programme tools created in Iteration 4, users couldn't actually use them without direct API calls. Integration into ToolAwareAgent enables the AI agent to automatically use these tools when users ask about funding opportunities across different programmes.

### What was changed

**Modified Files:**
- `app/services/agents/tool_aware_agent.py` - Added 3 new tools and their implementations

**Key Features Implemented:**

1. **New ToolCategory:**
   - Added `ToolCategory.PROGRAMMES` for multi-programme tools

2. **Tool Definitions (in `_init_tools()`):**
   - `search_all_programmes` - Search across all EU programmes with keywords, filters
   - `recommend_programmes` - Get AI-powered programme recommendations
   - `get_programme_info` - Get detailed programme information

3. **Tool Routing (in `_execute_single_tool()`):**
   - Added routing for all 3 new tools to their implementations

4. **Tool Implementations:**
   - `_tool_search_all_programmes()` - Calls `search_all_programmes_execute()`
   - `_tool_recommend_programmes()` - Calls `get_programme_recommendations_execute()`
   - `_tool_get_programme_info()` - Calls `get_programme_info_execute()`

**Example Use Cases Now Possible:**
```
User: "What EU funding programmes can support my AI healthcare research?"
Agent: Uses recommend_programmes() → Returns EU4Health, Horizon Europe, Digital Europe

User: "Find open calls for renewable energy across all programmes"
Agent: Uses search_all_programmes() → Returns calls from Horizon Europe, LIFE, Digital Europe

User: "Tell me about the Erasmus+ programme"
Agent: Uses get_programme_info() → Returns full Erasmus+ details including Key Actions
```

### Testing
Verified with Python tests:
- ✅ ToolAwareAgent class loads with programme-related methods
- ✅ All 3 tool implementation methods exist
- ✅ Tool imports from multi_programme_search work
- ✅ get_programme_info returns all 6 programmes
- ✅ recommend_programmes returns scored recommendations

### Follow-up items
- [ ] Add semantic search across programmes using embeddings
- [ ] Add programme comparison tool
- [ ] Add eligibility checker tool
- [ ] Create integration tests for natural language queries

---

## Upcoming Iterations

**Iteration 6:** Add proposal quality scoring tool
**Iteration 7:** Add budget validation tool
**Iterations 8-12:** Testing and validation
**Iterations 13-17:** Proposal writing enhancements
**Iterations 18-20:** Security, performance, documentation
