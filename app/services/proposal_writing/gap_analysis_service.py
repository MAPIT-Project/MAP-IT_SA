"""
Gap Analysis Service

Analyzes the gap between current score and target score,
providing a prioritized roadmap to reach funding threshold.
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class GapSeverity(str, Enum):
    """Severity level of a gap."""

    CRITICAL = "critical"  # Must fix to reach threshold
    MAJOR = "major"  # Significant impact on score
    MINOR = "minor"  # Nice to fix, small impact
    POLISH = "polish"  # Final touches


class GapCategory(str, Enum):
    """Category of gap."""

    CONTENT_MISSING = "content_missing"  # Required content not present
    CONTENT_WEAK = "content_weak"  # Content exists but insufficient
    STRUCTURE = "structure"  # Organization/flow issues
    SPECIFICITY = "specificity"  # Too vague or generic
    EU_ALIGNMENT = "eu_alignment"  # Missing EU priorities/terminology
    QUANTIFICATION = "quantification"  # Missing metrics/KPIs
    METHODOLOGY = "methodology"  # Approach not clear
    INNOVATION = "innovation"  # Beyond state-of-art not established


class EffortLevel(str, Enum):
    """Estimated effort to close gap."""

    QUICK = "quick"  # < 30 minutes
    MODERATE = "moderate"  # 30 min - 2 hours
    SUBSTANTIAL = "substantial"  # 2-4 hours
    MAJOR = "major"  # > 4 hours


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
    example_text: str | None = None
    related_criterion: str | None = None
    is_resolved: bool = False


@dataclass
class GapAnalysisResult:
    """Complete gap analysis for a section."""

    section_id: str
    section_type: str
    current_score: float
    target_score: float
    score_gap: float
    gaps: list[Gap]
    critical_count: int
    total_estimated_impact: float
    recommended_priority_order: list[str]  # Gap IDs in order
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
        self._ai_service = None
        self._evaluator = None
        self._db_url = os.getenv("DATABASE_URL")

    def _get_ai_service(self):
        """Lazy load AI service."""
        if self._ai_service is None:
            from .proposal_ai_service import ProposalAIService

            self._ai_service = ProposalAIService()
        return self._ai_service

    def _get_evaluator(self):
        """Lazy load evaluator."""
        if self._evaluator is None:
            from .evaluator_simulator import EvaluatorSimulator

            self._evaluator = EvaluatorSimulator()
        return self._evaluator

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self._db_url)

    async def analyze_gaps(
        self,
        content: str,
        section_type: str,
        current_score: float,
        target_score: float | None = None,
        evaluation_result: dict | None = None,
        cluster: str | None = None,
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

        logger.info(
            f"Analyzing gaps: current={current_score}, target={target_score}, gap={score_gap}"
        )

        # Get evaluation if not provided
        if evaluation_result is None:
            evaluator = self._get_evaluator()
            eval_result = await evaluator.evaluate_section(
                section_text=content,
                section_type=section_type,
                section_id="objectives",  # Default
            )
            evaluation_result = {
                "weaknesses": eval_result.weaknesses,
                "strengths": eval_result.strengths,
                "criterion_scores": [
                    {"criterion": cs.criterion, "score": cs.score}
                    for cs in eval_result.criterion_scores
                ],
            }

        # Identify gaps using LLM analysis
        gaps = await self._identify_gaps(
            content=content,
            section_type=section_type,
            current_score=current_score,
            target_score=target_score,
            weaknesses=evaluation_result.get("weaknesses", []),
            cluster=cluster,
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
            achievable_score=achievable,
        )

    async def _identify_gaps(
        self,
        content: str,
        section_type: str,
        current_score: float,
        target_score: float,
        weaknesses: list[str],
        cluster: str | None,
    ) -> list[Gap]:
        """Identify specific gaps using LLM analysis."""
        ai_service = self._get_ai_service()

        weaknesses_text = (
            "\n".join(f"- {w}" for w in weaknesses) if weaknesses else "None identified"
        )

        prompt = f"""Analyze this proposal section and identify specific gaps preventing a higher score.

SECTION TYPE: {section_type}
CURRENT SCORE: {current_score}/5
TARGET SCORE: {target_score}/5
CLUSTER: {cluster or "General"}

CONTENT:
{content[:3000]}

