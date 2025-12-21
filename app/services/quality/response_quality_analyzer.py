"""
Response Quality Analyzer

Analyzes AI responses for quality, detecting deflections and ensuring
content requirements are met. Critical for ensuring AI responses are
actually helpful rather than generic deflections.

Author: MAP-IT Development Team
Created: December 2025
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

    COMPLETE = "complete"  # Response fully addresses the query with all required elements
    PARTIAL = "partial"  # Response addresses some but not all requirements
    DEFLECTION = "deflection"  # Response deflects rather than answering
    EMPTY = "empty"  # Response is too short or lacks substance
    ERROR = "error"  # Response indicates an error occurred


class QueryType(str, Enum):
    """Types of queries for content validation."""

    CALL_INFORMATION = "call_information"  # Questions about specific funding calls
    PROJECT_SEARCH = "project_search"  # Searching for projects
    PROGRAMME_COMPARISON = "programme_comparison"  # Comparing programmes (EIC vs ERC)
    ELIGIBILITY_FAQ = "eligibility_faq"  # Questions about eligibility and rules
    BUDGET_BENCHMARK = "budget_benchmark"  # Budget-related queries
    PARTNER_DISCOVERY = "partner_discovery"  # Finding partners
    CONSORTIUM_PATTERN = "consortium_pattern"  # Consortium composition queries
    STATISTICS = "statistics"  # Statistics queries
    GENERAL = "general"  # General queries


@dataclass
class ContentRequirement:
    """A required element in a response."""

    name: str
    description: str
    patterns: list[str]  # Regex patterns to match
    required: bool = True
    min_occurrences: int = 1


@dataclass
class QualityAnalysis:
    """Result of quality analysis on an AI response."""

    score: int  # 0-100 quality score
    category: ResponseCategory
    confidence: float  # 0.0-1.0 confidence in the analysis
    query_type: QueryType
    missing_elements: list[str]  # List of required elements that are missing
    deflection_phrases_found: list[str]  # Deflection phrases detected
    recommendations: list[str]  # Suggestions for improvement
    content_elements_found: dict[str, int]  # Elements found with counts
    response_length: int
    analysis_time_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def is_acceptable(self, min_score: int = 70) -> bool:
        """Check if the response meets minimum quality threshold."""
        return self.score >= min_score and self.category not in [
            ResponseCategory.DEFLECTION,
            ResponseCategory.EMPTY,
        ]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "score": self.score,
            "category": self.category.value,
            "confidence": self.confidence,
            "query_type": self.query_type.value,
            "missing_elements": self.missing_elements,
            "deflection_phrases_found": self.deflection_phrases_found,
            "recommendations": self.recommendations,
            "content_elements_found": self.content_elements_found,
            "response_length": self.response_length,
            "analysis_time_ms": self.analysis_time_ms,
            "timestamp": self.timestamp,
            "is_acceptable": self.is_acceptable(),
        }


# Comprehensive list of deflection phrases that indicate the AI is not answering
DEFLECTION_PHRASES: list[str] = [
    # Direct admission of failure
    "could not find",
    "couldn't find",
    "no information available",
    "no information found",
    "no results found",
    "no matching results",
    "no data available",
    "unable to retrieve",
    "unable to find",
    "unable to locate",
    # Uncertainty phrases
    "i'm not sure",
    "i am not sure",
    "i'm uncertain",
    "i am uncertain",
    "i don't have",
    "i do not have",
    "i cannot determine",
    "i can't determine",
    # Redirection phrases
    "please try a more specific",
    "please try again",
    "try again later",
    "try a different",
    "try searching for",
    "please refine your",
    "could you be more specific",
    "could you clarify",
    # Partial failure indicators
    "found some information but could not extract",
    "found some information but couldn't extract",
    "found results but could not",
    "partial results only",
    "limited information available",
    # Technical failures
    "an error occurred",
    "error processing",
    "failed to process",
    "service unavailable",
    "timeout occurred",
    "request failed",
    # Generic non-answers
    "i apologize, but",
    "unfortunately, i",
    "regrettably, i",
    "i'm sorry, but i cannot",
    "i am sorry, but i cannot",
    # Tool failures
    "tool returned no results",
    "search returned empty",
    "no calls found",
    "no projects found",
    "no partners found",
    "database returned no",
]

# Patterns that indicate a substantive response
SUBSTANTIVE_PATTERNS: list[str] = [
    r"€\s*[\d,\.]+\s*(million|billion|k)?",  # Budget amounts
    r"\d{4}",  # Years
    r"HORIZON-[A-Z0-9-]+",  # Call identifiers
    r"(RIA|IA|CSA|ERC|MSCA|EIC)",  # Action types
    r"\d+%",  # Percentages
    r"deadline[:\s]",  # Deadline information
    r"budget[:\s]",  # Budget information
    r"eligible|eligibility",  # Eligibility information
]


class ResponseQualityAnalyzer:
    """
    Analyzes AI responses for quality, detecting deflections and
    ensuring content requirements are met.

    This is a critical component for ensuring that AI responses are
    actually helpful rather than generic deflections or non-answers.
    """

    # Minimum response lengths by query type
    MIN_RESPONSE_LENGTHS: dict[QueryType, int] = {
        QueryType.CALL_INFORMATION: 200,
        QueryType.PROJECT_SEARCH: 150,
        QueryType.PROGRAMME_COMPARISON: 300,
        QueryType.ELIGIBILITY_FAQ: 150,
        QueryType.BUDGET_BENCHMARK: 200,
        QueryType.PARTNER_DISCOVERY: 150,
        QueryType.CONSORTIUM_PATTERN: 200,
        QueryType.STATISTICS: 100,
        QueryType.GENERAL: 100,
    }

    # Content requirements by query type
    CONTENT_REQUIREMENTS: dict[QueryType, list[ContentRequirement]] = {
        QueryType.CALL_INFORMATION: [
            ContentRequirement(
                name="call_identifier",
                description="Call identifier or topic code",
                patterns=[r"HORIZON-[A-Z0-9-]+", r"topic\s*:?\s*[A-Z0-9-]+"],
                required=True,
            ),
            ContentRequirement(
                name="deadline",
                description="Deadline or timeline information",
                patterns=[
                    r"deadline[:\s]",
                    r"\d{1,2}[\./]\d{1,2}[\./]\d{4}",
                    r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}",
                    r"closes?\s+(on|in)",
                ],
                required=True,
            ),
            ContentRequirement(
                name="budget",
                description="Budget range or funding amount",
                patterns=[
                    r"€\s*[\d,\.]+",
                    r"budget[:\s]",
                    r"[\d,\.]+\s*(million|billion)",
                    r"EUR\s*[\d,\.]+",
                ],
                required=True,
            ),
            ContentRequirement(
                name="action_type",
                description="Action type (RIA, IA, CSA, etc.)",
                patterns=[
                    r"\b(RIA|IA|CSA|COFUND|ERC|MSCA|EIC)\b",
                    r"Research and Innovation Action",
                    r"Innovation Action",
                    r"Coordination and Support Action",
                ],
                required=True,
            ),
            ContentRequirement(
                name="status",
                description="Call status (Open, Upcoming, Closed)",
                patterns=[
                    r"\b(open|upcoming|closed|forthcoming|planned)\b",
                    r"status[:\s]",
                    r"currently (open|accepting)",
                ],
                required=False,
            ),
        ],
        QueryType.PROGRAMME_COMPARISON: [
            ContentRequirement(
                name="first_programme",
                description="First programme mentioned",
                patterns=[r"\b(EIC|ERC|RIA|IA|CSA|MSCA|Horizon)\b"],
                required=True,
                min_occurrences=2,
            ),
            ContentRequirement(
                name="comparison_words",
                description="Comparative language",
                patterns=[
                    r"\b(compared to|versus|vs\.?|while|whereas)\b",
                    r"\b(in contrast|differ|different|higher|lower)\b",
                ],
                required=True,
            ),
            ContentRequirement(
                name="metrics",
                description="Quantitative metrics",
                patterns=[r"\d+%", r"€[\d,\.]+", r"\d+\s*(projects|proposals|calls)"],
                required=True,
            ),
        ],
        QueryType.ELIGIBILITY_FAQ: [
            ContentRequirement(
                name="eligibility_info",
                description="Eligibility criteria",
                patterns=[
                    r"eligible|eligibility",
                    r"can participate",
                    r"must (be|have)",
                    r"requirement",
                ],
                required=True,
            ),
            ContentRequirement(
                name="entity_types",
                description="Types of eligible entities",
                patterns=[
                    r"\b(SME|university|research|organization|company|institution|countries?)\b"
                ],
                required=True,
            ),
        ],
        QueryType.BUDGET_BENCHMARK: [
            ContentRequirement(
                name="budget_figures",
                description="Budget amounts",
                patterns=[
                    r"€\s*[\d,\.]+",
                    r"[\d,\.]+\s*(million|billion)",
                    r"budget\s*:?\s*[\d,\.]+",
                ],
                required=True,
            ),
            ContentRequirement(
                name="statistics",
                description="Statistical measures",
                patterns=[
                    r"average|median|typical|range",
                    r"\d+%",
                    r"min|max|minimum|maximum",
                ],
                required=True,
            ),
        ],
        QueryType.PARTNER_DISCOVERY: [
            ContentRequirement(
                name="organization_names",
                description="Organization or partner names",
                patterns=[
                    r"[A-Z][a-z]+\s+(University|Institute|Centre|Center|GmbH|Ltd|Inc|AG)",
                    r"partners?\s*:?\s*\d+",
                ],
                required=True,
            ),
            ContentRequirement(
                name="expertise_area",
                description="Area of expertise",
                patterns=[
                    r"experience in|expertise in|specializ|focus on",
                    r"projects? in",
                ],
                required=True,
            ),
        ],
        QueryType.PROJECT_SEARCH: [
            ContentRequirement(
                name="project_info",
                description="Project information",
                patterns=[
                    r"project[:\s]",
                    r"funded (by|under)",
                    r"€[\d,\.]+",
                    r"consortium",
                ],
                required=True,
            ),
        ],
        QueryType.CONSORTIUM_PATTERN: [
            ContentRequirement(
                name="consortium_size",
                description="Consortium size information",
                patterns=[
                    r"\d+\s*partners?",
                    r"consortium (of|with)",
                    r"average\s*(partners?|size)",
                ],
                required=True,
            ),
            ContentRequirement(
                name="org_types",
                description="Organization type distribution",
                patterns=[
                    r"\b(HES|REC|PRC|PUB|OTH|university|research|industry|SME)\b",
                ],
                required=True,
            ),
        ],
        QueryType.STATISTICS: [
            ContentRequirement(
                name="numbers",
                description="Statistical numbers",
                patterns=[r"\d+", r"\d+%", r"€[\d,\.]+"],
                required=True,
            ),
        ],
        QueryType.GENERAL: [
            ContentRequirement(
                name="substantive_content",
                description="Substantive content",
                patterns=[r"\w{10,}"],  # At least some longer words
                required=True,
            ),
        ],
    }

    def __init__(self):
        """Initialize the response quality analyzer."""
        self.deflection_patterns = [
            re.compile(phrase, re.IGNORECASE) for phrase in DEFLECTION_PHRASES
        ]
        self.substantive_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in SUBSTANTIVE_PATTERNS
        ]

    def analyze(
        self,
        query: str,
        response: str,
        query_type: QueryType | None = None,
        expected_elements: list[str] | None = None,
        tools_used: list[str] | None = None,
        tool_results: dict[str, Any] | None = None,
    ) -> QualityAnalysis:
        """
        Analyze an AI response for quality.

        Args:
            query: The user's query
            response: The AI's response
            query_type: Type of query for content requirements (auto-detected if None)
            expected_elements: Optional list of expected content elements
            tools_used: List of tools that were used to generate the response
            tool_results: Raw results from tools (for validation)

        Returns:
            QualityAnalysis with score, category, and recommendations
        """
        start_time = datetime.now(UTC)

        # Auto-detect query type if not provided
        if query_type is None:
            query_type = self._detect_query_type(query)

        # Initialize analysis components
        deflections_found = self._detect_deflections(response)
        missing_elements: list[str] = []
        content_elements_found: dict[str, int] = {}
        recommendations: list[str] = []

        # Check response length
        response_length = len(response.strip())
        min_length = self.MIN_RESPONSE_LENGTHS.get(query_type, 100)

        # Get content requirements
        requirements = self.CONTENT_REQUIREMENTS.get(query_type, [])

        # Check each requirement
        for req in requirements:
            count = self._count_pattern_matches(response, req.patterns)
            content_elements_found[req.name] = count

            if req.required and count < req.min_occurrences:
                missing_elements.append(req.name)

        # Add expected elements if provided
        if expected_elements:
            for element in expected_elements:
                if element.lower() not in response.lower():
                    if element not in missing_elements:
                        missing_elements.append(element)

        # Validate tool results if provided
        if tool_results:
            tool_validation = self._validate_tool_results(tool_results, response)
            if not tool_validation["valid"]:
                recommendations.extend(tool_validation["issues"])

        # Calculate score and category
        score, category, confidence = self._calculate_score(
            response_length=response_length,
            min_length=min_length,
            deflections_found=deflections_found,
            missing_elements=missing_elements,
            content_elements_found=content_elements_found,
            requirements=requirements,
            response=response,
        )

        # Generate recommendations
        recommendations.extend(
            self._generate_recommendations(
                category=category,
                missing_elements=missing_elements,
                deflections_found=deflections_found,
                response_length=response_length,
                min_length=min_length,
            )
        )

        # Calculate analysis time
        end_time = datetime.now(UTC)
        analysis_time_ms = (end_time - start_time).total_seconds() * 1000

        return QualityAnalysis(
            score=score,
            category=category,
            confidence=confidence,
            query_type=query_type,
            missing_elements=missing_elements,
            deflection_phrases_found=deflections_found,
            recommendations=recommendations,
            content_elements_found=content_elements_found,
            response_length=response_length,
            analysis_time_ms=analysis_time_ms,
        )

    def _detect_query_type(self, query: str) -> QueryType:
        """Auto-detect the query type from the query text."""
        query_lower = query.lower()

        # Call information queries
        if re.search(r"HORIZON-[A-Z0-9-]+", query, re.IGNORECASE):
            return QueryType.CALL_INFORMATION
        if any(
            phrase in query_lower
            for phrase in ["tell me about call", "about the call", "call details"]
        ):
            return QueryType.CALL_INFORMATION
        if any(phrase in query_lower for phrase in ["funding call", "open call", "upcoming call"]):
            return QueryType.CALL_INFORMATION

        # Comparison queries
        if any(
            phrase in query_lower for phrase in ["compare", "vs", "versus", "difference between"]
        ):
            return QueryType.PROGRAMME_COMPARISON

        # Eligibility queries
        if any(
            phrase in query_lower
            for phrase in [
                "eligible",
                "eligibility",
                "can i apply",
                "can we apply",
                "can sme",
                "can a sme",
                "can an sme",
                "who can apply",
                "requirements for",
            ]
        ):
            return QueryType.ELIGIBILITY_FAQ

        # Budget queries
        if any(
            phrase in query_lower
            for phrase in [
                "budget",
                "funding amount",
                "typical budget",
                "benchmark",
                "how much funding",
                "funding request",
            ]
        ):
            return QueryType.BUDGET_BENCHMARK

        # Partner queries
        if any(
            phrase in query_lower
            for phrase in [
                "partner",
                "find organizations",
                "experienced in",
                "find german",
                "find french",
                "find italian",
                "find spanish",
                "smes with",
            ]
        ):
            return QueryType.PARTNER_DISCOVERY

        # Project queries
        if any(
            phrase in query_lower
            for phrase in [
                "find projects",
                "search projects",
                "projects about",
                "projects in",
                "search for",
            ]
        ):
            return QueryType.PROJECT_SEARCH

        # Consortium queries
        if any(phrase in query_lower for phrase in ["consortium", "consortium size", "team"]):
            return QueryType.CONSORTIUM_PATTERN

        # Statistics queries
        if any(phrase in query_lower for phrase in ["statistics", "success rate", "how many"]):
            return QueryType.STATISTICS

        return QueryType.GENERAL

    def _detect_deflections(self, response: str) -> list[str]:
        """Detect deflection phrases in the response."""
        deflections_found = []
        response_lower = response.lower()

        for phrase in DEFLECTION_PHRASES:
            if phrase.lower() in response_lower:
                deflections_found.append(phrase)

        return deflections_found

    def _count_pattern_matches(self, text: str, patterns: list[str]) -> int:
        """Count how many times patterns match in the text."""
        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)
        return count

    def _validate_tool_results(self, tool_results: dict[str, Any], response: str) -> dict[str, Any]:
        """Validate that tool results are reflected in the response."""
        issues = []
        valid = True

        for tool_name, result in tool_results.items():
            if isinstance(result, dict):
                # Check for error in tool result
                if result.get("error"):
                    issues.append(f"Tool '{tool_name}' returned an error")
                    valid = False
                    continue

                # Check if key data from tool is in response
                if "calls" in result:
                    calls = result.get("calls", [])
                    if calls and "no calls found" in response.lower():
                        msg = f"Tool '{tool_name}' returned {len(calls)} calls "
                        msg += "but response says none found"
                        issues.append(msg)
                        valid = False

                if "projects" in result:
                    projects = result.get("projects", [])
                    if projects and "no projects found" in response.lower():
                        msg = f"Tool '{tool_name}' returned {len(projects)} "
                        msg += "projects but response says none found"
                        issues.append(msg)
                        valid = False

        return {"valid": valid, "issues": issues}

    def _calculate_score(
        self,
        response_length: int,
        min_length: int,
        deflections_found: list[str],
        missing_elements: list[str],
        content_elements_found: dict[str, int],
        requirements: list[ContentRequirement],
        response: str = "",
    ) -> tuple[int, ResponseCategory, float]:
        """Calculate quality score, category, and confidence."""
        score = 100
        confidence = 0.9

        # Check for critical deflection phrases (very heavy penalty)
        critical_deflections = [
            "could not find",
            "couldn't find",
            "no information available",
            "no results found",
            "unable to retrieve",
            "unable to find",
            "i'm not sure",
            "i am not sure",
        ]
        response_lower = response.lower()
        has_critical_deflection = any(phrase in response_lower for phrase in critical_deflections)

        # Deduct for deflections (critical)
        deflection_count = len(deflections_found)
        if has_critical_deflection:
            score -= 50  # Major penalty for critical deflections
            confidence = 0.95
        elif deflection_count > 0:
            # Heavy penalty for deflections
            score -= min(40, deflection_count * 20)
            confidence = 0.95

        # Very short or empty responses
        if response_length == 0:
            score = 0
        elif response_length < 50:
            score = min(score, 15)  # Cap at 15 for very short responses

        # Deduct for missing elements
        required_count = sum(1 for r in requirements if r.required)
        if required_count > 0:
            missing_required = len(
                [m for m in missing_elements if m in [r.name for r in requirements if r.required]]
            )
            score -= int((missing_required / required_count) * 30)

        # Deduct for short response (less than minimum)
        if response_length > 0 and response_length < min_length:
            length_ratio = response_length / min_length
            score -= int((1 - length_ratio) * 25)

        # Bonus for substantive content
        total_content_found = sum(content_elements_found.values())
        if total_content_found > len(requirements):
            score = min(100, score + 5)  # Small bonus for rich content

        # Determine category (check empty first, then deflection)
        score = max(0, min(100, int(score)))

        if response_length < 50:
            category = ResponseCategory.EMPTY
        elif deflection_count >= 2 or has_critical_deflection:
            category = ResponseCategory.DEFLECTION
        elif deflection_count > 0 or len(missing_elements) > required_count * 0.5:
            category = ResponseCategory.PARTIAL
        elif score >= 70:
            category = ResponseCategory.COMPLETE
        else:
            category = ResponseCategory.PARTIAL

        return score, category, confidence

    def _generate_recommendations(
        self,
        category: ResponseCategory,
        missing_elements: list[str],
        deflections_found: list[str],
        response_length: int,
        min_length: int,
    ) -> list[str]:
        """Generate improvement recommendations."""
        recommendations = []

        if category == ResponseCategory.DEFLECTION:
            msg = (
                "Response contains deflection phrases indicating the query "
                "wasn't properly answered. "
                "Investigate why tools failed or data wasn't found."
            )
            recommendations.append(msg)

        if category == ResponseCategory.EMPTY:
            recommendations.append(
                f"Response is too short ({response_length} chars, minimum {min_length}). "
                "Ensure comprehensive information is provided."
            )

        if missing_elements:
            elements_str = ", ".join(missing_elements[:5])
            recommendations.append(
                f"Missing required content elements: {elements_str}. "
                "Add this information to the response."
            )

        if deflections_found:
            phrases_str = ", ".join([f'"{p}"' for p in deflections_found[:3]])
            recommendations.append(
                f"Avoid deflection phrases like {phrases_str}. "
                "If data truly isn't available, explain why specifically."
            )

        return recommendations

    def is_deflection(self, response: str) -> bool:
        """
        Quick check if a response is a deflection.

        A response is considered a deflection if it:
        - Contains 2+ deflection phrases, OR
        - Contains 1 deflection phrase and is very short (< 100 chars), OR
        - Contains 1 critical deflection phrase (e.g., "could not find", "no information")

        Args:
            response: The AI's response

        Returns:
            True if the response appears to be a deflection
        """
        deflections = self._detect_deflections(response)

        # 2+ deflections is definitely a deflection
        if len(deflections) >= 2:
            return True

        # 1 deflection + short response is a deflection
        if len(deflections) == 1 and len(response.strip()) < 150:
            return True

        # Critical deflection phrases always count as deflection
        critical_phrases = [
            "could not find",
            "couldn't find",
            "no information available",
            "no information found",
            "unable to retrieve",
            "unable to find",
            "no results found",
            "i'm not sure",
            "i am not sure",
        ]
        response_lower = response.lower()
        for phrase in critical_phrases:
            if phrase in response_lower:
                return True

        return False

    def get_required_elements(self, query_type: QueryType) -> list[str]:
        """
        Get list of required elements for a query type.

        Args:
            query_type: The type of query

        Returns:
            List of required element names
        """
        requirements = self.CONTENT_REQUIREMENTS.get(query_type, [])
        return [r.name for r in requirements if r.required]

    def batch_analyze(self, queries_and_responses: list[tuple[str, str]]) -> list[QualityAnalysis]:
        """
        Analyze multiple query-response pairs.

        Args:
            queries_and_responses: List of (query, response) tuples

        Returns:
            List of QualityAnalysis objects
        """
        return [self.analyze(q, r) for q, r in queries_and_responses]

    def get_summary_stats(self, analyses: list[QualityAnalysis]) -> dict[str, Any]:
        """
        Get summary statistics from multiple analyses.

        Args:
            analyses: List of QualityAnalysis objects

        Returns:
            Dictionary with summary statistics
        """
        if not analyses:
            return {"error": "No analyses provided"}

        scores = [a.score for a in analyses]
        categories = [a.category for a in analyses]

        return {
            "count": len(analyses),
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "category_distribution": {cat.value: categories.count(cat) for cat in ResponseCategory},
            "deflection_rate": categories.count(ResponseCategory.DEFLECTION) / len(analyses),
            "complete_rate": categories.count(ResponseCategory.COMPLETE) / len(analyses),
            "acceptable_rate": sum(1 for a in analyses if a.is_acceptable()) / len(analyses),
        }
