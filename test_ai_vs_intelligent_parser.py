#!/usr/bin/env python3
"""
Comparison test between AI-powered parser and intelligent query parser.
Tests both parsers with the same set of Horizon Europe questions.
"""

import sys
import os
import time
import logging
from typing import List, Dict, Tuple

# Add the current directory to Python path for proper imports
sys.path.insert(0, os.path.dirname(__file__))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_parser_comparison():
    """Compare AI parser vs intelligent query parser."""
    
    try:
        from app.services.intelligent_query_parser import IntelligentQueryParser
        from app.services.ai_query_parser import AIQueryParser
        
        print("🧪 AI vs Intelligent Query Parser Comparison")
        print("=" * 60)
        print()
        
        # Initialize both parsers
        intelligent_parser = IntelligentQueryParser()
        ai_parser = AIQueryParser()
        
        # Test queries covering all the required question types
        test_queries = [
            # Cluster 4 queries
            "What are the currently open Horizon Europe calls in Cluster 4?",
            "Cluster 4 digital industry space open calls",
            
            # Technology-specific queries
            "Which topics under the latest work programme match advanced AI, cybersecurity, and edge computing?",
            "AI cybersecurity edge computing calls",
            
            # Temporal queries
            "What calls close in the next 60 days that target TRL 5–7 demonstrators?",
            "TRL 5-7 demonstrators next 60 days",
            
            # Domain-specific queries
            "Which topics support living labs for digital public services or GovTech?",
            "Living labs GovTech digital public services",
            
            # Standardization queries
            "Are there open topics that fund standardisation activities for data interoperability?",
            "Standardization data interoperability funding",
            
            # Digital twins queries
            "Which calls fund digital twins for manufacturing or energy?",
            "Digital twins manufacturing energy calls",
            
            # Procedural queries
            "What's the difference between calls and topics on the Funding & Tenders Portal?",
            "How to filter calls by budget, type of action, and expected outcomes?",
            
            # Programme queries
            "Which EIC Accelerator cut-offs are upcoming for deep tech SMEs?",
            "EIC Accelerator deep tech SMEs cut-offs",
            
            # Mission calls queries
            "Are there mission calls relevant to climate-neutral and smart cities with digital solutions?",
            "Mission calls climate-neutral smart cities",
            
            # Funding type queries
            "How to identify topics with lump-sum funding vs actual cost funding?",
            "Lump-sum vs actual cost funding",
            
            # SSH integration queries
            "Which topics encourage social sciences and humanities (SSH) integration in digital projects?",
            "SSH integration social sciences humanities digital projects"
        ]
        
        results = []
        
        for i, query in enumerate(test_queries):
            print(f"\n🔍 Query {i+1}: '{query}'")
            print("-" * 50)
            
            # Test intelligent parser
            start_time = time.time()
            intel_filters = intelligent_parser.parse_query(query)
            intel_time = time.time() - start_time
            
            # Test AI parser
            start_time = time.time()
            ai_filters = ai_parser.parse_query(query)
            ai_time = time.time() - start_time
            
            # Compare results
            comparison = {
                'query': query,
                'intelligent': {
                    'intention': intel_filters.filter_intention,
                    'clean_query': intel_filters.clean_query,
                    'intents': intel_filters.user_intent_detected,
                    'time': intel_time,
                    'specific_filters': intel_filters.specific_filters
                },
                'ai': {
                    'intention': ai_filters.filter_intention,
                    'clean_query': ai_filters.clean_query,
                    'intents': ai_filters.user_intent_detected,
                    'time': ai_time,
                    'confidence': ai_filters.confidence,
                    'specific_filters': ai_filters.specific_filters
                },
                'time_difference': ai_time - intel_time
            }
            
            results.append(comparison)
            
            # Print comparison
            print(f"🤖 Intelligent Parser:")
            print(f"   Intention: {intel_filters.filter_intention}")
            print(f"   Clean query: '{intel_filters.clean_query}'")
            print(f"   Detected intents: {intel_filters.user_intent_detected}")
            print(f"   Specific filters: {intel_filters.specific_filters}")
            print(f"   Time: {intel_time:.3f}s")
            
            print(f"🧠 AI Parser:")
            print(f"   Intention: {ai_filters.filter_intention}")
            print(f"   Clean query: '{ai_filters.clean_query}'")
            print(f"   Detected intents: {ai_filters.user_intent_detected}")
            print(f"   Specific filters: {ai_filters.specific_filters}")
            print(f"   Confidence: {ai_filters.confidence:.2f}")
            print(f"   Time: {ai_time:.3f}s")
            
            print(f"⏱️  Time difference: {comparison['time_difference']:.3f}s")
            
            # Check if results are similar
            intents_similar = set(intel_filters.user_intent_detected) == set(ai_filters.user_intent_detected)
            clean_query_similar = intel_filters.clean_query.lower() == ai_filters.clean_query.lower()
            
            print(f"✅ Intents similar: {intents_similar}")
            print(f"✅ Clean query similar: {clean_query_similar}")
            
            if not intents_similar or not clean_query_similar:
                print("⚠️  Note: Parsers produced different results")
        
        # Generate summary statistics
        print("\n" + "="*60)
        print("📊 COMPARISON SUMMARY")
        print("="*60)
        
        total_queries = len(results)
        intel_total_time = sum(r['intelligent']['time'] for r in results)
        ai_total_time = sum(r['ai']['time'] for r in results)
        avg_intel_time = intel_total_time / total_queries
        avg_ai_time = ai_total_time / total_queries
        
        # Count successful intent detections
        intel_intent_count = sum(len(r['intelligent']['intents']) for r in results)
        ai_intent_count = sum(len(r['ai']['intents']) for r in results)
        
        # Count specific filter detections
        intel_filter_count = sum(len(r['intelligent']['specific_filters']) for r in results)
        ai_filter_count = sum(len(r['ai']['specific_filters']) for r in results)
        
        print(f"Total queries tested: {total_queries}")
        print(f"🤖 Intelligent Parser:")
        print(f"   Total time: {intel_total_time:.3f}s")
        print(f"   Average time per query: {avg_intel_time:.3f}s")
        print(f"   Total intents detected: {intel_intent_count}")
        print(f"   Total specific filters: {intel_filter_count}")
        
        print(f"🧠 AI Parser:")
        print(f"   Total time: {ai_total_time:.3f}s")
        print(f"   Average time per query: {avg_ai_time:.3f}s")
        print(f"   Total intents detected: {ai_intent_count}")
        print(f"   Total specific filters: {ai_filter_count}")
        print(f"   Average confidence: {sum(r['ai']['confidence'] for r in results) / total_queries:.2f}")
        
        print(f"\n⏱️  Performance comparison:")
        print(f"   AI is {avg_intel_time/avg_ai_time:.1f}x {'slower' if avg_ai_time > avg_intel_time else 'faster'}")
        print(f"   AI detects {ai_intent_count/intel_intent_count:.1f}x more intents")
        print(f"   AI detects {ai_filter_count/intel_filter_count:.1f}x more specific filters")
        
        # Detailed analysis by query type
        print(f"\n📈 Detailed analysis by query type:")
        query_types = {}
        for r in results:
            query_text = r['query']
            query_type = "other"
            
            if "cluster" in query_text.lower() and "4" in query_text:
                query_type = "cluster_4"
            elif any(tech in query_text.lower() for tech in ["ai", "cybersecurity", "edge computing"]):
                query_type = "technology"
            elif "next 60 days" in query_text.lower() or "trl" in query_text.lower():
                query_type = "temporal_trl"
            elif any(term in query_text.lower() for term in ["living labs", "govtech", "standardization"]):
                query_type = "domain_specific"
            elif any(term in query_text.lower() for term in ["eic", "mission", "lump-sum", "ssh"]):
                query_type = "programme_specific"
            
            if query_type not in query_types:
                query_types[query_type] = []
            query_types[query_type].append(r)
        
        for qtype, queries in query_types.items():
            print(f"\n   {qtype.upper()} queries ({len(queries)}):")
            intel_time = sum(q['intelligent']['time'] for q in queries) / len(queries)
            ai_time = sum(q['ai']['time'] for q in queries) / len(queries)
            print(f"     🤖 Intelligent: {intel_time:.3f}s avg")
            print(f"     🧠 AI: {ai_time:.3f}s avg")
            print(f"     ⏱️  Ratio: {ai_time/intel_time:.1f}x")
        
        print("\n🎉 Comparison completed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parser_comparison()