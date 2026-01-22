# MAPIT Advanced Conversation Flows PRD

> **Purpose**: Extend conversation capabilities to handle complex multi-programme queries, proposal workflows, and strategic planning
> **Method**: Scenario-based testing with specialized validation agents
> **Pass Threshold**: All scenarios pass, user goals achieved, quality >= 75/100
> **Target**: Production-ready advanced conversation handling

---

## Problem Statement

While the MAPIT application handles basic queries and maintains conversation stability, users need support for more sophisticated interaction patterns:

1. **Multi-programme navigation** - Users don't know which EU programme fits their needs
2. **Iterative proposal development** - Multi-session proposal refinement workflows
3. **Partner discovery journeys** - Finding, evaluating, and comparing potential partners
4. **Personalized recommendations** - System should learn user context over conversation
5. **Strategic planning** - Long-term funding strategy discussions
6. **Cross-programme comparisons** - Comparing options across different EU programmes
7. **Deadline-aware conversations** - Urgent time-sensitive queries
8. **Complex eligibility chains** - Multi-factor eligibility with dependencies

---

## User Personas & Goals

### Persona 1: Research Manager (Maria)
- **Organization**: University research department
- **Goal**: Find funding for hydrogen research team
- **Needs**: Call search, eligibility check, budget planning, partner finding
- **Pain Points**: Overwhelmed by programme options, unsure of eligibility

### Persona 2: SME Innovation Lead (Stefan)
- **Organization**: Deep-tech startup (15 employees)
- **Goal**: Secure funding for AI healthcare product
- **Needs**: EIC Accelerator guidance, budget calculation, success tips
- **Pain Points**: Limited time, needs quick answers on eligibility and deadlines

### Persona 3: Cultural Organization Director (Elena)
- **Organization**: Film production company
- **Goal**: Fund international co-production project
- **Needs**: Creative Europe MEDIA guidance, partner finding, application tips
- **Pain Points**: Unclear which strand/action fits, needs deadline tracking

### Persona 4: Education Coordinator (Ahmed)
- **Organization**: VET training institute
- **Goal**: Establish international mobility programme
- **Needs**: Erasmus+ KA1 guidance, budget calculation, partner matching
- **Pain Points**: Complex eligibility rules, budget calculation confusion

---

## Test Infrastructure

### Existing Agents (from Conversation Stability PRD)
| Agent | Purpose |
|-------|---------|
| `ConversationFlowAgent` | Simulates multi-turn conversations |
| `ContextValidatorAgent` | Validates DB/Redis consistency |
| `QualityEvaluatorAgent` | Scores responses using LLM-as-judge |

### New Agents Required
| Agent | Purpose |
|-------|---------|
| `GoalTrackingAgent` | Tracks user goal progress across turns |
| `PersonalizationAgent` | Validates context learning and personalization |
| `CrossProgrammeAgent` | Validates multi-programme navigation |

### New Scoring Dimensions
| Dimension | Points | What to Check |
|-----------|--------|---------------|
| Goal Progress | 30 | User advancing toward stated goal |
| Personalization | 20 | Response tailored to user context |
| Completeness | 25 | All relevant options presented |
| Actionability | 25 | Clear next steps with deadlines |

### Validation Type → Agent Mapping
This mapping ensures scenarios use the correct agent for each validation type:

| Validation Type | Agent | Method |
|-----------------|-------|--------|
| `goal_progress` | `GoalTrackingAgent` | `evaluate_progress()` |
| `goal_achieved` | `GoalTrackingAgent` | `check_completion()` |
| `personalization_applied` | `PersonalizationAgent` | `validate_personalization()` |
| `context_accumulated` | `PersonalizationAgent` | `validate_context_accumulation()` |
| `profile_used` | `PersonalizationAgent` | `validate_profile_usage()` |
| `programme_mentioned` | `CrossProgrammeAgent` | `check_programme_mentions()` |
| `programme_accurate` | `CrossProgrammeAgent` | `validate_programme_facts()` |
| `eligibility_correct` | `CrossProgrammeAgent` | `validate_eligibility_rules()` |
| `response_contains` | Built-in | Pattern matching |
| `tools_used` | Built-in | Tool call checking |
| `no_error` | Built-in | Error detection |
| `context_integrity` | `ContextValidatorAgent` | `validate_context_integrity()` |

**IMPORTANT**: Each agent task (002-004) includes a verification step that the test runner can import and call the agent.

---

## Tasks

### SCENARIO TASK PATTERN

All scenario tasks (006-047) must:
1. **Use the correct validation types** that leverage the agents, not just `response_contains`
2. **Include agent-based validations** from this mapping:
   - Multi-programme scenarios → `programme_mentioned`, `programme_accurate` (CrossProgrammeAgent)
   - Eligibility scenarios → `eligibility_correct` (CrossProgrammeAgent)
   - Long conversations → `goal_progress`, `goal_achieved` (GoalTrackingAgent)
   - Context-building scenarios → `context_accumulated`, `profile_used`, `personalization_applied` (PersonalizationAgent)
   - All scenarios → `context_integrity` in final_validations (ContextValidatorAgent)
3. **Specify which agent** handles each validation in comments

