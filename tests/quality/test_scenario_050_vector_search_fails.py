"""Vector timeouts return keyword results without waiting for a blocked worker."""

import asyncio
from datetime import datetime
from threading import Event
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from app.core.config import settings
from app.services.tools.similar_projects import SimilarProjectsTool


@pytest.fixture
def tool():
    # Construction normally discovers Neo4j. These tests supply every dependency.
    instance = SimilarProjectsTool.__new__(SimilarProjectsTool)
    instance._embedding_service = None
    instance._graph_service = None
    instance.db_url = None
    return instance


@pytest.fixture
def repository(monkeypatch):
    repository = Mock()
    record = SimpleNamespace(
        id=123,
        acronym="SYNTHETIC",
        title="Synthetic hydrogen project",
        objective="Research on hydrogen fuel cells",
        ec_contribution=1_000_000,
        start_date=datetime(2024, 1, 1),
        funding_scheme="RIA",
    )
    repository.search_projects.return_value = ([record], 1)
    monkeypatch.setattr(
        "app.services.data.cordis_repository.CordisProjectRepository",
        Mock(return_value=repository),
    )
    return repository


@pytest.mark.parametrize(
    "field", ["embedding_timeout", "vector_search_timeout", "graph_context_timeout"]
)
def test_timeouts_are_positive_settings(field):
    assert 0 < getattr(settings, field) <= 60


@pytest.mark.parametrize(
    "reason,message",
    [
        ("vector_search_timeout", "timed out"),
        ("embedding_service_unavailable", "embedding service unavailable"),
        ("embedding_generation_failed", "embedding generation failed"),
        ("unknown", "semantic search unavailable"),
    ],
)
def test_keyword_fallback_reports_reason_and_returns_repository_results(
    tool, repository, reason, message
):
    result = tool._get_keyword_fallback("hydrogen fuel cell research", None, None, 5, reason)
    assert result["success"] is True
    assert result["matches_found"] == 1
    assert result["similar_projects"][0]["cordis_id"] == "123"
    assert result["metadata"] == {
        "search_type": "keyword_fallback",
        "sources_used": ["keyword"],
        "fallback_reason": reason,
        "degraded": True,
    }
    assert message in result["message"].lower()
    repository.search_projects.assert_called_once()
    assert repository.search_projects.call_args.kwargs["sort_by"] == "relevance"
    assert repository.search_projects.call_args.kwargs["limit"] == 5


def test_keyword_fallback_keeps_filters(tool, repository):
    tool._get_keyword_fallback("hydrogen fuel cell research", "CL5", "RIA", 3)
    assert repository.search_projects.call_args.kwargs["filters"] == {
        "programme": "HORIZON",
        "action_type": "RIA",
    }


def test_keyword_fallback_returns_empty_results_without_crashing(tool, repository):
    repository.search_projects.return_value = ([], 0)
    result = tool._get_keyword_fallback("hydrogen research", None, None, 5)
    assert result["success"] is True
    assert result["matches_found"] == 0
    assert result["similar_projects"] == []


def test_keyword_fallback_reports_repository_failure(tool, repository):
    repository.search_projects.side_effect = RuntimeError("Synthetic unavailable database")
    result = tool._get_keyword_fallback("hydrogen research", None, None, 5)
    assert result["success"] is False
    assert result["metadata"]["degraded"] is True
    assert result["error"] == "Synthetic unavailable database"


@pytest.mark.parametrize("stage", ["embedding", "vector"])
def test_timeout_returns_before_worker_is_released(tool, monkeypatch, stage):
    started, release, finished = Event(), Event(), Event()

    def blocked(*args, **kwargs):
        started.set()
        try:
            release.wait(timeout=2)
            return []
        finally:
            finished.set()

    monkeypatch.setattr(
        settings, f"{stage}_timeout" if stage == "embedding" else "vector_search_timeout", 0.02
    )
    try:
        if stage == "embedding":
            service = SimpleNamespace(generate_embedding=blocked)
            result = tool._generate_embedding_with_timeout(service, "synthetic description")
            assert result is None
        else:
            tool._get_vector_results = blocked
            result = tool._get_vector_results_with_timeout(
                [0.1], None, None, None, None, None, 5, 0.3
            )
            assert result == ([], True)
        assert started.is_set()
        assert not finished.is_set(), "The caller waited for the timed-out worker"
    finally:
        release.set()
        assert finished.wait(timeout=1), "Test worker did not finish after release"


