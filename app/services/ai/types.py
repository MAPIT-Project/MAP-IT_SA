"""Small response type compatible with the application's generate_content callers."""

from dataclasses import dataclass, field
from typing import Literal, get_args

CodexReasoningEffort = Literal["minimal", "low", "medium", "high", "xhigh", "max", "ultra"]
CODEX_REASONING_EFFORTS = get_args(CodexReasoningEffort)


@dataclass
class TextResponse:
    text: str
    provider: str
    model_name: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
