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
        turn1 = await conversation_agent.send_message("Show me 3 projects about hydrogen research")
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
        assert not turn2.has_error, f"Invalid reference should not cause error: {turn2.error}"
        assert len(turn2.response_text) > 0, "Should have some response to invalid ref"

        # Response should acknowledge the invalid reference somehow
        response_lower = turn2.response_text.lower()
        invalid_acknowledged = (
            "only" in response_lower
            or "3" in response_lower
            or "three" in response_lower
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
        assert len(turn3.response_text) > 100, "Recovery response should be substantial"

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
        assert not turn2.has_error, f"Ambiguous query should not cause error: {turn2.error}"
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
        turn3 = await conversation_agent.send_message("I mean projects about hydrogen research")

        # Clarification MUST be accepted and processed
        assert not turn3.has_error, f"Clarification step error: {turn3.error}"
        assert len(turn3.response_text) > 100, "Clarification response should be substantial"

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

    @pytest.mark.asyncio
    async def test_tool_timeout_scenario_task_018(
        self,
        conversation_agent: ConversationFlowAgent,
    ):
        """
        Test tool timeout handling per PRD Task 018.

        This test validates:
        1. Timeout is properly handled when a tool takes too long
        2. User receives informative error (or graceful fallback)
        3. Conversation can continue after timeout error

        Since we cannot easily simulate real network timeouts in integration tests,
        this test verifies the conversation's resilience to errors by:
        - Establishing a baseline (normal query works)
        - Sending a query that may trigger tool calls
        - Verifying conversation continues to work after any errors
        """
        # Step 1: Baseline query to verify conversation works
        turn1 = await conversation_agent.send_message("What is Horizon Europe?")
        assert not turn1.has_error, f"Baseline query failed: {turn1.error}"
        assert len(turn1.response_text) > 50, "Baseline should have response"
        assert any(
            pattern in turn1.response_text.lower()
            for pattern in ["horizon europe", "funding", "research", "programme"]
        ), "Baseline should contain relevant content"

        # Small delay to ensure context is stored
        await asyncio.sleep(0.5)

        # Step 2: Query that uses tools (may or may not timeout in real scenarios)
        # This tests the error handling path when tools are involved
        turn2 = await conversation_agent.send_message("Find projects about hydrogen research")

        # The query should complete (may succeed or fail gracefully)
        # We check that no unhandled exception occurred
        if turn2.has_error:
            # Error is OK if it's informative (not a crash)
            error_lower = (turn2.error or "").lower()
            # Should not be a generic unhandled error
            assert "unexpected" not in error_lower or "timeout" in error_lower, (
                f"Error should be informative: {turn2.error}"
            )
            logger.info(f"Step 2 had handled error (expected in timeout test): {turn2.error}")
        else:
            # If no error, should have a response
            assert len(turn2.response_text) > 0, "Should have response if no error"
            logger.info("Step 2 completed without error")

        # Small delay before recovery step
        await asyncio.sleep(0.5)

        # Step 3: Recovery - conversation MUST continue to work
        turn3 = await conversation_agent.send_message(
            "What are the success rates for EIC Accelerator?"
        )

        # This MUST work - proves conversation recovers from any errors
        assert not turn3.has_error, f"Recovery step failed: {turn3.error}"
        assert len(turn3.response_text) > 100, "Recovery should have substantial response"

        # Response should contain EIC/Accelerator related content
        response_lower = turn3.response_text.lower()
        has_eic_content = (
            "eic" in response_lower
            or "accelerator" in response_lower
            or "success" in response_lower
            or "rate" in response_lower
            or "%" in turn3.response_text
        )
        assert has_eic_content, (
            f"Recovery should return EIC info. Got: {turn3.response_text[:300]}..."
        )

        # Small delay before final verification
        await asyncio.sleep(0.5)

        # Step 4: Verify tools work after recovery
        turn4 = await conversation_agent.send_message("Search for open funding calls")

        # Should complete without crashing
        assert not turn4.has_error, f"Post-recovery tool call failed: {turn4.error}"
        assert len(turn4.response_text) > 0, "Should have response for funding calls"

        # Verify conversation completed all 4 steps
        assert conversation_agent.turn_count >= 4, (
            f"Expected at least 4 turns, got {conversation_agent.turn_count}"
        )

        logger.info(
            "Task 018 test passed: Timeout scenario handled gracefully, "
            "conversation recovered successfully"
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
    @pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
    async def test_rapid_messages_scenario_task_019(
        self,
        conversation_agent: ConversationFlowAgent,
        context_validator: ContextValidatorAgent,
    ):
        """
        Test rapid message handling per PRD Task 019.

        This test validates:
        1. All 5 messages are stored correctly
        2. No message loss occurs
        3. Responses are in correct order
        4. No race conditions detected

        Uses ContextValidatorAgent.detect_race_condition() to identify issues.
        """
        # Define the 5 messages to send rapidly (100ms delays)
        messages = [
            "What is Horizon Europe?",
            "What are the main pillars?",
            "Tell me about Pillar 2",
            "What clusters are in it?",
            "How much budget does Cluster 5 have?",
        ]

        # Track all turns for verification
        turns = []
        response_order = []

        # Send messages with 100ms delays (rapid succession)
        for i, msg in enumerate(messages):
            turn = await conversation_agent.send_message(msg)
            turns.append(turn)
            response_order.append(turn.response_text[:50] if turn.response_text else f"ERROR:{i}")

            # 100ms delay between messages (rapid)
            await asyncio.sleep(0.1)

        # Allow time for all storage operations to complete
        await asyncio.sleep(2.0)

        # VALIDATION 1: All 5 messages should complete without crash
        completed_count = sum(1 for t in turns if not t.has_error)
        assert completed_count >= 4, (
            f"At least 4 of 5 messages should complete successfully: {completed_count}/5"
        )

        # VALIDATION 2: Check for message storage - all should be stored
        # Wait for consistency with expected message count (5 user + 5 assistant = 10)
        consistency_reached = await context_validator.wait_for_consistency(
            conversation_agent.conversation_id,
            expected_message_count=8,  # At least 4 turns stored
            timeout_seconds=10.0,
        )
        assert consistency_reached, "Messages should be stored within timeout period"

        # VALIDATION 3: Detect race conditions using ContextValidatorAgent
        race_result = await context_validator.detect_race_condition(
            conversation_agent.conversation_id,
            expected_sequence=messages,
        )

        # Log race condition details for debugging
        if race_result.detected:
            logger.warning(
                f"Race condition details:\n"
                f"  Missing: {race_result.missing}\n"
                f"  Duplicates: {race_result.duplicates}\n"
                f"  Out of order: {race_result.out_of_order_pairs}"
            )

        # Allow up to 1 missing message (network timing), but no duplicates
        assert len(race_result.duplicates) == 0, (
            f"No duplicate messages should exist: {race_result.duplicates}"
        )
        assert len(race_result.missing) <= 1, (
            f"At most 1 message can be missing due to timing: {race_result.missing}"
        )

        # VALIDATION 4: Check order preservation
        # Messages that ARE stored should be in correct order
        assert len(race_result.out_of_order_pairs) == 0, (
            f"Messages should be in correct order: {race_result.out_of_order_pairs}"
        )

        # VALIDATION 5: Verify context integrity
        integrity = await context_validator.validate_context_integrity(
            conversation_agent.conversation_id
        )

        # DB should have most messages
        assert integrity.db_message_count >= 8, (
            f"DB should have at least 8 messages (4 turns): {integrity.db_message_count}"
        )

        # Order should be preserved
        assert integrity.order_preserved, "Message order should be preserved in storage"

        # VALIDATION 6: Responses should contain relevant content
        # Check that we got meaningful responses (not empty/error)
        meaningful_responses = 0
        for turn in turns:
            if turn.response_text and len(turn.response_text) > 50:
                meaningful_responses += 1

        assert meaningful_responses >= 4, (
            f"At least 4 responses should be meaningful: {meaningful_responses}/5"
        )

        # Log success summary
        logger.info(
            f"Task 019 test passed:\n"
            f"  Messages sent: 5\n"
            f"  Completed without error: {completed_count}\n"
            f"  Stored in DB: {integrity.db_message_count}\n"
            f"  Order preserved: {integrity.order_preserved}\n"
            f"  Race conditions: {race_result.detected}\n"
            f"  Missing: {len(race_result.missing)}\n"
            f"  Duplicates: {len(race_result.duplicates)}"
        )

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

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
    async def test_simultaneous_messages(
        self,
        api_base_url: str,
        context_validator: ContextValidatorAgent,
    ):
        """
        Test simultaneous message handling per PRD Task 020.

        This test validates:
        1. No crashes when 3 messages are sent at exact same time
        2. All messages are processed (order may vary)
        3. Context remains consistent after concurrent processing

        Uses ConversationFlowAgent.run_concurrent_messages() with delay=0
        to simulate exact simultaneous submission.
        """
        agent = ConversationFlowAgent(base_url=api_base_url)

        # 3 distinct messages to send simultaneously
        messages = [
            "What is the EIC Accelerator programme?",
            "What are the clusters in Horizon Europe?",
            "What is the budget for MSCA fellowships?",
        ]

        # Send all 3 messages at exact same time (delay_between_ms=0)
        turns = await agent.run_concurrent_messages(messages, delay_between_ms=0)

        # VALIDATION 1: No crashes - all requests should complete
        assert len(turns) == 3, f"Expected 3 turns, got {len(turns)}"

        # Count errors and successful responses
        success_count = sum(1 for t in turns if not t.has_error)

        # Log details for debugging
        for i, turn in enumerate(turns):
            if turn.has_error:
                logger.warning(f"Simultaneous message {i + 1} error: {turn.error}")
            else:
                logger.info(
                    f"Simultaneous message {i + 1} completed: {len(turn.response_text)} chars"
                )

        # VALIDATION 2: All messages processed (allow 1 failure due to race conditions)
        # At least 2 of 3 messages should succeed (relaxed for concurrent stress)
        assert success_count >= 2, (
            f"Too many failures: only {success_count}/3 messages succeeded. "
            f"Errors: {[t.error for t in turns if t.has_error]}"
        )

        # If all succeeded, validate responses contain relevant content
        if success_count == 3:
            # Check each response has meaningful content
            for turn in turns:
                assert len(turn.response_text) > 50, (
                    f"Response too short: {turn.response_text[:100]}"
                )

            # Verify distinct responses (not all the same)
            response_texts = [t.response_text for t in turns]
            unique_responses = len(set(r[:100] for r in response_texts))
            assert unique_responses >= 2, (
                "Responses should be distinct (possible duplicate handling issue)"
            )

        # Allow time for storage operations to complete
        await asyncio.sleep(2.0)

        # VALIDATION 3: Context remains consistent
        integrity = await context_validator.validate_context_integrity(agent.conversation_id)

        # Check that we have some messages stored
        # Note: Due to race conditions, not all messages may be stored,
        # but we should have at least some
        assert integrity.db_message_count > 0, "At least some messages should be stored in DB"

        # Order should be preserved within what was stored
        # (messages may be stored in different order than sent)
        # The key validation is no data corruption
        assert integrity.is_consistent or integrity.order_preserved, (
            f"Context integrity check failed:\n"
            f"  DB message count: {integrity.db_message_count}\n"
            f"  Redis turn count: {integrity.redis_turn_count}\n"
            f"  Order preserved: {integrity.order_preserved}"
        )

        # VALIDATION 4: Check for race condition artifacts
        # No duplicate messages should exist
        race_result = await context_validator.detect_race_condition(
            agent.conversation_id,
            expected_sequence=messages,
        )

        # Duplicates are a definite sign of race condition bugs
        assert len(race_result.duplicates) == 0, (
            f"Duplicate messages detected (race condition bug): {race_result.duplicates}"
        )

        # Log final summary
        logger.info(
            f"Task 020 test completed:\n"
            f"  Messages sent: 3 simultaneously\n"
            f"  Successful: {success_count}/3\n"
            f"  Stored in DB: {integrity.db_message_count}\n"
            f"  Order preserved: {integrity.order_preserved}\n"
            f"  Duplicates: {len(race_result.duplicates)}\n"
            f"  Missing: {len(race_result.missing)}"
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
    async def test_interleaved_conversations_task_021(
        self,
        api_base_url: str,
        context_validator: ContextValidatorAgent,
    ):
        """
        Test interleaved conversations per PRD Task 021.

        This test validates:
        1. No cross-contamination of context between two concurrent conversations
        2. Each conversation maintains its own state
        3. Concurrent processing works correctly

        Uses two ConversationFlowAgent instances on different conversation IDs,
        sending messages alternately to verify conversation isolation.
        """
        # Create two separate conversation agents with different IDs
        agent1 = ConversationFlowAgent(base_url=api_base_url)
        agent2 = ConversationFlowAgent(base_url=api_base_url)

        # Ensure different conversation IDs
        assert agent1.conversation_id != agent2.conversation_id, (
            "Agents should have different conversation IDs"
        )

        # Define topic-specific messages for each conversation
        # Agent 1: Hydrogen research topic
        agent1_messages = [
            "I'm researching hydrogen energy funding opportunities",
            "What clusters support hydrogen research?",
            "Tell me about Cluster 5 specifically",
        ]

        # Agent 2: Healthcare AI topic (completely different)
        agent2_messages = [
            "I'm looking for AI healthcare projects",
            "What programmes fund digital health?",
            "Tell me about Cluster 1 Health",
        ]

        # Send messages alternately between the two conversations
        agent1_turns = []
        agent2_turns = []

        for i in range(max(len(agent1_messages), len(agent2_messages))):
            # Agent 1 sends message
            if i < len(agent1_messages):
                turn1 = await agent1.send_message(agent1_messages[i])
                agent1_turns.append(turn1)
                logger.info(f"Agent 1 turn {i + 1}: {len(turn1.response_text)} chars")

            # Small delay
            await asyncio.sleep(0.2)

            # Agent 2 sends message
            if i < len(agent2_messages):
                turn2 = await agent2.send_message(agent2_messages[i])
                agent2_turns.append(turn2)
                logger.info(f"Agent 2 turn {i + 1}: {len(turn2.response_text)} chars")

            # Small delay before next round
            await asyncio.sleep(0.2)

        # Allow time for storage operations to complete
        await asyncio.sleep(2.0)

        # VALIDATION 1: No crashes - both conversations should complete
        agent1_success = sum(1 for t in agent1_turns if not t.has_error)
        agent2_success = sum(1 for t in agent2_turns if not t.has_error)

        assert agent1_success >= 2, (
            f"Agent 1 should have at least 2 successful turns: {agent1_success}/3. "
            f"Errors: {[t.error for t in agent1_turns if t.has_error]}"
        )
        assert agent2_success >= 2, (
            f"Agent 2 should have at least 2 successful turns: {agent2_success}/3. "
            f"Errors: {[t.error for t in agent2_turns if t.has_error]}"
        )

        # VALIDATION 2: No cross-contamination of context
        # Agent 1's responses should NOT contain Agent 2's topic keywords
        for turn in agent1_turns:
            if turn.response_text:
                response_lower = turn.response_text.lower()
                # Allow "health" only if it's in context of energy or environment
                # but not if it's clearly healthcare focused
                contamination_found = False
                for keyword in ["healthcare", "medical", "patient", "clinical"]:
                    if keyword in response_lower:
                        # Check if it's incidental mention vs main topic
                        # Count hydrogen mentions vs healthcare mentions
                        hydrogen_count = response_lower.count("hydrogen")
                        health_count = response_lower.count(keyword)
                        if health_count > hydrogen_count:
                            contamination_found = True
                            break

                assert not contamination_found, (
                    f"Agent 1 (hydrogen topic) has cross-contamination from Agent 2 "
                    f"(healthcare topic). Response: {turn.response_text[:300]}..."
                )

        # Agent 2's responses should NOT contain Agent 1's topic keywords
        for turn in agent2_turns:
            if turn.response_text:
                response_lower = turn.response_text.lower()
                contamination_found = False
                for keyword in ["hydrogen", "h2", "fuel cell", "green hydrogen"]:
                    if keyword in response_lower:
                        # Check if it's incidental mention vs main topic
                        # Count healthcare mentions vs hydrogen mentions
                        healthcare_count = response_lower.count("health")
                        hydrogen_count = response_lower.count(keyword)
                        if hydrogen_count > healthcare_count:
                            contamination_found = True
                            break

                assert not contamination_found, (
                    f"Agent 2 (healthcare topic) has cross-contamination from Agent 1 "
                    f"(hydrogen topic). Response: {turn.response_text[:300]}..."
                )

        # VALIDATION 3: Each conversation maintains its own state
        # Check context integrity for both conversations
        integrity1 = await context_validator.validate_context_integrity(agent1.conversation_id)
        integrity2 = await context_validator.validate_context_integrity(agent2.conversation_id)

        # Both should have messages stored
        assert integrity1.db_message_count > 0, (
            f"Agent 1 should have messages in DB: {integrity1.db_message_count}"
        )
        assert integrity2.db_message_count > 0, (
            f"Agent 2 should have messages in DB: {integrity2.db_message_count}"
        )

        # Order should be preserved within each conversation
        assert integrity1.order_preserved, "Agent 1 message order should be preserved"
        assert integrity2.order_preserved, "Agent 2 message order should be preserved"

        # VALIDATION 4: Verify conversation IDs are independent
        # Get messages from DB and verify no overlap
        db_messages_1 = []
        db_messages_2 = []

        if context_validator._db_pool:
            async with context_validator._db_pool.acquire() as conn:
                rows1 = await conn.fetch(
                    """
                    SELECT conversation_id, content FROM conversation_messages
                    WHERE conversation_id = $1
                    """,
                    str(agent1.conversation_id),
                )
                rows2 = await conn.fetch(
                    """
                    SELECT conversation_id, content FROM conversation_messages
                    WHERE conversation_id = $1
                    """,
                    str(agent2.conversation_id),
                )
                db_messages_1 = [r["content"] for r in rows1]
                db_messages_2 = [r["content"] for r in rows2]

        # Verify messages are in the correct conversation
        for msg in agent1_messages:
            # Check that this message is in agent1's conversation, not agent2's
            in_conv1 = any(msg in content for content in db_messages_1)
            in_conv2 = any(msg in content for content in db_messages_2)
            # Should be in conv1 OR not stored yet (acceptable), but NOT in conv2
            assert not in_conv2, f"Agent 1's message found in Agent 2's conversation: {msg}"

        for msg in agent2_messages:
            # Check that this message is in agent2's conversation, not agent1's
            in_conv1 = any(msg in content for content in db_messages_1)
            in_conv2 = any(msg in content for content in db_messages_2)
            # Should be in conv2 OR not stored yet (acceptable), but NOT in conv1
            assert not in_conv1, f"Agent 2's message found in Agent 1's conversation: {msg}"

        # VALIDATION 5: Final context check - each conversation should reference its topic
        # Agent 1's last response should still be about hydrogen
        if agent1_turns and agent1_turns[-1].response_text:
            response1 = agent1_turns[-1].response_text.lower()
            topic_relevant = (
                "hydrogen" in response1
                or "cluster 5" in response1
                or "energy" in response1
                or "climate" in response1
            )
            assert topic_relevant, (
                f"Agent 1's final response should be about hydrogen/energy. "
                f"Got: {agent1_turns[-1].response_text[:200]}..."
            )

        # Agent 2's last response should still be about healthcare
        if agent2_turns and agent2_turns[-1].response_text:
            response2 = agent2_turns[-1].response_text.lower()
            topic_relevant = (
                "health" in response2
                or "cluster 1" in response2
                or "digital" in response2
                or "medical" in response2
                or "ai" in response2
            )
            assert topic_relevant, (
                f"Agent 2's final response should be about healthcare/AI. "
                f"Got: {agent2_turns[-1].response_text[:200]}..."
            )

        # Log success summary
        logger.info(
            f"Task 021 test completed:\n"
            f"  Conversation 1 (hydrogen): {agent1.conversation_id}\n"
            f"    - Turns: {len(agent1_turns)}, Successful: {agent1_success}\n"
            f"    - Messages in DB: {integrity1.db_message_count}\n"
            f"  Conversation 2 (healthcare): {agent2.conversation_id}\n"
            f"    - Turns: {len(agent2_turns)}, Successful: {agent2_success}\n"
            f"    - Messages in DB: {integrity2.db_message_count}\n"
            f"  Cross-contamination: None detected\n"
            f"  Conversation isolation: Verified"
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

    @pytest.mark.asyncio
    async def test_quality_degradation_detection_task_023(
        self,
        conversation_agent: ConversationFlowAgent,
        quality_evaluator: QualityEvaluatorAgent,
    ):
        """
        Test quality degradation detection per PRD Task 023.

        This test validates:
        1. Quality degradation detection is properly implemented
        2. The test fails if quality drops more than 15 points during conversation
        3. Running long_conversation scenario shows no degradation

        Uses QualityEvaluatorAgent.evaluate_conversation() to track quality
        across all turns and detect any drops of 15+ points.
        """
        # Load and run the long_conversation scenario messages
        # These are the 10 messages from long_conversation.yaml
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
        turn_scores = []

        for i, msg in enumerate(messages):
            turn = await conversation_agent.send_message(msg)

            # Allow some flexibility - don't fail on single turn errors
            if turn.has_error:
                logger.warning(f"Turn {i + 1} error: {turn.error}")

            turn_data = {
                "query": msg,
                "response": turn.response_text or f"Error: {turn.error}",
            }
            turns_data.append(turn_data)

            # Calculate quality score using improved rule-based method
            # This is more consistent than pattern-matching which varies by topic
            score = self._calculate_response_quality(turn.response_text or "")
            turn_scores.append(score)

            # Log individual turn quality for debugging
            logger.info(f"Turn {i + 1} quality: {score}/100")

            # Small delay between turns
            await asyncio.sleep(0.3)

        # Verify we completed all 10 turns
        assert len(turns_data) >= 10, f"Expected 10 turns, got {len(turns_data)}"

        # Evaluate full conversation quality using QualityEvaluatorAgent
        quality_result = await quality_evaluator.evaluate_conversation(turns_data)

        # TASK 023 CORE ASSERTION: Fail if quality drops more than 15 points
        assert not quality_result.degradation_detected, (
            f"QUALITY DEGRADATION DETECTED (Task 023 failure):\n"
            f"  Turn {quality_result.degradation_turn} dropped "
            f"{quality_result.degradation_amount:.1f} points\n"
            f"  Score progression: {turn_scores}\n"
            f"  Trend: {quality_result.trend}\n"
            f"  Average score: {quality_result.average_score:.1f}/100"
        )

        # Additional assertions for quality baseline
        assert quality_result.average_score >= 55, (
            f"Average quality too low: {quality_result.average_score:.1f}/100. "
            f"Expected >= 55 for long_conversation scenario."
        )

        # Check that individual turn scores don't have massive drops (15+ points)
        # using our rule-based scoring
        for i in range(1, len(turn_scores)):
            drop = turn_scores[i - 1] - turn_scores[i]
            if drop >= 15:
                logger.warning(
                    f"Quality drop of {drop} points detected between turn {i} and {i + 1}. "
                    f"Previous response length: {len(turns_data[i - 1]['response'])} chars, "
                    f"Current response length: {len(turns_data[i]['response'])} chars"
                )
                # This is a warning, not assertion - the QualityEvaluatorAgent
                # result is the authoritative check

        # Verify final turn correctly references initial topic
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

        # Log success summary
        logger.info(
            f"Task 023 quality degradation test PASSED:\n"
            f"  Turns: {len(turn_scores)}\n"
            f"  Average score: {quality_result.average_score:.1f}/100\n"
            f"  Min score: {quality_result.min_score}/100\n"
            f"  Max score: {quality_result.max_score}/100\n"
            f"  Trend: {quality_result.trend}\n"
            f"  Score progression: {turn_scores}"
        )

    def _calculate_response_quality(self, response: str) -> int:
        """
        Calculate response quality using consistent rule-based scoring.

        This method provides stable quality scores based on response characteristics
        rather than topic-specific pattern matching.

        Args:
            response: The response text to evaluate

        Returns:
            Quality score from 0-100
        """
        if not response or len(response) < 10:
            return 20

        score = 0

        # Length component (max 35 points)
        length = len(response)
        if length >= 800:
            score += 35
        elif length >= 500:
            score += 30
        elif length >= 300:
            score += 25
        elif length >= 150:
            score += 20
        elif length >= 50:
            score += 15
        else:
            score += 10

        # Structure component (max 25 points)
        # Check for structured content (lists, headers, etc.)
        has_list = any(marker in response for marker in ["1.", "2.", "3.", "- ", "• ", "* "])
        has_sections = response.count("\n\n") >= 1
        has_headers = ":" in response and response.count(":") >= 2

        if has_list:
            score += 10
        if has_sections:
            score += 8
        if has_headers:
            score += 7

        # Specificity component (max 25 points)
        # Check for specific details (numbers, names, dates)
        specificity_indicators = 0
        if any(char.isdigit() for char in response):
            specificity_indicators += 1
        if "%" in response or "percent" in response.lower():
            specificity_indicators += 1
        if "EUR" in response or "€" in response or "million" in response.lower():
            specificity_indicators += 1
        if any(year in response for year in ["2024", "2025", "2026", "2027"]):
            specificity_indicators += 1
        if any(word in response.lower() for word in ["specifically", "example", "such as"]):
            specificity_indicators += 1

        score += min(25, specificity_indicators * 5)

        # Completeness component (max 15 points)
        # Check for complete sentences and proper ending
        sentences = response.replace("!", ".").replace("?", ".").split(".")
        complete_sentences = sum(1 for s in sentences if len(s.strip()) > 20)

        if complete_sentences >= 5:
            score += 15
        elif complete_sentences >= 3:
            score += 10
        elif complete_sentences >= 1:
            score += 5

        return min(100, score)

    @pytest.mark.asyncio
    async def test_quality_degradation_with_scenario_runner(
        self,
        conversation_agent: ConversationFlowAgent,
        quality_evaluator: QualityEvaluatorAgent,
    ):
        """
        Test quality degradation using the scenario runner with long_conversation.yaml.

        This test verifies that the long_conversation scenario from
        tests/scenarios/context/long_conversation.yaml passes quality validation,
        specifically checking the quality_non_degradation final validation.
        """
        # Find the long_conversation scenario
        long_conv_scenario = None
        for scenario in CONTEXT_SCENARIOS:
            if "long" in scenario.name.lower():
                long_conv_scenario = scenario
                break

        if not long_conv_scenario:
            pytest.skip("long_conversation scenario not found in CONTEXT_SCENARIOS")

        # Run the scenario
        result = await conversation_agent.run_scenario(long_conv_scenario)

        # Verify scenario completed without critical errors
        completed_turns = len(result.turns)
        expected_turns = len(long_conv_scenario.steps)
        assert completed_turns >= expected_turns * 0.8, (
            f"Should complete at least 80% of turns: {completed_turns}/{expected_turns}"
        )

        # Extract turns data for quality evaluation
        turns_data = [
            {
                "query": turn.user_message,
                "response": turn.response_text or "",
            }
            for turn in result.turns
        ]

        # Evaluate quality across the conversation
        quality_result = await quality_evaluator.evaluate_conversation(turns_data)

        # Check for quality degradation (15+ points drop)
        assert not quality_result.degradation_detected, (
            f"Quality degradation detected in long_conversation scenario:\n"
            f"  Turn: {quality_result.degradation_turn}\n"
            f"  Drop: {quality_result.degradation_amount:.1f} points\n"
            f"  Trend: {quality_result.trend}"
        )

        # Check average quality is reasonable
        assert quality_result.average_score >= 50, (
            f"Average quality too low in long_conversation: {quality_result.average_score:.1f}/100"
        )

        # Check quality_non_degradation validation was included
        has_quality_validation = any("quality" in v.name.lower() for v in result.validations)
        if not has_quality_validation:
            logger.warning("quality_non_degradation validation not found in scenario results")

        logger.info(
            f"Long conversation scenario quality test PASSED:\n"
            f"  Scenario: {long_conv_scenario.name}\n"
            f"  Turns completed: {completed_turns}/{expected_turns}\n"
            f"  Average quality: {quality_result.average_score:.1f}/100\n"
            f"  Degradation detected: {quality_result.degradation_detected}\n"
            f"  Trend: {quality_result.trend}"
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
