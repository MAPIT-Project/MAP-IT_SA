#!/usr/bin/env python3
"""
Test with a unique query to bypass cache
"""
import asyncio
import os
import time
from dotenv import load_dotenv

load_dotenv()

async def test_fresh_query():
    """Test with a unique query"""
    
    print("=" * 80)
    print("Testing V2 with Fresh Query (Bypass Cache)")
    print("=" * 80)
    
    # Use a unique query with timestamp to bypass cache
    timestamp = int(time.time())
    question = f"What are some open calls for renewable energy? (test_{timestamp})"
    conversation_id = timestamp  # Use timestamp as conversation ID for uniqueness
    user_id = 1
    
    print(f"\n📝 Question: '{question}'")
    print(f"🔢 Conversation ID: {conversation_id}")
    print(f"👤 User ID: {user_id}\n")
    
    try:
        from app.services.conversation.conversation_manager import ConversationManager
        
        print("✅ Initializing ConversationManager...")
        manager = ConversationManager()
        print("✅ ConversationManager initialized\n")
        
        # Process the message
        print(f"🚀 Processing message...")
        result = await manager.process_message(
            conversation_id=conversation_id,
            user_message=question,
            user_id=user_id,
            streaming=False
        )
        
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        
        print(f"\n✅ Response received!")
        print(f"📊 Processing time: {result.get('processing_time', 0):.2f}s")
        print(f"🎯 Confidence: {result.get('confidence', 0):.2f}")
        print(f"🔧 Tools executed: {result.get('tools_executed', [])}")
        
        response_text = result.get('response', '')
        print(f"\n📝 Response length: {len(response_text)} characters")
        print(f"\n📄 Response preview (first 1500 chars):")
        print("-" * 80)
        print(response_text[:1500])
        
        if "No Results Found" in response_text or "couldn't find" in response_text.lower() or "no currently open calls" in response_text.lower():
            print("\n❌ Response indicates NO RESULTS FOUND")
        else:
            print("\n✅ Response contains actual results!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fresh_query())

