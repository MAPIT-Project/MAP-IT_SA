# Task 11: Build Smart Rewriter Service

> **Phase:** 3 - Smart Rewriting
> **Priority:** P1 (Core Value)
> **Estimated Effort:** 6-8 hours
> **Status:** Not Started
> **Depends On:** Tasks 01-04, 05, 08

---

## Problem Statement

Current system only provides suggestions like:
- "Consider adding TRL information"
- "Use stronger action verbs"
- "Add more EU terminology"

Users still have to **manually rewrite everything**. This is:
- Time-consuming
- Requires expertise they may not have
- Often results in suboptimal rewrites

---

## Solution: Smart Rewriter

Instead of suggestions, provide **actual rewritten versions**:
- Multiple options (concise, impactful, EU-aligned)
- Before/after with explanations
- Style transfer from successful proposals
- One-click apply

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SMART REWRITER SERVICE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐   │
│  │  Single       │  │  Multi-Option │  │  Style Transfer       │   │
│  │  Rewriter     │  │  Generator    │  │  Engine               │   │
│  │               │  │               │  │                       │   │
│  │ Focus on one  │  │ 3 different   │  │ Match style of        │   │
│  │ improvement   │  │ rewrites:     │  │ successful proposals  │   │
│  │ aspect        │  │ • Concise     │  │                       │   │
│  │               │  │ • Impactful   │  │                       │   │
│  │               │  │ • EU-aligned  │  │                       │   │
│  └───────────────┘  └───────────────┘  └───────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     COMPARISON ENGINE                        │   │
│  │                                                              │   │
│  │  • Before/after diffs                                       │   │
│  │  • Word count changes                                       │   │
│  │  • Score predictions for each version                       │   │
│  │  • Explanation of changes                                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation

### Step 1: Create Smart Rewriter Service

**File:** `app/services/proposal_writing/smart_rewriter.py`

