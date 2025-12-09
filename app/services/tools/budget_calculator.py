"""
Budget Calculator Tool for Horizon Europe Proposals.

ENHANCED with Hybrid Graph+SQL Architecture:
- Uses Neo4j graph database for cluster-specific budget patterns
- Uses PostgreSQL for detailed project analysis
- Parallel query execution for performance
- Cluster inference from keywords
- Real-data grounded cost ratios and recommendations

Helps users calculate realistic budget breakdowns for their proposals
based on patterns from funded projects and Horizon Europe cost rules.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# Cluster keyword mapping for automatic cluster inference
CLUSTER_KEYWORDS = {
    'CLUSTER-1': [
        'health', 'medical', 'clinical', 'disease', 'patient', 'healthcare',
        'hospital', 'therapy', 'diagnosis', 'pharmaceutical', 'cancer',
        'vaccine', 'drug', 'pandemic', 'infection', 'mental health',
        'aging', 'biomedical', 'genomics', 'personalized medicine'
    ],
    'CLUSTER-2': [
        'culture', 'democracy', 'social', 'heritage', 'creative', 'inclusive',
        'society', 'governance', 'media', 'migration', 'citizenship',
        'inequality', 'education', 'arts', 'humanities'
    ],
    'CLUSTER-3': [
        'security', 'cybersecurity', 'border', 'crime', 'disaster',
        'resilience', 'defence', 'terrorism', 'critical infrastructure',
        'crisis', 'surveillance', 'forensics', 'protection'
    ],
    'CLUSTER-4': [
        'digital', 'AI', 'artificial intelligence', 'data', 'industry',
        'space', 'manufacturing', 'robotics', 'computing', 'machine learning',
        'quantum', 'electronics', 'semiconductor', 'cloud', '5G', '6G',
        'IoT', 'internet of things', 'automation', 'cyber-physical'
    ],
    'CLUSTER-5': [
        'climate', 'energy', 'mobility', 'transport', 'hydrogen', 'battery',
        'renewable', 'green', 'carbon', 'solar', 'wind', 'electric vehicle',
        'decarbonization', 'sustainability', 'smart grid', 'fuel cell',
        'emission', 'clean energy', 'circular economy'
    ],
    'CLUSTER-6': [
        'food', 'agriculture', 'bioeconomy', 'biodiversity', 'ocean', 'marine',
        'environment', 'soil', 'water', 'forestry', 'fisheries', 'farming',
        'ecosystem', 'nature', 'rural', 'bio-based', 'sustainable food'
    ]
}

# Cluster code normalization
CLUSTER_MAP = {
    'CL1': 'CLUSTER-1', 'CLUSTER1': 'CLUSTER-1', 'CLUSTER-1': 'CLUSTER-1', 'HEALTH': 'CLUSTER-1', 'HLTH': 'CLUSTER-1',
    'CL2': 'CLUSTER-2', 'CLUSTER2': 'CLUSTER-2', 'CLUSTER-2': 'CLUSTER-2', 'CULTURE': 'CLUSTER-2',
    'CL3': 'CLUSTER-3', 'CLUSTER3': 'CLUSTER-3', 'CLUSTER-3': 'CLUSTER-3', 'SECURITY': 'CLUSTER-3',
    'CL4': 'CLUSTER-4', 'CLUSTER4': 'CLUSTER-4', 'CLUSTER-4': 'CLUSTER-4', 'DIGITAL': 'CLUSTER-4',
    'CL5': 'CLUSTER-5', 'CLUSTER5': 'CLUSTER-5', 'CLUSTER-5': 'CLUSTER-5', 'CLIMATE': 'CLUSTER-5', 'ENERGY': 'CLUSTER-5',
    'CL6': 'CLUSTER-6', 'CLUSTER6': 'CLUSTER-6', 'CLUSTER-6': 'CLUSTER-6', 'FOOD': 'CLUSTER-6',
}


class BudgetCalculatorTool:
    """
    Calculate realistic budget breakdowns for Horizon Europe proposals.

    ENHANCED with Hybrid Graph+SQL Architecture:
    - Graph service (Neo4j) for cluster-specific statistics and patterns
    - SQL service (PostgreSQL) for detailed project analysis
    - Parallel query execution for performance
    - Cluster inference from keywords
    """

    # Typical cost category ratios by action type (baseline, adjusted by real data)
    COST_RATIOS = {
        'RIA': {
            'personnel': 0.55,
            'equipment': 0.10,
            'travel': 0.05,
            'subcontracting': 0.10,
            'other_direct': 0.05,
            'indirect': 0.15,
        },
        'IA': {
            'personnel': 0.45,
            'equipment': 0.15,
            'travel': 0.05,
            'subcontracting': 0.15,
            'other_direct': 0.05,
            'indirect': 0.15,
        },
        'CSA': {
            'personnel': 0.65,
            'equipment': 0.02,
            'travel': 0.10,
            'subcontracting': 0.08,
            'other_direct': 0.05,
            'indirect': 0.10,
        },
        'ERC-STG': {
            'personnel': 0.70,
            'equipment': 0.10,
            'travel': 0.05,
            'subcontracting': 0.00,
            'other_direct': 0.05,
            'indirect': 0.10,
        },
        'ERC-COG': {
            'personnel': 0.70,
            'equipment': 0.10,
            'travel': 0.05,
            'subcontracting': 0.00,
            'other_direct': 0.05,
            'indirect': 0.10,
        },
        'ERC-ADG': {
            'personnel': 0.70,
            'equipment': 0.10,
            'travel': 0.05,
            'subcontracting': 0.00,
            'other_direct': 0.05,
            'indirect': 0.10,
        },
    }

    # Person-month costs by country tier (EUR)
    PM_COSTS = {
        'tier1': 8500,
        'tier2': 6500,
        'tier3': 4500,
        'default': 7000,
    }

    COUNTRY_TIERS = {
        'tier1': ['DE', 'FR', 'NL', 'BE', 'AT', 'DK', 'SE', 'FI', 'LU', 'NO', 'CH'],
        'tier2': ['ES', 'IT', 'PT', 'IE', 'CZ', 'SI', 'EE', 'GR', 'CY', 'MT'],
        'tier3': ['PL', 'HU', 'RO', 'BG', 'HR', 'SK', 'LT', 'LV'],
    }

    # Funding rates
    FUNDING_RATES = {
        'RIA': 1.0,
        'IA': 0.7,
        'CSA': 1.0,
        'ERC-STG': 1.0,
        'ERC-COG': 1.0,
        'ERC-ADG': 1.0,
        'EIC': 0.7,
    }

    def __init__(self):
        """Initialize with database connection and graph service."""
        self.db_url = os.getenv("DATABASE_URL")

        # Initialize graph service with graceful fallback
        self._graph_service = None
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            self._graph_service = GraphSearchService()
            logger.info("✅ Graph service available for budget calculator")
        except Exception as e:
            logger.warning(f"⚠️ Graph service not available for budget calculator: {e}")

        # Cache for cluster-specific statistics
        self._cluster_stats_cache = {}

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _normalize_cluster_code(self, cluster: Optional[str]) -> Optional[str]:
        """Normalize cluster code to CLUSTER-N format."""
        if not cluster:
            return None
        cluster_upper = cluster.upper().replace(' ', '').replace('-', '')
        # Handle cases like CL5 -> CLUSTER-5
        if cluster_upper.startswith('CL') and len(cluster_upper) == 3:
            cluster_upper = f"CLUSTER{cluster_upper[2]}"
        return CLUSTER_MAP.get(cluster_upper, cluster.upper() if cluster.upper().startswith('CLUSTER-') else None)

    def _infer_clusters_from_keywords(self, keywords: str) -> List[str]:
        """Infer clusters from research topic keywords."""
        if not keywords:
            return []

        keywords_lower = keywords.lower()
        inferred = []

        for cluster, kw_list in CLUSTER_KEYWORDS.items():
            for kw in kw_list:
                if kw.lower() in keywords_lower:
                    if cluster not in inferred:
                        inferred.append(cluster)
                    break

        return inferred

    def calculate_budget(
        self,
        action_type: str,
        duration_months: int,
        num_partners: int,
        total_person_months: Optional[int] = None,
        target_budget: Optional[float] = None,
        countries: Optional[List[str]] = None,
        cluster: Optional[str] = None,
        topic_keywords: Optional[str] = None,
        include_breakdown: bool = True,
        include_cluster_context: bool = True,
        include_similar_projects: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate recommended budget breakdown for a Horizon Europe proposal.

        ENHANCED with Hybrid Graph+SQL Architecture:
        - Uses graph database for cluster-specific budget patterns
        - Uses SQL for detailed project benchmarking
        - Cluster inference from keywords
        - Real-data grounded recommendations

        Args:
            action_type: RIA, IA, CSA, ERC-STG, ERC-COG, ERC-ADG, etc.
            duration_months: Project duration in months
            num_partners: Number of consortium partners
            total_person_months: Total PMs across all partners (optional)
            target_budget: Target total budget in EUR (optional)
            countries: List of partner country codes (optional)
            cluster: Cluster code for context (e.g., "CL5", "CLUSTER-5")
            topic_keywords: Keywords for cluster inference (alternative to cluster)
            include_breakdown: Include detailed cost category breakdown
            include_cluster_context: Include cluster-specific budget context from graph
            include_similar_projects: Include similar project examples

        Returns:
            Budget breakdown with graph-enhanced recommendations
        """
        action_type = action_type.upper()
        ratios = self.COST_RATIOS.get(action_type, self.COST_RATIOS['RIA'])
        funding_rate = self.FUNDING_RATES.get(action_type, 1.0)

        # Normalize cluster or infer from keywords
        normalized_cluster = self._normalize_cluster_code(cluster)
        inferred_clusters = []
        if not normalized_cluster and topic_keywords:
            inferred_clusters = self._infer_clusters_from_keywords(topic_keywords)
            if inferred_clusters:
                normalized_cluster = inferred_clusters[0]
                logger.info(f"Inferred cluster from keywords: {normalized_cluster}")

        # Use hybrid approach for enhanced budget calculation
        if self._graph_service and (normalized_cluster or action_type):
            return self._calculate_budget_hybrid(
                action_type=action_type,
                duration_months=duration_months,
                num_partners=num_partners,
                total_person_months=total_person_months,
                target_budget=target_budget,
                countries=countries,
                cluster=normalized_cluster,
                inferred_clusters=inferred_clusters,
                ratios=ratios,
                funding_rate=funding_rate,
                include_breakdown=include_breakdown,
                include_cluster_context=include_cluster_context,
                include_similar_projects=include_similar_projects
            )

        # Fallback to SQL-only calculation
        return self._calculate_budget_sql(
            action_type=action_type,
            duration_months=duration_months,
            num_partners=num_partners,
            total_person_months=total_person_months,
            target_budget=target_budget,
            countries=countries,
            ratios=ratios,
            funding_rate=funding_rate,
            include_breakdown=include_breakdown
        )

    def _calculate_budget_hybrid(
        self,
        action_type: str,
        duration_months: int,
        num_partners: int,
        total_person_months: Optional[int],
        target_budget: Optional[float],
        countries: Optional[List[str]],
        cluster: Optional[str],
        inferred_clusters: List[str],
        ratios: Dict[str, float],
        funding_rate: float,
        include_breakdown: bool,
        include_cluster_context: bool,
        include_similar_projects: bool
    ) -> Dict[str, Any]:
        """
        Hybrid Graph+SQL budget calculation with parallel queries.
        """
        results = {
            'graph': {},
            'sql': {}
        }

        # Execute graph and SQL queries in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}

            # Graph queries
            if self._graph_service:
                if cluster:
                    futures['graph_budget_stats'] = executor.submit(
                        self._get_graph_budget_statistics,
                        cluster, action_type
                    )

                    if include_cluster_context:
                        futures['graph_consortium'] = executor.submit(
                            self._get_graph_consortium_patterns,
                            cluster
                        )

                if include_similar_projects and cluster:
                    futures['graph_examples'] = executor.submit(
                        self._get_graph_project_examples,
                        cluster, action_type
                    )

            # SQL queries
            futures['sql_benchmarks'] = executor.submit(
                self._get_budget_benchmarks_sql,
                action_type
            )

            if include_similar_projects:
                futures['sql_similar'] = executor.submit(
                    self._get_similar_projects_sql,
                    action_type, cluster
                )

            # Collect results
            for key, future in futures.items():
                try:
                    if key.startswith('graph_'):
                        results['graph'][key.replace('graph_', '')] = future.result()
                    else:
                        results['sql'][key.replace('sql_', '')] = future.result()
                except Exception as e:
                    logger.warning(f"Query {key} failed: {e}")
                    if key.startswith('graph_'):
                        results['graph'][key.replace('graph_', '')] = None
                    else:
                        results['sql'][key.replace('sql_', '')] = None

        # Merge results and calculate budget
        return self._merge_and_calculate(
            results=results,
            action_type=action_type,
            duration_months=duration_months,
            num_partners=num_partners,
            total_person_months=total_person_months,
            target_budget=target_budget,
            countries=countries,
            cluster=cluster,
            inferred_clusters=inferred_clusters,
            ratios=ratios,
            funding_rate=funding_rate,
            include_breakdown=include_breakdown,
            include_cluster_context=include_cluster_context,
            include_similar_projects=include_similar_projects
        )

    def _get_graph_budget_statistics(
        self,
        cluster: str,
        action_type: Optional[str]
    ) -> Optional[Dict]:
        """Get budget statistics from graph database."""
        if not self._graph_service:
            return None

        try:
            stats = self._graph_service.get_budget_statistics(
                cluster_code=cluster,
                action_type=action_type
            )
            if stats and len(stats) > 0:
                return stats[0] if isinstance(stats, list) else stats
            return None
        except Exception as e:
            logger.warning(f"Graph budget statistics query failed: {e}")
            return None

    def _get_graph_consortium_patterns(self, cluster: str) -> Optional[Dict]:
        """Get consortium patterns from graph database."""
        if not self._graph_service:
            return None

        try:
            patterns = self._graph_service.get_consortium_patterns(
                cluster_code=cluster,
                min_partners=3
            )
            if patterns and len(patterns) > 0:
                return patterns[0] if isinstance(patterns, list) else patterns
            return None
        except Exception as e:
            logger.warning(f"Graph consortium patterns query failed: {e}")
            return None

    def _get_graph_project_examples(
        self,
        cluster: str,
        action_type: Optional[str]
    ) -> Optional[List[Dict]]:
        """Get project examples from graph database."""
        if not self._graph_service:
            return None

        try:
            examples = self._graph_service.get_project_examples(
                cluster_code=cluster,
                funding_scheme=action_type,
                min_budget=500000,
                limit=5
            )
            return examples
        except Exception as e:
            logger.warning(f"Graph project examples query failed: {e}")
            return None

    def _get_budget_benchmarks_sql(self, action_type: str) -> Dict[str, float]:
        """Get budget benchmarks from SQL database."""
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                scheme_pattern = f"%{action_type.replace('-', '%')}%"

                cursor.execute("""
                    SELECT
                        PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY "ecMaxContribution") as p10_budget,
                        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY "ecMaxContribution") as p25_budget,
                        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY "ecMaxContribution") as median_budget,
                        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY "ecMaxContribution") as p75_budget,
                        PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY "ecMaxContribution") as p90_budget,
                        AVG("ecMaxContribution") as avg_budget,
                        COUNT(*) as project_count
                    FROM projects
                    WHERE "frameworkProgramme" = 'HORIZON'
                      AND "fundingScheme" ILIKE %s
                      AND "ecMaxContribution" > 100000
                """, [scheme_pattern])

                row = cursor.fetchone()
                cursor.close()
                conn.close()

                if row and row['median_budget'] and row['project_count'] > 10:
                    return {
                        'min': float(row['p10_budget']),
                        'max': float(row['p90_budget']),
                        'mean': float(row['avg_budget']),
                        'median': float(row['median_budget']),
                        'p25': float(row['p25_budget']),
                        'p75': float(row['p75_budget']),
                        'sample_size': int(row['project_count']),
                        'source': 'sql'
                    }
        except Exception as e:
            logger.warning(f"SQL benchmarks query failed: {e}")

        # Fallback benchmarks
        return self._get_fallback_benchmarks(action_type)

    def _get_similar_projects_sql(
        self,
        action_type: str,
        cluster: Optional[str]
    ) -> Optional[List[Dict]]:
        """Get similar projects from SQL database."""
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                scheme_pattern = f"%{action_type.replace('-', '%')}%"
                params = [scheme_pattern]

                cluster_filter = ""
                if cluster:
                    # Convert CLUSTER-N to CLN for topic matching
                    cl_code = cluster.replace('CLUSTER-', 'CL')
                    cluster_filter = "AND topics ILIKE %s"
                    params.append(f"%{cl_code}%")

                cursor.execute(f"""
                    SELECT
                        acronym,
                        title,
                        "ecMaxContribution" as budget,
                        "fundingScheme" as action_type,
                        topics,
                        "startDate" as start_date
                    FROM projects
                    WHERE "frameworkProgramme" = 'HORIZON'
                      AND "fundingScheme" ILIKE %s
                      AND "ecMaxContribution" > 100000
                      {cluster_filter}
                    ORDER BY "startDate" DESC NULLS LAST
                    LIMIT 5
                """, params)

                rows = cursor.fetchall()
                cursor.close()
                conn.close()

                return [
                    {
                        'acronym': r['acronym'],
                        'title': r['title'][:80] + '...' if len(r['title']) > 80 else r['title'],
                        'budget': float(r['budget']) if r['budget'] else 0,
                        'action_type': r['action_type'],
                        'topic': r['topics'].split(';')[0] if r['topics'] else 'N/A'
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.warning(f"SQL similar projects query failed: {e}")

        return None

    def _get_fallback_benchmarks(self, action_type: str) -> Dict[str, float]:
        """Get fallback benchmarks when database is unavailable."""
        fallback = {
            'RIA': {'min': 2_000_000, 'max': 12_000_000, 'mean': 5_500_000, 'median': 5_000_000},
            'IA': {'min': 3_000_000, 'max': 20_000_000, 'mean': 9_000_000, 'median': 8_000_000},
            'CSA': {'min': 500_000, 'max': 5_000_000, 'mean': 2_000_000, 'median': 1_800_000},
            'ERC-STG': {'min': 1_000_000, 'max': 1_500_000, 'mean': 1_450_000, 'median': 1_500_000},
            'ERC-COG': {'min': 1_500_000, 'max': 2_000_000, 'mean': 1_900_000, 'median': 2_000_000},
            'ERC-ADG': {'min': 2_000_000, 'max': 2_500_000, 'mean': 2_400_000, 'median': 2_500_000},
        }
        benchmarks = fallback.get(action_type.upper(), fallback['RIA'])
        benchmarks['source'] = 'fallback'
        return benchmarks

    def _merge_and_calculate(
        self,
        results: Dict[str, Any],
        action_type: str,
        duration_months: int,
        num_partners: int,
        total_person_months: Optional[int],
        target_budget: Optional[float],
        countries: Optional[List[str]],
        cluster: Optional[str],
        inferred_clusters: List[str],
        ratios: Dict[str, float],
        funding_rate: float,
        include_breakdown: bool,
        include_cluster_context: bool,
        include_similar_projects: bool
    ) -> Dict[str, Any]:
        """Merge graph and SQL results and calculate budget."""

        # Get benchmarks - prefer graph if available, else use SQL
        graph_stats = results['graph'].get('budget_stats')
        sql_benchmarks = results['sql'].get('benchmarks', {})

        # Merge benchmarks (graph takes precedence for cluster-specific data)
        if graph_stats:
            benchmarks = {
                'min': graph_stats.get('min_budget', sql_benchmarks.get('min', 2_000_000)),
                'max': graph_stats.get('max_budget', sql_benchmarks.get('max', 12_000_000)),
                'mean': graph_stats.get('avg_budget', sql_benchmarks.get('mean', 5_500_000)),
                'median': graph_stats.get('median_budget', sql_benchmarks.get('median', 5_000_000)),
                'sample_size': graph_stats.get('project_count', sql_benchmarks.get('sample_size', 0)),
                'source': 'graph'
            }
        else:
            benchmarks = sql_benchmarks

        # Calculate average PM cost based on country mix
        avg_pm_cost = self._calculate_avg_pm_cost(countries)

        # Calculate or estimate total budget
        if target_budget:
            total = target_budget
            estimated_pms = int(total * ratios['personnel'] / avg_pm_cost)
        elif total_person_months:
            personnel_cost = total_person_months * avg_pm_cost
            total = personnel_cost / ratios['personnel']
            estimated_pms = total_person_months
        else:
            # Use benchmarks to estimate
            total = benchmarks.get('median', 5_000_000)
            estimated_pms = int(total * ratios['personnel'] / avg_pm_cost)

        # Adjust ratios based on graph data if available
        adjusted_ratios = self._adjust_ratios_from_graph(ratios, graph_stats, cluster)

        # Calculate breakdown
        breakdown = {}
        if include_breakdown:
            breakdown = self._calculate_breakdown(total, adjusted_ratios, estimated_pms)

        # Calculate per-partner distribution
        per_partner = self._calculate_per_partner(total, num_partners, estimated_pms)

        # Calculate EU contribution
        eu_contribution = total * funding_rate

        # Generate recommendations (enhanced with graph data)
        recommendations = self._generate_recommendations_hybrid(
            action_type=action_type,
            total=total,
            num_partners=num_partners,
            duration=duration_months,
            total_pms=estimated_pms,
            benchmarks=benchmarks,
            graph_consortium=results['graph'].get('consortium'),
            cluster=cluster
        )

        # Build response
        response = {
            "success": True,
            "tool_name": "calculate_budget",
            "input_parameters": {
                "action_type": action_type,
                "duration_months": duration_months,
                "num_partners": num_partners,
                "total_person_months": total_person_months,
                "target_budget": target_budget,
                "countries": countries,
                "cluster": cluster
            },
            "calculated_budget": {
                "total_cost": round(total, 0),
                "eu_contribution": round(eu_contribution, 0),
                "funding_rate": f"{funding_rate * 100:.0f}%",
            },
            "breakdown": breakdown,
            "per_partner": per_partner,
            "effort_summary": {
                "total_person_months": estimated_pms,
                "person_months_per_partner": round(estimated_pms / num_partners, 0),
                "avg_pm_cost_used": round(avg_pm_cost, 0),
                "pm_per_month": round(estimated_pms / duration_months, 1)
            },
            "benchmarks": {
                "typical_range": f"€{benchmarks['min']/1_000_000:.1f}M - €{benchmarks['max']/1_000_000:.1f}M",
                "median": f"€{benchmarks.get('median', benchmarks['mean'])/1_000_000:.1f}M",
                "your_budget_vs_median": self._compare_to_median(total, benchmarks),
                "sample_size": benchmarks.get('sample_size', 'N/A')
            },
            "recommendations": recommendations,
            "metadata": {
                "search_type": "hybrid",
                "sources_used": [],
                "cluster_used": cluster,
                "inferred_clusters": inferred_clusters,
                "benchmarks_source": benchmarks.get('source', 'unknown')
            },
            "timestamp": datetime.now().isoformat()
        }

        # Track sources used
        if graph_stats or results['graph'].get('consortium') or results['graph'].get('examples'):
            response["metadata"]["sources_used"].append("graph")
        if sql_benchmarks or results['sql'].get('similar'):
            response["metadata"]["sources_used"].append("sql")

        # Add cluster context from graph
        if include_cluster_context and results['graph'].get('consortium'):
            consortium = results['graph']['consortium']
            response["cluster_context"] = {
                "cluster_code": consortium.get('cluster_code'),
                "cluster_name": consortium.get('cluster_name'),
                "avg_partners": consortium.get('avg_partners'),
                "avg_countries": consortium.get('avg_countries'),
                "sample_size": consortium.get('sample_size'),
                "top_coordinator_countries": consortium.get('top_coordinator_countries', [])[:5]
            }

        # Add similar projects
        if include_similar_projects:
            graph_examples = results['graph'].get('examples', [])
            sql_similar = results['sql'].get('similar', [])

            # Combine and deduplicate
            all_examples = []
            seen_acronyms = set()

            for ex in (graph_examples or []):
                if ex.get('acronym') and ex['acronym'] not in seen_acronyms:
                    all_examples.append({
                        'acronym': ex.get('acronym'),
                        'title': ex.get('title', '')[:80],
                        'budget': ex.get('budget', 0),
                        'partners': ex.get('partner_count'),
                        'source': 'graph'
                    })
                    seen_acronyms.add(ex['acronym'])

            for ex in (sql_similar or []):
                if ex.get('acronym') and ex['acronym'] not in seen_acronyms:
                    all_examples.append({
                        'acronym': ex.get('acronym'),
                        'title': ex.get('title', ''),
                        'budget': ex.get('budget', 0),
                        'source': 'sql'
                    })
                    seen_acronyms.add(ex['acronym'])

            if all_examples:
                response["similar_projects"] = all_examples[:5]

        return response

    def _adjust_ratios_from_graph(
        self,
        base_ratios: Dict[str, float],
        graph_stats: Optional[Dict],
        cluster: Optional[str]
    ) -> Dict[str, float]:
        """
        Adjust cost ratios based on graph statistics.

        This provides cluster-specific adjustments when data is available.
        """
        if not graph_stats or not cluster:
            return base_ratios

        # Currently we don't have detailed cost breakdown in the graph,
        # but we can adjust based on consortium patterns and budget scale
        adjusted = base_ratios.copy()

        # If graph shows larger average budgets for this cluster, adjust equipment ratio
        avg_budget = graph_stats.get('avg_budget', 0)
        if avg_budget > 10_000_000:
            # Large projects tend to have higher equipment costs
            adjusted['equipment'] = min(0.15, base_ratios['equipment'] + 0.03)
            adjusted['personnel'] = base_ratios['personnel'] - 0.03

        return adjusted

    def _calculate_breakdown(
        self,
        total: float,
        ratios: Dict[str, float],
        estimated_pms: int
    ) -> Dict[str, Dict]:
        """Calculate detailed cost category breakdown."""
        return {
            'personnel': {
                'amount': round(total * ratios['personnel'], 0),
                'percentage': round(ratios['personnel'] * 100, 1),
                'description': 'Salaries, social charges for project staff',
                'person_months': estimated_pms
            },
            'equipment': {
                'amount': round(total * ratios['equipment'], 0),
                'percentage': round(ratios['equipment'] * 100, 1),
                'description': 'Depreciation of equipment purchased for project'
            },
            'travel': {
                'amount': round(total * ratios['travel'], 0),
                'percentage': round(ratios['travel'] * 100, 1),
                'description': 'Travel and subsistence for project meetings'
            },
            'subcontracting': {
                'amount': round(total * ratios['subcontracting'], 0),
                'percentage': round(ratios['subcontracting'] * 100, 1),
                'description': 'Work carried out by third parties'
            },
            'other_direct': {
                'amount': round(total * ratios['other_direct'], 0),
                'percentage': round(ratios['other_direct'] * 100, 1),
                'description': 'Consumables, publications, dissemination'
            },
            'indirect': {
                'amount': round(total * ratios['indirect'], 0),
                'percentage': round(ratios['indirect'] * 100, 1),
                'description': 'Indirect costs (25% flat rate of direct costs excl. subcontracting)'
            },
        }

    def _calculate_per_partner(
        self,
        total: float,
        num_partners: int,
        estimated_pms: int
    ) -> Dict[str, float]:
        """Calculate per-partner budget distribution."""
        coordinator_share = 0.20
        return {
            'average': round(total / num_partners, 0),
            'coordinator_typical': round(total * coordinator_share, 0),
            'partner_typical': round((total * (1 - coordinator_share)) / max(num_partners - 1, 1), 0),
            'pms_per_partner': round(estimated_pms / num_partners, 0)
        }

    def _calculate_avg_pm_cost(self, countries: Optional[List[str]]) -> float:
        """Calculate average person-month cost based on country mix."""
        if not countries:
            return self.PM_COSTS['default']

        total_cost = 0
        for country in countries:
            country_upper = country.upper()
            if country_upper in self.COUNTRY_TIERS['tier1']:
                total_cost += self.PM_COSTS['tier1']
            elif country_upper in self.COUNTRY_TIERS['tier2']:
                total_cost += self.PM_COSTS['tier2']
            elif country_upper in self.COUNTRY_TIERS['tier3']:
                total_cost += self.PM_COSTS['tier3']
            else:
                total_cost += self.PM_COSTS['default']

        return total_cost / len(countries)

    def _compare_to_median(self, total: float, benchmarks: Dict) -> str:
        """Compare calculated budget to median."""
        median = benchmarks.get('median', benchmarks.get('mean', 5_000_000))
        min_val = benchmarks.get('min', median * 0.4)
        max_val = benchmarks.get('max', median * 2.4)

        if total < min_val:
            return "below typical"
        elif total > max_val:
            return "above typical"
        else:
            return "within range"

    def _generate_recommendations_hybrid(
        self,
        action_type: str,
        total: float,
        num_partners: int,
        duration: int,
        total_pms: int,
        benchmarks: Dict,
        graph_consortium: Optional[Dict],
        cluster: Optional[str]
    ) -> List[str]:
        """Generate budget recommendations enhanced with graph data."""
        recommendations = []

        # Budget range check
        min_val = benchmarks.get('min', 2_000_000)
        max_val = benchmarks.get('max', 12_000_000)

        if total < min_val:
            recommendations.append(
                f"Budget (€{total/1_000_000:.1f}M) is below typical for {action_type}. "
                f"Consider increasing to at least €{min_val/1_000_000:.1f}M"
            )
        elif total > max_val:
            recommendations.append(
                f"Budget (€{total/1_000_000:.1f}M) is above typical for {action_type}. "
                f"Ensure strong justification for €{max_val/1_000_000:.1f}M+ budget"
            )
        else:
            recommendations.append(
                f"Budget is within typical range for {action_type} projects"
            )

        # Graph-enhanced consortium recommendations
        if graph_consortium:
            avg_partners = graph_consortium.get('avg_partners', 0)
            avg_countries = graph_consortium.get('avg_countries', 0)

            if avg_partners and num_partners < avg_partners * 0.7:
                recommendations.append(
                    f"Consortium has fewer partners ({num_partners}) than typical for this cluster "
                    f"(avg: {avg_partners:.0f}). Consider if more expertise is needed"
                )
            elif avg_partners and num_partners > avg_partners * 1.5:
                recommendations.append(
                    f"Consortium has more partners ({num_partners}) than typical for this cluster "
                    f"(avg: {avg_partners:.0f}). Ensure each partner has clear role"
                )

        # Per-partner budget check
        per_partner = total / num_partners
        if per_partner < 200_000:
            recommendations.append(
                f"Average per-partner budget (€{per_partner/1000:.0f}k) may be too low. "
                f"Consider reducing partners or increasing total budget"
            )

        # Duration check
        if duration > 48:
            recommendations.append(
                "Projects over 48 months are uncommon and need strong justification"
            )
        elif duration < 24 and action_type in ['RIA', 'IA']:
            recommendations.append(
                f"{action_type} projects typically run 36-48 months. Consider if {duration} months is sufficient"
            )

        # Effort intensity check
        pm_per_partner_per_month = total_pms / num_partners / duration
        if pm_per_partner_per_month < 0.5:
            recommendations.append(
                f"Low effort intensity ({pm_per_partner_per_month:.1f} PM/partner/month). "
                f"Ensure adequate commitment from each partner"
            )
        elif pm_per_partner_per_month > 3:
            recommendations.append(
                f"High effort intensity ({pm_per_partner_per_month:.1f} PM/partner/month). "
                f"Verify capacity of partners"
            )

        # Action-type specific advice
        if action_type == 'IA':
            recommendations.append(
                "Note: IA funding rate is 70% for for-profit entities (100% for non-profit)"
            )
        elif action_type.startswith('ERC'):
            recommendations.append(
                "ERC grants support single PI - ensure budget aligns with host institution guidelines"
            )
        elif action_type == 'CSA':
            recommendations.append(
                "CSA projects typically have lower equipment costs - focus budget on personnel and events"
            )

        # Cluster-specific advice
        if cluster:
            cluster_tips = {
                'CLUSTER-1': "Health cluster: Consider clinical validation costs and regulatory requirements",
                'CLUSTER-4': "Digital cluster: Budget for computing infrastructure and data management",
                'CLUSTER-5': "Climate cluster: Include pilot/demonstration costs for technology validation",
                'CLUSTER-6': "Food/Bio cluster: Consider field trials and biodiversity impact assessments",
            }
            if cluster in cluster_tips:
                recommendations.append(cluster_tips[cluster])

        return recommendations[:6]

    def _calculate_budget_sql(
        self,
        action_type: str,
        duration_months: int,
        num_partners: int,
        total_person_months: Optional[int],
        target_budget: Optional[float],
        countries: Optional[List[str]],
        ratios: Dict[str, float],
        funding_rate: float,
        include_breakdown: bool
    ) -> Dict[str, Any]:
        """SQL-only budget calculation (fallback)."""
        # Calculate average PM cost based on country mix
        avg_pm_cost = self._calculate_avg_pm_cost(countries)

        # Get benchmarks
        benchmarks = self._get_budget_benchmarks_sql(action_type)

        # Calculate or estimate total budget
        if target_budget:
            total = target_budget
            estimated_pms = int(total * ratios['personnel'] / avg_pm_cost)
        elif total_person_months:
            personnel_cost = total_person_months * avg_pm_cost
            total = personnel_cost / ratios['personnel']
            estimated_pms = total_person_months
        else:
            total = benchmarks.get('median', 5_000_000)
            estimated_pms = int(total * ratios['personnel'] / avg_pm_cost)

        # Calculate breakdown
        breakdown = {}
        if include_breakdown:
            breakdown = self._calculate_breakdown(total, ratios, estimated_pms)

        # Calculate per-partner distribution
        per_partner = self._calculate_per_partner(total, num_partners, estimated_pms)

        # Calculate EU contribution
        eu_contribution = total * funding_rate

        # Generate recommendations
        recommendations = self._generate_recommendations_hybrid(
            action_type=action_type,
            total=total,
            num_partners=num_partners,
            duration=duration_months,
            total_pms=estimated_pms,
            benchmarks=benchmarks,
            graph_consortium=None,
            cluster=None
        )

        return {
            "success": True,
            "tool_name": "calculate_budget",
            "input_parameters": {
                "action_type": action_type,
                "duration_months": duration_months,
                "num_partners": num_partners,
                "total_person_months": total_person_months,
                "target_budget": target_budget,
                "countries": countries
            },
            "calculated_budget": {
                "total_cost": round(total, 0),
                "eu_contribution": round(eu_contribution, 0),
                "funding_rate": f"{funding_rate * 100:.0f}%",
            },
            "breakdown": breakdown,
            "per_partner": per_partner,
            "effort_summary": {
                "total_person_months": estimated_pms,
                "person_months_per_partner": round(estimated_pms / num_partners, 0),
                "avg_pm_cost_used": round(avg_pm_cost, 0),
                "pm_per_month": round(estimated_pms / duration_months, 1)
            },
            "benchmarks": {
                "typical_range": f"€{benchmarks['min']/1_000_000:.1f}M - €{benchmarks['max']/1_000_000:.1f}M",
                "median": f"€{benchmarks.get('median', benchmarks['mean'])/1_000_000:.1f}M",
                "your_budget_vs_median": self._compare_to_median(total, benchmarks)
            },
            "recommendations": recommendations,
            "metadata": {
                "search_type": "sql_only",
                "sources_used": ["sql"]
            },
            "timestamp": datetime.now().isoformat()
        }


# Async wrapper for tool orchestrator compatibility
async def calculate_budget_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute budget calculator tool.

    This tool calculates budget breakdowns for Horizon Europe proposals.
    Use it when users want to plan their budget, understand cost categories,
    or validate their budget against typical values.

    ENHANCED with Hybrid Graph+SQL Architecture for:
    - Cluster-specific budget patterns from graph
    - Real-data grounded cost ratios
    - Consortium context for budget validation
    - Similar project examples
    """
    tool = BudgetCalculatorTool()

    return tool.calculate_budget(
        action_type=params.get('action_type', 'RIA'),
        duration_months=params.get('duration_months', 36),
        num_partners=params.get('num_partners', 8),
        total_person_months=params.get('total_person_months'),
        target_budget=params.get('target_budget'),
        countries=params.get('countries'),
        cluster=params.get('cluster'),
        topic_keywords=params.get('topic_keywords'),
        include_breakdown=params.get('include_breakdown', True),
        include_cluster_context=params.get('include_cluster_context', True),
        include_similar_projects=params.get('include_similar_projects', True)
    )
