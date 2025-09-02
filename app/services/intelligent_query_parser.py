"""
Intelligent Query Parser for Enhanced Call Search

Parses user queries to detect filter intentions:
- Status filters: "open calls", "closed calls", "forthcoming calls"
- Temporal filters: "recent calls", "latest calls", "new calls"
- Provides appropriate API filtering and user messaging
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class QueryFilters:
    """Container for parsed query filters."""
    status_filter: Optional[List[str]] = None  # Status codes to include
    date_filter: Optional[Dict[str, str]] = None  # Date range filters
    filter_intention: str = "all"  # "open_only", "recent_only", "all", etc.
    original_query: str = ""
    clean_query: str = ""  # Query with filter words removed
    user_intent_detected: List[str] = None  # What user specifically asked for

class IntelligentQueryParser:
    """Parses user queries to extract filter intentions."""
    
    def __init__(self):
        """Initialize the query parser."""
        
        # Status-related keywords
        self.status_keywords = {
            'open': {
                'patterns': [r'\bopen\s+calls?\b', r'\bcalls?\s+that\s+are\s+open\b', r'\bavailable\s+calls?\b', r'\bcurrently\s+open\b'],
                'codes': ['31094502'],  # Open only
                'intention': 'open_only'
            },
            'closed': {
                'patterns': [r'\bclosed\s+calls?\b', r'\bcalls?\s+that\s+are\s+closed\b', r'\bexpired\s+calls?\b'],
                'codes': ['31094503'],  # Closed only
                'intention': 'closed_only'
            },
            'forthcoming': {
                'patterns': [r'\bforthcoming\s+calls?\b', r'\bupcoming\s+calls?\b', r'\bfuture\s+calls?\b'],
                'codes': ['31094501'],  # Forthcoming only
                'intention': 'forthcoming_only'
            },
            'available': {
                'patterns': [r'\bavailable\s+calls?\b', r'\bcurrent\s+opportunities\b'],
                'codes': ['31094501', '31094502'],  # Open + Forthcoming
                'intention': 'available_only'
            }
        }
        
        # Temporal keywords
        self.temporal_keywords = {
            'recent': {
                'patterns': [r'\brecent\s+calls?\b', r'\blatest\s+calls?\b', r'\bnew\s+calls?\b'],
                'months_back': 6,
                'intention': 'recent_only'
            },
            'very_recent': {
                'patterns': [r'\bvery\s+recent\b', r'\bmost\s+recent\b', r'\bnewest\b'],
                'months_back': 3,
                'intention': 'very_recent_only'
            },
            'this_year': {
                'patterns': [r'\bthis\s+year\b', r'\b2025\b', r'\bcurrent\s+year\b'],
                'months_back': 12,
                'intention': 'current_year'
            }
        }
        
        logger.info("✅ Intelligent query parser initialized")
    
    def parse_query(self, query: str) -> QueryFilters:
        """Parse user query to extract filter intentions."""
        
        original_query = query.strip()
        query_lower = query.lower()
        clean_query = original_query
        
        # Initialize filters
        status_codes = None
        date_filter = None
        filter_intention = "all"
        user_intent_detected = []
        
        logger.info(f"🔍 Parsing query: '{original_query}'")
        
        # Detect status filters
        for status_type, config in self.status_keywords.items():
            for pattern in config['patterns']:
                if re.search(pattern, query_lower):
                    status_codes = config['codes']
                    filter_intention = config['intention']
                    user_intent_detected.append(f"status:{status_type}")
                    
                    # Remove filter words from clean query
                    clean_query = re.sub(pattern, '', clean_query, flags=re.IGNORECASE).strip()
                    clean_query = re.sub(r'\s+', ' ', clean_query)  # Clean up extra spaces
                    
                    logger.info(f"🎯 Detected status filter: {status_type} -> codes {status_codes}")
                    break
            if status_codes:
                break
        
        # Detect temporal filters
        for temporal_type, config in self.temporal_keywords.items():
            for pattern in config['patterns']:
                if re.search(pattern, query_lower):
                    # Calculate date range
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=config['months_back'] * 30)
                    
                    date_filter = {
                        "gte": start_date.strftime('%Y-%m-%d'),
                        "lte": end_date.strftime('%Y-%m-%d')
                    }
                    
                    # Update intention if not already set by status
                    if filter_intention == "all":
                        filter_intention = config['intention']
                    
                    user_intent_detected.append(f"temporal:{temporal_type}")
                    
                    # Remove temporal words from clean query
                    clean_query = re.sub(pattern, '', clean_query, flags=re.IGNORECASE).strip()
                    clean_query = re.sub(r'\s+', ' ', clean_query)  # Clean up extra spaces
                    
                    logger.info(f"📅 Detected temporal filter: {temporal_type} -> last {config['months_back']} months")
                    break
            if date_filter:
                break
        
        # Clean up remaining filter artifacts
        clean_query = re.sub(r'\b(calls?|for|related\s+to)\b', '', clean_query, flags=re.IGNORECASE).strip()
        clean_query = re.sub(r'\s+', ' ', clean_query)  # Clean up extra spaces
        
        # If clean query is empty, use original
        if not clean_query or len(clean_query.strip()) < 3:
            clean_query = original_query
        
        filters = QueryFilters(
            status_filter=status_codes,
            date_filter=date_filter,
            filter_intention=filter_intention,
            original_query=original_query,
            clean_query=clean_query,
            user_intent_detected=user_intent_detected or ["no_filters"]
        )
        
        logger.info(f"✅ Parsed filters: {filter_intention}, clean query: '{clean_query}'")
        return filters
    
    def get_filter_explanation(self, filters: QueryFilters, results_count: int) -> str:
        """Generate explanation for filter results."""
        
        explanations = []
        
        if filters.filter_intention == "open_only":
            if results_count == 0:
                explanations.append("🔴 **No currently open calls found** - this is normal as EU calls follow scheduled cycles")
                explanations.append("💡 **Suggestion**: Check recent closed calls to see what types of calls are typically available")
            else:
                explanations.append(f"🟢 **{results_count} open calls found** - these are currently accepting applications")
        
        elif filters.filter_intention == "recent_only":
            if results_count == 0:
                explanations.append("📅 **No recent calls found** - may indicate a gap between call cycles")
            else:
                explanations.append(f"📅 **{results_count} recent calls found** - from the last 6 months")
        
        elif filters.filter_intention == "available_only":
            if results_count == 0:
                explanations.append("🔵 **No available calls** (open or forthcoming) found at this time")
            else:
                explanations.append(f"🔵 **{results_count} available calls** (open or forthcoming)")
        
        elif filters.filter_intention == "all":
            explanations.append(f"📊 **{results_count} total calls found** (includes open, closed, and forthcoming)")
        
        return " | ".join(explanations)

# Example usage
if __name__ == "__main__":
    parser = IntelligentQueryParser()
    
    test_queries = [
        "What are some open calls related to quantum mechanics?",
        "Recent calls for artificial intelligence",
        "Closed calls about renewable energy", 
        "Forthcoming opportunities in healthcare",
        "Available calls for climate change research"
    ]
    
    print("🧪 Testing Query Parser")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        filters = parser.parse_query(query)
        
        print(f"   Status filter: {filters.status_filter}")
        print(f"   Date filter: {filters.date_filter}")
        print(f"   Intention: {filters.filter_intention}")
        print(f"   Clean query: '{filters.clean_query}'")
        print(f"   User intent: {filters.user_intent_detected}")
        
        explanation = parser.get_filter_explanation(filters, 0)
        print(f"   Explanation: {explanation}")