```python
"""
Smart Rewriter Service

Provide actual rewritten content, not just suggestions.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.services.proposal_writing.proposal_ai_service import ProposalAIService
from app.services.proposal_writing.schemas.ai_schemas import REWRITE_SCHEMA
from app.services.proposal_writing.proposal_learning_service import ProposalLearningService

logger = logging.getLogger(__name__)


class RewriteStyle(Enum):
    CONCISE = "concise"  # Shorter, more direct
    IMPACTFUL = "impactful"  # Stronger language, more persuasive
    EU_ALIGNED = "eu_aligned"  # More EU terminology and policy alignment
    TECHNICAL = "technical"  # More technical depth
    ACCESSIBLE = "accessible"  # Simpler language, clearer structure


@dataclass
class RewriteResult:
    """Result of a rewrite operation."""
    original_text: str
    rewritten_text: str
    style: str
    changes_made: List[str]
    before_after_examples: List[Dict[str, str]]
    improvement_summary: str
    word_count_original: int
    word_count_rewritten: int
    predicted_score_improvement: float


class SmartRewriter:
    """
    Provide actual rewritten versions of proposal text.

    Features:
    - Single-focus rewrites (clarity, impact, EU alignment)
    - Multi-option generation (3 different versions)
    - Style transfer from successful proposals
    - Before/after explanations
    """

    def __init__(self):
        self.ai_service = ProposalAIService()
        self.learning_service = ProposalLearningService()

    # =========================================================================
    # SINGLE-FOCUS REWRITING
    # =========================================================================

    async def rewrite_for_improvement(
        self,
        original_text: str,
        improvement_focus: str,
        section_type: str = "objectives",
        preserve_length: bool = False
    ) -> RewriteResult:
        """
        Rewrite text focusing on a specific improvement.

        Args:
            original_text: Original section text
            improvement_focus: What to improve (e.g., "clarity", "impact", "EU terminology")
            section_type: Type of section
            preserve_length: Try to maintain similar word count

        Returns:
            RewriteResult with rewritten text and explanations
        """

        logger.info(f"Rewriting for: {improvement_focus}")

        length_instruction = ""
        if preserve_length:
            word_count = len(original_text.split())
            length_instruction = f"\nMaintain approximately {word_count} words (±10%)."

        prompt = f"""You are an expert Horizon Europe proposal editor.

TASK: Rewrite this proposal section to improve: {improvement_focus}

ORIGINAL TEXT:
{original_text}

REQUIREMENTS:
1. Keep the core meaning and technical content intact
2. Focus specifically on improving {improvement_focus}
3. Maintain professional EU proposal style
4. Make the changes impactful but not excessive
{length_instruction}

IMPROVEMENT FOCUS "{improvement_focus}" MEANS:
{self._get_improvement_guidance(improvement_focus)}

Provide your response with:
1. The complete rewritten text
2. A list of specific changes made
3. 2-3 before/after examples showing key improvements
4. A 2-3 sentence summary of improvements"""

        try:
            result = await self.ai_service.generate_structured(
                prompt=prompt,
                response_schema=REWRITE_SCHEMA,
                temperature=0.4
            )

            return RewriteResult(
                original_text=original_text,
                rewritten_text=result.get("rewritten_text", original_text),
                style=improvement_focus,
                changes_made=result.get("changes_made", []),
                before_after_examples=result.get("before_after_examples", []),
                improvement_summary=result.get("improvement_summary", ""),
                word_count_original=len(original_text.split()),
                word_count_rewritten=len(result.get("rewritten_text", "").split()),
                predicted_score_improvement=0.3  # Estimated
            )

        except Exception as e:
            logger.error(f"Rewrite failed: {e}")
            raise

    def _get_improvement_guidance(self, focus: str) -> str:
        """Get specific guidance for improvement focus."""

        guidance = {
            "clarity": """
- Break long sentences into shorter ones (target 15-20 words)
- Replace vague terms with specific ones
- Improve logical flow between ideas
- Add clear topic sentences to paragraphs
- Remove unnecessary jargon""",

            "impact": """
- Use stronger action verbs (develop, create, transform, pioneer)
- Replace passive voice with active voice
- Add quantifiable outcomes where possible
- Emphasize breakthrough potential
- Strengthen claims with evidence references""",

            "EU terminology": """
- Add key EU terms: TRL, KPIs, deliverables, milestones, work packages
- Reference EU strategies: European Green Deal, Digital Europe, etc.
- Add "European added value" messaging
- Include stakeholder engagement language
- Reference relevant EU regulations and frameworks""",

            "conciseness": """
- Remove redundant phrases
- Eliminate unnecessary qualifiers (very, really, quite)
- Combine related ideas
- Remove tangential content
- Focus on essential information only""",

            "structure": """
- Add clear headings and subheadings
- Use bullet points for lists
- Improve paragraph organization
- Add transition sentences
- Create logical flow from problem to solution to impact""",

            "persuasiveness": """
- Lead with strongest arguments
- Add evidence and examples
- Address potential concerns proactively
- Use confident language (will, shall instead of might, could)
- End sections with strong impact statements"""
        }

        return guidance.get(focus, guidance["clarity"])

    # =========================================================================
    # MULTI-OPTION GENERATION
    # =========================================================================

    async def generate_rewrite_options(
        self,
        original_text: str,
        section_type: str = "objectives"
    ) -> Dict[str, RewriteResult]:
        """
        Generate multiple rewrite options for user to choose from.

        Returns three different versions:
        - Concise: Shorter, more direct
        - Impactful: Stronger language
        - EU-aligned: More EU terminology

        Args:
            original_text: Original section text
            section_type: Type of section

        Returns:
            Dict with 'concise', 'impactful', 'eu_aligned' keys
        """

        logger.info("Generating rewrite options")

        # Run all three rewrites in parallel
        results = await asyncio.gather(
            self.rewrite_for_improvement(
                original_text, "conciseness", section_type, preserve_length=False
            ),
            self.rewrite_for_improvement(
                original_text, "impact", section_type, preserve_length=True
            ),
            self.rewrite_for_improvement(
                original_text, "EU terminology", section_type, preserve_length=True
            ),
            return_exceptions=True
        )

        options = {}

        if not isinstance(results[0], Exception):
            options["concise"] = results[0]
        if not isinstance(results[1], Exception):
            options["impactful"] = results[1]
        if not isinstance(results[2], Exception):
            options["eu_aligned"] = results[2]

        return options

    # =========================================================================
    # STYLE TRANSFER
    # =========================================================================

    async def rewrite_like_successful_proposal(
        self,
        original_text: str,
        cluster: str = None,
        action_type: str = None,
        section_type: str = "objectives"
    ) -> RewriteResult:
        """
        Rewrite text using style from successful funded proposals.

        Finds similar funded projects and uses their language patterns
        to improve the user's text.
        """

        logger.info(f"Rewriting using style from funded {cluster or 'any cluster'} projects")

        # Find similar funded projects
        similar = await self.learning_service.find_similar_funded_projects(
            user_idea=original_text,
            cluster=cluster,
            action_type=action_type,
            limit=5
        )

        if not similar:
            # Fallback to regular rewrite
            return await self.rewrite_for_improvement(
                original_text, "impact", section_type
            )

        # Extract example excerpts
        examples = [p.objective[:800] for p in similar[:3] if p.objective]

        prompt = f"""You are an expert Horizon Europe proposal editor.

TASK: Rewrite this proposal section using the style and language patterns from these successful funded projects.

ORIGINAL TEXT:
{original_text}

SUCCESSFUL FUNDED PROJECT EXAMPLES:
{chr(10).join([f'Example {i+1}: {ex}' for i, ex in enumerate(examples)])}

REQUIREMENTS:
1. Keep the user's core technical content and meaning
2. Adopt the writing style, structure, and terminology from the examples
3. Match the professional tone of the funded proposals
4. Incorporate effective phrases and patterns you see in the examples
5. Maintain appropriate length for this section type

STYLE ELEMENTS TO TRANSFER:
- Opening patterns (how they introduce objectives)
- Terminology usage (technical and EU terms)
- Sentence structure (length, complexity)
- Impact framing (how they describe significance)
- European dimension (how they reference EU context)

Provide a complete rewrite that sounds like it could come from a funded proposal."""

        try:
            result = await self.ai_service.generate_structured(
                prompt=prompt,
                response_schema=REWRITE_SCHEMA,
                temperature=0.4
            )

            return RewriteResult(
                original_text=original_text,
                rewritten_text=result.get("rewritten_text", original_text),
                style="style_transfer",
                changes_made=result.get("changes_made", []),
                before_after_examples=result.get("before_after_examples", []),
                improvement_summary=result.get("improvement_summary", ""),
                word_count_original=len(original_text.split()),
                word_count_rewritten=len(result.get("rewritten_text", "").split()),
                predicted_score_improvement=0.5  # Higher for style transfer
            )

        except Exception as e:
            logger.error(f"Style transfer rewrite failed: {e}")
            raise

    # =========================================================================
    # TARGETED SENTENCE REWRITING
    # =========================================================================

    async def rewrite_sentence(
        self,
        sentence: str,
        context: str,
        improvement: str
    ) -> Dict[str, Any]:
        """
        Rewrite a single sentence with specific improvement.

        Useful for inline editing.
        """

        prompt = f"""Rewrite this sentence to improve {improvement}.

SENTENCE: {sentence}

CONTEXT: {context}

IMPROVEMENT FOCUS: {improvement}

Provide exactly 2-3 alternative versions, ranked by quality."""

        try:
            response = await self.ai_service.generate_text(prompt, temperature=0.5)

            # Parse alternatives from response
            alternatives = [
                line.strip().lstrip('123.-) ')
                for line in response.split('\n')
                if line.strip() and len(line.strip()) > 20
            ][:3]

            return {
                "original": sentence,
                "alternatives": alternatives,
                "improvement_focus": improvement,
                "recommended": alternatives[0] if alternatives else sentence
            }

        except Exception as e:
            logger.error(f"Sentence rewrite failed: {e}")
            return {
                "original": sentence,
                "alternatives": [],
                "improvement_focus": improvement,
                "recommended": sentence
            }

    # =========================================================================
    # COMPARISON AND DIFF
    # =========================================================================

    def generate_diff(
        self,
        original: str,
        rewritten: str
    ) -> List[Dict[str, Any]]:
        """
        Generate a diff showing what changed between versions.
        """

        original_sentences = original.split('.')
        rewritten_sentences = rewritten.split('.')

        diffs = []

        # Simple sentence-by-sentence comparison
        max_len = max(len(original_sentences), len(rewritten_sentences))

        for i in range(max_len):
            orig = original_sentences[i].strip() if i < len(original_sentences) else ""
            rewr = rewritten_sentences[i].strip() if i < len(rewritten_sentences) else ""

            if orig and rewr:
                if orig.lower() != rewr.lower():
                    diffs.append({
                        "type": "modified",
                        "original": orig,
                        "rewritten": rewr,
                        "position": i
                    })
            elif orig and not rewr:
                diffs.append({
                    "type": "removed",
                    "original": orig,
                    "rewritten": "",
                    "position": i
                })
            elif rewr and not orig:
                diffs.append({
                    "type": "added",
                    "original": "",
                    "rewritten": rewr,
                    "position": i
                })

        return diffs

    async def compare_versions(
        self,
        original: str,
        rewrites: List[RewriteResult],
        section_type: str = "objectives"
    ) -> Dict[str, Any]:
        """
        Compare original with multiple rewrite versions.

        Returns comparison with predicted scores for each.
        """

        # Import evaluator for score prediction
        from app.services.proposal_writing.evaluator_simulator import EvaluatorSimulator
        evaluator = EvaluatorSimulator()

        # Evaluate original
        original_eval = await evaluator.evaluate_section(
            section_text=original,
            section_type="excellence",
            section_id=section_type
        )

        comparisons = []

        for rewrite in rewrites:
            # Evaluate rewrite
            rewrite_eval = await evaluator.evaluate_section(
                section_text=rewrite.rewritten_text,
                section_type="excellence",
                section_id=section_type
            )

            comparisons.append({
                "style": rewrite.style,
                "word_count_change": rewrite.word_count_rewritten - rewrite.word_count_original,
                "original_score": original_eval.overall_score,
                "rewritten_score": rewrite_eval.overall_score,
                "score_change": rewrite_eval.overall_score - original_eval.overall_score,
                "changes_made": rewrite.changes_made,
                "recommendation": "Recommended" if rewrite_eval.overall_score > original_eval.overall_score else "Consider alternatives"
            })

        # Sort by score improvement
        comparisons.sort(key=lambda x: x["score_change"], reverse=True)

        return {
            "original_score": original_eval.overall_score,
            "comparisons": comparisons,
            "best_option": comparisons[0]["style"] if comparisons else None,
            "best_score_improvement": comparisons[0]["score_change"] if comparisons else 0
        }
```

