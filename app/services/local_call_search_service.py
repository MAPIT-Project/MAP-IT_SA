"""
Local Call Search Service

Searches for funding calls using locally ingested Work Programme documents.
No external API dependency - everything runs on your local data.

Architecture:
1. First tries `funding_calls` table (structured, fast, accurate)
2. Falls back to vector search if table has no results
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, date

import psycopg2
from psycopg2.extras import RealDictCursor

from .vector_search_service import VectorSearchService

logger = logging.getLogger(__name__)


@dataclass
class LocalCallResult:
    """Represents a call/topic found in local documents."""
    topic_code: Optional[str]
    title: str
    description: str
    source_document: str
    work_programme: str
    cluster: Optional[str]
    action_type: Optional[str]  # RIA, IA, CSA, etc.
    budget: Optional[str]
    deadline: Optional[str]
    relevance_score: float
    url: Optional[str] = None  # Constructed URL to EU portal
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'topic_code': self.topic_code,
            'title': self.title,
            'description': self.description,
            'source_document': self.source_document,
            'work_programme': self.work_programme,
            'cluster': self.cluster,
            'action_type': self.action_type,
            'budget': self.budget,
            'deadline': self.deadline,
            'relevance_score': self.relevance_score,
            'url': self.url
        }


class LocalCallSearchService:
    """
    Service to search for Horizon Europe calls using local Work Programme documents.
    
    This service:
    - Searches only locally ingested PDFs (Work Programmes, guides, etc.)
    - Extracts call codes, budgets, deadlines from document content
    - Returns structured results with source attribution
    - Works completely offline (no external API calls)
    """
    
    # Patterns to extract call information
    TOPIC_CODE_PATTERNS = [
        r'HORIZON-[A-Z0-9]+-\d{4}-[A-Z0-9-]+(?:-\d+)?',  # Standard: HORIZON-CL5-2025-D3-01-04
        r'HORIZON-EIC-\d{4}-[A-Z]+-\d+',  # EIC: HORIZON-EIC-2026-ACCELERATOR-01
        r'ERC-\d{4}-[A-Z]+',  # ERC: ERC-2026-STG
    ]
    
    # Action type patterns
    ACTION_TYPES = {
        'RIA': r'\bRIA\b|Research and Innovation Action',
        'IA': r'\bIA\b|Innovation Action[^s]',
        'CSA': r'\bCSA\b|Coordination and Support Action',
        'COFUND': r'\bCOFUND\b|Co-funded?',
        'MSCA-PF': r'MSCA.*Postdoctoral|Postdoctoral Fellowship',
        'MSCA-DN': r'MSCA.*Doctoral|Doctoral Network',
        'MSCA': r'\bMSCA\b|Marie Sk',
        'ERC-STG': r'ERC.*Starting|Starting Grant',
        'ERC-COG': r'ERC.*Consolidator|Consolidator Grant',
        'ERC-ADG': r'ERC.*Advanced|Advanced Grant',
        'ERC-POC': r'ERC.*Proof of Concept|Proof of Concept',
        'ERC': r'\bERC\b|European Research Council',
        'EIC-Accelerator': r'EIC Accelerator|Accelerator',
        'EIC-Pathfinder': r'EIC Pathfinder|Pathfinder',
        'EIC-Transition': r'EIC Transition|Transition',
        'EIC': r'\bEIC\b|European Innovation Council',
        'LUMP-SUM': r'Lump[- ]?Sum',
    }
    
    # Cluster mapping by keywords
    CLUSTER_KEYWORDS = {
        'CL1': ['health', 'cancer', 'pandemic', 'infectious disease', 'mental health', 'ageing', 'pharmaceutical'],
        'CL2': ['culture', 'creativity', 'inclusive', 'democracy', 'heritage', 'social', 'governance'],
        'CL3': ['security', 'cybersecurity', 'disaster', 'border', 'crime', 'terrorism', 'resilience'],
        'CL4': ['digital', 'AI', 'artificial intelligence', 'data', 'industry', 'space', 'manufacturing', 'robotics', 'quantum'],
        'CL5': ['climate', 'energy', 'mobility', 'transport', 'battery', 'hydrogen', 'renewable', 'clean', 'carbon', 'emission'],
        'CL6': ['food', 'bioeconomy', 'agriculture', 'biodiversity', 'environment', 'circular', 'ocean', 'soil', 'forest'],
    }
    
    # Work programme title mappings
    WP_TITLE_MAP = {
        'eic': 'EIC Work Programme 2026',
        'erc': 'ERC Work Programme 2026',
        'health': 'Cluster 1: Health',
        'culture': 'Cluster 2: Culture, Creativity & Inclusive Society',
        'inclusive': 'Cluster 2: Culture, Creativity & Inclusive Society',
        'security': 'Cluster 3: Civil Security for Society',
        'digital': 'Cluster 4: Digital, Industry and Space',
        'industry': 'Cluster 4: Digital, Industry and Space',
        'space': 'Cluster 4: Digital, Industry and Space',
        'climate': 'Cluster 5: Climate, Energy and Mobility',
        'energy': 'Cluster 5: Climate, Energy and Mobility',
        'mobility': 'Cluster 5: Climate, Energy and Mobility',
        'food': 'Cluster 6: Food, Bioeconomy & Environment',
        'bioeconomy': 'Cluster 6: Food, Bioeconomy & Environment',
        'widening': 'Widening Participation',
        'missions': 'Missions',
        'bauhaus': 'New European Bauhaus',
        'infrastructures': 'Research Infrastructures',
        'ecosystems': 'European Innovation Ecosystems',
        'general-annexes': 'General Annexes',
        'programme-guide': 'Horizon Europe Programme Guide',
    }
    
    def __init__(self):
        """Initialize the local call search service."""
        from ..core.config import settings

        self._db_url = settings.database_url
        self._structured_available = False
        self._enrichment_service = None
        self._embedding_service = None
        self._semantic_search_available = False

        # Try to check if funding_calls table exists
        try:
            conn = psycopg2.connect(self._db_url)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'funding_calls'
                )
            """)
            self._structured_available = cursor.fetchone()[0]

            if self._structured_available:
                cursor.execute("SELECT COUNT(*) FROM funding_calls")
                count = cursor.fetchone()[0]
                logger.info(f"✅ Structured call database available ({count} calls)")

                # Check if semantic search is available (embedding column exists and has data)
                cursor.execute("""
                    SELECT COUNT(*) FROM funding_calls WHERE embedding IS NOT NULL
                """)
                embedding_count = cursor.fetchone()[0]
                if embedding_count > 0:
                    self._semantic_search_available = True
                    logger.info(f"✅ Semantic search available ({embedding_count} calls with embeddings)")

                # Initialize enrichment service for on-demand API fetching
                try:
                    from .call_enrichment_service import CallEnrichmentService
                    self._enrichment_service = CallEnrichmentService(self._db_url)
                    logger.info("✅ Call enrichment service available (will fetch missing data from EU Portal)")
                except Exception as e:
                    logger.warning(f"Call enrichment service not available: {e}")

                # Initialize embedding service for semantic search
                if self._semantic_search_available:
                    try:
                        from .embedding_service import EmbeddingService
                        self._embedding_service = EmbeddingService()
                        logger.info("✅ Embedding service available for semantic search")
                    except Exception as e:
                        logger.warning(f"Embedding service not available: {e}")
                        self._semantic_search_available = False

            conn.close()
        except Exception as e:
            logger.warning(f"Structured call database not available: {e}")

        # Initialize graph service for relationship-based search
        self._graph_service = None
        try:
            from .data_intelligence.graph_service import GraphSearchService
            self._graph_service = GraphSearchService()
            logger.info("✅ Graph service available for relationship-based search")
        except Exception as e:
            logger.warning(f"Graph service not available: {e}")

        # Initialize vector service as fallback
        try:
            self.vector_service = VectorSearchService()
            self._available = True
            logger.info("✅ LocalCallSearchService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LocalCallSearchService: {e}")
            self._available = False

    def _normalize_call_status(self, call_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize call status based on actual deadline date.

        If a call has a deadline that has already passed, mark it as 'closed'
        regardless of what status the API or database reports.
        """
        deadline = call_dict.get('deadline')
        if not deadline:
            return call_dict

        # Parse deadline to date object for comparison
        deadline_date = None
        try:
            if isinstance(deadline, date) and not isinstance(deadline, datetime):
                # Already a date object
                deadline_date = deadline
            elif isinstance(deadline, datetime):
                # datetime object - extract date
                deadline_date = deadline.date()
            elif hasattr(deadline, 'strftime'):
                # Some other date-like object
                deadline_date = date(deadline.year, deadline.month, deadline.day)
            else:
                # String - parse it
                deadline_str = str(deadline)
                for fmt in ['%Y-%m-%d', '%d %B %Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        parsed = datetime.strptime(
                            deadline_str.split('T')[0] if 'T' in deadline_str else deadline_str,
                            fmt
                        )
                        deadline_date = parsed.date()
                        break
                    except ValueError:
                        continue
        except Exception:
            pass

        # If deadline has passed, mark as closed
        if deadline_date:
            today = date.today()
            if deadline_date < today:
                call_dict['status'] = 'closed'
                logger.debug(f"Status normalized to 'closed' for {call_dict.get('topic_code')} - deadline passed")

        return call_dict

    def search_calls(
        self,
        query: str,
        num_results: int = 10,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        include_closed: bool = False,
        year_filter: Optional[str] = None,
        use_semantic: bool = True
    ) -> Dict[str, Any]:
        """
        Search for calls matching the query in local Work Programme documents.

        Strategy:
        1. First try structured `funding_calls` table (fast, accurate keyword match)
        2. If no results, try semantic search (finds related concepts)
        3. Fall back to document vector search if needed

        Args:
            query: Search query (e.g., "clean energy", "hydrogen", "AI healthcare")
            num_results: Maximum number of results to return
            cluster: Optional filter by cluster (CL1-CL6)
            action_type: Optional filter by action type (RIA, IA, CSA, etc.)
            include_closed: If False, filter out calls from past years (default: False)
            year_filter: Only show calls from specific year (e.g., "2025", "2026")
            use_semantic: If True, use semantic search when keyword search fails

        Returns:
            Dict with 'calls' list and 'search_metadata'
        """
        if not self._available:
            return {
                'success': False,
                'error': 'Local call search service not available',
                'query': query,
                'calls_found': 0,
                'calls': []
            }

        # Get current date dynamically
        today = date.today()
        current_year = today.year
        logger.info(f"🔍 LOCAL SEARCH: '{query}' (cluster={cluster}, type={action_type}, include_closed={include_closed}, year={year_filter}, today={today})")

        # STRATEGY 1: Try structured database first (fast, accurate keyword match)
        if self._structured_available:
            structured_results = self._search_structured_calls(
                query=query,
                num_results=num_results,
                cluster=cluster,
                action_type=action_type,
                include_closed=include_closed,
                year_filter=int(year_filter) if year_filter else None,
                current_year=current_year
            )

            if structured_results and len(structured_results) > 0:
                logger.info(f"✅ Found {len(structured_results)} results from structured database")

                # Enhance with graph context (related clusters, experienced orgs)
                graph_context = self._search_graph_enhanced(query) if self._graph_service else None

                return {
                    'success': True,
                    'query': query,
                    'calls_found': len(structured_results),
                    'calls': [self._format_structured_call(c) for c in structured_results],
                    'current_date': today.isoformat(),
                    'search_metadata': {
                        'source': 'funding_calls_table',
                        'api_used': False,
                        'search_method': 'structured_fulltext',
                        'include_closed': include_closed,
                        'year_filter': year_filter,
                        'current_year': current_year,
                        'graph_context': graph_context if graph_context else None
                    }
                }

        # STRATEGY 2: Try semantic search (finds related concepts even without keyword match)
        if use_semantic and self._semantic_search_available:
            logger.info("🧠 Trying semantic search for cross-domain matching...")
            semantic_results = self._search_semantic_calls(
                query=query,
                num_results=num_results,
                include_closed=include_closed,
                similarity_threshold=0.4  # Adjust threshold as needed
            )

            if semantic_results and len(semantic_results) > 0:
                # Format results
                formatted_calls = []
                for c in semantic_results:
                    formatted = self._format_structured_call(c, enrich=False)
                    # Add semantic match info
                    formatted['match_type'] = 'semantic'
                    formatted['similarity_score'] = c.get('similarity_score', 0)
                    formatted_calls.append(formatted)

                logger.info(f"✅ Found {len(formatted_calls)} results via semantic search")

                # Enhance with graph context (related clusters, experienced orgs)
                graph_context = self._search_graph_enhanced(query)

                return {
                    'success': True,
                    'query': query,
                    'calls_found': len(formatted_calls),
                    'calls': formatted_calls,
                    'current_date': today.isoformat(),
                    'search_metadata': {
                        'source': 'funding_calls_table',
                        'api_used': False,
                        'search_method': 'semantic_similarity',
                        'include_closed': include_closed,
                        'year_filter': year_filter,
                        'current_year': current_year,
                        'note': 'Results found via semantic matching (related concepts)',
                        'graph_context': graph_context if graph_context else None
                    }
                }

        # STRATEGY 3: Try graph-enhanced search (find calls via related topics/clusters)
        if self._graph_service:
            logger.info("📊 Trying graph-enhanced search for relationship-based discovery...")
            graph_context = self._search_graph_enhanced(query)

            if graph_context.get('topic_codes_to_search'):
                # Search for calls matching topics found in the graph
                topic_calls = self._search_by_topic_codes(
                    graph_context['topic_codes_to_search'],
                    include_closed=include_closed
                )

                if topic_calls and len(topic_calls) > 0:
                    # Format results
                    formatted_calls = []
                    for c in topic_calls[:num_results]:
                        formatted = self._format_structured_call(c, enrich=False)
                        formatted['match_type'] = 'graph_relationship'
                        formatted_calls.append(formatted)

                    logger.info(f"✅ Found {len(formatted_calls)} results via graph-enhanced search")
                    return {
                        'success': True,
                        'query': query,
                        'calls_found': len(formatted_calls),
                        'calls': formatted_calls,
                        'current_date': today.isoformat(),
                        'search_metadata': {
                            'source': 'funding_calls_table',
                            'api_used': False,
                            'search_method': 'graph_enhanced',
                            'include_closed': include_closed,
                            'year_filter': year_filter,
                            'current_year': current_year,
                            'note': 'Results found via graph relationship analysis',
                            'related_clusters': graph_context.get('related_clusters', []),
                            'experienced_orgs': graph_context.get('experienced_orgs', [])[:5]
                        }
                    }

        # STRATEGY 4: Fall back to document vector search
        logger.info("📄 Falling back to document vector search...")
        
        # Build enhanced query for better recall
        if not include_closed and not year_filter:
            enhanced_query = self._enhance_query(query, cluster, action_type, current_year=current_year)
        else:
            enhanced_query = self._enhance_query(query, cluster, action_type, current_year=None)
        
        # Search vector database
        try:
            results = self.vector_service.hybrid_search(
                query=enhanced_query,
                num_results=num_results * 6,  # Get more for filtering/dedup
                vector_weight=0.4,  # Balance semantic and keyword
                similarity_threshold=0.3  # Lower threshold for better recall
            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'calls_found': 0,
                'calls': []
            }
        
        # Process results into call objects
        calls = []
        seen_codes = set()  # Deduplicate by topic code
        seen_content = set()  # Deduplicate by content hash
        
        for result in results:
            # Skip near-duplicate content
            content_hash = hash(result.content[:150])
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)
            
            # Extract call information
            call_info = self._extract_call_info(result)
            
            # Skip results without a proper topic code (low quality results)
            if not call_info.topic_code:
                logger.debug(f"Skipping result without topic code")
                continue
            
            # YEAR FILTERING - Only show current/upcoming calls by default
            if not include_closed:
                call_year = self._extract_year_from_call(call_info)
                if call_year and call_year < current_year:
                    logger.debug(f"Skipping old call {call_info.topic_code} (year={call_year})")
                    continue
            
            # Specific year filter
            if year_filter:
                call_year = self._extract_year_from_call(call_info)
                if not call_year or str(call_year) != str(year_filter):
                    continue
            
            # Skip if we've seen this topic code
            if call_info.topic_code in seen_codes:
                continue
            seen_codes.add(call_info.topic_code)
            
            # Apply filters
            if cluster:
                if call_info.cluster and cluster.upper() not in call_info.cluster.upper():
                    continue
            
            if action_type:
                if call_info.action_type and action_type.upper() not in call_info.action_type.upper():
                    continue
            
            calls.append(call_info)
            
            if len(calls) >= num_results:
                break
        
        logger.info(f"✅ Found {len(calls)} local results for '{query}' (filtered to current/upcoming)")

        # Convert to dicts and enrich results to get status/deadline
        formatted_calls = []
        for c in calls:
            call_dict = c.to_dict()

            # ALWAYS enrich if we have topic_code - we need status and deadline for filtering
            # Vector search results don't have status/deadline, so we must fetch from DB/API
            if self._enrichment_service and c.topic_code:
                logger.info(f"📡 Enriching vector result {c.topic_code}...")
                enriched = self._enrichment_service.get_call_details(c.topic_code)
                if enriched:
                    # Merge enriched data (status, deadline, better title/description)
                    call_dict = {**call_dict, **enriched}
                    logger.info(f"✅ Enriched {c.topic_code}: status={enriched.get('status')}, deadline={enriched.get('deadline')}")

            # Normalize status based on deadline (mark as closed if deadline passed)
            call_dict = self._normalize_call_status(call_dict)

            # Filter out closed calls if include_closed is False
            if not include_closed and call_dict.get('status') == 'closed':
                logger.info(f"🚫 Filtering out closed call {c.topic_code} (status=closed)")
                continue

            # Filter out calls with PAST deadlines (but allow NULL deadlines)
            deadline = call_dict.get('deadline')
            if not include_closed and deadline:
                # Check if deadline has passed
                try:
                    if isinstance(deadline, str):
                        from datetime import datetime
                        for fmt in ['%Y-%m-%d', '%d %B %Y', '%d/%m/%Y']:
                            try:
                                deadline_date = datetime.strptime(deadline, fmt).date()
                                break
                            except ValueError:
                                continue
                        else:
                            deadline_date = None
                    elif hasattr(deadline, 'date'):
                        deadline_date = deadline.date() if hasattr(deadline, 'date') else deadline
                    else:
                        deadline_date = deadline

                    if deadline_date and deadline_date < date.today():
                        logger.info(f"🚫 Filtering out call {c.topic_code} (deadline {deadline} has passed)")
                        continue
                except Exception as e:
                    logger.debug(f"Could not parse deadline for {c.topic_code}: {e}")

            formatted_calls.append(call_dict)

        # Build result with helpful message if no open calls found
        result = {
            'success': True,
            'query': query,
            'calls_found': len(formatted_calls),
            'calls': formatted_calls,
            'current_date': today.isoformat(),
            'search_metadata': {
                'source': 'local_work_programmes',
                'api_used': False,
                'search_method': 'vector_fallback',
                'enhanced_query': enhanced_query,
                'total_results_before_filter': len(results),
                'include_closed': include_closed,
                'year_filter': year_filter,
                'current_year': current_year,
                'filters_applied': {
                    'cluster': cluster,
                    'action_type': action_type
                }
            }
        }

        # Add helpful message when no open calls found but there were results before filtering
        if len(formatted_calls) == 0 and len(calls) > 0:
            result['message'] = (
                f"Found {len(calls)} calls matching your query, but none are currently open "
                f"(all have passed deadlines or are closed). "
                f"Consider checking the EU Funding & Tenders Portal for upcoming calls, "
                f"or search with include_closed=True to see past calls for reference."
            )

        return result
    
    def _search_structured_calls(
        self,
        query: str,
        num_results: int = 10,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        include_closed: bool = False,
        year_filter: Optional[int] = None,
        current_year: int = 2025
    ) -> List[Dict[str, Any]]:
        """
        Search the structured funding_calls table.

        Uses PostgreSQL full-text search for fast, accurate results.
        Also handles exact topic_code lookups (e.g., HORIZON-CL5-2026-02-D4-01).
        """
        try:
            conn = psycopg2.connect(self._db_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Check if query looks like a topic code (starts with HORIZON-)
            is_topic_code = query.upper().startswith('HORIZON-')

            # Build the query
            query_parts = ["SELECT * FROM funding_calls WHERE 1=1"]
            params = []

            # For topic code queries, use exact or LIKE match first
            if is_topic_code and query:
                query_parts.append("""
                    AND (
                        topic_code ILIKE %s
                        OR topic_code ILIKE %s
                    )
                """)
                params.append(query.upper())  # Exact match
                params.append(f"%{query.upper()}%")  # Partial match
            elif query:
                # Combined search: full-text search OR word-boundary-aware matching
                # For multi-word queries like "AI healthcare", ALL keywords must match (AND logic)
                words = [w.strip() for w in query.split() if len(w.strip()) >= 2]

                if words:
                    # First add the FTS query parameter
                    fts_param_index = len(params)
                    params.append(query)  # This will be used for plainto_tsquery

                    # Build conditions for each word with word-boundary awareness
                    # ALL words must match (AND logic) to avoid false positives
                    word_conditions = []
                    for word in words[:5]:  # Limit to first 5 words
                        # For short words (2-3 chars like "AI"), use word-boundary matching
                        # to avoid matching inside other words like "sustAInable"
                        if len(word) <= 3:
                            # Use regex word boundary matching for short words
                            # PostgreSQL regex: \m = word start, \M = word end
                            word_conditions.append(
                                "(topic_code ~* %s OR title ~* %s OR scope ~* %s OR expected_outcome ~* %s)"
                            )
                            word_boundary_pattern = f"\\m{word}\\M"
                            params.extend([word_boundary_pattern] * 4)
                        else:
                            # For longer words, simple ILIKE is fine
                            word_conditions.append(
                                "(topic_code ILIKE %s OR title ILIKE %s OR scope ILIKE %s OR expected_outcome ILIKE %s)"
                            )
                            params.extend([f"%{word}%"] * 4)

                    # Use AND to require ALL keywords match (not just any one)
                    query_parts.append(f"""
                        AND (
                            to_tsvector('english',
                                COALESCE(title, '') || ' ' ||
                                COALESCE(scope, '') || ' ' ||
                                COALESCE(expected_outcome, '')
                            ) @@ plainto_tsquery('english', %s)
                            OR ({' AND '.join(word_conditions)})
                        )
                    """)
                else:
                    # Fallback for empty query
                    query_parts.append("AND 1=1")
            
            # Cluster filter
            if cluster:
                query_parts.append("AND cluster = %s")
                params.append(cluster.upper())
            
            # Action type filter
            if action_type:
                query_parts.append("AND action_type = %s")
                params.append(action_type.upper())
            
            # Year and status filters - skip for topic code queries (we want to find it regardless)
            if not is_topic_code:
                # Year filter
                if year_filter:
                    query_parts.append("AND call_year = %s")
                    params.append(year_filter)
                elif not include_closed:
                    # Only current and future years
                    query_parts.append("AND call_year >= %s")
                    params.append(current_year)

                # Status filter - exclude closed calls and calls with PAST deadlines
                # But ALLOW calls with NULL deadlines (we'll try to enrich them)
                if not include_closed:
                    query_parts.append("""
                        AND status != 'closed'
                        AND (deadline IS NULL OR deadline >= CURRENT_DATE)
                    """)

            # Order by relevance and deadline
            if is_topic_code:
                # For topic code queries, order by exact match first
                query_parts.append("""
                    ORDER BY
                        CASE WHEN topic_code ILIKE %s THEN 0 ELSE 1 END,
                        deadline ASC NULLS LAST
                    LIMIT %s
                """)
                params.extend([query.upper(), num_results])
            else:
                # For text queries, order by full-text rank
                query_parts.append("""
                    ORDER BY
                        ts_rank(
                            to_tsvector('english',
                                COALESCE(title, '') || ' ' ||
                                COALESCE(scope, '') || ' ' ||
                                COALESCE(expected_outcome, '')
                            ),
                            plainto_tsquery('english', %s)
                        ) DESC,
                        deadline ASC NULLS LAST
                    LIMIT %s
                """)
                params.extend([query, num_results])

            full_query = " ".join(query_parts)
            logger.debug(f"Executing structured search: {full_query[:200]}...")
            cursor.execute(full_query, params)
            results = cursor.fetchall()

            conn.close()
            logger.info(f"Structured search returned {len(results)} results for '{query}'")
            return [dict(r) for r in results]

        except Exception as e:
            logger.error(f"Structured search failed: {e}")
            return []

    def _search_semantic_calls(
        self,
        query: str,
        num_results: int = 10,
        include_closed: bool = False,
        similarity_threshold: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        Search for calls using semantic similarity.

        This enables cross-domain queries like "AI in healthcare" to find
        relevant calls even if they don't contain the exact keywords.
        """
        if not self._semantic_search_available or not self._embedding_service:
            logger.debug("Semantic search not available")
            return []

        try:
            # Generate query embedding
            query_embedding = self._embedding_service.generate_query_embedding(query)

            if query_embedding is None or len(query_embedding) == 0:
                logger.warning("Failed to generate query embedding")
                return []

            # Search using vector similarity
            conn = psycopg2.connect(self._db_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build the semantic search query
            embedding_list = query_embedding.tolist()

            if include_closed:
                cursor.execute("""
                    SELECT
                        id, topic_code, title, scope, expected_outcome,
                        deadline, status, cluster, action_type, budget_total,
                        destination, portal_url, call_year,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM funding_calls
                    WHERE embedding IS NOT NULL
                    AND 1 - (embedding <=> %s::vector) > %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (embedding_list, embedding_list, similarity_threshold, embedding_list, num_results))
            else:
                cursor.execute("""
                    SELECT
                        id, topic_code, title, scope, expected_outcome,
                        deadline, status, cluster, action_type, budget_total,
                        destination, portal_url, call_year,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM funding_calls
                    WHERE embedding IS NOT NULL
                    AND status != 'closed'
                    AND (deadline IS NULL OR deadline >= CURRENT_DATE)
                    AND 1 - (embedding <=> %s::vector) > %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (embedding_list, embedding_list, similarity_threshold, embedding_list, num_results))

            results = cursor.fetchall()
            conn.close()

            logger.info(f"🧠 Semantic search returned {len(results)} results for '{query}' (threshold={similarity_threshold})")

            # Add semantic match indicator
            for r in results:
                r['match_type'] = 'semantic'
                r['similarity_score'] = r.get('similarity', 0)

            return [dict(r) for r in results]

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def _search_graph_enhanced(
        self,
        query: str,
        num_results: int = 10,
        include_closed: bool = False
    ) -> Dict[str, Any]:
        """
        Use graph database to enhance call search with relationship-based discovery.

        This finds:
        1. Calls in clusters related to the query (based on funded projects)
        2. Related topic codes from similar funded projects
        3. Experienced organizations in the domain

        Returns:
            Dict with 'related_clusters', 'related_topics', 'experienced_orgs'
        """
        if not self._graph_service:
            return {}

        try:
            result = {
                'related_clusters': [],
                'related_topics': [],
                'experienced_orgs': [],
                'topic_codes_to_search': []
            }

            # Map query terms to potential clusters
            cluster_keywords = {
                'CLUSTER-1': ['health', 'medical', 'clinical', 'disease', 'patient', 'healthcare', 'hospital', 'therapy', 'diagnosis', 'pharmaceutical', 'cancer', 'vaccine', 'drug'],
                'CLUSTER-2': ['culture', 'democracy', 'social', 'heritage', 'creative', 'inclusive', 'society', 'governance', 'media'],
                'CLUSTER-3': ['security', 'cybersecurity', 'border', 'crime', 'disaster', 'resilience', 'defence', 'terrorism'],
                'CLUSTER-4': ['digital', 'AI', 'artificial intelligence', 'data', 'industry', 'space', 'manufacturing', 'robotics', 'computing', 'machine learning', 'quantum', 'electronics'],
                'CLUSTER-5': ['climate', 'energy', 'mobility', 'transport', 'hydrogen', 'battery', 'renewable', 'green', 'carbon', 'solar', 'wind', 'electric vehicle'],
                'CLUSTER-6': ['food', 'agriculture', 'bioeconomy', 'biodiversity', 'ocean', 'environment', 'soil', 'water', 'forestry', 'marine']
            }

            query_lower = query.lower()
            matched_clusters = []

            for cluster_code, keywords in cluster_keywords.items():
                if any(kw in query_lower for kw in keywords):
                    matched_clusters.append(cluster_code)

            # If no cluster matched but query has meaningful keywords, search topics directly
            if not matched_clusters:
                # Extract meaningful words from query (2+ characters, not stopwords)
                stopwords = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been', 'this', 'with', 'from', 'what', 'how', 'who', 'where', 'when', 'which', 'find', 'search', 'looking'}
                keywords = [w.strip() for w in query_lower.split() if len(w.strip()) >= 2 and w.strip() not in stopwords]

                if keywords:
                    # Try to find topics matching any keyword
                    for keyword in keywords[:3]:  # Search up to 3 keywords
                        try:
                            topics = self._graph_service.search_topics(keyword, limit=5)
                            if topics:
                                result['related_topics'].extend(topics)
                                topic_codes = [t.get('code') for t in topics if t.get('code')]
                                result['topic_codes_to_search'].extend(topic_codes)
                                logger.info(f"📊 Graph: Found {len(topics)} topics for keyword '{keyword}'")
                        except Exception as e:
                            logger.debug(f"Topic search for '{keyword}' failed: {e}")

            if matched_clusters:
                result['related_clusters'] = matched_clusters
                logger.info(f"📊 Graph: Matched clusters from query: {matched_clusters}")

                # Get top organizations from matched clusters
                for cluster in matched_clusters[:2]:  # Limit to top 2 clusters
                    try:
                        top_orgs = self._graph_service.get_top_organizations(
                            cluster_code=cluster,
                            limit=5
                        )
                        if top_orgs:
                            result['experienced_orgs'].extend(top_orgs)
                    except Exception as e:
                        logger.warning(f"Failed to get top organizations for {cluster}: {e}")

                    # Get topics from the matched clusters (using BELONGS_TO relationship)
                    try:
                        cluster_topics = self._graph_service.get_topics_by_cluster(cluster, limit=10)
                        if cluster_topics:
                            result['related_topics'].extend(cluster_topics)
                            topic_codes = [t.get('code') for t in cluster_topics if t.get('code')]
                            result['topic_codes_to_search'].extend(topic_codes)
                            logger.info(f"📊 Graph: Found {len(cluster_topics)} topics in {cluster}")
                    except Exception as e:
                        logger.warning(f"Failed to get topics for {cluster}: {e}")

                # Also search for topic codes that match the query directly
                try:
                    topics = self._graph_service.search_topics(query, limit=10)
                    if topics:
                        result['related_topics'].extend(topics)
                        # Extract topic codes to search in funding_calls
                        topic_codes = [t.get('code') for t in topics if t.get('code')]
                        result['topic_codes_to_search'].extend(topic_codes)
                        logger.info(f"📊 Graph: Found {len(topics)} topics matching query")
                except Exception as e:
                    logger.warning(f"Failed to search topics: {e}")

            # Deduplicate topic codes
            result['topic_codes_to_search'] = list(set(result['topic_codes_to_search']))

            return result

        except Exception as e:
            logger.error(f"Graph-enhanced search failed: {e}")
            return {}

    def _search_by_topic_codes(
        self,
        topic_codes: List[str],
        include_closed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for calls matching specific topic codes from graph results.
        """
        if not topic_codes or not self._structured_available:
            return []

        try:
            conn = psycopg2.connect(self._db_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build query for multiple topic codes
            placeholders = ','.join(['%s'] * len(topic_codes))

            if include_closed:
                cursor.execute(f"""
                    SELECT id, topic_code, title, scope, expected_outcome,
                           deadline, status, cluster, action_type, budget_total,
                           destination, portal_url, call_year
                    FROM funding_calls
                    WHERE topic_code IN ({placeholders})
                    ORDER BY deadline ASC NULLS LAST
                """, topic_codes)
            else:
                cursor.execute(f"""
                    SELECT id, topic_code, title, scope, expected_outcome,
                           deadline, status, cluster, action_type, budget_total,
                           destination, portal_url, call_year
                    FROM funding_calls
                    WHERE topic_code IN ({placeholders})
                    AND status != 'closed'
                    AND (deadline IS NULL OR deadline >= CURRENT_DATE)
                    ORDER BY deadline ASC NULLS LAST
                """, topic_codes)

            results = cursor.fetchall()
            conn.close()

            logger.info(f"📊 Found {len(results)} calls matching graph topic codes")
            return [dict(r) for r in results]

        except Exception as e:
            logger.error(f"Topic code search failed: {e}")
            return []

    def get_graph_context(self, query: str) -> Dict[str, Any]:
        """
        Get enriched context from the graph for a query.

        Use this to provide additional insights alongside search results:
        - Which clusters are most relevant
        - Top organizations with expertise
        - Related funded projects
        """
        return self._search_graph_enhanced(query)

    def _format_structured_call(self, call: Dict[str, Any], enrich: bool = True) -> Dict[str, Any]:
        """
        Format a structured call result to match the expected output format.

        If enrich=True and data is incomplete, fetches from EU Portal API.
        """
        # Check if we need to enrich this call
        topic_code = call.get('topic_code')
        scope = call.get('scope') or ''
        title = call.get('title') or ''

        # Enrich if: scope is short OR title is missing/same as topic_code
        needs_enrichment = (
            len(scope) < 50 or
            len(title) < 20 or
            title == topic_code  # Title is just the call ID
        )

        if enrich and self._enrichment_service and needs_enrichment and topic_code:
            logger.info(f"📡 Enriching {topic_code} from EU Portal API (scope={len(scope)}, title='{title[:30]}...')...")
            enriched = self._enrichment_service.get_call_details(topic_code)
            if enriched:
                # Merge enriched data with original
                call = {**call, **enriched}
                logger.info(f"✅ Enriched {topic_code} successfully")
        
        # Format deadline and normalize status based on actual deadline date
        deadline_raw = call.get('deadline')
        deadline_date = None
        deadline_str = None

        if deadline_raw:
            # Parse deadline to date object for status check
            try:
                if isinstance(deadline_raw, date) and not isinstance(deadline_raw, datetime):
                    # Already a date object
                    deadline_date = deadline_raw
                    deadline_str = deadline_raw.strftime('%d %B %Y')
                elif isinstance(deadline_raw, datetime):
                    # datetime object
                    deadline_date = deadline_raw.date()
                    deadline_str = deadline_raw.strftime('%d %B %Y')
                elif hasattr(deadline_raw, 'strftime'):
                    # Some other date-like object
                    deadline_date = date(deadline_raw.year, deadline_raw.month, deadline_raw.day)
                    deadline_str = deadline_raw.strftime('%d %B %Y')
                else:
                    # String - parse it
                    deadline_str = str(deadline_raw)
                    for fmt in ['%Y-%m-%d', '%d %B %Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            parsed = datetime.strptime(
                                deadline_str.split('T')[0] if 'T' in deadline_str else deadline_str,
                                fmt
                            )
                            deadline_date = parsed.date()
                            # Reformat for display
                            deadline_str = parsed.strftime('%d %B %Y')
                            break
                        except ValueError:
                            continue
            except Exception:
                deadline_str = str(deadline_raw) if deadline_raw else None

        deadline = deadline_str

        # Normalize status: if deadline has passed, mark as closed regardless of stored status
        status = call.get('status', 'unknown')
        if deadline_date:
            today = date.today()
            if deadline_date < today:
                status = 'closed'
                logger.debug(f"Status corrected to 'closed' for {call.get('topic_code')} - deadline {deadline} has passed")

        # Format budget
        budget = call.get('budget_total')
        if budget:
            if isinstance(budget, str):
                budget = budget  # Already formatted
            elif budget >= 1_000_000:
                budget = f"EUR {budget / 1_000_000:.1f} million"
            else:
                budget = f"EUR {budget:,.0f}"
        
        return {
            'topic_code': call.get('topic_code'),
            'title': call.get('title'),
            'description': call.get('scope') or call.get('expected_outcome') or '',
            'expected_outcome': call.get('expected_outcome'),
            'scope': call.get('scope'),
            'source_document': call.get('source_document_title', ''),
            'work_programme': call.get('programme_part') or call.get('destination', ''),
            'cluster': call.get('cluster'),
            'action_type': call.get('action_type'),
            'budget': budget,
            'deadline': deadline,
            'status': status,  # Use normalized status (corrected by deadline)
            'relevance_score': 1.0,  # Structured results are always relevant
            'url': call.get('portal_url'),
            'call_year': call.get('call_year'),
            'expected_projects': call.get('expected_projects'),
            'enriched': call.get('enriched_from_api', False),
        }
    
    def get_call_details(self, topic_code: str) -> Optional[Dict[str, Any]]:
        """
        Get complete details for a specific call.

        Always tries to enrich with API data if local data is incomplete.
        """
        if not topic_code:
            return None

        topic_code = topic_code.upper().strip()
        logger.info(f"🔍 Getting call details for: {topic_code}")

        # First check local database
        local_call = self._get_local_call(topic_code)
        if local_call:
            logger.info(f"✅ Found {topic_code} in local database: {local_call.get('title', '')[:50]}")

        # If enrichment service available, get complete data from API
        if self._enrichment_service:
            logger.info(f"📡 Trying API enrichment for {topic_code}...")
            enriched = self._enrichment_service.get_call_details(topic_code)
            if enriched and (enriched.get('topic_code') or enriched.get('title')):
                logger.info(f"✅ Got API data for {topic_code}: {enriched.get('title', '')[:50]}")
                result = self._format_structured_call(enriched, enrich=False)
                if result and (result.get('topic_code') or result.get('title')):
                    return result
            else:
                logger.info(f"⚠️ No valid API data found for {topic_code}")

        # Fall back to local data
        if local_call:
            result = self._format_structured_call(local_call, enrich=False)
            if result and (result.get('topic_code') or result.get('title')):
                return result

        # Last resort: try vector search to find the call
        logger.info(f"🔎 Trying vector search for {topic_code}...")
        try:
            vector_results = self._vector_search.search_funding_calls(
                query=topic_code,
                limit=10
            )
            for call in vector_results:
                call_topic = (call.topic_code or '').upper()
                # Check for exact or partial match
                if topic_code in call_topic or call_topic in topic_code:
                    logger.info(f"✅ Found {call_topic} via vector search")
                    result = self._format_structured_call(call.to_dict(), enrich=True)
                    if result and (result.get('topic_code') or result.get('title')):
                        return result
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")

        logger.warning(f"❌ Could not find call details for {topic_code}")
        return None
    
    def _get_local_call(self, topic_code: str) -> Optional[Dict[str, Any]]:
        """Get call from local database with fuzzy matching for similar IDs."""
        try:
            conn = psycopg2.connect(self._db_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # First try exact match
            cursor.execute(
                "SELECT * FROM funding_calls WHERE topic_code = %s",
                (topic_code,)
            )
            result = cursor.fetchone()

            # If not found, try fuzzy matching for similar call IDs
            if not result:
                # Create a pattern for fuzzy matching - e.g., HORIZON-CL5-2026-D3-01 could match HORIZON-CL5-2026-02-D3-01
                # Extract parts of the topic code
                parts = topic_code.split('-')
                if len(parts) >= 3:
                    # Build a LIKE pattern with wildcards between parts
                    like_pattern = '%'.join(parts[:3]) + '%' + '%'.join(parts[3:]) if len(parts) > 3 else '%'.join(parts) + '%'
                    cursor.execute(
                        "SELECT * FROM funding_calls WHERE topic_code LIKE %s ORDER BY topic_code LIMIT 5",
                        (f"%{like_pattern}%",)
                    )
                    fuzzy_results = cursor.fetchall()
                    if fuzzy_results:
                        # Return the closest match
                        result = fuzzy_results[0]
                        logger.info(f"📍 Fuzzy matched {topic_code} to {result['topic_code']}")

            conn.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Database error: {e}")
            return None
    
    def _extract_year_from_call(self, call: LocalCallResult) -> Optional[int]:
        """Extract the year from a call's topic code or content."""
        # Try topic code first: HORIZON-CL5-2025-D3-01-04 -> 2025
        # Match any year from 2020-2039
        if call.topic_code:
            year_match = re.search(r'20(2[0-9]|3[0-9])', call.topic_code)
            if year_match:
                return int(year_match.group(0))
        
        # Try work programme name
        if call.work_programme:
            year_match = re.search(r'20(2[0-9]|3[0-9])', call.work_programme)
            if year_match:
                return int(year_match.group(0))
        
        # Try source document
        if call.source_document:
            year_match = re.search(r'20(2[0-9]|3[0-9])', call.source_document)
            if year_match:
                return int(year_match.group(0))
        
        return None
    
    def _enhance_query(
        self, 
        query: str, 
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        current_year: Optional[int] = None
    ) -> str:
        """Enhance the query with relevant context for better search."""
        parts = [query]
        
        # Add Horizon Europe context if not present
        if 'horizon' not in query.lower() and 'erc' not in query.lower() and 'eic' not in query.lower():
            parts.append("Horizon Europe funding call")
        
        # Add cluster keywords if specified
        if cluster and cluster.upper() in self.CLUSTER_KEYWORDS:
            keywords = self.CLUSTER_KEYWORDS[cluster.upper()][:2]
            parts.extend(keywords)
        
        # Add action type context
        if action_type:
            parts.append(action_type)
        
        # Bias toward current/upcoming years
        if current_year:
            parts.append(f"{current_year}")
            parts.append(f"{current_year + 1}")
        
        return " ".join(parts)
    
    def _extract_call_info(self, result) -> LocalCallResult:
        """Extract call information from a search result."""
        content = result.content
        doc_title = result.document_title or ""
        
        # Extract topic code AND title together
        # Format: "HORIZON-CL5-2025-02-D3-15: Building a Long-Term Africa Union..."
        topic_code = None
        call_title = None
        
        for pattern in self.TOPIC_CODE_PATTERNS:
            # Try to match topic code followed by title
            title_pattern = f'({pattern})[:\\s]+([^\\n\\.]+(?:\\([^)]+\\))?[^\\n]*)'
            title_match = re.search(title_pattern, content, re.IGNORECASE)
            if title_match:
                topic_code = title_match.group(1).upper()
                raw_title = title_match.group(2).strip()
                # Clean the title - remove page numbers, truncate at reasonable length
                call_title = self._clean_call_title(raw_title)
                break
            
            # Fallback: just get the topic code
            matches = re.findall(pattern, content)
            if matches:
                topic_code = matches[0].upper()
                break
        
        # Extract action type
        action_type = None
        for atype, pattern in self.ACTION_TYPES.items():
            if re.search(pattern, content, re.IGNORECASE):
                action_type = atype
                break
        
        # Detect cluster from document title or content
        cluster = self._detect_cluster(doc_title, content)
        
        # Extract budget (look for EUR patterns)
        budget = self._extract_budget(content)
        
        # Extract deadline - with validation against call year
        call_year = self._extract_year_from_topic_code(topic_code)
        deadline = self._extract_deadline(content, call_year)
        
        # Generate title - prefer extracted title, fall back to topic code
        if call_title and len(call_title) > 10:
            title = call_title
        elif topic_code:
            title = topic_code
        elif result.section_title:
            title = result.section_title[:100]
        else:
            title = self._generate_title_from_content(content)
        
        # Get description - try to extract content relevant to THIS specific call
        description = self._extract_relevant_description(content, topic_code, call_title)
        
        # Get work programme name
        work_programme = self._get_work_programme_name(doc_title)
        
        # Construct URL if we have a topic code
        url = self._construct_portal_url(topic_code)
        
        return LocalCallResult(
            topic_code=topic_code,
            title=title,
            description=description,
            source_document=doc_title,
            work_programme=work_programme,
            cluster=cluster,
            action_type=action_type,
            budget=budget,
            deadline=deadline,
            relevance_score=result.score,
            url=url
        )
    
    def _clean_call_title(self, raw_title: str) -> str:
        """Clean up extracted call title."""
        title = raw_title
        
        # Remove "Call: Cluster X Call..." pattern and everything after
        title = re.sub(r'\s*Call:\s*Cluster.*$', '', title, flags=re.IGNORECASE)
        
        # Remove action type indicators at the start (RIA, IA, CSA followed by numbers)
        title = re.sub(r'^(RIA|IA|CSA|COFUND)\s+[\d\.]+\s*', '', title)
        
        # Remove budget info (numbers followed by Around/million)
        title = re.sub(r'\s*[\d\.]+\s*(Around|million|EUR).*$', '', title, flags=re.IGNORECASE)
        
        # Remove "Specific conditions..." and everything after
        title = re.sub(r'\s*Specific conditions.*$', '', title, flags=re.IGNORECASE)
        
        # Remove "Expected EU..." and everything after
        title = re.sub(r'\s*Expected EU.*$', '', title, flags=re.IGNORECASE)
        
        # Remove "The Commission estimates..." and everything after
        title = re.sub(r'\s*The Commission.*$', '', title, flags=re.IGNORECASE)
        
        # Remove "Overview of this call..." 
        title = re.sub(r'\s*Overview of this call.*$', '', title, flags=re.IGNORECASE)
        
        # Remove page references
        title = re.sub(r'\s*\[Page \d+\].*$', '', title)
        title = re.sub(r'\s*Part \d+.*$', '', title)
        
        # Remove trailing dots, colons, or special chars
        title = re.sub(r'[\.\s:]+$', '', title)
        title = re.sub(r'^[\.\s:]+', '', title)
        
        # Truncate if too long but keep reasonable length for descriptive titles
        if len(title) > 120:
            # Try to cut at a word boundary
            title = title[:120]
            last_space = title.rfind(' ')
            if last_space > 80:
                title = title[:last_space]
            title = title + '...'
        
        return title.strip()
    
    def _extract_year_from_topic_code(self, topic_code: Optional[str]) -> Optional[int]:
        """Extract year from topic code like HORIZON-CL5-2025-... -> 2025"""
        if not topic_code:
            return None
        match = re.search(r'20(2[0-9]|3[0-9])', topic_code)
        return int(match.group(0)) if match else None
    
    def _construct_portal_url(self, topic_code: Optional[str]) -> Optional[str]:
        """Construct EU Portal URL from topic code."""
        if not topic_code:
            return None
        
        # EU Portal URL pattern for topic details
        base_url = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details"
        
        # Clean the topic code
        clean_code = topic_code.strip().upper()
        
        # Validate it looks like a real topic code
        if re.match(r'^HORIZON-[A-Z0-9]+-\d{4}', clean_code):
            return f"{base_url}/{clean_code}"
        elif re.match(r'^ERC-\d{4}', clean_code):
            return f"{base_url}/{clean_code}"
        
        return None
    
    def _detect_cluster(self, doc_title: str, content: str) -> Optional[str]:
        """Detect which cluster this content belongs to."""
        combined = (doc_title + " " + content).lower()
        
        # Check document title first (most reliable)
        for cl, keywords in self.CLUSTER_KEYWORDS.items():
            for kw in keywords:
                if kw in doc_title.lower():
                    return cl
        
        # Check content
        cluster_scores = {}
        for cl, keywords in self.CLUSTER_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                cluster_scores[cl] = score
        
        if cluster_scores:
            return max(cluster_scores, key=cluster_scores.get)
        
        return None
    
    def _extract_budget(self, content: str) -> Optional[str]:
        """Extract budget information from content."""
        # Look for various budget patterns
        patterns = [
            r'EUR\s*([\d,\.]+)\s*(million|billion|M|B)?',
            r'€\s*([\d,\.]+)\s*(million|billion|M|B)?',
            r'budget[:\s]+EUR?\s*([\d,\.]+)\s*(million|billion|M|B)?',
            r'([\d,\.]+)\s*(million|billion)\s*EUR',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                amount = match.group(1).replace(',', '')
                # Skip if amount is empty or only contains dots
                if not amount or not amount.replace('.', ''):
                    continue
                unit = match.group(2) if len(match.groups()) > 1 else ''
                if unit:
                    return f"EUR {amount} {unit}"
                try:
                    if float(amount.replace('.', '')) > 1000:
                        return f"EUR {amount}"
                except ValueError:
                    # Skip invalid amounts
                    continue

        return None
    
    def _extract_deadline(self, content: str, call_year: Optional[int] = None) -> Optional[str]:
        """
        Extract deadline information from content.
        Only returns deadlines that match the call year (or current/future years).
        """
        # Patterns that capture the full date with year
        # Format examples: "Deadline(s): 02 Sep 2025", "Deadline: 04 September 2025"
        patterns = [
            # "Deadline(s): 02 Sep 2025" - most common format in Work Programmes
            r'[Dd]eadline\(?s?\)?[:\s]+(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
            # "closes: 15 January 2026"
            r'[Cc]loses?[:\s]+(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
            # Date formats like "02/09/2025"
            r'[Dd]eadline\(?s?\)?[:\s]+(\d{1,2}/\d{1,2}/\d{4})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Validate the year in the deadline
                year_match = re.search(r'(20\d{2})', match)
                if year_match:
                    deadline_year = int(year_match.group(1))
                    
                    # If we know the call year, deadline should be same year or +1
                    if call_year:
                        if deadline_year >= call_year and deadline_year <= call_year + 1:
                            return match
                    else:
                        # No call year known - accept any current/future deadline
                        if deadline_year >= 2025:
                            return match
        
        # If no valid deadline found, return None (don't show misleading dates)
        return None
    
    def _generate_title_from_content(self, content: str) -> str:
        """Generate a title from content if no topic code found."""
        # Take first sentence or meaningful phrase
        sentences = content.split('.')
        if sentences:
            first = sentences[0].strip()
            if len(first) > 10 and len(first) < 150:
                return first
        
        # Fall back to first N words
        words = content.split()[:10]
        return " ".join(words) + "..."
    
    def _extract_relevant_description(
        self, 
        content: str, 
        topic_code: Optional[str],
        call_title: Optional[str]
    ) -> str:
        """
        Extract description that's actually relevant to the specific call.
        Looks for content near the topic code or after specific markers.
        """
        # If we have a topic code, try to find description near it
        if topic_code:
            # Look for "Scope:" or "Expected Outcome:" sections after the topic code
            scope_patterns = [
                rf'{re.escape(topic_code)}[^S]*Scope[:\s]+([^E]{{100,600}})',
                rf'{re.escape(topic_code)}[^E]*Expected Outcome[s]?[:\s]+([^\n]{{100,400}})',
                rf'{re.escape(topic_code)}[:\s]+[^\.]+\.\s*([A-Z][^\.]+(?:\.[^\.]+){{0,3}})',
            ]
            
            for pattern in scope_patterns:
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    desc = match.group(1).strip()
                    return self._clean_description(desc)
        
        # Look for general scope/outcome sections
        scope_match = re.search(
            r'(?:Scope|Expected Outcome|Objective)[s]?[:\s]+([A-Z][^\.]{50,400}(?:\.[^\.]{20,200})?)',
            content, 
            re.IGNORECASE
        )
        if scope_match:
            return self._clean_description(scope_match.group(1))
        
        # Fallback: use content after the title if available
        if call_title and call_title in content:
            idx = content.find(call_title) + len(call_title)
            remaining = content[idx:idx+500].strip()
            # Skip past any metadata
            remaining = re.sub(r'^[:\s\d\.]+', '', remaining)
            if len(remaining) > 50:
                return self._clean_description(remaining)
        
        # Last resort: clean first part of content
        return self._clean_description(content[:400])
    
    def _clean_description(self, text: str) -> str:
        """Clean up description text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove page markers
        text = re.sub(r'\[Page \d+\]', '', text)
        
        # Remove common noise patterns
        text = re.sub(r'Part \d+ - Page \d+ of \d+', '', text)
        text = re.sub(r'Horizon Europe - Work Programme \d+', '', text)
        text = re.sub(r'\.{3,}', '', text)  # Remove ....
        text = re.sub(r'\s+', ' ', text).strip()  # Clean up again
        
        # Truncate if needed, try to end at sentence
        if len(text) > 350:
            text = text[:350]
            last_period = text.rfind('.')
            if last_period > 200:
                text = text[:last_period + 1]
            else:
                text = text + "..."
        
        return text
    
    def _get_work_programme_name(self, doc_title: str) -> str:
        """Convert document title to friendly work programme name."""
        if not doc_title:
            return "Horizon Europe Work Programme"
        
        title_lower = doc_title.lower()
        
        # Check title map
        for key, name in self.WP_TITLE_MAP.items():
            if key in title_lower:
                return name
        
        # Clean up the title
        clean = doc_title.replace('_', ' ').replace('-', ' ')
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        return clean or "Horizon Europe Work Programme"
    
    def get_call_details(self, topic_code: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific call by its topic code.
        
        Args:
            topic_code: The call identifier (e.g., HORIZON-CL5-2025-D3-01-04)
        
        Returns:
            Detailed call information or None if not found
        """
        if not self._available:
            return None
        
        logger.info(f"🔍 Looking up call: {topic_code}")
        
        # Search specifically for this topic code
        results = self.vector_service.hybrid_search(
            query=topic_code,
            num_results=10,
            vector_weight=0.2  # Prioritize keyword match
        )
        
        # Find chunks containing the topic code
        relevant_chunks = []
        for r in results:
            if topic_code.upper() in r.content.upper():
                relevant_chunks.append(r)
        
        if not relevant_chunks:
            return {
                'success': False,
                'error': f'Call {topic_code} not found in local documents',
                'call': None
            }
        
        # Combine information from all relevant chunks
        combined_content = "\n\n---\n\n".join([c.content for c in relevant_chunks[:5]])
        
        call_info = self._extract_call_info(relevant_chunks[0])
        call_info.description = self._clean_description(combined_content[:2000])
        
        return {
            'success': True,
            'call': call_info.to_dict(),
            'source_chunks': len(relevant_chunks),
            'source': 'local_work_programmes'
        }
    
    def search_by_cluster(self, cluster: str, num_results: int = 10) -> Dict[str, Any]:
        """Search for all calls in a specific cluster."""
        cluster_names = {
            'CL1': 'health',
            'CL2': 'culture creativity inclusive society',
            'CL3': 'security cybersecurity',
            'CL4': 'digital AI industry space',
            'CL5': 'climate energy mobility transport',
            'CL6': 'food bioeconomy agriculture environment',
        }
        
        query = cluster_names.get(cluster.upper(), cluster)
        return self.search_calls(query, num_results=num_results, cluster=cluster)

