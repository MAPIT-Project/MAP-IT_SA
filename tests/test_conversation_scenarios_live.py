#!/usr/bin/env python3
"""
Live API tests for conversation scenarios.
Tests the V3 conversation API with real scenarios from CONVERSATION_SCENARIOS.md
"""

import asyncio
import aiohttp
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

BASE_URL = "http://localhost:8000"

@dataclass
class ScenarioResult:
    """Result of a scenario test."""
    category: str
    scenario_id: str
    scenario_name: str
    user_message: str
    response: str
    tools_used: List[str]
    duration_ms: int
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


async def send_message(session: aiohttp.ClientSession, conversation_id: int, message: str) -> Dict[str, Any]:
    """Send a message to the V3 API and collect the full response."""
    url = f"{BASE_URL}/api/v3/conversation/{conversation_id}/message/stream"

    start_time = time.time()
    response_text = ""
    tools_used = []
    agent_thoughts = []
    error = None
    metadata = {}

    try:
        async with session.post(url, json={"message": message}) as resp:
            if resp.status != 200:
                return {
                    "response": "",
                    "tools_used": [],
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "success": False,
                    "error": f"HTTP {resp.status}",
                    "metadata": {}
                }

            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        event_type = data.get('type', '')

                        if event_type == 'token':
                            response_text += data.get('content', '')
                        elif event_type == 'tool_call':
                            tools_used.append(data.get('tool', 'unknown'))
                        elif event_type == 'agent_thinking':
                            agent_thoughts.append(data.get('content', ''))
                        elif event_type == 'error':
                            error = data.get('error', 'Unknown error')
                        elif event_type == 'complete':
                            metadata = data.get('metadata', {})
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        error = str(e)

    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "response": response_text,
        "tools_used": tools_used,
        "duration_ms": duration_ms,
        "success": error is None and len(response_text) > 0,
        "error": error,
        "metadata": metadata,
        "agent_thoughts": agent_thoughts
    }


async def clear_conversation(session: aiohttp.ClientSession, conversation_id: int):
    """Clear conversation context."""
    url = f"{BASE_URL}/api/v3/conversation/{conversation_id}/context"
    try:
        async with session.delete(url) as resp:
            return resp.status == 200
    except:
        return False


