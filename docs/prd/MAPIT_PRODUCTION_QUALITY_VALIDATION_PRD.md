> ⚠️ **ARCHIVED — 20 juli 2026** — Dit document is historisch en niet meer actueel.
> Zie [START_HERE.md](../../../START_HERE.md) voor actuele documentatie.
> Reden: deze validatie-PRD is opgevolgd door de V3-versie en de actuele kwaliteitsrapporten.

# MAPIT Production Quality Validation PRD

> **Purpose**: Validate ALL conversation scenarios against the live API with comprehensive quality checks
> **Method**: Execute every scenario, evaluate with multi-dimensional quality scoring, fix failures until passing
> **Pass Threshold**: ALL scenarios must score >= 80/100, zero critical failures, zero factual errors
> **Target**: Production-ready system within 2 weeks
> **Priority**: CRITICAL - This is the final validation gate before production deployment

---

## Problem Statement

The Advanced Conversation Flows PRD created 47 scenario YAML files, but **many were never actually tested against the live API**. The progress file shows scenarios marked complete with only "YAML syntax validation: PASSED" - not actual execution results.

**Critical Issues Discovered:**
1. ~15-20 scenarios have NO evidence of live API testing
2. No systematic quality scoring was performed
3. No checks for "no results", "incorrect data", "missing data"
4. No fix cycles when scenarios fail
5. System goes to production in weeks without validation

**This PRD fixes that by requiring:**
- Every scenario MUST be executed against the live API
- Every response MUST be quality-scored with 4-dimensional rubric
- Every failure MUST trigger a fix cycle
- Every scenario MUST pass with >= 80/100 before being marked complete

---

## Success Criteria

### Hard Requirements (ALL must pass)
| Criterion | Threshold | Measurement |
|-----------|-----------|-------------|
| Scenarios Executed | 47/47 (100%) | All YAML scenarios run against live API |
| Quality Score | >= 80/100 per scenario | QualityEvaluatorAgent average score |
| Factual Accuracy | >= 90% per scenario | CrossProgrammeAgent validation |
| Zero Critical Failures | 0 | No "ERROR" responses, no crashes |
| No Results Rate | < 5% of turns | Turns with empty/useless responses |
| Data Completeness | >= 85% | Required data fields present |
| Context Preservation | 100% | All follow-ups resolve correctly |

### Quality Dimensions (100 points total)
| Dimension | Max Points | Pass Threshold |
|-----------|------------|----------------|
| Query Fulfillment | 40 | >= 32 (80%) |
| Specificity | 25 | >= 20 (80%) |
| Factual Accuracy | 25 | >= 22 (88%) |
| Actionability | 10 | >= 7 (70%) |

---

## Failure Categories & Detection

### Category 1: NO RESULTS
**Definition**: System returns empty, generic, or deflection response
**Detection Patterns**:
- Response < 100 characters
- Contains: "I don't have", "I cannot find", "no information", "not available"
- Tool returns empty array `[]` or `null`
- Response is generic without specifics

**Action**: Mark as CRITICAL, requires immediate fix

### Category 2: INCORRECT DATA
**Definition**: Response contains factually wrong information
**Detection Methods**:
- CrossProgrammeAgent.validate_programme_facts() returns incorrect facts
- Budget amounts outside known ranges (Horizon: €95.5B, Erasmus: €26.2B, Creative Europe: €2.44B)
- Funding rates wrong (RIA: 100%, IA: 70%, CSA: 100%)
- Eligibility rules incorrect for countries
- Dates/deadlines wrong

**Action**: Mark as CRITICAL, requires immediate fix with correct data source

### Category 3: MISSING DATA
**Definition**: Response omits required information
**Detection Methods**:
- Expected patterns not found (response_contains validation fails)
- Programme mentioned but key details missing (budget, deadlines, eligibility)
- Call search returns results but no call IDs, deadlines, or budgets
- Partner search returns names but no project counts or expertise

**Action**: Mark as HIGH, requires fix to add missing information

### Category 4: UNEXPECTED BEHAVIOR
**Definition**: System behaves erratically or inconsistently
**Detection Methods**:
- Tool called but wrong tool for query type
- Context not preserved (follow-up fails)
- Quality score drops > 15 points between turns
- Response contradicts previous turn
- Error in SSE stream

