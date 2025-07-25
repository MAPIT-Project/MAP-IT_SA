#!/usr/bin/env python3
"""
Test script to demonstrate V9's intelligent intent routing functionality.

This script tests the new ability to distinguish between:
1. Questions about existing projects (SEARCH_PROJECTS)
2. Questions about open calls for proposals (SEARCH_CALLS)
3. General queries (GENERAL_QUERY)

Run this script to see V9's intent classification in action.
"""

import requests
import json
import time
from typing import Dict, Any

# API configuration
BASE_URL = "http://localhost:8000/api/query"  # Changed back to port 8000

# Test questions for different intents
TEST_QUESTIONS = {
    "SEARCH_PROJECTS": [
        "What are some AI projects in healthcare?",
        "Show me renewable energy projects from Germany",
        "Which automotive research projects have been completed?",
        "What machine learning initiatives were funded in the last 5 years?"
    ],
    "SEARCH_CALLS": [
        "Are there any open calls for AI research?",
        "I need funding opportunities for renewable energy projects",
        "What calls are available for healthcare innovation?",
        "Where can I apply for automotive research funding?",
        "Show me open calls for proposals in digital transformation",
        "Are there any Horizon Europe calls for quantum computing?",
        "I'm looking for ERC grants in artificial intelligence",
        "What Marie Curie fellowships are currently open?"
    ],
    "GENERAL_QUERY": [
        "What is the EU's policy on digital transformation?",
        "How does the Horizon Europe program work?",
        "What are the main research priorities in Europe?"
    ]
}

def test_intent_routing(question: str) -> Dict[str, Any]:
    """
    Test V9's intent routing functionality with a single question.
    """
    payload = {
        "question": question,
        "max_results": 3,
        "ai_provider": "gemini",  # Use Gemini only for testing
        "ai_version": "V9",
        "use_local_db": False  # Disable local DB for more reliable testing
    }
    
    try:
        print(f"\n🧪 Testing: '{question}'")
        print("-" * 60)
        
        start_time = time.time()
        response = requests.post(BASE_URL, json=payload, timeout=120)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract key information
            answer = result.get('answer', '')
            logs = result.get('logs', {})
            routing_decision = logs.get('routing_decision', 'Unknown')
            intent_confidence = logs.get('intent_confidence', 0.0)
            data_source = result.get('data_source', 'Unknown')
            processing_time = result.get('processing_time', elapsed_time)
            
            print(f"✅ Intent: {routing_decision} (confidence: {intent_confidence:.2f})")
            print(f"📊 Data source: {data_source}")
            print(f"⏱️  Processing time: {processing_time:.2f}s")
            print(f"📝 Answer length: {len(answer)} characters")
            
            # Show routing phases
            phases = logs.get('phases', [])
            if phases:
                intent_phase = phases[0] if phases else {}
                if intent_phase.get('phase_name') == 'Intent Classification':
                    print(f"🎯 Intent classification time: {intent_phase.get('processing_time_ms', 0)}ms")
            
            # Show answer preview
            preview_length = 200
            answer_preview = answer[:preview_length] + ('...' if len(answer) > preview_length else '')
            print(f"💬 Answer preview: {answer_preview}")
            
            return {
                'success': True,
                'intent': routing_decision,
                'confidence': intent_confidence,
                'processing_time': processing_time,
                'answer_length': len(answer)
            }
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return {'success': False, 'error': response.text}
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return {'success': False, 'error': str(e)}

def main():
    """
    Run comprehensive tests of V9's intent routing functionality.
    """
    print("🚀 V9 Intent Routing Test Suite")
    print("=" * 60)
    print("Testing V9's ability to intelligently route between:")
    print("• Project searches (existing research projects)")
    print("• Call searches (open funding opportunities)")
    print("• General queries (policies, information)")
    print("=" * 60)
    
    # Check if API is available
    try:
        health_response = requests.get(f"http://localhost:8000/", timeout=10)
        if health_response.status_code != 200:
            print(f"❌ API not available at http://localhost:8000")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API at http://localhost:8000: {e}")
        print("💡 Make sure the FastAPI server is running with: python fast_api.py")
        return
    
    print(f"✅ API available at http://localhost:8000")
    
    # Test results summary
    results = {
        'SEARCH_PROJECTS': [],
        'SEARCH_CALLS': [],
        'GENERAL_QUERY': [],
        'total_tests': 0,
        'successful_tests': 0,
        'correct_classifications': 0
    }
    
    # Run tests for each category
    for expected_intent, questions in TEST_QUESTIONS.items():
        print(f"\n📂 Testing {expected_intent} questions:")
        print("=" * 40)
        
        for question in questions:
            result = test_intent_routing(question)
            results[expected_intent].append(result)
            results['total_tests'] += 1
            
            if result['success']:
                results['successful_tests'] += 1
                
                # Check if intent was classified correctly
                actual_intent = result.get('intent', '').upper()
                if actual_intent == expected_intent:
                    results['correct_classifications'] += 1
                    print(f"✅ Correct classification!")
                else:
                    print(f"⚠️ Misclassification: expected {expected_intent}, got {actual_intent}")
            
            time.sleep(1)  # Brief pause between requests
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    total_tests = results['total_tests']
    successful_tests = results['successful_tests']
    correct_classifications = results['correct_classifications']
    
    print(f"Total tests: {total_tests}")
    print(f"Successful requests: {successful_tests}")
    print(f"Correct classifications: {correct_classifications}")
    
    if total_tests > 0:
        success_rate = (successful_tests / total_tests) * 100
        accuracy_rate = (correct_classifications / successful_tests) * 100 if successful_tests > 0 else 0
        
        print(f"Request success rate: {success_rate:.1f}%")
        print(f"Classification accuracy: {accuracy_rate:.1f}%")
        
        if success_rate >= 90 and accuracy_rate >= 80:
            print("\n🎉 V9 Intent Routing is working excellently!")
        elif success_rate >= 70 and accuracy_rate >= 60:
            print("\n✅ V9 Intent Routing is working well!")
        else:
            print("\n⚠️ V9 Intent Routing needs improvement.")
    
    # Performance insights
    all_results = []
    for category_results in [results['SEARCH_PROJECTS'], results['SEARCH_CALLS'], results['GENERAL_QUERY']]:
        all_results.extend([r for r in category_results if r['success']])
    
    if all_results:
        avg_processing_time = sum(r['processing_time'] for r in all_results) / len(all_results)
        avg_confidence = sum(r['confidence'] for r in all_results) / len(all_results)
        
        print(f"\n⚡ Performance Metrics:")
        print(f"Average processing time: {avg_processing_time:.2f}s")
        print(f"Average confidence score: {avg_confidence:.2f}")
    
    print("\n🔗 Next steps:")
    print("• Try your own questions to test intent routing")
    print("• Check the FastAPI docs at http://localhost:8000/docs")
    print("• Monitor the console output for detailed routing decisions")

if __name__ == "__main__":
    main() 