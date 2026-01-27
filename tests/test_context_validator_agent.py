"""
Unit tests for the Context Validator Agent.

Tests the following functionality:
- Context persistence validation (validate_context_persistence)
- Agent can be imported and instantiated by test runner
- Validation result structure
"""

import pytest

from tests.agents.context_validator_agent import (
    ContextValidatorAgent,
    IntegrityResult,
    MessageRecord,
    RaceConditionResult,
    ValidationResult,
)


class TestContextValidatorAgentImport:
    """Test that the agent can be imported and instantiated."""

    def test_agent_can_be_imported(self):
        """Test that ContextValidatorAgent can be imported."""
        from tests.agents.context_validator_agent import ContextValidatorAgent

        assert ContextValidatorAgent is not None

    def test_agent_can_be_instantiated(self):
        """Test that ContextValidatorAgent can be instantiated."""
        agent = ContextValidatorAgent()
        assert agent is not None
        assert agent.database_url is None
        assert agent.redis_url is None
        assert agent.api_base_url is None

    def test_agent_instantiation_with_parameters(self):
        """Test agent instantiation with custom parameters."""
        agent = ContextValidatorAgent(
            database_url="postgresql://localhost/test",
            redis_url="redis://localhost:6379",
            api_base_url="http://localhost:8000",
        )
        assert agent.database_url == "postgresql://localhost/test"
        assert agent.redis_url == "redis://localhost:6379"
        assert agent.api_base_url == "http://localhost:8000"


class TestValidationResultStructure:
    """Test the ValidationResult dataclass."""

    def test_validation_result_passed(self):
        """Test creating a passed validation result."""
        result = ValidationResult(
            passed=True,
            check_name="test_check",
            message="Test passed",
            details={"key": "value"},
        )
        assert result.passed is True
        assert result.check_name == "test_check"
        assert result.message == "Test passed"
        assert result.details == {"key": "value"}

    def test_validation_result_failed(self):
        """Test creating a failed validation result."""
        result = ValidationResult(
            passed=False,
            check_name="test_check",
            message="Test failed",
        )
        assert result.passed is False
        assert result.check_name == "test_check"
        assert result.message == "Test failed"
        assert result.details == {}


class TestIntegrityResultStructure:
    """Test the IntegrityResult dataclass."""

    def test_integrity_result_defaults(self):
        """Test IntegrityResult default values."""
        result = IntegrityResult(conversation_id="test-123")
        assert result.conversation_id == "test-123"
        assert result.is_consistent is True
        assert result.message_count_match is True
        assert result.order_preserved is True
        assert result.content_match is True
        assert result.db_message_count == 0
        assert result.redis_turn_count == 0
        assert result.api_message_count == 0
        assert result.validation_results == []

    def test_add_validation_passed(self):
        """Test adding a passed validation."""
        result = IntegrityResult(conversation_id="test-123")
        result.add_validation("test_check", True, "Passed")
        assert len(result.validation_results) == 1
        assert result.validation_results[0].passed is True
        assert result.is_consistent is True

    def test_add_validation_failed(self):
        """Test adding a failed validation."""
        result = IntegrityResult(conversation_id="test-123")
        result.add_validation("test_check", False, "Failed")
        assert len(result.validation_results) == 1
        assert result.validation_results[0].passed is False
        assert result.is_consistent is False


