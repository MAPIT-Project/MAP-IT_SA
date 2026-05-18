# Task 05: Build Proposal Learning Service

> **Phase:** 1 - Learning from Success
> **Priority:** P1 (Core Value)
> **Estimated Effort:** 6-8 hours
> **Status:** Not Started
> **Depends On:** Tasks 01-04

---

## Problem Statement

The system has 13,865+ funded CORDIS projects with:
- Full objectives (text descriptions)
- Vector embeddings (768-dim)
- Funding amounts
- Consortium compositions
- Cluster/topic classifications

**But this data is NOT used for proposal writing at all.**

The current draft generator creates content from scratch without learning from what made successful proposals work.

---

## Solution: Proposal Learning Service

Create a service that:
1. Finds semantically similar funded projects to user's idea
2. Extracts patterns from successful proposals
3. Provides examples of excellent sections
4. Benchmarks user content against funded projects
5. Suggests language and structure from successful proposals

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PROPOSAL LEARNING SERVICE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │  Similar Project │    │  Pattern        │    │  Example        │ │
│  │  Finder          │    │  Extractor      │    │  Provider       │ │
│  │                  │    │                 │    │                 │ │
│  │ • Semantic search│    │ • Success       │    │ • Section       │ │
│  │ • Filter by      │    │   patterns      │    │   examples      │ │
│  │   cluster/type   │    │ • Language      │    │ • Annotated     │ │
│  │ • RRF ranking    │    │   patterns      │    │   samples       │ │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘ │
│           │                      │                      │          │
│           └──────────────────────┼──────────────────────┘          │
│                                  │                                  │
│                                  ▼                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    SEMANTIC BENCHMARKER                      │   │
│  │                                                              │   │
│  │  • Compare user text to successful proposals                │   │
│  │  • Calculate similarity percentile                          │   │
│  │  • Identify gaps from top examples                          │   │
│  │  • Generate specific improvement suggestions                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation

### Step 1: Create Proposal Learning Service

**File:** `app/services/proposal_writing/proposal_learning_service.py`

