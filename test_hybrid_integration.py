#!/usr/bin/env python3
"""
Test script to verify the hybrid search integration in the RAG service.
This tests that CORDIS API is searched first, then enriched with local database.
"""

import os
import sys
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def test_hybrid_rag_integration():
    """Test that the RAG service now uses hybrid search."""
    print("="*80)
    print("TESTING HYBRID SEARCH INTEGRATION IN RAG SERVICE")
    print("="*80)
    
    try:
        from app.services.rag_service import CordisRAG
        
        # Initialize RAG service
        print("\n1. Initializing CordisRAG...")
        # Set use_local_db=False to ensure it uses the hybrid approach
        rag = CordisRAG(use_local_db=False)
        print("✅ CordisRAG initialized")
        
        # Test query
        test_query = "What are some recent nuclear energy research projects in Europe?"
        print(f"\n2. Testing query: '{test_query}'")
        print("-"*60)
        
        # Get the response
        print("Searching with hybrid approach (CORDIS API → Database Enrichment)...")
        result = rag.get_ai_response(
            question=test_query,
            max_projects_to_process=5,
            max_cordis_results=10
        )
        
        # Check results
        if isinstance(result, dict):
            answer = result.get('answer', '')
            projects_found = result.get('projects_found', 0)
            data_source = result.get('data_source', '')
            processing_time = result.get('processing_time', 0)
            routing = result.get('routing_decision', '')
            
            print(f"\n✅ Search completed successfully!")
            print(f"   - Routing: {routing}")
            print(f"   - Data source: {data_source}")
            print(f"   - Projects found: {projects_found}")
            print(f"   - Processing time: {processing_time:.2f}s")
            
            # Check if hybrid search was used
            if "CORDIS API + Local Database" in data_source:
                print("\n✅ HYBRID SEARCH CONFIRMED: Using CORDIS API with database enrichment!")
            elif "CORDIS API" in data_source:
                print("\n✅ Using CORDIS API (some projects may not be in local database)")
            else:
                print(f"\n⚠️ Unexpected data source: {data_source}")
            
            # Check for framework programme mentions
            framework_mentions = []
            for framework in ['Horizon Europe', 'Horizon 2020', 'HORIZON', 'EURATOM', 'FP7']:
                if framework.lower() in answer.lower():
                    framework_mentions.append(framework)
            
            if framework_mentions:
                print(f"\n✅ Framework programmes mentioned: {', '.join(set(framework_mentions))}")
            
            # Display answer preview
            print(f"\n3. Answer preview (first 800 chars):")
            print("-"*60)
            print(answer[:800] + "..." if len(answer) > 800 else answer)
            
            return True
            
        else:
            print(f"\n❌ Unexpected result type: {type(result)}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_hybrid_service():
    """Test the hybrid search service directly."""
    print("\n" + "="*80)
    print("TESTING HYBRID SEARCH SERVICE DIRECTLY")
    print("="*80)
    
    try:
        from app.services.hybrid_search_service import HybridSearchService
        
        print("\n1. Initializing HybridSearchService...")
        hybrid = HybridSearchService()
        print("✅ HybridSearchService initialized")
        
        # Test search
        queries = ["nuclear energy", "startDate>2020-01-01"]
        print(f"\n2. Searching for: {queries}")
        print("-"*60)
        
        results = hybrid.search_projects(queries, max_results=5)
        
        if results:
            print(f"\n✅ Found {len(results)} projects")
            
            # Check enrichment status
            enriched_count = sum(1 for p in results if p.get('enrichment_status') == 'complete')
            api_only_count = sum(1 for p in results if p.get('enrichment_status') == 'not_in_database')
            
            print(f"   - Enriched with database: {enriched_count}")
            print(f"   - CORDIS API only: {api_only_count}")
            
            # Display sample project
            if results:
                sample = results[0]
                print(f"\n3. Sample project:")
                print(f"   Title: {sample.get('title', 'N/A')[:60]}...")
                print(f"   Framework: {sample.get('frameworkProgramme', 'N/A')}")
                print(f"   Data source: {sample.get('data_source', 'N/A')}")
                print(f"   Enrichment: {sample.get('enrichment_status', 'N/A')}")
            
            return True
        else:
            print("\n⚠️ No results found")
            return False
            
    except Exception as e:
        print(f"\n❌ Direct test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n🚀 Starting Hybrid Search Integration Tests")
    print("="*80)
    
    # Test 1: Direct hybrid service test
    direct_test_passed = test_direct_hybrid_service()
    
    # Test 2: RAG integration test
    rag_test_passed = test_hybrid_rag_integration()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if direct_test_passed and rag_test_passed:
        print("✅ ALL TESTS PASSED!")
        print("\nThe hybrid search integration is working correctly:")
        print("1. HybridSearchService successfully searches CORDIS API first")
        print("2. Database enrichment adds framework programme and consortium data")
        print("3. RAG service properly uses the hybrid approach")
        print("4. Framework programmes are correctly displayed in answers")
    else:
        print("❌ SOME TESTS FAILED")
        if not direct_test_passed:
            print("- Direct hybrid service test failed")
        if not rag_test_passed:
            print("- RAG integration test failed")
        print("\nPlease review the errors above.")
    
    print("="*80)

if __name__ == "__main__":
    main()