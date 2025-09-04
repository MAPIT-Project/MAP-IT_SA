#!/usr/bin/env python3
"""
Test script for 50 additional Horizon Europe questions to validate system robustness
"""

import sys
import time
import json
from typing import List, Dict

# Add the current directory to Python path
sys.path.insert(0, '.')

def test_50_additional_questions():
    """Test the system with 50 additional Horizon Europe questions."""
    
    try:
        from app.services.hybrid_query_parser import HybridQueryParser
        from app.services.enhanced_call_search import EnhancedCallSearchService
        
        print("🧪 Testing 50 Additional Horizon Europe Questions")
        print("=" * 70)
        print()
        
        # Initialize components
        hybrid_parser = HybridQueryParser()
        call_search = EnhancedCallSearchService()
        
        # 50 additional Horizon Europe questions covering various scenarios
        additional_questions = [
            # Cluster-specific queries
            "Find open calls in Cluster 5 for climate action",
            "What are forthcoming calls in Cluster 6 for bioeconomy?",
            "Show me closed calls from Cluster 3 for civil security",
            "Cluster 1 health research calls with deadlines next month",
            "Digital transformation calls in Cluster 4 ending in 2025",
            
            # Technology-specific queries
            "Quantum computing research opportunities in Horizon Europe",
            "AI and machine learning funding for SMEs",
            "Cybersecurity calls for critical infrastructure protection",
            "Edge computing and IoT deployment grants",
            "5G and 6G network development funding",
            
            # TRL and development stage queries
            "TRL 3-4 research actions for clean energy",
            "TRL 6-7 innovation actions for medical devices",
            "TRL 8-9 demonstration projects for smart cities",
            "Early-stage research (TRL 1-2) for novel materials",
            "Near-market innovations (TRL 7-8) for renewable energy",
            
            # Temporal queries
            "Calls closing in the next 30 days for digital technologies",
            "Forthcoming calls in Q1 2025 for space research",
            "Recently closed calls from last month in health sector",
            "Open calls with deadlines in March 2025",
            "Calls opening next quarter for climate adaptation",
            
            # Programme-specific queries
            "EIC Pathfinder challenges for deep tech startups",
            "ERC Starting Grants for early-career researchers",
            "MSCA Postdoctoral Fellowships in computer science",
            "Digital Europe Programme calls for data spaces",
            "Euratom research grants for nuclear safety",
            
            # Mission-oriented queries
            "Mission calls for cancer research and treatment",
            "Climate-neutral cities mission funding opportunities",
            "Ocean and waters mission calls for pollution reduction",
            "Soil health mission grants for sustainable agriculture",
            "Adaptation to climate change mission funding",
            
            # Partnership queries
            "European Partnership calls for clean hydrogen",
            "Co-funded partnership opportunities in batteries",
            "Joint Undertaking calls for high-performance computing",
            "Public-private partnership grants for pharmaceuticals",
            "ERA-NET calls for joint national-EU research",
            
            # Specific action types
            "Coordination and Support Actions for standardization",
            "Research and Innovation Actions for fundamental research",
            "Innovation Actions for market-ready solutions",
            "Programme Co-fund actions for member state alignment",
            "Pre-commercial procurement calls for public sector",
            
            # Budget and funding queries
            "Calls with budgets over €10 million for large consortia",
            "Small grants under €2 million for startups",
            "Lump-sum funding opportunities for simplified management",
            "Calls with 100% funding rate for non-profit organizations",
            "Grants with 70% funding rate for industry partners",
            
            # Geographic and eligibility queries
            "Calls open to associated countries like UK and Switzerland",
            "Widening participation calls for less developed regions",
            "Calls specifically for SME participation and coordination",
            "Opportunities for public authorities and government bodies",
            "Calls requiring international cooperation beyond Europe"
        ]
        
        results = []
        successful_parses = 0
        failed_parses = 0
        
        print(f"🔍 Testing {len(additional_questions)} additional questions...")
        print()
        
        for i, query in enumerate(additional_questions):
            print(f"{i+1:2d}. Testing: '{query}'")
            
            try:
                # Step 1: Parse query with hybrid parser
                parse_start = time.time()
                filters = hybrid_parser.parse_query(query)
                parse_time = time.time() - parse_start
                
                # Step 2: Execute search for queries with specific intents
                search_time = 0
                results_count = 0
                
                if "no_filters" not in filters.user_intent_detected:
                    search_start = time.time()
                    search_results = call_search.search_calls_enhanced(
                        query=filters.clean_query,
                        max_results=3,  # Limit to 3 for testing
                        enable_facet_analysis=False  # Faster testing
                    )
                    search_time = time.time() - search_start
                    results_count = len(search_results.get('results', []))
                
                results.append({
                    'query': query,
                    'parser_used': filters.parser_used,
                    'parse_time': parse_time,
                    'search_time': search_time,
                    'results_count': results_count,
                    'intents': filters.user_intent_detected,
                    'confidence': filters.confidence,
                    'success': True
                })
                
                successful_parses += 1
                print(f"   ✅ Parsed ({filters.parser_used}), {results_count} results")
                
            except Exception as e:
                results.append({
                    'query': query,
                    'error': str(e),
                    'success': False
                })
                failed_parses += 1
                print(f"   ❌ Failed: {e}")
        
        # Generate summary
        print("\n" + "="*70)
        print("📊 50-QUESTION TEST SUMMARY")
        print("="*70)
        
        total_queries = len(results)
        successful_queries = successful_parses
        failed_queries = failed_parses
        
        # Calculate statistics
        parse_times = [r['parse_time'] for r in results if r['success']]
        search_times = [r['search_time'] for r in results if r['success']]
        results_counts = [r['results_count'] for r in results if r['success']]
        confidences = [r['confidence'] for r in results if r['success']]
        
        avg_parse_time = sum(parse_times) / len(parse_times) if parse_times else 0
        avg_search_time = sum(search_times) / len(search_times) if search_times else 0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        total_results = sum(results_counts)
        
        # Parser usage
        intelligent_count = sum(1 for r in results if r.get('parser_used') == 'intelligent')
        ai_count = sum(1 for r in results if r.get('parser_used') == 'ai')
        
        print(f"\n📈 Performance Metrics:")
        print(f"   Total queries: {total_queries}")
        print(f"   Successful parses: {successful_queries} ({successful_queries/total_queries*100:.1f}%)")
        print(f"   Failed parses: {failed_queries} ({failed_queries/total_queries*100:.1f}%)")
        print(f"   Average parse time: {avg_parse_time:.3f}s")
        print(f"   Average search time: {avg_search_time:.3f}s")
        print(f"   Average confidence: {avg_confidence:.2f}")
        print(f"   Total results found: {total_results}")
        
        print(f"\n🎯 Parser Usage:")
        print(f"   Intelligent parser: {intelligent_count} ({intelligent_count/successful_queries*100:.1f}%)")
        print(f"   AI parser: {ai_count} ({ai_count/successful_queries*100:.1f}%)")
        
        # Show some examples
        print(f"\n🔍 Example Successful Queries:")
        successful_examples = [r for r in results if r['success']][:5]
        for example in successful_examples:
            print(f"   - '{example['query'][:40]}...' → {example['results_count']} results")
        
        if failed_queries > 0:
            print(f"\n⚠️  Failed Queries:")
            failed_examples = [r for r in results if not r['success']]
            for example in failed_examples:
                print(f"   - '{example['query'][:40]}...' → Error: {example['error']}")
        
        # Save detailed results for analysis
        timestamp = int(time.time())
        results_filename = f"test_results_50_questions_{timestamp}.json"
        with open(results_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed results saved to: {results_filename}")
        print("✅ 50-question test completed!")
        
        return results
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required modules are available")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_50_additional_questions()