# Define test scenarios
SCENARIOS = [
    # Category 1: Getting Started
    {
        "category": "Getting Started",
        "id": "1.1",
        "name": "New User Onboarding",
        "message": "I want to write a proposal for Horizon Europe. Where do I start?",
        "expect_keywords": ["proposal", "section", "call", "topic"],
    },
    {
        "category": "Getting Started",
        "id": "1.2",
        "name": "Call Selection",
        "message": "I found a call about AI in healthcare. The ID is HORIZON-HLTH-2024-TOOL-11-01. Can you tell me about it?",
        "expect_keywords": ["call", "health", "topic"],
        "expect_tools": ["search_funding_calls", "get_call_details"],
    },
    {
        "category": "Getting Started",
        "id": "1.3",
        "name": "Topic Understanding",
        "message": "What exactly is this call looking for? I don't understand the technical scope of HORIZON-CL4-2024-DIGITAL-EMERGING-01.",
        "expect_keywords": ["scope", "requirement", "topic"],
    },

    # Category 2: Section Writing
    {
        "category": "Section Writing",
        "id": "2.1",
        "name": "Generate Excellence Draft",
        "message": "Write the Excellence section for my proposal about quantum computing for drug discovery. The project aims to use quantum algorithms to simulate molecular interactions faster than classical computers.",
        "expect_keywords": ["excellence", "quantum", "drug", "innovation", "objective"],
    },
    {
        "category": "Section Writing",
        "id": "2.2",
        "name": "Generate Impact Draft",
        "message": "Now write the Impact section. Our main stakeholders are pharmaceutical companies, hospitals, and research institutions. We expect to reduce drug development time by 40%.",
        "expect_keywords": ["impact", "stakeholder", "dissemination", "exploitation"],
    },
    {
        "category": "Section Writing",
        "id": "2.5",
        "name": "Bullet Points to Prose",
        "message": """Here are my key points for the methodology:
- Novel AI algorithm using transformer architecture
- 50% faster than current state of art
- Validated on 3 public datasets
- Open source implementation
Turn this into a proper paragraph for the proposal.""",
        "expect_keywords": ["algorithm", "transformer", "validated", "methodology"],
    },

    # Category 3: Quality Improvement
    {
        "category": "Quality Improvement",
        "id": "3.1",
        "name": "General Improvement Request",
        "message": "This section feels weak: 'Our project will develop new AI methods for healthcare. We will use machine learning to analyze data and provide insights.' How can I make it stronger?",
        "expect_keywords": ["specific", "improve", "detail", "concrete"],
    },
    {
        "category": "Quality Improvement",
        "id": "3.2",
        "name": "Evaluator Perspective",
        "message": "What would an evaluator think of this paragraph: 'The consortium brings together leading experts from academia and industry across Europe. Our combined expertise ensures successful project delivery.'",
        "expect_keywords": ["evaluator", "vague", "specific", "evidence"],
    },

    # Category 4: Score & Feedback
    {
        "category": "Score & Feedback",
        "id": "4.1",
        "name": "Quick Score Check",
        "message": "Can you score this Excellence section? 'Our groundbreaking project QUANTUM-HEALTH will revolutionize drug discovery through quantum computing. We will develop novel quantum algorithms that simulate molecular binding with unprecedented accuracy. Our consortium includes 3 leading universities and 2 pharmaceutical companies with combined experience of over 50 years in computational chemistry.'",
        "expect_keywords": ["score", "criterion", "strength", "weakness"],
    },
    {
        "category": "Score & Feedback",
        "id": "4.6",
        "name": "Score Explanation",
        "message": "Why would a proposal get only 3.2 out of 5? What are the typical weaknesses that lead to below-threshold scores?",
        "expect_keywords": ["threshold", "weakness", "criteria", "improve"],
    },

    # Category 5: Gap Analysis
    {
        "category": "Gap Analysis",
        "id": "5.1",
        "name": "Identify All Gaps",
        "message": "What's typically missing from proposals that score below the funding threshold? What are the most common gaps?",
        "expect_keywords": ["gap", "missing", "requirement", "criteria"],
    },
    {
        "category": "Gap Analysis",
        "id": "5.3",
        "name": "Gap in Specific Area",
        "message": "Is there anything typically missing in methodology descriptions? What do evaluators expect to see?",
        "expect_keywords": ["methodology", "approach", "expect", "include"],
    },

    # Category 6: Rewriting & Suggestions
    {
        "category": "Rewriting & Suggestions",
        "id": "6.1",
        "name": "Full Section Rewrite",
        "message": "Rewrite this to be more compelling: 'We will develop software for data analysis. The software will help researchers. It will be user-friendly and efficient.'",
        "expect_keywords": ["develop", "platform", "researcher"],
    },
    {
        "category": "Rewriting & Suggestions",
        "id": "6.2",
        "name": "Multiple Rewrite Options",
        "message": "Give me 3 different ways to rewrite this paragraph: 'Our consortium has partners from several countries who will work together on the project objectives.'",
        "expect_keywords": ["option", "version", "alternative"],
    },

    # Category 7: Learning from Examples
    {
        "category": "Learning from Examples",
        "id": "7.1",
        "name": "Find Similar Projects",
        "message": "Show me funded Horizon Europe projects similar to AI for drug discovery.",
        "expect_keywords": ["project", "fund", "similar"],
        "expect_tools": ["search_projects", "find_similar_projects", "find_semantically_similar_projects"],
    },
    {
        "category": "Learning from Examples",
        "id": "7.6",
        "name": "Budget Benchmarking",
        "message": "What's a typical budget for a 4-year RIA project with 8 partners in the digital health area?",
        "expect_keywords": ["budget", "million", "partner", "cost"],
        "expect_tools": ["get_budget_benchmark"],
    },

    # Category 8: Budget & Timeline
    {
        "category": "Budget & Timeline",
        "id": "8.1",
        "name": "Generate Budget",
        "message": "Help me create a budget outline for a 3-year Innovation Action project with 6 partners requesting €4M total.",
        "expect_keywords": ["budget", "personnel", "cost", "partner"],
        "expect_tools": ["calculate_budget"],
    },
    {
        "category": "Budget & Timeline",
        "id": "8.4",
        "name": "Generate Timeline",
        "message": "Create a project timeline with work packages for a 36-month digital health project with 5 main work packages.",
        "expect_keywords": ["work package", "month", "deliverable", "milestone"],
        "expect_tools": ["generate_timeline"],
    },

    # Category 9: Compliance & Requirements
    {
        "category": "Compliance & Requirements",
        "id": "9.2",
        "name": "Consortium Eligibility",
        "message": "Is a consortium eligible for Horizon Europe if we have partners from Germany, Switzerland, and UK?",
        "expect_keywords": ["eligible", "associated", "country", "partner"],
    },
    {
        "category": "Compliance & Requirements",
        "id": "9.4",
        "name": "Missing Mandatory Elements",
        "message": "What mandatory elements must a Horizon Europe proposal include? What are the required sections?",
        "expect_keywords": ["mandatory", "section", "ethics", "require"],
    },

    # Category 10: Progress & Achievements (Proposal Writer specific)
    {
        "category": "Progress & Achievements",
        "id": "10.5",
        "name": "Motivation/Tips",
        "message": "I'm feeling stuck writing my proposal. Any tips for getting unstuck?",
        "expect_keywords": ["section", "start", "focus", "break"],
    },

    # Category 11: Dashboard & Overview
    {
        "category": "Dashboard & Overview",
        "id": "11.3",
        "name": "Next Actions Advice",
        "message": "I've written my Excellence and Impact sections but haven't started Implementation. What should I work on next?",
        "expect_keywords": ["implementation", "section", "work package", "start"],
    },
    {
        "category": "Dashboard & Overview",
        "id": "11.4",
        "name": "Submission Readiness",
        "message": "What should I check before submitting my Horizon Europe proposal? What's the pre-submission checklist?",
        "expect_keywords": ["check", "submit", "review", "requirement"],
    },

    # Category 13: Error Recovery
    {
        "category": "Error Recovery",
        "id": "13.1",
        "name": "Unclear Request",
        "message": "Make it better.",
        "expect_keywords": ["which", "section", "specify", "clarify", "what"],
    },
    {
        "category": "Error Recovery",
        "id": "13.5",
        "name": "Out of Scope Request",
        "message": "Write my PhD thesis introduction about machine learning.",
        "expect_keywords": ["proposal", "horizon", "help", "focus"],
    },

    # Category 14: Multi-Turn Conversations
    {
        "category": "Multi-Turn Conversations",
        "id": "14.1a",
        "name": "Iterative Refinement - Part 1",
        "message": "Write a brief objectives section for a renewable energy project.",
        "expect_keywords": ["objective", "energy", "renewable"],
        "multi_turn_id": "14.1",
    },
    {
        "category": "Multi-Turn Conversations",
        "id": "14.1b",
        "name": "Iterative Refinement - Part 2 (Follow-up)",
        "message": "Make the first objective more specific with measurable targets.",
        "expect_keywords": ["specific", "target", "measure", "%"],
        "multi_turn_id": "14.1",
        "requires_context": True,
    },

    # Category 15: Edge Cases
    {
        "category": "Edge Cases",
        "id": "15.5",
        "name": "Copy-Pasted Requirements",
        "message": "I have a call about 'Climate-neutral and smart cities'. The expected outcome is: 'Projects are expected to contribute to all of the following expected outcomes: Innovative approaches for climate neutrality, Demonstration of solutions for sustainable mobility, Engagement of citizens in urban transformation.' Write me a paragraph addressing these outcomes.",
        "expect_keywords": ["climate", "city", "mobility", "citizen"],
    },
    {
        "category": "Edge Cases",
        "id": "15.7",
        "name": "Last-Minute Panic",
        "message": "My deadline is tomorrow! What are the absolute most critical things I must have in my Horizon Europe proposal to not get rejected?",
        "expect_keywords": ["critical", "essential", "must", "section", "eligibility"],
    },
]