**Action**: Mark as HIGH, requires investigation and fix

### Category 5: POOR QUALITY
**Definition**: Response is technically correct but unhelpful
**Detection Methods**:
- QualityEvaluatorAgent score < 80
- Specificity score < 20 (vague response)
- Actionability score < 7 (no clear next steps)
- Response is wall of text without structure

**Action**: Mark as MEDIUM, requires prompt/formatting improvement

---

## Test Agents & Their Roles

### Primary Agents (MUST USE)

| Agent | Role | Methods to Call |
|-------|------|-----------------|
| `ConversationFlowAgent` | Execute scenarios | `run_scenario()`, `send_message()` |
| `QualityEvaluatorAgent` | Score every turn | `evaluate_response()`, `evaluate_conversation()` |
| `CrossProgrammeAgent` | Validate facts | `validate_programme_facts()`, `validate_eligibility_rules()` |

### Secondary Agents (USE FOR SPECIFIC SCENARIOS)

| Agent | When to Use | Methods |
|-------|-------------|---------|
| `GoalTrackingAgent` | Multi-turn journeys | `evaluate_progress()`, `check_completion()` |
| `PersonalizationAgent` | Context learning scenarios | `validate_personalization()`, `validate_context_accumulation()` |
| `ContextValidatorAgent` | All scenarios (final) | `validate_context_integrity()` |

---

## Execution Workflow

### Phase 1: EXECUTE
```
For each scenario:
  1. Load YAML from tests/scenarios/advanced/
  2. Create new conversation via API
  3. Execute each turn with ConversationFlowAgent.send_message()
  4. Collect: response_text, tools_used, tool_results, processing_time
  5. Save raw results to tests/quality/results/scenarios/
```

### Phase 2: EVALUATE
```
For each turn in scenario:
  1. Run QualityEvaluatorAgent.evaluate_response(query, response)
  2. Run CrossProgrammeAgent.validate_programme_facts() if programme mentioned
  3. Run CrossProgrammeAgent.validate_eligibility_rules() if eligibility discussed
  4. Check for NO RESULTS patterns
  5. Check for MISSING DATA patterns
  6. Calculate turn score and failure category

For scenario overall:
  1. Calculate average quality score
  2. Check quality degradation (> 15 point drops)
  3. Run ContextValidatorAgent.validate_context_integrity()
  4. Determine PASS/FAIL status
```

### Phase 3: FIX (if FAIL)
```
For each failing scenario:
  1. Identify failure category (NO RESULTS, INCORRECT DATA, etc.)
  2. Identify root cause:
     - Tool not returning data → Check tool implementation
     - Wrong facts → Check knowledge base / prompts
     - Missing context → Check memory service
     - Poor formatting → Check response formatter
  3. Implement fix in codebase
  4. Re-run scenario
  5. Repeat until PASS or escalate
```

### Phase 4: VERIFY
```
After all fixes:
  1. Run full suite 3 times for consistency
  2. All 3 runs must pass
  3. Calculate aggregate metrics
  4. Generate production readiness report
```

---

## Tasks

### ==========================================================
### PHASE 1: Critical Infrastructure
### ==========================================================

### Task 001: Create Production Quality Test Runner
- [x] CREATE: `tests/test_production_quality_validation.py` with:
  - ScenarioExecutionResult dataclass (scenario_name, turns, scores, failures, metadata)
  - TurnResult dataclass (query, response, quality_score, factual_score, failures, tools_used)
  - FailureRecord dataclass (category, severity, description, turn_number, evidence)
  - ProductionQualityRunner class with:
    - `run_scenario(scenario_path)` → ScenarioExecutionResult
    - `evaluate_turn(query, response)` → TurnResult
    - `detect_failures(turn)` → List[FailureRecord]
    - `generate_report(results)` → JSON report
  - Pattern detection for all 5 failure categories
  - Integration with all 6 test agents
- [x] TEST: Verify runner can execute a single scenario end-to-end
- [x] VERIFY: Results saved to `tests/quality/results/scenarios/`