Example scenario structure:
```yaml
name: "Example Scenario"
steps:
  - message: "User query"
    validations:
      - type: "programme_mentioned"  # CrossProgrammeAgent
        programmes: ["Horizon Europe"]
      - type: "goal_progress"  # GoalTrackingAgent
        min_progress: 0.2
final_validations:
  - type: "context_integrity"  # ContextValidatorAgent
  - type: "goal_achieved"  # GoalTrackingAgent
    min_progress: 0.8
```

### ==========================================================
### PHASE 0: Test Infrastructure Setup
### ==========================================================

### Task 001: Create Advanced Scenarios Directory
- [x] CREATE DIRECTORY: Create `tests/scenarios/advanced/` directory structure.
- [x] VERIFY: Directory exists and is ready for scenario YAML files.

### Task 002: Create Goal Tracking Agent
- [x] IMPLEMENT: Create `tests/agents/goal_tracking_agent.py` with:
  - Goal extraction from first turn (parse user intent into measurable goal)
  - Progress tracking across turns (0-100% completion estimation)
  - Completion detection (goal achieved / partially achieved / not achieved)
  - Success metrics collection (turns to completion, tools used, context preserved)
  - Integration with existing ConversationFlowAgent.
- [x] TEST: Create `tests/test_goal_tracking_agent.py` with unit tests for:
  - `evaluate_progress(query, response)` → returns 0.0-1.0 progress score
  - `check_completion(conversation)` → returns completion status
  - Agent can be imported and instantiated by test runner.
- [x] VERIFY: Validation types `goal_progress` and `goal_achieved` work in a sample scenario.

### Task 003: Create Personalization Agent
- [x] IMPLEMENT: Create `tests/agents/personalization_agent.py` with:
  - Context accumulation validation (profile fields extracted per turn)
  - Profile building detection (organization type, sector, country, experience level)
  - Personalized recommendation verification (response tailored to profile)
  - Preference application checking (filters applied correctly)
  - Integration with existing ContextValidatorAgent.
- [x] TEST: Create `tests/test_personalization_agent.py` with unit tests for:
  - `validate_personalization(response, profile)` → checks response uses profile
  - `validate_context_accumulation(turns)` → checks profile builds over time
  - `validate_profile_usage(response, expected_fields)` → checks fields used
  - Agent can be imported and instantiated by test runner.
- [x] VERIFY: Validation types `personalization_applied`, `context_accumulated`, `profile_used` work.

### Task 004: Create Cross-Programme Agent
- [x] IMPLEMENT: Create `tests/agents/cross_programme_agent.py` with:
  - Multi-programme mention detection (Horizon Europe, Erasmus+, Creative Europe)
  - Programme switching validation (context preserved across programme changes)
  - Comparison accuracy checking (correct facts for each programme)
  - Eligibility rule verification across programmes
  - Integration with existing QualityEvaluatorAgent.
- [x] TEST: Create `tests/test_cross_programme_agent.py` with unit tests for:
  - `check_programme_mentions(response)` → returns list of programmes mentioned
  - `validate_programme_facts(response, programme)` → checks facts are correct
  - `validate_eligibility_rules(response, context)` → checks eligibility accuracy
  - Agent can be imported and instantiated by test runner.
- [x] VERIFY: Validation types `programme_mentioned`, `programme_accurate`, `eligibility_correct` work.

### Task 005: Create Advanced Scenario Test Runner
- [x] IMPLEMENT: Create `tests/test_advanced_conversation_scenarios.py` with:
  - YAML scenario loader for `tests/scenarios/advanced/` directory
  - Multi-turn conversation execution using ConversationFlowAgent
  - Validation dispatcher that routes validation types to correct agents:
    - `goal_progress`, `goal_achieved` → GoalTrackingAgent
    - `personalization_applied`, `context_accumulated`, `profile_used` → PersonalizationAgent
    - `programme_mentioned`, `programme_accurate`, `eligibility_correct` → CrossProgrammeAgent
    - `context_integrity` → ContextValidatorAgent
    - `response_contains`, `tools_used`, `no_error` → built-in handlers
  - Quality scoring using QualityEvaluatorAgent
  - Result aggregation and reporting.
- [x] TEST: Create `tests/scenarios/advanced/_test_runner_validation.yaml` scenario that uses ALL validation types to verify the runner correctly dispatches to each agent.
- [x] VERIFY: Run the validation scenario and confirm all agents are called correctly.

### ==========================================================
### PHASE 1: Multi-Programme Navigation
### ==========================================================

### Task 006: Programme Discovery Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/advanced/programme_discovery.yaml` with steps:
  1. "I want to fund research on sustainable packaging materials"
  2. "What about if we want to include training for our staff?"
  3. "And what if we're a creative industry company making documentaries about sustainability?"
  Required validation types:
  - `programme_mentioned` (CrossProgrammeAgent): Check Horizon Europe, Erasmus+, Creative Europe mentioned
  - `programme_accurate` (CrossProgrammeAgent): Verify programme facts are correct
  - `goal_progress` (GoalTrackingAgent): Track progress toward finding right programme

- [x] RUN & FIX: Execute scenario. Verify cross-programme navigation works.

