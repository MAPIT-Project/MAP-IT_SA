"""
Repository for local-first CORDIS project data access.
Encapsulates queries against curated tables (cordis_processed.projects_enriched,
cordis_processed.organizations_enriched, cordis_processed.results_enriched).
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import DictCursor, RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class CordisProjectDTO:
    """Data transfer object for enriched CORDIS project data."""
    def __init__(
        self,
        id: str,
        rcn: str,
        title: str,
        acronym: Optional[str],
        objective: str,
        start_date: str,
        end_date: str,
        total_cost: float,
        ec_max_contribution: float,
        status: str,
        framework_programme: str,
        funding_scheme: str,
        legal_basis: str,
        topics: str,
        grant_doi: str,
        participant_count: int,
        country_count: int,
        sme_count: int,
        coordinator_name: Optional[str],
        coordinator_country: Optional[str],
        participant_names: List[str],
        participant_countries: List[str],
        participant_cities: List[str],
        total_ec_contribution: float,
        nuts_codes: List[str],
        activity_types: List[str],
        relevance_score: float = 0.0,
        data_source: str = "local_cordis"
    ):
        self.id = id
        self.rcn = rcn
        self.title = title
        self.acronym = acronym
        self.objective = objective
        self.start_date = start_date
        self.end_date = end_date
        self.total_cost = total_cost
        self.ec_max_contribution = ec_max_contribution
        self.status = status
        self.framework_programme = framework_programme
        self.funding_scheme = funding_scheme
        self.legal_basis = legal_basis
        self.topics = topics
        self.grant_doi = grant_doi
        self.participant_count = participant_count
        self.country_count = country_count
        self.sme_count = sme_count
        self.coordinator_name = coordinator_name
        self.coordinator_country = coordinator_country
        self.participant_names = participant_names
        self.participant_countries = participant_countries
        self.participant_cities = participant_cities
        self.total_ec_contribution = total_ec_contribution
        self.nuts_codes = nuts_codes
        self.activity_types = activity_types
        self.relevance_score = relevance_score
        self.data_source = data_source

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for downstream compatibility."""
        return {
            'id': self.id,
            'rcn': self.rcn,
            'title': self.title,
            'acronym': self.acronym,
            'objective': self.objective,
            'startDate': self.start_date,
            'endDate': self.end_date,
            'totalCost': self.total_cost,
            'ecMaxContribution': self.ec_max_contribution,
            'status': self.status,
            'frameworkProgramme': self.framework_programme,
            'fundingScheme': self.funding_scheme,
            'legalBasis': self.legal_basis,
            'topics': self.topics,
            'grantDoi': self.grant_doi,
            'participant_count': self.participant_count,
            'country_count': self.country_count,
            'sme_count': self.sme_count,
            'coordinator_name': self.coordinator_name,
            'coordinator_country': self.coordinator_country,
            'participant_names': self.participant_names,
            'participant_countries': self.participant_countries,
            'participant_cities': self.participant_cities,
            'total_ec_contribution': self.total_ec_contribution,
            'nuts_codes': self.nuts_codes,
            'activity_types': self.activity_types,
            'relevance_score': self.relevance_score,
            'data_source': self.data_source
        }


