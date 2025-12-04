# Task 10: Gap Analysis - Path to Threshold

> **Priority:** P1 (Core Value)
> **Estimated Effort:** 3-4 hours
> **Dependencies:** Task 08 (Evaluator Simulator), Task 09 (Score Integration)
> **Status:** Not Started

---

## Problem Statement

Users know their predicted score but don't understand:
1. What specific gaps are preventing a higher score
2. What exact changes would move them from 3.2 to 4.0
3. How much effort each gap requires to close
4. Which gaps have the highest impact on score

### Current State
- Evaluator gives a score and general comments
- No prioritized action plan
- No quantified gap analysis
- No path to improvement

### Target State
- Clear list of gaps with estimated score impact
- Prioritized action items with effort estimates
- Specific recommendations with examples
- Progress tracking as gaps are closed

---

## Implementation Plan

### Step 1: Create Gap Analysis Service

**File:** `app/services/proposal_writing/gap_analysis_service.py`

```python
"""
Gap Analysis Service

Analyzes the gap between current score and target score,
providing a prioritized roadmap to reach funding threshold.
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from app.services.proposal_writing.proposal_ai_service import ProposalAIService
from app.services.proposal_writing.evaluator_simulator import EvaluatorSimulator
from app.services.database import get_db_connection

logger = logging.getLogger(__name__)


class GapSeverity(str, Enum):
    """Severity level of a gap."""
    CRITICAL = "critical"      # Must fix to reach threshold
    MAJOR = "major"            # Significant impact on score
    MINOR = "minor"            # Nice to fix, small impact
    POLISH = "polish"          # Final touches


class GapCategory(str, Enum):
    """Category of gap."""
    CONTENT_MISSING = "content_missing"       # Required content not present
    CONTENT_WEAK = "content_weak"             # Content exists but insufficient
    STRUCTURE = "structure"                    # Organization/flow issues
    SPECIFICITY = "specificity"               # Too vague or generic
    EU_ALIGNMENT = "eu_alignment"             # Missing EU priorities/terminology
    QUANTIFICATION = "quantification"         # Missing metrics/KPIs
    METHODOLOGY = "methodology"               # Approach not clear
    INNOVATION = "innovation"                 # Beyond state-of-art not established


class EffortLevel(str, Enum):
    """Estimated effort to close gap."""
    QUICK = "quick"           # < 30 minutes
    MODERATE = "moderate"     # 30 min - 2 hours
    SUBSTANTIAL = "substantial"  # 2-4 hours
    MAJOR = "major"           # > 4 hours


@dataclass
class Gap:
    """A single identified gap."""
    id: str
    category: GapCategory
    severity: GapSeverity
    title: str
    description: str
    current_state: str
    target_state: str
    estimated_score_impact: float  # How many points this gap costs
    effort: EffortLevel
    specific_action: str
    example_text: Optional[str] = None
    related_criterion: Optional[str] = None
    is_resolved: bool = False


@dataclass
class GapAnalysisResult:
    """Complete gap analysis for a section."""
    section_id: str
    section_type: str
    current_score: float
    target_score: float
    score_gap: float
    gaps: List[Gap]
    critical_count: int
    total_estimated_impact: float
    recommended_priority_order: List[str]  # Gap IDs in order
    estimated_total_effort: str
    achievable_score: float  # Score if all gaps closed


class GapAnalysisService:
    """
    Service for analyzing gaps between current and target scores.

    Identifies specific improvements needed and prioritizes them
    by impact and effort for efficient score improvement.
    """

    # Target scores
    THRESHOLD_SCORE = 3.0
    COMPETITIVE_SCORE = 4.0
    EXCELLENT_SCORE = 4.5

    def __init__(self):
        self.ai_service = ProposalAIService()
        self.evaluator = EvaluatorSimulator()

    async def analyze_gaps(
        self,
        content: str,
        section_type: str,
        current_score: float,
        target_score: Optional[float] = None,
        evaluation_result: Optional[Dict] = None,
        cluster: Optional[str] = None
    ) -> GapAnalysisResult:
        """
        Analyze gaps between current content and target score.

        Args:
            content: Current section content
            section_type: Type of section
            current_score: Current predicted score
            target_score: Target score (default: COMPETITIVE_SCORE)
            evaluation_result: Previous evaluation (to avoid re-evaluating)
            cluster: HE cluster for context

        Returns:
            Detailed gap analysis with prioritized actions
        """
        if target_score is None:
            # Set target based on current score
            if current_score < self.THRESHOLD_SCORE:
                target_score = self.THRESHOLD_SCORE
            elif current_score < self.COMPETITIVE_SCORE:
                target_score = self.COMPETITIVE_SCORE
            else:
                target_score = self.EXCELLENT_SCORE

        score_gap = target_score - current_score

        logger.info(f"Analyzing gaps: current={current_score}, target={target_score}, gap={score_gap}")

        # Get evaluation if not provided
        if evaluation_result is None:
            eval_result = await self.evaluator.simulate_evaluation(
                content=content,
                section_type=section_type,
                cluster=cluster
            )
            evaluation_result = eval_result.__dict__

        # Identify gaps using LLM analysis
        gaps = await self._identify_gaps(
            content=content,
            section_type=section_type,
            current_score=current_score,
            target_score=target_score,
            weaknesses=evaluation_result.get('weaknesses', []),
            cluster=cluster
        )

        # Calculate metrics
        critical_count = sum(1 for g in gaps if g.severity == GapSeverity.CRITICAL)
        total_impact = sum(g.estimated_score_impact for g in gaps)

        # Prioritize gaps
        priority_order = self._prioritize_gaps(gaps)

        # Estimate total effort
        total_effort = self._estimate_total_effort(gaps)

        # Calculate achievable score
        achievable = min(5.0, current_score + total_impact)

        return GapAnalysisResult(
            section_id="",  # To be set by caller
            section_type=section_type,
            current_score=current_score,
            target_score=target_score,
            score_gap=score_gap,
            gaps=gaps,
            critical_count=critical_count,
            total_estimated_impact=total_impact,
            recommended_priority_order=priority_order,
            estimated_total_effort=total_effort,
            achievable_score=achievable
        )

    async def _identify_gaps(
        self,
        content: str,
        section_type: str,
        current_score: float,
        target_score: float,
        weaknesses: List[str],
        cluster: Optional[str]
    ) -> List[Gap]:
        """Identify specific gaps using LLM analysis."""

        prompt = f"""Analyze this proposal section and identify specific gaps preventing a higher score.

SECTION TYPE: {section_type}
CURRENT SCORE: {current_score}/5
TARGET SCORE: {target_score}/5
CLUSTER: {cluster or 'General'}

CONTENT:
{content[:3000]}

KNOWN WEAKNESSES:
{weaknesses}

Identify 3-6 specific gaps. For each gap, provide:
1. Category (content_missing, content_weak, structure, specificity, eu_alignment, quantification, methodology, innovation)
2. Severity (critical, major, minor, polish)
3. Title (short, specific)
4. Description (what's wrong)
5. Current state (what the text has now)
6. Target state (what it should have)
7. Estimated score impact (0.1 to 1.0 points)
8. Effort level (quick, moderate, substantial, major)
9. Specific action to take
10. Example text showing the improvement

Respond with JSON:
{{
    "gaps": [
        {{
            "category": "specificity",
            "severity": "major",
            "title": "Objectives lack measurable targets",
            "description": "The objectives are stated but without quantifiable success criteria",
            "current_state": "We aim to improve energy efficiency",
            "target_state": "We aim to improve energy efficiency by 30% as measured by...",
            "estimated_score_impact": 0.4,
            "effort": "moderate",
            "specific_action": "Add specific KPIs and metrics for each objective",
            "example_text": "Our primary objective is to achieve a 30% reduction in energy consumption, measured through real-time monitoring of 50 pilot buildings over 24 months.",
            "related_criterion": "excellence"
        }}
    ]
}}

Focus on the most impactful gaps first. Be specific and actionable."""

        response = await self.ai_service.generate_structured(
            prompt=prompt,
            schema_name="gap_analysis"
        )

        gaps = []
        for i, gap_data in enumerate(response.get('gaps', [])):
            try:
                gap = Gap(
                    id=f"gap_{i+1}",
                    category=GapCategory(gap_data['category']),
                    severity=GapSeverity(gap_data['severity']),
                    title=gap_data['title'],
                    description=gap_data['description'],
                    current_state=gap_data['current_state'],
                    target_state=gap_data['target_state'],
                    estimated_score_impact=gap_data['estimated_score_impact'],
                    effort=EffortLevel(gap_data['effort']),
                    specific_action=gap_data['specific_action'],
                    example_text=gap_data.get('example_text'),
                    related_criterion=gap_data.get('related_criterion')
                )
                gaps.append(gap)
            except (KeyError, ValueError) as e:
                logger.warning(f"Error parsing gap: {e}")
                continue

        return gaps

    def _prioritize_gaps(self, gaps: List[Gap]) -> List[str]:
        """
        Prioritize gaps by impact-to-effort ratio.

        Priority formula: (score_impact * severity_weight) / effort_weight
        """
        severity_weights = {
            GapSeverity.CRITICAL: 2.0,
            GapSeverity.MAJOR: 1.5,
            GapSeverity.MINOR: 1.0,
            GapSeverity.POLISH: 0.5
        }

        effort_weights = {
            EffortLevel.QUICK: 1.0,
            EffortLevel.MODERATE: 2.0,
            EffortLevel.SUBSTANTIAL: 4.0,
            EffortLevel.MAJOR: 8.0
        }

        def priority_score(gap: Gap) -> float:
            impact = gap.estimated_score_impact * severity_weights[gap.severity]
            effort = effort_weights[gap.effort]
            return impact / effort

        sorted_gaps = sorted(gaps, key=priority_score, reverse=True)
        return [g.id for g in sorted_gaps]

    def _estimate_total_effort(self, gaps: List[Gap]) -> str:
        """Estimate total effort to close all gaps."""
        effort_minutes = {
            EffortLevel.QUICK: 20,
            EffortLevel.MODERATE: 75,
            EffortLevel.SUBSTANTIAL: 180,
            EffortLevel.MAJOR: 360
        }

        total_minutes = sum(effort_minutes[g.effort] for g in gaps)

        if total_minutes < 60:
            return f"{total_minutes} minutes"
        elif total_minutes < 240:
            return f"{total_minutes // 60} hours"
        else:
            return f"{total_minutes // 60} hours ({total_minutes // 480} work days)"

    async def get_gap_closure_suggestion(
        self,
        gap: Gap,
        content: str,
        section_type: str
    ) -> Dict[str, Any]:
        """
        Get detailed suggestion for closing a specific gap.

        Returns rewritten text and explanation.
        """
        prompt = f"""Help close this gap in a proposal section.

GAP TO CLOSE:
- Title: {gap.title}
- Description: {gap.description}
- Current state: {gap.current_state}
- Target state: {gap.target_state}
- Action needed: {gap.specific_action}

FULL SECTION CONTENT:
{content[:2000]}

Provide a specific rewrite that closes this gap. Respond with JSON:
{{
    "rewritten_text": "The specific paragraph or section that should be changed, fully rewritten",
    "explanation": "Brief explanation of what was changed and why",
    "before_snippet": "The original text being replaced (exact match)",
    "after_snippet": "The new text to replace it with",
    "estimated_new_score_impact": 0.3,
    "additional_tips": ["tip1", "tip2"]
}}"""

        response = await self.ai_service.generate_structured(
            prompt=prompt,
            schema_name="gap_closure"
        )

        return response

    async def track_gap_progress(
        self,
        section_id: str,
        gap_id: str,
        resolved: bool
    ) -> None:
        """Track when a gap is resolved."""
        async with get_db_connection() as conn:
            await conn.execute("""
                INSERT INTO gap_tracking (section_id, gap_id, resolved, resolved_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (section_id, gap_id)
                DO UPDATE SET resolved = $3, resolved_at = NOW()
            """, section_id, gap_id, resolved)


class GapProgressTracker:
    """
    Tracks progress on closing gaps over time.

    Provides statistics and visualizations of improvement journey.
    """

    async def get_section_progress(self, section_id: str) -> Dict[str, Any]:
        """Get gap closure progress for a section."""
        async with get_db_connection() as conn:
            # Get gap tracking data
            tracking = await conn.fetch("""
                SELECT gap_id, resolved, resolved_at
                FROM gap_tracking
                WHERE section_id = $1
            """, section_id)

            # Get score history
            scores = await conn.fetch("""
                SELECT predicted_score, created_at
                FROM section_score_history
                WHERE section_id = $1
                ORDER BY created_at
            """, section_id)

            total_gaps = len(tracking)
            resolved_gaps = sum(1 for t in tracking if t['resolved'])

            return {
                "total_gaps_identified": total_gaps,
                "gaps_resolved": resolved_gaps,
                "completion_percentage": (resolved_gaps / total_gaps * 100) if total_gaps > 0 else 0,
                "score_history": [
                    {"score": float(s['predicted_score']), "date": s['created_at'].isoformat()}
                    for s in scores
                ],
                "score_improvement": float(scores[-1]['predicted_score'] - scores[0]['predicted_score']) if len(scores) >= 2 else 0
            }

    async def get_proposal_progress(self, proposal_id: str) -> Dict[str, Any]:
        """Get overall gap progress for a proposal."""
        async with get_db_connection() as conn:
            result = await conn.fetchrow("""
                SELECT
                    COUNT(DISTINCT gt.gap_id) as total_gaps,
                    COUNT(DISTINCT gt.gap_id) FILTER (WHERE gt.resolved) as resolved_gaps,
                    AVG(ss.predicted_score) as current_avg_score
                FROM gap_tracking gt
                JOIN section_scores ss ON gt.section_id = ss.section_id
                WHERE ss.proposal_id = $1
            """, proposal_id)

            return {
                "total_gaps": result['total_gaps'] or 0,
                "resolved_gaps": result['resolved_gaps'] or 0,
                "current_avg_score": float(result['current_avg_score']) if result['current_avg_score'] else 0,
                "completion_percentage": (
                    (result['resolved_gaps'] / result['total_gaps'] * 100)
                    if result['total_gaps'] else 0
                )
            }
```