### Task 007: Programme Comparison Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/advanced/programme_comparison.yaml` with steps:
  1. "Compare Horizon Europe and Erasmus+ for university research collaboration"
  2. "What about funding amounts?"
  3. "Which has better success rates?"
  4. "Which should I apply to first?"
  Required validation types:
  - `programme_mentioned` (CrossProgrammeAgent): Both programmes discussed
  - `programme_accurate` (CrossProgrammeAgent): Funding amounts and success rates correct
  - `response_contains`: Strategic recommendation present
  - `goal_achieved` (GoalTrackingAgent): User can make informed decision

- [x] RUN & FIX: Execute scenario. Fix any comparison logic issues.

### Task 008: Programme Recommendation Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/advanced/programme_recommendation.yaml` with steps:
  1. "I'm a small museum wanting to digitize our collection and share it across Europe"
  2. "We also want to train our staff on digital skills"
  3. "What's the best strategy?"
  Required validation types:
  - `programme_mentioned` (CrossProgrammeAgent): Creative Europe and Erasmus+ mentioned
  - `programme_accurate` (CrossProgrammeAgent): Correct strands/actions recommended
  - `personalization_applied` (PersonalizationAgent): Recommendation fits museum profile
  - `goal_achieved` (GoalTrackingAgent): Strategy provided with clear reasoning

- [x] RUN & FIX: Execute scenario. Verify recommendation logic.

### Task 009: Eligibility Routing Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/advanced/eligibility_routing.yaml` with steps:
  1. "We're a Swiss company wanting to participate in EU programmes"
  2. "What about Horizon Europe?"
  3. "And Erasmus+?"
  4. "Creative Europe?"
  Required validation types:
  - `eligibility_correct` (CrossProgrammeAgent): Switzerland eligibility accurate per programme
  - `programme_mentioned` (CrossProgrammeAgent): All three programmes addressed
  - `programme_accurate` (CrossProgrammeAgent): Associated Country rules correct
  - `context_accumulated` (PersonalizationAgent): Swiss company context preserved
  - `goal_achieved` (GoalTrackingAgent): User understands eligibility across programmes

- [x] RUN & FIX: Execute scenario. Verify eligibility rules accurate.

### ==========================================================
### PHASE 2: Proposal Development Workflows
### ==========================================================

### Task 010: Full Proposal Journey Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/advanced/full_proposal_journey.yaml` with 15+ steps:
  1. "I want to write a proposal for hydrogen energy storage research"
  2. "What calls are available?"
  3. "Tell me about HORIZON-CL5-2024-D3-01-01"
  4. "What's the success rate?"
  5. "Help me plan the budget for a 4M euro project"
  6. "What partners should I look for?"
  7. "Find organizations experienced in hydrogen storage"
  8. "Generate a timeline for 36 months"
  9. "What work packages should we have?"
  10. "What about deliverables?"
  11. "Remind me of the deadline"
  12. "What are the evaluation criteria?"
  13. "How should we structure the consortium?"
  14. "What's a typical budget breakdown?"
  15. "Summarize our proposal plan"
  Required validation types:
  - `goal_progress` (GoalTrackingAgent): Track progress at each step (should increase)
  - `goal_achieved` (GoalTrackingAgent): Final step achieves proposal plan goal
  - `context_accumulated` (PersonalizationAgent): Context builds across 15 turns
  - `context_integrity` (ContextValidatorAgent): All messages stored correctly
  - `tools_used`: Appropriate tools called (search_funding_calls, calculate_budget, etc.)

- [x] RUN & FIX: Execute long scenario. Track goal progression.

### Task 011: Budget Iteration Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/advanced/budget_iteration.yaml` with steps:
  1. "Calculate budget for a 3-year RIA with 5 partners"
  2. "What if we add 2 more partners?"
  3. "Can we increase personnel costs?"
  4. "Compare with typical projects in this area"
  5. "Adjust to stay within 90th percentile"
  Validations: Budget recalculated each time, comparisons accurate, final budget reasonable.

- [x] RUN & FIX: Execute scenario. Fix budget calculation persistence.

### Task 012: Timeline Refinement Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/advanced/timeline_refinement.yaml` with steps:
  1. "Generate timeline for 48-month health research project"
  2. "Add a clinical trial phase in WP4"
  3. "The ethics approval might delay us - add buffer"
  4. "Show me similar projects' timelines"
  5. "Adjust milestones to match typical patterns"
  Validations: Timeline modified incrementally, clinical trial WP added, realistic durations.

- [x] RUN & FIX: Execute scenario. Fix timeline modification logic.

### Task 013: Consortium Building Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/advanced/consortium_building.yaml` with steps:
  1. "We need partners for an AI in agriculture project"
  2. "Find organizations experienced in precision farming"
  3. "We need an SME partner from Southern Europe"
  4. "Find a research organization from Germany"
  5. "What's a typical consortium size for this topic?"
  6. "Show our proposed consortium"
  Validations: Partners accumulated across turns, consortium composition shown, geographic balance.

- [x] RUN & FIX: Execute scenario. Validate partner accumulation in context.

### ==========================================================
### PHASE 3: Partner Discovery Journeys
### ==========================================================

### Task 014: Partner Search Refinement Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/advanced/partner_search_refinement.yaml` with steps:
  1. "Find partners for quantum computing research"
  2. "Show only universities"
  3. "From EU15 countries only"
  4. "With experience coordinating projects"
  5. "Who have worked on quantum communication"
  Validations: Filters applied incrementally, results narrow down correctly.

