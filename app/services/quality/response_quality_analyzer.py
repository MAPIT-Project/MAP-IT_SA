"""
Response Quality Analyzer for AI Response Validation

This module provides comprehensive analysis of AI responses to ensure they meet
quality standards and don't contain deflection patterns that provide no value
to users.

Key features:
- Deflection phrase detection (e.g., "I could not find", "no information available")
- Content requirement validation (e.g., call info must have deadline, budget)
- Quality scoring (0-100)
- Response categorization (COMPLETE, PARTIAL, DEFLECTION, EMPTY, ERROR)
- Detailed analysis with recommendations

Usage:
    analyzer = ResponseQualityAnalyzer()
    analysis = analyzer.analyze(query="Tell me about HORIZON-CL5-2026-D3-01", response="...")
    if analysis.score < 75:
        # Handle low-quality response
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import timezone, datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ResponseCategory(str, Enum):
    """Category of the AI response based on quality analysis."""

    COMPLETE = "complete"  # Response fully answers the query with all required elements
    PARTIAL = "partial"  # Response has some useful info but missing elements
    DEFLECTION = "deflection"  # Response deflects/avoids answering (worst)
    EMPTY = "empty"  # Response is too short or contains no meaningful content
    ERROR = "error"  # Response indicates an error occurred


class QueryType(str, Enum):
    """Type of query to determine content requirements."""

    CALL_INFO = "call_info"  # Query about a specific funding call
    CALL_SEARCH = "call_search"  # Search for funding calls
    PROJECT_SEARCH = "project_search"  # Search for projects
    PROGRAMME_COMPARISON = "programme_comparison"  # Compare programmes
    ELIGIBILITY_FAQ = "eligibility_faq"  # Eligibility questions
    BUDGET_BENCHMARK = "budget_benchmark"  # Budget benchmarking
    PARTNER_DISCOVERY = "partner_discovery"  # Finding partners
    CONSORTIUM_PATTERNS = "consortium_patterns"  # Consortium analysis
    STATISTICS = "statistics"  # Programme/country statistics
    GENERAL_FAQ = "general_faq"  # General questions about EU funding


@dataclass
class ContentRequirement:
    """A required content element for a specific query type."""

    name: str  # Name of the requirement
    patterns: List[str]  # Regex patterns to match (any match = satisfied)
    weight: float = 1.0  # Importance weight for scoring (1.0 = normal)
    required: bool = True  # If True, missing this is a major issue
    case_sensitive: bool = False  # Whether pattern matching is case-sensitive


@dataclass
class QualityAnalysis:
    """Complete analysis result for a response."""

    score: int  # Overall quality score (0-100)
    category: ResponseCategory  # Response category
    confidence: float  # Confidence in this analysis (0.0-1.0)
    query_type: QueryType  # Detected type of query

    # Content analysis
    missing_elements: List[str] = field(default_factory=list)
    present_elements: List[str] = field(default_factory=list)
    content_coverage: float = 0.0  # Percentage of required content present

    # Deflection analysis
    deflection_phrases_found: List[str] = field(default_factory=list)
    deflection_severity: str = "none"  # "none", "minor", "major", "critical"

    # Quality metrics
    response_length: int = 0
    word_count: int = 0
    has_structured_data: bool = False
    has_citations: bool = False
    has_actionable_info: bool = False

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    # Metadata
    analysis_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    query: str = ""
    response_preview: str = ""


class ResponseQualityAnalyzer:
    """
    Analyzer for AI response quality.

    Detects deflection phrases, validates content requirements,
    and provides comprehensive quality scoring.
    """

    # Deflection phrases that indicate a poor/non-answer
    DEFLECTION_PHRASES: List[Tuple[str, str]] = [
        # (phrase pattern, severity: "minor", "major", "critical")
        (r"could not find", "major"),
        (r"couldn't find", "major"),
        (r"no information available", "critical"),
        (r"please try a more specific", "major"),
        (r"I am not sure", "minor"),
        (r"I'm not sure", "minor"),
        (r"I do not have", "major"),
        (r"I don't have", "major"),
        (r"unable to retrieve", "major"),
        (r"no results found", "major"),
        (r"try again later", "critical"),
        (r"could not extract specific details", "critical"),
        (r"found some information but", "major"),
        (r"I don't have access to", "major"),
        (r"I cannot provide", "major"),
        (r"I'm unable to", "major"),
        (r"I apologize.{0,30}I cannot", "major"),
        (r"Unfortunately.{0,30}I cannot", "major"),
        (r"I'm sorry.{0,30}I don't have", "major"),
        (r"I couldn't locate", "major"),
        (r"information is not available", "critical"),
        (r"data is unavailable", "critical"),
        (r"outside.{0,20}knowledge", "major"),
        (r"beyond.{0,20}capabilities", "major"),
        (r"not in my training", "major"),
        (r"no matching records", "major"),
        (r"search returned no", "major"),
        (r"empty result", "major"),
        (r"cannot access", "major"),
        (r"database error", "critical"),
        (r"database.{0,20}unavailable", "critical"),
        (r"currently unavailable", "critical"),
        (r"service.{0,20}unavailable", "critical"),
    ]

    # Content requirements by query type
    CONTENT_REQUIREMENTS: Dict[QueryType, List[ContentRequirement]] = {
        QueryType.CALL_INFO: [
            ContentRequirement(
                name="call_identifier",
                patterns=[
                    r"HORIZON-[A-Z0-9-]+",
                    r"topic\s*(code|id)",
                    r"call\s*(id|identifier)",
                ],
                weight=1.5,
            ),
            ContentRequirement(
                name="deadline",
                patterns=[
                    r"deadline",
                    r"\d{1,2}\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
                    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}",
                    r"\d{4}-\d{2}-\d{2}",
                ],
                weight=1.5,
            ),
            ContentRequirement(
                name="budget",
                patterns=[
                    r"budget",
                    r"€\s*[\d,.]+",
                    r"EUR\s*[\d,.]+",
                    r"million",
                    r"\d+[.,]?\d*\s*M",
                ],
                weight=1.3,
            ),
            ContentRequirement(
                name="action_type",
                patterns=[r"\bRIA\b", r"\bIA\b", r"\bCSA\b", r"action\s*type"],
                weight=1.2,
            ),
            ContentRequirement(
                name="status",
                patterns=[r"\bopen\b", r"\bclosed\b", r"\bupcoming\b", r"status"],
                weight=1.0,
            ),
            ContentRequirement(
                name="scope_or_description",
                patterns=[r"scope", r"focus", r"objective", r"aim", r"topic"],
                weight=1.0,
                required=False,
            ),
        ],
        QueryType.CALL_SEARCH: [
            ContentRequirement(
                name="calls_found",
                patterns=[
                    r"\d+\s*(funding\s*)?(call|opportunit)",
                    r"found\s*\d+",
                    r"identified\s*\d+",
                ],
                weight=1.5,
            ),
            ContentRequirement(
                name="call_identifiers",
                patterns=[r"HORIZON-[A-Z0-9-]+"],
                weight=1.3,
            ),
            ContentRequirement(
                name="deadlines",
                patterns=[r"deadline", r"\d{4}"],
                weight=1.2,
            ),
        ],
        QueryType.PROJECT_SEARCH: [
            ContentRequirement(
                name="projects_found",
                patterns=[
                    r"\d+\s*project",
                    r"found\s*\d+",
                    r"identified\s*\d+",
                ],
                weight=1.5,
            ),
            ContentRequirement(
                name="project_names",
                patterns=[r"acronym", r"project\s*(name|title)", r"\b[A-Z]{3,10}\b"],
                weight=1.2,
            ),
        ],
        QueryType.PROGRAMME_COMPARISON: [
            ContentRequirement(
                name="both_programmes",
                patterns=[r"(EIC|ERC|MSCA|RIA|IA|CSA).*\1", r"both"],
                weight=1.0,
                required=False,
            ),
            ContentRequirement(
                name="comparison_elements",
                patterns=[r"compar", r"differ", r"similar", r"vs\.?", r"versus"],
                weight=1.5,
            ),
            ContentRequirement(
                name="specific_metrics",
                patterns=[
                    r"success\s*rate",
                    r"budget",
                    r"funding",
                    r"duration",
                    r"eligib",
                ],
                weight=1.3,
            ),
        ],
        QueryType.ELIGIBILITY_FAQ: [
            ContentRequirement(
                name="clear_answer",
                patterns=[r"\byes\b", r"\bno\b", r"\bcan\b", r"\bcannot\b", r"eligible"],
                weight=1.5,
            ),
            ContentRequirement(
                name="requirements",
                patterns=[r"require", r"must", r"should", r"need"],
                weight=1.2,
            ),
            ContentRequirement(
                name="specific_rules",
                patterns=[r"minimum", r"at least", r"\d+", r"partner"],
                weight=1.0,
                required=False,
            ),
        ],
        QueryType.BUDGET_BENCHMARK: [
            ContentRequirement(
                name="budget_figures",
                patterns=[
                    r"€\s*[\d,.]+",
                    r"EUR\s*[\d,.]+",
                    r"\d+[.,]?\d*\s*M",
                    r"million",
                ],
                weight=1.5,
            ),
            ContentRequirement(
                name="statistics",
                patterns=[r"average", r"median", r"typical", r"range"],
                weight=1.3,
            ),
            ContentRequirement(
                name="consortium_size",
                patterns=[r"partner", r"consortium", r"organization"],
                weight=1.0,
                required=False,
            ),
        ],
        QueryType.PARTNER_DISCOVERY: [
            ContentRequirement(
                name="partners_found",
                patterns=[
                    r"partner",
                    r"organization",
                    r"institution",
                    r"universit",
                ],
                weight=1.5,
            ),
            ContentRequirement(
                name="country_info",
                patterns=[
                    r"Germany|France|Spain|Italy|Netherlands|Belgium",
                    r"\b[A-Z]{2}\b",
                ],
                weight=1.2,
            ),
            ContentRequirement(
                name="experience_indicators",
                patterns=[r"experience", r"project", r"track record", r"expertise"],
                weight=1.0,
            ),
        ],
        QueryType.CONSORTIUM_PATTERNS: [
            ContentRequirement(
                name="consortium_size",
                patterns=[r"\d+\s*partner", r"average", r"typical", r"size"],
                weight=1.5,
            ),
            ContentRequirement(
                name="org_type_distribution",
                patterns=[r"HES|REC|PRC|SME", r"universit", r"research", r"compan"],
                weight=1.3,
            ),
        ],
        QueryType.STATISTICS: [
            ContentRequirement(
                name="numerical_data",
                patterns=[r"\d+%?", r"€", r"EUR", r"million", r"billion"],
                weight=1.5,
            ),
            ContentRequirement(
                name="statistical_terms",
                patterns=[r"success\s*rate", r"average", r"total", r"count"],
                weight=1.3,
            ),
        ],
        QueryType.GENERAL_FAQ: [
            ContentRequirement(
                name="substantive_answer",
                patterns=[r".{100,}"],  # At least 100 chars of content
                weight=1.5,
            ),
        ],
    }

    # Minimum response lengths by query type
    MIN_RESPONSE_LENGTHS: Dict[QueryType, int] = {
        QueryType.CALL_INFO: 200,
        QueryType.CALL_SEARCH: 150,
        QueryType.PROJECT_SEARCH: 150,
        QueryType.PROGRAMME_COMPARISON: 300,
        QueryType.ELIGIBILITY_FAQ: 100,
        QueryType.BUDGET_BENCHMARK: 200,
        QueryType.PARTNER_DISCOVERY: 150,
        QueryType.CONSORTIUM_PATTERNS: 200,
        QueryType.STATISTICS: 150,
        QueryType.GENERAL_FAQ: 100,
    }

    # Query type detection patterns
    QUERY_TYPE_PATTERNS: Dict[QueryType, List[str]] = {
        QueryType.CALL_INFO: [
            r"HORIZON-[A-Z0-9-]+",
            r"tell me about.*(call|topic)",
            r"details.*(call|topic)",
            r"what is.*(call|topic)",
        ],
        QueryType.CALL_SEARCH: [
            r"find.*(call|funding|opportunit)",
            r"search.*(call|funding)",
            r"looking for.*(call|grant|funding|opportunit)",
            r"open\s+call",
        ],
        QueryType.PROJECT_SEARCH: [
            r"find.*(project)",
            r"search.*(project)",
            r"funded\s+project",
            r"CORDIS",
        ],
        QueryType.PROGRAMME_COMPARISON: [
            r"compar.*vs",
            r"differ.*between",
            r"EIC.*ERC|ERC.*EIC",
            r"RIA.*IA|IA.*RIA",
            r"which.*better",
            r"compare\s+(MSCA|EIC|ERC|RIA|IA)",
            r"(MSCA|EIC|ERC|RIA|IA).*(with|vs|compared)",
        ],
        QueryType.ELIGIBILITY_FAQ: [
            r"eligible",
            r"can.*(apply|participate)",
            r"who\s+can",
            r"requirements\s+for",
        ],
        QueryType.BUDGET_BENCHMARK: [
            r"budget.*(typical|average|benchmark)",
            r"how much.*funding",
            r"typical.*cost",
            r"budget.*RIA|budget.*IA",
            r"average\s+funding",
            r"funding.*(RIA|IA|CSA)",
        ],
        QueryType.PARTNER_DISCOVERY: [
            r"find.*partner",
            r"partner.*experience",
            r"organization.*hydrogen|hydrogen.*organization",
            r"SME.*experience",
            r"organization.*(in|from)\s+\w+",
            r"(universit|institut|compan).*(with|experience|expertise)",
            r"(Germany|France|Spain|Italy|Netherlands).*(partner|organization|universit)",
        ],
        QueryType.CONSORTIUM_PATTERNS: [
            r"consortium.*(pattern|size|composition)",
            r"typical.*consortium",
            r"how many.*partner",
        ],
        QueryType.STATISTICS: [
            r"success\s*rate",
            r"statistics.*for",
            r"how many.*(project|funding)",
            r"(country|programme)\s+statistics",
        ],
    }

    def __init__(self) -> None:
        """Initialize the analyzer with compiled regex patterns."""
        # Pre-compile deflection patterns for efficiency
        self._compiled_deflection_patterns: List[Tuple[re.Pattern, str]] = [
            (re.compile(pattern, re.IGNORECASE), severity)
            for pattern, severity in self.DEFLECTION_PHRASES
        ]

        # Pre-compile query type patterns
        self._compiled_query_patterns: Dict[QueryType, List[re.Pattern]] = {
            qt: [re.compile(p, re.IGNORECASE) for p in patterns]
            for qt, patterns in self.QUERY_TYPE_PATTERNS.items()
        }

    def analyze(
        self,
        query: str,
        response: str,
        query_type: Optional[QueryType] = None,
        expected_elements: Optional[List[str]] = None,
    ) -> QualityAnalysis:
        """
        Analyze the quality of an AI response.

        Args:
            query: The original user query
            response: The AI's response text
            query_type: Optional explicit query type (auto-detected if not provided)
            expected_elements: Optional list of expected content elements

        Returns:
            QualityAnalysis with complete quality metrics
        """
        # Detect query type if not provided
        if query_type is None:
            query_type = self._detect_query_type(query)

        # Detect deflection phrases
        deflection_phrases, deflection_severity = self._detect_deflections(response)

        # Analyze content requirements
        present, missing = self._analyze_content(response, query_type, expected_elements)

        # Calculate content coverage
        total_requirements = len(present) + len(missing)
        content_coverage = len(present) / max(total_requirements, 1)

        # Check for structured data markers
        has_structured_data = self._has_structured_data(response)

        # Check for citations
        has_citations = self._has_citations(response)

        # Check for actionable info
        has_actionable_info = self._has_actionable_info(response)

        # Calculate base metrics
        response_length = len(response)
        word_count = len(response.split())

        # Determine category
        category = self._determine_category(
            response_length=response_length,
            deflection_severity=deflection_severity,
            content_coverage=content_coverage,
            query_type=query_type,
        )

        # Calculate score
        score = self._calculate_score(
            category=category,
            content_coverage=content_coverage,
            deflection_severity=deflection_severity,
            response_length=response_length,
            word_count=word_count,
            has_structured_data=has_structured_data,
            has_citations=has_citations,
            has_actionable_info=has_actionable_info,
            query_type=query_type,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            category=category,
            missing_elements=missing,
            deflection_phrases=deflection_phrases,
            response_length=response_length,
            query_type=query_type,
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            response_length=response_length,
            content_coverage=content_coverage,
            query_type=query_type,
        )

        return QualityAnalysis(
            score=score,
            category=category,
            confidence=confidence,
            query_type=query_type,
            missing_elements=missing,
            present_elements=present,
            content_coverage=content_coverage,
            deflection_phrases_found=deflection_phrases,
            deflection_severity=deflection_severity,
            response_length=response_length,
            word_count=word_count,
            has_structured_data=has_structured_data,
            has_citations=has_citations,
            has_actionable_info=has_actionable_info,
            recommendations=recommendations,
            query=query[:200],
            response_preview=response[:500],
        )

    def _detect_query_type(self, query: str) -> QueryType:
        """Detect the type of query based on patterns."""
        scores: Dict[QueryType, int] = {qt: 0 for qt in QueryType}

        for query_type, patterns in self._compiled_query_patterns.items():
            for pattern in patterns:
                if pattern.search(query):
                    scores[query_type] += 1

        # Get the type with highest score
        max_score = max(scores.values())
        if max_score > 0:
            for qt, score in scores.items():
                if score == max_score:
                    return qt

        return QueryType.GENERAL_FAQ

    def _detect_deflections(self, response: str) -> Tuple[List[str], str]:
        """
        Detect deflection phrases in the response.

        Returns:
            Tuple of (list of found phrases, severity level)
        """
        found_phrases: List[str] = []
        severities: Set[str] = set()

        for pattern, severity in self._compiled_deflection_patterns:
            matches = pattern.findall(response)
            if matches:
                found_phrases.extend(matches if isinstance(matches[0], str) else [m[0] for m in matches])
                severities.add(severity)

        # Determine overall severity
        if "critical" in severities:
            return found_phrases, "critical"
        elif "major" in severities:
            return found_phrases, "major"
        elif "minor" in severities:
            return found_phrases, "minor"
        return found_phrases, "none"

    def _analyze_content(
        self,
        response: str,
        query_type: QueryType,
        expected_elements: Optional[List[str]] = None,
    ) -> Tuple[List[str], List[str]]:
        """
        Analyze content against requirements.

        Returns:
            Tuple of (present elements, missing elements)
        """
        present: List[str] = []
        missing: List[str] = []

        # Get requirements for this query type
        requirements = self.CONTENT_REQUIREMENTS.get(query_type, [])

        for req in requirements:
            found = False
            flags = 0 if req.case_sensitive else re.IGNORECASE

            for pattern in req.patterns:
                try:
                    if re.search(pattern, response, flags):
                        found = True
                        break
                except re.error:
                    logger.warning(f"Invalid regex pattern: {pattern}")
                    continue

            if found:
                present.append(req.name)
            elif req.required:
                missing.append(req.name)

        # Add custom expected elements
        if expected_elements:
            for element in expected_elements:
                if element.lower() in response.lower():
                    if element not in present:
                        present.append(element)
                else:
                    if element not in missing:
                        missing.append(element)

        return present, missing

    def _has_structured_data(self, response: str) -> bool:
        """Check if response contains structured data (lists, tables, etc.)."""
        indicators = [
            r"^\s*[-*]\s+",  # Bullet points
            r"^\s*\d+\.\s+",  # Numbered lists
            r"\|.*\|",  # Tables
            r"\*\*[^*]+\*\*\s*:",  # Bold headers with colon: **Header**: or **Header:**
            r"\*\*[^*]+:\*\*",  # Bold with internal colon: **Header:**
            r"#{1,3}\s+",  # Markdown headers
        ]

        for indicator in indicators:
            if re.search(indicator, response, re.MULTILINE):
                return True
        return False

    def _has_citations(self, response: str) -> bool:
        """Check if response contains citations or source references."""
        citation_patterns = [
            r"source:",
            r"according to",
            r"based on",
            r"work programme",
            r"regulation",
            r"article\s+\d+",
            r"horizon europe",
        ]

        for pattern in citation_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        return False

    def _has_actionable_info(self, response: str) -> bool:
        """Check if response contains actionable information."""
        actionable_patterns = [
            r"https?://",  # Links
            r"apply\s+(at|here|now|via)",  # Application instructions
            r"deadline",  # Deadline info
            r"step\s+\d+",  # Step-by-step
            r"contact",  # Contact information
            r"submit",  # Submission info
        ]

        for pattern in actionable_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        return False

    def _determine_category(
        self,
        response_length: int,
        deflection_severity: str,
        content_coverage: float,
        query_type: QueryType,
    ) -> ResponseCategory:
        """Determine the response category based on analysis."""
        min_length = self.MIN_RESPONSE_LENGTHS.get(query_type, 100)

        # Empty responses
        if response_length < 50:
            return ResponseCategory.EMPTY

        # Critical deflection
        if deflection_severity == "critical":
            return ResponseCategory.DEFLECTION

        # Too short responses
        if response_length < min_length:
            if deflection_severity in ("major", "minor"):
                return ResponseCategory.DEFLECTION
            return ResponseCategory.EMPTY

        # Deflection check
        if deflection_severity == "major":
            return ResponseCategory.DEFLECTION

        # Content coverage check
        if content_coverage >= 0.8:
            return ResponseCategory.COMPLETE
        elif content_coverage >= 0.5:
            if deflection_severity == "minor":
                return ResponseCategory.PARTIAL
            return ResponseCategory.PARTIAL
        elif content_coverage >= 0.3:
            return ResponseCategory.PARTIAL
        else:
            if deflection_severity != "none":
                return ResponseCategory.DEFLECTION
            return ResponseCategory.PARTIAL

    def _calculate_score(
        self,
        category: ResponseCategory,
        content_coverage: float,
        deflection_severity: str,
        response_length: int,
        word_count: int,
        has_structured_data: bool,
        has_citations: bool,
        has_actionable_info: bool,
        query_type: QueryType,
    ) -> int:
        """Calculate the overall quality score (0-100)."""
        # Base scores by category
        category_base_scores = {
            ResponseCategory.COMPLETE: 85,
            ResponseCategory.PARTIAL: 60,
            ResponseCategory.DEFLECTION: 20,
            ResponseCategory.EMPTY: 10,
            ResponseCategory.ERROR: 5,
        }

        score = category_base_scores.get(category, 50)

        # Adjust based on content coverage
        score += int(content_coverage * 15)

        # Penalties for deflection
        deflection_penalties = {
            "none": 0,
            "minor": -5,
            "major": -15,
            "critical": -25,
        }
        score += deflection_penalties.get(deflection_severity, 0)

        # Bonuses for quality indicators
        if has_structured_data:
            score += 5
        if has_citations:
            score += 3
        if has_actionable_info:
            score += 5

        # Length bonus/penalty
        min_length = self.MIN_RESPONSE_LENGTHS.get(query_type, 100)
        if response_length >= min_length * 2:
            score += 3
        elif response_length < min_length // 2:
            score -= 10

        # Ensure score is within bounds
        return max(0, min(100, score))

    def _generate_recommendations(
        self,
        category: ResponseCategory,
        missing_elements: List[str],
        deflection_phrases: List[str],
        response_length: int,
        query_type: QueryType,
    ) -> List[str]:
        """Generate recommendations for improvement."""
        recommendations: List[str] = []

        if category == ResponseCategory.DEFLECTION:
            recommendations.append(
                "Response contains deflection phrases and provides no useful information. "
                "The system should attempt alternative search strategies or provide partial results."
            )

        if category == ResponseCategory.EMPTY:
            recommendations.append(
                f"Response is too short ({response_length} chars). "
                f"Minimum expected: {self.MIN_RESPONSE_LENGTHS.get(query_type, 100)} chars."
            )

        if missing_elements:
            recommendations.append(
                f"Missing required content: {', '.join(missing_elements)}. "
                "Ensure these elements are present in the response."
            )

        if deflection_phrases:
            recommendations.append(
                f"Deflection phrases detected: {', '.join(deflection_phrases[:3])}. "
                "Avoid these non-helpful patterns."
            )

        if category == ResponseCategory.PARTIAL:
            recommendations.append(
                "Response is partial. Consider enriching with additional data sources "
                "or providing more specific information."
            )

        return recommendations

    def _calculate_confidence(
        self,
        response_length: int,
        content_coverage: float,
        query_type: QueryType,
    ) -> float:
        """Calculate confidence in the analysis."""
        confidence = 0.8  # Base confidence

        # Higher confidence for longer responses (more data to analyze)
        if response_length > 500:
            confidence += 0.1
        elif response_length < 100:
            confidence -= 0.2

        # Higher confidence when we have clear content matches
        if content_coverage > 0.7 or content_coverage < 0.3:
            confidence += 0.1

        # General FAQ queries are harder to assess
        if query_type == QueryType.GENERAL_FAQ:
            confidence -= 0.1

        return max(0.1, min(1.0, confidence))

    def is_acceptable(self, analysis: QualityAnalysis, min_score: int = 75) -> bool:
        """
        Check if a response meets minimum quality standards.

        Args:
            analysis: The quality analysis to check
            min_score: Minimum acceptable score (default 75)

        Returns:
            True if response is acceptable, False otherwise
        """
        # Immediate fail conditions
        if analysis.category == ResponseCategory.DEFLECTION:
            return False
        if analysis.category == ResponseCategory.EMPTY:
            return False
        if analysis.deflection_severity in ("critical", "major"):
            return False

        return analysis.score >= min_score

    def format_report(self, analysis: QualityAnalysis) -> str:
        """Format analysis as a human-readable report."""
        lines = [
            f"Response Quality Report",
            f"=" * 50,
            f"Score: {analysis.score}/100 ({analysis.category.value})",
            f"Query Type: {analysis.query_type.value}",
            f"Confidence: {analysis.confidence:.0%}",
            "",
            f"Content Analysis:",
            f"  - Coverage: {analysis.content_coverage:.0%}",
            f"  - Present: {', '.join(analysis.present_elements) or 'None'}",
            f"  - Missing: {', '.join(analysis.missing_elements) or 'None'}",
            "",
            f"Quality Indicators:",
            f"  - Length: {analysis.response_length} chars, {analysis.word_count} words",
            f"  - Structured Data: {'Yes' if analysis.has_structured_data else 'No'}",
            f"  - Citations: {'Yes' if analysis.has_citations else 'No'}",
            f"  - Actionable Info: {'Yes' if analysis.has_actionable_info else 'No'}",
            "",
            f"Deflection Analysis:",
            f"  - Severity: {analysis.deflection_severity}",
        ]

        if analysis.deflection_phrases_found:
            lines.append(
                f"  - Phrases: {', '.join(analysis.deflection_phrases_found[:5])}"
            )

        if analysis.recommendations:
            lines.append("")
            lines.append("Recommendations:")
            for rec in analysis.recommendations:
                lines.append(f"  - {rec}")

        return "\n".join(lines)
