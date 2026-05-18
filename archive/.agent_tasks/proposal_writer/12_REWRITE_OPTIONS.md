# Task 12: Rewrite Options UI Integration

> **Priority:** P1 (Core Value)
> **Estimated Effort:** 4-6 hours
> **Dependencies:** Task 11 (Smart Rewriter)
> **Status:** Not Started

---

## Problem Statement

The Smart Rewriter (Task 11) generates multiple rewrite options, but users need a polished UI to:
1. Compare options side-by-side
2. See predicted score changes for each option
3. Mix and match parts from different rewrites
4. Easily accept or reject suggestions
5. Track which rewrites have been applied

### Current State
- No UI for displaying rewrite options
- No comparison view
- No way to select parts of different rewrites

### Target State
- Beautiful side-by-side comparison UI
- One-click accept for any option
- Diff view showing changes
- Score preview for each option
- Ability to customize before accepting

---

## Implementation Plan

### Step 1: Rewrite Options Service (Backend)

**File:** `app/services/proposal_writing/rewrite_options_service.py`

```python
"""
Rewrite Options Service

Manages the generation, storage, and application of rewrite options.
Coordinates between Smart Rewriter and UI layer.
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import difflib

from app.services.proposal_writing.smart_rewriter import SmartRewriter, RewriteResult
from app.services.proposal_writing.evaluator_simulator import EvaluatorSimulator
from app.services.database import get_db_connection

logger = logging.getLogger(__name__)


class RewriteStatus(str, Enum):
    """Status of a rewrite option."""
    PENDING = "pending"           # Generated, not yet acted upon
    ACCEPTED = "accepted"         # User accepted this rewrite
    REJECTED = "rejected"         # User rejected this rewrite
    PARTIALLY_USED = "partially_used"  # User used parts of this rewrite
    EXPIRED = "expired"           # Content changed, rewrite no longer valid


@dataclass
class RewriteOption:
    """A single rewrite option with metadata."""
    id: str
    style: str
    rewritten_text: str
    original_text: str
    predicted_score: float
    score_change: float
    key_changes: List[str]
    diff_html: str
    word_count_change: int
    status: RewriteStatus = RewriteStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class RewriteSession:
    """A session containing multiple rewrite options."""
    session_id: str
    section_id: str
    original_text: str
    original_score: float
    options: List[RewriteOption]
    recommended_option_id: Optional[str]
    created_at: datetime = field(default_factory=datetime.now)


class RewriteOptionsService:
    """
    Service for managing rewrite options lifecycle.

    Handles generation, storage, comparison, and application of rewrites.
    """

    def __init__(self):
        self.smart_rewriter = SmartRewriter()
        self.evaluator = EvaluatorSimulator()

    async def generate_options(
        self,
        section_id: str,
        content: str,
        section_type: str,
        styles: List[str] = None,
        cluster: Optional[str] = None,
        num_options: int = 3
    ) -> RewriteSession:
        """
        Generate multiple rewrite options for content.

        Args:
            section_id: The section being rewritten
            content: Original content
            section_type: Type of section
            styles: Specific styles to generate (default: auto-select)
            cluster: HE cluster for context
            num_options: Number of options to generate

        Returns:
            RewriteSession with all options
        """
        import uuid

        session_id = str(uuid.uuid4())

        # Get original score
        original_eval = await self.evaluator.simulate_evaluation(
            content=content,
            section_type=section_type,
            cluster=cluster
        )
        original_score = original_eval.predicted_score

        # Default styles if not specified
        if styles is None:
            styles = self._select_styles(original_score, section_type)[:num_options]

        # Generate rewrites for each style
        options = []
        for i, style in enumerate(styles):
            result = await self.smart_rewriter.rewrite_section(
                content=content,
                section_type=section_type,
                style=style,
                cluster=cluster
            )

            # Generate diff HTML
            diff_html = self._generate_diff_html(content, result.rewritten_text)

            # Calculate word count change
            original_words = len(content.split())
            new_words = len(result.rewritten_text.split())
            word_count_change = new_words - original_words

            option = RewriteOption(
                id=f"option_{i+1}",
                style=style,
                rewritten_text=result.rewritten_text,
                original_text=content,
                predicted_score=result.predicted_score,
                score_change=result.predicted_score - original_score,
                key_changes=result.key_changes,
                diff_html=diff_html,
                word_count_change=word_count_change
            )
            options.append(option)

        # Determine recommended option (highest predicted score)
        recommended = max(options, key=lambda o: o.predicted_score)

        session = RewriteSession(
            session_id=session_id,
            section_id=section_id,
            original_text=content,
            original_score=original_score,
            options=options,
            recommended_option_id=recommended.id
        )

        # Store session
        await self._store_session(session)

        return session

    def _select_styles(self, current_score: float, section_type: str) -> List[str]:
        """Select appropriate styles based on current score and section type."""
        # Low scores need fundamental improvements
        if current_score < 3.0:
            return ["clarity_first", "add_substance", "eu_alignment"]

        # Medium scores need polish
        elif current_score < 4.0:
            return ["impactful", "evaluator_friendly", "concise"]

        # High scores need fine-tuning
        else:
            return ["executive_polish", "technical_precision", "storytelling"]

    def _generate_diff_html(self, original: str, rewritten: str) -> str:
        """Generate HTML diff between original and rewritten text."""
        # Split into sentences for better diff
        import re
        original_sentences = re.split(r'(?<=[.!?])\s+', original)
        rewritten_sentences = re.split(r'(?<=[.!?])\s+', rewritten)

        diff = difflib.HtmlDiff()
        table = diff.make_table(
            original_sentences,
            rewritten_sentences,
            fromdesc='Original',
            todesc='Rewritten',
            context=True
        )

        return table

    def _generate_inline_diff(self, original: str, rewritten: str) -> str:
        """Generate inline diff with additions/deletions marked."""
        matcher = difflib.SequenceMatcher(None, original.split(), rewritten.split())
        result = []

        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == 'equal':
                result.extend(original.split()[i1:i2])
            elif op == 'delete':
                deleted = ' '.join(original.split()[i1:i2])
                result.append(f'<del class="bg-red-100 line-through">{deleted}</del>')
            elif op == 'insert':
                inserted = ' '.join(rewritten.split()[j1:j2])
                result.append(f'<ins class="bg-green-100">{inserted}</ins>')
            elif op == 'replace':
                deleted = ' '.join(original.split()[i1:i2])
                inserted = ' '.join(rewritten.split()[j1:j2])
                result.append(f'<del class="bg-red-100 line-through">{deleted}</del>')
                result.append(f'<ins class="bg-green-100">{inserted}</ins>')

        return ' '.join(result)

    async def _store_session(self, session: RewriteSession) -> None:
        """Store rewrite session in database."""
        async with get_db_connection() as conn:
            await conn.execute("""
                INSERT INTO rewrite_sessions (
                    id, section_id, original_text, original_score,
                    options_json, recommended_option_id, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                session.session_id,
                session.section_id,
                session.original_text,
                session.original_score,
                [o.__dict__ for o in session.options],
                session.recommended_option_id,
                session.created_at
            )

    async def apply_option(
        self,
        session_id: str,
        option_id: str,
        customized_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply a rewrite option to the section.

        Args:
            session_id: The rewrite session
            option_id: Which option to apply
            customized_text: Optional user-modified version

        Returns:
            Result with new content and score
        """
        session = await self._get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        option = next((o for o in session['options'] if o['id'] == option_id), None)
        if not option:
            raise ValueError(f"Option not found: {option_id}")

        # Use customized text or original rewrite
        final_text = customized_text or option['rewritten_text']

        # Update section content
        async with get_db_connection() as conn:
            await conn.execute("""
                UPDATE proposal_sections
                SET content = $1, updated_at = NOW()
                WHERE id = $2
            """, final_text, session['section_id'])

            # Mark option as accepted
            await conn.execute("""
                UPDATE rewrite_sessions
                SET applied_option_id = $1, applied_at = NOW()
                WHERE id = $2
            """, option_id, session_id)

        # Re-evaluate to get actual new score
        new_eval = await self.evaluator.simulate_evaluation(
            content=final_text,
            section_type=session.get('section_type', 'general')
        )

        return {
            "success": True,
            "new_content": final_text,
            "new_score": new_eval.predicted_score,
            "score_change": new_eval.predicted_score - session['original_score']
        }

    async def _get_session(self, session_id: str) -> Optional[Dict]:
        """Retrieve a rewrite session."""
        async with get_db_connection() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM rewrite_sessions WHERE id = $1
            """, session_id)
            return dict(row) if row else None

    async def merge_options(
        self,
        session_id: str,
        selections: Dict[str, str]
    ) -> str:
        """
        Merge parts from different options.

        Args:
            session_id: The rewrite session
            selections: Mapping of paragraph index to option_id

        Returns:
            Merged text
        """
        session = await self._get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Split each option into paragraphs
        option_paragraphs = {}
        for opt in session['options']:
            option_paragraphs[opt['id']] = opt['rewritten_text'].split('\n\n')

        # Build merged text
        merged = []
        for idx, option_id in sorted(selections.items(), key=lambda x: int(x[0])):
            idx = int(idx)
            if option_id in option_paragraphs and idx < len(option_paragraphs[option_id]):
                merged.append(option_paragraphs[option_id][idx])

        return '\n\n'.join(merged)
```

