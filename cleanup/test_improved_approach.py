#!/usr/bin/env python3
"""
Test the improved approach: database search + enhanced fallback when needed.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_improved_approach():
    """Test the improved approach with database search + enhanced fallback."""
    
    print("🔧 Testing Improved Approach: Database Search + Enhanced Fallback")
    print("=" * 70)
    
    try:
        from app.services.conversation.conversation_manager import ConversationManager
        
        # Initialize conversation manager
        manager = ConversationManager()
        print("✅ ConversationManager initialized")
        
        # Test the exact query that was failing
        test_query = "How much funding is available in Horizon Europe and how is it structured?"
        
        print(f"\n🎯 Testing query: '{test_query}'")
        print("\nExpected behavior:")
        print("1. Intent: conversational")
        print("2. Tools: search_local_database (for context)")
        print("3. If database search fails/poor results: Enhanced fallback response")
        print("4. Result: Comprehensive Horizon Europe information")
        
        print(f"\n" + "="*60)
        print("🧪 RUNNING FULL PIPELINE TEST...")
        print("="*60)
        
        # Test the full pipeline
        result = await manager.process_message(
            conversation_id=1001,  # Unique test conversation
            user_message=test_query,
            user_id=1,
            streaming=False
        )
        
        print(f"\n📊 RESULTS ANALYSIS:")
        print("-" * 40)
        
        if isinstance(result, dict) and 'response' in result:
            response = result['response']
            
            print(f"✅ Response generated: {len(response)} characters")
            
            # Analyze response quality
            quality_checks = {
                "Contains 'Horizon Europe'": 'horizon europe' in response.lower(),
                "Contains budget info (95.5 billion)": '95.5 billion' in response.lower() or '95.5' in response,
                "Contains pillar information": 'pillar' in response.lower(),
                "Contains structure info": any(term in response.lower() for term in ['excellent science', 'global challenges', 'innovative europe']),
                "Professional length (>500 chars)": len(response) > 500,
                "Not a 'couldn't find' response": "couldn't find" not in response.lower(),
                "Contains specific budget figures": any(term in response for term in ['€', 'billion', 'million']),
                "Actionable/helpful": any(term in response.lower() for term in ['would you like', 'specific information', 'application', 'call'])
            }
            
            passed_checks = sum(1 for passed in quality_checks.values() if passed)
            total_checks = len(quality_checks)
            
            print(f"\n📋 Quality Assessment: {passed_checks}/{total_checks}")
            for check, passed in quality_checks.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check}")
            
            # Show system metadata
            print(f"\n📊 System Metadata:")
            print(f"  Tools executed: {result.get('tools_executed', 'Unknown')}")
            print(f"  Processing time: {result.get('processing_time', 0):.2f}s")
            print(f"  Confidence: {result.get('confidence', 0)}")
            print(f"  Grounded: {result.get('grounded', False)}")
            print(f"  Chunks retrieved: {result.get('chunks_retrieved', 0)}")
            
            # Show response preview and structure analysis
            print(f"\n📝 Response Structure Analysis:")
            lines = response.split('\n')
            print(f"  Total lines: {len(lines)}")
            print(f"  Headers/sections: {sum(1 for line in lines if '**' in line)}")
            print(f"  Bullet points: {sum(1 for line in lines if line.strip().startswith('•'))}")
            
            print(f"\n📄 Response Preview (first 500 chars):")
            print("-" * 50)
            print(response[:500] + "..." if len(response) > 500 else response)
            print("-" * 50)
            
            # Overall assessment
            quality_score = passed_checks / total_checks
            
            if quality_score >= 0.8:
                print(f"\n🎉 EXCELLENT! System is working perfectly!")
                print(f"   Quality score: {quality_score:.1%}")
                print("   The improved approach (database search + enhanced fallback) is successful!")
            elif quality_score >= 0.6:
                print(f"\n✅ GOOD! System is working well with minor room for improvement")
                print(f"   Quality score: {quality_score:.1%}")
            elif quality_score >= 0.4:
                print(f"\n⚠️ FAIR: System is working but needs improvement")
                print(f"   Quality score: {quality_score:.1%}")
            else:
                print(f"\n❌ POOR: System still has significant issues")
                print(f"   Quality score: {quality_score:.1%}")
                
            return quality_score >= 0.6
            
        else:
            print(f"❌ Invalid response format: {type(result)}")
            if isinstance(result, dict):
                print(f"Response keys: {list(result.keys())}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing system: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_formatter_directly():
    """Test the enhanced formatter directly."""
    
    print(f"\n🎨 Testing Enhanced Response Formatter")
    print("=" * 50)
    
    try:
        from app.services.response.unified_formatter import UnifiedResponseFormatter
        
        formatter = UnifiedResponseFormatter()
        
        # Test the enhanced research response method
        test_query = "How much funding is available in Horizon Europe and how is it structured?"
        
        enhanced_response = formatter._get_enhanced_research_response(test_query)
        
        print(f"Enhanced response length: {len(enhanced_response)} characters")
        print(f"Contains key terms: {all(term in enhanced_response.lower() for term in ['horizon europe', '95.5 billion', 'pillar'])}")
        
        print(f"\n📄 Enhanced Response Preview:")
        print("-" * 40)
        print(enhanced_response[:400] + "..." if len(enhanced_response) > 400 else enhanced_response)
        print("-" * 40)
        
        return len(enhanced_response) > 500 and 'horizon europe' in enhanced_response.lower()
        
    except Exception as e:
        print(f"❌ Error testing formatter: {e}")
        return False

async def main():
    """Main test function."""
    
    print("🚀 IMPROVED APPROACH VALIDATION")
    print("=" * 60)
    print("Testing: Database Search + Enhanced Fallback when needed")
    
    # Test 1: Enhanced formatter
    formatter_works = await test_formatter_directly()
    
    # Test 2: Full system
    system_works = await test_improved_approach()
    
    # Final assessment
    print(f"\n" + "=" * 60)
    print("🎯 FINAL VALIDATION RESULTS")
    print("=" * 60)
    
    if formatter_works and system_works:
        print("✅ VALIDATION: SUCCESS!")
        print("\n🎉 The improved approach is working correctly!")
        print("\nWhat this means:")
        print("• Database search provides context when available")
        print("• Enhanced fallback provides comprehensive answers when search fails")
        print("• Best of both worlds: contextual + comprehensive")
        
        print("\n📝 Next Steps:")
        print("1. Restart your Docker containers")
        print("2. Test your original query")
        print("3. You should get comprehensive Horizon Europe information")
        
    elif formatter_works:
        print("⚠️ VALIDATION: PARTIAL SUCCESS")
        print("Enhanced formatter works, but full system has issues")
        
    else:
        print("❌ VALIDATION: NEEDS MORE WORK")
        print("Both formatter and system need debugging")
    
    return formatter_works and system_works

if __name__ == "__main__":
    asyncio.run(main())