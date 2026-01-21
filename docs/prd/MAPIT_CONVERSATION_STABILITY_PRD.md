# MAPIT Conversation Stability PRD

> **Purpose**: Fix conversation flow instability and implement automated scenario testing
> **Method**: Sub-agent based testing with context validation and quality evaluation
> **Pass Threshold**: All scenarios pass, no race conditions, quality >= 75/100
> **Target**: Production-ready multi-turn conversations

---

## Problem Statement

The MAPIT application works well on individual test cases but exhibits significant instability in real-world conversational scenarios:

1. **Race conditions** when messages are sent rapidly
2. **Context loss** causing follow-up questions to fail
3. **Split-brain storage** between database and Redis
4. **Silent failures** that hide real issues
5. **Quality degradation** over long conversations

---

## Available Test Agents & Infrastructure

### Test Agents (in `tests/agents/`)
| Agent | Purpose |
|-------|---------|
| `ConversationFlowAgent` | Simulates multi-turn conversations, collects SSE events |
| `ContextValidatorAgent` | Validates DB/Redis consistency, detects race conditions |
| `QualityEvaluatorAgent` | Scores responses using LLM-as-judge (40/25/25/10 rubric) |

### Core Stability Modules (in `app/core/`)
| Module | Purpose |
|--------|---------|
| `conversation_lock.py` | Per-conversation async locks to prevent race conditions |
| `atomic_storage.py` | Atomic message storage with proper error reporting |

### Test Scenarios (in `tests/scenarios/`)
| Category | Scenarios |
|----------|-----------|
| `basic_flows/` | Funding call search, project search, budget calculation |
| `follow_up/` | Numbered references, "tell me more", comparisons |
| `context/` | Long conversations (10+ turns), memory overflow |
| `error_recovery/` | Invalid references, tool failures |
| `concurrent/` | Rapid messages, simultaneous requests |

### Scoring Dimensions (100 points total)
| Dimension | Points | What to Check |
|-----------|--------|---------------|
| Query Fulfillment | 40 | All query components addressed |
| Specificity | 25 | Numbers, dates, names, call IDs |
| Factual Accuracy | 25 | Correct EU funding information |
| Actionability | 10 | Clear next steps, links, deadlines |

---

## Configuration Notes

Before running tasks:
1. Test agents are in `tests/agents/` directory
2. Scenarios are in `tests/scenarios/` directory
3. Core modules are in `app/core/` directory
4. API is running: `docker compose up --build`
5. Environment variables set: `DATABASE_URL`, `REDIS_URL`, `NEO4J_URI`

Run scenario tests:
```bash
# All scenarios
pytest tests/test_conversation_scenarios.py -v

# Specific category
pytest tests/test_conversation_scenarios.py -k "basic" -v

# With live API
TEST_API_URL=http://localhost:8000 pytest tests/test_conversation_scenarios.py -v
```

---

## Tasks

### ==========================================================
### PHASE 1: Critical Infrastructure Fixes
### ==========================================================

### Task 001: Integrate Conversation Locking
- [x] IMPLEMENT: Update `app/services/conversation/conversation_manager.py` to use `ConversationLockManager`. Wrap the `process_message_v3_streaming` method with `async with get_conversation_lock(conversation_id)`. This prevents race conditions when multiple messages arrive for the same conversation.

- [x] TEST: Create test in `tests/test_conversation_lock.py` that sends 5 concurrent messages to the same conversation and verifies: (1) all messages stored, (2) no duplicates, (3) correct ordering.

### Task 002: Integrate Atomic Storage
- [x] IMPLEMENT: Update `app/services/conversation/conversation_manager.py` to use `AtomicMessageStorage` instead of separate `_store_user_message` and `_store_assistant_message` calls. Use `store_message_pair()` for atomic transaction.

- [x] TEST: Create test that simulates DB failure mid-storage and verifies: (1) partial storage is rolled back, (2) error is properly reported (not silent), (3) client receives error event.

