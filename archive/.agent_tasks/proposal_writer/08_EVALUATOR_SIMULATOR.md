# Task 08: Build Evaluator Simulator Service

> **Phase:** 2 - Evaluator Simulation
> **Priority:** P1 (Core Value)
> **Estimated Effort:** 6-8 hours
> **Status:** Not Started
> **Depends On:** Tasks 01-04

---

## Problem Statement

Users have no idea how evaluators will score their proposals. The current system provides:
- Generic quality metrics (readability, terminology)
- Basic compliance checking

But it **doesn't** tell users:
- What score they might receive (0-5 scale)
- What evaluators specifically look for
- How to increase their score by 0.5 points
- What the Evaluation Summary Report (ESR) would say

---

## Solution: Evaluator Simulator

Create a service that simulates EU evaluator behavior:
1. Score sections on 0-5 scale (like real evaluators)
2. Provide criterion-by-criterion assessment
3. Show what ESR comments would look like
4. Identify specific changes to improve score

---

## Horizon Europe Evaluation Background

### Scoring Scale
- **5 - Excellent**: Proposal successfully addresses all relevant aspects
- **4 - Very Good**: Proposal addresses the criterion very well, minor improvements possible
- **3 - Good**: Proposal addresses the criterion well, improvements needed
- **2 - Fair**: Proposal broadly addresses the criterion, significant weaknesses
- **1 - Poor**: Criterion is inadequately addressed, serious weaknesses
- **0 - Fail**: Proposal fails to address the criterion or cannot be assessed

### Threshold
- Individual threshold: **3.0** per criterion
- Overall threshold: Varies by call (typically 10/15 or 13/15)

### Evaluation Criteria by Section

**Excellence (max 5 points)**
- Clarity and pertinence of objectives
- Soundness of the concept and methodology
- Extent project is beyond state of the art
- Appropriate consideration of interdisciplinary, gender aspects

**Impact (max 5 points)**
- Credibility of pathways to achieve impacts
- Suitability of measures for exploitation/dissemination
- Significance of communication activities

**Implementation (max 5 points)**
- Coherence of work plan
- Quality and complementarity of consortium
- Appropriateness of management and resource allocation

---

## Implementation

### Step 1: Create Evaluator Simulator Service

**File:** `app/services/proposal_writing/evaluator_simulator.py`

