"""Quality assurance services for AI response validation.

This package provides tools for analyzing and validating AI response quality,
including deflection detection, content validation, and quality scoring.

Example usage:
    from app.services.quality import ResponseQualityAnalyzer, QualityAnalysis

    analyzer = ResponseQualityAnalyzer()
    analysis = analyzer.analyze(
        query="Tell me about HORIZON-CL5-2026-D3-01",
        response="I found the call HORIZON-CL5-2026-D3-01..."
    )

    if not analysis.is_acceptable(min_score=75):
        print(f"Response quality issues: {analysis.recommendations}")
"""

from app.services.quality.response_quality_analyzer import (
    QualityAnalysis,
    QueryType,
    ResponseCategory,
    ResponseQualityAnalyzer,
    get_analyzer,
)

__all__ = [
    "get_analyzer",
    "QualityAnalysis",
    "QueryType",
    "ResponseCategory",
    "ResponseQualityAnalyzer",
]