---

### Step 2: Create API Endpoints

**File:** Add to `app/api/proposal_routes.py`

```python
# Add imports
from app.services.proposal_writing.smart_rewriter import SmartRewriter, RewriteStyle

rewriter = SmartRewriter()


class RewriteRequest(BaseModel):
    original_text: str
    improvement_focus: str = "clarity"  # clarity, impact, EU terminology, conciseness, structure
    section_type: str = "objectives"
    preserve_length: bool = False


class RewriteOptionsRequest(BaseModel):
    original_text: str
    section_type: str = "objectives"


class StyleTransferRequest(BaseModel):
    original_text: str
    cluster: Optional[str] = None
    action_type: Optional[str] = None
    section_type: str = "objectives"


@router.post("/rewrite/improve")
async def rewrite_for_improvement(request: RewriteRequest):
    """
    Rewrite text with focus on specific improvement.

    Improvement options:
    - clarity: Clearer language, better flow
    - impact: Stronger verbs, more persuasive
    - EU terminology: More EU terms and policy alignment
    - conciseness: Shorter, more direct
    - structure: Better headings and organization
    """
    try:
        result = await rewriter.rewrite_for_improvement(
            original_text=request.original_text,
            improvement_focus=request.improvement_focus,
            section_type=request.section_type,
            preserve_length=request.preserve_length
        )

        return {
            "original": {
                "text": result.original_text,
                "word_count": result.word_count_original
            },
            "rewritten": {
                "text": result.rewritten_text,
                "word_count": result.word_count_rewritten
            },
            "changes_made": result.changes_made,
            "before_after_examples": result.before_after_examples,
            "summary": result.improvement_summary,
            "predicted_score_improvement": result.predicted_score_improvement
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rewrite/options")
async def generate_rewrite_options(request: RewriteOptionsRequest):
    """
    Generate multiple rewrite versions to choose from.

    Returns three options:
    - Concise: Shorter, more direct
    - Impactful: Stronger language, more persuasive
    - EU-aligned: More EU terminology and policy alignment
    """
    try:
        options = await rewriter.generate_rewrite_options(
            original_text=request.original_text,
            section_type=request.section_type
        )

        return {
            "original_word_count": len(request.original_text.split()),
            "options": {
                style: {
                    "text": result.rewritten_text,
                    "word_count": result.word_count_rewritten,
                    "changes": result.changes_made[:3],  # Top 3 changes
                    "summary": result.improvement_summary
                }
                for style, result in options.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rewrite/style-transfer")
async def rewrite_with_style_transfer(request: StyleTransferRequest):
    """
    Rewrite text using style from successful funded proposals.

    Finds similar funded projects and uses their language patterns.
    """
    try:
        result = await rewriter.rewrite_like_successful_proposal(
            original_text=request.original_text,
            cluster=request.cluster,
            action_type=request.action_type,
            section_type=request.section_type
        )

        return {
            "original": {
                "text": result.original_text,
                "word_count": result.word_count_original
            },
            "rewritten": {
                "text": result.rewritten_text,
                "word_count": result.word_count_rewritten
            },
            "style_source": f"Funded {request.cluster or 'similar'} projects",
            "changes_made": result.changes_made,
            "before_after_examples": result.before_after_examples,
            "summary": result.improvement_summary,
            "predicted_score_improvement": result.predicted_score_improvement
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rewrite/compare")
async def compare_rewrite_versions(request: RewriteOptionsRequest):
    """
    Generate multiple rewrites and compare with predicted scores.

    Shows which version would likely score highest.
    """
    try:
        # Generate options
        options = await rewriter.generate_rewrite_options(
            original_text=request.original_text,
            section_type=request.section_type
        )

        # Compare versions
        comparison = await rewriter.compare_versions(
            original=request.original_text,
            rewrites=list(options.values()),
            section_type=request.section_type
        )

        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Testing Plan

```python
# tests/test_smart_rewriter.py

