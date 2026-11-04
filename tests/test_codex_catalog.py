"""Mocked CLI catalog/preflight tests. These never run inference or inspect auth stores."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.ai.codex import CodexError, CodexTextModel


def catalog_row(slug):
    return {
        "slug": slug,
        "priority": 3,
        "description": "Synthetic catalog entry",
        "shell_type": "unified_exec",
        "apply_patch_tool_type": "freeform",
        "multi_agent_version": "v2",
        "experimental_supported_tools": ["clock", "send_user_message_async"],
        "tool_mode": "code_mode_only",
        "node_repl_disabled": False,
        "supports_search_tool": True,
    }


def inert_prompt():
    return [{
        "type": "message",
        "role": "system",
        "tools": [{
            "type": "namespace",
            "name": "functions",
            "tools": [{"type": "function", "name": "request_user_input"}],
        }],
    }]


@pytest.fixture
def model():
    return CodexTextModel(SimpleNamespace(
        codex_enabled=True,
        codex_cli_path="synthetic-codex",
        codex_model=None,
        codex_timeout_seconds=10,
    ))


@pytest.mark.asyncio
async def test_catalog_sanitizes_capabilities_preserving_model_identity_and_default(
    model, tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", "/synthetic-original-home")
    monkeypatch.setenv("CODEX_HOME", "/synthetic-original-auth-store")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-private-value")
    rows = [catalog_row("synthetic-default"), catalog_row("synthetic-second")]
    # These fields are optional in the official bundled gpt-5.5 entry.
    rows[1].pop("multi_agent_version")
    rows[1].pop("tool_mode")
    capture = AsyncMock(side_effect=[
        (0, json.dumps({"models": rows}).encode(), b""),
        (0, json.dumps(inert_prompt()).encode(), b""),
    ])
    monkeypatch.setattr(model, "_capture", capture)

    path, instructions = await model._inference_catalog("/synthetic/codex", str(tmp_path))

    sanitized = json.loads(path.read_text())["models"]
    assert [row["slug"] for row in sanitized] == ["synthetic-default", "synthetic-second"]
    for before, after in zip(rows, sanitized, strict=True):
        assert after["priority"] == before["priority"]
        assert after["description"] == before["description"]
        assert after["shell_type"] == "disabled"
        assert after["apply_patch_tool_type"] is None
        assert after["multi_agent_version"] is None
        assert after["experimental_supported_tools"] == []
        assert after["tool_mode"] == "direct"
        assert after["node_repl_disabled"] is True
        assert after["supports_search_tool"] is False
    assert "You generate text for MAPIT" in instructions.read_text()
    assert capture.call_args_list[0].args[0] == [
        "/synthetic/codex", "debug", "models", "--bundled"
    ]
    dry_run = capture.call_args_list[1].args[0]
    assert dry_run[:3] == ["/synthetic/codex", "debug", "prompt-input"]
    assert dry_run[-1] == "MAPIT inference capability check. Do not invoke tools."
    assert all("--model" not in call.args[0] for call in capture.call_args_list)
    for call in capture.call_args_list:
        environment = call.kwargs["env"]
        assert environment["HOME"] == str(tmp_path / "catalog-home")
        assert environment["CODEX_HOME"] == environment["HOME"]
        assert "synthetic-private-value" not in environment.values()
        assert "/synthetic-original-auth-store" not in environment.values()
        assert set(environment) <= {"HOME", "CODEX_HOME", "PATH", "LANG", "LC_ALL"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw",
    [b"not JSON", b"{}", b'{"models":[]}', b'{"models":[{}]}', b'{"models":[null]}'],
)
async def test_missing_or_unknown_catalog_fails_before_inference(model, tmp_path, monkeypatch, raw):
    capture = AsyncMock(return_value=(0, raw, b"private diagnostic not propagated"))
    monkeypatch.setattr(model, "_capture", capture)

    with pytest.raises(CodexError, match="supported bundled model catalog"):
        await model._inference_catalog("/synthetic/codex", str(tmp_path))
    assert capture.await_count == 1


@pytest.mark.asyncio
async def test_missing_configured_model_fails_without_choosing_another(model, tmp_path, monkeypatch):
    model.model_name = "synthetic-not-in-catalog"
    capture = AsyncMock(return_value=(0, json.dumps({
        "models": [catalog_row("synthetic-default")]
    }).encode(), b""))
    monkeypatch.setattr(model, "_capture", capture)

    with pytest.raises(CodexError, match="Configured Codex model is absent"):
        await model._inference_catalog("/synthetic/codex", str(tmp_path))
    assert capture.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tools",
    [
        [{"type": "function", "name": "exec_command"}],
        [{"type": "namespace", "name": "functions", "tools": [{"type": "function", "name": "exec"}]}],
        [{"type": "namespace", "name": "collaboration", "tools": []}],
        [{"type": "namespace", "name": "mcp", "tools": []}],
    ],
)
async def test_dry_run_rejects_executable_or_unknown_tools(
    model, tmp_path, monkeypatch, tools
):
    capture = AsyncMock(side_effect=[
        (0, json.dumps({"models": [catalog_row("synthetic-default")]}).encode(), b""),
        (0, json.dumps([{"type": "message", "role": "system", "tools": tools}]).encode(), b""),
    ])
    monkeypatch.setattr(model, "_capture", capture)

    with pytest.raises(CodexError, match="exposed tools that cannot be isolated"):
        await model._inference_catalog("/synthetic/codex", str(tmp_path))
    assert capture.await_count == 2


@pytest.mark.asyncio
async def test_exec_uses_the_verified_catalog_and_trusted_instructions(model, tmp_path, monkeypatch):
    model.model_name = "synthetic-selected"
    capture = AsyncMock(side_effect=[
        (0, json.dumps({"models": [catalog_row(model.model_name)]}).encode(), b""),
        (0, json.dumps(inert_prompt()).encode(), b""),
    ])
    monkeypatch.setattr(model, "_capture", capture)
    catalog, instructions = await model._inference_catalog("/synthetic/codex", str(tmp_path))

    argv = model._command("/synthetic/codex", tmp_path / "answer", None, catalog, instructions)

    assert argv[argv.index("--model") + 1] == "synthetic-selected"
    overrides = {
        argv[i + 1].split("=", 1)[0]: argv[i + 1].split("=", 1)[1]
        for i, value in enumerate(argv) if value == "-c"
    }
    assert json.loads(overrides["model_catalog_json"]) == str(catalog)
    assert json.loads(overrides["model_instructions_file"]) == str(instructions)
    assert json.loads(overrides["features.code_mode.enabled"]) is False
    assert "danger-full-access" not in argv
    assert "--dangerously-bypass-hook-trust" not in argv
    assert 'model="synthetic-selected"' in capture.call_args_list[1].args[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("messages", "accepted"),
    [
        ([{"type": "message", "role": "system", "content": "Changed CLI tool shape"}], False),
        ([{"type": "message", "role": "system", "tools": []}], True),
        ([{"type": "message", "role": "system", "tools": None}], False),
    ],
)
async def test_dry_run_requires_an_explicit_tool_declaration(
    model, tmp_path, monkeypatch, messages, accepted
):
    monkeypatch.setattr(model, "_capture", AsyncMock(side_effect=[
        (0, json.dumps({"models": [catalog_row("synthetic-default")]}).encode(), b""),
        (0, json.dumps(messages).encode(), b""),
    ]))
    if accepted:
        await model._inference_catalog("/synthetic/codex", str(tmp_path))
    else:
        with pytest.raises(CodexError, match="exposed tools that cannot be isolated"):
            await model._inference_catalog("/synthetic/codex", str(tmp_path))
