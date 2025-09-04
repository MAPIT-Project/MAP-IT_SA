"""
Hybrid Query Parser - Combines AI and rule-based parsing for optimal performance
Uses intelligent parser for speed, AI parser for complex queries and confidence
"""

import re
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import both parsers
try:
    from .intelligent_query_parser import IntelligentQueryParser, QueryFilters as IntelFilters
    from .ai_query_parser import AIQueryParser, QueryFilters as AIFilters
except ImportError:
    # Fallback imports for standalone testing
    from intelligent_query_parser import IntelligentQueryParser, QueryFilters as IntelFilters
    from ai_query_parser import AIQueryParser, QueryFilters as AIFilters

logger = logging.getLogger(__name__)

@dataclass
class HybridQueryFilters:
    """Enhanced query filters with hybrid metadata."""
    status_filter: Optional[List[str]] = None
    date_filter: Optional[Dict[str, str]] = None
    filter_intention: str = "all"
    original_query: str = ""
    clean_query: str = ""
    user_intent_detected: List[str] = None
    specific_filters: Dict[str, Any] = None
    confidence: float = 1.0
    parser_used: str = "intelligent"  # "intelligent", "ai", or "hybrid"
    processing_time: float = 0.0

class HybridQueryParser:
    """Hybrid parser that intelligently chooses between AI and rule-based parsing."""
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """Initialize hybrid parser with both engines."""
        self.intelligent_parser = IntelligentQueryParser()
        self.ai_parser = AIQueryParser(gemini_api_key)
        
        # Patterns to identify complex queries that should use AI
        self.complex_patterns = [
            r'\b(and|or|with|including)\b.*\b(and|or|with|including)\b',  # Multiple conjunctions
            r'\b(work\s+programme|latest\s+programme|current\s+programme)\b',
            r'\b(how\s+to|what\s+is|explain|difference\s+between)\b',  # Explanatory queries
            r'\b(trl\s*[0-9]+.*trl\s*[0-9]+)',  # Multiple TRL levels
            r'\b([a-z]+\s*,\s*[a-z]+\s*(?:,\s*[a-z]+)*)\b',  # Comma-separated lists
            r'\b(complex|detailed|comprehensive)\b',
        ]
        
        # Patterns for simple queries that should use rule-based
        self.simple_patterns = [
            r'^\s*[a-z]+\s+[a-z]+\s*$',  # Simple 2-word queries
            r'\b(open|closed|forthcoming)\s+calls?\b',  # Simple status queries
            r'\b(recent|latest|new)\s+calls?\b',  # Simple temporal queries
            r'^\s*\w+\s*$',  # Single word queries
        ]
        
        logger.info("✅ Hybrid query parser initialized")
    
    def _is_complex_query(self, query: str) -> bool:
        """Determine if query is complex enough to warrant AI parsing."""
        query_lower = query.lower()
        
        # Check for complex patterns that definitely need AI
        for pattern in self.complex_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # Check query length and complexity - be more conservative
        word_count = len(query.split())
        if word_count > 10:  # Only very long queries
            return True
        
        # Check for multiple domain terms - require at least 3 to use AI
        domain_terms = ['ai', 'cybersecurity', 'edge computing', 'cluster', 'trl',
                       'living labs', 'govtech', 'standardization', 'digital twins',
                       'eic', 'mission', 'lump-sum', 'ssh']
        found_terms = sum(1 for term in domain_terms if term in query_lower)
        if found_terms >= 3:  # Multiple domain terms indicate complexity
            return True
        
        # Check for explanatory/procedural queries that need AI
        explanatory_terms = ['how to', 'what is', 'explain', 'difference between',
                           'where to find', 'how do i']
        if any(term in query_lower for term in explanatory_terms):
            return True
        
        return False
    
    def _is_simple_query(self, query: str) -> bool:
        """Determine if query is simple enough for rule-based parsing."""
        query_lower = query.lower()
        
        # Check for simple patterns
        for pattern in self.simple_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # Short queries are generally simple
        if len(query.split()) <= 3:
            return True
        
        return False
    
    def _convert_intel_to_hybrid(self, intel_filters: IntelFilters, processing_time: float) -> HybridQueryFilters:
        """Convert intelligent parser filters to hybrid format."""
        return HybridQueryFilters(
            status_filter=intel_filters.status_filter,
            date_filter=intel_filters.date_filter,
            filter_intention=intel_filters.filter_intention,
            original_query=intel_filters.original_query,
            clean_query=intel_filters.clean_query,
            user_intent_detected=intel_filters.user_intent_detected,
            specific_filters=intel_filters.specific_filters,
            confidence=0.8,  # Default confidence for rule-based
            parser_used="intelligent",
            processing_time=processing_time
        )
    
    def _convert_ai_to_hybrid(self, ai_filters: AIFilters, processing_time: float) -> HybridQueryFilters:
        """Convert AI parser filters to hybrid format."""
        return HybridQueryFilters(
            status_filter=ai_filters.status_filter,
            date_filter=ai_filters.date_filter,
            filter_intention=ai_filters.filter_intention,
            original_query=ai_filters.original_query,
            clean_query=ai_filters.clean_query,
            user_intent_detected=ai_filters.user_intent_detected,
            specific_filters=ai_filters.specific_filters,
            confidence=ai_filters.confidence,
            parser_used="ai",
            processing_time=processing_time
        )
    
    def parse_query(self, query: str) -> HybridQueryFilters:
        """Parse query using hybrid approach."""
        start_time = time.time()
        original_query = query.strip()
        
        logger.info(f"🤝 Hybrid parsing query: '{original_query}'")
        
        # Step 1: Quick classification - prioritize intelligent parser for most queries
        if self._is_simple_query(original_query):
            logger.info("📋 Using intelligent parser (simple query)")
            intel_start = time.time()
            intel_filters = self.intelligent_parser.parse_query(original_query)
            intel_time = time.time() - intel_start
            total_time = time.time() - start_time
            
            return self._convert_intel_to_hybrid(intel_filters, total_time)
        
        elif self._is_complex_query(original_query):
            logger.info("🧠 Using AI parser (complex query)")
            ai_start = time.time()
            ai_filters = self.ai_parser.parse_query(original_query)
            ai_time = time.time() - ai_start
            total_time = time.time() - start_time
            
            return self._convert_ai_to_hybrid(ai_filters, total_time)
        
        else:
            # Default: try intelligent first for most Horizon Europe queries
            logger.info("⚡ Trying intelligent parser first (default for Horizon queries)")
            intel_start = time.time()
            intel_filters = self.intelligent_parser.parse_query(original_query)
            intel_time = time.time() - intel_start
            
            # Check if intelligent parser produced good results
            # For Horizon queries, we want to use intelligent parser when possible
            has_good_intents = (intel_filters.user_intent_detected and
                               "no_filters" not in intel_filters.user_intent_detected and
                               len(intel_filters.user_intent_detected) > 0)
            
            # Check if it's a procedural query that might need AI
            is_procedural = any(term in original_query.lower() for term in
                               ['how to', 'what is', 'explain', 'difference'])
            
            if has_good_intents and not is_procedural:
                total_time = time.time() - start_time
                logger.info("✅ Intelligent parser produced good results for Horizon query")
                return self._convert_intel_to_hybrid(intel_filters, total_time)
            else:
                # Fallback to AI for procedural queries or poor results
                logger.info("🔄 Falling back to AI (procedural or poor intelligent results)")
                ai_start = time.time()
                ai_filters = self.ai_parser.parse_query(original_query)
                ai_time = time.time() - ai_start
                total_time = time.time() - start_time
                
                return self._convert_ai_to_hybrid(ai_filters, total_time)
    
    def get_filter_explanation(self, filters: HybridQueryFilters, results_count: int) -> str:
        """Generate explanation for filter results with parser info."""
        explanations = []
        
        # Add parser information
        explanations.append(f"🔧 Parser: {filters.parser_used.upper()}")
        explanations.append(f"🎯 Confidence: {filters.confidence:.2f}")
        
        # Add standard explanations
        if filters.filter_intention == "open_only":
            if results_count == 0:
                explanations.append("🔴 No currently open calls found")
            else:
                explanations.append(f"🟢 {results_count} open calls found")
        
        elif filters.filter_intention == "next_60_days":
            if results_count == 0:
                explanations.append("📅 No calls closing in next 60 days")
            else:
                explanations.append(f"⏰ {results_count} calls closing soon")
        
        # Add technology/domain explanations
        tech_explanations = []
        for intent in filters.user_intent_detected:
            if intent.startswith("technology:") or intent.startswith("domain:"):
                tech = intent.split(":")[1]
                tech_explanations.append(tech.upper())
        
        if tech_explanations:
            explanations.append(f"🔧 Technologies: {', '.join(tech_explanations)}")
        
        return " | ".join(explanations)

# Example usage and testing
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    parser = HybridQueryParser()
    
    test_queries = [
        "open calls for AI",  # Simple
        "What are open calls for AI in Cluster 4 with TRL 5-7?",  # Complex
        "cybersecurity",  # Simple
        "How to filter calls by budget and type of action?",  # Complex
        "recent calls"  # Simple
    ]
    
    print("🧪 Testing Hybrid Query Parser")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        filters = parser.parse_query(query)
        
        print(f"   Parser used: {filters.parser_used}")
        print(f"   Intention: {filters.filter_intention}")
        print(f"   Clean query: '{filters.clean_query}'")
        print(f"   Detected intents: {filters.user_intent_detected}")
        print(f"   Confidence: {filters.confidence:.2f}")
        print(f"   Processing time: {filters.processing_time:.3f}s")