"""
AI Response Quality Analyzer

Analyzes AI responses for quality, completeness, and deflection patterns.
This is a critical component for ensuring MAP-IT provides actionable,
helpful responses rather than deflections or vague answers.

Key Features:
- Deflection phrase detection (phrases that indicate AI couldn't find info)
- Content completeness checking (verifies required elements are present)
- Quality scoring (0-100 scale)
- Categorization (complete, partial, deflection, empty, error)
- Recommendations for improvement
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ResponseCategory(str, Enum):
    """Categories for AI response quality."""

    COMPLETE = "complete"  # Response has all required elements
    PARTIAL = "partial"  # Response has some but not all required elements
    DEFLECTION = "deflection"  # Response deflects/avoids answering
    EMPTY = "empty"  # Response is essentially empty
    ERROR = "error"  # Response indicates an error occurred


@dataclass
class QualityAnalysis:
    """Result of quality analysis on an AI response.

    Attributes:
        score: Quality score from 0-100
        category: Classification of the response
        confidence: Confidence in the analysis (0.0-1.0)
        missing_elements: Required elements that are missing
        deflection_phrases_found: Deflection phrases detected in response
        recommendations: Suggestions for improving response quality
        metadata: Additional analysis data
    """

    score: int
    category: ResponseCategory
    confidence: float
    missing_elements: list[str] = field(default_factory=list)
    deflection_phrases_found: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_acceptable(self, min_score: int = 70) -> bool:
        """Check if the response meets minimum quality standards.

        Args:
            min_score: Minimum acceptable score (default 70)

        Returns:
            True if score meets minimum and no deflection detected
        """
        return self.score >= min_score and self.category != ResponseCategory.DEFLECTION


class ResponseQualityAnalyzer:
    """Analyzes AI responses for quality, completeness, and deflection patterns.

    This analyzer is used to ensure AI responses are actionable and helpful,
    not vague deflections. It's particularly important for EU funding queries
    where users need specific, accurate information.

    Example:
        >>> analyzer = ResponseQualityAnalyzer()
        >>> analysis = analyzer.analyze(
        ...     query="Tell me about HORIZON-CL5-2026-D3-01",
        ...     response="I found information about this call...",
        ...     expected_elements=["deadline", "budget", "type"]
        ... )
        >>> if not analysis.is_acceptable():
        ...     print(f"Poor quality: {analysis.recommendations}")
    """

    # Phrases that indicate the AI couldn't find or provide specific information
    DEFLECTION_PHRASES = [
        "could not find",
        "no information available",
        "please try a more specific",
        "I am not sure",
        "I do not have",
        "unable to retrieve",
        "no results found",
        "try again later",
        "could not extract specific details",
        "found some information but",
        "I don't have access to",
        "I cannot access",
        "I'm not able to",
        "information is not available",
        "data is not available",
        "unable to find",
        "couldn't locate",
        "no specific information",
        "general information only",
        "limited information",
        "insufficient data",
        "cannot determine",
        "unclear from the available",
        "not enough information",
        "beyond my current knowledge",
        "outside my knowledge",
        "I apologize, but I",
        "Unfortunately, I cannot",
        "I'm sorry, but I cannot",
        "regrettably, I don't",
    ]

    # Patterns that indicate a non-answer or evasion
    EVASION_PATTERNS = [
        r"(?i)you\s+(should|could|might)\s+(try|check|look)",
        r"(?i)I\s+recommend\s+checking\s+(the|official|external)",
        r"(?i)please\s+refer\s+to\s+(the|official)",
        r"(?i)for\s+more\s+(details|information),\s+(visit|check|see)",
        r"(?i)I\s+suggest\s+contacting",
    ]

    # Required elements for specific query types
    QUERY_TYPE_REQUIREMENTS = {
        "call_info": {
            "required": ["deadline", "type", "status"],
            "optional": ["budget", "scope", "apply_link"],
            "min_length": 200,
        },
        "project_info": {
            "required": ["title", "objective", "participants"],
            "optional": ["budget", "duration", "status"],
            "min_length": 150,
        },
        "programme_comparison": {
            "required": ["programme_a_info", "programme_b_info", "comparison"],
            "optional": ["success_rates", "funding_amounts"],
            "min_length": 300,
        },
        "budget_benchmark": {
            "required": ["budget_range", "source_count"],
            "optional": ["org_type_breakdown", "country_breakdown"],
            "min_length": 150,
        },
        "partner_discovery": {
            "required": ["partners_found", "experience_info"],
            "optional": ["country", "project_examples"],
            "min_length": 150,
        },
        "general_faq": {
            "required": ["answer"],
            "optional": ["sources", "examples"],
            "min_length": 100,
        },
    }

    # Element detection patterns for various content types
    ELEMENT_PATTERNS = {
        "deadline": [
            r"\b\d{1,2}[-/\s]\w{3,9}[-/\s]\d{4}\b",  # 15 March 2025
            r"\b\w{3,9}\s+\d{1,2},?\s+\d{4}\b",  # March 15, 2025
            r"\b\d{4}[-/]\d{2}[-/]\d{2}\b",  # 2025-03-15
            r"(?i)deadline[:\s]+",
        ],
        "budget": [
            r"(?i)€\s*[\d,\.]+\s*(million|M|k|thousand)?",
            r"(?i)EUR\s*[\d,\.]+\s*(million|M)?",
            r"(?i)budget[:\s]+",
            r"(?i)\d+[\.,]?\d*\s*(million|M)\s*(euro|EUR)?",
        ],
        "type": [
            r"(?i)\bRIA\b",
            r"(?i)\bIA\b",
            r"(?i)\bCSA\b",
            r"(?i)\bCOFUND\b",
            r"(?i)\bERC\b",
            r"(?i)\bMSCA\b",
            r"(?i)Research\s+and\s+Innovation\s+Action",
            r"(?i)Innovation\s+Action",
            r"(?i)Coordination\s+and\s+Support",
        ],
        "status": [
            r"(?i)\bopen\b",
            r"(?i)\bupcoming\b",
            r"(?i)\bclosed\b",
            r"(?i)\bactive\b",
        ],
        "apply_link": [
            r"https?://[^\s]+funding-tenders[^\s]*",
            r"(?i)apply[:\s]+https?://",
        ],
        "title": [r"(?i)title[:\s]+", r"(?i)project[:\s]+.{10,}"],
        "objective": [r"(?i)objective[:\s]+", r"(?i)aims?\s+to", r"(?i)goal[:\s]+"],
        "participants": [
            r"(?i)partner[s]?[:\s]+",
            r"(?i)consortium",
            r"(?i)participant[s]?[:\s]+",
        ],
        "comparison": [
            r"(?i)compar(e|ed|ing|ison)",
            r"(?i)versus|vs\.?",
            r"(?i)differ(ence|ent|s)",
            r"(?i)similar(ity|ities)?",
        ],
        "programme_a_info": [
            r"(?i)EIC",
            r"(?i)ERC",
            r"(?i)MSCA",
            r"(?i)RIA",
            r"(?i)Horizon",
        ],
        "programme_b_info": [
            r"(?i)EIC",
            r"(?i)ERC",
            r"(?i)MSCA",
            r"(?i)RIA",
            r"(?i)Horizon",
        ],
        "budget_range": [
            r"(?i)€\s*[\d,\.]+",
            r"(?i)EUR\s*[\d,\.]+",
            r"(?i)between.*and",
            r"(?i)average.*budget",
        ],
        "source_count": [r"(?i)\d+\s*project[s]?", r"(?i)analyzed", r"(?i)based\s+on"],
        "partners_found": [
            r"(?i)\d+\s*(partner|organization|institution)",
            r"(?i)found.*partner",
        ],
        "experience_info": [
            r"(?i)experience",
            r"(?i)track\s+record",
            r"(?i)participated",
        ],
        "success_rates": [r"(?i)success\s+rate", r"(?i)\d+(\.\d+)?%"],
        "funding_amounts": [
            r"(?i)€\s*[\d,\.]+",
            r"(?i)funding",
            r"(?i)contribution",
        ],
        "answer": [r".{50,}"],  # At least 50 chars of content
    }

    def __init__(self) -> None:
        """Initialize the response quality analyzer."""
        self._compiled_deflection_patterns: list[re.Pattern[str]] = []
        self._compiled_evasion_patterns: list[re.Pattern[str]] = []
        self._compile_patterns()
        logger.debug("ResponseQualityAnalyzer initialized")

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for better performance."""
        for phrase in self.DEFLECTION_PHRASES:
            try:
                # Escape and make case-insensitive
                pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                self._compiled_deflection_patterns.append(pattern)
            except re.error as e:
                logger.warning(f"Failed to compile deflection pattern '{phrase}': {e}")

        for evasion_pattern in self.EVASION_PATTERNS:
            try:
                compiled = re.compile(evasion_pattern, re.IGNORECASE)
                self._compiled_evasion_patterns.append(compiled)
            except re.error as e:
                logger.warning(f"Failed to compile evasion pattern '{evasion_pattern}': {e}")

    def analyze(
        self,
        query: str,
        response: str,
        query_type: str = "general_faq",
        expected_elements: list[str] | None = None,
        tool_results: dict[str, Any] | None = None,
    ) -> QualityAnalysis:
        """Analyze the quality of an AI response.

        Args:
            query: The original user query
            response: The AI's response text
            query_type: Type of query (call_info, project_info, etc.)
            expected_elements: Optional list of elements expected in response
            tool_results: Optional dict of tool results to check

        Returns:
            QualityAnalysis with score, category, and recommendations
        """
        if not response or not response.strip():
            return QualityAnalysis(
                score=0,
                category=ResponseCategory.EMPTY,
                confidence=1.0,
                recommendations=["Response is empty"],
            )

        # Check for error responses
        if self._is_error_response(response):
            return QualityAnalysis(
                score=0,
                category=ResponseCategory.ERROR,
                confidence=0.95,
                recommendations=["Response indicates an error occurred"],
            )

        # Detect deflection phrases
        deflection_phrases = self._detect_deflection_phrases(response)

        # Detect evasion patterns
        evasion_matches = self._detect_evasion_patterns(response)
        deflection_phrases.extend(evasion_matches)

        # Check required elements
        requirements = self.QUERY_TYPE_REQUIREMENTS.get(
            query_type, self.QUERY_TYPE_REQUIREMENTS["general_faq"]
        )
        if expected_elements:
            elements_to_check = expected_elements
        else:
            required_elements = requirements.get("required")
            elements_to_check = (
                list(required_elements)
                if isinstance(required_elements, list)
                else ["answer"]
            )

        missing_elements = self._check_elements(response, elements_to_check)

        # Check minimum length
        min_length_value = requirements.get("min_length", 100)
        if isinstance(min_length_value, int):
            min_length = min_length_value
        else:
            min_length = 100
        is_too_short = len(response.strip()) < min_length

        # Check tool results if provided
        tool_issues = self._check_tool_results(tool_results) if tool_results else []

        # Calculate score
        score, category = self._calculate_score(
            response=response,
            deflection_phrases=deflection_phrases,
            missing_elements=missing_elements,
            is_too_short=is_too_short,
            tool_issues=tool_issues,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            deflection_phrases=deflection_phrases,
            missing_elements=missing_elements,
            is_too_short=is_too_short,
            min_length=min_length,
            tool_issues=tool_issues,
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            response_length=len(response),
            num_deflections=len(deflection_phrases),
            num_missing=len(missing_elements),
        )

        analysis = QualityAnalysis(
            score=score,
            category=category,
            confidence=confidence,
            missing_elements=missing_elements,
            deflection_phrases_found=deflection_phrases,
            recommendations=recommendations,
            metadata={
                "query_type": query_type,
                "response_length": len(response),
                "analyzed_at": datetime.now(UTC).isoformat(),
                "min_length_required": min_length,
                "is_too_short": is_too_short,
                "tool_issues": tool_issues,
            },
        )

        logger.debug(
            f"Quality analysis: score={score}, category={category.value}, "
            f"deflections={len(deflection_phrases)}, missing={len(missing_elements)}"
        )

        return analysis

    def _detect_deflection_phrases(self, response: str) -> list[str]:
        """Detect deflection phrases in the response.

        Args:
            response: The AI response text

        Returns:
            List of deflection phrases found
        """
        found_phrases = []
        response_lower = response.lower()

        for i, pattern in enumerate(self._compiled_deflection_patterns):
            if pattern.search(response_lower):
                found_phrases.append(self.DEFLECTION_PHRASES[i])

        return found_phrases

    def _detect_evasion_patterns(self, response: str) -> list[str]:
        """Detect evasion patterns in the response.

        Args:
            response: The AI response text

        Returns:
            List of evasion pattern matches found
        """
        found_patterns = []

        for pattern in self._compiled_evasion_patterns:
            match = pattern.search(response)
            if match:
                found_patterns.append(match.group(0))

        return found_patterns

    def _is_error_response(self, response: str) -> bool:
        """Check if the response indicates an error.

        Args:
            response: The AI response text

        Returns:
            True if response appears to be an error message
        """
        error_indicators = [
            "error occurred",
            "service unavailable",
            "internal error",
            "request failed",
            "timeout error",
            "timed out",
            "exception occurred",
            "an exception",
            "raised exception",
            "unhandled exception",
            "500 internal",
            "503 service",
            "rate limit exceeded",
            "connection refused",
            "connection error",
        ]

        response_lower = response.lower()
        return any(indicator in response_lower for indicator in error_indicators)

    def _check_elements(self, response: str, expected_elements: list[str]) -> list[str]:
        """Check which expected elements are missing from the response.

        Args:
            response: The AI response text
            expected_elements: List of elements to check for

        Returns:
            List of missing elements
        """
        missing = []

        for element in expected_elements:
            patterns = self.ELEMENT_PATTERNS.get(element, [])
            found = False

            for pattern in patterns:
                try:
                    if re.search(pattern, response, re.IGNORECASE):
                        found = True
                        break
                except re.error:
                    continue

            if not found:
                missing.append(element)

        return missing

    def _check_tool_results(self, tool_results: dict[str, Any]) -> list[str]:
        """Check tool results for issues.

        Args:
            tool_results: Dictionary of tool name to result

        Returns:
            List of issues found with tool results
        """
        issues = []

        for tool_name, result in tool_results.items():
            if result is None:
                issues.append(f"Tool '{tool_name}' returned no results")
            elif isinstance(result, dict):
                if result.get("error"):
                    issues.append(f"Tool '{tool_name}' error: {result.get('error')}")
                elif result.get("success") is False:
                    issues.append(f"Tool '{tool_name}' failed")
                elif not result.get("data") and not result.get("items"):
                    # Check if it's an empty result
                    count_keys = ["count", "total", "total_found", "calls_found"]
                    has_count = any(result.get(k, 0) > 0 for k in count_keys)
                    if not has_count:
                        issues.append(f"Tool '{tool_name}' returned empty results")

        return issues

    def _calculate_score(
        self,
        response: str,
        deflection_phrases: list[str],
        missing_elements: list[str],
        is_too_short: bool,
        tool_issues: list[str],
    ) -> tuple[int, ResponseCategory]:
        """Calculate quality score and category.

        Args:
            response: The AI response text
            deflection_phrases: List of deflection phrases found
            missing_elements: List of missing elements
            is_too_short: Whether response is below minimum length
            tool_issues: List of tool-related issues

        Returns:
            Tuple of (score 0-100, ResponseCategory)
        """
        score = 100

        # Heavy penalty for deflection phrases (30 points per phrase, max 90)
        deflection_penalty = min(len(deflection_phrases) * 30, 90)
        score -= deflection_penalty

        # Penalty for missing elements (15 points per element, max 60)
        missing_penalty = min(len(missing_elements) * 15, 60)
        score -= missing_penalty

        # Penalty for being too short (20 points)
        if is_too_short:
            score -= 20

        # Penalty for tool issues (10 points per issue, max 30)
        tool_penalty = min(len(tool_issues) * 10, 30)
        score -= tool_penalty

        # Ensure score is in valid range
        score = max(0, min(100, score))

        # Determine category
        if len(deflection_phrases) >= 2 or (len(deflection_phrases) == 1 and score < 50):
            category = ResponseCategory.DEFLECTION
        elif len(response.strip()) < 50:
            category = ResponseCategory.EMPTY
        elif score < 50:
            category = ResponseCategory.PARTIAL
        elif len(missing_elements) > 0:
            category = ResponseCategory.PARTIAL
        else:
            category = ResponseCategory.COMPLETE

        return score, category

    def _generate_recommendations(
        self,
        deflection_phrases: list[str],
        missing_elements: list[str],
        is_too_short: bool,
        min_length: int,
        tool_issues: list[str],
    ) -> list[str]:
        """Generate recommendations for improving response quality.

        Args:
            deflection_phrases: List of deflection phrases found
            missing_elements: List of missing elements
            is_too_short: Whether response is below minimum length
            min_length: Minimum expected length
            tool_issues: List of tool-related issues

        Returns:
            List of recommendations
        """
        recommendations = []

        if deflection_phrases:
            recommendations.append(
                f"Remove deflection language: {', '.join(deflection_phrases[:3])}"
            )
            recommendations.append(
                "Provide specific information instead of saying what cannot be done"
            )

        if missing_elements:
            recommendations.append(f"Include missing elements: {', '.join(missing_elements)}")

        if is_too_short:
            recommendations.append(f"Expand response to at least {min_length} characters")

        if tool_issues:
            recommendations.append("Verify tool execution succeeded before synthesizing response")
            recommendations.append(f"Tool issues detected: {', '.join(tool_issues[:2])}")

        if not recommendations:
            recommendations.append("Response meets quality standards")

        return recommendations

    def _calculate_confidence(
        self,
        response_length: int,
        num_deflections: int,
        num_missing: int,
    ) -> float:
        """Calculate confidence in the analysis.

        Args:
            response_length: Length of the response
            num_deflections: Number of deflection phrases found
            num_missing: Number of missing elements

        Returns:
            Confidence score 0.0-1.0
        """
        # Base confidence
        confidence = 0.8

        # Higher confidence for longer responses (easier to analyze)
        if response_length > 500:
            confidence += 0.1
        elif response_length < 100:
            confidence -= 0.1

        # Higher confidence when we find clear indicators
        if num_deflections > 0:
            confidence += 0.05 * min(num_deflections, 2)

        # Lower confidence if we have many missing elements (might be false negatives)
        if num_missing > 3:
            confidence -= 0.1

        return max(0.5, min(1.0, confidence))

    def analyze_batch(
        self,
        items: list[tuple[str, str, str]],
    ) -> list[QualityAnalysis]:
        """Analyze a batch of query-response pairs.

        Args:
            items: List of (query, response, query_type) tuples

        Returns:
            List of QualityAnalysis results
        """
        return [self.analyze(query=item[0], response=item[1], query_type=item[2]) for item in items]

    def get_aggregate_stats(self, analyses: list[QualityAnalysis]) -> dict[str, Any]:
        """Get aggregate statistics from multiple analyses.

        Args:
            analyses: List of QualityAnalysis results

        Returns:
            Dictionary with aggregate statistics
        """
        if not analyses:
            return {"error": "No analyses provided"}

        scores = [a.score for a in analyses]
        categories = [a.category.value for a in analyses]

        return {
            "total_analyzed": len(analyses),
            "average_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "acceptable_count": sum(1 for a in analyses if a.is_acceptable()),
            "acceptable_rate": sum(1 for a in analyses if a.is_acceptable()) / len(analyses),
            "category_distribution": {cat: categories.count(cat) for cat in set(categories)},
            "common_deflections": self._get_common_deflections(analyses),
            "common_missing_elements": self._get_common_missing(analyses),
        }

    def _get_common_deflections(self, analyses: list[QualityAnalysis]) -> list[tuple[str, int]]:
        """Get most common deflection phrases across analyses.

        Args:
            analyses: List of QualityAnalysis results

        Returns:
            List of (phrase, count) tuples sorted by count
        """
        phrase_counts: dict[str, int] = {}
        for analysis in analyses:
            for phrase in analysis.deflection_phrases_found:
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1

        return sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    def _get_common_missing(self, analyses: list[QualityAnalysis]) -> list[tuple[str, int]]:
        """Get most commonly missing elements across analyses.

        Args:
            analyses: List of QualityAnalysis results

        Returns:
            List of (element, count) tuples sorted by count
        """
        element_counts: dict[str, int] = {}
        for analysis in analyses:
            for element in analysis.missing_elements:
                element_counts[element] = element_counts.get(element, 0) + 1

        return sorted(element_counts.items(), key=lambda x: x[1], reverse=True)[:5]
