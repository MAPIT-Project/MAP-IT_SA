#!/usr/bin/env python3
"""
Debug script to test the AI intent service directly
"""

import asyncio
import os
import sys

# Add the app directory to the path
sys.path.append('/home/anmar/Documents/VSCODE_REPOS/NEWMAPIT/MAP-IT_SA')

# Load environment variables from .env file if it exists
if os.path.exists('/home/anmar/Documents/VSCODE_REPOS/NEWMAPIT/MAP-IT_SA/.env'):
    from dotenv import load_dotenv
    load_dotenv('/home/anmar/Documents/VSCODE_REPOS/NEWMAPIT/MAP-IT_SA/.env')

from app.services.ai_intent_service import AIIntentService

async def debug_intent_service():
    """Debug the AI intent service with test queries"""

    # Set required environment variables
    if not os.getenv('GEMINI_API_KEY'):
        print("❌ GEMINI_API_KEY not set")
        return

    service = AIIntentService()

    test_queries = [
        "Hello, what can you help me with?",
        "What is Horizon Europe?",
        "Find open calls for AI research",
        "Show me renewable energy projects",
        "How do I apply for funding?"
    ]

    print("🔍 Debugging AI Intent Service")
    print("=" * 60)

    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}] Testing: '{query}'")
        print("-" * 40)

        try:
            analysis = await service.analyze_intent(query)

            print(f"✅ Intent: {analysis.intent_type}")
            print(f"✅ Confidence: {analysis.confidence}")
            print(f"✅ Requires Tools: {analysis.requires_tools}")
            print(f"✅ Tool Count: {len(analysis.tool_plan)}")
            print(f"✅ Processing Type: {analysis.processing_type}")
            print(f"✅ Keywords: {analysis.extracted_keywords}")

            if analysis.tool_plan:
                print("🔧 Tools Planned:")
                for tool in analysis.tool_plan:
                    print(f"   - {tool.tool_name}: {tool.parameters}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_intent_service())