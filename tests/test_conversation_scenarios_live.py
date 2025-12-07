"""
Live tests for all conversation scenarios from CONVERSATION_SCENARIOS.md
"""
import asyncio
import json
from typing import Dict, List
from app.services.agents.tool_aware_agent import ToolAwareAgent

# All test scenarios from the document
SCENARIOS = {
    # Section 1: Getting Started
    "1.1": ("I want to write a proposal for Horizon Europe. Where do I start?", "New User Onboarding"),
    "1.2": ("I found a call about European Film Sales. The ID is CREA-MEDIA-2026-FILMSALES.", "Call Selection"),
    "1.3": ("What exactly is this call looking for? I don't understand the technical scope.", "Topic Understanding"),
    "1.4": ("Let's start a new proposal for this call. Our project is about using machine learning to predict drug interactions.", "Proposal Initialization"),
    "1.5": ("I was working on my proposal yesterday. Can we continue?", "Returning User"),

    # Section 2: Section Writing
    "2.1": ("Write the Excellence section for my proposal about quantum computing for drug discovery.", "Generate Excellence"),
    "2.2": ("Now write the Impact section. Our main stakeholders are pharmaceutical companies and hospitals.", "Generate Impact"),
    "2.3": ("Generate the Implementation section. We have 5 partners from Germany, France, Spain, Netherlands, and Italy.", "Generate Implementation"),
    "2.4": ("I've written the first paragraph of my objectives. Can you continue from here?", "Partial Section Writing"),
    "2.5": ("Here are my key points:\n- Novel AI algorithm\n- 50% faster than state of art\n- Validated on 3 datasets\nTurn this into a proper paragraph.", "Bullet Points to Prose"),
    "2.6": ("What should go in the 'Methodology' subsection?", "Section-Specific Guidance"),

    # Section 3: Quality Improvement
    "3.1": ("This section feels weak. How can I make it stronger?", "General Improvement"),
    "3.2": ("What would an evaluator think of this paragraph?", "Evaluator Perspective"),
    "3.3": ("The innovation part isn't convincing enough. Help me strengthen it.", "Strengthen Innovation"),
    "3.4": ("Reviewers might think this is too superficial. Add more technical detail.", "Add Technical Depth"),
    "3.5": ("This paragraph is confusing. Make it clearer.", "Improve Clarity"),
    "3.6": ("This is too long. Cut it down by 30% without losing key points.", "Make Concise"),

    # Section 4: Score & Feedback
    "4.1": ("What's my current score for this section?", "Quick Score"),
    "4.2": ("Give me a detailed evaluation of my Excellence section.", "Detailed Evaluation"),
    "4.3": ("How does my score compare to the funding threshold?", "Score Comparison"),
    "4.4": ("Has my score improved since the last version?", "Track Improvement"),
    "4.5": ("If I submit now, what score would I likely get?", "Predict Final Score"),
    "4.6": ("Why did I only get 3.2? I thought this was good.", "Score Explanation"),

    # Section 5: Gap Analysis
    "5.1": ("What's missing from my proposal?", "Identify All Gaps"),
    "5.2": ("What are the most critical things I need to fix?", "Critical Gaps"),
    "5.3": ("Is there anything missing in my methodology description?", "Gap in Specific Area"),
    "5.4": ("Does my proposal address all the call requirements?", "Compare to Requirements"),
    "5.5": ("How do I fix the gap about 'clear KPIs'?", "Gap Resolution"),
    "5.6": ("I added the risk assessment. Is the gap closed now?", "Verify Gap Closure"),

    # Section 6: Rewriting & Suggestions
    "6.1": ("Rewrite this entire section to be more compelling.", "Full Section Rewrite"),
    "6.2": ("Give me 3 different ways to rewrite this paragraph.", "Paragraph Options"),
    "6.3": ("Show me suggestions for improving this text inline.", "Inline Suggestions"),
    "6.4": ("Apply suggestion 2 but not the others.", "Accept/Reject Suggestions"),
    "6.5": ("Rewrite this to match the style of my other sections.", "Style Matching"),
    "6.6": ("Rewrite just the innovation claims to be more specific.", "Targeted Rewrite"),

    # Section 7: Learning from Examples
    "7.1": ("Show me funded projects similar to mine.", "Find Similar Projects"),
    "7.2": ("What can I learn from how project EXAMPLE-123 wrote their Excellence section?", "Learn from Successful"),
    "7.3": ("How does my proposal compare to funded projects in this area?", "Benchmark Against Funded"),
    "7.4": ("Use a similar structure to what worked for funded AI projects.", "Copy Successful Patterns"),
    "7.5": ("Show me how other proposals described their consortium for digital health.", "Topic-Specific Examples"),
    "7.6": ("Is my budget realistic compared to similar funded projects?", "Budget Benchmarking"),

    # Section 8: Budget & Timeline
    "8.1": ("Create a budget for a 4-year RIA project with 8 partners requesting 5M total.", "Generate Budget"),
    "8.2": ("Is my budget compliant with Horizon Europe rules?", "Budget Validation"),
    "8.3": ("How can I optimize the budget distribution?", "Budget Optimization"),
    "8.4": ("Create a project timeline with work packages and milestones.", "Generate Timeline"),
    "8.5": ("Is my timeline realistic for the proposed activities?", "Timeline Validation"),
    "8.6": ("What should Partner 3's budget look like? They're a university doing WP2 and WP4.", "Partner Budget"),

    # Section 9: Compliance & Requirements
    "9.1": ("Is my proposal compliant with all requirements?", "Overall Compliance"),
    "9.2": ("Is our consortium eligible? We have partners from Germany, Switzerland, and UK.", "Consortium Eligibility"),
    "9.3": ("Does my proposal meet the page limits and formatting requirements?", "Format Compliance"),
    "9.4": ("What mandatory elements am I missing?", "Missing Mandatory"),
    "9.5": ("Help me fix the ethics section to be compliant.", "Fix Compliance"),
    "9.6": ("Give me a final checklist before submission.", "Pre-Submission Checklist"),

    # Section 10: Progress & Achievements
    "10.1": ("How far along is my proposal?", "Check Progress"),
    "10.2": ("What achievements have I earned?", "View Achievements"),
    "10.3": ("What's my writing streak?", "View Streak"),

    # Section 11: Dashboard & Overview
    "11.1": ("Show me my proposal dashboard.", "Full Dashboard"),
    "11.2": ("Give me a quick status update.", "Quick Summary"),
    "11.3": ("What should I work on next?", "Next Actions"),
    "11.4": ("Am I ready to submit?", "Submission Readiness"),
    "11.5": ("Which section needs the most work?", "Section Comparison"),
    "11.6": ("How much time do I have left?", "Time to Deadline"),

    # Section 13: Error Recovery
    "13.1": ("Make it better.", "Unclear Request"),
    "13.3": ("Continue writing.", "Missing Context"),
    "13.4": ("Make it shorter but add more detail about the methodology.", "Conflicting Instructions"),
    "13.5": ("Write my PhD thesis introduction.", "Out of Scope"),
}


