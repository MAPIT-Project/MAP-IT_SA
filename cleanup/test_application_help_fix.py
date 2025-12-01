#!/usr/bin/env python3
"""
Targeted test for the application_help fix.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import logging
from datetime import datetime
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def make_http_request(url: str, data: dict = None, method: str = "GET") -> dict:
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

        with urllib.request.urlopen(req, timeout=30) as response:
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

def test_application_help():
    """Test the application_help question specifically"""
    base_url = "http://localhost:8000"
    conversation_id = 12345

    print("🧪 Testing Application Help Fix")
    print("="*50)

    # Health check first
    print("\n🏥 Health check...")
    health_result = make_http_request(f"{base_url}/api/v2/conversation/health")
    if not health_result['success']:
        print(f"❌ Health check failed: {health_result.get('error')}")
        return False

    print("✅ System health OK")

    # Clear memory
    print("\n🧹 Clearing memory...")
    clear_result = make_http_request(f"{base_url}/api/v2/conversation/{conversation_id}/memory", method="DELETE")
    if clear_result['success']:
        print("✅ Memory cleared")

    # Test application help question
    question = "How do I apply for funding?"
    print(f"\n📝 Testing: '{question}'")

    url = f"{base_url}/api/v2/conversation/{conversation_id}/message"
    payload = {
        "message": question,
        "include_context": True,
        "memory_strategy": "full"
    }

    start_time = datetime.now()
    result = make_http_request(url, payload, "POST")
    processing_time = (datetime.now() - start_time).total_seconds()

    if result['success']:
        response_data = result['data']
        response_preview = response_data.get('response', '')[:200] + "..." if len(response_data.get('response', '')) > 200 else response_data.get('response', '')

        print(f"✅ Success in {processing_time:.1f}s")
        print(f"   Tools executed: {response_data.get('tools_executed', False)}")
        print(f"   Confidence: {response_data.get('confidence', 0.0):.2f}")
        print(f"   Response: {response_preview}")

        # Check if the response is the expected enhanced fallback
        response_text = response_data.get('response', '')
        if len(response_text) > 100 and 'application process' in response_text.lower():
            print("🎉 SUCCESS: Got comprehensive application help response!")
            return True
        else:
            print("⚠️ WARNING: Response may not be the enhanced fallback")
            print(f"   Full response: {response_text}")
            return False
    else:
        print(f"❌ Failed: {result.get('error')}")
        return False

if __name__ == "__main__":
    success = test_application_help()
    if success:
        print("\n🎉 Application help fix verified!")
    else:
        print("\n❌ Application help fix failed!")