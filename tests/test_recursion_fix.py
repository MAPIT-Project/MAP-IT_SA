#!/usr/bin/env python3
"""
Test script to verify the infinite recursion fix in the V9 RAG system.
"""
import os
import sys
import time
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.append('app')

def test_intent_detection():
    """Test that intent detection works without infinite recursion."""
    
    print("🧪 Testing V9 RAG System - Recursion Fix")
    print("=" * 50)
    
    try:
        # Import after adding path
        from services.rag_service import CordisRAG
        from services.call_specific_rag import CallSpecificRAG
        
        print("✅ Imports successful")
        
        # Test the exact question that was causing the recursion
        test_question = "What is the total budget for Horizon Europe 2021-2027?"
        print(f"🎯 Testing question: '{test_question}'")
        
        # Test CallSpecificRAG independently first
        print("\n1️⃣ Testing CallSpecificRAG.detect_call_specific_intent()...")
        
        start_time = time.time()
        call_rag = CallSpecificRAG()
        intent_type, call_identifier, confidence = call_rag.detect_call_specific_intent(test_question)
        elapsed_time = time.time() - start_time
        
        print(f"   ✅ Completed in {elapsed_time:.3f}s (no recursion!)")
        print(f"   📊 Result: intent='{intent_type}', identifier='{call_identifier}', confidence={confidence:.2f}")
        
        # Test CordisRAG.determine_user_intent()
        print("\n2️⃣ Testing CordisRAG.determine_user_intent()...")
        
        # We need to mock the environment variables for this test
        os.environ.setdefault('GEMINI_API_KEY', 'test_key')
        os.environ.setdefault('OPENAI_API_KEY', 'test_key')
        
        start_time = time.time()
        cordis_rag = CordisRAG(ai_provider="gemini", use_local_db=False)
        
        # This should not cause infinite recursion anymore
        intent, confidence = cordis_rag.determine_user_intent(test_question)
        elapsed_time = time.time() - start_time
        
        print(f"   ✅ Completed in {elapsed_time:.3f}s (no recursion!)")
        print(f"   📊 Result: intent='{intent}', confidence={confidence:.2f}")
        
        # Test a few more questions to ensure robustness
        test_questions = [
            "Are there any open calls for renewable energy research?",
            "What AI projects have been funded in healthcare?",
            "Show me successful cybersecurity initiatives"
        ]
        
        print("\n3️⃣ Testing additional questions...")
        for i, question in enumerate(test_questions, 1):
            print(f"   {i}. '{question}'")
            start_time = time.time()
            
            # Test CallSpecificRAG
            intent_type, call_id, conf1 = call_rag.detect_call_specific_intent(question)
            
            # Test CordisRAG  
            intent, conf2 = cordis_rag.determine_user_intent(question)
            
            elapsed_time = time.time() - start_time
            print(f"      ✅ {elapsed_time:.3f}s - CallRAG: {intent_type}({conf1:.2f}) | CordisRAG: {intent}({conf2:.2f})")
        
        print("\n🎉 ALL TESTS PASSED - Infinite recursion fixed!")
        return True
        
    except RecursionError as e:
        print(f"❌ RECURSION ERROR STILL EXISTS: {e}")
        return False
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_timeout():
    """Test with a timeout to catch infinite recursion."""
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Test timed out - likely infinite recursion")
    
    # Set a 10-second timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(10)
    
    try:
        result = test_intent_detection()
        signal.alarm(0)  # Cancel the alarm
        return result
    except TimeoutError as e:
        print(f"❌ TIMEOUT: {e}")
        return False
    except Exception as e:
        signal.alarm(0)  # Cancel the alarm
        raise e

if __name__ == "__main__":
    print("🚀 Starting Recursion Fix Test...")
    
    success = test_with_timeout()
    
    if success:
        print("\n✅ SUCCESS: The infinite recursion issue has been fixed!")
        exit(0)
    else:
        print("\n❌ FAILURE: The recursion issue may still exist.")
        exit(1)