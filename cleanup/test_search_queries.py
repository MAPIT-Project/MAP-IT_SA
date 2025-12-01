#!/usr/bin/env python3
"""
Simple test to check if search queries are working with tools
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import time
from typing import Dict, Any

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
                return {
                    'success': True,
                    'data': json.loads(response_data),
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

def test_search_query(base_url: str, conversation_id: int, question: str, description: str):
    """Test a single search query"""
    print(f"\n🔍 Testing: {description}")
    print(f"   Question: '{question}'")

    url = f"{base_url}/api/v2/conversation/{conversation_id}/message"
    payload = {
        "message": question,
        "include_context": True,
        "memory_strategy": "full"
    }

    start_time = time.time()
    result = make_http_request(url, payload, "POST")
    processing_time = time.time() - start_time

    if result['success']:
        response_data = result['data']
        tools_executed = response_data.get('tools_executed', False)
        confidence = response_data.get('confidence', 0.0)
        response_preview = response_data.get('response', '')[:100] + "..." if len(response_data.get('response', '')) > 100 else response_data.get('response', '')

        print(f"   ✅ Success in {processing_time:.1f}s")
        print(f"   🔧 Tools executed: {tools_executed}")
        print(f"   🎯 Confidence: {confidence:.2f}")
        print(f"   💬 Response: {response_preview}")

        return tools_executed
    else:
        print(f"   ❌ Failed: {result.get('error')}")
        return False

def main():
    base_url = "http://localhost:8000"
    conversation_id = 12345

    print("🔍 Search Query Test")
    print("=" * 50)

    # Clear conversation
    print("\n🧹 Clearing conversation...")
    clear_result = make_http_request(f"{base_url}/api/v2/conversation/{conversation_id}/memory", method="DELETE")
    if clear_result['success']:
        print("✅ Memory cleared")
    else:
        print(f"⚠️ Could not clear memory: {clear_result.get('error')}")

    # Test search queries
    search_tests = [
        ("Find open calls for AI research", "Call Search Query"),
        ("Show me renewable energy projects", "Project Search Query"),
    ]

    tool_execution_count = 0
    for question, description in search_tests:
        tools_executed = test_search_query(base_url, conversation_id, question, description)
        if tools_executed:
            tool_execution_count += 1
        time.sleep(2)  # Brief pause between tests

    # Summary
    print(f"\n📊 Results:")
    print(f"   Total search queries tested: {len(search_tests)}")
    print(f"   Queries that executed tools: {tool_execution_count}")
    print(f"   Success rate: {tool_execution_count/len(search_tests)*100:.1f}%")

    if tool_execution_count == len(search_tests):
        print("🎉 All search queries are working correctly with tools!")
    else:
        print("⚠️ Some search queries are not executing tools as expected.")

if __name__ == "__main__":
    main()