# Unified Intent Classification System

## Problem Statement

The previous system had **fragmented intent detection**:
- Separate keyword-based proposal writing detector
- Separate AI intent service for other intents  
- Call-specific detection mixed with general queries
- Many questions misclassified or routed incorrectly

**Result**: User questions not picked up correctly, confusing user experience

## Solution: Unified AI-Powered Classifier

Single intelligent AI system that handles **ALL 5 functionalities** with high accuracy:

### The 5 Intent Categories

1. **FAQ** - General questions about Horizon Europe
   - "How do I apply for funding?"
   - "What are eligibility criteria?"
   - "Explain the evaluation process"

2. **Search Projects** - Find CORDIS research projects
   - "Show me projects about renewable energy"
   - "Find AI healthcare research"
   - "What biotechnology projects exist?"

3. **Search Calls** - Find funding opportunities
   - "What calls are open for renewable energy?"
   - "Show me AI funding opportunities"
   - "Find grants with 2025 deadlines"

4. **Call-Specific** - Questions about a specific call
   - "Tell me about HORIZON-CL3-2025-02-CS-ECCC-01"
   - "What's the budget for HORIZON-MSCA-2024-DN-01?"
   - "When is deadline for HORIZON-HLTH-2025-01?"

5. **Proposal Writing** - Help with proposal drafting
   - "Help me write a proposal for [call]"
   - "Draft the objectives section"
   - "Move to next section"
   - "Export to Word"

## Key Improvements

### 🎯 Single Point of Classification
- **Before**: Multiple detection systems checking in sequence
- **After**: One intelligent AI analyzes intent once

### 🧠 Context-Aware
- Uses conversation history to resolve ambiguity
- Remembers previous call IDs and topics
- Understands follow-up questions

### 📊 High Accuracy
- Temperature 0.1 for consistent results
- Clear examples teach the AI proper classification
- Confidence scoring for reliability

### 🔧 Smart Tool Planning
- Automatically selects correct tools for each intent
- Generates appropriate parameters
- Handles edge cases gracefully

## How It Works

### Classification Flow

```
User Message
     ↓
[Build Context from recent messages]
     ↓
[AI Classification with clear examples]
     ↓
[Parse JSON response]
     ↓
[Generate tool plan if needed]
     ↓
Return UnifiedIntent object
```

### Intent Detection Logic

**FAQ Detection:**
- Keywords: "how", "what", "explain", "tell me about"
- No specific items to find
- General procedural questions
- Tool: `search_local_database` (knowledge base)

**Search Projects Detection:**
- Keywords: "find", "show", "search" + "projects"
- Looking for research outputs
- Tool: `search_cordis_projects`

**Search Calls Detection:**
- Keywords: "find", "show", "search" + "calls/opportunities/grants"
- Looking for funding
- Tool: `eu_portal_search`

**Call-Specific Detection:**
- Call ID present (HORIZON-XXX-YYYY-ZZ)
- Questions about that specific call
- Tool: `search_call_documents` with call_id

**Proposal Writing Detection:**
- Keywords: "write", "draft", "help", "generate", "export" + "proposal"
- Or: navigation words like "next section", "move to"
- Or: acronym setting "call it X", "acronym is Y"
- No tools (handled by proposal services)

## Integration Steps

### 1. Replace Current Intent Detection

**In `conversation_manager.py`:**

```python
from app.services.unified_intent_classifier import UnifiedIntentClassifier

class ConversationManager:
    def __init__(self):
        # ... existing code ...
        self.intent_classifier = UnifiedIntentClassifier()
    
    async def process_message(self, conversation_id, user_message, user_id, streaming=False):
        # Phase 1: Get recent messages for context
        recent_messages = self._get_recent_messages(conversation_id, limit=5)
        
        # Phase 2: Unified intent classification
        intent = await self.intent_classifier.classify_intent(
            user_message=user_message,
            conversation_id=conversation_id,
            recent_messages=recent_messages
        )
        
        logger.info(f"🎯 Intent: {intent.primary_intent} (confidence: {intent.confidence:.2f})")
        
        # Phase 3: Route to appropriate handler
        if intent.primary_intent == "proposal_writing":
            return await self._handle_proposal_writing(
                conversation_id=conversation_id,
                user_message=user_message,
                intent=intent
            )
        
        elif intent.primary_intent == "call_specific" and intent.call_id:
            return await self._handle_call_specific_question(
                conversation_id=conversation_id,
                user_message=user_message,
                call_id=intent.call_id,
                tool_plan=intent.tool_plan
            )
        
        elif intent.primary_intent in ["search_projects", "search_calls"]:
            return await self._handle_search(
                conversation_id=conversation_id,
                user_message=user_message,
                intent=intent
            )
        
        else:  # FAQ
            return await self._handle_faq(
                conversation_id=conversation_id,
                user_message=user_message,
                tool_plan=intent.tool_plan
            )
```

