"""
Collaboration API Routes.

Provides endpoints for:
- Real-time proposal collaboration via WebSocket
- HTTP endpoints for collaboration management
- Section locking
- Cursor synchronization
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from app.services.collaboration.collaboration_service import (
    BroadcastEvent,
    CursorPosition,
    EditOperation,
    OperationType,
    get_collaboration_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])


# =============================================================================
# Request/Response Models
# =============================================================================


class JoinSessionRequest(BaseModel):
    """Request to join a collaboration session."""
    username: str = Field(..., min_length=1, max_length=100)


class JoinSessionResponse(BaseModel):
    """Response after joining a session."""
    connection_id: str
    your_color: str
    collaborators: list[dict[str, Any]]
    locked_sections: list[dict[str, Any]]


class CursorUpdateRequest(BaseModel):
    """Request to update cursor position."""
    section_id: str
    position: int = Field(..., ge=0)
    selection_start: int | None = None
    selection_end: int | None = None


class LockSectionRequest(BaseModel):
    """Request to lock a section."""
    username: str


class LockResponse(BaseModel):
    """Response for lock operations."""
    success: bool
    lock: dict[str, Any] | None = None
    message: str | None = None


class EditOperationRequest(BaseModel):
    """Request to apply an edit operation."""
    operation_type: str = Field(..., pattern="^(insert|delete|replace|retain)$")
    position: int = Field(..., ge=0)
    content: str | None = None
    length: int | None = None
    base_version: int = Field(0, ge=0)


class EditOperationResponse(BaseModel):
    """Response after applying an edit."""
    success: bool
    version: int
    error: str | None = None


class CollaboratorResponse(BaseModel):
    """Collaborator information."""
    user_id: str
    username: str
    color: str
    active_section: str | None
    cursor: dict[str, Any] | None
    is_connected: bool


# =============================================================================
# WebSocket Connection Manager
# =============================================================================


class ConnectionManager:
    """Manages WebSocket connections for collaboration."""

    def __init__(self):
        # session_id -> {user_id -> websocket}
        self.active_connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
    ):
        """Accept and register a WebSocket connection."""
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = {}

        self.active_connections[session_id][user_id] = websocket

        logger.info(f"WebSocket connected: session={session_id}, user={user_id}")

    def disconnect(self, session_id: str, user_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            if user_id in self.active_connections[session_id]:
                del self.active_connections[session_id][user_id]

            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

        logger.info(f"WebSocket disconnected: session={session_id}, user={user_id}")

    async def broadcast(
        self,
        session_id: str,
        message: dict[str, Any],
        exclude_user: str | None = None,
    ):
        """Broadcast a message to all users in a session."""
        if session_id not in self.active_connections:
            return

        disconnected = []

        for user_id, websocket in self.active_connections[session_id].items():
            if user_id == exclude_user:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                disconnected.append(user_id)

        # Cleanup disconnected users
        for user_id in disconnected:
            self.disconnect(session_id, user_id)

    async def send_to_user(
        self,
        session_id: str,
        user_id: str,
        message: dict[str, Any],
    ):
        """Send a message to a specific user."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id].get(user_id)
            if websocket:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to user {user_id}: {e}")
                    self.disconnect(session_id, user_id)


