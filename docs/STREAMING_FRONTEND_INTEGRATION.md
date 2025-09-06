# Streaming Frontend Integration for SvelteKit

## Overview

This document provides complete implementation for streaming conversational AI responses in SvelteKit with real-time stage updates.

## Backend Streaming API

The backend now provides:
- `POST /api/conversation/{id}/message/stream` - Server-Sent Events endpoint
- Real-time progress updates during processing
- Token-by-token response streaming
- Context-aware conversation handling

## Frontend Implementation

### 1. Streaming Store (SvelteKit)

```typescript
// lib/stores/streamingConversation.ts

import { writable, derived } from 'svelte/store';
import type { Writable, Readable } from 'svelte/store';

export interface StreamingMessage {
  id: string;
  text: string;
  sender: 'user' | 'ai' | 'system';
  timestamp: string;
  isStreaming?: boolean;
  isComplete?: boolean;
}

export interface ProcessingStage {
  stage: string;
  message: string;
  timestamp: string;
}

export interface StreamingConversationState {
  conversationId: number;
  messages: StreamingMessage[];
  currentStage: ProcessingStage | null;
  isProcessing: boolean;
  followUpSuggestions: string[];
  discussedProjects: any[];
  contextUsed: boolean;
}

function createStreamingConversationStore() {
  const { subscribe, set, update }: Writable<StreamingConversationState> = writable({
    conversationId: 0,
    messages: [],
    currentStage: null,
    isProcessing: false,
    followUpSuggestions: [],
    discussedProjects: [],
    contextUsed: false
  });

  return {
    subscribe,
    
    setConversation: (id: number) => update(state => ({ 
      ...state, 
      conversationId: id 
    })),
    
    addUserMessage: (text: string) => update(state => ({
      ...state,
      messages: [...state.messages, {
        id: Date.now().toString(),
        text,
        sender: 'user',
        timestamp: new Date().toISOString(),
        isComplete: true
      }]
    })),
    
    startAIResponse: () => {
      const messageId = Date.now().toString();
      update(state => ({
        ...state,
        isProcessing: true,
        messages: [...state.messages, {
          id: messageId,
          text: '',
          sender: 'ai',
          timestamp: new Date().toISOString(),
          isStreaming: true,
          isComplete: false
        }]
      }));
      return messageId;
    },
    
    updateStage: (stage: ProcessingStage) => update(state => ({
      ...state,
      currentStage: stage
    })),
    
    appendToAIMessage: (messageId: string, content: string) => update(state => ({
      ...state,
      messages: state.messages.map(msg => 
        msg.id === messageId 
          ? { ...msg, text: msg.text + content }
          : msg
      )
    })),
    
    completeAIMessage: (messageId: string, metadata: any) => update(state => ({
      ...state,
      isProcessing: false,
      currentStage: null,
      followUpSuggestions: metadata.follow_up_suggestions || [],
      discussedProjects: metadata.projects_discussed || [],
      contextUsed: metadata.context_used || false,
      messages: state.messages.map(msg => 
        msg.id === messageId 
          ? { ...msg, isStreaming: false, isComplete: true }
          : msg
      )
    })),
    
    setError: (error: string) => update(state => ({
      ...state,
      isProcessing: false,
      currentStage: null,
      messages: [...state.messages, {
        id: Date.now().toString(),
        text: `Error: ${error}`,
        sender: 'system',
        timestamp: new Date().toISOString(),
        isComplete: true
      }]
    })),
    
    reset: () => set({
      conversationId: 0,
      messages: [],
      currentStage: null,
      isProcessing: false,
      followUpSuggestions: [],
      discussedProjects: [],
      contextUsed: false
    })
  };
}

export const streamingConversationStore = createStreamingConversationStore();

// Derived stores
export const conversationSummary: Readable<any> = derived(
  streamingConversationStore,
  $store => ({
    messageCount: $store.messages.length,
    projectCount: $store.discussedProjects.length,
    hasContext: $store.contextUsed,
    isActive: $store.isProcessing,
    currentStage: $store.currentStage?.stage || null
  })
);
```

### 2. Streaming API Client

