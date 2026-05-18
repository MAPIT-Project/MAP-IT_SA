# Task 06: Populate Proposal Examples from CORDIS

> **Priority:** P1 (Core Value)
> **Estimated Effort:** 4-6 hours
> **Dependencies:** Task 05 (Learning Service)
> **Status:** Not Started

---

## Problem Statement

The `proposal_examples` table exists in the database but is completely empty. We have 13,865 funded CORDIS projects with rich objectives text that could serve as excellent examples of successful proposal writing.

### Current State
```sql
SELECT COUNT(*) FROM proposal_examples;
-- Result: 0

SELECT COUNT(*) FROM projects WHERE objective IS NOT NULL AND LENGTH(objective) > 500;
-- Result: ~12,000 projects with substantial objectives
```

### Target State
- Populate `proposal_examples` with extracted sections from funded project objectives
- Categorize by section type (Excellence, Impact, Implementation patterns)
- Add embeddings for semantic search
- Enable the Learning Service to find relevant examples

---

## Implementation Plan

### Step 1: Create Example Extraction Service

**File:** `app/services/proposal_writing/example_extractor.py`

```python
"""
Example Extractor Service

Extracts proposal-like examples from CORDIS project objectives.
Populates the proposal_examples table with categorized, embedded content.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from app.core.config import settings
from app.services.database import get_db_connection
from app.services.embedding.embedding_service import EmbeddingService

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
    cluster: Optional[str]
    action_type: Optional[str]
    total_cost: Optional[float]
    start_date: Optional[str]
    quality_score: float  # Heuristic quality assessment


class ExampleExtractor:
    """
    Extracts and categorizes examples from CORDIS project objectives.

    The extraction uses a combination of:
    1. Pattern matching for section boundaries
    2. LLM-based classification for ambiguous content
    3. Quality scoring to filter low-value examples
    """

    # Patterns that indicate different section types
    SECTION_PATTERNS = {
        ExampleType.EXCELLENCE_OBJECTIVES: [
            r"(?i)the\s+(main\s+)?objective[s]?\s+(of\s+\w+\s+)?(is|are|will be)",
            r"(?i)this\s+project\s+(aims|seeks|will)",
            r"(?i)our\s+(primary\s+)?goal[s]?\s+(is|are)",
            r"(?i)the\s+overarching\s+aim",
        ],
        ExampleType.EXCELLENCE_METHODOLOGY: [
            r"(?i)we\s+will\s+(use|employ|apply|develop)",
            r"(?i)the\s+(proposed\s+)?methodology",
            r"(?i)our\s+approach\s+(will\s+)?involve",
            r"(?i)the\s+technical\s+approach",
        ],
        ExampleType.EXCELLENCE_AMBITION: [
            r"(?i)beyond\s+the\s+state[- ]of[- ]the[- ]art",
            r"(?i)novel\s+(and\s+)?innovative",
            r"(?i)breakthrough",
            r"(?i)first[- ]of[- ](its[- ])?kind",
        ],
        ExampleType.IMPACT_EXPECTED: [
            r"(?i)the\s+(expected\s+)?impact",
            r"(?i)will\s+(significantly\s+)?contribute\s+to",
            r"(?i)societal\s+(and\s+economic\s+)?benefits",
            r"(?i)expected\s+outcomes?\s+include",
        ],
        ExampleType.IMPACT_DISSEMINATION: [
            r"(?i)dissemination\s+(activities|plan|strategy)",
            r"(?i)exploitation\s+(of\s+results|strategy)",
            r"(?i)knowledge\s+transfer",
            r"(?i)stakeholder\s+engagement",
        ],
        ExampleType.IMPLEMENTATION_WORKPLAN: [
            r"(?i)work\s*package[s]?",
            r"(?i)the\s+project\s+(is\s+)?structured",
            r"(?i)deliverable[s]?",
            r"(?i)milestone[s]?",
        ],
    }

    # Minimum quality thresholds
    MIN_CONTENT_LENGTH = 200
    MIN_QUALITY_SCORE = 0.6

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self._llm_client = None

    async def extract_from_all_projects(
        self,
        batch_size: int = 100,
        max_projects: Optional[int] = None,
        clusters: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Extract examples from all projects in the database.

        Args:
            batch_size: Number of projects to process at once
            max_projects: Maximum number of projects to process (None = all)
            clusters: Filter to specific clusters (None = all)

        Returns:
            Statistics about extracted examples
        """
        stats = {
            "projects_processed": 0,
            "examples_extracted": 0,
            "examples_by_type": {t.value: 0 for t in ExampleType},
            "skipped_low_quality": 0,
            "errors": 0,
        }

        async with get_db_connection() as conn:
            # Build query with optional filters
            query = """
                SELECT
                    id, acronym, objective,
                    cluster, action_type,
                    total_cost, start_date
                FROM projects
                WHERE objective IS NOT NULL
                AND LENGTH(objective) > 500
            """
            params = []

            if clusters:
                query += " AND cluster = ANY($1)"
                params.append(clusters)

            if max_projects:
                query += f" LIMIT {max_projects}"

            projects = await conn.fetch(query, *params)

            logger.info(f"Processing {len(projects)} projects for example extraction")

            # Process in batches
            for i in range(0, len(projects), batch_size):
                batch = projects[i:i + batch_size]

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

                logger.info(f"Processed {min(i + batch_size, len(projects))}/{len(projects)} projects")

        return stats

    async def _extract_from_project(self, project: Dict) -> List[ExtractedExample]:
        """Extract all possible examples from a single project."""
        examples = []
        objective = project['objective']

        # Always create a full objective example
        full_example = ExtractedExample(
            project_id=project['id'],
            project_acronym=project['acronym'],
            section_type=ExampleType.FULL_OBJECTIVE,
            content=objective,
            cluster=project.get('cluster'),
            action_type=project.get('action_type'),
            total_cost=project.get('total_cost'),
            start_date=str(project.get('start_date')) if project.get('start_date') else None,
            quality_score=self._score_content_quality(objective)
        )
        examples.append(full_example)

        # Try to extract specific section types
        sections = await self._segment_objective(objective)

        for section_type, content in sections.items():
            if content and len(content) >= self.MIN_CONTENT_LENGTH:
                example = ExtractedExample(
                    project_id=project['id'],
                    project_acronym=project['acronym'],
                    section_type=section_type,
                    content=content,
                    cluster=project.get('cluster'),
                    action_type=project.get('action_type'),
                    total_cost=project.get('total_cost'),
                    start_date=str(project.get('start_date')) if project.get('start_date') else None,
                    quality_score=self._score_content_quality(content)
                )
                examples.append(example)

        return examples

    async def _segment_objective(self, objective: str) -> Dict[ExampleType, str]:
        """
        Segment an objective into component sections.

        Uses pattern matching first, falls back to LLM for complex cases.
        """
        import re

        segments = {}

        # Split into paragraphs
        paragraphs = [p.strip() for p in objective.split('\n\n') if p.strip()]

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
        import re

        score = 0.5  # Base score

        # Length scoring
        length = len(content)
        if 300 <= length <= 3000:
            score += 0.15
        elif 200 <= length < 300 or 3000 < length <= 5000:
            score += 0.1

        # Sentence variety
        sentences = re.split(r'[.!?]+', content)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        if sentence_lengths:
            avg_len = sum(sentence_lengths) / len(sentence_lengths)
            variance = sum((l - avg_len) ** 2 for l in sentence_lengths) / len(sentence_lengths)
            if 5 < variance < 100:  # Good variety
                score += 0.1

        # Technical vocabulary indicators
        technical_patterns = [
            r'\b(methodology|framework|approach|analysis|implementation)\b',
            r'\b(innovative|novel|breakthrough|state-of-the-art)\b',
            r'\b(stakeholder|consortium|deliverable|milestone)\b',
            r'\b(impact|outcome|objective|result)\b',
        ]
        tech_matches = sum(1 for p in technical_patterns if re.search(p, content, re.I))
        score += min(tech_matches * 0.05, 0.2)

        # Penalize boilerplate
        boilerplate_patterns = [
            r'Lorem ipsum',
            r'TBD|TBC|TODO',
            r'Insert .* here',
            r'\[placeholder\]',
        ]
        if any(re.search(p, content, re.I) for p in boilerplate_patterns):
            score -= 0.3

        return max(0.0, min(1.0, score))

    async def _save_example(self, conn, example: ExtractedExample) -> None:
        """Save an example to the database with embedding."""

        # Generate embedding
        embedding = await self.embedding_service.embed_text(example.content)

        await conn.execute("""
            INSERT INTO proposal_examples (
                project_id, section_type, content, source,
                cluster, action_type, example_embedding, quality_score
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (project_id, section_type)
            DO UPDATE SET
                content = EXCLUDED.content,
                example_embedding = EXCLUDED.example_embedding,
                quality_score = EXCLUDED.quality_score,
                updated_at = NOW()
        """,
            example.project_id,
            example.section_type.value,
            example.content,
            'cordis',
            example.cluster,
            example.action_type,
            embedding,
            example.quality_score
        )


class ExampleEnricher:
    """
    Enriches extracted examples with additional metadata using LLM analysis.

    This is a separate pass that can run after initial extraction.
    """

    def __init__(self):
        self.ai_service = None  # Will use ProposalAIService from Task 02

    async def enrich_examples(self, batch_size: int = 50) -> Dict[str, int]:
        """
        Enrich existing examples with LLM-analyzed metadata.

        Adds:
        - Key strengths identified
        - Writing techniques used
        - EU terminology alignment
        - Estimated evaluator appeal
        """
        from app.services.proposal_writing.proposal_ai_service import ProposalAIService

        self.ai_service = ProposalAIService()

        stats = {"enriched": 0, "errors": 0}

        async with get_db_connection() as conn:
            # Get examples needing enrichment
            examples = await conn.fetch("""
                SELECT id, content, section_type, cluster
                FROM proposal_examples
                WHERE enrichment_data IS NULL
                AND quality_score >= 0.7
                LIMIT $1
            """, batch_size)

            for example in examples:
                try:
                    enrichment = await self._analyze_example(example)

                    await conn.execute("""
                        UPDATE proposal_examples
                        SET enrichment_data = $1, enriched_at = NOW()
                        WHERE id = $2
                    """, enrichment, example['id'])

                    stats["enriched"] += 1

                except Exception as e:
                    logger.error(f"Error enriching example {example['id']}: {e}")
                    stats["errors"] += 1

        return stats

    async def _analyze_example(self, example: Dict) -> Dict[str, Any]:
        """Analyze an example for writing quality indicators."""

        prompt = f"""Analyze this funded EU proposal excerpt and identify what makes it effective.

Content ({example['section_type']}):
{example['content'][:2000]}

Respond with JSON:
{{
    "key_strengths": ["strength1", "strength2", ...],
    "writing_techniques": ["technique1", "technique2", ...],
    "eu_terminology": ["term1", "term2", ...],
    "evaluator_appeal_factors": ["factor1", "factor2", ...],
    "estimated_section_score": 4.2,
    "improvement_notes": "Brief notes on what could be even better"
}}"""

        response = await self.ai_service.generate_structured(
            prompt=prompt,
            schema_name="example_analysis"
        )

        return response
```

