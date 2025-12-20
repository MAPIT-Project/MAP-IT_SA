"""
Response Quality Analyzer.

Analyzes AI response quality to ensure responses are complete, actionable,
and do not contain deflection phrases that avoid answering the user's question.

Features:
- Deflection phrase detection
- Content element validation
- Quality scoring (0-100)
- Response categorization
- Improvement recommendations
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Pattern, Set

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Deflection phrases that indicate the AI failed to provide useful information
DEFLECTION_PHRASES: List[str] = [
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
    "no specific data",
    "cannot provide",
    "don't have access",
    "beyond my knowledge",
    "i cannot answer",
    "i'm unable to",
    "no matching",
    "unfortunately",
    "i apologize but",
    "i'm sorry but i cannot",
    "i don't know",
    "not available at this time",
    "information is not available",
    "i was unable to",
    "i couldn't locate",
    "no data available",
]

# Query types and their expected elements
QUERY_TYPE_EXPECTATIONS: Dict[str, Dict[str, List[str]]] = {
    "call_search": {
        "required": ["call_id", "deadline", "type"],
        "optional": ["budget", "status", "scope", "programme"],
        "min_score": 75,
    },
    "call_details": {
        "required": ["call_id", "deadline", "type", "status"],
        "optional": ["budget", "scope", "eligibility", "apply_link"],
        "min_score": 80,
    },
    "project_search": {
        "required": ["project_name", "participants"],
        "optional": ["budget", "duration", "objectives", "acronym"],
        "min_score": 70,
    },
    "programme_comparison": {
        "required": ["programme_a", "programme_b", "comparison_metric"],
        "optional": ["statistics", "differences", "recommendations"],
        "min_score": 75,
    },
    "eligibility_faq": {
        "required": ["answer"],
        "optional": ["source", "exceptions", "examples"],
        "min_score": 70,
    },
    "budget_benchmark": {
        "required": ["budget_range", "statistics"],
        "optional": ["recommendations", "sample_projects", "breakdown"],
        "min_score": 75,
    },
    "partner_discovery": {
        "required": ["partners", "experience"],
        "optional": ["projects", "countries", "org_types"],
        "min_score": 70,
    },
    "consortium_patterns": {
        "required": ["consortium_size", "org_distribution"],
        "optional": ["country_distribution", "coordinator_analysis"],
        "min_score": 70,
    },
}

# Minimum response length by query type
MIN_RESPONSE_LENGTHS: Dict[str, int] = {
    "call_search": 200,
    "call_details": 300,
    "project_search": 200,
    "programme_comparison": 400,
    "eligibility_faq": 150,
    "budget_benchmark": 250,
    "partner_discovery": 200,
    "consortium_patterns": 250,
    "default": 150,
}


# =============================================================================
# Data Models
# =============================================================================


class ResponseCategory(str, Enum):
    """Category of response quality."""
    COMPLETE = "complete"       # All expected elements present
    PARTIAL = "partial"         # Some expected elements missing
    DEFLECTION = "deflection"   # Response avoids answering
    EMPTY = "empty"             # No useful content
    ERROR = "error"             # Error response


@dataclass
class QualityAnalysis:
    """Result of response quality analysis."""
    score: int  # 0-100
    category: ResponseCategory
    confidence: float  # 0.0-1.0
    query_type: Optional[str] = None
    expected_elements: List[str] = field(default_factory=list)
    found_elements: List[str] = field(default_factory=list)
    missing_elements: List[str] = field(default_factory=list)
    deflection_phrases_found: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    response_length: int = 0
    min_length_met: bool = True
    passed: bool = True

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "score": self.score,
            "category": self.category.value,
            "confidence": self.confidence,
            "query_type": self.query_type,
            "expected_elements": self.expected_elements,
            "found_elements": self.found_elements,
            "missing_elements": self.missing_elements,
            "deflection_phrases_found": self.deflection_phrases_found,
            "recommendations": self.recommendations,
            "response_length": self.response_length,
            "min_length_met": self.min_length_met,
            "passed": self.passed,
        }


# =============================================================================
# Analyzer
# =============================================================================


class ResponseQualityAnalyzer:
    """
    Analyzes AI response quality.

    Usage:
        analyzer = ResponseQualityAnalyzer()
        analysis = analyzer.analyze(
            query="Tell me about HORIZON-CL5-2026-D3-01",
            response="I found information about this call...",
            query_type="call_details"
        )

        if not analysis.passed:
            print(f"Quality check failed: {analysis.category}")
            print(f"Missing: {analysis.missing_elements}")
    """

    def __init__(
        self,
        deflection_phrases: Optional[List[str]] = None,
        min_score_threshold: int = 70,
        strict_mode: bool = False,
    ):
        """
        Initialize the analyzer.

        Args:
            deflection_phrases: Custom list of deflection phrases
            min_score_threshold: Minimum score to pass (0-100)
            strict_mode: If True, any deflection phrase fails the check
        """
        self.deflection_phrases = deflection_phrases or DEFLECTION_PHRASES
        self.min_score_threshold = min_score_threshold
        self.strict_mode = strict_mode

        # Pre-compile patterns for performance
        self._deflection_patterns: List[Pattern] = [
            re.compile(re.escape(phrase), re.IGNORECASE)
            for phrase in self.deflection_phrases
        ]

    def analyze(
        self,
        query: str,
        response: str,
        query_type: Optional[str] = None,
        expected_elements: Optional[List[str]] = None,
        tools_used: Optional[List[str]] = None,
        tool_results: Optional[Dict] = None,
    ) -> QualityAnalysis:
        """
        Analyze response quality.

        Args:
            query: The user's query
            response: The AI response to analyze
            query_type: Type of query (call_search, project_search, etc.)
            expected_elements: Elements expected in the response
            tools_used: List of tools that were used
            tool_results: Results from tool calls

        Returns:
            QualityAnalysis with detailed quality metrics
        """
        # Handle empty/error responses
        if not response or response.strip() == "":
            return self._create_analysis(
                score=0,
                category=ResponseCategory.EMPTY,
                confidence=1.0,
                query_type=query_type,
                recommendations=["Response is empty - no content was generated"],
                response_length=0,
            )

        response_lower = response.lower()
        response_length = len(response)

        # Check for deflection phrases
        deflection_phrases_found = self._find_deflection_phrases(response_lower)

        # Infer query type if not provided
        if not query_type:
            query_type = self._infer_query_type(query)

        # Get expected elements
        if expected_elements is None and query_type:
            expectations = QUERY_TYPE_EXPECTATIONS.get(query_type, {})
            expected_elements = expectations.get("required", [])

        # Find elements in response
        found_elements = self._find_elements_in_response(response, expected_elements or [])
        missing_elements = [e for e in (expected_elements or []) if e not in found_elements]

        # Check minimum length
        min_length = MIN_RESPONSE_LENGTHS.get(query_type or "default", 150)
        min_length_met = response_length >= min_length

        # Calculate score
        score = self._calculate_score(
            response_length=response_length,
            deflection_count=len(deflection_phrases_found),
            found_count=len(found_elements),
            expected_count=len(expected_elements or []),
            min_length_met=min_length_met,
            tools_used=tools_used,
            tool_results=tool_results,
        )

        # Determine category
        category = self._determine_category(
            score=score,
            deflection_count=len(deflection_phrases_found),
            missing_count=len(missing_elements),
            response_length=response_length,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            category=category,
            missing_elements=missing_elements,
            deflection_phrases=deflection_phrases_found,
            min_length_met=min_length_met,
            tools_used=tools_used,
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            score=score,
            response_length=response_length,
            deflection_count=len(deflection_phrases_found),
        )

        # Determine if passed
        passed = self._check_passed(
            score=score,
            category=category,
            deflection_count=len(deflection_phrases_found),
        )

        return self._create_analysis(
            score=score,
            category=category,
            confidence=confidence,
            query_type=query_type,
            expected_elements=expected_elements or [],
            found_elements=found_elements,
            missing_elements=missing_elements,
            deflection_phrases_found=deflection_phrases_found,
            recommendations=recommendations,
            response_length=response_length,
            min_length_met=min_length_met,
            passed=passed,
        )

    def _find_deflection_phrases(self, response_lower: str) -> List[str]:
        """Find all deflection phrases in the response."""
        found = []
        for i, pattern in enumerate(self._deflection_patterns):
            if pattern.search(response_lower):
                found.append(self.deflection_phrases[i])
        return found

    def _infer_query_type(self, query: str) -> Optional[str]:
        """Infer query type from the query text."""
        query_lower = query.lower()

        # Pattern matching for query types
        if any(word in query_lower for word in ["horizon-", "call id", "topic code", "tell me about horizon"]):
            return "call_details"
        if any(word in query_lower for word in ["find calls", "search calls", "funding calls", "open calls"]):
            return "call_search"
        if any(word in query_lower for word in ["project", "cordis", "funded project"]):
            return "project_search"
        if any(word in query_lower for word in ["compare", "vs", "versus", "difference between"]):
            return "programme_comparison"
        if any(word in query_lower for word in ["eligible", "can i apply", "requirements", "rules"]):
            return "eligibility_faq"
        if any(word in query_lower for word in ["budget", "how much", "funding amount", "typical budget"]):
            return "budget_benchmark"
        if any(word in query_lower for word in ["partner", "find organization", "experienced"]):
            return "partner_discovery"
        if any(word in query_lower for word in ["consortium", "partners", "team composition"]):
            return "consortium_patterns"

        return None

    def _find_elements_in_response(
        self,
        response: str,
        expected_elements: List[str],
    ) -> List[str]:
        """Find which expected elements are present in the response."""
        response_lower = response.lower()
        found = []

        # Element detection patterns
        element_patterns: Dict[str, List[str]] = {
            "call_id": ["horizon-", "call id:", "topic:", "topic code:", "call:"],
            "deadline": ["deadline", "closes", "submission date", "due date", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "jan", "2024", "2025", "2026"],
            "type": ["ria", "ia", "csa", "cofund", "erc", "msca", "research and innovation", "innovation action"],
            "status": ["open", "upcoming", "closed", "forthcoming"],
            "budget": ["budget", "eur", "€", "million", "funding", "contribution"],
            "scope": ["scope", "objective", "focus", "aim", "goal"],
            "programme": ["cluster", "pillar", "horizon europe", "horizon 2020"],
            "apply_link": ["apply", "portal", "funding-tenders", "ec.europa.eu"],
            "eligibility": ["eligible", "eligibility", "requirement", "criteria"],
            "project_name": ["project", "acronym", "title:"],
            "participants": ["participant", "partner", "consortium", "coordinator", "member"],
            "duration": ["month", "year", "duration", "period"],
            "objectives": ["objective", "goal", "aim", "target"],
            "acronym": ["acronym"],
            "programme_a": ["eic", "erc", "ria", "ia"],
            "programme_b": ["eic", "erc", "ria", "ia"],
            "comparison_metric": ["success rate", "funding", "budget", "difference", "compare"],
            "statistics": ["statistics", "rate", "average", "total", "%", "percent"],
            "differences": ["difference", "unlike", "whereas", "however"],
            "recommendations": ["recommend", "suggest", "advise", "consider"],
            "answer": ["yes", "no", "can", "must", "should", "required", "allowed"],
            "source": ["according to", "based on", "regulation", "rule"],
            "exceptions": ["except", "unless", "however", "but"],
            "examples": ["example", "such as", "e.g.", "for instance"],
            "budget_range": ["€", "eur", "million", "range", "min", "max", "average", "median"],
            "sample_projects": ["project", "similar", "example", "funded"],
            "breakdown": ["breakdown", "personnel", "equipment", "travel", "subcontracting"],
            "partners": ["partner", "organization", "institution", "company"],
            "experience": ["experience", "track record", "previous", "expertise"],
            "projects": ["project", "grant", "funded"],
            "countries": ["germany", "france", "spain", "italy", "country", "de", "fr", "es", "it"],
            "org_types": ["university", "sme", "research", "company", "hes", "rec", "prc"],
            "consortium_size": ["partner", "member", "consortium size", "average"],
            "org_distribution": ["distribution", "percentage", "share", "%"],
            "country_distribution": ["country", "nation", "geographic"],
            "coordinator_analysis": ["coordinator", "lead", "leading"],
        }

        for element in expected_elements:
            element_lower = element.lower()
            patterns = element_patterns.get(element_lower, [element_lower])

            for pattern in patterns:
                if pattern in response_lower:
                    found.append(element)
                    break

        return list(set(found))

    def _calculate_score(
        self,
        response_length: int,
        deflection_count: int,
        found_count: int,
        expected_count: int,
        min_length_met: bool,
        tools_used: Optional[List[str]] = None,
        tool_results: Optional[Dict] = None,
    ) -> int:
        """Calculate quality score (0-100)."""
        score = 50  # Base score

        # Length scoring (up to +20)
        if response_length >= 500:
            score += 20
        elif response_length >= 300:
            score += 15
        elif response_length >= 200:
            score += 10
        elif response_length >= 100:
            score += 5
        elif response_length < 50:
            score -= 20

        # Length requirement penalty
        if not min_length_met:
            score -= 15

        # Deflection penalty (severe)
        score -= deflection_count * 25

        # Element coverage scoring
        if expected_count > 0:
            coverage_ratio = found_count / expected_count
            score += int(coverage_ratio * 30)  # Up to +30 for full coverage
            if coverage_ratio < 0.5:
                score -= 10  # Penalty for less than 50% coverage

        # Tool usage bonus
        if tools_used and len(tools_used) > 0:
            score += min(10, len(tools_used) * 3)  # Up to +10 for using tools

        # Tool results validation
        if tool_results:
            for tool, result in tool_results.items():
                if isinstance(result, dict):
                    if result.get("error"):
                        score -= 5
                    elif result.get("success") or result.get("found"):
                        score += 5

        # Clamp to 0-100
        return max(0, min(100, score))

    def _determine_category(
        self,
        score: int,
        deflection_count: int,
        missing_count: int,
        response_length: int,
    ) -> ResponseCategory:
        """Determine response category based on analysis."""
        if response_length < 50:
            return ResponseCategory.EMPTY

        if deflection_count >= 2 or (deflection_count >= 1 and score < 50):
            return ResponseCategory.DEFLECTION

        if score >= 75 and missing_count == 0:
            return ResponseCategory.COMPLETE

        if score >= 50:
            return ResponseCategory.PARTIAL

        if deflection_count > 0:
            return ResponseCategory.DEFLECTION

        return ResponseCategory.PARTIAL

    def _generate_recommendations(
        self,
        category: ResponseCategory,
        missing_elements: List[str],
        deflection_phrases: List[str],
        min_length_met: bool,
        tools_used: Optional[List[str]] = None,
    ) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        if category == ResponseCategory.DEFLECTION:
            recommendations.append("Response contains deflection phrases - ensure actual information is provided")
            if deflection_phrases:
                recommendations.append(f"Remove or replace: {', '.join(deflection_phrases[:3])}")

        if missing_elements:
            recommendations.append(f"Include missing elements: {', '.join(missing_elements[:5])}")

        if not min_length_met:
            recommendations.append("Response is too short - provide more detailed information")

        if category == ResponseCategory.EMPTY:
            recommendations.append("Response has no content - check tool execution and data sources")

        if not tools_used or len(tools_used) == 0:
            recommendations.append("Consider using appropriate tools to gather information")

        return recommendations

    def _calculate_confidence(
        self,
        score: int,
        response_length: int,
        deflection_count: int,
    ) -> float:
        """Calculate confidence in the analysis."""
        # High confidence if clear signals
        if deflection_count >= 2:
            return 0.95  # Very confident it's a deflection
        if response_length < 50:
            return 0.95  # Very confident it's empty
        if score >= 85:
            return 0.90  # Confident it's good
        if score <= 30:
            return 0.85  # Confident it's poor

        # Medium confidence for borderline cases
        return 0.70

    def _check_passed(
        self,
        score: int,
        category: ResponseCategory,
        deflection_count: int,
    ) -> bool:
        """Check if the response passes quality requirements."""
        if self.strict_mode and deflection_count > 0:
            return False

        if category in (ResponseCategory.DEFLECTION, ResponseCategory.EMPTY):
            return False

        return score >= self.min_score_threshold

    def _create_analysis(
        self,
        score: int,
        category: ResponseCategory,
        confidence: float,
        query_type: Optional[str] = None,
        expected_elements: Optional[List[str]] = None,
        found_elements: Optional[List[str]] = None,
        missing_elements: Optional[List[str]] = None,
        deflection_phrases_found: Optional[List[str]] = None,
        recommendations: Optional[List[str]] = None,
        response_length: int = 0,
        min_length_met: bool = True,
        passed: Optional[bool] = None,
    ) -> QualityAnalysis:
        """Create a QualityAnalysis with the given parameters."""
        # Ensure empty responses always fail
        if category == ResponseCategory.EMPTY:
            passed = False
        elif passed is None:
            passed = self._check_passed(
                score=score,
                category=category,
                deflection_count=len(deflection_phrases_found or []),
            )

        return QualityAnalysis(
            score=score,
            category=category,
            confidence=confidence,
            query_type=query_type,
            expected_elements=expected_elements or [],
            found_elements=found_elements or [],
            missing_elements=missing_elements or [],
            deflection_phrases_found=deflection_phrases_found or [],
            recommendations=recommendations or [],
            response_length=response_length,
            min_length_met=min_length_met,
            passed=passed,
        )

    def batch_analyze(
        self,
        queries_and_responses: List[Dict],
    ) -> List[QualityAnalysis]:
        """
        Analyze multiple query-response pairs.

        Args:
            queries_and_responses: List of dicts with 'query', 'response', and optional 'query_type'

        Returns:
            List of QualityAnalysis results
        """
        return [
            self.analyze(
                query=item.get("query", ""),
                response=item.get("response", ""),
                query_type=item.get("query_type"),
                expected_elements=item.get("expected_elements"),
                tools_used=item.get("tools_used"),
                tool_results=item.get("tool_results"),
            )
            for item in queries_and_responses
        ]

    def get_summary_stats(self, analyses: List[QualityAnalysis]) -> Dict:
        """
        Get summary statistics for a batch of analyses.

        Args:
            analyses: List of QualityAnalysis results

        Returns:
            Summary statistics dict
        """
        if not analyses:
            return {"total": 0}

        passed = sum(1 for a in analyses if a.passed)
        categories = {}
        for a in analyses:
            cat = a.category.value
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total": len(analyses),
            "passed": passed,
            "failed": len(analyses) - passed,
            "pass_rate": passed / len(analyses),
            "average_score": sum(a.score for a in analyses) / len(analyses),
            "categories": categories,
            "deflection_rate": categories.get("deflection", 0) / len(analyses),
        }
