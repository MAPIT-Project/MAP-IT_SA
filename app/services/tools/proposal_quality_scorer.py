"""
Proposal Quality Scoring Tool

Unified tool for evaluating proposal quality based on EU Horizon Europe
evaluation criteria. Provides standalone scoring without requiring a full
proposal session context.

This tool wraps EvaluatorSimulator and GapAnalysisService to provide:
1. Quick section quality assessment
2. Full proposal quality scoring
3. Improvement prioritization
4. Score predictions for funding probability
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """Quality level classifications matching EU thresholds."""

    EXCELLENT = "excellent"  # 4.5-5.0
    VERY_GOOD = "very_good"  # 3.5-4.4
    GOOD = "good"  # 3.0-3.4 (threshold)
    NEEDS_IMPROVEMENT = "needs_improvement"  # 2.0-2.9
    WEAK = "weak"  # 0-1.9


@dataclass
class CriterionAssessment:
    """Assessment for a single evaluation criterion."""

    criterion: str
    score: float
    max_score: float = 5.0
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    improvement_suggestion: str = ""
    score_potential: float = 0.0  # How much score could improve


@dataclass
class SectionScore:
    """Score for a proposal section."""

    section_type: str  # excellence, impact, implementation
    section_id: str  # objectives, methodology, etc.
    score: float
    max_score: float = 5.0
    criteria: list[CriterionAssessment] = field(default_factory=list)
    summary: str = ""
    quality_level: str = ""
    threshold_met: bool = False


@dataclass
class ProposalQualityReport:
    """Complete quality report for a proposal."""

    overall_score: float
    max_score: float
    quality_level: str
    funding_probability: str  # low, medium, high
    excellence_score: float
    impact_score: float
    implementation_score: float
    section_scores: list[SectionScore] = field(default_factory=list)
    top_improvements: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    threshold_status: str = ""  # above, at, below


class ProposalQualityScorerTool:
    """
    Unified tool for proposal quality scoring.

    Can evaluate:
    - Individual sections with detailed criterion breakdown
    - Full proposals with aggregated scores
    - Quick quality checks for drafts

    Uses EU Horizon Europe evaluation criteria:
    - Excellence (0-5): Scientific/technical quality
    - Impact (0-5): Expected outcomes and exploitation
    - Implementation (0-5): Work plan and resources

    Thresholds:
    - Section threshold: 3.0/5.0
    - Overall threshold: 10.0/15.0
    """

    # EU evaluation thresholds
    SECTION_THRESHOLD = 3.0
    OVERALL_THRESHOLD = 10.0
    MAX_SECTION_SCORE = 5.0
    MAX_OVERALL_SCORE = 15.0

    # Section weights by action type
    ACTION_WEIGHTS = {
        "RIA": {"excellence": 0.40, "impact": 0.30, "implementation": 0.30},
        "IA": {"excellence": 0.30, "impact": 0.40, "implementation": 0.30},
        "CSA": {"excellence": 0.30, "impact": 0.35, "implementation": 0.35},
    }

    # Criteria by section
    CRITERIA = {
        "excellence": {
            "objectives": [
                "Clarity and pertinence of objectives",
                "Measurability and SMART criteria",
                "Alignment with call scope",
            ],
            "methodology": [
                "Soundness of methodology",
                "Appropriateness of approach",
                "Risk mitigation strategy",
            ],
            "state_of_art": [
                "Beyond state-of-the-art advancement",
                "Innovation potential",
                "Scientific excellence",
            ],
        },
        "impact": {
            "pathways": [
                "Credibility of impact pathways",
                "Scale of contribution",
                "Alignment with expected outcomes",
            ],
            "dissemination": [
                "Exploitation plan quality",
                "Dissemination measures",
                "Communication strategy",
            ],
        },
        "implementation": {
            "work_plan": [
                "Work plan coherence",
                "Timeline realism",
                "Deliverable quality",
            ],
            "consortium": [
                "Partner complementarity",
                "Management structure",
                "Resource allocation",
            ],
        },
    }

    def __init__(self):
        self._evaluator = None
        self._gap_analyzer = None

    def _get_evaluator(self):
        """Lazy load evaluator simulator."""
        if self._evaluator is None:
            from ..proposal_writing.evaluator_simulator import EvaluatorSimulator

            self._evaluator = EvaluatorSimulator()
        return self._evaluator

    def _get_gap_analyzer(self):
        """Lazy load gap analyzer."""
        if self._gap_analyzer is None:
            from ..proposal_writing.gap_analysis_service import GapAnalysisService

            self._gap_analyzer = GapAnalysisService()
        return self._gap_analyzer

    def _classify_quality(self, score: float, max_score: float = 5.0) -> str:
        """Classify score into quality level."""
        normalized = (score / max_score) * 5.0
        if normalized >= 4.5:
            return QualityLevel.EXCELLENT.value
        elif normalized >= 3.5:
            return QualityLevel.VERY_GOOD.value
        elif normalized >= 3.0:
            return QualityLevel.GOOD.value
        elif normalized >= 2.0:
            return QualityLevel.NEEDS_IMPROVEMENT.value
        else:
            return QualityLevel.WEAK.value

    def _estimate_funding_probability(self, score: float) -> str:
        """Estimate funding probability based on score."""
        if score >= 13.5:
            return "high"
        elif score >= 11.5:
            return "medium-high"
        elif score >= 10.0:
            return "medium"
        elif score >= 8.0:
            return "low"
        else:
            return "very_low"

    async def score_section(
        self,
        content: str,
        section_type: str,
        section_id: str | None = None,
        action_type: str = "RIA",
        call_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Score a single proposal section.

        Args:
            content: Section text to evaluate
            section_type: 'excellence', 'impact', or 'implementation'
            section_id: Optional specific section (e.g., 'objectives')
            action_type: RIA, IA, or CSA
            call_id: Optional call ID for context

        Returns:
            Section score with criterion breakdown
        """
        if not content or len(content.strip()) < 50:
            return {
                "success": False,
                "error": "Content too short for meaningful evaluation (minimum 50 characters)",
                "section_type": section_type,
            }

        # Normalize section type
        section_type = section_type.lower()
        if section_type not in self.CRITERIA:
            return {
                "success": False,
                "error": f"Invalid section_type: {section_type}. Use: excellence, impact, implementation",
            }

        # If no section_id, infer from content or use first available
        if not section_id:
            section_id = list(self.CRITERIA[section_type].keys())[0]

        try:
            # Use evaluator simulator
            evaluator = self._get_evaluator()
            result = await evaluator.evaluate_section(
                section_text=content,
                section_type=section_type,
                section_id=section_id,
                call_id=call_id,
                action_type=action_type,
            )

            # Format response
            quality_level = self._classify_quality(result.overall_score)
            threshold_met = result.overall_score >= self.SECTION_THRESHOLD

            criteria_list = []
            for cs in result.criterion_scores:
                criteria_list.append(
                    {
                        "criterion": cs.criterion,
                        "score": cs.score,
                        "max_score": 5.0,
                        "justification": cs.justification,
                        "strengths": cs.strengths,
                        "weaknesses": cs.weaknesses,
                        "improvement_suggestion": cs.improvement_for_half_point,
                    }
                )

            return {
                "success": True,
                "section_type": section_type,
                "section_id": section_id,
                "score": result.overall_score,
                "max_score": 5.0,
                "quality_level": quality_level,
                "threshold_met": threshold_met,
                "threshold": self.SECTION_THRESHOLD,
                "criteria": criteria_list,
                "summary": result.esr_summary,
                "strengths": result.strengths,
                "weaknesses": result.weaknesses,
                "top_improvements": result.top_improvements,
                "confidence": result.confidence,
            }

        except Exception as e:
            logger.error(f"Section scoring error: {e}")
            # Fallback to rule-based scoring
            return await self._fallback_section_score(content, section_type, section_id)

    async def _fallback_section_score(
        self,
        content: str,
        section_type: str,
        section_id: str,
    ) -> dict[str, Any]:
        """Fallback rule-based scoring when AI is unavailable."""
        # Simple heuristic scoring
        score = 2.5  # Base score

        # Check content quality indicators
        word_count = len(content.split())
        if word_count > 500:
            score += 0.5
        if word_count > 1000:
            score += 0.3

        # Check for structure indicators
        structure_indicators = [
            "objective",
            "methodology",
            "approach",
            "impact",
            "result",
            "outcome",
            "deliverable",
            "milestone",
        ]
        for indicator in structure_indicators:
            if indicator in content.lower():
                score += 0.1

        score = min(score, 4.0)  # Cap at 4.0 for fallback

        return {
            "success": True,
            "section_type": section_type,
            "section_id": section_id,
            "score": round(score, 1),
            "max_score": 5.0,
            "quality_level": self._classify_quality(score),
            "threshold_met": score >= self.SECTION_THRESHOLD,
            "threshold": self.SECTION_THRESHOLD,
            "criteria": [],
            "summary": "Rule-based evaluation (AI unavailable)",
            "strengths": ["Content provided"],
            "weaknesses": ["Detailed AI evaluation unavailable"],
            "top_improvements": [],
            "confidence": 0.3,
            "fallback": True,
        }

    async def score_full_proposal(
        self,
        sections: dict[str, str],
        action_type: str = "RIA",
        call_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Score a complete proposal with all sections.

        Args:
            sections: Dict mapping section types to content
                     e.g., {'excellence': '...', 'impact': '...', 'implementation': '...'}
            action_type: RIA, IA, or CSA
            call_id: Optional call ID for context

        Returns:
            Complete proposal quality report
        """
        section_scores = []
        excellence_score = 0.0
        impact_score = 0.0
        implementation_score = 0.0

        # Score each section
        for section_type in ["excellence", "impact", "implementation"]:
            content = sections.get(section_type, "")

            if content:
                result = await self.score_section(
                    content=content,
                    section_type=section_type,
                    action_type=action_type,
                    call_id=call_id,
                )

                if result.get("success"):
                    score = result.get("score", 0.0)
                    section_scores.append(result)

                    if section_type == "excellence":
                        excellence_score = score
                    elif section_type == "impact":
                        impact_score = score
                    else:
                        implementation_score = score
            else:
                # Missing section
                section_scores.append(
                    {
                        "success": False,
                        "section_type": section_type,
                        "score": 0.0,
                        "error": "Section content not provided",
                    }
                )

        # Calculate overall score
        overall_score = excellence_score + impact_score + implementation_score

        # Determine threshold status
        if overall_score >= self.OVERALL_THRESHOLD + 2:
            threshold_status = "above"
        elif overall_score >= self.OVERALL_THRESHOLD:
            threshold_status = "at"
        else:
            threshold_status = "below"

        # Aggregate improvements
        all_improvements = []
        for section_result in section_scores:
            if section_result.get("success") and section_result.get("top_improvements"):
                for imp in section_result["top_improvements"]:
                    imp["section"] = section_result.get("section_type", "unknown")
                    all_improvements.append(imp)

        # Sort by expected score increase
        all_improvements.sort(key=lambda x: x.get("expected_score_increase", 0), reverse=True)

        return {
            "success": True,
            "overall_score": round(overall_score, 1),
            "max_score": self.MAX_OVERALL_SCORE,
            "quality_level": self._classify_quality(overall_score, self.MAX_OVERALL_SCORE),
            "funding_probability": self._estimate_funding_probability(overall_score),
            "threshold_status": threshold_status,
            "threshold": self.OVERALL_THRESHOLD,
            "excellence_score": round(excellence_score, 1),
            "impact_score": round(impact_score, 1),
            "implementation_score": round(implementation_score, 1),
            "section_scores": section_scores,
            "top_improvements": all_improvements[:5],
            "summary": self._generate_summary(
                overall_score,
                excellence_score,
                impact_score,
                implementation_score,
                threshold_status,
            ),
        }

    def _generate_summary(
        self,
        overall: float,
        excellence: float,
        impact: float,
        implementation: float,
        threshold_status: str,
    ) -> str:
        """Generate executive summary of proposal quality."""
        if threshold_status == "above":
            opening = (
                f"This proposal scores {overall:.1f}/15.0, well above the funding threshold (10.0)."
            )
        elif threshold_status == "at":
            opening = (
                f"This proposal scores {overall:.1f}/15.0, meeting the minimum funding threshold."
            )
        else:
            gap = self.OVERALL_THRESHOLD - overall
            opening = f"This proposal scores {overall:.1f}/15.0, {gap:.1f} points below the funding threshold."

        # Identify strongest and weakest
        scores = {"Excellence": excellence, "Impact": impact, "Implementation": implementation}
        strongest = max(scores, key=scores.get)
        weakest = min(scores, key=scores.get)

        return (
            f"{opening} "
            f"Strongest area: {strongest} ({scores[strongest]:.1f}/5.0). "
            f"Priority for improvement: {weakest} ({scores[weakest]:.1f}/5.0)."
        )

    async def quick_quality_check(
        self,
        text: str,
        context: str = "general",
    ) -> dict[str, Any]:
        """
        Quick quality check for draft text without full evaluation.

        Args:
            text: Draft text to check
            context: Context hint ('objectives', 'methodology', 'impact', etc.)

        Returns:
            Quick quality indicators
        """
        word_count = len(text.split())
        char_count = len(text)

        # Quality indicators
        indicators = {
            "word_count": word_count,
            "char_count": char_count,
            "has_structure": any(
                x in text.lower() for x in ["objective", "approach", "method", "result"]
            ),
            "has_quantification": any(char.isdigit() for char in text),
            "sentence_count": text.count(".") + text.count("!") + text.count("?"),
        }

        # Simple quality estimate
        quality_score = 2.0

        if word_count >= 200:
            quality_score += 0.5
        if word_count >= 500:
            quality_score += 0.5
        if indicators["has_structure"]:
            quality_score += 0.5
        if indicators["has_quantification"]:
            quality_score += 0.3
        if indicators["sentence_count"] >= 5:
            quality_score += 0.2

        quality_score = min(quality_score, 4.5)

        # Suggestions
        suggestions = []
        if word_count < 200:
            suggestions.append("Content seems brief - consider expanding with more detail")
        if not indicators["has_structure"]:
            suggestions.append(
                "Add structural elements (objectives, methodology, expected results)"
            )
        if not indicators["has_quantification"]:
            suggestions.append("Include quantitative targets and metrics")

        return {
            "success": True,
            "quality_estimate": round(quality_score, 1),
            "quality_level": self._classify_quality(quality_score),
            "indicators": indicators,
            "suggestions": suggestions,
            "note": "Quick check - use score_section() for detailed evaluation",
        }


# Standalone execute functions for tool orchestration


async def score_proposal_section_execute(
    content: str,
    section_type: str,
    section_id: str | None = None,
    action_type: str = "RIA",
    call_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute proposal section scoring.

    Args:
        content: Section text to evaluate
        section_type: 'excellence', 'impact', or 'implementation'
        section_id: Specific section (e.g., 'objectives', 'methodology')
        action_type: RIA, IA, or CSA
        call_id: Optional call ID for context

    Returns:
        Section score with detailed breakdown
    """
    tool = ProposalQualityScorerTool()
    return await tool.score_section(
        content=content,
        section_type=section_type,
        section_id=section_id,
        action_type=action_type,
        call_id=call_id,
    )


async def score_full_proposal_execute(
    excellence_content: str = "",
    impact_content: str = "",
    implementation_content: str = "",
    action_type: str = "RIA",
    call_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute full proposal scoring.

    Args:
        excellence_content: Excellence section content
        impact_content: Impact section content
        implementation_content: Implementation section content
        action_type: RIA, IA, or CSA
        call_id: Optional call ID for context

    Returns:
        Complete proposal quality report
    """
    sections = {
        "excellence": excellence_content,
        "impact": impact_content,
        "implementation": implementation_content,
    }

    tool = ProposalQualityScorerTool()
    return await tool.score_full_proposal(
        sections=sections,
        action_type=action_type,
        call_id=call_id,
    )


async def quick_quality_check_execute(
    text: str,
    context: str = "general",
) -> dict[str, Any]:
    """
    Execute quick quality check.

    Args:
        text: Draft text to check
        context: Context hint

    Returns:
        Quick quality indicators
    """
    tool = ProposalQualityScorerTool()
    return await tool.quick_quality_check(text=text, context=context)
