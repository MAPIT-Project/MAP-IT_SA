#!/usr/bin/env python3
"""
Test script to debug why "What are some open calls related to nuclear" doesn't trigger tools.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.conversation.conversation_manager import ConversationManager

async def test_nuclear_query():
    """Test the nuclear query to see where the tool detection fails."""
    print("🧪 Testing nuclear query: 'What are some open calls related to nuclear'")
    print("=" * 80)

    try:
        # Initialize conversation manager
        manager = ConversationManager()
        print("✅ ConversationManager initialized")

        # Test conversation ID
        conv_id = 9999

        # Test the exact query from the user
        test_message = "What are some open calls related to nuclear"

        print(f"\n📝 Testing message: '{test_message}'")
        print("-" * 50)

        # Step 1: Test the combined intent analysis phase directly
        print("🔧 Step 1: Testing combined intent analysis...")
        try:
            intent_analysis, context, tool_plan = await manager._combined_intent_context_tool_planner(
                conversation_id=conv_id,
                user_message=test_message
            )

            print(f"   Intent analysis: {intent_analysis}")
            print(f"   Tool plan: {tool_plan}")
            print(f"   Context length: {len(context)}")

            if tool_plan:
                print(f"   ✅ SUCCESS: Tool plan created with {len(tool_plan)} tools")
                for i, tool_call in enumerate(tool_plan):
                    print(f"      Tool {i+1}: {tool_call.tool_name}")
            else:
                print("   ❌ No tool plan created")

        except Exception as e:
            print(f"   ❌ Combined phase failed: {e}")
            import traceback
            traceback.print_exc()

        # Step 2: Test the forced tool planner directly
        print("\n🔧 Step 2: Testing forced tool planner...")
        try:
            # Create a mock intent analysis
            mock_intent_analysis = {
                "intent_type": "question",
                "requires_retrieval": True,
                "requires_tools": True,
                "confidence": 0.8,
                "explanation": "User asking about open calls"
            }

            mock_context = "Test context for nuclear query"

            tool_plan = await manager._forced_tool_planner(
                user_message=test_message,
                intent_analysis=mock_intent_analysis,
                context=mock_context,
                conversation_id=conv_id
            )

            print(f"   Tool plan: {tool_plan}")

            if tool_plan:
                print(f"   ✅ SUCCESS: Forced tool planner created {len(tool_plan)} tools")
                for i, tool_call in enumerate(tool_plan):
                    print(f"      Tool {i+1}: {tool_call.tool_name}")
            else:
                print("   ❌ No tool plan from forced planner")

        except Exception as e:
            print(f"   ❌ Forced tool planner failed: {e}")
            import traceback
            traceback.print_exc()

        # Step 3: Test keyword detection logic directly
        print("\n🔧 Step 3: Testing keyword detection logic...")
        try:
            message_lower = test_message.lower()

            # Test call keywords
            call_keywords = [
                'open calls', 'funding calls', 'call for proposals', 'grant calls',
                'submission deadline', 'funding opportunities', 'horizon calls',
                'eu calls', 'research calls', 'proposal calls'
            ]

            call_detected = any(keyword in message_lower for keyword in call_keywords)
            print(f"   Call keywords detected: {call_detected}")
            if call_detected:
                print(f"   ✅ SUCCESS: 'open calls' keyword found in message")
            else:
                print("   ❌ No call keywords detected")

            # Test domain + funding patterns
            import re
            domain_funding_patterns = [
                r'\b(energy|automotive|ai|health|climate|digital)\b.*\b(call|funding|grant|opportunity)\b',
                r'\b(call|funding|grant|opportunity)\b.*\b(energy|automotive|ai|health|climate|digital)\b',
                r'open.*\b(energy|automotive|ai|health|climate|digital)\b',
                r'\b(energy|automotive|ai|health|climate|digital)\b.*open'
            ]

            domain_pattern_detected = any(re.search(pattern, message_lower) for pattern in domain_funding_patterns)
            print(f"   Domain + funding patterns detected: {domain_pattern_detected}")

        except Exception as e:
            print(f"   ❌ Keyword detection test failed: {e}")

        # Step 4: Test the full process
        print("\n🔧 Step 4: Testing full process...")
        try:
            response = await manager.process_message(
                conversation_id=conv_id,
                user_message=test_message,
                user_id=1,
                streaming=False
            )

            tools_executed = response.get('tools_executed', False)
            print(f"   Tools executed: {tools_executed}")
            print(f"   Response preview: {response.get('response', 'No response')[:200]}...")

            if tools_executed:
                print("   ✅ SUCCESS: Full process executed tools")
            else:
                print("   ❌ Full process did not execute tools")

        except Exception as e:
            print(f"   ❌ Full process failed: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "=" * 80)
        print("✅ Nuclear query test completed!")

    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_nuclear_query())