#!/usr/bin/env python3
"""
Test script to verify citations are saved to the message table
"""
import os
import sys
import json
import asyncio
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_citations_message_table():
    """Test that citations are saved to the message table"""
    
    print("🧪 Testing citations saving to message table...")
    
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Initialize citations service
        from app.services.citations_service import CitationsService
        
        citations_service = CitationsService()
        print("✅ Citations service initialized")
        
        # Create the citations column if it doesn't exist
        citations_service.create_citations_column()
        print("✅ Citations column ensured to exist")
        
        # Test data with citations
        test_completion_data = {
            'type': 'complete',
            'citations': [
                {
                    'number': 1,
                    'text': 'CORDIS Project - AI Research',
                    'chunk_id': 'chunk_123',
                    'content_snippet': 'This project focuses on artificial intelligence research...',
                    'metadata': {
                        'source': 'cordis',
                        'project_id': '123456',
                        'relevance_score': 0.95
                    },
                    'source_type': 'project'
                },
                {
                    'number': 2,
                    'text': 'EU Portal - Call HORIZON-CL3-2024-01',
                    'chunk_id': 'call_789',
                    'content_snippet': 'This call aims to support research in digital technologies...',
                    'metadata': {
                        'source': 'eu_portal',
                        'call_id': 'HORIZON-CL3-2024-01',
                        'relevance_score': 0.88
                    },
                    'source_type': 'call'
                }
            ],
            'conversation_id': 12345
        }
        
        # Test saving citations
        conversation_id = 12345
        message_id = None  # Let the service find the most recent message
        
        print(f"💾 Saving {len(test_completion_data['citations'])} citations to message table...")
        
        saved_citations = citations_service.save_citations_from_stream_response(
            conversation_id=conversation_id,
            message_id=message_id,
            completion_data=test_completion_data
        )
        
        print(f"✅ Saved {len(saved_citations)} citations to message table")
        
        # Test retrieving citations
        print(f"📖 Retrieving citations for conversation {conversation_id}...")
        
        retrieved_citations = citations_service.get_citations_for_conversation(conversation_id)
        
        print(f"✅ Retrieved {len(retrieved_citations)} citations from message table")
        
        if retrieved_citations:
            print("\n📋 Retrieved citations:")
            for i, citation in enumerate(retrieved_citations, 1):
                print(f"  {i}. {citation.get('text', 'Unknown')}")
                print(f"     Source: {citation.get('source_type', 'Unknown')}")
                print(f"     Chunk ID: {citation.get('chunk_id', 'Unknown')}")
                print()
        
        # Test direct database query to verify
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            with psycopg2.connect(db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, sender, text, citations, created_at
                        FROM message 
                        WHERE conversation_id = %s AND citations IS NOT NULL
                        ORDER BY created_at DESC
                        LIMIT 5
                    """, (conversation_id,))
                    
                    messages_with_citations = cursor.fetchall()
                    
                    if messages_with_citations:
                        print(f"✅ Found {len(messages_with_citations)} message(s) with citations in database")
                        for msg in messages_with_citations:
                            citations_data = msg.get('citations', [])
                            print(f"  Message ID: {msg['id']}, Citations: {len(citations_data)}")
                    else:
                        print("⚠️ No messages with citations found in database")
        
        print("\n🎉 Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_citations_message_table())
    sys.exit(0 if success else 1)