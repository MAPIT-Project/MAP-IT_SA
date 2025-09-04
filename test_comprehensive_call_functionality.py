#!/usr/bin/env python3
"""
Comprehensive test of the enhanced call search functionality.
Tests various types of questions the system should be able to answer.
"""

import sys
import os
import logging
import time

# Add the current directory to Python path for proper imports
sys.path.insert(0, os.path.dirname(__file__))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_comprehensive_call_functionality():
    """Test various types of call-related questions."""
    
    try:
        from app.services.enhanced_call_search import EnhancedCallSearchService
        from app.services.intelligent_query_parser import IntelligentQueryParser
        from app.services.call_specific_rag import CallSpecificRAG
        
        print("🧪 Comprehensive Call Functionality Test")
        print("=" * 60)
        
        # Initialize services
        search_service = EnhancedCallSearchService()
        query_parser = IntelligentQueryParser()
        call_rag = CallSpecificRAG()
        
        # Test categories
        test_categories = [
            {
                'name': 'Status-based Queries',
                'queries': [
                    "What open calls are available for quantum computing?",
                    "Show me forthcoming calls about artificial intelligence",
                    "Are there any closed calls related to climate change?",
                    "Recent calls for health research",
                    "Latest funding opportunities in digital transformation"
                ]
            },
            {
                'name': 'Specific Call/Topic Identifiers',
                'queries': [
                    "HORIZON-CL4-2024-DATA-01-01 requirements",
                    "Tell me about EIC Accelerator grants",
                    "ERC Starting Grant deadlines",
                    "MSCA Postdoctoral Fellowship eligibility"
                ]
            },
            {
                'name': 'Cluster-specific Queries',
                'queries': [
                    "Health cluster calls for 2024",
                    "Digital transformation topics",
                    "Climate energy mobility funding",
                    "Food and bioeconomy opportunities"
                ]
            },
            {
                'name': 'General Call Searches',
                'queries': [
                    "calls about quantum mechanics",
                    "funding for renewable energy",
                    "research grants for AI in healthcare",
                    "opportunities for cybersecurity research"
                ]
            },
            {
                'name': 'Edge Cases',
                'queries': [
                    "calls",  # Very broad
                    "xyz123 calls",  # Non-existent topic
                    "calls about quantum physics and artificial intelligence and climate change",  # Multiple topics
                    ""  # Empty query (should handle gracefully)
                ]
            }
        ]
        
        for category in test_categories:
            print(f"\n📋 {category['name']}")
            print("-" * 40)
            
            for query in category['queries']:
                if not query.strip():  # Skip empty queries
                    continue
                    
                print(f"\n🔍 Query: '{query}'")
                print("─" * 30)
                
                # Test query parsing
                try:
                    parsed_filters = query_parser.parse_query(query)
                    print(f"✅ Parsed as: {parsed_filters.filter_intention}")
                    if parsed_filters.status_filter:
                        print(f"   Status filter: {parsed_filters.status_filter}")
                    print(f"   Clean query: '{parsed_filters.clean_query}'")
                except Exception as e:
                    print(f"❌ Query parsing failed: {e}")
                    continue
                
                # Test enhanced search
                try:
                    start_time = time.time()
                    result = search_service.search_calls_enhanced(
                        query=query,
                        max_results=3,  # Limit to top 3 for readability
                        enable_facet_analysis=True
                    )
                    elapsed = time.time() - start_time
                    
                    if result['status'] == 'success':
                        print(f"✅ Search completed in {elapsed:.2f}s")
                        print(f"📊 Results: {len(result['results'])}")
                        
                        if result['results']:
                            for i, res in enumerate(result['results'], 1):
                                status_emoji = "🟢" if res.status == "Open" else "🔵" if res.status == "Forthcoming" else "🔴"
                                print(f"  {i}. {status_emoji} {res.title[:60]}...")
                                print(f"     Status: {res.status}, Deadline: {res.deadline}")
                                print(f"     Score: {res.score:.3f}, ID: {res.identifier}")
                        else:
                            # Check if there's a filter explanation
                            filter_explanation = result['search_metadata'].get('filter_explanation', '')
                            if filter_explanation:
                                print(f"ℹ️  {filter_explanation}")
                            else:
                                print("ℹ️  No results found for this query")
                                
                        # Show facet info if available
                        if result['facets']:
                            print(f"📈 Facet categories: {len(result['facets'])}")
                            
                    else:
                        error_msg = result.get('search_metadata', {}).get('error', 'Unknown error')
                        print(f"❌ Search failed: {error_msg}")
                        
                except Exception as e:
                    print(f"❌ Search execution failed: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Small delay between queries to avoid rate limiting
                time.sleep(0.5)
        
        print("\n🎉 Comprehensive testing completed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_comprehensive_call_functionality()