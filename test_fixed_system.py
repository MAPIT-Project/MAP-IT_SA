#!/usr/bin/env python3
"""
Test the fixed conversation system with your specific query.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_your_query():
    """Test the exact query you mentioned."""
    
    print("🧪 Testing Your Specific Query")
    print("=" * 50)
    
    try:
        from app.services.conversation.conversation_manager import ConversationManager
        
        # Initialize conversation manager
        manager = ConversationManager()
        print("✅ ConversationManager initialized")
        
        # Your exact query
        test_query = "How much funding is available in Horizon Europe and how is it structured?"
        
        print(f"\n🔍 Testing query: '{test_query}'")
        print("Expected: Should use enhanced fallback with detailed Horizon Europe info")
        
        # Test both streaming and non-streaming
        print("\n1️⃣ Testing NON-STREAMING response...")
        
        result = await manager.process_message(
            conversation_id=1,
            user_message=test_query,
            user_id=1,
            streaming=False
        )
        
        if isinstance(result, dict) and 'response' in result:
            response = result['response']
            
            print(f"\n📄 Response received:")
            print(f"Length: {len(response)} characters")
            print(f"Contains 'Horizon Europe': {'horizon europe' in response.lower()}")
            print(f"Contains '95.5 billion': {'95.5 billion' in response.lower()}")
            print(f"Contains 'pillar': {'pillar' in response.lower()}")
            
            print(f"\n📝 Full Response:")
            print("-" * 60)
            print(response)
            print("-" * 60)
            
            # Check quality
            expected_terms = ["horizon europe", "95.5 billion", "pillar", "budget"]
            found_terms = [term for term in expected_terms if term.lower() in response.lower()]
            
            print(f"\n✅ Quality Check: {len(found_terms)}/{len(expected_terms)} expected terms found")
            print(f"Terms found: {found_terms}")
            
            if len(found_terms) >= 3 and len(response) > 300:
                print("🎉 NON-STREAMING: Success! Enhanced fallback is working!")
            else:
                print("⚠️ NON-STREAMING: Response quality could be better")
                
        else:
            print("❌ NON-STREAMING: Invalid response format")
            print(f"Received: {type(result)}")
            
        print(f"\n2️⃣ Testing STREAMING response...")
        
        # Test streaming response
        response_chunks = []
        
        async def collect_streaming_response():
            result = await manager.process_message(
                conversation_id=2,
                user_message=test_query,
                user_id=1,
                streaming=True
            )
            
            if hasattr(result, '__aiter__'):
                async for chunk in result:
                    if chunk.get('type') == 'token' and 'content' in chunk:
                        response_chunks.append(chunk['content'])
                    elif chunk.get('type') == 'complete':
                        break
            else:
                print("⚠️ Streaming result is not async generator")
                return str(result)
            
            return ''.join(response_chunks)
        
        streaming_response = await collect_streaming_response()
        
        print(f"\n📄 Streaming response received:")
        print(f"Length: {len(streaming_response)} characters")
        print(f"Contains 'Horizon Europe': {'horizon europe' in streaming_response.lower()}")
        
        print(f"\n📝 Streaming Response Preview:")
        print("-" * 60)
        print(streaming_response[:500] + "..." if len(streaming_response) > 500 else streaming_response)
        print("-" * 60)
        
        if "horizon europe" in streaming_response.lower() and len(streaming_response) > 300:
            print("🎉 STREAMING: Success! Enhanced fallback is working!")
        else:
            print("⚠️ STREAMING: Response quality could be better")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing system: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    
    print("🚀 Testing Fixed Conversation AI System")
    print("Testing the exact query that was failing...")
    
    success = asyncio.run(test_your_query())
    
    if success:
        print("\n🎯 Test completed! Check the output above to see if it's working correctly.")
        print("\nIf you're still getting poor responses, there might be another issue.")
        print("In that case, try restarting your FastAPI server to pick up the changes.")
    else:
        print("\n❌ Test failed - there are still issues with the system.")

if __name__ == "__main__":
    main()