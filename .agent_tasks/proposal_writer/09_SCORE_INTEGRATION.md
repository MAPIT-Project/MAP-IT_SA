# Task 09: Score Integration with UI

> **Priority:** P1 (Core Value)
> **Estimated Effort:** 3-4 hours
> **Dependencies:** Task 08 (Evaluator Simulator)
> **Status:** Not Started

---

## Problem Statement

The Evaluator Simulator (Task 08) generates predicted scores, but these need to be:
1. Stored persistently in the database
2. Displayed in the UI with proper formatting
3. Updated in real-time as content changes
4. Tracked historically for progress visualization

### Current State
- No score storage in database
- No score display in UI
- No historical tracking

### Target State
- Scores stored per section with confidence levels
- Visual score display with color coding
- Historical score tracking for improvement visualization
- Real-time score updates during editing

---

## Implementation Plan

### Step 1: Database Schema for Score Storage

**File:** `migration/011_score_storage.sql`

```sql
-- Score storage for evaluator predictions
-- Tracks current and historical scores for each section

-- Current scores for each section
CREATE TABLE IF NOT EXISTS section_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    section_id UUID NOT NULL REFERENCES proposal_sections(id) ON DELETE CASCADE,
    section_type VARCHAR(50) NOT NULL,

    -- Score data
    predicted_score DECIMAL(2,1) NOT NULL,  -- 0.0 to 5.0
    confidence DECIMAL(3,2) NOT NULL,        -- 0.00 to 1.00
    score_tier VARCHAR(20) NOT NULL,         -- threshold, good, excellent

    -- Breakdown
    criterion_scores JSONB,  -- Per-criterion breakdown
    strengths JSONB,         -- List of identified strengths
    weaknesses JSONB,        -- List of identified weaknesses
    evaluator_comments TEXT, -- ESR-style comments

    -- Metadata
    content_hash VARCHAR(64) NOT NULL,  -- Hash of content that was scored
    model_version VARCHAR(20) DEFAULT 'v1.0',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(section_id)  -- One current score per section
);

-- Historical scores for tracking improvement
CREATE TABLE IF NOT EXISTS section_score_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID NOT NULL REFERENCES proposal_sections(id) ON DELETE CASCADE,
    proposal_id UUID NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,

    -- Score snapshot
    predicted_score DECIMAL(2,1) NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    content_length INT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,

    -- Context
    trigger_type VARCHAR(20) NOT NULL,  -- manual, auto, save
    created_at TIMESTAMP DEFAULT NOW()
);

-- Proposal-level aggregated scores
CREATE TABLE IF NOT EXISTS proposal_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,

    -- Aggregated scores by criterion
    excellence_score DECIMAL(2,1),
    impact_score DECIMAL(2,1),
    implementation_score DECIMAL(2,1),
    overall_score DECIMAL(2,1),

    -- Derived metrics
    funding_probability DECIMAL(3,2),  -- 0.00 to 1.00
    threshold_distance DECIMAL(2,1),   -- Points from threshold
    estimated_rank VARCHAR(20),        -- top_10, top_25, etc.

    -- Metadata
    sections_scored INT DEFAULT 0,
    total_sections INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),

    UNIQUE(proposal_id)
);

-- Indexes for performance
CREATE INDEX idx_section_scores_proposal ON section_scores(proposal_id);
CREATE INDEX idx_section_scores_section ON section_scores(section_id);
CREATE INDEX idx_score_history_section ON section_score_history(section_id);
CREATE INDEX idx_score_history_created ON section_score_history(created_at);
CREATE INDEX idx_proposal_scores_proposal ON proposal_scores(proposal_id);

-- Function to update proposal aggregate scores
CREATE OR REPLACE FUNCTION update_proposal_aggregate_scores()
RETURNS TRIGGER AS $$
BEGIN
    -- Recalculate proposal-level scores
    INSERT INTO proposal_scores (
        proposal_id,
        excellence_score,
        impact_score,
        implementation_score,
        overall_score,
        sections_scored,
        total_sections,
        last_updated
    )
    SELECT
        NEW.proposal_id,
        AVG(CASE WHEN section_type LIKE 'excellence%' THEN predicted_score END),
        AVG(CASE WHEN section_type LIKE 'impact%' THEN predicted_score END),
        AVG(CASE WHEN section_type LIKE 'implementation%' THEN predicted_score END),
        AVG(predicted_score),
        COUNT(*),
        (SELECT COUNT(*) FROM proposal_sections WHERE proposal_id = NEW.proposal_id),
        NOW()
    FROM section_scores
    WHERE proposal_id = NEW.proposal_id
    GROUP BY proposal_id
    ON CONFLICT (proposal_id) DO UPDATE SET
        excellence_score = EXCLUDED.excellence_score,
        impact_score = EXCLUDED.impact_score,
        implementation_score = EXCLUDED.implementation_score,
        overall_score = EXCLUDED.overall_score,
        sections_scored = EXCLUDED.sections_scored,
        total_sections = EXCLUDED.total_sections,
        last_updated = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update aggregates
DROP TRIGGER IF EXISTS trg_update_proposal_scores ON section_scores;
CREATE TRIGGER trg_update_proposal_scores
AFTER INSERT OR UPDATE ON section_scores
FOR EACH ROW EXECUTE FUNCTION update_proposal_aggregate_scores();

-- View for easy score access
CREATE OR REPLACE VIEW v_section_scores AS
SELECT
    ss.id,
    ss.proposal_id,
    ss.section_id,
    ps.section_type,
    ps.title as section_title,
    ss.predicted_score,
    ss.confidence,
    ss.score_tier,
    ss.criterion_scores,
    ss.strengths,
    ss.weaknesses,
    ss.evaluator_comments,
    ss.created_at,
    p.title as proposal_title
FROM section_scores ss
JOIN proposal_sections ps ON ss.section_id = ps.id
JOIN proposals p ON ss.proposal_id = p.id;

-- View for score history with context
CREATE OR REPLACE VIEW v_score_history AS
SELECT
    sh.id,
    sh.section_id,
    sh.proposal_id,
    ps.section_type,
    ps.title as section_title,
    sh.predicted_score,
    sh.confidence,
    sh.content_length,
    sh.trigger_type,
    sh.created_at,
    LAG(sh.predicted_score) OVER (
        PARTITION BY sh.section_id ORDER BY sh.created_at
    ) as previous_score,
    sh.predicted_score - LAG(sh.predicted_score) OVER (
        PARTITION BY sh.section_id ORDER BY sh.created_at
    ) as score_change
FROM section_score_history sh
JOIN proposal_sections ps ON sh.section_id = ps.id
ORDER BY sh.created_at DESC;
```

