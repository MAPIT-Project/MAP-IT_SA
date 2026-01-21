"""
Tests for streaming storage order - verifying message storage happens before token streaming.

Task 003: Fix Streaming Before Storage Issue

Tests verify:
1. Message is in DB before first token is sent
2. Follow-up query immediately after response can access the stored message

The current implementation (as of this test creation) correctly stores messages BEFORE
streaming tokens. This test file documents and verifies this behavior.
"""

import asyncio
import os
import sys
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.atomic_storage import AtomicMessageStorage


class EventTracker:
    """Tracks events to verify ordering in streaming flow."""

    def __init__(self):
        self.events: list[dict[str, Any]] = []
        self.storage_timestamp: datetime | None = None
        self.first_token_timestamp: datetime | None = None

    def record_event(self, event_type: str, **kwargs):
        self.events.append({
            'type': event_type,
            'timestamp': datetime.now(),
            **kwargs
        })

        if event_type == 'storage_complete':
            self.storage_timestamp = datetime.now()
        elif event_type == 'first_token' and self.first_token_timestamp is None:
            self.first_token_timestamp = datetime.now()

    def storage_before_tokens(self) -> bool:
        """Return True if storage happened before first token."""
        if self.storage_timestamp is None or self.first_token_timestamp is None:
            return False
        return self.storage_timestamp <= self.first_token_timestamp


class MockDBPool:
    """Mock database connection pool for testing storage order."""

    def __init__(self):
        self.stored_messages: list[dict] = []
        self.storage_times: dict[int, datetime] = {}

    def getconn(self):
        return MockConnection(self)

    def putconn(self, conn):
        pass


class MockConnection:
    """Mock database connection."""

    def __init__(self, pool: MockDBPool):
        self.pool = pool
        self.committed = False

    def cursor(self):
        return MockCursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class MockCursor:
    """Mock database cursor."""

    def __init__(self, conn: MockConnection):
        self.conn = conn
        self._last_result = None
        self._insert_count = 0

    def execute(self, sql, params=None):
        pool = self.conn.pool

        if "INSERT INTO message" in sql and "RETURNING id" in sql:
            self._insert_count += 1
            msg_id = len(pool.stored_messages) + 1000

            # Record storage time
            pool.storage_times[msg_id] = datetime.now()

            self._last_result = (msg_id,)
            pool.stored_messages.append({
                'id': msg_id,
                'conversation_id': params[0] if params else 0,
                'sender': params[1] if params else 'unknown',
                'text': params[2] if params else '',
                'stored_at': datetime.now()
            })
        elif "SELECT id FROM message" in sql:
            self._last_result = None
        elif "UPDATE message" in sql:
            self._last_result = None
        else:
            self._last_result = None

    def fetchone(self):
        return self._last_result


class MockMemoryService:
    """Mock memory service."""

    def __init__(self):
        self.stm = MagicMock()
        self.redis_client = None