### Step 2: Database Schema Updates

**File:** `migration/010_proposal_examples_enhancement.sql`

```sql
-- Enhance proposal_examples table for better extraction
-- Run this migration before populating examples

-- Add new columns if they don't exist
DO $$
BEGIN
    -- Add cluster column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'cluster'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN cluster VARCHAR(50);
    END IF;

    -- Add action_type column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'action_type'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN action_type VARCHAR(20);
    END IF;

    -- Add embedding column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'example_embedding'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN example_embedding vector(768);
    END IF;

    -- Add quality_score column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'quality_score'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN quality_score DECIMAL(3,2);
    END IF;

    -- Add enrichment_data column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'enrichment_data'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN enrichment_data JSONB;
    END IF;

    -- Add enriched_at column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'enriched_at'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN enriched_at TIMESTAMP;
    END IF;
END $$;

-- Create unique constraint for deduplication
ALTER TABLE proposal_examples
DROP CONSTRAINT IF EXISTS proposal_examples_project_section_unique;

ALTER TABLE proposal_examples
ADD CONSTRAINT proposal_examples_project_section_unique
UNIQUE (project_id, section_type);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_proposal_examples_cluster
ON proposal_examples(cluster);

CREATE INDEX IF NOT EXISTS idx_proposal_examples_action_type
ON proposal_examples(action_type);

CREATE INDEX IF NOT EXISTS idx_proposal_examples_section_type
ON proposal_examples(section_type);

CREATE INDEX IF NOT EXISTS idx_proposal_examples_quality
ON proposal_examples(quality_score DESC);

-- Create embedding index for vector search
CREATE INDEX IF NOT EXISTS idx_proposal_examples_embedding
ON proposal_examples
USING ivfflat (example_embedding vector_cosine_ops)
WITH (lists = 100);

-- Create view for high-quality examples
CREATE OR REPLACE VIEW high_quality_examples AS
SELECT
    pe.*,
    p.acronym as project_acronym,
    p.title as project_title,
    p.total_cost,
    p.ec_contribution
FROM proposal_examples pe
JOIN projects p ON pe.project_id = p.id
WHERE pe.quality_score >= 0.7
ORDER BY pe.quality_score DESC;

-- Function to find similar examples by embedding
CREATE OR REPLACE FUNCTION find_similar_examples(
    query_embedding vector(768),
    target_section_type VARCHAR DEFAULT NULL,
    target_cluster VARCHAR DEFAULT NULL,
    target_action_type VARCHAR DEFAULT NULL,
    limit_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    project_id VARCHAR,
    section_type VARCHAR,
    content TEXT,
    cluster VARCHAR,
    action_type VARCHAR,
    quality_score DECIMAL,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pe.id,
        pe.project_id,
        pe.section_type,
        pe.content,
        pe.cluster,
        pe.action_type,
        pe.quality_score,
        1 - (pe.example_embedding <=> query_embedding) as similarity
    FROM proposal_examples pe
    WHERE
        pe.example_embedding IS NOT NULL
        AND pe.quality_score >= 0.6
        AND (target_section_type IS NULL OR pe.section_type = target_section_type)
        AND (target_cluster IS NULL OR pe.cluster = target_cluster)
        AND (target_action_type IS NULL OR pe.action_type = target_action_type)
    ORDER BY pe.example_embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Statistics view
CREATE OR REPLACE VIEW proposal_examples_stats AS
SELECT
    section_type,
    cluster,
    action_type,
    COUNT(*) as example_count,
    AVG(quality_score) as avg_quality,
    COUNT(*) FILTER (WHERE enrichment_data IS NOT NULL) as enriched_count
FROM proposal_examples
GROUP BY section_type, cluster, action_type
ORDER BY example_count DESC;
```

