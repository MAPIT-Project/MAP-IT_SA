# Frontend Streaming Specification for V3 Architecture

## Overview

This document specifies how the frontend should handle streaming responses from the **V3 Simplified Agentic Architecture**. The V3 architecture removes the complex intent classification layer and routes ALL queries through a single agentic loop.

---

## API Endpoint

### Current Endpoint (V2)
```
POST /api/v2/conversation/{conversation_id}/message/stream
```

### Request Body
```json
{
  "message": "Tell me about funding opportunities in clean energy research",
  "include_context": true,
  "memory_strategy": "full"
}
```

### Response Format
Server-Sent Events (SSE) with `Content-Type: text/event-stream`

---

## Current V2 Streaming Events

The current V2 architecture sends these SSE event types:

### 1. Status Events
```json
{"type": "status", "stage": "processing", "message": "Processing..."}
{"type": "status", "stage": "processing_message", "message": "Processing your message..."}
{"type": "status", "stage": "fetching_call_documents", "message": "Analyzing call HORIZON-..."}
{"type": "status", "stage": "context_resolution", "message": "Loading conversation context and memory"}
{"type": "status", "stage": "data_retrieval", "message": "Processing search results from EU databases"}
{"type": "status", "stage": "data_enriched", "message": "Enriching and formatting search results"}
{"type": "status", "stage": "answer_generation", "message": "Generating response based on processed data"}
{"type": "status", "stage": "streaming_response", "message": "Starting response stream"}
```

### 2. Progress Events
```json
{
  "type": "progress",
  "stage": "intent_detected",
  "message": "AI analyzed intent: search_calls",
  "routing_decision": "search_calls",
  "intent_confidence": 0.95
}

{
  "type": "progress",
  "stage": "follow_up_detected",
  "message": "Resolving your follow-up question..."
}

{
  "type": "progress",
  "stage": "call_documents_loaded",
  "message": "Loaded 5 relevant document sections",
  "chunks_loaded": 5
}

{
  "type": "progress",
  "stage": "agentic_search",
  "message": "AI is using self-correcting search..."
}

{
  "type": "progress",
  "stage": "agentic_executing",
  "message": "Searching data sources..."
}

{
  "type": "progress",
  "stage": "agentic_evaluating",
  "message": "Found good results!"
}
```

### 3. Token Events (Streaming Response Text)
```json
{"type": "token", "content": "I found "}
{"type": "token", "content": "**15 funding opportunities**"}
{"type": "token", "content": " for your query..."}
```

### 4. Complete Event
```json
{
  "type": "complete",
  "metadata": {
    "confidence": 0.9,
    "tools_executed": true,
    "grounded": true,
    "processing_time_ms": 3456.78,
    "citations": [],
    "projects_found": 0
  }
}
```

### 5. Error Event
```json
{
  "type": "error",
  "error": "Error message here",
  "stage": "error"
}
```

---

## V3 Architecture Changes

### What V3 Does Differently

1. **No Intent Classification** - The agent decides what to do, not a separate classifier
2. **Single Agentic Loop** - All queries go through `ToolAwareAgent.process_query()`
3. **Built-in Follow-up Understanding** - The agent reads conversation history and understands context
4. **Iterative Reasoning** - Agent may call tools multiple times (up to 5 iterations)

### New V3 Streaming Events

The V3 architecture should send these NEW event types:

#### Agent Thinking Events
```json
{
  "type": "agent_thinking",
  "stage": "reasoning",
  "iteration": 1,
  "thought": "User is asking about clean energy funding calls. I should use the search_funding_calls tool."
}
```

#### Tool Execution Events
```json
{
  "type": "tool_call",
  "stage": "executing_tool",
  "tool_name": "search_funding_calls",
  "parameters": {"keywords": "clean energy", "status": "open"},
  "iteration": 1
}

{
  "type": "tool_result",
  "stage": "tool_complete",
  "tool_name": "search_funding_calls",
  "success": true,
  "result_summary": "Found 15 calls",
  "iteration": 1
}
```

