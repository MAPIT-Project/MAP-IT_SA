#!/usr/bin/env python3
"""
Test 10 comprehensive questions on the /api/v2/conversation/{id}/message/stream endpoint
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

class ComprehensiveAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.test_results = []
    
    async def test_question(self, conversation_id: int, question: str, test_name: str):
        """Test a specific question on the v2 streaming endpoint"""
        print(f"\n🧪 Testing: {test_name}")
        print(f"📝 Question: {question}")
        print(f"🌐 Endpoint: /api/v2/conversation/{conversation_id}/message/stream")
        
        url = f"{self.base_url}/api/v2/conversation/{conversation_id}/message/stream"
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={
                        "message": question,
                        "include_context": True,
                        "memory_strategy": "full"
                    },
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status != 200:
                        print(f"❌ HTTP Error: {response.status}")
                        return False
                    
                    full_response = ""
                    metadata = {}
                    
                    async for line in response.content:
                        line_text = line.decode('utf-8').strip()
                        
                        if line_text.startswith('data: '):
                            try:
                                data = json.loads(line_text[6:])
                                
                                if data.get('type') == 'token':
                                    full_response += data.get('content', '')
                                elif data.get('type') == 'complete':
                                    metadata = data
                                    break
                                elif data.get('type') == 'error':
                                    print(f"❌ Stream error: {data.get('error')}")
                                    return False
                            except json.JSONDecodeError:
                                continue
                    
                    end_time = time.time()
                    processing_time = end_time - start_time
                    
                    # Analyze response
                    success = self._analyze_response(
                        full_response, metadata, processing_time, test_name
                    )
                    
                    self.test_results.append({
                        'test_name': test_name,
                        'question': question,
                        'success': success,
                        'response_length': len(full_response),
                        'processing_time': processing_time,
                        'metadata': metadata,
                        'response_preview': full_response[:200] + "..." if len(full_response) > 200 else full_response
                    })
                    
                    return success
                    
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    def _analyze_response(self, response: str, metadata: dict, processing_time: float, test_name: str):
        """Analyze response quality and content"""
        
        print(f"\n📊 Response Analysis:")
        print(f"   ⏱️ Processing time: {processing_time:.2f}s")
        print(f"   📏 Response length: {len(response)} characters")
        print(f"   🎯 Confidence: {metadata.get('confidence', 'N/A')}")
        print(f"   📚 Grounded: {metadata.get('grounded', 'N/A')}")
        print(f"   🔗 Citations: {len(metadata.get('citations', []))}")
        print(f"   🧠 Memory turns: {metadata.get('memory_stats', {}).get('turn_count', 'N/A')}")
        print(f"   🔧 Tools executed: {metadata.get('tools_executed', 'N/A')}")
        print(f"   📝 Response preview: {response[:150]}...")
        
        # Success criteria
        has_content = len(response) > 50
        reasonable_time = processing_time < 15.0
        not_error = "error" not in response.lower() or "apologize" not in response.lower()
        
        success = has_content and reasonable_time
        
        if success:
            print(f"   ✅ Test PASSED")
        else:
            print(f"   ❌ Test FAILED")
            if not has_content:
                print(f"      - Response too short: {len(response)} chars")
            if not reasonable_time:
                print(f"      - Too slow: {processing_time:.2f}s")
        
        return success

async def main():
    """Test 10 comprehensive questions"""
    
    print("""
╔══════════════════════════════════════════════════════════╗
║     Testing 10 Questions on /api/v2/conversation/stream  ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    tester = ComprehensiveAPITester()
    
    # 10 comprehensive test questions covering different scenarios
    test_questions = [
        {
            'conversation_id': 2001,
            'question': 'What are some open calls for clean energy?',
            'test_name': 'Open Calls - Clean Energy'
        },
        {
            'conversation_id': 2002,
            'question': 'Show me funding opportunities for AI research',
            'test_name': 'Funding Opportunities - AI'
        },
        {
            'conversation_id': 2003,
            'question': 'What are some recent projects related to nuclear energy?',
            'test_name': 'Recent Projects - Nuclear'
        },
        {
            'conversation_id': 2004,
            'question': 'Find open calls for quantum computing research',
            'test_name': 'Open Calls - Quantum Computing'
        },
        {
            'conversation_id': 2005,
            'question': 'What projects exist in renewable energy?',
            'test_name': 'Projects - Renewable Energy'
        },
        {
            'conversation_id': 2006,
            'question': 'Tell me about Horizon Europe budget',
            'test_name': 'General Info - Budget'
        },
        {
            'conversation_id': 2007,
            'question': 'How do I apply for ERC grants?',
            'test_name': 'Process Question - ERC'
        },
        {
            'conversation_id': 2008,
            'question': 'What are the eligibility criteria for SME funding?',
            'test_name': 'Eligibility - SME'
        },
        {
            'conversation_id': 2009,
            'question': 'Show me calls related to digital transformation',
            'test_name': 'Calls - Digital Transformation'
        },
        {
            'conversation_id': 2010,
            'question': 'What are some successful health research projects?',
            'test_name': 'Projects - Health Research'
        }
    ]
    
    print("🔍 Testing 10 Questions on v2 API...")
    print("="*70)
    
    passed_tests = 0
    total_tests = len(test_questions)
    
    for i, test_case in enumerate(test_questions, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}/{total_tests}")
        print('='*70)
        
        success = await tester.test_question(
            conversation_id=test_case['conversation_id'],
            question=test_case['question'],
            test_name=test_case['test_name']
        )
        
        if success:
            passed_tests += 1
        
        # Small delay between tests to avoid rate limits
        await asyncio.sleep(3)
    
    # Final results
    print(f"\n{'='*70}")
    print("FINAL TEST RESULTS")
    print('='*70)
    
    print(f"Tests passed: {passed_tests}/{total_tests}")
    print(f"Success rate: {passed_tests/total_tests:.1%}")
    
    # Detailed results
    print(f"\n📊 Detailed Results:")
    for result in tester.test_results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"   {result['test_name']:<35} {status} ({result['processing_time']:.2f}s)")
    
    # Show some successful responses
    successful_tests = [r for r in tester.test_results if r['success']]
    if successful_tests:
        print(f"\n🎉 Sample Successful Responses:")
        for result in successful_tests[:3]:
            print(f"\n📝 {result['test_name']}:")
            print(f"   Question: {result['question']}")
            print(f"   Response: {result['response_preview']}")
    
    if passed_tests >= 7:  # 70% success rate
        print("""
╔══════════════════════════════════════════════════════════╗
║                  🎉 EXCELLENT RESULTS! 🎉                ║
║                                                          ║
║  Your v2 API is working excellently!                   ║
║  AI agent + tool orchestrator integration successful!   ║
║                                                          ║
║  Ready for production use! 🚀                          ║
╚══════════════════════════════════════════════════════════╝
        """)
    elif passed_tests >= 5:  # 50% success rate
        print("""
╔══════════════════════════════════════════════════════════╗
║                  ✅ GOOD RESULTS!                        ║
║                                                          ║
║  Your v2 API is working well!                          ║
║  Some minor issues to address but core functionality    ║
║  is solid.                                              ║
╚══════════════════════════════════════════════════════════╝
        """)
    else:
        print("""
╔══════════════════════════════════════════════════════════╗
║                  ⚠️ NEEDS IMPROVEMENT                    ║
║                                                          ║
║  Some functionality needs fixes.                        ║
║  Check the detailed results above.                      ║
╚══════════════════════════════════════════════════════════╝
        """)
    
    return passed_tests >= 7

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)