"""Codex adapter tests use a synthetic CLI executable; no inference or APIs are called."""

import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.ai import factory
from app.services.ai.codex import CodexError, CodexTextModel
from app.services.ai.structured import codex_output_schema, omit_optional_nulls, validate_json
from app.services.ai.types import TextResponse


@pytest.mark.asyncio
@pytest.mark.parametrize("reference", ["$ref", "$dynamicRef", "$recursiveRef"])
async def test_external_schema_references_fail_before_inference(fake_cli, reference):
    cli = fake_cli()
    with pytest.raises(ValueError, match="External JSON schema references are unsupported"):
        await cli.model.generate_content_async(
            "Synthetic prompt",
            generation_config={"response_schema": {reference: "https://example.invalid/schema"}},
        )
    assert not cli.observations.exists()


@pytest.fixture
def local_settings(monkeypatch):
    config = Settings(
        _env_file=None,
        database_url="postgresql://dummy:dummy@localhost:1/dummy",
        supabase_url="http://localhost:1",
        supabase_service_key="dummy",
        default_ai_provider="gemini",
        ai_step_providers={},
        codex_enabled=True,
        codex_model=None,
        codex_timeout_seconds=5,
        gemini_api_key="dummy-gemini",
        openai_api_key="dummy-openai",
        openrouter_api_key="dummy-router",
    )
    monkeypatch.setattr(factory, "settings", config)
    return config


@pytest.fixture
def fake_cli(tmp_path, local_settings):
    """A fake CLI exercises OS subprocess handling, stdin and temporary files."""
    roots = []

    def create(mode="success", answer="Synthetic answer", model_event=True):
        root = tmp_path / str(len(roots))
        root.mkdir()
        roots.append(root)
        script = root / "fake-codex"
        observation = root / "observations.jsonl"
        pids = root / "pids.json"
        script.write_text(
            f"#!{sys.executable}\n"
            "import json, os, subprocess, sys, time\n"
            "from pathlib import Path\n"
            f"MODE = {mode!r}\nANSWER = {answer!r}\n"
            f"OBSERVATION = Path({str(observation)!r})\n"
            f"PIDS = Path({str(pids)!r})\n"
            f"FLAGS = {' '.join(CodexTextModel._required_flags)!r}\n"
            "args = sys.argv[1:]\n"
            "if args == ['debug', 'models', '--bundled']:\n"
            "    rows = [{'slug': slug, 'shell_type': 'unified_exec', 'apply_patch_tool_type': 'freeform',\n"
            "             'multi_agent_version': 'v2', 'experimental_supported_tools': ['web_search'],\n"
            "             'tool_mode': 'code_mode', 'node_repl_disabled': False, 'supports_search_tool': True}\n"
            "            for slug in ['synthetic-model', 'configured-synthetic-model']]\n"
            "    print(json.dumps({'models': rows}))\n"
            "    sys.exit(0)\n"
            "if args[:2] == ['debug', 'prompt-input']:\n"
            "    print(json.dumps([{'type': 'message', 'role': 'tool', 'tools': [\n"
            "        {'type': 'namespace', 'name': 'functions', 'tools': [\n"
            "            {'type': 'function', 'name': 'request_user_input'}]}]}]))\n"
            "    sys.exit(0)\n"
            "if args == ['exec', '--help']:\n"
            "    print('old cli' if MODE == 'old-cli' else FLAGS)\n"
            "    sys.exit(0)\n"
            "if args == ['login', 'status']:\n"
            "    print('Logged in using API key' if MODE == 'api-key-login' else 'Logged in using ChatGPT')\n"
            "    sys.exit(1 if MODE == 'logged-out' else 0)\n"
            "prompt = sys.stdin.read()\n"
            "record = {'argv': args, 'cwd': os.getcwd(), 'env': dict(os.environ), 'prompt': prompt}\n"
            "if '--output-schema' in args:\n"
            "    record['schema'] = json.loads(Path(args[args.index('--output-schema') + 1]).read_text())\n"
            "with OBSERVATION.open('a') as output:\n"
            "    output.write(json.dumps(record) + '\\n')\n"
            "if MODE in ('hang', 'leave-child'):\n"
            "    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
            "    PIDS.write_text(json.dumps([os.getpid(), child.pid]))\n"
            "    if MODE == 'hang':\n"
            "        time.sleep(60)\n"
            "if MODE == 'failure':\n"
            "    sys.stderr.write('SYNTHETIC_PRIVATE_DIAGNOSTIC ' + prompt)\n"
            "    sys.exit(7)\n"
            "if MODE != 'missing-output':\n"
            "    Path(args[args.index('--output-last-message') + 1]).write_text(ANSWER)\n"
            "print('non-json diagnostic line')\n"
            + (
                "print(json.dumps({'type': 'thread.started', 'model': 'synthetic-model'}))\n"
                if model_event else ""
            )
            + "print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 3, 'output_tokens': 2}}))\n"
            "if MODE == 'tool':\n"
            "    print(json.dumps({'type': 'item.completed', 'item': {'type': 'command_execution'}}))\n",
            encoding="utf-8",
        )
        script.chmod(0o700)
        config = local_settings.model_copy(update={"codex_cli_path": str(script)})
        model = CodexTextModel(config)
        return SimpleNamespace(model=model, executable=script, observations=observation, pids=pids)

    return create


