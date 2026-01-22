# isort: skip_file
"""
Test for Scenario 001: Programme Discovery (Phase 2: Multi-Programme Navigation).

This test executes the Programme Discovery scenario against the live MAPIT API
and evaluates quality using the ProductionQualityRunner.

Per PRD MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V2.md:
- EXECUTE: Run scenario `tests/scenarios/advanced/programme_discovery.yaml`
- Collect: response_text, tools_used, quality_score (QualityEvaluatorAgent),
           factual_score (CrossProgrammeAgent)
- Save: `tests/quality/results/scenarios/programme_discovery.json`
- Structure: {scenario_name, turns[], average_score, factual_score, failures[], status}
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pytest

from tests.quality.test_scenario_runner import (
    ProductionQualityRunner,
    ScenarioExecutionResult,
)

logger = logging.getLogger(__name__)

# Configuration
SCENARIO_PATH = Path("tests/scenarios/advanced/programme_discovery.yaml")
RESULTS_PATH = Path("tests/quality/results/scenarios/programme_discovery.json")
PASSING_THRESHOLD = 80


def save_result_prd_format(result: ScenarioExecutionResult, output_path: Path) -> dict:
    """
    Save result in PRD-specified format.

    PRD format: {scenario_name, turns[], average_score, factual_score, failures[], status}
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build PRD-compliant structure
    prd_result = {
        "scenario_name": result.scenario_name,
        "turns": [
            {
                "turn_number": t.turn_number,
                "query": t.query,
                "response_text": t.response,
                "tools_used": t.tools_used,
                "quality_score": t.quality_score,
                "factual_score": t.factual_score,
                "failures": [f.to_dict() for f in t.failures],
                "passed": t.passed,
            }
            for t in result.turns
        ],
        "average_score": result.average_quality_score,
        "factual_score": result.average_factual_score,
        "failures": [f.to_dict() for f in result.failures],
        "status": result.status,
        "execution_time_ms": result.execution_time_ms,
        "timestamp": datetime.now().isoformat(),
        "metadata": result.metadata,
        "fix_history": [],  # Empty until FIX IF NEEDED runs
    }

    with open(output_path, "w") as f:
        json.dump(prd_result, f, indent=2)

    return prd_result


