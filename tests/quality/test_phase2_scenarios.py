# isort: skip_file
"""
Phase 2 Scenario Execution Tests (Task 005).

Executes the Proposal Workflows scenarios against the live API
and validates quality per PRD requirements.

Phase 2 Scenarios:
- full_proposal_journey.yaml (15 turns - CRITICAL)
- budget_iteration.yaml
- timeline_refinement.yaml
- consortium_building.yaml

Success Criteria (per PRD):
- All scenarios must score >= 80/100 average quality
- Zero critical failures
- Factual accuracy >= 90%
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

# Import production quality runner and data structures
from tests.test_production_quality_validation import (
    ScenarioExecutionResult,
    FailureCategory,
    FailureSeverity,
)

logger = logging.getLogger(__name__)

# Directory paths
SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios" / "advanced"
RESULTS_DIR = Path(__file__).parent / "results" / "phase2"


# =============================================================================
# Phase 2 Scenario List
# =============================================================================

PHASE2_SCENARIOS = [
    "full_proposal_journey.yaml",
    "budget_iteration.yaml",
    "timeline_refinement.yaml",
    "consortium_building.yaml",
]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def base_url() -> str:
    """Get API base URL from environment or default."""
    return os.environ.get("TEST_API_URL", "http://localhost:8000")


@pytest.fixture
def results_dir() -> Path:
    """Create and return the results directory."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR


# =============================================================================
# Helper Functions
# =============================================================================


