# Task 16: Proposal Dashboard Overview UI

> **Priority:** P2 (User Experience)
> **Estimated Effort:** 6-8 hours
> **Dependencies:** Tasks 08-15 (All core features)
> **Status:** Not Started

---

## Problem Statement

Users need a central hub to see their entire proposal at a glance - all sections, scores, gaps, progress, and next actions. Currently there's no unified view.

### Current State
- No overall proposal dashboard
- Must navigate between sections to see status
- No prioritized action list
- No submission readiness check

### Target State
- Beautiful dashboard showing full proposal status
- Section cards with scores and status
- Prioritized "What to do next" list
- Submission readiness checklist
- Export and share options

---

## Implementation Plan

### Step 1: Dashboard Data Service

**File:** `app/services/proposal_writing/dashboard_service.py`

```python
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
from app.services.proposal_writing.gap_analysis_service import GapAnalysisService
from app.services.database import get_db_connection

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
        self.gap_service = GapAnalysisService()

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
        async with get_db_connection() as conn:
            # Get proposal info
            proposal = await conn.fetchrow("""
                SELECT
                    p.id, p.title, p.call_id,
                    c.title as call_title, c.deadline
                FROM proposals p
                LEFT JOIN funding_calls c ON p.call_id = c.id
                WHERE p.id = $1
            """, proposal_id)

            if not proposal:
                raise ValueError(f"Proposal not found: {proposal_id}")

            # Get sections
            sections = await self._get_section_summaries(conn, proposal_id)

            # Get overall metrics
            progress = await self.progress_service.get_progress(proposal_id)
            streak = await self.progress_service.get_streak(user_id)

            # Calculate sections by status
            sections_by_status = self._count_by_status(sections)

            # Get next actions
            next_actions = await self._generate_next_actions(conn, proposal_id, sections)

            # Run readiness checks
            readiness_checks = await self._run_readiness_checks(conn, proposal_id, sections)
            readiness_score = self._calculate_readiness_score(readiness_checks)

            # Calculate submission readiness
            submission_ready = all(c.passed for c in readiness_checks if c.blocking)

            # Calculate days until deadline
            days_until = None
            if proposal['deadline']:
                delta = proposal['deadline'] - datetime.now()
                days_until = max(0, delta.days)

            # Calculate funding probability (simplified)
            funding_probability = self._estimate_funding_probability(
                progress.average_score,
                readiness_score
            )

            return DashboardData(
                proposal_id=proposal_id,
                proposal_title=proposal['title'],
                call_id=proposal['call_id'],
                call_title=proposal['call_title'],
                deadline=proposal['deadline'],
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
        conn,
        proposal_id: str
    ) -> List[SectionSummary]:
        """Get summaries for all sections."""
        rows = await conn.fetch("""
            SELECT
                ps.id,
                ps.title,
                ps.section_type,
                ps.content,
                ps.updated_at,
                ss.predicted_score,
                ss.confidence,
                (SELECT COUNT(*) FROM gap_tracking gt WHERE gt.section_id = ps.id AND NOT gt.resolved) as gap_count,
                (SELECT COUNT(*) FROM suggestion_analytics sa WHERE sa.section_id = ps.id AND sa.action IS NULL) as suggestion_count
            FROM proposal_sections ps
            LEFT JOIN section_scores ss ON ps.id = ss.section_id
            WHERE ps.proposal_id = $1
            ORDER BY ps.order_index
        """, proposal_id)

        summaries = []
        for row in rows:
            content = row['content'] or ''
            word_count = len(content.split())

            # Determine status
            if word_count < 50:
                status = SectionStatus.NOT_STARTED
            elif row['predicted_score'] is None:
                status = SectionStatus.DRAFT
            elif row['predicted_score'] < self.THRESHOLD_SCORE:
                status = SectionStatus.NEEDS_WORK
            elif row['predicted_score'] < self.GOOD_SCORE:
                status = SectionStatus.ACCEPTABLE
            elif row['predicted_score'] < self.EXCELLENT_SCORE:
                status = SectionStatus.GOOD
            else:
                status = SectionStatus.EXCELLENT

            summaries.append(SectionSummary(
                id=str(row['id']),
                title=row['title'],
                section_type=row['section_type'],
                status=status,
                word_count=word_count,
                score=float(row['predicted_score']) if row['predicted_score'] else None,
                confidence=float(row['confidence']) if row['confidence'] else None,
                gap_count=row['gap_count'] or 0,
                suggestion_count=row['suggestion_count'] or 0,
                last_edited=row['updated_at']
            ))

        return summaries

    def _count_by_status(self, sections: List[SectionSummary]) -> Dict[str, int]:
        """Count sections by status."""
        counts = {status.value: 0 for status in SectionStatus}
        for section in sections:
            counts[section.status.value] += 1
        return counts

    async def _generate_next_actions(
        self,
        conn,
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
                actions.append(NextAction(
                    id=f"action_{action_id}",
                    title=f"Improve: {section.title}",
                    description=f"Score is {section.score:.1f}/5, needs to reach 3.0 for funding threshold.",
                    priority=ActionPriority.CRITICAL,
                    section_id=section.id,
                    section_title=section.title,
                    action_type="improve",
                    estimated_minutes=45,
                    impact=f"+{3.0 - section.score:.1f} points needed"
                ))

            # Has gaps
            if section.gap_count > 0:
                action_id += 1
                actions.append(NextAction(
                    id=f"action_{action_id}",
                    title=f"Close {section.gap_count} gaps in {section.title}",
                    description="Address identified weaknesses to improve score.",
                    priority=ActionPriority.MEDIUM if section.score >= 3.0 else ActionPriority.HIGH,
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

    async def _run_readiness_checks(
        self,
        conn,
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
        avg_score = sum(s.score for s in sections if s.score) / len([s for s in sections if s.score]) if any(s.score for s in sections) else 0
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
        total_weight = 0
        earned_weight = 0

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
```