```python
"""
Proposal Learning Service

Learn from 13,865+ funded CORDIS projects to improve proposal quality.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import os

from app.services.embedding_service import EmbeddingService
from app.core.dependencies import get_db_pool

logger = logging.getLogger(__name__)


@dataclass
class SimilarProject:
    """A funded project similar to user's idea."""
    project_id: str
    acronym: str
    title: str
    objective: str
    similarity_score: float
    ec_contribution: float
    cluster: str
    action_type: str
    start_date: str
    coordinator_country: str
    participant_count: int


@dataclass
class SuccessPattern:
    """Pattern extracted from successful proposals."""
    pattern_type: str  # 'language', 'structure', 'terminology', 'approach'
    description: str
    examples: List[str]
    frequency: float  # How often this pattern appears in successful proposals


class ProposalLearningService:
    """
    Learn from funded CORDIS projects to improve proposal writing.

    Features:
    - Find semantically similar funded projects
    - Extract success patterns
    - Provide section examples
    - Benchmark user content
    """

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self._db_pool = None

    async def _get_db_pool(self):
        """Get database connection pool."""
        if self._db_pool is None:
            self._db_pool = await get_db_pool()
        return self._db_pool

    # =========================================================================
    # SIMILAR PROJECT FINDER
    # =========================================================================

    async def find_similar_funded_projects(
        self,
        user_idea: str,
        cluster: str = None,
        action_type: str = None,
        min_funding: float = None,
        limit: int = 10
    ) -> List[SimilarProject]:
        """
        Find funded projects semantically similar to user's idea.

        Args:
            user_idea: User's project idea/description
            cluster: Filter by cluster (CL1-CL6, ERC, EIC, MSCA)
            action_type: Filter by action type (RIA, IA, CSA)
            min_funding: Minimum EC contribution
            limit: Maximum results to return

        Returns:
            List of similar funded projects with similarity scores
        """

        logger.info(f"Finding similar funded projects for idea: {user_idea[:100]}...")

        # Generate embedding for user's idea
        user_embedding = await self.embedding_service.generate_embedding(user_idea)

        pool = await self._get_db_pool()

        # Build query with filters
        filters = ["p.status = 'SIGNED'"]  # Only funded projects
        params = [user_embedding, limit]
        param_idx = 3

        if cluster:
            filters.append(f"p.cluster = ${param_idx}")
            params.append(cluster)
            param_idx += 1

        if action_type:
            filters.append(f"p.action_type = ${param_idx}")
            params.append(action_type)
            param_idx += 1

        if min_funding:
            filters.append(f"p.ec_contribution >= ${param_idx}")
            params.append(min_funding)
            param_idx += 1

        filter_clause = " AND ".join(filters)

        query = f"""
            SELECT
                p.id as project_id,
                p.acronym,
                p.title,
                p.objective,
                p.ec_contribution,
                p.cluster,
                p.action_type,
                p.start_date,
                p.coordinator_country,
                p.participant_count,
                1 - (pe.embedding <=> $1::vector) as similarity_score
            FROM projects p
            JOIN project_embeddings pe ON p.id = pe.project_id
            WHERE {filter_clause}
            ORDER BY pe.embedding <=> $1::vector
            LIMIT $2
        """

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            SimilarProject(
                project_id=str(row['project_id']),
                acronym=row['acronym'] or '',
                title=row['title'] or '',
                objective=row['objective'] or '',
                similarity_score=float(row['similarity_score']),
                ec_contribution=float(row['ec_contribution'] or 0),
                cluster=row['cluster'] or '',
                action_type=row['action_type'] or '',
                start_date=str(row['start_date']) if row['start_date'] else '',
                coordinator_country=row['coordinator_country'] or '',
                participant_count=int(row['participant_count'] or 0)
            )
            for row in rows
        ]

    async def find_projects_by_keywords(
        self,
        keywords: List[str],
        cluster: str = None,
        limit: int = 20
    ) -> List[SimilarProject]:
        """
        Find funded projects by keyword matching (for fallback).
        """

        pool = await self._get_db_pool()

        # Build keyword search
        keyword_conditions = " OR ".join([
            f"(p.title ILIKE '%{kw}%' OR p.objective ILIKE '%{kw}%')"
            for kw in keywords[:5]  # Limit keywords
        ])

        cluster_filter = f"AND p.cluster = '{cluster}'" if cluster else ""

        query = f"""
            SELECT
                p.id as project_id,
                p.acronym,
                p.title,
                p.objective,
                p.ec_contribution,
                p.cluster,
                p.action_type,
                p.start_date,
                p.coordinator_country,
                p.participant_count,
                0.5 as similarity_score
            FROM projects p
            WHERE p.status = 'SIGNED'
            AND ({keyword_conditions})
            {cluster_filter}
            ORDER BY p.ec_contribution DESC
            LIMIT $1
        """

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, limit)

        return [
            SimilarProject(
                project_id=str(row['project_id']),
                acronym=row['acronym'] or '',
                title=row['title'] or '',
                objective=row['objective'] or '',
                similarity_score=float(row['similarity_score']),
                ec_contribution=float(row['ec_contribution'] or 0),
                cluster=row['cluster'] or '',
                action_type=row['action_type'] or '',
                start_date=str(row['start_date']) if row['start_date'] else '',
                coordinator_country=row['coordinator_country'] or '',
                participant_count=int(row['participant_count'] or 0)
            )
            for row in rows
        ]

    # =========================================================================
    # PATTERN EXTRACTOR
    # =========================================================================

    async def extract_success_patterns(
        self,
        similar_projects: List[SimilarProject],
        pattern_type: str = "all"
    ) -> List[SuccessPattern]:
        """
        Extract patterns from successful proposals.

        Args:
            similar_projects: List of similar funded projects
            pattern_type: 'language', 'structure', 'terminology', 'approach', 'all'

        Returns:
            List of identified success patterns
        """

        if not similar_projects:
            return []

        patterns = []

        # Combine objectives for analysis
        objectives = [p.objective for p in similar_projects if p.objective]

        if pattern_type in ['terminology', 'all']:
            patterns.extend(await self._extract_terminology_patterns(objectives))

        if pattern_type in ['language', 'all']:
            patterns.extend(await self._extract_language_patterns(objectives))

        if pattern_type in ['structure', 'all']:
            patterns.extend(await self._extract_structure_patterns(objectives))

        if pattern_type in ['approach', 'all']:
            patterns.extend(await self._extract_approach_patterns(similar_projects))

        return patterns

    async def _extract_terminology_patterns(
        self,
        objectives: List[str]
    ) -> List[SuccessPattern]:
        """Extract commonly used terminology from successful proposals."""

        # Key EU/HE terms to look for
        eu_terms = [
            'state of the art', 'beyond', 'innovative', 'novel',
            'breakthrough', 'cutting-edge', 'transformative',
            'sustainable', 'scalable', 'replicable',
            'stakeholder', 'end-user', 'societal',
            'TRL', 'demonstrat', 'validat', 'pilot',
            'dissemination', 'exploitation', 'impact',
            'European added value', 'cross-border', 'pan-European'
        ]

        combined_text = ' '.join(objectives).lower()
        found_terms = {}

        for term in eu_terms:
            count = combined_text.count(term.lower())
            if count > 0:
                frequency = count / len(objectives)
                found_terms[term] = frequency

        # Sort by frequency
        sorted_terms = sorted(found_terms.items(), key=lambda x: x[1], reverse=True)

        if sorted_terms:
            return [SuccessPattern(
                pattern_type='terminology',
                description='Commonly used terms in successful proposals',
                examples=[f"{term} (used in {freq*100:.0f}% of similar projects)"
                         for term, freq in sorted_terms[:10]],
                frequency=sum(f for _, f in sorted_terms[:5]) / 5
            )]

        return []

    async def _extract_language_patterns(
        self,
        objectives: List[str]
    ) -> List[SuccessPattern]:
        """Extract effective language patterns."""

        patterns = []

        # Look for strong opening patterns
        strong_openings = [
            'will develop', 'aims to', 'seeks to',
            'will create', 'will establish', 'will demonstrate',
            'addresses the', 'tackles the', 'responds to'
        ]

        combined_text = ' '.join(objectives).lower()

        opening_counts = {
            op: combined_text.count(op)
            for op in strong_openings
        }

        top_openings = sorted(
            opening_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        if top_openings:
            patterns.append(SuccessPattern(
                pattern_type='language',
                description='Effective opening phrases',
                examples=[f"'{op}' - used {count} times" for op, count in top_openings if count > 0],
                frequency=sum(c for _, c in top_openings) / len(objectives)
            ))

        return patterns

    async def _extract_structure_patterns(
        self,
        objectives: List[str]
    ) -> List[SuccessPattern]:
        """Extract structural patterns from objectives."""

        patterns = []

        # Analyze average length
        lengths = [len(obj.split()) for obj in objectives]
        avg_length = sum(lengths) / len(lengths) if lengths else 0

        # Analyze paragraph structure
        paragraph_counts = [len(obj.split('\n\n')) for obj in objectives]
        avg_paragraphs = sum(paragraph_counts) / len(paragraph_counts) if paragraph_counts else 0

        patterns.append(SuccessPattern(
            pattern_type='structure',
            description='Typical objective structure',
            examples=[
                f"Average length: {avg_length:.0f} words",
                f"Average paragraphs: {avg_paragraphs:.1f}",
                "Most objectives follow: Problem → Approach → Expected Impact"
            ],
            frequency=0.8
        ))

        return patterns

    async def _extract_approach_patterns(
        self,
        projects: List[SimilarProject]
    ) -> List[SuccessPattern]:
        """Extract approach patterns from project metadata."""

        patterns = []

        # Analyze consortium sizes
        sizes = [p.participant_count for p in projects if p.participant_count > 0]
        if sizes:
            avg_size = sum(sizes) / len(sizes)
            patterns.append(SuccessPattern(
                pattern_type='approach',
                description='Typical consortium size',
                examples=[
                    f"Average: {avg_size:.1f} partners",
                    f"Range: {min(sizes)} to {max(sizes)} partners"
                ],
                frequency=0.9
            ))

        # Analyze funding amounts
        funding = [p.ec_contribution for p in projects if p.ec_contribution > 0]
        if funding:
            avg_funding = sum(funding) / len(funding)
            patterns.append(SuccessPattern(
                pattern_type='approach',
                description='Typical funding level',
                examples=[
                    f"Average: €{avg_funding/1_000_000:.1f}M",
                    f"Range: €{min(funding)/1_000_000:.1f}M to €{max(funding)/1_000_000:.1f}M"
                ],
                frequency=0.9
            ))

        return patterns

    # =========================================================================
    # SEMANTIC BENCHMARKER
    # =========================================================================

    async def benchmark_against_funded(
        self,
        user_text: str,
        section_type: str = "objectives",
        cluster: str = None,
        action_type: str = None
    ) -> Dict[str, Any]:
        """
        Benchmark user's text against funded proposals.

        Returns:
            {
                "similarity_percentile": 75,
                "similar_projects": [...],
                "patterns_matched": [...],
                "patterns_missing": [...],
                "improvement_suggestions": [...],
                "example_excerpts": [...]
            }
        """

        logger.info(f"Benchmarking {section_type} section against funded projects")

        # Find similar projects
        similar = await self.find_similar_funded_projects(
            user_idea=user_text,
            cluster=cluster,
            action_type=action_type,
            limit=20
        )

        if not similar:
            return {
                "similarity_percentile": 0,
                "similar_projects": [],
                "patterns_matched": [],
                "patterns_missing": ["No similar projects found for comparison"],
                "improvement_suggestions": ["Try adjusting cluster or action type filters"],
                "example_excerpts": []
            }

        # Calculate percentile based on similarity
        user_similarity = similar[0].similarity_score if similar else 0
        similarities = [p.similarity_score for p in similar]
        percentile = (sum(1 for s in similarities if user_similarity >= s) / len(similarities)) * 100

        # Extract patterns from successful projects
        patterns = await self.extract_success_patterns(similar, "all")

        # Check which patterns user's text matches
        user_text_lower = user_text.lower()
        matched = []
        missing = []

        for pattern in patterns:
            if pattern.pattern_type == 'terminology':
                # Check if user uses the common terms
                matched_examples = [
                    ex for ex in pattern.examples
                    if any(term.lower() in user_text_lower
                          for term in ex.split("'")[1:2])
                ]
                if matched_examples:
                    matched.append(f"Good terminology: {', '.join(matched_examples[:3])}")
                else:
                    missing.append(f"Consider using: {', '.join(pattern.examples[:3])}")

        # Generate improvement suggestions
        suggestions = await self._generate_benchmark_suggestions(
            user_text=user_text,
            similar_projects=similar[:5],
            patterns=patterns
        )

        # Get example excerpts from top projects
        excerpts = [
            {
                "project": p.acronym,
                "excerpt": p.objective[:500] + "..." if len(p.objective) > 500 else p.objective,
                "similarity": p.similarity_score,
                "funding": p.ec_contribution
            }
            for p in similar[:3]
        ]

        return {
            "similarity_percentile": round(percentile, 1),
            "similar_projects": [
                {
                    "acronym": p.acronym,
                    "title": p.title,
                    "similarity": p.similarity_score,
                    "funding": p.ec_contribution,
                    "cluster": p.cluster
                }
                for p in similar[:5]
            ],
            "patterns_matched": matched,
            "patterns_missing": missing,
            "improvement_suggestions": suggestions,
            "example_excerpts": excerpts
        }

    async def _generate_benchmark_suggestions(
        self,
        user_text: str,
        similar_projects: List[SimilarProject],
        patterns: List[SuccessPattern]
    ) -> List[str]:
        """Generate specific improvement suggestions based on benchmark."""

        suggestions = []
        user_text_lower = user_text.lower()

        # Check length
        user_words = len(user_text.split())
        avg_words = sum(len(p.objective.split()) for p in similar_projects) / len(similar_projects)

        if user_words < avg_words * 0.7:
            suggestions.append(
                f"Consider expanding your text. Similar funded projects average "
                f"{avg_words:.0f} words, yours has {user_words}."
            )
        elif user_words > avg_words * 1.5:
            suggestions.append(
                f"Consider being more concise. Similar funded projects average "
                f"{avg_words:.0f} words, yours has {user_words}."
            )

        # Check for key elements
        if 'european' not in user_text_lower and 'eu' not in user_text_lower:
            suggestions.append(
                "Add explicit European dimension - reference EU strategies, "
                "European added value, or pan-European impact."
            )

        if 'impact' not in user_text_lower:
            suggestions.append(
                "Include expected impact - successful proposals clearly state "
                "societal, economic, or scientific impact."
            )

        if not any(word in user_text_lower for word in ['novel', 'innovative', 'breakthrough', 'beyond']):
            suggestions.append(
                "Emphasize innovation - use terms like 'novel', 'innovative', "
                "'breakthrough', or 'beyond state of the art'."
            )

        return suggestions[:5]  # Limit to top 5

    # =========================================================================
    # EXAMPLE PROVIDER
    # =========================================================================

    async def get_section_examples(
        self,
        section_type: str,
        cluster: str = None,
        action_type: str = None,
        min_quality_score: float = 0.7,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get high-quality examples of specific sections from funded projects.

        Note: For now, uses CORDIS objectives as examples.
        Future: Use proposal_examples table with actual proposal sections.
        """

        pool = await self._get_db_pool()

        # Build filters
        filters = ["p.status = 'SIGNED'", "LENGTH(p.objective) > 500"]
        params = [limit]
        param_idx = 2

        if cluster:
            filters.append(f"p.cluster = ${param_idx}")
            params.append(cluster)
            param_idx += 1

        if action_type:
            filters.append(f"p.action_type = ${param_idx}")
            params.append(action_type)
            param_idx += 1

        filter_clause = " AND ".join(filters)

        # Get high-funded projects as proxy for quality
        query = f"""
            SELECT
                p.acronym,
                p.title,
                p.objective,
                p.ec_contribution,
                p.cluster,
                p.action_type,
                p.participant_count
            FROM projects p
            WHERE {filter_clause}
            ORDER BY p.ec_contribution DESC
            LIMIT $1
        """

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            {
                "acronym": row['acronym'],
                "title": row['title'],
                "example_text": row['objective'],
                "funding": row['ec_contribution'],
                "cluster": row['cluster'],
                "action_type": row['action_type'],
                "consortium_size": row['participant_count'],
                "section_type": section_type,
                "quality_indicators": [
                    "High funding level",
                    f"Cluster: {row['cluster']}",
                    f"Action type: {row['action_type']}"
                ]
            }
            for row in rows
        ]

    async def get_language_suggestions(
        self,
        user_text: str,
        similar_projects: List[SimilarProject]
    ) -> List[Dict[str, Any]]:
        """
        Suggest better language based on successful proposals.

        Returns phrases from funded projects that user could adapt.
        """

        if not similar_projects:
            return []

        suggestions = []

        # Extract strong phrases from successful objectives
        for project in similar_projects[:5]:
            objective = project.objective

            # Find sentences with strong verbs
            sentences = objective.split('.')
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 50 and len(sentence) < 300:
                    # Check for strong indicators
                    strong_indicators = [
                        'will develop', 'will create', 'will demonstrate',
                        'aims to', 'breakthrough', 'innovative', 'novel',
                        'European added value', 'state of the art'
                    ]

                    if any(ind in sentence.lower() for ind in strong_indicators):
                        suggestions.append({
                            "source_project": project.acronym,
                            "phrase": sentence + ".",
                            "why_effective": "Uses strong, confident language",
                            "adaptation_hint": "Adapt the structure for your specific context"
                        })

        return suggestions[:10]  # Limit to 10 suggestions
```

