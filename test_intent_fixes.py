#!/usr/bin/env python3
"""
Test script to verify intent detection fixes for procedural questions.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.rag_service import CordisRAG
from services.enhanced_rag_service import HorizonEuropeRAG

def test_intent_detection_fixes():
    """Test that procedural questions are now correctly classified as GENERAL_QUERY."""
    
    print("🧪 Testing Intent Detection Fixes")
    print("=" * 60)
    
    # Initialize the RAG service
    try:
        cordis_rag = CordisRAG()
        enhanced_rag = HorizonEuropeRAG()
        
        # Test queries that should be classified as GENERAL_QUERY (procedural)
        procedural_questions = [
            "How to find and apply for relevant calls?",
            "What is the application process for Horizon Europe?",
            "How do I form a consortium for EU proposals?", 
            "What are the eligibility criteria for ERC grants?",
            "How can I apply for funding?",
            "What are the steps to submit a proposal?",
            "How do I register on the EU portal?",
            "What is the evaluation process?",
            "How to prepare a competitive proposal?",
            "What are the requirements for participation?"
        ]
        
        # Test queries that should be classified as SEARCH_CALLS (looking for specific calls)
        call_search_questions = [
            "What calls are available for AI research?",
            "Show me open calls for renewable energy",
            "Are there any calls for healthcare projects?",
            "List available funding opportunities for SMEs",
            "Find calls for digital transformation projects"
        ]
        
        # Test queries that should be classified as SEARCH_PROJECTS  
        project_search_questions = [
            "What AI projects have been funded in healthcare?",
            "Show me successful renewable energy projects",
            "What research has been done on quantum computing?"
        ]
        
        print("🔍 Testing Procedural Questions (should be GENERAL_QUERY):")
        print("-" * 60)
        
        correct_procedural = 0
        for question in procedural_questions:
            intent, confidence = cordis_rag.determine_user_intent(question)
            status = "✅" if intent == "GENERAL_QUERY" else "❌"
            print(f"{status} '{question[:50]}...' -> {intent} (confidence: {confidence:.2f})")
            if intent == "GENERAL_QUERY":
                correct_procedural += 1
        
        print(f"\n📊 Procedural Questions: {correct_procedural}/{len(procedural_questions)} classified correctly")
        
        print("\n🔍 Testing Call Search Questions (should be SEARCH_CALLS):")
        print("-" * 60)
        
        correct_calls = 0
        for question in call_search_questions:
            intent, confidence = cordis_rag.determine_user_intent(question)
            status = "✅" if intent == "SEARCH_CALLS" else "❌"
            print(f"{status} '{question[:50]}...' -> {intent} (confidence: {confidence:.2f})")
            if intent == "SEARCH_CALLS":
                correct_calls += 1
                
        print(f"\n📊 Call Search Questions: {correct_calls}/{len(call_search_questions)} classified correctly")
        
        print("\n🔍 Testing Project Search Questions (should be SEARCH_PROJECTS):")
        print("-" * 60)
        
        correct_projects = 0
        for question in project_search_questions:
            intent, confidence = cordis_rag.determine_user_intent(question)
            status = "✅" if intent == "SEARCH_PROJECTS" else "❌"
            print(f"{status} '{question[:50]}...' -> {intent} (confidence: {confidence:.2f})")
            if intent == "SEARCH_PROJECTS":
                correct_projects += 1
                
        print(f"\n📊 Project Search Questions: {correct_projects}/{len(project_search_questions)} classified correctly")
        
        # Overall results
        total_correct = correct_procedural + correct_calls + correct_projects
        total_questions = len(procedural_questions) + len(call_search_questions) + len(project_search_questions)
        accuracy = (total_correct / total_questions) * 100
        
        print(f"\n🎯 Overall Results:")
        print(f"Total Accuracy: {total_correct}/{total_questions} ({accuracy:.1f}%)")
        
        if correct_procedural == len(procedural_questions):
            print("✅ SUCCESS: All procedural questions are now correctly classified!")
        else:
            print("❌ ISSUE: Some procedural questions are still misclassified")
            
        # Test the full pipeline with a procedural question
        print(f"\n🔄 Testing Full Pipeline with Procedural Question:")
        print("-" * 60)
        
        test_question = "How to find and apply for relevant calls?"
        print(f"Question: '{test_question}'")
        
        try:
            result = enhanced_rag.answer_question(
                question=test_question,
                max_context_chunks=3,
                include_documents=True,
                include_projects=False  # Disable projects to force document search
            )
            
            print(f"Intent: {result.get('intent', 'Unknown')}")
            print(f"Data Source: {result.get('data_source', 'Unknown')}")
            print(f"Success: {result.get('success', False)}")
            print(f"Answer Preview: {result.get('answer', '')[:200]}...")
            
            if result.get('intent') == 'GENERAL_INFO' and 'Documents' in result.get('data_source', ''):
                print("✅ SUCCESS: Procedural question routed to document search!")
            else:
                print("❌ ISSUE: Procedural question not properly routed")
                
        except Exception as e:
            print(f"❌ Error testing full pipeline: {e}")
        
        return accuracy >= 80  # Consider success if 80% or better
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Intent Detection Fix Tests...")
    success = test_intent_detection_fixes()
    
    if success:
        print("\n🎉 Tests completed successfully!")
        print("The system should now properly handle procedural 'how-to' questions.")
    else:
        print("\n❌ Tests revealed issues that need further fixing.")
        
    print("=" * 60)