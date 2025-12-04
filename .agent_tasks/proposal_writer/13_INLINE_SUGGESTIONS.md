# Task 13: Grammarly-Style Inline Suggestions

> **Priority:** P1 (Core Value)
> **Estimated Effort:** 6-8 hours
> **Dependencies:** Task 02 (Structured LLM), Task 08 (Evaluator)
> **Status:** Not Started

---

## Problem Statement

Users need real-time, contextual feedback while writing - not just after they complete a section. Current experience requires manual "Evaluate" clicks and doesn't guide users at the sentence level.

### Current State
- Feedback only after manual evaluation
- No sentence-level suggestions
- No inline highlighting of issues
- No contextual tips while writing

### Target State
- Grammarly-style underlines for issues
- Hover to see suggestion
- One-click to accept fix
- Categorized by: EU terminology, clarity, impact, specificity
- Non-intrusive but always helpful

---

## Implementation Plan

### Step 1: Inline Analysis Service

**File:** `app/services/proposal_writing/inline_suggestions_service.py`

```python
"""
Inline Suggestions Service

Provides Grammarly-style inline suggestions for proposal text.
Analyzes sentences and phrases for improvement opportunities.
"""

import logging
import re
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.services.proposal_writing.proposal_ai_service import ProposalAIService

logger = logging.getLogger(__name__)


class SuggestionCategory(str, Enum):
    """Category of inline suggestion."""
    EU_TERMINOLOGY = "eu_terminology"       # Use official EU terms
    CLARITY = "clarity"                     # Clearer language
    SPECIFICITY = "specificity"             # More specific/quantified
    IMPACT = "impact"                       # Stronger impact language
    PASSIVE_VOICE = "passive_voice"         # Active voice preferred
    WORDINESS = "wordiness"                 # Can be more concise
    WEAK_VERB = "weak_verb"                 # Stronger verbs
    VAGUE_CLAIM = "vague_claim"             # Needs evidence/metrics
    MISSING_CONTEXT = "missing_context"     # Add context for evaluators
    FORMATTING = "formatting"               # Structure improvements


class SuggestionPriority(str, Enum):
    """Priority level of suggestion."""
    HIGH = "high"       # Significantly affects score
    MEDIUM = "medium"   # Noticeable improvement
    LOW = "low"         # Nice to have


@dataclass
class TextSpan:
    """A span of text in the document."""
    start: int      # Character offset from start
    end: int        # Character offset end
    text: str       # The actual text


@dataclass
class InlineSuggestion:
    """A single inline suggestion."""
    id: str
    span: TextSpan
    category: SuggestionCategory
    priority: SuggestionPriority
    message: str
    suggestion: str
    replacement: Optional[str]  # Direct replacement text
    learn_more: Optional[str]   # Link or explanation


@dataclass
class AnalysisResult:
    """Result of inline analysis."""
    suggestions: List[InlineSuggestion]
    score_impact: float  # Estimated impact if all accepted
    stats: Dict[str, int]  # Count by category


class InlineSuggestionsService:
    """
    Service for generating Grammarly-style inline suggestions.

    Combines rule-based checks with LLM analysis for comprehensive
    sentence-level feedback on proposal text.
    """

    # EU terminology replacements
    EU_TERMINOLOGY_MAP = {
        # General terms
        "project goals": "project objectives",
        "team members": "consortium partners",
        "results": "outcomes and deliverables",
        "partners": "consortium members",
        "money": "funding / EU contribution",
        "budget": "financial resources",
        "timeline": "project duration / Gantt chart",
        "plan": "work plan / methodology",

        # Impact terms
        "help": "contribute to / enable",
        "improve": "enhance / strengthen",
        "make better": "optimize / advance",
        "change": "transform / revolutionize",

        # Technical terms
        "new technology": "innovative solution / novel approach",
        "cutting edge": "state-of-the-art / beyond state-of-the-art",
        "research": "R&I activities / scientific investigation",

        # EU-specific
        "european union": "EU / European Union",
        "green deal": "European Green Deal",
        "horizon europe": "Horizon Europe programme",
    }

    # Weak verbs to strengthen
    WEAK_VERBS = {
        "do": ["implement", "execute", "conduct", "perform"],
        "make": ["develop", "create", "establish", "build"],
        "get": ["obtain", "acquire", "achieve", "secure"],
        "use": ["employ", "utilize", "leverage", "apply"],
        "have": ["possess", "demonstrate", "exhibit", "maintain"],
        "show": ["demonstrate", "illustrate", "evidence", "prove"],
        "give": ["provide", "deliver", "offer", "contribute"],
        "try": ["endeavor", "strive", "aim", "seek"],
    }

    # Vague words that need quantification
    VAGUE_WORDS = [
        "many", "several", "various", "significant",
        "substantial", "major", "important", "considerable",
        "some", "few", "most", "often", "usually",
        "greatly", "highly", "very", "really", "quite"
    ]

    # Passive voice patterns
    PASSIVE_PATTERNS = [
        r'\b(is|are|was|were|been|being)\s+\w+ed\b',
        r'\b(will be|has been|have been)\s+\w+ed\b',
    ]

    def __init__(self):
        self.ai_service = ProposalAIService()

    async def analyze_text(
        self,
        text: str,
        section_type: str,
        cluster: Optional[str] = None,
        include_llm_analysis: bool = True
    ) -> AnalysisResult:
        """
        Analyze text for inline suggestions.

        Args:
            text: The text to analyze
            section_type: Type of section for context
            cluster: HE cluster for terminology context
            include_llm_analysis: Whether to use LLM for deeper analysis

        Returns:
            AnalysisResult with all suggestions
        """
        suggestions = []

        # Step 1: Rule-based checks (fast, free)
        suggestions.extend(self._check_eu_terminology(text))
        suggestions.extend(self._check_weak_verbs(text))
        suggestions.extend(self._check_vague_words(text))
        suggestions.extend(self._check_passive_voice(text))
        suggestions.extend(self._check_wordiness(text))

        # Step 2: LLM-based analysis (slower, costs tokens)
        if include_llm_analysis and len(text) > 100:
            llm_suggestions = await self._llm_analysis(text, section_type, cluster)
            suggestions.extend(llm_suggestions)

        # Remove duplicates and overlapping suggestions
        suggestions = self._deduplicate_suggestions(suggestions)

        # Assign IDs
        for i, sug in enumerate(suggestions):
            sug.id = f"sug_{i+1}"

        # Calculate stats
        stats = self._calculate_stats(suggestions)

        # Estimate score impact
        score_impact = self._estimate_score_impact(suggestions)

        return AnalysisResult(
            suggestions=suggestions,
            score_impact=score_impact,
            stats=stats
        )

    def _check_eu_terminology(self, text: str) -> List[InlineSuggestion]:
        """Check for non-EU terminology."""
        suggestions = []

        for incorrect, correct in self.EU_TERMINOLOGY_MAP.items():
            pattern = re.compile(r'\b' + re.escape(incorrect) + r'\b', re.IGNORECASE)

            for match in pattern.finditer(text):
                suggestions.append(InlineSuggestion(
                    id="",
                    span=TextSpan(
                        start=match.start(),
                        end=match.end(),
                        text=match.group()
                    ),
                    category=SuggestionCategory.EU_TERMINOLOGY,
                    priority=SuggestionPriority.MEDIUM,
                    message=f"Consider using EU terminology: '{correct}'",
                    suggestion=f"Replace '{match.group()}' with '{correct}'",
                    replacement=correct,
                    learn_more="EU proposals use specific terminology that evaluators expect"
                ))

        return suggestions

    def _check_weak_verbs(self, text: str) -> List[InlineSuggestion]:
        """Check for weak verbs that could be stronger."""
        suggestions = []

        for weak, alternatives in self.WEAK_VERBS.items():
            # Match weak verb as whole word, not as part of compound
            pattern = re.compile(r'\b' + weak + r'\b(?!\s+(to|up|out|in|on))', re.IGNORECASE)

            for match in pattern.finditer(text):
                # Skip if it's part of a common phrase where the verb is appropriate
                context = text[max(0, match.start()-20):min(len(text), match.end()+20)]

                suggestions.append(InlineSuggestion(
                    id="",
                    span=TextSpan(
                        start=match.start(),
                        end=match.end(),
                        text=match.group()
                    ),
                    category=SuggestionCategory.WEAK_VERB,
                    priority=SuggestionPriority.LOW,
                    message=f"Consider a stronger verb",
                    suggestion=f"Try: {', '.join(alternatives[:3])}",
                    replacement=alternatives[0],
                    learn_more="Strong verbs convey action and capability more effectively"
                ))

        return suggestions

    def _check_vague_words(self, text: str) -> List[InlineSuggestion]:
        """Check for vague words that need quantification."""
        suggestions = []

        for vague in self.VAGUE_WORDS:
            pattern = re.compile(r'\b' + vague + r'\b', re.IGNORECASE)

            for match in pattern.finditer(text):
                suggestions.append(InlineSuggestion(
                    id="",
                    span=TextSpan(
                        start=match.start(),
                        end=match.end(),
                        text=match.group()
                    ),
                    category=SuggestionCategory.VAGUE_CLAIM,
                    priority=SuggestionPriority.MEDIUM,
                    message=f"'{match.group()}' is vague - can you quantify?",
                    suggestion="Add specific numbers, percentages, or metrics",
                    replacement=None,
                    learn_more="Evaluators prefer quantified claims (e.g., '30%' instead of 'significant')"
                ))

        return suggestions

    def _check_passive_voice(self, text: str) -> List[InlineSuggestion]:
        """Check for passive voice constructions."""
        suggestions = []

        for pattern in self.PASSIVE_PATTERNS:
            regex = re.compile(pattern, re.IGNORECASE)

            for match in regex.finditer(text):
                suggestions.append(InlineSuggestion(
                    id="",
                    span=TextSpan(
                        start=match.start(),
                        end=match.end(),
                        text=match.group()
                    ),
                    category=SuggestionCategory.PASSIVE_VOICE,
                    priority=SuggestionPriority.LOW,
                    message="Consider active voice for stronger impact",
                    suggestion="Rewrite to show who performs the action",
                    replacement=None,
                    learn_more="Active voice is more direct: 'We will develop...' vs 'will be developed'"
                ))

        return suggestions

    def _check_wordiness(self, text: str) -> List[InlineSuggestion]:
        """Check for wordy phrases."""
        wordy_phrases = {
            "in order to": "to",
            "due to the fact that": "because",
            "at this point in time": "now/currently",
            "in the event that": "if",
            "has the ability to": "can",
            "is able to": "can",
            "for the purpose of": "to/for",
            "in spite of the fact that": "although",
            "with regard to": "regarding/about",
            "in terms of": "regarding",
            "a large number of": "many",
            "the majority of": "most",
            "on a daily basis": "daily",
            "at the present time": "now/currently",
        }

        suggestions = []

        for wordy, concise in wordy_phrases.items():
            pattern = re.compile(r'\b' + re.escape(wordy) + r'\b', re.IGNORECASE)

            for match in pattern.finditer(text):
                suggestions.append(InlineSuggestion(
                    id="",
                    span=TextSpan(
                        start=match.start(),
                        end=match.end(),
                        text=match.group()
                    ),
                    category=SuggestionCategory.WORDINESS,
                    priority=SuggestionPriority.LOW,
                    message=f"Can be more concise: '{concise}'",
                    suggestion=f"Replace with '{concise}'",
                    replacement=concise,
                    learn_more="Concise writing is easier to read and stays within page limits"
                ))

        return suggestions

    async def _llm_analysis(
        self,
        text: str,
        section_type: str,
        cluster: Optional[str]
    ) -> List[InlineSuggestion]:
        """Use LLM for deeper semantic analysis."""
        prompt = f"""Analyze this proposal text for specific improvements.

SECTION TYPE: {section_type}
CLUSTER: {cluster or 'General'}

TEXT:
{text[:2000]}

Find 3-5 specific sentences or phrases that could be improved.
Focus on:
1. Claims that need evidence or quantification
2. Impact statements that could be stronger
3. Missing EU policy connections
4. Technical descriptions that need clarity
5. Weak conclusions or transitions

For each issue, provide the EXACT text span (copy the text exactly) and a specific improvement.

Respond with JSON:
{{
    "suggestions": [
        {{
            "original_text": "exact text from the document",
            "category": "specificity",
            "priority": "medium",
            "message": "Short explanation of issue",
            "suggestion": "How to fix it",
            "replacement": "Suggested replacement text (or null if complex)"
        }}
    ]
}}

Only include suggestions where you can identify the exact text span."""

        try:
            response = await self.ai_service.generate_structured(
                prompt=prompt,
                schema_name="inline_suggestions"
            )

            suggestions = []
            for sug_data in response.get('suggestions', []):
                # Find the text span
                original = sug_data.get('original_text', '')
                start = text.find(original)

                if start == -1:
                    continue  # Skip if we can't find exact text

                suggestions.append(InlineSuggestion(
                    id="",
                    span=TextSpan(
                        start=start,
                        end=start + len(original),
                        text=original
                    ),
                    category=SuggestionCategory(sug_data.get('category', 'clarity')),
                    priority=SuggestionPriority(sug_data.get('priority', 'medium')),
                    message=sug_data.get('message', ''),
                    suggestion=sug_data.get('suggestion', ''),
                    replacement=sug_data.get('replacement'),
                    learn_more=None
                ))

            return suggestions

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return []

    def _deduplicate_suggestions(
        self,
        suggestions: List[InlineSuggestion]
    ) -> List[InlineSuggestion]:
        """Remove duplicate and overlapping suggestions."""
        if not suggestions:
            return []

        # Sort by start position
        sorted_sugs = sorted(suggestions, key=lambda s: s.span.start)

        result = []
        for sug in sorted_sugs:
            # Check if overlaps with any existing suggestion
            overlaps = False
            for existing in result:
                if (sug.span.start < existing.span.end and
                    sug.span.end > existing.span.start):
                    # Keep higher priority one
                    priority_order = {
                        SuggestionPriority.HIGH: 3,
                        SuggestionPriority.MEDIUM: 2,
                        SuggestionPriority.LOW: 1
                    }
                    if priority_order[sug.priority] > priority_order[existing.priority]:
                        result.remove(existing)
                        result.append(sug)
                    overlaps = True
                    break

            if not overlaps:
                result.append(sug)

        return result

    def _calculate_stats(self, suggestions: List[InlineSuggestion]) -> Dict[str, int]:
        """Calculate suggestion statistics by category."""
        stats = {cat.value: 0 for cat in SuggestionCategory}

        for sug in suggestions:
            stats[sug.category.value] += 1

        return stats

    def _estimate_score_impact(self, suggestions: List[InlineSuggestion]) -> float:
        """Estimate potential score improvement if all suggestions accepted."""
        impact_weights = {
            SuggestionPriority.HIGH: 0.1,
            SuggestionPriority.MEDIUM: 0.05,
            SuggestionPriority.LOW: 0.02
        }

        total = sum(impact_weights[s.priority] for s in suggestions)
        return min(1.0, total)  # Cap at 1.0 point improvement


class RealTimeAnalyzer:
    """
    Lightweight analyzer for real-time feedback during typing.

    Uses only rule-based checks for instant response.
    """

    def __init__(self):
        self.service = InlineSuggestionsService()

    async def analyze_quick(self, text: str) -> AnalysisResult:
        """
        Quick analysis without LLM (for real-time use).

        Returns within ~10ms.
        """
        return await self.service.analyze_text(
            text=text,
            section_type="general",
            include_llm_analysis=False
        )

    def analyze_sentence(self, sentence: str) -> List[InlineSuggestion]:
        """Analyze a single sentence (synchronous, for typing)."""
        suggestions = []
        suggestions.extend(self.service._check_eu_terminology(sentence))
        suggestions.extend(self.service._check_vague_words(sentence))
        suggestions.extend(self.service._check_passive_voice(sentence))
        return suggestions
```

