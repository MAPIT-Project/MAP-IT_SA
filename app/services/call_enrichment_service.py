"""
Call Enrichment Service

Fetches complete call details from the EU Funding & Tenders Portal API
when local data is incomplete. Caches results for future queries.

Strategy:
1. Check local `funding_calls` table first
2. If data is incomplete (missing scope, budget, deadline), fetch from API
3. Cache the enriched data for next time
"""

import logging
import re
import httpx
from typing import Dict, Any, Optional, List
from datetime import date, datetime
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# EU Portal API endpoints
EU_PORTAL_BASE = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
EU_PORTAL_TOPIC_DETAILS = "https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails"


class CallEnrichmentService:
    """
    Service to enrich call data from the EU Portal API.
    
    Fetches missing information (scope, budget, deadlines) and caches it locally.
    """
    
    def __init__(self, db_url: str):
        """Initialize with database connection."""
        self.db_url = db_url
        self._client = None
        logger.info("✅ CallEnrichmentService initialized")
    
    @property
    def client(self):
        """Lazy-load HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client
    
    def get_call_details(self, topic_code: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get complete call details, fetching from API if needed.
        
        Args:
            topic_code: The call identifier (e.g., HORIZON-CL5-2025-D3-01)
            force_refresh: If True, always fetch from API even if local data exists
            
        Returns:
            Complete call details dictionary
        """
        topic_code = topic_code.upper().strip()
        
        # Step 1: Check local database
        if not force_refresh:
            local_data = self._get_local_call(topic_code)
            if local_data and self._is_complete(local_data):
                logger.info(f"✅ Found complete local data for {topic_code}")
                return local_data
        
        # Step 2: Fetch from EU Portal API
        logger.info(f"🌐 Fetching {topic_code} from EU Portal API...")
        api_data = self._fetch_from_api(topic_code)
        
        if api_data:
            # Step 3: Cache the enriched data
            self._cache_call(topic_code, api_data)
            logger.info(f"✅ Cached enriched data for {topic_code}")
            return api_data
        
        # Fall back to local data if API failed
        local_data = self._get_local_call(topic_code)
        if local_data:
            logger.warning(f"⚠️ API fetch failed, using local data for {topic_code}")
            return local_data
        
        return None
    
    def enrich_search_results(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich a list of search results with complete data.
        
        Only fetches from API for calls that are missing critical info.
        """
        enriched = []
        
        for call in calls:
            topic_code = call.get('topic_code')
            if not topic_code:
                enriched.append(call)
                continue
            
            # Check if this call needs enrichment
            if self._needs_enrichment(call):
                full_data = self.get_call_details(topic_code)
                if full_data:
                    # Merge enriched data
                    call = {**call, **full_data}
            
            enriched.append(call)
        
        return enriched
    
    def _is_complete(self, call: Dict[str, Any]) -> bool:
        """Check if call has all important fields."""
        required_fields = ['scope', 'title']
        
        for field in required_fields:
            if not call.get(field) or len(str(call[field])) < 20:
                return False
        
        return True
    
    def _needs_enrichment(self, call: Dict[str, Any]) -> bool:
        """Check if a call needs to be enriched."""
        # Missing or very short scope
        scope = call.get('scope') or call.get('description') or ''
        if len(scope) < 50:
            return True
        
        # Missing deadline for current/upcoming calls
        if not call.get('deadline'):
            year = call.get('call_year') or call.get('year')
            if year and int(year) >= date.today().year:
                return True
        
        return False
    
    def _get_local_call(self, topic_code: str) -> Optional[Dict[str, Any]]:
        """Get call from local database."""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM funding_calls 
                WHERE topic_code = %s
            """, (topic_code,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            return None
    
    def _fetch_from_api(self, topic_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch call details from EU Portal API.

        First tries the direct topic details endpoint, then falls back to search API.
        """
        # Try direct topic details endpoint first (simpler and more reliable)
        direct_result = self._fetch_direct_topic_details(topic_code)
        if direct_result:
            return direct_result

        # Fall back to search API
        return self._fetch_via_search_api(topic_code)

    def _fetch_direct_topic_details(self, topic_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch topic details directly from the EU Portal topic details JSON endpoint.

        This endpoint returns complete details for a specific topic by ID.
        """
        try:
            # The EU Portal has a direct JSON endpoint for topic details
            # Format: https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails/{topic_code}.json
            # IMPORTANT: The endpoint requires LOWERCASE topic codes
            url = f"{EU_PORTAL_TOPIC_DETAILS}/{topic_code.lower()}.json"
            logger.info(f"📡 Fetching direct topic details from: {url}")

            response = self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                topic_data = data.get('TopicDetails', {})

                if topic_data:
                    logger.info(f"✅ Got direct topic details for {topic_code}")

                    # Extract deadline
                    deadline = None
                    deadline_model = topic_data.get('deadlineModel', [])
                    if deadline_model and isinstance(deadline_model, list) and len(deadline_model) > 0:
                        deadline_str = deadline_model[0].get('deadlineDate', '')
                        if deadline_str:
                            try:
                                # Parse ISO format date
                                if 'T' in deadline_str:
                                    deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00')).date()
                                else:
                                    deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
                            except Exception as e:
                                logger.debug(f"Could not parse deadline: {e}")

                    # Determine status from statusOfTopic
                    status_data = topic_data.get('statusOfTopic', {})
                    status_abbr = status_data.get('abbreviation', '').lower() if isinstance(status_data, dict) else str(status_data).lower()
                    if 'open' in status_abbr:
                        status = 'open'
                    elif 'closed' in status_abbr:
                        status = 'closed'
                    elif 'forthcoming' in status_abbr or 'upcoming' in status_abbr:
                        status = 'upcoming'
                    else:
                        status = 'closed'  # Default to closed for past calls

                    # Extract budget
                    budget = None
                    budget_data = topic_data.get('budgetOverviewModel', {})
                    if budget_data:
                        budget = budget_data.get('budgetTopicActionValue')

                    # Extract action type
                    action_type_data = topic_data.get('typeOfMGA', [])
                    action_type = ''
                    if action_type_data and isinstance(action_type_data, list) and len(action_type_data) > 0:
                        action_type = action_type_data[0].get('abbreviation', '')

                    return {
                        'topic_code': topic_data.get('identifier', topic_code).upper(),
                        'title': topic_data.get('title', ''),
                        'scope': topic_data.get('description', ''),
                        'expected_outcome': topic_data.get('expectedImpact', ''),
                        'deadline': deadline,
                        'status': status,
                        'action_type': action_type,
                        'budget': budget,
                        'budget_total': Decimal(str(budget)) if budget else None,
                        'call_identifier': topic_data.get('callIdentifier'),
                        'portal_url': f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{topic_code.lower()}",
                        'enriched_from_api': True,
                        'enriched_at': datetime.now().isoformat(),
                    }

            logger.info(f"Direct topic details endpoint returned {response.status_code} for {topic_code}")
            return None

        except Exception as e:
            logger.warning(f"Direct topic details fetch failed for {topic_code}: {e}")
            return None

    def _fetch_via_search_api(self, topic_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch call details via the EU Portal search API.

        Uses multipart POST approach.
        """
        try:
            import json

            # Build search query - include all statuses to find the call
            search_query = {
                "bool": {
                    "must": [
                        {
                            "bool": {
                                "must": [
                                    {"terms": {"type": ["1", "2", "8"]}},
                                    # Include all statuses to find any call
                                    {"terms": {"status": ["31094501", "31094502", "31094503"]}}
                                ]
                            }
                        },
                        {
                            "bool": {
                                "should": [
                                    {"phrase": {"query": topic_code, "field": "identifier", "phraseSlop": 0, "boost": 1100}},
                                    {"phrase": {"query": topic_code, "field": "title", "phraseSlop": 1, "boost": 500}},
                                ]
                            }
                        }
                    ]
                }
            }
            
            # Prepare form data
            form_data = {
                "apiKey": "SEDIA",
                "text": topic_code,  # Use exact topic code
                "pageSize": "10",
                "pageNumber": "1",
            }
            
            files = {
                "query": (None, json.dumps(search_query), "application/json"),
                "sort": (None, json.dumps({"order": "DESC", "field": "relevance"}), "application/json"),
            }
            
            response = self.client.post(
                EU_PORTAL_BASE,
                data=form_data,
                files=files
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                logger.info(f"API returned {len(results)} results for {topic_code}")

                # Find matching topic - try exact match first, then partial
                for result in results:
                    metadata = result.get('metadata', {})
                    # metadata values are lists, get first item
                    identifiers = metadata.get('identifier', [])
                    if identifiers:
                        result_id = identifiers[0].upper() if isinstance(identifiers, list) else str(identifiers).upper()
                        # Exact match
                        if result_id == topic_code.upper():
                            logger.info(f"✅ Found exact match for {topic_code}")
                            return self._parse_search_result(result, topic_code)

                # Try partial match (topic_code contained in identifier or vice versa)
                for result in results:
                    metadata = result.get('metadata', {})
                    identifiers = metadata.get('identifier', [])
                    if identifiers:
                        result_id = identifiers[0].upper() if isinstance(identifiers, list) else str(identifiers).upper()
                        if topic_code.upper() in result_id or result_id in topic_code.upper():
                            logger.info(f"✅ Found partial match: {result_id} for {topic_code}")
                            return self._parse_search_result(result, topic_code)

                # If no match but we have results, use the first one as fallback
                if results:
                    first_id = results[0].get('metadata', {}).get('identifier', ['unknown'])[0]
                    logger.info(f"⚠️ No exact match for {topic_code}, using closest result: {first_id}")
                    return self._parse_search_result(results[0], topic_code)
            
            logger.warning(f"API returned status {response.status_code} for {topic_code}")
            return None
            
        except Exception as e:
            logger.error(f"API fetch error for {topic_code}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_api_response(self, data: Dict[str, Any], topic_code: str) -> Dict[str, Any]:
        """Parse the topic details API response."""
        # The API response structure varies, handle different formats
        topic_data = data.get('topicDetails', data)
        
        # Extract deadline
        deadline = None
        deadlines = topic_data.get('deadlineDates', [])
        if deadlines:
            deadline_str = deadlines[0] if isinstance(deadlines[0], str) else deadlines[0].get('date')
            if deadline_str:
                try:
                    deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00')).date()
                except:
                    pass
        
        # Extract budget
        budget = None
        budget_info = topic_data.get('budget', {})
        if isinstance(budget_info, dict):
            budget = budget_info.get('budgetTopicActionValue')
        elif isinstance(budget_info, (int, float)):
            budget = budget_info
        
        # Determine status
        status_code = topic_data.get('status', {})
        if isinstance(status_code, dict):
            status_str = status_code.get('abbreviation', '').lower()
        else:
            status_str = str(status_code).lower()
        
        if 'open' in status_str:
            status = 'open'
        elif 'closed' in status_str:
            status = 'closed'
        elif 'forthcoming' in status_str or 'upcoming' in status_str:
            status = 'upcoming'
        else:
            status = 'unknown'
        
        return {
            'topic_code': topic_code,
            'title': topic_data.get('title', topic_code),
            'scope': topic_data.get('description', ''),
            'expected_outcome': topic_data.get('expectedImpact', ''),
            'deadline': deadline,
            'status': status,
            'budget_total': Decimal(str(budget)) if budget else None,
            'action_type': topic_data.get('actionType', {}).get('abbreviation'),
            'call_identifier': topic_data.get('callIdentifier'),
            'portal_url': f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{topic_code}",
            'enriched_from_api': True,
            'enriched_at': datetime.now().isoformat(),
        }
    
    def _parse_search_result(self, result: Dict[str, Any], topic_code: str) -> Dict[str, Any]:
        """Parse a search API result."""
        # Metadata is a dict where values are lists
        metadata = result.get('metadata', {})
        
        def get_first(key: str, default: str = '') -> str:
            """Get first value from metadata list."""
            val = metadata.get(key, [default])
            if isinstance(val, list):
                return val[0] if val else default
            return val or default
        
        # Extract fields - metadata values are lists, take first item
        identifier = get_first('identifier', topic_code)
        title = get_first('title') or get_first('callTitle') or result.get('title', topic_code)
        description = get_first('description') or get_first('esSummary') or result.get('summary', '')
        deadline_str = get_first('deadlineDate', '')
        status_code = get_first('status', '')
        
        # Parse deadline
        deadline = None
        if deadline_str:
            try:
                # Handle ISO format: 2024-10-01T22:00:00.000+0000
                if 'T' in deadline_str:
                    # Remove timezone for simpler parsing
                    clean_date = deadline_str.split('T')[0]
                    deadline = datetime.strptime(clean_date, '%Y-%m-%d').date()
                else:
                    deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except Exception as e:
                logger.debug(f"Could not parse deadline '{deadline_str}': {e}")
        
        # Map status code to string
        status_map = {
            '31094501': 'upcoming',  # Forthcoming
            '31094502': 'open',      # Open
            '31094503': 'closed',    # Closed
        }
        status = status_map.get(status_code, 'unknown')

        # Map typeOfMGAs numeric IDs to action type abbreviations
        # These IDs come from the EU Portal search API metadata
        action_type_map = {
            '43027843': 'RIA',       # Research and Innovation Action
            '43027844': 'IA',        # Innovation Action
            '43027845': 'CSA',       # Coordination and Support Action
            '43027846': 'LUMP-SUM',  # Lump Sum
            '43027847': 'PCP',       # Pre-Commercial Procurement
            '43027848': 'PPI',       # Public Procurement of Innovation
            '43027849': 'LUMP-SUM',  # Lump Sum (alternative ID)
            '43027850': 'COFUND',    # Co-fund
        }
        raw_action_type = get_first('typeOfMGAs')
        action_type = action_type_map.get(raw_action_type, raw_action_type if not raw_action_type.isdigit() else '')

        logger.info(f"✅ Parsed API result: {identifier} - {title[:50] if title else 'No title'}...")

        return {
            'topic_code': identifier.upper() if identifier else topic_code.upper(),
            'title': title,
            'scope': description,
            'expected_outcome': '',  # Not in search results
            'deadline': deadline,
            'status': status,
            'action_type': action_type,
            'call_identifier': get_first('callIdentifier'),
            'portal_url': f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{identifier or topic_code}",
            'enriched_from_api': True,
            'enriched_at': datetime.now().isoformat(),
        }
    
    def _cache_call(self, topic_code: str, data: Dict[str, Any]) -> bool:
        """Cache enriched call data to database."""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # Upsert the call data
            cursor.execute("""
                INSERT INTO funding_calls (
                    programme, topic_code, title, scope, expected_outcome,
                    deadline, status, budget_total, action_type,
                    call_identifier, portal_url, metadata
                ) VALUES (
                    'horizon_europe', %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s::jsonb
                )
                ON CONFLICT (topic_code) DO UPDATE SET
                    title = COALESCE(EXCLUDED.title, funding_calls.title),
                    scope = COALESCE(EXCLUDED.scope, funding_calls.scope),
                    expected_outcome = COALESCE(EXCLUDED.expected_outcome, funding_calls.expected_outcome),
                    deadline = COALESCE(EXCLUDED.deadline, funding_calls.deadline),
                    status = COALESCE(EXCLUDED.status, funding_calls.status),
                    budget_total = COALESCE(EXCLUDED.budget_total, funding_calls.budget_total),
                    action_type = COALESCE(EXCLUDED.action_type, funding_calls.action_type),
                    portal_url = COALESCE(EXCLUDED.portal_url, funding_calls.portal_url),
                    metadata = funding_calls.metadata || EXCLUDED.metadata,
                    updated_at = NOW()
            """, (
                topic_code,
                data.get('title'),
                data.get('scope'),
                data.get('expected_outcome'),
                data.get('deadline'),
                data.get('status', 'unknown'),
                float(data['budget_total']) if data.get('budget_total') else None,
                data.get('action_type'),
                data.get('call_identifier'),
                data.get('portal_url'),
                '{"enriched_from_api": true}'
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Cache error for {topic_code}: {e}")
            return False
    
    def close(self):
        """Close HTTP client."""
        if self._client:
            self._client.close()

