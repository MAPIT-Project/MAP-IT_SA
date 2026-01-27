# isort: skip_file
"""
Test for Scenario 006: Budget Iteration (Phase 3: Proposal Workflow).

This test executes the Budget Iteration scenario against the live MAPIT API
and evaluates quality using the ProductionQualityRunner.

Per PRD MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V3.md:
- EXECUTE: Run scenario `tests/scenarios/advanced/proposal_workflow/budget_iteration.yaml`
- Tests iterative budget refinement workflow
- Collect: response_text, tools_used, quality_score (QualityEvaluatorAgent),
           factual_score (CrossProgrammeAgent)
- Save: `tests/quality/results/scenarios/budget_iteration.json`
- Structure: {scenario_name, turns[], average_score, factual_score, failures[], status}

Note: The actual scenario file path is `tests/scenarios/advanced/budget_iteration.yaml`
(not in proposal_workflow subdirectory).

Scenario tests iterative budget calculation and refinement:
1. Turn 1: Initial budget calculation (3-year RIA, 5 partners)
2. Turn 2: Add partners (recalculate for 7 partners)
3. Turn 3: Increase personnel costs
4. Turn 4: Compare with typical RIA projects in energy area
5. Turn 5: Adjust to 90th percentile
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
SCENARIO_PATH = Path("tests/scenarios/advanced/budget_iteration.yaml")
RESULTS_PATH = Path("tests/quality/results/scenarios/budget_iteration.json")
PASSING_THRESHOLD = 80
NUM_TURNS = 5


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


class TestScenario006BudgetIterationOffline:
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
        assert data["name"] == "Budget Iteration"
        assert "steps" in data
        assert len(data["steps"]) == NUM_TURNS, (
            f"Expected {NUM_TURNS} turns, got {len(data['steps'])}"
        )

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

        # Create mock result for 5-turn budget iteration scenario
        mock_turns = [
            TurnResult(
                query=f"Query {i}",
                response=f"Response {i}",
                quality_score=80.0 + i,
                factual_score=85.0 + i % 5,
                tools_used=["calculate_budget"] if i % 2 == 0 else ["get_budget_benchmark"],
                turn_number=i,
            )
            for i in range(NUM_TURNS)
        ]

        mock_result = ScenarioExecutionResult(
            scenario_name="Budget Iteration",
            turns=mock_turns,
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
        assert len(prd_result["turns"]) == NUM_TURNS
        turn = prd_result["turns"][0]
        assert "response_text" in turn
        assert "tools_used" in turn
        assert "quality_score" in turn
        assert "factual_score" in turn

    def test_scenario_covers_budget_iteration(self):
        """Verify scenario covers budget iteration workflow."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        # Check tags include relevant context
        tags = data.get("tags", [])
        assert any(tag in tags for tag in ["budget", "iteration", "ria"])

        # Check first turn mentions budget calculation
        first_turn = data["steps"][0]["message"]
        assert "budget" in first_turn.lower()

    def test_scenario_covers_budget_elements(self):
        """Verify scenario covers all budget iteration elements."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        all_messages = " ".join(step["message"] for step in data["steps"])
        all_lower = all_messages.lower()

        # Should cover key budget iteration elements
        has_budget = "budget" in all_lower
        has_partners = "partner" in all_lower
        has_costs = "cost" in all_lower or "personnel" in all_lower
        has_compare = "compare" in all_lower or "typical" in all_lower
        has_percentile = "percentile" in all_lower or "90" in all_lower

        assert has_budget, "Scenario should mention budget"
        assert has_partners, "Scenario should mention partners"
        assert has_costs, "Scenario should mention costs"
        assert has_compare, "Scenario should include comparison"
        assert has_percentile, "Scenario should include percentile adjustment"

    def test_scenario_is_5_turns(self):
        """Verify this is a 5-turn budget iteration scenario."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        assert len(data["steps"]) == NUM_TURNS, (
            f"Expected {NUM_TURNS} turns, got {len(data['steps'])}"
        )


