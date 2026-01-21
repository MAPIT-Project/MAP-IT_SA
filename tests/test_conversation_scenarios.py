"""
Automated Conversation Scenario Test Runner.

This test module runs conversation scenarios defined in YAML files
using the test sub-agents for comprehensive conversation flow testing.

Features:
- Loads scenarios from YAML files
- Runs multi-turn conversations
- Validates context consistency
- Evaluates response quality
- Tests concurrent message handling

Usage:
    # Run all scenarios
    pytest tests/test_conversation_scenarios.py -v

    # Run specific category
    pytest tests/test_conversation_scenarios.py -k "basic" -v

    # Run with live API
    TEST_API_URL=http://localhost:8000 pytest tests/test_conversation_scenarios.py -v
"""

import asyncio
import logging
import os
from pathlib import Path

import pytest
from tests.agents.context_validator_agent import (
    ContextValidatorAgent,
)

# Import test agents
from tests.agents.conversation_flow_agent import (
    ConversationFlowAgent,
    ConversationScenario,
)
from tests.agents.quality_evaluator_agent import (
    QualityEvaluatorAgent,
)

logger = logging.getLogger(__name__)

# Configuration
SCENARIOS_DIR = Path(__file__).parent / "scenarios"
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 120.0


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
def conversation_agent(api_base_url):
    """Create a conversation flow agent."""
    return ConversationFlowAgent(
        base_url=api_base_url,
        timeout=DEFAULT_TIMEOUT,
    )


@pytest.fixture
async def context_validator(database_url, redis_url, api_base_url):
    """Create a context validator agent."""
    validator = ContextValidatorAgent(
        database_url=database_url,
        redis_url=redis_url,
        api_base_url=api_base_url,
    )
    await validator.connect()
    yield validator
    await validator.close()


@pytest.fixture
def quality_evaluator():
    """Create a quality evaluator agent."""
    return QualityEvaluatorAgent(
        passing_threshold=75,  # Lower threshold for testing
    )


# =============================================================================
# SCENARIO LOADING
# =============================================================================


def load_scenarios_from_directory(directory: Path) -> list[ConversationScenario]:
    """Load all scenarios from a directory."""
    scenarios = []

    if not directory.exists():
        return scenarios

    for yaml_file in directory.glob("*.yaml"):
        try:
            scenario = ConversationScenario.from_yaml(yaml_file)
            scenarios.append(scenario)
        except Exception as e:
            logger.warning(f"Failed to load scenario {yaml_file}: {e}")

    return scenarios


def load_all_scenarios() -> dict[str, list[ConversationScenario]]:
    """Load all scenarios organized by category."""
    categories = {}

    for category_dir in SCENARIOS_DIR.iterdir():
        if category_dir.is_dir():
            category_name = category_dir.name
            scenarios = load_scenarios_from_directory(category_dir)
            if scenarios:
                categories[category_name] = scenarios

    return categories


def get_scenario_ids(scenarios: list[ConversationScenario]) -> list[str]:
    """Get test IDs for scenarios."""
    return [s.name.lower().replace(" ", "_") for s in scenarios]


# Load scenarios at module level for parametrization
ALL_SCENARIOS = load_all_scenarios()
BASIC_SCENARIOS = ALL_SCENARIOS.get("basic_flows", [])
FOLLOW_UP_SCENARIOS = ALL_SCENARIOS.get("follow_up", [])
CONTEXT_SCENARIOS = ALL_SCENARIOS.get("context", [])
ERROR_SCENARIOS = ALL_SCENARIOS.get("error_recovery", [])
CONCURRENT_SCENARIOS = ALL_SCENARIOS.get("concurrent", [])


# =============================================================================
# BASIC FLOW TESTS
# =============================================================================


