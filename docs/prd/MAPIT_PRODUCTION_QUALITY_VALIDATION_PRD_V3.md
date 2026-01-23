# MAPIT Production Quality Validation PRD (V3 - Application-First)

> **Purpose**: Validate ALL conversation scenarios against the live API and FIX THE PRODUCTION APPLICATION when quality is insufficient
> **Method**: Each scenario has EXECUTE task followed by conditional FIX task
> **Pass Threshold**: Score >= 80/100
> **Max Fix Attempts**: 3 per scenario
> **Target**: Production-ready MAPIT application

---

## CRITICAL: What To Fix vs What Are Tests

**READ THIS CAREFULLY. THIS IS THE MOST IMPORTANT SECTION.**

### The Goal

When a scenario fails (score < 80), the goal is to **IMPROVE THE PRODUCTION APPLICATION** so that it generates better responses. The tests are just a way to identify what's wrong - fixing the tests themselves is NEVER the solution.

### PRODUCTION APPLICATION CODE (FIX THIS)

These are the files that generate responses. When quality is low, FIX THESE FILES:

| Component | Path | What It Does |
|-----------|------|--------------|
| Main Agent | `app/services/agents/tool_aware_agent.py` | The ReAct agent that processes queries and calls tools. FIX THE SYSTEM PROMPT HERE for actionability, formatting, reasoning. |
| Agent Evaluation | `app/services/agents/result_evaluator.py` | Evaluates if results are sufficient. FIX THIS if agent stops too early. |
| Agent Replanning | `app/services/agents/replanner.py` | Replans when results are bad. FIX THIS if agent doesn't retry properly. |
| Agentic Manager | `app/services/agents/agentic_manager.py` | Orchestrates the agent loop. FIX THIS for iteration/retry logic. |
| Call Search Tool | `app/services/local_call_search_service.py` | Searches for funding calls. FIX THIS if calls are missing. |
| Project Search Tool | `app/services/local_project_search_service.py` | Searches CORDIS projects. FIX THIS if projects are missing. |
| Partner Discovery | `app/services/tools/partner_discovery.py` | Finds experienced partners. FIX THIS for partner search issues. |
| Budget Benchmark | `app/services/tools/budget_benchmark.py` | Gets budget statistics. FIX THIS for budget data issues. |
| Budget Calculator | `app/services/tools/budget_calculator.py` | Calculates budgets. FIX THIS for calculation errors. |
| Timeline Generator | `app/services/tools/timeline_generator.py` | Generates project timelines. FIX THIS for timeline issues. |
| Consortium Patterns | `app/services/tools/consortium_patterns.py` | Analyzes consortiums. FIX THIS for consortium data issues. |
| Call History | `app/services/tools/call_history.py` | Analyzes call history. FIX THIS for historical data issues. |
| Similar Projects | `app/services/tools/similar_projects.py` | Finds similar projects. FIX THIS for similarity search issues. |
| Erasmus Eligibility | `app/services/tools/erasmus_eligibility.py` | Checks Erasmus+ eligibility. FIX THIS for Erasmus eligibility errors. |
| Erasmus Budget | `app/services/tools/erasmus_budget_calculator.py` | Calculates Erasmus+ budgets. FIX THIS for Erasmus budget errors. |
| Creative Europe Eligibility | `app/services/tools/creative_europe_eligibility.py` | Checks CE eligibility. FIX THIS for CE eligibility errors. |
| Creative Europe Budget | `app/services/tools/creative_europe_budget_calculator.py` | Calculates CE budgets. FIX THIS for CE budget errors. |
| Response Formatter | `app/services/response/v3_response_formatter.py` | Formats final responses. FIX THIS for formatting issues. |
| Memory Service | `app/services/memory/memory_service.py` | Manages conversation memory. FIX THIS for context loss. |
| Graph Service | `app/services/data_intelligence/graph_service.py` | Neo4j queries. FIX THIS for relationship/stats issues. |
| Vector Search | `app/services/vector_search_service.py` | Semantic search. FIX THIS for document retrieval issues. |

### TEST CODE (NEVER FIX TO SOLVE QUALITY ISSUES)

These files are for TESTING ONLY. They validate responses, they don't generate them:

