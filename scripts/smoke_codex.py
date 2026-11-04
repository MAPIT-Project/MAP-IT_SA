"""Real synthetic inference smoke. Does not load MAPIT settings or dotenv files."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ai.codex import CodexTextModel


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    model = CodexTextModel(SimpleNamespace(
        codex_enabled=True, codex_cli_path="codex", codex_model=args.model,
        codex_timeout_seconds=args.timeout,
    ))
    schema = {
        "type": "object",
        "properties": {
            "marker": {"type": "string"},
            "tools": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["marker", "tools"],
        "additionalProperties": False,
    }
    response = await model.generate_content_async(
        "Set marker to MAPIT_CODEX_OK. List exact names of every callable tool available "
        "to you in tools, or [] if none. Do not invoke any tools.",
        generation_config={"response_schema": schema},
    )
    print(json.dumps({"text": response.text, "model": response.model_name, "usage": response.usage}))


if __name__ == "__main__":
    asyncio.run(main())
