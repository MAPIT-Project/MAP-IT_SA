# Task 14: Streaming Real-Time Quality Feedback

> **Priority:** P2 (User Experience)
> **Estimated Effort:** 4-6 hours
> **Dependencies:** Task 08 (Evaluator), Task 13 (Inline Suggestions)
> **Status:** Not Started

---

## Problem Statement

Users want immediate feedback while writing, not just when they click "Evaluate". Current experience feels disconnected - write a lot, then wait for feedback.

### Current State
- Feedback only on manual trigger
- No progressive quality indicators
- No immediate response to changes
- Analysis feels slow and disconnected

### Target State
- Quality score updates as you type (with smart debouncing)
- Visual progress bar shows improvement
- Streaming "thinking" feedback during analysis
- Section health indicator always visible
- Celebratory feedback when score improves

---

## Implementation Plan

### Step 1: Real-Time Quality Service

**File:** `app/services/proposal_writing/realtime_quality_service.py`

```python
"""
Real-Time Quality Service

Provides streaming, incremental quality feedback during writing.
Uses lightweight analysis for instant feedback with periodic deep analysis.
"""

import asyncio
import logging
import hashlib
from typing import AsyncGenerator, Dict, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from app.services.proposal_writing.inline_suggestions_service import RealTimeAnalyzer
from app.services.proposal_writing.evaluator_simulator import EvaluatorSimulator
from app.services.database import get_db_connection

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """Types of streaming feedback."""
    QUICK_SCORE = "quick_score"         # Instant score estimate
    SUGGESTION_COUNT = "suggestion_count"  # Number of suggestions
    QUALITY_TIER = "quality_tier"       # threshold/good/excellent
    THINKING = "thinking"               # AI is analyzing
    SCORE_UPDATE = "score_update"       # Full score update
    IMPROVEMENT = "improvement"         # Score improved
    CELEBRATION = "celebration"         # Major milestone


class QualityTier(str, Enum):
    """Quality tier for visual indicator."""
    POOR = "poor"           # <2.5
    THRESHOLD = "threshold"  # 2.5-3.0
    ACCEPTABLE = "acceptable"  # 3.0-3.5
    GOOD = "good"           # 3.5-4.0
    EXCELLENT = "excellent"  # 4.0-4.5
    OUTSTANDING = "outstanding"  # >4.5


@dataclass
class StreamingFeedback:
    """A single piece of streaming feedback."""
    type: FeedbackType
    value: Any
    message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "value": self.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()
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
        3.0: "🎯 You've reached the funding threshold!",
        3.5: "📈 Your section is now competitive!",
        4.0: "⭐ Excellent! This section is strong!",
        4.5: "🏆 Outstanding! Top-tier quality!",
    }

    def __init__(self):
        self.quick_analyzer = RealTimeAnalyzer()
        self.evaluator = EvaluatorSimulator()
        self._score_cache: Dict[str, tuple] = {}  # content_hash -> (score, timestamp)
        self._last_deep_analysis: Dict[str, datetime] = {}

    async def stream_feedback(
        self,
        content: str,
        section_type: str,
        section_id: str,
        cluster: Optional[str] = None
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
        quick_result = await self.quick_analyzer.analyze_quick(content)

        # Yield suggestion count
        yield StreamingFeedback(
            type=FeedbackType.SUGGESTION_COUNT,
            value=len(quick_result.suggestions),
            message=f"{len(quick_result.suggestions)} suggestions"
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
            message=f"~{estimated_score:.1f}/5"
        )

        # Yield quality tier
        tier = self._get_quality_tier(estimated_score)
        yield StreamingFeedback(
            type=FeedbackType.QUALITY_TIER,
            value=tier.value,
            message=self._get_tier_message(tier)
        )

        # Step 3: Deep analysis if needed
        needs_deep_analysis = self._should_run_deep_analysis(
            section_id=section_id,
            content_hash=content_hash,
            content_length=len(content)
        )

        if needs_deep_analysis:
            # Yield thinking status
            yield StreamingFeedback(
                type=FeedbackType.THINKING,
                value=True,
                message="Analyzing content depth..."
            )

            # Get previous score for comparison
            previous_score = await self._get_previous_score(section_id)

            # Run full evaluation
            eval_result = await self.evaluator.simulate_evaluation(
                content=content,
                section_type=section_type,
                cluster=cluster
            )

            new_score = eval_result.predicted_score

            # Cache the score
            self._cache_score(content_hash, new_score)
            self._last_deep_analysis[section_id] = datetime.now()

            # Yield full score
            yield StreamingFeedback(
                type=FeedbackType.SCORE_UPDATE,
                value={
                    "score": new_score,
                    "confidence": eval_result.confidence,
                    "criterion_scores": eval_result.criterion_scores
                },
                message=f"Score: {new_score:.1f}/5"
            )

            # Yield thinking done
            yield StreamingFeedback(
                type=FeedbackType.THINKING,
                value=False
            )

            # Check for improvement
            if previous_score and new_score > previous_score:
                improvement = new_score - previous_score
                yield StreamingFeedback(
                    type=FeedbackType.IMPROVEMENT,
                    value={
                        "previous": previous_score,
                        "current": new_score,
                        "change": improvement
                    },
                    message=f"+{improvement:.1f} improvement!"
                )

                # Check for celebration
                celebration = self._check_celebration(previous_score, new_score)
                if celebration:
                    yield StreamingFeedback(
                        type=FeedbackType.CELEBRATION,
                        value=celebration['threshold'],
                        message=celebration['message']
                    )

    def _hash_content(self, content: str) -> str:
        """Generate hash for content caching."""
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _get_cached_score(self, content_hash: str) -> Optional[float]:
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
        self._score_cache = {
            k: v for k, v in self._score_cache.items()
            if v[1] > cutoff
        }

    def _estimate_quick_score(self, content: str, quick_result: Any) -> float:
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
        suggestion_count = len(quick_result.suggestions)
        penalty = min(0.5, suggestion_count * 0.05)
        base_score -= penalty

        # Technical vocabulary bonus
        import re
        tech_terms = len(re.findall(
            r'\b(methodology|framework|innovative|impact|deliverable|milestone|objective|consortium)\b',
            content.lower()
        ))
        base_score += min(0.3, tech_terms * 0.05)

        # EU terminology bonus
        eu_terms = len(re.findall(
            r'\b(horizon europe|green deal|digital|sustainable|EU|european)\b',
            content.lower()
        ))
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
        self,
        section_id: str,
        content_hash: str,
        content_length: int
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

    async def _get_previous_score(self, section_id: str) -> Optional[float]:
        """Get the previous score for a section."""
        async with get_db_connection() as conn:
            result = await conn.fetchval("""
                SELECT predicted_score
                FROM section_scores
                WHERE section_id = $1
            """, section_id)
            return float(result) if result else None

    def _check_celebration(
        self,
        previous: float,
        current: float
    ) -> Optional[Dict[str, Any]]:
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
        self.current_score: Optional[float] = None
        self.current_tier: Optional[QualityTier] = None
        self.suggestion_count: int = 0
        self.is_analyzing: bool = False

    async def update(
        self,
        content: str,
        cluster: Optional[str] = None,
        on_feedback: Callable[[StreamingFeedback], None] = None
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
            cluster=cluster
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
                self.current_score = feedback.value['score']

            # Callback
            if on_feedback:
                on_feedback(feedback)

    def get_state(self) -> Dict[str, Any]:
        """Get current indicator state."""
        return {
            "score": self.current_score,
            "tier": self.current_tier.value if self.current_tier else None,
            "suggestion_count": self.suggestion_count,
            "is_analyzing": self.is_analyzing
        }
```

