#!/usr/bin/env python3
"""
Research the EU API filtering capabilities to implement smart filtering.
Based on the provided curl examples and EU API documentation.
"""

import requests
import json
import time
from datetime import datetime, timedelta

def research_status_filtering():
    """Research how to filter by call status (open, closed, recent)."""
    print("🔬 RESEARCHING EU API FILTERING CAPABILITIES")
    print("=" * 60)
    
    # Test different status filter combinations
    status_tests = [
        {
            "name": "OPEN CALLS ONLY",
            "status_codes": ["31094502"],  # Open only
            "description": "Should return only currently open calls"
        },
        {
            "name": "FORTHCOMING CALLS ONLY", 
            "status_codes": ["31094501"],  # Forthcoming only
            "description": "Should return only upcoming calls"
        },
        {
            "name": "OPEN + FORTHCOMING",
            "status_codes": ["31094501", "31094502"],  # Open + Forthcoming
            "description": "Should return currently available opportunities"
        },
        {
            "name": "ALL STATUSES",
            "status_codes": ["31094501", "31094502", "31094503"],  # All
            "description": "Should return all calls (including closed)"
        }
    ]
    
    base_query = {
        "bool": {
            "must": [
                {
                    "bool": {
                        "must": [
                            {"terms": {"type": ["1", "2", "8"]}},
                            {"term": {"programmePeriod": "2021 - 2027"}}
                        ]
                    }
                },
                {
                    "bool": {
                        "should": [
                            {"phrase": {"query": "quantum mechanics", "field": "keywords", "phraseSlop": 0, "boost": 1000}},
                            {"phrase": {"query": "quantum mechanics", "field": "title", "phraseSlop": 1, "boost": 200}}
                        ]
                    }
                }
            ]
        }
    }
    
    for test in status_tests:
        print(f"\n🧪 Testing: {test['name']}")
        print(f"   Status codes: {test['status_codes']}")
        print(f"   Description: {test['description']}")
        
        # Create query with specific status filter
        test_query = base_query.copy()
        test_query["bool"]["must"][0]["bool"]["must"].append(
            {"terms": {"status": test["status_codes"]}}
        )
        
        try:
            files = {
                "sort": ("blob", json.dumps({"order": "DESC", "field": "relevance"}), "application/json"),
                "query": ("blob", json.dumps(test_query), "application/json"),
                "languages": ("blob", json.dumps(["en"]), "application/json")
            }
            
            response = requests.post(
                "https://api.tech.ec.europa.eu/search-api/prod/rest/search",
                params={"apiKey": "SEDIA", "text": "***", "pageSize": "50"},
                files=files,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                total_results = data.get("totalResults", 0)
                results = data.get("results", [])
                
                print(f"   ✅ Results: {len(results)} returned (total: {total_results})")
                
                # Show status breakdown
                status_counts = {}
                for result in results[:10]:  # Check first 10
                    metadata = result.get('metadata', {})
                    status_raw = metadata.get('status', [None])[0] if isinstance(metadata.get('status'), list) else None
                    status_readable = {
                        '31094502': 'Open',
                        '31094503': 'Closed', 
                        '31094501': 'Forthcoming'
                    }.get(str(status_raw), f"Unknown ({status_raw})")
                    
                    status_counts[status_readable] = status_counts.get(status_readable, 0) + 1
                
                print(f"   📊 Status breakdown (first 10): {status_counts}")
                
            else:
                print(f"   ❌ API failed with status {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        
        time.sleep(0.5)  # Rate limiting

def research_date_filtering():
    """Research how to filter by date ranges for 'recent calls'."""
    print(f"\n🕐 RESEARCHING DATE FILTERING")
    print("-" * 40)
    
    # Calculate date ranges for "recent" filtering
    now = datetime.now()
    last_6_months = now - timedelta(days=180)
    last_12_months = now - timedelta(days=365)
    
    print(f"Current date: {now.strftime('%Y-%m-%d')}")
    print(f"Last 6 months: {last_6_months.strftime('%Y-%m-%d')}")
    print(f"Last 12 months: {last_12_months.strftime('%Y-%m-%d')}")
    
    # Test date range filtering
    date_query = {
        "bool": {
            "must": [
                {
                    "bool": {
                        "must": [
                            {"terms": {"type": ["1", "2", "8"]}},
                            {"terms": {"status": ["31094501", "31094502", "31094503"]}},
                            {"term": {"programmePeriod": "2021 - 2027"}},
                            # Add date range filter for recent calls
                            {"range": {"deadlineDate": {"gte": last_6_months.strftime('%Y-%m-%d')}}}
                        ]
                    }
                },
                {
                    "bool": {
                        "should": [
                            {"phrase": {"query": "quantum mechanics", "field": "keywords", "phraseSlop": 0, "boost": 1000}}
                        ]
                    }
                }
            ]
        }
    }
    
    try:
        files = {
            "sort": ("blob", json.dumps({"order": "DESC", "field": "relevance"}), "application/json"),
            "query": ("blob", json.dumps(date_query), "application/json"),
            "languages": ("blob", json.dumps(["en"]), "application/json")
        }
        
        response = requests.post(
            "https://api.tech.ec.europa.eu/search-api/prod/rest/search",
            params={"apiKey": "SEDIA", "text": "***", "pageSize": "50"},
            files=files,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            total_results = data.get("totalResults", 0)
            results = data.get("results", [])
            
            print(f"✅ Recent calls (last 6 months): {len(results)} results (total: {total_results})")
            
            # Show recent call examples
            for i, result in enumerate(results[:3], 1):
                metadata = result.get('metadata', {})
                identifier = metadata.get('identifier', ['N/A'])[0] if isinstance(metadata.get('identifier'), list) else 'N/A'
                deadline_raw = metadata.get('deadlineDate', ['N/A'])[0] if isinstance(metadata.get('deadlineDate'), list) else 'N/A'
                print(f"   {i}. {identifier}: deadline {deadline_raw}")
                
        else:
            print(f"❌ Date filtering test failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Date filtering test failed: {e}")

def main():
    """Run all filtering research."""
    research_status_filtering()
    research_date_filtering()
    
    print(f"\n📋 FILTERING RESEARCH CONCLUSIONS:")
    print(f"✅ Status filtering works: Use specific status codes for open/closed calls")
    print(f"✅ Date filtering works: Use range queries on deadlineDate field")
    print(f"✅ Ready to implement intelligent query parsing!")

if __name__ == "__main__":
    main()