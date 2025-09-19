#!/usr/bin/env python3
"""
Test script for the enhanced conversational query system with database search.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ai_intent_service import AIIntentService
from app.services.tools.tool_orchestrator import create_research_orchestrator

async def test_conversational_database_search():
    """Test that conversational queries now use database search tool."""

    print("🧪 Testing Enhanced Conversational Query System")
    print("=" * 60)

    # Initialize services
    try:
        intent_service = AIIntentService()
        orchestrator = create_research_orchestrator()
        print("✅ Services initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        return False

    # Test queries that should trigger conversational intent with database search
    test_queries = [
        "How do I apply for Horizon Europe funding?",
        "What are the eligibility requirements?",
        "Can you explain the evaluation process?",
        "What documents do I need to submit?",
        "How does the funding system work?",
        "Hello, can you help me understand the application process?",
        "Tell me more about proposal requirements",
        "What are the key steps for submitting a proposal?"
    ]

    print(f"\n📋 Testing {len(test_queries)} conversational queries:")
    print("-" * 60)

    success_count = 0

    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        print("-" * 40)

        try:
            # Analyze intent
            analysis = await intent_service.analyze_intent(query)

            print(f"   Intent: {analysis.intent_type}")
            print(f"   Confidence: {analysis.confidence:.2f}")
            print(f"   Requires Tools: {analysis.requires_tools}")
            print(f"   Processing Type: {analysis.processing_type}")

            # Check if conversational queries now use tools
            if analysis.intent_type == "conversational":
                if analysis.requires_tools and len(analysis.tool_plan) > 0:
                    tool = analysis.tool_plan[0]
                    print(f"   Tool Used: {tool.tool_name}")
                    print(f"   Tool Parameters: {tool.parameters}")
                    print(f"   Tool Reason: {tool.reason}")
                    print("   ✅ SUCCESS: Conversational query now uses database search tool")

                    # Verify the tool is available in orchestrator
                    available_tools = orchestrator.get_available_tools()
                    tool_names = [t['name'] for t in available_tools]
                    if tool.tool_name in tool_names:
                        print(f"   ✅ Tool '{tool.tool_name}' is registered in orchestrator")
                        success_count += 1
                    else:
                        print(f"   ❌ Tool '{tool.tool_name}' not found in orchestrator")
                else:
                    print("   ❌ FAILED: Conversational query doesn't use tools")
            else:
                print(f"   ⚠️  WARNING: Query classified as {analysis.intent_type}, not conversational")

        except Exception as e:
            print(f"   ❌ ERROR: {e}")

    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"   Total queries tested: {len(test_queries)}")
    print(f"   Successful conversational queries with tools: {success_count}")
    print(f"   Success rate: {success_count/len(test_queries)*100:.1f}%")

    if success_count == len(test_queries):
        print("   🎉 ALL TESTS PASSED!")
        return True
    else:
        print("   ⚠️  SOME TESTS FAILED")
        return False

async def test_tool_orchestrator():
    """Test that the new tool is properly registered."""

    print("\n🔧 Testing Tool Orchestrator Registration")
    print("=" * 60)

    try:
        orchestrator = create_research_orchestrator()
        available_tools = orchestrator.get_available_tools()

        print(f"✅ Found {len(available_tools)} registered tools")

        # Check for our new tool
        database_tool = None
        for tool in available_tools:
            if tool['name'] == 'search_local_database':
                database_tool = tool
                break

        if database_tool:
            print("✅ 'search_local_database' tool found:")
            print(f"   Description: {database_tool['description']}")
            print(f"   Category: {database_tool['category']}")
            print(f"   Tags: {database_tool['tags']}")
            print(f"   Parameters: {list(database_tool['parameters'].keys())}")
            print("   ✅ Tool registration successful!")
            return True
        else:
            print("❌ 'search_local_database' tool not found in registered tools")
            print("Available tools:")
            for tool in available_tools:
                print(f"  - {tool['name']}: {tool['description']}")
            return False

    except Exception as e:
        print(f"❌ Tool orchestrator test failed: {e}")
        return False

async def main():
    """Run all tests."""

    print("🚀 Starting Enhanced Conversational Query System Tests")
    print("=" * 60)

    # Test tool registration
    tool_test_passed = await test_tool_orchestrator()

    # Test conversational queries
    conversational_test_passed = await test_conversational_database_search()

    print("\n" + "=" * 60)
    print("📋 FINAL RESULTS:")
    print(f"   Tool Registration: {'✅ PASSED' if tool_test_passed else '❌ FAILED'}")
    print(f"   Conversational Queries: {'✅ PASSED' if conversational_test_passed else '❌ FAILED'}")

    if tool_test_passed and conversational_test_passed:
        print("   🎉 ALL TESTS PASSED - Enhanced system is working!")
        return True
    else:
        print("   ❌ SOME TESTS FAILED - Please check the implementation")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)