### Step 2: Database Schema

**File:** `migration/013_rewrite_sessions.sql`

```sql
-- Rewrite sessions tracking
CREATE TABLE IF NOT EXISTS rewrite_sessions (
    id UUID PRIMARY KEY,
    section_id UUID NOT NULL REFERENCES proposal_sections(id) ON DELETE CASCADE,

    -- Original state
    original_text TEXT NOT NULL,
    original_score DECIMAL(2,1) NOT NULL,

    -- Options
    options_json JSONB NOT NULL,
    recommended_option_id VARCHAR(50),

    -- Application
    applied_option_id VARCHAR(50),
    applied_at TIMESTAMP,
    customized BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '24 hours'
);

-- Rewrite analytics
CREATE TABLE IF NOT EXISTS rewrite_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES rewrite_sessions(id),
    section_id UUID REFERENCES proposal_sections(id),

    -- What happened
    action VARCHAR(20) NOT NULL,  -- viewed, compared, accepted, rejected, customized
    option_id VARCHAR(50),
    time_spent_seconds INT,

    -- Context
    style VARCHAR(50),
    predicted_score DECIMAL(2,1),
    actual_score_after DECIMAL(2,1),

    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_rewrite_sessions_section ON rewrite_sessions(section_id);
CREATE INDEX idx_rewrite_sessions_created ON rewrite_sessions(created_at);
CREATE INDEX idx_rewrite_analytics_session ON rewrite_analytics(session_id);

-- View for rewrite effectiveness
CREATE OR REPLACE VIEW v_rewrite_effectiveness AS
SELECT
    rs.id as session_id,
    rs.section_id,
    rs.original_score,
    rs.options_json->0->>'predicted_score' as option_1_predicted,
    rs.applied_option_id,
    (
        SELECT predicted_score
        FROM section_scores ss
        WHERE ss.section_id = rs.section_id
        ORDER BY created_at DESC LIMIT 1
    ) as final_score,
    EXTRACT(EPOCH FROM (rs.applied_at - rs.created_at)) as decision_time_seconds
FROM rewrite_sessions rs
WHERE rs.applied_option_id IS NOT NULL;

-- Function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_rewrite_sessions()
RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM rewrite_sessions
    WHERE expires_at < NOW()
    AND applied_option_id IS NULL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
```

