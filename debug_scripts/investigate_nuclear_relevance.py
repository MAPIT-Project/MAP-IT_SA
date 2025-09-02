#!/usr/bin/env python3
"""
Investigate why open nuclear calls are being filtered out by relevance.
"""

import sys
import os
sys.path.append('.')

from app.services.enhanced_call_search import EnhancedCallSearchService

def investigate_nuclear_relevance():
    print('🔍 Investigating Nuclear Energy Relevance Filtering')
    print('=' * 60)

    try:
        service = EnhancedCallSearchService()
        
        print('🧪 Step 1: Test nuclear energy search without relevance filtering')
        
        # Get semantic tags first
        tags = service._get_semantic_tags('nuclear energy')
        print(f'📋 Found {len(tags)} semantic tags for "nuclear energy"')
        
        # Build query with open filter
        query_obj = service._build_advanced_query('nuclear energy', tags, {'status_filter': ['31094502']}, '2021 - 2027')
        
        # Execute search
        raw_results = service._execute_enhanced_search(query_obj, 10)
        print(f'📊 Found {len(raw_results)} raw results with OPEN filter')
        
        # Process results
        processed_results = service._process_enhanced_results(raw_results, 'nuclear energy')
        print(f'✅ Processed {len(processed_results)} results')
        
        print('\n🔍 Analyzing each result for nuclear relevance:')
        nuclear_terms = ['nuclear', 'euratom', 'fusion', 'fission', 'radioactive', 'atomic']
        
        for i, result in enumerate(processed_results, 1):
            print(f'\n{i}. {result.title}')
            print(f'   ID: {result.identifier}')
            print(f'   Programme: {result.framework_programme}')
            print(f'   Description: {result.description[:100]}...')
            
            # Check for nuclear relevance
            all_text = f"{result.title} {result.identifier} {result.description} {result.framework_programme}".lower()
            nuclear_matches = [term for term in nuclear_terms if term in all_text]
            
            print(f'   Nuclear terms found: {nuclear_matches if nuclear_matches else "NONE"}')
            
            # Calculate relevance score manually
            core_terms = {'nuclear', 'energy'}
            relevance_score = service._calculate_relevance_score(result, core_terms, 'nuclear energy')
            print(f'   Relevance score: {relevance_score:.3f}')
            print(f'   Would pass filter (>= 0.15): {"✅" if relevance_score >= 0.15 else "❌"}')
        
        print('\n🔍 Step 2: Now test without open filter to see all nuclear calls')
        
        # Search without open filter
        result_all = service.search_calls_enhanced('nuclear energy', max_results=10, include_closed=True)
        
        if result_all['status'] == 'success':
            print(f'📊 Found {len(result_all["results"])} results without open filter')
            
            open_count = sum(1 for call in result_all['results'] if call.status == 'Open')
            print(f'Of these, {open_count} are actually open')
            
            if open_count > 0:
                print('\n✅ Open nuclear calls that DO exist:')
                for call in result_all['results']:
                    if call.status == 'Open':
                        print(f'  • {call.title}')
                        print(f'    ID: {call.identifier}')
                        print(f'    Score: {call.score:.3f}')
    
    except Exception as e:
        print(f'❌ Error during investigation: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_nuclear_relevance()