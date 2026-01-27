#!/usr/bin/env python3
"""
Test the full system with real questions about the call.
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

async def test_questions():
    """Test multiple questions about the call"""
    
    from app.services.conversation.conversation_manager import ConversationManager
    
    print("\n" + "="*70)
    print("🧪 Testing Full System with Real Questions")
    print("="*70 + "\n")
    
    # Initialize
    print("📋 Initializing Conversation Manager...")
    manager = ConversationManager()
    print("✅ Initialized\n")
    
    conversation_id = 99999
    user_id = 1
    
    # Test questions
    questions = [
        "What are the eligibility criteria for HORIZON-CL3-2025-02-CS-ECCC-01?",
        "What is the budget for HORIZON-CL3-2025-02-CS-ECCC-01?",
        "What is the deadline for HORIZON-CL3-2025-02-CS-ECCC-01?",
    ]
    
    for i, question in enumerate(questions, 1):
        print("\n" + "="*70)
        print(f"Question {i}/{len(questions)}")
        print("="*70)
        print(f"💬 {question}\n")
        print("-" * 70)
        
        try:
            result = await manager.process_message(
                conversation_id=conversation_id,
                user_message=question,
                user_id=user_id,
                streaming=False
            )
            
            if result and result.get('response_text'):
                response = result['response_text']
                print(f"\n✅ Response ({len(response)} chars):")
                print("-" * 70)
                print(response[:500] + ("..." if len(response) > 500 else ""))
                print("-" * 70)
                
                # Check metadata
                if result.get('logs'):
                    logs = result['logs']
                    print("\n📊 Stats:")
                    print(f"   Processing time: {logs.get('total_processing_time_ms', 0)}ms")
                    print(f"   Phases: {', '.join(logs.get('phases', []))}")
                
                # Check if call documents were used
                context_used = result.get('context_used', False)
                print(f"   Context used: {context_used}")
                
            else:
                print("❌ No response generated")
                if result:
                    print(f"   Error: {result.get('error', 'Unknown')}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("✅ Test Complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_questions())


