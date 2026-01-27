"""
Goal Achievement Validation Tests for PHASE 2 Scenarios.

This test module validates that goal tracking works correctly for
proposal development workflow scenarios (Tasks 010-013):
- Full Proposal Journey (Task 010)
- Budget Iteration (Task 011)
- Timeline Refinement (Task 012)
- Consortium Building (Task 013)

Features:
- Runs PHASE 2 scenarios with goal tracking enabled
- Verifies goal progress is tracked correctly at each step
- Verifies completion is detected at the end
- Validates progress increases monotonically (or stays stable)
- Validates goal achievement thresholds

Usage:
    # Run all goal achievement tests
    pytest tests/test_goal_achievement_validation.py -v

    # Run specific scenario test
    pytest tests/test_goal_achievement_validation.py -k "full_proposal" -v

    # Run with live API
    TEST_API_URL=http://localhost:8000 pytest tests/test_goal_achievement_validation.py -v
"""

# isort: skip_file
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml

from tests.agents import (
    ConversationFlowAgent,
    GoalTrackingAgent,
)
from tests.agents.conversation_flow_agent import ConversationTurn

logger = logging.getLogger(__name__)

# Configuration
ADVANCED_SCENARIOS_DIR = Path(__file__).parent / "scenarios" / "advanced"
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 120.0

# PHASE 2 scenario files (proposal development workflows)
PHASE_2_SCENARIOS = [
    "full_proposal_journey.yaml",
    "budget_iteration.yaml",
    "timeline_refinement.yaml",
    "consortium_building.yaml",
]


@dataclass
class GoalTrackingResult:
    """Result of goal tracking validation for a scenario."""

    scenario_name: str
    passed: bool = True
    goal_detected: bool = False
    goal_category: str = ""
    progress_history: list[float] = field(default_factory=list)
    final_progress: float = 0.0
    completion_status: str = ""
    progress_trend: str = ""
    turns_executed: int = 0
    tools_used: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    validation_details: list[dict] = field(default_factory=list)


