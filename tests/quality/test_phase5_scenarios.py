# isort: skip_file
"""
Phase 5 Scenario Execution Tests (Task 008).

Executes the Strategic Planning scenarios against the live API
and validates quality per PRD requirements.

Phase 5 Scenarios:
- funding_strategy.yaml (6 turns - multi-year strategic planning)
- portfolio_planning.yaml (6 turns - multiple proposal management)
- capacity_building.yaml (5 turns - beginner onboarding)
- risk_assessment.yaml (5 turns - EIC Accelerator risk analysis)

Success Criteria (per PRD):
- All scenarios must score >= 80/100 average quality
- Zero critical failures
- Factual accuracy >= 90%
- Strategic advice quality tracked
- Context preserved across turns
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
    ProductionQualityRunner,
    ScenarioExecutionResult,
    FailureCategory,
    FailureSeverity,
)

logger = logging.getLogger(__name__)

# Directory paths
SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios" / "advanced"
RESULTS_DIR = Path(__file__).parent / "results" / "phase5"


# =============================================================================
# Phase 5 Scenario List
# =============================================================================

PHASE5_SCENARIOS = [
    "funding_strategy.yaml",
    "portfolio_planning.yaml",
    "capacity_building.yaml",
    "risk_assessment.yaml",
]

# Expected step counts for each scenario (from PRD and YAML files)
SCENARIO_STEP_COUNTS = {
    "funding_strategy.yaml": 6,
    "portfolio_planning.yaml": 6,
    "capacity_building.yaml": 5,
    "risk_assessment.yaml": 5,
}


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def base_url() -> str:
    """Get API base URL from environment or default."""
    return os.environ.get("TEST_API_URL", "http://localhost:8000")


@pytest.fixture
def runner(base_url: str) -> ProductionQualityRunner:
    """Create a ProductionQualityRunner instance."""
    return ProductionQualityRunner(
        base_url=base_url,
        passing_threshold=80,
        factual_threshold=0.9,
    )


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


def generate_phase5_report(
    results: list[ScenarioExecutionResult], output_dir: Path
) -> dict[str, Any]:
    """Generate a comprehensive Phase 5 report."""
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
        "phase": "Phase 5 - Strategic Planning",
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
    report_path = output_dir / "phase5_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


# =============================================================================
# Individual Scenario Tests
# =============================================================================


class TestPhase5Scenarios:
    """Test class for Phase 5 Strategic Planning scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("SKIP_LIVE_API_TESTS") == "1",
        reason="SKIP_LIVE_API_TESTS is set",
    )
    async def test_funding_strategy(self, runner: ProductionQualityRunner, results_dir: Path):
        """
        RUN: funding_strategy.yaml

        Tests multi-year strategic planning for EU funding.
        A university cybersecurity department seeks help planning a 3-year
        funding strategy combining Horizon Europe and Erasmus+ options.

        Key Test: System should provide multi-programme strategic advice
        with logical application sequencing and realistic timelines.
        """
        scenario_path = SCENARIOS_DIR / "funding_strategy.yaml"

        if not scenario_path.exists():
            pytest.skip(f"Scenario file not found: {scenario_path}")

        result = await runner.run_scenario(scenario_path)
        save_scenario_result(result, results_dir)

        # Log results
        logger.info(
            f"funding_strategy: Runtime={result.execution_time_ms / 1000:.2f}s, "
            f"Score={result.average_quality_score:.1f}/100, "
            f"Failures={len(result.failures)}, Status={result.status}"
        )

        # Assert minimum quality threshold
        assert result.average_quality_score >= 80, (
            f"Funding Strategy score {result.average_quality_score:.1f} < 80. "
            f"Failures: {[f.description for f in result.failures]}"
        )

        # Assert no critical failures
        critical = [f for f in result.failures if f.severity == FailureSeverity.CRITICAL]
        assert len(critical) == 0, (
            f"Funding Strategy has {len(critical)} critical failures: "
            f"{[f.description for f in critical]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("SKIP_LIVE_API_TESTS") == "1",
        reason="SKIP_LIVE_API_TESTS is set",
    )
    async def test_portfolio_planning(self, runner: ProductionQualityRunner, results_dir: Path):
        """
        RUN: portfolio_planning.yaml

        Tests portfolio approach for managing multiple EU funding applications.
        A researcher wants to submit 5 proposals in AI, robotics, and HMI,
        seeking advice on call matching, prioritization, and overlap avoidance.

        Key Test: System should recommend portfolio approach with diversification,
        success rate considerations, and overlap avoidance strategies.
        """
        scenario_path = SCENARIOS_DIR / "portfolio_planning.yaml"

        if not scenario_path.exists():
            pytest.skip(f"Scenario file not found: {scenario_path}")

        result = await runner.run_scenario(scenario_path)
        save_scenario_result(result, results_dir)

        logger.info(
            f"portfolio_planning: Runtime={result.execution_time_ms / 1000:.2f}s, "
            f"Score={result.average_quality_score:.1f}/100, "
            f"Failures={len(result.failures)}, Status={result.status}"
        )

        assert result.average_quality_score >= 80, (
            f"Portfolio Planning score {result.average_quality_score:.1f} < 80. "
            f"Failures: {[f.description for f in result.failures]}"
        )

        critical = [f for f in result.failures if f.severity == FailureSeverity.CRITICAL]
        assert len(critical) == 0, (
            f"Portfolio Planning has {len(critical)} critical failures: "
            f"{[f.description for f in critical]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("SKIP_LIVE_API_TESTS") == "1",
        reason="SKIP_LIVE_API_TESTS is set",
    )
    async def test_capacity_building(self, runner: ProductionQualityRunner, results_dir: Path):
        """
        RUN: capacity_building.yaml

        Tests beginner-friendly onboarding for organizations new to EU funding.
        A newcomer organization asks about getting started, suitable programmes,
        partner vs coordinator roles, project sizes, and building track record.

        Key Test: System should provide beginner-appropriate advice with
        a clear progression path from newcomer to experienced participant.
        """
        scenario_path = SCENARIOS_DIR / "capacity_building.yaml"

        if not scenario_path.exists():
            pytest.skip(f"Scenario file not found: {scenario_path}")

        result = await runner.run_scenario(scenario_path)
        save_scenario_result(result, results_dir)

        logger.info(
            f"capacity_building: Runtime={result.execution_time_ms / 1000:.2f}s, "
            f"Score={result.average_quality_score:.1f}/100, "
            f"Failures={len(result.failures)}, Status={result.status}"
        )

        assert result.average_quality_score >= 80, (
            f"Capacity Building score {result.average_quality_score:.1f} < 80. "
            f"Failures: {[f.description for f in result.failures]}"
        )

        critical = [f for f in result.failures if f.severity == FailureSeverity.CRITICAL]
        assert len(critical) == 0, (
            f"Capacity Building has {len(critical)} critical failures: "
            f"{[f.description for f in critical]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("SKIP_LIVE_API_TESTS") == "1",
        reason="SKIP_LIVE_API_TESTS is set",
    )
    async def test_risk_assessment(self, runner: ProductionQualityRunner, results_dir: Path):
        """
        RUN: risk_assessment.yaml

        Tests EIC Accelerator risk analysis and mitigation strategies.
        A user asks about risks of applying to EIC Accelerator, impact of
        prior funding and company size, the interview stage, and improvement strategies.

        Key Test: System should accurately identify EIC risks, explain
        factors affecting success, and provide actionable mitigation strategies.
        """
        scenario_path = SCENARIOS_DIR / "risk_assessment.yaml"

        if not scenario_path.exists():
            pytest.skip(f"Scenario file not found: {scenario_path}")

        result = await runner.run_scenario(scenario_path)
        save_scenario_result(result, results_dir)

        logger.info(
            f"risk_assessment: Runtime={result.execution_time_ms / 1000:.2f}s, "
            f"Score={result.average_quality_score:.1f}/100, "
            f"Failures={len(result.failures)}, Status={result.status}"
        )

        assert result.average_quality_score >= 80, (
            f"Risk Assessment score {result.average_quality_score:.1f} < 80. "
            f"Failures: {[f.description for f in result.failures]}"
        )

        critical = [f for f in result.failures if f.severity == FailureSeverity.CRITICAL]
        assert len(critical) == 0, (
            f"Risk Assessment has {len(critical)} critical failures: "
            f"{[f.description for f in critical]}"
        )


