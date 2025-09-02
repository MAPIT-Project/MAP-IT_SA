#!/usr/bin/env python3
"""
Test call-specific RAG directly for nuclear energy.
"""

import sys
import os
sys.path.append('.')

from app.services.call_specific_rag import CallSpecificRAG
from app.services.rag_service import CordisRAG

def test_call_specific_directly():
    print('🧪 Testing Call-Specific RAG Directly')
    print('=' * 60)

    try:
        # Initialize the systems
        cordis_rag = CordisRAG()
        call_rag = CallSpecificRAG(cordis_rag=cordis_rag)
        
        query = "Are there any open calls related to nuclear energy?"
        print(f'Query: "{query}"')
        print()
        
        # Test call-specific RAG directly
        print('🚀 Testing call-specific RAG handle_call_specific_query...')
        result = call_rag.handle_call_specific_query(query)
        
        print(f'✅ Result status: {result.get("success", False)}')
        print(f'📊 Data source: {result.get("data_source", "Unknown")}')
        print(f'🎯 Intent: {result.get("intent", "Unknown")}')
        
        if result.get('success'):
            answer = result.get('answer', '')
            print(f'📝 Answer length: {len(answer)} characters')
            
            # Show first 300 characters
            if len(answer) > 300:
                print(f'📄 Answer preview: {answer[:300]}...')
            else:
                print(f'📄 Answer: {answer}')
        else:
            print(f'❌ Error: {result.get("error", "Unknown error")}')
    
    except Exception as e:
        print(f'❌ Error during test: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_call_specific_directly()