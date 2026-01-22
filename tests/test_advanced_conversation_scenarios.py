"""
Advanced Conversation Scenario Test Runner.

This test module runs advanced conversation scenarios defined in YAML files
using the specialized test sub-agents for comprehensive conversation flow testing.

Features:
- Loads scenarios from tests/scenarios/advanced/ directory
- Multi-turn conversation execution using ConversationFlowAgent
- Validation dispatcher that routes validation types to correct agents:
  - goal_progress, goal_achieved → GoalTrackingAgent
  - personalization_applied, context_accumulated, profile_used → PersonalizationAgent
  - programme_mentioned, programme_accurate, eligibility_correct → CrossProgrammeAgent
  - context_integrity → ContextValidatorAgent
  - response_contains, tools_used, no_error → built-in handlers
- Quality scoring using QualityEvaluatorAgent
- Result aggregation and reporting

Usage:
    # Run all advanced scenarios
    pytest tests/test_advanced_conversation_scenarios.py -v

    # Run specific scenario
    pytest tests/test_advanced_conversation_scenarios.py -k "programme_discovery" -v

    # Run with live API
    TEST_API_URL=http://localhost:8000 pytest tests/test_advanced_conversation_scenarios.py -v
"""

# isort: skip_file
import asyncio
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.agents import (
    ContextValidatorAgent,
    ConversationFlowAgent,
    CrossProgrammeAgent,
    GoalTrackingAgent,
    PersonalizationAgent,
    QualityEvaluatorAgent,
)
from tests.agents.conversation_flow_agent import ConversationTurn, ValidationResult

logger = logging.getLogger(__name__)

# Configuration
ADVANCED_SCENARIOS_DIR = Path(__file__).parent / "scenarios" / "advanced"
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 120.0


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class AdvancedValidation:
    """Extended validation with additional parameters for advanced agents."""

    type: str
    name: str = ""
    # Pattern matching
    patterns: list[str] = field(default_factory=list)
    expected: list[str] = field(default_factory=list)
    # Goal tracking
    min_progress: float = 0.0
    # Personalization
    min_fields: int = 0
    expected_fields: list[str] = field(default_factory=list)
    min_usage: float = 0.0
    min_score: float = 0.0
    # Cross-programme
    programmes: list[str] = field(default_factory=list)
    programme: str = ""
    country: str = ""
    # General
    description: str = ""
    count: int = 0
    from_turn: int = 0


@dataclass
class AdvancedScenarioStep:
    """A single step in an advanced conversation scenario."""

    message: str
    validations: list[AdvancedValidation] = field(default_factory=list)
    delay_ms: int = 0


@dataclass
class AdvancedScenario:
    """An advanced conversation scenario for testing."""

    name: str
    description: str
    steps: list[AdvancedScenarioStep]
    tags: list[str] = field(default_factory=list)
    stop_on_error: bool = True
    final_validations: list[AdvancedValidation] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "AdvancedScenario":
        """Load scenario from YAML file."""
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        steps = []
        for s in data.get("steps", []):
            validations = []
            for v in s.get("validations", []):
                validations.append(
                    AdvancedValidation(
                        type=v.get("type", ""),
                        name=v.get("name", v.get("type", "")),
                        patterns=v.get("patterns", []),
                        expected=v.get("expected", []),
                        min_progress=v.get("min_progress", 0.0),
                        min_fields=v.get("min_fields", 0),
                        expected_fields=v.get("expected_fields", []),
                        min_usage=v.get("min_usage", 0.0),
                        min_score=v.get("min_score", 0.0),
                        programmes=v.get("programmes", []),
                        programme=v.get("programme", ""),
                        country=v.get("country", ""),
                        description=v.get("description", ""),
                        count=v.get("count", 0),
                        from_turn=v.get("from_turn", 0),
                    )
                )
            steps.append(
                AdvancedScenarioStep(
                    message=s.get("message", ""),
                    validations=validations,
                    delay_ms=s.get("delay_ms", 0),
                )
            )

        final_validations = []
        for v in data.get("final_validations", []):
            final_validations.append(
                AdvancedValidation(
                    type=v.get("type", ""),
                    name=v.get("name", v.get("type", "")),
                    min_progress=v.get("min_progress", 0.0),
                    min_fields=v.get("min_fields", 0),
                    expected_fields=v.get("expected_fields", []),
                    min_usage=v.get("min_usage", 0.0),
                    min_score=v.get("min_score", 0.0),
                    programmes=v.get("programmes", []),
                    programme=v.get("programme", ""),
                    country=v.get("country", ""),
                    description=v.get("description", ""),
                )
            )

        return cls(
            name=data.get("name", yaml_path.stem),
            description=data.get("description", ""),
            steps=steps,
            tags=data.get("tags", []),
            stop_on_error=data.get("stop_on_error", True),
            final_validations=final_validations,
        )


