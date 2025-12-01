#!/usr/bin/env python3
"""
Test with the ORIGINAL question after all fixes
"""
import asyncio
import os
import time
from dotenv import load_dotenv

load_dotenv()

async def test_original():
    """Test with the original question"""
    
    print("=" * 80)
    print("Testing ORIGINAL Question: 'What are some open calls for energy?'")
    print("=" * 80)
    
    # Use timestamp for unique conversation ID to bypass cache
    conversation_id = int(time.time())
    question = "What are some open calls for energy?"
    user_id = 1
    
    print(f"\n📝 Question: '{question}'")
    print(f"🔢 Conversation ID: {conversation_id} (fresh cache)\n")
    
    try:
        from app.services.conversation.conversation_manager import ConversationManager
        
        print("✅ Initializing ConversationManager...")
        manager = ConversationManager()
        print("✅ Initialized\n")
        
        # Process the message
        print(f"🚀 Processing...")
        result = await manager.process_message(
            conversation_id=conversation_id,
            user_message=question,
            user_id=user_id,
            streaming=False
        )
        
        print("\n" + "=" * 80)
        print("FINAL RESULTS")
        print("=" * 80)
        
        response_text = result.get('response', '')
        print(f"\n📝 Response length: {len(response_text)} characters")
        print(f"📊 Processing time: {result.get('processing_time', 0):.2f}s")
        print(f"\n📄 Response:")
        print("-" * 80)
        print(response_text[:2000])
        
        if "No Results Found" in response_text or "couldn't find" in response_text.lower() or "no currently open calls" in response_text.lower():
            print("\n\n❌❌❌ ISSUE: Response indicates NO RESULTS ❌❌❌")
            print("The system should be finding energy-related calls!")
        else:
            print("\n\n✅✅✅ SUCCESS: Response contains actual funding calls! ✅✅✅")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_original())


