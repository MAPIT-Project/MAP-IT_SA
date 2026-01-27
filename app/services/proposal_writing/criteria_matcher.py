"""
Evaluation Criteria Matcher

Analyzes proposal content against evaluation criteria using structured AI outputs.
"""

import logging
from typing import Any

from .proposal_ai_service import ProposalAIService
from .schemas.ai_schemas import CRITERIA_ANALYSIS_SCHEMA

logger = logging.getLogger(__name__)


class EvaluationCriteriaMatcher:
    """
    Match proposal content to evaluation criteria using structured AI analysis.
    """

    def __init__(self):
        self.ai_service = ProposalAIService()

    async def analyze_section(
        self,
        section_text: str,
        evaluation_criteria: list[str],
        call_id: str
    ) -> dict[str, Any]:
        """
        Analyze how well a section addresses evaluation criteria.

        Returns structured analysis with guaranteed fields.
        """

        logger.info(f"Analyzing section against {len(evaluation_criteria)} criteria")

        prompt = self._build_analysis_prompt(section_text, evaluation_criteria)

        try:
            # Use structured output - no more regex parsing!
            result = await self.ai_service.generate_structured(
                prompt=prompt,
                response_schema=CRITERIA_ANALYSIS_SCHEMA,
                temperature=0.2  # Low temperature for consistent evaluation
            )

            # Transform to expected format
            return self._transform_result(result, evaluation_criteria)

        except Exception as e:
            logger.error(f"Error analyzing section: {e}")
            return self._simple_criteria_analysis(section_text, evaluation_criteria)

    def _build_analysis_prompt(
        self,
        section_text: str,
        criteria: list[str]
    ) -> str:
        """Build prompt for structured criteria analysis."""

        criteria_list = "\n".join([f"{i+1}. {c}" for i, c in enumerate(criteria)])

        return f"""You are an expert Horizon Europe proposal evaluator. Analyze this proposal section against the evaluation criteria.

PROPOSAL SECTION:
{section_text}

EVALUATION CRITERIA:
{criteria_list}

TASK:
For each criterion, provide:
1. Whether it's addressed (true/false)
2. Strength score (0.0 to 1.0)
3. Specific evidence from the text
4. Any gaps or weaknesses
5. Specific improvement suggestion

Also provide:
- Overall score (average of all criteria strengths)
- Summary of the analysis
- Top 3 improvements ranked by impact

Be thorough but concise. Base scores on actual content, not assumptions."""

    def _transform_result(
        self,
        result: dict[str, Any],
        criteria: list[str]
    ) -> dict[str, Any]:
        """Transform structured result to expected format."""

        # Build criteria coverage dict
        coverage = {}
        recommendations = []

        for analysis in result.get("criteria_analysis", []):
            criterion_name = analysis.get("criterion_name", "")

            # Find matching criterion from input list
            matched_criterion = None
            for c in criteria:
                if criterion_name.lower() in c.lower() or c.lower() in criterion_name.lower():
                    matched_criterion = c
                    break

            if matched_criterion:
                coverage[matched_criterion] = {
                    "addressed": analysis.get("addressed", False),
                    "strength": analysis.get("strength", 0.5),
                    "evidence": analysis.get("evidence", []),
                    "gaps": analysis.get("gaps", [])
                }

                # Add recommendation if there are gaps
                if analysis.get("gaps"):
                    recommendations.append({
                        "criterion": matched_criterion,
                        "type": "gap",
                        "priority": "high" if analysis.get("strength", 0.5) < 0.5 else "medium",
                        "text": analysis.get("improvement_suggestion", "")
                    })

        return {
            "overall_score": result.get("overall_score", 0.5),
            "criteria_coverage": coverage,
            "recommendations": recommendations,
            "summary": result.get("summary", ""),
            "top_improvements": result.get("top_improvements", [])
        }

    def _simple_criteria_analysis(
        self,
        section_text: str,
        criteria: list[str]
    ) -> dict[str, Any]:
        """Fallback: Simple keyword-based analysis."""

        coverage = {}
        total_score = 0

        for criterion in criteria:
            keywords = [
                word.lower() for word in criterion.split()
                if len(word) > 4 and word.lower() not in ['the', 'and', 'for', 'with', 'that']
            ]

            matches = sum(1 for kw in keywords if kw in section_text.lower())
            strength = min(matches / len(keywords) if keywords else 0, 1.0)

            coverage[criterion] = {
                "addressed": strength > 0.3,
                "strength": strength,
                "evidence": [],
                "gaps": [] if strength > 0.5 else ["Limited evidence found"]
            }

            total_score += strength

        return {
            "overall_score": round(total_score / len(criteria), 2) if criteria else 0,
            "criteria_coverage": coverage,
            "recommendations": [],
            "summary": "Fallback analysis used - AI analysis unavailable",
            "top_improvements": []
        }

    async def compare_versions(
        self,
        version1: str,
        version2: str,
        criteria: list[str]
    ) -> dict[str, Any]:
        """
        Compare two versions of a section against criteria.
        """

        analysis1 = await self.analyze_section(version1, criteria, "")
        analysis2 = await self.analyze_section(version2, criteria, "")

        # Calculate improvement
        score_change = analysis2["overall_score"] - analysis1["overall_score"]

        # Identify specific improvements per criterion
        criterion_changes = {}
        for criterion in criteria:
            old_strength = analysis1["criteria_coverage"].get(criterion, {}).get("strength", 0)
            new_strength = analysis2["criteria_coverage"].get(criterion, {}).get("strength", 0)

            criterion_changes[criterion] = {
                "old_strength": old_strength,
                "new_strength": new_strength,
                "improvement": new_strength - old_strength
            }

        return {
            "version1_score": analysis1["overall_score"],
            "version2_score": analysis2["overall_score"],
            "improvement": score_change,
            "criterion_changes": criterion_changes,
            "recommendation": "Version 2" if score_change > 0 else "Version 1"
        }
