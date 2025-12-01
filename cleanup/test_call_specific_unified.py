#!/usr/bin/env python3
"""
Test that the unified classifier properly detects call-specific questions
"""

import requests
import json

API_BASE = "http://localhost:8000/api"

def test_call_specific_detection():
    """Test the exact query the user reported"""
    
    print("=" * 80)
    print("TESTING CALL-SPECIFIC DETECTION WITH UNIFIED CLASSIFIER")
    print("=" * 80)
    print()
    
    conversation_id = 999
    
    # The exact query the user tried
    message = "Can I apply for this call from the netherlands? HORIZON-CL5-2026-01-D2-01"
    
    print(f"Query: {message}")
    print(f"Expected: Should detect call_specific intent with call_id=HORIZON-CL5-2026-01-D2-01")
    print()
    print("=" * 80)
    print("RESPONSE:")
    print("=" * 80)
    print()
    
    response = requests.post(
        f"{API_BASE}/v2/conversation/{conversation_id}/message/stream",
        json={"message": message, "userId": "test-user"},
        stream=True,
        headers={"Accept": "text/event-stream"}
    )
    
    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        return
    
    intent_detected = None
    call_id_detected = None
    response_content = []
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                
                try:
                    data = json.loads(data_str)
                    msg_type = data.get('type')
                    
                    if msg_type == 'status':
                        print(f"⏳ {data.get('stage')}: {data.get('message')}")
                    
                    elif msg_type == 'progress':
                        stage = data.get('stage')
                        message = data.get('message')
                        print(f"📊 {stage}: {message}")
                        
                        # Check if intent was detected
                        if 'intent' in message.lower() or stage == 'intent_detected':
                            intent_detected = data.get('routing_decision') or data.get('message')
                    
                    elif msg_type == 'token':
                        content = data.get('content', '')
                        response_content.append(content)
                        print(content, end='', flush=True)
                    
                    elif msg_type == 'complete':
                        print("\n\n✅ Complete!")
                        
                        # Check for call-specific handling in citations
                        citations = data.get('citations', [])
                        for cit in citations:
                            if 'call' in cit.get('text', '').lower() or 'call' in cit.get('metadata', {}).get('source', ''):
                                print(f"✅ Found call-specific citation: {cit.get('text', '')[:50]}...")
                        
                        break
                    
                    elif msg_type == 'error':
                        print(f"\n❌ Error: {data.get('error')}")
                        break
                
                except json.JSONDecodeError:
                    pass
    
    print()
    print("=" * 80)
    print("RESULT:")
    print("=" * 80)
    
    full_response = ''.join(response_content)
    
    # Check if it properly answered about Netherlands eligibility
    if 'netherlands' in full_response.lower() or 'member state' in full_response.lower() or 'eligible' in full_response.lower():
        print("✅ GOOD: Response mentions eligibility/Netherlands")
    else:
        print("❌ BAD: Response doesn't address Netherlands eligibility")
    
    # Check if it detected call_specific intent
    if intent_detected and 'call' in intent_detected.lower():
        print(f"✅ GOOD: Detected call-related intent: {intent_detected}")
    else:
        print(f"⚠️  Intent detected: {intent_detected}")
    
    print()

if __name__ == "__main__":
    test_call_specific_detection()

