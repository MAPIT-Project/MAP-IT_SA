#!/usr/bin/env python3
"""
Debug the full nuclear energy search pipeline to find where results get lost.
"""

import sys
import os
sys.path.append('.')

from app.services.enhanced_call_search import EnhancedCallSearchService

def debug_full_pipeline():
    print('🔍 Debug Full Nuclear Energy Search Pipeline')
    print('=' * 60)

    try:
        service = EnhancedCallSearchService()
        
        print('🧪 Testing: "Are there any open calls related to nuclear energy?"')
        
        # This should trigger open filter + nuclear energy search
        result = service.search_calls_enhanced(
            query='Are there any open calls related to nuclear energy?',
            max_results=10,
            include_closed=False
        )
        
        metadata = result.get('search_metadata', {})
        print(f'Status: {result["status"]}')
        print(f'Query: {metadata.get("query", "Unknown")}')
        print(f'Clean query: {metadata.get("clean_query", "Unknown")}')
        print(f'Filter intention: {metadata.get("filter_intention", "Unknown")}')
        print(f'Filters applied: {metadata.get("filters_applied", [])}')
        print(f'Total found (before processing): {metadata.get("total_found", "Unknown")}')
        print(f'Returned (after processing): {metadata.get("returned", "Unknown")}')
        print(f'Filter explanation: {metadata.get("filter_explanation", "None")}')
        
        print(f'\nFinal results: {len(result["results"])}')
        
        for i, call in enumerate(result['results'], 1):
            print(f'{i}. {call.title}')
            print(f'   ID: {call.identifier}')
            print(f'   Status: {call.status}')
            print(f'   Relevance score: {call.metadata.get("relevance_score", "N/A")}')
        
        print('\n🔄 Now testing the same with include_closed=True to compare')
        
        result_all = service.search_calls_enhanced(
            query='nuclear energy',  # Clean query
            max_results=10,
            include_closed=True
        )
        
        print(f'Without open filter: {len(result_all["results"])} results')
        open_calls = [r for r in result_all['results'] if r.status == 'Open']
        print(f'Of these, {len(open_calls)} are open:')
        
        for call in open_calls:
            print(f'  • {call.title} ({call.identifier})')
            print(f'    Score: {call.score:.3f}')
            print(f'    Relevance: {call.metadata.get("relevance_score", "N/A")}')
    
    except Exception as e:
        print(f'❌ Error during debug: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_full_pipeline()