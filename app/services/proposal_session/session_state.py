"""
Proposal Session State Management

This module defines the state dataclasses for the unified proposal session,
combining conversation context with document state for seamless AI-assisted
proposal writing.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class SessionStatus(str, Enum):
    """Status of a proposal session."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    EXPIRED = "expired"


class SectionLockStatus(str, Enum):
    """Lock status for a section during AI generation."""

    UNLOCKED = "unlocked"
    LOCKED_BY_AI = "locked_by_ai"
    LOCKED_BY_USER = "locked_by_user"


class SectionStatus(str, Enum):
    """Status of a proposal section."""

    EMPTY = "empty"
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    COMPLETE = "complete"


@dataclass
class InlineSuggestion:
    """Inline suggestion for text improvement."""

    suggestion_id: str
    start_position: int
    end_position: int
    original_text: str
    suggested_text: str
    reason: str
    category: str  # 'grammar', 'clarity', 'terminology', 'impact', 'compliance'
    priority: str  # 'high', 'medium', 'low'
    applied: bool = False


@dataclass
class Gap:
    """Identified gap in a proposal section."""

    gap_id: str
    description: str
    severity: str  # 'critical', 'major', 'minor'
    category: str  # 'content', 'structure', 'evidence', 'compliance'
    suggested_fix: str
    effort_level: str  # 'quick', 'medium', 'substantial'
    resolved: bool = False


@dataclass
class SectionState:
    """State of a single proposal section."""

    section_id: str
    section_name: str
    content: str = ""
    word_count: int = 0
    quality_score: float | None = None  # 0-5 scale
    status: SectionStatus = SectionStatus.EMPTY
    suggestions: list[InlineSuggestion] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    lock_status: SectionLockStatus = SectionLockStatus.UNLOCKED
    locked_at: datetime | None = None
    is_dirty: bool = False  # Has unsaved changes
    version: int = 1
    last_updated: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "section_id": self.section_id,
            "section_name": self.section_name,
            "content": self.content,
            "word_count": self.word_count,
            "quality_score": self.quality_score,
            "status": self.status.value,
            "suggestions_count": len([s for s in self.suggestions if not s.applied]),
            "gaps_count": len([g for g in self.gaps if not g.resolved]),
            "lock_status": self.lock_status.value,
            "is_dirty": self.is_dirty,
            "version": self.version,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