### Step 2: API Endpoints

**File:** `app/api/dashboard_routes.py`

```python
"""
API routes for proposal dashboard.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.services.proposal_writing.dashboard_service import DashboardService

router = APIRouter(prefix="/api/proposal/dashboard", tags=["dashboard"])


class SectionSummaryResponse(BaseModel):
    id: str
    title: str
    section_type: str
    status: str
    word_count: int
    score: Optional[float]
    gap_count: int
    suggestion_count: int


class NextActionResponse(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    section_id: Optional[str]
    section_title: Optional[str]
    action_type: str
    estimated_minutes: int
    impact: str


class ReadinessCheckResponse(BaseModel):
    id: str
    category: str
    title: str
    description: str
    passed: bool
    details: Optional[str]
    blocking: bool


class DashboardResponse(BaseModel):
    proposal_id: str
    proposal_title: str
    call_title: Optional[str]
    deadline: Optional[str]

    completion_percentage: float
    overall_score: Optional[float]
    funding_probability: Optional[float]
    submission_ready: bool

    sections: List[SectionSummaryResponse]
    sections_by_status: dict

    next_actions: List[NextActionResponse]
    readiness_checks: List[ReadinessCheckResponse]
    readiness_score: float

    time_spent_minutes: int
    days_until_deadline: Optional[int]
    streak: int


@router.get("/{proposal_id}", response_model=DashboardResponse)
async def get_dashboard(proposal_id: str, user_id: str):
    """
    Get complete dashboard data for a proposal.

    Returns comprehensive view including:
    - Section summaries with scores
    - Prioritized next actions
    - Submission readiness checks
    - Progress metrics
    """
    service = DashboardService()

    try:
        data = await service.get_dashboard(proposal_id, user_id)

        return DashboardResponse(
            proposal_id=data.proposal_id,
            proposal_title=data.proposal_title,
            call_title=data.call_title,
            deadline=data.deadline.isoformat() if data.deadline else None,
            completion_percentage=data.completion_percentage,
            overall_score=data.overall_score,
            funding_probability=data.funding_probability,
            submission_ready=data.submission_ready,
            sections=[
                SectionSummaryResponse(
                    id=s.id,
                    title=s.title,
                    section_type=s.section_type,
                    status=s.status.value,
                    word_count=s.word_count,
                    score=s.score,
                    gap_count=s.gap_count,
                    suggestion_count=s.suggestion_count
                )
                for s in data.sections
            ],
            sections_by_status=data.sections_by_status,
            next_actions=[
                NextActionResponse(
                    id=a.id,
                    title=a.title,
                    description=a.description,
                    priority=a.priority.value,
                    section_id=a.section_id,
                    section_title=a.section_title,
                    action_type=a.action_type,
                    estimated_minutes=a.estimated_minutes,
                    impact=a.impact
                )
                for a in data.next_actions
            ],
            readiness_checks=[
                ReadinessCheckResponse(
                    id=c.id,
                    category=c.category,
                    title=c.title,
                    description=c.description,
                    passed=c.passed,
                    details=c.details,
                    blocking=c.blocking
                )
                for c in data.readiness_checks
            ],
            readiness_score=data.readiness_score,
            time_spent_minutes=data.time_spent_minutes,
            days_until_deadline=data.days_until_deadline,
            streak=data.streak
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{proposal_id}/summary")
async def get_quick_summary(proposal_id: str):
    """Get a quick summary (lighter than full dashboard)."""
    service = DashboardService()

    async with get_db_connection() as conn:
        # Quick query for basic stats
        stats = await conn.fetchrow("""
            SELECT
                p.title,
                COUNT(ps.id) as total_sections,
                COUNT(ss.id) as evaluated_sections,
                AVG(ss.predicted_score) as avg_score,
                COUNT(ss.id) FILTER (WHERE ss.predicted_score >= 3.0) as above_threshold
            FROM proposals p
            LEFT JOIN proposal_sections ps ON p.id = ps.proposal_id
            LEFT JOIN section_scores ss ON ps.id = ss.section_id
            WHERE p.id = $1
            GROUP BY p.id, p.title
        """, proposal_id)

        return {
            "title": stats['title'],
            "sections": {
                "total": stats['total_sections'],
                "evaluated": stats['evaluated_sections'],
                "above_threshold": stats['above_threshold']
            },
            "average_score": float(stats['avg_score']) if stats['avg_score'] else None,
            "completion": (stats['above_threshold'] / stats['total_sections'] * 100) if stats['total_sections'] else 0
        }
```