```typescript
// lib/api/streamingConversation.ts

export interface StreamingEventData {
  type: 'progress' | 'token' | 'complete' | 'error';
  stage?: string;
  message?: string;
  content?: string;
  error?: string;
  details?: string;
  [key: string]: any;
}

export class StreamingConversationClient {
  private eventSource: EventSource | null = null;
  
  async sendStreamingMessage(
    conversationId: number,
    message: string,
    includeContext: boolean = true,
    onProgress?: (stage: string, message: string) => void,
    onToken?: (content: string) => void,
    onComplete?: (metadata: any) => void,
    onError?: (error: string) => void
  ): Promise<void> {
    
    // Close any existing connection
    this.closeConnection();
    
    try {
      // Create the streaming request
      const url = `/api/proxy/conversation/${conversationId}/message/stream`;
      const requestBody = {
        message,
        include_context: includeContext
      };
      
      // Use fetch to initiate the stream
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(requestBody)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      // Process the stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      
      if (!reader) {
        throw new Error('No response body reader available');
      }
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: StreamingEventData = JSON.parse(line.slice(6));
              
              switch (data.type) {
                case 'progress':
                case 'status':
                  onProgress?.(data.stage || 'processing', data.message || '');
                  break;
                  
                case 'token':
                  onToken?.(data.content || '');
                  break;
                  
                case 'complete':
                  onComplete?.(data);
                  return; // End the stream
                  
                case 'error':
                  onError?.(data.error || 'Unknown error');
                  return; // End the stream
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', line);
            }
          }
        }
      }
      
    } catch (error) {
      console.error('Streaming error:', error);
      onError?.(error instanceof Error ? error.message : 'Connection failed');
    }
  }
  
  closeConnection() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

export const streamingClient = new StreamingConversationClient();
```

### 3. Streaming Conversation Component

