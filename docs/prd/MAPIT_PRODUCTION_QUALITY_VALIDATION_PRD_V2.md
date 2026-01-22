# MAPIT Production Quality Validation PRD (V2 - Ralphy Compatible)

> **Purpose**: Validate ALL conversation scenarios against the live API with comprehensive quality checks
> **Method**: Each scenario has EXECUTE task followed by conditional FIX task
> **Pass Threshold**: Score >= 80/100
> **Max Fix Attempts**: 3 per scenario
> **Target**: Production-ready system

---

## Configuration Notes for Ralphy

Before running, ensure:
1. Live API is running (`docker compose up --build`)
2. Results directory exists: `tests/quality/results/`
3. Test agents are available in `tests/agents/`

Run with: `./ralphy.sh --prd MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V2.md`

---

## Quality Scoring Dimensions (100 points total)

| Dimension | Max Points | Pass Threshold |
|-----------|------------|----------------|
| Query Fulfillment | 40 | >= 32 (80%) |
| Specificity | 25 | >= 20 (80%) |
| Factual Accuracy | 25 | >= 22 (88%) |
| Actionability | 10 | >= 7 (70%) |

---

## Tasks

### ==========================================================
### PHASE 1: Infrastructure Setup
### ==========================================================

### Task 001: Setup Test Infrastructure
- [x] CREATE test runner: Create `tests/quality/test_scenario_runner.py` if not exists with: ProductionQualityRunner class, ScenarioExecutionResult dataclass, TurnResult dataclass, pattern detection for failure categories. Verify by running `python -c "from tests.quality.test_scenario_runner import ProductionQualityRunner"`.

- [x] CREATE failure detector: Create `tests/validators/failure_detector.py` if not exists with: NoResultsDetector, IncorrectDataDetector, MissingDataDetector classes. Verify by running `pytest tests/validators/ -v -k detector`.

### ==========================================================
### PHASE 2: Multi-Programme Navigation Scenarios
### ==========================================================

### Scenario 001: Programme Discovery
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/programme_discovery.yaml` against the live API using ConversationFlowAgent. For each turn: collect response_text, tools_used, quality_score from QualityEvaluatorAgent, factual_score from CrossProgrammeAgent. Calculate average score. Save full result to `tests/quality/results/scenarios/programme_discovery.json` with structure: {scenario_name, turns[], average_score, factual_score, failures[], status}.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/programme_discovery.json`. If average_score < 80: identify root cause from failures[] (low_actionability → add Next Steps to agent prompt, factual_error → fix CrossProgrammeAgent validation, no_results → fix tool queries). Implement fix, re-run EXECUTE task, update JSON with fix_history. Repeat until score >= 80 or 3 attempts reached. Record final status: PASS/FAIL/MAX_ATTEMPTS.

### Scenario 002: Programme Comparison
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/programme_comparison.yaml` against the live API. This scenario tests comparing Horizon Europe, Erasmus+, and Creative Europe. Save result to `tests/quality/results/scenarios/programme_comparison.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/programme_comparison.json`. If average_score < 80: check for multi-programme budget confusion (CrossProgrammeAgent issue), success rate vs funding rate confusion, missing comparison data. Fix using patterns in `mapit-tools` skill, re-evaluate until passing or 3 attempts.

### Scenario 003: Programme Recommendation
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/programme_recommendation.yaml` against the live API. Tests recommending best programme for user context. Save result to `tests/quality/results/scenarios/programme_recommendation.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/programme_recommendation.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### Scenario 004: Eligibility Routing
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/eligibility_routing.yaml` against the live API. Tests routing eligibility questions to correct programme. Save result to `tests/quality/results/scenarios/eligibility_routing.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/eligibility_routing.json`. If average_score < 80: check eligibility validation in CrossProgrammeAgent, country status in eu-funding-domain. Fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### PHASE 3: Proposal Workflow Scenarios
### ==========================================================

### Scenario 005: Full Proposal Journey (15 turns - CRITICAL)
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/proposal_workflow/full_proposal_journey.yaml` against the live API. This is a 15-turn critical scenario testing the complete proposal journey. Save result to `tests/quality/results/scenarios/full_proposal_journey.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/full_proposal_journey.json`. If average_score < 80: this complex scenario may have multiple issues. Check each turn's scores. Common issues: low actionability (add Next Steps), context loss (fix memory service), tool failures (fix specific tool). Fix and re-evaluate until passing or 3 attempts.

### Scenario 006: Budget Iteration
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/proposal_workflow/budget_iteration.yaml` against the live API. Tests iterative budget refinement. Save result to `tests/quality/results/scenarios/budget_iteration.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/budget_iteration.json`. If average_score < 80: check get_budget_benchmark tool, budget calculation accuracy. Fix and re-evaluate until passing or 3 attempts.

