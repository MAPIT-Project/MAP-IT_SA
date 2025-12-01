#!/usr/bin/env python3
"""
Test the V2 conversation system with energy call query after the fix
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_v2_energy_call():
    """Test the V2 conversation manager with energy call query"""
    
    print("=" * 80)
    print("Testing V2 Conversation Manager: Energy Call Query")
    print("=" * 80)
    
    question = "What are some open calls for energy?"
    conversation_id = 99999
    user_id = 1
    
    print(f"\n📝 Question: '{question}'")
    print(f"🔢 Conversation ID: {conversation_id}")
    print(f"👤 User ID: {user_id}\n")
    
    try:
        # Import the V2 conversation manager
        from app.services.conversation.conversation_manager import ConversationManager
        
        print("✅ Importing ConversationManager...")
        manager = ConversationManager()
        print("✅ ConversationManager initialized\n")
        
        # Check if eu_portal_search tool is registered
        print("🔍 Checking tool registration...")
        try:
            # Access the tools dict directly
            registered_tools = manager.tool_orchestrator.tools
            print(f"✅ Registered tools ({len(registered_tools)}):")
            for tool_name, tool in registered_tools.items():
                print(f"  - {tool_name}: {tool.description[:60]}...")
            
            if 'eu_portal_search' in registered_tools:
                print("\n✅ ✅ ✅ eu_portal_search tool IS registered! ✅ ✅ ✅\n")
            else:
                print("\n❌ ❌ ❌ eu_portal_search tool NOT registered! ❌ ❌ ❌\n")
                print("Available tools:", list(registered_tools.keys()))
                return
        except Exception as e:
            print(f"⚠️ Could not check tool registration: {e}")
            print("Continuing with the test anyway...\n")
        
        # Process the message
        print(f"🚀 Processing message (non-streaming)...")
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
        print(f"📚 Grounded: {result.get('grounded', False)}")
        print(f"📑 Citations: {len(result.get('citations', []))}")
        
        response_text = result.get('response', '')
        print(f"\n📝 Response length: {len(response_text)} characters")
        print(f"\n📄 Response preview (first 1000 chars):")
        print("-" * 80)
        print(response_text[:1000])
        if len(response_text) > 1000:
            print("\n... (truncated)")
        
        # Check if response indicates no results
        if "No Results Found" in response_text or "couldn't find" in response_text.lower():
            print("\n❌ Response indicates NO RESULTS FOUND")
            print("This means the tool may not have been called or returned no data")
        else:
            print("\n✅ Response contains actual results!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_v2_energy_call())