```svelte
<!-- components/StreamingConversationInterface.svelte -->
<script lang="ts">
  import { streamingConversationStore, conversationSummary } from '$lib/stores/streamingConversation';
  import { streamingClient } from '$lib/api/streamingConversation';
  import StreamingMessageBubble from './StreamingMessageBubble.svelte';
  import ProcessingStageIndicator from './ProcessingStageIndicator.svelte';
  import FollowUpSuggestions from './FollowUpSuggestions.svelte';
  
  export let conversationId: number;
  
  let inputMessage = '';
  let messagesContainer: HTMLElement;
  
  $: streamingConversationStore.setConversation(conversationId);
  
  // Auto-scroll to bottom when new content arrives
  $: if ($streamingConversationStore.messages.length > 0) {
    setTimeout(() => {
      messagesContainer?.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: 'smooth'
      });
    }, 100);
  }
  
  async function handleSendMessage(message: string = inputMessage) {
    if (!message.trim() || $streamingConversationStore.isProcessing) return;
    
    const userMessage = message;
    inputMessage = '';
    
    // Add user message
    streamingConversationStore.addUserMessage(userMessage);
    
    // Start AI response
    const aiMessageId = streamingConversationStore.startAIResponse();
    
    // Send streaming request
    await streamingClient.sendStreamingMessage(
      conversationId,
      userMessage,
      true, // include context
      
      // onProgress
      (stage: string, message: string) => {
        streamingConversationStore.updateStage({
          stage,
          message,
          timestamp: new Date().toISOString()
        });
      },
      
      // onToken
      (content: string) => {
        streamingConversationStore.appendToAIMessage(aiMessageId, content);
      },
      
      // onComplete
      (metadata: any) => {
        streamingConversationStore.completeAIMessage(aiMessageId, metadata);
      },
      
      // onError
      (error: string) => {
        streamingConversationStore.setError(error);
      }
    );
  }
  
  function handleSuggestionClick(suggestion: string) {
    handleSendMessage(suggestion);
  }
</script>

<div class="streaming-conversation-container">
  <!-- Context and Status Header -->
  {#if $conversationSummary.hasContext || $conversationSummary.isActive}
    <div class="conversation-header">
      {#if $conversationSummary.hasContext}
        <div class="context-info">
          💬 {$conversationSummary.messageCount} messages • 
          📊 {$conversationSummary.projectCount} projects discussed
        </div>
      {/if}
      
      {#if $conversationSummary.isActive}
        <ProcessingStageIndicator 
          stage={$streamingConversationStore.currentStage}
        />
      {/if}
    </div>
  {/if}
  
  <!-- Messages Container -->
  <div class="messages-container" bind:this={messagesContainer}>
    {#each $streamingConversationStore.messages as message (message.id)}
      <StreamingMessageBubble 
        {message}
        isStreaming={message.isStreaming}
      />
    {/each}
  </div>
  
  <!-- Follow-up Suggestions -->
  {#if $streamingConversationStore.followUpSuggestions.length > 0 && !$streamingConversationStore.isProcessing}
    <FollowUpSuggestions 
      suggestions={$streamingConversationStore.followUpSuggestions}
      on:select={(e) => handleSuggestionClick(e.detail)}
    />
  {/if}
  
  <!-- Input Area -->
  <div class="input-container">
    <input
      type="text"
      bind:value={inputMessage}
      on:keypress={(e) => e.key === 'Enter' && handleSendMessage()}
      placeholder={$conversationSummary.hasContext 
        ? "Ask a follow-up question..." 
        : "Ask about European research projects..."}
      disabled={$streamingConversationStore.isProcessing}
      class:disabled={$streamingConversationStore.isProcessing}
    />
    <button 
      on:click={() => handleSendMessage()}
      disabled={!inputMessage.trim() || $streamingConversationStore.isProcessing}
      class:loading={$streamingConversationStore.isProcessing}
    >
      {#if $streamingConversationStore.isProcessing}
        <span class="spinner"></span>
      {:else}
        Send
      {/if}
    </button>
  </div>
</div>

<style>
  .streaming-conversation-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-width: 900px;
    margin: 0 auto;
    background: #f8f9fa;
  }
  
  .conversation-header {
    padding: 1rem;
    background: white;
    border-bottom: 1px solid #e0e0e0;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .context-info {
    font-size: 0.9rem;
    color: #666;
  }
  
  .messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  
  .input-container {
    display: flex;
    gap: 0.5rem;
    padding: 1rem;
    background: white;
    border-top: 1px solid #e0e0e0;
  }
  
  input {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 1rem;
    transition: border-color 0.2s;
  }
  
  input:focus {
    outline: none;
    border-color: #007bff;
  }
  
  input.disabled {
    background: #f5f5f5;
    cursor: not-allowed;
  }
  
  button {
    padding: 0.75rem 1.5rem;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1rem;
    transition: background-color 0.2s;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  button:hover:not(:disabled) {
    background: #0056b3;
  }
  
  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid transparent;
    border-top: 2px solid currentColor;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
```

### 4. Processing Stage Indicator Component

```svelte
<!-- components/ProcessingStageIndicator.svelte -->
<script lang="ts">
  import type { ProcessingStage } from '$lib/stores/streamingConversation';
  
  export let stage: ProcessingStage | null;
  
  const stageIcons: Record<string, string> = {
    'context_resolution': '🧠',
    'reference_resolved': '🎯',
    'intent_detection': '🤖',
    'intent_detected': '✅',
    'query_extraction': '🔍',
    'queries_extracted': '📝',
    'data_retrieval': '📡',
    'data_enriched': '✨',
    'data_selected': '🎯',
    'reranking': '📊',
    'answer_generation': '💭',
    'context_enhancement': '🔗',
    'streaming_response': '📤'
  };
  
  const stageDescriptions: Record<string, string> = {
    'context_resolution': 'Loading conversation context',
    'reference_resolved': 'Resolved references in your question',
    'intent_detection': 'Understanding your question',
    'intent_detected': 'Question intent identified',
    'query_extraction': 'Extracting search terms',
    'queries_extracted': 'Search queries ready',
    'data_retrieval': 'Searching CORDIS database',
    'data_enriched': 'Enriching with additional data',
    'data_selected': 'Selecting most relevant projects',
    'reranking': 'Ranking projects by relevance',
    'answer_generation': 'Generating comprehensive answer',
    'context_enhancement': 'Adding conversational context',
    'streaming_response': 'Delivering your answer'
  };
</script>

{#if stage}
  <div class="stage-indicator" class:pulsing={stage.stage !== 'streaming_response'}>
    <div class="stage-icon">
      {stageIcons[stage.stage] || '⚙️'}
    </div>
    <div class="stage-content">
      <div class="stage-title">
        {stageDescriptions[stage.stage] || stage.stage}
      </div>
      <div class="stage-message">
        {stage.message}
      </div>
    </div>
  </div>
{/if}

<style>
  .stage-indicator {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: #e3f2fd;
    border: 1px solid #bbdefb;
    border-radius: 8px;
    font-size: 0.9rem;
    transition: all 0.3s ease;
  }
  
  .stage-indicator.pulsing {
    animation: pulse 2s infinite;
  }
  
  .stage-icon {
    font-size: 1.2rem;
    min-width: 24px;
  }
  
  .stage-content {
    flex: 1;
  }
  
  .stage-title {
    font-weight: 600;
    color: #1976d2;
    margin-bottom: 0.25rem;
  }
  
  .stage-message {
    color: #666;
    font-size: 0.85rem;
  }
  
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }
</style>
```