def records(cli):
    return [json.loads(line) for line in cli.observations.read_text().splitlines()]


def assert_job_cleaned(cli):
    for record in records(cli):
        cwd = Path(record["cwd"])
        assert cwd.name.startswith("mapit-codex-")
        assert not cwd.exists(), "Job temporary directory was left behind"


def process_stopped(pid):
    # A killed orphan may remain a zombie briefly until the host reaps it.
    stat = Path(f"/proc/{pid}/stat")
    if stat.exists():
        try:
            return stat.read_text().split()[2] == "Z"
        except FileNotFoundError:
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


async def wait_for_pids(cli):
    async with asyncio.timeout(3):
        while not cli.pids.exists():
            await asyncio.sleep(0.01)
    return json.loads(cli.pids.read_text())


async def assert_processes_stopped(pids):
    async with asyncio.timeout(3):
        while not all(process_stopped(pid) for pid in pids):
            await asyncio.sleep(0.01)


def test_sync_inference_uses_stdin_safe_arguments_and_clean_environment(fake_cli, monkeypatch):
    cli = fake_cli()
    for name in (
        "OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "BUZZ_SECRET",
        "CODEX_API_KEY", "HTTP_PROXY", "LD_PRELOAD", "BASH_ENV", "NODE_OPTIONS",
    ):
        monkeypatch.setenv(name, "synthetic-sensitive-value")
    monkeypatch.setenv("HOME", "/synthetic-home")
    monkeypatch.setenv("CODEX_HOME", "/synthetic-codex-home")
    prompt = "Synthetic prompt with $(touch should-never-execute) and `shell syntax`"

    response = cli.model.generate_content(prompt)

    assert response == TextResponse(
        "Synthetic answer", "codex", "synthetic-model", {"input_tokens": 3, "output_tokens": 2}
    )
    record = records(cli)[0]
    argv = record["argv"]
    assert record["prompt"] == prompt
    assert prompt not in argv
    assert argv[-1] == "-"
    assert argv[argv.index("--sandbox") + 1] == "read-only"
    for flag in ("--ignore-user-config", "--ignore-rules", "--ephemeral", "--skip-git-repo-check"):
        assert flag in argv
    assert "--yolo" not in argv
    assert "danger-full-access" not in argv
    assert "--dangerously-bypass-approvals-and-sandbox" not in argv
    overrides = {
        argv[i + 1].split("=", 1)[0]: argv[i + 1].split("=", 1)[1]
        for i, value in enumerate(argv) if value == "-c"
    }
    assert json.loads(overrides["approval_policy"]) == "never"
    assert json.loads(overrides["web_search"]) == "disabled"
    assert overrides["mcp_servers"] == "{}"
    assert json.loads(overrides["project_doc_max_bytes"]) == 0
    assert json.loads(overrides["features.shell_tool"]) is False
    assert json.loads(overrides["features.unified_exec"]) is False
    assert json.loads(overrides["shell_environment_policy.inherit"]) == "none"
    assert set(record["env"]) <= {"HOME", "PATH", "CODEX_HOME", "LANG", "LC_ALL", "LC_CTYPE"}
    assert "synthetic-sensitive-value" not in record["env"].values()
    assert record["env"]["HOME"] == "/synthetic-home"
    assert_job_cleaned(cli)


