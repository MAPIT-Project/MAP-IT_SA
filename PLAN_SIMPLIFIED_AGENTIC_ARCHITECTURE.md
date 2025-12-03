# Plan: Simplified Single Agentic Architecture

## Current Problem

The current architecture is overly complex:
1. **Intent Classification** → tries to predict what the user wants
2. **Routing Logic** → routes to different code paths based on intent
3. **Tool Planning** → generates tool plans in the classifier
4. **Follow-up Resolution** → tries to resolve references with regex/LLM
5. **Execution** → finally executes tools
6. **Response Generation** → generates response

This creates:
- Multiple LLM calls (classification + tool execution + response)
- Brittle routing logic
- Race conditions (storing messages, context updates)
- Inconsistent behavior
- Hard to debug

## Target Architecture

**Single Agentic Loop**:
1. User message + conversation history → Agent
2. Agent decides what tools to use (or just answer from context)
3. Agent executes tools as needed
4. Agent synthesizes final answer
5. Store conversation turn

That's it. No intent classification. No routing. No separate follow-up handling.

## Implementation Plan

### Phase 1: Enhance ToolAwareAgent (30 min)

The `ToolAwareAgent` already exists and is capable. Enhancements needed:

1. **Better conversation context handling**
   - Current: passes context as string
   - New: structured conversation history with clear user/assistant turns

2. **Follow-up understanding built into system prompt**
   - Agent should understand: "this refers to the previous search"
   - Agent should understand: "user is complaining, I should try again"
   - Agent should understand: "the 4th call" = specific call from history

3. **Streaming support**
   - Add ability to stream tokens from final synthesis

### Phase 2: Create Single Entry Point (20 min)

Create `app/services/agents/main_agent.py`:

```python
class MainAgent:
    """Single entry point for all conversations."""

    def __init__(self):
        self.tool_agent = ToolAwareAgent()
        self.memory_service = MemoryService()

    async def process(self, conversation_id, user_message, streaming=False):
        # 1. Get conversation history
        history = self.memory_service.get_recent_turns(conversation_id)

        # 2. Run the agentic loop
        result = await self.tool_agent.answer(
            query=user_message,
            context=self._format_history(history),
            streaming=streaming
        )

        # 3. Store the turn
        self.memory_service.add_turn(conversation_id, 'user', user_message)
        self.memory_service.add_turn(conversation_id, 'assistant', result.answer)

        # 4. Return result
        return {
            'response': result.answer,
            'tools_used': result.tools_used,
            'confidence': result.confidence,
            'reasoning_trace': result.steps
        }
```

### Phase 3: Update Conversation Manager (15 min)

Simplify `conversation_manager.py`:

```python
async def process_message(self, conversation_id, user_message, streaming=False):
    # BEFORE: 500+ lines of routing logic
    # AFTER: 20 lines

    return await self.main_agent.process(
        conversation_id=conversation_id,
        user_message=user_message,
        streaming=streaming
    )
```

### Phase 4: Update API Routes (10 min)

The routes remain the same, they just call the simplified `process_message`.

### Phase 5: Remove Dead Code (15 min)

Delete or deprecate:
- `UnifiedIntentClassifier` (or keep for logging/analytics only)
- Intent routing logic in `conversation_manager.py`
- Follow-up resolution methods
- Multiple fallback handlers

## Detailed Changes

### File: `app/services/agents/tool_aware_agent.py`

#### 1. Update System Prompt

```python
REASONING_PROMPT = """You are an intelligent research assistant for EU funding (Horizon Europe).

## Your Capabilities
You have access to tools that can:
- Search funding calls (open/upcoming)
- Search funded projects (CORDIS)
- Get statistics (success rates, budgets)
- Compare programmes
- Search official documents

## Conversation Context
{conversation_history}

## Current Message
User: {user_message}

## Your Task
1. UNDERSTAND what the user wants
   - If they're asking for something new, search for it
   - If they're referring to previous results, understand what they mean
   - If they're complaining ("only 1 result"), try searching again with better parameters

2. DECIDE what tools to use (or answer directly if you can)

3. EXECUTE tools and analyze results

4. SYNTHESIZE a helpful response

## Response Format
{
    "thought": "What am I trying to accomplish?",
    "action": "call_tools" | "respond",
    "tool_calls": [...],  // if action is "call_tools"
    "response": "..."     // if action is "respond"
}
"""
```