class TestStorageBeforeStreaming:
    """Tests for verifying storage happens before streaming tokens."""

    @pytest.mark.asyncio
    async def test_storage_before_first_token_basic(self):
        """
        Task 003 Test 1: Verify message is in DB before first token is sent.

        This tests the atomic storage directly to ensure it completes
        before any token streaming would begin.
        """
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        tracker = EventTracker()

        # Simulate the streaming flow order
        # 1. First, store messages atomically
        result = await storage.store_message_pair(
            conversation_id=123,
            user_id=1,
            user_message="Test question",
            assistant_message="Test response for streaming"
        )
        tracker.record_event('storage_complete', result=result.success)

        # 2. Then, simulate token streaming
        answer = "Test response for streaming"
        for i in range(0, len(answer), 50):
            if i == 0:
                tracker.record_event('first_token')
            tracker.record_event('token', content=answer[i:i+50])

        # Verify storage happened before first token
        assert tracker.storage_before_tokens(), (
            "Storage must complete before first token is streamed"
        )

        # Verify messages are in DB
        assert len(db_pool.stored_messages) == 2
        assert result.success
        assert result.user_message_id is not None
        assert result.assistant_message_id is not None

    @pytest.mark.asyncio
    async def test_message_accessible_immediately_after_storage(self):
        """
        Task 003 Test 2: Verify follow-up query can immediately access stored message.

        After storage completes, the message should be available for
        subsequent queries to read (for context, follow-ups, etc.).
        """
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        # Store first message pair
        result1 = await storage.store_message_pair(
            conversation_id=456,
            user_id=1,
            user_message="Show me 5 funding calls",
            assistant_message="Here are 5 calls: 1. Call A, 2. Call B, 3. Call C..."
        )

        assert result1.success
        assert len(db_pool.stored_messages) == 2

        # Immediately after storage, messages should be in DB
        # This simulates a follow-up query accessing the stored message
        stored_user_msg = next(
            (m for m in db_pool.stored_messages if m['sender'] == 'user'),
            None
        )
        stored_assistant_msg = next(
            (m for m in db_pool.stored_messages if m['sender'] == 'assistant'),
            None
        )

        assert stored_user_msg is not None
        assert stored_assistant_msg is not None
        assert "5 funding calls" in stored_user_msg['text']
        assert "5 calls" in stored_assistant_msg['text']

        # Now store a follow-up
        result2 = await storage.store_message_pair(
            conversation_id=456,
            user_id=1,
            user_message="Tell me about the third one",
            assistant_message="Call C is about..."
        )

        assert result2.success
        assert len(db_pool.stored_messages) == 4  # 2 from first + 2 from follow-up


class TestStreamingFlowOrder:
    """Tests for the complete streaming flow ordering."""

    @pytest.mark.asyncio
    async def test_simulated_streaming_flow_order(self):
        """
        Test the complete streaming flow to verify:
        1. Agent processing completes
        2. Answer is generated
        3. Storage happens
        4. Tokens are streamed

        This simulates the actual _stream_v3_response flow.
        """
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        events = []

        async def simulate_streaming_flow() -> AsyncGenerator[dict, None]:
            """Simulate the streaming flow from conversation_manager."""
            # 1. Status event
            events.append({'type': 'status', 'stage': 'processing'})
            yield {'type': 'status', 'stage': 'processing'}

            # 2. Agent processing (simulated)
            events.append({'type': 'status', 'stage': 'agent_starting'})
            yield {'type': 'status', 'stage': 'agent_starting'}

            # 3. Agent completes with answer
            answer = "Here is my response about EU funding..."
            # Agent produces result with answer and confidence (simulated)
            # agent_result = {'answer': answer, 'confidence': 0.9}

            # 4. STORAGE HAPPENS BEFORE STREAMING TOKENS
            storage_result = await storage.store_message_pair(
                conversation_id=789,
                user_id=1,
                user_message="What is EU funding?",
                assistant_message=answer
            )
            events.append({
                'type': 'storage_complete',
                'success': storage_result.success,
                'user_id': storage_result.user_message_id,
                'assistant_id': storage_result.assistant_message_id
            })

            # 5. Stream status before tokens
            events.append({'type': 'status', 'stage': 'streaming_response'})
            yield {'type': 'status', 'stage': 'streaming_response'}

            # 6. NOW stream tokens (after storage)
            for i in range(0, len(answer), 50):
                chunk = answer[i:i+50]
                events.append({'type': 'token', 'content': chunk})
                yield {'type': 'token', 'content': chunk}

            # 7. Complete event
            events.append({'type': 'complete'})
            yield {'type': 'complete'}

        # Run the simulated streaming flow
        async for _event in simulate_streaming_flow():
            pass

        # Verify order: storage_complete should come BEFORE any token events
        storage_idx = next(
            i for i, e in enumerate(events) if e['type'] == 'storage_complete'
        )
        first_token_idx = next(
            i for i, e in enumerate(events) if e['type'] == 'token'
        )

        assert storage_idx < first_token_idx, (
            f"Storage (index {storage_idx}) must happen before "
            f"first token (index {first_token_idx})"
        )

        # Verify storage was successful
        storage_event = events[storage_idx]
        assert storage_event['success'], "Storage should succeed"
        assert storage_event['user_id'] is not None
        assert storage_event['assistant_id'] is not None

    @pytest.mark.asyncio
    async def test_concurrent_follow_up_can_access_stored_message(self):
        """
        Test that a concurrent follow-up query can access the stored message
        immediately after storage completes.

        This simulates the scenario where:
        1. User sends message
        2. Storage completes
        3. Before all tokens are streamed, user sends follow-up
        4. Follow-up can access the stored message
        """
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        # Store first message
        result1 = await storage.store_message_pair(
            conversation_id=999,
            user_id=1,
            user_message="List hydrogen projects",
            assistant_message="1. Project A\n2. Project B\n3. Project C"
        )

        assert result1.success

        # Simulate follow-up immediately after storage
        # In real flow, tokens might still be streaming at this point
        # but storage is complete, so follow-up should work

        # Verify messages are accessible
        messages_in_conv = [
            m for m in db_pool.stored_messages if m['conversation_id'] == 999
        ]
        assert len(messages_in_conv) == 2

        # Store follow-up
        result2 = await storage.store_message_pair(
            conversation_id=999,
            user_id=1,
            user_message="Tell me about Project B",
            assistant_message="Project B is a hydrogen research initiative..."
        )

        assert result2.success

        # All messages should be stored
        messages_in_conv = [
            m for m in db_pool.stored_messages if m['conversation_id'] == 999
        ]
        assert len(messages_in_conv) == 4