### Step 2: WebSocket Endpoint for Streaming

**File:** `app/api/quality_stream_routes.py`

```python
"""
WebSocket and SSE endpoints for streaming quality feedback.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio
import json

from app.services.proposal_writing.realtime_quality_service import (
    RealTimeQualityService, StreamingFeedback
)

router = APIRouter(prefix="/api/proposal/quality", tags=["quality-stream"])


@router.websocket("/ws/{section_id}")
async def quality_websocket(websocket: WebSocket, section_id: str):
    """
    WebSocket endpoint for real-time quality feedback.

    Send content updates, receive streaming feedback.
    """
    await websocket.accept()
    service = RealTimeQualityService()

    try:
        while True:
            # Receive content update
            data = await websocket.receive_json()

            if data.get("type") == "analyze":
                content = data.get("content", "")
                section_type = data.get("section_type", "general")
                cluster = data.get("cluster")

                # Stream feedback back
                async for feedback in service.stream_feedback(
                    content=content,
                    section_type=section_type,
                    section_id=section_id,
                    cluster=cluster
                ):
                    await websocket.send_json(feedback.to_dict())

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass


@router.post("/stream/{section_id}")
async def quality_stream_sse(
    request: Request,
    section_id: str,
    content: str,
    section_type: str = "general",
    cluster: Optional[str] = None
):
    """
    Server-Sent Events endpoint for quality feedback.

    Alternative to WebSocket for simpler client implementation.
    """
    service = RealTimeQualityService()

    async def generate():
        async for feedback in service.stream_feedback(
            content=content,
            section_type=section_type,
            section_id=section_id,
            cluster=cluster
        ):
            yield f"data: {json.dumps(feedback.to_dict())}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/quick-score")
async def get_quick_score(
    content: str,
    section_type: str = "general"
):
    """
    Get quick score estimate (no streaming, instant response).

    Use for lightweight polling if WebSocket not available.
    """
    from app.services.proposal_writing.inline_suggestions_service import RealTimeAnalyzer

    analyzer = RealTimeAnalyzer()
    service = RealTimeQualityService()

    quick_result = await analyzer.analyze_quick(content)
    estimated_score = service._estimate_quick_score(content, quick_result)
    tier = service._get_quality_tier(estimated_score)

    return {
        "score": estimated_score,
        "tier": tier.value,
        "suggestion_count": len(quick_result.suggestions),
        "tier_message": service._get_tier_message(tier)
    }
```