### 5. Streaming Message Bubble Component

```svelte
<!-- components/StreamingMessageBubble.svelte -->
<script lang="ts">
  import type { StreamingMessage } from '$lib/stores/streamingConversation';
  import { marked } from 'marked';
  
  export let message: StreamingMessage;
  export let isStreaming: boolean = false;
  
  $: formattedText = message.sender === 'ai' ? marked(message.text) : message.text;
  $: timestamp = new Date(message.timestamp).toLocaleTimeString();
</script>

<div class="message-bubble" class:user={message.sender === 'user'} class:ai={message.sender === 'ai'} class:system={message.sender === 'system'}>
  <div class="message-header">
    <span class="sender">
      {#if message.sender === 'user'}
        👤 You
      {:else if message.sender === 'ai'}
        🤖 AI Assistant
      {:else}
        ℹ️ System
      {/if}
    </span>
    <span class="timestamp">{timestamp}</span>
  </div>
  
  <div class="message-content">
    {#if message.sender === 'ai'}
      {@html formattedText}
    {:else}
      {message.text}
    {/if}
    
    {#if isStreaming}
      <span class="cursor">|</span>
    {/if}
  </div>
</div>

<style>
  .message-bubble {
    max-width: 80%;
    padding: 1rem;
    border-radius: 12px;
    margin-bottom: 0.5rem;
    animation: slideIn 0.3s ease-out;
  }
  
  .message-bubble.user {
    align-self: flex-end;
    background: #007bff;
    color: white;
    margin-left: auto;
  }
  
  .message-bubble.ai {
    align-self: flex-start;
    background: white;
    border: 1px solid #e0e0e0;
    color: #333;
  }
  
  .message-bubble.system {
    align-self: center;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    color: #666;
    font-style: italic;
    text-align: center;
  }
  
  .message-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
    font-size: 0.85rem;
    opacity: 0.8;
  }
  
  .sender {
    font-weight: 600;
  }
  
  .timestamp {
    font-size: 0.75rem;
  }
  
  .message-content {
    line-height: 1.5;
    position: relative;
  }
  
  .cursor {
    animation: blink 1s infinite;
    font-weight: bold;
  }
  
  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }
  
  /* Style markdown content in AI messages */
  .message-bubble.ai :global(h1),
  .message-bubble.ai :global(h2),
  .message-bubble.ai :global(h3) {
    margin-top: 1rem;
    margin-bottom: 0.5rem;
    color: #333;
  }
  
  .message-bubble.ai :global(p) {
    margin-bottom: 0.75rem;
  }
  
  .message-bubble.ai :global(ul),
  .message-bubble.ai :global(ol) {
    margin-bottom: 0.75rem;
    padding-left: 1.5rem;
  }
  
  .message-bubble.ai :global(a) {
    color: #007bff;
    text-decoration: none;
  }
  
  .message-bubble.ai :global(a:hover) {
    text-decoration: underline;
  }
  
  .message-bubble.ai :global(code) {
    background: #f8f9fa;
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-family: monospace;
  }
</style>
```

