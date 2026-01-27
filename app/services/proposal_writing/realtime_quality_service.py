"""
Real-Time Quality Service

Provides streaming, incremental quality feedback during writing.
Uses lightweight analysis for instant feedback with periodic deep analysis.
"""

import hashlib
import logging
import re
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from app.services.proposal_writing.evaluator_simulator import EvaluatorSimulator
from app.services.proposal_writing.inline_suggestions_service import RealTimeAnalyzer

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """Types of streaming feedback."""

    QUICK_SCORE = "quick_score"  # Instant score estimate
    SUGGESTION_COUNT = "suggestion_count"  # Number of suggestions
    QUALITY_TIER = "quality_tier"  # threshold/good/excellent
    THINKING = "thinking"  # AI is analyzing
    SCORE_UPDATE = "score_update"  # Full score update
    IMPROVEMENT = "improvement"  # Score improved
    CELEBRATION = "celebration"  # Major milestone


class QualityTier(str, Enum):
    """Quality tier for visual indicator."""

    POOR = "poor"  # <2.5
    THRESHOLD = "threshold"  # 2.5-3.0
    ACCEPTABLE = "acceptable"  # 3.0-3.5
    GOOD = "good"  # 3.5-4.0
    EXCELLENT = "excellent"  # 4.0-4.5
    OUTSTANDING = "outstanding"  # >4.5


