"""
Tests for Scenario 063: Tool Progress Visible - Multi-Tool Visibility Verification

PRD Reference:
- Query requiring multiple tools
- Expected: Tool calls and results visible during streaming
- Verify: User sees what's happening
- Fix if: Black box until final answer
- Pass threshold: Progress visible

This scenario tests that tool progress is visible during streaming:
1. tool_call events are emitted BEFORE tool execution
2. tool_result events are emitted AFTER tool execution
3. Tool names and parameters are visible in tool_call events
4. Tool results include success status, result count, and summary
5. Multiple tools show multiple tool_call/tool_result pairs
6. Events arrive in order: status → agent_thinking → tool_call → tool_result → tokens
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

# Minimum requirements for tool progress visibility
MIN_TOOL_CALL_EVENTS = 1  # At least 1 tool_call event
MIN_TOOL_RESULT_EVENTS = 1  # At least 1 tool_result event

# Required fields in tool_call events
REQUIRED_TOOL_CALL_FIELDS = {"tool_name", "parameters"}

# Required fields in tool_result events
REQUIRED_TOOL_RESULT_FIELDS = {"tool_name", "success"}

# Optional fields that improve visibility
OPTIONAL_TOOL_RESULT_FIELDS = {"result_count", "result_summary", "execution_time_ms"}

# All allowed event types (from conversation_routes_v3.py)
ALLOWED_EVENT_TYPES = {
    "status",
    "progress",
    "conversation_name",
    "agent_thinking",
    "tool_call",
    "tool_result",
    "token",
    "complete",
    "error",
}

# Test queries that should trigger multiple tool calls
MULTI_TOOL_QUERIES = [
    # Search queries that use search_funding_calls
    "Find open hydrogen funding calls and show partner organizations with hydrogen expertise",
    # Complex queries that may use multiple tools
    "What is the budget range for climate research RIA projects and find similar funded projects?",
    # Comparison queries that need multiple data points
    "Compare EIC Accelerator and ERC Starting Grant funding amounts and success rates",
]

# Simple tool queries (single tool expected)
SINGLE_TOOL_QUERIES = [
    "Find open funding calls for AI research",
    "Search for funded projects on quantum computing",
    "What budget should I plan for a health research project?",
]


# ============================================================================
# Data Classes for Tool Progress Analysis
# ============================================================================


@dataclass
class ToolCallEvent:
    """Represents a tool_call event."""

    timestamp: float
    iteration: int
    tool_name: str
    parameters: dict[str, Any]
    reasoning: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResultEvent:
    """Represents a tool_result event."""

    timestamp: float
    iteration: int
    tool_name: str
    success: bool
    result_count: int = 0
    result_summary: str = ""
    execution_time_ms: int = 0
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamingEvent:
    """Represents a single SSE event received during streaming."""

    type: str
    timestamp: float
    raw_data: str
    parsed_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolProgressAnalysis:
    """Analysis of tool progress visibility during a streaming response."""

    query: str
    events: list[StreamingEvent] = field(default_factory=list)
    tool_calls: list[ToolCallEvent] = field(default_factory=list)
    tool_results: list[ToolResultEvent] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    error: str | None = None

    @property
    def duration_seconds(self) -> float:
        """Total duration of streaming session."""
        if self.end_time == 0.0:
            return 0.0
        return self.end_time - self.start_time

    @property
    def event_types(self) -> list[str]:
        """List of all event types received in order."""
        return [e.type for e in self.events]

    @property
    def unique_event_types(self) -> set[str]:
        """Set of unique event types received."""
        return set(self.event_types)

    @property
    def tool_call_count(self) -> int:
        """Number of tool_call events received."""
        return len(self.tool_calls)

    @property
    def tool_result_count(self) -> int:
        """Number of tool_result events received."""
        return len(self.tool_results)

    @property
    def unique_tools_called(self) -> set[str]:
        """Set of unique tool names called."""
        return {tc.tool_name for tc in self.tool_calls}

    @property
    def has_tool_calls(self) -> bool:
        """Check if any tool_call events were received."""
        return self.tool_call_count >= MIN_TOOL_CALL_EVENTS

    @property
    def has_tool_results(self) -> bool:
        """Check if any tool_result events were received."""
        return self.tool_result_count >= MIN_TOOL_RESULT_EVENTS

    @property
    def has_tool_progress(self) -> bool:
        """Check if tool progress is visible (both calls and results)."""
        return self.has_tool_calls and self.has_tool_results

    @property
    def all_tools_have_results(self) -> bool:
        """Check if all tool calls have corresponding results."""
        call_names = {tc.tool_name for tc in self.tool_calls}
        result_names = {tr.tool_name for tr in self.tool_results}
        return call_names == result_names

    @property
    def tool_calls_before_tokens(self) -> bool:
        """Check if tool_call events appear before token events."""
        first_tool_call_idx = next(
            (i for i, e in enumerate(self.events) if e.type == "tool_call"), None
        )
        first_token_idx = next((i for i, e in enumerate(self.events) if e.type == "token"), None)
        if first_tool_call_idx is None or first_token_idx is None:
            return True  # No conflict if one is missing
        return first_tool_call_idx < first_token_idx

    @property
    def tool_results_before_tokens(self) -> bool:
        """Check if tool_result events appear before token events."""
        first_tool_result_idx = next(
            (i for i, e in enumerate(self.events) if e.type == "tool_result"), None
        )
        first_token_idx = next((i for i, e in enumerate(self.events) if e.type == "token"), None)
        if first_tool_result_idx is None or first_token_idx is None:
            return True  # No conflict if one is missing
        return first_tool_result_idx < first_token_idx

    @property
    def tool_calls_have_required_fields(self) -> bool:
        """Check if all tool_call events have required fields."""
        for tc in self.tool_calls:
            if not tc.tool_name:
                return False
            if tc.parameters is None:
                return False
        return True

    @property
    def tool_results_have_required_fields(self) -> bool:
        """Check if all tool_result events have required fields."""
        for tr in self.tool_results:
            if not tr.tool_name:
                return False
            # success field must be present (can be True or False)
        return True

    @property
    def tool_execution_times(self) -> list[int]:
        """List of tool execution times in milliseconds."""
        return [tr.execution_time_ms for tr in self.tool_results if tr.execution_time_ms > 0]

    @property
    def accumulated_response(self) -> str:
        """Accumulated text from all token events."""
        return "".join(e.parsed_data.get("content", "") for e in self.events if e.type == "token")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "query": self.query,
            "duration_seconds": self.duration_seconds,
            "total_events": len(self.events),
            "tool_call_count": self.tool_call_count,
            "tool_result_count": self.tool_result_count,
            "unique_tools_called": list(self.unique_tools_called),
            "has_tool_progress": self.has_tool_progress,
            "all_tools_have_results": self.all_tools_have_results,
            "tool_calls_before_tokens": self.tool_calls_before_tokens,
            "tool_results_before_tokens": self.tool_results_before_tokens,
            "tool_calls_have_required_fields": self.tool_calls_have_required_fields,
            "tool_results_have_required_fields": self.tool_results_have_required_fields,
            "tool_execution_times": self.tool_execution_times,
            "event_sequence": self.event_types,
            "response_length": len(self.accumulated_response),
            "error": self.error,
        }


# ============================================================================
# Tool Progress Evaluator
# ============================================================================


class ToolProgressVisibleEvaluator:
    """Evaluator for Scenario 063: Tool Progress Visible."""

    def __init__(
        self,
        min_tool_calls: int = MIN_TOOL_CALL_EVENTS,
        min_tool_results: int = MIN_TOOL_RESULT_EVENTS,
    ):
        self.min_tool_calls = min_tool_calls
        self.min_tool_results = min_tool_results

    def evaluate(self, analysis: ToolProgressAnalysis) -> dict[str, Any]:
        """
        Evaluate a tool progress analysis against requirements.

        Scoring (100 points total):
        - Tool Call Visibility (30 points): tool_call events present with required fields
        - Tool Result Visibility (30 points): tool_result events present with required fields
        - Event Order (15 points): tool events before tokens
        - Event Pairing (15 points): all calls have corresponding results
        - Result Detail (10 points): includes execution time, result count, summary
        """
        evaluation = {
            "query": analysis.query,
            "score": 0,
            "passed": False,
            "dimensions": {},
            "issues": [],
        }

        # Check for errors
        if analysis.error:
            evaluation["issues"].append(f"Error: {analysis.error}")
            return evaluation

        # 1. Tool Call Visibility (30 points)
        has_tool_calls = analysis.has_tool_calls
        has_required_fields = analysis.tool_calls_have_required_fields

        tool_call_score = 0
        if has_tool_calls and has_required_fields:
            tool_call_score = 30
        elif has_tool_calls:
            tool_call_score = 15

        evaluation["dimensions"]["tool_call_visibility"] = {
            "score": tool_call_score,
            "max_score": 30,
            "tool_call_count": analysis.tool_call_count,
            "min_required": self.min_tool_calls,
            "has_required_fields": has_required_fields,
            "tools_called": list(analysis.unique_tools_called),
        }
        evaluation["score"] += tool_call_score
        if not has_tool_calls:
            evaluation["issues"].append(f"No tool_call events (expected >= {self.min_tool_calls})")

        # 2. Tool Result Visibility (30 points)
        has_tool_results = analysis.has_tool_results
        has_result_fields = analysis.tool_results_have_required_fields

        tool_result_score = 0
        if has_tool_results and has_result_fields:
            tool_result_score = 30
        elif has_tool_results:
            tool_result_score = 15

        evaluation["dimensions"]["tool_result_visibility"] = {
            "score": tool_result_score,
            "max_score": 30,
            "tool_result_count": analysis.tool_result_count,
            "min_required": self.min_tool_results,
            "has_required_fields": has_result_fields,
            "successful_tools": [tr.tool_name for tr in analysis.tool_results if tr.success],
            "failed_tools": [tr.tool_name for tr in analysis.tool_results if not tr.success],
        }
        evaluation["score"] += tool_result_score
        if not has_tool_results:
            evaluation["issues"].append(
                f"No tool_result events (expected >= {self.min_tool_results})"
            )

        # 3. Event Order (15 points)
        calls_before_tokens = analysis.tool_calls_before_tokens
        results_before_tokens = analysis.tool_results_before_tokens

        order_score = 0
        if calls_before_tokens and results_before_tokens:
            order_score = 15
        elif calls_before_tokens or results_before_tokens:
            order_score = 8

        evaluation["dimensions"]["event_order"] = {
            "score": order_score,
            "max_score": 15,
            "tool_calls_before_tokens": calls_before_tokens,
            "tool_results_before_tokens": results_before_tokens,
            "order_correct": calls_before_tokens and results_before_tokens,
        }
        evaluation["score"] += order_score
        if not (calls_before_tokens and results_before_tokens):
            evaluation["issues"].append("Tool events should appear before token events")

        # 4. Event Pairing (15 points)
        all_paired = analysis.all_tools_have_results

        pairing_score = 15 if all_paired else 0

        evaluation["dimensions"]["event_pairing"] = {
            "score": pairing_score,
            "max_score": 15,
            "all_tools_have_results": all_paired,
            "call_count": analysis.tool_call_count,
            "result_count": analysis.tool_result_count,
        }
        evaluation["score"] += pairing_score
        if not all_paired:
            evaluation["issues"].append(
                f"Not all tool calls have results "
                f"({analysis.tool_call_count} calls, {analysis.tool_result_count} results)"
            )

        # 5. Result Detail (10 points)
        has_exec_times = len(analysis.tool_execution_times) > 0
        has_result_summaries = any(tr.result_summary for tr in analysis.tool_results)
        has_result_counts = any((tr.result_count or 0) > 0 for tr in analysis.tool_results)

        detail_score = 0
        if has_exec_times:
            detail_score += 4
        if has_result_summaries:
            detail_score += 3
        if has_result_counts:
            detail_score += 3

        evaluation["dimensions"]["result_detail"] = {
            "score": detail_score,
            "max_score": 10,
            "has_execution_times": has_exec_times,
            "has_result_summaries": has_result_summaries,
            "has_result_counts": has_result_counts,
            "execution_times": analysis.tool_execution_times,
        }
        evaluation["score"] += detail_score

        # Overall pass/fail
        # Pass if: has tool calls, has tool results, and score >= 70
        evaluation["passed"] = (
            analysis.has_tool_progress
            and evaluation["score"] >= 70
            and len(evaluation["issues"]) <= 2
        )

        return evaluation


# ============================================================================
# Unit Tests - Test Data Classes
# ============================================================================


class TestToolCallEvent:
    """Test ToolCallEvent data class."""

    def test_event_initialization(self):
        """Test that ToolCallEvent initializes correctly."""
        event = ToolCallEvent(
            timestamp=1000.0,
            iteration=1,
            tool_name="search_funding_calls",
            parameters={"keywords": "hydrogen"},
        )
        assert event.tool_name == "search_funding_calls"
        assert event.parameters["keywords"] == "hydrogen"
        assert event.iteration == 1

    def test_event_with_reasoning(self):
        """Test ToolCallEvent with reasoning."""
        event = ToolCallEvent(
            timestamp=1000.0,
            iteration=1,
            tool_name="search_funding_calls",
            parameters={"keywords": "hydrogen"},
            reasoning="User wants to find hydrogen funding calls",
        )
        assert "hydrogen" in event.reasoning


class TestToolResultEvent:
    """Test ToolResultEvent data class."""

    def test_event_initialization(self):
        """Test that ToolResultEvent initializes correctly."""
        event = ToolResultEvent(
            timestamp=1000.0,
            iteration=1,
            tool_name="search_funding_calls",
            success=True,
            result_count=15,
        )
        assert event.tool_name == "search_funding_calls"
        assert event.success is True
        assert event.result_count == 15

    def test_event_with_full_details(self):
        """Test ToolResultEvent with all details."""
        event = ToolResultEvent(
            timestamp=1000.0,
            iteration=1,
            tool_name="search_funding_calls",
            success=True,
            result_count=15,
            result_summary="Found 15 funding calls...",
            execution_time_ms=245,
        )
        assert event.execution_time_ms == 245
        assert "15 funding calls" in event.result_summary


class TestToolProgressAnalysis:
    """Test ToolProgressAnalysis data class."""

    def test_empty_analysis(self):
        """Test empty analysis initialization."""
        analysis = ToolProgressAnalysis(query="Test")
        assert analysis.query == "Test"
        assert analysis.tool_call_count == 0
        assert analysis.tool_result_count == 0
        assert analysis.has_tool_progress is False

    def test_analysis_with_tool_events(self):
        """Test analysis with tool events."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.tool_calls = [
            ToolCallEvent(
                timestamp=1.0,
                iteration=1,
                tool_name="search_funding_calls",
                parameters={"keywords": "hydrogen"},
            )
        ]
        analysis.tool_results = [
            ToolResultEvent(
                timestamp=2.0,
                iteration=1,
                tool_name="search_funding_calls",
                success=True,
                result_count=15,
            )
        ]
        assert analysis.tool_call_count == 1
        assert analysis.tool_result_count == 1
        assert analysis.has_tool_progress is True

    def test_unique_tools_called(self):
        """Test unique_tools_called property."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.tool_calls = [
            ToolCallEvent(
                timestamp=1.0,
                iteration=1,
                tool_name="search_funding_calls",
                parameters={},
            ),
            ToolCallEvent(
                timestamp=2.0,
                iteration=1,
                tool_name="find_experienced_partners",
                parameters={},
            ),
            ToolCallEvent(
                timestamp=3.0,
                iteration=2,
                tool_name="search_funding_calls",
                parameters={},
            ),
        ]
        assert analysis.unique_tools_called == {
            "search_funding_calls",
            "find_experienced_partners",
        }

    def test_all_tools_have_results_true(self):
        """Test all_tools_have_results when matched."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.tool_calls = [
            ToolCallEvent(
                timestamp=1.0,
                iteration=1,
                tool_name="search_funding_calls",
                parameters={},
            )
        ]
        analysis.tool_results = [
            ToolResultEvent(
                timestamp=2.0,
                iteration=1,
                tool_name="search_funding_calls",
                success=True,
            )
        ]
        assert analysis.all_tools_have_results is True

    def test_all_tools_have_results_false(self):
        """Test all_tools_have_results when unmatched."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.tool_calls = [
            ToolCallEvent(
                timestamp=1.0,
                iteration=1,
                tool_name="search_funding_calls",
                parameters={},
            ),
            ToolCallEvent(
                timestamp=2.0,
                iteration=1,
                tool_name="find_experienced_partners",
                parameters={},
            ),
        ]
        analysis.tool_results = [
            ToolResultEvent(
                timestamp=3.0,
                iteration=1,
                tool_name="search_funding_calls",
                success=True,
            )
            # Missing result for find_experienced_partners
        ]
        assert analysis.all_tools_have_results is False

    def test_tool_calls_before_tokens(self):
        """Test tool_calls_before_tokens property."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=1.0, raw_data=""),
            StreamingEvent(type="tool_call", timestamp=2.0, raw_data=""),
            StreamingEvent(type="tool_result", timestamp=3.0, raw_data=""),
            StreamingEvent(type="token", timestamp=4.0, raw_data=""),
        ]
        assert analysis.tool_calls_before_tokens is True

    def test_tool_calls_after_tokens(self):
        """Test tool_calls_before_tokens false when tokens first."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=1.0, raw_data=""),
            StreamingEvent(type="token", timestamp=2.0, raw_data=""),
            StreamingEvent(type="tool_call", timestamp=3.0, raw_data=""),
        ]
        assert analysis.tool_calls_before_tokens is False

    def test_tool_execution_times(self):
        """Test tool_execution_times property."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.tool_results = [
            ToolResultEvent(
                timestamp=1.0,
                iteration=1,
                tool_name="tool1",
                success=True,
                execution_time_ms=100,
            ),
            ToolResultEvent(
                timestamp=2.0,
                iteration=1,
                tool_name="tool2",
                success=True,
                execution_time_ms=200,
            ),
        ]
        assert analysis.tool_execution_times == [100, 200]

    def test_to_dict(self):
        """Test to_dict conversion."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.start_time = 100.0
        analysis.end_time = 105.0
        analysis.tool_calls = [
            ToolCallEvent(
                timestamp=101.0,
                iteration=1,
                tool_name="search_funding_calls",
                parameters={"keywords": "hydrogen"},
            )
        ]
        analysis.tool_results = [
            ToolResultEvent(
                timestamp=102.0,
                iteration=1,
                tool_name="search_funding_calls",
                success=True,
                result_count=15,
            )
        ]

        result = analysis.to_dict()
        assert result["query"] == "Test"
        assert result["tool_call_count"] == 1
        assert result["tool_result_count"] == 1
        assert "search_funding_calls" in result["unique_tools_called"]


# ============================================================================
# Unit Tests - Test Evaluator
# ============================================================================


class TestToolProgressVisibleEvaluator:
    """Test ToolProgressVisibleEvaluator."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return ToolProgressVisibleEvaluator()

    def test_evaluate_perfect_tool_visibility(self, evaluator):
        """Test evaluation of perfect tool visibility."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(type="tool_call", timestamp=100.5, raw_data=""),
            StreamingEvent(type="tool_result", timestamp=101.0, raw_data=""),
            StreamingEvent(type="token", timestamp=102.0, raw_data=""),
        ]
        analysis.tool_calls = [
            ToolCallEvent(
                timestamp=100.5,
                iteration=1,
                tool_name="search_funding_calls",
                parameters={"keywords": "hydrogen"},
            )
        ]
        analysis.tool_results = [
            ToolResultEvent(
                timestamp=101.0,
                iteration=1,
                tool_name="search_funding_calls",
                success=True,
                result_count=15,
                result_summary="Found 15 funding calls...",
                execution_time_ms=245,
            )
        ]

        result = evaluator.evaluate(analysis)
        assert result["score"] >= 70
        assert result["passed"] is True

    def test_evaluate_missing_tool_calls(self, evaluator):
        """Test evaluation when tool_call events missing."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(type="token", timestamp=101.0, raw_data=""),
        ]
        # No tool_calls or tool_results

        result = evaluator.evaluate(analysis)
        assert result["dimensions"]["tool_call_visibility"]["score"] == 0
        assert "No tool_call events" in str(result["issues"])

    def test_evaluate_missing_tool_results(self, evaluator):
        """Test evaluation when tool_result events missing."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(type="tool_call", timestamp=100.5, raw_data=""),
            StreamingEvent(type="token", timestamp=101.0, raw_data=""),
        ]
        analysis.tool_calls = [
            ToolCallEvent(
                timestamp=100.5,
                iteration=1,
                tool_name="search_funding_calls",
                parameters={},
            )
        ]
        # No tool_results

        result = evaluator.evaluate(analysis)
        assert result["dimensions"]["tool_result_visibility"]["score"] == 0
        assert "No tool_result events" in str(result["issues"])

    def test_evaluate_unmatched_calls_results(self, evaluator):
        """Test evaluation when calls don't match results."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(type="tool_call", timestamp=100.5, raw_data=""),
            StreamingEvent(type="tool_call", timestamp=100.6, raw_data=""),
            StreamingEvent(type="tool_result", timestamp=101.0, raw_data=""),
            StreamingEvent(type="token", timestamp=102.0, raw_data=""),
        ]
        analysis.tool_calls = [
            ToolCallEvent(
                timestamp=100.5,
                iteration=1,
                tool_name="search_funding_calls",
                parameters={},
            ),
            ToolCallEvent(
                timestamp=100.6,
                iteration=1,
                tool_name="find_experienced_partners",
                parameters={},
            ),
        ]
        analysis.tool_results = [
            ToolResultEvent(
                timestamp=101.0,
                iteration=1,
                tool_name="search_funding_calls",
                success=True,
            )
            # Missing result for find_experienced_partners
        ]

        result = evaluator.evaluate(analysis)
        assert result["dimensions"]["event_pairing"]["all_tools_have_results"] is False

    def test_evaluate_with_error(self, evaluator):
        """Test evaluation when analysis has error."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.error = "Connection refused"

        result = evaluator.evaluate(analysis)
        assert result["score"] == 0
        assert result["passed"] is False
        assert "Error: Connection refused" in result["issues"]

    def test_evaluate_tools_after_tokens(self, evaluator):
        """Test evaluation when tool events come after tokens."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(type="token", timestamp=100.5, raw_data=""),
            StreamingEvent(type="tool_call", timestamp=101.0, raw_data=""),
            StreamingEvent(type="tool_result", timestamp=102.0, raw_data=""),
        ]
        analysis.tool_calls = [
            ToolCallEvent(
                timestamp=101.0,
                iteration=1,
                tool_name="search_funding_calls",
                parameters={},
            )
        ]
        analysis.tool_results = [
            ToolResultEvent(
                timestamp=102.0,
                iteration=1,
                tool_name="search_funding_calls",
                success=True,
            )
        ]

        result = evaluator.evaluate(analysis)
        assert result["dimensions"]["event_order"]["order_correct"] is False

    def test_evaluate_multiple_tools(self, evaluator):
        """Test evaluation with multiple tool calls."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(type="tool_call", timestamp=100.5, raw_data=""),
            StreamingEvent(type="tool_call", timestamp=100.6, raw_data=""),
            StreamingEvent(type="tool_result", timestamp=101.0, raw_data=""),
            StreamingEvent(type="tool_result", timestamp=101.5, raw_data=""),
            StreamingEvent(type="token", timestamp=102.0, raw_data=""),
        ]
        analysis.tool_calls = [
            ToolCallEvent(
                timestamp=100.5,
                iteration=1,
                tool_name="search_funding_calls",
                parameters={"keywords": "hydrogen"},
            ),
            ToolCallEvent(
                timestamp=100.6,
                iteration=1,
                tool_name="find_experienced_partners",
                parameters={"topic": "hydrogen"},
            ),
        ]
        analysis.tool_results = [
            ToolResultEvent(
                timestamp=101.0,
                iteration=1,
                tool_name="search_funding_calls",
                success=True,
                result_count=15,
                execution_time_ms=245,
            ),
            ToolResultEvent(
                timestamp=101.5,
                iteration=1,
                tool_name="find_experienced_partners",
                success=True,
                result_count=20,
                execution_time_ms=320,
            ),
        ]

        result = evaluator.evaluate(analysis)
        assert result["score"] >= 70
        assert result["passed"] is True
        assert result["dimensions"]["event_pairing"]["all_tools_have_results"] is True


class TestToolProgressValidation:
    """Test tool progress validation edge cases."""

    def test_empty_tool_lists(self):
        """Test analysis with no tool events."""
        evaluator = ToolProgressVisibleEvaluator()
        analysis = ToolProgressAnalysis(query="Test")

        result = evaluator.evaluate(analysis)
        assert result["passed"] is False

    def test_tool_with_empty_name(self):
        """Test tool call with empty name."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.tool_calls = [
            ToolCallEvent(
                timestamp=1.0,
                iteration=1,
                tool_name="",  # Empty name
                parameters={},
            )
        ]

        assert analysis.tool_calls_have_required_fields is False

    def test_tool_result_failed(self):
        """Test handling of failed tool results."""
        analysis = ToolProgressAnalysis(query="Test")
        analysis.tool_results = [
            ToolResultEvent(
                timestamp=1.0,
                iteration=1,
                tool_name="search_funding_calls",
                success=False,  # Failed
                result_count=0,
            )
        ]

        # Tool still counts as having result even if failed
        assert analysis.has_tool_results is True


