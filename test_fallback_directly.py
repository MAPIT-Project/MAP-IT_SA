#!/usr/bin/env python3
"""
Test the enhanced fallback response directly.
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_enhanced_fallback():
    """Test the enhanced fallback response method directly."""
    
    print("🧪 Testing Enhanced Fallback Response")
    print("=" * 50)
    
    try:
        from app.services.conversation.conversation_manager import ConversationManager
        
        # Initialize conversation manager
        manager = ConversationManager()
        print("✅ ConversationManager initialized")
        
        # Test the enhanced fallback directly
        test_query = "How much funding is available in Horizon Europe and how is it structured?"
        
        print(f"\nTesting query: '{test_query}'")
        
        # Call the enhanced fallback method directly
        response = manager._get_enhanced_fallback_response(test_query, {"intent_type": "conversational"})
        
        print(f"\n📄 Enhanced Fallback Response:")
        print("-" * 30)
        print(response)
        print("-" * 30)
        print(f"\nResponse length: {len(response)} characters")
        
        # Check if it contains expected information
        expected_terms = ["95.5 billion", "horizon europe", "pillar", "budget"]
        found_terms = [term for term in expected_terms if term.lower() in response.lower()]
        
        print(f"\n✅ Expected terms found: {found_terms}")
        print(f"📊 Quality check: {len(found_terms)}/{len(expected_terms)} expected terms present")
        
        if len(found_terms) >= 3:
            print("🎉 Enhanced fallback is working correctly!")
        else:
            print("⚠️ Enhanced fallback may need adjustment")
            
        return response
        
    except Exception as e:
        print(f"❌ Error testing enhanced fallback: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_enhanced_fallback()