---

### Step 2: Create API Endpoints

**File:** `app/api/proposal_learning_routes.py`

```python
"""
Proposal Learning API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.proposal_writing.proposal_learning_service import ProposalLearningService

router = APIRouter(prefix="/api/proposal/learning", tags=["Proposal Learning"])

learning_service = ProposalLearningService()


class SimilarProjectsRequest(BaseModel):
    user_idea: str
    cluster: Optional[str] = None
    action_type: Optional[str] = None
    min_funding: Optional[float] = None
    limit: int = 10


class BenchmarkRequest(BaseModel):
    user_text: str
    section_type: str = "objectives"
    cluster: Optional[str] = None
    action_type: Optional[str] = None


@router.post("/similar-projects")
async def find_similar_projects(request: SimilarProjectsRequest):
    """
    Find funded projects similar to user's idea.

    Use this to:
    - Research what's been funded in your area
    - Find potential consortium partners
    - Understand typical funding levels
    """
    try:
        projects = await learning_service.find_similar_funded_projects(
            user_idea=request.user_idea,
            cluster=request.cluster,
            action_type=request.action_type,
            min_funding=request.min_funding,
            limit=request.limit
        )

        return {
            "projects": [
                {
                    "acronym": p.acronym,
                    "title": p.title,
                    "similarity_score": p.similarity_score,
                    "ec_contribution": p.ec_contribution,
                    "cluster": p.cluster,
                    "action_type": p.action_type,
                    "coordinator_country": p.coordinator_country,
                    "participant_count": p.participant_count,
                    "objective_preview": p.objective[:300] + "..." if len(p.objective) > 300 else p.objective
                }
                for p in projects
            ],
            "total_found": len(projects)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/benchmark")
async def benchmark_section(request: BenchmarkRequest):
    """
    Benchmark your section against funded proposals.

    Returns:
    - Similarity percentile (how your text compares)
    - Patterns you're using well
    - Patterns you're missing
    - Specific improvement suggestions
    """
    try:
        result = await learning_service.benchmark_against_funded(
            user_text=request.user_text,
            section_type=request.section_type,
            cluster=request.cluster,
            action_type=request.action_type
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/examples")
async def get_examples(
    section_type: str = "objectives",
    cluster: Optional[str] = None,
    action_type: Optional[str] = None,
    limit: int = 5
):
    """
    Get high-quality examples from funded projects.
    """
    try:
        examples = await learning_service.get_section_examples(
            section_type=section_type,
            cluster=cluster,
            action_type=action_type,
            limit=limit
        )

        return {"examples": examples}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patterns")
async def extract_patterns(request: SimilarProjectsRequest):
    """
    Extract success patterns from similar funded projects.
    """
    try:
        # First find similar projects
        projects = await learning_service.find_similar_funded_projects(
            user_idea=request.user_idea,
            cluster=request.cluster,
            action_type=request.action_type,
            limit=20
        )

        # Extract patterns
        patterns = await learning_service.extract_success_patterns(projects, "all")

        return {
            "patterns": [
                {
                    "type": p.pattern_type,
                    "description": p.description,
                    "examples": p.examples,
                    "frequency": p.frequency
                }
                for p in patterns
            ],
            "based_on_projects": len(projects)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### Step 3: Integrate with Draft Generator

**File:** Update `app/services/proposal_writing/draft_generator.py`

```python
# Add to imports
from app.services.proposal_writing.proposal_learning_service import ProposalLearningService

