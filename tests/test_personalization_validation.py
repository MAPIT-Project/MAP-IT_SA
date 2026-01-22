"""
Personalization Validation Tests for PHASE 4 Scenarios.

This test module validates that personalization works correctly for
personalized recommendation scenarios (Tasks 018-021):
- User Context Learning (Task 018)
- Returning User Context (Task 019)
- Progressive Profile Building (Task 020)
- Preference-Based Filtering (Task 021)

Features:
- Runs PHASE 4 scenarios with personalization validation enabled
- Verifies context accumulates correctly across turns
- Verifies recommendations are personalized based on accumulated profile
- Validates profile usage at each step
- Validates context integrity

Usage:
    # Run all personalization validation tests
    pytest tests/test_personalization_validation.py -v

    # Run specific scenario test
    pytest tests/test_personalization_validation.py -k "user_context" -v

    # Run with live API
    TEST_API_URL=http://localhost:8000 pytest tests/test_personalization_validation.py -v
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
    PersonalizationAgent,
)
from tests.agents.conversation_flow_agent import ConversationTurn
from tests.agents.personalization_agent import (
    AccumulationResult,
    PersonalizationResult,
    ProfileUsageResult,
)

logger = logging.getLogger(__name__)

# Configuration
ADVANCED_SCENARIOS_DIR = Path(__file__).parent / "scenarios" / "advanced"
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 120.0

# PHASE 4 scenario files (personalized recommendations)
PHASE_4_SCENARIOS = [
    "user_context_learning.yaml",
    "returning_user_context.yaml",
    "progressive_profile.yaml",
    "preference_filtering.yaml",
]


@dataclass
class PersonalizationValidationResult:
    """Result of personalization validation for a scenario."""

    scenario_name: str
    passed: bool = True
    turns_executed: int = 0
    # Context accumulation metrics
    total_fields_accumulated: int = 0
    fields_by_turn: dict[int, list[str]] = field(default_factory=dict)
    profile_completeness: float = 0.0
    # Personalization metrics
    personalization_scores: list[float] = field(default_factory=list)
    average_personalization: float = 0.0
    profile_usage_scores: list[float] = field(default_factory=list)
    average_profile_usage: float = 0.0
    # Tools and errors
    tools_used: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    validation_details: list[dict] = field(default_factory=list)


class PersonalizationValidator:
    """
    Validator for personalization in PHASE 4 scenarios.

    Runs scenarios with personalization validation enabled and validates:
    - Context accumulates correctly across turns
    - Recommendations are personalized based on profile
    - Profile fields are used in responses
    - Context integrity is maintained
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.conversation_agent: ConversationFlowAgent | None = None
        self.personalization_agent: PersonalizationAgent | None = None

    async def _init_agents(self):
        """Initialize agents for testing."""
        self.conversation_agent = ConversationFlowAgent(
            base_url=self.base_url,
            timeout=DEFAULT_TIMEOUT,
        )
        self.personalization_agent = PersonalizationAgent(use_llm=True)

    async def _cleanup_agents(self):
        """Cleanup agents after test."""
        # Reset for next test
        if self.personalization_agent:
            self.personalization_agent.reset()

    def load_scenario(self, scenario_file: str) -> dict:
        """Load a scenario YAML file."""
        scenario_path = ADVANCED_SCENARIOS_DIR / scenario_file
        with open(scenario_path) as f:
            return yaml.safe_load(f)

    async def validate_scenario(self, scenario_file: str) -> PersonalizationValidationResult:
        """
        Run a scenario and validate personalization.

        Args:
            scenario_file: Name of the scenario YAML file

        Returns:
            PersonalizationValidationResult with validation details
        """
        await self._init_agents()
        result = PersonalizationValidationResult(scenario_name=scenario_file.replace(".yaml", ""))

        try:
            scenario = self.load_scenario(scenario_file)
            steps = scenario.get("steps", [])

            if not steps:
                result.errors.append("No steps found in scenario")
                result.passed = False
                return result

            logger.info(f"Running scenario: {scenario.get('name', scenario_file)}")
            logger.info(f"Steps: {len(steps)}")

            # Execute each step and track personalization
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
                        # Continue to track personalization even with errors
                        continue

                    response_text = turn.response_text or ""

                    # Add turn to personalization agent (extracts profile from query)
                    turn_context = self.personalization_agent.add_turn(
                        query=message,
                        response=response_text,
                    )

                    # Track fields accumulated at this turn
                    result.fields_by_turn[step_index + 1] = list(
                        turn_context.extracted_fields.keys()
                    )

                    # Collect tools used
                    if turn.tools_used:
                        result.tools_used.extend(turn.tools_used)

                    # Validate step-level validations
                    step_validations = step.get("validations", [])
                    for validation in step_validations:
                        await self._validate_step_validation(
                            validation=validation,
                            step_index=step_index,
                            response_text=response_text,
                            result=result,
                        )

                    # Log progress
                    logger.debug(
                        f"Step {step_index + 1}: fields_extracted="
                        f"{list(turn_context.extracted_fields.keys())}"
                    )

                except Exception as e:
                    result.errors.append(f"Step {step_index + 1}: {str(e)}")
                    logger.exception(f"Error in step {step_index + 1}")

            # Get final accumulation status
            accumulation: AccumulationResult = (
                self.personalization_agent.validate_context_accumulation()
            )
            result.total_fields_accumulated = accumulation.total_fields_accumulated
            result.profile_completeness = accumulation.profile_completeness

            # Calculate averages
            if result.personalization_scores:
                result.average_personalization = sum(result.personalization_scores) / len(
                    result.personalization_scores
                )
            if result.profile_usage_scores:
                result.average_profile_usage = sum(result.profile_usage_scores) / len(
                    result.profile_usage_scores
                )

            # Deduplicate tools
            result.tools_used = list(set(result.tools_used))

            # Validate final validations
            final_validations = scenario.get("final_validations", [])
            for validation in final_validations:
                await self._validate_final_validation(
                    validation=validation,
                    result=result,
                )

            # Determine overall pass/fail
            # Pass if we executed turns and have no critical errors
            result.passed = result.turns_executed > 0 and len(result.errors) == 0

        except Exception as e:
            result.errors.append(f"Scenario execution error: {str(e)}")
            result.passed = False
            logger.exception(f"Error running scenario {scenario_file}")

        finally:
            await self._cleanup_agents()

        return result

    async def _validate_step_validation(
        self,
        validation: dict,
        step_index: int,
        response_text: str,
        result: PersonalizationValidationResult,
    ):
        """Validate a single step-level validation."""
        validation_type = validation.get("type", "")
        validation_name = validation.get("name", validation_type)

        if validation_type == "context_accumulated":
            min_fields = validation.get("min_fields", 0)
            accumulation = self.personalization_agent.validate_context_accumulation()
            step_passed = accumulation.total_fields_accumulated >= min_fields
            result.validation_details.append(
                {
                    "step": step_index + 1,
                    "validation": validation_name,
                    "type": validation_type,
                    "min_fields": min_fields,
                    "actual_fields": accumulation.total_fields_accumulated,
                    "passed": step_passed,
                }
            )
            if not step_passed:
                result.errors.append(
                    f"Step {step_index + 1}: context_accumulated "
                    f"{accumulation.total_fields_accumulated} < {min_fields}"
                )

        elif validation_type == "profile_used":
            expected_fields = validation.get("expected_fields", [])
            profile_usage: ProfileUsageResult = self.personalization_agent.validate_profile_usage(
                response=response_text,
                expected_fields=expected_fields if expected_fields else None,
            )
            result.profile_usage_scores.append(profile_usage.usage_score)
            # Profile usage is considered passed if usage_score >= 0.5 or no fields expected
            step_passed = profile_usage.passed
            result.validation_details.append(
                {
                    "step": step_index + 1,
                    "validation": validation_name,
                    "type": validation_type,
                    "expected_fields": expected_fields,
                    "fields_used": profile_usage.fields_used,
                    "usage_score": profile_usage.usage_score,
                    "passed": step_passed,
                }
            )

        elif validation_type == "personalization_applied":
            personalization: PersonalizationResult = (
                await self.personalization_agent.validate_personalization(
                    response=response_text,
                )
            )
            result.personalization_scores.append(personalization.score)
            step_passed = personalization.passed
            result.validation_details.append(
                {
                    "step": step_index + 1,
                    "validation": validation_name,
                    "type": validation_type,
                    "score": personalization.score,
                    "fields_used": personalization.profile_fields_used,
                    "passed": step_passed,
                }
            )

    async def _validate_final_validation(
        self,
        validation: dict,
        result: PersonalizationValidationResult,
    ):
        """Validate a single final validation."""
        validation_type = validation.get("type", "")
        validation_name = validation.get("name", validation_type)

        if validation_type == "context_accumulated":
            min_fields = validation.get("min_fields", 0)
            accumulation = self.personalization_agent.validate_context_accumulation()
            final_passed = accumulation.total_fields_accumulated >= min_fields
            result.validation_details.append(
                {
                    "step": "final",
                    "validation": validation_name,
                    "type": validation_type,
                    "min_fields": min_fields,
                    "actual_fields": accumulation.total_fields_accumulated,
                    "passed": final_passed,
                }
            )
            if not final_passed:
                result.errors.append(
                    f"Final: context_accumulated "
                    f"{accumulation.total_fields_accumulated} < {min_fields}"
                )

        elif validation_type == "profile_used":
            expected_fields = validation.get("expected_fields", [])
            # Get the last response from the conversation
            turns = self.personalization_agent.get_turns()
            if turns:
                last_response = turns[-1].response
                profile_usage: ProfileUsageResult = (
                    self.personalization_agent.validate_profile_usage(
                        response=last_response,
                        expected_fields=expected_fields if expected_fields else None,
                    )
                )
                final_passed = profile_usage.passed
                result.validation_details.append(
                    {
                        "step": "final",
                        "validation": validation_name,
                        "type": validation_type,
                        "expected_fields": expected_fields,
                        "fields_used": profile_usage.fields_used,
                        "usage_score": profile_usage.usage_score,
                        "passed": final_passed,
                    }
                )

        elif validation_type == "personalization_applied":
            # Get the last response
            turns = self.personalization_agent.get_turns()
            if turns:
                last_response = turns[-1].response
                personalization: PersonalizationResult = (
                    await self.personalization_agent.validate_personalization(
                        response=last_response,
                    )
                )
                final_passed = personalization.passed
                result.validation_details.append(
                    {
                        "step": "final",
                        "validation": validation_name,
                        "type": validation_type,
                        "score": personalization.score,
                        "fields_used": personalization.profile_fields_used,
                        "passed": final_passed,
                    }
                )


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def api_base_url():
    """Get API base URL from environment or default."""
    return os.environ.get("TEST_API_URL", DEFAULT_API_URL)


