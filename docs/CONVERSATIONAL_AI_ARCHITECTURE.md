# Conversational AI Architecture for CORDIS System

## Executive Summary

This document outlines the architecture for implementing a context-aware conversational AI system that maintains conversation history, understands context from previous messages, and can handle follow-up questions about previously discussed projects.

## Current State Analysis

### Existing Infrastructure
- **Frontend**: SvelteKit with conversation management
- **Database Schema**: 
  - `conversation` table for conversation threads
  - `message` table for individual messages
  - `ragLog` table for tracking RAG pipeline operations
- **Backend**: FastAPI with RAG service
- **Current Flow**: Each question is processed independently without context

### Key Requirements
1. Maintain conversation context across messages
2. Enable follow-up questions about previously mentioned projects
3. Support contextual references ("tell me more about the third project")
4. Remember user preferences and interests
5. Track conversation flow and topics

## Proposed Architecture

### 1. Context Management Layer

```
┌─────────────────────────────────────────────┐
│           Frontend (SvelteKit)               │
│  ┌─────────────────────────────────────┐    │
│  │   Conversation UI Component         │    │
│  │   - Message history display         │    │
│  │   - Context indicators              │    │
│  │   - Follow-up suggestions           │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│         API Gateway (FastAPI)                │
│  ┌─────────────────────────────────────┐    │
│  │   /api/conversation/message         │    │
│  │   - Accepts conversation_id         │    │
│  │   - Includes message history        │    │
│  │   - Returns contextual response     │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│     Conversation Context Manager             │
│  ┌─────────────────────────────────────┐    │
│  │   Context Extraction                │    │
│  │   - Previous projects discussed     │    │
│  │   - User interests                  │    │
│  │   - Conversation topics             │    │
│  └─────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────┐    │
│  │   Context Resolution                │    │
│  │   - Resolve references ("it", "that")│   │
│  │   - Map ordinals ("third project")  │    │
│  │   - Expand abbreviations            │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│         Enhanced RAG Service                 │
│  ┌─────────────────────────────────────┐    │
│  │   Context-Aware Query Generation    │    │
│  │   - Include conversation context    │    │
│  │   - Bias towards relevant topics    │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

### 2. Context Data Model

```python
class ConversationContext:
    conversation_id: int
    user_id: int
    
    # Message history
    messages: List[Message]
    
    # Extracted entities
    discussed_projects: List[ProjectReference]
    mentioned_organizations: List[str]
    topics_of_interest: List[str]
    
    # User preferences
    preferred_frameworks: List[str]
    preferred_countries: List[str]
    
    # Conversation state
    last_search_results: List[Dict]
    last_query_type: str  # "SEARCH_PROJECTS", "FAQ", etc.
    follow_up_expected: bool
    
class ProjectReference:
    project_id: str
    acronym: str
    title: str
    position_in_results: int  # For ordinal references
    mentioned_at: datetime
    details_shown: List[str]  # What aspects were discussed
```

### 3. Context-Aware Message Processing

#### 3.1 Input Processing Pipeline

```python
def process_message_with_context(
    conversation_id: int,
    user_message: str,
    user_id: int
) -> Dict:
    # 1. Load conversation context
    context = load_conversation_context(conversation_id)
    
    # 2. Resolve references in user message
    resolved_message = resolve_references(user_message, context)
    
    # 3. Determine if follow-up or new query
    query_type = classify_query_type(resolved_message, context)
    
    # 4. Generate context-aware search
    if query_type == "FOLLOW_UP":
        response = handle_follow_up(resolved_message, context)
    else:
        response = handle_new_query(resolved_message, context)
    
    # 5. Update context with new information
    update_context(context, user_message, response)
    
    # 6. Generate contextual response
    return format_contextual_response(response, context)
```

#### 3.2 Reference Resolution Examples

| User Input | Context | Resolved Query |
|------------|---------|----------------|
| "Tell me more about the third one" | Last results had 5 projects | "Tell me more about project ECOSENS" |
| "What about its budget?" | Last discussed EUROfusion | "What is the budget of EUROfusion project?" |
| "Show me similar projects" | Viewing nuclear energy project | "Find projects similar to nuclear energy research" |
| "Any projects from the same coordinator?" | Last project by MAX-PLANCK | "Find projects coordinated by MAX-PLANCK-GESELLSCHAFT" |

### 4. Implementation Components

#### 4.1 Conversation Context Service

```python
# app/services/conversation_context_service.py