KNOWN WEAKNESSES:
{weaknesses_text}

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

        schema = {
            "type": "object",
            "properties": {
                "gaps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "severity": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "current_state": {"type": "string"},
                            "target_state": {"type": "string"},
                            "estimated_score_impact": {"type": "number"},
                            "effort": {"type": "string"},
                            "specific_action": {"type": "string"},
                            "example_text": {"type": "string"},
                            "related_criterion": {"type": "string"},
                        },
                        "required": [
                            "category",
                            "severity",
                            "title",
                            "description",
                            "current_state",
                            "target_state",
                            "estimated_score_impact",
                            "effort",
                            "specific_action",
                        ],
                    },
                }
            },
            "required": ["gaps"],
        }

        response = await ai_service.generate_structured(prompt=prompt, response_schema=schema)

        gaps = []
        for i, gap_data in enumerate(response.get("gaps", [])):
            try:
                # Validate category
                category_str = gap_data["category"].lower()
                if category_str not in [c.value for c in GapCategory]:
                    category_str = "content_weak"

                # Validate severity
                severity_str = gap_data["severity"].lower()
                if severity_str not in [s.value for s in GapSeverity]:
                    severity_str = "major"

                # Validate effort
                effort_str = gap_data["effort"].lower()
                if effort_str not in [e.value for e in EffortLevel]:
                    effort_str = "moderate"

                gap = Gap(
                    id=f"gap_{i + 1}",
                    category=GapCategory(category_str),
                    severity=GapSeverity(severity_str),
                    title=gap_data["title"],
                    description=gap_data["description"],
                    current_state=gap_data["current_state"],
                    target_state=gap_data["target_state"],
                    estimated_score_impact=min(1.0, max(0.1, gap_data["estimated_score_impact"])),
                    effort=EffortLevel(effort_str),
                    specific_action=gap_data["specific_action"],
                    example_text=gap_data.get("example_text"),
                    related_criterion=gap_data.get("related_criterion"),
                )
                gaps.append(gap)
            except (KeyError, ValueError) as e:
                logger.warning(f"Error parsing gap: {e}")
                continue

        return gaps

    def _prioritize_gaps(self, gaps: list[Gap]) -> list[str]:
        """
        Prioritize gaps by impact-to-effort ratio.

        Priority formula: (score_impact * severity_weight) / effort_weight
        """
        severity_weights = {
            GapSeverity.CRITICAL: 2.0,
            GapSeverity.MAJOR: 1.5,
            GapSeverity.MINOR: 1.0,
            GapSeverity.POLISH: 0.5,
        }

        effort_weights = {
            EffortLevel.QUICK: 1.0,
            EffortLevel.MODERATE: 2.0,
            EffortLevel.SUBSTANTIAL: 4.0,
            EffortLevel.MAJOR: 8.0,
        }

        def priority_score(gap: Gap) -> float:
            impact = gap.estimated_score_impact * severity_weights[gap.severity]
            effort = effort_weights[gap.effort]
            return impact / effort

        sorted_gaps = sorted(gaps, key=priority_score, reverse=True)
        return [g.id for g in sorted_gaps]

    def _estimate_total_effort(self, gaps: list[Gap]) -> str:
        """Estimate total effort to close all gaps."""
        effort_minutes = {
            EffortLevel.QUICK: 20,
            EffortLevel.MODERATE: 75,
            EffortLevel.SUBSTANTIAL: 180,
            EffortLevel.MAJOR: 360,
        }

        total_minutes = sum(effort_minutes[g.effort] for g in gaps)

        if total_minutes < 60:
            return f"{total_minutes} minutes"
        elif total_minutes < 240:
            hours = total_minutes / 60
            return f"{hours:.1f} hours"
        else:
            hours = total_minutes / 60
            days = total_minutes / 480
            return f"{hours:.0f} hours ({days:.1f} work days)"

    async def get_gap_closure_suggestion(
        self, gap: Gap, content: str, section_type: str
    ) -> dict[str, Any]:
        """
        Get detailed suggestion for closing a specific gap.

        Returns rewritten text and explanation.
        """
        ai_service = self._get_ai_service()

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
    "before_snippet": "The original text being replaced (exact match from content)",
    "after_snippet": "The new text to replace it with",
    "estimated_new_score_impact": 0.3,
    "additional_tips": ["tip1", "tip2"]
}}"""

        schema = {
            "type": "object",
            "properties": {
                "rewritten_text": {"type": "string"},
                "explanation": {"type": "string"},
                "before_snippet": {"type": "string"},
                "after_snippet": {"type": "string"},
                "estimated_new_score_impact": {"type": "number"},
                "additional_tips": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["rewritten_text", "explanation", "before_snippet", "after_snippet"],
        }

        response = await ai_service.generate_structured(prompt=prompt, response_schema=schema)

        return response

    async def track_gap_progress(self, section_id: str, gap_id: str, resolved: bool) -> None:
        """Track when a gap is resolved."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE gap_tracking
                    SET resolved = %s, resolved_at = NOW()
                    WHERE section_id = %s AND gap_id = %s
                """,
                    (resolved, section_id, gap_id),
                )
                conn.commit()
        finally:
            conn.close()

    async def save_gaps(self, section_id: str, gaps: list[Gap]) -> None:
        """Save identified gaps to database."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                for gap in gaps:
                    cur.execute(
                        """
                        INSERT INTO gap_tracking (
                            section_id, gap_id, category, severity,
                            title, estimated_impact, effort_level
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (section_id, gap_id) DO UPDATE SET
                            category = EXCLUDED.category,
                            severity = EXCLUDED.severity,
                            title = EXCLUDED.title,
                            estimated_impact = EXCLUDED.estimated_impact,
                            effort_level = EXCLUDED.effort_level
                    """,
                        (
                            section_id,
                            gap.id,
                            gap.category.value,
                            gap.severity.value,
                            gap.title,
                            gap.estimated_score_impact,
                            gap.effort.value,
                        ),
                    )
                conn.commit()
        finally:
            conn.close()


