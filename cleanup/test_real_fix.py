#!/usr/bin/env python3
"""
Test the REAL fix for the conversational query issue.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_real_fix():
    """Test the conversational query with the real fix applied."""
    
    print("🔧 Testing REAL Fix for Conversational Queries")
    print("=" * 60)
    
    try:
        from app.services.conversation.conversation_manager import ConversationManager
        
        # Initialize conversation manager
        manager = ConversationManager()
        print("✅ ConversationManager initialized")
        
        # Test the exact failing query
        test_query = "How much funding is available in Horizon Europe and how is it structured?"
        
        print(f"\n🎯 Testing problematic query:")
        print(f"'{test_query}'")
        print("\nExpected behavior:")
        print("- Intent: conversational")
        print("- Tools: NONE (should be overridden)")
        print("- Response: Enhanced fallback with detailed Horizon Europe info")
        
        print(f"\n" + "="*50)
        print("🧪 RUNNING TEST...")
        print("="*50)
        
        # Test the full pipeline
        result = await manager.process_message(
            conversation_id=999,  # Unique conversation ID for testing
            user_message=test_query,
            user_id=1,
            streaming=False
        )
        
        print(f"\n📊 RESULTS:")
        print("-" * 30)
        
        if isinstance(result, dict) and 'response' in result:
            response = result['response']
            
            print(f"✅ Response received: {len(response)} characters")
            
            # Check for key indicators
            checks = {
                "Contains 'Horizon Europe'": 'horizon europe' in response.lower(),
                "Contains '95.5 billion'": '95.5 billion' in response.lower(),
                "Contains 'pillar' or 'Pillar'": 'pillar' in response.lower(),
                "Contains budget info": any(term in response.lower() for term in ['budget', 'billion', '€']),
                "Long enough (>300 chars)": len(response) > 300,
                "Not a 'couldn't find' response": "couldn't find" not in response.lower(),
                "Professional quality": len(response) > 500
            }
            
            passed_checks = sum(1 for passed in checks.values() if passed)
            total_checks = len(checks)
            
            print(f"\n📋 Quality Checks: {passed_checks}/{total_checks}")
            for check, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check}")
            
            # Show metadata
            metadata = result.get('metadata', {})
            print(f"\n📊 Metadata:")
            print(f"  Tools executed: {result.get('tools_executed', 'Unknown')}")
            print(f"  Confidence: {result.get('confidence', 'Unknown')}")
            print(f"  Processing time: {result.get('processing_time', 'Unknown'):.2f}s")
            
            # Show response preview
            print(f"\n📝 Response Preview:")
            print("-" * 40)
            print(response[:400] + "..." if len(response) > 400 else response)
            print("-" * 40)
            
            # Overall assessment
            if passed_checks >= 6:
                print(f"\n🎉 SUCCESS! The fix is working correctly!")
                print(f"   The system is now providing proper conversational responses.")
            elif passed_checks >= 4:
                print(f"\n⚠️ PARTIAL SUCCESS. The fix is mostly working but could be improved.")
            else:
                print(f"\n❌ FAILED. The fix is not working properly.")
                
            return passed_checks >= 4
            
        else:
            print(f"❌ Invalid response format: {type(result)}")
            if isinstance(result, dict):
                print(f"Keys: {list(result.keys())}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing fix: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    
    print("🚨 Testing Real Fix for Conversational Query Issues")
    
    success = asyncio.run(test_real_fix())
    
    print(f"\n" + "="*60)
    
    if success:
        print("🎯 FIX VALIDATION: SUCCESS!")
        print("\nThe system should now work correctly with your query:")
        print("'How much funding is available in Horizon Europe and how is it structured?'")
        print("\nTry restarting your FastAPI server and testing again.")
    else:
        print("❌ FIX VALIDATION: FAILED!")
        print("\nThe system still has issues. Additional debugging may be needed.")
    
    print("\n💡 Next Steps:")
    print("1. If successful: Restart your FastAPI server to pick up changes")
    print("2. If failed: There may be deeper issues that need investigation")

if __name__ == "__main__":
    main()