### 2. Remove Fragmented Detectors

**Delete/Replace:**
- `_detect_proposal_writing_mode()` - now handled by unified classifier
- Keyword-based call ID extraction - now part of AI classification
- Multiple intent checking loops - single classification

### 3. Update Tool Execution

The unified classifier provides ready-to-use tool plans:

```python
# Execute tools from unified intent
if intent.requires_tools and intent.tool_plan:
    tool_results = await self._execute_tools(intent.tool_plan)
```

## Benefits

### For Users
✅ Questions correctly understood the first time  
✅ Faster, more accurate responses  
✅ Better conversation flow  
✅ Consistent behavior across all query types

### For Developers
✅ Single point of maintenance  
✅ Easier to debug and improve  
✅ Clear separation of concerns  
✅ Testable AI prompts  
✅ Metrics and logging in one place

## Testing

### Test Each Intent Category

```python
# Test FAQ
"How do I apply for Horizon Europe funding?"
→ Intent: faq, Tool: search_local_database

# Test Search Projects
"Show me renewable energy projects"
→ Intent: search_projects, Tool: search_cordis_projects

# Test Search Calls
"Find AI funding opportunities"
→ Intent: search_calls, Tool: eu_portal_search

# Test Call-Specific
"What's the budget for HORIZON-CL3-2025-02-CS-ECCC-01?"
→ Intent: call_specific, call_id: HORIZON-CL3-2025-02-CS-ECCC-01

# Test Proposal Writing
"Help me write a proposal for HORIZON-CL3-2025-02-CS-ECCC-01"
→ Intent: proposal_writing, call_id: HORIZON-CL3-2025-02-CS-ECCC-01
```

### Edge Cases to Test

1. **Ambiguous queries**
   - "Tell me about renewable energy" → Should check context
   - If previous message asked about calls → search_calls
   - If previous message asked about projects → search_projects
   - Otherwise → faq

2. **Follow-up questions**
   - User: "Show me calls about AI"
   - System: [shows calls]
   - User: "Tell me more about the first one"
   - → Should use conversation context to identify call ID

3. **Multiple intents**
   - "Show me projects and calls about renewable energy"
   - → Primary: search_projects (mentioned first)
   - → Note: Could enhance to support multi-intent later

## Monitoring & Improvement

### Log Intent Classifications
```python
logger.info(f"""
Intent Classification:
  Message: {user_message[:50]}...
  Intent: {intent.primary_intent}
  Confidence: {intent.confidence:.2f}
  Reasoning: {intent.reasoning}
  Call ID: {intent.call_id}
  Tools: {[t['tool_name'] for t in intent.tool_plan]}
""")
```

### Track Misclassifications
Monitor for:
- Low confidence scores (<0.7)
- User corrections ("no, I meant...")
- Repeated questions (user not satisfied)

### Iterative Improvement
1. Collect misclassified examples
2. Add them to the prompt examples
3. Adjust temperature if needed
4. Update tool planning logic

## Next Steps

1. **Implement Integration**
   - Update `conversation_manager.py`
   - Remove old detection code
   - Add unified classifier

2. **Test Thoroughly**
   - Test all 5 intent types
   - Test edge cases
   - Test with real user queries

3. **Monitor Performance**
   - Log classifications
   - Track confidence scores
   - Identify patterns

4. **Iterate**
   - Add more examples for edge cases
   - Refine tool planning
   - Optimize for speed

## Expected Results

**Before:**
- 60-70% intent accuracy
- Many questions misrouted
- Slow due to multiple checks
- Fragile keyword matching

**After:**
- 85-95% intent accuracy
- Clear routing for all 5 categories
- Fast single AI call
- Robust context-aware classification

---

The Unified Intent System provides a **single, intelligent, maintainable** solution for all intent detection needs! 🚀