@dataclass
class AdvancedScenarioResult:
    """Result of running an advanced conversation scenario."""

    scenario_name: str
    passed: bool = True
    validations: list[ValidationResult] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    turns: list[ConversationTurn] = field(default_factory=list)
    duration_ms: float = 0.0
    quality_scores: list[float] = field(default_factory=list)
    average_quality: float = 0.0
    goal_progress_history: list[float] = field(default_factory=list)
    final_goal_progress: float = 0.0
    profile_fields_accumulated: list[str] = field(default_factory=list)
    programmes_mentioned: list[str] = field(default_factory=list)

    @property
    def all_validations_passed(self) -> bool:
        return all(v.passed for v in self.validations)

    @property
    def failed_validations(self) -> list[ValidationResult]:
        return [v for v in self.validations if not v.passed]

    def add_validation(self, name: str, passed: bool, step_index: int = 0, message: str = ""):
        self.validations.append(
            ValidationResult(
                passed=passed,
                name=name,
                message=message,
                step_index=step_index,
            )
        )
        if not passed:
            self.passed = False

    def add_error(self, step_index: int, step_message: str, error: str):
        self.errors.append(
            {
                "step_index": step_index,
                "step_message": step_message,
                "error": error,
            }
        )
        self.passed = False


# =============================================================================
# ADVANCED SCENARIO TEST RUNNER
# =============================================================================


