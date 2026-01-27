"""
Example Extractor Service

Extracts proposal-like examples from CORDIS project objectives.
Populates the proposal_examples table with categorized, embedded content.
"""

import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class ExampleType(str, Enum):
    """Types of extractable examples."""

    EXCELLENCE_OBJECTIVES = "excellence_objectives"
    EXCELLENCE_METHODOLOGY = "excellence_methodology"
    EXCELLENCE_AMBITION = "excellence_ambition"
    IMPACT_EXPECTED = "impact_expected"
    IMPACT_DISSEMINATION = "impact_dissemination"
    IMPLEMENTATION_WORKPLAN = "implementation_workplan"
    FULL_OBJECTIVE = "full_objective"


@dataclass
class ExtractedExample:
    """An extracted example from a project."""

    project_id: str
    project_acronym: str
    section_type: ExampleType
    content: str
    cluster: str | None
    action_type: str | None
    total_cost: float | None
    start_date: str | None
    quality_score: float


class ExampleExtractor:
    """
    Extracts and categorizes examples from CORDIS project objectives.

    The extraction uses a combination of:
    1. Pattern matching for section boundaries
    2. Quality scoring to filter low-value examples
    """

    # Patterns that indicate different section types
    SECTION_PATTERNS = {
        ExampleType.EXCELLENCE_OBJECTIVES: [
            r"(?i)the\s+(main\s+)?objective[s]?\s+(of\s+\w+\s+)?(is|are|will be)",
            r"(?i)this\s+project\s+(aims|seeks|will)",
            r"(?i)our\s+(primary\s+)?goal[s]?\s+(is|are)",
            r"(?i)the\s+overarching\s+aim",
            r"(?i)project\s+\w+\s+(aims|will|seeks)\s+to",
        ],
        ExampleType.EXCELLENCE_METHODOLOGY: [
            r"(?i)we\s+will\s+(use|employ|apply|develop)",
            r"(?i)the\s+(proposed\s+)?methodology",
            r"(?i)our\s+approach\s+(will\s+)?involve",
            r"(?i)the\s+technical\s+approach",
            r"(?i)methodological\s+framework",
        ],
        ExampleType.EXCELLENCE_AMBITION: [
            r"(?i)beyond\s+the\s+state[- ]of[- ]the[- ]art",
            r"(?i)novel\s+(and\s+)?innovative",
            r"(?i)breakthrough",
            r"(?i)first[- ]of[- ](its[- ])?kind",
            r"(?i)paradigm[- ]shift",
            r"(?i)pioneering",
        ],
        ExampleType.IMPACT_EXPECTED: [
            r"(?i)the\s+(expected\s+)?impact",
            r"(?i)will\s+(significantly\s+)?contribute\s+to",
            r"(?i)societal\s+(and\s+economic\s+)?benefits",
            r"(?i)expected\s+outcomes?\s+include",
            r"(?i)will\s+address\s+(the\s+)?challenge",
        ],
        ExampleType.IMPACT_DISSEMINATION: [
            r"(?i)dissemination\s+(activities|plan|strategy)",
            r"(?i)exploitation\s+(of\s+results|strategy)",
            r"(?i)knowledge\s+transfer",
            r"(?i)stakeholder\s+engagement",
            r"(?i)communication\s+activities",
        ],
        ExampleType.IMPLEMENTATION_WORKPLAN: [
            r"(?i)work\s*package[s]?",
            r"(?i)the\s+project\s+(is\s+)?structured",
            r"(?i)deliverable[s]?",
            r"(?i)milestone[s]?",
            r"(?i)consortium\s+(of|will|brings)",
        ],
    }

    # Minimum quality thresholds
    MIN_CONTENT_LENGTH = 200
    MIN_QUALITY_SCORE = 0.6

    def __init__(self):
        self._embedding_service = None
        self._db_url = os.getenv("DATABASE_URL")

    def _get_embedding_service(self):
        """Lazy load embedding service."""
        if self._embedding_service is None:
            from app.services.embedding_service import EmbeddingService

            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self._db_url)

    async def extract_from_all_projects(
        self,
        batch_size: int = 100,
        max_projects: int | None = None,
        clusters: list[str] | None = None,
        skip_existing: bool = True,
    ) -> dict[str, int]:
        """
        Extract examples from all projects in the database.

        Args:
            batch_size: Number of projects to process at once
            max_projects: Maximum number of projects to process (None = all)
            clusters: Filter to specific clusters (None = all)
            skip_existing: Skip projects that already have examples

        Returns:
            Statistics about extracted examples
        """
        stats = {
            "projects_processed": 0,
            "examples_extracted": 0,
            "examples_by_type": {t.value: 0 for t in ExampleType},
            "skipped_low_quality": 0,
            "skipped_existing": 0,
            "errors": 0,
        }

        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query with optional filters
                query = """
                    SELECT
                        p.id, p.acronym, p.objective,
                        p."fundingScheme" as action_type,
                        p."totalCost" as total_cost,
                        p."startDate" as start_date
                    FROM projects p
                    WHERE p.objective IS NOT NULL
                    AND LENGTH(p.objective) > 500
                """
                params = []

                if clusters:
                    query += " AND p.cluster = ANY(%s)"
                    params.append(clusters)

                if skip_existing:
                    query += """
                        AND NOT EXISTS (
                            SELECT 1 FROM proposal_examples pe
                            WHERE pe.project_id = p.id
                        )
                    """

                if max_projects:
                    query += f" LIMIT {max_projects}"

                cur.execute(query, params if params else None)
                projects = cur.fetchall()

                logger.info(f"Processing {len(projects)} projects for example extraction")

                # Process in batches
                for i in range(0, len(projects), batch_size):
                    batch = projects[i : i + batch_size]

                    for project in batch:
                        try:
                            examples = await self._extract_from_project(project)

                            for example in examples:
                                if example.quality_score >= self.MIN_QUALITY_SCORE:
                                    await self._save_example(conn, example)
                                    stats["examples_extracted"] += 1
                                    stats["examples_by_type"][example.section_type.value] += 1
                                else:
                                    stats["skipped_low_quality"] += 1

                            stats["projects_processed"] += 1

                        except Exception as e:
                            logger.error(f"Error processing project {project['id']}: {e}")
                            stats["errors"] += 1

                    conn.commit()
                    logger.info(
                        f"Processed {min(i + batch_size, len(projects))}/{len(projects)} projects"
                    )

        finally:
            conn.close()

        return stats

    async def _extract_from_project(self, project: dict) -> list[ExtractedExample]:
        """Extract all possible examples from a single project."""
        examples = []
        objective = project["objective"]

        # Always create a full objective example
        full_example = ExtractedExample(
            project_id=project["id"],
            project_acronym=project["acronym"] or "",
            section_type=ExampleType.FULL_OBJECTIVE,
            content=objective,
            cluster=None,  # Will be filled from project if available
            action_type=project.get("action_type"),
            total_cost=project.get("total_cost"),
            start_date=str(project.get("start_date")) if project.get("start_date") else None,
            quality_score=self._score_content_quality(objective),
        )
        examples.append(full_example)

        # Try to extract specific section types
        segments = self._segment_objective(objective)

        for section_type, content in segments.items():
            if content and len(content) >= self.MIN_CONTENT_LENGTH:
                example = ExtractedExample(
                    project_id=project["id"],
                    project_acronym=project["acronym"] or "",
                    section_type=section_type,
                    content=content,
                    cluster=None,
                    action_type=project.get("action_type"),
                    total_cost=project.get("total_cost"),
                    start_date=(
                        str(project.get("start_date")) if project.get("start_date") else None
                    ),
                    quality_score=self._score_content_quality(content),
                )
                examples.append(example)

        return examples

    def _segment_objective(self, objective: str) -> dict[ExampleType, str]:
        """
        Segment an objective into component sections.

        Uses pattern matching to identify different section types.
        """
        segments = {}

        # Split into paragraphs
        paragraphs = [p.strip() for p in objective.split("\n\n") if p.strip()]

        # If no double newlines, try single newlines
        if len(paragraphs) == 1:
            paragraphs = [
                p.strip() for p in objective.split("\n") if p.strip() and len(p.strip()) > 50
            ]

        for para in paragraphs:
            # Check each pattern type
            for section_type, patterns in self.SECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, para):
                        # Found a match - add to that section type
                        if section_type not in segments:
                            segments[section_type] = para
                        else:
                            segments[section_type] += "\n\n" + para
                        break

        return segments

    def _score_content_quality(self, content: str) -> float:
        """
        Score content quality using heuristics.

        Factors:
        - Length (longer generally better, but not too long)
        - Sentence structure (varied lengths)
        - Technical vocabulary
        - Absence of boilerplate
        """
        score = 0.5  # Base score

        # Length scoring
        length = len(content)
        if 300 <= length <= 3000:
            score += 0.15
        elif 200 <= length < 300 or 3000 < length <= 5000:
            score += 0.1

        # Sentence variety
        sentences = re.split(r"[.!?]+", content)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        if sentence_lengths:
            avg_len = sum(sentence_lengths) / len(sentence_lengths)
            variance = sum((sent_len - avg_len) ** 2 for sent_len in sentence_lengths) / len(
                sentence_lengths
            )
            if 5 < variance < 100:  # Good variety
                score += 0.1

        # Technical vocabulary indicators
        technical_patterns = [
            r"\b(methodology|framework|approach|analysis|implementation)\b",
            r"\b(innovative|novel|breakthrough|state-of-the-art)\b",
            r"\b(stakeholder|consortium|deliverable|milestone)\b",
            r"\b(impact|outcome|objective|result)\b",
        ]
        tech_matches = sum(1 for p in technical_patterns if re.search(p, content, re.I))
        score += min(tech_matches * 0.05, 0.2)

        # Penalize boilerplate
        boilerplate_patterns = [
            r"Lorem ipsum",
            r"TBD|TBC|TODO",
            r"Insert .* here",
            r"\[placeholder\]",
        ]
        if any(re.search(p, content, re.I) for p in boilerplate_patterns):
            score -= 0.3

        return max(0.0, min(1.0, score))

    async def _save_example(self, conn, example: ExtractedExample) -> None:
        """Save an example to the database with embedding."""
        try:
            # Generate embedding
            embedding_service = self._get_embedding_service()
            embedding = await embedding_service.embed_text(
                example.content[:8000]
            )  # Limit content for embedding

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO proposal_examples (
                        project_id, section_type, content, source,
                        cluster, action_type, example_embedding, quality_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s)
                    ON CONFLICT (project_id, section_type)
                    DO UPDATE SET
                        content = EXCLUDED.content,
                        example_embedding = EXCLUDED.example_embedding,
                        quality_score = EXCLUDED.quality_score,
                        updated_at = NOW()
                """,
                    (
                        example.project_id,
                        example.section_type.value,
                        example.content,
                        "cordis",
                        example.cluster,
                        example.action_type,
                        embedding,
                        example.quality_score,
                    ),
                )

        except Exception as e:
            logger.error(f"Error saving example for project {example.project_id}: {e}")
            raise

    async def get_extraction_stats(self) -> dict[str, Any]:
        """Get statistics about extracted examples."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT COUNT(*) as total FROM proposal_examples WHERE project_id IS NOT NULL"
                )
                total = cur.fetchone()["total"]

                cur.execute(
                    """
                    SELECT COUNT(*) as count FROM proposal_examples
                    WHERE example_embedding IS NOT NULL AND project_id IS NOT NULL
                """
                )
                with_embeddings = cur.fetchone()["count"]

                cur.execute(
                    """
                    SELECT COUNT(*) as count FROM proposal_examples
                    WHERE quality_score >= 0.7 AND project_id IS NOT NULL
                """
                )
                high_quality = cur.fetchone()["count"]

                cur.execute(
                    """
                    SELECT section_type, COUNT(*) as count
                    FROM proposal_examples
                    WHERE project_id IS NOT NULL
                    GROUP BY section_type
                    ORDER BY count DESC
                """
                )
                by_section = {row["section_type"]: row["count"] for row in cur.fetchall()}

                cur.execute(
                    """
                    SELECT action_type, COUNT(*) as count
                    FROM proposal_examples
                    WHERE project_id IS NOT NULL AND action_type IS NOT NULL
                    GROUP BY action_type
                    ORDER BY count DESC
                """
                )
                by_action_type = {row["action_type"]: row["count"] for row in cur.fetchall()}

                return {
                    "total_examples": total,
                    "with_embeddings": with_embeddings,
                    "high_quality_count": high_quality,
                    "by_section_type": by_section,
                    "by_action_type": by_action_type,
                }
        finally:
            conn.close()


