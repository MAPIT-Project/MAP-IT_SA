
# Conversation Context Implementation Guide

## Quick Start: Minimal Changes for Maximum Impact

This guide provides practical, implementable code to add conversational context to your existing CORDIS system with minimal disruption.

## Step 1: Create the Conversation Context Service

```python
# app/services/conversation_context_service.py

import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2.extras import DictCursor

@dataclass
class ProjectReference:
    """Reference to a project discussed in conversation"""
    project_id: str
    acronym: str
    title: str
    position_in_results: int
    mentioned_at: str
    framework_programme: str = None
    
@dataclass
class ConversationContext:
    """Complete context for a conversation"""
    conversation_id: int
    user_id: int
    messages: List[Dict[str, Any]]
    discussed_projects: List[ProjectReference]
    mentioned_organizations: List[str]
    topics_of_interest: List[str]
    last_search_results: List[Dict[str, Any]]
    last_query_type: str
    follow_up_expected: bool
    
    def to_dict(self):
        return {
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'message_count': len(self.messages),
            'projects_discussed': len(self.discussed_projects),
            'current_topics': self.topics_of_interest[:3] if self.topics_of_interest else []
        }
    
    def get_recent_messages(self, count: int = 5) -> List[Dict]:
        """Get recent messages for prompt context"""
        return self.messages[-count:] if self.messages else []
    
    def find_project_by_reference(self, reference: str) -> Optional[ProjectReference]:
        """Find a project by various references (ordinal, name, pronoun)"""
        reference_lower = reference.lower()
        
        # Check for ordinal references
        ordinal_map = {
            'first': 0, '1st': 0,
            'second': 1, '2nd': 1,
            'third': 2, '3rd': 2,
            'fourth': 3, '4th': 3,
            'fifth': 4, '5th': 4,
            'last': -1, 'latest': -1
        }
        
        for ordinal, index in ordinal_map.items():
            if ordinal in reference_lower:
                if 0 <= index < len(self.discussed_projects):
                    return self.discussed_projects[index]
                elif index == -1 and self.discussed_projects:
                    return self.discussed_projects[-1]
        
        # Check for acronym or title match
        for project in self.discussed_projects:
            if (project.acronym.lower() in reference_lower or 
                reference_lower in project.title.lower()):
                return project
        
        # Check for "it", "that", "the project" - return most recent
        if reference_lower in ['it', 'that', 'the project', 'this project']:
            return self.discussed_projects[-1] if self.discussed_projects else None
        
        return None


class ConversationContextService:
    """Service for managing conversation context"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.context_cache = {}  # Simple in-memory cache
        
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    def load_context(self, conversation_id: int) -> ConversationContext:
        """Load conversation context from database"""
        
        # Check cache first
        if conversation_id in self.context_cache:
            cached_context, timestamp = self.context_cache[conversation_id]
            if datetime.now() - timestamp < timedelta(minutes=30):
                return cached_context
        
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        try:
            # Get conversation info
            cursor.execute("""
                SELECT c.*, 
                       COUNT(m.id) as message_count
                FROM conversation c
                LEFT JOIN message m ON c.id = m."conversationId"
                WHERE c.id = %s
                GROUP BY c.id
            """, (conversation_id,))
            
            conv_data = cursor.fetchone()
            if not conv_data:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # Get recent messages
            cursor.execute("""
                SELECT id, text, sender, "createdAt",
                       "modelUsed", "projectsRetrieved"
                FROM message
                WHERE "conversationId" = %s
                ORDER BY "createdAt" DESC
                LIMIT 20
            """, (conversation_id,))
            
            messages = [dict(row) for row in cursor.fetchall()]
            messages.reverse()  # Put in chronological order
            
            # Extract context from messages
            context = self._extract_context_from_messages(
                conversation_id,
                conv_data['user_id'],
                messages
            )
            
            # Cache the context
            self.context_cache[conversation_id] = (context, datetime.now())
            
            return context
            
        finally:
            cursor.close()
            conn.close()
    
    def _extract_context_from_messages(
        self, 
        conversation_id: int,
        user_id: int,
        messages: List[Dict]
    ) -> ConversationContext:
        """Extract context information from message history"""
        
        discussed_projects = []
        mentioned_organizations = set()
        topics = set()
        last_search_results = []
        last_query_type = None
        
        for msg in messages:
            text = msg['text']
            
            # Extract project mentions (simple pattern matching)
            # Look for patterns like "project ACRONYM" or "ACRONYM project"
            project_pattern = r'\b([A-Z]{3,}(?:-[A-Z]+)*)\b'
            potential_acronyms = re.findall(project_pattern, text)
            
            for acronym in potential_acronyms:
                # Check if this looks like a project acronym
                if len(acronym) >= 3 and acronym not in ['API', 'SQL', 'JSON', 'HTTP']:
                    # Try to extract more info from surrounding text
                    title_match = re.search(
                        rf'{acronym}[:\s-]+([^.!?\n]+)',
                        text
                    )
                    title = title_match.group(1) if title_match else acronym
                    
                    discussed_projects.append(ProjectReference(
                        project_id=acronym,
                        acronym=acronym,
                        title=title,
                        position_in_results=len(discussed_projects),
                        mentioned_at=msg['createdAt'].isoformat() if isinstance(msg['createdAt'], datetime) else str(msg['createdAt'])
                    ))
            
            # Extract organization mentions
            org_pattern = r'(?:coordinated by|led by|participant[s]?:?)\s+([A-Z][A-Za-z\s&]+(?:University|Institute|Centre|Center|GmbH|Ltd|Inc|Corporation|Company|Foundation))'
            orgs = re.findall(org_pattern, text, re.IGNORECASE)
            mentioned_organizations.update(orgs)
            
            # Extract topics (simple keyword extraction)
            topic_keywords = ['nuclear', 'energy', 'renewable', 'solar', 'wind', 
                            'research', 'innovation', 'technology', 'climate',
                            'environment', 'health', 'digital', 'AI', 'quantum']
            
            for keyword in topic_keywords:
                if keyword.lower() in text.lower():
                    topics.add(keyword)
            
            # Check for query type indicators
            if 'SEARCH_PROJECTS' in text or 'projects found' in text:
                last_query_type = 'SEARCH_PROJECTS'
            elif 'SEARCH_CALLS' in text or 'calls found' in text:
                last_query_type = 'SEARCH_CALLS'
            elif 'FAQ' in text:
                last_query_type = 'FAQ'
        
        return ConversationContext(
            conversation_id=conversation_id,
            user_id=user_id,
            messages=messages,
            discussed_projects=discussed_projects,
            mentioned_organizations=list(mentioned_organizations),
            topics_of_interest=list(topics),
            last_search_results=last_search_results,
            last_query_type=last_query_type or 'UNKNOWN',
            follow_up_expected=True if discussed_projects else False
        )
    
    def resolve_references(self, message: str, context: ConversationContext) -> str:
        """Resolve references in user message to concrete entities"""
        
        resolved = message
        
        # Pattern for "tell me more about X"
        more_pattern = r'tell me (?:more )?about (the )?(first|second|third|fourth|fifth|last|latest|it|that|this)( one| project)?'
        match = re.search(more_pattern, resolved, re.IGNORECASE)
        
        if match:
            reference = match.group(2)
            project = context.find_project_by_reference(reference)
            if project:
                resolved = resolved.replace(
                    match.group(0),
                    f'tell me more about {project.acronym} ({project.title})'
                )
        
        # Pattern for "what about its X"
        its_pattern = r'what about (?:its|the) (\w+)'
        match = re.search(its_pattern, resolved, re.IGNORECASE)
        
        if match and context.discussed_projects:
            last_project = context.discussed_projects[-1]
            resolved = resolved.replace(
                'its', f"{last_project.acronym}'s"
            ).replace(
                'the project', last_project.acronym
            )
        
        # Pattern for "show me similar projects"
        if 'similar' in resolved.lower() and context.discussed_projects:
            last_project = context.discussed_projects[-1]
            resolved = f"Find projects similar to {last_project.acronym} in the {' '.join(context.topics_of_interest)} domain"
        
        return resolved
    
    def update_context(self, conversation_id: int, new_message: Dict, response: Dict):
        """Update context with new information"""
        
        if conversation_id in self.context_cache:
            context, _ = self.context_cache[conversation_id]
            
            # Add new message to history
            context.messages.append(new_message)
            
            # Extract projects from response
            if 'projects_found' in response:
                for i, project in enumerate(response.get('project_data', [])):
                    context.discussed_projects.append(ProjectReference(
                        project_id=project.get('id', 'N/A'),
                        acronym=project.get('acronym', 'N/A'),
                        title=project.get('title', 'Unknown'),
                        position_in_results=i,
                        mentioned_at=datetime.now().isoformat(),
                        framework_programme=project.get('frameworkProgramme', 'N/A')
                    ))
            
            # Update cache
            self.context_cache[conversation_id] = (context, datetime.now())
    
    def generate_follow_up_suggestions(
        self, 
        context: ConversationContext,
        last_response: Dict
    ) -> List[str]:
        """Generate contextual follow-up suggestions"""
        
        suggestions = []
        
        if context.discussed_projects:
            last_project = context.discussed_projects[-1]
            
            # Project-specific suggestions
            suggestions.extend([
                f"Tell me more about {last_project.acronym}'s consortium partners",
                f"What is the budget of {last_project.acronym}?",
                f"Find similar projects to {last_project.acronym}"
            ])
            
            # Framework-specific suggestions
            if last_project.framework_programme:
                suggestions.append(
                    f"Show me other {last_project.framework_programme} projects"
                )
        
        # Topic-based suggestions
        if context.topics_of_interest:
            topic = context.topics_of_interest[0]
            suggestions.append(f"Find more recent {topic} projects")
        
        # General suggestions based on last query type
        if context.last_query_type == 'SEARCH_PROJECTS':
            suggestions.extend([
                "Show me projects from different countries",
                "Find projects with larger consortiums",
                "What are the most recent projects in this area?"
            ])
        
        return suggestions[:4]  # Return top 4 suggestions
```

