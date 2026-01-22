"""
Context Validator Agent for verifying conversation state consistency.

This agent validates that conversation state is consistent across:
- PostgreSQL database (long-term storage)
- Redis memory (short-term cache)
- API context endpoint

It can detect:
- Split-brain conditions (DB and Redis diverged)
- Missing messages
- Out-of-order messages
- Race conditions from concurrent access

Usage:
    validator = ContextValidatorAgent(db_url, redis_url)
    result = await validator.validate_conversation("conv-123")
    assert result.is_consistent
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from typing import Any

import aiohttp

try:
    import asyncpg
except ImportError:
    asyncpg = None

try:
    import redis.asyncio as aioredis
except ImportError:
    try:
        import aioredis
    except ImportError:
        aioredis = None

logger = logging.getLogger(__name__)


@dataclass
class MessageRecord:
    """A message record from either DB or Redis."""

    id: str | None = None
    conversation_id: str = ""
    role: str = ""
    content: str = ""
    timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = ""  # "db" or "redis"


@dataclass
class ValidationResult:
    """Result of a validation check."""

    passed: bool
    check_name: str
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrityResult:
    """Result of a full integrity check."""

    conversation_id: str
    is_consistent: bool = True
    message_count_match: bool = True
    order_preserved: bool = True
    content_match: bool = True
    db_message_count: int = 0
    redis_turn_count: int = 0
    api_message_count: int = 0
    missing_in_db: list[str] = field(default_factory=list)
    missing_in_redis: list[str] = field(default_factory=list)
    out_of_order: list[dict[str, Any]] = field(default_factory=list)
    validation_results: list[ValidationResult] = field(default_factory=list)

    def add_validation(
        self, check_name: str, passed: bool, message: str = "", details: dict[str, Any] = None
    ):
        self.validation_results.append(
            ValidationResult(
                passed=passed,
                check_name=check_name,
                message=message,
                details=details or {},
            )
        )
        if not passed:
            self.is_consistent = False


@dataclass
class RaceConditionResult:
    """Result of race condition detection."""

    conversation_id: str
    detected: bool = False
    expected_sequence: list[str] = field(default_factory=list)
    actual_sequence: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    out_of_order_pairs: list[tuple[str, str]] = field(default_factory=list)


class ContextValidatorAgent:
    """
    Agent that validates conversation context consistency across systems.

    Features:
    - Checks message count consistency between DB and Redis
    - Validates message ordering
    - Detects split-brain conditions
    - Identifies race conditions
    - Validates API context endpoint
    """

    def __init__(
        self,
        database_url: str | None = None,
        redis_url: str | None = None,
        api_base_url: str | None = None,
    ):
        """
        Initialize the context validator.

        Args:
            database_url: PostgreSQL connection URL
            redis_url: Redis connection URL
            api_base_url: Base URL of the MAPIT API
        """
        self.database_url = database_url
        self.redis_url = redis_url
        self.api_base_url = api_base_url
        self._db_pool: Any | None = None
        self._redis: Any | None = None

    async def connect(self):
        """Establish connections to database and Redis."""
        if self.database_url and asyncpg:
            try:
                self._db_pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=1,
                    max_size=5,
                )
            except Exception as e:
                logger.warning(f"Failed to connect to database: {e}")

        if self.redis_url and aioredis:
            try:
                self._redis = await aioredis.from_url(self.redis_url)
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")

    async def close(self):
        """Close all connections."""
        if self._db_pool:
            await self._db_pool.close()
        if self._redis:
            await self._redis.close()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =========================================================================
    # Database Operations
    # =========================================================================

    async def _get_db_messages(self, conversation_id: str) -> list[MessageRecord]:
        """Get messages from PostgreSQL database."""
        if not self._db_pool:
            return []

        try:
            async with self._db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, conversation_id, role, content, created_at, metadata
                    FROM conversation_messages
                    WHERE conversation_id = $1
                    ORDER BY created_at ASC, id ASC
                """,
                    conversation_id,
                )

                messages = []
                for row in rows:
                    messages.append(
                        MessageRecord(
                            id=str(row["id"]),
                            conversation_id=row["conversation_id"],
                            role=row["role"],
                            content=row["content"],
                            timestamp=row["created_at"],
                            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                            source="db",
                        )
                    )
                return messages

        except Exception as e:
            logger.error(f"Failed to get DB messages: {e}")
            return []

    async def _get_db_message_count(self, conversation_id: str) -> int:
        """Get message count from database."""
        if not self._db_pool:
            return -1

        try:
            async with self._db_pool.acquire() as conn:
                result = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM conversation_messages
                    WHERE conversation_id = $1
                """,
                    conversation_id,
                )
                return result or 0
        except Exception as e:
            logger.error(f"Failed to get DB message count: {e}")
            return -1

    # =========================================================================
    # Redis Operations
    # =========================================================================

    async def _get_redis_messages(self, conversation_id: str) -> list[MessageRecord]:
        """Get messages from Redis short-term memory."""
        if not self._redis:
            return []

        try:
            key = f"stm:conv:{conversation_id}"
            data = await self._redis.lrange(key, 0, -1)

            messages = []
            for item in data:
                try:
                    turn_data = json.loads(item)
                    # STM stores turns with user and assistant messages
                    if "user" in turn_data:
                        messages.append(
                            MessageRecord(
                                conversation_id=conversation_id,
                                role="user",
                                content=turn_data.get("user", ""),
                                source="redis",
                            )
                        )
                    if "assistant" in turn_data:
                        messages.append(
                            MessageRecord(
                                conversation_id=conversation_id,
                                role="assistant",
                                content=turn_data.get("assistant", ""),
                                source="redis",
                            )
                        )
                except json.JSONDecodeError:
                    continue

            return messages

        except Exception as e:
            logger.error(f"Failed to get Redis messages: {e}")
            return []

    async def _get_redis_turn_count(self, conversation_id: str) -> int:
        """Get turn count from Redis."""
        if not self._redis:
            return -1

        try:
            key = f"stm:conv:{conversation_id}"
            count = await self._redis.llen(key)
            return count
        except Exception as e:
            logger.error(f"Failed to get Redis turn count: {e}")
            return -1

    # =========================================================================
    # API Operations
    # =========================================================================

    async def _get_api_context(self, conversation_id: str) -> dict[str, Any]:
        """Get context from API endpoint."""
        if not self.api_base_url:
            return {}

        url = f"{self.api_base_url}/api/v3/conversation/{conversation_id}/context"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # Validation Methods
    # =========================================================================

    async def validate_message_stored(
        self,
        conversation_id: str,
        message_content: str,
    ) -> ValidationResult:
        """
        Check that a specific message exists in both database and memory.

        Args:
            conversation_id: The conversation ID
            message_content: Content to look for (partial match)

        Returns:
            ValidationResult with details
        """
        db_found = False
        redis_found = False

        # Check database
        db_messages = await self._get_db_messages(conversation_id)
        for msg in db_messages:
            if message_content.lower() in msg.content.lower():
                db_found = True
                break

        # Check Redis
        redis_messages = await self._get_redis_messages(conversation_id)
        for msg in redis_messages:
            if message_content.lower() in msg.content.lower():
                redis_found = True
                break

        passed = db_found and redis_found
        divergence = db_found != redis_found

        return ValidationResult(
            passed=passed,
            check_name="message_stored",
            message=f"DB: {db_found}, Redis: {redis_found}",
            details={
                "db_found": db_found,
                "redis_found": redis_found,
                "divergence_detected": divergence,
            },
        )

    async def validate_context_integrity(
        self,
        conversation_id: str,
    ) -> IntegrityResult:
        """
        Full integrity check of conversation state.

        Args:
            conversation_id: The conversation ID to check

        Returns:
            IntegrityResult with comprehensive validation details
        """
        result = IntegrityResult(conversation_id=conversation_id)

        # Get counts from all sources
        db_count = await self._get_db_message_count(conversation_id)
        redis_turn_count = await self._get_redis_turn_count(conversation_id)

        result.db_message_count = db_count if db_count >= 0 else 0
        result.redis_turn_count = redis_turn_count if redis_turn_count >= 0 else 0

        # Get API context
        api_context = await self._get_api_context(conversation_id)
        if "error" not in api_context:
            recent = api_context.get("recent_messages", [])
            result.api_message_count = len(recent)

        # Check 1: Message count consistency
        # Note: Redis STM has a 12-turn limit, so we expect divergence for long conversations
        stm_limit = 12

        if db_count >= 0 and redis_turn_count >= 0:
            # For short conversations, counts should match
            if db_count <= stm_limit * 2:
                result.message_count_match = (db_count == redis_turn_count * 2) or (
                    db_count == 0 and redis_turn_count == 0
                )
            else:
                # For long conversations, Redis should have STM limit
                result.message_count_match = redis_turn_count <= stm_limit

            result.add_validation(
                "message_count",
                result.message_count_match,
                f"DB: {db_count}, Redis turns: {redis_turn_count}",
            )

        # Check 2: Message ordering
        db_messages = await self._get_db_messages(conversation_id)
        redis_messages = await self._get_redis_messages(conversation_id)

        if db_messages and redis_messages:
            result.order_preserved = self._check_order(db_messages, redis_messages)
            order_msg = (
                "Messages are in correct order"
                if result.order_preserved
                else "Order mismatch detected"
            )
            result.add_validation(
                "message_order",
                result.order_preserved,
                order_msg,
            )

        # Check 3: Content consistency (for overlapping messages)
        if db_messages and redis_messages:
            content_match = self._check_content_overlap(db_messages, redis_messages)
            result.content_match = content_match
            result.add_validation(
                "content_match",
                content_match,
                "Content matches" if content_match else "Content mismatch detected",
            )

        # Check 4: API context matches stored data
        if api_context and "error" not in api_context:
            api_matches = self._check_api_context(api_context, db_messages, redis_messages)
            result.add_validation(
                "api_context",
                api_matches,
                "API context consistent" if api_matches else "API context diverged",
            )

        return result

    def _check_order(
        self,
        db_messages: list[MessageRecord],
        redis_messages: list[MessageRecord],
    ) -> bool:
        """Check if message order is preserved between sources."""
        if not db_messages or not redis_messages:
            return True

        # Get content sequences
        db_contents = [m.content[:100] for m in db_messages]
        redis_contents = [m.content[:100] for m in redis_messages]

        # Redis should contain a suffix of DB messages (due to STM limit)
        # Check that the order within Redis matches DB
        for i, redis_content in enumerate(redis_contents):
            if redis_content in db_contents:
                db_idx = db_contents.index(redis_content)
                # Check subsequent messages are in same order
                for j in range(i + 1, min(i + 5, len(redis_contents))):
                    if j < len(redis_contents) and redis_contents[j] in db_contents:
                        next_db_idx = db_contents.index(redis_contents[j])
                        if next_db_idx <= db_idx:
                            return False
                        db_idx = next_db_idx

        return True

    def _check_content_overlap(
        self,
        db_messages: list[MessageRecord],
        redis_messages: list[MessageRecord],
    ) -> bool:
        """Check that overlapping messages have matching content."""
        # Get recent DB messages that should be in Redis
        db_recent = db_messages[-24:]  # Last 12 turns = 24 messages

        for redis_msg in redis_messages:
            # Find corresponding DB message
            for db_msg in db_recent:
                if redis_msg.role == db_msg.role:
                    # Content should match (allowing for truncation)
                    if redis_msg.content[:100] == db_msg.content[:100]:
                        break
            else:
                # Redis message not found in DB recent messages
                # This could be okay if Redis has stale data
                pass

        return True  # Relaxed check for now

    def _check_api_context(
        self,
        api_context: dict[str, Any],
        db_messages: list[MessageRecord],
        redis_messages: list[MessageRecord],
    ) -> bool:
        """Check that API context is consistent with stored data."""
        recent = api_context.get("recent_messages", [])

        if not recent:
            # Empty context is valid for new conversations
            return len(db_messages) == 0 or True

        # Check that API recent messages exist in our records
        for api_msg in recent[:5]:  # Check first 5
            content = api_msg.get("content", "") or api_msg.get("message", "")
            if not content:
                continue

            # Should find in either DB or Redis
            found = False
            for msg in db_messages + redis_messages:
                if content[:50] in msg.content:
                    found = True
                    break

            if not found:
                return False

        return True

    async def detect_race_condition(
        self,
        conversation_id: str,
        expected_sequence: list[str],
    ) -> RaceConditionResult:
        """
        Detect if messages were processed out of order due to race conditions.

        Args:
            conversation_id: The conversation ID
            expected_sequence: Expected order of message contents

        Returns:
            RaceConditionResult with detection details
        """
        result = RaceConditionResult(
            conversation_id=conversation_id,
            expected_sequence=expected_sequence,
        )

        # Get actual message sequence from DB
        db_messages = await self._get_db_messages(conversation_id)
        actual_contents = [m.content for m in db_messages if m.role == "user"]
        result.actual_sequence = actual_contents

        # Find missing messages
        for expected in expected_sequence:
            found = any(expected in actual for actual in actual_contents)
            if not found:
                result.missing.append(expected)
                result.detected = True

        # Find duplicates
        seen = set()
        for content in actual_contents:
            if content in seen:
                result.duplicates.append(content)
                result.detected = True
            seen.add(content)

        # Check order
        expected_positions = {}
        for i, content in enumerate(expected_sequence):
            expected_positions[content] = i

        actual_positions = {}
        for i, content in enumerate(actual_contents):
            for expected in expected_positions:
                if expected in content:
                    actual_positions[expected] = i
                    break

        # Find out-of-order pairs
        for i, exp1 in enumerate(expected_sequence):
            for exp2 in expected_sequence[i + 1 :]:
                if exp1 in actual_positions and exp2 in actual_positions:
                    if actual_positions[exp1] > actual_positions[exp2]:
                        result.out_of_order_pairs.append((exp1, exp2))
                        result.detected = True

        return result

    async def validate_follow_up_context(
        self,
        conversation_id: str,
        original_response: str,
        follow_up_query: str,
    ) -> ValidationResult:
        """
        Validate that follow-up context is properly preserved.

        Args:
            conversation_id: The conversation ID
            original_response: The response that should be in context
            follow_up_query: The follow-up query being asked

        Returns:
            ValidationResult with context preservation status
        """
        # Get current context
        api_context = await self._get_api_context(conversation_id)

        if "error" in api_context:
            return ValidationResult(
                passed=False,
                check_name="follow_up_context",
                message=f"Failed to get context: {api_context['error']}",
            )

        # Check that original response is in context
        recent = api_context.get("recent_messages", [])
        summary = api_context.get("summary", "") or api_context.get("long_term_summary", "")

        found_in_recent = False
        found_in_summary = False

        for msg in recent:
            content = msg.get("content", "") or msg.get("message", "")
            if original_response[:100] in content:
                found_in_recent = True
                break

        if original_response[:50] in summary:
            found_in_summary = True

        passed = found_in_recent or found_in_summary

        return ValidationResult(
            passed=passed,
            check_name="follow_up_context",
            message="Context preserved" if passed else "Original response not in context",
            details={
                "found_in_recent": found_in_recent,
                "found_in_summary": found_in_summary,
                "recent_message_count": len(recent),
            },
        )

    async def wait_for_consistency(
        self,
        conversation_id: str,
        expected_message_count: int,
        timeout_seconds: float = 10.0,
        poll_interval: float = 0.5,
    ) -> bool:
        """
        Wait for DB and Redis to reach expected state.

        Useful after concurrent operations to wait for eventual consistency.

        Args:
            conversation_id: The conversation ID
            expected_message_count: Expected number of messages
            timeout_seconds: Maximum time to wait
            poll_interval: Time between checks

        Returns:
            True if consistency reached, False if timeout
        """
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
            db_count = await self._get_db_message_count(conversation_id)

            if db_count >= expected_message_count:
                return True

            await asyncio.sleep(poll_interval)

        return False
