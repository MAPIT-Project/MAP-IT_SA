"""
Test script to verify the citations implementation
"""
import os
import sys
import json
from app.services.citations_service import CitationsService

def test_citations_service():
    """Test the citations service"""
    print("🧪 Testing Citations Service")
    print("=" * 50)
    
    # Initialize the service
    try:
        # Use the database URL from docker-compose if not available in environment
        db_url = os.getenv("DATABASE_URL") or "postgresql://postgres:postgres@localhost:54322/postgres"
        citations_service = CitationsService(db_url)
        print("✅ CitationsService initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize CitationsService: {e}")
        return False
    
    # Test creating the citations table
    try:
        citations_service.create_citations_table()
        print("✅ Citations table created/verified successfully")
    except Exception as e:
        print(f"❌ Failed to create citations table: {e}")
        return False
    
    # Test saving citations from a mock completion data
    try:
        mock_completion_data = {
            'type': 'complete',
            'citations': [
                {
                    'number': 1,
                    'text': 'Annex A - (PCP)',
                    'chunk_id': 34566,
                    'content_snippet': 'cases of applications for joint calls with third countries',
                    'metadata': {
                        'source': 'intelligent_retrieval',
                        'document_type': 'general_annexes',
                        'relevance_score': 0.167704
                    }
                },
                {
                    'number': 2,
                    'text': 'Annex A - A-C)',
                    'chunk_id': 34520,
                    'content_snippet': 'award criteria, mandatory documents and evaluation procedure',
                    'metadata': {
                        'source': 'intelligent_retrieval',
                        'document_type': 'general_annexes',
                        'relevance_score': 0.10937
                    }
                }
            ],
            'projects_discussed': [
                {
                    'id': 'test_project_1',
                    'title': 'Test Project 1',
                    'acronym': 'TP1',
                    'relevance_score': 0.85
                }
            ],
            'calls_data': [
                {
                    'identifier': 'test_call_1',
                    'title': 'Test Call 1'
                }
            ]
        }
        
        citation_ids = citations_service.save_citations_from_stream_response(
            conversation_id=999,  # Test conversation ID
            message_id=None,
            completion_data=mock_completion_data
        )
        
        print(f"✅ Saved {len(citation_ids)} citations successfully")
        for i, citation_id in enumerate(citation_ids):
            print(f"   Citation {i+1} ID: {citation_id}")
            
    except Exception as e:
        print(f"❌ Failed to save citations: {e}")
        return False
    
    # Test retrieving citations
    try:
        citations = citations_service.get_citations_for_conversation(999)
        print(f"✅ Retrieved {len(citations)} citations for conversation 999")
        
        for citation in citations:
            print(f"   - {citation['citation_type']}: {citation['citation_text']}")
            
    except Exception as e:
        print(f"❌ Failed to retrieve citations: {e}")
        return False
    
    print("\n🎉 All citation service tests passed!")
    return True

def test_database_connection():
    """Test database connection"""
    print("🔗 Testing Database Connection")
    print("=" * 50)
    
    try:
        import psycopg2
        from psycopg2.extras import DictCursor
        
        db_url = os.getenv("DATABASE_URL") or "postgresql://postgres:postgres@localhost:54322/postgres"
        print(f"🔗 Using database URL: {db_url}")
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # Test basic query
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"✅ Connected to PostgreSQL: {version[0]}")
        
        # Check if citations table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'citations'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("✅ Citations table exists")
        else:
            print("⚠️ Citations table does not exist yet")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Citations Implementation")
    print("=" * 60)
    
    # Test database connection first
    if not test_database_connection():
        print("\n❌ Database connection tests failed")
        sys.exit(1)
    
    print()
    
    # Test citations service
    if not test_citations_service():
        print("\n❌ Citations service tests failed")
        sys.exit(1)
    
    print("\n✅ All tests passed! Citations implementation is working correctly.")