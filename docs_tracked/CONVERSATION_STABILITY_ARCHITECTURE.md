# Conversation Stability Architecture

This document describes the architecture of the MAPIT conversation stability system, which ensures reliable multi-turn conversations by preventing race conditions, maintaining context integrity, and providing comprehensive automated testing.

## Table of Contents

1. [Overview](#overview)
2. [Lock Manager Design](#lock-manager-design)
3. [Atomic Storage Design](#atomic-storage-design)
4. [Test Agent Architecture](#test-agent-architecture)
5. [Scenario Format Specification](#scenario-format-specification)

---

## Overview

The conversation stability system addresses several critical challenges in multi-turn conversational AI:

| Challenge | Solution |
|-----------|----------|
| Race conditions from rapid messages | `ConversationLockManager` - per-conversation async locks |
| Split-brain storage (DB/Redis divergence) | `AtomicMessageStorage` - atomic operations with DB as source of truth |
| Context loss in follow-up queries | Storage-before-streaming pattern |
| Silent failures hiding real issues | Explicit error reporting with warnings |
| Quality degradation over conversations | `QualityEvaluatorAgent` with degradation detection |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     MAPIT Conversation API                       │
│                                                                  │
│  ┌────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │ ConversationLock│───▶│ AtomicMessage   │───▶│ Response     │ │
│  │ Manager         │    │ Storage         │    │ Generator    │ │
│  └────────────────┘    └─────────────────┘    └──────────────┘ │
│          │                      │                              │
│          ▼                      ▼                              │
│  ┌────────────────┐    ┌───────────────────────────┐          │
│  │ Lock Per       │    │ DB (PostgreSQL)  │ Memory │          │
│  │ Conversation   │    │ Source of Truth  │ (Redis)│          │
│  └────────────────┘    └───────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     Test Agent Infrastructure                    │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐│
│  │ConversationFlow│  │ContextValidator│  │ QualityEvaluator   ││
│  │Agent           │  │Agent           │  │ Agent              ││
│  └────────────────┘  └────────────────┘  └────────────────────┘│
│         │                   │                     │            │
│         ▼                   ▼                     ▼            │
│  ┌────────────────────────────────────────────────────────────┐│
│  │                  YAML Scenario Files                       ││
│  └────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Lock Manager Design

### Purpose

The `ConversationLockManager` (`app/core/conversation_lock.py`) prevents race conditions when multiple messages arrive for the same conversation simultaneously.

### Design Principles

1. **Per-Conversation Locking**: Each conversation has its own independent lock
2. **Async-Safe**: Uses `asyncio.Lock` for proper async context handling
3. **Timeout Support**: Prevents deadlocks with configurable timeouts
4. **Automatic Cleanup**: Stale locks are detected and released

### Class Structure

```python
@dataclass
class LockInfo:
    """Information about an active lock."""
    conversation_id: int
    acquired_at: datetime
    holder_id: str
    request_count: int = 0

class ConversationLockManager:
    """Manages conversation-level locks to prevent race conditions."""

    # Singleton pattern for global lock coordination
    _instance: Optional['ConversationLockManager'] = None

    # Internal state
    _locks: Dict[int, asyncio.Lock]      # Lock per conversation
    _lock_info: Dict[int, LockInfo]       # Debugging info
    _manager_lock: asyncio.Lock           # Protects internal state
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `get_instance()` | Get singleton instance (async) |
| `acquire(conversation_id, timeout, holder_id)` | Acquire lock with timeout |
| `is_locked(conversation_id)` | Check if conversation is locked |
| `get_lock_info(conversation_id)` | Get debugging info for lock |
| `cleanup_stale_locks(max_age_seconds)` | Release locks held too long |
| `get_stats()` | Get usage statistics |

### Usage Pattern

```python
from app.core import get_conversation_lock

async def process_message_with_lock(conversation_id: int, message: str):
    """Process a message with lock protection."""
    async with get_conversation_lock(conversation_id, timeout=60.0):
        # Only one request can be here at a time for this conversation
        result = await handle_message(conversation_id, message)
        await store_result(conversation_id, result)
    return result
```

### Lock Behavior

1. **Acquisition**: First request acquires immediately; subsequent requests wait
2. **Timeout**: If lock cannot be acquired within timeout, `TimeoutError` is raised
3. **Release**: Lock is always released in `finally` block, even on exception
4. **Logging**: Long waits (>1s) are logged as warnings

### Stale Lock Detection

Locks held longer than `max_age_seconds` (default: 300s) are considered stale:

```python
await manager.cleanup_stale_locks(max_age_seconds=300)
```

This should be called periodically (e.g., via background task) to prevent deadlocks from crashed processes.

---

## Atomic Storage Design

### Purpose

The `AtomicMessageStorage` (`app/core/atomic_storage.py`) ensures messages are stored consistently across PostgreSQL (source of truth) and Redis (cache) with proper error reporting.

### Design Principles

1. **DB as Source of Truth**: PostgreSQL is authoritative; Redis is a cache
2. **Fail-Fast on DB Errors**: If DB storage fails, the entire operation fails
3. **Warn-Only on Redis Errors**: Redis failures are logged but don't fail the operation
4. **Transaction Support**: Message pairs can be stored atomically
5. **Duplicate Detection**: Prevents storing the same message twice within 5 seconds

### Class Structure

```python
@dataclass
class StorageResult:
    """Result of a storage operation."""
    success: bool
    user_message_id: Optional[int] = None
    assistant_message_id: Optional[int] = None
    db_stored: bool = False
    memory_stored: bool = False
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

class AtomicMessageStorage:
    """Provides atomic storage operations for conversation messages."""

    def __init__(self, db_pool, memory_service):
        self.db_pool = db_pool
        self.memory_service = memory_service
        self._fallback_mode = False
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `store_user_message(...)` | Store a single user message |
| `store_assistant_message(...)` | Store a single assistant message |
| `store_message_pair(...)` | Store both messages atomically |
| `verify_storage(...)` | Verify message was stored correctly |
| `is_degraded` | Check if operating in fallback mode |

### Storage Flow

```
┌─────────────────────┐
│  Store Request      │
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  Check for Duplicate│───Yes──▶ Return existing ID
└─────────────────────┘
          │ No
          ▼
┌─────────────────────┐
│  Store to PostgreSQL│───Fail──▶ Return Error (no rollback needed)
└─────────────────────┘
          │ Success
          ▼
┌─────────────────────┐
│  Store to Redis     │───Fail──▶ Log Warning, Continue
└─────────────────────┘
          │ Success
          ▼
┌─────────────────────┐
│  Return Success     │
└─────────────────────┘
```

### Transaction Pattern for Message Pairs

```python
async def store_message_pair(self, conversation_id, user_id,
                             user_message, assistant_message, citations=None):
    """Store both messages in a single transaction."""
    conn = self.db_pool.getconn()
    try:
        cursor = conn.cursor()

        # Insert user message
        cursor.execute("""
            INSERT INTO message (conversation_id, sender, text, created_at)
            VALUES (%s, 'user', %s, NOW()) RETURNING id
        """, (conversation_id, user_message))
        user_id = cursor.fetchone()[0]

        # Insert assistant message
        cursor.execute("""
            INSERT INTO message (conversation_id, sender, text, created_at)
            VALUES (%s, 'assistant', %s, NOW()) RETURNING id
        """, (conversation_id, assistant_message))
        assistant_id = cursor.fetchone()[0]

        conn.commit()  # Atomic commit

    except Exception:
        conn.rollback()  # Atomic rollback
        raise
```

### Duplicate Detection

Prevents race condition duplicates within a 5-second window:

```sql
SELECT id FROM message
WHERE conversation_id = %s
  AND sender = %s
  AND text = %s
  AND created_at > NOW() - INTERVAL '5 seconds'
ORDER BY created_at DESC
LIMIT 1
```

### Memory Storage

Messages are stored in Redis short-term memory (STM) as `ConversationTurn` objects:

```python
from app.services.memory.short_term_memory import ConversationTurn

turn = ConversationTurn(
    message_id=message_id,
    role='user',  # or 'assistant'
    content=message,
    timestamp=datetime.now()
)
self.memory_service.stm.add_turn(conversation_id, turn)
```

### Degraded Mode Detection

The storage system tracks when it's operating in a degraded state:

```python
@property
def is_degraded(self) -> bool:
    """Check if storage is operating in degraded mode."""
    return self._fallback_mode or self.db_pool is None
```

---

## Test Agent Architecture

The test infrastructure consists of three specialized agents that work together to validate conversation stability.

### Agent Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    Test Agent Ecosystem                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ConversationFlowAgent                                           │
│  ├── Simulates multi-turn conversations                          │
│  ├── Collects SSE events                                         │
│  ├── Tracks tools used and results                               │
│  └── Runs complete scenarios from YAML                           │
│                                                                  │
│  ContextValidatorAgent                                           │
│  ├── Validates DB/Redis consistency                              │
│  ├── Detects race conditions                                     │
│  ├── Checks message ordering                                     │
│  └── Validates follow-up context preservation                    │
│                                                                  │
│  QualityEvaluatorAgent                                           │
│  ├── Scores responses using LLM-as-judge                         │
│  ├── Tracks quality across conversations                         │
│  ├── Detects quality degradation                                 │
│  └── Provides detailed feedback                                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 1. ConversationFlowAgent

**Location**: `tests/agents/conversation_flow_agent.py`

**Purpose**: Simulates real user interactions with the MAPIT API.

#### Key Classes

```python
@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation."""
    user_message: str
    response_text: str = ""
    events: list[dict] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    error: str | None = None
    processing_time_ms: float = 0.0

@dataclass
class ScenarioResult:
    """Result of running a conversation scenario."""
    scenario_name: str
    passed: bool = True
    validations: list[ValidationResult] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    turns: list[ConversationTurn] = field(default_factory=list)
    duration_ms: float = 0.0
```

#### Key Methods

| Method | Purpose |
|--------|---------|
| `send_message(message)` | Send message and collect streaming response |
| `send_message_non_streaming(message)` | Send via non-streaming endpoint |
| `get_context()` | Get current conversation context |
| `clear_context()` | Clear conversation memory |
| `run_scenario(scenario)` | Execute complete YAML scenario |
| `run_concurrent_messages(messages)` | Send multiple messages concurrently |

#### SSE Event Processing

The agent processes Server-Sent Events from the streaming API:

```python
async for line in response.content:
    line = line.decode("utf-8").strip()
    if line.startswith("data: "):
        event = json.loads(line[6:])

        if event["type"] == "token":
            turn.response_text += event["content"]
        elif event["type"] == "tool_call":
            turn.tools_used.append(event["tool"])
        elif event["type"] == "tool_result":
            turn.tool_results.append(event["result"])
        elif event["type"] == "complete":
            turn.metadata = event["metadata"]
        elif event["type"] == "error":
            turn.error = event["message"]
```

### 2. ContextValidatorAgent

**Location**: `tests/agents/context_validator_agent.py`

**Purpose**: Validates conversation state consistency across storage systems.

#### Key Classes

```python
@dataclass
class IntegrityResult:
    """Result of a full integrity check."""
    conversation_id: str
    is_consistent: bool = True
    message_count_match: bool = True
    order_preserved: bool = True
    content_match: bool = True
    db_message_count: int = 0
    redis_turn_count: int = 0
    api_message_count: int = 0

@dataclass
class RaceConditionResult:
    """Result of race condition detection."""
    conversation_id: str
    detected: bool = False
    expected_sequence: list[str] = field(default_factory=list)
    actual_sequence: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    out_of_order_pairs: list[tuple] = field(default_factory=list)
```

#### Key Methods

| Method | Purpose |
|--------|---------|
| `validate_message_stored(conv_id, content)` | Check message exists in DB and Redis |
| `validate_context_integrity(conv_id)` | Full consistency check |
| `detect_race_condition(conv_id, expected)` | Detect out-of-order processing |
| `validate_follow_up_context(conv_id, orig, follow)` | Check context preserved |
| `wait_for_consistency(conv_id, count, timeout)` | Wait for eventual consistency |

#### Consistency Checks

1. **Message Count**: DB and Redis have expected message counts
2. **Message Order**: Messages appear in correct sequence
3. **Content Match**: Overlapping messages have matching content
4. **API Context**: API endpoint returns consistent data

### 3. QualityEvaluatorAgent

**Location**: `tests/agents/quality_evaluator_agent.py`

**Purpose**: Evaluates response quality using LLM-as-judge methodology.

#### Scoring Dimensions

| Dimension | Max Points | Description |
|-----------|------------|-------------|
| Query Fulfillment | 40 | Does the response fully address the user's question? |
| Specificity | 25 | Is the response specific and detailed rather than vague? |
| Factual Accuracy | 25 | Is the information factually correct and verifiable? |
| Actionability | 10 | Can the user take action based on this response? |

#### Key Classes

```python
@dataclass
class QualityScore:
    """Complete quality score for a response."""
    total_score: int
    max_score: int
    dimension_scores: Dict[str, DimensionScore] = field(default_factory=dict)
    passed: bool = False
    feedback: str = ""

@dataclass
class ConversationQualityResult:
    """Quality evaluation result for a full conversation."""
    turn_scores: list[QualityScore] = field(default_factory=list)
    average_score: float = 0.0
    degradation_detected: bool = False
    degradation_turn: int = -1
    trend: str = "stable"  # "improving", "stable", "degrading"
```

#### Key Methods

| Method | Purpose |
|--------|---------|
| `evaluate_response(query, response)` | LLM-based single response evaluation |
| `evaluate_conversation(turns)` | Evaluate full conversation with trends |
| `quick_evaluate(response, patterns)` | Fast rule-based evaluation |
| `compare_responses(query, a, b)` | Compare two responses |

#### Degradation Detection

Quality degradation is detected when:
- A turn's score drops 15+ points from the previous turn
- The trend over the conversation shows declining scores

```python
for i in range(1, len(scores)):
    drop = scores[i - 1] - scores[i]
    if drop >= 15:
        result.degradation_detected = True
        result.degradation_turn = i
        break
```

---

## Scenario Format Specification

Test scenarios are defined in YAML files under `tests/scenarios/`.

### Directory Structure

```
tests/scenarios/
├── basic_flows/
│   ├── funding_call_search.yaml
│   ├── project_search.yaml
│   ├── budget_calculation.yaml
│   └── timeline_generation.yaml
├── follow_up/
│   ├── follow_up_by_number.yaml
│   ├── follow_up_more_details.yaml
│   └── follow_up_comparison.yaml
├── context/
│   ├── long_conversation.yaml
│   ├── topic_switching.yaml
│   └── memory_overflow.yaml
├── error_recovery/
│   ├── invalid_reference.yaml
│   ├── ambiguous_query.yaml
│   └── tool_timeout.yaml
└── concurrent/
    └── rapid_messages.yaml
```

### YAML Schema

```yaml
# Required metadata
name: "Scenario Name"
description: "What this scenario tests"
tags: ["tag1", "tag2"]  # For filtering tests
stop_on_error: true     # Stop on first failure

# Conversation steps
steps:
  - message: "User message text"
    delay_ms: 0  # Delay before sending (milliseconds)
    validations:
      - type: "validation_type"
        name: "validation_name"
        # Type-specific parameters...

# Final validations run after all steps
final_validations:
  - type: "context_integrity"
    name: "check_name"
    description: "What this checks"
```

### Validation Types

#### Response Validations

| Type | Parameters | Description |
|------|------------|-------------|
| `response_contains` | `patterns: [str]` | ALL patterns must appear in response |
| `response_contains_any` | `patterns: [str]` | At least ONE pattern must appear |
| `tools_used` | `expected: [str]` | Specified tools must be called |
| `min_results` | `count: int` | Tool results must have minimum count |
| `no_error` | (none) | Response must not contain errors |
| `has_metadata` | (none) | Response must include metadata |

#### Context Validations

| Type | Parameters | Description |
|------|------------|-------------|
| `follow_up_resolved` | (none) | Message references previous results |
| `context_preserved` | `from_turn: int` | Context from turn N is still accessible |

#### Final Validations

| Type | Parameters | Description |
|------|------------|-------------|
| `context_integrity` | (none) | All messages stored properly in DB/Redis |
| `quality_non_degradation` | (none) | Quality doesn't drop > 15 points |

### Example Scenario

```yaml
name: "Funding Call Search"
description: "User searches for calls and asks follow-ups"
tags: ["basic", "calls", "search"]
stop_on_error: true

steps:
  - message: "Find me open funding calls for hydrogen research"
    validations:
      - type: "response_contains"
        name: "mentions_funding"
        patterns: ["funding", "call"]
      - type: "tools_used"
        name: "uses_call_search"
        expected: ["search_funding_calls"]
      - type: "no_error"
        name: "no_errors"
    delay_ms: 0

  - message: "What are the deadlines?"
    validations:
      - type: "response_contains_any"
        name: "mentions_deadline"
        patterns: ["deadline", "date", "2025", "2026"]
      - type: "no_error"
        name: "no_errors"
    delay_ms: 500

  - message: "Tell me about the first one"
    validations:
      - type: "follow_up_resolved"
        name: "resolves_reference"
      - type: "no_error"
        name: "no_errors"
    delay_ms: 500

final_validations:
  - type: "context_integrity"
    name: "context_preserved"
  - type: "quality_non_degradation"
    name: "quality_stable"
```

### Running Scenarios

```bash
# All scenarios
pytest tests/test_conversation_scenarios.py -v

# By category tag
pytest tests/test_conversation_scenarios.py -k "basic" -v
pytest tests/test_conversation_scenarios.py -k "follow_up" -v
pytest tests/test_conversation_scenarios.py -k "concurrent" -v

# Specific scenario file
pytest tests/test_conversation_scenarios.py -k "funding_call_search" -v

# With live API
TEST_API_URL=http://localhost:8000 pytest tests/test_conversation_scenarios.py -v
```

### Creating New Scenarios

1. **Choose the right category**:
   - `basic_flows/` - Standard single-purpose interactions
   - `follow_up/` - Testing reference resolution
   - `context/` - Long conversations, topic changes
   - `error_recovery/` - Edge cases and errors
   - `concurrent/` - Race conditions, parallel messages

2. **Define clear validations**: Each step should validate something specific

3. **Use appropriate delays**: `delay_ms` simulates realistic user behavior

4. **Include final validations**: Always check `context_integrity` and `quality_non_degradation`

5. **Add meaningful tags**: Enable selective test runs

---

## Integration Guide

This section describes how to integrate the stability modules into new code.

### Integrating Lock Manager

When adding new API endpoints that process conversation messages:

```python
from app.core import get_conversation_lock

@router.post("/api/v3/conversation/{conversation_id}/message/stream")
async def stream_message(conversation_id: int, request: MessageRequest):
    """Stream a message response with lock protection."""
    try:
        async with get_conversation_lock(conversation_id, timeout=60.0):
            async for event in conversation_manager.process_message_v3(
                conversation_id=conversation_id,
                user_message=request.message,
                user_id=request.user_id,
                streaming=True
            ):
                yield event
    except TimeoutError:
        yield {
            "type": "error",
            "message": "Another message is being processed for this conversation"
        }
```

### Integrating Atomic Storage

When storing messages in conversation processing:

```python
from app.core import get_atomic_storage

class ConversationManager:
    def __init__(self, db_pool, memory_service):
        self.storage = get_atomic_storage(db_pool, memory_service)

    async def process_message_v3_streaming(
        self,
        conversation_id: int,
        user_id: int,
        message: str
    ):
        # 1. Store user message BEFORE processing
        user_result = await self.storage.store_user_message(
            conversation_id=conversation_id,
            user_id=user_id,
            message=message
        )
        if not user_result.success:
            yield {"type": "error", "message": user_result.error}
            return

        # 2. Process with agent and collect response
        response_text = ""
        async for event in self.agent.process(message):
            if event["type"] == "token":
                response_text += event["content"]
            yield event

        # 3. Store assistant message BEFORE completing
        assistant_result = await self.storage.store_assistant_message(
            conversation_id=conversation_id,
            message=response_text
        )
        if not assistant_result.success:
            yield {"type": "error", "message": assistant_result.error}
            return

        yield {"type": "complete", "metadata": {...}}
```

### Writing New Test Scenarios

1. Create a YAML file in the appropriate `tests/scenarios/` subdirectory
2. Follow the schema documented above
3. Test locally before committing:

```bash
# Test your scenario
pytest tests/test_conversation_scenarios.py -k "your_scenario_name" -v

# With verbose output
pytest tests/test_conversation_scenarios.py -k "your_scenario_name" -v -s
```

### Using Test Agents in Custom Tests

```python
import pytest
from tests.agents import (
    ConversationFlowAgent,
    ContextValidatorAgent,
    QualityEvaluatorAgent
)

@pytest.fixture
async def flow_agent():
    return ConversationFlowAgent("http://localhost:8000")

@pytest.fixture
async def validator():
    async with ContextValidatorAgent(
        database_url="postgresql://...",
        redis_url="redis://...",
        api_base_url="http://localhost:8000"
    ) as v:
        yield v

async def test_my_conversation(flow_agent, validator):
    # Send messages
    turn1 = await flow_agent.send_message("Find hydrogen projects")
    assert not turn1.has_error

    # Validate storage
    result = await validator.validate_message_stored(
        str(flow_agent.conversation_id),
        "hydrogen"
    )
    assert result.passed
```

---

## Debugging Guide

### Common Issues and Solutions

#### Issue: Race Condition Detected

**Symptoms**:
- Missing messages in conversation
- Out-of-order messages
- Duplicate messages

**Debugging**:
```python
from tests.agents import ContextValidatorAgent

async with ContextValidatorAgent(...) as validator:
    race = await validator.detect_race_condition(
        conversation_id=str(conv_id),
        expected_sequence=["msg1", "msg2", "msg3"]
    )

    if race.detected:
        print(f"Missing: {race.missing}")
        print(f"Duplicates: {race.duplicates}")
        print(f"Out of order pairs: {race.out_of_order_pairs}")
```

**Solution**: Ensure `get_conversation_lock()` is used at the API route level.

#### Issue: Context Loss in Follow-ups

**Symptoms**:
- "I don't have context about that" responses
- Follow-up queries fail to reference previous results

**Debugging**:
```python
from tests.agents import ContextValidatorAgent

async with ContextValidatorAgent(...) as validator:
    result = await validator.validate_follow_up_context(
        conversation_id=str(conv_id),
        original_response="The first call is HORIZON-CL5...",
        follow_up_query="Tell me more about it"
    )

    print(f"Found in recent: {result.details['found_in_recent']}")
    print(f"Found in summary: {result.details['found_in_summary']}")
```

**Solution**: Ensure messages are stored BEFORE streaming the response.

#### Issue: Split-Brain Storage (DB/Redis Divergence)

**Symptoms**:
- API returns different data than database queries
- Context seems inconsistent

**Debugging**:
```python
from tests.agents import ContextValidatorAgent

async with ContextValidatorAgent(...) as validator:
    integrity = await validator.validate_context_integrity(str(conv_id))

    print(f"DB count: {integrity.db_message_count}")
    print(f"Redis count: {integrity.redis_turn_count}")
    print(f"API count: {integrity.api_message_count}")
    print(f"Consistent: {integrity.is_consistent}")

    for v in integrity.validation_results:
        if not v.passed:
            print(f"FAILED: {v.check_name} - {v.message}")
```

**Solution**: Use `AtomicMessageStorage` for all message writes.

#### Issue: Quality Degradation

**Symptoms**:
- Later responses in conversation are vague
- Quality drops significantly over time

**Debugging**:
```python
from tests.agents import QualityEvaluatorAgent

evaluator = QualityEvaluatorAgent()
result = await evaluator.evaluate_conversation(turns)

print(f"Trend: {result.trend}")
print(f"Degradation detected: {result.degradation_detected}")
if result.degradation_detected:
    print(f"At turn: {result.degradation_turn}")
    print(f"Drop: {result.degradation_amount} points")
```

**Solution**: Check context window management and STM capacity limits.

### Log Messages to Monitor

| Log Pattern | Indicates |
|-------------|-----------|
| `Lock for conversation X acquired after Y.Zs wait` | Lock contention (normal if < 5s) |
| `Stale lock detected for conversation X` | Potential deadlock or crashed request |
| `Memory service is using FallbackRedis` | Redis unavailable (degraded mode) |
| `Database storage failed: ...` | Critical - data loss risk |
| `Memory storage failed (DB succeeded)` | Non-critical - cache miss possible |
| `Reusing existing message ID: X` | Duplicate detection working |
| `Force-released stale lock for conversation X` | Stale lock cleanup occurred |

### API Endpoints for Debugging

```bash
# Get conversation context
curl http://localhost:8000/api/v3/conversation/123/context

# Clear conversation context
curl -X DELETE http://localhost:8000/api/v3/conversation/123/context

# Health check
curl http://localhost:8000/api/v3/conversation/health
```

### Running Diagnostic Tests

```bash
# Run all stability tests
pytest tests/test_conversation_scenarios.py -v

# Run regression tests for specific fixes
pytest tests/test_conversation_regression.py -v

# Run with maximum verbosity
pytest tests/test_conversation_scenarios.py -v -s --log-cli-level=DEBUG

# Run specific category
pytest tests/test_conversation_scenarios.py -k "concurrent" -v
```

---

## Summary

The conversation stability architecture provides:

1. **Lock Manager**: Prevents race conditions with per-conversation async locks
2. **Atomic Storage**: Ensures consistent storage with DB as source of truth
3. **Test Agents**: Three specialized agents for comprehensive testing
4. **YAML Scenarios**: Declarative test definitions for maintainability

### Key Files Reference

| File | Purpose |
|------|---------|
| `app/core/conversation_lock.py` | Per-conversation async locks |
| `app/core/atomic_storage.py` | Atomic message storage |
| `tests/agents/conversation_flow_agent.py` | Multi-turn conversation simulation |
| `tests/agents/context_validator_agent.py` | DB/Redis consistency validation |
| `tests/agents/quality_evaluator_agent.py` | LLM-as-judge quality scoring |
| `tests/test_conversation_scenarios.py` | Main scenario test runner |
| `tests/test_conversation_regression.py` | Regression tests for fixes |
| `tests/conftest.py` | Shared test fixtures |

### Related Documentation

- **CLAUDE.md**: How to run tests and project conventions
- **docs/prd/MAPIT_CONVERSATION_STABILITY_PRD.md**: Full requirements and task list
- **tests/scenarios/**: All YAML test scenario files