### Step 3: Population Script

**File:** `scripts/populate_proposal_examples.py`

```python
#!/usr/bin/env python3
"""
Script to populate proposal_examples from CORDIS projects.

Usage:
    python scripts/populate_proposal_examples.py [--batch-size 100] [--max-projects 1000] [--cluster CL4]
"""

import asyncio
import argparse
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main(args):
    """Main execution function."""
    from app.services.proposal_writing.example_extractor import ExampleExtractor, ExampleEnricher

    logger.info("=" * 60)
    logger.info("PROPOSAL EXAMPLES POPULATION SCRIPT")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now()}")
    logger.info(f"Configuration:")
    logger.info(f"  - Batch size: {args.batch_size}")
    logger.info(f"  - Max projects: {args.max_projects or 'All'}")
    logger.info(f"  - Clusters: {args.clusters or 'All'}")
    logger.info("=" * 60)

    # Step 1: Extract examples
    logger.info("\n[STEP 1] Extracting examples from projects...")
    extractor = ExampleExtractor()

    clusters = args.clusters.split(',') if args.clusters else None

    extraction_stats = await extractor.extract_from_all_projects(
        batch_size=args.batch_size,
        max_projects=args.max_projects,
        clusters=clusters
    )

    logger.info("\nExtraction Results:")
    logger.info(f"  - Projects processed: {extraction_stats['projects_processed']}")
    logger.info(f"  - Examples extracted: {extraction_stats['examples_extracted']}")
    logger.info(f"  - Skipped (low quality): {extraction_stats['skipped_low_quality']}")
    logger.info(f"  - Errors: {extraction_stats['errors']}")
    logger.info("\n  By section type:")
    for section_type, count in extraction_stats['examples_by_type'].items():
        logger.info(f"    - {section_type}: {count}")

    # Step 2: Enrich high-quality examples (optional)
    if args.enrich:
        logger.info("\n[STEP 2] Enriching high-quality examples with LLM analysis...")
        enricher = ExampleEnricher()

        enrichment_stats = await enricher.enrich_examples(batch_size=50)

        logger.info("\nEnrichment Results:")
        logger.info(f"  - Examples enriched: {enrichment_stats['enriched']}")
        logger.info(f"  - Errors: {enrichment_stats['errors']}")

    # Step 3: Print final statistics
    logger.info("\n[FINAL] Database Statistics:")
    from app.services.database import get_db_connection

    async with get_db_connection() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM proposal_examples")
        with_embeddings = await conn.fetchval(
            "SELECT COUNT(*) FROM proposal_examples WHERE example_embedding IS NOT NULL"
        )
        high_quality = await conn.fetchval(
            "SELECT COUNT(*) FROM proposal_examples WHERE quality_score >= 0.7"
        )
        enriched = await conn.fetchval(
            "SELECT COUNT(*) FROM proposal_examples WHERE enrichment_data IS NOT NULL"
        )

        logger.info(f"  - Total examples: {total}")
        logger.info(f"  - With embeddings: {with_embeddings}")
        logger.info(f"  - High quality (≥0.7): {high_quality}")
        logger.info(f"  - Enriched: {enriched}")

        # By cluster
        cluster_stats = await conn.fetch("""
            SELECT cluster, COUNT(*) as count
            FROM proposal_examples
            WHERE cluster IS NOT NULL
            GROUP BY cluster
            ORDER BY count DESC
        """)

        logger.info("\n  By cluster:")
        for row in cluster_stats:
            logger.info(f"    - {row['cluster']}: {row['count']}")

    logger.info("\n" + "=" * 60)
    logger.info(f"Completed at: {datetime.now()}")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate proposal examples from CORDIS")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of projects to process at once"
    )
    parser.add_argument(
        "--max-projects",
        type=int,
        default=None,
        help="Maximum number of projects to process (default: all)"
    )
    parser.add_argument(
        "--clusters",
        type=str,
        default=None,
        help="Comma-separated list of clusters to process (default: all)"
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Run LLM enrichment after extraction"
    )

    args = parser.parse_args()
    asyncio.run(main(args))
```

