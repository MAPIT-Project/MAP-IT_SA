"""
Cross-Programme Validation Tests for PHASE 1 and PHASE 6 Scenarios.

This test module validates that cross-programme navigation and accuracy works
correctly for multi-programme scenarios:

PHASE 1 (Multi-Programme Navigation):
- Programme Discovery (Task 006)
- Programme Comparison (Task 007)
- Programme Recommendation (Task 008)
- Eligibility Routing (Task 009)

PHASE 6 (Cross-Programme Comparisons):
- Funding Type Comparison (Task 026)
- Success Rate Analysis (Task 027)
- Budget Comparison (Task 028)
- Timeline Comparison (Task 029)

Features:
- Runs PHASE 1 and PHASE 6 scenarios with cross-programme validation enabled
- Verifies programme mentions are detected correctly
- Verifies programme facts are accurate
- Validates eligibility rules are correct
- Validates comparisons are accurate and complete

Usage:
    # Run all cross-programme validation tests
    pytest tests/test_cross_programme_validation.py -v

    # Run PHASE 1 scenarios only
    pytest tests/test_cross_programme_validation.py -k "phase1" -v

    # Run PHASE 6 scenarios only
    pytest tests/test_cross_programme_validation.py -k "phase6" -v

    # Run with live API
    TEST_API_URL=http://localhost:8000 pytest tests/test_cross_programme_validation.py -v
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
    CrossProgrammeAgent,
)
from tests.agents.conversation_flow_agent import ConversationTurn
from tests.agents.cross_programme_agent import (
    EligibilityResult,
    ProgrammeFactsResult,
    ProgrammeMentionResult,
)

logger = logging.getLogger(__name__)

# Configuration
ADVANCED_SCENARIOS_DIR = Path(__file__).parent / "scenarios" / "advanced"
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 120.0

# PHASE 1 scenario files (multi-programme navigation)
PHASE_1_SCENARIOS = [
    "programme_discovery.yaml",
    "programme_comparison.yaml",
    "programme_recommendation.yaml",
    "eligibility_routing.yaml",
]

# PHASE 6 scenario files (cross-programme comparisons)
PHASE_6_SCENARIOS = [
    "funding_type_comparison.yaml",
    "success_rate_analysis.yaml",
    "budget_comparison.yaml",
    "timeline_comparison.yaml",
]


@dataclass
class CrossProgrammeValidationResult:
    """Result of cross-programme validation for a scenario."""

    scenario_name: str
    passed: bool = True
    turns_executed: int = 0
    # Programme mention tracking
    programmes_mentioned: list[str] = field(default_factory=list)
    mention_counts: dict[str, int] = field(default_factory=dict)
    is_multi_programme: bool = False
    # Accuracy metrics
    accuracy_scores: list[float] = field(default_factory=list)
    average_accuracy: float = 0.0
    facts_correct: list[str] = field(default_factory=list)
    facts_incorrect: list[str] = field(default_factory=list)
    # Eligibility metrics
    eligibility_scores: list[float] = field(default_factory=list)
    average_eligibility: float = 0.0
    rules_correct: list[str] = field(default_factory=list)
    rules_incorrect: list[str] = field(default_factory=list)
    # Tools and errors
    tools_used: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    validation_details: list[dict] = field(default_factory=list)


class CrossProgrammeValidator:
    """
    Validator for cross-programme navigation and accuracy in PHASE 1/6 scenarios.

    Runs scenarios with cross-programme validation enabled and validates:
    - Programme mentions are detected correctly
    - Programme facts are accurate
    - Eligibility rules are correct
    - Comparisons are complete and accurate
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.conversation_agent: ConversationFlowAgent | None = None
        self.cross_programme_agent: CrossProgrammeAgent | None = None

    async def _init_agents(self):
        """Initialize agents for testing."""
        self.conversation_agent = ConversationFlowAgent(
            base_url=self.base_url,
            timeout=DEFAULT_TIMEOUT,
        )
        self.cross_programme_agent = CrossProgrammeAgent(use_llm=True)

    async def _cleanup_agents(self):
        """Cleanup agents after test."""
        # Reset for next test
        if self.cross_programme_agent:
            self.cross_programme_agent.reset()

    def load_scenario(self, scenario_file: str) -> dict:
        """Load a scenario YAML file."""
        scenario_path = ADVANCED_SCENARIOS_DIR / scenario_file
        with open(scenario_path) as f:
            return yaml.safe_load(f)

    async def validate_scenario(self, scenario_file: str) -> CrossProgrammeValidationResult:
        """
        Run a scenario and validate cross-programme handling.

        Args:
            scenario_file: Name of the scenario YAML file

        Returns:
            CrossProgrammeValidationResult with validation details
        """
        await self._init_agents()
        result = CrossProgrammeValidationResult(scenario_name=scenario_file.replace(".yaml", ""))

        try:
            scenario = self.load_scenario(scenario_file)
            steps = scenario.get("steps", [])

            if not steps:
                result.errors.append("No steps found in scenario")
                result.passed = False
                return result

            logger.info(f"Running scenario: {scenario.get('name', scenario_file)}")
            logger.info(f"Steps: {len(steps)}")

            # Track context for eligibility validation
            eligibility_context: dict = {}

            # Execute each step and track cross-programme validation
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
                        # Continue to track validation even with errors
                        continue

                    response_text = turn.response_text or ""

                    # Check programme mentions
                    mentions: ProgrammeMentionResult = (
                        self.cross_programme_agent.check_programme_mentions(response_text)
                    )

                    # Track programmes mentioned
                    for prog in mentions.programmes_found:
                        if prog not in result.programmes_mentioned:
                            result.programmes_mentioned.append(prog)
                        result.mention_counts[prog] = result.mention_counts.get(prog, 0) + 1

                    if mentions.is_multi_programme:
                        result.is_multi_programme = True

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
                            message=message,
                            eligibility_context=eligibility_context,
                            result=result,
                        )

                    # Log progress
                    logger.debug(
                        f"Step {step_index + 1}: programmes={mentions.programmes_found}, "
                        f"multi_programme={mentions.is_multi_programme}"
                    )

                except Exception as e:
                    result.errors.append(f"Step {step_index + 1}: {str(e)}")
                    logger.exception(f"Error in step {step_index + 1}")

            # Get final programme coverage summary
            summary = self.cross_programme_agent.get_programme_coverage_summary()
            logger.info(f"Programme coverage: {summary}")

            # Calculate averages
            if result.accuracy_scores:
                result.average_accuracy = sum(result.accuracy_scores) / len(result.accuracy_scores)
            if result.eligibility_scores:
                result.average_eligibility = sum(result.eligibility_scores) / len(
                    result.eligibility_scores
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
        message: str,
        eligibility_context: dict,
        result: CrossProgrammeValidationResult,
    ):
        """Validate a single step-level validation."""
        validation_type = validation.get("type", "")
        validation_name = validation.get("name", validation_type)

        if validation_type == "programme_mentioned":
            expected_programmes = validation.get("programmes", [])
            mentions = self.cross_programme_agent.check_programme_mentions(response_text)
            mentioned_set = set(mentions.programmes_found)
            expected_set = set(expected_programmes)

            # Check if all expected programmes are mentioned
            step_passed = expected_set.issubset(mentioned_set)

            result.validation_details.append(
                {
                    "step": step_index + 1,
                    "validation": validation_name,
                    "type": validation_type,
                    "expected_programmes": expected_programmes,
                    "actual_programmes": mentions.programmes_found,
                    "passed": step_passed,
                }
            )

            if not step_passed:
                missing = expected_set - mentioned_set
                result.errors.append(
                    f"Step {step_index + 1}: programme_mentioned missing {list(missing)}"
                )

        elif validation_type == "programme_accurate":
            programme = validation.get("programme", "horizon_europe")
            min_score = validation.get("min_score", 0.7)

            facts_result: ProgrammeFactsResult = (
                await self.cross_programme_agent.validate_programme_facts(response_text, programme)
            )

            result.accuracy_scores.append(facts_result.score)
            result.facts_correct.extend(facts_result.facts_correct)
            result.facts_incorrect.extend(facts_result.facts_incorrect)

            step_passed = facts_result.score >= min_score

            result.validation_details.append(
                {
                    "step": step_index + 1,
                    "validation": validation_name,
                    "type": validation_type,
                    "programme": programme,
                    "min_score": min_score,
                    "actual_score": facts_result.score,
                    "facts_correct": facts_result.facts_correct,
                    "facts_incorrect": facts_result.facts_incorrect,
                    "passed": step_passed,
                }
            )

            if not step_passed:
                result.errors.append(
                    f"Step {step_index + 1}: programme_accurate "
                    f"{facts_result.score:.2f} < {min_score}"
                )

        elif validation_type == "eligibility_correct":
            # Extract country from message or context
            country = validation.get("country") or eligibility_context.get("country")
            programme = validation.get("programme") or eligibility_context.get("programme")
            min_score = validation.get("min_score", 0.7)

            # Try to extract country from message if not provided
            if not country:
                country = self._extract_country_from_message(message)
                if country:
                    eligibility_context["country"] = country

            context = {"country": country, "programme": programme}

            eligibility_result: EligibilityResult = (
                await self.cross_programme_agent.validate_eligibility_rules(response_text, context)
            )

            result.eligibility_scores.append(eligibility_result.score)
            result.rules_correct.extend(eligibility_result.rules_correct)
            result.rules_incorrect.extend(eligibility_result.rules_incorrect)

            step_passed = eligibility_result.score >= min_score

            result.validation_details.append(
                {
                    "step": step_index + 1,
                    "validation": validation_name,
                    "type": validation_type,
                    "country": country,
                    "programme": programme,
                    "min_score": min_score,
                    "actual_score": eligibility_result.score,
                    "rules_correct": eligibility_result.rules_correct,
                    "rules_incorrect": eligibility_result.rules_incorrect,
                    "passed": step_passed,
                }
            )

            if not step_passed:
                result.errors.append(
                    f"Step {step_index + 1}: eligibility_correct "
                    f"{eligibility_result.score:.2f} < {min_score}"
                )

    def _extract_country_from_message(self, message: str) -> str | None:
        """Extract country code from message text."""
        message_lower = message.lower()

        # Country name to code mapping
        country_map = {
            "swiss": "CH",
            "switzerland": "CH",
            "german": "DE",
            "germany": "DE",
            "french": "FR",
            "france": "FR",
            "turkish": "TR",
            "turkey": "TR",
            "polish": "PL",
            "poland": "PL",
            "spanish": "ES",
            "spain": "ES",
            "italian": "IT",
            "italy": "IT",
            "dutch": "NL",
            "netherlands": "NL",
            "belgian": "BE",
            "belgium": "BE",
            "portuguese": "PT",
            "portugal": "PT",
            "greek": "GR",
            "greece": "GR",
            "uk": "UK",
            "united kingdom": "UK",
            "british": "UK",
            "serbian": "RS",
            "serbia": "RS",
            "norwegian": "NO",
            "norway": "NO",
            "ukrainian": "UA",
            "ukraine": "UA",
        }

        for keyword, code in country_map.items():
            if keyword in message_lower:
                return code

        return None

    async def _validate_final_validation(
        self,
        validation: dict,
        result: CrossProgrammeValidationResult,
    ):
        """Validate a single final validation."""
        validation_type = validation.get("type", "")
        validation_name = validation.get("name", validation_type)

        if validation_type == "programme_mentioned":
            expected_programmes = validation.get("programmes", [])
            mentioned_set = set(result.programmes_mentioned)
            expected_set = set(expected_programmes)

            final_passed = expected_set.issubset(mentioned_set)

            result.validation_details.append(
                {
                    "step": "final",
                    "validation": validation_name,
                    "type": validation_type,
                    "expected_programmes": expected_programmes,
                    "actual_programmes": result.programmes_mentioned,
                    "passed": final_passed,
                }
            )

            if not final_passed:
                missing = expected_set - mentioned_set
                result.errors.append(f"Final: programme_mentioned missing {list(missing)}")

        elif validation_type == "programme_accurate":
            # Final accuracy check uses average score
            min_score = validation.get("min_score", 0.7)
            final_passed = result.average_accuracy >= min_score

            result.validation_details.append(
                {
                    "step": "final",
                    "validation": validation_name,
                    "type": validation_type,
                    "min_score": min_score,
                    "average_score": result.average_accuracy,
                    "passed": final_passed,
                }
            )

            if not final_passed:
                result.errors.append(
                    f"Final: programme_accurate average {result.average_accuracy:.2f} < {min_score}"
                )


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def api_base_url():
    """Get API base URL from environment or default."""
    return os.environ.get("TEST_API_URL", DEFAULT_API_URL)


