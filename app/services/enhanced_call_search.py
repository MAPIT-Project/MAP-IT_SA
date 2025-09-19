"""
Enhanced Call Search Service - Matching EU Portal's Sophisticated Approach

This service implements the multi-step search workflow used by the EU Funding & Tenders Portal:
1. Tag-based semantic search using client-centricity.io API
2. Advanced boolean query construction with field-specific boosts
3. Comprehensive facet analysis and filtering
4. Multi-step result processing and scoring
"""

import requests
import json
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict, field
import hashlib
import re

# Import the AI query parser
try:
    from .ai_query_parser import AIQueryParser, QueryFilters
    QUERY_PARSER_AVAILABLE = True
except ImportError:
    QUERY_PARSER_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class TagBoost:
    """Container for tag codes with boost scores."""
    code: str
    boost: float

@dataclass
class EnhancedSearchResult:
    """Enhanced search result with comprehensive metadata."""
    identifier: str
    title: str
    description: str
    status: str
    status_code: str
    deadline: str
    programme_period: str
    framework_programme: str
    call_identifier: str
    url: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    facets: Dict[str, Any] = None

class EnhancedCallSearchService:
    """Enhanced call search service matching EU portal sophistication."""
    
    def __init__(self):
        """Initialize the enhanced search service."""
        self.tags_api_url = "https://client-centricity.io/tags/query"
        self.search_api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
        self.facet_api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/facet"
        
        # Cache for tag queries to avoid repeated API calls
        self._tag_cache = {}
        self._cache_ttl = 3600  # 1 hour
        
        # Initialize AI query parser
        if QUERY_PARSER_AVAILABLE:
            self.query_parser = AIQueryParser()
            logger.info("✅ AI query parser initialized")
        else:
            self.query_parser = None
            logger.warning("⚠️ AI query parser not available")
        
        # Status code mapping (CORRECT!)
        self.status_mapping = {
            '31094501': 'Forthcoming', # Forthcoming/Future calls
            '31094502': 'Open',        # Open for submission
            '31094503': 'Closed',      # Closed calls
        }
        
        # Search configuration - maximize results
        self.default_params = {
            "apiKey": "SEDIA",
            "pageSize": "100",  # Increased from 50 to get more results
            "pageNumber": "1"
        }
        
        logger.info("✅ Enhanced call search service initialized")
    
    def search_calls_enhanced(
        self,
        query: str,
        max_results: int = 50,  # Increased from 10 to return more calls by default
        include_closed: bool = False,
        programme_period: str = "2021 - 2027",
        enable_facet_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Main enhanced search method implementing the EU portal's workflow.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            include_closed: Whether to include closed calls (overridden by intelligent parsing)
            programme_period: Programme period filter
            enable_facet_analysis: Whether to perform facet analysis
            
        Returns:
            Comprehensive search results with facets and metadata
        """
        
        start_time = time.time()
        logger.info(f"🚀 Enhanced search starting: '{query}'")
        
        # Step 0: Parse query for intelligent filtering and simplification
        parsed_filters = None
        search_query_text = query
        
        if self.query_parser:
            parsed_filters = self.query_parser.parse_query(query)
            search_query_text = parsed_filters.clean_query
            
        # Step 0.1: Simplify complex natural language queries for better API results
        search_query_text = self._simplify_query_for_api(search_query_text, query)
        
        # Cluster normalization: map "cluster X" to programme + identifier hints  
        if self.query_parser:
            m = re.search(r"cluster\s*(\d)", search_query_text, re.IGNORECASE)
            if m:
                cluster_num = m.group(1)
                cluster_map = {
                    '1': 'Health',
                    '2': 'Culture, Creativity and Inclusive Society',
                    '3': 'Civil Security for Society',
                    '4': 'Digital, Industry and Space',
                    '5': 'Climate, Energy and Mobility',
                    '6': 'Food, Bioeconomy, Natural Resources, Agriculture and Environment',
                }
                cluster_label = cluster_map.get(cluster_num)
                if cluster_label:
                    logger.info(f"🧭 Normalized cluster {cluster_num} to '{cluster_label}' and identifier hint")
                    # Replace the raw question with strong tokens only for the portal text field
                    search_query_text = f"HORIZON-CL{cluster_num} \"{cluster_label}\""
                    # Attach a specific filter flag to help advanced query builder
                    if not parsed_filters.specific_filters:
                        parsed_filters.specific_filters = {}
                    parsed_filters.specific_filters[f'cluster_{cluster_num}'] = True
            # If the user explicitly asked for OPEN calls, force open-only status filter
            if 'open' in query.lower():
                if not getattr(parsed_filters, 'status_filter', None):
                    parsed_filters.status_filter = ['31094502']  # Open only
                logger.info("🎯 Detected 'open' in query -> forcing OPEN-only status filter")
            logger.info(f"🧠 Parsed query: '{search_query_text}' with intention: {parsed_filters.filter_intention}")
        
        try:
            # Step 1: Get semantic tags with boost scores (using clean query)
            tag_boosts = self._get_semantic_tags(search_query_text)
            logger.info(f"📊 Retrieved {len(tag_boosts)} semantic tags")
            
            # Step 2: Build advanced query structure with intelligent filtering
            search_query = self._build_advanced_query(
                search_query_text,
                tag_boosts,
                parsed_filters,
                include_closed
            )
            
            # Step 3: Get facet analysis (if enabled)
            facets = {}
            if enable_facet_analysis:
                facets = self._get_facet_analysis(search_query)
                logger.info(f"📈 Retrieved {len(facets)} facet categories")
            
            # Step 4: Execute main search
            search_results = self._execute_enhanced_search(search_query, max_results)
            
            # Step 5: Process and enrich results
            processed_results = self._process_enhanced_results(search_results, query)
            
            # Only normalize status using deadline if we're including closed calls
            # If user specifically asked for open calls, don't override the API status
            if include_closed:
                # Normalize status using deadline: if deadline is past, mark as Closed
                try:
                    now = datetime.utcnow()
                    for r in processed_results:
                        if getattr(r, 'deadline', None) and isinstance(r.deadline, str) and r.deadline not in ('Not specified', ''):
                            try:
                                # Deadlines are typically Month DD, YYYY after formatting; support ISO as well
                                if ' ' in r.deadline and ',' in r.deadline:
                                    from datetime import datetime as _dt
                                    d = _dt.strptime(r.deadline, '%B %d, %Y')
                                else:
                                    from datetime import datetime as _dt
                                    d = _dt.fromisoformat(r.deadline.split('T')[0])
                                if d < now:
                                    r.status = 'Closed'
                            except Exception:
                                pass
                except Exception:
                    pass
            # Step 5: NO post-processing status filtering
            # Return ALL results from API - let API filtering handle status
            # User wants to see all calls without additional filtering

            # Step 6: Apply intelligent ranking
            ranked_results = self._apply_intelligent_ranking(processed_results, query, tag_boosts)
            
            # Step 7: NO relevance filtering - return ALL results from API
            # User wants to see all calls without any filtering
            relevant_results = ranked_results
            
            # Limit results
            final_results = relevant_results[:max_results]
            
            elapsed_time = time.time() - start_time
            
            # Generate filter explanation for no results or poor relevance matches
            filter_explanation = ""
            if parsed_filters and self.query_parser:
                if len(final_results) == 0:
                    # Check if we had results before relevance filtering
                    if len(processed_results) > 0:
                        filter_explanation = f"Found {len(processed_results)} {parsed_filters.filter_intention.replace('_', ' ')} calls, but none were relevant to '{search_query_text}'. Try broadening your search or removing the status filter."
                    else:
                        filter_explanation = self.query_parser.get_filter_explanation(parsed_filters, 0)
                elif len(final_results) < 3 and len(processed_results) > len(final_results) * 2:
                    # Many results were filtered out due to poor relevance
                    filter_explanation = f"Found {len(processed_results)} {parsed_filters.filter_intention.replace('_', ' ')} calls, but only {len(final_results)} were relevant to '{search_query_text}'"
            
            return {
                'results': final_results,
                'facets': facets,
                'search_metadata': {
                    'query': query,
                    'clean_query': search_query_text,
                    'total_found': len(search_results),
                    'returned': len(final_results),
                    'processing_time': round(elapsed_time, 3),
                    'semantic_tags_used': len(tag_boosts),
                    'facet_categories': len(facets),
                    'search_enhanced': True,
                    'filters_applied': parsed_filters.user_intent_detected if parsed_filters else [],
                    'filter_intention': parsed_filters.filter_intention if parsed_filters else 'all',
                    'filter_explanation': filter_explanation
                },
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced search failed: {e}")
            return {
                'results': [],
                'facets': {},
                'search_metadata': {
                    'query': query,
                    'error': str(e),
                    'processing_time': time.time() - start_time
                },
                'status': 'error'
            }
    
    def _get_semantic_tags(self, query: str) -> List[TagBoost]:
        """Get semantic tags using client-centricity.io API."""
        
        # Check cache first
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if cache_key in self._tag_cache:
            cached_data, timestamp = self._tag_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                logger.debug("📋 Using cached semantic tags")
                return cached_data
        
        try:
            headers = {
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json',
                'origin': 'https://ec.europa.eu',
                'referer': 'https://ec.europa.eu/',
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            }
            
            payload = {"query": query}
            
            response = requests.post(
                self.tags_api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok' and 'tags' in data:
                    tag_boosts = []
                    for tag in data['tags']:
                        tag_boost = TagBoost(
                            code=tag['code'],
                            boost=float(tag['boost'])
                        )
                        tag_boosts.append(tag_boost)
                    
                    # Cache the result
                    self._tag_cache[cache_key] = (tag_boosts, time.time())
                    
                    logger.info(f"🏷️ Retrieved {len(tag_boosts)} semantic tags from client-centricity.io")
                    return tag_boosts
            
            logger.warning(f"⚠️ Tag API returned status {response.status_code}")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to get semantic tags: {e}")
        
        return []
    
    def _simplify_query_for_api(self, clean_query: str, original_query: str) -> str:
        """
        Simplify complex natural language queries for better API results.
        
        Complex queries like 'What are some open calls about energy?' should become 'energy'
        to get maximum results from the API.
        """
        
        # Extract key topic words from the query
        import re
        
        # Common question words and phrases to remove
        question_words = [
            r'\bwhat\s+are\s+(some\s+)?',
            r'\bwhat\s+is\s+',
            r'\bhow\s+many\s+',
            r'\bcan\s+you\s+(find|show|tell)\s+me\s+',
            r'\bi\s+(want|need|am\s+looking\s+for)\s+',
            r'\bshow\s+me\s+',
            r'\bfind\s+me\s+',
            r'\btell\s+me\s+about\s+',
        ]
        
        # Remove question words
        simplified = clean_query.lower()
        for pattern in question_words:
            simplified = re.sub(pattern, '', simplified, flags=re.IGNORECASE)
        
        # Remove call-related words that are already handled by status filtering
        call_words = [
            r'\bopen\s+calls?\s+(about|for|on|related\s+to)\s+',
            r'\bcalls?\s+(about|for|on|related\s+to)\s+',
            r'\bfunding\s+(opportunities|calls?)\s+(about|for|on|related\s+to)\s+',
            r'\bfunding\s+(about|for|on|related\s+to)\s+',
            r'\bopportunities\s+(about|for|on|related\s+to)\s+',
        ]
        
        for pattern in call_words:
            simplified = re.sub(pattern, '', simplified, flags=re.IGNORECASE)
        
        # Extract core topic words (keep important domain terms)
        # Remove common words but keep domain-specific terms
        words_to_remove = [
            r'\bsome\b', r'\bany\b', r'\babout\b', r'\bfor\b', r'\bon\b', 
            r'\bin\b', r'\bof\b', r'\bthe\b', r'\ba\b', r'\ban\b',
            r'\brelated\s+to\b', r'\bconcerning\b', r'\bregarding\b'
        ]
        
        for pattern in words_to_remove:
            simplified = re.sub(pattern, ' ', simplified, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        simplified = re.sub(r'\s+', ' ', simplified).strip()
        
        # If we simplified too much, fall back to original clean query
        if len(simplified) < 2:
            simplified = clean_query
        
        logger.info(f"🔍 Query simplified: '{original_query}' → '{clean_query}' → '{simplified}'")
        return simplified
    
    def _build_advanced_query(
        self,
        query: str,
        tag_boosts: List[TagBoost],
        parsed_filters,  # QueryFilters object or None
        include_closed: bool = False  # Original boolean parameter
    ) -> Dict[str, Any]:
        """Build the advanced query structure matching EU portal approach with intelligent filtering."""
        
        # Base query structure
        base_query = {
            "bool": {
                "must": [
                    {
                        "bool": {
                            "must": [
                                # Document types: 1=Grant, 2=Other, 8=Additional
                                {"terms": {"type": ["1", "2", "8"]}}
                                # Removed programme period filter - it was blocking valid results
                                # Manual EU portal doesn't use this filter and finds 116+ results
                            ]
                        }
                    }
                ]
            }
        }
        
        # Domain-specific filters from parsed query
        domain_filters = []
        if parsed_filters and hasattr(parsed_filters, 'specific_filters') and parsed_filters.specific_filters:
            specific_filters = parsed_filters.specific_filters
            
            # Cluster 4 filter
            # Cluster filters: use programmeDivision where available; also bias text via identifier hint already injected
            for cnum, clabel in [("1", "Health"), ("2", "Culture, Creativity and Inclusive Society"), ("3", "Civil Security for Society"), ("4", "Digital, Industry and Space"), ("5", "Climate, Energy and Mobility"), ("6", "Food, Bioeconomy, Natural Resources, Agriculture and Environment")]:
                if specific_filters.get(f'cluster_{cnum}'):
                    domain_filters.append({"term": {"programmeDivision": clabel}})
                    logger.info(f"🎯 Applying Cluster {cnum} filter -> programmeDivision='{clabel}'")
            
            # TRL level filter (approximate based on call types)
            if specific_filters.get('trl'):
                # TRL 5-7 typically corresponds to Innovation Actions and some Research Actions
                domain_filters.append({"terms": {"typesOfAction": ["IA", "RIA"]}})
                logger.info("🎯 Applying TRL 5-7 filter (IA/RIA actions)")
            
            # Digital twins filter
            if specific_filters.get('digital_twins'):
                domain_filters.append({"term": {"keywords": "digital twin"}})
                logger.info("🎯 Applying digital twins filter")
            
            # EIC Accelerator filter
            if specific_filters.get('eic'):
                domain_filters.append({"term": {"frameworkProgramme": "EIC"}})
                logger.info("🎯 Applying EIC Accelerator filter")
            
            # Mission calls filter
            if specific_filters.get('mission_calls'):
                domain_filters.append({"term": {"mission": "true"}})
                logger.info("🎯 Applying mission calls filter")
            
            # Standardization filter
            if specific_filters.get('standardization'):
                domain_filters.append({"term": {"keywords": "standardization"}})
                logger.info("🎯 Applying standardization filter")
            
            # Living labs filter
            if specific_filters.get('living_labs'):
                domain_filters.append({"term": {"keywords": "living lab"}})
                logger.info("🎯 Applying living labs filter")
        
        # Add domain filters to base query
        if domain_filters:
            base_query["bool"]["must"][0]["bool"]["must"].extend(domain_filters)
        
        # Intelligent status filtering based on parsed query and include_closed parameter
        if parsed_filters and hasattr(parsed_filters, 'status_filter') and parsed_filters.status_filter:
            # Use specific status filter from parsed query (highest priority)
            status_codes = parsed_filters.status_filter
            logger.info(f"🎯 Applying intelligent status filter from parsed query: {status_codes}")
            base_query["bool"]["must"][0]["bool"]["must"].append(
                {"terms": {"status": status_codes}}
            )
        else:
            # Use include_closed parameter (fallback logic)
            if include_closed:
                # Include all statuses: closed, open, forthcoming
                logger.info("🎯 Including all call statuses (closed + open + forthcoming)")
                base_query["bool"]["must"][0]["bool"]["must"].append(
                    {"terms": {"status": ["31094501", "31094502", "31094503"]}}
                )
            else:
                # Only include open calls (match manual query exactly)
                logger.info("🎯 Including only open calls (31094502)")
                base_query["bool"]["must"][0]["bool"]["must"].append(
                    {"terms": {"status": ["31094502"]}}
                )
        
        # Add date filtering if specified
        if (parsed_filters and hasattr(parsed_filters, 'date_filter') and
            parsed_filters.date_filter):
            date_filter = parsed_filters.date_filter
            logger.info(f"📅 Applying date filter: {date_filter}")
            base_query["bool"]["must"][0]["bool"]["must"].append(
                {"range": {"deadlineDate": date_filter}}
            )
        
        # Build sophisticated text search with field-specific boosts
        text_search_should = []
        
        if query.strip():
            # High priority fields with exact phrase matching
            high_priority_fields = [
                {"field": "identifier", "phraseSlop": 0, "boost": 1100},
                {"field": "keywords", "phraseSlop": 0, "boost": 1000},
                {"field": "tags", "phraseSlop": 0, "boost": 950},
                {"field": "typesOfAction", "phraseSlop": 1, "boost": 900}
            ]
            
            # Medium priority fields
            medium_priority_fields = [
                {"field": "title", "phraseSlop": 1, "boost": 200},
                {"field": "callTitle", "phraseSlop": 1, "boost": 150},
                {"field": "projectAcronym", "phraseSlop": 1, "boost": 140},
                {"field": "projectName", "phraseSlop": 1, "boost": 130}
            ]
            
            # Lower priority fields
            low_priority_fields = [
                {"field": "description", "phraseSlop": 2, "boost": 100},
                {"field": "furtherInformation", "phraseSlop": 1, "boost": 90},
                {"field": "missionDescription", "phraseSlop": 1, "boost": 80},
                {"field": "missionDetails", "phraseSlop": 1, "boost": 75},
                {"field": "destinationDescription", "phraseSlop": 1, "boost": 70},
                {"field": "destinationDetails", "phraseSlop": 1, "boost": 65},
                {"field": "duration", "phraseSlop": 1, "boost": 60}
            ]
            
            # Build phrase queries for all fields
            all_fields = high_priority_fields + medium_priority_fields + low_priority_fields
            
            for field_config in all_fields:
                text_search_should.append({
                    "phrase": {
                        "query": query,
                        "field": field_config["field"],
                        "phraseSlop": field_config["phraseSlop"],
                        "boost": field_config["boost"]
                    }
                })
        
        # Add semantic tag boosts
        for tag_boost in tag_boosts:
            text_search_should.append({
                "term": {
                    "boost": tag_boost.boost,
                    "cenTagsA": tag_boost.code
                }
            })
        
        # Add the text search to the main query
        if text_search_should:
            base_query["bool"]["must"].append({
                "bool": {
                    "should": text_search_should
                }
            })
        
        logger.debug(f"🔧 Built advanced query with {len(text_search_should)} search clauses")
        return base_query
    
    def _get_facet_analysis(self, search_query: Dict[str, Any]) -> Dict[str, Any]:
        """Get facet analysis using the EU portal's facet API."""
        
        try:
            # Prepare multipart form data
            files = {
                "query": ("blob", json.dumps(search_query), "application/json"),
                "languages": ("blob", json.dumps(["en"]), "application/json"),
                "displayLanguage": ("blob", "en", "text/plain")
            }
            
            params = dict(self.default_params)
            params["text"] = "***"  # Wildcard for facet analysis
            
            response = requests.post(
                self.facet_api_url,
                params=params,
                files=files,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                facets_dict = {}
                
                if 'facets' in data:
                    for facet in data['facets']:
                        facet_name = facet.get('name', 'unknown')
                        facets_dict[facet_name] = {
                            'values': facet.get('values', []),
                            'count': facet.get('count', 0)
                        }
                
                logger.info(f"📊 Retrieved facet analysis with {len(facets_dict)} categories")
                return facets_dict
            
            logger.warning(f"⚠️ Facet API returned status {response.status_code}")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to get facet analysis: {e}")
        
        return {}
    
    def _execute_enhanced_search(self, search_query: Dict[str, Any], max_results: int) -> List[Dict[str, Any]]:
        """Execute the enhanced search with the built query."""
        
        try:
            # Prepare search parameters - maximize API results
            params = dict(self.default_params)
            params["pageSize"] = str(min(max_results * 2, 100))  # Get more results, increased from 50
            params["text"] = "***"  # Use wildcard since we have structured query
            
            # Prepare multipart form data
            sort_params = {"order": "DESC", "field": "relevance"}
            display_fields = [
                "type", "identifier", "reference", "callccm2Id", "title", "status", 
                "caName", "identifier", "projectAcronym", "startDate", "deadlineDate", 
                "deadlineModel", "frameworkProgramme", "typesOfAction"
            ]
            
            files = {
                "sort": ("blob", json.dumps(sort_params), "application/json"),
                "query": ("blob", json.dumps(search_query), "application/json"),
                "languages": ("blob", json.dumps(["en"]), "application/json"),
                "displayFields": ("blob", json.dumps(display_fields), "application/json")
            }
            
            response = requests.post(
                self.search_api_url,
                params=params,
                files=files,
                timeout=20
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                total_results = data.get("totalResults", 0)
                
                logger.info(f"🎯 Enhanced search returned {len(results)} results (total: {total_results})")
                return results
            
            logger.error(f"❌ Search API returned status {response.status_code}")
            
        except Exception as e:
            logger.error(f"❌ Enhanced search execution failed: {e}")
        
        return []
    
    def _process_enhanced_results(self, raw_results: List[Dict[str, Any]], query: str) -> List[EnhancedSearchResult]:
        """Process raw results into enhanced result objects."""
        
        processed = []
        current_date = datetime.now()
        
        for result in raw_results:
            try:
                metadata = result.get('metadata', {})
                
                # Extract core information
                identifier = self._get_metadata_value(metadata, 'identifier', 'N/A')
                title = result.get('content', '') or result.get('summary', '') or 'Unknown Call'
                title = re.sub(r'<[^>]+>', '', title).strip()  # Remove HTML tags
                
                # Status information
                status_raw = self._get_metadata_value(metadata, 'status')
                status_readable = self.status_mapping.get(str(status_raw), f"Unknown ({status_raw})")
                
                # Date information
                deadline_raw = self._get_metadata_value(metadata, 'deadlineDate')
                deadline_formatted = self._format_deadline(deadline_raw)
                
                # Programme information
                programme_period = self._get_metadata_value(metadata, 'programmePeriod', 'Not specified')
                framework_programme = self._get_metadata_value(metadata, 'frameworkProgramme', 'Horizon Europe')
                call_identifier = self._get_metadata_value(metadata, 'callIdentifier', 'Not specified')
                
                # Build enhanced description from multiple sources
                description = self._build_enhanced_description(result, metadata, query)
                
                # Build URL
                url = self._build_call_url(identifier, result.get('url'))
                
                # Calculate relevance score
                score = result.get('weight', 0.0)
                
                # Create enhanced result with proper null handling
                enhanced_result = EnhancedSearchResult(
                    identifier=identifier or 'N/A',
                    title=title or 'Unknown Call',
                    description=description or 'No description available',
                    status=status_readable or 'Unknown',
                    status_code=str(status_raw) if status_raw else 'unknown',
                    deadline=deadline_formatted or 'Not specified',
                    programme_period=programme_period or 'Not specified',
                    framework_programme=framework_programme or 'Horizon Europe',
                    call_identifier=call_identifier or 'Not specified',
                    url=url or 'https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home',
                    score=score or 0.0,
                    metadata=metadata or {}
                )
                
                processed.append(enhanced_result)
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to process result: {e}")
                continue
        
        logger.info(f"✅ Processed {len(processed)} enhanced results")
        return processed
    
    def _apply_intelligent_ranking(
        self,
        results: List[EnhancedSearchResult],
        query: str,
        tag_boosts: List[TagBoost]
    ) -> List[EnhancedSearchResult]:
        """Apply intelligent ranking based on multiple signals."""
        
        if len(results) <= 1:
            return results
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        for result in results:
            original_score = result.score
            
            # Exact query match in title (high boost)
            if query_lower in result.title.lower():
                result.score *= 1.5
                logger.debug(f"📍 Title match boost for {result.identifier}")
            
            # Exact query match in identifier
            if query_lower in result.identifier.lower():
                result.score *= 1.4
                logger.debug(f"🆔 Identifier match boost for {result.identifier}")
            
            # Status priority (open calls get higher scores)
            if result.status == 'Open':
                result.score *= 1.3
            elif result.status == 'Forthcoming':
                result.score *= 1.1
            
            # Recent calls get priority
            if 'recent' in query_lower or 'latest' in query_lower:
                try:
                    if '2024' in result.deadline or '2025' in result.deadline:
                        result.score *= 1.2
                except:
                    pass
            
            # Framework programme relevance
            if 'horizon' in query_lower and 'horizon' in result.framework_programme.lower():
                result.score *= 1.1
            
            # Keyword density in description
            desc_words = set(result.description.lower().split())
            keyword_overlap = len(query_words.intersection(desc_words))
            if keyword_overlap > 0:
                density_bonus = 1 + (keyword_overlap / len(query_words)) * 0.2
                result.score *= min(density_bonus, 1.5)  # Cap the bonus
            
            logger.debug(f"📊 Ranking: {result.identifier} score {original_score:.3f} -> {result.score:.3f}")
        
        # Sort by enhanced scores
        ranked = sorted(results, key=lambda x: x.score, reverse=True)
        
        logger.info(f"📈 Applied intelligent ranking to {len(results)} results")
        return ranked
    
    def _get_metadata_value(self, metadata: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Extract value from metadata arrays."""
        value = metadata.get(key)
        if isinstance(value, list) and value:
            return value[0]
        return value or default
    
    def _format_deadline(self, deadline_raw: str) -> str:
        """Format deadline for better readability."""
        if not deadline_raw or deadline_raw in ['Not specified', 'N/A']:
            return 'Not specified'
        
        try:
            if 'T' in deadline_raw:
                deadline_date = datetime.strptime(deadline_raw.split('T')[0], '%Y-%m-%d')
                formatted = deadline_date.strftime('%B %d, %Y')
                
                # Add urgency indicator
                days_until = (deadline_date - datetime.now()).days
                if days_until > 0:
                    if days_until <= 30:
                        return f"{formatted} ⚠️ **URGENT** ({days_until} days left!)"
                    elif days_until <= 60:
                        return f"{formatted} ⏰ **Soon** ({days_until} days left)"
                else:
                    return f"{formatted} ❌ **EXPIRED** ({abs(days_until)} days ago)"
                
                return formatted
        except:
            pass
        
        return str(deadline_raw)
    
    def _build_enhanced_description(self, result: Dict[str, Any], metadata: Dict[str, Any], query: str) -> str:
        """Build an enhanced, informative description from available data."""
        
        # Get the base title/content
        title = result.get('title', '') or result.get('content', '') or result.get('summary', '')
        title = re.sub(r'<[^>]+>', '', str(title)).strip()
        
        # Extract and enhance the action type
        action_type = self._get_metadata_value(metadata, 'typesOfAction', '')
        action_description = self._format_action_type(action_type)
        
        # Get call identifier for context
        identifier = self._get_metadata_value(metadata, 'identifier', '')
        context_info = self._extract_context_from_identifier(identifier)
        
        # Get programme info and make it more user-friendly
        programme = self._get_metadata_value(metadata, 'frameworkProgramme', 'Horizon Europe')
        programme_name = self._format_programme_name(programme)
        
        # Build enhanced description
        description_parts = []
        
        # Start with action type and context in a natural sentence
        if action_description and context_info:
            description_parts.append(f"{action_description} targeting {context_info}")
        elif action_description:
            description_parts.append(action_description)
        elif context_info:
            description_parts.append(f"Research funding opportunity in {context_info}")
        else:
            description_parts.append("Research funding opportunity")
        
        # Add programme context if meaningful
        if programme_name and programme_name != 'Horizon Europe':
            description_parts.append(f" within the {programme_name}")
        
        # Add specific objectives or goals if we can extract them from title
        objective = self._extract_objective_from_title(title)
        if objective and objective != title:
            description_parts.append(f". {objective}")
        
        final_description = "".join(description_parts)
        
        # Ensure minimum length and quality
        if len(final_description) < 50:
            if title:
                final_description = f"{action_description or 'Funding opportunity'}: {title}"
            else:
                final_description = "Research funding opportunity in the specified research area"
        
        return final_description
    
    def _format_action_type(self, action_type: str) -> str:
        """Format action type into user-friendly description."""
        
        if not action_type:
            return "Research funding opportunity"
            
        action_type_clean = str(action_type).strip()
        
        # Handle common EU action types
        action_mappings = {
            'RIA': 'Research and Innovation Action',
            'CSA': 'Coordination and Support Action',
            'IA': 'Innovation Action',
            'MSCA-PF': 'Marie Skłodowska-Curie Postdoctoral Fellowship',
            'MSCA-DN': 'Marie Skłodowska-Curie Doctoral Network',
            'ERC-STG': 'ERC Starting Grant',
            'ERC-COG': 'ERC Consolidator Grant',
            'ERC-ADG': 'ERC Advanced Grant',
            'ERC-SyG': 'ERC Synergy Grant',
            'EIC-2021-ACCELERATORMIXED': 'EIC Accelerator',
            'EIC-2021-PATHFINDERCHALLENGES': 'EIC Pathfinder Challenges',
            'EIC-2021-PATHFINDEROPEN': 'EIC Pathfinder Open'
        }
        
        # Check for exact matches first
        if action_type_clean in action_mappings:
            return action_mappings[action_type_clean]
        
        # Check for partial matches in longer strings
        for code, description in action_mappings.items():
            if code in action_type_clean:
                return description
        
        # Handle compound action types (like "DIGITAL JU Coordination and Support Actions")
        if 'coordination and support' in action_type_clean.lower():
            return 'Coordination and Support Action'
        elif 'research and innovation' in action_type_clean.lower():
            return 'Research and Innovation Action'
        elif 'innovation action' in action_type_clean.lower():
            return 'Innovation Action'
        elif 'simple grant' in action_type_clean.lower():
            return 'Research Grant'
        elif 'cascading grant' in action_type_clean.lower():
            return 'Cascading Grant'
        
        # If no match found, use the original but clean it up
        clean_type = action_type_clean.replace('_', ' ').title()
        return f"{clean_type} opportunity"
    
    def _extract_context_from_identifier(self, identifier: str) -> str:
        """Extract research context from call identifier."""
        
        if not identifier:
            return ""
            
        identifier = str(identifier).upper()
        
        # Map cluster codes to research areas
        cluster_mappings = {
            'CL1': 'Health research',
            'CL2': 'Culture, creativity and inclusive society',
            'CL3': 'Civil security for society',
            'CL4': 'Digital, industry and space',
            'CL5': 'Climate, energy and mobility',
            'CL6': 'Food, bioeconomy, natural resources, agriculture and environment',
            'EIC': 'Innovation and emerging technologies',
            'ERC': 'Frontier research',
            'MSCA': 'Researcher mobility and training',
            'WIDERA': 'Widening participation and strengthening research capacity',
            'DIGITAL': 'Digital transformation and technologies',
            'EUROHPC': 'High-performance computing',
            'EURATOM': 'Nuclear research and training'
        }
        
        # Look for cluster indicators in identifier
        for cluster_code, description in cluster_mappings.items():
            if cluster_code in identifier:
                return description
                
        # Extract specific topic areas from identifier patterns
        if 'QUANTUM' in identifier or 'QCI' in identifier:
            return 'quantum technologies and computing'
        elif 'AI' in identifier or 'ARTIFICIAL' in identifier:
            return 'artificial intelligence'
        elif 'CYBER' in identifier or 'SECURITY' in identifier:
            return 'cybersecurity'
        elif 'DATA' in identifier:
            return 'data technologies'
        elif 'SPACE' in identifier:
            return 'space research'
        elif 'CLIMATE' in identifier:
            return 'climate action'
        elif 'ENERGY' in identifier:
            return 'energy research'
        elif 'HEALTH' in identifier:
            return 'health and medical research'
        elif 'DIGITAL' in identifier:
            return 'digital transformation'
        
        # Default fallback
        return "research and innovation"
    
    def _format_programme_name(self, programme: str) -> str:
        """Format programme name for better readability."""
        
        if not programme:
            return ""
            
        programme = str(programme).strip()
        
        # Handle numeric programme codes
        if programme.isdigit():
            # These are internal programme codes, not very useful for users
            return ""
        
        # Clean up common programme names
        programme_mappings = {
            'Horizon Europe': 'Horizon Europe',
            'HORIZON EUROPE': 'Horizon Europe',
            'Digital Europe Programme': 'Digital Europe Programme',
            'DIGITAL EUROPE': 'Digital Europe Programme',
            'EIC': 'European Innovation Council',
            'ERC': 'European Research Council',
            'MSCA': 'Marie Skłodowska-Curie Actions',
            'EURATOM': 'Euratom Research and Training Programme'
        }
        
        for key, value in programme_mappings.items():
            if key in programme.upper():
                return value
        
        # If it's already readable, return as is
        if len(programme) > 10 and ' ' in programme:
            return programme
            
        return ""
    
    def _extract_objective_from_title(self, title: str) -> str:
        """Extract key objectives or focus from the title."""
        
        if not title or len(title) < 20:
            return ""
        
        # Look for action words that indicate objectives
        objective_patterns = [
            r'supporting?\s+(.+?)(?:\s+\(|$)',
            r'development\s+of\s+(.+?)(?:\s+\(|$)',
            r'advancing?\s+(.+?)(?:\s+\(|$)',
            r'promoting?\s+(.+?)(?:\s+\(|$)',
            r'establishing?\s+(.+?)(?:\s+\(|$)',
            r'creating?\s+(.+?)(?:\s+\(|$)',
            r'building?\s+(.+?)(?:\s+\(|$)'
        ]
        
        title_lower = title.lower()
        for pattern in objective_patterns:
            match = re.search(pattern, title_lower)
            if match:
                objective = match.group(1).strip()
                if len(objective) > 5 and len(objective) < 100:
                    return f"Aims to advance {objective}"
        
        # Look for "for" statements that indicate purpose
        for_match = re.search(r'\sfor\s+(.+?)(?:\s+\(|$)', title_lower)
        if for_match:
            purpose = for_match.group(1).strip()
            if len(purpose) > 5 and len(purpose) < 80:
                return f"Focuses on {purpose}"
        
        return ""
    
    def _filter_by_relevance(
        self,
        results: List[EnhancedSearchResult],
        query: str,
        filters: Optional[object] = None
    ) -> List[EnhancedSearchResult]:
        """Filter results by relevance to avoid returning irrelevant results when using status filters."""
        
        if not results or not query:
            return results
        
        query_lower = query.lower().strip()
        query_words = set(query_lower.split())
        
        # Define core search terms (remove common words but keep important context words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'are', 'what', 'some', 'related', 'about'}
        # Keep important words like "open", "calls", "funding", "opportunities" as they provide context
        important_context_words = {'open', 'closed', 'calls', 'funding', 'opportunities', 'grants', 'proposals'}
        
        # Remove stop words but preserve important context
        core_terms = (query_words - stop_words) | (query_words & important_context_words)
        
        if not core_terms:
            return results
        
        relevant_results = []
        relevance_threshold = 0.01  # MUCH lower minimum relevance score (was 0.05)
        
        for result in results:
            relevance_score = self._calculate_relevance_score(result, core_terms, query_lower)
            
            # For filtered searches, be very lenient - user is already filtering
            min_threshold = relevance_threshold
            if filters and hasattr(filters, 'status_filter') and filters.status_filter:
                # Very low threshold for filtered searches - user wants to see results!
                min_threshold = 0.02
            
            if relevance_score >= min_threshold:
                # Store relevance score for potential use (ensure metadata exists)
                if result.metadata is None:
                    result.metadata = {}
                result.metadata['relevance_score'] = relevance_score
                relevant_results.append(result)
        
        # If we filtered out too many results and have very few left, and this is a filtered search,
        # log the issue but still return what we have (much more lenient threshold)
        if len(relevant_results) < len(results) * 0.1 and len(relevant_results) < 1:
            logger.warning(f"⚠️ Relevance filtering removed {len(results) - len(relevant_results)} results. Query: '{query}', Remaining: {len(relevant_results)}")
        
        logger.info(f"🎯 Relevance filtering: {len(results)} -> {len(relevant_results)} results")
        return relevant_results
    
    def _calculate_relevance_score(self, result: EnhancedSearchResult, core_terms: set, query_lower: str) -> float:
        """Calculate relevance score for a search result."""
        
        # Combine all searchable text
        searchable_fields = [
            result.title,
            result.description,
            result.identifier,
            result.framework_programme
        ]
        
        combined_text = ' '.join(str(field) for field in searchable_fields if field).lower()
        combined_words = set(combined_text.split())
        
        # Calculate term overlap
        term_overlap = len(core_terms.intersection(combined_words))
        term_coverage = term_overlap / len(core_terms) if core_terms else 0
        
        # Check for phrase matches
        phrase_matches = 0
        if query_lower in combined_text:
            phrase_matches = 1
        
        # Check for partial phrase matches (2+ consecutive words)
        query_words = query_lower.split()
        if len(query_words) >= 2:
            for i in range(len(query_words) - 1):
                phrase = ' '.join(query_words[i:i+2])
                if phrase in combined_text:
                    phrase_matches += 0.5
        
        # Check for domain-specific relevance
        domain_bonus = self._get_domain_relevance_bonus(result, core_terms)
        
        # Calculate final score
        relevance_score = (
            term_coverage * 0.4 +           # Term coverage is most important
            phrase_matches * 0.3 +          # Phrase matches are valuable
            domain_bonus * 0.2 +            # Domain relevance helps
            min(term_overlap / 10, 0.1)     # Raw term count (capped)
        )
        
        return relevance_score
    
    def _get_domain_relevance_bonus(self, result: EnhancedSearchResult, core_terms: set) -> float:
        """Get domain relevance bonus based on identifier and programme context."""
        
        identifier = result.identifier.upper()
        programme = result.framework_programme.upper() if result.framework_programme else ""
        
        # Domain mappings for better relevance
        domain_mappings = {
            'nuclear': ['EURATOM', 'NUCLEAR', 'FUSION', 'FISSION'],
            'quantum': ['QUANTUM', 'QCI', 'IRIS'],
            'digital': ['DIGITAL', 'CL4', 'ICT'],
            'health': ['HEALTH', 'CL1', 'MEDICAL'],
            'climate': ['CLIMATE', 'CL5', 'ENERGY', 'GREEN'],
            'space': ['SPACE', 'COPERNICUS', 'GALILEO'],
            'ai': ['AI', 'ARTIFICIAL', 'MACHINE'],
            'cyber': ['CYBER', 'SECURITY', 'DEFENCE']
        }
        
        bonus = 0.0
        for term in core_terms:
            if term in domain_mappings:
                keywords = domain_mappings[term]
                if any(keyword in identifier or keyword in programme for keyword in keywords):
                    bonus += 0.5
                    break
            else:
                # Check if the core term appears in identifier or programme
                if term.upper() in identifier or term.upper() in programme:
                    bonus += 0.3
        
        return min(bonus, 1.0)  # Cap the bonus

    def _build_call_url(self, identifier: str, raw_url: Optional[str] = None) -> str:
        """Build proper EU portal URL for the call."""
        
        # Treat /data/topicDetails and JSON links as invalid for end users
        if raw_url and (raw_url.endswith('.json') or '/data/topicDetails/' in raw_url):
            raw_url = None
        
        # If a valid non-data URL exists already, keep it, except topic-search (prefer topic-details)
        if raw_url:
            if 'topic-search' in raw_url:
                raw_url = None
            else:
                return raw_url
        
        # Build proper topic details URL with identifier
        if identifier and identifier != 'N/A':
            return (
                f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
                f"screen/opportunities/topic-details/{identifier}?keywords={identifier}"
            )
        
        # Fallback to general portal
        return "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/opportunities-tenders"

    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """Get search suggestions based on partial query."""
        
        suggestions = []
        
        # Domain-specific suggestions
        domain_suggestions = {
            'quantum': ['quantum mechanics', 'quantum computing', 'quantum technologies', 'quantum communication'],
            'ai': ['artificial intelligence', 'machine learning', 'deep learning', 'neural networks'],
            'energy': ['renewable energy', 'clean energy', 'energy efficiency', 'sustainable energy'],
            'health': ['healthcare', 'medical research', 'digital health', 'personalized medicine'],
            'climate': ['climate change', 'green deal', 'carbon neutral', 'sustainability']
        }
        
        partial_lower = partial_query.lower()
        
        for domain, terms in domain_suggestions.items():
            if domain in partial_lower:
                suggestions.extend([term for term in terms if term not in suggestions])
            elif any(term.startswith(partial_lower) for term in terms):
                suggestions.extend([term for term in terms if term.startswith(partial_lower)])
        
        return suggestions[:10]

# Example usage and testing
if __name__ == "__main__":
    def test_enhanced_search():
        """Test the enhanced search functionality."""
        print("🧪 Testing Enhanced Call Search Service")
        print("=" * 60)
        
        service = EnhancedCallSearchService()
        
        test_queries = [
            "quantum mechanics",
            "artificial intelligence healthcare",
            "renewable energy",
            "digital transformation"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing: '{query}'")
            print("-" * 40)
            
            start_time = time.time()
            result = service.search_calls_enhanced(
                query=query,
                max_results=5,
                enable_facet_analysis=True
            )
            elapsed = time.time() - start_time
            
            if result['status'] == 'success':
                print(f"✅ Found {len(result['results'])} results in {elapsed:.2f}s")
                print(f"📊 Facet categories: {len(result['facets'])}")
                print(f"🏷️ Semantic tags: {result['search_metadata']['semantic_tags_used']}")
                
                # Show top result
                if result['results']:
                    top_result = result['results'][0]
                    print(f"🥇 Top result: {top_result.title}")
                    print(f"   Status: {top_result.status}")
                    print(f"   Score: {top_result.score:.3f}")
            else:
                print(f"❌ Search failed: {result.get('search_metadata', {}).get('error', 'Unknown error')}")
        
        print("\n🎉 Enhanced search testing completed!")

    if __name__ == "__main__":
        test_enhanced_search()