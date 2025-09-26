#!/usr/bin/env python3
"""
Simple test runner to validate the conversation AI system.
This script will test the system and provide clear feedback.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_test_script(script_name: str, description: str) -> bool:
    """Run a test script and return success status."""
    
    print(f"\n🧪 {description}")
    print("=" * 50)
    
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print(f"❌ Test script not found: {script_name}")
        return False
    
    try:
        # Run the test script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Display output
        if result.stdout:
            print(result.stdout)
        
        if result.stderr and result.returncode != 0:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully!")
            return True
        else:
            print(f"❌ {description} failed with return code: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False

def main():
    """Main test runner."""
    
    print("🚀 Research Manager AI Test Suite")
    print("Testing the improved conversation AI system...")
    
    # Test sequence
    tests = [
        ("simple_conversation_test.py", "Basic Conversation System Test"),
        ("final_test_improved_system.py", "Comprehensive Research Manager Test")
    ]
    
    results = []
    
    for script, description in tests:
        success = run_test_script(script, description)
        results.append((description, success))
        
        if not success:
            print(f"\n⚠️ {description} failed - check output above for details")
    
    # Summary
    print(f"\n" + "=" * 60)
    print("📊 TEST SUITE SUMMARY")
    print("=" * 60)
    
    successful_tests = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {description}")
    
    print(f"\nOverall: {successful_tests}/{total_tests} tests passed")
    
    if successful_tests == total_tests:
        print("🎉 All tests passed! System is ready for use.")
    elif successful_tests > 0:
        print("⚠️ Some tests passed - system has partial functionality.")
    else:
        print("❌ All tests failed - system needs debugging.")
    
    # Next steps
    print(f"\n💡 Next Steps:")
    if successful_tests == total_tests:
        print("  • System is ready for research manager queries")
        print("  • Consider deploying to production environment") 
        print("  • Monitor performance and gather user feedback")
    else:
        print("  • Review test output above for specific issues")
        print("  • Check environment setup (.env file, API keys)")
        print("  • Ensure all dependencies are installed")
        print("  • Consider running individual tests for debugging")

if __name__ == "__main__":
    main()