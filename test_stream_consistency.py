#!/usr/bin/env python3

import asyncio
import aiohttp
import json
import hashlib
import time
from datetime import datetime

async def test_streaming_endpoint():
    """Test the streaming endpoint for consistency"""
    
    url = "http://localhost:8000/api/query/stream"
    
    # Test question that should be automotive, not medical
    question = "What are some recent projects about cars"
    
    payload = {
        "question": question,
        "max_results": 5,
        "ai_provider": "gemini",  # Using Gemini as requested
        "ai_version": "V8",
        "use_local_db": True  # Test with local database
    }
    
    print(f"🔬 Testing streaming endpoint consistency")
    print(f"Question: '{question}'")
    print(f"Provider: {payload['ai_provider']}")
    print(f"Version: {payload['ai_version']}")
    print(f"Local DB: {payload['use_local_db']}")
    print("="*80)
    
    # Run multiple tests
    results = []
    
    for test_run in range(3):
        print(f"\n🧪 Run {test_run + 1}")
        print("-" * 40)
        
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        print(f"❌ Error {response.status}: {await response.text()}")
                        continue
                        
                    full_answer = ""
                    metadata = None
                    logs = None
                    
                    # Process streaming response
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                                
                                if data.get('type') == 'token':
                                    full_answer += data.get('content', '')
                                elif data.get('type') == 'complete':
                                    metadata = data
                                    logs = data.get('logs', {})
                                    break
                                elif data.get('type') == 'metadata':
                                    print(f"📊 Metadata: {data}")
                                elif data.get('type') == 'progress':
                                    print(f"⚡ {data.get('phase', 'unknown')}: {data.get('message', '')}")
                                elif data.get('type') == 'error':
                                    print(f"❌ Error: {data}")
                                    break
                            except json.JSONDecodeError:
                                continue
            
            elapsed = time.time() - start_time
            
            # Check for automotive vs medical content
            automotive_indicators = [
                "vehicle", "automotive", "transport", "mobility", "driving", 
                "5gmeta", "electric vehicle", "autonomous", "traffic"
            ]
            
            medical_indicators = [
                "car t-cell", "chimeric antigen receptor", "immunotherapy", 
                "cancer", "leukemia", "lymphoma", "t-cell therapy", "cd19", "cd22"
            ]
            
            automotive_count = sum(1 for term in automotive_indicators if term.lower() in full_answer.lower())
            medical_count = sum(1 for term in medical_indicators if term.lower() in full_answer.lower())
            
            print(f"✅ Run {test_run + 1} completed in {elapsed:.2f}s")
            print(f"Response length: {len(full_answer)} characters")
            print(f"Automotive indicators: {automotive_count}")
            print(f"Medical indicators: {medical_count}")
            
            if medical_count > automotive_count:
                print("🚨 WARNING: Medical content detected when asking about cars!")
            elif automotive_count > 0:
                print("✅ Automotive content correctly identified")
            else:
                print("❓ No clear automotive content detected")
            
            # Create content hash for consistency checking
            content_hash = hashlib.md5(full_answer.encode()).hexdigest()
            
            results.append({
                'run': test_run + 1,
                'hash': content_hash,
                'length': len(full_answer),
                'automotive_count': automotive_count,
                'medical_count': medical_count,
                'elapsed': elapsed,
                'answer_preview': full_answer[:200] + "..." if len(full_answer) > 200 else full_answer
            })
            
            print(f"Content hash: {content_hash}")
            
        except Exception as e:
            print(f"❌ Run {test_run + 1} failed: {e}")
    
    # Analyze consistency
    print("\n" + "="*80)
    print("🔍 CONSISTENCY ANALYSIS")
    print("="*80)
    
    if len(results) < 2:
        print("❌ Not enough successful runs to analyze consistency")
        return
    
    # Check hash consistency
    unique_hashes = set(result['hash'] for result in results)
    consistency_score = 1.0 if len(unique_hashes) == 1 else 0.0
    
    print(f"Unique response hashes: {len(unique_hashes)}")
    print(f"Consistency Score: {consistency_score:.2f}")
    
    if consistency_score == 1.0:
        print("✅ Perfect consistency - all responses identical")
    else:
        print("❌ Inconsistent responses detected")
        for i, result in enumerate(results):
            print(f"  Run {result['run']}: {result['hash']} ({result['length']} chars)")
    
    # Check interpretation consistency
    interpretation_consistency = True
    for result in results:
        if result['medical_count'] > result['automotive_count']:
            interpretation_consistency = False
            break
    
    print(f"\nInterpretation Consistency: {'✅ PASS' if interpretation_consistency else '❌ FAIL'}")
    
    # Show detailed results
    print("\n📋 DETAILED RESULTS:")
    for result in results:
        print(f"\nRun {result['run']}:")
        print(f"  Hash: {result['hash']}")
        print(f"  Length: {result['length']} chars")
        print(f"  Automotive: {result['automotive_count']}, Medical: {result['medical_count']}")
        print(f"  Preview: {result['answer_preview']}")

if __name__ == "__main__":
    asyncio.run(test_streaming_endpoint()) 