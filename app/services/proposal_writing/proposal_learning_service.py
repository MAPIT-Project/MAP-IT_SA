"""
Proposal Learning Service

Learn from 13,865+ funded CORDIS projects to improve proposal quality.
"""

import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.services.embedding_service import EmbeddingService

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
    examples: list[str]
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

    def _get_db_connection(self):
        """Get database connection using psycopg2."""
        import psycopg2
        from psycopg2.extras import RealDictCursor

        if not settings.database_url:
            raise RuntimeError("DATABASE_URL not configured")

        return psycopg2.connect(settings.database_url, cursor_factory=RealDictCursor)

    # =========================================================================
    # SIMILAR PROJECT FINDER
    # =========================================================================

    async def find_similar_funded_projects(
        self,
        user_idea: str,
        cluster: str = None,
        action_type: str = None,
        min_funding: float = None,
        limit: int = 10,
    ) -> list[SimilarProject]:
        """
        Find funded projects semantically similar to user's idea.

        Args:
            user_idea: User's project idea/description
            cluster: Filter by cluster (CL1-CL6, ERC, EIC, MSCA) - not used yet
            action_type: Filter by action type (RIA, IA, CSA)
            min_funding: Minimum EC contribution
            limit: Maximum results to return

        Returns:
            List of similar funded projects with similarity scores
        """

        logger.info(f"Finding similar funded projects for idea: {user_idea[:100]}...")

        if not user_idea or len(user_idea.strip()) < 10:
            logger.warning("User idea too short for meaningful search")
            return []

        try:
            # Generate embedding for user's idea
            user_embedding = self.embedding_service.generate_embedding(user_idea)
            user_embedding_list = user_embedding.tolist()

            conn = self._get_db_connection()
            cursor = conn.cursor()

            try:
                # Build filter conditions
                filters = ["pe.embedding_status = 'completed'", "pe.combined_embedding IS NOT NULL"]
                params = [user_embedding_list, user_embedding_list, limit]

                if action_type:
                    filters.append('p."fundingScheme" ILIKE %s')
                    params.insert(-1, f"%{action_type}%")

                if min_funding:
                    filters.append('p."ecMaxContribution" >= %s')
                    params.insert(-1, min_funding)

                filter_clause = " AND ".join(filters)

                query = f"""
                    SELECT
                        p.id,
                        p.acronym,
                        p.title,
                        p.objective,
                        p."ecMaxContribution" as ec_contribution,
                        p."fundingScheme" as action_type,
                        p."startDate" as start_date,
                        1 - (pe.combined_embedding <=> %s::vector) as similarity_score
                    FROM projects p
                    JOIN project_embeddings pe ON p.id = pe.project_id
                    WHERE {filter_clause}
                    ORDER BY pe.combined_embedding <=> %s::vector
                    LIMIT %s
                """

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [
                    SimilarProject(
                        project_id=str(row["id"]),
                        acronym=row["acronym"] or "",
                        title=row["title"] or "",
                        objective=row["objective"] or "",
                        similarity_score=float(row["similarity_score"]),
                        ec_contribution=float(row["ec_contribution"] or 0),
                        cluster="",  # Not in current schema
                        action_type=row["action_type"] or "",
                        start_date=str(row["start_date"]) if row["start_date"] else "",
                        coordinator_country="",  # Would need join
                        participant_count=0,  # Would need join
                    )
                    for row in rows
                ]

            finally:
                cursor.close()
                conn.close()

        except Exception as e:
            logger.error(f"Error finding similar projects: {e}")
            # Fall back to keyword search
            return await self.find_projects_by_keywords(keywords=user_idea.split()[:5], limit=limit)

    async def find_projects_by_keywords(
        self, keywords: list[str], cluster: str = None, limit: int = 20
    ) -> list[SimilarProject]:
        """
        Find funded projects by keyword matching (fallback method).
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            try:
                # Build keyword search using PostgreSQL full-text
                keyword_string = " | ".join(keywords[:5])

                query = """
                    SELECT
                        p.id,
                        p.acronym,
                        p.title,
                        p.objective,
                        p."ecMaxContribution" as ec_contribution,
                        p."fundingScheme" as action_type,
                        p."startDate" as start_date,
                        0.5 as similarity_score
                    FROM projects p
                    WHERE to_tsvector('english', COALESCE(p.title, '') || ' ' || COALESCE(p.objective, ''))
                          @@ to_tsquery('english', %s)
                    ORDER BY p."ecMaxContribution" DESC NULLS LAST
                    LIMIT %s
                """

                cursor.execute(query, (keyword_string, limit))
                rows = cursor.fetchall()

                return [
                    SimilarProject(
                        project_id=str(row["id"]),
                        acronym=row["acronym"] or "",
                        title=row["title"] or "",
                        objective=row["objective"] or "",
                        similarity_score=float(row["similarity_score"]),
                        ec_contribution=float(row["ec_contribution"] or 0),
                        cluster="",
                        action_type=row["action_type"] or "",
                        start_date=str(row["start_date"]) if row["start_date"] else "",
                        coordinator_country="",
                        participant_count=0,
                    )
                    for row in rows
                ]

            finally:
                cursor.close()
                conn.close()

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    # =========================================================================
    # PATTERN EXTRACTOR
    # =========================================================================

    async def extract_success_patterns(
        self, similar_projects: list[SimilarProject], pattern_type: str = "all"
    ) -> list[SuccessPattern]:
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

        if pattern_type in ["terminology", "all"]:
            patterns.extend(self._extract_terminology_patterns(objectives))

        if pattern_type in ["language", "all"]:
            patterns.extend(self._extract_language_patterns(objectives))

        if pattern_type in ["structure", "all"]:
            patterns.extend(self._extract_structure_patterns(objectives))

        if pattern_type in ["approach", "all"]:
            patterns.extend(self._extract_approach_patterns(similar_projects))

        return patterns

    def _extract_terminology_patterns(self, objectives: list[str]) -> list[SuccessPattern]:
        """Extract commonly used terminology from successful proposals."""

        # Key EU/HE terms to look for
        eu_terms = [
            "state of the art",
            "beyond",
            "innovative",
            "novel",
            "breakthrough",
            "cutting-edge",
            "transformative",
            "sustainable",
            "scalable",
            "replicable",
            "stakeholder",
            "end-user",
            "societal",
            "TRL",
            "demonstrat",
            "validat",
            "pilot",
            "dissemination",
            "exploitation",
            "impact",
            "European added value",
            "cross-border",
            "pan-European",
        ]

        combined_text = " ".join(objectives).lower()
        found_terms = {}

        for term in eu_terms:
            count = combined_text.count(term.lower())
            if count > 0:
                frequency = count / len(objectives) if objectives else 0
                found_terms[term] = frequency

        # Sort by frequency
        sorted_terms = sorted(found_terms.items(), key=lambda x: x[1], reverse=True)

        if sorted_terms:
            return [
                SuccessPattern(
                    pattern_type="terminology",
                    description="Commonly used terms in successful proposals",
                    examples=[
                        f"{term} (used in {freq * 100:.0f}% of similar projects)"
                        for term, freq in sorted_terms[:10]
                    ],
                    frequency=(
                        sum(f for _, f in sorted_terms[:5]) / 5 if len(sorted_terms) >= 5 else 0.5
                    ),
                )
            ]

        return []

    def _extract_language_patterns(self, objectives: list[str]) -> list[SuccessPattern]:
        """Extract effective language patterns."""

        patterns = []

        # Look for strong opening patterns
        strong_openings = [
            "will develop",
            "aims to",
            "seeks to",
            "will create",
            "will establish",
            "will demonstrate",
            "addresses the",
            "tackles the",
            "responds to",
        ]

        combined_text = " ".join(objectives).lower()

        opening_counts = {op: combined_text.count(op) for op in strong_openings}

        top_openings = sorted(opening_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        if top_openings and any(count > 0 for _, count in top_openings):
            patterns.append(
                SuccessPattern(
                    pattern_type="language",
                    description="Effective opening phrases",
                    examples=[
                        f"'{op}' - used {count} times" for op, count in top_openings if count > 0
                    ],
                    frequency=(
                        sum(c for _, c in top_openings) / len(objectives) if objectives else 0
                    ),
                )
            )

        return patterns

    def _extract_structure_patterns(self, objectives: list[str]) -> list[SuccessPattern]:
        """Extract structural patterns from objectives."""

        patterns = []

        if not objectives:
            return patterns

        # Analyze average length
        lengths = [len(obj.split()) for obj in objectives]
        avg_length = sum(lengths) / len(lengths) if lengths else 0

        # Analyze paragraph structure
        paragraph_counts = [len(obj.split("\n\n")) for obj in objectives]
        avg_paragraphs = sum(paragraph_counts) / len(paragraph_counts) if paragraph_counts else 0

        patterns.append(
            SuccessPattern(
                pattern_type="structure",
                description="Typical objective structure",
                examples=[
                    f"Average length: {avg_length:.0f} words",
                    f"Average paragraphs: {avg_paragraphs:.1f}",
                    "Most objectives follow: Problem → Approach → Expected Impact",
                ],
                frequency=0.8,
            )
        )

        return patterns

    def _extract_approach_patterns(self, projects: list[SimilarProject]) -> list[SuccessPattern]:
        """Extract approach patterns from project metadata."""

        patterns = []

        # Analyze consortium sizes
        sizes = [p.participant_count for p in projects if p.participant_count > 0]
        if sizes:
            avg_size = sum(sizes) / len(sizes)
            patterns.append(
                SuccessPattern(
                    pattern_type="approach",
                    description="Typical consortium size",
                    examples=[
                        f"Average: {avg_size:.1f} partners",
                        f"Range: {min(sizes)} to {max(sizes)} partners",
                    ],
                    frequency=0.9,
                )
            )

        # Analyze funding amounts
        funding = [p.ec_contribution for p in projects if p.ec_contribution > 0]
        if funding:
            avg_funding = sum(funding) / len(funding)
            patterns.append(
                SuccessPattern(
                    pattern_type="approach",
                    description="Typical funding level",
                    examples=[
                        f"Average: €{avg_funding / 1_000_000:.1f}M",
                        f"Range: €{min(funding) / 1_000_000:.1f}M to €{max(funding) / 1_000_000:.1f}M",
                    ],
                    frequency=0.9,
                )
            )

        return patterns

    # =========================================================================
    # SEMANTIC BENCHMARKER
    # =========================================================================

    async def benchmark_against_funded(
        self,
        user_text: str,
        section_type: str = "objectives",
        cluster: str = None,
        action_type: str = None,
    ) -> dict[str, Any]:
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
            user_idea=user_text, cluster=cluster, action_type=action_type, limit=20
        )

        if not similar:
            return {
                "similarity_percentile": 0,
                "similar_projects": [],
                "patterns_matched": [],
                "patterns_missing": ["No similar projects found for comparison"],
                "improvement_suggestions": ["Try adjusting cluster or action type filters"],
                "example_excerpts": [],
            }

        # Calculate percentile based on similarity
        user_similarity = similar[0].similarity_score if similar else 0
        similarities = [p.similarity_score for p in similar]
        percentile = (
            sum(1 for s in similarities if user_similarity >= s) / len(similarities)
        ) * 100

        # Extract patterns from successful projects
        patterns = await self.extract_success_patterns(similar, "all")

        # Check which patterns user's text matches
        user_text_lower = user_text.lower()
        matched = []
        missing = []

        for pattern in patterns:
            if pattern.pattern_type == "terminology":
                # Check if user uses the common terms
                for example in pattern.examples:
                    # Extract term from "term (used in X%)" format
                    term = example.split(" (")[0] if " (" in example else example
                    if term.lower() in user_text_lower:
                        matched.append(f"Good use of: '{term}'")
                    else:
                        missing.append(f"Consider adding: '{term}'")

        # Limit lists
        matched = matched[:5]
        missing = missing[:5]

        # Generate improvement suggestions
        suggestions = self._generate_benchmark_suggestions(
            user_text=user_text, similar_projects=similar[:5], patterns=patterns
        )

        # Get example excerpts from top projects
        excerpts = [
            {
                "project": p.acronym,
                "excerpt": p.objective[:500] + "..." if len(p.objective) > 500 else p.objective,
                "similarity": round(p.similarity_score, 3),
                "funding": p.ec_contribution,
            }
            for p in similar[:3]
        ]

        return {
            "similarity_percentile": round(percentile, 1),
            "similar_projects": [
                {
                    "acronym": p.acronym,
                    "title": p.title,
                    "similarity": round(p.similarity_score, 3),
                    "funding": p.ec_contribution,
                    "cluster": p.cluster,
                }
                for p in similar[:5]
            ],
            "patterns_matched": matched,
            "patterns_missing": missing,
            "improvement_suggestions": suggestions,
            "example_excerpts": excerpts,
        }

    def _generate_benchmark_suggestions(
        self, user_text: str, similar_projects: list[SimilarProject], patterns: list[SuccessPattern]
    ) -> list[str]:
        """Generate specific improvement suggestions based on benchmark."""

        suggestions = []
        user_text_lower = user_text.lower()

        # Check length
        user_words = len(user_text.split())
        if similar_projects:
            avg_words = sum(len(p.objective.split()) for p in similar_projects) / len(
                similar_projects
            )

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
        if "european" not in user_text_lower and "eu" not in user_text_lower:
            suggestions.append(
                "Add explicit European dimension - reference EU strategies, "
                "European added value, or pan-European impact."
            )

        if "impact" not in user_text_lower:
            suggestions.append(
                "Include expected impact - successful proposals clearly state "
                "societal, economic, or scientific impact."
            )

        if not any(
            word in user_text_lower for word in ["novel", "innovative", "breakthrough", "beyond"]
        ):
            suggestions.append(
                "Emphasize innovation - use terms like 'novel', 'innovative', "
                "'breakthrough', or 'beyond state of the art'."
            )

        return suggestions[:5]  # Limit to top 5

    # =========================================================================
    # EXAMPLE PROVIDER
    # =========================================================================

    async def get_section_examples(
        self, section_type: str, cluster: str = None, action_type: str = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Get high-quality examples of specific sections from funded projects.

        Note: For now, uses CORDIS objectives as examples.
        Future: Use proposal_examples table with actual proposal sections.
        """

        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            try:
                # Build filters for high-quality projects
                filters = ["p.objective IS NOT NULL", "LENGTH(p.objective) > 500"]
                params = [limit]

                if action_type:
                    filters.append('p."fundingScheme" ILIKE %s')
                    params.insert(0, f"%{action_type}%")

                filter_clause = " AND ".join(filters)

                # Get top funded projects as proxy for quality
                query = f"""
                    SELECT
                        p.acronym,
                        p.title,
                        p.objective,
                        p."ecMaxContribution" as ec_contribution,
                        p."fundingScheme" as action_type
                    FROM projects p
                    WHERE {filter_clause}
                    ORDER BY p."ecMaxContribution" DESC NULLS LAST
                    LIMIT %s
                """

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [
                    {
                        "acronym": row["acronym"] or "",
                        "title": row["title"] or "",
                        "example_text": row["objective"] or "",
                        "funding": float(row["ec_contribution"] or 0),
                        "cluster": "",
                        "action_type": row["action_type"] or "",
                        "consortium_size": 0,
                        "section_type": section_type,
                        "quality_indicators": [
                            "High funding level",
                            f"Action type: {row['action_type'] or 'N/A'}",
                        ],
                    }
                    for row in rows
                ]

            finally:
                cursor.close()
                conn.close()

        except Exception as e:
            logger.error(f"Error getting section examples: {e}")
            return []

    async def get_language_suggestions(
        self, user_text: str, similar_projects: list[SimilarProject]
    ) -> list[dict[str, Any]]:
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
            sentences = objective.split(".")
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 50 and len(sentence) < 300:
                    # Check for strong indicators
                    strong_indicators = [
                        "will develop",
                        "will create",
                        "will demonstrate",
                        "aims to",
                        "breakthrough",
                        "innovative",
                        "novel",
                        "European added value",
                        "state of the art",
                    ]

                    if any(ind in sentence.lower() for ind in strong_indicators):
                        suggestions.append(
                            {
                                "source_project": project.acronym,
                                "phrase": sentence + ".",
                                "why_effective": "Uses strong, confident language",
                                "adaptation_hint": "Adapt the structure for your specific context",
                            }
                        )

        return suggestions[:10]  # Limit to 10 suggestions