import pytest
from app.services.proposal_writing.smart_rewriter import SmartRewriter

@pytest.fixture
def rewriter():
    return SmartRewriter()

@pytest.mark.asyncio
async def test_rewrite_for_clarity(rewriter):
    """Test clarity-focused rewrite."""

    original = """
    The project, which will be developed by the consortium, aims to potentially
    create what could be considered a very innovative solution that might
    possibly address the issue of cybersecurity in healthcare settings.
    """

    result = await rewriter.rewrite_for_improvement(
        original_text=original,
        improvement_focus="clarity"
    )

    # Rewrite should be clearer (shorter sentences, less hedging)
    assert len(result.rewritten_text) > 0
    assert result.word_count_rewritten <= result.word_count_original * 1.1
    assert "might possibly" not in result.rewritten_text.lower()

@pytest.mark.asyncio
async def test_rewrite_for_impact(rewriter):
    """Test impact-focused rewrite."""

    original = "We will try to make a tool that could help with diagnosis."

    result = await rewriter.rewrite_for_improvement(
        original_text=original,
        improvement_focus="impact"
    )

    # Should use stronger language
    assert "try to" not in result.rewritten_text.lower()
    strong_verbs = ["develop", "create", "pioneer", "transform", "deliver"]
    assert any(v in result.rewritten_text.lower() for v in strong_verbs)