### Step 2: Database Schema for Gap Tracking

**File:** `migration/012_gap_tracking.sql`

```sql
-- Gap tracking schema
-- Tracks identified gaps and their resolution status

CREATE TABLE IF NOT EXISTS gap_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID NOT NULL REFERENCES proposal_sections(id) ON DELETE CASCADE,
    gap_id VARCHAR(50) NOT NULL,

    -- Gap details (snapshot at time of identification)
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title TEXT NOT NULL,
    estimated_impact DECIMAL(2,1),
    effort_level VARCHAR(20),

    -- Status
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,

    -- Metadata
    identified_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(section_id, gap_id)
);

-- Indexes
CREATE INDEX idx_gap_tracking_section ON gap_tracking(section_id);
CREATE INDEX idx_gap_tracking_resolved ON gap_tracking(resolved);
CREATE INDEX idx_gap_tracking_severity ON gap_tracking(severity);

-- View for gap statistics
CREATE OR REPLACE VIEW v_gap_statistics AS
SELECT
    ps.proposal_id,
    ps.id as section_id,
    ps.section_type,
    COUNT(gt.id) as total_gaps,
    COUNT(gt.id) FILTER (WHERE gt.resolved) as resolved_gaps,
    COUNT(gt.id) FILTER (WHERE gt.severity = 'critical') as critical_gaps,
    COUNT(gt.id) FILTER (WHERE gt.severity = 'critical' AND gt.resolved) as critical_resolved,
    SUM(gt.estimated_impact) as total_potential_impact,
    SUM(gt.estimated_impact) FILTER (WHERE gt.resolved) as realized_impact
FROM proposal_sections ps
LEFT JOIN gap_tracking gt ON ps.id = gt.section_id
GROUP BY ps.proposal_id, ps.id, ps.section_type;

-- Function to calculate gap closure rate
CREATE OR REPLACE FUNCTION get_gap_closure_rate(p_proposal_id UUID)
RETURNS DECIMAL AS $$
DECLARE
    total_gaps INT;
    resolved_gaps INT;
BEGIN
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE resolved)
    INTO total_gaps, resolved_gaps
    FROM gap_tracking gt
    JOIN proposal_sections ps ON gt.section_id = ps.id
    WHERE ps.proposal_id = p_proposal_id;

    IF total_gaps = 0 THEN
        RETURN 0;
    END IF;

    RETURN ROUND((resolved_gaps::DECIMAL / total_gaps) * 100, 1);
END;
$$ LANGUAGE plpgsql;
```

