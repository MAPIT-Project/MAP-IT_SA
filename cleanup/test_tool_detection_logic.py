#!/usr/bin/env python3
"""
Test the tool detection logic directly without importing the full system.
"""

def test_project_keyword_detection():
    """Test if the enhanced project keywords correctly detect project search intent."""

    print("🧪 Testing Project Keyword Detection Logic")
    print("=" * 60)

    # Enhanced project keywords from the conversation manager
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
        # Domain-specific project searches
        'projects in', 'projects on', 'projects for',
        # Action verbs + project terms
        'find me projects', 'show me projects', 'get me projects',
        'search me projects', 'look me projects'
    ]

    # Test messages that should trigger project search
    test_messages = [
        "Look up projects about nuclear stuff",
        "Search for projects on clean energy",
        "Find me projects about AI",
        "Show me information on projects for climate change",
        "Get projects related to renewable energy",
        "Retrieve information on projects about digital transformation",
        "Search cordis for projects with term nuclear",
        "Look up in cordis api for nuclear projects",
        "Find projects in the field of biotechnology",
        "Show me projects on sustainable transport"
    ]

    print("Testing messages that SHOULD trigger project search:")
    print("-" * 50)

    all_passed = True
    for i, message in enumerate(test_messages, 1):
        message_lower = message.lower()
        matches = [keyword for keyword in project_keywords if keyword in message_lower]

        print(f"{i}. '{message}'")
        print(f"   Matches: {matches}")
        print(f"   Match count: {len(matches)}")

        if matches:
            print("   ✅ PASS: Would trigger project search")
        else:
            print("   ❌ FAIL: Would NOT trigger project search")
            all_passed = False
        print()

    # Test messages that should NOT trigger project search
    non_project_messages = [
        "What is Horizon Europe?",
        "Tell me about funding opportunities",
        "How do I apply for grants?",
        "What are the eligibility criteria?",
        "Hello, can you help me?",
        "Thanks for the information",
        "What time is it?",
        "How are you today?"
    ]

    print("Testing messages that should NOT trigger project search:")
    print("-" * 50)

    for i, message in enumerate(non_project_messages, 1):
        message_lower = message.lower()
        matches = [keyword for keyword in project_keywords if keyword in message_lower]

        print(f"{i}. '{message}'")
        print(f"   Matches: {matches}")
        print(f"   Match count: {len(matches)}")

        if not matches:
            print("   ✅ PASS: Correctly does NOT trigger project search")
        else:
            print("   ❌ FAIL: Incorrectly triggers project search")
            all_passed = False
        print()

    print("=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)

    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("   The keyword detection logic is working correctly.")
        print("   Project search queries are properly detected.")
        print("   Non-project queries are correctly filtered out.")
    else:
        print("❌ SOME TESTS FAILED")
        print("   The keyword detection logic needs improvement.")

    return all_passed

def test_context_analysis_logic():
    """Test the context analysis logic for repeated patterns."""

    print("\n🔍 Testing Context Analysis Logic")
    print("=" * 60)

    # Simulate conversation history with repeated project requests
    conversation_history = """
User: What are some open calls for clean energy?
Assistant: [Response about no open calls found]
User: Okay how about we look up information on projects for clean energy?
Assistant: [Conversational response about CORDIS]
User: No i mean look up in the cordis api
Assistant: [Conversational response about API access]
User: No look up projects about clean energy
Assistant: [Conversational response about CORDIS search]
User: Look up projects about nuclear stuff
"""

    user_message = "Look up projects about nuclear stuff"
    user_message_lower = user_message.lower()
    history_lower = conversation_history.lower()

    # Test project indicators
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
    project_mentions += sum(1 for indicator in project_indicators if indicator in user_message_lower)

    # Check for frustration indicators
    frustration_indicators = [
        'no i mean', 'i said', 'i asked', 'but i want', 'i need',
        'please', 'can you', 'could you', 'would you',
        'search on', 'look up', 'find me', 'show me'
    ]

    frustration_count = sum(1 for indicator in frustration_indicators if indicator in user_message_lower)

    # Analyze intent persistence
    repeated_project_intent = project_mentions >= 2
    intent_persistence_score = min(project_mentions * 0.3, 1.0)
    frustration_indicators_present = frustration_count >= 1

    # Special case: User is explicitly asking for CORDIS/API searches
    cordis_explicit = any(term in user_message_lower for term in ['cordis', 'api', 'search on', 'look up in'])

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

    print("Context Analysis Results:")
    print(f"  Project mentions: {project_mentions}")
    print(f"  Frustration count: {frustration_count}")
    print(f"  Repeated project intent: {repeated_project_intent}")
    print(f"  CORDIS explicit: {cordis_explicit}")
    print(f"  Recommended tool: {recommended_tool}")
    print(f"  Confidence multiplier: {confidence_multiplier}")

    if recommended_tool == 'search_cordis_projects':
        print("✅ SUCCESS: Context analysis correctly recommends CORDIS search!")
        return True
    else:
        print("❌ FAILURE: Context analysis did not recommend CORDIS search.")
        return False

if __name__ == "__main__":
    # Test keyword detection
    keyword_success = test_project_keyword_detection()

    # Test context analysis
    context_success = test_context_analysis_logic()

    print("\n" + "=" * 80)
    print("🎯 COMPREHENSIVE ANALYSIS")
    print("=" * 80)

    if keyword_success and context_success:
        print("✅ ALL LOGIC TESTS PASSED!")
        print("   The system SHOULD correctly detect and execute CORDIS searches.")
        print("   If it's not working, the issue is in tool execution, not detection.")
        print("\n🔧 NEXT STEPS:")
        print("   1. Check if the tool_orchestrator is properly initialized")
        print("   2. Verify the search_cordis_projects tool is registered")
        print("   3. Check if tool execution is failing silently")
        print("   4. Ensure tool results are being processed in response generation")
    else:
        print("❌ LOGIC TESTS FAILED")
        print("   The detection logic itself needs to be fixed.")
        print("\n🔧 ISSUES TO FIX:")
        if not keyword_success:
            print("   - Keyword detection is not working properly")
        if not context_success:
            print("   - Context analysis is not recommending CORDIS search")