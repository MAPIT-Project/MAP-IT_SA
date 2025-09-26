#!/usr/bin/env python3
"""
Direct endpoint testing without async to understand the current system capabilities.
This will help identify issues and improve the conversation AI.
"""

import json
import time
import requests
from typing import Dict, Any
import subprocess
import sys
import os

# Add current directory to path
sys.path.insert(0, '/home/anmar/Documents/VSCODE_REPOS/MAP-IT_SA-1')

def start_server_in_background():
    """Start the FastAPI server in the background."""
    print("🚀 Starting FastAPI server...")
    
    # Change to project directory
    os.chdir('/home/anmar/Documents/VSCODE_REPOS/MAP-IT_SA-1')
    
    # Start server using subprocess
    try:
        # Try to start with uvicorn directly
        cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
        print(f"Running: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Wait a bit for server to start
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Server appears to be starting...")
            return process
        else:
            print("❌ Server failed to start")
            if process.stdout:
                output = process.stdout.read()
                print(f"Output: {output}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return None

def test_health_endpoint(base_url: str = "http://localhost:8000") -> bool:
    """Test the health endpoint."""
    try:
        response = requests.get(f"{base_url}/api/v2/conversation/health", timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {health_data.get('status', 'unknown')}")
            print(f"Components: {health_data.get('components', {})}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check connection error: {e}")
        return False

def test_conversation_endpoint(query: str, conversation_id: int = 1, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Test a conversation query using the regular endpoint."""
    
    print(f"\n🔍 Testing query: '{query}'")
    
    url = f"{base_url}/api/v2/conversation/{conversation_id}/message"
    payload = {
        "message": query,
        "include_context": True,
        "memory_strategy": "full",
        "tools_enabled": ["search", "analysis", "retrieval"]
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=60)
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! ({processing_time:.2f}s)")
            print(f"Response length: {len(data.get('response', ''))} chars")
            print(f"Processing time: {data.get('processing_time_ms', 0)} ms")
            print(f"Memory used: {data.get('memory_used', {})}")
            print(f"Retrieval stats: {data.get('retrieval_stats', {})}")
            print(f"Tools executed: {data.get('tools_executed', [])}")
            print(f"Confidence: {data.get('confidence', 0.0)}")
            print(f"Grounded: {data.get('grounded', False)}")
            print(f"Response preview: {data.get('response', '')[:300]}...")
            
            return {
                "success": True,
                "data": data,
                "processing_time": processing_time
            }
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "details": response.text
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return {
            "success": False,
            "error": "Request failed",
            "details": str(e)
        }

def test_streaming_endpoint(query: str, conversation_id: int = 1, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Test a conversation query using the streaming endpoint."""
    
    print(f"\n🎬 Testing streaming query: '{query}'")
    
    url = f"{base_url}/api/v2/conversation/{conversation_id}/message/stream"
    payload = {
        "message": query,
        "include_context": True,
        "memory_strategy": "full",
        "tools_enabled": ["search", "analysis", "retrieval"]
    }
    
    try:
        start_time = time.time()
        
        with requests.post(url, json=payload, stream=True, timeout=60) as response:
            if response.status_code != 200:
                print(f"❌ Streaming error {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "details": response.text
                }
            
            full_response = ""
            events_received = 0
            
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8').strip()
                    if line_text.startswith('data: '):
                        try:
                            data = json.loads(line_text[6:])  # Remove 'data: ' prefix
                            events_received += 1
                            
                            if data.get('type') == 'token' and 'content' in data:
                                full_response += data['content']
                            elif data.get('type') == 'complete':
                                break
                            elif data.get('type') == 'error':
                                print(f"❌ Streaming error: {data.get('error')}")
                                return {
                                    "success": False,
                                    "error": "Streaming error",
                                    "details": data.get('error')
                                }
                        except json.JSONDecodeError:
                            continue
            
            processing_time = time.time() - start_time
            
            print(f"✅ Streaming success! ({processing_time:.2f}s)")
            print(f"Events received: {events_received}")
            print(f"Response length: {len(full_response)} chars")
            print(f"Response preview: {full_response[:300]}...")
            
            return {
                "success": True,
                "response": full_response,
                "processing_time": processing_time,
                "events_received": events_received
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Streaming request failed: {e}")
        return {
            "success": False,
            "error": "Streaming request failed",
            "details": str(e)
        }

def run_comprehensive_tests():
    """Run comprehensive tests for research manager queries."""
    
    # Research manager test queries
    test_queries = [
        "What is Horizon Europe?",
        "Find AI and machine learning projects in healthcare",
        "Show me renewable energy projects funded in 2023",
        "What is the total budget for climate change projects?",
        "Which countries receive the most Horizon Europe funding?",
        "What are the trending research topics in quantum computing?",
        "Compare digital transformation projects between Germany and France",
        "Find collaborative projects between universities and industry",
        "What are the most successful projects in biotechnology?",
        "Analyze the impact of COVID-19 on European research funding priorities"
    ]
    
    base_url = "http://localhost:8000"
    
    # First test health
    if not test_health_endpoint(base_url):
        print("❌ Server is not healthy. Cannot proceed with tests.")
        return
    
    print(f"\n📋 Running {len(test_queries)} test queries...")
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test {i}/{len(test_queries)} ---")
        
        # Test regular endpoint
        result = test_conversation_endpoint(query, conversation_id=1, base_url=base_url)
        result["query"] = query
        result["test_number"] = i
        result["endpoint_type"] = "regular"
        results.append(result)
        
        # Small delay between tests
        time.sleep(2)
    
    # Summary
    successful_tests = sum(1 for r in results if r.get("success", False))
    total_tests = len(results)
    
    print(f"\n" + "="*60)
    print(f"📊 TEST SUMMARY")
    print(f"="*60)
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
    print(f"Failed: {total_tests - successful_tests}")
    
    # Show failed tests
    failed_tests = [r for r in results if not r.get("success", False)]
    if failed_tests:
        print(f"\n❌ Failed tests:")
        for test in failed_tests:
            print(f"  - Test {test['test_number']}: {test['query']}")
            print(f"    Error: {test.get('error', 'Unknown error')}")
    
    # Show success rate by processing time
    successful_results = [r for r in results if r.get("success", False)]
    if successful_results:
        avg_time = sum(r.get("processing_time", 0) for r in successful_results) / len(successful_results)
        print(f"\n⏱️  Average processing time: {avg_time:.2f}s")
    
    return results

def main():
    """Main test function."""
    print("🧪 FastAPI Conversation AI Testing Suite")
    print("="*50)
    
    # Check if server is already running
    if test_health_endpoint():
        print("✅ Server is already running!")
    else:
        print("🚀 Starting server...")
        server_process = start_server_in_background()
        
        if server_process:
            # Wait for server to fully start
            print("⏳ Waiting for server to be ready...")
            max_retries = 30
            for i in range(max_retries):
                time.sleep(2)
                if test_health_endpoint():
                    print("✅ Server is ready!")
                    break
                print(f"   Still waiting... ({i+1}/{max_retries})")
            else:
                print("❌ Server failed to start properly")
                return
        else:
            print("❌ Could not start server")
            return
    
    # Run tests
    try:
        results = run_comprehensive_tests()
        
        # Save results
        with open("test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Test results saved to 'test_results.json'")
        
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()