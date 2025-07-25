#!/usr/bin/env python3
"""
Direct test of V9 functionality without FastAPI server
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_v9_direct():
    """Test V9 functionality directly"""
    try:
        # Import V9
        from cordisBased_RAG_function_new_V9 import CordisRAG
        print("✅ V9 module imported successfully")
        
        # Create instance
        rag = CordisRAG(
            ai_provider="gemini",
            use_local_db=False
        )
        print("✅ V9 instance created successfully")
        
        # Test intent classification
        intent, confidence = rag.determine_user_intent("Are there open calls for AI research?")
        print(f"✅ Intent classification: {intent} (confidence: {confidence:.2f})")
        
        # Test call search
        if intent == "SEARCH_CALLS":
            print("🔍 Testing call search...")
            result = rag.search_for_calls("AI research", max_results=2)
            print(f"✅ Call search completed: {result.get('call_count', 0)} calls found")
            print(f"Search successful: {result.get('search_successful', False)}")
        
        # Test full routing
        print("🔍 Testing full V9 routing...")
        response = rag.get_ai_response_with_routing("Are there any open calls for quantum computing?")
        print(f"✅ Full routing test completed")
        print(f"Response type: {type(response)}")
        if isinstance(response, dict):
            print(f"Routing decision: {response.get('routing_decision', 'Not found')}")
            print(f"Answer length: {len(response.get('answer', ''))}")
        
        return True
        
    except Exception as e:
        print(f"❌ V9 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing V9 functionality directly...")
    print("=" * 50)
    
    success = test_v9_direct()
    
    if success:
        print("\n🎉 V9 direct test PASSED!")
    else:
        print("\n❌ V9 direct test FAILED!") 