#### Agent Iteration Events
```json
{
  "type": "agent_iteration",
  "stage": "iteration_complete",
  "iteration": 1,
  "total_iterations": 5,
  "needs_more_info": false,
  "tools_called": ["search_funding_calls"]
}
```

#### V3 Complete Event
```json
{
  "type": "complete",
  "metadata": {
    "architecture": "simplified_v3",
    "confidence": 0.85,
    "iterations": 2,
    "tools_used": ["search_funding_calls_1", "search_funding_calls_2"],
    "reasoning_steps": [
      {
        "step": 1,
        "thought": "User wants clean energy funding calls",
        "action": "call_tools",
        "tools_called": ["search_funding_calls"],
        "observation": "Found 15 calls..."
      }
    ],
    "processing_time_ms": 4567.89
  }
}
```

---

## Frontend Implementation Guide

### 1. SSE Connection Setup

```javascript
const eventSource = new EventSource(
  `/api/v2/conversation/${conversationId}/message/stream`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: userMessage })
  }
);

// Note: EventSource doesn't support POST natively
// Use fetch with ReadableStream instead:

async function streamMessage(conversationId, message) {
  const response = await fetch(
    `/api/v2/conversation/${conversationId}/message/stream`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    }
  );

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value);
    const lines = text.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        handleEvent(data);
      }
    }
  }
}
```

### 2. Event Handler

```javascript
function handleEvent(event) {
  switch (event.type) {
    case 'status':
      updateStatusUI(event.stage, event.message);
      break;

    case 'progress':
      updateProgressUI(event);
      break;

    case 'agent_thinking':
      // V3: Show agent reasoning (optional - can hide from users)
      showAgentThought(event.iteration, event.thought);
      break;

    case 'tool_call':
      // V3: Show which tool is being called
      showToolExecution(event.tool_name, event.iteration);
      break;

    case 'tool_result':
      // V3: Show tool result summary
      showToolResult(event.tool_name, event.result_summary, event.success);
      break;

    case 'agent_iteration':
      // V3: Update iteration progress
      updateIterationProgress(event.iteration, event.total_iterations);
      break;

    case 'token':
      // Append text to response area
      appendToResponse(event.content);
      break;

    case 'complete':
      // Finalize response
      finalizeResponse(event.metadata);
      break;

    case 'error':
      // Show error
      showError(event.error);
      break;
  }
}
```

### 3. UI State Machine

```
IDLE
  ↓ (user sends message)
PROCESSING
  ↓ (status: processing)
REASONING (V3)
  ↓ (agent_thinking events)
EXECUTING_TOOLS
  ↓ (tool_call / tool_result events)
  ↓ (may loop back to REASONING if needs_more_info)
GENERATING
  ↓ (status: answer_generation)
STREAMING
  ↓ (token events)
COMPLETE
  ↓ (complete event)
IDLE
```

### 4. Recommended UI Components

#### Status Indicator
```
┌─────────────────────────────────────────┐
│ 🔄 Processing your message...           │
└─────────────────────────────────────────┘
```

#### V3 Agent Progress (Optional - for power users)
```
┌─────────────────────────────────────────┐
│ 🤖 Agent Reasoning (Iteration 1/5)      │
│ ├─ Thought: Looking for clean energy... │
│ ├─ Tool: search_funding_calls           │
│ └─ Result: Found 15 calls ✓             │
└─────────────────────────────────────────┘
```

#### Streaming Response
```
┌─────────────────────────────────────────┐
│ I found **15 funding opportunities**    │
│ for your query about 'clean energy      │
│ research':                              │
│                                         │
│ **1. Sustainable Batteries**            │
│ 📋 Call ID: HORIZON-CL5-2025-D3-01     │
│ 🔬 Type: RIA                            │
│ ⏰ Deadline: 25 Sep 2025                │
│ ...                                     │
│ █                                       │ ← Cursor while streaming
└─────────────────────────────────────────┘
```

---

## Event Sequence Examples

### Example 1: Simple Call Search (V3)