@pytest.mark.asyncio
async def test_rewrite_for_eu_terminology(rewriter):
    """Test EU terminology enhancement."""

    original = "This project will advance technology for clean energy."

    result = await rewriter.rewrite_for_improvement(
        original_text=original,
        improvement_focus="EU terminology"
    )

    # Should add EU terms
    eu_terms = ["european", "eu", "trl", "horizon", "green deal", "member state"]
    assert any(t in result.rewritten_text.lower() for t in eu_terms)

@pytest.mark.asyncio
async def test_generate_multiple_options(rewriter):
    """Test multi-option generation."""

    original = "We will develop AI solutions for healthcare."

    options = await rewriter.generate_rewrite_options(
        original_text=original,
        section_type="objectives"
    )

    # Should have multiple options
    assert len(options) >= 2
    assert "concise" in options or "impactful" in options

    # Options should be different from each other
    texts = [opt.rewritten_text for opt in options.values()]
    assert len(set(texts)) == len(texts)  # All unique

@pytest.mark.asyncio
async def test_style_transfer(rewriter):
    """Test style transfer from funded projects."""

    original = "We make AI for health."

    result = await rewriter.rewrite_like_successful_proposal(
        original_text=original,
        cluster="CL1",  # Health
        section_type="objectives"
    )

    # Should produce significantly better text
    assert len(result.rewritten_text) > len(original)
    assert result.word_count_rewritten > result.word_count_original
```

---

## Acceptance Criteria

- [ ] Single-focus rewrite produces noticeably improved text
- [ ] Multi-option generation provides meaningfully different versions
- [ ] Style transfer captures patterns from funded proposals
- [ ] Before/after examples clearly show changes
- [ ] Word count changes are reported accurately
- [ ] Score predictions correlate with actual improvements
- [ ] API endpoints work correctly

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `app/services/proposal_writing/smart_rewriter.py` | CREATE |
| `app/services/proposal_writing/schemas/ai_schemas.py` | MODIFY (add REWRITE_SCHEMA) |
| `app/api/proposal_routes.py` | MODIFY (add endpoints) |
| `tests/test_smart_rewriter.py` | CREATE |

---

## Next Task

After completing this task, proceed to:
→ **Task 12: Rewrite Options UI Integration**