@pytest.mark.asyncio
async def test_async_inference_reports_completed_message_chunk(fake_cli):
    cli = fake_cli()

    response = await cli.model.generate_content_async("Synthetic async prompt")
    stream = await cli.model.generate_content_async("Synthetic stream prompt", stream=True)
    chunks = [chunk async for chunk in stream]

    assert response.text == "Synthetic answer"
    assert [chunk.text for chunk in chunks] == ["Synthetic answer"]
    assert chunks[0].provider == "codex"
    assert_job_cleaned(cli)


def test_sync_stream_is_one_completed_message(fake_cli):
    cli = fake_cli()

    chunks = list(cli.model.generate_content("Synthetic stream prompt", stream=True))

    assert [chunk.text for chunk in chunks] == ["Synthetic answer"]
    assert_job_cleaned(cli)


def test_model_can_use_cli_default_without_invented_model_id(fake_cli):
    cli = fake_cli(model_event=False)

    response = cli.model.generate_content("Synthetic prompt")

    assert "--model" not in records(cli)[0]["argv"]
    assert response.model_name is None


def test_explicit_model_is_forwarded_and_reported_model_is_preserved(fake_cli):
    cli = fake_cli()
    cli.model.model_name = "configured-synthetic-model"

    response = cli.model.generate_content("Synthetic prompt")

    argv = records(cli)[0]["argv"]
    assert argv[argv.index("--model") + 1] == "configured-synthetic-model"
    assert response.model_name == "synthetic-model"


@pytest.mark.asyncio
async def test_schema_is_forwarded_and_result_validated(fake_cli):
    cli = fake_cli(answer='{"ok":true}')
    schema = {
        "type": "object", "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"], "additionalProperties": False,
    }

    response = await cli.model.generate_content_async(
        "Synthetic JSON prompt", generation_config={"response_schema": schema}
    )

    assert json.loads(response.text) == {"ok": True}
    assert records(cli)[0]["schema"] == schema
    assert_job_cleaned(cli)


@pytest.mark.parametrize(
    "answer,config,message",
    [
        ("invalid JSON", {"response_mime_type": "application/json"}, "not valid JSON"),
        ('{"ok":"wrong"}', {"response_schema": {
            "type": "object", "properties": {"ok": {"type": "boolean"}}
        }}, "does not match"),
    ],
)
def test_structured_output_rejects_invalid_results(fake_cli, answer, config, message):
    cli = fake_cli(answer=answer)

    with pytest.raises(ValueError, match=message):
        cli.model.generate_content("Synthetic JSON prompt", generation_config=config)

    assert_job_cleaned(cli)


def test_json_mode_without_schema_adds_json_instruction(fake_cli):
    cli = fake_cli(answer='["synthetic"]')
    cli.model.generate_content(
        "Synthetic JSON prompt", generation_config={"response_mime_type": "application/json"}
    )

    record = records(cli)[0]
    assert record["prompt"].startswith("Return valid JSON only.")
    assert "--output-schema" not in record["argv"]


def test_json_validation_rejects_external_schema_references():
    with pytest.raises(ValueError, match="External JSON schema references"):
        validate_json("{}", {"$ref": "https://synthetic.invalid/schema.json"})


@pytest.mark.parametrize("mode,message", [
    ("failure", "exited with status 7"),
    ("missing-output", "missing or oversized"),
    ("tool", "tool operation"),
])
def test_subprocess_and_output_failures_are_redacted_and_cleaned(fake_cli, mode, message):
    cli = fake_cli(mode=mode)

    with pytest.raises(CodexError, match=message) as error:
        cli.model.generate_content("SYNTHETIC_PRIVATE_PROMPT")

    assert "SYNTHETIC_PRIVATE_PROMPT" not in str(error.value)
    assert "SYNTHETIC_PRIVATE_DIAGNOSTIC" not in str(error.value)
    assert len(str(error.value)) < 500
    assert_job_cleaned(cli)


@pytest.mark.parametrize("answer,limit,message", [
    ("   ", 4096, "empty final"),
    ("x" * 8192, 4096, "oversized"),
], ids=["empty", "oversized"])
def test_empty_and_oversized_outputs_fail(fake_cli, monkeypatch, answer, limit, message):
    cli = fake_cli(answer=answer)
    cli.model._max_output_bytes = limit
    monkeypatch.setattr(cli.model, "check_available", AsyncMock(return_value=str(cli.executable)))

    with pytest.raises(CodexError, match=message):
        cli.model.generate_content("Synthetic prompt")

    assert_job_cleaned(cli)


