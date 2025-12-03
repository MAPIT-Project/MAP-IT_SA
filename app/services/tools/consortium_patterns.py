"""
Consortium Patterns Tool for Horizon Europe Projects.

Analyzes real consortium compositions from funded CORDIS projects to help users
understand what successful consortia look like in their domain.
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

# Organization type descriptions
ORG_TYPE_DESCRIPTIONS = {
    "HES": "Higher Education Institutions (Universities)",
    "REC": "Research Organizations",
    "PRC": "Private Companies (Large)",
    "SME": "Small and Medium Enterprises",
    "PUB": "Public Bodies",
    "OTH": "Other Organizations"
}

# Cluster mapping (same as budget_benchmark)
CLUSTER_MAP = {
    'CL1': 'HLTH', 'CLUSTER1': 'HLTH', 'CLUSTER-1': 'HLTH', 'HEALTH': 'HLTH',
    'CL2': 'CL2', 'CLUSTER2': 'CL2', 'CLUSTER-2': 'CL2', 'CULTURE': 'CL2',
    'CL3': 'CL3', 'CLUSTER3': 'CL3', 'CLUSTER-3': 'CL3', 'SECURITY': 'CL3',
    'CL4': 'CL4', 'CLUSTER4': 'CL4', 'CLUSTER-4': 'CL4', 'DIGITAL': 'CL4',
    'CL5': 'CL5', 'CLUSTER5': 'CL5', 'CLUSTER-5': 'CL5', 'CLIMATE': 'CL5', 'ENERGY': 'CL5',
    'CL6': 'CL6', 'CLUSTER6': 'CL6', 'CLUSTER-6': 'CL6', 'FOOD': 'CL6',
    'EIC': 'EIC', 'ERC': 'ERC', 'MSCA': 'MSCA',
}


class ConsortiumPatternsTool:
    """Tool to analyze consortium composition patterns from funded projects."""

    def __init__(self):
        """Initialize with database connection."""
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.warning("DATABASE_URL not set - consortium patterns will be limited")

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _normalize_cluster(self, cluster: str) -> str:
        """Normalize cluster code to topic pattern."""
        cluster_upper = cluster.upper().replace(' ', '').replace('-', '')
        return CLUSTER_MAP.get(cluster_upper, cluster.upper())

    def get_patterns(
        self,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        topic_keywords: Optional[str] = None,
        min_projects: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze consortium composition patterns from funded Horizon Europe projects.

        Args:
            cluster: Cluster code (e.g., "CL4", "CL5", "EIC")
            action_type: Action type (e.g., "RIA", "IA", "CSA")
            topic_keywords: Keywords to filter projects
            min_projects: Minimum projects for reliable patterns

        Returns:
            Consortium patterns and recommendations
        """
        try:
            conn = self._get_connection()
            if not conn:
                return self._get_fallback_patterns(cluster, action_type)

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
                action_normalized = action_type.upper()
                where_conditions.append("p.\"fundingScheme\" ILIKE %s")
                params.append(f"%{action_normalized}%")

            # Topic keywords filter
            if topic_keywords:
                keywords = topic_keywords.split()
                for kw in keywords:
                    where_conditions.append(
                        "(p.objective ILIKE %s OR p.title ILIKE %s)"
                    )
                    params.extend([f"%{kw}%", f"%{kw}%"])

            where_clause = " AND ".join(where_conditions)

            # 1. Get consortium size statistics
            size_sql = f"""
                WITH project_orgs AS (
                    SELECT
                        p.id as project_id,
                        COUNT(DISTINCT o."organisationID") as partner_count,
                        COUNT(DISTINCT o.country) as country_count
                    FROM projects p
                    LEFT JOIN organizations o ON p.id = o."projectID"
                    WHERE {where_clause}
                    GROUP BY p.id
                    HAVING COUNT(DISTINCT o."organisationID") > 0
                )
                SELECT
                    COUNT(*) as project_count,
                    MIN(partner_count) as min_partners,
                    MAX(partner_count) as max_partners,
                    AVG(partner_count) as avg_partners,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY partner_count) as median_partners,
                    AVG(country_count) as avg_countries,
                    MIN(country_count) as min_countries,
                    MAX(country_count) as max_countries
                FROM project_orgs
            """
            cursor.execute(size_sql, params)
            size_stats = cursor.fetchone()

            if not size_stats or size_stats['project_count'] == 0:
                cursor.close()
                conn.close()
                return self._get_fallback_patterns(cluster, action_type)

            # 2. Get organization type distribution
            org_type_sql = f"""
                SELECT
                    o."activityType" as org_type,
                    COUNT(*) as participation_count,
                    COUNT(DISTINCT p.id) as project_count,
                    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
                FROM projects p
                JOIN organizations o ON p.id = o."projectID"
                WHERE {where_clause}
                  AND o."activityType" IS NOT NULL
                GROUP BY o."activityType"
                ORDER BY participation_count DESC
            """
            cursor.execute(org_type_sql, params)
            org_types = cursor.fetchall()

            # 3. Get country distribution
            # Get total project count first for percentage calculation
            total_projects = int(size_stats['project_count'])

            country_sql = f"""
                SELECT
                    o.country,
                    COUNT(*) as participation_count,
                    COUNT(DISTINCT p.id) as project_count
                FROM projects p
                JOIN organizations o ON p.id = o."projectID"
                WHERE {where_clause}
                  AND o.country IS NOT NULL
                GROUP BY o.country
                ORDER BY participation_count DESC
                LIMIT 15
            """
            cursor.execute(country_sql, params)
            countries_raw = cursor.fetchall()

            # Calculate participation rate manually
            countries = []
            for c in countries_raw:
                countries.append({
                    'country': c['country'],
                    'participation_count': c['participation_count'],
                    'project_count': c['project_count'],
                    'participation_rate': round(100.0 * c['project_count'] / max(total_projects, 1), 2)
                })

            # 4. Get coordinator profile
            coordinator_sql = f"""
                SELECT
                    o."activityType" as coord_type,
                    o.country as coord_country,
                    COUNT(*) as coordination_count
                FROM projects p
                JOIN organizations o ON p.id = o."projectID"
                WHERE {where_clause}
                  AND o.role = 'coordinator'
                GROUP BY o."activityType", o.country
                ORDER BY coordination_count DESC
            """
            cursor.execute(coordinator_sql, params)
            coordinators = cursor.fetchall()

            # 5. Get sample consortia
            sample_sql = f"""
                SELECT
                    p.id,
                    p.acronym,
                    p.title,
                    p."ecMaxContribution",
                    COUNT(DISTINCT o."organisationID") as partner_count,
                    COUNT(DISTINCT o.country) as country_count,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.name END) as coordinator_name,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.country END) as coordinator_country,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o."activityType" END) as coordinator_type,
                    ARRAY_AGG(DISTINCT o."activityType") FILTER (WHERE o."activityType" IS NOT NULL) as org_types
                FROM projects p
                JOIN organizations o ON p.id = o."projectID"
                WHERE {where_clause}
                GROUP BY p.id, p.acronym, p.title, p."ecMaxContribution"
                HAVING COUNT(DISTINCT o."organisationID") >= 3
                ORDER BY p."startDate" DESC NULLS LAST
                LIMIT 5
            """
            cursor.execute(sample_sql, params)
            samples = cursor.fetchall()

            cursor.close()
            conn.close()

            # Process results
            project_count = int(size_stats['project_count'])

            # Organization type distribution
            org_type_distribution = {}
            total_participations = sum(o['participation_count'] for o in org_types)
            for ot in org_types:
                org_code = ot['org_type']
                if org_code:
                    org_type_distribution[org_code] = {
                        "percentage": float(ot['percentage'] or 0),
                        "avg_per_project": round(ot['participation_count'] / max(project_count, 1), 1),
                        "description": ORG_TYPE_DESCRIPTIONS.get(org_code, org_code)
                    }

            # Country patterns
            country_patterns = {
                "top_participating": [
                    {
                        "country": c['country'],
                        "participation_rate": float(c['participation_rate'] or 0),
                        "project_count": int(c['project_count'] or 0)
                    }
                    for c in countries[:10]
                ],
                "geographic_diversity": {
                    "avg_countries": round(float(size_stats['avg_countries'] or 0), 1),
                    "min_countries": int(size_stats['min_countries'] or 0),
                    "max_countries": int(size_stats['max_countries'] or 0)
                }
            }

            # Coordinator profile
            coord_by_type = {}
            coord_by_country = {}
            for c in coordinators:
                if c['coord_type']:
                    coord_by_type[c['coord_type']] = coord_by_type.get(c['coord_type'], 0) + c['coordination_count']
                if c['coord_country']:
                    coord_by_country[c['coord_country']] = coord_by_country.get(c['coord_country'], 0) + c['coordination_count']

            # Sort and limit
            coord_by_type = dict(sorted(coord_by_type.items(), key=lambda x: x[1], reverse=True)[:5])
            coord_by_country = dict(sorted(coord_by_country.items(), key=lambda x: x[1], reverse=True)[:10])

            coordinator_profile = {
                "by_type": coord_by_type,
                "by_country": coord_by_country
            }

            # Sample consortia
            sample_consortia = []
            for s in samples:
                # Count org types in sample
                org_type_counts = {}
                if s['org_types']:
                    for ot in s['org_types']:
                        org_type_counts[ot] = org_type_counts.get(ot, 0) + 1

                sample_consortia.append({
                    "project_acronym": s['acronym'] or 'N/A',
                    "consortium_size": int(s['partner_count'] or 0),
                    "countries": int(s['country_count'] or 0),
                    "eu_contribution": round(float(s['ecMaxContribution'] or 0), 0),
                    "coordinator": {
                        "name": s['coordinator_name'] or 'Unknown',
                        "type": s['coordinator_type'] or 'Unknown',
                        "country": s['coordinator_country'] or 'Unknown'
                    }
                })

            # Generate recommendations
            recommendations = self._generate_recommendations(
                org_type_distribution, country_patterns, coordinator_profile,
                size_stats, action_type, project_count
            )

            return {
                "success": True,
                "tool_name": "get_consortium_patterns",
                "query_params": {
                    "cluster": cluster,
                    "action_type": action_type,
                    "topic_keywords": topic_keywords
                },
                "projects_analyzed": project_count,
                "consortium_size": {
                    "min": int(size_stats['min_partners'] or 0),
                    "max": int(size_stats['max_partners'] or 0),
                    "average": round(float(size_stats['avg_partners'] or 0), 1),
                    "median": round(float(size_stats['median_partners'] or 0), 0),
                    "recommended": f"{max(3, int(size_stats['median_partners'] or 8) - 2)}-{int(size_stats['median_partners'] or 8) + 3} partners"
                },
                "organization_type_distribution": org_type_distribution,
                "country_patterns": country_patterns,
                "coordinator_profile": coordinator_profile,
                "recommendations": recommendations,
                "sample_consortia": sample_consortia,
                "data_source": "cordis_database",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Consortium patterns error: {e}")
            import traceback
            traceback.print_exc()
            return self._get_fallback_patterns(cluster, action_type)

    def _generate_recommendations(
        self,
        org_dist: Dict,
        country_patterns: Dict,
        coordinator: Dict,
        size_stats: Dict,
        action_type: Optional[str],
        project_count: int
    ) -> Dict[str, Any]:
        """Generate actionable recommendations based on patterns."""

        recommendations = {
            "ideal_composition": [],
            "country_advice": "",
            "coordinator_advice": "",
            "confidence": "high" if project_count >= 20 else "medium" if project_count >= 5 else "low",
            "notes": []
        }

        # Calculate ideal composition based on org type distribution
        median_size = float(size_stats.get('median_partners') or 8)

        for org_type, data in sorted(org_dist.items(), key=lambda x: x[1]['percentage'], reverse=True):
            avg_count = data['avg_per_project']
            if avg_count >= 0.5:  # Only include if typically at least 0.5 per project
                count_str = f"{max(1, round(avg_count))}"
                if avg_count >= 2:
                    count_str = f"{max(1, round(avg_count) - 1)}-{round(avg_count) + 1}"
                desc = ORG_TYPE_DESCRIPTIONS.get(org_type, org_type)
                recommendations["ideal_composition"].append(f"{count_str} {desc}")

        # Country advice
        avg_countries = country_patterns.get('geographic_diversity', {}).get('avg_countries', 6)
        recommendations["country_advice"] = (
            f"Include partners from {max(3, int(avg_countries) - 2)}-{int(avg_countries) + 2} "
            f"EU member states for good geographic balance"
        )

        # Coordinator advice
        top_coord_type = max(coordinator.get('by_type', {'HES': 1}).items(), key=lambda x: x[1])[0]
        coord_desc = ORG_TYPE_DESCRIPTIONS.get(top_coord_type, top_coord_type)
        recommendations["coordinator_advice"] = f"{coord_desc} most commonly coordinate these projects"

        # Action-type specific advice
        if action_type:
            at = action_type.upper()
            if at == "RIA":
                recommendations["notes"].append("RIA projects typically have strong research institution presence")
            elif at == "IA":
                recommendations["notes"].append("IA projects often have more industry partners for demonstration/deployment")
            elif at == "CSA":
                recommendations["notes"].append("CSA projects are typically smaller with policy/coordination focus")

        if project_count < 10:
            recommendations["notes"].append(
                f"Based on {project_count} projects - consider broadening criteria for more reliable patterns"
            )

        return recommendations

    def _get_fallback_patterns(
        self,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return fallback patterns when database is unavailable."""

        # Default patterns based on action type
        defaults = {
            "RIA": {
                "size": 10,
                "countries": 7,
                "hes_pct": 35,
                "rec_pct": 30,
                "prc_pct": 20,
                "sme_pct": 15
            },
            "IA": {
                "size": 14,
                "countries": 9,
                "hes_pct": 25,
                "rec_pct": 20,
                "prc_pct": 35,
                "sme_pct": 20
            },
            "CSA": {
                "size": 8,
                "countries": 6,
                "hes_pct": 30,
                "rec_pct": 25,
                "prc_pct": 25,
                "sme_pct": 20
            }
        }

        at = (action_type or "RIA").upper()
        pattern = defaults.get(at, defaults["RIA"])

        return {
            "success": True,
            "tool_name": "get_consortium_patterns",
            "query_params": {
                "cluster": cluster,
                "action_type": action_type
            },
            "projects_analyzed": "N/A (using typical values)",
            "consortium_size": {
                "typical": pattern["size"],
                "recommended": f"{pattern['size'] - 2}-{pattern['size'] + 3} partners"
            },
            "organization_type_distribution": {
                "HES": {"percentage": pattern["hes_pct"], "description": ORG_TYPE_DESCRIPTIONS["HES"]},
                "REC": {"percentage": pattern["rec_pct"], "description": ORG_TYPE_DESCRIPTIONS["REC"]},
                "PRC": {"percentage": pattern["prc_pct"], "description": ORG_TYPE_DESCRIPTIONS["PRC"]},
                "SME": {"percentage": pattern["sme_pct"], "description": ORG_TYPE_DESCRIPTIONS["SME"]}
            },
            "country_patterns": {
                "geographic_diversity": {
                    "typical_countries": pattern["countries"]
                }
            },
            "recommendations": {
                "ideal_composition": [
                    f"3-4 {ORG_TYPE_DESCRIPTIONS['HES']}",
                    f"2-3 {ORG_TYPE_DESCRIPTIONS['REC']}",
                    f"2-3 {ORG_TYPE_DESCRIPTIONS['PRC']}",
                    f"1-2 {ORG_TYPE_DESCRIPTIONS['SME']}"
                ],
                "country_advice": f"Include partners from {pattern['countries'] - 2}-{pattern['countries'] + 2} EU member states",
                "coordinator_advice": "Universities and research organizations coordinate most successfully",
                "confidence": "low",
                "notes": ["Using typical values - database unavailable for specific statistics"]
            },
            "sample_consortia": [],
            "data_source": "fallback_estimates",
            "timestamp": datetime.now().isoformat()
        }


# Async wrapper for tool orchestrator compatibility
async def get_consortium_patterns_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute consortium patterns tool.

    This tool analyzes consortium composition patterns from funded Horizon Europe projects.
    Use it when users ask about typical consortium composition, partner types, country
    distribution, or coordinator profiles for specific domains.
    """
    tool = ConsortiumPatternsTool()

    return tool.get_patterns(
        cluster=params.get('cluster'),
        action_type=params.get('action_type'),
        topic_keywords=params.get('topic_keywords'),
        min_projects=params.get('min_projects', 10)
    )