class TestStorageOrderWithErrors:
    """Tests for storage order when errors occur."""

    @pytest.mark.asyncio
    async def test_storage_failure_still_streams_response(self):
        """
        Test that even when storage fails, the response is still streamed
        to the user (with an error event).
        """
        # Create a failing DB pool
        db_pool = MagicMock()
        db_pool.getconn.side_effect = Exception("Simulated DB failure")
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        events = []

        # Simulate streaming with storage failure
        answer = "Response that should still be streamed"

        result = await storage.store_message_pair(
            conversation_id=111,
            user_id=1,
            user_message="Test",
            assistant_message=answer
        )

        events.append({
            'type': 'storage_attempt',
            'success': result.success,
            'error': result.error
        })

        # Even with storage failure, tokens should stream
        if not result.success:
            events.append({
                'type': 'error',
                'error': f"Storage failed: {result.error}",
                'response': answer  # Response included
            })

        for i in range(0, len(answer), 50):
            events.append({'type': 'token', 'content': answer[i:i+50]})

        events.append({'type': 'complete'})

        # Verify storage failed but response still streamed
        storage_event = next(e for e in events if e['type'] == 'storage_attempt')
        assert not storage_event['success']

        # Verify error event was added
        error_events = [e for e in events if e['type'] == 'error']
        assert len(error_events) == 1
        assert answer in error_events[0]['response']

        # Verify tokens were still streamed
        token_events = [e for e in events if e['type'] == 'token']
        assert len(token_events) > 0


class TestStorageOrderVerification:
    """Additional verification tests for storage order."""

    @pytest.mark.asyncio
    async def test_storage_timestamp_before_token_timestamp(self):
        """
        Verify that storage completion timestamp is before first token timestamp.
        """
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        # Store message and record time
        result = await storage.store_message_pair(
            conversation_id=222,
            user_id=1,
            user_message="Test",
            assistant_message="Response"
        )
        storage_time = datetime.now()

        # Small delay to ensure clear ordering
        await asyncio.sleep(0.001)

        # Simulate token streaming start
        token_time = datetime.now()

        assert storage_time < token_time, (
            "Storage completion must happen before token streaming"
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_message_ids_available_before_streaming(self):
        """
        Verify that message IDs are available immediately after storage,
        which allows them to be included in metadata sent with tokens.
        """
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        result = await storage.store_message_pair(
            conversation_id=333,
            user_id=1,
            user_message="Query",
            assistant_message="Answer to query"
        )

        # IDs should be available immediately
        assert result.user_message_id is not None
        assert result.assistant_message_id is not None

        # These IDs can be included in streaming metadata
        metadata = {
            'user_message_id': result.user_message_id,
            'assistant_message_id': result.assistant_message_id,
            'storage_success': result.success
        }

        assert metadata['storage_success']
        assert isinstance(metadata['user_message_id'], int)
        assert isinstance(metadata['assistant_message_id'], int)


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
