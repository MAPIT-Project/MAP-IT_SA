#!/usr/bin/env python3
"""
Test to investigate why we're only finding 1 result instead of 2.
The facet API shows 2 results for 'clean energy' with status 31094502.
"""

import requests
import json

def test_different_query_structures():
    """Test different query structures to find the missing result."""
    print("🔍 Investigating Missing Result Issue")
    print("=" * 60)
    print("Facet API shows 2 results, but search only returns 1")
    print("Testing different query structures to find the missing call")
    print()
    
    search_api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
    params = {
        "apiKey": "SEDIA",
        "pageSize": "50",
        "pageNumber": "1",
        "text": "***"
    }
    
    # Test 1: Simple match query (like our current implementation)
    print("🧪 Test 1: Simple Match Query (Current Implementation)")
    simple_query = {
        "bool": {
            "must": [
                {"terms": {"type": ["1", "2", "8"]}},
                {"terms": {"status": ["31094502"]}}
            ],
            "should": [
                {"match": {"title": {"query": "clean energy", "boost": 2.0}}},
                {"match": {"description": {"query": "clean energy", "boost": 1.0}}},
                {"match": {"keywords": {"query": "clean energy", "boost": 1.5}}}
            ]
        }
    }
    
    files = {
        "query": ("blob", json.dumps(simple_query), "application/json"),
        "languages": ("blob", json.dumps(["en"]), "application/json")
    }
    
    try:
        response = requests.post(search_api_url, params=params, files=files, timeout=20)
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Results: {len(data.get('results', []))}")
            if data.get('results'):
                for result in data.get('results', []):
                    title = result.get('content', 'No title')
                    identifier = result.get('metadata', {}).get('identifier', ['N/A'])[0]
                    print(f"   • {identifier}: {title[:80]}...")
        else:
            print(f"❌ Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 2: Phrase query (like the facet API uses)
    print(f"\n🧪 Test 2: Phrase Query (Like Facet API)")
    phrase_query = {
        "bool": {
            "must": [
                {"terms": {"type": ["1", "2", "8"]}},
                {"terms": {"status": ["31094502"]}}
            ],
            "should": [
                {"phrase": {"query": "clean energy", "field": "title", "phraseSlop": 1, "boost": 200}},
                {"phrase": {"query": "clean energy", "field": "description", "phraseSlop": 2, "boost": 100}},
                {"phrase": {"query": "clean energy", "field": "keywords", "phraseSlop": 0, "boost": 1000}}
            ]
        }
    }
    
    files = {
        "query": ("blob", json.dumps(phrase_query), "application/json"),
        "languages": ("blob", json.dumps(["en"]), "application/json")
    }
    
    try:
        response = requests.post(search_api_url, params=params, files=files, timeout=20)
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Results: {len(data.get('results', []))}")
            if data.get('results'):
                for result in data.get('results', []):
                    title = result.get('content', 'No title')
                    identifier = result.get('metadata', {}).get('identifier', ['N/A'])[0]
                    print(f"   • {identifier}: {title[:80]}...")
        else:
            print(f"❌ Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 3: No text filtering (just status filter)
    print(f"\n🧪 Test 3: No Text Filter (Just Status)")
    no_text_query = {
        "bool": {
            "must": [
                {"terms": {"type": ["1", "2", "8"]}},
                {"terms": {"status": ["31094502"]}}
            ]
        }
    }
    
    files = {
        "query": ("blob", json.dumps(no_text_query), "application/json"),
        "languages": ("blob", json.dumps(["en"]), "application/json")
    }
    
    try:
        response = requests.post(search_api_url, params=params, files=files, timeout=20)
        if response.status_code == 200:
            data = response.json()
            total_results = data.get('totalResults', 0)
            print(f"📊 Total results with status 31094502: {total_results}")
            print(f"📊 Returned results: {len(data.get('results', []))}")
            
            # Show first few results to see what's available
            if data.get('results'):
                print(f"📋 Sample results:")
                for i, result in enumerate(data.get('results', [])[:5], 1):
                    title = result.get('content', 'No title')
                    identifier = result.get('metadata', {}).get('identifier', ['N/A'])[0]
                    keywords = result.get('metadata', {}).get('keywords', ['N/A'])
                    print(f"{i}. {identifier}: {title[:60]}...")
                    print(f"   Keywords: {keywords}")
        else:
            print(f"❌ Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed: {e}")

def test_broader_search():
    """Test a broader search to find the missing call."""
    print(f"\n🔍 Testing Broader Search Terms")
    print("=" * 40)
    
    search_api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
    params = {
        "apiKey": "SEDIA",
        "pageSize": "50",
        "pageNumber": "1",
        "text": "***"
    }
    
    # Test different search terms that might match the missing call
    search_terms = ["energy", "clean", "climate", "renewable", "sustainable"]
    
    for term in search_terms:
        query = {
            "bool": {
                "must": [
                    {"terms": {"type": ["1", "2", "8"]}},
                    {"terms": {"status": ["31094502"]}}
                ],
                "should": [
                    {"match": {"title": {"query": term, "boost": 2.0}}},
                    {"match": {"description": {"query": term, "boost": 1.0}}}
                ]
            }
        }
        
        files = {
            "query": ("blob", json.dumps(query), "application/json"),
            "languages": ("blob", json.dumps(["en"]), "application/json")
        }
        
        try:
            response = requests.post(search_api_url, params=params, files=files, timeout=15)
            if response.status_code == 200:
                data = response.json()
                results = len(data.get('results', []))
                if results > 0:
                    print(f"📊 '{term}': {results} results")
                    if results == 2:
                        print(f"   ✅ Found the missing call with term '{term}'!")
                        # Show the results
                        for result in data.get('results', []):
                            title = result.get('content', 'No title')
                            identifier = result.get('metadata', {}).get('identifier', ['N/A'])[0]
                            print(f"   • {identifier}: {title[:80]}...")
            else:
                print(f"📊 '{term}': Error {response.status_code}")
        except Exception as e:
            print(f"📊 '{term}': Failed {e}")

def main():
    """Run the investigation."""
    print("🚀 Investigating Missing Search Result")
    print("=" * 60)
    print("Problem: Facet API shows 2 results, but search returns only 1")
    print("Goal: Find why the second call is not being returned")
    print()
    
    # Test different query structures
    test_different_query_structures()
    
    # Test broader search terms
    test_broader_search()
    
    print(f"\n📋 Conclusion:")
    print(f"• The issue might be with the search query structure")
    print(f"• The missing call might not contain 'clean energy' specifically")
    print(f"• We may need to use phrase queries instead of match queries")
    print(f"• The search might be too restrictive")

if __name__ == "__main__":
    main()