### Step 2: Score Storage Service

**File:** `app/services/proposal_writing/score_storage_service.py`

```python
"""
Score Storage Service

Handles persistent storage and retrieval of evaluator scores.
Manages both current scores and historical tracking.
"""

import hashlib
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from app.services.database import get_db_connection

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    """What triggered the score calculation."""
    MANUAL = "manual"       # User clicked "Evaluate"
    AUTO = "auto"           # Automatic on content change
    SAVE = "save"           # On section save
    BATCH = "batch"         # Batch evaluation


@dataclass
class StoredScore:
    """A stored section score."""
    id: str
    proposal_id: str
    section_id: str
    section_type: str
    predicted_score: float
    confidence: float
    score_tier: str
    criterion_scores: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    evaluator_comments: str
    created_at: datetime


@dataclass
class ScoreHistoryEntry:
    """A historical score entry."""
    id: str
    section_id: str
    predicted_score: float
    confidence: float
    content_length: int
    trigger_type: str
    created_at: datetime
    previous_score: Optional[float]
    score_change: Optional[float]


@dataclass
class ProposalScoreSummary:
    """Aggregated scores for a proposal."""
    proposal_id: str
    excellence_score: Optional[float]
    impact_score: Optional[float]
    implementation_score: Optional[float]
    overall_score: Optional[float]
    funding_probability: Optional[float]
    threshold_distance: Optional[float]
    sections_scored: int
    total_sections: int
    last_updated: datetime


class ScoreStorageService:
    """
    Service for storing and retrieving evaluator scores.

    Handles:
    - Saving current scores with deduplication
    - Tracking score history for improvement visualization
    - Aggregating proposal-level metrics
    - Efficient retrieval for UI display
    """

    # Scoring thresholds
    THRESHOLD_SCORE = 3.0  # Minimum to pass
    GOOD_SCORE = 4.0       # Competitive score
    EXCELLENT_SCORE = 4.5  # High-scoring proposal

    async def save_score(
        self,
        proposal_id: str,
        section_id: str,
        section_type: str,
        content: str,
        score_result: Dict[str, Any],
        trigger: TriggerType = TriggerType.MANUAL
    ) -> StoredScore:
        """
        Save an evaluation score for a section.

        Args:
            proposal_id: The proposal ID
            section_id: The section ID
            section_type: Type of section (excellence_objectives, etc.)
            content: The content that was scored
            score_result: Result from EvaluatorSimulator
            trigger: What triggered this evaluation

        Returns:
            The stored score record
        """
        content_hash = self._hash_content(content)

        # Check if content has changed
        existing = await self._get_existing_score(section_id)
        if existing and existing.get('content_hash') == content_hash:
            logger.info(f"Score already exists for unchanged content: {section_id}")
            return await self.get_section_score(section_id)

        # Determine score tier
        score_tier = self._get_score_tier(score_result['predicted_score'])

        async with get_db_connection() as conn:
            # Save current score (upsert)
            result = await conn.fetchrow("""
                INSERT INTO section_scores (
                    proposal_id, section_id, section_type,
                    predicted_score, confidence, score_tier,
                    criterion_scores, strengths, weaknesses,
                    evaluator_comments, content_hash
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (section_id) DO UPDATE SET
                    predicted_score = EXCLUDED.predicted_score,
                    confidence = EXCLUDED.confidence,
                    score_tier = EXCLUDED.score_tier,
                    criterion_scores = EXCLUDED.criterion_scores,
                    strengths = EXCLUDED.strengths,
                    weaknesses = EXCLUDED.weaknesses,
                    evaluator_comments = EXCLUDED.evaluator_comments,
                    content_hash = EXCLUDED.content_hash,
                    updated_at = NOW()
                RETURNING *
            """,
                proposal_id,
                section_id,
                section_type,
                score_result['predicted_score'],
                score_result.get('confidence', 0.8),
                score_tier,
                score_result.get('criterion_scores', {}),
                score_result.get('strengths', []),
                score_result.get('weaknesses', []),
                score_result.get('evaluator_comments', ''),
                content_hash
            )

            # Add to history
            await conn.execute("""
                INSERT INTO section_score_history (
                    section_id, proposal_id, predicted_score,
                    confidence, content_length, content_hash, trigger_type
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                section_id,
                proposal_id,
                score_result['predicted_score'],
                score_result.get('confidence', 0.8),
                len(content),
                content_hash,
                trigger.value
            )

            return StoredScore(
                id=str(result['id']),
                proposal_id=proposal_id,
                section_id=section_id,
                section_type=section_type,
                predicted_score=result['predicted_score'],
                confidence=result['confidence'],
                score_tier=result['score_tier'],
                criterion_scores=result['criterion_scores'] or {},
                strengths=result['strengths'] or [],
                weaknesses=result['weaknesses'] or [],
                evaluator_comments=result['evaluator_comments'] or '',
                created_at=result['created_at']
            )

    async def get_section_score(self, section_id: str) -> Optional[StoredScore]:
        """Get the current score for a section."""
        async with get_db_connection() as conn:
            result = await conn.fetchrow("""
                SELECT * FROM section_scores WHERE section_id = $1
            """, section_id)

            if not result:
                return None

            return StoredScore(
                id=str(result['id']),
                proposal_id=str(result['proposal_id']),
                section_id=str(result['section_id']),
                section_type=result['section_type'],
                predicted_score=float(result['predicted_score']),
                confidence=float(result['confidence']),
                score_tier=result['score_tier'],
                criterion_scores=result['criterion_scores'] or {},
                strengths=result['strengths'] or [],
                weaknesses=result['weaknesses'] or [],
                evaluator_comments=result['evaluator_comments'] or '',
                created_at=result['created_at']
            )

    async def get_proposal_scores(self, proposal_id: str) -> List[StoredScore]:
        """Get all section scores for a proposal."""
        async with get_db_connection() as conn:
            results = await conn.fetch("""
                SELECT * FROM section_scores
                WHERE proposal_id = $1
                ORDER BY section_type
            """, proposal_id)

            return [
                StoredScore(
                    id=str(r['id']),
                    proposal_id=str(r['proposal_id']),
                    section_id=str(r['section_id']),
                    section_type=r['section_type'],
                    predicted_score=float(r['predicted_score']),
                    confidence=float(r['confidence']),
                    score_tier=r['score_tier'],
                    criterion_scores=r['criterion_scores'] or {},
                    strengths=r['strengths'] or [],
                    weaknesses=r['weaknesses'] or [],
                    evaluator_comments=r['evaluator_comments'] or '',
                    created_at=r['created_at']
                )
                for r in results
            ]

    async def get_proposal_summary(self, proposal_id: str) -> Optional[ProposalScoreSummary]:
        """Get aggregated scores for a proposal."""
        async with get_db_connection() as conn:
            result = await conn.fetchrow("""
                SELECT * FROM proposal_scores WHERE proposal_id = $1
            """, proposal_id)

            if not result:
                return None

            return ProposalScoreSummary(
                proposal_id=str(result['proposal_id']),
                excellence_score=float(result['excellence_score']) if result['excellence_score'] else None,
                impact_score=float(result['impact_score']) if result['impact_score'] else None,
                implementation_score=float(result['implementation_score']) if result['implementation_score'] else None,
                overall_score=float(result['overall_score']) if result['overall_score'] else None,
                funding_probability=float(result['funding_probability']) if result['funding_probability'] else None,
                threshold_distance=float(result['threshold_distance']) if result['threshold_distance'] else None,
                sections_scored=result['sections_scored'],
                total_sections=result['total_sections'],
                last_updated=result['last_updated']
            )

    async def get_score_history(
        self,
        section_id: str,
        limit: int = 50
    ) -> List[ScoreHistoryEntry]:
        """Get score history for a section."""
        async with get_db_connection() as conn:
            results = await conn.fetch("""
                SELECT * FROM v_score_history
                WHERE section_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, section_id, limit)

            return [
                ScoreHistoryEntry(
                    id=str(r['id']),
                    section_id=str(r['section_id']),
                    predicted_score=float(r['predicted_score']),
                    confidence=float(r['confidence']),
                    content_length=r['content_length'],
                    trigger_type=r['trigger_type'],
                    created_at=r['created_at'],
                    previous_score=float(r['previous_score']) if r['previous_score'] else None,
                    score_change=float(r['score_change']) if r['score_change'] else None
                )
                for r in results
            ]

    async def get_improvement_trend(
        self,
        section_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get improvement trend for a section over time."""
        async with get_db_connection() as conn:
            results = await conn.fetch("""
                SELECT
                    DATE(created_at) as date,
                    AVG(predicted_score) as avg_score,
                    MAX(predicted_score) as max_score,
                    COUNT(*) as evaluations
                FROM section_score_history
                WHERE section_id = $1
                AND created_at >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date
            """ % days, section_id)

            if not results:
                return {"trend": "no_data", "data": []}

            data = [
                {
                    "date": str(r['date']),
                    "avg_score": float(r['avg_score']),
                    "max_score": float(r['max_score']),
                    "evaluations": r['evaluations']
                }
                for r in results
            ]

            # Calculate trend direction
            if len(data) >= 2:
                first_score = data[0]['avg_score']
                last_score = data[-1]['avg_score']
                change = last_score - first_score

                if change > 0.3:
                    trend = "improving"
                elif change < -0.3:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"

            return {
                "trend": trend,
                "data": data,
                "total_improvement": data[-1]['avg_score'] - data[0]['avg_score'] if len(data) >= 2 else 0
            }

    def _hash_content(self, content: str) -> str:
        """Generate a hash of content for change detection."""
        return hashlib.sha256(content.encode()).hexdigest()[:64]

    def _get_score_tier(self, score: float) -> str:
        """Determine the score tier."""
        if score >= self.EXCELLENT_SCORE:
            return "excellent"
        elif score >= self.GOOD_SCORE:
            return "good"
        elif score >= self.THRESHOLD_SCORE:
            return "threshold"
        else:
            return "below_threshold"

    async def _get_existing_score(self, section_id: str) -> Optional[Dict]:
        """Get existing score record if any."""
        async with get_db_connection() as conn:
            return await conn.fetchrow("""
                SELECT content_hash FROM section_scores WHERE section_id = $1
            """, section_id)
```

