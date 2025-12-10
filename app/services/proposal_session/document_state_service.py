"""
Document State Service

Provides high-level operations for managing proposal document state,
including section content, quality analysis, and real-time updates.
Works in conjunction with ProposalSessionManager for persistence.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .session_state import (
    Gap,
    InlineSuggestion,
    ProposalDocument,
    ProposalSessionState,
    SectionLockStatus,
    SectionState,
    SectionStatus,
)

logger = logging.getLogger(__name__)


class DocumentStateService:
    """
    High-level service for document state operations.

    Provides:
    - Section content analysis and word counting
    - Quality score management
    - Gap and suggestion tracking
    - Section navigation and focus management
    - Document overview generation for agents

    Works with ProposalSessionManager for persistence operations.
    """

    # Standard section structure for RIA/IA proposals
    STANDARD_SECTIONS_RIA = [
        ("excellence.objectives", "Objectives and ambition"),
        ("excellence.methodology", "Methodology"),
        ("excellence.beyond_sota", "Beyond the state of the art"),
        ("impact.pathways", "Pathways to impact"),
        ("impact.dissemination", "Dissemination and exploitation"),
        ("implementation.work_plan", "Work plan and resources"),
        ("implementation.consortium", "Consortium and management"),
    ]

    # Section structure for CSA proposals
    STANDARD_SECTIONS_CSA = [
        ("excellence.objectives", "Objectives and ambition"),
        ("excellence.methodology", "Methodology"),
        ("impact.expected_outcomes", "Expected outcomes and impacts"),
        ("impact.dissemination", "Dissemination and exploitation"),
        ("implementation.work_plan", "Work plan and resources"),
        ("implementation.consortium", "Consortium and management"),
    ]

    # Section structure for ERC proposals
    STANDARD_SECTIONS_ERC = [
        ("extended_synopsis", "Extended synopsis"),
        ("cv", "Curriculum vitae"),
        ("track_record", "Track record"),
        ("research_proposal", "Research proposal"),
    ]

    def __init__(self):
        """Initialize the document state service."""
        pass

    # =========================================================================
    # Section Structure Operations
    # =========================================================================

    def get_standard_sections(self, proposal_type: str) -> List[Tuple[str, str]]:
        """
        Get standard section structure for a proposal type.

        Args:
            proposal_type: Type of proposal (RIA, IA, CSA, ERC)

        Returns:
            List of (section_id, section_name) tuples
        """
        proposal_type = proposal_type.upper()
        if proposal_type in ("RIA", "IA"):
            return self.STANDARD_SECTIONS_RIA
        elif proposal_type == "CSA":
            return self.STANDARD_SECTIONS_CSA
        elif proposal_type == "ERC":
            return self.STANDARD_SECTIONS_ERC
        else:
            # Default to RIA structure
            return self.STANDARD_SECTIONS_RIA

    def initialize_document_sections(
        self, document: ProposalDocument, proposal_type: str = "RIA"
    ) -> None:
        """
        Initialize a document with standard sections.

        Args:
            document: Document to initialize
            proposal_type: Type of proposal
        """
        sections = self.get_standard_sections(proposal_type)
        for section_id, section_name in sections:
            if section_id not in document.sections:
                document.sections[section_id] = SectionState(
                    section_id=section_id,
                    section_name=section_name,
                )
        logger.info(
            f"Initialized {len(sections)} sections for {proposal_type} proposal"
        )

    # =========================================================================
    # Section Content Operations
    # =========================================================================

    def update_section_content(
        self,
        session: ProposalSessionState,
        section_id: str,
        content: str,
        source: str = "user",
    ) -> Optional[SectionState]:
        """
        Update section content with validation.

        Args:
            session: Current session state
            section_id: Section to update
            content: New content
            source: Source of update ('user', 'ai')

        Returns:
            Updated section state or None if failed
        """
        section = session.document.get_section(section_id)
        if not section:
            logger.warning(f"Section not found: {section_id}")
            return None

        # Check lock status
        if section.lock_status == SectionLockStatus.LOCKED_BY_AI and source == "user":
            logger.warning(f"Section {section_id} is locked by AI")
            return None
        if section.lock_status == SectionLockStatus.LOCKED_BY_USER and source == "ai":
            logger.warning(f"Section {section_id} is locked by user")
            return None

        # Update content
        session.document.update_section(section_id, content)

        return section

    def append_to_section(
        self,
        session: ProposalSessionState,
        section_id: str,
        content: str,
        separator: str = "\n\n",
    ) -> Optional[SectionState]:
        """
        Append content to an existing section.

        Args:
            session: Current session state
            section_id: Section to append to
            content: Content to append
            separator: Separator between existing and new content

        Returns:
            Updated section state or None if failed
        """
        section = session.document.get_section(section_id)
        if not section:
            return None

        new_content = section.content + separator + content if section.content else content
        return self.update_section_content(session, section_id, new_content, "ai")

    def clear_section(
        self, session: ProposalSessionState, section_id: str
    ) -> Optional[SectionState]:
        """
        Clear section content.

        Args:
            session: Current session state
            section_id: Section to clear

        Returns:
            Updated section state or None if failed
        """
        return self.update_section_content(session, section_id, "", "user")

    # =========================================================================
    # Quality Score Operations
    # =========================================================================

    def update_quality_score(
        self,
        session: ProposalSessionState,
        section_id: str,
        score: float,
        breakdown: Optional[Dict[str, float]] = None,
    ) -> bool:
        """
        Update quality score for a section.

        Args:
            session: Current session state
            section_id: Section to update
            score: Quality score (0-5 scale)
            breakdown: Optional score breakdown by criterion

        Returns:
            True if updated successfully
        """
        section = session.document.get_section(section_id)
        if not section:
            return False

        # Validate and clamp score
        section.quality_score = max(0.0, min(5.0, score))

        # Update status based on score
        if section.quality_score >= 4.0 and section.word_count >= 100:
            section.status = SectionStatus.COMPLETE
        elif section.quality_score >= 2.5 and section.word_count >= 50:
            section.status = SectionStatus.IN_REVIEW
        elif section.word_count >= 10:
            section.status = SectionStatus.DRAFT
        else:
            section.status = SectionStatus.EMPTY

        # Recalculate document totals
        session.document._recalculate_totals()

        logger.info(
            f"Updated quality score for {section_id}: {score:.1f}/5 "
            f"(status: {section.status.value})"
        )
        return True

    def calculate_section_completeness(self, section: SectionState) -> float:
        """
        Calculate completeness percentage for a section.

        Args:
            section: Section to analyze

        Returns:
            Completeness percentage (0-100)
        """
        # Factors: word count, quality score, gaps resolved
        word_score = min(100, (section.word_count / 500) * 100) if section.word_count else 0
        quality_score = (section.quality_score / 5 * 100) if section.quality_score else 0

        total_gaps = len(section.gaps)
        resolved_gaps = len([g for g in section.gaps if g.resolved])
        gap_score = (resolved_gaps / total_gaps * 100) if total_gaps > 0 else 100

        # Weighted average
        completeness = (word_score * 0.4) + (quality_score * 0.4) + (gap_score * 0.2)
        return round(completeness, 1)

    # =========================================================================
    # Gap and Suggestion Operations
    # =========================================================================

    def add_gap(
        self,
        session: ProposalSessionState,
        section_id: str,
        description: str,
        severity: str = "major",
        category: str = "content",
        suggested_fix: str = "",
        effort_level: str = "medium",
    ) -> Optional[Gap]:
        """
        Add a gap to a section.

        Args:
            session: Current session state
            section_id: Target section
            description: Gap description
            severity: 'critical', 'major', 'minor'
            category: 'content', 'structure', 'evidence', 'compliance'
            suggested_fix: Suggested resolution
            effort_level: 'quick', 'medium', 'substantial'

        Returns:
            Created Gap or None if failed
        """
        section = session.document.get_section(section_id)
        if not section:
            return None

        gap = Gap(
            gap_id=str(uuid.uuid4()),
            description=description,
            severity=severity,
            category=category,
            suggested_fix=suggested_fix,
            effort_level=effort_level,
        )
        section.gaps.append(gap)
        return gap

    def resolve_gap(
        self, session: ProposalSessionState, section_id: str, gap_id: str
    ) -> bool:
        """
        Mark a gap as resolved.

        Args:
            session: Current session state
            section_id: Section containing the gap
            gap_id: Gap to resolve

        Returns:
            True if resolved successfully
        """
        section = session.document.get_section(section_id)
        if not section:
            return False

        for gap in section.gaps:
            if gap.gap_id == gap_id:
                gap.resolved = True
                return True
        return False

    def add_suggestion(
        self,
        session: ProposalSessionState,
        section_id: str,
        original_text: str,
        suggested_text: str,
        reason: str,
        category: str = "clarity",
        priority: str = "medium",
        start_position: int = 0,
        end_position: int = 0,
    ) -> Optional[InlineSuggestion]:
        """
        Add an inline suggestion to a section.

        Args:
            session: Current session state
            section_id: Target section
            original_text: Text to replace
            suggested_text: Replacement text
            reason: Reason for suggestion
            category: 'grammar', 'clarity', 'terminology', 'impact', 'compliance'
            priority: 'high', 'medium', 'low'
            start_position: Start character position
            end_position: End character position

        Returns:
            Created InlineSuggestion or None if failed
        """
        section = session.document.get_section(section_id)
        if not section:
            return None

        suggestion = InlineSuggestion(
            suggestion_id=str(uuid.uuid4()),
            start_position=start_position,
            end_position=end_position,
            original_text=original_text,
            suggested_text=suggested_text,
            reason=reason,
            category=category,
            priority=priority,
        )
        section.suggestions.append(suggestion)
        return suggestion

    def apply_suggestion(
        self, session: ProposalSessionState, section_id: str, suggestion_id: str
    ) -> bool:
        """
        Apply an inline suggestion (replace text).

        Args:
            session: Current session state
            section_id: Section containing the suggestion
            suggestion_id: Suggestion to apply

        Returns:
            True if applied successfully
        """
        section = session.document.get_section(section_id)
        if not section:
            return False

        for suggestion in section.suggestions:
            if suggestion.suggestion_id == suggestion_id and not suggestion.applied:
                # Replace the text
                new_content = section.content.replace(
                    suggestion.original_text, suggestion.suggested_text, 1
                )
                session.document.update_section(section_id, new_content)
                suggestion.applied = True
                return True
        return False

    def dismiss_suggestion(
        self, session: ProposalSessionState, section_id: str, suggestion_id: str
    ) -> bool:
        """
        Dismiss (remove) an inline suggestion.

        Args:
            session: Current session state
            section_id: Section containing the suggestion
            suggestion_id: Suggestion to dismiss

        Returns:
            True if dismissed successfully
        """
        section = session.document.get_section(section_id)
        if not section:
            return False

        for i, suggestion in enumerate(section.suggestions):
            if suggestion.suggestion_id == suggestion_id:
                section.suggestions.pop(i)
                return True
        return False

    # =========================================================================
    # Document Overview Operations
    # =========================================================================

    def get_document_overview(
        self, session: ProposalSessionState
    ) -> Dict[str, Any]:
        """
        Get comprehensive document overview for agent context.

        Args:
            session: Current session state

        Returns:
            Document overview dictionary
        """
        doc = session.document
        sections_summary = []

        for section in doc.sections.values():
            unresolved_gaps = [g for g in section.gaps if not g.resolved]
            pending_suggestions = [s for s in section.suggestions if not s.applied]

            sections_summary.append({
                "id": section.section_id,
                "name": section.section_name,
                "status": section.status.value,
                "word_count": section.word_count,
                "quality_score": section.quality_score,
                "completeness": self.calculate_section_completeness(section),
                "unresolved_gaps": len(unresolved_gaps),
                "pending_suggestions": len(pending_suggestions),
                "is_locked": section.lock_status != SectionLockStatus.UNLOCKED,
            })

        return {
            "proposal_id": doc.proposal_id,
            "title": doc.title,
            "acronym": doc.acronym,
            "call_id": doc.call_id,
            "proposal_type": doc.proposal_type,
            "status": doc.status,
            "overall_score": doc.overall_score,
            "completion_percentage": doc.completion_percentage,
            "total_words": doc.total_words,
            "sections": sections_summary,
            "active_section": session.active_section_id,
        }

    def get_section_details(
        self, session: ProposalSessionState, section_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a section.

        Args:
            session: Current session state
            section_id: Section to get details for

        Returns:
            Section details dictionary or None
        """
        section = session.document.get_section(section_id)
        if not section:
            return None

        unresolved_gaps = [
            {
                "id": g.gap_id,
                "description": g.description,
                "severity": g.severity,
                "category": g.category,
                "suggested_fix": g.suggested_fix,
                "effort_level": g.effort_level,
            }
            for g in section.gaps
            if not g.resolved
        ]

        pending_suggestions = [
            {
                "id": s.suggestion_id,
                "original_text": s.original_text,
                "suggested_text": s.suggested_text,
                "reason": s.reason,
                "category": s.category,
                "priority": s.priority,
            }
            for s in section.suggestions
            if not s.applied
        ]

        return {
            "section_id": section.section_id,
            "section_name": section.section_name,
            "content": section.content,
            "word_count": section.word_count,
            "quality_score": section.quality_score,
            "status": section.status.value,
            "completeness": self.calculate_section_completeness(section),
            "lock_status": section.lock_status.value,
            "version": section.version,
            "gaps": unresolved_gaps,
            "suggestions": pending_suggestions,
            "last_updated": (
                section.last_updated.isoformat() if section.last_updated else None
            ),
        }

    def get_sections_needing_attention(
        self, session: ProposalSessionState
    ) -> List[Dict[str, Any]]:
        """
        Get sections that need attention (low scores, gaps, incomplete).

        Args:
            session: Current session state

        Returns:
            List of sections needing attention with reasons
        """
        attention_needed = []

        for section in session.document.sections.values():
            reasons = []

            # Check for critical gaps
            critical_gaps = [g for g in section.gaps if not g.resolved and g.severity == "critical"]
            if critical_gaps:
                reasons.append(f"{len(critical_gaps)} critical gap(s)")

            # Check for low quality score
            if section.quality_score is not None and section.quality_score < 3.0:
                reasons.append(f"Low quality score ({section.quality_score:.1f}/5)")

            # Check for empty or short content
            if section.word_count < 50:
                reasons.append("Insufficient content")

            # Check for high-priority suggestions
            high_priority = [s for s in section.suggestions if not s.applied and s.priority == "high"]
            if high_priority:
                reasons.append(f"{len(high_priority)} high-priority suggestion(s)")

            if reasons:
                attention_needed.append({
                    "section_id": section.section_id,
                    "section_name": section.section_name,
                    "reasons": reasons,
                    "word_count": section.word_count,
                    "quality_score": section.quality_score,
                })

        # Sort by urgency (critical gaps first, then low scores)
        attention_needed.sort(
            key=lambda x: (
                "critical gap" not in str(x["reasons"]),
                x.get("quality_score") or 0,
            )
        )

        return attention_needed

    # =========================================================================
    # Navigation Operations
    # =========================================================================

    def set_active_section(
        self, session: ProposalSessionState, section_id: Optional[str]
    ) -> bool:
        """
        Set the currently active section.

        Args:
            session: Current session state
            section_id: Section to focus on (None to clear)

        Returns:
            True if set successfully
        """
        if section_id and section_id not in session.document.sections:
            return False

        session.active_section_id = section_id
        session.conversation.active_section_context = section_id
        return True

    def get_next_section(
        self, session: ProposalSessionState, current_section_id: str
    ) -> Optional[str]:
        """
        Get the next section in order.

        Args:
            session: Current session state
            current_section_id: Current section

        Returns:
            Next section ID or None
        """
        sections = list(session.document.sections.keys())
        try:
            idx = sections.index(current_section_id)
            if idx < len(sections) - 1:
                return sections[idx + 1]
        except ValueError:
            pass
        return None

    def get_previous_section(
        self, session: ProposalSessionState, current_section_id: str
    ) -> Optional[str]:
        """
        Get the previous section in order.

        Args:
            session: Current session state
            current_section_id: Current section

        Returns:
            Previous section ID or None
        """
        sections = list(session.document.sections.keys())
        try:
            idx = sections.index(current_section_id)
            if idx > 0:
                return sections[idx - 1]
        except ValueError:
            pass
        return None
