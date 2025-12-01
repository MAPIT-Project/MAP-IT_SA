#!/usr/bin/env python3
"""
Debug script to test "What are some open calls for energy?" query
"""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Test the complete pipeline
def test_energy_call_query():
    """Test the energy call query through the entire pipeline"""
    
    print("=" * 80)
    print("DEBUG: Energy Call Query Test")
    print("=" * 80)
    
    question = "What are some open calls for energy?"
    
    # Step 1: Test intent detection
    print("\n📌 Step 1: Testing Intent Detection")
    print(f"Question: '{question}'")
    
    from app.services.intent_service import IntentService
    intent, confidence = IntentService.determine_intent(question)
    
    print(f"✅ Intent: {intent} (confidence: {confidence:.2f})")
    
    # Step 2: Test RAG routing
    print("\n📌 Step 2: Testing RAG Routing")
    
    from app.services.rag_service import CordisRAG
    rag_service = CordisRAG(use_local_db=False, ai_provider="gemini")
    
    print(f"🔍 Calling get_ai_response_with_routing...")
    try:
        response = rag_service.get_ai_response_with_routing(
            question=question,
            max_projects_to_process=5,
            max_cordis_results=10
        )
        
        print(f"\n✅ Response received:")
        print(f"  - Routing decision: {response.get('routing_decision')}")
        print(f"  - Data source: {response.get('data_source')}")
        print(f"  - Success: {response.get('success')}")
        print(f"  - Call count: {response.get('call_count', 0)}")
        print(f"  - Answer length: {len(response.get('answer', ''))}")
        print(f"\n📝 Answer:")
        print(response.get('answer', 'No answer provided'))
        
        if response.get('error'):
            print(f"\n❌ Error: {response.get('error')}")
        if response.get('fallback_reason'):
            print(f"\n⚠️ Fallback reason: {response.get('fallback_reason')}")
            
    except Exception as e:
        print(f"❌ Error in RAG routing: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 3: Test Enhanced RAG directly
    print("\n📌 Step 3: Testing Enhanced RAG Direct Call")
    
    try:
        from app.services.enhanced_rag_service import HorizonEuropeRAG
        enhanced_rag = HorizonEuropeRAG()
        
        print(f"🔍 Calling handle_call_query...")
        result = enhanced_rag.handle_call_query(question)
        
        print(f"\n✅ Enhanced RAG result:")
        print(f"  - Intent: {result.get('intent')}")
        print(f"  - Data source: {result.get('data_source')}")
        print(f"  - Success: {result.get('success')}")
        print(f"  - Answer length: {len(result.get('answer', ''))}")
        print(f"\n📝 Answer:")
        print(result.get('answer', 'No answer provided'))
        
    except Exception as e:
        print(f"❌ Error in Enhanced RAG: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 4: Test Enhanced Call Search directly
    print("\n📌 Step 4: Testing Enhanced Call Search Service")
    
    try:
        from app.services.enhanced_call_search import EnhancedCallSearchService
        search_service = EnhancedCallSearchService()
        
        print(f"🔍 Calling search_calls_enhanced...")
        result = search_service.search_calls_enhanced(
            query=question,
            max_results=10,
            include_closed=False
        )
        
        print(f"\n✅ Enhanced search result:")
        print(f"  - Status: {result.get('status')}")
        print(f"  - Results count: {len(result.get('results', []))}")
        print(f"  - Search metadata: {result.get('search_metadata', {})}")
        
        if result.get('results'):
            print(f"\n📋 First 3 results:")
            for i, call in enumerate(result['results'][:3]):
                print(f"  {i+1}. {call.title}")
                print(f"     Status: {call.status}, Deadline: {call.deadline}")
        else:
            print("\n⚠️ No results found")
            
    except Exception as e:
        print(f"❌ Error in Enhanced Call Search: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 5: Test CORDIS API directly
    print("\n📌 Step 5: Testing CORDIS API Direct Call")
    
    try:
        queries = ["energy", "clean energy", "renewable energy"]
        print(f"🔍 Testing with queries: {queries}")
        
        calls_found = rag_service._search_cordis_calls_api(queries, max_results=10, original_question=question)
        
        print(f"\n✅ CORDIS API result:")
        print(f"  - Calls found: {len(calls_found) if calls_found else 0}")
        
        if calls_found:
            print(f"\n📋 First 3 calls:")
            for i, call in enumerate(calls_found[:3]):
                print(f"  {i+1}. {call.get('title', 'No title')}")
                print(f"     ID: {call.get('call_id', 'No ID')}")
                print(f"     Status: {call.get('status', 'Unknown')}")
        else:
            print("\n⚠️ No calls found from CORDIS API")
            
    except Exception as e:
        print(f"❌ Error in CORDIS API call: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("DEBUG: Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    test_energy_call_query()


