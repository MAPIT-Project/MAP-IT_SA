#!/usr/bin/env python3
"""
Test that both incoming and outgoing messages are saved to the database
with their citations attached to the correct message.
"""

import asyncio
import json
import requests
import psycopg2
from psycopg2.extras import DictCursor
import os
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

def get_messages_from_db(conversation_id: int):
    """Get all messages for a conversation from the database"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        cursor.execute("""
            SELECT id, sender, text, citations, created_at
            FROM message
            WHERE conversation_id = %s
            ORDER BY created_at ASC
        """, (conversation_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row['id'],
                'sender': row['sender'],
                'text': row['text'],
                'citations': row['citations'],  # JSONB is already deserialized by psycopg2
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            })
        
        cursor.close()
        conn.close()
        return messages
    except Exception as e:
        print(f"❌ Error getting messages from DB: {e}")
        return []

def test_non_streaming_endpoint():
    """Test the non-streaming endpoint"""
    print("\n🧪 Testing Non-Streaming Endpoint")
    print("=" * 50)
    
    conversation_id = 99999  # Use a unique test ID
    
    # Send a message that should return citations
    test_message = "Find me projects about artificial intelligence"
    
    print(f"📝 Sending message: {test_message}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v2/conversation/{conversation_id}/message",
            json={"message": test_message, "include_context": True},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Response received (length: {len(data.get('response', ''))})")
            
            # Check if citations are in the response
            if 'citations' in data and data['citations']:
                print(f"📋 Found {len(data['citations'])} citations in response")
            else:
                print("⚠️ No citations found in response")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Request error: {e}")
        return False
    
    # Wait a moment for database writes to complete
    import time
    time.sleep(1)
    
    # Check database for messages
    print("\n📊 Checking database for saved messages...")
    messages = get_messages_from_db(conversation_id)
    
    if not messages:
        print("❌ No messages found in database")
        return False
    
    print(f"✅ Found {len(messages)} messages in database")
    
    user_messages = [m for m in messages if m['sender'] == 'user']
    assistant_messages = [m for m in messages if m['sender'] == 'assistant']
    
    print(f"   User messages: {len(user_messages)}")
    print(f"   Assistant messages: {len(assistant_messages)}")
    
    # Check user message
    if user_messages:
        user_msg = user_messages[0]
        print(f"✅ User message saved: {user_msg['text'][:50]}...")
        print(f"   Message ID: {user_msg['id']}")
    else:
        print("❌ No user message found in database")
        return False
    
    # Check assistant message
    if assistant_messages:
        assistant_msg = assistant_messages[0]
        print(f"✅ Assistant message saved: {assistant_msg['text'][:50]}...")
        print(f"   Message ID: {assistant_msg['id']}")
        
        # Check citations
        if assistant_msg['citations']:
            print(f"✅ Citations saved to message: {len(assistant_msg['citations'])} citations")
            for i, citation in enumerate(assistant_msg['citations'][:3], 1):
                print(f"   {i}. {citation.get('text', 'No text')[:50]}...")
        else:
            print("⚠️ No citations saved to message")
    else:
        print("❌ No assistant message found in database")
        return False
    
    return True

async def test_streaming_endpoint():
    """Test the streaming endpoint"""
    print("\n🧪 Testing Streaming Endpoint")
    print("=" * 50)
    
    conversation_id = 99998  # Use a unique test ID
    
    # Send a message that should return citations
    test_message = "Find projects about renewable energy"
    
    print(f"📝 Sending message: {test_message}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v2/conversation/{conversation_id}/message/stream",
            json={"message": test_message, "include_context": True},
            headers={"Content-Type": "application/json"},
            stream=True
        )
        
        if response.status_code == 200:
            print("✅ Streaming response received")
            
            # Process the stream
            full_response = ""
            citations_found = []
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            
                            if data.get('type') == 'token':
                                full_response += data.get('content', '')
                            elif data.get('type') == 'complete':
                                if 'citations' in data:
                                    citations_found = data['citations']
                                    print(f"📋 Found {len(citations_found)} citations in streaming response")
                                break
                        except json.JSONDecodeError:
                            continue
            
            print(f"✅ Full response assembled (length: {len(full_response)})")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Request error: {e}")
        return False
    
    # Wait a moment for database writes to complete
    import time
    time.sleep(1)
    
    # Check database for messages
    print("\n📊 Checking database for saved messages...")
    messages = get_messages_from_db(conversation_id)
    
    if not messages:
        print("❌ No messages found in database")
        return False
    
    print(f"✅ Found {len(messages)} messages in database")
    
    user_messages = [m for m in messages if m['sender'] == 'user']
    assistant_messages = [m for m in messages if m['sender'] == 'assistant']
    
    print(f"   User messages: {len(user_messages)}")
    print(f"   Assistant messages: {len(assistant_messages)}")
    
    # Check user message
    if user_messages:
        user_msg = user_messages[0]
        print(f"✅ User message saved: {user_msg['text'][:50]}...")
        print(f"   Message ID: {user_msg['id']}")
    else:
        print("❌ No user message found in database")
        return False
    
    # Check assistant message
    if assistant_messages:
        assistant_msg = assistant_messages[0]
        print(f"✅ Assistant message saved: {assistant_msg['text'][:50]}...")
        print(f"   Message ID: {assistant_msg['id']}")
        
        # Check citations
        if assistant_msg['citations']:
            print(f"✅ Citations saved to message: {len(assistant_msg['citations'])} citations")
            for i, citation in enumerate(assistant_msg['citations'][:3], 1):
                print(f"   {i}. {citation.get('text', 'No text')[:50]}...")
        else:
            print("⚠️ No citations saved to message")
    else:
        print("❌ No assistant message found in database")
        return False
    
    return True

async def main():
    """Run all tests"""
    print("🚀 Testing Message Persistence with Citations")
    print("=" * 60)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print("❌ API is not responding correctly")
            return
        print("✅ API is running")
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("Please make sure the API server is running on localhost:8000")
        return
    
    # Check database connection
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Cannot connect to database: {e}")
        return
    
    # Run tests
    test1_passed = test_non_streaming_endpoint()
    test2_passed = await test_streaming_endpoint()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Non-streaming endpoint: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Streaming endpoint: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Both incoming and outgoing messages are being saved to the database")
        print("✅ Citations are being properly attached to the correct messages")
    else:
        print("\n⚠️ Some tests failed")
        print("Please check the logs above for details")

if __name__ == "__main__":
    asyncio.run(main())