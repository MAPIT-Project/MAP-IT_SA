# Task 07: Semantic Benchmarking

> **Priority:** P1 (Core Value)
> **Estimated Effort:** 4-6 hours
> **Dependencies:** Task 05 (Learning Service), Task 06 (Populate Examples)
> **Status:** Not Started

---

## Problem Statement

Users write proposal sections but have no way to know how their content compares to successfully funded proposals. They need objective, data-driven feedback on how their writing stacks up.

### Current State
- User writes a section
- Quality Improver gives generic heuristic feedback
- No comparison to actual funded proposals
- No quantitative benchmarking

### Target State
- User writes a section
- System finds 5 most similar funded proposals
- Provides similarity score (0-100%)
- Shows what funded proposals did differently
- Highlights gaps and strengths relative to benchmark

---

## Implementation Plan

### Step 1: Create Semantic Benchmarking Service

**File:** `app/services/proposal_writing/semantic_benchmarking.py`

```python
"""
Semantic Benchmarking Service

Compares user-written content against successfully funded proposals
to provide data-driven quality assessment and improvement suggestions.
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from app.services.database import get_db_connection
from app.services.embedding.embedding_service import EmbeddingService
from app.services.proposal_writing.proposal_ai_service import ProposalAIService

logger = logging.getLogger(__name__)


class BenchmarkDimension(str, Enum):
    """Dimensions for benchmarking analysis."""
    OVERALL_SIMILARITY = "overall_similarity"
    TECHNICAL_DEPTH = "technical_depth"
    IMPACT_CLARITY = "impact_clarity"
    METHODOLOGY_RIGOR = "methodology_rigor"
    INNOVATION_CLAIMS = "innovation_claims"
    EU_ALIGNMENT = "eu_alignment"


@dataclass
class BenchmarkExample:
    """A funded example used for benchmarking."""
    project_id: str
    project_acronym: str
    content: str
    cluster: Optional[str]
    action_type: Optional[str]
    total_cost: Optional[float]
    similarity_score: float
    relevant_excerpts: List[str] = field(default_factory=list)


@dataclass
class DimensionScore:
    """Score for a single benchmarking dimension."""
    dimension: BenchmarkDimension
    score: float  # 0-100
    benchmark_avg: float  # Average score of benchmark examples
    gap: float  # Difference from benchmark
    explanation: str
    improvement_hint: str


@dataclass
class BenchmarkResult:
    """Complete benchmarking result."""
    user_content: str
    section_type: str
    cluster: Optional[str]

    # Overall metrics
    overall_similarity: float  # 0-100
    percentile_rank: int  # What % of funded proposals is this better than

    # Dimension breakdown
    dimension_scores: List[DimensionScore]

    # Benchmark examples
    top_examples: List[BenchmarkExample]

    # Insights
    key_strengths: List[str]
    key_gaps: List[str]
    specific_suggestions: List[str]

    # Statistics
    examples_compared: int
    avg_funded_similarity: float


class SemanticBenchmarkingService:
    """
    Service for benchmarking user content against funded proposals.

    Uses semantic similarity and LLM analysis to provide detailed
    comparison metrics and actionable improvement suggestions.
    """

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.ai_service = ProposalAIService()

    async def benchmark_content(
        self,
        content: str,
        section_type: str,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        num_examples: int = 5
    ) -> BenchmarkResult:
        """
        Benchmark user content against funded proposals.

        Args:
            content: User-written proposal content
            section_type: Type of section (excellence_objectives, impact_expected, etc.)
            cluster: HE cluster to filter examples (optional)
            action_type: Action type to filter examples (optional)
            num_examples: Number of benchmark examples to use

        Returns:
            Comprehensive benchmark result with scores and suggestions
        """
        logger.info(f"Benchmarking content for section_type={section_type}, cluster={cluster}")

        # Step 1: Get user content embedding
        user_embedding = await self.embedding_service.embed_text(content)

        # Step 2: Find similar funded examples
        examples = await self._find_benchmark_examples(
            user_embedding=user_embedding,
            section_type=section_type,
            cluster=cluster,
            action_type=action_type,
            limit=num_examples
        )

        if not examples:
            logger.warning("No benchmark examples found")
            return self._create_empty_result(content, section_type, cluster)

        # Step 3: Calculate overall similarity
        overall_similarity = self._calculate_overall_similarity(examples)

        # Step 4: Get dimension scores via LLM analysis
        dimension_scores = await self._analyze_dimensions(
            content, examples, section_type
        )

        # Step 5: Generate insights
        insights = await self._generate_insights(
            content, examples, dimension_scores, section_type
        )

        # Step 6: Calculate percentile rank
        percentile = await self._calculate_percentile(
            user_embedding, section_type, cluster
        )

        return BenchmarkResult(
            user_content=content,
            section_type=section_type,
            cluster=cluster,
            overall_similarity=overall_similarity,
            percentile_rank=percentile,
            dimension_scores=dimension_scores,
            top_examples=examples,
            key_strengths=insights['strengths'],
            key_gaps=insights['gaps'],
            specific_suggestions=insights['suggestions'],
            examples_compared=len(examples),
            avg_funded_similarity=overall_similarity
        )

    async def _find_benchmark_examples(
        self,
        user_embedding: List[float],
        section_type: str,
        cluster: Optional[str],
        action_type: Optional[str],
        limit: int
    ) -> List[BenchmarkExample]:
        """Find the most similar funded examples."""

        async with get_db_connection() as conn:
            results = await conn.fetch("""
                SELECT
                    pe.project_id,
                    p.acronym as project_acronym,
                    pe.content,
                    pe.cluster,
                    pe.action_type,
                    p.total_cost,
                    1 - (pe.example_embedding <=> $1) as similarity
                FROM proposal_examples pe
                JOIN projects p ON pe.project_id = p.id
                WHERE
                    pe.example_embedding IS NOT NULL
                    AND pe.quality_score >= 0.6
                    AND ($2::text IS NULL OR pe.section_type = $2)
                    AND ($3::text IS NULL OR pe.cluster = $3)
                    AND ($4::text IS NULL OR pe.action_type = $4)
                ORDER BY pe.example_embedding <=> $1
                LIMIT $5
            """,
                user_embedding,
                section_type,
                cluster,
                action_type,
                limit
            )

            return [
                BenchmarkExample(
                    project_id=r['project_id'],
                    project_acronym=r['project_acronym'],
                    content=r['content'],
                    cluster=r['cluster'],
                    action_type=r['action_type'],
                    total_cost=r['total_cost'],
                    similarity_score=r['similarity'] * 100
                )
                for r in results
            ]

    def _calculate_overall_similarity(self, examples: List[BenchmarkExample]) -> float:
        """Calculate weighted average similarity to benchmark examples."""
        if not examples:
            return 0.0

        # Weight by position (top examples count more)
        weights = [1.0 / (i + 1) for i in range(len(examples))]
        total_weight = sum(weights)

        weighted_sum = sum(
            ex.similarity_score * w
            for ex, w in zip(examples, weights)
        )

        return weighted_sum / total_weight

    async def _analyze_dimensions(
        self,
        content: str,
        examples: List[BenchmarkExample],
        section_type: str
    ) -> List[DimensionScore]:
        """Analyze content across multiple quality dimensions."""

        # Prepare benchmark text (top 3 examples)
        benchmark_text = "\n\n---\n\n".join([
            f"[{ex.project_acronym}]: {ex.content[:1500]}"
            for ex in examples[:3]
        ])

        prompt = f"""Compare this user-written proposal section against successful funded proposals.

USER CONTENT ({section_type}):
{content[:2000]}

FUNDED BENCHMARK EXAMPLES:
{benchmark_text}

Analyze across these dimensions and respond with JSON:
{{
    "dimensions": [
        {{
            "dimension": "technical_depth",
            "user_score": 65,
            "benchmark_avg": 78,
            "explanation": "User content lacks specific methodology details",
            "improvement_hint": "Add specific techniques, tools, or methods"
        }},
        {{
            "dimension": "impact_clarity",
            "user_score": 72,
            "benchmark_avg": 81,
            "explanation": "Impact statements are present but not quantified",
            "improvement_hint": "Add measurable KPIs and target metrics"
        }},
        {{
            "dimension": "methodology_rigor",
            "user_score": 58,
            "benchmark_avg": 75,
            "explanation": "Missing work breakdown structure",
            "improvement_hint": "Structure around clear phases or work packages"
        }},
        {{
            "dimension": "innovation_claims",
            "user_score": 70,
            "benchmark_avg": 82,
            "explanation": "Claims innovation but lacks comparison to state-of-art",
            "improvement_hint": "Explicitly compare to existing approaches"
        }},
        {{
            "dimension": "eu_alignment",
            "user_score": 60,
            "benchmark_avg": 85,
            "explanation": "Missing EU policy and priority references",
            "improvement_hint": "Reference Green Deal, Digital Decade, or specific policies"
        }}
    ]
}}

Score each dimension 0-100. Be honest but constructive."""

        response = await self.ai_service.generate_structured(
            prompt=prompt,
            schema_name="dimension_analysis"
        )

        dimension_scores = []
        for dim in response.get('dimensions', []):
            try:
                dimension_scores.append(DimensionScore(
                    dimension=BenchmarkDimension(dim['dimension']),
                    score=dim['user_score'],
                    benchmark_avg=dim['benchmark_avg'],
                    gap=dim['benchmark_avg'] - dim['user_score'],
                    explanation=dim['explanation'],
                    improvement_hint=dim['improvement_hint']
                ))
            except (KeyError, ValueError) as e:
                logger.warning(f"Error parsing dimension: {e}")
                continue

        return dimension_scores

    async def _generate_insights(
        self,
        content: str,
        examples: List[BenchmarkExample],
        dimension_scores: List[DimensionScore],
        section_type: str
    ) -> Dict[str, List[str]]:
        """Generate actionable insights from benchmark comparison."""

        # Extract key differences
        gaps = [
            (ds.dimension.value, ds.gap, ds.improvement_hint)
            for ds in dimension_scores
            if ds.gap > 10  # Significant gap
        ]

        strengths = [
            (ds.dimension.value, ds.score)
            for ds in dimension_scores
            if ds.gap < 5 and ds.score >= 70  # At or above benchmark
        ]

        prompt = f"""Based on the benchmarking analysis, generate specific, actionable insights.

SECTION TYPE: {section_type}
USER CONTENT (excerpt): {content[:1000]}

GAPS IDENTIFIED (dimension, gap_size, hint):
{gaps}

STRENGTHS IDENTIFIED (dimension, score):
{strengths}

TOP BENCHMARK EXAMPLE (for style reference):
{examples[0].content[:1000] if examples else "No examples available"}

Generate JSON:
{{
    "strengths": [
        "Specific strength 1 - what user did well",
        "Specific strength 2"
    ],
    "gaps": [
        "Specific gap 1 - what's missing compared to funded proposals",
        "Specific gap 2"
    ],
    "suggestions": [
        "Concrete suggestion 1 - exact action to take",
        "Concrete suggestion 2 - with example if possible",
        "Concrete suggestion 3"
    ]
}}

Be specific and reference actual content. Max 3-4 items per category."""

        response = await self.ai_service.generate_structured(
            prompt=prompt,
            schema_name="benchmark_insights"
        )

        return {
            'strengths': response.get('strengths', []),
            'gaps': response.get('gaps', []),
            'suggestions': response.get('suggestions', [])
        }

    async def _calculate_percentile(
        self,
        user_embedding: List[float],
        section_type: str,
        cluster: Optional[str]
    ) -> int:
        """
        Calculate what percentile the user content falls in
        compared to all funded proposals.
        """
        async with get_db_connection() as conn:
            # Get similarity to median funded example
            result = await conn.fetchrow("""
                WITH similarity_scores AS (
                    SELECT
                        1 - (example_embedding <=> $1) as similarity
                    FROM proposal_examples
                    WHERE
                        example_embedding IS NOT NULL
                        AND quality_score >= 0.6
                        AND ($2::text IS NULL OR section_type = $2)
                        AND ($3::text IS NULL OR cluster = $3)
                )
                SELECT
                    COUNT(*) FILTER (WHERE similarity < (
                        SELECT 1 - (example_embedding <=> $1)
                        FROM proposal_examples
                        WHERE example_embedding IS NOT NULL
                        ORDER BY example_embedding <=> $1
                        LIMIT 1
                    )) * 100 / COUNT(*) as percentile
                FROM similarity_scores
            """, user_embedding, section_type, cluster)

            return result['percentile'] if result and result['percentile'] else 50

    def _create_empty_result(
        self,
        content: str,
        section_type: str,
        cluster: Optional[str]
    ) -> BenchmarkResult:
        """Create an empty result when no benchmarks are available."""
        return BenchmarkResult(
            user_content=content,
            section_type=section_type,
            cluster=cluster,
            overall_similarity=0.0,
            percentile_rank=50,
            dimension_scores=[],
            top_examples=[],
            key_strengths=["Unable to benchmark - no examples available"],
            key_gaps=[],
            specific_suggestions=["Populate proposal examples to enable benchmarking"],
            examples_compared=0,
            avg_funded_similarity=0.0
        )


class BenchmarkVisualizer:
    """
    Generates visual representations of benchmark results.

    Creates charts, comparison tables, and formatted reports.
    """

    @staticmethod
    def generate_radar_chart_data(result: BenchmarkResult) -> Dict[str, Any]:
        """Generate data for a radar/spider chart comparing dimensions."""
        dimensions = []
        user_scores = []
        benchmark_scores = []

        for ds in result.dimension_scores:
            dimensions.append(ds.dimension.value.replace('_', ' ').title())
            user_scores.append(ds.score)
            benchmark_scores.append(ds.benchmark_avg)

        return {
            "labels": dimensions,
            "datasets": [
                {
                    "label": "Your Content",
                    "data": user_scores,
                    "borderColor": "#3b82f6",
                    "backgroundColor": "rgba(59, 130, 246, 0.2)"
                },
                {
                    "label": "Funded Average",
                    "data": benchmark_scores,
                    "borderColor": "#10b981",
                    "backgroundColor": "rgba(16, 185, 129, 0.2)"
                }
            ]
        }

    @staticmethod
    def generate_comparison_table(result: BenchmarkResult) -> List[Dict]:
        """Generate a comparison table for display."""
        rows = []

        for ds in result.dimension_scores:
            status = "✅" if ds.gap <= 5 else "⚠️" if ds.gap <= 15 else "❌"
            rows.append({
                "dimension": ds.dimension.value.replace('_', ' ').title(),
                "your_score": f"{ds.score:.0f}",
                "benchmark": f"{ds.benchmark_avg:.0f}",
                "gap": f"{ds.gap:+.0f}",
                "status": status,
                "hint": ds.improvement_hint
            })

        return rows

    @staticmethod
    def generate_summary_report(result: BenchmarkResult) -> str:
        """Generate a text summary of the benchmark results."""
        lines = [
            f"## Benchmark Report: {result.section_type.replace('_', ' ').title()}",
            "",
            f"**Overall Similarity:** {result.overall_similarity:.1f}%",
            f"**Percentile Rank:** Top {100 - result.percentile_rank}%",
            f"**Examples Compared:** {result.examples_compared}",
            "",
            "### Dimension Scores",
            ""
        ]

        for ds in result.dimension_scores:
            indicator = "🟢" if ds.gap <= 5 else "🟡" if ds.gap <= 15 else "🔴"
            lines.append(f"- {indicator} **{ds.dimension.value.replace('_', ' ').title()}**: "
                        f"{ds.score:.0f}/100 (benchmark: {ds.benchmark_avg:.0f})")

        lines.extend([
            "",
            "### Key Strengths",
            ""
        ])
        for strength in result.key_strengths:
            lines.append(f"- ✅ {strength}")

        lines.extend([
            "",
            "### Areas for Improvement",
            ""
        ])
        for gap in result.key_gaps:
            lines.append(f"- ⚠️ {gap}")

        lines.extend([
            "",
            "### Specific Suggestions",
            ""
        ])
        for i, suggestion in enumerate(result.specific_suggestions, 1):
            lines.append(f"{i}. {suggestion}")

        return "\n".join(lines)
```

