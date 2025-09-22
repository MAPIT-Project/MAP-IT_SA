"""
Improved EU Portal Call Search Service
Based on the official API documentation for better results and reliability.

This service implements the direct approach used by the EU Funding & Tenders Portal:
- Simple, direct query construction using CCM2 codes
- No complex semantic analysis that reduces results
- Proper status code usage (31094501=Open, 31094502=Closed, etc.)
- Direct text search with minimal filtering
"""

import requests
import json
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import re

logger = logging.getLogger(__name__)

@dataclass
class SimpleSearchResult:
    """Simple search result with essential metadata."""
    identifier: str
    title: str
    description: str
    status: str
    deadline: str
    framework_programme: str
    url: str
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class ImprovedCallSearchService:
    """Improved call search service using direct EU portal API approach."""
    
    def __init__(self):
        """Initialize the improved search service."""
        self.search_api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
        self.facet_api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/facet"
        
        # Correct status code mapping based on actual API behavior
        self.status_mapping = {
            '31094501': 'Forthcoming', # Forthcoming calls (7 results)
            '31094502': 'Open',        # Open for submission (468 results) - CONFIRMED BY API
            '31094503': 'Closed',      # Closed calls (9664 results)
        }
        
        # Simple configuration - maximize results
        self.default_params = {
            "apiKey": "SEDIA",
            "pageSize": "100",  # Get maximum results per request
            "pageNumber": "1"
        }
        
        logger.info("✅ Improved call search service initialized")
    
    def search_calls_simple(
        self,
        query: str,
        max_results: int = 50,
        include_closed: bool = False,
        programme_period: str = "2021 - 2027"
    ) -> Dict[str, Any]:
        """
        Simple, direct search method that matches EU portal behavior.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            include_closed: Whether to include closed calls
            programme_period: Programme period filter
            
        Returns:
            Search results with metadata
        """
        
        start_time = time.time()
        logger.info(f"🚀 Simple search starting: '{query}'")
        
        try:
            # Step 1: Simplify query - remove complex natural language
            clean_query = self._simplify_query(query)
            logger.info(f"🔍 Query simplified: '{query}' → '{clean_query}'")
            
            # Step 2: Build simple query structure
            search_query = self._build_simple_query(clean_query, include_closed)
            
            # Step 3: Execute search
            search_results = self._execute_simple_search(search_query, max_results)
            
            # Step 4: Process results
            processed_results = self._process_simple_results(search_results, clean_query)
            
            # Step 4.1: Apply deadline-based status correction for data quality issues
            processed_results = self._correct_status_by_deadline(processed_results)
            
            # Step 5: Apply basic ranking
            ranked_results = self._apply_basic_ranking(processed_results, clean_query)
            
            # Limit results
            final_results = ranked_results[:max_results]
            
            elapsed_time = time.time() - start_time
            
            return {
                'results': final_results,
                'facets': {},  # Skip facet analysis for simplicity
                'search_metadata': {
                    'query': query,
                    'clean_query': clean_query,
                    'total_found': len(search_results),
                    'returned': len(final_results),
                    'processing_time': round(elapsed_time, 3),
                    'search_method': 'simple_direct'
                },
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"❌ Simple search failed: {e}")
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
    
    def _simplify_query(self, query: str) -> str:
        """
        Simple query cleaning - just basic whitespace normalization.
        AI intent service now handles keyword extraction, so we don't need complex pattern matching.
        """
        if not query:
            return ""
        
        # Basic cleaning - just normalize whitespace
        cleaned = re.sub(r'\s+', ' ', query).strip()
        
        return cleaned
    
    def _build_simple_query(self, query: str, include_closed: bool) -> Dict[str, Any]:
        """
        Build simple query structure matching EU portal approach.
        Uses direct CCM2 codes and minimal filtering.
        """
        
        # Base query structure - match EU portal exactly
        base_query = {
            "bool": {
                "must": [
                    {
                        "bool": {
                            "must": [
                                # Document types: 1=Grant, 2=Other, 8=Additional
                                {"terms": {"type": ["1", "2", "8"]}}
                            ]
                        }
                    }
                ]
            }
        }
        
        # Status filtering - use correct CCM2 codes based on API behavior
        if include_closed:
            # Include all statuses
            status_codes = ["31094501", "31094502", "31094503"]  # Forthcoming, Open, Closed
            logger.info("🎯 Including all call statuses")
        else:
            # Only open calls (correct code is 31094502 for open calls - CONFIRMED BY API)
            status_codes = ["31094502"]  # Open calls only
            logger.info("🎯 Including only open calls")
        
        base_query["bool"]["must"][0]["bool"]["must"].append(
            {"terms": {"status": status_codes}}
        )
        
        # Add text search if query exists - use phrase queries like enhanced service
        if query.strip():
            text_search_should = []
            
            # Use phrase queries with field-specific boosts like enhanced service
            fields_config = [
                {"field": "identifier", "phraseSlop": 0, "boost": 1100},
                {"field": "keywords", "phraseSlop": 0, "boost": 1000},
                {"field": "title", "phraseSlop": 1, "boost": 200},
                {"field": "description", "phraseSlop": 2, "boost": 100}
            ]
            
            for field_config in fields_config:
                text_search_should.append({
                    "phrase": {
                        "query": query,
                        "field": field_config["field"],
                        "phraseSlop": field_config["phraseSlop"],
                        "boost": field_config["boost"]
                    }
                })
            
            base_query["bool"]["must"].append({
                "bool": {
                    "should": text_search_should
                }
            })
        
        logger.debug(f"🔧 Built simple query with status filter: {status_codes}")
        logger.debug(f"🔧 Query structure: {json.dumps(base_query, indent=2)}")
        return base_query
    
    def _execute_simple_search(self, search_query: Dict[str, Any], max_results: int) -> List[Dict[str, Any]]:
        """Execute the simple search with the built query."""
        
        try:
            # Prepare search parameters - match enhanced service exactly
            params = dict(self.default_params)
            params["pageSize"] = str(min(max_results * 2, 100))
            params["text"] = "***"  # Use wildcard since we have structured query
            
            # Prepare multipart form data - match enhanced service format
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
            
            logger.debug(f"🔧 API Request URL: {self.search_api_url}")
            logger.debug(f"🔧 API Request Params: {params}")
            logger.debug(f"🔧 API Request Files keys: {list(files.keys())}")
            
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
                
                logger.info(f"🎯 Simple search returned {len(results)} results (total: {total_results})")
                return results
            
            logger.error(f"❌ Search API returned status {response.status_code}")
            logger.error(f"❌ Response content: {response.text}")
            
        except Exception as e:
            logger.error(f"❌ Simple search execution failed: {e}")
        
        return []
    
    def _process_simple_results(self, raw_results: List[Dict[str, Any]], query: str) -> List[SimpleSearchResult]:
        """Process raw results into simple result objects."""
        
        processed = []
        
        for result in raw_results:
            try:
                metadata = result.get('metadata', {})
                
                # Extract core information
                identifier = self._get_metadata_value(metadata, 'identifier', 'N/A')
                title = result.get('content', '') or result.get('summary', '') or 'Unknown Call'
                title = re.sub(r'<[^>]+>', '', title).strip()
                
                # Status information
                status_raw = self._get_metadata_value(metadata, 'status')
                status_readable = self.status_mapping.get(str(status_raw), f"Unknown ({status_raw})")
                
                # Date information
                deadline_raw = self._get_metadata_value(metadata, 'deadlineDate')
                deadline_formatted = self._format_deadline(deadline_raw)
                
                # Programme information
                framework_programme = self._get_metadata_value(metadata, 'frameworkProgramme', 'Horizon Europe')
                
                # Description
                description = self._build_simple_description(result, metadata, query)
                
                # Build URL
                url = self._build_call_url(identifier)
                
                # Create simple result
                simple_result = SimpleSearchResult(
                    identifier=identifier or 'N/A',
                    title=title or 'Unknown Call',
                    description=description or 'No description available',
                    status=status_readable or 'Unknown',
                    deadline=deadline_formatted or 'Not specified',
                    framework_programme=framework_programme or 'Horizon Europe',
                    url=url or 'https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home',
                    metadata=metadata or {}
                )
                
                processed.append(simple_result)
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to process result: {e}")
                continue
        
        logger.info(f"✅ Processed {len(processed)} simple results")
        return processed
    
    def _apply_basic_ranking(self, results: List[SimpleSearchResult], query: str) -> List[SimpleSearchResult]:
        """Apply basic ranking based on query relevance."""
        
        if len(results) <= 1:
            return results
        
        query_lower = query.lower()
        
        for result in results:
            score = 1.0  # Base score
            
            # Exact query match in title (high boost)
            if query_lower in result.title.lower():
                score *= 2.0
            
            # Exact query match in identifier
            if query_lower in result.identifier.lower():
                score *= 1.8
            
            # Status priority (open calls get higher scores)
            if result.status == 'Open':
                score *= 1.5
            elif result.status == 'Closing soon':
                score *= 1.2
            
            # Query words in description
            query_words = set(query_lower.split())
            desc_words = set(result.description.lower().split())
            keyword_overlap = len(query_words.intersection(desc_words))
            if keyword_overlap > 0:
                score *= 1 + (keyword_overlap * 0.1)
            
            result.score = score
        
        # Sort by enhanced scores
        ranked = sorted(results, key=lambda x: x.score, reverse=True)
        
        logger.info(f"📈 Applied basic ranking to {len(results)} results")
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
                return deadline_date.strftime('%B %d, %Y')
        except:
            pass
        
        return str(deadline_raw)
    
    def _build_simple_description(self, result: Dict[str, Any], metadata: Dict[str, Any], query: str) -> str:
        """Build a simple, informative description."""
        
        # Get the base title/content
        title = result.get('title', '') or result.get('content', '') or result.get('summary', '')
        title = re.sub(r'<[^>]+>', '', str(title)).strip()
        
        # Get programme info
        programme = self._get_metadata_value(metadata, 'frameworkProgramme', 'Horizon Europe')
        
        # Build simple description
        if title:
            return f"{programme} funding opportunity: {title}"
        else:
            return f"{programme} research funding opportunity"
    
    def _correct_status_by_deadline(self, results: List[SimpleSearchResult]) -> List[SimpleSearchResult]:
        """Correct call status based on deadline to handle data quality issues."""
        from datetime import datetime
        
        current_year = datetime.now().year
        
        for result in results:
            # Check if this is a 2021 call marked as open (data quality issue)
            if '2021' in result.identifier and result.status == 'Open':
                result.status = 'Closed (Data Corrected)'
                logger.info(f"🔧 Corrected status for {result.identifier}: Open → Closed (2021 call)")
            
            # Also check deadline dates for past calls marked as open
            if result.deadline and result.deadline != 'Not specified':
                try:
                    # Parse the deadline to check if it's in the past
                    if 'T' in result.deadline:
                        deadline_date = datetime.strptime(result.deadline.split('T')[0], '%Y-%m-%d')
                        if deadline_date.year < current_year and result.status == 'Open':
                            result.status = 'Closed (Past Deadline)'
                            logger.info(f"🔧 Corrected status for {result.identifier}: Past deadline")
                except:
                    pass
        
        return results

    def _build_call_url(self, identifier: str) -> str:
        """Build proper EU portal URL for the call."""
        if identifier and identifier != 'N/A':
            return (
                f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
                f"screen/opportunities/topic-details/{identifier}?keywords={identifier}"
            )
        
        return "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/opportunities-tenders"

# Test function
def test_improved_search():
    """Test the improved search functionality."""
    print("🧪 Testing Improved Call Search Service")
    print("=" * 60)
    
    service = ImprovedCallSearchService()
    
    # Test the problematic query
    test_query = "please search calls about clean energy"
    
    print(f"\n🔍 Testing: '{test_query}'")
    print("-" * 40)
    
    start_time = time.time()
    result = service.search_calls_simple(
        query=test_query,
        max_results=10,
        include_closed=False
    )
    elapsed = time.time() - start_time
    
    if result['status'] == 'success':
        print(f"✅ Found {len(result['results'])} results in {elapsed:.2f}s")
        print(f"📊 Search method: {result['search_metadata']['search_method']}")
        
        # Show results
        for i, res in enumerate(result['results'][:3], 1):
            print(f"\n{i}. {res.title}")
            print(f"   Status: {res.status}")
            print(f"   Deadline: {res.deadline}")
            print(f"   Score: {res.score:.3f}")
    else:
        print(f"❌ Search failed: {result.get('search_metadata', {}).get('error', 'Unknown error')}")
    
    print("\n🎉 Improved search testing completed!")

if __name__ == "__main__":
    test_improved_search()