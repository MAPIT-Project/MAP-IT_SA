import os
import requests
import re
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    OPENAI_AVAILABLE = False

try:
    from google import genai as google_genai_sdk
    from google.genai import types
    GEMINI_AVAILABLE = True
except Exception:
    google_genai_sdk = None
    types = None
    GEMINI_AVAILABLE = False
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2
from psycopg2.extras import DictCursor
import psycopg2.pool
from urllib.parse import urlparse
from collections import defaultdict
import hashlib
from decimal import Decimal
import asyncio
from dataclasses import asdict

# Load environment variables
load_dotenv()

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

class CordisRAG:
    """
    Retrieval-Augmented Generation system for European research projects using CORDIS database.
    V9: Enhanced with intelligent intent routing to search for projects OR open calls for proposals.
    This addresses the requirement to expand beyond searching existing projects to include funding opportunities.
    """
    def __init__(self, openai_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None,
                 ai_provider: str = "gemini",
                 openai_model_name: str = "gpt-4-turbo",
                 gemini_model_name: str = "gemini-flash-lite-latest",
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
                # Increased pool size for better concurrent processing support
                min_connections = int(os.getenv("DB_MIN_CONNECTIONS", "5"))
                max_connections = int(os.getenv("DB_MAX_CONNECTIONS", "50"))
                self.db_pool = psycopg2.pool.SimpleConnectionPool(
                    min_connections, max_connections,  # Support more concurrent connections
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
        self._call_cache = {}  # Cache for call search results
        self._cache_ttl = 3600  # Cache TTL in seconds (1 hour)
        self._max_cache_size = 1000  # Maximum cache entries to prevent memory issues
        
        # Query preprocessing utilities
        self._domain_keywords = self._load_domain_keywords()
        self._stopwords = {'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
                          'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
                          'to', 'was', 'will', 'with', 'the'}
        
        # Call-specific functionality is now integrated into EnhancedRAGService
        self.call_specific_rag = None
        print("ℹ️ Call-specific functionality integrated into EnhancedRAGService")
        
        if self.ai_provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ValueError("OpenAI package not installed. Install with: pip install openai")
            used_openai_api_key = openai_api_key if openai_api_key else os.getenv("OPENAI_API_KEY")
            if not used_openai_api_key:
                raise ValueError("OpenAI API key not provided and not found in .env file.")
            self.openai_client = openai.OpenAI(api_key=used_openai_api_key)
        elif self.ai_provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ValueError("Google Gemini package not installed. Install with: pip install google-genai")
            used_gemini_api_key = gemini_api_key if gemini_api_key else os.getenv("GEMINI_API_KEY")
            if not used_gemini_api_key:
                raise ValueError("Gemini API key not provided and not found in .env file.")
            self.gemini_client = google_genai_sdk.Client(api_key=used_gemini_api_key)
        else:
            raise ValueError("Invalid AI provider specified. Choose 'openai' or 'gemini'.")


    def search_for_calls(self, question: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Search for Horizon Europe calls and topics, using appropriate data sources.
        Enhanced to use call-specific RAG for detailed call/topic queries.
        """
        print(f"📞 V9: Searching for calls/topics related to: '{question}'")
        
        # Check cache first
        cache_key = f"calls_{hashlib.md5(f'{question}_{max_results}'.encode()).hexdigest()}"
        cached_result = self._get_from_cache(self._call_cache, cache_key)
        if cached_result is not None:
            print(f"Using cached call search results")
            return cached_result

        try:
            # First, check if this is ANY call/topic query that should use the call-specific RAG
            if self.call_specific_rag:
                intent_type, call_identifier, confidence = self.call_specific_rag.detect_call_specific_intent(question)
                
                # Only use call-specific RAG for very specific call/topic queries.
                # For GENERAL or broad call queries we prefer the EU Funding & Tenders Portal API.
                if intent_type in ["SPECIFIC_CALL", "SPECIFIC_TOPIC", "CLUSTER_SPECIFIC"]:
                    print(f"🎯 Using call-specific RAG for {intent_type}: {call_identifier}")
                    
                    # Handle with call-specific RAG (enhanced search will be used automatically)
                    result = self.call_specific_rag.handle_call_specific_query(
                        question=question,
                        call_identifier=call_identifier,
                        max_context_chunks=max_results
                    )
                    
                    # If the call-specific RAG found useful documentation, return it.
                    if result.get('success'):
                        data_source = 'EU Funding & Tenders Portal (Enhanced)'
                        return {
                            'answer': result.get('answer', ''),
                            'call_count': result.get('chunks_used', 0),
                            'search_successful': True,
                            'queries_used': [question],
                            'calls_data': result.get('calls_data', []),
                            'data_source': data_source,
                            'confidence': result.get('confidence', 0.0)
                        }
                    else:
                        # If call-specific RAG failed to find call docs, log and fall through to API search
                        print("🔄 Call-specific RAG did not return results; falling back to EU Portal API")
                else:
                    # For GENERAL_CALL or other non-specific intents, prefer the EU Portal API
                    print(f"🔁 Call-specific RAG skipped for intent: {intent_type}; using EU Portal API")

            # Fall back to CORDIS API for general call searches
            print("📞 Falling back to CORDIS API for general call search")
            
            # Phase 1: Extract keywords from the question using existing logic with fallback
            try:
                role, quest = self._get_phase1_prompt(question)
                queries, end_flag, _, _, problem_text, _ = self._extract_queries(role, quest)

                if end_flag:
                    print(f"⚠️ LLM query extraction had issues: {problem_text}")
                    print("🔄 Using fallback query extraction...")
                    queries = self._extract_queries_fallback(question)
                
                if not queries:
                    print("⚠️ LLM returned no queries, using fallback...")
                    queries = self._extract_queries_fallback(question)
                    
            except Exception as llm_error:
                print(f"⚠️ LLM query extraction failed: {llm_error}")
                print("🔄 Using fallback query extraction...")
                queries = self._extract_queries_fallback(question)

            if not queries:
                queries = [question.strip()]  # Final fallback to using the whole question

            print(f"🔍 Extracted queries for call search: {queries}")

            # Search for calls using CORDIS API - pass original question for better demo fallback
            calls_found = self._search_cordis_calls_api(queries, max_results, original_question=question)
            
            if not calls_found:
                return {
                    'answer': self._generate_no_calls_portal_fallback(question),
                    'call_count': 0,
                    'search_successful': True,
                    'queries_used': queries
                }

            # Generate comprehensive answer about the calls
            answer = self._generate_calls_answer(question, calls_found)
            
            result = {
                'answer': answer,
                'call_count': len(calls_found),
                'search_successful': True,
                'queries_used': queries,
                'calls_data': calls_found,
                'data_source': 'CORDIS Topics/Calls API'
            }
            
            # Cache the result
            self._set_cache(self._call_cache, cache_key, result)
            
            return result

        except Exception as e:
            print(f"❌ Error searching for calls: {e}")
            return {
                'answer': f"I encountered an error while searching for open calls: {str(e)}. Please try rephrasing your question or try again later.",
                'call_count': 0,
                'search_successful': False,
                'error': str(e)
            }

    def _extract_queries_fallback(self, question: str) -> List[str]:
        """
        Fallback query extraction when LLM is not available
        """
        import re
        
        # Clean up the question
        cleaned_question = question.lower().strip()
        
        # Extract key terms related to energy and sustainability
        energy_terms = [
            "clean energy", "renewable energy", "sustainable energy", "green energy",
            "solar energy", "wind energy", "energy efficiency", "energy storage",
            "energy transition", "decarbonization", "carbon neutral",
            "hydrogen", "biomass", "geothermal", "hydropower", "photovoltaic",
            "battery", "grid", "smart grid", "energy systems", "climate",
            "environment", "sustainability", "innovation", "technology"
        ]
        
        # Find matching terms in the question
        found_terms = []
        for term in energy_terms:
            if term in cleaned_question:
                found_terms.append(term)
        
        # If no specific energy terms found, use general terms based on keywords
        if not found_terms:
            # Look for general funding/research terms
            if any(word in cleaned_question for word in ["research", "innovation", "technology", "development"]):
                found_terms = ["clean energy", "sustainable technology"]
            elif any(word in cleaned_question for word in ["call", "funding", "proposal", "grant"]):
                found_terms = ["clean energy"]  # Default for funding questions
            else:
                found_terms = ["clean energy"]  # Default fallback
        
        # Remove duplicates and limit to top 5
        unique_terms = list(dict.fromkeys(found_terms))[:5]
        
        print(f"🔄 Fallback extraction found terms: {unique_terms}")
        return unique_terms

    def _search_cordis_calls_api(self, queries: List[str], max_results: int, original_question: str = "") -> List[Dict[str, Any]]:
        """
        Search EU Funding & Tenders Portal API specifically for open calls/topics.
        Uses advanced JSON query structure with boolean operators and proper filtering.
        """
        api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
        
        # Build search terms from queries - FILTER OUT PROJECT-SPECIFIC DATE FILTERS
        search_terms = []
        for query in queries:
            query_stripped = query.strip()
            if not query_stripped:
                continue
            
            # CRITICAL FIX: Filter out project-specific date filters that don't work for calls
            # Projects have startDate/endDate, but calls have deadline dates with different API structure
            if any(filter_type in query_stripped.lower() for filter_type in ['startdate>', 'enddate>', 'totalcost']):
                print(f"🚫 Skipping project-specific filter for call search: {query_stripped}")
                continue
                
            # Handle OR conditions in queries
            if " OR " in query_stripped.upper():
                or_terms = [term.strip() for term in re.split(r'\s+OR\s+', query_stripped, flags=re.IGNORECASE)]
                search_terms.extend([term for term in or_terms if term.strip()])
            else:
                search_terms.append(query_stripped)
        
        # If no valid search terms remain after filtering, extract from original question
        if not search_terms:
            print(f"🔄 No valid search terms after filtering, extracting from original question: {original_question}")
            # Extract key terms from the original question
            question_words = original_question.lower().replace("what are some open calls for", "").replace("?", "").strip()
            if question_words:
                search_terms = [question_words]
            else:
                search_terms = ["Horizon Europe"]
        
        # Combine search terms into a single search string
        search_text = " ".join(search_terms[:5]) if search_terms else "Horizon Europe"
        
        print(f"🔍 Searching EU Portal for: '{search_text}'")
        
        # Log the verification URL for manual checking
        verification_url = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;freeTextSearchKeyword={search_text.replace(' ', '%20')};sortQuery=sortStatus;orderBy=asc"
        print(f"🔗 Manual verification URL: {verification_url}")
        
        try:
            start_time = time.time()
            
            # First, try the advanced JSON query approach
            calls_found = self._search_with_advanced_json_query(api_url, search_text, max_results)
            
            # If advanced query fails or returns no results, fallback to basic search
            if not calls_found:
                print("⚠️ Advanced query returned no results, trying basic search...")
                calls_found = self._search_with_basic_params(api_url, search_text, max_results)
            
            elapsed = time.time() - start_time
            print(f"📞 EU Portal API completed in {elapsed:.2f}s, found {len(calls_found)} relevant calls")
            
            # Save API response to JSON file for debugging
            self._save_debug_response(calls_found, search_text)
            
            return calls_found
            
        except Exception as e:
            print(f"⚠️ EU Funding & Tenders Portal API error: {e}")
            print("❌ No demonstration data fallback - returning empty results")
            return []

    def _search_with_advanced_json_query(self, api_url: str, search_text: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Use advanced JSON query that matches the working EU portal structure exactly.
        This implementation matches the structure from the successful curl request.
        """
        # URL parameters - match the working curl request exactly
        params = {
            "apiKey": "SEDIA",
            "text": search_text,
            "pageSize": str(min(max_results * 2, 50)),  # Get enough results
            "pageNumber": "1",
        }
        
        # Build query structure that exactly matches the working curl request
        query = {
            "bool": {
                "must": [
                    {
                        "bool": {
                            "must": [
                                # CRITICAL FIX: Include type "8" - this was missing!
                                {"terms": {"type": ["1", "2", "8"]}},
                                # CRITICAL FIX: Status must be required, not optional
                                {"terms": {"status": ["31094502"]}},  # Open calls only
                                {"term": {"programmePeriod": "2021 - 2027"}}
                            ]
                        }
                    }
                ]
            }
        }
        
        # Add sophisticated text search structure that matches the working request
        if search_text.strip():
            text_search_should = [
                # High boost for exact matches in key fields
                {"phrase": {"query": search_text, "field": "identifier", "phraseSlop": 0, "boost": 1100}},
                {"phrase": {"query": search_text, "field": "keywords", "phraseSlop": 0, "boost": 1000}},
                {"phrase": {"query": search_text, "field": "tags", "phraseSlop": 0, "boost": 950}},
                {"phrase": {"query": search_text, "field": "typesOfAction", "phraseSlop": 1, "boost": 900}},
                
                # Medium boost for title and call information
                {"phrase": {"query": search_text, "field": "title", "phraseSlop": 1, "boost": 200}},
                {"phrase": {"query": search_text, "field": "callTitle", "phraseSlop": 1, "boost": 150}},
                {"phrase": {"query": search_text, "field": "projectAcronym", "phraseSlop": 1, "boost": 140}},
                {"phrase": {"query": search_text, "field": "projectName", "phraseSlop": 1, "boost": 130}},
                
                # Lower boost for description fields
                {"phrase": {"query": search_text, "field": "description", "phraseSlop": 2, "boost": 100}},
                {"phrase": {"query": search_text, "field": "furtherInformation", "phraseSlop": 1, "boost": 90}},
                {"phrase": {"query": search_text, "field": "missionDescription", "phraseSlop": 1, "boost": 80}},
                {"phrase": {"query": search_text, "field": "missionDetails", "phraseSlop": 1, "boost": 75}},
                {"phrase": {"query": search_text, "field": "destinationDescription", "phraseSlop": 1, "boost": 70}},
                {"phrase": {"query": search_text, "field": "destinationDetails", "phraseSlop": 1, "boost": 65}},
                {"phrase": {"query": search_text, "field": "duration", "phraseSlop": 1, "boost": 60}}
            ]
            
            # Add some relevant boost terms for virtual reality / technology searches
            # boost_terms = [
            #     {"term": {"boost": 45, "cenTagsA": "TCM_00018093"}},
            #     {"term": {"boost": 4.9798017, "cenTagsA": "TTG_00134801"}},
            #     {"term": {"boost": 4.651707, "cenTagsA": "TTG_00056821"}},
            #     {"term": {"boost": 4.2821107, "cenTagsA": "TTG_00114649"}},
            #     {"term": {"boost": 4.1363397, "cenTagsA": "TTG_00056836"}},
            #     {"term": {"boost": 4.0872984, "cenTagsA": "TTG_00048552"}},
            #     {"term": {"boost": 3.4304051, "cenTagsA": "TTG_00136923"}},
            #     {"term": {"boost": 3.3573449, "cenTagsA": "TTG_00118987"}},
            #     {"term": {"boost": 3.338732, "cenTagsA": "TCM_00019020"}},
            #     {"term": {"boost": 3.338732, "cenTagsA": "TTG_00027115"}}
            # ]
            
            # text_search_should.extend(boost_terms)
            
            # Add the text search as a second bool condition
            query["bool"]["must"].append({
                "bool": {
                    "should": text_search_should
                }
            })
        
        # Use exact sort and display fields from the working request
        languages = ["en"]
        sort_params = {"order": "DESC", "field": "relevance"}  # FIXED: Use relevance sort
        
        # Add display fields that match the working request
        display_fields = [
            "type", "identifier", "reference", "callccm2Id", "title", "status", 
            "caName", "identifier", "projectAcronym", "startDate", "deadlineDate", 
            "deadlineModel", "frameworkProgramme", "typesOfAction"
        ]
        
        print("🔥 Using EXACT working EU portal query structure...")
        print(f"📡 Advanced API Request Details:")
        print(f"   URL: {api_url}")
        print(f"   Params: {params}")
        print(f"   Query (truncated): bool.must[0].bool.must = types[1,2,8], status[31094502], period[2021-2027]")
        
        try:
            import httpx
            with httpx.Client(timeout=httpx.Timeout(15.0)) as client:
                response = client.post(
                api_url,
                params=params,
                files={
                    "sort": ("blob", json.dumps(sort_params), "application/json"),
                    "query": ("blob", json.dumps(query), "application/json"),
                    "languages": ("blob", json.dumps(languages), "application/json"),
                    "displayFields": ("blob", json.dumps(display_fields), "application/json"),
                },
            )
            response.raise_for_status()
            data = response.json()
            print(f"🎯 Fixed query returned {data.get('totalResults', 0)} total results")
            return self._process_api_results(data, max_results, "advanced_fixed")
        except Exception as e:
            print(f"⚠️ Fixed advanced query failed: {e}")
            return []

    def _search_with_basic_params(self, api_url: str, search_text: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Fallback to basic parameter search with better result processing
        """
        search_params = {
            "apiKey": "SEDIA",
            "index": "opportunities", 
            "pageSize": str(min(max_results * 2, 50)),  # Get more results to filter through
            "pageNumber": "1",
            "text": search_text,
            "language": "en",
        }
        
        print("🔧 Using basic parameter search as fallback...")
        print(f"📡 Fallback API Request Details:")
        print(f"   URL: {api_url}")
        print(f"   Data: {search_params}")
        
        try:
            import httpx
            with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
                response = client.post(api_url, data=search_params)
            response.raise_for_status()
            data = response.json()
            return self._process_api_results(data, max_results, "basic")
        except Exception as e:
            print(f"⚠️ Basic search also failed: {e}")
            return []

    def _process_api_results(self, data: Dict[str, Any], max_results: int, query_type: str) -> List[Dict[str, Any]]:
        """
        Process API results with practical filtering (less restrictive since most EU calls are historical)
        """
        results = data.get("results", [])
        total_results = data.get("totalResults", 0)
        
        print(f"📊 {query_type.title()} query returned {len(results)} results (total: {total_results})")
        
        calls_found = []
        seen_identifiers = set()
        current_date = datetime.now()
        
        # Categorize results for better selection
        open_calls = []
        forthcoming_calls = []
        recent_closed_calls = []
        
        for result in results:
            call_data = self._extract_eu_portal_call_data(result)
            if not call_data:
                print("⚠️ Skipping result - no call data extracted")
                continue
                
            # Check for duplicates
            identifier = call_data.get('identifier', 'N/A')
            if identifier in seen_identifiers:
                print(f"🔄 Skipping duplicate: {identifier}")
                continue
            seen_identifiers.add(identifier)
            
            # Extract status information
            metadata = result.get('metadata', {})
            status_raw = metadata.get('status', [None])[0] if isinstance(metadata.get('status'), list) else None
            status_readable = self._decode_call_status(status_raw)
            
            # Check if programme period is relevant (current Horizon Europe) - be less restrictive
            programme_period = metadata.get('programmePeriod', [''])[0] if isinstance(metadata.get('programmePeriod'), list) else ''
            # Only skip if we're sure it's from an old programme (be permissive about empty/unknown periods)
            if programme_period and '2014' in programme_period and '2020' in programme_period:
                continue  # Skip definitely old programmes (2014-2020)
            
            # Parse deadline for date-based filtering
            deadline_raw = metadata.get('deadlineDate', [None])[0] if isinstance(metadata.get('deadlineDate'), list) else None
            deadline_date = None
            is_recent = False
            
            if deadline_raw:
                try:
                    deadline_date = datetime.strptime(deadline_raw.split('T')[0], '%Y-%m-%d')
                    days_ago = (current_date - deadline_date).days
                    
                    # Strict filtering - prioritize truly current calls, avoid old examples unless no current calls exist
                    if deadline_date > current_date:
                        is_recent = True  # Future deadlines (truly open calls)
                    elif deadline_date.year >= 2024:  # Only very recent calls
                        is_recent = True  # Recent calls from 2024+
                    else:
                        is_recent = False  # Exclude 2023 and earlier - they're too old to show as "current"
                except Exception as e:
                    # If we can't parse the date, include it (be permissive for parsing issues)
                    is_recent = True
            else:
                is_recent = True
            
            # Add additional metadata to call_data
            call_data.update({
                'status': status_readable,
                'status_raw': status_raw,
                'programme_period': programme_period,
                'framework_programme': metadata.get('frameworkProgramme', [''])[0] if isinstance(metadata.get('frameworkProgramme'), list) else '',
                'call_identifier': metadata.get('callIdentifier', [''])[0] if isinstance(metadata.get('callIdentifier'), list) else '',
                'call_title': metadata.get('callTitle', [''])[0] if isinstance(metadata.get('callTitle'), list) else '',
                'deadline_date': deadline_date,
                'is_recent': is_recent
            })
            
            # Categorize calls for smart selection
            if status_readable == 'Open':
                open_calls.append(call_data)
                print(f"✅ Found OPEN call: {call_data.get('title', 'Unknown')} (ID: {identifier})")
            elif status_readable == 'Forthcoming':
                forthcoming_calls.append(call_data)
                print(f"🔜 Found FORTHCOMING call: {call_data.get('title', 'Unknown')} (ID: {identifier})")
            elif status_readable == 'Closed' and is_recent:
                recent_closed_calls.append(call_data)
                print(f"📋 Found RECENT call: {call_data.get('title', 'Unknown')} (ID: {identifier})")
            elif (status_readable == 'Unknown' or 'Unknown' in status_readable) and programme_period and '2021' in programme_period and '2027' in programme_period:
                # Include calls with unknown status from current programme period - they might be valid
                recent_closed_calls.append(call_data)
                print(f"❓ Found UNKNOWN status call from current period: {call_data.get('title', 'Unknown')} (ID: {identifier})")
        
        # Smart selection priority: Open > Forthcoming > Recent closed calls (but only if no current calls)
        print(f"\n📈 Call categories found:")
        print(f"   🟢 Open calls: {len(open_calls)}")
        print(f"   🔵 Forthcoming calls: {len(forthcoming_calls)}")
        print(f"   🟡 Recent relevant calls: {len(recent_closed_calls)}")
        
        # Select the best calls to return - PRIORITIZE TRULY CURRENT CALLS
        calls_found = []
        
        # First, add all open calls
        calls_found.extend(open_calls)
        
        # Then add forthcoming calls if we need more
        if len(calls_found) < max_results:
            calls_found.extend(forthcoming_calls[:max_results - len(calls_found)])
        
        # ONLY add closed calls if we have NO open/forthcoming calls at all
        # This prevents showing old 2022 calls when users want current opportunities
        if len(calls_found) == 0:
            print("⚠️ No open or forthcoming calls found - considering recent closed calls as examples")
            
            # Be more selective about which closed calls to show
            filtered_recent_calls = []
            current_year = datetime.now().year
            
            for call in recent_closed_calls:
                deadline_date = call.get('deadline_date')
                # Only include calls from 2024+ (very recent) or current programme with no clear deadline
                if deadline_date:
                    if deadline_date.year >= 2024:  # Only very recent calls
                        filtered_recent_calls.append(call)
                        call['note'] = "⚠️ This call has recently closed - watch for similar upcoming calls in 2025"
                else:
                    # Unknown deadline calls from current programme might be worth showing
                    programme_period = call.get('programme_period', '')
                    if '2021' in programme_period and '2027' in programme_period:
                        filtered_recent_calls.append(call)
                        call['note'] = "⚠️ Status unclear - check the EU portal directly for current availability"
            
            # If we still have no results, the truth is there are no current calls
            if not filtered_recent_calls:
                print("💡 No current calls found - will inform user about the reality of EU funding timing")
            else:
                calls_found.extend(filtered_recent_calls[:max_results])
        else:
            print(f"🎉 Found {len(calls_found)} current/forthcoming calls - no need to show closed calls")
        
        # Limit to requested number
        calls_found = calls_found[:max_results]
        
        if not calls_found:
            print("⚠️ No current open calls found after strict filtering.")
            print("💡 This could mean:")
            print("   • No active calls in this specific area right now")
            print("   • All matching calls have recently closed")
            print("   • New calls may be published soon - check the EU portal directly")
        else:
            print(f"🎯 Returning {len(calls_found)} current/relevant calls")
        
        return calls_found

    def _decode_call_status(self, status_code: str) -> str:
        """
        Decode status codes to readable format based on EU API documentation
        """
        if not status_code:
            return "Unknown"
        
        status_mapping = {
            '31094502': 'Open',
            '31094503': 'Closed', 
            '31094501': 'Forthcoming',
        }
        
        return status_mapping.get(str(status_code), f"Unknown ({status_code})")

    def _save_debug_response(self, calls_found: List[Dict], search_text: str):
        """
        Save debug information for troubleshooting
        """
        try:
            import os
            import stat
            debug_dir = "debug"
            
            # Create debug directory with proper permissions
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir, exist_ok=True)
                # Set directory permissions explicitly
                os.chmod(debug_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
            
            timestamp = int(time.time())
            filename = os.path.join(debug_dir, f"eu_api_calls_found_{timestamp}.json")
            
            debug_data = {
                "search_text": search_text,
                "timestamp": timestamp,
                "datetime": datetime.now().isoformat(),
                "calls_found_count": len(calls_found),
                "calls_found": calls_found,
                "verification_url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;freeTextSearchKeyword={search_text.replace(' ', '%20')};sortQuery=sortStatus;orderBy=asc"
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Set file permissions
            os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            
            print(f"💾 Debug data saved to: {filename}")
            print(f"📂 You can inspect the raw API response in this file")
        except Exception as save_error:
            # Just print the error but don't fail - debug saving is not critical
            print(f"⚠️ Could not save debug data: {save_error}")
            print(f"   Try running: sudo chown -R $USER:$USER debug/ && chmod -R 755 debug/")
    
    def _get_demonstration_calls(self, search_text: str, max_results: int) -> List[Dict[str, Any]]:
        """
        DISABLED: This function previously generated fake demonstration data.
        It has been completely disabled to ensure only real data is ever returned.
        
        ⚠️ NO FAKE DATA POLICY: This system only provides real funding opportunities from official sources.
        """
        print("❌ _get_demonstration_calls called but DISABLED - no fake data will be provided")
        return []  # Always return empty list - no fake data ever

    def _extract_eu_portal_call_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and structure call/topic data from EU Funding & Tenders Portal API response.
        Updated based on actual API response structure analysis.
        """
        data = {}
        
        # Extract from metadata structure (the API returns data in metadata arrays)
        metadata = result.get('metadata', {})
        
        # Title extraction - based on actual API response analysis
        # The `content` field often contains the clean title, `summary` is descriptive
        title_candidates = [
            # Clean up HTML tags from content field which often has the title
            re.sub(r'<[^>]+>', '', result.get('content', '')).strip() if result.get('content') else None,
            # From metadata arrays
            metadata.get('callTitle', [None])[0] if isinstance(metadata.get('callTitle'), list) and metadata.get('callTitle') else None,
            # Direct fields as fallback
            result.get('title'),
            result.get('summary'),
            'Unknown Call'
        ]
        data['title'] = next((title for title in title_candidates if title and str(title).strip() and str(title).strip().lower() != 'none'), 'Unknown Call')
        
        # Identifier extraction - check metadata first
        identifier_candidates = [
            # From metadata arrays - this is where the actual identifier is stored
            metadata.get('identifier', [None])[0] if isinstance(metadata.get('identifier'), list) and metadata.get('identifier') else None,
            # Direct fields as fallback
            result.get('reference'),
            result.get('id'),
            'N/A'
        ]
        data['identifier'] = next((id_val for id_val in identifier_candidates if id_val and str(id_val).strip()), 'N/A')
        
        # Description - use summary as primary source, enhanced with content if needed
        description_parts = []
        
        # Summary is usually the main description
        if result.get('summary'):
            description_parts.append(result.get('summary'))
        
        # Add detailed description from metadata if available
        desc_bytes = metadata.get('descriptionByte', [None])[0] if isinstance(metadata.get('descriptionByte'), list) and metadata.get('descriptionByte') else None
        if desc_bytes:
            # Clean up HTML tags and extract readable text
            clean_desc = re.sub(r'<[^>]+>', ' ', str(desc_bytes))
            clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
            if len(clean_desc) > 100:  # Only add if substantial
                description_parts.append(clean_desc[:1000] + '...' if len(clean_desc) > 1000 else clean_desc)
        
        data['description'] = ' | '.join(description_parts) if description_parts else 'No description available'
        
        # Dates and deadlines - extract from metadata arrays
        deadline_candidates = [
            metadata.get('deadlineDate', [None])[0] if isinstance(metadata.get('deadlineDate'), list) and metadata.get('deadlineDate') else None,
            result.get('deadlineDate'),
            result.get('deadline'),
            'Not specified'
        ]
        data['deadline'] = next((date for date in deadline_candidates if date and str(date).strip()), 'Not specified')
        
        # Format deadline for better readability
        if data['deadline'] != 'Not specified':
            try:
                if 'T' in data['deadline']:
                    deadline_date = datetime.strptime(data['deadline'].split('T')[0], '%Y-%m-%d')
                    data['deadline'] = deadline_date.strftime('%B %d, %Y')
            except:
                pass  # Keep original format if parsing fails
        
        # Extract sort date for ordering
        sort_date_candidates = [
            metadata.get('es_SortDate', [None])[0] if isinstance(metadata.get('es_SortDate'), list) and metadata.get('es_SortDate') else None,
            result.get('sortDate'),
            'Not specified'
        ]
        data['sortDate'] = next((date for date in sort_date_candidates if date and str(date).strip()), 'Not specified')
        
        data['startDate'] = data['sortDate']  # Use sort date as start date for calls
        data['endDate'] = data['deadline']
        
        # Programme information from metadata
        programme_period = metadata.get('programmePeriod', [''])[0] if isinstance(metadata.get('programmePeriod'), list) and metadata.get('programmePeriod') else ''
        data['programme_period'] = programme_period or 'Not specified'
        
        framework_programme = metadata.get('frameworkProgramme', [''])[0] if isinstance(metadata.get('frameworkProgramme'), list) and metadata.get('frameworkProgramme') else ''
        data['frameworkProgramme'] = framework_programme or 'Horizon Europe'
        
        # Call information from metadata
        call_title = metadata.get('callTitle', [''])[0] if isinstance(metadata.get('callTitle'), list) and metadata.get('callTitle') else ''
        data['call_title'] = call_title or 'Not specified'
        
        call_identifier = metadata.get('callIdentifier', [''])[0] if isinstance(metadata.get('callIdentifier'), list) and metadata.get('callIdentifier') else ''
        data['call_identifier'] = call_identifier or 'Not specified'
        
        # Budget information - calls usually don't have specific budget in this API
        data['budget'] = 'Not specified in call data'
        
        # Call status and type - extract from metadata
        status_candidates = [
            metadata.get('status', [None])[0] if isinstance(metadata.get('status'), list) and metadata.get('status') else None,
            result.get('status'),
            'Unknown'
        ]
        raw_status = next((status for status in status_candidates if status and str(status).strip()), 'Unknown')
        
        # Map status codes to readable names
        status_mapping = {
            '31094502': 'Open',
            '31094503': 'Closed',
            '31094501': 'Forthcoming',
        }
        data['status'] = status_mapping.get(str(raw_status), f'Unknown ({raw_status})')
        
        # Get call type from metadata
        type_candidates = [
            metadata.get('type', [None])[0] if isinstance(metadata.get('type'), list) and metadata.get('type') else None,
            result.get('type'),
            'Call for proposals'
        ]
        data['type'] = next((call_type for call_type in type_candidates if call_type and str(call_type).strip()), 'Call for proposals')
        
        # Build proper working EU portal URLs
        url = None
        
        # Check if we have a valid URL from metadata (avoid JSON files)
        if metadata.get('esST_URL') and isinstance(metadata.get('esST_URL'), list):
            raw_url = metadata.get('esST_URL')[0]
            if raw_url and not raw_url.endswith('.json') and 'topic-details' not in raw_url:
                url = raw_url
        
        # Build proper EU portal URL that actually works
        if not url and data['identifier'] and data['identifier'] != 'N/A':
            # Use the EU portal search with topic code - this actually works
            encoded_identifier = data['identifier'].replace('-', '%2D')
            url = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;freeTextSearchKeyword={encoded_identifier}"
        
        # Fallback to general opportunities portal
        if not url:
            url = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/opportunities-tenders"
            
        data['url'] = url
        
        # Extract keywords from metadata
        keywords_list = metadata.get('keywords', []) if isinstance(metadata.get('keywords'), list) else []
        if keywords_list:
            data['keywords'] = ', '.join([str(k) for k in keywords_list if k and str(k).strip()])
        else:
            data['keywords'] = 'Not specified'
        
        # Extract work programme part
        work_programme = metadata.get('workProgrammepart', []) if isinstance(metadata.get('workProgrammepart'), list) else []
        data['work_programme'] = ', '.join([str(w) for w in work_programme if w]) if work_programme else 'Not specified'
        
        # Extract focus area
        focus_area = metadata.get('focusArea', []) if isinstance(metadata.get('focusArea'), list) else []
        data['focus_area'] = ', '.join([str(f) for f in focus_area if f]) if focus_area else 'Not specified'
        
        # Extract destination details if available
        destination_details = metadata.get('destinationDetails', [None])[0] if isinstance(metadata.get('destinationDetails'), list) and metadata.get('destinationDetails') else None
        if destination_details:
            # Clean up HTML and limit length
            clean_dest = re.sub(r'<[^>]+>', ' ', str(destination_details))
            clean_dest = re.sub(r'\s+', ' ', clean_dest).strip()
            data['destination_details'] = clean_dest[:500] + '...' if len(clean_dest) > 500 else clean_dest
        else:
            data['destination_details'] = 'Not specified'
        
        # Extract funding scheme information
        mga_types = metadata.get('typeOfMGAs', []) if isinstance(metadata.get('typeOfMGAs'), list) else []
        data['funding_scheme'] = ', '.join([str(m) for m in mga_types if m]) if mga_types else 'Not specified'
        
        # Language information
        language = metadata.get('language', ['en'])[0] if isinstance(metadata.get('language'), list) and metadata.get('language') else 'en'
        data['language'] = language
        
        return data

    def _generate_calls_answer(self, question: str, calls_data: List[Dict[str, Any]]) -> str:
        """
        Generate a comprehensive answer about found calls for proposals using EU Portal data.
        Enhanced to leverage the richer data available from the EU Funding & Tenders Portal API.
        """
        if not calls_data:
            return self._generate_no_calls_response(question)

        # Sort by deadline (if available) and relevance
        def sort_key(call):
            deadline = call.get('deadline', '')
            if deadline and deadline != 'Not specified':
                try:
                    # Try to parse deadline for sorting
                    return datetime.strptime(deadline.split('T')[0], '%Y-%m-%d')
                except:
                    pass
            return datetime.now()  # Default to now for unparseable dates

        sorted_calls = sorted(calls_data, key=sort_key)

        # Generate structured response
        answer_parts = [
            f"I found {len(calls_data)} relevant funding opportunities for your query about '{question}':",
            "",
            "⚠️ **IMPORTANT**: These are REAL funding opportunities from official sources. No fake or demonstration data is provided.",
            ""
        ]

        for i, call in enumerate(sorted_calls, 1):
            title = call.get('title', 'Unknown Call')
            identifier = call.get('identifier', 'N/A')
            deadline = call.get('deadline', 'Not specified')
            budget = call.get('budget', 'Not specified')
            programme = call.get('frameworkProgramme', 'Not specified')
            description = call.get('description', 'No description available')
            url = call.get('url', '')
            status = call.get('status', 'Unknown')
            funding_scheme = call.get('funding_scheme', 'Not specified')
            submission_procedure = call.get('submission_procedure', 'Standard submission')
            evaluation_type = call.get('evaluation_type', 'Not specified')

            # Format deadline nicely
            deadline_text = deadline
            if deadline != 'Not specified' and 'T' in deadline:
                try:
                    deadline_date = datetime.strptime(deadline.split('T')[0], '%Y-%m-%d')
                    deadline_text = deadline_date.strftime('%B %d, %Y')
                    
                    # Add urgency indicator (only for future dates)
                    days_until_deadline = (deadline_date - datetime.now()).days
                    if days_until_deadline > 0:  # Only show urgency for future deadlines
                        if days_until_deadline <= 30:
                            deadline_text += f" ⚠️ **URGENT** (only {days_until_deadline} days left!)"
                        elif days_until_deadline <= 60:
                            deadline_text += f" ⏰ **Soon** ({days_until_deadline} days left)"
                    else:
                        deadline_text += f" ❌ **EXPIRED** ({abs(days_until_deadline)} days ago)"
                except:
                    pass

            call_summary = f"**{i}. {title}**"
            
            if identifier != 'N/A':
                call_summary += f"\n📋 **Call ID:** {identifier}"
            
            if status != 'Unknown':
                call_summary += f"\n📊 **Status:** {status}"
            
            if deadline_text != 'Not specified':
                call_summary += f"\n⏰ **Application Deadline:** {deadline_text}"
            
            if programme != 'Not specified':
                call_summary += f"\n🏛️ **Programme:** {programme}"
                if funding_scheme != 'Not specified' and funding_scheme != programme:
                    call_summary += f" / {funding_scheme}"
            
            if budget != 'Not specified':
                call_summary += f"\n💰 **Budget:** {budget}"
            
            # Add submission and evaluation details
            if submission_procedure != 'Standard submission':
                call_summary += f"\n📝 **Submission:** {submission_procedure}"
            
            if evaluation_type != 'Not specified':
                call_summary += f"\n🔍 **Evaluation:** {evaluation_type}"
            
            # Add description (truncated)
            if description and description != 'No description available':
                desc_preview = description[:300] + ('...' if len(description) > 300 else '')
                call_summary += f"\n\n**Call Description:**\n{desc_preview}"
            
            # Add link
            if url:
                call_summary += f"\n\n🔗 **Apply Here:** {url}"
            else:
                # Fallback to general portal link
                call_summary += f"\n\n🔗 **Find on Portal:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home"
            
            answer_parts.append(call_summary)
            answer_parts.append("")  # Empty line between calls

        # Add enhanced footer with EU Portal specific guidance
        answer_parts.extend([
            "---",
            "",
            "💡 **How to Apply:**",
            "• **Register** on the EU Funding & Tenders Portal if you haven't already",
            "• **Check eligibility** criteria carefully for each call",
            "• **Prepare partnerships** - many calls require consortium applications",
            "• **Review evaluation criteria** and weightings in the call documentation",
            "• **Submit well before** the deadline - the portal can be busy near deadlines",
            "",
            "📚 **Useful Resources:**",
            "• EU Funding & Tenders Portal: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            "• Application Guidelines: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate",
            "• Partner Search: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/participant-register-search",
            "",
            "🎯 **Next Steps:**",
            "• Click on the 'Apply Here' links above for full call details",
            "• Download the call documentation and work programme",
            "• Start building your consortium if partnerships are required",
            "• Prepare your proposal using the official templates",
            "",
            "🔍 **Need more specific calls?** Try refining your search with more specific keywords, research areas, or check back regularly as new calls are published throughout the year."
        ])

        return "\n".join(answer_parts)

    def _generate_no_calls_response(self, question: str) -> str:
        """
        Generate a helpful response when no calls are found.
        Updated to reference the EU Funding & Tenders Portal and explain API issues.
        """
        current_year = datetime.now().year
        
        # Extract search terms for verification URL
        search_terms = question.lower().replace("what are some open calls for", "").replace("?", "").strip()
        if not search_terms:
            search_terms = "clean energy"
        
        verification_url = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;freeTextSearchKeyword={search_terms.replace(' ', '%20')};sortQuery=sortStatus;orderBy=asc"
        
        return f"""**🔍 No Currently Open Calls Found**

I searched the EU Funding & Tenders Portal but found **no currently open calls** for "{question}" right now in {current_year}.

**🔗 Verify This Yourself:**
**Manual Check:** {verification_url}
*(You can click this link to see the same search results I found)*

**📅 Why This Happens:**
• **EU funding follows scheduled cycles** - calls aren't always open
• **Clean energy calls** typically open at specific times during the year
• **Early {current_year}** - new calls may not be published yet
• **Previous calls closed** in late 2024

**🎯 What to Do Next:**

**📧 Set Up Alerts** (Recommended):
🔗 **EU Call Alerts:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/mailing-lists
• Get notified when new clean energy calls open
• Select "Climate, Energy and Environment" topics

**🔍 Check These Resources:**
🔗 **EU Funding Portal:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home
🔗 **Horizon Europe Work Programme:** https://ec.europa.eu/info/research-and-innovation/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe_en
🔗 **Call Calendar:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/calls-calendar

**⏰ When to Expect New Calls:**
• **Spring {current_year}**: Major Horizon Europe calls often published
• **Quarterly releases**: Check portal every 3 months
• **Follow @HorizonEU** on social media for announcements

**🔄 Alternative Approaches:**
• Try broader terms: "sustainable energy", "climate action", "green transition"
• Look for related programmes: EIC Accelerator, LIFE Programme, Digital Europe
• Consider national/regional funding opportunities

**💡 The Reality:** EU funding is competitive and cyclical. No open calls right now doesn't mean no opportunities - it means timing is everything!"""

    def _generate_no_calls_portal_fallback(self, question: str) -> str:
        """
        Concise fallback used when the EU Portal returns no calls for the query.
        Returns a short message with a portal verification URL and an explicit portal search link.
        """
        current_year = datetime.now().year

        # Extract search terms for verification URL
        search_terms = question.lower().replace("what are some open calls for", "").replace("?", "").strip()
        if not search_terms:
            search_terms = "Horizon Europe"

        verification_url = (
            "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/"
            f"topic-search;freeTextSearchKeyword={search_terms.replace(' ', '%20')};sortQuery=sortStatus;orderBy=asc"
        )

        # Concise, actionable fallback — no long documentation fallback here
        return (
            f"🔍 No currently open calls found for \"{question}\".\n\n"
            f"🔗 Try this portal search to verify: {verification_url}\n\n"
            "Tip: Broaden your keywords (e.g. 'sustainable energy', 'climate action') or check back later — "
            "new calls are published periodically."
        )
    def get_ai_response_with_routing(self, question: str, max_projects_to_process: int = 5, max_cordis_results: int = 10) -> Dict[str, Any]:
        """
        SIMPLIFIED routing system - only handles 3 specific functions:
        1. FAQ: General questions -> Enhanced RAG
        2. SEARCH_PROJECTS: Project search -> CORDIS
        3. SEARCH_CALLS: Call search -> EU Portal
        """
        total_start_time = time.time()
        
        print(f"🎯 SIMPLIFIED ROUTING: Processing question: '{question}'")
        
        try:
            # Simple intent determination
            from app.services.intent_service import IntentService
            user_intent, confidence = IntentService.determine_intent(question)
            
            print(f"🎯 Intent: {user_intent} (confidence: {confidence:.2f})")
            
            # Route to ONLY the 3 allowed functions
            if user_intent == "FAQ":
                print(f"📚 Routing FAQ to Enhanced RAG")
                try:
                    from .enhanced_rag_service import HorizonEuropeRAG
                    enhanced_rag = HorizonEuropeRAG()
                    
                    result = enhanced_rag.handle_general_query(
                        question=question,
                        max_context_chunks=5,
                        search_type="hybrid",
                        similarity_threshold=0.7
                    )
                    
                    total_time = time.time() - total_start_time
                    
                    return {
                        'answer': result.get('answer', 'I could not find relevant information to answer your question.'),
                        'routing_decision': 'FAQ',
                        'intent_confidence': confidence,
                        'data_source': 'Horizon Europe Documents (FAQ)',
                        'processing_time': round(total_time, 2),
                        'success': result.get('success', True)
                    }
                    
                except Exception as e:
                    print(f"❌ Enhanced RAG failed: {e}")
                    return {
                        'answer': 'I apologize, but I encountered an error accessing the documentation to answer your question. Please try rephrasing your question.',
                        'routing_decision': 'FAQ',
                        'intent_confidence': confidence,
                        'data_source': 'Error',
                        'success': False,
                        'error': str(e)
                    }
            
            elif user_intent == "SEARCH_CALLS":
                print(f"📞 Routing to Enhanced Call Search")
                try:
                    from .enhanced_rag_service import HorizonEuropeRAG
                    enhanced_rag = HorizonEuropeRAG(existing_cordis_rag=self)
                    
                    call_result = enhanced_rag.handle_call_query(question)
                    
                    total_time = time.time() - total_start_time
                    
                    return {
                        'answer': call_result.get('answer', 'No calls found.'),
                        'routing_decision': 'SEARCH_CALLS',
                        'intent_confidence': confidence,
                        'data_source': call_result.get('data_source', 'Enhanced Call Search'),
                        'processing_time': round(total_time, 2),
                        'call_count': call_result.get('call_count', 0),
                        'success': call_result.get('success', True)
                    }
                    
                except Exception as e:
                    print(f"❌ Enhanced call search failed, falling back: {e}")
                    # Fallback to original call search
                    call_result = self.search_for_calls(question, max_results=max_cordis_results)
                    
                    total_time = time.time() - total_start_time
                    
                    return {
                        'answer': call_result.get('answer', 'No calls found.'),
                        'routing_decision': 'SEARCH_CALLS',
                        'intent_confidence': confidence,
                        'data_source': call_result.get('data_source', 'EU Funding Portal (Fallback)'),
                        'processing_time': round(total_time, 2),
                        'call_count': call_result.get('call_count', 0),
                        'success': call_result.get('search_successful', True),
                        'fallback_used': True,
                        'fallback_reason': str(e)
                    }
            
            elif user_intent == "SEARCH_PROJECTS":
                print(f"🔬 Routing to Project Search")
                print(f"🔬 DEBUG: Question: '{question}'")
                print(f"🔬 DEBUG: Intent confidence: {confidence}")

                # Extract queries
                role, quest = self._get_phase1_prompt(question)
                print(f"🔬 DEBUG: About to extract queries from question: '{question}'")
                queries, end_flag, new_query_keys, rerank_criteria, problem_text, next_pass = self._extract_queries(role, quest)
                print(f"🔬 DEBUG: Extracted queries: {queries}")
                print(f"🔬 DEBUG: End flag: {end_flag}")
                print(f"🔬 DEBUG: Problem text: {problem_text}")

                if end_flag:
                    print(f"🔬 DEBUG: Query extraction failed with problem: {problem_text}")
                    return {
                        'answer': problem_text,
                        'routing_decision': 'SEARCH_PROJECTS',
                        'intent_confidence': confidence,
                        'data_source': 'Error',
                        'success': False
                    }
                
                # Use HYBRID SEARCH: CORDIS API first, then database enrichment
                try:
                    from app.services.hybrid_search_service import HybridSearchService
                    print("🔄 Using Hybrid Search: CORDIS API → Database Enrichment")
                    print(f"🔄 DEBUG: Queries being passed to hybrid search: {queries}")
                    print(f"🔄 DEBUG: Max CORDIS results: {max_cordis_results}")

                    hybrid_search = HybridSearchService()
                    project_data = hybrid_search.search_projects(queries, max_results=max_cordis_results)

                    print(f"🔄 DEBUG: Hybrid search returned {len(project_data) if project_data else 0} projects")
                    if project_data:
                        for i, proj in enumerate(project_data[:3]):  # Log first 3 projects
                            print(f"🔄 DEBUG: Project {i+1}: {proj.get('title', 'No title')[:100]}...")

                    # Determine data source based on enrichment
                    if project_data and any(p.get('enrichment_status') == 'complete' for p in project_data):
                        data_source = "CORDIS API + Local Database"
                    else:
                        data_source = "CORDIS API"
                    
                    # Select best projects if we got more than requested
                    if len(project_data) > max_projects_to_process:
                        project_data = self._adaptive_result_selection(project_data, question, max_projects_to_process)
                    
                except ImportError as e:
                    print(f"⚠️ Hybrid search not available: {e}, falling back to original method")
                    # Fallback to original method
                    data_source = "Local Database" if self.use_local_db else "CORDIS API"
                    
                    if self.use_local_db:
                        raw_project_data = self._search_local_database(queries, max_results=max_projects_to_process * 3)
                        project_data = self._adaptive_result_selection(raw_project_data, question, max_projects_to_process)
                    else:
                        project_items = self._search_cordis_api(queries, max_results=max_cordis_results)
                        project_data = [self._extract_project_data(item) for item in project_items[:max_projects_to_process]]
                        project_data = self._enrich_with_xml_data(project_data)
                
                # Rerank if needed
                if rerank_criteria and len(project_data) > 1:
                    project_data = self._enhanced_rerank_projects(project_data, rerank_criteria, question, role)
                
                # Generate answer
                answer = self._generate_enhanced_answer(role, question, project_data)
                
                total_time = time.time() - total_start_time
                
                return {
                    'answer': answer,
                    'routing_decision': 'SEARCH_PROJECTS',
                    'intent_confidence': confidence,
                    'data_source': data_source,
                    'processing_time': round(total_time, 2),
                    'projects_found': len(project_data),
                    'success': True
                }
            
            else:
                # Should never happen with new simplified intent detection
                return {
                    'answer': 'I can only help with three types of queries: (1) General FAQ about EU funding procedures and policies, (2) Searching for existing research projects, or (3) Finding open funding calls. Please rephrase your question to fit one of these categories.',
                    'routing_decision': 'UNSUPPORTED',
                    'intent_confidence': 0.0,
                    'data_source': 'None',
                    'success': False
                }

        except Exception as e:
            error_message = str(e)
            print(f"❌ Simplified routing failed: {error_message}")
            
            return {
                'answer': f"I apologize, but I encountered an error while processing your request: {error_message}",
                'routing_decision': 'ERROR',
                'intent_confidence': 0.0,
                'data_source': 'Error',
                'success': False,
                'error': error_message
            }

    def _is_capability_question(self, question: str) -> bool:
        """Detect if the user is asking about system capabilities."""
        q = (question or "").strip().lower()
        if not q:
            return False
        triggers = [
            "what can you help me with",
            "what can you do",
            "what do you do",
            "how can you help",
            "your capabilities",
            "what are you capable",
            "capabilities",
            "help me with?",
        ]
        return any(t in q for t in triggers)

    def _generate_capabilities_answer(self) -> str:
        """Return a concise description of assistant capabilities."""
        parts = [
            "Here's what I can help you with:",
            "",
            "1) Find open funding opportunities (EU Funding & Tenders Portal)",
            "   - Search and summarize open or forthcoming calls relevant to your topic",
            "   - Provide identifiers, deadlines, eligibility hints, and portal links",
            "",
            "2) Explore existing EU research projects (CORDIS)",
            "   - Search CORDIS projects, enrich results, and provide summaries",
            "   - Include direct CORDIS links and key details (programme, dates, partners)",
            "",
            "3) Answer Horizon Europe FAQs from documentation",
            "   - Procedures, eligibility, submission, evaluation, and guidance",
            "",
            "4) Conversational context & streaming",
            "   - Remember context in a conversation and stream answers progressively",
            "",
            "If you tell me your topic and goal, I can: (a) list open calls, (b) surface relevant projects, or (c) explain how to apply." 
        ]
        return "\n".join(parts)

    # Keep all existing V8 methods for backward compatibility
    def get_ai_response(self, question: str, max_projects_to_process: int = 5, max_cordis_results: int = 10) -> Dict[str, Any]:
        """
        Legacy method maintained for backward compatibility.
        In V9, this delegates to the new routing method.
        """
        return self.get_ai_response_with_routing(question, max_projects_to_process, max_cordis_results)

    # All other methods from V8 remain unchanged...
    def _get_cache_key(self, data) -> str:
        """Generate a cache key from data."""
        return hashlib.md5(str(data).encode()).hexdigest()

    def _get_from_cache(self, cache_dict: dict, key: str):
        """Get data from cache with TTL check."""
        if key in cache_dict:
            cached_data, timestamp = cache_dict[key]
            if time.time() - timestamp < self._cache_ttl:
                return cached_data
            else:
                # Cache expired, remove it
                del cache_dict[key]
        return None
    
    def _set_cache(self, cache_dict: dict, key: str, data):
        """Set data in cache with timestamp and size management."""
        # Clean up expired entries first
        current_time = time.time()
        expired_keys = [k for k, (_, timestamp) in cache_dict.items() 
                       if current_time - timestamp >= self._cache_ttl]
        for k in expired_keys:
            del cache_dict[k]
        
        # Limit cache size to prevent memory issues
        if len(cache_dict) >= self._max_cache_size:
            # Remove oldest entries
            oldest_keys = sorted(cache_dict.keys(), 
                               key=lambda k: cache_dict[k][1])[:len(cache_dict)//4]
            for k in oldest_keys:
                del cache_dict[k]
        
        cache_dict[key] = (data, current_time)

    def _format_db_project_data(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Format database row data into structured project data with ALL available fields."""
        project = {}
        
        # Basic project information
        project['id'] = str(row_dict.get('id', 'N/A'))
        project['rcn'] = str(row_dict.get('rcn', 'N/A'))
        project['title'] = row_dict.get('title', 'Unknown Title')
        project['acronym'] = row_dict.get('acronym', 'N/A')
        project['objective'] = row_dict.get('objective', 'No description available')
        
        # CRITICAL FIX: Properly retrieve status field
        project['status'] = row_dict.get('status', 'UNKNOWN')
        
        # Dates
        project['startDate'] = str(row_dict.get('startDate', 'Unknown'))
        project['endDate'] = str(row_dict.get('endDate', 'Unknown'))
        
        # Financial information
        total_cost = row_dict.get('totalCost')
        if total_cost and total_cost != 'N/A':
            try:
                # Convert Decimal to float for JSON serialization
                project['totalCost'] = float(str(total_cost))
                project['budget'] = f"€{float(str(total_cost)):,.0f}"
            except (ValueError, TypeError):
                project['totalCost'] = 0
                project['budget'] = 'N/A'
        else:
            project['totalCost'] = 0
            project['budget'] = 'N/A'
        
        ec_max_contribution = row_dict.get('ecMaxContribution')
        if ec_max_contribution:
            try:
                # Convert Decimal to float for JSON serialization
                project['ecMaxContribution'] = float(str(ec_max_contribution))
                project['ecContribution'] = f"€{float(str(ec_max_contribution)):,.0f}"
            except (ValueError, TypeError):
                project['ecMaxContribution'] = 0
                project['ecContribution'] = 'N/A'
        else:
            project['ecMaxContribution'] = 0
            project['ecContribution'] = 'N/A'
        
        # CRITICAL FIX: Properly retrieve ALL programme information fields
        project['frameworkProgramme'] = row_dict.get('frameworkProgramme', 'Unknown programme framework')
        project['fundingScheme'] = row_dict.get('fundingScheme', 'Unknown funding scheme')
        project['legalBasis'] = row_dict.get('legalBasis', 'N/A')
        project['topics'] = row_dict.get('topics', 'N/A')
        project['grantDoi'] = row_dict.get('grantDoi', 'N/A')
        
        # Participant information from aggregated data
        project['participant_count'] = row_dict.get('participant_count', 0)
        project['country_count'] = row_dict.get('country_count', 0)
        project['sme_count'] = row_dict.get('sme_count', 0)
        
        # Coordinator information
        project['coordinator_name'] = row_dict.get('coordinator_name', 'N/A')
        project['coordinator_country'] = row_dict.get('coordinator_country', 'N/A')
        project['coordinator_city'] = row_dict.get('coordinator_city', 'N/A')
        
        # Participant details (arrays from PostgreSQL)
        participant_names = row_dict.get('participant_names', [])
        if participant_names and participant_names != [None]:
            project['participant_names'] = [str(name) for name in participant_names if name]
        else:
            project['participant_names'] = []
        
        participant_countries = row_dict.get('participant_countries', [])
        if participant_countries and participant_countries != [None]:
            project['participant_countries'] = [str(country) for country in participant_countries if country]
        else:
            project['participant_countries'] = []
        
        participant_cities = row_dict.get('participant_cities', [])
        if participant_cities and participant_cities != [None]:
            project['participant_cities'] = [str(city) for city in participant_cities if city]
        else:
            project['participant_cities'] = []
        
        # Financial aggregations - convert Decimals to floats
        project['total_ec_contribution'] = float(str(row_dict.get('total_ec_contribution', 0) or 0))
        project['total_net_ec_contribution'] = float(str(row_dict.get('total_net_ec_contribution', 0) or 0))
        project['total_org_costs'] = float(str(row_dict.get('total_org_costs', 0) or 0))
        
        # Additional arrays
        nuts_codes = row_dict.get('nuts_codes', [])
        if nuts_codes and nuts_codes != [None]:
            project['nuts_codes'] = [str(code) for code in nuts_codes if code]
        else:
            project['nuts_codes'] = []
        
        activity_types = row_dict.get('activity_types', [])
        if activity_types and activity_types != [None]:
            project['activity_types'] = [str(activity) for activity in activity_types if activity]
        else:
            project['activity_types'] = []
        
        # Relevance score (if available from search)
        project['relevance_score'] = row_dict.get('relevance_score', 0)
        
        # Legacy fields for compatibility
        project['keywords'] = project.get('topics', 'N/A')
        
        # ENHANCED: Create comprehensive call_info with all programme details
        call_info_parts = []
        if project['frameworkProgramme'] != 'Unknown programme framework' and project['frameworkProgramme'] != 'N/A':
            call_info_parts.append(project['frameworkProgramme'])
        if project['fundingScheme'] != 'Unknown funding scheme' and project['fundingScheme'] != 'N/A':
            call_info_parts.append(project['fundingScheme'])
        
        project['call_info'] = ' / '.join(call_info_parts) if call_info_parts else 'Programme information not available'
        project['publications'] = 'N/A'  # Not available in basic project data
        
        # Add a flag to indicate if this project has complete programme information
        project['has_complete_programme_info'] = (
            project['frameworkProgramme'] != 'Unknown programme framework' and
            project['frameworkProgramme'] != 'N/A' and
            project['fundingScheme'] != 'Unknown funding scheme' and
            project['fundingScheme'] != 'N/A'
        )
        
        return project

    def _initialize_database_optimization(self):
        """Initialize database-specific optimizations and analysis."""
        if not self.db_pool:
            return
            
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
                    CREATE INDEX IF NOT EXISTS idx_projects_text_search 
                    ON projects USING gin(to_tsvector('english', title || ' ' || COALESCE(objective, '') || ' ' || COALESCE(topics, '')))
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_organizations_text_search 
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
            if 'conn' in locals() and self.db_pool:
                self.db_pool.putconn(conn)

    def _load_domain_keywords(self) -> Dict[str, List[str]]:
        """Load domain-specific keyword mappings for better query understanding."""
        return {
            'ai_ml': ['artificial intelligence', 'machine learning', 'deep learning', 'neural networks', 
                     'computer vision', 'natural language processing', 'nlp', 'ai', 'ml'],
            'energy': ['renewable energy', 'solar', 'wind', 'battery', 'energy storage', 'green energy',
                      'photovoltaic', 'hydroelectric', 'geothermal', 'energy efficiency', 'nuclear'],
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
    
    def _apply_disambiguation_filters(self, queries: List[str]) -> List[str]:
        """Apply disambiguation filters to avoid confusion between different domains."""
        filtered_queries = []
        
        for query in queries:
            query_lower = query.lower()
            
            # Detect automotive queries and filter out medical terms
            if any(auto_term in query_lower for auto_term in ['automotive', 'vehicle', 'car', 'transportation', 'mobility']):
                # If this is an automotive query, exclude medical CAR-T terms
                if not any(medical_term in query_lower for medical_term in ['car t-cell', 'car-t', 'chimeric', 'immunotherapy', 'leukemia', 'cancer']):
                    
                    # Replace generic "car" terms with more specific automotive terms
                    enhanced_query = query
                    if query.lower().strip() == "cars":
                        enhanced_query = "automotive OR vehicles OR transportation OR mobility OR electric OR driving"
                    elif "cars" in query_lower:
                        enhanced_query = query.replace("cars", "automotive OR vehicles OR transportation")
                        enhanced_query = enhanced_query.replace("Cars", "automotive OR vehicles OR transportation")
                        enhanced_query = enhanced_query.replace("CARS", "automotive OR vehicles OR transportation")
                    
                    # STRONG medical exclusion with comprehensive terms
                    medical_exclusions = ("AND NOT (immunotherapy OR leukemia OR cancer OR chimeric OR antigen OR receptor OR "
                                        "tcell OR t-cell OR cd19 OR cd22 OR cart OR car-t OR oncology OR hematology OR "
                                        "tumor OR tumour OR malignancy OR cytotoxic OR leukaemia OR therapy OR treatment OR "
                                        "clinical OR medical OR lymphoma OR myeloma OR blastic OR acute OR chronic)")
                    
                    enhanced_query = f"{enhanced_query} {medical_exclusions}"
                    filtered_queries.append(enhanced_query)
                    print(f"🚗🚨 Applied STRONG automotive filter: {enhanced_query}")
                else:
                    # Skip mixed queries that contain both automotive and medical terms
                    print(f"⚠️ Skipped mixed automotive/medical query: {query}")
                    continue
            else:
                # Non-automotive queries pass through unchanged
                filtered_queries.append(query)
        
        return filtered_queries if filtered_queries else queries  # Fallback to original if all filtered out

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
            
            # Apply disambiguation filters to avoid medical/automotive confusion
            filtered_queries = self._apply_disambiguation_filters(processed_queries)
            
            print(f"🔍 Enhanced search for: {filtered_queries}")
            
            # Separate text queries from date/budget queries
            text_queries = []
            date_conditions = []
            budget_conditions = []
            
            for query in filtered_queries:
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
        
        # Enhanced SQL with relevance scoring and ALL critical fields
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
                -- CRITICAL: Ensure we fetch ALL programme fields
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
        """Convert natural language query to PostgreSQL tsquery format with proper exclusion support."""
        
        # Handle AND NOT exclusions first
        if ' AND NOT ' in query.upper():
            # Split into include and exclude parts
            parts = re.split(r'\s+AND\s+NOT\s+', query, flags=re.IGNORECASE)
            include_part = parts[0].strip()
            exclude_parts = parts[1:] if len(parts) > 1 else []
            
            # Process include part
            include_tsquery = self._convert_simple_query_to_tsquery(include_part)
            
            # Process exclude parts
            exclude_terms = []
            for exclude_part in exclude_parts:
                # Handle parentheses in exclusions like "(immunotherapy OR cancer)"
                exclude_part = exclude_part.strip()
                if exclude_part.startswith('(') and exclude_part.endswith(')'):
                    exclude_part = exclude_part[1:-1]  # Remove parentheses
                
                # Split by OR for exclusions
                if ' OR ' in exclude_part.upper():
                    or_terms = [term.strip() for term in re.split(r'\s+OR\s+', exclude_part, flags=re.IGNORECASE)]
                    for term in or_terms:
                        clean_term = term.replace('"', '').replace("'", "").strip()
                        if len(clean_term) > 2 and clean_term.lower() not in self._stopwords:
                            exclude_terms.append(f"!{clean_term}")
                else:
                    # Single exclusion term
                    clean_term = exclude_part.replace('"', '').replace("'", "").strip()
                    if len(clean_term) > 2 and clean_term.lower() not in self._stopwords:
                        exclude_terms.append(f"!{clean_term}")
            
            # Combine include and exclude parts
            if exclude_terms:
                full_query = f"{include_tsquery} & {' & '.join(exclude_terms)}"
                print(f"🔍 Converted query with exclusions: '{query}' -> '{full_query}'")
                return full_query
            else:
                return include_tsquery
        
        # If no exclusions, use the simple conversion
        return self._convert_simple_query_to_tsquery(query)
    
    def _convert_simple_query_to_tsquery(self, query: str) -> str:
        """Convert a simple query (no exclusions) to tsquery format."""
        # Handle OR conditions
        if ' OR ' in query.upper():
            terms = [term.strip() for term in re.split(r'\s+OR\s+', query, flags=re.IGNORECASE)]
            # Clean terms - remove quotes and escape special characters
            clean_terms = []
            for term in terms:
                if term:
                    # Remove any existing quotes and clean the term
                    clean_term = term.replace('"', '').replace("'", "").strip()
                    # Split multi-word terms and join with &
                    if ' ' in clean_term:
                        words = [w for w in clean_term.split() if len(w) > 2 and w.lower() not in self._stopwords]
                        if words:
                            clean_terms.append(' & '.join(words))
                    elif len(clean_term) > 2 and clean_term.lower() not in self._stopwords:
                        clean_terms.append(clean_term)
            
            return ' | '.join(clean_terms) if clean_terms else 'automotive'
        
        # Handle AND conditions (default)
        terms = query.split()
        # Filter out stopwords and short terms
        meaningful_terms = [term for term in terms if len(term) > 2 and term.lower() not in self._stopwords]
        
        if not meaningful_terms:
            # Fallback to a simple term
            return 'automotive'
        
        return ' & '.join(meaningful_terms[:5])  # Limit to 5 terms

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
        
        # Simple filtered query with ALL programme fields
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
- ALWAYS mention the programme framework (Horizon Europe, Horizon 2020, FP7, etc.) for EACH project - this is CRITICAL information
- If a project's framework programme is unknown, explicitly state "programme framework not available in database"
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
            # Filter out unknown/N/A values for better insights
            valid_frameworks = {k: v for k, v in frameworks.items()
                              if k not in ['Unknown programme framework', 'N/A', 'Unknown', '']}
            if valid_frameworks:
                top_fw = max(valid_frameworks.items(), key=lambda x: x[1])
                insights.append(f"Most common programme: {top_fw[0]} ({top_fw[1]} projects)")
                
                # List all frameworks if there are multiple
                if len(valid_frameworks) > 1:
                    fw_list = ', '.join([f"{fw} ({count})" for fw, count in valid_frameworks.items()])
                    insights.append(f"Programme distribution: {fw_list}")
        
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
            # CRITICAL FIX: Get framework programme with proper fallback
            framework_programme = proj.get('frameworkProgramme', 'Unknown programme framework')
            funding_scheme = proj.get('fundingScheme', 'Unknown funding scheme')
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
            
            # Programme and funding - ENHANCED DISPLAY
            programme_parts = []
            if framework_programme not in ['N/A', 'Unknown programme framework', None, '']:
                programme_parts.append(framework_programme)
            if funding_scheme not in ['N/A', 'Unknown funding scheme', None, ''] and funding_scheme != framework_programme:
                programme_parts.append(funding_scheme)
            
            if programme_parts:
                summary += f"\n🏛️ **Programme:** {' / '.join(programme_parts)}"
            else:
                summary += f"\n🏛️ **Programme:** Information not available in database"
            
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

    def _enrich_with_xml_data(self, project_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Placeholder for XML enrichment - not needed for local database mode."""
        return project_data

    def _call_llm_for_generation(self, role: str, prompt: str) -> str:
        """Centralized LLM calling with error handling."""
        try:
            if self.ai_provider == "openai":
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model_name,
                    messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt}],
                    temperature=0.0  # Complete determinism for consistency
                )
                content = response.choices[0].message.content
                return content if content is not None else "I apologize, but I received an empty response."
            elif self.ai_provider == "gemini":
                gemini_contents = [
                    types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                    types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
                ]
                gen_config = types.GenerateContentConfig(temperature=0.0)  # Complete determinism for consistency
                if self.gemini_client:
                    response = self.gemini_client.models.generate_content(
                        model=self.gemini_model_name,
                        contents=gemini_contents,
                        config=gen_config
                    )
                    content = response.text
                    return content if content is not None else "I apologize, but I received an empty response."
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

    def _disambiguate_query_response(self, ans: str, original_question: str) -> str:
        """
        Disambiguate common query misinterpretations to ensure consistency.
        
        This method fixes common AI misinterpretations like confusing:
        - "cars" (automotive) with "CAR" (Chimeric Antigen Receptor therapy)
        - Other domain-specific ambiguities
        """
        if not ans or not original_question:
            return ans
            
        original_lower = original_question.lower()
        ans_lower = ans.lower()
        
        # Fix "cars" vs "CAR T-cell therapy" confusion
        if ("cars" in original_lower or "automotive" in original_lower or "vehicle" in original_lower):
            # If the AI interpreted it as CAR T-cell therapy, fix it
            problematic_terms = ["car t-cell", "car-t", "chimeric antigen receptor", "immunotherapy", "t cell", "cancer"]
            if any(term in ans_lower for term in problematic_terms):
                print("🔧 Detected CAR T-cell therapy misinterpretation for automotive query - fixing...")
                # Replace with automotive terms
                fixed_ans = re.sub(r'CAR T-cell.*?therapy', 'automotive vehicles', ans, flags=re.IGNORECASE)
                fixed_ans = re.sub(r'chimeric antigen receptor', 'automotive vehicles', fixed_ans, flags=re.IGNORECASE)
                fixed_ans = re.sub(r'immunotherapy', 'automotive', fixed_ans, flags=re.IGNORECASE)
                fixed_ans = re.sub(r'cancer.*?treatment', 'automotive technology', fixed_ans, flags=re.IGNORECASE)
                
                # Fix the queries specifically
                fixed_ans = re.sub(r'queries\s*=\s*\[.*?\]', 
                                 'queries = ["automotive OR vehicles OR cars OR transportation"]', 
                                 fixed_ans, flags=re.IGNORECASE)
                return fixed_ans
        
        # Fix wind energy misinterpretations 
        if ("wind energy" in original_lower or "wind power" in original_lower):
            # Ensure wind energy projects are properly targeted
            if "wind" not in ans_lower and "renewable" not in ans_lower:
                print("🔧 Adding wind energy terms to improve search...")
                # Add wind energy terms to queries
                ans = re.sub(r'(queries\s*=\s*\[)', r'\1"wind energy OR wind power OR offshore wind OR renewable energy", ', ans)
        
        return ans

    def _extract_queries(self, role, quest):
        # Temporarily disable caching for consistency testing
        # The per-request instance creation means cache isn't shared anyway
        
        ans = ""
        if self.ai_provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ValueError("OpenAI package not installed. Install with: pip install openai")
            completion = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[{"role": "system", "content": role}, {"role": "user", "content": quest}],
                temperature=0.0,  # Complete determinism for consistency
                n=1  # Generate only one completion for deterministic behavior
            )
            ans = completion.choices[0].message.content  # Always pick the first (and only) completion
        elif self.ai_provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ValueError("Google Gemini package not installed. Install with: pip install google-genai")
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="user", parts=[types.Part.from_text(text=quest)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.0)  # Complete determinism for consistency
            if self.gemini_client:
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model_name,
                    contents=gemini_contents,
                    config=gen_config
                )
                ans = response.text if response.text else ""
            else:
                ans = ""
        
        # Ensure ans is never None
        if ans is None:
            ans = ""
        
        # Add query disambiguation for common misinterpretations  
        original_ans = ans
        ans = self._disambiguate_query_response(ans, quest)
        if ans != original_ans:
            print("🔧 Query disambiguation applied - interpretation corrected")
        
        # Additional ULTRA STRONG disambiguation at query level
        if "cars" in quest.lower() or "automotive" in quest.lower() or "vehicle" in quest.lower():
            # Force automotive interpretation if detected
            if ("car t-cell" in ans.lower() or "chimeric antigen receptor" in ans.lower() or 
                "immunotherapy" in ans.lower() or "leukemia" in ans.lower() or "cancer" in ans.lower()):
                print("🚨🚗 ULTRA STRONG disambiguation: Forcing automotive interpretation and blocking ALL medical content")
                # Completely replace with automotive-specific queries that exclude all medical terms
                ans = re.sub(r'queries\s*=\s*\[.*?\]', 
                           'queries = ["(automotive OR vehicles OR transportation OR mobility OR electric OR driving) AND NOT (immunotherapy OR cancer OR leukemia OR therapy OR medical OR clinical)", "startDate>2019-01-01"]', 
                           ans, flags=re.IGNORECASE)
            elif "cars" in ans.lower() and not ("automotive" in ans.lower() or "vehicle" in ans.lower()):
                # If just using generic "cars", make it more automotive-specific
                print("🚗 Making 'cars' query more automotive-specific")
                ans = ans.replace('"cars"', '"automotive OR vehicles OR transportation OR mobility"')
                ans = ans.replace("'cars'", "'automotive OR vehicles OR transportation OR mobility'")
                ans = ans.replace("cars", "automotive OR vehicles OR transportation")
            
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
                # Handle cases where words might not be properly quoted
                try:
                    queries = eval(lst)
                except (NameError, SyntaxError) as e:
                    # Fix unquoted bare words like project_objective
                    lst_normalized = lst.replace('"', '').replace("'", '')
                    lst_quoted = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_\s]*)\b', r'"\1"', lst_normalized)
                    lst_quoted = re.sub(r'""', r'"', lst_quoted)
                    try:
                        queries = eval(lst_quoted)
                        print(f"Fixed queries parsing: {lst} -> {lst_quoted}")
                    except (SyntaxError, ValueError, NameError) as e2:
                        print(f"Error parsing queries: {lst} -> {lst_quoted}. Error: {e2}")
                        queries = []  # Fallback to empty list
            if "second_stage" in line:
                if "True" in line:
                    next_pass = 1
            if "required_information=" in line or "required_information =" in line:
                lst = line[line.index("["):line.index("]")+1]
                # Handle cases where words might not be properly quoted
                try:
                    new_query_keys = eval(lst)
                except (NameError, SyntaxError) as e:
                    # Fix unquoted bare words like project_objective
                    lst_normalized = lst.replace('"', '').replace("'", '')
                    lst_quoted = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_\s]*)\b', r'"\1"', lst_normalized)
                    lst_quoted = re.sub(r'""', r'"', lst_quoted)
                    try:
                        new_query_keys = eval(lst_quoted)
                        print(f"Fixed required_information parsing: {lst} -> {lst_quoted}")
                    except (SyntaxError, ValueError, NameError) as e2:
                        print(f"Error parsing required_information: {lst} -> {lst_quoted}. Error: {e2}")
                        new_query_keys = []  # Fallback to empty list
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
        # Return result directly (caching disabled for consistency testing)
        result = (queries, end_flag, new_query_keys, rerank_criteria, problem_text, next_pass)
        print(f"🎯 Generated {len(queries)} queries: {queries}")
        
        return result

    def _search_cordis_api(self, queries: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        # Create cache key from queries
        cache_key = self._get_cache_key((queries, max_results))
        
        # Check cache first
        cached_result = self._get_from_cache(self._api_cache, cache_key)
        if cached_result is not None:
            print(f"Using cached CORDIS API results for {len(queries)} queries")
            return cached_result
        
        base_api_url = "https://cordis.europa.eu/api/search/results"
        
        # Separate static filters from keyword searches
        static_parts = ["contenttype='project'", "language='en'"]
        keyword_parts = []
        
        for item_query in queries:
            item_query_stripped = item_query.strip()
            if not item_query_stripped:
                continue
            item_query_lower = item_query_stripped.lower()
            
            # Date filters go in static parts
            if "startdate" in item_query_lower or "enddate" in item_query_lower:
                date_str = item_query_stripped.replace(" ", "")
                static_parts.append(date_str)
            # Keyword searches go in keyword parts
            else:
                or_terms = item_query_stripped.split("OR")
                valid_or_terms = [term.strip() for term in or_terms if term.strip()]
                if not valid_or_terms:
                    continue
                # Don't wrap in extra parentheses - we'll do that when combining
                for term in valid_or_terms:
                    keyword_parts.append(f"'{term}'")
        
        # Build final query: static filters AND (keyword1 OR keyword2 OR ...)
        if keyword_parts:
            keyword_query = f"({ ' OR '.join(keyword_parts) })"
            q_value = " AND ".join(static_parts + [keyword_query])
        else:
            q_value = " AND ".join(static_parts)
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
        prompt_rerank = f"""The json files embodying detailed information about relevant projects are as follows: {json.dumps(project_data, cls=DecimalEncoder)}. Sort those json files according to the criteria in the following list: {rerank_criteria}. Also consider their relevance to the question and their overall importance. At the very and of your response, give the sorted list of titles of projects. The titles you put in the list must be written totally the same as they are in the json file. The list must be a python list named sorted_titles and must be in a single line. Except that list, do not include any python code in your reponse."""
        if self.ai_provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ValueError("OpenAI package not installed. Install with: pip install openai")
            reranker_response = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt_rerank}]
            )
            reranked_str = reranker_response.choices[0].message.content
        elif self.ai_provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ValueError("Google Gemini package not installed. Install with: pip install google-genai")
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="user", parts=[types.Part.from_text(text=prompt_rerank)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.0)  # Complete determinism for consistency
            if self.gemini_client:
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model_name,
                    contents=gemini_contents,
                    config=gen_config
                )
                reranked_str = response.text
            else:
                reranked_str = None
        
        if not reranked_str:
            return project_data  # Return original data if reranking fails
            
        try:
            offset = reranked_str.index("sorted_titles =") if "sorted_titles =" in reranked_str else reranked_str.index("sorted_titles=")
            start_idx_lst = reranked_str.index("[",offset)
            end_idx_lst = reranked_str.index("]",start_idx_lst)
            # Handle cases where titles might not be properly quoted
            list_str = reranked_str[start_idx_lst:end_idx_lst+1].strip()
        except (ValueError, AttributeError):
            # If we can't find the sorted_titles list, return original data
            return project_data
        
        try:
            sorted_titles = eval(list_str)
        except (NameError, SyntaxError) as e:
            # Fix unquoted bare words
            lst_normalized = list_str.replace('"', '').replace("'", '')
            lst_quoted = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_\s]*)\b', r'"\1"', lst_normalized)
            lst_quoted = re.sub(r'""', r'"', lst_quoted)
            try:
                sorted_titles = eval(lst_quoted)
                print(f"Fixed sorted_titles parsing: {list_str} -> {lst_quoted}")
            except (SyntaxError, ValueError, NameError) as e2:
                print(f"Error parsing sorted_titles: {list_str} -> {lst_quoted}. Error: {e2}")
                sorted_titles = []  # Fallback to empty list
        reranked_jsons = []
        for title in sorted_titles[:5]:
            for proj in project_data:
                if set(proj["title"].lower().split(" ")) - {"", " "} == set(title.lower().split(" ")) - {"", " "}:
                    reranked_jsons.append(proj)
        return reranked_jsons

    def __del__(self):
        """Clean up database connections."""
        if hasattr(self, 'db_pool') and self.db_pool:
            self.db_pool.closeall()

    async def get_ai_response_stream(self, question: str, max_projects_to_process: int = 5, max_cordis_results: int = 10):
        """
        Stream the AI response generation process with real-time updates.
        Yields progress updates and token-by-token response for enhanced user experience.
        """
        total_start_time = time.time()
        data_source = "Local Database" if self.use_local_db else "CORDIS API"
        
        # Initialize comprehensive logging
        pipeline_logs = {
            'question': question,
            'data_source': data_source,
            'model_used': self.openai_model_name if self.ai_provider == "openai" else self.gemini_model_name,
            'ai_provider': self.ai_provider,
            'phases': [],
            'total_processing_time_ms': 0,
            'projects_retrieved': 0,
            'projects_processed': 0,
            'success': True,
            'error_message': None
        }
        
        try:
            # Phase 1: Query extraction with streaming updates
            yield {'type': 'progress', 'phase': 'query_extraction', 'message': 'Analyzing question and extracting search queries...'}
            
            phase_start = time.time()
            role, quest = self._get_phase1_prompt(question)
            queries, end_flag, new_query_keys, rerank_criteria, problem_text, next_pass = self._extract_queries(role, quest)
            phase_time = time.time() - phase_start
            
            # Log Phase 1
            phase_log = {
                'phase_number': 1,
                'phase_name': 'Query extraction',
                'operation': 'Extract search queries from user question',
                'processing_time_ms': int(phase_time * 1000),
                'queries_generated': queries,
                'rerank_criteria': rerank_criteria,
                'success': not end_flag,
                'error_message': problem_text if end_flag else None
            }
            pipeline_logs['phases'].append(phase_log)
            
            if end_flag:
                pipeline_logs['success'] = False
                pipeline_logs['error_message'] = problem_text
                pipeline_logs['total_processing_time_ms'] = int((time.time() - total_start_time) * 1000)
                yield {'type': 'error', 'error': 'Query processing failed', 'details': problem_text}
                return
            
            # Phase 2: Enhanced data retrieval with progress updates
            yield {'type': 'progress', 'phase': 'data_retrieval', 'message': f'Searching for projects using {len(queries)} queries...'}
            
            phase_start = time.time()
            if self.use_local_db:
                # Get more results initially for better selection
                initial_results = max_projects_to_process * 3
                raw_project_data = self._search_local_database(queries, max_results=initial_results)
                
                # Intelligently select the best projects
                project_data = self._adaptive_result_selection(raw_project_data, question, max_projects_to_process)
                
                # Log Phase 2 (Local DB)
                phase_time = time.time() - phase_start
                phase_log = {
                    'phase_number': 2,
                    'phase_name': 'Enhanced Local DB search',
                    'operation': 'Search local database and select best projects',
                    'processing_time_ms': int(phase_time * 1000),
                    'projects_found': len(raw_project_data),
                    'projects_selected': len(project_data),
                    'relevance_scores': [proj.get('relevance_score', 0) for proj in project_data],
                    'success': True,
                    'error_message': None
                }
                pipeline_logs['phases'].append(phase_log)
                pipeline_logs['projects_retrieved'] = len(raw_project_data)
                pipeline_logs['projects_processed'] = len(project_data)
                
                yield {'type': 'progress', 'phase': 'data_retrieval', 'message': f'Selected {len(project_data)} best projects from {len(raw_project_data)} candidates'}
            else:
                project_items = self._search_cordis_api(queries, max_results=max_cordis_results)
                
                yield {'type': 'progress', 'phase': 'data_processing', 'message': f'Processing {len(project_items)} projects from CORDIS API...'}
                
                # Log Phase 2 (API)
                phase_time = time.time() - phase_start
                phase_log = {
                    'phase_number': 2,
                    'phase_name': 'CORDIS API search',
                    'operation': 'Search CORDIS API for projects',
                    'processing_time_ms': int(phase_time * 1000),
                    'projects_found': len(project_items),
                    'success': True,
                    'error_message': None
                }
                pipeline_logs['phases'].append(phase_log)
                
                # Phase 3: Project data extraction (only for API mode)
                phase_start = time.time()
                project_data = [self._extract_project_data(item) for item in project_items[:max_projects_to_process]]
                
                # Log Phase 3
                phase_time = time.time() - phase_start
                phase_log = {
                    'phase_number': 3,
                    'phase_name': 'Data extraction',
                    'operation': 'Extract structured data from API results',
                    'processing_time_ms': int(phase_time * 1000),
                    'projects_processed': len(project_data),
                    'success': True,
                    'error_message': None
                }
                pipeline_logs['phases'].append(phase_log)
                pipeline_logs['projects_retrieved'] = len(project_items)
                pipeline_logs['projects_processed'] = len(project_data)
                
                print(f"📊 Phase 3 (Data extraction) completed in {phase_time:.2f}s")
                
                # Phase 3.5: XML enrichment (only for API mode)
                phase_start = time.time()
                project_data = self._enrich_with_xml_data(project_data)
                
                # Log Phase 3.5
                phase_time = time.time() - phase_start
                phase_log = {
                    'phase_number': 3.5,
                    'phase_name': 'XML enrichment',
                    'operation': 'Enrich project data with XML details',
                    'processing_time_ms': int(phase_time * 1000),
                    'projects_processed': len(project_data),
                    'success': True,
                    'error_message': None
                }
                pipeline_logs['phases'].append(phase_log)
                print(f"🔗 Phase 3.5 (XML enrichment) completed in {phase_time:.2f}s")
            
            # Phase 4: Enhanced reranking
            if rerank_criteria and len(project_data) > 1:
                yield {'type': 'progress', 'phase': 'reranking', 'message': 'Reranking projects by relevance and criteria...'}
                
                phase_start = time.time()
                original_count = len(project_data)
                project_data = self._enhanced_rerank_projects(project_data, rerank_criteria, question, role)
                
                # Log Phase 4
                phase_time = time.time() - phase_start
                phase_log = {
                    'phase_number': 4,
                    'phase_name': 'Enhanced reranking',
                    'operation': 'Rerank projects based on criteria and relevance',
                    'processing_time_ms': int(phase_time * 1000),
                    'projects_before_rerank': original_count,
                    'projects_after_rerank': len(project_data),
                    'rerank_criteria': rerank_criteria,
                    'success': True,
                    'error_message': None
                }
                pipeline_logs['phases'].append(phase_log)
            
            # Phase 6: Enhanced answer generation with streaming
            yield {'type': 'progress', 'phase': 'answer_generation', 'message': 'Generating comprehensive answer with real-time streaming...'}
            
            # Stream the answer generation
            full_answer = ""
            async for token_chunk in self._generate_enhanced_answer_stream(role, question, project_data):
                if token_chunk['type'] == 'token':
                    full_answer += token_chunk['content']
                    yield token_chunk
                elif token_chunk['type'] == 'complete':
                    break
            
            # Log Phase 6
            phase_time = time.time() - total_start_time  # Total time for answer generation
            phase_log = {
                'phase_number': 6,
                'phase_name': 'Enhanced answer generation',
                'operation': 'Generate comprehensive answer with streaming',
                'processing_time_ms': int(phase_time * 1000),
                'projects_used_in_answer': len(project_data),
                'answer_length': len(full_answer),
                'success': True,
                'error_message': None
            }
            pipeline_logs['phases'].append(phase_log)
            
            # Finalize logging
            total_time = time.time() - total_start_time
            pipeline_logs['total_processing_time_ms'] = int(total_time * 1000)
            
            # Calculate average relevance score
            relevance_scores = []
            for project in project_data:
                score = project.get('relevance_score', 0)
                if score > 0:
                    relevance_scores.append(score)
            
            pipeline_logs['average_relevance_score'] = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
            
            # Final completion
            yield {
                'type': 'complete',
                'answer': full_answer,
                'logs': pipeline_logs,
                'data_source': data_source,
                'projects_found': len(project_data),
                'processing_time': round(total_time, 2),
                'ai_provider': self.ai_provider,
                'ai_version': 'V8'
            }
            
        except Exception as e:
            # Log the error
            error_message = str(e)
            pipeline_logs['success'] = False
            pipeline_logs['error_message'] = error_message
            pipeline_logs['total_processing_time_ms'] = int((time.time() - total_start_time) * 1000)
            
            yield {'type': 'error', 'error': 'Processing failed', 'details': error_message}

    async def _generate_enhanced_answer_stream(self, role: str, user_text: str, project_data: List[Dict[str, Any]]):
        """
        Generate enhanced answer with token-by-token streaming for real-time user experience.
        Optimized for performance with minimal delays.
        """
        if not project_data:
            error_msg = self._generate_no_results_response(user_text)
            # Stream the error message with minimal delay
            words = error_msg.split(' ')
            for i, word in enumerate(words):
                token = word + (' ' if i < len(words) - 1 else '')
                yield {'type': 'token', 'content': token}
            yield {'type': 'complete'}
            return
        
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
        
        # Stream the LLM response based on provider
        if self.ai_provider == "openai":
            # Use OpenAI's native streaming
            try:
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model_name,
                    messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt}],
                    temperature=0.0,  # Complete determinism for consistency
                    stream=True
                )
                
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        yield {'type': 'token', 'content': chunk.choices[0].delta.content}
                        # No artificial delay for OpenAI streaming - it's already throttled
            except Exception as e:
                print(f"OpenAI streaming error: {e}")
                # Fallback to non-streaming
                answer = self._call_llm_for_generation(role, prompt)
                # Stream by chunks instead of words for better performance
                chunk_size = 50  # Characters per chunk
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i+chunk_size]
                    yield {'type': 'token', 'content': chunk}
        
        elif self.ai_provider == "gemini":
            # Gemini doesn't have native streaming in this SDK, so use optimized chunking
            answer = self._call_llm_for_generation(role, prompt)
            
            # Stream by larger chunks for better performance
            chunk_size = 30  # Characters per chunk
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i+chunk_size]
                yield {'type': 'token', 'content': chunk}
        
        yield {'type': 'complete'}
    def get_ai_response_with_context(
        self,
        question: str,
        conversation_context,
        max_projects_to_process: int = 5,
        max_cordis_results: int = 10
    ) -> Dict[str, Any]:
        """
        Process question with CONTEXT-FIRST analysis, then decide on approach.
        This enables more intelligent, conversational responses.
        """
        
        print(f"🧠 Context-First Processing: '{question}'")
        
        # Step 1: Analyze conversation context FIRST
        try:
            from app.services.context_aware_planning_service import ContextFirstRAGService
            context_first_rag = ContextFirstRAGService(ai_provider=self.ai_provider)
            
            # Get context-aware response
            result = context_first_rag.get_context_aware_response(
                question,
                conversation_context,
                max_projects_to_process
            )
            
            if result['success']:
                print(f"✅ Context-first approach: {result['approach']}")
                
                # Format response to match expected structure
                response = {
                    'answer': result['answer'],
                    'routing_decision': f"CONTEXT_FIRST_{result['approach'].upper()}",
                    'data_source': result.get('data_source', 'Context Analysis'),
                    'context_used': True,
                    'resolved_question': question,
                    'approach': result['approach'],
                    'success': True
                }
                
                # Add clarification questions if available
                if 'clarification_questions' in result:
                    response['clarification_questions'] = result['clarification_questions']
                
                # Add context insight
                if 'context_insight' in result:
                    response['context_insight'] = {
                        'analysis': result['context_insight'].analysis_result.value,
                        'confidence': result['context_insight'].confidence,
                        'reasoning': result['context_insight'].reasoning
                    }
                
                # Generate follow-up suggestions
                from app.services.conversation_context_service import ConversationContextService
                context_service = ConversationContextService(os.getenv("DATABASE_URL"))
                response['follow_up_suggestions'] = context_service.generate_follow_up_suggestions(
                    conversation_context,
                    response
                )
                
                return response
            else:
                print("⚠️ Context-first processing failed, falling back")
                
        except Exception as e:
            print(f"⚠️ Context-first RAG failed: {e}, falling back to regular processing")
        
        # Fallback to original method if context-first fails
        print("🔄 Using fallback context-aware processing")
        
        # Resolve references in the question
        from app.services.conversation_context_service import ConversationContextService
        context_service = ConversationContextService(os.getenv("DATABASE_URL"))
        
        # Handle both old and new resolve_references return formats
        resolution_result = context_service.resolve_references(question, conversation_context)
        if isinstance(resolution_result, tuple):
            resolved_question, needs_detailed_lookup = resolution_result
        else:
            resolved_question = resolution_result
            needs_detailed_lookup = False
        
        # Build context-aware prompt
        context_prompt = self._build_context_prompt(conversation_context)
        
        # Get the base response using existing method
        response = self.get_ai_response_with_routing(
            resolved_question,
            max_projects_to_process,
            max_cordis_results
        )
        
        # Enhance the answer with context
        if conversation_context.discussed_projects:
            enhanced_answer = self._enhance_answer_with_context(
                response['answer'],
                conversation_context,
                resolved_question
            )
            response['answer'] = enhanced_answer
        
        # Add context information to response
        response['context_used'] = True
        response['resolved_question'] = resolved_question
        response['discussed_projects'] = [
            asdict(p) for p in conversation_context.discussed_projects
        ]
        
        # Generate follow-up suggestions
        response['follow_up_suggestions'] = context_service.generate_follow_up_suggestions(
            conversation_context,
            response
        )
        
        return response

    def _build_context_prompt(self, context) -> str:
        """Build context information for the prompt"""
        
        prompt_parts = []
        
        # Add recent conversation history
        recent_messages = context.get_recent_messages(5)
        if recent_messages:
            prompt_parts.append("Recent conversation:")
            for msg in recent_messages:
                sender = msg['sender']
                text = msg['text'][:200]  # Truncate long messages
                prompt_parts.append(f"  {sender}: {text}")
        
        # Add discussed projects
        if context.discussed_projects:
            prompt_parts.append("\nProjects discussed:")
            for proj in context.discussed_projects[-5:]:  # Last 5 projects
                prompt_parts.append(f"  - {proj.acronym}: {proj.title}")
        
        # Add topics of interest
        if context.topics_of_interest:
            prompt_parts.append(f"\nTopics of interest: {', '.join(context.topics_of_interest)}")
        
        return "\n".join(prompt_parts)

    def _enhance_answer_with_context(
        self,
        base_answer: str,
        context,
        question: str
    ) -> str:
        """Enhance answer with conversational context"""
        
        # Create context-aware prompt
        enhancement_prompt = f"""
You are continuing a conversation about European research projects.

CONVERSATION CONTEXT:
{self._build_context_prompt(context)}

CURRENT QUESTION: {question}

BASE ANSWER: {base_answer}

Please enhance this answer by:
1. Referencing previously discussed projects when relevant
2. Making connections to topics already explored
3. Using natural language that acknowledges the conversation history
4. Avoiding repetition of information already provided
5. Suggesting natural follow-up questions

Enhanced answer:
"""
        
        # Call LLM for enhancement
        enhanced = self._call_llm_for_generation(
            "You are a conversational AI assistant that maintains context across messages.",
            enhancement_prompt
        )
        
        return enhanced
    async def get_ai_response_stream_with_context(
        self,
        question: str,
        conversation_context,
        max_projects_to_process: int = 5,
        max_cordis_results: int = 10
    ):
        """
        Stream AI response with conversation context and real-time stage updates.
        """
        total_start_time = time.time()
        
        try:
            # Phase 1: Context Resolution
            yield {'type': 'progress', 'phase': 'context_resolution', 'message': 'Resolving references and loading context...'}
            
            from app.services.conversation_context_service import ConversationContextService
            context_service = ConversationContextService(os.getenv("DATABASE_URL"))
            
            # Handle tuple return from resolve_references
            resolution_result = context_service.resolve_references(question, conversation_context)
            if isinstance(resolution_result, tuple):
                resolved_question, needs_detailed_lookup = resolution_result
            else:
                resolved_question = resolution_result
                needs_detailed_lookup = False
            
            if resolved_question != question:
                yield {'type': 'progress', 'phase': 'reference_resolved', 'message': f'Resolved: "{resolved_question}"'}
            
            # Phase 2: Intent Detection
            yield {'type': 'progress', 'phase': 'intent_detection', 'message': 'Analyzing question intent...'}

            from app.services.intent_service import IntentService
            user_intent, confidence = IntentService.determine_intent(resolved_question)
            yield {'type': 'progress', 'phase': 'intent_detected', 'message': f'Intent: {user_intent} (confidence: {confidence:.2f})'}
            
            # Phase 3: Query Extraction
            yield {'type': 'progress', 'phase': 'query_extraction', 'message': 'Extracting search queries...'}
            
            role, quest = self._get_phase1_prompt(resolved_question)
            queries, end_flag, new_query_keys, rerank_criteria, problem_text, next_pass = self._extract_queries(role, quest)
            
            if end_flag:
                yield {'type': 'error', 'error': 'Query processing failed', 'details': problem_text}
                return
            
            yield {'type': 'progress', 'phase': 'queries_extracted', 'message': f'Generated {len(queries)} search queries'}
            
            # Phase 4: Data Retrieval
            if user_intent == "SEARCH_PROJECTS":
                yield {'type': 'progress', 'phase': 'data_retrieval', 'message': 'Searching CORDIS API and enriching with database...'}
                
                # Use hybrid search
                try:
                    from app.services.hybrid_search_service import HybridSearchService
                    hybrid_search = HybridSearchService()
                    project_data = hybrid_search.search_projects(queries, max_results=max_cordis_results)
                    
                    enriched_count = sum(1 for p in project_data if p.get('enrichment_status') == 'complete')
                    yield {'type': 'progress', 'phase': 'data_enriched', 'message': f'Found {len(project_data)} projects, enriched {enriched_count} with database'}
                    
                    # Select best projects
                    if len(project_data) > max_projects_to_process:
                        project_data = self._adaptive_result_selection(project_data, resolved_question, max_projects_to_process)
                        yield {'type': 'progress', 'phase': 'data_selected', 'message': f'Selected {len(project_data)} most relevant projects'}
                    
                except ImportError:
                    yield {'type': 'progress', 'phase': 'fallback_search', 'message': 'Using fallback search method...'}
                    project_items = self._search_cordis_api(queries, max_results=max_cordis_results)
                    project_data = [self._extract_project_data(item) for item in project_items[:max_projects_to_process]]
                
                # Phase 5: Reranking (if needed)
                if rerank_criteria and len(project_data) > 1:
                    yield {'type': 'progress', 'phase': 'reranking', 'message': 'Reranking projects by relevance...'}
                    project_data = self._enhanced_rerank_projects(project_data, rerank_criteria, resolved_question, role)
                
                # Phase 6: Answer Generation with Streaming
                yield {'type': 'progress', 'phase': 'answer_generation', 'message': 'Generating comprehensive answer...'}
                
                # Build context-aware prompt
                context_prompt = self._build_context_prompt(conversation_context)
                
                # Generate base answer
                base_answer = self._generate_enhanced_answer(role, resolved_question, project_data)
                
                # Enhance with context if available
                if conversation_context.discussed_projects:
                    yield {'type': 'progress', 'phase': 'context_enhancement', 'message': 'Enhancing answer with conversation context...'}
                    enhanced_answer = self._enhance_answer_with_context(base_answer, conversation_context, resolved_question)
                    final_answer = enhanced_answer
                else:
                    final_answer = base_answer
                
                # Stream the final answer
                yield {'type': 'progress', 'phase': 'streaming_response', 'message': 'Streaming response...'}
                
                # Stream answer in chunks for better UX
                chunk_size = 50  # Characters per chunk
                for i in range(0, len(final_answer), chunk_size):
                    chunk = final_answer[i:i+chunk_size]
                    yield {'type': 'token', 'content': chunk}
                    await asyncio.sleep(0.01)  # Small delay for smooth streaming
                
                # Send completion
                total_time = time.time() - total_start_time
                yield {
                    'type': 'complete',
                    'answer': final_answer,
                    'context_used': True,
                    'resolved_question': resolved_question,
                    'projects_found': len(project_data),
                    'processing_time': round(total_time, 2),
                    'data_source': "CORDIS API + Local Database" if any(p.get('enrichment_status') == 'complete' for p in project_data) else "CORDIS API"
                }
                
            else:
                # Handle FAQ and SEARCH_CALLS with basic streaming
                yield {'type': 'progress', 'phase': 'processing_query', 'message': f'Processing {user_intent} query...'}
                
                response = self.get_ai_response_with_routing(
                    resolved_question,
                    max_projects_to_process,
                    max_cordis_results
                )
                
                # Stream the answer
                answer = response['answer']
                chunk_size = 50
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i+chunk_size]
                    yield {'type': 'token', 'content': chunk}
                    await asyncio.sleep(0.01)
                
                # Send completion
                total_time = time.time() - total_start_time
                yield {
                    'type': 'complete',
                    'answer': answer,
                    'context_used': False,
                    'resolved_question': resolved_question,
                    'processing_time': round(total_time, 2),
                    'data_source': response.get('data_source', 'Unknown')
                }
            
        except Exception as e:
            yield {'type': 'error', 'error': 'Processing failed', 'details': str(e)}



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
                result = rag_local.get_ai_response(question, max_projects_to_process=3)
                elapsed = time.time() - start_time
                
                # Extract answer and logs from the new return format
                answer = result.get('answer', '') if isinstance(result, dict) else result
                logs = result.get('logs', {}) if isinstance(result, dict) else {}
                
                print(f"✅ Test {i} completed in {elapsed:.2f}s")
                print(f"Response length: {len(answer)} characters")
                print(f"Contains CORDIS links: {'cordis.europa.eu' in answer}")
                
                # Log information
                if logs:
                    print(f"Model used: {logs.get('model_used', 'Unknown')}")
                    print(f"Projects retrieved: {logs.get('projects_retrieved', 0)}")
                    print(f"Projects processed: {logs.get('projects_processed', 0)}")
                    print(f"Pipeline phases: {len(logs.get('phases', []))}")
                
                # Show a snippet of the response
                print(f"Response preview: {answer[:200]}...")
                
            return True
            
        except Exception as e:
            print(f"❌ Local database test failed: {e}")
            return False
    
    def compare_performance():
        """Compare performance between local database and API"""
        print("="*60)
        print("PERFORMANCE COMPARISON: LOCAL DB vs CORDIS API")
        def get_ai_response_with_context(
            self,
            question: str,
            conversation_context,
            max_projects_to_process: int = 5,
            max_cordis_results: int = 10
        ) -> Dict[str, Any]:
            """
            Process question with conversation context.
            This is the context-aware version of get_ai_response.
            """
            
            # Resolve references in the question
            from app.services.conversation_context_service import ConversationContextService
            context_service = ConversationContextService(os.getenv("DATABASE_URL"))
            resolved_question = context_service.resolve_references(question, conversation_context)
            
            print(f"🧠 Original question: {question}")
            print(f"🎯 Resolved question: {resolved_question}")
            
            # Build context-aware prompt
            context_prompt = self._build_context_prompt(conversation_context)
            
            # Get the base response using existing method
            response = self.get_ai_response_with_routing(
                resolved_question,
                max_projects_to_process,
                max_cordis_results
            )
            
            # Enhance the answer with context
            if conversation_context.discussed_projects:
                enhanced_answer = self._enhance_answer_with_context(
                    response['answer'],
                    conversation_context,
                    resolved_question
                )
                response['answer'] = enhanced_answer
            
            # Add context information to response
            response['context_used'] = True
            response['resolved_question'] = resolved_question
            response['discussed_projects'] = [
                asdict(p) for p in conversation_context.discussed_projects
            ]
            
            # Generate follow-up suggestions
            response['follow_up_suggestions'] = context_service.generate_follow_up_suggestions(
                conversation_context,
                response
            )
            
            return response
    
        def _build_context_prompt(self, context) -> str:
            """Build context information for the prompt"""
            
            prompt_parts = []
            
            # Add recent conversation history
            recent_messages = context.get_recent_messages(5)
            if recent_messages:
                prompt_parts.append("Recent conversation:")
                for msg in recent_messages:
                    sender = msg['sender']
                    text = msg['text'][:200]  # Truncate long messages
                    prompt_parts.append(f"  {sender}: {text}")
            
            # Add discussed projects
            if context.discussed_projects:
                prompt_parts.append("\nProjects discussed:")
                for proj in context.discussed_projects[-5:]:  # Last 5 projects
                    prompt_parts.append(f"  - {proj.acronym}: {proj.title}")
            
            # Add topics of interest
            if context.topics_of_interest:
                prompt_parts.append(f"\nTopics of interest: {', '.join(context.topics_of_interest)}")
            
            return "\n".join(prompt_parts)
    
        def _enhance_answer_with_context(
            self,
            base_answer: str,
            context,
            question: str
        ) -> str:
            """Enhance answer with conversational context"""
            
            # Create context-aware prompt
            enhancement_prompt = f"""
    You are continuing a conversation about European research projects.
    
    CONVERSATION CONTEXT:
    {self._build_context_prompt(context)}
    
    CURRENT QUESTION: {question}
    
    BASE ANSWER: {base_answer}
    
    Please enhance this answer by:
    1. Referencing previously discussed projects when relevant
    2. Making connections to topics already explored
    3. Using natural language that acknowledges the conversation history
    4. Avoiding repetition of information already provided
    5. Suggesting natural follow-up questions
    
    Enhanced answer:
    """
            
            # Call LLM for enhancement
            enhanced = self._call_llm_for_generation(
                "You are a conversational AI assistant that maintains context across messages.",
                enhancement_prompt
            )
            
            return enhanced
    
        print("="*60)
        
        question = "machine learning projects in healthcare"
        
        try:
            # Test local database
            print("\n🔍 Testing Local Database...")
            rag_local = CordisRAG(use_local_db=True)
            start_time = time.time()
            result_local = rag_local.get_ai_response(question, max_projects_to_process=3)
            local_time = time.time() - start_time
            
            # Extract answer from new return format
            response_local = result_local.get('answer', '') if isinstance(result_local, dict) else result_local
            logs_local = result_local.get('logs', {}) if isinstance(result_local, dict) else {}
            
            print(f"✅ Local DB completed in {local_time:.2f}s")
            print(f"Local response length: {len(response_local)} characters")
            if logs_local:
                print(f"Projects retrieved: {logs_local.get('projects_retrieved', 0)}")
                print(f"Pipeline phases: {len(logs_local.get('phases', []))}")
            
            # Test CORDIS API
            print("\n🌐 Testing CORDIS API...")
            rag_api = CordisRAG(use_local_db=False)
            start_time = time.time()
            result_api = rag_api.get_ai_response(question, max_projects_to_process=3, max_cordis_results=5)
            api_time = time.time() - start_time
            
            # Extract answer from new return format
            response_api = result_api.get('answer', '') if isinstance(result_api, dict) else result_api
            logs_api = result_api.get('logs', {}) if isinstance(result_api, dict) else {}
            
            print(f"✅ CORDIS API completed in {api_time:.2f}s")
            print(f"API response length: {len(response_api)} characters")
            if logs_api:
                print(f"Projects retrieved: {logs_api.get('projects_retrieved', 0)}")
                print(f"Pipeline phases: {len(logs_api.get('phases', []))}")
            
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