### Step 2: API Endpoints

**File:** `app/api/benchmark_routes.py`

```python
"""
API routes for semantic benchmarking.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel, Field

from app.services.proposal_writing.semantic_benchmarking import (
    SemanticBenchmarkingService,
    BenchmarkResult,
    BenchmarkVisualizer
)

router = APIRouter(prefix="/api/proposal/benchmark", tags=["benchmark"])


class BenchmarkRequest(BaseModel):
    content: str = Field(..., min_length=100, description="Content to benchmark")
    section_type: str = Field(..., description="Section type (excellence_objectives, impact_expected, etc.)")
    cluster: Optional[str] = Field(None, description="HE cluster filter")
    action_type: Optional[str] = Field(None, description="Action type filter (RIA, IA, etc.)")
    num_examples: int = Field(5, ge=1, le=10, description="Number of benchmark examples")


class DimensionScoreResponse(BaseModel):
    dimension: str
    score: float
    benchmark_avg: float
    gap: float
    explanation: str
    improvement_hint: str


class BenchmarkExampleResponse(BaseModel):
    project_id: str
    project_acronym: str
    content_preview: str
    cluster: Optional[str]
    action_type: Optional[str]
    similarity_score: float


class BenchmarkResponse(BaseModel):
    overall_similarity: float
    percentile_rank: int
    dimension_scores: List[DimensionScoreResponse]
    top_examples: List[BenchmarkExampleResponse]
    key_strengths: List[str]
    key_gaps: List[str]
    specific_suggestions: List[str]
    examples_compared: int


class ChartDataResponse(BaseModel):
    labels: List[str]
    datasets: List[dict]


class ComparisonTableRow(BaseModel):
    dimension: str
    your_score: str
    benchmark: str
    gap: str
    status: str
    hint: str


@router.post("/analyze", response_model=BenchmarkResponse)
async def benchmark_content(request: BenchmarkRequest):
    """
    Benchmark user content against funded proposals.

    Compares the provided content to similar sections from successfully
    funded Horizon Europe projects and provides:
    - Overall similarity score (0-100%)
    - Percentile rank (what % of funded proposals this is better than)
    - Dimension-by-dimension analysis
    - Key strengths and gaps
    - Specific improvement suggestions
    """
    service = SemanticBenchmarkingService()

    try:
        result = await service.benchmark_content(
            content=request.content,
            section_type=request.section_type,
            cluster=request.cluster,
            action_type=request.action_type,
            num_examples=request.num_examples
        )

        return BenchmarkResponse(
            overall_similarity=result.overall_similarity,
            percentile_rank=result.percentile_rank,
            dimension_scores=[
                DimensionScoreResponse(
                    dimension=ds.dimension.value,
                    score=ds.score,
                    benchmark_avg=ds.benchmark_avg,
                    gap=ds.gap,
                    explanation=ds.explanation,
                    improvement_hint=ds.improvement_hint
                )
                for ds in result.dimension_scores
            ],
            top_examples=[
                BenchmarkExampleResponse(
                    project_id=ex.project_id,
                    project_acronym=ex.project_acronym,
                    content_preview=ex.content[:300] + "..." if len(ex.content) > 300 else ex.content,
                    cluster=ex.cluster,
                    action_type=ex.action_type,
                    similarity_score=ex.similarity_score
                )
                for ex in result.top_examples
            ],
            key_strengths=result.key_strengths,
            key_gaps=result.key_gaps,
            specific_suggestions=result.specific_suggestions,
            examples_compared=result.examples_compared
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chart-data", response_model=ChartDataResponse)
async def get_benchmark_chart_data(request: BenchmarkRequest):
    """
    Get chart data for visualizing benchmark results.

    Returns data formatted for Chart.js radar chart.
    """
    service = SemanticBenchmarkingService()

    result = await service.benchmark_content(
        content=request.content,
        section_type=request.section_type,
        cluster=request.cluster,
        action_type=request.action_type,
        num_examples=request.num_examples
    )

    chart_data = BenchmarkVisualizer.generate_radar_chart_data(result)
    return ChartDataResponse(**chart_data)


@router.post("/comparison-table", response_model=List[ComparisonTableRow])
async def get_comparison_table(request: BenchmarkRequest):
    """
    Get a comparison table for benchmark results.

    Returns rows comparing user scores to benchmark scores across dimensions.
    """
    service = SemanticBenchmarkingService()

    result = await service.benchmark_content(
        content=request.content,
        section_type=request.section_type,
        cluster=request.cluster,
        action_type=request.action_type,
        num_examples=request.num_examples
    )

    table_data = BenchmarkVisualizer.generate_comparison_table(result)
    return [ComparisonTableRow(**row) for row in table_data]


@router.post("/report")
async def get_benchmark_report(request: BenchmarkRequest):
    """
    Get a formatted markdown report of benchmark results.

    Returns a complete textual analysis suitable for display or export.
    """
    service = SemanticBenchmarkingService()

    result = await service.benchmark_content(
        content=request.content,
        section_type=request.section_type,
        cluster=request.cluster,
        action_type=request.action_type,
        num_examples=request.num_examples
    )

    report = BenchmarkVisualizer.generate_summary_report(result)
    return {"report": report}
```

