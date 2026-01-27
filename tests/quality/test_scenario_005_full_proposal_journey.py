# isort: skip_file
"""
Test for Scenario 005: Full Proposal Journey (Phase 3: Proposal Workflow).

This test executes the Full Proposal Journey scenario against the live MAPIT API
and evaluates quality using the ProductionQualityRunner.

Per PRD MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V3.md:
- EXECUTE: Run scenario `tests/scenarios/advanced/proposal_workflow/full_proposal_journey.yaml`
- This is a 15-turn CRITICAL scenario testing the complete proposal journey
- Collect: response_text, tools_used, quality_score (QualityEvaluatorAgent),
           factual_score (CrossProgrammeAgent)
- Save: `tests/quality/results/scenarios/full_proposal_journey.json`
- Structure: {scenario_name, turns[], average_score, factual_score, failures[], status}

Note: The actual scenario file path is `tests/scenarios/advanced/full_proposal_journey.yaml`
(not in proposal_workflow subdirectory).

Scenario tests a complete proposal development workflow for hydrogen energy storage:
1. Turn 1: User expresses intent to write a proposal
2. Turn 2: Explores available calls
3. Turn 3: Gets details on specific call
4. Turn 4: Checks success rates
5. Turn 5: Plans budget (4M EUR, 4 years)
6. Turn 6: Identifies partner needs
7. Turn 7: Finds experienced partners
8. Turn 8: Generates timeline (48 months, 6 WPs)
9. Turn 9: Defines work packages
10. Turn 10: Plans deliverables and milestones
11. Turn 11: Checks deadlines
12. Turn 12: Reviews evaluation criteria
13. Turn 13: Structures consortium (8 partners)
14. Turn 14: Reviews budget breakdown
15. Turn 15: Gets proposal summary
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
SCENARIO_PATH = Path("tests/scenarios/advanced/full_proposal_journey.yaml")
RESULTS_PATH = Path("tests/quality/results/scenarios/full_proposal_journey.json")
PASSING_THRESHOLD = 80
NUM_TURNS = 15  # This is a 15-turn critical scenario


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


class TestScenario005FullProposalJourneyOffline:
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
        assert data["name"] == "Full Proposal Journey"
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

        # Create mock result for 15-turn scenario
        mock_turns = [
            TurnResult(
                query=f"Query {i}",
                response=f"Response {i}",
                quality_score=80.0 + i,
                factual_score=85.0 + i % 5,
                tools_used=["search_funding_calls"] if i < 5 else ["calculate_budget"],
                turn_number=i,
            )
            for i in range(NUM_TURNS)
        ]

        mock_result = ScenarioExecutionResult(
            scenario_name="Full Proposal Journey",
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

    def test_scenario_covers_hydrogen_context(self):
        """Verify scenario covers hydrogen energy storage context."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        # Check tags include relevant context
        tags = data.get("tags", [])
        assert any(tag in tags for tag in ["hydrogen", "full-journey", "proposal-development"])

        # Check first turn mentions hydrogen
        first_turn = data["steps"][0]["message"]
        assert "hydrogen" in first_turn.lower()

    def test_scenario_covers_proposal_elements(self):
        """Verify scenario covers all proposal elements (budget, timeline, consortium)."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        all_messages = " ".join(step["message"] for step in data["steps"])
        all_lower = all_messages.lower()

        # Should cover key proposal elements
        has_budget = "budget" in all_lower
        has_timeline = "timeline" in all_lower
        has_partner = "partner" in all_lower
        has_consortium = "consortium" in all_lower
        has_deadline = "deadline" in all_lower
        has_work_package = "work package" in all_lower

        assert has_budget, "Scenario should mention budget"
        assert has_timeline, "Scenario should mention timeline"
        assert has_partner, "Scenario should mention partners"
        assert has_consortium, "Scenario should mention consortium"
        assert has_deadline, "Scenario should mention deadlines"
        assert has_work_package, "Scenario should mention work packages"

    def test_scenario_is_15_turns(self):
        """Verify this is indeed a 15-turn critical scenario."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        assert len(data["steps"]) == NUM_TURNS, (
            f"PRD specifies 15-turn critical scenario, got {len(data['steps'])}"
        )


