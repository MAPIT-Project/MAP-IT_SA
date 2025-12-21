"""
Response Quality Analyzer

Analyzes AI responses to ensure they provide meaningful, actionable answers
rather than deflections or empty responses. This is critical for production
quality assurance.

Key capabilities:
- Detect deflection phrases that indicate non-answers
- Validate content requirements for different query types
- Score response quality on multiple dimensions
- Categorize responses for tracking and improvement
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ResponseCategory(str, Enum):
    """Categories for classifying AI response quality."""

    COMPLETE = "complete"  # Response has all expected elements
    PARTIAL = "partial"  # Response has some but not all expected elements
    DEFLECTION = "deflection"  # Response avoids answering with excuses
    EMPTY = "empty"  # Response has no meaningful content
    ERROR = "error"  # Response indicates an error occurred


@dataclass
class QualityAnalysis:
    """Results of analyzing a response's quality."""

    score: int  # 0-100 quality score
    category: ResponseCategory
    confidence: float  # 0-1 confidence in the analysis
    missing_elements: List[str]  # Expected elements not found
    deflection_phrases_found: List[str]  # Deflection phrases detected
    recommendations: List[str]  # Suggestions for improvement
    element_scores: Dict[str, float] = field(default_factory=dict)  # Per-element scores


@dataclass
class ContentRequirements:
    """Content requirements for a specific query type."""

    required_elements: List[str]  # Elements that must be present
    optional_elements: List[str] = field(default_factory=list)  # Nice to have
    min_response_length: int = 200  # Minimum character count
    min_elements_for_partial: int = 2  # Minimum for partial category
    min_elements_for_complete: int = 4  # Minimum for complete category


