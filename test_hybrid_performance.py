#!/usr/bin/env python3
"""
Performance test for AI query parser with Horizon Europe questions
"""

import sys
import time
import logging
from typing import List, Dict

# Add the current directory to Python path
sys.path.insert(0, '.')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_ai_parser_performance():
    """Test AI parser performance with Horizon Europe questions."""
    
    try:
        from app.services.ai_query_parser import AIQueryParser
        
        print("AI Query Parser Performance Test")
        print("=" * 60)
        print()
        
        # Initialize AI parser
        ai_parser = AIQueryParser()
        
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
            print(f"Query {i+1}: '{query}'")
            print("-" * 50)
            
            # Test AI parser
            start_time = time.time()
            filters = ai_parser.parse_query(query)
            processing_time = time.time() - start_time
            
            parser_results = {
                'ai': {
                    'intention': filters.filter_intention,
                    'clean_query': filters.clean_query,
                    'intents': filters.user_intent_detected,
                    'specific_filters': filters.specific_filters,
                    'time': processing_time,
                    'confidence': filters.confidence
                }
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
                print(f"      Confidence: {result['confidence']:.2f}")
                print(f"      Time: {result['time']:.3f}s")
                print()
        
        # Generate summary statistics
        print("="*60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)
        
        total_queries = len(results)
        
        # Calculate totals and averages for AI parser
        total_time = 0
        total_intents = 0
        total_filters = 0
        
        for result in results:
            parser_result = result['parsers']['ai']
            total_time += parser_result['time']
            total_intents += len(parser_result['intents'])
            total_filters += len(parser_result.get('specific_filters', {}))
        
        avg_time = total_time / total_queries
        avg_intents = total_intents / total_queries
        avg_filters = total_filters / total_queries
        
        print(f"AI Parser Performance:")
        print(f"   Avg time per query: {avg_time:.3f}s")
        print(f"   Avg intents detected: {avg_intents:.1f}")
        print(f"   Avg specific filters: {avg_filters:.1f}")
        print(f"   Total queries processed: {total_queries}")
        
        print("AI Parser Performance Test completed!")
        
    except ImportError as e:
        print(f"Import error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai_parser_performance()