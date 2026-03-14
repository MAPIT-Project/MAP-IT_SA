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

import asyncio
import logging
import re
import time
from dataclasses import asdict, dataclass
from typing import Any

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class ProjectSearchResult:
    """Unified project search result."""

    project_id: str
    rcn: str
    title: str
    acronym: str | None
    objective: str
    start_date: str
    end_date: str
    status: str
    total_cost: float
    ec_contribution: float
    programme: str
    funding_scheme: str
    topics: str
    coordinator_name: str | None
    coordinator_country: str | None
    participant_count: int
    country_count: int
    sme_count: int
    participant_countries: list[str]
    relevance_score: float
    data_source: str
    cordis_url: str

    def to_dict(self) -> dict[str, Any]:
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
        "find",
        "show",
        "me",
        "get",
        "search",
        "for",
        "about",
        "in",
        "from",
        "with",
        "projects",
        "project",
        "calls",
        "call",
        "funding",
        "grants",
        "grant",
        "has",
        "have",
        "had",
        "are",
        "is",
        "was",
        "were",
        "been",
        "being",
        "coordinated",
        "coordinating",
        "participated",
        "participating",
        "what",
        "which",
        "where",
        "when",
        "who",
        "how",
        "why",
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "some",
        "any",
        "all",
        "each",
        "every",
        "this",
        "that",
        "these",
        "those",
        "to",
        "of",
        "on",
        "at",
        "by",
        "into",
        "onto",
        "can",
        "could",
        "should",
        "would",
        "may",
        "might",
        "must",
        "will",
        "shall",
    }

    # Important short terms that should NOT be filtered out despite being <= 2 chars
    # These are domain-specific acronyms and abbreviations that carry meaning
    IMPORTANT_SHORT_TERMS = {
        "ai",
        "ml",
        "it",
        "ict",
        "hpc",
        "iot",
        "5g",
        "6g",  # Technology
        "co2",
        "ph",
        "uv",
        "ev",
        "eu",
        "un",  # Science/Geography
        "ria",
        "csa",
        "ia",
        "erc",
        "eic",
        "eit",  # EU funding instruments
        "sme",
        "ngo",
        "prc",
        "rec",
        "hes",
        "pub",  # Organization types
    }

    # Country name to code mapping for filter extraction
    COUNTRY_MAPPINGS = {
        "germany": "DE",
        "german": "DE",
        "deutschland": "DE",
        "france": "FR",
        "french": "FR",
        "italy": "IT",
        "italian": "IT",
        "spain": "ES",
        "spanish": "ES",
        "netherlands": "NL",
        "dutch": "NL",
        "holland": "NL",
        "belgium": "BE",
        "belgian": "BE",
        "austria": "AT",
        "austrian": "AT",
        "sweden": "SE",
        "swedish": "SE",
        "denmark": "DK",
        "danish": "DK",
        "finland": "FI",
        "finnish": "FI",
        "poland": "PL",
        "polish": "PL",
        "portugal": "PT",
        "portuguese": "PT",
        "greece": "GR",
        "greek": "GR",
        "el": "GR",
        "ireland": "IE",
        "irish": "IE",
        "czech": "CZ",
        "czechia": "CZ",
        "hungary": "HU",
        "hungarian": "HU",
        "romania": "RO",
        "romanian": "RO",
        "switzerland": "CH",
        "swiss": "CH",
        "norway": "NO",
        "norwegian": "NO",
        "uk": "UK",
        "united kingdom": "UK",
        "britain": "UK",
        "british": "UK",
        "israel": "IL",
        "israeli": "IL",
    }

    # Programme keywords
    PROGRAMME_MAPPINGS = {
        "horizon europe": "HORIZON",
        "horizon 2020": "H2020",
        "h2020": "H2020",
        "fp7": "FP7",
        "framework programme 7": "FP7",
    }

    # Funding scheme keywords
    SCHEME_KEYWORDS = {
        "ria": "RIA",
        "ia": "IA",
        "csa": "CSA",
        "erc": "ERC",
        "msca": "MSCA",
        "eic": "EIC",
        "research innovation action": "RIA",
        "innovation action": "IA",
        "coordination support": "CSA",
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
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'project_embeddings'
                ) AND EXISTS (
                    SELECT 1 FROM project_embeddings
                    WHERE embedding_status = 'completed'
                    AND combined_embedding IS NOT NULL
                    LIMIT 1
                )
            """
            )

            has_embeddings = cursor.fetchone()[0]
            cursor.close()
            self._postgres_repo.db_pool.putconn(conn)

            return has_embeddings
        except Exception as e:
            logger.warning(f"Failed to check project embeddings: {e}")
            return False

    async def _search_vector(
        self, query: str, filters: dict[str, Any], limit: int
    ) -> list[dict[str, Any]]:
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
            query_embedding = await asyncio.to_thread(embedding_service.generate_embedding, query)

            if query_embedding is None or not query_embedding.any():
                logger.warning("Failed to generate query embedding")
                return []

            # Convert to list for PostgreSQL
            query_vector = query_embedding.tolist()

            # Build WHERE clause for filters using %s placeholders
            where_clauses = [
                "pe.embedding_status = 'completed'",
                "pe.combined_embedding IS NOT NULL",
            ]
            params = [query_vector]  # First param is the query vector

            if "programme" in filters:
                where_clauses.append('p."frameworkProgramme" = %s')
                params.append(filters["programme"])

            if "countries" in filters and filters["countries"]:
                # Check if any participant country matches using organizations table
                country_placeholders = ",".join(["%s"] * len(filters["countries"]))
                where_clauses.append(
                    f"""
                    EXISTS (
                        SELECT 1 FROM organizations o
                        WHERE o."projectID" = p.id
                        AND o.country IN ({country_placeholders})
                    )
                """
                )
                params.extend(filters["countries"])

            if "status" in filters:
                where_clauses.append("p.status = %s")
                params.append(filters["status"])

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

                # Format results — filter out low-similarity matches
                SIMILARITY_THRESHOLD = 0.35  # Below this, results are noise
                results = []
                rank = 0
                for row in rows:
                    similarity = float(row[13])
                    if similarity < SIMILARITY_THRESHOLD:
                        continue
                    rank += 1
                    results.append(
                        {
                            "id": row[0],
                            "rcn": row[1] or "",
                            "title": row[2],
                            "acronym": row[3],
                            "objective": (row[4] or "")[:500],
                            "startDate": str(row[5]) if row[5] else "",
                            "endDate": str(row[6]) if row[6] else "",
                            "status": row[7],
                            "totalCost": float(row[8] or 0),
                            "ecMaxContribution": float(row[9] or 0),
                            "frameworkProgramme": row[10] or "",
                            "fundingScheme": row[11] or "",
                            "topics": row[12] or "",
                            "similarity_score": similarity,
                            "_source": "vector",
                            "_rank": rank,
                        }
                    )

                if len(rows) != len(results):
                    logger.info(
                        f"   Vector: filtered {len(rows) - len(results)} low-similarity results "
                        f"(threshold={SIMILARITY_THRESHOLD})"
                    )

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
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        include_graph: bool = True,
        include_semantic: bool = True,
        sort_by: str | None = None,
    ) -> dict[str, Any]:
        """
        Search for projects using optimized retrieve-rerank-enrich pipeline.

        Architecture:
          Stage 1 - RETRIEVE: PostgreSQL keyword + vector semantic search (parallel)
          Stage 2 - FUSE: Reciprocal Rank Fusion combines both retrieval signals
          Stage 3 - RERANK: Cross-encoder neural reranking for precision
          Stage 4 - ENRICH: Neo4j graph adds cluster/topic/coordinator metadata

        Neo4j is NOT used for text search (PostgreSQL already does that better).
        Neo4j is used for what it excels at: graph-based metadata enrichment.

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
            include_graph: Whether to enrich results with Neo4j graph metadata
            include_semantic: Whether to include vector semantic search
            sort_by: Sort order ('relevance', 'ec_contribution', 'total_cost', 'start_date')

        Returns:
            Dict with projects, metadata, and statistics
        """
        start_time = time.time()
        logger.info(f"🔍 LocalProjectSearch: '{query}' (limit={limit}, sort_by={sort_by})")

        # 1. Parse query for implicit filters
        parsed_filters, search_terms = self._parse_query(query, filters)
        logger.info(f"   Parsed filters: {parsed_filters}")
        logger.info(f"   Search terms: {search_terms}")

        # 2. RETRIEVE: Run PostgreSQL keyword + vector search in parallel
        all_results = {}
        sources_used = []

        # Build retrieval tasks to run in parallel
        retrieval_tasks = []

        # PostgreSQL full-text search (primary retrieval)
        if self._postgres_repo:
            retrieval_tasks.append(
                self._run_postgres_search(
                    search_terms, parsed_filters, limit * 2, sort_by, all_results, sources_used
                )
            )

        # Vector semantic search (secondary retrieval — finds conceptually similar projects)
        if include_semantic and self._has_project_embeddings():
            retrieval_tasks.append(
                self._run_vector_search(query, parsed_filters, limit, all_results, sources_used)
            )

        # Execute retrieval in parallel
        if retrieval_tasks:
            await asyncio.gather(*retrieval_tasks)

        # 3. FUSE: Combine results from multiple retrieval sources
        if len(all_results) > 1:
            fused_results = self._reciprocal_rank_fusion(all_results)
        elif all_results:
            fused_results = list(all_results.values())[0]
        else:
            fused_results = []

        # 4. Deduplicate by project_id (merges fields from duplicate entries)
        unique_results = self._deduplicate(fused_results)

        # 5. RERANK: Cross-encoder neural reranking for precision (relevance sort only)
        if not sort_by or sort_by == "relevance":
            unique_results = await self._rerank_with_cross_encoder(query, unique_results, limit)
        else:
            # Re-sort by explicit sort_by (ec_contribution, total_cost, start_date)
            sort_key_map = {
                "ec_contribution": lambda p: float(
                    p.get("ec_contribution") or p.get("ecMaxContribution") or p.get("budget") or 0
                ),
                "total_cost": lambda p: float(p.get("total_cost") or p.get("totalCost") or 0),
                "start_date": lambda p: str(p.get("start_date") or p.get("startDate") or ""),
            }
            key_fn = sort_key_map.get(sort_by)
            if key_fn:
                logger.info(f"   Re-sorting {len(unique_results)} results by {sort_by}")
                unique_results.sort(key=key_fn, reverse=True)

        # 6. Take top N
        final_results = unique_results[:limit]

        # 7. ENRICH: Add coordinator + graph metadata to final results
        final_results = self._enrich_coordinator_data(final_results)

        if include_graph and self._graph_service:
            final_results = await self._enrich_with_graph(final_results)
            sources_used.append("neo4j")

        # 8. Format response
        elapsed = time.time() - start_time

        return {
            "success": True,
            "query": query,
            "projects": [self._format_project(p) for p in final_results],
            "total_found": len(unique_results),
            "returned": len(final_results),
            "filters_applied": parsed_filters,
            "search_terms": search_terms,
            "sources_used": sources_used,
            "processing_time_ms": int(elapsed * 1000),
            "data_source": "local_multi_source",
            "search_quality": {
                "vector_search": "vector" in sources_used,
                "cross_encoder_reranked": not sort_by or sort_by == "relevance",
                "graph_enriched": "neo4j" in sources_used,
                "fusion_method": "rrf" if len(all_results) > 1 else "single_source",
            },
        }

    async def _run_postgres_search(
        self,
        search_terms: list[str],
        parsed_filters: dict[str, Any],
        limit: int,
        sort_by: str | None,
        all_results: dict,
        sources_used: list,
    ) -> None:
        """Run PostgreSQL search and collect results (for parallel execution)."""
        try:
            postgres_results = await self._search_postgres(
                search_terms, parsed_filters, limit, sort_by=sort_by
            )
            all_results["postgresql"] = postgres_results
            sources_used.append("postgresql")
            logger.info(f"   PostgreSQL returned {len(postgres_results)} projects")
        except Exception as e:
            logger.error(f"   PostgreSQL search failed: {e}")

    async def _run_vector_search(
        self,
        query: str,
        parsed_filters: dict[str, Any],
        limit: int,
        all_results: dict,
        sources_used: list,
    ) -> None:
        """Run vector semantic search and collect results (for parallel execution)."""
        try:
            vector_results = await self._search_vector(query, parsed_filters, limit)
            all_results["vector"] = vector_results
            sources_used.append("vector")
            logger.info(f"   Vector search returned {len(vector_results)} projects")
        except Exception as e:
            logger.warning(f"   Vector search failed: {e}")

    async def _enrich_with_graph(self, projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Enrich final results with Neo4j graph metadata (cluster, topics).

        Only runs on the final top-N results, not the full candidate set.
        This is what Neo4j excels at: graph traversal for relationship data.
        """
        if not self._graph_service or not projects:
            return projects

        project_ids = [str(p.get("id")) for p in projects if p.get("id")]
        if not project_ids:
            return projects

        try:
            # Batch fetch cluster/topic data for all final results
            placeholders = ", ".join([f"'{pid}'" for pid in project_ids])
            cypher = f"""
                MATCH (p:Project)
                WHERE p.id IN [{placeholders}]
                OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
                OPTIONAL MATCH (p)-[:FUNDED_UNDER]->(t:Topic)
                RETURN p.id as id,
                       COLLECT(DISTINCT c.name)[0] as clusterName,
                       COLLECT(DISTINCT c.code)[0] as clusterCode,
                       COLLECT(DISTINCT t.code) as topicCodes
            """

            results = self._graph_service.db.execute_query(cypher)

            # Build lookup map
            graph_data = {}
            for r in results:
                pid = str(r.get("id"))
                topic_codes = r.get("topicCodes") or []
                graph_data[pid] = {
                    "cluster_name": r.get("clusterName"),
                    "cluster_code": r.get("clusterCode"),
                    "topic_codes": [t for t in topic_codes if t],
                }

            # Enrich projects
            enriched = 0
            for p in projects:
                pid = str(p.get("id"))
                if pid in graph_data:
                    gd = graph_data[pid]
                    if gd["cluster_name"]:
                        p["cluster_name"] = gd["cluster_name"]
                    if gd["cluster_code"]:
                        p["cluster_code"] = gd["cluster_code"]
                    if gd["topic_codes"] and not p.get("topics"):
                        p["topics"] = ", ".join(gd["topic_codes"])
                    enriched += 1

            logger.info(
                f"   Neo4j enriched {enriched}/{len(projects)} projects with cluster/topic data"
            )

        except Exception as e:
            logger.warning(f"   Neo4j graph enrichment failed (non-critical): {e}")

        return projects

    async def find_similar_projects(
        self, project_id: str, similarity_type: str = "topic", limit: int = 10
    ) -> dict[str, Any]:
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
                "success": False,
                "error": "Graph service not available for similarity search",
                "projects": [],
            }

        try:
            similar = self._graph_service.find_similar_projects(
                project_id=project_id, similarity_type=similarity_type, limit=limit
            )

            return {
                "success": True,
                "reference_project": project_id,
                "similarity_type": similarity_type,
                "projects": similar,
                "total_found": len(similar),
            }
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return {"success": False, "error": str(e), "projects": []}

    async def find_similar_projects_by_embedding(
        self, project_id: str, limit: int = 10
    ) -> dict[str, Any]:
        """
        Find projects semantically similar to a given project using embeddings.

        Args:
            project_id: ID of the reference project
            limit: Maximum results

        Returns:
            Dict with similar projects and similarity scores
        """
        if not self._postgres_repo or not self._postgres_repo.db_pool:
            return {"success": False, "error": "Database not available", "projects": []}

        if not self._has_project_embeddings():
            return {
                "success": False,
                "error": "Vector similarity search not available - no embeddings in database",
                "projects": [],
            }

        try:
            conn = self._postgres_repo.db_pool.getconn()
            cursor = conn.cursor()

            try:
                # Get the reference project's embedding
                cursor.execute(
                    """
                    SELECT combined_embedding
                    FROM project_embeddings
                    WHERE project_id = %s
                      AND embedding_status = 'completed'
                      AND combined_embedding IS NOT NULL
                """,
                    (project_id,),
                )

                result = cursor.fetchone()
                if not result:
                    return {
                        "success": False,
                        "error": f"No embedding found for project {project_id}",
                        "projects": [],
                    }

                ref_embedding = result[0]

                # Find similar projects with proper column names
                cursor.execute(
                    """
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
                """,
                    (ref_embedding, project_id, ref_embedding, limit),
                )

                rows = cursor.fetchall()

                # Format results
                projects = []
                for row in rows:
                    projects.append(
                        {
                            "id": row[0],
                            "rcn": row[1] or "",
                            "title": row[2],
                            "acronym": row[3],
                            "objective": (row[4] or "")[:300],
                            "start_date": str(row[5]) if row[5] else "",
                            "end_date": str(row[6]) if row[6] else "",
                            "status": row[7],
                            "total_cost": float(row[8] or 0),
                            "ec_contribution": float(row[9] or 0),
                            "programme": row[10] or "",
                            "funding_scheme": row[11] or "",
                            "topics": row[12] or "",
                            "similarity_score": float(row[13]),
                            "cordis_url": f"https://cordis.europa.eu/project/id/{row[0]}",
                        }
                    )

                return {
                    "success": True,
                    "reference_project": project_id,
                    "similarity_type": "semantic",
                    "projects": projects,
                    "total_found": len(projects),
                }

            finally:
                cursor.close()
                self._postgres_repo.db_pool.putconn(conn)

        except Exception as e:
            logger.error(f"Embedding similarity search failed: {e}")
            return {"success": False, "error": str(e), "projects": []}

    async def find_projects_by_organization(
        self, organization_name: str, role: str | None = None, limit: int = 20
    ) -> dict[str, Any]:
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
                        queries=[organization_name], limit=limit
                    )
                    return {
                        "success": True,
                        "organization": organization_name,
                        "projects": [self._format_project_from_dto(p) for p in results],
                        "total_found": total,
                        "source": "postgresql_fallback",
                    }
                except Exception as e:
                    logger.error(f"PostgreSQL fallback failed: {e}")

            return {"success": False, "error": "No search service available", "projects": []}

        try:
            projects = self._graph_service.find_projects_by_organization(
                organization_name=organization_name, role=role, limit=limit
            )

            return {
                "success": True,
                "organization": organization_name,
                "role_filter": role,
                "projects": projects,
                "total_found": len(projects),
            }
        except Exception as e:
            logger.error(f"Organization project search failed: {e}")
            return {"success": False, "error": str(e), "projects": []}

    def _parse_query(
        self, query: str, explicit_filters: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], list[str]]:
        """
        Parse query for implicit filters and extract search terms.

        Returns:
            Tuple of (filters dict, list of search terms)
        """
        filters = explicit_filters.copy() if explicit_filters else {}
        query_lower = query.lower()
        remaining_query = query

        # Extract country mentions (use word boundary to avoid substring matches)
        if "countries" not in filters:
            found_countries = []
            for name, code in self.COUNTRY_MAPPINGS.items():
                # Use word boundary regex to avoid "el" matching inside "relevant"
                if re.search(rf"\b{re.escape(name)}\b", query_lower):
                    found_countries.append(code)
                    # Remove from query to get cleaner search terms
                    remaining_query = re.sub(
                        rf"\b{re.escape(name)}\b", "", remaining_query, flags=re.IGNORECASE
                    )

            if found_countries:
                filters["countries"] = list(set(found_countries))

        # Extract programme mentions (use word boundary for multi-word matches)
        if "programme" not in filters:
            for name, code in self.PROGRAMME_MAPPINGS.items():
                # Use word boundary regex for accurate matching
                if re.search(rf"\b{re.escape(name)}\b", query_lower):
                    filters["programme"] = code
                    remaining_query = re.sub(
                        rf"\b{re.escape(name)}\b", "", remaining_query, flags=re.IGNORECASE
                    )
                    break

        # Extract funding scheme mentions (use word boundary to avoid substring matches)
        if "funding_scheme" not in filters:
            for name, code in self.SCHEME_KEYWORDS.items():
                # Use word boundary regex to avoid "ia" matching inside "AI"
                if re.search(rf"\b{re.escape(name)}\b", query_lower):
                    filters["funding_scheme"] = code
                    remaining_query = re.sub(
                        rf"\b{re.escape(name)}\b", "", remaining_query, flags=re.IGNORECASE
                    )
                    break

        # Extract status mentions
        if "status" not in filters:
            if "ongoing" in query_lower or "active" in query_lower or "current" in query_lower:
                filters["status"] = "SIGNED"
                remaining_query = re.sub(
                    r"\b(ongoing|active|current)\b", "", remaining_query, flags=re.IGNORECASE
                )
            elif "completed" in query_lower or "finished" in query_lower or "closed" in query_lower:
                filters["status"] = "CLOSED"
                remaining_query = re.sub(
                    r"\b(completed|finished|closed)\b", "", remaining_query, flags=re.IGNORECASE
                )

        # Remove common query verbs that don't add search value
        query_verbs = [
            "coordinated",
            "coordinating",
            "coordinator",
            "participated",
            "participating",
            "participant",
            "has",
            "have",
            "had",
            "show",
            "shows",
            "showing",
            "find",
            "finding",
            "search",
            "searches",
            "searched",
            "get",
            "gets",
            "getting",
        ]
        for verb in query_verbs:
            remaining_query = re.sub(rf"\b{verb}\b", "", remaining_query, flags=re.IGNORECASE)

        # Clean up remaining query to get search terms
        remaining_query = re.sub(r"\s+", " ", remaining_query).strip()

        # Remove punctuation and split into words
        words = re.findall(r"\b\w+\b", remaining_query.lower())

        # Filter out stopwords and short words (but keep important short terms)
        search_terms = [
            word
            for word in words
            if word not in self.STOPWORDS and (len(word) > 2 or word in self.IMPORTANT_SHORT_TERMS)
        ]

        # If no meaningful search terms left, use the original query (cleaned)
        if not search_terms:
            # Fallback: use original query but remove common query words
            fallback_words = [w for w in words if w not in self.STOPWORDS]
            search_terms = fallback_words if fallback_words else [query]

        return filters, search_terms

    async def _search_postgres(
        self,
        search_terms: list[str],
        filters: dict[str, Any],
        limit: int,
        sort_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search PostgreSQL using the CordisProjectRepository."""
        if not self._postgres_repo:
            return []

        try:
            # Build filter dict for repository
            repo_filters = {}

            if "programme" in filters:
                repo_filters["programme"] = filters["programme"]
            if "countries" in filters:
                repo_filters["countries"] = filters["countries"]
            if "date_range" in filters:
                repo_filters["date_range"] = filters["date_range"]
            if "budget_range" in filters:
                repo_filters["budget_range"] = filters["budget_range"]

            # Execute search
            projects, total = self._postgres_repo.search_projects(
                queries=search_terms,
                filters=repo_filters if repo_filters else None,
                limit=limit,
                sort_by=sort_by,
            )

            # Convert DTOs to dicts with source marker
            results = []
            for i, project in enumerate(projects):
                result = project.to_dict()
                result["_source"] = "postgresql"
                result["_rank"] = i + 1
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"PostgreSQL search error: {e}")
            return []

    def _has_neo4j_fulltext_index(self) -> bool:
        """Check if the Neo4j full-text index exists (cached)."""
        if not hasattr(self, "_neo4j_ft_available"):
            try:
                results = self._graph_service.db.execute_query(
                    "SHOW INDEXES YIELD name WHERE name = 'project_fulltext_search' RETURN name"
                )
                self._neo4j_ft_available = len(results) > 0
                if self._neo4j_ft_available:
                    logger.info("✅ Neo4j full-text index 'project_fulltext_search' available")
                else:
                    logger.warning(
                        "⚠️ Neo4j full-text index not found — falling back to CONTAINS. "
                        "Run: python scripts/create_neo4j_fulltext_index.py to create it."
                    )
            except Exception:
                self._neo4j_ft_available = False
        return self._neo4j_ft_available

    async def _search_graph(
        self, search_terms: list[str], filters: dict[str, Any], limit: int
    ) -> list[dict[str, Any]]:
        """
        Search Neo4j for projects matching criteria.

        Uses full-text index (Lucene) when available for ranked relevance scoring,
        falls back to CONTAINS substring matching otherwise.
        """
        if not self._graph_service:
            return []

        try:
            search_query = " ".join(search_terms)
            params = {"limit": limit}
            use_fulltext = self._has_neo4j_fulltext_index()

            # Check if we need country filtering
            has_country_filter = "countries" in filters and filters["countries"]

            status_clause = ""
            if "status" in filters:
                status_clause = "AND p.status = $status"
                params["status"] = filters["status"]

            if use_fulltext:
                # Full-text search with Lucene scoring — much faster and more accurate
                # Escape special Lucene characters and build query
                lucene_query = self._build_lucene_query(search_terms)
                params["search"] = lucene_query

                if has_country_filter:
                    params["countries"] = filters["countries"]
                    cypher = f"""
                    CALL db.index.fulltext.queryNodes('project_fulltext_search', $search)
                    YIELD node AS p, score AS ft_score

                    // Country filter via organization
                    WHERE EXISTS {{
                        MATCH (o:Organization)-[:PARTICIPATES_IN]->(p)
                        WHERE o.country IN $countries
                    }}
                    {status_clause}

                    WITH p, ft_score

                    // Get related cluster and topic info
                    OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
                    OPTIONAL MATCH (p)-[:FUNDED_UNDER]->(t:Topic)
                    OPTIONAL MATCH (coord:Organization)-[r:PARTICIPATES_IN {{role: 'coordinator'}}]->(p)

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
                           COLLECT(DISTINCT t.code) as topicCodes,
                           coord.name as coordinatorName,
                           coord.country as coordinatorCountry,
                           ft_score
                    ORDER BY ft_score DESC
                    LIMIT $limit
                    """
                else:
                    cypher = f"""
                    CALL db.index.fulltext.queryNodes('project_fulltext_search', $search)
                    YIELD node AS p, score AS ft_score

                    WHERE true {status_clause}

                    WITH p, ft_score

                    // Get related cluster and topic info
                    OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
                    OPTIONAL MATCH (p)-[:FUNDED_UNDER]->(t:Topic)
                    OPTIONAL MATCH (coord:Organization)-[r:PARTICIPATES_IN {{role: 'coordinator'}}]->(p)

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
                           COLLECT(DISTINCT t.code) as topicCodes,
                           coord.name as coordinatorName,
                           coord.country as coordinatorCountry,
                           ft_score
                    ORDER BY ft_score DESC
                    LIMIT $limit
                    """
            else:
                # Fallback: CONTAINS substring matching (slow, no relevance scoring)
                params["search"] = search_query

                if has_country_filter:
                    params["countries"] = filters["countries"]
                    cypher = f"""
                    MATCH (o:Organization)-[:PARTICIPATES_IN]->(p:Project)
                    WHERE o.country IN $countries
                      AND (toLower(p.title) CONTAINS toLower($search)
                           OR toLower(p.objective) CONTAINS toLower($search))
                      {status_clause}

                    WITH DISTINCT p

                    OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
                    OPTIONAL MATCH (p)-[:FUNDED_UNDER]->(t:Topic)
                    OPTIONAL MATCH (coord:Organization)-[r:PARTICIPATES_IN {{role: 'coordinator'}}]->(p)

                    RETURN p.id as id, p.title as title, p.acronym as acronym,
                           p.objective as objective, p.startDate as startDate,
                           p.endDate as endDate, p.totalCost as totalCost,
                           p.ecMaxContribution as ecMaxContribution,
                           p.status as status, p.fundingScheme as fundingScheme,
                           COLLECT(DISTINCT c.name)[0] as clusterName,
                           COLLECT(DISTINCT c.code)[0] as clusterCode,
                           COLLECT(DISTINCT t.code) as topicCodes,
                           coord.name as coordinatorName,
                           coord.country as coordinatorCountry
                    ORDER BY p.startDate DESC
                    LIMIT $limit
                    """
                else:
                    cypher = f"""
                    MATCH (p:Project)
                    WHERE (toLower(p.title) CONTAINS toLower($search)
                           OR toLower(p.objective) CONTAINS toLower($search))
                      {status_clause}

                    OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
                    OPTIONAL MATCH (p)-[:FUNDED_UNDER]->(t:Topic)
                    OPTIONAL MATCH (coord:Organization)-[r:PARTICIPATES_IN {{role: 'coordinator'}}]->(p)

                    RETURN p.id as id, p.title as title, p.acronym as acronym,
                           p.objective as objective, p.startDate as startDate,
                           p.endDate as endDate, p.totalCost as totalCost,
                           p.ecMaxContribution as ecMaxContribution,
                           p.status as status, p.fundingScheme as fundingScheme,
                           COLLECT(DISTINCT c.name)[0] as clusterName,
                           COLLECT(DISTINCT c.code)[0] as clusterCode,
                           COLLECT(DISTINCT t.code) as topicCodes,
                           coord.name as coordinatorName,
                           coord.country as coordinatorCountry
                    ORDER BY p.startDate DESC
                    LIMIT $limit
                    """

            results = self._graph_service.db.execute_query(cypher, params)

            # Convert to standard format
            formatted = []
            for i, r in enumerate(results):
                topic_codes = r.get("topicCodes") or []
                formatted.append(
                    {
                        "id": r.get("id"),
                        "rcn": "",  # Not in Neo4j
                        "title": r.get("title"),
                        "acronym": r.get("acronym"),
                        "objective": (r.get("objective") or "")[:500],
                        "startDate": r.get("startDate"),
                        "endDate": r.get("endDate"),
                        "totalCost": r.get("totalCost", 0),
                        "ecMaxContribution": r.get("ecMaxContribution", 0),
                        "status": r.get("status"),
                        "frameworkProgramme": "",  # Not in Neo4j Project node
                        "fundingScheme": r.get("fundingScheme"),
                        "topics": ", ".join([t for t in topic_codes if t]) if topic_codes else "",
                        "cluster_name": r.get("clusterName"),
                        "cluster_code": r.get("clusterCode"),
                        "coordinator_name": r.get("coordinatorName"),
                        "coordinator_country": r.get("coordinatorCountry"),
                        "_source": "neo4j",
                        "_rank": i + 1,
                        "_ft_score": r.get("ft_score"),  # Lucene relevance score (if available)
                    }
                )

            return formatted

        except Exception as e:
            logger.error(f"Neo4j search error: {e}")
            return []

    @staticmethod
    def _build_lucene_query(search_terms: list[str]) -> str:
        """Build a Lucene query string for Neo4j full-text search.

        Escapes special characters and joins terms with OR for broad matching,
        while also including the exact phrase for boost.
        """
        # Lucene special chars that need escaping
        special = set('+-&|!(){}[]^"~*?:\\/]')
        escaped = []
        for term in search_terms:
            clean = "".join(f"\\{c}" if c in special else c for c in term)
            if clean:
                escaped.append(clean)

        if not escaped:
            return ""

        # Combine: individual terms OR + exact phrase boost
        parts = escaped.copy()
        if len(escaped) > 1:
            # Boost exact phrase match
            phrase = " ".join(escaped)
            parts.append(f'"{phrase}"^2')

        return " OR ".join(parts)

    async def search_projects_by_relationship(
        self, relationship_type: str, entity_value: str, limit: int = 20
    ) -> dict[str, Any]:
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
            return {"success": False, "error": "Graph service not available", "projects": []}

        try:
            params = {"value": entity_value, "limit": limit}

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
                return {
                    "success": False,
                    "error": f"Unknown relationship type: {relationship_type}",
                    "projects": [],
                }

            results = self._graph_service.db.execute_query(cypher, params)

            projects = []
            for r in results:
                projects.append(
                    {
                        "id": r.get("id"),
                        "title": r.get("title"),
                        "acronym": r.get("acronym"),
                        "objective": (r.get("objective") or "")[:300],
                        "status": r.get("status"),
                        "budget": r.get("budget", 0),
                        "funding_scheme": r.get("scheme"),
                        "cluster_name": r.get("clusterName"),
                        "cluster_code": r.get("clusterCode"),
                        "topic_code": r.get("topicCode"),
                        "org_name": r.get("orgName"),
                        "org_country": r.get("orgCountry"),
                        "org_count": r.get("orgCount"),
                        "cordis_url": f"https://cordis.europa.eu/project/id/{r.get('id')}",
                    }
                )

            return {
                "success": True,
                "relationship_type": relationship_type,
                "entity": entity_value,
                "projects": projects,
                "total_found": len(projects),
            }

        except Exception as e:
            logger.error(f"Relationship search error: {e}")
            return {"success": False, "error": str(e), "projects": []}

    async def _rerank_with_cross_encoder(
        self,
        query: str,
        results: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Rerank top candidates using cross-encoder for better relevance.

        Only reranks the top candidates (up to 2x limit, max 50) to keep latency
        acceptable. Falls back to original ordering if reranker unavailable.
        """
        if len(results) < 2:
            return results

        # Only rerank a reasonable number of candidates
        rerank_count = min(len(results), max(limit * 2, 20), 50)
        candidates = results[:rerank_count]
        remainder = results[rerank_count:]

        try:
            from .data_intelligence.cross_encoder_reranker import get_reranker

            reranker = get_reranker(model_type="fast")

            # Run reranking in thread to not block async loop
            ranked = await asyncio.to_thread(
                reranker.rerank,
                query=query,
                documents=candidates,
                content_key="objective",  # Rank on project objective text
                top_k=rerank_count,
            )

            if ranked:
                # Rebuild result list from reranked order
                reranked_results = [r.to_dict() for r in ranked]
                logger.info(
                    f"   Cross-encoder reranked {len(candidates)} candidates "
                    f"(top moved: {reranked_results[0].get('acronym', '?')})"
                )
                return reranked_results + remainder

        except ImportError:
            logger.debug(
                "Cross-encoder reranker not available (sentence-transformers not installed)"
            )
        except Exception as e:
            logger.warning(f"Cross-encoder reranking failed, using RRF order: {e}")

        return results

    def _reciprocal_rank_fusion(
        self, results_by_source: dict[str, list[dict]], k: int = 60
    ) -> list[dict[str, Any]]:
        """
        Combine rankings using Reciprocal Rank Fusion.

        RRF score = Σ 1/(k + rank) for each list the item appears in.
        Higher k gives more weight to items appearing in multiple lists.
        """
        scores = {}
        projects_map = {}

        for source, projects in results_by_source.items():
            for project in projects:
                pid = str(project.get("id"))
                rank = project.get("_rank", 1)

                if pid not in scores:
                    scores[pid] = 0
                    projects_map[pid] = project.copy()
                    projects_map[pid]["_sources"] = []

                scores[pid] += 1 / (k + rank)
                projects_map[pid]["_sources"].append(source)

        # Boost projects found by multiple sources (higher confidence)
        for pid in scores:
            num_sources = len(projects_map[pid]["_sources"])
            if num_sources >= 3:
                scores[pid] *= 1.15  # Found by all 3 sources — strong signal
            elif num_sources >= 2:
                scores[pid] *= 1.05  # Found by 2 sources — moderate boost

        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        results = []
        for pid in sorted_ids:
            project = projects_map[pid]
            project["_rrf_score"] = scores[pid]
            results.append(project)

        return results

    def _deduplicate(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate projects, merging fields from all versions.

        Keeps the highest-scored version as the base but fills in missing
        fields from duplicate entries (e.g., Neo4j version may lack totalCost
        but PostgreSQL version has it).
        """
        seen: dict[str, dict[str, Any]] = {}
        unique = []

        for project in results:
            pid = str(project.get("id"))
            if pid not in seen:
                seen[pid] = project
                unique.append(project)
            else:
                # Merge: fill in missing fields from this duplicate
                existing = seen[pid]
                for key, value in project.items():
                    if key.startswith("_"):
                        # Merge source tracking lists
                        if key == "_sources" and isinstance(value, list):
                            existing_sources = existing.get("_sources", [])
                            for s in value:
                                if s not in existing_sources:
                                    existing_sources.append(s)
                            existing["_sources"] = existing_sources
                        continue
                    existing_val = existing.get(key)
                    if existing_val in (None, "", 0, [], {}):
                        existing[key] = value

        return unique

    def _enrich_coordinator_data(self, projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Enrich projects with coordinator data from PostgreSQL.

        Neo4j and Vector search results may not include coordinator info.
        This method fetches coordinator data for projects missing it.

        Args:
            projects: List of project dictionaries

        Returns:
            Projects with coordinator_name and coordinator_country populated
        """
        if not self._postgres_repo or not self._postgres_repo.db_pool:
            return projects

        # Find projects missing coordinator data
        projects_needing_enrichment = []
        for p in projects:
            # Check if coordinator info is missing
            has_coordinator = (
                p.get("coordinator_name") is not None
                or p.get("coordinator", {}).get("name") is not None
            )
            if not has_coordinator and p.get("id"):
                projects_needing_enrichment.append(str(p.get("id")))

        if not projects_needing_enrichment:
            return projects

        logger.info(
            f"📡 Enriching coordinator data for {len(projects_needing_enrichment)} projects"
        )

        try:
            conn = self._postgres_repo.db_pool.getconn()
            cursor = conn.cursor()

            # Batch fetch coordinator data
            placeholders = ",".join(["%s"] * len(projects_needing_enrichment))
            cursor.execute(
                f"""
                SELECT
                    p.id,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.name END) as coordinator_name,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.country END) as coordinator_country,
                    COUNT(DISTINCT o."organisationID") as participant_count,
                    COUNT(DISTINCT o.country) as country_count,
                    COUNT(CASE WHEN o."SME" = true THEN 1 END) as sme_count,
                    ARRAY_AGG(DISTINCT o.country) FILTER (WHERE o.country IS NOT NULL) as participant_countries
                FROM projects p
                LEFT JOIN organizations o ON p.id = o."projectID"
                WHERE p.id IN ({placeholders})
                GROUP BY p.id
            """,
                projects_needing_enrichment,
            )

            # Build lookup map
            coordinator_map = {}
            for row in cursor.fetchall():
                coordinator_map[str(row[0])] = {
                    "coordinator_name": row[1],
                    "coordinator_country": row[2],
                    "participant_count": row[3] or 0,
                    "country_count": row[4] or 0,
                    "sme_count": row[5] or 0,
                    "participant_countries": row[6] or [],
                }

            cursor.close()
            self._postgres_repo.db_pool.putconn(conn)

            # Enrich projects
            enriched_count = 0
            for p in projects:
                pid = str(p.get("id"))
                if pid in coordinator_map:
                    coord_data = coordinator_map[pid]
                    p["coordinator_name"] = coord_data["coordinator_name"]
                    p["coordinator_country"] = coord_data["coordinator_country"]
                    # Also enrich consortium data if missing
                    if not p.get("participant_count"):
                        p["participant_count"] = coord_data["participant_count"]
                        p["country_count"] = coord_data["country_count"]
                        p["sme_count"] = coord_data["sme_count"]
                        p["participant_countries"] = coord_data["participant_countries"]
                    enriched_count += 1

            logger.info(f"✅ Enriched {enriched_count} projects with coordinator data")

        except Exception as e:
            logger.error(f"Failed to enrich coordinator data: {e}")

        return projects

    def _format_project(self, project: dict[str, Any]) -> dict[str, Any]:
        """Format project for API response."""
        project_id = project.get("id", "")

        # Get coordinator info - use "Data not yet available" for missing data
        coordinator_name = project.get("coordinator_name")
        coordinator_country = project.get("coordinator_country")

        # If coordinator info is None but project has organizations, it's truly unknown
        # Otherwise, mark as "data not yet available" for new projects
        if coordinator_name is None:
            coordinator_name = "Data not yet available"
        if coordinator_country is None:
            coordinator_country = "N/A"

        return {
            "id": project_id,
            "rcn": project.get("rcn", ""),
            "title": project.get("title", "Unknown Title"),
            "acronym": project.get("acronym"),
            "objective": self._truncate(project.get("objective", ""), 500),
            "start_date": project.get("startDate") or project.get("start_date", ""),
            "end_date": project.get("endDate") or project.get("end_date", ""),
            "status": project.get("status", "Unknown"),
            "total_cost": project.get("totalCost") or project.get("total_cost", 0),
            "ec_contribution": project.get("ecMaxContribution")
            or project.get("ec_max_contribution")
            or project.get("ec_contribution", 0),
            "programme": project.get("frameworkProgramme") or project.get("programme", ""),
            "funding_scheme": project.get("fundingScheme") or project.get("funding_scheme", ""),
            "topics": project.get("topics", ""),
            "coordinator": {"name": coordinator_name, "country": coordinator_country},
            "consortium": {
                "participant_count": project.get("participant_count", 0),
                "country_count": project.get("country_count", 0),
                "sme_count": project.get("sme_count", 0),
                "countries": project.get("participant_countries", []),
            },
            "cluster": {
                "name": project.get("cluster_name"),
                "code": project.get("cluster_code"),
            }
            if project.get("cluster_name") or project.get("cluster_code")
            else None,
            "relevance_score": project.get("_rrf_score", project.get("relevance_score", 0)),
            "similarity_score": project.get("similarity_score"),
            "sources": project.get("_sources", [project.get("_source", "unknown")]),
            "cordis_url": (
                f"https://cordis.europa.eu/project/id/{project_id}" if project_id else None
            ),
            "doi_url": (
                project.get("doi_url")
                or (f"https://doi.org/10.3030/{project_id}" if project_id else None)
            ),
        }

    def _format_project_from_dto(self, dto) -> dict[str, Any]:
        """Format a CordisProjectDTO for response."""
        return {
            "id": dto.id,
            "rcn": dto.rcn,
            "title": dto.title,
            "acronym": dto.acronym,
            "objective": self._truncate(dto.objective, 500),
            "start_date": dto.start_date,
            "end_date": dto.end_date,
            "status": dto.status,
            "total_cost": dto.total_cost,
            "ec_contribution": dto.ec_max_contribution,
            "programme": dto.framework_programme,
            "funding_scheme": dto.funding_scheme,
            "topics": dto.topics,
            "coordinator": {"name": dto.coordinator_name, "country": dto.coordinator_country},
            "consortium": {
                "participant_count": dto.participant_count,
                "country_count": dto.country_count,
                "sme_count": dto.sme_count,
                "countries": dto.participant_countries,
            },
            "relevance_score": dto.relevance_score,
            "sources": [dto.data_source],
            "cordis_url": f"https://cordis.europa.eu/project/id/{dto.id}",
            "doi_url": getattr(dto, "doi_url", None) or f"https://doi.org/10.3030/{dto.id}",
        }

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis."""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."


# Module-level instance for convenience
local_project_search = LocalProjectSearchService()
