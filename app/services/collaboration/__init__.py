"""
Collaboration Service Module.

Provides functionality for:
- Real-time proposal collaboration
- Section locking
- Cursor tracking
- WebSocket support for live updates
"""

from app.services.collaboration.collaboration_service import (
    CollaborationService,
    CollaboratorSession,
    SectionLock,
    get_collaboration_service,
)

__all__ = [
    "CollaborationService",
    "CollaboratorSession",
    "SectionLock",
    "get_collaboration_service",
]