@dataclass
class StreamingFeedback:
    """A single piece of streaming feedback."""

    type: FeedbackType
    value: Any
    message: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "value": self.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class RealTimeQualityService:
    """
    Service for providing real-time quality feedback.

    Combines fast heuristic analysis with periodic LLM evaluation
    to provide responsive feedback without excessive API calls.
    """

    # Score thresholds
    TIER_THRESHOLDS = {
        QualityTier.POOR: 0,
        QualityTier.THRESHOLD: 2.5,
        QualityTier.ACCEPTABLE: 3.0,
        QualityTier.GOOD: 3.5,
        QualityTier.EXCELLENT: 4.0,
        QualityTier.OUTSTANDING: 4.5,
    }

    # Celebration triggers
    CELEBRATIONS = {
        3.0: "You've reached the funding threshold!",
        3.5: "Your section is now competitive!",
        4.0: "Excellent! This section is strong!",
        4.5: "Outstanding! Top-tier quality!",
    }

    def __init__(self):
        self.quick_analyzer = RealTimeAnalyzer()
        self.evaluator = EvaluatorSimulator()
        self._score_cache: dict[str, tuple] = {}  # content_hash -> (score, timestamp)
        self._last_deep_analysis: dict[str, datetime] = {}
        self._previous_scores: dict[str, float] = {}  # section_id -> last known score

    async def stream_feedback(
        self, content: str, section_type: str, section_id: str, cluster: str | None = None
    ) -> AsyncGenerator[StreamingFeedback, None]:
        """
        Stream quality feedback for content.

        Yields multiple feedback items as analysis progresses:
        1. Quick score (instant)
        2. Suggestion count (instant)
        3. Quality tier (instant)
        4. Thinking status (if deep analysis)
        5. Full score (after deep analysis)
        6. Celebration (if applicable)

        Args:
            content: Current section content
            section_type: Type of section
            section_id: Section ID for tracking
            cluster: HE cluster for context

        Yields:
            StreamingFeedback items
        """
        content_hash = self._hash_content(content)

        # Step 1: Quick analysis (instant)
        quick_result = self.quick_analyzer.get_quick_feedback(content)

        # Yield suggestion count
        yield StreamingFeedback(
            type=FeedbackType.SUGGESTION_COUNT,
            value=quick_result.get("total", 0),
            message=f"{quick_result.get('total', 0)} suggestions",
        )

        # Step 2: Get cached or estimate score
        cached_score = self._get_cached_score(content_hash)

        if cached_score:
            estimated_score = cached_score
        else:
            # Quick score estimation based on heuristics
            estimated_score = self._estimate_quick_score(content, quick_result)

        # Yield quick score
        yield StreamingFeedback(
            type=FeedbackType.QUICK_SCORE,
            value=estimated_score,
            message=f"~{estimated_score:.1f}/5",
        )

        # Yield quality tier
        tier = self._get_quality_tier(estimated_score)
        yield StreamingFeedback(
            type=FeedbackType.QUALITY_TIER, value=tier.value, message=self._get_tier_message(tier)
        )

        # Step 3: Deep analysis if needed
        needs_deep_analysis = self._should_run_deep_analysis(
            section_id=section_id, content_hash=content_hash, content_length=len(content)
        )

        if needs_deep_analysis:
            # Yield thinking status
            yield StreamingFeedback(
                type=FeedbackType.THINKING, value=True, message="Analyzing content depth..."
            )

            # Get previous score for comparison
            previous_score = self._previous_scores.get(section_id)

            try:
                # Run full evaluation
                eval_result = await self.evaluator.simulate_evaluation(
                    content=content, section_type=section_type, cluster=cluster
                )

                new_score = eval_result.predicted_score

                # Cache the score
                self._cache_score(content_hash, new_score)
                self._last_deep_analysis[section_id] = datetime.now()
                self._previous_scores[section_id] = new_score

                # Yield full score
                yield StreamingFeedback(
                    type=FeedbackType.SCORE_UPDATE,
                    value={
                        "score": new_score,
                        "confidence": eval_result.confidence,
                        "criterion_scores": eval_result.criterion_scores,
                    },
                    message=f"Score: {new_score:.1f}/5",
                )

                # Yield thinking done
                yield StreamingFeedback(type=FeedbackType.THINKING, value=False)

                # Check for improvement
                if previous_score and new_score > previous_score:
                    improvement = new_score - previous_score
                    yield StreamingFeedback(
                        type=FeedbackType.IMPROVEMENT,
                        value={
                            "previous": previous_score,
                            "current": new_score,
                            "change": improvement,
                        },
                        message=f"+{improvement:.1f} improvement!",
                    )

                    # Check for celebration
                    celebration = self._check_celebration(previous_score, new_score)
                    if celebration:
                        yield StreamingFeedback(
                            type=FeedbackType.CELEBRATION,
                            value=celebration["threshold"],
                            message=celebration["message"],
                        )

            except Exception as e:
                logger.error(f"Deep analysis failed: {e}")
                # Yield thinking done even on error
                yield StreamingFeedback(type=FeedbackType.THINKING, value=False)

    def _hash_content(self, content: str) -> str:
        """Generate hash for content caching."""
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _get_cached_score(self, content_hash: str) -> float | None:
        """Get cached score if recent enough."""
        if content_hash in self._score_cache:
            score, timestamp = self._score_cache[content_hash]
            if datetime.now() - timestamp < timedelta(minutes=5):
                return score
        return None

    def _cache_score(self, content_hash: str, score: float):
        """Cache a score."""
        self._score_cache[content_hash] = (score, datetime.now())

        # Clean old entries
        cutoff = datetime.now() - timedelta(minutes=30)
        self._score_cache = {k: v for k, v in self._score_cache.items() if v[1] > cutoff}

    def _estimate_quick_score(self, content: str, quick_result: dict) -> float:
        """
        Quick score estimation based on heuristics.

        Factors:
        - Content length
        - Suggestion count
        - Sentence variety
        - Technical vocabulary
        """
        base_score = 2.5

        # Length bonus (up to 0.5)
        word_count = len(content.split())
        if word_count > 500:
            base_score += 0.5
        elif word_count > 300:
            base_score += 0.3
        elif word_count > 150:
            base_score += 0.1

        # Suggestion penalty (up to -0.5)
        suggestion_count = quick_result.get("total", 0)
        penalty = min(0.5, suggestion_count * 0.05)
        base_score -= penalty

        # Technical vocabulary bonus
        tech_terms = len(
            re.findall(
                r"\b(methodology|framework|innovative|impact|deliverable|milestone|objective|consortium)\b",
                content.lower(),
            )
        )
        base_score += min(0.3, tech_terms * 0.05)

        # EU terminology bonus
        eu_terms = len(
            re.findall(
                r"\b(horizon europe|green deal|digital|sustainable|EU|european)\b", content.lower()
            )
        )
        base_score += min(0.2, eu_terms * 0.05)

        return max(1.0, min(5.0, base_score))

    def _get_quality_tier(self, score: float) -> QualityTier:
        """Get quality tier for score."""
        for tier in reversed(list(QualityTier)):
            if score >= self.TIER_THRESHOLDS[tier]:
                return tier
        return QualityTier.POOR

    def _get_tier_message(self, tier: QualityTier) -> str:
        """Get message for quality tier."""
        messages = {
            QualityTier.POOR: "Needs significant work",
            QualityTier.THRESHOLD: "Approaching threshold",
            QualityTier.ACCEPTABLE: "At threshold level",
            QualityTier.GOOD: "Good quality",
            QualityTier.EXCELLENT: "Excellent quality",
            QualityTier.OUTSTANDING: "Outstanding!",
        }
        return messages[tier]

    def _should_run_deep_analysis(
        self, section_id: str, content_hash: str, content_length: int
    ) -> bool:
        """Determine if deep analysis should run."""
        # Skip if content too short
        if content_length < 200:
            return False

        # Skip if we have a recent cache
        if content_hash in self._score_cache:
            return False

        # Skip if we analyzed this section recently
        last_analysis = self._last_deep_analysis.get(section_id)
        if last_analysis and datetime.now() - last_analysis < timedelta(seconds=30):
            return False

        return True

    def _check_celebration(self, previous: float, current: float) -> dict[str, Any] | None:
        """Check if a celebration threshold was crossed."""
        for threshold, message in self.CELEBRATIONS.items():
            if previous < threshold <= current:
                return {"threshold": threshold, "message": message}
        return None


