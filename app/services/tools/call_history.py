"""
Call History Analysis Tool for Horizon Europe.

ENHANCED with Hybrid Graph+SQL Architecture:
- Uses Neo4j graph database for pre-aggregated funding trends
- Uses PostgreSQL for detailed filtering and keyword-based search
- Parallel query execution for performance
- Cluster inference from keywords
- Topic evolution and landscape analysis
- AI-powered keyword expansion for broader scope searches

Analyzes historical funding patterns for specific topic areas, showing what got
funded, when, and under which calls. Helps users understand funding landscape
and identify trends.
"""

import os
import logging
import re
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Import Gemini for AI-powered keyword expansion
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

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

# Cluster to CLUSTER-N mapping for graph queries
CLUSTER_TO_GRAPH = {
    'CL1': 'CLUSTER-1',
    'CL2': 'CLUSTER-2',
    'CL3': 'CLUSTER-3',
    'CL4': 'CLUSTER-4',
    'CL5': 'CLUSTER-5',
    'CL6': 'CLUSTER-6',
}

# Keyword to cluster mapping for automatic cluster inference
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


class CallHistoryTool:
    """
    Tool to analyze historical funding patterns for Horizon Europe.

    ENHANCED with Hybrid Graph+SQL Architecture:
    - Graph service (Neo4j) for pre-aggregated trends and topic landscape
    - SQL service (PostgreSQL) for detailed filtering and keyword search
    - Parallel query execution for performance
    - Cluster inference from keywords
    """

    def __init__(self):
        """Initialize with database connection and graph service."""
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.warning("DATABASE_URL not set - call history analysis will be limited")

        # Initialize graph service with graceful fallback
        self._graph_service = None
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            self._graph_service = GraphSearchService()
            logger.info("✅ Graph service available for call history analysis")
        except Exception as e:
            logger.warning(f"⚠️ Graph service not available for call history analysis: {e}")

        # Initialize Gemini for AI-powered keyword expansion
        self._gemini_model = None
        if GEMINI_AVAILABLE:
            try:
                api_key = os.getenv('GEMINI_API_KEY')
                if api_key:
                    genai.configure(api_key=api_key)
                    model_name = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')
                    self._gemini_model = genai.GenerativeModel(model_name)
                    logger.info(f"✅ Gemini available for keyword expansion (model: {model_name})")
            except Exception as e:
                logger.warning(f"⚠️ Gemini not available for keyword expansion: {e}")

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _normalize_cluster(self, cluster: str) -> str:
        """Normalize cluster code."""
        cluster_upper = cluster.upper().replace(' ', '').replace('-', '')
        return CLUSTER_MAP.get(cluster_upper, cluster.upper())

    def _cluster_to_graph_code(self, cluster: str) -> Optional[str]:
        """Convert cluster code to graph format (CLUSTER-N)."""
        normalized = self._normalize_cluster(cluster)
        return CLUSTER_TO_GRAPH.get(normalized, normalized if normalized.startswith('CLUSTER-') else None)

    def _infer_clusters_from_keywords(self, keywords: str) -> List[str]:
        """Infer clusters from keywords for more targeted search."""
        if not keywords:
            return []

        # Handle both string and list inputs for keywords
        if isinstance(keywords, list):
            keywords_lower = ' '.join(str(k) for k in keywords).lower()
        else:
            keywords_lower = str(keywords).lower()
        inferred = []

        for cluster, kw_list in CLUSTER_KEYWORDS.items():
            for kw in kw_list:
                if kw.lower() in keywords_lower:
                    if cluster not in inferred:
                        inferred.append(cluster)
                    break

        return inferred

    # Common keyword expansions for fallback when AI fails
    FALLBACK_EXPANSIONS = {
        'ai': ['artificial intelligence', 'AI', 'machine learning', 'deep learning', 'neural network',
               'computer vision', 'natural language processing', 'NLP', 'predictive analytics',
               'data-driven', 'intelligent systems', 'automated', 'cognitive computing'],
        'artificial intelligence': ['artificial intelligence', 'AI', 'machine learning', 'deep learning',
                                   'neural network', 'computer vision', 'NLP', 'intelligent systems'],
        'hydrogen': ['hydrogen', 'H2', 'fuel cell', 'electrolyzer', 'green hydrogen', 'clean hydrogen',
                    'hydrogen storage', 'hydrogen production', 'power-to-gas', 'FCEV'],
        'battery': ['battery', 'energy storage', 'lithium-ion', 'solid-state battery', 'EV battery',
                   'battery management', 'BMS', 'cell chemistry', 'gigafactory'],
        'quantum': ['quantum', 'quantum computing', 'quantum communication', 'quantum sensing',
                   'qubit', 'quantum cryptography', 'quantum algorithms'],
        'climate': ['climate', 'climate change', 'decarbonization', 'net-zero', 'greenhouse gas',
                   'carbon neutral', 'climate adaptation', 'climate mitigation'],
        'cybersecurity': ['cybersecurity', 'cyber security', 'information security', 'data protection',
                         'threat detection', 'encryption', 'secure systems', 'privacy'],
        'robotics': ['robotics', 'robot', 'autonomous systems', 'industrial automation', 'cobots',
                    'manipulation', 'mobile robotics', 'human-robot interaction'],
    }

    def _expand_keywords_with_ai(self, keywords: str) -> List[str]:
        """
        Use AI to expand keywords to include related terms for broader scope searches.

        For example, "AI" → ["artificial intelligence", "AI", "machine learning",
        "deep learning", "neural network", "computer vision", "NLP", etc.]

        This allows finding projects that USE a technology rather than just focus on it.
        Falls back to predefined expansions if AI fails.
        """
        # Handle list input
        if isinstance(keywords, list):
            original_keywords = ', '.join(keywords)
        else:
            original_keywords = keywords

        # Check for fallback expansion first (common topics)
        keywords_lower = original_keywords.lower().strip()
        for key, expansion in self.FALLBACK_EXPANSIONS.items():
            if key in keywords_lower or keywords_lower == key:
                logger.info(f"🔍 Using fallback expansion for '{original_keywords}': {len(expansion)} terms")
                return expansion

        if not self._gemini_model:
            logger.warning("⚠️ Gemini not available - using original keywords only")
            return [original_keywords]

        prompt = f"""You are a research topic expert helping to find EU research projects. Given a topic keyword, expand it to include all related terms, techniques, methods, and applications.

Task: Expand the topic "{original_keywords}" into related search terms.

Requirements:
- Include the original term(s)
- Add synonyms, acronyms, and full forms
- Add specific techniques, methods, and sub-fields
- Add common applications and use cases
- Keep each term concise (1-3 words)
- Return 10-20 related terms
- Focus on terms likely to appear in scientific research titles or descriptions

Return ONLY a JSON array of strings. Example: ["term1", "term2", "term3"]"""

        try:
            response = self._gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=500,
                )
            )

            # Try to get text, handle blocked responses
            try:
                response_text = response.text.strip()
            except Exception:
                # Response might be blocked - check for candidates
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            for part in candidate.content.parts:
                                if hasattr(part, 'text'):
                                    response_text = part.text.strip()
                                    break
                else:
                    raise ValueError("No valid response from AI")

            # Parse JSON response
            # Handle markdown code blocks if present
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1])  # Remove first and last lines

            expanded = json.loads(response_text)

            if isinstance(expanded, list) and len(expanded) > 0:
                logger.info(f"🔍 AI expanded '{original_keywords}' to {len(expanded)} terms: {expanded[:5]}...")
                return expanded
            else:
                logger.warning(f"⚠️ AI expansion returned unexpected format, using original")
                return [original_keywords]

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Failed to parse AI expansion response: {e}")
            return [original_keywords]
        except Exception as e:
            logger.warning(f"⚠️ AI keyword expansion failed: {e}, using original")
            return [original_keywords]

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
        include_topic_evolution: bool = True,
        include_cluster_trends: bool = True,
        strict_match: bool = True,  # Use stricter keyword matching
        expand_scope: bool = False,  # NEW: Expand keywords to include related terms
        limit: int = 500
    ) -> Dict[str, Any]:
        """
        Analyze historical funding patterns for specific topic areas.

        ENHANCED with Hybrid Graph+SQL Architecture:
        - Uses graph database for pre-aggregated trends (faster)
        - Uses SQL for detailed filtering and keyword search
        - Parallel query execution for performance
        - Cluster inference from keywords
        - Strict matching mode for accurate topic-specific results
        - AI-powered keyword expansion for broader scope searches

        Args:
            topic_pattern: Topic code pattern (e.g., "HORIZON-CL4-2023")
            cluster: Cluster code (e.g., "CL4", "CL5", "CLUSTER-4")
            keywords: Keywords to search in call titles/descriptions
            year_from: Starting year filter
            year_to: Ending year filter
            action_types: Filter by action types (RIA, IA, CSA)
            include_projects: Include funded project examples
            include_topic_evolution: Include topic landscape analysis from graph
            include_cluster_trends: Include cluster-level trends from graph
            strict_match: Use stricter keyword matching (title-focused, word boundaries)
            expand_scope: Use AI to expand keywords to related terms (for "projects using X" queries)
            limit: Max results per query

        Returns:
            Comprehensive analysis of funding history with graph-enhanced insights
        """
        try:
            # Handle keyword expansion for broader scope searches
            original_keywords = keywords
            expanded_keywords_list = None
            if expand_scope and keywords:
                expanded_keywords_list = self._expand_keywords_with_ai(keywords)
                # Join expanded keywords for search (using comma separation)
                keywords = ', '.join(expanded_keywords_list)
                # When expanding scope, don't use strict_match (we want broader results)
                strict_match = False
                # Also don't auto-apply cluster filter (we want cross-cluster results)
                logger.info(f"🔍 Expanded scope: '{original_keywords}' → {len(expanded_keywords_list)} related terms")

            # Normalize cluster if provided
            normalized_cluster = None
            graph_cluster = None
            if cluster:
                normalized_cluster = self._normalize_cluster(cluster)
                graph_cluster = self._cluster_to_graph_code(cluster)

            # Infer clusters from keywords if no cluster specified
            inferred_clusters = []
            if not cluster and keywords:
                inferred_clusters = self._infer_clusters_from_keywords(keywords)
                if inferred_clusters:
                    graph_cluster = inferred_clusters[0]  # Use first inferred cluster for graph queries
                    logger.info(f"Inferred clusters from keywords: {inferred_clusters}")

            # For AI-specific queries, auto-apply cluster filter for better accuracy
            # BUT NOT when expand_scope is True (user wants broader results)
            effective_cluster = normalized_cluster
            if not cluster and keywords and strict_match and not expand_scope:
                # Check if this is an AI-specific query
                keywords_lower = keywords.lower() if isinstance(keywords, str) else ' '.join(keywords).lower()
                ai_keywords = ['artificial intelligence', ' ai ', 'ai,', ',ai', 'machine learning', 'deep learning', 'neural network']
                if any(kw in keywords_lower or keywords_lower.startswith('ai') for kw in ai_keywords):
                    # Auto-apply CL4 (Digital) cluster for AI queries
                    effective_cluster = 'CL4'
                    if not graph_cluster:
                        graph_cluster = 'CLUSTER-4'
                    logger.info(f"Auto-applied CL4 cluster filter for AI-specific query")

            # Use hybrid approach if graph service available
            # Now also trigger for keyword searches (not just cluster)
            if self._graph_service and (graph_cluster or topic_pattern or keywords):
                return self._analyze_history_hybrid(
                    topic_pattern=topic_pattern,
                    cluster=effective_cluster,
                    graph_cluster=graph_cluster,
                    keywords=keywords,
                    year_from=year_from,
                    year_to=year_to,
                    action_types=action_types,
                    include_projects=include_projects,
                    include_topic_evolution=include_topic_evolution,
                    include_cluster_trends=include_cluster_trends,
                    inferred_clusters=inferred_clusters,
                    strict_match=strict_match,
                    expand_scope=expand_scope,
                    original_keywords=original_keywords,
                    expanded_keywords_list=expanded_keywords_list,
                    limit=limit
                )

            # Fallback to SQL-only analysis
            return self._analyze_history_sql(
                topic_pattern=topic_pattern,
                cluster=effective_cluster,
                keywords=keywords,
                year_from=year_from,
                year_to=year_to,
                action_types=action_types,
                include_projects=include_projects,
                strict_match=strict_match,
                limit=limit
            )

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

    def _analyze_history_hybrid(
        self,
        topic_pattern: Optional[str],
        cluster: Optional[str],
        graph_cluster: Optional[str],
        keywords: Optional[str],
        year_from: Optional[int],
        year_to: Optional[int],
        action_types: Optional[List[str]],
        include_projects: bool,
        include_topic_evolution: bool,
        include_cluster_trends: bool,
        inferred_clusters: List[str],
        strict_match: bool = True,
        expand_scope: bool = False,
        original_keywords: Optional[str] = None,
        expanded_keywords_list: Optional[List[str]] = None,
        limit: int = 500
    ) -> Dict[str, Any]:
        """
        Hybrid Graph+SQL analysis for funding history.

        Uses parallel queries to graph and SQL for comprehensive analysis.
        With strict_match=True, uses stricter keyword matching for accuracy.
        """
        results = {
            'graph': {},
            'sql': {}
        }

        # Execute graph and SQL queries in parallel
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {}

            # Graph queries (if graph service available)
            if self._graph_service:
                if include_cluster_trends and graph_cluster:
                    futures['graph_trends'] = executor.submit(
                        self._get_graph_funding_trends,
                        graph_cluster
                    )

                if include_topic_evolution and graph_cluster:
                    futures['graph_topics'] = executor.submit(
                        self._get_graph_topic_landscape,
                        graph_cluster,
                        topic_pattern
                    )

                if graph_cluster:
                    futures['graph_stats'] = executor.submit(
                        self._get_graph_cluster_statistics,
                        graph_cluster
                    )

                # NEW: Graph-based keyword search for projects
                # This gives much better results than SQL ILIKE for semantic queries
                if keywords:
                    futures['graph_projects'] = executor.submit(
                        self._get_graph_projects_by_keywords,
                        keywords,
                        graph_cluster,
                        limit
                    )

                    # Also get funding trends for keyword-matched projects
                    futures['graph_keyword_trends'] = executor.submit(
                        self._get_graph_keyword_funding_trends,
                        keywords,
                        graph_cluster
                    )

            # SQL queries (as fallback/complement)
            futures['sql_calls'] = executor.submit(
                self._get_calls_history_sql,
                topic_pattern, cluster, keywords,
                year_from, year_to, action_types, limit,
                strict_match
            )

            futures['sql_timeline'] = executor.submit(
                self._get_timeline_aggregates_sql,
                topic_pattern, cluster, keywords,
                year_from, year_to,
                strict_match
            )

            if include_projects:
                futures['sql_projects'] = executor.submit(
                    self._get_funded_projects_sql,
                    topic_pattern, cluster, keywords,
                    year_from, year_to, limit,
                    strict_match
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

        # Merge and format results
        return self._merge_history_results(
            results,
            topic_pattern=topic_pattern,
            cluster=cluster,
            graph_cluster=graph_cluster,
            keywords=keywords,
            year_from=year_from,
            year_to=year_to,
            action_types=action_types,
            inferred_clusters=inferred_clusters,
            include_projects=include_projects,
            expand_scope=expand_scope,
            original_keywords=original_keywords,
            expanded_keywords_list=expanded_keywords_list
        )

    def _get_graph_funding_trends(self, cluster: str) -> Optional[List[Dict]]:
        """Get funding trends from graph database."""
        if not self._graph_service:
            return None

        try:
            trends = self._graph_service.get_funding_trends(
                cluster_code=cluster,
                group_by='year'
            )
            return trends
        except Exception as e:
            logger.warning(f"Graph funding trends query failed: {e}")
            return None

    def _get_graph_topic_landscape(
        self,
        cluster: str,
        topic_pattern: Optional[str] = None
    ) -> Optional[Dict]:
        """Get topic landscape and evolution from graph."""
        if not self._graph_service:
            return None

        try:
            result = {}

            # Get all topics in cluster
            topics = self._graph_service.get_topics_by_cluster(cluster, limit=100)
            if topics:
                result['total_topics'] = len(topics)
                result['top_topics'] = topics[:15]

                # Analyze topic distribution by year (from topic codes)
                topic_years = defaultdict(int)
                for topic in topics:
                    code = topic.get('code', '')
                    year = self._extract_year_from_topic(code)
                    if year:
                        topic_years[year] += 1

                result['topics_by_year'] = dict(sorted(topic_years.items(), reverse=True))

            # Search for related topics if pattern provided
            if topic_pattern:
                related = self._graph_service.search_topics(topic_pattern, limit=20)
                result['related_topics'] = related

            return result
        except Exception as e:
            logger.warning(f"Graph topic landscape query failed: {e}")
            return None

    def _get_graph_cluster_statistics(self, cluster: str) -> Optional[Dict]:
        """Get cluster statistics from graph."""
        if not self._graph_service:
            return None

        try:
            stats = self._graph_service.get_cluster_statistics(cluster_code=cluster)
            if stats:
                return stats[0] if isinstance(stats, list) and len(stats) > 0 else stats
            return None
        except Exception as e:
            logger.warning(f"Graph cluster statistics query failed: {e}")
            return None

    def _get_graph_projects_by_keywords(
        self,
        keywords: str,
        cluster: Optional[str],
        limit: int
    ) -> Optional[List[Dict]]:
        """
        Get projects matching keywords using graph database.

        Much more effective than SQL ILIKE for semantic queries because:
        - Graph uses regex patterns that match word boundaries better
        - Can traverse relationships (project -> topic -> cluster)
        - Better for multi-word queries
        """
        if not self._graph_service:
            return None

        try:
            # Handle both string and list inputs for keywords
            if isinstance(keywords, list):
                keyword_list = [k.strip() for k in keywords if k and k.strip()]
            else:
                keyword_list = [k.strip() for k in str(keywords).split(',') if k.strip()]

            # Use graph service's keyword search
            projects = self._graph_service.search_projects_by_keywords(
                keywords=keyword_list,
                status=None,  # Get all statuses
                limit=limit
            )

            if projects:
                logger.info(f"📊 Graph keyword search found {len(projects)} projects for '{keywords}'")

            return projects

        except Exception as e:
            logger.warning(f"Graph keyword project search failed: {e}")
            return None

    def _get_graph_keyword_funding_trends(
        self,
        keywords: str,
        cluster: Optional[str]
    ) -> Optional[Dict]:
        """
        Get funding trends for keyword-matched projects from graph.

        Calculates year-by-year funding for projects matching keywords.
        """
        if not self._graph_service:
            return None

        try:
            # Handle both string and list inputs for keywords
            if isinstance(keywords, list):
                keyword_list = [k.strip() for k in keywords if k and k.strip()]
            else:
                keyword_list = [k.strip() for k in str(keywords).split(',') if k.strip()]

            # Build word boundary patterns for short keywords (like "AI") to avoid false positives
            # Neo4j regex uses \\b for word boundaries
            pattern_parts = []
            for kw in keyword_list:
                kw_lower = kw.lower()
                if len(kw) <= 3:
                    # Short keywords need word boundary matching
                    pattern_parts.append(f"\\\\b{kw_lower}\\\\b")
                else:
                    # Longer keywords can use partial match
                    pattern_parts.append(kw_lower)
            search_pattern = '|'.join(pattern_parts)

            # Build query to get funding by year for matching projects
            keyword_where = f"(toLower(p.title) =~ '.*({search_pattern}).*' OR toLower(p.objective) =~ '.*({search_pattern}).*')"

            if cluster:
                # If cluster filter is provided, use MATCH instead of OPTIONAL MATCH
                query = f"""
                MATCH (p:Project)-[:TARGETS]->(c:Cluster)
                WHERE {keyword_where}
                  AND p.startDate IS NOT NULL
                  AND c.code = $cluster

                WITH p,
                     substring(p.startDate, 0, 4) as year

                RETURN year,
                       COUNT(p) as project_count,
                       SUM(p.ecMaxContribution) as total_funding,
                       AVG(p.ecMaxContribution) as avg_funding,
                       COLLECT(DISTINCT p.fundingScheme) as funding_schemes
                ORDER BY year DESC
                """
                params = {'cluster': cluster}
            else:
                # No cluster filter - use OPTIONAL MATCH
                query = f"""
                MATCH (p:Project)
                WHERE {keyword_where}
                  AND p.startDate IS NOT NULL
                OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)

                WITH p,
                     substring(p.startDate, 0, 4) as year

                RETURN year,
                       COUNT(p) as project_count,
                       SUM(p.ecMaxContribution) as total_funding,
                       AVG(p.ecMaxContribution) as avg_funding,
                       COLLECT(DISTINCT p.fundingScheme) as funding_schemes
                ORDER BY year DESC
                """
                params = {}
            results = self._graph_service.db.execute_query(query, params)

            if results:
                trends = {
                    'by_year': {},
                    'total_projects': 0,
                    'total_funding': 0
                }

                for r in results:
                    year = r.get('year')
                    if year and year.isdigit():
                        year_int = int(year)
                        project_count = r.get('project_count', 0)
                        total_funding = r.get('total_funding', 0) or 0
                        avg_funding = r.get('avg_funding', 0) or 0

                        trends['by_year'][year_int] = {
                            'projects': project_count,
                            'total_funding': total_funding,
                            'avg_funding': avg_funding,
                            'funding_schemes': r.get('funding_schemes', [])
                        }
                        trends['total_projects'] += project_count
                        trends['total_funding'] += total_funding

                logger.info(f"📊 Graph keyword trends: {trends['total_projects']} projects, €{trends['total_funding']/1_000_000:.0f}M")
                return trends

            return None

        except Exception as e:
            logger.warning(f"Graph keyword funding trends query failed: {e}")
            return None

    def _get_graph_cluster_statistics_old(self, cluster: str) -> Optional[Dict]:
        """Get cluster statistics from graph (original method kept for reference)."""
        if not self._graph_service:
            return None

        try:
            stats = self._graph_service.get_cluster_statistics(cluster_code=cluster)
            if stats:
                return stats[0] if isinstance(stats, list) and len(stats) > 0 else stats
            return None
        except Exception as e:
            logger.warning(f"Graph cluster statistics query failed: {e}")
            return None

    def _get_calls_history_sql(
        self,
        topic_pattern: Optional[str],
        cluster: Optional[str],
        keywords: Optional[str],
        year_from: Optional[int],
        year_to: Optional[int],
        action_types: Optional[List[str]],
        limit: int,
        strict_match: bool = True
    ) -> List[Dict]:
        """Get calls from funding_calls table (SQL).

        With strict_match=True:
        - Prioritizes title matches over scope/outcome
        - Uses word boundary matching where possible
        """
        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

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
                # Handle both string and list inputs for keywords
                if isinstance(keywords, list):
                    keyword_list = [k.strip() for k in keywords if k and k.strip()]
                else:
                    keyword_list = [k.strip() for k in str(keywords).split(',') if k.strip()]
                if keyword_list:
                    keyword_conditions = []
                    for kw in keyword_list:
                        if strict_match:
                            # Strict mode: Use word boundary matching with regex for short keywords
                            # and require match in title OR (scope AND outcome) for better precision
                            if len(kw) <= 3:  # Short keywords like "AI" need word boundary
                                # PostgreSQL regex for word boundary: \m for start, \M for end
                                keyword_conditions.append(
                                    "(title ~* %s OR (scope ~* %s AND expected_outcome ~* %s))"
                                )
                                word_pattern = f"\\m{kw}\\M"  # Word boundary match
                                params.extend([word_pattern, word_pattern, word_pattern])
                            else:
                                # Longer keywords: title match OR both scope and outcome
                                keyword_conditions.append(
                                    "(title ILIKE %s OR (scope ILIKE %s AND expected_outcome ILIKE %s))"
                                )
                                params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
                        else:
                            # Non-strict: Original behavior - match anywhere
                            keyword_conditions.append("(title ILIKE %s OR scope ILIKE %s OR expected_outcome ILIKE %s)")
                            params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
                    # Use OR to match ANY of the keywords
                    where_conditions.append(f"({' OR '.join(keyword_conditions)})")

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

            cursor.close()
            conn.close()
            return calls

        except Exception as e:
            logger.error(f"SQL calls history query failed: {e}")
            if conn:
                conn.close()
            return []

    def _get_timeline_aggregates_sql(
        self,
        topic_pattern: Optional[str],
        cluster: Optional[str],
        keywords: Optional[str],
        year_from: Optional[int],
        year_to: Optional[int],
        strict_match: bool = True
    ) -> Dict[int, Dict]:
        """Get aggregated timeline data from SQL (no limit)."""
        conn = self._get_connection()
        if not conn:
            return {}

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            where_clause, params = self._build_where_clause(
                topic_pattern, cluster, keywords, year_from, year_to, strict_match
            )

            sql = f"""
                SELECT
                    EXTRACT(YEAR FROM "startDate")::int as year,
                    COUNT(*) as project_count,
                    SUM("ecMaxContribution") as total_funding,
                    AVG("ecMaxContribution") as avg_funding,
                    COUNT(DISTINCT "fundingScheme") as scheme_count
                FROM projects
                WHERE {where_clause}
                  AND "startDate" IS NOT NULL
                GROUP BY EXTRACT(YEAR FROM "startDate")
                ORDER BY year DESC
            """

            cursor.execute(sql, params)
            results = cursor.fetchall()

            timeline = {}
            total_projects = 0
            total_funding = 0.0
            for r in results:
                year = r['year']
                if year:
                    timeline[year] = {
                        "projects_funded": int(r['project_count'] or 0),
                        "total_funding": float(r['total_funding'] or 0),
                        "avg_project_budget": round(float(r['avg_funding'] or 0), 0),
                        "calls": 0,  # Will be updated from calls data
                        "key_topics": []
                    }
                    total_projects += timeline[year]["projects_funded"]
                    total_funding += timeline[year]["total_funding"]

            logger.info(f"📊 SQL timeline query: cluster={cluster}, keywords={keywords}, strict={strict_match}")
            logger.info(f"📊 SQL timeline results: {total_projects} projects, €{total_funding/1e6:.0f}M")

            cursor.close()
            conn.close()
            return timeline

        except Exception as e:
            logger.error(f"SQL timeline aggregates query failed: {e}")
            if conn:
                conn.close()
            return {}

    def _get_funded_projects_sql(
        self,
        topic_pattern: Optional[str],
        cluster: Optional[str],
        keywords: Optional[str],
        year_from: Optional[int],
        year_to: Optional[int],
        limit: int,
        strict_match: bool = True
    ) -> List[Dict]:
        """Get funded projects matching criteria (SQL)."""
        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            where_clause, params = self._build_where_clause(
                topic_pattern, cluster, keywords, year_from, year_to, strict_match
            )

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

            cursor.close()
            conn.close()
            return projects

        except Exception as e:
            logger.error(f"SQL funded projects query failed: {e}")
            if conn:
                conn.close()
            return []

    def _merge_history_results(
        self,
        results: Dict[str, Any],
        topic_pattern: Optional[str],
        cluster: Optional[str],
        graph_cluster: Optional[str],
        keywords: Optional[str],
        year_from: Optional[int],
        year_to: Optional[int],
        action_types: Optional[List[str]],
        inferred_clusters: List[str],
        include_projects: bool,
        expand_scope: bool = False,
        original_keywords: Optional[str] = None,
        expanded_keywords_list: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Merge graph and SQL results into comprehensive response."""

        calls = results['sql'].get('calls', [])
        timeline = results['sql'].get('timeline', {})
        projects = results['sql'].get('projects', []) if include_projects else []

        graph_trends = results['graph'].get('trends')
        graph_topics = results['graph'].get('topics')
        graph_stats = results['graph'].get('stats')

        # NEW: Get graph keyword search results
        graph_projects = results['graph'].get('projects', [])
        graph_keyword_trends = results['graph'].get('keyword_trends')

        # Merge graph projects with SQL projects (graph first, then SQL)
        if graph_projects:
            # Create a set of existing project IDs to avoid duplicates
            existing_ids = {p.get('id') for p in projects if p.get('id')}
            for gp in graph_projects:
                if gp.get('id') not in existing_ids:
                    projects.append(gp)
                    existing_ids.add(gp.get('id'))
            logger.info(f"📊 Merged {len(graph_projects)} graph projects with SQL results")

        # Use graph keyword trends if available (more accurate for keyword searches)
        if graph_keyword_trends and graph_keyword_trends.get('by_year'):
            keyword_timeline = graph_keyword_trends['by_year']
            # Merge or replace timeline with graph keyword results
            for year, data in keyword_timeline.items():
                if year not in timeline:
                    timeline[year] = {
                        "projects_funded": 0,
                        "total_funding": 0,
                        "avg_project_budget": 0,
                        "calls": 0,
                        "key_topics": []
                    }
                # Use graph data as it's more accurate for keyword searches
                timeline[year]["projects_funded"] = max(
                    timeline[year]["projects_funded"],
                    data.get('projects', 0)
                )
                timeline[year]["total_funding"] = max(
                    timeline[year]["total_funding"],
                    data.get('total_funding', 0)
                )
                if data.get('avg_funding'):
                    timeline[year]["avg_project_budget"] = data['avg_funding']
            logger.info(f"📊 Enhanced timeline with graph keyword trends")

        # Check if we have any results now
        if not calls and not timeline and not graph_trends and not graph_keyword_trends:
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
                ],
                "metadata": {
                    "search_type": "hybrid",
                    "sources_used": ["graph", "sql"] if self._graph_service else ["sql"],
                    "inferred_clusters": inferred_clusters
                }
            }

        # Update timeline with call counts
        for call in calls:
            year = call.get('year')
            if year and year in timeline:
                timeline[year]["calls"] += 1

        # Enhance timeline with graph trends if available
        # IMPORTANT: Only use cluster-wide graph_trends when there are NO keywords
        # When keywords are provided, graph_keyword_trends already has accurate filtered data
        # Using cluster-wide trends would inflate the numbers significantly
        if graph_trends and not keywords:
            for trend in graph_trends:
                period = trend.get('period')
                if period and period.isdigit():
                    year = int(period)
                    if year not in timeline:
                        timeline[year] = {
                            "projects_funded": 0,
                            "total_funding": 0,
                            "avg_project_budget": 0,
                            "calls": 0,
                            "key_topics": []
                        }
                    # Update with graph data (may be more complete)
                    if trend.get('project_count'):
                        timeline[year]["projects_funded"] = max(
                            timeline[year]["projects_funded"],
                            trend['project_count']
                        )
                    if trend.get('total_funding'):
                        timeline[year]["total_funding"] = max(
                            timeline[year]["total_funding"],
                            trend['total_funding']
                        )

        # Analyze by action type
        by_action_type = self._analyze_by_action_type(calls, projects)

        # Identify top topics
        top_topics = self._identify_top_topics(projects)

        # Detect trends
        trends = self._detect_trends(timeline, projects, keywords)

        # Generate recommendations
        recommendations = self._generate_recommendations(trends, top_topics, cluster, keywords)

        # Calculate totals from timeline (accurate, not limited)
        total_funding = sum(t.get('total_funding', 0) for t in timeline.values())
        total_projects = sum(t.get('projects_funded', 0) for t in timeline.values())

        # Build response
        response = {
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
            "projects_funded": total_projects,
            "timeline": dict(sorted(timeline.items(), reverse=True)),
            "funding_by_action_type": by_action_type,
            "top_funded_topics": top_topics[:10],
            "trends": trends,
            "sample_funded_projects": self._format_sample_projects(projects[:8]),
            "recommendations": recommendations,
            "metadata": {
                "search_type": "hybrid",
                "sources_used": [],
                "graph_trends_available": graph_trends is not None,
                "graph_keyword_search_used": graph_keyword_trends is not None,
                "graph_projects_found": len(graph_projects) if graph_projects else 0,
                "sql_projects_found": len(results['sql'].get('projects', [])),
                "total_projects_merged": len(projects),
                "inferred_clusters": inferred_clusters,
                "scope_expanded": expand_scope,
                "original_keywords": original_keywords if expand_scope else None,
                "expanded_keywords": expanded_keywords_list if expand_scope else None
            },
            "timestamp": datetime.now().isoformat()
        }

        # Track sources used
        if graph_trends or graph_topics or graph_stats or graph_keyword_trends or graph_projects:
            response["metadata"]["sources_used"].append("graph")
        if calls or results['sql'].get('timeline') or results['sql'].get('projects'):
            response["metadata"]["sources_used"].append("sql")

        # Add topic landscape from graph if available
        if graph_topics:
            response["topic_landscape"] = {
                "total_topics": graph_topics.get('total_topics', 0),
                "top_topics": graph_topics.get('top_topics', [])[:10],
                "topics_by_year": graph_topics.get('topics_by_year', {}),
                "related_topics": graph_topics.get('related_topics', [])[:10] if topic_pattern else []
            }

        # Add cluster statistics from graph if available
        if graph_stats:
            response["cluster_statistics"] = {
                "cluster_code": graph_stats.get('code'),
                "cluster_name": graph_stats.get('name'),
                "total_projects": graph_stats.get('project_count'),
                "total_funding": graph_stats.get('total_funding'),
                "avg_budget": graph_stats.get('avg_budget'),
                "funding_schemes": graph_stats.get('funding_schemes', [])
            }

        return response

    def _analyze_history_sql(
        self,
        topic_pattern: Optional[str],
        cluster: Optional[str],
        keywords: Optional[str],
        year_from: Optional[int],
        year_to: Optional[int],
        action_types: Optional[List[str]],
        include_projects: bool,
        limit: int
    ) -> Dict[str, Any]:
        """SQL-only analysis (fallback when graph not available)."""
        conn = self._get_connection()
        if not conn:
            return {
                "success": False,
                "tool_name": "analyze_call_history",
                "error": "Database unavailable",
                "message": "Cannot analyze call history - database connection failed."
            }

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get calls from funding_calls table
        calls = self._get_calls_history_sql(
            topic_pattern, cluster, keywords,
            year_from, year_to, action_types, limit
        )

        # Get timeline aggregates (full data, no limit)
        timeline = self._get_timeline_aggregates_sql(
            topic_pattern, cluster, keywords,
            year_from, year_to
        )

        # Get funded projects (limited, for samples and detailed analysis)
        projects = []
        if include_projects:
            projects = self._get_funded_projects_sql(
                topic_pattern, cluster, keywords,
                year_from, year_to, limit
            )

        cursor.close()
        conn.close()

        if not calls and not timeline:
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
                ],
                "metadata": {
                    "search_type": "sql_only",
                    "sources_used": ["sql"]
                }
            }

        # Update timeline with call counts
        for call in calls:
            year = call.get('year')
            if year and year in timeline:
                timeline[year]["calls"] += 1

        # Analyze by action type
        by_action_type = self._analyze_by_action_type(calls, projects)

        # Identify top topics
        top_topics = self._identify_top_topics(projects)

        # Detect trends
        trends = self._detect_trends(timeline, projects, keywords)

        # Generate recommendations
        recommendations = self._generate_recommendations(trends, top_topics, cluster, keywords)

        # Calculate totals from timeline (accurate, not limited)
        total_funding = sum(t.get('total_funding', 0) for t in timeline.values())
        total_projects = sum(t.get('projects_funded', 0) for t in timeline.values())

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
            "projects_funded": total_projects,
            "timeline": dict(sorted(timeline.items(), reverse=True)),
            "funding_by_action_type": by_action_type,
            "top_funded_topics": top_topics[:10],
            "trends": trends,
            "sample_funded_projects": self._format_sample_projects(projects[:8]),
            "recommendations": recommendations,
            "metadata": {
                "search_type": "sql_only",
                "sources_used": ["sql"]
            },
            "timestamp": datetime.now().isoformat()
        }

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

    def _build_where_clause(
        self,
        topic_pattern: Optional[str],
        cluster: Optional[str],
        keywords: Optional[str],
        year_from: Optional[int],
        year_to: Optional[int],
        strict_match: bool = True
    ) -> tuple:
        """Build WHERE clause and params for project queries.

        With strict_match=True:
        - Short keywords (<=3 chars) use word boundary regex
        - Matches prioritize title over objective
        """
        where_conditions = ["\"frameworkProgramme\" = 'HORIZON'"]
        params = []

        if topic_pattern:
            where_conditions.append("topics ILIKE %s")
            params.append(f"%{topic_pattern}%")

        if cluster:
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
            # Handle both string and list inputs for keywords
            if isinstance(keywords, list):
                keyword_list = [k.strip() for k in keywords if k and k.strip()]
            else:
                keyword_list = [k.strip() for k in str(keywords).split(',') if k.strip()]
            if keyword_list:
                keyword_conditions = []
                for kw in keyword_list:
                    if strict_match:
                        # Strict mode: Use word boundary for short keywords, prioritize title
                        if len(kw) <= 3:  # Short keywords like "AI" need word boundary
                            # PostgreSQL regex for word boundary
                            keyword_conditions.append("(title ~* %s OR objective ~* %s)")
                            word_pattern = f"\\m{kw}\\M"  # Word boundary match
                            params.extend([word_pattern, word_pattern])
                        else:
                            # Longer keywords: standard ILIKE but prioritize title
                            keyword_conditions.append("(title ILIKE %s OR objective ILIKE %s)")
                            params.extend([f"%{kw}%", f"%{kw}%"])
                    else:
                        # Non-strict: Original behavior
                        keyword_conditions.append("(title ILIKE %s OR objective ILIKE %s)")
                        params.extend([f"%{kw}%", f"%{kw}%"])
                # Use OR to match ANY of the keywords
                where_conditions.append(f"({' OR '.join(keyword_conditions)})")

        if year_from:
            where_conditions.append("EXTRACT(YEAR FROM \"startDate\") >= %s")
            params.append(year_from)

        if year_to:
            where_conditions.append("EXTRACT(YEAR FROM \"startDate\") <= %s")
            params.append(year_to)

        return " AND ".join(where_conditions), params

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
                # Handle both list (from graph) and string (from SQL) formats
                if isinstance(topic, list):
                    # Graph returns topics as a list
                    main_topic = topic[0] if topic else ''
                else:
                    # SQL returns topics as semicolon-separated string
                    main_topic = str(topic).split(';')[0].strip()

                if not main_topic:
                    continue

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
        formatted = []
        for p in projects:
            # Handle topics which can be list (from graph) or string (from SQL)
            topics = p.get('topics', '')
            if isinstance(topics, list):
                topic_str = topics[0][:50] if topics else 'N/A'
            elif topics:
                topic_str = str(topics).split(';')[0][:50]
            else:
                topic_str = 'N/A'

            formatted.append({
                "acronym": p.get('acronym', 'N/A'),
                "title": p.get('title', '')[:80] + "..." if len(p.get('title', '')) > 80 else p.get('title', ''),
                "topic": topic_str,
                "eu_contribution": p.get('eu_contribution', 0),
                "start_date": p.get('start_date'),
                "action_type": p.get('action_type'),
                "cordis_url": f"https://cordis.europa.eu/project/id/{p.get('id')}"
            })
        return formatted

    def get_cluster_evolution(
        self,
        cluster: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        NEW METHOD: Analyze how a cluster has evolved over time.

        Uses graph service for comprehensive cluster analysis including:
        - Yearly funding trends
        - Topic evolution
        - Action type distribution changes
        """
        normalized_cluster = self._normalize_cluster(cluster)
        graph_cluster = self._cluster_to_graph_code(cluster)

        if not self._graph_service:
            # Fallback to SQL-based evolution
            return self._get_cluster_evolution_sql(normalized_cluster, year_from, year_to)

        try:
            result = {
                'success': True,
                'cluster': normalized_cluster,
                'graph_cluster': graph_cluster,
                'source': 'neo4j_graph'
            }

            # Get funding trends by year
            trends = self._graph_service.get_funding_trends(
                cluster_code=graph_cluster,
                group_by='year'
            )
            if trends:
                result['yearly_trends'] = trends

            # Get cluster statistics
            stats = self._graph_service.get_cluster_statistics(cluster_code=graph_cluster)
            if stats:
                result['statistics'] = stats[0] if isinstance(stats, list) and stats else stats

            # Get topic landscape
            topics = self._graph_service.get_topics_by_cluster(graph_cluster, limit=50)
            if topics:
                result['topic_landscape'] = {
                    'total_topics': len(topics),
                    'top_topics': topics[:15]
                }

            # Get budget statistics for the cluster
            budget_stats = self._graph_service.get_budget_statistics(
                cluster_code=graph_cluster
            )
            if budget_stats:
                result['budget_statistics'] = budget_stats[0] if isinstance(budget_stats, list) and budget_stats else budget_stats

            return result

        except Exception as e:
            logger.warning(f"Graph cluster evolution query failed: {e}")
            return self._get_cluster_evolution_sql(normalized_cluster, year_from, year_to)

    def _get_cluster_evolution_sql(
        self,
        cluster: str,
        year_from: Optional[int],
        year_to: Optional[int]
    ) -> Dict[str, Any]:
        """SQL fallback for cluster evolution analysis."""
        timeline = self._get_timeline_aggregates_sql(
            topic_pattern=None,
            cluster=cluster,
            keywords=None,
            year_from=year_from,
            year_to=year_to
        )

        trends = self._detect_trends(timeline, [], None)

        return {
            'success': True,
            'cluster': cluster,
            'yearly_trends': [
                {
                    'period': str(year),
                    'project_count': data['projects_funded'],
                    'total_funding': data['total_funding'],
                    'avg_budget': data['avg_project_budget']
                }
                for year, data in sorted(timeline.items(), reverse=True)
            ],
            'statistics': trends,
            'source': 'postgresql'
        }

    def get_topic_history(
        self,
        topic_pattern: str,
        include_similar: bool = True
    ) -> Dict[str, Any]:
        """
        NEW METHOD: Get detailed history for a specific topic or topic pattern.

        Args:
            topic_pattern: Topic code pattern (e.g., "HORIZON-CL5-2024-D3")
            include_similar: Include similar/related topics from graph
        """
        result = {
            'success': True,
            'topic_pattern': topic_pattern
        }

        # Get projects under this topic
        projects = self._get_funded_projects_sql(
            topic_pattern=topic_pattern,
            cluster=None,
            keywords=None,
            year_from=None,
            year_to=None,
            limit=100
        )

        result['projects_found'] = len(projects)
        result['total_funding'] = sum(p.get('eu_contribution', 0) for p in projects)
        result['sample_projects'] = self._format_sample_projects(projects[:10])

        # Get related topics from graph
        if include_similar and self._graph_service:
            try:
                related = self._graph_service.search_topics(topic_pattern, limit=20)
                result['related_topics'] = related
                result['source'] = 'hybrid'
            except Exception as e:
                logger.warning(f"Graph related topics query failed: {e}")
                result['source'] = 'sql_only'
        else:
            result['source'] = 'sql_only'

        return result


# Async wrapper for tool orchestrator compatibility
async def analyze_call_history_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute call history analysis tool.

    This tool analyzes historical funding patterns for Horizon Europe topics.
    Use when users want to understand funding trends, what got funded in the past,
    topic frequency, or funding evolution over time.

    ENHANCED with Hybrid Graph+SQL Architecture for:
    - Pre-aggregated funding trends from graph
    - Topic landscape and evolution analysis
    - Cluster-level statistics
    - Automatic cluster inference from keywords
    """
    # Extract cluster with fallback alternatives (LLM might use different parameter names)
    cluster_param = (
        params.get('cluster') or
        params.get('cluster_code') or
        params.get('cluster_id') or
        params.get('pillar')
    )

    tool = CallHistoryTool()

    return tool.analyze_history(
        topic_pattern=params.get('topic_pattern'),
        cluster=cluster_param,
        keywords=params.get('keywords'),
        year_from=params.get('year_from'),
        year_to=params.get('year_to'),
        action_types=params.get('action_types'),
        include_projects=params.get('include_projects', True),
        include_topic_evolution=params.get('include_topic_evolution', True),
        include_cluster_trends=params.get('include_cluster_trends', True),
        limit=params.get('limit', 50)
    )
