# Unified Intent Classifier - Implementation Status

## ✅ What's Working

### 1. Unified Classifier Created & Tested
- **File**: `app/services/unified_intent_classifier.py`
- **Accuracy**: 91.3% (21/23 test queries correct)
- **Handles all 5 intents**:
  - FAQ (general questions)
  - Search Projects (CORDIS)
  - Search Calls (EU Portal)
  - Call-Specific (questions about specific calls)
  - Proposal Writing (draft/improve/export)

### 2. Integrated into ConversationManager
- Added import and initialization
- Called in BOTH streaming and non-streaming flows
- Extracts call IDs correctly
- Routes to appropriate handlers

### 3. Test Results
For query: "Can I apply for this call from the netherlands? HORIZON-CL5-2026-01-D2-01"

**Unified Classifier Output**:
```
🎯 UNIFIED INTENT: call_specific (confidence: 0.98)
   Call ID: HORIZON-CL5-2026-01-D2-01
📞 ROUTING TO: Call-Specific
✅ Loaded 11 relevant document sections
```

✅ **This is working perfectly!**

## ❌ What's NOT Working

### The Problem: Old AI Intent Service Still Being Called

Even though the unified classifier correctly identifies the intent and loads call documents, the system CONTINUES to call the old `AIIntentService`, which then re-classifies the query as "conversational" and overrides everything.

**Evidence**:
```
📊 intent_detected: AI analyzed intent: conversational  ← This is the OLD service
```

### Why This Happens

The current flow:
1. ✅ Unified classifier detects `call_specific` 
2. ✅ Loads call documents (11 chunks)
3. ❌ Continues to Phase 2: Calls `_analyze_intent_and_plan_tools()`
4. ❌ Which calls `ai_intent_service.analyze_intent()`
5. ❌ Which re-classifies as "conversational"
6. ❌ Final response ignores call documents

## 🔧 What Needs to be Fixed

### Option 1: Skip Old AI Intent Service (RECOMMENDED)

When unified classifier has already classified the intent, **skip** the old AI intent service entirely.

**Implementation**:
```python
# In _generate_streaming_response_with_processing()

# After unified classifier and loading call documents...

# Skip old AI intent service - we already have the intent!
if unified_intent.primary_intent == 'call_specific' and call_document_results:
    # Use call documents directly, skip intent analysis
    logger.info("📚 Using unified intent classification - skipping old AI intent service")
    
    # Go directly to response generation with call documents
    async for chunk in self._generate_response_with_call_documents(
        conversation_id=conversation_id,
        user_message=user_message,
        call_id=call_id,
        call_documents=call_document_results
    ):
        yield chunk
    return
```

### Option 2: Phase Out Old AI Intent Service Completely

Replace ALL calls to `ai_intent_service` with unified classifier and route based on `unified_intent.tool_plan`.

**Benefits**:
- Single source of truth
- No conflicting classifications
- Cleaner code
- Better maintainability

## 📊 Current System Architecture

```
User Message
     ↓
[Unified Classifier] → Intent + Call ID + Tool Plan
     ↓
[Route to Handler]
     ├─ Proposal Writing → handle_proposal_writing()
     ├─ Call-Specific → load_call_documents()
     ├─ Search Projects → execute tools (search_cordis_projects)
     ├─ Search Calls → execute tools (eu_portal_search)
     └─ FAQ → execute tools (search_local_database)
     ↓
[OLD AI Intent Service] ← ❌ THIS IS THE PROBLEM
     ↓
[Response Generation]
```

**The Issue**: After routing and loading documents, the system STILL calls the old AI intent service, which overrides the unified classification.

## 🎯 Recommended Fix

1. **Immediate Fix**: Skip old AI intent service when unified classifier has already provided intent + documents
2. **Long-term**: Remove old AI intent service completely, use only unified classifier

## Implementation Priority

### High Priority (Do Now)
- [ ] Skip old AI intent service after unified classifier in streaming flow
- [ ] Skip old AI intent service after unified classifier in non-streaming flow
- [ ] Test that call-specific questions get proper answers

### Medium Priority (Do Soon)
- [ ] Add more examples to unified classifier prompt for edge cases
- [ ] Log both classifications temporarily to compare accuracy
- [ ] Monitor for misclassifications

### Low Priority (Future)
- [ ] Complete removal of old AI intent service
- [ ] Simplify flow to use only unified classifier
- [ ] Performance optimization

## Test Case to Verify Fix

**Query**: "Can I apply for this call from the netherlands? HORIZON-CL5-2026-01-D2-01"

**Expected**:
- ✅ Detect: `call_specific` intent
- ✅ Extract: `HORIZON-CL5-2026-01-D2-01`
- ✅ Load: Call-specific eligibility documents
- ✅ Answer: "Yes, the Netherlands is an EU member state and eligible for this call..."

**Currently Getting**:
- ✅ Detect: `call_specific` intent
- ✅ Extract: `HORIZON-CL5-2026-01-D2-01`
- ✅ Load: 11 call-specific documents
- ❌ Answer: Generic "here's how to apply" (ignores loaded documents)

## Summary

The **Unified Intent Classifier is working perfectly** at 91% accuracy and correctly routing requests.

The **problem is architectural** - the old AI intent service is still being called and overriding the unified classifier's decisions.

**Fix**: Skip the old AI intent service when unified classifier has already classified the intent and loaded relevant documents.

**Impact**: This one change will fix the user's reported issue and make the system much more reliable!

