"""
AI-Powered Query Parser using Gemini 2.5 Flash
Enhanced version with comprehensive prompt for better intent detection
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
import json
import os
from dotenv import load_dotenv

try:
    from google import genai as google_genai_sdk
    from google.genai import types
except ImportError:
    google_genai_sdk = None
    types = None

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
    specific_filters: Dict[str, Any] = None  # Domain-specific filters
    confidence: float = 1.0  # AI confidence score

class AIQueryParser:
    """AI-powered query parser using Gemini 2.5 Flash for advanced intent detection."""
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """Initialize the AI query parser."""
        load_dotenv()
        
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.gemini_client = None
        self.gemini_model_name = "gemini-2.5-flash-lite"
        
        if not self.gemini_api_key:
            logger.warning("⚠️ Gemini API key not provided - will use fallback parsing")
        else:
            try:
                self.gemini_client = google_genai_sdk.Client(api_key=self.gemini_api_key)
                logger.info("✅ Gemini client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Gemini client: {e}")
        
        # Fallback patterns for when AI is unavailable
        self.fallback_patterns = self._setup_fallback_patterns()
        
        logger.info("✅ AI query parser initialized")
    
    def _setup_fallback_patterns(self) -> Dict:
        """Setup fallback patterns for when AI is unavailable."""
        return {
            'status': {
                'open': {
                    'patterns': [r'\bopen\s+calls?\b', r'\bcalls?\s+that\s+are\s+open\b', r'\bavailable\s+calls?\b'],
                    'codes': ['31094502'],
                    'intention': 'open_only'
                },
                'closed': {
                    'patterns': [r'\bclosed\s+calls?\b', r'\bcalls?\s+that\s+are\s+closed\b'],
                    'codes': ['31094503'],
                    'intention': 'closed_only'
                },
                'forthcoming': {
                    'patterns': [r'\bforthcoming\s+calls?\b', r'\bupcomm?ing\s+calls?\b'],
                    'codes': ['31094501'],
                    'intention': 'forthcoming_only'
                }
            },
            'temporal': {
                'next_60_days': {
                    'patterns': [r'\bnext\s+60\s+days\b', r'\b60\s+days\b'],
                    'days': 60,
                    'intention': 'next_60_days'
                },
                'recent': {
                    'patterns': [r'\brecent\s+calls?\b', r'\blatest\s+calls?\b'],
                    'months_back': 6,
                    'intention': 'recent_only'
                }
            },
            'domain': {
                'cluster_4': [r'cluster\s*4', r'digital.*industry.*space'],
                'trl': [r'trl\s*[5-7]', r'technology\s*readiness\s*level'],
                'ai': [r'\bai\b', r'artificial\s*intelligence'],
                'cybersecurity': [r'cyber.*security', r'cybersecurity'],
                'edge_computing': [r'edge\s*computing'],
                'living_labs': [r'living\s*labs?', r'govtech'],
                'standardization': [r'standardi[sz]ation', r'data\s*interoperability'],
                'digital_twins': [r'digital\s*twins?'],
                'eic': [r'eic\s*accelerator', r'deep\s*tech'],
                'mission_calls': [r'mission\s*calls?', r'climate.*neutral.*cities'],
                'lump_sum': [r'lump.*sum', r'actual\s*cost'],
                'ssh': [r'ssh\s*integration', r'social\s*sciences.*humanities']
            }
        }
    
    def _create_comprehensive_prompt(self, query: str) -> str:
        """Create comprehensive prompt for Gemini AI."""
        return f"""You are an expert query parser for Horizon Europe funding opportunities. Your task is to analyze the user's query and extract precise filtering intentions.

**QUERY TO ANALYZE:** "{query}"

**AVAILABLE FILTER CATEGORIES:**

1. **STATUS FILTERS:**
   - OPEN: Currently accepting applications (status code: 31094502)
   - CLOSED: Past deadlines (status code: 31094503) 
   - FORTHCOMING: Future calls not yet open (status code: 31094501)
   - AVAILABLE: Both open and forthcoming calls

2. **TEMPORAL FILTERS:**
   - NEXT_60_DAYS: Calls closing in the next 60 days
   - NEXT_30_DAYS: Calls closing in the next 30 days
   - RECENT: Calls from last 6 months
   - VERY_RECENT: Calls from last 3 months
   - CURRENT_YEAR: Calls from current year

3. **DOMAIN-SPECIFIC FILTERS:**
   - CLUSTER_4: Digital, Industry and Space cluster
   - TRL: Technology Readiness Level (specify levels if mentioned)
   - AI: Artificial Intelligence topics
   - CYBERSECURITY: Cybersecurity and information security
   - EDGE_COMPUTING: Edge computing technologies
   - LIVING_LABS: Living labs and GovTech
   - STANDARDIZATION: Standardization activities
   - DIGITAL_TWINS: Digital twins for manufacturing/energy
   - EIC: EIC Accelerator and deep tech
   - MISSION_CALLS: Mission-oriented calls
   - LUMP_SUM: Lump-sum funding vs actual cost
   - SSH: Social Sciences and Humanities integration

