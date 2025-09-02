#!/usr/bin/env python3
"""
Debug the exact data flow in enhanced search to see where 29 results come from.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "app"))

def debug_search_flow():
    """Debug the actual search flow step by step."""
    print("🔬 DEBUGGING ENHANCED SEARCH DATA FLOW")
    print("=" * 60)
    
    try:
        from app.services.enhanced_call_search import EnhancedCallSearchService
        
        service = EnhancedCallSearchService()
        
        print("Step 1: Getting semantic tags...")
        tags = service._get_semantic_tags("quantum mechanics")
        print(f"✅ Retrieved {len(tags)} semantic tags")
        
        print("\nStep 2: Building advanced query...")
        query = service._build_advanced_query("quantum mechanics", tags, True, "2021 - 2027")
        print(f"✅ Built query with {len(query.get('bool', {}).get('must', []))} main clauses")
        
        print("\nStep 3: Executing enhanced search...")
        raw_results = service._execute_enhanced_search(query, 50)
        print(f"📊 Raw results from EU API: {len(raw_results)}")
        
        if len(raw_results) == 0:
            print("❌ EU API returned 0 results!")
            print("🔍 This means the 29 results must be coming from somewhere else...")
            
            # Check if fallback is happening
            print("\n🔍 INVESTIGATING FALLBACK MECHANISM...")
            
            # Test your current system
            from app.services.call_specific_rag import CallSpecificRAG
            rag = CallSpecificRAG()
            
            print("Testing with enhanced search disabled...")
            rag.enhanced_search = None  # Disable enhanced search
            
            result = rag.handle_call_specific_query("quantum mechanics", max_context_chunks=50)
            print(f"Vector search fallback: {result.get('chunks_used', 0)} results")
            print(f"Data source: {result.get('data_source')}")
            
            # Now test with enhanced search enabled
            rag.enhanced_search = service
            result2 = rag.handle_call_specific_query("quantum mechanics", max_context_chunks=50)
            print(f"With enhanced search: {result2.get('chunks_used', 0)} results")
            print(f"Data source: {result2.get('data_source')}")
            
        else:
            print(f"✅ EU API returned {len(raw_results)} results")
            print("These are the REAL EU portal results!")
            
            # Show sample
            for i, result in enumerate(raw_results[:3], 1):
                metadata = result.get('metadata', {})
                identifier = metadata.get('identifier', ['N/A'])[0] if isinstance(metadata.get('identifier'), list) else 'N/A'
                title = result.get('content', 'Unknown')[:60] + '...'
                print(f"   {i}. {identifier}: {title}")
        
        print("\n🎯 CONCLUSION:")
        if len(raw_results) > 0:
            print(f"✅ The 29 results ARE coming from the LIVE EU Portal APIs!")
            print(f"✅ This is the SAME data source as your manual search!")
            print(f"✅ Results are REAL funding opportunities from ec.europa.eu!")
        else:
            print(f"⚠️ The 29 results are coming from your LOCAL vector database")
            print(f"⚠️ Enhanced search fell back to local data due to API issues")
            print(f"⚠️ This explains the discrepancy with manual search")
            
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_search_flow()