### Step 3: API Endpoints for Score Management

**File:** `app/api/score_routes.py`

```python
"""
API routes for score management.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from app.services.proposal_writing.score_storage_service import (
    ScoreStorageService, TriggerType
)
from app.services.proposal_writing.evaluator_simulator import EvaluatorSimulator

router = APIRouter(prefix="/api/proposal/scores", tags=["scores"])


class EvaluateRequest(BaseModel):
    proposal_id: str
    section_id: str
    section_type: str
    content: str
    cluster: Optional[str] = None
    action_type: Optional[str] = None


class ScoreResponse(BaseModel):
    section_id: str
    predicted_score: float
    confidence: float
    score_tier: str
    criterion_scores: dict
    strengths: List[str]
    weaknesses: List[str]
    evaluator_comments: str
    created_at: datetime


class ProposalScoreSummaryResponse(BaseModel):
    proposal_id: str
    excellence_score: Optional[float]
    impact_score: Optional[float]
    implementation_score: Optional[float]
    overall_score: Optional[float]
    funding_probability: Optional[float]
    threshold_distance: Optional[float]
    sections_scored: int
    total_sections: int
    completion_percentage: float


class ScoreHistoryResponse(BaseModel):
    entries: List[dict]
    trend: str
    total_improvement: float


class ScoreTrendData(BaseModel):
    date: str
    avg_score: float
    max_score: float
    evaluations: int


@router.post("/evaluate", response_model=ScoreResponse)
async def evaluate_section(request: EvaluateRequest):
    """
    Evaluate a section and store the score.

    Runs the evaluator simulator and persists the result.
    Returns the complete score breakdown.
    """
    evaluator = EvaluatorSimulator()
    storage = ScoreStorageService()

    try:
        # Run evaluation
        result = await evaluator.simulate_evaluation(
            content=request.content,
            section_type=request.section_type,
            cluster=request.cluster,
            action_type=request.action_type
        )

        # Store the score
        stored = await storage.save_score(
            proposal_id=request.proposal_id,
            section_id=request.section_id,
            section_type=request.section_type,
            content=request.content,
            score_result=result.__dict__,
            trigger=TriggerType.MANUAL
        )

        return ScoreResponse(
            section_id=stored.section_id,
            predicted_score=stored.predicted_score,
            confidence=stored.confidence,
            score_tier=stored.score_tier,
            criterion_scores=stored.criterion_scores,
            strengths=stored.strengths,
            weaknesses=stored.weaknesses,
            evaluator_comments=stored.evaluator_comments,
            created_at=stored.created_at
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/section/{section_id}", response_model=ScoreResponse)
async def get_section_score(section_id: str):
    """Get the current score for a section."""
    storage = ScoreStorageService()

    score = await storage.get_section_score(section_id)
    if not score:
        raise HTTPException(status_code=404, detail="No score found for section")

    return ScoreResponse(
        section_id=score.section_id,
        predicted_score=score.predicted_score,
        confidence=score.confidence,
        score_tier=score.score_tier,
        criterion_scores=score.criterion_scores,
        strengths=score.strengths,
        weaknesses=score.weaknesses,
        evaluator_comments=score.evaluator_comments,
        created_at=score.created_at
    )


@router.get("/proposal/{proposal_id}", response_model=List[ScoreResponse])
async def get_proposal_scores(proposal_id: str):
    """Get all section scores for a proposal."""
    storage = ScoreStorageService()

    scores = await storage.get_proposal_scores(proposal_id)

    return [
        ScoreResponse(
            section_id=s.section_id,
            predicted_score=s.predicted_score,
            confidence=s.confidence,
            score_tier=s.score_tier,
            criterion_scores=s.criterion_scores,
            strengths=s.strengths,
            weaknesses=s.weaknesses,
            evaluator_comments=s.evaluator_comments,
            created_at=s.created_at
        )
        for s in scores
    ]


@router.get("/proposal/{proposal_id}/summary", response_model=ProposalScoreSummaryResponse)
async def get_proposal_summary(proposal_id: str):
    """Get aggregated scores for a proposal."""
    storage = ScoreStorageService()

    summary = await storage.get_proposal_summary(proposal_id)
    if not summary:
        raise HTTPException(status_code=404, detail="No scores found for proposal")

    completion = (summary.sections_scored / summary.total_sections * 100) if summary.total_sections > 0 else 0

    return ProposalScoreSummaryResponse(
        proposal_id=summary.proposal_id,
        excellence_score=summary.excellence_score,
        impact_score=summary.impact_score,
        implementation_score=summary.implementation_score,
        overall_score=summary.overall_score,
        funding_probability=summary.funding_probability,
        threshold_distance=summary.threshold_distance,
        sections_scored=summary.sections_scored,
        total_sections=summary.total_sections,
        completion_percentage=completion
    )


@router.get("/section/{section_id}/history", response_model=ScoreHistoryResponse)
async def get_score_history(section_id: str, days: int = 7):
    """Get score history for a section."""
    storage = ScoreStorageService()

    history = await storage.get_score_history(section_id)
    trend_data = await storage.get_improvement_trend(section_id, days)

    return ScoreHistoryResponse(
        entries=[
            {
                "id": h.id,
                "predicted_score": h.predicted_score,
                "confidence": h.confidence,
                "content_length": h.content_length,
                "trigger_type": h.trigger_type,
                "created_at": h.created_at.isoformat(),
                "previous_score": h.previous_score,
                "score_change": h.score_change
            }
            for h in history[:20]  # Last 20 entries
        ],
        trend=trend_data['trend'],
        total_improvement=trend_data.get('total_improvement', 0)
    )


@router.post("/proposal/{proposal_id}/evaluate-all")
async def evaluate_all_sections(
    proposal_id: str,
    background_tasks: BackgroundTasks
):
    """
    Evaluate all sections in a proposal (background task).

    Returns immediately and runs evaluation in background.
    """
    background_tasks.add_task(_evaluate_all_sections, proposal_id)

    return {
        "status": "started",
        "message": "Evaluation started in background",
        "proposal_id": proposal_id
    }


async def _evaluate_all_sections(proposal_id: str):
    """Background task to evaluate all sections."""
    from app.services.database import get_db_connection

    evaluator = EvaluatorSimulator()
    storage = ScoreStorageService()

    async with get_db_connection() as conn:
        sections = await conn.fetch("""
            SELECT id, section_type, content
            FROM proposal_sections
            WHERE proposal_id = $1 AND content IS NOT NULL
        """, proposal_id)

        for section in sections:
            try:
                result = await evaluator.simulate_evaluation(
                    content=section['content'],
                    section_type=section['section_type']
                )

                await storage.save_score(
                    proposal_id=proposal_id,
                    section_id=str(section['id']),
                    section_type=section['section_type'],
                    content=section['content'],
                    score_result=result.__dict__,
                    trigger=TriggerType.BATCH
                )

            except Exception as e:
                logger.error(f"Error evaluating section {section['id']}: {e}")
```

