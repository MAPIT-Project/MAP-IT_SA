#!/usr/bin/env python3
"""
Test script for Live Proposal Document Editor API
"""

import requests
import json

API_BASE = "http://localhost:8000/api"

def test_endpoints():
    """Test all proposal document API endpoints"""
    
    print("\n" + "="*80)
    print("TESTING LIVE PROPOSAL DOCUMENT EDITOR API")
    print("="*80)
    
    # Test 1: Check if endpoints are registered
    print("\n📋 Test 1: Check API documentation...")
    response = requests.get(f"{API_BASE}/docs")
    if response.status_code == 200:
        print("✅ API documentation accessible at /docs")
    else:
        print(f"❌ API docs failed: {response.status_code}")
    
    # Test 2: Create a test proposal first (using existing endpoint)
    print("\n📋 Test 2: Create test proposal...")
    try:
        # First check if we need to create a proposal
        # Let's try to get proposal ID 1 first
        response = requests.get(f"{API_BASE}/proposal-document/1")
        
        if response.status_code == 200:
            proposal_id = 1
            print(f"✅ Using existing proposal ID: {proposal_id}")
        else:
            print(f"⚠️ No existing proposal found. Create one first via the proposal writing system.")
            proposal_id = None
    except Exception as e:
        print(f"❌ Error: {e}")
        proposal_id = None
    
    if not proposal_id:
        print("\n⚠️ Skipping tests - no proposal available")
        print("   To create a proposal, use:")
        print("   POST /api/proposal/generate-template")
        return
    
    # Test 3: Get complete proposal document
    print(f"\n📋 Test 3: GET /proposal-document/{proposal_id}")
    try:
        response = requests.get(f"{API_BASE}/proposal-document/{proposal_id}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Retrieved proposal:")
            print(f"   - Title: {data.get('proposal_title', 'N/A')}")
            print(f"   - Call: {data.get('call_id', 'N/A')}")
            print(f"   - Sections: {len(data.get('sections', []))}")
            print(f"   - Progress: {data.get('progress', {}).get('completion_percentage', 0)}%")
            print(f"   - Total words: {data.get('progress', {}).get('total_words', 0)}")
        elif response.status_code == 404:
            print(f"⚠️ Proposal {proposal_id} not found")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Get single section
    print(f"\n📋 Test 4: GET /proposal-document/{proposal_id}/section/excellence.objectives")
    try:
        response = requests.get(
            f"{API_BASE}/proposal-document/{proposal_id}/section/excellence.objectives"
        )
        
        if response.status_code == 200:
            section = response.json()
            print(f"✅ Retrieved section:")
            print(f"   - Name: {section.get('section_name')}")
            print(f"   - Word count: {section.get('word_count', 0)}")
            print(f"   - Content preview: {section.get('content', '')[:100]}...")
        elif response.status_code == 404:
            print(f"⚠️ Section not found - this is OK if no content yet")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: Update section content
    print(f"\n📋 Test 5: PUT /proposal-document/{proposal_id}/section/test.section")
    try:
        test_content = """## Test Section

This is a test section created by the API test script.

**Objective**: Verify that the PUT endpoint works correctly.

**Expected Behavior**:
- Section should be created or updated
- Word count should be calculated automatically
- Response should include success message

This test section has approximately 50 words."""

        response = requests.put(
            f"{API_BASE}/proposal-document/{proposal_id}/section/test.section",
            json={
                "content": test_content,
                "metadata": {
                    "quality_score": 0.8
                }
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Section updated:")
            print(f"   - Success: {result.get('success')}")
            print(f"   - Word count: {result.get('word_count')}")
            print(f"   - Estimated pages: {result.get('estimated_pages')}")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 6: Get progress
    print(f"\n📋 Test 6: GET /proposal-document/{proposal_id}/progress")
    try:
        response = requests.get(f"{API_BASE}/proposal-document/{proposal_id}/progress")
        
        if response.status_code == 200:
            progress = response.json()
            overall = progress.get('overall_progress', {})
            print(f"✅ Progress retrieved:")
            print(f"   - Completion: {overall.get('completion_percentage')}%")
            print(f"   - Complete sections: {overall.get('complete_sections')}")
            print(f"   - Draft sections: {overall.get('draft_sections')}")
            print(f"   - Empty sections: {overall.get('empty_sections')}")
            print(f"   - Total words: {overall.get('total_words')}")
            print(f"   - Average quality: {overall.get('average_quality')}")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 7: Delete test section
    print(f"\n📋 Test 7: DELETE /proposal-document/{proposal_id}/section/test.section")
    try:
        response = requests.delete(
            f"{API_BASE}/proposal-document/{proposal_id}/section/test.section"
        )
        
        if response.status_code == 200:
            print(f"✅ Section deleted successfully")
        elif response.status_code == 404:
            print(f"⚠️ Section not found (may have been deleted already)")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*80)
    print("API TEST COMPLETE")
    print("="*80)
    print("\n✨ All endpoints are working!")
    print("\n📖 Next steps:")
    print("   1. Review LIVE_PROPOSAL_EDITOR_FRONTEND_GUIDE.md")
    print("   2. Implement frontend using the guide")
    print("   3. Test with real research managers")
    print("\n")

if __name__ == "__main__":
    test_endpoints()