```python
"""
Evaluator Simulator Service

Simulate EU evaluator scoring to help users predict and improve scores.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.services.proposal_writing.proposal_ai_service import ProposalAIService
from app.services.proposal_writing.schemas.ai_schemas import EVALUATOR_SIMULATION_SCHEMA

logger = logging.getLogger(__name__)


class ScoreLevel(Enum):
    EXCELLENT = 5
    VERY_GOOD = 4
    GOOD = 3
    FAIR = 2
    POOR = 1
    FAIL = 0


@dataclass
class CriterionScore:
    """Score for a single criterion."""
    criterion: str
    score: float
    justification: str
    strengths: List[str]
    weaknesses: List[str]
    improvement_for_half_point: str


@dataclass
class EvaluationResult:
    """Complete evaluation result for a section."""
    section_type: str
    overall_score: float
    criterion_scores: List[CriterionScore]
    esr_summary: str
    strengths: List[str]
    weaknesses: List[str]
    top_improvements: List[Dict[str, Any]]
    threshold_status: str  # 'above', 'at', 'below'
    confidence: float


class EvaluatorSimulator:
    """
    Simulate EU Horizon Europe evaluator scoring.

    Features:
    - Score sections on 0-5 scale
    - Criterion-by-criterion breakdown
    - ESR-style summary
    - Specific improvement suggestions
    """

    # Standard evaluation criteria by section
    CRITERIA = {
        "excellence": {
            "objectives": [
                "Clarity and pertinence of the project's objectives",
                "Soundness of the proposed methodology",
                "Ambition and innovation potential"
            ],
            "methodology": [
                "Soundness and credibility of the methodology",
                "Appropriateness of the approach to the objectives",
                "Quality of the interdisciplinary approach (if relevant)"
            ],
            "beyond_sota": [
                "Extent the proposed work is beyond state of the art",
                "Innovation potential (scientific, technical, societal)",
                "Appropriate consideration of gender dimension"
            ]
        },
        "impact": {
            "pathways": [
                "Credibility of the pathways to achieve expected impacts",
                "Scale and significance of project's contribution to expected impacts",
                "Suitability of project's contribution to the Work Programme"
            ],
            "dissemination": [
                "Quality of proposed measures for exploitation of results",
                "Quality of proposed dissemination measures",
                "Quality of proposed communication activities"
            ]
        },
        "implementation": {
            "work_plan": [
                "Coherence and effectiveness of the work plan",
                "Appropriateness of the effort allocation",
                "Quality and realism of the timeline"
            ],
            "consortium": [
                "Quality, relevant expertise and complementarity of the consortium",
                "Appropriateness of the management structures",
                "Appropriateness of resource allocation (budget)"
            ]
        }
    }

    # Score thresholds
    SECTION_THRESHOLD = 3.0
    FUNDING_THRESHOLD = 10.0  # Out of 15 total

    def __init__(self):
        self.ai_service = ProposalAIService()

    async def evaluate_section(
        self,
        section_text: str,
        section_type: str,
        section_id: str,
        call_id: str = None,
        action_type: str = "RIA"
    ) -> EvaluationResult:
        """
        Evaluate a proposal section as an EU evaluator would.

        Args:
            section_text: The section content to evaluate
            section_type: 'excellence', 'impact', or 'implementation'
            section_id: Specific section (e.g., 'objectives', 'methodology')
            call_id: Optional call ID for context
            action_type: RIA, IA, CSA (affects criteria weights)

        Returns:
            Complete evaluation with scores and recommendations
        """

        logger.info(f"Evaluating {section_type}.{section_id} section")

        # Get relevant criteria
        criteria = self._get_criteria(section_type, section_id)

        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(
            section_text=section_text,
            section_type=section_type,
            section_id=section_id,
            criteria=criteria,
            action_type=action_type
        )

        try:
            # Get AI evaluation
            result = await self.ai_service.generate_structured(
                prompt=prompt,
                response_schema=EVALUATOR_SIMULATION_SCHEMA,
                temperature=0.2  # Low temperature for consistent evaluation
            )

            return self._parse_evaluation_result(
                result=result,
                section_type=section_type,
                section_id=section_id,
                criteria=criteria
            )

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return self._fallback_evaluation(
                section_text=section_text,
                section_type=section_type,
                section_id=section_id,
                criteria=criteria
            )

    def _get_criteria(self, section_type: str, section_id: str) -> List[str]:
        """Get evaluation criteria for section."""

        section_criteria = self.CRITERIA.get(section_type, {})
        return section_criteria.get(section_id, [
            "Clarity and completeness",
            "Relevance to call objectives",
            "Quality of content"
        ])

    def _build_evaluation_prompt(
        self,
        section_text: str,
        section_type: str,
        section_id: str,
        criteria: List[str],
        action_type: str
    ) -> str:
        """Build prompt for evaluator simulation."""

        criteria_list = "\n".join([f"- {c}" for c in criteria])

        return f"""You are an expert Horizon Europe evaluator with 10+ years of experience evaluating {action_type} proposals.

TASK: Evaluate this proposal section as if you were writing the Evaluation Summary Report (ESR).

SECTION TYPE: {section_type.upper()} - {section_id}
ACTION TYPE: {action_type}

SECTION CONTENT:
{section_text}

EVALUATION CRITERIA:
{criteria_list}

SCORING GUIDELINES:
- 5 (Excellent): Successfully addresses all relevant aspects. Any shortcomings are minor.
- 4 (Very Good): Addresses the criterion very well, but small improvements possible.
- 3 (Good): Addresses the criterion well, but improvements needed.
- 2 (Fair): Broadly addresses the criterion, but significant weaknesses.
- 1 (Poor): Inadequately addressed, serious weaknesses.
- 0 (Fail): Fails to address the criterion or cannot be assessed.

THRESHOLD: A score of 3.0 or higher is needed to pass this section.

YOUR TASK:
1. Score each criterion on 0-5 scale (use 0.5 increments)
2. Calculate overall section score (average of criteria)
3. Write an ESR-style summary (3-4 sentences, formal evaluator tone)
4. List specific strengths and weaknesses
5. For each criterion below 4.5, explain exactly what would add 0.5 to the score

Be rigorous but fair. Base your evaluation on:
- Clarity and specificity of content
- Alignment with Horizon Europe expectations
- Scientific/technical quality
- European added value
- Innovation level (for Excellence)
- Impact potential (for Impact)
- Feasibility (for Implementation)

Evaluate as a real EU evaluator would - thorough, objective, and constructive."""

    def _parse_evaluation_result(
        self,
        result: Dict[str, Any],
        section_type: str,
        section_id: str,
        criteria: List[str]
    ) -> EvaluationResult:
        """Parse AI result into EvaluationResult."""

        overall_score = result.get("overall_score", 3.0)

        # Parse criterion scores
        criterion_scores = []
        for cs in result.get("criteria_scores", []):
            criterion_scores.append(CriterionScore(
                criterion=cs.get("criterion", "Unknown"),
                score=cs.get("score", 3.0),
                justification=cs.get("justification", ""),
                strengths=cs.get("strengths", []),
                weaknesses=cs.get("weaknesses", []),
                improvement_for_half_point=cs.get("improvement_for_half_point", "")
            ))

        # Determine threshold status
        if overall_score >= 4.0:
            threshold_status = "above"
        elif overall_score >= self.SECTION_THRESHOLD:
            threshold_status = "at"
        else:
            threshold_status = "below"

        # Parse improvements
        top_improvements = []
        for imp in result.get("top_improvements", []):
            if isinstance(imp, dict):
                top_improvements.append(imp)
            else:
                top_improvements.append({
                    "improvement": str(imp),
                    "expected_score_increase": 0.5
                })

        return EvaluationResult(
            section_type=section_type,
            overall_score=overall_score,
            criterion_scores=criterion_scores,
            esr_summary=result.get("evaluator_summary", ""),
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
            top_improvements=top_improvements,
            threshold_status=threshold_status,
            confidence=0.85
        )

    def _fallback_evaluation(
        self,
        section_text: str,
        section_type: str,
        section_id: str,
        criteria: List[str]
    ) -> EvaluationResult:
        """Fallback rule-based evaluation."""

        # Simple heuristics
        word_count = len(section_text.split())
        has_headings = '#' in section_text or ':' in section_text

        # Base score
        base_score = 3.0

        # Adjust for length
        if word_count > 500:
            base_score += 0.5
        elif word_count < 200:
            base_score -= 0.5

        # Adjust for structure
        if has_headings:
            base_score += 0.25

        # Check for key terms
        key_terms = ['innovative', 'european', 'impact', 'beyond', 'state of the art']
        term_count = sum(1 for t in key_terms if t in section_text.lower())
        base_score += min(term_count * 0.1, 0.5)

        # Clamp score
        final_score = max(1.0, min(5.0, base_score))

        return EvaluationResult(
            section_type=section_type,
            overall_score=final_score,
            criterion_scores=[
                CriterionScore(
                    criterion=c,
                    score=final_score,
                    justification="Automated assessment - detailed AI evaluation unavailable",
                    strengths=[],
                    weaknesses=["Detailed analysis requires AI evaluation"],
                    improvement_for_half_point=""
                )
                for c in criteria
            ],
            esr_summary="Automated assessment. Please retry for detailed evaluation.",
            strengths=["Section is present and contains content"],
            weaknesses=["Detailed analysis unavailable"],
            top_improvements=[{
                "improvement": "Retry for detailed AI-powered evaluation",
                "expected_score_increase": 0.0
            }],
            threshold_status="at" if final_score >= 3.0 else "below",
            confidence=0.3
        )

    async def evaluate_full_proposal(
        self,
        sections: Dict[str, str],
        action_type: str = "RIA"
    ) -> Dict[str, Any]:
        """
        Evaluate all sections and calculate total score.

        Args:
            sections: Dict of section_id -> text
            action_type: RIA, IA, CSA

        Returns:
            {
                "total_score": 12.5,
                "max_score": 15,
                "threshold": 10,
                "above_threshold": True,
                "section_scores": {...},
                "overall_assessment": "...",
                "funding_probability": 0.7
            }
        """

        section_results = {}

        # Map section IDs to types
        section_mapping = {
            "excellence.objectives": ("excellence", "objectives"),
            "excellence.methodology": ("excellence", "methodology"),
            "excellence.beyond_sota": ("excellence", "beyond_sota"),
            "impact.pathways": ("impact", "pathways"),
            "impact.dissemination": ("impact", "dissemination"),
            "implementation.work_plan": ("implementation", "work_plan"),
            "implementation.consortium": ("implementation", "consortium")
        }

        # Evaluate each section
        for section_id, text in sections.items():
            if section_id in section_mapping:
                section_type, sub_section = section_mapping[section_id]
                result = await self.evaluate_section(
                    section_text=text,
                    section_type=section_type,
                    section_id=sub_section,
                    action_type=action_type
                )
                section_results[section_id] = result

        # Calculate overall scores per main section
        excellence_scores = [
            r.overall_score for k, r in section_results.items()
            if k.startswith("excellence")
        ]
        impact_scores = [
            r.overall_score for k, r in section_results.items()
            if k.startswith("impact")
        ]
        implementation_scores = [
            r.overall_score for k, r in section_results.items()
            if k.startswith("implementation")
        ]

        excellence_avg = sum(excellence_scores) / len(excellence_scores) if excellence_scores else 0
        impact_avg = sum(impact_scores) / len(impact_scores) if impact_scores else 0
        implementation_avg = sum(implementation_scores) / len(implementation_scores) if implementation_scores else 0

        total_score = excellence_avg + impact_avg + implementation_avg
        max_score = 15.0
        threshold = 10.0

        # Estimate funding probability
        funding_probability = self._estimate_funding_probability(
            total_score=total_score,
            excellence=excellence_avg,
            impact=impact_avg,
            implementation=implementation_avg,
            action_type=action_type
        )

        return {
            "total_score": round(total_score, 1),
            "max_score": max_score,
            "threshold": threshold,
            "above_threshold": total_score >= threshold,
            "section_scores": {
                "excellence": round(excellence_avg, 1),
                "impact": round(impact_avg, 1),
                "implementation": round(implementation_avg, 1)
            },
            "detailed_results": {
                k: {
                    "score": r.overall_score,
                    "status": r.threshold_status,
                    "summary": r.esr_summary
                }
                for k, r in section_results.items()
            },
            "overall_assessment": self._generate_overall_assessment(
                total_score, excellence_avg, impact_avg, implementation_avg
            ),
            "funding_probability": funding_probability,
            "recommendation": self._generate_recommendation(total_score, section_results)
        }

    def _estimate_funding_probability(
        self,
        total_score: float,
        excellence: float,
        impact: float,
        implementation: float,
        action_type: str
    ) -> float:
        """Estimate probability of funding based on scores."""

        # These are rough estimates based on typical success rates
        # Real probability depends on competition level

        if total_score < 10:
            return 0.05  # Below threshold

        # Base probability by score
        if total_score >= 14:
            base_prob = 0.85
        elif total_score >= 13:
            base_prob = 0.60
        elif total_score >= 12:
            base_prob = 0.35
        elif total_score >= 11:
            base_prob = 0.20
        else:
            base_prob = 0.10

        # Adjust for section balance
        min_section = min(excellence, impact, implementation)
        if min_section < 3.0:
            base_prob *= 0.3  # Below threshold in any section is very bad

        return round(base_prob, 2)

    def _generate_overall_assessment(
        self,
        total: float,
        excellence: float,
        impact: float,
        implementation: float
    ) -> str:
        """Generate overall assessment text."""

        if total >= 13:
            return (
                f"This proposal is highly competitive with a total score of {total:.1f}/15. "
                f"All sections score above threshold with Excellence ({excellence:.1f}), "
                f"Impact ({impact:.1f}), and Implementation ({implementation:.1f}). "
                f"The proposal demonstrates strong potential for funding."
            )
        elif total >= 10:
            weak = []
            if excellence < 4:
                weak.append("Excellence")
            if impact < 4:
                weak.append("Impact")
            if implementation < 4:
                weak.append("Implementation")

            return (
                f"This proposal meets the funding threshold with {total:.1f}/15. "
                f"{'The ' + ', '.join(weak) + ' section(s) could be strengthened. ' if weak else ''}"
                f"With targeted improvements, this proposal could be more competitive."
            )
        else:
            return (
                f"This proposal scores {total:.1f}/15, below the typical threshold of 10/15. "
                f"Significant improvements are needed, particularly in sections scoring below 3.0. "
                f"Focus on addressing the identified weaknesses before submission."
            )

    def _generate_recommendation(
        self,
        total_score: float,
        section_results: Dict[str, EvaluationResult]
    ) -> str:
        """Generate actionable recommendation."""

        if total_score >= 13:
            return "Focus on final polish. Consider addressing minor weaknesses in lowest-scoring section."

        # Find weakest section
        weakest = min(section_results.items(), key=lambda x: x[1].overall_score)
        weakest_id, weakest_result = weakest

        if weakest_result.overall_score < 3.0:
            return f"URGENT: {weakest_id} scores {weakest_result.overall_score:.1f}/5, below threshold. Must address: {weakest_result.top_improvements[0]['improvement'] if weakest_result.top_improvements else 'see detailed feedback'}"

        return f"Prioritize improving {weakest_id} (currently {weakest_result.overall_score:.1f}/5). Potential gain: {weakest_result.top_improvements[0]['expected_score_increase'] if weakest_result.top_improvements else 0.5} points."
```

