#!/usr/bin/env python3
"""
EU Funding & Tenders Portal API Test Script
============================================

This script tests the EU API to search for open calls related to clean energy.
Use this to debug and experiment with different API parameters and request formats.

Usage:
    python3 test_eu_api_calls.py

You can modify the search parameters, API endpoint, and processing logic
to test different approaches for finding current funding opportunities.
"""

import requests
import json
import time
import re
from datetime import datetime
from typing import List, Dict, Any

class EUAPITester:
    def __init__(self):
        self.api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
        self.api_key = "SEDIA"  # Public API key for open data
        
    def test_basic_search(self, search_term: str = "clean energy", max_results: int = 10):
        """
        Test basic search functionality with the EU API
        """
        print(f"🔍 Testing EU API search for: '{search_term}'")
        print(f"📡 API URL: {self.api_url}")
        print("-" * 60)
        
        # Basic search parameters
        search_params = {
            "apiKey": self.api_key,
            "index": "opportunities",  # Dataset for funding opportunities
            "pageSize": str(min(max_results, 50)),
            "pageNumber": "1",
            "text": search_term,
            "language": "en",
        }
        
        print("📋 Request Parameters:")
        for key, value in search_params.items():
            print(f"   {key}: {value}")
        print()
        
        try:
            start_time = time.time()
            
            # Make the API request
            print("🚀 Making API request...")
            response = requests.post(
                self.api_url,
                data=search_params,
                timeout=15
            )
            
            elapsed_time = time.time() - start_time
            print(f"⏱️  Response time: {elapsed_time:.2f} seconds")
            print(f"📊 HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.analyze_response(data, search_term)
                return data
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"💥 Request failed: {e}")
            return None
    
    def analyze_response(self, data: Dict[str, Any], search_term: str):
        """
        Analyze and display the API response structure and results
        """
        print("\n" + "="*60)
        print("📊 RESPONSE ANALYSIS")
        print("="*60)
        
        # Basic response info
        total_results = data.get('totalResults', 0)
        page_size = data.get('pageSize', 0)
        page_number = data.get('pageNumber', 0)
        response_time = data.get('responseTime', 0)
        
        print(f"🔢 Total Results: {total_results}")
        print(f"📄 Page Size: {page_size}")
        print(f"📖 Page Number: {page_number}")
        print(f"⚡ API Response Time: {response_time}ms")
        
        results = data.get('results', [])
        print(f"📋 Results in this page: {len(results)}")
        
        if not results:
            print("\n❌ No results found!")
            return
        
        print("\n" + "-"*40)
        print("🔍 ANALYZING INDIVIDUAL RESULTS")
        print("-"*40)
        
        # Analyze each result
        current_calls = 0
        closed_calls = 0
        unknown_status_calls = 0
        
        for i, result in enumerate(results[:5], 1):  # Analyze first 5 results
            print(f"\n📌 Result #{i}:")
            
            # Extract basic info
            title = result.get('title')
            reference = result.get('reference', 'N/A')
            url = result.get('url', 'N/A')
            summary = result.get('summary', 'No summary')
            
            print(f"   Title: {title}")
            print(f"   Reference: {reference}")
            print(f"   Summary: {summary[:100]}...")
            
            # Extract metadata
            metadata = result.get('metadata', {})
            
            # Status analysis
            status_raw = metadata.get('status', [None])[0] if isinstance(metadata.get('status'), list) else None
            status_readable = self.decode_status(status_raw)
            
            # Programme period
            programme_period = metadata.get('programmePeriod', ['Unknown'])[0] if isinstance(metadata.get('programmePeriod'), list) else 'Unknown'
            
            # Deadline
            deadline_raw = metadata.get('deadlineDate', [None])[0] if isinstance(metadata.get('deadlineDate'), list) else None
            deadline_readable = self.format_deadline(deadline_raw)
            
            # Identifier
            identifier = metadata.get('identifier', [None])[0] if isinstance(metadata.get('identifier'), list) else None
            
            print(f"   📋 Identifier: {identifier}")
            print(f"   📊 Status: {status_readable} (raw: {status_raw})")
            print(f"   📅 Programme Period: {programme_period}")
            print(f"   ⏰ Deadline: {deadline_readable}")
            print(f"   🔗 URL: {url}")
            
            # Count status types
            if status_readable == 'Open':
                current_calls += 1
            elif status_readable == 'Closed':
                closed_calls += 1
            else:
                unknown_status_calls += 1
        
        # Summary statistics
        print("\n" + "="*40)
        print("📈 SUMMARY STATISTICS")
        print("="*40)
        print(f"✅ Open calls found: {current_calls}")
        print(f"❌ Closed calls found: {closed_calls}")
        print(f"❓ Unknown status calls: {unknown_status_calls}")
        
        if current_calls == 0:
            print("\n⚠️  WARNING: No open calls found in the results!")
            print("💡 This suggests the API may be returning historical data only.")
            print("🔍 Try different search terms or check the official EU portal directly.")
    
    def decode_status(self, status_code: str) -> str:
        """
        Decode status codes to readable format
        """
        if not status_code:
            return "Unknown"
        
        status_mapping = {
            '31094502': 'Open',
            '31094503': 'Closed', 
            '31094501': 'Forthcoming',
        }
        
        return status_mapping.get(str(status_code), f"Unknown ({status_code})")
    
    def format_deadline(self, deadline_raw: str) -> str:
        """
        Format deadline for display
        """
        if not deadline_raw:
            return "Not specified"
        
        try:
            # Try to parse and format the date
            if 'T' in deadline_raw:
                deadline_date = datetime.strptime(deadline_raw.split('T')[0], '%Y-%m-%d')
                formatted = deadline_date.strftime('%B %d, %Y')
                
                # Check if it's in the future
                days_diff = (deadline_date - datetime.now()).days
                if days_diff > 0:
                    return f"{formatted} ({days_diff} days from now)"
                else:
                    return f"{formatted} ({abs(days_diff)} days ago - EXPIRED)"
            else:
                return deadline_raw
        except:
            return deadline_raw
    
    def save_response_to_file(self, data: Dict[str, Any], filename: str = None):
        """
        Save the API response to a JSON file for detailed analysis
        """
        if not filename:
            timestamp = int(time.time())
            filename = f"eu_api_response_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Response saved to: {filename}")
        except Exception as e:
            print(f"❌ Failed to save response: {e}")
    
    def test_different_search_terms(self):
        """
        Test various search terms related to energy and sustainability
        """
        search_terms = [
            "clean energy",
            "renewable energy",
            "energy efficiency", 
            "sustainable energy",
            "green energy",
            "energy storage",
            "solar energy",
            "wind energy",
            "energy transition"
        ]
        
        print("🧪 Testing different search terms...")
        print("="*60)
        
        results_summary = {}
        
        for term in search_terms:
            print(f"\n🔍 Testing: '{term}'")
            print("-" * 30)
            
            data = self.test_basic_search(term, max_results=5)
            if data:
                total_results = data.get('totalResults', 0)
                results_summary[term] = total_results
                print(f"📊 Total results for '{term}': {total_results}")
            else:
                results_summary[term] = 0
                print(f"❌ No results for '{term}'")
            
            time.sleep(1)  # Be nice to the API
        
        # Summary
        print("\n" + "="*60)
        print("📈 SEARCH TERMS COMPARISON")
        print("="*60)
        
        sorted_results = sorted(results_summary.items(), key=lambda x: x[1], reverse=True)
        for term, count in sorted_results:
            print(f"{term:20} : {count:,} results")
    
    def test_advanced_parameters(self):
        """
        Test different API parameters to understand what works
        """
        print("🔬 Testing advanced API parameters...")
        print("="*60)
        
        # Test different parameter combinations
        test_configs = [
            {
                "name": "Basic text search",
                "params": {
                    "apiKey": self.api_key,
                    "index": "opportunities",
                    "text": "energy",
                    "pageSize": "10"
                }
            },
            {
                "name": "With language filter",
                "params": {
                    "apiKey": self.api_key,
                    "index": "opportunities", 
                    "text": "energy",
                    "language": "en",
                    "pageSize": "10"
                }
            },
            {
                "name": "With status filter (open)",
                "params": {
                    "apiKey": self.api_key,
                    "index": "opportunities",
                    "text": "energy",
                    "status": "31094502",  # Open status
                    "pageSize": "10"
                }
            },
            {
                "name": "With programme period",
                "params": {
                    "apiKey": self.api_key,
                    "index": "opportunities",
                    "text": "energy",
                    "programmePeriod": "2021 - 2027",
                    "pageSize": "10"
                }
            }
        ]
        
        for config in test_configs:
            print(f"\n🧪 Testing: {config['name']}")
            print("-" * 40)
            
            try:
                response = requests.post(
                    self.api_url,
                    data=config['params'],
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    total_results = data.get('totalResults', 0)
                    print(f"✅ Success: {total_results} results")
                else:
                    print(f"❌ Failed: HTTP {response.status_code}")
                    print(f"   Response: {response.text[:200]}...")
                    
            except Exception as e:
                print(f"💥 Error: {e}")
            
            time.sleep(1)  # Rate limiting

    def test_advanced_json_query(self, max_results: int = 50):
        """
        Test advanced JSON query with boolean operators and specific filtering
        This approach uses file uploads to send JSON query structures
        """
        print("🧪 Testing advanced JSON query with boolean operators...")
        print(f"📡 API URL: {self.api_url}")
        print("-" * 60)
        
        # URL parameters
        params = {
            "apiKey": self.api_key,
            "text": "Horizon Europe",  # Query string
            "pageSize": str(min(max_results, 50)),
            "pageNumber": "1",
        }
        
        # Advanced JSON query with boolean operators
        query = {
            "bool": {
                "must": [
                    {"terms": {"type": ["1", "2"]}},  # Types for calls/topics
                    {"terms": {"status": ["31094502"]}},  # Status for open
                    {"term": {"programmePeriod": "2021 - 2027"}},
                    {"terms": {"frameworkProgramme": ["43108390"]}},  # Horizon Europe
                ]
            }
        }
        
        languages = ["en"]
        sort_params = {"field": "sortStatus", "order": "ASC"}
        
        print("📋 URL Parameters:")
        for key, value in params.items():
            print(f"   {key}: {value}")
        
        print("\n📋 JSON Query Structure:")
        print(json.dumps(query, indent=2))
        
        print(f"\n🌐 Languages: {languages}")
        print(f"📊 Sort: {sort_params}")
        print()
        
        try:
            start_time = time.time()
            
            # Make the API request with file uploads for JSON data
            print("🚀 Making advanced API request with JSON query...")
            response = requests.post(
                self.api_url,
                params=params,
                files={
                    "query": ("blob", json.dumps(query), "application/json"),
                    "languages": ("blob", json.dumps(languages), "application/json"),
                    "sort": ("blob", json.dumps(sort_params), "application/json"),
                },
                timeout=15
            )
            
            elapsed_time = time.time() - start_time
            print(f"⏱️  Response time: {elapsed_time:.2f} seconds")
            print(f"📊 HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.analyze_advanced_response(data)
                return data
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"💥 Request failed: {e}")
            return None
    
    def analyze_advanced_response(self, data: Dict[str, Any]):
        """
        Analyze the response from the advanced JSON query
        """
        print("\n" + "="*60)
        print("📊 ADVANCED QUERY RESPONSE ANALYSIS")
        print("="*60)
        
        # Basic response info
        total_results = data.get('totalResults', 0)
        page_size = data.get('pageSize', 0)
        page_number = data.get('pageNumber', 0)
        response_time = data.get('responseTime', 0)
        
        print(f"🔢 Total Results: {total_results}")
        print(f"📄 Page Size: {page_size}")
        print(f"📖 Page Number: {page_number}")
        print(f"⚡ API Response Time: {response_time}ms")
        
        results = data.get('results', [])
        print(f"📋 Results in this page: {len(results)}")
        
        if not results:
            print("\n❌ No results found with advanced query!")
            print("💡 This might indicate:")
            print("   • No current open calls matching the criteria")
            print("   • Incorrect query parameters")
            print("   • Need to adjust the boolean query structure")
            return
        
        print("\n" + "-"*40)
        print("🔍 ANALYZING ADVANCED QUERY RESULTS")
        print("-"*40)
        
        # Analyze each result
        open_calls = 0
        horizon_europe_calls = 0
        
        for i, result in enumerate(results[:10], 1):  # Analyze first 10 results
            print(f"\n📌 Result #{i}:")
            
            # Extract content information
            content = result.get('content', 'No content')
            url = result.get('url', 'N/A')
            
            print(f"   📋 Content/Title: {content}")
            print(f"   🔗 URL: {url}")
            
            # Extract metadata if available
            metadata = result.get('metadata', {})
            if metadata:
                # Status analysis
                status_raw = metadata.get('status', [None])[0] if isinstance(metadata.get('status'), list) else None
                status_readable = self.decode_status(status_raw)
                
                # Programme info
                programme_period = metadata.get('programmePeriod', ['Unknown'])[0] if isinstance(metadata.get('programmePeriod'), list) else 'Unknown'
                framework_programme = metadata.get('frameworkProgramme', ['Unknown'])[0] if isinstance(metadata.get('frameworkProgramme'), list) else 'Unknown'
                
                # Deadline
                deadline_raw = metadata.get('deadlineDate', [None])[0] if isinstance(metadata.get('deadlineDate'), list) else None
                deadline_readable = self.format_deadline(deadline_raw)
                
                print(f"   📊 Status: {status_readable} (raw: {status_raw})")
                print(f"   📅 Programme Period: {programme_period}")
                print(f"   🏛️  Framework Programme: {framework_programme}")
                print(f"   ⏰ Deadline: {deadline_readable}")
                
                # Count specific types
                if status_readable == 'Open':
                    open_calls += 1
                if 'horizon' in str(framework_programme).lower() or 'horizon' in content.lower():
                    horizon_europe_calls += 1
            else:
                print("   ⚠️  No metadata available")
        
        # Summary statistics for advanced query
        print("\n" + "="*40)
        print("📈 ADVANCED QUERY SUMMARY")
        print("="*40)
        print(f"✅ Open calls found: {open_calls}")
        print(f"🇪🇺 Horizon Europe related: {horizon_europe_calls}")
        print(f"📊 Total results analyzed: {min(len(results), 10)}")
        
        if open_calls > 0:
            print(f"\n🎉 SUCCESS: Found {open_calls} open calls with advanced filtering!")
            print("💡 The boolean query approach is working effectively.")
        else:
            print("\n⚠️  No open calls found with current filters.")
            print("💡 Consider adjusting the query parameters:")
            print("   • Try different status codes")
            print("   • Adjust the programme period")
            print("   • Modify the framework programme filter")


def main():
    """
    Main function to run the EU API tests
    """
    print("🚀 EU Funding & Tenders Portal API Tester")
    print("="*60)
    print("This script will test the EU API for clean energy funding calls.")
    print("You can modify the parameters and logic to experiment with different approaches.")
    print()
    
    tester = EUAPITester()
    
    # Run basic test
    print("1️⃣  Running basic search test...")
    data = tester.test_basic_search("clean energy", max_results=10)
    
    if data:
        # Save response for detailed analysis
        tester.save_response_to_file(data)
        print("✅ Basic test completed!")
    
    # Run advanced JSON query test
    print("\n" + "="*60)
    print("2️⃣  Running advanced JSON query test...")
    advanced_data = tester.test_advanced_json_query(max_results=20)
    
    if advanced_data:
        # Save advanced response
        timestamp = int(time.time())
        advanced_filename = f"eu_api_advanced_response_{timestamp}.json"
        tester.save_response_to_file(advanced_data, advanced_filename)
        print("✅ Advanced query test completed!")
    
    if data or advanced_data:
        print("\n" + "="*60)
        print("✅ API TESTING COMPLETED!")
        print("💡 You can now:")
        print("   • Examine the saved JSON files for detailed response structure")
        print("   • Compare basic vs advanced query results")
        print("   • Modify the JSON query structure for different filtering")
        print("   • Test different boolean operators and criteria")
        
        # Ask if user wants to run additional tests
        print("\n🤔 Would you like to run additional tests?")
        print("   Uncomment the lines below to test:")
        print("   • Different search terms")
        print("   • Advanced API parameters")
        
        # Uncomment these lines to run additional tests:
        # print("\n3️⃣  Testing different search terms...")
        # tester.test_different_search_terms()
        
        # print("\n4️⃣  Testing advanced parameters...")
        # tester.test_advanced_parameters()
    
    else:
        print("❌ All tests failed. Check your internet connection and API availability.")


if __name__ == "__main__":
    main() 