class TestContextPersistenceValidationLogic:
    """Test the context persistence validation logic in isolation."""

    @pytest.mark.asyncio
    async def test_validate_context_persistence_topic_in_response(self):
        """Test that topics found in response pass validation."""
        agent = ContextValidatorAgent()

        # Mock the _get_api_context method to return empty context
        async def mock_get_api_context(conversation_id):
            return {"recent_messages": [], "summary": ""}

        agent._get_api_context = mock_get_api_context

        result = await agent.validate_context_persistence(
            conversation_id="test-123",
            expected_topics=["hydrogen"],
            current_response="I found several hydrogen funding calls for you.",
        )

        # Should pass because topic is in response
        assert result.passed is True
        assert "hydrogen" in result.details["topics_in_response"]
        assert result.details["asking_for_clarification"] is False

    @pytest.mark.asyncio
    async def test_validate_context_persistence_topic_in_context(self):
        """Test that topics found in context pass validation."""
        agent = ContextValidatorAgent()

        # Mock the _get_api_context method to return context with topic
        async def mock_get_api_context(conversation_id):
            return {
                "recent_messages": [
                    {"content": "I work on hydrogen storage technologies"},
                    {"content": "I found hydrogen funding opportunities"},
                ],
                "summary": "User interested in hydrogen research",
            }

        agent._get_api_context = mock_get_api_context

        result = await agent.validate_context_persistence(
            conversation_id="test-123",
            expected_topics=["hydrogen"],
            current_response="Here are some energy funding calls.",
        )

        # Should pass because topic is in context
        assert result.passed is True
        assert "hydrogen" in result.details["topics_in_context"]

    @pytest.mark.asyncio
    async def test_validate_context_persistence_asking_clarification_fails(self):
        """Test that asking for clarification fails validation."""
        agent = ContextValidatorAgent()

        # Mock the _get_api_context method
        async def mock_get_api_context(conversation_id):
            return {"recent_messages": [], "summary": ""}

        agent._get_api_context = mock_get_api_context

        result = await agent.validate_context_persistence(
            conversation_id="test-123",
            expected_topics=["hydrogen"],
            current_response="What topic are you interested in? Could you clarify?",
        )

        # Should fail because system is asking for clarification
        assert result.passed is False
        assert result.details["asking_for_clarification"] is True

    @pytest.mark.asyncio
    async def test_validate_context_persistence_topic_not_found(self):
        """Test that missing topics fail validation."""
        agent = ContextValidatorAgent()

        # Mock the _get_api_context method to return empty context
        async def mock_get_api_context(conversation_id):
            return {"recent_messages": [], "summary": ""}

        agent._get_api_context = mock_get_api_context

        result = await agent.validate_context_persistence(
            conversation_id="test-123",
            expected_topics=["quantum computing"],
            current_response="Here are some general funding calls.",
        )

        # Should fail because topic is not in context or response
        assert result.passed is False
        assert result.details["context_recalled"] is False

    @pytest.mark.asyncio
    async def test_validate_context_persistence_api_error(self):
        """Test that API errors are handled gracefully."""
        agent = ContextValidatorAgent()

        # Mock the _get_api_context method to return error
        async def mock_get_api_context(conversation_id):
            return {"error": "Connection refused"}

        agent._get_api_context = mock_get_api_context

        result = await agent.validate_context_persistence(
            conversation_id="test-123",
            expected_topics=["hydrogen"],
            current_response="Here are some calls.",
        )

        # Should fail due to API error
        assert result.passed is False
        assert "Connection refused" in result.message


class TestClarificationPatterns:
    """Test the clarification pattern detection."""

    @pytest.mark.asyncio
    async def test_various_clarification_patterns(self):
        """Test various clarification patterns are detected."""
        agent = ContextValidatorAgent()

        async def mock_get_api_context(conversation_id):
            return {"recent_messages": [], "summary": ""}

        agent._get_api_context = mock_get_api_context

        clarification_responses = [
            "What topic are you interested in?",
            "Which topic would you like to explore?",
            "Could you specify what area you're looking for?",
            "Could you clarify what you mean?",
            "What do you mean by that?",
            "Please clarify your research focus.",
            "Can you tell me more about what specific area?",
            "What exactly are you working on?",
            "Could you provide more details about what you're looking for?",
        ]

        for response in clarification_responses:
            result = await agent.validate_context_persistence(
                conversation_id="test-123",
                expected_topics=["hydrogen"],
                current_response=response,
            )
            assert result.details["asking_for_clarification"] is True, (
                f"Failed to detect clarification in: {response}"
            )

    @pytest.mark.asyncio
    async def test_non_clarification_responses(self):
        """Test that normal responses don't trigger clarification detection."""
        agent = ContextValidatorAgent()

        async def mock_get_api_context(conversation_id):
            return {"recent_messages": [], "summary": ""}

        agent._get_api_context = mock_get_api_context

        normal_responses = [
            "I found several hydrogen funding calls.",
            "Here are the relevant energy opportunities.",
            "Based on your interest in hydrogen, I recommend these calls.",
            "The deadline for this call is next month.",
            "This call specifically targets hydrogen storage research.",
        ]

        for response in normal_responses:
            result = await agent.validate_context_persistence(
                conversation_id="test-123",
                expected_topics=["hydrogen"],
                current_response=response,
            )
            assert result.details["asking_for_clarification"] is False, (
                f"False positive clarification detection in: {response}"
            )


class TestMessageRecord:
    """Test the MessageRecord dataclass."""

    def test_message_record_creation(self):
        """Test creating a MessageRecord."""
        record = MessageRecord(
            id="123",
            conversation_id="conv-456",
            role="user",
            content="Hello",
            source="db",
        )
        assert record.id == "123"
        assert record.conversation_id == "conv-456"
        assert record.role == "user"
        assert record.content == "Hello"
        assert record.source == "db"
        assert record.metadata == {}


class TestRaceConditionResult:
    """Test the RaceConditionResult dataclass."""

    def test_race_condition_result_defaults(self):
        """Test RaceConditionResult default values."""
        result = RaceConditionResult(conversation_id="test-123")
        assert result.conversation_id == "test-123"
        assert result.detected is False
        assert result.expected_sequence == []
        assert result.actual_sequence == []
        assert result.missing == []
        assert result.duplicates == []
        assert result.out_of_order_pairs == []