- [x] RUN & FIX: Execute scenario. Fix filter accumulation.

### Task 015: Partner Comparison Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/advanced/partner_comparison.yaml` with steps:
  1. "Find experienced partners in renewable energy"
  2. "Compare the top 3 organizations"
  3. "Which has the most EU funding?"
  4. "Which has the most diverse collaboration network?"
  5. "Recommend the best fit for a coordination role"
  Validations: Comparison accurate, recommendation justified with data.

- [x] RUN & FIX: Execute scenario. Fix partner comparison logic.

### Task 016: Network Exploration Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/advanced/network_exploration.yaml` with steps:
  1. "Show me the collaboration network for climate research"
  2. "Who are the most connected organizations?"
  3. "Show projects coordinated by Fraunhofer"
  4. "Who do they typically partner with?"
  5. "Find their partners that work on hydrogen"
  Validations: Network traversal works, relationship chains followed.

- [x] RUN & FIX: Execute scenario. Fix network exploration.

### Task 017: Organization Deep-Dive Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/organization_deep_dive.yaml` with steps:
  1. "Tell me about Technical University of Munich's EU funding history"
  2. "What topics do they focus on?"
  3. "What's their success rate as coordinator?"
  4. "Show their recent projects"
  5. "Who are their preferred partners?"
  Validations: Organization profile complete, statistics accurate.

- [ ] RUN & FIX: Execute scenario. Verify organization data accuracy.

### ==========================================================
### PHASE 4: Personalized Recommendations
### ==========================================================

### Task 018: User Context Learning Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/user_context_learning.yaml` with steps:
  1. "I'm from a small university in Portugal"
  2. "We work on marine biology"
  3. "We've never coordinated before"
  4. "What calls should we apply to?"
  5. "What about as a partner?"
  Required validation types:
  - `context_accumulated` (PersonalizationAgent): Profile builds (org type, country, sector, experience)
  - `profile_used` (PersonalizationAgent): Final recommendations use accumulated profile
  - `personalization_applied` (PersonalizationAgent): Response tailored to user context
  - `goal_progress` (GoalTrackingAgent): Progress toward finding suitable calls

- [ ] RUN & FIX: Execute scenario. Verify context influences recommendations.

### Task 019: Returning User Context Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/returning_user_context.yaml` with steps:
  1. User says: "I mentioned earlier I work on hydrogen - any new calls?"
  (Simulate conversation history with hydrogen context)
  Validations: System recalls context, doesn't ask for topic again.

- [ ] IMPLEMENT: Add context persistence validation to `ContextValidatorAgent`.

### Task 020: Progressive Profile Building Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/progressive_profile.yaml` with 12+ turns:
  1. "I work for an SME"
  2. "We're in the healthcare sector"
  3. "Specifically medical devices"
  4. "We're based in Germany"
  5. "We have 50 employees"
  6. "Annual revenue around 10M"
  7. "We want to expand into AI diagnostics"
  8. "We have some research partnerships already"
  9. "But never done EU funding before"
  10. "What's our best option?"
  Validations: Profile built across turns, final recommendation uses all context.

- [ ] RUN & FIX: Execute scenario. Track profile accumulation.

### Task 021: Preference-Based Filtering Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/preference_filtering.yaml` with steps:
  1. "Find funding calls - but nothing with lump sum funding"
  2. "I prefer calls with 70%+ funding rate"
  3. "Show only calls with deadlines in Q2 2024"
  4. "Remove any requiring more than 5 partners"
  Validations: Preferences accumulated, applied to results.

- [ ] RUN & FIX: Execute scenario. Fix preference filter application.

### ==========================================================
### PHASE 5: Strategic Planning Conversations
### ==========================================================

### Task 022: Funding Strategy Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/funding_strategy.yaml` with steps:
  1. "Help me plan our research funding strategy for the next 3 years"
  2. "We're a university department focusing on cybersecurity"
  3. "What Horizon Europe options do we have?"
  4. "What about building capacity through Erasmus+?"
  5. "How should we sequence our applications?"
  6. "What's a realistic timeline?"
  Validations: Multi-year strategy proposed, sequencing logical, programmes combined.

- [ ] RUN & FIX: Execute scenario. Verify strategic planning quality.

### Task 023: Portfolio Planning Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/portfolio_planning.yaml` with steps:
  1. "We want to submit 5 proposals this year"
  2. "Our research areas are: AI, robotics, and human-machine interaction"
  3. "What calls match our profile?"
  4. "Which should we prioritize?"
  5. "How do we avoid overlap?"
  6. "What's a realistic success expectation?"
  Validations: Portfolio approach recommended, diversification considered, success rates cited.

- [ ] RUN & FIX: Execute scenario. Fix portfolio recommendation logic.

### Task 024: Capacity Building Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/capacity_building.yaml` with steps:
  1. "We're new to EU funding - how do we get started?"
  2. "What programmes are best for beginners?"
  3. "Should we start as partner or coordinator?"
  4. "What's a good first project size?"
  5. "How do we build track record?"
  Validations: Beginner-appropriate advice, progression path suggested.

- [ ] RUN & FIX: Execute scenario. Verify onboarding quality.