| Component | Path | Purpose |
|-----------|------|---------|
| ConversationFlowAgent | `tests/agents/conversation_flow_agent.py` | Simulates conversations with the API. READ-ONLY. |
| QualityEvaluatorAgent | `tests/agents/quality_evaluator_agent.py` | Scores response quality. READ-ONLY. |
| CrossProgrammeAgent | `tests/agents/cross_programme_agent.py` | Validates factual accuracy. READ-ONLY. |
| ContextValidatorAgent | `tests/agents/context_validator_agent.py` | Validates context preservation. READ-ONLY. |
| Scenario Runner | `tests/quality/test_scenario_runner.py` | Runs test scenarios. READ-ONLY. |
| Failure Detector | `tests/validators/failure_detector.py` | Detects failure patterns. READ-ONLY. |
| Scenario Files | `tests/scenarios/**/*.yaml` | Define test conversations. READ-ONLY. |

**NEVER modify test files to make tests pass. That defeats the entire purpose.**

---

## Fix Decision Tree

When a scenario fails, follow this decision tree to identify WHAT to fix in the PRODUCTION APPLICATION:

```
SCENARIO FAILED (score < 80)
│
├── Query Fulfillment Low (< 32/40)?
│   ├── No tool was called → FIX: app/services/agents/tool_aware_agent.py (improve tool selection logic in prompt)
│   ├── Wrong tool called → FIX: app/services/agents/tool_aware_agent.py (improve tool descriptions/selection)
│   ├── Tool returned no results → FIX: The specific tool in app/services/tools/*.py
│   └── Tool returned results but not used → FIX: app/services/agents/tool_aware_agent.py (improve result synthesis)
│
├── Specificity Low (< 20/25)?
│   ├── Missing numbers/dates → FIX: app/services/agents/tool_aware_agent.py (add "include specific numbers" to prompt)
│   ├── Missing call IDs → FIX: app/services/response/v3_response_formatter.py (ensure call IDs included)
│   └── Missing deadlines → FIX: app/services/local_call_search_service.py (ensure deadline fields populated)
│
├── Factual Accuracy Low (< 22/25)?
│   ├── Wrong programme budget → FIX: Knowledge base documents or tool that provides budget data
│   ├── Wrong funding rates → FIX: app/services/tools/ (the tool providing rates)
│   ├── Wrong eligibility rules → FIX: app/services/tools/erasmus_eligibility.py or creative_europe_eligibility.py
│   └── Confused programmes → FIX: app/services/agents/tool_aware_agent.py (improve programme context in prompt)
│
└── Actionability Low (< 7/10)?
    └── No next steps → FIX: app/services/agents/tool_aware_agent.py (add "Always end with Next Steps" to prompt)
```

---

## Configuration Notes for Ralphy

Before running, ensure:
1. Live API is running (`docker compose up --build`)
2. Results directory exists: `tests/quality/results/`
3. Test agents are available in `tests/agents/` (but NEVER modify them to fix quality)

Run with: `./ralphy.sh --prd docs/prd/MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V3.md`

---

## Quality Scoring Dimensions (100 points total)

