#!/usr/bin/env python3
"""
Simplified test focusing only on enhanced call search functionality.
"""

import sys
import os
import logging
import time

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_enhanced_search_only():
    """Test enhanced search functionality with various query types."""
    
    try:
        from services.enhanced_call_search import EnhancedCallSearchService
        from services.intelligent_query_parser import IntelligentQueryParser
        
        print("🧪 Enhanced Call Search Functionality Test")
        print("=" * 60)
        
        # Initialize services
        search_service = EnhancedCallSearchService()
        query_parser = IntelligentQueryParser()
        
        # Test queries covering different scenarios
        test_queries = [
            # Status-based queries
            "open calls for quantum computing",
            "forthcoming artificial intelligence funding",
            "closed climate change grants",
            "recent health research opportunities",
            
            # Specific topics
            "quantum mechanics calls",
            "renewable energy funding",
            "AI in healthcare research",
            "cybersecurity grants",
            
            # Cluster-specific
            "digital transformation topics",
            "health cluster calls 2024",
            "climate energy mobility",
            
            # Edge cases
            "calls",  # Very broad
            "xyz123 funding",  # Non-existent
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            print("─" * 40)
            
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
                    max_results=3,
                    enable_facet_analysis=False  # Disable facets for faster testing
                )
                elapsed = time.time() - start_time
                
                if result['status'] == 'success':
                    print(f"✅ Search completed in {elapsed:.2f}s")
                    print(f"📊 Results: {len(result['results'])}")
                    
                    if result['results']:
                        for i, res in enumerate(result['results'], 1):
                            status_emoji = "🟢" if res.status == "Open" else "🔵" if res.status == "Forthcoming" else "🔴"
                            print(f"  {i}. {status_emoji} {res.title[:70]}...")
                            print(f"     Status: {res.status}, Deadline: {res.deadline}")
                            print(f"     Score: {res.score:.3f}")
                    else:
                        filter_explanation = result['search_metadata'].get('filter_explanation', '')
                        if filter_explanation:
                            print(f"ℹ️  {filter_explanation}")
                        else:
                            print("ℹ️  No results found")
                            
                else:
                    error_msg = result.get('search_metadata', {}).get('error', 'Unknown error')
                    print(f"❌ Search failed: {error_msg}")
                    
            except Exception as e:
                print(f"❌ Search execution failed: {e}")
                import traceback
                traceback.print_exc()
            
            # Small delay between queries
            time.sleep(0.5)
        
        print("\n🎉 Enhanced search testing completed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_search_only()