def test_embedding_errors_return_none(tool):
    service = SimpleNamespace(
        generate_embedding=Mock(side_effect=RuntimeError("Synthetic API error"))
    )
    assert tool._generate_embedding_with_timeout(service, "synthetic description") is None
    service.generate_embedding.assert_called_once_with("synthetic description", use_cache=False)


def test_successful_embedding_is_returned(tool):
    expected = np.array([0.1, 0.2])
    service = SimpleNamespace(generate_embedding=Mock(return_value=expected))
    assert tool._generate_embedding_with_timeout(service, "synthetic description") is expected


def test_successful_vector_search_is_not_marked_timed_out(tool):
    expected = [{"id": "synthetic", "similarity_score": 0.9}]
    tool._get_vector_results = Mock(return_value=expected)
    assert tool._get_vector_results_with_timeout([0.1], None, None, None, None, None, 5, 0.3) == (
        expected,
        False,
    )


@pytest.mark.parametrize(
    "embedding,reason",
    [
        (None, "embedding_service_unavailable"),
        (np.zeros(3), "embedding_generation_failed"),
    ],
)
def test_find_similar_degrades_to_keyword_results(tool, repository, embedding, reason):
    tool._get_embedding_service = Mock(return_value=None if embedding is None else object())
    tool._generate_embedding_with_timeout = Mock(return_value=embedding)
    result = tool.find_similar("hydrogen fuel cell research", limit=5)
    assert result["success"] is True
    assert result["metadata"]["fallback_reason"] == reason
    assert result["similar_projects"][0]["cordis_id"] == "123"


def test_hybrid_vector_timeout_uses_keyword_fallback(tool, repository):
    tool._get_vector_results_with_timeout = Mock(return_value=([], True))
    result = tool._find_similar_hybrid(
        "hydrogen fuel cell research",
        [0.1],
        None,
        None,
        None,
        None,
        None,
        None,
        5,
        0.3,
        True,
        True,
        [],
    )
    assert result["success"] is True
    assert result["metadata"]["fallback_reason"] == "vector_search_timeout"


@pytest.mark.asyncio
async def test_agent_timeout_uses_keyword_fallback():
    from concurrent.futures import TimeoutError as FuturesTimeoutError

    from app.services.agents.tool_aware_agent import ToolAwareAgent

    agent = ToolAwareAgent.__new__(ToolAwareAgent)
    selected_tool = MagicMock()
    selected_tool.find_similar.side_effect = FuturesTimeoutError()
    selected_tool._get_keyword_fallback.return_value = {
        "success": True,
        "metadata": {"fallback_reason": "agent_level_timeout", "degraded": True},
    }
    with patch(
        "app.services.tools.similar_projects.SimilarProjectsTool", return_value=selected_tool
    ):
        result = await agent._tool_get_similar_funded_projects(
            {"description": "synthetic hydrogen"}
        )
    assert result["metadata"]["fallback_reason"] == "agent_level_timeout"
    selected_tool._get_keyword_fallback.assert_called_once_with(
        description="synthetic hydrogen",
        cluster=None,
        action_type=None,
        limit=100,
        fallback_reason="agent_level_timeout",
    )


@pytest.mark.asyncio
async def test_agent_wait_is_cancellable_while_search_worker_is_blocked():
    from app.services.agents.tool_aware_agent import ToolAwareAgent

    agent = ToolAwareAgent.__new__(ToolAwareAgent)
    started, release, finished = Event(), Event(), Event()

    def blocked(**kwargs):
        started.set()
        try:
            release.wait(timeout=2)
            return {"success": True}
        finally:
            finished.set()

    selected_tool = MagicMock()
    selected_tool.find_similar.side_effect = blocked
    task = None
    try:
        with patch(
            "app.services.tools.similar_projects.SimilarProjectsTool", return_value=selected_tool
        ):
            task = asyncio.create_task(
                agent._tool_get_similar_funded_projects({"description": "synthetic"})
            )
            assert await asyncio.to_thread(started.wait, 1)
            assert not finished.is_set()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            selected_tool._get_keyword_fallback.assert_not_called()
    finally:
        release.set()
        if task is not None and not task.done():
            task.cancel()
        assert await asyncio.to_thread(finished.wait, 1)
