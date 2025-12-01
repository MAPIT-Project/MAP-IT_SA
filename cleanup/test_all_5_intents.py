#!/usr/bin/env python3
"""
Test that ALL 5 intent types work with the unified classifier
"""

import requests
import json
import time

API_BASE = "http://localhost:8000/api"

def test_intent(query: str, expected_intent: str, conversation_id: int = 999):
    """Test a single query"""
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"Expected Intent: {expected_intent}")
    print(f"{'='*80}\n")
    
    response = requests.post(
        f"{API_BASE}/v2/conversation/{conversation_id}/message/stream",
        json={"message": query, "userId": "test-user"},
        stream=True,
        headers={"Accept": "text/event-stream"}
    )
    
    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        return False
    
    detected_intent = None
    response_started = False
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    msg_type = data.get('type')
                    
                    if msg_type == 'status':
                        print(f"⏳ {data.get('stage')}")
                    
                    elif msg_type == 'progress':
                        stage = data.get('stage')
                        if stage == 'intent_detected':
                            detected_intent = data.get('routing_decision')
                            print(f"🎯 Detected: {detected_intent}")
                    
                    elif msg_type == 'token':
                        if not response_started:
                            print(f"\n📝 Response:")
                            response_started = True
                        print(data.get('content', ''), end='', flush=True)
                    
                    elif msg_type == 'complete':
                        print(f"\n\n✅ Complete!\n")
                        break
                    
                    elif msg_type == 'error':
                        print(f"\n❌ Error: {data.get('error')}\n")
                        return False
                
                except json.JSONDecodeError:
                    pass
    
    if detected_intent == expected_intent:
        print(f"✅ Intent detection CORRECT: {detected_intent}")
        return True
    else:
        print(f"❌ Intent detection WRONG: expected '{expected_intent}', got '{detected_intent}'")
        return False

def main():
    """Test all 5 intent types"""
    
    print("\n" + "="*80)
    print("TESTING ALL 5 INTENT TYPES WITH UNIFIED CLASSIFIER")
    print("="*80)
    
    tests = [
        # 1. FAQ
        ("How do I apply for Horizon Europe funding?", "faq"),
        
        # 2. Search Projects
        ("Show me projects about renewable energy", "search_projects"),
        
        # 3. Search Calls
        ("What calls are open for AI research?", "search_calls"),
        
        # 4. Call-Specific
        ("Can I apply from the Netherlands? HORIZON-CL5-2026-01-D2-01", "call_specific"),
        
        # 5. Proposal Writing
        ("Help me write a proposal for HORIZON-CL3-2025-02-CS-ECCC-01", "proposal_writing"),
    ]
    
    results = []
    for query, expected_intent in tests:
        # Use different conversation IDs to avoid context interference
        conversation_id = 1000 + len(results)
        result = test_intent(query, expected_intent, conversation_id)
        results.append((expected_intent, result))
        time.sleep(1)  # Brief pause between tests
    
    print("\n" + "="*80)
    print("FINAL RESULTS:")
    print("="*80)
    
    for intent_type, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {intent_type}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    print(f"\n{passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80 + "\n")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The unified classifier is working for all 5 intents!")
    elif passed >= total * 0.8:
        print("👍 MOST TESTS PASSED! Minor adjustments may be needed.")
    else:
        print("⚠️  NEEDS WORK! Review the failing cases.")

if __name__ == "__main__":
    main()