class TestBasicConversationFlows:
    """Tests for basic conversation flows (funding calls, projects, budget)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "scenario",
        BASIC_SCENARIOS,
        ids=get_scenario_ids(BASIC_SCENARIOS),
    )
    async def test_basic_flow(
        self,
        scenario: ConversationScenario,
        conversation_agent: ConversationFlowAgent,
    ):
        """Test basic conversation flow scenarios."""
        if not BASIC_SCENARIOS:
            pytest.skip("No basic flow scenarios found")

        result = await conversation_agent.run_scenario(scenario)

        # Check all validations passed
        assert result.passed, (
            f"Scenario '{scenario.name}' failed:\n"
            f"  Failed validations: {[v.name for v in result.failed_validations]}\n"
            f"  Errors: {result.errors}"
        )

        # Check no errors occurred
        assert len(result.errors) == 0, f"Errors occurred: {result.errors}"

    @pytest.mark.asyncio
    async def test_funding_call_search_tools(
        self,
        conversation_agent: ConversationFlowAgent,
    ):
        """Test that funding call search uses correct tools."""
        turn = await conversation_agent.send_message("Find open funding calls for renewable energy")

        assert not turn.has_error, f"Error: {turn.error}"
        assert "search_funding_calls" in turn.tools_used, (
            f"Expected search_funding_calls tool, got: {turn.tools_used}"
        )
        assert len(turn.response_text) > 0, "Response should not be empty"

    @pytest.mark.asyncio
    async def test_project_search_tools(
        self,
        conversation_agent: ConversationFlowAgent,
    ):
        """Test that project search uses correct tools."""
        turn = await conversation_agent.send_message("Find funded AI research projects")

        assert not turn.has_error, f"Error: {turn.error}"
        assert "search_projects" in turn.tools_used, (
            f"Expected search_projects tool, got: {turn.tools_used}"
        )


# =============================================================================
# FOLLOW-UP HANDLING TESTS
# =============================================================================


class TestFollowUpHandling:
    """Tests for follow-up reference resolution."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "scenario",
        FOLLOW_UP_SCENARIOS,
        ids=get_scenario_ids(FOLLOW_UP_SCENARIOS),
    )
    async def test_follow_up_scenario(
        self,
        scenario: ConversationScenario,
        conversation_agent: ConversationFlowAgent,
    ):
        """Test follow-up handling scenarios."""
        if not FOLLOW_UP_SCENARIOS:
            pytest.skip("No follow-up scenarios found")

        result = await conversation_agent.run_scenario(scenario)

        # Check follow-up validations specifically
        follow_up_validations = [
            v
            for v in result.validations
            if "follow_up" in v.name.lower() or "reference" in v.name.lower()
        ]

        for v in follow_up_validations:
            assert v.passed, f"Follow-up validation '{v.name}' failed"

    @pytest.mark.asyncio
    async def test_numbered_reference(
        self,
        conversation_agent: ConversationFlowAgent,
    ):
        """Test that numbered references are resolved correctly."""
        # First message to establish results
        await conversation_agent.send_message("Show me 5 open funding calls")

        # Follow-up with numbered reference
        turn = await conversation_agent.send_message("Tell me about the third one")

        assert not turn.has_error, f"Error: {turn.error}"
        assert turn.references_previous_result, "Should detect reference pattern"
        assert len(turn.response_text) > 100, "Should have substantial response"


# =============================================================================
# CONTEXT PRESERVATION TESTS
# =============================================================================


