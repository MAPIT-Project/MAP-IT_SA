"""
Proposal Session Package

This package provides unified session management for AI-assisted proposal writing,
bridging conversation context with document state for seamless interaction.

Key Components:
- ProposalSessionState: Unified state combining conversation + document
- ProposalSessionManager: Session lifecycle and persistence
- DocumentStateService: Section content and metadata management
"""

from .document_state_service import DocumentStateService
from .proposal_session_manager import ProposalSessionManager
from .session_state import (
    ConversationMessage,
    ConversationState,
    Gap,
    InlineSuggestion,
    ProposalDocument,
    ProposalSessionState,
    SectionLockStatus,
    SectionState,
    SectionStatus,
    SessionStatus,
)

__all__ = [
    # Enums
    "SessionStatus",
    "SectionLockStatus",
    "SectionStatus",
    # State classes
    "InlineSuggestion",
    "Gap",
    "SectionState",
    "ProposalDocument",
    "ConversationMessage",
    "ConversationState",
    "ProposalSessionState",
    # Services
    "ProposalSessionManager",
    "DocumentStateService",
]
