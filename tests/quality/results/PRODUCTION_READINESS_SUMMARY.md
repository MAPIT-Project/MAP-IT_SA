# MAPIT Production Quality Validation - Summary Report

**Generated:** 2026-01-23
**PRD Version:** V3 - Application-First
**Passing Threshold:** 80/100

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Scenarios | 42 |
| Scenarios Found | 41 |
| **Passed** | 25 (61.0%) |
| Failed | 8 |
| Max Attempts | 3 |
| Close to Threshold | 5 |
| Not Found | 1 |
| **Average Quality Score** | 81.4/100 |
| **Average Factual Score** | 97.9/100 |

### Production Readiness: ❌ NOT READY

The system is not production ready. While the average quality score (81.4) exceeds the threshold (80), only 61% of scenarios pass individually.

---

## Blocking Issues (Score < 80)

| Scenario | Score | Status | Issue |
|----------|-------|--------|-------|
| 001 - Programme Discovery | 79.7 | FAIL | Requires further fix attempts |
| 002 - Programme Comparison | 78.0 | FAIL | 6 critical failures (factual) |
| 003 - Programme Recommendation | 77.0 | FAIL | 2 critical failures |
| 005 - Full Proposal Journey | 78.5 | MAX_ATTEMPTS | Tool selection issues |
| 006 - Budget Iteration | 76.6 | MAX_ATTEMPTS | LLM uses wrong tool |
| 007 - Timeline Refinement | 79.0 | MAX_ATTEMPTS | LLM uses wrong tool |

---

## Phase-by-Phase Results

### Phase 2: Multi-Programme Navigation (001-004)
- **Status:** 0/4 PASS
- **Issues:** Programme navigation scenarios have low scores due to factual errors and tool selection

### Phase 3: Proposal Workflow (005-008)
- **Status:** 0/4 PASS
- **Issues:** LLM consistently selects `search_documents` instead of specialized tools

### Phase 4: Partner Discovery (009-012)
- **Status:** 0/4 PASS (all CLOSE_TO_THRESHOLD)
- **Issues:** Context truncation, tool selection, scores 75-79

### Phase 5: Personalization (013-016)
- **Status:** 3/4 PASS
- **Best:** Preference Filtering (83.0)
- **Issue:** User Context Learning at 79.4

### Phase 6: Strategic Planning (017-020)
- **Status:** 2/4 PASS
- **Best:** Risk Assessment (83.4), Capacity Building (82.6)
- **Issues:** Funding Strategy, Portfolio Planning marked FAIL in result files

### Phase 7: Comparisons (021-024)
- **Status:** 2/4 PASS
- **Best:** Funding Type Comparison (83.8), Timeline Comparison (82.2)
- **Issues:** Success Rate Analysis, Budget Comparison marked FAIL

### Phase 8: Deadline Management (025-028)
- **Status:** 4/4 PASS ✓
- **Best:** Urgent Deadline (85.0), Multi-Call Timeline (83.8)

### Phase 9: Complex Eligibility (029-032)
- **Status:** 4/4 PASS ✓
- **Best:** Multi-Factor Eligibility (84.6)

### Phase 10: Erasmus+ Specific (033-035)
- **Status:** 3/3 PASS ✓
- **Best:** Erasmus Accreditation (83.8)

### Phase 11: Creative Europe Specific (036-038)
- **Status:** 3/3 PASS ✓
- **Best:** Creative Europe Strand (83.0)

### Phase 12: Error Handling (039-042)
- **Status:** 4/4 PASS ✓
- **Best:** Out of Scope (85.0), Outdated Information (85.0)

---

## Files Modified During Fixes

All fixes were applied to production application files in `app/`:

1. **app/services/agents/tool_aware_agent.py** - Primary file modified across all fix attempts
   - Added query detection methods for various scenario types
   - Added guidance generators for built-in knowledge responses
   - Improved tool selection logic
   - Enhanced response synthesis

---

## Common Failure Patterns

1. **Tool Selection Issues**
   - LLM defaults to `search_documents` instead of specialized tools
   - Affects: Budget Iteration, Timeline Refinement, Full Proposal Journey
   - Root cause: Model behavior not fully controlled by prompt engineering

2. **Context Truncation**
   - Multi-turn conversations lose context in later turns
   - Affects: Partner Comparison, Network Exploration
   - Root cause: Context window management

3. **Factual Accuracy**
   - Programme Comparison has 6 critical factual failures
   - Cross-programme information sometimes confused

---

## Recommendations

1. **Re-run all scenarios** after the accumulated fixes to get accurate final scores
2. **Address tool selection** issues in proposal workflow scenarios
3. **Improve context preservation** for partner discovery scenarios
4. **Verify factual data** in programme comparison scenarios

---

## Technical Notes

- Report generated from result files in `tests/quality/results/scenarios/*.json`
- Some scenarios have result files in `tests/quality/results/phase*/` subdirectories
- PRD documentation shows fixes were applied but result files may be stale
- Consortium Building (008) result file has parsing issues
