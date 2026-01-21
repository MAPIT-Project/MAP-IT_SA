"""
Partner Discovery Tool for Horizon Europe Projects.

Helps users find potential consortium partners based on their track record
in relevant Horizon Europe projects.

Enhanced with Neo4j graph database integration for:
- Relationship-based partner discovery
- 2-hop partner discovery (partners of partners)
- Collaboration network analysis
- Network centrality scoring
"""

import logging
import os
from datetime import datetime
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()
logger = logging.getLogger(__name__)

# Cluster keyword mapping for research area -> cluster inference
# Note: ICT/sensor keywords can map to multiple clusters based on application domain
CLUSTER_KEYWORDS = {
    'CLUSTER-1': ['health', 'medical', 'clinical', 'disease', 'patient', 'healthcare',
                  'hospital', 'therapy', 'diagnosis', 'pharmaceutical', 'cancer',
                  'vaccine', 'drug', 'biomedical', 'genomics', 'personalized medicine',
                  'medical device', 'wearable', 'health monitoring', 'telemedicine'],
    'CLUSTER-2': ['culture', 'democracy', 'social', 'heritage', 'creative', 'inclusive',
                  'society', 'governance', 'media', 'arts', 'humanities', 'SSH',
                  'migration', 'identity', 'citizen', 'participation', 'cohesion',
                  'european identity', 'cultural', 'societal', 'democratic', 'policy',
                  'education', 'gender', 'inequality', 'inclusion', 'diversity'],
    'CLUSTER-3': ['security', 'cybersecurity', 'border', 'crime', 'disaster', 'resilience',
                  'defence', 'terrorism', 'critical infrastructure', 'surveillance'],
    'CLUSTER-4': ['digital', 'AI', 'artificial intelligence', 'data', 'industry', 'space',
                  'manufacturing', 'robotics', 'computing', 'machine learning', 'quantum',
                  'electronics', 'semiconductor', 'cloud', 'iot', 'internet of things',
                  'sensor', 'monitoring', 'ICT', 'smart technology', 'data platform',
                  'automation', 'embedded systems', 'telemetry', 'edge computing'],
    'CLUSTER-5': ['climate', 'energy', 'mobility', 'transport', 'hydrogen', 'battery',
                  'renewable', 'green', 'carbon', 'solar', 'wind', 'electric vehicle',
                  'sustainable', 'decarbonization', 'clean energy', 'smart grid',
                  'energy monitoring', 'building automation'],
    'CLUSTER-6': ['food', 'agriculture', 'bioeconomy', 'biodiversity', 'ocean', 'environment',
                  'soil', 'water', 'forestry', 'marine', 'circular economy', 'farming',
                  'precision agriculture', 'smart farming', 'environmental monitoring',
                  'water management', 'nature-based solutions', 'irrigation', 'aridity',
                  'water quality', 'soil sensors', 'agritech']
}

# Organization type descriptions
ORG_TYPE_DESCRIPTIONS = {
    "HES": "Higher Education Institution",
    "REC": "Research Organization",
    "PRC": "Private Company (Large)",
    "SME": "Small/Medium Enterprise",
    "PUB": "Public Body",
    "OTH": "Other Organization"
}

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

# Country name to code mapping
COUNTRY_CODES = {
    'germany': 'DE', 'german': 'DE', 'de': 'DE',
    'france': 'FR', 'french': 'FR', 'fr': 'FR',
    'italy': 'IT', 'italian': 'IT', 'it': 'IT',
    'spain': 'ES', 'spanish': 'ES', 'es': 'ES',
    'netherlands': 'NL', 'dutch': 'NL', 'nl': 'NL',
    'belgium': 'BE', 'belgian': 'BE', 'be': 'BE',
    'austria': 'AT', 'austrian': 'AT', 'at': 'AT',
    'sweden': 'SE', 'swedish': 'SE', 'se': 'SE',
    'denmark': 'DK', 'danish': 'DK', 'dk': 'DK',
    'finland': 'FI', 'finnish': 'FI', 'fi': 'FI',
    'ireland': 'IE', 'irish': 'IE', 'ie': 'IE',
    'portugal': 'PT', 'portuguese': 'PT', 'pt': 'PT',
    'greece': 'EL', 'greek': 'EL', 'el': 'EL', 'gr': 'EL',
    'poland': 'PL', 'polish': 'PL', 'pl': 'PL',
    'czech': 'CZ', 'czechia': 'CZ', 'cz': 'CZ',
    'romania': 'RO', 'romanian': 'RO', 'ro': 'RO',
    'hungary': 'HU', 'hungarian': 'HU', 'hu': 'HU',
    'switzerland': 'CH', 'swiss': 'CH', 'ch': 'CH',
    'norway': 'NO', 'norwegian': 'NO', 'no': 'NO',
    'uk': 'UK', 'united kingdom': 'UK', 'britain': 'UK', 'british': 'UK', 'gb': 'UK',
    'israel': 'IL', 'israeli': 'IL', 'il': 'IL',
    'slovenia': 'SI', 'slovenian': 'SI', 'si': 'SI',
    'croatia': 'HR', 'croatian': 'HR', 'hr': 'HR',
    'estonia': 'EE', 'estonian': 'EE', 'ee': 'EE',
    'latvia': 'LV', 'latvian': 'LV', 'lv': 'LV',
    'lithuania': 'LT', 'lithuanian': 'LT', 'lt': 'LT',
    'cyprus': 'CY', 'cypriot': 'CY', 'cy': 'CY',
    'malta': 'MT', 'maltese': 'MT', 'mt': 'MT',
    'luxembourg': 'LU', 'lu': 'LU',
    'slovakia': 'SK', 'slovak': 'SK', 'sk': 'SK',
    'bulgaria': 'BG', 'bulgarian': 'BG', 'bg': 'BG',
    'turkey': 'TR', 'turkish': 'TR', 'tr': 'TR',
}