## Step 2: Modify RAG Service for Context Support

```python
# Add to app/services/rag_service.py

def get_ai_response_with_context(
    self,
    question: str,
    conversation_context: ConversationContext,
    max_projects_to_process: int = 5,
    max_cordis_results: int = 10
) -> Dict[str, Any]:
    """
    Process question with conversation context.
    This is the context-aware version of get_ai_response.
    """
    
    # Resolve references in the question
    from app.services.conversation_context_service import ConversationContextService
    context_service = ConversationContextService(os.getenv("DATABASE_URL"))
    resolved_question = context_service.resolve_references(question, conversation_context)
    
    print(f"🧠 Original question: {question}")
    print(f"🎯 Resolved question: {resolved_question}")
    
    # Build context-aware prompt
    context_prompt = self._build_context_prompt(conversation_context)
    
    # Get the base response using existing method
    response = self.get_ai_response_with_routing(
        resolved_question,
        max_projects_to_process,
        max_cordis_results
    )
    
    # Enhance the answer with context
    if conversation_context.discussed_projects:
        enhanced_answer = self._enhance_answer_with_context(
            response['answer'],
            conversation_context,
            resolved_question
        )
        response['answer'] = enhanced_answer
    
    # Add context information to response
    response['context_used'] = True
    response['resolved_question'] = resolved_question
    response['discussed_projects'] = [
        asdict(p) for p in conversation_context.discussed_projects
    ]
    
    # Generate follow-up suggestions
    response['follow_up_suggestions'] = context_service.generate_follow_up_suggestions(
        conversation_context,
        response
    )
    
    return response

def _build_context_prompt(self, context: ConversationContext) -> str:
    """Build context information for the prompt"""
    
    prompt_parts = []
    
    # Add recent conversation history
    recent_messages = context.get_recent_messages(5)
    if recent_messages:
        prompt_parts.append("Recent conversation:")
        for msg in recent_messages:
            sender = msg['sender']
            text = msg['text'][:200]  # Truncate long messages
            prompt_parts.append(f"  {sender}: {text}")
    
    # Add discussed projects
    if context.discussed_projects:
        prompt_parts.append("\nProjects discussed:")
        for proj in context.discussed_projects[-5:]:  # Last 5 projects
            prompt_parts.append(f"  - {proj.acronym}: {proj.title}")
    
    # Add topics of interest
    if context.topics_of_interest:
        prompt_parts.append(f"\nTopics of interest: {', '.join(context.topics_of_interest)}")
    
    return "\n".join(prompt_parts)

def _enhance_answer_with_context(
    self,
    base_answer: str,
    context: ConversationContext,
    question: str
) -> str:
    """Enhance answer with conversational context"""
    
    # Create context-aware prompt
    enhancement_prompt = f"""
You are continuing a conversation about European research projects.

CONVERSATION CONTEXT:
{self._build_context_prompt(context)}

CURRENT QUESTION: {question}

BASE ANSWER: {base_answer}

Please enhance this answer by:
1. Referencing previously discussed projects when relevant
2. Making connections to topics already explored
3. Using natural language that acknowledges the conversation history
4. Avoiding repetition of information already provided
5. Suggesting natural follow-up questions

Enhanced answer:
"""
    
    # Call LLM for enhancement
    enhanced = self._call_llm_for_generation(
        "You are a conversational AI assistant that maintains context across messages.",
        enhancement_prompt
    )
    
    return enhanced
```