# =============================================================================
# Full Phase 5 Execution Test
# =============================================================================


class TestPhase5FullExecution:
    """Full Phase 5 execution test that runs all scenarios and generates report."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("SKIP_LIVE_API_TESTS") == "1",
        reason="SKIP_LIVE_API_TESTS is set",
    )
    async def test_run_all_phase5_scenarios(
        self, runner: ProductionQualityRunner, results_dir: Path
    ):
        """
        Run all Phase 5 scenarios and verify all pass with >= 80/100.

        This is the main test that satisfies Task 008 requirements:
        - RUN all 4 Phase 5 scenarios
        - VERIFY all pass with >= 80/100
        """
        results: list[ScenarioExecutionResult] = []

        for scenario_file in PHASE5_SCENARIOS:
            scenario_path = SCENARIOS_DIR / scenario_file

            if not scenario_path.exists():
                logger.warning(f"Scenario not found, skipping: {scenario_path}")
                continue

            logger.info(f"Running scenario: {scenario_file}")
            result = await runner.run_scenario(scenario_path)
            results.append(result)

            # Save individual result
            save_scenario_result(result, results_dir)

            # Log individual result
            logger.info(
                f"  → {result.scenario_name}: "
                f"Score={result.average_quality_score:.1f}/100, "
                f"Status={result.status}"
            )

        # Generate phase report
        report = generate_phase5_report(results, results_dir)

        # Print summary
        print("\n" + "=" * 60)
        print("PHASE 5 EXECUTION RESULTS")
        print("=" * 60)
        print(f"Total Scenarios: {report['summary']['total_scenarios']}")
        print(f"Passed: {report['summary']['passed']}")
        print(f"Failed: {report['summary']['failed']}")
        print(f"Pass Rate: {report['summary']['pass_rate']:.1f}%")
        print(f"Average Quality Score: {report['summary']['average_quality_score']}/100")
        print(f"Average Factual Score: {report['summary']['average_factual_score']}/100")
        print(f"Total Runtime: {report['summary']['total_runtime_seconds']:.2f}s")
        print(f"Critical Failures: {report['summary']['critical_failures']}")
        print("=" * 60)

        for scenario_result in report["scenario_results"]:
            status_icon = "✓" if scenario_result["status"] == "PASS" else "✗"
            print(
                f"  {status_icon} {scenario_result['name']}: "
                f"{scenario_result['average_quality_score']}/100 "
                f"({scenario_result['runtime_seconds']:.2f}s)"
            )

        print("=" * 60 + "\n")

        # Verify all scenarios passed
        assert report["summary"]["passed"] == report["summary"]["total_scenarios"], (
            f"Not all Phase 5 scenarios passed: "
            f"{report['summary']['passed']}/{report['summary']['total_scenarios']}"
        )

        # Verify average quality score
        assert report["summary"]["average_quality_score"] >= 80, (
            f"Phase 5 average quality score {report['summary']['average_quality_score']} < 80"
        )

        # Verify no critical failures
        assert report["summary"]["critical_failures"] == 0, (
            f"Phase 5 has {report['summary']['critical_failures']} critical failures"
        )


# =============================================================================
# Offline Tests (Run without live API)
# =============================================================================


class TestPhase5Infrastructure:
    """Tests for Phase 5 infrastructure that don't require live API."""

    def test_scenarios_exist(self):
        """Verify all Phase 5 scenario files exist."""
        for scenario_file in PHASE5_SCENARIOS:
            scenario_path = SCENARIOS_DIR / scenario_file
            assert scenario_path.exists(), f"Missing scenario: {scenario_path}"

    def test_scenarios_are_valid_yaml(self):
        """Verify all Phase 5 scenarios are valid YAML."""
        import yaml

        for scenario_file in PHASE5_SCENARIOS:
            scenario_path = SCENARIOS_DIR / scenario_file
            if scenario_path.exists():
                with open(scenario_path) as f:
                    data = yaml.safe_load(f)
                assert "name" in data, f"Scenario {scenario_file} missing 'name'"
                assert "steps" in data, f"Scenario {scenario_file} missing 'steps'"
                assert len(data["steps"]) > 0, f"Scenario {scenario_file} has no steps"

    def test_scenarios_have_correct_step_counts(self):
        """Verify Phase 5 scenarios have expected step counts."""
        import yaml

        for scenario_file, expected_steps in SCENARIO_STEP_COUNTS.items():
            scenario_path = SCENARIOS_DIR / scenario_file
            if scenario_path.exists():
                with open(scenario_path) as f:
                    data = yaml.safe_load(f)
                actual_steps = len(data["steps"])
                assert actual_steps == expected_steps, (
                    f"{scenario_file} should have {expected_steps} steps, found {actual_steps}"
                )

    def test_results_directory_creation(self, results_dir: Path):
        """Verify results directory can be created."""
        assert results_dir.exists()
        assert results_dir.is_dir()

    def test_report_generation_empty_results(self, results_dir: Path):
        """Test report generation with empty results."""
        report = generate_phase5_report([], results_dir)

        assert report["summary"]["total_scenarios"] == 0
        assert report["summary"]["pass_rate"] == 0
        assert "timestamp" in report

    def test_report_generation_mock_results(self, results_dir: Path):
        """Test report generation with mock results."""
        from tests.test_production_quality_validation import TurnResult

        # Create mock results representing the 4 Phase 5 scenarios
        mock_results = [
            ScenarioExecutionResult(
                scenario_name="Funding Strategy",
                turns=[
                    TurnResult(
                        query="Q1",
                        response="R1" * 100,
                        quality_score=85,
                        factual_score=90,
                        turn_number=i,
                    )
                    for i in range(6)
                ],
                execution_time_ms=150000,
            ),
            ScenarioExecutionResult(
                scenario_name="Portfolio Planning",
                turns=[
                    TurnResult(
                        query="Q2",
                        response="R2" * 100,
                        quality_score=82,
                        factual_score=95,
                        turn_number=i,
                    )
                    for i in range(6)
                ],
                execution_time_ms=140000,
            ),
            ScenarioExecutionResult(
                scenario_name="Capacity Building",
                turns=[
                    TurnResult(
                        query="Q3",
                        response="R3" * 100,
                        quality_score=88,
                        factual_score=92,
                        turn_number=i,
                    )
                    for i in range(5)
                ],
                execution_time_ms=120000,
            ),
            ScenarioExecutionResult(
                scenario_name="Risk Assessment",
                turns=[
                    TurnResult(
                        query="Q4",
                        response="R4" * 100,
                        quality_score=84,
                        factual_score=90,
                        turn_number=i,
                    )
                    for i in range(5)
                ],
                execution_time_ms=110000,
            ),
        ]

        report = generate_phase5_report(mock_results, results_dir)

        assert report["summary"]["total_scenarios"] == 4
        assert report["summary"]["passed"] == 4
        assert report["summary"]["average_quality_score"] == 84.75
        assert len(report["scenario_results"]) == 4

        # Verify individual scenario turn counts
        for scenario_result in report["scenario_results"]:
            if "Funding Strategy" in scenario_result["name"]:
                assert scenario_result["turn_count"] == 6
            elif "Portfolio Planning" in scenario_result["name"]:
                assert scenario_result["turn_count"] == 6
            elif "Capacity Building" in scenario_result["name"]:
                assert scenario_result["turn_count"] == 5
            elif "Risk Assessment" in scenario_result["name"]:
                assert scenario_result["turn_count"] == 5