class ExampleEnricher:
    """
    Enriches extracted examples with additional metadata using LLM analysis.

    This is a separate pass that can run after initial extraction.
    """

    def __init__(self):
        self._ai_service = None
        self._db_url = os.getenv("DATABASE_URL")

    def _get_ai_service(self):
        """Lazy load AI service."""
        if self._ai_service is None:
            from .proposal_ai_service import ProposalAIService

            self._ai_service = ProposalAIService()
        return self._ai_service

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self._db_url)

    async def enrich_examples(self, batch_size: int = 50) -> dict[str, int]:
        """
        Enrich existing examples with LLM-analyzed metadata.

        Adds:
        - Key strengths identified
        - Writing techniques used
        - EU terminology alignment
        - Estimated evaluator appeal
        """
        stats = {"enriched": 0, "errors": 0}

        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get examples needing enrichment
                cur.execute(
                    """
                    SELECT id, content, section_type, cluster
                    FROM proposal_examples
                    WHERE enrichment_data IS NULL
                    AND quality_score >= 0.7
                    AND project_id IS NOT NULL
                    LIMIT %s
                """,
                    (batch_size,),
                )
                examples = cur.fetchall()

                for example in examples:
                    try:
                        enrichment = await self._analyze_example(example)

                        cur.execute(
                            """
                            UPDATE proposal_examples
                            SET enrichment_data = %s, enriched_at = NOW()
                            WHERE id = %s
                        """,
                            (enrichment, example["id"]),
                        )

                        stats["enriched"] += 1

                    except Exception as e:
                        logger.error(f"Error enriching example {example['id']}: {e}")
                        stats["errors"] += 1

                conn.commit()

        finally:
            conn.close()

        return stats

    async def _analyze_example(self, example: dict) -> str:
        """Analyze an example for writing quality indicators."""
        import json

        ai_service = self._get_ai_service()

        prompt = f"""Analyze this funded EU proposal excerpt and identify what makes it effective.

Content ({example["section_type"]}):
{example["content"][:2000]}

Respond with JSON:
{{
    "key_strengths": ["strength1", "strength2", ...],
    "writing_techniques": ["technique1", "technique2", ...],
    "eu_terminology": ["term1", "term2", ...],
    "evaluator_appeal_factors": ["factor1", "factor2", ...],
    "estimated_section_score": 4.2,
    "improvement_notes": "Brief notes on what could be even better"
}}"""

        response = await ai_service.generate_structured(
            prompt=prompt,
            response_schema={
                "type": "object",
                "properties": {
                    "key_strengths": {"type": "array", "items": {"type": "string"}},
                    "writing_techniques": {"type": "array", "items": {"type": "string"}},
                    "eu_terminology": {"type": "array", "items": {"type": "string"}},
                    "evaluator_appeal_factors": {"type": "array", "items": {"type": "string"}},
                    "estimated_section_score": {"type": "number"},
                    "improvement_notes": {"type": "string"},
                },
                "required": ["key_strengths", "writing_techniques"],
            },
        )

        return json.dumps(response)