## Step 3: Create API Endpoints

```python
# app/api/conversation_routes.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
from app.services.rag_service import CordisRAG
from app.services.conversation_context_service import ConversationContextService

router = APIRouter(prefix="/api/conversation", tags=["conversation"])

# Initialize services
rag_service = CordisRAG(use_local_db=False)
context_service = ConversationContextService(os.getenv("DATABASE_URL"))

class MessageRequest(BaseModel):
    message: str
    include_context: bool = True

class MessageResponse(BaseModel):
    response: str
    context_used: bool
    resolved_question: Optional[str]
    follow_up_suggestions: List[str]
    projects_discussed: List[dict]
    processing_time: float

@router.post("/{conversation_id}/message", response_model=MessageResponse)
async def send_contextual_message(
    conversation_id: int,
    request: MessageRequest
):
    """Send a message with conversation context"""
    
    import time
    start_time = time.time()
    
    try:
        # Load conversation context
        if request.include_context:
            context = context_service.load_context(conversation_id)
        else:
            # Create minimal context for non-contextual queries
            context = ConversationContext(
                conversation_id=conversation_id,
                user_id=0,
                messages=[],
                discussed_projects=[],
                mentioned_organizations=[],
                topics_of_interest=[],
                last_search_results=[],
                last_query_type='UNKNOWN',
                follow_up_expected=False
            )
        
        # Process with RAG service
        response = rag_service.get_ai_response_with_context(
            question=request.message,
            conversation_context=context
        )
        
        # Save message to database (implement this based on your schema)
        # save_message(conversation_id, request.message, response['answer'])
        
        # Update context with new information
        context_service.update_context(
            conversation_id,
            {'text': request.message, 'sender': 'user'},
            response
        )
        
        processing_time = time.time() - start_time
        
        return MessageResponse(
            response=response['answer'],
            context_used=response.get('context_used', False),
            resolved_question=response.get('resolved_question'),
            follow_up_suggestions=response.get('follow_up_suggestions', []),
            projects_discussed=response.get('discussed_projects', []),
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{conversation_id}/context")
async def get_conversation_context(conversation_id: int):
    """Get the current context for a conversation"""
    
    try:
        context = context_service.load_context(conversation_id)
        return {
            'conversation_id': conversation_id,
            'message_count': len(context.messages),
            'projects_discussed': [asdict(p) for p in context.discussed_projects],
            'topics': context.topics_of_interest,
            'last_query_type': context.last_query_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{conversation_id}/reset-context")
async def reset_conversation_context(conversation_id: int):
    """Reset the context for a conversation"""
    
    # Clear from cache
    if conversation_id in context_service.context_cache:
        del context_service.context_cache[conversation_id]
    
    return {"message": "Context reset successfully"}
```