@pytest.mark.parametrize("mode,message", [
    ("old-cli", "required isolation flags"),
    ("logged-out", "codex login"),
    ("api-key-login", "ChatGPT CLI login"),
])
@pytest.mark.asyncio
async def test_preflight_rejects_unsupported_cli_or_login(fake_cli, mode, message):
    cli = fake_cli(mode=mode)

    with pytest.raises(CodexError, match=message):
        await cli.model.generate_content_async("Synthetic prompt")

    assert not cli.observations.exists(), "Inference must not start after failed preflight"


@pytest.mark.asyncio
async def test_missing_executable_has_actionable_error(local_settings, tmp_path):
    local_settings.codex_cli_path = str(tmp_path / "does-not-exist")
    model = CodexTextModel(local_settings)

    with pytest.raises(CodexError, match="Install it and check CODEX_CLI_PATH"):
        await model.generate_content_async("Synthetic prompt")

    # Also cover an executable disappearing between resolution and process creation.
    with pytest.raises(CodexError, match="CLI not found"):
        await model._capture([local_settings.codex_cli_path], str(tmp_path))


@pytest.mark.asyncio
async def test_executable_permission_error_is_actionable(local_settings, tmp_path):
    executable = tmp_path / "not-executable"
    executable.write_text("synthetic")
    model = CodexTextModel(local_settings)

    with pytest.raises(CodexError, match="executable permissions"):
        await model._capture([str(executable)], str(tmp_path))


@pytest.mark.asyncio
async def test_timeout_kills_entire_process_group_and_removes_job(fake_cli, monkeypatch):
    cli = fake_cli(mode="hang")
    cli.model.timeout = 0.3
    monkeypatch.setattr(cli.model, "check_available", AsyncMock(return_value=str(cli.executable)))

    with pytest.raises(CodexError, match="CODEX_TIMEOUT_SECONDS"):
        await cli.model.generate_content_async("Synthetic timeout prompt")

    await assert_processes_stopped(json.loads(cli.pids.read_text()))
    assert_job_cleaned(cli)


@pytest.mark.asyncio
async def test_cancellation_kills_entire_process_group_and_removes_job(fake_cli, monkeypatch):
    cli = fake_cli(mode="hang")
    monkeypatch.setattr(cli.model, "check_available", AsyncMock(return_value=str(cli.executable)))
    task = asyncio.create_task(cli.model.generate_content_async("Synthetic cancellation prompt"))
    pids = await wait_for_pids(cli)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    await assert_processes_stopped(pids)
    assert_job_cleaned(cli)


@pytest.mark.asyncio
async def test_cancellation_during_spawn_does_not_orphan_process(fake_cli, monkeypatch):
    cli = fake_cli(mode="hang")
    monkeypatch.setattr(cli.model, "check_available", AsyncMock(return_value=str(cli.executable)))
    real_spawn = asyncio.create_subprocess_exec
    spawned = asyncio.Event()
    release = asyncio.Event()
    job = {}

    async def delayed_spawn(*args, **kwargs):
        process = await real_spawn(*args, **kwargs)
        job.update(pid=process.pid, cwd=kwargs["cwd"])
        spawned.set()
        await release.wait()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed_spawn)
    task = asyncio.create_task(cli.model.generate_content_async("Synthetic spawn prompt"))
    await asyncio.wait_for(spawned.wait(), timeout=3)
    task.cancel()
    release.set()

    with pytest.raises(asyncio.CancelledError):
        await task

    await assert_processes_stopped([job["pid"]])
    assert not Path(job["cwd"]).exists()


@pytest.mark.asyncio
async def test_success_also_kills_descendants_left_by_cli(fake_cli):
    cli = fake_cli(mode="leave-child")

    response = await cli.model.generate_content_async("Synthetic prompt")

    assert response.text == "Synthetic answer"
    await assert_processes_stopped(json.loads(cli.pids.read_text()))
    assert_job_cleaned(cli)


@pytest.mark.asyncio
async def test_concurrent_jobs_use_distinct_temporary_directories(fake_cli):
    cli = fake_cli()

    responses = await asyncio.gather(*(
        cli.model.generate_content_async(f"Synthetic prompt {i}") for i in range(3)
    ))

    assert len({record["cwd"] for record in records(cli)}) == 3
    assert [response.text for response in responses] == ["Synthetic answer"] * 3
    assert_job_cleaned(cli)