### Step 4: API Endpoints

**File:** `app/api/proposal_example_routes.py`

```python
"""
API routes for proposal examples.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from app.services.proposal_writing.example_extractor import ExampleExtractor, ExampleType
from app.services.database import get_db_connection

router = APIRouter(prefix="/api/proposal/examples", tags=["proposal-examples"])


class ExampleResponse(BaseModel):
    id: str
    project_id: str
    project_acronym: Optional[str]
    section_type: str
    content: str
    cluster: Optional[str]
    action_type: Optional[str]
    quality_score: float
    similarity: Optional[float] = None


class ExampleSearchRequest(BaseModel):
    query: str
    section_type: Optional[str] = None
    cluster: Optional[str] = None
    action_type: Optional[str] = None
    limit: int = 5


class ExampleStatsResponse(BaseModel):
    total_examples: int
    with_embeddings: int
    high_quality_count: int
    by_section_type: dict
    by_cluster: dict


@router.get("/stats", response_model=ExampleStatsResponse)
async def get_example_stats():
    """Get statistics about available proposal examples."""
    async with get_db_connection() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM proposal_examples")
        with_embeddings = await conn.fetchval(
            "SELECT COUNT(*) FROM proposal_examples WHERE example_embedding IS NOT NULL"
        )
        high_quality = await conn.fetchval(
            "SELECT COUNT(*) FROM proposal_examples WHERE quality_score >= 0.7"
        )

        by_section = await conn.fetch("""
            SELECT section_type, COUNT(*) as count
            FROM proposal_examples GROUP BY section_type
        """)

        by_cluster = await conn.fetch("""
            SELECT cluster, COUNT(*) as count
            FROM proposal_examples
            WHERE cluster IS NOT NULL
            GROUP BY cluster
        """)

        return ExampleStatsResponse(
            total_examples=total,
            with_embeddings=with_embeddings,
            high_quality_count=high_quality,
            by_section_type={r['section_type']: r['count'] for r in by_section},
            by_cluster={r['cluster']: r['count'] for r in by_cluster}
        )


@router.post("/search", response_model=List[ExampleResponse])
async def search_similar_examples(request: ExampleSearchRequest):
    """
    Search for similar proposal examples using semantic search.

    - **query**: Text to find similar examples for
    - **section_type**: Filter by section type (excellence_objectives, impact_expected, etc.)
    - **cluster**: Filter by HE cluster (CL1, CL2, etc.)
    - **action_type**: Filter by action type (RIA, IA, CSA, etc.)
    - **limit**: Maximum number of results (default: 5)
    """
    from app.services.embedding.embedding_service import EmbeddingService

    embedding_service = EmbeddingService()
    query_embedding = await embedding_service.embed_text(request.query)

    async with get_db_connection() as conn:
        results = await conn.fetch("""
            SELECT
                pe.id::text,
                pe.project_id,
                p.acronym as project_acronym,
                pe.section_type,
                pe.content,
                pe.cluster,
                pe.action_type,
                pe.quality_score,
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
            query_embedding,
            request.section_type,
            request.cluster,
            request.action_type,
            request.limit
        )

        return [ExampleResponse(**dict(r)) for r in results]


@router.get("/types")
async def get_example_types():
    """Get available example section types."""
    return {
        "types": [
            {
                "value": t.value,
                "label": t.value.replace('_', ' ').title(),
                "description": _get_type_description(t)
            }
            for t in ExampleType
        ]
    }


def _get_type_description(example_type: ExampleType) -> str:
    """Get description for an example type."""
    descriptions = {
        ExampleType.EXCELLENCE_OBJECTIVES: "Main objectives and aims of the project",
        ExampleType.EXCELLENCE_METHODOLOGY: "Technical approach and methodology",
        ExampleType.EXCELLENCE_AMBITION: "Beyond state-of-the-art and innovation claims",
        ExampleType.IMPACT_EXPECTED: "Expected impacts and outcomes",
        ExampleType.IMPACT_DISSEMINATION: "Dissemination and exploitation plans",
        ExampleType.IMPLEMENTATION_WORKPLAN: "Work plan structure and organization",
        ExampleType.FULL_OBJECTIVE: "Complete project objective text",
    }
    return descriptions.get(example_type, "")


@router.get("/{example_id}", response_model=ExampleResponse)
async def get_example(example_id: str):
    """Get a specific example by ID."""
    async with get_db_connection() as conn:
        result = await conn.fetchrow("""
            SELECT
                pe.id::text,
                pe.project_id,
                p.acronym as project_acronym,
                pe.section_type,
                pe.content,
                pe.cluster,
                pe.action_type,
                pe.quality_score
            FROM proposal_examples pe
            JOIN projects p ON pe.project_id = p.id
            WHERE pe.id = $1
        """, example_id)

        if not result:
            raise HTTPException(status_code=404, detail="Example not found")

        return ExampleResponse(**dict(result))
```

