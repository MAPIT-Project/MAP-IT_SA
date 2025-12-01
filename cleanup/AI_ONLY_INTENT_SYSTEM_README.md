# Enhanced AI-Only Intent System Design

## Overview

This document outlines the design for an enhanced AI-only intent system that improves upon the existing AI intent service by:
1. **Better handling of general questions** - Using local database search for general questions that don't match project or funding patterns
2. **Better handling of memory queries** - Recognizing queries like "What is the first message I sent you?" as memory-related queries
3. **Pure AI-driven analysis** - No keyword detection, no regex patterns, pure AI analysis
4. **Enhanced examples and context** - Better examples for the AI to make better decisions

## Key Improvements

### 1. Enhanced General Question Support

**Problem**: The current system classifies queries like "What is the first message I sent you?" as conversational queries and doesn't use the local database search tool to search conversation history.

**Solution**: The enhanced AI will be trained to recognize:
- **General information requests**: "Tell me about X", "Explain X", "What is X?"
- **Memory queries**: "What was my first message?", "What did I ask about X earlier?"
- **Follow-up questions**: "Tell me more about X", "Can you explain that in more detail?"

When the AI detects these patterns, it will:
1. Use `search_local_database` tool to search conversation history
2. Provide context-aware responses based on actual conversation context
3. Use AI to generate responses using retrieved information

### 2. Enhanced Memory Query Support

**Problem**: Memory queries like "What is the first message I sent you?" are classified as conversational queries instead of using conversation history.

**Solution**: The enhanced AI will be trained to recognize memory-related patterns:
- "What was my first message?"
- "What did I ask about X earlier?"
- "Can you remind me what we discussed about X?"
- "What was the first thing I asked you?"

When detected, the AI will:
1. Use `search_local_database` tool to search conversation history
2. Return actual conversation history instead of generating new responses
3. Provide accurate memory retrieval instead of AI-generated responses

### 3. Enhanced AI Prompt Design

The enhanced AI prompt will include:
- **Better examples** for general questions and memory queries
- **Clear intent definitions** with detailed descriptions
- **Tool selection guidance** with specific tool parameters
- **Confidence scoring** with clear guidelines

### 4. Fallback System Enhancements

The fallback system will include debugging information:
- `[FALLBACK MODE]` prefix for fallback analysis
- Original error information included in reasoning
- `[EMERGENCY FALLBACK]` prefix for double fallback
- Detailed error reporting

## Enhanced AI Prompt