@pytest.mark.asyncio
async def test_sync_api_rejects_running_event_loop(fake_cli):
    cli = fake_cli()

    with pytest.raises(RuntimeError, match="generate_content_async"):
        cli.model.generate_content("Synthetic prompt")

    assert not cli.observations.exists()


@pytest.mark.asyncio
async def test_non_string_prompts_rejected_before_start(fake_cli, monkeypatch):
    cli = fake_cli()
    preflight = AsyncMock()
    monkeypatch.setattr(cli.model, "check_available", preflight)

    with pytest.raises(TypeError, match="string prompt"):
        await cli.model.generate_content_async(["Synthetic prompt"])

    preflight.assert_not_called()


def test_routing_precedence_and_scope_reset(local_settings):
    local_settings.ai_step_providers = {"chat_reasoning": "codex", "memory_summary": "gemini"}

    assert factory.resolve_provider("chat_reasoning") == "codex"
    assert factory.resolve_provider("proposal_generation") == "gemini"
    with factory.provider_scope("openai"):
        assert factory.resolve_provider("chat_reasoning") == "openai"
        assert factory.resolve_provider("chat_reasoning", "openrouter") == "openrouter"
        with factory.provider_scope("gemini"):
            assert factory.resolve_provider("chat_reasoning") == "gemini"
        assert factory.resolve_provider("chat_reasoning") == "openai"
    assert factory.resolve_provider("chat_reasoning") == "codex"
    assert factory.resolve_provider("memory_summary") == "gemini"


@pytest.mark.parametrize("provider", ["unknown", "", "CODEX"])
def test_unsupported_provider_fails_clearly(local_settings, provider):
    with pytest.raises(ValueError, match="Unsupported AI provider"):
        factory.resolve_provider("chat_reasoning", provider)


def test_unsupported_step_and_disabled_codex_fail_clearly(local_settings):
    with pytest.raises(ValueError, match="Unsupported AI step"):
        factory.resolve_provider("invented-step")
    local_settings.codex_enabled = False
    with pytest.raises(ValueError, match="CODEX_ENABLED"):
        factory.resolve_provider("chat_reasoning", "codex")
    with pytest.raises(ValueError, match="CODEX_ENABLED"), factory.provider_scope("codex"):
        pass
    with pytest.raises(CodexError, match="CODEX_ENABLED"):
        CodexTextModel(local_settings)


def test_settings_validate_provider_and_step_names():
    required = {
        "database_url": "postgresql://dummy:dummy@localhost:1/dummy",
        "supabase_url": "http://localhost:1", "supabase_service_key": "dummy",
    }
    with pytest.raises(ValidationError):
        Settings(_env_file=None, default_ai_provider="invented", **required)
    with pytest.raises(ValidationError, match="Unknown AI steps"):
        Settings(_env_file=None, ai_step_providers={"invented-step": "codex"}, **required)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ai_step_providers={"memory_summary": "invented"}, **required)
    assert Settings(_env_file=None, **required).default_ai_provider == "gemini"
    assert Settings(_env_file=None, **required).codex_enabled is False


class SyntheticModel:
    def __init__(self, provider):
        self.provider = provider
        self.model_name = f"synthetic-{provider}"

    def generate_content(self, prompt, **kwargs):
        return TextResponse(prompt, self.provider, self.model_name)

    async def generate_content_async(self, prompt, **kwargs):
        await asyncio.sleep(0)
        return self.generate_content(prompt, **kwargs)


@pytest.mark.asyncio
async def test_cached_model_routes_concurrent_request_scopes_independently(local_settings, monkeypatch):
    monkeypatch.setattr(factory, "CodexTextModel", lambda config: SyntheticModel("codex"))
    monkeypatch.setattr(factory, "APITextModel", lambda provider, *args: SyntheticModel(provider))
    shared = factory.create_text_model("chat_reasoning", model="gemini-legacy")

    async def infer(provider):
        with factory.provider_scope(provider):
            await asyncio.sleep(0)
            response = await shared.generate_content_async(provider)
            return response.provider, shared.provider, shared.model_name

    results = await asyncio.gather(infer("codex"), infer("openai"), infer("openrouter"))

    assert results == [(p, p, f"synthetic-{p}") for p in ("codex", "openai", "openrouter")]
    assert shared.provider == "gemini"
    assert shared.model_name == "gemini-legacy"


