# AI Proposal Writer - Frontend Integration Guide

## Overview

This document provides comprehensive integration instructions for connecting the frontend to the V4 AI Proposal Writer API. The architecture enables a **chat-first proposal writing experience** where users interact via chat and see AI-generated content appear in a split-panel document viewer.

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                     │
│  ┌─────────────────────────┐    ┌─────────────────────────────────┐ │
│  │     Chat Panel          │    │      Document Viewer            │ │
│  │  ┌─────────────────┐    │    │  ┌───────────────────────────┐  │ │
│  │  │ Message History │    │    │  │ Section: Objectives       │  │ │
│  │  │ - User messages │    │    │  │ [Content appears here     │  │ │
│  │  │ - AI responses  │    │    │  │  as AI generates it]      │  │ │
│  │  │ - Tool events   │    │    │  │                           │  │ │
│  │  └─────────────────┘    │    │  │ Score: 3.5/5 ⭐           │  │ │
│  │  ┌─────────────────┐    │    │  │ Gaps: 2 identified        │  │ │
│  │  │ Input Box       │    │    │  └───────────────────────────┘  │ │
│  │  │ "Write the..."  │    │    │  ┌───────────────────────────┐  │ │
│  │  └─────────────────┘    │    │  │ Section: Methodology      │  │ │
│  └─────────────────────────┘    │  │ [Empty - click to focus]  │  │ │
│                                  │  └───────────────────────────┘  │ │
│                                  └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    V4 API ENDPOINTS                                  │
│  POST /api/v4/proposal-session/create                               │
│  POST /api/v4/proposal-session/{id}/message/stream  (SSE)           │
│  PATCH /api/v4/proposal-session/{id}/section/{section_id}           │
│  POST /api/v4/proposal-session/{id}/section/{section_id}/generate   │
│  POST /api/v4/proposal-session/{id}/section/{section_id}/evaluate   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [API Endpoints Reference](#api-endpoints-reference)
3. [Session Management](#session-management)
4. [Chat Integration (SSE Streaming)](#chat-integration-sse-streaming)
5. [SSE Event Types](#sse-event-types)
6. [Section Operations](#section-operations)
7. [State Management](#state-management)
8. [TypeScript Interfaces](#typescript-interfaces)
9. [React Implementation Examples](#react-implementation-examples)
10. [Error Handling](#error-handling)
11. [Best Practices](#best-practices)

---

## Quick Start

### 1. Create a Session

```typescript
const response = await fetch('/api/v4/proposal-session/create', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    proposal_id: 123,
    call_id: 'HORIZON-CL5-2025-D3-01',
    title: 'Green Hydrogen Innovation Project',
    proposal_type: 'RIA'
  })
});

const session = await response.json();
// session.session_id = "uuid-here"
```

### 2. Connect to Chat Stream

```typescript
const eventSource = new EventSource(
  `/api/v4/proposal-session/${sessionId}/message/stream`,
  { /* POST body handled separately - see full implementation */ }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'agent_thinking':
      showThinkingIndicator(data.thought);
      break;
    case 'section_update':
      updateSectionContent(data.section_id, data.content);
      break;
    case 'token':
      appendToResponse(data.content);
      break;
  }
};
```

---

## API Endpoints Reference

### Base URL
```
/api/v4/proposal-session
```

### Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/create` | Create new proposal session |
| `GET` | `/{session_id}` | Get session details |
| `DELETE` | `/{session_id}` | Delete session |
| `POST` | `/{session_id}/message/stream` | Send message (SSE streaming) |
| `POST` | `/{session_id}/message` | Send message (non-streaming) |
| `PATCH` | `/{session_id}/section/{section_id}` | Update section content |
| `POST` | `/{session_id}/section/{section_id}/generate` | AI generate section (SSE) |
| `POST` | `/{session_id}/section/{section_id}/evaluate` | Evaluate section |
| `POST` | `/{session_id}/section/{section_id}/analyze-gaps` | Analyze gaps |
| `POST` | `/{session_id}/focus/{section_id}` | Set active section |
| `GET` | `/health` | Health check |

---

## Session Management

### Create Session

**Request:**
```http
POST /api/v4/proposal-session/create?user_id=user123
Content-Type: application/json

{
  "proposal_id": 123,
  "call_id": "HORIZON-CL5-2025-D3-01",
  "title": "Green Hydrogen Innovation Project",
  "proposal_type": "RIA",
  "conversation_id": null
}
```

**Response:**
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "proposal_id": 123,
  "call_id": "HORIZON-CL5-2025-D3-01",
  "title": "Green Hydrogen Innovation Project",
  "status": "active",
  "active_section_id": null,
  "completion_percentage": 0.0,
  "total_words": 0,
  "sections": {
    "excellence.objectives": {
      "section_id": "excellence.objectives",
      "section_name": "Objectives and ambition",
      "content": "",
      "word_count": 0,
      "quality_score": null,
      "status": "empty",
      "suggestions_count": 0,
      "gaps_count": 0,
      "lock_status": "unlocked",
      "is_dirty": false,
      "version": 1,
      "last_updated": null
    },
    "excellence.methodology": {
      "section_id": "excellence.methodology",
      "section_name": "Methodology",
      // ... same structure
    },
    // ... other sections
  },
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Get Session

**Request:**
```http
GET /api/v4/proposal-session/{session_id}
```

**Response:** Same structure as create response.

### Delete Session

**Request:**
```http
DELETE /api/v4/proposal-session/{session_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Session deleted"
}
```

---

## Chat Integration (SSE Streaming)

The chat endpoint uses Server-Sent Events (SSE) for real-time streaming. Since SSE natively only supports GET requests, we use a fetch-based approach for POST with streaming.

### Sending a Message with Streaming

```typescript
async function sendMessageWithStreaming(
  sessionId: string,
  message: string,
  sectionContext?: string,
  onEvent: (event: SSEEvent) => void
): Promise<void> {
  const response = await fetch(
    `/api/v4/proposal-session/${sessionId}/message/stream`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({
        message: message,
        section_context: sectionContext || null
      })
    }
  );

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('Response body is null');
  }

  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();

    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE format: "data: {...}\n\n"
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || ''; // Keep incomplete data in buffer

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const jsonStr = line.slice(6); // Remove "data: " prefix
          const event = JSON.parse(jsonStr);
          onEvent(event);
        } catch (e) {
          console.error('Failed to parse SSE event:', e);
        }
      }
    }
  }
}
```

### Usage Example

```typescript
await sendMessageWithStreaming(
  sessionId,
  "Write the objectives section focusing on green hydrogen production",
  "excellence.objectives",
  (event) => {
    switch (event.type) {
      case 'status':
        setStatusMessage(event.message);
        break;

      case 'agent_thinking':
        addThinkingStep({
          iteration: event.iteration,
          thought: event.thought,
          action: event.action
        });
        break;

      case 'tool_call':
        addToolCallIndicator({
          toolName: event.tool_name,
          parameters: event.parameters,
          reasoning: event.reasoning
        });
        break;

      case 'tool_result':
        updateToolResult({
          toolName: event.tool_name,
          success: event.success,
          resultCount: event.result_count
        });
        break;

      case 'section_update':
        // KEY: Update the document viewer with new content
        updateSectionInViewer(event.section_id, event.content);
        break;

      case 'token':
        appendTokenToResponse(event.content);
        break;

      case 'agent_complete':
        finalizeResponse(event.result);
        break;

      case 'session_state':
        updateSessionState({
          completionPercentage: event.completion_percentage,
          totalWords: event.total_words,
          sectionsAffected: event.sections_affected
        });
        break;

      case 'error':
        handleError(event.error);
        break;
    }
  }
);
```

---

## SSE Event Types

### 1. `status`
Processing status updates.

```json
{
  "type": "status",
  "stage": "processing",
  "message": "Processing your request..."
}
```

### 2. `agent_thinking`
Agent's reasoning at each iteration.

```json
{
  "type": "agent_thinking",
  "iteration": 1,
  "thought": "The user wants to write the objectives section. I should use generate_section_draft tool with the call context.",
  "action": "call_tools"
}
```

**UI Suggestion:** Show a "thinking" indicator with expandable reasoning details.

### 3. `tool_call`
When a tool is being invoked.

```json
{
  "type": "tool_call",
  "iteration": 1,
  "tool_name": "generate_section_draft",
  "parameters": {
    "section_id": "excellence.objectives",
    "call_id": "HORIZON-CL5-2025-D3-01",
    "word_target": 500
  },
  "reasoning": "Generating draft content for the objectives section"
}
```

**UI Suggestion:** Show a tool execution indicator (e.g., "🔧 Generating section draft...")

### 4. `tool_result`
Tool execution result.

```json
{
  "type": "tool_result",
  "tool_name": "generate_section_draft",
  "success": true,
  "result_count": 1,
  "execution_time_ms": 2340.5
}
```

### 5. `section_update` ⭐ CRITICAL
When section content is generated or modified.

```json
{
  "type": "section_update",
  "section_id": "excellence.objectives",
  "tool_name": "generate_section_draft",
  "content": "## Objectives and Ambition\n\nThis project aims to revolutionize green hydrogen production through innovative electrolyzer technology...\n\n### Specific Objectives:\n\n1. **SO1**: Develop a novel PEM electrolyzer with 85% efficiency\n2. **SO2**: Demonstrate cost reduction of 40% compared to state-of-art\n3. **SO3**: Validate technology at TRL 6 in industrial environment"
}
```

**UI Handling:** This is the key event for updating the document viewer. When received:

```typescript
function handleSectionUpdate(event: SectionUpdateEvent) {
  // 1. Update the section content in state
  setSections(prev => ({
    ...prev,
    [event.section_id]: {
      ...prev[event.section_id],
      content: event.content,
      word_count: countWords(event.content),
      status: 'draft'
    }
  }));

  // 2. Highlight the section in the viewer
  highlightSection(event.section_id);

  // 3. Optionally scroll to the section
  scrollToSection(event.section_id);

  // 4. Show a visual indicator that content was AI-generated
  showAIGeneratedBadge(event.section_id);
}
```

### 6. `token`
Streaming response text token.

```json
{
  "type": "token",
  "content": "I've drafted the objectives section "
}
```

### 7. `agent_complete`
Final result when agent completes.

```json
{
  "type": "agent_complete",
  "result": {
    "answer": "I've drafted the objectives section for your green hydrogen project. The content focuses on three specific objectives aligned with the call requirements...",
    "success": true,
    "sections_affected": ["excellence.objectives"],
    "iterations": 2,
    "confidence": 0.85,
    "total_time_ms": 4521.3,
    "proposal_intent": "generate_section"
  }
}
```

### 8. `session_state`
Updated session state after changes.

```json
{
  "type": "session_state",
  "completion_percentage": 14.3,
  "total_words": 487,
  "sections_affected": ["excellence.objectives"]
}
```

### 9. `error`
Error information.

```json
{
  "type": "error",
  "error": "Section is locked by another operation"
}
```

---

## Section Operations

### Update Section Content (User Edit)

When the user directly edits content in the document viewer:

**Request:**
```http
PATCH /api/v4/proposal-session/{session_id}/section/{section_id}
Content-Type: application/json

{
  "content": "## Updated Objectives\n\nUser-edited content here..."
}
```

**Response:**
```json
{
  "success": true,
  "section_id": "excellence.objectives",
  "word_count": 342,
  "status": "draft",
  "quality_score": null
}
```

**Important:** If the section is locked (AI is generating), the request will fail with:
```json
{
  "detail": "Failed to update section (may be locked)"
}
```

### Generate Section Content (AI)

Stream AI-generated content for a section:

**Request:**
```http
POST /api/v4/proposal-session/{session_id}/section/{section_id}/generate
Content-Type: application/json

{
  "guidance": "Focus on innovative aspects and alignment with EU Green Deal",
  "word_target": 600,
  "style": "formal"
}
```

**Response:** SSE stream with events:
```
data: {"type": "status", "message": "Generating content...", "section_id": "excellence.objectives"}

data: {"type": "content", "section_id": "excellence.objectives", "content": "## Objectives and Ambition\n\n..."}

data: {"type": "complete", "section_id": "excellence.objectives", "word_count": 587}
```

### Evaluate Section

Get EU evaluator simulation score:

**Request:**
```http
POST /api/v4/proposal-session/{session_id}/section/{section_id}/evaluate
```

**Response:**
```json
{
  "section_id": "excellence.objectives",
  "score": 3.5,
  "max_score": 5.0,
  "criterion_scores": [
    {
      "name": "Clarity of objectives",
      "score": 4.0,
      "max": 5.0,
      "feedback": "Objectives are clearly stated with measurable targets"
    },
    {
      "name": "Ambition level",
      "score": 3.5,
      "max": 5.0,
      "feedback": "Good ambition but could be more specific about breakthrough potential"
    }
  ],
  "strengths": [
    "Clear structure with numbered objectives",
    "Measurable KPIs included",
    "Good alignment with call scope"
  ],
  "weaknesses": [
    "Missing quantitative targets for some objectives",
    "Limited reference to state-of-art advancement"
  ],
  "suggestions": [
    "Add specific numerical targets (e.g., '85% efficiency')",
    "Include comparison with current best technologies",
    "Strengthen the 'beyond state-of-art' narrative"
  ],
  "evaluated": true
}
```

### Analyze Gaps

Identify missing elements:

**Request:**
```http
POST /api/v4/proposal-session/{session_id}/section/{section_id}/analyze-gaps
```

**Response:**
```json
{
  "section_id": "excellence.objectives",
  "gaps": [
    {
      "id": "gap-1",
      "description": "Missing quantitative targets for SO2",
      "severity": "major",
      "category": "content",
      "suggested_fix": "Add specific cost reduction percentage and timeline",
      "effort": "quick"
    },
    {
      "id": "gap-2",
      "description": "No reference to EU policy alignment",
      "severity": "minor",
      "category": "compliance",
      "suggested_fix": "Add explicit reference to EU Green Deal and Hydrogen Strategy",
      "effort": "quick"
    }
  ],
  "gap_count": 2,
  "analyzed": true
}
```

### Set Active Section (Focus)

Tell the backend which section the user is focused on:

**Request:**
```http
POST /api/v4/proposal-session/{session_id}/focus/{section_id}
```

**Response:**
```json
{
  "success": true,
  "active_section_id": "excellence.methodology"
}
```

**When to call:** When user clicks on a section in the document viewer. This helps the agent provide more contextual responses.

---

## State Management

### Recommended State Structure (React/Redux)

```typescript
interface ProposalSessionState {
  // Session metadata
  sessionId: string | null;
  proposalId: number | null;
  callId: string;
  title: string;
  status: 'active' | 'paused' | 'completed' | 'expired';

  // Document state
  sections: Record<string, SectionState>;
  activeSectionId: string | null;
  completionPercentage: number;
  totalWords: number;

  // Chat state
  messages: ChatMessage[];
  isStreaming: boolean;
  currentThought: string | null;
  pendingToolCalls: ToolCall[];

  // UI state
  isLoading: boolean;
  error: string | null;
  lockedSections: Set<string>;
}

interface SectionState {
  sectionId: string;
  sectionName: string;
  content: string;
  wordCount: number;
  qualityScore: number | null;
  status: 'empty' | 'draft' | 'in_review' | 'complete';
  suggestionsCount: number;
  gapsCount: number;
  lockStatus: 'unlocked' | 'locked_by_ai' | 'locked_by_user';
  isDirty: boolean;
  version: number;
  lastUpdated: string | null;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  toolsUsed?: string[];
  sectionsAffected?: string[];
  metadata?: {
    thinking?: ThinkingStep[];
    toolCalls?: ToolCallInfo[];
  };
}
```

### State Update Flow

```
User types message
       │
       ▼
┌─────────────────────────────────────┐
│ 1. Add user message to chat state   │
│ 2. Set isStreaming = true           │
│ 3. Clear currentThought             │
└─────────────────────────────────────┘
       │
       ▼
Send POST to /message/stream
       │
       ▼
┌─────────────────────────────────────┐
│ SSE Events arrive:                  │
│                                     │
│ agent_thinking → Update thought     │
│ tool_call → Add to pendingToolCalls │
│ tool_result → Update tool status    │
│ section_update → UPDATE SECTIONS    │
│ token → Append to response          │
│ agent_complete → Finalize           │
│ session_state → Update stats        │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ 1. Add assistant message to chat    │
│ 2. Set isStreaming = false          │
│ 3. Update completion percentage     │
└─────────────────────────────────────┘
```

---

## TypeScript Interfaces

### Complete Type Definitions

```typescript
// API Request Types
interface CreateSessionRequest {
  proposal_id: number;
  call_id: string;
  title: string;
  proposal_type?: 'RIA' | 'IA' | 'CSA' | 'ERC';
  conversation_id?: number | null;
}

interface MessageRequest {
  message: string;
  section_context?: string | null;
}

interface SectionUpdateRequest {
  content: string;
}

interface SectionGenerateRequest {
  guidance?: string | null;
  word_target?: number;
  style?: 'formal' | 'technical' | 'accessible';
}

// API Response Types
interface SessionResponse {
  session_id: string;
  proposal_id: number;
  call_id: string;
  title: string;
  status: 'active' | 'paused' | 'completed' | 'expired';
  active_section_id: string | null;
  completion_percentage: number;
  total_words: number;
  sections: Record<string, SectionResponse>;
  created_at: string;
}

interface SectionResponse {
  section_id: string;
  section_name: string;
  content: string;
  word_count: number;
  quality_score: number | null;
  status: 'empty' | 'draft' | 'in_review' | 'complete';
  suggestions_count: number;
  gaps_count: number;
  lock_status: 'unlocked' | 'locked_by_ai' | 'locked_by_user';
  is_dirty: boolean;
  version: number;
  last_updated: string | null;
}

interface EvaluationResponse {
  section_id: string;
  score: number;
  max_score: number;
  criterion_scores: CriterionScore[];
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  evaluated: boolean;
}

interface CriterionScore {
  name: string;
  score: number;
  max: number;
  feedback: string;
}

interface GapAnalysisResponse {
  section_id: string;
  gaps: Gap[];
  gap_count: number;
  analyzed: boolean;
}

interface Gap {
  id: string;
  description: string;
  severity: 'critical' | 'major' | 'minor';
  category: 'content' | 'structure' | 'evidence' | 'compliance';
  suggested_fix: string;
  effort: 'quick' | 'medium' | 'substantial';
}

// SSE Event Types
type SSEEvent =
  | StatusEvent
  | AgentThinkingEvent
  | ToolCallEvent
  | ToolResultEvent
  | SectionUpdateEvent
  | TokenEvent
  | AgentCompleteEvent
  | SessionStateEvent
  | ErrorEvent;

interface StatusEvent {
  type: 'status';
  stage: string;
  message: string;
}

interface AgentThinkingEvent {
  type: 'agent_thinking';
  iteration: number;
  thought: string;
  action: 'call_tools' | 'conclude' | 'analyze_results';
}

interface ToolCallEvent {
  type: 'tool_call';
  iteration: number;
  tool_name: string;
  parameters: Record<string, unknown>;
  reasoning: string;
}

interface ToolResultEvent {
  type: 'tool_result';
  tool_name: string;
  success: boolean;
  result_count: number;
  execution_time_ms: number;
}

interface SectionUpdateEvent {
  type: 'section_update';
  section_id: string;
  tool_name: string;
  content: string;
}

interface TokenEvent {
  type: 'token';
  content: string;
}

interface AgentCompleteEvent {
  type: 'agent_complete';
  result: {
    answer: string;
    success: boolean;
    sections_affected: string[];
    iterations: number;
    confidence: number;
    total_time_ms: number;
    proposal_intent: string | null;
  };
}

interface SessionStateEvent {
  type: 'session_state';
  completion_percentage: number;
  total_words: number;
  sections_affected: string[];
}

interface ErrorEvent {
  type: 'error';
  error: string;
}
```

---

## React Implementation Examples

### ProposalSessionProvider

```tsx
import React, { createContext, useContext, useReducer, useCallback } from 'react';

// Context
const ProposalSessionContext = createContext<{
  state: ProposalSessionState;
  dispatch: React.Dispatch<Action>;
  sendMessage: (message: string, sectionContext?: string) => Promise<void>;
  updateSection: (sectionId: string, content: string) => Promise<void>;
  evaluateSection: (sectionId: string) => Promise<EvaluationResponse>;
  focusSection: (sectionId: string) => Promise<void>;
} | null>(null);

// Reducer
type Action =
  | { type: 'SET_SESSION'; payload: SessionResponse }
  | { type: 'SET_STREAMING'; payload: boolean }
  | { type: 'ADD_MESSAGE'; payload: ChatMessage }
  | { type: 'SET_THOUGHT'; payload: string | null }
  | { type: 'UPDATE_SECTION'; payload: { sectionId: string; content: string } }
  | { type: 'SET_SECTION_SCORE'; payload: { sectionId: string; score: number } }
  | { type: 'UPDATE_SESSION_STATS'; payload: { completionPercentage: number; totalWords: number } }
  | { type: 'SET_ACTIVE_SECTION'; payload: string | null }
  | { type: 'ADD_TOOL_CALL'; payload: ToolCallInfo }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'APPEND_TO_RESPONSE'; payload: string };

function reducer(state: ProposalSessionState, action: Action): ProposalSessionState {
  switch (action.type) {
    case 'SET_SESSION':
      return {
        ...state,
        sessionId: action.payload.session_id,
        proposalId: action.payload.proposal_id,
        callId: action.payload.call_id,
        title: action.payload.title,
        status: action.payload.status,
        sections: action.payload.sections,
        activeSectionId: action.payload.active_section_id,
        completionPercentage: action.payload.completion_percentage,
        totalWords: action.payload.total_words,
      };

    case 'UPDATE_SECTION':
      return {
        ...state,
        sections: {
          ...state.sections,
          [action.payload.sectionId]: {
            ...state.sections[action.payload.sectionId],
            content: action.payload.content,
            wordCount: action.payload.content.split(/\s+/).filter(Boolean).length,
            status: action.payload.content.length > 0 ? 'draft' : 'empty',
            isDirty: true,
          }
        }
      };

    case 'SET_STREAMING':
      return { ...state, isStreaming: action.payload };

    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };

    case 'SET_THOUGHT':
      return { ...state, currentThought: action.payload };

    case 'SET_ACTIVE_SECTION':
      return { ...state, activeSectionId: action.payload };

    case 'UPDATE_SESSION_STATS':
      return {
        ...state,
        completionPercentage: action.payload.completionPercentage,
        totalWords: action.payload.totalWords,
      };

    case 'SET_ERROR':
      return { ...state, error: action.payload };

    default:
      return state;
  }
}

// Provider Component
export function ProposalSessionProvider({
  children,
  sessionId
}: {
  children: React.ReactNode;
  sessionId: string;
}) {
  const [state, dispatch] = useReducer(reducer, initialState);

  // Load session on mount
  React.useEffect(() => {
    loadSession(sessionId);
  }, [sessionId]);

  const loadSession = async (id: string) => {
    const response = await fetch(`/api/v4/proposal-session/${id}`);
    const session = await response.json();
    dispatch({ type: 'SET_SESSION', payload: session });
  };

  const sendMessage = useCallback(async (message: string, sectionContext?: string) => {
    if (!state.sessionId) return;

    // Add user message
    dispatch({
      type: 'ADD_MESSAGE',
      payload: {
        id: crypto.randomUUID(),
        role: 'user',
        content: message,
        timestamp: new Date(),
      }
    });

    dispatch({ type: 'SET_STREAMING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });

    let responseContent = '';

    try {
      await sendMessageWithStreaming(
        state.sessionId,
        message,
        sectionContext,
        (event) => {
          switch (event.type) {
            case 'agent_thinking':
              dispatch({ type: 'SET_THOUGHT', payload: event.thought });
              break;

            case 'section_update':
              dispatch({
                type: 'UPDATE_SECTION',
                payload: {
                  sectionId: event.section_id,
                  content: event.content,
                }
              });
              break;

            case 'token':
              responseContent += event.content;
              break;

            case 'agent_complete':
              dispatch({
                type: 'ADD_MESSAGE',
                payload: {
                  id: crypto.randomUUID(),
                  role: 'assistant',
                  content: event.result.answer,
                  timestamp: new Date(),
                  sectionsAffected: event.result.sections_affected,
                }
              });
              break;

            case 'session_state':
              dispatch({
                type: 'UPDATE_SESSION_STATS',
                payload: {
                  completionPercentage: event.completion_percentage,
                  totalWords: event.total_words,
                }
              });
              break;

            case 'error':
              dispatch({ type: 'SET_ERROR', payload: event.error });
              break;
          }
        }
      );
    } finally {
      dispatch({ type: 'SET_STREAMING', payload: false });
      dispatch({ type: 'SET_THOUGHT', payload: null });
    }
  }, [state.sessionId]);

  const updateSection = useCallback(async (sectionId: string, content: string) => {
    if (!state.sessionId) return;

    const response = await fetch(
      `/api/v4/proposal-session/${state.sessionId}/section/${sectionId}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      }
    );

    if (response.ok) {
      dispatch({
        type: 'UPDATE_SECTION',
        payload: { sectionId, content }
      });
    }
  }, [state.sessionId]);

  const evaluateSection = useCallback(async (sectionId: string) => {
    if (!state.sessionId) throw new Error('No session');

    const response = await fetch(
      `/api/v4/proposal-session/${state.sessionId}/section/${sectionId}/evaluate`,
      { method: 'POST' }
    );

    const result = await response.json();

    if (result.score !== undefined) {
      dispatch({
        type: 'SET_SECTION_SCORE',
        payload: { sectionId, score: result.score }
      });
    }

    return result;
  }, [state.sessionId]);

  const focusSection = useCallback(async (sectionId: string) => {
    if (!state.sessionId) return;

    await fetch(
      `/api/v4/proposal-session/${state.sessionId}/focus/${sectionId}`,
      { method: 'POST' }
    );

    dispatch({ type: 'SET_ACTIVE_SECTION', payload: sectionId });
  }, [state.sessionId]);

  return (
    <ProposalSessionContext.Provider value={{
      state,
      dispatch,
      sendMessage,
      updateSection,
      evaluateSection,
      focusSection,
    }}>
      {children}
    </ProposalSessionContext.Provider>
  );
}

export function useProposalSession() {
  const context = useContext(ProposalSessionContext);
  if (!context) {
    throw new Error('useProposalSession must be used within ProposalSessionProvider');
  }
  return context;
}
```

### Chat Panel Component

```tsx
import React, { useState, useRef, useEffect } from 'react';
import { useProposalSession } from './ProposalSessionProvider';

export function ChatPanel() {
  const { state, sendMessage } = useProposalSession();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || state.isStreaming) return;

    const message = input;
    setInput('');
    await sendMessage(message, state.activeSectionId || undefined);
  };

  return (
    <div className="chat-panel">
      <div className="messages-container">
        {state.messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div className="message-content">{msg.content}</div>
            {msg.sectionsAffected && msg.sectionsAffected.length > 0 && (
              <div className="sections-affected">
                Sections updated: {msg.sectionsAffected.join(', ')}
              </div>
            )}
          </div>
        ))}

        {/* Thinking indicator */}
        {state.isStreaming && state.currentThought && (
          <div className="thinking-indicator">
            <span className="thinking-icon">🤔</span>
            <span className="thinking-text">{state.currentThought}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={state.isStreaming ? "AI is responding..." : "Ask about your proposal..."}
          disabled={state.isStreaming}
        />
        <button type="submit" disabled={state.isStreaming || !input.trim()}>
          Send
        </button>
      </form>

      {/* Quick actions */}
      <div className="quick-actions">
        <button onClick={() => sendMessage("What sections need the most work?")}>
          📊 Analyze Progress
        </button>
        <button onClick={() => sendMessage(`Evaluate the ${state.activeSectionId} section`)}>
          ⭐ Evaluate Section
        </button>
        <button onClick={() => sendMessage(`What are the gaps in ${state.activeSectionId}?`)}>
          🔍 Find Gaps
        </button>
      </div>
    </div>
  );
}
```

### Document Viewer Component

```tsx
import React from 'react';
import { useProposalSession } from './ProposalSessionProvider';

export function DocumentViewer() {
  const { state, updateSection, focusSection, evaluateSection } = useProposalSession();

  const handleSectionClick = (sectionId: string) => {
    focusSection(sectionId);
  };

  const handleContentChange = async (sectionId: string, content: string) => {
    await updateSection(sectionId, content);
  };

  return (
    <div className="document-viewer">
      <div className="document-header">
        <h2>{state.title}</h2>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${state.completionPercentage}%` }}
          />
          <span>{state.completionPercentage.toFixed(0)}% complete</span>
        </div>
        <div className="word-count">{state.totalWords} words</div>
      </div>

      <div className="sections-list">
        {Object.values(state.sections).map((section) => (
          <SectionCard
            key={section.sectionId}
            section={section}
            isActive={state.activeSectionId === section.sectionId}
            isLocked={section.lockStatus !== 'unlocked'}
            onClick={() => handleSectionClick(section.sectionId)}
            onContentChange={(content) => handleContentChange(section.sectionId, content)}
            onEvaluate={() => evaluateSection(section.sectionId)}
          />
        ))}
      </div>
    </div>
  );
}

interface SectionCardProps {
  section: SectionResponse;
  isActive: boolean;
  isLocked: boolean;
  onClick: () => void;
  onContentChange: (content: string) => void;
  onEvaluate: () => void;
}

function SectionCard({
  section,
  isActive,
  isLocked,
  onClick,
  onContentChange,
  onEvaluate
}: SectionCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [localContent, setLocalContent] = useState(section.content);

  // Sync with external updates (e.g., from AI)
  useEffect(() => {
    setLocalContent(section.content);
  }, [section.content]);

  const handleBlur = () => {
    setIsEditing(false);
    if (localContent !== section.content) {
      onContentChange(localContent);
    }
  };

  return (
    <div
      className={`section-card ${isActive ? 'active' : ''} ${isLocked ? 'locked' : ''}`}
      onClick={onClick}
    >
      <div className="section-header">
        <h3>{section.sectionName}</h3>
        <div className="section-meta">
          <span className={`status-badge ${section.status}`}>
            {section.status}
          </span>
          {section.qualityScore !== null && (
            <span className="score">
              ⭐ {section.qualityScore.toFixed(1)}/5
            </span>
          )}
          <span className="word-count">{section.wordCount} words</span>
        </div>
      </div>

      {/* Lock indicator */}
      {isLocked && (
        <div className="lock-indicator">
          🔒 AI is generating content...
        </div>
      )}

      {/* Content area */}
      <div className="section-content">
        {section.content ? (
          isEditing && !isLocked ? (
            <textarea
              value={localContent}
              onChange={(e) => setLocalContent(e.target.value)}
              onBlur={handleBlur}
              autoFocus
            />
          ) : (
            <div
              className="content-preview"
              onClick={() => !isLocked && setIsEditing(true)}
            >
              {section.content}
            </div>
          )
        ) : (
          <div className="empty-section">
            <p>This section is empty. Ask the AI to write it!</p>
            <code>
              "Write the {section.sectionName.toLowerCase()} section"
            </code>
          </div>
        )}
      </div>

      {/* Section actions */}
      <div className="section-actions">
        {section.gapsCount > 0 && (
          <span className="gaps-badge">
            ⚠️ {section.gapsCount} gap{section.gapsCount > 1 ? 's' : ''}
          </span>
        )}
        {section.suggestionsCount > 0 && (
          <span className="suggestions-badge">
            💡 {section.suggestionsCount} suggestion{section.suggestionsCount > 1 ? 's' : ''}
          </span>
        )}
        <button onClick={onEvaluate} disabled={!section.content}>
          Evaluate
        </button>
      </div>
    </div>
  );
}
```

### Main App Layout

```tsx
import React from 'react';
import { ProposalSessionProvider } from './ProposalSessionProvider';
import { ChatPanel } from './ChatPanel';
import { DocumentViewer } from './DocumentViewer';

export function ProposalWriterApp({ sessionId }: { sessionId: string }) {
  return (
    <ProposalSessionProvider sessionId={sessionId}>
      <div className="proposal-writer-layout">
        <div className="left-panel">
          <ChatPanel />
        </div>
        <div className="right-panel">
          <DocumentViewer />
        </div>
      </div>
    </ProposalSessionProvider>
  );
}

// CSS (Tailwind-style or regular CSS)
const styles = `
.proposal-writer-layout {
  display: flex;
  height: 100vh;
}

.left-panel {
  width: 40%;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
}

.right-panel {
  width: 60%;
  overflow-y: auto;
}

.section-card.active {
  border: 2px solid #3b82f6;
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.3);
}

.section-card.locked {
  opacity: 0.7;
  pointer-events: none;
}

.lock-indicator {
  background: #fef3c7;
  padding: 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
`;
```

---

## Error Handling

### HTTP Errors

```typescript
async function handleApiCall<T>(call: () => Promise<Response>): Promise<T> {
  const response = await call();

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));

    switch (response.status) {
      case 400:
        throw new Error(`Bad Request: ${error.detail}`);
      case 404:
        throw new Error(`Not Found: ${error.detail}`);
      case 423: // Locked
        throw new Error(`Section is locked: ${error.detail}`);
      case 500:
        throw new Error(`Server Error: ${error.detail}`);
      default:
        throw new Error(`HTTP ${response.status}: ${error.detail}`);
    }
  }

  return response.json();
}
```

### SSE Connection Errors

```typescript
function handleSSEError(error: unknown, retryCount: number, maxRetries: number) {
  console.error('SSE Error:', error);

  if (retryCount < maxRetries) {
    // Exponential backoff
    const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
    console.log(`Retrying in ${delay}ms...`);
    setTimeout(() => reconnect(), delay);
  } else {
    // Show user-friendly error
    showError('Connection lost. Please refresh the page.');
  }
}
```

### Section Lock Handling

```typescript
async function updateSectionWithRetry(
  sessionId: string,
  sectionId: string,
  content: string,
  maxRetries: number = 3
): Promise<boolean> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await updateSection(sessionId, sectionId, content);
      return true;
    } catch (error) {
      if (error.message.includes('locked')) {
        // Wait and retry
        await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
        continue;
      }
      throw error;
    }
  }
  return false;
}
```

---

## Best Practices

### 1. Optimistic Updates
Update UI immediately, then sync with server:

```typescript
function handleContentChange(sectionId: string, content: string) {
  // Update UI immediately
  dispatch({ type: 'UPDATE_SECTION', payload: { sectionId, content } });

  // Debounce server update
  debouncedUpdateSection(sectionId, content);
}

const debouncedUpdateSection = debounce(async (sectionId, content) => {
  try {
    await updateSection(sessionId, sectionId, content);
  } catch (error) {
    // Revert on failure
    dispatch({ type: 'REVERT_SECTION', payload: sectionId });
    showError('Failed to save changes');
  }
}, 500);
```

### 2. Section Focus Tracking
Always tell the backend which section the user is working on:

```typescript
// When user clicks a section
function handleSectionFocus(sectionId: string) {
  focusSection(sectionId);
}

// Include in chat messages for context
function sendMessage(message: string) {
  sendMessageWithStreaming(sessionId, message, activeSectionId);
}
```

### 3. Visual Feedback for AI Operations
Show clear indicators when AI is working:

```tsx
{isStreaming && (
  <div className="ai-status-bar">
    <Spinner />
    <span>AI is working...</span>
    {currentThought && <span className="thought">{currentThought}</span>}
  </div>
)}

{lockedSections.has(sectionId) && (
  <div className="section-lock-overlay">
    <Spinner />
    <span>Generating content...</span>
  </div>
)}
```

### 4. Keyboard Shortcuts
Improve productivity with shortcuts:

```typescript
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case 'Enter':
          e.preventDefault();
          sendMessage(input, activeSectionId);
          break;
        case 'e':
          e.preventDefault();
          evaluateSection(activeSectionId);
          break;
        case 'g':
          e.preventDefault();
          sendMessage(`Generate the ${activeSectionId} section`);
          break;
      }
    }
  };

  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}, [input, activeSectionId]);
```

### 5. Progressive Loading
Load session data progressively:

```typescript
// Load basic session info first
const session = await getSession(sessionId);
dispatch({ type: 'SET_SESSION', payload: session });

// Then load detailed section data in background
for (const sectionId of Object.keys(session.sections)) {
  if (session.sections[sectionId].content) {
    // Trigger evaluation in background
    evaluateSection(sectionId).then(result => {
      dispatch({ type: 'SET_SECTION_SCORE', payload: { sectionId, score: result.score } });
    });
  }
}
```

---

## Example User Flows

### Flow 1: New Proposal Writing

```
1. User creates session
   → POST /create with call_id, title

2. User sees empty document with 7 sections
   → Frontend renders section cards

3. User clicks "excellence.objectives"
   → POST /focus/excellence.objectives

4. User types: "Write the objectives section focusing on AI for healthcare"
   → POST /message/stream
   → SSE: agent_thinking, tool_call, section_update, token, complete
   → Document viewer shows content appearing

5. User reviews generated content
   → Can edit directly in viewer (PATCH /section/{id})

6. User asks: "Evaluate this section"
   → POST /section/{id}/evaluate
   → Shows score 3.5/5 with feedback

7. User asks: "Improve the weaknesses you identified"
   → POST /message/stream
   → AI uses improve_section tool
   → Updated content appears

8. Continue for other sections...
```

### Flow 2: Improving Existing Proposal

```
1. User loads existing session
   → GET /{session_id}
   → Frontend shows current document state

2. User clicks section with low score
   → POST /focus/{section_id}

3. User asks: "What's wrong with this section?"
   → POST /message/stream
   → AI uses analyze_gaps and evaluate_section
   → Chat shows detailed analysis

4. User asks: "Fix the identified gaps"
   → AI uses improve_section
   → Content updates in viewer

5. User evaluates again
   → Score improved from 2.5 to 3.8
```

---

## Support

For issues or questions:
- Check the API health: `GET /api/v4/proposal-session/health`
- Review server logs for error details
- Ensure database migration `015_proposal_sessions.sql` has been applied