## Step 4: Frontend Integration (SvelteKit)

```typescript
// lib/stores/conversation.ts

import { writable, derived } from 'svelte/store';
import type { Writable, Readable } from 'svelte/store';

export interface ProjectReference {
  project_id: string;
  acronym: string;
  title: string;
  position_in_results: number;
  framework_programme?: string;
}

export interface ConversationContext {
  conversationId: number;
  messages: Array<{
    text: string;
    sender: 'user' | 'ai' | 'system';
    timestamp: string;
  }>;
  discussedProjects: ProjectReference[];
  followUpSuggestions: string[];
  isContextual: boolean;
}

function createConversationStore() {
  const { subscribe, set, update }: Writable<ConversationContext> = writable({
    conversationId: 0,
    messages: [],
    discussedProjects: [],
    followUpSuggestions: [],
    isContextual: true
  });

  return {
    subscribe,
    setConversation: (id: number) => update(ctx => ({ ...ctx, conversationId: id })),
    addMessage: (message: any) => update(ctx => ({
      ...ctx,
      messages: [...ctx.messages, message]
    })),
    updateProjects: (projects: ProjectReference[]) => update(ctx => ({
      ...ctx,
      discussedProjects: projects
    })),
    updateSuggestions: (suggestions: string[]) => update(ctx => ({
      ...ctx,
      followUpSuggestions: suggestions
    })),
    toggleContext: () => update(ctx => ({
      ...ctx,
      isContextual: !ctx.isContextual
    })),
    reset: () => set({
      conversationId: 0,
      messages: [],
      discussedProjects: [],
      followUpSuggestions: [],
      isContextual: true
    })
  };
}

export const conversationStore = createConversationStore();

// Derived store for context summary
export const contextSummary: Readable<any> = derived(
  conversationStore,
  $store => ({
    hasContext: $store.messages.length > 0,
    projectCount: $store.discussedProjects.length,
    messageCount: $store.messages.length,
    lastProject: $store.discussedProjects[$store.discussedProjects.length - 1] || null
  })
);
```

