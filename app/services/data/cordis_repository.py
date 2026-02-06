"""
CORDIS Project Repository - PostgreSQL data access layer.

Provides full-text search and structured queries for CORDIS project data
stored in the local PostgreSQL database.
"""

import logging
import os
import re
from dataclasses import asdict, dataclass
from typing import Any

from dotenv import load_dotenv
from psycopg2 import pool

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class CordisProjectDTO:
    """Data Transfer Object for CORDIS project data."""

    id: str
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
    cordis_url: str

    def to_dict(self) -> dict[str, Any]:
        """Convert DTO to dictionary."""
        return asdict(self)


class CordisProjectRepository:
    """
    Repository for accessing CORDIS project data from PostgreSQL.

    Provides:
    - Full-text search on project titles, objectives, and topics
    - Structured filtering by programme, country, date, budget
    - Organization joins for consortium data
    """

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

    def __init__(self, database_url: str | None = None, min_conn: int = 1, max_conn: int = 10):
        """
        Initialize the repository with a database connection pool.

        Args:
            database_url: PostgreSQL connection string
            min_conn: Minimum pool connections
            max_conn: Maximum pool connections
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")

        try:
            self.db_pool = pool.ThreadedConnectionPool(min_conn, max_conn, self.database_url)
            logger.info("✅ CORDIS repository connected to PostgreSQL")
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise

    def _convert_to_tsquery(self, terms: list[str]) -> str:
        """
        Convert search terms to PostgreSQL tsquery format.

        Args:
            terms: List of search terms

        Returns:
            PostgreSQL tsquery string
        """
        if not terms:
            return ""

        # Clean and filter terms (keep important short terms like AI, ML, etc.)
        clean_terms = []
        for term in terms:
            # Remove special characters
            clean = re.sub(r"[^\w\s]", "", term.strip()).lower()
            if clean and (len(clean) > 1 or clean in self.IMPORTANT_SHORT_TERMS):
                clean_terms.append(clean)

        if not clean_terms:
            return ""

        # Join with OR for flexible matching
        return " | ".join(clean_terms)

    def search_projects(
        self, queries: list[str], filters: dict[str, Any] | None = None, limit: int = 10
    ) -> tuple[list[CordisProjectDTO], int]:
        """
        Search projects using full-text search and filters.

        Args:
            queries: List of search terms
            filters: Optional filters:
                - programme: str (e.g., "HORIZON", "H2020")
                - countries: List[str] (e.g., ["DE", "FR"])
                - date_range: Dict with 'start' and/or 'end'
                - budget_range: Dict with 'min' and/or 'max'
                - status: str (e.g., "SIGNED", "CLOSED")
            limit: Maximum results to return

        Returns:
            Tuple of (list of projects, total count)
        """
        filters = filters or {}
        conn = None

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Build base query
            params = []
            where_clauses = []

            # Full-text search
            tsquery = self._convert_to_tsquery(queries)
            if tsquery:
                where_clauses.append("""
                    (to_tsvector('english', COALESCE(p.title, '') || ' ' || COALESCE(p.objective, '') || ' ' || COALESCE(p.topics, ''))
                    @@ to_tsquery('english', %s))
                """)
                params.append(tsquery)

            # Programme filter (using camelCase column name)
            if "programme" in filters:
                where_clauses.append('p."frameworkProgramme" = %s')
                params.append(filters["programme"])

            # Country filter
            if "countries" in filters and filters["countries"]:
                where_clauses.append("""
                    EXISTS (
                        SELECT 1 FROM organizations o
                        WHERE o."projectID" = p.id
                        AND o.country = ANY(%s)
                    )
                """)
                params.append(filters["countries"])

            # Status filter
            if "status" in filters:
                where_clauses.append("p.status = %s")
                params.append(filters["status"])

            # Date range filter (using camelCase column names)
            if "date_range" in filters:
                date_range = filters["date_range"]
                if "start" in date_range:
                    where_clauses.append('p."startDate" >= %s')
                    params.append(date_range["start"])
                if "end" in date_range:
                    where_clauses.append('p."endDate" <= %s')
                    params.append(date_range["end"])

            # Budget range filter (using camelCase column names)
            if "budget_range" in filters:
                budget_range = filters["budget_range"]
                if "min" in budget_range:
                    where_clauses.append('p."totalCost" >= %s')
                    params.append(budget_range["min"])
                if "max" in budget_range:
                    where_clauses.append('p."totalCost" <= %s')
                    params.append(budget_range["max"])

            where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

            # Count query
            count_sql = f"""
                SELECT COUNT(*) FROM projects p
                WHERE {where_sql}
            """
            cursor.execute(count_sql, params)
            total_count = cursor.fetchone()[0]

            # Main query with organization aggregation
            # Note: PostgreSQL column names use camelCase with quotes
            params.append(limit)
            main_sql = f"""
                SELECT
                    p.id,
                    p.rcn,
                    p.title,
                    p.acronym,
                    COALESCE(LEFT(p.objective, 1000), '') as objective,
                    p."startDate",
                    p."endDate",
                    p.status,
                    COALESCE(p."totalCost", 0) as total_cost,
                    COALESCE(p."ecMaxContribution", 0) as ec_contribution,
                    p."frameworkProgramme",
                    p."fundingScheme",
                    COALESCE(p.topics, '') as topics,
                    coord.name as coordinator_name,
                    coord.country as coordinator_country,
                    (SELECT COUNT(*) FROM organizations WHERE "projectID" = p.id) as participant_count,
                    (SELECT COUNT(DISTINCT country) FROM organizations WHERE "projectID" = p.id) as country_count,
                    (SELECT COUNT(*) FROM organizations WHERE "projectID" = p.id AND "SME" = true) as sme_count,
                    ARRAY(SELECT DISTINCT country FROM organizations WHERE "projectID" = p.id) as participant_countries
                FROM projects p
                LEFT JOIN organizations coord ON coord."projectID" = p.id AND coord.role = 'coordinator'
                WHERE {where_sql}
                ORDER BY p."startDate" DESC
                LIMIT %s
            """

            cursor.execute(main_sql, params)
            rows = cursor.fetchall()

            # Convert to DTOs
            projects = []
            for row in rows:
                project = CordisProjectDTO(
                    id=row[0] or "",
                    rcn=row[1] or "",
                    title=row[2] or "",
                    acronym=row[3],
                    objective=row[4] or "",
                    start_date=str(row[5]) if row[5] else "",
                    end_date=str(row[6]) if row[6] else "",
                    status=row[7] or "",
                    total_cost=float(row[8]) if row[8] else 0.0,
                    ec_contribution=float(row[9]) if row[9] else 0.0,
                    programme=row[10] or "",
                    funding_scheme=row[11] or "",
                    topics=row[12] or "",
                    coordinator_name=row[13],
                    coordinator_country=row[14],
                    participant_count=row[15] or 0,
                    country_count=row[16] or 0,
                    sme_count=row[17] or 0,
                    participant_countries=row[18] or [],
                    cordis_url=f"https://cordis.europa.eu/project/id/{row[0]}" if row[0] else "",
                )
                projects.append(project)

            cursor.close()
            return projects, total_count

        except Exception as e:
            logger.error(f"Search error: {e}")
            return [], 0
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def get_project_by_rcn(self, rcn: str) -> CordisProjectDTO | None:
        """
        Get a project by its RCN or ID.

        Args:
            rcn: Project RCN or ID

        Returns:
            CordisProjectDTO or None if not found
        """
        return self.get_project_by_id(rcn)

    def get_project_by_id(self, project_id: str) -> CordisProjectDTO | None:
        """
        Get a project by its ID.

        Args:
            project_id: Project ID or RCN

        Returns:
            CordisProjectDTO or None if not found
        """
        conn = None

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Note: PostgreSQL column names use camelCase with quotes
            sql = """
                SELECT
                    p.id,
                    p.rcn,
                    p.title,
                    p.acronym,
                    COALESCE(p.objective, '') as objective,
                    p."startDate",
                    p."endDate",
                    p.status,
                    COALESCE(p."totalCost", 0) as total_cost,
                    COALESCE(p."ecMaxContribution", 0) as ec_contribution,
                    p."frameworkProgramme",
                    p."fundingScheme",
                    COALESCE(p.topics, '') as topics,
                    coord.name as coordinator_name,
                    coord.country as coordinator_country,
                    (SELECT COUNT(*) FROM organizations WHERE "projectID" = p.id) as participant_count,
                    (SELECT COUNT(DISTINCT country) FROM organizations WHERE "projectID" = p.id) as country_count,
                    (SELECT COUNT(*) FROM organizations WHERE "projectID" = p.id AND "SME" = true) as sme_count,
                    ARRAY(SELECT DISTINCT country FROM organizations WHERE "projectID" = p.id) as participant_countries
                FROM projects p
                LEFT JOIN organizations coord ON coord."projectID" = p.id AND coord.role = 'coordinator'
                WHERE p.id = %s OR p.rcn = %s
                LIMIT 1
            """

            cursor.execute(sql, (project_id, project_id))
            row = cursor.fetchone()

            if not row:
                cursor.close()
                return None

            project = CordisProjectDTO(
                id=row[0] or "",
                rcn=row[1] or "",
                title=row[2] or "",
                acronym=row[3],
                objective=row[4] or "",
                start_date=str(row[5]) if row[5] else "",
                end_date=str(row[6]) if row[6] else "",
                status=row[7] or "",
                total_cost=float(row[8]) if row[8] else 0.0,
                ec_contribution=float(row[9]) if row[9] else 0.0,
                programme=row[10] or "",
                funding_scheme=row[11] or "",
                topics=row[12] or "",
                coordinator_name=row[13],
                coordinator_country=row[14],
                participant_count=row[15] or 0,
                country_count=row[16] or 0,
                sme_count=row[17] or 0,
                participant_countries=row[18] or [],
                cordis_url=f"https://cordis.europa.eu/project/id/{row[0]}" if row[0] else "",
            )

            cursor.close()
            return project

        except Exception as e:
            logger.error(f"Get project error: {e}")
            return None
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def get_project_count(self) -> int:
        """Get total count of projects in the database."""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM projects")
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            logger.error(f"Count error: {e}")
            return 0
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def close(self):
        """Close all database connections."""
        if self.db_pool:
            self.db_pool.closeall()
            logger.info("🔒 CORDIS repository connections closed")
