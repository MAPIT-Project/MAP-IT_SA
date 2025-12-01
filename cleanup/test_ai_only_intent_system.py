#!/usr/bin/env python3
"""
Test script for the new AI-only intent system.
Tests that the system works without keyword detection, pattern matching, or regex.
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ai_intent_service import AIIntentService

async def test_ai_only_intent_system():
    """Test the AI-only intent system with various queries."""
    print("🧪 Testing AI-Only Intent System")
    print("=" * 60)

    try:
        # Initialize the service
        service = AIIntentService()

        # Test queries that should be classified differently
        test_queries = [
            # Should be search_calls
            "What are the open calls for renewable energy?",
            "Show me funding opportunities in AI",
            "Are there any grants for clean technology?",

            # Should be search_projects
            "Can you show me projects about renewable energy?",
            "What research has been done on climate change?",
            "Find examples of successful Horizon Europe projects",

            # Should be conversational
            "Hello, how can you help me?",
            "How do I apply for funding?",
            "Can you explain the process?",
            "What documents do I need?",
            "Tell me more about that",

            # Edge cases
            "Can you tell me about renewable energy projects?",
            "I want to find projects and also know about funding",
            "Help me understand both projects and calls"
        ]

        print(f"Testing {len(test_queries)} queries...\n")

        for i, query in enumerate(test_queries, 1):
            print(f"{i:2d}. Query: '{query}'")
            print("-" * 50)

            try:
                analysis = await service.analyze_intent(query)

                print(f"   Intent: {analysis.intent_type}")
                print(f"   Confidence: {analysis.confidence:.2f}")
                print(f"   Requires Tools: {analysis.requires_tools}")
                print(f"   Processing Type: {analysis.processing_type}")
                print(f"   Tools Planned: {len(analysis.tool_plan)}")

                if analysis.tool_plan:
                    for j, tool in enumerate(analysis.tool_plan):
                        print(f"     Tool {j+1}: {tool.tool_name}")
                        print(f"     Reason: {tool.reason}")

                print(f"   Reasoning: {analysis.reasoning}")
                print(f"   Context: {analysis.context_assessment}")

            except Exception as e:
                print(f"   ❌ Error: {e}")

            print()

        print("✅ AI-Only Intent System test completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_only_intent_system())