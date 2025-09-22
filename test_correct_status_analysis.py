#!/usr/bin/env python3
"""
Analysis of the correct status codes based on actual API behavior.
The facet API shows that 31094502 = "Open for submission" and returns 2 results.
"""

import requests
import json

def analyze_correct_status_codes():
    """Analyze what the correct status codes should be based on API behavior."""
    print("🔍 Analyzing Correct Status Codes Based on API Behavior")
    print("=" * 60)
    
    # The facet API response shows:
    # - status: 31094502 = "Open for submission" with 2 results
    # This means our previous correction was wrong!
    
    print("📊 Evidence from Facet API Response:")
    print("• Status: 31094502 → 'Open for submission' (count: 2)")
    print("• This means 31094502 is actually the correct code for OPEN calls")
    print()
    
    # Test with the correct status code (31094502)
    correct_query = {
        "bool": {
            "must": [
                {
                    "bool": {
                        "must": [
                            {"terms": {"type": ["1", "2", "8"]}},
                            {"terms": {"status": ["31094502"]}}  # This is actually correct!
                        ]
                    }
                },
                {
                    "bool": {
                        "should": [
                            {"phrase": {"query": "clean energy", "field": "title", "phraseSlop": 1, "boost": 200}},
                            {"phrase": {"query": "clean energy", "field": "description", "phraseSlop": 2, "boost": 100}},
                            {"phrase": {"query": "clean energy", "field": "keywords", "phraseSlop": 0, "boost": 1000}}
                        ]
                    }
                }
            ]
        }
    }
    
    print("🧪 Testing with Status Code 31094502 (Open for submission)")
    print("=" * 40)
    
    search_api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
    params = {
        "apiKey": "SEDIA",
        "pageSize": "50",
        "pageNumber": "1",
        "text": "***"
    }
    
    # Prepare multipart form data
    files = {
        "query": ("blob", json.dumps(correct_query), "application/json"),
        "languages": ("blob", json.dumps(["en"]), "application/json")
    }
    
    try:
        response = requests.post(
            search_api_url,
            params=params,
            files=files,
            timeout=20
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            total_results = data.get("totalResults", 0)
            
            print(f"✅ Search API returned {len(results)} results (total: {total_results})")
            
            if results:
                print(f"\n📋 Results found:")
                for i, result in enumerate(results, 1):
                    title = result.get('content', '') or result.get('summary', 'No title')
                    metadata = result.get('metadata', {})
                    identifier = metadata.get('identifier', ['N/A'])[0] if isinstance(metadata.get('identifier'), list) else metadata.get('identifier', 'N/A')
                    status = metadata.get('status', ['Unknown'])[0] if isinstance(metadata.get('status'), list) else metadata.get('status', 'Unknown')
                    deadline = metadata.get('deadlineDate', 'Not specified')
                    
                    print(f"{i}. {title[:100]}...")
                    print(f"   ID: {identifier}, Status: {status}, Deadline: {deadline}")
                    
                    # Check if this is the problematic 2021 call
                    if '2021' in identifier:
                        print(f"   ⚠️  This is the problematic 2021 call!")
            else:
                print(f"❌ No results found")
                
        else:
            print(f"❌ Search API returned status {response.status_code}")
            print(f"📊 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Search execution failed: {e}")

def test_all_status_codes():
    """Test what each status code actually returns."""
    print(f"\n🧪 Testing All Status Codes")
    print("=" * 40)
    
    status_codes = ["31094501", "31094502", "31094503"]
    
    for status_code in status_codes:
        print(f"\n📊 Testing status code: {status_code}")
        
        query = {
            "bool": {
                "must": [
                    {
                        "bool": {
                            "must": [
                                {"terms": {"type": ["1", "2", "8"]}},
                                {"terms": {"status": [status_code]}}
                            ]
                        }
                    }
                ]
            }
        }
        
        search_api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
        params = {
            "apiKey": "SEDIA",
            "pageSize": "10",
            "pageNumber": "1",
            "text": "***"
        }
        
        files = {
            "query": ("blob", json.dumps(query), "application/json"),
            "languages": ("blob", json.dumps(["en"]), "application/json")
        }
        
        try:
            response = requests.post(
                search_api_url,
                params=params,
                files=files,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                total_results = data.get("totalResults", 0)
                print(f"   Results: {total_results}")
            else:
                print(f"   Error: {response.status_code}")
                
        except Exception as e:
            print(f"   Failed: {e}")

def main():
    """Run the analysis."""
    print("🚀 Correct Status Code Analysis")
    print("=" * 60)
    print("Based on the facet API response, we need to REVERSE our status code mapping!")
    print()
    
    # Analyze with the correct status code
    analyze_correct_status_codes()
    
    # Test all status codes to understand what they return
    test_all_status_codes()
    
    print(f"\n📋 Conclusion:")
    print(f"• The facet API shows 31094502 = 'Open for submission' with 2 results")
    print(f"• Our previous correction was WRONG - 31094502 is actually the OPEN status")
    print(f"• We need to REVERSE the status code mapping:")
    print(f"  31094501 → ??? (need to test)")
    print(f"  31094502 → 'Open' (confirmed by API)")
    print(f"  31094503 → 'Closed' (likely correct)")
    print(f"• The issue with the 2021 call showing as open is a separate data quality issue")

if __name__ == "__main__":
    main()