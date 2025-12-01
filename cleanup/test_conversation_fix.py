#!/usr/bin/env python3
"""
Test to verify the conversation context issue is fixed.
Simulates the exact conversation flow that was failing.
"""

import asyncio
from app.services.conversation.conversation_manager import ConversationManager

async def test_conversation_flow():
    """Test the exact conversation flow that was failing."""
    print("🧪 Testing Conversation Context Fix")
    print("=" * 60)
    print("Simulating: 'renewable energy' → 'include closed calls'")
    print()
    
    manager = ConversationManager()
    conversation_id = 9999
    
    # First message: "Please search for renewable energy calls"
    print("📝 Message 1: 'Please search for renewable energy calls'")
    response1 = await manager.process_message(
        conversation_id=conversation_id,
        user_message="Please search for renewable energy calls",
        user_id=1,
        streaming=False
    )
    
    print(f"✅ Response 1: Tools executed = {response1.get('tools_executed', False)}")
    print(f"📊 Response preview: {response1.get('response', 'No response')[:200]}...")
    print()
    
    # Second message: "Can you also include closed calls?"
    print("📝 Message 2: 'Can you also include closed calls?'")
    response2 = await manager.process_message(
        conversation_id=conversation_id,
        user_message="Can you also include closed calls?",
        user_id=1,
        streaming=False
    )
    
    print(f"✅ Response 2: Tools executed = {response2.get('tools_executed', False)}")
    print(f"📊 Response preview: {response2.get('response', 'No response')[:300]}...")
    
    # Check if the response contains the problematic "clean energy OR renewable energy" text
    response_text = response2.get('response', '')
    if "clean energy OR renewable energy" in response_text:
        print("❌ PROBLEM: Response still contains combined query 'clean energy OR renewable energy'")
    else:
        print("✅ SUCCESS: Response correctly uses only the current query")
    
    # Check if the verification URL is correct
    if "freeTextSearchKeyword=renewable%20energy" in response_text:
        print("✅ SUCCESS: Verification URL correctly uses 'renewable energy'")
    elif "freeTextSearchKeyword=clean%20energy%20OR%20renewable%20energy" in response_text:
        print("❌ PROBLEM: Verification URL incorrectly combines queries")
    else:
        print("ℹ️  Verification URL pattern not found in response")

async def test_direct_search():
    """Test the search service directly to verify it works correctly."""
    print(f"\n🧪 Testing Direct Search Service")
    print("=" * 40)
    
    from app.services.improved_call_search import ImprovedCallSearchService
    
    service = ImprovedCallSearchService()
    
    # Test renewable energy with closed calls
    print("🔍 Testing: 'renewable energy' with include_closed=True")
    result = service.search_calls_simple(
        query="renewable energy",
        max_results=10,
        include_closed=True
    )
    
    print(f"📊 Results found: {len(result['results'])}")
    print(f"✅ Status: {result['status']}")
    
    if result['results']:
        for i, res in enumerate(result['results'][:3], 1):
            print(f"   {i}. {res.title} - {res.status}")

async def main():
    """Run all tests."""
    print("🚀 Testing Conversation Context Fix")
    print("=" * 60)
    
    # Test direct search first
    await test_direct_search()
    
    # Test conversation flow
    await test_conversation_flow()
    
    print(f"\n📋 Test Summary:")
    print(f"• The fix should prevent query combination in follow-up messages")
    print(f"• Each search should use only the current user's query")
    print(f"• Verification URLs should match the actual search terms")

if __name__ == "__main__":
    asyncio.run(main())