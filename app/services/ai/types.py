"""Small response type compatible with the application's generate_content callers."""

from dataclasses import dataclass, field


@dataclass
class TextResponse:
    text: str
    provider: str
    model_name: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