### Step 3: API Endpoints

**File:** `app/api/rewrite_routes.py`

```python
"""
API routes for rewrite options.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from app.services.proposal_writing.rewrite_options_service import (
    RewriteOptionsService
)

router = APIRouter(prefix="/api/proposal/rewrite", tags=["rewrite"])


class GenerateOptionsRequest(BaseModel):
    section_id: str
    content: str = Field(..., min_length=100)
    section_type: str
    styles: Optional[List[str]] = None
    cluster: Optional[str] = None
    num_options: int = Field(3, ge=1, le=5)


class RewriteOptionResponse(BaseModel):
    id: str
    style: str
    rewritten_text: str
    predicted_score: float
    score_change: float
    key_changes: List[str]
    diff_html: str
    word_count_change: int


class RewriteSessionResponse(BaseModel):
    session_id: str
    section_id: str
    original_score: float
    options: List[RewriteOptionResponse]
    recommended_option_id: str


class ApplyOptionRequest(BaseModel):
    session_id: str
    option_id: str
    customized_text: Optional[str] = None


class ApplyOptionResponse(BaseModel):
    success: bool
    new_content: str
    new_score: float
    score_change: float


class MergeOptionsRequest(BaseModel):
    session_id: str
    selections: Dict[str, str]  # paragraph_index -> option_id


@router.post("/generate", response_model=RewriteSessionResponse)
async def generate_rewrite_options(request: GenerateOptionsRequest):
    """
    Generate multiple rewrite options for a section.

    Returns 3-5 different style variations with predicted scores.
    """
    service = RewriteOptionsService()

    try:
        session = await service.generate_options(
            section_id=request.section_id,
            content=request.content,
            section_type=request.section_type,
            styles=request.styles,
            cluster=request.cluster,
            num_options=request.num_options
        )

        return RewriteSessionResponse(
            session_id=session.session_id,
            section_id=session.section_id,
            original_score=session.original_score,
            options=[
                RewriteOptionResponse(
                    id=opt.id,
                    style=opt.style,
                    rewritten_text=opt.rewritten_text,
                    predicted_score=opt.predicted_score,
                    score_change=opt.score_change,
                    key_changes=opt.key_changes,
                    diff_html=opt.diff_html,
                    word_count_change=opt.word_count_change
                )
                for opt in session.options
            ],
            recommended_option_id=session.recommended_option_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply", response_model=ApplyOptionResponse)
async def apply_rewrite_option(request: ApplyOptionRequest):
    """
    Apply a rewrite option to update the section content.

    Optionally accepts customized text if user modified the suggestion.
    """
    service = RewriteOptionsService()

    try:
        result = await service.apply_option(
            session_id=request.session_id,
            option_id=request.option_id,
            customized_text=request.customized_text
        )

        return ApplyOptionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/merge")
async def merge_rewrite_options(request: MergeOptionsRequest):
    """
    Merge paragraphs from different rewrite options.

    Allows users to pick the best parts from each option.
    """
    service = RewriteOptionsService()

    try:
        merged_text = await service.merge_options(
            session_id=request.session_id,
            selections=request.selections
        )

        return {"merged_text": merged_text}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/styles")
async def get_available_styles():
    """Get list of available rewrite styles with descriptions."""
    return {
        "styles": [
            {
                "id": "concise",
                "name": "Concise & Clear",
                "description": "Shorter sentences, clearer language, removes fluff",
                "best_for": "Sections that are too long or unclear"
            },
            {
                "id": "impactful",
                "name": "Impactful",
                "description": "Stronger language, active voice, emphasizes significance",
                "best_for": "Impact sections, executive summaries"
            },
            {
                "id": "technical_precision",
                "name": "Technical Precision",
                "description": "More specific terms, adds methodology details",
                "best_for": "Methodology and implementation sections"
            },
            {
                "id": "eu_alignment",
                "name": "EU-Aligned",
                "description": "Adds EU policy references, uses official terminology",
                "best_for": "All sections, especially impact"
            },
            {
                "id": "evaluator_friendly",
                "name": "Evaluator-Friendly",
                "description": "Clear structure, explicit addressing of criteria",
                "best_for": "Sections scoring below threshold"
            },
            {
                "id": "storytelling",
                "name": "Narrative Flow",
                "description": "Better flow, smoother transitions, engaging tone",
                "best_for": "Excellence and overall narrative"
            },
            {
                "id": "add_substance",
                "name": "Add Substance",
                "description": "More specific details, examples, and evidence",
                "best_for": "Sections that feel too vague"
            },
            {
                "id": "executive_polish",
                "name": "Executive Polish",
                "description": "Professional tone, confident language, polished finish",
                "best_for": "Final review of high-scoring sections"
            }
        ]
    }


@router.post("/track-analytics")
async def track_rewrite_analytics(
    session_id: str,
    action: str,
    option_id: Optional[str] = None,
    time_spent_seconds: Optional[int] = None
):
    """Track user interaction with rewrite options for analytics."""
    from app.services.database import get_db_connection

    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO rewrite_analytics (session_id, action, option_id, time_spent_seconds)
            VALUES ($1, $2, $3, $4)
        """, session_id, action, option_id, time_spent_seconds)

    return {"status": "tracked"}
```