### Step 3: API Endpoints

**File:** `app/api/gap_analysis_routes.py`

```python
"""
API routes for gap analysis.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel, Field

from app.services.proposal_writing.gap_analysis_service import (
    GapAnalysisService, GapProgressTracker, Gap
)

router = APIRouter(prefix="/api/proposal/gaps", tags=["gap-analysis"])


class GapAnalysisRequest(BaseModel):
    content: str = Field(..., min_length=100)
    section_type: str
    current_score: float = Field(..., ge=0, le=5)
    target_score: Optional[float] = Field(None, ge=0, le=5)
    cluster: Optional[str] = None


class GapResponse(BaseModel):
    id: str
    category: str
    severity: str
    title: str
    description: str
    current_state: str
    target_state: str
    estimated_score_impact: float
    effort: str
    specific_action: str
    example_text: Optional[str]
    related_criterion: Optional[str]


class GapAnalysisResponse(BaseModel):
    current_score: float
    target_score: float
    score_gap: float
    gaps: List[GapResponse]
    critical_count: int
    total_estimated_impact: float
    recommended_priority_order: List[str]
    estimated_total_effort: str
    achievable_score: float


class GapClosureRequest(BaseModel):
    gap_id: str
    content: str
    section_type: str
    gap_title: str
    gap_description: str
    current_state: str
    target_state: str
    specific_action: str


class GapClosureResponse(BaseModel):
    rewritten_text: str
    explanation: str
    before_snippet: str
    after_snippet: str
    estimated_new_score_impact: float
    additional_tips: List[str]


class ProgressResponse(BaseModel):
    total_gaps_identified: int
    gaps_resolved: int
    completion_percentage: float
    score_improvement: float


@router.post("/analyze", response_model=GapAnalysisResponse)
async def analyze_gaps(request: GapAnalysisRequest):
    """
    Analyze gaps in a proposal section.

    Identifies specific improvements needed to reach the target score,
    prioritized by impact and effort.
    """
    service = GapAnalysisService()

    try:
        result = await service.analyze_gaps(
            content=request.content,
            section_type=request.section_type,
            current_score=request.current_score,
            target_score=request.target_score,
            cluster=request.cluster
        )

        return GapAnalysisResponse(
            current_score=result.current_score,
            target_score=result.target_score,
            score_gap=result.score_gap,
            gaps=[
                GapResponse(
                    id=g.id,
                    category=g.category.value,
                    severity=g.severity.value,
                    title=g.title,
                    description=g.description,
                    current_state=g.current_state,
                    target_state=g.target_state,
                    estimated_score_impact=g.estimated_score_impact,
                    effort=g.effort.value,
                    specific_action=g.specific_action,
                    example_text=g.example_text,
                    related_criterion=g.related_criterion
                )
                for g in result.gaps
            ],
            critical_count=result.critical_count,
            total_estimated_impact=result.total_estimated_impact,
            recommended_priority_order=result.recommended_priority_order,
            estimated_total_effort=result.estimated_total_effort,
            achievable_score=result.achievable_score
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close-gap", response_model=GapClosureResponse)
async def get_gap_closure_suggestion(request: GapClosureRequest):
    """
    Get specific suggestion for closing a gap.

    Returns rewritten text that addresses the identified gap.
    """
    service = GapAnalysisService()

    # Reconstruct gap object
    from app.services.proposal_writing.gap_analysis_service import (
        Gap, GapCategory, GapSeverity, EffortLevel
    )

    gap = Gap(
        id=request.gap_id,
        category=GapCategory.CONTENT_WEAK,  # Default
        severity=GapSeverity.MAJOR,
        title=request.gap_title,
        description=request.gap_description,
        current_state=request.current_state,
        target_state=request.target_state,
        estimated_score_impact=0.3,
        effort=EffortLevel.MODERATE,
        specific_action=request.specific_action
    )

    result = await service.get_gap_closure_suggestion(
        gap=gap,
        content=request.content,
        section_type=request.section_type
    )

    return GapClosureResponse(**result)


@router.post("/section/{section_id}/gap/{gap_id}/resolve")
async def mark_gap_resolved(section_id: str, gap_id: str, resolved: bool = True):
    """Mark a gap as resolved or unresolved."""
    service = GapAnalysisService()

    await service.track_gap_progress(
        section_id=section_id,
        gap_id=gap_id,
        resolved=resolved
    )

    return {"status": "success", "gap_id": gap_id, "resolved": resolved}


@router.get("/section/{section_id}/progress", response_model=ProgressResponse)
async def get_section_gap_progress(section_id: str):
    """Get gap closure progress for a section."""
    tracker = GapProgressTracker()

    result = await tracker.get_section_progress(section_id)

    return ProgressResponse(
        total_gaps_identified=result['total_gaps_identified'],
        gaps_resolved=result['gaps_resolved'],
        completion_percentage=result['completion_percentage'],
        score_improvement=result['score_improvement']
    )


@router.get("/proposal/{proposal_id}/progress", response_model=ProgressResponse)
async def get_proposal_gap_progress(proposal_id: str):
    """Get overall gap progress for a proposal."""
    tracker = GapProgressTracker()

    result = await tracker.get_proposal_progress(proposal_id)

    return ProgressResponse(
        total_gaps_identified=result['total_gaps'],
        gaps_resolved=result['resolved_gaps'],
        completion_percentage=result['completion_percentage'],
        score_improvement=result.get('score_improvement', 0)
    )
```

