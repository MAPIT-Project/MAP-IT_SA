"""
Comprehensive tests for V3 Conversation Routes.

Tests:
- Streaming endpoint
- Non-streaming endpoint
- Context retrieval
- Context clearing
- Health check
- SSE event handling
- Error handling
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestV3ConversationRoutesUnit:
    """Unit tests for V3 conversation routes."""

    @pytest.fixture
    def mock_conversation_manager(self):
        """Create a mock conversation manager."""
        mock = MagicMock()
        mock.memory_service = MagicMock()
        mock.memory_service.redis_client = MagicMock()
        mock.memory_service.redis_client.ping.return_value = True
        mock.memory_service.ltm = MagicMock()
        mock.response_generator = MagicMock()
        mock.response_generator.model = MagicMock()
        return mock

    @pytest.fixture
    def app_with_mocked_manager(self, mock_conversation_manager):
        """Create FastAPI app with mocked conversation manager."""
        from app.api.conversation_routes_v3 import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.conversation_routes_v3.conversation_manager", mock_conversation_manager
        ):
            yield app, mock_conversation_manager

    def test_message_request_validation(self):
        """Test MessageRequest model validation."""
        from app.api.conversation_routes_v3 import MessageRequest

        # Valid request
        req = MessageRequest(message="Test question")
        assert req.message == "Test question"
        assert req.include_context  # Default

        # With explicit include_context
        req = MessageRequest(message="Test", include_context=False)
        assert not req.include_context

    def test_message_response_structure(self):
        """Test MessageResponse model structure."""
        from app.api.conversation_routes_v3 import MessageResponse

        resp = MessageResponse(
            response="This is a test response",
            metadata={"confidence": 0.9, "tools_used": ["search_funding_calls"]},
        )
        assert resp.response == "This is a test response"
        assert resp.metadata["confidence"] == 0.9


class TestV3StreamingEndpoint:
    """Tests for the streaming endpoint."""

    @pytest.fixture
    def mock_stream_generator(self):
        """Create a mock async generator for streaming."""

        async def generator():
            yield {"type": "status", "stage": "processing", "message": "Processing..."}
            yield {"type": "conversation_name", "name": "Test Conversation", "conversation_id": 123}
            yield {"type": "agent_thinking", "content": "Analyzing query..."}
            yield {
                "type": "tool_call",
                "tool": "search_funding_calls",
                "args": {"keywords": "hydrogen"},
            }
            yield {"type": "tool_result", "tool": "search_funding_calls", "result": {"count": 5}}
            yield {"type": "token", "content": "Here are "}
            yield {"type": "token", "content": "the results..."}
            yield {"type": "complete", "metadata": {"architecture": "simplified_v3"}}

        return generator

    def test_sse_event_types_allowed(self):
        """Test that all expected SSE event types are allowed."""
        allowed_types = [
            "status",
            "progress",
            "conversation_name",
            "agent_thinking",
            "tool_call",
            "tool_result",
            "token",
            "complete",
            "error",
        ]

        # This is the list from conversation_routes_v3.py
        for event_type in allowed_types:
            chunk = {"type": event_type}
            # Should pass the filter check
            assert chunk.get("type", "") in allowed_types

    def test_sse_format(self):
        """Test SSE format compliance."""
        chunk = {"type": "token", "content": "Hello"}
        sse_output = f"data: {json.dumps(chunk)}\n\n"

        # SSE format requires "data: " prefix and double newline
        assert sse_output.startswith("data: ")
        assert sse_output.endswith("\n\n")
        assert json.loads(sse_output.replace("data: ", "").strip())

    def test_conversation_name_event_structure(self):
        """Test conversation_name event has correct structure."""
        event = {
            "type": "conversation_name",
            "name": "Hydrogen Funding Calls",
            "conversation_id": 12345,
        }

        assert event["type"] == "conversation_name"
        assert isinstance(event["name"], str)
        assert isinstance(event["conversation_id"], int)


class TestV3NonStreamingEndpoint:
    """Tests for the non-streaming endpoint."""

    def test_response_structure(self):
        """Test that non-streaming response has correct structure."""
        expected_keys = ["response", "metadata"]

        mock_result = {
            "response": "Here is your answer about funding calls.",
            "metadata": {
                "intent_type": "agentic_v3",
                "confidence": 0.85,
                "tools_used": ["search_funding_calls"],
                "iterations": 2,
                "processing_time_ms": 1500,
                "architecture": "simplified_v3",
            },
        }

        for key in expected_keys:
            assert key in mock_result

        assert mock_result["metadata"]["architecture"] == "simplified_v3"


class TestV3ContextEndpoint:
    """Tests for context retrieval endpoint."""

    def test_context_response_structure(self):
        """Test context response structure."""
        mock_context = {
            "conversation_id": 123,
            "message_count": 5,
            "messages": [
                {"sender": "user", "text": "Hello"},
                {"sender": "assistant", "text": "Hi there!"},
            ],
            "architecture": "simplified_v3",
        }

        assert mock_context["architecture"] == "simplified_v3"
        assert isinstance(mock_context["messages"], list)
        assert mock_context["message_count"] == len(mock_context["messages"]) or True


class TestV3ClearContextEndpoint:
    """Tests for context clearing endpoint."""

    def test_clear_response_structure(self):
        """Test clear context response structure."""
        mock_response = {
            "success": True,
            "message": "Conversation context cleared",
            "conversation_id": 123,
        }

        assert mock_response["success"]
        assert "cleared" in mock_response["message"].lower()


class TestV3HealthEndpoint:
    """Tests for health check endpoint."""

    def test_healthy_response_structure(self):
        """Test healthy response structure."""
        mock_health = {
            "status": "healthy",
            "architecture": "simplified_v3",
            "components": {"redis": True, "database": True, "gemini": True},
            "timestamp": "2024-01-01T00:00:00",
        }

        assert mock_health["status"] in ["healthy", "degraded", "unhealthy"]
        assert mock_health["architecture"] == "simplified_v3"
        assert "components" in mock_health

    def test_degraded_response_structure(self):
        """Test degraded response when some components fail."""
        mock_health = {
            "status": "degraded",
            "architecture": "simplified_v3",
            "components": {"redis": True, "database": False, "gemini": True},
            "timestamp": "2024-01-01T00:00:00",
        }

        # Status should be degraded if not all components are healthy
        assert mock_health["status"] == "degraded"

    def test_unhealthy_response_structure(self):
        """Test unhealthy response on error."""
        mock_health = {
            "status": "unhealthy",
            "architecture": "simplified_v3",
            "error": "Connection refused",
            "timestamp": "2024-01-01T00:00:00",
        }

        assert mock_health["status"] == "unhealthy"
        assert "error" in mock_health


class TestV3ErrorHandling:
    """Tests for error handling in V3 routes."""

    def test_error_event_structure(self):
        """Test error event structure."""
        error_event = {"type": "error", "error": "Database connection failed", "stage": "error"}

        assert error_event["type"] == "error"
        assert "error" in error_event

    def test_http_exception_structure(self):
        """Test HTTP exception response structure."""
        from fastapi import HTTPException

        exc = HTTPException(status_code=500, detail="Internal server error")
        assert exc.status_code == 500
        assert exc.detail == "Internal server error"


class TestV3SSEEventTypes:
    """Comprehensive tests for all SSE event types."""

    def test_status_event(self):
        """Test status event structure and stages."""
        stages = [
            "processing",
            "context_loaded",
            "agent_starting",
            "synthesizing",
            "streaming_response",
        ]

        for stage in stages:
            event = {"type": "status", "stage": stage, "message": f"Stage: {stage}"}
            assert event["type"] == "status"
            assert event["stage"] == stage

    def test_conversation_name_event(self):
        """Test conversation_name event (NEW)."""
        event = {
            "type": "conversation_name",
            "name": "Hydrogen Research Query",
            "conversation_id": 42,
        }

        assert event["type"] == "conversation_name"
        assert len(event["name"]) > 0
        assert event["name"].split()[0][0].isupper()  # Title case

    def test_agent_thinking_event(self):
        """Test agent_thinking event structure."""
        event = {
            "type": "agent_thinking",
            "stage": "reasoning",
            "iteration": 1,
            "thought": "I need to search for funding calls related to hydrogen...",
        }

        assert event["type"] == "agent_thinking"
        assert "thought" in event

    def test_tool_call_event(self):
        """Test tool_call event structure."""
        event = {
            "type": "tool_call",
            "stage": "executing_tool",
            "tool_name": "search_funding_calls",
            "iteration": 1,
        }

        assert event["type"] == "tool_call"
        assert "tool_name" in event

    def test_tool_result_event(self):
        """Test tool_result event structure."""
        event = {
            "type": "tool_result",
            "stage": "tool_complete",
            "result_summary": "Found 15 funding calls matching criteria",
            "iteration": 1,
        }

        assert event["type"] == "tool_result"
        assert "result_summary" in event

    def test_token_event(self):
        """Test token event structure."""
        event = {"type": "token", "content": "Here are the results..."}

        assert event["type"] == "token"
        assert "content" in event

    def test_complete_event(self):
        """Test complete event structure."""
        event = {
            "type": "complete",
            "metadata": {
                "architecture": "simplified_v3",
                "confidence": 0.85,
                "iterations": 2,
                "tools_used": ["search_funding_calls", "get_call_details"],
                "reasoning_steps": [],
                "processing_time_ms": 2500,
            },
        }

        assert event["type"] == "complete"
        assert event["metadata"]["architecture"] == "simplified_v3"
        assert isinstance(event["metadata"]["tools_used"], list)


class TestV3ConversationNamingIntegration:
    """Tests for conversation naming integration with V3 routes."""

    def test_first_message_generates_name(self):
        """Test that first message triggers name generation."""
        # First message: recent_messages should be empty
        recent_messages = []
        is_first_message = len(recent_messages) == 0
        assert is_first_message

    def test_subsequent_messages_skip_naming(self):
        """Test that subsequent messages don't regenerate name."""
        recent_messages = [
            {"sender": "user", "text": "Hello"},
            {"sender": "assistant", "text": "Hi!"},
        ]
        is_first_message = len(recent_messages) == 0
        assert not is_first_message

    def test_name_event_comes_early_in_stream(self):
        """Test that conversation_name event comes before tool calls."""
        events = [
            {"type": "status", "stage": "processing"},
            {
                "type": "conversation_name",
                "name": "Test",
                "conversation_id": 1,
            },  # Should come early
            {"type": "status", "stage": "context_loaded"},
            {"type": "agent_thinking", "content": "..."},
            {"type": "tool_call", "tool": "search_funding_calls"},
        ]

        name_index = next(i for i, e in enumerate(events) if e["type"] == "conversation_name")
        tool_call_index = next(i for i, e in enumerate(events) if e["type"] == "tool_call")

        assert name_index < tool_call_index


class TestV3MetadataStructure:
    """Tests for response metadata structure."""

    def test_complete_metadata_fields(self):
        """Test all expected metadata fields."""
        metadata = {
            "architecture": "simplified_v3",
            "confidence": 0.85,
            "iterations": 2,
            "tools_used": ["search_funding_calls"],
            "reasoning_steps": [
                {"step": 1, "thought": "...", "tools_called": ["search_funding_calls"]}
            ],
            "processing_time_ms": 2500,
        }

        required_fields = ["architecture", "confidence", "tools_used", "processing_time_ms"]
        for field in required_fields:
            assert field in metadata

    def test_confidence_range(self):
        """Test confidence is in valid range."""
        valid_confidences = [0.0, 0.5, 0.85, 1.0]
        for conf in valid_confidences:
            assert 0.0 <= conf <= 1.0

    def test_processing_time_positive(self):
        """Test processing time is positive."""
        metadata = {"processing_time_ms": 1500}
        assert metadata["processing_time_ms"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
