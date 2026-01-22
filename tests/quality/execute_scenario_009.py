#!/usr/bin/env python3
# isort: skip_file
"""
Execute Scenario 009: Partner Search Refinement against the live API.

This script runs the partner_search_refinement scenario and saves the results
to tests/quality/results/scenarios/partner_search_refinement.json

Per PRD Task: Scenario 009 EXECUTE
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.test_production_quality_validation import ProductionQualityRunner


async def main():
    """Execute Scenario 009 and save results."""
    # Initialize runner
    runner = ProductionQualityRunner(base_url="http://localhost:8000")

    # Scenario path
    scenario_path = Path("tests/scenarios/advanced/partner_search_refinement.yaml")

    print(f"[{datetime.now().isoformat()}] Executing Scenario 009: Partner Search Refinement")
    print(f"Scenario path: {scenario_path}")
    print("-" * 60)

    # Execute scenario
    result = await runner.run_scenario(scenario_path)

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"SCENARIO COMPLETE: {result.scenario_name}")
    print(f"{'=' * 60}")
    print(f"Status: {result.status}")
    print(f"Average Quality Score: {result.average_quality_score:.2f}/100")
    print(f"Average Factual Score: {result.average_factual_score:.2f}/100")
    print(f"Execution Time: {result.execution_time_ms:.0f}ms")
    print(f"Turns: {len(result.turns)}")
    print()

    # Print per-turn summary
    print("Per-Turn Results:")
    print("-" * 60)
    for i, turn in enumerate(result.turns):
        status = "✓" if turn.passed else "✗"
        tools = ", ".join(turn.tools_used) if turn.tools_used else "none"
        print(f"Turn {i}: {status} Score={turn.quality_score:.0f} Tools=[{tools}]")
        print(f"        Query: {turn.query[:60]}...")
    print()

    # Build output structure matching expected format from PRD
    output = {
        "scenario_name": result.scenario_name,
        "turns": [],
        "average_score": result.average_quality_score,
        "factual_score": result.average_factual_score,
        "failures": [],
        "status": result.status,
        "execution_time_ms": result.execution_time_ms,
        "timestamp": datetime.now().isoformat(),
        "metadata": result.metadata,
    }

    # Format turns
    for turn in result.turns:
        turn_data = {
            "turn_number": turn.turn_number,
            "query": turn.query,
            "response_text": turn.response,
            "tools_used": turn.tools_used,
            "quality_score": turn.quality_score,
            "factual_score": turn.factual_score,
            "failures": [f.description for f in turn.failures] if turn.failures else [],
            "passed": turn.passed,
        }
        output["turns"].append(turn_data)

    # Aggregate failures
    for turn in result.turns:
        for failure in turn.failures:
            if failure.description not in output["failures"]:
                output["failures"].append(failure.description)

    # Save to JSON
    output_path = Path("tests/quality/results/scenarios/partner_search_refinement.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Results saved to: {output_path}")
    print(f"Final Status: {result.status}")

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    # Exit with 0 if passed, 1 if failed
    sys.exit(0 if result.passed else 1)
