"""
Comprehensive AI-Powered Proposal Reviewer

Multi-pass review simulating EU evaluators for Excellence, Impact, and Implementation.
Provides detailed feedback, scoring, and improvement suggestions.
"""

import os
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ReviewSeverity(str, Enum):
    """Severity levels for review findings."""
    CRITICAL = "critical"  # Must fix before submission
    MAJOR = "major"  # Should fix to improve chances
    MINOR = "minor"  # Nice to fix
    SUGGESTION = "suggestion"  # Optional improvement


class ReviewCategory(str, Enum):
    """Categories for review findings."""
    EXCELLENCE = "excellence"
    IMPACT = "impact"
    IMPLEMENTATION = "implementation"
    COMPLIANCE = "compliance"
    LANGUAGE = "language"
    CONSISTENCY = "consistency"
    BUDGET = "budget"
    CONSORTIUM = "consortium"


@dataclass
class ReviewFinding:
    """A single review finding."""
    severity: ReviewSeverity
    category: ReviewCategory
    section: str
    issue: str
    suggestion: str
    confidence: float = 0.8
    quote: Optional[str] = None  # Relevant quote from proposal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "section": self.section,
            "issue": self.issue,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "quote": self.quote
        }


@dataclass
class ReviewScore:
    """Score for a criterion."""
    criterion: str
    score: float  # 0-5 scale
    max_score: float = 5.0
    justification: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)


