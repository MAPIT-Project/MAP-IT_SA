"""
Test script to debug the keyword extraction issue where "funding" is being added inappropriately.
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ai_intent_service import AIIntentService

async def test_keyword_extraction():
    """Test what keywords are being extracted for different queries."""
    
    service = AIIntentService()
    
    test_queries = [
        "what are some calls about clothes?",
        "find calls for clothing research",
        "search for textile funding",
        "what are open calls about fashion",
        "show me calls about clean energy"
    ]
    
    print("🧪 Testing AI Keyword Extraction")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        
        try:
            analysis = await service.analyze_intent(query)
            
            print(f"   Intent: {analysis.intent_type}")
            print(f"   Confidence: {analysis.confidence:.2f}")
            print(f"   Extracted Keywords: {analysis.extracted_keywords}")
            print(f"   Reasoning: {analysis.reasoning[:200]}...")
            
            # Check if "funding" is inappropriately included
            if analysis.extracted_keywords and "funding" in analysis.extracted_keywords:
                print("   ⚠️  ISSUE: 'funding' was inappropriately extracted as a keyword!")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

async def test_specific_clothes_query():
    """Test the specific clothes query that's causing issues."""
    
    service = AIIntentService()
    
    query = "what are some calls about clothes?"
    print(f"\n🔍 Testing specific query: '{query}'")
    
    try:
        analysis = await service.analyze_intent(query)
        
        print(f"   Intent: {analysis.intent_type}")
        print(f"   Confidence: {analysis.confidence:.2f}")
        print(f"   Extracted Keywords: {analysis.extracted_keywords}")
        print(f"   Reasoning: {analysis.reasoning}")
        
        # Check the tool plan
        if analysis.tool_plan:
            for tool in analysis.tool_plan:
                print(f"   Tool: {tool.tool_name}")
                print(f"   Parameters: {tool.parameters}")
        
        # Check if "funding" is inappropriately included
        if analysis.extracted_keywords and "funding" in analysis.extracted_keywords:
            print("   ⚠️  ISSUE: 'funding' was inappropriately extracted as a keyword!")
            print("   This will cause the search to look for 'clothes OR funding' instead of just 'clothes'")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("🔧 Testing AI Keyword Extraction Issue")
    print("This test will show what keywords are being extracted for different queries.")
    print("The issue is that 'funding' is being added when it shouldn't be.\n")
    
    asyncio.run(test_keyword_extraction())
    asyncio.run(test_specific_clothes_query())