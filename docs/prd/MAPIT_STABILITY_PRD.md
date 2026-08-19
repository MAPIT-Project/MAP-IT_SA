> ⚠️ **ARCHIVED — 20 July 2026** — This document is historical and no longer current.
> See [START_HERE.md](../../../START_HERE.md) for current documentation.
> Reason: this is an older, entirely unchecked duplicate PRD that has been superseded by the conversation stability documentation.

# MAPIT Conversation Stability PRD

> **Purpose**: Systematically test and fix conversation flow stability issues using automated sub-agents
> **Method**: Run conversation scenarios through test agents, validate context consistency, evaluate quality
> **Pass Threshold**: All validations pass, quality score >= 75/100, no race conditions detected
> **Max Fix Attempts**: 3 per issue

---

## Available Test Agents & Tools

### Test Sub-Agents (in `tests/agents/`)
| Agent | Purpose |
|-------|---------|
| `ConversationFlowAgent` | Simulates multi-turn conversations, collects SSE events |
| `ContextValidatorAgent` | Validates DB/Redis consistency, detects race conditions |
| `QualityEvaluatorAgent` | Scores response quality using LLM-as-judge (40/25/25/10) |

### Core Stability Modules (in `app/core/`)
| Module | Purpose |
|--------|---------|
| `conversation_lock.py` | Per-conversation async locks to prevent race conditions |
| `atomic_storage.py` | Atomic DB + memory storage with proper error handling |

### Test Scenarios (in `tests/scenarios/`)
| Category | Scenarios |
|----------|-----------|
| `basic_flows/` | funding_call_search, project_search, budget_calculation |
| `follow_up/` | follow_up_by_number, follow_up_more_details |
| `context/` | long_conversation (10+ turns) |
| `error_recovery/` | invalid_reference |
| `concurrent/` | rapid_messages |

### Scoring Dimensions (100 points total)
| Dimension | Points | What to Check |
|-----------|--------|---------------|
| Query Fulfillment | 40 | All query components addressed |
| Specificity | 25 | Numbers, dates, names, call IDs |
| Factual Accuracy | 25 | Cross-ref with actual tool results |
| Actionability | 10 | Clear next steps, links, deadlines |

---

## Configuration Notes

Before running, ensure:
1. Test agents are in `tests/agents/` directory
2. Scenario files are in `tests/scenarios/` directory
3. Results directory exists: `tests/stability_results/`
4. API is running: `docker compose up --build`
5. Environment variables set: `DATABASE_URL`, `REDIS_URL`, `TEST_API_URL`

Run with:
```bash
# All scenario tests
pytest tests/test_conversation_scenarios.py -v

# Specific category
pytest tests/test_conversation_scenarios.py -k "basic" -v

# With live API
TEST_API_URL=http://localhost:8000 pytest tests/test_conversation_scenarios.py -v
```

---

## Tasks

### ==========================================================
### PHASE 1: Infrastructure Setup
### ==========================================================

### Task 001: Verify Test Agent Installation
- [ ] VERIFY: Confirm all test agents are properly installed and importable. Run:
  ```python
  from tests.agents import ConversationFlowAgent, ContextValidatorAgent, QualityEvaluatorAgent
  ```
  Save verification result to `tests/stability_results/task_001_agents_verified.json`.

- [ ] FIX IF NEEDED: If import fails, check `tests/agents/__init__.py` exports and fix any missing dependencies.

### Task 002: Verify Scenario Files
- [ ] VERIFY: Confirm all YAML scenario files are valid and loadable. Use `ConversationScenario.from_yaml()` to load each file in `tests/scenarios/`. Save results to `tests/stability_results/task_002_scenarios_verified.json`.

- [ ] FIX IF NEEDED: Fix any YAML syntax errors or missing required fields.

### Task 003: Verify Core Stability Modules
- [ ] VERIFY: Confirm `ConversationLockManager` and `AtomicMessageStorage` are properly installed:
  ```python
  from app.core import ConversationLockManager, AtomicMessageStorage, get_conversation_lock
  ```
  Save verification to `tests/stability_results/task_003_core_modules_verified.json`.

- [ ] FIX IF NEEDED: Check `app/core/__init__.py` exports and fix any import errors.

### ==========================================================
### PHASE 2: Basic Conversation Flow Tests
### ==========================================================

### Task 004: Funding Call Search Flow
- [ ] TEST: Run `tests/scenarios/basic_flows/funding_call_search.yaml` scenario using `ConversationFlowAgent`. Verify:
  - All 3 messages complete without errors
  - `search_funding_calls` tool is used
  - Follow-up references are resolved
  Save result to `tests/stability_results/task_004_funding_call_search.json`.

