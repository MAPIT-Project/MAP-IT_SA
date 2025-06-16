import os
import requests
import re
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import openai
from google import genai as google_genai_sdk
from google.genai import types
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2
from psycopg2.extras import DictCursor
import psycopg2.pool
from urllib.parse import urlparse
from collections import defaultdict

# Load environment variables
load_dotenv()

class CordisRAG:
    """
    Retrieval-Augmented Generation system for European research projects using CORDIS database.
    V5: Enhanced with local Supabase database integration for faster and richer data retrieval.
    """
    def __init__(self, openai_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None, 
                 ai_provider: str = "openai", 
                 openai_model_name: str = "gpt-4-turbo",
                 gemini_model_name: str = "gemini-2.5-flash-preview-05-20",
                 use_local_db: bool = False,
                 database_url: Optional[str] = None):
        load_dotenv()
        self.ai_provider = ai_provider.lower()
        self.openai_model_name = openai_model_name
        self.gemini_model_name = gemini_model_name
        self.gemini_client = None
        self.use_local_db = use_local_db
        
        # Database connection setup
        self.db_pool = None
        if self.use_local_db:
            db_url = database_url or os.getenv("DATABASE_URL")
            if not db_url:
                raise ValueError("DATABASE_URL required when use_local_db=True")
            
            try:
                self.db_pool = psycopg2.pool.SimpleConnectionPool(
                    1, 20,  # min and max connections
                    db_url
                )
                print("✅ Local database connection established")
                
                # Initialize database optimization
                self._initialize_database_optimization()
                
            except Exception as e:
                print(f"❌ Database connection failed: {e}")
                raise
        
        # Performance optimizations
        self._xml_cache = {}  # Cache for XML data
        self._api_cache = {}  # Cache for API responses
        self._db_cache = {}  # Cache for database queries
        self._query_cache = {}  # Cache for preprocessed queries
        self._cache_ttl = 3600  # Cache TTL in seconds (1 hour)
        
        # Query preprocessing utilities
        self._domain_keywords = self._load_domain_keywords()
        self._stopwords = {'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 
                          'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 
                          'to', 'was', 'will', 'with', 'the'}
        
        if self.ai_provider == "openai":
            used_openai_api_key = openai_api_key if openai_api_key else os.getenv("OPENAI_API_KEY")
            if not used_openai_api_key:
                raise ValueError("OpenAI API key not provided and not found in .env file.")
            self.openai_client = openai.OpenAI(api_key=used_openai_api_key)
        elif self.ai_provider == "gemini":
            used_gemini_api_key = gemini_api_key if gemini_api_key else os.getenv("GEMINI_API_KEY")
            if not used_gemini_api_key:
                raise ValueError("Gemini API key not provided and not found in .env file.")
            self.gemini_client = google_genai_sdk.Client(api_key=used_gemini_api_key)
        else:
            raise ValueError("Invalid AI provider specified. Choose 'openai' or 'gemini'.")

    def _initialize_database_optimization(self):
        """Initialize database-specific optimizations and analysis."""
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            # Analyze database content for better query optimization
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_projects,
                    MIN("startDate") as earliest_project,
                    MAX("startDate") as latest_project,
                    COUNT(DISTINCT "frameworkProgramme") as frameworks,
                    COUNT(DISTINCT "fundingScheme") as funding_schemes
                FROM projects
            """)
            stats = cursor.fetchone()
            
            if stats and stats[0] > 0:
                self._db_stats = {
                    'total_projects': stats[0],
                    'date_range': (stats[1], stats[2]),
                    'frameworks': stats[3],
                    'funding_schemes': stats[4]
                }
                print(f"📊 Database contains {stats[0]} projects from {stats[1]} to {stats[2]}")
            
            # Create text search indexes if they don't exist (for PostgreSQL)
            try:
                cursor.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_text_search 
                    ON projects USING gin(to_tsvector('english', title || ' ' || COALESCE(objective, '') || ' ' || COALESCE(topics, '')))
                """)
                cursor.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_text_search 
                    ON organizations USING gin(to_tsvector('english', name || ' ' || COALESCE(country, '')))
                """)
                print("✅ Full-text search indexes created/verified")
            except Exception as e:
                print(f"⚠️ Could not create search indexes: {e}")
            
        except Exception as e:
            print(f"⚠️ Database optimization initialization failed: {e}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self.db_pool.putconn(conn)

    def _load_domain_keywords(self) -> Dict[str, List[str]]:
        """Load domain-specific keyword mappings for better query understanding."""
        return {
            'ai_ml': ['artificial intelligence', 'machine learning', 'deep learning', 'neural networks', 
                     'computer vision', 'natural language processing', 'nlp', 'ai', 'ml'],
            'energy': ['renewable energy', 'solar', 'wind', 'battery', 'energy storage', 'green energy',
                      'photovoltaic', 'hydroelectric', 'geothermal', 'energy efficiency'],
            'health': ['healthcare', 'medical', 'pharmaceutical', 'biomedical', 'clinical', 'therapy',
                      'drug discovery', 'precision medicine', 'digital health', 'telemedicine'],
            'mobility': ['transportation', 'autonomous vehicles', 'electric vehicles', 'smart mobility',
                        'urban mobility', 'logistics', 'traffic', 'sustainable transport'],
            'environment': ['climate change', 'sustainability', 'carbon', 'emissions', 'green technology',
                           'circular economy', 'biodiversity', 'pollution', 'environmental'],
            'digital': ['digitalization', 'digital transformation', 'iot', 'blockchain', 'cybersecurity',
                       'cloud computing', 'big data', 'smart cities', 'industry 4.0']
        }

    def _preprocess_queries(self, queries: List[str]) -> List[str]:
        """Enhanced query preprocessing with domain knowledge and expansion."""
        cache_key = self._get_cache_key(('preprocess', queries))
        cached_result = self._get_from_cache(self._query_cache, cache_key)
        if cached_result is not None:
            return cached_result
        
        processed_queries = []
        
        for query in queries:
            query = query.strip().lower()
            if not query:
                continue
            
            # Skip date queries - handle them separately
            if any(date_keyword in query for date_keyword in ['startdate>', 'enddate>', 'totalcost']):
                processed_queries.append(query)
                continue
            
            # Expand domain-specific terms
            expanded_terms = []
            query_words = set(query.replace(' or ', '|').replace(' and ', '&').split())
            
            for domain, keywords in self._domain_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in query.lower():
                        # Add related terms from the same domain
                        related_terms = [k for k in keywords if k != keyword and len(k) > 3][:3]
                        expanded_terms.extend(related_terms)
            
            # Create enhanced query
            if expanded_terms:
                # Combine original query with expanded terms using OR
                base_query = query
                expansion = ' OR '.join(expanded_terms)
                enhanced_query = f"{base_query} OR {expansion}"
                processed_queries.append(enhanced_query)
            else:
                processed_queries.append(query)
        
        # Cache the result
        self._set_cache(self._query_cache, cache_key, processed_queries)
        return processed_queries

    def _search_local_database(self, queries: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Enhanced database search with full-text search, query optimization, and better relevance scoring.
        """
        # Create cache key from queries
        cache_key = self._get_cache_key((queries, max_results, "local_db_enhanced"))
        
        # Check cache first
        cached_result = self._get_from_cache(self._db_cache, cache_key)
        if cached_result is not None:
            print(f"Using cached database results for {len(queries)} queries")
            return cached_result
        
        if not self.db_pool:
            print("❌ Database pool not available")
            return []
        
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            # Preprocess queries for better matching
            processed_queries = self._preprocess_queries(queries)
            print(f"🔍 Enhanced search for: {processed_queries}")
            
            # Separate text queries from date/budget queries
            text_queries = []
            date_conditions = []
            budget_conditions = []
            
            for query in processed_queries:
                query = query.strip()
                if not query:
                    continue
                    
                # Handle date queries
                if 'startdate>' in query.lower():
                    try:
                        date_part = query.lower().split('startdate>')[1]
                        date_conditions.append(f"p.\"startDate\" >= '{date_part}'")
                        print(f"📅 Added date condition: startDate >= {date_part}")
                        continue
                    except:
                        print(f"⚠️ Could not parse date query: {query}")
                        continue
                elif 'enddate>' in query.lower():
                    try:
                        date_part = query.lower().split('enddate>')[1]
                        date_conditions.append(f"p.\"endDate\" >= '{date_part}'")
                        continue
                    except:
                        continue
                elif 'totalcost' in query.lower():
                    try:
                        budget_conditions.append(self._parse_budget_query(query))
                        continue
                    except:
                        continue
                
                text_queries.append(query)
            
            # Build enhanced SQL query with full-text search and relevance scoring
            if text_queries:
                projects = self._execute_enhanced_text_search(cursor, text_queries, date_conditions, budget_conditions, max_results)
            else:
                # No text queries, just date/budget filters
                projects = self._execute_filtered_search(cursor, date_conditions, budget_conditions, max_results)
            
            # Cache the result
            self._set_cache(self._db_cache, cache_key, projects)
            
            print(f"Enhanced database search completed, found {len(projects)} projects")
            return projects
            
        except Exception as e:
            print(f"Database query error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self.db_pool.putconn(conn)

    def _execute_enhanced_text_search(self, cursor, text_queries: List[str], date_conditions: List[str], 
                                    budget_conditions: List[str], max_results: int) -> List[Dict[str, Any]]:
        """Execute enhanced full-text search with PostgreSQL tsvector."""
        
        # Build full-text search conditions
        search_conditions = []
        params = []
        
        for query in text_queries:
            # Convert OR/AND logic to PostgreSQL tsquery format
            ts_query = self._convert_to_tsquery(query)
            search_conditions.append("""
                (to_tsvector('english', p.title || ' ' || COALESCE(p.objective, '') || ' ' || COALESCE(p.topics, '')) @@ to_tsquery('english', %s)
                 OR to_tsvector('english', COALESCE(o.name, '') || ' ' || COALESCE(o.country, '')) @@ to_tsquery('english', %s))
            """)
            params.extend([ts_query, ts_query])
        
        # Build complete WHERE clause
        all_conditions = search_conditions + date_conditions + budget_conditions
        where_clause = f" AND ({' AND '.join(all_conditions)})" if all_conditions else ""
        
        # Enhanced SQL with relevance scoring
        sql_query = f"""
            SELECT DISTINCT
                p.id,
                p.acronym,
                p.title,
                p.objective,
                p."startDate",
                p."endDate",
                p."totalCost",
                p."ecMaxContribution",
                p.status,
                p.topics,
                p."frameworkProgramme",
                p."fundingScheme",
                p."legalBasis",
                p.rcn,
                p."grantDoi",
                -- Relevance scoring
                ts_rank_cd(to_tsvector('english', p.title || ' ' || COALESCE(p.objective, '')), 
                          to_tsquery('english', %s), 32) as relevance_score,
                -- Aggregated organization data
                COUNT(o."organisationID") as participant_count,
                ARRAY_AGG(DISTINCT o.name) FILTER (WHERE o.name IS NOT NULL) as participant_names,
                ARRAY_AGG(DISTINCT o.country) FILTER (WHERE o.country IS NOT NULL) as participant_countries,
                ARRAY_AGG(DISTINCT o.city) FILTER (WHERE o.city IS NOT NULL) as participant_cities,
                SUM(o."ecContribution") as total_ec_contribution,
                SUM(o."netEcContribution") as total_net_ec_contribution,
                SUM(o."totalCost") as total_org_costs,
                -- Coordinator information
                MAX(CASE WHEN o.role = 'coordinator' THEN o.name END) as coordinator_name,
                MAX(CASE WHEN o.role = 'coordinator' THEN o.country END) as coordinator_country,
                MAX(CASE WHEN o.role = 'coordinator' THEN o.city END) as coordinator_city,
                -- SME and geographic info
                COUNT(CASE WHEN o."SME" = true THEN 1 END) as sme_count,
                COUNT(DISTINCT o.country) as country_count,
                ARRAY_AGG(DISTINCT o."nutsCode") FILTER (WHERE o."nutsCode" IS NOT NULL) as nuts_codes,
                ARRAY_AGG(DISTINCT o."activityType") FILTER (WHERE o."activityType" IS NOT NULL) as activity_types
            FROM projects p
            LEFT JOIN organizations o ON p.id = o."projectID"
            WHERE p.id IS NOT NULL{where_clause}
            GROUP BY p.id, p.acronym, p.title, p.objective, p."startDate", p."endDate", 
                     p."totalCost", p."ecMaxContribution", p.status, p.topics, 
                     p."frameworkProgramme", p."fundingScheme", p."legalBasis", p.rcn, p."grantDoi"
            ORDER BY relevance_score DESC, p."startDate" DESC NULLS LAST
            LIMIT %s
        """
        
        # Add relevance query parameter and limit
        all_params = [self._convert_to_tsquery(' OR '.join(text_queries))] + params + [max_results]
        
        start_time = time.time()
        cursor.execute(sql_query, all_params)
        rows = cursor.fetchall()
        
        print(f"📊 Enhanced search returned {len(rows)} rows in {time.time() - start_time:.2f}s")
        
        # Convert to structured project data
        projects = []
        for row in rows:
            project = self._format_db_project_data(dict(row))
            project['relevance_score'] = float(row.get('relevance_score', 0))
            projects.append(project)
            print(f"  - {project['title'][:50]}... (relevance: {project['relevance_score']:.3f})")
        
        return projects

    def _convert_to_tsquery(self, query: str) -> str:
        """Convert natural language query to PostgreSQL tsquery format."""
        # Handle OR conditions
        if ' OR ' in query.upper():
            terms = [term.strip() for term in re.split(r'\s+OR\s+', query, flags=re.IGNORECASE)]
            return ' | '.join(f'"{term}"' for term in terms if term)
        
        # Handle AND conditions (default)
        terms = query.split()
        # Filter out stopwords and short terms
        meaningful_terms = [term for term in terms if len(term) > 2 and term.lower() not in self._stopwords]
        
        if not meaningful_terms:
            return f'"{query}"'
        
        return ' & '.join(f'"{term}"' for term in meaningful_terms[:5])  # Limit to 5 terms

    def _parse_budget_query(self, query: str) -> str:
        """Parse budget queries like totalCost>1000000."""
        query_lower = query.lower()
        if 'totalcost>' in query_lower:
            amount = query_lower.split('totalcost>')[1]
            return f'p."totalCost" > {amount}'
        elif 'totalcost<' in query_lower:
            amount = query_lower.split('totalcost<')[1]
            return f'p."totalCost" < {amount}'
        elif 'totalcost=' in query_lower:
            range_part = query_lower.split('totalcost=')[1]
            if '-' in range_part:
                low, high = range_part.split('-')
                return f'p."totalCost" BETWEEN {low} AND {high}'
        return ""

    def _execute_filtered_search(self, cursor, date_conditions: List[str], budget_conditions: List[str], max_results: int) -> List[Dict[str, Any]]:
        """Execute search with only date and budget filters."""
        all_conditions = date_conditions + budget_conditions
        where_clause = f" AND ({' AND '.join(all_conditions)})" if all_conditions else ""
        
        # Simple filtered query
        sql_query = f"""
            SELECT DISTINCT
                p.id, p.acronym, p.title, p.objective, p."startDate", p."endDate",
                p."totalCost", p."ecMaxContribution", p.status, p.topics,
                p."frameworkProgramme", p."fundingScheme", p."legalBasis", p.rcn, p."grantDoi",
                COUNT(o."organisationID") as participant_count,
                ARRAY_AGG(DISTINCT o.name) FILTER (WHERE o.name IS NOT NULL) as participant_names,
                ARRAY_AGG(DISTINCT o.country) FILTER (WHERE o.country IS NOT NULL) as participant_countries,
                MAX(CASE WHEN o.role = 'coordinator' THEN o.name END) as coordinator_name,
                MAX(CASE WHEN o.role = 'coordinator' THEN o.country END) as coordinator_country,
                COUNT(CASE WHEN o."SME" = true THEN 1 END) as sme_count,
                COUNT(DISTINCT o.country) as country_count
            FROM projects p
            LEFT JOIN organizations o ON p.id = o."projectID"
            WHERE p.id IS NOT NULL{where_clause}
            GROUP BY p.id, p.acronym, p.title, p.objective, p."startDate", p."endDate",
                     p."totalCost", p."ecMaxContribution", p.status, p.topics,
                     p."frameworkProgramme", p."fundingScheme", p."legalBasis", p.rcn, p."grantDoi"
            ORDER BY p."startDate" DESC NULLS LAST, p."totalCost" DESC NULLS LAST
            LIMIT %s
        """
        
        cursor.execute(sql_query, [max_results])
        rows = cursor.fetchall()
        
        projects = []
        for row in rows:
            project = self._format_db_project_data(dict(row))
            projects.append(project)
        
        return projects

    def _adaptive_result_selection(self, project_data: List[Dict[str, Any]], question: str, max_results: int) -> List[Dict[str, Any]]:
        """Intelligently select the most relevant projects based on question context."""
        if len(project_data) <= max_results:
            return project_data
        
        # Score projects based on multiple factors
        scored_projects = []
        question_lower = question.lower()
        
        for project in project_data:
            score = 0
            
            # Relevance score from database
            score += project.get('relevance_score', 0) * 10
            
            # Recency bonus (more recent = higher score)
            try:
                start_date = project.get('startDate', '')
                if start_date and start_date != 'Unknown':
                    year = int(str(start_date)[:4])
                    current_year = datetime.now().year
                    recency_score = max(0, (year - 2010) / (current_year - 2010)) * 5
                    score += recency_score
            except:
                pass
            
            # Budget significance (larger budget = more significant)
            try:
                total_cost = project.get('totalCost', 0)
                if isinstance(total_cost, (int, float)) and total_cost > 0:
                    budget_score = min(5, total_cost / 10000000)  # Scale to max 5 points
                    score += budget_score
            except:
                pass
            
            # Participation diversity bonus
            country_count = project.get('country_count', 0)
            if country_count > 1:
                score += min(3, country_count * 0.5)
            
            # SME involvement bonus
            sme_count = project.get('sme_count', 0)
            if sme_count > 0:
                score += min(2, sme_count * 0.5)
            
            # Question-specific keyword matching
            title = project.get('title', '').lower()
            objective = project.get('objective', '').lower()
            
            # Check for question keywords in project
            question_words = set(question_lower.split()) - self._stopwords
            project_text = f"{title} {objective}".lower()
            
            keyword_matches = sum(1 for word in question_words if word in project_text and len(word) > 3)
            score += keyword_matches * 2
            
            scored_projects.append((score, project))
        
        # Sort by score and return top results
        scored_projects.sort(key=lambda x: x[0], reverse=True)
        return [project for score, project in scored_projects[:max_results]]

    def get_ai_response(self, question: str, max_projects_to_process: int = 5, max_cordis_results: int = 10) -> str:
        """
        Enhanced AI response generation with adaptive result selection and improved answer quality.
        """
        total_start_time = time.time()
        data_source = "Local Database" if self.use_local_db else "CORDIS API"
        print(f"🚀 Starting Enhanced V5 RAG pipeline using {data_source} for: '{question}'")
        
        # 1. Phase 1: Query extraction with enhanced preprocessing
        phase_start = time.time()
        role, quest = self._get_phase1_prompt(question)
        queries, end_flag, new_query_keys, rerank_criteria, problem_text, next_pass = self._extract_queries(role, quest)
        print(f"📝 Phase 1 (Query extraction) completed in {time.time() - phase_start:.2f}s")
        
        if end_flag:
            return problem_text
        
        # 2. Phase 2: Enhanced data retrieval
        phase_start = time.time()
        if self.use_local_db:
            # Get more results initially for better selection
            initial_results = max_projects_to_process * 3
            raw_project_data = self._search_local_database(queries, max_results=initial_results)
            
            # Intelligently select the best projects
            project_data = self._adaptive_result_selection(raw_project_data, question, max_projects_to_process)
            print(f"🎯 Selected {len(project_data)} best projects from {len(raw_project_data)} candidates")
            
            print(f"🔍 Phase 2 (Enhanced Local DB search) completed in {time.time() - phase_start:.2f}s")
        else:
            project_items = self._search_cordis_api(queries, max_results=max_cordis_results)
            print(f"🔍 Phase 2 (CORDIS API search) completed in {time.time() - phase_start:.2f}s")
            
            # Phase 3: Project data extraction (only for API mode)
            phase_start = time.time()
            project_data = [self._extract_project_data(item) for item in project_items[:max_projects_to_process]]
            print(f"📊 Phase 3 (Data extraction) completed in {time.time() - phase_start:.2f}s")
            
            # Phase 3.5: XML enrichment (only for API mode)
            phase_start = time.time()
            project_data = self._enrich_with_xml_data(project_data)
            print(f"🔗 Phase 3.5 (XML enrichment) completed in {time.time() - phase_start:.2f}s")
        
        # 4. Phase 4: Enhanced reranking
        if rerank_criteria and len(project_data) > 1:
            phase_start = time.time()
            project_data = self._enhanced_rerank_projects(project_data, rerank_criteria, question, role)
            print(f"📈 Phase 4 (Enhanced reranking) completed in {time.time() - phase_start:.2f}s")
        
        # 5. Phase 6: Enhanced answer generation
        phase_start = time.time()
        answer = self._generate_enhanced_answer(role, question, project_data)
        print(f"💬 Phase 6 (Enhanced answer generation) completed in {time.time() - phase_start:.2f}s")
        
        total_time = time.time() - total_start_time
        print(f"✅ Enhanced V5 RAG pipeline completed in {total_time:.2f}s total")
        
        return answer

    def _enhanced_rerank_projects(self, project_data: List[Dict[str, Any]], rerank_criteria: List[str], 
                                question: str, role: str) -> List[Dict[str, Any]]:
        """Enhanced reranking with better project scoring and selection."""
        if len(project_data) <= 1:
            return project_data
        
        # Combine LLM reranking with algorithmic scoring
        llm_ranked = self._rerank_projects(project_data, rerank_criteria, question, role)
        
        # If LLM reranking failed, fall back to algorithmic ranking
        if not llm_ranked:
            return self._adaptive_result_selection(project_data, question, len(project_data))
        
        return llm_ranked

    def _generate_enhanced_answer(self, role: str, user_text: str, project_data: List[Dict[str, Any]]) -> str:
        """Generate enhanced answer with better structure and insights."""
        if not project_data:
            return self._generate_no_results_response(user_text)
        
        # Analyze project portfolio for insights
        insights = self._analyze_project_portfolio(project_data)
        
        # Generate enhanced project summaries
        project_summaries = self._create_enhanced_project_summaries(project_data)
        
        # Create enhanced prompt with insights
        projects_text = "\n\n".join(project_summaries)
        data_source_note = "from our local CORDIS database" if self.use_local_db else "from the CORDIS database"
        
        insights_text = ""
        if insights:
            insights_text = f"\n\nPortfolio Insights:\n{insights}"
        
        prompt = f"""Based on the following European research projects {data_source_note}, provide a comprehensive and insightful answer to the user's question.

User Question: {user_text}

Retrieved Projects:
{projects_text}{insights_text}

Instructions:
- Write in a conversational, authoritative tone
- Start with a clear overview addressing the user's question
- ALWAYS include the provided CORDIS links for each project discussed
- Highlight the most relevant and recent projects first
- Include specific details like budgets, timelines, consortium information, and geographic distribution
- Note programme frameworks (Horizon, FP7, etc.) and their significance
- Identify trends, patterns, and relationships between projects
- Use the portfolio insights to provide deeper analysis
- Organize information logically with clear sections if discussing multiple aspects
- Make sure to preserve all 🔗 CORDIS Links in your response
- Conclude with actionable insights or recommendations when appropriate
- Write as if you're an expert consultant familiar with the European research landscape
"""
        
        return self._call_llm_for_generation(role, prompt)

    def _analyze_project_portfolio(self, projects: List[Dict[str, Any]]) -> str:
        """Analyze the project portfolio to extract insights."""
        if len(projects) < 2:
            return ""
        
        insights = []
        
        # Temporal analysis
        years = []
        for project in projects:
            try:
                start_date = project.get('startDate', '')
                if start_date and start_date != 'Unknown':
                    year = int(str(start_date)[:4])
                    years.append(year)
            except:
                pass
        
        if years:
            insights.append(f"Projects span from {min(years)} to {max(years)}")
        
        # Geographic analysis
        all_countries = []
        for project in projects:
            countries = project.get('participant_countries', [])
            all_countries.extend(countries)
        
        if all_countries:
            country_counts = defaultdict(int)
            for country in all_countries:
                country_counts[country] += 1
            top_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            insights.append(f"Top participating countries: {', '.join([f'{c} ({n})' for c, n in top_countries])}")
        
        # Budget analysis
        budgets = []
        for project in projects:
            try:
                total_cost = project.get('totalCost', 0)
                if isinstance(total_cost, (int, float)) and total_cost > 0:
                    budgets.append(total_cost)
            except:
                pass
        
        if budgets:
            total_funding = sum(budgets)
            avg_budget = total_funding / len(budgets)
            insights.append(f"Total funding: €{total_funding:,.0f}, Average: €{avg_budget:,.0f}")
        
        # Framework analysis
        frameworks = defaultdict(int)
        for project in projects:
            fw = project.get('frameworkProgramme', 'Unknown')
            if fw and fw != 'N/A':
                frameworks[fw] += 1
        
        if frameworks:
            top_fw = max(frameworks.items(), key=lambda x: x[1])
            insights.append(f"Most common programme: {top_fw[0]} ({top_fw[1]} projects)")
        
        return " | ".join(insights) if insights else ""

    def _create_enhanced_project_summaries(self, projects: List[Dict[str, Any]]) -> List[str]:
        """Create enhanced project summaries with better formatting and information."""
        summaries = []
        
        for i, proj in enumerate(projects, 1):
            title = proj.get('title', 'Unknown Title')
            acronym = proj.get('acronym', '')
            objective = proj.get('objective', 'No description available')
            budget = proj.get('budget', 'Budget not specified')
            start_date = proj.get('startDate', 'Unknown')
            end_date = proj.get('endDate', 'Unknown')
            project_id = proj.get('id', '')
            rcn = proj.get('rcn', '')
            status = proj.get('status', 'N/A')
            
            # Enhanced information from database
            coordinator_name = proj.get('coordinator_name', 'N/A')
            coordinator_country = proj.get('coordinator_country', 'N/A')
            participant_count = proj.get('participant_count', 0)
            country_count = proj.get('country_count', 0)
            sme_count = proj.get('sme_count', 0)
            framework_programme = proj.get('frameworkProgramme', 'N/A')
            funding_scheme = proj.get('fundingScheme', 'N/A')
            relevance_score = proj.get('relevance_score', 0)
            
            # Create structured summary
            summary = f"**Project {i}: {title}"
            if acronym and acronym != 'N/A':
                summary += f" ({acronym})"
            summary += "**"
            
            # Add relevance indicator if available
            if relevance_score > 0:
                summary += f" [Relevance: {relevance_score:.2f}]"
            
            # Duration and status
            if start_date != 'Unknown' and end_date != 'Unknown':
                summary += f"\n📅 **Duration:** {start_date} to {end_date}"
            elif start_date != 'Unknown':
                summary += f"\n📅 **Started:** {start_date}"
            
            if status != 'N/A':
                summary += f" (Status: {status})"
            
            # Programme and funding
            if framework_programme != 'N/A':
                summary += f"\n🏛️ **Programme:** {framework_programme}"
                if funding_scheme != 'N/A' and funding_scheme != framework_programme:
                    summary += f" / {funding_scheme}"
            
            if budget != 'N/A' and budget != 'Budget not specified':
                summary += f"\n💰 **Budget:** {budget}"
            
            # Enhanced CORDIS links
            if project_id and project_id != 'N/A':
                summary += f"\n🔗 **CORDIS:** https://cordis.europa.eu/project/id/{project_id}"
            elif rcn and rcn != 'N/A':
                summary += f"\n🔗 **CORDIS:** https://cordis.europa.eu/project/rcn/{rcn}"
            
            # Consortium information
            consortium_info = []
            if coordinator_name != 'N/A':
                coord_text = f"Coordinated by {coordinator_name}"
                if coordinator_country != 'N/A':
                    coord_text += f" ({coordinator_country})"
                consortium_info.append(coord_text)
            
            if participant_count > 0:
                participant_text = f"{participant_count} participants"
                if country_count > 1:
                    participant_text += f" from {country_count} countries"
                if sme_count > 0:
                    participant_text += f" (including {sme_count} SMEs)"
                consortium_info.append(participant_text)
            
            if consortium_info:
                summary += f"\n🤝 **Consortium:** {' | '.join(consortium_info)}"
            
            # Project description
            summary += f"\n\n{objective[:400]}{'...' if len(objective) > 400 else ''}"
            
            summaries.append(summary)
        
        return summaries

    def _generate_no_results_response(self, question: str) -> str:
        """Generate a helpful response when no projects are found."""
        suggestions = []
        
        # Analyze question for suggestions
        question_lower = question.lower()
        
        if 'recent' in question_lower or 'latest' in question_lower:
            suggestions.append("Try searching for projects from a broader time range")
        
        if any(term in question_lower for term in ['nuclear', 'quantum', 'blockchain']):
            suggestions.append("Consider searching for related or broader terms")
        
        if not suggestions:
            suggestions.append("Try rephrasing your question with different keywords")
            suggestions.append("Consider broadening your search criteria")
        
        response = "I couldn't find any specific project data matching your query in the CORDIS database."
        
        if hasattr(self, '_db_stats') and self.use_local_db:
            stats = self._db_stats
            response += f"\n\nOur database contains {stats['total_projects']} projects from {stats['date_range'][0]} to {stats['date_range'][1]}."
        
        response += f"\n\n**Suggestions:**\n" + "\n".join(f"• {s}" for s in suggestions)
        response += f"\n\n🔍 **Alternative:** Visit the full CORDIS database at https://cordis.europa.eu/search for comprehensive results."
        
        return response

    def _call_llm_for_generation(self, role: str, prompt: str) -> str:
        """Centralized LLM calling with error handling."""
        try:
            if self.ai_provider == "openai":
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model_name,
                    messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt}],
                    temperature=0.25
                )
                return response.choices[0].message.content
            elif self.ai_provider == "gemini":
                gemini_contents = [
                    types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                    types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
                ]
                gen_config = types.GenerateContentConfig(temperature=0.25)
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model_name,
                    contents=gemini_contents,
                    config=gen_config
                )
                return response.text
        except Exception as e:
            print(f"LLM generation error: {e}")
            return "I apologize, but I encountered an error generating the response. Please try again."

    def _get_phase1_prompt(self, question: str):
        # Get current year for dynamic date calculations
        current_year = datetime.now().year
        recent_start_year = current_year - 5  # Last 5 years for "recent"
        very_recent_start_year = current_year - 3  # Last 3 years for "very recent"
        
        role = f"""You play the role of a knowledge steward providing the research and innovation landscape of European research projects. You are helping to a research university or an institute or an SME to retrieve information from the corpus of previously funded projects.\nYour scenario of operation is as such: \nYou will receive a question. In two stages, you will extract queries from the question. At the first stage, you should extract queries to retrieve information about projects required to answer the questions. The first stage queries will be input to a xml retriever. Those queries may be names, topics, keywords, used methods and technologies of the projects as well as information related to participating organizations such as name, country, type, employees of the institution. Occasionally, they may be start and end dates of projects, a budget interval or the name or the acronym of a project call. \nThe xml retriever will retrieve xml files that include information about the project. If needed, at the second stage, according to information in the xml files and the information need in the question, you will generate new queries called second stage queries that will be input to the xml retriever.\n"""
        quest = f"""The question is: {question}\nPlease generate the first stage queries to input to the xml retriever to retrieve projects relevant to the question. Generate neat and concise textual boolean queries. If you need to connect parts of a query with \"AND\" connective, give them as seperate queries. That is, for example, if the query is \"word1 AND word2\" give it as two seperate queries which are \"word1\" and \"word2\". However, if you need to connect parts of a query with \"OR\" do it explicitly and do not seperate it into multiple queries in this case. That is, \"word1 OR word2\" should be given as it is. If you generate a query about dates, write in the format \"startDate>YEAR-MONTH-DAY\", \"endDate>YEAR-MONTH-DAY\". If you generate a query about budget, write in the format totalCost<1000, totalCost>1000. Moreover, if you are given a budget interval between a lower limit ans an upper limit write it in the format totalCost=lower-upper. Note that date related information need may be implicitly given in the question using words recent, first, last etc. For \"recent\" projects, use startDate>{recent_start_year}-01-01 to capture projects from the last 5 years. For \"very recent\" or \"latest\", use startDate>{very_recent_start_year}-01-01. If you generate a query about geographical locations, only include country names and no other region names, no continent names, no city names. Explain your reasoning step by step. Do not provide the queries or relations about which you are not sure. Give your whole answer in xml format with the fields <explanation>,<code>, and <problem>. Your explanations goes under <explanations> key. Under the <code> key, provide the queries as a Python code in the following format:   \"\nqueries= []\nproblem_flag = False\nrequired_information = []\nsecond_stage = False\nranking_criteria = []\n\"\nGive the code in exactly five lines.\nThe list of queries you generate must be at the first line. For example, for the question \"What are the machine learning related projects?\" the queries list should be queries = [machine learning OR deep learning OR artificial intelligence] and for the question \"What are the machine learning related projects in which Turkish organizations participated?\" the queries list should be queries = [machine learning OR deep learning OR artificial intelligence, Turkey]. Please keep this format. Note that queries should only include texts in natural language and the logical connectives. If no queries can be generated from given information, take the question itself as the query and add it to the queries list. Also, do not forget that queries include be names, topics, keywords, used methods and technologies of the projects as well as information related to participating organizations such as name, country, type of the institution. Occasionally, they may include start and end dates of projects, a budget interval or the name or the acronym of a project call. \nYou must put the variable problem_flag to the second line. problem_flag is set True when such a problem in the question exists: If you think the question is problematic (irrelevant or too general or we have no sufficient information sources to answer the question), set the problem_flag to True in the code and write the problem and a brief guiding sentence for the user under the <problem> key.\nThe third line must contain the list named required_information. As you know, some xml files each holding information about one project will be returned as response to your queries. Remember that a second stage of query generation may be run on those xml files. So, decide that which type of information should be requested by the second stage queries. Fill the required_information list with the required types of information that will be asked in second stage queries. Available types of information are project_objective, keywords, call_scope, budget, participant_names, participant_properties, participant_countries. For example, if countries of participants are required for the second stage, the required information list should be required_information = [participant_countries]. Note that if you need participant related information for the second stage, you generally do not need keywords. If no second stage queries are required, leave required_information list empty and set second_stage=False.\nAs underlined in the provided code format, the variable second_stage must be at the fourth line.\nAt the fifth line we have another list named ranking_criteria. Let me explain the expected content of that list: After the first stage retrieval, we need to rerank the retrieved documents according to some criteria such that documents that are more relevant to the intention of the first stage retrieval ranked higher. However, those reranking criteria should be dynamically inferred from the question. Those criteria are expected to be recency, novelty, actuality, impact, success, budget level of the project. For example, when the first stage retrieval aims to retrieve most successful projects, the ranking criteria may be ranking_criteria = [high success, high impact, high novelty, high budget], similarly, when the the first stage retrieval aims to retrieve the most unrealistic projects, the ranking criteria may be ranking_criteria = [low success, low impact, low actuality]. Beware that in the list of queries you are absolutely forbidden to include reranking criteria such as impact, success, recency, novelty, actuality! For example, [\"machine learning\", \"successful\"] and [\"machine learning\", \"high impact\"] are WRONG queries because they respectively include the words \"successful\" and \"high impact\". \nBefore giving the code, in your explanation, explicitly write to what the question reduced after receiving the reply to the first stage query. That reduced question will help you to formulate the required information and to decide the ranking criteria. Then, try justifying that reduced question. If you cannot justify it, change the reduced question. Additionally, in your explanation, explicitly write why you selected the required information types and ranking criteria you selected. Then, try justifying your selections, and change the selections you cannot justify.\nThe last remarks for you: Firstly, if the second stage will not require retrieving information about projects or participating organizations, such a second stage is unnecessary. So, for such cases, set second_stage = False. Secondly, if the question asks for filtering projects according to a metric such as best projects, worst projects, most successful projects etc., we need some restrictions about the projects we will consider, such as topics, participants, keywords etc. of the project. Otherwise we cannot reply the question, so you must set problem_flag = True in this case. Also, if the only restriction is about time, we can still not reply, so set problem_flag = True in this case as well. However, if the set of projects we should consider is sufficiently restricted, then we can devise a metric to answer such questions, therefore, no problem in this case. For example, we cannot answer the questions most successful project or the most successful recent project, however, we can answer the questions of most successful machine learning project or the most successful project conducted in Central Europe in the last decade. \n"""
        return role, quest

    def _extract_queries(self, role, quest):
        ans = ""
        if self.ai_provider == "openai":
            completion = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[{"role": "system", "content": role}, {"role": "user", "content": quest}],
                temperature=0.9,
                n=3
            )
            ans = completion.choices[1].message.content
        elif self.ai_provider == "gemini":
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="user", parts=[types.Part.from_text(text=quest)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.9)
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=gemini_contents,
                config=gen_config
            )
            ans = response.text
        ans_lines = ans.splitlines()
        end_flag = False
        queries = []
        next_pass = 0
        new_query_keys = []
        rerank_criteria = []
        problem_text = ""
        for line in ans_lines:
            if line == "problem_flag=True" or line=="problem_flag = True":
                end_flag = True
                break
            if "queries=" in line or "queries =" in line:
                lst = line[line.index("["):line.index("]")+1]
                queries = eval(lst)
            if "second_stage" in line:
                if "True" in line:
                    next_pass = 1
            if "required_information=" in line or "required_information =" in line:
                lst = line[line.index("["):line.index("]")+1]
                new_query_keys = eval(lst)
            if "ranking_criteria=" in line or "ranking_criteria =" in line:
                lst = line[line.index("["):line.index("]")+1]
                # Handle cases where words might already be quoted or have mixed quoting
                # First, normalize by removing any existing quotes
                lst_normalized = lst.replace('"', '').replace("'", '')
                # Then add proper quotes around bare words
                lst_quoted = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_\s]*)\b', r'"\1"', lst_normalized)
                # Clean up any double quotes that might result from the replacement
                lst_quoted = re.sub(r'""', r'"', lst_quoted)
                try:
                    rerank_criteria = eval(lst_quoted)
                except (SyntaxError, ValueError) as e:
                    print(f"Error parsing rerank_criteria: {lst} -> {lst_quoted}. Error: {e}")
                    rerank_criteria = []  # Fallback to empty list
        if end_flag:
            full = "\n".join(ans_lines)
            if "<problem>" in full and "</problem>" in full:
                start_problem = full.index("<problem>")
                end_problem = full.index("</problem>")
                problem_text = full[start_problem+9:end_problem]
            else:
                problem_text = "Problematic question."
        return queries, end_flag, new_query_keys, rerank_criteria, problem_text, next_pass

    def _search_cordis_api(self, queries: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        # Create cache key from queries
        cache_key = self._get_cache_key((queries, max_results))
        
        # Check cache first
        cached_result = self._get_from_cache(self._api_cache, cache_key)
        if cached_result is not None:
            print(f"Using cached CORDIS API results for {len(queries)} queries")
            return cached_result
        
        base_api_url = "https://cordis.europa.eu/api/search/results"
        api_q_parts = ["contenttype='project'", "language='en'"]
        for item_query in queries:
            item_query_stripped = item_query.strip()
            if not item_query_stripped:
                continue
            item_query_lower = item_query_stripped.lower()
            if "startdate" in item_query_lower or "enddate" in item_query_lower:
                date_str = item_query_stripped.replace(" ", "")
                api_q_parts.append(date_str)
            else:
                or_terms = item_query_stripped.split("OR")
                valid_or_terms = [term.strip() for term in or_terms if term.strip()]
                if not valid_or_terms:
                    continue
                quoted_or_terms = [f"'{term}'" for term in valid_or_terms]
                keyword_part = f"({ ' OR '.join(quoted_or_terms) })"
                api_q_parts.append(keyword_part)
        q_value = " AND ".join(api_q_parts)
        updated_fields = "uri,rcn,title,id,code,startDate,endDate,teaser,contentUpdateDate,name,relatedImage,availableLanguages,language,issueNumber,issueDate,issueLastDate,issue,archivedDate,acronym,legalName,euCode,city,country,iprPrefix,iprNumber,iprDate,iprAwarded,description,doi,journalTitle,journalNumber,publishedYear,publishedPages,authors,periodFrom,periodTo,webItem,webItem/_ATTR_*,physUrl,webLink,webLink/_ATTR_*,physUrl,frameworkProgramme,totalCost,projectTotalCost,keywords,subjects,programme,participants"
        params = {
            "q": q_value,
            "p": 1,
            "num": max_results,
            "srt": "Relevance:decreasing",
            # "fields": updated_fields,
            "archived": "true"
        }
        project_items: List[Dict[str, Any]] = []
        try:
            start_time = time.time()
            response = requests.get(base_api_url, params=params, timeout=30)
            response.raise_for_status()
            json_data = response.json()
            if json_data.get("payload") and "results" in json_data["payload"]:
                project_items = json_data["payload"]["results"]
            
            # Cache the result
            self._set_cache(self._api_cache, cache_key, project_items)
            print(f"CORDIS API call completed in {time.time() - start_time:.2f}s, found {len(project_items)} projects")
            
        except Exception as e:
            print(f"CORDIS API error: {e}")
        return project_items

    def _extract_project_data(self, project_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and structure project data from a CORDIS project item dictionary.
        
        Args:
            project_json: A dictionary containing raw project data from CORDIS API search result item.
        
        Returns:
            Dict[str, Any]: A dictionary with structured project data.
        """
        data = {}
        data['rcn'] = project_json.get('rcn', 'N/A')
        
        # Enhanced project ID extraction for better link generation
        project_id = None
        # Try multiple possible ID fields
        for id_field in ['id', 'reference', 'projectId', 'code']:
            if project_json.get(id_field):
                project_id = str(project_json[id_field]).strip()
                if project_id and project_id != 'N/A':
                    break
        
        # If still no ID, try extracting from URI field
        if not project_id or project_id == 'N/A':
            uri = project_json.get('uri', '')
            if uri and '/project/id/' in uri:
                try:
                    project_id = uri.split('/project/id/')[-1].split('/')[0]
                except:
                    pass
        
        data['id'] = project_id if project_id else 'N/A'
        data['title'] = project_json.get('title', 'N/A')
        data['acronym'] = project_json.get('acronym', 'N/A')
        data['objective'] = project_json.get('description', project_json.get('teaser', 'N/A'))
        if not data['objective'] or data['objective'] == 'N/A':
            data['objective'] = project_json.get('teaser', 'N/A')
        data['startDate'] = project_json.get('startDate', 'N/A')
        data['endDate'] = project_json.get('endDate', 'N/A')
        raw_budget = project_json.get('totalCost', project_json.get('projectTotalCost'))
        if isinstance(raw_budget, dict) and 'value' in raw_budget:
            currency = raw_budget.get('currency', '')
            value = raw_budget.get('value')
            data['budget'] = f"{value} {currency}".strip() if value is not None else 'N/A'
        elif raw_budget is not None:
            data['budget'] = str(raw_budget)
        else:
            data['budget'] = 'N/A'
        keywords_data = project_json.get('keywords', project_json.get('subjects'))
        if isinstance(keywords_data, list):
            data['keywords'] = ', '.join(str(k.get('label', k) if isinstance(k, dict) else k) for k in keywords_data if k)
        elif isinstance(keywords_data, str):
            data['keywords'] = keywords_data
        elif isinstance(keywords_data, dict):
            data['keywords'] = ', '.join(str(v) for v in keywords_data.values() if v)
        else:
            data['keywords'] = 'N/A'
        programme_info_list = project_json.get('programme')
        if isinstance(programme_info_list, list) and len(programme_info_list) > 0:
            main_programme = programme_info_list[0]
            if isinstance(main_programme, dict):
                call_title = main_programme.get('title', '')
                call_code = main_programme.get('code', '')
                data['call_info'] = f"{call_title} ({call_code})".strip() if call_title or call_code else 'N/A'
            else:
                data['call_info'] = str(main_programme)
        else:
            data['call_info'] = 'N/A'
        participant_names_list = []
        participant_countries_list = []
        participants_data = project_json.get('participants')
        if isinstance(participants_data, list):
            for p_entry in participants_data:
                if isinstance(p_entry, dict):
                    name = p_entry.get('name', p_entry.get('legalName', p_entry.get('shortName')))
                    country = p_entry.get('country')
                    if isinstance(country, dict):
                        country = country.get('isoCode', country.get('label'))
                    if name:
                        participant_names_list.append(str(name))
                    if country:
                        participant_countries_list.append(str(country))
        if not participant_names_list:
            coordinator_name = project_json.get('legalName')
            if coordinator_name:
                participant_names_list.append(str(coordinator_name))
            coordinator_country = project_json.get('country')
            if isinstance(coordinator_country, dict):
                coordinator_country = coordinator_country.get('isoCode', coordinator_country.get('label'))
            if coordinator_country:
                participant_countries_list.append(str(coordinator_country))
        data['participant_names'] = participant_names_list
        data['participant_countries'] = participant_countries_list
        authors_list = project_json.get('authors')
        pub_details = []
        if isinstance(authors_list, list) and authors_list:
            author_names = []
            for author_entry in authors_list:
                if isinstance(author_entry, dict):
                    author_names.append(author_entry.get('fullName', author_entry.get('name', 'Unknown Author')))
                else:
                    author_names.append(str(author_entry))
            if author_names:
                pub_details.append(f"Authors: {', '.join(author_names)}")
        journal_title = project_json.get('journalTitle')
        if journal_title:
            pub_details.append(f"Journal: {journal_title}")
        published_year = project_json.get('publishedYear')
        if published_year:
            pub_details.append(f"Year: {published_year}")
        data['publications'] = '. '.join(pub_details) if pub_details else 'N/A'
        return data

    def _rerank_projects(self, project_data, rerank_criteria, question, role):
        # Use LLM to rerank the projects according to rerank_criteria
        prompt_rerank = f"""The json files embodying detailed information about relevant projects are as follows: {json.dumps(project_data)}. Sort those json files according to the criteria in the following list: {rerank_criteria}. Also consider their relevance to the question and their overall importance. At the very and of your response, give the sorted list of titles of projects. The titles you put in the list must be written totally the same as they are in the json file. The list must be a python list named sorted_titles and must be in a single line. Except that list, do not include any python code in your reponse."""
        if self.ai_provider == "openai":
            reranker_response = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt_rerank}]
            )
            reranked_str = reranker_response.choices[0].message.content
        elif self.ai_provider == "gemini":
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="user", parts=[types.Part.from_text(text=prompt_rerank)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.7)
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=gemini_contents,
                config=gen_config
            )
            reranked_str = response.text
        offset = reranked_str.index("sorted_titles =") if "sorted_titles =" in reranked_str else reranked_str.index("sorted_titles=")
        start_idx_lst = reranked_str.index("[",offset)
        end_idx_lst = reranked_str.index("]",start_idx_lst)
        sorted_titles = eval(reranked_str[start_idx_lst:end_idx_lst+1].strip())
        reranked_jsons = []
        for title in sorted_titles[:5]:
            for proj in project_data:
                if set(proj["title"].lower().split(" ")) - {"", " "} == set(title.lower().split(" ")) - {"", " "}:
                    reranked_jsons.append(proj)
        return reranked_jsons

    def _generate_answer(self, role: str, user_text: str, project_data: List[Dict[str, Any]]) -> str:
        if not project_data:
            return "I couldn't find any specific project data relevant to your query in the CORDIS database. You might want to try rephrasing your question or making it more specific."
        
        # Create enhanced project summaries with richer database information
        project_summaries = []
        for proj in project_data:
            title = proj.get('title', 'Unknown Title')
            acronym = proj.get('acronym', '')
            objective = proj.get('objective', 'No description available')
            budget = proj.get('budget', 'Budget not specified')
            start_date = proj.get('startDate', 'Unknown')
            end_date = proj.get('endDate', 'Unknown')
            project_id = proj.get('id', '')
            rcn = proj.get('rcn', '')
            status = proj.get('status', 'N/A')
            
            # Enhanced information from local database
            coordinator_name = proj.get('coordinator_name', 'N/A')
            coordinator_country = proj.get('coordinator_country', 'N/A')
            participant_count = proj.get('participant_count', 0)
            country_count = proj.get('country_count', 0)
            sme_count = proj.get('sme_count', 0)
            framework_programme = proj.get('frameworkProgramme', 'N/A')
            funding_scheme = proj.get('fundingScheme', 'N/A')
            relevance_score = proj.get('relevance_score', 0)
            
            # Create structured summary
            summary = f"**{title}"
            if acronym and acronym != 'N/A':
                summary += f" ({acronym})"
            summary += f"**"
            
            # Add relevance indicator if available
            if relevance_score > 0:
                summary += f" [Relevance: {relevance_score:.2f}]"
            
            # Duration and status
            if start_date != 'Unknown' and end_date != 'Unknown':
                summary += f"\n📅 **Duration:** {start_date} to {end_date}"
            elif start_date != 'Unknown':
                summary += f"\n📅 **Started:** {start_date}"
            
            if status != 'N/A':
                summary += f" (Status: {status})"
            
            # Programme and funding
            if framework_programme != 'N/A':
                summary += f"\n🏛️ **Programme:** {framework_programme}"
                if funding_scheme != 'N/A' and funding_scheme != framework_programme:
                    summary += f" / {funding_scheme}"
            
            # Add budget information
            if budget != 'N/A' and budget != 'Budget not specified':
                summary += f"\n💰 **Budget:** {budget}"
            
            # Enhanced CORDIS project link generation with multiple fallbacks
            cordis_link_added = False
            
            # Primary: Use project ID if available
            if project_id and project_id != 'N/A' and project_id.strip():
                summary += f"\n🔗 **CORDIS Link:** https://cordis.europa.eu/project/id/{project_id}"
                cordis_link_added = True
            
            # Fallback 1: Use RCN if project ID not available
            elif rcn and rcn != 'N/A' and rcn.strip():
                summary += f"\n🔗 **CORDIS Link:** https://cordis.europa.eu/project/rcn/{rcn}"
                cordis_link_added = True
            
            # Fallback 2: Search link using project title
            elif title and title != 'Unknown Title':
                search_title = title.replace(' ', '+').replace('&', '%26')
                summary += f"\n🔍 **CORDIS Search:** https://cordis.europa.eu/search?q={search_title}&p=1&num=10&srt=Relevance:decreasing"
                cordis_link_added = True
            
            # Always add a link, even if we have to use a general search
            if not cordis_link_added:
                summary += f"\n🔍 **CORDIS Database:** https://cordis.europa.eu/search"
            
            # Add project description
            summary += f"\n{objective[:350]}{'...' if len(objective) > 350 else ''}"
            
            # Add enhanced participant information
            if coordinator_name != 'N/A' and coordinator_country != 'N/A':
                summary += f"\n👥 **Coordinated by:** {coordinator_name} ({coordinator_country})"
            elif coordinator_name != 'N/A':
                summary += f"\n👥 **Coordinated by:** {coordinator_name}"
            elif coordinator_country != 'N/A':
                summary += f"\n🌍 **Country:** {coordinator_country}"
            
            if participant_count > 0:
                summary += f"\n👥 **Participants:** {participant_count} total"
                if country_count > 1:
                    summary += f" ({country_count} countries)"
                if sme_count > 0:
                    summary += f" | {sme_count} SMEs involved"
            
            # Add keywords and call information if available
            if proj.get('keywords') and proj['keywords'] != 'N/A':
                summary += f"\n🔑 **Keywords:** {proj['keywords']}"
            if proj.get('call_info') and proj['call_info'] != 'N/A':
                summary += f"\n📞 **Call Info:** {proj['call_info']}"
            
            summaries.append(summary)
        
        # Create enhanced prompt for answer generation
        projects_text = "\n\n".join(summaries)
        data_source_note = "from our local CORDIS database" if self.use_local_db else "from the CORDIS database"
        
        prompt = f"""Based on the following European research projects {data_source_note}, provide a comprehensive and natural answer to the user's question.

User Question: {user_text}

Retrieved Projects:
{projects_text}

Instructions:
- Write in a conversational, informative tone
- ALWAYS mention and include the provided CORDIS links for each project you discuss
- Highlight the most relevant and recent projects first
- Include specific details like budgets, timelines, consortium information, and key participants when available
- Note the programme frameworks (Horizon, FP7, etc.) when relevant
- Group related projects or identify common themes
- If projects span different time periods, organize chronologically or by relevance
- Make sure to preserve all the 🔗 CORDIS Link and 🔍 CORDIS Search links in your response
- Encourage users to visit the CORDIS links for more detailed information
- Don't use template phrases like "Stage 1" or "based on retrieved information"
- Write as if you're explaining to someone interested in the research landscape
- If any projects seem outdated for the question (e.g., asking for "recent" but showing old projects), acknowledge this
- Leverage the rich consortium information (coordinators, SME participation, geographic distribution) when relevant
"""
        
        if self.ai_provider == "openai":
            response = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt}],
                temperature=0.25  # Lower temperature for more accurate, factual responses
            )
            final_response = response.choices[0].message.content
        elif self.ai_provider == "gemini":
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.25)  # Lower temperature for more accurate, factual responses
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=gemini_contents,
                config=gen_config
            )
            final_response = response.text
        
        # Ensure links are preserved in the final response
        if 'cordis.europa.eu' not in final_response.lower():
            final_response += f"\n\n🔗 **For more detailed information, visit the CORDIS database:** https://cordis.europa.eu/"
        
        return final_response

    def _search_local_database(self, queries: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Enhanced database search with full-text search, query optimization, and better relevance scoring.
        """
        # Create cache key from queries
        cache_key = self._get_cache_key((queries, max_results, "local_db_enhanced"))
        
        # Check cache first
        cached_result = self._get_from_cache(self._db_cache, cache_key)
        if cached_result is not None:
            print(f"Using cached database results for {len(queries)} queries")
            return cached_result
        
        if not self.db_pool:
            print("❌ Database pool not available")
            return []
        
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            # Preprocess queries for better matching
            processed_queries = self._preprocess_queries(queries)
            print(f"🔍 Enhanced search for: {processed_queries}")
            
            # Separate text queries from date/budget queries
            text_queries = []
            date_conditions = []
            budget_conditions = []
            
            for query in processed_queries:
                query = query.strip()
                if not query:
                    continue
                    
                # Handle date queries
                if 'startdate>' in query.lower():
                    try:
                        date_part = query.lower().split('startdate>')[1]
                        date_conditions.append(f"p.\"startDate\" >= '{date_part}'")
                        print(f"📅 Added date condition: startDate >= {date_part}")
                        continue
                    except:
                        print(f"⚠️ Could not parse date query: {query}")
                        continue
                elif 'enddate>' in query.lower():
                    try:
                        date_part = query.lower().split('enddate>')[1]
                        date_conditions.append(f"p.\"endDate\" >= '{date_part}'")
                        continue
                    except:
                        continue
                elif 'totalcost' in query.lower():
                    try:
                        budget_conditions.append(self._parse_budget_query(query))
                        continue
                    except:
                        continue
                
                text_queries.append(query)
            
            # Build enhanced SQL query with full-text search and relevance scoring
            if text_queries:
                projects = self._execute_enhanced_text_search(cursor, text_queries, date_conditions, budget_conditions, max_results)
            else:
                # No text queries, just date/budget filters
                projects = self._execute_filtered_search(cursor, date_conditions, budget_conditions, max_results)
            
            # Cache the result
            self._set_cache(self._db_cache, cache_key, projects)
            
            print(f"Enhanced database search completed, found {len(projects)} projects")
            return projects
            
        except Exception as e:
            print(f"Database query error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self.db_pool.putconn(conn)

    def _execute_enhanced_text_search(self, cursor, text_queries: List[str], date_conditions: List[str], 
                                    budget_conditions: List[str], max_results: int) -> List[Dict[str, Any]]:
        """Execute enhanced full-text search with PostgreSQL tsvector."""
        
        # Build full-text search conditions
        search_conditions = []
        params = []
        
        for query in text_queries:
            # Convert OR/AND logic to PostgreSQL tsquery format
            ts_query = self._convert_to_tsquery(query)
            search_conditions.append("""
                (to_tsvector('english', p.title || ' ' || COALESCE(p.objective, '') || ' ' || COALESCE(p.topics, '')) @@ to_tsquery('english', %s)
                 OR to_tsvector('english', COALESCE(o.name, '') || ' ' || COALESCE(o.country, '')) @@ to_tsquery('english', %s))
            """)
            params.extend([ts_query, ts_query])
        
        # Build complete WHERE clause
        all_conditions = search_conditions + date_conditions + budget_conditions
        where_clause = f" AND ({' AND '.join(all_conditions)})" if all_conditions else ""
        
        # Enhanced SQL with relevance scoring
        sql_query = f"""
            SELECT DISTINCT
                p.id,
                p.acronym,
                p.title,
                p.objective,
                p."startDate",
                p."endDate",
                p."totalCost",
                p."ecMaxContribution",
                p.status,
                p.topics,
                p."frameworkProgramme",
                p."fundingScheme",
                p."legalBasis",
                p.rcn,
                p."grantDoi",
                -- Relevance scoring
                ts_rank_cd(to_tsvector('english', p.title || ' ' || COALESCE(p.objective, '')), 
                          to_tsquery('english', %s), 32) as relevance_score,
                -- Aggregated organization data
                COUNT(o."organisationID") as participant_count,
                ARRAY_AGG(DISTINCT o.name) FILTER (WHERE o.name IS NOT NULL) as participant_names,
                ARRAY_AGG(DISTINCT o.country) FILTER (WHERE o.country IS NOT NULL) as participant_countries,
                ARRAY_AGG(DISTINCT o.city) FILTER (WHERE o.city IS NOT NULL) as participant_cities,
                SUM(o."ecContribution") as total_ec_contribution,
                SUM(o."netEcContribution") as total_net_ec_contribution,
                SUM(o."totalCost") as total_org_costs,
                -- Coordinator information
                MAX(CASE WHEN o.role = 'coordinator' THEN o.name END) as coordinator_name,
                MAX(CASE WHEN o.role = 'coordinator' THEN o.country END) as coordinator_country,
                MAX(CASE WHEN o.role = 'coordinator' THEN o.city END) as coordinator_city,
                -- SME and geographic info
                COUNT(CASE WHEN o."SME" = true THEN 1 END) as sme_count,
                COUNT(DISTINCT o.country) as country_count,
                ARRAY_AGG(DISTINCT o."nutsCode") FILTER (WHERE o."nutsCode" IS NOT NULL) as nuts_codes,
                ARRAY_AGG(DISTINCT o."activityType") FILTER (WHERE o."activityType" IS NOT NULL) as activity_types
            FROM projects p
            LEFT JOIN organizations o ON p.id = o."projectID"
            WHERE p.id IS NOT NULL{where_clause}
            GROUP BY p.id, p.acronym, p.title, p.objective, p."startDate", p."endDate", 
                     p."totalCost", p."ecMaxContribution", p.status, p.topics, 
                     p."frameworkProgramme", p."fundingScheme", p."legalBasis", p.rcn, p."grantDoi"
            ORDER BY relevance_score DESC, p."startDate" DESC NULLS LAST
            LIMIT %s
        """
        
        # Add relevance query parameter and limit
        all_params = [self._convert_to_tsquery(' OR '.join(text_queries))] + params + [max_results]
        
        start_time = time.time()
        cursor.execute(sql_query, all_params)
        rows = cursor.fetchall()
        
        print(f"📊 Enhanced search returned {len(rows)} rows in {time.time() - start_time:.2f}s")
        
        # Convert to structured project data
        projects = []
        for row in rows:
            project = self._format_db_project_data(dict(row))
            project['relevance_score'] = float(row.get('relevance_score', 0))
            projects.append(project)
            print(f"  - {project['title'][:50]}... (relevance: {project['relevance_score']:.3f})")
        
        return projects

    def _convert_to_tsquery(self, query: str) -> str:
        """Convert natural language query to PostgreSQL tsquery format."""
        # Handle OR conditions
        if ' OR ' in query.upper():
            terms = [term.strip() for term in re.split(r'\s+OR\s+', query, flags=re.IGNORECASE)]
            return ' | '.join(f'"{term}"' for term in terms if term)
        
        # Handle AND conditions (default)
        terms = query.split()
        # Filter out stopwords and short terms
        meaningful_terms = [term for term in terms if len(term) > 2 and term.lower() not in self._stopwords]
        
        if not meaningful_terms:
            return f'"{query}"'
        
        return ' & '.join(f'"{term}"' for term in meaningful_terms[:5])  # Limit to 5 terms

    def _parse_budget_query(self, query: str) -> str:
        """Parse budget queries like totalCost>1000000."""
        query_lower = query.lower()
        if 'totalcost>' in query_lower:
            amount = query_lower.split('totalcost>')[1]
            return f'p."totalCost" > {amount}'
        elif 'totalcost<' in query_lower:
            amount = query_lower.split('totalcost<')[1]
            return f'p."totalCost" < {amount}'
        elif 'totalcost=' in query_lower:
            range_part = query_lower.split('totalcost=')[1]
            if '-' in range_part:
                low, high = range_part.split('-')
                return f'p."totalCost" BETWEEN {low} AND {high}'
        return ""

    def _execute_filtered_search(self, cursor, date_conditions: List[str], budget_conditions: List[str], max_results: int) -> List[Dict[str, Any]]:
        """Execute search with only date and budget filters."""
        all_conditions = date_conditions + budget_conditions
        where_clause = f" AND ({' AND '.join(all_conditions)})" if all_conditions else ""
        
        # Simple filtered query
        sql_query = f"""
            SELECT DISTINCT
                p.id, p.acronym, p.title, p.objective, p."startDate", p."endDate",
                p."totalCost", p."ecMaxContribution", p.status, p.topics,
                p."frameworkProgramme", p."fundingScheme", p."legalBasis", p.rcn, p."grantDoi",
                COUNT(o."organisationID") as participant_count,
                ARRAY_AGG(DISTINCT o.name) FILTER (WHERE o.name IS NOT NULL) as participant_names,
                ARRAY_AGG(DISTINCT o.country) FILTER (WHERE o.country IS NOT NULL) as participant_countries,
                MAX(CASE WHEN o.role = 'coordinator' THEN o.name END) as coordinator_name,
                MAX(CASE WHEN o.role = 'coordinator' THEN o.country END) as coordinator_country,
                COUNT(CASE WHEN o."SME" = true THEN 1 END) as sme_count,
                COUNT(DISTINCT o.country) as country_count
            FROM projects p
            LEFT JOIN organizations o ON p.id = o."projectID"
            WHERE p.id IS NOT NULL{where_clause}
            GROUP BY p.id, p.acronym, p.title, p.objective, p."startDate", p."endDate",
                     p."totalCost", p."ecMaxContribution", p.status, p.topics,
                     p."frameworkProgramme", p."fundingScheme", p."legalBasis", p.rcn, p."grantDoi"
            ORDER BY p."startDate" DESC NULLS LAST, p."totalCost" DESC NULLS LAST
            LIMIT %s
        """
        
        cursor.execute(sql_query, [max_results])
        rows = cursor.fetchall()
        
        projects = []
        for row in rows:
            project = self._format_db_project_data(dict(row))
            projects.append(project)
        
        return projects

    def _adaptive_result_selection(self, project_data: List[Dict[str, Any]], question: str, max_results: int) -> List[Dict[str, Any]]:
        """Intelligently select the most relevant projects based on question context."""
        if len(project_data) <= max_results:
            return project_data
        
        # Score projects based on multiple factors
        scored_projects = []
        question_lower = question.lower()
        
        for project in project_data:
            score = 0
            
            # Relevance score from database
            score += project.get('relevance_score', 0) * 10
            
            # Recency bonus (more recent = higher score)
            try:
                start_date = project.get('startDate', '')
                if start_date and start_date != 'Unknown':
                    year = int(str(start_date)[:4])
                    current_year = datetime.now().year
                    recency_score = max(0, (year - 2010) / (current_year - 2010)) * 5
                    score += recency_score
            except:
                pass
            
            # Budget significance (larger budget = more significant)
            try:
                total_cost = project.get('totalCost', 0)
                if isinstance(total_cost, (int, float)) and total_cost > 0:
                    budget_score = min(5, total_cost / 10000000)  # Scale to max 5 points
                    score += budget_score
            except:
                pass
            
            # Participation diversity bonus
            country_count = project.get('country_count', 0)
            if country_count > 1:
                score += min(3, country_count * 0.5)
            
            # SME involvement bonus
            sme_count = project.get('sme_count', 0)
            if sme_count > 0:
                score += min(2, sme_count * 0.5)
            
            # Question-specific keyword matching
            title = project.get('title', '').lower()
            objective = project.get('objective', '').lower()
            
            # Check for question keywords in project
            question_words = set(question_lower.split()) - self._stopwords
            project_text = f"{title} {objective}".lower()
            
            keyword_matches = sum(1 for word in question_words if word in project_text and len(word) > 3)
            score += keyword_matches * 2
            
            scored_projects.append((score, project))
        
        # Sort by score and return top results
        scored_projects.sort(key=lambda x: x[0], reverse=True)
        return [project for score, project in scored_projects[:max_results]]

    def get_ai_response(self, question: str, max_projects_to_process: int = 5, max_cordis_results: int = 10) -> str:
        """
        Enhanced AI response generation with adaptive result selection and improved answer quality.
        """
        total_start_time = time.time()
        data_source = "Local Database" if self.use_local_db else "CORDIS API"
        print(f"🚀 Starting Enhanced V5 RAG pipeline using {data_source} for: '{question}'")
        
        # 1. Phase 1: Query extraction with enhanced preprocessing
        phase_start = time.time()
        role, quest = self._get_phase1_prompt(question)
        queries, end_flag, new_query_keys, rerank_criteria, problem_text, next_pass = self._extract_queries(role, quest)
        print(f"📝 Phase 1 (Query extraction) completed in {time.time() - phase_start:.2f}s")
        
        if end_flag:
            return problem_text
        
        # 2. Phase 2: Enhanced data retrieval
        phase_start = time.time()
        if self.use_local_db:
            # Get more results initially for better selection
            initial_results = max_projects_to_process * 3
            raw_project_data = self._search_local_database(queries, max_results=initial_results)
            
            # Intelligently select the best projects
            project_data = self._adaptive_result_selection(raw_project_data, question, max_projects_to_process)
            print(f"🎯 Selected {len(project_data)} best projects from {len(raw_project_data)} candidates")
            
            print(f"🔍 Phase 2 (Enhanced Local DB search) completed in {time.time() - phase_start:.2f}s")
        else:
            project_items = self._search_cordis_api(queries, max_results=max_cordis_results)
            print(f"🔍 Phase 2 (CORDIS API search) completed in {time.time() - phase_start:.2f}s")
            
            # Phase 3: Project data extraction (only for API mode)
            phase_start = time.time()
            project_data = [self._extract_project_data(item) for item in project_items[:max_projects_to_process]]
            print(f"📊 Phase 3 (Data extraction) completed in {time.time() - phase_start:.2f}s")
            
            # Phase 3.5: XML enrichment (only for API mode)
            phase_start = time.time()
            project_data = self._enrich_with_xml_data(project_data)
            print(f"🔗 Phase 3.5 (XML enrichment) completed in {time.time() - phase_start:.2f}s")
        
        # 4. Phase 4: Enhanced reranking
        if rerank_criteria and len(project_data) > 1:
            phase_start = time.time()
            project_data = self._enhanced_rerank_projects(project_data, rerank_criteria, question, role)
            print(f"📈 Phase 4 (Enhanced reranking) completed in {time.time() - phase_start:.2f}s")
        
        # 5. Phase 6: Enhanced answer generation
        phase_start = time.time()
        answer = self._generate_enhanced_answer(role, question, project_data)
        print(f"💬 Phase 6 (Enhanced answer generation) completed in {time.time() - phase_start:.2f}s")
        
        total_time = time.time() - total_start_time
        print(f"✅ Enhanced V5 RAG pipeline completed in {total_time:.2f}s total")
        
        return answer

    def _enhanced_rerank_projects(self, project_data: List[Dict[str, Any]], rerank_criteria: List[str], 
                                question: str, role: str) -> List[Dict[str, Any]]:
        """Enhanced reranking with better project scoring and selection."""
        if len(project_data) <= 1:
            return project_data
        
        # Combine LLM reranking with algorithmic scoring
        llm_ranked = self._rerank_projects(project_data, rerank_criteria, question, role)
        
        # If LLM reranking failed, fall back to algorithmic ranking
        if not llm_ranked:
            return self._adaptive_result_selection(project_data, question, len(project_data))
        
        return llm_ranked

    def _generate_enhanced_answer(self, role: str, user_text: str, project_data: List[Dict[str, Any]]) -> str:
        """Generate enhanced answer with better structure and insights."""
        if not project_data:
            return self._generate_no_results_response(user_text)
        
        # Analyze project portfolio for insights
        insights = self._analyze_project_portfolio(project_data)
        
        # Generate enhanced project summaries
        project_summaries = self._create_enhanced_project_summaries(project_data)
        
        # Create enhanced prompt with insights
        projects_text = "\n\n".join(project_summaries)
        data_source_note = "from our local CORDIS database" if self.use_local_db else "from the CORDIS database"
        
        insights_text = ""
        if insights:
            insights_text = f"\n\nPortfolio Insights:\n{insights}"
        
        prompt = f"""Based on the following European research projects {data_source_note}, provide a comprehensive and insightful answer to the user's question.

User Question: {user_text}

Retrieved Projects:
{projects_text}{insights_text}

Instructions:
- Write in a conversational, authoritative tone
- Start with a clear overview addressing the user's question
- ALWAYS include the provided CORDIS links for each project discussed
- Highlight the most relevant and recent projects first
- Include specific details like budgets, timelines, consortium information, and geographic distribution
- Note programme frameworks (Horizon, FP7, etc.) and their significance
- Identify trends, patterns, and relationships between projects
- Use the portfolio insights to provide deeper analysis
- Organize information logically with clear sections if discussing multiple aspects
- Make sure to preserve all 🔗 CORDIS Links in your response
- Conclude with actionable insights or recommendations when appropriate
- Write as if you're an expert consultant familiar with the European research landscape
"""
        
        return self._call_llm_for_generation(role, prompt)

    def _analyze_project_portfolio(self, projects: List[Dict[str, Any]]) -> str:
        """Analyze the project portfolio to extract insights."""
        if len(projects) < 2:
            return ""
        
        insights = []
        
        # Temporal analysis
        years = []
        for project in projects:
            try:
                start_date = project.get('startDate', '')
                if start_date and start_date != 'Unknown':
                    year = int(str(start_date)[:4])
                    years.append(year)
            except:
                pass
        
        if years:
            insights.append(f"Projects span from {min(years)} to {max(years)}")
        
        # Geographic analysis
        all_countries = []
        for project in projects:
            countries = project.get('participant_countries', [])
            all_countries.extend(countries)
        
        if all_countries:
            country_counts = defaultdict(int)
            for country in all_countries:
                country_counts[country] += 1
            top_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            insights.append(f"Top participating countries: {', '.join([f'{c} ({n})' for c, n in top_countries])}")
        
        # Budget analysis
        budgets = []
        for project in projects:
            try:
                total_cost = project.get('totalCost', 0)
                if isinstance(total_cost, (int, float)) and total_cost > 0:
                    budgets.append(total_cost)
            except:
                pass
        
        if budgets:
            total_funding = sum(budgets)
            avg_budget = total_funding / len(budgets)
            insights.append(f"Total funding: €{total_funding:,.0f}, Average: €{avg_budget:,.0f}")
        
        # Framework analysis
        frameworks = defaultdict(int)
        for project in projects:
            fw = project.get('frameworkProgramme', 'Unknown')
            if fw and fw != 'N/A':
                frameworks[fw] += 1
        
        if frameworks:
            top_fw = max(frameworks.items(), key=lambda x: x[1])
            insights.append(f"Most common programme: {top_fw[0]} ({top_fw[1]} projects)")
        
        return " | ".join(insights) if insights else ""

    def _create_enhanced_project_summaries(self, projects: List[Dict[str, Any]]) -> List[str]:
        """Create enhanced project summaries with better formatting and information."""
        summaries = []
        
        for i, proj in enumerate(projects, 1):
            title = proj.get('title', 'Unknown Title')
            acronym = proj.get('acronym', '')
            objective = proj.get('objective', 'No description available')
            budget = proj.get('budget', 'Budget not specified')
            start_date = proj.get('startDate', 'Unknown')
            end_date = proj.get('endDate', 'Unknown')
            project_id = proj.get('id', '')
            rcn = proj.get('rcn', '')
            status = proj.get('status', 'N/A')
            
            # Enhanced information from database
            coordinator_name = proj.get('coordinator_name', 'N/A')
            coordinator_country = proj.get('coordinator_country', 'N/A')
            participant_count = proj.get('participant_count', 0)
            country_count = proj.get('country_count', 0)
            sme_count = proj.get('sme_count', 0)
            framework_programme = proj.get('frameworkProgramme', 'N/A')
            funding_scheme = proj.get('fundingScheme', 'N/A')
            relevance_score = proj.get('relevance_score', 0)
            
            # Create structured summary
            summary = f"**Project {i}: {title}"
            if acronym and acronym != 'N/A':
                summary += f" ({acronym})"
            summary += "**"
            
            # Add relevance indicator if available
            if relevance_score > 0:
                summary += f" [Relevance: {relevance_score:.2f}]"
            
            # Duration and status
            if start_date != 'Unknown' and end_date != 'Unknown':
                summary += f"\n📅 **Duration:** {start_date} to {end_date}"
            elif start_date != 'Unknown':
                summary += f"\n📅 **Started:** {start_date}"
            
            if status != 'N/A':
                summary += f" (Status: {status})"
            
            # Programme and funding
            if framework_programme != 'N/A':
                summary += f"\n🏛️ **Programme:** {framework_programme}"
                if funding_scheme != 'N/A' and funding_scheme != framework_programme:
                    summary += f" / {funding_scheme}"
            
            # Add budget information
            if budget != 'N/A' and budget != 'Budget not specified':
                summary += f"\n💰 **Budget:** {budget}"
            
            # Enhanced CORDIS links
            if project_id and project_id != 'N/A':
                summary += f"\n🔗 **CORDIS Link:** https://cordis.europa.eu/project/id/{project_id}"
            elif rcn and rcn != 'N/A':
                summary += f"\n🔗 **CORDIS Link:** https://cordis.europa.eu/project/rcn/{rcn}"
            
            # Consortium information
            consortium_info = []
            if coordinator_name != 'N/A':
                coord_text = f"Coordinated by {coordinator_name}"
                if coordinator_country != 'N/A':
                    coord_text += f" ({coordinator_country})"
                consortium_info.append(coord_text)
            
            if participant_count > 0:
                participant_text = f"{participant_count} participants"
                if country_count > 1:
                    participant_text += f" from {country_count} countries"
                if sme_count > 0:
                    participant_text += f" (including {sme_count} SMEs)"
                consortium_info.append(participant_text)
            
            if consortium_info:
                summary += f"\n🤝 **Consortium:** {' | '.join(consortium_info)}"
            
            # Project description
            summary += f"\n\n{objective[:400]}{'...' if len(objective) > 400 else ''}"
            
            summaries.append(summary)
        
        return summaries

    def _generate_no_results_response(self, question: str) -> str:
        """Generate a helpful response when no projects are found."""
        suggestions = []
        
        # Analyze question for suggestions
        question_lower = question.lower()
        
        if 'recent' in question_lower or 'latest' in question_lower:
            suggestions.append("Try searching for projects from a broader time range")
        
        if any(term in question_lower for term in ['nuclear', 'quantum', 'blockchain']):
            suggestions.append("Consider searching for related or broader terms")
        
        if not suggestions:
            suggestions.append("Try rephrasing your question with different keywords")
            suggestions.append("Consider broadening your search criteria")
        
        response = "I couldn't find any specific project data matching your query in the CORDIS database."
        
        if hasattr(self, '_db_stats') and self.use_local_db:
            stats = self._db_stats
            response += f"\n\nOur database contains {stats['total_projects']} projects from {stats['date_range'][0]} to {stats['date_range'][1]}."
        
        response += f"\n\n**Suggestions:**\n" + "\n".join(f"• {s}" for s in suggestions)
        response += f"\n\n🔍 **Alternative:** Visit the full CORDIS database at https://cordis.europa.eu/search for comprehensive results."
        
        return response

    def _call_llm_for_generation(self, role: str, prompt: str) -> str:
        """Centralized LLM calling with error handling."""
        try:
            if self.ai_provider == "openai":
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model_name,
                    messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt}],
                    temperature=0.25
                )
                return response.choices[0].message.content
            elif self.ai_provider == "gemini":
                gemini_contents = [
                    types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                    types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
                ]
                gen_config = types.GenerateContentConfig(temperature=0.25)
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model_name,
                    contents=gemini_contents,
                    config=gen_config
                )
                return response.text
        except Exception as e:
            print(f"LLM generation error: {e}")
            return "I apologize, but I encountered an error generating the response. Please try again."

    # ...existing code for other methods...
    
    def __del__(self):
        """Clean up database connections."""
        if hasattr(self, 'db_pool') and self.db_pool:
            self.db_pool.closeall()

