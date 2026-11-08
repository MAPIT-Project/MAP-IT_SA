"""Provider names and text generation steps shared by settings and services."""

from typing import Literal

AIProvider = Literal["gemini", "openai", "openrouter", "codex", "antigravity"]
PROVIDERS = frozenset({"gemini", "openai", "openrouter", "codex", "antigravity"})
TEXT_STEPS = frozenset(
    {
        "chat_reasoning",
        "chat_response",
        "query_preprocessing",
        "memory_summary",
        "conversation_naming",
        "query_planning",
        "call_document_summary",
        "call_history",
        "proposal_generation",
        "call_understanding",
        "proposal_review",
        "proposal_draft",
        "proposal_criteria",
        "proposal_quality",
        "proposal_evaluation",
        "proposal_gaps",
        "proposal_examples",
        "proposal_benchmarking",
        "proposal_rewrite",
        "proposal_suggestions",
    }
)
