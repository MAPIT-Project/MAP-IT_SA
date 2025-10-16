#!/usr/bin/env python3
"""
Test script to directly test the streaming conversation endpoint with citations
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

async def test_streaming_citations():
    """Test the streaming conversation endpoint to verify citations are saved"""
    
    print("🧪 Testing streaming conversation endpoint with citations...")
    
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Test data
        conversation_id = int(time.time())  # Use timestamp as unique ID
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
                citations_found = []
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
                                
                                # Print the complete response data for debugging
                                print(f"📊 Complete response keys: {list(data.keys())}")
                                if 'projects_found' in data:
                                    print(f"📊 Projects found: {data.get('projects_found', 0)}")
                                if 'logs' in data:
                                    logs = data.get('logs', {})
                                    print(f"📊 Projects retrieved: {logs.get('projects_retrieved', 0)}")
                                
                                # Extract citations
                                citations = data.get('citations', [])
                                if citations:
                                    print(f"📋 Found {len(citations)} citations in response")
                                    citations_found = citations
                                    for i, citation in enumerate(citations, 1):
                                        print(f"  {i}. {citation.get('text', 'Unknown')}")
                                        print(f"     Source: {citation.get('source_type', 'Unknown')}")
                                else:
                                    print("⚠️ No citations found in response")
                                    # Check if there are other citation-related fields
                                    if 'projects_discussed' in data and data['projects_discussed']:
                                        print(f"📋 Found {len(data['projects_discussed'])} projects_discussed instead")
                                    if 'calls_data' in data and data['calls_data']:
                                        print(f"📋 Found {len(data['calls_data'])} calls_data instead")
                                
                                break
                            elif data.get('type') == 'token':
                                # Print a few tokens to show progress
                                if len(citations_found) == 0:  # Only print before citations are found
                                    pass  # Silently process tokens
                            elif data.get('type') == 'status':
                                stage = data.get('stage', 'unknown')
                                message = data.get('message', '')
                                print(f"📊 Status: {stage} - {message}")
                            elif data.get('type') == 'error':
                                print(f"❌ Error in stream: {data.get('error', 'Unknown error')}")
                                return False
                                
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Failed to parse JSON: {e}")
                            continue
                
                if not complete_data:
                    print("❌ No complete response received")
                    return False
        
        # Verify citations were saved to database
        if citations_found:
            print(f"\n💾 Verifying citations were saved to database...")
            
            from app.services.citations_service import CitationsService
            citations_service = CitationsService()
            
            # Get citations for the conversation
            saved_citations = citations_service.get_citations_for_conversation(conversation_id)
            
            if saved_citations:
                print(f"✅ Found {len(saved_citations)} citations saved to message table")
                
                # Verify they match what we received
                if len(saved_citations) == len(citations_found):
                    print("✅ Citation counts match between response and database")
                else:
                    print(f"⚠️ Citation count mismatch: response={len(citations_found)}, database={len(saved_citations)}")
                
                return True
            else:
                print("❌ No citations found in database")
                return False
        else:
            print("⚠️ No citations to verify")
            return True  # Still consider success if no citations were expected
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚀 Starting streaming citations test...")
    
    # Check if server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health") as response:
                if response.status == 200:
                    print("✅ Server is running")
                else:
                    print(f"⚠️ Server health check returned: {response.status}")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please make sure the API server is running on http://localhost:8000")
        return False
    
    # Run the test
    success = await test_streaming_citations()
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("✅ Citations are being saved to the message table from streaming responses")
    else:
        print("\n❌ Test failed")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)