### Step 3: Add JSON Schemas for Structured Output

**Add to:** `app/services/proposal_writing/ai_schemas.py`

```python
# Add these schemas to the existing ai_schemas.py file

DIMENSION_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "dimensions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dimension": {
                        "type": "string",
                        "enum": [
                            "technical_depth",
                            "impact_clarity",
                            "methodology_rigor",
                            "innovation_claims",
                            "eu_alignment"
                        ]
                    },
                    "user_score": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100
                    },
                    "benchmark_avg": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100
                    },
                    "explanation": {
                        "type": "string",
                        "maxLength": 200
                    },
                    "improvement_hint": {
                        "type": "string",
                        "maxLength": 150
                    }
                },
                "required": ["dimension", "user_score", "benchmark_avg", "explanation", "improvement_hint"]
            }
        }
    },
    "required": ["dimensions"]
}

BENCHMARK_INSIGHTS_SCHEMA = {
    "type": "object",
    "properties": {
        "strengths": {
            "type": "array",
            "items": {"type": "string", "maxLength": 200},
            "maxItems": 4
        },
        "gaps": {
            "type": "array",
            "items": {"type": "string", "maxLength": 200},
            "maxItems": 4
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string", "maxLength": 250},
            "maxItems": 5
        }
    },
    "required": ["strengths", "gaps", "suggestions"]
}
```

