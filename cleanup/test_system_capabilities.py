#!/usr/bin/env python3
"""
Comprehensive test script for the V2 conversational AI wrapper system.
Tests all major categories of questions to verify system functionality.

This script tests the AI streaming endpoint via direct API calls to verify
the system works as intended. Each category represents a different capability
of the AI wrapper.
"""

import asyncio
import json
import aiohttp
import logging
from datetime import datetime
from typing import Dict, Any, List
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemTester:
    """Comprehensive tester for the V2 conversational AI system"""

    def __init__(self, base_url: str = "http://localhost:8000", conversation_id: int = 9999):
        self.base_url = base_url
        self.conversation_id = conversation_id
        self.session = None
        self.test_results = []

        # Test questions covering all major capabilities
        self.test_questions = {
            # Greeting & Basic Interaction
            "greeting": {
                "question": "Hello, how are you?",
                "expected_intent": "conversational",
                "description": "Basic greeting and conversation start"
            },

            # Horizon Europe General Knowledge
            "horizon_europe_info": {
                "question": "What is Horizon Europe and what's its budget?",
                "expected_intent": "conversational",
                "description": "General knowledge about Horizon Europe programme"
            },

            # Funding Call Search
            "call_search": {
                "question": "Find open calls for artificial intelligence research",
                "expected_intent": "search_calls",
                "description": "Search for current funding opportunities"
            },

            # Project Search (CORDIS)
            "project_search": {
                "question": "Search for completed projects about renewable energy",
                "expected_intent": "search_projects",
                "description": "Search for past EU research projects"
            },

            # Call Document Specific Query
            "call_specific": {
                "question": "What are the eligibility criteria for HORIZON-CL3-2025-02-CS-ECCC-01?",
                "expected_intent": "call_document",
                "description": "Specific question about a particular call"
            },

            # Country Eligibility Question
            "country_eligibility": {
                "question": "Can researchers from Switzerland apply for Horizon Europe funding?",
                "expected_intent": "conversational",
                "description": "Country-specific eligibility information"
            },

            # Application Process Query
            "application_process": {
                "question": "How do I apply for a Horizon Europe grant?",
                "expected_intent": "conversational",
                "description": "Application guidance and process information"
            },

            # Budget & Funding Information
            "budget_info": {
                "question": "What are the typical funding rates for different types of projects?",
                "expected_intent": "conversational",
                "description": "Budget and funding rate information"
            },

            # Technology/Digital Focus
            "technology_focus": {
                "question": "What funding opportunities exist for quantum computing research?",
                "expected_intent": "search_calls",
                "description": "Technology-specific funding opportunities"
            },

            # Climate & Environment
            "climate_focus": {
                "question": "Show me climate change adaptation projects",
                "expected_intent": "search_projects",
                "description": "Environmental and climate-related projects"
            },

            # Health Research
            "health_research": {
                "question": "What health research areas are prioritized?",
                "expected_intent": "conversational",
                "description": "Health research priorities and information"
            },

            # Partnership & Collaboration
            "collaboration": {
                "question": "How can I find research partners in Germany?",
                "expected_intent": "conversational",
                "description": "Partnership and collaboration guidance"
            },

            # Success Stories & Examples
            "success_stories": {
                "question": "Show me successful AI projects that received funding",
                "expected_intent": "search_projects",
                "description": "Success stories and case studies"
            },

            # Deadline Information
            "deadline_query": {
                "question": "What are the upcoming deadlines for energy research calls?",
                "expected_intent": "search_calls",
                "description": "Deadline and timing information"
            },

            # Complex Multi-part Query
            "complex_query": {
                "question": "I'm a researcher from Spain interested in applying for renewable energy funding. What calls are available and what are the success rates?",
                "expected_intent": "search_calls",
                "description": "Complex query with multiple components"
            }
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def test_streaming_endpoint(self, question: str, category: str) -> Dict[str, Any]:
        """Test the streaming endpoint with a question"""

        url = f"{self.base_url}/api/v2/conversation/{self.conversation_id}/message/stream"
        payload = {
            "message": question,
            "include_context": True,
            "memory_strategy": "full"
        }

        start_time = datetime.now()
        response_chunks = []
        metadata = {}

        try:
            logger.info(f"🧪 Testing {category}: '{question[:50]}...'")

            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "category": category,
                        "question": question,
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "chunks_received": 0,
                        "processing_time": 0
                    }

                # Process streaming response
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        try:
                            chunk_data = json.loads(data_str)
                            response_chunks.append(chunk_data)

                            # Extract metadata from completion event
                            if chunk_data.get('type') == 'complete':
                                metadata = chunk_data
                                break

                        except json.JSONDecodeError:
                            continue

                processing_time = (datetime.now() - start_time).total_seconds()

                # Analyze response
                success = len(response_chunks) > 0 and metadata.get('success', True)

                return {
                    "category": category,
                    "question": question,
                    "success": success,
                    "chunks_received": len(response_chunks),
                    "processing_time": processing_time,
                    "metadata": metadata,
                    "response_preview": self._extract_response_preview(response_chunks)
                }

        except Exception as e:
            logger.error(f"Error testing {category}: {e}")
            return {
                "category": category,
                "question": question,
                "success": False,
                "error": str(e),
                "chunks_received": 0,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

    def _extract_response_preview(self, chunks: List[Dict]) -> str:
        """Extract response preview from chunks"""
        response_parts = []
        for chunk in chunks:
            if chunk.get('type') == 'token':
                response_parts.append(chunk.get('content', ''))
        return ''.join(response_parts)[:200] + "..." if response_parts else "No response content"

    async def run_all_tests(self):
        """Run all test categories"""
        logger.info("🚀 Starting comprehensive system test...")
        logger.info(f"📍 Testing against: {self.base_url}")
        logger.info(f"💬 Conversation ID: {self.conversation_id}")

        # Clear conversation memory first
        await self._clear_conversation()

        # Test each category
        for category, test_data in self.test_questions.items():
            result = await self.test_streaming_endpoint(
                test_data["question"],
                category
            )

            result["expected_intent"] = test_data["expected_intent"]
            result["description"] = test_data["description"]

            self.test_results.append(result)

            # Brief pause between tests
            await asyncio.sleep(1)

        # Generate summary
        self._print_summary()

    async def _clear_conversation(self):
        """Clear conversation memory for clean testing"""
        try:
            url = f"{self.base_url}/api/v2/conversation/{self.conversation_id}/memory"
            async with self.session.delete(url) as response:
                if response.status == 200:
                    logger.info("🧹 Cleared conversation memory")
        except Exception as e:
            logger.warning(f"Could not clear conversation memory: {e}")

    def _print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE SYSTEM TEST SUMMARY")
        print("="*80)

        successful_tests = sum(1 for r in self.test_results if r["success"])
        total_tests = len(self.test_results)

        print(f"📊 Overall Success Rate: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"⏱️  Total Testing Time: {sum(r['processing_time'] for r in self.test_results):.2f}s")

        print(f"\n📋 DETAILED RESULTS:")
        print("-"*80)

        for result in self.test_results:
            status_icon = "✅" if result["success"] else "❌"
            time_icon = "⚡" if result["processing_time"] < 3 else "🐌" if result["processing_time"] > 10 else "🕐"

            print(f"{status_icon} {result['category'].upper()}")
            print(f"   📝 Question: {result['question']}")
            print(f"   📖 Description: {result['description']}")
            print(f"   🎯 Expected Intent: {result['expected_intent']}")
            print(f"   {time_icon} Processing Time: {result['processing_time']:.2f}s")
            print(f"   📦 Chunks Received: {result['chunks_received']}")

            if result["success"]:
                metadata = result.get("metadata", {})
                if metadata:
                    print(f"   🤖 AI Provider: {metadata.get('ai_provider', 'Unknown')}")
                    print(f"   📊 Data Source: {metadata.get('data_source', 'Unknown')}")
                    print(f"   🎯 Projects Found: {metadata.get('projects_found', 0)}")

                print(f"   💬 Response Preview: {result['response_preview']}")
            else:
                print(f"   ❌ Error: {result.get('error', 'Unknown error')}")

            print()

        # System health check
        print("🏥 SYSTEM HEALTH CHECK")
        print("-"*40)
        asyncio.create_task(self._check_system_health())

    async def _check_system_health(self):
        """Check system health endpoint"""
        try:
            url = f"{self.base_url}/api/v2/conversation/health"
            async with self.session.get(url) as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"   Status: {health_data.get('status', 'Unknown')}")

                    components = health_data.get('components', {})
                    for component, status in components.items():
                        icon = "✅" if status else "❌"
                        print(f"   {icon} {component.title()}: {'OK' if status else 'ERROR'}")
                else:
                    print(f"   ❌ Health check failed: HTTP {response.status}")
        except Exception as e:
            print(f"   ❌ Health check error: {e}")

async def main():
    """Main test execution"""
    # Check if server is running
    base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")

    print("🔍 V2 Conversational AI System Tester")
    print("="*50)
    print(f"🌐 Testing server at: {base_url}")

    # Quick health check before starting
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/api/v2/conversation/health") as response:
                if response.status != 200:
                    print(f"❌ Server health check failed. Is the server running at {base_url}?")
                    sys.exit(1)

                health = await response.json()
                print(f"✅ Server health: {health.get('status', 'Unknown')}")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please ensure the server is running before executing this test.")
        sys.exit(1)

    # Run comprehensive tests
    async with SystemTester(base_url=base_url) as tester:
        await tester.run_all_tests()

    print("\n🎉 Testing completed! Review the summary above to verify system functionality.")

if __name__ == "__main__":
    asyncio.run(main())