### Task 002: Create Failure Detection Module
- [x] CREATE: `tests/validators/failure_detector.py` with:
  - NoResultsDetector class (patterns, thresholds)
  - IncorrectDataDetector class (fact checking rules)
  - MissingDataDetector class (required field patterns)
  - UnexpectedBehaviorDetector class (consistency checks)
  - PoorQualityDetector class (quality thresholds)
  - `detect_all(turn_result)` → List[FailureRecord]
- [x] TEST: Unit tests for each detector with known good/bad examples
- [x] VERIFY: Detectors correctly categorize sample failures

### Task 003: Create Fix Tracking System
- [x] CREATE: `tests/quality/fix_tracker.py` with:
  - FixAttempt dataclass (scenario, failure, fix_description, before_score, after_score, success)
  - FixTracker class with:
    - `record_failure(scenario, failure)` → Creates fix ticket
    - `record_fix_attempt(scenario, fix_description)` → Logs attempt
    - `record_resolution(scenario, after_score)` → Marks resolved
    - `get_open_failures()` → List of unresolved issues
    - `generate_fix_report()` → Summary of all fixes
  - Persistence to `tests/quality/results/fix_history.json`
- [x] TEST: Track a mock failure through fix cycle
- [x] VERIFY: Fix history persists correctly

### ==========================================================
### PHASE 2: Execute ALL Scenarios (NO SKIPPING)
### ==========================================================

**CRITICAL**: Every scenario MUST be executed. Mark each with actual runtime and score.

### Task 004: Execute Phase 1 Scenarios (Multi-Programme Navigation)
- [x] RUN: `programme_discovery.yaml`
  - Runtime: 98.63 seconds
  - Average Score: 79.67/100
  - Failures: 0
  - Status: NEEDS_IMPROVEMENT (score < 80)
- [x] RUN: `programme_comparison.yaml`
  - Runtime: 185.98 seconds
  - Average Score: 78.0/100
  - Failures: 3 (factual validation false positives - success rates vs funding rates confusion)
  - Status: NEEDS_FIX
- [x] RUN: `programme_recommendation.yaml`
  - Runtime: 80.35 seconds
  - Average Score: 77.0/100
  - Failures: 1
  - Status: NEEDS_FIX
- [x] RUN: `eligibility_routing.yaml`
  - Runtime: 161.99 seconds
  - Average Score: 79.5/100
  - Failures: 1
  - Status: NEEDS_IMPROVEMENT (score < 80)
- [x] FIX: Any failures in Phase 1 scenarios
  - Issue identified: CrossProgrammeAgent fact validation conflates funding rates (RIA=100%, IA=70%) with success rates (~12%)
  - Fix implemented: Updated `_validate_facts_rules()` in `tests/agents/cross_programme_agent.py` to:
    - Process responses line-by-line to avoid cross-line pattern matching issues
    - Skip lines containing success rate keywords ("success rate", "selected", "awarded", "funded proposals")
    - Only validate lines that explicitly mention funding-related terms ("funding", "rate", "cost", "reimburs", "cover")
    - Use more precise regex patterns for funding rate detection
  - Updated LLM prompt in `_validate_facts_llm()` to clearly distinguish between funding rates and success rates
  - Tests created: `tests/agents/test_cross_programme_agent_fix.py` (13 tests, all passing)
  - Test infrastructure created: `tests/quality/test_phase1_scenarios.py`
  - Results saved: `tests/quality/results/phase1/`
- [ ] VERIFY: All 4 scenarios pass with >= 80/100

### Task 005: Execute Phase 2 Scenarios (Proposal Workflows)
- [x] RUN: `full_proposal_journey.yaml` (15 turns - CRITICAL)
  - Runtime: 460.0 seconds
  - Average Score: 78.47/100
  - Failures: 1 (INCORRECT_DATA - budget confusion €5.4B vs €95.5B in success rate response)
  - Status: NEEDS_FIX
- [x] RUN: `budget_iteration.yaml`
  - Runtime: 140.2 seconds
  - Average Score: 79.0/100
  - Failures: 0
  - Status: NEEDS_IMPROVEMENT (score < 80)
- [x] RUN: `timeline_refinement.yaml`
  - Runtime: 172.3 seconds
  - Average Score: 75.8/100
  - Failures: 0
  - Status: NEEDS_FIX