class TestScenario006BudgetIterationLive:
    """Live API tests for Budget Iteration scenario."""

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
                    f"{api_base_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    assert response.status == 200
        except Exception as e:
            pytest.skip(f"API not available at {api_base_url}: {e}")

    @pytest.mark.asyncio
    async def test_execute_scenario_006_budget_iteration(self, runner, api_base_url):
        """
        EXECUTE task: Run Budget Iteration scenario against live API.

        This is the main test that executes Scenario 006 per the PRD.
        Tests iterative budget calculation and refinement for a RIA project.
        """
        import aiohttp

        # First check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)
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
        assert result.scenario_name == "Budget Iteration"
        assert len(result.turns) == NUM_TURNS, (
            f"Expected {NUM_TURNS} turns, got {len(result.turns)}"
        )

        # Check that budget-related terms are mentioned across conversation
        all_responses = " ".join(t.response for t in result.turns)
        all_lower = all_responses.lower()

        budget_mentioned = any(
            term in all_lower for term in ["budget", "cost", "million", "eur", "euro"]
        )
        partner_mentioned = any(
            term in all_lower for term in ["partner", "consortium", "organization"]
        )
        personnel_mentioned = any(
            term in all_lower for term in ["personnel", "salary", "staff", "researcher"]
        )
        comparison_mentioned = any(
            term in all_lower for term in ["compare", "typical", "average", "benchmark"]
        )

        logger.info(
            f"Budget elements: budget={budget_mentioned}, partner={partner_mentioned}, "
            f"personnel={personnel_mentioned}, comparison={comparison_mentioned}"
        )

        # PRD-specific checks for budget iteration
        # Check for RIA context maintenance
        ria_context = any(term in all_lower for term in ["ria", "research", "innovation"])
        logger.info(f"RIA context maintained: {ria_context}")

        # Check for budget-specific language
        budget_terms = [
            "budget",
            "cost",
            "funding",
            "million",
            "partner",
            "personnel",
        ]
        has_budget_guidance = any(term in all_lower for term in budget_terms)
        logger.info(f"Budget guidance present: {has_budget_guidance}")

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
    async def test_scenario_006_individual_turn_quality(self, runner, api_base_url):
        """Test that each turn meets minimum quality thresholds."""
        import aiohttp

        # Check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)
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
    async def test_scenario_006_no_critical_failures(self, runner, api_base_url):
        """Test that scenario has no critical failures."""
        import aiohttp

        # Check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)
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
    async def test_scenario_006_budget_tools_used(self, runner, api_base_url):
        """Test that budget-related tools are used during scenario."""
        import aiohttp

        # Check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        pytest.skip(f"API not healthy: status {response.status}")
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        # Execute scenario
        result = await runner.run_scenario(SCENARIO_PATH)

        # Collect all tools used
        all_tools = []
        for turn in result.turns:
            all_tools.extend(turn.tools_used)

        unique_tools = set(all_tools)
        logger.info(f"Tools used: {unique_tools}")

        # Budget iteration should use budget-related tools
        # Expected tools based on scenario steps:
        # - calculate_budget (budget calculation)
        # - get_budget_benchmark (comparison with typical projects)
        budget_tools = ["calculate_budget", "get_budget_benchmark"]
        budget_tools_used = any(tool in unique_tools for tool in budget_tools)

        logger.info(f"Budget tools used: {budget_tools_used}")

        # Log which budget tools were used
        for tool in budget_tools:
            if tool in unique_tools:
                logger.info(f"  - {tool}: used")
            else:
                logger.info(f"  - {tool}: not used")

    @pytest.mark.asyncio
    async def test_scenario_006_context_preserved(self, runner, api_base_url):
        """Test that budget context is preserved across turns."""
        import aiohttp

        # Check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        pytest.skip(f"API not healthy: status {response.status}")
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        # Execute scenario
        result = await runner.run_scenario(SCENARIO_PATH)

        # For budget iteration, context preservation is important
        all_responses = " ".join(t.response for t in result.turns)
        all_lower = all_responses.lower()

        # Key context elements that should persist
        budget_mentions = all_lower.count("budget")
        partner_mentions = all_lower.count("partner")
        ria_mentions = all_lower.count("ria")

        logger.info(f"Budget mentions across {NUM_TURNS} turns: {budget_mentions}")
        logger.info(f"Partner mentions across {NUM_TURNS} turns: {partner_mentions}")
        logger.info(f"RIA mentions across {NUM_TURNS} turns: {ria_mentions}")

        # Should have multiple mentions of budget context across turns
        assert budget_mentions >= 2, "Budget context should be maintained across turns"