### 6. Usage in SvelteKit Page

```svelte
<!-- routes/conversation/[id]/+page.svelte -->
<script lang="ts">
  import { page } from '$app/stores';
  import StreamingConversationInterface from '$lib/components/StreamingConversationInterface.svelte';
  import { streamingConversationStore } from '$lib/stores/streamingConversation';
  import { onDestroy } from 'svelte';
  import { streamingClient } from '$lib/api/streamingConversation';
  
  $: conversationId = parseInt($page.params.id);
  
  // Clean up on page leave
  onDestroy(() => {
    streamingClient.closeConnection();
  });
</script>

<svelte:head>
  <title>Conversation {conversationId} - CORDIS AI</title>
</svelte:head>

<div class="page-container">
  <header class="page-header">
    <h1>CORDIS AI Assistant</h1>
    <p>Conversational research project exploration</p>
  </header>
  
  <main class="conversation-main">
    <StreamingConversationInterface {conversationId} />
  </main>
</div>

<style>
  .page-container {
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
  
  .page-header {
    padding: 1rem 2rem;
    background: #fff;
    border-bottom: 1px solid #e0e0e0;
    text-align: center;
  }
  
  .page-header h1 {
    margin: 0 0 0.5rem 0;
    color: #333;
  }
  
  .page-header p {
    margin: 0;
    color: #666;
    font-size: 0.9rem;
  }
  
  .conversation-main {
    flex: 1;
    overflow: hidden;
  }
</style>
```

### 7. API Proxy Route for SvelteKit

```typescript
// src/routes/api/proxy/conversation/[id]/message/stream/+server.ts

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ params, request, fetch }) => {
  const conversationId = params.id;
  
  try {
    // Forward the request to your FastAPI backend
    const backendUrl = `${process.env.BACKEND_URL || 'http://localhost:8000'}/api/conversation/${conversationId}/message/stream`;
    
    const body = await request.text();
    
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body
    });
    
    if (!response.ok) {
      throw error(response.status, `Backend error: ${response.statusText}`);
    }
    
    // Return the streaming response
    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': '*',
      }
    });
    
  } catch (err) {
    console.error('Proxy error:', err);
    throw error(500, 'Failed to proxy streaming request');
  }
};
```

## Implementation Steps

### 1. Backend Setup
- ✅ Added streaming endpoint to conversation routes
- ✅ Implemented Server-Sent Events format
- ✅ Added real-time stage updates
- ✅ Integrated with existing context system

### 2. Frontend Setup

```bash
# Install required dependencies
npm install marked  # For markdown rendering
```

### 3. Integration

```typescript
// In your main layout or app component
import { streamingConversationStore } from '$lib/stores/streamingConversation';

// Initialize conversation
streamingConversationStore.setConversation(conversationId);
```

## Streaming Event Types

### Progress Events
```json
{
  "type": "progress",
  "stage": "data_retrieval",
  "message": "Searching CORDIS API and enriching with database..."
}
```

### Token Events
```json
{
  "type": "token",
  "content": "The nuclear energy research landscape in Europe..."
}
```

### Completion Events
```json
{
  "type": "complete",
  "follow_up_suggestions": ["Tell me about ECOSENS", "What's the budget?"],
  "context_used": true,
  "projects_discussed": [...],
  "processing_time": 5.2
}
```

## Benefits

1. **Real-time Feedback**: Users see exactly what the AI is doing
2. **Smooth UX**: Token-by-token streaming feels natural
3. **Context Awareness**: Maintains conversation state during streaming
4. **Error Handling**: Graceful error display and recovery
5. **Performance**: Non-blocking UI with progress indicators

## Testing

```bash
# Test the streaming endpoint
curl -N -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "Find nuclear projects", "include_context": true}' \
  http://localhost:8000/api/conversation/1/message/stream
```

This implementation provides a smooth, real-time conversational experience with full context awareness and streaming responses.