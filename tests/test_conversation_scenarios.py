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

import pytest
import asyncio
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import yaml

# Import test agents
from tests.agents.conversation_flow_agent import (
    ConversationFlowAgent,
    ConversationScenario,
    ScenarioResult,
)
from tests.agents.context_validator_agent import (
    ContextValidatorAgent,
    IntegrityResult,
)
from tests.agents.quality_evaluator_agent import (
    QualityEvaluatorAgent,
    ConversationQualityResult,
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

def load_scenarios_from_directory(directory: Path) -> List[ConversationScenario]:
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


def load_all_scenarios() -> Dict[str, List[ConversationScenario]]:
    """Load all scenarios organized by category."""
    categories = {}

    for category_dir in SCENARIOS_DIR.iterdir():
        if category_dir.is_dir():
            category_name = category_dir.name
            scenarios = load_scenarios_from_directory(category_dir)
            if scenarios:
                categories[category_name] = scenarios

    return categories


def get_scenario_ids(scenarios: List[ConversationScenario]) -> List[str]:
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
        turn = await conversation_agent.send_message(
            "Find open funding calls for renewable energy"
        )

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
        turn = await conversation_agent.send_message(
            "Find funded AI research projects"
        )

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
            v for v in result.validations
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
        await conversation_agent.send_message(
            "Show me 5 open funding calls"
        )

        # Follow-up with numbered reference
        turn = await conversation_agent.send_message(
            "Tell me about the third one"
        )

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
        context_validations = [
            v for v in result.validations
            if "context" in v.name.lower()
        ]

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
        await conversation_agent.send_message(
            "Show me 3 funding calls"
        )

        # Make invalid reference
        turn = await conversation_agent.send_message(
            "Tell me about the 100th one"
        )

        # Should not crash, should have some response
        assert not turn.has_error or "error" not in turn.error.lower(), (
            "Should handle invalid reference gracefully"
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
    @pytest.mark.skipif(
        not os.environ.get("DATABASE_URL"),
        reason="DATABASE_URL not set"
    )
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

        assert result.passed, (
            f"Message not stored properly: {result.message}"
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.environ.get("DATABASE_URL"),
        reason="DATABASE_URL not set"
    )
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
            f"Quality too low: {score.total_score}/100\n"
            f"Response: {turn.response_text[:500]}..."
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
            turns_data.append({
                "query": msg,
                "response": turn.response_text,
            })

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
    @pytest.mark.skipif(
        not os.environ.get("DATABASE_URL"),
        reason="DATABASE_URL not set"
    )
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
    pytest.main([
        __file__,
        "-v",
        "-x",
        "--tb=short",
    ])