### Step 4: React UI Components

**File:** `frontend/components/RewriteOptions.tsx`

```typescript
import React, { useState, useEffect } from 'react';

interface RewriteOption {
  id: string;
  style: string;
  rewritten_text: string;
  predicted_score: float;
  score_change: float;
  key_changes: string[];
  diff_html: string;
  word_count_change: number;
}

interface RewriteOptionsProps {
  sessionId: string;
  originalText: string;
  originalScore: number;
  options: RewriteOption[];
  recommendedOptionId: string;
  onApply: (optionId: string, customizedText?: string) => void;
  onCancel: () => void;
}

export const RewriteOptions: React.FC<RewriteOptionsProps> = ({
  sessionId,
  originalText,
  originalScore,
  options,
  recommendedOptionId,
  onApply,
  onCancel
}) => {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'cards' | 'compare' | 'diff'>('cards');
  const [customizedText, setCustomizedText] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);

  // Track analytics
  useEffect(() => {
    fetch('/api/proposal/rewrite/track-analytics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, action: 'viewed' })
    });
  }, [sessionId]);

  const handleSelectOption = (optionId: string) => {
    setSelectedOption(optionId);
    const option = options.find(o => o.id === optionId);
    if (option) {
      setCustomizedText(option.rewritten_text);
    }
  };

  const handleApply = () => {
    if (selectedOption) {
      const option = options.find(o => o.id === selectedOption);
      const isCustomized = customizedText !== option?.rewritten_text;
      onApply(selectedOption, isCustomized ? customizedText : undefined);
    }
  };

  const getScoreColor = (change: number) => {
    if (change > 0.5) return 'text-green-600';
    if (change > 0) return 'text-green-500';
    if (change < 0) return 'text-red-500';
    return 'text-gray-500';
  };

  const getStyleIcon = (style: string) => {
    const icons: Record<string, string> = {
      concise: '✂️',
      impactful: '💪',
      technical_precision: '🔬',
      eu_alignment: '🇪🇺',
      evaluator_friendly: '👨‍⚖️',
      storytelling: '📖',
      add_substance: '📊',
      executive_polish: '✨'
    };
    return icons[style] || '📝';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-bold">Rewrite Options</h2>
              <p className="text-sm opacity-90">
                Current score: {originalScore.toFixed(1)}/5 • Choose a style to improve
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode('cards')}
                className={`px-3 py-1 rounded ${viewMode === 'cards' ? 'bg-white text-blue-600' : 'bg-blue-500'}`}
              >
                Cards
              </button>
              <button
                onClick={() => setViewMode('compare')}
                className={`px-3 py-1 rounded ${viewMode === 'compare' ? 'bg-white text-blue-600' : 'bg-blue-500'}`}
              >
                Compare
              </button>
              <button
                onClick={() => setViewMode('diff')}
                className={`px-3 py-1 rounded ${viewMode === 'diff' ? 'bg-white text-blue-600' : 'bg-blue-500'}`}
              >
                Diff
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 200px)' }}>
          {viewMode === 'cards' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {options.map(option => (
                <div
                  key={option.id}
                  onClick={() => handleSelectOption(option.id)}
                  className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                    selectedOption === option.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-blue-300'
                  } ${option.id === recommendedOptionId ? 'ring-2 ring-yellow-400' : ''}`}
                >
                  {/* Option Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{getStyleIcon(option.style)}</span>
                      <span className="font-medium capitalize">
                        {option.style.replace(/_/g, ' ')}
                      </span>
                    </div>
                    {option.id === recommendedOptionId && (
                      <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">
                        Recommended
                      </span>
                    )}
                  </div>

                  {/* Score Change */}
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-2xl font-bold">
                      {option.predicted_score.toFixed(1)}
                    </span>
                    <span className={`text-sm font-medium ${getScoreColor(option.score_change)}`}>
                      {option.score_change > 0 ? '+' : ''}{option.score_change.toFixed(1)}
                    </span>
                  </div>

                  {/* Key Changes */}
                  <div className="space-y-1 mb-3">
                    {option.key_changes.slice(0, 3).map((change, i) => (
                      <div key={i} className="text-sm text-gray-600 flex items-start gap-1">
                        <span className="text-green-500">✓</span>
                        <span>{change}</span>
                      </div>
                    ))}
                  </div>

                  {/* Word Count */}
                  <div className="text-xs text-gray-400">
                    {option.word_count_change > 0 ? '+' : ''}{option.word_count_change} words
                  </div>

                  {/* Preview */}
                  <div className="mt-3 p-2 bg-gray-50 rounded text-sm text-gray-600 line-clamp-3">
                    {option.rewritten_text.substring(0, 150)}...
                  </div>
                </div>
              ))}
            </div>
          )}

          {viewMode === 'compare' && selectedOption && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h3 className="font-medium mb-2 text-gray-600">Original</h3>
                <div className="bg-gray-50 p-4 rounded-lg text-sm whitespace-pre-wrap">
                  {originalText}
                </div>
              </div>
              <div>
                <h3 className="font-medium mb-2 text-blue-600">
                  {options.find(o => o.id === selectedOption)?.style.replace(/_/g, ' ')}
                </h3>
                <div className="bg-blue-50 p-4 rounded-lg text-sm whitespace-pre-wrap">
                  {isEditing ? (
                    <textarea
                      value={customizedText}
                      onChange={(e) => setCustomizedText(e.target.value)}
                      className="w-full h-64 p-2 border rounded"
                    />
                  ) : (
                    options.find(o => o.id === selectedOption)?.rewritten_text
                  )}
                </div>
                <button
                  onClick={() => setIsEditing(!isEditing)}
                  className="mt-2 text-sm text-blue-600 hover:underline"
                >
                  {isEditing ? 'Done Editing' : 'Edit Before Applying'}
                </button>
              </div>
            </div>
          )}

          {viewMode === 'diff' && selectedOption && (
            <div>
              <h3 className="font-medium mb-2">Changes Highlighted</h3>
              <div
                className="bg-gray-50 p-4 rounded-lg text-sm"
                dangerouslySetInnerHTML={{
                  __html: options.find(o => o.id === selectedOption)?.diff_html || ''
                }}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t p-4 flex justify-between items-center bg-gray-50">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <div className="flex gap-2">
            {selectedOption && (
              <>
                <span className="text-sm text-gray-500 self-center">
                  Selected: {options.find(o => o.id === selectedOption)?.style.replace(/_/g, ' ')}
                </span>
                <button
                  onClick={handleApply}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
                >
                  Apply This Rewrite
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Compact inline component for editor integration
export const RewriteButton: React.FC<{
  onGenerateOptions: () => void;
  isLoading: boolean;
}> = ({ onGenerateOptions, isLoading }) => {
  return (
    <button
      onClick={onGenerateOptions}
      disabled={isLoading}
      className="flex items-center gap-1 px-3 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200 disabled:opacity-50"
    >
      {isLoading ? (
        <>
          <span className="animate-spin">⏳</span>
          Generating...
        </>
      ) : (
        <>
          <span>✨</span>
          Rewrite Options
        </>
      )}
    </button>
  );
};
```

---

## Testing Plan

```python
# tests/test_rewrite_options.py

import pytest
from app.services.proposal_writing.rewrite_options_service import (
    RewriteOptionsService
)


class TestRewriteOptions:

    @pytest.fixture
    def service(self):
        return RewriteOptionsService()

    @pytest.mark.asyncio
    async def test_generate_options_returns_multiple(self, service):
        """Test that multiple options are generated."""
        content = """
        Our project aims to develop innovative solutions for urban mobility.
        We will work with partners across Europe to implement new technologies
        that reduce emissions and improve transportation efficiency.
        """

        session = await service.generate_options(
            section_id="test-section",
            content=content,
            section_type="excellence_objectives",
            num_options=3
        )

        assert len(session.options) == 3
        assert session.recommended_option_id is not None
        assert all(opt.predicted_score > 0 for opt in session.options)

    @pytest.mark.asyncio
    async def test_options_have_different_styles(self, service):
        """Test that options use different styles."""
        content = "Test content for rewriting with sufficient length to be meaningful."

        session = await service.generate_options(
            section_id="test",
            content=content * 5,
            section_type="impact",
            num_options=3
        )

        styles = [opt.style for opt in session.options]
        assert len(set(styles)) == len(styles)  # All unique

    def test_diff_generation(self, service):
        """Test that diff HTML is generated correctly."""
        original = "The project aims to improve efficiency."
        rewritten = "The innovative project aims to significantly improve energy efficiency."

        diff_html = service._generate_diff_html(original, rewritten)

        assert '<' in diff_html or 'del' in diff_html or 'ins' in diff_html
```

---

## Verification Checklist

- [ ] Multiple rewrite options are generated (3-5)
- [ ] Each option has a different style
- [ ] Predicted scores are calculated for each option
- [ ] Recommended option is highlighted
- [ ] Diff view shows changes clearly
- [ ] Side-by-side comparison works
- [ ] User can edit before applying
- [ ] Apply updates section content
- [ ] Analytics are tracked
- [ ] Sessions expire after 24 hours

---

## UI/UX Notes

1. **Card View**: Default for quick overview
2. **Compare View**: For detailed side-by-side analysis
3. **Diff View**: For precise change tracking
4. **Keyboard Shortcuts**:
   - `1-5`: Select option
   - `Enter`: Apply selected
   - `Esc`: Cancel
5. **Mobile**: Stack cards vertically, swipe to compare