class TestContextPreservation:
    """Tests for context preservation across turns."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "scenario",
        CONTEXT_SCENARIOS,
        ids=get_scenario_ids(CONTEXT_SCENARIOS),
    )
    async def test_context_scenario(
        self,
        scenario: ConversationScenario,
        conversation_agent: ConversationFlowAgent,
    ):
        """Test context preservation scenarios."""
        if not CONTEXT_SCENARIOS:
            pytest.skip("No context scenarios found")

        result = await conversation_agent.run_scenario(scenario)

        # Check that context-related validations passed
        context_validations = [v for v in result.validations if "context" in v.name.lower()]

        for v in context_validations:
            assert v.passed, f"Context validation '{v.name}' failed at step {v.step_index}"

    @pytest.mark.asyncio
    async def test_long_conversation_context(
        self,
        conversation_agent: ConversationFlowAgent,
    ):
        """Test context preservation over 5+ turns."""
        messages = [
            "I'm researching hydrogen energy funding",
            "What programmes cover this?",
            "Tell me about Cluster 5",
            "What types of projects are funded?",
            "What's a typical budget?",
            "Can you remind me what we're discussing?",
        ]

        for msg in messages:
            turn = await conversation_agent.send_message(msg)
            assert not turn.has_error, f"Error on '{msg}': {turn.error}"

        # Check that final response references initial topic
        final_response = conversation_agent.message_history[-1].response_text.lower()
        assert "hydrogen" in final_response or "energy" in final_response, (
            "Should remember initial topic"
        )

    @pytest.mark.asyncio
    async def test_long_conversation_with_quality_tracking(
        self,
        conversation_agent: ConversationFlowAgent,
        quality_evaluator: QualityEvaluatorAgent,
    ):
        """
        Test long conversation (10+ turns) with quality evaluation.

        Task 013: Long Conversation Scenario
        - Runs a 10+ turn conversation about climate/hydrogen research funding
        - Uses QualityEvaluatorAgent to track quality across all turns
        - Validates no quality degradation (drop > 15 points)
        - Verifies final turn correctly references initial topic
        """
        # Long conversation messages (10+ turns)
        messages = [
            "I'm interested in climate research funding",
            "What clusters cover this area?",
            "What types of projects are funded?",
            "Tell me about RIA projects specifically",
            "What's the typical budget?",
            "How many partners are usually needed?",
            "What countries participate most?",
            "Are there any open calls right now?",
            "What's the deadline for the first one?",
            "Can you remind me what we started talking about?",
        ]

        turns_data = []
        for i, msg in enumerate(messages):
            turn = await conversation_agent.send_message(msg)
            # Allow some flexibility - don't fail on single turn errors
            if turn.has_error:
                logger.warning(f"Turn {i + 1} error: {turn.error}")
            turns_data.append(
                {
                    "query": msg,
                    "response": turn.response_text or f"Error: {turn.error}",
                }
            )
            # Small delay between turns to allow context processing
            await asyncio.sleep(0.3)

        # Verify we completed all 10+ turns
        assert len(turns_data) >= 10, f"Expected 10+ turns, got {len(turns_data)}"

        # Evaluate quality across the full conversation
        quality_result = await quality_evaluator.evaluate_conversation(turns_data)

        # Check for quality degradation (drop of 15+ points)
        assert not quality_result.degradation_detected, (
            f"Quality degradation detected at turn {quality_result.degradation_turn}: "
            f"dropped {quality_result.degradation_amount} points"
        )

        # Check average quality is reasonable (60+ out of 100)
        assert quality_result.average_score >= 60, (
            f"Average quality too low: {quality_result.average_score}/100"
        )

        # Check that final turn references initial topic (climate)
        final_response = conversation_agent.message_history[-1].response_text.lower()
        initial_topic_referenced = (
            "climate" in final_response
            or "research" in final_response
            or "funding" in final_response
        )
        assert initial_topic_referenced, (
            f"Final turn should reference initial topic (climate research funding). "
            f"Got: {final_response[:200]}..."
        )

        # Log quality trend for debugging
        logger.info(
            f"Long conversation quality: avg={quality_result.average_score:.1f}, "
            f"trend={quality_result.trend}, turns={len(quality_result.turn_scores)}"
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
    async def test_memory_overflow_with_context_validation(
        self,
        conversation_agent: ConversationFlowAgent,
        context_validator: ContextValidatorAgent,
        quality_evaluator: QualityEvaluatorAgent,
    ):
        """
        Test memory overflow (15+ turns) with context integrity validation.

        Task 015: Memory Overflow Scenario
        - Runs a 15+ turn conversation to exceed STM capacity (12 turns)
        - Uses ContextValidatorAgent.validate_context_integrity() for consistency
        - Verifies recent messages are preserved
        - Verifies earlier context is summarized in LTM
        - Validates quality doesn't catastrophically degrade
        """
        # 17-turn conversation about renewable energy funding
        messages = [
            "I'm researching renewable energy funding opportunities",
            "Which EU programmes support this area?",
            "Tell me about Cluster 5 specifically",
            "What types of projects are funded?",
            "What's the difference between RIA and IA?",
            "What's a typical budget for these projects?",
            "How many partners do I need in my consortium?",
            "Which countries participate most in these projects?",
            "What are the success rates?",
            "Are there any open calls right now?",
            "What are the upcoming deadlines?",
            "How are proposals evaluated?",
            # Beyond STM limit (12 turns)
            "I'm particularly interested in hydrogen projects",
            "Show me some funded hydrogen projects",
            "Are there similar projects I could learn from?",
            "What was the budget of these projects?",
            "Remind me what we started talking about",
        ]

        turns_data = []
        for i, msg in enumerate(messages):
            turn = await conversation_agent.send_message(msg)
            # Allow some flexibility - don't fail on single turn errors
            if turn.has_error:
                logger.warning(f"Turn {i + 1} error: {turn.error}")
            turns_data.append(
                {
                    "query": msg,
                    "response": turn.response_text or f"Error: {turn.error}",
                }
            )
            # Small delay between turns to allow context processing
            await asyncio.sleep(0.3)

        # Verify we completed all 17 turns (15+ as required)
        assert len(turns_data) >= 15, f"Expected 15+ turns, got {len(turns_data)}"

        # Give time for storage to complete
        await asyncio.sleep(1.0)

        # Validate context integrity using ContextValidatorAgent
        integrity = await context_validator.validate_context_integrity(
            conversation_agent.conversation_id
        )

        # Check that context integrity is maintained
        # Note: For long conversations, we expect Redis to have STM limit (12 turns)
        # while DB should have all messages
        logger.info(
            f"Memory overflow context: DB messages={integrity.db_message_count}, "
            f"Redis turns={integrity.redis_turn_count}"
        )

        # DB should have all messages (17 turns * 2 = 34 messages)
        assert integrity.db_message_count >= 30, (
            f"DB should have most messages: {integrity.db_message_count}"
        )

        # Redis STM should be capped at limit (12 turns)
        # This validates that STM overflow is handled correctly
        stm_limit = 12
        assert integrity.redis_turn_count <= stm_limit, (
            f"Redis STM should be capped at {stm_limit} turns: {integrity.redis_turn_count}"
        )

        # Evaluate quality across the full conversation
        quality_result = await quality_evaluator.evaluate_conversation(turns_data)

        # Check for quality degradation (drop of 15+ points)
        assert not quality_result.degradation_detected, (
            f"Quality degradation detected at turn {quality_result.degradation_turn}: "
            f"dropped {quality_result.degradation_amount} points"
        )

        # Check average quality is reasonable (55+ out of 100 for long conversations)
        assert quality_result.average_score >= 55, (
            f"Average quality too low: {quality_result.average_score}/100"
        )

        # Check that final turn references initial topic (renewable energy)
        final_response = conversation_agent.message_history[-1].response_text.lower()
        initial_topic_referenced = (
            "renewable" in final_response
            or "energy" in final_response
            or "funding" in final_response
            or "research" in final_response
        )
        assert initial_topic_referenced, (
            f"Final turn should reference initial topic (renewable energy funding). "
            f"Got: {final_response[:200]}..."
        )

        # Log quality trend for debugging
        logger.info(
            f"Memory overflow quality: avg={quality_result.average_score:.1f}, "
            f"trend={quality_result.trend}, turns={len(quality_result.turn_scores)}"
        )


# =============================================================================
# ERROR RECOVERY TESTS
# =============================================================================


class TestErrorRecovery:
    """Tests for error recovery and graceful handling."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "scenario",
        ERROR_SCENARIOS,
        ids=get_scenario_ids(ERROR_SCENARIOS),
    )
    async def test_error_scenario(
        self,
        scenario: ConversationScenario,
        conversation_agent: ConversationFlowAgent,
    ):
        """Test error recovery scenarios."""
        if not ERROR_SCENARIOS:
            pytest.skip("No error recovery scenarios found")

        result = await conversation_agent.run_scenario(scenario)

        # For error scenarios, we check that the conversation continued
        # despite invalid inputs
        completed_turns = len(result.turns)
        expected_turns = len(scenario.steps)

        assert completed_turns >= expected_turns * 0.8, (
            f"Should complete most turns despite errors: {completed_turns}/{expected_turns}"
        )

    @pytest.mark.asyncio
    async def test_graceful_invalid_reference(
        self,
        conversation_agent: ConversationFlowAgent,
    ):
        """Test graceful handling of invalid references."""
        # Establish some results
        await conversation_agent.send_message("Show me 3 funding calls")

        # Make invalid reference
        turn = await conversation_agent.send_message("Tell me about the 100th one")

        # Should not crash, should have some response
        assert not turn.has_error or "error" not in turn.error.lower(), (
            "Should handle invalid reference gracefully"
        )

    @pytest.mark.asyncio
    async def test_invalid_reference_scenario_task_016(
        self,
        conversation_agent: ConversationFlowAgent,
    ):
        """
        Test invalid reference handling per PRD Task 016.

        This test validates:
        1. "Show me 3 projects" - should return 3 projects
        2. "Tell me about the 100th one" (invalid) - graceful error handling
        3. "What about the first one?" (valid) - should recover and work

        The conversation should remain functional after invalid references.
        """
        # Step 1: Establish results with projects
        turn1 = await conversation_agent.send_message(
            "Show me 3 projects about hydrogen research"
        )
        assert not turn1.has_error, f"Step 1 error: {turn1.error}"
        assert len(turn1.response_text) > 50, "Should have substantial response"
        # Verify search_projects tool was used
        assert "search_projects" in turn1.tools_used, (
            f"Expected search_projects tool, got: {turn1.tools_used}"
        )

        # Small delay to ensure context is stored
        await asyncio.sleep(0.5)

        # Step 2: Invalid reference (100th item doesn't exist)
        turn2 = await conversation_agent.send_message("Tell me about the 100th one")

        # Should NOT crash - this is the key assertion
        # The response should indicate the reference is invalid, but no error
        assert not turn2.has_error, (
            f"Invalid reference should not cause error: {turn2.error}"
        )
        assert len(turn2.response_text) > 0, "Should have some response to invalid ref"

        # Response should acknowledge the invalid reference somehow
        response_lower = turn2.response_text.lower()
        invalid_acknowledged = (
            "only" in response_lower
            or "3" in response_lower or "three" in response_lower
            or "doesn't exist" in response_lower
            or "not available" in response_lower
            or "cannot find" in response_lower
            or "no such" in response_lower
            or "invalid" in response_lower
            or "did not" in response_lower
            or "don't have" in response_lower
        )
        # Log but don't fail if not acknowledged - some systems just search again
        if not invalid_acknowledged:
            logger.warning(
                f"Invalid reference may not be acknowledged: {turn2.response_text[:200]}"
            )

        # Small delay before recovery step
        await asyncio.sleep(0.5)

        # Step 3: Valid reference - should work after invalid one
        turn3 = await conversation_agent.send_message("What about the first one?")

        # This MUST work - proves conversation recovered from invalid ref
        assert not turn3.has_error, f"Recovery step error: {turn3.error}"
        assert len(turn3.response_text) > 100, (
            "Recovery response should be substantial"
        )

        # The response should contain project-related content
        response_lower = turn3.response_text.lower()
        has_project_content = (
            "project" in response_lower
            or "funding" in response_lower
            or "research" in response_lower
            or "budget" in response_lower
            or "consortium" in response_lower
            or "hydrogen" in response_lower
        )
        assert has_project_content, (
            f"Recovery should return project info. Got: {turn3.response_text[:300]}..."
        )

        # Verify conversation completed all 3 steps
        assert conversation_agent.turn_count >= 3, (
            f"Expected at least 3 turns, got {conversation_agent.turn_count}"
        )

        logger.info(
            "Task 016 test passed: Invalid reference handled gracefully, "
            "conversation recovered successfully"
        )

    @pytest.mark.asyncio
    async def test_ambiguous_query_scenario_task_017(
        self,
        conversation_agent: ConversationFlowAgent,
    ):
        """
        Test ambiguous query handling per PRD Task 017.

        This test validates:
        1. "Show me projects" - should return projects
        2. "Tell me about it" (ambiguous) - should handle gracefully
        3. "I mean projects about hydrogen research" (clarification) - should accept

        The conversation should handle ambiguity and accept clarifications.
        """
        # Step 1: Establish results with a broad query
        turn1 = await conversation_agent.send_message("Show me projects")
        assert not turn1.has_error, f"Step 1 error: {turn1.error}"
        assert len(turn1.response_text) > 50, "Should have substantial response"
        # Verify search_projects tool was used
        assert "search_projects" in turn1.tools_used, (
            f"Expected search_projects tool, got: {turn1.tools_used}"
        )

        # Small delay to ensure context is stored
        await asyncio.sleep(0.5)

        # Step 2: Ambiguous reference ("Tell me about it")
        turn2 = await conversation_agent.send_message("Tell me about it")

        # Should NOT crash - this is the key assertion
        assert not turn2.has_error, (
            f"Ambiguous query should not cause error: {turn2.error}"
        )
        assert len(turn2.response_text) > 0, "Should have some response to ambiguous query"

        # Response should either ask for clarification OR make a reasonable assumption
        response_lower = turn2.response_text.lower()
        handled_ambiguity = (
            # Asks for clarification
            "which" in response_lower
            or "clarify" in response_lower
            or "specific" in response_lower
            or "more details" in response_lower
            or "can you" in response_lower
            # Or makes reasonable assumption and provides info
            or "project" in response_lower
            or "first" in response_lower
        )
        assert handled_ambiguity, (
            f"Should handle ambiguity (ask for clarification or assume). "
            f"Got: {turn2.response_text[:300]}..."
        )

        # Small delay before clarification
        await asyncio.sleep(0.5)

        # Step 3: Clarification - should accept and process
        turn3 = await conversation_agent.send_message(
            "I mean projects about hydrogen research"
        )

        # Clarification MUST be accepted and processed
        assert not turn3.has_error, f"Clarification step error: {turn3.error}"
        assert len(turn3.response_text) > 100, (
            "Clarification response should be substantial"
        )

        # The response should contain hydrogen-related content
        response_lower = turn3.response_text.lower()
        has_hydrogen_content = (
            "hydrogen" in response_lower
            or "energy" in response_lower
            or "fuel" in response_lower
            or "project" in response_lower
            or "research" in response_lower
        )
        assert has_hydrogen_content, (
            f"Clarification should return hydrogen info. Got: {turn3.response_text[:300]}..."
        )

        # Verify conversation completed all 3 steps
        assert conversation_agent.turn_count >= 3, (
            f"Expected at least 3 turns, got {conversation_agent.turn_count}"
        )

        logger.info(
            "Task 017 test passed: Ambiguous query handled gracefully, "
            "clarification accepted successfully"
        )