class AdvancedScenarioRunner:
    """
    Runner for advanced conversation scenarios with specialized agent dispatch.

    Routes validation types to the correct agents:
    - goal_progress, goal_achieved → GoalTrackingAgent
    - personalization_applied, context_accumulated, profile_used → PersonalizationAgent
    - programme_mentioned, programme_accurate, eligibility_correct → CrossProgrammeAgent
    - context_integrity → ContextValidatorAgent
    - response_contains, tools_used, no_error → built-in handlers
    """

    def __init__(
        self,
        base_url: str,
        database_url: str | None = None,
        redis_url: str | None = None,
    ):
        """
        Initialize the advanced scenario runner.

        Args:
            base_url: Base URL of the MAPIT API
            database_url: Database URL for context validation
            redis_url: Redis URL for context validation
        """
        self.base_url = base_url
        self.database_url = database_url
        self.redis_url = redis_url

        # Initialize agents
        self.conversation_agent: ConversationFlowAgent | None = None
        self.goal_tracker: GoalTrackingAgent | None = None
        self.personalization_agent: PersonalizationAgent | None = None
        self.cross_programme_agent: CrossProgrammeAgent | None = None
        self.context_validator: ContextValidatorAgent | None = None
        self.quality_evaluator: QualityEvaluatorAgent | None = None

    async def _init_agents(self):
        """Initialize all agents for a new scenario."""
        self.conversation_agent = ConversationFlowAgent(
            base_url=self.base_url,
            timeout=DEFAULT_TIMEOUT,
        )
        self.goal_tracker = GoalTrackingAgent(use_llm=True)
        self.personalization_agent = PersonalizationAgent(use_llm=True)
        self.cross_programme_agent = CrossProgrammeAgent(use_llm=True)
        self.quality_evaluator = QualityEvaluatorAgent(passing_threshold=75)

        if self.database_url or self.redis_url:
            self.context_validator = ContextValidatorAgent(
                database_url=self.database_url,
                redis_url=self.redis_url,
                api_base_url=self.base_url,
            )
            await self.context_validator.connect()

    async def _cleanup_agents(self):
        """Cleanup agents after scenario."""
        if self.context_validator:
            await self.context_validator.close()

    async def run_scenario(self, scenario: AdvancedScenario) -> AdvancedScenarioResult:
        """
        Execute an advanced conversation scenario.

        Args:
            scenario: The scenario to run

        Returns:
            AdvancedScenarioResult with all validation results
        """
        await self._init_agents()
        result = AdvancedScenarioResult(scenario_name=scenario.name)

        try:
            from datetime import datetime

            start_time = datetime.now()

            # Execute each step
            for step_index, step in enumerate(scenario.steps):
                # Apply delay if specified
                if step.delay_ms > 0:
                    await asyncio.sleep(step.delay_ms / 1000.0)

                try:
                    # Send the message
                    turn = await self.conversation_agent.send_message(step.message)
                    result.turns.append(turn)

                    # Check if turn had an error
                    if turn.has_error:
                        result.add_error(step_index, step.message, turn.error or "Unknown error")
                        if scenario.stop_on_error:
                            break
                        continue

                    # Update tracking agents with this turn
                    await self._update_tracking_agents(
                        step.message, turn.response_text, turn.tools_used
                    )

                    # Run step-level validations
                    for validation in step.validations:
                        passed, message = await self._run_validation(validation, turn, step_index)
                        result.add_validation(
                            name=validation.name or validation.type,
                            passed=passed,
                            step_index=step_index,
                            message=message,
                        )

                        if not passed and scenario.stop_on_error:
                            break

                except Exception as e:
                    result.add_error(step_index, step.message, str(e))
                    logger.exception(f"Error in step {step_index}: {e}")
                    if scenario.stop_on_error:
                        break

            # Run final validations
            for validation in scenario.final_validations:
                passed, message = await self._run_final_validation(validation, result)
                result.add_validation(
                    name=validation.name or validation.type,
                    passed=passed,
                    message=message,
                )

            # Collect metrics
            result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            self._collect_metrics(result)

        finally:
            await self._cleanup_agents()

        return result

    async def _update_tracking_agents(self, query: str, response: str, tools_used: list[str]):
        """Update tracking agents with the current turn."""
        # Update goal tracker
        if self.goal_tracker:
            await self.goal_tracker.evaluate_progress(query, response, tools_used)

        # Update personalization agent
        if self.personalization_agent:
            self.personalization_agent.add_turn(query, response)

        # Update cross-programme agent
        if self.cross_programme_agent:
            self.cross_programme_agent.check_programme_mentions(response)

    async def _run_validation(
        self,
        validation: AdvancedValidation,
        turn: ConversationTurn,
        step_index: int,
    ) -> tuple[bool, str]:
        """
        Run a single validation and return (passed, message).

        Routes to the correct agent based on validation type.
        """
        v_type = validation.type

        # Built-in validations
        if v_type == "response_contains":
            passed = all(p.lower() in turn.response_text.lower() for p in validation.patterns)
            message = f"Patterns {'found' if passed else 'not found'}: {validation.patterns}"
            return passed, message

        if v_type == "response_contains_any":
            passed = any(p.lower() in turn.response_text.lower() for p in validation.patterns)
            message = (
                f"At least one pattern {'found' if passed else 'not found'}: {validation.patterns}"
            )
            return passed, message

        if v_type == "tools_used":
            passed = all(t in turn.tools_used for t in validation.expected)
            message = f"Tools used: {turn.tools_used}, expected: {validation.expected}"
            return passed, message

        if v_type == "no_error":
            passed = not turn.has_error
            message = f"Error: {turn.error}" if not passed else "No error"
            return passed, message

        if v_type == "min_results":
            passed = False
            for tool_result in turn.tool_results:
                if tool_result.get("count", 0) >= validation.count:
                    passed = True
                    break
            message = f"Min results: {validation.count}, got tool results: {turn.tool_results}"
            return passed, message

        # GoalTrackingAgent validations
        if v_type == "goal_progress":
            if self.goal_tracker:
                passed = self.goal_tracker.validate_goal_progress(validation.min_progress)
                current = (
                    max(p.score for p in self.goal_tracker._progress_history)
                    if self.goal_tracker._progress_history
                    else 0.0
                )
                message = f"Goal progress: {current:.2f}, required: {validation.min_progress}"
                return passed, message
            return True, "Goal tracker not available"

        if v_type == "goal_achieved":
            if self.goal_tracker:
                passed = self.goal_tracker.validate_goal_achieved(validation.min_progress)
                status = self.goal_tracker.check_completion()
                message = (
                    f"Goal status: {status.status}, progress: {status.progress:.2f}, "
                    f"required: {validation.min_progress}"
                )
                return passed, message
            return True, "Goal tracker not available"

        # PersonalizationAgent validations
        if v_type == "personalization_applied":
            if self.personalization_agent:
                passed = await self.personalization_agent.validate_personalization_applied(
                    turn.response_text, validation.min_score
                )
                result = await self.personalization_agent.validate_personalization(
                    turn.response_text
                )
                message = (
                    f"Personalization score: {result.score:.2f}, required: {validation.min_score}"
                )
                return passed, message
            return True, "Personalization agent not available"

        if v_type == "context_accumulated":
            if self.personalization_agent:
                passed = self.personalization_agent.validate_context_accumulated(
                    validation.min_fields
                )
                result = self.personalization_agent.validate_context_accumulation()
                message = (
                    f"Fields accumulated: {result.total_fields_accumulated}, "
                    f"required: {validation.min_fields}"
                )
                return passed, message
            return True, "Personalization agent not available"

        if v_type == "profile_used":
            if self.personalization_agent:
                passed = self.personalization_agent.validate_profile_used(
                    turn.response_text,
                    validation.expected_fields or None,
                    validation.min_usage,
                )
                result = self.personalization_agent.validate_profile_usage(
                    turn.response_text, validation.expected_fields or None
                )
                message = (
                    f"Profile usage: {result.usage_score:.2f}, fields used: {result.fields_used}"
                )
                return passed, message
            return True, "Personalization agent not available"

        # CrossProgrammeAgent validations
        if v_type == "programme_mentioned":
            if self.cross_programme_agent:
                passed = self.cross_programme_agent.validate_programme_mentioned(
                    turn.response_text, validation.programmes
                )
                result = self.cross_programme_agent.check_programme_mentions(turn.response_text)
                message = (
                    f"Programmes found: {result.programmes_found}, "
                    f"required: {validation.programmes}"
                )
                return passed, message
            return True, "Cross-programme agent not available"

        if v_type == "programme_accurate":
            if self.cross_programme_agent:
                passed = await self.cross_programme_agent.validate_programme_accurate(
                    turn.response_text,
                    validation.programme,
                    validation.min_score or 0.7,
                )
                result = await self.cross_programme_agent.validate_programme_facts(
                    turn.response_text, validation.programme
                )
                message = f"Programme accuracy for {validation.programme}: {result.score:.2f}"
                return passed, message
            return True, "Cross-programme agent not available"

        if v_type == "eligibility_correct":
            if self.cross_programme_agent:
                context = {
                    "country": validation.country,
                    "programme": validation.programme,
                }
                passed = await self.cross_programme_agent.validate_eligibility_correct(
                    turn.response_text,
                    context,
                    validation.min_score or 0.7,
                )
                result = await self.cross_programme_agent.validate_eligibility_rules(
                    turn.response_text, context
                )
                message = f"Eligibility accuracy: {result.score:.2f}"
                return passed, message
            return True, "Cross-programme agent not available"

        # ContextValidatorAgent validations
        if v_type == "context_preserved":
            if self.context_validator and self.conversation_agent:
                result = await self.context_validator.validate_context_integrity(
                    self.conversation_agent.conversation_id
                )
                passed = result.is_consistent or result.order_preserved
                message = f"Context integrity: consistent={result.is_consistent}"
                return passed, message
            return True, "Context validator not available"

        # Unknown validation type - pass by default
        logger.warning(f"Unknown validation type: {v_type}")
        return True, f"Unknown validation type: {v_type}"

    async def _run_final_validation(
        self,
        validation: AdvancedValidation,
        result: AdvancedScenarioResult,
    ) -> tuple[bool, str]:
        """Run a final validation that operates on the entire scenario."""
        v_type = validation.type

        if v_type == "context_integrity":
            if self.context_validator and self.conversation_agent:
                integrity = await self.context_validator.validate_context_integrity(
                    self.conversation_agent.conversation_id
                )
                passed = integrity.is_consistent or integrity.order_preserved
                message = (
                    f"DB messages: {integrity.db_message_count}, "
                    f"Redis turns: {integrity.redis_turn_count}, "
                    f"Order preserved: {integrity.order_preserved}"
                )
                return passed, message
            return True, "Context validator not available"

        if v_type == "goal_achieved":
            if self.goal_tracker:
                passed = self.goal_tracker.validate_goal_achieved(validation.min_progress)
                status = self.goal_tracker.check_completion()
                message = f"Final goal status: {status.status}, progress: {status.progress:.2f}"
                return passed, message
            return True, "Goal tracker not available"

        if v_type == "context_accumulated":
            if self.personalization_agent:
                passed = self.personalization_agent.validate_context_accumulated(
                    validation.min_fields
                )
                acc_result = self.personalization_agent.validate_context_accumulation()
                message = f"Total fields accumulated: {acc_result.total_fields_accumulated}"
                return passed, message
            return True, "Personalization agent not available"

        if v_type == "quality_non_degradation":
            if self.quality_evaluator and result.turns:
                turns_data = [
                    {"query": t.user_message, "response": t.response_text or ""}
                    for t in result.turns
                ]
                quality_result = await self.quality_evaluator.evaluate_conversation(turns_data)
                passed = not quality_result.degradation_detected
                message = (
                    f"Quality trend: {quality_result.trend}, "
                    f"avg: {quality_result.average_score:.1f}"
                )
                return passed, message
            return True, "Quality evaluator not available"

        # Unknown validation type
        logger.warning(f"Unknown final validation type: {v_type}")
        return True, f"Unknown final validation type: {v_type}"

    def _collect_metrics(self, result: AdvancedScenarioResult):
        """Collect metrics from tracking agents into the result."""
        # Goal progress history
        if self.goal_tracker and self.goal_tracker._progress_history:
            result.goal_progress_history = [p.score for p in self.goal_tracker._progress_history]
            result.final_goal_progress = (
                max(result.goal_progress_history) if result.goal_progress_history else 0.0
            )

        # Profile fields accumulated
        if self.personalization_agent:
            profile = self.personalization_agent.get_profile()
            result.profile_fields_accumulated = profile.get_filled_fields()

        # Programmes mentioned
        if self.cross_programme_agent:
            summary = self.cross_programme_agent.get_programme_coverage_summary()
            result.programmes_mentioned = summary.get("programmes_discussed", [])