async def run_scenario(session: aiohttp.ClientSession, scenario: Dict, conversation_id: int) -> ScenarioResult:
    """Run a single scenario and return the result."""
    print(f"\n{'='*60}")
    print(f"Running: [{scenario['id']}] {scenario['name']}")
    print(f"Category: {scenario['category']}")
    print(f"Message: {scenario['message'][:100]}...")

    result = await send_message(session, conversation_id, scenario['message'])

    # Check if expected keywords are present in response
    response_lower = result['response'].lower()
    keywords_found = []
    keywords_missing = []

    for keyword in scenario.get('expect_keywords', []):
        if keyword.lower() in response_lower:
            keywords_found.append(keyword)
        else:
            keywords_missing.append(keyword)

    # Check if expected tools were used
    expected_tools = scenario.get('expect_tools', [])
    tools_found = [t for t in expected_tools if t in result['tools_used']]
    tools_missing = [t for t in expected_tools if t not in result['tools_used']]

    # Determine overall success
    success = result['success']
    if keywords_missing and len(keywords_missing) > len(scenario.get('expect_keywords', [])) / 2:
        success = False

    print(f"Duration: {result['duration_ms']}ms")
    print(f"Tools used: {result['tools_used']}")
    print(f"Response length: {len(result['response'])} chars")
    print(f"Keywords found: {keywords_found}")
    if keywords_missing:
        print(f"Keywords missing: {keywords_missing}")
    if result['error']:
        print(f"Error: {result['error']}")
    print(f"Success: {'✅' if success else '❌'}")
    print(f"\nResponse preview: {result['response'][:300]}...")

    return ScenarioResult(
        category=scenario['category'],
        scenario_id=scenario['id'],
        scenario_name=scenario['name'],
        user_message=scenario['message'],
        response=result['response'],
        tools_used=result['tools_used'],
        duration_ms=result['duration_ms'],
        success=success,
        error=result['error'],
        metadata={
            "keywords_found": keywords_found,
            "keywords_missing": keywords_missing,
            "tools_found": tools_found,
            "tools_missing": tools_missing,
            "expect_tools": expected_tools,
        }
    )