- [ ] FIX IF NEEDED: If scenario fails, check tool execution, follow-up resolution, and response formatting. Use `mapit-tools` skill patterns.

### Task 005: Project Search Flow
- [ ] TEST: Run `tests/scenarios/basic_flows/project_search.yaml` scenario. Verify:
  - All 4 messages complete
  - `search_projects` tool is used
  - "first project" reference is resolved
  Save result to `tests/stability_results/task_005_project_search.json`.

- [ ] FIX IF NEEDED: If fails, check project search tool and numbered reference resolution in `conversation_manager.py`.

### Task 006: Budget Calculation Flow
- [ ] TEST: Run `tests/scenarios/basic_flows/budget_calculation.yaml` scenario. Verify:
  - Budget tool is used
  - Benchmark comparison tool is used
  - Context is maintained across turns
  Save result to `tests/stability_results/task_006_budget_calculation.json`.

- [ ] FIX IF NEEDED: If fails, check `calculate_budget` and `get_budget_benchmark` tools.

### ==========================================================
### PHASE 3: Follow-Up Handling Tests
### ==========================================================

### Task 007: Follow-Up by Number Reference
- [ ] TEST: Run `tests/scenarios/follow_up/follow_up_by_number.yaml` scenario. Verify:
  - "third one" reference resolves correctly
  - "first one" comparison reference works
  - "number 5" reference works
  Save result to `tests/stability_results/task_007_follow_up_by_number.json`.

- [ ] FIX IF NEEDED: Check `_resolve_follow_up_references()` in conversation_manager.py. Ensure previous results are in context.

### Task 008: Follow-Up More Details
- [ ] TEST: Run `tests/scenarios/follow_up/follow_up_more_details.yaml` scenario. Verify:
  - "Tell me more" continues same topic
  - "elaborate" requests are handled
  - Topic context is preserved
  Save result to `tests/stability_results/task_008_follow_up_more_details.json`.

- [ ] FIX IF NEEDED: Check context formatting in `_format_conversation_for_agent()`.

### ==========================================================
### PHASE 4: Context Preservation Tests
### ==========================================================

### Task 009: Long Conversation (10+ Turns)
- [ ] TEST: Run `tests/scenarios/context/long_conversation.yaml` scenario. Verify:
  - All 10 messages complete
  - Final message can recall initial topic ("climate research")
  - Quality doesn't degrade significantly
  Use `QualityEvaluatorAgent` to check quality trends. Save result to `tests/stability_results/task_009_long_conversation.json`.

- [ ] FIX IF NEEDED: If context degrades, check STM capacity (12 turns), LTM summarization, and context truncation limits.

### Task 010: Context Integrity Validation
- [ ] TEST: After running Task 009, use `ContextValidatorAgent` to verify:
  - Message count matches in DB and Redis
  - Message order is preserved
  - No split-brain condition detected
  Save result to `tests/stability_results/task_010_context_integrity.json`.

- [ ] FIX IF NEEDED: If integrity fails, integrate `AtomicMessageStorage` into conversation_manager.py to ensure atomic storage.

### ==========================================================
### PHASE 5: Error Recovery Tests
### ==========================================================

### Task 011: Invalid Reference Handling
- [ ] TEST: Run `tests/scenarios/error_recovery/invalid_reference.yaml` scenario. Verify:
  - "50th one" (invalid) is handled gracefully
  - "purple call" (nonsense) doesn't crash
  - Recovery to valid reference works
  Save result to `tests/stability_results/task_011_invalid_reference.json`.

- [ ] FIX IF NEEDED: Add graceful error handling for invalid references. Should clarify and ask user to rephrase.

### Task 012: Tool Failure Recovery
- [ ] TEST: Create scenario that simulates tool timeout/failure. Verify:
  - Agent retries or falls back gracefully
  - User gets informative error message
  - Conversation can continue after failure
  Save result to `tests/stability_results/task_012_tool_failure.json`.

- [ ] FIX IF NEEDED: Check circuit breaker usage in tool execution. Add proper fallback messages.

### ==========================================================
### PHASE 6: Concurrent Access Tests
### ==========================================================

### Task 013: Rapid Message Sequence
- [ ] TEST: Run `tests/scenarios/concurrent/rapid_messages.yaml` scenario with 100ms delays. Verify:
  - All 5 messages are stored
  - No message loss
  - Order is preserved
  Save result to `tests/stability_results/task_013_rapid_messages.json`.

