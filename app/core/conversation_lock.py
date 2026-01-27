"""
Conversation-level locking to prevent race conditions.

This module provides locking mechanisms to ensure that:
1. Only one request processes a conversation at a time
2. Messages are stored in order
3. No race conditions occur with concurrent requests

Usage:
    async with ConversationLockManager.get_lock(conversation_id):
        # Process message safely
        pass
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LockInfo:
    """Information about an active lock."""

    conversation_id: int
    acquired_at: datetime
    holder_id: str
    request_count: int = 0


class ConversationLockManager:
    """
    Manages conversation-level locks to prevent race conditions.

    Features:
    - Per-conversation async locks
    - Automatic cleanup of stale locks
    - Lock timeout support
    - Request counting for debugging

    Thread Safety:
    - Uses asyncio.Lock for async-safe operations
    - Safe for concurrent use in async context
    """

    # Singleton instance
    _instance: Optional["ConversationLockManager"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        """Initialize the lock manager."""
        self._locks: dict[int, asyncio.Lock] = {}
        self._lock_info: dict[int, LockInfo] = {}
        self._manager_lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> "ConversationLockManager":
        """Get the singleton instance."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def _get_or_create_lock(self, conversation_id: int) -> asyncio.Lock:
        """Get or create a lock for a conversation."""
        async with self._manager_lock:
            if conversation_id not in self._locks:
                self._locks[conversation_id] = asyncio.Lock()
                logger.debug(f"Created new lock for conversation {conversation_id}")
            return self._locks[conversation_id]

    @asynccontextmanager
    async def acquire(
        self, conversation_id: int, timeout: float = 60.0, holder_id: str = "unknown"
    ):
        """
        Acquire a lock for a conversation with timeout.

        Args:
            conversation_id: The conversation ID to lock
            timeout: Maximum time to wait for lock (seconds)
            holder_id: Identifier for the lock holder (for debugging)

        Yields:
            LockInfo about the acquired lock

        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        lock = await self._get_or_create_lock(conversation_id)
        start_time = time.time()

        try:
            # Try to acquire with timeout
            acquired = await asyncio.wait_for(lock.acquire(), timeout=timeout)

            if not acquired:
                raise TimeoutError(f"Failed to acquire lock for conversation {conversation_id}")

            # Record lock info
            wait_time = time.time() - start_time
            lock_info = LockInfo(
                conversation_id=conversation_id,
                acquired_at=datetime.now(),
                holder_id=holder_id,
            )
            self._lock_info[conversation_id] = lock_info

            if wait_time > 1.0:
                logger.warning(
                    f"Lock for conversation {conversation_id} acquired after {wait_time:.2f}s wait"
                )
            else:
                logger.debug(f"Lock acquired for conversation {conversation_id} by {holder_id}")

            yield lock_info

        except TimeoutError as err:
            logger.error(
                f"Timeout waiting for lock on conversation {conversation_id} "
                f"(waited {timeout}s, holder: {self._lock_info.get(conversation_id)})"
            )
            raise TimeoutError(
                f"Could not acquire lock for conversation {conversation_id} within {timeout}s"
            ) from err

        finally:
            # Always release the lock
            if lock.locked():
                lock.release()
                logger.debug(f"Lock released for conversation {conversation_id}")

            # Clean up lock info
            if conversation_id in self._lock_info:
                del self._lock_info[conversation_id]

    async def is_locked(self, conversation_id: int) -> bool:
        """Check if a conversation is currently locked."""
        lock = self._locks.get(conversation_id)
        return lock is not None and lock.locked()

    async def get_lock_info(self, conversation_id: int) -> LockInfo | None:
        """Get information about a lock."""
        return self._lock_info.get(conversation_id)

    async def cleanup_stale_locks(self, max_age_seconds: float = 300.0):
        """
        Clean up locks that have been held too long.

        This should be called periodically to prevent deadlocks.

        Args:
            max_age_seconds: Maximum age for a lock before it's considered stale
        """
        now = datetime.now()
        stale_conversations = []

        for conv_id, info in self._lock_info.items():
            age = (now - info.acquired_at).total_seconds()
            if age > max_age_seconds:
                stale_conversations.append(conv_id)
                logger.warning(
                    f"Stale lock detected for conversation {conv_id} "
                    f"(held for {age:.1f}s by {info.holder_id})"
                )

        # Force release stale locks
        for conv_id in stale_conversations:
            lock = self._locks.get(conv_id)
            if lock and lock.locked():
                try:
                    lock.release()
                    logger.warning(f"Force-released stale lock for conversation {conv_id}")
                except RuntimeError:
                    pass  # Lock was already released

            if conv_id in self._lock_info:
                del self._lock_info[conv_id]

    def get_stats(self) -> dict:
        """Get statistics about lock usage."""
        return {
            "total_locks_created": len(self._locks),
            "currently_locked": sum(1 for lk in self._locks.values() if lk.locked()),
            "active_lock_info": {
                str(k): {
                    "holder": v.holder_id,
                    "acquired_at": v.acquired_at.isoformat(),
                    "age_seconds": (datetime.now() - v.acquired_at).total_seconds(),
                }
                for k, v in self._lock_info.items()
            },
        }


# Convenience function for getting locks
async def get_conversation_lock(conversation_id: int, timeout: float = 60.0):
    """
    Get a lock for a conversation.

    Usage:
        async with get_conversation_lock(conversation_id):
            # Process message safely
            pass
    """
    manager = await ConversationLockManager.get_instance()
    return manager.acquire(conversation_id, timeout=timeout)