---

### Step 2: Add Score Visualization Helpers

**File:** `app/services/proposal_writing/score_visualizer.py`

```python
"""
Score Visualization Helpers

Generate visual representations of evaluation scores.
"""

from typing import Dict, Any, List


def generate_score_bar(score: float, max_score: float = 5.0) -> str:
    """Generate a text-based score bar."""

    filled = int((score / max_score) * 10)
    empty = 10 - filled

    bar = "█" * filled + "░" * empty
    percentage = (score / max_score) * 100

    return f"[{bar}] {score:.1f}/{max_score:.0f} ({percentage:.0f}%)"


def generate_score_summary(evaluation_result: Dict[str, Any]) -> str:
    """Generate a formatted score summary."""

    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("EVALUATION SUMMARY")
    lines.append("=" * 60)
    lines.append("")

    # Total score
    total = evaluation_result.get("total_score", 0)
    threshold = evaluation_result.get("threshold", 10)
    status = "✅ ABOVE THRESHOLD" if total >= threshold else "❌ BELOW THRESHOLD"

    lines.append(f"Total Score: {total:.1f}/15 {status}")
    lines.append(generate_score_bar(total, 15))
    lines.append("")

    # Section scores
    section_scores = evaluation_result.get("section_scores", {})

    lines.append("Section Breakdown:")
    for section, score in section_scores.items():
        status_emoji = "✅" if score >= 3 else "⚠️" if score >= 2 else "❌"
        lines.append(f"  {status_emoji} {section.title()}: {generate_score_bar(score, 5)}")

    lines.append("")

    # Funding probability
    prob = evaluation_result.get("funding_probability", 0)
    prob_bar = "█" * int(prob * 10) + "░" * (10 - int(prob * 10))
    lines.append(f"Funding Probability: [{prob_bar}] {prob*100:.0f}%")

    lines.append("")
    lines.append("-" * 60)

    # Assessment
    lines.append("Assessment:")
    lines.append(evaluation_result.get("overall_assessment", ""))

    lines.append("")
    lines.append("-" * 60)

    # Recommendation
    lines.append("Next Steps:")
    lines.append(f"→ {evaluation_result.get('recommendation', '')}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def generate_criterion_table(criterion_scores: List[Dict]) -> str:
    """Generate a table of criterion scores."""

    lines = []
    lines.append("| Criterion | Score | Status |")
    lines.append("|-----------|-------|--------|")

    for cs in criterion_scores:
        score = cs.get("score", 0)
        if score >= 4:
            status = "✅ Strong"
        elif score >= 3:
            status = "⚡ Acceptable"
        else:
            status = "❌ Needs Work"

        criterion_short = cs.get("criterion", "")[:40]
        lines.append(f"| {criterion_short}... | {score:.1f} | {status} |")

    return "\n".join(lines)
```

