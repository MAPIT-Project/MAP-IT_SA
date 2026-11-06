"""Embedding evaluation uses fake SDK calls here, never a real key or endpoint."""

import os
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from tests.tool_scenarios.embeddings import EmbeddingAllowance, EmbeddingLimitExceeded
from tests.tool_scenarios.environment import isolated_settings
from tests.tool_scenarios.oracles import OraclePrerequisiteError


def owner():
    return SimpleNamespace(model_name="synthetic-embedding", embedding_dimension=3072)


def generate(instance, text):
    import google.generativeai as genai

    response = genai.embed_content(model=instance.model_name, content=text)
    return np.asarray(response["embedding"])


def test_embeddings_are_separately_capped_cached_and_never_retried():
    sdk = Mock(return_value={"embedding": [0.01] * 3072})
    budget = EmbeddingAllowance(1)
    first = budget.query(owner(), "consortium", generate, sdk)
    assert budget.query(owner(), "consortium", generate, sdk) is not first
    assert budget.snapshot()["cache_hits"] == 1
    sdk.assert_called_once()
    assert sdk.call_args.kwargs["request_options"] == {"timeout": 20, "retry": None}
    with pytest.raises(EmbeddingLimitExceeded):
        budget.query(owner(), "different question", generate, sdk)
    assert budget.snapshot()["attempted"] == 1
    assert budget.snapshot()["stopped"] is True


def test_failed_embedding_does_not_leak_sdk_diagnostics_or_trigger_another_call():
    sdk = Mock(return_value={"embedding": [0.0] * 3072})
    budget = EmbeddingAllowance(2)
    with pytest.raises(OraclePrerequisiteError, match="valid vector"):
        budget.query(owner(), "question", generate, sdk)
    with pytest.raises(OraclePrerequisiteError, match="no automatic retry"):
        budget.query(owner(), "different question", generate, sdk)
    assert sdk.call_count == 1


def test_optional_runtime_configuration_keeps_only_embedding_values(monkeypatch):
    import dotenv

    def load(path, override=False):
        os.environ.update(
            GOOGLE_EMBEDDING_API_KEY="dummy-embedding",
            OPENAI_API_KEY="dummy-paid",
            GEMINI_API_KEY="dummy-paid",
            BUZZ_SECRET="dummy-private",
        )

    monkeypatch.setattr(dotenv, "load_dotenv", load)
    with isolated_settings(embedding_env_file="dummy.env"):
        assert os.environ["GOOGLE_EMBEDDING_API_KEY"] == "dummy-embedding"
        assert os.environ["DEFAULT_AI_PROVIDER"] == "codex"
        assert "OPENAI_API_KEY" not in os.environ
        assert "GEMINI_API_KEY" not in os.environ
        assert "BUZZ_SECRET" not in os.environ


def test_default_settings_do_not_consume_runtime_credentials(monkeypatch):
    monkeypatch.setenv("GOOGLE_EMBEDDING_API_KEY", "dummy-inherited")
    with isolated_settings():
        assert "GOOGLE_EMBEDDING_API_KEY" not in os.environ
        assert os.environ["VECTOR_SEARCH_ENABLED"] == "false"