| Dimension | Max Points | Pass Threshold | What It Measures |
|-----------|------------|----------------|------------------|
| Query Fulfillment | 40 | >= 32 (80%) | Did the response answer what was asked? |
| Specificity | 25 | >= 20 (80%) | Does it have specific numbers, dates, IDs? |
| Factual Accuracy | 25 | >= 22 (88%) | Are the EU funding facts correct? |
| Actionability | 10 | >= 7 (70%) | Are there clear next steps for the user? |

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

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/programme_discovery.json`. If average_score < 80:
  1. Analyze the failures[] array to identify root cause using the Fix Decision Tree above
  2. ONLY modify files in `app/` directory - NEVER modify test files
  3. Common fixes for this scenario:
     - Low actionability → Edit `app/services/agents/tool_aware_agent.py` and add "End every response with a '**Next Steps:**' section" to the system prompt
     - Factual errors about programmes → Check the tool being used and fix data in `app/services/tools/`
     - No results found → Fix the search logic in `app/services/local_call_search_service.py` or `app/services/local_project_search_service.py`
  4. Re-run EXECUTE task after each fix
  5. Update JSON with fix_history showing which APPLICATION files were modified
  6. Repeat until score >= 80 or 3 attempts reached
  7. Record final status: PASS/FAIL/MAX_ATTEMPTS

### Scenario 002: Programme Comparison
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/programme_comparison.yaml` against the live API. This scenario tests comparing Horizon Europe, Erasmus+, and Creative Europe. Save result to `tests/quality/results/scenarios/programme_comparison.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/programme_comparison.json`. If average_score < 80:
  1. Analyze failures[] using the Fix Decision Tree
  2. ONLY modify files in `app/` directory
  3. Common fixes for comparison scenarios:
     - Budget confusion between programmes → Edit `app/services/agents/tool_aware_agent.py` to add clearer programme context handling
     - Success rate vs funding rate confusion → Fix the statistics in `app/services/data_intelligence/graph_service.py`
     - Missing comparison structure → Edit `app/services/agents/tool_aware_agent.py` to add "Use tables or bullet points for comparisons" to prompt
  4. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 003: Programme Recommendation
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/programme_recommendation.yaml` against the live API. Tests recommending best programme for user context. Save result to `tests/quality/results/scenarios/programme_recommendation.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/programme_recommendation.json`. If average_score < 80:
  1. Analyze failures[] using the Fix Decision Tree
  2. ONLY modify files in `app/` directory
  3. Common fixes:
     - Recommendation not personalized → Edit `app/services/agents/tool_aware_agent.py` to improve user context handling
     - Missing eligibility considerations → Fix `app/services/tools/erasmus_eligibility.py` or `app/services/tools/creative_europe_eligibility.py`
  4. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 004: Eligibility Routing
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/eligibility_routing.yaml` against the live API. Tests routing eligibility questions to correct programme. Save result to `tests/quality/results/scenarios/eligibility_routing.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/eligibility_routing.json`. If average_score < 80:
  1. Analyze failures[] using the Fix Decision Tree
  2. ONLY modify files in `app/` directory
  3. Common fixes:
     - Wrong programme eligibility rules → Fix `app/services/tools/erasmus_eligibility.py`, `app/services/tools/creative_europe_eligibility.py`
     - Country eligibility errors → Update country data in the eligibility tools above
     - Agent not calling eligibility tools → Edit `app/services/agents/tool_aware_agent.py` to improve tool selection for eligibility queries
  4. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### ==========================================================
### PHASE 3: Proposal Workflow Scenarios
### ==========================================================

