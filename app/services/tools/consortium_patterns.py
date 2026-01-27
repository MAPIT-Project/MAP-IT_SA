"""
Consortium Patterns Tool for Horizon Europe Projects.

Analyzes real consortium compositions from funded CORDIS projects to help users
understand what successful consortia look like in their domain.

HYBRID ARCHITECTURE: Combines Neo4j graph patterns with PostgreSQL detailed analysis
for comprehensive consortium insights.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()
logger = logging.getLogger(__name__)

# Organization type descriptions
ORG_TYPE_DESCRIPTIONS = {
    "HES": "Higher Education Institutions (Universities)",
    "REC": "Research Organizations",
    "PRC": "Private Companies (Large)",
    "SME": "Small and Medium Enterprises",
    "PUB": "Public Bodies",
    "OTH": "Other Organizations",
}

# Cluster keyword mapping for automatic cluster inference
CLUSTER_KEYWORDS = {
    "CLUSTER-1": [
        "health",
        "medical",
        "clinical",
        "disease",
        "patient",
        "healthcare",
        "hospital",
        "therapy",
        "diagnosis",
        "pharmaceutical",
        "cancer",
        "vaccine",
        "drug",
        "pandemic",
        "pathogen",
        "infection",
    ],
    "CLUSTER-2": [
        "culture",
        "democracy",
        "social",
        "heritage",
        "creative",
        "inclusive",
        "society",
        "governance",
        "media",
        "migration",
        "inequality",
        "education",
    ],
    "CLUSTER-3": [
        "security",
        "cybersecurity",
        "border",
        "crime",
        "disaster",
        "resilience",
        "defence",
        "defense",
        "terrorism",
        "critical infrastructure",
        "forensic",
    ],
    "CLUSTER-4": [
        "digital",
        "AI",
        "artificial intelligence",
        "data",
        "industry",
        "space",
        "manufacturing",
        "robotics",
        "computing",
        "machine learning",
        "quantum",
        "electronics",
        "semiconductor",
        "cloud",
        "IoT",
        "blockchain",
    ],
    "CLUSTER-5": [
        "climate",
        "energy",
        "mobility",
        "transport",
        "hydrogen",
        "battery",
        "renewable",
        "green",
        "carbon",
        "solar",
        "wind",
        "electric vehicle",
        "sustainable",
        "emission",
        "fuel cell",
        "smart grid",
    ],
    "CLUSTER-6": [
        "food",
        "agriculture",
        "bioeconomy",
        "biodiversity",
        "ocean",
        "environment",
        "soil",
        "water",
        "forestry",
        "marine",
        "fisheries",
        "circular economy",
        "ecosystem",
        "nature",
        "farming",
    ],
}

# Cluster mapping (same as budget_benchmark)
CLUSTER_MAP = {
    "CL1": "CLUSTER-1",
    "CLUSTER1": "CLUSTER-1",
    "CLUSTER-1": "CLUSTER-1",
    "HEALTH": "CLUSTER-1",
    "HLTH": "CLUSTER-1",
    "CL2": "CLUSTER-2",
    "CLUSTER2": "CLUSTER-2",
    "CLUSTER-2": "CLUSTER-2",
    "CULTURE": "CLUSTER-2",
    "CL3": "CLUSTER-3",
    "CLUSTER3": "CLUSTER-3",
    "CLUSTER-3": "CLUSTER-3",
    "SECURITY": "CLUSTER-3",
    "CL4": "CLUSTER-4",
    "CLUSTER4": "CLUSTER-4",
    "CLUSTER-4": "CLUSTER-4",
    "DIGITAL": "CLUSTER-4",
    "CL5": "CLUSTER-5",
    "CLUSTER5": "CLUSTER-5",
    "CLUSTER-5": "CLUSTER-5",
    "CLIMATE": "CLUSTER-5",
    "ENERGY": "CLUSTER-5",
    "CL6": "CLUSTER-6",
    "CLUSTER6": "CLUSTER-6",
    "CLUSTER-6": "CLUSTER-6",
    "FOOD": "CLUSTER-6",
    "EIC": "EIC",
    "ERC": "ERC",
    "MSCA": "MSCA",
}

# Reverse mapping for SQL queries (CLUSTER-X -> topic pattern)
CLUSTER_TO_TOPIC = {
    "CLUSTER-1": "HLTH",
    "CLUSTER-2": "CL2",
    "CLUSTER-3": "CL3",
    "CLUSTER-4": "CL4",
    "CLUSTER-5": "CL5",
    "CLUSTER-6": "CL6",
}


class ConsortiumPatternsTool:
    """
    Tool to analyze consortium composition patterns from funded projects.

    HYBRID ARCHITECTURE:
    - Neo4j Graph: Pre-aggregated consortium patterns, coordinator analysis, successful templates
    - PostgreSQL: Detailed breakdowns, sample consortia, keyword filtering
    - Parallel queries for performance
    """

    def __init__(self):
        """Initialize with database connection and graph service."""
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.warning("DATABASE_URL not set - consortium patterns will be limited")

        # Initialize graph service
        self._graph_service = None
        try:
            from ..data_intelligence.graph_service import GraphSearchService

            self._graph_service = GraphSearchService()
            logger.info("✅ Graph service available for consortium patterns")
        except Exception as e:
            logger.warning(f"⚠️ Graph service not available for consortium patterns: {e}")

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _normalize_cluster(self, cluster: str) -> str:
        """Normalize cluster code to CLUSTER-X format."""
        if not cluster:
            return None
        cluster_upper = cluster.upper().replace(" ", "").replace("-", "")
        return CLUSTER_MAP.get(
            cluster_upper, cluster.upper() if cluster.upper().startswith("CLUSTER") else None
        )

    def _infer_clusters_from_keywords(self, keywords: str) -> list[str]:
        """Infer relevant clusters from topic keywords."""
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

    def get_patterns(
        self,
        cluster: str | None = None,
        action_type: str | None = None,
        topic_keywords: str | None = None,
        min_projects: int = 10,
        include_successful_templates: bool = True,
        include_coordinator_analysis: bool = True,
    ) -> dict[str, Any]:
        """
        Analyze consortium composition patterns using HYBRID Graph+SQL architecture.

        Args:
            cluster: Cluster code (e.g., "CL4", "CL5", "CLUSTER-4")
            action_type: Action type (e.g., "RIA", "IA", "CSA")
            topic_keywords: Keywords to filter projects
            min_projects: Minimum projects for reliable patterns
            include_successful_templates: Include templates from successful projects
            include_coordinator_analysis: Include coordinator profile analysis

        Returns:
            Consortium patterns and recommendations from hybrid sources
        """
        # Normalize cluster code
        normalized_cluster = self._normalize_cluster(cluster)

        # Infer clusters from keywords if no cluster specified
        inferred_clusters = []
        if topic_keywords and not normalized_cluster:
            inferred_clusters = self._infer_clusters_from_keywords(topic_keywords)
            if inferred_clusters:
                normalized_cluster = inferred_clusters[0]

        # Execute hybrid search
        result = self._get_patterns_hybrid(
            cluster=normalized_cluster,
            action_type=action_type,
            topic_keywords=topic_keywords,
            min_projects=min_projects,
            include_successful_templates=include_successful_templates,
            include_coordinator_analysis=include_coordinator_analysis,
        )

        # Add inferred clusters to metadata
        if inferred_clusters:
            result["metadata"] = result.get("metadata", {})
            result["metadata"]["inferred_clusters"] = inferred_clusters

        return result

    def _get_patterns_hybrid(
        self,
        cluster: str | None,
        action_type: str | None,
        topic_keywords: str | None,
        min_projects: int,
        include_successful_templates: bool,
        include_coordinator_analysis: bool,
    ) -> dict[str, Any]:
        """Execute hybrid Graph+SQL consortium pattern analysis."""
        graph_patterns = None
        sql_patterns = None
        successful_templates = None
        coordinator_analysis = None

        # Use ThreadPoolExecutor for parallel queries
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}

            # Submit graph query if available
            if self._graph_service and cluster:
                futures["graph"] = executor.submit(self._get_patterns_graph, cluster, action_type)

            # Submit SQL query
            futures["sql"] = executor.submit(
                self._get_patterns_sql, cluster, action_type, topic_keywords
            )

            # Submit successful templates if requested
            if include_successful_templates and self._graph_service and cluster:
                futures["templates"] = executor.submit(
                    self._get_successful_templates, cluster, action_type
                )

            # Submit coordinator analysis if requested
            if include_coordinator_analysis and cluster:
                futures["coordinator"] = executor.submit(
                    self._get_coordinator_analysis, cluster, action_type
                )

            # Collect results
            for key, future in futures.items():
                try:
                    result = future.result(timeout=30)
                    if key == "graph":
                        graph_patterns = result
                    elif key == "sql":
                        sql_patterns = result
                    elif key == "templates":
                        successful_templates = result
                    elif key == "coordinator":
                        coordinator_analysis = result
                except Exception as e:
                    logger.warning(f"Failed to get {key} patterns: {e}")

        # Merge results
        merged = self._merge_pattern_results(graph_patterns, sql_patterns)

        # Build response
        project_count = merged.get("projects_analyzed", 0)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            merged.get("organization_type_distribution", {}),
            merged.get("country_patterns", {}),
            merged.get("coordinator_profile", {}),
            merged.get("consortium_size", {}),
            action_type,
            project_count,
        )

        result = {
            "success": True,
            "tool_name": "get_consortium_patterns",
            "query_params": {
                "cluster": cluster,
                "action_type": action_type,
                "topic_keywords": topic_keywords,
            },
            "projects_analyzed": project_count,
            "consortium_size": merged.get("consortium_size", {}),
            "organization_type_distribution": merged.get("organization_type_distribution", {}),
            "country_patterns": merged.get("country_patterns", {}),
            "coordinator_profile": merged.get("coordinator_profile", {}),
            "recommendations": recommendations,
            "sample_consortia": merged.get("sample_consortia", []),
            "metadata": {
                "search_type": (
                    "hybrid"
                    if graph_patterns and sql_patterns
                    else ("graph_only" if graph_patterns else "sql_only")
                ),
                "sources_used": [],
                "graph_sample_size": graph_patterns.get("sample_size", 0) if graph_patterns else 0,
                "sql_project_count": sql_patterns.get("project_count", 0) if sql_patterns else 0,
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Track sources used
        if graph_patterns:
            result["metadata"]["sources_used"].append("graph")
        if sql_patterns:
            result["metadata"]["sources_used"].append("sql")

        # Add optional analyses
        if successful_templates:
            result["successful_templates"] = successful_templates
        if coordinator_analysis:
            result["coordinator_analysis"] = coordinator_analysis

        return result

    def _get_patterns_graph(self, cluster: str, action_type: str | None) -> dict[str, Any] | None:
        """Get consortium patterns from Neo4j graph."""
        if not self._graph_service:
            return None

        try:
            patterns = self._graph_service.get_consortium_patterns(
                cluster_code=cluster, min_partners=3
            )

            if not patterns:
                return None

            # Get the pattern for this cluster
            pattern = (
                patterns[0]
                if len(patterns) == 1
                else next(
                    (p for p in patterns if p.get("cluster_code") == cluster),
                    patterns[0] if patterns else None,
                )
            )

            if not pattern:
                return None

            return {
                "avg_partners": pattern.get("avg_partners", 0),
                "avg_countries": pattern.get("avg_countries", 0),
                "sample_size": pattern.get("sample_size", 0),
                "top_coordinator_countries": pattern.get("top_coordinator_countries", []),
                "source": "neo4j_graph",
            }

        except Exception as e:
            logger.error(f"Graph patterns query failed: {e}")
            return None

    def _get_patterns_sql(
        self, cluster: str | None, action_type: str | None, topic_keywords: str | None
    ) -> dict[str, Any] | None:
        """Get consortium patterns from PostgreSQL."""
        try:
            conn = self._get_connection()
            if not conn:
                return None

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build WHERE conditions
            where_conditions = ["p.\"frameworkProgramme\" = 'HORIZON'"]
            params = []

            # Cluster filter
            if cluster:
                topic_pattern = CLUSTER_TO_TOPIC.get(cluster, cluster)
                where_conditions.append("p.topics ILIKE %s")
                params.append(f"%{topic_pattern}%")

            # Action type filter
            if action_type:
                action_normalized = action_type.upper()
                where_conditions.append('p."fundingScheme" ILIKE %s')
                params.append(f"%{action_normalized}%")

            # Topic keywords filter
            if topic_keywords:
                keywords = topic_keywords.split()
                for kw in keywords:
                    where_conditions.append("(p.objective ILIKE %s OR p.title ILIKE %s)")
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

            if not size_stats or size_stats["project_count"] == 0:
                cursor.close()
                conn.close()
                return None

            # 2. Get organization type distribution
            org_type_sql = f"""
                SELECT
                    COALESCE(o."activityType", 'OTH') as org_type,
                    COUNT(*) as participation_count,
                    COUNT(DISTINCT p.id) as project_count,
                    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
                FROM projects p
                JOIN organizations o ON p.id = o."projectID"
                WHERE {where_clause}
                GROUP BY COALESCE(o."activityType", 'OTH')
                ORDER BY participation_count DESC
            """
            cursor.execute(org_type_sql, params)
            org_types = cursor.fetchall()

            # 3. Get country distribution
            total_projects = int(size_stats["project_count"])

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

            countries = []
            for c in countries_raw:
                countries.append(
                    {
                        "country": c["country"],
                        "participation_count": c["participation_count"],
                        "project_count": c["project_count"],
                        "participation_rate": round(
                            100.0 * c["project_count"] / max(total_projects, 1), 2
                        ),
                    }
                )

            # 4. Get coordinator profile
            coordinator_sql = f"""
                SELECT
                    COALESCE(o."activityType", 'OTH') as coord_type,
                    o.country as coord_country,
                    COUNT(*) as coordination_count
                FROM projects p
                JOIN organizations o ON p.id = o."projectID"
                WHERE {where_clause}
                  AND o.role = 'coordinator'
                GROUP BY COALESCE(o."activityType", 'OTH'), o.country
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
                    MAX(CASE WHEN o.role = 'coordinator' THEN o."activityType" END) as coordinator_type
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

            # Process org type distribution
            org_type_distribution = {}
            for ot in org_types:
                org_code = ot["org_type"]
                if org_code:
                    org_type_distribution[org_code] = {
                        "percentage": float(ot["percentage"] or 0),
                        "avg_per_project": round(
                            ot["participation_count"] / max(total_projects, 1), 1
                        ),
                        "description": ORG_TYPE_DESCRIPTIONS.get(org_code, org_code),
                    }

            # Process coordinator profile
            coord_by_type = {}
            coord_by_country = {}
            for c in coordinators:
                if c["coord_type"]:
                    coord_by_type[c["coord_type"]] = (
                        coord_by_type.get(c["coord_type"], 0) + c["coordination_count"]
                    )
                if c["coord_country"]:
                    coord_by_country[c["coord_country"]] = (
                        coord_by_country.get(c["coord_country"], 0) + c["coordination_count"]
                    )

            coord_by_type = dict(
                sorted(coord_by_type.items(), key=lambda x: x[1], reverse=True)[:5]
            )
            coord_by_country = dict(
                sorted(coord_by_country.items(), key=lambda x: x[1], reverse=True)[:10]
            )

            # Process sample consortia
            sample_consortia = []
            for s in samples:
                sample_consortia.append(
                    {
                        "project_acronym": s["acronym"] or "N/A",
                        "consortium_size": int(s["partner_count"] or 0),
                        "countries": int(s["country_count"] or 0),
                        "eu_contribution": round(float(s["ecMaxContribution"] or 0), 0),
                        "coordinator": {
                            "name": s["coordinator_name"] or "Unknown",
                            "type": s["coordinator_type"] or "Unknown",
                            "country": s["coordinator_country"] or "Unknown",
                        },
                    }
                )

            return {
                "project_count": total_projects,
                "consortium_size": {
                    "min": int(size_stats["min_partners"] or 0),
                    "max": int(size_stats["max_partners"] or 0),
                    "average": round(float(size_stats["avg_partners"] or 0), 1),
                    "median": round(float(size_stats["median_partners"] or 0), 0),
                },
                "geographic_diversity": {
                    "avg_countries": round(float(size_stats["avg_countries"] or 0), 1),
                    "min_countries": int(size_stats["min_countries"] or 0),
                    "max_countries": int(size_stats["max_countries"] or 0),
                },
                "org_type_distribution": org_type_distribution,
                "country_distribution": countries,
                "coordinator_by_type": coord_by_type,
                "coordinator_by_country": coord_by_country,
                "sample_consortia": sample_consortia,
                "source": "postgresql",
            }

        except Exception as e:
            logger.error(f"SQL patterns query failed: {e}")
            return None

    def _merge_pattern_results(
        self, graph_patterns: dict[str, Any] | None, sql_patterns: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Merge pattern results from Graph and SQL."""
        if not graph_patterns and not sql_patterns:
            return self._get_fallback_patterns(None, None)

        if not graph_patterns:
            return self._format_sql_only_results(sql_patterns)

        if not sql_patterns:
            return self._format_graph_only_results(graph_patterns)

        # Both sources available - merge
        # Use SQL for detailed stats, Graph for aggregate patterns
        graph_avg_partners = graph_patterns.get("avg_partners", 0)
        sql_avg_partners = sql_patterns.get("consortium_size", {}).get("average", 0)

        # Weighted average (prefer SQL when keyword filtering is applied)
        avg_partners = (
            (graph_avg_partners * 0.4 + sql_avg_partners * 0.6)
            if sql_avg_partners > 0
            else graph_avg_partners
        )

        return {
            "projects_analyzed": sql_patterns.get(
                "project_count", graph_patterns.get("sample_size", 0)
            ),
            "consortium_size": {
                "min": sql_patterns.get("consortium_size", {}).get("min", 3),
                "max": sql_patterns.get("consortium_size", {}).get("max", 30),
                "average": round(avg_partners, 1),
                "median": sql_patterns.get("consortium_size", {}).get(
                    "median", round(avg_partners)
                ),
                "recommended": f"{max(3, int(avg_partners) - 2)}-{int(avg_partners) + 3} partners",
            },
            "organization_type_distribution": sql_patterns.get("org_type_distribution", {}),
            "country_patterns": {
                "top_participating": sql_patterns.get("country_distribution", [])[:10],
                "geographic_diversity": {
                    "avg_countries": graph_patterns.get(
                        "avg_countries",
                        sql_patterns.get("geographic_diversity", {}).get("avg_countries", 6),
                    ),
                    "min_countries": sql_patterns.get("geographic_diversity", {}).get(
                        "min_countries", 1
                    ),
                    "max_countries": sql_patterns.get("geographic_diversity", {}).get(
                        "max_countries", 20
                    ),
                },
            },
            "coordinator_profile": {
                "by_type": sql_patterns.get("coordinator_by_type", {}),
                "by_country": sql_patterns.get("coordinator_by_country", {}),
                "top_countries_graph": graph_patterns.get("top_coordinator_countries", []),
            },
            "sample_consortia": sql_patterns.get("sample_consortia", []),
            "data_source": "hybrid_graph_sql",
        }

    def _format_sql_only_results(self, sql_patterns: dict[str, Any]) -> dict[str, Any]:
        """Format SQL-only results into standard format."""
        avg_partners = sql_patterns.get("consortium_size", {}).get("average", 10)
        return {
            "projects_analyzed": sql_patterns.get("project_count", 0),
            "consortium_size": {
                "min": sql_patterns.get("consortium_size", {}).get("min", 3),
                "max": sql_patterns.get("consortium_size", {}).get("max", 30),
                "average": avg_partners,
                "median": sql_patterns.get("consortium_size", {}).get("median", avg_partners),
                "recommended": f"{max(3, int(avg_partners) - 2)}-{int(avg_partners) + 3} partners",
            },
            "organization_type_distribution": sql_patterns.get("org_type_distribution", {}),
            "country_patterns": {
                "top_participating": sql_patterns.get("country_distribution", [])[:10],
                "geographic_diversity": sql_patterns.get("geographic_diversity", {}),
            },
            "coordinator_profile": {
                "by_type": sql_patterns.get("coordinator_by_type", {}),
                "by_country": sql_patterns.get("coordinator_by_country", {}),
            },
            "sample_consortia": sql_patterns.get("sample_consortia", []),
            "data_source": "postgresql",
        }

    def _format_graph_only_results(self, graph_patterns: dict[str, Any]) -> dict[str, Any]:
        """Format graph-only results into standard format."""
        avg_partners = graph_patterns.get("avg_partners", 10)
        return {
            "projects_analyzed": graph_patterns.get("sample_size", 0),
            "consortium_size": {
                "average": round(avg_partners, 1),
                "recommended": f"{max(3, int(avg_partners) - 2)}-{int(avg_partners) + 3} partners",
            },
            "country_patterns": {
                "geographic_diversity": {"avg_countries": graph_patterns.get("avg_countries", 6)}
            },
            "coordinator_profile": {
                "top_countries_graph": graph_patterns.get("top_coordinator_countries", [])
            },
            "sample_consortia": [],
            "data_source": "neo4j_graph",
        }

    def _get_successful_templates(
        self, cluster: str, action_type: str | None
    ) -> list[dict[str, Any]] | None:
        """Get successful consortium templates from graph."""
        if not self._graph_service:
            return None

        try:
            examples = self._graph_service.get_project_examples(
                cluster_code=cluster, funding_scheme=action_type, min_budget=1000000, limit=5
            )

            if not examples:
                return None

            templates = []
            for project in examples:
                # Count org types in consortium
                org_types = {}
                countries = set()
                for partner in project.get("partners", []):
                    org_type = partner.get("type", "OTH")
                    org_types[org_type] = org_types.get(org_type, 0) + 1
                    if partner.get("country"):
                        countries.add(partner["country"])

                templates.append(
                    {
                        "project_acronym": project.get("acronym"),
                        "budget": project.get("budget"),
                        "partner_count": project.get("partner_count"),
                        "country_count": project.get("country_count"),
                        "org_type_distribution": org_types,
                        "countries": list(countries)[:10],
                        "source": "neo4j_graph",
                    }
                )

            return templates

        except Exception as e:
            logger.warning(f"Failed to get successful templates: {e}")
            return None

    def _get_coordinator_analysis(
        self, cluster: str, action_type: str | None
    ) -> dict[str, Any] | None:
        """Get coordinator analysis - who coordinates successfully."""
        if not self._graph_service:
            # Fall back to SQL-based analysis
            return self._get_coordinator_analysis_sql(cluster, action_type)

        try:
            top_orgs = self._graph_service.get_top_organizations(cluster_code=cluster, limit=20)

            # Filter to those with coordinations
            coordinators = [o for o in top_orgs if o.get("coordinations", 0) > 0]

            return {
                "cluster": cluster,
                "top_coordinators": coordinators[:10],
                "total_found": len(coordinators),
                "source": "neo4j_graph",
            }

        except Exception as e:
            logger.warning(f"Failed to get coordinator analysis from graph: {e}")
            return self._get_coordinator_analysis_sql(cluster, action_type)

    def _get_coordinator_analysis_sql(
        self, cluster: str, action_type: str | None
    ) -> dict[str, Any] | None:
        """Get coordinator analysis from SQL."""
        try:
            conn = self._get_connection()
            if not conn:
                return None

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            topic_pattern = CLUSTER_TO_TOPIC.get(cluster, cluster)

            where_conditions = [
                "p.\"frameworkProgramme\" = 'HORIZON'",
                "p.topics ILIKE %s",
                "o.role = 'coordinator'",
            ]
            params = [f"%{topic_pattern}%"]

            if action_type:
                where_conditions.append('p."fundingScheme" ILIKE %s')
                params.append(f"%{action_type.upper()}%")

            where_clause = " AND ".join(where_conditions)

            query = f"""
                SELECT
                    o.name,
                    o.country,
                    COALESCE(o."activityType", 'OTH') as entity_type,
                    COUNT(DISTINCT p.id) as coordinations,
                    SUM(p."ecMaxContribution") as total_funding
                FROM projects p
                JOIN organizations o ON p.id = o."projectID"
                WHERE {where_clause}
                GROUP BY o.name, o.country, COALESCE(o."activityType", 'OTH')
                ORDER BY coordinations DESC, total_funding DESC
                LIMIT 15
            """

            cursor.execute(query, params)
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            coordinators = [
                {
                    "name": r["name"],
                    "country": r["country"],
                    "entity_type": r["entity_type"],
                    "coordinations": int(r["coordinations"]),
                    "total_funding": round(float(r["total_funding"] or 0), 0),
                }
                for r in results
            ]

            return {
                "cluster": cluster,
                "top_coordinators": coordinators,
                "total_found": len(coordinators),
                "source": "postgresql",
            }

        except Exception as e:
            logger.error(f"SQL coordinator analysis failed: {e}")
            return None

    def _generate_recommendations(
        self,
        org_dist: dict,
        country_patterns: dict,
        coordinator: dict,
        size_stats: dict,
        action_type: str | None,
        project_count: int,
    ) -> dict[str, Any]:
        """Generate actionable recommendations based on patterns."""

        recommendations = {
            "ideal_composition": [],
            "country_advice": "",
            "coordinator_advice": "",
            "confidence": (
                "high" if project_count >= 20 else "medium" if project_count >= 5 else "low"
            ),
            "notes": [],
        }

        # Calculate ideal composition based on org type distribution
        for org_type, data in sorted(
            org_dist.items(), key=lambda x: x[1].get("percentage", 0), reverse=True
        ):
            avg_count = data.get("avg_per_project", 0)
            if avg_count >= 0.5:
                count_str = f"{max(1, round(avg_count))}"
                if avg_count >= 2:
                    count_str = f"{max(1, round(avg_count) - 1)}-{round(avg_count) + 1}"
                desc = ORG_TYPE_DESCRIPTIONS.get(org_type, org_type)
                recommendations["ideal_composition"].append(f"{count_str} {desc}")

        # Country advice
        geo_diversity = country_patterns.get("geographic_diversity", {})
        avg_countries = geo_diversity.get("avg_countries", 6)
        recommendations["country_advice"] = (
            f"Include partners from {max(3, int(avg_countries) - 2)}-{int(avg_countries) + 2} "
            f"EU member states for good geographic balance"
        )

        # Coordinator advice
        coord_by_type = coordinator.get("by_type", {})
        if coord_by_type:
            top_coord_type = max(coord_by_type.items(), key=lambda x: x[1])[0]
            coord_desc = ORG_TYPE_DESCRIPTIONS.get(top_coord_type, top_coord_type)
            recommendations["coordinator_advice"] = (
                f"{coord_desc} most commonly coordinate these projects"
            )

        # Check for top coordinator countries from graph
        top_countries_graph = coordinator.get("top_countries_graph", [])
        if top_countries_graph:
            recommendations["notes"].append(
                f"Top coordinator countries: {', '.join(top_countries_graph[:5])}"
            )

        # Action-type specific advice
        if action_type:
            at = action_type.upper()
            if at == "RIA":
                recommendations["notes"].append(
                    "RIA projects typically have strong research institution presence"
                )
            elif at == "IA":
                recommendations["notes"].append(
                    "IA projects often have more industry partners for demonstration/deployment"
                )
            elif at == "CSA":
                recommendations["notes"].append(
                    "CSA projects are typically smaller with policy/coordination focus"
                )

        if project_count < 10:
            recommendations["notes"].append(
                f"Based on {project_count} projects - consider broadening criteria for more reliable patterns"
            )

        return recommendations

    def _get_fallback_patterns(
        self, cluster: str | None = None, action_type: str | None = None
    ) -> dict[str, Any]:
        """Return fallback patterns when databases are unavailable."""

        defaults = {
            "RIA": {
                "size": 10,
                "countries": 7,
                "hes_pct": 35,
                "rec_pct": 30,
                "prc_pct": 20,
                "sme_pct": 15,
            },
            "IA": {
                "size": 14,
                "countries": 9,
                "hes_pct": 25,
                "rec_pct": 20,
                "prc_pct": 35,
                "sme_pct": 20,
            },
            "CSA": {
                "size": 8,
                "countries": 6,
                "hes_pct": 30,
                "rec_pct": 25,
                "prc_pct": 25,
                "sme_pct": 20,
            },
        }

        at = (action_type or "RIA").upper()
        pattern = defaults.get(at, defaults["RIA"])

        return {
            "projects_analyzed": "N/A (using typical values)",
            "consortium_size": {
                "typical": pattern["size"],
                "recommended": f"{pattern['size'] - 2}-{pattern['size'] + 3} partners",
            },
            "organization_type_distribution": {
                "HES": {
                    "percentage": pattern["hes_pct"],
                    "description": ORG_TYPE_DESCRIPTIONS["HES"],
                },
                "REC": {
                    "percentage": pattern["rec_pct"],
                    "description": ORG_TYPE_DESCRIPTIONS["REC"],
                },
                "PRC": {
                    "percentage": pattern["prc_pct"],
                    "description": ORG_TYPE_DESCRIPTIONS["PRC"],
                },
                "SME": {
                    "percentage": pattern["sme_pct"],
                    "description": ORG_TYPE_DESCRIPTIONS["SME"],
                },
            },
            "country_patterns": {
                "geographic_diversity": {"typical_countries": pattern["countries"]}
            },
            "recommendations": {
                "ideal_composition": [
                    f"3-4 {ORG_TYPE_DESCRIPTIONS['HES']}",
                    f"2-3 {ORG_TYPE_DESCRIPTIONS['REC']}",
                    f"2-3 {ORG_TYPE_DESCRIPTIONS['PRC']}",
                    f"1-2 {ORG_TYPE_DESCRIPTIONS['SME']}",
                ],
                "country_advice": f"Include partners from {pattern['countries'] - 2}-{pattern['countries'] + 2} EU member states",
                "coordinator_advice": "Universities and research organizations coordinate most successfully",
                "confidence": "low",
                "notes": ["Using typical values - database unavailable for specific statistics"],
            },
            "sample_consortia": [],
            "data_source": "fallback_estimates",
        }


# Default country groups for geographic diversification analysis
DEFAULT_COUNTRY_GROUPS = {
    "Nordic": ["NO", "DK", "SE", "FI"],
    "South Europe": ["ES", "PT", "IT", "GR"],
    "Western Europe": ["FR", "DE", "BE", "NL", "LU"],  # BENELUX = BE, NL, LU
    "Baltic": ["EE", "LV", "LT"],
    "CEE": ["PL", "SK", "CZ", "HU", "SI"],  # Central and Eastern Europe
    "Western Balkans": ["HR", "RS", "ME"],
    "EPC": ["MD", "BY", "UA", "GE", "AM", "AZ"],  # Eastern Partnership Countries
    "Islands": ["IE", "UK", "MT", "CY"],
}


class GeographicDiversificationTool:
    """
    Tool to analyze geographic diversification of country partners in consortia.

    Supports custom country group definitions and calculates:
    - Share of projects with partners from each group
    - Coverage statistics (projects with 5/6/7/8+ groups)
    - Group representation patterns
    """

    def __init__(self):
        """Initialize with database connection."""
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.warning("DATABASE_URL not set - geographic diversification limited")

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _normalize_cluster(self, cluster: str) -> str:
        """Normalize cluster code."""
        if not cluster:
            return None
        cluster_upper = cluster.upper().replace(" ", "").replace("-", "")
        return CLUSTER_MAP.get(cluster_upper, cluster.upper())

    def analyze_geographic_diversification(
        self,
        cluster: str | None = None,
        country_groups: dict[str, list[str]] | None = None,
        exclude_widening: bool = True,
        min_partners: int = 3,
    ) -> dict[str, Any]:
        """
        Analyze geographic diversification of country partners.

        Args:
            cluster: Cluster code (e.g., "CL2", "CLUSTER-2")
            country_groups: Custom country group definitions (default: European regions)
            exclude_widening: Whether to exclude Widening calls (default: True)
            min_partners: Minimum partners for consortium to be included (default: 3)

        Returns:
            Geographic diversification analysis with coverage statistics
        """
        # Use default groups if not provided
        groups = country_groups or DEFAULT_COUNTRY_GROUPS

        # Normalize cluster
        normalized_cluster = self._normalize_cluster(cluster)

        try:
            conn = self._get_connection()
            if not conn:
                return self._get_fallback_diversification(groups)

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build WHERE conditions
            where_conditions = ["p.\"frameworkProgramme\" = 'HORIZON'"]
            params = []

            # Cluster filter
            if normalized_cluster:
                topic_pattern = CLUSTER_TO_TOPIC.get(normalized_cluster, normalized_cluster)
                where_conditions.append("p.topics ILIKE %s")
                params.append(f"%{topic_pattern}%")

            # Exclude Widening calls
            if exclude_widening:
                where_conditions.append("p.topics NOT ILIKE '%%WIDERA%%'")

            where_clause = " AND ".join(where_conditions)

            # Step 1: Get all projects with their partner countries
            projects_sql = f"""
                WITH project_countries AS (
                    SELECT
                        p.id as project_id,
                        p.acronym,
                        p.title,
                        ARRAY_AGG(DISTINCT o.country) as countries,
                        COUNT(DISTINCT o."organisationID") as partner_count
                    FROM projects p
                    JOIN organizations o ON p.id = o."projectID"
                    WHERE {where_clause}
                      AND o.country IS NOT NULL
                    GROUP BY p.id, p.acronym, p.title
                    HAVING COUNT(DISTINCT o."organisationID") >= %s
                )
                SELECT * FROM project_countries
            """
            cursor.execute(projects_sql, params + [min_partners])
            projects = cursor.fetchall()

            if not projects:
                cursor.close()
                conn.close()
                return {
                    "success": False,
                    "error": "No projects found matching criteria",
                    "query_params": {
                        "cluster": normalized_cluster,
                        "exclude_widening": exclude_widening,
                    },
                }

            total_projects = len(projects)

            # Step 2: Analyze each project's country group coverage
            group_presence = {group: 0 for group in groups.keys()}
            coverage_counts = {
                "all_groups": 0,
                "7_groups": 0,
                "6_groups": 0,
                "5_groups": 0,
                "4_groups": 0,
                "3_or_fewer": 0,
            }

            # Create reverse mapping: country -> group
            country_to_group = {}
            for group_name, countries in groups.items():
                for country in countries:
                    country_to_group[country] = group_name

            for project in projects:
                project_countries = project["countries"] or []
                groups_in_project = set()

                for country in project_countries:
                    if country in country_to_group:
                        groups_in_project.add(country_to_group[country])

                # Count group presence
                for group in groups_in_project:
                    group_presence[group] += 1

                # Count coverage
                num_groups = len(groups_in_project)
                total_group_count = len(groups)

                if num_groups >= total_group_count:
                    coverage_counts["all_groups"] += 1
                elif num_groups >= 7:
                    coverage_counts["7_groups"] += 1
                elif num_groups == 6:
                    coverage_counts["6_groups"] += 1
                elif num_groups == 5:
                    coverage_counts["5_groups"] += 1
                elif num_groups == 4:
                    coverage_counts["4_groups"] += 1
                else:
                    coverage_counts["3_or_fewer"] += 1

            cursor.close()
            conn.close()

            # Calculate percentages
            group_statistics = []
            for group_name, count in sorted(
                group_presence.items(), key=lambda x: x[1], reverse=True
            ):
                group_statistics.append(
                    {
                        "group": group_name,
                        "countries": groups[group_name],
                        "projects_with_partner": count,
                        "share_percentage": round(100.0 * count / total_projects, 1),
                    }
                )

            coverage_statistics = {
                f"all_{len(groups)}_groups": {
                    "count": coverage_counts["all_groups"],
                    "share_percentage": round(
                        100.0 * coverage_counts["all_groups"] / total_projects, 1
                    ),
                },
                "7_groups": {
                    "count": coverage_counts["7_groups"],
                    "share_percentage": round(
                        100.0 * coverage_counts["7_groups"] / total_projects, 1
                    ),
                },
                "6_groups": {
                    "count": coverage_counts["6_groups"],
                    "share_percentage": round(
                        100.0 * coverage_counts["6_groups"] / total_projects, 1
                    ),
                },
                "5_groups": {
                    "count": coverage_counts["5_groups"],
                    "share_percentage": round(
                        100.0 * coverage_counts["5_groups"] / total_projects, 1
                    ),
                },
                "4_groups": {
                    "count": coverage_counts["4_groups"],
                    "share_percentage": round(
                        100.0 * coverage_counts["4_groups"] / total_projects, 1
                    ),
                },
                "3_or_fewer_groups": {
                    "count": coverage_counts["3_or_fewer"],
                    "share_percentage": round(
                        100.0 * coverage_counts["3_or_fewer"] / total_projects, 1
                    ),
                },
            }

            # Calculate cumulative "at least N groups"
            at_least_stats = {
                "at_least_7_groups": {
                    "count": coverage_counts["all_groups"] + coverage_counts["7_groups"],
                    "share_percentage": round(
                        100.0
                        * (coverage_counts["all_groups"] + coverage_counts["7_groups"])
                        / total_projects,
                        1,
                    ),
                },
                "at_least_6_groups": {
                    "count": (
                        coverage_counts["all_groups"]
                        + coverage_counts["7_groups"]
                        + coverage_counts["6_groups"]
                    ),
                    "share_percentage": round(
                        100.0
                        * (
                            coverage_counts["all_groups"]
                            + coverage_counts["7_groups"]
                            + coverage_counts["6_groups"]
                        )
                        / total_projects,
                        1,
                    ),
                },
                "at_least_5_groups": {
                    "count": (
                        coverage_counts["all_groups"]
                        + coverage_counts["7_groups"]
                        + coverage_counts["6_groups"]
                        + coverage_counts["5_groups"]
                    ),
                    "share_percentage": round(
                        100.0
                        * (
                            coverage_counts["all_groups"]
                            + coverage_counts["7_groups"]
                            + coverage_counts["6_groups"]
                            + coverage_counts["5_groups"]
                        )
                        / total_projects,
                        1,
                    ),
                },
            }

            # Identify underrepresented and well-represented groups
            avg_share = sum(g["share_percentage"] for g in group_statistics) / len(groups)
            underrepresented = [
                g for g in group_statistics if g["share_percentage"] < avg_share * 0.5
            ]
            well_represented = [
                g for g in group_statistics if g["share_percentage"] > avg_share * 1.5
            ]

            return {
                "success": True,
                "tool_name": "analyze_geographic_diversification",
                "query_params": {
                    "cluster": normalized_cluster,
                    "exclude_widening": exclude_widening,
                    "min_partners": min_partners,
                    "country_groups_defined": len(groups),
                },
                "total_projects_analyzed": total_projects,
                "country_groups": groups,
                "group_representation": group_statistics,
                "coverage_statistics": coverage_statistics,
                "at_least_coverage": at_least_stats,
                "insights": {
                    "typical_coverage": (
                        "5-6 groups"
                        if (coverage_counts["5_groups"] + coverage_counts["6_groups"])
                        / total_projects
                        > 0.4
                        else "4-5 groups"
                    ),
                    "well_represented_groups": [g["group"] for g in well_represented],
                    "underrepresented_groups": [g["group"] for g in underrepresented],
                    "avg_group_presence": round(avg_share, 1),
                },
                "recommendations": {
                    "consortium_building": (
                        "Most projects cover 5-6 country groups. "
                        f"To maximize diversity, include partners from underrepresented groups: "
                        f"{', '.join([g['group'] for g in underrepresented[:3]])}."
                        if underrepresented
                        else "Geographic diversification is relatively balanced across groups."
                    ),
                    "evaluation_note": (
                        "Geographic diversity is positively evaluated in Horizon Europe. "
                        "Wider geographic coverage demonstrates broader European impact."
                    ),
                },
                "metadata": {
                    "data_source": "postgresql",
                    "widening_excluded": exclude_widening,
                    "timestamp": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Geographic diversification analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query_params": {
                    "cluster": normalized_cluster,
                    "exclude_widening": exclude_widening,
                },
            }

    def _get_fallback_diversification(self, groups: dict[str, list[str]]) -> dict[str, Any]:
        """Return fallback diversification data when database unavailable."""
        # Estimated typical values based on EU funding patterns
        return {
            "success": True,
            "tool_name": "analyze_geographic_diversification",
            "total_projects_analyzed": "N/A (using estimates)",
            "country_groups": groups,
            "group_representation": [
                {"group": "Western Europe", "share_percentage": 90, "note": "estimate"},
                {"group": "South Europe", "share_percentage": 85, "note": "estimate"},
                {"group": "Nordic", "share_percentage": 55, "note": "estimate"},
                {"group": "CEE", "share_percentage": 45, "note": "estimate"},
                {"group": "Baltic", "share_percentage": 30, "note": "estimate"},
                {"group": "Islands", "share_percentage": 25, "note": "estimate"},
                {"group": "Western Balkans", "share_percentage": 15, "note": "estimate"},
                {"group": "EPC", "share_percentage": 8, "note": "estimate"},
            ],
            "coverage_statistics": {
                "all_8_groups": {"share_percentage": 5, "note": "estimate"},
                "7_groups": {"share_percentage": 12, "note": "estimate"},
                "6_groups": {"share_percentage": 22, "note": "estimate"},
                "5_groups": {"share_percentage": 28, "note": "estimate"},
            },
            "at_least_coverage": {
                "at_least_7_groups": {"share_percentage": 17, "note": "estimate"},
                "at_least_6_groups": {"share_percentage": 39, "note": "estimate"},
                "at_least_5_groups": {"share_percentage": 67, "note": "estimate"},
            },
            "metadata": {
                "data_source": "fallback_estimates",
                "note": "Actual data unavailable - using typical EU funding patterns",
            },
        }


# Async wrapper for geographic diversification tool
async def analyze_geographic_diversification_execute(
    params: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    """
    Execute geographic diversification analysis tool.

    This tool analyzes the geographic diversification of consortium partners
    by custom-defined country groups. Use it when users ask about:
    - Country group representation in consortia
    - Geographic diversity patterns (Nordic, South Europe, CEE, etc.)
    - Share of projects with partners from specific country groups
    - Coverage statistics (projects with N+ country groups)
    """
    # Extract cluster with fallback alternatives
    cluster_param = params.get("cluster") or params.get("cluster_code") or params.get("cluster_id")

    # Extract country groups (use default if not provided)
    country_groups = params.get("country_groups")

    tool = GeographicDiversificationTool()

    return tool.analyze_geographic_diversification(
        cluster=cluster_param,
        country_groups=country_groups,
        exclude_widening=params.get("exclude_widening", True),
        min_partners=params.get("min_partners", 3),
    )


# Async wrapper for tool orchestrator compatibility
async def get_consortium_patterns_execute(
    params: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    """
    Execute consortium patterns tool.

    This tool analyzes consortium composition patterns from funded Horizon Europe projects.
    Use it when users ask about typical consortium composition, partner types, country
    distribution, or coordinator profiles for specific domains.

    HYBRID ARCHITECTURE: Combines Neo4j graph patterns with PostgreSQL for detailed analysis.
    """
    # Extract cluster with fallback alternatives (LLM might use different parameter names)
    cluster_param = (
        params.get("cluster")
        or params.get("cluster_code")
        or params.get("cluster_id")
        or params.get("pillar")
    )

    tool = ConsortiumPatternsTool()

    return tool.get_patterns(
        cluster=cluster_param,
        action_type=params.get("action_type"),
        topic_keywords=params.get("topic_keywords"),
        min_projects=params.get("min_projects", 10),
        include_successful_templates=params.get("include_successful_templates", True),
        include_coordinator_analysis=params.get("include_coordinator_analysis", True),
    )
