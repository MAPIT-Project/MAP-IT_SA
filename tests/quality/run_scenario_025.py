#!/usr/bin/env python
"""
Run Scenario 025: Urgent Deadline

Execute the urgent deadline scenario and save results.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.quality.test_scenario_runner import ProductionQualityRunner


async def main():
    """Run the urgent deadline scenario."""
    # Initialize runner
    runner = ProductionQualityRunner(
        base_url="http://localhost:8000",
        passing_threshold=80,
    )

    # Scenario path
    scenario_path = Path("tests/scenarios/advanced/urgent_deadline.yaml")

    print(f"Running scenario: {scenario_path}")
    print("=" * 60)

    # Run scenario
    result = await runner.run_scenario(scenario_path)

    # Print results
    print(f"\nScenario: {result.scenario_name}")
    print(f"Status: {result.status}")
    print(f"Average Quality Score: {result.average_quality_score:.1f}")
    print(f"Average Factual Score: {result.average_factual_score:.1f}")
    print(f"Execution Time: {result.execution_time_ms / 1000:.1f}s")
    print(f"Passed: {result.passed}")

    print("\n" + "-" * 60)
    print("Turn Details:")
    for turn in result.turns:
        status = "PASS" if turn.passed else "FAIL"
        print(f"  Turn {turn.turn_number + 1}: {turn.quality_score:.0f}/100 [{status}]")
        print(f"    Query: {turn.query[:60]}...")
        if turn.tools_used:
            print(f"    Tools: {', '.join(turn.tools_used)}")
        if turn.failures:
            for f in turn.failures:
                print(f"    FAILURE [{f.severity.value}]: {f.description}")

    print("\n" + "-" * 60)
    print(
        f"Critical Failures: {len([f for f in result.failures if f.severity.value == 'CRITICAL'])}"
    )
    print(f"High Failures: {len([f for f in result.failures if f.severity.value == 'HIGH'])}")
    print(f"Medium Failures: {len([f for f in result.failures if f.severity.value == 'MEDIUM'])}")

    # Save result with standard naming (urgent_deadline.json)
    output_dir = Path("tests/quality/results/scenarios")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "urgent_deadline.json"

    with open(output_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    print(f"\nResult saved to: {output_path}")

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result.passed else 1)
