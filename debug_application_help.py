#!/usr/bin/env python3
"""
Debug script to trace exactly where the error is coming from.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.conversation.conversation_manager import ConversationManager

async def debug_conversation_manager():
    """Debug the conversation manager directly"""
    print("🔍 Debugging Conversation Manager directly...")

    try:
        manager = ConversationManager()
        print("✅ ConversationManager initialized successfully")

        # Test the application help question
        conv_id = 99999
        question = "How do I apply for funding?"

        print(f"\n📝 Testing: '{question}'")

        response = await manager.process_message(
            conversation_id=conv_id,
            user_message=question,
            user_id=1,
            streaming=False
        )

        print(f"\n📊 Response Analysis:")
        print(f"   Response type: {type(response)}")
        print(f"   Keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")

        if isinstance(response, dict):
            print(f"   Response: {response.get('response', 'No response')[:200]}...")
            print(f"   Tools executed: {response.get('tools_executed', False)}")
            print(f"   Confidence: {response.get('confidence', 0.0)}")
            print(f"   Grounded: {response.get('grounded', False)}")
            print(f"   Error: {response.get('error', 'None')}")

        # Check if it contains the error message
        response_text = response.get('response', '') if isinstance(response, dict) else str(response)
        if "encountered an error accessing the documentation" in response_text:
            print("❌ FOUND THE ERROR: 'encountered an error accessing the documentation'")
            return False
        elif len(response_text) > 100 and 'application' in response_text.lower():
            print("✅ GOOD: Got application-related response")
            return True
        else:
            print(f"⚠️ UNCLEAR: Unexpected response pattern")
            print(f"   Full response: {response_text}")
            return False

    except Exception as e:
        print(f"❌ Exception during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_conversation_manager())
    if success:
        print("\n🎉 Debug test successful!")
    else:
        print("\n❌ Debug test failed!")