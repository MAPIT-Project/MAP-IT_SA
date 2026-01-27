"""
Timeline Generator Tool for Horizon Europe Proposals.

ENHANCED with Hybrid Graph+SQL Architecture:
- Uses Neo4j graph database for real project duration patterns
- Uses PostgreSQL for project examples and duration statistics
- Parallel query execution for performance
- Cluster inference from keywords
- Real-data grounded duration and WP recommendations

Generates realistic project timelines with work packages, deliverables,
and milestones based on best practices from funded projects.
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

# Cluster code normalization
CLUSTER_MAP = {
    'CL1': 'CLUSTER-1', 'CLUSTER1': 'CLUSTER-1', 'CLUSTER-1': 'CLUSTER-1', 'HEALTH': 'CLUSTER-1',
    'CL2': 'CLUSTER-2', 'CLUSTER2': 'CLUSTER-2', 'CLUSTER-2': 'CLUSTER-2', 'CULTURE': 'CLUSTER-2',
    'CL3': 'CLUSTER-3', 'CLUSTER3': 'CLUSTER-3', 'CLUSTER-3': 'CLUSTER-3', 'SECURITY': 'CLUSTER-3',
    'CL4': 'CLUSTER-4', 'CLUSTER4': 'CLUSTER-4', 'CLUSTER-4': 'CLUSTER-4', 'DIGITAL': 'CLUSTER-4',
    'CL5': 'CLUSTER-5', 'CLUSTER5': 'CLUSTER-5', 'CLUSTER-5': 'CLUSTER-5', 'CLIMATE': 'CLUSTER-5',
    'CL6': 'CLUSTER-6', 'CLUSTER6': 'CLUSTER-6', 'CLUSTER-6': 'CLUSTER-6', 'FOOD': 'CLUSTER-6',
}

# Cluster-specific WP customizations
CLUSTER_WP_CUSTOMIZATIONS = {
    'CLUSTER-1': {  # Health
        'research': {'title': 'Clinical Research & Development', 'additional_deliverables': ['Clinical Protocol', 'Ethical Approval Report']},
        'validation': {'title': 'Clinical Validation & Trials', 'additional_deliverables': ['Trial Results Report']},
    },
    'CLUSTER-4': {  # Digital
        'research': {'title': 'AI/ML Model Development', 'additional_deliverables': ['Model Architecture Report', 'Training Dataset']},
        'validation': {'title': 'System Integration & Testing', 'additional_deliverables': ['Integration Test Report']},
    },
    'CLUSTER-5': {  # Climate/Energy
        'research': {'title': 'Technology Development & Optimization', 'additional_deliverables': ['Technical Specifications']},
        'pilot': {'title': 'Pilot Demonstration & Scale-up', 'additional_deliverables': ['Pilot Site Selection Report', 'Scale-up Strategy']},
    },
    'CLUSTER-6': {  # Food/Bio
        'research': {'title': 'Bio-based Development', 'additional_deliverables': ['Life Cycle Assessment']},
        'pilot': {'title': 'Field Trials & Demonstration', 'additional_deliverables': ['Field Trial Protocol', 'Environmental Impact Assessment']},
    },
}


class TimelineGeneratorTool:
    """
    Generate project timelines based on Horizon Europe best practices.

    ENHANCED with Hybrid Graph+SQL Architecture:
    - Graph service (Neo4j) for real project duration patterns
    - SQL service (PostgreSQL) for project examples and statistics
    - Parallel query execution for performance
    - Cluster inference from keywords
    """

    # Typical WP structure by action type (enhanced with descriptions and tasks)
    WP_TEMPLATES = {
        'RIA': [
            {
                'title': 'Project Management',
                'effort_pct': 0.08,
                'full_duration': True,
                'type': 'management',
                'objective': 'Ensure efficient coordination, quality management, and timely delivery of project outcomes.',
                'tasks': ['Overall project coordination and monitoring', 'Quality assurance and risk management', 'Financial management and reporting', 'Consortium communication and meetings']
            },
            {
                'title': 'Requirements & State of the Art',
                'effort_pct': 0.12,
                'months': (1, 12),
                'type': 'requirements',
                'objective': 'Establish comprehensive requirements and analyze existing solutions and knowledge gaps.',
                'tasks': ['User and stakeholder requirements analysis', 'State-of-the-art review and gap analysis', 'Technical specifications development', 'Use case definition and validation scenarios']
            },
            {
                'title': 'Core Research & Development',
                'effort_pct': 0.35,
                'months': (6, -6),
                'type': 'research',
                'objective': 'Conduct core research activities and develop innovative solutions addressing project objectives.',
                'tasks': ['Novel methodology/algorithm development', 'Prototype implementation', 'Component development and testing', 'Technical documentation']
            },
            {
                'title': 'Integration & Validation',
                'effort_pct': 0.20,
                'months': (12, -3),
                'type': 'validation',
                'objective': 'Integrate developed components and validate against requirements through comprehensive testing.',
                'tasks': ['System integration and configuration', 'Validation against requirements', 'User acceptance testing', 'Performance benchmarking']
            },
            {
                'title': 'Dissemination & Exploitation',
                'effort_pct': 0.15,
                'full_duration': True,
                'type': 'dissemination',
                'objective': 'Maximize project impact through effective dissemination, communication, and exploitation activities.',
                'tasks': ['Publication and conference activities', 'Stakeholder engagement and workshops', 'Exploitation planning and market analysis', 'Standardization activities']
            },
            {
                'title': 'Ethics & Data Management',
                'effort_pct': 0.10,
                'full_duration': True,
                'type': 'ethics',
                'objective': 'Ensure ethical compliance and responsible data management throughout the project lifecycle.',
                'tasks': ['Ethics requirements implementation', 'Data management plan maintenance', 'GDPR compliance and data protection', 'Open science and FAIR data practices']
            },
        ],
        'IA': [
            {
                'title': 'Project Management',
                'effort_pct': 0.08,
                'full_duration': True,
                'type': 'management',
                'objective': 'Coordinate project activities and ensure delivery of innovation objectives on time and budget.',
                'tasks': ['Project coordination and governance', 'Quality and risk management', 'Financial management', 'IP and innovation management']
            },
            {
                'title': 'Market Analysis & Requirements',
                'effort_pct': 0.10,
                'months': (1, 9),
                'type': 'requirements',
                'objective': 'Understand market needs and define requirements for commercially viable solutions.',
                'tasks': ['Market analysis and competitive assessment', 'Customer requirements gathering', 'Business requirements specification', 'Regulatory requirements analysis']
            },
            {
                'title': 'Technology Development',
                'effort_pct': 0.30,
                'months': (3, -9),
                'type': 'research',
                'objective': 'Develop and optimize technology for deployment at higher TRL levels.',
                'tasks': ['Technology adaptation and optimization', 'Prototype development and testing', 'Manufacturing process development', 'Technical documentation']
            },
            {
                'title': 'Pilot Deployment',
                'effort_pct': 0.25,
                'months': (12, -6),
                'type': 'pilot',
                'objective': 'Deploy and validate solutions in real-world operational environments.',
                'tasks': ['Pilot site preparation and setup', 'System deployment and configuration', 'Operational testing and monitoring', 'Performance evaluation and optimization']
            },
            {
                'title': 'Business Model & Scale-up',
                'effort_pct': 0.12,
                'months': (18, -3),
                'type': 'business',
                'objective': 'Develop sustainable business models and prepare for market scale-up.',
                'tasks': ['Business model development and validation', 'Go-to-market strategy', 'Investment and funding roadmap', 'Scale-up planning']
            },
            {
                'title': 'Dissemination & Exploitation',
                'effort_pct': 0.15,
                'full_duration': True,
                'type': 'dissemination',
                'objective': 'Maximize commercial and societal impact through targeted dissemination and exploitation.',
                'tasks': ['Industry engagement and demonstrations', 'Exploitation planning and IP strategy', 'Standards and policy engagement', 'Communication activities']
            },
        ],
        'CSA': [
            {
                'title': 'Project Management',
                'effort_pct': 0.10,
                'full_duration': True,
                'type': 'management',
                'objective': 'Coordinate support and coordination activities effectively.',
                'tasks': ['Project coordination', 'Quality management', 'Administrative and financial management', 'Reporting']
            },
            {
                'title': 'Stakeholder Engagement',
                'effort_pct': 0.25,
                'full_duration': True,
                'type': 'communication',
                'objective': 'Build and maintain strong stakeholder networks and communities.',
                'tasks': ['Stakeholder mapping and engagement', 'Community building activities', 'Event organization', 'Network facilitation']
            },
            {
                'title': 'Analysis & Best Practices',
                'effort_pct': 0.25,
                'months': (1, 18),
                'type': 'research',
                'objective': 'Conduct analysis and identify best practices to inform recommendations.',
                'tasks': ['Data collection and analysis', 'Best practice identification', 'Comparative studies', 'Documentation and synthesis']
            },
            {
                'title': 'Policy Recommendations',
                'effort_pct': 0.20,
                'months': (12, -3),
                'type': 'validation',
                'objective': 'Develop actionable recommendations for policy and practice.',
                'tasks': ['Policy analysis', 'Recommendation development', 'Consultation and validation', 'Roadmap development']
            },
            {
                'title': 'Communication & Outreach',
                'effort_pct': 0.20,
                'full_duration': True,
                'type': 'dissemination',
                'objective': 'Ensure wide dissemination and uptake of project outputs.',
                'tasks': ['Communication strategy implementation', 'Publication and dissemination', 'Training and capacity building', 'Impact assessment']
            },
        ],
        'ERC': [
            {
                'title': 'Research Direction 1',
                'effort_pct': 0.35,
                'full_duration': True,
                'type': 'research',
                'objective': 'Pursue primary research direction with groundbreaking scientific inquiry.',
                'tasks': ['Fundamental research activities', 'Data collection and analysis', 'Theory development', 'Publication preparation']
            },
            {
                'title': 'Research Direction 2',
                'effort_pct': 0.30,
                'full_duration': True,
                'type': 'research',
                'objective': 'Explore complementary research direction expanding project scope.',
                'tasks': ['Secondary research activities', 'Cross-disciplinary exploration', 'Methodology development', 'Knowledge synthesis']
            },
            {
                'title': 'Cross-cutting Activities',
                'effort_pct': 0.20,
                'full_duration': True,
                'type': 'research',
                'objective': 'Address cross-cutting themes and integrate research directions.',
                'tasks': ['Integration activities', 'Collaboration with external partners', 'Training and supervision', 'Scientific outreach']
            },
            {
                'title': 'Scientific Coordination',
                'effort_pct': 0.15,
                'full_duration': True,
                'type': 'management',
                'objective': 'Ensure scientific coherence and effective resource management.',
                'tasks': ['Research coordination', 'Team management', 'Resource allocation', 'Scientific reporting']
            },
        ],
    }

    # Deliverable types
    DELIVERABLE_TYPES = {
        'R': 'Document, report',
        'DEM': 'Demonstrator, pilot, prototype',
        'DEC': 'Websites, patents, press releases',
        'DATA': 'Data sets, microdata, etc.',
        'DMP': 'Data management plan',
        'ETHICS': 'Ethics deliverables',
        'OTHER': 'Software, technical diagram, etc.',
    }

    # Dissemination levels
    DISSEMINATION_LEVELS = {
        'PU': 'Public',
        'SEN': 'Sensitive',
        'CO': 'Confidential',
    }

    def __init__(self):
        """Initialize with database connection and graph service."""
        self.db_url = os.getenv("DATABASE_URL")

        # Initialize graph service with graceful fallback
        self._graph_service = None
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            self._graph_service = GraphSearchService()
            logger.info("✅ Graph service available for timeline generator")
        except Exception as e:
            logger.warning(f"⚠️ Graph service not available for timeline generator: {e}")

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _normalize_cluster_code(self, cluster: str | None) -> str | None:
        """Normalize cluster code to CLUSTER-N format."""
        if not cluster:
            return None
        cluster_upper = cluster.upper().replace(' ', '').replace('-', '')
        if cluster_upper.startswith('CL') and len(cluster_upper) == 3:
            cluster_upper = f"CLUSTER{cluster_upper[2]}"
        return CLUSTER_MAP.get(cluster_upper, cluster.upper() if cluster.upper().startswith('CLUSTER-') else None)

    def _infer_clusters_from_keywords(self, keywords: str) -> list[str]:
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

    def generate_timeline(
        self,
        action_type: str,
        duration_months: int,
        num_partners: int,
        total_person_months: int,
        project_title: str = "Project",
        custom_wps: list[dict] | None = None,
        start_date: str | None = None,
        cluster: str | None = None,
        topic_keywords: str | None = None,
        use_real_patterns: bool = True,
        include_similar_projects: bool = True
    ) -> dict[str, Any]:
        """
        Generate a project timeline with work packages, deliverables, and milestones.

        ENHANCED with Hybrid Graph+SQL Architecture:
        - Uses graph database for real project duration patterns
        - Uses SQL for project examples and statistics
        - Cluster inference from keywords
        - Cluster-specific WP customizations

        Args:
            action_type: RIA, IA, CSA, ERC
            duration_months: Total project duration
            num_partners: Number of partners
            total_person_months: Total effort in PMs
            project_title: Project title for naming
            custom_wps: Optional custom WP definitions
            start_date: Optional start date (YYYY-MM-DD)
            cluster: Cluster code for context (e.g., "CL5", "CLUSTER-5")
            topic_keywords: Keywords for cluster inference
            use_real_patterns: Use real project patterns from graph (default: True)
            include_similar_projects: Include similar project examples (default: True)

        Returns:
            Complete timeline with WPs, deliverables, milestones, Gantt data
        """
        action_type = action_type.upper()
        if action_type.startswith('ERC'):
            action_type = 'ERC'

        # Normalize cluster or infer from keywords
        normalized_cluster = self._normalize_cluster_code(cluster)
        inferred_clusters = []
        if not normalized_cluster and topic_keywords:
            inferred_clusters = self._infer_clusters_from_keywords(topic_keywords)
            if inferred_clusters:
                normalized_cluster = inferred_clusters[0]
                logger.info(f"Inferred cluster from keywords: {normalized_cluster}")

        # Use hybrid approach if graph service available and real patterns requested
        if self._graph_service and use_real_patterns:
            return self._generate_timeline_hybrid(
                action_type=action_type,
                duration_months=duration_months,
                num_partners=num_partners,
                total_person_months=total_person_months,
                project_title=project_title,
                custom_wps=custom_wps,
                start_date=start_date,
                cluster=normalized_cluster,
                inferred_clusters=inferred_clusters,
                include_similar_projects=include_similar_projects
            )

        # Fallback to template-based generation
        return self._generate_timeline_template(
            action_type=action_type,
            duration_months=duration_months,
            num_partners=num_partners,
            total_person_months=total_person_months,
            project_title=project_title,
            custom_wps=custom_wps,
            start_date=start_date,
            cluster=normalized_cluster
        )

    def _generate_timeline_hybrid(
        self,
        action_type: str,
        duration_months: int,
        num_partners: int,
        total_person_months: int,
        project_title: str,
        custom_wps: list[dict] | None,
        start_date: str | None,
        cluster: str | None,
        inferred_clusters: list[str],
        include_similar_projects: bool
    ) -> dict[str, Any]:
        """
        Hybrid Graph+SQL timeline generation with real project patterns.
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
                    futures['graph_duration_stats'] = executor.submit(
                        self._get_graph_duration_statistics,
                        cluster, action_type
                    )

                    futures['graph_examples'] = executor.submit(
                        self._get_graph_project_examples,
                        cluster, action_type
                    )

            # SQL queries
            futures['sql_duration_stats'] = executor.submit(
                self._get_sql_duration_statistics,
                action_type, cluster
            )

            if include_similar_projects:
                futures['sql_examples'] = executor.submit(
                    self._get_sql_project_examples,
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

        # Generate timeline with enhanced data
        return self._generate_with_real_patterns(
            results=results,
            action_type=action_type,
            duration_months=duration_months,
            num_partners=num_partners,
            total_person_months=total_person_months,
            project_title=project_title,
            custom_wps=custom_wps,
            start_date=start_date,
            cluster=cluster,
            inferred_clusters=inferred_clusters,
            include_similar_projects=include_similar_projects
        )

    def _get_graph_duration_statistics(
        self,
        cluster: str,
        action_type: str | None
    ) -> dict | None:
        """Get duration statistics from graph database."""
        if not self._graph_service:
            return None

        try:
            # Get project examples with duration info
            stats = self._graph_service.get_budget_statistics(
                cluster_code=cluster,
                action_type=action_type
            )
            if stats and len(stats) > 0:
                return stats[0] if isinstance(stats, list) else stats
            return None
        except Exception as e:
            logger.warning(f"Graph duration statistics query failed: {e}")
            return None

    def _get_graph_project_examples(
        self,
        cluster: str,
        action_type: str | None
    ) -> list[dict] | None:
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

    def _get_sql_duration_statistics(
        self,
        action_type: str,
        cluster: str | None
    ) -> dict | None:
        """Get duration statistics from SQL database."""
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                scheme_pattern = f"%{action_type.replace('-', '%')}%"
                params = [scheme_pattern]

                cluster_filter = ""
                if cluster:
                    cl_code = cluster.replace('CLUSTER-', 'CL')
                    cluster_filter = "AND topics ILIKE %s"
                    params.append(f"%{cl_code}%")

                cursor.execute(f"""
                    SELECT
                        AVG(EXTRACT(YEAR FROM age("endDate", "startDate")) * 12 +
                            EXTRACT(MONTH FROM age("endDate", "startDate"))) as avg_duration,
                        MIN(EXTRACT(YEAR FROM age("endDate", "startDate")) * 12 +
                            EXTRACT(MONTH FROM age("endDate", "startDate"))) as min_duration,
                        MAX(EXTRACT(YEAR FROM age("endDate", "startDate")) * 12 +
                            EXTRACT(MONTH FROM age("endDate", "startDate"))) as max_duration,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (
                            ORDER BY EXTRACT(YEAR FROM age("endDate", "startDate")) * 12 +
                                     EXTRACT(MONTH FROM age("endDate", "startDate"))
                        ) as median_duration,
                        COUNT(*) as project_count
                    FROM projects
                    WHERE "frameworkProgramme" = 'HORIZON'
                      AND "fundingScheme" ILIKE %s
                      AND "startDate" IS NOT NULL
                      AND "endDate" IS NOT NULL
                      AND "endDate" > "startDate"
                      {cluster_filter}
                """, params)

                row = cursor.fetchone()
                cursor.close()
                conn.close()

                if row and row['avg_duration'] and row['project_count'] > 5:
                    return {
                        'avg_duration': float(row['avg_duration']),
                        'min_duration': float(row['min_duration']) if row['min_duration'] else None,
                        'max_duration': float(row['max_duration']) if row['max_duration'] else None,
                        'median_duration': float(row['median_duration']) if row['median_duration'] else None,
                        'project_count': int(row['project_count']),
                        'source': 'sql'
                    }
        except Exception as e:
            logger.warning(f"SQL duration statistics query failed: {e}")

        return None

    def _get_sql_project_examples(
        self,
        action_type: str,
        cluster: str | None
    ) -> list[dict] | None:
        """Get project examples from SQL database."""
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                scheme_pattern = f"%{action_type.replace('-', '%')}%"
                params = [scheme_pattern]

                cluster_filter = ""
                if cluster:
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
                        "startDate" as start_date,
                        "endDate" as end_date,
                        EXTRACT(YEAR FROM age("endDate", "startDate")) * 12 +
                        EXTRACT(MONTH FROM age("endDate", "startDate")) as duration_months
                    FROM projects
                    WHERE "frameworkProgramme" = 'HORIZON'
                      AND "fundingScheme" ILIKE %s
                      AND "ecMaxContribution" > 500000
                      AND "startDate" IS NOT NULL
                      AND "endDate" IS NOT NULL
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
                        'duration_months': int(r['duration_months']) if r['duration_months'] else None,
                        'start_date': str(r['start_date'])[:10] if r['start_date'] else None,
                        'end_date': str(r['end_date'])[:10] if r['end_date'] else None
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.warning(f"SQL project examples query failed: {e}")

        return None

    def _generate_with_real_patterns(
        self,
        results: dict[str, Any],
        action_type: str,
        duration_months: int,
        num_partners: int,
        total_person_months: int,
        project_title: str,
        custom_wps: list[dict] | None,
        start_date: str | None,
        cluster: str | None,
        inferred_clusters: list[str],
        include_similar_projects: bool
    ) -> dict[str, Any]:
        """Generate timeline with real project patterns from graph and SQL."""

        # Get duration statistics
        graph_stats = results['graph'].get('duration_stats')
        sql_stats = results['sql'].get('duration_stats')

        # Merge duration statistics
        duration_context = None
        if graph_stats or sql_stats:
            avg_duration = None
            if graph_stats and graph_stats.get('avg_duration'):
                avg_duration = graph_stats.get('avg_duration')
            elif sql_stats and sql_stats.get('avg_duration'):
                avg_duration = sql_stats['avg_duration']

            if avg_duration:
                duration_context = {
                    'avg_duration': round(avg_duration, 0),
                    'median_duration': round(sql_stats.get('median_duration', avg_duration), 0) if sql_stats else round(avg_duration, 0),
                    'typical_range': f"{int(sql_stats.get('min_duration', avg_duration * 0.7))}-{int(sql_stats.get('max_duration', avg_duration * 1.3))} months" if sql_stats else None,
                    'project_count': sql_stats.get('project_count', 0) if sql_stats else 0,
                    'your_duration_vs_typical': self._compare_duration(duration_months, avg_duration)
                }

        # Get WP templates (customized for cluster if available)
        templates = custom_wps or self._get_cluster_customized_templates(action_type, cluster)

        # Generate timeline using templates
        work_packages = []
        all_deliverables = []
        all_milestones = []
        deliverable_counter = 1
        milestone_counter = 1

        for i, template in enumerate(templates, 1):
            # Calculate WP timing
            if template.get('full_duration'):
                start_month = 1
                end_month = duration_months
            else:
                months = template.get('months', (1, duration_months))
                start_month = months[0]
                end_month = duration_months + months[1] if months[1] < 0 else months[1]
                end_month = min(end_month, duration_months)

            # Calculate effort
            effort = int(total_person_months * template['effort_pct'])

            # Generate deliverables (with cluster-specific additions)
            wp_deliverables, deliverable_counter = self._generate_deliverables(
                wp_num=i,
                wp_title=template['title'],
                start_month=start_month,
                end_month=end_month,
                action_type=action_type,
                counter_start=deliverable_counter,
                cluster=cluster,
                wp_type=template.get('type')
            )

            # Generate milestones
            wp_milestones, milestone_counter = self._generate_milestones(
                wp_num=i,
                wp_title=template['title'],
                start_month=start_month,
                end_month=end_month,
                counter_start=milestone_counter
            )

            # Assign partners to WP (distribute leadership across partners)
            lead_partner_idx = ((i - 1) % num_partners) + 1
            # Calculate participant partners (all others involved proportionally)
            participant_partners = [
                f'P{p}' for p in range(1, num_partners + 1) if p != lead_partner_idx
            ][:min(4, num_partners - 1)]  # Max 4 participants listed

            wp = {
                'number': i,
                'title': template['title'],
                'objective': template.get('objective', ''),
                'lead': f'P{lead_partner_idx}',
                'lead_partner': f'Partner {lead_partner_idx}',
                'participants': participant_partners,
                'start_month': start_month,
                'end_month': end_month,
                'duration_months': end_month - start_month + 1,
                'effort_pms': effort,
                'effort_percentage': round(template['effort_pct'] * 100, 1),
                'tasks': template.get('tasks', []),
                'deliverables': wp_deliverables,
                'milestones': wp_milestones,
            }

            work_packages.append(wp)
            all_deliverables.extend(wp_deliverables)
            all_milestones.extend(wp_milestones)

        # Sort and deduplicate
        all_deliverables.sort(key=lambda d: (d['due_month'], d['wp']))
        all_milestones.sort(key=lambda m: m['due_month'])

        seen_milestones = set()
        unique_milestones = []
        for m in all_milestones:
            key = (m['title'], m['due_month'])
            if key not in seen_milestones:
                seen_milestones.add(key)
                unique_milestones.append(m)
        all_milestones = unique_milestones

        for i, m in enumerate(all_milestones, 1):
            m['id'] = f'MS{i}'

        for i, d in enumerate(all_deliverables, 1):
            d['seq_id'] = f'D{i}'

        # Generate Gantt chart data
        gantt_data = self._generate_gantt_data(work_packages, duration_months)

        # Calculate effort distribution
        effort_distribution = {wp['title']: wp['effort_pms'] for wp in work_packages}

        # Generate recommendations (enhanced with real data)
        recommendations = self._generate_timeline_recommendations_hybrid(
            work_packages=work_packages,
            duration=duration_months,
            action_type=action_type,
            num_partners=num_partners,
            duration_context=duration_context,
            cluster=cluster
        )

        # Build response
        response = {
            "success": True,
            "tool_name": "generate_timeline",
            "project_title": project_title,
            "parameters": {
                "action_type": action_type,
                "duration_months": duration_months,
                "num_partners": num_partners,
                "total_person_months": total_person_months,
                "start_date": start_date,
                "cluster": cluster
            },
            "work_packages": work_packages,
            "deliverables": all_deliverables,
            "milestones": all_milestones,
            "gantt_data": gantt_data,
            "summary": {
                "total_wps": len(work_packages),
                "total_deliverables": len(all_deliverables),
                "total_milestones": len(all_milestones),
                "effort_distribution": effort_distribution,
                "deliverables_by_type": self._count_by_type(all_deliverables),
            },
            "recommendations": recommendations,
            "metadata": {
                "search_type": "hybrid",
                "sources_used": [],
                "cluster_used": cluster,
                "inferred_clusters": inferred_clusters,
                "templates_customized": cluster is not None
            },
            "timestamp": datetime.now().isoformat()
        }

        # Track sources used
        if graph_stats or results['graph'].get('examples'):
            response["metadata"]["sources_used"].append("graph")
        if sql_stats or results['sql'].get('examples'):
            response["metadata"]["sources_used"].append("sql")

        # Add duration context
        if duration_context:
            response["duration_context"] = duration_context

        # Add similar projects
        if include_similar_projects:
            graph_examples = results['graph'].get('examples', [])
            sql_examples = results['sql'].get('examples', [])

            all_examples = []
            seen_acronyms = set()

            for ex in (graph_examples or []):
                if ex.get('acronym') and ex['acronym'] not in seen_acronyms:
                    all_examples.append({
                        'acronym': ex.get('acronym'),
                        'title': ex.get('title', '')[:80],
                        'budget': ex.get('budget', 0),
                        'duration_months': ex.get('duration'),
                        'source': 'graph'
                    })
                    seen_acronyms.add(ex['acronym'])

            for ex in (sql_examples or []):
                if ex.get('acronym') and ex['acronym'] not in seen_acronyms:
                    all_examples.append({
                        'acronym': ex.get('acronym'),
                        'title': ex.get('title', ''),
                        'budget': ex.get('budget', 0),
                        'duration_months': ex.get('duration_months'),
                        'source': 'sql'
                    })
                    seen_acronyms.add(ex['acronym'])

            if all_examples:
                response["similar_projects"] = all_examples[:5]

        return response

    def _get_cluster_customized_templates(
        self,
        action_type: str,
        cluster: str | None
    ) -> list[dict]:
        """Get WP templates customized for the cluster."""
        base_templates = self.WP_TEMPLATES.get(action_type, self.WP_TEMPLATES['RIA'])

        if not cluster or cluster not in CLUSTER_WP_CUSTOMIZATIONS:
            return base_templates

        customizations = CLUSTER_WP_CUSTOMIZATIONS[cluster]
        customized = []

        for template in base_templates:
            wp_type = template.get('type', 'default')
            if wp_type in customizations:
                custom = template.copy()
                custom['title'] = customizations[wp_type].get('title', template['title'])
                custom['additional_deliverables'] = customizations[wp_type].get('additional_deliverables', [])
                customized.append(custom)
            else:
                customized.append(template)

        return customized

    def _compare_duration(self, user_duration: int, avg_duration: float) -> str:
        """Compare user's duration to average."""
        if user_duration < avg_duration * 0.7:
            return "shorter than typical"
        elif user_duration > avg_duration * 1.3:
            return "longer than typical"
        else:
            return "within typical range"

    def _generate_timeline_template(
        self,
        action_type: str,
        duration_months: int,
        num_partners: int,
        total_person_months: int,
        project_title: str,
        custom_wps: list[dict] | None,
        start_date: str | None,
        cluster: str | None
    ) -> dict[str, Any]:
        """Template-based timeline generation (fallback)."""
        templates = custom_wps or self._get_cluster_customized_templates(action_type, cluster)

        work_packages = []
        all_deliverables = []
        all_milestones = []
        deliverable_counter = 1
        milestone_counter = 1

        for i, template in enumerate(templates, 1):
            if template.get('full_duration'):
                start_month = 1
                end_month = duration_months
            else:
                months = template.get('months', (1, duration_months))
                start_month = months[0]
                end_month = duration_months + months[1] if months[1] < 0 else months[1]
                end_month = min(end_month, duration_months)

            effort = int(total_person_months * template['effort_pct'])

            wp_deliverables, deliverable_counter = self._generate_deliverables(
                wp_num=i,
                wp_title=template['title'],
                start_month=start_month,
                end_month=end_month,
                action_type=action_type,
                counter_start=deliverable_counter,
                cluster=cluster,
                wp_type=template.get('type')
            )

            wp_milestones, milestone_counter = self._generate_milestones(
                wp_num=i,
                wp_title=template['title'],
                start_month=start_month,
                end_month=end_month,
                counter_start=milestone_counter
            )

            # Assign partners to WP (distribute leadership across partners)
            lead_partner_idx = ((i - 1) % num_partners) + 1
            participant_partners = [
                f'P{p}' for p in range(1, num_partners + 1) if p != lead_partner_idx
            ][:min(4, num_partners - 1)]

            wp = {
                'number': i,
                'title': template['title'],
                'objective': template.get('objective', ''),
                'lead': f'P{lead_partner_idx}',
                'lead_partner': f'Partner {lead_partner_idx}',
                'participants': participant_partners,
                'start_month': start_month,
                'end_month': end_month,
                'duration_months': end_month - start_month + 1,
                'effort_pms': effort,
                'effort_percentage': round(template['effort_pct'] * 100, 1),
                'tasks': template.get('tasks', []),
                'deliverables': wp_deliverables,
                'milestones': wp_milestones,
            }

            work_packages.append(wp)
            all_deliverables.extend(wp_deliverables)
            all_milestones.extend(wp_milestones)

        all_deliverables.sort(key=lambda d: (d['due_month'], d['wp']))
        all_milestones.sort(key=lambda m: m['due_month'])

        seen_milestones = set()
        unique_milestones = []
        for m in all_milestones:
            key = (m['title'], m['due_month'])
            if key not in seen_milestones:
                seen_milestones.add(key)
                unique_milestones.append(m)
        all_milestones = unique_milestones

        for i, m in enumerate(all_milestones, 1):
            m['id'] = f'MS{i}'

        for i, d in enumerate(all_deliverables, 1):
            d['seq_id'] = f'D{i}'

        gantt_data = self._generate_gantt_data(work_packages, duration_months)
        effort_distribution = {wp['title']: wp['effort_pms'] for wp in work_packages}

        return {
            "success": True,
            "tool_name": "generate_timeline",
            "project_title": project_title,
            "parameters": {
                "action_type": action_type,
                "duration_months": duration_months,
                "num_partners": num_partners,
                "total_person_months": total_person_months,
                "start_date": start_date
            },
            "work_packages": work_packages,
            "deliverables": all_deliverables,
            "milestones": all_milestones,
            "gantt_data": gantt_data,
            "summary": {
                "total_wps": len(work_packages),
                "total_deliverables": len(all_deliverables),
                "total_milestones": len(all_milestones),
                "effort_distribution": effort_distribution,
                "deliverables_by_type": self._count_by_type(all_deliverables),
            },
            "recommendations": self._generate_timeline_recommendations(
                work_packages, duration_months, action_type, num_partners
            ),
            "metadata": {
                "search_type": "template_only",
                "sources_used": ["template"]
            },
            "timestamp": datetime.now().isoformat()
        }

    def _generate_deliverables(
        self,
        wp_num: int,
        wp_title: str,
        start_month: int,
        end_month: int,
        action_type: str,
        counter_start: int,
        cluster: str | None = None,
        wp_type: str | None = None
    ) -> tuple[list[dict], int]:
        """Generate typical deliverables for a WP."""
        deliverables = []
        duration = end_month - start_month
        counter = counter_start

        wp_type = wp_type or self._classify_wp_type(wp_title)

        deliverable_templates = {
            'management': [
                {'title': 'Project Management Report', 'type': 'R', 'level': 'CO', 'timing': 'periodic'},
                {'title': 'Quality Assurance Plan', 'type': 'R', 'level': 'CO', 'timing': 'early'},
            ],
            'requirements': [
                {'title': 'Requirements Specification', 'type': 'R', 'level': 'PU', 'timing': 'early'},
                {'title': 'State of the Art Report', 'type': 'R', 'level': 'PU', 'timing': 'early'},
            ],
            'research': [
                {'title': 'Technical Report', 'type': 'R', 'level': 'PU', 'timing': 'mid'},
                {'title': 'Prototype', 'type': 'DEM', 'level': 'CO', 'timing': 'late'},
            ],
            'development': [
                {'title': 'Software Release', 'type': 'OTHER', 'level': 'PU', 'timing': 'mid'},
                {'title': 'Technical Documentation', 'type': 'R', 'level': 'PU', 'timing': 'late'},
            ],
            'validation': [
                {'title': 'Validation Report', 'type': 'R', 'level': 'PU', 'timing': 'late'},
                {'title': 'Validated Prototype', 'type': 'DEM', 'level': 'CO', 'timing': 'late'},
            ],
            'pilot': [
                {'title': 'Pilot Setup Report', 'type': 'R', 'level': 'CO', 'timing': 'mid'},
                {'title': 'Pilot Evaluation Report', 'type': 'R', 'level': 'PU', 'timing': 'late'},
            ],
            'business': [
                {'title': 'Business Model Canvas', 'type': 'R', 'level': 'CO', 'timing': 'mid'},
                {'title': 'Exploitation Plan', 'type': 'R', 'level': 'CO', 'timing': 'late'},
            ],
            'dissemination': [
                {'title': 'Dissemination and Exploitation Plan', 'type': 'R', 'level': 'PU', 'timing': 'early'},
                {'title': 'Final Dissemination Report', 'type': 'R', 'level': 'PU', 'timing': 'final'},
            ],
            'communication': [
                {'title': 'Project Website', 'type': 'DEC', 'level': 'PU', 'timing': 'early'},
                {'title': 'Communication Materials', 'type': 'DEC', 'level': 'PU', 'timing': 'mid'},
            ],
            'ethics': [
                {'title': 'Ethics Requirements Report', 'type': 'ETHICS', 'level': 'CO', 'timing': 'early'},
                {'title': 'Data Management Plan', 'type': 'DMP', 'level': 'PU', 'timing': 'early'},
            ],
            'default': [
                {'title': 'Report', 'type': 'R', 'level': 'PU', 'timing': 'late'},
            ],
        }

        templates = deliverable_templates.get(wp_type, deliverable_templates['default'])

        for template in templates:
            if template['timing'] == 'early':
                due_month = start_month + max(duration // 4, 3)
            elif template['timing'] == 'mid':
                due_month = start_month + duration // 2
            elif template['timing'] == 'late':
                due_month = end_month - max(duration // 6, 2)
            elif template['timing'] == 'final':
                due_month = end_month
            elif template['timing'] == 'periodic':
                for period in range(12, duration + 1, 12):
                    deliverables.append({
                        'id': f'D{wp_num}.{counter}',
                        'title': f"{template['title']} (M{start_month + period})",
                        'wp': wp_num,
                        'type': template['type'],
                        'type_description': self.DELIVERABLE_TYPES.get(template['type'], 'Report'),
                        'dissemination_level': template['level'],
                        'due_month': start_month + period,
                    })
                    counter += 1
                continue
            else:
                due_month = end_month

            due_month = min(due_month, end_month)

            deliverables.append({
                'id': f'D{wp_num}.{counter}',
                'title': template['title'],
                'wp': wp_num,
                'type': template['type'],
                'type_description': self.DELIVERABLE_TYPES.get(template['type'], 'Report'),
                'dissemination_level': template['level'],
                'due_month': due_month,
            })
            counter += 1

        return deliverables, counter

    def _generate_milestones(
        self,
        wp_num: int,
        wp_title: str,
        start_month: int,
        end_month: int,
        counter_start: int
    ) -> tuple[list[dict], int]:
        """Generate milestones for a WP."""
        milestones = []
        duration = end_month - start_month
        counter = counter_start

        wp_type = self._classify_wp_type(wp_title)

        milestone_templates = {
            'management': [
                {'title': 'Project Kickoff', 'timing': 'start'},
            ],
            'requirements': [
                {'title': 'Requirements Frozen', 'timing': 'end'},
            ],
            'research': [
                {'title': 'Research Phase Completed', 'timing': 'end'},
            ],
            'development': [
                {'title': 'Development Phase Completed', 'timing': 'end'},
            ],
            'validation': [
                {'title': 'Validation Completed', 'timing': 'end'},
            ],
            'pilot': [
                {'title': 'Pilot Operational', 'timing': 'mid'},
                {'title': 'Pilot Evaluation Completed', 'timing': 'end'},
            ],
            'business': [
                {'title': 'Business Model Validated', 'timing': 'end'},
            ],
            'dissemination': [],
            'default': [],
        }

        templates = milestone_templates.get(wp_type, milestone_templates['default'])

        for template in templates:
            if template['timing'] == 'start':
                due_month = start_month
            elif template['timing'] == 'mid':
                due_month = start_month + duration // 2
            elif template['timing'] == 'end':
                due_month = end_month
            else:
                due_month = end_month

            milestones.append({
                'id': f'MS{counter}',
                'title': template['title'],
                'related_wp': wp_num,
                'due_month': due_month,
                'verification_means': 'Deliverable submission / Review meeting',
            })
            counter += 1

        return milestones, counter

    def _classify_wp_type(self, wp_title: str) -> str:
        """Classify WP type based on title."""
        title_lower = wp_title.lower()

        if 'ethics' in title_lower or 'data management' in title_lower:
            return 'ethics'
        elif 'project management' in title_lower or 'coordination' in title_lower:
            return 'management'
        elif 'requirement' in title_lower or 'state of the art' in title_lower:
            return 'requirements'
        elif 'validation' in title_lower or 'integration' in title_lower or 'testing' in title_lower:
            return 'validation'
        elif 'pilot' in title_lower or 'deployment' in title_lower or 'demonstration' in title_lower:
            return 'pilot'
        elif 'research' in title_lower or 'development' in title_lower or 'core' in title_lower:
            return 'research'
        elif 'dissemination' in title_lower or 'exploitation' in title_lower:
            return 'dissemination'
        elif 'communication' in title_lower or 'outreach' in title_lower or 'stakeholder' in title_lower:
            return 'communication'
        elif 'market' in title_lower or 'business' in title_lower or 'scale' in title_lower:
            return 'business'
        else:
            return 'default'

    def _generate_gantt_data(self, work_packages: list[dict], duration: int) -> dict[str, Any]:
        """Generate Gantt chart data for visualization."""
        gantt_rows = []

        for wp in work_packages:
            row = {
                'id': f'WP{wp["number"]}',
                'label': f'WP{wp["number"]}: {wp["title"]}',
                'start_month': wp['start_month'],
                'end_month': wp['end_month'],
                'effort': wp['effort_pms'],
                'lead': wp.get('lead', ''),
                'bar': self._create_text_bar(wp['start_month'], wp['end_month'], duration)
            }
            gantt_rows.append(row)

        # Generate ASCII Gantt chart
        ascii_gantt = self._generate_ascii_gantt(work_packages, duration)

        # Generate WP dependencies based on timing
        dependencies = self._generate_wp_dependencies(work_packages)

        return {
            'rows': gantt_rows,
            'total_months': duration,
            'phases': self._identify_phases(work_packages, duration),
            'ascii_chart': ascii_gantt,
            'dependencies': dependencies
        }

    def _generate_ascii_gantt(self, work_packages: list[dict], duration: int) -> str:
        """Generate a formatted ASCII Gantt chart."""
        lines = []

        # Header with year markers
        year_marks = duration // 12
        header_line = "                                        "  # Space for WP labels
        for y in range(year_marks + 1):
            month = y * 12 + 1
            if month <= duration:
                header_line += f"Y{y + 1:<11}"
        lines.append(header_line)

        # Month scale
        scale_line = "Work Package                    Lead     "
        for m in range(1, duration + 1):
            if m % 6 == 1:
                scale_line += f"M{m:<5}"
            elif m % 6 == 0:
                scale_line += "|"
            else:
                scale_line += " "
        lines.append(scale_line)
        lines.append("-" * (42 + duration))

        # WP bars
        for wp in work_packages:
            wp_num = wp['number']
            title = wp['title'][:24].ljust(24)
            lead = wp.get('lead', 'P1')[:4].ljust(4)
            bar = self._create_text_bar(wp['start_month'], wp['end_month'], duration)

            # Add milestone markers to bar
            bar_list = list(bar)
            for ms in wp.get('milestones', []):
                ms_month = ms.get('due_month', 0)
                if 0 < ms_month <= duration:
                    bar_list[ms_month - 1] = '◆'  # Milestone marker

            # Add deliverable markers
            for d in wp.get('deliverables', []):
                d_month = d.get('due_month', 0)
                if 0 < d_month <= duration and bar_list[d_month - 1] != '◆':
                    bar_list[d_month - 1] = '▼'  # Deliverable marker

            bar = ''.join(bar_list)
            lines.append(f"WP{wp_num}: {title} {lead} {bar}")

        # Legend
        lines.append("-" * (42 + duration))
        lines.append("Legend: █ = Active  ░ = Inactive  ◆ = Milestone  ▼ = Deliverable")

        return '\n'.join(lines)

    def _generate_wp_dependencies(self, work_packages: list[dict]) -> list[dict]:
        """Generate WP dependencies based on timing and logical sequence."""
        dependencies = []

        # Sort WPs by start time
        sorted_wps = sorted(work_packages, key=lambda x: x['start_month'])

        for i, wp in enumerate(sorted_wps):
            wp_num = wp['number']
            wp_type = self._classify_wp_type(wp['title'])

            # Find WPs that this WP depends on (start before and overlap)
            for other_wp in sorted_wps:
                if other_wp['number'] == wp_num:
                    continue

                other_type = self._classify_wp_type(other_wp['title'])

                # Logical dependencies
                if wp_type == 'research' and other_type == 'requirements':
                    if other_wp['end_month'] >= wp['start_month']:
                        dependencies.append({
                            'from': f"WP{other_wp['number']}",
                            'to': f"WP{wp_num}",
                            'type': 'depends_on',
                            'description': "Research depends on requirements"
                        })
                elif wp_type == 'validation' and other_type == 'research':
                    if other_wp['start_month'] < wp['start_month']:
                        dependencies.append({
                            'from': f"WP{other_wp['number']}",
                            'to': f"WP{wp_num}",
                            'type': 'depends_on',
                            'description': "Validation depends on research outputs"
                        })
                elif wp_type == 'pilot' and other_type == 'validation':
                    if other_wp['start_month'] < wp['start_month']:
                        dependencies.append({
                            'from': f"WP{other_wp['number']}",
                            'to': f"WP{wp_num}",
                            'type': 'depends_on',
                            'description': "Pilot depends on validated components"
                        })

        return dependencies

    def _create_text_bar(self, start: int, end: int, total: int) -> str:
        """Create a simple text representation of a Gantt bar."""
        bar = []
        for m in range(1, total + 1):
            if start <= m <= end:
                bar.append('█')
            else:
                bar.append('░')
        return ''.join(bar)

    def _identify_phases(self, work_packages: list[dict], duration: int) -> list[dict]:
        """Identify project phases based on WP overlap patterns."""
        phases = []

        if duration >= 36:
            phases = [
                {'name': 'Phase 1: Foundation', 'start': 1, 'end': 12},
                {'name': 'Phase 2: Core Development', 'start': 7, 'end': duration - 12},
                {'name': 'Phase 3: Consolidation', 'start': duration - 12, 'end': duration},
            ]
        elif duration >= 24:
            phases = [
                {'name': 'Phase 1: Setup & Analysis', 'start': 1, 'end': 9},
                {'name': 'Phase 2: Implementation', 'start': 6, 'end': duration - 6},
                {'name': 'Phase 3: Finalization', 'start': duration - 9, 'end': duration},
            ]
        else:
            phases = [
                {'name': 'Phase 1: Execution', 'start': 1, 'end': duration},
            ]

        return phases

    def _count_by_type(self, deliverables: list[dict]) -> dict[str, int]:
        """Count deliverables by type."""
        counts = {}
        for d in deliverables:
            d_type = d.get('type', 'OTHER')
            counts[d_type] = counts.get(d_type, 0) + 1
        return counts

    def _generate_timeline_recommendations(
        self,
        work_packages: list[dict],
        duration: int,
        action_type: str,
        num_partners: int
    ) -> list[str]:
        """Generate recommendations for the timeline (template-based)."""
        recommendations = []

        wp_count = len(work_packages)
        if wp_count < 4:
            recommendations.append(
                f"Consider adding more work packages (currently {wp_count}). "
                "Typical projects have 5-7 WPs for better task organization"
            )
        elif wp_count > 10:
            recommendations.append(
                f"High number of work packages ({wp_count}). "
                "Consider consolidating for easier management"
            )

        typical_durations = {'RIA': (36, 48), 'IA': (36, 48), 'CSA': (24, 36), 'ERC': (60, 60)}
        typical = typical_durations.get(action_type, (36, 48))

        if duration < typical[0]:
            recommendations.append(
                f"Duration ({duration} months) is shorter than typical for {action_type} "
                f"({typical[0]}-{typical[1]} months). Ensure scope is achievable"
            )
        elif duration > typical[1]:
            recommendations.append(
                f"Duration ({duration} months) exceeds typical for {action_type}. "
                "Strong justification may be needed"
            )

        research_wps = [wp for wp in work_packages if 'research' in wp['title'].lower() or 'development' in wp['title'].lower()]
        if research_wps:
            avg_start = sum(wp['start_month'] for wp in research_wps) / len(research_wps)
            if avg_start < 3:
                recommendations.append(
                    "Research/development activities start very early. "
                    "Consider allowing time for requirements analysis first"
                )

        total_dels = sum(len(wp['deliverables']) for wp in work_packages)
        dels_per_year = total_dels / (duration / 12)
        if dels_per_year > 15:
            recommendations.append(
                f"High deliverable density ({dels_per_year:.1f}/year). "
                "Consider consolidating or spacing deliverables"
            )
        elif dels_per_year < 5:
            recommendations.append(
                f"Low deliverable density ({dels_per_year:.1f}/year). "
                "Consider adding intermediate deliverables for progress tracking"
            )

        if num_partners > wp_count:
            recommendations.append(
                f"More partners ({num_partners}) than WPs ({wp_count}). "
                "Ensure all partners have meaningful roles in WP leadership"
            )

        return recommendations

    def _generate_timeline_recommendations_hybrid(
        self,
        work_packages: list[dict],
        duration: int,
        action_type: str,
        num_partners: int,
        duration_context: dict | None,
        cluster: str | None
    ) -> list[str]:
        """Generate recommendations enhanced with real data."""
        recommendations = []

        # Duration comparison with real data
        if duration_context:
            comparison = duration_context.get('your_duration_vs_typical', 'within typical range')
            avg_dur = duration_context.get('avg_duration', duration)

            if comparison == "shorter than typical":
                recommendations.append(
                    f"Your duration ({duration} months) is shorter than typical for this type "
                    f"(avg: {avg_dur:.0f} months based on {duration_context.get('project_count', 'N/A')} projects). "
                    "Ensure scope is achievable"
                )
            elif comparison == "longer than typical":
                recommendations.append(
                    f"Your duration ({duration} months) is longer than typical "
                    f"(avg: {avg_dur:.0f} months). Strong justification may be needed"
                )
            else:
                recommendations.append(
                    f"Duration ({duration} months) is within typical range for similar projects"
                )
        else:
            # Fallback to template-based duration check
            typical_durations = {'RIA': (36, 48), 'IA': (36, 48), 'CSA': (24, 36), 'ERC': (60, 60)}
            typical = typical_durations.get(action_type, (36, 48))
            if duration < typical[0]:
                recommendations.append(
                    f"Duration ({duration} months) is shorter than typical for {action_type}"
                )
            elif duration > typical[1]:
                recommendations.append(
                    f"Duration ({duration} months) exceeds typical for {action_type}"
                )

        # WP count recommendations
        wp_count = len(work_packages)
        if wp_count < 4:
            recommendations.append(
                f"Consider adding more work packages (currently {wp_count}). "
                "Typical projects have 5-7 WPs"
            )
        elif wp_count > 10:
            recommendations.append(
                f"High number of work packages ({wp_count}). Consider consolidating"
            )

        # Deliverable density
        total_dels = sum(len(wp['deliverables']) for wp in work_packages)
        dels_per_year = total_dels / (duration / 12)
        if dels_per_year > 15:
            recommendations.append(
                f"High deliverable density ({dels_per_year:.1f}/year). Consider spacing"
            )
        elif dels_per_year < 5:
            recommendations.append(
                f"Low deliverable density ({dels_per_year:.1f}/year). Consider adding intermediate deliverables"
            )

        # Partner/WP balance
        if num_partners > wp_count:
            recommendations.append(
                f"More partners ({num_partners}) than WPs ({wp_count}). "
                "Ensure all partners have meaningful roles"
            )

        # Cluster-specific advice
        if cluster:
            cluster_tips = {
                'CLUSTER-1': "Health projects: Allow time for ethics approvals and clinical protocols",
                'CLUSTER-4': "Digital projects: Plan for iterative development and testing cycles",
                'CLUSTER-5': "Climate/Energy projects: Include buffer time for pilot site deployment",
                'CLUSTER-6': "Food/Bio projects: Account for seasonal constraints in field trials",
            }
            if cluster in cluster_tips:
                recommendations.append(cluster_tips[cluster])

        return recommendations[:6]


# Async wrapper for tool orchestrator compatibility
async def generate_timeline_execute(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """
    Execute timeline generator tool.

    This tool generates project timelines with work packages, deliverables,
    and milestones for Horizon Europe proposals.

    ENHANCED with Hybrid Graph+SQL Architecture for:
    - Real project duration patterns from funded projects
    - Cluster-specific WP customizations
    - Duration benchmarks from similar projects
    - Similar project examples for reference
    """
    tool = TimelineGeneratorTool()

    return tool.generate_timeline(
        action_type=params.get('action_type', 'RIA'),
        duration_months=params.get('duration_months', 36),
        num_partners=params.get('num_partners', 8),
        total_person_months=params.get('total_person_months', 300),
        project_title=params.get('project_title', 'Project'),
        custom_wps=params.get('custom_wps'),
        start_date=params.get('start_date'),
        cluster=params.get('cluster'),
        topic_keywords=params.get('topic_keywords'),
        use_real_patterns=params.get('use_real_patterns', True),
        include_similar_projects=params.get('include_similar_projects', True)
    )
