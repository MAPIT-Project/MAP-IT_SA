#!/usr/bin/env python3
"""
Test script for EU Programme Call Assessment questions.
Tests the V3 API's ability to answer questions from the MAPIT assessment framework.
"""

import sys
import time

import requests

BASE_URL = "http://localhost:8000/api/v3/conversation"

# Test questions organized by category
TEST_QUESTIONS = {
    "General Call Identification": [
        "What are the open funding calls for clean energy research?",
        "Tell me about call HORIZON-CL5-2026-D3-01",
        "What types of actions are available (RIA, IA, CSA)?",
    ],
    "Budget and Funding": [
        "What is the typical EU contribution rate for RIA projects?",
        "Are there specific co-funding or in-kind contribution requirements for Horizon Europe?",
        "What are the budget limits per project for Innovation Actions?",
    ],
    "Consortium Composition and Eligibility": [
        "What is the minimum consortium composition required for Horizon Europe projects?",
        "Are there specific eligibility requirements regarding the type of organisations (HEIs, NGOs, SMEs, Research Institutes)?",
        "Can third-country participants join Horizon Europe projects?",
    ],
    "Thematic and Policy Alignment": [
        "What are the policy priorities addressed by Cluster 5 Climate calls?",
        "How does Horizon Europe align with the Green Deal?",
        "What are the cross-cutting priorities like open science and gender in Horizon Europe?",
    ],
    "Formal and Administrative Aspects": [
        "What is the typical TRL level required for Innovation Actions?",
        "What are the page limits for Horizon Europe proposals?",
        "What are the reporting requirements for Horizon Europe projects?",
    ],
}


def test_question(conversation_id: int, question: str) -> dict:
    """Send a question and get the response."""
    url = f"{BASE_URL}/{conversation_id}/message"

    try:
        response = requests.post(
            url,
            json={"message": question, "include_context": True},
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
                "error": f"HTTP {response.status_code}: {response.text[:200]}"
            }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def evaluate_response(question: str, response: str) -> dict:
    """Evaluate the quality of a response."""
    issues = []

    # Check for raw JSON/dict in response
    if "{'documents':" in response or '{"documents":' in response:
        issues.append("Contains raw JSON documents structure")
    if "{'calls':" in response or '{"calls":' in response:
        issues.append("Contains raw JSON calls structure")
    if "'content':" in response and "'source':" in response:
        issues.append("Contains raw document dict fields")

    # Check for incomplete formatting
    if "Based on my search:" in response and len(response) < 100:
        issues.append("Fallback response with minimal content")

    # Check for error messages
    if "error" in response.lower() and "no details found" in response.lower():
        issues.append("Error message in response")

    # Check response length
    if len(response) < 50:
        issues.append("Response too short")

    # Check for proper formatting (should have structure)
    has_structure = any([
        "**" in response,  # Bold text
        "•" in response or "- " in response,  # Bullet points
        "\n\n" in response,  # Paragraphs
    ])
    if not has_structure and len(response) > 200:
        issues.append("Missing formatting structure")

    return {
        "has_issues": len(issues) > 0,
        "issues": issues,
        "response_length": len(response)
    }


def main():
    print("=" * 80)
    print("EU Programme Call Assessment - Question Testing")
    print("=" * 80)

    conversation_id = int(time.time()) % 100000  # Random conversation ID
    results = {"passed": 0, "failed": 0, "issues": []}

    for category, questions in TEST_QUESTIONS.items():
        print(f"\n{'=' * 40}")
        print(f"Category: {category}")
        print("=" * 40)

        for i, question in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] Question: {question[:60]}...")

            # Get response
            result = test_question(conversation_id, question)

            if not result["success"]:
                print(f"  ❌ FAILED: {result.get('error', 'Unknown error')}")
                results["failed"] += 1
                results["issues"].append({
                    "category": category,
                    "question": question,
                    "error": result.get("error")
                })
                continue

            response = result["response"]

            # Evaluate response
            evaluation = evaluate_response(question, response)

            if evaluation["has_issues"]:
                print(f"  ⚠️ ISSUES: {', '.join(evaluation['issues'])}")
                results["failed"] += 1
                results["issues"].append({
                    "category": category,
                    "question": question,
                    "issues": evaluation["issues"],
                    "response_preview": response[:200] + "..." if len(response) > 200 else response
                })
            else:
                print(f"  ✅ PASSED (length: {evaluation['response_length']} chars)")
                results["passed"] += 1

            # Small delay between requests
            time.sleep(1)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")

    if results["issues"]:
        print(f"\nIssues found ({len(results['issues'])}):")
        for issue in results["issues"]:
            print(f"\n  Category: {issue['category']}")
            print(f"  Question: {issue['question'][:60]}...")
            if "error" in issue:
                print(f"  Error: {issue['error']}")
            if "issues" in issue:
                print(f"  Issues: {', '.join(issue['issues'])}")
            if "response_preview" in issue:
                print(f"  Response preview: {issue['response_preview'][:100]}...")

    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