---

## Integration with Other Services

### Quality Improver Integration

```python
# In quality_improver.py, add benchmarking to the improvement flow

class QualityImprover:
    def __init__(self):
        self.benchmarking_service = SemanticBenchmarkingService()

    async def improve_section(
        self,
        content: str,
        section_type: str,
        cluster: str = None
    ) -> QualityImprovementResult:
        """Improve a section with benchmark-informed suggestions."""

        # First, benchmark the content
        benchmark = await self.benchmarking_service.benchmark_content(
            content=content,
            section_type=section_type,
            cluster=cluster
        )

        # Use benchmark insights to guide improvements
        improvements = await self._generate_improvements(
            content=content,
            benchmark=benchmark
        )

        return QualityImprovementResult(
            original_content=content,
            improved_content=improvements['improved_text'],
            changes_made=improvements['changes'],
            benchmark_before=benchmark.overall_similarity,
            benchmark_after=None,  # Calculate after user accepts
            suggestions=benchmark.specific_suggestions
        )
```

### Real-time Benchmarking Hook

```python
# For streaming feedback (Task 14), provide real-time benchmark updates

class RealTimeBenchmarker:
    """Provides lightweight benchmarking during typing."""

    def __init__(self):
        self.service = SemanticBenchmarkingService()
        self._cache = {}  # Cache recent embeddings

    async def quick_benchmark(
        self,
        content: str,
        section_type: str
    ) -> Dict[str, Any]:
        """
        Fast benchmark for real-time feedback.

        Returns only similarity score and one key suggestion.
        """
        # Only benchmark if content is substantial
        if len(content) < 200:
            return {"status": "too_short", "min_length": 200}

        # Get embedding (may be cached)
        embedding = await self._get_cached_embedding(content)

        # Quick similarity check (no LLM analysis)
        similarity = await self._quick_similarity(embedding, section_type)

        return {
            "status": "ready",
            "similarity": similarity,
            "tier": self._get_tier(similarity),
            "quick_hint": self._get_quick_hint(similarity)
        }

    def _get_tier(self, similarity: float) -> str:
        if similarity >= 80:
            return "excellent"
        elif similarity >= 65:
            return "good"
        elif similarity >= 50:
            return "average"
        else:
            return "needs_work"

    def _get_quick_hint(self, similarity: float) -> str:
        hints = {
            "excellent": "Great! Your content aligns well with funded proposals.",
            "good": "Good progress. Consider adding more specific details.",
            "average": "Add more technical depth and EU policy references.",
            "needs_work": "Focus on methodology and measurable impacts."
        }
        return hints[self._get_tier(similarity)]
```

