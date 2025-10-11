#!/usr/bin/env python3
"""
Test the streaming proposal writing functionality end-to-end
"""

import requests
import json
import time

API_BASE = "http://localhost:8000/api"

def test_streaming_proposal():
    """Test streaming proposal draft generation"""
    
    print("🧪 Testing Streaming Proposal Writing\n")
    print("=" * 80)
    
    # Use a test conversation ID (any valid conversation ID will work)
    conversation_id = 1
    print(f"📝 Using conversation ID: {conversation_id}")
    
    # Step 2: Send a proposal writing request with streaming
    print("\n📝 Step 2: Sending proposal writing request...")
    message = "Please help me write a proposal for HORIZON-CL3-2025-02-CS-ECCC-01 about AI-powered cybersecurity threat detection"
    
    print(f"💬 Message: {message}")
    print(f"🔗 URL: {API_BASE}/v2/conversation/{conversation_id}/message/stream")
    print("\n" + "=" * 80)
    print("STREAMING RESPONSE:")
    print("=" * 80 + "\n")
    
    start_time = time.time()
    
    response = requests.post(
        f"{API_BASE}/v2/conversation/{conversation_id}/message/stream",
        json={"message": message, "userId": "test-user"},
        stream=True,
        headers={"Accept": "text/event-stream"}
    )
    
    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        print(response.text)
        return
    
    progress_count = 0
    token_count = 0
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            
            if line_str.startswith('data: '):
                data_str = line_str[6:]  # Remove 'data: ' prefix
                
                try:
                    data = json.loads(data_str)
                    msg_type = data.get('type')
                    
                    if msg_type == 'status':
                        print(f"⏳ Status: {data.get('stage')} - {data.get('message')}")
                    
                    elif msg_type == 'progress':
                        progress_count += 1
                        step = data.get('step', '?')
                        total = data.get('total_steps', '?')
                        message = data.get('message', '')
                        elapsed = time.time() - start_time
                        print(f"📊 Progress [{step}/{total}] ({elapsed:.1f}s): {message}")
                    
                    elif msg_type == 'token':
                        token_count += 1
                        content = data.get('content', '')
                        if token_count == 1:
                            print(f"\n✨ PROPOSAL DRAFT:\n{'-' * 80}")
                        print(content, end='', flush=True)
                    
                    elif msg_type == 'complete':
                        elapsed = time.time() - start_time
                        print(f"\n{'-' * 80}")
                        print(f"\n✅ Complete! ({elapsed:.1f}s)")
                        print(f"   - Progress updates: {progress_count}")
                        print(f"   - Content tokens: {token_count}")
                        print(f"   - Model: {data.get('model_used', 'unknown')}")
                        print(f"   - Citations: {len(data.get('citations', []))}")
                        
                        # Print citations
                        citations = data.get('citations', [])
                        if citations:
                            print(f"\n📚 Citations:")
                            for cit in citations:
                                print(f"   [{cit.get('number')}] {cit.get('text', 'Unknown')}")
                        
                        break
                    
                    elif msg_type == 'error':
                        print(f"\n❌ Error: {data.get('error')}")
                        break
                
                except json.JSONDecodeError:
                    print(f"⚠️  Invalid JSON: {data_str}")
    
    total_time = time.time() - start_time
    print(f"\n{'=' * 80}")
    print(f"🏁 Total time: {total_time:.2f}s")
    print(f"{'=' * 80}\n")

if __name__ == "__main__":
    test_streaming_proposal()