def test_gemini_default_preserves_legacy_model_and_response(local_settings, monkeypatch):
    import google.generativeai as genai

    configure = MagicMock()
    native = MagicMock()
    native.generate_content.return_value = SimpleNamespace(text="Synthetic Gemini")
    constructor = MagicMock(return_value=native)
    monkeypatch.setattr(genai, "configure", configure)
    monkeypatch.setattr(genai, "GenerativeModel", constructor)
    selected = factory.create_text_model("conversation_naming", model="gemini-legacy")

    result = selected.generate_content("Synthetic prompt")

    assert selected.provider == "gemini"
    assert selected.model_name == "gemini-legacy"
    assert result is native.generate_content.return_value
    constructor.assert_called_once_with("gemini-legacy")
    configure.assert_called_once_with(api_key="dummy-gemini")


def test_constructor_credentials_remain_bound_to_original_provider(local_settings, monkeypatch):
    import google.generativeai as genai

    configure = MagicMock()
    monkeypatch.setattr(genai, "configure", configure)
    monkeypatch.setattr(genai, "GenerativeModel", MagicMock())
    selected = factory.create_text_model("memory_summary", api_key="explicit-dummy-gemini")
    assert selected._get_model()[0] == "gemini"
    configure.assert_called_once_with(api_key="explicit-dummy-gemini")

    with factory.provider_scope("openrouter"):
        provider, model = selected._get_model()
        assert provider == "openrouter"
        assert model.api_key == "dummy-router"
        assert model.model_name == local_settings.openrouter_model
    with factory.provider_scope("openai"):
        provider, model = selected._get_model()
        assert provider == "openai"
        assert model.api_key == "dummy-openai"


@pytest.mark.asyncio
async def test_codex_only_needs_no_api_keys_and_never_falls_back(local_settings, monkeypatch):
    import google.generativeai as genai

    local_settings.default_ai_provider = "codex"
    local_settings.gemini_api_key = None
    local_settings.openai_api_key = None
    local_settings.openrouter_api_key = None
    codex = MagicMock()
    codex.generate_content.side_effect = CodexError("Synthetic CLI failure")
    codex.generate_content_async = AsyncMock(side_effect=CodexError("Synthetic CLI failure"))
    codex_factory = MagicMock(return_value=codex)
    paid_factory = MagicMock(side_effect=AssertionError("Paid fallback was attempted"))
    gemini_factory = MagicMock(side_effect=AssertionError("Gemini fallback was attempted"))
    monkeypatch.setattr(factory, "CodexTextModel", codex_factory)
    monkeypatch.setattr(factory, "APITextModel", paid_factory)
    monkeypatch.setattr(genai, "GenerativeModel", gemini_factory)
    selected = factory.create_text_model("chat_reasoning", model="gemini-legacy")

    with pytest.raises(CodexError, match="Synthetic CLI failure"):
        selected.generate_content("Synthetic prompt")
    with pytest.raises(CodexError, match="Synthetic CLI failure"):
        await selected.generate_content_async("Synthetic prompt")

    assert selected.provider == "codex"
    assert selected.model_name is None
    codex_factory.assert_called_once()
    paid_factory.assert_not_called()
    gemini_factory.assert_not_called()


def test_global_codex_leaves_google_embeddings_and_dimensions_unchanged(local_settings, monkeypatch):
    import google.generativeai as genai

    from app.services.embedding.incremental_embedding_service import IncrementalEmbeddingService

    local_settings.default_ai_provider = "codex"
    local_settings.google_embedding_api_key = "dummy-embedding-key"
    assert local_settings.embedding_dimension == 3072
    assert local_settings.embedding_model == "models/gemini-embedding-001"
    assert local_settings.effective_embedding_api_key == "dummy-embedding-key"
    embedding = MagicMock(return_value={"embedding": [0.0] * 3072})
    monkeypatch.setattr(genai, "embed_content", embedding)
    service = object.__new__(IncrementalEmbeddingService)
    service.embedding_model = local_settings.embedding_model
    service.embedding_dimension = local_settings.embedding_dimension

    result = service.generate_embedding("Synthetic project text for an embedding test")

    assert len(result) == 3072
    embedding.assert_called_once_with(
        model="models/gemini-embedding-001",
        content="Synthetic project text for an embedding test",
        task_type="retrieval_document", output_dimensionality=3072,
    )


