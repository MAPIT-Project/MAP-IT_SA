#!/usr/bin/env python3
"""
Test script to check intent detection for call-specific queries.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.call_specific_rag import CallSpecificRAG
from services.rag_service import CordisRAG

def test_intent_detection():
    """Test intent detection for various query types."""
    
    # Initialize the RAG services
    cordis_rag = CordisRAG()
    call_specific_rag = CallSpecificRAG(cordis_rag=cordis_rag)
    
    # Test queries
    test_queries = [
        "What are the eligibility criteria for HORIZON-CL4-2024-DATA-01-01?",
        "Tell me about HORIZON-CL5-2024-CLIMATE-01",
        "What health cluster calls are available?",
        "Find funding for AI research",
        "What are the eligibility criteria for Horizon Europe?"
    ]
    
    print("Testing Intent Detection:")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Test CORDIS general intent detection
        cordis_intent, cordis_confidence = cordis_rag.determine_user_intent(query)
        print(f"  CORDIS Intent: {cordis_intent} (confidence: {cordis_confidence:.2f})")
        
        # Test call-specific intent detection
        call_intent, call_id, call_confidence = call_specific_rag.detect_call_specific_intent(query)
        print(f"  Call-Specific Intent: {call_intent}, Call ID: {call_id}, Confidence: {call_confidence:.2f}")

if __name__ == "__main__":
    test_intent_detection()