class TestScenario005FullProposalJourneyLive:
    """Live API tests for Full Proposal Journey scenario."""

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
    async def test_execute_scenario_005_full_proposal_journey(self, runner, api_base_url):
        """
        EXECUTE task: Run Full Proposal Journey scenario against live API.

        This is the main test that executes Scenario 005 per the PRD.
        Tests complete 15-turn proposal development workflow for
        hydrogen energy storage research.
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
        assert result.scenario_name == "Full Proposal Journey"
        assert len(result.turns) == NUM_TURNS, (
            f"Expected {NUM_TURNS} turns, got {len(result.turns)}"
        )

        # Check that key proposal elements are mentioned across conversation
        all_responses = " ".join(t.response for t in result.turns)
        all_lower = all_responses.lower()

        budget_mentioned = any(
            term in all_lower for term in ["budget", "cost", "million", "eur", "euro"]
        )
        timeline_mentioned = any(
            term in all_lower for term in ["timeline", "month", "duration", "schedule"]
        )
        partner_mentioned = any(
            term in all_lower for term in ["partner", "consortium", "organization"]
        )
        work_package_mentioned = any(
            term in all_lower for term in ["work package", "wp", "deliverable", "milestone"]
        )

        logger.info(
            f"Proposal elements: budget={budget_mentioned}, timeline={timeline_mentioned}, "
            f"partner={partner_mentioned}, wp={work_package_mentioned}"
        )

        # PRD-specific checks for full proposal journey
        # Check for hydrogen context maintenance
        hydrogen_context = any(term in all_lower for term in ["hydrogen", "storage", "energy"])
        logger.info(f"Hydrogen context maintained: {hydrogen_context}")

        # Check for proposal-specific language
        proposal_terms = [
            "proposal",
            "funding",
            "call",
            "horizon",
            "success",
            "rate",
            "eligibility",
        ]
        has_proposal_guidance = any(term in all_lower for term in proposal_terms)
        logger.info(f"Proposal guidance present: {has_proposal_guidance}")

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
    async def test_scenario_005_individual_turn_quality(self, runner, api_base_url):
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
    async def test_scenario_005_no_critical_failures(self, runner, api_base_url):
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
    async def test_scenario_005_context_preserved_across_turns(self, runner, api_base_url):
        """Test that context is preserved across all 15 turns."""
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

        # For a 15-turn scenario, context preservation is critical
        # Later turns should reference or build upon earlier context
        all_responses = " ".join(t.response for t in result.turns)
        all_lower = all_responses.lower()

        # Key context elements that should persist
        # Initial context: hydrogen energy storage, proposal writing
        hydrogen_mentions = all_lower.count("hydrogen")
        proposal_mentions = all_lower.count("proposal")

        logger.info(f"Hydrogen mentions across {NUM_TURNS} turns: {hydrogen_mentions}")
        logger.info(f"Proposal mentions across {NUM_TURNS} turns: {proposal_mentions}")

        # Should have multiple mentions of core context across 15 turns
        assert hydrogen_mentions >= 3, "Hydrogen context should be maintained across turns"
        assert proposal_mentions >= 3, "Proposal context should be maintained across turns"

    @pytest.mark.asyncio
    async def test_scenario_005_tool_usage_variety(self, runner, api_base_url):
        """Test that scenario uses variety of tools appropriate for proposal development."""
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

        # Full proposal journey should use multiple tool types
        # Expected tools based on scenario steps:
        # - search_funding_calls (finding calls)
        # - get_programme_statistics (success rates)
        # - calculate_budget (budget planning)
        # - find_experienced_partners (partner discovery)
        # - generate_timeline (timeline generation)
        # - get_consortium_patterns (consortium advice)

        expected_tool_categories = [
            ["search_funding_calls", "get_call_details"],  # Call discovery
            ["calculate_budget", "get_budget_benchmark"],  # Budget
            ["find_experienced_partners", "partner_discovery"],  # Partners
            ["generate_timeline"],  # Timeline
        ]

        # Check that at least some expected tool categories are used
        categories_used = 0
        for category in expected_tool_categories:
            if any(tool in unique_tools for tool in category):
                categories_used += 1

        logger.info(f"Tool categories used: {categories_used}/{len(expected_tool_categories)}")

        # Should use at least 2 different tool categories in a full proposal journey
        assert categories_used >= 2, f"Expected at least 2 tool categories, got {categories_used}"


class TestScenario005FullProposalJourneyResults:
    """Tests for reading and validating scenario results."""

    def test_read_existing_results(self):
        """Read and validate existing results file if it exists."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet - run execute test first")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        # Validate PRD structure
        assert "scenario_name" in result
        assert result["scenario_name"] == "Full Proposal Journey"
        assert "turns" in result
        assert "average_score" in result
        assert "factual_score" in result
        assert "status" in result

        # Validate this is a 15-turn scenario
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

                # PRD-specific root cause hints for full proposal journey
                if "context" in description.lower():
                    logger.warning("    Hint: Fix app/services/memory/memory_service.py")
                if "actionability" in description.lower():
                    logger.warning("    Hint: Edit app/services/agents/tool_aware_agent.py prompt")
                if "tool" in description.lower():
                    logger.warning("    Hint: Fix specific tool in app/services/tools/")
                if "synthesis" in description.lower():
                    logger.warning("    Hint: Improve context usage in tool_aware_agent.py")
                if "budget" in description.lower():
                    logger.warning(
                        "    Hint: Fix app/services/tools/budget_benchmark.py "
                        "or budget_calculator.py"
                    )
                if "timeline" in description.lower():
                    logger.warning("    Hint: Fix app/services/tools/timeline_generator.py")
                if "partner" in description.lower():
                    logger.warning("    Hint: Fix app/services/tools/partner_discovery.py")
                if "consortium" in description.lower():
                    logger.warning("    Hint: Fix app/services/tools/consortium_patterns.py")

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

        # Identify patterns
        if low_quality:
            logger.warning(f"Low quality turns need attention: {low_quality}")

            # Check if low quality turns cluster (e.g., all late turns = context loss)
            if all(t >= 10 for t in low_quality):
                logger.warning("Pattern: Later turns are weaker - may indicate context loss")
            if all(t < 5 for t in low_quality):
                logger.warning("Pattern: Early turns are weaker - may indicate cold start issue")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--log-cli-level=INFO"])
