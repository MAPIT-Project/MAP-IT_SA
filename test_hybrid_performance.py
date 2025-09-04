#!/usr/bin/env python3
"""
Comprehensive test of hybrid parser vs individual parsers
with the original Horizon Europe questions
"""

import sys
import time
import logging
from typing import List, Dict

# Add the current directory to Python path
sys.path.insert(0, '.')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_hybrid_performance():
    """Test hybrid parser performance with Horizon Europe questions."""
    
    try:
        from app.services.intelligent_query_parser import IntelligentQueryParser
        from app.services.ai_query_parser import AIQueryParser
        from app.services.hybrid_query_parser import HybridQueryParser
        
        print("🧪 Hybrid Parser Performance Test")
        print("=" * 60)
        print()
        
        # Initialize all parsers
        intelligent_parser = IntelligentQueryParser()
        ai_parser = AIQueryParser()
        hybrid_parser = HybridQueryParser()
        
        # Original Horizon Europe questions from the task
        horizon_questions = [
            "What are the currently open Horizon Europe calls in Cluster 4?",
            "Which topics under the latest work programme match advanced AI, cybersecurity, and edge computing?",
            "What calls close in the next 60 days that target TRL 5–7 demonstrators?",
            "Which topics support living labs for digital public services or GovTech?",
            "Are there open topics that fund standardisation activities for data interoperability?",
            "Which calls fund digital twins for manufacturing or energy?",
            "What's the difference between calls and topics on the Funding & Tenders Portal?",
            "How to filter calls by budget, type of action, and expected outcomes?",
            "Which EIC Accelerator cut-offs are upcoming for deep tech SMEs?",
            "Are there mission calls relevant to climate-neutral and smart cities with digital solutions?",
            "How to identify topics with lump-sum funding vs actual cost funding?",
            "Which topics encourage social sciences and humanities (SSH) integration in digital projects?"
        ]
        
        results = []
        
        for i, query in enumerate(horizon_questions):
            print(f"\n🔍 Query {i+1}: '{query}'")
            print("-" * 50)
            
            # Test all three parsers
            parsers = {
                "intelligent": intelligent_parser,
                "ai": ai_parser,
                "hybrid": hybrid_parser
            }
            
            parser_results = {}
            
            for parser_name, parser in parsers.items():
                start_time = time.time()
                
                if parser_name == "intelligent":
                    filters = parser.parse_query(query)
                    processing_time = time.time() - start_time
                    parser_results[parser_name] = {
                        'intention': filters.filter_intention,
                        'clean_query': filters.clean_query,
                        'intents': filters.user_intent_detected,
                        'specific_filters': filters.specific_filters,
                        'time': processing_time,
                        'confidence': 0.8  # Default for intelligent
                    }
                
                elif parser_name == "ai":
                    filters = parser.parse_query(query)
                    processing_time = time.time() - start_time
                    parser_results[parser_name] = {
                        'intention': filters.filter_intention,
                        'clean_query': filters.clean_query,
                        'intents': filters.user_intent_detected,
                        'specific_filters': filters.specific_filters,
                        'time': processing_time,
                        'confidence': filters.confidence
                    }
                
                elif parser_name == "hybrid":
                    filters = parser.parse_query(query)
                    processing_time = time.time() - start_time
                    parser_results[parser_name] = {
                        'intention': filters.filter_intention,
                        'clean_query': filters.clean_query,
                        'intents': filters.user_intent_detected,
                        'specific_filters': filters.specific_filters,
                        'time': processing_time,
                        'confidence': filters.confidence,
                        'parser_used': filters.parser_used
                    }
            
            results.append({
                'query': query,
                'parsers': parser_results
            })
            
            # Print results for this query
            for parser_name, result in parser_results.items():
                print(f"   {parser_name.upper():<12}:")
                print(f"      Intention: {result['intention']}")
                print(f"      Clean query: '{result['clean_query']}'")
                print(f"      Intents: {result['intents']}")
                if parser_name == 'hybrid':
                    print(f"      Parser used: {result.get('parser_used', 'N/A')}")
                print(f"      Confidence: {result['confidence']:.2f}")
                print(f"      Time: {result['time']:.3f}s")
                print()
        
        # Generate summary statistics
        print("\n" + "="*60)
        print("📊 PERFORMANCE SUMMARY")
        print("="*60)
        
        total_queries = len(results)
        
        # Calculate totals and averages
        stats = {
            'intelligent': {'total_time': 0, 'total_intents': 0, 'total_filters': 0},
            'ai': {'total_time': 0, 'total_intents': 0, 'total_filters': 0},
            'hybrid': {'total_time': 0, 'total_intents': 0, 'total_filters': 0}
        }
        
        hybrid_parser_choices = {'intelligent': 0, 'ai': 0}
        
        for result in results:
            for parser_name in ['intelligent', 'ai', 'hybrid']:
                parser_result = result['parsers'][parser_name]
                stats[parser_name]['total_time'] += parser_result['time']
                stats[parser_name]['total_intents'] += len(parser_result['intents'])
                stats[parser_name]['total_filters'] += len(parser_result.get('specific_filters', {}))
                
                if parser_name == 'hybrid':
                    parser_used = parser_result.get('parser_used')
                    if parser_used in hybrid_parser_choices:
                        hybrid_parser_choices[parser_used] += 1
        
        # Print statistics
        for parser_name in ['intelligent', 'ai', 'hybrid']:
            data = stats[parser_name]
            avg_time = data['total_time'] / total_queries
            avg_intents = data['total_intents'] / total_queries
            avg_filters = data['total_filters'] / total_queries
            
            print(f"\n{parser_name.upper()} Parser:")
            print(f"   Avg time per query: {avg_time:.3f}s")
            print(f"   Avg intents detected: {avg_intents:.1f}")
            print(f"   Avg specific filters: {avg_filters:.1f}")
        
        # Hybrid parser choices
        print(f"\n🤝 Hybrid Parser Choices:")
        print(f"   Intelligent parser used: {hybrid_parser_choices['intelligent']} times")
        print(f"   AI parser used: {hybrid_parser_choices['ai']} times")
        print(f"   Hybrid efficiency: {(hybrid_parser_choices['intelligent'] / total_queries * 100):.1f}%")
        
        # Calculate time savings
        intelligent_avg = stats['intelligent']['total_time'] / total_queries
        ai_avg = stats['ai']['total_time'] / total_queries
        hybrid_avg = stats['hybrid']['total_time'] / total_queries
        
        print(f"\n⏱️  Time Savings:")
        print(f"   Hybrid vs AI: {(ai_avg - hybrid_avg):.3f}s per query ({(1 - hybrid_avg/ai_avg)*100:.1f}% faster)")
        print(f"   Hybrid maintains {stats['hybrid']['total_intents']/stats['ai']['total_intents']*100:.1f}% of AI's intent detection")
        
        # Quality comparison
        print(f"\n🎯 Quality Comparison:")
        print(f"   Hybrid detected {stats['hybrid']['total_intents']} intents vs AI's {stats['ai']['total_intents']}")
        print(f"   Hybrid detected {stats['hybrid']['total_filters']} filters vs AI's {stats['ai']['total_filters']}")
        
        print("\n🎉 Test completed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hybrid_performance()