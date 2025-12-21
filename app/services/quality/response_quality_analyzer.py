"""
Response Quality Analyzer for MAP-IT AI Responses.

This module provides comprehensive analysis of AI responses to detect:
- Deflection phrases that indicate the AI failed to answer properly
- Missing required elements based on query type
- Response completeness and quality scoring
- Actionable recommendations for improvement

The analyzer is designed to catch common failure modes where the AI
returns unhelpful responses like "I could not find information" instead
of actually answering the query.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ResponseCategory(str, Enum):
    """Categories for response quality."""

    COMPLETE = "complete"  # Response fully answers the query
    PARTIAL = "partial"  # Response has some information but missing elements
    DEFLECTION = "deflection"  # Response deflects instead of answering
    EMPTY = "empty"  # Response is empty or near-empty
    ERROR = "error"  # Response indicates an error occurred


class QueryType(str, Enum):
    """Types of queries with specific requirements."""

    CALL_SEARCH = "call_search"  # Looking for funding calls
    CALL_SPECIFIC = "call_specific"  # Asking about a specific call ID
    PROJECT_SEARCH = "project_search"  # Looking for funded projects
    PROGRAMME_COMPARISON = "programme_comparison"  # Comparing programmes
    ELIGIBILITY_FAQ = "eligibility_faq"  # Eligibility and rules questions
    BUDGET_BENCHMARK = "budget_benchmark"  # Budget statistics queries
    PARTNER_DISCOVERY = "partner_discovery"  # Finding partners
    CONSORTIUM_PATTERN = "consortium_pattern"  # Consortium composition queries
    STATISTICS = "statistics"  # General statistics queries
    GENERAL = "general"  # General queries


class QualityAnalysis(BaseModel):
    """Result of quality analysis on a response."""

    score: int = Field(..., ge=0, le=100, description="Quality score 0-100")
    category: ResponseCategory = Field(..., description="Response category")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the analysis"
    )
    query_type: QueryType = Field(
        default=QueryType.GENERAL, description="Detected query type"
    )
    missing_elements: List[str] = Field(
        default_factory=list, description="Required elements not found"
    )
    deflection_phrases_found: List[str] = Field(
        default_factory=list, description="Deflection phrases detected"
    )
    positive_indicators: List[str] = Field(
        default_factory=list, description="Positive quality indicators found"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for improvement"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional analysis metadata"
    )


@dataclass
class QueryRequirements:
    """Requirements for a specific query type."""

    required_elements: List[str]
    min_response_length: int = 200
    expected_patterns: List[str] = field(default_factory=list)
    positive_indicators: List[str] = field(default_factory=list)


class ResponseQualityAnalyzer:
    """
    Analyzes AI response quality to detect deflections and incomplete answers.

    This analyzer is specifically designed for EU funding queries and ensures
    that responses contain the expected information rather than generic
    deflection phrases.

    Attributes:
        DEFLECTION_PHRASES: Common phrases indicating the AI failed to answer
        QUERY_REQUIREMENTS: Required elements by query type
    """

    # Phrases that indicate the AI is deflecting instead of answering
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
        "i cannot provide",
        "i can't provide",
        "no matching",
        "no data available",
        "information is not available",
        "beyond my knowledge",
        "outside my training",
        "i don't know",
        "i do not know",
        "unfortunately",
        "i apologize but",
        "i'm sorry but",
        "i was unable to",
        "this information is currently unavailable",
        "i could not locate",
        "no specific information",
    ]

    # Patterns that indicate positive quality
    POSITIVE_INDICATORS: List[str] = [
        r"\*\*[A-Z]",  # Bold formatted headers
        r"€\s?\d",  # Euro amounts
        r"\d+[\.,]\d+\s*(million|billion|M|B)",  # Funding amounts
        r"HORIZON-[A-Z]{2,3}\d?-\d{4}",  # Call IDs
        r"🔬|🚀|🤝|💱|🎓|👨‍🔬",  # Action type icons
        r"🟢|🟡|🔴",  # Status icons
        r"\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}",  # Dates
        r"(RIA|IA|CSA|COFUND|ERC|MSCA)",  # Action types
        r"Cluster\s*[1-6]|CL[1-6]|CLUSTER-[1-6]",  # Cluster references
        r"https?://",  # URLs (apply links)
    ]

    # Requirements by query type
    QUERY_REQUIREMENTS: Dict[QueryType, QueryRequirements] = {
        QueryType.CALL_SPECIFIC: QueryRequirements(
            required_elements=[
                "call_id",
                "deadline_or_timeline",
                "budget_or_funding",
                "action_type",
                "status",
            ],
            min_response_length=300,
            expected_patterns=[
                r"HORIZON-[A-Z]{2,3}\d?-\d{4}",
                r"(deadline|closes?|due)",
            ],
            positive_indicators=["📋", "⏰", "💰", "🏛️"],
        ),
        QueryType.CALL_SEARCH: QueryRequirements(
            required_elements=[
                "call_count_or_results",
                "at_least_one_call_id",
            ],
            min_response_length=200,
            expected_patterns=[
                r"found\s+\d+",
                r"HORIZON-[A-Z]{2,3}\d?-\d{4}",
            ],
        ),
        QueryType.PROJECT_SEARCH: QueryRequirements(
            required_elements=[
                "project_names_or_acronyms",
            ],
            min_response_length=150,
            expected_patterns=[
                r"project",
            ],
        ),
        QueryType.PROGRAMME_COMPARISON: QueryRequirements(
            required_elements=[
                "programme_1_info",
                "programme_2_info",
                "comparison_metrics",
            ],
            min_response_length=400,
            expected_patterns=[
                r"(EIC|ERC|MSCA|RIA|IA|CSA)",
                r"(compare|comparison|versus|vs\.?|differ)",
            ],
        ),
        QueryType.ELIGIBILITY_FAQ: QueryRequirements(
            required_elements=[
                "clear_answer",
                "relevant_rules_or_criteria",
            ],
            min_response_length=150,
        ),
        QueryType.BUDGET_BENCHMARK: QueryRequirements(
            required_elements=[
                "budget_statistics",
                "numerical_values",
            ],
            min_response_length=200,
            expected_patterns=[
                r"€\s?\d|EUR",
                r"(average|median|typical|range)",
            ],
        ),
        QueryType.PARTNER_DISCOVERY: QueryRequirements(
            required_elements=[
                "partner_names_or_organizations",
                "experience_indicators",
            ],
            min_response_length=200,
            expected_patterns=[
                r"(partner|organization|institution|company)",
                r"(experience|expertise|participated|involved)",
            ],
        ),
        QueryType.CONSORTIUM_PATTERN: QueryRequirements(
            required_elements=[
                "consortium_size_info",
                "composition_details",
            ],
            min_response_length=200,
            expected_patterns=[
                r"(partner|member|organization)",
                r"\d+\s*(partner|member|countr)",
            ],
        ),
        QueryType.STATISTICS: QueryRequirements(
            required_elements=[
                "numerical_data",
            ],
            min_response_length=100,
            expected_patterns=[
                r"\d+[\.,]?\d*\s*%?",
            ],
        ),
        QueryType.GENERAL: QueryRequirements(
            required_elements=[],
            min_response_length=100,
        ),
    }

    # Query type detection patterns
    QUERY_TYPE_PATTERNS: Dict[QueryType, List[str]] = {
        QueryType.CALL_SPECIFIC: [
            r"HORIZON-[A-Z]{2,3}\d?-\d{4}",
            r"tell me about.*call",
            r"what is.*call.*HORIZON",
            r"details.*call",
            r"call.*details",
            r"describe.*HORIZON",
        ],
        QueryType.CALL_SEARCH: [
            r"find.*call",
            r"search.*call",
            r"looking for.*call",
            r"open.*call",
            r"funding.*opportunit",
            r"upcoming.*call",
        ],
        QueryType.PROJECT_SEARCH: [
            r"find.*project",
            r"search.*project",
            r"funded.*project",
            r"projects.*about",
            r"projects.*related",
        ],
        QueryType.PROGRAMME_COMPARISON: [
            r"compare",
            r"comparison",
            r"versus",
            r"vs\.?\s",
            r"differ.*between",
            r"what.*difference",
            r"how do.*differ",
            r"and.*differ\??$",
        ],
        QueryType.ELIGIBILITY_FAQ: [
            r"can.*participate",
            r"eligible",
            r"eligibility",
            r"can.*apply",
            r"who can",
            r"allowed to",
            r"requirements.*to.*apply",
            r"apply.*requirements",
        ],
        QueryType.BUDGET_BENCHMARK: [
            r"budget",
            r"typical.*funding",
            r"average.*budget",
            r"how much.*funding",
            r"funding.*amount",
            r"benchmark",
        ],
        QueryType.PARTNER_DISCOVERY: [
            r"find.*partner",
            r"looking for.*partner",
            r"organizations.*with.*experience",
            r"experienced.*partner",
            r"potential.*partner",
            r"with.*experience$",
            r"SMEs with",
            r"partners for",
        ],
        QueryType.CONSORTIUM_PATTERN: [
            r"consortium.*size",
            r"consortium.*composition",
            r"typical.*consortium",
            r"how many.*partner",
            r"partner.*distribution",
        ],
        QueryType.STATISTICS: [
            r"success.*rate",
            r"statistics",
            r"how many",
            r"what percentage",
            r"participation.*data",
        ],
    }

    def __init__(self) -> None:
        """Initialize the ResponseQualityAnalyzer."""
        # Compile patterns for efficiency
        self._deflection_patterns = [
            re.compile(re.escape(phrase), re.IGNORECASE)
            for phrase in self.DEFLECTION_PHRASES
        ]
        self._positive_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.POSITIVE_INDICATORS
        ]
        self._query_type_compiled = {
            qt: [re.compile(p, re.IGNORECASE) for p in patterns]
            for qt, patterns in self.QUERY_TYPE_PATTERNS.items()
        }

    def detect_query_type(self, query: str) -> QueryType:
        """
        Detect the type of query to determine required elements.

        Args:
            query: The user's query string

        Returns:
            The detected QueryType
        """
        # Check for specific call ID first (highest priority)
        # Any query containing a HORIZON call ID is treated as call-specific
        # Match formats: CL5-2026, HLTH-2025, ERC-2025, etc.
        if re.search(r"HORIZON-[A-Z]{2,5}\d?-\d{4}", query, re.IGNORECASE):
            return QueryType.CALL_SPECIFIC

        # Check for partner discovery before project search (partners often found in projects)
        for pattern in self._query_type_compiled.get(QueryType.PARTNER_DISCOVERY, []):
            if pattern.search(query):
                return QueryType.PARTNER_DISCOVERY

        # Check for programme comparison before other types
        for pattern in self._query_type_compiled.get(QueryType.PROGRAMME_COMPARISON, []):
            if pattern.search(query):
                return QueryType.PROGRAMME_COMPARISON

        # Check other query types in priority order
        priority_order = [
            QueryType.CALL_SEARCH,
            QueryType.BUDGET_BENCHMARK,
            QueryType.CONSORTIUM_PATTERN,
            QueryType.STATISTICS,
            QueryType.PROJECT_SEARCH,
            QueryType.ELIGIBILITY_FAQ,
        ]

        for query_type in priority_order:
            patterns = self._query_type_compiled.get(query_type, [])
            for pattern in patterns:
                if pattern.search(query):
                    return query_type

        return QueryType.GENERAL

    def find_deflection_phrases(self, response: str) -> List[str]:
        """
        Find deflection phrases in the response.

        Args:
            response: The AI response to analyze

        Returns:
            List of deflection phrases found
        """
        found = []
        response_lower = response.lower()

        for i, pattern in enumerate(self._deflection_patterns):
            if pattern.search(response_lower):
                found.append(self.DEFLECTION_PHRASES[i])

        return found

    def find_positive_indicators(self, response: str) -> List[str]:
        """
        Find positive quality indicators in the response.

        Args:
            response: The AI response to analyze

        Returns:
            List of positive indicators found (pattern descriptions)
        """
        found = []
        indicator_names = [
            "formatted_headers",
            "euro_amounts",
            "funding_amounts",
            "call_ids",
            "action_type_icons",
            "status_icons",
            "dates",
            "action_types",
            "cluster_references",
            "urls",
        ]

        for i, pattern in enumerate(self._positive_patterns):
            if pattern.search(response):
                found.append(indicator_names[i])

        return found

    def check_required_elements(
        self, query: str, response: str, query_type: QueryType
    ) -> Tuple[List[str], List[str]]:
        """
        Check which required elements are present or missing.

        Args:
            query: The original query
            response: The AI response
            query_type: The detected query type

        Returns:
            Tuple of (present_elements, missing_elements)
        """
        requirements = self.QUERY_REQUIREMENTS.get(
            query_type, self.QUERY_REQUIREMENTS[QueryType.GENERAL]
        )

        present = []
        missing = []
        response_lower = response.lower()

        for element in requirements.required_elements:
            found = False

            # Check based on element type
            if element == "call_id" or element == "at_least_one_call_id":
                if re.search(
                    r"HORIZON-[A-Z]{2,3}\d?-\d{4}", response, re.IGNORECASE
                ):
                    found = True
            elif element == "deadline_or_timeline":
                deadline_patterns = [
                    r"deadline",
                    r"closes?\s*:?",
                    r"due\s*:?",
                    r"\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
                    r"\d{4}-\d{2}-\d{2}",
                ]
                found = any(
                    re.search(p, response, re.IGNORECASE) for p in deadline_patterns
                )
            elif element == "budget_or_funding":
                found = bool(
                    re.search(r"€\s?\d|EUR\s?\d|budget|funding", response, re.IGNORECASE)
                )
            elif element == "action_type":
                found = bool(
                    re.search(r"(RIA|IA|CSA|COFUND|ERC|MSCA|🔬|🚀|🤝)", response)
                )
            elif element == "status":
                found = bool(
                    re.search(r"(open|upcoming|closed|🟢|🟡|🔴|status)", response, re.IGNORECASE)
                )
            elif element == "call_count_or_results":
                pattern = r"found\s+\d+|(\d+)\s*(call|opportunit|result)"
                found = bool(re.search(pattern, response, re.IGNORECASE))
            elif element == "project_names_or_acronyms":
                # Look for project references (typically in bold or with acronyms)
                found = bool(
                    re.search(
                        r"\*\*[A-Z][A-Z0-9\-]+\*\*|project.{1,50}(titled|called|named)",
                        response,
                        re.IGNORECASE,
                    )
                ) or "project" in response_lower
            elif element == "programme_1_info" or element == "programme_2_info":
                # Check for programme mentions
                programmes = re.findall(
                    r"(EIC|ERC|MSCA|Horizon|RIA|IA|CSA)", response, re.IGNORECASE
                )
                found = len(programmes) >= 1
            elif element == "comparison_metrics":
                found = bool(
                    re.search(
                        r"(success rate|funding|budget|eligib|differ|advantage|disadvantage)",
                        response,
                        re.IGNORECASE,
                    )
                )
            elif element == "clear_answer":
                # Check that the response directly addresses the query
                # Not a deflection and substantial content
                found = (
                    len(response) >= 100
                    and not any(
                        p.search(response.lower()) for p in self._deflection_patterns[:5]
                    )
                )
            elif element == "relevant_rules_or_criteria":
                found = bool(
                    re.search(
                        r"(rule|regulation|criteria|requirement|condition|must|should|need to)",
                        response,
                        re.IGNORECASE,
                    )
                )
            elif element == "budget_statistics":
                found = bool(
                    re.search(
                        r"(€|EUR|average|median|typical|range|budget|funding).{0,50}\d",
                        response,
                        re.IGNORECASE,
                    )
                )
            elif element == "numerical_values":
                found = bool(re.search(r"\d+[\.,]?\d*", response))
            elif element == "partner_names_or_organizations":
                found = bool(
                    re.search(
                        r"(university|institute|company|organization|gmbh|ltd|inc|s\.?a\.?|center|centre)",
                        response,
                        re.IGNORECASE,
                    )
                )
            elif element == "experience_indicators":
                pattern = (
                    r"(experience|expertise|participated|project|funded|"
                    r"successful|track record)"
                )
                found = bool(re.search(pattern, response, re.IGNORECASE))
            elif element == "consortium_size_info":
                found = bool(
                    re.search(
                        r"\d+\s*(partner|member|organization|countr)", response, re.IGNORECASE
                    )
                )
            elif element == "composition_details":
                found = bool(
                    re.search(
                        r"(HES|REC|PRC|PUB|universit|research|industry|SME|academic|private)",
                        response,
                        re.IGNORECASE,
                    )
                )
            elif element == "numerical_data":
                found = bool(re.search(r"\d+", response))
            else:
                # Default check - just look for the element name in response
                found = element.replace("_", " ") in response_lower

            if found:
                present.append(element)
            else:
                missing.append(element)

        return present, missing

    def calculate_score(
        self,
        response: str,
        query_type: QueryType,
        deflections: List[str],
        missing_elements: List[str],
        present_elements: List[str],
        positive_indicators: List[str],
    ) -> int:
        """
        Calculate a quality score from 0-100.

        Args:
            response: The AI response
            query_type: The detected query type
            deflections: List of deflection phrases found
            missing_elements: List of missing required elements
            present_elements: List of present required elements
            positive_indicators: List of positive indicators found

        Returns:
            Score from 0 to 100
        """
        score = 100

        # Heavy penalty for deflection phrases - each deflection is a major issue
        score -= len(deflections) * 25

        # Penalty for missing required elements
        total_required = len(missing_elements) + len(present_elements)
        if total_required > 0:
            missing_ratio = len(missing_elements) / total_required
            score -= int(missing_ratio * 30)

        # Check minimum length - more severe penalty for very short responses
        requirements = self.QUERY_REQUIREMENTS.get(
            query_type, self.QUERY_REQUIREMENTS[QueryType.GENERAL]
        )
        if len(response) < requirements.min_response_length:
            length_ratio = len(response) / requirements.min_response_length
            # Exponential penalty for very short responses
            if length_ratio < 0.3:
                score -= 40
            elif length_ratio < 0.5:
                score -= 30
            else:
                score -= int((1 - length_ratio) * 25)

        # Bonus for positive indicators
        score += min(len(positive_indicators) * 3, 15)

        # Bonus for expected patterns
        for pattern in requirements.expected_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                score += 3

        # Ensure score is in valid range
        return max(0, min(100, score))

    def determine_category(
        self, score: int, deflections: List[str], response: str
    ) -> ResponseCategory:
        """
        Determine the response category based on analysis.

        Args:
            score: The calculated quality score
            deflections: List of deflection phrases found
            response: The AI response

        Returns:
            The ResponseCategory
        """
        # Check for empty response first
        if len(response.strip()) < 50:
            return ResponseCategory.EMPTY

        # Check for error indicators - but be careful not to match legitimate uses
        # like "error correction" or "error-corrected"
        error_patterns = [
            r"\berror\b(?![\-\s]correc)",  # "error" but not "error-correction" or "error corrected"
            r"\bexception\b",
            r"\bfailed\b(?!\s+to\s+find)",  # "failed" but not "failed to find" (that's deflection)
            r"service.*unavailable",
            r"system.*unavailable",
        ]
        for pattern in error_patterns:
            if re.search(pattern, response.lower()):
                return ResponseCategory.ERROR

        # Check for deflections - any deflection phrase is a problem
        # Multiple deflections or deflection with low score = definite DEFLECTION
        if len(deflections) >= 2:
            return ResponseCategory.DEFLECTION
        if len(deflections) >= 1 and score < 70:
            return ResponseCategory.DEFLECTION
        # Even a single deflection with high score is concerning - mark as PARTIAL
        if len(deflections) >= 1:
            return ResponseCategory.PARTIAL

        # Determine based on score
        if score >= 75:
            return ResponseCategory.COMPLETE
        elif score >= 40:
            return ResponseCategory.PARTIAL
        else:
            return ResponseCategory.DEFLECTION

    def generate_recommendations(
        self,
        query_type: QueryType,
        missing_elements: List[str],
        deflections: List[str],
        category: ResponseCategory,
    ) -> List[str]:
        """
        Generate actionable recommendations for improvement.

        Args:
            query_type: The detected query type
            missing_elements: List of missing required elements
            deflections: List of deflection phrases found
            category: The response category

        Returns:
            List of recommendations
        """
        recommendations = []

        if deflections:
            recommendations.append(
                f"Remove deflection phrases: {', '.join(deflections[:3])}"
            )

        if missing_elements:
            for element in missing_elements[:3]:
                readable = element.replace("_", " ")
                recommendations.append(f"Add {readable} to the response")

        if category == ResponseCategory.EMPTY:
            recommendations.append(
                "Response is too short - provide substantive information"
            )

        if category == ResponseCategory.DEFLECTION:
            recommendations.append(
                "Instead of deflecting, provide the available information "
                "or clearly state what specific data is missing"
            )

        if query_type == QueryType.CALL_SPECIFIC:
            if "deadline_or_timeline" in missing_elements:
                recommendations.append(
                    "Include the call deadline or timeline information"
                )
            if "budget_or_funding" in missing_elements:
                recommendations.append("Include budget/funding amount information")

        return recommendations

    def analyze(
        self, query: str, response: str, expected_elements: Optional[List[str]] = None
    ) -> QualityAnalysis:
        """
        Perform comprehensive quality analysis on a response.

        Args:
            query: The original user query
            response: The AI response to analyze
            expected_elements: Optional list of additional expected elements

        Returns:
            QualityAnalysis with detailed breakdown
        """
        if not response:
            return QualityAnalysis(
                score=0,
                category=ResponseCategory.EMPTY,
                confidence=1.0,
                query_type=QueryType.GENERAL,
                missing_elements=["any_response"],
                deflection_phrases_found=[],
                positive_indicators=[],
                recommendations=["Response is empty - generate actual content"],
                metadata={"response_length": 0},
            )

        # Detect query type
        query_type = self.detect_query_type(query)

        # Find deflections
        deflections = self.find_deflection_phrases(response)

        # Find positive indicators
        positive_indicators = self.find_positive_indicators(response)

        # Check required elements
        present_elements, missing_elements = self.check_required_elements(
            query, response, query_type
        )

        # Add custom expected elements if provided
        if expected_elements:
            for element in expected_elements:
                element_lower = element.lower()
                if element_lower in response.lower():
                    if element not in present_elements:
                        present_elements.append(element)
                else:
                    if element not in missing_elements:
                        missing_elements.append(element)

        # Calculate score
        score = self.calculate_score(
            response,
            query_type,
            deflections,
            missing_elements,
            present_elements,
            positive_indicators,
        )

        # Determine category
        category = self.determine_category(score, deflections, response)

        # Generate recommendations
        recommendations = self.generate_recommendations(
            query_type, missing_elements, deflections, category
        )

        # Calculate confidence based on detection clarity
        confidence = 0.9
        if len(deflections) > 0 and len(positive_indicators) > 0:
            # Mixed signals reduce confidence
            confidence = 0.7
        if score >= 40 and score <= 60:
            # Edge cases reduce confidence
            confidence -= 0.1

        return QualityAnalysis(
            score=score,
            category=category,
            confidence=confidence,
            query_type=query_type,
            missing_elements=missing_elements,
            deflection_phrases_found=deflections,
            positive_indicators=positive_indicators,
            recommendations=recommendations,
            metadata={
                "response_length": len(response),
                "present_elements": present_elements,
                "total_required": len(missing_elements) + len(present_elements),
            },
        )

    def is_acceptable(
        self, analysis: QualityAnalysis, min_score: int = 70
    ) -> bool:
        """
        Check if a response meets minimum quality standards.

        Args:
            analysis: The QualityAnalysis result
            min_score: Minimum acceptable score (default 70)

        Returns:
            True if the response is acceptable, False otherwise
        """
        # Never accept responses with deflection category
        unacceptable = [
            ResponseCategory.DEFLECTION,
            ResponseCategory.EMPTY,
            ResponseCategory.ERROR,
        ]
        if analysis.category in unacceptable:
            return False

        # Also reject if deflection phrases were found (even if categorized as PARTIAL/COMPLETE)
        if len(analysis.deflection_phrases_found) > 0:
            return False

        # Check score threshold
        return analysis.score >= min_score

    def get_failure_reason(self, analysis: QualityAnalysis) -> str:
        """
        Get a human-readable failure reason from the analysis.

        Args:
            analysis: The QualityAnalysis result

        Returns:
            A string describing why the response failed quality checks
        """
        reasons = []

        if analysis.category == ResponseCategory.DEFLECTION:
            phrases = ", ".join(analysis.deflection_phrases_found[:3])
            reasons.append(f"DEFLECTION: Response contains deflection phrases: {phrases}")
        elif analysis.category == ResponseCategory.EMPTY:
            reasons.append("EMPTY: Response is too short or empty")
        elif analysis.category == ResponseCategory.ERROR:
            reasons.append("ERROR: Response indicates an error occurred")

        if analysis.missing_elements:
            reasons.append(
                f"MISSING ELEMENTS: {', '.join(analysis.missing_elements[:5])}"
            )

        if analysis.score < 70:
            reasons.append(f"LOW SCORE: {analysis.score}/100")

        return " | ".join(reasons) if reasons else "Unknown failure reason"