4. **TECHNOLOGY FILTERS:**
   - AI, CYBERSECURITY, EDGE_COMPUTING, QUANTUM, DATA_SPACES

**ANALYSIS TASK:**
1. Determine the user's primary intent (what they're really looking for)
2. Extract all relevant filters from the categories above
3. Provide a clean search query (remove filter words)
4. Estimate confidence level (0.0-1.0)

**RESPONSE FORMAT (JSON):**
{{
  "status_filter": ["status_code"] or null,
  "temporal_filter": {{"type": "filter_type", "days": number}} or null,
  "filter_intention": "specific_intention",
  "clean_query": "cleaned search terms",
  "user_intent_detected": ["category:value"],
  "specific_filters": {{"filter_name": true}},
  "confidence": 0.95
}}

**EXAMPLES:**
Example 1: "What are open calls for AI in Cluster 4?"
Response: {{
  "status_filter": ["31094502"],
  "temporal_filter": null,
  "filter_intention": "open_only",
  "clean_query": "AI",
  "user_intent_detected": ["status:open", "domain:cluster_4", "technology:ai"],
  "specific_filters": {{"cluster_4": true, "ai": true}},
  "confidence": 0.98
}}

Example 2: "Calls closing in next 60 days for cybersecurity"
Response: {{
  "status_filter": null,
  "temporal_filter": {{"type": "next_60_days", "days": 60}},
  "filter_intention": "next_60_days",
  "clean_query": "cybersecurity",
  "user_intent_detected": ["temporal:next_60_days", "technology:cybersecurity"],
  "specific_filters": {{"cybersecurity": true}},
  "confidence": 0.96
}}

