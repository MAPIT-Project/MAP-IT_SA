#!/usr/bin/env python3
"""
Simple test of the context analysis logic improvements.
Tests the core logic without requiring complex dependencies.
"""

import json
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_conversation_context_for_intent(user_message: str,
                                          conversation_history: str,
                                          summary_text: str = "") -> dict:
    """
    Analyze conversation context for repeated patterns and intent persistence.
    This is the core logic from the improved conversation manager.
    """
    try:
        user_message_lower = user_message.lower()
        context_analysis = {
            'repeated_project_intent': False,
            'repeated_call_intent': False,
            'frustration_indicators': False,
            'intent_persistence_score': 0.0,
            'recommended_tool_boost': None,
            'confidence_multiplier': 1.0
        }

        # Analyze conversation history for repeated patterns
        history_lower = conversation_history.lower()

        # Check for repeated project search patterns
        project_indicators = [
            'look up projects', 'search projects', 'find projects',
            'show me projects', 'get projects', 'retrieve projects',
            'cordis api', 'cordis search', 'search cordis',
            'information on projects', 'data on projects', 'details about projects',
            'what projects', 'which projects', 'show me information on projects',
            'get information on projects', 'retrieve information on projects',
            'search for information on projects'
        ]

        # Count how many times project-related terms appear in recent history
        project_mentions = sum(1 for indicator in project_indicators if indicator in history_lower)
        project_mentions += sum(1 for indicator in project_indicators if indicator in user_message_lower)

        # Check for repeated call search patterns
        call_indicators = [
            'open calls', 'funding calls', 'call for proposals', 'grant calls',
            'submission deadline', 'funding opportunities', 'horizon calls',
            'eu calls', 'research calls', 'proposal calls'
        ]

        call_mentions = sum(1 for indicator in call_indicators if indicator in history_lower)
        call_mentions += sum(1 for indicator in call_indicators if indicator in user_message_lower)

        # Check for frustration indicators (user repeatedly asking for same thing)
        frustration_indicators = [
            'no i mean', 'i said', 'i asked', 'but i want', 'i need',
            'please', 'can you', 'could you', 'would you',
            'search on', 'look up', 'find me', 'show me'
        ]

        frustration_count = sum(1 for indicator in frustration_indicators if indicator in user_message_lower)

        # Analyze intent persistence
        if project_mentions >= 2:  # User mentioned projects multiple times
            context_analysis['repeated_project_intent'] = True
            context_analysis['intent_persistence_score'] = min(project_mentions * 0.3, 1.0)
            context_analysis['recommended_tool_boost'] = 'search_cordis_projects'
            context_analysis['confidence_multiplier'] = 1.5

        if call_mentions >= 2:  # User mentioned calls multiple times
            context_analysis['repeated_call_intent'] = True
            context_analysis['intent_persistence_score'] = min(call_mentions * 0.3, 1.0)
            context_analysis['recommended_tool_boost'] = 'eu_portal_search'
            context_analysis['confidence_multiplier'] = 1.5

        if frustration_count >= 1:  # User showing frustration
            context_analysis['frustration_indicators'] = True
            context_analysis['confidence_multiplier'] *= 1.2

        # Special case: User is explicitly asking for CORDIS/API searches
        if any(term in user_message_lower for term in ['cordis', 'api', 'search on', 'look up in']):
            context_analysis['confidence_multiplier'] = 2.0
            if 'project' in user_message_lower or any(term in history_lower for term in ['project', 'cordis']):
                context_analysis['recommended_tool_boost'] = 'search_cordis_projects'

        return context_analysis

    except Exception as e:
        logger.error(f"Error in context analysis: {e}")
        return {
            'repeated_project_intent': False,
            'repeated_call_intent': False,
            'frustration_indicators': False,
            'intent_persistence_score': 0.0,
            'recommended_tool_boost': None,
            'confidence_multiplier': 1.0
        }

