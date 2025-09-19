#!/usr/bin/env python3
"""
Test the CORDIS tool import and basic functionality.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_cordis_tool_import():
    """Test that the CORDIS tool can be imported and initialized."""

    print("🧪 Testing CORDIS Tool Import and Basic Functionality")
    print("=" * 60)

    try:
        # Test import
        print("📦 Testing import...")
        from app.services.tools.tool_orchestrator import create_research_orchestrator, ResearchTools
        print("✅ Tool orchestrator imported successfully")

        # Test CORDIS RAG import
        print("📦 Testing CORDIS RAG import...")
        from app.services.rag_service import CordisRAG
        print("✅ CORDIS RAG imported successfully")

        # Test tool creation
        print("🔧 Testing tool creation...")
        orchestrator = create_research_orchestrator()
        print("✅ Tool orchestrator created successfully")

        # Test available tools
        tools = orchestrator.get_available_tools()
        print(f"✅ Available tools: {len(tools)}")
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description'][:50]}...")

        # Check if CORDIS tool is registered
        cordis_tool = next((t for t in tools if t['name'] == 'search_cordis_projects'), None)
        if cordis_tool:
            print("✅ CORDIS search tool is registered")
        else:
            print("❌ CORDIS search tool is NOT registered")
            return False

        # Test tool parameters
        print("🔧 Testing tool parameters...")
        params = cordis_tool['parameters']
        print(f"   Query parameter: {params['query']}")
        print(f"   Max results parameter: {params['max_results']}")

        print("\n🎉 ALL IMPORT TESTS PASSED!")
        print("The CORDIS tool is properly configured and ready to use.")
        return True

    except ImportError as e:
        print(f"❌ IMPORT ERROR: {e}")
        print("This indicates a missing dependency or incorrect import path.")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_cordis_tool_execution():
    """Test actual execution of the CORDIS tool."""

    print("\n🔧 Testing CORDIS Tool Execution")
    print("=" * 60)

    try:
        from app.services.tools.tool_orchestrator import create_research_orchestrator

        # Create orchestrator
        orchestrator = create_research_orchestrator()

        # Test parameters
        test_params = {
            'query': 'clean energy',
            'max_results': 3,
            'include_summary': True
        }

        print(f"📝 Testing with parameters: {test_params}")

        # Execute tool directly
        from app.services.tools.tool_orchestrator import ResearchTools
        result = await ResearchTools.search_cordis_projects(test_params, {})

        print("📊 EXECUTION RESULT:")
        print(f"   Success: {result.get('success', False)}")
        print(f"   Projects found: {result.get('results', {}).get('projects_found', 0)}")
        print(f"   Data source: {result.get('results', {}).get('data_source', 'unknown')}")

        if result.get('success'):
            print("✅ CORDIS tool executed successfully!")
            return True
        else:
            print("❌ CORDIS tool execution failed")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ EXECUTION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    async def main():
        print("🚀 STARTING CORDIS TOOL TESTS")
        print("=" * 80)

        # Test import and setup
        import_success = await test_cordis_tool_import()

        if import_success:
            # Test actual execution
            execution_success = await test_cordis_tool_execution()

            if execution_success:
                print("\n🎉 ALL TESTS PASSED!")
                print("The CORDIS tool is working correctly and should return results for project searches.")
            else:
                print("\n⚠️  IMPORT TESTS PASSED but EXECUTION FAILED")
                print("The tool is configured correctly but may have issues with the underlying CORDIS service.")
        else:
            print("\n❌ IMPORT TESTS FAILED")
            print("The tool configuration has issues that need to be resolved.")

    asyncio.run(main())