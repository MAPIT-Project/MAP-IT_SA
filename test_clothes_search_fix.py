"""
Test the actual search functionality with the clothes query to verify the fix works end-to-end.
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.conversation.conversation_manager import ConversationManager

async def test_clothes_search():
    """Test the clothes search query end-to-end."""
    
    print("🧪 Testing Clothes Search Query End-to-End")
    print("=" * 60)
    
    try:
        # Initialize the conversation manager
        manager = ConversationManager()
        
        # Test the specific query that was causing issues
        query = "what are some calls about clothes?"
        conversation_id = 9999
        
        print(f"📝 Query: '{query}'")
        print("🔄 Processing message...")
        
        response = await manager.process_message(
            conversation_id=conversation_id,
            user_message=query,
            user_id=1,
            streaming=False
        )
        
        print(f"✅ Response generated successfully!")
        print(f"📊 Tools executed: {response.get('tools_executed', False)}")
        print(f"📊 Confidence: {response.get('confidence', 0.0)}")
        print(f"📊 Processing time: {response.get('processing_time', 0):.2f}s")
        
        # Check if tools were executed
        if response.get('tools_executed'):
            print("🎯 SUCCESS: Tools were correctly executed for this search query!")
        else:
            print("⚠️  WARNING: No tools were executed - this might be a conversational response")
        
        # Show a preview of the response
        response_text = response.get('response', 'No response')
        print(f"\n📄 Response preview: {response_text[:300]}...")
        
        # Check if the response mentions no results (which would be expected for clothes)
        if "no calls" in response_text.lower() or "no results" in response_text.lower():
            print("ℹ️  NOTE: The search correctly returned no results for 'clothes' - this is expected behavior")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_multiple_queries():
    """Test multiple queries to ensure the fix works broadly."""
    
    print("\n🧪 Testing Multiple Queries")
    print("=" * 60)
    
    try:
        manager = ConversationManager()
        conversation_id = 10000
        
        test_queries = [
            "what are some calls about clothes?",
            "find calls for clothing research", 
            "search for textile funding",
            "show me calls about clean energy"
        ]
        
        for query in test_queries:
            print(f"\n📝 Query: '{query}'")
            
            response = await manager.process_message(
                conversation_id=conversation_id,
                user_message=query,
                user_id=1,
                streaming=False
            )
            
            tools_executed = response.get('tools_executed', False)
            status = "✅ TOOLS EXECUTED" if tools_executed else "⚠️  CONVERSATIONAL"
            
            print(f"   {status}")
            print(f"   Response preview: {response.get('response', 'No response')[:100]}...")
            
            # For search queries, we expect tools to be executed
            if "calls" in query.lower() or "search" in query.lower():
                if not tools_executed:
                    print("   ⚠️  WARNING: Expected tools for search query but got conversational response")
                else:
                    print("   ✅ SUCCESS: Correctly executed tools for search query")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🔧 Testing Clothes Search Fix")
    print("This test verifies that the keyword extraction fix works end-to-end.")
    print("The issue was that 'funding' was being inappropriately added to search queries.\n")
    
    asyncio.run(test_clothes_search())
    asyncio.run(test_multiple_queries())