- [x] RUN: `consortium_building.yaml`
  - Runtime: 144.6 seconds
  - Average Score: 77.3/100
  - Failures: 0
  - Status: NEEDS_FIX
- [x] FIX: Any failures in Phase 2 scenarios
  - Common issue: Low actionability scores (0-4/10) across all scenarios
  - **FIX IMPLEMENTED**: Added mandatory "🎯 Next Steps:" section requirement to ToolAwareAgent
  - **FIX IMPLEMENTED**: Added query-aware guidance methods to V3ResponseFormatter
  - **FIX IMPLEMENTED**: Added project guidance footer with actionable resources
  - Test infrastructure created: `tests/quality/test_phase2_scenarios.py`
  - Results saved: `tests/quality/results/phase2/`
- [ ] VERIFY: All 4 scenarios pass with >= 80/100

### Task 006: Execute Phase 3 Scenarios (Partner Discovery)
- [x] RUN: `partner_search_refinement.yaml`
  - Runtime: 167.48 seconds
  - Average Score: 79.0/100
  - Failures: 0
  - Status: NEEDS_IMPROVEMENT (score < 80)
- [x] RUN: `partner_comparison.yaml`
  - Runtime: 166.51 seconds
  - Average Score: 75.4/100
  - Failures: 0
  - Status: NEEDS_FIX
- [x] RUN: `network_exploration.yaml`
  - Runtime: 158.42 seconds
  - Average Score: 76.2/100
  - Failures: 0
  - Status: NEEDS_FIX
- [x] RUN: `organization_deep_dive.yaml`
  - Runtime: 98.57 seconds
  - Average Score: 76.2/100
  - Failures: 0
  - Status: NEEDS_FIX
- [x] TEST_INFRASTRUCTURE: Created `tests/quality/test_phase3_scenarios.py`
  - Individual test methods for each scenario
  - Full Phase 3 execution test with report generation
  - Infrastructure tests (6 tests, all passing)
  - Results directory: `tests/quality/results/phase3/`
- [x] FIX: Any failures in Phase 3 scenarios
  - Common issue: Low actionability scores (0/10) across all scenarios
  - **FIX IMPLEMENTED**: Same actionability fix as Phase 2 (shared root cause)
  - **FIX IMPLEMENTED**: Added partner-specific guidance in `_get_partner_guidance()`
  - Factual accuracy is 100% (excellent)
  - No critical failures
  - Results saved: `tests/quality/results/phase3/`
- [ ] VERIFY: All 4 scenarios pass with >= 80/100

### Task 007: Execute Phase 4 Scenarios (Personalization)
- [x] RUN: `user_context_learning.yaml`
  - Runtime: 230.03 seconds
  - Average Score: 84.6/100
  - Personalization Score: 93.33/100 (factual)
  - Failures: 1 (INCORRECT_DATA - false positive: Erasmus+ budget confused with Horizon Europe €95.5B)
  - Status: NEEDS_FIX
- [x] RUN: `returning_user_context.yaml`
  - Runtime: 151.82 seconds
  - Average Score: 82.0/100
  - Context Preserved: YES (hydrogen context recalled in turn 4)
  - Failures: 0 (turn 2 scored 77/100 - below 80 threshold)
  - Status: NEEDS_IMPROVEMENT
- [x] RUN: `progressive_profile.yaml` (12 turns)
  - Runtime: 398.79 seconds
  - Average Score: 78.17/100
  - Profile Fields Accumulated: 6
  - Failures: 1 (NO_RESULTS on turn 1 - empty response for "We're in the healthcare sector")
  - Status: NEEDS_FIX
- [x] RUN: `preference_filtering.yaml`
  - Runtime: 162.42 seconds
  - Average Score: 84.0/100
  - Preferences Applied: YES
  - Failures: 0
  - Status: PASS
- [x] TEST_INFRASTRUCTURE: Created `tests/quality/test_phase4_scenarios.py`
  - Individual test methods for each scenario
  - Full Phase 4 execution test with report generation
  - Infrastructure tests (6 tests, all passing)
  - Results directory: `tests/quality/results/phase4/`
