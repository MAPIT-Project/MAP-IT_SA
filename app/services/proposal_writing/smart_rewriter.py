"""
Smart Rewriter Service

Provide actual rewritten content, not just suggestions.
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.services.proposal_writing.proposal_ai_service import ProposalAIService
from app.services.proposal_writing.proposal_learning_service import ProposalLearningService
from app.services.proposal_writing.schemas.ai_schemas import REWRITE_SCHEMA

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
    changes_made: list[str]
    before_after_examples: list[dict[str, str]]
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
        preserve_length: bool = False,
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
                prompt=prompt, response_schema=REWRITE_SCHEMA, temperature=0.4
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
                predicted_score_improvement=0.3,  # Estimated
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
- End sections with strong impact statements""",
        }

        return guidance.get(focus, guidance["clarity"])

    # =========================================================================
    # MULTI-OPTION GENERATION
    # =========================================================================

    async def generate_rewrite_options(
        self, original_text: str, section_type: str = "objectives"
    ) -> dict[str, RewriteResult]:
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
            return_exceptions=True,
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
        section_type: str = "objectives",
    ) -> RewriteResult:
        """
        Rewrite text using style from successful funded proposals.

        Finds similar funded projects and uses their language patterns
        to improve the user's text.
        """

        logger.info(f"Rewriting using style from funded {cluster or 'any cluster'} projects")

        # Find similar funded projects
        similar = await self.learning_service.find_similar_funded_projects(
            user_idea=original_text, cluster=cluster, action_type=action_type, limit=5
        )

        if not similar:
            # Fallback to regular rewrite
            return await self.rewrite_for_improvement(original_text, "impact", section_type)

        # Extract example excerpts
        examples = [p.objective[:800] for p in similar[:3] if p.objective]

        prompt = f"""You are an expert Horizon Europe proposal editor.

TASK: Rewrite this proposal section using the style and language patterns from these successful funded projects.

ORIGINAL TEXT:
{original_text}

SUCCESSFUL FUNDED PROJECT EXAMPLES:
{chr(10).join([f"Example {i + 1}: {ex}" for i, ex in enumerate(examples)])}

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
                prompt=prompt, response_schema=REWRITE_SCHEMA, temperature=0.4
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
                predicted_score_improvement=0.5,  # Higher for style transfer
            )

        except Exception as e:
            logger.error(f"Style transfer rewrite failed: {e}")
            raise

    # =========================================================================
    # TARGETED SENTENCE REWRITING
    # =========================================================================

    async def rewrite_sentence(
        self, sentence: str, context: str, improvement: str
    ) -> dict[str, Any]:
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
                line.strip().lstrip("123.-) ")
                for line in response.split("\n")
                if line.strip() and len(line.strip()) > 20
            ][:3]

            return {
                "original": sentence,
                "alternatives": alternatives,
                "improvement_focus": improvement,
                "recommended": alternatives[0] if alternatives else sentence,
            }

        except Exception as e:
            logger.error(f"Sentence rewrite failed: {e}")
            return {
                "original": sentence,
                "alternatives": [],
                "improvement_focus": improvement,
                "recommended": sentence,
            }

    # =========================================================================
    # COMPARISON AND DIFF
    # =========================================================================

    def generate_diff(self, original: str, rewritten: str) -> list[dict[str, Any]]:
        """
        Generate a diff showing what changed between versions.
        """

        original_sentences = original.split(".")
        rewritten_sentences = rewritten.split(".")

        diffs = []

        # Simple sentence-by-sentence comparison
        max_len = max(len(original_sentences), len(rewritten_sentences))

        for i in range(max_len):
            orig = original_sentences[i].strip() if i < len(original_sentences) else ""
            rewr = rewritten_sentences[i].strip() if i < len(rewritten_sentences) else ""

            if orig and rewr:
                if orig.lower() != rewr.lower():
                    diffs.append(
                        {"type": "modified", "original": orig, "rewritten": rewr, "position": i}
                    )
            elif orig and not rewr:
                diffs.append({"type": "removed", "original": orig, "rewritten": "", "position": i})
            elif rewr and not orig:
                diffs.append({"type": "added", "original": "", "rewritten": rewr, "position": i})

        return diffs

    async def compare_versions(
        self, original: str, rewrites: list[RewriteResult], section_type: str = "objectives"
    ) -> dict[str, Any]:
        """
        Compare original with multiple rewrite versions.

        Returns comparison with predicted scores for each.
        """

        # Import evaluator for score prediction
        from app.services.proposal_writing.evaluator_simulator import EvaluatorSimulator

        evaluator = EvaluatorSimulator()

        # Evaluate original
        original_eval = await evaluator.evaluate_section(
            section_text=original, section_type="excellence", section_id=section_type
        )

        comparisons = []

        for rewrite in rewrites:
            # Evaluate rewrite
            rewrite_eval = await evaluator.evaluate_section(
                section_text=rewrite.rewritten_text,
                section_type="excellence",
                section_id=section_type,
            )

            comparisons.append(
                {
                    "style": rewrite.style,
                    "word_count_change": rewrite.word_count_rewritten - rewrite.word_count_original,
                    "original_score": original_eval.overall_score,
                    "rewritten_score": rewrite_eval.overall_score,
                    "score_change": rewrite_eval.overall_score - original_eval.overall_score,
                    "changes_made": rewrite.changes_made,
                    "recommendation": (
                        "Recommended"
                        if rewrite_eval.overall_score > original_eval.overall_score
                        else "Consider alternatives"
                    ),
                }
            )

        # Sort by score improvement
        comparisons.sort(key=lambda x: x["score_change"], reverse=True)

        return {
            "original_score": original_eval.overall_score,
            "comparisons": comparisons,
            "best_option": comparisons[0]["style"] if comparisons else None,
            "best_score_improvement": comparisons[0]["score_change"] if comparisons else 0,
        }

    # =========================================================================
    # ADDITIONAL REWRITE STYLES
    # =========================================================================

    async def rewrite_for_technical_depth(
        self, original_text: str, domain: str = "general", section_type: str = "methodology"
    ) -> RewriteResult:
        """
        Rewrite to add more technical depth and rigor.

        Useful for methodology and implementation sections.
        """

        prompt = f"""You are an expert Horizon Europe proposal editor specializing in technical content.

