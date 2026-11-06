"""Real, synthetic framework/Codex tool-call round trip. No app settings or database."""

import argparse
import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.ai.codex import CodexTextModel


class SyntheticAnswer(BaseModel):
    marker: Literal["FRAMEWORK_OK"]
    total: int
    record_id: str


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--reasoning-effort", default="high")
    args = parser.parse_args()
    # Import the model adapter without app.services.agents' eager app-settings import.
    spec = importlib.util.spec_from_file_location(
        "mapit_synthetic_framework_model", ROOT / "app/services/agents/framework/models.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    transport = CodexTextModel(
        SimpleNamespace(
            codex_enabled=True,
            codex_cli_path="codex",
            codex_model=args.model,
            codex_reasoning_effort=args.reasoning_effort,
            codex_timeout_seconds=120,
        )
    )
    agent = Agent(
        module.CodexAgentModel(transport),
        output_type=SyntheticAnswer,
        instructions=(
            "Call both registered Python functions before producing final_result. "
            "The record ID is unknown until the function returns it. Do not guess."
        ),
    )
    calls = []
    record_id = f"synthetic-{uuid4()}"

    @agent.tool_plain
    def add_numbers(a: int, b: int) -> int:
        """Add the two supplied synthetic integers."""
        calls.append("add_numbers")
        return a + b

    @agent.tool_plain
    def synthetic_record() -> dict[str, str]:
        """Retrieve the synthetic record ID needed in the final answer."""
        calls.append("synthetic_record")
        return {"record_id": record_id}

    result = await agent.run(
        "Add 2 and 3 using add_numbers, retrieve synthetic_record, and return FRAMEWORK_OK, "
        "the computed total, and the exact returned record_id.",
        usage_limits=UsageLimits(request_limit=5, tool_calls_limit=4),
        timeout=300,
    )
    assert result.output.total == 5 and result.output.record_id == record_id
    assert set(calls) == {"add_numbers", "synthetic_record"}
    print(
        json.dumps(
            {
                "provider": "codex",
                "requested_model": args.model,
                "reasoning_effort": args.reasoning_effort,
                "tool_calls": calls,
                "output": result.output.model_dump(),
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