async def run_all_scenarios():
    """Run all scenarios and generate a report."""
    print("="*60)
    print("CONVERSATION SCENARIOS LIVE TEST")
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"API Base: {BASE_URL}")
    print("="*60)

    results: List[ScenarioResult] = []

    # Use different conversation IDs for different scenario groups
    # Multi-turn scenarios share a conversation ID
    multi_turn_conversations = {}
    base_conversation_id = int(time.time()) % 100000

    async with aiohttp.ClientSession() as session:
        # Check API health first
        try:
            async with session.get(f"{BASE_URL}/api/v3/conversation/health") as resp:
                if resp.status != 200:
                    print("❌ API is not healthy!")
                    return
                health = await resp.json()
                print(f"✅ API Health: {health}")
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            return

        for i, scenario in enumerate(SCENARIOS):
            # Determine conversation ID
            multi_turn_id = scenario.get('multi_turn_id')
            if multi_turn_id:
                if multi_turn_id not in multi_turn_conversations:
                    multi_turn_conversations[multi_turn_id] = base_conversation_id + i
                conversation_id = multi_turn_conversations[multi_turn_id]
            else:
                conversation_id = base_conversation_id + i

            try:
                result = await run_scenario(session, scenario, conversation_id)
                results.append(result)
            except Exception as e:
                print(f"❌ Error running scenario: {e}")
                results.append(ScenarioResult(
                    category=scenario['category'],
                    scenario_id=scenario['id'],
                    scenario_name=scenario['name'],
                    user_message=scenario['message'],
                    response="",
                    tools_used=[],
                    duration_ms=0,
                    success=False,
                    error=str(e),
                ))

            # Small delay between scenarios to avoid rate limiting
            await asyncio.sleep(1)

    # Generate summary report
    print("\n" + "="*60)
    print("SUMMARY REPORT")
    print("="*60)

    # Group by category
    categories = {}
    for result in results:
        if result.category not in categories:
            categories[result.category] = []
        categories[result.category].append(result)

    total_success = 0
    total_tests = len(results)

    for category, cat_results in categories.items():
        cat_success = sum(1 for r in cat_results if r.success)
        cat_total = len(cat_results)
        total_success += cat_success

        print(f"\n{category}: {cat_success}/{cat_total}")
        for r in cat_results:
            status = "✅" if r.success else "❌"
            print(f"  {status} [{r.scenario_id}] {r.scenario_name} ({r.duration_ms}ms)")
            if not r.success and r.error:
                print(f"      Error: {r.error}")
            if r.metadata.get('keywords_missing'):
                print(f"      Missing keywords: {r.metadata['keywords_missing']}")

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_success}/{total_tests} scenarios passed ({100*total_success/total_tests:.1f}%)")
    print(f"Average response time: {sum(r.duration_ms for r in results)/len(results):.0f}ms")
    print("="*60)

    # Return results for further analysis
    return results


if __name__ == "__main__":
    asyncio.run(run_all_scenarios())
