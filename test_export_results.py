#!/usr/bin/env python3
"""
Export test results with questions and answers to a file for analysis.
"""

import json
import sys
import time

import requests

BASE_URL = "http://localhost:8000/api/v3/conversation"

# All test questions
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


def get_response(conversation_id: int, question: str) -> dict:
    """Get response for a question."""
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
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    print("=" * 80)
    print("Exporting Questions and Answers")
    print("=" * 80)

    conversation_id = int(time.time()) % 100000
    results = []

    for category, questions in TEST_QUESTIONS.items():
        print(f"\nCategory: {category}")

        for i, question in enumerate(questions, 1):
            print(f"  [{i}/{len(questions)}] Processing: {question[:50]}...")

            result = get_response(conversation_id, question)

            results.append({
                "category": category,
                "question": question,
                "response": result.get("response", "") if result["success"] else f"ERROR: {result.get('error', '')}",
                "success": result["success"],
                "iterations": result.get("metadata", {}).get("iterations", 0),
                "confidence": result.get("metadata", {}).get("confidence", 0),
            })

            if result["success"]:
                print(f"      ✅ Got response ({len(result.get('response', ''))} chars)")
            else:
                print(f"      ❌ Error: {result.get('error', '')[:50]}")

            time.sleep(1)

    # Export to JSON
    output_file = "test_results_export.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Exported to {output_file}")

    # Export to readable text
    text_file = "test_results_export.txt"
    with open(text_file, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("EU Programme Call Assessment - Test Results Export\n")
        f.write("=" * 80 + "\n\n")

        current_category = None
        for r in results:
            if r["category"] != current_category:
                current_category = r["category"]
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"CATEGORY: {current_category}\n")
                f.write("=" * 80 + "\n")

            f.write(f"\n📝 QUESTION: {r['question']}\n")
            f.write("-" * 60 + "\n")
            f.write(f"✅ STATUS: {'Success' if r['success'] else 'Failed'}\n")
            f.write(f"📊 Confidence: {r['confidence']}, Iterations: {r['iterations']}\n")
            f.write("-" * 60 + "\n")
            f.write(f"💬 RESPONSE:\n{r['response']}\n")
            f.write("\n" + "-" * 60 + "\n")

    print(f"✅ Exported to {text_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
