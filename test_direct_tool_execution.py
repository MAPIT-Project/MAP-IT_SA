#!/usr/bin/env python3
"""
Test direct tool execution to verify the CORDIS search tool works.
"""

import asyncio
import json
from app.services.conversation.conversation_manager import ConversationManager

async def test_direct_tool_execution():
    """Test if the CORDIS search tool can be executed directly."""

    print("🔧 Testing Direct Tool Execution")
    print("=" * 50)

    try:
        # Initialize conversation manager
        manager = ConversationManager()

        # Test conversation ID
        conv_id = 123

        # Test message that should trigger CORDIS search
        message = "Look up projects about nuclear stuff"

        print(f"📝 Testing message: '{message}'")
        print(f"Conversation ID: {conv_id}")

        # Process the message
        response = await manager.process_message(
            conversation_id=conv_id,
            user_message=message,
            user_id=1,
            streaming=False
        )

        # Analyze the response
        tools_executed = response.get('tools_executed', False)
        response_text = response.get('response', 'No response')

        print("\n📊 RESPONSE ANALYSIS")
        print(f"Tools executed: {tools_executed}")
        print(f"Response length: {len(response_text)} characters")

        # Check if the response contains actual project data or just conversational text
        if tools_executed:
            print("✅ SUCCESS: Tools were executed!")
            print("Response preview:")
            print(response_text[:300] + "..." if len(response_text) > 300 else response_text)

            # Check if response contains project-related content
            project_indicators = ['project', 'cordis', 'nuclear', 'research', 'funding']
            has_project_content = any(indicator in response_text.lower() for indicator in project_indicators)

            if has_project_content:
                print("✅ SUCCESS: Response contains project-related content!")
            else:
                print("⚠️  WARNING: Response doesn't seem to contain project data")

        else:
            print("❌ FAILURE: No tools were executed")
            print("Response preview:")
            print(response_text[:300] + "..." if len(response_text) > 300 else response_text)

            # Check if it's a conversational response
            conversational_indicators = ['recommend', 'visit', 'website', 'cordis.europa.eu', 'search it here']
            is_conversational = any(indicator in response_text.lower() for indicator in conversational_indicators)

            if is_conversational:
                print("❌ CONFIRMED: This is a conversational response, not actual tool execution")
            else:
                print("🤔 UNEXPECTED: Response doesn't match expected patterns")

        # Check available tools
        print("\n🔧 AVAILABLE TOOLS:")
        available_tools = manager.tool_orchestrator.get_available_tools()
        for tool in available_tools:
            print(f"  - {tool['name']}: {tool['description']}")

        return tools_executed

    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_direct_tool_execution())

    print("\n" + "=" * 50)
    print("🎯 FINAL RESULT")
    print("=" * 50)

    if result:
        print("✅ SUCCESS: The system correctly executed tools for the nuclear query!")
        print("   The CORDIS search tool is working properly.")
    else:
        print("❌ FAILURE: The system did NOT execute tools for the nuclear query.")
        print("   The CORDIS search tool is NOT being called when it should be.")
        print("\n🔧 POSSIBLE ISSUES:")
        print("   1. Tool detection logic is not working")
        print("   2. Tool execution is failing silently")
        print("   3. Tool results are not being processed correctly")
        print("   4. Response generation is not using tool results")