- [ ] FIX IF NEEDED: If messages are lost, ensure `_store_user_message` commits immediately and STM updates are synchronous.

### Task 014: Concurrent Messages (Same Conversation)
- [ ] TEST: Use `ConversationFlowAgent.run_concurrent_messages()` to send 3 messages simultaneously to same conversation. Verify:
  - No errors (some failures acceptable)
  - Messages don't corrupt each other
  - Context remains valid after concurrent access
  Use `ContextValidatorAgent.detect_race_condition()`. Save result to `tests/stability_results/task_014_concurrent_messages.json`.

- [ ] FIX IF NEEDED: Integrate `ConversationLockManager` into conversation_manager.py:
  ```python
  async with get_conversation_lock(conversation_id):
      # Process message
  ```

### Task 015: Interleaved Conversations
- [ ] TEST: Create test that switches between 3 different conversations rapidly. Verify:
  - Each conversation maintains its own context
  - No cross-contamination between conversations
  - All conversations complete successfully
  Save result to `tests/stability_results/task_015_interleaved_conversations.json`.

- [ ] FIX IF NEEDED: Ensure conversation_id is properly isolated in all memory operations.

### ==========================================================
### PHASE 7: Quality Evaluation Tests
### ==========================================================

### Task 016: Single Response Quality
- [ ] TEST: Send query "What is EIC Accelerator and who can apply?" via `ConversationFlowAgent`. Evaluate response with `QualityEvaluatorAgent`. Verify:
  - Score >= 75/100
  - Query fulfillment >= 30/40
  - Contains specific details (budget, eligibility)
  Save result to `tests/stability_results/task_016_single_quality.json`.

- [ ] FIX IF NEEDED: If quality low, check V3ResponseFormatter and agent synthesis.

### Task 017: Conversation Quality Stability
- [ ] TEST: Run 5-turn conversation about Horizon Europe funding. Use `QualityEvaluatorAgent.evaluate_conversation()`. Verify:
  - Average score >= 70/100
  - No quality degradation > 15 points between turns
  - Trend is "stable" or "improving"
  Save result to `tests/stability_results/task_017_conversation_quality.json`.

- [ ] FIX IF NEEDED: If quality degrades, check context truncation limits and summarization quality.

### ==========================================================
### PHASE 8: Integration with Existing Tests
### ==========================================================

### Task 018: Integrate with Quality Evaluation Suite
- [ ] INTEGRATE: Add conversation flow validation to existing `tests/quality/` tests. For each prompt test:
  - After getting response, verify context was stored
  - Check no errors in SSE stream
  - Log any storage warnings
  Save integration plan to `tests/stability_results/task_018_quality_integration.json`.

- [ ] FIX IF NEEDED: Update quality test fixtures to use shared conftest.py fixtures.

### Task 019: Regression Test Suite
- [ ] CREATE: Based on all scenarios tested, create regression test suite that runs on every PR:
  - Fast tests (< 30s): basic flows, simple follow-ups
  - Medium tests (< 2min): long conversations, concurrent tests
  - Full tests (< 10min): all scenarios
  Save configuration to `tests/stability_results/task_019_regression_suite.json`.

- [ ] FIX IF NEEDED: Add pytest markers for test categories. Update CI configuration.

### Task 020: Documentation Update
- [ ] DOCUMENT: Update `docs/MAPIT_IMPROVEMENT_REPORT.md` with:
  - Test results summary
  - Fixed issues and their solutions
  - Remaining known issues
  - Performance metrics
  Save summary to `tests/stability_results/task_020_documentation.json`.

- [ ] FIX IF NEEDED: Ensure all fixes are documented with code locations and rationale.

### ==========================================================
### PHASE 9: Critical Bug Fixes
### ==========================================================

### Task 021: Fix Split-Brain Message Storage
- [ ] IMPLEMENT: Integrate `AtomicMessageStorage` into `conversation_manager.py`:
  - Replace `_store_user_message` calls with `atomic_storage.store_user_message()`
  - Replace `_store_assistant_message` calls with `atomic_storage.store_assistant_message()`
  - Ensure DB is stored BEFORE response is sent
  Save implementation to `tests/stability_results/task_021_atomic_storage.json`.

- [ ] VERIFY: Run `ContextValidatorAgent` tests to confirm no more split-brain conditions.

### Task 022: Fix Streaming Before Storage
- [ ] IMPLEMENT: In `_stream_v3_response()`, move assistant message storage BEFORE token streaming:
  ```python
  # Store first
  assistant_message_id = await atomic_storage.store_assistant_message(...)
  # Then stream
  for chunk in answer:
      yield {"type": "token", "content": chunk}
  ```
  Save implementation to `tests/stability_results/task_022_storage_before_streaming.json`.

