#!/usr/bin/env python3
"""
Quick test to check if the conversation system is working without a running server.
"""

import os
import sys
import asyncio

# Add the project root to Python path
sys.path.append('/home/anmar/Documents/VSCODE_REPOS/MAP-IT_SA-1')

async def test_conversation_manager():
    """Test the conversation manager directly without HTTP."""
    
    print("🔄 Testing Conversation Manager directly...")
    
    try:
        # Import the conversation manager
        from app.services.conversation.conversation_manager import ConversationManager
        
        # Initialize conversation manager
        manager = ConversationManager()
        print("✅ ConversationManager initialized successfully")
        
        # Test queries that a research manager might have
        test_queries = [
            "What is Horizon Europe?",
            "Find AI projects in healthcare",
            "What are the trending research topics in quantum computing?",
            "Which countries receive the most Horizon Europe funding?",
        ]
        
        conversation_id = 1
        user_id = 1
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Test {i}: {query} ---")
            
            try:
                # Process the message
                result = await manager.process_message(
                    conversation_id=conversation_id,
                    user_message=query,
                    user_id=user_id,
                    streaming=False
                )
                
                if isinstance(result, dict):
                    response = result.get('response', '')
                    processing_time = result.get('processing_time', 0)
                    memory_stats = result.get('memory_stats', {})
                    retrieval_stats = result.get('retrieval_stats', {})
                    
                    print(f"✅ Success! Processing time: {processing_time:.2f}s")
                    print(f"Response length: {len(response)} chars")
                    print(f"Response preview: {response[:200]}...")
                    print(f"Memory stats: {memory_stats}")
                    print(f"Retrieval stats: {retrieval_stats}")
                    
                else:
                    print(f"❌ Unexpected result type: {type(result)}")
                    
            except Exception as e:
                print(f"❌ Error processing query: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n✅ Direct conversation manager test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize conversation manager: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_conversation_manager())