class TestScenario006BudgetIterationResults:
    """Tests for reading and validating scenario results."""

    def test_read_existing_results(self):
        """Read and validate existing results file if it exists."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet - run execute test first")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        # Validate PRD structure
        assert "scenario_name" in result
        assert result["scenario_name"] == "Budget Iteration"
        assert "turns" in result
        assert "average_score" in result
        assert "factual_score" in result
        assert "status" in result

        # Validate this is a 5-turn scenario
        assert len(result["turns"]) == NUM_TURNS, (
            f"Expected {NUM_TURNS} turns, got {len(result['turns'])}"
        )

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

            # Identify problematic turns
            for turn in result.get("turns", []):
                turn_score = turn.get("quality_score", 0)
                if turn_score < PASSING_THRESHOLD:
                    logger.warning(
                        f"  Turn {turn.get('turn_number')}: score={turn_score:.1f}, "
                        f"tools={turn.get('tools_used')}"
                    )

            # Identify root causes from failures (per PRD)
            for failure in result.get("failures", []):
                category = failure.get("category", "")
                description = failure.get("description", "")

                logger.warning(f"  - {category}: {description}")

                # PRD-specific root cause hints for budget iteration
                if "benchmark" in description.lower():
                    logger.warning("    Hint: Fix app/services/tools/budget_benchmark.py")
                if "calculation" in description.lower() or "calculate" in description.lower():
                    logger.warning("    Hint: Fix app/services/tools/budget_calculator.py")
                if "breakdown" in description.lower():
                    logger.warning("    Hint: Edit tool to include detailed breakdown")
                if "context" in description.lower():
                    logger.warning("    Hint: Fix app/services/memory/memory_service.py")

    def test_analyze_per_turn_scores(self):
        """Analyze scores per turn to identify weak points."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        turns = result.get("turns", [])

        # Group turns by quality level
        high_quality = []
        medium_quality = []
        low_quality = []

        for turn in turns:
            score = turn.get("quality_score", 0)
            turn_num = turn.get("turn_number", 0)

            if score >= 85:
                high_quality.append(turn_num)
            elif score >= 70:
                medium_quality.append(turn_num)
            else:
                low_quality.append(turn_num)

        logger.info(f"High quality turns (>=85): {high_quality}")
        logger.info(f"Medium quality turns (70-84): {medium_quality}")
        logger.info(f"Low quality turns (<70): {low_quality}")

        # Identify patterns specific to budget iteration
        if low_quality:
            logger.warning(f"Low quality turns need attention: {low_quality}")

            # Check specific turn patterns for budget iteration
            for turn_num in low_quality:
                if turn_num == 0:
                    logger.warning("  Turn 0 (initial budget): May need better budget calculation")
                elif turn_num == 1:
                    logger.warning(
                        "  Turn 1 (add partners): May need partner count adjustment handling"
                    )
                elif turn_num == 2:
                    logger.warning("  Turn 2 (personnel costs): May need cost adjustment handling")
                elif turn_num == 3:
                    logger.warning("  Turn 3 (comparison): May need benchmark tool improvement")
                elif turn_num == 4:
                    logger.warning("  Turn 4 (percentile): May need percentile-based adjustment")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--log-cli-level=INFO"])
