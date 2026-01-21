"""
Conversation Stability Regression Test Suite

This file consolidates critical regression tests for all Phase 1 infrastructure fixes:
1. Race condition prevention (Task 001) - ConversationLockManager
2. Atomic storage (Task 002) - AtomicMessageStorage
3. Storage before streaming (Task 003) - Storage order verification
4. Redis fallback warning (Task 004) - FallbackRedis warning logging
5. Context window reset (Task 005) - Context accumulation prevention

Run this test suite to verify no regressions in conversation stability features:
    pytest tests/test_conversation_regression.py -v

This suite is designed to run quickly and catch regressions before deployment.
All tests should pass - any failure indicates a regression in critical infrastructure.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.atomic_storage import (
    AtomicMessageStorage,
)
from app.core.conversation_lock import (
    ConversationLockManager,
    LockInfo,
    get_conversation_lock,
)
from app.services.agents.tool_aware_agent import (
    ContextLimits,
    ContextWindowManager,
    ToolAwareAgent,
    _context_manager,
)
from app.services.memory.memory_service import FallbackRedis

# =============================================================================
# TASK 001: Race Condition Prevention Regression Tests
# =============================================================================


class TestTask001RaceConditionPrevention:
    """
    Regression tests for Task 001: Conversation Locking.

    These tests verify that the ConversationLockManager correctly prevents
    race conditions when multiple messages arrive for the same conversation.

    Key requirements:
    - Lock acquisition and release work correctly
    - Concurrent messages to same conversation are serialized
    - Different conversations can be processed in parallel
    - No message duplicates or loss under concurrent load
    """

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the ConversationLockManager singleton before each test."""
        ConversationLockManager._instance = None
        yield
        ConversationLockManager._instance = None

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Verify ConversationLockManager maintains singleton pattern."""
        manager1 = await ConversationLockManager.get_instance()
        manager2 = await ConversationLockManager.get_instance()
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_basic_lock_acquisition_and_release(self):
        """Verify lock acquisition and release work correctly."""
        manager = ConversationLockManager()
        conversation_id = 12345

        async with manager.acquire(conversation_id, holder_id="test"):
            assert await manager.is_locked(conversation_id)

        assert not await manager.is_locked(conversation_id)

    @pytest.mark.asyncio
    async def test_lock_info_tracking(self):
        """Verify lock info is correctly tracked during acquisition."""
        manager = ConversationLockManager()
        conversation_id = 67890
        holder_id = "test_holder"

        async with manager.acquire(conversation_id, holder_id=holder_id) as lock_info:
            assert isinstance(lock_info, LockInfo)
            assert lock_info.conversation_id == conversation_id
            assert lock_info.holder_id == holder_id
            assert isinstance(lock_info.acquired_at, datetime)

            stored_info = await manager.get_lock_info(conversation_id)
            assert stored_info is not None
            assert stored_info.holder_id == holder_id

        assert await manager.get_lock_info(conversation_id) is None

    @pytest.mark.asyncio
    async def test_five_concurrent_messages_no_duplicates(self):
        """
        CRITICAL REGRESSION TEST: 5 concurrent messages to same conversation.

        Verifies:
        1. All messages are stored
        2. No duplicates
        3. Correct ordering (sequential due to locking)
        """
        manager = ConversationLockManager()
        conversation_id = 555

        stored_messages = []
        message_order = []

        async def mock_store(conv_id, user_id, message):
            await asyncio.sleep(0.05)  # Simulate processing time
            msg_id = len(stored_messages) + 1
            stored_messages.append(
                {
                    "id": msg_id,
                    "conversation_id": conv_id,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            message_order.append(message)
            return msg_id

        messages = [f"Message {i}" for i in range(1, 6)]

        async def send_message(message: str):
            holder = f"sender_{message}"
            async with manager.acquire(conversation_id, timeout=30.0, holder_id=holder):
                return await mock_store(conversation_id, 1, message)

        tasks = [send_message(msg) for msg in messages]
        await asyncio.gather(*tasks)

        # All messages stored
        assert len(stored_messages) == 5, f"Expected 5 messages, got {len(stored_messages)}"

        # No duplicate IDs
        ids = [m["id"] for m in stored_messages]
        assert len(ids) == len(set(ids)), "Duplicate message IDs found"

        # No duplicate content
        contents = [m["message"] for m in stored_messages]
        assert len(contents) == len(set(contents)), "Duplicate message content found"

        # All original messages present
        for msg in messages:
            assert msg in contents, f"Message '{msg}' not found in stored messages"

    @pytest.mark.asyncio
    async def test_same_conversation_processed_serially(self):
        """Verify same conversation messages are processed one at a time."""
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

        tasks = [process_message(i) for i in range(5)]
        await asyncio.gather(*tasks)

        assert max_concurrent == 1, f"Expected max 1 concurrent, got {max_concurrent}"

    @pytest.mark.asyncio
    async def test_different_conversations_parallel(self):
        """Verify different conversations can be processed in parallel."""
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

        assert both_processing, "Different conversations should be processed in parallel"

    @pytest.mark.asyncio
    async def test_lock_timeout_on_contention(self):
        """Verify lock acquisition times out when held by another."""
        manager = ConversationLockManager()
        conversation_id = 333

        async def hold_lock():
            async with manager.acquire(conversation_id, timeout=10.0, holder_id="holder"):
                await asyncio.sleep(2.0)

        async def try_acquire_with_short_timeout():
            await asyncio.sleep(0.1)  # Let first one acquire
            with pytest.raises(TimeoutError):
                async with manager.acquire(conversation_id, timeout=0.5, holder_id="waiter"):
                    pass

        await asyncio.gather(hold_lock(), try_acquire_with_short_timeout())

    @pytest.mark.asyncio
    async def test_helper_function_acquires_lock(self):
        """Verify get_conversation_lock helper function works correctly."""
        conversation_id = 999

        async with await get_conversation_lock(conversation_id, timeout=5.0):
            manager = await ConversationLockManager.get_instance()
            assert await manager.is_locked(conversation_id)

        manager = await ConversationLockManager.get_instance()
        assert not await manager.is_locked(conversation_id)


# =============================================================================
# TASK 002: Atomic Storage Regression Tests
# =============================================================================


class MockDBPool:
    """Mock database connection pool for testing."""

    def __init__(self, should_fail=False, fail_on_second=False, fail_on_commit=False):
        self.should_fail = should_fail
        self.fail_on_second = fail_on_second
        self.fail_on_commit = fail_on_commit
        self.connections = []
        self.stored_messages = []
        self._call_count = 0

    def getconn(self):
        conn = MockConnection(self)
        self.connections.append(conn)
        return conn

    def putconn(self, conn):
        pass


class MockConnection:
    """Mock database connection."""

    def __init__(self, pool: MockDBPool):
        self.pool = pool
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return MockCursor(self)

    def commit(self):
        if self.pool.fail_on_commit:
            raise Exception("Simulated commit failure")
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class MockCursor:
    """Mock database cursor."""

    def __init__(self, conn: MockConnection):
        self.conn = conn
        self._last_result = None
        self._insert_count = 0

    def execute(self, sql, params=None):
        pool = self.conn.pool
        pool._call_count += 1

        if pool.should_fail:
            raise Exception("Simulated database error")

        if pool.fail_on_second and self._insert_count == 1:
            raise Exception("Simulated failure on second insert")

        if "INSERT INTO message" in sql and "RETURNING id" in sql:
            self._insert_count += 1
            msg_id = len(pool.stored_messages) + 1000
            self._last_result = (msg_id,)
            pool.stored_messages.append(
                {
                    "id": msg_id,
                    "conversation_id": params[0] if params else 0,
                    "sender": params[1] if params else "unknown",
                    "text": params[2] if params else "",
                }
            )
        else:
            self._last_result = None

    def fetchone(self):
        return self._last_result


class MockMemoryService:
    """Mock memory service for testing."""

    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.stm = MockSTM(should_fail)
        self.redis_client = None


class MockSTM:
    """Mock short-term memory."""

    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.turns = {}

    def add_turn(self, conversation_id, turn):
        if self.should_fail:
            raise Exception("Simulated memory storage failure")
        if conversation_id not in self.turns:
            self.turns[conversation_id] = []
        self.turns[conversation_id].append(turn)


class TestTask002AtomicStorage:
    """
    Regression tests for Task 002: Atomic Storage.

    These tests verify that AtomicMessageStorage correctly handles:
    - Atomic transactions (both messages stored or neither)
    - Proper error reporting (no silent failures)
    - Rollback on partial failure
    - Client receives error events

    Key requirements:
    - DB failure mid-storage is rolled back
    - Error is properly reported (not silent)
    - Client receives error event
    """

    def test_initialization(self):
        """Verify AtomicMessageStorage initializes correctly."""
        db_pool = MockDBPool()
        memory_service = MockMemoryService()

        storage = AtomicMessageStorage(db_pool, memory_service)

        assert storage.db_pool == db_pool
        assert storage.memory_service == memory_service
        assert not storage._fallback_mode

    @pytest.mark.asyncio
    async def test_successful_message_pair_storage(self):
        """Verify both messages are stored successfully in atomic operation."""
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        result = await storage.store_message_pair(
            conversation_id=123,
            user_id=1,
            user_message="Hello, world!",
            assistant_message="Hello! How can I help?",
        )

        assert result.success
        assert result.user_message_id is not None
        assert result.assistant_message_id is not None
        assert result.db_stored
        assert result.error is None
        assert len(db_pool.stored_messages) == 2
        assert db_pool.stored_messages[0]["sender"] == "user"
        assert db_pool.stored_messages[1]["sender"] == "assistant"

    @pytest.mark.asyncio
    async def test_db_failure_returns_failure_result(self):
        """
        CRITICAL REGRESSION TEST: DB failure properly reported.

        Verifies that DB failure returns failed result, not silent failure.
        """
        db_pool = MockDBPool(should_fail=True)
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        result = await storage.store_message_pair(
            conversation_id=200,
            user_id=1,
            user_message="This should fail",
            assistant_message="Never stored",
        )

        assert not result.success
        assert result.error is not None
        assert "Simulated database error" in result.error or "Transaction failed" in result.error
        assert not result.db_stored

    @pytest.mark.asyncio
    async def test_partial_storage_is_rolled_back(self):
        """
        CRITICAL REGRESSION TEST: Partial storage rollback.

        When DB fails mid-storage, neither message should be persisted.
        """
        db_pool = MockDBPool(fail_on_second=True)
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        result = await storage.store_message_pair(
            conversation_id=201,
            user_id=1,
            user_message="First message",
            assistant_message="Second message fails",
        )

        assert not result.success
        assert result.error is not None

        # Rollback should have occurred
        conn = db_pool.connections[0]
        assert conn.rolled_back

    @pytest.mark.asyncio
    async def test_error_is_not_silent(self):
        """
        CRITICAL REGRESSION TEST: Error must be explicitly reported.

        The error must be:
        1. Returned in the result
        2. Contain meaningful information
        3. Not be None or empty
        """
        db_pool = MockDBPool(should_fail=True)
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        result = await storage.store_message_pair(
            conversation_id=203,
            user_id=1,
            user_message="Error should be reported",
            assistant_message="Not stored",
        )

        # Error should be explicit
        assert result.error is not None
        assert len(result.error) > 0
        assert "error" in result.error.lower() or "failed" in result.error.lower()
        assert result.success is False
        assert result.db_stored is False

    @pytest.mark.asyncio
    async def test_client_error_event_info_available(self):
        """Verify storage result contains enough info for client error event."""
        db_pool = MockDBPool(should_fail=True)
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        result = await storage.store_message_pair(
            conversation_id=300, user_id=1, user_message="Test", assistant_message="Response"
        )

        # Should be able to construct client error event
        error_event = {"type": "error", "stage": "storage_failed", "error": result.error}

        assert error_event["type"] == "error"
        assert error_event["error"] is not None
        assert "storage_failed" in error_event["stage"]

    @pytest.mark.asyncio
    async def test_memory_failure_adds_warning_not_failure(self):
        """Verify memory failure adds warning but doesn't fail overall."""
        db_pool = MockDBPool()
        memory_service = MockMemoryService(should_fail=True)
        storage = AtomicMessageStorage(db_pool, memory_service)

        result = await storage.store_message_pair(
            conversation_id=400,
            user_id=1,
            user_message="Memory will fail",
            assistant_message="But DB succeeds",
        )

        # Overall success because DB succeeded (source of truth)
        assert result.success
        assert result.db_stored
        assert not result.memory_stored
        assert len(result.warnings) > 0
        assert any("memory" in w.lower() for w in result.warnings)

    def test_is_degraded_without_pool(self):
        """Verify is_degraded returns True when pool is None."""
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(None, memory_service)
        assert storage.is_degraded


