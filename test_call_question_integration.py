#!/usr/bin/env python3
"""
Test the integrated call document system with a real question.

This tests the end-to-end flow:
1. User asks about a specific call
2. System detects call ID
3. Automatically fetches/caches documents
4. Retrieves relevant chunks
5. Generates answer using chunks
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

async def test_call_question():
    """Test asking a question about a specific call"""
    
    from app.services.conversation.conversation_manager import ConversationManager
    
    print("\n" + "="*70)
    print("🧪 Testing Call Document Integration")
    print("="*70 + "\n")
    
    # Initialize conversation manager
    print("📋 Initializing Conversation Manager...")
    manager = ConversationManager()
    print("✅ Initialized\n")
    
    # Test conversation
    conversation_id = 99999  # Test conversation
    user_id = 1
    
    # Test question about the call
    question = "What are the eligibility criteria for HORIZON-CL3-2025-02-CS-ECCC-01?"
    
    print(f"💬 Question: {question}\n")
    print("-" * 70)
    
    # Process the message
    print("🔄 Processing...\n")
    
    result = await manager.process_message(
        conversation_id=conversation_id,
        user_message=question,
        user_id=user_id,
        streaming=False
    )
    
    print("\n" + "-" * 70)
    print("📊 RESULTS")
    print("-" * 70 + "\n")
    
    if result:
        print(f"✅ Success: {result.get('success', False)}")
        print(f"📄 Response length: {len(result.get('response_text', ''))} chars")
        print(f"🔧 Tools executed: {result.get('tools_executed', False)}")
        print(f"📚 Context used: {result.get('context_used', False)}")
        
        if result.get('logs'):
            logs = result['logs']
            print(f"\n📝 Logs:")
            print(f"   - Phases: {logs.get('phases', [])}")
            print(f"   - Processing time: {logs.get('total_processing_time_ms', 0)}ms")
        
        print(f"\n💬 Response:")
        print("-" * 70)
        print(result.get('response_text', 'No response'))
        print("-" * 70)
        
        # Check if call documents were used
        if 'metadata' in result:
            metadata = result['metadata']
            if metadata.get('data_source'):
                print(f"\n📊 Data Source: {metadata['data_source']}")
        
    else:
        print("❌ No result returned")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(test_call_question())


