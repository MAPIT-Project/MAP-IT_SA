"""
Call History Analysis Tool for Horizon Europe.

Analyzes historical funding patterns for specific topic areas, showing what got
funded, when, and under which calls. Helps users understand funding landscape
and identify trends.
"""

import os
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Cluster code mapping
CLUSTER_MAP = {
    'CL1': 'CL1', 'CLUSTER1': 'CL1', 'CLUSTER-1': 'CL1', 'HEALTH': 'CL1', 'HLTH': 'CL1',
    'CL2': 'CL2', 'CLUSTER2': 'CL2', 'CLUSTER-2': 'CL2', 'CULTURE': 'CL2',
    'CL3': 'CL3', 'CLUSTER3': 'CL3', 'CLUSTER-3': 'CL3', 'SECURITY': 'CL3',
    'CL4': 'CL4', 'CLUSTER4': 'CL4', 'CLUSTER-4': 'CL4', 'DIGITAL': 'CL4',
    'CL5': 'CL5', 'CLUSTER5': 'CL5', 'CLUSTER-5': 'CL5', 'CLIMATE': 'CL5', 'ENERGY': 'CL5',
    'CL6': 'CL6', 'CLUSTER6': 'CL6', 'CLUSTER-6': 'CL6', 'FOOD': 'CL6',
    'EIC': 'EIC', 'ERC': 'ERC', 'MSCA': 'MSCA',
}