### Scenario 007: Timeline Refinement
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/proposal_workflow/timeline_refinement.yaml` against the live API. Tests timeline generation and refinement. Save result to `tests/quality/results/scenarios/timeline_refinement.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/timeline_refinement.json`. If average_score < 80: check generate_timeline tool, WP structure, milestone generation. Fix and re-evaluate until passing or 3 attempts.

### Scenario 008: Consortium Building
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/proposal_workflow/consortium_building.yaml` against the live API. Tests consortium composition advice. Save result to `tests/quality/results/scenarios/consortium_building.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/consortium_building.json`. If average_score < 80: check get_consortium_patterns tool, find_experienced_partners tool. Fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### PHASE 4: Partner Discovery Scenarios
### ==========================================================

### Scenario 009: Partner Search Refinement
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/partner_discovery/partner_search_refinement.yaml` against the live API. Tests iterative partner search. Save result to `tests/quality/results/scenarios/partner_search_refinement.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/partner_search_refinement.json`. If average_score < 80: check find_experienced_partners tool, RRF fusion logic. Fix and re-evaluate until passing or 3 attempts.

### Scenario 010: Partner Comparison
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/partner_discovery/partner_comparison.yaml` against the live API. Tests comparing potential partners. Save result to `tests/quality/results/scenarios/partner_comparison.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/partner_comparison.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### Scenario 011: Network Exploration
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/partner_discovery/network_exploration.yaml` against the live API. Tests exploring collaboration networks. Save result to `tests/quality/results/scenarios/network_exploration.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/network_exploration.json`. If average_score < 80: check get_collaboration_network tool. Fix and re-evaluate until passing or 3 attempts.

### Scenario 012: Organization Deep Dive
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/partner_discovery/organization_deep_dive.yaml` against the live API. Tests deep dive into organization history. Save result to `tests/quality/results/scenarios/organization_deep_dive.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/organization_deep_dive.json`. If average_score < 80: check find_organization_projects tool. Fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### PHASE 5: Personalization Scenarios
### ==========================================================

### Scenario 013: User Context Learning
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/personalization/user_context_learning.yaml` against the live API. Tests learning user context over conversation. Save result to `tests/quality/results/scenarios/user_context_learning.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/user_context_learning.json`. If average_score < 80: common issues are (1) multi-programme budget confusion - fix CrossProgrammeAgent to use distance-based validation, (2) context-building messages returning empty - add handling in ToolAwareAgent prompt. Fix and re-evaluate until passing or 3 attempts.

### Scenario 014: Returning User Context
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/personalization/returning_user_context.yaml` against the live API. Tests recalling context from earlier in conversation. Save result to `tests/quality/results/scenarios/returning_user_context.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/returning_user_context.json`. If average_score < 80: check memory service, context preservation. Fix and re-evaluate until passing or 3 attempts.

### Scenario 015: Progressive Profile Building (12 turns)
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/personalization/progressive_profile.yaml` against the live API. Tests building user profile over 12 turns. Save result to `tests/quality/results/scenarios/progressive_profile.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/progressive_profile.json`. If average_score < 80: check for empty responses on context-building queries (e.g., "We're in healthcare sector"). Add context-building message handling to ToolAwareAgent if missing. Fix and re-evaluate until passing or 3 attempts.

### Scenario 016: Preference-Based Filtering
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/personalization/preference_filtering.yaml` against the live API. Tests filtering results based on user preferences. Save result to `tests/quality/results/scenarios/preference_filtering.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/preference_filtering.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### PHASE 6: Strategic Planning Scenarios
### ==========================================================

### Scenario 017: Funding Strategy
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/strategic_planning/funding_strategy.yaml` against the live API. Tests multi-year funding strategy advice. Save result to `tests/quality/results/scenarios/funding_strategy.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/funding_strategy.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### Scenario 018: Portfolio Planning
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/strategic_planning/portfolio_planning.yaml` against the live API. Tests managing multiple proposal submissions. Save result to `tests/quality/results/scenarios/portfolio_planning.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/portfolio_planning.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### Scenario 019: Capacity Building
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/strategic_planning/capacity_building.yaml` against the live API. Tests advice for organizations new to EU funding. Save result to `tests/quality/results/scenarios/capacity_building.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/capacity_building.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### Scenario 020: Risk Assessment
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/strategic_planning/risk_assessment.yaml` against the live API. Tests EIC Accelerator risk analysis. Save result to `tests/quality/results/scenarios/risk_assessment.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/risk_assessment.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### PHASE 7: Comparison Scenarios
### ==========================================================

