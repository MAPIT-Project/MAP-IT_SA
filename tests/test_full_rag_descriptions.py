#!/usr/bin/env python3
"""
Test script for enhanced descriptions in full RAG pipeline.
"""

import sys
import os
sys.path.append('.')

from app.services.call_specific_rag import CallSpecificRAG
from app.services.rag_service import CordisRAG

def test_full_rag_descriptions():
    print('🧪 Testing Enhanced Descriptions in Full RAG Pipeline')
    print('=' * 70)

    try:
        # Initialize the system
        cordis_rag = CordisRAG()
        call_rag = CallSpecificRAG(cordis_rag=cordis_rag)

        # Test with the same query
        query = 'What are some open calls related to quantum mechanics?'
        print(f'Query: {query}')
        print()
        
        result = call_rag.handle_call_specific_query(query)

        if result.get('success'):
            print('✅ RAG Success')
            print(f'Data Source: {result.get("data_source", "Unknown")}')
            print(f'Intent: {result.get("intent", "Unknown")}')
            print()
            
            print('Answer preview:')
            print('-' * 50)
            answer = result['answer']
            # Show first 1000 characters to see the enhanced descriptions
            if len(answer) > 1000:
                print(answer[:1000] + '...')
            else:
                print(answer)
        else:
            print('❌ RAG Failed')
            error = result.get('error', 'Unknown error')
            print(f'Error: {error}')
    
    except Exception as e:
        print(f'❌ Error during test: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_rag_descriptions()