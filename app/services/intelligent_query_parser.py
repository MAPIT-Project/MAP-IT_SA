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
            },
            'coming_soon': {
                'patterns': [r'\bcom+ing\s+up\s+soon\b', r'\bcom+ing\s+soon\b', r'\bupcoming\b', r'\bsoon\b'],
                'months_back': 12,
                'intention': 'forthcoming_only',
                'status_codes': ['31094501']  # Forthcoming status
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
                    
                    # Remove filter words from clean query - also remove common question words
                    clean_query = re.sub(pattern, '', clean_query, flags=re.IGNORECASE).strip()
                    
                    # Remove common question starters that might be left
                    question_starters = [r'\bwhat\s+are\s+some\s*', r'\bwhat\s+are\s*', r'\bshow\s+me\s*', r'\blist\s*', r'\bfind\s*']
                    for starter in question_starters:
                        clean_query = re.sub(starter, '', clean_query, flags=re.IGNORECASE).strip()
                    
                    clean_query = re.sub(r'\s+', ' ', clean_query)  # Clean up extra spaces
                    
                    logger.info(f"🎯 Detected status filter: {status_type} -> codes {status_codes}")
                    break
            if status_codes:
                break
        
        # Detect temporal filters
        for temporal_type, config in self.temporal_keywords.items():
            for pattern in config['patterns']:
                if re.search(pattern, query_lower):
                    # Special handling for "coming soon" - this should be status filter, not date filter
                    if temporal_type == 'coming_soon':
                        # Set status filter for forthcoming calls instead of date filter
                        if 'status_codes' in config:
                            status_codes = config['status_codes']
                            logger.info(f"🔜 Detected 'coming soon' -> setting status filter: {status_codes}")
                    else:
                        # Calculate date range for other temporal filters
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
                    
                    # Remove temporal words from clean query - also remove common question words
                    clean_query = re.sub(pattern, '', clean_query, flags=re.IGNORECASE).strip()
                    
                    # Remove common question starters that might be left
                    question_starters = [r'\bwhat\s+are\s+some\s*', r'\bwhat\s+are\s*', r'\bshow\s+me\s*', r'\blist\s*', r'\bfind\s*']
                    for starter in question_starters:
                        clean_query = re.sub(starter, '', clean_query, flags=re.IGNORECASE).strip()
                        
                    clean_query = re.sub(r'\s+', ' ', clean_query)  # Clean up extra spaces
                    
                    logger.info(f"📅 Detected temporal filter: {temporal_type} -> {config['intention']}")
                    break
            if date_filter or (temporal_type == 'coming_soon' and status_codes):
                break
        
        # ULTRA-SIMPLIFIED query cleaning - be very conservative to avoid breaking meaning
        working_query = clean_query
        
        # Only clean up basic punctuation and normalize spaces
        working_query = re.sub(r'[?!.,;:]', '', working_query)
        working_query = re.sub(r'\s+', ' ', working_query).strip()
        
        # For specific cases, extract obvious topics ONLY if we're confident
        topic_extracted = False
        
        # Pattern 1: "related to X" or "about X" - extract X
        topic_match = re.search(r'(?:related\s+to|about)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)', working_query, flags=re.IGNORECASE)
        if topic_match:
            topic = topic_match.group(1).strip()
            if len(topic) >= 3 and topic.lower() not in ['the', 'any', 'some', 'that', 'are', 'can', 'you', 'find']:
                working_query = topic
                topic_extracted = True
        
        # Pattern 2: Status-only queries (e.g., "what are some forthcoming calls?")
        if not topic_extracted and filter_intention in ['open_only', 'forthcoming_only', 'closed_only', 'available_only']:
            # For pure status queries, use broad search term
            working_query = "Horizon Europe"
            topic_extracted = True
        
        # If we didn't extract a specific topic, keep more of the original query
        if not topic_extracted:
            # Just remove obvious noise words but keep the core query intact
            noise_words = [r'\bcan\s+you\s+tell\s+me\s+', r'\bwhere\s+i\s+can\s+', r'\bwhat\s+are\s+some\s+']
            for noise in noise_words:
                working_query = re.sub(noise, '', working_query, flags=re.IGNORECASE).strip()
        
        clean_query = working_query
        
        # Final safety check
        if not clean_query or len(clean_query.strip()) < 2:
            clean_query = original_query  # Use original as last resort
        
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