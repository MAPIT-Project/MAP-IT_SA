#!/usr/bin/env python3
"""
Debug script to examine the raw API response from the EU portal.
"""

import sys
import os
sys.path.append('.')

from app.services.enhanced_call_search import EnhancedCallSearchService
import json

def debug_api_response():
    print('🔍 Debugging API Response Data')
    print('=' * 60)

    try:
        service = EnhancedCallSearchService()
        
        # Get semantic tags first
        tags = service._get_semantic_tags('quantum mechanics')
        print(f'📋 Found {len(tags)} semantic tags')
        
        # Build query
        query = service._build_advanced_query('quantum mechanics', tags, True, '2021 - 2027')
        
        # Execute search and get raw results
        raw_results = service._execute_enhanced_search(query, 2)
        
        print(f'📊 Found {len(raw_results)} raw results')
        print()
        
        for i, result in enumerate(raw_results[:2], 1):
            print(f'🔍 RESULT {i}:')
            print('-' * 40)
            print(f'Keys available: {list(result.keys())}')
            print()
            
            # Show content fields
            if 'content' in result and result['content']:
                print(f'Content: {result["content"][:200]}...')
            if 'summary' in result and result['summary']:
                print(f'Summary: {result["summary"][:200]}...')
            if 'title' in result and result['title']:
                print(f'Title: {result["title"][:200]}...')
            
            print()
            
            # Show metadata structure
            if 'metadata' in result:
                metadata = result['metadata']
                print(f'Metadata keys: {list(metadata.keys())}')
                print()
                
                # Check for description-like fields
                description_fields = [
                    'description', 'summary', 'furtherInformation', 
                    'missionDescription', 'destinationDescription',
                    'typesOfAction', 'objectiveDescription', 'scopeDescription'
                ]
                
                for field in description_fields:
                    if field in metadata:
                        value = metadata[field]
                        if isinstance(value, list) and value:
                            value = value[0]
                        if value and len(str(value)) > 10:
                            print(f'{field}: {str(value)[:150]}...')
            
            print()
            print('=' * 60)
    
    except Exception as e:
        print(f'❌ Error during debug: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_api_response()