- [x] FIX: Any failures in Phase 4 scenarios
  - Issue 1: False positive factual error (Erasmus+ budget confused with Horizon Europe)
    - **FIX IMPLEMENTED**: Updated CrossProgrammeAgent budget validation to use distance-based programme association
    - **FIX IMPLEMENTED**: Added 5 new tests for multi-programme budget validation
  - Issue 2: Empty response for generic context messages ("We're in healthcare sector")
    - **FIX IMPLEMENTED**: Added "Handling Context-Building Messages" section to ToolAwareAgent prompt
    - **FIX IMPLEMENTED**: Made it MANDATORY to respond proactively with guidance and follow-up questions
  - Issue 3: Low actionability scores causing turn failures
    - **FIX IMPLEMENTED**: Same actionability fix as Phase 2/3 (shared root cause)
  - Results saved: `tests/quality/results/phase4/`
- [ ] VERIFY: All 4 scenarios pass with >= 80/100

### Task 008: Execute Phase 5 Scenarios (Strategic Planning)
- [ ] RUN: `funding_strategy.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Failures: ___
  - Status: PASS/FAIL
- [ ] RUN: `portfolio_planning.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Failures: ___
  - Status: PASS/FAIL
- [ ] RUN: `capacity_building.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Failures: ___
  - Status: PASS/FAIL
- [ ] RUN: `risk_assessment.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Failures: ___
  - Status: PASS/FAIL
- [x] TEST_INFRASTRUCTURE: Created `tests/quality/test_phase5_scenarios.py`
  - Individual test methods for each scenario
  - Full Phase 5 execution test with report generation
  - Infrastructure tests (6 tests, all passing)
  - Results directory: `tests/quality/results/phase5/`
- [ ] FIX: Any failures in Phase 5 scenarios
- [ ] VERIFY: All 4 scenarios pass with >= 80/100

### Task 009: Execute Phase 6 Scenarios (Comparisons)
- [ ] RUN: `funding_type_comparison.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Factual Accuracy: ___/100
  - Status: PASS/FAIL
- [ ] RUN: `success_rate_analysis.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Data Present: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `budget_comparison.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Numbers Accurate: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `timeline_comparison.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Failures: ___
  - Status: PASS/FAIL
- [ ] FIX: Any failures in Phase 6 scenarios
- [ ] VERIFY: All 4 scenarios pass with >= 80/100

### Task 010: Execute Phase 7 Scenarios (Deadlines)
- [ ] RUN: `urgent_deadline.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Deadline Info Present: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `deadline_tracking.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Failures: ___
  - Status: PASS/FAIL
- [ ] RUN: `call_opening_alert.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Future Calls Found: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `multi_call_timeline.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Failures: ___
  - Status: PASS/FAIL
- [ ] FIX: Any failures in Phase 7 scenarios
- [ ] VERIFY: All 4 scenarios pass with >= 80/100

### Task 011: Execute Phase 8 Scenarios (Complex Eligibility)
- [ ] RUN: `multi_factor_eligibility.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Eligibility Accuracy: ___/100
  - Status: PASS/FAIL
- [ ] RUN: `sme_eligibility.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - SME Rules Correct: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `consortium_eligibility.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Country Rules Correct: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `cross_programme_eligibility.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Double Funding Rules: CORRECT/INCORRECT
  - Status: PASS/FAIL
- [ ] FIX: Any failures in Phase 8 scenarios
- [ ] VERIFY: All 4 scenarios pass with >= 80/100

### Task 012: Execute Phase 9 Scenarios (Erasmus+)
- [ ] RUN: `erasmus_action_selection.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - KA1/KA2/KA3 Correct: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `erasmus_budget_calculation.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Unit Costs Mentioned: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `erasmus_accreditation.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Accreditation Info Correct: YES/NO
  - Status: PASS/FAIL
- [ ] FIX: Any failures in Phase 9 scenarios
- [ ] VERIFY: All 3 scenarios pass with >= 80/100

### Task 013: Execute Phase 10 Scenarios (Creative Europe)
- [ ] RUN: `creative_europe_strand.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - MEDIA/CULTURE/CROSS Correct: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `creative_europe_eligibility.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Country Eligibility Correct: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `creative_europe_cooperation.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Scale Requirements Correct: YES/NO
  - Status: PASS/FAIL
