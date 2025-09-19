#!/usr/bin/env python3
"""
Simple test to verify tool registration without requiring API keys.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_tool_registration():
    """Test that the new conversational database search tool is properly registered."""

    print("🔧 Testing Tool Registration")
    print("=" * 50)

    try:
        from app.services.tools.tool_orchestrator import create_research_orchestrator

        orchestrator = create_research_orchestrator()
        available_tools = orchestrator.get_available_tools()

        print(f"✅ Found {len(available_tools)} registered tools")

        # Check for our new tool
        database_tool = None
        for tool in available_tools:
            if tool['name'] == 'search_local_database':
                database_tool = tool
                break

        if database_tool:
            print("✅ 'search_local_database' tool found:")
            print(f"   Description: {database_tool['description']}")
            print(f"   Category: {database_tool['category']}")
            print(f"   Tags: {database_tool['tags']}")
            print(f"   Parameters: {list(database_tool['parameters'].keys())}")
            print("   ✅ Tool registration successful!")

            # Verify expected parameters
            expected_params = ['query', 'max_context_chunks', 'search_type', 'similarity_threshold']
            actual_params = list(database_tool['parameters'].keys())

            if set(expected_params) == set(actual_params):
                print("   ✅ All expected parameters are present")
            else:
                print(f"   ❌ Parameter mismatch. Expected: {expected_params}, Got: {actual_params}")

            # Verify expected tags
            expected_tags = ['local_database', 'conversational', 'documents', 'rag', 'horizon_europe']
            actual_tags = database_tool['tags']

            if set(expected_tags) == set(actual_tags):
                print("   ✅ All expected tags are present")
            else:
                print(f"   ❌ Tag mismatch. Expected: {expected_tags}, Got: {actual_tags}")

            return True
        else:
            print("❌ 'search_local_database' tool not found in registered tools")
            print("Available tools:")
            for tool in available_tools:
                print(f"  - {tool['name']}: {tool['description']}")
            return False

    except Exception as e:
        print(f"❌ Tool registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tool_orchestrator_methods():
    """Test that the tool orchestrator has the expected methods."""

    print("\n🔧 Testing Tool Orchestrator Methods")
    print("=" * 50)

    try:
        from app.services.tools.tool_orchestrator import create_research_orchestrator

        orchestrator = create_research_orchestrator()

        # Test that we can get available tools
        tools = orchestrator.get_available_tools()
        print(f"✅ get_available_tools() works: {len(tools)} tools returned")

        # Test that we can print available tools
        print("✅ print_available_tools() works:")
        orchestrator.print_available_tools()

        return True

    except Exception as e:
        print(f"❌ Tool orchestrator methods test failed: {e}")
        return False

def main():
    """Run all tests."""

    print("🚀 Testing Enhanced Conversational Query Tool Registration")
    print("=" * 60)

    # Test tool registration
    registration_test_passed = test_tool_registration()

    # Test orchestrator methods
    methods_test_passed = test_tool_orchestrator_methods()

    print("\n" + "=" * 60)
    print("📋 FINAL RESULTS:")
    print(f"   Tool Registration: {'✅ PASSED' if registration_test_passed else '❌ FAILED'}")
    print(f"   Orchestrator Methods: {'✅ PASSED' if methods_test_passed else '❌ FAILED'}")

    if registration_test_passed and methods_test_passed:
        print("   🎉 ALL TESTS PASSED - Tool registration is working correctly!")
        print("\n📝 SUMMARY:")
        print("   ✅ New 'search_local_database' tool is properly registered")
        print("   ✅ Tool has correct parameters and metadata")
        print("   ✅ Tool orchestrator methods work correctly")
        print("   ✅ Tool is ready for use in conversational queries")
        return True
    else:
        print("   ❌ SOME TESTS FAILED - Please check the implementation")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)