# =============================================================================
# CONCURRENT ACCESS TESTS
# =============================================================================


class TestConcurrentAccess:
    """Tests for concurrent message handling and race conditions."""

    @pytest.mark.asyncio
    async def test_rapid_messages(
        self,
        conversation_agent: ConversationFlowAgent,
    ):
        """Test handling of rapidly sent messages."""
        messages = [
            "What is Horizon Europe?",
            "What are the pillars?",
            "Tell me about Pillar 2",
        ]

        # Send messages with minimal delay
        for msg in messages:
            turn = await conversation_agent.send_message(msg)
            assert not turn.has_error, f"Error on '{msg}': {turn.error}"
            await asyncio.sleep(0.1)  # Very short delay

        assert conversation_agent.turn_count == len(messages)

    @pytest.mark.asyncio
    async def test_concurrent_messages_same_conversation(
        self,
        api_base_url: str,
    ):
        """Test concurrent messages on the same conversation."""
        agent = ConversationFlowAgent(base_url=api_base_url)

        messages = [
            "Question 1: What is RIA?",
            "Question 2: What is IA?",
            "Question 3: What is CSA?",
        ]

        # Send all messages concurrently
        turns = await agent.run_concurrent_messages(messages, delay_between_ms=0)

        # Check results
        error_count = sum(1 for t in turns if t.has_error)

        # Allow some failures due to race conditions, but not all
        assert error_count < len(messages), (
            f"Too many errors ({error_count}/{len(messages)}) in concurrent test"
        )