---

## Testing Plan

### Unit Tests

```python
# tests/test_semantic_benchmarking.py

import pytest
from app.services.proposal_writing.semantic_benchmarking import (
    SemanticBenchmarkingService,
    BenchmarkVisualizer
)


class TestSemanticBenchmarking:

    @pytest.fixture
    def service(self):
        return SemanticBenchmarkingService()

    @pytest.mark.asyncio
    async def test_benchmark_content_returns_result(self, service):
        """Test that benchmarking returns a valid result."""
        content = """
        The main objective of this project is to develop innovative
        methodologies for sustainable urban mobility. We will employ
        machine learning techniques to optimize traffic flow and reduce
        emissions by 30% in pilot cities. The expected impact includes
        improved air quality and reduced commute times for EU citizens.
        """

        result = await service.benchmark_content(
            content=content,
            section_type="excellence_objectives",
            cluster="CL5"
        )

        assert result.overall_similarity > 0
        assert 0 <= result.percentile_rank <= 100
        assert len(result.dimension_scores) > 0
        assert len(result.specific_suggestions) > 0

    @pytest.mark.asyncio
    async def test_benchmark_empty_cluster(self, service):
        """Test benchmarking without cluster filter."""
        content = "Test content for benchmarking purposes with objectives and methodology."

        result = await service.benchmark_content(
            content=content,
            section_type="full_objective",
            cluster=None
        )

        assert result.examples_compared > 0

    def test_radar_chart_data_structure(self):
        """Test that chart data has correct structure."""
        # Mock result
        from app.services.proposal_writing.semantic_benchmarking import (
            BenchmarkResult, DimensionScore, BenchmarkDimension
        )

        mock_result = BenchmarkResult(
            user_content="test",
            section_type="test",
            cluster=None,
            overall_similarity=70.0,
            percentile_rank=65,
            dimension_scores=[
                DimensionScore(
                    dimension=BenchmarkDimension.TECHNICAL_DEPTH,
                    score=75,
                    benchmark_avg=80,
                    gap=5,
                    explanation="test",
                    improvement_hint="test"
                )
            ],
            top_examples=[],
            key_strengths=["test"],
            key_gaps=["test"],
            specific_suggestions=["test"],
            examples_compared=5,
            avg_funded_similarity=72.0
        )

        chart_data = BenchmarkVisualizer.generate_radar_chart_data(mock_result)

        assert "labels" in chart_data
        assert "datasets" in chart_data
        assert len(chart_data["datasets"]) == 2


@pytest.mark.asyncio
async def test_benchmark_api_endpoint():
    """Test the benchmark API endpoint."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    response = client.post("/api/proposal/benchmark/analyze", json={
        "content": "This project aims to develop innovative solutions " * 20,
        "section_type": "excellence_objectives",
        "cluster": "CL4",
        "num_examples": 3
    })

    assert response.status_code == 200
    data = response.json()
    assert "overall_similarity" in data
    assert "dimension_scores" in data
    assert "specific_suggestions" in data
```