async def test_scenario(agent, scenario_id, query, name):
    """Test a single scenario and return results."""
    try:
        result = await agent.process_query(
            query=query,
            conversation_history=[],
            context={}
        )

        tools_used = []
        for step in result.get('reasoning_steps', []):
            tools_used.extend(step.get('tools_called', []))

        answer = result.get('answer', '')
        success = result.get('success', False)

        # Determine if the response is meaningful
        is_meaningful = (
            len(answer) > 100 and
            "I found some information but couldn't extract" not in answer and
            answer != ""
        )

        return {
            'scenario_id': scenario_id,
            'name': name,
            'query': query,
            'success': success,
            'is_meaningful': is_meaningful,
            'tools_used': tools_used,
            'answer_length': len(answer),
            'answer_preview': answer[:500] if answer else "NO ANSWER",
            'error': None
        }
    except Exception as e:
        import traceback
        return {
            'scenario_id': scenario_id,
            'name': name,
            'query': query,
            'success': False,
            'is_meaningful': False,
            'tools_used': [],
            'answer_length': 0,
            'answer_preview': "",
            'error': str(e) + "\n" + traceback.format_exc()
        }


async def run_all_tests():
    """Run all scenario tests."""
    agent = ToolAwareAgent()
    results = []

    for scenario_id, (query, name) in SCENARIOS.items():
        print(f"Testing {scenario_id}: {name}...")
        result = await test_scenario(agent, scenario_id, query, name)
        results.append(result)

        status = "PASS" if result['is_meaningful'] else "FAIL"
        print(f"  [{status}] Tools: {result['tools_used']}, Length: {result['answer_length']}")

    return results


def print_summary(results):
    """Print test summary."""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = [r for r in results if r['is_meaningful']]
    failed = [r for r in results if not r['is_meaningful']]

    print(f"\nPassed: {len(passed)}/{len(results)}")
    print(f"Failed: {len(failed)}/{len(results)}")

    if failed:
        print("\n" + "="*80)
        print("FAILED SCENARIOS:")
        print("="*80)
        for r in failed:
            print(f"\n{r['scenario_id']}: {r['name']}")
            print(f"  Query: {r['query'][:80]}...")
            print(f"  Tools: {r['tools_used']}")
            if r['error']:
                print(f"  Error: {r['error'][:200]}")
            print(f"  Preview: {r['answer_preview'][:150]}...")

    return passed, failed


if __name__ == "__main__":
    results = asyncio.run(run_all_tests())
    passed, failed = print_summary(results)

    # Save detailed results
    with open("scenario_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nDetailed results saved to scenario_test_results.json")
