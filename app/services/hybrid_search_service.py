"""
Hybrid Search Service that combines CORDIS API with local database enrichment.
This service searches CORDIS API first, then enriches results with local database data.
"""

import os
import time
import requests
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up structured telemetry logger
logger = logging.getLogger(__name__)

class HybridSearchService:
    """
    Service that performs hybrid search:
    1. Primary search via CORDIS API
    2. Enrichment with local database data
    """
    
    def __init__(self, database_url: Optional[str] = None, ai_provider: str = "gemini"):
        """Initialize the hybrid search service."""
        self.db_url = database_url or os.getenv("DATABASE_URL")
        self.ai_provider = ai_provider
        self.db_pool = None
        
        if self.db_url:
            try:
                import psycopg2.pool
                self.db_pool = psycopg2.pool.SimpleConnectionPool(
                    1, 5,  # min and max connections
                    self.db_url
                )
                logger.info("✅ Hybrid Search: Database connection established for enrichment")
            except Exception as e:
                logger.error(f"⚠️ Hybrid Search: Database connection failed: {e}")
                logger.info("   Will use CORDIS API only without local enrichment")
    
    def search_projects(self, queries: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Perform hybrid search: CORDIS API first, then database enrichment.
        
        Args:
            queries: List of search queries
            max_results: Maximum number of results to return
            
        Returns:
            List of enriched project data
        """
        logger.info(f"🔍 Hybrid Search: Starting with {len(queries)} queries")
        
        # Step 1: Search CORDIS API
        api_projects = self._query_legacy_cordis_api(queries, max_results)
        logger.info(f"📡 CORDIS API returned {len(api_projects)} projects")
        
        if not api_projects:
            logger.warning("⚠️ No projects found via CORDIS API")
            return []
        
        # Step 2: Enrich with local database if available
        if self.db_pool:
            enriched_projects = self._enrich_with_database(api_projects)
            logger.info(f"✨ Enriched {len(enriched_projects)} projects with database data")
            return enriched_projects
        else:
            logger.info("ℹ️ Database not available, returning CORDIS API data only")
            return api_projects
    
    def search_projects_local_first(
        self,
        queries: List[str],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        offset: int = 0,
        repository: Optional["CordisProjectRepository"] = None
    ) -> List[Dict[str, Any]]:
        """
        Local-first hybrid search: repository first, fallback to legacy CORDIS API if needed.
        
        Args:
            queries: List of search queries
            filters: Optional structured filters (programme, date_range, budget_range, countries)
            limit: Maximum number of results to return
            offset: Pagination offset
            repository: Optional CordisProjectRepository instance (injected for testing)
            
        Returns:
            List of enriched project data with data_source flag
        """
        start_time = datetime.now()
        logger.info(f"Starting local-first hybrid search: {len(queries)} queries, limit={limit}")
        logger.info(f"🔍 Local-First Hybrid Search: {len(queries)} queries")
        
        # Use injected repository or create default instance
        if repository is None:
            try:
                from .data.cordis_repository import CordisProjectRepository
                repository = CordisProjectRepository()
            except ImportError as e:
                logger.error(f"Repository not available: {e}, falling back to legacy API")
                logger.warning(f"⚠️ Repository not available: {e}, falling back to legacy API")
                return self._query_legacy_cordis_api(queries, limit)
        
        # Step 1: Search local repository
        try:
            local_projects, total_count = repository.search_projects(
                queries=queries,
                filters=filters,
                limit=limit,
                offset=offset
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Local repository search completed: {len(local_projects)} projects in {elapsed:.2f}s (total: {total_count})")
            logger.info(f"📚 Local repository returned {len(local_projects)} projects (total: {total_count})")
            
            if local_projects:
                # Convert DTOs to dicts for downstream compatibility
                projects = [proj.to_dict() for proj in local_projects]
                
                # Mark as local data source with telemetry
                for project in projects:
                    project['data_source'] = 'local_cordis'
                    project['enrichment_status'] = 'complete'
                    project['search_latency_ms'] = elapsed * 1000
                
                return projects
            else:
                logger.info("No projects found in local repository, falling back to legacy API")
                logger.warning("⚠️ No projects found in local repository")
                return self._query_legacy_cordis_api(queries, limit)
                
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"Local repository search failed after {elapsed:.2f}s: {e}")
            logger.error(f"❌ Local repository search failed: {e}")
            logger.info("🔄 Falling back to legacy CORDIS API")
            return self._query_legacy_cordis_api(queries, limit)
    
    def _query_legacy_cordis_api(self, queries: List[str], max_results: int) -> List[Dict[str, Any]]:
        """
        Search CORDIS API for projects.
        
        Args:
            queries: Search queries
            max_results: Maximum results
            
        Returns:
            List of project data from CORDIS API
        """
        base_api_url = "https://cordis.europa.eu/api/search/results"
        
        # Separate static filters from keyword searches
        static_parts = ["contenttype='project'", "language='en'"]
        keyword_parts = []
        
        for query in queries:
            query_stripped = query.strip()
            if not query_stripped:
                continue
            
            query_lower = query_stripped.lower()
            
            # Date filters go in static parts
            if "startdate" in query_lower or "enddate" in query_lower:
                date_str = query_stripped.replace(" ", "")
                static_parts.append(date_str)
            # Handle budget queries in static parts
            elif "totalcost" in query_lower:
                static_parts.append(query_stripped)
            # Keyword searches go in keyword parts
            else:
                # Handle OR conditions
                or_terms = query_stripped.split(" OR ")
                valid_terms = [term.strip() for term in or_terms if term.strip()]
                if valid_terms:
                    # Don't wrap in extra parentheses - we'll do that when combining
                    for term in valid_terms:
                        keyword_parts.append(f"'{term}'")
        
        # Build final query: static filters AND (keyword1 OR keyword2 OR ...)
        if keyword_parts:
            keyword_query = f"({ ' OR '.join(keyword_parts) })"
            q_value = " AND ".join(static_parts + [keyword_query])
        else:
            q_value = " AND ".join(static_parts)
        
        params = {
            "q": q_value,
            "p": 1,
            "num": max_results,
            "srt": "Relevance:decreasing",
            "archived": "true"
        }
        
        logger.info(f"📡 Calling CORDIS API with query: {q_value[:100]}...")
        
        try:
            response = requests.get(base_api_url, params=params, timeout=30)
            response.raise_for_status()
            
            json_data = response.json()
            if json_data.get("payload") and "results" in json_data["payload"]:
                results = json_data["payload"]["results"]
                
                # Extract and format project data
                projects = []
                for item in results:
                    project = self._extract_cordis_project_data(item)
                    projects.append(project)
                
                return projects
            
            return []
            
        except Exception as e:
            logger.error(f"❌ CORDIS API error: {e}")
            return []
    
    def _extract_cordis_project_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract project data from CORDIS API response item."""
        project = {}
        
        # Basic information
        project['id'] = item.get('id', item.get('reference', 'N/A'))
        project['rcn'] = item.get('rcn', 'N/A')
        project['title'] = item.get('title', 'Unknown Title')
        project['acronym'] = item.get('acronym', 'N/A')
        project['objective'] = item.get('description', item.get('teaser', 'No description available'))
        
        # Dates
        project['startDate'] = item.get('startDate', 'Unknown')
        project['endDate'] = item.get('endDate', 'Unknown')
        
        # Financial information
        raw_budget = item.get('totalCost', item.get('projectTotalCost'))
        if isinstance(raw_budget, dict) and 'value' in raw_budget:
            project['totalCost'] = raw_budget.get('value', 0)
            project['budget'] = f"€{raw_budget.get('value', 0):,.0f}"
        elif raw_budget:
            project['totalCost'] = raw_budget
            project['budget'] = f"€{raw_budget:,.0f}"
        else:
            project['totalCost'] = 0
            project['budget'] = 'N/A'
        
        # Programme information (often missing in CORDIS API)
        project['frameworkProgramme'] = item.get('frameworkProgramme', 'To be enriched from database')
        project['fundingScheme'] = item.get('fundingScheme', 'To be enriched from database')
        
        # Keywords
        keywords_data = item.get('keywords', item.get('subjects'))
        if isinstance(keywords_data, list):
            project['keywords'] = ', '.join(str(k.get('label', k) if isinstance(k, dict) else k) for k in keywords_data if k)
        else:
            project['keywords'] = 'N/A'
        
        # Participants (basic from API)
        participants = item.get('participants', [])
        project['participant_count'] = len(participants)
        project['participant_names'] = []
        project['participant_countries'] = []
        
        for p in participants:
            if isinstance(p, dict):
                name = p.get('name', p.get('legalName'))
                if name:
                    project['participant_names'].append(name)
                
                country = p.get('country')
                if isinstance(country, dict):
                    country = country.get('isoCode', country.get('label'))
                if country:
                    project['participant_countries'].append(country)
        
        # Mark as needing enrichment
        project['needs_enrichment'] = True
        project['data_source'] = 'CORDIS API'
        
        return project
    
    def _enrich_with_database(self, api_projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich CORDIS API projects with local database data.
        
        Args:
            api_projects: Projects from CORDIS API
            
        Returns:
            Enriched project data
        """
        if not self.db_pool:
            return api_projects
        
        enriched_projects = []
        
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            for api_project in api_projects:
                # Try to find project in database by ID or RCN
                project_id = api_project.get('id', 'N/A')
                project_rcn = api_project.get('rcn', 'N/A')
                
                # Query database for enrichment data
                cursor.execute("""
                    SELECT 
                        p.id,
                        p.rcn,
                        p."frameworkProgramme",
                        p."fundingScheme",
                        p.status,
                        p."legalBasis",
                        p.topics,
                        p."grantDoi",
                        p."ecMaxContribution",
                        -- Organization aggregations
                        COUNT(DISTINCT o."organisationID") as participant_count,
                        COUNT(DISTINCT o.country) as country_count,
                        COUNT(CASE WHEN o."SME" = true THEN 1 END) as sme_count,
                        ARRAY_AGG(DISTINCT o.name) FILTER (WHERE o.name IS NOT NULL) as org_names,
                        ARRAY_AGG(DISTINCT o.country) FILTER (WHERE o.country IS NOT NULL) as org_countries,
                        ARRAY_AGG(DISTINCT o.city) FILTER (WHERE o.city IS NOT NULL) as org_cities,
                        MAX(CASE WHEN o.role = 'coordinator' THEN o.name END) as coordinator_name,
                        MAX(CASE WHEN o.role = 'coordinator' THEN o.country END) as coordinator_country,
                        SUM(o."ecContribution") as total_ec_contribution
                    FROM projects p
                    LEFT JOIN organizations o ON p.id = o."projectID"
                    WHERE p.id = %s OR p.rcn = %s
                    GROUP BY p.id, p.rcn, p."frameworkProgramme", p."fundingScheme", 
                             p.status, p."legalBasis", p.topics, p."grantDoi", p."ecMaxContribution"
                """, (project_id, project_rcn))
                
                db_data = cursor.fetchone()
                
                if db_data:
                    # Enrich API project with database data
                    enriched_project = api_project.copy()
                    
                    # Override/enrich programme information
                    if db_data['frameworkProgramme']:
                        enriched_project['frameworkProgramme'] = db_data['frameworkProgramme']
                    if db_data['fundingScheme']:
                        enriched_project['fundingScheme'] = db_data['fundingScheme']
                    
                    # Add additional fields from database
                    enriched_project['status'] = db_data.get('status', 'N/A')
                    enriched_project['legalBasis'] = db_data.get('legalBasis', 'N/A')
                    enriched_project['topics'] = db_data.get('topics', 'N/A')
                    enriched_project['grantDoi'] = db_data.get('grantDoi', 'N/A')
                    
                    # Enhanced participant information
                    if db_data['participant_count'] > 0:
                        enriched_project['participant_count'] = db_data['participant_count']
                        enriched_project['country_count'] = db_data['country_count']
                        enriched_project['sme_count'] = db_data['sme_count']
                        enriched_project['coordinator_name'] = db_data.get('coordinator_name', 'N/A')
                        enriched_project['coordinator_country'] = db_data.get('coordinator_country', 'N/A')
                        
                        # Update participant lists with database data
                        if db_data['org_names']:
                            enriched_project['participant_names'] = list(db_data['org_names'])
                        if db_data['org_countries']:
                            enriched_project['participant_countries'] = list(db_data['org_countries'])
                        if db_data['org_cities']:
                            enriched_project['participant_cities'] = list(db_data['org_cities'])
                    
                    # Financial enrichment
                    if db_data['ecMaxContribution']:
                        enriched_project['ecMaxContribution'] = float(str(db_data['ecMaxContribution']))
                        enriched_project['ecContribution'] = f"€{float(str(db_data['ecMaxContribution'])):,.0f}"
                    
                    if db_data['total_ec_contribution']:
                        enriched_project['total_ec_contribution'] = float(str(db_data['total_ec_contribution']))
                    
                    # Update enrichment status
                    enriched_project['needs_enrichment'] = False
                    enriched_project['data_source'] = 'CORDIS API + Local Database'
                    enriched_project['enrichment_status'] = 'complete'
                    
                    logger.info(f"✅ Enriched project: {enriched_project.get('acronym', 'N/A')} - {enriched_project['frameworkProgramme']}")
                    enriched_projects.append(enriched_project)
                else:
                    # Project not found in database, use API data as-is
                    api_project['enrichment_status'] = 'not_in_database'
                    logger.info(f"ℹ️ Project not in database: {api_project.get('acronym', 'N/A')}")
                    enriched_projects.append(api_project)
            
            cursor.close()
            self.db_pool.putconn(conn)
            
        except Exception as e:
            logger.error(f"❌ Database enrichment error: {e}")
            # Return original API data if enrichment fails
            return api_projects
        
        return enriched_projects
    
    def format_enriched_results(self, projects: List[Dict[str, Any]]) -> str:
        """
        Format enriched project results for display.
        
        Args:
            projects: List of enriched projects
            
        Returns:
            Formatted string for display
        """
        if not projects:
            return "No projects found."
        
        output = []
        output.append(f"Found {len(projects)} projects (CORDIS API + Database Enrichment):\n")
        
        for i, project in enumerate(projects, 1):
            output.append(f"\n{i}. {project.get('title', 'Unknown Title')}")
            
            if project.get('acronym') and project['acronym'] != 'N/A':
                output.append(f"   Acronym: {project['acronym']}")
            
            # Show framework programme with enrichment indicator
            framework = project.get('frameworkProgramme', 'Unknown')
            if framework == 'To be enriched from database':
                output.append(f"   Framework: Not available (not in local database)")
            else:
                enrichment_marker = " ✨" if project.get('enrichment_status') == 'complete' else ""
                output.append(f"   Framework: {framework}{enrichment_marker}")
            
            if project.get('fundingScheme') and project['fundingScheme'] not in ['N/A', 'To be enriched from database']:
                output.append(f"   Funding: {project['fundingScheme']}")
            
            if project.get('coordinator_name') and project['coordinator_name'] != 'N/A':
                output.append(f"   Coordinator: {project['coordinator_name']} ({project.get('coordinator_country', 'N/A')})")
            
            if project.get('participant_count', 0) > 0:
                output.append(f"   Participants: {project['participant_count']} from {project.get('country_count', 0)} countries")
                if project.get('sme_count', 0) > 0:
                    output.append(f"   SMEs: {project['sme_count']}")
            
            if project.get('budget') and project['budget'] != 'N/A':
                output.append(f"   Budget: {project['budget']}")
            
            output.append(f"   Data Source: {project.get('data_source', 'CORDIS API')}")
        
        output.append("\n✨ = Enriched with local database data")
        
        return "\n".join(output)


def test_hybrid_search():
    """Test the hybrid search functionality."""
    logger.info("="*80)
    logger.info("TESTING HYBRID SEARCH SERVICE")
    logger.info("="*80)
    
    # Initialize hybrid search
    hybrid = HybridSearchService()
    
    # Test search
    queries = ["nuclear energy", "startDate>2020-01-01"]
    logger.info(f"\nSearching for: {queries}")
    logger.info("-"*60)
    
    # Perform hybrid search
    results = hybrid.search_projects(queries, max_results=5)
    
    # Display results
    formatted = hybrid.format_enriched_results(results)
    logger.info(formatted)
    
    logger.info("\n" + "="*80)
    logger.info("HYBRID SEARCH TEST COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    test_hybrid_search()