@dataclass
class ProposalDocument:
    """Complete proposal document state."""

    proposal_id: int
    call_id: str
    title: str
    acronym: str | None = None
    proposal_type: str = "RIA"
    status: str = "draft"
    sections: dict[str, SectionState] = field(default_factory=dict)
    overall_score: float | None = None
    completion_percentage: float = 0.0
    total_words: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def get_section(self, section_id: str) -> SectionState | None:
        """Get a section by ID."""
        return self.sections.get(section_id)

    def update_section(self, section_id: str, content: str) -> None:
        """Update section content and recalculate stats."""
        if section_id in self.sections:
            section = self.sections[section_id]
            section.content = content
            section.word_count = len(content.split()) if content else 0
            section.is_dirty = True
            section.last_updated = datetime.now(UTC)

            # Update status based on content
            if not content or section.word_count < 10:
                section.status = SectionStatus.EMPTY
            elif section.word_count < 100:
                section.status = SectionStatus.DRAFT
            else:
                section.status = SectionStatus.IN_REVIEW

            self._recalculate_totals()

    def _recalculate_totals(self) -> None:
        """Recalculate total words and completion percentage."""
        self.total_words = sum(s.word_count for s in self.sections.values())

        total_sections = len(self.sections)
        if total_sections > 0:
            completed = sum(
                1
                for s in self.sections.values()
                if s.status in (SectionStatus.IN_REVIEW, SectionStatus.COMPLETE)
            )
            self.completion_percentage = (completed / total_sections) * 100

        # Calculate overall score as average of sections with scores
        scored_sections = [s for s in self.sections.values() if s.quality_score is not None]
        if scored_sections:
            self.overall_score = sum(s.quality_score for s in scored_sections) / len(
                scored_sections
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "proposal_id": self.proposal_id,
            "call_id": self.call_id,
            "title": self.title,
            "acronym": self.acronym,
            "proposal_type": self.proposal_type,
            "status": self.status,
            "overall_score": self.overall_score,
            "completion_percentage": self.completion_percentage,
            "total_words": self.total_words,
            "sections": {k: v.to_dict() for k, v in self.sections.items()},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class ConversationMessage:
    """A single message in the conversation."""

    message_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    tools_used: list[str] = field(default_factory=list)
    sections_affected: list[str] = field(default_factory=list)


@dataclass
class ConversationState:
    """Conversation state within a proposal session."""

    conversation_id: int
    messages: list[ConversationMessage] = field(default_factory=list)
    active_section_context: str | None = None  # Section the user is focused on

    def add_message(
        self,
        role: str,
        content: str,
        tools_used: list[str] | None = None,
        sections_affected: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        """Add a message to the conversation."""
        message = ConversationMessage(
            message_id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=datetime.now(UTC),
            metadata=metadata or {},
            tools_used=tools_used or [],
            sections_affected=sections_affected or [],
        )
        self.messages.append(message)
        return message

    def get_recent_messages(self, limit: int = 10) -> list[ConversationMessage]:
        """Get the most recent messages."""
        return self.messages[-limit:] if self.messages else []

    def get_context_for_agent(self, max_chars: int = 8000) -> str:
        """Format conversation history for agent context injection."""
        context_parts = []
        total_chars = 0

        for msg in reversed(self.messages):
            msg_text = f"{msg.role.upper()}: {msg.content}"
            if total_chars + len(msg_text) > max_chars:
                break
            context_parts.insert(0, msg_text)
            total_chars += len(msg_text)

        return "\n\n".join(context_parts)


@dataclass
class ProposalSessionState:
    """
    Unified session state combining conversation and document.

    This is the central state object that bridges:
    - Conversation context (chat history, agent interactions)
    - Document state (sections, content, scores)
    - Real-time sync state (pending changes, locks)
    """

    session_id: str
    user_id: str

    # Document state
    document: ProposalDocument

    # Conversation state
    conversation: ConversationState

    # Session metadata
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None

    # Active focus
    active_section_id: str | None = None

    # Sync state
    pending_changes: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create_new(
        cls,
        user_id: str,
        proposal_id: int,
        call_id: str,
        title: str,
        proposal_type: str = "RIA",
        conversation_id: int = 0,
    ) -> "ProposalSessionState":
        """Create a new session with default structure."""
        session_id = str(uuid.uuid4())

        # Initialize document with standard section structure
        document = ProposalDocument(
            proposal_id=proposal_id,
            call_id=call_id,
            title=title,
            proposal_type=proposal_type,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Initialize standard sections for RIA/IA proposals
        standard_sections = [
            ("excellence.objectives", "Objectives and ambition"),
            ("excellence.methodology", "Methodology"),
            ("excellence.beyond_sota", "Beyond the state of the art"),
            ("impact.pathways", "Pathways to impact"),
            ("impact.dissemination", "Dissemination and exploitation"),
            ("implementation.work_plan", "Work plan and resources"),
            ("implementation.consortium", "Consortium and management"),
        ]

        for section_id, section_name in standard_sections:
            document.sections[section_id] = SectionState(
                section_id=section_id,
                section_name=section_name,
            )

        # Initialize conversation
        conversation = ConversationState(conversation_id=conversation_id)

        return cls(
            session_id=session_id,
            user_id=user_id,
            document=document,
            conversation=conversation,
        )

    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity_at = datetime.now(UTC)

    def lock_section(
        self, section_id: str, lock_type: SectionLockStatus = SectionLockStatus.LOCKED_BY_AI
    ) -> bool:
        """Lock a section for AI generation."""
        section = self.document.get_section(section_id)
        if section and section.lock_status == SectionLockStatus.UNLOCKED:
            section.lock_status = lock_type
            section.locked_at = datetime.now(UTC)
            return True
        return False

    def unlock_section(self, section_id: str) -> bool:
        """Unlock a section after AI generation completes."""
        section = self.document.get_section(section_id)
        if section:
            section.lock_status = SectionLockStatus.UNLOCKED
            section.locked_at = None
            return True
        return False

    def is_section_locked(self, section_id: str) -> bool:
        """Check if a section is locked."""
        section = self.document.get_section(section_id)
        return section is not None and section.lock_status != SectionLockStatus.UNLOCKED

    def get_context_for_agent(self) -> str:
        """
        Generate context string for agent injection.

        This provides the agent with awareness of:
        - Current document state
        - Active section
        - Recent conversation
        - Quality scores and gaps
        """
        doc = self.document
        active_section = doc.get_section(self.active_section_id) if self.active_section_id else None

        context_parts = [
            "## Current Proposal State",
            f"**Proposal:** {doc.title}" + (f" ({doc.acronym})" if doc.acronym else ""),
            f"**Call:** {doc.call_id}",
            f"**Type:** {doc.proposal_type}",
            f"**Progress:** {doc.completion_percentage:.0f}% complete ({doc.total_words} words)",
            "",
            "### Section Overview",
        ]

        # Add section summaries
        for section in doc.sections.values():
            score_str = f"{section.quality_score:.1f}/5" if section.quality_score else "Not scored"
            gaps_str = (
                f", {len([g for g in section.gaps if not g.resolved])} gaps" if section.gaps else ""
            )
            context_parts.append(
                f"- **{section.section_name}**: {section.word_count} words, {section.status.value}, Score: {score_str}{gaps_str}"
            )

        # Add active section details if present
        if active_section:
            context_parts.extend(
                [
                    "",
                    f"### Active Section: {active_section.section_name}",
                    f"**Status:** {active_section.status.value}",
                    f"**Words:** {active_section.word_count}",
                    (
                        f"**Score:** {active_section.quality_score:.1f}/5"
                        if active_section.quality_score
                        else "**Score:** Not yet evaluated"
                    ),
                ]
            )

            if active_section.content:
                preview = active_section.content[:1000]
                if len(active_section.content) > 1000:
                    preview += "..."
                context_parts.extend(
                    [
                        "",
                        "**Current Content:**",
                        "```",
                        preview,
                        "```",
                    ]
                )

            # Add top gaps
            unresolved_gaps = [g for g in active_section.gaps if not g.resolved][:3]
            if unresolved_gaps:
                context_parts.extend(
                    [
                        "",
                        "**Top Gaps to Address:**",
                    ]
                )
                for gap in unresolved_gaps:
                    context_parts.append(f"- [{gap.severity}] {gap.description}")

        return "\n".join(context_parts)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "active_section_id": self.active_section_id,
            "document": self.document.to_dict(),
            "conversation_messages_count": len(self.conversation.messages),
            "created_at": self.created_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
        }
