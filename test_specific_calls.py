#!/usr/bin/env python3
"""
Test specific call queries and follow-up questions.
Tests the V3 API's conversation flow for call analysis.
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000/api/v3/conversation"


def send_message(conversation_id: int, message: str) -> dict:
    """Send a message and get the response."""
    url = f"{BASE_URL}/{conversation_id}/message"

    try:
        response = requests.post(
            url,
            json={"message": message, "include_context": True},
            timeout=120
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "response": data.get("response", ""),
                "metadata": data.get("metadata", {})
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:500]}"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_response_quality(response: str) -> list:
    """Check for common issues in responses."""
    issues = []

    # Check for raw data patterns
    raw_patterns = [
        ("{'documents':", "Raw JSON documents"),
        ('{"documents":', "Raw JSON documents"),
        ("'content':", "Raw dict fields"),
        ("search_specific_topic:", "Raw tool name"),
        ("search_documents:", "Raw tool name"),
        ("get_call_details:", "Raw tool name"),
        ("{'call_id': None", "Empty call details"),
    ]

    for pattern, issue in raw_patterns:
        if pattern in response:
            issues.append(issue)

    if len(response) < 50:
        issues.append("Response too short")

    return issues


def print_response(label: str, response: str, max_len: int = 500):
    """Print a response with truncation."""
    print(f"\n{label}:")
    print("-" * 40)
    if len(response) > max_len:
        print(response[:max_len] + "...")
    else:
        print(response)
    print("-" * 40)


def main():
    print("=" * 80)
    print("Specific Call Testing - Conversation Flow")
    print("=" * 80)

    conversation_id = int(time.time()) % 100000
    all_issues = []

    # Test 1: Search for calls and then ask about a specific one
    print("\n\n### TEST 1: Search and Follow-up ###")

    # Step 1: Search
    print("\nStep 1: Searching for hydrogen calls...")
    result = send_message(conversation_id, "Find open funding calls for hydrogen energy")
    if result["success"]:
        issues = check_response_quality(result["response"])
        if issues:
            print(f"  ⚠️ Issues: {issues}")
            all_issues.append(("Search hydrogen", issues))
        else:
            print(f"  ✅ Response OK ({len(result['response'])} chars)")
        print_response("Response", result["response"])
    else:
        print(f"  ❌ Failed: {result['error']}")
        all_issues.append(("Search hydrogen", [result["error"]]))

    time.sleep(2)

    # Step 2: Follow-up about first call
    print("\nStep 2: Asking about the first call...")
    result = send_message(conversation_id, "Tell me more about the first call. What are its eligibility requirements?")
    if result["success"]:
        issues = check_response_quality(result["response"])
        if issues:
            print(f"  ⚠️ Issues: {issues}")
            all_issues.append(("Follow-up first call", issues))
        else:
            print(f"  ✅ Response OK ({len(result['response'])} chars)")
        print_response("Response", result["response"])
    else:
        print(f"  ❌ Failed: {result['error']}")
        all_issues.append(("Follow-up first call", [result["error"]]))

    time.sleep(2)

    # Test 2: Direct specific questions
    print("\n\n### TEST 2: Direct Specific Questions ###")

    specific_questions = [
        "What is the deadline for HORIZON-CL5-2025-D3-01?",
        "What is the budget for Cluster 5 energy calls in 2025?",
        "List the expected outcomes for climate and energy calls",
    ]

    for q in specific_questions:
        print(f"\nQuestion: {q[:60]}...")
        result = send_message(conversation_id, q)
        if result["success"]:
            issues = check_response_quality(result["response"])
            if issues:
                print(f"  ⚠️ Issues: {issues}")
                all_issues.append((q[:40], issues))
            else:
                print(f"  ✅ Response OK ({len(result['response'])} chars)")
            print_response("Response", result["response"], 300)
        else:
            print(f"  ❌ Failed: {result['error']}")
            all_issues.append((q[:40], [result["error"]]))
        time.sleep(2)

    # Test 3: Complex questions requiring multiple sources
    print("\n\n### TEST 3: Complex Multi-Source Questions ###")

    complex_questions = [
        "Compare the eligibility requirements between RIA and IA action types",
        "What are the success rates for climate energy projects and what factors contribute to success?",
        "How should I structure a consortium for a Cluster 5 clean energy call?",
    ]

    for q in complex_questions:
        print(f"\nQuestion: {q[:60]}...")
        result = send_message(conversation_id, q)
        if result["success"]:
            issues = check_response_quality(result["response"])
            if issues:
                print(f"  ⚠️ Issues: {issues}")
                all_issues.append((q[:40], issues))
            else:
                print(f"  ✅ Response OK ({len(result['response'])} chars)")
            print_response("Response", result["response"], 400)
        else:
            print(f"  ❌ Failed: {result['error']}")
            all_issues.append((q[:40], [result["error"]]))
        time.sleep(2)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if all_issues:
        print(f"\n⚠️ Found {len(all_issues)} questions with issues:")
        for q, issues in all_issues:
            print(f"  - {q}: {issues}")
        return 1
    else:
        print("\n✅ All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
