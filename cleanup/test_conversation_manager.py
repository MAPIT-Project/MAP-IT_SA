#!/usr/bin/env python3
"""
Test the conversation manager directly to see if it's saving messages properly.
"""

import asyncio
import os
import sys
import json

# Add the project root to the path
sys.path.append('/home/anmar/Documents/VSCODE_REPOS/NEWMAPIT/MAP-IT_SA')

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:54322/postgres'
os.environ['GEMINI_API_KEY'] = 'test-key'  # Set a dummy key for testing

from app.services.conversation.conversation_manager import ConversationManager
import psycopg2
from psycopg2.extras import DictCursor

def get_messages_from_db(conversation_id: int):
    """Get all messages for a conversation from the database"""
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
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

async def test_conversation_manager():
    """Test the conversation manager directly"""
    print("🧪 Testing Conversation Manager Directly")
    print("=" * 50)
    
    conversation_id = 88888  # Use a unique test ID
    
    # Initialize conversation manager
    manager = ConversationManager()
    
    # Send a message
    test_message = "Find me projects about artificial intelligence"
    print(f"📝 Sending message: {test_message}")
    
    try:
        # Process message (non-streaming)
        result = await manager.process_message(
            conversation_id=conversation_id,
            user_message=test_message,
            user_id=1,
            streaming=False
        )
        
        print(f"✅ Response received: {result.get('response', 'No response')[:100]}...")
        print(f"   Citations: {len(result.get('citations', []))}")
        
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
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the test"""
    print("🚀 Testing Conversation Manager Message Persistence")
    print("=" * 60)
    
    # Check database connection
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Cannot connect to database: {e}")
        return
    
    # Run test
    test_passed = await test_conversation_manager()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULT")
    print("=" * 60)
    print(f"Conversation Manager: {'✅ PASSED' if test_passed else '❌ FAILED'}")
    
    if test_passed:
        print("\n🎉 TEST PASSED!")
        print("✅ Conversation manager is saving messages to the database")
    else:
        print("\n⚠️ TEST FAILED")
        print("❌ Conversation manager is not saving messages properly")

if __name__ == "__main__":
    asyncio.run(main())