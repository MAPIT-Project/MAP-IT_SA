#!/usr/bin/env python3
"""
Simple comprehensive test script for the V2 conversational AI wrapper system.
Tests all major categories of questions using standard library only.

This script tests the AI streaming endpoint via direct API calls to verify
the system works as intended. Each category represents a different capability
of the AI wrapper.
"""

import asyncio
import json
import urllib.request
import urllib.parse
import urllib.error
import logging
from datetime import datetime
from typing import Dict, Any, List
import sys
import os
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleSystemTester:
    """Simple tester for the V2 conversational AI system using standard library"""

    def __init__(self, base_url: str = "http://localhost:8000", conversation_id: int = 9999):
        self.base_url = base_url
        self.conversation_id = conversation_id
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

    def make_http_request(self, url: str, data: Dict = None, method: str = "GET") -> Dict[str, Any]:
        """Make HTTP request using standard library"""
        try:
            if method == "POST" and data:
                json_data = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(
                    url,
                    data=json_data,
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'text/event-stream'
                    }
                )
            else:
                req = urllib.request.Request(
                    url,
                    headers={'Accept': 'application/json'}
                )

            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode('utf-8')

                if response.status == 200:
                    try:
                        return {
                            'success': True,
                            'data': json.loads(response_data),
                            'status_code': response.status
                        }
                    except json.JSONDecodeError:
                        return {
                            'success': True,
                            'data': response_data,
                            'status_code': response.status
                        }
                else:
                    return {
                        'success': False,
                        'error': f"HTTP {response.status}: {response_data}",
                        'status_code': response.status
                    }

        except urllib.error.URLError as e:
            return {
                'success': False,
                'error': f"Network error: {str(e)}",
                'status_code': 0
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Request error: {str(e)}",
                'status_code': 0
            }

    def test_non_streaming_endpoint(self, question: str, category: str) -> Dict[str, Any]:
        """Test the non-streaming endpoint with a question"""

        url = f"{self.base_url}/api/v2/conversation/{self.conversation_id}/message"
        payload = {
            "message": question,
            "include_context": True,
            "memory_strategy": "full"
        }

        start_time = datetime.now()

        try:
            logger.info(f"🧪 Testing {category}: '{question[:50]}...'")

            result = self.make_http_request(url, payload, "POST")

            processing_time = (datetime.now() - start_time).total_seconds()

            if result['success']:
                response_data = result['data']
                response_preview = response_data.get('response', '')[:200] + "..." if len(response_data.get('response', '')) > 200 else response_data.get('response', '')

                return {
                    "category": category,
                    "question": question,
                    "success": True,
                    "processing_time": processing_time,
                    "response_data": response_data,
                    "response_preview": response_preview,
                    "tools_executed": response_data.get('tools_executed', False),
                    "confidence": response_data.get('confidence', 0.0),
                    "grounded": response_data.get('grounded', False),
                    "citations": response_data.get('citations', [])
                }
            else:
                return {
                    "category": category,
                    "question": question,
                    "success": False,
                    "error": result.get('error', 'Unknown error'),
                    "processing_time": processing_time
                }

        except Exception as e:
            logger.error(f"Error testing {category}: {e}")
            return {
                "category": category,
                "question": question,
                "success": False,
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

    def run_all_tests(self):
        """Run all test categories"""
        logger.info("🚀 Starting comprehensive system test...")
        logger.info(f"📍 Testing against: {self.base_url}")
        logger.info(f"💬 Conversation ID: {self.conversation_id}")

        # Check system health first
        health_check = self._check_system_health()
        if not health_check['success']:
            print(f"❌ System health check failed: {health_check.get('error')}")
            return

        print(f"✅ System health: {health_check.get('data', {}).get('status', 'Unknown')}")

        # Clear conversation memory first
        self._clear_conversation()

        # Test each category
        for i, (category, test_data) in enumerate(self.test_questions.items(), 1):
            print(f"\n📝 [{i}/{len(self.test_questions)}] Testing {category}...")
            result = self.test_non_streaming_endpoint(
                test_data["question"],
                category
            )

            result["expected_intent"] = test_data["expected_intent"]
            result["description"] = test_data["description"]

            self.test_results.append(result)

            # Brief pause between tests
            time.sleep(1)

        # Generate summary
        self._print_summary()

    def _clear_conversation(self):
        """Clear conversation memory for clean testing"""
        try:
            url = f"{self.base_url}/api/v2/conversation/{self.conversation_id}/memory"
            result = self.make_http_request(url, method="DELETE")
            if result['success']:
                logger.info("🧹 Cleared conversation memory")
            else:
                logger.warning(f"Could not clear conversation memory: {result.get('error')}")
        except Exception as e:
            logger.warning(f"Could not clear conversation memory: {e}")

    def _check_system_health(self) -> Dict[str, Any]:
        """Check system health endpoint"""
        try:
            url = f"{self.base_url}/api/v2/conversation/health"
            return self.make_http_request(url)
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

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

            if result["success"]:
                print(f"   🔧 Tools Executed: {result['tools_executed']}")
                print(f"   🎯 Confidence: {result['confidence']:.2f}")
                print(f"   📚 Grounded: {result['grounded']}")
                print(f"   📄 Citations: {len(result['citations'])}")
                print(f"   💬 Response Preview: {result['response_preview']}")
            else:
                print(f"   ❌ Error: {result.get('error', 'Unknown error')}")

            print()

        # System capabilities analysis
        print("🔍 SYSTEM CAPABILITIES ANALYSIS")
        print("-"*40)

        tool_based_tests = [r for r in self.test_results if r.get('tools_executed', False)]
        conversational_tests = [r for r in self.test_results if r['success'] and not r.get('tools_executed', False)]

        print(f"   🔧 Tool-based responses: {len(tool_based_tests)}")
        print(f"   💬 Conversational responses: {len(conversational_tests)}")
        print(f"   📚 Average confidence: {sum(r.get('confidence', 0) for r in self.test_results if r['success']) / max(len([r for r in self.test_results if r['success']]), 1):.2f}")

        if tool_based_tests:
            avg_tool_time = sum(r['processing_time'] for r in tool_based_tests) / len(tool_based_tests)
            print(f"   ⏱️  Avg tool response time: {avg_tool_time:.2f}s")

        if conversational_tests:
            avg_conv_time = sum(r['processing_time'] for r in conversational_tests) / len(conversational_tests)
            print(f"   ⏱️  Avg conversational time: {avg_conv_time:.2f}s")

def main():
    """Main test execution"""
    # Check if server is running
    base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")

    print("🔍 V2 Conversational AI System Tester")
    print("="*50)
    print(f"🌐 Testing server at: {base_url}")

    # Quick health check before starting
    try:
        tester = SimpleSystemTester(base_url=base_url)
        health_check = tester._check_system_health()

        if not health_check['success']:
            print(f"❌ Server health check failed: {health_check.get('error')}")
            print("Please ensure the server is running before executing this test.")
            sys.exit(1)

        health_data = health_check.get('data', {})
        print(f"✅ Server health: {health_data.get('status', 'Unknown')}")

        components = health_data.get('components', {})
        if components:
            for component, status in components.items():
                icon = "✅" if status else "❌"
                print(f"   {icon} {component.title()}: {'OK' if status else 'ERROR'}")

    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please ensure the server is running before executing this test.")
        sys.exit(1)

    # Run comprehensive tests
    tester = SimpleSystemTester(base_url=base_url)
    tester.run_all_tests()

    print("\n🎉 Testing completed! Review the summary above to verify system functionality.")
    print("\n💡 Tips for using this test:")
    print("   - Run this script whenever you make changes to verify the system still works")
    print("   - Check that tool-based responses work for search queries")
    print("   - Verify conversational responses work for general questions")
    print("   - Monitor processing times to detect performance issues")
    print("   - Ensure all major capabilities are functioning")

if __name__ == "__main__":
    main()