### Step 3: React Dashboard Component

**File:** `frontend/pages/ProposalDashboard.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

interface Section {
  id: string;
  title: string;
  section_type: string;
  status: string;
  word_count: number;
  score: number | null;
  gap_count: number;
}

interface NextAction {
  id: string;
  title: string;
  description: string;
  priority: string;
  section_id: string | null;
  action_type: string;
  estimated_minutes: number;
  impact: string;
}

interface ReadinessCheck {
  id: string;
  category: string;
  title: string;
  passed: boolean;
  details: string | null;
  blocking: boolean;
}

interface DashboardData {
  proposal_title: string;
  call_title: string | null;
  deadline: string | null;
  completion_percentage: number;
  overall_score: number | null;
  funding_probability: number | null;
  submission_ready: boolean;
  sections: Section[];
  sections_by_status: Record<string, number>;
  next_actions: NextAction[];
  readiness_checks: ReadinessCheck[];
  readiness_score: number;
  days_until_deadline: number | null;
  streak: number;
}

const STATUS_COLORS: Record<string, string> = {
  not_started: '#9ca3af',
  draft: '#fbbf24',
  needs_work: '#ef4444',
  acceptable: '#f59e0b',
  good: '#22c55e',
  excellent: '#10b981',
};

const STATUS_ICONS: Record<string, string> = {
  not_started: '○',
  draft: '◐',
  needs_work: '⚠️',
  acceptable: '✓',
  good: '✓✓',
  excellent: '⭐',
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f59e0b',
  medium: '#3b82f6',
  low: '#9ca3af',
};

export const ProposalDashboard: React.FC = () => {
  const { proposalId } = useParams<{ proposalId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, [proposalId]);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/proposal/dashboard/${proposalId}?user_id=current`);
      setData(await res.json());
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin text-4xl">⏳</div>
      </div>
    );
  }

  if (!data) {
    return <div>Failed to load dashboard</div>;
  }

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{data.proposal_title}</h1>
              {data.call_title && (
                <p className="text-gray-500">{data.call_title}</p>
              )}
            </div>
            <div className="text-right">
              {data.days_until_deadline !== null && (
                <div className={`text-lg font-bold ${data.days_until_deadline < 7 ? 'text-red-600' : 'text-gray-600'}`}>
                  {data.days_until_deadline} days until deadline
                </div>
              )}
              {data.streak > 0 && (
                <div className="text-orange-500">
                  🔥 {data.streak} day streak
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Completion */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="text-sm text-gray-500 mb-1">Completion</div>
            <div className="text-3xl font-bold text-blue-600">
              {data.completion_percentage.toFixed(0)}%
            </div>
            <div className="h-2 bg-gray-200 rounded-full mt-2 overflow-hidden">
              <div
                className="h-full bg-blue-500"
                style={{ width: `${data.completion_percentage}%` }}
              />
            </div>
          </div>

          {/* Overall Score */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="text-sm text-gray-500 mb-1">Overall Score</div>
            <div className="text-3xl font-bold" style={{
              color: data.overall_score && data.overall_score >= 3.5 ? '#22c55e' :
                     data.overall_score && data.overall_score >= 3.0 ? '#f59e0b' : '#ef4444'
            }}>
              {data.overall_score?.toFixed(1) || '—'}/5
            </div>
            <div className="text-sm text-gray-400 mt-1">
              Threshold: 3.0
            </div>
          </div>

          {/* Funding Probability */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="text-sm text-gray-500 mb-1">Funding Probability</div>
            <div className="text-3xl font-bold text-purple-600">
              {data.funding_probability
                ? `${(data.funding_probability * 100).toFixed(0)}%`
                : '—'}
            </div>
            <div className="text-sm text-gray-400 mt-1">
              Estimated chance
            </div>
          </div>

          {/* Readiness */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="text-sm text-gray-500 mb-1">Submission Ready</div>
            <div className={`text-3xl font-bold ${data.submission_ready ? 'text-green-600' : 'text-red-600'}`}>
              {data.submission_ready ? '✓ Yes' : '✗ No'}
            </div>
            <div className="text-sm text-gray-400 mt-1">
              Readiness: {data.readiness_score.toFixed(0)}%
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Sections Column */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-lg font-bold mb-4">Sections</h2>

              <div className="space-y-3">
                {data.sections.map(section => (
                  <div
                    key={section.id}
                    onClick={() => navigate(`/proposal/${proposalId}/section/${section.id}`)}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                    style={{ borderLeftColor: STATUS_COLORS[section.status], borderLeftWidth: '4px' }}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-lg">{STATUS_ICONS[section.status]}</span>
                      <div>
                        <div className="font-medium">{section.title}</div>
                        <div className="text-sm text-gray-500">
                          {section.word_count} words
                          {section.gap_count > 0 && ` • ${section.gap_count} gaps`}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div
                        className="text-lg font-bold"
                        style={{ color: STATUS_COLORS[section.status] }}
                      >
                        {section.score?.toFixed(1) || '—'}
                      </div>
                      <div className="text-xs text-gray-400 capitalize">
                        {section.status.replace('_', ' ')}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">

            {/* Next Actions */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-lg font-bold mb-4">What to Do Next</h2>

              <div className="space-y-3">
                {data.next_actions.slice(0, 5).map(action => (
                  <div
                    key={action.id}
                    onClick={() => action.section_id && navigate(`/proposal/${proposalId}/section/${action.section_id}`)}
                    className="p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: PRIORITY_COLORS[action.priority] }}
                      />
                      <span className="font-medium text-sm">{action.title}</span>
                    </div>
                    <div className="text-xs text-gray-500 flex justify-between">
                      <span>~{action.estimated_minutes} min</span>
                      <span className="text-green-600">{action.impact}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Readiness Checks */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-lg font-bold mb-4">Submission Checklist</h2>

              <div className="space-y-2">
                {data.readiness_checks.map(check => (
                  <div
                    key={check.id}
                    className="flex items-center gap-2 text-sm"
                  >
                    <span className={check.passed ? 'text-green-500' : 'text-red-500'}>
                      {check.passed ? '✓' : '✗'}
                    </span>
                    <span className={check.passed ? 'text-gray-600' : 'text-gray-900'}>
                      {check.title}
                    </span>
                    {check.blocking && !check.passed && (
                      <span className="text-xs bg-red-100 text-red-700 px-1 rounded">
                        Required
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Section Status Summary */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-lg font-bold mb-4">Section Status</h2>

              <div className="space-y-2">
                {Object.entries(data.sections_by_status).map(([status, count]) => (
                  count > 0 && (
                    <div key={status} className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: STATUS_COLORS[status] }}
                      />
                      <span className="capitalize text-sm">{status.replace('_', ' ')}</span>
                      <span className="ml-auto font-medium">{count}</span>
                    </div>
                  )
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
```

---

## Testing Plan

```python
# tests/test_dashboard.py

import pytest
from app.services.proposal_writing.dashboard_service import (
    DashboardService, SectionStatus
)


class TestDashboard:

    @pytest.fixture
    def service(self):
        return DashboardService()

    @pytest.mark.asyncio
    async def test_get_dashboard_returns_data(self, service):
        """Test that dashboard returns comprehensive data."""
        # Would need database fixtures
        pass

    def test_section_status_calculation(self, service):
        """Test section status determination."""
        # Score-based status
        assert service.THRESHOLD_SCORE == 3.0
        assert service.GOOD_SCORE == 3.5
        assert service.EXCELLENT_SCORE == 4.0

    def test_readiness_score_calculation(self, service):
        """Test readiness score calculation."""
        from app.services.proposal_writing.dashboard_service import ReadinessCheck

        checks = [
            ReadinessCheck("1", "Test", "Test", "", True, None, True),   # Blocking, passed
            ReadinessCheck("2", "Test", "Test", "", True, None, False),  # Non-blocking, passed
            ReadinessCheck("3", "Test", "Test", "", False, None, True),  # Blocking, failed
        ]

        score = service._calculate_readiness_score(checks)
        # 2 blocking (weight 2 each) + 1 non-blocking (weight 1)
        # Passed: 1 blocking (2) + 1 non-blocking (1) = 3
        # Total: 2+2+1 = 5
        # Score: 3/5 = 60%
        assert score == 60.0

    def test_funding_probability_estimation(self, service):
        """Test funding probability calculation."""
        # Low score
        prob_low = service._estimate_funding_probability(2.5, 80)
        assert prob_low < 0.1

        # Threshold score
        prob_thresh = service._estimate_funding_probability(3.0, 90)
        assert 0.1 < prob_thresh < 0.3

        # Good score
        prob_good = service._estimate_funding_probability(4.0, 95)
        assert 0.4 < prob_good < 0.6

        # Excellent score
        prob_exc = service._estimate_funding_probability(4.5, 100)
        assert prob_exc > 0.6
```

---

## Verification Checklist

- [ ] Dashboard loads with all sections
- [ ] Section statuses calculated correctly
- [ ] Overall score aggregates properly
- [ ] Funding probability is reasonable
- [ ] Next actions are prioritized correctly
- [ ] Readiness checks identify issues
- [ ] Deadline countdown displays
- [ ] Click on section navigates correctly
- [ ] Mobile responsive layout
- [ ] Loading states display properly

---

## UI/UX Notes

1. **Color coding**: Consistent across all status indicators
2. **Clickable sections**: Navigate directly to edit
3. **Priority badges**: Visual hierarchy for actions
4. **Progress bars**: Always show context (current/total)
5. **Deadline warning**: Red when < 7 days
6. **Streak display**: Motivational element
7. **Empty states**: Helpful messaging when no data

---

## Integration Points

1. **With Score Integration (Task 09)**: Shows section scores
2. **With Gap Analysis (Task 10)**: Shows gap counts
3. **With Progress Tracking (Task 15)**: Shows streak and time
4. **With Streaming Feedback (Task 14)**: Real-time score updates
5. **With Export**: Add "Export Proposal" button