#### 2. Add Conversation History Formatting

```python
def _format_conversation_history(self, history: List[Dict]) -> str:
    """Format conversation history for the agent."""
    if not history:
        return "No previous conversation."

    lines = []
    for turn in history[-10:]:  # Last 10 turns
        role = turn['role'].upper()
        content = turn['content'][:500]  # Truncate long responses
        lines.append(f"{role}: {content}")

    return "\n\n".join(lines)
```

#### 3. Update Main Entry Method

```python
async def answer(
    self,
    query: str,
    conversation_history: List[Dict] = None,
    streaming: bool = False
) -> AgentResult:
    """
    Main entry point - answer any query using the agentic loop.

    The agent will:
    1. Understand the query in context of conversation
    2. Decide what tools to use
    3. Execute tools iteratively until satisfied
    4. Synthesize final answer
    """

    # Format context
    context = self._format_conversation_history(conversation_history or [])

    # Build the initial prompt
    prompt = self.REASONING_PROMPT.format(
        conversation_history=context,
        user_message=query,
        tools_description=self._get_tools_description()
    )

    # Run the reasoning loop
    steps = []
    max_iterations = 5

    for i in range(max_iterations):
        # Get next action from LLM
        response = await self._get_llm_response(prompt)

        if response['action'] == 'respond':
            # Agent is ready to give final answer
            return AgentResult(
                answer=response['response'],
                tools_used=[s.tool_calls for s in steps],
                confidence=self._calculate_confidence(steps),
                steps=steps
            )

        elif response['action'] == 'call_tools':
            # Execute the tool calls
            results = await self._execute_tools(response['tool_calls'])

            # Add to steps
            step = ReasoningStep(
                step_number=i + 1,
                thought=response['thought'],
                action='call_tools',
                tool_calls=results,
                observation=self._summarize_results(results)
            )
            steps.append(step)

            # Update prompt with results
            prompt += f"\n\n## Step {i+1} Results\n{step.observation}"

    # Max iterations reached - synthesize what we have
    return await self._synthesize_answer(steps, query)
```

### File: `app/services/conversation/conversation_manager.py`

Replace the complex `process_message` with:

```python
async def process_message(
    self,
    conversation_id: int,
    user_message: str,
    user_id: int,
    streaming: bool = False
) -> Dict[str, Any]:
    """Process a message using the single agentic architecture."""

    start_time = datetime.now()

    # 1. Get conversation history
    history = self.memory_service.get_conversation_history(conversation_id, limit=10)

    # 2. Store user message
    self.memory_service.add_turn(conversation_id, 'user', user_message)

    # 3. Run the agent
    if streaming:
        return self._stream_agent_response(conversation_id, user_message, history, start_time)

    result = await self.tool_aware_agent.answer(
        query=user_message,
        conversation_history=history
    )

    # 4. Store assistant response
    self.memory_service.add_turn(conversation_id, 'assistant', result.answer)

    # 5. Return formatted response
    return {
        'response': result.answer,
        'metadata': {
            'tools_used': result.tools_used,
            'confidence': result.confidence,
            'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
            'reasoning_steps': len(result.steps)
        }
    }
```

## Benefits

1. **Simpler code**: 50 lines instead of 500+
2. **More intelligent**: Agent decides, not hardcoded routing
3. **Better follow-ups**: Agent understands context naturally
4. **Easier debugging**: One code path, clear reasoning trace
5. **Consistent behavior**: Same logic for all queries
6. **Faster iteration**: Change prompts, not code

## Migration Strategy

1. Keep old code in place
2. Add new `MainAgent` alongside
3. Add feature flag: `USE_SIMPLIFIED_AGENT=true`
4. Test extensively
5. Remove old code once validated

## Testing Plan

Test cases to verify:
1. Simple FAQ: "What is Horizon Europe?" → should answer directly
2. Call search: "Show me clean energy calls" → should use eu_portal_search
3. Project search: "Find AI projects" → should use search_cordis_projects
4. Follow-up complaint: "That's only 1 result" → should re-search
5. Ordinal reference: "Tell me about the 4th one" → should understand context
6. Comparison: "Compare EIC vs ERC" → should use multiple tools
7. Complex: "Success rates by country for climate" → should use stats + docs