### Task 003: Fix Streaming Before Storage Issue
- [x] IMPLEMENT: In `process_message_v3_streaming()`, move the assistant message storage to happen BEFORE yielding response tokens. Current flow streams response then stores; change to store then stream.

- [x] TEST: Create test that verifies: (1) message is in DB before first token is sent, (2) follow-up query immediately after response can access the stored message.

### Task 004: Fix Silent Redis Fallback
- [x] IMPLEMENT: Update `app/services/memory/memory_service.py` `FallbackRedis` class to log WARNING level messages on every operation and track fallback usage in metrics. Add `is_fallback_mode` property.

- [x] TEST: Create test that: (1) disconnects Redis, (2) sends message, (3) verifies WARNING is logged, (4) verifies `is_fallback_mode` returns True.

### Task 005: Add Context Window Reset
- [x] IMPLEMENT: In `app/services/agents/tool_aware_agent.py`, add automatic `context_window_manager.reset()` call at the start of each `process_query()` invocation to prevent memory leak across queries.

- [x] TEST: Create test that processes 10 queries in sequence and verifies context size doesn't accumulate beyond expected limits.

### ==========================================================
### PHASE 2: Basic Flow Scenario Testing
### ==========================================================

### Task 006: Funding Call Search Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/basic_flows/funding_call_search.yaml` with steps:
  1. "Find open funding calls for hydrogen research"
  2. "What are the deadlines?"
  3. "Tell me about the first one"
  Validations: tools_used includes search_funding_calls, response contains call details, follow-up resolves correctly.

- [x] RUN & FIX: Execute scenario using `ConversationFlowAgent`. If any step fails, identify the issue using `ContextValidatorAgent`, fix, and re-run until passing.

### Task 007: Project Search Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/basic_flows/project_search.yaml` with steps:
  1. "Show me recent AI healthcare projects"
  2. "What was the budget of the largest one?"
  3. "Who coordinated it?"
  Validations: tools_used includes search_projects, specific project details returned.

- [x] RUN & FIX: Execute scenario. Fix any failures and re-run until passing.

### Task 008: Budget Calculation Scenario
- [x] VERIFY SCENARIO: Verify `tests/scenarios/basic_flows/budget_calculation.yaml` runs correctly with steps:
  1. Budget calculation request
  2. Personnel breakdown follow-up
  3. Comparison with similar projects
  Validations: tools_used includes calculate_budget and get_budget_benchmark.

- [x] RUN & FIX: Execute scenario. Fix any failures and re-run until passing.

### Task 009: Timeline Generation Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/basic_flows/timeline_generation.yaml` with steps:
  1. "Generate a timeline for a 3-year RIA project on renewable energy"
  2. "Can we add more deliverables in WP2?"
  3. "What about milestones?"
  Validations: tools_used includes generate_timeline, work packages returned.

- [x] RUN & FIX: Execute scenario. Fix any failures and re-run until passing.

### ==========================================================
### PHASE 3: Follow-Up Reference Testing
### ==========================================================

### Task 010: Numbered Reference Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/follow_up/follow_up_by_number.yaml` with steps:
  1. "Show me 5 open calls for climate research"
  2. "Tell me about the third one"
  3. "What's the deadline for that call?"
  4. "Compare it with the first one"
  Validations: numbered references resolve to correct items, context preserved.

- [x] RUN & FIX: Execute scenario. Use `ContextValidatorAgent.validate_follow_up_context()` to debug failures. Fix and re-run.

### Task 011: "Tell Me More" Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/follow_up/follow_up_more_details.yaml` with steps:
  1. "What is the EIC Accelerator?"
  2. "Tell me more about the application process"
  3. "What about the budget?"
  4. "And the success rate?"
  Validations: each follow-up builds on previous context.

- [x] RUN & FIX: Execute scenario. Fix any failures and re-run until passing.

