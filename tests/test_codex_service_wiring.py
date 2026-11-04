"""Service routing tests. All text responses, Redis and database services are mocked."""

import importlib
import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(autouse=True)
def isolated_services(monkeypatch):
    # Import-time settings and graph singletons must never load developer secrets or connect.
    from pydantic_settings import BaseSettings

    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy:dummy@localhost:1/dummy")
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:1")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "dummy")
    monkeypatch.setattr(
        BaseSettings,
        "settings_customise_sources",
        classmethod(
            lambda cls, settings_cls, init_settings, env_settings,
            dotenv_settings, file_secret_settings: (init_settings, env_settings)
        ),
    )
    monkeypatch.setitem(
        sys.modules, "app.core.neo4j_config", SimpleNamespace(neo4j_db=MagicMock())
    )


@pytest.fixture
def text_model():
    model = MagicMock()
    model.provider = "codex"
    model.model_name = "synthetic-model"
    model.generate_content_async = AsyncMock(return_value=SimpleNamespace(text="Synthetic Answer"))
    return model


def mock_factory(monkeypatch, module, text_model):
    factory = MagicMock(return_value=text_model)
    monkeypatch.setattr(module, "create_text_model", factory)
    if hasattr(module, "resolve_provider"):
        monkeypatch.setattr(module, "resolve_provider", lambda *args: "codex")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return factory


def test_memory_generation_uses_selected_model_without_gemini_key(monkeypatch, text_model):
    module = importlib.import_module("app.services.memory.rolling_summarizer")
    factory = mock_factory(monkeypatch, module, text_model)
    text_model.generate_content.return_value = SimpleNamespace(
        text='{"summary":"Synthetic summary","key_points":["One fact"]}'
    )
    summarizer = module.RollingSummarizer()
    turn = module.ConversationTurn(
        message_id=42, role="user", content="Synthetic data", timestamp=datetime.now()
    )

    summary = summarizer.summarize_turn(None, [turn])

    assert summary.summary_text == "Synthetic summary"
    assert summary.covers_messages == (42, 42)
    assert summarizer.ai_provider == "codex"
    assert factory.call_args.args == ("memory_summary",)
    assert factory.call_args.kwargs["provider"] is None
    text_model.generate_content.assert_called_once()


def test_memory_fact_and_entity_extraction_use_same_selected_model(monkeypatch, text_model):
    module = importlib.import_module("app.services.memory.rolling_summarizer")
    mock_factory(monkeypatch, module, text_model)
    text_model.generate_content.side_effect = [
        SimpleNamespace(
            text='{"facts":[{"fact_type":"preference","fact_content":"Local",'
            '"confidence":0.9,"source_message_id":42}]}'
        ),
        SimpleNamespace(
            text='{"entities":[{"entity_type":"topic","entity_name":"Synthetic",'
            '"entity_data":{}}]}'
        ),
    ]
    summarizer = module.RollingSummarizer()
    turn = module.ConversationTurn(
        message_id=42, role="user", content="Synthetic data", timestamp=datetime.now()
    )

    assert summarizer.extract_facts([turn])[0].fact_content == "Local"
    assert summarizer.extract_entities([turn])[0].entity_name == "Synthetic"
    assert text_model.generate_content.call_count == 2


def test_memory_service_does_not_override_named_step(monkeypatch):
    module = importlib.import_module("app.services.memory.memory_service")
    monkeypatch.setenv("DEFAULT_AI_PROVIDER", "gemini")
    monkeypatch.setattr(module.redis, "Redis", MagicMock())
    summarizer = MagicMock()
    monkeypatch.setattr(module, "RollingSummarizer", summarizer)

    module.MemoryService()

    assert "ai_provider" not in summarizer.call_args.kwargs


@pytest.mark.asyncio
async def test_naming_awaits_selected_provider_without_gemini_key(monkeypatch, text_model):
    module = importlib.import_module("app.services.conversation.conversation_namer")
    factory = mock_factory(monkeypatch, module, text_model)
    namer = module.ConversationNamer()

    assert await namer.generate_name("Synthetic prompt") == "Synthetic Answer"
    assert factory.call_args.args == ("conversation_naming",)
    text_model.generate_content_async.assert_awaited_once()
    text_model.generate_content.assert_not_called()


