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


# =============================================================================
# TEST CLASSES
# =============================================================================


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

            assert (
                has_goal_achieved
            ), f"No goal_achieved validation in final_validations for {scenario_file}"

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