class GoalAchievementValidator:
    """
    Validator for goal achievement in PHASE 2 scenarios.

    Runs scenarios with goal tracking enabled and validates:
    - Goal is correctly extracted from first message
    - Progress increases across turns
    - Completion is detected appropriately
    - Progress thresholds are met
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.conversation_agent: ConversationFlowAgent | None = None
        self.goal_tracker: GoalTrackingAgent | None = None

    async def _init_agents(self):
        """Initialize agents for testing."""
        self.conversation_agent = ConversationFlowAgent(
            base_url=self.base_url,
            timeout=DEFAULT_TIMEOUT,
        )
        self.goal_tracker = GoalTrackingAgent(use_llm=True)

    async def _cleanup_agents(self):
        """Cleanup agents after test."""
        # Reset for next test
        if self.goal_tracker:
            self.goal_tracker.reset()

    def load_scenario(self, scenario_file: str) -> dict:
        """Load a scenario YAML file."""
        scenario_path = ADVANCED_SCENARIOS_DIR / scenario_file
        with open(scenario_path) as f:
            return yaml.safe_load(f)

    async def validate_scenario(self, scenario_file: str) -> GoalTrackingResult:
        """
        Run a scenario and validate goal tracking.

        Args:
            scenario_file: Name of the scenario YAML file

        Returns:
            GoalTrackingResult with validation details
        """
        await self._init_agents()
        result = GoalTrackingResult(scenario_name=scenario_file.replace(".yaml", ""))

        try:
            scenario = self.load_scenario(scenario_file)
            steps = scenario.get("steps", [])

            if not steps:
                result.errors.append("No steps found in scenario")
                result.passed = False
                return result

            logger.info(f"Running scenario: {scenario.get('name', scenario_file)}")
            logger.info(f"Steps: {len(steps)}")

            # Execute each step and track progress
            for step_index, step in enumerate(steps):
                message = step.get("message", "")
                if not message:
                    continue

                try:
                    # Send message
                    turn: ConversationTurn = await self.conversation_agent.send_message(message)
                    result.turns_executed += 1

                    # Check for errors
                    if turn.has_error:
                        result.errors.append(
                            f"Step {step_index + 1}: {turn.error or 'Unknown error'}"
                        )
                        # Continue to track progress even with errors
                        continue

                    # Track goal progress
                    progress = await self.goal_tracker.evaluate_progress(
                        query=message,
                        response=turn.response_text or "",
                        tools_used=turn.tools_used,
                    )

                    result.progress_history.append(progress.score)

                    # Collect tools used
                    if turn.tools_used:
                        result.tools_used.extend(turn.tools_used)

                    # Log progress
                    logger.debug(
                        f"Step {step_index + 1}: progress={progress.score:.2f}, "
                        f"reasoning={progress.reasoning}"
                    )

                    # Validate step-level goal_progress requirements
                    step_validations = step.get("validations", [])
                    for validation in step_validations:
                        if validation.get("type") == "goal_progress":
                            min_progress = validation.get("min_progress", 0.0)
                            step_passed = progress.score >= min_progress
                            result.validation_details.append(
                                {
                                    "step": step_index + 1,
                                    "validation": validation.get("name", "goal_progress"),
                                    "min_progress": min_progress,
                                    "actual_progress": progress.score,
                                    "passed": step_passed,
                                }
                            )
                            if not step_passed:
                                result.errors.append(
                                    f"Step {step_index + 1}: goal_progress "
                                    f"{progress.score:.2f} < {min_progress}"
                                )

                except Exception as e:
                    result.errors.append(f"Step {step_index + 1}: {str(e)}")
                    logger.exception(f"Error in step {step_index + 1}")

            # Get final goal tracking status
            goal = self.goal_tracker.get_goal()
            if goal:
                result.goal_detected = True
                result.goal_category = goal.category

            completion = self.goal_tracker.check_completion()
            result.completion_status = completion.status
            result.final_progress = completion.progress

            result.progress_trend = self.goal_tracker.get_progress_trend()

            # Deduplicate tools
            result.tools_used = list(set(result.tools_used))

            # Validate final goal_achieved requirements
            final_validations = scenario.get("final_validations", [])
            for validation in final_validations:
                if validation.get("type") == "goal_achieved":
                    min_progress = validation.get("min_progress", 0.8)
                    final_passed = completion.progress >= min_progress
                    result.validation_details.append(
                        {
                            "step": "final",
                            "validation": validation.get("name", "goal_achieved"),
                            "min_progress": min_progress,
                            "actual_progress": completion.progress,
                            "passed": final_passed,
                        }
                    )
                    if not final_passed:
                        result.errors.append(
                            f"Final: goal_achieved {completion.progress:.2f} < {min_progress}"
                        )

            # Determine overall pass/fail
            result.passed = (
                result.goal_detected and result.turns_executed > 0 and len(result.errors) == 0
            )

        except Exception as e:
            result.errors.append(f"Scenario execution error: {str(e)}")
            result.passed = False
            logger.exception(f"Error running scenario {scenario_file}")

        finally:
            await self._cleanup_agents()

        return result


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def api_base_url():
    """Get API base URL from environment or default."""
    return os.environ.get("TEST_API_URL", DEFAULT_API_URL)


@pytest.fixture
def goal_validator(api_base_url):
    """Create a goal achievement validator."""
    return GoalAchievementValidator(base_url=api_base_url)


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestGoalAchievementValidation:
    """
    Tests for goal achievement validation in PHASE 2 scenarios.

    These tests verify that:
    1. Goal tracking is properly enabled for each scenario
    2. Progress is tracked correctly at each step
    3. Completion is detected at the appropriate threshold
    4. Progress generally increases across turns
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario_file", PHASE_2_SCENARIOS)
    async def test_phase2_scenario_goal_tracking(
        self,
        scenario_file: str,
        goal_validator: GoalAchievementValidator,
    ):
        """
        Test goal tracking for a PHASE 2 scenario.

        Validates:
        - Goal is extracted from first message
        - Progress is tracked at each step
        - Final completion status is appropriate
        """
        result = await goal_validator.validate_scenario(scenario_file)

        # Log detailed results
        logger.info(
            f"\nScenario: {result.scenario_name}\n"
            f"  Goal detected: {result.goal_detected}\n"
            f"  Goal category: {result.goal_category}\n"
            f"  Turns executed: {result.turns_executed}\n"
            f"  Progress history: {[f'{p:.2f}' for p in result.progress_history]}\n"
            f"  Final progress: {result.final_progress:.2f}\n"
            f"  Completion status: {result.completion_status}\n"
            f"  Progress trend: {result.progress_trend}\n"
            f"  Tools used: {len(result.tools_used)}\n"
            f"  Errors: {len(result.errors)}"
        )

        # Print validation details
        for detail in result.validation_details:
            status = "✓" if detail["passed"] else "✗"
            logger.info(
                f"  {status} Step {detail['step']}: {detail['validation']} "
                f"({detail['actual_progress']:.2f} >= {detail['min_progress']})"
            )

        # Assert scenario passed
        assert result.passed, (
            f"Scenario '{result.scenario_name}' failed goal tracking:\n"
            f"  Errors: {result.errors}\n"
            f"  Progress: {result.progress_history}\n"
            f"  Final: {result.final_progress:.2f}"
        )

        # Verify goal was detected
        assert result.goal_detected, f"Goal not detected for scenario '{result.scenario_name}'"

        # Verify turns were executed
        assert result.turns_executed > 0, f"No turns executed for scenario '{result.scenario_name}'"

    @pytest.mark.asyncio
    async def test_goal_progress_increases(
        self,
        goal_validator: GoalAchievementValidator,
    ):
        """
        Verify that goal progress generally increases across turns.

        For proposal development workflows, progress should increase
        as the user gets closer to their goal.
        """
        for scenario_file in PHASE_2_SCENARIOS:
            result = await goal_validator.validate_scenario(scenario_file)

            if len(result.progress_history) < 2:
                continue  # Skip if not enough data

            # Check that progress increases or stays stable
            # Allow for some variance but overall trend should be positive
            first_quarter = result.progress_history[: len(result.progress_history) // 4]
            last_quarter = result.progress_history[-len(result.progress_history) // 4 :]

            if first_quarter and last_quarter:
                first_avg = sum(first_quarter) / len(first_quarter)
                last_avg = sum(last_quarter) / len(last_quarter)

                # Last quarter should be higher or equal to first quarter
                # Allow small variance (0.05) for LLM inconsistency
                assert last_avg >= first_avg - 0.05, (
                    f"Progress declined in {result.scenario_name}: "
                    f"first quarter avg={first_avg:.2f}, last quarter avg={last_avg:.2f}"
                )

    @pytest.mark.asyncio
    async def test_completion_detection(
        self,
        goal_validator: GoalAchievementValidator,
    ):
        """
        Verify that completion is correctly detected for each scenario.

        PHASE 2 scenarios should reach at least "partially_achieved" status
        by the end of the conversation.
        """
        for scenario_file in PHASE_2_SCENARIOS:
            result = await goal_validator.validate_scenario(scenario_file)

            # Completion should be detected
            valid_statuses = ["achieved", "partially_achieved", "in_progress"]
            assert result.completion_status in valid_statuses, (
                f"Unexpected completion status for {result.scenario_name}: "
                f"{result.completion_status}"
            )

            # For PHASE 2 scenarios, we expect at least partial achievement
            # since they have proper goal_progress validations
            if result.turns_executed >= 3:
                assert result.final_progress >= 0.3, (
                    f"Progress too low for {result.scenario_name}: {result.final_progress:.2f}"
                )


class TestGoalTrackingInfrastructure:
    """Tests for goal tracking infrastructure."""

    def test_phase2_scenarios_exist(self):
        """Verify all PHASE 2 scenario files exist."""
        for scenario_file in PHASE_2_SCENARIOS:
            scenario_path = ADVANCED_SCENARIOS_DIR / scenario_file
            assert scenario_path.exists(), f"PHASE 2 scenario not found: {scenario_file}"

    def test_phase2_scenarios_have_goal_validations(self):
        """Verify PHASE 2 scenarios have goal tracking validations."""
        for scenario_file in PHASE_2_SCENARIOS:
            scenario_path = ADVANCED_SCENARIOS_DIR / scenario_file
            with open(scenario_path) as f:
                scenario = yaml.safe_load(f)

            # Check for goal_progress validations in steps
            has_goal_progress = False
            for step in scenario.get("steps", []):
                for validation in step.get("validations", []):
                    if validation.get("type") == "goal_progress":
                        has_goal_progress = True
                        break

            assert has_goal_progress, f"No goal_progress validations in {scenario_file}"

            # Check for goal_achieved in final validations
            has_goal_achieved = False
            for validation in scenario.get("final_validations", []):
                if validation.get("type") == "goal_achieved":
                    has_goal_achieved = True
                    break

            assert has_goal_achieved, (
                f"No goal_achieved validation in final_validations for {scenario_file}"
            )

    @pytest.mark.asyncio
    async def test_goal_tracker_initialization(self):
        """Test that GoalTrackingAgent initializes correctly."""
        tracker = GoalTrackingAgent(use_llm=True)

        # Test goal extraction
        goal = tracker.extract_goal(
            "I want to write a proposal for hydrogen energy storage research"
        )

        assert goal is not None
        assert goal.description != ""
        assert goal.category in [
            "plan_proposal",
            "find_funding",
            "find_projects",
            "unknown",
        ]

        # Test progress evaluation
        progress = await tracker.evaluate_progress(
            query="What calls are available?",
            response="I found several funding calls for hydrogen research.",
            tools_used=["search_funding_calls"],
        )

        assert progress is not None
        assert 0.0 <= progress.score <= 1.0

        # Test completion check
        completion = tracker.check_completion()
        assert completion is not None
        assert completion.status in [
            "achieved",
            "partially_achieved",
            "in_progress",
            "not_achieved",
        ]

    @pytest.mark.asyncio
    async def test_goal_progress_metrics(self):
        """Test that metrics are correctly collected."""
        tracker = GoalTrackingAgent(use_llm=True)

        # Set goal
        tracker.set_goal("Calculate budget for a RIA project")

        # Simulate multiple turns
        await tracker.evaluate_progress(
            "Calculate budget for 3-year RIA",
            "Here's the budget breakdown: Total 3M EUR...",
            ["calculate_budget"],
        )
        await tracker.evaluate_progress(
            "Add more partners",
            "Updated budget for 7 partners: 4M EUR...",
            ["calculate_budget"],
        )

        # Get metrics
        metrics = tracker.get_metrics()

        assert metrics.goal is not None
        assert metrics.total_turns == 2
        assert len(metrics.progress_history) == 2
        assert "calculate_budget" in metrics.tools_used


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    pytest.main(
        [
            __file__,
            "-v",
            "-x",
            "--tb=short",
        ]
    )
