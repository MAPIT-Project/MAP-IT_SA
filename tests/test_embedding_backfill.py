"""A failed embedding provider must never populate the search index with sentinels."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from scripts.reembed_funding_calls import reembed_nulls, validated_updates


def validator():
    return SimpleNamespace(
        validate_embedding=lambda emb: emb.shape == (3,)
        and bool(np.any(emb))
        and bool(np.all(np.isfinite(emb)))
    )


def test_valid_results_keep_source_identity_and_content_hash():
    calls = [{"id": 4, "content_hash": "original-source"}]
    result = validated_updates(calls, [np.array([0.1, 0.2, 0.3])], validator())
    assert result == [([0.1, 0.2, 0.3], 4, "original-source")]


@pytest.mark.parametrize("values", [[], [None], [np.zeros(3)], [np.ones(2)], [np.full(3, np.nan)]])
def test_failed_partial_or_invalid_batches_are_rejected(values):
    with pytest.raises(RuntimeError, match="no vectors.*saved"):
        validated_updates([{"id": 4, "content_hash": "original-source"}], values, validator())


@pytest.mark.asyncio
async def test_failure_does_not_commit_or_open_an_update_cursor():
    pool, conn = MagicMock(), MagicMock()
    pool.getconn.return_value = conn
    conn.cursor.return_value.fetchall.return_value = [
        {"id": 4, "content": "AI health", "content_hash": "h"}
    ]
    embedder = validator()
    embedder.generate_embeddings_batch = MagicMock(return_value=[np.zeros(3)])
    with (
        patch("scripts.reembed_funding_calls.SimpleConnectionPool", return_value=pool),
        patch("scripts.reembed_funding_calls.EmbeddingService", return_value=embedder),
    ):
        with pytest.raises(RuntimeError):
            await reembed_nulls()
    conn.commit.assert_not_called()
    assert conn.cursor.call_count == 1
    pool.closeall.assert_called_once()


@pytest.mark.asyncio
async def test_dry_run_makes_no_provider_request_or_updates():
    pool, conn = MagicMock(), MagicMock()
    pool.getconn.return_value = conn
    conn.cursor.return_value.fetchall.return_value = [
        {"id": 4, "content": "AI health", "content_hash": "h"}
    ]
    embedder = MagicMock()
    with (
        patch("scripts.reembed_funding_calls.SimpleConnectionPool", return_value=pool),
        patch("scripts.reembed_funding_calls.EmbeddingService", return_value=embedder),
    ):
        await reembed_nulls(dry_run=True)
    embedder.generate_embeddings_batch.assert_not_called()
    conn.commit.assert_not_called()
    pool.closeall.assert_called_once()
