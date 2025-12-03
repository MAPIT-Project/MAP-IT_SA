#!/usr/bin/env python3
"""Test script for the simplified V3 agentic architecture."""

import asyncio
import os
import sys
import random

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def test_v3_architecture():
    """Test the simplified V3 architecture."""

    from app.services.conversation.conversation_manager import ConversationManager

    print("=" * 60)
    print("TESTING SIMPLIFIED V3 ARCHITECTURE")
    print("=" * 60)

    manager = ConversationManager()
    conversation_id = random.randint(100000, 999999)
    user_id = 1
    print(f"Using conversation ID: {conversation_id}")

    # Test 1: Simple call search
    print("\n" + "=" * 60)
    print("TEST 1: Search for funding calls")
    print("=" * 60)

    response1 = await manager.process_message_v3(
        conversation_id=conversation_id,
        user_message="Tell me about funding opportunities in clean energy research",
        user_id=user_id,
        streaming=False
    )

    print(f"\n📊 Response 1:")
    print(f"   Architecture: {response1.get('metadata', {}).get('architecture', 'unknown')}")
    print(f"   Iterations: {response1.get('metadata', {}).get('iterations', 0)}")
    print(f"   Tools used: {response1.get('metadata', {}).get('tools_used', [])}")
    answer1 = response1.get('response', '')
    print(f"   Answer length: {len(answer1)} chars")
    print(f"   Answer preview: {answer1[:300]}...")

    # Wait for memory to persist
    import time
    time.sleep(0.5)

    # Test 2: Follow-up complaint
    print("\n" + "=" * 60)
    print("TEST 2: Follow-up complaint - 'you just gave me 1 call wtf'")
    print("=" * 60)

    # Check memory state
    recent = manager._get_recent_messages_simple(conversation_id, limit=5)
    print(f"\n📋 Memory before test 2: {len(recent)} messages")
    for msg in recent[:3]:
        sender = msg.get('sender', 'unknown')
        text = msg.get('text', '')[:60]
        print(f"   - {sender}: {text}...")

    response2 = await manager.process_message_v3(
        conversation_id=conversation_id,
        user_message="you just gave me 1 call wtf",
        user_id=user_id,
        streaming=False
    )

    print(f"\n📊 Response 2:")
    print(f"   Architecture: {response2.get('metadata', {}).get('architecture', 'unknown')}")
    print(f"   Iterations: {response2.get('metadata', {}).get('iterations', 0)}")
    print(f"   Tools used: {response2.get('metadata', {}).get('tools_used', [])}")
    answer2 = response2.get('response', '')
    print(f"   Answer length: {len(answer2)} chars")
    print(f"   Answer preview: {answer2[:300]}...")

    # Validate test 2 - should search for more clean energy calls
    import re
    horizon_calls = re.findall(r'HORIZON-[A-Z0-9-]+', answer2, re.IGNORECASE)
    unique_calls = set(horizon_calls)
    clean_energy_terms = ['clean', 'energy', 'climate', 'renewable', 'hydrogen', 'battery']
    mentioned_terms = [t for t in clean_energy_terms if t.lower() in answer2.lower()]

    print(f"\n✅ VALIDATION:")
    print(f"   - HORIZON calls found: {len(unique_calls)}")
    print(f"   - Clean energy terms: {mentioned_terms}")

    # Test 3: Ordinal reference (if we got calls)
    if unique_calls:
        print("\n" + "=" * 60)
        print("TEST 3: Ordinal reference - 'tell me more about the first one'")
        print("=" * 60)

        response3 = await manager.process_message_v3(
            conversation_id=conversation_id,
            user_message="tell me more about the first one",
            user_id=user_id,
            streaming=False
        )

        print(f"\n📊 Response 3:")
        print(f"   Architecture: {response3.get('metadata', {}).get('architecture', 'unknown')}")
        print(f"   Iterations: {response3.get('metadata', {}).get('iterations', 0)}")
        answer3 = response3.get('response', '')
        print(f"   Answer length: {len(answer3)} chars")
        print(f"   Answer preview: {answer3[:300]}...")

    # Final verdict
    success = (
        response1.get('metadata', {}).get('architecture') == 'simplified_v3' and
        response2.get('metadata', {}).get('architecture') == 'simplified_v3' and
        len(answer1) > 100 and
        len(answer2) > 100
    )

    print("\n" + "=" * 60)
    if success:
        print("✅ V3 ARCHITECTURE TEST PASSED")
    else:
        print("❌ V3 ARCHITECTURE TEST FAILED")
    print("=" * 60)

    return success

if __name__ == "__main__":
    success = asyncio.run(test_v3_architecture())
    sys.exit(0 if success else 1)