class ConversationContextService:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.context_cache = {}  # In-memory cache
        
    def load_context(self, conversation_id: int) -> ConversationContext:
        """Load conversation context from database and cache"""
        
    def extract_entities(self, messages: List[Message]) -> Dict:
        """Extract projects, organizations, topics from message history"""
        
    def resolve_references(self, message: str, context: ConversationContext) -> str:
        """Resolve pronouns and references to concrete entities"""
        
    def update_context(self, conversation_id: int, new_data: Dict):
        """Update context with new information from latest interaction"""
        
    def get_relevant_history(self, conversation_id: int, max_messages: int = 10) -> List[Dict]:
        """Get relevant message history for prompt context"""
```

#### 4.2 Enhanced RAG Service Integration

```python
# Modify app/services/rag_service.py

class CordisRAG:
    def get_ai_response_with_context(
        self,
        question: str,
        conversation_context: ConversationContext,
        max_projects_to_process: int = 5
    ) -> Dict[str, Any]:
        """Process question with conversation context"""
        
        # Include context in prompt
        enhanced_prompt = self._build_contextual_prompt(
            question, 
            conversation_context
        )
        
        # Bias search towards discussed topics
        if conversation_context.topics_of_interest:
            search_queries = self._enhance_queries_with_context(
                queries,
                conversation_context.topics_of_interest
            )
        
        # Rest of RAG pipeline...
```

#### 4.3 API Endpoints

```python
# app/api/conversation_routes.py

@router.post("/conversation/{conversation_id}/message")
async def send_message(
    conversation_id: int,
    request: MessageRequest,
    current_user: User = Depends(get_current_user)
):
    """Send a message in a conversation with context"""
    
    # Load conversation context
    context = context_service.load_context(conversation_id)
    
    # Process with context
    response = rag_service.get_ai_response_with_context(
        question=request.message,
        conversation_context=context
    )
    
    # Save message and response
    save_message_exchange(conversation_id, request.message, response)
    
    # Return with context indicators
    return {
        "response": response["answer"],
        "context_used": context.to_summary(),
        "follow_up_suggestions": generate_follow_ups(response, context),
        "projects_discussed": context.discussed_projects
    }