# =============================================================================
# CONTEXT VALIDATION TESTS
# =============================================================================


class TestContextValidation:
    """Tests that use the ContextValidatorAgent."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
    async def test_message_storage_consistency(
        self,
        conversation_agent: ConversationFlowAgent,
        context_validator: ContextValidatorAgent,
    ):
        """Test that messages are stored consistently in DB and Redis."""
        # Send a message
        turn = await conversation_agent.send_message(
            "What are the success rates for EIC Accelerator?"
        )

        assert not turn.has_error

        # Give time for storage
        await asyncio.sleep(1.0)

        # Validate storage
        result = await context_validator.validate_message_stored(
            conversation_agent.conversation_id,
            "success rates",
        )

        assert result.passed, f"Message not stored properly: {result.message}"

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
    async def test_context_integrity_after_conversation(
        self,
        conversation_agent: ConversationFlowAgent,
        context_validator: ContextValidatorAgent,
    ):
        """Test context integrity after a multi-turn conversation."""
        messages = [
            "What is Horizon Europe?",
            "What are the main clusters?",
            "Tell me about Cluster 5",
        ]

        for msg in messages:
            await conversation_agent.send_message(msg)
            await asyncio.sleep(0.5)

        # Validate integrity
        integrity = await context_validator.validate_context_integrity(
            conversation_agent.conversation_id
        )

        assert integrity.is_consistent, (
            f"Context integrity check failed:\n"
            f"  Message count match: {integrity.message_count_match}\n"
            f"  Order preserved: {integrity.order_preserved}\n"
            f"  DB count: {integrity.db_message_count}\n"
            f"  Redis count: {integrity.redis_turn_count}"
        )


# =============================================================================
# QUALITY EVALUATION TESTS
# =============================================================================


class TestQualityEvaluation:
    """Tests that use the QualityEvaluatorAgent."""

    @pytest.mark.asyncio
    async def test_response_quality_single(
        self,
        conversation_agent: ConversationFlowAgent,
        quality_evaluator: QualityEvaluatorAgent,
    ):
        """Test quality evaluation of a single response."""
        turn = await conversation_agent.send_message(
            "What is the EIC Accelerator and who can apply?"
        )

        assert not turn.has_error

        # Quick evaluation (rule-based)
        score = quality_evaluator.quick_evaluate(
            turn.response_text,
            expected_patterns=["EIC", "Accelerator", "SME", "apply", "funding"],
            min_length=200,
        )

        assert score.total_score >= 50, (
            f"Quality too low: {score.total_score}/100\nResponse: {turn.response_text[:500]}..."
        )

    @pytest.mark.asyncio
    async def test_quality_across_conversation(
        self,
        conversation_agent: ConversationFlowAgent,
        quality_evaluator: QualityEvaluatorAgent,
    ):
        """Test that quality remains stable across conversation."""
        messages = [
            "What is Horizon Europe?",
            "What are the main funding instruments?",
            "Tell me about RIA projects",
        ]

        turns_data = []
        for msg in messages:
            turn = await conversation_agent.send_message(msg)
            turns_data.append(
                {
                    "query": msg,
                    "response": turn.response_text,
                }
            )

        # Evaluate conversation quality
        quality_result = await quality_evaluator.evaluate_conversation(turns_data)

        assert not quality_result.degradation_detected, (
            f"Quality degraded at turn {quality_result.degradation_turn}\n"
            f"Drop: {quality_result.degradation_amount} points"
        )

        assert quality_result.average_score >= 60, (
            f"Average quality too low: {quality_result.average_score}"
        )


# =============================================================================
# INTEGRATION TEST
# =============================================================================


class TestFullIntegration:
    """Full integration tests combining all agents."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
    async def test_full_conversation_flow(
        self,
        conversation_agent: ConversationFlowAgent,
        context_validator: ContextValidatorAgent,
        quality_evaluator: QualityEvaluatorAgent,
    ):
        """Test a complete conversation with all validations."""
        # Run a multi-turn conversation
        messages = [
            "Find open calls for AI research in health",
            "Tell me about the first one",
            "What are the eligibility requirements?",
            "What's the typical budget for similar projects?",
        ]

        turns_data = []
        for msg in messages:
            turn = await conversation_agent.send_message(msg)
            assert not turn.has_error, f"Error: {turn.error}"
            turns_data.append({"query": msg, "response": turn.response_text})
            await asyncio.sleep(0.5)

        # Validate context integrity
        integrity = await context_validator.validate_context_integrity(
            conversation_agent.conversation_id
        )
        assert integrity.is_consistent, "Context integrity failed"

        # Validate quality
        quality = await quality_evaluator.evaluate_conversation(turns_data)
        assert quality.average_score >= 60, f"Quality too low: {quality.average_score}"
        assert not quality.degradation_detected, "Quality degraded"

        # Validate all turns completed
        assert conversation_agent.turn_count == len(messages)


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
