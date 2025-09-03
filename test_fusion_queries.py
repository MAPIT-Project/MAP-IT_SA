#!/usr/bin/env python3
"""
Test script to verify the enhanced call search fixes for fusion-related queries.
This tests the specific issues reported by the user:
1. "Are there any upcomming calls about fusion?" returning closed calls
2. "Are there any forthcoming call about fusion?" causing NoneType assignment error
"""

import sys
import os
import logging

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_fusion_queries():
    """Test the specific fusion queries that were causing issues."""
    
    try:
        from services.enhanced_call_search import EnhancedCallSearchService
        from services.intelligent_query_parser import IntelligentQueryParser
        
        print("🧪 Testing Enhanced Call Search Fixes for Fusion Queries")
        print("=" * 60)
        
        # Initialize services
        search_service = EnhancedCallSearchService()
        query_parser = IntelligentQueryParser()
        
        # Test queries that were problematic
        test_queries = [
            "Are there any upcomming calls about fusion?",
            "Are there any forthcoming call about fusion?",
            "open calls about fusion",
            "fusion calls"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            print("-" * 40)
            
            # First test the query parser
            try:
                parsed_filters = query_parser.parse_query(query)
                print(f"✅ Query parsing: {parsed_filters.filter_intention}")
                print(f"   Clean query: '{parsed_filters.clean_query}'")
                if parsed_filters.status_filter:
                    print(f"   Status filter: {parsed_filters.status_filter}")
            except Exception as e:
                print(f"❌ Query parsing failed: {e}")
                continue
            
            # Test the enhanced search
            try:
                result = search_service.search_calls_enhanced(
                    query=query,
                    max_results=5,
                    enable_facet_analysis=True
                )
                
                if result['status'] == 'success':
                    print(f"✅ Search successful: {len(result['results'])} results")
                    
                    # Check if status filtering worked correctly
                    if parsed_filters.status_filter:
                        expected_status_codes = parsed_filters.status_filter
                        for res in result['results']:
                            if res.status_code not in expected_status_codes:
                                print(f"❌ WRONG STATUS: {res.identifier} has status {res.status} ({res.status_code}) but expected {expected_status_codes}")
                            else:
                                print(f"✅ Correct status: {res.identifier} - {res.status}")
                    
                    # Show results
                    for i, res in enumerate(result['results'][:3], 1):
                        print(f"  {i}. {res.title}")
                        print(f"     Status: {res.status}, Deadline: {res.deadline}")
                        print(f"     Score: {res.score:.3f}")
                        
                else:
                    print(f"❌ Search failed: {result.get('search_metadata', {}).get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ Search execution failed: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n🎉 Fusion query testing completed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fusion_queries()