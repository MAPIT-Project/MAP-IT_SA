"""
Response Quality Analyzer for AI Response Validation.

This module provides comprehensive analysis of AI responses to ensure:
- Responses contain actionable, specific information
- No deflection phrases that avoid answering the question
- Tool results are properly synthesized into responses
- All required elements are present for specific query types
"""

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResponseCategory(str, Enum):
    """Category classification for AI responses."""

    COMPLETE = "complete"      # Response fully addresses the query
    PARTIAL = "partial"        # Response partially addresses the query
    DEFLECTION = "deflection"  # Response avoids answering with vague phrases
    EMPTY = "empty"            # Response has no substantive content
    ERROR = "error"            # Response indicates an error occurred


class QualityAnalysis(BaseModel):
    """Result of analyzing an AI response for quality."""

    score: int = Field(..., ge=0, le=100, description="Quality score 0-100")
    category: ResponseCategory = Field(..., description="Response category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence")
    missing_elements: list[str] = Field(
        default_factory=list, description="Required elements not found"
    )
    deflection_phrases_found: list[str] = Field(
        default_factory=list, description="Deflection phrases detected"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Improvement suggestions"
    )
    content_length: int = Field(default=0, description="Response length")
    specificity_indicators: dict[str, bool] = Field(
        default_factory=dict, description="Content indicators"
    )