```
1. {"type": "status", "stage": "processing", "message": "Processing..."}
2. {"type": "agent_thinking", "iteration": 1, "thought": "User wants clean energy funding calls"}
3. {"type": "tool_call", "tool_name": "search_funding_calls", "iteration": 1}
4. {"type": "tool_result", "tool_name": "search_funding_calls", "success": true, "result_summary": "Found 15 calls"}
5. {"type": "agent_iteration", "iteration": 1, "needs_more_info": false}
6. {"type": "status", "stage": "generating_response", "message": "Generating response..."}
7. {"type": "token", "content": "I found "}
8. {"type": "token", "content": "**15 funding opportunities**"}
... more tokens ...
99. {"type": "complete", "metadata": {"architecture": "simplified_v3", "iterations": 1, "tools_used": ["search_funding_calls_1"]}}
```

### Example 2: Follow-up Complaint (V3)

User: "you just gave me 1 call wtf"

```
1. {"type": "status", "stage": "processing", "message": "Processing..."}
2. {"type": "agent_thinking", "iteration": 1, "thought": "User is complaining about previous results. Looking at conversation history, they asked about clean energy. I should search again."}
3. {"type": "tool_call", "tool_name": "search_funding_calls", "parameters": {"keywords": "clean energy"}, "iteration": 1}
4. {"type": "tool_result", "tool_name": "search_funding_calls", "success": true, "result_summary": "Found 15 calls"}
5. {"type": "agent_iteration", "iteration": 1, "needs_more_info": false}
6. {"type": "status", "stage": "generating_response", "message": "Generating response..."}
7. {"type": "token", "content": "I apologize "}
8. {"type": "token", "content": "that the previous summary was too brief."}
... more tokens ...
99. {"type": "complete", "metadata": {"architecture": "simplified_v3", "iterations": 1}}
```

### Example 3: Complex Query with Multiple Iterations (V3)

User: "Compare EIC and ERC success rates"

```
1. {"type": "status", "stage": "processing", "message": "Processing..."}
2. {"type": "agent_thinking", "iteration": 1, "thought": "User wants comparison. Need to get stats for both EIC and ERC."}
3. {"type": "tool_call", "tool_name": "get_programme_statistics", "parameters": {"programme": "EIC"}, "iteration": 1}
4. {"type": "tool_call", "tool_name": "get_programme_statistics", "parameters": {"programme": "ERC"}, "iteration": 1}
5. {"type": "tool_result", "tool_name": "get_programme_statistics", "success": true, "result_summary": "EIC: 8% success rate"}
6. {"type": "tool_result", "tool_name": "get_programme_statistics", "success": true, "result_summary": "ERC: 12% success rate"}
7. {"type": "agent_iteration", "iteration": 1, "needs_more_info": true}
8. {"type": "agent_thinking", "iteration": 2, "thought": "Got stats, but should verify with documents"}
9. {"type": "tool_call", "tool_name": "search_documents", "parameters": {"query": "EIC ERC success rate comparison"}, "iteration": 2}
10. {"type": "tool_result", "tool_name": "search_documents", "success": true}
11. {"type": "agent_iteration", "iteration": 2, "needs_more_info": false}
12. {"type": "status", "stage": "generating_response", "message": "Generating response..."}
13. {"type": "token", "content": "**Comparing EIC and ERC Success Rates**\n\n"}
... more tokens ...
99. {"type": "complete", "metadata": {"architecture": "simplified_v3", "iterations": 2, "tools_used": ["get_programme_statistics_1", "get_programme_statistics_1", "search_documents_2"]}}
```

---

## Backward Compatibility

### V2 Events Still Supported

The V3 architecture should continue to emit V2-style events for backward compatibility:

| V2 Event | Still Emitted in V3? | Notes |
|----------|---------------------|-------|
| `status: processing` | ✅ Yes | Always sent first |
| `progress: intent_detected` | ⚠️ Changed | Now shows "agentic_v3" |
| `progress: agentic_search` | ❌ Removed | Replaced by `agent_thinking` |
| `progress: agentic_executing` | ❌ Removed | Replaced by `tool_call` |
| `progress: agentic_evaluating` | ❌ Removed | Replaced by `tool_result` |
| `token: content` | ✅ Yes | Same format |
| `complete: metadata` | ⚠️ Extended | Has new fields |
| `error: error` | ✅ Yes | Same format |

