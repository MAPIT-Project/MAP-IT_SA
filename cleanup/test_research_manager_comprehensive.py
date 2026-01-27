#!/usr/bin/env python3
"""
Comprehensive test suite for the FastAPI Conversation AI system.
Testing queries that a research manager might have about Horizon Europe projects.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any

import aiohttp

BASE_URL = "http://localhost:8000"

# Test queries that a research manager might ask
RESEARCH_MANAGER_QUERIES = [
    # Basic information queries
    {
        "query": "What is Horizon Europe?",
        "category": "basic_info",
        "expected_topics": ["funding", "research", "innovation", "european"],
        "description": "Basic overview of the Horizon Europe program",
    },
    # Project search queries
    {
        "query": "Find AI and machine learning projects in healthcare",
        "category": "project_search",
        "expected_topics": [
            "artificial intelligence",
            "machine learning",
            "healthcare",
            "projects",
        ],
        "description": "Search for specific domain projects",
    },
    {
        "query": "Show me renewable energy projects funded in 2023",
        "category": "project_search",
        "expected_topics": ["renewable energy", "2023", "funded", "projects"],
        "description": "Time-filtered project search",
    },
    # Funding and budget queries
    {
        "query": "What is the total budget for climate change projects?",
        "category": "funding_analysis",
        "expected_topics": ["budget", "climate change", "funding"],
        "description": "Budget analysis for specific themes",
    },
    {
        "query": "Which countries receive the most Horizon Europe funding?",
        "category": "funding_analysis",
        "expected_topics": ["countries", "funding", "distribution"],
        "description": "Geographic funding distribution",
    },
    # Trend and analysis queries
    {
        "query": "What are the trending research topics in quantum computing?",
        "category": "trend_analysis",
        "expected_topics": ["quantum computing", "research", "trends"],
        "description": "Research trend analysis",
    },
    {
        "query": "Compare digital transformation projects between Germany and France",
        "category": "comparative_analysis",
        "expected_topics": ["digital transformation", "Germany", "France", "comparison"],
        "description": "Comparative country analysis",
    },
    # Collaboration queries
    {
        "query": "Find collaborative projects between universities and industry",
        "category": "collaboration_analysis",
        "expected_topics": ["collaboration", "universities", "industry", "partnerships"],
        "description": "Collaboration pattern analysis",
    },
    # Success metrics queries
    {
        "query": "What are the most successful projects in biotechnology?",
        "category": "success_metrics",
        "expected_topics": ["successful", "biotechnology", "projects", "outcomes"],
        "description": "Success evaluation queries",
    },
    # Complex analytical queries
    {
        "query": "Analyze the impact of COVID-19 on European research funding priorities",
        "category": "impact_analysis",
        "expected_topics": ["COVID-19", "research funding", "priorities", "impact"],
        "description": "Complex impact analysis",
    },
    # Forward-looking queries
    {
        "query": "What emerging technologies should we prioritize for the next call?",
        "category": "strategic_planning",
        "expected_topics": ["emerging technologies", "priorities", "future", "recommendations"],
        "description": "Strategic planning support",
    },
    # Specific project queries
    {
        "query": "Tell me about project CORDIS-123456 and its deliverables",
        "category": "project_details",
        "expected_topics": ["project", "deliverables", "details"],
        "description": "Specific project information",
    },
]


class ConversationAITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.conversation_id = 1  # Using fixed conversation ID for testing
        self.session = None
        self.results = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_health_endpoint(self) -> bool:
        """Test if the API is healthy and responsive."""
        try:
            async with self.session.get(f"{self.base_url}/api/v2/conversation/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ Health check passed: {health_data.get('status', 'unknown')}")
                    return True
                else:
                    print(f"❌ Health check failed with status: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    async def test_conversation_endpoint(
        self, query_data: dict[str, Any], use_streaming: bool = True
    ) -> dict[str, Any]:
        """Test a single conversation query."""

        query = query_data["query"]
        category = query_data["category"]
        description = query_data["description"]

        print(f"\n🔍 Testing {category}: {description}")
        print(f"Query: '{query}'")

        # Prepare request
        payload = {
            "message": query,
            "include_context": True,
            "memory_strategy": "full",
            "tools_enabled": ["search", "analysis", "retrieval"],
        }

        start_time = time.time()

        try:
            if use_streaming:
                # Test streaming endpoint
                response_text = await self._test_streaming_endpoint(payload)
            else:
                # Test regular endpoint
                response_text = await self._test_regular_endpoint(payload)

            processing_time = time.time() - start_time

            # Analyze response quality
            quality_score = self._analyze_response_quality(response_text, query_data)

            result = {
                "query": query,
                "category": category,
                "description": description,
                "response": (
                    response_text[:500] + "..." if len(response_text) > 500 else response_text
                ),
                "full_response": response_text,
                "processing_time": processing_time,
                "quality_score": quality_score,
                "success": len(response_text) > 50,  # Basic success check
                "timestamp": datetime.now().isoformat(),
            }

            if result["success"]:
                print(f"✅ Success (Quality: {quality_score:.2f}) - {processing_time:.2f}s")
                print(f"Response preview: {result['response']}")
            else:
                print("❌ Failed - Response too short or empty")

            self.results.append(result)
            return result

        except Exception as e:
            print(f"❌ Error: {e}")
            error_result = {
                "query": query,
                "category": category,
                "description": description,
                "error": str(e),
                "success": False,
                "processing_time": time.time() - start_time,
                "quality_score": 0.0,
                "timestamp": datetime.now().isoformat(),
            }
            self.results.append(error_result)
            return error_result

    async def _test_streaming_endpoint(self, payload: dict[str, Any]) -> str:
        """Test the streaming endpoint and collect full response."""
        url = f"{self.base_url}/api/v2/conversation/{self.conversation_id}/message/stream"

        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}: {await response.text()}")

            full_response = ""
            async for line in response.content:
                if line:
                    line_text = line.decode("utf-8").strip()
                    if line_text.startswith("data: "):
                        try:
                            data = json.loads(line_text[6:])  # Remove 'data: ' prefix
                            if data.get("type") == "token" and "content" in data:
                                full_response += data["content"]
                            elif data.get("type") == "complete":
                                break
                            elif data.get("type") == "error":
                                raise Exception(f"Streaming error: {data.get('error')}")
                        except json.JSONDecodeError:
                            continue

            return full_response

    async def _test_regular_endpoint(self, payload: dict[str, Any]) -> str:
        """Test the regular (non-streaming) endpoint."""
        url = f"{self.base_url}/api/v2/conversation/{self.conversation_id}/message"

        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}: {await response.text()}")

            data = await response.json()
            return data.get("response", "")

    def _analyze_response_quality(self, response: str, query_data: dict[str, Any]) -> float:
        """Analyze the quality of the response based on expected content."""
        if not response:
            return 0.0

        score = 0.0
        response_lower = response.lower()

        # Check for expected topics (40% of score)
        expected_topics = query_data.get("expected_topics", [])
        if expected_topics:
            topics_found = sum(1 for topic in expected_topics if topic.lower() in response_lower)
            score += (topics_found / len(expected_topics)) * 0.4

        # Check response length and structure (30% of score)
        if len(response) > 100:
            score += 0.3
        elif len(response) > 50:
            score += 0.15

        # Check for specific research-related terms (20% of score)
        research_terms = ["project", "research", "funding", "europe", "horizon", "innovation"]
        research_found = sum(1 for term in research_terms if term in response_lower)
        score += (min(research_found, 3) / 3) * 0.2

        # Check for actionable content (10% of score)
        actionable_terms = ["recommend", "suggest", "analyze", "find", "show", "compare"]
        actionable_found = any(term in response_lower for term in actionable_terms)
        if actionable_found:
            score += 0.1

        return min(score, 1.0)

    async def test_memory_functionality(self):
        """Test conversation memory by asking follow-up questions."""
        print("\n🧠 Testing Memory Functionality")

        # First, ask about a specific topic
        initial_query = {
            "query": "Tell me about AI projects in healthcare",
            "category": "memory_test",
            "expected_topics": ["ai", "healthcare"],
            "description": "Initial query for memory test",
        }

        await self.test_conversation_endpoint(initial_query)

        # Then ask a follow-up that requires memory
        followup_query = {
            "query": "What was the total budget for those projects?",
            "category": "memory_test",
            "expected_topics": ["budget", "total"],
            "description": "Follow-up query testing memory",
        }

        await self.test_conversation_endpoint(followup_query)

    async def test_context_endpoint(self):
        """Test the context retrieval endpoint."""
        try:
            url = f"{self.base_url}/api/v2/conversation/{self.conversation_id}/context"
            async with self.session.get(url) as response:
                if response.status == 200:
                    context_data = await response.json()
                    print(
                        f"✅ Context endpoint working - Memory stats: {context_data.get('memory_stats', {})}"
                    )
                else:
                    print(f"❌ Context endpoint failed: {response.status}")
        except Exception as e:
            print(f"❌ Context endpoint error: {e}")

    def generate_report(self) -> dict[str, Any]:
        """Generate a comprehensive test report."""
        if not self.results:
            return {"error": "No test results available"}

        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.get("success", False))
        avg_processing_time = sum(r.get("processing_time", 0) for r in self.results) / total_tests
        avg_quality = sum(r.get("quality_score", 0) for r in self.results) / total_tests

        # Categorize results
        by_category = {}
        for result in self.results:
            category = result.get("category", "unknown")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(result)

        report = {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": successful_tests / total_tests * 100,
                "avg_processing_time": avg_processing_time,
                "avg_quality_score": avg_quality,
                "timestamp": datetime.now().isoformat(),
            },
            "by_category": {},
            "failed_tests": [],
            "recommendations": [],
        }

        # Analyze by category
        for category, tests in by_category.items():
            category_success = sum(1 for t in tests if t.get("success", False))
            category_quality = sum(t.get("quality_score", 0) for t in tests) / len(tests)

            report["by_category"][category] = {
                "total": len(tests),
                "successful": category_success,
                "success_rate": category_success / len(tests) * 100,
                "avg_quality": category_quality,
            }

        # Collect failed tests
        report["failed_tests"] = [
            {
                "query": r["query"],
                "category": r["category"],
                "error": r.get("error", "Unknown failure"),
            }
            for r in self.results
            if not r.get("success", False)
        ]

        # Generate recommendations
        if avg_quality < 0.7:
            report["recommendations"].append(
                "Consider improving response quality - many responses lack expected content"
            )
        if avg_processing_time > 10:
            report["recommendations"].append(
                "Consider optimizing response time - average processing is slow"
            )
        if successful_tests < total_tests * 0.8:
            report["recommendations"].append(
                "System reliability needs improvement - high failure rate detected"
            )

        return report


async def main():
    """Run the comprehensive test suite."""
    print("🚀 Starting Comprehensive FastAPI Conversation AI Test Suite")
    print("=" * 60)

    async with ConversationAITester() as tester:
        # Test health first
        if not await tester.test_health_endpoint():
            print("❌ API is not healthy. Exiting...")
            return

        # Test all research manager queries
        print(f"\n📝 Testing {len(RESEARCH_MANAGER_QUERIES)} research manager queries...")

        for i, query_data in enumerate(RESEARCH_MANAGER_QUERIES, 1):
            print(f"\n--- Test {i}/{len(RESEARCH_MANAGER_QUERIES)} ---")
            await tester.test_conversation_endpoint(query_data, use_streaming=True)

            # Small delay between requests
            await asyncio.sleep(1)

        # Test memory functionality
        await tester.test_memory_functionality()

        # Test context endpoint
        await tester.test_context_endpoint()

        # Generate and display report
        print("\n" + "=" * 60)
        print("📊 TEST REPORT")
        print("=" * 60)

        report = tester.generate_report()

        # Display summary
        summary = report["summary"]
        print(f"✅ Total Tests: {summary['total_tests']}")
        print(f"✅ Successful: {summary['successful_tests']} ({summary['success_rate']:.1f}%)")
        print(f"⏱️  Avg Processing Time: {summary['avg_processing_time']:.2f}s")
        print(f"⭐ Avg Quality Score: {summary['avg_quality_score']:.2f}/1.0")

        # Display category breakdown
        print("\n📋 Results by Category:")
        for category, stats in report["by_category"].items():
            print(
                f"  {category}: {stats['successful']}/{stats['total']} ({stats['success_rate']:.1f}%) - Quality: {stats['avg_quality']:.2f}"
            )

        # Display failures
        if report["failed_tests"]:
            print(f"\n❌ Failed Tests ({len(report['failed_tests'])}):")
            for failure in report["failed_tests"]:
                print(f"  - {failure['category']}: {failure['query']}")
                print(f"    Error: {failure['error']}")

        # Display recommendations
        if report["recommendations"]:
            print("\n💡 Recommendations:")
            for rec in report["recommendations"]:
                print(f"  - {rec}")

        # Save detailed report
        with open("test_report.json", "w") as f:
            json.dump({"report": report, "detailed_results": tester.results}, f, indent=2)

        print("\n💾 Detailed results saved to 'test_report.json'")

        return report


if __name__ == "__main__":
    asyncio.run(main())
