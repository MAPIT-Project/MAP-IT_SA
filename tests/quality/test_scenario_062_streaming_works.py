"""
Tests for Scenario 062: Streaming Works - SSE Functionality Verification

PRD Reference:
- Send query to streaming endpoint
- Expected: Tokens stream progressively, status updates shown
- Verify: SSE events received correctly
- Fix if: All-at-once response, broken streaming
- Pass threshold: Streaming functional

This scenario tests that streaming responses work correctly:
1. SSE events are received in correct format (data: {json}\n\n)
2. Tokens stream progressively (multiple token events over time)
3. Status updates are shown before tokens
4. Required event types are present (status, token, complete)
5. Events arrive in proper order (status → agent events → tokens → complete)
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

# Minimum requirements for streaming to be considered "working"
MIN_TOKEN_EVENTS = 3  # At least 3 token events for progressive streaming
MIN_STATUS_EVENTS = 1  # At least 1 status event before tokens
MAX_INTER_TOKEN_GAP_SECONDS = 5.0  # Tokens should not be delayed more than 5s apart
MIN_STREAMING_DURATION_SECONDS = 0.1  # Streaming should take some time (not instant)

# Required event types for a valid streaming response
REQUIRED_EVENT_TYPES = {"status", "token", "complete"}

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

# Test queries
STREAMING_TEST_QUERIES = [
    "What is RIA funding?",
    "Find hydrogen funding calls",
    "What are the ERC grant types?",
]


# ============================================================================
# Data Classes for Streaming Analysis
# ============================================================================


@dataclass
class StreamingEvent:
    """Represents a single SSE event received during streaming."""

    type: str
    timestamp: float
    raw_data: str
    parsed_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamingAnalysis:
    """Analysis of a streaming response session."""

    query: str
    events: list[StreamingEvent] = field(default_factory=list)
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
    def token_events(self) -> list[StreamingEvent]:
        """List of all token events."""
        return [e for e in self.events if e.type == "token"]

    @property
    def status_events(self) -> list[StreamingEvent]:
        """List of all status events."""
        return [e for e in self.events if e.type == "status"]

    @property
    def token_count(self) -> int:
        """Number of token events received."""
        return len(self.token_events)

    @property
    def first_token_timestamp(self) -> float | None:
        """Timestamp of first token event."""
        tokens = self.token_events
        return tokens[0].timestamp if tokens else None

    @property
    def last_token_timestamp(self) -> float | None:
        """Timestamp of last token event."""
        tokens = self.token_events
        return tokens[-1].timestamp if tokens else None

    @property
    def token_spread_seconds(self) -> float | None:
        """Time between first and last token."""
        first = self.first_token_timestamp
        last = self.last_token_timestamp
        if first is None or last is None:
            return None
        return last - first

    @property
    def inter_token_gaps(self) -> list[float]:
        """Time gaps between consecutive token events."""
        tokens = self.token_events
        if len(tokens) < 2:
            return []
        return [tokens[i + 1].timestamp - tokens[i].timestamp for i in range(len(tokens) - 1)]

    @property
    def max_inter_token_gap(self) -> float | None:
        """Maximum gap between consecutive tokens."""
        gaps = self.inter_token_gaps
        return max(gaps) if gaps else None

    @property
    def has_required_events(self) -> bool:
        """Check if all required event types are present."""
        return REQUIRED_EVENT_TYPES.issubset(self.unique_event_types)

    @property
    def has_progressive_streaming(self) -> bool:
        """Check if tokens are streamed progressively (not all at once)."""
        if self.token_count < MIN_TOKEN_EVENTS:
            return False
        spread = self.token_spread_seconds
        return spread is not None and spread >= MIN_STREAMING_DURATION_SECONDS

    @property
    def has_status_before_tokens(self) -> bool:
        """Check if status events appear before token events."""
        first_token_idx = next((i for i, e in enumerate(self.events) if e.type == "token"), None)
        first_status_idx = next((i for i, e in enumerate(self.events) if e.type == "status"), None)
        if first_token_idx is None or first_status_idx is None:
            return False
        return first_status_idx < first_token_idx

    @property
    def has_complete_event(self) -> bool:
        """Check if complete event was received."""
        return "complete" in self.unique_event_types

    @property
    def complete_comes_last(self) -> bool:
        """Check if complete event is the last significant event."""
        if not self.events:
            return False
        # Complete should be one of the last events (allow for trailing status)
        last_few_types = self.event_types[-3:] if len(self.events) >= 3 else self.event_types
        return "complete" in last_few_types

    @property
    def all_events_valid(self) -> bool:
        """Check if all received event types are valid/allowed."""
        return all(e.type in ALLOWED_EVENT_TYPES for e in self.events)

    @property
    def accumulated_response(self) -> str:
        """Accumulated text from all token events."""
        return "".join(e.parsed_data.get("content", "") for e in self.token_events)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "query": self.query,
            "duration_seconds": self.duration_seconds,
            "total_events": len(self.events),
            "token_count": self.token_count,
            "unique_event_types": list(self.unique_event_types),
            "event_sequence": self.event_types,
            "has_required_events": self.has_required_events,
            "has_progressive_streaming": self.has_progressive_streaming,
            "has_status_before_tokens": self.has_status_before_tokens,
            "has_complete_event": self.has_complete_event,
            "complete_comes_last": self.complete_comes_last,
            "all_events_valid": self.all_events_valid,
            "token_spread_seconds": self.token_spread_seconds,
            "max_inter_token_gap": self.max_inter_token_gap,
            "response_length": len(self.accumulated_response),
            "error": self.error,
        }


# ============================================================================
# Streaming Evaluator
# ============================================================================


class StreamingWorksEvaluator:
    """Evaluator for Scenario 062: Streaming Works."""

    def __init__(
        self,
        min_token_events: int = MIN_TOKEN_EVENTS,
        max_inter_token_gap: float = MAX_INTER_TOKEN_GAP_SECONDS,
    ):
        self.min_token_events = min_token_events
        self.max_inter_token_gap = max_inter_token_gap

    def evaluate(self, analysis: StreamingAnalysis) -> dict[str, Any]:
        """
        Evaluate a streaming analysis against requirements.

        Scoring (100 points total):
        - SSE Format (20 points): Events received in correct format
        - Progressive Streaming (25 points): Multiple tokens over time
        - Status Updates (15 points): Status events before tokens
        - Event Completeness (20 points): All required events present
        - Event Order (10 points): Events in correct order
        - Response Quality (10 points): Non-empty response accumulated
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

        # 1. SSE Format (20 points)
        sse_score = 20 if analysis.all_events_valid else 0
        evaluation["dimensions"]["sse_format"] = {
            "score": sse_score,
            "max_score": 20,
            "all_events_valid": analysis.all_events_valid,
            "invalid_types": [e.type for e in analysis.events if e.type not in ALLOWED_EVENT_TYPES],
        }
        evaluation["score"] += sse_score
        if not analysis.all_events_valid:
            invalid = [e.type for e in analysis.events if e.type not in ALLOWED_EVENT_TYPES]
            evaluation["issues"].append(f"Invalid event types: {invalid}")

        # 2. Progressive Streaming (25 points)
        progressive_streaming = analysis.has_progressive_streaming
        token_count_ok = analysis.token_count >= self.min_token_events
        inter_token_ok = (
            analysis.max_inter_token_gap is None
            or analysis.max_inter_token_gap <= self.max_inter_token_gap
        )

        progressive_score = 0
        if progressive_streaming and token_count_ok:
            progressive_score = 25 if inter_token_ok else 15
        elif token_count_ok:
            progressive_score = 10  # Has tokens but not progressive

        evaluation["dimensions"]["progressive_streaming"] = {
            "score": progressive_score,
            "max_score": 25,
            "token_count": analysis.token_count,
            "min_required": self.min_token_events,
            "token_spread_seconds": analysis.token_spread_seconds,
            "max_inter_token_gap": analysis.max_inter_token_gap,
            "is_progressive": progressive_streaming,
        }
        evaluation["score"] += progressive_score
        if not progressive_streaming:
            evaluation["issues"].append(
                f"Not progressive: {analysis.token_count} tokens, "
                f"spread={analysis.token_spread_seconds:.3f}s"
                if analysis.token_spread_seconds
                else f"Not progressive: only {analysis.token_count} tokens"
            )

        # 3. Status Updates (15 points)
        status_score = 15 if analysis.has_status_before_tokens else 0
        evaluation["dimensions"]["status_updates"] = {
            "score": status_score,
            "max_score": 15,
            "status_count": len(analysis.status_events),
            "status_before_tokens": analysis.has_status_before_tokens,
        }
        evaluation["score"] += status_score
        if not analysis.has_status_before_tokens:
            evaluation["issues"].append("No status events before tokens")

        # 4. Event Completeness (20 points)
        has_required = analysis.has_required_events
        completeness_score = 20 if has_required else 0
        missing_types = REQUIRED_EVENT_TYPES - analysis.unique_event_types

        evaluation["dimensions"]["event_completeness"] = {
            "score": completeness_score,
            "max_score": 20,
            "has_required_events": has_required,
            "missing_types": list(missing_types),
            "received_types": list(analysis.unique_event_types),
        }
        evaluation["score"] += completeness_score
        if not has_required:
            evaluation["issues"].append(f"Missing required events: {missing_types}")

        # 5. Event Order (10 points)
        order_ok = (
            analysis.has_status_before_tokens
            and analysis.has_complete_event
            and analysis.complete_comes_last
        )
        order_score = 10 if order_ok else 5 if analysis.has_complete_event else 0

        evaluation["dimensions"]["event_order"] = {
            "score": order_score,
            "max_score": 10,
            "status_before_tokens": analysis.has_status_before_tokens,
            "complete_comes_last": analysis.complete_comes_last,
            "order_correct": order_ok,
        }
        evaluation["score"] += order_score
        if not order_ok:
            evaluation["issues"].append("Event order incorrect")

        # 6. Response Quality (10 points)
        response = analysis.accumulated_response
        response_ok = len(response) >= 50  # At least 50 chars
        response_score = 10 if response_ok else 5 if len(response) >= 10 else 0

        evaluation["dimensions"]["response_quality"] = {
            "score": response_score,
            "max_score": 10,
            "response_length": len(response),
            "has_content": response_ok,
        }
        evaluation["score"] += response_score
        if not response_ok:
            evaluation["issues"].append(f"Response too short: {len(response)} chars")

        # Overall pass/fail (threshold: 80 points)
        evaluation["passed"] = evaluation["score"] >= 80 and len(evaluation["issues"]) <= 2

        return evaluation