### Task 012: Comparison Follow-Up Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/follow_up/follow_up_comparison.yaml` with steps:
  1. "Show me 3 calls for digital innovation"
  2. "Compare the first and second ones"
  3. "Which has a higher budget?"
  Validations: comparison correctly references previous results.

- [x] RUN & FIX: Execute scenario. Fix and re-run until passing.

### ==========================================================
### PHASE 4: Context Preservation Testing
### ==========================================================

### Task 013: Long Conversation Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/context/long_conversation.yaml` with 10+ steps:
  1. "I'm researching hydrogen energy funding"
  2. "What programmes cover this?"
  3. "Tell me about Cluster 5"
  ... (continue to 10+ turns)
  10. "Remind me what we started discussing"
  Validations: final turn correctly references initial topic.

- [x] RUN & FIX: Execute scenario. Use `QualityEvaluatorAgent.evaluate_conversation()` to track quality across turns. Fix any degradation.

### Task 014: Topic Switching Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/context/topic_switching.yaml` with steps:
  1. "Tell me about RIA projects"
  2. "What about Erasmus+ mobility?"
  3. "Going back to RIA, what's the funding rate?"
  Validations: can switch topics and return to previous topic.

- [x] RUN & FIX: Execute scenario. Fix any failures and re-run until passing.

### Task 015: Memory Overflow Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/context/memory_overflow.yaml` with 15+ steps to exceed STM capacity (12 turns). Verify:
  1. Recent messages are preserved
  2. Earlier context is summarized in LTM
  3. Quality doesn't catastrophically degrade.

- [x] RUN & FIX: Execute scenario. Check `ContextValidatorAgent.validate_context_integrity()` for consistency.

### ==========================================================
### PHASE 5: Error Recovery Testing
### ==========================================================

### Task 016: Invalid Reference Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/error_recovery/invalid_reference.yaml` with steps:
  1. "Show me 3 projects"
  2. "Tell me about the 100th one" (invalid)
  3. "What about the first one?" (valid)
  Validations: graceful error for invalid, recovery for valid.

- [x] RUN & FIX: Execute scenario. Ensure error handling doesn't break conversation.

### Task 017: Ambiguous Query Scenario
- [x] CREATE SCENARIO: Create `tests/scenarios/error_recovery/ambiguous_query.yaml` with steps:
  1. "Show me projects"
  2. "Tell me about it" (ambiguous)
  3. "I mean the hydrogen project" (clarification)
  Validations: handles ambiguity, accepts clarification.

- [x] RUN & FIX: Execute scenario. Fix any failures and re-run until passing.

### Task 018: Tool Timeout Simulation
- [x] CREATE SCENARIO: Create `tests/scenarios/error_recovery/tool_timeout.yaml` that tests behavior when a tool takes too long. Verify:
  1. Timeout is properly handled
  2. User receives informative error
  3. Conversation can continue after error.

- [x] RUN & FIX: May require mocking tool to simulate timeout. Fix any failures.

### ==========================================================
### PHASE 6: Concurrent Access Testing
### ==========================================================

### Task 019: Rapid Messages Scenario
- [x] VERIFY SCENARIO: Verify `tests/scenarios/concurrent/rapid_messages.yaml` runs correctly with 5 messages sent with 100ms delays. Verify:
  1. All messages stored
  2. No message loss
  3. Responses in correct order.

- [x] RUN & FIX: Use `ContextValidatorAgent.detect_race_condition()` to identify issues. Fix any race conditions.

### Task 020: Simultaneous Messages Test
- [x] CREATE TEST: In `tests/test_conversation_scenarios.py`, create `test_simultaneous_messages()` that uses `ConversationFlowAgent.run_concurrent_messages()` to send 3 messages at exact same time. Verify:
  1. No crashes
  2. All messages processed (order may vary)
  3. Context remains consistent.

- [x] RUN & FIX: If race conditions detected, verify `ConversationLockManager` is properly integrated.

