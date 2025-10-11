#!/usr/bin/env python3
"""
Test the Unified Intent Classifier with various query types
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from app.services.unified_intent_classifier import UnifiedIntentClassifier

async def test_classifier():
    """Test the unified intent classifier with various queries"""
    
    classifier = UnifiedIntentClassifier()
    
    # Test queries covering all 5 intent types
    test_queries = [
        # FAQ queries
        ("How do I apply for Horizon Europe funding?", "faq"),
        ("What are the eligibility criteria?", "faq"),
        ("Explain the evaluation process", "faq"),
        ("Tell me about consortium requirements", "faq"),
        
        # Search Projects
        ("Show me projects about renewable energy", "search_projects"),
        ("Find AI healthcare research", "search_projects"),
        ("What projects have been funded in biotechnology?", "search_projects"),
        ("Can you show me successful climate projects?", "search_projects"),
        
        # Search Calls
        ("What calls are open for renewable energy?", "search_calls"),
        ("Show me funding opportunities in AI", "search_calls"),
        ("Find grants with deadline in 2025", "search_calls"),
        ("Are there any open calls for SMEs?", "search_calls"),
        
        # Call-Specific
        ("Tell me about HORIZON-CL3-2025-02-CS-ECCC-01", "call_specific"),
        ("What's the budget for HORIZON-MSCA-2024-DN-01?", "call_specific"),
        ("When is the deadline for HORIZON-HLTH-2025-01?", "call_specific"),
        ("Explain the scope of HORIZON-CL6-2025-CLIMATE-01", "call_specific"),
        
        # Proposal Writing
        ("Help me write a proposal for HORIZON-CL3-2025-02-CS-ECCC-01", "proposal_writing"),
        ("Draft the objectives section", "proposal_writing"),
        ("Move to the next section", "proposal_writing"),
        ("Export my proposal to Word", "proposal_writing"),
        ("The project acronym is BEETHOVEN", "proposal_writing"),
        
        # Edge cases
        ("renewable energy", "faq"),  # Ambiguous - should default to FAQ
        ("Tell me more", "faq"),  # Context-dependent
    ]
    
    print("=" * 80)
    print("UNIFIED INTENT CLASSIFIER TESTS")
    print("=" * 80)
    print()
    
    correct = 0
    total = len(test_queries)
    
    for query, expected_intent in test_queries:
        print(f"Query: {query}")
        print(f"Expected: {expected_intent}")
        
        intent = await classifier.classify_intent(
            user_message=query,
            conversation_id=1,
            recent_messages=[]
        )
        
        print(f"Got: {intent.primary_intent} (confidence: {intent.confidence:.2f})")
        print(f"Reasoning: {intent.reasoning[:100]}...")
        
        if intent.call_id:
            print(f"Call ID: {intent.call_id}")
        if intent.proposal_action:
            print(f"Proposal Action: {intent.proposal_action}")
        if intent.tool_plan:
            print(f"Tools: {[t['tool_name'] for t in intent.tool_plan]}")
        
        if intent.primary_intent == expected_intent:
            print("✅ CORRECT")
            correct += 1
        else:
            print("❌ INCORRECT")
        
        print("-" * 80)
        print()
    
    print("=" * 80)
    print(f"RESULTS: {correct}/{total} correct ({correct/total*100:.1f}%)")
    print("=" * 80)
    
    if correct / total >= 0.85:
        print("🎉 EXCELLENT! Classifier is working well!")
    elif correct / total >= 0.70:
        print("👍 GOOD! Some edge cases need refinement")
    else:
        print("⚠️ NEEDS WORK! Review prompt and examples")

if __name__ == "__main__":
    asyncio.run(test_classifier())