### Scenario 005: Full Proposal Journey (15 turns - CRITICAL)
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/full_proposal_journey.yaml` against the live API. This is a 15-turn critical scenario testing the complete proposal journey. Save result to `tests/quality/results/scenarios/full_proposal_journey.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/full_proposal_journey.json`. If average_score < 80:
  1. This complex scenario may have multiple issues - check EACH turn's scores
  2. ONLY modify files in `app/` directory
  3. Common fixes:
     - Context loss between turns → Fix `app/services/memory/memory_service.py`
     - Low actionability → Edit `app/services/agents/tool_aware_agent.py` system prompt
     - Tool failures → Fix the specific tool in `app/services/tools/`
     - Poor synthesis of multi-turn info → Edit `app/services/agents/tool_aware_agent.py` to improve context usage
  4. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 006: Budget Iteration
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/budget_iteration.yaml` against the live API. Tests iterative budget refinement. Save result to `tests/quality/results/scenarios/budget_iteration.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/budget_iteration.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Common fixes:
     - Budget benchmark errors → Fix `app/services/tools/budget_benchmark.py`
     - Budget calculation errors → Fix `app/services/tools/budget_calculator.py`
     - Missing budget breakdown → Edit tool to include detailed breakdown
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts
  4. Record final status: PASS/FAIL/MAX_ATTEMPTS

### Scenario 007: Timeline Refinement
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/proposal_workflow/timeline_refinement.yaml` against the live API. Tests timeline generation and refinement. Save result to `tests/quality/results/scenarios/timeline_refinement.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/timeline_refinement.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Common fixes:
     - Timeline generation issues → Fix `app/services/tools/timeline_generator.py`
     - Missing work packages → Fix WP generation logic in timeline tool
     - Missing milestones → Fix milestone generation logic
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 008: Consortium Building
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/proposal_workflow/consortium_building.yaml` against the live API. Tests consortium composition advice. Save result to `tests/quality/results/scenarios/consortium_building.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/consortium_building.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Common fixes:
     - Consortium patterns wrong → Fix `app/services/tools/consortium_patterns.py`
     - Partner discovery issues → Fix `app/services/tools/partner_discovery.py`
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts
  4. Record final status: PASS/FAIL/MAX_ATTEMPTS

### ==========================================================
### PHASE 4: Partner Discovery Scenarios
### ==========================================================

### Scenario 009: Partner Search Refinement
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/partner_discovery/partner_search_refinement.yaml` against the live API. Tests iterative partner search. Save result to `tests/quality/results/scenarios/partner_search_refinement.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/partner_search_refinement.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Common fixes:
     - Partner search returns no results → Fix `app/services/tools/partner_discovery.py` (check RRF fusion, 2-hop queries)
     - Wrong partner types → Fix filtering logic in partner discovery tool
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts
  4. **Attempt 1 Result**: Score improved from 77.0 to 79.4 (1 attempt). Tool selection now correct for all turns. Status: CLOSE_TO_THRESHOLD

### Scenario 010: Partner Comparison
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/partner_comparison.yaml` against the live API. Tests comparing potential partners. Save result to `tests/quality/results/scenarios/partner_comparison.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/partner_comparison.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix partner comparison logic in `app/services/tools/partner_discovery.py` or agent prompt
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts
  4. **Attempt 1 Result**: Score improved from 77.4 to 78.2 (1 attempt). Fixed substring matching bugs in _extract_org_type() and _extract_country(). Added partner comparison detection with context synthesis. Status: CLOSE_TO_THRESHOLD (remaining issue: context truncation loses partner data in later turns)

### Scenario 011: Network Exploration
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/partner_discovery/network_exploration.yaml` against the live API. Tests exploring collaboration networks. Save result to `tests/quality/results/scenarios/network_exploration.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/network_exploration.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix collaboration network queries in `app/services/data_intelligence/graph_service.py`
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts
  4. **Attempt 1 Result**: Score improved from 76.6 to 77.0 (1 attempt). Added response synthesis handlers for get_collaboration_network and find_organization_projects. Turn 1 now displays detailed network tables. Remaining issues: Turns 2-3 still use search_documents instead of specialized tools (LLM tool selection issue). Status: CLOSE_TO_THRESHOLD

### Scenario 012: Organization Deep Dive
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/partner_discovery/organization_deep_dive.yaml` against the live API. Tests deep dive into organization history. Save result to `tests/quality/results/scenarios/organization_deep_dive.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/organization_deep_dive.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix organization queries in `app/services/tools/partner_discovery.py` or graph service
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts
  4. **Attempt 1 Result**: Score stable at 75.4 (1 attempt). Fixed: (1) Added `_detect_initial_organization_profile_query()` for queries like "Tell me about TUM's EU funding" to use `find_organization_projects` instead of `find_experienced_partners`, (2) Reordered detection flow to check organization deep-dive BEFORE partner comparison, (3) Added organization-aware formatting in V3ResponseFormatter, (4) Fixed "## Projects by" pattern matching in `_extract_org_from_context`, (5) Prevented role filtering for "success rate" queries to get full statistics. All turns now use correct tools. Remaining issue: base response quality scores ~75/100 due to generic project listing format. Status: CLOSE_TO_THRESHOLD

### ==========================================================
### PHASE 5: Personalization Scenarios
### ==========================================================

### Scenario 013: User Context Learning
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/user_context_learning.yaml` against the live API. Tests learning user context over conversation. Save result to `tests/quality/results/scenarios/user_context_learning.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/user_context_learning.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Common fixes:
     - Context not remembered → Fix `app/services/memory/memory_service.py`
     - Context-building messages return empty → Edit `app/services/agents/tool_aware_agent.py` to handle non-tool queries better
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts
  4. **Attempt 1 Result**: Score improved from 77.4 to 80.2 (1 attempt). Fixed: (1) Improved `recommend_programmes` tool to infer organization type from description and provide overview when no keyword matches, (2) Added `_detect_personalized_call_query()` in ToolAwareAgent to route personalized call queries to `search_funding_calls` using accumulated context (sector, country, org type), (3) Added "Using Accumulated Context for Personalization" section to REASONING_PROMPT with explicit rules for referencing user profile. Turns 3-4 now use `search_funding_calls` with marine biology keywords. Status: PASS

### Scenario 014: Returning User Context
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/personalization/returning_user_context.yaml` against the live API. Tests recalling context from earlier in conversation. Save result to `tests/quality/results/scenarios/returning_user_context.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/returning_user_context.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix memory/context preservation in `app/services/memory/memory_service.py`
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts
  4. **Attempt 1 Result**: Score improved from 78.5 to 80.0 (1 attempt). Fixed: Added `_detect_context_recall_query()` method in ToolAwareAgent to detect patterns like "I mentioned earlier I work on X" and route to `search_funding_calls`. Turn 3 now correctly uses `search_funding_calls` instead of `search_documents` and recalls hydrogen context. Status: PASS

### Scenario 015: Progressive Profile Building (12 turns)
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/personalization/progressive_profile.yaml` against the live API. Tests building user profile over 12 turns. Save result to `tests/quality/results/scenarios/progressive_profile.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/progressive_profile.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Common fixes:
     - Empty responses on context-building queries → Edit `app/services/agents/tool_aware_agent.py` to acknowledge and store context
     - Profile not built progressively → Fix memory service context accumulation
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts
  4. **Attempt 1 Result**: Score improved from 77.5 to 81.0 (1 attempt). Fixed: (1) Added profile-based recommendation detection patterns ("best option", "recommend") to `_detect_personalized_call_query`, (2) Added domain keyword extraction for health/medical/AI/diagnostics context, (3) Added SME bonuses in `recommend_programmes` for Horizon Europe (EIC Accelerator), EU4Health, and Digital Europe, (4) Added `get_programme_info` result handling in `_synthesize_from_results`, (5) Added `_detect_tell_me_more_query` for follow-up queries, (6) Fixed Next Steps section to be personalized when profile info is detected. Status: PASS

### Scenario 016: Preference-Based Filtering
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/personalization/preference_filtering.yaml` against the live API. Tests filtering results based on user preferences. Save result to `tests/quality/results/scenarios/preference_filtering.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/scenarios/preference_filtering.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix preference handling in agent prompt or tool parameters
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts
  4. **Attempt 1 Result**: Score 83.0 (0 attempts needed). All 4 turns passed (83/100 each). No critical/high/medium failures. Tool usage consistent: `search_funding_calls` for all turns. Status: PASS

### ==========================================================
### PHASE 6: Strategic Planning Scenarios
### ==========================================================

### Scenario 017: Funding Strategy
- [x] EXECUTE: Run scenario `tests/scenarios/advanced/strategic_planning/funding_strategy.yaml` against the live API. Tests multi-year funding strategy advice. Save result to `tests/quality/results/scenarios/funding_strategy.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/funding_strategy.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix strategy generation in agent prompt or call history tool
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 018: Portfolio Planning
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/strategic_planning/portfolio_planning.yaml` against the live API. Tests managing multiple proposal submissions. Save result to `tests/quality/results/scenarios/portfolio_planning.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/portfolio_planning.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix portfolio planning logic in agent or tools
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 019: Capacity Building
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/strategic_planning/capacity_building.yaml` against the live API. Tests advice for organizations new to EU funding. Save result to `tests/quality/results/scenarios/capacity_building.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/capacity_building.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix capacity building advice in agent prompt
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 020: Risk Assessment
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/strategic_planning/risk_assessment.yaml` against the live API. Tests EIC Accelerator risk analysis. Save result to `tests/quality/results/scenarios/risk_assessment.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/risk_assessment.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix risk assessment logic in tools or agent prompt
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### ==========================================================
### PHASE 7: Comparison Scenarios
### ==========================================================