class CordisProjectRepository:
    """Repository for local CORDIS project data access with change tracking."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize repository with database connection pool."""
        self.db_url = database_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL required for CordisProjectRepository")
        
        try:
            min_conn = int(os.getenv("DB_MIN_CONNECTIONS", "5"))
            max_conn = int(os.getenv("DB_MAX_CONNECTIONS", "20"))
            self.db_pool = SimpleConnectionPool(min_conn, max_conn, self.db_url)
            logger.info("✅ CordisProjectRepository: Database connection pool established")
        except Exception as e:
            logger.error(f"❌ Failed to create database pool: {e}")
            raise

    def search_projects(
        self,
        queries: List[str],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Tuple[List[CordisProjectDTO], int]:
        """
        Search projects with full-text and structured filters.
        
        Args:
            queries: Text search queries
            filters: Optional structured filters (programme, date_range, budget_range, countries)
            limit: Maximum results to return
            offset: Pagination offset
            
        Returns:
            Tuple of (project DTOs, total count)
        """
        if not self.db_pool:
            logger.error("❌ Database pool not available")
            return [], 0
        
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            # Build WHERE conditions and parameters
            where_conditions = []
            params = []
            
            # Add text search conditions
            if queries:
                ts_queries = []
                for query in queries:
                    if query.strip():
                        # Convert to PostgreSQL tsquery format
                        ts_query = self._convert_to_tsquery(query)
                        ts_queries.append(ts_query)
                
                if ts_queries:
                    # Combine text search conditions with | (tsquery OR operator)
                    text_search = " | ".join(ts_queries)
                    where_conditions.append(
                        "(to_tsvector('english', p.title || ' ' || COALESCE(p.objective, '') || ' ' || COALESCE(p.topics, '')) @@ to_tsquery('english', %s))"
                    )
                    params.append(text_search)
            
            # Add structured filters
            if filters:
                # Programme filter
                if 'programme' in filters:
                    where_conditions.append("p.\"frameworkProgramme\" = %s")
                    params.append(filters['programme'])
                
                # Date range filter
                if 'date_range' in filters:
                    date_filter = filters['date_range']
                    if 'start' in date_filter:
                        where_conditions.append("p.\"startDate\" >= %s")
                        params.append(date_filter['start'])
                    if 'end' in date_filter:
                        where_conditions.append("p.\"endDate\" <= %s")
                        params.append(date_filter['end'])
                
                # Budget range filter
                if 'budget_range' in filters:
                    budget_filter = filters['budget_range']
                    if 'min' in budget_filter:
                        where_conditions.append("p.\"totalCost\" >= %s")
                        params.append(budget_filter['min'])
                    if 'max' in budget_filter:
                        where_conditions.append("p.\"totalCost\" <= %s")
                        params.append(budget_filter['max'])
                
                # Countries filter (organization country is lowercase in DB)
                if 'countries' in filters:
                    countries = filters['countries']
                    if countries:
                        country_placeholders = ','.join(['%s'] * len(countries))
                        where_conditions.append(f"o.country IN ({country_placeholders})")
                        params.extend(countries)
            
            # Build final query
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Main query with joins to organizations for enrichment
            # NOTE: Tables are in public schema (projects, organizations), NOT cordis_processed
            sql = f"""
                SELECT DISTINCT
                    p.id,
                    p.rcn,
                    p.title,
                    p.acronym,
                    p.objective,
                    p."startDate",
                    p."endDate",
                    p."totalCost",
                    p."ecMaxContribution",
                    p.status,
                    p."frameworkProgramme",
                    p."fundingScheme",
                    p."legalBasis",
                    p.topics,
                    p."grantDoi",
                    -- Organization aggregations
                    COUNT(DISTINCT o."organisationID") as participant_count,
                    COUNT(DISTINCT o.country) as country_count,
                    COUNT(CASE WHEN o."SME" = true THEN 1 END) as sme_count,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.name END) as coordinator_name,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.country END) as coordinator_country,
                    ARRAY_AGG(DISTINCT o.name) FILTER (WHERE o.name IS NOT NULL) as participant_names,
                    ARRAY_AGG(DISTINCT o.country) FILTER (WHERE o.country IS NOT NULL) as participant_countries,
                    ARRAY_AGG(DISTINCT o.city) FILTER (WHERE o.city IS NOT NULL) as participant_cities,
                    SUM(o."ecContribution") as total_ec_contribution,
                    ARRAY_AGG(DISTINCT o."nutsCode") FILTER (WHERE o."nutsCode" IS NOT NULL) as nuts_codes,
                    ARRAY_AGG(DISTINCT o."activityType") FILTER (WHERE o."activityType" IS NOT NULL) as activity_types,
                    -- Relevance scoring (basic for now)
                    0.0 as relevance_score
                FROM projects p
                LEFT JOIN organizations o ON p.id = o."projectID"
                WHERE {where_clause}
                GROUP BY p.id, p.rcn, p.title, p.acronym, p.objective, p."startDate", p."endDate",
                         p."totalCost", p."ecMaxContribution", p.status, p."frameworkProgramme", p."fundingScheme",
                         p."legalBasis", p.topics, p."grantDoi"
                ORDER BY relevance_score DESC, p."startDate" DESC NULLS LAST
                LIMIT %s OFFSET %s
            """
            
            # Add limit and offset to params
            params.extend([limit, offset])
            
            start_time = datetime.now()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Get total count for pagination
            count_sql = f"""
                SELECT COUNT(DISTINCT p.id) as total
                FROM projects p
                LEFT JOIN organizations o ON p.id = o."projectID"
                WHERE {where_clause}
            """
            cursor.execute(count_sql, params[:-2])  # Exclude limit/offset for count
            total_row = cursor.fetchone()
            total_count = total_row['total'] if total_row else 0
            
            cursor.close()
            self.db_pool.putconn(conn)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"🔍 Repository search: {len(rows)} projects in {elapsed:.2f}s (total: {total_count})")
            
            # Convert to DTOs
            projects = []
            for row in rows:
                dto = CordisProjectDTO(
                    id=str(row['id']),
                    rcn=str(row['rcn']),
                    title=row['title'] or 'Unknown Title',
                    acronym=row['acronym'],
                    objective=row['objective'] or 'No description available',
                    start_date=str(row['startDate']),
                    end_date=str(row['endDate']),
                    total_cost=float(row['totalCost'] or 0),
                    ec_max_contribution=float(row['ecMaxContribution'] or 0),
                    status=row['status'] or 'Unknown',
                    framework_programme=row['frameworkProgramme'] or 'Unknown programme framework',
                    funding_scheme=row['fundingScheme'] or 'Unknown funding scheme',
                    legal_basis=row['legalBasis'] or 'N/A',
                    topics=row['topics'] or 'N/A',
                    grant_doi=row['grantDoi'] or 'N/A',
                    participant_count=int(row['participant_count'] or 0),
                    country_count=int(row['country_count'] or 0),
                    sme_count=int(row['sme_count'] or 0),
                    coordinator_name=row['coordinator_name'],
                    coordinator_country=row['coordinator_country'],
                    participant_names=row['participant_names'] or [],
                    participant_countries=row['participant_countries'] or [],
                    participant_cities=row['participant_cities'] or [],
                    total_ec_contribution=float(row['total_ec_contribution'] or 0),
                    nuts_codes=row['nuts_codes'] or [],
                    activity_types=row['activity_types'] or [],
                    relevance_score=float(row['relevance_score'] or 0)
                )
                projects.append(dto)
            
            return projects, total_count
            
        except Exception as e:
            logger.error(f"❌ Repository search failed: {e}")
            return [], 0

    def get_project_by_id(self, project_id: str) -> Optional[CordisProjectDTO]:
        """Get a single project by ID."""
        if not self.db_pool:
            logger.error("❌ Database pool not available")
            return None
        
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute("""
                SELECT
                    p.id, p.rcn, p.title, p.acronym, p.objective,
                    p."startDate", p."endDate", p."totalCost", p."ecMaxContribution",
                    p.status, p."frameworkProgramme", p."fundingScheme", p."legalBasis",
                    p.topics, p."grantDoi",
                    COUNT(DISTINCT o."organisationID") as participant_count,
                    COUNT(DISTINCT o.country) as country_count,
                    COUNT(CASE WHEN o."SME" = true THEN 1 END) as sme_count,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.name END) as coordinator_name,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.country END) as coordinator_country,
                    ARRAY_AGG(DISTINCT o.name) FILTER (WHERE o.name IS NOT NULL) as participant_names,
                    ARRAY_AGG(DISTINCT o.country) FILTER (WHERE o.country IS NOT NULL) as participant_countries,
                    ARRAY_AGG(DISTINCT o.city) FILTER (WHERE o.city IS NOT NULL) as participant_cities,
                    SUM(o."ecContribution") as total_ec_contribution,
                    ARRAY_AGG(DISTINCT o."nutsCode") FILTER (WHERE o."nutsCode" IS NOT NULL) as nuts_codes,
                    ARRAY_AGG(DISTINCT o."activityType") FILTER (WHERE o."activityType" IS NOT NULL) as activity_types
                FROM projects p
                LEFT JOIN organizations o ON p.id = o."projectID"
                WHERE p.id = %s
                GROUP BY p.id, p.rcn, p.title, p.acronym, p.objective, p."startDate", p."endDate",
                         p."totalCost", p."ecMaxContribution", p.status, p."frameworkProgramme", p."fundingScheme",
                         p."legalBasis", p.topics, p."grantDoi"
            """, (project_id,))
            
            row = cursor.fetchone()
            cursor.close()
            self.db_pool.putconn(conn)
            
            if not row:
                return None
            
            return CordisProjectDTO(
                id=str(row['id']),
                rcn=str(row['rcn']),
                title=row['title'] or 'Unknown Title',
                acronym=row['acronym'],
                objective=row['objective'] or 'No description available',
                start_date=str(row['startDate']),
                end_date=str(row['endDate']),
                total_cost=float(row['totalCost'] or 0),
                ec_max_contribution=float(row['ecMaxContribution'] or 0),
                status=row['status'] or 'Unknown',
                framework_programme=row['frameworkProgramme'] or 'Unknown programme framework',
                funding_scheme=row['fundingScheme'] or 'Unknown funding scheme',
                legal_basis=row['legalBasis'] or 'N/A',
                topics=row['topics'] or 'N/A',
                grant_doi=row['grantDoi'] or 'N/A',
                participant_count=int(row['participant_count'] or 0),
                country_count=int(row['country_count'] or 0),
                sme_count=int(row['sme_count'] or 0),
                coordinator_name=row['coordinator_name'],
                coordinator_country=row['coordinator_country'],
                participant_names=row['participant_names'] or [],
                participant_countries=row['participant_countries'] or [],
                participant_cities=row['participant_cities'] or [],
                total_ec_contribution=float(row['total_ec_contribution'] or 0),
                nuts_codes=row['nuts_codes'] or [],
                activity_types=row['activity_types'] or []
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to get project {project_id}: {e}")
            return None

    def get_freshness_cursor(self) -> Optional[datetime]:
        """Get the timestamp of the most recent successful ingestion batch."""
        if not self.db_pool:
            return None
        
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute("""
                SELECT MAX(updated_at) as last_update
                FROM cordis_processed.ingestion_batches
                WHERE status = 'completed'
            """)
            
            row = cursor.fetchone()
            cursor.close()
            self.db_pool.putconn(conn)
            
            return row['last_update'] if row and row['last_update'] else None
            
        except Exception as e:
            logger.error(f"❌ Failed to get freshness cursor: {e}")
            return None

    def get_batch_changes_since(self, since: datetime) -> List[Dict[str, Any]]:
        """Get project changes since a given timestamp for incremental sync."""
        if not self.db_pool:
            return []
        
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute("""
                SELECT batch_id, table_name, operation, record_ids, updated_at
                FROM cordis_processed.change_log
                WHERE updated_at > %s
                ORDER BY updated_at ASC
            """, (since,))
            
            rows = cursor.fetchall()
            cursor.close()
            self.db_pool.putconn(conn)
            
            logger.info(f"📋 Found {len(rows)} batch changes since {since}")
            return rows
            
        except Exception as e:
            logger.error(f"❌ Failed to get batch changes: {e}")
            return []

    def _convert_to_tsquery(self, query: str) -> str:
        """Convert natural language query to PostgreSQL tsquery format."""
        import re

        # Basic cleanup
        query = query.strip().lower()

        # Remove special characters that break tsquery
        query = re.sub(r'[^\w\s]', ' ', query)

        # Get individual terms
        terms = [term.strip() for term in query.split() if term.strip() and len(term) > 2]

        if not terms:
            return ''

        # Use prefix matching with :* and AND logic with &
        # E.g., "quantum computing" -> "quantum:* & computing:*"
        tsquery_terms = [f"{term}:*" for term in terms]
        return ' & '.join(tsquery_terms)

    def get_project_publications(self, project_id: str, limit: int = 5) -> List[Dict]:
        """
        Get publications for a project.

        Args:
            project_id: The CORDIS project ID
            limit: Maximum number of publications to return

        Returns:
            List of publication dictionaries
        """
        if not self.db_pool:
            return []

        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Try enriched publications table first
            cursor.execute("""
                SELECT
                    title,
                    authors,
                    journal_title as journal,
                    publication_date,
                    doi,
                    is_open_access,
                    url
                FROM cordis_processed.publications_enriched
                WHERE project_id = %s
                ORDER BY publication_date DESC NULLS LAST
                LIMIT %s
            """, (project_id, limit))

            results = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            return results

        except Exception as e:
            logger.warning(f"Failed to get publications for project {project_id}: {e}")
            return []
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def get_project_deliverables(self, project_id: str, limit: int = 5) -> List[Dict]:
        """
        Get deliverables for a project.

        Args:
            project_id: The CORDIS project ID
            limit: Maximum number of deliverables to return

        Returns:
            List of deliverable dictionaries
        """
        if not self.db_pool:
            return []

        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Try enriched deliverables table
            cursor.execute("""
                SELECT
                    title,
                    type,
                    description,
                    url
                FROM cordis_processed.deliverables_enriched
                WHERE project_id = %s
                ORDER BY title
                LIMIT %s
            """, (project_id, limit))

            results = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            return results

        except Exception as e:
            logger.warning(f"Failed to get deliverables for project {project_id}: {e}")
            return []
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def get_project_impact_metrics(self, project_id: str) -> Dict[str, Any]:
        """
        Get impact metrics for a project (publication count, patents, datasets).

        Args:
            project_id: The CORDIS project ID

        Returns:
            Dictionary with impact metrics
        """
        if not self.db_pool:
            return {}

        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            metrics = {}

            # Publications count
            try:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM cordis_processed.publications_enriched
                    WHERE project_id = %s
                """, (project_id,))
                row = cursor.fetchone()
                if row:
                    metrics['publications_count'] = row['count']
            except:
                pass

            # Deliverables count
            try:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM cordis_processed.deliverables_enriched
                    WHERE project_id = %s
                """, (project_id,))
                row = cursor.fetchone()
                if row:
                    metrics['deliverables_count'] = row['count']
            except:
                pass

            cursor.close()
            return metrics

        except Exception as e:
            logger.warning(f"Failed to get impact metrics for project {project_id}: {e}")
            return {}
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def close(self):
        """Close database connection pool."""
        if hasattr(self, 'db_pool') and self.db_pool:
            self.db_pool.closeall()
            logger.info("🔒 CordisProjectRepository connections closed")

    def __del__(self):
        """Cleanup on deletion."""
        self.close()