### Task 025: Risk Assessment Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/risk_assessment.yaml` with steps:
  1. "What are the risks of applying to EIC Accelerator?"
  2. "What if we don't have prior EU funding?"
  3. "How does our company size affect chances?"
  4. "What about the interview stage?"
  5. "What can we do to improve our odds?"
  Validations: Risks identified accurately, mitigation strategies provided.

- [ ] RUN & FIX: Execute scenario. Verify risk information accuracy.

### ==========================================================
### PHASE 6: Cross-Programme Comparisons
### ==========================================================

### Task 026: Funding Type Comparison Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/funding_type_comparison.yaml` with steps:
  1. "Compare RIA vs IA for applied research"
  2. "What about CSA?"
  3. "How does EIC Pathfinder differ?"
  4. "What about MSCA Postdoctoral Fellowships?"
  5. "Which gives the most freedom?"
  Validations: All funding types compared accurately, differences highlighted.

- [ ] RUN & FIX: Execute scenario. Fix comparison tables.

### Task 027: Success Rate Analysis Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/success_rate_analysis.yaml` with steps:
  1. "What's the success rate for Horizon Europe?"
  2. "Break it down by cluster"
  3. "How does Cluster 5 compare to Cluster 1?"
  4. "What about by country?"
  5. "How does Germany compare to Poland?"
  6. "What factors improve success rates?"
  Validations: Statistics accurate, trends identified, factors explained.

- [ ] RUN & FIX: Execute scenario. Verify statistics accuracy.

### Task 028: Budget Comparison Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/budget_comparison.yaml` with steps:
  1. "Compare typical budgets: RIA vs IA vs EIC"
  2. "What's the average per-partner budget?"
  3. "How does this vary by organization type?"
  4. "What about coordinator vs partner budgets?"
  5. "Show budget trends over 2021-2024"
  Validations: Budget comparisons accurate, trends shown.

- [ ] RUN & FIX: Execute scenario. Fix budget statistics.

### Task 029: Timeline Comparison Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/timeline_comparison.yaml` with steps:
  1. "How long does a typical Horizon Europe proposal take to prepare?"
  2. "Compare with Erasmus+ KA2"
  3. "What about Creative Europe cooperation projects?"
  4. "Which has the fastest decision time?"
  5. "What's the project start lag after selection?"
  Validations: Timeline estimates reasonable, programme differences clear.

- [ ] RUN & FIX: Execute scenario. Verify timeline accuracy.

### ==========================================================
### PHASE 7: Deadline-Aware Conversations
### ==========================================================

### Task 030: Urgent Deadline Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/urgent_deadline.yaml` with steps:
  1. "What calls close in the next 30 days?"
  2. "Any for renewable energy?"
  3. "Is there still time to apply?"
  4. "What's the minimum we need ready?"
  5. "Can you prioritize by feasibility?"
  Validations: Deadlines accurate, feasibility assessment provided.

- [ ] RUN & FIX: Execute scenario. Verify deadline accuracy.

### Task 031: Deadline Tracking Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/deadline_tracking.yaml` with steps:
  1. "Track deadlines for Cluster 4 Digital calls"
  2. "When's the next one?"
  3. "What about the one after that?"
  4. "How much time between them?"
  5. "Which one should I target?"
  Validations: Deadline sequence correct, timeline logical.

- [ ] RUN & FIX: Execute scenario. Fix deadline sorting.

### Task 032: Call Opening Alert Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/call_opening_alert.yaml` with steps:
  1. "When do the 2025 Horizon Europe calls open?"
  2. "Specifically for health research"
  3. "What about Cluster 1 work programme?"
  4. "When should I start preparing?"
  5. "What's the typical time between opening and deadline?"
  Validations: Opening dates accurate (or appropriately uncertain), preparation advice given.

- [ ] RUN & FIX: Execute scenario. Verify work programme timeline handling.

### Task 033: Multi-Call Timeline Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/multi_call_timeline.yaml` with steps:
  1. "I want to apply to 3 calls this quarter"
  2. "Show me climate and energy calls with staggered deadlines"
  3. "Help me plan my submission timeline"
  4. "What if one call deadline changes?"
  5. "Show alternative calls as backup"
  Validations: Multi-call planning provided, contingency considered.

- [ ] RUN & FIX: Execute scenario. Fix multi-deadline planning.

### ==========================================================
### PHASE 8: Complex Eligibility Scenarios
### ==========================================================

### Task 034: Multi-Factor Eligibility Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/multi_factor_eligibility.yaml` with steps:
  1. "Can a Turkish university coordinate a Horizon Europe project?"
  2. "What about as partner?"
  3. "Does it matter if the project involves defense?"
  4. "What about quantum technology?"
  5. "Are there any calls where Turkey can coordinate?"
  Required validation types:
  - `eligibility_correct` (CrossProgrammeAgent): Associated country rules accurate
  - `programme_accurate` (CrossProgrammeAgent): Topic restrictions correctly identified
  - `context_accumulated` (PersonalizationAgent): Country context preserved across turns
  - `goal_achieved` (GoalTrackingAgent): User understands their eligibility options

- [ ] RUN & FIX: Execute scenario. Verify eligibility rule accuracy.

### Task 035: SME Eligibility Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/sme_eligibility.yaml` with steps:
  1. "We're an SME - what's available for us?"
  2. "We have 200 employees - are we still SME?"
  3. "Our parent company is large - does that affect us?"
  4. "What about EIC Accelerator?"
  5. "Can we participate in RIA as non-SME?"
  Validations: SME definition correct, ownership rules explained.