**NOW ANALYZE THIS QUERY:** "{query}"
"""

    def parse_with_ai(self, query: str) -> Optional[Dict]:
        """Parse query using Gemini AI."""
        if not self.gemini_client:
            return None
            
        try:
            prompt = self._create_comprehensive_prompt(query)
            
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.0)
            
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=gemini_contents,
                config=gen_config
            )
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                # If no JSON found, try to parse the text response
                logger.warning("⚠️ No JSON found in AI response, trying to parse text")
                return self._parse_text_response(response_text)
                
        except Exception as e:
            logger.error(f"❌ AI parsing failed: {e}")
            return None
    
    def _parse_text_response(self, response_text: str) -> Optional[Dict]:
        """Fallback parsing for text responses."""
        try:
            # Simple pattern matching for text responses
            lines = response_text.split('\n')
            result = {
                "status_filter": None,
                "temporal_filter": None,
                "filter_intention": "all",
                "clean_query": "",
                "user_intent_detected": [],
                "specific_filters": {},
                "confidence": 0.7
            }
            
            for line in lines:
                line_lower = line.lower()
                if "status_filter" in line_lower and "31094502" in line:
                    result["status_filter"] = ["31094502"]
                    result["filter_intention"] = "open_only"
                    result["user_intent_detected"].append("status:open")
                elif "temporal_filter" in line_lower and "next_60_days" in line_lower:
                    result["temporal_filter"] = {"type": "next_60_days", "days": 60}
                    result["filter_intention"] = "next_60_days"
                    result["user_intent_detected"].append("temporal:next_60_days")
                elif "clean_query" in line_lower:
                    # Extract clean query
                    match = re.search(r'clean_query[:\s]+["\']?(.*?)["\']?$', line, re.IGNORECASE)
                    if match:
                        result["clean_query"] = match.group(1).strip()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Text response parsing failed: {e}")
            return None
    
    def _fallback_parse(self, query: str) -> QueryFilters:
        """Fallback parsing when AI is unavailable."""
        query_lower = query.lower()
        clean_query = query
        status_codes = None
        date_filter = None
        filter_intention = "all"
        user_intent_detected = []
        specific_filters = {}
        
        # Status filters
        for status_type, config in self.fallback_patterns['status'].items():
            for pattern in config['patterns']:
                if re.search(pattern, query_lower):
                    status_codes = config['codes']
                    filter_intention = config['intention']
                    user_intent_detected.append(f"status:{status_type}")
                    clean_query = re.sub(pattern, '', clean_query, flags=re.IGNORECASE).strip()
                    break
        
        # Temporal filters
        for temp_type, config in self.fallback_patterns['temporal'].items():
            for pattern in config['patterns']:
                if re.search(pattern, query_lower):
                    if temp_type == 'next_60_days':
                        end_date = datetime.now() + timedelta(days=config['days'])
                        date_filter = {
                            "gte": datetime.now().strftime('%Y-%m-%d'),
                            "lte": end_date.strftime('%Y-%m-%d')
                        }
                    filter_intention = config['intention']
                    user_intent_detected.append(f"temporal:{temp_type}")
                    clean_query = re.sub(pattern, '', clean_query, flags=re.IGNORECASE).strip()
                    break
        
        # Domain filters
        for domain, patterns in self.fallback_patterns['domain'].items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    user_intent_detected.append(f"domain:{domain}")
                    specific_filters[domain] = True
                    break
        
        # Final cleanup
        if not clean_query or len(clean_query.strip()) < 2:
            clean_query = query
        
        return QueryFilters(
            status_filter=status_codes,
            date_filter=date_filter,
            filter_intention=filter_intention,
            original_query=query,
            clean_query=clean_query,
            user_intent_detected=user_intent_detected or ["no_filters"],
            specific_filters=specific_filters,
            confidence=0.7  # Lower confidence for fallback
        )
    
    def parse_query(self, query: str) -> QueryFilters:
        """Parse user query using AI or fallback."""
        logger.info(f"🧠 AI Parsing query: '{query}'")
        
        # Try AI parsing first
        ai_result = self.parse_with_ai(query)
        
        if ai_result:
            try:
                # Convert AI result to QueryFilters
                status_filter = ai_result.get("status_filter")
                temporal_filter = ai_result.get("temporal_filter")
                
                # Convert temporal filter to date format if needed
                date_filter = None
                if temporal_filter and temporal_filter.get("type") == "next_60_days":
                    end_date = datetime.now() + timedelta(days=temporal_filter.get("days", 60))
                    date_filter = {
                        "gte": datetime.now().strftime('%Y-%m-%d'),
                        "lte": end_date.strftime('%Y-%m-%d')
                    }
                
                filters = QueryFilters(
                    status_filter=status_filter,
                    date_filter=date_filter,
                    filter_intention=ai_result.get("filter_intention", "all"),
                    original_query=query,
                    clean_query=ai_result.get("clean_query", query),
                    user_intent_detected=ai_result.get("user_intent_detected", []),
                    specific_filters=ai_result.get("specific_filters", {}),
                    confidence=ai_result.get("confidence", 0.9)
                )
                
                logger.info(f"✅ AI Parsed: {filters.filter_intention}, confidence: {filters.confidence}")
                logger.info(f"   Detected intents: {filters.user_intent_detected}")
                return filters
                
            except Exception as e:
                logger.error(f"❌ AI result processing failed: {e}, using fallback")
        
        # Fallback to rule-based parsing
        logger.info("🔄 Using fallback parsing")
        return self._fallback_parse(query)
    
    def get_filter_explanation(self, filters: QueryFilters, results_count: int) -> str:
        """Generate explanation for filter results."""
        explanations = []
        
        if filters.filter_intention == "open_only":
            if results_count == 0:
                explanations.append("🔴 **No currently open calls found** - check forthcoming calls")
            else:
                explanations.append(f"🟢 **{results_count} open calls found**")
        
        elif filters.filter_intention == "next_60_days":
            if results_count == 0:
                explanations.append("📅 **No calls closing in next 60 days**")
            else:
                explanations.append(f"⏰ **{results_count} calls closing soon**")
        
        elif "cluster_4" in filters.specific_filters:
            explanations.append("🏭 **Cluster 4 (Digital, Industry & Space)**")
        
        # Add technology-specific explanations
        tech_explanations = []
        for intent in filters.user_intent_detected:
            if intent.startswith("technology:"):
                tech = intent.split(":")[1]
                tech_explanations.append(tech.upper())
        
        if tech_explanations:
            explanations.append(f"🔧 **Technologies**: {', '.join(tech_explanations)}")
        
        return " | ".join(explanations) if explanations else "No specific filters applied"

# Example usage and testing
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    parser = AIQueryParser()
    
    test_queries = [
        "What are open calls for AI in Cluster 4?",
        "Calls closing in next 60 days for cybersecurity",
        "TRL 5-7 demonstrators for edge computing",
        "Living labs for digital public services",
        "EIC Accelerator cut-offs for deep tech SMEs"
    ]
    
    print("🧪 Testing AI Query Parser")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        filters = parser.parse_query(query)
        
        print(f"   Status filter: {filters.status_filter}")
        print(f"   Date filter: {filters.date_filter}")
        print(f"   Intention: {filters.filter_intention}")
        print(f"   Clean query: '{filters.clean_query}'")
        print(f"   User intent: {filters.user_intent_detected}")
        print(f"   Specific filters: {filters.specific_filters}")
        print(f"   Confidence: {filters.confidence:.2f}")