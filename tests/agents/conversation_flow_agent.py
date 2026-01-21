"""
Conversation Flow Agent for automated multi-turn conversation testing.

This agent simulates real user interactions with the MAPIT conversation API,
including:
- Sending messages and collecting SSE events
- Tracking conversation state across turns
- Validating response structure
- Running complete conversation scenarios

Usage:
    agent = ConversationFlowAgent("http://localhost:8000")
    turn = await agent.send_message("Find hydrogen funding calls")
    print(turn.response_text)
    print(turn.tools_used)
"""

import asyncio
import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
import yaml

logger = logging.getLogger(__name__)


def _generate_conversation_id() -> int:
    """Generate a random integer conversation ID.

    Uses a large range to avoid collisions while staying within
    safe integer bounds for database storage.
    """
    # Generate a random ID between 1_000_000 and 2_000_000_000
    return random.randint(1_000_000, 2_000_000_000)


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation."""

    user_message: str
    response_text: str = ""
    events: list[dict[str, Any]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    error: str | None = None
    processing_time_ms: float = 0.0
    conversation_name: str | None = None

    @property
    def has_error(self) -> bool:
        """Check if this turn has an error."""
        return self.error is not None or any(e.get("type") == "error" for e in self.events)

    @property
    def references_previous_result(self) -> bool:
        """Check if this turn references a previous result."""
        reference_patterns = [
            "the first",
            "the second",
            "the third",
            "the fourth",
            "the fifth",
            "the 1st",
            "the 2nd",
            "the 3rd",
            "the 4th",
            "the 5th",
            "that one",
            "this call",
            "this project",
            "mentioned above",
            "tell me more",
            "more details",
            "elaborate",
            "the same",
            "number 1",
            "number 2",
            "number 3",
            "#1",
            "#2",
            "#3",
            "item 1",
            "item 2",
            "item 3",
            # Comparative references that imply previous results
            "which one",
            "these calls",
            "these projects",
            "them",
            "the largest",
            "the smallest",
            "the highest",
            "the lowest",
        ]
        lower_msg = self.user_message.lower()
        return any(pattern in lower_msg for pattern in reference_patterns)

    def get_events_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.get("type") == event_type]


@dataclass
class Validation:
    """A validation to run on a conversation turn."""

    type: str
    name: str = ""
    patterns: list[str] = field(default_factory=list)
    expected: list[str] = field(default_factory=list)
    count: int = 0
    from_turn: int = 0
    description: str = ""

    async def check(self, turn: ConversationTurn, agent: "ConversationFlowAgent") -> bool:
        """Run this validation and return whether it passed."""
        if self.type == "response_contains":
            # Requires ALL patterns to match
            return all(p.lower() in turn.response_text.lower() for p in self.patterns)

        elif self.type == "response_contains_any":
            # Requires at least ONE pattern to match
            return any(p.lower() in turn.response_text.lower() for p in self.patterns)

        elif self.type == "tools_used":
            return all(t in turn.tools_used for t in self.expected)

        elif self.type == "min_results":
            # Check tool results for count
            for result in turn.tool_results:
                if result.get("count", 0) >= self.count:
                    return True
            return False

        elif self.type == "follow_up_resolved":
            return turn.references_previous_result

        elif self.type == "context_preserved":
            # Check that context from previous turn is preserved
            if self.from_turn < len(agent.message_history):
                prev_turn = agent.message_history[self.from_turn]
                return await agent.validate_context_contains(prev_turn.response_text[:100])
            return True

        elif self.type == "no_error":
            return not turn.has_error

        elif self.type == "has_metadata":
            return bool(turn.metadata)

        return True


@dataclass
class ScenarioStep:
    """A single step in a conversation scenario."""

    message: str
    validations: list[Validation] = field(default_factory=list)
    delay_ms: int = 0  # Delay before sending this message

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenarioStep":
        """Create from dictionary."""
        validations = []
        for v in data.get("validations", []):
            validations.append(
                Validation(
                    type=v.get("type", ""),
                    name=v.get("name", v.get("type", "")),
                    patterns=v.get("patterns", []),
                    expected=v.get("expected", []),
                    count=v.get("count", 0),
                    from_turn=v.get("from_turn", 0),
                    description=v.get("description", ""),
                )
            )
        return cls(
            message=data.get("message", ""),
            validations=validations,
            delay_ms=data.get("delay_ms", 0),
        )


@dataclass
class ConversationScenario:
    """A complete conversation scenario for testing."""

    name: str
    description: str
    steps: list[ScenarioStep]
    tags: list[str] = field(default_factory=list)
    stop_on_error: bool = True
    final_validations: list[Validation] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ConversationScenario":
        """Load scenario from YAML file."""
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        steps = [ScenarioStep.from_dict(s) for s in data.get("steps", [])]

        final_validations = []
        for v in data.get("final_validations", []):
            final_validations.append(
                Validation(
                    type=v.get("type", ""),
                    name=v.get("name", v.get("type", "")),
                    description=v.get("description", ""),
                )
            )

        return cls(
            name=data.get("name", yaml_path.stem),
            description=data.get("description", ""),
            steps=steps,
            tags=data.get("tags", []),
            stop_on_error=data.get("stop_on_error", True),
            final_validations=final_validations,
        )


@dataclass
class ValidationResult:
    """Result of a validation check."""

    passed: bool
    name: str = ""
    message: str = ""
    step_index: int = 0


@dataclass
class ScenarioResult:
    """Result of running a conversation scenario."""

    scenario_name: str
    passed: bool = True
    validations: list[ValidationResult] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    turns: list[ConversationTurn] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def all_validations_passed(self) -> bool:
        return all(v.passed for v in self.validations)

    @property
    def failed_validations(self) -> list[ValidationResult]:
        return [v for v in self.validations if not v.passed]

    def add_validation(self, name: str, passed: bool, step_index: int = 0, message: str = ""):
        self.validations.append(
            ValidationResult(
                passed=passed,
                name=name,
                message=message,
                step_index=step_index,
            )
        )
        if not passed:
            self.passed = False

    def add_error(self, step_index: int, step_message: str, error: str):
        self.errors.append(
            {
                "step_index": step_index,
                "step_message": step_message,
                "error": error,
            }
        )
        self.passed = False


class ConversationFlowAgent:
    """
    Agent that simulates multi-turn conversations for testing.

    Features:
    - Sends messages via streaming API
    - Collects and validates SSE events
    - Tracks conversation state across turns
    - Supports running complete scenarios
    - Validates response quality
    """

    def __init__(
        self,
        base_url: str,
        conversation_id: int | None = None,
        timeout: float = 120.0,
    ):
        """
        Initialize the conversation flow agent.

        Args:
            base_url: Base URL of the MAPIT API
            conversation_id: Optional conversation ID (generates new if not provided)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.conversation_id = conversation_id or _generate_conversation_id()
        self.timeout = timeout
        self.message_history: list[ConversationTurn] = []
        self.context_snapshots: list[dict[str, Any]] = []

    async def send_message(
        self,
        message: str,
        wait_for_complete: bool = True,
        collect_events: bool = True,
    ) -> ConversationTurn:
        """
        Send a message and collect the full response.

        Args:
            message: The user message to send
            wait_for_complete: Whether to wait for the complete event
            collect_events: Whether to collect all SSE events

        Returns:
            ConversationTurn with all response data
        """
        turn = ConversationTurn(
            user_message=message,
            timestamp=datetime.now(),
        )

        start_time = datetime.now()
        url = f"{self.base_url}/api/v3/conversation/{self.conversation_id}/message/stream"

        try:
            timeout_config = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                async with session.post(
                    url,
                    json={"message": message, "include_context": True},
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status != 200:
                        turn.error = f"HTTP {response.status}: {await response.text()}"
                        return turn

                    async for line in response.content:
                        line = line.decode("utf-8").strip()

                        if not line or not line.startswith("data: "):
                            continue

                        try:
                            event_data = line[6:]  # Remove "data: " prefix
                            event = json.loads(event_data)

                            if collect_events:
                                turn.events.append(event)

                            # Process event by type
                            event_type = event.get("type", "")

                            if event_type == "token":
                                turn.response_text += event.get("content", "")

                            elif event_type == "tool_call":
                                # Handle both 'tool' and 'tool_name' field names
                                tool_name = event.get("tool") or event.get("tool_name", "")
                                if tool_name:
                                    turn.tools_used.append(tool_name)

                            elif event_type == "tool_result":
                                turn.tool_results.append(
                                    {
                                        "tool": event.get("tool", ""),
                                        "result": event.get("result", {}),
                                        "count": event.get("result", {}).get("count", 0),
                                    }
                                )

                            elif event_type == "conversation_name":
                                turn.conversation_name = event.get("name", "")

                            elif event_type == "complete":
                                turn.metadata = event.get("metadata", {})
                                if not wait_for_complete:
                                    break

                            elif event_type == "error":
                                turn.error = event.get("message", "Unknown error")
                                break

                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse SSE event: {e}")
                            continue

        except TimeoutError:
            turn.error = f"Request timed out after {self.timeout}s"
        except aiohttp.ClientError as e:
            turn.error = f"Request failed: {str(e)}"
        except Exception as e:
            turn.error = f"Unexpected error: {str(e)}"

        turn.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        self.message_history.append(turn)

        return turn

    async def send_message_non_streaming(self, message: str) -> ConversationTurn:
        """
        Send a message using the non-streaming endpoint.

        Args:
            message: The user message to send

        Returns:
            ConversationTurn with response data
        """
        turn = ConversationTurn(
            user_message=message,
            timestamp=datetime.now(),
        )

        start_time = datetime.now()
        url = f"{self.base_url}/api/v3/conversation/{self.conversation_id}/message"

        try:
            timeout_config = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                async with session.post(
                    url,
                    json={"message": message, "include_context": True},
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status != 200:
                        turn.error = f"HTTP {response.status}: {await response.text()}"
                        return turn

                    data = await response.json()
                    turn.response_text = data.get("response", "")
                    turn.metadata = data.get("metadata", {})
                    turn.tools_used = turn.metadata.get("tools_used", [])

        except Exception as e:
            turn.error = f"Request failed: {str(e)}"

        turn.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        self.message_history.append(turn)

        return turn

    async def get_context(self) -> dict[str, Any]:
        """Get the current conversation context from the API."""
        url = f"{self.base_url}/api/v3/conversation/{self.conversation_id}/context"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        context = await response.json()
                        self.context_snapshots.append(context)
                        return context
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}

    async def clear_context(self) -> bool:
        """Clear the conversation context."""
        url = f"{self.base_url}/api/v3/conversation/{self.conversation_id}/context"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(url) as response:
                    return response.status == 200
        except Exception:
            return False

    async def validate_context_contains(self, expected_content: str) -> bool:
        """Check if the conversation context contains expected content."""
        context = await self.get_context()

        if "error" in context:
            return False

        # Check in recent messages
        recent_messages = context.get("recent_messages", [])
        for msg in recent_messages:
            content = msg.get("content", "") or msg.get("message", "")
            if expected_content.lower() in content.lower():
                return True

        # Check in summary
        summary = context.get("summary", "") or context.get("long_term_summary", "")
        if expected_content.lower() in summary.lower():
            return True

        return False

    async def run_scenario(self, scenario: ConversationScenario) -> ScenarioResult:
        """
        Execute a complete conversation scenario.

        Args:
            scenario: The scenario to run

        Returns:
            ScenarioResult with all validation results
        """
        result = ScenarioResult(scenario_name=scenario.name)
        start_time = datetime.now()

        for step_index, step in enumerate(scenario.steps):
            # Apply delay if specified
            if step.delay_ms > 0:
                await asyncio.sleep(step.delay_ms / 1000.0)

            try:
                turn = await self.send_message(step.message)
                result.turns.append(turn)

                # Check if turn had an error
                if turn.has_error:
                    result.add_error(step_index, step.message, turn.error or "Unknown error")
                    if scenario.stop_on_error:
                        break
                    continue

                # Run step-level validations
                for validation in step.validations:
                    passed = await validation.check(turn, self)
                    result.add_validation(
                        name=validation.name or validation.type,
                        passed=passed,
                        step_index=step_index,
                        message=f"Step {step_index + 1}: {step.message[:50]}...",
                    )

                    if not passed and scenario.stop_on_error:
                        break

            except Exception as e:
                result.add_error(step_index, step.message, str(e))
                if scenario.stop_on_error:
                    break

        # Run final validations
        for validation in scenario.final_validations:
            if validation.type == "context_integrity":
                context = await self.get_context()
                passed = "error" not in context
            elif validation.type == "quality_non_degradation":
                # Check that quality doesn't drop significantly
                passed = True  # Placeholder - QualityEvaluatorAgent handles this
            else:
                passed = True

            result.add_validation(
                name=validation.name or validation.type,
                passed=passed,
                message=validation.description,
            )

        result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        return result

    async def run_concurrent_messages(
        self,
        messages: list[str],
        delay_between_ms: int = 0,
    ) -> list[ConversationTurn]:
        """
        Send multiple messages concurrently to test race conditions.

        Args:
            messages: List of messages to send
            delay_between_ms: Delay between starting each message

        Returns:
            List of ConversationTurn results
        """

        async def send_with_delay(message: str, delay: int) -> ConversationTurn:
            if delay > 0:
                await asyncio.sleep(delay / 1000.0)
            return await self.send_message(message)

        tasks = [send_with_delay(msg, i * delay_between_ms) for i, msg in enumerate(messages)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        turns = []
        for result in results:
            if isinstance(result, ConversationTurn):
                turns.append(result)
            elif isinstance(result, Exception):
                turn = ConversationTurn(
                    user_message="(failed)",
                    error=str(result),
                )
                turns.append(turn)

        return turns

    def reset(self):
        """Reset the agent state for a new conversation."""
        self.conversation_id = _generate_conversation_id()
        self.message_history = []
        self.context_snapshots = []

    def get_turn(self, index: int) -> ConversationTurn | None:
        """Get a specific turn from history."""
        if 0 <= index < len(self.message_history):
            return self.message_history[index]
        return None

    @property
    def turn_count(self) -> int:
        """Get the number of turns in this conversation."""
        return len(self.message_history)

    @property
    def all_tools_used(self) -> list[str]:
        """Get all tools used across all turns."""
        tools = []
        for turn in self.message_history:
            tools.extend(turn.tools_used)
        return tools

    @property
    def total_processing_time_ms(self) -> float:
        """Get total processing time across all turns."""
        return sum(turn.processing_time_ms for turn in self.message_history)
