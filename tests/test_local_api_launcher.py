"""Local launcher tests use dummy settings and never load private files."""

import os

import pytest
from scripts.run_local_api import arguments, configure, local_database_url


@pytest.fixture(autouse=True)
def isolated_process_environment(monkeypatch):
    monkeypatch.setattr(os, "environ", os.environ.copy())


def test_local_url_preserves_database_and_authentication():
    assert (
        local_database_url(
            "postgresql://dummy:p%40ss@docker-db:5432/postgres?sslmode=disable", 54322
        )
        == "postgresql://dummy:p%40ss@127.0.0.1:54322/postgres?sslmode=disable"
    )


@pytest.mark.parametrize("value", ["", "https://example.invalid", "postgresql:///postgres"])
def test_invalid_database_url_diagnostic_has_no_input(value):
    with pytest.raises(ValueError) as error:
        local_database_url(value, 54322)
    assert str(error.value) == "DATABASE_URL must be a PostgreSQL URL for local-service overrides"


def test_codex_launch_uses_process_overrides_and_preserves_embedding_key(monkeypatch):
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda **kwargs: False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy:dummy@docker-db:5432/postgres")
    monkeypatch.setenv("GOOGLE_EMBEDDING_API_KEY", "dummy-embedding")
    args = arguments(
        [
            "--env-file",
            "dummy.env",
            "--provider",
            "codex",
            "--model",
            "gpt-6.1-sol",
            "--reasoning-effort",
            "high",
            "--local-services",
        ]
    )
    configure(args)
    assert os.environ["DEFAULT_AI_PROVIDER"] == "codex"
    assert os.environ["CODEX_ENABLED"] == "true"
    assert os.environ["CODEX_MODEL"] == "gpt-6.1-sol"
    assert os.environ["CODEX_REASONING_EFFORT"] == "high"
    assert os.environ["GOOGLE_EMBEDDING_API_KEY"] == "dummy-embedding"
    assert os.environ["DATABASE_URL"].endswith("127.0.0.1:54322/postgres")
    assert os.environ["REDIS_HOST"] == "127.0.0.1"
    assert os.environ["REDIS_PORT"] == "16379"


def test_antigravity_launch_uses_process_overrides(monkeypatch):
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda **kwargs: False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy:dummy@docker-db:5432/postgres")
    args = arguments(
        [
            "--env-file",
            "dummy.env",
            "--provider",
            "antigravity",
            "--model",
            "gemini-3.8-flash-high",
            "--reasoning-effort",
            "high",
            "--local-services",
        ]
    )
    configure(args)
    assert os.environ["DEFAULT_AI_PROVIDER"] == "antigravity"
    assert os.environ["ANTIGRAVITY_ENABLED"] == "true"
    assert os.environ["ANTIGRAVITY_MODEL"] == "gemini-3.8-flash-high"
    assert os.environ["ANTIGRAVITY_REASONING_EFFORT"] == "high"


def test_api_provider_selection_remains_available(monkeypatch):
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda **kwargs: False)
    monkeypatch.delenv("CODEX_ENABLED", raising=False)
    configure(
        arguments(["--env-file", "dummy.env", "--provider", "openai", "--model", "dummy-model"])
    )
    assert os.environ["DEFAULT_AI_PROVIDER"] == "openai"
    assert os.environ["OPENAI_MODEL"] == "dummy-model"
    assert "CODEX_ENABLED" not in os.environ


@pytest.mark.parametrize(
    "flags", [["--model", "dummy"], ["--provider", "gemini", "--reasoning-effort", "high"]]
)
def test_ambiguous_model_overrides_are_rejected(flags):
    with pytest.raises(SystemExit):
        arguments(["--env-file", "dummy.env", *flags])
