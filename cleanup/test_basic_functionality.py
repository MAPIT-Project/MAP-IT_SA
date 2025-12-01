#!/usr/bin/env python3
"""
Basic functionality test for the V2 conversational AI wrapper system.
Tests core functionality to verify the system is working.

This is a quick script to verify basic system functionality.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import sys
import os
import time

def check_server_health(base_url: str) -> bool:
    """Check if server is healthy"""
    try:
        req = urllib.request.Request(f"{base_url}/api/v2/conversation/health")
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                return data.get('status') == 'healthy'
    except Exception:
        pass
    return False

def test_simple_question(base_url: str, conversation_id: int) -> bool:
    """Test a simple question"""
    try:
        url = f"{base_url}/api/v2/conversation/{conversation_id}/message"
        payload = {
            "message": "Hello",
            "include_context": True,
            "memory_strategy": "full"
        }

        json_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                print(data)
                return 'response' in data and len(data['response']) > 0
    except Exception as e:
        print(f"Error testing question: {e}")
    return False

def main():
    """Main test"""
    base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
    conversation_id = 9999

    print("🔍 V2 Conversational AI System - Basic Test")
    print("="*50)
    print(f"🌐 Server: {base_url}")

    # Test 1: Health check
    print("\n1️⃣ Checking server health...")
    if check_server_health(base_url):
        print("✅ Server is healthy")
    else:
        print("❌ Server is not healthy or not responding")
        sys.exit(1)

    # Test 2: Clear conversation
    print("\n2️⃣ Clearing conversation...")
    try:
        req = urllib.request.Request(f"{base_url}/api/v2/conversation/{conversation_id}/memory", method='DELETE')
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print("✅ Conversation cleared")
            else:
                print(f"⚠️ Clear returned status {response.status}")
    except Exception as e:
        print(f"⚠️ Could not clear conversation: {e}")

    # Test 3: Simple question
    print("\n3️⃣ Testing simple question...")
    if test_simple_question(base_url, conversation_id):
        print("✅ Simple question test passed")
    else:
        print("❌ Simple question test failed")
        sys.exit(1)

    print("\n🎉 All basic tests passed!")
    print("The V2 conversational AI system is working correctly.")

if __name__ == "__main__":
    main()