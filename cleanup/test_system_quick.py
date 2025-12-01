#!/usr/bin/env python3
"""
Quick test script for the V2 conversational AI wrapper system.
Tests key categories of questions to verify system functionality quickly.

This script provides a fast way to verify the system is working properly
by testing one question from each major capability category.
"""

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

def make_http_request(url: str, data: Dict = None, method: str = "GET") -> Dict[str, Any]:
    """Make HTTP request using standard library"""
    try:
        if method == "POST" and data:
            json_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=json_data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
        else:
            req = urllib.request.Request(
                url,
                headers={'Accept': 'application/json'}
            )

        with urllib.request.urlopen(req, timeout=60) as response:
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

def test_endpoint(base_url: str, conversation_id: int, question: str, category: str) -> Dict[str, Any]:
    """Test the endpoint with a question"""

    url = f"{base_url}/api/v2/conversation/{conversation_id}/message"
    payload = {
        "message": question,
        "include_context": True,
        "memory_strategy": "full"
    }

    start_time = datetime.now()

    try:
        logger.info(f"🧪 Testing {category}: '{question}'")

        result = make_http_request(url, payload, "POST")

        processing_time = (datetime.now() - start_time).total_seconds()

        if result['success']:
            response_data = result['data']
            response_preview = response_data.get('response', '')[:150] + "..." if len(response_data.get('response', '')) > 150 else response_data.get('response', '')

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

def main():
    """Main test execution"""
    base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
    conversation_id = 9999

    print("🔍 V2 Conversational AI System - Quick Test")
    print("="*50)
    print(f"🌐 Testing server at: {base_url}")
    print(f"💬 Conversation ID: {conversation_id}")

    # Quick health check
    print("\n🏥 Checking system health...")
    health_result = make_http_request(f"{base_url}/api/v2/conversation/health")

    if not health_result['success']:
        print(f"❌ Health check failed: {health_result.get('error')}")
        print("Please ensure the server is running before executing this test.")
        sys.exit(1)

    health_data = health_result.get('data', {})
    print(f"✅ System health: {health_data.get('status', 'Unknown')}")

    components = health_data.get('components', {})
    if components:
        for component, status in components.items():
            icon = "✅" if status else "❌"
            print(f"   {icon} {component.title()}: {'OK' if status else 'ERROR'}")

    # Clear conversation memory
    print("\n🧹 Clearing conversation memory...")
    clear_result = make_http_request(f"{base_url}/api/v2/conversation/{conversation_id}/memory", method="DELETE")
    if clear_result['success']:
        print("✅ Memory cleared")
    else:
        print(f"⚠️ Could not clear memory: {clear_result.get('error')}")

    # Key test questions (one from each major category)
    key_tests = [
        {
            "category": "greeting",
            "question": "Hello, what can you help me with?",
            "description": "Basic greeting"
        },
        {
            "category": "horizon_info",
            "question": "What is Horizon Europe?",
            "description": "General programme information"
        },
        {
            "category": "call_search",
            "question": "Find open calls for AI research",
            "description": "Funding opportunity search"
        },
        {
            "category": "project_search",
            "question": "Show me renewable energy projects",
            "description": "Project search"
        },
        {
            "category": "application_help",
            "question": "How do I apply for funding?",
            "description": "Application guidance"
        }
    ]

    print(f"\n🧪 Running {len(key_tests)} key tests...")
    print("-"*50)

    test_results = []

    for i, test in enumerate(key_tests, 1):
        print(f"\n[{i}/{len(key_tests)}] Testing {test['category']}...")

        result = test_endpoint(base_url, conversation_id, test['question'], test['category'])
        result["description"] = test["description"]
        test_results.append(result)

        if result["success"]:
            status_icon = "✅"
            time_icon = "⚡" if result["processing_time"] < 5 else "🕐"

            print(f"{status_icon} Success in {result['processing_time']:.1f}s {time_icon}")
            print(f"   Tools: {'Yes' if result['tools_executed'] else 'No'}")
            print(f"   Confidence: {result['confidence']:.2f}")
            print(f"   Response: {result['response_preview']}")
        else:
            print(f"❌ Failed: {result['error']}")

        # Brief pause between tests
        time.sleep(1)

    # Summary
    print("\n" + "="*60)
    print("📊 QUICK TEST SUMMARY")
    print("="*60)

    successful_tests = sum(1 for r in test_results if r["success"])
    total_tests = len(test_results)

    print(f"🎯 Success Rate: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")

    if successful_tests == total_tests:
        print("🎉 ALL TESTS PASSED! System is working correctly.")
    elif successful_tests > 0:
        print("⚠️ Some tests passed. System partially working.")
    else:
        print("❌ ALL TESTS FAILED! System needs attention.")

    print(f"\n⏱️ Performance:")
    total_time = sum(r['processing_time'] for r in test_results)
    avg_time = total_time / total_tests if total_tests > 0 else 0
    print(f"   Total time: {total_time:.1f}s")
    print(f"   Average per request: {avg_time:.1f}s")

    print(f"\n🔧 Tool-based responses: {sum(1 for r in test_results if r.get('tools_executed', False))}")
    print(f"💬 Conversational responses: {sum(1 for r in test_results if r['success'] and not r.get('tools_executed', False))}")

    print(f"\n🎯 Key capabilities tested:")
    for test in key_tests:
        result = next((r for r in test_results if r['category'] == test['category']), None)
        status = "✅" if result and result['success'] else "❌"
        print(f"   {status} {test['description']}")

    print(f"\n💡 Usage: Run this script to quickly verify system functionality.")
    print(f"   If all tests pass, the system is working as intended.")

if __name__ == "__main__":
    main()