# ============================================================================
# Unit Tests - Test Data Classes
# ============================================================================


class TestStreamingEvent:
    """Test StreamingEvent data class."""

    def test_event_initialization(self):
        """Test that StreamingEvent initializes correctly."""
        event = StreamingEvent(
            type="token", timestamp=1000.0, raw_data='{"type":"token","content":"Hello"}'
        )
        assert event.type == "token"
        assert event.timestamp == 1000.0
        assert event.raw_data == '{"type":"token","content":"Hello"}'

    def test_event_with_parsed_data(self):
        """Test StreamingEvent with parsed data."""
        event = StreamingEvent(
            type="token",
            timestamp=1000.0,
            raw_data='{"type":"token","content":"Hello"}',
            parsed_data={"type": "token", "content": "Hello"},
        )
        assert event.parsed_data["content"] == "Hello"


class TestStreamingAnalysis:
    """Test StreamingAnalysis data class."""

    def test_empty_analysis(self):
        """Test empty analysis initialization."""
        analysis = StreamingAnalysis(query="Test")
        assert analysis.query == "Test"
        assert analysis.events == []
        assert analysis.duration_seconds == 0.0
        assert analysis.token_count == 0

    def test_event_types_property(self):
        """Test event_types returns types in order."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=1.0, raw_data=""),
            StreamingEvent(type="token", timestamp=2.0, raw_data=""),
            StreamingEvent(type="token", timestamp=3.0, raw_data=""),
            StreamingEvent(type="complete", timestamp=4.0, raw_data=""),
        ]
        assert analysis.event_types == ["status", "token", "token", "complete"]

    def test_unique_event_types(self):
        """Test unique_event_types returns set."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=1.0, raw_data=""),
            StreamingEvent(type="token", timestamp=2.0, raw_data=""),
            StreamingEvent(type="token", timestamp=3.0, raw_data=""),
            StreamingEvent(type="complete", timestamp=4.0, raw_data=""),
        ]
        assert analysis.unique_event_types == {"status", "token", "complete"}

    def test_token_count(self):
        """Test token_count property."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=1.0, raw_data=""),
            StreamingEvent(type="token", timestamp=2.0, raw_data=""),
            StreamingEvent(type="token", timestamp=3.0, raw_data=""),
            StreamingEvent(type="token", timestamp=4.0, raw_data=""),
        ]
        assert analysis.token_count == 3

    def test_token_spread_seconds(self):
        """Test token_spread_seconds calculation."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="token", timestamp=100.0, raw_data=""),
            StreamingEvent(type="token", timestamp=101.5, raw_data=""),
            StreamingEvent(type="token", timestamp=103.0, raw_data=""),
        ]
        assert analysis.token_spread_seconds == 3.0

    def test_inter_token_gaps(self):
        """Test inter_token_gaps calculation."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="token", timestamp=100.0, raw_data=""),
            StreamingEvent(type="token", timestamp=101.0, raw_data=""),
            StreamingEvent(type="token", timestamp=103.0, raw_data=""),
        ]
        assert analysis.inter_token_gaps == [1.0, 2.0]

    def test_max_inter_token_gap(self):
        """Test max_inter_token_gap calculation."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="token", timestamp=100.0, raw_data=""),
            StreamingEvent(type="token", timestamp=101.0, raw_data=""),
            StreamingEvent(type="token", timestamp=105.0, raw_data=""),
        ]
        assert analysis.max_inter_token_gap == 4.0

    def test_has_required_events_true(self):
        """Test has_required_events when all present."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=1.0, raw_data=""),
            StreamingEvent(type="token", timestamp=2.0, raw_data=""),
            StreamingEvent(type="complete", timestamp=3.0, raw_data=""),
        ]
        assert analysis.has_required_events is True

    def test_has_required_events_false(self):
        """Test has_required_events when missing some."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=1.0, raw_data=""),
            StreamingEvent(type="token", timestamp=2.0, raw_data=""),
            # Missing complete
        ]
        assert analysis.has_required_events is False

    def test_has_progressive_streaming_true(self):
        """Test has_progressive_streaming when tokens spread over time."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="token", timestamp=100.0, raw_data=""),
            StreamingEvent(type="token", timestamp=100.1, raw_data=""),
            StreamingEvent(type="token", timestamp=100.2, raw_data=""),
            StreamingEvent(type="token", timestamp=100.3, raw_data=""),
        ]
        assert analysis.has_progressive_streaming is True

    def test_has_progressive_streaming_false_instant(self):
        """Test has_progressive_streaming false when tokens instant."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="token", timestamp=100.0, raw_data=""),
            StreamingEvent(type="token", timestamp=100.0, raw_data=""),
            StreamingEvent(type="token", timestamp=100.0, raw_data=""),
        ]
        assert analysis.has_progressive_streaming is False

    def test_has_progressive_streaming_false_too_few(self):
        """Test has_progressive_streaming false when too few tokens."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="token", timestamp=100.0, raw_data=""),
            StreamingEvent(type="token", timestamp=100.5, raw_data=""),
        ]
        # Only 2 tokens, need at least 3
        assert analysis.has_progressive_streaming is False

    def test_has_status_before_tokens(self):
        """Test has_status_before_tokens property."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=1.0, raw_data=""),
            StreamingEvent(type="token", timestamp=2.0, raw_data=""),
        ]
        assert analysis.has_status_before_tokens is True

    def test_has_status_before_tokens_false(self):
        """Test has_status_before_tokens false when tokens first."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="token", timestamp=1.0, raw_data=""),
            StreamingEvent(type="status", timestamp=2.0, raw_data=""),
        ]
        assert analysis.has_status_before_tokens is False

    def test_accumulated_response(self):
        """Test accumulated_response concatenates token content."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(
                type="token",
                timestamp=1.0,
                raw_data="",
                parsed_data={"content": "Hello "},
            ),
            StreamingEvent(
                type="token",
                timestamp=2.0,
                raw_data="",
                parsed_data={"content": "World"},
            ),
        ]
        assert analysis.accumulated_response == "Hello World"

    def test_to_dict(self):
        """Test to_dict conversion."""
        analysis = StreamingAnalysis(query="Test")
        analysis.start_time = 100.0
        analysis.end_time = 105.0
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(
                type="token",
                timestamp=101.0,
                raw_data="",
                parsed_data={"content": "Test response"},
            ),
            StreamingEvent(type="complete", timestamp=105.0, raw_data=""),
        ]

        result = analysis.to_dict()
        assert result["query"] == "Test"
        assert result["duration_seconds"] == 5.0
        assert result["token_count"] == 1
        assert "status" in result["unique_event_types"]