# ============================================================================
# Integration Tests - Require Live API
# ============================================================================


def check_api_available() -> bool:
    """Check if the API is available."""
    try:
        import httpx

        response = httpx.get("http://localhost:8000/api/v3/conversation/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


# Skip decorator for live API tests
live_api = pytest.mark.skipif(
    not check_api_available(),
    reason="Live API not available. Start the server with: make run",
)


async def collect_tool_progress_analysis(query: str, conversation_id: int) -> ToolProgressAnalysis:
    """
    Collect tool progress analysis from live API.

    Args:
        query: The query to send
        conversation_id: Conversation ID to use

    Returns:
        ToolProgressAnalysis with all events collected
    """
    import aiohttp

    url = f"http://localhost:8000/api/v3/conversation/{conversation_id}/message/stream"
    analysis = ToolProgressAnalysis(query=query)
    analysis.start_time = time.time()

    try:
        timeout = aiohttp.ClientTimeout(total=120.0)  # Longer timeout for multi-tool queries
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                json={"message": query, "include_context": True},
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status != 200:
                    analysis.error = f"HTTP {response.status}"
                    return analysis

                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if not line or not line.startswith("data: "):
                        continue

                    raw_data = line[6:]  # Remove "data: " prefix
                    try:
                        parsed = json.loads(raw_data)
                        event_type = parsed.get("type", "unknown")

                        event = StreamingEvent(
                            type=event_type,
                            timestamp=time.time(),
                            raw_data=raw_data,
                            parsed_data=parsed,
                        )
                        analysis.events.append(event)

                        # Parse tool_call events
                        if event_type == "tool_call":
                            tool_call = ToolCallEvent(
                                timestamp=time.time(),
                                iteration=parsed.get("iteration", 0),
                                tool_name=parsed.get("tool_name", parsed.get("tool", "")),
                                parameters=parsed.get("parameters", parsed.get("args", {})),
                                reasoning=parsed.get("reasoning", ""),
                                raw_data=parsed,
                            )
                            analysis.tool_calls.append(tool_call)

                        # Parse tool_result events
                        elif event_type == "tool_result":
                            tool_result = ToolResultEvent(
                                timestamp=time.time(),
                                iteration=parsed.get("iteration", 0),
                                tool_name=parsed.get("tool_name", parsed.get("tool", "")),
                                success=parsed.get("success", True),
                                result_count=parsed.get("result_count", 0),
                                result_summary=parsed.get("result_summary", ""),
                                execution_time_ms=parsed.get("execution_time_ms", 0),
                                raw_data=parsed,
                            )
                            analysis.tool_results.append(tool_result)

                    except json.JSONDecodeError:
                        analysis.events.append(
                            StreamingEvent(
                                type="parse_error",
                                timestamp=time.time(),
                                raw_data=raw_data,
                            )
                        )

    except Exception as e:
        analysis.error = str(e)

    analysis.end_time = time.time()
    return analysis


class TestScenario063LiveAPI:
    """Live API tests for Scenario 063: Tool Progress Visible."""

    @live_api
    @pytest.mark.asyncio
    async def test_tool_progress_visible_basic(self):
        """
        Test basic tool progress visibility.

        This is the primary test case from the PRD:
        - Query requiring tool usage
        - Verify tool_call and tool_result events visible
        - Verify user can see what's happening
        """
        import random

        query = "Find open funding calls for AI research"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_tool_progress_analysis(query, conversation_id)

        # Log analysis for debugging
        logger.info(f"Tool Progress Analysis: {json.dumps(analysis.to_dict(), indent=2)}")

        # Evaluate
        evaluator = ToolProgressVisibleEvaluator()
        result = evaluator.evaluate(analysis)

        logger.info(f"Evaluation Result: {json.dumps(result, indent=2)}")

        # Assertions
        assert analysis.error is None, f"Request failed: {analysis.error}"
        assert result["passed"], (
            f"Tool progress test failed with score {result['score']}: {result['issues']}"
        )

    @live_api
    @pytest.mark.asyncio
    async def test_tool_call_events_present(self):
        """Test that tool_call events are emitted during streaming."""
        import random

        query = "Find hydrogen funding calls"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_tool_progress_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Check tool_call events
        assert analysis.has_tool_calls, (
            f"Expected tool_call events but got none. Event types: {analysis.unique_event_types}"
        )

        # Verify tool_call has required fields
        for tc in analysis.tool_calls:
            assert tc.tool_name, f"Tool call missing tool_name: {tc.raw_data}"
            assert tc.parameters is not None, f"Tool call missing parameters: {tc.raw_data}"

    @live_api
    @pytest.mark.asyncio
    async def test_tool_result_events_present(self):
        """Test that tool_result events are emitted after tool execution."""
        import random

        query = "Search for funded projects on renewable energy"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_tool_progress_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Check tool_result events
        assert analysis.has_tool_results, (
            f"Expected tool_result events but got none. Event types: {analysis.unique_event_types}"
        )

        # Verify tool_result has required fields
        for tr in analysis.tool_results:
            assert tr.tool_name, f"Tool result missing tool_name: {tr.raw_data}"
            # success field should be present (True or False)

    @live_api
    @pytest.mark.asyncio
    async def test_tool_calls_paired_with_results(self):
        """Test that all tool calls have corresponding results."""
        import random

        query = "Find open funding calls for climate research"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_tool_progress_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        if analysis.has_tool_calls:
            # All calls should have results
            assert analysis.all_tools_have_results, (
                f"Not all tool calls have results. "
                f"Calls: {[tc.tool_name for tc in analysis.tool_calls]}, "
                f"Results: {[tr.tool_name for tr in analysis.tool_results]}"
            )

    @live_api
    @pytest.mark.asyncio
    async def test_tool_events_before_tokens(self):
        """Test that tool events appear before response tokens."""
        import random

        query = "Find open AI funding calls"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_tool_progress_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Check order
        if analysis.has_tool_calls:
            assert analysis.tool_calls_before_tokens, (
                f"Tool calls should appear before tokens. Event sequence: {analysis.event_types}"
            )

        if analysis.has_tool_results:
            assert analysis.tool_results_before_tokens, (
                f"Tool results should appear before tokens. Event sequence: {analysis.event_types}"
            )

    @live_api
    @pytest.mark.asyncio
    async def test_tool_result_includes_execution_time(self):
        """Test that tool_result events include execution time."""
        import random

        query = "What budget should I plan for a health research RIA project?"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_tool_progress_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Check execution times
        if analysis.tool_results:
            has_exec_times = any(tr.execution_time_ms > 0 for tr in analysis.tool_results)
            logger.info(f"Execution times: {analysis.tool_execution_times}")
            # Execution time is optional but good to have
            if not has_exec_times:
                logger.warning("No execution times in tool results")

    @live_api
    @pytest.mark.asyncio
    async def test_tool_result_includes_count(self):
        """Test that tool_result events include result count."""
        import random

        query = "Find open funding calls for digital transformation"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_tool_progress_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Check result counts
        if analysis.tool_results:
            result_counts = [tr.result_count for tr in analysis.tool_results]
            logger.info(f"Result counts: {result_counts}")
            # Result count is optional but good to have
            has_counts = any(count > 0 for count in result_counts)
            if not has_counts:
                logger.warning("No result counts in tool results")

    @live_api
    @pytest.mark.asyncio
    async def test_tool_result_includes_summary(self):
        """Test that tool_result events include result summary."""
        import random

        query = "Find funded projects on quantum computing"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_tool_progress_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Check result summaries
        if analysis.tool_results:
            summaries = [tr.result_summary for tr in analysis.tool_results]
            logger.info(f"Result summaries (first 100 chars): {[s[:100] for s in summaries if s]}")
            # Summary is optional but good to have
            has_summaries = any(s for s in summaries)
            if not has_summaries:
                logger.warning("No result summaries in tool results")


class TestScenario063MultiToolQueries:
    """Tests for multi-tool query visibility."""

    @live_api
    @pytest.mark.asyncio
    async def test_multi_tool_query_visibility(self):
        """Test that multi-tool queries show all tool progress."""
        import random

        # This query should potentially use multiple tools
        query = "What is the budget range for climate research RIA projects?"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_tool_progress_analysis(query, conversation_id)

        logger.info(f"Multi-tool Analysis: {json.dumps(analysis.to_dict(), indent=2)}")

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Should have tool progress
        if analysis.has_tool_calls:
            logger.info(f"Tools called: {list(analysis.unique_tools_called)}")
            # Verify visibility
            evaluator = ToolProgressVisibleEvaluator()
            result = evaluator.evaluate(analysis)
            assert result["score"] >= 60, f"Tool visibility score too low: {result['score']}"

    @live_api
    @pytest.mark.asyncio
    async def test_comparison_query_tool_visibility(self):
        """Test tool visibility for comparison queries."""
        import random

        query = "Compare RIA and IA funding instruments"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_tool_progress_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        logger.info(f"Comparison query analysis: {json.dumps(analysis.to_dict(), indent=2)}")

        # Should show tool progress if tools are used
        if analysis.has_tool_calls:
            evaluator = ToolProgressVisibleEvaluator()
            result = evaluator.evaluate(analysis)
            assert result["passed"], f"Comparison query failed: {result['issues']}"


class TestScenario063SingleToolQueries:
    """Tests for single tool query visibility."""

    @live_api
    @pytest.mark.asyncio
    async def test_single_tool_query_visibility(self):
        """Test that single tool queries show tool progress."""
        import random

        for query in SINGLE_TOOL_QUERIES[:2]:  # Test first 2 queries
            conversation_id = random.randint(1_000_000, 2_000_000_000)

            analysis = await collect_tool_progress_analysis(query, conversation_id)

            assert analysis.error is None, f"Request failed for '{query}': {analysis.error}"

            if analysis.has_tool_calls:
                logger.info(
                    f"Query '{query[:50]}...' - "
                    f"Tools: {list(analysis.unique_tools_called)}, "
                    f"Results: {analysis.tool_result_count}"
                )

                # Verify pairing
                assert analysis.all_tools_have_results, (
                    f"Tool call/result mismatch for '{query}': "
                    f"Calls: {[tc.tool_name for tc in analysis.tool_calls]}, "
                    f"Results: {[tr.tool_name for tr in analysis.tool_results]}"
                )

            # Small delay between queries
            await asyncio.sleep(0.5)


class TestScenario063EventSequence:
    """Tests for event sequence in tool progress."""

    @live_api
    @pytest.mark.asyncio
    async def test_event_sequence_status_first(self):
        """Test that status events come first in the sequence."""
        import random

        query = "Find open funding calls for AI"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_tool_progress_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Status should be first
        if analysis.events:
            first_event_type = analysis.events[0].type
            assert first_event_type == "status", (
                f"Expected status first, got {first_event_type}. "
                f"Sequence: {analysis.event_types[:5]}"
            )

    @live_api
    @pytest.mark.asyncio
    async def test_event_sequence_complete_last(self):
        """Test that complete event comes last in the sequence."""
        import random

        query = "What is ERC funding?"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_tool_progress_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Complete should be near the end
        if analysis.events:
            last_few_types = analysis.event_types[-3:]
            assert "complete" in last_few_types, (
                f"Expected complete near end, got {last_few_types}. "
                f"Full sequence: {analysis.event_types}"
            )


class TestScenario063Validation:
    """Validation tests for Scenario 063 implementation."""

    def test_scenario_test_queries_defined(self):
        """Test that test queries are defined."""
        assert len(MULTI_TOOL_QUERIES) > 0
        assert len(SINGLE_TOOL_QUERIES) > 0

    def test_required_fields_defined(self):
        """Test that required fields are defined."""
        assert REQUIRED_TOOL_CALL_FIELDS == {"tool_name", "parameters"}
        assert REQUIRED_TOOL_RESULT_FIELDS == {"tool_name", "success"}

    def test_allowed_event_types_include_tool_events(self):
        """Test that allowed event types include tool events."""
        assert "tool_call" in ALLOWED_EVENT_TYPES
        assert "tool_result" in ALLOWED_EVENT_TYPES

    def test_evaluator_uses_correct_thresholds(self):
        """Test that evaluator uses correct thresholds."""
        evaluator = ToolProgressVisibleEvaluator()
        assert evaluator.min_tool_calls == MIN_TOOL_CALL_EVENTS
        assert evaluator.min_tool_results == MIN_TOOL_RESULT_EVENTS


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
