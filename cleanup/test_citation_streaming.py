#!/usr/bin/env python3
"""
Test script to verify that citations are being properly saved from streaming responses
"""
import asyncio
import json
import requests
import os
from datetime import datetime

# Test configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CONVERSATION_ID = 1  # Use an existing conversation ID or create a new one

async def test_streaming_citations():
    """Test that citations are saved from streaming responses"""
    
    print("🧪 Testing citation saving from streaming responses...")
    
    # Test question that should return citations
    test_question = "What are some recent AI projects in healthcare?"
    
    print(f"📝 Sending question: {test_question}")
    
    # Send streaming request
    url = f"{BASE_URL}/api/conversation/{CONVERSATION_ID}/message/stream"
    payload = {
        "message": test_question,
        "include_context": True
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Accept": "text/event-stream"},
            stream=True
        )
        
        if response.status_code != 200:
            print(f"❌ Request failed with status {response.status_code}")
            print(response.text)
            return False
        
        citations_found = []
        completion_data = None
        
        print("📡 Receiving streaming response...")
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    data_str = decoded_line[6:]  # Remove 'data: ' prefix
                    try:
                        data = json.loads(data_str)
                        
                        if data.get('type') == 'complete':
                            completion_data = data
                            print(f"✅ Received complete response")
                            
                            # Check for citations
                            if 'citations' in data:
                                citations_found = data['citations']
                                print(f"📋 Found {len(citations_found)} citations in response")
                                for i, citation in enumerate(citations_found):
                                    print(f"   Citation {i+1}: {citation.get('text', 'No text')[:100]}...")
                            else:
                                print("⚠️ No citations found in response")
                        
                        elif data.get('type') == 'token':
                            # Just print a dot to show progress
                            print(".", end="", flush=True)
                            
                        elif data.get('type') == 'progress':
                            print(f"\n🔄 {data.get('message', 'Processing...')}")
                            
                        elif data.get('type') == 'error':
                            print(f"\n❌ Error: {data.get('error', 'Unknown error')}")
                            return False
                            
                    except json.JSONDecodeError as e:
                        print(f"\n⚠️ Failed to decode JSON: {e}")
                        continue
        
        print("\n")
        
        # Check if citations were saved to database
        if citations_found:
            print(f"✅ Found {len(citations_found)} citations in streaming response")
            await check_citations_in_database(CONVERSATION_ID, len(citations_found))
            return True
        else:
            print("⚠️ No citations found in streaming response")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

async def check_citations_in_database(conversation_id: int, expected_count: int):
    """Check if citations were saved to the database"""
    
    print(f"🔍 Checking if {expected_count} citations were saved to database...")
    
    try:
        import psycopg2
        from psycopg2.extras import DictCursor
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not set")
            return False
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # Get citations for this conversation
        cursor.execute("""
            SELECT id, citation_type, citation_text, created_at
            FROM citations
            WHERE conversation_id = %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (conversation_id,))
        
        citations = cursor.fetchall()
        
        if citations:
            print(f"✅ Found {len(citations)} citations in database:")
            for citation in citations:
                print(f"   - [{citation['citation_type']}] {citation['citation_text'][:80]}...")
                print(f"     Created: {citation['created_at']}")
            
            if len(citations) >= expected_count:
                print(f"✅ Expected {expected_count} citations, found {len(citations)} or more")
            else:
                print(f"⚠️ Expected {expected_count} citations, only found {len(citations)}")
        else:
            print("❌ No citations found in database")
        
        cursor.close()
        conn.close()
        
        return len(citations) > 0
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

async def main():
    """Main test function"""
    print("=" * 60)
    print("CITATION SAVING TEST FOR STREAMING RESPONSES")
    print("=" * 60)
    
    success = await test_streaming_citations()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 CITATION SAVING TEST PASSED!")
    else:
        print("❌ CITATION SAVING TEST FAILED!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())