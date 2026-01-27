"""
Collaboration Service.

Provides real-time collaboration features for proposal writing:
- Collaborator presence tracking
- Section locking for conflict prevention
- Cursor position tracking
- Operation broadcasting for live updates
- Operational Transformation (OT) for concurrent editing

Features:
- Redis-backed for distributed state
- WebSocket-ready event broadcasting
- Automatic lock expiry
- Conflict resolution via OT
"""

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class OperationType(str, Enum):
    """Types of editing operations."""
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"
    RETAIN = "retain"


@dataclass
class CursorPosition:
    """Cursor position in a document."""
    section_id: str
    position: int  # Character offset
    selection_start: int | None = None
    selection_end: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "position": self.position,
            "selection_start": self.selection_start,
            "selection_end": self.selection_end,
        }


@dataclass
class CollaboratorSession:
    """A collaborator's session in a proposal."""
    user_id: str
    session_id: str  # Proposal session ID
    connection_id: str  # Unique connection ID for this instance
    username: str
    color: str  # Color for cursor/highlights
    cursor: CursorPosition | None = None
    active_section: str | None = None
    joined_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_connected: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "connection_id": self.connection_id,
            "username": self.username,
            "color": self.color,
            "cursor": self.cursor.to_dict() if self.cursor else None,
            "active_section": self.active_section,
            "joined_at": self.joined_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_connected": self.is_connected,
        }


@dataclass
class SectionLock:
    """A lock on a proposal section."""
    section_id: str
    session_id: str  # Proposal session ID
    locked_by: str  # User ID
    locked_by_name: str
    locked_at: datetime
    expires_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "session_id": self.session_id,
            "locked_by": self.locked_by,
            "locked_by_name": self.locked_by_name,
            "locked_at": self.locked_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_expired": datetime.now(UTC) > self.expires_at,
        }


@dataclass
class EditOperation:
    """An editing operation for OT."""
    operation_id: str
    section_id: str
    operation_type: OperationType
    position: int
    content: str | None = None  # For insert/replace
    length: int | None = None   # For delete/retain
    user_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    base_version: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "section_id": self.section_id,
            "operation_type": self.operation_type.value,
            "position": self.position,
            "content": self.content,
            "length": self.length,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "base_version": self.base_version,
        }


@dataclass
class BroadcastEvent:
    """An event to broadcast to collaborators."""
    event_type: str
    session_id: str
    payload: dict[str, Any]
    exclude_user: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "session_id": self.session_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }


# Color palette for collaborators
COLLABORATOR_COLORS = [
    "#3B82F6",  # Blue
    "#10B981",  # Green
    "#F59E0B",  # Amber
    "#EF4444",  # Red
    "#8B5CF6",  # Purple
    "#EC4899",  # Pink
    "#14B8A6",  # Teal
    "#F97316",  # Orange
]


