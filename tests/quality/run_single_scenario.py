#!/usr/bin/env python3
# isort: skip_file
"""
Run a single scenario and save results.

Usage:
    python tests/quality/run_single_scenario.py <scenario_path> [<output_path>]

Example:
    python tests/quality/run_single_scenario.py scenario.yaml
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.test_production_quality_validation import (
    ProductionQualityRunner,
    ScenarioExecutionResult,
)


async def run_scenario(
    scenario_path: str, output_path: str | None = None
) -> ScenarioExecutionResult:
    """Run a single scenario and save results."""
    runner = ProductionQualityRunner(base_url="http://localhost:8000")

    print(f"Running scenario: {scenario_path}")
    result = await runner.run_scenario(scenario_path)

    # Determine output path
    if output_path is None:
        scenario_name = Path(scenario_path).stem
        output_path = f"tests/quality/results/scenarios/{scenario_name}.json"

    # Save results
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Scenario: {result.scenario_name}")
    print(f"Status: {result.status}")
    print(f"Average Quality Score: {result.average_quality_score:.1f}")
    print(f"Average Factual Score: {result.average_factual_score:.1f}")
    print(f"Turns: {len(result.turns)}")
    critical = len([f for f in result.failures if f.severity.value == "CRITICAL"])
    high = len([f for f in result.failures if f.severity.value == "HIGH"])
    print(f"Critical Failures: {critical}")
    print(f"High Failures: {high}")
    print(f"Results saved to: {output_file}")
    print(f"{'=' * 60}\n")

    # Print per-turn details
    print("Turn Details:")
    for turn in result.turns:
        status = "✓" if turn.passed else "✗"
        print(
            f"  Turn {turn.turn_number + 1}: {status} Score={turn.quality_score:.0f}, "
            f"Tools={turn.tools_used or 'none'}"
        )

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_single_scenario.py <scenario_path> [<output_path>]")
        sys.exit(1)

    scenario_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = asyncio.run(run_scenario(scenario_path, output_path))
    sys.exit(0 if result.passed else 1)
