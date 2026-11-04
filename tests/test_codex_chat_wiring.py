"""Chat routing and SSE tests use mocked inference and storage, with no external services."""

import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.agents import query_preprocessing
from app.services.agents.tool_aware_agent import ToolAwareAgent
from app.services.conversation.conversation_manager import ConversationManager


def test_agent_initializes_each_generation_step(monkeypatch):
    import app.services.agents.tool_aware_agent as module

    calls = []

    def create(step, **kwargs):
        calls.append((step, kwargs))
        return SimpleNamespace(provider="codex", model_name=None)

    monkeypatch.setattr(module, "create_text_model", create)
    monkeypatch.setattr(module, "resolve_provider", lambda step: "codex")
    agent = ToolAwareAgent.__new__(ToolAwareAgent)
    agent._init_llm()
    assert [step for step, _ in calls] == [
        "chat_reasoning",
        "chat_reasoning",
        "chat_response",
        "query_preprocessing",
    ]
    agent._select_model_for_query("analysis", "Compare funding programmes")
    assert agent.llm is agent.llm_flash
    assert agent._active_model_name is None


def test_gemini_smart_routing_still_selects_pro(monkeypatch):
    import app.services.agents.tool_aware_agent as module

    monkeypatch.setattr(module, "resolve_provider", lambda step: "gemini")
    agent = ToolAwareAgent.__new__(ToolAwareAgent)
    agent.smart_model_routing = True
    agent.llm_flash = SimpleNamespace(provider="gemini", model_name="flash")
    agent.llm_pro = SimpleNamespace(provider="gemini", model_name="pro")
    agent.flash_model_name = "flash"
    agent.pro_model_name = "pro"
    agent._select_model_for_query("analysis", "Compare funding programmes")
    assert agent.llm is agent.llm_pro
    agent._select_model_for_query("simple", "What is a grant?")
    assert agent.llm is agent.llm_flash


@pytest.mark.asyncio
async def test_async_preprocessing_awaits_model(monkeypatch):
    monkeypatch.setattr(query_preprocessing.settings, "long_query_threshold", 20)
    model = SimpleNamespace(
        generate_content_async=AsyncMock(
            return_value=SimpleNamespace(
                text='{"intent": "find grants", "processed_query": "Find hydrogen grants"}'
            )
        )
    )
    result = await query_preprocessing.preprocess_long_query_async(
        "Find hydrogen grants for our research project in Germany.", model
    )
    assert result.processed_query == "Find hydrogen grants"
    model.generate_content_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_response_synthesis_uses_response_step(monkeypatch):
    import app.services.agents.tool_aware_agent as module

    response_model = SimpleNamespace(provider="codex", model_name="reported-model")
    inference = AsyncMock(return_value=SimpleNamespace(text="A grounded answer. " * 10))
    monkeypatch.setattr(module, "generate_content", inference)
    agent = ToolAwareAgent.__new__(ToolAwareAgent)
    agent.llm = SimpleNamespace(provider="gemini", model_name="gemini-model")
    agent.llm_response = response_model
    agent._format_tool_result_summary = MagicMock(return_value="Three funded projects")
    answer = await agent._llm_synthesize_results("Which projects?", {"projects": {}})
    assert answer
    assert inference.await_args.args[0] is response_model
    assert agent._generation_metadata() == {
        "ai_provider": "codex",
        "model_used": "reported-model",
        "reasoning_provider": "gemini",
        "reasoning_model": "gemini-model",
        "response_provider": "codex",
        "response_model": "reported-model",
    }


def manager_with_mocked_agent():
    manager = ConversationManager.__new__(ConversationManager)
    result = {
        "answer": "**Hydrogen projects**: This synthetic response lists three funded projects.",
        "ai_provider": "codex",
        "model_used": "reported-model",
        "sources_used": [],
        "tool_results": {},
    }
    manager.tool_aware_agent = SimpleNamespace(process_query=AsyncMock(return_value=result))
    manager._get_recent_messages_simple = MagicMock(return_value=[{"role": "user", "content": "Hi"}])
    manager._format_conversation_for_agent = MagicMock(return_value="Previous conversation")
    manager._add_to_memory_only = MagicMock()
    manager.atomic_storage = SimpleNamespace(
        store_message_pair=AsyncMock(return_value=SimpleNamespace(success=True))
    )
    return manager, result


@pytest.mark.asyncio
async def test_chat_storage_and_result_preserve_codex_metadata():
    manager, _ = manager_with_mocked_agent()
    response = await manager._process_v3_sync(1, "Synthetic question", 1, datetime.now())
    assert response["metadata"]["ai_provider"] == "codex"
    assert response["metadata"]["model_used"] == "reported-model"
    stored = manager.atomic_storage.store_message_pair.await_args.kwargs["assistant_metadata"]
    assert stored["ai_provider"] == "codex"
    assert stored["model_used"] == "reported-model"


@pytest.mark.asyncio
async def test_stream_preserves_token_and_complete_contract():
    manager, result = manager_with_mocked_agent()

    async def agent_stream(**kwargs):
        yield {"type": "agent_thinking", "content": "Synthetic reasoning"}
        yield {"type": "agent_complete", "result": result}

    manager.tool_aware_agent.process_query_streaming = agent_stream
    events = [
        event
        async for event in manager._stream_v3_response(
            1, "Synthetic question", 1, datetime.now()
        )
    ]
    assert "".join(event["content"] for event in events if event["type"] == "token") == result[
        "answer"
    ]
    complete = events[-1]
    assert complete["type"] == "complete"
    assert complete["ai_provider"] == "codex"
    assert complete["metadata"]["ai_provider"] == "codex"
    assert complete["metadata"]["streaming_mode"] == "completed_message_chunks"