- [ ] RUN & FIX: Execute scenario. Verify SME eligibility rules.

### Task 036: Consortium Eligibility Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/consortium_eligibility.yaml` with steps:
  1. "We have partners from Germany, France, and UK"
  2. "Is this consortium eligible?"
  3. "What if we add a Swiss partner?"
  4. "What about a US partner?"
  5. "What's the minimum we need?"
  Validations: Consortium rules correct, third country participation explained.

- [ ] RUN & FIX: Execute scenario. Fix consortium eligibility logic.

### Task 037: Cross-Programme Eligibility Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/cross_programme_eligibility.yaml` with steps:
  1. "Can we have the same project in Horizon Europe and Erasmus+?"
  2. "What about different components of the same initiative?"
  3. "Are there rules against double funding?"
  4. "Can we apply to both simultaneously?"
  5. "What's the best strategy?"
  Validations: Double funding rules explained, complementary funding strategies suggested.

- [ ] RUN & FIX: Execute scenario. Verify cross-programme rules.

### ==========================================================
### PHASE 9: Erasmus+ Specific Flows
### ==========================================================

### Task 038: Erasmus+ Action Selection Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/erasmus_action_selection.yaml` with steps:
  1. "What Erasmus+ actions are there?"
  2. "We're a VET school wanting international mobility"
  3. "What about long-term partnerships?"
  4. "We also want to develop new curriculum"
  5. "Which combination works best?"
  Required validation types:
  - `programme_accurate` (CrossProgrammeAgent): KA1/KA2 correctly explained
  - `eligibility_correct` (CrossProgrammeAgent): VET sector eligibility accurate
  - `personalization_applied` (PersonalizationAgent): Recommendations fit VET school profile
  - `context_accumulated` (PersonalizationAgent): VET school context builds across turns
  - `goal_achieved` (GoalTrackingAgent): User understands best action combination

- [ ] RUN & FIX: Execute scenario. Verify Erasmus+ action mapping.

### Task 039: Erasmus+ Budget Calculation Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/erasmus_budget_calculation.yaml` with steps:
  1. "Calculate budget for 20 student exchanges to France"
  2. "5 months each"
  3. "Include staff training too - 10 staff for 1 week"
  4. "What about exceptional costs?"
  5. "What's the total we can request?"
  Validations: Unit costs applied correctly, travel bands correct, lump sums accurate.

- [ ] RUN & FIX: Execute scenario. Fix Erasmus+ budget calculation.

### Task 040: Erasmus+ Accreditation Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/erasmus_accreditation.yaml` with steps:
  1. "Should we get Erasmus accreditation?"
  2. "What are the benefits?"
  3. "How long does it take?"
  4. "Can we still apply to KA1 without it?"
  5. "What's the strategic choice?"
  Validations: Accreditation vs short-term projects explained, strategic advice given.

- [ ] RUN & FIX: Execute scenario. Verify accreditation information.

### ==========================================================
### PHASE 10: Creative Europe Specific Flows
### ==========================================================

### Task 041: Creative Europe Strand Selection Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/creative_europe_strand.yaml` with steps:
  1. "We're a film production company - what's available?"
  2. "Tell me about MEDIA strand"
  3. "What about development funding?"
  4. "We're also interested in distribution"
  5. "Can we apply to multiple actions?"
  Validations: MEDIA actions explained, development vs distribution differentiated.

- [ ] RUN & FIX: Execute scenario. Fix Creative Europe navigation.

### Task 042: Creative Europe Eligibility Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/creative_europe_eligibility.yaml` with steps:
  1. "Is our Serbian NGO eligible for Creative Europe?"
  2. "What about the Culture strand?"
  3. "As coordinator or partner?"
  4. "What about MEDIA?"
  5. "Are there any restrictions?"
  Validations: Participating country status correct, strand-specific rules explained.

- [ ] RUN & FIX: Execute scenario. Verify Creative Europe eligibility.

### Task 043: Creative Europe Cooperation Project Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/creative_europe_cooperation.yaml` with steps:
  1. "Explain Creative Europe cooperation projects"
  2. "What's the difference between small, medium, large?"
  3. "We have 3 partners - which category?"
  4. "What's the funding rate?"
  5. "Help us plan a medium-scale project"
  Validations: Scale definitions correct, partnership requirements accurate.

- [ ] RUN & FIX: Execute scenario. Fix cooperation project logic.

### ==========================================================
### PHASE 11: Error Handling & Edge Cases
### ==========================================================

### Task 044: Conflicting Requirements Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/conflicting_requirements.yaml` with steps:
  1. "Find calls for SMEs with 100% funding"
  2. "That allow for-profit companies to coordinate"
  3. "With no match funding required"
  4. "In the defense sector"
  5. "For a US company"
  Validations: System explains impossibilities gracefully, suggests alternatives.

- [ ] RUN & FIX: Execute scenario. Fix conflict handling.

### Task 045: Outdated Information Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/outdated_information.yaml` with steps:
  1. "Tell me about H2020 calls" (historical)
  2. "What about FP7?" (very old)
  3. "Can I still apply?"
  4. "What replaced them?"
  Validations: Historical context provided, current alternatives suggested.