- [ ] VERIFY: Run concurrent tests to confirm responses are always persisted.

### Task 023: Add Conversation Locking
- [ ] IMPLEMENT: Wrap message processing in `ConversationLockManager`:
  ```python
  async def process_message_v3(...):
      async with get_conversation_lock(conversation_id):
          # All processing here
  ```
  Save implementation to `tests/stability_results/task_023_conversation_locking.json`.

- [ ] VERIFY: Run concurrent message tests to confirm no race conditions.

### Task 024: Replace Silent Redis Fallback
- [ ] IMPLEMENT: Update `MemoryService._create_fallback_redis()` to:
  - Log ERROR level warnings (not just INFO)
  - Set a `_fallback_mode` flag
  - Expose degraded state via health check
  Save implementation to `tests/stability_results/task_024_redis_fallback.json`.

- [ ] VERIFY: Test that Redis failure is visible in health checks and logs.

### Task 025: Fix Context Window Memory Leak
- [ ] IMPLEMENT: In `ToolAwareAgent`, ensure `ContextWindowManager.reset()` is called at start of each query:
  ```python
  async def process_query(self, ...):
      self.context_manager.reset()  # Reset at start
      # ... rest of processing
  ```
  Save implementation to `tests/stability_results/task_025_context_reset.json`.

- [ ] VERIFY: Run long conversation tests to confirm context doesn't accumulate.

---

## Summary

| Phase | Tasks | Focus Area |
|-------|-------|------------|
| 1 | 001-003 | Infrastructure Setup |
| 2 | 004-006 | Basic Conversation Flows |
| 3 | 007-008 | Follow-Up Handling |
| 4 | 009-010 | Context Preservation |
| 5 | 011-012 | Error Recovery |
| 6 | 013-015 | Concurrent Access |
| 7 | 016-017 | Quality Evaluation |
| 8 | 018-020 | Integration & Documentation |
| 9 | 021-025 | Critical Bug Fixes |

**Total: 25 tasks**

---

## Post-Run Actions

After completing all tasks:

1. Review `tests/stability_results/` for all JSON files
2. Generate summary report:
   ```bash
   pytest tests/test_conversation_scenarios.py -v --json-report --json-report-file=tests/stability_results/final_report.json
   ```
3. Check for any tasks that failed after 3 fix attempts
4. Document patterns in failures for future improvement
5. Update CI/CD pipeline to run stability tests on PRs
6. Schedule nightly full stability test runs

---

## Test Agent Quick Reference

### When Debugging Failures

| Failure Type | Agent to Use | What to Check |
|--------------|--------------|---------------|
| Messages not stored | `ContextValidatorAgent` | DB/Redis consistency |
| Follow-up broken | `ConversationFlowAgent` | Context contains previous results |
| Quality degradation | `QualityEvaluatorAgent` | Score trends across turns |
| Race condition | `ContextValidatorAgent` | `detect_race_condition()` |
| Tool timeout | `ConversationFlowAgent` | SSE events for errors |
| Context lost | `ContextValidatorAgent` | `validate_context_integrity()` |

### Test Pipeline

```
Scenario YAML
    ↓
[ConversationFlowAgent] → Runs conversation, collects events
    ↓
[ContextValidatorAgent] → Validates DB/Redis consistency
    ↓
[QualityEvaluatorAgent] → Scores response quality
    ↓
Test Result (PASS/FAIL + details)
```

---

## Files Created by This PRD

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Shared pytest fixtures |
| `tests/agents/__init__.py` | Agent exports |
| `tests/agents/conversation_flow_agent.py` | Multi-turn conversation simulator |
| `tests/agents/context_validator_agent.py` | DB/Redis consistency checker |
| `tests/agents/quality_evaluator_agent.py` | LLM-as-judge quality scorer |
| `tests/scenarios/basic_flows/*.yaml` | Basic flow scenarios |
| `tests/scenarios/follow_up/*.yaml` | Follow-up handling scenarios |
| `tests/scenarios/context/*.yaml` | Context preservation scenarios |
| `tests/scenarios/error_recovery/*.yaml` | Error recovery scenarios |
| `tests/scenarios/concurrent/*.yaml` | Concurrent access scenarios |
| `tests/test_conversation_scenarios.py` | Scenario test runner |
| `app/core/conversation_lock.py` | Conversation locking module |
| `app/core/atomic_storage.py` | Atomic message storage module |
| `docs/MAPIT_IMPROVEMENT_REPORT.md` | Detailed analysis report |
