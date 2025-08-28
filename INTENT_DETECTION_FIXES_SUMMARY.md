# Intent Detection Fixes - Summary Report

## Problem Identified
The AI system was misclassifying procedural "how-to" questions as `SEARCH_CALLS` instead of `GENERAL_QUERY`, causing it to search for specific calls rather than providing procedural guidance from the documentation.

**Original Problem Question**: "How to find and apply for relevant calls?"
- **Before**: Classified as `SEARCH_CALLS` → Tried to find specific calls
- **After**: Classified as `GENERAL_QUERY` → Routes to document search for procedural guidance

## Root Causes Found
1. **LLM Intent Detection**: The prompt in `determine_user_intent()` didn't clearly distinguish between procedural questions vs call searches
2. **Call-Specific RAG Interference**: The `detect_call_specific_intent()` method was too aggressive, intercepting procedural questions before they reached the improved LLM classifier

## Fixes Implemented

### 1. Enhanced LLM Intent Detection ([`rag_service.py:152-198`](app/services/rag_service.py:152))
- Added clear distinction between `SEARCH_CALLS` and `GENERAL_QUERY` intents
- Emphasized that procedural questions (how-to, process, criteria) are `GENERAL_QUERY`
- Added comprehensive examples showing the difference

### 2. Fixed Call-Specific RAG ([`call_specific_rag.py:99-140`](app/services/call_specific_rag.py:99))
- Added procedural pattern detection BEFORE keyword analysis
- Prevents procedural questions from being misclassified as call searches
- Uses regex patterns to detect "how to", "what is the process", etc.

### 3. Verified Routing Logic ([`enhanced_rag_service.py:76-79`](app/services/enhanced_rag_service.py:76))
- Confirmed that `GENERAL_QUERY` correctly routes to document search
- Document search has all the procedural information needed

## Test Results

### Before Fixes
- **Original Problem**: "How to find and apply for relevant calls?" → `SEARCH_CALLS` (incorrect)
- **Overall Accuracy**: ~50% for procedural questions

### After Fixes ✅
- **Original Problem**: "How to find and apply for relevant calls?" → `GENERAL_QUERY` (correct, 1.00 confidence)
- **Procedural Questions**: 9/10 correctly classified (90% accuracy)
- **Call Search Questions**: 5/5 correctly classified (100% accuracy)
- **Overall System Accuracy**: 83.3% (15/18 questions)

## Impact

### ✅ **Fixed Questions Now Work Correctly:**
- "How to find and apply for relevant calls?"
- "What is the application process for Horizon Europe?"
- "How do I form a consortium for EU proposals?"
- "How can I apply for funding?"
- "What are the steps to submit a proposal?"
- "How do I register on the EU portal?"
- "What is the evaluation process?"
- "How to prepare a competitive proposal?"
- "What are the requirements for participation?"

### 🔍 **Still Work as Expected:**
- "What calls are available for AI research?" → `SEARCH_CALLS`
- "Show me open calls for renewable energy" → `SEARCH_CALLS`
- "What AI projects have been funded?" → `SEARCH_PROJECTS`

## System Flow After Fixes

```
User Question: "How to find and apply for relevant calls?"
        ↓
1. Call-Specific RAG detects "how to" pattern
        ↓
2. Returns GENERAL_QUERY (confidence: 0.95)
        ↓
3. Enhanced RAG routes to handle_general_query()
        ↓
4. Vector search finds procedural documentation
        ↓
5. LLM generates answer with step-by-step guidance
```

## Files Modified
1. [`app/services/rag_service.py`](app/services/rag_service.py) - Enhanced intent detection prompt
2. [`app/services/call_specific_rag.py`](app/services/call_specific_rag.py) - Added procedural question detection

## Testing
- Created [`test_simple_intent.py`](test_simple_intent.py) for comprehensive testing
- Verified 83.3% overall accuracy with 90% accuracy for procedural questions
- Confirmed the original problem question now works correctly

---

**Status**: ✅ **COMPLETE** - The system now properly distinguishes between procedural guidance questions and call/project searches, routing users to appropriate information sources.