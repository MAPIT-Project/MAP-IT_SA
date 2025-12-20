"""
Query Optimizer for Database Operations

Provides optimized SQL queries and index recommendations for the MAP-IT system.
Focuses on common query patterns and performance-critical operations.

Key Features:
- Optimized SQL templates for common queries
- Index recommendations for performance
- Query plan analysis helpers
- Connection pool optimization guidance
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries that can be optimized."""
    PROJECT_SEARCH = "project_search"
    PROJECT_BY_CLUSTER = "project_by_cluster"
    PROJECT_BY_ORGANIZATION = "project_by_organization"
    CALL_SEARCH = "call_search"
    CALL_OPEN = "call_open"
    ORGANIZATION_LOOKUP = "organization_lookup"
    EMBEDDING_LOOKUP = "embedding_lookup"
    STATISTICS_AGGREGATE = "statistics_aggregate"


@dataclass
class OptimizedQuery:
    """Container for an optimized query with metadata."""
    sql: str
    params: Dict[str, Any]
    query_type: QueryType
    estimated_cost: str  # "low", "medium", "high"
    uses_index: bool
    notes: Optional[str] = None


class QueryOptimizer:
    """Optimize database queries for better performance."""

    # SQL Templates for common queries
    SQL_TEMPLATES = {
        # Project search with full-text search (uses GIN index)
        "project_keyword_search": """
            SELECT
                p.id,
                p.rcn,
                p.acronym,
                p.title,
                p.status,
                p.start_date,
                p.end_date,
                p.total_cost,
                p.eu_contribution,
                p.objective,
                ts_rank(
                    to_tsvector('english', COALESCE(p.title, '') || ' ' || COALESCE(p.objective, '')),
                    plainto_tsquery('english', %(keywords)s)
                ) as rank
            FROM projects p
            WHERE
                to_tsvector('english', COALESCE(p.title, '') || ' ' || COALESCE(p.objective, ''))
                @@ plainto_tsquery('english', %(keywords)s)
            ORDER BY rank DESC
            LIMIT %(limit)s
        """,

        # Project search with status filter (uses partial index)
        "project_keyword_status_search": """
            SELECT
                p.id,
                p.rcn,
                p.acronym,
                p.title,
                p.status,
                p.start_date,
                p.end_date,
                p.total_cost,
                p.eu_contribution,
                p.objective,
                ts_rank(
                    to_tsvector('english', COALESCE(p.title, '') || ' ' || COALESCE(p.objective, '')),
                    plainto_tsquery('english', %(keywords)s)
                ) as rank
            FROM projects p
            WHERE
                p.status = %(status)s
                AND to_tsvector('english', COALESCE(p.title, '') || ' ' || COALESCE(p.objective, ''))
                    @@ plainto_tsquery('english', %(keywords)s)
            ORDER BY rank DESC
            LIMIT %(limit)s
        """,

        # Projects by cluster (uses index on programme)
        "projects_by_cluster": """
            SELECT
                p.id,
                p.rcn,
                p.acronym,
                p.title,
                p.status,
                p.total_cost,
                p.eu_contribution,
                p.objective
            FROM projects p
            WHERE p.programme ILIKE %(cluster_pattern)s
            ORDER BY p.start_date DESC NULLS LAST
            LIMIT %(limit)s
        """,

        # Open funding calls (uses partial index on status)
        "open_calls": """
            SELECT
                c.id,
                c.call_identifier,
                c.title,
                c.status,
                c.deadline,
                c.description,
                c.budget_overview,
                c.cluster
            FROM funding_calls c
            WHERE
                c.status = 'open'
                AND c.deadline > NOW()
            ORDER BY c.deadline ASC
            LIMIT %(limit)s
        """,

        # Calls with keyword search
        "call_keyword_search": """
            SELECT
                c.id,
                c.call_identifier,
                c.title,
                c.status,
                c.deadline,
                c.description,
                c.budget_overview,
                c.cluster,
                ts_rank(
                    to_tsvector('english', COALESCE(c.title, '') || ' ' || COALESCE(c.description, '')),
                    plainto_tsquery('english', %(keywords)s)
                ) as rank
            FROM funding_calls c
            WHERE
                to_tsvector('english', COALESCE(c.title, '') || ' ' || COALESCE(c.description, ''))
                @@ plainto_tsquery('english', %(keywords)s)
                AND (%(status)s IS NULL OR c.status = %(status)s)
            ORDER BY
                CASE WHEN c.status = 'open' THEN 0 ELSE 1 END,
                rank DESC
            LIMIT %(limit)s
        """,

        # Organization lookup by name (uses trigram index if available)
        "organization_by_name": """
            SELECT
                o.id,
                o.name,
                o.short_name,
                o.country,
                o.activity_type,
                o.ec_contribution_total
            FROM organizations o
            WHERE
                o.name ILIKE %(name_pattern)s
                OR o.short_name ILIKE %(name_pattern)s
            ORDER BY o.ec_contribution_total DESC NULLS LAST
            LIMIT %(limit)s
        """,

        # Project embeddings lookup (optimized for batch)
        "embeddings_batch": """
            SELECT
                pe.project_id,
                pe.embedding,
                p.title,
                p.acronym
            FROM project_embeddings pe
            JOIN projects p ON p.id = pe.project_id
            WHERE pe.project_id = ANY(%(project_ids)s)
        """,

        # Statistics aggregation (optimized with pre-computation hints)
        "project_statistics_by_cluster": """
            SELECT
                p.programme as cluster,
                COUNT(*) as project_count,
                SUM(p.total_cost) as total_cost,
                SUM(p.eu_contribution) as total_eu_contribution,
                AVG(p.total_cost) as avg_cost,
                AVG(p.eu_contribution) as avg_eu_contribution
            FROM projects p
            WHERE p.programme IS NOT NULL
            GROUP BY p.programme
            ORDER BY project_count DESC
        """,

        # Projects needing embeddings
        "projects_needing_embeddings": """
            SELECT p.id, p.rcn, p.title, p.objective
            FROM projects p
            LEFT JOIN project_embeddings pe ON p.id = pe.project_id
            WHERE
                pe.id IS NULL
                OR pe.embedding IS NULL
                OR pe.updated_at < p.updated_at
            ORDER BY p.updated_at DESC
            LIMIT %(limit)s
        """,
    }

    # Recommended indexes for optimal performance
    RECOMMENDED_INDEXES = [
        # Full-text search index for projects
        {
            "name": "idx_projects_fts",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_fts
                ON projects USING GIN(to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(objective, '')))
            """,
            "purpose": "Full-text search on project title and objective",
            "priority": "high",
        },
        # Full-text search index for calls
        {
            "name": "idx_calls_fts",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_calls_fts
                ON funding_calls USING GIN(to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, '')))
            """,
            "purpose": "Full-text search on call title and description",
            "priority": "high",
        },
        # Partial index for open calls
        {
            "name": "idx_calls_open",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_calls_open
                ON funding_calls(deadline)
                WHERE status = 'open'
            """,
            "purpose": "Fast lookup of open calls by deadline",
            "priority": "high",
        },
        # Index for project status
        {
            "name": "idx_projects_status",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_status
                ON projects(status)
            """,
            "purpose": "Filter projects by status",
            "priority": "medium",
        },
        # Index for project programme/cluster
        {
            "name": "idx_projects_programme",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_programme
                ON projects(programme)
            """,
            "purpose": "Filter projects by programme/cluster",
            "priority": "medium",
        },
        # Index for organization name search
        {
            "name": "idx_orgs_name",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orgs_name
                ON organizations(name, country)
            """,
            "purpose": "Organization lookup by name and country",
            "priority": "medium",
        },
        # Index for project embeddings
        {
            "name": "idx_embeddings_project_id",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_project_id
                ON project_embeddings(project_id)
            """,
            "purpose": "Fast embedding lookup by project ID",
            "priority": "high",
        },
        # Index for document chunks embedding search (if using pgvector)
        {
            "name": "idx_chunks_embedding_ivfflat",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_embedding_ivfflat
                ON document_chunks USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """,
            "purpose": "Fast vector similarity search on document chunks",
            "priority": "high",
            "requires": "pgvector",
        },
        # Index for project embeddings vector search
        {
            "name": "idx_project_embeddings_ivfflat",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_project_embeddings_ivfflat
                ON project_embeddings USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """,
            "purpose": "Fast vector similarity search on project embeddings",
            "priority": "high",
            "requires": "pgvector",
        },
    ]

    @classmethod
    def get_optimized_query(
        cls,
        query_type: str,
        params: Dict[str, Any]
    ) -> OptimizedQuery:
        """
        Get an optimized query for the given type and parameters.

        Args:
            query_type: Type of query (from SQL_TEMPLATES keys)
            params: Query parameters

        Returns:
            OptimizedQuery with SQL and metadata
        """
        if query_type not in cls.SQL_TEMPLATES:
            raise ValueError(f"Unknown query type: {query_type}")

        sql = cls.SQL_TEMPLATES[query_type]

        # Determine query characteristics
        uses_index = any(idx in query_type for idx in ["fts", "status", "cluster", "open"])
        cost = "low" if uses_index else "medium"

        return OptimizedQuery(
            sql=sql.strip(),
            params=params,
            query_type=QueryType(query_type) if query_type in [e.value for e in QueryType] else QueryType.PROJECT_SEARCH,
            estimated_cost=cost,
            uses_index=uses_index
        )

    @classmethod
    def optimize_project_search(
        cls,
        keywords: str,
        status: Optional[str] = None,
        cluster: Optional[str] = None,
        limit: int = 20
    ) -> OptimizedQuery:
        """
        Get optimized query for project search.

        Args:
            keywords: Search keywords
            status: Optional status filter
            cluster: Optional cluster filter
            limit: Maximum results

        Returns:
            OptimizedQuery for project search
        """
        if status:
            return cls.get_optimized_query(
                "project_keyword_status_search",
                {"keywords": keywords, "status": status, "limit": limit}
            )
        else:
            return cls.get_optimized_query(
                "project_keyword_search",
                {"keywords": keywords, "limit": limit}
            )

    @classmethod
    def optimize_call_search(
        cls,
        keywords: Optional[str] = None,
        status: str = "open",
        limit: int = 20
    ) -> OptimizedQuery:
        """
        Get optimized query for call search.

        Args:
            keywords: Optional search keywords
            status: Call status filter
            limit: Maximum results

        Returns:
            OptimizedQuery for call search
        """
        if status == "open" and not keywords:
            return cls.get_optimized_query(
                "open_calls",
                {"limit": limit}
            )
        else:
            return cls.get_optimized_query(
                "call_keyword_search",
                {"keywords": keywords or "", "status": status if status != "all" else None, "limit": limit}
            )

    @classmethod
    def get_missing_indexes(cls, existing_indexes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get list of recommended indexes that don't exist yet.

        Args:
            existing_indexes: List of existing index names (if known)

        Returns:
            List of index recommendations
        """
        existing = set(existing_indexes or [])

        missing = [
            idx for idx in cls.RECOMMENDED_INDEXES
            if idx["name"] not in existing
        ]

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        missing.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))

        return missing

    @classmethod
    def get_index_creation_sql(cls, priority: str = "all") -> str:
        """
        Get SQL to create recommended indexes.

        Args:
            priority: Filter by priority ("high", "medium", "low", or "all")

        Returns:
            SQL statements for index creation
        """
        indexes = cls.RECOMMENDED_INDEXES

        if priority != "all":
            indexes = [idx for idx in indexes if idx.get("priority") == priority]

        sql_parts = []
        for idx in indexes:
            requires = idx.get("requires")
            if requires:
                sql_parts.append(f"-- Requires {requires} extension")
            sql_parts.append(f"-- {idx['purpose']}")
            sql_parts.append(idx["sql"].strip() + ";")
            sql_parts.append("")

        return "\n".join(sql_parts)

    @classmethod
    def estimate_query_cost(cls, query: str) -> Dict[str, Any]:
        """
        Estimate query cost based on query patterns.

        This is a heuristic-based estimation without running EXPLAIN.

        Args:
            query: SQL query string

        Returns:
            Cost estimation dict
        """
        query_lower = query.lower()

        cost_factors = {
            "uses_fts": "to_tsvector" in query_lower or "@@" in query_lower,
            "uses_index_hint": "using" in query_lower,
            "has_order_by": "order by" in query_lower,
            "has_group_by": "group by" in query_lower,
            "has_subquery": query_lower.count("select") > 1,
            "has_join": "join" in query_lower,
            "has_limit": "limit" in query_lower,
            "has_distinct": "distinct" in query_lower,
        }

        # Calculate estimated cost
        base_cost = 1.0
        if cost_factors["has_subquery"]:
            base_cost *= 2.0
        if cost_factors["has_join"]:
            base_cost *= 1.5
        if cost_factors["has_group_by"]:
            base_cost *= 1.3
        if cost_factors["uses_fts"]:
            base_cost *= 0.8  # FTS with index is efficient
        if cost_factors["has_limit"]:
            base_cost *= 0.5  # Limit reduces cost

        cost_level = "low" if base_cost < 1.5 else ("medium" if base_cost < 3.0 else "high")

        return {
            "estimated_cost": cost_level,
            "cost_score": round(base_cost, 2),
            "factors": cost_factors,
            "recommendations": cls._get_query_recommendations(cost_factors)
        }

    @classmethod
    def _get_query_recommendations(cls, factors: Dict[str, bool]) -> List[str]:
        """Get recommendations based on query factors."""
        recommendations = []

        if factors.get("has_subquery"):
            recommendations.append("Consider using CTEs or JOINs instead of subqueries")
        if factors.get("has_group_by") and not factors.get("has_limit"):
            recommendations.append("Add LIMIT to prevent large result sets")
        if not factors.get("uses_fts") and not factors.get("has_limit"):
            recommendations.append("Consider adding full-text search index or LIMIT clause")

        return recommendations