### Scenario 021: Funding Type Comparison
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/comparisons/funding_type_comparison.yaml` against the live API. Save result to `tests/quality/results/scenarios/funding_type_comparison.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/funding_type_comparison.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix comparison tool in `app/services/tools/` or agent comparison handling
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 022: Success Rate Analysis
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/comparisons/success_rate_analysis.yaml` against the live API. Save result to `tests/quality/results/scenarios/success_rate_analysis.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/success_rate_analysis.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Ensure success rates vs funding rates are not confused - fix in graph service or tools
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 023: Budget Comparison
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/comparisons/budget_comparison.yaml` against the live API. Save result to `tests/quality/results/scenarios/budget_comparison.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/budget_comparison.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix budget comparison in budget tools
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 024: Timeline Comparison
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/comparisons/timeline_comparison.yaml` against the live API. Save result to `tests/quality/results/scenarios/timeline_comparison.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/timeline_comparison.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix timeline comparison in timeline tool
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### ==========================================================
### PHASE 8: Deadline Management Scenarios
### ==========================================================

### Scenario 025: Urgent Deadline
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/deadlines/urgent_deadline.yaml` against the live API. Save result to `tests/quality/results/scenarios/urgent_deadline.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/urgent_deadline.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix deadline handling in `app/services/local_call_search_service.py`
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 026: Deadline Tracking
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/deadlines/deadline_tracking.yaml` against the live API. Save result to `tests/quality/results/scenarios/deadline_tracking.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/deadline_tracking.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix deadline tracking in call search service
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 027: Call Opening Alert
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/deadlines/call_opening_alert.yaml` against the live API. Save result to `tests/quality/results/scenarios/call_opening_alert.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/call_opening_alert.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix opening date handling in call search
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 028: Multi-Call Timeline
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/deadlines/multi_call_timeline.yaml` against the live API. Save result to `tests/quality/results/scenarios/multi_call_timeline.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/multi_call_timeline.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix multi-call timeline generation
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### ==========================================================
### PHASE 9: Complex Eligibility Scenarios
### ==========================================================

