#!/usr/bin/env python3
"""
Simple test script to verify intent detection fixes for procedural questions.
"""

import sys
import os

# Add the project root and app directories to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'app'))

def test_intent_detection_only():
    """Test just the intent detection without the full RAG pipeline."""
    
    print("🧪 Testing Intent Detection Fixes (Core Functionality)")
    print("=" * 60)
    
    try:
        # Import with proper path handling
        from app.services.rag_service import CordisRAG
        
        # Initialize just the CORDIS RAG service
        cordis_rag = CordisRAG(use_local_db=False)  # Use API mode to avoid DB dependencies
        
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
            try:
                intent, confidence = cordis_rag.determine_user_intent(question)
                status = "✅" if intent == "GENERAL_QUERY" else "❌"
                print(f"{status} '{question[:45]}...' -> {intent} ({confidence:.2f})")
                if intent == "GENERAL_QUERY":
                    correct_procedural += 1
            except Exception as e:
                print(f"❌ Error testing '{question[:30]}...': {e}")
        
        print(f"\n📊 Procedural Questions: {correct_procedural}/{len(procedural_questions)} classified correctly")
        
        print("\n🔍 Testing Call Search Questions (should be SEARCH_CALLS):")
        print("-" * 60)
        
        correct_calls = 0
        for question in call_search_questions:
            try:
                intent, confidence = cordis_rag.determine_user_intent(question)
                status = "✅" if intent == "SEARCH_CALLS" else "❌"
                print(f"{status} '{question[:45]}...' -> {intent} ({confidence:.2f})")
                if intent == "SEARCH_CALLS":
                    correct_calls += 1
            except Exception as e:
                print(f"❌ Error testing '{question[:30]}...': {e}")
                
        print(f"\n📊 Call Search Questions: {correct_calls}/{len(call_search_questions)} classified correctly")
        
        print("\n🔍 Testing Project Search Questions (should be SEARCH_PROJECTS):")
        print("-" * 60)
        
        correct_projects = 0 
        for question in project_search_questions:
            try:
                intent, confidence = cordis_rag.determine_user_intent(question)
                status = "✅" if intent == "SEARCH_PROJECTS" else "❌"
                print(f"{status} '{question[:45]}...' -> {intent} ({confidence:.2f})")
                if intent == "SEARCH_PROJECTS":
                    correct_projects += 1
            except Exception as e:
                print(f"❌ Error testing '{question[:30]}...': {e}")
                
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
            
        # Test the specific problem question
        print(f"\n🎯 Testing the Original Problem Question:")
        print("-" * 60)
        
        problem_question = "How to find and apply for relevant calls?"
        try:
            intent, confidence = cordis_rag.determine_user_intent(problem_question)
            print(f"Question: '{problem_question}'")
            print(f"Intent: {intent}")
            print(f"Confidence: {confidence:.2f}")
            
            if intent == "GENERAL_QUERY":
                print("✅ SUCCESS: The original problem question is now correctly classified!")
            else:
                print("❌ ISSUE: The original problem question is still misclassified")
        except Exception as e:
            print(f"❌ Error testing problem question: {e}")
            
        return accuracy >= 80  # Consider success if 80% or better
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please make sure all dependencies are installed and environment is set up correctly.")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Simple Intent Detection Tests...")
    success = test_intent_detection_only()
    
    if success:
        print("\n🎉 Intent detection tests completed successfully!")
        print("The system should now properly handle procedural 'how-to' questions.")
    else:
        print("\n❌ Tests revealed issues that need further fixing.")
        
    print("=" * 60)