#!/usr/bin/env python3
"""
Test script to verify concurrent processing of streaming requests.
This tests the /api/query/stream endpoint to ensure multiple requests can be processed simultaneously.
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime

# Test configuration
API_BASE_URL = "http://localhost:8000"
STREAM_ENDPOINT = f"{API_BASE_URL}/api/query/stream"

# Test questions for concurrent processing
TEST_QUESTIONS = [
    "AI projects in healthcare from the last 5 years",
    "European renewable energy research projects", 
    "Machine learning applications in automotive industry"
]

async def test_streaming_request(session, question_id, question):
    """Send a streaming request and measure timing."""
    start_time = time.time()
    
    request_data = {
        "question": question,
        "max_results": 3,
        "ai_provider": "gemini",
        "ai_version": "V8"
    }
    
    print(f"📤 Request {question_id}: Starting - {question[:50]}...")
    
    try:
        async with session.post(STREAM_ENDPOINT, json=request_data) as response:
            if response.status != 200:
                error_text = await response.text()
                print(f"❌ Request {question_id}: HTTP {response.status} - {error_text}")
                return None
            
            # Track streaming events
            events = []
            tokens_received = 0
            processing_complete_time = None
            
            async for line in response.content:
                line_text = line.decode('utf-8').strip()
                if line_text.startswith('data: '):
                    data_json = line_text[6:]  # Remove 'data: ' prefix
                    try:
                        event = json.loads(data_json)
                        events.append(event)
                        
                        # Track different event types
                        if event.get('type') == 'metadata':
                            print(f"🎯 Request {question_id}: Started processing ({time.time() - start_time:.2f}s)")
                        elif event.get('type') == 'progress' and 'worker' in event.get('message', '').lower():
                            print(f"⚙️ Request {question_id}: {event.get('message', '')} ({time.time() - start_time:.2f}s)")
                        elif event.get('type') == 'token':
                            tokens_received += len(event.get('content', ''))
                        elif event.get('type') == 'complete':
                            processing_complete_time = time.time()
                            print(f"✅ Request {question_id}: Completed ({processing_complete_time - start_time:.2f}s)")
                            break
                        elif event.get('type') == 'error':
                            print(f"❌ Request {question_id}: Error - {event.get('details', 'Unknown error')}")
                            return None
                            
                    except json.JSONDecodeError:
                        continue  # Skip malformed JSON
            
            total_time = time.time() - start_time
            
            # Extract final results
            final_event = events[-1] if events else {}
            result = {
                'question_id': question_id,
                'question': question,
                'start_time': start_time,
                'total_time': total_time,
                'processing_complete_time': processing_complete_time,
                'events_count': len(events),
                'tokens_received': tokens_received,
                'task_id': final_event.get('task_id', 'unknown'),
                'concurrent_processing': final_event.get('concurrent_processing', False),
                'ai_provider': final_event.get('ai_provider', 'unknown'),
                'projects_found': final_event.get('projects_found', 0),
                'success': processing_complete_time is not None
            }
            
            print(f"🏁 Request {question_id}: Total time {total_time:.2f}s, Events: {len(events)}, Tokens: {tokens_received}")
            return result
            
    except Exception as e:
        print(f"❌ Request {question_id}: Exception - {str(e)}")
        return None

async def test_concurrent_streaming():
    """Test multiple streaming requests concurrently."""
    print("🚀 Testing Concurrent Streaming Processing")
    print("=" * 60)
    
    # Check API health first
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/api/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    celery_status = health_data.get('components', {}).get('celery', {}).get('status', 'unknown')
                    print(f"🏥 API Health: OK | Celery: {celery_status}")
                    
                    if celery_status != 'available':
                        print("⚠️ Warning: Celery not available, concurrent processing may not work")
                else:
                    print(f"⚠️ API Health check failed: HTTP {response.status}")
        except Exception as e:
            print(f"⚠️ Could not check API health: {e}")
    
    print(f"📋 Testing {len(TEST_QUESTIONS)} concurrent streaming requests...")
    print()
    
    # Start all requests simultaneously
    start_time = time.time()
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as session:
        # Create concurrent tasks
        tasks = []
        for i, question in enumerate(TEST_QUESTIONS, 1):
            task = asyncio.create_task(test_streaming_request(session, i, question))
            tasks.append(task)
        
        print(f"🏃‍♂️ All {len(tasks)} requests launched simultaneously at {datetime.now().strftime('%H:%M:%S')}")
        print()
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    total_test_time = time.time() - start_time
    
    # Analyze results
    print()
    print("📊 CONCURRENT STREAMING TEST RESULTS")
    print("=" * 60)
    
    successful_results = [r for r in results if r and isinstance(r, dict) and r.get('success')]
    failed_results = [r for r in results if not r or isinstance(r, Exception) or (isinstance(r, dict) and not r.get('success'))]
    
    print(f"✅ Successful requests: {len(successful_results)}/{len(TEST_QUESTIONS)}")
    print(f"❌ Failed requests: {len(failed_results)}")
    print(f"⏱️ Total test time: {total_test_time:.2f}s")
    print()
    
    if successful_results:
        # Time analysis
        start_times = [r['start_time'] for r in successful_results]
        complete_times = [r['processing_complete_time'] for r in successful_results if r['processing_complete_time']]
        
        if len(start_times) > 1:
            time_spread = max(start_times) - min(start_times)
            print(f"🎯 Request time spread: {time_spread:.3f}s")
            
            if time_spread < 1.0:
                print("✅ CONCURRENCY DETECTED: Requests started nearly simultaneously")
            else:
                print("⚠️ Sequential processing detected: Large time spread between starts")
        
        if len(complete_times) > 1:
            completion_spread = max(complete_times) - min(complete_times)
            print(f"🏁 Completion time spread: {completion_spread:.2f}s")
        
        # Performance analysis  
        avg_time = sum(r['total_time'] for r in successful_results) / len(successful_results)
        min_time = min(r['total_time'] for r in successful_results)
        max_time = max(r['total_time'] for r in successful_results)
        
        print(f"📈 Average response time: {avg_time:.2f}s")
        print(f"⚡ Fastest response: {min_time:.2f}s")
        print(f"🐌 Slowest response: {max_time:.2f}s")
        
        # Celery analysis
        concurrent_processing_count = sum(1 for r in successful_results if r.get('concurrent_processing'))
        unique_task_ids = len(set(r.get('task_id', 'unknown') for r in successful_results))
        
        print(f"🔄 Requests using Celery workers: {concurrent_processing_count}/{len(successful_results)}")
        print(f"🆔 Unique task IDs: {unique_task_ids}")
        
        print()
        print("📋 Individual Request Details:")
        for r in successful_results:
            status_icon = "✅" if r['success'] else "❌"
            celery_icon = "🔄" if r.get('concurrent_processing') else "🔀"
            print(f"  {status_icon} Q{r['question_id']}: {r['total_time']:.2f}s {celery_icon} "
                  f"Task:{r.get('task_id', 'N/A')[:8]} Projects:{r.get('projects_found', 0)}")
        
        # Final assessment
        print()
        print("🎯 CONCURRENT STREAMING ASSESSMENT:")
        if concurrent_processing_count >= 2 and time_spread < 1.0 and unique_task_ids >= 2:
            print("✅ SUCCESS: Concurrent streaming processing is working correctly!")
            print("   - Multiple requests processed simultaneously by different Celery workers")
            print("   - Requests started nearly at the same time")
            print("   - Each request got its own task ID")
        elif concurrent_processing_count >= 2:
            print("⚠️ PARTIAL: Celery is working but timing may indicate some serialization")
        else:
            print("❌ FAILED: Streaming requests are not being processed concurrently")
            print("   - Check Celery worker status and streaming endpoint implementation")
    
    else:
        print("❌ No successful requests to analyze")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_concurrent_streaming()) 