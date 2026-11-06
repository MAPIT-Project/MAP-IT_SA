"""Regressions for the reported 'Test' response. All inference/storage is mocked."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.config import settings
from app.services.agents import tool_aware_agent as agent_module
from app.services.agents.query_preprocessing import LongQueryResult
from app.services.agents.tool_aware_agent import ToolAwareAgent
from app.services.agents.tool_registry import AgentPlan
from app.services.ai.errors import generation_error_message
from app.services.conversation.conversation_manager import ConversationManager


@pytest.mark.parametrize("provider", ["gemini", "openai", "openrouter"])
def test_authentication_diagnostic_does_not_expose_sdk_payload(provider):
    error = RuntimeError("API_KEY_INVALID secret-value and private uploaded document")
    message = generation_error_message(error, provider)
    assert "authentication failed" in message
    assert "secret-value" not in message
    assert "private" not in message


@pytest.mark.parametrize(
    "code,label", [(401, "authentication"), (403, "authentication"), (429, "quota")]
)
def test_generation_status_codes_are_actionable(code, label):
    error = RuntimeError("private SDK payload")
    error.status_code = code
    assert label in generation_error_message(error, "gemini")


@pytest.mark.asyncio
async def test_legacy_auth_failure_does_not_search_or_attempt_synthesis(monkeypatch):
    monkeypatch.setattr(settings, "agent_framework", "legacy")
    owner = ToolAwareAgent.__new__(ToolAwareAgent)
    owner.llm = SimpleNamespace(provider="gemini", model_name="synthetic-model")
    owner.max_iterations = 5
    owner.plan_cache = None
    owner._get_tool_hint = Mock(return_value="")
    owner._select_knowledge_sections = Mock(return_value="")
    owner._get_tools_description = Mock(return_value="")
    owner._execute_tool_calls = AsyncMock()
    owner._llm_synthesize_results = AsyncMock()
    inference = AsyncMock(side_effect=RuntimeError("API_KEY_INVALID secret-value"))
    monkeypatch.setattr(agent_module, "generate_content", inference)
    plan = AgentPlan("Test", "simple", [])
    count, results = await owner._execute_react_loop("Test", "", plan)
    assert count == 1
    assert results == {}
    assert "authentication failed" in plan.error
    assert plan.final_answer is None
    assert plan.confidence == 0
    inference.assert_awaited_once()
    owner._execute_tool_calls.assert_not_awaited()
    owner._llm_synthesize_results.assert_not_awaited()


def manager(result):
    owner = ConversationManager.__new__(ConversationManager)
    owner.tool_aware_agent = SimpleNamespace(process_query=AsyncMock(return_value=result))
    owner._get_recent_messages_simple = Mock(return_value=[{"sender": "user", "text": "Hi"}])
    owner._format_conversation_for_agent = Mock(return_value="")
    owner._add_to_memory_only = Mock()
    owner.atomic_storage = SimpleNamespace(
        store_message_pair=AsyncMock(return_value=SimpleNamespace(success=True))
    )
    owner._synthesize_agent_response = AsyncMock(return_value="Unexpected extra generation")

    async def stream(**kwargs):
        yield {"type": "agent_complete", "result": result}

    owner.tool_aware_agent.process_query_streaming = stream
    return owner


@pytest.mark.asyncio
@pytest.mark.parametrize("framework", ["legacy", "pydantic"])
async def test_failed_generation_is_never_stored_or_streamed_as_a_success(framework):
    result = {
        "answer": "Based on my search: " + "_" * 500,
        "success": False,
        "agent_error": "Gemini generation authentication failed.",
        "agent_framework": framework,
        "confidence": 0.7,
        "ai_provider": "gemini",
        "model_used": "synthetic-model",
        "tool_results": {"search_documents": {"documents": [{"content": "1\n\f"}]}},
    }
    owner = manager(result)
    sync = await owner._process_v3_sync(1, "Test", 1, datetime.now())
    assert sync["success"] is False
    assert sync["response"] == ""
    assert sync["metadata"]["confidence"] == 0
    events = [event async for event in owner._stream_v3_response(1, "Test", 1, datetime.now())]
    assert events[-1]["type"] == "error"
    assert events[-1]["metadata"]["confidence"] == 0
    assert not any(event["type"] in ("token", "complete") for event in events)
    owner.atomic_storage.store_message_pair.assert_not_awaited()
    owner._synthesize_agent_response.assert_not_awaited()


@pytest.mark.asyncio
async def test_short_framework_answer_is_preserved_without_raw_document_append_or_extra_call():
    result = {
        "answer": "Connected. What would you like to explore?",
        "success": True,
        "agent_framework": "pydantic",
        "agent_error": None,
        "tool_results": {"search_documents": {"documents": [{"content": "_" * 1000}]}},
    }
    owner = manager(result)
    sync = await owner._process_v3_sync(1, "Test", 1, datetime.now())
    assert sync["response"] == result["answer"]
    events = [event async for event in owner._stream_v3_response(1, "Test", 1, datetime.now())]
    assert (
        "".join(event["content"] for event in events if event["type"] == "token")
        == result["answer"]
    )
    owner._synthesize_agent_response.assert_not_awaited()


def test_framework_failure_with_partial_evidence_cannot_become_a_confident_fallback():
    owner = ToolAwareAgent.__new__(ToolAwareAgent)
    owner.llm = SimpleNamespace(provider="gemini", model_name="synthetic-model")
    owner._analyze_response_quality = Mock(return_value=None)
    owner._build_fallback_answer = Mock(return_value="Raw document dump")
    plan = AgentPlan("Test", "simple", [], confidence=0.7, error="Generation unavailable")
    result = owner._build_result_dict(
        plan,
        {"search_documents": {"documents": [{"content": "1"}]}},
        "Test",
        0,
        1,
        LongQueryResult(original_query="Test", processed_query="Test", was_processed=False),
        None,
        None,
    )
    assert result["success"] is False
    assert result["confidence"] == 0
    assert "Generation unavailable" in result["answer"]
    assert "Raw document dump" not in result["answer"]
    owner._build_fallback_answer.assert_not_called()


@pytest.mark.asyncio
async def test_legacy_response_synthesis_failure_cannot_return_the_original_document_dump(
    monkeypatch,
):
    import app.services.conversation.conversation_manager as module

    model = SimpleNamespace(provider="gemini", model_name="configured-gemini-model")
    factory = Mock(return_value=model)
    monkeypatch.setattr(module, "create_text_model", factory)
    monkeypatch.setattr(
        module,
        "generate_content",
        AsyncMock(side_effect=RuntimeError("API_KEY_INVALID secret-value")),
    )
    owner = ConversationManager.__new__(ConversationManager)
    with pytest.raises(RuntimeError, match="authentication failed") as error:
        await owner._synthesize_agent_response(
            "Test",
            {
                "answer": "Raw document dump",
                "reasoning_steps": [{"observation": "1\n\f"}],
            },
            "",
        )
    assert "secret-value" not in str(error.value)
    assert "Raw document dump" not in str(error.value)
    factory.assert_called_once_with("chat_response")
