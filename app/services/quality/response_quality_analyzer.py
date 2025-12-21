"""
Response Quality Analyzer for AI Response Validation.

This module provides comprehensive quality analysis for AI responses,
including deflection detection, content validation, and quality scoring.

The analyzer is designed to catch "lazy" AI responses that:
- Deflect with phrases like "I could not find" or "no information available"
- Provide partial or incomplete information
- Fail to include required elements for specific query types

Usage:
    analyzer = ResponseQualityAnalyzer()
    analysis = analyzer.analyze(query="Tell me about HORIZON-CL5-2026-D3-01", response="...")

    if analysis.category == ResponseCategory.DEFLECTION:
        # Response is a deflection, needs investigation
        pass

    if analysis.score < 70:
        # Response quality is below threshold
        pass
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ResponseCategory(str, Enum):
    """Categories for AI response quality classification."""

    COMPLETE = "complete"      # Response fully addresses the query with all required elements
    PARTIAL = "partial"        # Response addresses some but not all aspects of the query
    DEFLECTION = "deflection"  # Response deflects, claims inability to find/provide information
    EMPTY = "empty"            # Response is essentially empty or has no meaningful content
    ERROR = "error"            # Response indicates an error occurred


class QueryType(str, Enum):
    """Types of queries for content requirement matching."""

    CALL_INFO = "call_info"              # Questions about specific funding calls
    PROGRAMME_COMPARISON = "programme_comparison"  # Comparing programmes/schemes
    ELIGIBILITY_FAQ = "eligibility_faq"  # Questions about eligibility/rules
    BUDGET_BENCHMARK = "budget_benchmark"  # Budget-related queries
    PARTNER_DISCOVERY = "partner_discovery"  # Finding partners
    PROJECT_SEARCH = "project_search"    # Searching for projects
    CONSORTIUM_PATTERN = "consortium_pattern"  # Consortium composition questions
    STATISTICS = "statistics"            # Statistical queries
    GENERAL = "general"                  # General queries


@dataclass
class ContentRequirement:
    """Defines required elements for a specific query type."""

    query_type: QueryType
    required_elements: List[str]
    min_elements_present: int
    min_response_length: int
    patterns: List[str] = field(default_factory=list)  # Regex patterns to detect query type


@dataclass
class QualityAnalysis:
    """Result of quality analysis for an AI response."""

    score: int  # 0-100 quality score
    category: ResponseCategory
    confidence: float  # 0.0-1.0 confidence in the analysis
    query_type: QueryType
    missing_elements: List[str]
    deflection_phrases_found: List[str]
    recommendations: List[str]
    elements_found: List[str]
    response_length: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary for serialization."""
        return {
            "score": self.score,
            "category": self.category.value,
            "confidence": self.confidence,
            "query_type": self.query_type.value,
            "missing_elements": self.missing_elements,
            "deflection_phrases_found": self.deflection_phrases_found,
            "recommendations": self.recommendations,
            "elements_found": self.elements_found,
            "response_length": self.response_length,
            "timestamp": self.timestamp,
        }