def test_strict_schema_normalization_closes_objects_and_preserves_source():
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "detail": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "count": {"type": "integer"}},
                "required": ["name"],
            },
            "items": {
                "type": "array",
                "items": {"type": "object", "properties": {"label": {"type": "string"}}},
            },
        },
        "required": ["title", "items"],
    }
    original = json.loads(json.dumps(schema))

    wire = codex_output_schema(schema)

    assert schema == original, "Normalization must not mutate reusable application schemas"
    assert wire["additionalProperties"] is False
    assert wire["required"] == ["title", "detail", "items"]
    detail, null_branch = wire["properties"]["detail"]["anyOf"]
    assert null_branch == {"type": "null"}
    assert detail["additionalProperties"] is False
    assert detail["required"] == ["name", "count"]
    assert detail["properties"]["count"] == {"anyOf": [{"type": "integer"}, {"type": "null"}]}
    item = wire["properties"]["items"]["items"]
    assert item["additionalProperties"] is False
    assert item["required"] == ["label"]
    assert item["properties"]["label"] == {"anyOf": [{"type": "string"}, {"type": "null"}]}


@pytest.mark.parametrize("schema", [
    {"type": "object", "additionalProperties": {"type": "string"}},
    {"type": "object", "properties": {"label": {"type": "string"}}, "additionalProperties": True},
    {"type": "object", "properties": {"label": {"type": "string"}}, "additionalProperties": {"type": "string"}},
    {"$ref": "#/$defs/item", "$defs": {"item": {"type": "string"}}},
    {"type": "object", "properties": {"metadata": {"type": "object"}}},
])
def test_open_maps_and_references_use_prompted_json(schema):
    assert codex_output_schema(schema) is None


def test_optional_null_cleanup_preserves_required_nulls_and_unknown_fields():
    schema = {
        "type": "object",
        "properties": {
            "required": {"type": ["string", "null"]},
            "optional": {"type": "string"},
            "entries": {
                "type": "array",
                "items": {"type": "object", "properties": {"optional": {"type": "string"}}},
            },
        },
        "required": ["required", "entries"],
    }
    value = {"required": None, "optional": None, "unknown": None, "entries": [{"optional": None}]}

    cleaned = omit_optional_nulls(value, schema)

    assert cleaned == {"required": None, "unknown": None, "entries": [{}]}
    assert value["optional"] is None, "Cleanup must not mutate the parsed response"
    validate_json(json.dumps(cleaned), schema)


@pytest.mark.parametrize("union", ["anyOf", "oneOf"])
def test_optional_null_cleanup_handles_normalized_union_branches(union):
    schema = {
        "type": "object",
        "properties": {
            "entry": {
                union: [
                    {"type": "object", "properties": {"optional": {"type": "string"}}},
                    {"type": "null"},
                ]
            }
        },
        "required": ["entry"],
    }
    value = {"entry": {"optional": None}}
    assert codex_output_schema(schema) is not None

    cleaned = omit_optional_nulls(value, schema)

    assert cleaned == {"entry": {}}
    validate_json(json.dumps(cleaned), schema)


@pytest.mark.asyncio
async def test_adapter_omits_optional_nulls_before_original_schema_validation(fake_cli):
    schema = {
        "type": "object", "properties": {
            "title": {"type": "string"}, "optional": {"type": "string"},
            "entries": {"type": "array", "items": {
                "type": "object", "properties": {"detail": {"type": "string"}}
            }},
        }, "required": ["title", "entries"],
    }
    cli = fake_cli(answer='{"title":"Synthetic","optional":null,"entries":[{"detail":null}]}')

    response = await cli.model.generate_content_async(
        "Synthetic prompt", generation_config={"response_schema": schema}
    )

    assert json.loads(response.text) == {"title": "Synthetic", "entries": [{}]}
    assert records(cli)[0]["schema"] == codex_output_schema(schema)
    assert_job_cleaned(cli)


@pytest.mark.asyncio
async def test_adapter_prompts_open_map_schema_and_still_validates_locally(fake_cli):
    schema = {"type": "object", "additionalProperties": {"type": "string"}}
    cli = fake_cli(answer='{"arbitrary-key":"Synthetic value"}')

    response = await cli.model.generate_content_async(
        "Synthetic prompt", generation_config={"response_schema": schema}
    )

    assert json.loads(response.text) == {"arbitrary-key": "Synthetic value"}
    record = records(cli)[0]
    assert "--output-schema" not in record["argv"]
    assert json.dumps(schema) in record["prompt"]
    assert_job_cleaned(cli)