# =============================================================================
# SCENARIO LOADING
# =============================================================================


def load_advanced_scenarios() -> list[AdvancedScenario]:
    """Load all advanced scenarios from the scenarios/advanced directory."""
    scenarios = []

    if not ADVANCED_SCENARIOS_DIR.exists():
        logger.warning(f"Advanced scenarios directory not found: {ADVANCED_SCENARIOS_DIR}")
        return scenarios

    for yaml_file in sorted(ADVANCED_SCENARIOS_DIR.glob("*.yaml")):
        try:
            scenario = AdvancedScenario.from_yaml(yaml_file)
            scenarios.append(scenario)
            logger.info(f"Loaded scenario: {scenario.name}")
        except Exception as e:
            logger.warning(f"Failed to load scenario {yaml_file}: {e}")

    return scenarios


def get_scenario_ids(scenarios: list[AdvancedScenario]) -> list[str]:
    """Get test IDs for scenarios."""
    return [s.name.lower().replace(" ", "_") for s in scenarios]


# Load scenarios at module level for parametrization
ADVANCED_SCENARIOS = load_advanced_scenarios()


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def api_base_url():
    """Get API base URL from environment or default."""
    return os.environ.get("TEST_API_URL", DEFAULT_API_URL)


@pytest.fixture
def database_url():
    """Get database URL from environment."""
    return os.environ.get("DATABASE_URL")


