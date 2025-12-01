# Improved AI-Only Intent System Test Plan

## Overview

The improved intent system replaces complex rule-based logic with a single AI-only approach. This document outlines the testing strategy and expected improvements.

## Architecture Changes

### Before (Rule-Based System)
- **200+ lines** of keyword matching logic
- **Multiple fallback layers** with complex rule interactions
- **Mixed AI and rule-based** approach creating inconsistency
- **Hard to maintain** and debug

### After (AI-Only System)
- **Single AI call** handles all intent analysis and tool planning
- **Consistent behavior** across all query types
- **Simplified architecture** with fewer moving parts
- **Easier to maintain** and extend

## Test Cases

### 1. Funding Call Queries
```python
test_queries = [
    "What are some open calls for clean energy?",
    "Show me funding opportunities in AI",
    "Find calls for proposals about renewable energy",
    "What grants are available for climate research?"
]
```

**Expected Behavior:**
- Intent: `search_calls`
- Tools: `eu_portal_search`
- Confidence: > 0.8

### 2. Project Search Queries
```python
test_queries = [
    "Show me projects about nuclear energy",
    "Find research projects in biotechnology",
    "What case studies exist for AI in healthcare?",
    "Search CORDIS for projects on clean energy"
]
```

**Expected Behavior:**
- Intent: `search_projects`
- Tools: `search_cordis_projects`
- Confidence: > 0.8

### 3. Conversational Queries
```python
test_queries = [
    "Hello, how can you help me?",
    "What is Horizon Europe?",
    "How do I get started with EU funding?",
    "Thank you for your help"
]
```

**Expected Behavior:**
- Intent: `conversational`
- Tools: None
- Confidence: > 0.7

### 4. Clarification Queries
```python
test_queries = [
    "Can you explain that in more detail?",
    "What do you mean by that?",
    "Tell me more about the budget requirements",
    "Could you clarify the eligibility criteria?"
]
```

**Expected Behavior:**
- Intent: `clarification`
- Tools: None (or minimal)
- Confidence: > 0.7

### 5. FAQ Queries
```python
test_queries = [
    "How do I apply for funding?",
    "What documents do I need?",
    "What are the eligibility requirements?",
    "How long does the application process take?"
]
```

**Expected Behavior:**
- Intent: `faq`
- Tools: None
- Confidence: > 0.8

## Testing the Streaming Endpoint

### Test Script Structure
```python
async def test_streaming_endpoint():
    """Test the V2 streaming endpoint with improved intent system"""

    # Test different query types
    test_cases = [
        {
            "name": "Funding Call Query",
            "message": "What are some open calls for clean energy?",
            "expected_intent": "search_calls",
            "expected_tools": ["eu_portal_search"]
        },
        {
            "name": "Project Search Query",
            "message": "Show me projects about AI in healthcare",
            "expected_intent": "search_projects",
            "expected_tools": ["search_cordis_projects"]
        },
        {
            "name": "Conversational Query",
            "message": "Hello, how can you help me?",
            "expected_intent": "conversational",
            "expected_tools": []
        }
    ]

    for test_case in test_cases:
        print(f"🧪 Testing: {test_case['name']}")
        print(f"   Query: {test_case['message']}")

        # Test the streaming endpoint
        response = await test_streaming_response(test_case['message'])

        # Validate results
        validate_intent_analysis(response, test_case)
```

### Validation Criteria

1. **Intent Accuracy**: Correct intent classification
2. **Tool Selection**: Appropriate tools selected for intent
3. **Confidence Levels**: High confidence scores (>0.8 for clear intents)
4. **Response Quality**: Relevant and helpful responses
5. **Streaming Performance**: Smooth streaming without errors

## Expected Improvements

### 1. Reliability
- **Before**: Rule conflicts and edge cases caused unpredictable behavior
- **After**: Single AI model provides consistent decisions

### 2. Accuracy
- **Before**: Complex keyword matching missed nuanced queries
- **After**: AI understands context and intent better

### 3. Maintainability
- **Before**: 500+ lines of complex rule logic
- **After**: Clean, focused AI-only service

### 4. Performance
- **Before**: Multiple AI calls with fallbacks
- **After**: Single AI call for all decisions

### 5. User Experience
- **Before**: Sometimes incorrect tool routing
- **After**: More accurate intent understanding

## Integration Testing

### Test with Real API
```python
async def integration_test():
    """Test with actual EU Portal and CORDIS APIs"""

    # Test successful tool execution
    queries_with_expected_results = [
        "open calls for energy",
        "projects about renewable energy",
        "funding opportunities in AI"
    ]

    for query in queries_with_expected_results:
        result = await process_with_improved_system(query)
        assert result['success'] == True
        assert len(result['tools_executed']) > 0
```

### Error Handling Test
```python
async def error_handling_test():
    """Test error scenarios"""

    # Test with API failures
    # Test with malformed responses
    # Test with network timeouts
    # Verify graceful fallbacks
```

## Performance Benchmarks

### Before vs After Comparison
- **Latency**: Expected 20-30% improvement
- **Accuracy**: Expected 15-25% improvement
- **Maintenance**: 80% reduction in code complexity
- **Reliability**: 90% reduction in edge cases

## Monitoring and Metrics

### Key Metrics to Track
1. **Intent Accuracy Rate**: Percentage of correctly classified intents
2. **Tool Selection Accuracy**: Percentage of appropriate tool choices
3. **Response Quality Score**: User satisfaction with responses
4. **System Reliability**: Uptime and error rates
5. **Performance Metrics**: Response time and throughput

## Rollout Strategy

### 1. Development Testing
- Unit tests for AI Intent Service
- Integration tests with conversation manager
- End-to-end streaming endpoint tests

### 2. Staging Environment
- Test with production-like data
- Monitor performance and accuracy
- A/B testing against old system

### 3. Gradual Rollout
- Start with percentage of traffic
- Monitor for issues
- Full rollout once validated

## Conclusion

The AI-only intent system represents a significant improvement over the complex rule-based approach. By leveraging modern AI capabilities, we achieve:

- **Better accuracy** through contextual understanding
- **Simplified architecture** with fewer moving parts
- **Easier maintenance** with less code to manage
- **More reliable behavior** with consistent AI decisions
- **Better user experience** with more accurate intent detection

The testing strategy ensures we validate these improvements while maintaining system reliability during the transition.