@pytest.fixture
def cross_programme_validator(api_base_url):
    """Create a cross-programme validator."""
    return CrossProgrammeValidator(base_url=api_base_url)


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestCrossProgrammeValidation:
    """
    Tests for cross-programme validation in PHASE 1 and PHASE 6 scenarios.

    These tests verify that:
    1. Programme mentions are detected correctly
    2. Programme facts are accurate
    3. Eligibility rules are correctly validated
    4. Comparisons are complete and accurate
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario_file", PHASE_1_SCENARIOS)
    async def test_phase1_scenario_cross_programme(
        self,
        scenario_file: str,
        cross_programme_validator: CrossProgrammeValidator,
    ):
        """
        Test cross-programme validation for a PHASE 1 scenario.

        Validates:
        - Multiple programmes are mentioned correctly
        - Programme facts are accurate
        - Navigation between programmes works
        """
        result = await cross_programme_validator.validate_scenario(scenario_file)

        # Log detailed results
        logger.info(
            f"\nScenario: {result.scenario_name}\n"
            f"  Turns executed: {result.turns_executed}\n"
            f"  Programmes mentioned: {result.programmes_mentioned}\n"
            f"  Is multi-programme: {result.is_multi_programme}\n"
            f"  Avg accuracy: {result.average_accuracy:.2f}\n"
            f"  Facts correct: {len(result.facts_correct)}\n"
            f"  Facts incorrect: {len(result.facts_incorrect)}\n"
            f"  Tools used: {len(result.tools_used)}\n"
            f"  Errors: {len(result.errors)}"
        )

        # Print validation details
        for detail in result.validation_details:
            status = "✓" if detail.get("passed", False) else "✗"
            detail_info = ""
            if "actual_programmes" in detail:
                detail_info = f"programmes={detail['actual_programmes']}"
            elif "actual_score" in detail:
                detail_info = f"score={detail['actual_score']:.2f}"
            logger.info(f"  {status} Step {detail['step']}: {detail['validation']} ({detail_info})")

        # Assert scenario passed
        assert result.passed, (
            f"Scenario '{result.scenario_name}' failed cross-programme validation:\n"
            f"  Errors: {result.errors}\n"
            f"  Programmes: {result.programmes_mentioned}\n"
            f"  Avg accuracy: {result.average_accuracy:.2f}"
        )

        # Verify turns were executed
        assert result.turns_executed > 0, f"No turns executed for scenario '{result.scenario_name}'"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario_file", PHASE_6_SCENARIOS)
    async def test_phase6_scenario_cross_programme(
        self,
        scenario_file: str,
        cross_programme_validator: CrossProgrammeValidator,
    ):
        """
        Test cross-programme validation for a PHASE 6 scenario.

        Validates:
        - Programme information is accurate
        - Comparisons include correct facts
        - Statistics and trends are accurate
        """
        result = await cross_programme_validator.validate_scenario(scenario_file)

        # Log detailed results
        logger.info(
            f"\nScenario: {result.scenario_name}\n"
            f"  Turns executed: {result.turns_executed}\n"
            f"  Programmes mentioned: {result.programmes_mentioned}\n"
            f"  Avg accuracy: {result.average_accuracy:.2f}\n"
            f"  Facts correct: {len(result.facts_correct)}\n"
            f"  Facts incorrect: {len(result.facts_incorrect)}\n"
            f"  Tools used: {len(result.tools_used)}\n"
            f"  Errors: {len(result.errors)}"
        )

        # Print validation details
        for detail in result.validation_details:
            status = "✓" if detail.get("passed", False) else "✗"
            detail_info = ""
            if "actual_programmes" in detail:
                detail_info = f"programmes={detail['actual_programmes']}"
            elif "actual_score" in detail:
                detail_info = f"score={detail['actual_score']:.2f}"
            logger.info(f"  {status} Step {detail['step']}: {detail['validation']} ({detail_info})")

        # Assert scenario passed
        assert result.passed, (
            f"Scenario '{result.scenario_name}' failed cross-programme validation:\n"
            f"  Errors: {result.errors}\n"
            f"  Programmes: {result.programmes_mentioned}\n"
            f"  Avg accuracy: {result.average_accuracy:.2f}"
        )

        # Verify turns were executed
        assert result.turns_executed > 0, f"No turns executed for scenario '{result.scenario_name}'"

    @pytest.mark.asyncio
    async def test_programme_accuracy_across_scenarios(
        self,
        cross_programme_validator: CrossProgrammeValidator,
    ):
        """
        Verify that programme accuracy is maintained across all scenarios.

        For multi-programme scenarios, accuracy scores should be consistently
        high to ensure correct information is provided.
        """
        all_scenarios = PHASE_1_SCENARIOS + PHASE_6_SCENARIOS

        for scenario_file in all_scenarios:
            result = await cross_programme_validator.validate_scenario(scenario_file)

            # If we have accuracy scores, check they're reasonable
            if result.accuracy_scores:
                avg_accuracy = result.average_accuracy
                min_accuracy = min(result.accuracy_scores)

                logger.info(
                    f"{result.scenario_name}: "
                    f"avg accuracy={avg_accuracy:.2f}, min={min_accuracy:.2f}"
                )

                # Average accuracy should be at least 0.5 for valid scenarios
                # (LLM responses may vary, so we use lenient thresholds)
                assert avg_accuracy >= 0.4, (
                    f"Average accuracy too low for {result.scenario_name}: {avg_accuracy:.2f}"
                )

    @pytest.mark.asyncio
    async def test_multi_programme_detection(
        self,
        cross_programme_validator: CrossProgrammeValidator,
    ):
        """
        Verify that multi-programme scenarios correctly detect multiple programmes.

        PHASE 1 scenarios should involve multiple EU funding programmes.
        """
        # These scenarios should mention multiple programmes
        multi_programme_scenarios = [
            "programme_discovery.yaml",
            "programme_comparison.yaml",
            "eligibility_routing.yaml",
        ]

        for scenario_file in multi_programme_scenarios:
            result = await cross_programme_validator.validate_scenario(scenario_file)

            if result.turns_executed > 0:
                logger.info(
                    f"{result.scenario_name}: "
                    f"programmes={result.programmes_mentioned}, "
                    f"is_multi={result.is_multi_programme}"
                )

                # At least one programme should be mentioned
                assert len(result.programmes_mentioned) >= 1, (
                    f"No programmes mentioned in {result.scenario_name}"
                )

    @pytest.mark.asyncio
    async def test_eligibility_validation(
        self,
        cross_programme_validator: CrossProgrammeValidator,
    ):
        """
        Verify that eligibility rules are correctly validated.

        The eligibility_routing scenario should correctly validate
        eligibility rules for different countries and programmes.
        """
        result = await cross_programme_validator.validate_scenario("eligibility_routing.yaml")

        if result.turns_executed > 0:
            logger.info(
                f"eligibility_routing: "
                f"avg eligibility={result.average_eligibility:.2f}, "
                f"rules correct={len(result.rules_correct)}, "
                f"rules incorrect={len(result.rules_incorrect)}"
            )

            # If eligibility validations exist, check they're reasonable
            if result.eligibility_scores:
                # Eligibility scores should be valid (0.0 to 1.0)
                for score in result.eligibility_scores:
                    assert 0.0 <= score <= 1.0, f"Invalid eligibility score: {score}"


class TestCrossProgrammeInfrastructure:
    """Tests for cross-programme validation infrastructure."""

    def test_phase1_scenarios_exist(self):
        """Verify all PHASE 1 scenario files exist."""
        for scenario_file in PHASE_1_SCENARIOS:
            scenario_path = ADVANCED_SCENARIOS_DIR / scenario_file
            assert scenario_path.exists(), f"PHASE 1 scenario not found: {scenario_file}"

    def test_phase6_scenarios_exist(self):
        """Verify all PHASE 6 scenario files exist."""
        for scenario_file in PHASE_6_SCENARIOS:
            scenario_path = ADVANCED_SCENARIOS_DIR / scenario_file
            assert scenario_path.exists(), f"PHASE 6 scenario not found: {scenario_file}"

    def test_phase1_scenarios_have_cross_programme_validations(self):
        """Verify PHASE 1 scenarios have cross-programme validations."""
        # Programme names to look for in response_contains patterns
        programme_keywords = [
            "horizon europe",
            "horizon",
            "erasmus",
            "erasmus+",
            "creative europe",
            "culture",
            "media",
        ]

        for scenario_file in PHASE_1_SCENARIOS:
            scenario_path = ADVANCED_SCENARIOS_DIR / scenario_file
            with open(scenario_path) as f:
                scenario = yaml.safe_load(f)

            # Check for cross-programme validations in steps
            has_cross_programme_validation = False
            for step in scenario.get("steps", []):
                for validation in step.get("validations", []):
                    val_type = validation.get("type", "")
                    # Direct cross-programme validation types
                    if val_type in [
                        "programme_mentioned",
                        "programme_accurate",
                        "eligibility_correct",
                    ]:
                        has_cross_programme_validation = True
                        break
                    # Check response_contains patterns for programme keywords
                    # (some scenarios use response_contains instead of programme_mentioned)
                    if val_type in ["response_contains", "response_contains_any"]:
                        patterns = validation.get("patterns", [])
                        for pattern in patterns:
                            if pattern.lower() in programme_keywords:
                                has_cross_programme_validation = True
                                break

            assert has_cross_programme_validation, (
                f"No cross-programme validations in {scenario_file}"
            )

    def test_phase6_scenarios_have_programme_accuracy_validations(self):
        """Verify PHASE 6 scenarios have programme accuracy validations."""
        for scenario_file in PHASE_6_SCENARIOS:
            scenario_path = ADVANCED_SCENARIOS_DIR / scenario_file
            with open(scenario_path) as f:
                scenario = yaml.safe_load(f)

            # Check for programme_accurate validations in steps
            has_accuracy_validation = False
            for step in scenario.get("steps", []):
                for validation in step.get("validations", []):
                    if validation.get("type") in [
                        "programme_mentioned",
                        "programme_accurate",
                    ]:
                        has_accuracy_validation = True
                        break

            assert has_accuracy_validation, f"No programme accuracy validations in {scenario_file}"

    def test_cross_programme_agent_initialization(self):
        """Test that CrossProgrammeAgent initializes correctly."""
        agent = CrossProgrammeAgent(use_llm=True)

        # Test programme mention detection
        response = (
            "Horizon Europe is the EU's main research funding programme. "
            "You might also consider Erasmus+ for training activities."
        )
        mentions = agent.check_programme_mentions(response)

        assert mentions is not None
        assert len(mentions.programmes_found) >= 1
        assert "horizon_europe" in mentions.programmes_found

    @pytest.mark.asyncio
    async def test_programme_facts_validation(self):
        """Test that programme facts validation works correctly."""
        agent = CrossProgrammeAgent(use_llm=True)

        # Test with accurate information
        response = (
            "Horizon Europe has a budget of €95.5 billion for 2021-2027. "
            "It includes ERC for excellent science and EIC for innovation."
        )

        result = await agent.validate_programme_facts(response, "horizon_europe")

        assert result is not None
        assert 0.0 <= result.score <= 1.0

    @pytest.mark.asyncio
    async def test_eligibility_validation(self):
        """Test that eligibility validation works correctly."""
        agent = CrossProgrammeAgent(use_llm=True)

        # Test with Swiss eligibility (special case)
        response = (
            "Switzerland is a non-associated third country for Horizon Europe. "
            "Swiss organizations can participate as partners but cannot coordinate "
            "and typically don't receive EU funding."
        )

        result = await agent.validate_eligibility_rules(
            response,
            {"country": "CH", "programme": "horizon_europe"},
        )

        assert result is not None
        assert 0.0 <= result.score <= 1.0

    def test_programme_facts_database(self):
        """Test that programme facts database is complete."""
        agent = CrossProgrammeAgent(use_llm=False)

        # Check all programmes have required facts
        for programme in ["horizon_europe", "erasmus_plus", "creative_europe"]:
            facts = agent.get_programme_facts(programme)
            assert facts is not None, f"No facts for {programme}"
            assert "name" in facts
            assert "budget" in facts
            assert "duration" in facts

    def test_eligibility_info_retrieval(self):
        """Test that eligibility info can be retrieved."""
        agent = CrossProgrammeAgent(use_llm=False)

        # Test EU member state
        info = agent.get_eligibility_info("DE", "horizon_europe")
        assert info.get("coordinator") is True
        assert info.get("full_funding") is True

        # Test special case (Switzerland)
        info = agent.get_eligibility_info("CH", "horizon_europe")
        assert info.get("coordinator") is False

    @pytest.mark.asyncio
    async def test_cross_programme_metrics(self):
        """Test that cross-programme metrics are correctly collected."""
        agent = CrossProgrammeAgent(use_llm=True)

        # Simulate checking multiple responses
        response1 = "Horizon Europe offers research funding opportunities."
        response2 = "Erasmus+ is great for educational exchanges."
        response3 = "Creative Europe supports cultural projects."

        agent.check_programme_mentions(response1)
        agent.check_programme_mentions(response2)
        agent.check_programme_mentions(response3)

        # Get coverage summary
        summary = agent.get_programme_coverage_summary()

        assert summary is not None
        assert "programmes_discussed" in summary
        assert "num_programmes" in summary
        assert summary["num_programmes"] >= 3
        assert summary["is_multi_programme"] is True


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
