"""Response Quality Analyzer for AI response validation.

This module provides comprehensive analysis of AI responses to detect:
- Deflection patterns (e.g., "I could not find", "no information available")
- Incomplete responses that fail to address the user's query
- Missing required content elements for specific query types
- Low-quality responses that should trigger test failures

The analyzer is designed to ensure AI responses are substantive and actionable,
not vague deflections that provide no value to users.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ResponseCategory(str, Enum):
    """Categories for classifying AI response quality."""

    COMPLETE = "complete"  # Response fully addresses query with substantive content
    PARTIAL = "partial"  # Response partially addresses query, missing some elements
    DEFLECTION = "deflection"  # Response avoids answering, uses deflection phrases
    EMPTY = "empty"  # Response is essentially empty or too short
    ERROR = "error"  # Response indicates an error occurred


class QueryType(str, Enum):
    """Types of queries for determining expected content requirements."""

    CALL_SEARCH = "call_search"  # Searching for funding calls
    CALL_DETAILS = "call_details"  # Details about a specific call
    PROJECT_SEARCH = "project_search"  # Searching for funded projects
    PROGRAMME_COMPARISON = "programme_comparison"  # Comparing programmes
    ELIGIBILITY_FAQ = "eligibility_faq"  # Eligibility questions
    BUDGET_BENCHMARK = "budget_benchmark"  # Budget-related queries
    PARTNER_DISCOVERY = "partner_discovery"  # Finding partners
    CONSORTIUM_PATTERNS = "consortium_patterns"  # Consortium analysis
    GENERAL_FAQ = "general_faq"  # General questions


@dataclass
class QualityAnalysis:
    """Result of analyzing an AI response's quality.

    Attributes:
        score: Quality score from 0-100
        category: Classification of the response type
        confidence: Confidence in the analysis (0.0-1.0)
        missing_elements: List of expected elements that are missing
        deflection_phrases_found: List of deflection phrases detected
        recommendations: Suggestions for improving the response
        query_type: Detected type of the query
        analyzed_at: Timestamp of the analysis
    """

    score: int
    category: ResponseCategory
    confidence: float
    missing_elements: list[str] = field(default_factory=list)
    deflection_phrases_found: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    query_type: QueryType | None = None
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_acceptable(self, min_score: int = 70) -> bool:
        """Check if the response quality meets the minimum threshold.

        Args:
            min_score: Minimum acceptable quality score (default 70)

        Returns:
            True if quality is acceptable, False otherwise
        """
        return (
            self.score >= min_score
            and self.category != ResponseCategory.DEFLECTION
            and self.category != ResponseCategory.EMPTY
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert analysis to dictionary for serialization."""
        return {
            "score": self.score,
            "category": self.category.value,
            "confidence": self.confidence,
            "missing_elements": self.missing_elements,
            "deflection_phrases_found": self.deflection_phrases_found,
            "recommendations": self.recommendations,
            "query_type": self.query_type.value if self.query_type else None,
            "analyzed_at": self.analyzed_at.isoformat(),
            "is_acceptable": self.is_acceptable(),
        }