class GapProgressTracker:
    """
    Tracks progress on closing gaps over time.

    Provides statistics and visualizations of improvement journey.
    """

    def __init__(self):
        self._db_url = os.getenv("DATABASE_URL")

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self._db_url)

    async def get_section_progress(self, section_id: str) -> dict[str, Any]:
        """Get gap closure progress for a section."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get gap tracking data
                cur.execute(
                    """
                    SELECT gap_id, resolved, resolved_at
                    FROM gap_tracking
                    WHERE section_id = %s
                """,
                    (section_id,),
                )
                tracking = cur.fetchall()

                # Get score history
                cur.execute(
                    """
                    SELECT predicted_score, created_at
                    FROM section_score_history
                    WHERE section_id = %s
                    ORDER BY created_at
                """,
                    (section_id,),
                )
                scores = cur.fetchall()

                total_gaps = len(tracking)
                resolved_gaps = sum(1 for t in tracking if t["resolved"])

                score_improvement = 0
                if len(scores) >= 2:
                    score_improvement = float(scores[-1]["predicted_score"]) - float(
                        scores[0]["predicted_score"]
                    )

                return {
                    "total_gaps_identified": total_gaps,
                    "gaps_resolved": resolved_gaps,
                    "completion_percentage": (
                        (resolved_gaps / total_gaps * 100) if total_gaps > 0 else 0
                    ),
                    "score_history": [
                        {"score": float(s["predicted_score"]), "date": s["created_at"].isoformat()}
                        for s in scores
                    ],
                    "score_improvement": score_improvement,
                }
        finally:
            conn.close()

    async def get_proposal_progress(self, proposal_id: str) -> dict[str, Any]:
        """Get overall gap progress for a proposal."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(DISTINCT gt.gap_id) as total_gaps,
                        COUNT(DISTINCT gt.gap_id) FILTER (WHERE gt.resolved) as resolved_gaps,
                        AVG(ss.predicted_score) as current_avg_score
                    FROM gap_tracking gt
                    JOIN section_scores ss ON gt.section_id = ss.section_id
                    WHERE ss.proposal_id = %s
                """,
                    (proposal_id,),
                )
                result = cur.fetchone()

                total_gaps = result["total_gaps"] or 0
                resolved_gaps = result["resolved_gaps"] or 0

                return {
                    "total_gaps": total_gaps,
                    "resolved_gaps": resolved_gaps,
                    "current_avg_score": (
                        float(result["current_avg_score"]) if result["current_avg_score"] else 0
                    ),
                    "completion_percentage": (
                        (resolved_gaps / total_gaps * 100) if total_gaps else 0
                    ),
                }
        finally:
            conn.close()