### Step 4: JSON Schemas for Structured Output

**Add to:** `app/services/proposal_writing/ai_schemas.py`

```python
GAP_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["content_missing", "content_weak", "structure", "specificity",
                                "eu_alignment", "quantification", "methodology", "innovation"]
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "major", "minor", "polish"]
                    },
                    "title": {"type": "string", "maxLength": 100},
                    "description": {"type": "string", "maxLength": 300},
                    "current_state": {"type": "string", "maxLength": 200},
                    "target_state": {"type": "string", "maxLength": 200},
                    "estimated_score_impact": {"type": "number", "minimum": 0.1, "maximum": 1.0},
                    "effort": {
                        "type": "string",
                        "enum": ["quick", "moderate", "substantial", "major"]
                    },
                    "specific_action": {"type": "string", "maxLength": 200},
                    "example_text": {"type": "string", "maxLength": 500},
                    "related_criterion": {"type": "string"}
                },
                "required": ["category", "severity", "title", "description",
                            "current_state", "target_state", "estimated_score_impact",
                            "effort", "specific_action"]
            },
            "minItems": 1,
            "maxItems": 8
        }
    },
    "required": ["gaps"]
}

GAP_CLOSURE_SCHEMA = {
    "type": "object",
    "properties": {
        "rewritten_text": {"type": "string"},
        "explanation": {"type": "string", "maxLength": 300},
        "before_snippet": {"type": "string"},
        "after_snippet": {"type": "string"},
        "estimated_new_score_impact": {"type": "number", "minimum": 0, "maximum": 1},
        "additional_tips": {
            "type": "array",
            "items": {"type": "string", "maxLength": 150},
            "maxItems": 3
        }
    },
    "required": ["rewritten_text", "explanation", "before_snippet", "after_snippet"]
}
```

