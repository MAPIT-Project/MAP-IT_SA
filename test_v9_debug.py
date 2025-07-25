#!/usr/bin/env python3
"""
Debug script to test V9 response format and identify the JSON serialization issue.
"""
import os
import sys
import json
from typing import Dict, Any

# Mock minimal imports to avoid dependency issues
class MockOpenAI:
    def __init__(self, api_key): pass
    def chat(self): return MockCompletions()

class MockCompletions:
    def completions(self): return self
    def create(self, **kwargs):
        # Mock response that simulates the actual V9 behavior
        mock_response = type('MockResponse', (), {})()
        mock_response.choices = [type('Choice', (), {})()]
        mock_response.choices[0].message = type('Message', (), {})()
        mock_response.choices[0].message.content = "CLASSIFICATION: SEARCH_CALLS\nCONFIDENCE: 1.0\nREASONING: User is asking about open calls"
        return mock_response

# Monkey patch to avoid import errors
sys.modules['openai'] = type('openai', (), {'OpenAI': MockOpenAI})()
sys.modules['google'] = type('google', (), {})()
sys.modules['google.genai'] = type('genai', (), {'Client': lambda api_key: None, 'types': type('types', (), {})()})()

# Set required environment variables
os.environ['GEMINI_API_KEY'] = 'test-key'

# Now try to import V9
try:
    from cordisBased_RAG_function_new_V9 import CordisRAG
    
    print("🧪 Testing V9 Call Search Response Format")
    print("=" * 50)
    
    # Test the search_for_calls method directly
    rag = CordisRAG(ai_provider='gemini')
    
    # Test call search directly
    print("1. Testing search_for_calls method...")
    call_result = rag.search_for_calls("Are there any open calls for AI research?", max_results=3)
    
    print(f"Call result type: {type(call_result)}")
    print(f"Call result keys: {list(call_result.keys()) if isinstance(call_result, dict) else 'Not a dict'}")
    
    if isinstance(call_result, dict):
        answer = call_result.get('answer', '')
        print(f"Answer type: {type(answer)}")
        print(f"Answer length: {len(answer)}")
        print(f"Answer preview (first 100 chars): {answer[:100]}...")
        print(f"Answer is string: {isinstance(answer, str)}")
        
        # Check if the answer itself contains stringified JSON
        if answer.startswith("{'") or answer.startswith('{"'):
            print("❌ ISSUE FOUND: Answer contains stringified dictionary!")
        else:
            print("✅ Answer format looks correct")
    
    print("\n2. Testing full get_ai_response method...")
    # Test the full pipeline
    full_result = rag.get_ai_response("Are there any open calls for AI research?", max_projects_to_process=3)
    
    print(f"Full result type: {type(full_result)}")
    print(f"Full result keys: {list(full_result.keys()) if isinstance(full_result, dict) else 'Not a dict'}")
    
    if isinstance(full_result, dict):
        final_answer = full_result.get('answer', '')
        print(f"Final answer type: {type(final_answer)}")
        print(f"Final answer preview: {final_answer[:100]}...")
        
        # Check if the final answer contains stringified JSON
        if final_answer.startswith("{'") or final_answer.startswith('{"'):
            print("❌ ISSUE FOUND: Final answer contains stringified dictionary!")
            print("🔍 This means the issue is in V9 itself, not in FastAPI")
        else:
            print("✅ Final answer format looks correct")
            
        print(f"Data source: {full_result.get('data_source', 'Unknown')}")
        print(f"Routing decision: {full_result.get('routing_decision', 'Unknown')}")
    
    print("\n3. Testing JSON serialization...")
    try:
        json_str = json.dumps(full_result, indent=2)
        print("✅ Result can be JSON serialized")
        print(f"JSON length: {len(json_str)}")
    except Exception as e:
        print(f"❌ JSON serialization error: {e}")

except Exception as e:
    print(f"❌ Error running test: {e}")
    import traceback
    traceback.print_exc()

print("\nDone! Check the output above to identify where the stringification is happening.") 