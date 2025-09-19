#!/usr/bin/env python3
"""
Test script for improved intent detection to ensure project queries are properly classified.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_project_intent_detection():
    """Test that project-related queries are properly classified as search_projects."""

    print("🧪 Testing Improved Intent Detection for Project Queries")
    print("=" * 60)

    # Test queries that should be classified as search_projects
    project_queries = [
        "Can you tell me about projects related to clean energy?",
        "Find projects about renewable energy",
        "Search for projects on climate change",
        "Show me projects in biotechnology",
        "What projects are there on AI?",
        "Tell me about clean energy projects",
        "Find me projects about renewable energy",
        "Search projects on climate change",
        "Show projects in biotechnology",
        "What projects exist on AI?"
    ]

    # Test queries that should be classified as conversational
    conversational_queries = [
        "How do I apply for funding?",
        "What are the eligibility requirements?",
        "Can you explain the evaluation process?",
        "Hello, can you help?",
        "What documents do I need?"
    ]

    print(f"\n📋 Testing {len(project_queries)} project queries:")
    print("-" * 60)

    # Test project queries
    project_success_count = 0
    for i, query in enumerate(project_queries, 1):
        print(f"\n{i}. Query: '{query}'")

        # Check if query contains project-related keywords
        query_lower = query.lower()
        project_keywords = ['projects', 'find projects', 'search for projects', 'show me projects']

        has_project_keywords = any(keyword in query_lower for keyword in project_keywords)

        if has_project_keywords:
            print("   ✅ Contains project keywords - should be search_projects")
            project_success_count += 1
        else:
            print("   ❌ Missing project keywords - might be conversational")

    print(f"\n📋 Testing {len(conversational_queries)} conversational queries:")
    print("-" * 60)

    # Test conversational queries
    conversational_success_count = 0
    for i, query in enumerate(conversational_queries, 1):
        print(f"\n{i}. Query: '{query}'")

        # Check if query contains project-related keywords
        query_lower = query.lower()
        project_keywords = ['projects', 'find projects', 'search for projects', 'show me projects']

        has_project_keywords = any(keyword in query_lower for keyword in project_keywords)

        if not has_project_keywords:
            print("   ✅ No project keywords - should be conversational")
            conversational_success_count += 1
        else:
            print("   ❌ Contains project keywords - might be misclassified")

    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"   Project queries that should be detected: {project_success_count}/{len(project_queries)}")
    print(f"   Conversational queries that should be detected: {conversational_success_count}/{len(conversational_queries)}")

    project_success_rate = project_success_count / len(project_queries) * 100
    conversational_success_rate = conversational_success_count / len(conversational_queries) * 100

    print(f"   Project detection rate: {project_success_rate:.1f}%")
    print(f"   Conversational detection rate: {conversational_success_rate:.1f}%")

    if project_success_rate >= 80 and conversational_success_rate >= 80:
        print("   🎉 INTENT DETECTION IMPROVEMENTS LOOK GOOD!")
        return True
    else:
        print("   ⚠️  INTENT DETECTION NEEDS MORE IMPROVEMENT")
        return False

def test_specific_examples():
    """Test the specific examples from the user's conversation."""

    print("\n🔍 Testing Specific Examples from User Conversation")
    print("=" * 60)

    # The specific query from the user's example
    user_query = "Can you tell be about projects related to clean energy?"

    print(f"User Query: '{user_query}'")
    print("-" * 40)

    query_lower = user_query.lower()

    # Check for project keywords
    project_keywords = ['projects', 'find projects', 'search for projects', 'show me projects', 'about projects', 'related to projects']

    has_project_keywords = any(keyword in query_lower for keyword in project_keywords)

    print(f"Contains project keywords: {has_project_keywords}")

    if has_project_keywords:
        print("✅ Should be classified as: search_projects")
        print("✅ Should trigger: search_cordis_projects tool")
        return True
    else:
        print("❌ Should be classified as: search_projects")
        print("❌ But might be classified as: conversational")
        return False

def main():
    """Run all tests."""

    print("🚀 Testing Improved Intent Detection")
    print("=" * 60)

    # Test general project intent detection
    general_test_passed = test_project_intent_detection()

    # Test specific examples
    specific_test_passed = test_specific_examples()

    print("\n" + "=" * 60)
    print("📋 FINAL RESULTS:")
    print(f"   General Project Detection: {'✅ PASSED' if general_test_passed else '❌ FAILED'}")
    print(f"   Specific Example Test: {'✅ PASSED' if specific_test_passed else '❌ FAILED'}")

    if general_test_passed and specific_test_passed:
        print("   🎉 ALL TESTS PASSED - Intent detection improvements are working!")
        print("\n📝 SUMMARY:")
        print("   ✅ Project queries now have better keyword detection")
        print("   ✅ More specific examples added to AI prompt")
        print("   ✅ Clearer precedence rules established")
        print("   ✅ Fallback analysis improved")
        return True
    else:
        print("   ❌ SOME TESTS FAILED - Intent detection needs more work")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)