### Task 021: Interleaved Conversations Test
- [x] CREATE TEST: Create test with 2 `ConversationFlowAgent` instances on different conversation IDs, sending messages alternately. Verify:
  1. No cross-contamination of context
  2. Each conversation maintains its own state
  3. Concurrent processing works.

- [x] RUN & FIX: Fix any issues with conversation isolation.

### ==========================================================
### PHASE 7: Quality Validation
### ==========================================================

### Task 022: Quality Baseline Measurement
- [ ] MEASURE: Run all basic_flows scenarios and record quality scores using `QualityEvaluatorAgent.evaluate_conversation()`. Save baseline to `tests/quality/results/conversation_quality_baseline.json`.

- [ ] DOCUMENT: Create summary of average scores per scenario, identify lowest scoring areas.

### Task 023: Quality Degradation Detection
- [ ] IMPLEMENT: Add quality degradation detection to `test_conversation_scenarios.py` that fails if quality drops more than 15 points during a conversation.

- [ ] VERIFY: Run long_conversation scenario and verify no degradation detected.

### Task 024: Regression Test Suite
- [ ] CREATE: Create `tests/test_conversation_regression.py` with tests for each fixed issue:
  1. Race condition prevention (Task 001)
  2. Atomic storage (Task 002)
  3. Storage before streaming (Task 003)
  4. Redis fallback warning (Task 004)
  5. Context window reset (Task 005)

- [ ] RUN: Execute full regression suite. All tests must pass.

### ==========================================================
### PHASE 8: CI/CD Integration
### ==========================================================

### Task 025: GitHub Actions Workflow
- [ ] CREATE: Create `.github/workflows/conversation-tests.yml` with:
  1. Service containers (postgres, redis, neo4j)
  2. API server startup
  3. Scenario test execution
  4. Quality baseline comparison
  5. Artifact upload for results.

- [ ] TEST: Trigger workflow manually, verify it completes successfully.

### Task 026: Pre-commit Hook
- [ ] CREATE: Add pre-commit hook that runs quick conversation smoke tests before allowing commits that modify `conversation_manager.py` or `memory_service.py`.

- [ ] VERIFY: Make a test change and verify hook runs.

### Task 027: Quality Gate
- [ ] IMPLEMENT: Add quality gate to CI that fails PR if:
  1. Any scenario test fails
  2. Quality score below 75
  3. Race condition detected
  4. Context integrity check fails.

- [ ] VERIFY: Create test PR that would fail quality gate, verify it's blocked.

### ==========================================================
### PHASE 9: Documentation & Cleanup
### ==========================================================

### Task 028: Update CLAUDE.md
- [ ] UPDATE: Add section to `CLAUDE.md` documenting:
  1. Conversation stability architecture
  2. How to run scenario tests
  3. How to add new scenarios
  4. Quality evaluation process.

### Task 029: Architecture Documentation
- [ ] CREATE: Create `docs/CONVERSATION_STABILITY_ARCHITECTURE.md` with:
  1. Lock manager design
  2. Atomic storage design
  3. Test agent architecture
  4. Scenario format specification.

### Task 030: Cleanup Temporary Files
- [ ] CLEANUP: Remove any temporary test files, ensure all new code is properly documented, run linter and formatter on all new files.

- [ ] VERIFY: Run `make lint` and `make format` with no errors.

---

## Summary

| Phase | Tasks | Focus Area |
|-------|-------|------------|
| 1 | 001-005 | Critical Infrastructure Fixes |
| 2 | 006-009 | Basic Flow Scenarios |
| 3 | 010-012 | Follow-Up Reference Testing |
| 4 | 013-015 | Context Preservation |
| 5 | 016-018 | Error Recovery |
| 6 | 019-021 | Concurrent Access |
| 7 | 022-024 | Quality Validation |
| 8 | 025-027 | CI/CD Integration |
| 9 | 028-030 | Documentation & Cleanup |

**Total: 30 tasks across 9 phases**

---

