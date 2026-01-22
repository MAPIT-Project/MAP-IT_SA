# isort: skip_file
"""
Phase 3 Scenario Execution Tests (Task 006).

Executes the Partner Discovery scenarios against the live API
and validates quality per PRD requirements.

Phase 3 Scenarios:
- partner_search_refinement.yaml (5 turns - iterative filtering)
- partner_comparison.yaml (5 turns - ranking and recommendation)
- network_exploration.yaml (5 turns - relationship traversal)
- organization_deep_dive.yaml (5 turns - profile exploration)

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
    ProductionQualityRunner,
    ScenarioExecutionResult,
    FailureCategory,
    FailureSeverity,
)

logger = logging.getLogger(__name__)

# Directory paths
SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios" / "advanced"
RESULTS_DIR = Path(__file__).parent / "results" / "phase3"


# =============================================================================
# Phase 3 Scenario List
# =============================================================================

PHASE3_SCENARIOS = [
    "partner_search_refinement.yaml",
    "partner_comparison.yaml",
    "network_exploration.yaml",
    "organization_deep_dive.yaml",
]


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


def generate_phase3_report(
    results: list[ScenarioExecutionResult], output_dir: Path
) -> dict[str, Any]:
    """Generate a comprehensive Phase 3 report."""
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
        "phase": "Phase 3 - Partner Discovery",
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
    report_path = output_dir / "phase3_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


# =============================================================================
# Individual Scenario Tests
# =============================================================================


class TestPhase3Scenarios:
    """Test class for Phase 3 Partner Discovery scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("SKIP_LIVE_API_TESTS") == "1",
        reason="SKIP_LIVE_API_TESTS is set",
    )
    async def test_partner_search_refinement(
        self, runner: ProductionQualityRunner, results_dir: Path
    ):
        """
        RUN: partner_search_refinement.yaml

        Tests iterative partner search with incremental filter refinement.
        A user progressively narrows down partner search for quantum computing research
        through 5 steps: broad search → universities only → EU15 countries →
        coordination experience → quantum communication expertise.

        Key Test: Filters should be applied incrementally, with results narrowing correctly.
        """
        scenario_path = SCENARIOS_DIR / "partner_search_refinement.yaml"

        if not scenario_path.exists():
            pytest.skip(f"Scenario file not found: {scenario_path}")

        result = await runner.run_scenario(scenario_path)
        save_scenario_result(result, results_dir)

        # Log results
        logger.info(
            f"partner_search_refinement: Runtime={result.execution_time_ms / 1000:.2f}s, "
            f"Score={result.average_quality_score:.1f}/100, "
            f"Failures={len(result.failures)}, Status={result.status}"
        )

        # Assert minimum quality threshold
        assert result.average_quality_score >= 80, (
            f"Partner Search Refinement score {result.average_quality_score:.1f} < 80. "
            f"Failures: {[f.description for f in result.failures]}"
        )

        # Assert no critical failures
        critical = [f for f in result.failures if f.severity == FailureSeverity.CRITICAL]
        assert len(critical) == 0, (
            f"Partner Search Refinement has {len(critical)} critical failures: "
            f"{[f.description for f in critical]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("SKIP_LIVE_API_TESTS") == "1",
        reason="SKIP_LIVE_API_TESTS is set",
    )
    async def test_partner_comparison(self, runner: ProductionQualityRunner, results_dir: Path):
        """
        RUN: partner_comparison.yaml

        Tests partner comparison workflow with ranking and recommendation.
        A user finds experienced partners in renewable energy, compares top 3 organizations,
        analyzes funding and network diversity, then gets a coordination recommendation.

        Key Test: Comparison should be accurate and recommendation justified with data.
        """
        scenario_path = SCENARIOS_DIR / "partner_comparison.yaml"

        if not scenario_path.exists():
            pytest.skip(f"Scenario file not found: {scenario_path}")

        result = await runner.run_scenario(scenario_path)
        save_scenario_result(result, results_dir)

        logger.info(
            f"partner_comparison: Runtime={result.execution_time_ms / 1000:.2f}s, "
            f"Score={result.average_quality_score:.1f}/100, "
            f"Failures={len(result.failures)}, Status={result.status}"
        )

        assert result.average_quality_score >= 80, (
            f"Partner Comparison score {result.average_quality_score:.1f} < 80. "
            f"Failures: {[f.description for f in result.failures]}"
        )

        critical = [f for f in result.failures if f.severity == FailureSeverity.CRITICAL]
        assert len(critical) == 0, (
            f"Partner Comparison has {len(critical)} critical failures: "
            f"{[f.description for f in critical]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("SKIP_LIVE_API_TESTS") == "1",
        reason="SKIP_LIVE_API_TESTS is set",
    )
    async def test_network_exploration(self, runner: ProductionQualityRunner, results_dir: Path):
        """
        RUN: network_exploration.yaml

        Tests network traversal and relationship discovery workflows.
        A user explores the collaboration network for climate research,
        identifies key players, explores Fraunhofer's projects, their partners,
        and follows relationship chains to hydrogen-focused collaborators.

        Key Test: Network traversal works, relationship chains followed.
        """
        scenario_path = SCENARIOS_DIR / "network_exploration.yaml"

        if not scenario_path.exists():
            pytest.skip(f"Scenario file not found: {scenario_path}")

        result = await runner.run_scenario(scenario_path)
        save_scenario_result(result, results_dir)

        logger.info(
            f"network_exploration: Runtime={result.execution_time_ms / 1000:.2f}s, "
            f"Score={result.average_quality_score:.1f}/100, "
            f"Failures={len(result.failures)}, Status={result.status}"
        )

        assert result.average_quality_score >= 80, (
            f"Network Exploration score {result.average_quality_score:.1f} < 80. "
            f"Failures: {[f.description for f in result.failures]}"
        )

        critical = [f for f in result.failures if f.severity == FailureSeverity.CRITICAL]
        assert len(critical) == 0, (
            f"Network Exploration has {len(critical)} critical failures: "
            f"{[f.description for f in critical]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("SKIP_LIVE_API_TESTS") == "1",
        reason="SKIP_LIVE_API_TESTS is set",
    )
    async def test_organization_deep_dive(self, runner: ProductionQualityRunner, results_dir: Path):
        """
        RUN: organization_deep_dive.yaml

        Tests organization profile exploration and detailed information retrieval.
        A user explores Technical University of Munich's EU funding history,
        research topics, success rate as coordinator, recent projects,
        and preferred partners.

        Key Test: Organization profile complete, statistics accurate.
        """
        scenario_path = SCENARIOS_DIR / "organization_deep_dive.yaml"

        if not scenario_path.exists():
            pytest.skip(f"Scenario file not found: {scenario_path}")

        result = await runner.run_scenario(scenario_path)
        save_scenario_result(result, results_dir)

        logger.info(
            f"organization_deep_dive: Runtime={result.execution_time_ms / 1000:.2f}s, "
            f"Score={result.average_quality_score:.1f}/100, "
            f"Failures={len(result.failures)}, Status={result.status}"
        )

        assert result.average_quality_score >= 80, (
            f"Organization Deep-Dive score {result.average_quality_score:.1f} < 80. "
            f"Failures: {[f.description for f in result.failures]}"
        )

        critical = [f for f in result.failures if f.severity == FailureSeverity.CRITICAL]
        assert len(critical) == 0, (
            f"Organization Deep-Dive has {len(critical)} critical failures: "
            f"{[f.description for f in critical]}"
        )


