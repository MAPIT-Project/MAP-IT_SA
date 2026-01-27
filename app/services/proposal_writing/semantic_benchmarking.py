"""
Semantic Benchmarking Service

Compares user-written content against successfully funded proposals
to provide data-driven quality assessment and improvement suggestions.
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

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
    cluster: str | None
    action_type: str | None
    total_cost: float | None
    similarity_score: float
    relevant_excerpts: list[str] = field(default_factory=list)


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
    cluster: str | None

    # Overall metrics
    overall_similarity: float  # 0-100
    percentile_rank: int  # What % of funded proposals is this better than

    # Dimension breakdown
    dimension_scores: list[DimensionScore]

    # Benchmark examples
    top_examples: list[BenchmarkExample]

    # Insights
    key_strengths: list[str]
    key_gaps: list[str]
    specific_suggestions: list[str]

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
        self._embedding_service = None
        self._ai_service = None
        self._db_url = os.getenv("DATABASE_URL")

    def _get_embedding_service(self):
        """Lazy load embedding service."""
        if self._embedding_service is None:
            from app.services.embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def _get_ai_service(self):
        """Lazy load AI service."""
        if self._ai_service is None:
            from .proposal_ai_service import ProposalAIService
            self._ai_service = ProposalAIService()
        return self._ai_service

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self._db_url)

    async def benchmark_content(
        self,
        content: str,
        section_type: str,
        cluster: str | None = None,
        action_type: str | None = None,
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
        embedding_service = self._get_embedding_service()
        user_embedding = await embedding_service.embed_text(content[:8000])

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
        user_embedding: list[float],
        section_type: str,
        cluster: str | None,
        action_type: str | None,
        limit: int
    ) -> list[BenchmarkExample]:
        """Find the most similar funded examples."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query with optional filters
                query = """
                    SELECT
                        pe.project_id,
                        p.acronym as project_acronym,
                        pe.content,
                        pe.cluster,
                        pe.action_type,
                        p."totalCost" as total_cost,
                        1 - (pe.example_embedding <=> %s::vector) as similarity
                    FROM proposal_examples pe
                    LEFT JOIN projects p ON pe.project_id = p.id
                    WHERE
                        pe.example_embedding IS NOT NULL
                        AND pe.quality_score >= 0.6
                """
                params = [user_embedding]

                if section_type:
                    query += " AND pe.section_type = %s"
                    params.append(section_type)

                if cluster:
                    query += " AND pe.cluster = %s"
                    params.append(cluster)

                if action_type:
                    query += " AND pe.action_type = %s"
                    params.append(action_type)

                query += """
                    ORDER BY pe.example_embedding <=> %s::vector
                    LIMIT %s
                """
                params.extend([user_embedding, limit])

                cur.execute(query, params)
                results = cur.fetchall()

                return [
                    BenchmarkExample(
                        project_id=r['project_id'] or '',
                        project_acronym=r['project_acronym'] or 'Unknown',
                        content=r['content'] or '',
                        cluster=r['cluster'],
                        action_type=r['action_type'],
                        total_cost=float(r['total_cost']) if r['total_cost'] else None,
                        similarity_score=r['similarity'] * 100 if r['similarity'] else 0.0
                    )
                    for r in results
                ]
        finally:
            conn.close()

    def _calculate_overall_similarity(self, examples: list[BenchmarkExample]) -> float:
        """Calculate weighted average similarity to benchmark examples."""
        if not examples:
            return 0.0

        # Weight by position (top examples count more)
        weights = [1.0 / (i + 1) for i in range(len(examples))]
        total_weight = sum(weights)

        weighted_sum = sum(
            ex.similarity_score * w
            for ex, w in zip(examples, weights, strict=False)
        )

        return weighted_sum / total_weight

    async def _analyze_dimensions(
        self,
        content: str,
        examples: list[BenchmarkExample],
        section_type: str
    ) -> list[DimensionScore]:
        """Analyze content across multiple quality dimensions."""
        ai_service = self._get_ai_service()

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

        schema = {
            "type": "object",
            "properties": {
                "dimensions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "dimension": {"type": "string"},
                            "user_score": {"type": "integer"},
                            "benchmark_avg": {"type": "integer"},
                            "explanation": {"type": "string"},
                            "improvement_hint": {"type": "string"}
                        },
                        "required": ["dimension", "user_score", "benchmark_avg", "explanation", "improvement_hint"]
                    }
                }
            },
            "required": ["dimensions"]
        }

        response = await ai_service.generate_structured(
            prompt=prompt,
            response_schema=schema
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
        examples: list[BenchmarkExample],
        dimension_scores: list[DimensionScore],
        section_type: str
    ) -> dict[str, list[str]]:
        """Generate actionable insights from benchmark comparison."""
        ai_service = self._get_ai_service()

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

        schema = {
            "type": "object",
            "properties": {
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "gaps": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "suggestions": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["strengths", "gaps", "suggestions"]
        }

        response = await ai_service.generate_structured(
            prompt=prompt,
            response_schema=schema
        )

        return {
            'strengths': response.get('strengths', []),
            'gaps': response.get('gaps', []),
            'suggestions': response.get('suggestions', [])
        }

    async def _calculate_percentile(
        self,
        user_embedding: list[float],
        section_type: str,
        cluster: str | None
    ) -> int:
        """
        Calculate what percentile the user content falls in
        compared to all funded proposals.
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get user's similarity to most similar example
                query = """
                    SELECT 1 - (example_embedding <=> %s::vector) as user_similarity
                    FROM proposal_examples
                    WHERE example_embedding IS NOT NULL
                    AND quality_score >= 0.6
                """
                params = [user_embedding]

                if section_type:
                    query += " AND section_type = %s"
                    params.append(section_type)

                if cluster:
                    query += " AND cluster = %s"
                    params.append(cluster)

                query += " ORDER BY example_embedding <=> %s::vector LIMIT 1"
                params.append(user_embedding)

                cur.execute(query, params)
                result = cur.fetchone()

                if not result or not result['user_similarity']:
                    return 50

                user_similarity = result['user_similarity']

                # Count how many examples have lower similarity (are worse matches)
                count_query = """
                    WITH all_similarities AS (
                        SELECT 1 - (example_embedding <=> %s::vector) as similarity
                        FROM proposal_examples
                        WHERE example_embedding IS NOT NULL
                        AND quality_score >= 0.6
                """
                count_params = [user_embedding]

                if section_type:
                    count_query += " AND section_type = %s"
                    count_params.append(section_type)

                if cluster:
                    count_query += " AND cluster = %s"
                    count_params.append(cluster)

                count_query += """
                    )
                    SELECT
                        COUNT(*) FILTER (WHERE similarity < %s) * 100.0 / NULLIF(COUNT(*), 0) as percentile
                    FROM all_similarities
                """
                count_params.append(user_similarity)

                cur.execute(count_query, count_params)
                percentile_result = cur.fetchone()

                if percentile_result and percentile_result['percentile']:
                    return int(percentile_result['percentile'])
                return 50

        finally:
            conn.close()

    def _create_empty_result(
        self,
        content: str,
        section_type: str,
        cluster: str | None
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
    def generate_radar_chart_data(result: BenchmarkResult) -> dict[str, Any]:
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
    def generate_comparison_table(result: BenchmarkResult) -> list[dict]:
        """Generate a comparison table for display."""
        rows = []

        for ds in result.dimension_scores:
            status = "pass" if ds.gap <= 5 else "warning" if ds.gap <= 15 else "fail"
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
            indicator = "PASS" if ds.gap <= 5 else "WARN" if ds.gap <= 15 else "FAIL"
            lines.append(f"- [{indicator}] **{ds.dimension.value.replace('_', ' ').title()}**: "
                        f"{ds.score:.0f}/100 (benchmark: {ds.benchmark_avg:.0f})")

        lines.extend([
            "",
            "### Key Strengths",
            ""
        ])
        for strength in result.key_strengths:
            lines.append(f"- {strength}")

        lines.extend([
            "",
            "### Areas for Improvement",
            ""
        ])
        for gap in result.key_gaps:
            lines.append(f"- {gap}")

        lines.extend([
            "",
            "### Specific Suggestions",
            ""
        ])
        for i, suggestion in enumerate(result.specific_suggestions, 1):
            lines.append(f"{i}. {suggestion}")

        return "\n".join(lines)


class RealTimeBenchmarker:
    """Provides lightweight benchmarking during typing."""

    def __init__(self):
        self._embedding_service = None
        self._db_url = os.getenv("DATABASE_URL")
        self._cache = {}

    def _get_embedding_service(self):
        """Lazy load embedding service."""
        if self._embedding_service is None:
            from app.services.embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self._db_url)

    async def quick_benchmark(
        self,
        content: str,
        section_type: str
    ) -> dict[str, Any]:
        """
        Fast benchmark for real-time feedback.

        Returns only similarity score and one key suggestion.
        """
        # Only benchmark if content is substantial
        if len(content) < 200:
            return {"status": "too_short", "min_length": 200}

        # Get embedding
        embedding_service = self._get_embedding_service()
        embedding = await embedding_service.embed_text(content[:4000])

        # Quick similarity check (no LLM analysis)
        similarity = await self._quick_similarity(embedding, section_type)

        return {
            "status": "ready",
            "similarity": similarity,
            "tier": self._get_tier(similarity),
            "quick_hint": self._get_quick_hint(similarity)
        }

    async def _quick_similarity(self, embedding: list[float], section_type: str) -> float:
        """Get quick similarity score."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT AVG(1 - (example_embedding <=> %s::vector)) * 100 as avg_similarity
                    FROM (
                        SELECT example_embedding
                        FROM proposal_examples
                        WHERE example_embedding IS NOT NULL
                        AND quality_score >= 0.6
                        AND section_type = %s
                        ORDER BY example_embedding <=> %s::vector
                        LIMIT 5
                    ) top5
                """, (embedding, section_type, embedding))

                result = cur.fetchone()
                return result['avg_similarity'] if result and result['avg_similarity'] else 50.0
        finally:
            conn.close()

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