class CallHistoryTool:
    """Tool to analyze historical funding patterns for Horizon Europe."""

    def __init__(self):
        """Initialize with database connection."""
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.warning("DATABASE_URL not set - call history analysis will be limited")

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _normalize_cluster(self, cluster: str) -> str:
        """Normalize cluster code."""
        cluster_upper = cluster.upper().replace(' ', '').replace('-', '')
        return CLUSTER_MAP.get(cluster_upper, cluster.upper())

    def _extract_year_from_topic(self, topic_code: str) -> Optional[int]:
        """Extract year from topic code like HORIZON-CL5-2024-D3-01-04."""
        if not topic_code:
            return None
        match = re.search(r'20[2-3][0-9]', topic_code)
        if match:
            return int(match.group(0))
        return None

    def analyze_history(
        self,
        topic_pattern: Optional[str] = None,
        cluster: Optional[str] = None,
        keywords: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        action_types: Optional[List[str]] = None,
        include_projects: bool = True,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Analyze historical funding patterns for specific topic areas.

        Args:
            topic_pattern: Topic code pattern (e.g., "HORIZON-CL4-2023")
            cluster: Cluster code (e.g., "CL4", "CL5")
            keywords: Keywords to search in call titles/descriptions
            year_from: Starting year filter
            year_to: Ending year filter
            action_types: Filter by action types (RIA, IA, CSA)
            include_projects: Include funded project examples
            limit: Max results per query

        Returns:
            Comprehensive analysis of funding history
        """
        try:
            conn = self._get_connection()
            if not conn:
                return {
                    "success": False,
                    "tool_name": "analyze_call_history",
                    "error": "Database unavailable",
                    "message": "Cannot analyze call history - database connection failed."
                }

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Normalize cluster if provided
            if cluster:
                cluster = self._normalize_cluster(cluster)

            # Get calls from funding_calls table
            calls = self._get_calls_history(
                cursor, topic_pattern, cluster, keywords,
                year_from, year_to, action_types, limit
            )

            # Get funded projects
            projects = []
            if include_projects:
                projects = self._get_funded_projects(
                    cursor, topic_pattern, cluster, keywords,
                    year_from, year_to, limit
                )

            cursor.close()
            conn.close()

            if not calls and not projects:
                return {
                    "success": True,
                    "tool_name": "analyze_call_history",
                    "query_params": {
                        "topic_pattern": topic_pattern,
                        "cluster": cluster,
                        "keywords": keywords,
                        "year_range": f"{year_from or 'start'}-{year_to or 'now'}"
                    },
                    "calls_analyzed": 0,
                    "projects_funded": 0,
                    "message": "No matching calls or projects found. Try broadening your search.",
                    "suggestions": [
                        "Remove year filters for broader results",
                        "Try different keywords",
                        "Search by cluster only (e.g., CL4, CL5)"
                    ]
                }

            # Build timeline
            timeline = self._build_timeline(calls, projects)

            # Analyze by action type
            by_action_type = self._analyze_by_action_type(calls, projects)

            # Identify top topics
            top_topics = self._identify_top_topics(projects)

            # Detect trends
            trends = self._detect_trends(timeline, projects, keywords)

            # Generate recommendations
            recommendations = self._generate_recommendations(trends, top_topics, cluster, keywords)

            # Calculate totals
            total_funding = sum(p.get('eu_contribution', 0) for p in projects)

            return {
                "success": True,
                "tool_name": "analyze_call_history",
                "query_params": {
                    "topic_pattern": topic_pattern,
                    "cluster": cluster,
                    "keywords": keywords,
                    "year_range": f"{year_from or '2021'}-{year_to or 'now'}",
                    "action_types": action_types
                },
                "calls_analyzed": len(calls),
                "total_funding_allocated": total_funding,
                "projects_funded": len(projects),
                "timeline": timeline,
                "funding_by_action_type": by_action_type,
                "top_funded_topics": top_topics[:10],
                "trends": trends,
                "sample_funded_projects": self._format_sample_projects(projects[:8]),
                "recommendations": recommendations,
                "data_source": "cordis_projects",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Call history analysis error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "tool_name": "analyze_call_history",
                "error": str(e),
                "message": "Analysis failed. Please try again with different parameters."
            }

    def _get_calls_history(
        self,
        cursor,
        topic_pattern: Optional[str],
        cluster: Optional[str],
        keywords: Optional[str],
        year_from: Optional[int],
        year_to: Optional[int],
        action_types: Optional[List[str]],
        limit: int
    ) -> List[Dict]:
        """Get calls from funding_calls table."""
        where_conditions = ["topic_code IS NOT NULL"]
        params = []

        if topic_pattern:
            where_conditions.append("topic_code ILIKE %s")
            params.append(f"%{topic_pattern}%")

        if cluster:
            # Match cluster in topic_code or cluster field
            where_conditions.append("(topic_code ILIKE %s OR cluster = %s)")
            params.extend([f"%{cluster}%", cluster])

        if keywords:
            where_conditions.append("(title ILIKE %s OR scope ILIKE %s OR expected_outcome ILIKE %s)")
            keyword_pattern = f"%{keywords}%"
            params.extend([keyword_pattern, keyword_pattern, keyword_pattern])

        if year_from:
            where_conditions.append("(call_year >= %s OR topic_code ~ %s)")
            params.extend([year_from, f"20[2-3][0-9]"])  # Will filter after

        if year_to:
            where_conditions.append("(call_year <= %s OR call_year IS NULL)")
            params.append(year_to)

        if action_types:
            action_placeholders = ','.join(['%s'] * len(action_types))
            where_conditions.append(f"action_type IN ({action_placeholders})")
            params.extend([at.upper() for at in action_types])

        where_clause = " AND ".join(where_conditions)

        sql = f"""
            SELECT
                topic_code,
                title,
                action_type,
                call_year,
                deadline,
                cluster,
                budget_total,
                scope,
                expected_outcome
            FROM funding_calls
            WHERE {where_clause}
            ORDER BY COALESCE(call_year, 2025) DESC, topic_code
            LIMIT %s
        """
        params.append(limit)

        cursor.execute(sql, params)
        results = cursor.fetchall()

        calls = []
        for r in results:
            # Extract year from topic_code if call_year is null
            year = r['call_year'] or self._extract_year_from_topic(r['topic_code'])

            # Apply year_from filter for extracted years
            if year_from and year and year < year_from:
                continue
            if year_to and year and year > year_to:
                continue

            calls.append({
                "topic_code": r['topic_code'],
                "title": r['title'],
                "action_type": r['action_type'],
                "year": year,
                "deadline": str(r['deadline']) if r['deadline'] else None,
                "cluster": r['cluster'] or self._extract_cluster_from_topic(r['topic_code']),
                "budget_total": float(r['budget_total']) if r['budget_total'] else None
            })

        return calls

    def _extract_cluster_from_topic(self, topic_code: str) -> Optional[str]:
        """Extract cluster from topic code."""
        if not topic_code:
            return None
        match = re.search(r'CL[1-6]', topic_code.upper())
        if match:
            return match.group(0)
        if 'HLTH' in topic_code.upper():
            return 'CL1'
        if 'ERC' in topic_code.upper():
            return 'ERC'
        if 'EIC' in topic_code.upper():
            return 'EIC'
        if 'MSCA' in topic_code.upper():
            return 'MSCA'
        return None

    def _get_funded_projects(
        self,
        cursor,
        topic_pattern: Optional[str],
        cluster: Optional[str],
        keywords: Optional[str],
        year_from: Optional[int],
        year_to: Optional[int],
        limit: int
    ) -> List[Dict]:
        """Get funded projects matching criteria."""
        where_conditions = ["\"frameworkProgramme\" = 'HORIZON'"]
        params = []

        if topic_pattern:
            where_conditions.append("topics ILIKE %s")
            params.append(f"%{topic_pattern}%")

        if cluster:
            # Map cluster to what appears in topics field
            cluster_patterns = {
                'CL1': ['CL1', 'HLTH'],
                'CL2': ['CL2'],
                'CL3': ['CL3'],
                'CL4': ['CL4'],
                'CL5': ['CL5'],
                'CL6': ['CL6'],
                'ERC': ['ERC'],
                'EIC': ['EIC'],
                'MSCA': ['MSCA'],
            }
            patterns = cluster_patterns.get(cluster, [cluster])
            cluster_conditions = " OR ".join(["topics ILIKE %s" for _ in patterns])
            where_conditions.append(f"({cluster_conditions})")
            params.extend([f"%{p}%" for p in patterns])

        if keywords:
            where_conditions.append("(title ILIKE %s OR objective ILIKE %s)")
            keyword_pattern = f"%{keywords}%"
            params.extend([keyword_pattern, keyword_pattern])

        if year_from:
            where_conditions.append("EXTRACT(YEAR FROM \"startDate\") >= %s")
            params.append(year_from)

        if year_to:
            where_conditions.append("EXTRACT(YEAR FROM \"startDate\") <= %s")
            params.append(year_to)

        where_clause = " AND ".join(where_conditions)

        sql = f"""
            SELECT
                id,
                acronym,
                title,
                topics,
                "ecMaxContribution",
                "totalCost",
                "startDate",
                "endDate",
                "fundingScheme",
                status
            FROM projects
            WHERE {where_clause}
            ORDER BY "startDate" DESC NULLS LAST
            LIMIT %s
        """
        params.append(limit)

        cursor.execute(sql, params)
        results = cursor.fetchall()

        projects = []
        for r in results:
            start_year = r['startDate'].year if r['startDate'] else None
            projects.append({
                "id": str(r['id']),
                "acronym": r['acronym'],
                "title": r['title'],
                "topics": r['topics'],
                "eu_contribution": float(r['ecMaxContribution']) if r['ecMaxContribution'] else 0,
                "total_cost": float(r['totalCost']) if r['totalCost'] else 0,
                "start_date": str(r['startDate'])[:10] if r['startDate'] else None,
                "end_date": str(r['endDate'])[:10] if r['endDate'] else None,
                "start_year": start_year,
                "action_type": r['fundingScheme'],
                "status": r['status'],
                "cluster": self._extract_cluster_from_topic(r['topics'])
            })

        return projects

    def _build_timeline(self, calls: List[Dict], projects: List[Dict]) -> Dict[str, Any]:
        """Build year-by-year timeline from projects (more reliable data)."""
        timeline = defaultdict(lambda: {
            "calls": 0,
            "total_funding": 0,
            "projects_funded": 0,
            "avg_project_budget": 0,
            "key_topics": []
        })

        # Group calls by year
        for call in calls:
            year = call.get('year')
            if year:
                timeline[year]["calls"] += 1

        # Group projects by year
        topic_counts = defaultdict(lambda: defaultdict(int))
        for project in projects:
            year = project.get('start_year')
            if year:
                timeline[year]["projects_funded"] += 1
                timeline[year]["total_funding"] += project.get('eu_contribution', 0)

                # Track topics
                topic = project.get('topics', '')
                if topic:
                    # Extract main topic (first one if multiple)
                    main_topic = topic.split(';')[0].strip()
                    topic_counts[year][main_topic] += 1

        # Calculate averages and add key topics
        for year, data in timeline.items():
            if data["projects_funded"] > 0:
                data["avg_project_budget"] = round(data["total_funding"] / data["projects_funded"], 0)

            # Add top 3 topics for this year
            if year in topic_counts:
                sorted_topics = sorted(topic_counts[year].items(), key=lambda x: x[1], reverse=True)
                data["key_topics"] = [
                    {"topic": t[0], "projects": t[1]}
                    for t in sorted_topics[:3]
                ]

        # Convert to sorted dict
        return dict(sorted(timeline.items(), reverse=True))

    def _analyze_by_action_type(self, calls: List[Dict], projects: List[Dict]) -> Dict[str, Any]:
        """Analyze funding by action type."""
        by_type = defaultdict(lambda: {
            "projects": 0,
            "total_funding": 0,
            "avg_funding": 0
        })

        for project in projects:
            action_type = project.get('action_type', 'Unknown')
            # Normalize action type
            if action_type:
                if 'RIA' in action_type.upper():
                    action_type = 'RIA'
                elif 'IA' in action_type.upper() and 'RIA' not in action_type.upper():
                    action_type = 'IA'
                elif 'CSA' in action_type.upper():
                    action_type = 'CSA'
                elif 'ERC' in action_type.upper():
                    action_type = 'ERC'
                elif 'MSCA' in action_type.upper():
                    action_type = 'MSCA'
                elif 'EIC' in action_type.upper():
                    action_type = 'EIC'

            by_type[action_type]["projects"] += 1
            by_type[action_type]["total_funding"] += project.get('eu_contribution', 0)

        # Calculate averages
        for action_type, data in by_type.items():
            if data["projects"] > 0:
                data["avg_funding"] = round(data["total_funding"] / data["projects"], 0)

        return dict(sorted(by_type.items(), key=lambda x: x[1]["total_funding"], reverse=True))

    def _identify_top_topics(self, projects: List[Dict]) -> List[Dict]:
        """Identify most funded topic areas."""
        topic_stats = defaultdict(lambda: {
            "topic": "",
            "projects": 0,
            "total_funding": 0,
            "avg_funding": 0
        })

        for project in projects:
            topic = project.get('topics', '')
            if topic:
                # Use first topic if multiple
                main_topic = topic.split(';')[0].strip()
                # Extract topic prefix (e.g., HORIZON-CL5-2024)
                parts = main_topic.split('-')
                if len(parts) >= 3:
                    topic_prefix = '-'.join(parts[:4]) if len(parts) >= 4 else main_topic
                else:
                    topic_prefix = main_topic

                topic_stats[topic_prefix]["topic"] = topic_prefix
                topic_stats[topic_prefix]["projects"] += 1
                topic_stats[topic_prefix]["total_funding"] += project.get('eu_contribution', 0)

        # Calculate averages
        result = []
        for topic_key, data in topic_stats.items():
            if data["projects"] > 0:
                data["avg_funding"] = round(data["total_funding"] / data["projects"], 0)
            result.append(data)

        # Sort by total funding
        return sorted(result, key=lambda x: x["total_funding"], reverse=True)

    def _detect_trends(
        self,
        timeline: Dict,
        projects: List[Dict],
        keywords: Optional[str]
    ) -> Dict[str, Any]:
        """Detect funding trends over time."""
        years = sorted([y for y in timeline.keys() if isinstance(y, int)])

        if len(years) < 2:
            return {
                "funding_trend": "insufficient_data",
                "note": "Need at least 2 years of data for trend analysis"
            }

        # Calculate year-over-year growth
        budgets = [timeline[y]["total_funding"] for y in years]
        growth_rates = []
        for i in range(1, len(budgets)):
            if budgets[i-1] > 0:
                growth = (budgets[i] - budgets[i-1]) / budgets[i-1] * 100
                growth_rates.append(growth)

        avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0

        # Determine trend
        if avg_growth > 10:
            trend = "strongly_increasing"
        elif avg_growth > 3:
            trend = "increasing"
        elif avg_growth > -3:
            trend = "stable"
        elif avg_growth > -10:
            trend = "decreasing"
        else:
            trend = "strongly_decreasing"

        # Project count trend
        project_counts = [timeline[y]["projects_funded"] for y in years]
        project_growth = []
        for i in range(1, len(project_counts)):
            if project_counts[i-1] > 0:
                growth = (project_counts[i] - project_counts[i-1]) / project_counts[i-1] * 100
                project_growth.append(growth)

        avg_project_growth = sum(project_growth) / len(project_growth) if project_growth else 0

        return {
            "funding_trend": trend,
            "year_over_year_funding_growth": round(avg_growth, 1),
            "year_over_year_project_growth": round(avg_project_growth, 1),
            "years_analyzed": len(years),
            "first_year": min(years),
            "last_year": max(years),
            "total_projects_in_period": sum(project_counts),
            "total_funding_in_period": sum(budgets),
            "peak_year": years[budgets.index(max(budgets))] if budgets else None,
            "peak_funding": max(budgets) if budgets else 0
        }

    def _generate_recommendations(
        self,
        trends: Dict,
        top_topics: List[Dict],
        cluster: Optional[str],
        keywords: Optional[str]
    ) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Trend-based recommendations
        trend = trends.get('funding_trend', 'unknown')
        if trend in ['strongly_increasing', 'increasing']:
            recommendations.append(f"Funding in this area is {trend.replace('_', ' ')} - good timing for proposals")
        elif trend == 'stable':
            recommendations.append("Funding remains stable - consistent opportunities available")
        elif trend in ['decreasing', 'strongly_decreasing']:
            recommendations.append("Funding trend is declining - consider related emerging topics")

        # Growth rate insight
        growth = trends.get('year_over_year_funding_growth', 0)
        if growth > 15:
            recommendations.append(f"Strong growth ({growth:.0f}% YoY) indicates high EU priority")
        elif growth < -10:
            recommendations.append(f"Declining funding ({growth:.0f}% YoY) - explore adjacent topic areas")

        # Top topics insights
        if top_topics:
            top_topic = top_topics[0]
            avg_budget = top_topic.get('avg_funding', 0)
            if avg_budget > 0:
                recommendations.append(
                    f"Average project budget: €{avg_budget/1_000_000:.1f}M - "
                    f"plan consortium accordingly"
                )

        # Cluster-specific recommendations
        if cluster:
            cluster_tips = {
                'CL4': "Digital cluster: Strong focus on AI, data, and cybersecurity",
                'CL5': "Climate cluster: Emphasis on clean energy and decarbonization",
                'CL6': "Food cluster: Focus on sustainable food systems and bioeconomy",
                'CL1': "Health cluster: Priorities include digital health and personalized medicine",
            }
            if cluster in cluster_tips:
                recommendations.append(cluster_tips[cluster])

        # General recommendations
        if len(recommendations) < 3:
            recommendations.append("Check upcoming Work Programme for new call openings")
            recommendations.append("Consider cross-cluster proposals for broader impact")

        return recommendations[:5]

    def _format_sample_projects(self, projects: List[Dict]) -> List[Dict]:
        """Format sample projects for output."""
        return [
            {
                "acronym": p.get('acronym', 'N/A'),
                "title": p.get('title', '')[:80] + "..." if len(p.get('title', '')) > 80 else p.get('title', ''),
                "topic": p.get('topics', '').split(';')[0][:50] if p.get('topics') else 'N/A',
                "eu_contribution": p.get('eu_contribution', 0),
                "start_date": p.get('start_date'),
                "action_type": p.get('action_type'),
                "cordis_url": f"https://cordis.europa.eu/project/id/{p.get('id')}"
            }
            for p in projects
        ]


# Async wrapper for tool orchestrator compatibility
async def analyze_call_history_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute call history analysis tool.

    This tool analyzes historical funding patterns for Horizon Europe topics.
    Use when users want to understand funding trends, what got funded in the past,
    topic frequency, or funding evolution over time.
    """
    tool = CallHistoryTool()

    return tool.analyze_history(
        topic_pattern=params.get('topic_pattern'),
        cluster=params.get('cluster'),
        keywords=params.get('keywords'),
        year_from=params.get('year_from'),
        year_to=params.get('year_to'),
        action_types=params.get('action_types'),
        include_projects=params.get('include_projects', True),
        limit=params.get('limit', 50)
    )
