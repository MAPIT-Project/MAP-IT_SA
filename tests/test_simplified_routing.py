#!/usr/bin/env python3
"""
Test script to verify the simplified routing system only handles 3 functions:
1. FAQ: General questions -> Enhanced RAG
2. SEARCH_PROJECTS: Project search -> CORDIS
3. SEARCH_CALLS: Call search -> EU Portal
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.services.rag_service import CordisRAG

def test_simplified_routing():
    """Test that routing works correctly for the 3 allowed functions only."""
    
    print("🧪 TESTING SIMPLIFIED ROUTING SYSTEM")
    print("=" * 60)
    
    # Initialize the RAG system
    try:
        rag = CordisRAG(ai_provider="openai", use_local_db=False)
        print("✅ RAG system initialized")
    except Exception as e:
        print(f"❌ Failed to initialize RAG: {e}")
        return False
    
    # Test cases for each of the 3 allowed functions
    test_cases = [
        # FAQ queries - should route to Enhanced RAG
        {
            'question': "What are the eligibility criteria for Horizon Europe?",
            'expected_intent': 'FAQ',
            'expected_routing': 'FAQ'
        },
        {
            'question': "How do I apply to Horizon Europe funding?",
            'expected_intent': 'FAQ', 
            'expected_routing': 'FAQ'
        },
        {
            'question': "What is the evaluation process for EU grants?",
            'expected_intent': 'FAQ',
            'expected_routing': 'FAQ'
        },
        
        # Project search queries - should route to CORDIS
        {
            'question': "What AI projects have been funded in healthcare?",
            'expected_intent': 'SEARCH_PROJECTS',
            'expected_routing': 'SEARCH_PROJECTS'
        },
        {
            'question': "Show me renewable energy research projects",
            'expected_intent': 'SEARCH_PROJECTS',
            'expected_routing': 'SEARCH_PROJECTS'
        },
        {
            'question': "Previous work on quantum computing initiatives",
            'expected_intent': 'SEARCH_PROJECTS',
            'expected_routing': 'SEARCH_PROJECTS'
        },
        
        # Call search queries - should route to EU Portal
        {
            'question': "What calls are available for AI research?",
            'expected_intent': 'SEARCH_CALLS',
            'expected_routing': 'SEARCH_CALLS'
        },
        {
            'question': "Show me open calls for climate change",
            'expected_intent': 'SEARCH_CALLS',
            'expected_routing': 'SEARCH_CALLS'
        },
        {
            'question': "Are there any funding opportunities for green energy?",
            'expected_intent': 'SEARCH_CALLS',
            'expected_routing': 'SEARCH_CALLS'
        }
    ]
    
    print(f"\n🔍 Testing {len(test_cases)} queries...")
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        question = test_case['question']
        expected_intent = test_case['expected_intent']
        expected_routing = test_case['expected_routing']
        
        print(f"\n📝 Test {i}: {question}")
        print("-" * 50)
        
        # Test intent detection
        try:
            intent, confidence = rag.determine_user_intent(question)
            print(f"🎯 Intent: {intent} (confidence: {confidence:.2f})")
            
            intent_correct = (intent == expected_intent)
            if intent_correct:
                print(f"✅ Intent detection CORRECT (expected {expected_intent})")
            else:
                print(f"❌ Intent detection WRONG (expected {expected_intent}, got {intent})")
            
        except Exception as e:
            print(f"❌ Intent detection failed: {e}")
            intent_correct = False
            intent = 'ERROR'
        
        # Test full routing
        try:
            result = rag.get_ai_response_with_routing(question, max_projects_to_process=2)
            actual_routing = result.get('routing_decision', 'UNKNOWN')
            
            print(f"🔀 Routing: {actual_routing}")
            
            routing_correct = (actual_routing == expected_routing)
            if routing_correct:
                print(f"✅ Routing CORRECT (expected {expected_routing})")
            else:
                print(f"❌ Routing WRONG (expected {expected_routing}, got {actual_routing})")
            
            # Show response info
            answer_length = len(result.get('answer', ''))
            data_source = result.get('data_source', 'Unknown')
            success = result.get('success', False)
            
            print(f"📊 Response: {answer_length} chars, Source: {data_source}, Success: {success}")
            
        except Exception as e:
            print(f"❌ Routing failed: {e}")
            routing_correct = False
            actual_routing = 'ERROR'
        
        results.append({
            'question': question,
            'expected_intent': expected_intent,
            'actual_intent': intent,
            'intent_correct': intent_correct,
            'expected_routing': expected_routing,
            'actual_routing': actual_routing,
            'routing_correct': routing_correct
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    intent_correct_count = sum(1 for r in results if r['intent_correct'])
    routing_correct_count = sum(1 for r in results if r['routing_correct'])
    total_tests = len(results)
    
    print(f"Intent Detection: {intent_correct_count}/{total_tests} correct ({intent_correct_count/total_tests*100:.1f}%)")
    print(f"Routing: {routing_correct_count}/{total_tests} correct ({routing_correct_count/total_tests*100:.1f}%)")
    
    # Show failures
    failures = [r for r in results if not (r['intent_correct'] and r['routing_correct'])]
    if failures:
        print(f"\n❌ {len(failures)} FAILURES:")
        for f in failures:
            print(f"  • {f['question'][:60]}...")
            if not f['intent_correct']:
                print(f"    Intent: expected {f['expected_intent']}, got {f['actual_intent']}")
            if not f['routing_correct']:
                print(f"    Routing: expected {f['expected_routing']}, got {f['actual_routing']}")
    
    success = (intent_correct_count == total_tests and routing_correct_count == total_tests)
    
    if success:
        print("\n🎉 ALL TESTS PASSED! Simplified routing system working correctly.")
        print("\n✅ The AI is now restricted to only these 3 functions:")
        print("   1. FAQ: Answer questions about EU funding procedures/policies")
        print("   2. SEARCH_PROJECTS: Find existing/past research projects") 
        print("   3. SEARCH_CALLS: Find open funding calls/opportunities")
    else:
        print(f"\n❌ {len(failures)} tests failed. Routing system needs fixing.")
    
    return success

if __name__ == "__main__":
    success = test_simplified_routing()
    exit(0 if success else 1)