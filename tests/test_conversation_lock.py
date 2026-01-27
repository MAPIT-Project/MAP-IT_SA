"""
Tests for conversation locking to prevent race conditions.

Tests:
- ConversationLockManager basic functionality
- Concurrent message handling with locking
- Lock timeout behavior
- Conversation isolation
- Message ordering under concurrent load
"""

import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.conversation_lock import ConversationLockManager, LockInfo, get_conversation_lock


class TestConversationLockManagerBasics:
    """Tests for basic ConversationLockManager functionality."""

    @pytest.fixture
    def fresh_lock_manager(self):
        """Create a fresh lock manager for each test."""
        # Reset singleton for testing
        ConversationLockManager._instance = None
        return ConversationLockManager()

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test that get_instance returns the same instance."""
        ConversationLockManager._instance = None
        manager1 = await ConversationLockManager.get_instance()
        manager2 = await ConversationLockManager.get_instance()
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_lock_acquisition(self, fresh_lock_manager):
        """Test basic lock acquisition and release."""
        manager = fresh_lock_manager
        conversation_id = 12345

        async with manager.acquire(conversation_id, holder_id="test"):
            # Lock should be held
            assert await manager.is_locked(conversation_id)

        # Lock should be released
        assert not await manager.is_locked(conversation_id)

    @pytest.mark.asyncio
    async def test_lock_info_tracking(self, fresh_lock_manager):
        """Test that lock info is tracked during acquisition."""
        manager = fresh_lock_manager
        conversation_id = 67890
        holder_id = "test_holder"

        async with manager.acquire(conversation_id, holder_id=holder_id) as lock_info:
            assert isinstance(lock_info, LockInfo)
            assert lock_info.conversation_id == conversation_id
            assert lock_info.holder_id == holder_id
            assert isinstance(lock_info.acquired_at, datetime)

            # Info should be accessible via get_lock_info
            stored_info = await manager.get_lock_info(conversation_id)
            assert stored_info is not None
            assert stored_info.holder_id == holder_id

        # Info should be cleared after release
        assert await manager.get_lock_info(conversation_id) is None

    @pytest.mark.asyncio
    async def test_multiple_conversations_independent(self, fresh_lock_manager):
        """Test that different conversations have independent locks."""
        manager = fresh_lock_manager
        conv_1 = 111
        conv_2 = 222

        async with manager.acquire(conv_1, holder_id="holder_1"):
            # Can still acquire lock for different conversation
            async with manager.acquire(conv_2, holder_id="holder_2"):
                assert await manager.is_locked(conv_1)
                assert await manager.is_locked(conv_2)

    @pytest.mark.asyncio
    async def test_get_stats(self, fresh_lock_manager):
        """Test statistics collection."""
        manager = fresh_lock_manager

        async with manager.acquire(100, holder_id="stats_test"):
            stats = manager.get_stats()
            assert stats["total_locks_created"] >= 1
            assert stats["currently_locked"] >= 1
            assert "100" in stats["active_lock_info"]


class TestConversationLockTimeout:
    """Tests for lock timeout behavior."""

    @pytest.mark.asyncio
    async def test_lock_timeout_on_contention(self):
        """Test that lock acquisition times out when held."""
        ConversationLockManager._instance = None
        manager = ConversationLockManager()
        conversation_id = 333

        async def hold_lock():
            async with manager.acquire(conversation_id, timeout=10.0, holder_id="holder"):
                await asyncio.sleep(2.0)  # Hold for 2 seconds

        async def try_acquire_with_short_timeout():
            await asyncio.sleep(0.1)  # Let the first one acquire
            with pytest.raises(TimeoutError):
                async with manager.acquire(conversation_id, timeout=0.5, holder_id="waiter"):
                    pass

        # Run concurrently
        await asyncio.gather(hold_lock(), try_acquire_with_short_timeout())

    @pytest.mark.asyncio
    async def test_lock_acquired_after_release(self):
        """Test that lock can be acquired after release."""
        ConversationLockManager._instance = None
        manager = ConversationLockManager()
        conversation_id = 444
        acquired_order = []

        async def holder(name: str, hold_time: float):
            async with manager.acquire(conversation_id, timeout=5.0, holder_id=name):
                acquired_order.append(name)
                await asyncio.sleep(hold_time)

        # First holder holds briefly
        await holder("first", 0.1)

        # Second holder should be able to acquire
        await holder("second", 0.1)

        assert acquired_order == ["first", "second"]


class TestConcurrentMessages:
    """Tests for concurrent message handling."""

    @pytest.fixture
    def mock_conversation_manager(self):
        """Create a mock conversation manager with lock integration."""
        manager = MagicMock()
        manager.stored_messages = []
        manager.message_order = []

        async def mock_store(conv_id, user_id, message):
            # Simulate some processing time
            await asyncio.sleep(0.05)
            msg_id = len(manager.stored_messages) + 1
            manager.stored_messages.append(
                {
                    "id": msg_id,
                    "conversation_id": conv_id,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            manager.message_order.append(message)
            return msg_id

        manager.store_message = mock_store
        return manager

    @pytest.mark.asyncio
    async def test_five_concurrent_messages_no_duplicates(self, mock_conversation_manager):
        """
        Test that 5 concurrent messages to the same conversation:
        1. All messages are stored
        2. No duplicates
        3. Correct ordering (sequential due to locking)

        This is the key test specified in Task 001.
        """
        ConversationLockManager._instance = None
        manager = ConversationLockManager()
        conversation_id = 555
        messages = [f"Message {i}" for i in range(1, 6)]
        stored_results = []

        async def send_message(message: str):
            """Simulate sending a message with locking."""
            holder = f"sender_{message}"
            async with manager.acquire(conversation_id, timeout=30.0, holder_id=holder):
                result = await mock_conversation_manager.store_message(conversation_id, 1, message)
                stored_results.append(result)
                return result

        # Send all 5 messages concurrently
        tasks = [send_message(msg) for msg in messages]
        await asyncio.gather(*tasks)

        # Verify all messages stored
        assert len(mock_conversation_manager.stored_messages) == 5, (
            f"Expected 5 messages, got {len(mock_conversation_manager.stored_messages)}"
        )

        # Verify no duplicates (check unique IDs)
        ids = [m["id"] for m in mock_conversation_manager.stored_messages]
        assert len(ids) == len(set(ids)), "Duplicate message IDs found"

        # Verify message content uniqueness
        contents = [m["message"] for m in mock_conversation_manager.stored_messages]
        assert len(contents) == len(set(contents)), "Duplicate message content found"

        # Verify all original messages are present
        for msg in messages:
            assert msg in contents, f"Message '{msg}' not found in stored messages"

    @pytest.mark.asyncio
    async def test_messages_processed_sequentially(self, mock_conversation_manager):
        """Test that messages are processed one at a time with locking."""
        ConversationLockManager._instance = None
        manager = ConversationLockManager()
        conversation_id = 666
        processing_times = []

        async def send_message_with_timing(message: str):
            """Track when message processing starts and ends."""
            async with manager.acquire(conversation_id, timeout=30.0, holder_id=message):
                start = datetime.now()
                await mock_conversation_manager.store_message(conversation_id, 1, message)
                end = datetime.now()
                processing_times.append({"message": message, "start": start, "end": end})

        # Send 3 messages concurrently
        messages = ["A", "B", "C"]
        tasks = [send_message_with_timing(msg) for msg in messages]
        await asyncio.gather(*tasks)

        # Verify no overlapping processing times
        # Sort by start time
        processing_times.sort(key=lambda x: x["start"])

        for i in range(len(processing_times) - 1):
            current = processing_times[i]
            next_item = processing_times[i + 1]
            # Next message should start after current ends
            assert next_item["start"] >= current["end"], (
                f"Message {next_item['message']} started before {current['message']} finished"
            )


class TestConversationIsolation:
    """Tests for conversation isolation."""

    @pytest.mark.asyncio
    async def test_different_conversations_parallel(self):
        """Test that different conversations can be processed in parallel."""
        ConversationLockManager._instance = None
        manager = ConversationLockManager()

        conv_1_processing = False
        conv_2_processing = False
        both_processing = False

        async def process_conv_1():
            nonlocal conv_1_processing, both_processing
            async with manager.acquire(1, holder_id="conv_1"):
                conv_1_processing = True
                await asyncio.sleep(0.1)
                if conv_2_processing:
                    both_processing = True
                await asyncio.sleep(0.1)
                conv_1_processing = False

        async def process_conv_2():
            nonlocal conv_2_processing, both_processing
            await asyncio.sleep(0.05)  # Start slightly after conv_1
            async with manager.acquire(2, holder_id="conv_2"):
                conv_2_processing = True
                await asyncio.sleep(0.1)
                if conv_1_processing:
                    both_processing = True
                await asyncio.sleep(0.1)
                conv_2_processing = False

        await asyncio.gather(process_conv_1(), process_conv_2())

        # Both should have been processing at the same time
        assert both_processing, "Different conversations should be processed in parallel"

    @pytest.mark.asyncio
    async def test_same_conversation_serial(self):
        """Test that same conversation messages are processed serially."""
        ConversationLockManager._instance = None
        manager = ConversationLockManager()
        conversation_id = 777

        processing_count = 0
        max_concurrent = 0

        async def process_message(msg_id: int):
            nonlocal processing_count, max_concurrent
            async with manager.acquire(conversation_id, holder_id=f"msg_{msg_id}"):
                processing_count += 1
                max_concurrent = max(max_concurrent, processing_count)
                await asyncio.sleep(0.05)
                processing_count -= 1

        # Send 5 messages concurrently
        tasks = [process_message(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Max concurrent should be 1 (only one at a time)
        assert max_concurrent == 1, f"Expected max 1 concurrent, got {max_concurrent}"


class TestStaleLocksCleanup:
    """Tests for stale lock cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_stale_locks(self):
        """Test that stale locks can be cleaned up."""
        ConversationLockManager._instance = None
        manager = ConversationLockManager()
        conversation_id = 888

        # Manually create a "stale" lock state by acquiring
        lock = await manager._get_or_create_lock(conversation_id)
        await lock.acquire()

        # Manually add lock info with old timestamp
        from datetime import timedelta

        old_time = datetime.now() - timedelta(seconds=400)
        manager._lock_info[conversation_id] = LockInfo(
            conversation_id=conversation_id, acquired_at=old_time, holder_id="stale_holder"
        )

        # Run cleanup with short max age
        await manager.cleanup_stale_locks(max_age_seconds=300)

        # Lock info should be cleared
        assert conversation_id not in manager._lock_info