---

### Step 3: Create API Endpoints

**File:** Add to `app/api/proposal_routes.py`

```python
# Add these imports
from app.services.proposal_writing.evaluator_simulator import EvaluatorSimulator
from app.services.proposal_writing.score_visualizer import generate_score_summary

evaluator = EvaluatorSimulator()


class EvaluateSectionRequest(BaseModel):
    section_text: str
    section_type: str  # 'excellence', 'impact', 'implementation'
    section_id: str  # 'objectives', 'methodology', etc.
    action_type: str = "RIA"


class EvaluateProposalRequest(BaseModel):
    sections: Dict[str, str]  # section_id -> text
    action_type: str = "RIA"


@router.post("/evaluate/section")
async def evaluate_section(request: EvaluateSectionRequest):
    """
    Evaluate a single section as an EU evaluator would.

    Returns:
    - Score on 0-5 scale
    - Criterion-by-criterion breakdown
    - ESR-style summary
    - Specific improvements to increase score
    """
    try:
        result = await evaluator.evaluate_section(
            section_text=request.section_text,
            section_type=request.section_type,
            section_id=request.section_id,
            action_type=request.action_type
        )

        return {
            "overall_score": result.overall_score,
            "threshold_status": result.threshold_status,
            "esr_summary": result.esr_summary,
            "criterion_scores": [
                {
                    "criterion": cs.criterion,
                    "score": cs.score,
                    "justification": cs.justification,
                    "strengths": cs.strengths,
                    "weaknesses": cs.weaknesses,
                    "improvement_for_half_point": cs.improvement_for_half_point
                }
                for cs in result.criterion_scores
            ],
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "top_improvements": result.top_improvements,
            "confidence": result.confidence
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate/proposal")
async def evaluate_full_proposal(request: EvaluateProposalRequest):
    """
    Evaluate all sections and calculate total score.

    Returns:
    - Total score out of 15
    - Section-by-section breakdown
    - Funding probability estimate
    - Overall assessment and recommendation
    """
    try:
        result = await evaluator.evaluate_full_proposal(
            sections=request.sections,
            action_type=request.action_type
        )

        # Add formatted summary
        result["formatted_summary"] = generate_score_summary(result)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Testing Plan

```python
# tests/test_evaluator_simulator.py