### Step 5: UI Components (React)

**File:** `frontend/components/GapAnalysis.tsx`

```typescript
import React, { useState } from 'react';

interface Gap {
  id: string;
  category: string;
  severity: 'critical' | 'major' | 'minor' | 'polish';
  title: string;
  description: string;
  current_state: string;
  target_state: string;
  estimated_score_impact: number;
  effort: 'quick' | 'moderate' | 'substantial' | 'major';
  specific_action: string;
  example_text?: string;
}

interface GapAnalysisProps {
  gaps: Gap[];
  currentScore: number;
  targetScore: number;
  achievableScore: number;
  onCloseGap: (gapId: string) => void;
  onApplySuggestion: (gapId: string, suggestion: string) => void;
}

export const GapAnalysis: React.FC<GapAnalysisProps> = ({
  gaps,
  currentScore,
  targetScore,
  achievableScore,
  onCloseGap,
  onApplySuggestion
}) => {
  const [expandedGap, setExpandedGap] = useState<string | null>(null);
  const [resolvedGaps, setResolvedGaps] = useState<Set<string>>(new Set());

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'border-red-500 bg-red-50';
      case 'major': return 'border-orange-500 bg-orange-50';
      case 'minor': return 'border-yellow-500 bg-yellow-50';
      case 'polish': return 'border-blue-500 bg-blue-50';
      default: return 'border-gray-500 bg-gray-50';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return '🚨';
      case 'major': return '⚠️';
      case 'minor': return '💡';
      case 'polish': return '✨';
      default: return '📝';
    }
  };

  const getEffortBadge = (effort: string) => {
    const colors = {
      quick: 'bg-green-100 text-green-800',
      moderate: 'bg-yellow-100 text-yellow-800',
      substantial: 'bg-orange-100 text-orange-800',
      major: 'bg-red-100 text-red-800'
    };
    return colors[effort] || 'bg-gray-100 text-gray-800';
  };

  const handleResolve = (gapId: string) => {
    setResolvedGaps(prev => new Set(prev).add(gapId));
    onCloseGap(gapId);
  };

  return (
    <div className="space-y-4">
      {/* Score Overview */}
      <div className="bg-white rounded-lg p-4 shadow">
        <h3 className="text-lg font-semibold mb-3">Path to Target Score</h3>
        <div className="flex items-center gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-600">{currentScore.toFixed(1)}</div>
            <div className="text-sm text-gray-500">Current</div>
          </div>
          <div className="flex-1 h-2 bg-gray-200 rounded-full relative">
            <div
              className="absolute h-full bg-blue-500 rounded-full"
              style={{ width: `${(currentScore / 5) * 100}%` }}
            />
            <div
              className="absolute h-full w-1 bg-green-500"
              style={{ left: `${(targetScore / 5) * 100}%` }}
            />
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">{targetScore.toFixed(1)}</div>
            <div className="text-sm text-gray-500">Target</div>
          </div>
        </div>
        <div className="mt-2 text-sm text-gray-600">
          Close all gaps to potentially reach <strong>{achievableScore.toFixed(1)}</strong>
        </div>
      </div>

      {/* Gap List */}
      <div className="space-y-3">
        {gaps.map((gap, index) => (
          <div
            key={gap.id}
            className={`border-l-4 rounded-lg p-4 ${getSeverityColor(gap.severity)} ${
              resolvedGaps.has(gap.id) ? 'opacity-50' : ''
            }`}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between cursor-pointer"
              onClick={() => setExpandedGap(expandedGap === gap.id ? null : gap.id)}
            >
              <div className="flex items-center gap-2">
                <span>{getSeverityIcon(gap.severity)}</span>
                <span className="font-medium">{gap.title}</span>
                <span className={`text-xs px-2 py-1 rounded ${getEffortBadge(gap.effort)}`}>
                  {gap.effort}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-green-600">
                  +{gap.estimated_score_impact.toFixed(1)} pts
                </span>
                <span>{expandedGap === gap.id ? '▼' : '▶'}</span>
              </div>
            </div>

            {/* Expanded Content */}
            {expandedGap === gap.id && (
              <div className="mt-4 space-y-3">
                <p className="text-gray-700">{gap.description}</p>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h5 className="text-sm font-medium text-red-700">Current State</h5>
                    <p className="text-sm text-gray-600 italic">"{gap.current_state}"</p>
                  </div>
                  <div>
                    <h5 className="text-sm font-medium text-green-700">Target State</h5>
                    <p className="text-sm text-gray-600 italic">"{gap.target_state}"</p>
                  </div>
                </div>

                <div className="bg-white rounded p-3">
                  <h5 className="text-sm font-medium text-blue-700">Action Required</h5>
                  <p className="text-sm">{gap.specific_action}</p>
                </div>

                {gap.example_text && (
                  <div className="bg-green-50 rounded p-3">
                    <h5 className="text-sm font-medium text-green-700">Example</h5>
                    <p className="text-sm italic">"{gap.example_text}"</p>
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={() => onApplySuggestion(gap.id, gap.example_text || '')}
                    className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                    disabled={resolvedGaps.has(gap.id)}
                  >
                    Apply Suggestion
                  </button>
                  <button
                    onClick={() => handleResolve(gap.id)}
                    className="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600"
                    disabled={resolvedGaps.has(gap.id)}
                  >
                    {resolvedGaps.has(gap.id) ? '✓ Resolved' : 'Mark Resolved'}
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="bg-gray-100 rounded-lg p-4">
        <div className="flex justify-between text-sm">
          <span>Gaps resolved: {resolvedGaps.size}/{gaps.length}</span>
          <span>
            Estimated remaining effort:{' '}
            {gaps.filter(g => !resolvedGaps.has(g.id)).length} items
          </span>
        </div>
      </div>
    </div>
  );
};
```

