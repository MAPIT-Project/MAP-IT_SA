#!/usr/bin/env python3
"""
Debug script to test open nuclear energy search specifically.
"""

import sys
import os
sys.path.append('.')

from app.services.enhanced_call_search import EnhancedCallSearchService

def debug_open_nuclear_search():
    print('🔍 Debugging Open Nuclear Energy Search')
    print('=' * 60)

    try:
        service = EnhancedCallSearchService()
        
        # Test the exact query that's problematic
        print('🔍 Testing: "Are there any open calls related to nuclear energy?"')
        print('This should trigger OPEN filter + nuclear energy search')
        print()
        
        result = service.search_calls_enhanced(
            query='Are there any open calls related to nuclear energy?',
            max_results=10,
            include_closed=False  # Mimic the open-only filter
        )
        
        if result['status'] == 'success':
            print(f'Found {len(result["results"])} results')
            print(f'Query intention: {result["search_metadata"].get("filter_intention", "unknown")}')
            print(f'Filters applied: {result["search_metadata"].get("filters_applied", [])}')
            print()
            
            nuclear_terms = ['nuclear', 'euratom', 'fusion', 'fission', 'radioactive', 'atomic']
            
            for i, call in enumerate(result['results'], 1):
                title = call.title[:80] + '...' if len(call.title) > 80 else call.title
                print(f'{i}. {title}')
                print(f'   ID: {call.identifier}')
                print(f'   Status: {call.status}')
                
                # Check nuclear relevance
                is_nuclear = any(term in call.title.lower() or term in call.identifier.lower() 
                               or term in call.description.lower() for term in nuclear_terms)
                print(f'   Nuclear-related: {"✅" if is_nuclear else "❌"}')
                print(f'   Score: {call.score:.3f}')
                print()
        else:
            print(f'❌ Search failed: {result.get("search_metadata", {}).get("error", "Unknown")}')
        
        print()
        print('🔍 Now testing nuclear energy WITHOUT open filter (include closed calls)')
        result_all = service.search_calls_enhanced(
            query='nuclear energy',
            max_results=10,
            include_closed=True
        )
        
        if result_all['status'] == 'success':
            print(f'Found {len(result_all["results"])} results when including closed calls')
            open_count = sum(1 for call in result_all['results'] if call.status == 'Open')
            closed_count = sum(1 for call in result_all['results'] if call.status == 'Closed')
            print(f'Open: {open_count}, Closed: {closed_count}')
    
    except Exception as e:
        print(f'❌ Error during debug: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_open_nuclear_search()