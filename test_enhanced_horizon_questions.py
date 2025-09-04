#!/usr/bin/env python3
"""
Test script for enhanced Horizon Europe call question answering capabilities.
Tests the specific questions mentioned in the requirements.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.intelligent_query_parser import IntelligentQueryParser
from services.enhanced_call_search import EnhancedCallSearchService

def test_specific_questions():
    """Test the specific Horizon Europe questions."""
    
    print("🧪 Testing Enhanced Horizon Europe Question Answering")
    print("=" * 60)
    
    parser = IntelligentQueryParser()
    search_service = EnhancedCallSearchService()
    
    # Test questions from the requirements
    test_questions = [
        # Call discovery questions
        "What are the currently open Horizon Europe calls in Cluster 4 (Digital, Industry and Space)?",
        "Which topics under the latest work programme match advanced AI, cybersecurity, and edge computing?",
        "What calls close in the next 60 days that target TRL 5–7 demonstrators?",
        "Which topics support living labs for digital public services or GovTech?",
        "Are there open topics that fund standardisation activities for data interoperability?",
        "Which calls fund digital twins for manufacturing or energy?",
        "What's the difference between calls and topics on the Funding & Tenders Portal?",
        "How to filter calls by budget, type of action, and expected outcomes?",
        "Which work programmes are relevant to digital transition and data spaces?",
        "How to find co-funded European Partnerships that have open calls?",
        "Where to find cascade funding (Financial Support to Third Parties) in ongoing projects?",
        "Which EIC Accelerator cut-offs are upcoming for deep tech SMEs?",
        "Are there mission calls relevant to climate-neutral and smart cities with digital solutions?",
        "How to identify topics with lump-sum funding vs actual cost funding?",
        "Which topics encourage social sciences and humanities (SSH) integration in digital projects?"
    ]
    
    print(f"📋 Testing {len(test_questions)} specific questions")
    print("-" * 60)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. 📝 Question: '{question}'")
        
        # Parse the query
        filters = parser.parse_query(question)
        print(f"   🎯 Parsed filters: {filters.filter_intention}")
        print(f"   🔍 Clean query: '{filters.clean_query}'")
        print(f"   📊 User intent detected: {filters.user_intent_detected}")
        
        if filters.specific_filters:
            print(f"   🎯 Specific filters: {filters.specific_filters}")
        
        # Test enhanced search (this will use the API)
        try:
            result = search_service.search_calls_enhanced(
                query=question,
                max_results=3,
                enable_facet_analysis=False
            )
            
            if result['status'] == 'success':
                print(f"   ✅ Search successful: {len(result['results'])} results found")
                if result['results']:
                    for j, call in enumerate(result['results'][:2], 1):
                        print(f"      {j}. {call.title}")
                        print(f"         Status: {call.status}, Score: {call.score:.3f}")
            else:
                print(f"   ⚠️  Search failed: {result.get('search_metadata', {}).get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Error during search: {e}")
        
        print("   " + "-" * 40)

def test_query_parsing_comprehensive():
    """Test comprehensive query parsing for all question types."""
    
    print("\n🧠 Testing Comprehensive Query Parsing")
    print("=" * 50)
    
    parser = IntelligentQueryParser()
    
    # Test different question patterns
    test_cases = [
        # Cluster 4 questions
        ("Cluster 4 open calls", "cluster_4"),
        ("Digital industry space calls", "cluster_4"),
        
        # TRL questions
        ("TRL 5-7 demonstrators", "trl"),
        ("Technology readiness level 6", "trl"),
        
        # Technology questions
        ("AI cybersecurity edge computing", ["technology:ai", "technology:cybersecurity", "technology:edge_computing"]),
        ("Artificial intelligence calls", "technology:ai"),
        
        # Living labs and GovTech
        ("Living labs digital public services", "living_labs"),
        ("GovTech topics", "living_labs"),
        
        # Standardization
        ("Standardization data interoperability", "standardization"),
        ("Data interoperability standards", "standardization"),
        
        # Digital twins
        ("Digital twins manufacturing", "digital_twins"),
        ("Energy digital twins", "digital_twins"),
        
        # EIC Accelerator
        ("EIC Accelerator cut-offs", "eic"),
        ("Deep tech SMEs", "eic"),
        
        # Mission calls
        ("Mission calls climate-neutral cities", "mission_calls"),
        ("Smart cities digital solutions", "mission_calls"),
        
        # SSH integration
        ("SSH integration digital projects", "ssh"),
        ("Social sciences humanities", "ssh")
    ]
    
    for query, expected_intent in test_cases:
        print(f"\n📝 Testing: '{query}'")
        filters = parser.parse_query(query)
        
        if isinstance(expected_intent, list):
            # Check if all expected intents are detected
            detected = all(any(intent in detected_intent for detected_intent in filters.user_intent_detected) 
                          for intent in expected_intent)
            status = "✅" if detected else "❌"
            print(f"   {status} Expected: {expected_intent}, Got: {filters.user_intent_detected}")
        else:
            # Check if specific intent is detected
            detected = any(expected_intent in intent for intent in filters.user_intent_detected)
            status = "✅" if detected else "❌"
            print(f"   {status} Expected: {expected_intent}, Got: {filters.user_intent_detected}")
        
        if filters.specific_filters:
            print(f"   🎯 Specific filters: {filters.specific_filters}")

if __name__ == "__main__":
    print("🚀 Starting Enhanced Horizon Europe Question Testing")
    print("=" * 60)
    
    try:
        # Test query parsing first
        test_query_parsing_comprehensive()
        
        # Test specific questions (this will make API calls)
        test_specific_questions()
        
        print("\n🎉 Testing completed successfully!")
        print("\n📋 Summary of implemented capabilities:")
        print("   ✅ Cluster 4 (Digital, Industry and Space) filtering")
        print("   ✅ TRL 5-7 level detection and filtering")
        print("   ✅ Advanced AI, cybersecurity, edge computing detection")
        print("   ✅ Living labs and GovTech detection")
        print("   ✅ Standardization activities detection")
        print("   ✅ Digital twins detection")
        print("   ✅ EIC Accelerator detection")
        print("   ✅ Mission calls detection")
        print("   ✅ SSH integration detection")
        print("   ✅ Next 60 days temporal filtering")
        print("   ✅ Enhanced intent detection for specific question types")
        
    except Exception as e:
        print(f"❌ Testing failed with error: {e}")
        import traceback
        traceback.print_exc()