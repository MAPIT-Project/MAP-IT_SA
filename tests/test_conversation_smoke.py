"""
Conversation Stability Smoke Tests

Quick, lightweight tests that run as part of pre-commit hooks when
conversation_manager.py or memory_service.py are modified.

These tests are designed to:
1. Run quickly (< 5 seconds total)
2. Catch critical regressions in conversation stability
3. Not require external services (DB, Redis, API)

Run manually:
    pytest tests/test_conversation_smoke.py -v

This file is triggered by pre-commit when modifying:
- app/services/conversation/conversation_manager.py
- app/services/memory/memory_service.py
"""

import asyncio
import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.atomic_storage import AtomicMessageStorage
from app.core.conversation_lock import ConversationLockManager, get_conversation_lock
from app.services.agents.tool_aware_agent import ContextWindowManager, _context_manager
from app.services.memory.memory_service import FallbackRedis

# =============================================================================
# Smoke Test: Conversation Locking
# =============================================================================


class TestConversationLockingSmoke:
    """Quick smoke tests for conversation locking infrastructure."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        ConversationLockManager._instance = None
        yield
        ConversationLockManager._instance = None

    @pytest.mark.asyncio
    async def test_lock_acquisition_and_release(self):
        """Smoke test: Lock can be acquired and released."""
        manager = ConversationLockManager()
        conversation_id = 12345

        async with manager.acquire(conversation_id, holder_id="smoke_test"):
            assert await manager.is_locked(conversation_id)

        assert not await manager.is_locked(conversation_id)

    @pytest.mark.asyncio
    async def test_concurrent_locks_serialized(self):
        """Smoke test: Concurrent operations on same conversation are serialized."""
        manager = ConversationLockManager()
        conversation_id = 99999

        processing_count = 0
        max_concurrent = 0

        async def process(msg_id: int):
            nonlocal processing_count, max_concurrent
            async with manager.acquire(conversation_id, holder_id=f"msg_{msg_id}"):
                processing_count += 1
                max_concurrent = max(max_concurrent, processing_count)
                await asyncio.sleep(0.01)
                processing_count -= 1

        tasks = [process(i) for i in range(3)]
        await asyncio.gather(*tasks)

        assert max_concurrent == 1, "Concurrent processing detected - lock not working"

    @pytest.mark.asyncio
    async def test_helper_function_works(self):
        """Smoke test: get_conversation_lock helper works."""
        conversation_id = 55555

        async with await get_conversation_lock(conversation_id, timeout=5.0):
            manager = await ConversationLockManager.get_instance()
            assert await manager.is_locked(conversation_id)


# =============================================================================
# Smoke Test: Atomic Storage
# =============================================================================


class MockDBPool:
    """Minimal mock for database pool."""

    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.stored_messages = []

    def getconn(self):
        return MockConnection(self)

    def putconn(self, conn):
        pass


class MockConnection:
    """Minimal mock for database connection."""

    def __init__(self, pool):
        self.pool = pool
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return MockCursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class MockCursor:
    """Minimal mock for database cursor."""

    def __init__(self, conn):
        self.conn = conn
        self._last_result = None

    def execute(self, sql, params=None):
        if self.conn.pool.should_fail:
            raise Exception("Simulated database error")

        if "INSERT INTO message" in sql and "RETURNING id" in sql:
            msg_id = len(self.conn.pool.stored_messages) + 1000
            self._last_result = (msg_id,)
            self.conn.pool.stored_messages.append({"id": msg_id})

    def fetchone(self):
        return self._last_result


class MockMemoryService:
    """Minimal mock for memory service."""

    def __init__(self):
        self.stm = MockSTM()
        self.redis_client = None


class MockSTM:
    """Minimal mock for short-term memory."""

    def add_turn(self, conversation_id, turn):
        pass


class TestAtomicStorageSmoke:
    """Quick smoke tests for atomic storage."""

    @pytest.mark.asyncio
    async def test_successful_storage(self):
        """Smoke test: Message pair can be stored atomically."""
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        result = await storage.store_message_pair(
            conversation_id=123,
            user_id=1,
            user_message="Hello",
            assistant_message="Hi there!",
        )

        assert result.success
        assert result.user_message_id is not None
        assert result.assistant_message_id is not None
        assert len(db_pool.stored_messages) == 2

    @pytest.mark.asyncio
    async def test_failure_is_reported(self):
        """Smoke test: DB failure is properly reported."""
        db_pool = MockDBPool(should_fail=True)
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)

        result = await storage.store_message_pair(
            conversation_id=123,
            user_id=1,
            user_message="This will fail",
            assistant_message="Never stored",
        )

        assert not result.success
        assert result.error is not None


# =============================================================================
# Smoke Test: Redis Fallback
# =============================================================================


class TestRedisFallbackSmoke:
    """Quick smoke tests for Redis fallback mode."""

    def test_fallback_mode_property(self):
        """Smoke test: is_fallback_mode returns True."""
        fallback = FallbackRedis()
        assert fallback.is_fallback_mode is True

    def test_operations_log_warnings(self, caplog):
        """Smoke test: Operations log warnings."""
        fallback = FallbackRedis()

        with caplog.at_level(logging.WARNING):
            fallback.ping()
            fallback.rpush("key", "value")
            fallback.get("key")

        warning_count = sum(1 for r in caplog.records if r.levelno == logging.WARNING)
        assert warning_count >= 3

    def test_metrics_tracking(self):
        """Smoke test: Operation metrics are tracked."""
        fallback = FallbackRedis()

        fallback.rpush("key", "val1")
        fallback.rpush("key", "val2")
        fallback.get("key")

        metrics = fallback.get_fallback_metrics()
        assert metrics["total_operations"] == 3
        assert metrics["operation_counts"]["rpush"] == 2
        assert metrics["operation_counts"]["get"] == 1


# =============================================================================
# Smoke Test: Context Window
# =============================================================================


class TestContextWindowSmoke:
    """Quick smoke tests for context window management."""

    def test_reset_clears_context(self):
        """Smoke test: Reset clears context."""
        manager = ContextWindowManager()
        manager.add_to_context("Some content " * 100)
        assert manager.current_size > 0

        manager.reset()
        assert manager.current_size == 0

    def test_global_manager_exists(self):
        """Smoke test: Global context manager is initialized."""
        assert _context_manager is not None
        assert hasattr(_context_manager, "reset")
        assert callable(_context_manager.reset)

    def test_no_accumulation_pattern(self):
        """Smoke test: Context doesn't accumulate across resets."""
        manager = ContextWindowManager()

        for i in range(5):
            manager.reset()
            manager.add_to_context(f"Query {i}: " + "x" * 500)
            assert manager.current_size < 600, f"Query {i}: Context size unexpectedly large"


# =============================================================================
# Integration Smoke Test
# =============================================================================


class TestIntegrationSmoke:
    """Quick integration smoke test combining multiple components."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        ConversationLockManager._instance = None
        yield
        ConversationLockManager._instance = None

    @pytest.mark.asyncio
    async def test_lock_with_storage(self):
        """Smoke test: Lock and storage work together."""
        db_pool = MockDBPool()
        memory_service = MockMemoryService()
        storage = AtomicMessageStorage(db_pool, memory_service)
        manager = ConversationLockManager()

        conversation_id = 88888

        async with manager.acquire(conversation_id, holder_id="integration_test"):
            result = await storage.store_message_pair(
                conversation_id=conversation_id,
                user_id=1,
                user_message="Integration test",
                assistant_message="Integration response",
            )
            assert result.success
            assert await manager.is_locked(conversation_id)

        assert not await manager.is_locked(conversation_id)
        assert len(db_pool.stored_messages) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
