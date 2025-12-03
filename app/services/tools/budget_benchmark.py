"""
Budget Benchmarking Tool for Horizon Europe Projects.

Provides real budget statistics from funded CORDIS projects to help users
set realistic budget expectations for their proposals.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class BudgetBenchmarkTool:
    """Tool to get budget benchmarks from funded Horizon Europe projects."""

    def __init__(self):
        """Initialize with database connection."""
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.warning("DATABASE_URL not set - budget benchmark will be limited")

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def get_benchmark(
        self,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        topic_keywords: Optional[str] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get budget benchmarks from funded Horizon Europe projects.

        Args:
            cluster: Cluster code (e.g., "CL4", "CL5", "EIC")
            action_type: Action type (e.g., "RIA", "IA", "CSA")
            topic_keywords: Keywords to filter projects
            year: Filter by funding year

        Returns:
            Budget statistics and recommendations
        """
        try:
            conn = self._get_connection()
            if not conn:
                return self._get_fallback_benchmarks(cluster, action_type)

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build WHERE conditions
            where_conditions = ["p.\"frameworkProgramme\" = 'HORIZON'"]
            params = []

            # Cluster filter (in topics field)
            if cluster:
                # Map cluster names/codes to topic patterns
                cluster_map = {
                    'CL1': 'HLTH', 'CLUSTER1': 'HLTH', 'CLUSTER-1': 'HLTH', 'HEALTH': 'HLTH',
                    'CL2': 'CL2', 'CLUSTER2': 'CL2', 'CLUSTER-2': 'CL2', 'CULTURE': 'CL2',
                    'CL3': 'CL3', 'CLUSTER3': 'CL3', 'CLUSTER-3': 'CL3', 'SECURITY': 'CL3',
                    'CL4': 'CL4', 'CLUSTER4': 'CL4', 'CLUSTER-4': 'CL4', 'DIGITAL': 'CL4',
                    'CL5': 'CL5', 'CLUSTER5': 'CL5', 'CLUSTER-5': 'CL5', 'CLIMATE': 'CL5', 'ENERGY': 'CL5',
                    'CL6': 'CL6', 'CLUSTER6': 'CL6', 'CLUSTER-6': 'CL6', 'FOOD': 'CL6',
                    'EIC': 'EIC', 'ERC': 'ERC', 'MSCA': 'MSCA',
                }
                cluster_upper = cluster.upper().replace(' ', '').replace('-', '')
                cluster_normalized = cluster_map.get(cluster_upper, cluster.upper())
                where_conditions.append("p.topics ILIKE %s")
                params.append(f"%{cluster_normalized}%")

            # Action type filter (in fundingScheme field)
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
                return self._get_fallback_benchmarks(cluster, action_type)

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

            # Build response
            project_count = int(stats_row['project_count'])
            avg_budget = float(stats_row['avg_budget'] or 0)
            median_budget = float(stats_row['median_budget'] or 0)
            min_budget = float(stats_row['min_budget'] or 0)
            max_budget = float(stats_row['max_budget'] or 0)
            std_dev = float(stats_row['std_dev'] or 0)
            avg_partners = float(stats_row['avg_partners'] or 0)
            median_partners = float(stats_row['median_partners'] or 0)
            avg_per_partner = float(stats_row['avg_per_partner'] or 0)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                avg_budget, median_budget, std_dev,
                avg_partners, median_partners, avg_per_partner,
                action_type, project_count
            )

            return {
                "success": True,
                "tool_name": "get_budget_benchmark",
                "query_params": {
                    "cluster": cluster,
                    "action_type": action_type,
                    "topic_keywords": topic_keywords,
                    "year": year
                },
                "statistics": {
                    "projects_analyzed": project_count,
                    "total_eu_contribution": {
                        "min": round(min_budget, 0),
                        "max": round(max_budget, 0),
                        "average": round(avg_budget, 0),
                        "median": round(median_budget, 0),
                        "std_dev": round(std_dev, 0)
                    },
                    "budget_per_partner": {
                        "average": round(avg_per_partner, 0),
                        "median": round(median_budget / max(median_partners, 1), 0)
                    },
                    "consortium_size": {
                        "min": int(stats_row['min_partners'] or 0),
                        "max": int(stats_row['max_partners'] or 0),
                        "average": round(avg_partners, 1),
                        "median": round(median_partners, 0)
                    }
                },
                "recommendations": recommendations,
                "sample_projects": [
                    {
                        "acronym": p.get('acronym') or 'N/A',
                        "title": (p.get('title') or '')[:80] + ('...' if len(p.get('title') or '') > 80 else ''),
                        "eu_contribution": round(float(p.get('eu_contribution') or 0), 0),
                        "partners": int(p.get('partner_count') or 0),
                        "action_type": p.get('fundingScheme') or p.get('fundingscheme') or 'N/A',
                        "start_year": p.get('startDate').year if p.get('startDate') else None
                    }
                    for p in sample_projects
                ],
                "data_source": "cordis_database",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Budget benchmark error: {e}")
            return self._get_fallback_benchmarks(cluster, action_type)

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
        lower = max(median_budget - std_dev * 0.5, median_budget * 0.6)
        upper = median_budget + std_dev * 0.5

        # Format as human-readable
        def format_millions(amount: float) -> str:
            if amount >= 1_000_000:
                return f"€{amount / 1_000_000:.1f}M"
            elif amount >= 1000:
                return f"€{amount / 1000:.0f}k"
            return f"€{amount:.0f}"

        # Partner range
        partner_lower = max(int(median_partners - 2), 3)
        partner_upper = int(median_partners + 3)

        # Per-partner budget
        per_partner_lower = avg_per_partner * 0.7
        per_partner_upper = avg_per_partner * 1.3

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
        """Return fallback benchmarks when database is unavailable."""

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
            "success": True,
            "tool_name": "get_budget_benchmark",
            "query_params": {
                "cluster": cluster,
                "action_type": action_type
            },
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
            "recommendations": {
                "suggested_budget_range": f"€{benchmark['median']/1_000_000:.1f}M - €{benchmark['max']/1_000_000:.1f}M",
                "suggested_consortium_size": f"{max(3, benchmark['partners']-2)}-{benchmark['partners']+2} partners",
                "suggested_budget_per_partner": f"€{benchmark['avg']/benchmark['partners']/1000:.0f}k - €{benchmark['avg']*1.3/benchmark['partners']/1000:.0f}k",
                "confidence": "low",
                "notes": ["Using typical values - database unavailable for specific statistics"]
            },
            "sample_projects": [],
            "data_source": "fallback_estimates",
            "timestamp": datetime.now().isoformat()
        }


# Async wrapper for tool orchestrator compatibility
async def get_budget_benchmark_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute budget benchmark tool.

    This tool provides real budget statistics from funded Horizon Europe projects.
    Use it when users ask about typical budgets, EU contributions, or budget-per-partner
    for specific clusters, action types, or topics.
    """
    tool = BudgetBenchmarkTool()

    return tool.get_benchmark(
        cluster=params.get('cluster'),
        action_type=params.get('action_type'),
        topic_keywords=params.get('topic_keywords'),
        year=params.get('year')
    )
