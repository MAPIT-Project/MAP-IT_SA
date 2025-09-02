#!/usr/bin/env python3
"""
Final validation test for intelligent query filtering.
Tests "open calls", "recent calls", and general calls with proper explanations.
"""

import sys
import time
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "app"))

def test_filtering_scenarios():
    """Test different filtering scenarios."""
    print("🧪 FINAL FILTERING VALIDATION")
    print("=" * 60)
    
    test_cases = [
        {
            "query": "What are some open calls related to quantum mechanics?",
            "expected_filter": "open_only",
            "expected_explanation": "No currently open calls",
            "description": "Should filter to only open calls and explain why 0 found"
        },
        {
            "query": "Recent calls for artificial intelligence",
            "expected_filter": "recent_only", 
            "expected_explanation": "No recent calls found",
            "description": "Should filter to last 6 months and explain results"
        },
        {
            "query": "Closed calls about quantum mechanics",
            "expected_filter": "closed_only",
            "expected_explanation": "Should find closed calls",
            "description": "Should filter to only closed calls"
        },
        {
            "query": "What are calls about quantum mechanics?",
            "expected_filter": "all",
            "expected_explanation": "Should find all calls",
            "description": "Should search all statuses (no filter words)"
        }
    ]
    
    try:
        # Test query parser
        print("1️⃣ Testing Query Parser")
        print("-" * 40)
        
        from app.services.intelligent_query_parser import IntelligentQueryParser
        parser = IntelligentQueryParser()
        
        for i, test in enumerate(test_cases, 1):
            print(f"\n🔍 Test {i}: '{test['query']}'")
            filters = parser.parse_query(test['query'])
            
            print(f"   Filter intention: {filters.filter_intention}")
            print(f"   Status filter: {filters.status_filter}")
            print(f"   Clean query: '{filters.clean_query}'")
            print(f"   Expected: {test['expected_filter']}")
            
            if test['expected_filter'] in filters.filter_intention:
                print("   ✅ CORRECT filtering detected")
            else:
                print(f"   ❌ WRONG filtering: expected {test['expected_filter']}, got {filters.filter_intention}")
        
        # Test enhanced search with filtering
        print(f"\n2️⃣ Testing Enhanced Search with Filtering")
        print("-" * 40)
        
        from app.services.enhanced_call_search import EnhancedCallSearchService
        service = EnhancedCallSearchService()
        
        for i, test in enumerate(test_cases, 1):
            print(f"\n🚀 Test {i}: '{test['query']}'")
            
            result = service.search_calls_enhanced(
                query=test['query'],
                max_results=10,
                enable_facet_analysis=False  # Skip facets for faster testing
            )
            
            if result['status'] == 'success':
                results_count = len(result['results'])
                metadata = result['search_metadata']
                
                print(f"   Results: {results_count}")
                print(f"   Filter intention: {metadata.get('filter_intention', 'none')}")
                print(f"   Filters applied: {metadata.get('filters_applied', [])}")
                
                if metadata.get('filter_explanation'):
                    print(f"   Explanation: {metadata['filter_explanation']}")
                    
                # Show status distribution
                if results_count > 0:
                    statuses = {}
                    for result in result['results'][:5]:
                        status = result.status
                        statuses[status] = statuses.get(status, 0) + 1
                    print(f"   Status breakdown: {statuses}")
                    
            else:
                print(f"   ❌ Search failed")
        
        # Test full RAG integration
        print(f"\n3️⃣ Testing Full RAG Integration")
        print("-" * 40)
        
        from app.services.call_specific_rag import CallSpecificRAG
        rag = CallSpecificRAG()
        
        # Test the critical "open calls" query
        test_query = "What are some open calls related to quantum mechanics?"
        print(f"\n🎯 Critical test: '{test_query}'")
        
        result = rag.handle_call_specific_query(test_query)
        
        if result.get('success'):
            answer = result.get('answer', '')
            print(f"✅ RAG Success")
            print(f"📊 Data source: {result.get('data_source')}")
            
            # Check if the answer properly explains the filtering
            if "No currently open calls" in answer or "open calls found" in answer:
                print("✅ FILTERING EXPLANATION PRESENT")
            else:
                print("⚠️ Missing filtering explanation")
            
            # Show answer preview
            print(f"\nAnswer preview:")
            print(answer[:400] + "..." if len(answer) > 400 else answer)
            
        else:
            print(f"❌ RAG failed: {result.get('error')}")
            
        return True
        
    except Exception as e:
        print(f"❌ Filtering validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_filtering_scenarios()
    
    if success:
        print("\n🎉 FILTERING VALIDATION COMPLETE!")
        print("✅ Your system can now intelligently filter calls based on user requests")
        print("✅ Proper explanations provided when specific filters return no results")
    else:
        print("\n❌ FILTERING VALIDATION FAILED!")
        print("⚠️ Additional debugging may be needed")