### Scenario 021: Funding Type Comparison
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/comparisons/funding_type_comparison.yaml` against the live API. Save result to `tests/quality/results/scenarios/funding_type_comparison.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/funding_type_comparison.json`. If average_score < 80: check compare_programmes tool. Fix and re-evaluate until passing or 3 attempts.

### Scenario 022: Success Rate Analysis
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/comparisons/success_rate_analysis.yaml` against the live API. Save result to `tests/quality/results/scenarios/success_rate_analysis.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/success_rate_analysis.json`. If average_score < 80: ensure success rates vs funding rates are not confused. Fix and re-evaluate until passing or 3 attempts.

### Scenario 023: Budget Comparison
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/comparisons/budget_comparison.yaml` against the live API. Save result to `tests/quality/results/scenarios/budget_comparison.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/budget_comparison.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### Scenario 024: Timeline Comparison
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/comparisons/timeline_comparison.yaml` against the live API. Save result to `tests/quality/results/scenarios/timeline_comparison.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/timeline_comparison.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### PHASE 8: Deadline Management Scenarios
### ==========================================================

### Scenario 025: Urgent Deadline
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/deadlines/urgent_deadline.yaml` against the live API. Save result to `tests/quality/results/scenarios/urgent_deadline.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/urgent_deadline.json`. If average_score < 80: check deadline info in search_funding_calls results. Fix and re-evaluate until passing or 3 attempts.

### Scenario 026: Deadline Tracking
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/deadlines/deadline_tracking.yaml` against the live API. Save result to `tests/quality/results/scenarios/deadline_tracking.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/deadline_tracking.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### Scenario 027: Call Opening Alert
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/deadlines/call_opening_alert.yaml` against the live API. Save result to `tests/quality/results/scenarios/call_opening_alert.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/call_opening_alert.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### Scenario 028: Multi-Call Timeline
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/deadlines/multi_call_timeline.yaml` against the live API. Save result to `tests/quality/results/scenarios/multi_call_timeline.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/multi_call_timeline.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### PHASE 9: Complex Eligibility Scenarios
### ==========================================================

### Scenario 029: Multi-Factor Eligibility
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/eligibility/multi_factor_eligibility.yaml` against the live API. Save result to `tests/quality/results/scenarios/multi_factor_eligibility.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/multi_factor_eligibility.json`. If average_score < 80: check eligibility rules in CrossProgrammeAgent. Fix and re-evaluate until passing or 3 attempts.

### Scenario 030: SME Eligibility
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/eligibility/sme_eligibility.yaml` against the live API. Save result to `tests/quality/results/scenarios/sme_eligibility.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/sme_eligibility.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### Scenario 031: Consortium Eligibility
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/eligibility/consortium_eligibility.yaml` against the live API. Save result to `tests/quality/results/scenarios/consortium_eligibility.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/consortium_eligibility.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### Scenario 032: Cross-Programme Eligibility
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/eligibility/cross_programme_eligibility.yaml` against the live API. Save result to `tests/quality/results/scenarios/cross_programme_eligibility.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/cross_programme_eligibility.json`. If average_score < 80: check double funding rules. Fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### PHASE 10: Erasmus+ Specific Scenarios
### ==========================================================

### Scenario 033: Erasmus Action Selection
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/erasmus/erasmus_action_selection.yaml` against the live API. Save result to `tests/quality/results/scenarios/erasmus_action_selection.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/erasmus_action_selection.json`. If average_score < 80: check check_erasmus_eligibility tool, KA1/KA2/KA3 accuracy. Fix and re-evaluate until passing or 3 attempts.

### Scenario 034: Erasmus Budget Calculation
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/erasmus/erasmus_budget_calculation.yaml` against the live API. Save result to `tests/quality/results/scenarios/erasmus_budget_calculation.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/erasmus_budget_calculation.json`. If average_score < 80: check calculate_erasmus_budget tool, unit costs. Fix and re-evaluate until passing or 3 attempts.

### Scenario 035: Erasmus Accreditation
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/erasmus/erasmus_accreditation.yaml` against the live API. Save result to `tests/quality/results/scenarios/erasmus_accreditation.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/erasmus_accreditation.json`. If average_score < 80: fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### PHASE 11: Creative Europe Specific Scenarios
### ==========================================================

