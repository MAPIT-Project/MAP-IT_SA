#!/usr/bin/env python3
"""
Test the eu_portal_search tool directly to see what it returns
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_tool_directly():
    """Test the tool execution directly"""
    
    print("=" * 80)
    print("Testing eu_portal_search Tool Directly")
    print("=" * 80)
    
    try:
        from app.services.conversation.conversation_manager import ConversationManager
        
        print("\n✅ Initializing ConversationManager...")
        manager = ConversationManager()
        
        # Get the tool
        tool = manager.tool_orchestrator.tools.get('eu_portal_search')
        if not tool:
            print("❌ eu_portal_search tool not found!")
            return
        
        print(f"✅ Found tool: {tool.name}")
        print(f"📝 Description: {tool.description}")
        
        # Execute the tool directly
        params = {
            'query': 'energy',
            'max_results': 10,
            'include_closed': False
        }
        
        context = {}
        
        print(f"\n🔍 Executing tool with params: {params}")
        result = await tool.execute_func(params, context)
        
        print("\n" + "=" * 80)
        print("TOOL RESULT")
        print("=" * 80)
        
        print(f"\nSuccess: {result.get('success', False)}")
        print(f"Tool name: {result.get('tool_name', 'N/A')}")
        print(f"Calls found: {result.get('calls_found', 0)}")
        
        if result.get('error'):
            print(f"\n❌ Error: {result['error']}")
        
        if result.get('calls'):
            calls = result['calls']
            print(f"\n✅ Calls returned: {len(calls)}")
            print(f"\nFirst 3 calls:")
            for i, call in enumerate(calls[:3]):
                print(f"\n  {i+1}. {call.get('title', 'No title')}")
                print(f"     ID: {call.get('identifier', 'No ID')}")
                print(f"     Status: {call.get('status', 'Unknown')}")
                print(f"     Deadline: {call.get('deadline', 'Not specified')}")
                print(f"     URL: {call.get('url', 'No URL')}")
        else:
            print("\n⚠️ No 'calls' key in result")
            print(f"Result keys: {list(result.keys())}")
        
        # Now test through the unified classifier and tool orchestrator
        print("\n" + "=" * 80)
        print("Testing through Unified Classifier")
        print("=" * 80)
        
        from app.services.unified_intent_classifier import UnifiedIntentClassifier
        classifier = UnifiedIntentClassifier()
        
        question = "What are some open calls for energy?"
        print(f"\n📝 Question: '{question}'")
        
        print(f"\n🎯 Classifying intent...")
        unified_intent = await classifier.classify_intent(question, conversation_id=99999)
        
        print(f"\n✅ Intent classified:")
        print(f"  Primary intent: {unified_intent.primary_intent}")
        print(f"  Confidence: {unified_intent.confidence}")
        print(f"  Reasoning: {unified_intent.reasoning}")
        print(f"  Call keywords: {unified_intent.call_keywords}")
        print(f"  Tool plan: {unified_intent.tool_plan}")
        
        if unified_intent.tool_plan:
            print(f"\n🔧 Tool plan has {len(unified_intent.tool_plan)} tools:")
            for tp in unified_intent.tool_plan:
                if isinstance(tp, dict):
                    print(f"  - {tp.get('tool_name')}: {tp.get('parameters')}")
                else:
                    print(f"  - {tp.tool_name}: {tp.parameters}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tool_directly())

