#!/usr/bin/env python3
"""
Test script for enhanced description functionality.
"""

import sys
import os
sys.path.append('.')

from app.services.enhanced_call_search import EnhancedCallSearchService

def test_enhanced_descriptions():
    print('🧪 Testing Enhanced Description Extraction')
    print('=' * 60)

    try:
        service = EnhancedCallSearchService()
        
        # Test with quantum mechanics query
        result = service.search_calls_enhanced('quantum mechanics', max_results=3, include_closed=True)

        if result['status'] == 'success' and result['results']:
            print(f'Found {len(result["results"])} results')
            print()
            
            for i, call in enumerate(result['results'], 1):
                print(f'{i}. {call.title}')
                print(f'   ID: {call.identifier}')
                print(f'   Status: {call.status}')
                print(f'   Description: {call.description}')
                print(f'   Description Length: {len(call.description)} characters')
                print()
        else:
            print('❌ No results found')
            print(f'Status: {result["status"]}')
            if result.get("search_metadata", {}).get("error"):
                print(f'Error: {result["search_metadata"]["error"]}')
    
    except Exception as e:
        print(f'❌ Error during test: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_descriptions()