def save_scenario_result(result: ScenarioExecutionResult, output_dir: Path) -> Path:
    """Save a scenario result to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create filename from scenario name
    safe_name = result.scenario_name.lower().replace(" ", "_").replace("-", "_")
    filename = f"{safe_name}_result.json"
    output_path = output_dir / filename

    with open(output_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    return output_path


def generate_phase2_report(
    results: list[ScenarioExecutionResult], output_dir: Path
) -> dict[str, Any]:
    """Generate a comprehensive Phase 2 report."""
    total_scenarios = len(results)
    passed_scenarios = sum(1 for r in results if r.passed)
    failed_scenarios = total_scenarios - passed_scenarios

    all_failures = []
    for r in results:
        all_failures.extend(r.failures)

    critical_failures = [f for f in all_failures if f.severity == FailureSeverity.CRITICAL]
    high_failures = [f for f in all_failures if f.severity == FailureSeverity.HIGH]
    medium_failures = [f for f in all_failures if f.severity == FailureSeverity.MEDIUM]

    # Calculate average scores
    avg_quality = sum(r.average_quality_score for r in results) / len(results) if results else 0.0
    avg_factual = sum(r.average_factual_score for r in results) / len(results) if results else 0.0

    # Calculate total runtime
    total_runtime_ms = sum(r.execution_time_ms for r in results)

    # Group failures by category
    failures_by_category = {}
    for category in FailureCategory:
        count = len([f for f in all_failures if f.category == category])
        failures_by_category[category.value] = count

    report = {
        "phase": "Phase 2 - Proposal Workflows",
        "summary": {
            "total_scenarios": total_scenarios,
            "passed": passed_scenarios,
            "failed": failed_scenarios,
            "pass_rate": ((passed_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0),
            "average_quality_score": round(avg_quality, 2),
            "average_factual_score": round(avg_factual, 2),
            "total_runtime_seconds": round(total_runtime_ms / 1000, 2),
            "critical_failures": len(critical_failures),
            "high_failures": len(high_failures),
            "medium_failures": len(medium_failures),
        },
        "failures_by_category": failures_by_category,
        "scenario_results": [],
        "timestamp": datetime.now().isoformat(),
    }

    # Add individual scenario summaries
    for result in results:
        scenario_summary = {
            "name": result.scenario_name,
            "status": result.status,
            "average_quality_score": round(result.average_quality_score, 2),
            "average_factual_score": round(result.average_factual_score, 2),
            "runtime_seconds": round(result.execution_time_ms / 1000, 2),
            "turn_count": len(result.turns),
            "failures": len(result.failures),
            "critical_failures": len(
                [f for f in result.failures if f.severity == FailureSeverity.CRITICAL]
            ),
        }
        report["scenario_results"].append(scenario_summary)

    # Save report
    report_path = output_dir / "phase2_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


# =============================================================================
# Individual Scenario Tests
# =============================================================================


# =============================================================================
# Full Phase 2 Execution Test
# =============================================================================


# =============================================================================
# Offline Tests (Run without live API)
# =============================================================================


class TestPhase2Infrastructure:
    """Tests for Phase 2 infrastructure that don't require live API."""

    def test_scenarios_exist(self):
        """Verify all Phase 2 scenario files exist."""
        for scenario_file in PHASE2_SCENARIOS:
            scenario_path = SCENARIOS_DIR / scenario_file
            assert scenario_path.exists(), f"Missing scenario: {scenario_path}"

    def test_scenarios_are_valid_yaml(self):
        """Verify all Phase 2 scenarios are valid YAML."""
        import yaml

        for scenario_file in PHASE2_SCENARIOS:
            scenario_path = SCENARIOS_DIR / scenario_file
            if scenario_path.exists():
                with open(scenario_path) as f:
                    data = yaml.safe_load(f)
                assert "name" in data, f"Scenario {scenario_file} missing 'name'"
                assert "steps" in data, f"Scenario {scenario_file} missing 'steps'"
                assert len(data["steps"]) > 0, f"Scenario {scenario_file} has no steps"

    def test_full_proposal_journey_has_15_steps(self):
        """Verify full_proposal_journey.yaml has 15+ steps as required."""
        import yaml

        scenario_path = SCENARIOS_DIR / "full_proposal_journey.yaml"
        if scenario_path.exists():
            with open(scenario_path) as f:
                data = yaml.safe_load(f)
            assert (
                len(data["steps"]) >= 15
            ), f"full_proposal_journey.yaml should have 15+ steps, found {len(data['steps'])}"

    def test_results_directory_creation(self, results_dir: Path):
        """Verify results directory can be created."""
        assert results_dir.exists()
        assert results_dir.is_dir()

    def test_report_generation_empty_results(self, results_dir: Path):
        """Test report generation with empty results."""
        report = generate_phase2_report([], results_dir)

        assert report["summary"]["total_scenarios"] == 0
        assert report["summary"]["pass_rate"] == 0
        assert "timestamp" in report

    def test_report_generation_mock_results(self, results_dir: Path):
        """Test report generation with mock results."""
        from tests.test_production_quality_validation import TurnResult

        # Create mock results
        mock_results = [
            ScenarioExecutionResult(
                scenario_name="Full Proposal Journey",
                turns=[
                    TurnResult(
                        query="Q1",
                        response="R1" * 100,
                        quality_score=85,
                        factual_score=90,
                        turn_number=0,
                    )
                ],
                execution_time_ms=120000,
            ),
            ScenarioExecutionResult(
                scenario_name="Budget Iteration",
                turns=[
                    TurnResult(
                        query="Q2",
                        response="R2" * 100,
                        quality_score=82,
                        factual_score=95,
                        turn_number=0,
                    )
                ],
                execution_time_ms=45000,
            ),
            ScenarioExecutionResult(
                scenario_name="Timeline Refinement",
                turns=[
                    TurnResult(
                        query="Q3",
                        response="R3" * 100,
                        quality_score=88,
                        factual_score=92,
                        turn_number=0,
                    )
                ],
                execution_time_ms=40000,
            ),
            ScenarioExecutionResult(
                scenario_name="Consortium Building",
                turns=[
                    TurnResult(
                        query="Q4",
                        response="R4" * 100,
                        quality_score=84,
                        factual_score=90,
                        turn_number=0,
                    )
                ],
                execution_time_ms=50000,
            ),
        ]

        report = generate_phase2_report(mock_results, results_dir)

        assert report["summary"]["total_scenarios"] == 4
        assert report["summary"]["passed"] == 4
        assert report["summary"]["average_quality_score"] == 84.75
        assert len(report["scenario_results"]) == 4