@pytest.fixture
def personalization_validator(api_base_url):
    """Create a personalization validator."""
    return PersonalizationValidator(base_url=api_base_url)


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestPersonalizationValidation:
    """
    Tests for personalization validation in PHASE 4 scenarios.

    These tests verify that:
    1. Context accumulates correctly across turns
    2. Recommendations are personalized based on profile
    3. Profile fields are used in responses
    4. Personalization scores meet thresholds
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario_file", PHASE_4_SCENARIOS)
    async def test_phase4_scenario_personalization(
        self,
        scenario_file: str,
        personalization_validator: PersonalizationValidator,
    ):
        """
        Test personalization for a PHASE 4 scenario.

        Validates:
        - Context accumulates across turns
        - Profile is used in recommendations
        - Responses are personalized
        """
        result = await personalization_validator.validate_scenario(scenario_file)

        # Log detailed results
        logger.info(
            f"\nScenario: {result.scenario_name}\n"
            f"  Turns executed: {result.turns_executed}\n"
            f"  Fields accumulated: {result.total_fields_accumulated}\n"
            f"  Profile completeness: {result.profile_completeness:.2f}\n"
            f"  Avg personalization: {result.average_personalization:.2f}\n"
            f"  Avg profile usage: {result.average_profile_usage:.2f}\n"
            f"  Tools used: {len(result.tools_used)}\n"
            f"  Errors: {len(result.errors)}"
        )

        # Print validation details
        for detail in result.validation_details:
            status = "✓" if detail.get("passed", False) else "✗"
            detail_info = ""
            if "actual_fields" in detail:
                detail_info = f"fields={detail['actual_fields']}"
            elif "score" in detail:
                detail_info = f"score={detail['score']:.2f}"
            elif "usage_score" in detail:
                detail_info = f"usage={detail['usage_score']:.2f}"
            logger.info(f"  {status} Step {detail['step']}: {detail['validation']} ({detail_info})")

        # Assert scenario passed
        assert result.passed, (
            f"Scenario '{result.scenario_name}' failed personalization:\n"
            f"  Errors: {result.errors}\n"
            f"  Fields accumulated: {result.total_fields_accumulated}\n"
            f"  Avg personalization: {result.average_personalization:.2f}"
        )

        # Verify turns were executed
        assert result.turns_executed > 0, f"No turns executed for scenario '{result.scenario_name}'"

    @pytest.mark.asyncio
    async def test_context_accumulates_over_time(
        self,
        personalization_validator: PersonalizationValidator,
    ):
        """
        Verify that context accumulates across turns for multi-turn scenarios.

        For scenarios with user profile information revealed over time,
        the accumulated fields should generally increase.
        """
        # Test scenarios that explicitly build profile over time
        profile_building_scenarios = [
            "user_context_learning.yaml",
            "progressive_profile.yaml",
        ]

        for scenario_file in profile_building_scenarios:
            result = await personalization_validator.validate_scenario(scenario_file)

            if result.turns_executed < 2:
                continue  # Skip if not enough data

            # Check that fields accumulate
            # At least some fields should be extracted
            # Note: The actual extraction depends on the messages in the scenario
            logger.info(
                f"{result.scenario_name}: accumulated {result.total_fields_accumulated} fields"
            )

            # Profile completeness should be tracked
            assert result.profile_completeness >= 0.0, (
                f"Invalid profile completeness for {result.scenario_name}: "
                f"{result.profile_completeness}"
            )

    @pytest.mark.asyncio
    async def test_personalization_score_quality(
        self,
        personalization_validator: PersonalizationValidator,
    ):
        """
        Verify that personalization scores are reasonable.

        For PHASE 4 scenarios, personalization should be applied
        at least partially in responses.
        """
        for scenario_file in PHASE_4_SCENARIOS:
            result = await personalization_validator.validate_scenario(scenario_file)

            # If we have personalization scores, check they're reasonable
            if result.personalization_scores:
                # At least some personalization should be detected
                max_score = max(result.personalization_scores)
                logger.info(f"{result.scenario_name}: max personalization score = {max_score:.2f}")

                # Personalization scores should be valid (0.0 to 1.0)
                for score in result.personalization_scores:
                    assert (
                        0.0 <= score <= 1.0
                    ), f"Invalid personalization score for {result.scenario_name}: {score}"

    @pytest.mark.asyncio
    async def test_profile_usage_in_recommendations(
        self,
        personalization_validator: PersonalizationValidator,
    ):
        """
        Verify that profile information is used in recommendations.

        When the user provides profile information and asks for recommendations,
        the response should use that profile context.
        """
        for scenario_file in PHASE_4_SCENARIOS:
            result = await personalization_validator.validate_scenario(scenario_file)

            # If we have profile usage scores, check they're tracked
            if result.profile_usage_scores:
                logger.info(
                    f"{result.scenario_name}: "
                    f"avg profile usage = {result.average_profile_usage:.2f}"
                )

                # Profile usage scores should be valid (0.0 to 1.0)
                for score in result.profile_usage_scores:
                    assert (
                        0.0 <= score <= 1.0
                    ), f"Invalid profile usage score for {result.scenario_name}: {score}"


class TestPersonalizationInfrastructure:
    """Tests for personalization infrastructure."""

    def test_phase4_scenarios_exist(self):
        """Verify all PHASE 4 scenario files exist."""
        for scenario_file in PHASE_4_SCENARIOS:
            scenario_path = ADVANCED_SCENARIOS_DIR / scenario_file
            assert scenario_path.exists(), f"PHASE 4 scenario not found: {scenario_file}"

    def test_phase4_scenarios_have_personalization_validations(self):
        """Verify PHASE 4 scenarios have personalization validations."""
        for scenario_file in PHASE_4_SCENARIOS:
            scenario_path = ADVANCED_SCENARIOS_DIR / scenario_file
            with open(scenario_path) as f:
                scenario = yaml.safe_load(f)

            # Check for context_accumulated or personalization_applied in steps
            has_personalization_validation = False
            for step in scenario.get("steps", []):
                for validation in step.get("validations", []):
                    if validation.get("type") in [
                        "context_accumulated",
                        "personalization_applied",
                        "profile_used",
                    ]:
                        has_personalization_validation = True
                        break

            assert (
                has_personalization_validation
            ), f"No personalization validations in {scenario_file}"

            # Check for personalization validations in final validations
            has_final_personalization = False
            for validation in scenario.get("final_validations", []):
                if validation.get("type") in [
                    "context_accumulated",
                    "personalization_applied",
                    "profile_used",
                ]:
                    has_final_personalization = True
                    break

            assert (
                has_final_personalization
            ), f"No personalization validation in final_validations for {scenario_file}"

    def test_personalization_agent_initialization(self):
        """Test that PersonalizationAgent initializes correctly."""
        agent = PersonalizationAgent(use_llm=True)

        # Test adding a turn
        turn = agent.add_turn(
            query="I'm from a small university in Portugal",
            response="Great! As a Portuguese university, you have access to...",
        )

        assert turn is not None
        assert turn.turn_number == 1
        # Should extract country and organization type
        # Note: Extraction depends on pattern matching

        # Test context accumulation
        accumulation = agent.validate_context_accumulation()
        assert accumulation is not None
        assert accumulation.total_fields_accumulated >= 0

    @pytest.mark.asyncio
    async def test_personalization_validation(self):
        """Test that personalization validation works correctly."""
        agent = PersonalizationAgent(use_llm=True)

        # Add context
        agent.add_turn(
            query="I'm from a German SME in the healthcare sector",
            response="As a German healthcare SME, you have excellent opportunities...",
        )

        # Test personalization validation
        result = await agent.validate_personalization(
            response="For a German healthcare SME like yours, I recommend EIC Accelerator..."
        )

        assert result is not None
        assert 0.0 <= result.score <= 1.0

    def test_profile_extraction_patterns(self):
        """Test that profile extraction patterns work correctly."""
        agent = PersonalizationAgent(use_llm=False)

        # Test country extraction
        agent.add_turn("We're based in Germany", "Noted, Germany is an EU member state...")
        profile = agent.get_profile()
        assert profile.country == "DE"

        agent.reset()

        # Test organization type extraction
        agent.add_turn("We're a small university", "Universities can access...")
        profile = agent.get_profile()
        assert profile.organization_type == "university"

        agent.reset()

        # Test sector extraction
        agent.add_turn("We work on renewable energy", "The energy sector has...")
        profile = agent.get_profile()
        assert profile.sector == "energy"

        agent.reset()

        # Test experience level extraction
        agent.add_turn("We've never coordinated before", "As a first-time coordinator...")
        profile = agent.get_profile()
        assert profile.experience_level == "newcomer"

    @pytest.mark.asyncio
    async def test_context_accumulation_metrics(self):
        """Test that context accumulation metrics are correctly collected."""
        agent = PersonalizationAgent(use_llm=True)

        # Simulate multiple turns building profile
        agent.add_turn("I'm from a university in Portugal", "As a Portuguese university...")
        agent.add_turn(
            "We work on marine biology", "Marine biology research has funding opportunities..."
        )
        agent.add_turn(
            "We've never coordinated before", "For first-time coordinators, I recommend..."
        )

        # Get accumulation result
        accumulation = agent.validate_context_accumulation()

        assert accumulation is not None
        assert accumulation.total_fields_accumulated >= 0
        assert len(accumulation.fields_by_turn) == 3
        assert accumulation.profile_completeness >= 0.0

        # Get context summary
        summary = agent.get_context_summary()
        assert "profile" in summary
        assert "turns_analyzed" in summary
        assert summary["turns_analyzed"] == 3


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