# Migration SQL for creating recommended indexes
MIGRATION_SQL = """
-- Migration: Add recommended indexes for query optimization
-- Generated by QueryOptimizer

-- Transaction wrapper
BEGIN;

-- Check if we have the pgvector extension (for vector indexes)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE NOTICE 'pgvector extension found, vector indexes will be created';
    ELSE
        RAISE NOTICE 'pgvector extension not found, skipping vector indexes';
    END IF;
END
$$;

-- Full-text search index for projects
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_fts
ON projects USING GIN(to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(objective, '')));

-- Full-text search index for calls
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_calls_fts
ON funding_calls USING GIN(to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, '')));

-- Partial index for open calls
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_calls_open
ON funding_calls(deadline)
WHERE status = 'open';

-- Index for project status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_status
ON projects(status);

-- Index for project programme/cluster
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_programme
ON projects(programme);

-- Index for organization lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orgs_name
ON organizations(name, country);

-- Index for project embeddings
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_project_id
ON project_embeddings(project_id);

-- Vector indexes (only if pgvector extension is available)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        -- Document chunks vector index
        EXECUTE '
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_embedding_ivfflat
            ON document_chunks USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        ';

        -- Project embeddings vector index
        EXECUTE '
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_project_embeddings_ivfflat
            ON project_embeddings USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        ';

        RAISE NOTICE 'Vector indexes created successfully';
    END IF;
END
$$;

-- Analyze tables to update statistics
ANALYZE projects;
ANALYZE funding_calls;
ANALYZE organizations;
ANALYZE project_embeddings;

COMMIT;

-- Verify indexes were created
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
"""