### Step 4: UI Components (React)

**File:** `frontend/components/ScoreDisplay.tsx`

```typescript
import React from 'react';

interface ScoreDisplayProps {
  score: number;  // 0-5
  confidence: number;  // 0-1
  tier: 'excellent' | 'good' | 'threshold' | 'below_threshold';
  showDetails?: boolean;
}

export const ScoreDisplay: React.FC<ScoreDisplayProps> = ({
  score,
  confidence,
  tier,
  showDetails = false
}) => {
  const getColorClass = () => {
    switch (tier) {
      case 'excellent': return 'bg-green-500 text-white';
      case 'good': return 'bg-blue-500 text-white';
      case 'threshold': return 'bg-yellow-500 text-black';
      case 'below_threshold': return 'bg-red-500 text-white';
    }
  };

  const getTierLabel = () => {
    switch (tier) {
      case 'excellent': return 'Excellent';
      case 'good': return 'Competitive';
      case 'threshold': return 'At Threshold';
      case 'below_threshold': return 'Needs Work';
    }
  };

  return (
    <div className="flex items-center gap-2">
      {/* Main score badge */}
      <div className={`rounded-full px-3 py-1 font-bold ${getColorClass()}`}>
        {score.toFixed(1)}/5
      </div>

      {/* Tier label */}
      <span className="text-sm text-gray-600">{getTierLabel()}</span>

      {/* Confidence indicator */}
      {showDetails && (
        <span className="text-xs text-gray-400">
          ({Math.round(confidence * 100)}% confidence)
        </span>
      )}
    </div>
  );
};

interface ScoreBreakdownProps {
  criterionScores: Record<string, number>;
  strengths: string[];
  weaknesses: string[];
}

export const ScoreBreakdown: React.FC<ScoreBreakdownProps> = ({
  criterionScores,
  strengths,
  weaknesses
}) => {
  return (
    <div className="space-y-4">
      {/* Criterion scores */}
      <div className="grid grid-cols-3 gap-4">
        {Object.entries(criterionScores).map(([criterion, score]) => (
          <div key={criterion} className="text-center">
            <div className="text-2xl font-bold">{score.toFixed(1)}</div>
            <div className="text-sm text-gray-500 capitalize">
              {criterion.replace('_', ' ')}
            </div>
          </div>
        ))}
      </div>

      {/* Strengths */}
      <div>
        <h4 className="font-medium text-green-700 mb-2">Strengths</h4>
        <ul className="list-disc list-inside text-sm space-y-1">
          {strengths.map((s, i) => (
            <li key={i} className="text-green-600">{s}</li>
          ))}
        </ul>
      </div>

      {/* Weaknesses */}
      <div>
        <h4 className="font-medium text-red-700 mb-2">Areas to Improve</h4>
        <ul className="list-disc list-inside text-sm space-y-1">
          {weaknesses.map((w, i) => (
            <li key={i} className="text-red-600">{w}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};

interface ScoreHistoryChartProps {
  data: Array<{
    date: string;
    avg_score: number;
    max_score: number;
  }>;
  trend: 'improving' | 'declining' | 'stable' | 'no_data';
}

export const ScoreHistoryChart: React.FC<ScoreHistoryChartProps> = ({
  data,
  trend
}) => {
  const getTrendIcon = () => {
    switch (trend) {
      case 'improving': return '📈';
      case 'declining': return '📉';
      case 'stable': return '➡️';
      default: return '❓';
    }
  };

  const getTrendColor = () => {
    switch (trend) {
      case 'improving': return 'text-green-600';
      case 'declining': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div>
      <div className={`flex items-center gap-2 mb-2 ${getTrendColor()}`}>
        <span>{getTrendIcon()}</span>
        <span className="capitalize">{trend.replace('_', ' ')}</span>
      </div>

      {/* Simple sparkline visualization */}
      <div className="flex items-end gap-1 h-16">
        {data.map((point, i) => (
          <div
            key={i}
            className="flex-1 bg-blue-400 rounded-t"
            style={{ height: `${(point.avg_score / 5) * 100}%` }}
            title={`${point.date}: ${point.avg_score.toFixed(1)}`}
          />
        ))}
      </div>
    </div>
  );
};
```

