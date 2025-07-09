#!/usr/bin/env python3
"""
Test script to verify true concurrent processing with Celery.
This script sends multiple requests simultaneously and measures if they're processed concurrently.
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import List, Dict, Any
import json

# Test configuration
API_BASE_URL = "http://localhost:8000"
CONCURRENT_REQUESTS = 3
TEST_QUESTIONS = [
    "What are recent AI projects in healthcare?",
    "European renewable energy research projects",
    "Quantum computing projects in Germany",
    "Automotive technology projects in Italy",
    "Cybersecurity research in France"
]

async def send_request(session: aiohttp.ClientSession, question: str, request_id: int) -> Dict[str, Any]:
    """Send a single API request and measure response time."""
    
    payload = {
        "question": question,
        "ai_version": "V8",
        "max_results": 3
    }
    
    start_time = time.time()
    print(f"🚀 [{request_id}] Started: {question[:50]}... at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    
    try:
        async with session.post(
            f"{API_BASE_URL}/api/query",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        ) as response:
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.status == 200:
                result = await response.json()
                print(f"✅ [{request_id}] Completed: {duration:.2f}s - {question[:50]}...")
                
                return {
                    "request_id": request_id,
                    "question": question,
                    "duration": duration,
                    "success": True,
                    "answer_length": len(result.get("answer", "")),
                    "ai_provider": result.get("ai_provider"),
                    "data_source": result.get("data_source"),
                    "projects_found": result.get("projects_found", 0),
                    "start_time": start_time,
                    "end_time": end_time
                }
            else:
                error_text = await response.text()
                print(f"❌ [{request_id}] Failed ({response.status}): {error_text[:100]}...")
                
                return {
                    "request_id": request_id,
                    "question": question,
                    "duration": duration,
                    "success": False,
                    "error": f"HTTP {response.status}: {error_text}",
                    "start_time": start_time,
                    "end_time": end_time
                }
                
    except asyncio.TimeoutError:
        duration = time.time() - start_time
        print(f"⏰ [{request_id}] Timeout after {duration:.2f}s: {question[:50]}...")
        
        return {
            "request_id": request_id,
            "question": question,
            "duration": duration,
            "success": False,
            "error": "Request timeout",
            "start_time": start_time,
            "end_time": time.time()
        }
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"💥 [{request_id}] Error after {duration:.2f}s: {str(e)}")
        
        return {
            "request_id": request_id,
            "question": question,
            "duration": duration,
            "success": False,
            "error": str(e),
            "start_time": start_time,
            "end_time": time.time()
        }

async def test_concurrent_processing():
    """Test concurrent processing by sending multiple requests simultaneously."""
    
    print("🧪 Testing Concurrent Processing with Celery")
    print("=" * 60)
    
    # Check API health first
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/") as response:
                if response.status != 200:
                    print(f"❌ API not available. Status: {response.status}")
                    return
                print("✅ API is available")
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return
    
    # Select questions for testing
    questions = TEST_QUESTIONS[:CONCURRENT_REQUESTS]
    
    print(f"\n🎯 Sending {len(questions)} concurrent requests...")
    print("-" * 60)
    
    # Record overall start time
    overall_start = time.time()
    
    # Send all requests concurrently
    async with aiohttp.ClientSession() as session:
        tasks = [
            send_request(session, question, i + 1) 
            for i, question in enumerate(questions)
        ]
        
        # Wait for all requests to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    overall_end = time.time()
    overall_duration = overall_end - overall_start
    
    print("-" * 60)
    print(f"⏱️  Total time for {len(questions)} requests: {overall_duration:.2f}s")
    print("=" * 60)
    
    # Analyze results
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success", False)]
    failed_results = [r for r in results if isinstance(r, dict) and not r.get("success", False)]
    exceptions = [r for r in results if not isinstance(r, dict)]
    
    print("\n📊 Results Analysis:")
    print("-" * 30)
    print(f"✅ Successful requests: {len(successful_results)}")
    print(f"❌ Failed requests: {len(failed_results)}")
    print(f"💥 Exceptions: {len(exceptions)}")
    
    if successful_results:
        durations = [r["duration"] for r in successful_results]
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        print(f"\n⏱️  Performance Metrics:")
        print(f"   Average response time: {avg_duration:.2f}s")
        print(f"   Fastest response: {min_duration:.2f}s")
        print(f"   Slowest response: {max_duration:.2f}s")
        
        # Check for true concurrency
        start_times = [r["start_time"] for r in successful_results]
        end_times = [r["end_time"] for r in successful_results]
        
        time_spread = max(start_times) - min(start_times)
        overlap_detected = max(start_times) < min(end_times)
        
        print(f"\n🔄 Concurrency Analysis:")
        print(f"   Request start time spread: {time_spread:.3f}s")
        print(f"   Requests overlapped: {'✅ YES' if overlap_detected else '❌ NO'}")
        
        if time_spread < 1.0 and overlap_detected:
            print("   🎉 TRUE CONCURRENCY DETECTED!")
            print("   Multiple requests were processed simultaneously.")
        else:
            print("   ⚠️  Sequential processing detected.")
            print("   Requests may be blocking each other.")
        
        # Show individual results
        print(f"\n📝 Individual Results:")
        for result in successful_results:
            print(f"   [{result['request_id']}] {result['duration']:.2f}s - "
                  f"{result['projects_found']} projects - "
                  f"{result['data_source']} - "
                  f"{result['ai_provider']}")
    
    if failed_results:
        print(f"\n❌ Failed Requests:")
        for result in failed_results:
            print(f"   [{result['request_id']}] {result.get('error', 'Unknown error')}")
    
    if exceptions:
        print(f"\n💥 Exceptions:")
        for i, exc in enumerate(exceptions):
            print(f"   [{i+1}] {exc}")
    
    # Overall verdict
    print("\n" + "=" * 60)
    if len(successful_results) >= 2 and overlap_detected and time_spread < 1.0:
        print("🎉 CELERY CONCURRENCY TEST: PASSED")
        print("   Multiple requests processed simultaneously!")
    elif len(successful_results) >= 1:
        print("⚠️  CELERY CONCURRENCY TEST: PARTIAL")
        print("   Some requests succeeded but concurrency unclear.")
    else:
        print("❌ CELERY CONCURRENCY TEST: FAILED")
        print("   No successful concurrent processing detected.")
    
    print("=" * 60)

async def test_celery_worker_status():
    """Check if Celery workers are available."""
    
    print("\n🔍 Checking Celery Worker Status...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Check if Celery status endpoint exists
            async with session.get(f"{API_BASE_URL}/api/providers") as response:
                if response.status == 200:
                    data = await response.json()
                    celery_info = data.get("concurrent_processing", {})
                    print(f"   Concurrent processing enabled: {celery_info.get('enabled', False)}")
                    print(f"   Thread pool size: {celery_info.get('thread_pool_size', 'Unknown')}")
                else:
                    print(f"   ❌ Cannot get provider status: {response.status}")
    except Exception as e:
        print(f"   ❌ Error checking status: {e}")

if __name__ == "__main__":
    print("🚀 Starting Celery Concurrency Test")
    print(f"📍 API URL: {API_BASE_URL}")
    print(f"📊 Concurrent requests: {CONCURRENT_REQUESTS}")
    
    # Run the tests
    asyncio.run(test_celery_worker_status())
    asyncio.run(test_concurrent_processing())
    
    print("\n💡 Tips:")
    print("   - If concurrency fails, ensure Celery workers are running")
    print("   - Check: docker-compose -f docker-compose.celery.yml ps")
    print("   - Monitor: http://localhost:5555 (Flower dashboard)")
    print("   - Logs: docker-compose logs celery-worker") 