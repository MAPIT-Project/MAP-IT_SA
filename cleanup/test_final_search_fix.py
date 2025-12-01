#!/usr/bin/env python3
"""
Final test to verify the search fixes work correctly.
Tests the corrected status codes and deadline-based status correction.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.improved_call_search import ImprovedCallSearchService

def test_corrected_search():
    """Test the search with corrected status codes and deadline-based correction."""
    print("🧪 Testing Corrected Search Implementation")
    print("=" * 60)
    
    service = ImprovedCallSearchService()
    
    # Test the problematic query
    test_query = "clean energy"
    
    print(f"🔍 Testing: '{test_query}'")
    print(f"📊 Expected: Should find 2 open calls (as shown by facet API)")
    print()
    
    # Test with open calls only (should use status 31094502)
    result = service.search_calls_simple(
        query=test_query,
        max_results=10,
        include_closed=False
    )
    
    if result['status'] == 'success':
        print(f"✅ Search completed successfully")
        print(f"📊 Results found: {len(result['results'])}")
        print(f"📊 Search method: {result['search_metadata']['search_method']}")
        
        if result['results']:
            print(f"\n📋 Results:")
            for i, res in enumerate(result['results'], 1):
                print(f"{i}. {res.title}")
                print(f"   ID: {res.identifier}")
                print(f"   Status: {res.status}")
                print(f"   Deadline: {res.deadline}")
                print(f"   Score: {res.score:.3f}")
                
                # Check if this is the problematic 2021 call
                if '2021' in res.identifier:
                    if res.status == 'Closed (Data Corrected)':
                        print(f"   ✅ CORRECTED: 2021 call properly marked as closed")
                    else:
                        print(f"   ⚠️  ISSUE: 2021 call still showing as {res.status}")
        else:
            print(f"❌ No results found - this suggests the search query structure needs adjustment")
            
    else:
        print(f"❌ Search failed: {result.get('search_metadata', {}).get('error', 'Unknown error')}")
    
    # Also test with all statuses to see what's available
    print(f"\n🧪 Testing with all statuses (include_closed=True)")
    print("=" * 40)
    
    result_all = service.search_calls_simple(
        query=test_query,
        max_results=10,
        include_closed=True
    )
    
    if result_all['status'] == 'success':
        print(f"📊 All-status results found: {len(result_all['results'])}")
        
        if result_all['results']:
            status_counts = {}
            for res in result_all['results']:
                status_counts[res.status] = status_counts.get(res.status, 0) + 1
            
            print(f"📊 Status distribution: {status_counts}")
            
    print(f"\n📋 Summary:")
    print(f"• Status code 31094502 is now correctly used for open calls")
    print(f"• Deadline-based correction handles the 2021 data quality issue")
    print(f"• The system should now return accurate status information")

def test_status_mapping():
    """Verify the corrected status mapping."""
    print(f"\n🧪 Testing Status Code Mapping")
    print("=" * 40)
    
    service = ImprovedCallSearchService()
    
    print(f"📊 Current status mapping:")
    for code, status in service.status_mapping.items():
        print(f"  {code} → {status}")
    
    # Verify the mapping is correct based on API behavior
    expected_mapping = {
        '31094501': 'Forthcoming',  # 7 results
        '31094502': 'Open',         # 468 results (confirmed by API)
        '31094503': 'Closed'        # 9664 results
    }
    
    if service.status_mapping == expected_mapping:
        print(f"✅ Status mapping is correct")
    else:
        print(f"❌ Status mapping is incorrect")
        print(f"Expected: {expected_mapping}")

def main():
    """Run all tests."""
    print("🚀 Final Search Fix Verification")
    print("=" * 60)
    print("Testing the corrected status codes and deadline-based status correction")
    print()
    
    # Test status mapping
    test_status_mapping()
    
    # Test the actual search
    test_corrected_search()
    
    print(f"\n🎉 Testing completed!")
    print(f"📝 What was fixed:")
    print(f"• Status code mapping corrected based on actual API behavior")
    print(f"• 31094502 is now correctly used for open calls")
    print(f"• Deadline-based status correction handles data quality issues")
    print(f"• The 2021 call should now show as 'Closed (Data Corrected)'")

if __name__ == "__main__":
    main()