# ============================================================================
# Unit Tests - Test Evaluator
# ============================================================================


class TestStreamingWorksEvaluator:
    """Test StreamingWorksEvaluator."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return StreamingWorksEvaluator()

    def test_evaluate_perfect_streaming(self, evaluator):
        """Test evaluation of perfect streaming response."""
        analysis = StreamingAnalysis(query="Test")
        analysis.start_time = 100.0
        analysis.end_time = 105.0
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(
                type="token",
                timestamp=100.5,
                raw_data="",
                parsed_data={"content": "This is a test response "},
            ),
            StreamingEvent(
                type="token",
                timestamp=101.0,
                raw_data="",
                parsed_data={"content": "that has multiple tokens "},
            ),
            StreamingEvent(
                type="token",
                timestamp=101.5,
                raw_data="",
                parsed_data={"content": "streamed progressively."},
            ),
            StreamingEvent(type="complete", timestamp=105.0, raw_data=""),
        ]

        result = evaluator.evaluate(analysis)
        assert result["score"] >= 80
        assert result["passed"] is True

    def test_evaluate_missing_status(self, evaluator):
        """Test evaluation when status events missing."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(
                type="token",
                timestamp=100.0,
                raw_data="",
                parsed_data={"content": "Response without status "},
            ),
            StreamingEvent(
                type="token",
                timestamp=100.5,
                raw_data="",
                parsed_data={"content": "events before "},
            ),
            StreamingEvent(
                type="token",
                timestamp=101.0,
                raw_data="",
                parsed_data={"content": "tokens."},
            ),
            StreamingEvent(type="complete", timestamp=102.0, raw_data=""),
        ]

        result = evaluator.evaluate(analysis)
        # Should lose points for missing status
        assert result["dimensions"]["status_updates"]["score"] == 0
        assert "No status events before tokens" in result["issues"]

    def test_evaluate_missing_complete(self, evaluator):
        """Test evaluation when complete event missing."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(
                type="token",
                timestamp=100.5,
                raw_data="",
                parsed_data={"content": "Response without complete event."},
            ),
        ]

        result = evaluator.evaluate(analysis)
        # Should lose points for missing complete
        assert result["dimensions"]["event_completeness"]["score"] == 0
        assert "complete" in str(result["issues"])

    def test_evaluate_non_progressive(self, evaluator):
        """Test evaluation when streaming is not progressive (instant)."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            # All tokens at same timestamp = not progressive
            StreamingEvent(
                type="token",
                timestamp=100.5,
                raw_data="",
                parsed_data={"content": "Token 1 "},
            ),
            StreamingEvent(
                type="token",
                timestamp=100.5,
                raw_data="",
                parsed_data={"content": "Token 2 "},
            ),
            StreamingEvent(
                type="token",
                timestamp=100.5,
                raw_data="",
                parsed_data={"content": "Token 3"},
            ),
            StreamingEvent(type="complete", timestamp=100.5, raw_data=""),
        ]

        result = evaluator.evaluate(analysis)
        # Should lose points for non-progressive
        assert result["dimensions"]["progressive_streaming"]["is_progressive"] is False

    def test_evaluate_with_error(self, evaluator):
        """Test evaluation when analysis has error."""
        analysis = StreamingAnalysis(query="Test")
        analysis.error = "Connection refused"

        result = evaluator.evaluate(analysis)
        assert result["score"] == 0
        assert result["passed"] is False
        assert "Error: Connection refused" in result["issues"]

    def test_evaluate_invalid_event_types(self, evaluator):
        """Test evaluation with invalid event types."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(type="invalid_type", timestamp=100.5, raw_data=""),  # Invalid
            StreamingEvent(
                type="token",
                timestamp=101.0,
                raw_data="",
                parsed_data={"content": "Test response content."},
            ),
            StreamingEvent(type="complete", timestamp=102.0, raw_data=""),
        ]

        result = evaluator.evaluate(analysis)
        assert result["dimensions"]["sse_format"]["score"] == 0
        assert "invalid_type" in str(result["issues"])

    def test_evaluate_short_response(self, evaluator):
        """Test evaluation with very short response."""
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(
                type="token",
                timestamp=100.5,
                raw_data="",
                parsed_data={"content": "Hi"},  # Very short
            ),
            StreamingEvent(
                type="token",
                timestamp=101.0,
                raw_data="",
                parsed_data={"content": "!"},
            ),
            StreamingEvent(
                type="token",
                timestamp=101.5,
                raw_data="",
                parsed_data={"content": " "},
            ),
            StreamingEvent(type="complete", timestamp=102.0, raw_data=""),
        ]

        result = evaluator.evaluate(analysis)
        # Response "Hi! " is very short
        assert result["dimensions"]["response_quality"]["response_length"] == 4
        assert result["dimensions"]["response_quality"]["score"] < 10


class TestStreamingValidation:
    """Test streaming validation edge cases."""

    def test_empty_events_list(self):
        """Test analysis with no events."""
        evaluator = StreamingWorksEvaluator()
        analysis = StreamingAnalysis(query="Test")
        analysis.events = []

        result = evaluator.evaluate(analysis)
        assert result["passed"] is False
        assert result["score"] < 50

    def test_only_status_events(self):
        """Test analysis with only status events."""
        evaluator = StreamingWorksEvaluator()
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(type="status", timestamp=101.0, raw_data=""),
        ]

        result = evaluator.evaluate(analysis)
        assert result["passed"] is False
        # Should have status but no tokens/complete

    def test_single_token_event(self):
        """Test analysis with single token event."""
        evaluator = StreamingWorksEvaluator()
        analysis = StreamingAnalysis(query="Test")
        analysis.events = [
            StreamingEvent(type="status", timestamp=100.0, raw_data=""),
            StreamingEvent(
                type="token",
                timestamp=100.5,
                raw_data="",
                parsed_data={"content": "Single token response."},
            ),
            StreamingEvent(type="complete", timestamp=101.0, raw_data=""),
        ]

        result = evaluator.evaluate(analysis)
        # Only 1 token, so not progressive
        assert result["dimensions"]["progressive_streaming"]["token_count"] == 1


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


async def collect_streaming_analysis(query: str, conversation_id: int) -> StreamingAnalysis:
    """
    Collect streaming analysis from live API.

    Args:
        query: The query to send
        conversation_id: Conversation ID to use

    Returns:
        StreamingAnalysis with all events collected
    """
    import aiohttp

    url = f"http://localhost:8000/api/v3/conversation/{conversation_id}/message/stream"
    analysis = StreamingAnalysis(query=query)
    analysis.start_time = time.time()

    try:
        timeout = aiohttp.ClientTimeout(total=60.0)
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
                        event = StreamingEvent(
                            type=parsed.get("type", "unknown"),
                            timestamp=time.time(),
                            raw_data=raw_data,
                            parsed_data=parsed,
                        )
                        analysis.events.append(event)
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


class TestScenario062LiveAPI:
    """Live API tests for Scenario 062: Streaming Works."""

    @live_api
    @pytest.mark.asyncio
    async def test_streaming_works_basic(self):
        """
        Test basic streaming functionality.

        This is the primary test case from the PRD:
        - Send query to streaming endpoint
        - Verify SSE events received correctly
        - Verify tokens stream progressively
        """
        import random

        query = "What is RIA funding?"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_streaming_analysis(query, conversation_id)

        # Log analysis for debugging
        logger.info(f"Streaming Analysis: {json.dumps(analysis.to_dict(), indent=2)}")

        # Evaluate
        evaluator = StreamingWorksEvaluator()
        result = evaluator.evaluate(analysis)

        logger.info(f"Evaluation Result: {json.dumps(result, indent=2)}")

        # Assertions
        assert analysis.error is None, f"Request failed: {analysis.error}"
        assert result[
            "passed"
        ], f"Streaming test failed with score {result['score']}: {result['issues']}"

    @live_api
    @pytest.mark.asyncio
    async def test_sse_format_compliance(self):
        """Test that all events comply with SSE format."""
        import random

        query = "Find hydrogen funding calls"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_streaming_analysis(query, conversation_id)

        # Check SSE format
        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Verify all events have valid types
        for event in analysis.events:
            assert (
                event.type in ALLOWED_EVENT_TYPES or event.type == "agent_complete"
            ), f"Invalid event type: {event.type}"

        # Verify all events are valid JSON
        for event in analysis.events:
            assert (
                event.parsed_data is not None or event.type == "parse_error"
            ), f"Failed to parse event: {event.raw_data}"

    @live_api
    @pytest.mark.asyncio
    async def test_progressive_token_streaming(self):
        """Test that tokens are streamed progressively over time."""
        import random

        query = "What are the ERC grant types?"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_streaming_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Check progressive streaming
        assert (
            analysis.token_count >= MIN_TOKEN_EVENTS
        ), f"Expected at least {MIN_TOKEN_EVENTS} token events, got {analysis.token_count}"

        # Tokens should be spread over time
        spread = analysis.token_spread_seconds
        assert spread is not None, "No token spread calculated"
        assert (
            spread >= MIN_STREAMING_DURATION_SECONDS
        ), f"Token spread {spread:.3f}s too small (min: {MIN_STREAMING_DURATION_SECONDS}s)"

    @live_api
    @pytest.mark.asyncio
    async def test_status_events_before_tokens(self):
        """Test that status events appear before token events."""
        import random

        query = "What is Horizon Europe?"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_streaming_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Check status before tokens
        assert (
            analysis.has_status_before_tokens
        ), f"Status events should appear before tokens. Event sequence: {analysis.event_types}"

    @live_api
    @pytest.mark.asyncio
    async def test_complete_event_present(self):
        """Test that complete event is present at end of stream."""
        import random

        query = "What is an Innovation Action?"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_streaming_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Check complete event
        assert (
            analysis.has_complete_event
        ), f"Complete event missing. Event types: {analysis.unique_event_types}"

    @live_api
    @pytest.mark.asyncio
    async def test_response_content_accumulated(self):
        """Test that response content is accumulated from token events."""
        import random

        query = "What is RIA funding?"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_streaming_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Check response content
        response = analysis.accumulated_response
        assert len(response) >= 50, f"Response too short: {len(response)} chars"

        # Response should be relevant to query
        response_lower = response.lower()
        assert any(
            term in response_lower
            for term in ["ria", "research", "innovation", "action", "funding"]
        ), f"Response not relevant to query: {response[:200]}"

    @live_api
    @pytest.mark.asyncio
    async def test_multiple_queries_streaming(self):
        """Test streaming works across multiple different queries."""
        import random

        results = []

        for query in STREAMING_TEST_QUERIES:
            conversation_id = random.randint(1_000_000, 2_000_000_000)
            analysis = await collect_streaming_analysis(query, conversation_id)

            evaluator = StreamingWorksEvaluator()
            result = evaluator.evaluate(analysis)
            result["query"] = query
            results.append(result)

            # Small delay between queries
            await asyncio.sleep(0.5)

        # All queries should pass
        passed_count = sum(1 for r in results if r["passed"])
        pass_rate = passed_count / len(results)

        logger.info(f"Streaming pass rate: {pass_rate:.0%} ({passed_count}/{len(results)})")

        assert pass_rate >= 0.8, (
            f"Streaming pass rate {pass_rate:.0%} < 80%. "
            f"Failed: {[r['query'] for r in results if not r['passed']]}"
        )


class TestScenario062EventTypes:
    """Tests for specific event types in streaming responses."""

    @live_api
    @pytest.mark.asyncio
    async def test_agent_thinking_events(self):
        """Test that agent_thinking events are emitted during reasoning."""
        import random

        query = "Compare EIC and ERC grants"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_streaming_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Check for agent_thinking events (may not always be present)
        agent_thinking_count = len([e for e in analysis.events if e.type == "agent_thinking"])
        logger.info(f"Agent thinking events: {agent_thinking_count}")

        # Agent thinking events are optional but good to have
        # This test just verifies they are valid if present
        for event in analysis.events:
            if event.type == "agent_thinking":
                assert "thought" in event.parsed_data or "content" in event.parsed_data

    @live_api
    @pytest.mark.asyncio
    async def test_tool_call_events(self):
        """Test that tool_call events are emitted when tools are used."""
        import random

        query = "Find open funding calls for AI research"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_streaming_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Check for tool_call events
        tool_calls = [e for e in analysis.events if e.type == "tool_call"]
        logger.info(f"Tool call events: {len(tool_calls)}")

        # Tool calls should have tool name
        for event in tool_calls:
            assert "tool_name" in event.parsed_data or "tool" in event.parsed_data

    @live_api
    @pytest.mark.asyncio
    async def test_complete_event_metadata(self):
        """Test that complete event contains expected metadata."""
        import random

        query = "What is RIA funding?"
        conversation_id = random.randint(1_000_000, 2_000_000_000)

        analysis = await collect_streaming_analysis(query, conversation_id)

        assert analysis.error is None, f"Request failed: {analysis.error}"

        # Find complete event
        complete_events = [e for e in analysis.events if e.type == "complete"]
        assert len(complete_events) == 1, f"Expected 1 complete event, got {len(complete_events)}"

        complete = complete_events[0]
        metadata = complete.parsed_data.get("metadata", {})

        # Check expected metadata fields
        assert "architecture" in metadata, "Missing architecture in metadata"
        assert (
            metadata.get("architecture") == "simplified_v3"
        ), f"Wrong architecture: {metadata.get('architecture')}"


class TestScenario062Validation:
    """Validation tests for Scenario 062 implementation."""

    def test_scenario_test_queries_defined(self):
        """Test that streaming test queries are defined."""
        assert len(STREAMING_TEST_QUERIES) > 0
        assert "What is RIA funding?" in STREAMING_TEST_QUERIES

    def test_required_event_types_defined(self):
        """Test that required event types are defined."""
        assert REQUIRED_EVENT_TYPES == {"status", "token", "complete"}

    def test_allowed_event_types_complete(self):
        """Test that all allowed event types are defined."""
        expected = {
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
        assert ALLOWED_EVENT_TYPES == expected

    def test_evaluator_uses_correct_thresholds(self):
        """Test that evaluator uses correct thresholds."""
        evaluator = StreamingWorksEvaluator()
        assert evaluator.min_token_events == MIN_TOKEN_EVENTS
        assert evaluator.max_inter_token_gap == MAX_INTER_TOKEN_GAP_SECONDS

    def test_min_token_events_reasonable(self):
        """Test that minimum token events is reasonable."""
        assert 2 <= MIN_TOKEN_EVENTS <= 10

    def test_streaming_constants_valid(self):
        """Test that streaming constants are valid."""
        assert MAX_INTER_TOKEN_GAP_SECONDS > 0
        assert MIN_STREAMING_DURATION_SECONDS >= 0


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