import pytest
from app.services.proposal_writing.evaluator_simulator import EvaluatorSimulator

@pytest.fixture
def evaluator():
    return EvaluatorSimulator()

@pytest.mark.asyncio
async def test_evaluate_section_returns_score(evaluator):
    """Test that evaluation returns a valid score."""

    result = await evaluator.evaluate_section(
        section_text="""
        The project aims to develop innovative AI solutions for healthcare diagnostics.
        Our methodology combines machine learning with clinical validation across
        multiple European hospitals. We will advance the state of the art in
        medical image analysis through novel deep learning architectures.
        The consortium brings together leading research institutions and
        healthcare providers from 5 EU countries.
        """,
        section_type="excellence",
        section_id="objectives",
        action_type="RIA"
    )

    assert 0 <= result.overall_score <= 5
    assert result.threshold_status in ['above', 'at', 'below']
    assert len(result.esr_summary) > 50

@pytest.mark.asyncio
async def test_score_improves_with_better_content(evaluator):
    """Test that better content gets higher scores."""

    weak_text = "We will do research. It will be good."

    strong_text = """
    This project addresses a critical gap in European healthcare by developing
    breakthrough AI-powered diagnostic tools that will significantly improve
    early cancer detection rates across EU member states. Our innovative approach
    combines state-of-the-art deep learning with clinical expertise from
    leading European cancer centers. The methodology has been validated through
    preliminary studies showing 40% improvement over current diagnostic accuracy.
    The consortium brings together world-class research institutions, clinical
    partners, and innovative SMEs from 7 EU countries, ensuring both scientific
    excellence and rapid translation to clinical practice.
    """

    weak_result = await evaluator.evaluate_section(
        section_text=weak_text,
        section_type="excellence",
        section_id="objectives"
    )

    strong_result = await evaluator.evaluate_section(
        section_text=strong_text,
        section_type="excellence",
        section_id="objectives"
    )

    assert strong_result.overall_score > weak_result.overall_score