- [ ] FIX: Any failures in Phase 10 scenarios
- [ ] VERIFY: All 3 scenarios pass with >= 80/100

### Task 014: Execute Phase 11 Scenarios (Error Handling)
- [ ] RUN: `conflicting_requirements.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Graceful Degradation: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `outdated_information.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Redirects to Current: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `ambiguous_programme.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Clarification Provided: YES/NO
  - Status: PASS/FAIL
- [ ] RUN: `out_of_scope.yaml`
  - Runtime: ___ seconds
  - Average Score: ___/100
  - Scope Explained: YES/NO
  - Status: PASS/FAIL
- [ ] FIX: Any failures in Phase 11 scenarios
- [ ] VERIFY: All 4 scenarios pass with >= 80/100

### ==========================================================
### PHASE 3: Deep Quality Validation
### ==========================================================

### Task 015: Factual Accuracy Audit
- [ ] AUDIT: Run CrossProgrammeAgent.validate_programme_facts() on ALL turns mentioning programmes
- [ ] RECORD: List all incorrect facts found
- [ ] FIX: Update knowledge base / prompts for each incorrect fact
- [ ] VERIFY: Re-run and confirm 0 incorrect facts

### Task 016: No Results Audit
- [ ] AUDIT: Identify all turns with < 100 character responses
- [ ] AUDIT: Identify all turns containing deflection phrases
- [ ] AUDIT: Identify all tool calls returning empty results
- [ ] RECORD: List all "no results" situations
- [ ] FIX: Improve tool queries, add fallbacks, enhance prompts
- [ ] VERIFY: No results rate < 5%

### Task 017: Missing Data Audit
- [ ] AUDIT: For call searches - verify all have: call_id, deadline, budget, topic
- [ ] AUDIT: For project searches - verify all have: project_id, acronym, budget, partners
- [ ] AUDIT: For partner searches - verify all have: org_name, country, project_count
- [ ] AUDIT: For eligibility queries - verify rules, exceptions, and examples provided
- [ ] RECORD: List all missing data instances
- [ ] FIX: Enhance response formatting, add required fields to tool outputs
- [ ] VERIFY: Data completeness >= 85%

### Task 018: Context Preservation Audit
- [ ] AUDIT: Run all follow-up scenarios and check context preserved
- [ ] AUDIT: Verify numbered references resolve correctly ("tell me more about #2")
- [ ] AUDIT: Verify pronoun resolution ("that call", "their budget")
- [ ] AUDIT: Verify topic continuity across programme switches
- [ ] RECORD: List all context failures
- [ ] FIX: Improve memory service, enhance context injection
- [ ] VERIFY: 100% context preservation

### Task 019: Quality Consistency Audit
- [ ] AUDIT: Run each scenario 3 times, check score variance
- [ ] AUDIT: Identify scenarios with > 10 point variance between runs
- [ ] AUDIT: Check for quality degradation within scenarios (> 15 point drops)
- [ ] RECORD: List all inconsistent scenarios
- [ ] FIX: Stabilize prompts, add guardrails
- [ ] VERIFY: All scenarios have < 10 point variance

### ==========================================================
### PHASE 4: Production Readiness
### ==========================================================

### Task 020: Generate Production Readiness Report
- [ ] CREATE: `tests/quality/results/production_readiness_report.json` with:
  - Total scenarios: 47
  - Scenarios passed: ___
  - Average quality score: ___
  - Factual accuracy rate: ___
  - No results rate: ___
  - Data completeness rate: ___
  - Context preservation rate: ___
  - Critical failures: ___
  - High failures: ___
  - Medium failures: ___
  - Fix attempts: ___
  - Fixes successful: ___
- [ ] CREATE: Human-readable summary report
- [ ] VERIFY: All hard requirements met

### Task 021: Create Regression Test Suite
- [ ] CREATE: `tests/test_production_regression.py` that runs all scenarios
- [ ] CONFIGURE: CI/CD to run on every PR
- [ ] SET: Failure threshold (any scenario < 80 = PR blocked)
- [ ] VERIFY: Suite runs in < 30 minutes total

### Task 022: Create Monitoring Dashboard Spec
- [ ] DEFINE: Metrics to track in production:
  - Average response quality score
  - No results rate
  - Error rate
  - Tool success rate
  - Response time
- [ ] DEFINE: Alert thresholds
- [ ] DOCUMENT: Monitoring setup guide

### Task 023: Final Validation Run
- [ ] RUN: All 47 scenarios 3 times each
- [ ] VERIFY: All pass all 3 times
- [ ] SIGN-OFF: Mark system as production ready

---

## Scenario Checklist

**Instructions**: Mark each scenario with its actual execution results. Do NOT mark complete without running.

### Multi-Programme Navigation (Phase 1)
| Scenario | Executed | Score | Factual | Failures | Status |
|----------|----------|-------|---------|----------|--------|
| programme_discovery | [ ] | /100 | /100 | | |
| programme_comparison | [ ] | /100 | /100 | | |
| programme_recommendation | [ ] | /100 | /100 | | |
| eligibility_routing | [ ] | /100 | /100 | | |

### Proposal Workflows (Phase 2)
| Scenario | Executed | Score | Factual | Failures | Status |
|----------|----------|-------|---------|----------|--------|
| full_proposal_journey | [ ] | /100 | /100 | | |
| budget_iteration | [ ] | /100 | /100 | | |
| timeline_refinement | [ ] | /100 | /100 | | |
| consortium_building | [ ] | /100 | /100 | | |

### Partner Discovery (Phase 3)
| Scenario | Executed | Score | Factual | Failures | Status |
|----------|----------|-------|---------|----------|--------|
| partner_search_refinement | [ ] | /100 | /100 | | |
| partner_comparison | [ ] | /100 | /100 | | |
| network_exploration | [ ] | /100 | /100 | | |
| organization_deep_dive | [ ] | /100 | /100 | | |

### Personalization (Phase 4)
| Scenario | Executed | Score | Personalization | Failures | Status |
|----------|----------|-------|-----------------|----------|--------|
| user_context_learning | [ ] | /100 | /100 | | |
| returning_user_context | [ ] | /100 | /100 | | |
| progressive_profile | [ ] | /100 | /100 | | |
| preference_filtering | [ ] | /100 | /100 | | |

### Strategic Planning (Phase 5)
| Scenario | Executed | Score | Factual | Failures | Status |
|----------|----------|-------|---------|----------|--------|
| funding_strategy | [ ] | /100 | /100 | | |
| portfolio_planning | [ ] | /100 | /100 | | |
| capacity_building | [ ] | /100 | /100 | | |
| risk_assessment | [ ] | /100 | /100 | | |

### Comparisons (Phase 6)
| Scenario | Executed | Score | Factual | Failures | Status |
|----------|----------|-------|---------|----------|--------|
| funding_type_comparison | [ ] | /100 | /100 | | |
| success_rate_analysis | [ ] | /100 | /100 | | |
| budget_comparison | [ ] | /100 | /100 | | |
| timeline_comparison | [ ] | /100 | /100 | | |

### Deadline Management (Phase 7)
| Scenario | Executed | Score | Data Present | Failures | Status |
|----------|----------|-------|--------------|----------|--------|
| urgent_deadline | [ ] | /100 | YES/NO | | |
| deadline_tracking | [ ] | /100 | YES/NO | | |
| call_opening_alert | [ ] | /100 | YES/NO | | |
| multi_call_timeline | [ ] | /100 | YES/NO | | |

### Complex Eligibility (Phase 8)
| Scenario | Executed | Score | Eligibility | Failures | Status |
|----------|----------|-------|-------------|----------|--------|
| multi_factor_eligibility | [ ] | /100 | /100 | | |
| sme_eligibility | [ ] | /100 | /100 | | |
| consortium_eligibility | [ ] | /100 | /100 | | |
| cross_programme_eligibility | [ ] | /100 | /100 | | |

### Erasmus+ Specific (Phase 9)
| Scenario | Executed | Score | Factual | Failures | Status |
|----------|----------|-------|---------|----------|--------|
| erasmus_action_selection | [ ] | /100 | /100 | | |
| erasmus_budget_calculation | [ ] | /100 | /100 | | |
| erasmus_accreditation | [ ] | /100 | /100 | | |

### Creative Europe Specific (Phase 10)
| Scenario | Executed | Score | Factual | Failures | Status |
|----------|----------|-------|---------|----------|--------|
| creative_europe_strand | [ ] | /100 | /100 | | |
| creative_europe_eligibility | [ ] | /100 | /100 | | |
| creative_europe_cooperation | [ ] | /100 | /100 | | |

### Error Handling (Phase 11)
| Scenario | Executed | Score | Graceful | Failures | Status |
|----------|----------|-------|----------|----------|--------|
| conflicting_requirements | [ ] | /100 | YES/NO | | |
| outdated_information | [ ] | /100 | YES/NO | | |
| ambiguous_programme | [ ] | /100 | YES/NO | | |
| out_of_scope | [ ] | /100 | YES/NO | | |

---

## Fix Cycle Protocol

### When a Scenario Fails:

1. **Identify Failure Category**
   ```
   NO RESULTS → Check tool implementation, data availability
   INCORRECT DATA → Check knowledge base, prompts, fact sources
   MISSING DATA → Check response formatting, tool outputs
   UNEXPECTED BEHAVIOR → Check memory, context, tool routing
   POOR QUALITY → Check prompts, formatting, examples
   ```

2. **Document the Failure**
   - Scenario name
   - Turn number
   - Query text
   - Response text
   - Expected vs Actual
   - Failure category
   - Severity (CRITICAL/HIGH/MEDIUM)

3. **Implement Fix**
   - Create branch: `fix/scenario-name-issue`
   - Make minimal targeted fix
   - Add regression test if applicable

4. **Re-test**
   - Run ONLY the failing scenario first
   - If pass, run related scenarios
   - If pass, run full suite

5. **Document Resolution**
   - Before score
   - After score
   - Fix description
   - Files changed

### Maximum Fix Attempts
- CRITICAL failures: 5 attempts, then escalate
- HIGH failures: 3 attempts, then escalate
- MEDIUM failures: 2 attempts, then accept or deprioritize

---

## Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| Week 1 | Infrastructure + Execution | Tasks 001-014 complete, all scenarios run once |
| Week 2 | Fixes + Validation | Tasks 015-019 complete, all fixes applied |
| Week 2 | Production Readiness | Tasks 020-023 complete, sign-off |

---

## Appendix: Failure Pattern Dictionary

### No Results Patterns
```python
NO_RESULTS_PATTERNS = [
    "I don't have",
    "I cannot find",
    "no information available",
    "I'm not able to",
    "I don't see any",
    "no results found",
    "unable to find",
    "no data available",
    "I couldn't find",
    "there are no",
]
```

### Deflection Patterns
```python
DEFLECTION_PATTERNS = [
    "you might want to",
    "I suggest checking",
    "please visit",
    "for more information",
    "I recommend contacting",
    "you should consult",
]
```

### Required Data Fields by Query Type
```python
REQUIRED_FIELDS = {
    "call_search": ["call_id", "title", "deadline", "budget"],
    "project_search": ["project_id", "acronym", "budget", "coordinator"],
    "partner_search": ["organization_name", "country", "project_count"],
    "eligibility_query": ["eligible", "requirements", "exceptions"],
    "budget_calculation": ["total_budget", "breakdown", "funding_rate"],
    "timeline_generation": ["work_packages", "milestones", "duration"],
}
```

### Factual Accuracy Checks
```python
KNOWN_FACTS = {
    "horizon_europe": {
        "budget": (95_000_000_000, 96_000_000_000),  # €95.5B range
        "duration": "2021-2027",
        "pillars": 3,
        "clusters": 6,
    },
    "erasmus_plus": {
        "budget": (26_000_000_000, 27_000_000_000),  # €26.2B range
        "duration": "2021-2027",
        "key_actions": ["KA1", "KA2", "KA3", "Jean Monnet", "Sport"],
    },
    "creative_europe": {
        "budget": (2_400_000_000, 2_500_000_000),  # €2.44B range
        "duration": "2021-2027",
        "strands": ["CULTURE", "MEDIA", "CROSS-SECTORAL"],
    },
}
```

---

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| QA Lead | | | |
| Dev Lead | | | |
| Product Owner | | | |

**Production Readiness Confirmed**: [ ] YES / [ ] NO

**Remaining Issues**: ___

**Go/No-Go Decision**: ___
