"""Unit tests for the Antigravity CLI adapter."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai.antigravity import AntigravityError, AntigravityTextModel


@pytest.fixture
def base_settings():
    return SimpleNamespace(
        antigravity_enabled=True,
        antigravity_cli_path="agy",
        antigravity_model="gemini-3.8-flash-high",
        antigravity_reasoning_effort="high",
        antigravity_timeout_seconds=30.0,
    )


def test_antigravity_requires_opt_in(base_settings):
    base_settings.antigravity_enabled = False
    with pytest.raises(AntigravityError, match="ANTIGRAVITY_ENABLED=true"):
        AntigravityTextModel(base_settings)


def test_antigravity_validates_reasoning_effort(base_settings):
    base_settings.antigravity_reasoning_effort = "invalid_effort"
    with pytest.raises(AntigravityError, match="Unsupported ANTIGRAVITY_REASONING_EFFORT"):
        AntigravityTextModel(base_settings)


@pytest.mark.asyncio
async def test_antigravity_check_available_missing_cli(base_settings):
    base_settings.antigravity_cli_path = "/nonexistent/path/to/agy"
    model = AntigravityTextModel(base_settings)
    with pytest.raises(AntigravityError, match="Antigravity CLI not found"):
        await model.check_available()


@pytest.mark.asyncio
async def test_antigravity_generate_content_plain_text(base_settings):
    model = AntigravityTextModel(base_settings)
    mock_payload = {
        "status": "SUCCESS",
        "response": "Hello from Antigravity Gemini 3.8",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 20,
            "thinking_tokens": 50,
            "total_tokens": 170,
        },
    }

    with patch.object(model, "check_available", AsyncMock(return_value="/bin/agy")):
        with patch.object(
            model,
            "_capture",
            AsyncMock(return_value=(0, json.dumps(mock_payload).encode("utf-8"), b"")),
        ) as mock_capture:
            response = await model.generate_content_async("Say hello")
            assert response.text == "Hello from Antigravity Gemini 3.8"
            assert response.provider == "antigravity"
            assert response.model_name == "gemini-3.8-flash-high"
            assert response.usage["input_tokens"] == 100
            assert response.usage["reasoning_output_tokens"] == 50

            args, _ = mock_capture.call_args
            cmd = args[0]
            assert cmd[0] == "/bin/agy"
            assert "--model" in cmd
            assert cmd[cmd.index("--model") + 1] == "gemini-3.8-flash-high"
            assert "--effort" in cmd
            assert cmd[cmd.index("--effort") + 1] == "high"
            assert "--settings" in cmd


@pytest.mark.asyncio
async def test_antigravity_generate_content_structured_schema(base_settings):
    model = AntigravityTextModel(base_settings)
    schema = {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    }
    mock_payload = {
        "status": "SUCCESS",
        "response": '{"city": "Amsterdam"}',
        "structured_output": {"city": "Amsterdam"},
        "usage": {"input_tokens": 50, "output_tokens": 10, "thinking_tokens": 30},
    }

    with patch.object(model, "check_available", AsyncMock(return_value="/bin/agy")):
        with patch.object(
            model,
            "_capture",
            AsyncMock(return_value=(0, json.dumps(mock_payload).encode("utf-8"), b"")),
        ) as mock_capture:
            response = await model.generate_content_async(
                "Name a city", generation_config={"response_schema": schema}
            )
            data = json.loads(response.text)
            assert data == {"city": "Amsterdam"}
            args, _ = mock_capture.call_args
            cmd = args[0]
            assert "--json-schema" in cmd


@pytest.mark.asyncio
async def test_antigravity_generate_content_failure(base_settings):
    model = AntigravityTextModel(base_settings)
    with patch.object(model, "check_available", AsyncMock(return_value="/bin/agy")):
        with patch.object(
            model,
            "_capture",
            AsyncMock(return_value=(1, b"", b"Model quota exhausted")),
        ):
            with pytest.raises(
                AntigravityError, match="exited with status 1: Model quota exhausted"
            ):
                await model.generate_content_async("Test failure")
