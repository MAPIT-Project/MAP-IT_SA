#!/usr/bin/env python3
"""
Debug why nuclear energy search is routing to general RAG instead of call search.
"""

import sys
import os
sys.path.append('.')

from app.services.call_specific_rag import CallSpecificRAG
from app.services.rag_service import CordisRAG

def debug_routing():
    print('🔍 Debug Nuclear Energy Routing Issue')
    print('=' * 60)

    try:
        # Initialize the RAG systems
        cordis_rag = CordisRAG()
        call_rag = CallSpecificRAG(cordis_rag=cordis_rag)
        
        # Test intent detection
        query = "Are there any open calls related to nuclear energy?"
        print(f'Query: "{query}"')
        print()
        
        # Check call-specific intent detection
        intent_type, call_id, confidence = call_rag.detect_call_specific_intent(query)
        print(f'🎯 Call-specific RAG detection:')
        print(f'   Intent: {intent_type}')
        print(f'   Call ID: {call_id}')
        print(f'   Confidence: {confidence}')
        print()
        
        # Skip the method that doesn't exist, go straight to full routing test
        print(f'🎯 Skipping individual method tests, going to full routing...')
        print()
        
        # Now test the full CordisRAG routing
        print('🔀 Testing full CordisRAG routing...')
        result = cordis_rag.process_query(query)
        
        print(f'🎯 Final routing decision:')
        print(f'   Data source: {result.get("data_source", "Unknown")}')
        print(f'   Routing decision: {result.get("routing_decision", "Unknown")}')
        print(f'   Success: {result.get("search_successful", "Unknown")}')
        
        # Show answer preview
        answer = result.get('answer', '')
        if len(answer) > 200:
            print(f'   Answer preview: {answer[:200]}...')
        else:
            print(f'   Answer: {answer}')
    
    except Exception as e:
        print(f'❌ Error during debug: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_routing()