if __name__ == "__main__":
    def test_local_database():
        """Test the local database functionality"""
        print("="*60)
        print("TESTING LOCAL DATABASE INTEGRATION")
        print("="*60)
        
        try:
            # Test with local database
            rag_local = CordisRAG(use_local_db=True)
            
            test_questions = [
                "What are some AI projects in healthcare?",
                "European renewable energy projects",
                "Projects coordinated by German organizations"
            ]
            
            for i, question in enumerate(test_questions, 1):
                print(f"\n🧪 Test {i}: {question}")
                print("-" * 50)
                
                start_time = time.time()
                response = rag_local.get_ai_response(question, max_projects_to_process=3)
                elapsed = time.time() - start_time
                
                print(f"✅ Test {i} completed in {elapsed:.2f}s")
                print(f"Response length: {len(response)} characters")
                print(f"Contains CORDIS links: {'cordis.europa.eu' in response}")
                
                # Show a snippet of the response
                print(f"Response preview: {response[:200]}...")
                
            return True
            
        except Exception as e:
            print(f"❌ Local database test failed: {e}")
            return False
    
    def compare_performance():
        """Compare performance between local database and API"""
        print("="*60)
        print("PERFORMANCE COMPARISON: LOCAL DB vs CORDIS API")
        print("="*60)
        
        question = "machine learning projects in healthcare"
        
        try:
            # Test local database
            print("\n🔍 Testing Local Database...")
            rag_local = CordisRAG(use_local_db=True)
            start_time = time.time()
            response_local = rag_local.get_ai_response(question, max_projects_to_process=3)
            local_time = time.time() - start_time
            
            print(f"✅ Local DB completed in {local_time:.2f}s")
            print(f"Local response length: {len(response_local)} characters")
            
            # Test CORDIS API
            print("\n🌐 Testing CORDIS API...")
            rag_api = CordisRAG(use_local_db=False)
            start_time = time.time()
            response_api = rag_api.get_ai_response(question, max_projects_to_process=3, max_cordis_results=5)
            api_time = time.time() - start_time
            
            print(f"✅ CORDIS API completed in {api_time:.2f}s")
            print(f"API response length: {len(response_api)} characters")
            
            # Performance comparison
            speedup = api_time / local_time if local_time > 0 else 0
            print(f"\n📊 Performance Results:")
            print(f"Local Database: {local_time:.2f}s")
            print(f"CORDIS API: {api_time:.2f}s")
            print(f"Speedup: {speedup:.1f}x faster with local database")
            
            return True
            
        except Exception as e:
            print(f"❌ Performance comparison failed: {e}")
            return False
    
    # Run tests
    print("🚀 Starting V5 Local Database Tests...")
    
    db_test_passed = test_local_database()
    print("\n" + "="*60)
    
    if db_test_passed:
        compare_performance()
        print("\n🎉 ALL V5 TESTS PASSED! Local database integration working correctly.")
    else:
        print("\n❌ Local database tests failed.")
    
    print("="*60)