# Global connection manager
manager = ConnectionManager()


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@router.websocket("/{session_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: str = Query(...),
    username: str = Query(...),
):
    """
    WebSocket endpoint for real-time collaboration.

    Events sent from server:
    - collaborator_joined: New user joined
    - collaborator_left: User left
    - cursor_update: User cursor moved
    - section_locked: Section was locked
    - section_unlocked: Section was unlocked
    - operation_applied: Edit operation applied

    Events from client:
    - join: Join session
    - leave: Leave session
    - cursor: Update cursor position
    - lock: Lock a section
    - unlock: Unlock a section
    - operation: Apply edit operation
    - heartbeat: Keep connection alive
    """
    service = get_collaboration_service()

    await manager.connect(websocket, session_id, user_id)

    # Register event broadcaster
    async def broadcast_handler(event: BroadcastEvent):
        await manager.broadcast(
            session_id,
            event.to_dict(),
            exclude_user=event.exclude_user,
        )

    service.add_listener(session_id, broadcast_handler)

    try:
        # Send initial state after connection
        result = await service.join_session(session_id, user_id, username)
        await websocket.send_json({
            "event_type": "connected",
            "payload": result,
        })

        while True:
            try:
                # Receive message with timeout for heartbeat checking
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=60.0,
                )
            except TimeoutError:
                # Send ping to check connection
                await websocket.send_json({"event_type": "ping"})
                continue

            event_type = data.get("type") or data.get("event_type")
            payload = data.get("payload", {})

            if event_type == "cursor":
                # Update cursor position
                cursor = CursorPosition(
                    section_id=payload["section_id"],
                    position=payload["position"],
                    selection_start=payload.get("selection_start"),
                    selection_end=payload.get("selection_end"),
                )
                await service.update_cursor(session_id, user_id, cursor)

            elif event_type == "lock":
                # Lock a section
                lock = await service.lock_section(
                    session_id,
                    payload["section_id"],
                    user_id,
                    username,
                )
                await websocket.send_json({
                    "event_type": "lock_result",
                    "payload": {
                        "success": lock is not None,
                        "lock": lock.to_dict() if lock else None,
                    },
                })

            elif event_type == "unlock":
                # Unlock a section
                success = await service.unlock_section(
                    session_id,
                    payload["section_id"],
                    user_id,
                )
                await websocket.send_json({
                    "event_type": "unlock_result",
                    "payload": {"success": success},
                })

            elif event_type == "operation":
                # Apply edit operation
                operation = EditOperation(
                    operation_id=payload.get("operation_id", str(datetime.now(UTC).timestamp())),
                    section_id=payload["section_id"],
                    operation_type=OperationType(payload["operation_type"]),
                    position=payload["position"],
                    content=payload.get("content"),
                    length=payload.get("length"),
                    user_id=user_id,
                    base_version=payload.get("base_version", 0),
                )
                result = await service.apply_operation(
                    session_id,
                    payload["section_id"],
                    user_id,
                    operation,
                )
                await websocket.send_json({
                    "event_type": "operation_result",
                    "payload": result,
                })

            elif event_type == "heartbeat" or event_type == "pong":
                await service.update_heartbeat(session_id, user_id)

            elif event_type == "leave":
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}/{user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cleanup
        service.remove_listener(session_id, broadcast_handler)
        manager.disconnect(session_id, user_id)
        await service.leave_session(session_id, user_id)


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.post("/{session_id}/join", response_model=JoinSessionResponse)
async def join_session(
    session_id: str,
    request: JoinSessionRequest,
    user_id: str = Query(..., description="User ID"),
):
    """
    Join a collaboration session via HTTP.

    For real-time updates, use the WebSocket endpoint instead.
    """
    service = get_collaboration_service()
    result = await service.join_session(session_id, user_id, request.username)

    return JoinSessionResponse(
        connection_id=result["connection_id"],
        your_color=result["your_color"],
        collaborators=result["collaborators"],
        locked_sections=result["locked_sections"],
    )


@router.post("/{session_id}/leave")
async def leave_session(
    session_id: str,
    user_id: str = Query(..., description="User ID"),
):
    """Leave a collaboration session."""
    service = get_collaboration_service()
    await service.leave_session(session_id, user_id)
    return {"success": True}


@router.get("/{session_id}/collaborators", response_model=list[CollaboratorResponse])
async def get_collaborators(
    session_id: str,
):
    """Get all collaborators in a session."""
    service = get_collaboration_service()
    collaborators = await service.get_collaborators(session_id)

    return [
        CollaboratorResponse(
            user_id=c.user_id,
            username=c.username,
            color=c.color,
            active_section=c.active_section,
            cursor=c.cursor.to_dict() if c.cursor else None,
            is_connected=c.is_connected,
        )
        for c in collaborators
    ]


@router.post("/{session_id}/cursor")
async def update_cursor(
    session_id: str,
    request: CursorUpdateRequest,
    user_id: str = Query(..., description="User ID"),
):
    """Update cursor position via HTTP."""
    service = get_collaboration_service()

    cursor = CursorPosition(
        section_id=request.section_id,
        position=request.position,
        selection_start=request.selection_start,
        selection_end=request.selection_end,
    )

    await service.update_cursor(session_id, user_id, cursor)
    return {"success": True}


@router.post("/{session_id}/sections/{section_id}/lock", response_model=LockResponse)
async def lock_section(
    session_id: str,
    section_id: str,
    request: LockSectionRequest,
    user_id: str = Query(..., description="User ID"),
):
    """Lock a section for editing."""
    service = get_collaboration_service()

    lock = await service.lock_section(
        session_id,
        section_id,
        user_id,
        request.username,
    )

    if lock:
        return LockResponse(
            success=True,
            lock=lock.to_dict(),
        )
    else:
        return LockResponse(
            success=False,
            message="Section is locked by another user",
        )


@router.post("/{session_id}/sections/{section_id}/unlock", response_model=LockResponse)
async def unlock_section(
    session_id: str,
    section_id: str,
    user_id: str = Query(..., description="User ID"),
):
    """Unlock a section."""
    service = get_collaboration_service()

    success = await service.unlock_section(session_id, section_id, user_id)

    return LockResponse(
        success=success,
        message=None if success else "You don't have the lock on this section",
    )


@router.post("/{session_id}/sections/{section_id}/refresh-lock")
async def refresh_lock(
    session_id: str,
    section_id: str,
    user_id: str = Query(..., description="User ID"),
):
    """Refresh a section lock to prevent expiry."""
    service = get_collaboration_service()
    success = await service.refresh_lock(session_id, section_id, user_id)

    return {"success": success}


@router.get("/{session_id}/locks", response_model=list[dict[str, Any]])
async def get_locked_sections(
    session_id: str,
):
    """Get all locked sections in a session."""
    service = get_collaboration_service()
    locks = await service.get_locked_sections(session_id)

    return [lock.to_dict() for lock in locks]


@router.post("/{session_id}/sections/{section_id}/operation", response_model=EditOperationResponse)
async def apply_operation(
    session_id: str,
    section_id: str,
    request: EditOperationRequest,
    user_id: str = Query(..., description="User ID"),
):
    """Apply an edit operation to a section."""
    service = get_collaboration_service()

    operation = EditOperation(
        operation_id=str(datetime.now(UTC).timestamp()),
        section_id=section_id,
        operation_type=OperationType(request.operation_type),
        position=request.position,
        content=request.content,
        length=request.length,
        user_id=user_id,
        base_version=request.base_version,
    )

    result = await service.apply_operation(session_id, section_id, user_id, operation)

    return EditOperationResponse(
        success=result.get("success", False),
        version=result.get("version", 0),
        error=result.get("error"),
    )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint for collaboration service."""
    return {
        "status": "healthy",
        "service": "collaboration",
        "timestamp": datetime.now(UTC).isoformat(),
    }