TASK: Rewrite this proposal section to add more technical depth and rigor.

ORIGINAL TEXT:
{original_text}

DOMAIN: {domain}

REQUIREMENTS:
1. Add specific technical details where appropriate
2. Include relevant methodological terminology
3. Reference standard approaches and frameworks
4. Add technical metrics and KPIs where relevant
5. Maintain clarity while increasing technical substance

TECHNICAL DEPTH MEANS:
- Specific methods and approaches (not just "we will analyze")
- Technical terminology appropriate for evaluators
- Reference to established frameworks or standards
- Quantifiable technical parameters
- Clear technical justification for approaches

Provide a complete rewrite with enhanced technical depth."""

        try:
            result = await self.ai_service.generate_structured(
                prompt=prompt,
                response_schema=REWRITE_SCHEMA,
                temperature=0.3,  # Lower temperature for technical content
            )

            return RewriteResult(
                original_text=original_text,
                rewritten_text=result.get("rewritten_text", original_text),
                style="technical",
                changes_made=result.get("changes_made", []),
                before_after_examples=result.get("before_after_examples", []),
                improvement_summary=result.get("improvement_summary", ""),
                word_count_original=len(original_text.split()),
                word_count_rewritten=len(result.get("rewritten_text", "").split()),
                predicted_score_improvement=0.4,
            )

        except Exception as e:
            logger.error(f"Technical rewrite failed: {e}")
            raise

    async def rewrite_for_accessibility(
        self,
        original_text: str,
        target_audience: str = "mixed evaluators",
        section_type: str = "objectives",
    ) -> RewriteResult:
        """
        Rewrite for clearer, more accessible language.

        Useful when text is too jargon-heavy or complex.
        """

        prompt = f"""You are an expert Horizon Europe proposal editor.

TASK: Rewrite this proposal section for clearer, more accessible language.

ORIGINAL TEXT:
{original_text}

TARGET AUDIENCE: {target_audience}

REQUIREMENTS:
1. Simplify complex terminology where possible
2. Use shorter sentences (15-20 words average)
3. Explain technical concepts briefly where needed
4. Maintain professional tone
5. Keep the substantive content intact

ACCESSIBILITY MEANS:
- Clear, direct language
- Technical terms defined or explained
- Logical paragraph structure
- One main idea per paragraph
- Active voice preferred

Provide a complete rewrite that maintains rigor while improving accessibility."""

        try:
            result = await self.ai_service.generate_structured(
                prompt=prompt, response_schema=REWRITE_SCHEMA, temperature=0.4
            )

            return RewriteResult(
                original_text=original_text,
                rewritten_text=result.get("rewritten_text", original_text),
                style="accessible",
                changes_made=result.get("changes_made", []),
                before_after_examples=result.get("before_after_examples", []),
                improvement_summary=result.get("improvement_summary", ""),
                word_count_original=len(original_text.split()),
                word_count_rewritten=len(result.get("rewritten_text", "").split()),
                predicted_score_improvement=0.3,
            )

        except Exception as e:
            logger.error(f"Accessibility rewrite failed: {e}")
            raise

    # =========================================================================
    # BATCH REWRITING
    # =========================================================================

    async def rewrite_all_styles(
        self, original_text: str, section_type: str = "objectives"
    ) -> dict[str, RewriteResult]:
        """
        Generate all five rewrite styles for maximum choice.

        Returns: concise, impactful, eu_aligned, technical, accessible
        """

        logger.info("Generating all rewrite styles")

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
            self.rewrite_for_technical_depth(original_text, section_type=section_type),
            self.rewrite_for_accessibility(original_text, section_type=section_type),
            return_exceptions=True,
        )

        styles = ["concise", "impactful", "eu_aligned", "technical", "accessible"]
        options = {}

        for i, style in enumerate(styles):
            if not isinstance(results[i], Exception):
                options[style] = results[i]
            else:
                logger.warning(f"Failed to generate {style} rewrite: {results[i]}")

        return options
