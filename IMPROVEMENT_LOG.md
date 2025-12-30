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

## Upcoming Iterations

**Iteration 2:** Creative Europe Programme Call Extractor
**Iteration 3:** EU4Health Programme Call Extractor
**Iteration 4:** Update tool orchestration for multi-programme support
**Iteration 5:** Add multi-programme search tool
**Iterations 6-10:** Testing and validation
**Iterations 11-15:** Proposal writing enhancements
**Iterations 16-20:** Security, performance, documentation