class StreamingQualityIndicator:
    """
    Manages the streaming quality indicator state.

    Provides a simple interface for UI components.
    """

    def __init__(self, section_id: str, section_type: str):
        self.section_id = section_id
        self.section_type = section_type
        self.service = RealTimeQualityService()
        self.current_score: float | None = None
        self.current_tier: QualityTier | None = None
        self.suggestion_count: int = 0
        self.is_analyzing: bool = False

    async def update(
        self,
        content: str,
        cluster: str | None = None,
        on_feedback: Callable[[StreamingFeedback], None] | None = None,
    ):
        """
        Update quality indicator with new content.

        Args:
            content: Current content
            cluster: HE cluster
            on_feedback: Callback for each feedback item
        """
        async for feedback in self.service.stream_feedback(
            content=content,
            section_type=self.section_type,
            section_id=self.section_id,
            cluster=cluster,
        ):
            # Update internal state
            if feedback.type == FeedbackType.QUICK_SCORE:
                self.current_score = feedback.value
            elif feedback.type == FeedbackType.QUALITY_TIER:
                self.current_tier = QualityTier(feedback.value)
            elif feedback.type == FeedbackType.SUGGESTION_COUNT:
                self.suggestion_count = feedback.value
            elif feedback.type == FeedbackType.THINKING:
                self.is_analyzing = feedback.value
            elif feedback.type == FeedbackType.SCORE_UPDATE:
                self.current_score = feedback.value["score"]

            # Callback
            if on_feedback:
                on_feedback(feedback)

    def get_state(self) -> dict[str, Any]:
        """Get current indicator state."""
        return {
            "score": self.current_score,
            "tier": self.current_tier.value if self.current_tier else None,
            "suggestion_count": self.suggestion_count,
            "is_analyzing": self.is_analyzing,
        }
