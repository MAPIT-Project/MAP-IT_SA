#!/usr/bin/env python3
"""
Test script to verify concurrent request processing in the FastAPI server.
This script sends multiple requests simultaneously to test if they're processed concurrently.
"""

import asyncio
import aiohttp
import time
import json
from typing import List

async def send_request(session: aiohttp.ClientSession, url: str, data: dict, request_id: int) -> dict:
    """Send a single request and track timing."""
    start_time = time.time()
    try:
        async with session.post(url, json=data) as response:
            result = await response.json()
            end_time = time.time()
            return {
                'request_id': request_id,
                'status_code': response.status,
                'response_time': end_time - start_time,
                'success': response.status == 200,
                'answer_preview': result.get('answer', '')[:100] if result.get('answer') else 'No answer',
                'ai_version': result.get('ai_version'),
                'processing_time': result.get('processing_time')
            }
    except Exception as e:
        end_time = time.time()
        return {
            'request_id': request_id,
            'status_code': 0,
            'response_time': end_time - start_time,
            'success': False,
            'error': str(e),
            'answer_preview': '',
            'ai_version': None,
            'processing_time': None
        }

async def test_concurrent_requests(base_url: str = "http://localhost:8000", num_requests: int = 5):
    """Test multiple concurrent requests to verify they're processed in parallel."""
    
    # Test questions
    questions = [
        "What are some AI projects in healthcare?",
        "Tell me about renewable energy research in Europe",
        "What quantum computing projects exist?",
        "Show me cybersecurity initiatives",
        "What biotech projects focus on agriculture?"
    ]
    
    # Prepare request data
    test_data = [
        {
            "question": questions[i % len(questions)],
            "max_results": 3,
            "ai_version": "V8",
            "ai_provider": "gemini"
        }
        for i in range(num_requests)
    ]
    
    url = f"{base_url}/api/query"
    
    print(f"🚀 Testing {num_requests} concurrent requests to {url}")
    print("=" * 60)
    
    start_time = time.time()
    
    # Send all requests concurrently
    async with aiohttp.ClientSession() as session:
        tasks = [
            send_request(session, url, data, i)
            for i, data in enumerate(test_data)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Analyze results
    successful_requests = [r for r in results if isinstance(r, dict) and r.get('success')]
    failed_requests = [r for r in results if isinstance(r, dict) and not r.get('success')]
    exceptions = [r for r in results if not isinstance(r, dict)]
    
    print(f"📊 Results Summary:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Successful: {len(successful_requests)}/{num_requests}")
    print(f"   Failed: {len(failed_requests)}")
    print(f"   Exceptions: {len(exceptions)}")
    print()
    
    if successful_requests:
        avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
        avg_processing_time = sum(r['processing_time'] for r in successful_requests if r['processing_time']) / len([r for r in successful_requests if r['processing_time']])
        
        print(f"📈 Performance Metrics:")
        print(f"   Average response time: {avg_response_time:.2f}s")
        print(f"   Average processing time: {avg_processing_time:.2f}s")
        print(f"   Requests per second: {len(successful_requests)/total_time:.2f}")
        print()
        
        # Check if requests were processed concurrently
        max_individual_time = max(r['response_time'] for r in successful_requests)
        if total_time < max_individual_time * 0.8:  # Allow some overhead
            print("✅ CONCURRENT PROCESSING DETECTED!")
            print(f"   Total time ({total_time:.2f}s) < Individual max time ({max_individual_time:.2f}s)")
        else:
            print("⚠️  SEQUENTIAL PROCESSING DETECTED")
            print(f"   Total time ({total_time:.2f}s) ≈ Sum of individual times")
        print()
    
    # Detailed results
    print("📋 Detailed Results:")
    for i, result in enumerate(results):
        if isinstance(result, dict):
            status = "✅" if result['success'] else "❌"
            print(f"   {status} Request {i}: {result['response_time']:.2f}s - {result['answer_preview']}")
        else:
            print(f"   ❌ Request {i}: Exception - {result}")

async def test_streaming_concurrency(base_url: str = "http://localhost:8000", num_requests: int = 3):
    """Test concurrent streaming requests."""
    print("\n🌊 Testing Streaming Concurrency")
    print("=" * 60)
    
    questions = [
        "What are some AI projects in healthcare?",
        "Tell me about renewable energy research",
        "What quantum computing projects exist?"
    ]
    
    async def stream_request(session: aiohttp.ClientSession, question: str, request_id: int):
        """Send a streaming request and collect chunks."""
        start_time = time.time()
        chunk_count = 0
        
        data = {
            "question": question,
            "max_results": 2,
            "ai_version": "V8"
        }
        
        try:
            async with session.post(f"{base_url}/api/query/stream", json=data) as response:
                async for chunk in response.content.iter_chunked(1024):
                    chunk_count += 1
                    if chunk_count % 10 == 0:  # Print every 10th chunk
                        print(f"   Request {request_id}: Received chunk {chunk_count}")
                
                end_time = time.time()
                return {
                    'request_id': request_id,
                    'total_chunks': chunk_count,
                    'response_time': end_time - start_time,
                    'success': True
                }
        except Exception as e:
            end_time = time.time()
            return {
                'request_id': request_id,
                'error': str(e),
                'response_time': end_time - start_time,
                'success': False
            }
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            stream_request(session, questions[i], i)
            for i in range(num_requests)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n📊 Streaming Results:")
    print(f"   Total time: {total_time:.2f}s")
    
    for result in results:
        if isinstance(result, dict) and result['success']:
            print(f"   ✅ Request {result['request_id']}: {result['response_time']:.2f}s, {result['total_chunks']} chunks")
        else:
            print(f"   ❌ Request failed: {result}")

if __name__ == "__main__":
    print("🧪 FastAPI Concurrency Test")
    print("Make sure your FastAPI server is running on http://localhost:8000")
    print()
    
    # Test regular concurrent requests
    asyncio.run(test_concurrent_requests(num_requests=5))
    
    # Test streaming concurrent requests
    asyncio.run(test_streaming_concurrency(num_requests=3))
    
    print("\n✨ Test completed!")
    print("\nTo run this test:")
    print("1. Start your FastAPI server: python fast_api.py")
    print("2. Run this test: python test_concurrency.py") 