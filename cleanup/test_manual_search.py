#!/usr/bin/env python3
"""
Test script to analyze why search returns no results despite facet API showing 2 results.
This will help identify the issue with the current search implementation.
"""

import requests
import json
import sys
import os

def test_simple_search():
    """Test a simple search query to see what's happening."""
    print("🧪 Testing Simple Search Query")
    print("=" * 60)
    
    # The query that should return results
    query = "clean energy"
    
    # Build a simpler query structure
    simple_query = {
        "bool": {
            "must": [
                {
                    "terms": {
                        "type": ["1", "2", "8"]
                    }
                },
                {
                    "terms": {
                        "status": ["31094501"]  # Open calls (corrected code)
                    }
                }
            ],
            "should": [
                {
                    "match": {
                        "title": {
                            "query": query,
                            "boost": 2.0
                        }
                    }
                },
                {
                    "match": {
                        "description": {
                            "query": query,
                            "boost": 1.0
                        }
                    }
                },
                {
                    "match": {
                        "keywords": {
                            "query": query,
                            "boost": 1.5
                        }
                    }
                }
            ]
        }
    }
    
    print(f"🔍 Testing query: '{query}'")
    print(f"📊 Query structure: {json.dumps(simple_query, indent=2)}")
    
    # Execute the search
    search_api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
    params = {
        "apiKey": "SEDIA",
        "pageSize": "50",
        "pageNumber": "1",
        "text": "***"
    }
    
    # Prepare multipart form data
    files = {
        "query": ("blob", json.dumps(simple_query), "application/json"),
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
                for i, result in enumerate(results[:5], 1):
                    title = result.get('content', '') or result.get('summary', 'No title')
                    metadata = result.get('metadata', {})
                    identifier = metadata.get('identifier', 'N/A')
                    status = metadata.get('status', 'Unknown')
                    
                    print(f"{i}. {title[:100]}...")
                    print(f"   ID: {identifier}, Status: {status}")
            else:
                print(f"❌ No results found despite facet API showing 2 results")
                print(f"📊 Full response: {json.dumps(data, indent=2)}")
                
        else:
            print(f"❌ Search API returned status {response.status_code}")
            print(f"📊 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Search execution failed: {e}")

def test_exact_facet_query():
    """Test the exact query structure from the facet API call."""
    print(f"\n🧪 Testing Exact Facet Query Structure")
    print("=" * 60)
    
    # This is the exact query from the facet API call that showed 2 results
    facet_query = {
        "bool": {
            "must": [
                {
                    "bool": {
                        "must": [
                            {"terms": {"type": ["1", "2", "8"]}},
                            {"terms": {"status": ["31094502"]}}  # Note: This uses 31094502 (old code)
                        ]
                    }
                },
                {
                    "bool": {
                        "should": [
                            {"phrase": {"query": "clean energy", "field": "identifier", "phraseSlop": 0, "boost": 1100}},
                            {"phrase": {"query": "clean energy", "field": "keywords", "phraseSlop": 0, "boost": 1000}},
                            {"phrase": {"query": "clean energy", "field": "tags", "phraseSlop": 0, "boost": 950}},
                            {"phrase": {"query": "clean energy", "field": "typesOfAction", "phraseSlop": 1, "boost": 900}},
                            {"phrase": {"query": "clean energy", "field": "title", "phraseSlop": 1, "boost": 200}},
                            {"phrase": {"query": "clean energy", "field": "callTitle", "phraseSlop": 1, "boost": 150}},
                            {"phrase": {"query": "clean energy", "field": "projectAcronym", "phraseSlop": 1, "boost": 140}},
                            {"phrase": {"query": "clean energy", "field": "projectName", "phraseSlop": 1, "boost": 130}},
                            {"phrase": {"query": "clean energy", "field": "description", "phraseSlop": 2, "boost": 100}},
                            {"phrase": {"query": "clean energy", "field": "furtherInformation", "phraseSlop": 1, "boost": 90}},
                            {"phrase": {"query": "clean energy", "field": "missionDescription", "phraseSlop": 1, "boost": 80}},
                            {"phrase": {"query": "clean energy", "field": "missionDetails", "phraseSlop": 1, "boost": 75}},
                            {"phrase": {"query": "clean energy", "field": "destinationDescription", "phraseSlop": 1, "boost": 70}},
                            {"phrase": {"query": "clean energy", "field": "destinationDetails", "phraseSlop": 1, "boost": 65}},
                            {"phrase": {"query": "clean energy", "field": "duration", "phraseSlop": 1, "boost": 60}}
                        ]
                    }
                }
            ]
        }
    }
    
    print(f"🔍 Testing exact facet query structure")
    print(f"📊 Status code used: 31094502 (old code)")
    
    # Execute the search
    search_api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
    params = {
        "apiKey": "SEDIA",
        "pageSize": "50",
        "pageNumber": "1",
        "text": "***"
    }
    
    # Prepare multipart form data
    files = {
        "query": ("blob", json.dumps(facet_query), "application/json"),
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
                print(f"\n📋 Results found with old status code:")
                for i, result in enumerate(results, 1):
                    title = result.get('content', '') or result.get('summary', 'No title')
                    metadata = result.get('metadata', {})
                    identifier = metadata.get('identifier', 'N/A')
                    status = metadata.get('status', 'Unknown')
                    
                    print(f"{i}. {title[:100]}...")
                    print(f"   ID: {identifier}, Status: {status}")
            else:
                print(f"❌ No results found even with old status code")
                
        else:
            print(f"❌ Search API returned status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Search execution failed: {e}")

def test_with_corrected_status():
    """Test with the corrected status code."""
    print(f"\n🧪 Testing with Corrected Status Code")
    print("=" * 60)
    
    # Same query structure but with corrected status code
    corrected_query = {
        "bool": {
            "must": [
                {
                    "bool": {
                        "must": [
                            {"terms": {"type": ["1", "2", "8"]}},
                            {"terms": {"status": ["31094501"]}}  # Corrected: 31094501 for open
                        ]
                    }
                },
                {
                    "bool": {
                        "should": [
                            {"match": {"title": {"query": "clean energy", "boost": 2.0}}},
                            {"match": {"description": {"query": "clean energy", "boost": 1.0}}},
                            {"match": {"keywords": {"query": "clean energy", "boost": 1.5}}}
                        ]
                    }
                }
            ]
        }
    }
    
    print(f"🔍 Testing with corrected status code: 31094501")
    
    # Execute the search
    search_api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
    params = {
        "apiKey": "SEDIA",
        "pageSize": "50",
        "pageNumber": "1",
        "text": "***"
    }
    
    # Prepare multipart form data
    files = {
        "query": ("blob", json.dumps(corrected_query), "application/json"),
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
                print(f"\n📋 Results found with corrected status code:")
                for i, result in enumerate(results, 1):
                    title = result.get('content', '') or result.get('summary', 'No title')
                    metadata = result.get('metadata', {})
                    identifier = metadata.get('identifier', 'N/A')
                    status = metadata.get('status', 'Unknown')
                    
                    print(f"{i}. {title[:100]}...")
                    print(f"   ID: {identifier}, Status: {status}")
            else:
                print(f"❌ No results found with corrected status code")
                print(f"📊 This suggests the issue is not just the status code")
                
        else:
            print(f"❌ Search API returned status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Search execution failed: {e}")

def main():
    """Run all tests."""
    print("🚀 Analyzing Search API Issue")
    print("=" * 60)
    print("Problem: System returns no results despite facet API showing 2 results")
    print("Goal: Identify why search queries are not returning expected results")
    print()
    
    # Test 1: Simple search query
    test_simple_search()
    
    # Test 2: Exact facet query structure
    test_exact_facet_query()
    
    # Test 3: With corrected status code
    test_with_corrected_status()
    
    print(f"\n📋 Analysis Summary:")
    print(f"• The facet API shows 2 results for 'clean energy' with status 31094502")
    print(f"• Our search queries should return these 2 results")
    print(f"• If no results are returned, the issue may be:")
    print(f"  1. Query structure is too restrictive")
    print(f"  2. Status code filtering is incorrect")
    print(f"  3. Field matching is too strict")
    print(f"  4. API behavior has changed")

if __name__ == "__main__":
    main()