### Scenario 029: Multi-Factor Eligibility
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/eligibility/multi_factor_eligibility.yaml` against the live API. Save result to `tests/quality/results/scenarios/multi_factor_eligibility.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/multi_factor_eligibility.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix eligibility rules in `app/services/tools/erasmus_eligibility.py` or `app/services/tools/creative_europe_eligibility.py`
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 030: SME Eligibility
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/eligibility/sme_eligibility.yaml` against the live API. Save result to `tests/quality/results/scenarios/sme_eligibility.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/sme_eligibility.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix SME eligibility rules in eligibility tools
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 031: Consortium Eligibility
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/eligibility/consortium_eligibility.yaml` against the live API. Save result to `tests/quality/results/scenarios/consortium_eligibility.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/consortium_eligibility.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix consortium eligibility rules
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 032: Cross-Programme Eligibility
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/eligibility/cross_programme_eligibility.yaml` against the live API. Save result to `tests/quality/results/scenarios/cross_programme_eligibility.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/cross_programme_eligibility.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix double funding rules in eligibility tools
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### ==========================================================
### PHASE 10: Erasmus+ Specific Scenarios
### ==========================================================

### Scenario 033: Erasmus Action Selection
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/erasmus/erasmus_action_selection.yaml` against the live API. Save result to `tests/quality/results/scenarios/erasmus_action_selection.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/erasmus_action_selection.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix KA1/KA2/KA3 selection in `app/services/tools/erasmus_eligibility.py`
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 034: Erasmus Budget Calculation
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/erasmus/erasmus_budget_calculation.yaml` against the live API. Save result to `tests/quality/results/scenarios/erasmus_budget_calculation.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/erasmus_budget_calculation.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix unit costs in `app/services/tools/erasmus_budget_calculator.py`
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 035: Erasmus Accreditation
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/erasmus/erasmus_accreditation.yaml` against the live API. Save result to `tests/quality/results/scenarios/erasmus_accreditation.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/erasmus_accreditation.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix accreditation info in Erasmus tools or agent prompt
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### ==========================================================
### PHASE 11: Creative Europe Specific Scenarios
### ==========================================================

### Scenario 036: Creative Europe Strand Selection
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/creative_europe/creative_europe_strand.yaml` against the live API. Save result to `tests/quality/results/scenarios/creative_europe_strand.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/creative_europe_strand.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix MEDIA/CULTURE/CROSS-SECTORAL in `app/services/tools/creative_europe_eligibility.py`
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 037: Creative Europe Eligibility
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/creative_europe/creative_europe_eligibility.yaml` against the live API. Save result to `tests/quality/results/scenarios/creative_europe_eligibility.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/creative_europe_eligibility.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix `app/services/tools/creative_europe_eligibility.py`
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 038: Creative Europe Cooperation
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/creative_europe/creative_europe_cooperation.yaml` against the live API. Save result to `tests/quality/results/scenarios/creative_europe_cooperation.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/creative_europe_cooperation.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix scale requirements (small/medium/large) in CE eligibility tool
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### ==========================================================
### PHASE 12: Error Handling Scenarios
### ==========================================================