# =============================================================================
# Full Phase 3 Execution Test
# =============================================================================


class TestPhase3FullExecution:
    """Full Phase 3 execution test that runs all scenarios and generates report."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("SKIP_LIVE_API_TESTS") == "1",
        reason="SKIP_LIVE_API_TESTS is set",
    )
    async def test_run_all_phase3_scenarios(
        self, runner: ProductionQualityRunner, results_dir: Path
    ):
        """
        Run all Phase 3 scenarios and verify all pass with >= 80/100.

        This is the main test that satisfies Task 006 requirements:
        - RUN all 4 Phase 3 scenarios
        - VERIFY all pass with >= 80/100
        """
        results: list[ScenarioExecutionResult] = []

        for scenario_file in PHASE3_SCENARIOS:
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
        report = generate_phase3_report(results, results_dir)

        # Print summary
        print("\n" + "=" * 60)
        print("PHASE 3 EXECUTION RESULTS")
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
            f"Not all Phase 3 scenarios passed: "
            f"{report['summary']['passed']}/{report['summary']['total_scenarios']}"
        )

        # Verify average quality score
        assert (
            report["summary"]["average_quality_score"] >= 80
        ), f"Phase 3 average quality score {report['summary']['average_quality_score']} < 80"

        # Verify no critical failures
        assert (
            report["summary"]["critical_failures"] == 0
        ), f"Phase 3 has {report['summary']['critical_failures']} critical failures"


# =============================================================================
# Offline Tests (Run without live API)
# =============================================================================


class TestPhase3Infrastructure:
    """Tests for Phase 3 infrastructure that don't require live API."""

    def test_scenarios_exist(self):
        """Verify all Phase 3 scenario files exist."""
        for scenario_file in PHASE3_SCENARIOS:
            scenario_path = SCENARIOS_DIR / scenario_file
            assert scenario_path.exists(), f"Missing scenario: {scenario_path}"

    def test_scenarios_are_valid_yaml(self):
        """Verify all Phase 3 scenarios are valid YAML."""
        import yaml

        for scenario_file in PHASE3_SCENARIOS:
            scenario_path = SCENARIOS_DIR / scenario_file
            if scenario_path.exists():
                with open(scenario_path) as f:
                    data = yaml.safe_load(f)
                assert "name" in data, f"Scenario {scenario_file} missing 'name'"
                assert "steps" in data, f"Scenario {scenario_file} missing 'steps'"
                assert len(data["steps"]) > 0, f"Scenario {scenario_file} has no steps"

    def test_all_scenarios_have_5_steps(self):
        """Verify all Phase 3 scenarios have 5 steps as required."""
        import yaml

        for scenario_file in PHASE3_SCENARIOS:
            scenario_path = SCENARIOS_DIR / scenario_file
            if scenario_path.exists():
                with open(scenario_path) as f:
                    data = yaml.safe_load(f)
                assert (
                    len(data["steps"]) == 5
                ), f"{scenario_file} should have 5 steps, found {len(data['steps'])}"

    def test_results_directory_creation(self, results_dir: Path):
        """Verify results directory can be created."""
        assert results_dir.exists()
        assert results_dir.is_dir()

    def test_report_generation_empty_results(self, results_dir: Path):
        """Test report generation with empty results."""
        report = generate_phase3_report([], results_dir)

        assert report["summary"]["total_scenarios"] == 0
        assert report["summary"]["pass_rate"] == 0
        assert "timestamp" in report

    def test_report_generation_mock_results(self, results_dir: Path):
        """Test report generation with mock results."""
        from tests.test_production_quality_validation import TurnResult

        # Create mock results
        mock_results = [
            ScenarioExecutionResult(
                scenario_name="Partner Search Refinement",
                turns=[
                    TurnResult(
                        query="Q1",
                        response="R1" * 100,
                        quality_score=85,
                        factual_score=90,
                        turn_number=0,
                    )
                ],
                execution_time_ms=90000,
            ),
            ScenarioExecutionResult(
                scenario_name="Partner Comparison",
                turns=[
                    TurnResult(
                        query="Q2",
                        response="R2" * 100,
                        quality_score=82,
                        factual_score=95,
                        turn_number=0,
                    )
                ],
                execution_time_ms=85000,
            ),
            ScenarioExecutionResult(
                scenario_name="Network Exploration",
                turns=[
                    TurnResult(
                        query="Q3",
                        response="R3" * 100,
                        quality_score=88,
                        factual_score=92,
                        turn_number=0,
                    )
                ],
                execution_time_ms=95000,
            ),
            ScenarioExecutionResult(
                scenario_name="Organization Deep-Dive",
                turns=[
                    TurnResult(
                        query="Q4",
                        response="R4" * 100,
                        quality_score=84,
                        factual_score=90,
                        turn_number=0,
                    )
                ],
                execution_time_ms=80000,
            ),
        ]

        report = generate_phase3_report(mock_results, results_dir)

        assert report["summary"]["total_scenarios"] == 4
        assert report["summary"]["passed"] == 4
        assert report["summary"]["average_quality_score"] == 84.75
        assert len(report["scenario_results"]) == 4
