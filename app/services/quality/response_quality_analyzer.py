"""
Response Quality Analyzer for AI Response Validation.

This module provides comprehensive analysis of AI-generated responses to detect:
- Deflection patterns (vague, unhelpful responses)
- Content completeness (missing required elements)
- Response quality scoring
- Category classification

CRITICAL: A test that passes when the AI returns "I could not find specific details"
or similar deflection phrases is WORTHLESS. This analyzer catches such failures.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ResponseCategory(str, Enum):
    """Category classification for AI responses."""

    COMPLETE = "complete"  # All required elements present, high quality
    PARTIAL = "partial"  # Some elements present, acceptable quality
    DEFLECTION = "deflection"  # Vague, unhelpful, or evasive response
    EMPTY = "empty"  # No meaningful content
    ERROR = "error"  # Error response or failed tool execution


@dataclass
class ContentRequirement:
    """Defines a required content element for validation."""

    name: str
    patterns: list[str]  # Regex patterns that indicate presence
    weight: float = 1.0  # Importance weight for scoring
    required: bool = True  # Whether this element is mandatory

    def matches(self, text: str) -> bool:
        """Check if any pattern matches the text (case-insensitive)."""
        text_lower = text.lower()
        for pattern in self.patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False


@dataclass
class QualityAnalysis:
    """Result of quality analysis for an AI response."""

    score: int  # 0-100 quality score
    category: ResponseCategory
    confidence: float  # 0.0-1.0 confidence in the analysis
    missing_elements: list[str] = field(default_factory=list)
    deflection_phrases_found: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    matched_elements: list[str] = field(default_factory=list)
    response_length: int = 0
    tool_results_analyzed: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_acceptable(self, min_score: int = 70) -> bool:
        """Check if the response meets minimum quality threshold."""
        return self.score >= min_score and self.category != ResponseCategory.DEFLECTION

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "score": self.score,
            "category": self.category.value,
            "confidence": self.confidence,
            "missing_elements": self.missing_elements,
            "deflection_phrases_found": self.deflection_phrases_found,
            "recommendations": self.recommendations,
            "matched_elements": self.matched_elements,
            "response_length": self.response_length,
            "tool_results_analyzed": self.tool_results_analyzed,
            "timestamp": self.timestamp.isoformat(),
        }


class ResponseQualityAnalyzer:
    """
    Comprehensive AI response quality analyzer.

    This class analyzes AI-generated responses to ensure they provide
    genuine, helpful information rather than vague deflections or
    partial answers.

    Usage:
        analyzer = ResponseQualityAnalyzer()
        analysis = analyzer.analyze(query, response)
        if not analysis.is_acceptable(min_score=75):
            # Handle low-quality response
            logger.warning(f"Low quality: {analysis.recommendations}")
    """

    # Deflection phrases that indicate an unhelpful response
    # These are phrases that AI models commonly use when they can't find information
    DEFLECTION_PHRASES: list[str] = [
        "could not find",
        "couldn't find",
        "no information available",
        "please try a more specific",
        "i am not sure",
        "i'm not sure",
        "i do not have",
        "i don't have",
        "unable to retrieve",
        "no results found",
        "try again later",
        "could not extract specific details",
        "found some information but",
        "unable to locate",
        "no data available",
        "information is not available",
        "cannot provide specific",
        "don't have access to",
        "do not have access to",
        "outside my knowledge",
        "beyond my current knowledge",
        "i apologize, but i cannot",
        "unfortunately, i cannot",
        "i cannot find",
        "i can't find",
        "no specific information",
        "lacks specific details",
        "insufficient information",
        "couldn't retrieve",
        "failed to find",
        "failed to retrieve",
        "no matching results",
        "search returned no results",
        "unable to answer",
        "cannot answer this",
        "not able to provide",
        "please rephrase your question",
        "please be more specific",
        "try rephrasing",
        "query is too broad",
        "query is too vague",
    ]

    # Minimum response length for substantive queries (in characters)
    MIN_SUBSTANTIVE_LENGTH: int = 200

    # Content requirements by query type
    QUERY_TYPE_REQUIREMENTS: dict[str, list[ContentRequirement]] = {
        "call_search": [
            ContentRequirement(
                name="call_id",
                patterns=[r"horizon-[a-z0-9-]+", r"call\s*(id|identifier)", r"topic"],
                weight=1.5,
            ),
            ContentRequirement(
                name="deadline",
                patterns=[
                    r"deadline",
                    r"\d{1,2}\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
                    r"(january|february|march|april|may|june|july|august|september|october|november|december)\s*\d{4}",
                    r"\d{4}-\d{2}-\d{2}",
                ],
                weight=1.2,
            ),
            ContentRequirement(
                name="budget",
                patterns=[
                    r"budget",
                    r"eur\s*\d+",
                    r"\d+\s*million",
                    r"\d+m\s*eur",
                    r"funding",
                ],
                weight=1.0,
            ),
            ContentRequirement(
                name="action_type",
                patterns=[
                    r"\bria\b",
                    r"\bia\b",
                    r"\bcsa\b",
                    r"\bcofund\b",
                    r"\berc\b",
                    r"\bmsca\b",
                    r"research\s*(and|&)\s*innovation\s*action",
                    r"innovation\s*action",
                    r"type:\s*(ria|ia|csa)",
                    r"blended\s*finance",  # EIC specific
                ],
                weight=1.0,
            ),
            ContentRequirement(
                name="status",
                patterns=[r"(open|upcoming|closed|status)"],
                weight=1.0,
                required=False,
            ),
            ContentRequirement(
                name="programme",
                patterns=[r"(cluster|horizon|programme|program|pillar)"],
                weight=0.8,
                required=False,
            ),
        ],
        "project_search": [
            ContentRequirement(
                name="project_name",
                patterns=[r"project", r"acronym", r"title"],
                weight=1.2,
            ),
            ContentRequirement(
                name="funding",
                patterns=[r"funding", r"budget", r"eur", r"contribution", r"cost"],
                weight=1.0,
            ),
            ContentRequirement(
                name="coordinator",
                patterns=[r"coordinat", r"led by", r"partner"],
                weight=0.8,
                required=False,
            ),
            ContentRequirement(
                name="description",
                patterns=[r"objective", r"focus", r"aim", r"research", r"develop"],
                weight=1.0,
            ),
        ],
        "comparison": [
            ContentRequirement(
                name="comparison_elements",
                patterns=[
                    r"compar",
                    r"difference",
                    r"similar",
                    r"versus",
                    r"vs\.?",
                    r"while",
                    r"whereas",
                    r"in contrast",
                    r"on the other hand",
                ],
                weight=1.5,
            ),
            ContentRequirement(
                name="statistics",
                patterns=[
                    r"\d+%",
                    r"success rate",
                    r"average",
                    r"typically",
                    r"range",
                    r"\d+\s*million",
                ],
                weight=1.2,
            ),
            ContentRequirement(
                name="both_subjects",
                patterns=[r"(eic|erc|ria|ia|csa|msca|horizon)"],
                weight=1.0,
            ),
        ],
        "faq": [
            ContentRequirement(
                name="direct_answer",
                patterns=[
                    r"yes,?\s",
                    r"no,?\s",
                    r"can\s",
                    r"must\s",
                    r"should\s",
                    r"eligible",
                    r"require",
                ],
                weight=1.5,
            ),
            ContentRequirement(
                name="supporting_details",
                patterns=[r"because", r"since", r"therefore", r"for example", r"such as"],
                weight=1.0,
                required=False,
            ),
            ContentRequirement(
                name="source_reference",
                patterns=[r"(work programme|regulation|rule|article|section|according to)"],
                weight=0.8,
                required=False,
            ),
        ],
        "budget_benchmark": [
            ContentRequirement(
                name="budget_figures",
                patterns=[r"eur\s*\d+", r"\d+\s*million", r"\d+m", r"average\s*(budget|cost)"],
                weight=1.5,
            ),
            ContentRequirement(
                name="statistics",
                patterns=[r"average", r"median", r"range", r"typical", r"minimum", r"maximum"],
                weight=1.2,
            ),
            ContentRequirement(
                name="breakdown",
                patterns=[r"personnel", r"equipment", r"subcontract", r"travel", r"other\s*costs"],
                weight=1.0,
                required=False,
            ),
        ],
        "partner_discovery": [
            ContentRequirement(
                name="organization_names",
                patterns=[
                    r"(university|institut|center|centre|company|gmbh|ltd|inc|srl|sa\b)",
                    r"partner",
                    r"organization",
                ],
                weight=1.5,
            ),
            ContentRequirement(
                name="experience",
                patterns=[r"experience", r"project", r"participation", r"expertise"],
                weight=1.2,
            ),
            ContentRequirement(
                name="country",
                patterns=[r"(germany|france|spain|italy|netherlands|belgium|sweden|austria|finland|denmark|DE|FR|ES|IT|NL|BE|SE|AT|FI|DK)"],
                weight=1.0,
                required=False,
            ),
        ],
        "consortium_patterns": [
            ContentRequirement(
                name="consortium_size",
                patterns=[r"partner", r"consortium", r"average", r"typical"],
                weight=1.5,
            ),
            ContentRequirement(
                name="countries",
                patterns=[r"countr", r"nation", r"eu\s*member", r"associated"],
                weight=1.0,
            ),
            ContentRequirement(
                name="organization_types",
                patterns=[r"(hes|rec|prc|pub|university|research|sme|industry)"],
                weight=1.0,
                required=False,
            ),
        ],
        "general": [
            ContentRequirement(
                name="relevant_content",
                patterns=[r"horizon|europe|funding|research|project|call|grant"],
                weight=1.0,
            ),
        ],
    }

    def __init__(self) -> None:
        """Initialize the ResponseQualityAnalyzer."""
        self._deflection_patterns = [
            re.compile(phrase, re.IGNORECASE) for phrase in self.DEFLECTION_PHRASES
        ]
        logger.debug("ResponseQualityAnalyzer initialized with %d deflection patterns", len(self._deflection_patterns))

    def analyze(
        self,
        query: str,
        response: str,
        tool_results: dict[str, Any] | None = None,
        expected_elements: list[str] | None = None,
        query_type: str | None = None,
    ) -> QualityAnalysis:
        """
        Analyze the quality of an AI response.

        Args:
            query: The user's original query
            response: The AI-generated response text
            tool_results: Optional dict of tool execution results
            expected_elements: Optional list of expected content elements
            query_type: Optional query type for specific requirements

        Returns:
            QualityAnalysis with score, category, and recommendations
        """
        # Detect query type if not provided
        if query_type is None:
            query_type = self._detect_query_type(query)

        # Initialize analysis components
        deflection_phrases = self._detect_deflections(response)
        response_length = len(response)

        # Get requirements for this query type
        requirements = self.QUERY_TYPE_REQUIREMENTS.get(
            query_type, self.QUERY_TYPE_REQUIREMENTS["general"]
        )

        # Check content requirements
        matched_elements: list[str] = []
        missing_elements: list[str] = []

        for req in requirements:
            if req.matches(response):
                matched_elements.append(req.name)
            elif req.required:
                missing_elements.append(req.name)

        # Check custom expected elements if provided
        if expected_elements:
            for element in expected_elements:
                element_lower = element.lower()
                if element_lower in response.lower():
                    if element not in matched_elements:
                        matched_elements.append(element)
                elif element not in missing_elements:
                    missing_elements.append(element)

        # Calculate score and category
        score, category = self._calculate_score_and_category(
            response_length=response_length,
            deflection_phrases=deflection_phrases,
            matched_elements=matched_elements,
            missing_elements=missing_elements,
            requirements=requirements,
            tool_results=tool_results,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            category=category,
            deflection_phrases=deflection_phrases,
            missing_elements=missing_elements,
            response_length=response_length,
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            response_length=response_length,
            matched_count=len(matched_elements),
            total_requirements=len([r for r in requirements if r.required]),
        )

        return QualityAnalysis(
            score=score,
            category=category,
            confidence=confidence,
            missing_elements=missing_elements,
            deflection_phrases_found=deflection_phrases,
            recommendations=recommendations,
            matched_elements=matched_elements,
            response_length=response_length,
            tool_results_analyzed=len(tool_results) if tool_results else 0,
        )

    def _detect_deflections(self, response: str) -> list[str]:
        """Detect deflection phrases in the response."""
        found_phrases: list[str] = []
        response_lower = response.lower()

        for phrase in self.DEFLECTION_PHRASES:
            if phrase in response_lower:
                found_phrases.append(phrase)

        return found_phrases

    def _detect_query_type(self, query: str) -> str:
        """Detect the type of query based on its content."""
        query_lower = query.lower()

        # First check for specific call ID pattern (HORIZON-XXX)
        if re.search(r"horizon-[a-z0-9-]+", query_lower):
            return "call_search"

        # Comparison patterns (check early as they often contain other keywords)
        if any(p in query_lower for p in ["compare", " vs ", "versus", "difference between", "difference"]):
            return "comparison"

        # Call search patterns
        if any(p in query_lower for p in ["call", "funding", "opportunity", "deadline", " open "]):
            return "call_search"

        # Budget patterns (check before consortium to avoid confusion)
        if any(p in query_lower for p in ["budget", "cost", "benchmark", "typical cost"]):
            return "budget_benchmark"

        # FAQ patterns - check BEFORE consortium patterns to catch "what is the minimum..."
        # Questions asking about requirements/rules are FAQ, not pattern analysis
        if any(p in query_lower for p in ["can ", "eligible", "requirement", "how to", "what is", "what are"]):
            return "faq"

        # Consortium patterns (must contain analysis words, not just "consortium")
        if any(p in query_lower for p in ["consortium size", "consortium pattern", "typical consortium", "average consortium"]):
            return "consortium_patterns"

        # Partner patterns
        if any(p in query_lower for p in ["partner", "organization", "consortium member", "experienced"]):
            return "partner_discovery"

        # Project search patterns
        if any(p in query_lower for p in ["project", "funded", "cordis", "similar project"]):
            return "project_search"

        return "general"

    def _calculate_score_and_category(
        self,
        response_length: int,
        deflection_phrases: list[str],
        matched_elements: list[str],
        missing_elements: list[str],
        requirements: list[ContentRequirement],
        tool_results: dict[str, Any] | None,
    ) -> tuple[int, ResponseCategory]:
        """Calculate quality score and category."""
        # Start with base score
        base_score = 55  # Slightly higher base for substantive responses

        # Deflection check BEFORE empty check - short deflections are deflections, not empty
        if deflection_phrases:
            penalty = len(deflection_phrases) * 20  # Stronger penalty for deflections
            base_score -= min(penalty, 55)
            # Any deflection phrase in a short response = DEFLECTION
            if response_length < self.MIN_SUBSTANTIVE_LENGTH or len(deflection_phrases) >= 2:
                return max(0, base_score), ResponseCategory.DEFLECTION

        # Empty response (only if no deflection detected)
        if response_length < 50 and not deflection_phrases:
            return 0, ResponseCategory.EMPTY

        # Length score (up to +10)
        if response_length >= self.MIN_SUBSTANTIVE_LENGTH:
            length_bonus = min(10, (response_length - self.MIN_SUBSTANTIVE_LENGTH) // 100)
            base_score += length_bonus
        else:
            base_score -= 10

        # Content match score (up to +35)
        total_weight = sum(r.weight for r in requirements if r.required)
        matched_weight = sum(
            r.weight for r in requirements if r.name in matched_elements and r.required
        )

        if total_weight > 0:
            content_ratio = matched_weight / total_weight
            content_bonus = int(content_ratio * 35)  # Increased from 30
            base_score += content_bonus

        # Penalty for missing required elements (reduced penalty)
        required_missing = [
            e for e in missing_elements
            if any(r.name == e and r.required for r in requirements)
        ]
        if required_missing:
            missing_penalty = len(required_missing) * 6  # Reduced from 8
            base_score -= min(missing_penalty, 25)

        # Tool results bonus
        if tool_results:
            successful_tools = sum(
                1 for r in tool_results.values()
                if isinstance(r, dict) and r.get("success", False)
            )
            base_score += min(successful_tools * 5, 15)

        # Determine category
        final_score = max(0, min(100, base_score))

        if deflection_phrases:
            category = ResponseCategory.DEFLECTION
        elif final_score >= 70 and len(missing_elements) <= 1:
            category = ResponseCategory.COMPLETE
        elif final_score >= 40:
            category = ResponseCategory.PARTIAL
        else:
            category = ResponseCategory.DEFLECTION if deflection_phrases else ResponseCategory.PARTIAL

        return final_score, category

    def _generate_recommendations(
        self,
        category: ResponseCategory,
        deflection_phrases: list[str],
        missing_elements: list[str],
        response_length: int,
    ) -> list[str]:
        """Generate improvement recommendations."""
        recommendations: list[str] = []

        if deflection_phrases:
            recommendations.append(
                f"Response contains deflection phrases: {', '.join(deflection_phrases[:3])}. "
                "Ensure tools are returning actual data and the response synthesizes it properly."
            )

        if response_length < self.MIN_SUBSTANTIVE_LENGTH:
            recommendations.append(
                f"Response is too short ({response_length} chars). "
                f"Substantive responses should be at least {self.MIN_SUBSTANTIVE_LENGTH} characters."
            )

        if missing_elements:
            recommendations.append(
                f"Missing required elements: {', '.join(missing_elements[:5])}. "
                "Consider using additional tools or improving response synthesis."
            )

        if category == ResponseCategory.DEFLECTION:
            recommendations.append(
                "Response appears to be a deflection. Check if the underlying tools "
                "returned actual results and the AI properly synthesized the data."
            )

        if not recommendations:
            recommendations.append("Response meets quality standards.")

        return recommendations

    def _calculate_confidence(
        self,
        response_length: int,
        matched_count: int,
        total_requirements: int,
    ) -> float:
        """Calculate confidence in the quality analysis."""
        # Base confidence from response length
        if response_length < 50:
            return 0.9  # High confidence it's empty

        if response_length < self.MIN_SUBSTANTIVE_LENGTH:
            base_confidence = 0.7
        else:
            base_confidence = 0.85

        # Adjust based on matched requirements
        if total_requirements > 0:
            match_ratio = matched_count / total_requirements
            confidence = base_confidence * (0.7 + 0.3 * match_ratio)
        else:
            confidence = base_confidence

        return min(1.0, max(0.0, confidence))

    def validate_tool_response(
        self,
        tool_name: str,
        tool_result: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """
        Validate that a tool response contains actual data.

        Args:
            tool_name: Name of the tool that was executed
            tool_result: The result returned by the tool

        Returns:
            Tuple of (is_valid, list of issues found)
        """
        issues: list[str] = []

        if not isinstance(tool_result, dict):
            return False, ["Tool result is not a dictionary"]

        # Check for error indicators
        if tool_result.get("error"):
            issues.append(f"Tool returned error: {tool_result.get('error')}")
            return False, issues

        if not tool_result.get("success", True):
            issues.append("Tool execution was not successful")

        # Check for empty results based on tool type
        if tool_name == "search_funding_calls":
            calls_found = tool_result.get("calls_found", 0)
            if calls_found == 0:
                issues.append("No funding calls found")
            elif not tool_result.get("calls"):
                issues.append("calls_found > 0 but no calls array")

        elif tool_name == "search_projects":
            projects_count = tool_result.get("projects_count", 0)
            if projects_count == 0:
                issues.append("No projects found")
            elif not tool_result.get("projects"):
                issues.append("projects_count > 0 but no projects array")

        elif tool_name == "find_experienced_partners":
            partners = tool_result.get("partners", [])
            if not partners:
                issues.append("No partners found")

        elif tool_name == "get_budget_benchmark":
            if not tool_result.get("statistics"):
                issues.append("No budget statistics returned")

        elif tool_name == "get_programme_statistics":
            if not tool_result.get("statistics"):
                issues.append("No programme statistics returned")

        return len(issues) == 0, issues

    def analyze_with_tools(
        self,
        query: str,
        response: str,
        tool_results: dict[str, dict[str, Any]],
        expected_tools: list[str] | None = None,
    ) -> QualityAnalysis:
        """
        Analyze response quality including tool execution validation.

        Args:
            query: The user's original query
            response: The AI-generated response text
            tool_results: Dict mapping tool names to their results
            expected_tools: Optional list of tools that should have been called

        Returns:
            QualityAnalysis with comprehensive validation
        """
        # First do standard response analysis
        analysis = self.analyze(query, response, tool_results)

        # Check for expected tools
        if expected_tools:
            missing_tools = [t for t in expected_tools if t not in tool_results]
            if missing_tools:
                analysis.missing_elements.extend([f"tool:{t}" for t in missing_tools])
                analysis.recommendations.append(
                    f"Expected tools not called: {', '.join(missing_tools)}"
                )

        # Validate each tool result
        tool_issues: list[str] = []
        for tool_name, result in tool_results.items():
            is_valid, issues = self.validate_tool_response(tool_name, result)
            if not is_valid:
                tool_issues.extend([f"{tool_name}: {issue}" for issue in issues])

        if tool_issues:
            analysis.recommendations.append(
                f"Tool result issues: {'; '.join(tool_issues[:3])}"
            )
            # Reduce score for tool issues
            analysis.score = max(0, analysis.score - len(tool_issues) * 5)

        return analysis
