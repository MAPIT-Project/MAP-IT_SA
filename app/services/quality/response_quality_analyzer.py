"""
Response Quality Analyzer Service

Analyzes and scores the quality of AI-generated responses to detect:
- Deflection phrases ("I could not find", "no information available", etc.)
- Incomplete answers (missing required elements)
- Low-quality responses (short, generic, unhelpful)

This service is designed for testing and monitoring AI response quality.
It helps identify when the AI is producing lazy or unhelpful responses.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ResponseCategory(str, Enum):
    """Category of response quality."""

    COMPLETE = "complete"       # Full, comprehensive answer
    PARTIAL = "partial"         # Some information but missing elements
    DEFLECTION = "deflection"   # Avoiding the question / no real answer
    EMPTY = "empty"             # Essentially empty response
    ERROR = "error"             # Error or failure response


@dataclass
class QualityAnalysis:
    """Result of quality analysis on a response."""

    score: int  # 0-100 quality score
    category: ResponseCategory
    confidence: float  # 0.0-1.0 confidence in analysis
    missing_elements: List[str] = field(default_factory=list)
    deflection_phrases_found: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    content_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "score": self.score,
            "category": self.category.value,
            "confidence": self.confidence,
            "missing_elements": self.missing_elements,
            "deflection_phrases_found": self.deflection_phrases_found,
            "recommendations": self.recommendations,
            "content_metrics": self.content_metrics,
        }


class ResponseQualityAnalyzer:
    """
    Analyzer for AI response quality.

    Detects deflection, incomplete answers, and provides actionable feedback.
    Designed for testing and quality monitoring of AI-generated responses.
    """

    # Phrases that indicate the AI is deflecting/avoiding the question
    DEFLECTION_PHRASES: List[str] = [
        "could not find",
        "no information available",
        "please try a more specific",
        "i am not sure",
        "i do not have",
        "unable to retrieve",
        "no results found",
        "try again later",
        "could not extract specific details",
        "found some information but",
        "i don't have access",
        "i cannot find",
        "no data available",
        "information not available",
        "unable to locate",
        "couldn't find any",
        "no matching results",
        "sorry, i could not",
        "unfortunately, i could not",
        "i was unable to",
        "the search returned no",
        "i couldn't retrieve",
        "no relevant information",
        "information is not currently available",
        "i don't have enough information",
    ]

    # Required elements for different query types
    CALL_REQUIRED_ELEMENTS: Set[str] = {
        "call_id",           # Call identifier/topic code
        "deadline",          # Deadline or timeline
        "budget",            # Budget range or funding amount
        "type",              # Type (RIA, IA, CSA, etc.)
        "status",            # Status (Open, Upcoming, Closed)
        "programme",         # Programme name
    }

    PROJECT_REQUIRED_ELEMENTS: Set[str] = {
        "acronym",           # Project acronym
        "title",             # Project title
        "funding",           # Funding amount
        "coordinator",       # Coordinating organization
        "status",            # Project status
    }

    COMPARISON_REQUIRED_ELEMENTS: Set[str] = {
        "programme_a",       # First programme mentioned
        "programme_b",       # Second programme mentioned
        "comparison",        # Comparison data/metrics
        "differences",       # Differences noted
    }

    def __init__(self):
        """Initialize the quality analyzer."""
        # Precompile regex patterns for efficiency
        self._deflection_patterns = [
            re.compile(re.escape(phrase), re.IGNORECASE)
            for phrase in self.DEFLECTION_PHRASES
        ]
        logger.info("ResponseQualityAnalyzer initialized")

    def analyze(self, query: str, response: str) -> QualityAnalysis:
        """
        Analyze the quality of an AI response.

        Args:
            query: The original user query
            response: The AI-generated response

        Returns:
            QualityAnalysis with score, category, and recommendations
        """
        if not response:
            return QualityAnalysis(
                score=0,
                category=ResponseCategory.EMPTY,
                confidence=1.0,
                missing_elements=["entire response"],
                recommendations=["Response is empty - AI failed to generate any content"],
            )

        # Normalize response for analysis
        response_lower = response.lower()
        response_length = len(response)

        # Initialize metrics
        deflection_phrases: List[str] = []
        missing_elements: List[str] = []
        recommendations: List[str] = []

        # 1. Check for deflection phrases
        for phrase in self.DEFLECTION_PHRASES:
            if phrase in response_lower:
                deflection_phrases.append(phrase)

        # 2. Check response length (substantive queries need substantive answers)
        is_substantive_query = len(query) > 20 and not self._is_simple_greeting(query)
        is_short_response = response_length < 200

        # 3. Infer query type and check required elements
        query_type = self._infer_query_type(query)
        if query_type:
            missing = self._check_required_elements(query_type, response)
            missing_elements.extend(missing)

        # 4. Calculate content metrics
        content_metrics = self._calculate_content_metrics(response)

        # 5. Determine category and score
        if len(deflection_phrases) >= 2:
            category = ResponseCategory.DEFLECTION
            score = 20  # Heavily penalize deflection
            recommendations.append(
                f"Response contains {len(deflection_phrases)} deflection phrases - "
                "AI is avoiding answering the question"
            )
        elif len(deflection_phrases) == 1 and is_short_response:
            category = ResponseCategory.DEFLECTION
            score = 30
            recommendations.append(
                f"Response contains deflection phrase '{deflection_phrases[0]}' "
                "and is too short - likely an unsatisfactory answer"
            )
        elif is_substantive_query and is_short_response and len(missing_elements) > 2:
            category = ResponseCategory.EMPTY
            score = 25
            recommendations.append(
                "Response is too short for the complexity of the query"
            )
        elif len(missing_elements) > 3:
            category = ResponseCategory.PARTIAL
            score = 50
            recommendations.append(
                f"Response is missing {len(missing_elements)} expected elements"
            )
        elif len(missing_elements) > 0:
            category = ResponseCategory.PARTIAL
            # Scale score based on missing elements (max 4 missing = score 60)
            score = max(60, 80 - (len(missing_elements) * 5))
            recommendations.append(
                f"Consider adding information about: {', '.join(missing_elements[:3])}"
            )
        else:
            category = ResponseCategory.COMPLETE
            # Base score 75, add points for length and richness
            score = min(100, 75 + self._calculate_richness_bonus(content_metrics))

        # 6. Calculate confidence based on how clearly we can categorize
        confidence = self._calculate_confidence(
            category=category,
            deflection_count=len(deflection_phrases),
            missing_count=len(missing_elements),
            response_length=response_length,
        )

        # 7. Add element-specific recommendations
        if missing_elements:
            for element in missing_elements[:3]:
                if element not in [r.lower() for r in recommendations]:
                    recommendations.append(f"Add {element} information")

        return QualityAnalysis(
            score=score,
            category=category,
            confidence=confidence,
            missing_elements=missing_elements,
            deflection_phrases_found=deflection_phrases,
            recommendations=recommendations,
            content_metrics=content_metrics,
        )

    def validate_call_response(
        self,
        response: str,
        expected_call_id: Optional[str] = None,
    ) -> QualityAnalysis:
        """
        Validate a response about funding calls.

        Args:
            response: The AI response about calls
            expected_call_id: Optional specific call ID that should be mentioned

        Returns:
            QualityAnalysis with call-specific validation
        """
        analysis = self.analyze("find funding calls", response)

        # Additional call-specific checks
        response_lower = response.lower()

        # Check for call-specific patterns
        has_deadline = any(
            pattern in response_lower
            for pattern in ["deadline", "closes", "submission date", "due date"]
        )
        has_budget = any(
            pattern in response_lower
            for pattern in ["budget", "million", "eur", "funding", "grant"]
        )
        has_type = any(
            pattern in response_lower
            for pattern in ["ria", "ia", "csa", "cofund", "erc", "msca"]
        )
        has_status = any(
            pattern in response_lower
            for pattern in ["open", "upcoming", "closed", "forthcoming"]
        )
        has_call_id = bool(re.search(r"horizon-[a-z0-9-]+", response_lower))

        # Count how many required elements are present
        elements_present = sum([
            has_deadline, has_budget, has_type, has_status, has_call_id
        ])

        # Adjust score based on call-specific elements
        if elements_present >= 4:
            analysis.score = min(100, analysis.score + 15)
            if analysis.category == ResponseCategory.PARTIAL:
                analysis.category = ResponseCategory.COMPLETE
        elif elements_present <= 2:
            analysis.score = max(0, analysis.score - 20)
            if analysis.category == ResponseCategory.COMPLETE:
                analysis.category = ResponseCategory.PARTIAL

        # Check for specific call ID if expected
        if expected_call_id and expected_call_id.lower() not in response_lower:
            analysis.missing_elements.append(f"expected call ID: {expected_call_id}")
            analysis.score = max(0, analysis.score - 15)

        return analysis

    def validate_project_response(
        self,
        response: str,
        expected_elements: Optional[List[str]] = None,
    ) -> QualityAnalysis:
        """
        Validate a response about projects.

        Args:
            response: The AI response about projects
            expected_elements: Optional list of elements that should be mentioned

        Returns:
            QualityAnalysis with project-specific validation
        """
        analysis = self.analyze("search projects", response)

        response_lower = response.lower()

        # Check for project-specific patterns
        has_acronym = bool(re.search(r"\b[A-Z]{3,10}\b", response))  # Acronyms are uppercase
        has_funding = any(
            pattern in response_lower
            for pattern in ["funding", "budget", "grant", "eur", "million"]
        )
        has_coordinator = "coordinator" in response_lower or "coordinated by" in response_lower
        has_objective = "objective" in response_lower or "aims to" in response_lower

        elements_present = sum([has_acronym, has_funding, has_coordinator, has_objective])

        if elements_present >= 3:
            analysis.score = min(100, analysis.score + 10)
        elif elements_present <= 1:
            analysis.score = max(0, analysis.score - 15)

        # Check for expected elements
        if expected_elements:
            for element in expected_elements:
                if element.lower() not in response_lower:
                    analysis.missing_elements.append(element)
                    analysis.score = max(0, analysis.score - 5)

        return analysis

    def validate_comparison_response(
        self,
        response: str,
        programme_a: str,
        programme_b: str,
    ) -> QualityAnalysis:
        """
        Validate a comparison response.

        Args:
            response: The AI response comparing programmes
            programme_a: First programme being compared
            programme_b: Second programme being compared

        Returns:
            QualityAnalysis with comparison-specific validation
        """
        query = f"Compare {programme_a} vs {programme_b}"
        analysis = self.analyze(query, response)

        response_lower = response.lower()

        # Both programmes should be mentioned
        has_prog_a = programme_a.lower() in response_lower
        has_prog_b = programme_b.lower() in response_lower

        # Check for comparison language
        comparison_words = [
            "compared to", "versus", "vs", "higher than", "lower than",
            "more than", "less than", "difference", "similar", "contrast",
            "while", "whereas", "on the other hand", "in comparison"
        ]
        has_comparison = any(word in response_lower for word in comparison_words)

        # Check for metrics
        has_metrics = any(
            pattern in response_lower
            for pattern in ["success rate", "funding", "budget", "percentage", "%"]
        )

        # Validate required elements
        if not has_prog_a:
            analysis.missing_elements.append(f"mention of {programme_a}")
            analysis.score = max(0, analysis.score - 20)

        if not has_prog_b:
            analysis.missing_elements.append(f"mention of {programme_b}")
            analysis.score = max(0, analysis.score - 20)

        if not has_comparison:
            analysis.missing_elements.append("comparison language")
            analysis.score = max(0, analysis.score - 15)

        if not has_metrics:
            analysis.missing_elements.append("comparative metrics")
            analysis.score = max(0, analysis.score - 10)

        if has_prog_a and has_prog_b and has_comparison and has_metrics:
            analysis.score = min(100, analysis.score + 15)
            analysis.category = ResponseCategory.COMPLETE

        return analysis

    def validate_budget_benchmark_response(self, response: str) -> QualityAnalysis:
        """
        Validate a budget benchmark response.

        Args:
            response: The AI response about budget benchmarks

        Returns:
            QualityAnalysis with budget-specific validation
        """
        analysis = self.analyze("budget benchmark", response)
        response_lower = response.lower()

        # Check for budget-specific elements
        has_average = any(
            pattern in response_lower
            for pattern in ["average", "mean", "typical"]
        )
        has_range = any(
            pattern in response_lower
            for pattern in ["range", "minimum", "maximum", "from", "to"]
        )
        has_currency = any(
            pattern in response_lower
            for pattern in ["eur", "euro", "million", "m"]
        )
        has_project_count = any(
            pattern in response_lower
            for pattern in ["projects", "based on", "analyzed"]
        )

        elements_present = sum([has_average, has_range, has_currency, has_project_count])

        if elements_present >= 3:
            analysis.score = min(100, analysis.score + 15)
            analysis.category = ResponseCategory.COMPLETE
        elif elements_present <= 1:
            analysis.score = max(0, analysis.score - 20)
            analysis.missing_elements.append("budget statistics")

        return analysis

    def validate_partner_discovery_response(
        self,
        response: str,
        expected_country: Optional[str] = None,
    ) -> QualityAnalysis:
        """
        Validate a partner discovery response.

        Args:
            response: The AI response about potential partners
            expected_country: Optional country filter

        Returns:
            QualityAnalysis with partner-specific validation
        """
        analysis = self.analyze("find partners", response)
        response_lower = response.lower()

        # Check for partner-specific elements
        has_org_names = bool(re.search(r"[A-Z][a-zA-Z\s]+(?:University|Institute|Ltd|GmbH|SA|AG)", response))
        has_experience = any(
            pattern in response_lower
            for pattern in ["experience", "participated", "projects", "expertise"]
        )
        has_country = expected_country.lower() in response_lower if expected_country else True

        if has_org_names and has_experience:
            analysis.score = min(100, analysis.score + 10)

        if expected_country and not has_country:
            analysis.missing_elements.append(f"partners from {expected_country}")
            analysis.score = max(0, analysis.score - 15)

        return analysis

    def is_acceptable(self, analysis: QualityAnalysis, min_score: int = 70) -> bool:
        """
        Check if the response quality is acceptable.

        Args:
            analysis: The quality analysis result
            min_score: Minimum acceptable score (default 70)

        Returns:
            True if acceptable, False otherwise
        """
        return (
            analysis.score >= min_score
            and analysis.category not in [ResponseCategory.DEFLECTION, ResponseCategory.EMPTY]
        )

    def _infer_query_type(self, query: str) -> Optional[str]:
        """Infer the type of query for validation."""
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["call", "funding", "deadline", "horizon-"]):
            return "call"
        elif any(kw in query_lower for kw in ["project", "funded", "cordis"]):
            return "project"
        elif any(kw in query_lower for kw in ["compare", "versus", "vs", "difference"]):
            return "comparison"
        elif any(kw in query_lower for kw in ["budget", "benchmark", "typical cost"]):
            return "budget"
        elif any(kw in query_lower for kw in ["partner", "organization", "consortium"]):
            return "partner"

        return None

    def _check_required_elements(
        self,
        query_type: str,
        response: str,
    ) -> List[str]:
        """Check which required elements are missing from the response."""
        response_lower = response.lower()
        missing = []

        if query_type == "call":
            if not any(kw in response_lower for kw in ["horizon-", "call id", "topic"]):
                missing.append("call_id")
            if not any(kw in response_lower for kw in ["deadline", "closes", "date"]):
                missing.append("deadline")
            if not any(kw in response_lower for kw in ["budget", "million", "eur"]):
                missing.append("budget")
            if not any(kw in response_lower for kw in ["ria", "ia", "csa", "type"]):
                missing.append("type")
            if not any(kw in response_lower for kw in ["open", "upcoming", "closed"]):
                missing.append("status")

        elif query_type == "project":
            if not bool(re.search(r"\b[A-Z]{3,10}\b", response)):
                missing.append("project_acronym")
            if not any(kw in response_lower for kw in ["funding", "budget", "grant"]):
                missing.append("funding_amount")

        elif query_type == "comparison":
            if not any(kw in response_lower for kw in ["compare", "versus", "difference"]):
                missing.append("comparison_language")

        return missing

    def _calculate_content_metrics(self, response: str) -> Dict[str, Any]:
        """Calculate various content metrics for the response."""
        words = response.split()
        sentences = re.split(r"[.!?]+", response)

        return {
            "character_count": len(response),
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "avg_word_length": sum(len(w) for w in words) / max(len(words), 1),
            "has_structured_data": any(
                pattern in response
                for pattern in ["**", "- ", "1.", "2.", "|"]
            ),
            "has_links": "http" in response or "https" in response,
            "has_numbers": bool(re.search(r"\d+", response)),
        }

    def _calculate_richness_bonus(self, metrics: Dict[str, Any]) -> int:
        """Calculate bonus points based on content richness."""
        bonus = 0

        if metrics.get("word_count", 0) > 300:
            bonus += 5
        if metrics.get("has_structured_data"):
            bonus += 5
        if metrics.get("has_links"):
            bonus += 5
        if metrics.get("has_numbers"):
            bonus += 5
        if metrics.get("sentence_count", 0) > 5:
            bonus += 5

        return bonus

    def _calculate_confidence(
        self,
        category: ResponseCategory,
        deflection_count: int,
        missing_count: int,
        response_length: int,
    ) -> float:
        """Calculate confidence in the quality analysis."""
        # High confidence cases
        if deflection_count >= 3:
            return 0.95  # Very confident it's deflection
        if response_length < 50:
            return 0.90  # Very confident it's empty/low quality
        if category == ResponseCategory.COMPLETE and missing_count == 0:
            return 0.85  # Confident it's complete

        # Medium confidence
        if deflection_count == 1 or missing_count <= 2:
            return 0.70

        # Lower confidence for edge cases
        return 0.60

    def _is_simple_greeting(self, query: str) -> bool:
        """Check if query is a simple greeting that doesn't need a long answer."""
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "thanks"]
        query_lower = query.lower().strip()
        return any(query_lower.startswith(g) for g in greetings)