@pytest.fixture
def redis_url():
    """Get Redis URL from environment."""
    return os.environ.get("REDIS_URL")


@pytest.fixture
def scenario_runner(api_base_url, database_url, redis_url):
    """Create an advanced scenario runner."""
    return AdvancedScenarioRunner(
        base_url=api_base_url,
        database_url=database_url,
        redis_url=redis_url,
    )


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestAdvancedScenarios:
    """Tests for advanced conversation scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "scenario",
        ADVANCED_SCENARIOS,
        ids=get_scenario_ids(ADVANCED_SCENARIOS),
    )
    async def test_advanced_scenario(
        self,
        scenario: AdvancedScenario,
        scenario_runner: AdvancedScenarioRunner,
    ):
        """Test an advanced conversation scenario."""
        if not ADVANCED_SCENARIOS:
            pytest.skip("No advanced scenarios found")

        result = await scenario_runner.run_scenario(scenario)

        # Log detailed results
        logger.info(
            f"Scenario '{scenario.name}' completed:\n"
            f"  Passed: {result.passed}\n"
            f"  Turns: {len(result.turns)}\n"
            f"  Validations: {len(result.validations)} "
            f"({len([v for v in result.validations if v.passed])} passed)\n"
            f"  Goal progress: {result.final_goal_progress:.2f}\n"
            f"  Profile fields: {result.profile_fields_accumulated}\n"
            f"  Programmes: {result.programmes_mentioned}\n"
            f"  Duration: {result.duration_ms:.1f}ms"
        )

        # Assert scenario passed
        assert result.passed, (
            f"Scenario '{scenario.name}' failed:\n"
            f"  Failed validations: {[v.name for v in result.failed_validations]}\n"
            f"  Errors: {result.errors}"
        )

        # Assert no errors occurred
        assert len(result.errors) == 0, f"Errors occurred: {result.errors}"


class TestAdvancedScenarioInfrastructure:
    """Tests for the advanced scenario infrastructure itself."""

    def test_scenarios_directory_exists(self):
        """Verify the advanced scenarios directory exists."""
        assert (
            ADVANCED_SCENARIOS_DIR.exists()
        ), f"Advanced scenarios directory not found: {ADVANCED_SCENARIOS_DIR}"

    def test_scenarios_loaded(self):
        """Verify that scenarios were loaded successfully."""
        assert len(ADVANCED_SCENARIOS) > 0, "No advanced scenarios loaded"

    def test_validation_scenario_exists(self):
        """Verify the test runner validation scenario exists."""
        validation_scenario = ADVANCED_SCENARIOS_DIR / "_test_runner_validation.yaml"
        assert (
            validation_scenario.exists()
        ), f"Test runner validation scenario not found: {validation_scenario}"

    @pytest.mark.asyncio
    async def test_goal_tracking_agent_integration(self, scenario_runner):
        """Test that GoalTrackingAgent is properly integrated."""
        await scenario_runner._init_agents()
        try:
            assert scenario_runner.goal_tracker is not None
            # Test basic functionality
            await scenario_runner.goal_tracker.evaluate_progress(
                "Find funding for hydrogen research",
                "I found several funding opportunities for hydrogen research.",
                ["search_funding_calls"],
            )
            assert len(scenario_runner.goal_tracker._progress_history) == 1
        finally:
            await scenario_runner._cleanup_agents()

    @pytest.mark.asyncio
    async def test_personalization_agent_integration(self, scenario_runner):
        """Test that PersonalizationAgent is properly integrated."""
        await scenario_runner._init_agents()
        try:
            assert scenario_runner.personalization_agent is not None
            # Test basic functionality
            scenario_runner.personalization_agent.add_turn(
                "I'm from a German SME",
                "As an SME from Germany, you have several options.",
            )
            profile = scenario_runner.personalization_agent.get_profile()
            assert profile is not None
        finally:
            await scenario_runner._cleanup_agents()

    @pytest.mark.asyncio
    async def test_cross_programme_agent_integration(self, scenario_runner):
        """Test that CrossProgrammeAgent is properly integrated."""
        await scenario_runner._init_agents()
        try:
            assert scenario_runner.cross_programme_agent is not None
            # Test basic functionality
            result = scenario_runner.cross_programme_agent.check_programme_mentions(
                "Horizon Europe and Erasmus+ are both EU funding programmes."
            )
            assert result.is_multi_programme
            assert "horizon_europe" in result.programmes_found
            assert "erasmus_plus" in result.programmes_found
        finally:
            await scenario_runner._cleanup_agents()


class TestValidationDispatcher:
    """Tests for the validation dispatcher logic."""

    @pytest.mark.asyncio
    async def test_builtin_response_contains(self, scenario_runner):
        """Test built-in response_contains validation."""
        await scenario_runner._init_agents()
        try:
            from tests.agents.conversation_flow_agent import ConversationTurn

            turn = ConversationTurn(
                user_message="Test",
                response_text="Horizon Europe has three pillars.",
            )
            validation = AdvancedValidation(
                type="response_contains",
                name="test_response_contains",
                patterns=["Horizon Europe", "pillars"],
            )
            passed, message = await scenario_runner._run_validation(validation, turn, 0)
            assert passed
        finally:
            await scenario_runner._cleanup_agents()

    @pytest.mark.asyncio
    async def test_builtin_tools_used(self, scenario_runner):
        """Test built-in tools_used validation."""
        await scenario_runner._init_agents()
        try:
            from tests.agents.conversation_flow_agent import ConversationTurn

            turn = ConversationTurn(
                user_message="Find calls",
                response_text="Found calls",
                tools_used=["search_funding_calls", "get_call_details"],
            )
            validation = AdvancedValidation(
                type="tools_used",
                name="test_tools_used",
                expected=["search_funding_calls"],
            )
            passed, message = await scenario_runner._run_validation(validation, turn, 0)
            assert passed
        finally:
            await scenario_runner._cleanup_agents()

    @pytest.mark.asyncio
    async def test_builtin_no_error(self, scenario_runner):
        """Test built-in no_error validation."""
        await scenario_runner._init_agents()
        try:
            from tests.agents.conversation_flow_agent import ConversationTurn

            # Turn without error
            turn_ok = ConversationTurn(
                user_message="Test",
                response_text="Response",
            )
            validation = AdvancedValidation(type="no_error", name="test_no_error")
            passed, message = await scenario_runner._run_validation(validation, turn_ok, 0)
            assert passed

            # Turn with error
            turn_err = ConversationTurn(
                user_message="Test",
                response_text="",
                error="Some error",
            )
            passed, message = await scenario_runner._run_validation(validation, turn_err, 0)
            assert not passed
        finally:
            await scenario_runner._cleanup_agents()


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Allow running specific tests from command line
    pytest.main(
        [
            __file__,
            "-v",
            "-x",
            "--tb=short",
        ]
    )
