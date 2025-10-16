#!/usr/bin/env python3
"""
Direct test of the citations service to verify it works correctly
"""
import os
import json
from app.services.citations_service import CitationsService

def test_citations_service():
    """Test the citations service directly"""
    
    print("🧪 Testing citations service directly...")
    
    # Initialize the service
    try:
        citations_service = CitationsService()
        print("✅ Citations service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize citations service: {e}")
        return False
    
    # Create test completion data with citations
    test_completion_data = {
        "type": "complete",
        "citations": [
            {
                "number": 1,
                "text": "Test citation 1 - AI in Healthcare Project",
                "chunk_id": "chunk_123",
                "metadata": {
                    "relevance_score": 0.95,
                    "source": "CORDIS"
                }
            },
            {
                "number": 2,
                "text": "Test citation 2 - Machine Learning for Medical Diagnosis",
                "chunk_id": "chunk_456",
                "metadata": {
                    "relevance_score": 0.87,
                    "source": "CORDIS"
                }
            }
        ],
        "projects_discussed": [
            {
                "id": "project_789",
                "title": "AI Healthcare Project",
                "acronym": "AIHEALTH",
                "relevance_score": 0.92
            }
        ]
    }
    
    # Test saving citations
    conversation_id = 999  # Test conversation ID
    message_id = None
    
    try:
        citation_ids = citations_service.save_citations_from_stream_response(
            conversation_id=conversation_id,
            message_id=message_id,
            completion_data=test_completion_data
        )
        
        if citation_ids:
            print(f"✅ Successfully saved {len(citation_ids)} citations to database")
            print(f"   Citation IDs: {citation_ids}")
        else:
            print("⚠️ No citations were saved")
            return False
            
    except Exception as e:
        print(f"❌ Failed to save citations: {e}")
        return False
    
    # Test retrieving citations
    try:
        citations = citations_service.get_citations_for_conversation(conversation_id)
        
        if citations:
            print(f"✅ Successfully retrieved {len(citations)} citations from database")
            for citation in citations:
                print(f"   - [{citation['citation_type']}] {citation['citation_text'][:50]}...")
        else:
            print("⚠️ No citations found in database")
            return False
            
    except Exception as e:
        print(f"❌ Failed to retrieve citations: {e}")
        return False
    
    return True

def check_citations_table():
    """Check if the citations table exists"""
    
    print("🔍 Checking if citations table exists...")
    
    try:
        import psycopg2
        from psycopg2.extras import DictCursor
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not set")
            return False
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'citations'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("✅ Citations table exists")
            
            # Get table structure
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'citations'
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            print("📋 Table structure:")
            for column in columns:
                nullable_text = 'NULL' if column['is_nullable'] == 'YES' else 'NOT NULL'
                print(f"   - {column['column_name']}: {column['data_type']} ({nullable_text})")
                
        else:
            print("❌ Citations table does not exist")
            return False
        
        cursor.close()
        conn.close()
        
        return table_exists
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("DIRECT CITATIONS SERVICE TEST")
    print("=" * 60)
    
    # Check if table exists
    if not check_citations_table():
        print("❌ Citations table does not exist - please run the migration first")
        return
    
    print()
    
    # Test the service
    success = test_citations_service()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 CITATIONS SERVICE TEST PASSED!")
        print("The citations service is working correctly and can save/retrieve citations.")
    else:
        print("❌ CITATIONS SERVICE TEST FAILED!")
    print("=" * 60)

if __name__ == "__main__":
    main()