### Step 2: API Endpoints

**File:** `app/api/inline_suggestions_routes.py`

```python
"""
API routes for inline suggestions.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel, Field

from app.services.proposal_writing.inline_suggestions_service import (
    InlineSuggestionsService, RealTimeAnalyzer
)

router = APIRouter(prefix="/api/proposal/suggestions", tags=["suggestions"])


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=10)
    section_type: str = "general"
    cluster: Optional[str] = None
    include_llm: bool = True


class TextSpanResponse(BaseModel):
    start: int
    end: int
    text: str


class SuggestionResponse(BaseModel):
    id: str
    span: TextSpanResponse
    category: str
    priority: str
    message: str
    suggestion: str
    replacement: Optional[str]
    learn_more: Optional[str]


class AnalysisResponse(BaseModel):
    suggestions: List[SuggestionResponse]
    score_impact: float
    stats: dict


class QuickAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=5)


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(request: AnalyzeRequest):
    """
    Analyze text for inline suggestions.

    Combines rule-based checks with optional LLM analysis
    for comprehensive feedback.
    """
    service = InlineSuggestionsService()

    result = await service.analyze_text(
        text=request.text,
        section_type=request.section_type,
        cluster=request.cluster,
        include_llm_analysis=request.include_llm
    )

    return AnalysisResponse(
        suggestions=[
            SuggestionResponse(
                id=s.id,
                span=TextSpanResponse(
                    start=s.span.start,
                    end=s.span.end,
                    text=s.span.text
                ),
                category=s.category.value,
                priority=s.priority.value,
                message=s.message,
                suggestion=s.suggestion,
                replacement=s.replacement,
                learn_more=s.learn_more
            )
            for s in result.suggestions
        ],
        score_impact=result.score_impact,
        stats=result.stats
    )


@router.post("/analyze-quick", response_model=AnalysisResponse)
async def analyze_quick(request: QuickAnalyzeRequest):
    """
    Quick analysis for real-time feedback (no LLM).

    Use this for typing feedback - responds in <50ms.
    """
    analyzer = RealTimeAnalyzer()

    result = await analyzer.analyze_quick(request.text)

    return AnalysisResponse(
        suggestions=[
            SuggestionResponse(
                id=s.id,
                span=TextSpanResponse(
                    start=s.span.start,
                    end=s.span.end,
                    text=s.span.text
                ),
                category=s.category.value,
                priority=s.priority.value,
                message=s.message,
                suggestion=s.suggestion,
                replacement=s.replacement,
                learn_more=s.learn_more
            )
            for s in result.suggestions
        ],
        score_impact=result.score_impact,
        stats=result.stats
    )


@router.post("/accept/{suggestion_id}")
async def accept_suggestion(
    suggestion_id: str,
    section_id: str,
    original_text: str,
    replacement_text: str
):
    """
    Track when a suggestion is accepted.

    Used for analytics and improving suggestion quality.
    """
    from app.services.database import get_db_connection

    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO suggestion_analytics (
                suggestion_id, section_id, action,
                original_text, replacement_text, created_at
            ) VALUES ($1, $2, 'accepted', $3, $4, NOW())
        """, suggestion_id, section_id, original_text, replacement_text)

    return {"status": "tracked"}


@router.post("/dismiss/{suggestion_id}")
async def dismiss_suggestion(
    suggestion_id: str,
    section_id: str,
    reason: Optional[str] = None
):
    """Track when a suggestion is dismissed."""
    from app.services.database import get_db_connection

    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO suggestion_analytics (
                suggestion_id, section_id, action,
                dismiss_reason, created_at
            ) VALUES ($1, $2, 'dismissed', $3, NOW())
        """, suggestion_id, section_id, reason)

    return {"status": "tracked"}


@router.get("/categories")
async def get_suggestion_categories():
    """Get available suggestion categories with descriptions."""
    return {
        "categories": [
            {
                "id": "eu_terminology",
                "name": "EU Terminology",
                "description": "Use official European Union terminology",
                "icon": "🇪🇺",
                "color": "#003399"
            },
            {
                "id": "clarity",
                "name": "Clarity",
                "description": "Make the text clearer and easier to understand",
                "icon": "💡",
                "color": "#fbbf24"
            },
            {
                "id": "specificity",
                "name": "Specificity",
                "description": "Add specific details, numbers, or evidence",
                "icon": "🎯",
                "color": "#ef4444"
            },
            {
                "id": "impact",
                "name": "Impact",
                "description": "Strengthen impact statements",
                "icon": "💪",
                "color": "#10b981"
            },
            {
                "id": "passive_voice",
                "name": "Passive Voice",
                "description": "Consider using active voice",
                "icon": "✍️",
                "color": "#8b5cf6"
            },
            {
                "id": "wordiness",
                "name": "Wordiness",
                "description": "Can be more concise",
                "icon": "✂️",
                "color": "#6366f1"
            },
            {
                "id": "weak_verb",
                "name": "Weak Verb",
                "description": "Consider a stronger verb",
                "icon": "💪",
                "color": "#f59e0b"
            },
            {
                "id": "vague_claim",
                "name": "Vague Claim",
                "description": "Needs quantification or evidence",
                "icon": "❓",
                "color": "#ef4444"
            }
        ]
    }
```