class ResponseQualityAnalyzer:
    """
    Analyzes AI responses for quality and completeness.

    Detects:
    - Deflection phrases that indicate the AI is avoiding an answer
    - Missing content elements expected for specific query types
    - Empty or near-empty responses
    - Error responses

    Provides:
    - Quality scores (0-100)
    - Category classifications
    - Actionable recommendations
    """

    # Deflection phrases that indicate non-answers (case insensitive)
    DEFLECTION_PHRASES: List[str] = [
        "could not find",
        "couldn't find",
        "no information available",
        "please try a more specific",
        "try a more specific",
        "i am not sure",
        "i'm not sure",
        "i do not have",
        "i don't have",
        "unable to retrieve",
        "no results found",
        "try again later",
        "could not extract specific details",
        "couldn't extract specific details",
        "found some information but",
        "i cannot find",
        "i can't find",
        "no data available",
        "data not available",
        "information not found",
        "details not available",
        "not enough information",
        "insufficient information",
        "i apologize but",
        "unfortunately, i cannot",
        "i'm unable to",
        "i am unable to",
        "no matching",
        "cannot determine",
        "can't determine",
        "unclear from the available",
        "not clear from",
        "beyond my current knowledge",
        "outside my knowledge",
        "i lack the information",
        "this information is not in",
    ]

    # Query type to content requirements mapping
    QUERY_REQUIREMENTS: Dict[str, ContentRequirements] = {
        "call_search": ContentRequirements(
            required_elements=[
                "call_id",
                "deadline",
                "budget",
                "type",
                "status",
                "title",
            ],
            optional_elements=["programme", "scope", "apply_link"],
            min_response_length=300,
            min_elements_for_partial=3,
            min_elements_for_complete=5,
        ),
        "call_specific": ContentRequirements(
            required_elements=[
                "call_id",
                "deadline",
                "budget",
                "type",
                "status",
                "scope",
            ],
            optional_elements=["eligibility", "apply_link", "programme"],
            min_response_length=400,
            min_elements_for_partial=4,
            min_elements_for_complete=5,
        ),
        "project_search": ContentRequirements(
            required_elements=[
                "project_name",
                "funding",
                "partners",
                "objective",
            ],
            optional_elements=["duration", "coordinator", "country", "cluster"],
            min_response_length=300,
            min_elements_for_partial=2,
            min_elements_for_complete=4,
        ),
        "comparison": ContentRequirements(
            required_elements=[
                "first_item",
                "second_item",
                "comparison_metric",
                "difference",
            ],
            optional_elements=["recommendation", "context", "source"],
            min_response_length=400,
            min_elements_for_partial=2,
            min_elements_for_complete=4,
        ),
        "partner_discovery": ContentRequirements(
            required_elements=[
                "organization_name",
                "country",
                "experience",
                "project_count",
            ],
            optional_elements=["expertise_area", "role", "collaboration_network"],
            min_response_length=300,
            min_elements_for_partial=2,
            min_elements_for_complete=4,
        ),
        "budget_benchmark": ContentRequirements(
            required_elements=[
                "average_budget",
                "budget_range",
                "consortium_size",
                "action_type",
            ],
            optional_elements=["percentiles", "org_type_breakdown", "recommendations"],
            min_response_length=300,
            min_elements_for_partial=2,
            min_elements_for_complete=4,
        ),
        "consortium_patterns": ContentRequirements(
            required_elements=[
                "partner_count",
                "country_count",
                "org_type_distribution",
            ],
            optional_elements=["coordinator_profile", "successful_templates"],
            min_response_length=300,
            min_elements_for_partial=2,
            min_elements_for_complete=3,
        ),
        "faq": ContentRequirements(
            required_elements=["answer", "explanation"],
            optional_elements=["source", "examples", "related_info"],
            min_response_length=150,
            min_elements_for_partial=1,
            min_elements_for_complete=2,
        ),
    }

    # Content detection patterns for each element type
    ELEMENT_PATTERNS: Dict[str, List[str]] = {
        "call_id": [
            r"HORIZON-[A-Z0-9-]+",
            r"call\s*(?:id|identifier)[:\s]+\w+",
            r"topic[:\s]+\w+",
        ],
        "deadline": [
            r"\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}",
            r"deadline[:\s]+[\w\s,]+\d{4}",
            r"\d{4}-\d{2}-\d{2}",
        ],
        "budget": [
            r"€\s*[\d.,]+\s*(?:million|m|billion|b)?",
            r"EUR\s*[\d.,]+\s*(?:million|m)?",
            r"budget[:\s]+[\d.,]+",
            r"[\d.,]+\s*(?:million|M)\s*(?:EUR|euros?)?",
        ],
        "type": [
            r"\bRIA\b",
            r"\bIA\b",
            r"\bCSA\b",
            r"\bCOFUND\b",
            r"\bERC\b",
            r"\bMSCA\b",
            r"research\s+and\s+innovation\s+action",
            r"innovation\s+action",
            r"coordination\s+and\s+support\s+action",
        ],
        "status": [
            r"(?:🟢|🟡|🔴)\s*(?:open|upcoming|closed)",
            r"\b(?:open|upcoming|closed|forthcoming)\b",
            r"status[:\s]+(?:open|upcoming|closed)",
        ],
        "title": [r".{20,}", r"\*\*.+\*\*"],  # Any substantial text or bold text
        "programme": [
            r"cluster\s*\d",
            r"horizon\s*europe",
            r"pillar\s*\d",
            r"EIC|ERC|MSCA",
        ],
        "scope": [r"scope[:\s].{50,}", r"objective[:\s].{50,}", r"focus[:\s].{30,}"],
        "apply_link": [r"https?://[^\s]+portal[^\s]*", r"apply[:\s]+http"],
        "project_name": [r"(?:project|acronym)[:\s]+\w+", r"\*\*[A-Z][A-Z0-9-]+\*\*"],
        "funding": [r"(?:funding|grant|contribution)[:\s]+[\d.,]+", r"€\s*[\d.,]+"],
        "partners": [
            r"\d+\s*partners?",
            r"consortium\s+of\s+\d+",
            r"participants?[:\s]+\d+",
        ],
        "objective": [r"objective[:\s].{30,}", r"aims?\s+to", r"goal[:\s].{30,}"],
        "duration": [r"\d+\s*months?", r"duration[:\s]+\d+"],
        "coordinator": [r"coordinator[:\s]+\w+", r"coordinated\s+by"],
        "country": [r"\b[A-Z]{2}\b", r"(?:Germany|France|Spain|Italy|Netherlands)"],
        "cluster": [r"cluster[:\s]*\d", r"CL[1-6]", r"CLUSTER-[1-6]"],
        "first_item": [r"EIC|ERC|RIA|IA|CSA", r"programme\s+\w+"],
        "second_item": [r"EIC|ERC|RIA|IA|CSA", r"programme\s+\w+"],
        "comparison_metric": [
            r"success\s+rate",
            r"funding",
            r"budget",
            r"average",
            r"difference",
        ],
        "difference": [r"\d+%?\s+(?:vs|versus|compared)", r"higher|lower|more|less"],
        "organization_name": [r"(?:university|institute|GmbH|Ltd|Inc)", r"\b[A-Z][a-z]+\s+[A-Z]"],
        "experience": [r"\d+\s+projects?", r"experience\s+in", r"track\s+record"],
        "project_count": [r"\d+\s+projects?", r"participated\s+in\s+\d+"],
        "expertise_area": [r"expertise\s+in", r"specializ", r"focus\s+on"],
        "role": [r"coordinator|partner|participant"],
        "collaboration_network": [r"network|collaborat", r"partners?"],
        "average_budget": [r"average[:\s]+[\d.,]+", r"avg[:\s]+€?\s*[\d.,]+"],
        "budget_range": [r"range[:\s]+[\d.,]+\s*[-–]\s*[\d.,]+", r"min[:\s]+[\d.,]+.*max"],
        "consortium_size": [
            r"\d+\s*partners?",
            r"consortium\s+size[:\s]+\d+",
            r"average\s+partners",
        ],
        "action_type": [r"\bRIA\b|\bIA\b|\bCSA\b"],
        "percentiles": [r"p\d{2}[:\s]+[\d.,]+", r"percentile"],
        "org_type_breakdown": [r"HES|REC|PRC|PUB|OTH", r"organization\s+type"],
        "recommendations": [r"recommend", r"suggest", r"consider"],
        "partner_count": [
            r"\d+\s*partners?",
            r"number\s+of\s+partners",
            r"average\s+partners[:\s]+[\d.]+",
        ],
        "country_count": [
            r"\d+\s*countries?",
            r"number\s+of\s+countries",
            r"average\s+countries[:\s]+[\d.]+",
        ],
        "org_type_distribution": [
            r"HES[:\s]+\d+%?",
            r"REC[:\s]+\d+%?",
            r"PRC[:\s]+\d+%?",
            r"Higher\s+Education[^:]*:\s*\d+%?",
            r"Research\s+Center[^:]*:\s*\d+%?",
            r"Private\s+Compan[^:]*:\s*\d+%?",
        ],
        "coordinator_profile": [r"coordinator", r"leading\s+org"],
        "successful_templates": [r"template|example|successful\s+project"],
        "answer": [r".{50,}"],  # Any substantial response
        "explanation": [r"because|therefore|this\s+means|explains?"],
        "source": [r"source[:\s]", r"according\s+to", r"based\s+on"],
        "examples": [r"example|for\s+instance|such\s+as"],
        "related_info": [r"also|additionally|furthermore|related"],
    }

    def __init__(self):
        """Initialize the analyzer."""
        # Compile deflection patterns for efficiency
        self._deflection_patterns = [
            re.compile(re.escape(phrase), re.IGNORECASE)
            for phrase in self.DEFLECTION_PHRASES
        ]

    def analyze(
        self,
        query: str,
        response: str,
        query_type: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
    ) -> QualityAnalysis:
        """
        Analyze the quality of an AI response.

        Args:
            query: The original user query
            response: The AI's response text
            query_type: Type of query (call_search, project_search, etc.)
                       If None, will be inferred from query
            tools_used: List of tools that were used to generate the response

        Returns:
            QualityAnalysis with score, category, and recommendations
        """
        if not response or not response.strip():
            return QualityAnalysis(
                score=0,
                category=ResponseCategory.EMPTY,
                confidence=1.0,
                missing_elements=["any_content"],
                deflection_phrases_found=[],
                recommendations=["The response is empty. Check tool execution."],
            )

        # Infer query type if not provided
        if query_type is None:
            query_type = self._infer_query_type(query)

        # Check for deflection phrases
        deflections = self._find_deflections(response)

        # Check response length
        response_length = len(response.strip())
        requirements = self.QUERY_REQUIREMENTS.get(
            query_type, self.QUERY_REQUIREMENTS["faq"]
        )

        # If short response with deflections, likely a deflection
        if response_length < 200 and deflections:
            return QualityAnalysis(
                score=max(0, 25 - len(deflections) * 5),
                category=ResponseCategory.DEFLECTION,
                confidence=0.9,
                missing_elements=requirements.required_elements.copy(),
                deflection_phrases_found=deflections,
                recommendations=[
                    "Response contains deflection phrases instead of actual content.",
                    "Verify that the tools returned data.",
                    "Consider refining the search parameters.",
                ],
            )

        # Check for required content elements
        element_scores, missing_elements = self._check_content_elements(
            response, requirements
        )

        # Calculate base score
        found_count = len(requirements.required_elements) - len(missing_elements)
        total_required = len(requirements.required_elements)
        content_score = (found_count / max(total_required, 1)) * 60  # 60% for content

        # Length score (20% weight)
        length_ratio = min(response_length / requirements.min_response_length, 1.0)
        length_score = length_ratio * 20

        # Deflection penalty (up to 20% reduction)
        deflection_penalty = min(len(deflections) * 5, 20)

        # Final score
        score = int(content_score + length_score - deflection_penalty + 20)  # Base 20
        score = max(0, min(100, score))

        # Determine category
        if deflections and score < 50:
            category = ResponseCategory.DEFLECTION
        elif found_count >= requirements.min_elements_for_complete:
            category = ResponseCategory.COMPLETE
        elif found_count >= requirements.min_elements_for_partial:
            category = ResponseCategory.PARTIAL
        elif response_length < 100:
            category = ResponseCategory.EMPTY
        else:
            category = ResponseCategory.PARTIAL

        # Generate recommendations
        recommendations = self._generate_recommendations(
            missing_elements, deflections, response_length, requirements, query_type
        )

        # Calculate confidence based on how clear-cut the analysis is
        confidence = self._calculate_confidence(
            score, deflections, found_count, total_required
        )

        return QualityAnalysis(
            score=score,
            category=category,
            confidence=confidence,
            missing_elements=missing_elements,
            deflection_phrases_found=deflections,
            recommendations=recommendations,
            element_scores=element_scores,
        )

    def _infer_query_type(self, query: str) -> str:
        """Infer the query type from the query text."""
        query_lower = query.lower()

        if any(
            kw in query_lower for kw in ["horizon-", "call id", "topic", "tell me about"]
        ):
            return "call_specific"
        if any(kw in query_lower for kw in ["find call", "search call", "funding call"]):
            return "call_search"
        if any(kw in query_lower for kw in ["project", "funded", "cordis"]):
            return "project_search"
        if any(kw in query_lower for kw in ["compare", "vs", "versus", "difference"]):
            return "comparison"
        # Check consortium patterns BEFORE partner_discovery (more specific)
        if any(
            kw in query_lower
            for kw in ["consortium pattern", "consortium size", "how many partners"]
        ):
            return "consortium_patterns"
        if any(kw in query_lower for kw in ["partner", "organization"]):
            return "partner_discovery"
        if any(kw in query_lower for kw in ["budget", "cost", "funding amount"]):
            return "budget_benchmark"

        return "faq"

    def _find_deflections(self, response: str) -> List[str]:
        """Find deflection phrases in the response."""
        found = []
        response_lower = response.lower()

        for phrase in self.DEFLECTION_PHRASES:
            if phrase.lower() in response_lower:
                found.append(phrase)

        return found

    def _check_content_elements(
        self, response: str, requirements: ContentRequirements
    ) -> tuple[Dict[str, float], List[str]]:
        """
        Check for required content elements in the response.

        Returns:
            Tuple of (element_scores dict, missing_elements list)
        """
        element_scores: Dict[str, float] = {}
        missing_elements: List[str] = []

        for element in requirements.required_elements:
            patterns = self.ELEMENT_PATTERNS.get(element, [])
            found = False

            for pattern in patterns:
                try:
                    if re.search(pattern, response, re.IGNORECASE):
                        found = True
                        break
                except re.error:
                    # Invalid regex, skip
                    continue

            if found:
                element_scores[element] = 1.0
            else:
                element_scores[element] = 0.0
                missing_elements.append(element)

        return element_scores, missing_elements

    def _generate_recommendations(
        self,
        missing_elements: List[str],
        deflections: List[str],
        response_length: int,
        requirements: ContentRequirements,
        query_type: str,
    ) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        if deflections:
            recommendations.append(
                f"Remove deflection phrases: {', '.join(deflections[:3])}"
            )

        if missing_elements:
            recommendations.append(
                f"Add missing information: {', '.join(missing_elements[:5])}"
            )

        if response_length < requirements.min_response_length:
            recommendations.append(
                f"Expand response (currently {response_length} chars, "
                f"recommended min: {requirements.min_response_length})"
            )

        if not recommendations:
            recommendations.append("Response meets quality standards.")

        return recommendations

    def _calculate_confidence(
        self,
        score: int,
        deflections: List[str],
        found_count: int,
        total_required: int,
    ) -> float:
        """Calculate confidence in the analysis."""
        # High confidence if clearly good or clearly bad
        if score >= 80 or score <= 30:
            return 0.95

        # High confidence if many deflections found
        if len(deflections) >= 2:
            return 0.9

        # Medium confidence for middle-ground cases
        if found_count == 0 or found_count == total_required:
            return 0.85

        return 0.75

    def validate_call_response(
        self, query: str, response: str, expected_call_id: Optional[str] = None
    ) -> QualityAnalysis:
        """
        Specialized validation for call-related responses.

        Args:
            query: The original query
            response: The AI response
            expected_call_id: If known, the specific call ID that should be mentioned

        Returns:
            QualityAnalysis with call-specific validation
        """
        analysis = self.analyze(query, response, query_type="call_specific")

        # Additional check: if we expected a specific call ID, verify it's mentioned
        if expected_call_id:
            if expected_call_id.lower() not in response.lower():
                analysis.missing_elements.append(f"expected_call_id:{expected_call_id}")
                analysis.score = max(0, analysis.score - 15)
                analysis.recommendations.insert(
                    0, f"Response should mention the requested call: {expected_call_id}"
                )

        return analysis

    def validate_comparison_response(
        self,
        query: str,
        response: str,
        items_to_compare: Optional[List[str]] = None,
    ) -> QualityAnalysis:
        """
        Specialized validation for comparison responses.

        Args:
            query: The original query
            response: The AI response
            items_to_compare: List of items that should be compared

        Returns:
            QualityAnalysis with comparison-specific validation
        """
        analysis = self.analyze(query, response, query_type="comparison")

        if items_to_compare:
            response_lower = response.lower()
            for item in items_to_compare:
                if item.lower() not in response_lower:
                    analysis.missing_elements.append(f"comparison_item:{item}")
                    analysis.score = max(0, analysis.score - 10)
                    analysis.recommendations.insert(
                        0, f"Response should mention '{item}' in the comparison"
                    )

        return analysis

    def get_requirements_for_query_type(self, query_type: str) -> ContentRequirements:
        """Get content requirements for a specific query type."""
        return self.QUERY_REQUIREMENTS.get(
            query_type, self.QUERY_REQUIREMENTS["faq"]
        )

    @staticmethod
    def get_supported_query_types() -> List[str]:
        """Get list of supported query types."""
        return list(ResponseQualityAnalyzer.QUERY_REQUIREMENTS.keys())


def create_quality_analyzer() -> ResponseQualityAnalyzer:
    """Factory function to create a quality analyzer instance."""
    return ResponseQualityAnalyzer()
