#!/usr/bin/env python3
"""
Simple test script for the combined phase implementation.
Tests the logic without requiring full dependencies.
"""

import json
import re
from typing import Dict, Any, Optional, List, Tuple

# Mock classes to simulate the dependencies
class MockResponseGenerator:
    def __init__(self):
        self.model = MockModel()

class MockModel:
    def generate_content(self, prompt: str):
        # Mock response that simulates the combined phase output
        mock_response = {
            "intent_analysis": {
                "intent_type": "question",
                "requires_retrieval": True,
                "requires_tools": True,
                "confidence": 0.85,
                "explanation": "User is asking about funding calls"
            },
            "context_assessment": {
                "relevant_topics": ["funding", "calls", "energy"],
                "context_importance": "high",
                "context_summary": "Previous conversation about energy research funding"
            },
            "tool_plan": {
                "tools_needed": [
                    {
                        "tool_name": "eu_portal_search",
                        "parameters": {
                            "query": "energy calls",
                            "status": "open",
                            "max_results": 20
                        },
                        "reason": "User asking for open calls about energy"
                    }
                ],
                "execution_strategy": "parallel",
                "reasoning": "Direct match for call search query"
            },
            "processing_recommendation": {
                "use_tools": True,
                "use_retrieval": False,
                "response_type": "tool_based"
            }
        }
        return MockResponse(text=json.dumps(mock_response))

class MockResponse:
    def __init__(self, text: str):
        self.text = text

class MockToolCall:
    def __init__(self, tool_name: str, parameters: Dict, execution_order: int):
        self.tool_name = tool_name
        self.parameters = parameters
        self.execution_order = execution_order

# Simplified version of the combined phase method for testing
async def test_combined_intent_context_tool_planner(user_message: str) -> Tuple[Dict[str, Any], str, Optional[List]]:
    """
    Test version of the combined phase method
    """
    try:
        # Mock conversation data
        conversation_history = "User: What are some open calls?\nAssistant: I can help you find current funding opportunities."

        # Mock available tools
        available_tools = [
            {"name": "eu_portal_search", "description": "Search EU funding portal"},
            {"name": "search_cordis_projects", "description": "Search CORDIS projects"}
        ]

        # Create comprehensive prompt for combined analysis
        prompt = f"""You are an AI assistant specializing in European research funding. Analyze this user message and provide a comprehensive response that includes intent analysis, context assessment, and tool planning.

CONVERSATION CONTEXT:
Recent History:
{conversation_history}

USER MESSAGE: {user_message}

AVAILABLE TOOLS:
{json.dumps(available_tools, indent=2)}

INSTRUCTIONS:
1. Analyze the user's intent and classify the query type
2. Assess what context is most relevant for this query
3. Determine if tools are needed and which ones
4. Provide reasoning for your decisions

RESPONSE FORMAT (JSON):
{{
    "intent_analysis": {{
        "intent_type": "question|command|clarification|follow_up|greeting",
        "requires_retrieval": true/false,
        "requires_tools": true/false,
        "confidence": 0.0-1.0,
        "explanation": "Brief explanation of intent"
    }},
    "context_assessment": {{
        "relevant_topics": ["topic1", "topic2"],
        "context_importance": "high|medium|low",
        "context_summary": "Summary of relevant context"
    }},
    "tool_plan": {{
        "tools_needed": [
            {{
                "tool_name": "eu_portal_search|search_cordis_projects",
                "parameters": {{
                    "query": "search terms",
                    "status": "open|closed",
                    "max_results": 20
                }},
                "reason": "Why this tool is needed"
            }}
        ],
        "execution_strategy": "parallel|sequential",
        "reasoning": "Overall reasoning for tool selection"
    }},
    "processing_recommendation": {{
        "use_tools": true/false,
        "use_retrieval": true/false,
        "response_type": "tool_based|conversational|mixed"
    }}
}}

TOOL SELECTION RULES:
- For "open calls", "funding opportunities", "calls for proposals" → eu_portal_search
- For "projects", "research projects", "case studies" → search_cordis_projects
- For conversational queries (hello, help, thanks) → no tools
- For nonsense/short queries without funding terms → no tools
- For domain + funding patterns (energy calls, AI funding) → eu_portal_search

If no tools are needed, set tools_needed to empty array.
"""

        # Simulate AI call with mock response generator
        mock_generator = MockResponseGenerator()
        response = mock_generator.model.generate_content(prompt)

        # Parse JSON response
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            combined_decision = json.loads(json_match.group())
            print(f"🤖 COMBINED PHASE TEST: {combined_decision['processing_recommendation']['response_type']}")

            # Extract components
            intent_analysis = combined_decision['intent_analysis']
            context_assessment = combined_decision['context_assessment']
            tool_plan_data = combined_decision['tool_plan']

            # Build context string from assessment
            context = f"Context Assessment: {context_assessment['context_summary']}\n"
            context += f"Relevant Topics: {', '.join(context_assessment['relevant_topics'])}\n"
            context += f"Conversation Summary: {conversation_history}"

            # Convert tool plan to ToolCall objects
            tool_plan = None
            if tool_plan_data['tools_needed']:
                tool_calls = []
                for i, tool_spec in enumerate(tool_plan_data['tools_needed']):
                    tool_call = MockToolCall(
                        tool_name=tool_spec['tool_name'],
                        parameters=tool_spec['parameters'],
                        execution_order=i
                    )
                    tool_calls.append(tool_call)
                tool_plan = tool_calls
                print(f"   Tools planned: {len(tool_calls)}")

            return intent_analysis, context, tool_plan

    except Exception as e:
        print(f"Combined phase test error: {e}")
        return None, None, None

async def main():
    """Test the combined phase with different query types"""
    print("🧪 Testing Combined Phase Implementation")
    print("=" * 50)

    test_queries = [
        "What are some open calls for energy research?",
        "Tell me about completed AI projects",
        "Hello, how can you help me?",
        "Thanks for the information"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: '{query}'")
        print("-" * 30)

        intent_analysis, context, tool_plan = await test_combined_intent_context_tool_planner(query)

        if intent_analysis:
            print(f"Intent: {intent_analysis['intent_type']} (confidence: {intent_analysis['confidence']})")
            print(f"Requires tools: {intent_analysis['requires_tools']}")
            print(f"Context length: {len(context) if context else 0} chars")
            print(f"Tools planned: {len(tool_plan) if tool_plan else 0}")
        else:
            print("❌ Combined phase failed")

    print("\n✅ Combined phase testing completed!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())