### Step 3: React UI Components

**File:** `frontend/components/InlineEditor.tsx`

```typescript
import React, { useState, useEffect, useRef, useMemo } from 'react';
import { debounce } from 'lodash';

interface TextSpan {
  start: number;
  end: number;
  text: string;
}

interface Suggestion {
  id: string;
  span: TextSpan;
  category: string;
  priority: 'high' | 'medium' | 'low';
  message: string;
  suggestion: string;
  replacement: string | null;
  learn_more: string | null;
}

interface InlineEditorProps {
  initialContent: string;
  sectionType: string;
  cluster?: string;
  onChange: (content: string) => void;
  onSave: () => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  eu_terminology: '#003399',
  clarity: '#fbbf24',
  specificity: '#ef4444',
  impact: '#10b981',
  passive_voice: '#8b5cf6',
  wordiness: '#6366f1',
  weak_verb: '#f59e0b',
  vague_claim: '#ef4444',
};

const CATEGORY_ICONS: Record<string, string> = {
  eu_terminology: '🇪🇺',
  clarity: '💡',
  specificity: '🎯',
  impact: '💪',
  passive_voice: '✍️',
  wordiness: '✂️',
  weak_verb: '💪',
  vague_claim: '❓',
};

export const InlineEditor: React.FC<InlineEditorProps> = ({
  initialContent,
  sectionType,
  cluster,
  onChange,
  onSave
}) => {
  const [content, setContent] = useState(initialContent);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [activeSuggestion, setActiveSuggestion] = useState<Suggestion | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [hiddenCategories, setHiddenCategories] = useState<Set<string>>(new Set());
  const editorRef = useRef<HTMLDivElement>(null);

  // Debounced analysis
  const analyzeContent = useMemo(
    () =>
      debounce(async (text: string) => {
        if (text.length < 50) return;

        setIsAnalyzing(true);
        try {
          const response = await fetch('/api/proposal/suggestions/analyze-quick', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
          });
          const data = await response.json();
          setSuggestions(data.suggestions);
        } catch (error) {
          console.error('Analysis failed:', error);
        } finally {
          setIsAnalyzing(false);
        }
      }, 500),
    []
  );

  // Full analysis with LLM
  const runFullAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      const response = await fetch('/api/proposal/suggestions/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: content,
          section_type: sectionType,
          cluster,
          include_llm: true
        })
      });
      const data = await response.json();
      setSuggestions(data.suggestions);
    } catch (error) {
      console.error('Full analysis failed:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Analyze on content change
  useEffect(() => {
    analyzeContent(content);
  }, [content, analyzeContent]);

  const handleContentChange = (e: React.FormEvent<HTMLDivElement>) => {
    const newContent = e.currentTarget.innerText;
    setContent(newContent);
    onChange(newContent);
  };

  const handleAcceptSuggestion = async (suggestion: Suggestion) => {
    if (!suggestion.replacement) return;

    // Replace text
    const newContent =
      content.substring(0, suggestion.span.start) +
      suggestion.replacement +
      content.substring(suggestion.span.end);

    setContent(newContent);
    onChange(newContent);
    setActiveSuggestion(null);

    // Remove this suggestion
    setSuggestions(prev => prev.filter(s => s.id !== suggestion.id));

    // Track acceptance
    await fetch(`/api/proposal/suggestions/accept/${suggestion.id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        section_id: 'current',
        original_text: suggestion.span.text,
        replacement_text: suggestion.replacement
      })
    });
  };

  const handleDismissSuggestion = async (suggestion: Suggestion) => {
    setSuggestions(prev => prev.filter(s => s.id !== suggestion.id));
    setActiveSuggestion(null);

    await fetch(`/api/proposal/suggestions/dismiss/${suggestion.id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ section_id: 'current' })
    });
  };

  const toggleCategory = (category: string) => {
    setHiddenCategories(prev => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  // Render text with underlines
  const renderHighlightedContent = () => {
    const visibleSuggestions = suggestions.filter(
      s => !hiddenCategories.has(s.category)
    );

    if (visibleSuggestions.length === 0) {
      return content;
    }

    // Sort by position
    const sorted = [...visibleSuggestions].sort((a, b) => a.span.start - b.span.start);

    const parts: React.ReactNode[] = [];
    let lastEnd = 0;

    sorted.forEach((sug, i) => {
      // Text before this suggestion
      if (sug.span.start > lastEnd) {
        parts.push(content.substring(lastEnd, sug.span.start));
      }

      // The suggestion span
      const underlineColor = CATEGORY_COLORS[sug.category] || '#ef4444';
      const isHigh = sug.priority === 'high';

      parts.push(
        <span
          key={sug.id}
          className={`cursor-pointer relative ${
            activeSuggestion?.id === sug.id ? 'bg-yellow-100' : ''
          }`}
          style={{
            borderBottom: `2px ${isHigh ? 'solid' : 'dashed'} ${underlineColor}`,
            paddingBottom: '2px'
          }}
          onClick={() => setActiveSuggestion(sug)}
          onMouseEnter={() => setActiveSuggestion(sug)}
        >
          {sug.span.text}
        </span>
      );

      lastEnd = sug.span.end;
    });

    // Remaining text
    if (lastEnd < content.length) {
      parts.push(content.substring(lastEnd));
    }

    return parts;
  };

  // Get suggestion stats
  const stats = useMemo(() => {
    const counts: Record<string, number> = {};
    suggestions.forEach(s => {
      counts[s.category] = (counts[s.category] || 0) + 1;
    });
    return counts;
  }, [suggestions]);

  return (
    <div className="flex gap-4">
      {/* Editor */}
      <div className="flex-1">
        {/* Toolbar */}
        <div className="flex items-center gap-2 mb-2 p-2 bg-gray-100 rounded-t">
          <button
            onClick={runFullAnalysis}
            disabled={isAnalyzing}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {isAnalyzing ? '🔍 Analyzing...' : '🔍 Deep Analysis'}
          </button>

          <div className="flex-1" />

          {/* Category filters */}
          <div className="flex gap-1">
            {Object.entries(stats).map(([cat, count]) => (
              <button
                key={cat}
                onClick={() => toggleCategory(cat)}
                className={`px-2 py-1 rounded text-xs flex items-center gap-1 ${
                  hiddenCategories.has(cat)
                    ? 'bg-gray-200 text-gray-500'
                    : 'bg-white border'
                }`}
                style={{
                  borderColor: hiddenCategories.has(cat) ? undefined : CATEGORY_COLORS[cat]
                }}
              >
                <span>{CATEGORY_ICONS[cat]}</span>
                <span>{count}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Editable area */}
        <div
          ref={editorRef}
          contentEditable
          className="min-h-[400px] p-4 border rounded-b bg-white focus:outline-none focus:ring-2 focus:ring-blue-300"
          onInput={handleContentChange}
          suppressContentEditableWarning
        >
          {renderHighlightedContent()}
        </div>
      </div>

      {/* Suggestion panel */}
      {activeSuggestion && (
        <div className="w-80 bg-white border rounded-lg shadow-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xl">{CATEGORY_ICONS[activeSuggestion.category]}</span>
            <span
              className="text-sm font-medium capitalize"
              style={{ color: CATEGORY_COLORS[activeSuggestion.category] }}
            >
              {activeSuggestion.category.replace(/_/g, ' ')}
            </span>
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                activeSuggestion.priority === 'high'
                  ? 'bg-red-100 text-red-700'
                  : activeSuggestion.priority === 'medium'
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-gray-100 text-gray-700'
              }`}
            >
              {activeSuggestion.priority}
            </span>
          </div>

          <p className="text-gray-700 mb-3">{activeSuggestion.message}</p>

          <div className="bg-gray-50 p-2 rounded mb-3">
            <div className="text-xs text-gray-500 mb-1">Original:</div>
            <div className="text-sm line-through text-red-600">
              {activeSuggestion.span.text}
            </div>
          </div>

          {activeSuggestion.replacement && (
            <div className="bg-green-50 p-2 rounded mb-3">
              <div className="text-xs text-gray-500 mb-1">Suggestion:</div>
              <div className="text-sm text-green-700">
                {activeSuggestion.replacement}
              </div>
            </div>
          )}

          <p className="text-sm text-gray-600 mb-4">{activeSuggestion.suggestion}</p>

          {activeSuggestion.learn_more && (
            <p className="text-xs text-gray-500 mb-4 italic">
              💡 {activeSuggestion.learn_more}
            </p>
          )}

          <div className="flex gap-2">
            {activeSuggestion.replacement && (
              <button
                onClick={() => handleAcceptSuggestion(activeSuggestion)}
                className="flex-1 px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600"
              >
                ✓ Accept
              </button>
            )}
            <button
              onClick={() => handleDismissSuggestion(activeSuggestion)}
              className="flex-1 px-3 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            >
              ✕ Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
```

### Step 4: Database for Analytics

**File:** `migration/014_suggestion_analytics.sql`

```sql
-- Track suggestion acceptance/dismissal for learning
CREATE TABLE IF NOT EXISTS suggestion_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suggestion_id VARCHAR(50) NOT NULL,
    section_id UUID,

    action VARCHAR(20) NOT NULL,  -- accepted, dismissed
    original_text TEXT,
    replacement_text TEXT,
    dismiss_reason TEXT,

    category VARCHAR(50),
    priority VARCHAR(20),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_suggestion_analytics_action ON suggestion_analytics(action);
CREATE INDEX idx_suggestion_analytics_category ON suggestion_analytics(category);

-- View for suggestion effectiveness
CREATE OR REPLACE VIEW v_suggestion_effectiveness AS
SELECT
    category,
    COUNT(*) as total_shown,
    COUNT(*) FILTER (WHERE action = 'accepted') as accepted,
    COUNT(*) FILTER (WHERE action = 'dismissed') as dismissed,
    ROUND(
        COUNT(*) FILTER (WHERE action = 'accepted')::DECIMAL /
        NULLIF(COUNT(*), 0) * 100, 1
    ) as acceptance_rate
FROM suggestion_analytics
GROUP BY category
ORDER BY acceptance_rate DESC;
```

---

## Testing Plan

```python
# tests/test_inline_suggestions.py

import pytest
from app.services.proposal_writing.inline_suggestions_service import (
    InlineSuggestionsService, SuggestionCategory
)


class TestInlineSuggestions:

    @pytest.fixture
    def service(self):
        return InlineSuggestionsService()

    def test_eu_terminology_detection(self, service):
        """Test detection of non-EU terminology."""
        text = "The project goals include helping team members."

        suggestions = service._check_eu_terminology(text)

        assert len(suggestions) >= 2
        terms_found = [s.span.text.lower() for s in suggestions]
        assert "project goals" in terms_found or "team members" in terms_found

    def test_vague_word_detection(self, service):
        """Test detection of vague words."""
        text = "We will achieve significant improvements in many areas."

        suggestions = service._check_vague_words(text)

        assert len(suggestions) >= 2
        words_found = [s.span.text.lower() for s in suggestions]
        assert "significant" in words_found
        assert "many" in words_found

    def test_wordiness_detection(self, service):
        """Test detection of wordy phrases."""
        text = "In order to achieve results, we need to work hard."

        suggestions = service._check_wordiness(text)

        assert len(suggestions) >= 1
        assert any("in order to" in s.span.text.lower() for s in suggestions)

    @pytest.mark.asyncio
    async def test_full_analysis(self, service):
        """Test full analysis with all checks."""
        text = """
        The project goals are to help team members achieve significant
        improvements. In order to do this, we will use various methods
        that have been developed by our partners.
        """

        result = await service.analyze_text(
            text=text,
            section_type="excellence_objectives",
            include_llm_analysis=False
        )

        assert len(result.suggestions) > 0
        assert result.score_impact > 0
        assert sum(result.stats.values()) == len(result.suggestions)
```

---

## Verification Checklist

- [ ] Rule-based checks complete in <50ms
- [ ] EU terminology suggestions are accurate
- [ ] Vague word detection works
- [ ] Passive voice patterns are found
- [ ] Wordiness phrases are detected
- [ ] LLM analysis adds value beyond rules
- [ ] Suggestions don't overlap
- [ ] Accept replaces text correctly
- [ ] Dismiss removes suggestion
- [ ] Analytics are tracked
- [ ] UI underlines display correctly

---

## Performance Considerations

1. **Quick analysis** (rule-based only): <50ms
2. **Full analysis** (with LLM): 2-3 seconds
3. **Debounce typing**: 500ms delay
4. **Cache LLM results**: 5 minutes per text hash
5. **Limit suggestions**: Max 20 per section

---

## Future Improvements

1. **Learn from user behavior**: Adjust suggestion priority based on acceptance rates
2. **Custom dictionary**: Allow users to add their own terminology
3. **Section-specific rules**: Different rules for Excellence vs Impact
4. **Keyboard shortcuts**: Tab to accept, Esc to dismiss
5. **Bulk accept**: Accept all suggestions of a category