@pytest.mark.asyncio
async def test_evaluate_full_proposal(evaluator):
    """Test full proposal evaluation."""

    sections = {
        "excellence.objectives": "We develop AI solutions with innovative methodology...",
        "excellence.methodology": "Our approach uses machine learning and clinical trials...",
        "impact.pathways": "The impact will be significant for European healthcare...",
        "implementation.work_plan": "The project spans 36 months with 6 work packages..."
    }

    result = await evaluator.evaluate_full_proposal(
        sections=sections,
        action_type="RIA"
    )

    assert "total_score" in result
    assert "section_scores" in result
    assert "funding_probability" in result
    assert 0 <= result["funding_probability"] <= 1
```

---

## Acceptance Criteria

- [ ] Section evaluation returns score on 0-5 scale
- [ ] Criterion breakdown matches Horizon Europe criteria
- [ ] ESR summary reads like actual evaluator feedback
- [ ] Improvements are specific and actionable
- [ ] Full proposal evaluation calculates correct totals
- [ ] Funding probability is realistic (not always high)
- [ ] Better content consistently scores higher

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `app/services/proposal_writing/evaluator_simulator.py` | CREATE |
| `app/services/proposal_writing/score_visualizer.py` | CREATE |
| `app/services/proposal_writing/schemas/ai_schemas.py` | MODIFY (add schema) |
| `app/api/proposal_routes.py` | MODIFY (add endpoints) |
| `tests/test_evaluator_simulator.py` | CREATE |

---

## Next Task

After completing this task, proceed to:
→ **Task 09: Score Prediction Integration**
