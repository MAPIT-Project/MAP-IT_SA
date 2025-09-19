#!/usr/bin/env python3
"""
Comprehensive test script for research manager questions against the streaming endpoint.
Tests realistic questions that a research manager would ask about CORDIS projects.
"""

import asyncio
import json
import aiohttp
import logging
from typing import List, Dict, Any
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchManagerTester:
    """Test class for research manager questions against the streaming API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_streaming_endpoint(self, conversation_id: int, message: str) -> Dict[str, Any]:
        """Test a single message against the streaming endpoint."""

        url = f"{self.base_url}/api/v2/conversation/{conversation_id}/message/stream"
        payload = {
            "message": message,
            "include_context": True,
            "memory_strategy": "full"
        }

        logger.info(f"🧪 Testing: '{message}'")

        try:
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ HTTP {response.status}: {error_text}")
                    return {
                        'success': False,
                        'error': f'HTTP {response.status}',
                        'message': message,
                        'response': error_text
                    }

                # Collect streaming response
                full_response = ""
                tools_executed = False
                confidence = 0.0
                processing_time = 0.0
                projects_found = 0

                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        try:
                            chunk = json.loads(line[6:])  # Remove 'data: ' prefix

                            if chunk.get('type') == 'token':
                                full_response += chunk.get('content', '')
                            elif chunk.get('type') == 'complete':
                                tools_executed = chunk.get('logs', {}).get('projects_retrieved', 0) > 0
                                confidence = chunk.get('logs', {}).get('average_relevance_score', 0.0)
                                processing_time = chunk.get('logs', {}).get('total_processing_time_ms', 0)
                                projects_found = chunk.get('logs', {}).get('projects_retrieved', 0)
                        except json.JSONDecodeError:
                            continue

                return {
                    'success': True,
                    'message': message,
                    'response': full_response,
                    'tools_executed': tools_executed,
                    'confidence': confidence,
                    'processing_time_ms': processing_time,
                    'projects_found': projects_found
                }

        except Exception as e:
            logger.error(f"❌ Request failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': message,
                'response': None
            }

    async def run_comprehensive_test(self):
        """Run comprehensive test with realistic research manager questions."""

        print("🚀 Starting Research Manager Questions Test")
        print("=" * 80)

        # Realistic research manager questions about CORDIS projects
        test_questions = [
            # Basic project searches
            "Can you find me projects on renewable energy from the last 3 years?",
            "Show me successful AI projects funded by Horizon Europe",
            "What are some completed projects in biotechnology?",

            # Specific domain searches
            "Find projects related to climate change adaptation",
            "Show me projects that received funding over 5 million euros",
            "What are some innovative projects in the field of quantum computing?",

            # Collaboration and scope searches
            "Find me projects that involve international collaboration",
            "Show me projects focused on sustainable transport",
            "What are some breakthrough projects in health research?",

            # Follow-up questions (testing context awareness)
            "Can you find similar projects in digital transformation?",
            "Show me more projects about artificial intelligence",
            "What other projects are there in the energy sector?",

            # Complex queries
            "Find projects that combine AI with healthcare applications",
            "Show me projects that address both climate change and digital innovation",
            "What are some cross-disciplinary projects involving multiple European countries?"
        ]

        conversation_id = int(datetime.now().timestamp())  # Unique conversation ID

        results = []
        success_count = 0
        tool_execution_count = 0

        for i, question in enumerate(test_questions, 1):
            print(f"\n📋 Question {i}/{len(test_questions)}")
            print("-" * 60)

            result = await self.test_streaming_endpoint(conversation_id, question)
            results.append(result)

            if result['success']:
                success_count += 1
                tools_used = "✅ TOOLS EXECUTED" if result.get('tools_executed', False) else "❌ NO TOOLS"
                confidence = result.get('confidence', 0.0)
                projects = result.get('projects_found', 0)
                time_ms = result.get('processing_time_ms', 0)

                print(f"   Status: ✅ SUCCESS")
                print(f"   Tools: {tools_used}")
                print(f"   Confidence: {confidence:.2f}")
                print(f"   Projects Found: {projects}")
                print(f"   Processing Time: {time_ms:.2f}ms")
                print(f"   Response Preview: {result['response'][:200]}...")

                if result.get('tools_executed', False):
                    tool_execution_count += 1
                else:
                    print("   ⚠️  WARNING: No tools executed - this might be an issue!")

            else:
                print(f"   Status: ❌ FAILED")
                print(f"   Error: {result.get('error', 'Unknown error')}")

        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Total Questions: {len(test_questions)}")
        print(f"Successful Requests: {success_count}/{len(test_questions)} ({success_count/len(test_questions)*100:.1f}%)")
        print(f"Questions with Tool Execution: {tool_execution_count}/{len(test_questions)} ({tool_execution_count/len(test_questions)*100:.1f}%)")

        # Analyze issues
        issues = []

        if tool_execution_count == 0:
            issues.append("❌ CRITICAL: No tools were executed for any questions!")
        elif tool_execution_count < len(test_questions) * 0.7:  # Less than 70% tool usage
            issues.append(f"⚠️  WARNING: Only {tool_execution_count}/{len(test_questions)} questions triggered tools")

        failed_requests = len(test_questions) - success_count
        if failed_requests > 0:
            issues.append(f"❌ ERROR: {failed_requests} requests failed")

        if issues:
            print("\n🚨 ISSUES IDENTIFIED:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("\n✅ ALL TESTS PASSED!")

        # Detailed analysis
        print("\n🔍 DETAILED ANALYSIS:")
        print("-" * 40)

        # Group by tool execution
        with_tools = [r for r in results if r.get('tools_executed', False)]
        without_tools = [r for r in results if not r.get('tools_executed', False) and r['success']]

        print(f"Questions that triggered CORDIS search: {len(with_tools)}")
        if with_tools:
            avg_confidence = sum(r.get('confidence', 0) for r in with_tools) / len(with_tools)
            avg_projects = sum(r.get('projects_found', 0) for r in with_tools) / len(with_tools)
            print(f"   Average Confidence: {avg_confidence:.2f}")
            print(f"   Average Projects Found: {avg_projects:.1f}")
        print(f"Questions that used conversational AI: {len(without_tools)}")
        if without_tools:
            print("   (These should ideally trigger CORDIS searches for project questions)")

        return results

async def main():
    """Main test function."""
    print("🔬 Research Manager CORDIS Project Search Test")
    print("Testing realistic questions against the streaming API endpoint")
    print()

    async with ResearchManagerTester() as tester:
        results = await tester.run_comprehensive_test()

        # Save results for analysis
        with open('test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print("\n💾 Results saved to test_results.json")

if __name__ == "__main__":
    asyncio.run(main())