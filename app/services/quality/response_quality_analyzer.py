"""
Response Quality Analyzer for AI Response Validation

This module provides comprehensive analysis of AI responses to detect:
- Deflection patterns (e.g., "I could not find", "no information available")
- Content completeness for different query types
- Quality scoring based on expected elements

Used for:
1. Automated testing of AI response quality
2. Runtime quality monitoring
3. Continuous improvement of response generation
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ResponseCategory(str, Enum):
    """Categories for response quality classification."""

    COMPLETE = "complete"  # Response has all expected elements
    PARTIAL = "partial"  # Response has some but not all elements
    DEFLECTION = "deflection"  # Response deflects without providing info
    EMPTY = "empty"  # Response is empty or too short
    ERROR = "error"  # Response contains error indicators


class QueryType(str, Enum):
    """Types of queries for context-aware validation."""

    CALL_SEARCH = "call_search"
    CALL_DETAILS = "call_details"
    PROJECT_SEARCH = "project_search"
    PROGRAMME_COMPARISON = "programme_comparison"
    PROGRAMME_STATISTICS = "programme_statistics"
    COUNTRY_STATISTICS = "country_statistics"
    BUDGET_BENCHMARK = "budget_benchmark"
    PARTNER_DISCOVERY = "partner_discovery"
    CONSORTIUM_PATTERNS = "consortium_patterns"
    ELIGIBILITY_FAQ = "eligibility_faq"
    GENERAL_FAQ = "general_faq"
    CALL_HISTORY = "call_history"
    SIMILAR_PROJECTS = "similar_projects"


class QualityAnalysis(BaseModel):
    """Result of quality analysis for an AI response."""

    score: int = Field(ge=0, le=100, description="Overall quality score 0-100")
    category: ResponseCategory = Field(description="Response category classification")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the analysis")
    query_type: QueryType | None = Field(default=None, description="Detected query type")
    expected_elements: list[str] = Field(
        default_factory=list, description="Elements expected in the response"
    )
    found_elements: list[str] = Field(
        default_factory=list, description="Elements found in the response"
    )
    missing_elements: list[str] = Field(
        default_factory=list, description="Elements missing from the response"
    )
    deflection_phrases_found: list[str] = Field(
        default_factory=list, description="Deflection phrases detected"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Recommendations for improvement"
    )
    word_count: int = Field(default=0, description="Word count of the response")
    has_structured_data: bool = Field(
        default=False, description="Whether response contains structured data"
    )
    has_citations: bool = Field(
        default=False, description="Whether response contains citations/sources"
    )


@dataclass
class QueryTypePattern:
    """Pattern for detecting query types."""

    query_type: QueryType
    patterns: list[str]
    expected_elements: list[str]
    min_word_count: int = 50


class ResponseQualityAnalyzer:
    """
    Comprehensive analyzer for AI response quality.

    Detects deflections, validates content completeness, and provides
    quality scores based on expected response elements.
    """

    # Deflection phrases that indicate non-answers
    DEFLECTION_PHRASES: list[str] = [
        "could not find",
        "couldn't find",
        "no information available",
        "please try a more specific",
        "I am not sure",
        "I'm not sure",
        "I do not have",
        "I don't have",
        "unable to retrieve",
        "no results found",
        "try again later",
        "could not extract specific details",
        "found some information but",
        "I cannot provide",
        "I can't provide",
        "not able to find",
        "wasn't able to find",
        "no matching",
        "no relevant",
        "unfortunately, I could not",
        "unfortunately I could not",
        "I apologize, but I could not",
        "I'm sorry, but I could not",
        "no data available",
        "insufficient information",
        "I don't know",
        "I do not know",
    ]

    # Phrases that indicate partial information
    PARTIAL_PHRASES: list[str] = [
        "limited information",
        "partial results",
        "some results",
        "could only find",
        "only found",
        "might not be complete",
        "may be incomplete",
    ]

    # Query type detection patterns with expected elements
    QUERY_TYPE_PATTERNS: list[QueryTypePattern] = [
        # Call-related queries
        QueryTypePattern(
            query_type=QueryType.CALL_DETAILS,
            patterns=[
                r"HORIZON-[A-Z0-9-]+",
                r"tell me about.+call",
                r"details.+call",
                r"information about.+HORIZON",
            ],
            expected_elements=[
                "call_id",
                "title",
                "deadline",
                "budget",
                "type",
                "status",
            ],
            min_word_count=100,
        ),
        QueryTypePattern(
            query_type=QueryType.CALL_SEARCH,
            patterns=[
                r"find.+calls?",
                r"search.+calls?",
                r"open calls?",
                r"upcoming calls?",
                r"funding (calls?|opportunities)",
                r"calls? (for|about|on)",
            ],
            expected_elements=["calls_found", "call_list", "deadlines"],
            min_word_count=150,
        ),
        # Partner discovery (before programme comparison to avoid conflicts)
        QueryTypePattern(
            query_type=QueryType.PARTNER_DISCOVERY,
            patterns=[
                r"find.+partners?",
                r"partners?.+(for|with|experienced)",
                r"organizations?.+(with|experienced|working)",
                r"who.+(works?|working).+on",
                r"(SME|SMEs|company|companies|university|universities).+(with|for|in)",
                r"find.+(SME|SMEs|German|French|Dutch|experienced)",
                r"(German|French|Dutch|Spanish|Italian).+(SME|partner|organization)",
                r"partners?.+expertise",
            ],
            expected_elements=[
                "partners_found",
                "partner_names",
                "experience_score",
                "relevant_projects",
            ],
            min_word_count=150,
        ),
        # Eligibility queries (before programme comparison to catch specific patterns)
        QueryTypePattern(
            query_type=QueryType.ELIGIBILITY_FAQ,
            patterns=[
                r"(can|eligible|eligibility).+(participate|apply|submit)",
                r"(requirements?|criteria).+(for|to)",
                r"who can apply",
                r"(SME|university|company).+(eligible|apply)",
                r"(Switzerland|UK|Norway|Israel|Turkey).+(eligible|participate)",
                r"is.+(eligible|allowed)",
                r"eligibility.+(criteria|requirements?)",
            ],
            expected_elements=[
                "eligibility_rules",
                "requirements",
                "minimum_consortium",
            ],
            min_word_count=100,
        ),
        # Programme queries
        QueryTypePattern(
            query_type=QueryType.PROGRAMME_COMPARISON,
            patterns=[
                r"compare.+(EIC|ERC|MSCA|RIA|IA|CSA|Horizon)",
                r"(EIC|ERC|MSCA|RIA|IA|CSA).+vs",
                r"difference.+between.+(EIC|ERC|MSCA|RIA|IA|CSA|Horizon)",
                r"(EIC|ERC|MSCA|RIA|IA|CSA).+(or|versus).+(EIC|ERC|MSCA|RIA|IA|CSA)",
                r"Horizon Europe.+vs.+Horizon 2020",
                r"Horizon 2020.+vs.+Horizon Europe",
                r"compare.+Horizon",
            ],
            expected_elements=[
                "comparison_table",
                "success_rate",
                "funding_range",
                "target_applicants",
            ],
            min_word_count=200,
        ),
        QueryTypePattern(
            query_type=QueryType.PROGRAMME_STATISTICS,
            patterns=[
                r"(statistics|stats).+(EIC|ERC|MSCA|RIA|IA|CSA|Horizon)",
                r"success rate.+(EIC|ERC|MSCA|RIA|IA|CSA)",
                r"(EIC|ERC|MSCA|RIA|IA|CSA).+statistics",
                r"how many projects.+(funded|successful)",
            ],
            expected_elements=[
                "success_rate",
                "total_projects",
                "funding_amount",
                "consortium_size",
            ],
            min_word_count=100,
        ),
        # Budget and consortium queries
        QueryTypePattern(
            query_type=QueryType.BUDGET_BENCHMARK,
            patterns=[
                r"(typical|average|median).+budget",
                r"budget.+(for|benchmark|range)",
                r"how much.+(funding|budget|grant)",
                r"budget.+(RIA|IA|CSA|Cluster)",
            ],
            expected_elements=[
                "budget_range",
                "average_budget",
                "consortium_size",
                "per_partner",
            ],
            min_word_count=100,
        ),
        QueryTypePattern(
            query_type=QueryType.CONSORTIUM_PATTERNS,
            patterns=[
                r"consortium.+(patterns?|composition|size|structure)",
                r"(typical|average).+consortium",
                r"how many partners",
                r"partner.+mix",
            ],
            expected_elements=[
                "consortium_size",
                "entity_types",
                "country_distribution",
                "coordinator_patterns",
            ],
            min_word_count=100,
        ),
        # Project queries
        QueryTypePattern(
            query_type=QueryType.PROJECT_SEARCH,
            patterns=[
                r"find.+projects?",
                r"search.+projects?",
                r"projects?.+(about|on|related)",
                r"funded projects?",
            ],
            expected_elements=["projects_found", "project_list", "funding_amounts"],
            min_word_count=150,
        ),
        QueryTypePattern(
            query_type=QueryType.SIMILAR_PROJECTS,
            patterns=[
                r"similar projects?",
                r"projects? like",
                r"related projects?",
                r"comparable projects?",
            ],
            expected_elements=[
                "similar_projects",
                "similarity_score",
                "project_details",
            ],
            min_word_count=100,
        ),
        QueryTypePattern(
            query_type=QueryType.COUNTRY_STATISTICS,
            patterns=[
                r"(Germany|France|Spain|Italy|Netherlands|UK|Belgium|Sweden).+(statistics|performance|participation)",
                r"(statistics|performance).+(Germany|France|Spain|Italy)",
                r"how.+(Germany|France|Spain|Italy).+perform",
            ],
            expected_elements=[
                "participation_count",
                "funding_received",
                "success_rate",
                "top_organizations",
            ],
            min_word_count=100,
        ),
        QueryTypePattern(
            query_type=QueryType.CALL_HISTORY,
            patterns=[
                r"(historical|history|trends?).+(calls?|funding)",
                r"funding.+over.+(years?|time)",
                r"how.+changed.+over",
                r"trends?.+(in|for|cluster)",
            ],
            expected_elements=["timeline", "trend_analysis", "funding_trend"],
            min_word_count=100,
        ),
        # General FAQ - last as catch-all for FAQ-like queries
        QueryTypePattern(
            query_type=QueryType.GENERAL_FAQ,
            patterns=[
                r"what is.+(RIA|IA|CSA|EIC|ERC|MSCA|Horizon)",
                r"how does.+(work|apply)",
                r"explain.+(RIA|IA|CSA|EIC|ERC)",
                r"definition of",
            ],
            expected_elements=["definition", "explanation", "key_features"],
            min_word_count=50,
        ),
    ]

    # Structured data indicators
    STRUCTURED_DATA_INDICATORS: list[str] = [
        r"\*\*[^*]+\*\*:",  # Bold headers with colons
        r"^\s*[-•]\s+",  # Bullet points
        r"^\s*\d+\.\s+",  # Numbered lists
        r"\|\s*[^|]+\s*\|",  # Table format
        r"📋|🔬|🚀|🟢|🟡|🔴|💰|⏰|🏛️|💡|📚|📦|👥",  # Emoji icons used in formatting
    ]

    # Citation indicators
    CITATION_INDICATORS: list[str] = [
        r"according to",
        r"based on",
        r"source:",
        r"reference:",
        r"https?://",
        r"Horizon Europe",
        r"Work Programme",
        r"EU Regulation",
    ]

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the ResponseQualityAnalyzer.

        Args:
            strict_mode: If True, applies stricter quality thresholds
        """
        self.strict_mode = strict_mode
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for efficiency."""
        self._deflection_pattern = re.compile(
            "|".join(re.escape(p) for p in self.DEFLECTION_PHRASES), re.IGNORECASE
        )
        self._partial_pattern = re.compile(
            "|".join(re.escape(p) for p in self.PARTIAL_PHRASES), re.IGNORECASE
        )
        self._structured_pattern = re.compile(
            "|".join(self.STRUCTURED_DATA_INDICATORS), re.MULTILINE
        )
        self._citation_pattern = re.compile("|".join(self.CITATION_INDICATORS), re.IGNORECASE)

    def analyze(self, query: str, response: str) -> QualityAnalysis:
        """
        Analyze the quality of an AI response.

        Args:
            query: The original user query
            response: The AI-generated response

        Returns:
            QualityAnalysis with comprehensive quality metrics
        """
        # Basic metrics
        word_count = len(response.split())
        query_type = self._detect_query_type(query)

        # Check for deflection
        deflection_phrases = self._find_deflection_phrases(response)

        # Check for structured data and citations
        has_structured_data = bool(self._structured_pattern.search(response))
        has_citations = bool(self._citation_pattern.search(response))

        # Get expected elements based on query type
        expected_elements = self._get_expected_elements(query_type, query)

        # Find which elements are present
        found_elements = self._find_elements(response, expected_elements)
        missing_elements = [e for e in expected_elements if e not in found_elements]

        # Calculate category and score
        category = self._determine_category(
            word_count=word_count,
            deflection_phrases=deflection_phrases,
            found_elements=found_elements,
            expected_elements=expected_elements,
            query_type=query_type,
        )

        score = self._calculate_score(
            category=category,
            word_count=word_count,
            found_elements=found_elements,
            expected_elements=expected_elements,
            has_structured_data=has_structured_data,
            has_citations=has_citations,
            query_type=query_type,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            category=category,
            missing_elements=missing_elements,
            deflection_phrases=deflection_phrases,
            word_count=word_count,
            has_structured_data=has_structured_data,
            query_type=query_type,
        )

        # Calculate confidence
        confidence = self._calculate_confidence(query_type, expected_elements)

        return QualityAnalysis(
            score=score,
            category=category,
            confidence=confidence,
            query_type=query_type,
            expected_elements=expected_elements,
            found_elements=found_elements,
            missing_elements=missing_elements,
            deflection_phrases_found=deflection_phrases,
            recommendations=recommendations,
            word_count=word_count,
            has_structured_data=has_structured_data,
            has_citations=has_citations,
        )

    def _detect_query_type(self, query: str) -> QueryType | None:
        """Detect the type of query based on patterns."""
        query_lower = query.lower()

        for pattern_info in self.QUERY_TYPE_PATTERNS:
            for pattern in pattern_info.patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    return pattern_info.query_type

        return QueryType.GENERAL_FAQ

    def _find_deflection_phrases(self, response: str) -> list[str]:
        """Find deflection phrases in the response."""
        found = []
        response_lower = response.lower()

        for phrase in self.DEFLECTION_PHRASES:
            if phrase.lower() in response_lower:
                found.append(phrase)

        return found

    def _get_expected_elements(self, query_type: QueryType | None, query: str) -> list[str]:
        """Get expected elements based on query type."""
        if query_type is None:
            return ["answer", "explanation"]

        for pattern_info in self.QUERY_TYPE_PATTERNS:
            if pattern_info.query_type == query_type:
                return pattern_info.expected_elements

        return ["answer", "explanation"]

    def _find_elements(self, response: str, expected_elements: list[str]) -> list[str]:
        """Find which expected elements are present in the response."""
        found = []
        response_lower = response.lower()

        # Element detection patterns
        element_patterns: dict[str, list[str]] = {
            # Call elements
            "call_id": [r"HORIZON-[A-Z0-9-]+", r"call id", r"call identifier", r"📋"],
            "title": [r"\*\*\d+\.", r"title:", r"call title"],
            "deadline": [
                r"deadline",
                r"due date",
                r"closes?:?",
                r"⏰",
                r"\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
            ],
            "budget": [r"€\s?\d+", r"EUR\s?\d+", r"\d+\s*M\s*EUR", r"budget", r"💰", r"million"],
            "type": [r"RIA|IA|CSA|COFUND", r"action type", r"🔬|🚀|🤝"],
            "status": [r"open|closed|upcoming", r"status", r"🟢|🟡|🔴"],
            # Search elements
            "calls_found": [r"\d+\s+(calls?|opportunities?|results?)", r"found\s+\d+", r"I found"],
            "call_list": [r"\*\*\d+\.", r"1\.", r"•\s+HORIZON"],
            "deadlines": [r"deadline", r"due by", r"closes"],
            # Programme elements
            "comparison_table": [r"\|.*\|", r"vs\.", r"compared to", r"whereas", r"while"],
            "success_rate": [r"\d+(\.\d+)?%\s*(success|rate)", r"success rate", r"approval rate"],
            "funding_range": [r"€?\d+.*-.*€?\d+", r"up to €", r"between.*and", r"range"],
            "target_applicants": [r"SME|researcher|university|company|startup|for.*who"],
            # Budget elements
            "budget_range": [r"€?\d+.*-.*€?\d+", r"between.*€", r"from.*to"],
            "average_budget": [r"average.*€", r"median.*€", r"typical.*€", r"around €"],
            "consortium_size": [r"\d+\s*(partners?|organizations?|entities)", r"consortium.*\d+"],
            "per_partner": [r"per partner", r"each partner", r"per organization"],
            # Consortium elements
            "entity_types": [r"HES|REC|PRC|SME|university|research|company"],
            "country_distribution": [r"Germany|France|Netherlands|Spain|Italy", r"countries"],
            "coordinator_patterns": [r"coordinator", r"lead partner", r"coordination"],
            # Partner elements
            "partners_found": [r"\d+\s*(partners?|organizations?|found)", r"found\s+\d+"],
            "partner_names": [r"University|Institute|Fraunhofer|CNRS|TNO|VTT|IMEC"],
            "experience_score": [r"experience|score|rating|track record"],
            "relevant_projects": [r"\d+\s*projects?", r"project.*experience"],
            # Project elements
            "projects_found": [r"\d+\s*(projects?|results?)", r"found\s+\d+"],
            "project_list": [r"\*\*\d+\.", r"project.*:", r"•\s+\w+"],
            "funding_amounts": [r"€\s?\d+", r"EUR\s?\d+", r"funded"],
            # Analysis elements
            "similar_projects": [r"similar", r"related", r"like.*project"],
            "similarity_score": [r"similarity|match|score"],
            "project_details": [r"objective|description|abstract"],
            "timeline": [r"\d{4}", r"year", r"since", r"from.*to"],
            "trend_analysis": [r"trend|increasing|decreasing|stable|growing"],
            "funding_trend": [r"funding.*trend|growing|declining"],
            # FAQ elements
            "eligibility_rules": [r"eligible|eligibility|can.*apply|cannot.*apply"],
            "requirements": [r"require|must|need|minimum"],
            "minimum_consortium": [r"minimum.*\d+", r"at least.*\d+", r"\d+.*independent"],
            # Stats elements
            "total_projects": [r"\d+\s*projects?", r"total.*\d+"],
            "funding_amount": [r"€.*billion|million|€\d+", r"funding.*€"],
            # Country stats
            "participation_count": [r"\d+\s*participation", r"participated.*\d+"],
            "funding_received": [r"received.*€", r"€.*funding"],
            "top_organizations": [r"top.*organization|leading.*institution"],
            # General
            "definition": [r"is a|refers to|defined as|means"],
            "explanation": [r"because|therefore|this means|specifically"],
            "key_features": [r"key|main|important|feature|characteristic"],
            "answer": [r".{50,}"],  # At least 50 chars indicates an answer
        }

        for element in expected_elements:
            if element in element_patterns:
                for pattern in element_patterns[element]:
                    if re.search(pattern, response, re.IGNORECASE):
                        found.append(element)
                        break
            else:
                # Fallback: check if element word appears
                if element.replace("_", " ") in response_lower:
                    found.append(element)

        return list(set(found))

    def _determine_category(
        self,
        word_count: int,
        deflection_phrases: list[str],
        found_elements: list[str],
        expected_elements: list[str],
        query_type: QueryType | None,
    ) -> ResponseCategory:
        """Determine the response category."""
        # Get minimum word count for query type
        min_words = 50
        for pattern_info in self.QUERY_TYPE_PATTERNS:
            if pattern_info.query_type == query_type:
                min_words = pattern_info.min_word_count
                break

        # Check for empty/too short
        if word_count < 20:
            return ResponseCategory.EMPTY

        # Check for deflection
        if len(deflection_phrases) >= 2:
            return ResponseCategory.DEFLECTION
        if len(deflection_phrases) == 1 and word_count < min_words:
            return ResponseCategory.DEFLECTION

        # Check completeness
        if len(expected_elements) == 0:
            return (
                ResponseCategory.COMPLETE if word_count >= min_words else ResponseCategory.PARTIAL
            )

        coverage = len(found_elements) / len(expected_elements)

        if coverage >= 0.7:
            return ResponseCategory.COMPLETE
        elif coverage >= 0.4:
            return ResponseCategory.PARTIAL
        elif word_count < min_words // 2:
            return ResponseCategory.EMPTY
        else:
            return ResponseCategory.PARTIAL

    def _calculate_score(
        self,
        category: ResponseCategory,
        word_count: int,
        found_elements: list[str],
        expected_elements: list[str],
        has_structured_data: bool,
        has_citations: bool,
        query_type: QueryType | None,
    ) -> int:
        """Calculate quality score from 0-100."""
        # Base score by category
        base_scores = {
            ResponseCategory.COMPLETE: 75,
            ResponseCategory.PARTIAL: 50,
            ResponseCategory.DEFLECTION: 15,
            ResponseCategory.EMPTY: 5,
            ResponseCategory.ERROR: 0,
        }
        score = base_scores.get(category, 0)

        # Add element coverage bonus (up to 15 points)
        if expected_elements:
            coverage = len(found_elements) / len(expected_elements)
            score += int(coverage * 15)

        # Add structured data bonus (5 points)
        if has_structured_data:
            score += 5

        # Add citations bonus (5 points)
        if has_citations:
            score += 5

        # Word count bonus (up to 5 points for longer, comprehensive responses)
        min_words = 100
        for pattern_info in self.QUERY_TYPE_PATTERNS:
            if pattern_info.query_type == query_type:
                min_words = pattern_info.min_word_count
                break

        if word_count >= min_words * 2:
            score += 5
        elif word_count >= min_words * 1.5:
            score += 3
        elif word_count >= min_words:
            score += 1

        # Penalty for deflection phrases
        deflection_count = (
            len(self._find_deflection_phrases_from_response(""))
            if hasattr(self, "_last_response")
            else 0
        )
        score -= deflection_count * 10

        # Ensure score is within bounds
        return max(0, min(100, score))

    def _find_deflection_phrases_from_response(self, response: str) -> list[str]:
        """Helper to find deflection phrases (used in scoring)."""
        return self._find_deflection_phrases(response)

    def _calculate_confidence(
        self, query_type: QueryType | None, expected_elements: list[str]
    ) -> float:
        """Calculate confidence in the analysis."""
        confidence = 0.5

        # Higher confidence if we detected a query type
        if query_type is not None:
            confidence += 0.2

        # Higher confidence if we have clear expectations
        if len(expected_elements) >= 3:
            confidence += 0.2

        # Higher confidence for specific query types
        high_confidence_types = [
            QueryType.CALL_DETAILS,
            QueryType.CALL_SEARCH,
            QueryType.BUDGET_BENCHMARK,
            QueryType.PARTNER_DISCOVERY,
        ]
        if query_type in high_confidence_types:
            confidence += 0.1

        return min(1.0, confidence)

    def _generate_recommendations(
        self,
        category: ResponseCategory,
        missing_elements: list[str],
        deflection_phrases: list[str],
        word_count: int,
        has_structured_data: bool,
        query_type: QueryType | None,
    ) -> list[str]:
        """Generate recommendations for improving the response."""
        recommendations = []

        if category == ResponseCategory.DEFLECTION:
            recommendations.append(
                "Response contains deflection phrases. Ensure tools return actual data."
            )
            if deflection_phrases:
                recommendations.append(
                    f"Detected deflection phrases: {', '.join(deflection_phrases[:3])}"
                )

        if category == ResponseCategory.EMPTY:
            recommendations.append(
                "Response is too short. Ensure adequate information is provided."
            )

        if missing_elements:
            recommendations.append(f"Missing expected elements: {', '.join(missing_elements[:5])}")

        if not has_structured_data and query_type in [
            QueryType.CALL_SEARCH,
            QueryType.PROJECT_SEARCH,
            QueryType.PARTNER_DISCOVERY,
        ]:
            recommendations.append(
                "Consider using structured formatting (bullet points, tables) for list-based responses."
            )

        min_words = 100
        for pattern_info in self.QUERY_TYPE_PATTERNS:
            if pattern_info.query_type == query_type:
                min_words = pattern_info.min_word_count
                break

        if word_count < min_words:
            recommendations.append(
                f"Response may be too brief. Expected minimum {min_words} words for this query type."
            )

        return recommendations

    def is_acceptable(self, analysis: QualityAnalysis, min_score: int = 70) -> bool:
        """
        Check if the response quality is acceptable.

        Args:
            analysis: The QualityAnalysis result
            min_score: Minimum acceptable score (default 70)

        Returns:
            True if the response meets quality standards
        """
        if analysis.category == ResponseCategory.DEFLECTION:
            return False
        if analysis.category == ResponseCategory.EMPTY:
            return False
        return analysis.score >= min_score

    def quick_check(self, response: str) -> tuple[bool, str]:
        """
        Quick check for obvious quality issues.

        Args:
            response: The AI response to check

        Returns:
            Tuple of (is_ok, reason)
        """
        word_count = len(response.split())

        if word_count < 20:
            return False, "Response too short"

        deflections = self._find_deflection_phrases(response)
        if len(deflections) >= 2:
            return False, f"Multiple deflection phrases found: {deflections[:2]}"

        return True, "OK"


# Convenience function for testing
def analyze_response(query: str, response: str) -> QualityAnalysis:
    """
    Convenience function to analyze a response.

    Args:
        query: The user query
        response: The AI response

    Returns:
        QualityAnalysis result
    """
    analyzer = ResponseQualityAnalyzer()
    return analyzer.analyze(query, response)