class ResponseQualityAnalyzer:
    """Analyzer for detecting low-quality AI responses.

    This class identifies deflection patterns, missing content, and
    insufficient responses to ensure AI outputs meet quality standards.

    The analyzer enforces strict quality requirements:
    - Responses must be substantive (not vague deflections)
    - Required elements must be present based on query type
    - Minimum length requirements for substantive queries
    - Confidence scoring to identify borderline cases
    """

    # Deflection phrases that indicate the AI is avoiding answering
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
        "i cannot provide",
        "i can't provide",
        "unfortunately, i",
        "i apologize, but",
        "i wasn't able to",
        "i was not able to",
        "no specific information",
        "information is not available",
        "data is not available",
        "cannot access",
        "can't access",
        "unable to access",
        "information unavailable",
        "data unavailable",
        "no matching results",
        "no data found",
        "search returned no results",
        "did not find any",
        "didn't find any",
        "unable to locate",
        "could not locate",
        "couldn't locate",
    ]

    # Minimum response lengths by query type (characters)
    MIN_RESPONSE_LENGTHS: dict[QueryType, int] = {
        QueryType.CALL_DETAILS: 300,
        QueryType.CALL_SEARCH: 200,
        QueryType.PROJECT_SEARCH: 200,
        QueryType.PROGRAMME_COMPARISON: 400,
        QueryType.ELIGIBILITY_FAQ: 150,
        QueryType.BUDGET_BENCHMARK: 250,
        QueryType.PARTNER_DISCOVERY: 200,
        QueryType.CONSORTIUM_PATTERNS: 250,
        QueryType.GENERAL_FAQ: 100,
    }

    # Required content patterns by query type
    REQUIRED_PATTERNS: dict[QueryType, list[tuple[str, str]]] = {
        QueryType.CALL_DETAILS: [
            (r"HORIZON-[A-Z0-9-]+|horizon-[a-z0-9-]+", "call_identifier"),
            (r"deadline|due date|closes?|submission", "deadline"),
            (r"€|EUR|euro|million|budget", "budget"),
            (r"RIA|IA|CSA|COFUND|ERC|MSCA", "action_type"),
        ],
        QueryType.CALL_SEARCH: [
            (r"found|opportunities?|calls?|topics?", "results_indication"),
            (r"HORIZON-[A-Z0-9-]+|horizon-[a-z0-9-]+", "call_identifier"),
        ],
        QueryType.PROJECT_SEARCH: [
            (r"projects?|funded|research", "project_indication"),
            (r"partner|organization|participant", "organization"),
        ],
        QueryType.PROGRAMME_COMPARISON: [
            (r"comparison|compare|vs\.?|versus|differ", "comparison_language"),
            (r"success rate|funding|budget|rate", "metric"),
        ],
        QueryType.BUDGET_BENCHMARK: [
            (r"€|EUR|euro|million|budget|cost", "budget_figure"),
            (r"average|median|typical|range", "statistical_term"),
        ],
        QueryType.PARTNER_DISCOVERY: [
            (r"partner|organization|institution|company", "organization"),
            (r"experience|expertise|track record", "experience"),
        ],
        QueryType.CONSORTIUM_PATTERNS: [
            (r"consortium|partner|participant", "consortium_term"),
            (r"average|typical|pattern|size", "pattern_term"),
        ],
    }

    def __init__(self) -> None:
        """Initialize the ResponseQualityAnalyzer."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        self._deflection_patterns = [
            re.compile(re.escape(phrase), re.IGNORECASE)
            for phrase in self.DEFLECTION_PHRASES
        ]
        self._required_patterns_compiled: dict[
            QueryType, list[tuple[re.Pattern[str], str]]
        ] = {}
        for query_type, patterns in self.REQUIRED_PATTERNS.items():
            self._required_patterns_compiled[query_type] = [
                (re.compile(pattern, re.IGNORECASE), name)
                for pattern, name in patterns
            ]

    def analyze(
        self,
        query: str,
        response: str,
        query_type: QueryType | None = None,
        expected_elements: list[str] | None = None,
    ) -> QualityAnalysis:
        """Analyze an AI response for quality issues.

        Args:
            query: The original user query
            response: The AI's response text
            query_type: Optional explicit query type (auto-detected if not provided)
            expected_elements: Optional list of expected content elements

        Returns:
            QualityAnalysis with detailed quality assessment
        """
        if not response or not response.strip():
            logger.warning(f"Empty response for query: {query[:50]}...")
            return QualityAnalysis(
                score=0,
                category=ResponseCategory.EMPTY,
                confidence=1.0,
                missing_elements=["any_content"],
                recommendations=["Response should not be empty"],
            )

        response_lower = response.lower()

        # Detect query type if not provided
        detected_query_type = query_type or self._detect_query_type(query)

        # Check for deflection phrases
        deflections = self._detect_deflections(response_lower)

        # Check response length
        min_length = self.MIN_RESPONSE_LENGTHS.get(
            detected_query_type, 100
        ) if detected_query_type else 100
        is_too_short = len(response.strip()) < min_length

        # Check for required content patterns
        missing_elements = self._check_required_patterns(
            response, detected_query_type, expected_elements
        )

        # Check for explicit expected elements
        if expected_elements:
            for element in expected_elements:
                if element.lower() not in response_lower:
                    if element not in missing_elements:
                        missing_elements.append(element)

        # Calculate score and category
        score, category, confidence = self._calculate_score(
            response=response,
            deflections=deflections,
            is_too_short=is_too_short,
            missing_elements=missing_elements,
            query_type=detected_query_type,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            deflections=deflections,
            is_too_short=is_too_short,
            missing_elements=missing_elements,
            category=category,
        )

        return QualityAnalysis(
            score=score,
            category=category,
            confidence=confidence,
            missing_elements=missing_elements,
            deflection_phrases_found=deflections,
            recommendations=recommendations,
            query_type=detected_query_type,
        )

    def _detect_query_type(self, query: str) -> QueryType | None:
        """Detect the type of query based on content.

        Args:
            query: The user's query text

        Returns:
            Detected QueryType or None if unclear
        """
        query_lower = query.lower()

        # Call-specific queries (explicit call ID)
        if re.search(r"horizon-[a-z0-9-]+", query_lower):
            if any(word in query_lower for word in ["about", "tell", "details", "what is"]):
                return QueryType.CALL_DETAILS

        # Call search patterns
        if any(phrase in query_lower for phrase in [
            "find call", "search call", "funding call", "open call",
            "upcoming call", "call for", "funding opportunit"
        ]):
            return QueryType.CALL_SEARCH

        # Project search patterns
        if any(phrase in query_lower for phrase in [
            "find project", "search project", "funded project",
            "cordis", "similar project"
        ]):
            return QueryType.PROJECT_SEARCH

        # Comparison patterns
        if any(phrase in query_lower for phrase in [
            "compare", "versus", " vs ", "difference between",
            "better", "comparison"
        ]):
            return QueryType.PROGRAMME_COMPARISON

        # Budget patterns
        if any(phrase in query_lower for phrase in [
            "budget", "cost", "funding amount", "how much",
            "typical budget", "benchmark"
        ]):
            return QueryType.BUDGET_BENCHMARK

        # Partner discovery patterns
        if any(phrase in query_lower for phrase in [
            "find partner", "partner with", "organization",
            "experienced", "track record", "expertise in",
            "with experience", "experience in", "find sme",
            "find institution", "find research", "find compan"
        ]):
            return QueryType.PARTNER_DISCOVERY

        # Consortium patterns
        if any(phrase in query_lower for phrase in [
            "consortium", "typical partner", "how many partner",
            "consortium size", "partner composition"
        ]):
            return QueryType.CONSORTIUM_PATTERNS

        # Eligibility FAQ patterns
        if any(phrase in query_lower for phrase in [
            "eligible", "can i", "can we", "eligibility",
            "qualify", "requirement", "sme", "apply"
        ]):
            return QueryType.ELIGIBILITY_FAQ

        return QueryType.GENERAL_FAQ

    def _detect_deflections(self, response_lower: str) -> list[str]:
        """Detect deflection phrases in the response.

        Args:
            response_lower: Lowercase response text

        Returns:
            List of deflection phrases found
        """
        found = []
        for pattern, phrase in zip(
            self._deflection_patterns, self.DEFLECTION_PHRASES, strict=True
        ):
            if pattern.search(response_lower):
                found.append(phrase)
        return found

    def _check_required_patterns(
        self,
        response: str,
        query_type: QueryType | None,
        expected_elements: list[str] | None,
    ) -> list[str]:
        """Check for required content patterns based on query type.

        Args:
            response: The response text
            query_type: Type of query being checked
            expected_elements: Explicitly expected elements

        Returns:
            List of missing required elements
        """
        missing = []

        if query_type and query_type in self._required_patterns_compiled:
            for pattern, element_name in self._required_patterns_compiled[query_type]:
                if not pattern.search(response):
                    missing.append(element_name)

        return missing

    def _calculate_score(
        self,
        response: str,
        deflections: list[str],
        is_too_short: bool,
        missing_elements: list[str],
        query_type: QueryType | None,
    ) -> tuple[int, ResponseCategory, float]:
        """Calculate quality score, category, and confidence.

        Args:
            response: The response text
            deflections: List of deflection phrases found
            is_too_short: Whether response is below minimum length
            missing_elements: List of missing required elements
            query_type: Type of query

        Returns:
            Tuple of (score, category, confidence)
        """
        # Start with base score of 100
        score = 100
        confidence = 1.0

        # Major penalty for deflections
        if deflections:
            # Multiple deflections indicate strong deflection
            deflection_penalty = min(len(deflections) * 25, 70)
            score -= deflection_penalty

            # If more than 2 deflection phrases, it's definitely a deflection
            if len(deflections) >= 2:
                return (
                    max(score, 5),
                    ResponseCategory.DEFLECTION,
                    0.95,
                )

        # Penalty for being too short
        if is_too_short:
            score -= 20

        # Penalty for missing required elements
        if missing_elements:
            # Each missing element costs points
            element_penalty = len(missing_elements) * 10
            score -= min(element_penalty, 40)

        # Determine category
        if score <= 20:
            if deflections:
                category = ResponseCategory.DEFLECTION
            else:
                category = ResponseCategory.EMPTY
            confidence = 0.9
        elif score <= 50:
            category = ResponseCategory.PARTIAL
            confidence = 0.8
        elif score <= 75:
            category = ResponseCategory.PARTIAL
            confidence = 0.85
        else:
            category = ResponseCategory.COMPLETE
            confidence = 0.9

        # Adjust confidence based on response length relative to expected
        if query_type:
            min_len = self.MIN_RESPONSE_LENGTHS.get(query_type, 100)
            actual_len = len(response.strip())
            if actual_len >= min_len * 2:
                confidence = min(confidence + 0.05, 1.0)
            elif actual_len < min_len:
                confidence = max(confidence - 0.1, 0.5)

        return (max(score, 0), category, confidence)

    def _generate_recommendations(
        self,
        deflections: list[str],
        is_too_short: bool,
        missing_elements: list[str],
        category: ResponseCategory,
    ) -> list[str]:
        """Generate recommendations for improving response quality.

        Args:
            deflections: List of deflection phrases found
            is_too_short: Whether response is too short
            missing_elements: List of missing elements
            category: Determined response category

        Returns:
            List of improvement recommendations
        """
        recommendations = []

        if deflections:
            recommendations.append(
                f"Response contains deflection phrases: {', '.join(deflections[:3])}. "
                "Provide specific information instead of deflecting."
            )

        if is_too_short:
            recommendations.append(
                "Response is too short. Provide more detailed information."
            )

        if missing_elements:
            recommendations.append(
                f"Response is missing expected elements: {', '.join(missing_elements)}. "
                "Include these to fully address the query."
            )

        if category == ResponseCategory.DEFLECTION:
            recommendations.append(
                "Response appears to deflect rather than answer. "
                "Use available tools to find relevant information."
            )

        if category == ResponseCategory.EMPTY:
            recommendations.append(
                "Response is empty or contains no useful content."
            )

        return recommendations

    def validate_tool_result(
        self,
        tool_name: str,
        tool_result: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate that a tool result contains expected data.

        Args:
            tool_name: Name of the tool that produced the result
            tool_result: The tool's result dictionary

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check for error in result
        if "error" in tool_result:
            issues.append(f"Tool returned error: {tool_result['error']}")
            return (False, issues)

        # Check for empty results
        if not tool_result:
            issues.append("Tool returned empty result")
            return (False, issues)

        # Tool-specific validations
        if tool_name == "search_funding_calls":
            if "calls" in tool_result and len(tool_result.get("calls", [])) == 0:
                issues.append("Call search returned no results")
            if "calls_found" in tool_result and tool_result.get("calls_found", 0) == 0:
                issues.append("Call search found zero calls")

        elif tool_name == "search_projects":
            if "projects" in tool_result and len(tool_result.get("projects", [])) == 0:
                issues.append("Project search returned no results")

        elif tool_name == "get_budget_benchmark":
            if "statistics" not in tool_result:
                issues.append("Budget benchmark missing statistics")
            if "metadata" not in tool_result:
                issues.append("Budget benchmark missing metadata")

        elif tool_name == "find_experienced_partners":
            partners = tool_result.get("experienced_partners", [])
            if not partners:
                issues.append("Partner discovery found no partners")

        elif tool_name == "get_consortium_patterns":
            if "consortium_size" not in tool_result:
                issues.append("Consortium patterns missing size data")

        elif tool_name in ["get_programme_statistics", "compare_programmes"]:
            if "success" in tool_result and not tool_result.get("success"):
                issues.append("Statistics tool returned unsuccessful result")

        # Check for expected metadata in hybrid tools
        if tool_name in [
            "get_budget_benchmark",
            "find_experienced_partners",
            "get_consortium_patterns",
            "analyze_call_history",
        ]:
            metadata = tool_result.get("metadata", {})
            if not metadata.get("sources_used"):
                issues.append("Hybrid tool missing sources_used metadata")

        is_valid = len(issues) == 0
        return (is_valid, issues)

    def analyze_with_tools(
        self,
        query: str,
        response: str,
        tools_used: list[str],
        tool_results: dict[str, Any],
        expected_elements: list[str] | None = None,
    ) -> QualityAnalysis:
        """Analyze response quality including tool execution validation.

        Args:
            query: The original user query
            response: The AI's response text
            tools_used: List of tools that were called
            tool_results: Dictionary mapping tool names to their results
            expected_elements: Optional expected content elements

        Returns:
            QualityAnalysis with comprehensive quality assessment
        """
        # First, do standard response analysis
        analysis = self.analyze(query, response, expected_elements=expected_elements)

        # Then validate tool results
        tool_issues = []
        for tool_name in tools_used:
            if tool_name in tool_results:
                is_valid, issues = self.validate_tool_result(
                    tool_name, tool_results[tool_name]
                )
                if not is_valid:
                    tool_issues.extend(issues)

        # Adjust score and recommendations based on tool validation
        if tool_issues:
            # Each tool issue reduces score
            penalty = len(tool_issues) * 10
            analysis.score = max(analysis.score - penalty, 0)
            analysis.missing_elements.extend(tool_issues)
            analysis.recommendations.append(
                f"Tool validation issues: {'; '.join(tool_issues)}"
            )

            # If too many tool issues, downgrade category
            if len(tool_issues) >= 2 and analysis.category == ResponseCategory.COMPLETE:
                analysis.category = ResponseCategory.PARTIAL

        return analysis


# Singleton instance for convenience
_analyzer_instance: ResponseQualityAnalyzer | None = None


def get_analyzer() -> ResponseQualityAnalyzer:
    """Get the shared ResponseQualityAnalyzer instance.

    Returns:
        The singleton ResponseQualityAnalyzer instance
    """
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ResponseQualityAnalyzer()
    return _analyzer_instance
