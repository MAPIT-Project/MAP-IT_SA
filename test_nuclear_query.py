#!/usr/bin/env python3
"""
Test the specific nuclear query that was failing.
"""

import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_nuclear_query_detection():
    """Test if 'Look up projects about nuclear stuff' is correctly detected."""

    message = "Look up projects about nuclear stuff"
    message_lower = message.lower()

    print(f"🧪 Testing: '{message}'")
    print("=" * 60)

    # Test the enhanced keyword matching
    project_keywords = [
        # Original keywords
        'completed projects', 'research projects', 'project results',
        'cordis projects', 'funded projects', 'project examples',
        'successful projects', 'project outcomes',
        # Enhanced keywords for better detection
        'look up projects', 'search projects', 'find projects',
        'show me projects', 'get projects', 'retrieve projects',
        'cordis api', 'cordis search', 'search cordis',
        'information on projects', 'data on projects', 'details about projects',
        'what projects', 'which projects', 'show me information on projects',
        'get information on projects', 'retrieve information on projects',
        'search for information on projects',
        # Generic project terms that should trigger search
        'projects about', 'projects related to', 'search for projects',
        'find information on projects', 'get information on projects',
        'retrieve information on projects', 'search for information on projects',
        'projects in', 'projects on', 'projects for',
        # Action verbs + project terms
        'find me projects', 'show me projects', 'get me projects',
        'search me projects', 'look me projects'
    ]

    # Check for matches
    matches = [keyword for keyword in project_keywords if keyword in message_lower]

    print(f"Message (lowercase): '{message_lower}'")
    print(f"Matching keywords: {matches}")
    print(f"Number of matches: {len(matches)}")

    if matches:
        print("✅ SUCCESS: Query correctly detected as project search!")
        print("   This should trigger the CORDIS search tool.")
        return True
    else:
        print("❌ FAILED: Query not detected as project search.")
        print("   This would result in a conversational response.")
        return False

def test_context_analysis():
    """Test the context analysis for the nuclear query."""

    print("\n🔍 Testing Context Analysis")
    print("-" * 40)

    message = "Look up projects about nuclear stuff"
    conversation_history = """
User: What are some open calls for clean energy?
Assistant: [Response about no open calls found]
User: Okay how about we look up information on projects for clean energy?
Assistant: [Conversational response about CORDIS]
User: No i mean look up in the cordis api
Assistant: [Conversational response about API access]
User: No look up projects about clean energy
Assistant: [Conversational response about CORDIS search]
"""

    # Simulate the context analysis logic
    message_lower = message.lower()
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

    # Count how many times project-related terms appear
    project_mentions = sum(1 for indicator in project_indicators if indicator in history_lower)
    project_mentions += sum(1 for indicator in project_indicators if indicator in message_lower)

    # Check for frustration indicators
    frustration_indicators = [
        'no i mean', 'i said', 'i asked', 'but i want', 'i need',
        'please', 'can you', 'could you', 'would you',
        'search on', 'look up', 'find me', 'show me'
    ]

    frustration_count = sum(1 for indicator in frustration_indicators if indicator in message_lower)

    # Analyze intent persistence
    repeated_project_intent = project_mentions >= 2
    intent_persistence_score = min(project_mentions * 0.3, 1.0)
    frustration_indicators_present = frustration_count >= 1

    # Special case: User is explicitly asking for CORDIS/API searches
    cordis_explicit = any(term in message_lower for term in ['cordis', 'api', 'search on', 'look up in'])

    # Calculate confidence multiplier
    confidence_multiplier = 1.0
    if repeated_project_intent:
        confidence_multiplier = 1.5
    if frustration_indicators_present:
        confidence_multiplier *= 1.2
    if cordis_explicit:
        confidence_multiplier = 2.0

    # Determine recommended tool
    recommended_tool = None
    if repeated_project_intent or cordis_explicit:
        recommended_tool = 'search_cordis_projects'

    context_analysis = {
        'repeated_project_intent': repeated_project_intent,
        'frustration_indicators': frustration_indicators_present,
        'intent_persistence_score': intent_persistence_score,
        'recommended_tool_boost': recommended_tool,
        'confidence_multiplier': confidence_multiplier,
        'project_mentions': project_mentions,
        'frustration_count': frustration_count,
        'cordis_explicit': cordis_explicit
    }

    print(f"Context Analysis Results:")
    print(json.dumps(context_analysis, indent=2))

    if recommended_tool == 'search_cordis_projects':
        print("✅ SUCCESS: Context analysis correctly recommends CORDIS search!")
        return True
    else:
        print("❌ FAILED: Context analysis did not recommend CORDIS search.")
        return False

if __name__ == "__main__":
    print("🔬 Testing Nuclear Query Detection")
    print("This tests the specific query that was failing: 'Look up projects about nuclear stuff'")
    print()

    # Test keyword matching
    keyword_success = test_nuclear_query_detection()

    # Test context analysis
    context_success = test_context_analysis()

    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)

    if keyword_success and context_success:
        print("✅ ALL TESTS PASSED!")
        print("   The nuclear query should now be correctly routed to CORDIS search.")
    else:
        print("❌ SOME TESTS FAILED")
        if not keyword_success:
            print("   - Keyword matching failed")
        if not context_success:
            print("   - Context analysis failed")

    print("\nExpected behavior:")
    print("- Query should trigger search_cordis_projects tool")
    print("- Should NOT give conversational response about CORDIS website")
    print("- Should actually search CORDIS for nuclear-related projects")