---

## Testing Plan

### Unit Tests

```python
# tests/test_example_extractor.py

import pytest
from app.services.proposal_writing.example_extractor import (
    ExampleExtractor, ExampleType
)


class TestExampleExtractor:

    @pytest.fixture
    def extractor(self):
        return ExampleExtractor()

    def test_score_content_quality_good(self, extractor):
        """Test quality scoring for good content."""
        good_content = """
        The main objective of this project is to develop an innovative
        methodology for sustainable energy production. Our approach combines
        state-of-the-art machine learning techniques with novel material science
        to achieve breakthrough results. The expected impact includes significant
        reduction in carbon emissions and new industry standards for the sector.
        The consortium brings together leading research institutions and SMEs
        with complementary expertise to deliver measurable outcomes.
        """

        score = extractor._score_content_quality(good_content)
        assert score >= 0.7, f"Good content should score >= 0.7, got {score}"

    def test_score_content_quality_poor(self, extractor):
        """Test quality scoring for poor content."""
        poor_content = "TBD. Insert content here. [placeholder]"

        score = extractor._score_content_quality(poor_content)
        assert score < 0.5, f"Poor content should score < 0.5, got {score}"

    @pytest.mark.asyncio
    async def test_segment_objective(self, extractor):
        """Test objective segmentation."""
        objective = """
        The main objectives of EXAMPLE are to develop new methodologies
        for renewable energy integration.

        Our methodology will employ cutting-edge AI techniques combined
        with advanced sensor networks.

        The expected impact includes a 30% reduction in grid instability
        and new standards for energy management.
        """

        segments = await extractor._segment_objective(objective)

        assert ExampleType.EXCELLENCE_OBJECTIVES in segments
        assert ExampleType.EXCELLENCE_METHODOLOGY in segments
        assert ExampleType.IMPACT_EXPECTED in segments


@pytest.mark.asyncio
async def test_example_search_endpoint():
    """Test the example search API endpoint."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    response = client.post("/api/proposal/examples/search", json={
        "query": "renewable energy objectives",
        "section_type": "excellence_objectives",
        "limit": 3
    })

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 3
```