class ComprehensiveReviewer:
    """
    Multi-pass AI review simulating EU evaluators.

    Performs separate reviews for:
    - Excellence (scientific/technical quality)
    - Impact (societal/economic outcomes)
    - Implementation (feasibility, consortium, budget)
    - Compliance (EU requirements, ethics)
    - Language (clarity, structure)
    - Consistency (internal coherence)
    """

    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None
            logger.warning("Gemini API key not configured - reviewer disabled")

    async def full_review(
        self,
        proposal: Dict[str, Any],
        call_requirements: Optional[Dict[str, Any]] = None,
        action_type: str = "RIA"
    ) -> Dict[str, Any]:
        """
        Perform comprehensive proposal review.

        Args:
            proposal: Dictionary containing all proposal sections
            call_requirements: Optional call-specific requirements
            action_type: Type of action (RIA, IA, CSA, etc.)

        Returns:
            Comprehensive review with scores, findings, and recommendations
        """
        if not self.model:
            return {"error": "Reviewer not configured - missing API key"}

        logger.info(f"Starting comprehensive review for {action_type} proposal")
        start_time = datetime.now()

        # Run all review passes in parallel
        review_tasks = [
            self._excellence_review(proposal, call_requirements, action_type),
            self._impact_review(proposal, call_requirements, action_type),
            self._implementation_review(proposal, call_requirements, action_type),
            self._compliance_review(proposal, call_requirements),
            self._language_review(proposal),
            self._consistency_review(proposal),
        ]

        reviews = await asyncio.gather(*review_tasks, return_exceptions=True)

        # Process results
        all_findings: List[ReviewFinding] = []
        all_scores: List[ReviewScore] = []

        review_names = ["excellence", "impact", "implementation", "compliance", "language", "consistency"]
        for name, review in zip(review_names, reviews):
            if isinstance(review, Exception):
                logger.error(f"{name} review failed: {review}")
                continue
            all_findings.extend(review.get("findings", []))
            if "score" in review:
                all_scores.append(review["score"])

        # Calculate overall score
        overall_score = self._calculate_overall_score(all_scores, all_findings)

        # Generate summary
        summary = await self._generate_review_summary(all_findings, overall_score)

        # Get recommendation
        recommendation = self._get_recommendation(overall_score, all_findings)

        # Estimate evaluator score
        estimated_score = self._estimate_evaluator_score(overall_score, all_findings)

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "overall_score": overall_score,
            "estimated_evaluator_score": estimated_score,
            "recommendation": recommendation,
            "summary": summary,
            "scores": [asdict(s) if hasattr(s, '__dataclass_fields__') else s for s in all_scores],
            "findings": [f.to_dict() for f in all_findings],
            "findings_by_severity": self._group_by_severity(all_findings),
            "findings_by_category": self._group_by_category(all_findings),
            "review_metadata": {
                "action_type": action_type,
                "sections_reviewed": list(proposal.keys()),
                "total_findings": len(all_findings),
                "duration_ms": round(duration_ms),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    async def _excellence_review(
        self,
        proposal: Dict[str, Any],
        requirements: Optional[Dict[str, Any]],
        action_type: str
    ) -> Dict[str, Any]:
        """Review excellence criterion."""
        excellence_content = proposal.get("excellence", "") or proposal.get("section_1", "")

        if not excellence_content:
            return {
                "findings": [ReviewFinding(
                    severity=ReviewSeverity.CRITICAL,
                    category=ReviewCategory.EXCELLENCE,
                    section="excellence",
                    issue="Excellence section is missing or empty",
                    suggestion="Add detailed excellence section covering objectives, methodology, and beyond state-of-art"
                )],
                "score": ReviewScore(
                    criterion="excellence",
                    score=0.0,
                    justification="Section missing"
                )
            }

        prompt = f"""You are an expert EU Horizon Europe proposal evaluator reviewing the Excellence section.

ACTION TYPE: {action_type}
{"CALL REQUIREMENTS: " + json.dumps(requirements.get('excellence_criteria', '')) if requirements else ""}

PROPOSAL EXCELLENCE SECTION:
{excellence_content[:8000]}

Evaluate against these official EU criteria:
1. Clarity and pertinence of the project's objectives
2. Soundness of the proposed methodology
3. Extent that proposed work is ambitious, beyond state-of-the-art
4. Quality of interdisciplinary approach (if applicable)

For each issue found, provide in JSON format:
{{
    "findings": [
        {{
            "severity": "critical|major|minor|suggestion",
            "issue": "specific issue description",
            "suggestion": "concrete improvement suggestion",
            "quote": "relevant quote from proposal (if applicable)"
        }}
    ],
    "score": {{
        "value": 0-5,
        "justification": "why this score",
        "strengths": ["strength 1", "strength 2"],
        "weaknesses": ["weakness 1"]
    }}
}}

Be thorough but fair. Identify both strengths and weaknesses. Return valid JSON only."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            result = self._parse_json_response(response.text)

            findings = [
                ReviewFinding(
                    severity=ReviewSeverity(f.get("severity", "minor")),
                    category=ReviewCategory.EXCELLENCE,
                    section="excellence",
                    issue=f.get("issue", ""),
                    suggestion=f.get("suggestion", ""),
                    quote=f.get("quote")
                )
                for f in result.get("findings", [])
            ]

            score_data = result.get("score", {})
            score = ReviewScore(
                criterion="excellence",
                score=float(score_data.get("value", 3.0)),
                justification=score_data.get("justification", ""),
                strengths=score_data.get("strengths", []),
                weaknesses=score_data.get("weaknesses", [])
            )

            return {"findings": findings, "score": score}

        except Exception as e:
            logger.error(f"Excellence review failed: {e}")
            return {"findings": [], "score": ReviewScore(criterion="excellence", score=3.0)}

    async def _impact_review(
        self,
        proposal: Dict[str, Any],
        requirements: Optional[Dict[str, Any]],
        action_type: str
    ) -> Dict[str, Any]:
        """Review impact criterion."""
        impact_content = proposal.get("impact", "") or proposal.get("section_2", "")

        if not impact_content:
            return {
                "findings": [ReviewFinding(
                    severity=ReviewSeverity.CRITICAL,
                    category=ReviewCategory.IMPACT,
                    section="impact",
                    issue="Impact section is missing or empty",
                    suggestion="Add impact section covering expected outcomes, exploitation, and communication"
                )],
                "score": ReviewScore(criterion="impact", score=0.0, justification="Section missing")
            }

        prompt = f"""You are an expert EU Horizon Europe proposal evaluator reviewing the Impact section.

ACTION TYPE: {action_type}

PROPOSAL IMPACT SECTION:
{impact_content[:8000]}

Evaluate against these official EU criteria:
1. Credibility of pathways to achieve expected outcomes and impacts
2. Suitability of measures to maximise expected outcomes and impacts (dissemination, exploitation, communication)
3. Quality of proposed measures to evaluate and communicate project activities and results

For each issue, provide JSON:
{{
    "findings": [
        {{
            "severity": "critical|major|minor|suggestion",
            "issue": "specific issue",
            "suggestion": "improvement suggestion"
        }}
    ],
    "score": {{
        "value": 0-5,
        "justification": "score rationale",
        "strengths": [],
        "weaknesses": []
    }}
}}

Return valid JSON only."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            result = self._parse_json_response(response.text)

            findings = [
                ReviewFinding(
                    severity=ReviewSeverity(f.get("severity", "minor")),
                    category=ReviewCategory.IMPACT,
                    section="impact",
                    issue=f.get("issue", ""),
                    suggestion=f.get("suggestion", "")
                )
                for f in result.get("findings", [])
            ]

            score_data = result.get("score", {})
            score = ReviewScore(
                criterion="impact",
                score=float(score_data.get("value", 3.0)),
                justification=score_data.get("justification", ""),
                strengths=score_data.get("strengths", []),
                weaknesses=score_data.get("weaknesses", [])
            )

            return {"findings": findings, "score": score}

        except Exception as e:
            logger.error(f"Impact review failed: {e}")
            return {"findings": [], "score": ReviewScore(criterion="impact", score=3.0)}

    async def _implementation_review(
        self,
        proposal: Dict[str, Any],
        requirements: Optional[Dict[str, Any]],
        action_type: str
    ) -> Dict[str, Any]:
        """Review implementation criterion."""
        impl_content = proposal.get("implementation", "") or proposal.get("section_3", "")
        budget_content = proposal.get("budget", "")
        consortium_content = proposal.get("consortium", "")

        combined = f"""
IMPLEMENTATION:
{impl_content[:5000]}

BUDGET:
{budget_content[:2000]}

CONSORTIUM:
{consortium_content[:2000]}
"""

        prompt = f"""You are an expert EU Horizon Europe proposal evaluator reviewing the Implementation section.

ACTION TYPE: {action_type}

PROPOSAL CONTENT:
{combined}

Evaluate against these official EU criteria:
1. Quality and effectiveness of work plan (work packages, tasks, deliverables, milestones)
2. Appropriateness of management structures and procedures
3. Complementarity of participants and consortium composition
4. Appropriateness of allocated resources (budget, personnel)

For each issue, provide JSON:
{{
    "findings": [
        {{
            "severity": "critical|major|minor|suggestion",
            "issue": "specific issue",
            "suggestion": "improvement suggestion"
        }}
    ],
    "score": {{
        "value": 0-5,
        "justification": "score rationale",
        "strengths": [],
        "weaknesses": []
    }}
}}

Return valid JSON only."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            result = self._parse_json_response(response.text)

            findings = [
                ReviewFinding(
                    severity=ReviewSeverity(f.get("severity", "minor")),
                    category=ReviewCategory.IMPLEMENTATION,
                    section="implementation",
                    issue=f.get("issue", ""),
                    suggestion=f.get("suggestion", "")
                )
                for f in result.get("findings", [])
            ]

            score_data = result.get("score", {})
            score = ReviewScore(
                criterion="implementation",
                score=float(score_data.get("value", 3.0)),
                justification=score_data.get("justification", ""),
                strengths=score_data.get("strengths", []),
                weaknesses=score_data.get("weaknesses", [])
            )

            return {"findings": findings, "score": score}

        except Exception as e:
            logger.error(f"Implementation review failed: {e}")
            return {"findings": [], "score": ReviewScore(criterion="implementation", score=3.0)}

    async def _compliance_review(
        self,
        proposal: Dict[str, Any],
        requirements: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Review compliance with EU requirements."""
        findings = []

        # Check for required elements
        required_sections = ["excellence", "impact", "implementation"]
        for section in required_sections:
            content = proposal.get(section, "") or proposal.get(f"section_{required_sections.index(section)+1}", "")
            if not content:
                findings.append(ReviewFinding(
                    severity=ReviewSeverity.CRITICAL,
                    category=ReviewCategory.COMPLIANCE,
                    section=section,
                    issue=f"Required section '{section}' is missing",
                    suggestion=f"Add the {section} section as required by EU guidelines"
                ))

        # Check ethics mentions
        all_content = " ".join(str(v) for v in proposal.values() if isinstance(v, str))

        ethics_keywords = ["ethics", "gdpr", "data protection", "informed consent"]
        if not any(kw in all_content.lower() for kw in ethics_keywords):
            findings.append(ReviewFinding(
                severity=ReviewSeverity.MAJOR,
                category=ReviewCategory.COMPLIANCE,
                section="ethics",
                issue="No mention of ethics or data protection considerations",
                suggestion="Add ethics section addressing potential ethical issues and GDPR compliance"
            ))

        # Check gender dimension
        if "gender" not in all_content.lower():
            findings.append(ReviewFinding(
                severity=ReviewSeverity.MINOR,
                category=ReviewCategory.COMPLIANCE,
                section="impact",
                issue="Gender dimension not explicitly addressed",
                suggestion="Consider how the project addresses gender aspects in research content and team composition"
            ))

        return {"findings": findings}

    async def _language_review(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Review language quality and clarity."""
        all_content = " ".join(str(v) for v in proposal.values() if isinstance(v, str))

        if len(all_content) < 500:
            return {
                "findings": [ReviewFinding(
                    severity=ReviewSeverity.MAJOR,
                    category=ReviewCategory.LANGUAGE,
                    section="all",
                    issue="Proposal content is very short",
                    suggestion="Expand proposal with more detailed content in all sections"
                )]
            }

        prompt = f"""Analyze this EU proposal for language quality. Focus on:
1. Clarity and readability
2. Technical accuracy
3. Grammar and spelling
4. Jargon overuse
5. Passive voice overuse

PROPOSAL TEXT (excerpt):
{all_content[:6000]}

Return JSON with findings:
{{
    "findings": [
        {{
            "severity": "minor|suggestion",
            "issue": "language issue",
            "suggestion": "how to improve",
            "quote": "problematic text if applicable"
        }}
    ]
}}

Return valid JSON only."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            result = self._parse_json_response(response.text)

            findings = [
                ReviewFinding(
                    severity=ReviewSeverity(f.get("severity", "suggestion")),
                    category=ReviewCategory.LANGUAGE,
                    section="language",
                    issue=f.get("issue", ""),
                    suggestion=f.get("suggestion", ""),
                    quote=f.get("quote")
                )
                for f in result.get("findings", [])
            ]

            return {"findings": findings}

        except Exception as e:
            logger.error(f"Language review failed: {e}")
            return {"findings": []}

    async def _consistency_review(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Check internal consistency across sections."""
        proposal_json = json.dumps(proposal, indent=2, default=str)[:10000]

        prompt = f"""Check this EU proposal for internal consistency issues:

1. Budget figures matching between sections
2. Timeline consistency with deliverables
3. Partner roles consistent across sections
4. Objectives alignment with methodology
5. Impact claims supported by activities
6. Acronyms and terminology consistency
7. Work package descriptions matching Gantt chart

PROPOSAL:
{proposal_json}

Return JSON with inconsistencies found:
{{
    "findings": [
        {{
            "severity": "major|minor",
            "issue": "inconsistency description",
            "suggestion": "how to resolve"
        }}
    ]
}}

Return valid JSON only."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            result = self._parse_json_response(response.text)

            findings = [
                ReviewFinding(
                    severity=ReviewSeverity(f.get("severity", "minor")),
                    category=ReviewCategory.CONSISTENCY,
                    section="consistency",
                    issue=f.get("issue", ""),
                    suggestion=f.get("suggestion", "")
                )
                for f in result.get("findings", [])
            ]

            return {"findings": findings}

        except Exception as e:
            logger.error(f"Consistency review failed: {e}")
            return {"findings": []}

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from AI response."""
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()

            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response: {text[:200]}")
            return {"findings": [], "score": {"value": 3.0}}

    def _calculate_overall_score(
        self,
        scores: List[ReviewScore],
        findings: List[ReviewFinding]
    ) -> float:
        """Calculate overall proposal score."""
        if not scores:
            return 3.0

        # Weighted average of criterion scores
        weights = {
            "excellence": 0.4,
            "impact": 0.3,
            "implementation": 0.3
        }

        total_weight = 0
        weighted_sum = 0

        for score in scores:
            weight = weights.get(score.criterion, 0.1)
            weighted_sum += score.score * weight
            total_weight += weight

        base_score = weighted_sum / max(total_weight, 0.1)

        # Adjust for critical findings
        critical_count = len([f for f in findings if f.severity == ReviewSeverity.CRITICAL])
        major_count = len([f for f in findings if f.severity == ReviewSeverity.MAJOR])

        penalty = (critical_count * 0.3) + (major_count * 0.1)
        final_score = max(0, base_score - penalty)

        return round(final_score, 2)

    async def _generate_review_summary(
        self,
        findings: List[ReviewFinding],
        score: float
    ) -> str:
        """Generate executive summary of the review."""
        critical = [f for f in findings if f.severity == ReviewSeverity.CRITICAL]
        major = [f for f in findings if f.severity == ReviewSeverity.MAJOR]

        if score >= 4.0:
            status = "strong"
        elif score >= 3.0:
            status = "adequate"
        else:
            status = "needs significant improvement"

        summary = f"""Overall Assessment: This proposal is {status} with a score of {score}/5.

Key Statistics:
- Critical issues: {len(critical)}
- Major issues: {len(major)}
- Total findings: {len(findings)}
"""

        if critical:
            summary += "\nCritical Issues (must fix):\n"
            for f in critical[:3]:
                summary += f"- {f.issue}\n"

        if major:
            summary += "\nMajor Issues (should fix):\n"
            for f in major[:3]:
                summary += f"- {f.issue}\n"

        return summary

    def _get_recommendation(
        self,
        score: float,
        findings: List[ReviewFinding]
    ) -> Dict[str, Any]:
        """Get submission recommendation."""
        critical_count = len([f for f in findings if f.severity == ReviewSeverity.CRITICAL])
        major_count = len([f for f in findings if f.severity == ReviewSeverity.MAJOR])

        if critical_count > 0:
            return {
                "status": "NOT_READY",
                "message": f"Address {critical_count} critical issue(s) before submission",
                "confidence": "high"
            }
        elif major_count > 3:
            return {
                "status": "NEEDS_WORK",
                "message": f"Address {major_count} major issues to improve success chances",
                "confidence": "medium"
            }
        elif score >= 4.0:
            return {
                "status": "READY",
                "message": "Proposal is competitive. Consider minor improvements.",
                "confidence": "high"
            }
        elif score >= 3.0:
            return {
                "status": "ACCEPTABLE",
                "message": "Meets threshold but improvements recommended for better chances",
                "confidence": "medium"
            }
        else:
            return {
                "status": "BELOW_THRESHOLD",
                "message": "Significant revision needed to be competitive",
                "confidence": "high"
            }

    def _estimate_evaluator_score(
        self,
        score: float,
        findings: List[ReviewFinding]
    ) -> Dict[str, Any]:
        """Estimate likely evaluator score range."""
        # EU uses 0-5 scale with threshold of 3 per criterion
        # Overall threshold typically 10/15 or similar

        # Add uncertainty based on findings
        uncertainty = min(0.5, len(findings) * 0.05)

        low = max(0, score - uncertainty)
        high = min(5, score + uncertainty)

        return {
            "estimated_range": f"{low:.1f} - {high:.1f}",
            "threshold_status": "above" if score >= 3.0 else "below",
            "confidence": "medium",
            "note": "Actual scores may vary based on evaluator interpretation and competition level"
        }

    def _group_by_severity(self, findings: List[ReviewFinding]) -> Dict[str, List[Dict]]:
        """Group findings by severity."""
        grouped = {s.value: [] for s in ReviewSeverity}
        for f in findings:
            grouped[f.severity.value].append(f.to_dict())
        return grouped

    def _group_by_category(self, findings: List[ReviewFinding]) -> Dict[str, List[Dict]]:
        """Group findings by category."""
        grouped = {c.value: [] for c in ReviewCategory}
        for f in findings:
            grouped[f.category.value].append(f.to_dict())
        return grouped


# Singleton instance
_reviewer = None


def get_comprehensive_reviewer(db_pool=None) -> ComprehensiveReviewer:
    """Get singleton reviewer instance."""
    global _reviewer
    if _reviewer is None:
        _reviewer = ComprehensiveReviewer(db_pool)
    return _reviewer
