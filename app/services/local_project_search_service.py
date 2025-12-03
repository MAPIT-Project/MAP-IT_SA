"""
Local-first project search service.

Combines PostgreSQL full-text search, Neo4j graph queries, and vector semantic search
for comprehensive project discovery without relying on external APIs.

Architecture:
1. PostgreSQL (cordis_processed.projects_enriched) - Full-text search + structured filters
2. Neo4j Graph - Relationship-based discovery (similar projects, org collaborations)
3. Vector Search (optional) - Semantic similarity on project objectives

Results are fused using Reciprocal Rank Fusion (RRF) for optimal ranking.
"""

import os
import re
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class ProjectSearchResult:
    """Unified project search result."""
    project_id: str
    rcn: str
    title: str
    acronym: Optional[str]
    objective: str
    start_date: str
    end_date: str
    status: str
    total_cost: float
    ec_contribution: float
    programme: str
    funding_scheme: str
    topics: str
    coordinator_name: Optional[str]
    coordinator_country: Optional[str]
    participant_count: int
    country_count: int
    sme_count: int
    participant_countries: List[str]
    relevance_score: float
    data_source: str
    cordis_url: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class LocalProjectSearchService:
    """
    Multi-source local project search service.
    
    Search strategy:
    1. Parse query for implicit filters (countries, dates, programmes)
    2. Run parallel searches: PostgreSQL full-text, Neo4j graph
    3. Fuse results using Reciprocal Rank Fusion (RRF)
    4. Deduplicate and rank
    
    No external API calls - 100% local data!
    """
    
    # Stopwords to remove from search terms
    STOPWORDS = {
        'find', 'show', 'me', 'get', 'search', 'for', 'about', 'in', 'from', 'with',
        'projects', 'project', 'calls', 'call', 'funding', 'grants', 'grant',
        'has', 'have', 'had', 'are', 'is', 'was', 'were', 'been', 'being',
        'coordinated', 'coordinating', 'participated', 'participating',
        'what', 'which', 'where', 'when', 'who', 'how', 'why',
        'the', 'a', 'an', 'and', 'or', 'but', 'if', 'then', 'else',
        'some', 'any', 'all', 'each', 'every', 'this', 'that', 'these', 'those',
        'to', 'of', 'on', 'at', 'by', 'for', 'with', 'from', 'into', 'onto',
        'can', 'could', 'should', 'would', 'may', 'might', 'must', 'will', 'shall'
    }
    
    # Country name to code mapping for filter extraction
    COUNTRY_MAPPINGS = {
        'germany': 'DE', 'german': 'DE', 'deutschland': 'DE',
        'france': 'FR', 'french': 'FR',
        'italy': 'IT', 'italian': 'IT',
        'spain': 'ES', 'spanish': 'ES',
        'netherlands': 'NL', 'dutch': 'NL', 'holland': 'NL',
        'belgium': 'BE', 'belgian': 'BE',
        'austria': 'AT', 'austrian': 'AT',
        'sweden': 'SE', 'swedish': 'SE',
        'denmark': 'DK', 'danish': 'DK',
        'finland': 'FI', 'finnish': 'FI',
        'poland': 'PL', 'polish': 'PL',
        'portugal': 'PT', 'portuguese': 'PT',
        'greece': 'GR', 'greek': 'GR', 'el': 'GR',
        'ireland': 'IE', 'irish': 'IE',
        'czech': 'CZ', 'czechia': 'CZ',
        'hungary': 'HU', 'hungarian': 'HU',
        'romania': 'RO', 'romanian': 'RO',
        'switzerland': 'CH', 'swiss': 'CH',
        'norway': 'NO', 'norwegian': 'NO',
        'uk': 'UK', 'united kingdom': 'UK', 'britain': 'UK', 'british': 'UK',
        'israel': 'IL', 'israeli': 'IL',
    }
    
    # Programme keywords
    PROGRAMME_MAPPINGS = {
        'horizon europe': 'HORIZON',
        'horizon 2020': 'H2020',
        'h2020': 'H2020',
        'fp7': 'FP7',
        'framework programme 7': 'FP7',
    }
    
    # Funding scheme keywords
    SCHEME_KEYWORDS = {
        'ria': 'RIA',
        'ia': 'IA',
        'csa': 'CSA',
        'erc': 'ERC',
        'msca': 'MSCA',
        'eic': 'EIC',
        'research innovation action': 'RIA',
        'innovation action': 'IA',
        'coordination support': 'CSA',
    }
    
    def __init__(self):
        """Initialize the search service with available data sources."""
        self._postgres_repo = None
        self._graph_service = None
        self._init_sources()
    
    def _init_sources(self):
        """Initialize data sources with graceful fallbacks."""
        # PostgreSQL Repository
        try:
            from .data.cordis_repository import CordisProjectRepository
            self._postgres_repo = CordisProjectRepository()
            logger.info("✅ PostgreSQL project repository initialized")
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL repository unavailable: {e}")
            self._postgres_repo = None
        
        # Neo4j Graph Service
        try:
            from .data_intelligence.graph_service import GraphSearchService
            self._graph_service = GraphSearchService()
            logger.info("✅ Neo4j graph service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Neo4j graph service unavailable: {e}")
            self._graph_service = None

    def _has_project_embeddings(self) -> bool:
        """Check if project_embeddings table exists and has data."""
        if not self._postgres_repo or not self._postgres_repo.db_pool:
            return False

        try:
            conn = self._postgres_repo.db_pool.getconn()
            cursor = conn.cursor()

            # Check if table exists and has embeddings
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'project_embeddings'
                ) AND EXISTS (
                    SELECT 1 FROM project_embeddings
                    WHERE embedding_status = 'completed'
                    AND combined_embedding IS NOT NULL
                    LIMIT 1
                )
            """)

            has_embeddings = cursor.fetchone()[0]
            cursor.close()
            self._postgres_repo.db_pool.putconn(conn)

            return has_embeddings
        except Exception as e:
            logger.warning(f"Failed to check project embeddings: {e}")
            return False

    async def _search_vector(
        self,
        query: str,
        filters: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Search projects using vector similarity.

        Args:
            query: Natural language search query
            filters: Applied filters
            limit: Maximum results

        Returns:
            List of project dicts with vector similarity scores
        """
        if not self._postgres_repo or not self._postgres_repo.db_pool:
            return []

        try:
            # Get query embedding
            from .embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            query_embedding = await asyncio.to_thread(
                embedding_service.generate_embedding,
                query
            )

            if query_embedding is None or not query_embedding.any():
                logger.warning("Failed to generate query embedding")
                return []

            # Convert to list for PostgreSQL
            query_vector = query_embedding.tolist()

            # Build WHERE clause for filters using %s placeholders
            where_clauses = ["pe.embedding_status = 'completed'", "pe.combined_embedding IS NOT NULL"]
            params = [query_vector]  # First param is the query vector

            if 'programme' in filters:
                where_clauses.append('p."frameworkProgramme" = %s')
                params.append(filters['programme'])

            if 'countries' in filters and filters['countries']:
                # Check if any participant country matches using organizations table
                country_placeholders = ','.join(['%s'] * len(filters['countries']))
                where_clauses.append(f"""
                    EXISTS (
                        SELECT 1 FROM organizations o
                        WHERE o."projectID" = p.id
                        AND o.country IN ({country_placeholders})
                    )
                """)
                params.extend(filters['countries'])

            if 'status' in filters:
                where_clauses.append("p.status = %s")
                params.append(filters['status'])

            where_clause = " AND ".join(where_clauses)
            params.append(query_vector)  # Second query vector for ORDER BY
            params.append(limit)

            # Execute vector similarity search
            conn = self._postgres_repo.db_pool.getconn()
            cursor = conn.cursor()

            try:
                query_sql = f"""
                    SELECT
                        p.id,
                        p.rcn,
                        p.title,
                        p.acronym,
                        p.objective,
                        p."startDate",
                        p."endDate",
                        p.status,
                        p."totalCost",
                        p."ecMaxContribution",
                        p."frameworkProgramme",
                        p."fundingScheme",
                        p.topics,
                        1 - (pe.combined_embedding <=> %s::vector) as similarity_score
                    FROM projects p
                    JOIN project_embeddings pe ON p.id = pe.project_id
                    WHERE {where_clause}
                    ORDER BY pe.combined_embedding <=> %s::vector
                    LIMIT %s
                """

                cursor.execute(query_sql, params)
                rows = cursor.fetchall()

                # Format results
                results = []
                for i, row in enumerate(rows):
                    results.append({
                        'id': row[0],
                        'rcn': row[1] or '',
                        'title': row[2],
                        'acronym': row[3],
                        'objective': (row[4] or '')[:500],
                        'startDate': str(row[5]) if row[5] else '',
                        'endDate': str(row[6]) if row[6] else '',
                        'status': row[7],
                        'totalCost': float(row[8] or 0),
                        'ecMaxContribution': float(row[9] or 0),
                        'frameworkProgramme': row[10] or '',
                        'fundingScheme': row[11] or '',
                        'topics': row[12] or '',
                        'similarity_score': float(row[13]),
                        '_source': 'vector',
                        '_rank': i + 1
                    })

                return results

            finally:
                cursor.close()
                self._postgres_repo.db_pool.putconn(conn)

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    async def search_projects(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        include_graph: bool = True,
        include_semantic: bool = True
    ) -> Dict[str, Any]:
        """
        Search for projects using all available local sources.
        
        Args:
            query: Natural language search query
            filters: Optional explicit filters:
                - programme: str (e.g., "H2020", "HORIZON")
                - countries: List[str] (e.g., ["DE", "FR"])
                - date_range: Dict with 'start' and/or 'end'
                - budget_range: Dict with 'min' and/or 'max'
                - status: str (e.g., "SIGNED", "CLOSED")
                - funding_scheme: str (e.g., "RIA", "ERC")
            limit: Maximum results to return
            include_graph: Whether to include Neo4j graph search
            include_semantic: Whether to include vector semantic search

        Returns:
            Dict with projects, metadata, and statistics
        """
        start_time = time.time()
        logger.info(f"🔍 LocalProjectSearch: '{query}' (limit={limit})")
        
        # 1. Parse query for implicit filters
        parsed_filters, search_terms = self._parse_query(query, filters)
        logger.info(f"   Parsed filters: {parsed_filters}")
        logger.info(f"   Search terms: {search_terms}")
        
        # 2. Run searches in parallel
        all_results = {}
        sources_used = []
        
        # PostgreSQL search (primary)
        if self._postgres_repo:
            try:
                postgres_results = await self._search_postgres(search_terms, parsed_filters, limit * 2)
                all_results['postgresql'] = postgres_results
                sources_used.append('postgresql')
                logger.info(f"   PostgreSQL returned {len(postgres_results)} projects")
            except Exception as e:
                logger.error(f"   PostgreSQL search failed: {e}")
        
        # Neo4j graph search (for relationship-based results)
        if include_graph and self._graph_service:
            try:
                graph_results = await self._search_graph(search_terms, parsed_filters, limit)
                all_results['neo4j'] = graph_results
                sources_used.append('neo4j')
                logger.info(f"   Neo4j returned {len(graph_results)} projects")
            except Exception as e:
                logger.warning(f"   Neo4j search failed: {e}")

        # Vector semantic search (for semantic similarity)
        if include_semantic and self._has_project_embeddings():
            try:
                vector_results = await self._search_vector(query, parsed_filters, limit)
                all_results['vector'] = vector_results
                sources_used.append('vector')
                logger.info(f"   Vector search returned {len(vector_results)} projects")
            except Exception as e:
                logger.warning(f"   Vector search failed: {e}")

        # 3. Fuse results if we have multiple sources
        if len(all_results) > 1:
            fused_results = self._reciprocal_rank_fusion(all_results)
        elif all_results:
            # Single source - just use those results
            fused_results = list(all_results.values())[0]
        else:
            fused_results = []
        
        # 4. Deduplicate by project_id
        unique_results = self._deduplicate(fused_results)
        
        # 5. Take top N
        final_results = unique_results[:limit]
        
        # 6. Format response
        elapsed = time.time() - start_time
        
        return {
            'success': True,
            'query': query,
            'projects': [self._format_project(p) for p in final_results],
            'total_found': len(unique_results),
            'returned': len(final_results),
            'filters_applied': parsed_filters,
            'search_terms': search_terms,
            'sources_used': sources_used,
            'processing_time_ms': int(elapsed * 1000),
            'data_source': 'local_multi_source'
        }
    
    async def find_similar_projects(
        self,
        project_id: str,
        similarity_type: str = "topic",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Find projects similar to a given project.
        
        Args:
            project_id: ID of the reference project
            similarity_type: Type of similarity:
                - "topic": Same topic/call
                - "consortium": Shared organizations
                - "cluster": Same cluster area
            limit: Maximum results
            
        Returns:
            Dict with similar projects
        """
        if not self._graph_service:
            return {
                'success': False,
                'error': 'Graph service not available for similarity search',
                'projects': []
            }
        
        try:
            similar = self._graph_service.find_similar_projects(
                project_id=project_id,
                similarity_type=similarity_type,
                limit=limit
            )
            
            return {
                'success': True,
                'reference_project': project_id,
                'similarity_type': similarity_type,
                'projects': similar,
                'total_found': len(similar)
            }
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'projects': []
            }

    async def find_similar_projects_by_embedding(
        self,
        project_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Find projects semantically similar to a given project using embeddings.

        Args:
            project_id: ID of the reference project
            limit: Maximum results

        Returns:
            Dict with similar projects and similarity scores
        """
        if not self._postgres_repo or not self._postgres_repo.db_pool:
            return {
                'success': False,
                'error': 'Database not available',
                'projects': []
            }

        if not self._has_project_embeddings():
            return {
                'success': False,
                'error': 'Vector similarity search not available - no embeddings in database',
                'projects': []
            }

        try:
            conn = self._postgres_repo.db_pool.getconn()
            cursor = conn.cursor()

            try:
                # Get the reference project's embedding
                cursor.execute("""
                    SELECT combined_embedding
                    FROM project_embeddings
                    WHERE project_id = %s
                      AND embedding_status = 'completed'
                      AND combined_embedding IS NOT NULL
                """, (project_id,))

                result = cursor.fetchone()
                if not result:
                    return {
                        'success': False,
                        'error': f'No embedding found for project {project_id}',
                        'projects': []
                    }

                ref_embedding = result[0]

                # Find similar projects with proper column names
                cursor.execute("""
                    SELECT
                        p.id,
                        p.rcn,
                        p.title,
                        p.acronym,
                        p.objective,
                        p."startDate",
                        p."endDate",
                        p.status,
                        p."totalCost",
                        p."ecMaxContribution",
                        p."frameworkProgramme",
                        p."fundingScheme",
                        p.topics,
                        1 - (pe.combined_embedding <=> %s::vector) as similarity_score
                    FROM projects p
                    JOIN project_embeddings pe ON p.id = pe.project_id
                    WHERE pe.project_id != %s
                      AND pe.embedding_status = 'completed'
                      AND pe.combined_embedding IS NOT NULL
                    ORDER BY pe.combined_embedding <=> %s::vector
                    LIMIT %s
                """, (ref_embedding, project_id, ref_embedding, limit))

                rows = cursor.fetchall()

                # Format results
                projects = []
                for row in rows:
                    projects.append({
                        'id': row[0],
                        'rcn': row[1] or '',
                        'title': row[2],
                        'acronym': row[3],
                        'objective': (row[4] or '')[:300],
                        'start_date': str(row[5]) if row[5] else '',
                        'end_date': str(row[6]) if row[6] else '',
                        'status': row[7],
                        'total_cost': float(row[8] or 0),
                        'ec_contribution': float(row[9] or 0),
                        'programme': row[10] or '',
                        'funding_scheme': row[11] or '',
                        'topics': row[12] or '',
                        'similarity_score': float(row[13]),
                        'cordis_url': f"https://cordis.europa.eu/project/id/{row[0]}"
                    })

                return {
                    'success': True,
                    'reference_project': project_id,
                    'similarity_type': 'semantic',
                    'projects': projects,
                    'total_found': len(projects)
                }

            finally:
                cursor.close()
                self._postgres_repo.db_pool.putconn(conn)

        except Exception as e:
            logger.error(f"Embedding similarity search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'projects': []
            }

    async def find_projects_by_organization(
        self,
        organization_name: str,
        role: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Find all projects an organization participated in.
        
        Args:
            organization_name: Name (or partial name) of organization
            role: Filter by role ("coordinator", "participant", or None for both)
            limit: Maximum results
            
        Returns:
            Dict with projects
        """
        if not self._graph_service:
            # Fallback to PostgreSQL
            if self._postgres_repo:
                try:
                    # Use text search on organization names
                    results, total = self._postgres_repo.search_projects(
                        queries=[organization_name],
                        limit=limit
                    )
                    return {
                        'success': True,
                        'organization': organization_name,
                        'projects': [self._format_project_from_dto(p) for p in results],
                        'total_found': total,
                        'source': 'postgresql_fallback'
                    }
                except Exception as e:
                    logger.error(f"PostgreSQL fallback failed: {e}")
            
            return {
                'success': False,
                'error': 'No search service available',
                'projects': []
            }
        
        try:
            projects = self._graph_service.find_projects_by_organization(
                organization_name=organization_name,
                role=role,
                limit=limit
            )
            
            return {
                'success': True,
                'organization': organization_name,
                'role_filter': role,
                'projects': projects,
                'total_found': len(projects)
            }
        except Exception as e:
            logger.error(f"Organization project search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'projects': []
            }
    
    def _parse_query(
        self,
        query: str,
        explicit_filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Parse query for implicit filters and extract search terms.
        
        Returns:
            Tuple of (filters dict, list of search terms)
        """
        filters = explicit_filters.copy() if explicit_filters else {}
        query_lower = query.lower()
        remaining_query = query
        
        # Extract country mentions
        if 'countries' not in filters:
            found_countries = []
            for name, code in self.COUNTRY_MAPPINGS.items():
                if name in query_lower:
                    found_countries.append(code)
                    # Remove from query to get cleaner search terms
                    remaining_query = re.sub(rf'\b{name}\b', '', remaining_query, flags=re.IGNORECASE)
            
            if found_countries:
                filters['countries'] = list(set(found_countries))
        
        # Extract programme mentions
        if 'programme' not in filters:
            for name, code in self.PROGRAMME_MAPPINGS.items():
                if name in query_lower:
                    filters['programme'] = code
                    remaining_query = re.sub(rf'\b{re.escape(name)}\b', '', remaining_query, flags=re.IGNORECASE)
                    break
        
        # Extract funding scheme mentions
        if 'funding_scheme' not in filters:
            for name, code in self.SCHEME_KEYWORDS.items():
                if name in query_lower:
                    filters['funding_scheme'] = code
                    remaining_query = re.sub(rf'\b{re.escape(name)}\b', '', remaining_query, flags=re.IGNORECASE)
                    break
        
        # Extract status mentions
        if 'status' not in filters:
            if 'ongoing' in query_lower or 'active' in query_lower or 'current' in query_lower:
                filters['status'] = 'SIGNED'
                remaining_query = re.sub(r'\b(ongoing|active|current)\b', '', remaining_query, flags=re.IGNORECASE)
            elif 'completed' in query_lower or 'finished' in query_lower or 'closed' in query_lower:
                filters['status'] = 'CLOSED'
                remaining_query = re.sub(r'\b(completed|finished|closed)\b', '', remaining_query, flags=re.IGNORECASE)
        
        # Remove common query verbs that don't add search value
        query_verbs = ['coordinated', 'coordinating', 'coordinator', 'participated', 'participating', 
                      'participant', 'has', 'have', 'had', 'show', 'shows', 'showing', 'find', 'finding',
                      'search', 'searches', 'searched', 'get', 'gets', 'getting']
        for verb in query_verbs:
            remaining_query = re.sub(rf'\b{verb}\b', '', remaining_query, flags=re.IGNORECASE)
        
        # Clean up remaining query to get search terms
        remaining_query = re.sub(r'\s+', ' ', remaining_query).strip()
        
        # Remove punctuation and split into words
        words = re.findall(r'\b\w+\b', remaining_query.lower())
        
        # Filter out stopwords and short words
        search_terms = [
            word for word in words 
            if word not in self.STOPWORDS and len(word) > 2
        ]
        
        # If no meaningful search terms left, use the original query (cleaned)
        if not search_terms:
            # Fallback: use original query but remove common query words
            fallback_words = [w for w in words if w not in self.STOPWORDS]
            search_terms = fallback_words if fallback_words else [query]
        
        return filters, search_terms
    
    async def _search_postgres(
        self,
        search_terms: List[str],
        filters: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search PostgreSQL using the CordisProjectRepository."""
        if not self._postgres_repo:
            return []
        
        try:
            # Build filter dict for repository
            repo_filters = {}
            
            if 'programme' in filters:
                repo_filters['programme'] = filters['programme']
            if 'countries' in filters:
                repo_filters['countries'] = filters['countries']
            if 'date_range' in filters:
                repo_filters['date_range'] = filters['date_range']
            if 'budget_range' in filters:
                repo_filters['budget_range'] = filters['budget_range']
            
            # Execute search
            projects, total = self._postgres_repo.search_projects(
                queries=search_terms,
                filters=repo_filters if repo_filters else None,
                limit=limit
            )
            
            # Convert DTOs to dicts with source marker
            results = []
            for i, project in enumerate(projects):
                result = project.to_dict()
                result['_source'] = 'postgresql'
                result['_rank'] = i + 1
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"PostgreSQL search error: {e}")
            return []
    
    async def _search_graph(
        self,
        search_terms: List[str],
        filters: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Search Neo4j for projects matching criteria.
        
        Neo4j Schema:
        - Project: id, title, acronym, objective, status, startDate, endDate, 
                   totalCost, ecMaxContribution, fundingScheme, legalBasis
        - Organization: id, name, shortName, city, country, sme, activityType
        - Relationships: FUNDED_UNDER (Project->Topic), TARGETS (Project->Cluster),
                        PARTICIPATES_IN (Organization->Project), LOCATED_IN (Org->Country)
        """
        if not self._graph_service:
            return []
        
        try:
            search_query = ' '.join(search_terms)
            params = {'search': search_query, 'limit': limit}
            
            # Check if we need country filtering
            has_country_filter = 'countries' in filters and filters['countries']
            
            if has_country_filter:
                # Query with country filter via organization
                params['countries'] = filters['countries']
                
                status_clause = ""
                if 'status' in filters:
                    status_clause = "AND p.status = $status"
                    params['status'] = filters['status']
                
                cypher = f"""
                MATCH (o:Organization)-[:PARTICIPATES_IN]->(p:Project)
                WHERE o.country IN $countries
                  AND (toLower(p.title) CONTAINS toLower($search)
                       OR toLower(p.objective) CONTAINS toLower($search))
                  {status_clause}
                
                WITH DISTINCT p
                
                // Get related cluster and topic info
                OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
                OPTIONAL MATCH (p)-[:FUNDED_UNDER]->(t:Topic)
                
                RETURN p.id as id, 
                       p.title as title, 
                       p.acronym as acronym,
                       p.objective as objective, 
                       p.startDate as startDate, 
                       p.endDate as endDate,
                       p.totalCost as totalCost, 
                       p.ecMaxContribution as ecMaxContribution,
                       p.status as status, 
                       p.fundingScheme as fundingScheme,
                       COLLECT(DISTINCT c.name)[0] as clusterName, 
                       COLLECT(DISTINCT c.code)[0] as clusterCode, 
                       COLLECT(DISTINCT t.code) as topicCodes
                ORDER BY p.startDate DESC
                LIMIT $limit
                """
            else:
                # Simple query without country filter
                status_clause = ""
                if 'status' in filters:
                    status_clause = "AND p.status = $status"
                    params['status'] = filters['status']
                
                cypher = f"""
                MATCH (p:Project)
                WHERE (toLower(p.title) CONTAINS toLower($search)
                       OR toLower(p.objective) CONTAINS toLower($search))
                  {status_clause}
                
                // Get related cluster and topic info
                OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
                OPTIONAL MATCH (p)-[:FUNDED_UNDER]->(t:Topic)
                
                RETURN p.id as id, 
                       p.title as title, 
                       p.acronym as acronym,
                       p.objective as objective, 
                       p.startDate as startDate, 
                       p.endDate as endDate,
                       p.totalCost as totalCost, 
                       p.ecMaxContribution as ecMaxContribution,
                       p.status as status, 
                       p.fundingScheme as fundingScheme,
                       COLLECT(DISTINCT c.name)[0] as clusterName, 
                       COLLECT(DISTINCT c.code)[0] as clusterCode, 
                       COLLECT(DISTINCT t.code) as topicCodes
                ORDER BY p.startDate DESC
                LIMIT $limit
                """
            
            results = self._graph_service.db.execute_query(cypher, params)
            
            # Convert to standard format
            formatted = []
            for i, r in enumerate(results):
                topic_codes = r.get('topicCodes') or []
                formatted.append({
                    'id': r.get('id'),
                    'rcn': '',  # Not in Neo4j
                    'title': r.get('title'),
                    'acronym': r.get('acronym'),
                    'objective': (r.get('objective') or '')[:500],
                    'startDate': r.get('startDate'),
                    'endDate': r.get('endDate'),
                    'totalCost': r.get('totalCost', 0),
                    'ecMaxContribution': r.get('ecMaxContribution', 0),
                    'status': r.get('status'),
                    'frameworkProgramme': '',  # Not in Neo4j Project node
                    'fundingScheme': r.get('fundingScheme'),
                    'topics': ', '.join([t for t in topic_codes if t]) if topic_codes else '',
                    'cluster_name': r.get('clusterName'),
                    'cluster_code': r.get('clusterCode'),
                    '_source': 'neo4j',
                    '_rank': i + 1
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Neo4j search error: {e}")
            return []
    
    async def search_projects_by_relationship(
        self,
        relationship_type: str,
        entity_value: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search projects by graph relationships.
        
        Args:
            relationship_type: Type of relationship to search:
                - "cluster": Find projects in a cluster
                - "topic": Find projects under a topic code
                - "organization": Find projects with an organization
                - "country": Find projects with partners from a country
            entity_value: The value to search for (cluster name, topic code, org name, country code)
            limit: Max results
            
        Returns:
            Dict with projects and relationship metadata
        """
        if not self._graph_service:
            return {'success': False, 'error': 'Graph service not available', 'projects': []}
        
        try:
            params = {'value': entity_value, 'limit': limit}
            
            if relationship_type == "cluster":
                cypher = """
                MATCH (p:Project)-[:TARGETS]->(c:Cluster)
                WHERE toLower(c.name) CONTAINS toLower($value) 
                   OR toLower(c.code) CONTAINS toLower($value)
                RETURN p.id as id, p.title as title, p.acronym as acronym,
                       p.objective as objective, p.status as status,
                       p.ecMaxContribution as budget, p.fundingScheme as scheme,
                       c.name as clusterName, c.code as clusterCode
                ORDER BY p.startDate DESC
                LIMIT $limit
                """
            elif relationship_type == "topic":
                cypher = """
                MATCH (p:Project)-[:FUNDED_UNDER]->(t:Topic)
                WHERE toLower(t.code) CONTAINS toLower($value)
                RETURN p.id as id, p.title as title, p.acronym as acronym,
                       p.objective as objective, p.status as status,
                       p.ecMaxContribution as budget, p.fundingScheme as scheme,
                       t.code as topicCode
                ORDER BY p.startDate DESC
                LIMIT $limit
                """
            elif relationship_type == "organization":
                cypher = """
                MATCH (o:Organization)-[:PARTICIPATES_IN]->(p:Project)
                WHERE toLower(o.name) CONTAINS toLower($value)
                   OR toLower(o.shortName) CONTAINS toLower($value)
                RETURN p.id as id, p.title as title, p.acronym as acronym,
                       p.objective as objective, p.status as status,
                       p.ecMaxContribution as budget, p.fundingScheme as scheme,
                       o.name as orgName, o.country as orgCountry
                ORDER BY p.startDate DESC
                LIMIT $limit
                """
            elif relationship_type == "country":
                cypher = """
                MATCH (o:Organization)-[:PARTICIPATES_IN]->(p:Project)
                WHERE o.country = $value
                WITH p, COUNT(DISTINCT o) as orgCount
                RETURN p.id as id, p.title as title, p.acronym as acronym,
                       p.objective as objective, p.status as status,
                       p.ecMaxContribution as budget, p.fundingScheme as scheme,
                       orgCount
                ORDER BY orgCount DESC, p.startDate DESC
                LIMIT $limit
                """
            else:
                return {'success': False, 'error': f'Unknown relationship type: {relationship_type}', 'projects': []}
            
            results = self._graph_service.db.execute_query(cypher, params)
            
            projects = []
            for r in results:
                projects.append({
                    'id': r.get('id'),
                    'title': r.get('title'),
                    'acronym': r.get('acronym'),
                    'objective': (r.get('objective') or '')[:300],
                    'status': r.get('status'),
                    'budget': r.get('budget', 0),
                    'funding_scheme': r.get('scheme'),
                    'cluster_name': r.get('clusterName'),
                    'cluster_code': r.get('clusterCode'),
                    'topic_code': r.get('topicCode'),
                    'org_name': r.get('orgName'),
                    'org_country': r.get('orgCountry'),
                    'org_count': r.get('orgCount'),
                    'cordis_url': f"https://cordis.europa.eu/project/id/{r.get('id')}"
                })
            
            return {
                'success': True,
                'relationship_type': relationship_type,
                'entity': entity_value,
                'projects': projects,
                'total_found': len(projects)
            }
            
        except Exception as e:
            logger.error(f"Relationship search error: {e}")
            return {'success': False, 'error': str(e), 'projects': []}
    
    def _reciprocal_rank_fusion(
        self,
        results_by_source: Dict[str, List[Dict]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combine rankings using Reciprocal Rank Fusion.
        
        RRF score = Σ 1/(k + rank) for each list the item appears in.
        Higher k gives more weight to items appearing in multiple lists.
        """
        scores = {}
        projects_map = {}
        
        for source, projects in results_by_source.items():
            for project in projects:
                pid = str(project.get('id'))
                rank = project.get('_rank', 1)
                
                if pid not in scores:
                    scores[pid] = 0
                    projects_map[pid] = project.copy()
                    projects_map[pid]['_sources'] = []
                
                scores[pid] += 1 / (k + rank)
                projects_map[pid]['_sources'].append(source)
        
        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        results = []
        for pid in sorted_ids:
            project = projects_map[pid]
            project['_rrf_score'] = scores[pid]
            results.append(project)
        
        return results
    
    def _deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate projects, keeping highest-scored version."""
        seen = set()
        unique = []
        
        for project in results:
            pid = str(project.get('id'))
            if pid not in seen:
                seen.add(pid)
                unique.append(project)
        
        return unique
    
    def _format_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Format project for API response."""
        project_id = project.get('id', '')
        
        return {
            'id': project_id,
            'rcn': project.get('rcn', ''),
            'title': project.get('title', 'Unknown Title'),
            'acronym': project.get('acronym'),
            'objective': self._truncate(project.get('objective', ''), 500),
            'start_date': project.get('startDate', ''),
            'end_date': project.get('endDate', ''),
            'status': project.get('status', 'Unknown'),
            'total_cost': project.get('totalCost', 0),
            'ec_contribution': project.get('ecMaxContribution', 0),
            'programme': project.get('frameworkProgramme', ''),
            'funding_scheme': project.get('fundingScheme', ''),
            'topics': project.get('topics', ''),
            'coordinator': {
                'name': project.get('coordinator_name'),
                'country': project.get('coordinator_country')
            },
            'consortium': {
                'participant_count': project.get('participant_count', 0),
                'country_count': project.get('country_count', 0),
                'sme_count': project.get('sme_count', 0),
                'countries': project.get('participant_countries', [])
            },
            'relevance_score': project.get('_rrf_score', project.get('relevance_score', 0)),
            'similarity_score': project.get('similarity_score'),
            'sources': project.get('_sources', [project.get('_source', 'unknown')]),
            'cordis_url': f"https://cordis.europa.eu/project/id/{project_id}" if project_id else None
        }
    
    def _format_project_from_dto(self, dto) -> Dict[str, Any]:
        """Format a CordisProjectDTO for response."""
        return {
            'id': dto.id,
            'rcn': dto.rcn,
            'title': dto.title,
            'acronym': dto.acronym,
            'objective': self._truncate(dto.objective, 500),
            'start_date': dto.start_date,
            'end_date': dto.end_date,
            'status': dto.status,
            'total_cost': dto.total_cost,
            'ec_contribution': dto.ec_max_contribution,
            'programme': dto.framework_programme,
            'funding_scheme': dto.funding_scheme,
            'topics': dto.topics,
            'coordinator': {
                'name': dto.coordinator_name,
                'country': dto.coordinator_country
            },
            'consortium': {
                'participant_count': dto.participant_count,
                'country_count': dto.country_count,
                'sme_count': dto.sme_count,
                'countries': dto.participant_countries
            },
            'relevance_score': dto.relevance_score,
            'sources': [dto.data_source],
            'cordis_url': f"https://cordis.europa.eu/project/id/{dto.id}"
        }
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis."""
        if not text:
            return ''
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + '...'


# Module-level instance for convenience
local_project_search = LocalProjectSearchService()

