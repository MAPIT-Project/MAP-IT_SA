"""
Budget Benchmarking Tool for Horizon Europe Projects.

Provides real budget statistics from funded CORDIS projects to help users
set realistic budget expectations for their proposals.

HYBRID ARCHITECTURE: Combines Neo4j graph queries with PostgreSQL keyword search
for optimal results using RRF (Reciprocal Rank Fusion).
"""

import os
import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()
logger = logging.getLogger(__name__)


# Cluster keyword mapping for automatic cluster inference
CLUSTER_KEYWORDS = {
    'CLUSTER-1': ['health', 'medical', 'clinical', 'disease', 'patient', 'healthcare',
                  'hospital', 'therapy', 'diagnosis', 'pharmaceutical', 'cancer',
                  'vaccine', 'drug', 'pandemic', 'pathogen', 'infection'],
    'CLUSTER-2': ['culture', 'democracy', 'social', 'heritage', 'creative', 'inclusive',
                  'society', 'governance', 'media', 'migration', 'inequality', 'education'],
    'CLUSTER-3': ['security', 'cybersecurity', 'border', 'crime', 'disaster', 'resilience',
                  'defence', 'defense', 'terrorism', 'critical infrastructure', 'forensic'],
    'CLUSTER-4': ['digital', 'AI', 'artificial intelligence', 'data', 'industry', 'space',
                  'manufacturing', 'robotics', 'computing', 'machine learning', 'quantum',
                  'electronics', 'semiconductor', 'cloud', 'IoT', 'blockchain'],
    'CLUSTER-5': ['climate', 'energy', 'mobility', 'transport', 'hydrogen', 'battery',
                  'renewable', 'green', 'carbon', 'solar', 'wind', 'electric vehicle',
                  'sustainable', 'emission', 'fuel cell', 'smart grid'],
    'CLUSTER-6': ['food', 'agriculture', 'bioeconomy', 'biodiversity', 'ocean', 'environment',
                  'soil', 'water', 'forestry', 'marine', 'fisheries', 'circular economy',
                  'ecosystem', 'nature', 'farming']
}