class TestGetConversationLockHelper:
    """Tests for the get_conversation_lock helper function."""

    @pytest.mark.asyncio
    async def test_helper_function_works(self):
        """Test that the helper function acquires locks correctly."""
        ConversationLockManager._instance = None
        conversation_id = 999

        async with await get_conversation_lock(conversation_id, timeout=5.0):
            manager = await ConversationLockManager.get_instance()
            assert await manager.is_locked(conversation_id)

        # Should be released after context
        manager = await ConversationLockManager.get_instance()
        assert not await manager.is_locked(conversation_id)


class TestConversationManagerIntegration:
    """Integration tests simulating real ConversationManager usage."""

    @pytest.mark.asyncio
    async def test_simulated_process_message_v3_with_locking(self):
        """
        Simulate the actual process_message_v3 flow with locking.
        This verifies the pattern used in the real implementation.
        """
        ConversationLockManager._instance = None
        stored_messages = []
        processing_order = []

        async def simulated_process_message_v3(conversation_id: int, message: str):
            """Simulate the locked message processing."""
            async with await get_conversation_lock(conversation_id, timeout=30.0):
                # Simulate getting conversation history
                await asyncio.sleep(0.02)

                # Simulate storing user message
                msg_id = len(stored_messages) + 1
                stored_messages.append(
                    {
                        "id": msg_id,
                        "type": "user",
                        "content": message,
                        "conversation_id": conversation_id,
                    }
                )
                processing_order.append(f"user:{message}")

                # Simulate agent processing
                await asyncio.sleep(0.05)

                # Simulate storing assistant response
                response_id = len(stored_messages) + 1
                stored_messages.append(
                    {
                        "id": response_id,
                        "type": "assistant",
                        "content": f"Response to: {message}",
                        "conversation_id": conversation_id,
                    }
                )
                processing_order.append(f"assistant:{message}")

                return {"response": f"Response to: {message}"}

        # Send 3 concurrent messages to same conversation
        conversation_id = 1000
        messages = ["Query 1", "Query 2", "Query 3"]

        tasks = [simulated_process_message_v3(conversation_id, msg) for msg in messages]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 3

        # Should have 6 messages total (3 user + 3 assistant)
        assert len(stored_messages) == 6

        # Messages should be paired correctly (user followed by assistant)
        for i in range(0, len(processing_order), 2):
            user_msg = processing_order[i]
            assistant_msg = processing_order[i + 1]
            # Extract the query number
            user_query = user_msg.split(":")[1]
            assistant_query = assistant_msg.split(":")[1]
            assert user_query == assistant_query, f"Mismatched pair: {user_msg} -> {assistant_msg}"

    @pytest.mark.asyncio
    async def test_streaming_with_locking_simulation(self):
        """
        Simulate streaming response with locking.
        Verifies that lock is held for entire stream duration.
        """
        ConversationLockManager._instance = None
        lock_held_during_all_yields = True

        async def simulated_stream_with_lock(conversation_id: int):
            """Simulate streaming with lock held throughout."""
            nonlocal lock_held_during_all_yields
            manager = await ConversationLockManager.get_instance()

            async with await get_conversation_lock(conversation_id, timeout=30.0):
                for i in range(5):
                    # Check lock is still held
                    if not await manager.is_locked(conversation_id):
                        lock_held_during_all_yields = False
                    yield {"type": "token", "content": f"chunk_{i}"}
                    await asyncio.sleep(0.01)

        conversation_id = 1100
        chunks = []
        async for chunk in simulated_stream_with_lock(conversation_id):
            chunks.append(chunk)

        assert len(chunks) == 5
        assert lock_held_during_all_yields, "Lock was released during streaming"


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
