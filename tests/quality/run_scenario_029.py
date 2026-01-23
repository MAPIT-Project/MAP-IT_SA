# isort: skip_file
#!/usr/bin/env python3
"""
Scenario 029: Multi-Factor Eligibility Execution Script

This script runs the multi-factor eligibility scenario against the live API
and saves results to the specified JSON file.

Usage:
    python tests/quality/run_scenario_029.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.quality.test_scenario_runner import ProductionQualityRunner  # noqa: E402


async def main():
    """Run scenario 029 and save results."""
    # Configuration
    scenario_path = project_root / "tests/scenarios/advanced/multi_factor_eligibility.yaml"
    results_path = project_root / "tests/quality/results/scenarios/multi_factor_eligibility.json"

    # Ensure results directory exists
    results_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Running scenario: {scenario_path}")
    print("-" * 60)

    # Initialize runner
    runner = ProductionQualityRunner(base_url="http://localhost:8000")

    # Run scenario
    result = await runner.run_scenario(scenario_path)

    # Save results
    with open(results_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    print(f"\nResults saved to: {results_path}")
    print(f"\nScenario: {result.scenario_name}")
    print(f"Status: {result.status}")
    print(f"Average Quality Score: {result.average_quality_score:.1f}")
    print(f"Average Factual Score: {result.average_factual_score:.1f}")
    print(f"Turn Count: {len(result.turns)}")
    print(f"Execution Time: {result.execution_time_ms:.2f}ms")

    print("\nPer-turn scores:")
    for i, turn in enumerate(result.turns):
        status = "PASS" if turn.passed else "FAIL"
        print(f"  Turn {i + 1}: {turn.quality_score:.0f}/100 ({status}) - {turn.query[:50]}...")

    critical_count = len([f for f in result.failures if f.severity.value == "CRITICAL"])
    print(f"\nCritical failures: {critical_count}")
    print(f"High failures: {len([f for f in result.failures if f.severity.value == 'HIGH'])}")
    print(f"Medium failures: {len([f for f in result.failures if f.severity.value == 'MEDIUM'])}")

    if result.failures:
        print("\nFailure details:")
        for f in result.failures[:5]:  # Show first 5
            print(f"  - [{f.severity.value}] Turn {f.turn_number}: {f.description}")

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result.passed else 1)