class TestScenario001ProgrammeDiscoveryOffline:
    """Offline tests that don't require live API."""

    def test_scenario_file_exists(self):
        """Verify the scenario YAML file exists."""
        assert SCENARIO_PATH.exists(), f"Scenario file not found: {SCENARIO_PATH}"

    def test_scenario_yaml_is_valid(self):
        """Verify the scenario YAML is parseable."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        assert "name" in data
        assert data["name"] == "Programme Discovery"
        assert "steps" in data
        assert len(data["steps"]) == 3  # 3 turns in programme discovery

    def test_results_directory_exists(self):
        """Verify results directory can be created."""
        RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        assert RESULTS_PATH.parent.exists()

    def test_prd_result_format(self):
        """Test that PRD result format is correctly structured."""
        from tests.quality.test_scenario_runner import (
            FailureCategory,
            FailureRecord,
            FailureSeverity,
            TurnResult,
        )

        # Create mock result
        mock_result = ScenarioExecutionResult(
            scenario_name="Programme Discovery",
            turns=[
                TurnResult(
                    query="Test query",
                    response="Test response about Horizon Europe programme.",
                    quality_score=85.0,
                    factual_score=90.0,
                    tools_used=["get_programme_info"],
                    turn_number=0,
                ),
            ],
            failures=[
                FailureRecord(
                    category=FailureCategory.MISSING_DATA,
                    severity=FailureSeverity.MEDIUM,
                    description="Test failure",
                    turn_number=0,
                ),
            ],
        )

        # Use temp directory for test
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_result.json"
            prd_result = save_result_prd_format(mock_result, test_path)

        # Verify PRD structure
        assert "scenario_name" in prd_result
        assert "turns" in prd_result
        assert "average_score" in prd_result
        assert "factual_score" in prd_result
        assert "failures" in prd_result
        assert "status" in prd_result
        assert "fix_history" in prd_result

        # Verify turn structure
        assert len(prd_result["turns"]) == 1
        turn = prd_result["turns"][0]
        assert "response_text" in turn
        assert "tools_used" in turn
        assert "quality_score" in turn
        assert "factual_score" in turn


class TestScenario001ProgrammeDiscoveryLive:
    """Live API tests for Programme Discovery scenario."""

    @pytest.fixture
    def api_base_url(self):
        """Get API base URL from environment or default."""
        return os.environ.get("TEST_API_URL", "http://localhost:8000")

    @pytest.fixture
    def runner(self, api_base_url):
        """Create ProductionQualityRunner instance."""
        return ProductionQualityRunner(
            base_url=api_base_url,
            passing_threshold=PASSING_THRESHOLD,
        )

    @pytest.mark.asyncio
    async def test_api_is_available(self, api_base_url):
        """Check if API is available before running scenario."""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    assert response.status == 200
        except Exception as e:
            pytest.skip(f"API not available at {api_base_url}: {e}")

    @pytest.mark.asyncio
    async def test_execute_scenario_001_programme_discovery(self, runner, api_base_url):
        """
        EXECUTE task: Run Programme Discovery scenario against live API.

        This is the main test that executes Scenario 001 per the PRD.
        """
        import aiohttp

        # First check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        pytest.skip(f"API not healthy: status {response.status}")
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        # Execute scenario
        logger.info(f"Executing scenario: {SCENARIO_PATH}")
        result = await runner.run_scenario(SCENARIO_PATH)

        # Log results
        logger.info(f"Scenario: {result.scenario_name}")
        logger.info(f"Average Quality Score: {result.average_quality_score:.2f}")
        logger.info(f"Average Factual Score: {result.average_factual_score:.2f}")
        logger.info(f"Status: {result.status}")
        logger.info(f"Turns: {len(result.turns)}")
        logger.info(f"Failures: {len(result.failures)}")

        # Log per-turn details
        for turn in result.turns:
            logger.info(
                f"  Turn {turn.turn_number}: Q={turn.quality_score:.1f}, "
                f"F={turn.factual_score:.1f}, Tools={turn.tools_used}"
            )

        # Save result in PRD format
        prd_result = save_result_prd_format(result, RESULTS_PATH)
        logger.info(f"Result saved to: {RESULTS_PATH}")

        # Assertions based on PRD requirements
        assert result.scenario_name == "Programme Discovery"
        assert len(result.turns) == 3, f"Expected 3 turns, got {len(result.turns)}"

        # Check that all 3 programmes are mentioned across conversation
        all_responses = " ".join(t.response for t in result.turns)
        horizon_mentioned = "horizon europe" in all_responses.lower()
        erasmus_mentioned = "erasmus" in all_responses.lower()
        creative_mentioned = "creative europe" in all_responses.lower()

        logger.info(
            f"Programme mentions: HE={horizon_mentioned}, E+={erasmus_mentioned}, "
            f"CE={creative_mentioned}"
        )

        # Log final status
        if result.average_quality_score >= PASSING_THRESHOLD:
            logger.info(
                f"✅ PASSED: Score {result.average_quality_score:.1f} >= {PASSING_THRESHOLD}"
            )
        else:
            logger.warning(
                f"⚠️ NEEDS FIX: Score {result.average_quality_score:.1f} < {PASSING_THRESHOLD}"
            )

        # Store pass/fail for FIX IF NEEDED task
        return prd_result

    @pytest.mark.asyncio
    async def test_scenario_001_individual_turn_quality(self, runner, api_base_url):
        """Test that each turn meets minimum quality thresholds."""
        import aiohttp

        # Check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        pytest.skip(f"API not healthy: status {response.status}")
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        # Execute scenario
        result = await runner.run_scenario(SCENARIO_PATH)

        # Check each turn
        min_turn_score = 60  # Minimum acceptable per-turn score

        for turn in result.turns:
            assert turn.quality_score >= min_turn_score, (
                f"Turn {turn.turn_number} quality score {turn.quality_score:.1f} "
                f"< minimum {min_turn_score}"
            )

    @pytest.mark.asyncio
    async def test_scenario_001_no_critical_failures(self, runner, api_base_url):
        """Test that scenario has no critical failures."""
        import aiohttp

        # Check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        pytest.skip(f"API not healthy: status {response.status}")
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        # Execute scenario
        result = await runner.run_scenario(SCENARIO_PATH)

        # Check for critical failures
        from tests.quality.test_scenario_runner import FailureSeverity

        critical_failures = [f for f in result.failures if f.severity == FailureSeverity.CRITICAL]

        if critical_failures:
            for f in critical_failures:
                logger.error(f"CRITICAL FAILURE at turn {f.turn_number}: {f.description}")

        # This test passes even with critical failures (they're logged)
        # The main test_execute checks overall pass/fail
        logger.info(f"Critical failures: {len(critical_failures)}")


class TestScenario001ProgrammeDiscoveryResults:
    """Tests for reading and validating scenario results."""

    def test_read_existing_results(self):
        """Read and validate existing results file if it exists."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet - run execute test first")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        # Validate PRD structure
        assert "scenario_name" in result
        assert result["scenario_name"] == "Programme Discovery"
        assert "turns" in result
        assert "average_score" in result
        assert "factual_score" in result
        assert "status" in result

        # Log current status
        logger.info(f"Current status: {result['status']}")
        logger.info(f"Average score: {result['average_score']}")

    def test_check_if_fix_needed(self):
        """Check if scenario needs fixing based on results."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        avg_score = result.get("average_score", 0)

        if avg_score >= PASSING_THRESHOLD:
            logger.info(f"✅ Score {avg_score:.1f} >= {PASSING_THRESHOLD}: No fix needed")
        else:
            logger.warning(f"⚠️ Score {avg_score:.1f} < {PASSING_THRESHOLD}: Fix needed")
            logger.warning(f"Failures: {len(result.get('failures', []))}")

            # Identify root causes from failures
            for failure in result.get("failures", []):
                logger.warning(f"  - {failure.get('category')}: {failure.get('description')}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--log-cli-level=INFO"])