- [ ] RUN & FIX: Execute scenario. Fix historical programme handling.

### Task 046: Ambiguous Programme Reference Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/ambiguous_programme.yaml` with steps:
  1. "Tell me about the innovation fund"
  2. "I mean the EU one"
  3. "The one for climate"
  4. "With grants not loans"
  Validations: Disambiguation handled well, multiple possibilities explained.

- [ ] RUN & FIX: Execute scenario. Fix ambiguity resolution.

### Task 047: Out-of-Scope Query Handling Scenario
- [ ] CREATE SCENARIO: Create `tests/scenarios/advanced/out_of_scope.yaml` with steps:
  1. "What about US NSF grants?"
  2. "Or UK Research Council funding?"
  3. "Can you compare with EU programmes?"
  4. "What's similar to Horizon Europe internationally?"
  Validations: Gracefully explains scope, provides what info possible.

- [ ] RUN & FIX: Execute scenario. Fix out-of-scope handling.

### ==========================================================
### PHASE 12: Integration & Quality
### ==========================================================

### Task 048: Goal Achievement Validation
- [ ] TEST: Run all PHASE 2 scenarios with goal tracking enabled.
- [ ] VERIFY: Goal progress tracked correctly, completion detected.

### Task 049: Personalization Validation
- [ ] TEST: Run all PHASE 4 scenarios with personalization validation.
- [ ] VERIFY: Context accumulated correctly, recommendations personalized.

### Task 050: Cross-Programme Validation
- [ ] TEST: Run all PHASE 1 and PHASE 6 scenarios with cross-programme validation.
- [ ] VERIFY: Programme information accurate, comparisons correct.

### Task 051: Quality Baseline for Advanced Scenarios
- [ ] MEASURE: Run all advanced scenarios and record quality scores.
  Save to `tests/quality/results/advanced_flows_quality_baseline.json`.

- [ ] DOCUMENT: Create summary of challenging scenarios, identify improvement areas.

### Task 052: Regression Suite for Advanced Flows
- [ ] CREATE: Create `tests/test_advanced_conversation_regression.py` with tests for:
  1. Multi-programme navigation (Tasks 006-009)
  2. Proposal workflows (Tasks 010-013)
  3. Partner discovery (Tasks 014-017)
  4. Personalization (Tasks 018-021)
  5. Strategic planning (Tasks 022-025)
  6. Programme comparisons (Tasks 026-029)
  7. Deadline handling (Tasks 030-033)
  8. Complex eligibility (Tasks 034-037)

- [ ] RUN: Execute full regression suite. All tests must pass.

### Task 053: CI/CD Integration
- [ ] UPDATE: Extend `.github/workflows/conversation-tests.yml` with:
  - Advanced scenario test execution
  - Goal achievement metrics
  - Personalization quality checks
  - Cross-programme accuracy validation.

- [ ] VERIFY: Trigger workflow, ensure advanced tests run successfully.

---

## Summary

| Phase | Tasks | Focus Area |
|-------|-------|------------|
| 0 | 001-005 | Test Infrastructure Setup |
| 1 | 006-009 | Multi-Programme Navigation |
| 2 | 010-013 | Proposal Development Workflows |
| 3 | 014-017 | Partner Discovery Journeys |
| 4 | 018-021 | Personalized Recommendations |
| 5 | 022-025 | Strategic Planning Conversations |
| 6 | 026-029 | Cross-Programme Comparisons |
| 7 | 030-033 | Deadline-Aware Conversations |
| 8 | 034-037 | Complex Eligibility Scenarios |
| 9 | 038-040 | Erasmus+ Specific Flows |
| 10 | 041-043 | Creative Europe Specific Flows |
| 11 | 044-047 | Error Handling & Edge Cases |
| 12 | 048-053 | Integration & Quality |

**Total: 53 tasks across 13 phases**

---

## Completion Criteria

The PRD is complete when:

1. **All scenario tests pass** - 0 failures across all categories
2. **Goal achievement tracked** - User goals identified and progress measured
3. **Personalization working** - Context accumulated and used across turns
4. **Cross-programme accurate** - Correct information for all three programmes
5. **Deadlines accurate** - Time-sensitive queries handled correctly
6. **Eligibility accurate** - Complex eligibility chains resolved correctly
7. **Quality maintained** - No degradation > 15 points in long conversations
8. **CI/CD integrated** - Automated testing for advanced scenarios

---

## Quick Reference

### Running Tests

```bash
# All advanced scenarios
pytest tests/test_advanced_conversation_scenarios.py -v

# Multi-programme navigation
pytest tests/test_advanced_conversation_scenarios.py -k "programme" -v

# Proposal workflows
pytest tests/test_advanced_conversation_scenarios.py -k "proposal" -v

# Partner discovery
pytest tests/test_advanced_conversation_scenarios.py -k "partner" -v

# Deadline handling
pytest tests/test_advanced_conversation_scenarios.py -k "deadline" -v

# Eligibility scenarios
pytest tests/test_advanced_conversation_scenarios.py -k "eligibility" -v

# Programme-specific tests
pytest tests/test_advanced_conversation_scenarios.py -k "erasmus" -v
pytest tests/test_advanced_conversation_scenarios.py -k "creative" -v

# With coverage
pytest tests/test_advanced_conversation_scenarios.py --cov=app/services -v
```