class ProposalDraftGenerator:
    def __init__(self, call_doc_service, template_service):
        # ... existing init ...
        self.learning_service = ProposalLearningService()

    async def generate_section_draft(
        self,
        call_id: str,
        section_id: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:

        # ... existing code ...

        # NEW: Find similar funded projects for context
        similar_projects = await self.learning_service.find_similar_funded_projects(
            user_idea=user_context.get('project_idea', ''),
            cluster=call_analysis['cluster']['code'],
            action_type=call_analysis.get('action_type'),
            limit=5
        )

        # NEW: Extract patterns
        patterns = await self.learning_service.extract_success_patterns(
            similar_projects, "all"
        )

        # NEW: Include in prompt
        prompt = self._build_context_aware_prompt(
            section_id=section_id,
            call_id=call_id,
            call_analysis=call_analysis,
            cluster_terms=cluster_terms,
            user_context=user_context,
            guidance=guidance,
            similar_projects=similar_projects,  # NEW
            patterns=patterns  # NEW
        )

        # ... rest of generation ...
```

---

## Testing Plan

```python
# tests/test_proposal_learning.py

import pytest
from app.services.proposal_writing.proposal_learning_service import ProposalLearningService

@pytest.fixture
def service():
    return ProposalLearningService()

@pytest.mark.asyncio
async def test_find_similar_projects(service):
    """Test finding similar funded projects."""
    projects = await service.find_similar_funded_projects(
        user_idea="Development of AI-powered diagnostic tools for early cancer detection",
        cluster="CL1",
        limit=5
    )

    assert len(projects) <= 5
    assert all(hasattr(p, 'similarity_score') for p in projects)
    assert all(0 <= p.similarity_score <= 1 for p in projects)

@pytest.mark.asyncio
async def test_benchmark_against_funded(service):
    """Test benchmarking user text."""
    result = await service.benchmark_against_funded(
        user_text="We will develop innovative AI solutions for healthcare.",
        section_type="objectives",
        cluster="CL1"
    )

    assert "similarity_percentile" in result
    assert "patterns_matched" in result
    assert "improvement_suggestions" in result

@pytest.mark.asyncio
async def test_extract_patterns(service):
    """Test pattern extraction."""
    projects = await service.find_similar_funded_projects(
        user_idea="Renewable energy storage solutions",
        cluster="CL5",
        limit=10
    )

    patterns = await service.extract_success_patterns(projects, "terminology")

    assert len(patterns) > 0
    assert all(hasattr(p, 'pattern_type') for p in patterns)
```

---

## Acceptance Criteria

- [ ] `find_similar_funded_projects()` returns relevant projects
- [ ] Similarity scores are accurate (semantic, not just keyword)
- [ ] Pattern extraction identifies meaningful patterns
- [ ] Benchmark provides actionable insights
- [ ] Integration with draft generator improves quality
- [ ] API endpoints work correctly
- [ ] Performance is acceptable (<2s for most operations)

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `app/services/proposal_writing/proposal_learning_service.py` | CREATE |
| `app/api/proposal_learning_routes.py` | CREATE |
| `app/services/proposal_writing/draft_generator.py` | MODIFY |
| `app/main.py` | MODIFY (add router) |
| `tests/test_proposal_learning.py` | CREATE |

---

## Next Task

After completing this task, proceed to:
→ **Task 06: Populate Proposal Examples from CORDIS**