@pytest.mark.asyncio
async def test_query_planning_awaits_selected_provider(monkeypatch, text_model):
    module = importlib.import_module("app.services.data_intelligence.query_planner")
    factory = mock_factory(monkeypatch, module, text_model)
    text_model.generate_content_async.return_value = SimpleNamespace(
        text='{"intent_type":"general","confidence":0.8,"plan":[]}'
    )
    planner = module.QueryPlanner(ai_provider="codex")

    plan = await planner.generate_plan("Synthetic prompt")

    assert plan.intent_type == "general"
    assert plan.confidence == 0.8
    assert planner.model_name == "synthetic-model"
    assert factory.call_args.args == ("query_planning",)
    assert factory.call_args.kwargs["provider"] == "codex"
    text_model.generate_content_async.assert_awaited_once()
    text_model.generate_content.assert_not_called()


@pytest.mark.asyncio
async def test_call_document_answers_await_selected_provider(monkeypatch, text_model):
    module = importlib.import_module("app.api.call_document_routes")
    factory = mock_factory(monkeypatch, module, text_model)
    monkeypatch.setattr(module, "_text_model", None)
    documents = MagicMock()
    documents.get_call_documents.return_value = {"cached": True}
    documents.search_call_chunks.return_value = [
        {"document_title": "Synthetic", "section_title": "Test", "chunk_text": "Synthetic data"}
    ]
    monkeypatch.setattr(module, "_get_call_doc_service", lambda: documents)

    response = await module.ask_call_question(
        "SYNTHETIC", module.CallQuestionRequest(question="Synthetic question")
    )

    assert response.answer == "Synthetic Answer"
    assert response.chunks_used == 1
    assert factory.call_args.args == ("call_document_summary",)
    text_model.generate_content_async.assert_awaited_once()
    text_model.generate_content.assert_not_called()


def test_call_history_expansion_uses_selected_provider(monkeypatch, text_model):
    module = importlib.import_module("app.services.tools.call_history")
    graph = importlib.import_module("app.services.data_intelligence.graph_service")
    monkeypatch.setattr(graph, "GraphSearchService", MagicMock())
    factory = mock_factory(monkeypatch, module, text_model)
    text_model.generate_content.return_value = SimpleNamespace(text='["synthetic", "related"]')

    tool = module.CallHistoryTool()

    assert tool._expand_keywords_with_ai("synthetic") == ["synthetic", "related"]
    assert factory.call_args.args == ("call_history",)
    text_model.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_call_history_async_inference_precedes_database_work(monkeypatch, text_model):
    module = importlib.import_module("app.services.tools.call_history")
    tool = module.CallHistoryTool.__new__(module.CallHistoryTool)
    tool._text_model = text_model
    text_model.generate_content_async.return_value = SimpleNamespace(
        text='["synthetic", "related"]'
    )
    analysis = MagicMock(return_value={"success": True})
    monkeypatch.setattr(tool, "analyze_history", analysis)

    assert await tool.analyze_history_async(
        expand_scope=True, keywords="synthetic"
    ) == {"success": True}
    assert analysis.call_args.kwargs["_expanded_keywords"] == ["synthetic", "related"]
    text_model.generate_content_async.assert_awaited_once()
    text_model.generate_content.assert_not_called()


@pytest.mark.asyncio
async def test_call_history_cancellation_reaches_inference(monkeypatch, text_model):
    import asyncio

    module = importlib.import_module("app.services.tools.call_history")
    tool = module.CallHistoryTool.__new__(module.CallHistoryTool)
    tool._text_model = text_model
    text_model.generate_content_async.side_effect = asyncio.CancelledError
    analysis = MagicMock()
    monkeypatch.setattr(tool, "analyze_history", analysis)

    with pytest.raises(asyncio.CancelledError):
        await tool.analyze_history_async(expand_scope=True, keywords="synthetic")

    analysis.assert_not_called()
