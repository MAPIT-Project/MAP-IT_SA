#!/usr/bin/env python3
"""
Integration test showing hybrid parser working with RAG service
for Horizon Europe call discovery questions
"""

import sys
import time
from typing import List, Dict

# Add the current directory to Python path
sys.path.insert(0, '.')

def test_hybrid_rag_integration():
    """Test hybrid parser integration with RAG service for Horizon questions."""
    
    try:
        from app.services.hybrid_query_parser import HybridQueryParser
        from app.services.enhanced_call_search import EnhancedCallSearchService
        
        print("🔗 Hybrid Parser + RAG Integration Test")
        print("=" * 60)
        print()
        
        # Initialize components
        hybrid_parser = HybridQueryParser()
        call_search = EnhancedCallSearchService()
        
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
            
            # Step 1: Parse query with hybrid parser
            parse_start = time.time()
            filters = hybrid_parser.parse_query(query)
            parse_time = time.time() - parse_start
            
            print(f"   🤖 Parser: {filters.parser_used.upper()}")
            print(f"   🎯 Intention: {filters.filter_intention}")
            print(f"   🧠 Detected intents: {filters.user_intent_detected}")
            print(f"   ⏱️  Parse time: {parse_time:.3f}s")
            print(f"   💪 Confidence: {filters.confidence:.2f}")
            
            # Step 2: Use filters for enhanced call search
            if "no_filters" not in filters.user_intent_detected:
                search_start = time.time()
                
                # Execute search using the enhanced service (it handles filters internally)
                search_results = call_search.search_calls_enhanced(
                    query=filters.clean_query,
                    max_results=5,
                    enable_facet_analysis=True
                )
                search_time = time.time() - search_start
                
                print(f"   🔍 Search results: {len(search_results.get('calls_data', []))} calls found")
                print(f"   ⏱️  Search time: {search_time:.3f}s")
                
                # Generate explanation
                explanation = hybrid_parser.get_filter_explanation(
                    filters, len(search_results.get('calls_data', []))
                )
                print(f"   📝 Explanation: {explanation}")
                
                results.append({
                    'query': query,
                    'parser_used': filters.parser_used,
                    'parse_time': parse_time,
                    'search_time': search_time,
                    'total_time': parse_time + search_time,
                    'results_count': len(search_results.get('calls_data', [])),
                    'explanation': explanation
                })
            else:
                print("   ⚠️  No specific filters detected - using general search")
                # For queries without specific filters, we might use different approach
                results.append({
                    'query': query,
                    'parser_used': filters.parser_used,
                    'parse_time': parse_time,
                    'search_time': 0,
                    'total_time': parse_time,
                    'results_count': 0,
                    'explanation': "General query - needs procedural response"
                })
        
        # Generate summary
        print("\n" + "="*60)
        print("📊 INTEGRATION SUMMARY")
        print("="*60)
        
        total_queries = len(results)
        intelligent_count = sum(1 for r in results if r['parser_used'] == 'intelligent')
        ai_count = sum(1 for r in results if r['parser_used'] == 'ai')
        
        total_parse_time = sum(r['parse_time'] for r in results)
        total_search_time = sum(r['search_time'] for r in results)
        total_results = sum(r['results_count'] for r in results)
        
        avg_parse_time = total_parse_time / total_queries
        avg_search_time = total_search_time / total_queries
        avg_total_time = (total_parse_time + total_search_time) / total_queries
        
        print(f"\n📈 Performance Metrics:")
        print(f"   Total queries processed: {total_queries}")
        print(f"   Intelligent parser used: {intelligent_count} times ({intelligent_count/total_queries*100:.1f}%)")
        print(f"   AI parser used: {ai_count} times ({ai_count/total_queries*100:.1f}%)")
        print(f"   Average parse time: {avg_parse_time:.3f}s")
        print(f"   Average search time: {avg_search_time:.3f}s")
        print(f"   Average total time: {avg_total_time:.3f}s")
        print(f"   Total calls found: {total_results}")
        
        print(f"\n🎯 Parser Effectiveness:")
        queries_with_results = sum(1 for r in results if r['results_count'] > 0)
        print(f"   Queries with results: {queries_with_results}/{total_queries} ({queries_with_results/total_queries*100:.1f}%)")
        
        # Show examples of different parser choices
        print(f"\n🔍 Example Parser Choices:")
        intelligent_examples = [r for r in results if r['parser_used'] == 'intelligent'][:2]
        ai_examples = [r for r in results if r['parser_used'] == 'ai'][:2]
        
        print(f"   Intelligent parser examples:")
        for example in intelligent_examples:
            print(f"     - '{example['query'][:50]}...' → {example['results_count']} results")
        
        print(f"   AI parser examples:")
        for example in ai_examples:
            print(f"     - '{example['query'][:50]}...' → {example['results_count']} results")
        
        print("\n✅ Integration test completed successfully!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required modules are available")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hybrid_rag_integration()