```typescript
// lib/api/conversation.ts

export interface MessageRequest {
  message: string;
  include_context?: boolean;
}

export interface MessageResponse {
  response: string;
  context_used: boolean;
  resolved_question?: string;
  follow_up_suggestions: string[];
  projects_discussed: any[];
  processing_time: number;
}

export async function sendContextualMessage(
  conversationId: number,
  message: string,
  includeContext: boolean = true
): Promise<MessageResponse> {
  const response = await fetch(`/api/proxy/conversation/${conversationId}/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      include_context: includeContext
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to send message: ${response.statusText}`);
  }

  return response.json();
}

export async function getConversationContext(conversationId: number) {
  const response = await fetch(`/api/proxy/conversation/${conversationId}/context`);
  
  if (!response.ok) {
    throw new Error(`Failed to get context: ${response.statusText}`);
  }

  return response.json();
}
```

```svelte
<!-- components/ConversationInterface.svelte -->
<script lang="ts">
  import { conversationStore, contextSummary } from '$lib/stores/conversation';
  import { sendContextualMessage } from '$lib/api/conversation';
  import MessageBubble from './MessageBubble.svelte';
  import FollowUpSuggestions from './FollowUpSuggestions.svelte';
  import ContextIndicator from './ContextIndicator.svelte';
  
  export let conversationId: number;
  
  let inputMessage = '';
  let isLoading = false;
  
  $: conversationStore.setConversation(conversationId);
  
  async function handleSendMessage(message: string = inputMessage) {
    if (!message.trim() || isLoading) return;
    
    isLoading = true;
    const userMessage = message;
    inputMessage = '';
    
    // Add user message to store
    conversationStore.addMessage({
      text: userMessage,
      sender: 'user',
      timestamp: new Date().toISOString()
    });
    
    try {
      const response = await sendContextualMessage(
        conversationId,
        userMessage,
        $conversationStore.isContextual
      );
      
      // Add AI response to store
      conversationStore.addMessage({
        text: response.response,
        sender: 'ai',
        timestamp: new Date().toISOString()
      });
      
      // Update context information
      conversationStore.updateProjects(response.projects_discussed);
      conversationStore.updateSuggestions(response.follow_up_suggestions);
      
      // Show resolved question if different
      if (response.resolved_question && response.resolved_question !== userMessage) {
        conversationStore.addMessage({
          text: `Understood as: "${response.resolved_question}"`,
          sender: 'system',
          timestamp: new Date().toISOString()
        });
      }
      
    } catch (error) {
      console.error('Failed to send message:', error);
      conversationStore.addMessage({
        text: 'Sorry, I encountered an error processing your message.',
        sender: 'system',
        timestamp: new Date().toISOString()
      });
    } finally {
      isLoading = false;
    }
  }
</script>

<div class="conversation-container">
  <!-- Context Indicator -->
  {#if $contextSummary.hasContext}
    <ContextIndicator 
      projectCount={$contextSummary.projectCount}
      messageCount={$contextSummary.messageCount}
      isContextual={$conversationStore.isContextual}
      on:toggle={() => conversationStore.toggleContext()}
    />
  {/if}
  
  <!-- Messages -->
  <div class="messages-container">
    {#each $conversationStore.messages as message}
      <MessageBubble 
        text={message.text}
        sender={message.sender}
        timestamp={message.timestamp}
      />
    {/each}
    
    {#if isLoading}
      <div class="loading-indicator">AI is thinking...</div>
    {/if}
  </div>
  
  <!-- Follow-up Suggestions -->
  {#if $conversationStore.followUpSuggestions.length > 0 && !isLoading}
    <FollowUpSuggestions 
      suggestions={$conversationStore.followUpSuggestions}
      on:select={(e) => handleSendMessage(e.detail)}
    />
  {/if}
  
  <!-- Input Area -->
  <div class="input-container">
    <input
      type="text"
      bind:value={inputMessage}
      on:keypress={(e) => e.key === 'Enter' && handleSendMessage()}
      placeholder={$contextSummary.hasContext 
        ? "Ask a follow-up question..." 
        : "Ask about European research projects..."}
      disabled={isLoading}
    />
    <button 
      on:click={() => handleSendMessage()}
      disabled={!inputMessage.trim() || isLoading}
    >
      Send
    </button>
  </div>
</div>

<style>
  .conversation-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    max-width: 800px;
    margin: 0 auto;
  }
  
  .messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  
  .loading-indicator {
    padding: 0.5rem;
    text-align: center;
    color: #666;
    font-style: italic;
  }
  
  .input-container {
    display: flex;
    gap: 0.5rem;
    padding: 1rem;
    border-top: 1px solid #e0e0e0;
  }
  
  input {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
  }
  
  button {
    padding: 0.75rem 1.5rem;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
  }
  
  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
```

