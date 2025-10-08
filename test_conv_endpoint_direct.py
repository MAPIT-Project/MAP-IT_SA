#!/usr/bin/env python3
"""
Test conversation endpoint with call document detection.
"""

import asyncio
import requests
import json

async def test():
    url = "http://localhost:8000/api/v2/conversation/123123/message"
    
    questions = [
        "What are the eligibility criteria for HORIZON-CL3-2025-02-CS-ECCC-01?",
        "What is the budget for HORIZON-CL3-2025-02-CS-ECCC-01?",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*70}")
        print(f"Question {i}: {question}")
        print('='*70)
        
        response = requests.post(
            url,
            json={"message": question},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check both possible keys
            answer = data.get('response_text') or data.get('response') or 'No response'
            
            print(f"\n✅ Response ({len(answer)} chars):")
            print(f"{answer[:500]}...")
            
            print(f"\n📊 Metadata:")
            print(f"   Tools: {data.get('tools_executed', [])}")
            print(f"   Time: {data.get('processing_time_ms', 0):.0f}ms")
            print(f"   Context: {data.get('context_used', False)}")
            print(f"   Grounded: {data.get('grounded', False)}")
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text[:500])

if __name__ == "__main__":
    asyncio.run(test())