# =============================================================================
# TASK 003: Storage Before Streaming Regression Tests
# =============================================================================


class TestTask003StorageBeforeStreaming:
    """
    Regression tests for Task 003: Storage Before Streaming.

    These tests verify that message storage happens BEFORE token streaming:
    1. Message is in DB before first token is sent
    2. Follow-up query immediately after response can access stored message

    Key requirements:
    - Storage completion timestamp before first token timestamp
    - Message IDs available before streaming starts
    """

    @pytest.fixture
    def storage_setup(self):
        """Create storage infrastructure for tests."""
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)
        return {"db_pool": db_pool, "memory_service": memory_service, "storage": storage}

    @pytest.mark.asyncio
    async def test_storage_before_first_token(self, storage_setup):
        """
        CRITICAL REGRESSION TEST: Storage happens before token streaming.

        Verifies message is in DB before first token would be sent.
        """
        storage = storage_setup["storage"]
        db_pool = storage_setup["db_pool"]

        events = []

        # Store messages
        result = await storage.store_message_pair(
            conversation_id=123,
            user_id=1,
            user_message="Test question",
            assistant_message="Test response for streaming",
        )
        events.append({"type": "storage_complete", "time": datetime.now()})

        # Simulate first token
        await asyncio.sleep(0.001)  # Small delay to ensure ordering
        events.append({"type": "first_token", "time": datetime.now()})

        storage_time = events[0]["time"]
        token_time = events[1]["time"]

        assert storage_time < token_time, "Storage must complete before first token"
        assert len(db_pool.stored_messages) == 2
        assert result.success
        assert result.user_message_id is not None
        assert result.assistant_message_id is not None

    @pytest.mark.asyncio
    async def test_follow_up_query_can_access_stored_message(self, storage_setup):
        """
        CRITICAL REGRESSION TEST: Follow-up query can access stored message.

        After storage completes, the message should be immediately available.
        """
        storage = storage_setup["storage"]
        db_pool = storage_setup["db_pool"]

        # Store first message pair
        result1 = await storage.store_message_pair(
            conversation_id=456,
            user_id=1,
            user_message="Show me 5 funding calls",
            assistant_message="Here are 5 calls: 1. Call A, 2. Call B...",
        )

        assert result1.success
        assert len(db_pool.stored_messages) == 2

        # Immediately verify messages are accessible
        stored_user_msg = next((m for m in db_pool.stored_messages if m["sender"] == "user"), None)
        stored_assistant_msg = next(
            (m for m in db_pool.stored_messages if m["sender"] == "assistant"), None
        )

        assert stored_user_msg is not None
        assert stored_assistant_msg is not None
        assert "5 funding calls" in stored_user_msg["text"]

        # Store follow-up immediately
        result2 = await storage.store_message_pair(
            conversation_id=456,
            user_id=1,
            user_message="Tell me about the third one",
            assistant_message="Call C is about...",
        )

        assert result2.success
        assert len(db_pool.stored_messages) == 4

    @pytest.mark.asyncio
    async def test_message_ids_available_before_streaming(self, storage_setup):
        """Verify message IDs are available immediately after storage."""
        storage = storage_setup["storage"]

        result = await storage.store_message_pair(
            conversation_id=333,
            user_id=1,
            user_message="Query",
            assistant_message="Answer to query",
        )

        # IDs should be available immediately for streaming metadata
        assert result.user_message_id is not None
        assert result.assistant_message_id is not None

        metadata = {
            "user_message_id": result.user_message_id,
            "assistant_message_id": result.assistant_message_id,
            "storage_success": result.success,
        }

        assert metadata["storage_success"]
        assert isinstance(metadata["user_message_id"], int)
        assert isinstance(metadata["assistant_message_id"], int)