@router.get("/conversation/{conversation_id}/context")
async def get_conversation_context(
    conversation_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get current conversation context"""
    context = context_service.load_context(conversation_id)
    return context.to_dict()
```

### 5. Prompt Engineering for Context

#### 5.1 Context-Aware System Prompt

```python
CONTEXT_AWARE_SYSTEM_PROMPT = """
You are a conversational AI assistant for European research projects.

CONVERSATION CONTEXT:
- Previous topics discussed: {topics}
- Projects mentioned: {projects}
- User interests: {interests}

CONVERSATION HISTORY:
{message_history}

CURRENT QUERY: {current_query}

Instructions:
1. Consider the conversation context when answering
2. Reference previously discussed projects when relevant
3. Build upon previous answers rather than repeating
4. Use pronouns and references naturally
5. Suggest relevant follow-up questions
6. Remember user preferences and interests
"""
```

#### 5.2 Follow-up Question Generation

```python
def generate_follow_up_suggestions(response: Dict, context: ConversationContext) -> List[str]:
    """Generate contextual follow-up questions"""
    
    suggestions = []
    
    if response.get("projects_found"):
        # Project-specific follow-ups
        suggestions.extend([
            "Would you like to know more about the consortium partners?",
            "Should I find similar projects in this domain?",
            "Are you interested in the funding details?"
        ])
    
    if context.discussed_projects:
        # Context-based follow-ups
        last_project = context.discussed_projects[-1]
        suggestions.extend([
            f"Would you like to compare this with {last_project.acronym}?",
            "Should I search for projects from the same time period?",
            "Are you interested in projects from the same framework programme?"
        ])
    
    return suggestions[:3]  # Limit to 3 suggestions
```

### 6. Frontend Integration

#### 6.1 SvelteKit Store for Context

```typescript
// stores/conversation.ts
import { writable, derived } from 'svelte/store';

interface ConversationContext {
  conversationId: number;
  messages: Message[];
  discussedProjects: ProjectReference[];
  currentTopic: string;
  followUpSuggestions: string[];
}

export const conversationContext = writable<ConversationContext>({
  conversationId: null,
  messages: [],
  discussedProjects: [],
  currentTopic: '',
  followUpSuggestions: []
});

// Derived store for context summary
export const contextSummary = derived(
  conversationContext,
  $context => ({
    projectCount: $context.discussedProjects.length,
    messageCount: $context.messages.length,
    hasPreviousContext: $context.messages.length > 0
  })
);
```

#### 6.2 API Client Updates

```typescript
// lib/api/conversation.ts

export async function sendMessageWithContext(
  conversationId: number,
  message: string
): Promise<ContextualResponse> {
  const response = await fetch(`/api/conversation/${conversationId}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  
  const data = await response.json();
  
  // Update context store
  conversationContext.update(ctx => ({
    ...ctx,
    messages: [...ctx.messages, { text: message, sender: 'user' }, { text: data.response, sender: 'ai' }],
    discussedProjects: data.projects_discussed,
    followUpSuggestions: data.follow_up_suggestions
  }));
  
  return data;
}
```

#### 6.3 UI Components

```svelte
<!-- components/ConversationView.svelte -->
<script lang="ts">
  import { conversationContext, contextSummary } from '$stores/conversation';
  import MessageList from './MessageList.svelte';
  import ContextIndicator from './ContextIndicator.svelte';
  import FollowUpSuggestions from './FollowUpSuggestions.svelte';
  
  async function handleSendMessage(message: string) {
    const response = await sendMessageWithContext($conversationContext.conversationId, message);
    // Response handling...
  }
</script>

<div class="conversation-container">
  {#if $contextSummary.hasPreviousContext}
    <ContextIndicator 
      projectCount={$contextSummary.projectCount}
      messageCount={$contextSummary.messageCount}
    />
  {/if}
  
  <MessageList messages={$conversationContext.messages} />
  
  {#if $conversationContext.followUpSuggestions.length > 0}
    <FollowUpSuggestions 
      suggestions={$conversationContext.followUpSuggestions}
      on:select={handleSendMessage}
    />
  {/if}
  
  <MessageInput on:send={handleSendMessage} />
</div>
```

### 7. Database Schema Updates

```sql
-- Add context tracking to conversations
ALTER TABLE conversation ADD COLUMN context_data JSONB;
ALTER TABLE conversation ADD COLUMN last_topic VARCHAR(255);
ALTER TABLE conversation ADD COLUMN user_preferences JSONB;

-- Add reference tracking to messages
ALTER TABLE message ADD COLUMN referenced_projects JSONB;
ALTER TABLE message ADD COLUMN query_type VARCHAR(50);
ALTER TABLE message ADD COLUMN context_used BOOLEAN DEFAULT FALSE;

-- Create index for faster context queries
CREATE INDEX idx_conversation_context ON conversation USING GIN (context_data);
CREATE INDEX idx_message_references ON message USING GIN (referenced_projects);
```

### 8. Implementation Phases

#### Phase 1: Basic Context Management (Week 1)
- [ ] Implement ConversationContextService
- [ ] Add context loading from message history
- [ ] Basic reference resolution ("it", "that", "the project")

#### Phase 2: Enhanced RAG Integration (Week 2)
- [ ] Modify RAG service to accept context
- [ ] Implement context-aware prompt engineering
- [ ] Add query biasing based on conversation topics

#### Phase 3: API and Frontend (Week 3)
- [ ] Create conversation API endpoints
- [ ] Update frontend stores and components
- [ ] Add follow-up suggestion generation

#### Phase 4: Advanced Features (Week 4)
- [ ] Ordinal reference resolution ("third project")
- [ ] Cross-conversation learning
- [ ] User preference tracking

### 9. Testing Strategy

#### Unit Tests
```python
def test_reference_resolution():
    context = ConversationContext(
        discussed_projects=[
            ProjectReference(acronym="ECOSENS", position=1),
            ProjectReference(acronym="APRENDE", position=2)
        ]
    )
    
    assert resolve_references("tell me about the first one", context) == "tell me about ECOSENS"
    assert resolve_references("what about its budget?", context) == "what about APRENDE budget?"
```

#### Integration Tests
- Test full conversation flow with multiple turns
- Verify context persistence across messages
- Test reference resolution accuracy
- Validate follow-up suggestion relevance

### 10. Performance Considerations

#### Caching Strategy
- Cache conversation context in Redis/memory
- TTL: 30 minutes of inactivity
- Lazy load full message history (last 10 messages by default)

#### Context Size Management
- Limit message history to last 20 messages for prompt
- Summarize older messages if needed
- Track only last 10 discussed projects

#### Response Time Optimization
- Parallel processing of context extraction and query resolution
- Pre-compute follow-up suggestions
- Background context updates

## Conclusion

This architecture provides a comprehensive solution for implementing conversational AI with context awareness. It leverages your existing database schema while adding the necessary components for maintaining and utilizing conversation context effectively.

The system will enable natural conversations where users can:
- Ask follow-up questions using references
- Explore topics in depth across multiple messages
- Get personalized responses based on conversation history
- Receive relevant suggestions for continued exploration

Next steps:
1. Review and approve the architecture
2. Begin Phase 1 implementation
3. Set up testing infrastructure
4. Plan frontend UI updates