---

## Testing Plan

```python
# tests/test_gap_analysis.py

import pytest
from app.services.proposal_writing.gap_analysis_service import (
    GapAnalysisService, GapSeverity, EffortLevel
)


class TestGapAnalysis:

    @pytest.fixture
    def service(self):
        return GapAnalysisService()

    @pytest.mark.asyncio
    async def test_analyze_gaps_returns_results(self, service):
        """Test that gap analysis returns valid results."""
        content = """
        Our project aims to improve energy efficiency.
        We will work with partners to develop solutions.
        The impact will be positive for society.
        """

        result = await service.analyze_gaps(
            content=content,
            section_type="excellence_objectives",
            current_score=2.8,
            target_score=4.0
        )

        assert result.current_score == 2.8
        assert result.target_score == 4.0
        assert len(result.gaps) > 0
        assert result.achievable_score > result.current_score

    @pytest.mark.asyncio
    async def test_gap_prioritization(self, service):
        """Test that gaps are prioritized correctly."""
        from app.services.proposal_writing.gap_analysis_service import Gap, GapCategory

        gaps = [
            Gap(
                id="gap_1",
                category=GapCategory.SPECIFICITY,
                severity=GapSeverity.CRITICAL,
                title="Critical quick fix",
                description="",
                current_state="",
                target_state="",
                estimated_score_impact=0.5,
                effort=EffortLevel.QUICK,
                specific_action=""
            ),
            Gap(
                id="gap_2",
                category=GapCategory.METHODOLOGY,
                severity=GapSeverity.MINOR,
                title="Minor major effort",
                description="",
                current_state="",
                target_state="",
                estimated_score_impact=0.2,
                effort=EffortLevel.MAJOR,
                specific_action=""
            )
        ]

        priority = service._prioritize_gaps(gaps)

        # Critical quick fix should be first
        assert priority[0] == "gap_1"

    def test_effort_estimation(self, service):
        """Test total effort calculation."""
        from app.services.proposal_writing.gap_analysis_service import Gap, GapCategory

        gaps = [
            Gap(
                id="1", category=GapCategory.SPECIFICITY,
                severity=GapSeverity.MAJOR, title="", description="",
                current_state="", target_state="",
                estimated_score_impact=0.3, effort=EffortLevel.QUICK,
                specific_action=""
            ),
            Gap(
                id="2", category=GapCategory.SPECIFICITY,
                severity=GapSeverity.MAJOR, title="", description="",
                current_state="", target_state="",
                estimated_score_impact=0.3, effort=EffortLevel.MODERATE,
                specific_action=""
            )
        ]

        effort = service._estimate_total_effort(gaps)
        assert "hour" in effort or "minute" in effort
```

---

## Verification Checklist

- [ ] Gap analysis service identifies 3-6 relevant gaps
- [ ] Gaps are categorized correctly
- [ ] Severity assignment is appropriate
- [ ] Priority ordering favors high-impact, low-effort gaps
- [ ] Score impact estimates are reasonable (0.1-1.0)
- [ ] Gap closure suggestions are actionable
- [ ] Progress tracking persists gap resolution
- [ ] UI displays gaps clearly with severity colors
- [ ] Example text helps users understand target state

---

## Integration Notes

1. **With Score Integration (Task 09)**: Run gap analysis after each evaluation
2. **With Smart Rewriter (Task 11)**: Use gap info to guide rewrites
3. **With Progress Tracking (Task 15)**: Feed gap closure into achievements
4. **With Dashboard (Task 16)**: Show proposal-wide gap summary