class ResponseQualityAnalyzer:
    """
    Analyzes AI response quality to detect deflections, incomplete responses,
    and validate content requirements.

    This analyzer is designed to catch "lazy" AI responses that fail to
    provide substantive information even when it should be available.

    Key features:
    - Deflection phrase detection (e.g., "could not find", "no information")
    - Query type inference and content requirement validation
    - Multi-dimensional scoring based on completeness, relevance, and specificity
    - Actionable recommendations for improvement

    Attributes:
        DEFLECTION_PHRASES: List of phrases that indicate deflection
        CONTENT_REQUIREMENTS: Dict mapping query types to required elements
    """

    # Phrases that indicate the AI is deflecting or avoiding answering
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
        "cannot provide",
        "don't have access to",
        "no specific information",
        "unable to find",
        "couldn't locate",
        "no data available",
        "information is not available",
        "i cannot answer",
        "i'm unable to",
        "i am unable to",
        "without more information",
        "need more context",
        "please provide more details",
        "this is outside my knowledge",
        "i don't know",
        "i do not know",
        "not in my training data",
        "my knowledge cutoff",
        "i lack the information",
        "insufficient data",
        "data is unavailable",
        "no matching results",
        "search returned no results",
        "query returned empty",
    ]

    # Content requirements by query type
    CONTENT_REQUIREMENTS: Dict[QueryType, ContentRequirement] = {
        QueryType.CALL_INFO: ContentRequirement(
            query_type=QueryType.CALL_INFO,
            required_elements=["call_id", "deadline", "budget", "type", "status", "scope"],
            min_elements_present=4,
            min_response_length=200,
            patterns=[
                r"HORIZON-[A-Z0-9-]+",
                r"tell me about .*(call|topic)",
                r"what is .*(call|topic)",
                r"details (of|about|for) .*(call|topic)",
            ],
        ),
        QueryType.PROGRAMME_COMPARISON: ContentRequirement(
            query_type=QueryType.PROGRAMME_COMPARISON,
            required_elements=["programme_1", "programme_2", "comparison_aspect", "recommendation"],
            min_elements_present=3,
            min_response_length=300,
            patterns=[
                r"compare .* (with|vs|versus|and|to)",
                r"difference between .* and",
                r"(eic|erc|ria|ia|msca|csa) vs",
                r"which (is better|should i choose)",
            ],
        ),
        QueryType.ELIGIBILITY_FAQ: ContentRequirement(
            query_type=QueryType.ELIGIBILITY_FAQ,
            required_elements=["eligibility_criteria", "requirements", "answer"],
            min_elements_present=2,
            min_response_length=150,
            patterns=[
                r"(can|am i|are we|is .* eligible)",
                r"eligibility (for|requirements|criteria)",
                r"who (can|is eligible|may) (apply|participate)",
                r"(requirements|rules) for",
                r"who is eligible",
            ],
        ),
        QueryType.BUDGET_BENCHMARK: ContentRequirement(
            query_type=QueryType.BUDGET_BENCHMARK,
            required_elements=["budget_range", "average", "consortium_size", "recommendation"],
            min_elements_present=3,
            min_response_length=200,
            patterns=[
                r"(typical|average|benchmark) budget",
                r"how much (funding|budget|money)",
                r"budget for .*(ria|ia|csa|horizon)",
                r"funding (range|amount|level)",
                r"average funding",
            ],
        ),
        QueryType.PARTNER_DISCOVERY: ContentRequirement(
            query_type=QueryType.PARTNER_DISCOVERY,
            required_elements=["partner_names", "countries", "experience", "relevance"],
            min_elements_present=2,
            min_response_length=200,
            patterns=[
                r"find (partners|organizations|institutions)",
                r"(experienced|suitable) partners",
                r"who (has experience|works on|specializes)",
                r"partners (in|from|with)",
                r"organizations (working on|with experience)",
                r"(find|search) .*(sme|university|institute|partner)",
            ],
        ),
        QueryType.PROJECT_SEARCH: ContentRequirement(
            query_type=QueryType.PROJECT_SEARCH,
            required_elements=["project_names", "descriptions", "funding", "relevance"],
            min_elements_present=2,
            min_response_length=150,
            patterns=[
                r"find .*projects",
                r"search (for|funded) projects",
                r"projects (about|on|related to)",
                r"(funded|completed|ongoing) projects",
            ],
        ),
        QueryType.CONSORTIUM_PATTERN: ContentRequirement(
            query_type=QueryType.CONSORTIUM_PATTERN,
            required_elements=["consortium_size", "partner_types", "countries", "distribution"],
            min_elements_present=3,
            min_response_length=200,
            patterns=[
                r"(typical|average|ideal) consortium",
                r"consortium (size|composition|pattern)",
                r"how many partners",
                r"(partner|organization) mix",
            ],
        ),
        QueryType.STATISTICS: ContentRequirement(
            query_type=QueryType.STATISTICS,
            required_elements=["statistics", "numbers", "source", "context"],
            min_elements_present=2,
            min_response_length=150,
            patterns=[
                r"(success|acceptance) rate",
                r"statistics (for|about|on)",
                r"how many .*(funded|accepted|submitted)",
                r"(average|total|median) (funding|budget|participation)",
            ],
        ),
        QueryType.GENERAL: ContentRequirement(
            query_type=QueryType.GENERAL,
            required_elements=["answer", "context"],
            min_elements_present=1,
            min_response_length=100,
            patterns=[],  # Fallback for unmatched queries
        ),
    }

    def __init__(self, custom_deflection_phrases: Optional[List[str]] = None) -> None:
        """
        Initialize the ResponseQualityAnalyzer.

        Args:
            custom_deflection_phrases: Additional deflection phrases to detect.
        """
        self.deflection_phrases = list(self.DEFLECTION_PHRASES)
        if custom_deflection_phrases:
            self.deflection_phrases.extend(custom_deflection_phrases)

        # Pre-compile deflection patterns for efficiency
        self._deflection_patterns = [
            re.compile(re.escape(phrase), re.IGNORECASE)
            for phrase in self.deflection_phrases
        ]

        # Pre-compile query type patterns
        self._query_type_patterns: Dict[QueryType, List[re.Pattern]] = {}
        for query_type, req in self.CONTENT_REQUIREMENTS.items():
            self._query_type_patterns[query_type] = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in req.patterns
            ]

        logger.info("ResponseQualityAnalyzer initialized with %d deflection phrases", len(self.deflection_phrases))

    def analyze(
        self,
        query: str,
        response: str,
        tool_results: Optional[Dict[str, Any]] = None,
        expected_query_type: Optional[QueryType] = None,
    ) -> QualityAnalysis:
        """
        Analyze the quality of an AI response.

        Args:
            query: The user's original query.
            response: The AI's response text.
            tool_results: Optional dict of tool results used in generating the response.
            expected_query_type: Optional override for query type detection.

        Returns:
            QualityAnalysis containing score, category, and recommendations.
        """
        # Normalize inputs
        query_lower = query.lower().strip()
        response_lower = response.lower().strip()
        response_length = len(response.strip())

        # Step 1: Check for empty response
        if response_length < 20:
            return QualityAnalysis(
                score=0,
                category=ResponseCategory.EMPTY,
                confidence=1.0,
                query_type=QueryType.GENERAL,
                missing_elements=["meaningful_content"],
                deflection_phrases_found=[],
                recommendations=["Response is too short. Provide substantive information."],
                elements_found=[],
                response_length=response_length,
            )

        # Step 2: Detect deflection phrases
        deflection_phrases_found = self._detect_deflection_phrases(response_lower)

        # Step 3: Infer query type
        query_type = expected_query_type or self._infer_query_type(query_lower)
        requirements = self.CONTENT_REQUIREMENTS.get(query_type, self.CONTENT_REQUIREMENTS[QueryType.GENERAL])

        # Step 4: Check content requirements
        elements_found, missing_elements = self._check_content_requirements(
            query_lower, response_lower, requirements
        )

        # Step 5: Validate tool results if provided
        tool_quality_score = self._validate_tool_results(tool_results) if tool_results else 100

        # Step 6: Calculate score
        score, category, confidence = self._calculate_score(
            response_length=response_length,
            deflection_phrases_found=deflection_phrases_found,
            elements_found=elements_found,
            missing_elements=missing_elements,
            requirements=requirements,
            tool_quality_score=tool_quality_score,
        )

        # Step 7: Generate recommendations
        recommendations = self._generate_recommendations(
            category=category,
            missing_elements=missing_elements,
            deflection_phrases_found=deflection_phrases_found,
            requirements=requirements,
        )

        return QualityAnalysis(
            score=score,
            category=category,
            confidence=confidence,
            query_type=query_type,
            missing_elements=missing_elements,
            deflection_phrases_found=deflection_phrases_found,
            recommendations=recommendations,
            elements_found=elements_found,
            response_length=response_length,
        )

    def _detect_deflection_phrases(self, response_lower: str) -> List[str]:
        """
        Detect deflection phrases in the response.

        Args:
            response_lower: Lowercase response text.

        Returns:
            List of deflection phrases found in the response.
        """
        found = []
        for phrase, pattern in zip(self.deflection_phrases, self._deflection_patterns):
            if pattern.search(response_lower):
                found.append(phrase)
        return found

    def _infer_query_type(self, query_lower: str) -> QueryType:
        """
        Infer the query type from the query text.

        Args:
            query_lower: Lowercase query text.

        Returns:
            Inferred QueryType.
        """
        # Check each query type's patterns
        for query_type, patterns in self._query_type_patterns.items():
            for pattern in patterns:
                if pattern.search(query_lower):
                    return query_type

        # Check for call ID pattern
        if re.search(r"HORIZON-[A-Z0-9-]+", query_lower, re.IGNORECASE):
            return QueryType.CALL_INFO

        return QueryType.GENERAL

    def _check_content_requirements(
        self,
        query_lower: str,
        response_lower: str,
        requirements: ContentRequirement,
    ) -> Tuple[List[str], List[str]]:
        """
        Check if the response meets content requirements.

        Args:
            query_lower: Lowercase query text.
            response_lower: Lowercase response text.
            requirements: ContentRequirement for this query type.

        Returns:
            Tuple of (elements_found, missing_elements).
        """
        elements_found = []
        missing_elements = []

        # Element detection patterns
        element_patterns = {
            "call_id": r"HORIZON-[A-Z0-9-]+",
            "deadline": r"(deadline|due date|closes?|submission).*\d{1,2}.*\d{4}|\d{1,2}.*20\d{2}",
            "budget": r"(budget|funding|eur|euro|million|€|contribution).*\d+",
            "type": r"(ria|ia|csa|cofund|erc|msca|innovation action|research and innovation)",
            "status": r"(open|closed|upcoming|forthcoming|active)",
            "scope": r"(scope|focus|objective|aim|target|address)",
            "programme_1": r"(eic|erc|ria|ia|msca|horizon|cluster)",
            "programme_2": r"(eic|erc|ria|ia|msca|horizon|cluster)",
            "comparison_aspect": r"(success rate|funding|eligibility|difference|comparison|versus|vs)",
            "recommendation": r"(recommend|suggest|advise|should|better|prefer)",
            "eligibility_criteria": r"(eligible|eligibility|criteria|requirement|must|should)",
            "requirements": r"(require|must|need|minimum|at least)",
            "answer": r"(yes|no|can|cannot|allowed|permitted|possible|may)",
            "budget_range": r"(range|between|from.*to|\d+.*-.*\d+|million)",
            "average": r"(average|mean|typical|median)",
            "consortium_size": r"(partner|consortium|participant).*(\d+|size)",
            "partner_names": r"(university|institute|center|centre|organization|organisation|gmbh|ltd|inc)",
            "countries": r"(germany|france|spain|italy|netherlands|belgium|sweden|austria|finland|denmark|de|fr|es|it|nl|be|se|at|fi|dk)",
            "experience": r"(experience|track record|expertise|history|previous|past)",
            "relevance": r"(relevant|related|similar|matching|suitable)",
            "project_names": r"([A-Z]{3,10}[-\s]?[A-Z0-9]*|project \w+)",
            "descriptions": r"(description|objective|aim|focus|about|summary)",
            "funding": r"(fund|grant|budget|contribution|eur|euro|€)",
            "partner_types": r"(hes|rec|prc|sme|university|research|company|industry)",
            "distribution": r"(%|percent|share|proportion|ratio)",
            "statistics": r"(\d+%|\d+\s*percent|\d+\s*projects|\d+\s*applications)",
            "numbers": r"\d+",
            "source": r"(cordis|horizon|eu portal|database|data from)",
            "context": r"(because|since|due to|as|however|therefore)",
        }

        for element in requirements.required_elements:
            pattern = element_patterns.get(element)
            if pattern:
                if re.search(pattern, response_lower, re.IGNORECASE):
                    elements_found.append(element)
                else:
                    missing_elements.append(element)
            else:
                # If no pattern defined, check if element keyword appears
                if element.replace("_", " ") in response_lower or element in response_lower:
                    elements_found.append(element)
                else:
                    missing_elements.append(element)

        return elements_found, missing_elements

    def _validate_tool_results(self, tool_results: Dict[str, Any]) -> int:
        """
        Validate the quality of tool results.

        Args:
            tool_results: Dictionary of tool results.

        Returns:
            Quality score for tool results (0-100).
        """
        if not tool_results:
            return 50  # No tool results, neutral score

        score = 100

        for tool_name, result in tool_results.items():
            if isinstance(result, dict):
                # Check for error indicators
                if result.get("error") or result.get("success") is False:
                    score -= 20
                    continue

                # Check for empty results
                if result.get("results") == [] or result.get("count") == 0:
                    score -= 15
                    continue

                # Check for calls/projects found
                calls_found = result.get("calls_found", result.get("count", -1))
                projects_found = result.get("projects_count", result.get("count", -1))

                if calls_found == 0 or projects_found == 0:
                    score -= 15

        return max(0, score)

    def _calculate_score(
        self,
        response_length: int,
        deflection_phrases_found: List[str],
        elements_found: List[str],
        missing_elements: List[str],
        requirements: ContentRequirement,
        tool_quality_score: int,
    ) -> Tuple[int, ResponseCategory, float]:
        """
        Calculate the overall quality score and determine category.

        Args:
            response_length: Length of the response.
            deflection_phrases_found: List of deflection phrases found.
            elements_found: List of required elements found.
            missing_elements: List of required elements missing.
            requirements: ContentRequirement for this query type.
            tool_quality_score: Quality score from tool results.

        Returns:
            Tuple of (score, category, confidence).
        """
        score = 100
        confidence = 1.0

        # Penalize for deflection phrases (heavily)
        deflection_penalty = len(deflection_phrases_found) * 20
        score -= min(deflection_penalty, 60)  # Cap at 60 points

        # Penalize for short responses
        if response_length < requirements.min_response_length:
            length_ratio = response_length / requirements.min_response_length
            score -= int((1 - length_ratio) * 20)

        # Penalize for missing elements
        if elements_found:
            elements_ratio = len(elements_found) / (len(elements_found) + len(missing_elements))
            score -= int((1 - elements_ratio) * 30)
        else:
            score -= 30  # No elements found at all

        # Factor in tool quality
        tool_factor = tool_quality_score / 100
        score = int(score * (0.7 + 0.3 * tool_factor))

        # Clamp score
        score = max(0, min(100, score))

        # Determine category
        if len(deflection_phrases_found) >= 2:
            category = ResponseCategory.DEFLECTION
            confidence = 0.95
        elif len(deflection_phrases_found) == 1 and score < 60:
            category = ResponseCategory.DEFLECTION
            confidence = 0.85
        elif len(deflection_phrases_found) == 1 and response_length < 200:
            # Short response with deflection phrase is likely a deflection
            category = ResponseCategory.DEFLECTION
            confidence = 0.8
        elif response_length < 50:
            category = ResponseCategory.EMPTY
            confidence = 0.9
        elif score >= 70 and len(elements_found) >= requirements.min_elements_present:
            category = ResponseCategory.COMPLETE
            confidence = 0.85
        elif score >= 50:
            category = ResponseCategory.PARTIAL
            confidence = 0.75
        else:
            category = ResponseCategory.PARTIAL
            confidence = 0.7

        return score, category, confidence

    def _generate_recommendations(
        self,
        category: ResponseCategory,
        missing_elements: List[str],
        deflection_phrases_found: List[str],
        requirements: ContentRequirement,
    ) -> List[str]:
        """
        Generate actionable recommendations for improving the response.

        Args:
            category: Response category.
            missing_elements: List of missing elements.
            deflection_phrases_found: List of deflection phrases found.
            requirements: ContentRequirement for this query type.

        Returns:
            List of recommendations.
        """
        recommendations = []

        if category == ResponseCategory.DEFLECTION:
            recommendations.append(
                "Response contains deflection phrases. Investigate why the data was not found."
            )
            if deflection_phrases_found:
                recommendations.append(
                    f"Found deflection phrases: {', '.join(deflection_phrases_found[:3])}"
                )

        if category == ResponseCategory.EMPTY:
            recommendations.append(
                "Response is too short. Ensure tools are returning data and it's being included."
            )

        if missing_elements:
            formatted_elements = [e.replace("_", " ") for e in missing_elements]
            recommendations.append(
                f"Missing required elements: {', '.join(formatted_elements)}"
            )

        if requirements.query_type == QueryType.CALL_INFO and "deadline" in missing_elements:
            recommendations.append(
                "Call information should always include deadline. Check call enrichment service."
            )

        if requirements.query_type == QueryType.BUDGET_BENCHMARK and "budget_range" in missing_elements:
            recommendations.append(
                "Budget benchmarks should include specific ranges. Check budget_benchmark tool."
            )

        return recommendations

    def is_quality_sufficient(
        self,
        analysis: QualityAnalysis,
        min_score: int = 70,
    ) -> bool:
        """
        Check if the quality analysis indicates sufficient quality.

        Args:
            analysis: QualityAnalysis result.
            min_score: Minimum acceptable score.

        Returns:
            True if quality is sufficient, False otherwise.
        """
        if analysis.category == ResponseCategory.DEFLECTION:
            return False
        if analysis.category == ResponseCategory.EMPTY:
            return False
        return analysis.score >= min_score

    def get_category_description(self, category: ResponseCategory) -> str:
        """
        Get a human-readable description of a response category.

        Args:
            category: ResponseCategory to describe.

        Returns:
            Description string.
        """
        descriptions = {
            ResponseCategory.COMPLETE: "Response fully addresses the query with all required elements.",
            ResponseCategory.PARTIAL: "Response addresses some but not all aspects of the query.",
            ResponseCategory.DEFLECTION: "Response deflects or claims inability to provide information.",
            ResponseCategory.EMPTY: "Response has no meaningful content.",
            ResponseCategory.ERROR: "An error occurred during response generation.",
        }
        return descriptions.get(category, "Unknown category.")
