#!/usr/bin/env python3
"""
Test the streaming endpoint that the frontend actually calls
"""
import requests
import json
import time

def test_streaming_endpoint():
    """Test the actual streaming API endpoint"""
    
    print("=" * 80)
    print("Testing Streaming Endpoint: /api/conversation/{conv_id}/message/stream")
    print("=" * 80)
    
    # Use a test conversation ID
    conversation_id = 99999
    question = "What are some open calls for energy?"
    
    url = f"http://localhost:8000/api/conversation/{conversation_id}/message/stream"
    
    payload = {
        "message": question,
        "include_context": True
    }
    
    print(f"\n📤 Sending request to: {url}")
    print(f"📝 Message: {question}")
    print(f"🔄 Waiting for streaming response...\n")
    
    try:
        response = requests.post(
            url,
            json=payload,
            stream=True,
            timeout=120
        )
        
        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        print(f"✅ Connection established (HTTP {response.status_code})")
        print(f"📥 Streaming response:\n")
        
        full_answer = ""
        tokens_received = 0
        completion_data = None
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                # SSE format: "data: {json}"
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove "data: " prefix
                    
                    try:
                        data = json.loads(data_str)
                        
                        if data.get('type') == 'status':
                            print(f"  🔄 [{data['stage']}] {data.get('message', '')}")
                        
                        elif data.get('type') == 'progress':
                            print(f"  📊 Progress: {data}")
                        
                        elif data.get('type') == 'token':
                            content = data.get('content', '')
                            full_answer += content
                            tokens_received += 1
                            print(content, end='', flush=True)
                        
                        elif data.get('type') == 'complete':
                            completion_data = data
                            print(f"\n\n  ✅ Stream complete!")
                        
                        elif data.get('type') == 'error':
                            print(f"\n  ❌ Error: {data.get('error')}")
                            print(f"     Details: {data.get('details', '')}")
                            
                    except json.JSONDecodeError as e:
                        print(f"  ⚠️ JSON decode error: {e}")
                        print(f"     Raw line: {line_str}")
        
        print("\n" + "=" * 80)
        print("RESULTS SUMMARY")
        print("=" * 80)
        print(f"✅ Tokens received: {tokens_received}")
        print(f"✅ Total answer length: {len(full_answer)} characters")
        
        if completion_data:
            print(f"\n📊 Completion data:")
            print(f"  - Routing decision: {completion_data.get('routing_decision')}")
            print(f"  - Data source: {completion_data.get('data_source')}")
            print(f"  - Processing time: {completion_data.get('processing_time', 0):.2f}s")
            print(f"  - Projects found: {completion_data.get('projects_found', 0)}")
            
            if completion_data.get('citations'):
                print(f"  - Citations: {len(completion_data['citations'])}")
        
        if full_answer:
            print(f"\n📝 Full answer preview (first 500 chars):")
            print(full_answer[:500])
            if len(full_answer) > 500:
                print("...")
        else:
            print("\n⚠️ No answer content received!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Is the server running on localhost:8000?")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_streaming_endpoint()

