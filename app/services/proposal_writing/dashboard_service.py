"""
Dashboard Service

Aggregates all proposal data into a comprehensive dashboard view.
Provides submission readiness checks and prioritized next actions.
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.services.proposal_writing.progress_tracking_service import ProgressTrackingService

logger = logging.getLogger(__name__)


class SectionStatus(str, Enum):
    """Status of a proposal section."""
    NOT_STARTED = "not_started"      # No content
    DRAFT = "draft"                   # Has content, not evaluated
    NEEDS_WORK = "needs_work"         # Score < 3.0
    ACCEPTABLE = "acceptable"         # Score 3.0-3.5
    GOOD = "good"                     # Score 3.5-4.0
    EXCELLENT = "excellent"           # Score > 4.0


class ActionPriority(str, Enum):
    """Priority level for actions."""
    CRITICAL = "critical"     # Blocking submission
    HIGH = "high"             # Should do soon
    MEDIUM = "medium"         # When you have time
    LOW = "low"               # Nice to have


@dataclass
class SectionSummary:
    """Summary of a single section."""
    id: str
    title: str
    section_type: str
    status: SectionStatus
    word_count: int
    score: Optional[float]
    confidence: Optional[float]
    gap_count: int
    suggestion_count: int
    last_edited: Optional[datetime]


@dataclass
class NextAction:
    """A recommended next action."""
    id: str
    title: str
    description: str
    priority: ActionPriority
    section_id: Optional[str]
    section_title: Optional[str]
    action_type: str  # write, improve, review, fix
    estimated_minutes: int
    impact: str  # Description of impact


@dataclass
class ReadinessCheck:
    """A submission readiness check item."""
    id: str
    category: str
    title: str
    description: str
    passed: bool
    details: Optional[str]
    blocking: bool  # If false, can still submit


@dataclass
class DashboardData:
    """Complete dashboard data."""
    proposal_id: str
    proposal_title: str
    call_id: Optional[str]
    call_title: Optional[str]
    deadline: Optional[datetime]

    # Overall metrics
    completion_percentage: float
    overall_score: Optional[float]
    funding_probability: Optional[float]
    submission_ready: bool

    # Section breakdown
    sections: List[SectionSummary]
    sections_by_status: Dict[str, int]

    # Actions
    next_actions: List[NextAction]

    # Readiness
    readiness_checks: List[ReadinessCheck]
    readiness_score: float  # 0-100

    # Progress
    time_spent_minutes: int
    days_until_deadline: Optional[int]
    streak: int


class DashboardService:
    """
    Service for generating comprehensive proposal dashboard data.

    Aggregates data from multiple sources to provide a unified view
    of proposal status and recommended actions.
    """

    # Score thresholds
    THRESHOLD_SCORE = 3.0
    GOOD_SCORE = 3.5
    EXCELLENT_SCORE = 4.0

    def __init__(self):
        self.progress_service = ProgressTrackingService()
        self._proposal_cache: Dict[str, Dict[str, Any]] = {}
        self._sections_cache: Dict[str, List[SectionSummary]] = {}

    async def get_dashboard(
        self,
        proposal_id: str,
        user_id: str
    ) -> DashboardData:
        """
        Get complete dashboard data for a proposal.

        Args:
            proposal_id: The proposal ID
            user_id: The user ID for streak data

        Returns:
            Complete dashboard data
        """
        # Get proposal info (using cache or defaults for now)
        proposal = self._proposal_cache.get(proposal_id, {
            'id': proposal_id,
            'title': 'Untitled Proposal',
            'call_id': None,
            'call_title': None,
            'deadline': None
        })

        # Get sections
        sections = await self._get_section_summaries(proposal_id)

        # Get overall metrics
        progress = await self.progress_service.get_progress(proposal_id)
        streak = await self.progress_service.get_streak(user_id)

        # Calculate sections by status
        sections_by_status = self._count_by_status(sections)

        # Get next actions
        next_actions = self._generate_next_actions(proposal_id, sections)

        # Run readiness checks
        readiness_checks = self._run_readiness_checks(proposal_id, sections)
        readiness_score = self._calculate_readiness_score(readiness_checks)

        # Calculate submission readiness
        submission_ready = all(c.passed for c in readiness_checks if c.blocking)

        # Calculate days until deadline
        days_until = None
        if proposal.get('deadline'):
            delta = proposal['deadline'] - datetime.now()
            days_until = max(0, delta.days)

        # Calculate funding probability
        funding_probability = self._estimate_funding_probability(
            progress.average_score,
            readiness_score
        )

        return DashboardData(
            proposal_id=proposal_id,
            proposal_title=proposal.get('title', 'Untitled Proposal'),
            call_id=proposal.get('call_id'),
            call_title=proposal.get('call_title'),
            deadline=proposal.get('deadline'),
            completion_percentage=progress.completion_percentage,
            overall_score=progress.average_score,
            funding_probability=funding_probability,
            submission_ready=submission_ready,
            sections=sections,
            sections_by_status=sections_by_status,
            next_actions=next_actions,
            readiness_checks=readiness_checks,
            readiness_score=readiness_score,
            time_spent_minutes=progress.time_spent_minutes,
            days_until_deadline=days_until,
            streak=streak.current_streak
        )

    async def _get_section_summaries(
        self,
        proposal_id: str
    ) -> List[SectionSummary]:
        """Get summaries for all sections."""
        # Check cache
        if proposal_id in self._sections_cache:
            return self._sections_cache[proposal_id]

        # Return empty list (in real implementation, would query database)
        return []

    def add_section(
        self,
        proposal_id: str,
        section_id: str,
        title: str,
        section_type: str,
        content: str = "",
        score: Optional[float] = None,
        confidence: Optional[float] = None
    ) -> SectionSummary:
        """Add a section to the dashboard cache."""
        word_count = len(content.split()) if content else 0

        # Determine status
        if word_count < 50:
            status = SectionStatus.NOT_STARTED
        elif score is None:
            status = SectionStatus.DRAFT
        elif score < self.THRESHOLD_SCORE:
            status = SectionStatus.NEEDS_WORK
        elif score < self.GOOD_SCORE:
            status = SectionStatus.ACCEPTABLE
        elif score < self.EXCELLENT_SCORE:
            status = SectionStatus.GOOD
        else:
            status = SectionStatus.EXCELLENT

        summary = SectionSummary(
            id=section_id,
            title=title,
            section_type=section_type,
            status=status,
            word_count=word_count,
            score=score,
            confidence=confidence,
            gap_count=0,
            suggestion_count=0,
            last_edited=datetime.now()
        )

        if proposal_id not in self._sections_cache:
            self._sections_cache[proposal_id] = []
        self._sections_cache[proposal_id].append(summary)

        return summary

    def update_section_score(
        self,
        proposal_id: str,
        section_id: str,
        score: float,
        confidence: Optional[float] = None
    ) -> Optional[SectionSummary]:
        """Update a section's score."""
        sections = self._sections_cache.get(proposal_id, [])
        for section in sections:
            if section.id == section_id:
                section.score = score
                if confidence is not None:
                    section.confidence = confidence

                # Update status based on new score
                if section.word_count < 50:
                    section.status = SectionStatus.NOT_STARTED
                elif score < self.THRESHOLD_SCORE:
                    section.status = SectionStatus.NEEDS_WORK
                elif score < self.GOOD_SCORE:
                    section.status = SectionStatus.ACCEPTABLE
                elif score < self.EXCELLENT_SCORE:
                    section.status = SectionStatus.GOOD
                else:
                    section.status = SectionStatus.EXCELLENT

                return section
        return None

    def set_proposal_info(
        self,
        proposal_id: str,
        title: str,
        call_id: Optional[str] = None,
        call_title: Optional[str] = None,
        deadline: Optional[datetime] = None
    ):
        """Set proposal info in cache."""
        self._proposal_cache[proposal_id] = {
            'id': proposal_id,
            'title': title,
            'call_id': call_id,
            'call_title': call_title,
            'deadline': deadline
        }

    def _count_by_status(self, sections: List[SectionSummary]) -> Dict[str, int]:
        """Count sections by status."""
        counts = {status.value: 0 for status in SectionStatus}
        for section in sections:
            counts[section.status.value] += 1
        return counts

    def _generate_next_actions(
        self,
        proposal_id: str,
        sections: List[SectionSummary]
    ) -> List[NextAction]:
        """Generate prioritized list of next actions."""
        actions = []
        action_id = 0

        for section in sections:
            # Not started sections
            if section.status == SectionStatus.NOT_STARTED:
                action_id += 1
                actions.append(NextAction(
                    id=f"action_{action_id}",
                    title=f"Start writing: {section.title}",
                    description=f"This section has no content yet. Start with an outline.",
                    priority=ActionPriority.CRITICAL,
                    section_id=section.id,
                    section_title=section.title,
                    action_type="write",
                    estimated_minutes=60,
                    impact="Required for submission"
                ))

            # Draft sections (not evaluated)
            elif section.status == SectionStatus.DRAFT:
                action_id += 1
                actions.append(NextAction(
                    id=f"action_{action_id}",
                    title=f"Evaluate: {section.title}",
                    description="Run AI evaluation to get score and improvement suggestions.",
                    priority=ActionPriority.HIGH,
                    section_id=section.id,
                    section_title=section.title,
                    action_type="review",
                    estimated_minutes=5,
                    impact="Get feedback on current quality"
                ))

            # Below threshold
            elif section.status == SectionStatus.NEEDS_WORK:
                action_id += 1
                score_str = f"{section.score:.1f}" if section.score else "N/A"
                actions.append(NextAction(
                    id=f"action_{action_id}",
                    title=f"Improve: {section.title}",
                    description=f"Score is {score_str}/5, needs to reach 3.0 for funding threshold.",
                    priority=ActionPriority.CRITICAL,
                    section_id=section.id,
                    section_title=section.title,
                    action_type="improve",
                    estimated_minutes=45,
                    impact=f"+{3.0 - (section.score or 0):.1f} points needed"
                ))

            # Has gaps
            if section.gap_count > 0:
                action_id += 1
                actions.append(NextAction(
                    id=f"action_{action_id}",
                    title=f"Close {section.gap_count} gaps in {section.title}",
                    description="Address identified weaknesses to improve score.",
                    priority=ActionPriority.MEDIUM if section.score and section.score >= 3.0 else ActionPriority.HIGH,
                    section_id=section.id,
                    section_title=section.title,
                    action_type="fix",
                    estimated_minutes=section.gap_count * 15,
                    impact=f"Could improve score by ~{section.gap_count * 0.2:.1f} points"
                ))

        # Sort by priority
        priority_order = {
            ActionPriority.CRITICAL: 0,
            ActionPriority.HIGH: 1,
            ActionPriority.MEDIUM: 2,
            ActionPriority.LOW: 3
        }
        actions.sort(key=lambda a: priority_order[a.priority])

        return actions[:10]  # Top 10 actions

    def _run_readiness_checks(
        self,
        proposal_id: str,
        sections: List[SectionSummary]
    ) -> List[ReadinessCheck]:
        """Run all submission readiness checks."""
        checks = []

        # Check 1: All sections have content
        not_started = [s for s in sections if s.status == SectionStatus.NOT_STARTED]
        checks.append(ReadinessCheck(
            id="all_content",
            category="Content",
            title="All sections have content",
            description="Every section must have substantive content",
            passed=len(not_started) == 0,
            details=f"{len(not_started)} sections need content" if not_started else None,
            blocking=True
        ))

        # Check 2: All sections evaluated
        drafts = [s for s in sections if s.status == SectionStatus.DRAFT]
        checks.append(ReadinessCheck(
            id="all_evaluated",
            category="Quality",
            title="All sections evaluated",
            description="Run AI evaluation on all sections",
            passed=len(drafts) == 0,
            details=f"{len(drafts)} sections need evaluation" if drafts else None,
            blocking=False
        ))

        # Check 3: All sections above threshold
        below_threshold = [s for s in sections if s.score and s.score < 3.0]
        checks.append(ReadinessCheck(
            id="above_threshold",
            category="Quality",
            title="All sections above funding threshold",
            description="Every section should score at least 3.0/5",
            passed=len(below_threshold) == 0,
            details=f"{len(below_threshold)} sections below 3.0" if below_threshold else None,
            blocking=True
        ))

        # Check 4: Average score competitive
        scored_sections = [s for s in sections if s.score]
        avg_score = sum(s.score for s in scored_sections) / len(scored_sections) if scored_sections else 0
        checks.append(ReadinessCheck(
            id="competitive_score",
            category="Quality",
            title="Average score is competitive",
            description="Overall average should be at least 3.5/5",
            passed=avg_score >= 3.5,
            details=f"Current average: {avg_score:.1f}/5" if avg_score < 3.5 else None,
            blocking=False
        ))

        # Check 5: Critical gaps resolved
        total_gaps = sum(s.gap_count for s in sections)
        checks.append(ReadinessCheck(
            id="gaps_resolved",
            category="Quality",
            title="No critical gaps remaining",
            description="All high-impact gaps should be addressed",
            passed=total_gaps == 0,
            details=f"{total_gaps} gaps remaining" if total_gaps else None,
            blocking=False
        ))

        # Check 6: Word count reasonable
        total_words = sum(s.word_count for s in sections)
        checks.append(ReadinessCheck(
            id="word_count",
            category="Format",
            title="Word count within limits",
            description="Total content should be 5,000-15,000 words",
            passed=5000 <= total_words <= 15000,
            details=f"Current: {total_words} words" if not (5000 <= total_words <= 15000) else None,
            blocking=False
        ))

        # Check 7: Budget section complete (if exists)
        budget_section = next((s for s in sections if 'budget' in s.section_type.lower()), None)
        if budget_section:
            checks.append(ReadinessCheck(
                id="budget_complete",
                category="Content",
                title="Budget section complete",
                description="Budget breakdown is filled in",
                passed=budget_section.word_count >= 200,
                details="Budget section needs more detail" if budget_section.word_count < 200 else None,
                blocking=True
            ))

        # Check 8: Consortium section complete (if exists)
        consortium_section = next((s for s in sections if 'consortium' in s.section_type.lower()), None)
        if consortium_section:
            checks.append(ReadinessCheck(
                id="consortium_complete",
                category="Content",
                title="Consortium section complete",
                description="Partner descriptions are included",
                passed=consortium_section.word_count >= 500,
                details="Need more consortium detail" if consortium_section.word_count < 500 else None,
                blocking=True
            ))

        return checks

    def _calculate_readiness_score(self, checks: List[ReadinessCheck]) -> float:
        """Calculate overall readiness score (0-100)."""
        if not checks:
            return 0.0

        # Weight blocking checks more heavily
        total_weight = 0.0
        earned_weight = 0.0

        for check in checks:
            weight = 2.0 if check.blocking else 1.0
            total_weight += weight
            if check.passed:
                earned_weight += weight

        return (earned_weight / total_weight) * 100 if total_weight > 0 else 0.0

    def _estimate_funding_probability(
        self,
        average_score: Optional[float],
        readiness_score: float
    ) -> Optional[float]:
        """Estimate funding probability based on score and readiness."""
        if average_score is None:
            return None

        # Base probability from score
        # 3.0 -> ~20%, 4.0 -> ~50%, 4.5 -> ~70%, 5.0 -> ~90%
        if average_score < 3.0:
            base_prob = 0.05
        elif average_score < 3.5:
            base_prob = 0.15 + (average_score - 3.0) * 0.2
        elif average_score < 4.0:
            base_prob = 0.25 + (average_score - 3.5) * 0.4
        elif average_score < 4.5:
            base_prob = 0.45 + (average_score - 4.0) * 0.4
        else:
            base_prob = 0.65 + (average_score - 4.5) * 0.5

        # Adjust for readiness
        readiness_factor = readiness_score / 100

        return min(0.95, base_prob * readiness_factor)

    async def get_quick_summary(self, proposal_id: str) -> Dict[str, Any]:
        """Get a quick summary (lighter than full dashboard)."""
        sections = await self._get_section_summaries(proposal_id)
        proposal = self._proposal_cache.get(proposal_id, {})

        scored_sections = [s for s in sections if s.score]
        avg_score = sum(s.score for s in scored_sections) / len(scored_sections) if scored_sections else None
        above_threshold = len([s for s in sections if s.score and s.score >= 3.0])

        return {
            "title": proposal.get('title', 'Untitled Proposal'),
            "sections": {
                "total": len(sections),
                "evaluated": len(scored_sections),
                "above_threshold": above_threshold
            },
            "average_score": avg_score,
            "completion": (above_threshold / len(sections) * 100) if sections else 0
        }