```text
You are an expert AI assistant specializing in European research funding and innovation. Analyze this user message and determine their intent using your understanding of natural language and context.

USER MESSAGE: "{message}"

CONVERSATION CONTEXT:
{conversation_context if conversation_context else "New conversation"}

RECENT HISTORY:
{conversation_history if conversation_history else "No recent history"}

AVAILABLE TOOLS:
{json.dumps(available_tools, indent=2)}

INTENT CATEGORIES:
- "search_calls": User wants to find funding opportunities, open calls, grants, deadlines, or funding programs
- "search_projects": User wants to find existing research projects, case studies, examples, or research initiatives
- "conversational": General questions, greetings, help requests, discussions, procedural questions, clarification requests

TOOL SELECTION:
- "eu_portal_search": Use for finding funding calls and opportunities, grants, or funding programs
- "search_cordis_projects": Use for finding research projects, case studies, examples, or research initiatives
- "search_local_database": Use for conversational queries, procedural questions, informational requests, explanations

CONFIDENCE SCORING:
- 0.9-1.0: Very clear intent with strong indicators
- 0.7-0.89: Clear intent but some ambiguity
- 0.5-0.69: Moderate ambiguity
- Below 0.5: Unclear intent

RESPONSE FORMAT (JSON):
{
    "intent_type": "search_calls|search_projects|conversational",
    "confidence": 0.85,
    "requires_tools": true/false,
    "tool_plan": [
        {
            "tool_name": "eu_portal_search",
            "parameters": {
                "query": "clean energy funding",
                "status": "open",
                "max_results": 20
            },
            "reason": "User is asking for funding opportunities"
        }
    ],
    "reasoning": "Step-by-step reasoning: 1. Check for search keywords... 2. Default to conversational",
    "context_assessment": "Assessment of conversation context",
    "processing_type": "tool_based|conversational|mixed"
}

MANDATORY: You must follow the step-by-step reasoning process exactly as specified. Show your reasoning in the "reasoning" field.

CRITICAL RULES:
- If user mentions "open calls", "funding opportunities", "calls for proposals", "grants", "deadlines" → search_calls
- If user mentions "projects", "research projects", "case studies", "cordis", "api", "search on", "find projects", "show me projects", "what projects", "projects about", "projects on", "projects in" → search_projects
- For conversational queries (hello, hi, help, thanks, what can you do, how to, explain, detail, requirements, process) → conversational
- Always provide specific tool parameters when tools are needed
- Consider conversation context for follow-up questions

NEW ENHANCED RULES FOR ENHANCED AI-ONLY INTENT DETection:
- "What was my first message?" → search_local_database → conversational
- "What did I ask about X earlier?" → search_local_database → conversational
- "Tell me more about X" → search_local_database → conversational
- "Can you explain that in more detail?" → search_local_database → conversational
- "What can you help me with?" → search_local_database → conversational
- "Tell me about X" → search_local_database → conversational
- "How does X work?" → search_local_database → conversational
- "What are the requirements for X?" → search_local_database → conversational
- "Could you elaborate on X?" → search_local_database → conversational
- "How does the application process work?" → search_local_database → conversational
- "What do you mean by X?" → search_local_database → conversational

EXAMPLES TO GUIDE YOUR UNDERSTANDING:

SEARCH CALLS EXAMPLES:
- "What are the open calls for renewable energy?"
- "Show me funding opportunities in AI"
- "Are there any grants for clean technology?"

SEARCH PROJECTS EXAMPLES:
- "Can you show me projects about renewable energy?"
- "What research has been done on climate change?"
- "Find examples of successful Horizon Europe projects"
- "Show me case studies in biotechnology"

CONVERSATIONAL EXAMPLES:
- "Hello, how can you help me?"
- "How do I apply for funding?"
- "Can you explain the process?"
- "What documents do I need?"
- "Tell me more about that"
- "What are the eligibility requirements?"
- "Could you elaborate on that?"
- "How does the application process work?"
- "What do you mean by that?"

MEMORY QUERY EXAMPLES:
- "What was my first message?"
- "What did I ask about X earlier?"
- "Can you remind me what we discussed about X?"
- "What was the first thing I asked you?"

GENERAL QUESTION EXAMPLES:
- "Tell me about X"
- "Explain X in more detail?"
- "What is X?"
- "How does X work?"
- "What are the requirements for X?"
- "Could you elaborate on X?"
- "How does the application process work?"
- "What do you mean by X?"

CLASSIFICATION PRECEDENCE:
1. If query mentions calls, funding, grants, opportunities → search_calls
2. If query mentions projects, research, case studies, CORDIS, API, "find projects", "search for projects", "show me projects" → search_projects
3. If query is a memory query (see MEMORY QUERY EXAMPLES above) → search_local_database → conversational
4. If query is a general question (see GENERAL QUESTION EXAMPLES above) → search_local_database → conversational
5. Everything else → conversational

IMPORTANT: You must analyze the user's intent using your natural language understanding, NOT keyword detection or regex patterns.

ANALYZE THE MESSAGE: "{message}"
```

## Implementation Plan

### Phase 1: Create Enhanced AI Intent Service
1. Create `app/services/enhanced_ai_intent_service.py` implementing the enhanced AI-only intent detection
2. Update `app/services/conversation/conversation_manager.py` to use the enhanced intent service
3. Create test scripts to validate the enhanced intent detection
4. Document the enhanced system in this document

### Phase 2: Testing Strategy
1. **Test general questions**: "Tell me about Horizon Europe funding"
2. **Test memory queries**: "What was my first message?"
3. **Test follow-up questions**: "Tell me more about renewable energy projects"
4. **Test edge cases**: Mixed queries that could be ambiguous

## Benefits

1. **Better general question handling**: AI will use local database search for general questions
2. **Better memory query handling**: AI will search conversation history for memory queries
3. **More reliable intent detection**: Pure AI-driven analysis without keyword detection
4. **Better debugging**: Enhanced fallback system with detailed error reporting
5. **Simplified architecture**: Single AI call handles intent analysis and tool planning

This enhanced AI-only intent system will provide more reliable, consistent intent detection with better support for general questions and memory queries.