class ResponseQualityAnalyzer:
    """
    Comprehensive analyzer for AI response quality.

    This analyzer detects:
    - Deflection phrases that avoid answering
    - Missing required content elements
    - Insufficient response length for substantive queries
    - Lack of specificity in responses

    Usage:
        analyzer = ResponseQualityAnalyzer()
        analysis = analyzer.analyze(query="Find hydrogen calls", response="I found 15 calls...")
        if analysis.score < 75:
            pytest.fail(f"Response quality too low: {analysis.score}")
    """

    # Deflection phrases that indicate a low-quality response
    DEFLECTION_PHRASES = [
        "could not find",
        "couldn't find",
        "no information available",
        "please try a more specific",
        "i am not sure",
        "i'm not sure",
        "not sure about",
        "i don't have",
        "i do not have",
        "unable to retrieve",
        "no results found",
        "try again later",
        "could not extract",
        "couldn't extract",
        "found some information but",
        "couldn't find",
        "no data available",
        "unable to find",
        "cannot provide",
        "don't have access to",
        "do not have access to",
        "unfortunately, i",
        "i apologize, but",
        "i'm sorry, but",
        "i'm unable to",
        "i am unable to",
        "not able to provide",
        "cannot answer that",
        "cannot retrieve",
        "failed to find",
        "failed to retrieve",
        "error occurred while",
        "something went wrong",
        "an error happened",
        "encountered an issue",
        "having trouble",
        "experiencing difficulties",
        "technical difficulties",
        "service unavailable",
        "you might want to check",
        "check the portal",
    ]

    # Required elements for specific query types
    CALL_INFO_REQUIRED_ELEMENTS = [
        "call_id",
        "deadline",
        "budget",
        "type",
        "status",
        "programme",
    ]

    PROJECT_INFO_REQUIRED_ELEMENTS = [
        "acronym",
        "funding",
        "participants",
        "objectives",
    ]

    COMPARISON_REQUIRED_ELEMENTS = [
        "first_entity",
        "second_entity",
        "comparison_metrics",
        "conclusion",
    ]

    # Minimum response lengths for different query types
    MIN_LENGTHS = {
        "simple_faq": 100,
        "call_search": 200,
        "project_search": 200,
        "comparison": 300,
        "analysis": 400,
        "default": 150,
    }

    def __init__(self, strict_mode: bool = True):
        """
        Initialize the analyzer.

        Args:
            strict_mode: If True, apply stricter quality thresholds
        """
        self.strict_mode = strict_mode

    def analyze(
        self,
        query: str,
        response: str,
        tool_results: dict[str, Any] | None = None,
        expected_elements: list[str] | None = None,
        query_type: str | None = None,
    ) -> QualityAnalysis:
        """
        Analyze an AI response for quality.

        Args:
            query: The original user query
            response: The AI response text
            tool_results: Optional dict of tool execution results
            expected_elements: Optional list of elements expected in response
            query_type: Type of query (call_search, project_search, etc.)

        Returns:
            QualityAnalysis with score, category, and recommendations
        """
        response_lower = response.lower()
        content_length = len(response.strip())

        # Detect deflection phrases
        deflection_phrases_found = self._detect_deflection_phrases(response_lower)

        # Infer query type if not provided
        if not query_type:
            query_type = self._infer_query_type(query)

        # Get expected elements based on query type
        if not expected_elements:
            expected_elements = self._get_expected_elements(query_type)

        # Check for missing elements
        missing_elements = self._check_missing_elements(response, expected_elements)

        # Analyze specificity
        specificity_indicators = self._check_specificity(response, query_type)

        # Calculate score
        score = self._calculate_score(
            content_length=content_length,
            deflection_count=len(deflection_phrases_found),
            missing_count=len(missing_elements),
            expected_count=len(expected_elements),
            specificity_indicators=specificity_indicators,
            query_type=query_type,
            tool_results=tool_results,
        )

        # Determine category
        category = self._determine_category(
            score=score,
            content_length=content_length,
            deflection_count=len(deflection_phrases_found),
            has_tool_error=self._has_tool_error(tool_results),
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            missing_elements=missing_elements,
            deflection_phrases_found=deflection_phrases_found,
            content_length=content_length,
            query_type=query_type,
            specificity_indicators=specificity_indicators,
        )

        # Calculate confidence based on how certain we are about the analysis
        confidence = self._calculate_confidence(
            content_length=content_length,
            query_type=query_type,
            has_expected_elements=len(expected_elements) > 0,
        )

        return QualityAnalysis(
            score=score,
            category=category,
            confidence=confidence,
            missing_elements=missing_elements,
            deflection_phrases_found=deflection_phrases_found,
            recommendations=recommendations,
            content_length=content_length,
            specificity_indicators=specificity_indicators,
        )

    def _detect_deflection_phrases(self, response_lower: str) -> list[str]:
        """Detect deflection phrases in the response."""
        found = []
        for phrase in self.DEFLECTION_PHRASES:
            if phrase in response_lower:
                found.append(phrase)
        return found

    def _infer_query_type(self, query: str) -> str:
        """Infer query type from the query text."""
        query_lower = query.lower()

        call_keywords = ["call", "funding opportunity", "deadline", "topic code", "horizon-"]
        if any(kw in query_lower for kw in call_keywords):
            return "call_search"

        project_keywords = ["project", "funded", "cordis", "similar projects"]
        if any(kw in query_lower for kw in project_keywords):
            return "project_search"

        comparison_keywords = ["compare", "versus", "vs", "difference between", "vs."]
        if any(kw in query_lower for kw in comparison_keywords):
            return "comparison"

        if any(kw in query_lower for kw in ["budget", "benchmark", "consortium", "partners"]):
            return "proposal_support"

        if any(kw in query_lower for kw in ["what is", "how does", "can i", "eligibility"]):
            return "simple_faq"

        if any(kw in query_lower for kw in ["analyze", "trend", "statistics", "success rate"]):
            return "analysis"

        return "default"

    def _get_expected_elements(self, query_type: str) -> list[str]:
        """Get expected elements based on query type."""
        elements_map = {
            "call_search": ["call_id", "deadline", "type", "status"],
            "project_search": ["project_name", "funding_amount"],
            "comparison": ["comparison_point", "metric"],
            "proposal_support": ["data_point", "recommendation"],
            "analysis": ["statistic", "trend"],
            "simple_faq": ["answer"],
            "default": ["answer"],
        }
        return elements_map.get(query_type, ["answer"])

    def _check_missing_elements(self, response: str, expected_elements: list[str]) -> list[str]:
        """Check for missing required elements in response."""
        missing = []
        response_lower = response.lower()

        # Element detection patterns
        # fmt: off
        element_patterns = {
            "call_id": r"horizon[-\s]?\w+[-\s]?\d+[-\s]?\w*[-\s]?\d*",
            "deadline": (
                r"\d{1,2}[\s/\-]+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
                r"[\s/\-]+\d{4}|\d{4}-\d{2}-\d{2}"
            ),
            "type": r"\b(ria|ia|csa|cofund|erc|msca|lump\s*sum)\b",
            "status": r"\b(open|upcoming|closed|published)\b",
            "budget": (
                r"(?:eur|\u20ac|million|m\s*eur|€)\s*\d+|"
                r"\d+(?:\.\d+)?\s*(?:million|m\s*eur|eur|€)"
            ),
            "programme": r"cluster\s*\d|horizon\s*europe|eic|erc|msca",
            "project_name": r"[A-Z][A-Z0-9\-]{2,}",  # Acronyms
            "funding_amount": r"(?:eur|\u20ac)\s*[\d,]+|\d+(?:\.\d+)?\s*(?:million|eur)",
            "comparison_point": r"compare|versus|difference|higher|lower|better|worse",
            "metric": r"\d+\s*%|success\s*rate|funding|budget|partners",
            "data_point": r"\d+(?:\.\d+)?|average|median|typical",
            "recommendation": r"recommend|suggest|advise|should|consider",
            "statistic": r"\d+\s*%|\d+\s*projects?|\d+\s*calls?",
            "trend": r"increas|decreas|grow|decline|stable|rising|falling",
            "answer": r".{50,}",  # At least some substantive content
        }
        # fmt: on

        for element in expected_elements:
            pattern = element_patterns.get(element, r".{10,}")
            if not re.search(pattern, response_lower, re.IGNORECASE):
                missing.append(element)

        return missing

    def _check_specificity(self, response: str, query_type: str) -> dict[str, bool]:
        """Check for specific content indicators."""
        indicators = {
            "has_numbers": bool(re.search(r"\d+", response)),
            "has_dates": bool(re.search(r"\d{4}|\d{1,2}[\/\-]\d{1,2}", response)),
            "has_percentages": bool(re.search(r"\d+\s*%", response)),
            "has_currency": bool(re.search(r"(?:EUR|€|\$)\s*[\d,]+", response, re.IGNORECASE)),
            "has_call_ids": bool(re.search(r"HORIZON-[A-Z0-9\-]+", response, re.IGNORECASE)),
            "has_project_acronyms": bool(re.search(r"\b[A-Z][A-Z0-9\-]{2,}\b", response)),
            # Organization names: match known research orgs, universities, suffixes
            "has_organization_names": bool(re.search(
                r"\b(?:University|Institute|Research|Centre|Center|GmbH|Ltd|Inc|"
                r"Fraunhofer|CNRS|CEA|TNO|DLR|CSIC|VTT|SINTEF|Helmholtz|"
                r"Max\s*Planck|ETH|EPFL|TU\s+\w+|MIT|Stanford)\b",
                response, re.IGNORECASE)),
            "has_country_codes": bool(re.search(r"\b[A-Z]{2}\b", response)),
            "has_structured_data": bool(re.search(r"[\*\-\•]|\d+\.\s+", response)),
            "has_links": bool(re.search(r"https?://|www\.", response)),
        }

        # Query-type specific indicators
        if query_type == "call_search":
            resp_lower = response.lower()
            indicators["has_apply_link"] = "apply" in resp_lower or "ec.europa.eu" in resp_lower
        elif query_type == "project_search":
            resp_lower = response.lower()
            indicators["has_cordis_reference"] = "cordis" in resp_lower or "rcn" in resp_lower

        return indicators

    def _calculate_score(
        self,
        content_length: int,
        deflection_count: int,
        missing_count: int,
        expected_count: int,
        specificity_indicators: dict[str, bool],
        query_type: str,
        tool_results: dict[str, Any] | None,
    ) -> int:
        """Calculate quality score (0-100)."""
        score = 100

        # Penalty for deflection phrases (severe - each deflection is very bad)
        score -= deflection_count * 30

        # Penalty for missing elements
        if expected_count > 0:
            completeness_ratio = 1 - (missing_count / expected_count)
            score -= int((1 - completeness_ratio) * 30)

        # Penalty for short responses (stricter for empty/very short)
        min_length = self.MIN_LENGTHS.get(query_type, self.MIN_LENGTHS["default"])
        if content_length < 10:
            score -= 50  # Essentially empty
        elif content_length < 30:
            score -= 40  # Very short
        elif content_length < min_length:
            length_ratio = content_length / min_length
            score -= int((1 - length_ratio) * 25)

        # Bonus/penalty for specificity
        specificity_score = sum(1 for v in specificity_indicators.values() if v)
        specificity_ratio = specificity_score / max(len(specificity_indicators), 1)
        if specificity_ratio < 0.3:
            score -= 15  # Too vague
        elif specificity_ratio > 0.6:
            score += 5  # Good specificity

        # Penalty if tool results indicate failure
        if tool_results:
            tool_failed = any(
                not r.get("success", True)
                for r in tool_results.values()
                if isinstance(r, dict)
            )
            if tool_failed:
                score -= 10

        # Ensure score is in valid range
        return max(0, min(100, score))

    def _determine_category(
        self,
        score: int,
        content_length: int,
        deflection_count: int,
        has_tool_error: bool,
    ) -> ResponseCategory:
        """Determine response category based on analysis."""
        if has_tool_error:
            return ResponseCategory.ERROR

        if content_length < 20:
            return ResponseCategory.EMPTY

        # Any deflection phrase is concerning
        if deflection_count >= 1:
            return ResponseCategory.DEFLECTION

        if score >= 75:
            return ResponseCategory.COMPLETE
        elif score >= 50:
            return ResponseCategory.PARTIAL
        else:
            return ResponseCategory.DEFLECTION

    def _has_tool_error(self, tool_results: dict[str, Any] | None) -> bool:
        """Check if any tool returned an error."""
        if not tool_results:
            return False

        for result in tool_results.values():
            if isinstance(result, dict):
                if result.get("error") or not result.get("success", True):
                    return True

        return False

    def _generate_recommendations(
        self,
        missing_elements: list[str],
        deflection_phrases_found: list[str],
        content_length: int,
        query_type: str,
        specificity_indicators: dict[str, bool],
    ) -> list[str]:
        """Generate improvement recommendations."""
        recommendations = []

        if deflection_phrases_found:
            recommendations.append(
                f"Avoid deflection phrases: {', '.join(deflection_phrases_found[:3])}"
            )

        if missing_elements:
            recommendations.append(
                f"Include missing elements: {', '.join(missing_elements)}"
            )

        min_length = self.MIN_LENGTHS.get(query_type, self.MIN_LENGTHS["default"])
        if content_length < min_length:
            recommendations.append(
                f"Response too short ({content_length} chars). Minimum: {min_length} chars"
            )

        if not specificity_indicators.get("has_numbers"):
            recommendations.append("Add specific numbers/statistics for credibility")

        if query_type == "call_search" and not specificity_indicators.get("has_call_ids"):
            recommendations.append("Include call IDs (e.g., HORIZON-CL5-2026-D3-01)")

        if query_type == "call_search" and not specificity_indicators.get("has_apply_link"):
            recommendations.append("Include Apply link or portal URL")

        return recommendations

    def _calculate_confidence(
        self,
        content_length: int,
        query_type: str,
        has_expected_elements: bool,
    ) -> float:
        """Calculate confidence in the analysis."""
        confidence = 0.8  # Base confidence

        # More content means more confident analysis
        if content_length > 500:
            confidence += 0.1
        elif content_length < 50:
            confidence -= 0.2

        # Known query types give higher confidence
        if query_type in ["call_search", "project_search", "comparison"]:
            confidence += 0.05

        # Having expected elements to check increases confidence
        if has_expected_elements:
            confidence += 0.05

        return max(0.0, min(1.0, confidence))

    def validate_tool_results(
        self,
        tool_name: str,
        tool_result: dict[str, Any],
    ) -> QualityAnalysis:
        """
        Validate a specific tool's results.

        Args:
            tool_name: Name of the tool
            tool_result: The tool's result dictionary

        Returns:
            QualityAnalysis for the tool result
        """
        if not tool_result:
            return QualityAnalysis(
                score=0,
                category=ResponseCategory.EMPTY,
                confidence=1.0,
                missing_elements=["tool_result"],
                recommendations=["Tool returned no results"],
            )

        if not tool_result.get("success", True):
            error_msg = tool_result.get("error", "Unknown error")
            return QualityAnalysis(
                score=0,
                category=ResponseCategory.ERROR,
                confidence=1.0,
                missing_elements=["successful_result"],
                recommendations=[f"Fix tool error: {error_msg}"],
            )

        # Tool-specific validation
        validators = {
            "get_budget_benchmark": self._validate_budget_benchmark,
            "find_experienced_partners": self._validate_partner_discovery,
            "get_consortium_patterns": self._validate_consortium_patterns,
            "search_funding_calls": self._validate_call_search,
            "search_projects": self._validate_project_search,
            "get_similar_funded_projects": self._validate_similar_projects,
            "analyze_call_history": self._validate_call_history,
        }

        validator = validators.get(tool_name)
        if validator:
            return validator(tool_result)

        # Generic validation
        return self._validate_generic_tool(tool_result)

    def _validate_budget_benchmark(self, result: dict[str, Any]) -> QualityAnalysis:
        """Validate budget benchmark tool results."""
        missing = []

        if "statistics" not in result:
            missing.append("statistics")
        else:
            stats = result["statistics"]
            if "projects_analyzed" not in stats:
                missing.append("projects_analyzed")
            if "total_eu_contribution" not in stats:
                missing.append("total_eu_contribution")

        if "recommendations" not in result:
            missing.append("recommendations")

        score = 100 - (len(missing) * 20)

        return QualityAnalysis(
            score=max(0, score),
            category=ResponseCategory.COMPLETE if score >= 75 else ResponseCategory.PARTIAL,
            confidence=0.95,
            missing_elements=missing,
            recommendations=[f"Add missing: {e}" for e in missing],
        )

    def _validate_partner_discovery(self, result: dict[str, Any]) -> QualityAnalysis:
        """Validate partner discovery tool results."""
        missing = []

        partners = result.get("experienced_partners") or result.get("partners")
        if not partners:
            missing.append("partners_list")
            missing.append("at_least_one_partner")
        elif len(partners) == 0:
            missing.append("at_least_one_partner")

        if "metadata" in result:
            metadata = result["metadata"]
            if "search_type" not in metadata:
                missing.append("search_type_metadata")

        # Each missing element costs 30 points
        score = 100 - (len(missing) * 30)

        return QualityAnalysis(
            score=max(0, score),
            category=ResponseCategory.COMPLETE if score >= 75 else ResponseCategory.PARTIAL,
            confidence=0.9,
            missing_elements=missing,
            recommendations=[f"Add missing: {e}" for e in missing],
        )

    def _validate_consortium_patterns(self, result: dict[str, Any]) -> QualityAnalysis:
        """Validate consortium patterns tool results."""
        missing = []

        if "consortium_size" not in result:
            missing.append("consortium_size")

        score = 100 - (len(missing) * 30)

        return QualityAnalysis(
            score=max(0, score),
            category=ResponseCategory.COMPLETE if score >= 75 else ResponseCategory.PARTIAL,
            confidence=0.9,
            missing_elements=missing,
            recommendations=[f"Add missing: {e}" for e in missing],
        )

    def _validate_call_search(self, result: dict[str, Any]) -> QualityAnalysis:
        """Validate call search results."""
        missing = []

        calls = result.get("calls", [])
        if not calls:
            missing.append("calls_list")
        else:
            # Check first call has required fields
            first_call = calls[0] if calls else {}
            for field in ["topic_code", "deadline_date", "title"]:
                if field not in first_call:
                    missing.append(f"call_{field}")

        score = 100 - (len(missing) * 20)

        return QualityAnalysis(
            score=max(0, score),
            category=ResponseCategory.COMPLETE if score >= 75 else ResponseCategory.PARTIAL,
            confidence=0.9,
            missing_elements=missing,
            recommendations=[f"Add missing: {e}" for e in missing],
        )

    def _validate_project_search(self, result: dict[str, Any]) -> QualityAnalysis:
        """Validate project search results."""
        missing = []

        projects = result.get("projects", [])
        if not projects:
            missing.append("projects_list")

        score = 100 - (len(missing) * 30)

        return QualityAnalysis(
            score=max(0, score),
            category=ResponseCategory.COMPLETE if score >= 75 else ResponseCategory.PARTIAL,
            confidence=0.9,
            missing_elements=missing,
            recommendations=[f"Add missing: {e}" for e in missing],
        )

    def _validate_similar_projects(self, result: dict[str, Any]) -> QualityAnalysis:
        """Validate similar projects tool results."""
        missing = []

        projects = result.get("similar_projects") or result.get("projects")
        if not projects:
            missing.append("similar_projects_list")

        score = 100 - (len(missing) * 30)

        return QualityAnalysis(
            score=max(0, score),
            category=ResponseCategory.COMPLETE if score >= 75 else ResponseCategory.PARTIAL,
            confidence=0.85,
            missing_elements=missing,
            recommendations=[f"Add missing: {e}" for e in missing],
        )

    def _validate_call_history(self, result: dict[str, Any]) -> QualityAnalysis:
        """Validate call history analysis results."""
        missing = []

        if "timeline" not in result and "trends" not in result:
            missing.append("timeline_or_trends")

        if "calls_analyzed" not in result and "projects_funded" not in result:
            missing.append("analysis_counts")

        score = 100 - (len(missing) * 25)

        return QualityAnalysis(
            score=max(0, score),
            category=ResponseCategory.COMPLETE if score >= 75 else ResponseCategory.PARTIAL,
            confidence=0.9,
            missing_elements=missing,
            recommendations=[f"Add missing: {e}" for e in missing],
        )

    def _validate_generic_tool(self, result: dict[str, Any]) -> QualityAnalysis:
        """Generic validation for unknown tools."""
        missing = []

        if not result.get("success", True):
            missing.append("success")

        # Check for any content
        has_content = any(
            key not in ["success", "tool_name", "error", "metadata"]
            for key in result.keys()
        )
        if not has_content:
            missing.append("result_content")

        score = 100 - (len(missing) * 40)

        return QualityAnalysis(
            score=max(0, score),
            category=ResponseCategory.COMPLETE if score >= 75 else ResponseCategory.PARTIAL,
            confidence=0.7,
            missing_elements=missing,
            recommendations=[f"Add missing: {e}" for e in missing],
        )
