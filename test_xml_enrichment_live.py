#!/usr/bin/env python3
"""
Live test for XML enrichment functionality using real CORDIS data
"""

import os
from cordisBased_RAG_function_new_V3 import CordisRAG

def test_xml_enrichment_with_real_data():
    """Test XML enrichment with real CORDIS API data"""
    print("="*60)
    print("TESTING XML ENRICHMENT WITH REAL CORDIS DATA")
    print("="*60)
    
    try:
        # Initialize RAG system
        rag = CordisRAG()
        
        # First, get some real project data from CORDIS API
        print("Step 1: Fetching real project data from CORDIS API...")
        queries = ["artificial intelligence", "machine learning"]
        project_items = rag._search_cordis_api(queries, max_results=3)
        
        if not project_items:
            print("❌ No project items found from CORDIS API")
            return False
            
        print(f"✓ Found {len(project_items)} projects from CORDIS API")
        
        # Extract project data
        print("\nStep 2: Extracting project data...")
        project_data = []
        for item in project_items[:2]:  # Test with first 2 projects
            extracted = rag._extract_project_data(item)
            project_data.append(extracted)
            print(f"  - Project: {extracted.get('title', 'Unknown')[:50]}...")
            print(f"    RCN: {extracted.get('rcn', 'N/A')}")
        
        # Test XML enrichment
        print("\nStep 3: Testing XML enrichment...")
        enriched_projects = rag._enrich_with_xml_data(project_data)
        
        # Analyze results
        print("\nStep 4: Analyzing enrichment results...")
        success_count = 0
        for i, (original, enriched) in enumerate(zip(project_data, enriched_projects)):
            print(f"\n--- Project {i+1}: {original.get('title', 'Unknown')[:40]}... ---")
            print(f"Original keys: {len(original.keys())}")
            print(f"Enriched keys: {len(enriched.keys())}")
            
            # Check for XML enrichments
            xml_additions = []
            
            # Check if objective was enhanced
            if (enriched.get('objective', '') != original.get('objective', '') and 
                len(enriched.get('objective', '')) > len(original.get('objective', ''))):
                xml_additions.append('enhanced_objective')
            
            # Check for new fields
            if 'call_id' in enriched and enriched['call_id'] != 'Unknown':
                xml_additions.append('call_id')
            if 'eu_contribution' in enriched and enriched['eu_contribution'] != 'Unknown':
                xml_additions.append('eu_contribution')
            if 'detailed_participants' in enriched:
                xml_additions.append('detailed_participants')
                
            if xml_additions:
                print(f"✓ XML enrichments added: {xml_additions}")
                success_count += 1
            else:
                print("⚠️ No XML enrichments detected")
                
        print(f"\n{'='*60}")
        print(f"RESULTS: {success_count}/{len(project_data)} projects successfully enriched")
        
        if success_count > 0:
            print("🎉 XML enrichment is working!")
            return True
        else:
            print("⚠️ XML enrichment needs investigation")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_xml_url_structure():
    """Test different XML URL structures to find the correct one"""
    print("\n" + "="*60)
    print("TESTING XML URL STRUCTURES")
    print("="*60)
    
    import requests
    
    # Sample RCN to test with (this is a known project ID)
    test_rcns = ["223041", "101016775", "101017716"]
    
    url_patterns = [
        "https://cordis.europa.eu/project/id/{rcn}?format=xml",
        "https://cordis.europa.eu/project/rcn/{rcn}?format=xml", 
        "https://cordis.europa.eu/project/{rcn}?format=xml",
        "https://cordis.europa.eu/api/projects/{rcn}?format=xml",
        "https://cordis.europa.eu/api/project/{rcn}?format=xml"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
    }
    
    for rcn in test_rcns:
        print(f"\nTesting RCN: {rcn}")
        for pattern in url_patterns:
            url = pattern.format(rcn=rcn)
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200 and 'xml' in response.headers.get('content-type', '').lower():
                    print(f"✓ SUCCESS: {url}")
                    print(f"  Content-Type: {response.headers.get('content-type')}")
                    print(f"  Content length: {len(response.content)} bytes")
                    if b'<' in response.content[:100]:
                        print(f"  Contains XML: Yes")
                    return True
                else:
                    print(f"✗ FAILED: {url} (Status: {response.status_code})")
            except Exception as e:
                print(f"✗ ERROR: {url} - {e}")
    
    return False

if __name__ == "__main__":
    # Test XML URL structure first
    url_test_passed = test_xml_url_structure()
    
    if url_test_passed:
        print("\n✓ Found working XML URL structure")
    else:
        print("\n⚠️ No working XML URL found, but continuing with main test...")
    
    # Run main test
    test_passed = test_xml_enrichment_with_real_data()
    
    if test_passed:
        print("\n🎉 XML ENRICHMENT TESTS PASSED!")
    else:
        print("\n❌ XML enrichment needs further investigation")
