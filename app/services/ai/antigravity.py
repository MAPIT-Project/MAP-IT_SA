"""Inference-only integration with the authenticated official Antigravity CLI.

No API keys are read by MAPIT for this provider. The CLI owns authentication and model session.
Each job runs non-interactively with terminal sandbox restrictions and slash commands disabled.
"""

import asyncio
import contextlib
import json
import os
import shutil
import signal
import tempfile
from pathlib import Path
from typing import Any

from app.services.ai.budget import budgeted_inference
from app.services.ai.structured import omit_optional_nulls, validate_json
from app.services.ai.types import ANTIGRAVITY_REASONING_EFFORTS, TextResponse


class AntigravityError(RuntimeError):
    """An Antigravity CLI job failed. Messages never include prompts or raw CLI output."""


def _clean_json_text(text: str) -> str:
    """Strip markdown code fence blocks if returned in raw text response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


class AntigravityTextModel:
    provider = "antigravity"
    _max_output_bytes = 4 * 1024 * 1024

    def __init__(self, settings: Any):
        if not settings.antigravity_enabled:
            raise AntigravityError(
                "Antigravity requires local opt-in: set ANTIGRAVITY_ENABLED=true"
            )
        if os.name != "posix":
            raise AntigravityError(
                "MAPIT's Antigravity adapter requires a POSIX host for process cleanup"
            )
        self.cli_path = settings.antigravity_cli_path
        self.model_name = settings.antigravity_model or "gemini-3.8-flash-high"
        self.reasoning_effort = getattr(settings, "antigravity_reasoning_effort", "high")
        if (
            self.reasoning_effort is not None
            and self.reasoning_effort not in ANTIGRAVITY_REASONING_EFFORTS
        ):
            raise AntigravityError(
                f"Unsupported ANTIGRAVITY_REASONING_EFFORT: {self.reasoning_effort}"
            )
        self.timeout = settings.antigravity_timeout_seconds

    @staticmethod
    def _environment() -> dict[str, str]:
        names = ("HOME", "PATH", "LANG", "LC_ALL", "GEMINI_CLI_HOME", "ANTIGRAVITY_HOME")
        return {name: os.environ[name] for name in names if name in os.environ}

    @staticmethod
    async def _stop(process: asyncio.subprocess.Process) -> None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        await process.wait()

    async def _capture(
        self,
        args: list[str],
        cwd: str,
        *,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[int, bytes, bytes]:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = None
            spawn = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    *args,
                    cwd=cwd,
                    env=self._environment() if env is None else env,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=True,
                )
            )
            try:
                try:
                    process = await asyncio.shield(spawn)
                except asyncio.CancelledError:
                    process = await spawn
                    raise
                await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout or self.timeout,
                )
                stdout.seek(0)
                stderr.seek(0)
                return (
                    process.returncode,
                    stdout.read(self._max_output_bytes),
                    stderr.read(65536),
                )
            except FileNotFoundError:
                raise AntigravityError(
                    "Antigravity CLI not found. Install it and check ANTIGRAVITY_CLI_PATH"
                ) from None
            except TimeoutError:
                if process is not None:
                    await self._stop(process)
                raise AntigravityError(
                    f"Antigravity CLI timed out after {timeout or self.timeout} seconds"
                ) from None
            except BaseException:
                if process is not None:
                    await self._stop(process)
                raise

    async def check_available(self) -> str:
        resolved = shutil.which(self.cli_path) or (
            self.cli_path if Path(self.cli_path).is_file() else None
        )
        if not resolved:
            raise AntigravityError(
                f"Antigravity CLI not found at '{self.cli_path}'. Install it or set ANTIGRAVITY_CLI_PATH"
            )
        with tempfile.TemporaryDirectory(prefix="mapit-antigravity-check-") as cwd:
            code, stdout, stderr = await self._capture([resolved, "--version"], cwd, timeout=10.0)
            if code != 0:
                raise AntigravityError(
                    f"Antigravity CLI availability check failed with status {code}"
                )
        return resolved

    @budgeted_inference
    async def generate_content_async(
        self,
        prompt: str,
        generation_config: dict[str, Any] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> TextResponse | Any:
        if not isinstance(prompt, str):
            raise TypeError("Antigravity text generation requires a string prompt")
        config = generation_config or {}
        if not isinstance(config, dict):
            config = {
                key: getattr(config, key, None) for key in ("response_schema", "response_mime_type")
            }
        schema = config.get("response_schema")
        json_mode = schema is not None or config.get("response_mime_type") == "application/json"

        executable = await self.check_available()

        with tempfile.TemporaryDirectory(prefix="mapit-antigravity-") as cwd:
            gemini_md = Path(cwd) / "GEMINI.md"
            gemini_md.write_text(
                "# System Instructions\n"
                "You are an inference-only engine for MAPIT.\n"
                "CRITICAL:\n"
                "1. NEVER execute workspace commands or tools (run_command, read_file, edit_file, etc.).\n"
                "2. The workspace is empty; do not check or explore the directory.\n"
                "3. Immediately return the structured JSON decision or final answer in the very first turn.\n",
                encoding="utf-8",
            )
            settings_payload = {
                "toolPermission": "strict",
                "permissions": {
                    "deny": [
                        "command(*)",
                        "read_file(*)",
                        "write_file(*)",
                        "read_url(*)",
                        "mcp(*)",
                    ]
                },
            }
            cmd = [
                executable,
                "-p",
                prompt,
                "--output-format",
                "json",
                "--model",
                self.model_name,
                "--sandbox",
                "--disable-slash-commands",
                "--settings",
                json.dumps(settings_payload),
            ]
            if self.reasoning_effort:
                cmd.extend(["--effort", self.reasoning_effort])

            schema_path = None
            if schema is not None:
                schema_path = Path(cwd) / "schema.json"
                schema_path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
                cmd.extend(["--json-schema", str(schema_path)])
            elif json_mode:
                prompt_adjusted = "Return valid JSON only.\n\n" + prompt
                cmd[2] = prompt_adjusted

            code, stdout_bytes, stderr_bytes = await self._capture(cmd, cwd)
            if code != 0:
                err_text = stderr_bytes.decode("utf-8", errors="replace").strip()
                raise AntigravityError(
                    f"Antigravity CLI exited with status {code}: {err_text or 'unknown error'}"
                )

            raw_text = stdout_bytes.decode("utf-8", errors="replace").strip()
            if not raw_text:
                raise AntigravityError("Antigravity CLI returned an empty response")

            try:
                data = json.loads(raw_text)
            except Exception as e:
                raise AntigravityError(
                    f"Antigravity CLI did not return valid JSON wrapper: {e}"
                ) from None

            if data.get("status") not in (None, "SUCCESS"):
                error_msg = data.get("error") or data.get("status")
                raise AntigravityError(f"Antigravity CLI reported error: {error_msg}")

            if (
                schema is not None
                and "structured_output" in data
                and data["structured_output"] is not None
            ):
                value = data["structured_output"]
                value = omit_optional_nulls(value, schema)
                answer = json.dumps(value, ensure_ascii=False)
                validate_json(answer, schema)
            else:
                answer = data.get("response", "").strip()
                if json_mode:
                    cleaned = _clean_json_text(answer)
                    value = validate_json(cleaned, schema)
                    if schema is not None:
                        value = omit_optional_nulls(value, schema)
                    answer = json.dumps(value, ensure_ascii=False)
                elif not answer:
                    raise AntigravityError("Antigravity CLI returned empty response text")

            raw_usage = data.get("usage") or {}
            usage = {
                "input_tokens": raw_usage.get("input_tokens", 0),
                "output_tokens": raw_usage.get("output_tokens", 0),
                "reasoning_output_tokens": raw_usage.get("thinking_tokens", 0),
                "total_tokens": raw_usage.get("total_tokens", 0),
            }
            response = TextResponse(answer, self.provider, self.model_name, usage)

        if stream:

            async def chunks():
                yield response

            return chunks()
        return response

    def generate_content(
        self,
        prompt: str,
        generation_config: dict[str, Any] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> TextResponse | Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            response = asyncio.run(
                self.generate_content_async(prompt, generation_config, False, **kwargs)
            )
            return iter([response]) if stream else response
        raise RuntimeError("Use await generate_content_async() inside an async call path")
