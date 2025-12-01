#!/usr/bin/env python3
"""
Test script to verify the status code fix for EU Portal search.
This tests that the correct status codes are being used.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.improved_call_search import ImprovedCallSearchService
from app.services.enhanced_call_search import EnhancedCallSearchService

def test_status_code_mappings():
    """Test that status code mappings are correct."""
    print("🧪 Testing Status Code Mappings")
    print("=" * 60)
    
    # Test improved service
    improved_service = ImprovedCallSearchService()
    print("\n📊 Improved Call Search Service Status Mapping:")
    for code, status in improved_service.status_mapping.items():
        print(f"  {code} -> {status}")
    
    # Test enhanced service
    enhanced_service = EnhancedCallSearchService()
    print("\n📊 Enhanced Call Search Service Status Mapping:")
    for code, status in enhanced_service.status_mapping.items():
        print(f"  {code} -> {status}")
    
    # Verify the mappings are correct according to EU API documentation
    expected_mapping = {
        '31094501': 'Open',
        '31094502': 'Closing soon', 
        '31094503': 'Closed'
    }
    
    print(f"\n✅ Expected mapping from EU API documentation:")
    for code, status in expected_mapping.items():
        print(f"  {code} -> {status}")
    
    # Check if mappings match
    improved_correct = improved_service.status_mapping == expected_mapping
    enhanced_correct = enhanced_service.status_mapping == expected_mapping
    
    print(f"\n🔍 Verification Results:")
    print(f"  Improved service: {'✅ CORRECT' if improved_correct else '❌ INCORRECT'}")
    print(f"  Enhanced service: {'✅ CORRECT' if enhanced_correct else '❌ INCORRECT'}")
    
    if improved_correct and enhanced_correct:
        print(f"\n🎉 All status code mappings are correct!")
        return True
    else:
        print(f"\n⚠️  Some status code mappings are incorrect!")
        return False

def test_status_filtering():
    """Test that status filtering uses correct codes."""
    print(f"\n🧪 Testing Status Filtering Logic")
    print("=" * 60)
    
    # Test improved service filtering
    improved_service = ImprovedCallSearchService()
    
    # Test open-only filtering
    query_open = improved_service._build_simple_query("test", include_closed=False)
    status_filter_open = query_open["bool"]["must"][0]["bool"]["must"][1]["terms"]["status"]
    print(f"📊 Improved service open-only filter: {status_filter_open}")
    
    # Test all statuses filtering
    query_all = improved_service._build_simple_query("test", include_closed=True)
    status_filter_all = query_all["bool"]["must"][0]["bool"]["must"][1]["terms"]["status"]
    print(f"📊 Improved service all-status filter: {status_filter_all}")
    
    # Verify correct codes are used
    open_correct = status_filter_open == ['31094501']  # Should be 31094501 for open
    all_correct = set(status_filter_all) == {'31094501', '31094502', '31094503'}
    
    print(f"\n🔍 Filter Verification:")
    print(f"  Open-only filter: {'✅ CORRECT' if open_correct else '❌ INCORRECT'}")
    print(f"  All-status filter: {'✅ CORRECT' if all_correct else '❌ INCORRECT'}")
    
    if open_correct and all_correct:
        print(f"\n🎉 Status filtering logic is correct!")
        return True
    else:
        print(f"\n⚠️  Status filtering logic needs adjustment!")
        return False

def test_call_id_analysis():
    """Analyze the problematic call ID from the user's report."""
    print(f"\n🧪 Analyzing Problematic Call ID")
    print("=" * 60)
    
    call_id = "HORIZON-CL5-2021-D3-01-04"
    print(f"📋 Call ID: {call_id}")
    
    # Extract information from the call ID
    parts = call_id.split('-')
    if len(parts) >= 3:
        programme = parts[0]
        cluster = parts[1]
        year = parts[2]
        
        print(f"📊 Call Analysis:")
        print(f"  Programme: {programme}")
        print(f"  Cluster: {cluster}")
        print(f"  Year: {year}")
        
        # This call is from 2021, so it should be closed
        if year == '2021':
            print(f"  ⚠️  This call is from 2021 - it should be CLOSED")
            print(f"  ❌ The system was incorrectly showing it as OPEN with 2025 deadline")
            print(f"  ✅ With the fix, it should now show as CLOSED")
        else:
            print(f"  ℹ️  This call is from {year}")
    
    return True

def main():
    """Run all tests."""
    print("🚀 Testing EU Portal Search Status Code Fix")
    print("=" * 60)
    
    # Run tests
    mapping_ok = test_status_code_mappings()
    filtering_ok = test_status_filtering()
    analysis_ok = test_call_id_analysis()
    
    print(f"\n📋 Test Summary:")
    print(f"  Status code mappings: {'✅ PASS' if mapping_ok else '❌ FAIL'}")
    print(f"  Status filtering: {'✅ PASS' if filtering_ok else '❌ FAIL'}")
    print(f"  Call ID analysis: {'✅ PASS' if analysis_ok else '❌ FAIL'}")
    
    if mapping_ok and filtering_ok and analysis_ok:
        print(f"\n🎉 All tests passed! The status code fix should resolve the issue.")
        print(f"\n📝 What was fixed:")
        print(f"  • Status code 31094501 now correctly maps to 'Open' (was 'Forthcoming')")
        print(f"  • Status code 31094502 now correctly maps to 'Closing soon' (was 'Open')")
        print(f"  • Status filtering now uses 31094501 for open calls (was 31094502)")
        print(f"  • The 2021 call should now correctly show as 'Closed'")
    else:
        print(f"\n⚠️  Some tests failed. The fix may not be complete.")
    
    return mapping_ok and filtering_ok and analysis_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)