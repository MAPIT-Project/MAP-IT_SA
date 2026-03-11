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
    max_observation_chars: int = 8000  # Per reasoning step — allows rich tool results for synthesis
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
            max_observation_chars=int(os.getenv("MAX_OBSERVATION_CHARS", "8000")),
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
        """Truncate an observation to fit within limits, using smart truncation."""
        return self.smart_truncate_observation(observation, self.limits.max_observation_chars)

    def smart_truncate_observation(self, observation: str, max_chars: int = 0) -> str:
        """Truncate observation intelligently, preserving structure.

        Detects content type and preserves:
        - Header/aggregate metrics
        - First N complete items
        - "...and N more" suffix
        Falls back to simple truncation for unknown formats.
        """
        if not observation:
            return ""
        max_chars = max_chars or self.limits.max_observation_chars
        if len(observation) <= max_chars:
            return observation

        lines = observation.split("\n")

        # Detect structured list format (numbered items like "1. NAME (CC, TYPE): ...")
        # Common in partner discovery, project lists, etc.
        numbered_pattern = any(
            line.strip().startswith(f"{i}.") for line in lines[:5] for i in range(1, 6)
        )

        if numbered_pattern or self._has_structured_items(lines):
            return self._truncate_structured(lines, max_chars)

        # Detect markdown sections (## headers, **bold** metrics)
        has_sections = any(line.strip().startswith(("##", "**")) for line in lines[:10])
        if has_sections:
            return self._truncate_sections(lines, max_chars)

        # Fallback to simple truncation
        return self.truncate_text(observation, max_chars)

    def _has_structured_items(self, lines: list[str]) -> bool:
        """Check if lines contain structured numbered/bulleted items."""
        item_count = sum(
            1
            for line in lines
            if line.strip()
            and (
                line.strip()[0].isdigit()
                and ". " in line[:5]
                or line.strip().startswith("- **")
                or line.strip().startswith("| ")
            )
        )
        return item_count >= 3

    def _truncate_structured(self, lines: list[str], max_chars: int) -> str:
        """Truncate structured list, keeping header + first N items + summary."""
        result_lines = []
        current_size = 0
        # Reserve space for "...and N more" suffix (min 50, max 100)
        reserve = min(100, max(50, max_chars // 20))
        effective_max = max_chars - reserve

        # Phase 1: Always include header lines (non-numbered, before first item)
        header_end = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and (
                (stripped[0].isdigit() and ". " in stripped[:5])
                or stripped.startswith("- **")
                or stripped.startswith("| ")
            ):
                header_end = i
                break
        else:
            header_end = len(lines)

        for line in lines[:header_end]:
            if current_size + len(line) + 1 > effective_max:
                break
            result_lines.append(line)
            current_size += len(line) + 1

        # Phase 2: Include as many complete items as possible
        items_included = 0
        total_items = 0
        i = header_end
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Count items (numbered lines or bold-prefixed lines)
            is_item_start = (
                stripped and stripped[0].isdigit() and ". " in stripped[:5]
            ) or stripped.startswith("- **")

            if is_item_start:
                total_items += 1

            # Collect this item (item start + any continuation lines)
            item_lines = [line]
            j = i + 1
            while j < len(lines):
                next_stripped = lines[j].strip()
                next_is_item = (
                    next_stripped and next_stripped[0].isdigit() and ". " in next_stripped[:5]
                ) or next_stripped.startswith("- **")
                if next_is_item or not next_stripped:
                    break
                item_lines.append(lines[j])
                j += 1

            item_text = "\n".join(item_lines)
            if current_size + len(item_text) + 1 > effective_max:
                # Can't fit more items
                remaining = total_items
                # Count remaining items
                for k in range(j, len(lines)):
                    sk = lines[k].strip()
                    if (sk and sk[0].isdigit() and ". " in sk[:5]) or sk.startswith("- **"):
                        remaining += 1
                if remaining > 0:
                    result_lines.append(f"\n...and {remaining} more items (truncated)")
                break

            result_lines.extend(item_lines)
            current_size += len(item_text) + 1
            items_included += 1
            i = j

        return "\n".join(result_lines)

    def _truncate_sections(self, lines: list[str], max_chars: int) -> str:
        """Truncate content with markdown sections, preserving headers and key metrics."""
        result_lines = []
        current_size = 0
        reserve = 80
        effective_max = max_chars - reserve

        for line in lines:
            if current_size + len(line) + 1 > effective_max:
                result_lines.append("\n...(truncated)")
                break
            result_lines.append(line)
            current_size += len(line) + 1

        return "\n".join(result_lines)

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