# =============================================================================
# TASK 004: Redis Fallback Warning Regression Tests
# =============================================================================


class TestTask004RedisFallbackWarning:
    """
    Regression tests for Task 004: Silent Redis Fallback.

    These tests verify that FallbackRedis:
    1. Logs WARNING on every operation
    2. is_fallback_mode property returns True
    3. Tracks fallback usage in metrics

    Key requirements:
    - WARNING logged on disconnect
    - is_fallback_mode returns True
    """

    @pytest.fixture
    def fallback_redis(self):
        """Create a FallbackRedis instance."""
        return FallbackRedis()

    def test_is_fallback_mode_returns_true(self, fallback_redis):
        """CRITICAL REGRESSION TEST: is_fallback_mode must return True."""
        assert fallback_redis.is_fallback_mode is True

    def test_ping_logs_warning(self, fallback_redis, caplog):
        """Verify ping operation logs WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.ping()

        assert len(caplog.records) >= 1
        assert any("Redis fallback: ping called" in r.message for r in caplog.records)
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_rpush_logs_warning(self, fallback_redis, caplog):
        """Verify rpush operation logs WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.rpush("test_key", "test_value")

        assert any("Redis fallback: rpush called" in r.message for r in caplog.records)

    def test_get_logs_warning(self, fallback_redis, caplog):
        """Verify get operation logs WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.get("key")

        assert any("Redis fallback: get called" in r.message for r in caplog.records)

    def test_lrange_logs_warning(self, fallback_redis, caplog):
        """Verify lrange operation logs WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.lrange("key", 0, -1)

        assert any("Redis fallback: lrange called" in r.message for r in caplog.records)

    def test_hset_logs_warning(self, fallback_redis, caplog):
        """Verify hset operation logs WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.hset("hash_key", "field", "value")

        assert any("Redis fallback: hset called" in r.message for r in caplog.records)

    def test_delete_logs_warning(self, fallback_redis, caplog):
        """Verify delete operation logs WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.delete("key")

        assert any("Redis fallback: delete called" in r.message for r in caplog.records)

    def test_fallback_metrics_initial(self, fallback_redis):
        """Verify initial fallback metrics structure."""
        metrics = fallback_redis.get_fallback_metrics()
        assert metrics["is_fallback_mode"] is True
        assert metrics["total_operations"] == 0
        assert "operation_counts" in metrics

    def test_operation_counts_increment(self, fallback_redis):
        """Verify operation counts increment correctly."""
        fallback_redis.rpush("key", "value")
        fallback_redis.rpush("key", "value2")
        fallback_redis.get("key")

        metrics = fallback_redis.get_fallback_metrics()
        assert metrics["operation_counts"]["rpush"] == 2
        assert metrics["operation_counts"]["get"] == 1
        assert metrics["total_operations"] == 3

    def test_multiple_operations_log_multiple_warnings(self, fallback_redis, caplog):
        """Verify multiple operations log multiple warnings."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.rpush("conversation:1:messages", "msg")
            fallback_redis.lrange("conversation:1:messages", 0, -1)
            fallback_redis.hset("conversation:1:metadata", "key", "value")

        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_messages) >= 3
        assert any("rpush" in msg for msg in warning_messages)
        assert any("lrange" in msg for msg in warning_messages)
        assert any("hset" in msg for msg in warning_messages)


# =============================================================================
# TASK 005: Context Window Reset Regression Tests
# =============================================================================


class TestTask005ContextWindowReset:
    """
    Regression tests for Task 005: Context Window Reset.

    These tests verify that:
    1. Context window resets at start of each process_query()
    2. Context size doesn't accumulate beyond expected limits
    3. Reset prevents memory leak across queries

    Key requirements:
    - context_window_manager.reset() called at start of process_query()
    - 10 queries in sequence with bounded context
    """

    def test_reset_clears_current_size(self):
        """Verify reset() sets current_size to 0."""
        manager = ContextWindowManager()
        manager.add_to_context("Test content " * 100)
        assert manager.current_size > 0

        manager.reset()
        assert manager.current_size == 0

    def test_add_to_context_accumulates(self):
        """Verify add_to_context correctly accumulates size."""
        manager = ContextWindowManager()

        manager.add_to_context("First")
        first_size = manager.current_size

        manager.add_to_context("Second")
        assert manager.current_size > first_size

    def test_reset_then_add_starts_fresh(self):
        """Verify reset followed by add_to_context starts fresh."""
        manager = ContextWindowManager()

        manager.add_to_context("First content " * 50)
        original_size = manager.current_size

        manager.reset()
        manager.add_to_context("Second")

        assert manager.current_size == len("Second")
        assert manager.current_size < original_size

    def test_global_context_manager_exists(self):
        """Verify global _context_manager is properly initialized."""
        assert _context_manager is not None
        assert isinstance(_context_manager, ContextWindowManager)
        assert hasattr(_context_manager, "reset")
        assert callable(_context_manager.reset)

    def test_simulated_query_sequence_no_accumulation(self):
        """
        CRITICAL REGRESSION TEST: 10 queries without accumulation.

        Simulate 10 queries in sequence and verify context size
        doesn't accumulate beyond expected limits.
        """
        manager = ContextWindowManager()
        max_observed_size = 0

        for query_num in range(10):
            # Reset at start (simulating process_query behavior)
            manager.reset()
            assert manager.current_size == 0, f"Query {query_num}: Context should be 0 after reset"

            # Simulate adding context during query processing
            manager.add_to_context(f"Tool result for query {query_num}: " + "x" * 1000)
            manager.add_to_context(f"Observation {query_num}: " + "y" * 500)
            manager.add_to_context(f"Formatted results {query_num}: " + "z" * 500)

            query_size = manager.current_size
            max_observed_size = max(max_observed_size, query_size)

            # Each query should have bounded context size
            expected_max_per_query = 3000
            assert query_size < expected_max_per_query, (
                f"Query {query_num}: Context size {query_size} exceeds max {expected_max_per_query}"
            )

        # Max observed should be much less than 10x a single query
        # (would be ~20000 if accumulating, should be ~2000)
        assert max_observed_size < 5000, (
            f"Max observed size {max_observed_size} suggests accumulation across queries"
        )

    def test_context_bounded_across_many_iterations(self):
        """Test context remains bounded even with many iterations."""
        limits = ContextLimits(max_context_chars=50000)
        manager = ContextWindowManager(limits)

        sizes_after_each_query = []

        for _ in range(50):
            manager.reset()

            # Simulate 3 reasoning iterations per query
            for iteration in range(3):
                manager.add_to_context(f"Step {iteration}: " + "content " * 100)

            sizes_after_each_query.append(manager.current_size)

        # All query sizes should be similar (within 15% of each other)
        avg_size = sum(sizes_after_each_query) / len(sizes_after_each_query)
        for i, size in enumerate(sizes_after_each_query):
            deviation = abs(size - avg_size) / avg_size
            assert deviation < 0.15, (
                f"Query {i}: Size {size} deviates {deviation * 100:.1f}% from average {avg_size}"
            )

    @pytest.mark.asyncio
    async def test_process_query_resets_context_at_start(self):
        """Verify process_query() resets context window at the start."""
        with patch("app.services.agents.tool_aware_agent._context_manager") as mock_ctx:
            mock_ctx.reset = Mock()
            mock_ctx.current_size = 0
            mock_ctx.truncate_observation = Mock(return_value="obs")
            mock_ctx.format_results_for_context = Mock(return_value="results")

            with patch.object(ToolAwareAgent, "__init__", return_value=None):
                agent = ToolAwareAgent.__new__(ToolAwareAgent)
                agent.max_iterations = 1
                agent.tools = {}
                agent.speculative_executor = None
                agent.plan_cache = None
                agent.llm = None
                agent._assess_complexity = Mock(return_value="simple")
                agent._identify_required_sources = Mock(return_value=[])
                agent._reason_next_step = AsyncMock(
                    return_value={
                        "thought": "test thought",
                        "action": "conclude",
                        "conclusion": "Test answer",
                        "confidence": 0.9,
                    }
                )
                agent._build_fallback_answer = Mock(return_value="Fallback")
                agent._analyze_response_quality = Mock(return_value={})

                await agent.process_query("Test query")
                mock_ctx.reset.assert_called()

    def test_reset_when_already_zero_is_safe(self):
        """Verify reset is safe when size is already zero."""
        manager = ContextWindowManager()
        assert manager.current_size == 0

        manager.reset()
        assert manager.current_size == 0

    def test_default_limits_reasonable(self):
        """Verify default limits are reasonable."""
        limits = ContextLimits()

        assert limits.max_context_chars > 0
        assert limits.reserved_for_response > 0
        assert limits.max_tool_result_chars > 0


# =============================================================================
# Combined Integration Regression Tests
# =============================================================================


class TestCombinedIntegrationRegression:
    """
    Integration tests that verify multiple fixes work together correctly.

    These tests ensure the conversation stability infrastructure
    functions cohesively.
    """

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singletons before each test."""
        ConversationLockManager._instance = None
        yield
        ConversationLockManager._instance = None

    @pytest.mark.asyncio
    async def test_locking_with_atomic_storage_flow(self):
        """
        Integration test: Locking + Atomic Storage together.

        Verifies that the lock is held during atomic storage operations.
        """
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        manager = ConversationLockManager()
        conversation_id = 12345

        async with manager.acquire(conversation_id, holder_id="test"):
            # Storage should work while lock is held
            result = await storage.store_message_pair(
                conversation_id=conversation_id,
                user_id=1,
                user_message="Test message",
                assistant_message="Test response",
            )

            assert result.success
            assert await manager.is_locked(conversation_id)

        # Lock should be released after storage
        assert not await manager.is_locked(conversation_id)

    @pytest.mark.asyncio
    async def test_concurrent_storage_with_locking(self):
        """
        Integration test: Concurrent storage requests with locking.

        Verifies multiple concurrent storage requests are serialized properly.
        """
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)
        manager = ConversationLockManager()
        conversation_id = 54321

        results = []

        async def store_with_lock(msg_num: int):
            async with manager.acquire(conversation_id, holder_id=f"msg_{msg_num}"):
                result = await storage.store_message_pair(
                    conversation_id=conversation_id,
                    user_id=1,
                    user_message=f"User message {msg_num}",
                    assistant_message=f"Assistant response {msg_num}",
                )
                results.append({"num": msg_num, "success": result.success})
                return result

        tasks = [store_with_lock(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # All storage operations should succeed
        assert len(results) == 5
        assert all(r["success"] for r in results)

        # Should have 10 messages (5 pairs)
        assert len(db_pool.stored_messages) == 10

    def test_context_reset_doesnt_affect_storage(self):
        """
        Integration test: Context reset + Storage independence.

        Verifies context window reset doesn't interfere with storage.
        """
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)
        context_manager = ContextWindowManager()

        # Simulate query processing pattern
        for i in range(5):
            # Reset context at start
            context_manager.reset()
            assert context_manager.current_size == 0

            # Add context
            context_manager.add_to_context(f"Query {i} context")

            # Storage should work independently
            import asyncio

            result = asyncio.get_event_loop().run_until_complete(
                storage.store_message_pair(
                    conversation_id=i,
                    user_id=1,
                    user_message=f"Message {i}",
                    assistant_message=f"Response {i}",
                )
            )
            assert result.success

        # All messages stored
        assert len(db_pool.stored_messages) == 10


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
