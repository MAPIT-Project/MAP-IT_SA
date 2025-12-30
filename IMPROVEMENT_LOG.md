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

## Upcoming Iterations

**Iteration 4:** Update tool orchestration for multi-programme support
**Iteration 5:** Add multi-programme search tool
**Iterations 6-10:** Testing and validation
**Iterations 11-15:** Proposal writing enhancements
**Iterations 16-20:** Security, performance, documentation
