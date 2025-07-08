#!/usr/bin/env python3
"""
Test script to verify consistency of AI responses for identical questions.
This script helps identify non-deterministic behavior in the RAG system.
"""

import requests
import json
import time
import hashlib
from typing import List, Dict, Any

API_BASE_URL = "http://localhost:8000"

def test_question_consistency(question: str, num_tests: int = 5, provider: str = "gemini", version: str = "V8"):
    """Test if the same question produces consistent results."""
    
    print(f"🧪 Testing consistency for: '{question}'")
    print(f"📊 Running {num_tests} tests with {provider} {version}")
    print("=" * 80)
    
    results = []
    question_hashes = []
    
    for i in range(num_tests):
        print(f"🔄 Test {i+1}/{num_tests}...")
        
        try:
            # Make API call
            start_time = time.time()
            response = requests.post(
                f"{API_BASE_URL}/api/query",
                json={
                    "question": question,
                    "provider": provider,
                    "version": version,
                    "max_projects": 5
                },
                timeout=60
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract key information for comparison
                answer_text = result.get("answer", "")
                projects = result.get("projects", [])
                projects_count = len(projects) if projects is not None else 0
                
                # Create content hash for comparison
                content_hash = hashlib.md5(
                    (answer_text + str(projects_count)).encode()
                ).hexdigest()[:8]
                
                # Store result
                test_result = {
                    "test_number": i + 1,
                    "response_time": response_time,
                    "answer_length": len(answer_text),
                    "projects_count": projects_count,
                    "content_hash": content_hash,
                    "status": "success",
                    "answer_preview": answer_text[:200] + "..." if len(answer_text) > 200 else answer_text
                }
                
                results.append(test_result)
                question_hashes.append(content_hash)
                
                print(f"   ✅ Success in {response_time:.1f}s | {projects_count} projects | Hash: {content_hash}")
                
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text}")
                results.append({
                    "test_number": i + 1,
                    "status": "error",
                    "error_code": response.status_code,
                    "error_message": response.text
                })
                
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
            results.append({
                "test_number": i + 1,
                "status": "exception",
                "error_message": str(e)
            })
        
        # Small delay between requests
        if i < num_tests - 1:
            time.sleep(2)
    
    # Analyze consistency
    print("\n" + "=" * 80)
    print("📈 CONSISTENCY ANALYSIS")
    print("=" * 80)
    
    successful_tests = [r for r in results if r.get("status") == "success"]
    
    if len(successful_tests) >= 2:
        # Check hash consistency
        unique_hashes = set(r["content_hash"] for r in successful_tests)
        
        print(f"🎯 Successful tests: {len(successful_tests)}/{num_tests}")
        print(f"🔍 Unique content hashes: {len(unique_hashes)}")
        print(f"📝 Content hashes: {list(unique_hashes)}")
        
        if len(unique_hashes) == 1:
            print("✅ PERFECT CONSISTENCY - All responses are identical!")
        elif len(unique_hashes) <= 2:
            print("⚠️  MINOR INCONSISTENCY - Very similar responses")
        else:
            print("❌ MAJOR INCONSISTENCY - Responses vary significantly")
        
        # Show statistics
        response_times = [r["response_time"] for r in successful_tests]
        project_counts = [r["projects_count"] for r in successful_tests]
        
        print(f"⏱️  Response time: {min(response_times):.1f}s - {max(response_times):.1f}s (avg: {sum(response_times)/len(response_times):.1f}s)")
        print(f"📊 Project counts: {min(project_counts)} - {max(project_counts)} (avg: {sum(project_counts)/len(project_counts):.1f})")
        
        # Show answer previews for different hashes
        print("\n🔍 ANSWER PREVIEWS BY HASH:")
        for unique_hash in unique_hashes:
            example = next(r for r in successful_tests if r["content_hash"] == unique_hash)
            print(f"   Hash {unique_hash}: {example['answer_preview']}")
            
    else:
        print("❌ Too few successful tests to analyze consistency")
    
    return results, len(unique_hashes) if successful_tests else float('inf')

def main():
    """Run consistency tests on various questions."""
    
    print("🚀 CONSISTENCY TEST SUITE")
    print("Testing if identical questions produce identical results")
    print("=" * 80)
    
    # Test questions that previously showed inconsistency
    test_questions = [
        "What are some recent projects about cars",
        "What are recent wind energy projects",
        "Tell me about machine learning projects",
        "What are automotive research projects"
    ]
    
    overall_results = {}
    
    for question in test_questions:
        print(f"\n" + "🎯" * 40)
        results, unique_count = test_question_consistency(question, num_tests=3, provider="gemini")
        overall_results[question] = {
            "results": results,
            "consistency_score": 1.0 / unique_count if unique_count > 0 else 0.0,
            "unique_responses": unique_count
        }
        
        print(f"\n📊 Consistency Score: {overall_results[question]['consistency_score']:.2f}")
        time.sleep(3)  # Pause between different questions
    
    # Final summary
    print("\n" + "🏆" * 40)
    print("FINAL CONSISTENCY REPORT")
    print("🏆" * 40)
    
    for question, data in overall_results.items():
        score = data["consistency_score"]
        status = "✅ EXCELLENT" if score == 1.0 else "⚠️ INCONSISTENT" if score > 0.3 else "❌ POOR"
        print(f"{status} | Score: {score:.2f} | '{question}'")
    
    # Overall assessment
    avg_score = sum(data["consistency_score"] for data in overall_results.values()) / len(overall_results)
    print(f"\n🎯 OVERALL CONSISTENCY SCORE: {avg_score:.2f}")
    
    if avg_score >= 0.9:
        print("🎉 EXCELLENT: The consistency fixes are working perfectly!")
    elif avg_score >= 0.6:
        print("✅ GOOD: Minor inconsistencies remain but much improved")
    else:
        print("❌ POOR: Significant consistency issues still exist")

if __name__ == "__main__":
    main() 