# Organization type mapping from user input
# Note: CORDIS doesn't have a separate SME type - SMEs are classified as PRC
# We map SME requests to PRC but note this in the output
ORG_TYPE_MAP = {
    'university': 'HES', 'universities': 'HES', 'hes': 'HES', 'academic': 'HES',
    'research': 'REC', 'rec': 'REC', 'research organization': 'REC', 'institute': 'REC',
    'company': 'PRC', 'companies': 'PRC', 'prc': 'PRC', 'industry': 'PRC', 'corporate': 'PRC',
    'sme': 'PRC', 'smes': 'PRC', 'small': 'PRC', 'startup': 'PRC', 'startups': 'PRC',  # SMEs are under PRC in CORDIS
    'public': 'PUB', 'pub': 'PUB', 'government': 'PUB',
}


class PartnerDiscoveryTool:
    """Tool to find experienced partners for consortium building.

    Enhanced with Neo4j graph integration for:
    - Faster relationship-based queries
    - 2-hop partner discovery (partners of partners)
    - Collaboration network analysis
    - Network centrality scoring
    """

    def __init__(self):
        """Initialize with database connection and graph service."""
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.warning("DATABASE_URL not set - partner discovery will be limited")

        # Initialize Neo4j graph service for relationship-based queries
        self._graph_service = None
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            self._graph_service = GraphSearchService()
            logger.info("✅ Graph service available for partner discovery")
        except Exception as e:
            logger.warning(f"⚠️ Graph service not available: {e}")

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _normalize_country(self, country: str | None) -> str | None:
        """Normalize country name to code."""
        if not country:
            return None
        country_lower = country.lower().strip()
        # Check if already a 2-letter code
        if len(country_lower) == 2:
            return country_lower.upper()
        return COUNTRY_CODES.get(country_lower, country.upper())

    def _normalize_org_type(self, org_type: str | None) -> str | None:
        """Normalize organization type to code."""
        if not org_type:
            return None
        org_lower = org_type.lower().strip()
        return ORG_TYPE_MAP.get(org_lower, org_type.upper())

    def _normalize_cluster(self, cluster: str | None) -> str | None:
        """Normalize cluster code.

        Handles various formats:
        - Single codes: "CL5", "CLUSTER-5", "cluster 5"
        - Comma-separated (takes first): "CL4, CL5" -> "CL4"
        """
        if not cluster:
            return None

        # Handle comma-separated values - take the first one
        if ',' in cluster:
            cluster = cluster.split(',')[0].strip()
            logger.debug(f"Cluster had multiple values, using first: {cluster}")

        cluster_upper = cluster.upper().replace(' ', '').replace('-', '')
        return CLUSTER_MAP.get(cluster_upper, cluster.upper())

    def _infer_clusters_from_keywords(self, keywords: str) -> list[str]:
        """
        Infer relevant Horizon Europe clusters from research keywords.

        Returns list of cluster codes (e.g., ['CLUSTER-4', 'CLUSTER-1'])
        """
        keywords_lower = keywords.lower()
        matched_clusters = []

        for cluster_code, cluster_keywords in CLUSTER_KEYWORDS.items():
            if any(kw in keywords_lower for kw in cluster_keywords):
                matched_clusters.append(cluster_code)

        return matched_clusters if matched_clusters else ['CLUSTER-4']  # Default to digital

    def _find_partners_graph(
        self,
        topic_keywords: str,
        country: str | None = None,
        organization_type: str | None = None,
        cluster: str | None = None,
        min_projects: int = 2,
        limit: int = 20,
        include_2hop: bool = True
    ) -> dict[str, Any]:
        """
        Find partners using Neo4j graph database.

        Advantages over SQL:
        - Faster relationship traversal
        - 2-hop partner discovery (partners of partners)
        - Network centrality awareness
        """
        if not self._graph_service:
            return None

        try:
            # Determine cluster(s) to search
            if cluster:
                clusters_to_search = [self._normalize_cluster(cluster)]
            else:
                clusters_to_search = self._infer_clusters_from_keywords(topic_keywords)

            logger.info(f"📊 Graph partner search: keywords='{topic_keywords}', clusters={clusters_to_search}")

            all_partners = []
            seen_org_names: set[str] = set()

            for cluster_code in clusters_to_search[:2]:  # Limit to top 2 clusters
                # Get partner suggestions from graph
                suggestions = self._graph_service.suggest_consortium_partners(
                    cluster_code=cluster_code,
                    coordinator_country=None,
                    target_partner_count=limit * 2  # Get more for filtering
                )

                for partner in suggestions.get('suggestions', []):
                    org_name = partner.get('name', '')

                    # Skip duplicates
                    if org_name in seen_org_names:
                        continue
                    seen_org_names.add(org_name)

                    # Apply filters
                    if country:
                        country_code = self._normalize_country(country)
                        if partner.get('country') != country_code:
                            continue

                    if organization_type:
                        org_type_code = self._normalize_org_type(organization_type)
                        if partner.get('entity_type') != org_type_code:
                            continue

                    # Filter by min projects
                    if partner.get('project_count', 0) < min_projects:
                        continue

                    # Calculate experience score
                    experience_score = self._calculate_experience_score(
                        relevant_projects=partner.get('project_count', 0),
                        as_coordinator=partner.get('coordinations', 0),
                        total_projects=partner.get('project_count', 0),
                        funding=partner.get('total_funding', 0)
                    )

                    formatted_partner = {
                        "name": org_name,
                        "short_name": partner.get('short_name') or org_name,
                        "country": partner.get('country', 'Unknown'),
                        "city": "",
                        "type": partner.get('entity_type', 'Unknown'),
                        "type_description": ORG_TYPE_DESCRIPTIONS.get(
                            partner.get('entity_type'), partner.get('entity_type_name', 'Unknown')
                        ),
                        "track_record": {
                            "total_he_projects": partner.get('project_count', 0),
                            "relevant_projects": partner.get('project_count', 0),
                            "as_coordinator": partner.get('coordinations', 0),
                            "as_participant": partner.get('project_count', 0) - partner.get('coordinations', 0),
                            "funding_in_relevant": partner.get('total_funding', 0)
                        },
                        "relevant_projects": [],  # Graph doesn't return project details
                        "experience_score": experience_score,
                        "discovery_type": "direct",
                        "matched_cluster": cluster_code
                    }

                    all_partners.append(formatted_partner)

            # Find 2-hop partners if requested and we found direct partners
            two_hop_partners = []
            if include_2hop and all_partners:
                two_hop_partners = self._find_2hop_partners(
                    all_partners[:5],  # Use top 5 as seeds
                    seen_org_names,
                    country,
                    organization_type,
                    min_projects,
                    limit=10
                )

            # Combine results
            all_partners.extend(two_hop_partners)

            # Sort by experience score
            all_partners.sort(key=lambda x: x['experience_score'], reverse=True)

            # Limit results
            all_partners = all_partners[:limit]

            if not all_partners:
                return None  # Fall back to SQL

            # Generate insights
            insights = self._generate_insights(all_partners, topic_keywords)

            return {
                "success": True,
                "tool_name": "find_experienced_partners",
                "query_params": {
                    "topic_keywords": topic_keywords,
                    "country": country,
                    "organization_type": organization_type,
                    "cluster": cluster,
                    "min_projects": min_projects
                },
                "total_found": len(all_partners),
                "experienced_partners": all_partners,
                "aggregated_insights": insights,
                "search_tips": self._generate_search_tips(all_partners, topic_keywords, country, organization_type),
                "data_source": "neo4j_graph",
                "search_metadata": {
                    "method": "graph_enhanced",
                    "clusters_searched": clusters_to_search,
                    "include_2hop": include_2hop,
                    "direct_partners": len([p for p in all_partners if p.get('discovery_type') == 'direct']),
                    "two_hop_partners": len([p for p in all_partners if p.get('discovery_type') == '2-hop'])
                },
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Graph partner search failed: {e}")
            return None  # Fall back to SQL

    def _find_2hop_partners(
        self,
        seed_partners: list[dict],
        seen_names: set[str],
        country: str | None,
        organization_type: str | None,
        min_projects: int,
        limit: int = 10
    ) -> list[dict]:
        """
        Find 2-hop partners (partners of partners).

        These are organizations that have collaborated with our top direct partners
        but haven't been found in the direct search. Great for finding:
        - Smaller but well-connected organizations
        - Partners from underrepresented countries
        - Organizations with strong collaboration networks

        Note: min_projects is relaxed for 2-hop (uses min(min_projects, 2)) since
        these are discovered via relationships, not keyword matching.
        """
        if not self._graph_service:
            return []

        two_hop_partners = []

        # Relax min_projects for 2-hop (relationship-based discovery)
        relaxed_min = min(min_projects, 2)

        # Track collaboration strength for ranking
        partner_strength: dict[str, int] = {}

        for seed in seed_partners[:5]:  # Use top 5 seeds for better coverage
            seed_name = seed.get('name', '')
            if not seed_name:
                continue

            try:
                # Get collaboration network
                network = self._graph_service.get_organization_collaboration_network(
                    seed_name,
                    depth=1,
                    limit=30  # Get more partners per seed
                )

                for partner in network.get('partners', []):
                    partner_name = partner.get('name', '')

                    # Skip if already seen as direct partner
                    if partner_name in seen_names:
                        # But track if they collaborate with multiple seeds
                        if partner_name in partner_strength:
                            partner_strength[partner_name] += partner.get('collaborations', 0)
                        continue

                    # Apply filters (relaxed)
                    if country:
                        country_code = self._normalize_country(country)
                        if partner.get('country') != country_code:
                            continue

                    if organization_type:
                        org_type_code = self._normalize_org_type(organization_type)
                        partner_type = partner.get('type', '')
                        if partner_type and partner_type != org_type_code:
                            continue

                    collaborations = partner.get('collaborations', 0)
                    if collaborations < relaxed_min:
                        continue

                    seen_names.add(partner_name)

                    # Track total collaboration strength (may see same partner via multiple seeds)
                    if partner_name in partner_strength:
                        partner_strength[partner_name] += collaborations
                    else:
                        partner_strength[partner_name] = collaborations

                    # Calculate experience score based on collaboration strength
                    # Higher base score for 2-hop partners with strong connections
                    experience_score = min(0.3 + (collaborations / 20), 0.6)

                    formatted_partner = {
                        "name": partner_name,
                        "short_name": partner_name.split()[0] if partner_name else "Unknown",
                        "country": partner.get('country', 'Unknown'),
                        "city": "",
                        "type": partner.get('type', 'Unknown'),
                        "type_description": ORG_TYPE_DESCRIPTIONS.get(
                            partner.get('type'), 'Unknown'
                        ),
                        "track_record": {
                            "total_he_projects": collaborations,
                            "relevant_projects": collaborations,
                            "as_coordinator": 0,
                            "as_participant": collaborations,
                            "funding_in_relevant": 0
                        },
                        "relevant_projects": [],
                        "experience_score": experience_score,
                        "discovery_type": "2-hop",
                        "connected_via": seed_name,
                        "shared_projects_with_seed": collaborations
                    }

                    two_hop_partners.append(formatted_partner)

            except Exception as e:
                logger.debug(f"Error getting 2-hop partners for {seed_name}: {e}")
                continue

        # Sort by collaboration strength and limit
        two_hop_partners.sort(
            key=lambda x: partner_strength.get(x.get('name', ''), x.get('shared_projects_with_seed', 0)),
            reverse=True
        )

        logger.info(f"📊 Found {len(two_hop_partners)} 2-hop partners")
        return two_hop_partners[:limit]

    def get_collaboration_network(
        self,
        organization_name: str,
        depth: int = 1,
        limit: int = 30
    ) -> dict[str, Any]:
        """
        Get the collaboration network for a specific organization.

        This shows which organizations have partnered with the target organization
        across Horizon Europe projects.

        Args:
            organization_name: Name of the organization to analyze
            depth: How many hops to traverse (1 = direct partners)
            limit: Maximum number of partners to return

        Returns:
            Dict with organization details and partner list
        """
        if not self._graph_service:
            return {
                "success": False,
                "error": "Graph service not available for network analysis",
                "tool_name": "get_collaboration_network"
            }

        try:
            network = self._graph_service.get_organization_collaboration_network(
                organization_name,
                depth=depth,
                limit=limit
            )

            if not network.get('success', False) and not network.get('organization'):
                return {
                    "success": False,
                    "error": f"Organization '{organization_name}' not found in database",
                    "tool_name": "get_collaboration_network"
                }

            # Format partners with more detail
            formatted_partners = []
            for partner in network.get('partners', []):
                formatted_partners.append({
                    "name": partner.get('name', 'Unknown'),
                    "country": partner.get('country', 'Unknown'),
                    "type": partner.get('type', 'Unknown'),
                    "is_sme": partner.get('is_sme', False),
                    "collaborations": partner.get('collaborations', 0)
                })

            # Sort by collaboration count
            formatted_partners.sort(key=lambda x: x['collaborations'], reverse=True)

            return {
                "success": True,
                "tool_name": "get_collaboration_network",
                "organization": network.get('organization', organization_name),
                "country": network.get('country', 'Unknown'),
                "total_partners": len(formatted_partners),
                "partners": formatted_partners,
                "data_source": "neo4j_graph",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Collaboration network error: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": "get_collaboration_network"
            }

    def find_partners(
        self,
        topic_keywords: str,
        country: str | None = None,
        organization_type: str | None = None,
        cluster: str | None = None,
        min_projects: int = 2,
        role_filter: str | None = None,
        limit: int = 20,
        include_2hop: bool = True,
        programme: str | None = None
    ) -> dict[str, Any]:
        """
        Find organizations with proven track records in Horizon Europe and/or H2020 projects.

        Uses a HYBRID approach combining:
        1. Graph (Neo4j): Fast relationship-based discovery + 2-hop partners
        2. SQL (PostgreSQL): Precise keyword matching + detailed project examples

        Results are combined using Reciprocal Rank Fusion (RRF) for optimal relevance.

        Args:
            topic_keywords: Required keywords describing the research area
            country: Optional country name or code
            organization_type: Optional org type (HES, REC, PRC, SME)
            cluster: Optional cluster code
            min_projects: Minimum projects to be considered experienced
            role_filter: Filter by role (coordinator, participant, or None for both)
            limit: Max results to return
            include_2hop: Include 2-hop partners (partners of partners) - graph only
            programme: Optional programme filter: 'HORIZON' (HE only), 'H2020' (H2020 only),
                       'both' or None (includes both programmes for comprehensive results)

        Returns:
            List of experienced partners with track records from both sources
        """
        return self._find_partners_hybrid(
            topic_keywords=topic_keywords,
            country=country,
            organization_type=organization_type,
            cluster=cluster,
            min_projects=min_projects,
            role_filter=role_filter,
            limit=limit,
            include_2hop=include_2hop,
            programme=programme
        )

    def _find_partners_hybrid(
        self,
        topic_keywords: str,
        country: str | None = None,
        organization_type: str | None = None,
        cluster: str | None = None,
        min_projects: int = 2,
        role_filter: str | None = None,
        limit: int = 20,
        include_2hop: bool = True,
        programme: str | None = None
    ) -> dict[str, Any]:
        """
        Hybrid partner discovery combining Graph and SQL sources.

        Strategy:
        1. Graph search: Find partners via cluster relationships + 2-hop discovery
        2. SQL search: Find partners via precise keyword matching in project text
        3. Merge: Combine results using RRF, enrich graph results with SQL details
        """
        sources_used = []
        graph_partners = []
        sql_partners = []

        # Normalize inputs
        country_code = self._normalize_country(country)
        org_type_code = self._normalize_org_type(organization_type)
        cluster_code = self._normalize_cluster(cluster) if cluster else None

        # ========================================================================
        # SOURCE 1: Graph-based discovery (relationships + 2-hop)
        # ========================================================================
        if self._graph_service:
            try:
                graph_result = self._find_partners_graph(
                    topic_keywords=topic_keywords,
                    country=country,
                    organization_type=organization_type,
                    cluster=cluster,
                    min_projects=min_projects,
                    limit=limit * 2,  # Get more for merging
                    include_2hop=include_2hop
                )
                if graph_result and graph_result.get('experienced_partners'):
                    graph_partners = graph_result['experienced_partners']
                    sources_used.append('neo4j_graph')
                    logger.info(f"📊 Graph source: {len(graph_partners)} partners found")
            except Exception as e:
                logger.warning(f"Graph search failed: {e}")

        # ========================================================================
        # SOURCE 2: SQL-based discovery (keyword matching + project details)
        # ========================================================================
        try:
            sql_result = self._find_partners_sql(
                topic_keywords=topic_keywords,
                country_code=country_code,
                org_type_code=org_type_code,
                cluster_code=cluster_code,
                min_projects=min_projects,
                role_filter=role_filter,
                limit=limit * 2,  # Get more for merging
                programme=programme
            )
            if sql_result:
                sql_partners = sql_result
                sources_used.append('postgresql')
                logger.info(f"📊 SQL source: {len(sql_partners)} partners found")
        except Exception as e:
            logger.warning(f"SQL search failed: {e}")

        # ========================================================================
        # MERGE: Combine results using RRF and enrich
        # ========================================================================
        if not graph_partners and not sql_partners:
            return {
                "success": True,
                "tool_name": "find_experienced_partners",
                "query_params": {
                    "topic_keywords": topic_keywords,
                    "country": country,
                    "organization_type": organization_type,
                    "cluster": cluster,
                    "min_projects": min_projects,
                    "programme": programme
                },
                "total_found": 0,
                "experienced_partners": [],
                "message": f"No organizations found with {min_projects}+ projects matching '{topic_keywords}'. Try broader keywords or reduce min_projects.",
                "suggestions": [
                    "Try more general keywords",
                    "Remove country or organization type filters",
                    "Lower min_projects threshold to 1"
                ],
                "data_source": "none",
                "sources_used": sources_used,
                "timestamp": datetime.now().isoformat()
            }

        # Merge and deduplicate using RRF
        merged_partners, graph_only_to_enrich = self._merge_partner_results(
            graph_partners=graph_partners,
            sql_partners=sql_partners,
            topic_keywords=topic_keywords,
            limit=limit
        )

        # Enrich graph-only partners with SQL project details
        if graph_only_to_enrich:
            logger.info(f"📊 Enriching {len(graph_only_to_enrich)} graph-only partners with SQL project details")
            self._enrich_graph_partners_with_sql(graph_only_to_enrich, topic_keywords)

        # Generate insights
        insights = self._generate_insights(merged_partners, topic_keywords)

        # Count sources
        direct_count = len([p for p in merged_partners if p.get('discovery_type') == 'direct'])
        two_hop_count = len([p for p in merged_partners if p.get('discovery_type') == '2-hop'])
        sql_only_count = len([p for p in merged_partners if p.get('discovery_type') == 'keyword_match'])
        enriched_count = len([p for p in merged_partners if 'sql_enriched' in p.get('found_in_sources', [])])
        both_sources_count = len([p for p in merged_partners if p.get('found_in_sources') == ['graph', 'sql']])

        return {
            "success": True,
            "tool_name": "find_experienced_partners",
            "query_params": {
                "topic_keywords": topic_keywords,
                "country": country,
                "organization_type": organization_type,
                "cluster": cluster,
                "min_projects": min_projects,
                "programme": programme
            },
            "total_found": len(merged_partners),
            "experienced_partners": merged_partners,
            "aggregated_insights": insights,
            "search_tips": self._generate_search_tips(merged_partners, topic_keywords, country, organization_type),
            "data_source": "hybrid",
            "search_metadata": {
                "method": "hybrid_graph_sql",
                "sources_used": sources_used,
                "graph_results": len(graph_partners),
                "sql_results": len(sql_partners),
                "direct_partners": direct_count,
                "two_hop_partners": two_hop_count,
                "keyword_match_partners": sql_only_count,
                "both_sources": both_sources_count,
                "graph_enriched_with_sql": enriched_count,
                "include_2hop": include_2hop,
                "programme_filter": programme or "both"
            },
            "timestamp": datetime.now().isoformat()
        }

    def _find_partners_sql(
        self,
        topic_keywords: str,
        country_code: str | None = None,
        org_type_code: str | None = None,
        cluster_code: str | None = None,
        min_projects: int = 2,
        role_filter: str | None = None,
        limit: int = 20,
        programme: str | None = None
    ) -> list[dict[str, Any]]:
        """
        SQL-based partner discovery with precise keyword matching.

        Args:
            topic_keywords: Keywords to search for in project descriptions
            country_code: Optional country filter (2-letter code)
            org_type_code: Optional organization type filter
            cluster_code: Optional cluster filter
            min_projects: Minimum projects required
            role_filter: Optional role filter ('coordinator' or 'participant')
            limit: Maximum results to return
            programme: Optional programme filter:
                       - 'HORIZON' for Horizon Europe only
                       - 'H2020' for Horizon 2020 only
                       - 'both' or None for both programmes (default)

        Returns list of partners with full project details.
        """
        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build WHERE conditions for projects
            # Default: Include both HORIZON (HE) and H2020 for comprehensive results
            params = []
            if programme and programme.upper() == 'HORIZON':
                project_conditions = ["p.\"frameworkProgramme\" = 'HORIZON'"]
            elif programme and programme.upper() == 'H2020':
                project_conditions = ["p.\"frameworkProgramme\" = 'H2020'"]
            else:
                # Default: Include both programmes for comprehensive results
                project_conditions = ["p.\"frameworkProgramme\" IN ('HORIZON', 'H2020')"]

            # Topic keywords filter (search in objective and title)
            keywords = topic_keywords.split()
            keyword_conditions = []
            for kw in keywords:
                keyword_conditions.append("(p.objective ILIKE %s OR p.title ILIKE %s)")
                params.extend([f"%{kw}%", f"%{kw}%"])
            if keyword_conditions:
                project_conditions.append(f"({' OR '.join(keyword_conditions)})")

            # Cluster filter
            if cluster_code:
                project_conditions.append("p.topics ILIKE %s")
                params.append(f"%{cluster_code}%")

            project_where = " AND ".join(project_conditions)

            # Build organization filter conditions
            org_conditions = []
            if country_code:
                org_conditions.append("o.country = %s")
                params.append(country_code)

            if org_type_code:
                org_conditions.append("o.\"activityType\" = %s")
                params.append(org_type_code)

            if role_filter:
                org_conditions.append("o.role = %s")
                params.append(role_filter.lower())

            org_where = " AND ".join(org_conditions) if org_conditions else "TRUE"

            # Main query: Find organizations with experience in matching projects
            sql = f"""
                WITH matching_projects AS (
                    SELECT DISTINCT p.id, p.acronym, p.title, p."ecMaxContribution", p."startDate"
                    FROM projects p
                    WHERE {project_where}
                ),
                org_participation AS (
                    SELECT
                        o."organisationID",
                        o.name,
                        o."shortName",
                        o.country,
                        o.city,
                        o."activityType",
                        mp.id as project_id,
                        mp.acronym as project_acronym,
                        mp.title as project_title,
                        mp."startDate" as project_start,
                        o.role,
                        o."ecContribution"
                    FROM organizations o
                    JOIN matching_projects mp ON o."projectID" = mp.id
                    WHERE {org_where}
                ),
                org_stats AS (
                    SELECT
                        "organisationID",
                        name,
                        "shortName",
                        country,
                        MAX(city) as city,
                        "activityType",
                        COUNT(DISTINCT project_id) as relevant_projects,
                        SUM(CASE WHEN role = 'coordinator' THEN 1 ELSE 0 END) as as_coordinator,
                        SUM(CASE WHEN role = 'participant' THEN 1 ELSE 0 END) as as_participant,
                        SUM("ecContribution") as funding_in_relevant,
                        ARRAY_AGG(DISTINCT jsonb_build_object(
                            'acronym', project_acronym,
                            'title', project_title,
                            'role', role,
                            'funding', "ecContribution",
                            'start_date', project_start
                        )) as projects
                    FROM org_participation
                    GROUP BY "organisationID", name, "shortName", country, "activityType"
                    HAVING COUNT(DISTINCT project_id) >= %s
                )
                SELECT
                    os.*,
                    (SELECT COUNT(DISTINCT o2."projectID")
                     FROM organizations o2
                     WHERE o2."organisationID" = os."organisationID") as total_he_projects
                FROM org_stats os
                ORDER BY relevant_projects DESC, as_coordinator DESC, funding_in_relevant DESC
                LIMIT %s
            """
            params.extend([min_projects, limit])

            cursor.execute(sql, params)
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            if not results:
                return []

            # Process results into partner list
            partners = []
            for r in results:
                # Parse projects JSON
                projects_list = []
                if r['projects']:
                    for p in r['projects'][:5]:  # Limit to 5 recent projects
                        if isinstance(p, dict):
                            projects_list.append({
                                "acronym": p.get('acronym', 'N/A'),
                                "title": (p.get('title') or '')[:60] + ('...' if len(p.get('title') or '') > 60 else ''),
                                "role": p.get('role', 'participant'),
                                "funding": round(float(p.get('funding') or 0), 0),
                                "start_date": str(p.get('start_date', ''))[:10] if p.get('start_date') else None
                            })

                # Calculate experience score
                experience_score = self._calculate_experience_score(
                    relevant_projects=int(r['relevant_projects'] or 0),
                    as_coordinator=int(r['as_coordinator'] or 0),
                    total_projects=int(r['total_he_projects'] or 0),
                    funding=float(r['funding_in_relevant'] or 0)
                )

                partner = {
                    "name": r['name'] or 'Unknown',
                    "short_name": r['shortName'] or r['name'] or 'Unknown',
                    "country": r['country'] or 'Unknown',
                    "city": r['city'] or '',
                    "type": r['activityType'] or 'Unknown',
                    "type_description": ORG_TYPE_DESCRIPTIONS.get(r['activityType'], r['activityType'] or 'Unknown'),
                    "track_record": {
                        "total_he_projects": int(r['total_he_projects'] or 0),
                        "relevant_projects": int(r['relevant_projects'] or 0),
                        "as_coordinator": int(r['as_coordinator'] or 0),
                        "as_participant": int(r['as_participant'] or 0),
                        "funding_in_relevant": round(float(r['funding_in_relevant'] or 0), 0)
                    },
                    "relevant_projects": projects_list,
                    "experience_score": experience_score,
                    "discovery_type": "keyword_match"  # Mark as SQL result
                }

                partners.append(partner)

            return partners

        except Exception as e:
            logger.error(f"SQL partner search failed: {e}")
            return []

    def _merge_partner_results(
        self,
        graph_partners: list[dict[str, Any]],
        sql_partners: list[dict[str, Any]],
        topic_keywords: str = "",
        limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        Merge and deduplicate partner results from Graph and SQL sources.

        Uses Reciprocal Rank Fusion (RRF) to combine rankings.
        Enriches graph results with SQL project details when available.

        RRF formula: score = sum(1 / (k + rank_i)) for each source
        where k=60 is a constant that balances top and lower ranked results.

        Additional boost for:
        - Partners found in both sources (+0.005)
        - 2-hop partners with high collaboration count (+0.002)
        """
        k = 60  # RRF constant

        # Build name -> partner mapping for deduplication
        partner_map: dict[str, dict[str, Any]] = {}

        # Track RRF scores
        rrf_scores: dict[str, float] = {}

        # Build SQL lookup for enrichment
        sql_by_name: dict[str, dict[str, Any]] = {}
        for partner in sql_partners:
            name = partner.get('name', '').upper().strip()
            if name:
                sql_by_name[name] = partner

        # Process graph partners (ranked by experience_score)
        for rank, partner in enumerate(graph_partners, 1):
            name = partner.get('name', '').upper().strip()
            if not name:
                continue

            rrf_scores[name] = rrf_scores.get(name, 0) + (1.0 / (k + rank))

            # Boost 2-hop partners with strong connections
            if partner.get('discovery_type') == '2-hop':
                shared_projects = partner.get('shared_projects_with_seed', 0)
                if shared_projects >= 5:
                    rrf_scores[name] += 0.002  # Boost well-connected 2-hop partners

            partner_map[name] = partner

        # Process SQL partners (ranked by experience_score and project count)
        for rank, partner in enumerate(sql_partners, 1):
            name = partner.get('name', '').upper().strip()
            if not name:
                continue

            rrf_scores[name] = rrf_scores.get(name, 0) + (1.0 / (k + rank))

            if name in partner_map:
                # Enrich graph result with SQL details (project examples)
                existing = partner_map[name]

                # Keep SQL project details (more complete)
                if partner.get('relevant_projects') and not existing.get('relevant_projects'):
                    existing['relevant_projects'] = partner['relevant_projects']

                # Keep better track record info (SQL has keyword-specific counts)
                sql_track = partner.get('track_record', {})
                existing_track = existing.get('track_record', {})

                # SQL track record is keyword-specific, so prefer it
                if sql_track.get('relevant_projects', 0) > 0:
                    existing['track_record'] = sql_track
                    existing['city'] = partner.get('city', existing.get('city', ''))

                # Mark as found in both sources and boost score
                existing['found_in_sources'] = ['graph', 'sql']
                rrf_scores[name] += 0.005  # Boost for being in both sources
            else:
                # New partner from SQL only
                partner_map[name] = partner
                partner['found_in_sources'] = ['sql']

        # Mark graph-only partners and try to enrich them
        graph_only_names = []
        for name, partner in partner_map.items():
            if 'found_in_sources' not in partner:
                partner['found_in_sources'] = ['graph']
                graph_only_names.append(name)

        # Sort by RRF score (higher is better)
        sorted_names = sorted(rrf_scores.keys(), key=lambda n: rrf_scores[n], reverse=True)

        # Build final list (limited)
        merged = []
        for name in sorted_names[:limit]:
            partner = partner_map[name]
            partner['rrf_score'] = round(rrf_scores[name], 4)
            merged.append(partner)

        # Collect graph-only partners that need enrichment
        graph_only_to_enrich = [
            p for p in merged
            if p.get('found_in_sources') == ['graph'] and not p.get('relevant_projects')
        ]

        return merged, graph_only_to_enrich

    def _enrich_graph_partners_with_sql(
        self,
        partners_to_enrich: list[dict[str, Any]],
        topic_keywords: str
    ) -> None:
        """
        Fetch project details from SQL for graph-only partners.

        Modifies partners in-place to add relevant_projects.
        """
        if not partners_to_enrich:
            return

        conn = self._get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            for partner in partners_to_enrich:
                org_name = partner.get('name', '')
                if not org_name:
                    continue

                # Query for this organization's projects matching keywords
                keywords = topic_keywords.split()
                keyword_conditions = []
                params = [org_name]

                for kw in keywords[:3]:  # Limit to first 3 keywords
                    keyword_conditions.append("(p.objective ILIKE %s OR p.title ILIKE %s)")
                    params.extend([f"%{kw}%", f"%{kw}%"])

                keyword_where = f"({' OR '.join(keyword_conditions)})" if keyword_conditions else "TRUE"

                sql = f"""
                    SELECT p.acronym, p.title, o.role, o."ecContribution", p."startDate",
                           p."frameworkProgramme" as programme
                    FROM organizations o
                    JOIN projects p ON o."projectID" = p.id
                    WHERE o.name = %s
                    AND p."frameworkProgramme" IN ('HORIZON', 'H2020')
                    AND {keyword_where}
                    ORDER BY p."startDate" DESC NULLS LAST
                    LIMIT 5
                """

                cursor.execute(sql, params)
                results = cursor.fetchall()

                if results:
                    projects_list = []
                    for r in results:
                        projects_list.append({
                            "acronym": r.get('acronym', 'N/A'),
                            "title": (r.get('title') or '')[:60] + ('...' if len(r.get('title') or '') > 60 else ''),
                            "role": r.get('role', 'participant'),
                            "funding": round(float(r.get('ecContribution') or 0), 0),
                            "start_date": str(r.get('startDate', ''))[:10] if r.get('startDate') else None
                        })

                    partner['relevant_projects'] = projects_list
                    partner['found_in_sources'].append('sql_enriched')
                    logger.debug(f"Enriched {org_name} with {len(projects_list)} projects")

            cursor.close()
            conn.close()

        except Exception as e:
            logger.warning(f"Failed to enrich graph partners: {e}")

    def _calculate_experience_score(
        self,
        relevant_projects: int,
        as_coordinator: int,
        total_projects: int,
        funding: float
    ) -> float:
        """Calculate experience/expertise score for ranking."""
        score = 0.0

        # Relevant project count (max 0.4)
        score += min(relevant_projects / 10, 0.4)

        # Coordinator experience bonus (max 0.25)
        score += min(as_coordinator / 5, 0.25)

        # Total HE experience (max 0.15)
        score += min(total_projects / 50, 0.15)

        # Funding received (max 0.2)
        score += min(funding / 10_000_000, 0.2)

        return round(min(score, 1.0), 2)

    def _generate_insights(
        self,
        partners: list[dict],
        keywords: str
    ) -> dict[str, Any]:
        """Generate aggregated insights from results."""
        if not partners:
            return {}

        # Most common partner types
        type_counts = {}
        country_counts = {}
        total_relevant = 0

        for p in partners:
            org_type = p.get('type', 'Unknown')
            country = p.get('country', 'Unknown')
            relevant = p.get('track_record', {}).get('relevant_projects', 0)

            type_counts[org_type] = type_counts.get(org_type, 0) + 1
            country_counts[country] = country_counts.get(country, 0) + 1
            total_relevant += relevant

        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "most_common_partner_types": [t[0] for t in sorted_types[:3]],
            "top_countries_in_topic": [c[0] for c in sorted_countries[:5]],
            "total_relevant_projects_found": total_relevant,
            "average_projects_per_org": round(total_relevant / max(len(partners), 1), 1)
        }

    def _generate_search_tips(
        self,
        partners: list[dict],
        keywords: str,
        country: str | None,
        organization_type: str | None = None
    ) -> list[str]:
        """Generate helpful search tips."""
        tips = []

        if len(partners) < 5:
            tips.append("Consider broadening your search with more general keywords")

        if not country and partners:
            # Suggest top country
            countries = [p.get('country') for p in partners if p.get('country')]
            if countries:
                from collections import Counter
                top_country = Counter(countries).most_common(1)[0][0]
                tips.append(f"Most experienced partners in this area are from {top_country}")

        # Note about SME data
        if organization_type and organization_type.lower() in ['sme', 'smes', 'small', 'startup']:
            tips.append("Note: CORDIS classifies SMEs under 'Private Companies' (PRC). Results show companies which may include SMEs.")

        # Coordinator tip
        coordinators = [p for p in partners if p.get('track_record', {}).get('as_coordinator', 0) > 0]
        if coordinators:
            tips.append(f"{len(coordinators)} organizations have coordination experience in this area")

        return tips

    def _get_fallback_response(self, keywords: str) -> dict[str, Any]:
        """Return fallback when database unavailable."""
        return {
            "success": False,
            "tool_name": "find_experienced_partners",
            "query_params": {"topic_keywords": keywords},
            "total_found": 0,
            "experienced_partners": [],
            "message": "Database unavailable - cannot search for partners",
            "suggestions": [
                "Check database connection",
                "Try again later"
            ],
            "data_source": "fallback",
            "timestamp": datetime.now().isoformat()
        }


# Async wrapper for tool orchestrator compatibility
async def find_experienced_partners_execute(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """
    Execute partner discovery tool.

    This tool finds organizations with proven track records in Horizon Europe and H2020 topics.
    Use when users want to find potential consortium partners, identify experienced coordinators,
    or discover organizations working in a specific research area.

    Uses HYBRID approach combining:
    - Graph (Neo4j): Relationship-based discovery + 2-hop partners
    - SQL (PostgreSQL): Precise keyword matching + project details
    Results are merged using Reciprocal Rank Fusion (RRF).
    """
    # Extract cluster with fallback alternatives (LLM might use different parameter names)
    cluster_param = (
        params.get('cluster') or
        params.get('cluster_code') or
        params.get('cluster_id') or
        params.get('pillar')
    )

    # Extract programme filter with fallback alternatives
    # Supports: 'HORIZON', 'H2020', 'both', 'all', or None (default: both)
    programme_param = (
        params.get('programme') or
        params.get('framework_programme') or
        params.get('framework')
    )
    # Normalize 'all' to 'both'
    if programme_param and programme_param.lower() == 'all':
        programme_param = 'both'

    tool = PartnerDiscoveryTool()

    topic_keywords = params.get('topic_keywords') or params.get('keywords', '')
    if not topic_keywords:
        return {
            "success": False,
            "error": "topic_keywords is required",
            "tool_name": "find_experienced_partners"
        }

    return tool.find_partners(
        topic_keywords=topic_keywords,
        country=params.get('country'),
        organization_type=params.get('organization_type'),
        cluster=cluster_param,
        min_projects=params.get('min_projects', 2),
        role_filter=params.get('role_filter'),
        limit=params.get('limit', 20),
        include_2hop=params.get('include_2hop', True),
        programme=programme_param
    )


async def get_collaboration_network_execute(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """
    Get the collaboration network for a specific organization.

    This tool shows which organizations have partnered with a target organization
    across Horizon Europe projects. Useful for:
    - Understanding an organization's partnership landscape
    - Finding potential partners through existing networks
    - Identifying key collaborators in a research area
    """
    tool = PartnerDiscoveryTool()

    organization_name = params.get('organization_name') or params.get('name', '')
    if not organization_name:
        return {
            "success": False,
            "error": "organization_name is required",
            "tool_name": "get_collaboration_network"
        }

    return tool.get_collaboration_network(
        organization_name=organization_name,
        depth=params.get('depth', 1),
        limit=params.get('limit', 30)
    )
