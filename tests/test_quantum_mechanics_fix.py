#!/usr/bin/env python3
"""
Direct test for the quantum mechanics search issue.
Tests the specific query that was returning only 1 result.
"""

import sys
import time
import os
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "app"))

def test_quantum_mechanics_direct():
    """Test the exact query that was problematic."""
    print("🧪 TESTING QUANTUM MECHANICS SEARCH FIX")
    print("=" * 60)
    print("Query: 'What are some open calls related to quantum mechanics?'")
    print("Expected: ~30+ results (to match manual search of 38)")
    print("=" * 60)
    
    try:
        # Test 1: Direct enhanced search service
        print("\n1️⃣ Testing Enhanced Search Service Directly")
        print("-" * 50)
        
        from app.services.enhanced_call_search import EnhancedCallSearchService
        
        service = EnhancedCallSearchService()
        start_time = time.time()
        result = service.search_calls_enhanced(
            query="quantum mechanics",
            max_results=50,  # Get more results to match manual search
            include_closed=True,
            enable_facet_analysis=True
        )
        elapsed = time.time() - start_time
        
        if result['status'] == 'success':
            print(f"✅ ENHANCED SEARCH: Found {len(result['results'])} results in {elapsed:.3f}s")
            print(f"🏷️ Semantic tags used: {result['search_metadata']['semantic_tags_used']}")
            print(f"📊 Total found: {result['search_metadata']['total_found']}")
        else:
            print(f"❌ Enhanced search failed")
            return False
        
        # Test 2: Intent detection 
        print("\n2️⃣ Testing Intent Detection")
        print("-" * 50)
        
        from app.services.call_specific_rag import CallSpecificRAG
        
        rag = CallSpecificRAG()
        intent_type, call_id, confidence = rag.detect_call_specific_intent("What are some open calls related to quantum mechanics?")
        print(f"Intent detected: {intent_type}, Call ID: {call_id}, Confidence: {confidence:.2f}")
        
        if intent_type != "GENERAL_CALL":
            print(f"❌ WRONG INTENT! Should be GENERAL_CALL, got {intent_type}")
            return False
        
        # Test 3: Full RAG integration
        print("\n3️⃣ Testing Full RAG Integration")
        print("-" * 50)
        
        start_time = time.time()
        result = rag.handle_call_specific_query(
            question="What are some open calls related to quantum mechanics?",
            max_context_chunks=50  # Get more results
        )
        elapsed = time.time() - start_time
        
        if result.get('success'):
            print(f"✅ RAG INTEGRATION: Success in {elapsed:.3f}s")
            print(f"📊 Data source: {result.get('data_source')}")
            print(f"🔗 Sources found: {len(result.get('sources', []))}")
            
            # Check if enhanced search was used
            if 'Enhanced' in result.get('data_source', ''):
                print("🚀 ENHANCED SEARCH WAS USED!")
            else:
                print("⚠️ Fallback search was used")
                
        else:
            print(f"❌ RAG integration failed")
            return False
        
        # Test 4: Main RAG routing
        print("\n4️⃣ Testing Main RAG Routing")
        print("-" * 50)
        
        from app.services.rag_service import CordisRAG
        
        main_rag = CordisRAG()
        start_time = time.time()
        result = main_rag.get_ai_response_with_routing("What are some open calls related to quantum mechanics?")
        elapsed = time.time() - start_time
        
        if result:
            answer = result.get('answer', '')
            call_count = result.get('call_count', 0)
            print(f"✅ MAIN RAG: Generated response in {elapsed:.3f}s")
            print(f"📞 Calls found: {call_count}")
            print(f"🔀 Routing decision: {result.get('routing_decision')}")
            
            # Check the answer for result count
            if "1 relevant funding" in answer:
                print("❌ STILL ONLY FINDING 1 RESULT!")
                print(f"Answer preview: {answer[:300]}")
                return False
            else:
                print("🎉 MULTIPLE RESULTS FOUND!")
                
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_quantum_mechanics_direct()
    if success:
        print("\n🎉 ALL TESTS PASSED! The quantum mechanics search should now work!")
    else:
        print("\n❌ TESTS FAILED! The issue needs more investigation.")