def test_research_manager_questions():
    """Test the improved context analysis with realistic research manager questions."""

    print("🧪 Testing Context Analysis Logic")
    print("=" * 60)

    # Simulate conversation history from the user's frustrated experience
    conversation_history_template = """
User: What are some open calls for clean energy?
Assistant: [Response about no open calls found]
User: Okay how about we look up information on projects for clean energy?
Assistant: [Conversational response about CORDIS]
User: No i mean look up in the cordis api
Assistant: [Conversational response about API access]
User: No look up projects about clean energy
Assistant: [Conversational response about CORDIS search]
"""

    # Realistic research manager questions
    test_cases = [
        {
            'message': 'What are some open calls for clean energy?',
            'expected_tool': 'eu_portal_search',
            'description': 'Initial call search'
        },
        {
            'message': 'Okay how about we look up information on projects for clean energy?',
            'expected_tool': 'search_cordis_projects',
            'description': 'First project search attempt'
        },
        {
            'message': 'No i mean look up in the cordis api',
            'expected_tool': 'search_cordis_projects',
            'description': 'Frustrated project search with CORDIS mention'
        },
        {
            'message': 'No look up projects about clean energy',
            'expected_tool': 'search_cordis_projects',
            'description': 'Direct project search request'
        },
        {
            'message': 'SEARCH ON CORDIS FOR PROJECTS WITH THE TERM CLEAN ENERGY',
            'expected_tool': 'search_cordis_projects',
            'description': 'Explicit CORDIS search command'
        },
        {
            'message': 'Can you find me projects on renewable energy from the last 3 years?',
            'expected_tool': 'search_cordis_projects',
            'description': 'Specific project search'
        },
        {
            'message': 'Show me successful AI projects funded by Horizon Europe',
            'expected_tool': 'search_cordis_projects',
            'description': 'AI projects search'
        },
        {
            'message': 'What are some completed projects in biotechnology?',
            'expected_tool': 'search_cordis_projects',
            'description': 'Biotechnology projects'
        },
        {
            'message': 'Find projects related to climate change adaptation',
            'expected_tool': 'search_cordis_projects',
            'description': 'Climate change projects'
        },
        {
            'message': 'Show me projects that received funding over 5 million euros',
            'expected_tool': 'search_cordis_projects',
            'description': 'High funding projects'
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['description']}")
        print(f"   Message: '{test_case['message']}'")

        # Use conversation history up to this point
        history_up_to_now = conversation_history_template
        if i > 1:
            # Add previous messages to history
            history_up_to_now = "\n".join([
                f"User: {tc['message']}\nAssistant: [Previous response]"
                for tc in test_cases[:i-1]
            ]) + "\n" + conversation_history_template

        # Analyze context
        analysis = analyze_conversation_context_for_intent(
            test_case['message'],
            history_up_to_now,
            "Conversation about clean energy funding and projects"
        )

        print(f"   Context Analysis: {json.dumps(analysis, indent=2)}")

        # Check if analysis correctly identifies intent
        recommended_tool = analysis.get('recommended_tool_boost')
        confidence_multiplier = analysis.get('confidence_multiplier', 1.0)

        success = recommended_tool == test_case['expected_tool']
        status = "✅ SUCCESS" if success else "❌ FAILED"

        print(f"   Result: {status}")
        print(f"   Confidence Multiplier: {confidence_multiplier:.1f}")
        print(f"   Expected: {test_case['expected_tool']}")
        print(f"   Got: {recommended_tool}")

        results.append({
            'test_case': test_case,
            'analysis': analysis,
            'success': success
        })

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    successful_tests = sum(1 for r in results if r['success'])
    total_tests = len(results)

    print(f"Total Tests: {total_tests}")
    print(f"Successful Tests: {successful_tests}")
    print(f"Success Rate: {successful_tests/total_tests*100:.1f}%")
    # Analyze failures
    failures = [r for r in results if not r['success']]
    if failures:
        print(f"\n❌ FAILED TESTS ({len(failures)}):")
        for failure in failures:
            test_case = failure['test_case']
            analysis = failure['analysis']
            print(f"   - '{test_case['message']}'")
            print(f"     Expected: {test_case['expected_tool']}")
            print(f"     Got: {analysis.get('recommended_tool_boost')}")
    else:
        print("\n✅ ALL TESTS PASSED!")

    # Performance analysis
    print("\n🔍 PERFORMANCE ANALYSIS:")
    print("-" * 40)

    cordis_triggers = sum(1 for r in results if r['analysis'].get('recommended_tool_boost') == 'search_cordis_projects')
    call_triggers = sum(1 for r in results if r['analysis'].get('recommended_tool_boost') == 'eu_portal_search')

    print(f"CORDIS project searches triggered: {cordis_triggers}/{total_tests}")
    print(f"EU call searches triggered: {call_triggers}/{total_tests}")

    high_confidence = sum(1 for r in results if r['analysis'].get('confidence_multiplier', 1.0) > 1.5)
    print(f"High confidence detections: {high_confidence}/{total_tests}")

    return results

if __name__ == "__main__":
    test_research_manager_questions()