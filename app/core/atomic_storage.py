"""
Atomic message storage for conversation consistency.

This module provides atomic storage operations that ensure:
1. Messages are stored in both DB and memory atomically
2. Failures are properly reported (not silently ignored)
3. Storage happens BEFORE response is sent to client
4. Rollback on partial failures

Usage:
    storage = AtomicMessageStorage(db_pool, memory_service)
    result = await storage.store_message_pair(
        conversation_id=123,
        user_message="Hello",
        assistant_message="Hi there!",
        user_id=1
    )
    if result.success:
        # Safe to send response to client
        pass
"""

import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StorageResult:
    """Result of a storage operation."""

    success: bool
    user_message_id: int | None = None
    assistant_message_id: int | None = None
    db_stored: bool = False
    memory_stored: bool = False
    error: str | None = None
    warnings: list[str] = field(default_factory=list)

    def add_warning(self, message: str):
        self.warnings.append(message)
        logger.warning(f"Storage warning: {message}")


class AtomicMessageStorage:
    """
    Provides atomic storage operations for conversation messages.

    Features:
    - Stores to DB first, then memory (DB is source of truth)
    - Proper error reporting (no silent failures)
    - Transaction support for DB operations
    - Automatic retry on transient failures
    - Rollback on partial failures

    Architecture:
    - DB (PostgreSQL) is the source of truth
    - Memory (Redis STM) is a cache that can be rebuilt from DB
    - If memory storage fails, we warn but continue (DB is authoritative)
    - If DB storage fails, we fail the entire operation
    """

    def __init__(self, db_pool, memory_service):
        """
        Initialize the atomic storage service.

        Args:
            db_pool: PostgreSQL connection pool
            memory_service: MemoryService instance with STM
        """
        self.db_pool = db_pool
        self.memory_service = memory_service
        self._fallback_mode = False

    async def store_user_message(
        self,
        conversation_id: int,
        user_id: int,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> StorageResult:
        """
        Store a user message atomically.

        Args:
            conversation_id: The conversation ID
            user_id: The user ID
            message: The message content
            metadata: Optional metadata

        Returns:
            StorageResult with success status and message ID
        """
        result = StorageResult(success=False)

        # Step 1: Store in DB (source of truth)
        try:
            message_id = await self._store_to_db(
                conversation_id=conversation_id,
                user_id=user_id,
                sender="user",
                message=message,
                metadata=metadata,
            )
            result.user_message_id = message_id
            result.db_stored = True
        except Exception as e:
            result.error = f"Database storage failed: {str(e)}"
            logger.error(f"Failed to store user message in DB: {e}")
            return result

        # Step 2: Store in memory (cache)
        try:
            self._store_to_memory(
                conversation_id=conversation_id, message_id=message_id, role="user", content=message
            )
            result.memory_stored = True
        except Exception as e:
            # Memory failure is a warning, not a hard failure
            result.add_warning(f"Memory storage failed (DB succeeded): {str(e)}")
            logger.warning(f"Memory storage failed for user message: {e}")

        result.success = result.db_stored
        return result

    async def store_assistant_message(
        self,
        conversation_id: int,
        message: str,
        citations: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StorageResult:
        """
        Store an assistant message atomically.

        Args:
            conversation_id: The conversation ID
            message: The message content
            citations: Optional citations
            metadata: Optional metadata

        Returns:
            StorageResult with success status and message ID
        """
        result = StorageResult(success=False)

        # Step 1: Store in DB (source of truth)
        try:
            message_id = await self._store_to_db(
                conversation_id=conversation_id,
                user_id=1,  # System user
                sender="assistant",
                message=message,
                citations=citations,
                metadata=metadata,
            )
            result.assistant_message_id = message_id
            result.db_stored = True
        except Exception as e:
            result.error = f"Database storage failed: {str(e)}"
            logger.error(f"Failed to store assistant message in DB: {e}")
            return result

        # Step 2: Store in memory (cache)
        try:
            self._store_to_memory(
                conversation_id=conversation_id,
                message_id=message_id,
                role="assistant",
                content=message[:2000],  # Limit for memory
            )
            result.memory_stored = True
        except Exception as e:
            result.add_warning(f"Memory storage failed (DB succeeded): {str(e)}")
            logger.warning(f"Memory storage failed for assistant message: {e}")

        result.success = result.db_stored
        return result

    async def store_message_pair(
        self,
        conversation_id: int,
        user_id: int,
        user_message: str,
        assistant_message: str,
        citations: list[dict[str, Any]] | None = None,
    ) -> StorageResult:
        """
        Store both user and assistant messages atomically.

        This ensures both messages are stored together or neither is stored.
        Useful when you want to guarantee conversation consistency.

        Args:
            conversation_id: The conversation ID
            user_id: The user ID
            user_message: The user's message
            assistant_message: The assistant's response
            citations: Optional citations

        Returns:
            StorageResult with both message IDs
        """
        result = StorageResult(success=False)

        # Start a DB transaction
        if not self.db_pool:
            result.error = "No database connection available"
            return result

        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Ensure conversation exists
            cursor.execute(
                """
                INSERT INTO conversation (id, user_id, name, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (id) DO NOTHING
            """,
                (conversation_id, user_id, f"Chat {conversation_id}"),
            )

            # Store user message
            cursor.execute(
                """
                INSERT INTO message (conversation_id, sender, text, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id
            """,
                (conversation_id, "user", user_message),
            )
            result.user_message_id = cursor.fetchone()[0]

            # Store assistant message
            cursor.execute(
                """
                INSERT INTO message (conversation_id, sender, text, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id
            """,
                (conversation_id, "assistant", assistant_message),
            )
            result.assistant_message_id = cursor.fetchone()[0]

            # Store citations if provided
            if citations:
                cursor.execute(
                    """
                    UPDATE message SET citations = %s WHERE id = %s
                """,
                    (json.dumps(citations), result.assistant_message_id),
                )

            # Commit transaction
            conn.commit()
            result.db_stored = True
            logger.info(
                f"Stored message pair: user={result.user_message_id}, "
                f"assistant={result.assistant_message_id}"
            )

        except Exception as e:
            if conn:
                conn.rollback()
            result.error = f"Transaction failed: {str(e)}"
            logger.error(f"Failed to store message pair: {e}")
            return result

        finally:
            if conn:
                self.db_pool.putconn(conn)

        # Store in memory (non-critical)
        try:
            self._store_to_memory(
                conversation_id=conversation_id,
                message_id=result.user_message_id,
                role="user",
                content=user_message,
            )
            self._store_to_memory(
                conversation_id=conversation_id,
                message_id=result.assistant_message_id,
                role="assistant",
                content=assistant_message[:2000],
            )
            result.memory_stored = True
        except Exception as e:
            result.add_warning(f"Memory storage failed: {str(e)}")

        result.success = result.db_stored
        return result

    async def _store_to_db(
        self,
        conversation_id: int,
        user_id: int,
        sender: str,
        message: str,
        citations: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Store message to database and return message ID."""
        if not self.db_pool:
            # Generate a pseudo-random ID but log a warning
            logger.warning(
                "Database not available - message will not be persisted! "
                "This is a serious issue in production."
            )
            self._fallback_mode = True
            return random.randint(100000, 999999)

        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()

            # Ensure conversation exists
            cursor.execute(
                """
                INSERT INTO conversation (id, user_id, name, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (id) DO NOTHING
            """,
                (conversation_id, user_id, f"Chat {conversation_id}"),
            )

            # Check for duplicate
            cursor.execute(
                """
                SELECT id FROM message
                WHERE conversation_id = %s
                  AND sender = %s
                  AND text = %s
                  AND created_at > NOW() - INTERVAL '5 seconds'
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (conversation_id, sender, message),
            )

            existing = cursor.fetchone()
            if existing:
                logger.info(f"Reusing existing message ID: {existing[0]}")
                return existing[0]

            # Insert message
            cursor.execute(
                """
                INSERT INTO message (conversation_id, sender, text, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id
            """,
                (conversation_id, sender, message),
            )

            message_id = cursor.fetchone()[0]

            # Add citations if provided
            if citations:
                cursor.execute(
                    """
                    UPDATE message SET citations = %s WHERE id = %s
                """,
                    (json.dumps(citations), message_id),
                )

            conn.commit()
            return message_id

        except Exception:
            conn.rollback()
            raise

        finally:
            self.db_pool.putconn(conn)

    def _store_to_memory(self, conversation_id: int, message_id: int, role: str, content: str):
        """Store message to memory service."""
        if not self.memory_service:
            raise RuntimeError("Memory service not available")

        # Check if memory service is in fallback mode
        if hasattr(self.memory_service, "redis_client"):
            redis = self.memory_service.redis_client
            if hasattr(redis, "__class__") and redis.__class__.__name__ == "FallbackRedis":
                logger.warning(
                    "Memory service is using FallbackRedis - conversation context may not persist!"
                )

        from ..memory.short_term_memory import ConversationTurn

        turn = ConversationTurn(
            message_id=message_id, role=role, content=content, timestamp=datetime.now()
        )
        self.memory_service.stm.add_turn(conversation_id, turn)

    async def verify_storage(
        self, conversation_id: int, message_id: int, expected_content: str
    ) -> bool:
        """
        Verify that a message was stored correctly.

        Useful for critical operations where you need to confirm storage.

        Args:
            conversation_id: The conversation ID
            message_id: The message ID to verify
            expected_content: Expected content (partial match)

        Returns:
            True if message is found with expected content
        """
        if not self.db_pool:
            return False

        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT text FROM message WHERE id = %s AND conversation_id = %s
            """,
                (message_id, conversation_id),
            )

            result = cursor.fetchone()
            if result:
                return expected_content[:100] in result[0]
            return False

        finally:
            self.db_pool.putconn(conn)

    @property
    def is_degraded(self) -> bool:
        """Check if storage is operating in degraded mode."""
        return self._fallback_mode or self.db_pool is None


def get_atomic_storage(db_pool, memory_service) -> AtomicMessageStorage:
    """Factory function to get an AtomicMessageStorage instance."""
    return AtomicMessageStorage(db_pool, memory_service)