---

## Verification Checklist

- [ ] Migration 010 runs successfully
- [ ] ExampleExtractor extracts from sample projects
- [ ] Quality scoring produces reasonable values (0.5-0.9 range)
- [ ] Embeddings are generated and stored
- [ ] Population script completes for full dataset
- [ ] API endpoint `/api/proposal/examples/stats` returns data
- [ ] Semantic search `/api/proposal/examples/search` finds relevant examples
- [ ] Learning Service (Task 05) can query examples

---

## Expected Outcomes

After running the population script:

| Metric | Expected Value |
|--------|----------------|
| Total examples | ~50,000+ |
| Full objectives | ~12,000 |
| Excellence examples | ~15,000 |
| Impact examples | ~12,000 |
| Implementation examples | ~8,000 |
| High quality (≥0.7) | ~30,000 |
| With embeddings | 100% |

---

## Integration with Learning Service

Once populated, the Learning Service (Task 05) will use these examples:

```python
# In ProposalLearningService

async def find_similar_examples(
    self,
    user_content: str,
    section_type: str,
    cluster: str = None
) -> List[ProposalExample]:
    """Find similar funded proposal examples."""

    # Use the populated proposal_examples table
    results = await self._search_examples(
        query=user_content,
        section_type=section_type,
        cluster=cluster,
        limit=5
    )

    return results
```

---

## Notes

- Initial population takes ~2-3 hours for all 13,865 projects
- Embedding generation is the bottleneck (rate limits)
- Run enrichment separately after initial population
- Quality scores can be recalculated without re-embedding
