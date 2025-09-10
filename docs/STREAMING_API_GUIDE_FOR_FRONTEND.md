# Streaming API Guide for Frontend Implementation

## Streaming Endpoint

**URL:** `POST /api/conversation/{conversation_id}/message/stream`

**Purpose:** Send a message and receive a streaming response with real-time progress updates and token-by-token answer delivery.

## Request Format

```typescript
// Request body
{
  "message": "Find nuclear energy projects in Europe",
  "include_context": true  // optional, defaults to true
}

// Example fetch request
const response = await fetch(`/api/conversation/${conversationId}/message/stream`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream'
  },
  body: JSON.stringify({
    message: userMessage,
    include_context: true
  })
});
```

## Response Format (Server-Sent Events)

The endpoint returns a stream of events in Server-Sent Events format. Each event is a JSON object with different types:

### 1. Status Events
```json
{
  "type": "status",
  "stage": "context_loaded",
  "message": "Conversation context loaded"
}
```

### 2. Progress Events
```json
{
  "type": "progress", 
  "stage": "data_retrieval",
  "message": "Searching CORDIS API and enriching with database..."
}
```

### 3. Token Events (Streaming Response)
```json
{
  "type": "token",
  "content": "The nuclear energy research landscape in Europe..."
}
```

### 4. Completion Event
```json
{
  "type": "complete",
  "follow_up_suggestions": [
    "Tell me more about SANE's consortium partners",
    "What is the budget of APRENDE?",
    "Find similar projects to ECOSENS"
  ],
  "context_used": true,
  "resolved_question": "Find nuclear energy projects in Europe",
  "projects_discussed": [
    {
      "project_id": "SANE",
      "acronym": "SANE", 
      "title": "Safety Assessment of Non-Electric uses of nuclear energy",
      "position_in_results": 0
    }
  ],
  "processing_time": 8.5
}
```

### 5. Error Events
```json
{
  "type": "error",
  "error": "Processing failed",
  "details": "Database connection timeout"
}
```

## Processing Stages

The system goes through these stages and sends progress updates:

1. **context_loaded** - Conversation context loaded
2. **reference_resolved** - References like "the first one" resolved
3. **processing** - Starting to process the question
4. **context_resolution** - Resolving references and loading context
5. **intent_detection** - Analyzing question intent
6. **intent_detected** - Intent determined (SEARCH_PROJECTS, FAQ, etc.)
7. **query_extraction** - Extracting search queries
8. **queries_extracted** - Search queries generated
9. **data_retrieval** - Searching CORDIS API and database
10. **data_enriched** - Projects found and enriched with database
11. **data_selected** - Most relevant projects selected
12. **reranking** - Projects ranked by relevance
13. **answer_generation** - Generating comprehensive answer
14. **context_enhancement** - Adding conversational context
15. **streaming_response** - Delivering the answer

## Frontend Implementation Example

```typescript
async function sendStreamingMessage(conversationId: number, message: string) {
  const response = await fetch(`/api/conversation/${conversationId}/message/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream'
    },
    body: JSON.stringify({
      message: message,
      include_context: true
    })
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  
  let currentAnswer = '';
  let followUpSuggestions: string[] = [];
  
  if (reader) {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            
            switch (data.type) {
              case 'status':
              case 'progress':
                // Update progress indicator
                updateProgressIndicator(data.stage, data.message);
                break;
                
              case 'token':
                // Append to current answer
                currentAnswer += data.content;
                updateStreamingMessage(currentAnswer);
                break;
                
              case 'complete':
                // Handle completion
                followUpSuggestions = data.follow_up_suggestions || [];
                showFollowUpSuggestions(followUpSuggestions);
                hideProgressIndicator();
                break;
                
              case 'error':
                // Handle error
                showError(data.error, data.details);
                break;
            }
          } catch (e) {
            console.warn('Failed to parse SSE data:', line);
          }
        }
      }
    }
  }
}
```

## Key Features

### 1. Conversation Context
- Automatically tracks discussed projects
- Resolves references like "the first one", "its budget"
- Maintains conversation history

### 2. Real-time Updates
- Shows exactly what the AI is doing at each stage
- Progress indicators for better UX
- Smooth token-by-token streaming

### 3. Follow-up Suggestions
- Intelligent suggestions based on conversation
- Project-specific questions
- Topic-based exploration

### 4. Error Handling
- Graceful error messages
- Fallback to non-streaming if needed
- Connection recovery

## Alternative: Non-Streaming with Context

If you prefer non-streaming but still want context:

```typescript
// Use the regular endpoint with conversation_id
const response = await fetch('/api/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: message,
    conversation_id: conversationId  // This enables context
  })
});
```

## Testing the Endpoint

```bash
# Test with curl
curl -N -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "Find nuclear projects", "include_context": true}' \
  http://localhost:8000/api/conversation/1/message/stream
```

## Summary for Frontend AI

**Endpoint:** `POST /api/conversation/{conversation_id}/message/stream`

**Input:** 
- `message`: User's question
- `include_context`: Boolean (optional, defaults to true)

**Output:** Server-Sent Events stream with:
- Progress updates during processing
- Token-by-token response streaming  
- Follow-up suggestions on completion
- Error handling

**Key benefit:** Maintains conversation context so "tell me about the first one" works correctly by referencing previously discussed projects.