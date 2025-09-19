#!/usr/bin/env python3
"""
Final verification test for the improved conversation manager.
Tests the nuclear query example to ensure project searches work end-to-end.
"""

import asyncio
import json
from app.services.conversation.conversation_manager import ConversationManager

async def test_nuclear_query_end_to_end():
    """Test the nuclear query example end-to-end to verify the improvements work."""

    print("🎯 FINAL VERIFICATION: Nuclear Query Test")
    print("=" * 60)

    try:
        # Initialize conversation manager
        manager = ConversationManager()

        # Test conversation ID
        conv_id = 777

        # The nuclear query that should trigger CORDIS search
        nuclear_query = "Look up projects about nuclear stuff"

        print(f"📝 Testing nuclear query: '{nuclear_query}'")
        print(f"Conversation ID: {conv_id}")

        # Process the nuclear query
        response = await manager.process_message(
            conversation_id=conv_id,
            user_message=nuclear_query,
            user_id=1,
            streaming=False
        )

        # Analyze the response
        tools_executed = response.get('tools_executed', False)
        response_text = response.get('response', 'No response')
        processing_time = response.get('processing_time', 0)

        print("\n📊 RESPONSE ANALYSIS")
        print(f"Tools executed: {tools_executed}")
        print(f"Processing time: {processing_time:.3f}s")
        print(f"Response length: {len(response_text)} characters")

        # Check if the response indicates tool execution
        if tools_executed:
            print("✅ SUCCESS: Tools were executed!")
            print("Response preview:")
            print(response_text[:300] + "..." if len(response_text) > 300 else response_text)

            # Check if response contains project-related content
            project_indicators = ['project', 'cordis', 'nuclear', 'research', 'funding', 'search', 'database']
            has_project_content = any(indicator in response_text.lower() for indicator in project_indicators)

            if has_project_content:
                print("✅ SUCCESS: Response contains project-related content!")
                print("🎉 VERIFICATION COMPLETE: The system correctly detected and executed CORDIS search!")
                return True
            else:
                print("⚠️  WARNING: Tools executed but response doesn't seem to contain project data")
                print("   This might indicate tool execution succeeded but result processing failed")
                return False

        else:
            print("❌ FAILURE: No tools were executed")
            print("Response preview:")
            print(response_text[:300] + "..." if len(response_text) > 300 else response_text)

            # Check if it's a conversational response
            conversational_indicators = ['recommend', 'visit', 'website', 'cordis.europa.eu', 'search it here']
            is_conversational = any(indicator in response_text.lower() for indicator in conversational_indicators)

            if is_conversational:
                print("❌ CONFIRMED: This is a conversational response, not actual tool execution")
                print("   The detection logic is still not working properly")
                return False
            else:
                print("🤔 UNEXPECTED: Response doesn't match expected patterns")
                return False

    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_multiple_project_queries():
    """Test multiple project search queries to verify consistency."""

    print("\n🔄 TESTING MULTIPLE PROJECT QUERIES")
    print("=" * 60)

    try:
        manager = ConversationManager()
        conv_id = 888

        # Test various project search queries
        test_queries = [
            "Look up projects about nuclear stuff",
            "Search for projects on clean energy",
            "Find me projects about AI",
            "Show me information on projects for climate change",
            "Get projects related to renewable energy"
        ]

        success_count = 0

        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 Test {i}: '{query}'")

            response = await manager.process_message(
                conversation_id=conv_id,
                user_message=query,
                user_id=1,
                streaming=False
            )

            tools_executed = response.get('tools_executed', False)

            if tools_executed:
                print("   ✅ SUCCESS: Tools executed")
                success_count += 1
            else:
                print("   ❌ FAILURE: No tools executed")

        print("\n📊 MULTIPLE QUERY RESULTS")
        print(f"Success rate: {success_count}/{len(test_queries)} ({success_count/len(test_queries)*100:.1f}%)")

        if success_count >= len(test_queries) * 0.8:  # 80% success rate
            print("✅ SUCCESS: Most project queries are working correctly!")
            return True
        else:
            print("❌ FAILURE: Too many project queries are not triggering tools")
            return False

    except Exception as e:
        print(f"❌ MULTIPLE QUERY TEST FAILED: {e}")
        return False

if __name__ == "__main__":
    async def main():
        print("🚀 STARTING FINAL VERIFICATION TESTS")
        print("=" * 80)

        # Test the nuclear query specifically
        nuclear_success = await test_nuclear_query_end_to_end()

        # Test multiple project queries for consistency
        multiple_success = await test_multiple_project_queries()

        print("\n" + "=" * 80)
        print("🎯 FINAL VERIFICATION RESULTS")
        print("=" * 80)

        if nuclear_success and multiple_success:
            print("✅ ALL TESTS PASSED!")
            print("   The improved conversation manager is working correctly.")
            print("   Project searches are being detected and executed properly.")
            print("   The nuclear query example now works as expected!")
            print("\n🎉 SUCCESS: The architecture improvements have been successfully implemented!")
        else:
            print("❌ SOME TESTS FAILED")
            if not nuclear_success:
                print("   - Nuclear query test failed")
            if not multiple_success:
                print("   - Multiple query consistency test failed")
            print("\n🔧 NEXT STEPS:")
            print("   1. Check if the tool orchestrator is properly configured")
            print("   2. Verify the search_cordis_projects tool is available")
            print("   3. Check for any runtime errors in tool execution")
            print("   4. Ensure the combined phase is not failing silently")

    asyncio.run(main())