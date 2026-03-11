"""
Context Window Management for LLM Prompts.

Extracted from tool_aware_agent.py to allow independent reuse of context
window tracking and truncation logic.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# CONTEXT WINDOW MANAGEMENT
# =============================================================================


@dataclass
class ContextLimits:
    """Configuration for context window limits."""

    # Maximum tokens for various components (approximate, using char/4 ratio)
    max_context_chars: int = 100000  # ~25k tokens
    max_tool_result_chars: int = 8000  # Per tool result
    max_observation_chars: int = (
        5000  # Per reasoning step (increased for cross-analysis with partner lists)
    )
    max_document_chars: int = 1000  # Per document in synthesis
    max_documents_per_result: int = 10  # Max docs to include
    max_calls_per_result: int = 15  # Max calls to include
    max_projects_per_result: int = 15  # Max projects to include
    reserved_for_response: int = 4000  # Reserve for output

    @classmethod
    def from_env(cls) -> "ContextLimits":
        """Load limits from environment variables with defaults."""
        return cls(
            max_context_chars=int(os.getenv("MAX_CONTEXT_CHARS", "100000")),
            max_tool_result_chars=int(os.getenv("MAX_TOOL_RESULT_CHARS", "8000")),
            max_observation_chars=int(os.getenv("MAX_OBSERVATION_CHARS", "5000")),
            max_document_chars=int(os.getenv("MAX_DOCUMENT_CHARS", "1000")),
        )


class ContextWindowManager:
    """Manages context window for LLM prompts to prevent overflow."""

    def __init__(self, limits: ContextLimits | None = None):
        self.limits = limits or ContextLimits.from_env()
        self._current_size = 0

    def reset(self):
        """Reset the context size tracker."""
        self._current_size = 0

    @property
    def current_size(self) -> int:
        """Get the current context size in characters."""
        return self._current_size

    def truncate_text(self, text: str, max_chars: int, suffix: str = "...") -> str:
        """Truncate text to max_chars, adding suffix if truncated."""
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - len(suffix)] + suffix

    def truncate_tool_result(self, result: Any) -> str:
        """Truncate a tool result to fit within limits."""
        if result is None:
            return "No results"

        result_str = str(result) if not isinstance(result, str) else result
        return self.truncate_text(result_str, self.limits.max_tool_result_chars)

    def truncate_observation(self, observation: str) -> str:
        """Truncate an observation to fit within limits."""
        return self.truncate_text(observation, self.limits.max_observation_chars)

    def truncate_document(self, content: str) -> str:
        """Truncate document content to fit within limits."""
        return self.truncate_text(content, self.limits.max_document_chars)

    def estimate_prompt_size(self, prompt: str) -> int:
        """Estimate the token count of a prompt (chars / 4 approximation)."""
        return len(prompt) // 4

    def would_exceed_limit(self, additional_chars: int) -> bool:
        """Check if adding more content would exceed the context limit."""
        return (self._current_size + additional_chars) > self.limits.max_context_chars

    def add_to_context(self, content: str) -> str:
        """Add content to context, truncating if necessary."""
        available = (
            self.limits.max_context_chars - self._current_size - self.limits.reserved_for_response
        )
        if available <= 0:
            logger.warning("Context window exhausted, dropping content")
            return ""

        if len(content) > available:
            content = self.truncate_text(content, available)
            logger.warning(f"Content truncated to fit context window ({available} chars)")

        self._current_size += len(content)
        return content

    def format_results_for_context(
        self, results: dict[str, Any], priority_keys: list[str] | None = None
    ) -> str:
        """Format tool results for inclusion in context, respecting limits."""
        if not results:
            return "No tool results yet"

        # Prioritize certain result types
        priority_keys = priority_keys or ["calls", "projects", "documents"]

        formatted_parts = []
        remaining_budget = (
            self.limits.max_context_chars - self._current_size - self.limits.reserved_for_response
        )

        for name, result in results.items():
            if remaining_budget <= 0:
                logger.warning("Skipping remaining results due to context limits")
                break

            result_str = self.truncate_tool_result(result)
            part = f"\n**{name}**: {result_str}\n"

            if len(part) > remaining_budget:
                part = self.truncate_text(part, remaining_budget)

            formatted_parts.append(part)
            remaining_budget -= len(part)

        return "".join(formatted_parts)


# Module-level singleton
_context_manager = ContextWindowManager(ContextLimits.from_env())
