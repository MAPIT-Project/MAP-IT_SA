"""
Quality Improvement Advisor

AI-powered suggestions to improve proposal quality using structured outputs.
"""

import logging
import re
from typing import Any

from .proposal_ai_service import ProposalAIService
from .schemas.ai_schemas import QUALITY_ANALYSIS_SCHEMA

logger = logging.getLogger(__name__)


class QualityImprover:
    """
    Analyze and improve proposal quality using AI with structured outputs.
    """

    def __init__(self, ai_service: Any | None = None):
        # Use ProposalAIService for structured outputs
        self.ai_service = ProposalAIService()

    async def analyze_quality(
        self, section_text: str, section_type: str, call_id: str = None, use_ai: bool = True
    ) -> dict[str, Any]:
        """
        Comprehensive quality analysis with AI or rule-based fallback.

        Args:
            section_text: The text to analyze
            section_type: Type of section (e.g., 'objectives', 'methodology')
            call_id: Optional call identifier for context
            use_ai: Whether to use AI analysis (True) or rule-based only (False)

        Returns:
            Quality analysis with scores and suggestions
        """

        logger.info(f"Analyzing quality of {section_type} section")

        if use_ai:
            try:
                return await self._ai_quality_analysis(section_text, section_type)
            except Exception as e:
                logger.warning(f"AI quality analysis failed: {e}, falling back to rule-based")

        # Rule-based analysis (always available as fallback)
        return self._rule_based_analysis(section_text, section_type)

    async def _ai_quality_analysis(self, section_text: str, section_type: str) -> dict[str, Any]:
        """AI-powered quality analysis using structured outputs."""

        prompt = self._build_quality_prompt(section_text, section_type)

        result = await self.ai_service.generate_structured(
            prompt=prompt, response_schema=QUALITY_ANALYSIS_SCHEMA, temperature=0.3
        )

        return result

    def _build_quality_prompt(self, section_text: str, section_type: str) -> str:
        """Build prompt for quality analysis."""

        return f"""Analyze the quality of this Horizon Europe proposal section.

SECTION TYPE: {section_type}

SECTION TEXT:
{section_text}

Analyze the following aspects:

1. READABILITY
   - Average sentence length (ideal: 15-20 words)
   - Complex word usage
   - Overall readability for EU evaluators

2. EU TERMINOLOGY
   - Check for key Horizon Europe terms: TRL, KPI, WP, deliverable, milestone, dissemination, exploitation, EU added value, state of the art
   - Identify missing recommended terms
   - Suggest terminology improvements

3. STRUCTURE
   - Presence of clear headings/subheadings
   - Use of bullet points or numbered lists
   - Paragraph organization
   - Logical flow

4. IMPACT LANGUAGE
   - Use of strong action verbs (develop, create, innovate, transform)
   - Presence of weak/uncertain language (might, could, try to)
   - Future-focused language

5. IMPROVEMENT SUGGESTIONS
   - Provide specific, actionable suggestions
   - Include before/after examples where possible
   - Prioritize by impact (critical, high, medium, low)

Be specific and constructive in your analysis."""

    def _rule_based_analysis(self, section_text: str, section_type: str) -> dict[str, Any]:
        """Fallback rule-based analysis."""

        readability = self._analyze_readability(section_text)
        terminology = self._check_terminology(section_text)
        structure = self._analyze_structure(section_text, section_type)
        impact = self._analyze_impact_language(section_text)

        # Calculate overall score
        overall_score = (
            readability["score"] * 0.3
            + terminology["score"] * 0.2
            + structure["score"] * 0.3
            + impact["score"] * 0.2
        )

        # Generate suggestions
        suggestions = self._generate_rule_based_suggestions(
            readability, terminology, structure, impact
        )

        return {
            "overall_quality_score": round(overall_score, 2),
            "readability": readability,
            "terminology": terminology,
            "structure": structure,
            "impact_language": impact,
            "improvement_suggestions": suggestions,
        }

    def _analyze_readability(self, text: str) -> dict[str, Any]:
        """Analyze text readability."""

        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        words = text.split()
        word_count = len(words)
        sentence_count = len(sentences)

        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0

        # Count complex words (>12 characters as proxy)
        complex_words = [w for w in words if len(w) > 12]
        complex_word_ratio = len(complex_words) / word_count if word_count > 0 else 0

        issues = []
        strengths = []

        if avg_sentence_length > 25:
            issues.append(
                f"Sentences are too long (avg {avg_sentence_length:.1f} words). "
                "Consider breaking into shorter sentences."
            )
        elif avg_sentence_length < 10:
            issues.append("Sentences are very short. Consider combining some for better flow.")
        else:
            strengths.append("Good sentence length")

        if complex_word_ratio > 0.3:
            issues.append(
                f"{complex_word_ratio * 100:.0f}% complex words. "
                "Consider using simpler alternatives."
            )

        length_score = 1.0 if 15 <= avg_sentence_length <= 20 else 0.7
        complexity_score = 1.0 if complex_word_ratio < 0.25 else 0.6
        score = (length_score + complexity_score) / 2

        return {
            "score": score,
            "avg_sentence_length": avg_sentence_length,
            "issues": issues,
            "strengths": strengths,
        }

    def _check_terminology(self, text: str) -> dict[str, Any]:
        """Check for proper EU/Horizon Europe terminology."""

        recommended_terms = {
            "TRL": "Technology Readiness Level",
            "KPI": "Key Performance Indicator",
            "deliverable": "Project deliverable",
            "milestone": "Project milestone",
            "dissemination": "Results dissemination",
            "exploitation": "Results exploitation",
            "EU added value": "European added value",
            "state of the art": "Current state of the art",
        }

        text_lower = text.lower()

        missing_terms = []
        found_terms = []

        for term in recommended_terms:
            if term.lower() in text_lower:
                found_terms.append(term)
            else:
                missing_terms.append(term)

        score = len(found_terms) / len(recommended_terms) if recommended_terms else 0

        return {
            "score": score,
            "found_terms": found_terms,
            "missing_terms": missing_terms[:5],
            "suggestions": [f"Consider adding: {term}" for term in missing_terms[:3]],
        }

    def _analyze_structure(self, text: str, section_type: str) -> dict[str, Any]:
        """Analyze section structure."""

        has_headings = bool(re.search(r"^#+\s+\w+|^\w+\s*:|\d+\.\d+", text, re.MULTILINE))
        has_lists = bool(re.search(r"^\s*[-*•]\s+|\d+\.\s+", text, re.MULTILINE))

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        paragraph_count = len(paragraphs)

        issues = []
        strengths = []

        if not has_headings:
            issues.append("No clear subheadings found. Add structure with headings.")
        else:
            strengths.append("Good use of headings")

        if not has_lists and section_type in ["objectives", "work_plan", "implementation"]:
            issues.append("Consider using bullet points for lists")

        if paragraph_count < 3:
            issues.append("Section seems underdeveloped. Add more content.")
        elif paragraph_count > 15:
            issues.append("Section is very long. Consider using subsections.")

        structure_score = 1.0
        if not has_headings:
            structure_score -= 0.3
        if paragraph_count < 3 or paragraph_count > 15:
            structure_score -= 0.2

        return {
            "score": max(structure_score, 0),
            "has_headings": has_headings,
            "has_lists": has_lists,
            "paragraph_count": paragraph_count,
            "issues": issues,
        }

    def _analyze_impact_language(self, text: str) -> dict[str, Any]:
        """Analyze use of impactful language."""

        strong_verbs = [
            "develop",
            "create",
            "innovate",
            "transform",
            "advance",
            "pioneer",
            "establish",
            "demonstrate",
            "achieve",
            "deliver",
        ]

        weak_phrases = [
            "will try to",
            "might",
            "possibly",
            "could potentially",
            "may be able to",
            "hope to",
        ]

        text_lower = text.lower()

        strong_found = [v for v in strong_verbs if v in text_lower]
        weak_found = [p for p in weak_phrases if p in text_lower]

        issues = []

        if len(weak_found) > 2:
            issues.append(f"Avoid weak language: {', '.join(weak_found[:3])}")

        if len(strong_found) < 3:
            issues.append("Use more strong action verbs")

        score = min((len(strong_found) / 5) - (len(weak_found) / 5), 1.0)
        score = max(score, 0)

        return {
            "score": score,
            "strong_verbs_found": strong_found,
            "weak_phrases_found": weak_found,
            "issues": issues,
        }

    def _generate_rule_based_suggestions(
        self, readability: dict, terminology: dict, structure: dict, impact: dict
    ) -> list[dict[str, Any]]:
        """Generate improvement suggestions from rule-based analysis."""

        suggestions = []

        if readability["score"] < 0.7:
            suggestions.append(
                {
                    "type": "readability",
                    "priority": "high",
                    "issue": "Text readability can be improved",
                    "suggestion": "Break long sentences into shorter ones (15-20 words ideal).",
                    "example_before": "",
                    "example_after": "",
                }
            )

        if terminology["score"] < 0.5:
            missing = terminology["missing_terms"][:2]
            suggestions.append(
                {
                    "type": "terminology",
                    "priority": "medium",
                    "issue": f"Missing EU terms: {', '.join(missing)}",
                    "suggestion": f"Add these terms: {', '.join(missing)}",
                    "example_before": "",
                    "example_after": "",
                }
            )

        if impact["weak_phrases_found"]:
            suggestions.append(
                {
                    "type": "impact",
                    "priority": "high",
                    "issue": "Weak language detected",
                    "suggestion": "Replace uncertain phrases with confident statements",
                    "example_before": "will try to develop",
                    "example_after": "will develop",
                }
            )

        if structure["issues"]:
            suggestions.append(
                {
                    "type": "structure",
                    "priority": "medium",
                    "issue": (
                        structure["issues"][0]
                        if structure["issues"]
                        else "Structure could be improved"
                    ),
                    "suggestion": "Add clear headings and organize content logically",
                    "example_before": "",
                    "example_after": "",
                }
            )

        return suggestions
