#!/usr/bin/env python3
"""
Test to verify the formatter fix for conversation context issues.
"""

from app.services.response.unified_formatter import UnifiedResponseFormatter

def test_formatter_fix():
    """Test the formatter fix for conversation context issues."""
    print("🧪 Testing Formatter Fix for Conversation Context")
    print("=" * 60)
    
    formatter = UnifiedResponseFormatter()
    
    # Test case 1: Simple query
    print("\n📝 Test 1: Simple query 'renewable energy'")
    response1 = formatter._format_no_calls_found("renewable energy")
    print(f"✅ Response generated successfully")
    print(f"📊 Contains 'renewable energy': {'renewable energy' in response1}")
    print(f"📊 Contains 'clean energy': {'clean energy' in response1}")
    
    # Test case 2: Query with conversational phrases
    print("\n📝 Test 2: Conversational query")
    response2 = formatter._format_no_calls_found("what are some open calls for renewable energy")
    print(f"✅ Response generated successfully")
    print(f"📊 Contains 'renewable energy': {'renewable energy' in response2}")
    print(f"📊 Contains 'what are some': {'what are some' in response2}")
    
    # Test case 3: Combined query (the problematic case)
    print("\n📝 Test 3: Combined query 'clean energy OR renewable energy'")
    response3 = formatter._format_no_calls_found("clean energy OR renewable energy")
    print(f"✅ Response generated successfully")
    print(f"📊 Contains 'clean energy OR renewable energy': {'clean energy OR renewable energy' in response3}")
    print(f"📊 Contains 'renewable energy': {'renewable energy' in response3}")
    print(f"📊 Contains 'clean energy': {'clean energy' in response3}")
    
    # Test case 4: Follow-up query
    print("\n📝 Test 4: Follow-up query 'Can you also include closed calls?'")
    response4 = formatter._format_no_calls_found("Can you also include closed calls?")
    print(f"✅ Response generated successfully")
    print(f"📊 Contains 'closed calls': {'closed calls' in response4}")
    print(f"📊 Contains 'Can you also': {'Can you also' in response4}")
    
    # Check verification URLs
    print("\n🔗 Verification URL Analysis:")
    for i, (test_name, response) in enumerate([
        ("Simple query", response1),
        ("Conversational query", response2), 
        ("Combined query", response3),
        ("Follow-up query", response4)
    ], 1):
        # Extract verification URL
        url_start = response.find("https://ec.europa.eu")
        if url_start != -1:
            url_end = response.find(";sortQuery", url_start)
            if url_end != -1:
                url = response[url_start:url_end]
                print(f"{i}. {test_name}:")
                print(f"   URL: {url}")
                if "clean%20energy%20OR%20renewable%20energy" in url:
                    print("   ❌ PROBLEM: URL contains combined query")
                elif "renewable%20energy" in url:
                    print("   ✅ SUCCESS: URL uses correct query")
                elif "clean%20energy" in url:
                    print("   ⚠️  WARNING: URL uses previous query")
                else:
                    print("   ℹ️  URL uses different query")
    
    print(f"\n📋 Summary:")
    print(f"• The fix should prevent query combination in verification URLs")
    print(f"• Each response should use only the relevant search terms")
    print(f"• Follow-up queries should not inherit previous search terms")

def test_query_extraction():
    """Test the query extraction logic specifically."""
    print(f"\n🧪 Testing Query Extraction Logic")
    print("=" * 40)
    
    formatter = UnifiedResponseFormatter()
    
    test_cases = [
        "renewable energy",
        "what are some open calls for renewable energy", 
        "clean energy OR renewable energy",
        "Can you also include closed calls?",
        "open calls for clean energy",
        "calls about artificial intelligence"
    ]
    
    for query in test_cases:
        # Simulate the extraction logic
        search_terms = query.strip()
        
        # Handle OR queries
        if " OR " in search_terms.upper():
            parts = search_terms.upper().split(" OR ")
            if len(parts) > 1:
                search_terms = parts[-1].strip()
        
        # Clean conversational phrases
        clean_phrases = [
            "what are some open calls for", "what are some open calls about", 
            "open calls for", "open calls about", "calls for", "calls about",
            "can you also include closed calls", "include closed calls"
        ]
        
        for phrase in clean_phrases:
            if phrase in search_terms.lower():
                search_terms = search_terms.lower().replace(phrase, "").strip()
        
        # Remove question marks
        search_terms = search_terms.replace("?", "").strip()
        
        print(f"📝 '{query}' → '{search_terms}'")

if __name__ == "__main__":
    test_formatter_fix()
    test_query_extraction()