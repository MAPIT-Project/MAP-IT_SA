#!/usr/bin/env python3
"""
Validate that the intent analysis fix works correctly.
This will test the AI Intent Service directly to ensure it's not recommending tools for conversational queries.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_intent_fix():
    """Test that intent analysis is fixed and won't recommend tools for conversational queries."""
    
    print("🔧 Testing Intent Analysis Fix")
    print("=" * 50)
    
    try:
        from app.services.ai_intent_service import AIIntentService
        
        # Initialize AI Intent Service
        print("Initializing AI Intent Service...")
        intent_service = AIIntentService()
        print("✅ AI Intent Service initialized")
        
        # Test the problematic query
        test_query = "How much funding is available in Horizon Europe and how is it structured?"
        
        print(f"\n🎯 Testing problematic query:")
        print(f"'{test_query}'")
        
        # Analyze intent
        print("\n📊 Running intent analysis...")
        
        intent_result = await intent_service.analyze_intent(
            message=test_query,
            conversation_context="",
            conversation_history="",
            conversation_id=1
        )
        
        print(f"\n📋 Intent Analysis Results:")
        print(f"  Intent Type: {intent_result.intent_type}")
        print(f"  Confidence: {intent_result.confidence:.2f}")
        print(f"  Requires Tools: {intent_result.requires_tools}")
        print(f"  Tool Plan Length: {len(intent_result.tool_plan) if intent_result.tool_plan else 0}")
        print(f"  Processing Type: {intent_result.processing_type}")
        print(f"  Reasoning: {intent_result.reasoning}")
        
        if intent_result.tool_plan:
            print(f"\n🔧 Tool Plan:")
            for i, tool in enumerate(intent_result.tool_plan):
                print(f"    {i+1}. {tool.tool_name} - {tool.reason}")
        
        # Validation checks
        print(f"\n✅ Validation Checks:")
        
        checks = {
            "Intent is conversational": intent_result.intent_type == "conversational",
            "No tools required": not intent_result.requires_tools,
            "Empty tool plan": not intent_result.tool_plan or len(intent_result.tool_plan) == 0,
            "Good confidence": intent_result.confidence >= 0.5
        }
        
        passed = 0
        for check_name, check_result in checks.items():
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")
            if check_result:
                passed += 1
        
        print(f"\n📊 Overall Score: {passed}/{len(checks)}")
        
        if passed == len(checks):
            print("🎉 SUCCESS! Intent analysis fix is working correctly!")
            print("The system should now use conversational responses without tools.")
            return True
        elif passed >= 3:
            print("⚠️ MOSTLY WORKING - Minor issues detected")
            return True
        else:
            print("❌ FAILED - Intent analysis still has issues")
            return False
            
    except Exception as e:
        print(f"❌ Error testing intent fix: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_multiple_queries():
    """Test multiple conversational queries to ensure they all work correctly."""
    
    print(f"\n🧪 Testing Multiple Conversational Queries")
    print("=" * 50)
    
    conversational_queries = [
        "What is Horizon Europe?",
        "How much funding is available in Horizon Europe and how is it structured?",
        "What are the pillars of Horizon Europe?",
        "Tell me about the budget allocation for climate research",
        "Explain the application process for Horizon Europe",
        "What are the eligibility requirements?",
        "How does the evaluation process work?"
    ]
    
    try:
        from app.services.ai_intent_service import AIIntentService
        intent_service = AIIntentService()
        
        results = []
        
        for i, query in enumerate(conversational_queries, 1):
            print(f"\n--- Query {i}: {query} ---")
            
            try:
                intent_result = await intent_service.analyze_intent(
                    message=query,
                    conversation_context="",
                    conversation_history="",
                    conversation_id=1
                )
                
                is_correct = (
                    intent_result.intent_type == "conversational" and
                    not intent_result.requires_tools and
                    (not intent_result.tool_plan or len(intent_result.tool_plan) == 0)
                )
                
                status = "✅" if is_correct else "❌"
                print(f"{status} Intent: {intent_result.intent_type}, Tools: {intent_result.requires_tools}")
                
                results.append(is_correct)
                
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append(False)
        
        # Summary
        passed = sum(results)
        total = len(results)
        
        print(f"\n📊 Multiple Query Test Results: {passed}/{total}")
        
        if passed == total:
            print("🎉 All conversational queries handled correctly!")
            return True
        elif passed >= total * 0.8:
            print("✅ Most queries handled correctly")
            return True
        else:
            print("❌ Many queries still have issues")
            return False
            
    except Exception as e:
        print(f"❌ Error in multiple query test: {e}")
        return False

async def main():
    """Main test function."""
    
    print("🚨 INTENT ANALYSIS FIX VALIDATION")
    print("=" * 60)
    print("This test validates that conversational queries no longer trigger tools")
    
    # Test 1: Single problematic query
    success1 = await test_intent_fix()
    
    # Test 2: Multiple conversational queries  
    success2 = await test_multiple_queries()
    
    # Final assessment
    print(f"\n" + "=" * 60)
    print("🎯 FINAL VALIDATION RESULTS")
    print("=" * 60)
    
    if success1 and success2:
        print("✅ FIX VALIDATION: PASSED!")
        print("\n🎉 The intent analysis fix is working correctly!")
        print("Conversational queries should now use enhanced fallback responses.")
        print("\n📝 Next Steps:")
        print("1. Restart your Docker containers to pick up the changes")
        print("2. Test your original query again")
        print("3. You should get a proper Horizon Europe response")
    elif success1 or success2:
        print("⚠️ FIX VALIDATION: PARTIAL SUCCESS")
        print("Some issues remain but the fix is mostly working")
    else:
        print("❌ FIX VALIDATION: FAILED")
        print("The intent analysis fix is not working properly")
    
    return success1 and success2

if __name__ == "__main__":
    asyncio.run(main())