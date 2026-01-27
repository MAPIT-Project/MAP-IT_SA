"""
Score Storage Service

Handles persistent storage and retrieval of evaluator scores.
Manages both current scores and historical tracking.
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    """What triggered the score calculation."""

    MANUAL = "manual"  # User clicked "Evaluate"
    AUTO = "auto"  # Automatic on content change
    SAVE = "save"  # On section save
    BATCH = "batch"  # Batch evaluation


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
    criterion_scores: dict[str, float]
    strengths: list[str]
    weaknesses: list[str]
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
    previous_score: float | None
    score_change: float | None


@dataclass
class ProposalScoreSummary:
    """Aggregated scores for a proposal."""

    proposal_id: str
    excellence_score: float | None
    impact_score: float | None
    implementation_score: float | None
    overall_score: float | None
    funding_probability: float | None
    threshold_distance: float | None
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
    GOOD_SCORE = 4.0  # Competitive score
    EXCELLENT_SCORE = 4.5  # High-scoring proposal

    def __init__(self):
        self._db_url = os.getenv("DATABASE_URL")

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self._db_url)

    async def save_score(
        self,
        proposal_id: str,
        section_id: str,
        section_type: str,
        content: str,
        score_result: dict[str, Any],
        trigger: TriggerType = TriggerType.MANUAL,
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
        if existing and existing.get("content_hash") == content_hash:
            logger.info(f"Score already exists for unchanged content: {section_id}")
            return await self.get_section_score(section_id)

        # Determine score tier
        predicted_score = score_result.get(
            "overall_score", score_result.get("predicted_score", 3.0)
        )
        score_tier = self._get_score_tier(predicted_score)

        # Prepare criterion scores as JSON
        criterion_scores = score_result.get("criterion_scores", {})
        if isinstance(criterion_scores, list):
            # Convert list of CriterionScore objects to dict
            criterion_scores = {
                cs.get("criterion", f"criterion_{i}"): cs.get("score", 0)
                for i, cs in enumerate(criterion_scores)
            }

        strengths = score_result.get("strengths", [])
        weaknesses = score_result.get("weaknesses", [])
        evaluator_comments = score_result.get(
            "esr_summary", score_result.get("evaluator_comments", "")
        )
        confidence = score_result.get("confidence", 0.8)

        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Save current score (upsert)
                cur.execute(
                    """
                    INSERT INTO section_scores (
                        proposal_id, section_id, section_type,
                        predicted_score, confidence, score_tier,
                        criterion_scores, strengths, weaknesses,
                        evaluator_comments, content_hash
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    (
                        proposal_id,
                        section_id,
                        section_type,
                        predicted_score,
                        confidence,
                        score_tier,
                        json.dumps(criterion_scores),
                        json.dumps(strengths),
                        json.dumps(weaknesses),
                        evaluator_comments,
                        content_hash,
                    ),
                )
                result = cur.fetchone()

                # Add to history
                cur.execute(
                    """
                    INSERT INTO section_score_history (
                        section_id, proposal_id, predicted_score,
                        confidence, content_length, content_hash, trigger_type
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        section_id,
                        proposal_id,
                        predicted_score,
                        confidence,
                        len(content),
                        content_hash,
                        trigger.value,
                    ),
                )

                conn.commit()

                # Parse JSON fields
                cs = result["criterion_scores"]
                st = result["strengths"]
                wk = result["weaknesses"]

                return StoredScore(
                    id=str(result["id"]),
                    proposal_id=str(proposal_id),
                    section_id=str(section_id),
                    section_type=section_type,
                    predicted_score=float(result["predicted_score"]),
                    confidence=float(result["confidence"]),
                    score_tier=result["score_tier"],
                    criterion_scores=cs if isinstance(cs, dict) else json.loads(cs) if cs else {},
                    strengths=st if isinstance(st, list) else json.loads(st) if st else [],
                    weaknesses=wk if isinstance(wk, list) else json.loads(wk) if wk else [],
                    evaluator_comments=result["evaluator_comments"] or "",
                    created_at=result["created_at"],
                )
        finally:
            conn.close()

    async def get_section_score(self, section_id: str) -> StoredScore | None:
        """Get the current score for a section."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM section_scores WHERE section_id = %s
                """,
                    (section_id,),
                )
                result = cur.fetchone()

                if not result:
                    return None

                cs = result["criterion_scores"]
                st = result["strengths"]
                wk = result["weaknesses"]

                return StoredScore(
                    id=str(result["id"]),
                    proposal_id=str(result["proposal_id"]),
                    section_id=str(result["section_id"]),
                    section_type=result["section_type"],
                    predicted_score=float(result["predicted_score"]),
                    confidence=float(result["confidence"]),
                    score_tier=result["score_tier"],
                    criterion_scores=cs if isinstance(cs, dict) else json.loads(cs) if cs else {},
                    strengths=st if isinstance(st, list) else json.loads(st) if st else [],
                    weaknesses=wk if isinstance(wk, list) else json.loads(wk) if wk else [],
                    evaluator_comments=result["evaluator_comments"] or "",
                    created_at=result["created_at"],
                )
        finally:
            conn.close()

    async def get_proposal_scores(self, proposal_id: str) -> list[StoredScore]:
        """Get all section scores for a proposal."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM section_scores
                    WHERE proposal_id = %s
                    ORDER BY section_type
                """,
                    (proposal_id,),
                )
                results = cur.fetchall()

                scores = []
                for r in results:
                    cs = r["criterion_scores"]
                    st = r["strengths"]
                    wk = r["weaknesses"]

                    scores.append(
                        StoredScore(
                            id=str(r["id"]),
                            proposal_id=str(r["proposal_id"]),
                            section_id=str(r["section_id"]),
                            section_type=r["section_type"],
                            predicted_score=float(r["predicted_score"]),
                            confidence=float(r["confidence"]),
                            score_tier=r["score_tier"],
                            criterion_scores=(
                                cs if isinstance(cs, dict) else json.loads(cs) if cs else {}
                            ),
                            strengths=st if isinstance(st, list) else json.loads(st) if st else [],
                            weaknesses=wk if isinstance(wk, list) else json.loads(wk) if wk else [],
                            evaluator_comments=r["evaluator_comments"] or "",
                            created_at=r["created_at"],
                        )
                    )

                return scores
        finally:
            conn.close()

    async def get_proposal_summary(self, proposal_id: str) -> ProposalScoreSummary | None:
        """Get aggregated scores for a proposal."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM proposal_scores WHERE proposal_id = %s
                """,
                    (proposal_id,),
                )
                result = cur.fetchone()

                if not result:
                    return None

                return ProposalScoreSummary(
                    proposal_id=str(result["proposal_id"]),
                    excellence_score=(
                        float(result["excellence_score"]) if result["excellence_score"] else None
                    ),
                    impact_score=float(result["impact_score"]) if result["impact_score"] else None,
                    implementation_score=(
                        float(result["implementation_score"])
                        if result["implementation_score"]
                        else None
                    ),
                    overall_score=(
                        float(result["overall_score"]) if result["overall_score"] else None
                    ),
                    funding_probability=(
                        float(result["funding_probability"])
                        if result["funding_probability"]
                        else None
                    ),
                    threshold_distance=(
                        float(result["threshold_distance"])
                        if result["threshold_distance"]
                        else None
                    ),
                    sections_scored=result["sections_scored"],
                    total_sections=result["total_sections"],
                    last_updated=result["last_updated"],
                )
        finally:
            conn.close()

    async def get_score_history(self, section_id: str, limit: int = 50) -> list[ScoreHistoryEntry]:
        """Get score history for a section."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        sh.id,
                        sh.section_id,
                        sh.predicted_score,
                        sh.confidence,
                        sh.content_length,
                        sh.trigger_type,
                        sh.created_at,
                        LAG(sh.predicted_score) OVER (
                            PARTITION BY sh.section_id ORDER BY sh.created_at
                        ) as previous_score
                    FROM section_score_history sh
                    WHERE sh.section_id = %s
                    ORDER BY sh.created_at DESC
                    LIMIT %s
                """,
                    (section_id, limit),
                )
                results = cur.fetchall()

                return [
                    ScoreHistoryEntry(
                        id=str(r["id"]),
                        section_id=str(r["section_id"]),
                        predicted_score=float(r["predicted_score"]),
                        confidence=float(r["confidence"]),
                        content_length=r["content_length"],
                        trigger_type=r["trigger_type"],
                        created_at=r["created_at"],
                        previous_score=float(r["previous_score"]) if r["previous_score"] else None,
                        score_change=(
                            float(r["predicted_score"]) - float(r["previous_score"])
                            if r["previous_score"]
                            else None
                        ),
                    )
                    for r in results
                ]
        finally:
            conn.close()

    async def get_improvement_trend(self, section_id: str, days: int = 7) -> dict[str, Any]:
        """Get improvement trend for a section over time."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        DATE(created_at) as date,
                        AVG(predicted_score) as avg_score,
                        MAX(predicted_score) as max_score,
                        COUNT(*) as evaluations
                    FROM section_score_history
                    WHERE section_id = %s
                    AND created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """,
                    (section_id, days),
                )
                results = cur.fetchall()

                if not results:
                    return {"trend": "no_data", "data": []}

                data = [
                    {
                        "date": str(r["date"]),
                        "avg_score": float(r["avg_score"]),
                        "max_score": float(r["max_score"]),
                        "evaluations": r["evaluations"],
                    }
                    for r in results
                ]

                # Calculate trend direction
                if len(data) >= 2:
                    first_score = data[0]["avg_score"]
                    last_score = data[-1]["avg_score"]
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
                    "total_improvement": (
                        data[-1]["avg_score"] - data[0]["avg_score"] if len(data) >= 2 else 0
                    ),
                }
        finally:
            conn.close()

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

    async def _get_existing_score(self, section_id: str) -> dict | None:
        """Get existing score record if any."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT content_hash FROM section_scores WHERE section_id = %s
                """,
                    (section_id,),
                )
                return cur.fetchone()
        finally:
            conn.close()
