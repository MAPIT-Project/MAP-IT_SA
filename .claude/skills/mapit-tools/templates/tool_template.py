"""
{TOOL_NAME} Tool for Horizon Europe / Erasmus+ / Creative Europe.

{TOOL_DESCRIPTION}

ARCHITECTURE: {HYBRID|GRAPH|SQL|VECTOR}
- Graph (Neo4j): {Graph description}
- SQL (PostgreSQL): {SQL description}
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()
logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

CLUSTER_KEYWORDS = {
    'CLUSTER-1': ['health', 'medical', 'clinical', 'disease', 'pandemic', 'pharmaceutical'],
    'CLUSTER-2': ['culture', 'heritage', 'democracy', 'migration', 'social'],
    'CLUSTER-3': ['security', 'cybersecurity', 'border', 'defense', 'resilience'],
    'CLUSTER-4': ['digital', 'AI', 'artificial intelligence', 'data', 'cloud', 'robotics'],
    'CLUSTER-5': ['climate', 'energy', 'hydrogen', 'solar', 'wind', 'transport', 'battery'],
    'CLUSTER-6': ['food', 'agriculture', 'biodiversity', 'ocean', 'water', 'bioeconomy'],
}

CLUSTER_MAP = {
    'CLUSTER1': 'CLUSTER-1', 'CLUSTER-1': 'CLUSTER-1', 'CL1': 'CLUSTER-1', 'HEALTH': 'CLUSTER-1',
    'CLUSTER2': 'CLUSTER-2', 'CLUSTER-2': 'CLUSTER-2', 'CL2': 'CLUSTER-2', 'CULTURE': 'CLUSTER-2',
    'CLUSTER3': 'CLUSTER-3', 'CLUSTER-3': 'CLUSTER-3', 'CL3': 'CLUSTER-3', 'SECURITY': 'CLUSTER-3',
    'CLUSTER4': 'CLUSTER-4', 'CLUSTER-4': 'CLUSTER-4', 'CL4': 'CLUSTER-4', 'DIGITAL': 'CLUSTER-4',
    'CLUSTER5': 'CLUSTER-5', 'CLUSTER-5': 'CLUSTER-5', 'CL5': 'CLUSTER-5', 'CLIMATE': 'CLUSTER-5',
    'CLUSTER6': 'CLUSTER-6', 'CLUSTER-6': 'CLUSTER-6', 'CL6': 'CLUSTER-6', 'FOOD': 'CLUSTER-6',
}


# ============================================================================
# TOOL CLASS
# ============================================================================

class {ToolClassName}:
    """
    {Tool description}

    HYBRID ARCHITECTURE:
    - Graph: {Graph purpose}
    - SQL: {SQL purpose}
    """

    def __init__(self):
        """Initialize database connections with graceful degradation."""
        self.db_url = os.getenv("DATABASE_URL")

        # Lazy-load graph service
        self._graph_service = None
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            self._graph_service = GraphSearchService()
            logger.info("{ToolClassName}: Graph service available")
        except Exception as e:
            logger.warning(f"{ToolClassName}: Graph service not available: {e}")

    def _get_connection(self):
        """Get PostgreSQL database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _normalize_cluster_code(self, cluster: Optional[str]) -> Optional[str]:
        """Normalize cluster code to CLUSTER-X format."""
        if not cluster:
            return None
        cluster_upper = cluster.upper().strip().replace(' ', '-')
        return CLUSTER_MAP.get(cluster_upper)

    def _infer_clusters_from_keywords(self, keywords: str) -> List[str]:
        """Infer Horizon Europe clusters from research keywords."""
        keywords_lower = keywords.lower()
        matched = []
        for cluster_code, kw_list in CLUSTER_KEYWORDS.items():
            if any(kw in keywords_lower for kw in kw_list):
                matched.append(cluster_code)
        return matched if matched else ['CLUSTER-4']

    # ========================================================================
    # MAIN PUBLIC METHOD
    # ========================================================================

    def {main_method_name}(
        self,
        required_param: str,
        optional_param: Optional[str] = None,
        cluster: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        {Method description}

        Args:
            required_param: {Description}
            optional_param: {Description}
            cluster: Optional cluster filter (e.g., 'CL5', 'CLIMATE')
            limit: Maximum results to return

        Returns:
            Dict with success status, results, and metadata
        """
        try:
            # Normalize inputs
            normalized_cluster = self._normalize_cluster_code(cluster)
            inferred_clusters = []

            if not normalized_cluster:
                inferred_clusters = self._infer_clusters_from_keywords(required_param)
                normalized_cluster = inferred_clusters[0] if inferred_clusters else None

            # Execute hybrid query
            results = self._execute_hybrid(
                required_param,
                optional_param,
                normalized_cluster,
                limit
            )

            return {
                "success": True,
                "tool_name": "{tool_name}",
                "query_params": {
                    "required_param": required_param,
                    "optional_param": optional_param,
                    "cluster": cluster,
                    "limit": limit
                },
                "results": results.get('data', []),
                "total_found": len(results.get('data', [])),
                "metadata": {
                    "search_type": results.get('search_type', 'sql_only'),
                    "sources_used": results.get('sources_used', ['sql']),
                    "inferred_clusters": inferred_clusters,
                    "cluster_used": normalized_cluster,
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"{ToolClassName} error: {e}")
            return {
                "success": False,
                "tool_name": "{tool_name}",
                "error": str(e),
                "message": "Failed to execute tool. Please try again.",
                "suggestions": [
                    "Check your input parameters",
                    "Try using different keywords"
                ]
            }

    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================

    def _execute_hybrid(
        self,
        param1: str,
        param2: Optional[str],
        cluster: Optional[str],
        limit: int
    ) -> Dict[str, Any]:
        """Execute hybrid Graph+SQL query."""
        graph_results = []
        sql_results = []
        sources_used = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}

            # Submit graph query if available
            if self._graph_service:
                futures['graph'] = executor.submit(
                    self._query_graph, param1, cluster, limit
                )

            # Always submit SQL query
            futures['sql'] = executor.submit(
                self._query_sql, param1, param2, cluster, limit
            )

            # Collect results with timeout
            for key, future in futures.items():
                try:
                    result = future.result(timeout=30)
                    if result:
                        if key == 'graph':
                            graph_results = result
                            sources_used.append('graph')
                        else:
                            sql_results = result
                            sources_used.append('sql')
                except Exception as e:
                    logger.warning(f"{key} query failed: {e}")

        # Merge results
        merged = self._merge_results(graph_results, sql_results, limit)

        return {
            'data': merged,
            'search_type': 'hybrid' if len(sources_used) > 1 else sources_used[0] if sources_used else 'none',
            'sources_used': sources_used
        }

    def _query_graph(self, param1: str, cluster: Optional[str], limit: int) -> List[Dict]:
        """Query Neo4j graph database."""
        if not self._graph_service:
            return []

        try:
            # TODO: Implement your graph query
            # Example:
            # return self._graph_service.find_by_cluster(cluster, limit=limit)
            return []
        except Exception as e:
            logger.error(f"Graph query error: {e}")
            return []

    def _query_sql(
        self,
        param1: str,
        param2: Optional[str],
        cluster: Optional[str],
        limit: int
    ) -> List[Dict]:
        """Query PostgreSQL database."""
        conn = self._get_connection()
        if not conn:
            return []

        cursor = None
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build query dynamically
            query = """
                SELECT id, title, objective, total_cost
                FROM projects
                WHERE 1=1
            """
            params = []

            if param1:
                query += " AND (title ILIKE %s OR objective ILIKE %s)"
                params.extend([f"%{param1}%", f"%{param1}%"])

            # Add cluster filter if provided
            # (Adjust table/column names as needed)

            query += " LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"SQL query error: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def _merge_results(
        self,
        graph_results: List[Dict],
        sql_results: List[Dict],
        limit: int
    ) -> List[Dict]:
        """
        Merge results using RRF (Reciprocal Rank Fusion).

        For simpler merging, you can use weighted averaging instead.
        """
        k = 60  # RRF constant

        scores = {}
        items = {}
        sources = {}

        # Score graph results
        for rank, item in enumerate(graph_results, 1):
            key = str(item.get('id', f"graph_{rank}"))
            scores[key] = scores.get(key, 0) + (1.0 / (k + rank))
            items[key] = item
            sources.setdefault(key, set()).add('graph')

        # Score SQL results
        for rank, item in enumerate(sql_results, 1):
            key = str(item.get('id', f"sql_{rank}"))
            scores[key] = scores.get(key, 0) + (1.0 / (k + rank))
            if key not in items:
                items[key] = item
            sources.setdefault(key, set()).add('sql')

        # Boost items found in both sources
        for key in scores:
            if len(sources.get(key, set())) > 1:
                scores[key] += 0.005

        # Sort by score and return
        ranked_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [items[key] for key in ranked_keys[:limit]]


# ============================================================================
# ASYNC EXECUTE FUNCTION (Entry point for ToolAwareAgent)
# ============================================================================

async def {tool_name}_execute(
    params: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute {tool_name} tool.

    This tool {brief description}.
    Use when users {usage guidance}.

    HYBRID ARCHITECTURE:
    - Graph: {Graph description}
    - SQL: {SQL description}
    """
    # Parameter fallback handling (LLM might use different names)
    required_param = (
        params.get('required_param') or
        params.get('keywords') or
        params.get('query') or
        params.get('search')
    )

    if not required_param:
        return {
            "success": False,
            "error": "required_param is required",
            "tool_name": "{tool_name}",
            "suggestions": ["Provide keywords or search terms"]
        }

    # Extract optional parameters
    optional_param = params.get('optional_param')
    cluster = (
        params.get('cluster') or
        params.get('cluster_code') or
        params.get('pillar')
    )
    limit = params.get('limit', 10)

    # Create tool instance and execute
    tool = {ToolClassName}()
    return tool.{main_method_name}(
        required_param=required_param,
        optional_param=optional_param,
        cluster=cluster,
        limit=limit
    )