### Detecting V3 vs V2 Responses

Check the `complete` event's metadata:

```javascript
function handleComplete(metadata) {
  if (metadata.architecture === 'simplified_v3') {
    // V3 response - has reasoning_steps, iterations, etc.
    console.log('V3 response with', metadata.iterations, 'iterations');
  } else {
    // V2 response
    console.log('V2 response');
  }
}
```

---

## Error Handling

### V3-Specific Errors

```json
{
  "type": "error",
  "error": "Agent exceeded maximum iterations (5)",
  "stage": "agent_loop",
  "iteration": 5
}

{
  "type": "error",
  "error": "Tool execution failed: search_funding_calls",
  "stage": "tool_execution",
  "tool_name": "search_funding_calls"
}
```

### Fallback Behavior

If V3 is unavailable, the system automatically falls back to V2:

```javascript
function handleComplete(metadata) {
  if (metadata.architecture === 'simplified_v3') {
    // V3 succeeded
  } else if (metadata.fallback_reason) {
    // Fell back to V2
    console.log('Fallback:', metadata.fallback_reason);
  }
}
```

---

## Implementation Checklist for Frontend

### Required Changes

- [ ] Handle new `agent_thinking` events (can show/hide based on user preference)
- [ ] Handle new `tool_call` events (show tool name being executed)
- [ ] Handle new `tool_result` events (show success/failure indicator)
- [ ] Handle new `agent_iteration` events (show iteration progress)
- [ ] Update `complete` handler to read new metadata fields
- [ ] Add UI for showing reasoning steps (optional, for power users)

### Optional Enhancements

- [ ] Add "Show reasoning" toggle for power users
- [ ] Show iteration progress bar (1/5, 2/5, etc.)
- [ ] Display tool execution timeline
- [ ] Show confidence score in UI
- [ ] Cache conversation context client-side for faster follow-ups

---

## Testing

### Test URLs

```bash
# V3 Streaming endpoint (once implemented in routes)
curl -X POST "http://localhost:8000/api/v3/conversation/123/message/stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about clean energy funding calls"}'

# Current V2 endpoint (for comparison)
curl -X POST "http://localhost:8000/api/v2/conversation/123/message/stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about clean energy funding calls"}'
```

### Test Scenarios

1. **Simple query**: "What is Horizon Europe?" → Should complete in 1 iteration
2. **Call search**: "Show me AI funding calls" → Should use `search_funding_calls` tool
3. **Project search**: "Find hydrogen projects" → Should use `search_projects` tool
4. **Follow-up**: First ask about calls, then say "show me more" → Should remember topic
5. **Complaint**: Ask for calls, then say "only 1 result wtf" → Should re-search same topic
6. **Comparison**: "Compare EIC vs ERC" → Should use multiple tools, 2+ iterations

---

## Current Implementation Status

### Backend (as of now)

| Component | Status | Notes |
|-----------|--------|-------|
| `ToolAwareAgent` | ✅ Done | Enhanced with conversation context |
| `process_message_v3` | ✅ Done | Non-streaming works |
| V3 streaming endpoint | ❌ Not Done | Needs implementation |
| V3 route in `conversation_routes_v2.py` | ❌ Not Done | Needs new endpoint |

### What Needs to Be Built

1. **`process_message_v3` streaming support** - Add `streaming=True` mode that yields events
2. **New V3 route** - Add `/api/v3/conversation/{id}/message/stream` endpoint
3. **Event emission during agent loop** - Yield events at each reasoning step

---

## Contact

For questions about this spec, refer to:
- `app/services/agents/tool_aware_agent.py` - Agent implementation
- `app/services/conversation/conversation_manager.py` - `process_message_v3` method
- `PLAN_SIMPLIFIED_AGENTIC_ARCHITECTURE.md` - Architecture overview