## Completion Criteria

The PRD is complete when:

1. **All scenario tests pass** - 0 failures across all categories
2. **No race conditions** - Concurrent tests complete without data loss
3. **Context integrity** - DB and Redis remain synchronized
4. **Quality maintained** - No degradation > 15 points in conversations
5. **CI/CD active** - Automated testing on every PR
6. **Documentation complete** - All new code documented

---

## Quick Reference

### Running Tests

```bash
# All conversation scenarios
pytest tests/test_conversation_scenarios.py -v

# Basic flows only
pytest tests/test_conversation_scenarios.py -k "basic" -v

# Follow-up tests only
pytest tests/test_conversation_scenarios.py -k "follow_up" -v

# Concurrent tests only
pytest tests/test_conversation_scenarios.py -k "concurrent" -v

# With coverage
pytest tests/test_conversation_scenarios.py --cov=app/services/conversation -v
```

### Debugging Failures

| Failure Type | Agent to Use | What to Check |
|--------------|--------------|---------------|
| Message not stored | `ContextValidatorAgent` | `validate_message_stored()` |
| Context lost | `ContextValidatorAgent` | `validate_context_integrity()` |
| Follow-up fails | `ContextValidatorAgent` | `validate_follow_up_context()` |
| Race condition | `ContextValidatorAgent` | `detect_race_condition()` |
| Quality drop | `QualityEvaluatorAgent` | `evaluate_conversation()` |
| Tool not called | `ConversationFlowAgent` | Check `turn.tools_used` |

### Key Files

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Shared fixtures |
| `tests/agents/conversation_flow_agent.py` | Conversation simulation |
| `tests/agents/context_validator_agent.py` | State validation |
| `tests/agents/quality_evaluator_agent.py` | Quality scoring |
| `tests/test_conversation_scenarios.py` | Main test runner |
| `app/core/conversation_lock.py` | Lock manager |
| `app/core/atomic_storage.py` | Atomic storage |

---

## Appendix: Files Created

### Test Infrastructure
- [x] `tests/conftest.py` - Shared fixtures (43 fixtures consolidated)
- [x] `tests/agents/__init__.py` - Agent exports
- [x] `tests/agents/conversation_flow_agent.py` - Multi-turn conversation simulation
- [x] `tests/agents/context_validator_agent.py` - DB/Redis consistency validation
- [x] `tests/agents/quality_evaluator_agent.py` - LLM-as-judge quality scoring
- [x] `tests/test_conversation_scenarios.py` - Scenario test runner

### Scenarios
- [x] `tests/scenarios/basic_flows/funding_call_search.yaml`
- [x] `tests/scenarios/basic_flows/project_search.yaml`
- [x] `tests/scenarios/basic_flows/budget_calculation.yaml`
- [x] `tests/scenarios/basic_flows/timeline_generation.yaml`
- [x] `tests/scenarios/follow_up/follow_up_by_number.yaml`
- [x] `tests/scenarios/follow_up/follow_up_more_details.yaml`
- [x] `tests/scenarios/follow_up/follow_up_comparison.yaml`
- [x] `tests/scenarios/context/long_conversation.yaml`
- [x] `tests/scenarios/context/topic_switching.yaml`
- [x] `tests/scenarios/context/memory_overflow.yaml`
- [x] `tests/scenarios/error_recovery/invalid_reference.yaml`
- [x] `tests/scenarios/error_recovery/ambiguous_query.yaml`
- [x] `tests/scenarios/error_recovery/tool_timeout.yaml`
- [x] `tests/scenarios/concurrent/rapid_messages.yaml`

### Core Stability Modules
- [x] `app/core/conversation_lock.py` - Async conversation locking
- [x] `app/core/atomic_storage.py` - Atomic message storage
- [x] `app/core/__init__.py` - Updated exports

### Documentation
- [x] `docs/MAPIT_IMPROVEMENT_REPORT.md` - Comprehensive analysis report