### Scenario 036: Creative Europe Strand Selection
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/creative_europe/creative_europe_strand.yaml` against the live API. Save result to `tests/quality/results/scenarios/creative_europe_strand.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/creative_europe_strand.json`. If average_score < 80: check MEDIA/CULTURE/CROSS-SECTORAL accuracy. Fix and re-evaluate until passing or 3 attempts.

### Scenario 037: Creative Europe Eligibility
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/creative_europe/creative_europe_eligibility.yaml` against the live API. Save result to `tests/quality/results/scenarios/creative_europe_eligibility.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/creative_europe_eligibility.json`. If average_score < 80: check check_creative_europe_eligibility tool. Fix and re-evaluate until passing or 3 attempts.

### Scenario 038: Creative Europe Cooperation
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/creative_europe/creative_europe_cooperation.yaml` against the live API. Save result to `tests/quality/results/scenarios/creative_europe_cooperation.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/creative_europe_cooperation.json`. If average_score < 80: check scale requirements (small/medium/large). Fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### PHASE 12: Error Handling Scenarios
### ==========================================================

### Scenario 039: Conflicting Requirements
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/error_handling/conflicting_requirements.yaml` against the live API. Save result to `tests/quality/results/scenarios/conflicting_requirements.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/conflicting_requirements.json`. If average_score < 80: check graceful degradation. Fix and re-evaluate until passing or 3 attempts.

### Scenario 040: Outdated Information Handling
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/error_handling/outdated_information.yaml` against the live API. Save result to `tests/quality/results/scenarios/outdated_information.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/outdated_information.json`. If average_score < 80: check redirect to current info. Fix and re-evaluate until passing or 3 attempts.

### Scenario 041: Ambiguous Programme Query
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/error_handling/ambiguous_programme.yaml` against the live API. Save result to `tests/quality/results/scenarios/ambiguous_programme.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/ambiguous_programme.json`. If average_score < 80: check clarification handling. Fix and re-evaluate until passing or 3 attempts.

### Scenario 042: Out of Scope Query
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/error_handling/out_of_scope.yaml` against the live API. Save result to `tests/quality/results/scenarios/out_of_scope.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/out_of_scope.json`. If average_score < 80: check scope explanation. Fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### PHASE 13: Final Validation
### ==========================================================

### Task: Generate Production Readiness Report
- [ ] GENERATE REPORT: Read all result files in `tests/quality/results/scenarios/*.json`. Generate `tests/quality/results/production_readiness_report.json` with: total_scenarios (42), scenarios_passed (count where status=PASS), scenarios_failed (count where status=FAIL or MAX_ATTEMPTS), average_quality_score, factual_accuracy_rate, common_failure_patterns[], fixes_applied[]. Also generate human-readable summary.

### Task: Final Verification Run
- [ ] FINAL VERIFICATION: Run ALL 42 scenarios one more time. All must score >= 80/100. If any fail, mark as production NOT ready with list of failing scenarios.

---

## Summary

| Phase | Scenarios | Focus Area |
|-------|-----------|------------|
| 2 | 001-004 | Multi-Programme Navigation |
| 3 | 005-008 | Proposal Workflows |
| 4 | 009-012 | Partner Discovery |
| 5 | 013-016 | Personalization |
| 6 | 017-020 | Strategic Planning |
| 7 | 021-024 | Comparisons |
| 8 | 025-028 | Deadline Management |
| 9 | 029-032 | Complex Eligibility |
| 10 | 033-035 | Erasmus+ Specific |
| 11 | 036-038 | Creative Europe Specific |
| 12 | 039-042 | Error Handling |
| 13 | Report + Final | Production Readiness |

**Total: 42 scenarios × 2 tasks = 84 tasks + 2 final tasks = 86 tasks**

---

## Fix Patterns Reference

When fixing failures, consult these patterns:

| Failure Type | Where to Fix | Example Fix |
|--------------|--------------|-------------|
| Low actionability (0/10) | `app/services/agents/tool_aware_agent.py` | Add "🎯 Next Steps:" requirement to prompt |
| Multi-programme budget confusion | `tests/agents/cross_programme_agent.py` | Use distance-based programme association |
| Empty response for context-building | `app/services/agents/tool_aware_agent.py` | Add context-building message handling |
| Wrong funding rates | `eu-funding-domain` skill | Update knowledge base |
| Missing call details | `app/services/tools/` | Fix search_funding_calls tool |
| Partner search gaps | `app/services/tools/partner_discovery.py` | Fix RRF fusion, 2-hop queries |
| Eligibility errors | `tests/agents/cross_programme_agent.py` | Update COUNTRY_ELIGIBILITY rules |
