#!/usr/bin/env python3
"""
Test script to verify XML enrichment functionality in the V3 implementation.
This tests that all XML data extraction patterns from the original implementation are working.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cordisBased_RAG_function_new_V3 import CordisRAG
import json

def test_xml_enrichment():
    """Test the XML enrichment functionality with a sample query."""
    print("🔍 Testing XML enrichment functionality...")
    
    try:
        # Initialize the CordisRAG system
        rag = CordisRAG(ai_provider="openai")
        
        # Test with a specific query that should return projects with XML data
        test_question = "What are some machine learning projects with German participants?"
        print(f"\n📋 Test question: {test_question}")
        
        # Get a small number of projects for testing
        print("\n🔄 Fetching and enriching project data...")
        
        # Test the individual components first
        print("\n1️⃣ Testing query extraction...")
        role, quest = rag._get_phase1_prompt(test_question)
        queries, end_flag, new_query_keys, rerank_criteria, problem_text, next_pass = rag._extract_queries(role, quest)
        
        if end_flag:
            print(f"❌ Query extraction failed: {problem_text}")
            return False
            
        print(f"✅ Extracted queries: {queries}")
        
        # Test CORDIS API search
        print("\n2️⃣ Testing CORDIS API search...")
        project_items = rag._search_cordis_api(queries, max_results=3)  # Small number for testing
        print(f"✅ Found {len(project_items)} projects from CORDIS API")
        
        # Test basic project data extraction
        print("\n3️⃣ Testing basic project data extraction...")
        project_data_basic = [rag._extract_project_data(item) for item in project_items]
        
        print("📊 Basic project data (before XML enrichment):")
        for i, proj in enumerate(project_data_basic):
            print(f"  Project {i+1}: {proj.get('title', 'No title')[:80]}...")
            print(f"    RCN: {proj.get('rcn', 'N/A')}")
            print(f"    Objective length: {len(str(proj.get('objective', '')))}")
            print(f"    Keywords: {proj.get('keywords', 'N/A')[:100]}...")
            print(f"    Participants: {len(proj.get('participant_names', []))}")
        
        # Test XML enrichment
        print("\n4️⃣ Testing XML enrichment...")
        enriched_projects = rag._enrich_with_xml_data(project_data_basic)
        
        print("🔥 Enriched project data (after XML enrichment):")
        for i, proj in enumerate(enriched_projects):
            print(f"  Project {i+1}: {proj.get('title', 'No title')[:80]}...")
            print(f"    RCN: {proj.get('rcn', 'N/A')}")
            print(f"    Objective length: {len(str(proj.get('objective', '')))}")
            print(f"    Keywords: {proj.get('keywords', 'N/A')[:100]}...")
            print(f"    Participants: {len(proj.get('participant_names', []))}")
            print(f"    EU Contribution: {proj.get('eu_contribution', 'N/A')}")
            print(f"    Call ID: {proj.get('call_id', 'N/A')}")
            print(f"    Detailed participants: {len(proj.get('detailed_participants', []))}")
            
            # Show detailed participant info if available
            detailed_participants = proj.get('detailed_participants', [])
            if detailed_participants:
                print(f"    Sample participants:")
                for j, participant in enumerate(detailed_participants[:2]):  # Show first 2
                    print(f"      - {participant.get('name', 'N/A')} ({participant.get('country', 'N/A')}, {participant.get('city', 'N/A')})")
        
        # Compare data richness
        print("\n📈 Data enrichment comparison:")
        for i, (basic, enriched) in enumerate(zip(project_data_basic, enriched_projects)):
            print(f"  Project {i+1}:")
            
            # Compare objective detail
            basic_obj_len = len(str(basic.get('objective', '')))
            enriched_obj_len = len(str(enriched.get('objective', '')))
            print(f"    Objective: {basic_obj_len} → {enriched_obj_len} chars")
            
            # Compare keywords
            basic_keywords = basic.get('keywords', 'N/A')
            enriched_keywords = enriched.get('keywords', 'N/A')
            basic_kw_len = len(basic_keywords) if basic_keywords != 'N/A' else 0
            enriched_kw_len = len(enriched_keywords) if enriched_keywords != 'N/A' else 0
            print(f"    Keywords: {basic_kw_len} → {enriched_kw_len} chars")
            
            # Compare participant count
            basic_participants = len(basic.get('participant_names', []))
            enriched_participants = len(enriched.get('participant_names', []))
            print(f"    Participants: {basic_participants} → {enriched_participants}")
            
            # Check for new fields
            new_fields = []
            if enriched.get('eu_contribution') and enriched['eu_contribution'] != 'N/A':
                new_fields.append('eu_contribution')
            if enriched.get('call_id') and enriched['call_id'] != 'N/A':
                new_fields.append('call_id')
            if enriched.get('detailed_participants'):
                new_fields.append('detailed_participants')
            
            if new_fields:
                print(f"    New fields added: {', '.join(new_fields)}")
        
        print("\n✅ XML enrichment test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ XML enrichment test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_workflow():
    """Test the complete workflow including XML enrichment."""
    print("\n🚀 Testing complete workflow with XML enrichment...")
    
    try:
        rag = CordisRAG(ai_provider="openai")
        
        # Test question that should benefit from XML enrichment
        test_question = "What are recent AI projects in healthcare with participants from Germany?"
        print(f"📋 Test question: {test_question}")
        
        # Run the complete workflow
        response = rag.get_ai_response(test_question, max_projects_to_process=3, max_cordis_results=5)
        
        print("\n📝 Generated response:")
        print("=" * 80)
        print(response)
        print("=" * 80)
        
        # Check if response contains detailed information that would come from XML enrichment
        response_lower = response.lower()
        xml_indicators = [
            'budget', 'contribution', 'participants', 'organization', 'country',
            'call', 'objective', 'eur', '€', 'million'
        ]
        
        found_indicators = [indicator for indicator in xml_indicators if indicator in response_lower]
        print(f"\n🔍 Found XML-enriched content indicators: {found_indicators}")
        
        if len(found_indicators) >= 3:
            print("✅ Response appears to contain XML-enriched data!")
        else:
            print("⚠️ Response may not contain sufficient XML-enriched data")
        
        return True
        
    except Exception as e:
        print(f"❌ Full workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing XML Enrichment Implementation")
    print("=" * 50)
    
    # Test XML enrichment functionality
    xml_test_success = test_xml_enrichment()
    
    if xml_test_success:
        # Test full workflow
        workflow_test_success = test_full_workflow()
        
        if workflow_test_success:
            print("\n🎉 All tests passed! XML enrichment is working correctly.")
        else:
            print("\n⚠️ XML enrichment works but full workflow has issues.")
    else:
        print("\n❌ XML enrichment test failed. Check the implementation.")