### Step 5: Real-time Score Updates via WebSocket

**File:** `app/api/score_websocket.py`

```python
"""
WebSocket endpoint for real-time score updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Track active connections per proposal
active_connections: Dict[str, Set[WebSocket]] = {}


class ScoreConnectionManager:
    """Manages WebSocket connections for score updates."""

    async def connect(self, websocket: WebSocket, proposal_id: str):
        await websocket.accept()
        if proposal_id not in active_connections:
            active_connections[proposal_id] = set()
        active_connections[proposal_id].add(websocket)
        logger.info(f"Client connected to proposal {proposal_id}")

    def disconnect(self, websocket: WebSocket, proposal_id: str):
        if proposal_id in active_connections:
            active_connections[proposal_id].discard(websocket)
            if not active_connections[proposal_id]:
                del active_connections[proposal_id]
        logger.info(f"Client disconnected from proposal {proposal_id}")

    async def broadcast_score_update(
        self,
        proposal_id: str,
        section_id: str,
        score_data: dict
    ):
        """Broadcast score update to all connected clients for a proposal."""
        if proposal_id not in active_connections:
            return

        message = json.dumps({
            "type": "score_update",
            "section_id": section_id,
            "data": score_data
        })

        disconnected = set()
        for websocket in active_connections[proposal_id]:
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.add(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            active_connections[proposal_id].discard(ws)


manager = ScoreConnectionManager()


@router.websocket("/ws/scores/{proposal_id}")
async def score_websocket(websocket: WebSocket, proposal_id: str):
    """
    WebSocket endpoint for real-time score updates.

    Clients can:
    - Receive score updates when any section is evaluated
    - Request immediate evaluation of a section
    """
    await manager.connect(websocket, proposal_id)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "evaluate":
                # Client requested evaluation
                from app.services.proposal_writing.evaluator_simulator import EvaluatorSimulator
                from app.services.proposal_writing.score_storage_service import (
                    ScoreStorageService, TriggerType
                )

                evaluator = EvaluatorSimulator()
                storage = ScoreStorageService()

                result = await evaluator.simulate_evaluation(
                    content=message["content"],
                    section_type=message["section_type"]
                )

                stored = await storage.save_score(
                    proposal_id=proposal_id,
                    section_id=message["section_id"],
                    section_type=message["section_type"],
                    content=message["content"],
                    score_result=result.__dict__,
                    trigger=TriggerType.AUTO
                )

                # Broadcast to all connected clients
                await manager.broadcast_score_update(
                    proposal_id=proposal_id,
                    section_id=message["section_id"],
                    score_data={
                        "predicted_score": stored.predicted_score,
                        "confidence": stored.confidence,
                        "score_tier": stored.score_tier,
                        "strengths": stored.strengths,
                        "weaknesses": stored.weaknesses
                    }
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, proposal_id)
```

