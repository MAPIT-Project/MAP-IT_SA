#!/usr/bin/env python3
"""Test script for the simplified V3 agentic architecture."""

import asyncio
import os
import random
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()


async def test_v3_streaming():
    """Test V3 streaming support."""
    from app.services.conversation.conversation_manager import ConversationManager

    print("\n" + "=" * 60)
    print("TEST 4: V3 STREAMING")
    print("=" * 60)

    manager = ConversationManager()
    conversation_id = random.randint(200000, 299999)

    print(f"\nUsing conversation ID: {conversation_id}")
    print("Streaming query: 'Show me AI funding calls'\n")

    result = await manager.process_message_v3(
        conversation_id=conversation_id,
        user_message="Show me AI funding calls",
        user_id=1,
        streaming=True,
    )

    # Collect streaming events
    events = []
    async for event in result:
        events.append(event)
        event_type = event.get("type", "unknown")

        if event_type == "status":
            print(f"  📊 STATUS: {event.get('stage')} - {event.get('message')}")
        elif event_type == "agent_thinking":
            print(
                f"  🧠 THINKING (iter {event.get('iteration')}): {event.get('thought', '')[:60]}..."
            )
        elif event_type == "tool_call":
            print(f"  🔧 TOOL CALL: {event.get('tool_name')} (iter {event.get('iteration')})")
        elif event_type == "tool_result":
            print(f"  ✅ TOOL RESULT: {event.get('result_summary', '')[:60]}...")
        elif event_type == "token":
            pass  # Don't print every token
        elif event_type == "complete":
            meta = event.get("metadata", {})
            print("\n  🏁 COMPLETE:")
            print(f"     Architecture: {meta.get('architecture')}")
            print(f"     Iterations: {meta.get('iterations')}")
            print(f"     Tools: {meta.get('tools_used')}")
            print(f"     Time: {meta.get('processing_time_ms', 0):.0f}ms")
        elif event_type == "error":
            print(f"  ❌ ERROR: {event.get('error')}")

    # Collect response from tokens
    response_text = "".join([e.get("content", "") for e in events if e.get("type") == "token"])
    print(f"\n📝 Response ({len(response_text)} chars): {response_text[:200]}...")

    # Validate
    has_complete = any(e.get("type") == "complete" for e in events)
    has_tokens = any(e.get("type") == "token" for e in events)
    is_v3 = any(e.get("metadata", {}).get("architecture") == "simplified_v3" for e in events)

    success = has_complete and has_tokens and is_v3
    print(f"\n{'✅ STREAMING TEST PASSED' if success else '❌ STREAMING TEST FAILED'}")

    return success


async def test_v3_architecture():
    """Test the simplified V3 architecture (non-streaming)."""

    from app.services.conversation.conversation_manager import ConversationManager

    print("=" * 60)
    print("TESTING SIMPLIFIED V3 ARCHITECTURE")
    print("=" * 60)

    manager = ConversationManager()
    conversation_id = random.randint(100000, 199999)
    user_id = 1
    print(f"Using conversation ID: {conversation_id}")

    # Test 1: Simple call search
    print("\n" + "=" * 60)
    print("TEST 1: Search for funding calls (non-streaming)")
    print("=" * 60)

    response1 = await manager.process_message_v3(
        conversation_id=conversation_id,
        user_message="Tell me about funding opportunities in clean energy research",
        user_id=user_id,
        streaming=False,
    )

    print("\n📊 Response 1:")
    print(f"   Architecture: {response1.get('metadata', {}).get('architecture', 'unknown')}")
    print(f"   Iterations: {response1.get('metadata', {}).get('iterations', 0)}")
    print(f"   Tools used: {response1.get('metadata', {}).get('tools_used', [])}")
    answer1 = response1.get("response", "")
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
        sender = msg.get("sender", "unknown")
        text = msg.get("text", "")[:60]
        print(f"   - {sender}: {text}...")

    response2 = await manager.process_message_v3(
        conversation_id=conversation_id,
        user_message="you just gave me 1 call wtf",
        user_id=user_id,
        streaming=False,
    )

    print("\n📊 Response 2:")
    print(f"   Architecture: {response2.get('metadata', {}).get('architecture', 'unknown')}")
    print(f"   Iterations: {response2.get('metadata', {}).get('iterations', 0)}")
    print(f"   Tools used: {response2.get('metadata', {}).get('tools_used', [])}")
    answer2 = response2.get("response", "")
    print(f"   Answer length: {len(answer2)} chars")
    print(f"   Answer preview: {answer2[:300]}...")

    # Validate test 2 - should search for more clean energy calls
    import re

    horizon_calls = re.findall(r"HORIZON-[A-Z0-9-]+", answer2, re.IGNORECASE)
    unique_calls = set(horizon_calls)
    clean_energy_terms = ["clean", "energy", "climate", "renewable", "hydrogen", "battery"]
    mentioned_terms = [t for t in clean_energy_terms if t.lower() in answer2.lower()]

    print("\n✅ VALIDATION:")
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
            streaming=False,
        )

        print("\n📊 Response 3:")
        print(f"   Architecture: {response3.get('metadata', {}).get('architecture', 'unknown')}")
        print(f"   Iterations: {response3.get('metadata', {}).get('iterations', 0)}")
        answer3 = response3.get("response", "")
        print(f"   Answer length: {len(answer3)} chars")
        print(f"   Answer preview: {answer3[:300]}...")

    # Non-streaming verdict
    non_streaming_success = (
        response1.get("metadata", {}).get("architecture") == "simplified_v3"
        and response2.get("metadata", {}).get("architecture") == "simplified_v3"
        and len(answer1) > 100
        and len(answer2) > 100
    )

    print("\n" + "=" * 60)
    if non_streaming_success:
        print("✅ NON-STREAMING TESTS PASSED")
    else:
        print("❌ NON-STREAMING TESTS FAILED")
    print("=" * 60)

    # Test 4: Streaming
    streaming_success = await test_v3_streaming()

    # Final verdict
    all_success = non_streaming_success and streaming_success

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"  Non-streaming: {'✅ PASS' if non_streaming_success else '❌ FAIL'}")
    print(f"  Streaming:     {'✅ PASS' if streaming_success else '❌ FAIL'}")
    print("=" * 60)
    if all_success:
        print("✅ ALL V3 TESTS PASSED")
    else:
        print("❌ SOME V3 TESTS FAILED")
    print("=" * 60)

    return all_success


if __name__ == "__main__":
    success = asyncio.run(test_v3_architecture())
    sys.exit(0 if success else 1)