class BudgetBenchmarkTool:
    """
    Tool to get budget benchmarks from funded Horizon Europe projects.

    HYBRID ARCHITECTURE:
    - Neo4j Graph: Pre-aggregated statistics, cluster relationships, consortium patterns
    - PostgreSQL: Keyword-based filtering, sample projects, detailed breakdowns
    - RRF Fusion: Combines results from both sources for comprehensive benchmarks
    """

    def __init__(self):
        """Initialize with database connection and graph service."""
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.warning("DATABASE_URL not set - budget benchmark will be limited")

        # Initialize graph service
        self._graph_service = None
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            self._graph_service = GraphSearchService()
            logger.info("✅ Graph service available for budget benchmarks")
        except Exception as e:
            logger.warning(f"⚠️ Graph service not available for budget benchmarks: {e}")

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _infer_clusters_from_keywords(self, keywords: str) -> List[str]:
        """
        Infer relevant clusters from topic keywords.

        Args:
            keywords: Research topic keywords

        Returns:
            List of cluster codes (e.g., ['CLUSTER-4', 'CLUSTER-5'])
        """
        if not keywords:
            return []

        keywords_lower = keywords.lower()
        inferred = []

        for cluster, cluster_keywords in CLUSTER_KEYWORDS.items():
            for kw in cluster_keywords:
                if kw.lower() in keywords_lower:
                    if cluster not in inferred:
                        inferred.append(cluster)
                    break

        return inferred

    def get_benchmark(
        self,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        topic_keywords: Optional[str] = None,
        year: Optional[int] = None,
        include_consortium_context: bool = True,
        include_org_type_breakdown: bool = True,
        include_country_breakdown: bool = False
    ) -> Dict[str, Any]:
        """
        Get budget benchmarks using HYBRID Graph+SQL architecture.

        Args:
            cluster: Cluster code (e.g., "CL4", "CL5", "CLUSTER-4")
            action_type: Action type (e.g., "RIA", "IA", "CSA")
            topic_keywords: Keywords to filter projects
            year: Filter by funding year
            include_consortium_context: Include consortium composition patterns
            include_org_type_breakdown: Include budget breakdown by organization type
            include_country_breakdown: Include budget breakdown by country

        Returns:
            Budget statistics with recommendations from hybrid sources
        """
        logger.info(f"get_benchmark called with: cluster={cluster!r}, action_type={action_type!r}, topic_keywords={topic_keywords!r}")

        # Normalize cluster code
        normalized_cluster = self._normalize_cluster_code(cluster)
        logger.info(f"get_benchmark: normalized_cluster={normalized_cluster!r}")

        # Infer clusters from keywords if no cluster specified
        inferred_clusters = []
        if topic_keywords and not normalized_cluster:
            inferred_clusters = self._infer_clusters_from_keywords(topic_keywords)
            if inferred_clusters:
                normalized_cluster = inferred_clusters[0]  # Use primary inferred cluster

        # Execute hybrid search
        result = self._get_benchmark_hybrid(
            cluster=normalized_cluster,
            action_type=action_type,
            topic_keywords=topic_keywords,
            year=year,
            include_consortium_context=include_consortium_context,
            include_org_type_breakdown=include_org_type_breakdown,
            include_country_breakdown=include_country_breakdown
        )

        # Add inferred clusters to metadata
        if inferred_clusters:
            result['metadata'] = result.get('metadata', {})
            result['metadata']['inferred_clusters'] = inferred_clusters

        return result

    def _normalize_cluster_code(self, cluster: Optional[str]) -> Optional[str]:
        """Normalize cluster code to CLUSTER-X format."""
        if not cluster:
            logger.debug(f"_normalize_cluster_code: input is None or empty")
            return None

        # Handle various input types
        if not isinstance(cluster, str):
            cluster = str(cluster)
            logger.debug(f"_normalize_cluster_code: converted non-string to '{cluster}'")

        # Strip whitespace
        cluster = cluster.strip()
        if not cluster:
            logger.debug(f"_normalize_cluster_code: empty after strip")
            return None

        cluster_upper = cluster.upper().replace(' ', '').replace('-', '')
        logger.debug(f"_normalize_cluster_code: input='{cluster}', normalized='{cluster_upper}'")

        # Map various formats to standard CLUSTER-X format
        cluster_map = {
            # Full names
            'CLUSTER1': 'CLUSTER-1', 'CLUSTER2': 'CLUSTER-2', 'CLUSTER3': 'CLUSTER-3',
            'CLUSTER4': 'CLUSTER-4', 'CLUSTER5': 'CLUSTER-5', 'CLUSTER6': 'CLUSTER-6',
            # Short codes CL1-CL6
            'CL1': 'CLUSTER-1', 'CL2': 'CLUSTER-2', 'CL3': 'CLUSTER-3',
            'CL4': 'CLUSTER-4', 'CL5': 'CLUSTER-5', 'CL6': 'CLUSTER-6',
            # Just numbers (1-6)
            '1': 'CLUSTER-1', '2': 'CLUSTER-2', '3': 'CLUSTER-3',
            '4': 'CLUSTER-4', '5': 'CLUSTER-5', '6': 'CLUSTER-6',
            # Thematic names
            'HEALTH': 'CLUSTER-1', 'HLTH': 'CLUSTER-1',
            'CULTURE': 'CLUSTER-2', 'SOCIETY': 'CLUSTER-2',
            'SECURITY': 'CLUSTER-3', 'CIVIL': 'CLUSTER-3',
            'DIGITAL': 'CLUSTER-4', 'INDUSTRY': 'CLUSTER-4', 'SPACE': 'CLUSTER-4',
            'CLIMATE': 'CLUSTER-5', 'ENERGY': 'CLUSTER-5', 'MOBILITY': 'CLUSTER-5',
            'FOOD': 'CLUSTER-6', 'BIO': 'CLUSTER-6', 'BIOECONOMY': 'CLUSTER-6',
        }

        result = cluster_map.get(cluster_upper)
        if result:
            logger.debug(f"_normalize_cluster_code: mapped '{cluster_upper}' to '{result}'")
            return result

        # Fallback for formats like "CLUSTER-4" that are already correct
        if cluster.upper().startswith('CLUSTER'):
            # Extract number and format properly
            match = re.search(r'(\d+)', cluster)
            if match:
                num = match.group(1)
                result = f"CLUSTER-{num}"
                logger.debug(f"_normalize_cluster_code: extracted number, result='{result}'")
                return result
            logger.warning(f"_normalize_cluster_code: starts with CLUSTER but no number found: '{cluster}'")
            return cluster.upper()

        logger.warning(f"_normalize_cluster_code: could not normalize '{cluster}', returning None")
        return None

    def _get_benchmark_hybrid(
        self,
        cluster: Optional[str],
        action_type: Optional[str],
        topic_keywords: Optional[str],
        year: Optional[int],
        include_consortium_context: bool,
        include_org_type_breakdown: bool,
        include_country_breakdown: bool
    ) -> Dict[str, Any]:
        """
        Execute hybrid Graph+SQL benchmark search.

        Runs both graph and SQL queries in parallel, then merges results.
        """
        graph_stats = None
        sql_stats = None
        consortium_patterns = None
        org_type_breakdown = None
        country_breakdown = None
        sample_projects = []

        # Use ThreadPoolExecutor for parallel queries
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}

            # Submit graph query if available
            if self._graph_service and cluster:
                futures['graph'] = executor.submit(
                    self._get_benchmark_graph,
                    cluster, action_type
                )

            # Submit SQL query
            futures['sql'] = executor.submit(
                self._get_benchmark_sql,
                cluster, action_type, topic_keywords, year
            )

            # Submit consortium patterns if requested
            if include_consortium_context and self._graph_service and cluster:
                futures['consortium'] = executor.submit(
                    self._get_consortium_context,
                    cluster
                )

            # Submit org type breakdown if requested
            if include_org_type_breakdown and cluster:
                futures['org_type'] = executor.submit(
                    self._get_budget_by_org_type,
                    cluster, action_type
                )

            # Submit country breakdown if requested
            if include_country_breakdown and cluster:
                futures['country'] = executor.submit(
                    self._get_budget_by_country,
                    cluster, action_type
                )

            # Collect results
            for key, future in futures.items():
                try:
                    result = future.result(timeout=30)
                    if key == 'graph':
                        graph_stats = result
                    elif key == 'sql':
                        sql_stats = result
                    elif key == 'consortium':
                        consortium_patterns = result
                    elif key == 'org_type':
                        org_type_breakdown = result
                    elif key == 'country':
                        country_breakdown = result
                except Exception as e:
                    logger.warning(f"Failed to get {key} benchmark: {e}")

        # Merge results using RRF-style fusion
        merged_stats = self._merge_benchmark_results(graph_stats, sql_stats)

        # Get sample projects from SQL
        if sql_stats and 'sample_projects' in sql_stats:
            sample_projects = sql_stats['sample_projects']

        # Build response
        statistics = merged_stats.get('statistics', {})
        project_count = statistics.get('projects_analyzed', 0)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            avg_budget=statistics.get('total_eu_contribution', {}).get('average', 0),
            median_budget=statistics.get('total_eu_contribution', {}).get('median', 0),
            std_dev=statistics.get('total_eu_contribution', {}).get('std_dev', 0),
            avg_partners=statistics.get('consortium_size', {}).get('average', 0),
            median_partners=statistics.get('consortium_size', {}).get('median', 0),
            avg_per_partner=statistics.get('budget_per_partner', {}).get('average', 0),
            action_type=action_type,
            project_count=project_count
        )

        result = {
            "success": True,
            "tool_name": "get_budget_benchmark",
            "query_params": {
                "cluster": cluster,
                "action_type": action_type,
                "topic_keywords": topic_keywords,
                "year": year
            },
            "statistics": statistics,
            "recommendations": recommendations,
            "sample_projects": sample_projects,
            "metadata": {
                "search_type": "hybrid" if graph_stats and sql_stats else ("graph_only" if graph_stats else "sql_only"),
                "sources_used": [],
                "graph_project_count": graph_stats.get('project_count', 0) if graph_stats else 0,
                "sql_project_count": sql_stats.get('project_count', 0) if sql_stats else 0
            },
            "timestamp": datetime.now().isoformat()
        }

        # Track sources used
        if graph_stats:
            result['metadata']['sources_used'].append('graph')
        if sql_stats:
            result['metadata']['sources_used'].append('sql')

        # Add optional breakdowns
        if consortium_patterns:
            result['consortium_context'] = consortium_patterns
        if org_type_breakdown:
            result['budget_by_org_type'] = org_type_breakdown
        if country_breakdown:
            result['budget_by_country'] = country_breakdown

        return result

    def _get_benchmark_graph(
        self,
        cluster: str,
        action_type: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Get budget statistics from Neo4j graph.

        Uses pre-aggregated statistics from the graph database.
        """
        if not self._graph_service:
            return None

        try:
            stats_list = self._graph_service.get_budget_statistics(
                cluster_code=cluster,
                action_type=action_type
            )

            if not stats_list:
                return None

            # Combine if multiple clusters returned
            if len(stats_list) == 1:
                stats = stats_list[0]
            else:
                # Aggregate across clusters
                stats = {
                    'project_count': sum(s.get('project_count', 0) for s in stats_list),
                    'total_funding': sum(s.get('total_funding', 0) for s in stats_list),
                    'avg_budget': sum(s.get('avg_budget', 0) * s.get('project_count', 1) for s in stats_list) / max(sum(s.get('project_count', 1) for s in stats_list), 1),
                    'min_budget': min(s.get('min_budget', float('inf')) for s in stats_list),
                    'max_budget': max(s.get('max_budget', 0) for s in stats_list),
                    'median_budget': stats_list[0].get('median_budget', 0),  # Approximate
                    'cluster_code': cluster,
                    'source': 'neo4j_graph'
                }

            return {
                'project_count': stats.get('project_count', 0),
                'total_funding': stats.get('total_funding', 0),
                'avg_budget': stats.get('avg_budget', 0),
                'min_budget': stats.get('min_budget', 0),
                'max_budget': stats.get('max_budget', 0),
                'median_budget': stats.get('median_budget', 0),
                'source': 'neo4j_graph'
            }

        except Exception as e:
            logger.error(f"Graph benchmark query failed: {e}")
            return None

    def _get_benchmark_sql(
        self,
        cluster: Optional[str],
        action_type: Optional[str],
        topic_keywords: Optional[str],
        year: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        """
        Get budget statistics from PostgreSQL.

        Supports keyword filtering and provides sample projects.
        """
        try:
            conn = self._get_connection()
            if not conn:
                return None

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build WHERE conditions
            where_conditions = ["p.\"frameworkProgramme\" = 'HORIZON'"]
            params = []

            # Cluster filter (in topics field)
            if cluster:
                # Map CLUSTER-X to topic patterns
                cluster_topic_map = {
                    'CLUSTER-1': 'HLTH',
                    'CLUSTER-2': 'CL2',
                    'CLUSTER-3': 'CL3',
                    'CLUSTER-4': 'CL4',
                    'CLUSTER-5': 'CL5',
                    'CLUSTER-6': 'CL6',
                }
                topic_pattern = cluster_topic_map.get(cluster, cluster)
                where_conditions.append("p.topics ILIKE %s")
                params.append(f"%{topic_pattern}%")

            # Action type filter
            if action_type:
                action_normalized = action_type.upper()
                where_conditions.append("p.\"fundingScheme\" ILIKE %s")
                params.append(f"%{action_normalized}%")

            # Topic keywords filter
            if topic_keywords:
                keywords = topic_keywords.split()
                for kw in keywords:
                    where_conditions.append(
                        "(p.objective ILIKE %s OR p.title ILIKE %s OR p.topics ILIKE %s)"
                    )
                    params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])

            # Year filter
            if year:
                where_conditions.append("EXTRACT(YEAR FROM p.\"startDate\") = %s")
                params.append(year)

            where_clause = " AND ".join(where_conditions)

            # Main statistics query
            stats_sql = f"""
                WITH project_stats AS (
                    SELECT
                        p.id,
                        p.acronym,
                        p.title,
                        p."totalCost",
                        p."ecMaxContribution",
                        p."fundingScheme",
                        p.topics,
                        p."startDate",
                        COUNT(DISTINCT o."organisationID") as partner_count
                    FROM projects p
                    LEFT JOIN organizations o ON p.id = o."projectID"
                    WHERE {where_clause}
                    GROUP BY p.id, p.acronym, p.title, p."totalCost",
                             p."ecMaxContribution", p."fundingScheme", p.topics, p."startDate"
                    HAVING p."ecMaxContribution" > 0 AND COUNT(DISTINCT o."organisationID") > 0
                )
                SELECT
                    COUNT(*) as project_count,
                    MIN("ecMaxContribution") as min_budget,
                    MAX("ecMaxContribution") as max_budget,
                    AVG("ecMaxContribution") as avg_budget,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY "ecMaxContribution") as median_budget,
                    STDDEV("ecMaxContribution") as std_dev,
                    SUM("ecMaxContribution") as total_funding,
                    AVG(partner_count) as avg_partners,
                    MIN(partner_count) as min_partners,
                    MAX(partner_count) as max_partners,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY partner_count) as median_partners,
                    AVG("ecMaxContribution" / NULLIF(partner_count, 0)) as avg_per_partner
                FROM project_stats
            """

            cursor.execute(stats_sql, params)
            stats_row = cursor.fetchone()

            if not stats_row or stats_row['project_count'] == 0:
                cursor.close()
                conn.close()
                return None

            # Get sample projects
            sample_sql = f"""
                SELECT
                    p.acronym,
                    p.title,
                    p."ecMaxContribution" as eu_contribution,
                    p."totalCost" as total_cost,
                    p."fundingScheme",
                    p.topics,
                    p."startDate",
                    COUNT(DISTINCT o."organisationID") as partner_count
                FROM projects p
                LEFT JOIN organizations o ON p.id = o."projectID"
                WHERE {where_clause}
                GROUP BY p.id, p.acronym, p.title, p."ecMaxContribution",
                         p."totalCost", p."fundingScheme", p.topics, p."startDate"
                HAVING p."ecMaxContribution" > 0
                ORDER BY p."startDate" DESC
                LIMIT 5
            """

            cursor.execute(sample_sql, params)
            sample_projects = cursor.fetchall()

            cursor.close()
            conn.close()

            return {
                'project_count': int(stats_row['project_count']),
                'total_funding': float(stats_row['total_funding'] or 0),
                'avg_budget': float(stats_row['avg_budget'] or 0),
                'min_budget': float(stats_row['min_budget'] or 0),
                'max_budget': float(stats_row['max_budget'] or 0),
                'median_budget': float(stats_row['median_budget'] or 0),
                'std_dev': float(stats_row['std_dev'] or 0),
                'avg_partners': float(stats_row['avg_partners'] or 0),
                'min_partners': int(stats_row['min_partners'] or 0),
                'max_partners': int(stats_row['max_partners'] or 0),
                'median_partners': float(stats_row['median_partners'] or 0),
                'avg_per_partner': float(stats_row['avg_per_partner'] or 0),
                'source': 'postgresql',
                'sample_projects': [
                    {
                        "acronym": p.get('acronym') or 'N/A',
                        "title": (p.get('title') or '')[:80] + ('...' if len(p.get('title') or '') > 80 else ''),
                        "eu_contribution": round(float(p.get('eu_contribution') or 0), 0),
                        "partners": int(p.get('partner_count') or 0),
                        "action_type": p.get('fundingScheme') or p.get('fundingscheme') or 'N/A',
                        "start_year": p.get('startDate').year if p.get('startDate') else None
                    }
                    for p in sample_projects
                ]
            }

        except Exception as e:
            logger.error(f"SQL benchmark query failed: {e}")
            return None

    def _merge_benchmark_results(
        self,
        graph_stats: Optional[Dict[str, Any]],
        sql_stats: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge benchmark results from Graph and SQL using weighted averaging.

        Graph data is pre-aggregated and accurate for cluster-level stats.
        SQL data supports keyword filtering and provides more details.
        """
        # If only one source available, use it
        if not graph_stats and not sql_stats:
            return self._get_fallback_benchmarks(None, None)

        if not graph_stats:
            return self._format_sql_stats(sql_stats)

        if not sql_stats:
            return self._format_graph_stats(graph_stats)

        # Both sources available - merge with weighted averaging
        # Weight by project count (more projects = more reliable)
        graph_count = graph_stats.get('project_count', 0)
        sql_count = sql_stats.get('project_count', 0)
        total_count = graph_count + sql_count

        if total_count == 0:
            return self._get_fallback_benchmarks(None, None)

        graph_weight = graph_count / total_count
        sql_weight = sql_count / total_count

        # Weighted average for key metrics
        avg_budget = (
            graph_stats.get('avg_budget', 0) * graph_weight +
            sql_stats.get('avg_budget', 0) * sql_weight
        )

        # Use SQL for median (more accurate with keyword filtering)
        median_budget = sql_stats.get('median_budget', graph_stats.get('median_budget', 0))

        # Use the more extreme min/max values
        min_budget = min(
            graph_stats.get('min_budget', float('inf')),
            sql_stats.get('min_budget', float('inf'))
        )
        max_budget = max(
            graph_stats.get('max_budget', 0),
            sql_stats.get('max_budget', 0)
        )

        # Use SQL for partner stats (has more detail)
        avg_partners = sql_stats.get('avg_partners', 0)
        median_partners = sql_stats.get('median_partners', 0)
        avg_per_partner = sql_stats.get('avg_per_partner', 0)
        std_dev = sql_stats.get('std_dev', 0)

        # Use max project count (graph covers all, SQL may be filtered)
        project_count = max(graph_count, sql_count)

        return {
            'statistics': {
                'projects_analyzed': project_count,
                'total_eu_contribution': {
                    'min': round(min_budget, 0),
                    'max': round(max_budget, 0),
                    'average': round(avg_budget, 0),
                    'median': round(median_budget, 0),
                    'std_dev': round(std_dev, 0)
                },
                'budget_per_partner': {
                    'average': round(avg_per_partner, 0),
                    'median': round(median_budget / max(median_partners, 1), 0)
                },
                'consortium_size': {
                    'min': sql_stats.get('min_partners', 3),
                    'max': sql_stats.get('max_partners', 20),
                    'average': round(avg_partners, 1),
                    'median': round(median_partners, 0)
                }
            },
            'data_source': 'hybrid_graph_sql'
        }

    def _format_sql_stats(self, sql_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Format SQL-only stats into standard response format."""
        return {
            'statistics': {
                'projects_analyzed': sql_stats.get('project_count', 0),
                'total_eu_contribution': {
                    'min': round(sql_stats.get('min_budget', 0), 0),
                    'max': round(sql_stats.get('max_budget', 0), 0),
                    'average': round(sql_stats.get('avg_budget', 0), 0),
                    'median': round(sql_stats.get('median_budget', 0), 0),
                    'std_dev': round(sql_stats.get('std_dev', 0), 0)
                },
                'budget_per_partner': {
                    'average': round(sql_stats.get('avg_per_partner', 0), 0),
                    'median': round(sql_stats.get('median_budget', 0) / max(sql_stats.get('median_partners', 1), 1), 0)
                },
                'consortium_size': {
                    'min': sql_stats.get('min_partners', 3),
                    'max': sql_stats.get('max_partners', 20),
                    'average': round(sql_stats.get('avg_partners', 0), 1),
                    'median': round(sql_stats.get('median_partners', 0), 0)
                }
            },
            'data_source': 'postgresql'
        }

    def _format_graph_stats(self, graph_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Format graph-only stats into standard response format."""
        avg_budget = graph_stats.get('avg_budget', 0)
        median_budget = graph_stats.get('median_budget', 0)

        return {
            'statistics': {
                'projects_analyzed': graph_stats.get('project_count', 0),
                'total_eu_contribution': {
                    'min': round(graph_stats.get('min_budget', 0), 0),
                    'max': round(graph_stats.get('max_budget', 0), 0),
                    'average': round(avg_budget, 0),
                    'median': round(median_budget, 0),
                    'std_dev': 0  # Graph doesn't provide std_dev
                },
                'budget_per_partner': {
                    'average': round(avg_budget / 10, 0),  # Estimate ~10 partners
                    'median': round(median_budget / 10, 0)
                },
                'consortium_size': {
                    'min': 3,
                    'max': 20,
                    'average': 10,
                    'median': 9
                }
            },
            'data_source': 'neo4j_graph'
        }

    def _get_consortium_context(self, cluster: str) -> Optional[Dict[str, Any]]:
        """Get consortium composition patterns from graph."""
        if not self._graph_service:
            return None

        try:
            patterns = self._graph_service.get_consortium_patterns(
                cluster_code=cluster
            )

            if patterns:
                pattern = patterns[0] if len(patterns) == 1 else patterns
                return {
                    'avg_partners': pattern.get('avg_partners', 0),
                    'avg_countries': pattern.get('avg_countries', 0),
                    'sample_size': pattern.get('sample_size', 0),
                    'top_coordinator_countries': pattern.get('top_coordinator_countries', []),
                    'source': 'neo4j_graph'
                }
            return None

        except Exception as e:
            logger.warning(f"Failed to get consortium context: {e}")
            return None

    def _get_budget_by_org_type(
        self,
        cluster: str,
        action_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get budget distribution by organization type.

        Uses SQL query for detailed breakdown by org type (HES, REC, PRC, etc.)
        """
        try:
            conn = self._get_connection()
            if not conn:
                return None

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Map CLUSTER-X to topic patterns
            cluster_topic_map = {
                'CLUSTER-1': 'HLTH',
                'CLUSTER-2': 'CL2',
                'CLUSTER-3': 'CL3',
                'CLUSTER-4': 'CL4',
                'CLUSTER-5': 'CL5',
                'CLUSTER-6': 'CL6',
            }
            topic_pattern = cluster_topic_map.get(cluster, cluster)

            # Build query
            where_conditions = [
                "p.\"frameworkProgramme\" = 'HORIZON'",
                "p.topics ILIKE %s"
            ]
            params = [f"%{topic_pattern}%"]

            if action_type:
                where_conditions.append("p.\"fundingScheme\" ILIKE %s")
                params.append(f"%{action_type.upper()}%")

            where_clause = " AND ".join(where_conditions)

            query = f"""
                SELECT
                    COALESCE(o."activityType", 'OTH') as org_type,
                    COUNT(DISTINCT o."organisationID") as org_count,
                    COUNT(DISTINCT p.id) as project_count,
                    AVG(o."ecContribution") as avg_contribution,
                    SUM(o."ecContribution") as total_contribution,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY o."ecContribution") as median_contribution
                FROM projects p
                JOIN organizations o ON p.id = o."projectID"
                WHERE {where_clause}
                GROUP BY COALESCE(o."activityType", 'OTH')
                ORDER BY total_contribution DESC
            """

            cursor.execute(query, params)
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            if not results:
                return None

            # Format results
            org_type_names = {
                'HES': 'Higher Education',
                'REC': 'Research Organizations',
                'PRC': 'Private Companies',
                'PUB': 'Public Bodies',
                'OTH': 'Other'
            }

            breakdown = []
            total_contribution = sum(r.get('total_contribution', 0) or 0 for r in results)

            for r in results:
                org_type = r.get('org_type', 'OTH')
                org_contribution = r.get('total_contribution', 0) or 0

                breakdown.append({
                    'org_type': org_type,
                    'org_type_name': org_type_names.get(org_type, org_type),
                    'organization_count': int(r.get('org_count', 0)),
                    'project_count': int(r.get('project_count', 0)),
                    'avg_contribution': round(float(r.get('avg_contribution', 0) or 0), 0),
                    'median_contribution': round(float(r.get('median_contribution', 0) or 0), 0),
                    'total_contribution': round(org_contribution, 0),
                    'percentage_of_total': round((org_contribution / total_contribution * 100) if total_contribution > 0 else 0, 1)
                })

            return {
                'cluster': cluster,
                'action_type': action_type,
                'by_org_type': breakdown,
                'total_contribution': round(total_contribution, 0),
                'source': 'postgresql'
            }

        except Exception as e:
            logger.error(f"Failed to get budget by org type: {e}")
            return None

    def _get_budget_by_country(
        self,
        cluster: str,
        action_type: Optional[str] = None,
        limit: int = 15
    ) -> Optional[Dict[str, Any]]:
        """
        Get budget distribution by country.

        Shows top countries by total EU contribution in the cluster.
        """
        try:
            conn = self._get_connection()
            if not conn:
                return None

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Map CLUSTER-X to topic patterns
            cluster_topic_map = {
                'CLUSTER-1': 'HLTH',
                'CLUSTER-2': 'CL2',
                'CLUSTER-3': 'CL3',
                'CLUSTER-4': 'CL4',
                'CLUSTER-5': 'CL5',
                'CLUSTER-6': 'CL6',
            }
            topic_pattern = cluster_topic_map.get(cluster, cluster)

            # Build query
            where_conditions = [
                "p.\"frameworkProgramme\" = 'HORIZON'",
                "p.topics ILIKE %s",
                "o.country IS NOT NULL"
            ]
            params = [f"%{topic_pattern}%"]

            if action_type:
                where_conditions.append("p.\"fundingScheme\" ILIKE %s")
                params.append(f"%{action_type.upper()}%")

            where_clause = " AND ".join(where_conditions)

            query = f"""
                SELECT
                    o.country,
                    COUNT(DISTINCT o."organisationID") as org_count,
                    COUNT(DISTINCT p.id) as project_count,
                    COUNT(DISTINCT CASE WHEN o.role = 'coordinator' THEN p.id END) as coordinations,
                    AVG(o."ecContribution") as avg_contribution,
                    SUM(o."ecContribution") as total_contribution
                FROM projects p
                JOIN organizations o ON p.id = o."projectID"
                WHERE {where_clause}
                GROUP BY o.country
                HAVING SUM(o."ecContribution") > 0
                ORDER BY SUM(o."ecContribution") DESC NULLS LAST
                LIMIT %s
            """
            params.append(limit)

            cursor.execute(query, params)
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            if not results:
                return None

            # Format results
            total_contribution = sum(r.get('total_contribution', 0) or 0 for r in results)

            breakdown = []
            for r in results:
                country_contribution = r.get('total_contribution', 0) or 0
                breakdown.append({
                    'country': r.get('country'),
                    'organization_count': int(r.get('org_count', 0)),
                    'project_count': int(r.get('project_count', 0)),
                    'coordinations': int(r.get('coordinations', 0)),
                    'avg_contribution': round(float(r.get('avg_contribution', 0) or 0), 0),
                    'total_contribution': round(country_contribution, 0),
                    'percentage_of_total': round((country_contribution / total_contribution * 100) if total_contribution > 0 else 0, 1)
                })

            return {
                'cluster': cluster,
                'action_type': action_type,
                'by_country': breakdown,
                'total_contribution': round(total_contribution, 0),
                'countries_shown': len(breakdown),
                'source': 'postgresql'
            }

        except Exception as e:
            logger.error(f"Failed to get budget by country: {e}")
            return None

    def _generate_recommendations(
        self,
        avg_budget: float,
        median_budget: float,
        std_dev: float,
        avg_partners: float,
        median_partners: float,
        avg_per_partner: float,
        action_type: Optional[str],
        project_count: int
    ) -> Dict[str, Any]:
        """Generate budget recommendations based on statistics."""

        # Calculate suggested range (median ± 0.5 std_dev)
        if std_dev > 0:
            lower = max(median_budget - std_dev * 0.5, median_budget * 0.6)
            upper = median_budget + std_dev * 0.5
        else:
            lower = median_budget * 0.7
            upper = median_budget * 1.3

        # Format as human-readable
        def format_millions(amount: float) -> str:
            if amount >= 1_000_000:
                return f"€{amount / 1_000_000:.1f}M"
            elif amount >= 1000:
                return f"€{amount / 1000:.0f}k"
            return f"€{amount:.0f}"

        # Partner range
        if median_partners > 0:
            partner_lower = max(int(median_partners - 2), 3)
            partner_upper = int(median_partners + 3)
        else:
            partner_lower = 3
            partner_upper = 12

        # Per-partner budget
        if avg_per_partner > 0:
            per_partner_lower = avg_per_partner * 0.7
            per_partner_upper = avg_per_partner * 1.3
        else:
            per_partner_lower = avg_budget * 0.7 / max(avg_partners, 1)
            per_partner_upper = avg_budget * 1.3 / max(avg_partners, 1)

        recommendations = {
            "suggested_budget_range": f"{format_millions(lower)} - {format_millions(upper)}",
            "suggested_consortium_size": f"{partner_lower}-{partner_upper} partners",
            "suggested_budget_per_partner": f"{format_millions(per_partner_lower)} - {format_millions(per_partner_upper)}",
            "confidence": "high" if project_count >= 20 else "medium" if project_count >= 5 else "low",
            "notes": []
        }

        # Add contextual notes
        if project_count < 10:
            recommendations["notes"].append(
                f"Based on {project_count} projects - consider broadening search criteria for more reliable statistics"
            )

        if action_type:
            at = action_type.upper()
            if at == "RIA":
                recommendations["notes"].append("RIA projects typically receive 100% funding rate")
            elif at == "IA":
                recommendations["notes"].append("IA projects typically receive 70% funding rate (100% for non-profit)")
            elif at == "CSA":
                recommendations["notes"].append("CSA projects are typically smaller with 100% funding rate")

        return recommendations

    def _get_fallback_benchmarks(
        self,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return fallback benchmarks when databases are unavailable."""

        # Default benchmarks based on action type
        defaults = {
            "RIA": {
                "avg": 5_000_000,
                "median": 4_500_000,
                "min": 2_000_000,
                "max": 12_000_000,
                "partners": 9
            },
            "IA": {
                "avg": 8_000_000,
                "median": 7_000_000,
                "min": 3_000_000,
                "max": 20_000_000,
                "partners": 12
            },
            "CSA": {
                "avg": 2_500_000,
                "median": 2_000_000,
                "min": 500_000,
                "max": 5_000_000,
                "partners": 6
            },
            "ERC-STG": {
                "avg": 1_500_000,
                "median": 1_500_000,
                "min": 1_000_000,
                "max": 1_500_000,
                "partners": 1
            },
            "ERC-COG": {
                "avg": 2_000_000,
                "median": 2_000_000,
                "min": 1_500_000,
                "max": 2_000_000,
                "partners": 1
            },
            "ERC-ADG": {
                "avg": 2_500_000,
                "median": 2_500_000,
                "min": 2_000_000,
                "max": 2_500_000,
                "partners": 1
            }
        }

        at = (action_type or "RIA").upper()
        benchmark = defaults.get(at, defaults["RIA"])

        return {
            "statistics": {
                "projects_analyzed": "N/A (using typical values)",
                "total_eu_contribution": {
                    "min": benchmark["min"],
                    "max": benchmark["max"],
                    "average": benchmark["avg"],
                    "median": benchmark["median"],
                    "std_dev": "N/A"
                },
                "budget_per_partner": {
                    "average": round(benchmark["avg"] / benchmark["partners"], 0),
                    "median": round(benchmark["median"] / benchmark["partners"], 0)
                },
                "consortium_size": {
                    "typical": benchmark["partners"],
                    "range": f"{max(3, benchmark['partners']-3)}-{benchmark['partners']+3}"
                }
            },
            "data_source": "fallback_estimates"
        }

    # Additional methods for enhanced functionality

    def get_budget_trends(
        self,
        cluster: str,
        action_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get budget trends over time for a cluster.

        Uses graph service for pre-aggregated trend data.
        """
        if not self._graph_service:
            return {'success': False, 'error': 'Graph service not available'}

        try:
            trends = self._graph_service.get_funding_trends(
                cluster_code=cluster,
                group_by='year'
            )

            return {
                'success': True,
                'cluster': cluster,
                'action_type': action_type,
                'trends': trends,
                'source': 'neo4j_graph'
            }

        except Exception as e:
            logger.error(f"Failed to get budget trends: {e}")
            return {'success': False, 'error': str(e)}

    def get_benchmark_comparison(
        self,
        clusters: List[str],
        action_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare budget benchmarks across multiple clusters.

        Useful for understanding relative budget expectations.
        """
        comparisons = []

        for cluster in clusters:
            normalized = self._normalize_cluster_code(cluster)
            if normalized:
                result = self.get_benchmark(
                    cluster=normalized,
                    action_type=action_type,
                    include_consortium_context=False,
                    include_org_type_breakdown=False
                )
                if result.get('success'):
                    comparisons.append({
                        'cluster': normalized,
                        'statistics': result.get('statistics', {})
                    })

        return {
            'success': True,
            'action_type': action_type,
            'comparisons': comparisons,
            'clusters_compared': len(comparisons)
        }


# Async wrapper for tool orchestrator compatibility
async def get_budget_benchmark_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute budget benchmark tool.

    This tool provides real budget statistics from funded Horizon Europe projects.
    Use it when users ask about typical budgets, EU contributions, or budget-per-partner
    for specific clusters, action types, or topics.

    HYBRID ARCHITECTURE: Combines Neo4j graph data with PostgreSQL for comprehensive benchmarks.
    """
    # Extract cluster with fallback alternatives (LLM might use different parameter names)
    cluster_param = (
        params.get('cluster') or
        params.get('cluster_code') or
        params.get('cluster_id') or
        params.get('pillar')
    )
    logger.info(f"get_budget_benchmark_execute: params={params}, extracted cluster={cluster_param!r}")

    tool = BudgetBenchmarkTool()

    return tool.get_benchmark(
        cluster=cluster_param,
        action_type=params.get('action_type'),
        topic_keywords=params.get('topic_keywords'),
        year=params.get('year'),
        include_consortium_context=params.get('include_consortium_context', True),
        include_org_type_breakdown=params.get('include_org_type_breakdown', True),
        include_country_breakdown=params.get('include_country_breakdown', False)
    )