### Step 3: React UI Components

**File:** `frontend/components/StreamingQualityIndicator.tsx`

```typescript
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { debounce } from 'lodash';
import confetti from 'canvas-confetti';

interface QualityState {
  score: number | null;
  tier: string | null;
  tierMessage: string | null;
  suggestionCount: number;
  isAnalyzing: boolean;
  lastImprovement: number | null;
}

interface StreamingQualityIndicatorProps {
  sectionId: string;
  sectionType: string;
  content: string;
  cluster?: string;
}

const TIER_COLORS: Record<string, string> = {
  poor: '#ef4444',
  threshold: '#f59e0b',
  acceptable: '#fbbf24',
  good: '#22c55e',
  excellent: '#10b981',
  outstanding: '#06b6d4',
};

const TIER_GRADIENTS: Record<string, string> = {
  poor: 'from-red-500 to-red-600',
  threshold: 'from-orange-400 to-orange-500',
  acceptable: 'from-yellow-400 to-yellow-500',
  good: 'from-green-400 to-green-500',
  excellent: 'from-emerald-400 to-emerald-500',
  outstanding: 'from-cyan-400 to-cyan-500',
};

export const StreamingQualityIndicator: React.FC<StreamingQualityIndicatorProps> = ({
  sectionId,
  sectionType,
  content,
  cluster
}) => {
  const [state, setState] = useState<QualityState>({
    score: null,
    tier: null,
    tierMessage: null,
    suggestionCount: 0,
    isAnalyzing: false,
    lastImprovement: null
  });

  const [celebrationMessage, setCelebrationMessage] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Connect to WebSocket
  const connect = useCallback(() => {
    const ws = new WebSocket(`ws://localhost:8000/api/proposal/quality/ws/${sectionId}`);

    ws.onopen = () => {
      console.log('Quality WebSocket connected');
    };

    ws.onmessage = (event) => {
      const feedback = JSON.parse(event.data);
      handleFeedback(feedback);
    };

    ws.onclose = () => {
      // Reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    };

    wsRef.current = ws;
  }, [sectionId]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  // Handle incoming feedback
  const handleFeedback = (feedback: any) => {
    switch (feedback.type) {
      case 'quick_score':
        setState(prev => ({ ...prev, score: feedback.value }));
        break;
      case 'suggestion_count':
        setState(prev => ({ ...prev, suggestionCount: feedback.value }));
        break;
      case 'quality_tier':
        setState(prev => ({
          ...prev,
          tier: feedback.value,
          tierMessage: feedback.message
        }));
        break;
      case 'thinking':
        setState(prev => ({ ...prev, isAnalyzing: feedback.value }));
        break;
      case 'score_update':
        setState(prev => ({ ...prev, score: feedback.value.score }));
        break;
      case 'improvement':
        setState(prev => ({ ...prev, lastImprovement: feedback.value.change }));
        // Clear after animation
        setTimeout(() => {
          setState(prev => ({ ...prev, lastImprovement: null }));
        }, 3000);
        break;
      case 'celebration':
        setCelebrationMessage(feedback.message);
        triggerCelebration();
        setTimeout(() => setCelebrationMessage(null), 5000);
        break;
    }
  };

  // Send content for analysis
  const analyzeContent = useCallback(
    debounce((text: string) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'analyze',
          content: text,
          section_type: sectionType,
          cluster
        }));
      }
    }, 500),
    [sectionType, cluster]
  );

  // Analyze when content changes
  useEffect(() => {
    if (content.length > 50) {
      analyzeContent(content);
    }
  }, [content, analyzeContent]);

  // Celebration confetti
  const triggerCelebration = () => {
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 }
    });
  };

  const gradientClass = state.tier ? TIER_GRADIENTS[state.tier] : 'from-gray-400 to-gray-500';
  const scoreColor = state.tier ? TIER_COLORS[state.tier] : '#9ca3af';

  return (
    <div className="relative">
      {/* Main indicator */}
      <div
        className={`
          flex items-center gap-3 p-3 rounded-lg shadow-sm
          bg-gradient-to-r ${gradientClass}
          transition-all duration-500
        `}
      >
        {/* Score circle */}
        <div className="relative">
          <div
            className="w-14 h-14 rounded-full bg-white flex items-center justify-center shadow-inner"
          >
            {state.isAnalyzing ? (
              <div className="animate-spin text-2xl">⏳</div>
            ) : (
              <span
                className="text-xl font-bold"
                style={{ color: scoreColor }}
              >
                {state.score?.toFixed(1) || '—'}
              </span>
            )}
          </div>

          {/* Improvement badge */}
          {state.lastImprovement && state.lastImprovement > 0 && (
            <div className="absolute -top-1 -right-1 bg-green-500 text-white text-xs px-1.5 py-0.5 rounded-full animate-bounce">
              +{state.lastImprovement.toFixed(1)}
            </div>
          )}
        </div>

        {/* Info */}
        <div className="text-white">
          <div className="font-medium">{state.tierMessage || 'Analyzing...'}</div>
          <div className="text-sm opacity-80">
            {state.suggestionCount > 0
              ? `${state.suggestionCount} suggestions`
              : 'No suggestions'}
          </div>
        </div>

        {/* Progress bar */}
        <div className="flex-1 ml-2">
          <div className="h-2 bg-white bg-opacity-30 rounded-full overflow-hidden">
            <div
              className="h-full bg-white transition-all duration-500"
              style={{ width: `${(state.score || 0) / 5 * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-white opacity-60 mt-1">
            <span>0</span>
            <span>5</span>
          </div>
        </div>
      </div>

      {/* Celebration overlay */}
      {celebrationMessage && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 rounded-lg animate-pulse">
          <div className="text-white text-lg font-bold px-4 py-2 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-lg shadow-lg">
            {celebrationMessage}
          </div>
        </div>
      )}
    </div>
  );
};

// Compact version for sidebar
export const CompactQualityIndicator: React.FC<{
  score: number | null;
  tier: string | null;
  isAnalyzing: boolean;
}> = ({ score, tier, isAnalyzing }) => {
  const color = tier ? TIER_COLORS[tier] : '#9ca3af';

  return (
    <div className="flex items-center gap-2">
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold"
        style={{ backgroundColor: color }}
      >
        {isAnalyzing ? '...' : score?.toFixed(1) || '—'}
      </div>
      <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full transition-all duration-500"
          style={{
            width: `${(score || 0) / 5 * 100}%`,
            backgroundColor: color
          }}
        />
      </div>
    </div>
  );
};

// Mini version for inline display
export const MiniQualityBadge: React.FC<{
  score: number | null;
  tier: string | null;
}> = ({ score, tier }) => {
  const color = tier ? TIER_COLORS[tier] : '#9ca3af';

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-white"
      style={{ backgroundColor: color }}
    >
      {score?.toFixed(1) || '—'}/5
    </span>
  );
};
```

### Step 4: Integration with Editor

**File:** `frontend/components/ProposalEditor.tsx` (partial)

```typescript
// Add to existing editor component

import { StreamingQualityIndicator } from './StreamingQualityIndicator';

export const ProposalEditor: React.FC<EditorProps> = ({
  section,
  onSave
}) => {
  const [content, setContent] = useState(section.content);

  return (
    <div className="flex flex-col h-full">
      {/* Quality indicator at top */}
      <div className="mb-4">
        <StreamingQualityIndicator
          sectionId={section.id}
          sectionType={section.type}
          content={content}
          cluster={section.cluster}
        />
      </div>

      {/* Editor area */}
      <div className="flex-1">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="w-full h-full p-4 border rounded-lg focus:ring-2 focus:ring-blue-300"
        />
      </div>

      {/* Save button */}
      <div className="mt-4">
        <button
          onClick={() => onSave(content)}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Save Section
        </button>
      </div>
    </div>
  );
};
```

---

## Testing Plan

```python
# tests/test_streaming_quality.py

import pytest
from app.services.proposal_writing.realtime_quality_service import (
    RealTimeQualityService, FeedbackType, QualityTier
)


class TestStreamingQuality:

    @pytest.fixture
    def service(self):
        return RealTimeQualityService()

    @pytest.mark.asyncio
    async def test_stream_feedback_yields_items(self, service):
        """Test that streaming yields multiple feedback items."""
        content = "Test content " * 50  # Make it long enough

        items = []
        async for feedback in service.stream_feedback(
            content=content,
            section_type="excellence_objectives",
            section_id="test-section"
        ):
            items.append(feedback)

        # Should have at least quick score, suggestion count, tier
        types = [item.type for item in items]
        assert FeedbackType.QUICK_SCORE in types
        assert FeedbackType.SUGGESTION_COUNT in types
        assert FeedbackType.QUALITY_TIER in types

    def test_quality_tier_calculation(self, service):
        """Test quality tier calculation."""
        assert service._get_quality_tier(1.0) == QualityTier.POOR
        assert service._get_quality_tier(2.8) == QualityTier.THRESHOLD
        assert service._get_quality_tier(3.2) == QualityTier.ACCEPTABLE
        assert service._get_quality_tier(3.7) == QualityTier.GOOD
        assert service._get_quality_tier(4.2) == QualityTier.EXCELLENT
        assert service._get_quality_tier(4.7) == QualityTier.OUTSTANDING

    def test_celebration_detection(self, service):
        """Test celebration threshold detection."""
        assert service._check_celebration(2.9, 3.1) is not None
        assert service._check_celebration(3.9, 4.1) is not None
        assert service._check_celebration(3.5, 3.7) is None  # No threshold crossed

    def test_quick_score_estimation(self, service):
        """Test quick score estimation."""
        from app.services.proposal_writing.inline_suggestions_service import RealTimeAnalyzer

        short_content = "Short text"
        long_content = "Long content with methodology and innovative approaches. " * 20

        # Mocked quick result
        class MockResult:
            suggestions = []

        short_score = service._estimate_quick_score(short_content, MockResult())
        long_score = service._estimate_quick_score(long_content, MockResult())

        # Longer content should score higher
        assert long_score > short_score
```

---

## Verification Checklist

- [ ] WebSocket connection establishes
- [ ] Quick score returns in <100ms
- [ ] Quality tier displays correctly
- [ ] Suggestion count updates
- [ ] Deep analysis triggers appropriately
- [ ] Score improvements are detected
- [ ] Celebrations trigger at thresholds
- [ ] Confetti animation works
- [ ] Reconnection works after disconnect
- [ ] UI updates smoothly without flicker

---

## Performance Notes

1. **Quick analysis**: <50ms (rule-based only)
2. **Deep analysis**: 2-3 seconds (with LLM)
3. **Debounce**: 500ms between updates
4. **Cache duration**: 5 minutes for scores
5. **Deep analysis interval**: Min 30 seconds between runs

---

## Accessibility

1. **Score announced**: Screen readers get score updates
2. **Color not sole indicator**: Text labels accompany colors
3. **Reduced motion**: Skip confetti if prefers-reduced-motion
4. **Keyboard**: All interactions keyboard accessible
