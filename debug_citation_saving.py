"""
Debug script to test citation saving with the actual stream response format
"""
import os
import json
from app.services.citations_service import CitationsService

def test_with_actual_response():
    """Test with the actual stream response format"""
    print("🔍 Testing with actual stream response format")
    print("=" * 60)
    
    # Initialize the service
    try:
        db_url = os.getenv("DATABASE_URL") or "postgresql://postgres:postgres@localhost:54322/postgres"
        citations_service = CitationsService(db_url)
        print("✅ CitationsService initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize CitationsService: {e}")
        return False
    
    # Use the actual completion data from your stream response
    actual_completion_data = {
        "type": "complete",
        "ai_provider": "google",
        "ai_version": "gemini-flash-lite-latest",
        "model_used": "gemini-flash-lite-latest",
        "data_source": "Conversational AI",
        "processing_time": 2.719317,
        "projects_found": 0,
        "citations": [
            {
                "number": 1,
                "text": "Annex A - (PCP)",
                "chunk_id": 34566,
                "content_snippet": "cases of applications for joint calls with third countries (including scientific and technological organisations or agencies from third countries), international organisations or non -profit legal ent...",
                "metadata": {
                    "source": "intelligent_retrieval",
                    "document_type": "general_annexes",
                    "scope_identifier": None,
                    "relevance_score": 0.167704,
                    "primary_intent": "general"
                },
                "source_type": "intelligent_retrieval"
            },
            {
                "number": 2,
                "text": "Annex A - A-C);",
                "chunk_id": 34520,
                "content_snippet": "## A-C); – award criteria, mandatory documents and evaluation procedure (Annexes D -F); – legal and financial set -up of the grant agreements (Annex G); – specific conditions applying to actions which...",
                "metadata": {
                    "source": "intelligent_retrieval",
                    "document_type": "general_annexes",
                    "scope_identifier": None,
                    "relevance_score": 0.10937,
                    "primary_intent": "general"
                },
                "source_type": "intelligent_retrieval"
            }
        ],
        "confidence": 0.8,
        "grounded": True,
        "logs": {
            "question": "Test",
            "model_used": "gemini-flash-lite-latest",
            "phases": ["context_resolution", "ai_intent_analysis", "conversational", "answer_generation", "streaming_response"],
            "total_processing_time_ms": 2719,
            "projects_retrieved": 0,
            "projects_processed": 0,
            "success": True,
            "average_relevance_score": 0.8
        },
        "context_used": True,
        "resolved_question": "Test",
        "follow_up_suggestions": [
            "What are some open calls about energy?",
            "Show me completed AI projects",
            "How do I apply for Horizon Europe funding?"
        ],
        "projects_discussed": []
    }
    
    # Test saving citations
    try:
        citation_ids = citations_service.save_citations_from_stream_response(
            conversation_id=12345,  # Test conversation ID
            message_id=None,
            completion_data=actual_completion_data
        )
        
        print(f"✅ Saved {len(citation_ids)} citations successfully")
        for i, citation_id in enumerate(citation_ids):
            print(f"   Citation {i+1} ID: {citation_id}")
            
    except Exception as e:
        print(f"❌ Failed to save citations: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test retrieving citations
    try:
        citations = citations_service.get_citations_for_conversation(12345)
        print(f"✅ Retrieved {len(citations)} citations for conversation 12345")
        
        for citation in citations:
            print(f"   - {citation['citation_type']}: {citation['citation_text'][:50]}...")
            
    except Exception as e:
        print(f"❌ Failed to retrieve citations: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Debugging Citation Saving")
    print("=" * 70)
    
    success = test_with_actual_response()
    
    if success:
        print("\n✅ Debug test passed! Citations are being saved correctly.")
    else:
        print("\n❌ Debug test failed. There's an issue with citation saving.")