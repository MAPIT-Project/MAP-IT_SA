"""
Similar Projects Tool for Horizon Europe.

Finds funded projects semantically similar to a user's project description
using vector embeddings (768-dim, Google text-embedding-004).
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import numpy as np

load_dotenv()
logger = logging.getLogger(__name__)

# Cluster mapping
CLUSTER_MAP = {
    'CL1': 'HLTH', 'CLUSTER1': 'HLTH', 'CLUSTER-1': 'HLTH', 'HEALTH': 'HLTH',
    'CL2': 'CL2', 'CLUSTER2': 'CL2', 'CLUSTER-2': 'CL2', 'CULTURE': 'CL2',
    'CL3': 'CL3', 'CLUSTER3': 'CL3', 'CLUSTER-3': 'CL3', 'SECURITY': 'CL3',
    'CL4': 'CL4', 'CLUSTER4': 'CL4', 'CLUSTER-4': 'CL4', 'DIGITAL': 'CL4',
    'CL5': 'CL5', 'CLUSTER5': 'CL5', 'CLUSTER-5': 'CL5', 'CLIMATE': 'CL5', 'ENERGY': 'CL5',
    'CL6': 'CL6', 'CLUSTER6': 'CL6', 'CLUSTER-6': 'CL6', 'FOOD': 'CL6',
    'EIC': 'EIC', 'ERC': 'ERC', 'MSCA': 'MSCA',
}


class SimilarProjectsTool:
    """Tool to find funded projects semantically similar to a description."""

    def __init__(self):
        """Initialize with database connection and embedding service."""
        self.db_url = os.getenv("DATABASE_URL")
        self._embedding_service = None

        if not self.db_url:
            logger.warning("DATABASE_URL not set - similar projects search will be limited")

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _get_embedding_service(self):
        """Lazy load embedding service."""
        if self._embedding_service is None:
            try:
                from ..embedding_service import EmbeddingService
                self._embedding_service = EmbeddingService()
            except Exception as e:
                logger.error(f"Failed to initialize embedding service: {e}")
                return None
        return self._embedding_service

    def _normalize_cluster(self, cluster: str) -> str:
        """Normalize cluster code."""
        cluster_upper = cluster.upper().replace(' ', '').replace('-', '')
        return CLUSTER_MAP.get(cluster_upper, cluster.upper())

    def find_similar(
        self,
        description: str,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        min_budget: Optional[int] = None,
        max_budget: Optional[int] = None,
        year_from: Optional[int] = None,
        limit: int = 10,
        similarity_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Find funded Horizon Europe projects semantically similar to a description.

        Args:
            description: Project idea or description to match against
            cluster: Optional cluster filter (CL4, CL5, etc.)
            action_type: Optional action type filter (RIA, IA, CSA)
            min_budget: Optional minimum EU contribution
            max_budget: Optional maximum EU contribution
            year_from: Optional filter for projects starting from year
            limit: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            Similar projects with similarity scores and details
        """
        if not description or len(description.strip()) < 20:
            return {
                "success": False,
                "tool_name": "get_similar_funded_projects",
                "error": "Description must be at least 20 characters",
                "message": "Please provide a more detailed project description for better matching."
            }

        try:
            # Get embedding service
            embedding_service = self._get_embedding_service()
            if not embedding_service:
                return self._get_keyword_fallback(description, cluster, action_type, limit)

            # Generate embedding for user's description
            logger.info(f"Generating embedding for description ({len(description)} chars)")
            query_embedding = embedding_service.generate_query_embedding(description)

            if query_embedding is None or np.all(query_embedding == 0):
                logger.warning("Failed to generate embedding, falling back to keyword search")
                return self._get_keyword_fallback(description, cluster, action_type, limit)

            # Convert to list for PostgreSQL
            embedding_list = query_embedding.tolist()

            conn = self._get_connection()
            if not conn:
                return self._get_keyword_fallback(description, cluster, action_type, limit)

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build WHERE conditions
            where_conditions = ["p.\"frameworkProgramme\" = 'HORIZON'"]
            params = []

            # Cluster filter
            if cluster:
                cluster_normalized = self._normalize_cluster(cluster)
                where_conditions.append("p.topics ILIKE %s")
                params.append(f"%{cluster_normalized}%")

            # Action type filter
            if action_type:
                where_conditions.append("p.\"fundingScheme\" ILIKE %s")
                params.append(f"%{action_type.upper()}%")

            # Budget filters
            if min_budget:
                where_conditions.append("p.\"ecMaxContribution\" >= %s")
                params.append(min_budget)

            if max_budget:
                where_conditions.append("p.\"ecMaxContribution\" <= %s")
                params.append(max_budget)

            # Year filter
            if year_from:
                where_conditions.append("EXTRACT(YEAR FROM p.\"startDate\") >= %s")
                params.append(year_from)

            where_clause = " AND ".join(where_conditions)

            # Vector similarity search using pgvector
            # Using cosine distance: 1 - (a <=> b) gives similarity score
            sql = f"""
                WITH similar_results AS (
                    SELECT
                        p.id,
                        p.acronym,
                        p.title,
                        p.objective,
                        p."totalCost",
                        p."ecMaxContribution",
                        p."startDate",
                        p."endDate",
                        p.status,
                        p."fundingScheme",
                        p.topics,
                        1 - (pe.combined_embedding <=> %s::vector) as similarity_score
                    FROM projects p
                    JOIN project_embeddings pe ON p.id = pe.project_id
                    WHERE {where_clause}
                      AND pe.combined_embedding IS NOT NULL
                    ORDER BY pe.combined_embedding <=> %s::vector
                    LIMIT %s
                )
                SELECT * FROM similar_results
                WHERE similarity_score >= %s
                ORDER BY similarity_score DESC
            """

            # Add embedding twice (for distance calculation and ordering)
            params_with_embedding = [embedding_list] + params + [embedding_list, limit * 2, similarity_threshold]

            cursor.execute(sql, params_with_embedding)
            results = cursor.fetchall()

            # Get consortium data for top results
            similar_projects = []
            for r in results[:limit]:
                project_id = r['id']

                # Get consortium info
                cursor.execute("""
                    SELECT
                        COUNT(DISTINCT "organisationID") as partner_count,
                        COUNT(DISTINCT country) as country_count,
                        MAX(CASE WHEN role = 'coordinator' THEN name END) as coordinator_name,
                        MAX(CASE WHEN role = 'coordinator' THEN country END) as coordinator_country,
                        ARRAY_AGG(DISTINCT "activityType") FILTER (WHERE "activityType" IS NOT NULL) as org_types,
                        ARRAY_AGG(DISTINCT country) FILTER (WHERE country IS NOT NULL) as countries
                    FROM organizations
                    WHERE "projectID" = %s
                """, [project_id])
                consortium = cursor.fetchone()

                # Extract keywords from objective
                keywords = self._extract_keywords(r['objective'] or '')

                project = {
                    "rank": len(similar_projects) + 1,
                    "similarity_score": round(float(r['similarity_score']), 3),
                    "acronym": r['acronym'] or 'N/A',
                    "title": r['title'] or 'N/A',
                    "cordis_id": str(r['id']),
                    "cordis_url": f"https://cordis.europa.eu/project/id/{r['id']}",
                    "objective_summary": self._summarize_text(r['objective'] or '', 300),
                    "total_cost": round(float(r['totalCost'] or 0), 0),
                    "eu_contribution": round(float(r['ecMaxContribution'] or 0), 0),
                    "start_date": str(r['startDate'])[:10] if r['startDate'] else None,
                    "end_date": str(r['endDate'])[:10] if r['endDate'] else None,
                    "status": r['status'] or 'unknown',
                    "action_type": r['fundingScheme'] or 'N/A',
                    "topics": r['topics'] or '',
                    "consortium": {
                        "size": int(consortium['partner_count'] or 0),
                        "countries": int(consortium['country_count'] or 0),
                        "coordinator": {
                            "name": consortium['coordinator_name'] or 'Unknown',
                            "country": consortium['coordinator_country'] or 'Unknown'
                        },
                        "country_list": consortium['countries'][:10] if consortium['countries'] else []
                    },
                    "keywords": keywords[:8]
                }
                similar_projects.append(project)

            cursor.close()
            conn.close()

            if not similar_projects:
                return {
                    "success": True,
                    "tool_name": "get_similar_funded_projects",
                    "query_description": description[:200] + "..." if len(description) > 200 else description,
                    "projects_searched": "13,850+",
                    "matches_found": 0,
                    "similar_projects": [],
                    "message": "No similar projects found. Try a different description or lower the similarity threshold.",
                    "suggestions": [
                        "Use more specific technical terms",
                        "Remove filters (cluster, action_type) for broader search",
                        "Describe the methodology or approach in more detail"
                    ],
                    "data_source": "cordis_embeddings",
                    "timestamp": datetime.now().isoformat()
                }

            # Generate insights
            insights = self._generate_insights(similar_projects)

            return {
                "success": True,
                "tool_name": "get_similar_funded_projects",
                "query_description": description[:200] + "..." if len(description) > 200 else description,
                "filters_applied": {
                    "cluster": cluster,
                    "action_type": action_type,
                    "budget_range": f"€{min_budget or 0:,} - €{max_budget:,}" if max_budget else None
                },
                "projects_searched": "13,850+",
                "matches_found": len(similar_projects),
                "similar_projects": similar_projects,
                "topic_analysis": insights.get("topic_analysis", {}),
                "insights": insights.get("insights", []),
                "data_source": "cordis_embeddings",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Similar projects search error: {e}")
            import traceback
            traceback.print_exc()
            return self._get_keyword_fallback(description, cluster, action_type, limit)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key terms from text (simple approach)."""
        # Common stop words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'this', 'that', 'these', 'those', 'it', 'its', 'they', 'their',
            'which', 'who', 'whom', 'what', 'where', 'when', 'why', 'how',
            'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'not', 'only', 'same', 'so', 'than', 'too',
            'very', 'just', 'also', 'now', 'new', 'project', 'develop', 'research',
            'approach', 'system', 'based', 'using', 'use', 'used', 'provide',
            'including', 'well', 'through', 'within', 'between', 'into', 'over',
            'european', 'europe', 'eu', 'horizon'
        }

        # Simple word extraction
        words = text.lower().split()
        keywords = []

        for word in words:
            # Clean word
            clean_word = ''.join(c for c in word if c.isalnum())
            if len(clean_word) > 3 and clean_word not in stop_words:
                if clean_word not in keywords:
                    keywords.append(clean_word)

        return keywords[:15]

    def _summarize_text(self, text: str, max_length: int) -> str:
        """Summarize text to max length, ending at sentence boundary if possible."""
        if not text:
            return ""

        if len(text) <= max_length:
            return text

        # Try to end at sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        last_space = truncated.rfind(' ')

        if last_period > max_length * 0.7:
            return truncated[:last_period + 1]
        elif last_space > max_length * 0.8:
            return truncated[:last_space] + "..."

        return truncated + "..."

    def _generate_insights(self, projects: List[Dict]) -> Dict[str, Any]:
        """Generate insights from similar projects."""
        if not projects:
            return {"topic_analysis": {}, "insights": []}

        insights = []
        topic_counts = {}
        budgets = []
        durations = []
        action_types = {}

        for p in projects:
            # Extract topic codes
            topics = p.get('topics', '')
            if topics:
                # Extract main topic pattern (e.g., HORIZON-CL4-2023-...)
                parts = topics.split(';') if ';' in topics else [topics]
                for topic in parts:
                    topic = topic.strip()
                    if topic:
                        # Get topic prefix (first 3-4 parts)
                        topic_parts = topic.split('-')
                        if len(topic_parts) >= 3:
                            prefix = '-'.join(topic_parts[:3])
                            topic_counts[prefix] = topic_counts.get(prefix, 0) + 1

            # Collect budgets
            budget = p.get('eu_contribution', 0)
            if budget > 0:
                budgets.append(budget)

            # Action types
            at = p.get('action_type', 'Unknown')
            action_types[at] = action_types.get(at, 0) + 1

        # Topic analysis
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        topic_analysis = {
            "most_common_topics": [{"topic": t[0], "count": t[1]} for t in sorted_topics[:5]],
            "funding_range": {
                "min": min(budgets) if budgets else 0,
                "max": max(budgets) if budgets else 0,
                "average": sum(budgets) / len(budgets) if budgets else 0
            }
        }

        # Generate insights
        if budgets:
            avg_budget = sum(budgets) / len(budgets)
            insights.append(f"Average EU contribution for similar projects: €{avg_budget/1_000_000:.1f}M")

        if sorted_topics:
            top_topic = sorted_topics[0][0]
            insights.append(f"Most common topic area: {top_topic}")

        # Consortium insights
        consortium_sizes = [p.get('consortium', {}).get('size', 0) for p in projects]
        if consortium_sizes:
            avg_size = sum(consortium_sizes) / len(consortium_sizes)
            insights.append(f"Typical consortium size: {avg_size:.0f} partners")

        # Action type distribution
        if action_types:
            top_action = max(action_types.items(), key=lambda x: x[1])[0]
            insights.append(f"Most common action type: {top_action}")

        return {
            "topic_analysis": topic_analysis,
            "insights": insights
        }

    def _get_keyword_fallback(
        self,
        description: str,
        cluster: Optional[str],
        action_type: Optional[str],
        limit: int
    ) -> Dict[str, Any]:
        """Fallback to keyword search when embeddings unavailable."""
        try:
            conn = self._get_connection()
            if not conn:
                return {
                    "success": False,
                    "tool_name": "get_similar_funded_projects",
                    "error": "Database unavailable",
                    "message": "Cannot search for similar projects - database connection failed."
                }

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Extract keywords from description
            keywords = self._extract_keywords(description)[:5]

            if not keywords:
                return {
                    "success": False,
                    "tool_name": "get_similar_funded_projects",
                    "error": "No keywords extracted",
                    "message": "Could not extract meaningful keywords from description."
                }

            # Build keyword search
            where_conditions = ["p.\"frameworkProgramme\" = 'HORIZON'"]
            params = []

            # Add keyword conditions
            keyword_conditions = []
            for kw in keywords:
                keyword_conditions.append("(p.objective ILIKE %s OR p.title ILIKE %s)")
                params.extend([f"%{kw}%", f"%{kw}%"])

            if keyword_conditions:
                where_conditions.append(f"({' OR '.join(keyword_conditions)})")

            # Cluster filter
            if cluster:
                cluster_normalized = self._normalize_cluster(cluster)
                where_conditions.append("p.topics ILIKE %s")
                params.append(f"%{cluster_normalized}%")

            # Action type filter
            if action_type:
                where_conditions.append("p.\"fundingScheme\" ILIKE %s")
                params.append(f"%{action_type.upper()}%")

            where_clause = " AND ".join(where_conditions)

            sql = f"""
                SELECT
                    p.id,
                    p.acronym,
                    p.title,
                    p.objective,
                    p."ecMaxContribution",
                    p."startDate",
                    p."fundingScheme",
                    p.topics
                FROM projects p
                WHERE {where_clause}
                ORDER BY p."startDate" DESC NULLS LAST
                LIMIT %s
            """
            params.append(limit)

            cursor.execute(sql, params)
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            similar_projects = []
            for i, r in enumerate(results):
                similar_projects.append({
                    "rank": i + 1,
                    "similarity_score": 0.0,  # No embedding score
                    "acronym": r['acronym'] or 'N/A',
                    "title": r['title'] or 'N/A',
                    "cordis_id": str(r['id']),
                    "cordis_url": f"https://cordis.europa.eu/project/id/{r['id']}",
                    "objective_summary": self._summarize_text(r['objective'] or '', 300),
                    "eu_contribution": round(float(r['ecMaxContribution'] or 0), 0),
                    "start_date": str(r['startDate'])[:10] if r['startDate'] else None,
                    "action_type": r['fundingScheme'] or 'N/A',
                    "note": "Matched by keywords (embedding search unavailable)"
                })

            return {
                "success": True,
                "tool_name": "get_similar_funded_projects",
                "query_description": description[:200],
                "search_method": "keyword_fallback",
                "keywords_used": keywords,
                "matches_found": len(similar_projects),
                "similar_projects": similar_projects,
                "message": "Results based on keyword matching (semantic search unavailable).",
                "data_source": "cordis_keyword_search",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Keyword fallback error: {e}")
            return {
                "success": False,
                "tool_name": "get_similar_funded_projects",
                "error": str(e),
                "message": "Search failed. Please try again."
            }


# Async wrapper for tool orchestrator compatibility
async def get_similar_funded_projects_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute similar projects tool.

    This tool finds funded Horizon Europe projects semantically similar to a project
    description using AI embeddings. Use when users want to see examples of funded
    projects in their area, understand what got funded, or benchmark their idea.
    """
    tool = SimilarProjectsTool()

    description = params.get('description', '')
    if not description:
        return {
            "success": False,
            "error": "description is required",
            "tool_name": "get_similar_funded_projects"
        }

    return tool.find_similar(
        description=description,
        cluster=params.get('cluster'),
        action_type=params.get('action_type'),
        min_budget=params.get('min_budget'),
        max_budget=params.get('max_budget'),
        year_from=params.get('year_from'),
        limit=params.get('limit', 10),
        similarity_threshold=params.get('similarity_threshold', 0.3)
    )
