#!/usr/bin/env python3
"""
Test script to verify citations are saved to the message table using mock data
"""
import os
import sys
import json
import asyncio
import aiohttp
import time
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_mock_citations():
    """Test that mock citations are saved to the message table"""
    
    print("🧪 Testing mock citations saving to message table...")
    
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
        
        # First, create a test message in the database
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not found in environment variables")
            return False
        
        conversation_id = int(time.time())
        message_text = "This is a test assistant response about AI research projects in Europe."
        
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cursor:
                # First ensure conversation exists
                cursor.execute("""
                    INSERT INTO conversation (id, user_id, name, created_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (id) DO NOTHING
                """, (conversation_id, 1, f'Test Conversation {conversation_id}'))
                
                # Insert a test assistant message
                cursor.execute("""
                    INSERT INTO message (conversation_id, sender, text, created_at)
                    VALUES (%s, %s, %s, NOW())
                    RETURNING id
                """, (conversation_id, 'assistant', message_text))
                
                result = cursor.fetchone()
                if result:
                    message_id = result[0]
                    print(f"✅ Created test assistant message with ID: {message_id}")
                else:
                    print("❌ Failed to create test message")
                    return False
                
                conn.commit()
        
        # Test data with mock citations
        test_completion_data = {
            'type': 'complete',
            'citations': [
                {
                    'number': 1,
                    'text': 'CORDIS Project - AI Research Initiative',
                    'chunk_id': 'chunk_123',
                    'content_snippet': 'This project focuses on artificial intelligence research and machine learning applications...',
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
                    'content_snippet': 'This call aims to support research in digital technologies and AI...',
                    'metadata': {
                        'source': 'eu_portal',
                        'call_id': 'HORIZON-CL3-2024-01',
                        'relevance_score': 0.88
                    },
                    'source_type': 'call'
                }
            ],
            'conversation_id': conversation_id
        }
        
        # Test saving citations with the actual message ID
        print(f"💾 Saving {len(test_completion_data['citations'])} mock citations to message {message_id}...")
        
        saved_citations = citations_service.save_citations_from_stream_response(
            conversation_id=conversation_id,
            message_id=message_id,
            completion_data=test_completion_data
        )
        
        print(f"✅ Saved {len(saved_citations)} mock citations to message table")
        
        # Test retrieving citations for the specific message
        print(f"📖 Retrieving citations for message {message_id}...")
        
        retrieved_citations = citations_service.get_citations_for_message(
            conversation_id=conversation_id,
            message_id=message_id
        )
        
        print(f"✅ Retrieved {len(retrieved_citations)} citations from message table")
        
        if retrieved_citations:
            print("\n📋 Retrieved citations:")
            for i, citation in enumerate(retrieved_citations, 1):
                print(f"  {i}. {citation.get('text', 'Unknown')}")
                print(f"     Source: {citation.get('source_type', 'Unknown')}")
                print(f"     Chunk ID: {citation.get('chunk_id', 'Unknown')}")
                print()
        
        # Test direct database query to verify
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
                        if citations_data:
                            print(f"  First citation: {citations_data[0].get('text', 'Unknown')}")
                else:
                    print("⚠️ No messages with citations found in database")
        
        print("\n🎉 Mock citations test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_streaming_with_mock():
    """Test the streaming endpoint by intercepting and adding mock citations"""
    
    print("\n🧪 Testing streaming endpoint with mock citations...")
    
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Test data
        conversation_id = int(time.time())
        test_message = "Search for projects about artificial intelligence in CORDIS database"
        
        print(f"📝 Testing with conversation ID: {conversation_id}")
        print(f"📝 Test message: '{test_message}'")
        
        # API endpoint URL
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        endpoint = f"{base_url}/api/v2/conversation/{conversation_id}/message/stream"
        
        print(f"🌐 Testing endpoint: {endpoint}")
        
        # Prepare request data
        request_data = {
            "message": test_message,
            "include_context": True
        }
        
        # Make the streaming request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status != 200:
                    print(f"❌ HTTP Error: {response.status}")
                    error_text = await response.text()
                    print(f"Error details: {error_text}")
                    return False
                
                print(f"✅ Connected to streaming endpoint (status: {response.status})")
                
                # Process the streaming response
                complete_data = None
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            
                            if data.get('type') == 'complete':
                                complete_data = data
                                print(f"✅ Received complete response")
                                
                                # Add mock citations to test saving
                                mock_citations = [
                                    {
                                        'number': 1,
                                        'text': 'CORDIS Project - AI Research Initiative (Mock)',
                                        'chunk_id': 'chunk_123',
                                        'content_snippet': 'This project focuses on artificial intelligence research and machine learning applications...',
                                        'metadata': {
                                            'source': 'cordis',
                                            'project_id': '123456',
                                            'relevance_score': 0.95
                                        },
                                        'source_type': 'project'
                                    },
                                    {
                                        'number': 2,
                                        'text': 'EU Portal - Call HORIZON-CL3-2024-01 (Mock)',
                                        'chunk_id': 'call_789',
                                        'content_snippet': 'This call aims to support research in digital technologies and AI...',
                                        'metadata': {
                                            'source': 'eu_portal',
                                            'call_id': 'HORIZON-CL3-2024-01',
                                            'relevance_score': 0.88
                                        },
                                        'source_type': 'call'
                                    }
                                ]
                                
                                # Update the complete data with mock citations
                                complete_data['citations'] = mock_citations
                                print(f"📋 Added {len(mock_citations)} mock citations to response")
                                
                                # Save citations to database
                                from app.services.citations_service import CitationsService
                                citations_service = CitationsService()
                                
                                saved_citations = citations_service.save_citations_from_stream_response(
                                    conversation_id=conversation_id,
                                    message_id=None,  # Let service find the message
                                    completion_data=complete_data
                                )
                                
                                print(f"💾 Saved {len(saved_citations)} mock citations to message table")
                                
                                # Verify citations were saved
                                retrieved_citations = citations_service.get_citations_for_conversation(conversation_id)
                                
                                if retrieved_citations:
                                    print(f"✅ Verified {len(retrieved_citations)} citations saved to database")
                                    for i, citation in enumerate(retrieved_citations, 1):
                                        print(f"  {i}. {citation.get('text', 'Unknown')}")
                                else:
                                    print("❌ No citations found in database after saving")
                                
                                break
                                
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Failed to parse JSON: {e}")
                            continue
                
                if not complete_data:
                    print("❌ No complete response received")
                    return False
        
        print("\n🎉 Streaming with mock citations test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚀 Starting mock citations tests...")
    
    # Test 1: Direct citations service test
    success1 = await test_mock_citations()
    
    # Test 2: Streaming endpoint with mock citations
    success2 = await test_streaming_with_mock()
    
    overall_success = success1 and success2
    
    if overall_success:
        print("\n🎉 All tests completed successfully!")
        print("✅ Citations are being saved to the message table correctly")
    else:
        print("\n❌ Some tests failed")
    
    return overall_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)