## Step 5: Testing the Implementation

```python
# test_conversation_context.py

import pytest
from app.services.conversation_context_service import (
    ConversationContextService,
    ConversationContext,
    ProjectReference
)

def test_reference_resolution():
    """Test that references are correctly resolved"""
    
    context = ConversationContext(
        conversation_id=1,
        user_id=1,
        messages=[],
        discussed_projects=[
            ProjectReference(
                project_id="101",
                acronym="ECOSENS",
                title="Economic and Social Considerations",
                position_in_results=0,
                mentioned_at="2024-01-01"
            ),
            ProjectReference(
                project_id="102",
                acronym="APRENDE",
                title="Addressing Priorities",
                position_in_results=1,
                mentioned_at="2024-01-02"
            )
        ],
        mentioned_organizations=[],
        topics_of_interest=["nuclear", "energy"],
        last_search_results=[],
        last_query_type="SEARCH_PROJECTS",
        follow_up_expected=True
    )
    
    service = ConversationContextService("postgresql://test")
    
    # Test ordinal references
    assert "ECOSENS" in service.resolve_references(
        "tell me more about the first one", context
    )
    
    # Test pronoun references
    assert "APRENDE" in service.resolve_references(
        "what about its budget?", context
    )
    
    # Test similarity requests
    resolved = service.resolve_references(
        "show me similar projects", context
    )
    assert "APRENDE" in resolved
    assert "nuclear" in resolved.lower()

def test_follow_up_generation():