@pytest.mark.asyncio
async def test_stream_close_cancels_reasoning_task():
    agent = ToolAwareAgent.__new__(ToolAwareAgent)
    agent._handle_show_more_request = MagicMock(return_value=None)
    agent._preprocess_query = AsyncMock(
        return_value=("query", "", None, None, SimpleNamespace(was_processed=False), "query")
    )
    agent._extract_structured_memory = MagicMock(return_value={})
    agent._init_plan_and_model = MagicMock(return_value=object())
    agent._start_speculation = AsyncMock()
    cancelled = asyncio.Event()

    async def reasoning(**kwargs):
        try:
            await kwargs["event_callback"]({"type": "agent_thinking", "content": "waiting"})
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    agent._execute_react_loop = reasoning
    stream = agent.process_query_streaming("query")
    assert (await anext(stream))["type"] == "agent_thinking"
    await stream.aclose()
    assert cancelled.is_set()


@pytest.fixture
def mocked_routes(monkeypatch):
    import importlib

    import app.services.analytics as analytics
    import app.services.conversation.conversation_manager as manager_module
    from app.services.ai import factory

    monkeypatch.setattr(manager_module, "ConversationManager", MagicMock())
    monkeypatch.setattr(analytics, "get_conversation_analytics_service", MagicMock())
    routes = importlib.import_module("app.api.conversation_routes_v3")
    monkeypatch.setattr(routes, "analytics_service", MagicMock())
    monkeypatch.setattr(routes.analytics_service, "log_conversation_async", AsyncMock())
    monkeypatch.setattr(factory.settings, "default_ai_provider", "gemini")
    monkeypatch.setattr(factory.settings, "ai_step_providers", {})
    monkeypatch.setattr(factory.settings, "codex_enabled", True)
    return routes


@pytest.mark.asyncio
async def test_request_provider_is_scoped_to_nonstream_request(mocked_routes, monkeypatch):
    from app.services.ai.factory import resolve_provider

    captured = []

    async def process(**kwargs):
        captured.append(resolve_provider("chat_reasoning"))
        return {"response": "Synthetic answer", "metadata": {"ai_provider": captured[-1]}}

    monkeypatch.setattr(
        mocked_routes, "conversation_manager", SimpleNamespace(process_message_v3=process)
    )
    request = mocked_routes.MessageRequest(message="Synthetic question", ai_provider="codex")
    response = await mocked_routes.send_message(1, request)
    assert captured == ["codex"]
    assert response.metadata["ai_provider"] == "codex"
    assert resolve_provider("chat_reasoning") == "gemini"


@pytest.mark.asyncio
async def test_request_provider_stays_scoped_while_streaming(mocked_routes, monkeypatch):
    from app.services.ai.factory import resolve_provider

    captured = []

    async def stream():
        captured.append(resolve_provider("chat_reasoning"))
        yield {"type": "token", "content": "Synthetic answer"}
        captured.append(resolve_provider("chat_response"))
        yield {"type": "complete", "metadata": {"ai_provider": captured[-1]}}

    async def process(**kwargs):
        captured.append(resolve_provider("query_preprocessing"))
        return stream()

    monkeypatch.setattr(
        mocked_routes, "conversation_manager", SimpleNamespace(process_message_v3=process)
    )
    request = mocked_routes.MessageRequest(message="Synthetic question", ai_provider="codex")
    response = await mocked_routes.send_message_stream(1, request)
    events = [event async for event in response.body_iterator]
    assert captured == ["codex", "codex", "codex"]
    assert '"type": "token"' in events[0]
    assert '"type": "complete"' in events[1]
    assert resolve_provider("chat_reasoning") == "gemini"


@pytest.mark.asyncio
async def test_concurrent_requests_keep_separate_metadata_from_child_tasks(monkeypatch):
    from app.services.ai import factory

    monkeypatch.setattr(factory.settings, "default_ai_provider", "gemini")
    monkeypatch.setattr(factory.settings, "ai_step_providers", {})
    monkeypatch.setattr(factory.settings, "codex_enabled", True)
    agent = ToolAwareAgent.__new__(ToolAwareAgent)
    agent.llm = factory.create_text_model("chat_reasoning")
    agent.llm_response = factory.create_text_model("chat_response")
    ready = []
    both_ready = asyncio.Event()

    async def request(provider):
        with factory.provider_scope(provider):
            agent._reset_generation_metadata()

            async def child_reasoning():
                # These responses stand in for two completed inference jobs.
                agent._record_generation(
                    "reasoning",
                    agent.llm,
                    SimpleNamespace(provider=provider, model_name=f"{provider}-reasoning-result"),
                )
                if provider == "codex":
                    agent._record_generation(
                        "response",
                        agent.llm_response,
                        SimpleNamespace(provider=provider, model_name="codex-response-result"),
                    )
                ready.append(provider)
                if len(ready) == 2:
                    both_ready.set()
                await both_ready.wait()

            await asyncio.create_task(child_reasoning())
            return agent._generation_metadata()

    codex, gemini = await asyncio.gather(request("codex"), request("gemini"))
    assert codex["ai_provider"] == "codex"
    assert codex["reasoning_model"] == "codex-reasoning-result"
    assert codex["response_model"] == "codex-response-result"
    assert gemini["ai_provider"] == "gemini"
    assert gemini["model_used"] == "gemini-reasoning-result"
    assert "response_provider" not in gemini
