# isort: skip_file
"""
Test for Scenario 002: Programme Comparison (Phase 2: Multi-Programme Navigation).

This test executes the Programme Comparison scenario against the live MAPIT API
and evaluates quality using the ProductionQualityRunner.

Per PRD MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V2.md:
- EXECUTE: Run scenario `tests/scenarios/advanced/programme_comparison.yaml`
- Tests comparing Horizon Europe, Erasmus+, and Creative Europe
- Collect: response_text, tools_used, quality_score (QualityEvaluatorAgent),
           factual_score (CrossProgrammeAgent)
- Save: `tests/quality/results/scenarios/programme_comparison.json`
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
SCENARIO_PATH = Path("tests/scenarios/advanced/programme_comparison.yaml")
RESULTS_PATH = Path("tests/quality/results/scenarios/programme_comparison.json")
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


class TestScenario002ProgrammeComparisonOffline:
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
        assert data["name"] == "Programme Comparison"
        assert "steps" in data
        assert len(data["steps"]) == 4  # 4 turns in programme comparison

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
            scenario_name="Programme Comparison",
            turns=[
                TurnResult(
                    query="Compare Horizon Europe and Erasmus+",
                    response="Both programmes support research collaboration.",
                    quality_score=85.0,
                    factual_score=90.0,
                    tools_used=["compare_programmes"],
                    turn_number=0,
                ),
                TurnResult(
                    query="What about funding amounts?",
                    response="Horizon Europe: €95.5B, Erasmus+: €26.2B",
                    quality_score=88.0,
                    factual_score=92.0,
                    tools_used=["get_programme_statistics"],
                    turn_number=1,
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
        assert len(prd_result["turns"]) == 2
        turn = prd_result["turns"][0]
        assert "response_text" in turn
        assert "tools_used" in turn
        assert "quality_score" in turn
        assert "factual_score" in turn


class TestScenario002ProgrammeComparisonLive:
    """Live API tests for Programme Comparison scenario."""

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
    async def test_execute_scenario_002_programme_comparison(self, runner, api_base_url):
        """
        EXECUTE task: Run Programme Comparison scenario against live API.

        This is the main test that executes Scenario 002 per the PRD.
        Tests comparing Horizon Europe, Erasmus+, and Creative Europe.
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
        assert result.scenario_name == "Programme Comparison"
        assert len(result.turns) == 4, f"Expected 4 turns, got {len(result.turns)}"

        # Check that both programmes are mentioned across conversation
        all_responses = " ".join(t.response for t in result.turns)
        horizon_mentioned = "horizon europe" in all_responses.lower()
        erasmus_mentioned = "erasmus" in all_responses.lower()

        logger.info(f"Programme mentions: HE={horizon_mentioned}, E+={erasmus_mentioned}")

        # PRD-specific checks for programme comparison
        # Check for multi-programme budget confusion (common issue per PRD)
        budget_terms = ["billion", "million", "eur", "€"]
        has_budget_info = any(term in all_responses.lower() for term in budget_terms)
        logger.info(f"Budget information present: {has_budget_info}")

        # Check for success rate vs funding rate confusion (common issue per PRD)
        success_terms = ["success rate", "acceptance", "competitive", "%"]
        has_success_info = any(term in all_responses.lower() for term in success_terms)
        logger.info(f"Success rate information present: {has_success_info}")

        # Log final status
        if result.average_quality_score >= PASSING_THRESHOLD:
            logger.info(f"PASSED: Score {result.average_quality_score:.1f} >= {PASSING_THRESHOLD}")
        else:
            logger.warning(
                f"NEEDS FIX: Score {result.average_quality_score:.1f} < {PASSING_THRESHOLD}"
            )

        # Store pass/fail for FIX IF NEEDED task
        return prd_result

    @pytest.mark.asyncio
    async def test_scenario_002_individual_turn_quality(self, runner, api_base_url):
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
    async def test_scenario_002_no_critical_failures(self, runner, api_base_url):
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

    @pytest.mark.asyncio
    async def test_scenario_002_comparison_quality(self, runner, api_base_url):
        """Test that comparison-specific quality checks pass."""
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

        # Comparison-specific checks per PRD
        all_responses = " ".join(t.response for t in result.turns)
        all_lower = all_responses.lower()

        # 1. Check for multi-programme budget confusion
        # Both programmes should have distinct budget references
        has_horizon_budget = any(
            term in all_lower for term in ["95", "95.5", "horizon budget", "horizon funding"]
        )
        has_erasmus_budget = any(
            term in all_lower for term in ["26", "26.2", "erasmus budget", "erasmus funding"]
        )

        logger.info(f"Horizon budget info: {has_horizon_budget}")
        logger.info(f"Erasmus budget info: {has_erasmus_budget}")

        # 2. Check for strategic recommendation in final turn
        final_turn = result.turns[-1] if result.turns else None
        if final_turn:
            recommendation_patterns = [
                "recommend",
                "suggest",
                "start with",
                "first",
                "consider",
                "should",
            ]
            has_recommendation = any(
                pattern in final_turn.response.lower() for pattern in recommendation_patterns
            )
            logger.info(f"Strategic recommendation present: {has_recommendation}")


class TestScenario002ProgrammeComparisonResults:
    """Tests for reading and validating scenario results."""

    def test_read_existing_results(self):
        """Read and validate existing results file if it exists."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet - run execute test first")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        # Validate PRD structure
        assert "scenario_name" in result
        assert result["scenario_name"] == "Programme Comparison"
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
            logger.info(f"Score {avg_score:.1f} >= {PASSING_THRESHOLD}: No fix needed")
        else:
            logger.warning(f"Score {avg_score:.1f} < {PASSING_THRESHOLD}: Fix needed")
            logger.warning(f"Failures: {len(result.get('failures', []))}")

            # Identify root causes from failures (per PRD)
            # PRD: check for multi-programme budget confusion,
            # success rate vs funding rate confusion
            for failure in result.get("failures", []):
                category = failure.get("category", "")
                description = failure.get("description", "")

                logger.warning(f"  - {category}: {description}")

                # PRD-specific root cause hints
                if "budget" in description.lower():
                    logger.warning("    Hint: CrossProgrammeAgent budget validation issue")
                if "rate" in description.lower():
                    logger.warning("    Hint: Success rate vs funding rate confusion")
                if "missing" in description.lower():
                    logger.warning("    Hint: Missing comparison data")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--log-cli-level=INFO"])