### Debugging Failures

| Failure Type | Agent to Use | What to Check |
|--------------|--------------|---------------|
| Goal not achieved | `GoalTrackingAgent` | `track_goal_progress()` |
| Context not used | `PersonalizationAgent` | `validate_context_usage()` |
| Wrong programme info | `CrossProgrammeAgent` | `validate_programme_accuracy()` |
| Deadline wrong | `ContextValidatorAgent` | `validate_deadline_accuracy()` |
| Eligibility wrong | `CrossProgrammeAgent` | `validate_eligibility_rules()` |
| Quality drop | `QualityEvaluatorAgent` | `evaluate_conversation()` |

### Key Scenarios by Persona

| Persona | Key Scenarios |
|---------|---------------|
| Research Manager (Maria) | 010, 011, 013, 022, 034 |
| SME Innovation Lead (Stefan) | 018, 025, 030, 035 |
| Cultural Director (Elena) | 008, 041, 042, 043 |
| Education Coordinator (Ahmed) | 038, 039, 040 |

---

## Appendix: New Files to Create

### Test Agents (Phase 0)
- `tests/agents/goal_tracking_agent.py` - Goal progress tracking
- `tests/agents/personalization_agent.py` - Context learning validation
- `tests/agents/cross_programme_agent.py` - Multi-programme accuracy

### Scenario Runner (Phase 0)
- `tests/test_advanced_conversation_scenarios.py` - Main test runner

### Scenarios Directory
- `tests/scenarios/advanced/` - Directory for all advanced scenario YAML files

### Scenarios (38 YAML files)
- `tests/scenarios/advanced/programme_discovery.yaml`
- `tests/scenarios/advanced/programme_comparison.yaml`
- `tests/scenarios/advanced/programme_recommendation.yaml`
- `tests/scenarios/advanced/eligibility_routing.yaml`
- `tests/scenarios/advanced/full_proposal_journey.yaml`
- `tests/scenarios/advanced/budget_iteration.yaml`
- `tests/scenarios/advanced/timeline_refinement.yaml`
- `tests/scenarios/advanced/consortium_building.yaml`
- `tests/scenarios/advanced/partner_search_refinement.yaml`
- `tests/scenarios/advanced/partner_comparison.yaml`
- `tests/scenarios/advanced/network_exploration.yaml`
- `tests/scenarios/advanced/organization_deep_dive.yaml`
- `tests/scenarios/advanced/user_context_learning.yaml`
- `tests/scenarios/advanced/returning_user_context.yaml`
- `tests/scenarios/advanced/progressive_profile.yaml`
- `tests/scenarios/advanced/preference_filtering.yaml`
- `tests/scenarios/advanced/funding_strategy.yaml`
- `tests/scenarios/advanced/portfolio_planning.yaml`
- `tests/scenarios/advanced/capacity_building.yaml`
- `tests/scenarios/advanced/risk_assessment.yaml`
- `tests/scenarios/advanced/funding_type_comparison.yaml`
- `tests/scenarios/advanced/success_rate_analysis.yaml`
- `tests/scenarios/advanced/budget_comparison.yaml`
- `tests/scenarios/advanced/timeline_comparison.yaml`
- `tests/scenarios/advanced/urgent_deadline.yaml`
- `tests/scenarios/advanced/deadline_tracking.yaml`
- `tests/scenarios/advanced/call_opening_alert.yaml`
- `tests/scenarios/advanced/multi_call_timeline.yaml`
- `tests/scenarios/advanced/multi_factor_eligibility.yaml`
- `tests/scenarios/advanced/sme_eligibility.yaml`
- `tests/scenarios/advanced/consortium_eligibility.yaml`
- `tests/scenarios/advanced/cross_programme_eligibility.yaml`
- `tests/scenarios/advanced/erasmus_action_selection.yaml`
- `tests/scenarios/advanced/erasmus_budget_calculation.yaml`
- `tests/scenarios/advanced/erasmus_accreditation.yaml`
- `tests/scenarios/advanced/creative_europe_strand.yaml`
- `tests/scenarios/advanced/creative_europe_eligibility.yaml`
- `tests/scenarios/advanced/creative_europe_cooperation.yaml`
- `tests/scenarios/advanced/conflicting_requirements.yaml`
- `tests/scenarios/advanced/outdated_information.yaml`
- `tests/scenarios/advanced/ambiguous_programme.yaml`
- `tests/scenarios/advanced/out_of_scope.yaml`

### Regression Test File
- `tests/test_advanced_conversation_regression.py` - Regression suite

### Quality Tracking
- `tests/quality/results/advanced_flows_quality_baseline.json`

---

## Dependency on Conversation Stability PRD

This PRD builds on the foundation established in `MAPIT_CONVERSATION_STABILITY_PRD.md`:

| Stability PRD Provides | This PRD Uses |
|------------------------|---------------|
| `ConversationLockManager` | Race condition prevention in long scenarios |
| `AtomicMessageStorage` | Reliable context persistence |
| `ConversationFlowAgent` | Multi-turn simulation |
| `ContextValidatorAgent` | Context integrity checking |
| `QualityEvaluatorAgent` | Quality scoring |

**Prerequisite**: All tasks in the Conversation Stability PRD should be complete before starting this PRD.
