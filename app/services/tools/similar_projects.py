"""
Similar Projects Tool for Horizon Europe.

ENHANCED with Hybrid Vector+Graph Architecture:
- Uses pgvector embeddings for semantic similarity search
- Uses Neo4j graph database for graph-based reranking and context
- Combines embedding scores with graph relationships
- Cluster inference from keywords
- Enhanced consortium context from graph

Finds funded projects semantically similar to a user's project description
using vector embeddings (768-dim, Google text-embedding-004) and graph context.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import numpy as np

load_dotenv()
logger = logging.getLogger(__name__)


# Cluster keyword mapping for automatic cluster inference
CLUSTER_KEYWORDS = {
    'CLUSTER-1': [
        'health', 'medical', 'clinical', 'disease', 'patient', 'healthcare',
        'hospital', 'therapy', 'diagnosis', 'pharmaceutical', 'cancer',
        'vaccine', 'drug', 'pandemic', 'infection', 'mental health'
    ],
    'CLUSTER-2': [
        'culture', 'democracy', 'social', 'heritage', 'creative', 'inclusive',
        'society', 'governance', 'media', 'migration', 'education'
    ],
    'CLUSTER-3': [
        'security', 'cybersecurity', 'border', 'crime', 'disaster',
        'resilience', 'defence', 'terrorism', 'critical infrastructure'
    ],
    'CLUSTER-4': [
        'digital', 'AI', 'artificial intelligence', 'data', 'industry',
        'space', 'manufacturing', 'robotics', 'computing', 'machine learning',
        'quantum', 'electronics', 'semiconductor', 'cloud', 'IoT'
    ],
    'CLUSTER-5': [
        'climate', 'energy', 'mobility', 'transport', 'hydrogen', 'battery',
        'renewable', 'green', 'carbon', 'solar', 'wind', 'electric vehicle',
        'decarbonization', 'sustainability', 'smart grid', 'fuel cell'
    ],
    'CLUSTER-6': [
        'food', 'agriculture', 'bioeconomy', 'biodiversity', 'ocean', 'marine',
        'environment', 'soil', 'water', 'forestry', 'fisheries', 'farming'
    ]
}

# Cluster mapping for topic codes
CLUSTER_MAP = {
    'CL1': 'HLTH', 'CLUSTER1': 'HLTH', 'CLUSTER-1': 'HLTH', 'HEALTH': 'HLTH',
    'CL2': 'CL2', 'CLUSTER2': 'CL2', 'CLUSTER-2': 'CL2', 'CULTURE': 'CL2',
    'CL3': 'CL3', 'CLUSTER3': 'CL3', 'CLUSTER-3': 'CL3', 'SECURITY': 'CL3',
    'CL4': 'CL4', 'CLUSTER4': 'CL4', 'CLUSTER-4': 'CL4', 'DIGITAL': 'CL4',
    'CL5': 'CL5', 'CLUSTER5': 'CL5', 'CLUSTER-5': 'CL5', 'CLIMATE': 'CL5', 'ENERGY': 'CL5',
    'CL6': 'CL6', 'CLUSTER6': 'CL6', 'CLUSTER-6': 'CL6', 'FOOD': 'CL6',
    'EIC': 'EIC', 'ERC': 'ERC', 'MSCA': 'MSCA',
}

# Cluster to graph format
CLUSTER_TO_GRAPH = {
    'HLTH': 'CLUSTER-1',
    'CL1': 'CLUSTER-1',
    'CL2': 'CLUSTER-2',
    'CL3': 'CLUSTER-3',
    'CL4': 'CLUSTER-4',
    'CL5': 'CLUSTER-5',
    'CL6': 'CLUSTER-6',
}


class SimilarProjectsTool:
    """
    Tool to find funded projects semantically similar to a description.

    ENHANCED with Hybrid Vector+Graph Architecture:
    - Vector search (pgvector) for semantic similarity
    - Graph service (Neo4j) for reranking and context enhancement
    - Combined scoring for better relevance
    """

    def __init__(self):
        """Initialize with database connection, embedding service, and graph service."""
        self.db_url = os.getenv("DATABASE_URL")
        self._embedding_service = None

        if not self.db_url:
            logger.warning("DATABASE_URL not set - similar projects search will be limited")

        # Initialize graph service with graceful fallback
        self._graph_service = None
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            self._graph_service = GraphSearchService()
            logger.info("✅ Graph service available for similar projects")
        except Exception as e:
            logger.warning(f"⚠️ Graph service not available for similar projects: {e}")

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
        """Normalize cluster code for SQL queries."""
        cluster_upper = cluster.upper().replace(' ', '').replace('-', '')
        return CLUSTER_MAP.get(cluster_upper, cluster.upper())

    def _cluster_to_graph_code(self, cluster: str) -> Optional[str]:
        """Convert cluster code to graph format (CLUSTER-N)."""
        if not cluster:
            return None
        normalized = self._normalize_cluster(cluster)
        return CLUSTER_TO_GRAPH.get(normalized, f'CLUSTER-{normalized[-1]}' if normalized.startswith('CL') else None)

    def _infer_clusters_from_description(self, description: str) -> List[str]:
        """Infer clusters from project description."""
        if not description:
            return []

        desc_lower = description.lower()
        inferred = []

        for cluster, kw_list in CLUSTER_KEYWORDS.items():
            for kw in kw_list:
                if kw.lower() in desc_lower:
                    if cluster not in inferred:
                        inferred.append(cluster)
                    break

        return inferred

    def find_similar(
        self,
        description: str,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        min_budget: Optional[int] = None,
        max_budget: Optional[int] = None,
        year_from: Optional[int] = None,
        limit: int = 10,
        similarity_threshold: float = 0.3,
        rerank_with_graph: bool = True,
        include_graph_context: bool = True
    ) -> Dict[str, Any]:
        """
        Find funded Horizon Europe projects semantically similar to a description.

        ENHANCED with Hybrid Vector+Graph Architecture:
        - Uses embedding similarity as primary signal
        - Optionally reranks using graph context
        - Includes graph-enhanced consortium information

        Args:
            description: Project idea or description to match against
            cluster: Optional cluster filter (CL4, CL5, etc.)
            action_type: Optional action type filter (RIA, IA, CSA)
            min_budget: Optional minimum EU contribution
            max_budget: Optional maximum EU contribution
            year_from: Optional filter for projects starting from year
            limit: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            rerank_with_graph: Whether to rerank results using graph context (default: True)
            include_graph_context: Include graph-enhanced project details (default: True)

        Returns:
            Similar projects with similarity scores and graph-enhanced details
        """
        if not description or len(description.strip()) < 20:
            return {
                "success": False,
                "tool_name": "get_similar_funded_projects",
                "error": "Description must be at least 20 characters",
                "message": "Please provide a more detailed project description for better matching."
            }

        # Infer clusters from description if not provided
        inferred_clusters = []
        if not cluster:
            inferred_clusters = self._infer_clusters_from_description(description)
            if inferred_clusters:
                logger.info(f"Inferred clusters from description: {inferred_clusters}")

        # Get graph cluster code
        graph_cluster = None
        if cluster:
            graph_cluster = self._cluster_to_graph_code(cluster)
        elif inferred_clusters:
            graph_cluster = inferred_clusters[0]  # Use first inferred

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

            # Use hybrid approach if graph service available
            if self._graph_service and (rerank_with_graph or include_graph_context):
                return self._find_similar_hybrid(
                    description=description,
                    embedding_list=embedding_list,
                    cluster=cluster,
                    graph_cluster=graph_cluster,
                    action_type=action_type,
                    min_budget=min_budget,
                    max_budget=max_budget,
                    year_from=year_from,
                    limit=limit,
                    similarity_threshold=similarity_threshold,
                    rerank_with_graph=rerank_with_graph,
                    include_graph_context=include_graph_context,
                    inferred_clusters=inferred_clusters
                )

            # Fallback to vector-only search
            return self._find_similar_vector(
                description=description,
                embedding_list=embedding_list,
                cluster=cluster,
                action_type=action_type,
                min_budget=min_budget,
                max_budget=max_budget,
                year_from=year_from,
                limit=limit,
                similarity_threshold=similarity_threshold
            )

        except Exception as e:
            logger.error(f"Similar projects search error: {e}")
            import traceback
            traceback.print_exc()
            return self._get_keyword_fallback(description, cluster, action_type, limit)

    def _find_similar_hybrid(
        self,
        description: str,
        embedding_list: List[float],
        cluster: Optional[str],
        graph_cluster: Optional[str],
        action_type: Optional[str],
        min_budget: Optional[int],
        max_budget: Optional[int],
        year_from: Optional[int],
        limit: int,
        similarity_threshold: float,
        rerank_with_graph: bool,
        include_graph_context: bool,
        inferred_clusters: List[str]
    ) -> Dict[str, Any]:
        """
        Hybrid Vector+Graph search with optional reranking.
        """
        # Step 1: Get vector similarity results
        vector_results = self._get_vector_results(
            embedding_list=embedding_list,
            cluster=cluster,
            action_type=action_type,
            min_budget=min_budget,
            max_budget=max_budget,
            year_from=year_from,
            limit=limit * 2,  # Get more for reranking
            similarity_threshold=similarity_threshold
        )

        if not vector_results:
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
                "metadata": {
                    "search_type": "hybrid",
                    "sources_used": ["vector"]
                },
                "timestamp": datetime.now().isoformat()
            }

        # Step 2: Enhance with graph context (parallel queries)
        if include_graph_context:
            vector_results = self._enhance_with_graph_context(vector_results, graph_cluster)

        # Step 3: Rerank using graph signals if requested
        if rerank_with_graph and self._graph_service:
            vector_results = self._rerank_with_graph(vector_results, graph_cluster)

        # Take top results after reranking
        final_results = vector_results[:limit]

        # Format results
        similar_projects = self._format_results(final_results)

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
            "metadata": {
                "search_type": "hybrid",
                "sources_used": ["vector", "graph"] if include_graph_context else ["vector"],
                "reranked_with_graph": rerank_with_graph,
                "inferred_clusters": inferred_clusters
            },
            "timestamp": datetime.now().isoformat()
        }

    def _get_vector_results(
        self,
        embedding_list: List[float],
        cluster: Optional[str],
        action_type: Optional[str],
        min_budget: Optional[int],
        max_budget: Optional[int],
        year_from: Optional[int],
        limit: int,
        similarity_threshold: float
    ) -> List[Dict]:
        """Get vector similarity results from pgvector."""
        conn = self._get_connection()
        if not conn:
            return []

        try:
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

            params_with_embedding = [embedding_list] + params + [embedding_list, limit, similarity_threshold]
            cursor.execute(sql, params_with_embedding)
            results = cursor.fetchall()

            # Get basic consortium info from SQL
            output = []
            for r in results:
                project_id = r['id']

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

                output.append({
                    'id': str(r['id']),
                    'acronym': r['acronym'],
                    'title': r['title'],
                    'objective': r['objective'],
                    'total_cost': float(r['totalCost'] or 0),
                    'eu_contribution': float(r['ecMaxContribution'] or 0),
                    'start_date': str(r['startDate'])[:10] if r['startDate'] else None,
                    'end_date': str(r['endDate'])[:10] if r['endDate'] else None,
                    'status': r['status'],
                    'action_type': r['fundingScheme'],
                    'topics': r['topics'],
                    'similarity_score': float(r['similarity_score']),
                    'consortium': {
                        'size': int(consortium['partner_count'] or 0),
                        'countries': int(consortium['country_count'] or 0),
                        'coordinator_name': consortium['coordinator_name'],
                        'coordinator_country': consortium['coordinator_country'],
                        'org_types': consortium['org_types'] or [],
                        'country_list': consortium['countries'][:10] if consortium['countries'] else []
                    }
                })

            cursor.close()
            conn.close()
            return output

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            if conn:
                conn.close()
            return []

    def _enhance_with_graph_context(
        self,
        results: List[Dict],
        graph_cluster: Optional[str]
    ) -> List[Dict]:
        """Enhance results with graph context (parallel queries)."""
        if not self._graph_service or not results:
            return results

        def get_graph_project_info(project_id: str) -> Optional[Dict]:
            """Get graph-based info for a project."""
            try:
                # Get similar projects count from graph
                similar = self._graph_service.find_similar_projects(
                    project_id,
                    similarity_type='cluster',
                    limit=5
                )
                return {
                    'graph_similar_count': len(similar) if similar else 0,
                    'graph_similar': similar[:3] if similar else []
                }
            except Exception as e:
                logger.warning(f"Graph project info query failed for {project_id}: {e}")
                return None

        # Parallel queries for graph context
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(get_graph_project_info, r['id']): i
                for i, r in enumerate(results[:10])  # Only top 10 for performance
            }

            for future in futures:
                idx = futures[future]
                try:
                    graph_info = future.result()
                    if graph_info:
                        results[idx]['graph_context'] = graph_info
                except Exception as e:
                    logger.warning(f"Graph context query failed: {e}")

        return results

    def _rerank_with_graph(
        self,
        results: List[Dict],
        graph_cluster: Optional[str]
    ) -> List[Dict]:
        """Rerank results by combining embedding score with graph signals."""
        for r in results:
            embedding_score = r.get('similarity_score', 0)

            # Graph signals
            graph_context = r.get('graph_context', {})
            graph_similar_count = graph_context.get('graph_similar_count', 0)

            # Consortium size (larger consortiums often indicate established topics)
            consortium_size = r.get('consortium', {}).get('size', 0)
            consortium_score = min(consortium_size / 15, 1.0) * 0.1  # Normalize, cap at 15 partners

            # Graph similarity score (more graph-similar projects = more established area)
            graph_score = min(graph_similar_count / 5, 1.0) * 0.1  # Normalize, cap at 5

            # Budget score (higher budgets may indicate EU priority)
            budget = r.get('eu_contribution', 0)
            budget_score = min(budget / 10_000_000, 1.0) * 0.05  # Normalize, cap at 10M

            # Combined score (embedding weighted highest)
            r['combined_score'] = (
                embedding_score * 0.75 +
                graph_score +
                consortium_score +
                budget_score
            )

        # Sort by combined score
        results.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
        return results

    def _format_results(self, results: List[Dict]) -> List[Dict]:
        """Format results for output."""
        formatted = []
        for i, r in enumerate(results):
            keywords = self._extract_keywords(r.get('objective', ''))

            project = {
                "rank": i + 1,
                "similarity_score": round(r.get('similarity_score', 0), 3),
                "combined_score": round(r.get('combined_score', r.get('similarity_score', 0)), 3),
                "acronym": r.get('acronym') or 'N/A',
                "title": r.get('title') or 'N/A',
                "cordis_id": r.get('id'),
                "cordis_url": f"https://cordis.europa.eu/project/id/{r.get('id')}",
                "objective_summary": self._summarize_text(r.get('objective', ''), 300),
                "total_cost": round(r.get('total_cost', 0), 0),
                "eu_contribution": round(r.get('eu_contribution', 0), 0),
                "start_date": r.get('start_date'),
                "end_date": r.get('end_date'),
                "status": r.get('status') or 'unknown',
                "action_type": r.get('action_type') or 'N/A',
                "topics": r.get('topics') or '',
                "consortium": {
                    "size": r.get('consortium', {}).get('size', 0),
                    "countries": r.get('consortium', {}).get('countries', 0),
                    "coordinator": {
                        "name": r.get('consortium', {}).get('coordinator_name') or 'Unknown',
                        "country": r.get('consortium', {}).get('coordinator_country') or 'Unknown'
                    },
                    "country_list": r.get('consortium', {}).get('country_list', [])
                },
                "keywords": keywords[:8]
            }

            # Add graph context if available
            if r.get('graph_context'):
                project['graph_context'] = {
                    'similar_projects_in_cluster': r['graph_context'].get('graph_similar_count', 0)
                }

            formatted.append(project)

        return formatted

    def _find_similar_vector(
        self,
        description: str,
        embedding_list: List[float],
        cluster: Optional[str],
        action_type: Optional[str],
        min_budget: Optional[int],
        max_budget: Optional[int],
        year_from: Optional[int],
        limit: int,
        similarity_threshold: float
    ) -> Dict[str, Any]:
        """Vector-only search (fallback when graph not available)."""
        vector_results = self._get_vector_results(
            embedding_list=embedding_list,
            cluster=cluster,
            action_type=action_type,
            min_budget=min_budget,
            max_budget=max_budget,
            year_from=year_from,
            limit=limit,
            similarity_threshold=similarity_threshold
        )

        if not vector_results:
            return {
                "success": True,
                "tool_name": "get_similar_funded_projects",
                "query_description": description[:200] + "..." if len(description) > 200 else description,
                "projects_searched": "13,850+",
                "matches_found": 0,
                "similar_projects": [],
                "message": "No similar projects found. Try a different description or lower the similarity threshold.",
                "data_source": "cordis_embeddings",
                "metadata": {
                    "search_type": "vector_only",
                    "sources_used": ["vector"]
                },
                "timestamp": datetime.now().isoformat()
            }

        similar_projects = self._format_results(vector_results)
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
            "metadata": {
                "search_type": "vector_only",
                "sources_used": ["vector"]
            },
            "timestamp": datetime.now().isoformat()
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key terms from text (simple approach)."""
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

        words = text.lower().split()
        keywords = []

        for word in words:
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
        action_types = {}

        for p in projects:
            topics = p.get('topics', '')
            if topics:
                parts = topics.split(';') if ';' in topics else [topics]
                for topic in parts:
                    topic = topic.strip()
                    if topic:
                        topic_parts = topic.split('-')
                        if len(topic_parts) >= 3:
                            prefix = '-'.join(topic_parts[:3])
                            topic_counts[prefix] = topic_counts.get(prefix, 0) + 1

            budget = p.get('eu_contribution', 0)
            if budget > 0:
                budgets.append(budget)

            at = p.get('action_type', 'Unknown')
            action_types[at] = action_types.get(at, 0) + 1

        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        topic_analysis = {
            "most_common_topics": [{"topic": t[0], "count": t[1]} for t in sorted_topics[:5]],
            "funding_range": {
                "min": min(budgets) if budgets else 0,
                "max": max(budgets) if budgets else 0,
                "average": sum(budgets) / len(budgets) if budgets else 0
            }
        }

        if budgets:
            avg_budget = sum(budgets) / len(budgets)
            insights.append(f"Average EU contribution for similar projects: €{avg_budget/1_000_000:.1f}M")

        if sorted_topics:
            top_topic = sorted_topics[0][0]
            insights.append(f"Most common topic area: {top_topic}")

        consortium_sizes = [p.get('consortium', {}).get('size', 0) for p in projects]
        if consortium_sizes:
            avg_size = sum(consortium_sizes) / len(consortium_sizes)
            insights.append(f"Typical consortium size: {avg_size:.0f} partners")

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

            keywords = self._extract_keywords(description)[:5]

            if not keywords:
                return {
                    "success": False,
                    "tool_name": "get_similar_funded_projects",
                    "error": "No keywords extracted",
                    "message": "Could not extract meaningful keywords from description."
                }

            where_conditions = ["p.\"frameworkProgramme\" = 'HORIZON'"]
            params = []

            keyword_conditions = []
            for kw in keywords:
                keyword_conditions.append("(p.objective ILIKE %s OR p.title ILIKE %s)")
                params.extend([f"%{kw}%", f"%{kw}%"])

            if keyword_conditions:
                where_conditions.append(f"({' OR '.join(keyword_conditions)})")

            if cluster:
                cluster_normalized = self._normalize_cluster(cluster)
                where_conditions.append("p.topics ILIKE %s")
                params.append(f"%{cluster_normalized}%")

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
                    "similarity_score": 0.0,
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
                "metadata": {
                    "search_type": "keyword_fallback",
                    "sources_used": ["keyword"]
                },
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
    description using AI embeddings and graph-based reranking.

    ENHANCED with Hybrid Vector+Graph Architecture for:
    - Embedding similarity as primary signal
    - Graph-based reranking for better relevance
    - Graph-enhanced consortium context
    - Cluster inference from description
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
        similarity_threshold=params.get('similarity_threshold', 0.3),
        rerank_with_graph=params.get('rerank_with_graph', True),
        include_graph_context=params.get('include_graph_context', True)
    )
