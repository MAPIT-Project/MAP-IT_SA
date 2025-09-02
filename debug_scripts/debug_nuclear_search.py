#!/usr/bin/env python3
"""
Debug script to investigate nuclear energy search issues.
"""

import sys
import os
sys.path.append('.')

from app.services.enhanced_call_search import EnhancedCallSearchService

def debug_nuclear_search():
    print('🔍 Debugging Nuclear Energy Search')
    print('=' * 60)

    try:
        service = EnhancedCallSearchService()
        
        # Test semantic tags first
        tags = service._get_semantic_tags('nuclear energy')
        print(f'📋 Semantic tags for "nuclear energy":')
        for i, tag in enumerate(tags, 1):
            print(f'  {i}. {tag.code} (boost: {tag.boost})')
        print()
        
        # Test search with different parameters
        queries_to_test = [
            'nuclear energy',
            'nuclear power',
            'nuclear research',
            'EURATOM',
            'nuclear fusion',
            'nuclear safety'
        ]
        
        for query in queries_to_test:
            print(f'🔍 Testing: "{query}"')
            result = service.search_calls_enhanced(
                query=query, 
                max_results=5, 
                include_closed=True  # Include closed to see if there are ANY nuclear calls
            )
            
            if result['status'] == 'success':
                print(f'  Found {len(result["results"])} results')
                
                # Show first 2 results to check relevance
                for i, call in enumerate(result['results'][:2], 1):
                    title = call.title[:80] + '...' if len(call.title) > 80 else call.title
                    print(f'    {i}. {title}')
                    print(f'       ID: {call.identifier}')
                    print(f'       Status: {call.status}')
                    
                    # Check if title contains nuclear-related terms
                    nuclear_terms = ['nuclear', 'euratom', 'fusion', 'fission', 'radioactive', 'atomic']
                    is_nuclear = any(term in call.title.lower() or term in call.identifier.lower() for term in nuclear_terms)
                    print(f'       Nuclear-related: {"✅" if is_nuclear else "❌"}')
                print()
            else:
                print(f'  ❌ Search failed: {result.get("search_metadata", {}).get("error", "Unknown")}')
            print()
    
    except Exception as e:
        print(f'❌ Error during debug: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_nuclear_search()