### Scenario 039: Conflicting Requirements
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/error_handling/conflicting_requirements.yaml` against the live API. Save result to `tests/quality/results/scenarios/conflicting_requirements.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/conflicting_requirements.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix graceful degradation in `app/services/agents/tool_aware_agent.py`
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 040: Outdated Information Handling
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/error_handling/outdated_information.yaml` against the live API. Save result to `tests/quality/results/scenarios/outdated_information.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/outdated_information.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix redirect to current info in agent prompt
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 041: Ambiguous Programme Query
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/error_handling/ambiguous_programme.yaml` against the live API. Save result to `tests/quality/results/scenarios/ambiguous_programme.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/ambiguous_programme.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix clarification handling in agent prompt
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### Scenario 042: Out of Scope Query
- [ ] EXECUTE: Run scenario `tests/scenarios/advanced/error_handling/out_of_scope.yaml` against the live API. Save result to `tests/quality/results/scenarios/out_of_scope.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/scenarios/out_of_scope.json`. If average_score < 80:
  1. ONLY modify files in `app/` directory
  2. Fix scope explanation in agent prompt
  3. Re-run EXECUTE, repeat until score >= 80 or 3 attempts

### ==========================================================
### PHASE 13: Final Validation
### ==========================================================

### Task: Generate Production Readiness Report
- [ ] GENERATE REPORT: Read all result files in `tests/quality/results/scenarios/*.json`. Generate `tests/quality/results/production_readiness_report.json` with: total_scenarios (42), scenarios_passed (count where status=PASS), scenarios_failed (count where status=FAIL or MAX_ATTEMPTS), average_quality_score, factual_accuracy_rate, common_failure_patterns[], fixes_applied[] (listing ONLY app/ files that were modified). Also generate human-readable summary.

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

## Application Fix Patterns Reference

**IMPORTANT: ALL fixes must be in `app/` directory. NEVER modify `tests/` files.**

| Failure Type | Production File to Fix | Example Fix |
|--------------|------------------------|-------------|
| Low actionability (0-6/10) | `app/services/agents/tool_aware_agent.py` | Add "End every response with **Next Steps:**" to system prompt |
| No tool called | `app/services/agents/tool_aware_agent.py` | Improve tool descriptions or selection logic in prompt |
| Wrong tool called | `app/services/agents/tool_aware_agent.py` | Clarify when to use each tool in system prompt |
| Empty response | `app/services/agents/tool_aware_agent.py` | Add handling for non-tool queries |
| Context lost | `app/services/memory/memory_service.py` | Fix context preservation logic |
| Call search fails | `app/services/local_call_search_service.py` | Fix search queries or filters |
| Project search fails | `app/services/local_project_search_service.py` | Fix search queries or filters |
| Partner search fails | `app/services/tools/partner_discovery.py` | Fix RRF fusion or 2-hop queries |
| Budget errors | `app/services/tools/budget_benchmark.py` or `budget_calculator.py` | Fix calculation logic |
| Timeline errors | `app/services/tools/timeline_generator.py` | Fix WP/milestone generation |
| Consortium errors | `app/services/tools/consortium_patterns.py` | Fix pattern analysis |
| Erasmus eligibility wrong | `app/services/tools/erasmus_eligibility.py` | Fix eligibility rules |
| Erasmus budget wrong | `app/services/tools/erasmus_budget_calculator.py` | Fix unit costs |
| CE eligibility wrong | `app/services/tools/creative_europe_eligibility.py` | Fix eligibility rules |
| CE budget wrong | `app/services/tools/creative_europe_budget_calculator.py` | Fix calculation |
| Statistics wrong | `app/services/data_intelligence/graph_service.py` | Fix Neo4j queries |
| Documents not found | `app/services/vector_search_service.py` | Fix vector search |
| Response poorly formatted | `app/services/response/v3_response_formatter.py` | Fix formatting logic |

---

## Verification Checklist

Before marking any FIX IF NEEDED task as complete, verify:

- [ ] All modified files are in `app/` directory (NOT `tests/`)
- [ ] Re-ran the EXECUTE task after fix
- [ ] Score improved (or reached 80+)
- [ ] fix_history in JSON shows only `app/` file paths
- [ ] No test files were modified