---

## Testing Plan

```python
# tests/test_score_integration.py

import pytest
from app.services.proposal_writing.score_storage_service import (
    ScoreStorageService, TriggerType
)


class TestScoreStorage:

    @pytest.fixture
    def service(self):
        return ScoreStorageService()

    @pytest.mark.asyncio
    async def test_save_and_retrieve_score(self, service):
        """Test saving and retrieving a score."""
        score_result = {
            "predicted_score": 4.2,
            "confidence": 0.85,
            "criterion_scores": {"excellence": 4.0, "impact": 4.5},
            "strengths": ["Clear objectives"],
            "weaknesses": ["Missing methodology"],
            "evaluator_comments": "Good but needs work"
        }

        stored = await service.save_score(
            proposal_id="test-proposal",
            section_id="test-section",
            section_type="excellence_objectives",
            content="Test content for evaluation",
            score_result=score_result,
            trigger=TriggerType.MANUAL
        )

        assert stored.predicted_score == 4.2
        assert stored.confidence == 0.85
        assert stored.score_tier == "good"

        # Retrieve
        retrieved = await service.get_section_score("test-section")
        assert retrieved.predicted_score == 4.2

    @pytest.mark.asyncio
    async def test_score_tier_calculation(self, service):
        """Test score tier assignment."""
        assert service._get_score_tier(4.8) == "excellent"
        assert service._get_score_tier(4.2) == "good"
        assert service._get_score_tier(3.5) == "threshold"
        assert service._get_score_tier(2.5) == "below_threshold"
```

---

## Verification Checklist

- [ ] Migration 011 runs successfully
- [ ] Scores are saved correctly to database
- [ ] Duplicate content doesn't create new history entries
- [ ] Proposal aggregate scores calculate correctly
- [ ] API endpoints return proper responses
- [ ] WebSocket connection establishes and broadcasts
- [ ] Score history tracks changes over time
- [ ] UI components display scores correctly

---

## UI Integration Notes

1. **Section Editor**: Add score badge next to section title
2. **Sidebar**: Show proposal summary with all section scores
3. **Real-time Updates**: Connect WebSocket on proposal open
4. **History Modal**: Show score trend chart on click
5. **Color Coding**: Green (≥4.5), Blue (≥4.0), Yellow (≥3.0), Red (<3.0)
