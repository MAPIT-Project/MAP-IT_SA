#!/usr/bin/env python3
"""
Test script for the improved AI-only intent service.
Tests various query types to ensure proper intent classification and tool planning.
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.ai_intent_service import AIIntentService

async def test_ai_intent_service():
    """Test the AI intent service with various query types."""

    print("🧪 Testing AI-Only Intent Service")
    print("=" * 50)

    # Initialize the service
    try:
        service = AIIntentService()
        print("✅ AI Intent Service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize AI Intent Service: {e}")
        return

    # Test cases with expected outcomes
    test_cases = [
        {
            "name": "Funding Call Query",
            "message": "What are some open calls for clean energy research?",
            "expected_intent": "search_calls",
            "expected_tools": ["eu_portal_search"]
        },
        {
            "name": "Project Search Query",
            "message": "Show me projects about AI in healthcare",
            "expected_intent": "search_projects",
            "expected_tools": ["search_cordis_projects"]
        },
        {
            "name": "Conversational Query",
            "message": "Hello, how can you help me with EU funding?",
            "expected_intent": "conversational",
            "expected_tools": []
        },
        {
            "name": "FAQ Query",
            "message": "How do I apply for Horizon Europe funding?",
            "expected_intent": "conversational",
            "expected_tools": []
        },
        {
            "name": "Clarification Query",
            "message": "Can you explain that in more detail?",
            "expected_intent": "conversational",
            "expected_tools": []
        },
        {
            "name": "Complex Query",
            "message": "I want to find both open calls and existing projects about renewable energy",
            "expected_intent": "search_calls",  # Should prioritize calls
            "expected_tools": ["eu_portal_search"]
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Query: {test_case['message']}")

        try:
            # Analyze intent
            analysis = await service.analyze_intent(
                message=test_case['message'],
                conversation_context="New conversation",
                conversation_history=""
            )

            print(f"   Intent: {analysis.intent_type}")
            print(f"   Confidence: {analysis.confidence:.2f}")
            print(f"   Requires Tools: {analysis.requires_tools}")
            print(f"   Processing Type: {analysis.processing_type}")
            print(f"   Tools Planned: {len(analysis.tool_plan)}")

            if analysis.tool_plan:
                for tool in analysis.tool_plan:
                    print(f"     - {tool.tool_name}: {tool.reason}")

            # Validate results
            success = True
            issues = []

            if analysis.intent_type != test_case['expected_intent']:
                success = False
                issues.append(f"Expected intent {test_case['expected_intent']}, got {analysis.intent_type}")

            if analysis.confidence < 0.5:
                success = False
                issues.append(f"Low confidence: {analysis.confidence:.2f}")

            # Check tool planning
            expected_tools = test_case['expected_tools']
            actual_tools = [tool.tool_name for tool in analysis.tool_plan]

            if set(expected_tools) != set(actual_tools):
                success = False
                issues.append(f"Expected tools {expected_tools}, got {actual_tools}")

            if success:
                print("   ✅ PASS")
            else:
                print(f"   ❌ FAIL: {'; '.join(issues)}")

            results.append({
                "test_case": test_case['name'],
                "success": success,
                "intent": analysis.intent_type,
                "confidence": analysis.confidence,
                "tools": actual_tools,
                "issues": issues
            })

        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append({
                "test_case": test_case['name'],
                "success": False,
                "error": str(e)
            })

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])

    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")

    if passed_tests == total_tests:
        print("🎉 All tests passed! AI-only intent system is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the results above for details.")

        # Show failed tests
        print("\nFailed Tests:")
        for result in results:
            if not result['success']:
                print(f"  - {result['test_case']}: {'; '.join(result.get('issues', ['Unknown error']))}")

    # Show intent distribution
    print("\nIntent Distribution:")
    intent_counts = {}
    for result in results:
        if result['success']:
            intent = result['intent']
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

    for intent, count in intent_counts.items():
        print(f"  - {intent}: {count} queries")

    return passed_tests == total_tests

if __name__ == "__main__":
    success = asyncio.run(test_ai_intent_service())
    sys.exit(0 if success else 1)