---

## Verification Checklist

- [ ] SemanticBenchmarkingService initializes correctly
- [ ] Embedding generation works for user content
- [ ] Similar examples are found from database
- [ ] Dimension analysis returns valid scores
- [ ] Insights generation produces actionable suggestions
- [ ] Percentile calculation is reasonable (0-100)
- [ ] API endpoints return properly formatted responses
- [ ] Radar chart data has correct structure for Chart.js
- [ ] Integration with Quality Improver works
- [ ] Real-time benchmarker provides quick feedback

---

## UI Integration Notes

The frontend should display:

1. **Overall Score Card**
   - Large percentage (e.g., "72%")
   - Percentile rank (e.g., "Top 35% of funded proposals")
   - Color indicator (green/yellow/red)

2. **Radar Chart**
   - Compare user vs benchmark across 5 dimensions
   - Interactive hover for details

3. **Dimension Table**
   - Sortable by gap size
   - Each row shows dimension, scores, status, hint

4. **Insights Panel**
   - Collapsible sections for strengths/gaps/suggestions
   - Checkboxes for tracking addressed items

5. **Benchmark Examples**
   - Expandable cards showing similar funded content
   - "Use as template" button for each

---

## Notes

- Benchmarking requires populated proposal_examples (Task 06)
- LLM analysis costs ~$0.01 per benchmark request
- Cache embeddings to reduce latency on repeated benchmarks
- Consider batch benchmarking for full proposal analysis