class CollaborationService:
    """Service for real-time proposal collaboration."""

    # Lock expiry time in seconds
    LOCK_EXPIRY_SECONDS = 300  # 5 minutes

    # Session heartbeat interval
    HEARTBEAT_INTERVAL_SECONDS = 30

    # Inactivity timeout
    INACTIVITY_TIMEOUT_SECONDS = 600  # 10 minutes

    def __init__(self, redis_client=None, db_pool=None):
        """
        Initialize the collaboration service.

        Args:
            redis_client: Redis client for distributed state
            db_pool: PostgreSQL connection pool for persistence
        """
        self.redis = redis_client
        self.db_pool = db_pool

        # In-memory fallback if Redis not available
        self._local_sessions: dict[str, dict[str, CollaboratorSession]] = {}
        self._local_locks: dict[str, dict[str, SectionLock]] = {}
        self._local_versions: dict[str, dict[str, int]] = {}

        # Event listeners for broadcasting
        self._listeners: dict[str, list[Callable]] = {}

    # =========================================================================
    # Session Management
    # =========================================================================

    async def join_session(
        self,
        session_id: str,
        user_id: str,
        username: str,
    ) -> dict[str, Any]:
        """
        Join a collaboration session.

        Args:
            session_id: Proposal session ID
            user_id: User ID
            username: Display name

        Returns:
            Session info with collaborators and locked sections
        """
        connection_id = str(uuid4())

        # Get existing collaborators to determine color
        existing = await self.get_collaborators(session_id)
        used_colors = {c.color for c in existing}
        available_colors = [c for c in COLLABORATOR_COLORS if c not in used_colors]
        color = available_colors[0] if available_colors else COLLABORATOR_COLORS[len(existing) % len(COLLABORATOR_COLORS)]

        collaborator = CollaboratorSession(
            user_id=user_id,
            session_id=session_id,
            connection_id=connection_id,
            username=username,
            color=color,
        )

        await self._register_collaborator(collaborator)

        # Broadcast join event
        await self._broadcast(
            BroadcastEvent(
                event_type="collaborator_joined",
                session_id=session_id,
                payload={"collaborator": collaborator.to_dict()},
                exclude_user=user_id,
            )
        )

        # Get current state
        collaborators = await self.get_collaborators(session_id)
        locked_sections = await self.get_locked_sections(session_id)

        return {
            "connection_id": connection_id,
            "collaborators": [c.to_dict() for c in collaborators],
            "locked_sections": [l.to_dict() for l in locked_sections],
            "your_color": color,
        }

    async def leave_session(
        self,
        session_id: str,
        user_id: str,
        connection_id: str | None = None,
    ) -> bool:
        """
        Leave a collaboration session.

        Args:
            session_id: Proposal session ID
            user_id: User ID
            connection_id: Specific connection to leave (optional)

        Returns:
            True if successfully left
        """
        # Release any locks held by this user
        await self._release_user_locks(session_id, user_id)

        # Remove from collaborators
        await self._unregister_collaborator(session_id, user_id, connection_id)

        # Broadcast leave event
        await self._broadcast(
            BroadcastEvent(
                event_type="collaborator_left",
                session_id=session_id,
                payload={"user_id": user_id, "connection_id": connection_id},
            )
        )

        return True

    async def get_collaborators(self, session_id: str) -> list[CollaboratorSession]:
        """Get all active collaborators in a session."""
        if self.redis:
            try:
                key = f"collab:session:{session_id}:collaborators"
                data = self.redis.hgetall(key)

                collaborators = []
                for user_data in data.values():
                    user_dict = json.loads(user_data)
                    collaborators.append(self._dict_to_collaborator(user_dict))

                return collaborators
            except Exception as e:
                logger.warning(f"Redis error getting collaborators: {e}")

        # Fallback to local storage
        return list(self._local_sessions.get(session_id, {}).values())

    async def update_heartbeat(self, session_id: str, user_id: str):
        """Update user's heartbeat to keep session alive."""
        if self.redis:
            try:
                key = f"collab:session:{session_id}:collaborators"
                data = self.redis.hget(key, user_id)
                if data:
                    user_dict = json.loads(data)
                    user_dict["last_activity"] = datetime.now(UTC).isoformat()
                    self.redis.hset(key, user_id, json.dumps(user_dict))
            except Exception as e:
                logger.warning(f"Redis error updating heartbeat: {e}")
        else:
            session = self._local_sessions.get(session_id, {}).get(user_id)
            if session:
                session.last_activity = datetime.now(UTC)

    # =========================================================================
    # Cursor Tracking
    # =========================================================================

    async def update_cursor(
        self,
        session_id: str,
        user_id: str,
        cursor: CursorPosition,
    ) -> bool:
        """
        Update user's cursor position.

        Args:
            session_id: Proposal session ID
            user_id: User ID
            cursor: New cursor position

        Returns:
            True if successfully updated
        """
        # Update stored cursor
        if self.redis:
            try:
                key = f"collab:session:{session_id}:collaborators"
                data = self.redis.hget(key, user_id)
                if data:
                    user_dict = json.loads(data)
                    user_dict["cursor"] = cursor.to_dict()
                    user_dict["active_section"] = cursor.section_id
                    user_dict["last_activity"] = datetime.now(UTC).isoformat()
                    self.redis.hset(key, user_id, json.dumps(user_dict))
            except Exception as e:
                logger.warning(f"Redis error updating cursor: {e}")
        else:
            session = self._local_sessions.get(session_id, {}).get(user_id)
            if session:
                session.cursor = cursor
                session.active_section = cursor.section_id
                session.last_activity = datetime.now(UTC)

        # Broadcast cursor update
        await self._broadcast(
            BroadcastEvent(
                event_type="cursor_update",
                session_id=session_id,
                payload={
                    "user_id": user_id,
                    "cursor": cursor.to_dict(),
                },
                exclude_user=user_id,
            )
        )

        return True

    # =========================================================================
    # Section Locking
    # =========================================================================

    async def lock_section(
        self,
        session_id: str,
        section_id: str,
        user_id: str,
        username: str,
    ) -> SectionLock | None:
        """
        Lock a section for editing.

        Args:
            session_id: Proposal session ID
            section_id: Section to lock
            user_id: User requesting lock
            username: User's display name

        Returns:
            SectionLock if acquired, None if already locked
        """
        lock_key = f"collab:lock:{session_id}:{section_id}"
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self.LOCK_EXPIRY_SECONDS)

        lock = SectionLock(
            section_id=section_id,
            session_id=session_id,
            locked_by=user_id,
            locked_by_name=username,
            locked_at=now,
            expires_at=expires_at,
        )

        if self.redis:
            try:
                # Try to acquire lock atomically
                acquired = self.redis.set(
                    lock_key,
                    json.dumps(lock.to_dict()),
                    nx=True,  # Only if not exists
                    ex=self.LOCK_EXPIRY_SECONDS,
                )

                if not acquired:
                    # Check if current lock is expired or held by same user
                    existing = self.redis.get(lock_key)
                    if existing:
                        existing_lock = json.loads(existing)
                        if existing_lock["locked_by"] == user_id:
                            # Refresh own lock
                            self.redis.setex(
                                lock_key,
                                self.LOCK_EXPIRY_SECONDS,
                                json.dumps(lock.to_dict()),
                            )
                            acquired = True
                        elif datetime.fromisoformat(existing_lock["expires_at"]) < now:
                            # Expired, take over
                            self.redis.setex(
                                lock_key,
                                self.LOCK_EXPIRY_SECONDS,
                                json.dumps(lock.to_dict()),
                            )
                            acquired = True

                if not acquired:
                    return None

            except Exception as e:
                logger.warning(f"Redis error acquiring lock: {e}")
                return None
        else:
            # Local fallback
            session_locks = self._local_locks.setdefault(session_id, {})
            existing = session_locks.get(section_id)

            if existing and existing.locked_by != user_id and existing.expires_at > now:
                return None

            session_locks[section_id] = lock

        # Broadcast lock event
        await self._broadcast(
            BroadcastEvent(
                event_type="section_locked",
                session_id=session_id,
                payload={"lock": lock.to_dict()},
            )
        )

        return lock

    async def unlock_section(
        self,
        session_id: str,
        section_id: str,
        user_id: str,
    ) -> bool:
        """
        Release a section lock.

        Args:
            session_id: Proposal session ID
            section_id: Section to unlock
            user_id: User releasing lock

        Returns:
            True if released, False if not locked by user
        """
        lock_key = f"collab:lock:{session_id}:{section_id}"

        if self.redis:
            try:
                existing = self.redis.get(lock_key)
                if existing:
                    lock_data = json.loads(existing)
                    if lock_data["locked_by"] != user_id:
                        return False
                    self.redis.delete(lock_key)
            except Exception as e:
                logger.warning(f"Redis error releasing lock: {e}")
                return False
        else:
            session_locks = self._local_locks.get(session_id, {})
            existing = session_locks.get(section_id)
            if existing and existing.locked_by != user_id:
                return False
            if section_id in session_locks:
                del session_locks[section_id]

        # Broadcast unlock event
        await self._broadcast(
            BroadcastEvent(
                event_type="section_unlocked",
                session_id=session_id,
                payload={"section_id": section_id, "user_id": user_id},
            )
        )

        return True

    async def refresh_lock(
        self,
        session_id: str,
        section_id: str,
        user_id: str,
    ) -> bool:
        """Refresh an existing lock to prevent expiry."""
        lock_key = f"collab:lock:{session_id}:{section_id}"

        if self.redis:
            try:
                existing = self.redis.get(lock_key)
                if existing:
                    lock_data = json.loads(existing)
                    if lock_data["locked_by"] == user_id:
                        lock_data["expires_at"] = (
                            datetime.now(UTC) + timedelta(seconds=self.LOCK_EXPIRY_SECONDS)
                        ).isoformat()
                        self.redis.setex(
                            lock_key,
                            self.LOCK_EXPIRY_SECONDS,
                            json.dumps(lock_data),
                        )
                        return True
            except Exception as e:
                logger.warning(f"Redis error refreshing lock: {e}")

        return False

    async def get_locked_sections(self, session_id: str) -> list[SectionLock]:
        """Get all locked sections in a session."""
        locks = []

        if self.redis:
            try:
                pattern = f"collab:lock:{session_id}:*"
                for key in self.redis.scan_iter(pattern):
                    data = self.redis.get(key)
                    if data:
                        lock_dict = json.loads(data)
                        lock = SectionLock(
                            section_id=lock_dict["section_id"],
                            session_id=lock_dict["session_id"],
                            locked_by=lock_dict["locked_by"],
                            locked_by_name=lock_dict["locked_by_name"],
                            locked_at=datetime.fromisoformat(lock_dict["locked_at"]),
                            expires_at=datetime.fromisoformat(lock_dict["expires_at"]),
                        )
                        # Only include non-expired locks
                        if lock.expires_at > datetime.now(UTC):
                            locks.append(lock)
            except Exception as e:
                logger.warning(f"Redis error getting locks: {e}")
        else:
            session_locks = self._local_locks.get(session_id, {})
            now = datetime.now(UTC)
            locks = [l for l in session_locks.values() if l.expires_at > now]

        return locks

    async def _release_user_locks(self, session_id: str, user_id: str):
        """Release all locks held by a user."""
        locks = await self.get_locked_sections(session_id)
        for lock in locks:
            if lock.locked_by == user_id:
                await self.unlock_section(session_id, lock.section_id, user_id)

    # =========================================================================
    # Editing Operations
    # =========================================================================

    async def apply_operation(
        self,
        session_id: str,
        section_id: str,
        user_id: str,
        operation: EditOperation,
    ) -> dict[str, Any]:
        """
        Apply an editing operation with OT.

        Args:
            session_id: Proposal session ID
            section_id: Section being edited
            user_id: User making the edit
            operation: The editing operation

        Returns:
            Result with new content and version
        """
        version_key = f"collab:version:{session_id}:{section_id}"
        content_key = f"collab:content:{session_id}:{section_id}"

        if self.redis:
            try:
                # Get current version
                current_version = int(self.redis.get(version_key) or 0)

                # Transform operation if needed
                if operation.base_version < current_version:
                    pending_ops = await self._get_pending_operations(
                        session_id, section_id, operation.base_version
                    )
                    operation = self._transform_operation(operation, pending_ops)

                # Get current content
                current_content = self.redis.get(content_key) or ""
                if isinstance(current_content, bytes):
                    current_content = current_content.decode()

                # Apply operation
                new_content = self._apply_operation_to_content(current_content, operation)

                # Save new state
                new_version = current_version + 1
                self.redis.set(content_key, new_content)
                self.redis.set(version_key, new_version)

                # Store operation for OT
                await self._store_operation(session_id, section_id, operation, new_version)

            except Exception as e:
                logger.error(f"Redis error applying operation: {e}")
                return {"success": False, "error": str(e)}
        else:
            # Local fallback
            versions = self._local_versions.setdefault(session_id, {})
            current_version = versions.get(section_id, 0)
            new_version = current_version + 1
            versions[section_id] = new_version
            new_content = ""  # Would need content storage for full local support

        # Broadcast operation
        await self._broadcast(
            BroadcastEvent(
                event_type="operation_applied",
                session_id=session_id,
                payload={
                    "section_id": section_id,
                    "operation": operation.to_dict(),
                    "version": new_version,
                    "user_id": user_id,
                },
                exclude_user=user_id,
            )
        )

        return {
            "success": True,
            "version": new_version,
            "content": new_content if self.redis else None,
        }

    def _transform_operation(
        self,
        operation: EditOperation,
        pending_ops: list[EditOperation],
    ) -> EditOperation:
        """
        Transform operation against pending operations (OT).

        This is a simplified OT implementation. For production,
        consider using a library like ot.py or ShareJS.
        """
        transformed = operation

        for pending in pending_ops:
            if pending.position <= transformed.position:
                # Pending operation is before our operation
                if pending.operation_type == OperationType.INSERT:
                    # Shift our position by insert length
                    transformed.position += len(pending.content or "")
                elif pending.operation_type == OperationType.DELETE:
                    # Shift our position by delete length (negative)
                    transformed.position -= (pending.length or 0)
                    transformed.position = max(0, transformed.position)

        return transformed

    def _apply_operation_to_content(
        self,
        content: str,
        operation: EditOperation,
    ) -> str:
        """Apply an operation to content string."""
        pos = operation.position

        if operation.operation_type == OperationType.INSERT:
            return content[:pos] + (operation.content or "") + content[pos:]

        elif operation.operation_type == OperationType.DELETE:
            end = pos + (operation.length or 0)
            return content[:pos] + content[end:]

        elif operation.operation_type == OperationType.REPLACE:
            end = pos + (operation.length or 0)
            return content[:pos] + (operation.content or "") + content[end:]

        return content

    async def _get_pending_operations(
        self,
        session_id: str,
        section_id: str,
        since_version: int,
    ) -> list[EditOperation]:
        """Get operations since a version for OT."""
        if not self.redis:
            return []

        try:
            key = f"collab:ops:{session_id}:{section_id}"
            ops = []

            for i in range(since_version + 1, int(self.redis.get(f"collab:version:{session_id}:{section_id}") or 0) + 1):
                data = self.redis.hget(key, str(i))
                if data:
                    op_dict = json.loads(data)
                    ops.append(EditOperation(
                        operation_id=op_dict["operation_id"],
                        section_id=op_dict["section_id"],
                        operation_type=OperationType(op_dict["operation_type"]),
                        position=op_dict["position"],
                        content=op_dict.get("content"),
                        length=op_dict.get("length"),
                        user_id=op_dict.get("user_id"),
                        base_version=op_dict["base_version"],
                    ))

            return ops
        except Exception as e:
            logger.warning(f"Error getting pending operations: {e}")
            return []

    async def _store_operation(
        self,
        session_id: str,
        section_id: str,
        operation: EditOperation,
        version: int,
    ):
        """Store operation for OT history."""
        if not self.redis:
            return

        try:
            key = f"collab:ops:{session_id}:{section_id}"
            self.redis.hset(key, str(version), json.dumps(operation.to_dict()))
            # Keep only last 100 operations
            self.redis.expire(key, 3600)
        except Exception as e:
            logger.warning(f"Error storing operation: {e}")

    # =========================================================================
    # Broadcasting
    # =========================================================================

    def add_listener(self, session_id: str, callback: Callable):
        """Add a listener for session events (for WebSocket broadcasting)."""
        if session_id not in self._listeners:
            self._listeners[session_id] = []
        self._listeners[session_id].append(callback)

    def remove_listener(self, session_id: str, callback: Callable):
        """Remove a listener."""
        if session_id in self._listeners:
            self._listeners[session_id] = [
                l for l in self._listeners[session_id] if l != callback
            ]

    async def _broadcast(self, event: BroadcastEvent):
        """Broadcast an event to all listeners."""
        listeners = self._listeners.get(event.session_id, [])

        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception as e:
                logger.error(f"Error in broadcast listener: {e}")

        # Also publish to Redis for distributed broadcasting
        if self.redis:
            try:
                channel = f"collab:events:{event.session_id}"
                self.redis.publish(channel, json.dumps(event.to_dict()))
            except Exception as e:
                logger.warning(f"Redis publish error: {e}")

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    async def _register_collaborator(self, collaborator: CollaboratorSession):
        """Register a collaborator in the session."""
        if self.redis:
            try:
                key = f"collab:session:{collaborator.session_id}:collaborators"
                self.redis.hset(
                    key,
                    collaborator.user_id,
                    json.dumps(collaborator.to_dict()),
                )
                self.redis.expire(key, 86400)  # 24 hour TTL
            except Exception as e:
                logger.warning(f"Redis error registering collaborator: {e}")

        # Also store locally
        session = self._local_sessions.setdefault(collaborator.session_id, {})
        session[collaborator.user_id] = collaborator

    async def _unregister_collaborator(
        self,
        session_id: str,
        user_id: str,
        connection_id: str | None = None,
    ):
        """Remove a collaborator from the session."""
        if self.redis:
            try:
                key = f"collab:session:{session_id}:collaborators"
                self.redis.hdel(key, user_id)
            except Exception as e:
                logger.warning(f"Redis error unregistering collaborator: {e}")

        # Also remove locally
        session = self._local_sessions.get(session_id, {})
        if user_id in session:
            del session[user_id]

    def _dict_to_collaborator(self, data: dict[str, Any]) -> CollaboratorSession:
        """Convert dict to CollaboratorSession."""
        cursor = None
        if data.get("cursor"):
            cursor = CursorPosition(
                section_id=data["cursor"]["section_id"],
                position=data["cursor"]["position"],
                selection_start=data["cursor"].get("selection_start"),
                selection_end=data["cursor"].get("selection_end"),
            )

        return CollaboratorSession(
            user_id=data["user_id"],
            session_id=data["session_id"],
            connection_id=data["connection_id"],
            username=data["username"],
            color=data["color"],
            cursor=cursor,
            active_section=data.get("active_section"),
            joined_at=datetime.fromisoformat(data["joined_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            is_connected=data.get("is_connected", True),
        )

    async def cleanup_inactive_sessions(self):
        """Cleanup inactive collaborator sessions."""
        timeout = datetime.now(UTC) - timedelta(seconds=self.INACTIVITY_TIMEOUT_SECONDS)

        for session_id, collaborators in list(self._local_sessions.items()):
            for user_id, session in list(collaborators.items()):
                if session.last_activity < timeout:
                    await self.leave_session(session_id, user_id)


# Singleton instance
_collaboration_service: CollaborationService | None = None


def get_collaboration_service(
    redis_client=None,
    db_pool=None,
) -> CollaborationService:
    """Get or create the CollaborationService singleton."""
    global _collaboration_service

    if _collaboration_service is None:
        _collaboration_service = CollaborationService(
            redis_client=redis_client,
            db_pool=db_pool,
        )

    return _collaboration_service
