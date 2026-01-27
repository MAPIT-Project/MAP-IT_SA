#!/usr/bin/env python3
"""
Script to inspect and display available tools in the tool orchestrator.
This helps with manual verification of tool configurations and descriptions.
"""

import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from app.services.tools.tool_orchestrator import ToolOrchestrator, create_research_orchestrator
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed (run: pip install -r requirements.txt)")
    print("Or install redis: pip install redis")
    sys.exit(1)


def inspect_builtin_tools():
    """Inspect tools registered in the basic ToolOrchestrator."""
    print("=== INSPECTING BUILT-IN TOOLS ===")
    orchestrator = ToolOrchestrator()
    orchestrator.print_available_tools()


def inspect_research_tools():
    """Inspect tools registered in the research-specific orchestrator."""
    print("=== INSPECTING RESEARCH TOOLS ===")
    orchestrator = create_research_orchestrator()
    orchestrator.print_available_tools()


def inspect_tool_details():
    """Get detailed information about tools."""
    print("=== DETAILED TOOL INSPECTION ===")

    # Basic orchestrator
    basic_orch = ToolOrchestrator()
    tools = basic_orch.get_available_tools()

    print(f"Basic Orchestrator - Total tools: {len(tools)}")
    for tool in tools:
        print(f"- {tool['name']}: {tool['description']}")

    # Research orchestrator
    research_orch = create_research_orchestrator()
    tools = research_orch.get_available_tools()

    print(f"\nResearch Orchestrator - Total tools: {len(tools)}")
    for tool in tools:
        print(f"- {tool['name']}: {tool['description']}")


if __name__ == "__main__":
    print("Tool Inspection Script")
    print("=" * 50)

    try:
        inspect_builtin_tools()
        print("\n" + "=" * 50)
        inspect_research_tools()
        print("\n" + "=" * 50)
        inspect_tool_details()

    except Exception as e:
        print(f"Error during inspection: {e}")
        import traceback

        traceback.print_exc()
