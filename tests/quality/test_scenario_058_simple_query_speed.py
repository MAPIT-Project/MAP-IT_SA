"""
Tests for Scenario 058: Simple Query Speed - Performance Testing

PRD Reference:
- Query: "What is RIA funding?"
- Target: First token < 2 seconds, complete < 5 seconds
- Verify: Measure actual response time
- Fix if: Consistently > 5 seconds
- Pass threshold: Response time target met

This scenario tests that simple FAQ queries are answered quickly:
1. Time to first token (TTFT): Target < 2 seconds
2. Total response time: Target < 5 seconds

Simple queries are those that:
- Don't require tool calls (or minimal tool usage)
- Can be answered from cached/pre-loaded knowledge
- Have straightforward, single-intent questions
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

# Performance targets (in seconds)
TARGET_FIRST_TOKEN_SECONDS = 2.0
TARGET_COMPLETE_SECONDS = 5.0

# Acceptable variance for flaky network conditions
VARIANCE_MULTIPLIER = 1.5  # Allow 50% more time in some cases

# Test queries categorized by expected complexity
SIMPLE_FAQ_QUERIES = [
    "What is RIA funding?",
    "What does RIA stand for?",
    "What is Horizon Europe?",
    "What is an Innovation Action?",
    "What is the difference between RIA and IA?",
]

# Queries that may be slightly slower but should still be fast
MEDIUM_FAQ_QUERIES = [
    "Who can apply for ERC grants?",
    "What are the funding rates for Horizon Europe?",
    "How long does an ERC grant last?",
]


# ============================================================================
# Performance Metrics Data Classes
# ============================================================================


@dataclass
class StreamingMetrics:
    """Metrics collected from a streaming response."""

    query: str
    start_time: float = 0.0
    first_token_time: float | None = None
    complete_time: float | None = None
    token_count: int = 0
    event_count: int = 0
    tools_used: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def time_to_first_token(self) -> float | None:
        """Time from start to first token in seconds."""
        if self.first_token_time is None:
            return None
        return self.first_token_time - self.start_time

    @property
    def total_time(self) -> float | None:
        """Total time from start to complete in seconds."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.start_time

    @property
    def meets_first_token_target(self) -> bool:
        """Check if first token time meets target."""
        ttft = self.time_to_first_token
        return ttft is not None and ttft <= TARGET_FIRST_TOKEN_SECONDS

    @property
    def meets_total_time_target(self) -> bool:
        """Check if total time meets target."""
        total = self.total_time
        return total is not None and total <= TARGET_COMPLETE_SECONDS

    @property
    def passes(self) -> bool:
        """Check if all performance targets are met."""
        return self.meets_first_token_target and self.meets_total_time_target

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "query": self.query,
            "time_to_first_token_seconds": self.time_to_first_token,
            "total_time_seconds": self.total_time,
            "token_count": self.token_count,
            "event_count": self.event_count,
            "tools_used": self.tools_used,
            "meets_first_token_target": self.meets_first_token_target,
            "meets_total_time_target": self.meets_total_time_target,
            "passes": self.passes,
            "error": self.error,
        }


@dataclass
class PerformanceReport:
    """Aggregated performance report for multiple queries."""

    metrics: list[StreamingMetrics] = field(default_factory=list)

    @property
    def total_queries(self) -> int:
        return len(self.metrics)

    @property
    def passed_queries(self) -> int:
        return sum(1 for m in self.metrics if m.passes)

    @property
    def pass_rate(self) -> float:
        if self.total_queries == 0:
            return 0.0
        return self.passed_queries / self.total_queries

    @property
    def avg_time_to_first_token(self) -> float | None:
        ttfts = [m.time_to_first_token for m in self.metrics if m.time_to_first_token is not None]
        return sum(ttfts) / len(ttfts) if ttfts else None

    @property
    def avg_total_time(self) -> float | None:
        totals = [m.total_time for m in self.metrics if m.total_time is not None]
        return sum(totals) / len(totals) if totals else None

    @property
    def max_time_to_first_token(self) -> float | None:
        ttfts = [m.time_to_first_token for m in self.metrics if m.time_to_first_token is not None]
        return max(ttfts) if ttfts else None

    @property
    def max_total_time(self) -> float | None:
        totals = [m.total_time for m in self.metrics if m.total_time is not None]
        return max(totals) if totals else None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "total_queries": self.total_queries,
            "passed_queries": self.passed_queries,
            "pass_rate": self.pass_rate,
            "avg_time_to_first_token_seconds": self.avg_time_to_first_token,
            "avg_total_time_seconds": self.avg_total_time,
            "max_time_to_first_token_seconds": self.max_time_to_first_token,
            "max_total_time_seconds": self.max_total_time,
            "individual_metrics": [m.to_dict() for m in self.metrics],
        }


# ============================================================================
# Evaluator for Scenario 058
# ============================================================================


class SimpleQuerySpeedEvaluator:
    """Evaluator for simple query speed performance."""

    def __init__(
        self,
        first_token_target: float = TARGET_FIRST_TOKEN_SECONDS,
        total_time_target: float = TARGET_COMPLETE_SECONDS,
    ):
        self.first_token_target = first_token_target
        self.total_time_target = total_time_target

    def evaluate_metrics(self, metrics: StreamingMetrics) -> dict[str, Any]:
        """
        Evaluate a single query's performance metrics.

        Returns:
            Dict with evaluation results including score and pass/fail details.
        """
        evaluation = {
            "query": metrics.query,
            "passed": False,
            "score": 0,
            "details": {},
            "issues": [],
        }

        # Check for errors
        if metrics.error:
            evaluation["issues"].append(f"Error: {metrics.error}")
            return evaluation

        # Evaluate time to first token (50 points)
        ttft = metrics.time_to_first_token
        if ttft is None:
            evaluation["issues"].append("No first token received")
            evaluation["details"]["first_token"] = {"received": False}
        else:
            first_token_passed = ttft <= self.first_token_target
            # Score: full points if under target, partial if within 2x, zero if over
            if first_token_passed:
                first_token_score = 50
            elif ttft <= self.first_token_target * 2:
                # Partial credit: linearly scale from 50 to 0
                first_token_score = int(50 * (2 - ttft / self.first_token_target))
            else:
                first_token_score = 0

            evaluation["details"]["first_token"] = {
                "time_seconds": ttft,
                "target_seconds": self.first_token_target,
                "passed": first_token_passed,
                "score": first_token_score,
            }
            evaluation["score"] += first_token_score

            if not first_token_passed:
                evaluation["issues"].append(
                    f"First token too slow: {ttft:.2f}s > {self.first_token_target}s target"
                )

        # Evaluate total time (50 points)
        total = metrics.total_time
        if total is None:
            evaluation["issues"].append("No complete event received")
            evaluation["details"]["total_time"] = {"received": False}
        else:
            total_time_passed = total <= self.total_time_target
            # Score: full points if under target, partial if within 2x, zero if over
            if total_time_passed:
                total_time_score = 50
            elif total <= self.total_time_target * 2:
                # Partial credit: linearly scale from 50 to 0
                total_time_score = int(50 * (2 - total / self.total_time_target))
            else:
                total_time_score = 0

            evaluation["details"]["total_time"] = {
                "time_seconds": total,
                "target_seconds": self.total_time_target,
                "passed": total_time_passed,
                "score": total_time_score,
            }
            evaluation["score"] += total_time_score

            if not total_time_passed:
                evaluation["issues"].append(
                    f"Total time too slow: {total:.2f}s > {self.total_time_target}s target"
                )

        # Overall pass/fail
        evaluation["passed"] = len(evaluation["issues"]) == 0

        return evaluation

    def evaluate_report(self, report: PerformanceReport) -> dict[str, Any]:
        """
        Evaluate an aggregated performance report.

        Returns:
            Dict with overall evaluation including pass rate and recommendations.
        """
        individual_evals = [self.evaluate_metrics(m) for m in report.metrics]
        if individual_evals:
            avg_score = sum(e["score"] for e in individual_evals) / len(individual_evals)
        else:
            avg_score = 0

        return {
            "total_queries": report.total_queries,
            "passed_queries": report.passed_queries,
            "pass_rate": report.pass_rate,
            "average_score": avg_score,
            "passed": report.pass_rate >= 0.8,  # 80% pass rate required
            "avg_time_to_first_token": report.avg_time_to_first_token,
            "avg_total_time": report.avg_total_time,
            "max_time_to_first_token": report.max_time_to_first_token,
            "max_total_time": report.max_total_time,
            "individual_evaluations": individual_evals,
        }


# ============================================================================
# Unit Tests - Test evaluator and metrics logic
# ============================================================================


class TestStreamingMetrics:
    """Test the StreamingMetrics data class."""

    def test_metrics_initialization(self):
        """Test that StreamingMetrics initializes correctly."""
        metrics = StreamingMetrics(query="Test query")
        assert metrics.query == "Test query"
        assert metrics.start_time == 0.0
        assert metrics.first_token_time is None
        assert metrics.complete_time is None
        assert metrics.token_count == 0
        assert metrics.event_count == 0
        assert metrics.tools_used == []
        assert metrics.error is None

    def test_time_to_first_token_calculation(self):
        """Test TTFT calculation."""
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.first_token_time = 101.5  # 1.5 seconds later

        assert metrics.time_to_first_token == 1.5

    def test_time_to_first_token_none_when_no_token(self):
        """Test TTFT is None when no first token received."""
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        # No first_token_time set

        assert metrics.time_to_first_token is None

    def test_total_time_calculation(self):
        """Test total time calculation."""
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 103.5  # 3.5 seconds later

        assert metrics.total_time == 3.5

    def test_meets_first_token_target_pass(self):
        """Test TTFT target check - pass case."""
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.first_token_time = 101.5  # 1.5s < 2s target

        assert metrics.meets_first_token_target is True

    def test_meets_first_token_target_fail(self):
        """Test TTFT target check - fail case."""
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.first_token_time = 103.0  # 3s > 2s target

        assert metrics.meets_first_token_target is False

    def test_meets_total_time_target_pass(self):
        """Test total time target check - pass case."""
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 104.0  # 4s < 5s target

        assert metrics.meets_total_time_target is True

    def test_meets_total_time_target_fail(self):
        """Test total time target check - fail case."""
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 107.0  # 7s > 5s target

        assert metrics.meets_total_time_target is False

    def test_passes_all_targets(self):
        """Test overall pass when all targets met."""
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.first_token_time = 101.5  # 1.5s TTFT
        metrics.complete_time = 104.0  # 4s total

        assert metrics.passes is True

    def test_fails_when_ttft_exceeds(self):
        """Test overall fail when TTFT exceeds."""
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.first_token_time = 103.0  # 3s TTFT > 2s target
        metrics.complete_time = 104.0  # 4s total OK

        assert metrics.passes is False

    def test_fails_when_total_exceeds(self):
        """Test overall fail when total time exceeds."""
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.first_token_time = 101.5  # 1.5s TTFT OK
        metrics.complete_time = 107.0  # 7s total > 5s target

        assert metrics.passes is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = StreamingMetrics(query="Test query")
        metrics.start_time = 100.0
        metrics.first_token_time = 101.5
        metrics.complete_time = 104.0
        metrics.token_count = 50
        metrics.event_count = 55
        metrics.tools_used = ["search_documents"]

        result = metrics.to_dict()

        assert result["query"] == "Test query"
        assert result["time_to_first_token_seconds"] == 1.5
        assert result["total_time_seconds"] == 4.0
        assert result["token_count"] == 50
        assert result["tools_used"] == ["search_documents"]
        assert result["passes"] is True


class TestPerformanceReport:
    """Test the PerformanceReport aggregation."""

    def test_empty_report(self):
        """Test empty report properties."""
        report = PerformanceReport()

        assert report.total_queries == 0
        assert report.passed_queries == 0
        assert report.pass_rate == 0.0
        assert report.avg_time_to_first_token is None
        assert report.avg_total_time is None

    def test_report_aggregation(self):
        """Test aggregation of multiple metrics."""
        report = PerformanceReport()

        # Add passing metrics
        m1 = StreamingMetrics(query="Query 1")
        m1.start_time = 100.0
        m1.first_token_time = 101.0  # 1s
        m1.complete_time = 103.0  # 3s
        report.metrics.append(m1)

        # Add another passing metrics
        m2 = StreamingMetrics(query="Query 2")
        m2.start_time = 100.0
        m2.first_token_time = 101.5  # 1.5s
        m2.complete_time = 104.0  # 4s
        report.metrics.append(m2)

        assert report.total_queries == 2
        assert report.passed_queries == 2
        assert report.pass_rate == 1.0
        assert report.avg_time_to_first_token == 1.25  # (1 + 1.5) / 2
        assert report.avg_total_time == 3.5  # (3 + 4) / 2

    def test_report_with_failures(self):
        """Test report with some failing metrics."""
        report = PerformanceReport()

        # Passing
        m1 = StreamingMetrics(query="Query 1")
        m1.start_time = 100.0
        m1.first_token_time = 101.0
        m1.complete_time = 103.0
        report.metrics.append(m1)

        # Failing - TTFT too slow
        m2 = StreamingMetrics(query="Query 2")
        m2.start_time = 100.0
        m2.first_token_time = 103.5  # 3.5s > 2s target
        m2.complete_time = 104.0
        report.metrics.append(m2)

        assert report.total_queries == 2
        assert report.passed_queries == 1
        assert report.pass_rate == 0.5

    def test_max_time_calculations(self):
        """Test max time calculations."""
        report = PerformanceReport()

        m1 = StreamingMetrics(query="Query 1")
        m1.start_time = 100.0
        m1.first_token_time = 101.0  # 1s
        m1.complete_time = 103.0  # 3s
        report.metrics.append(m1)

        m2 = StreamingMetrics(query="Query 2")
        m2.start_time = 100.0
        m2.first_token_time = 101.8  # 1.8s
        m2.complete_time = 104.5  # 4.5s
        report.metrics.append(m2)

        assert abs(report.max_time_to_first_token - 1.8) < 0.01
        assert abs(report.max_total_time - 4.5) < 0.01


class TestSimpleQuerySpeedEvaluator:
    """Test the SimpleQuerySpeedEvaluator logic."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator with default targets."""
        return SimpleQuerySpeedEvaluator()

    def test_evaluate_passing_metrics(self, evaluator):
        """Test evaluation of passing metrics."""
        metrics = StreamingMetrics(query="What is RIA?")
        metrics.start_time = 100.0
        metrics.first_token_time = 101.5  # 1.5s TTFT
        metrics.complete_time = 104.0  # 4s total

        result = evaluator.evaluate_metrics(metrics)

        assert result["passed"] is True
        assert result["score"] == 100  # 50 + 50
        assert len(result["issues"]) == 0

    def test_evaluate_slow_ttft(self, evaluator):
        """Test evaluation when TTFT is slow."""
        metrics = StreamingMetrics(query="What is RIA?")
        metrics.start_time = 100.0
        metrics.first_token_time = 103.0  # 3s TTFT > 2s target
        metrics.complete_time = 104.0  # 4s total OK

        result = evaluator.evaluate_metrics(metrics)

        assert result["passed"] is False
        assert result["score"] < 100
        assert any("First token too slow" in issue for issue in result["issues"])

    def test_evaluate_slow_total(self, evaluator):
        """Test evaluation when total time is slow."""
        metrics = StreamingMetrics(query="What is RIA?")
        metrics.start_time = 100.0
        metrics.first_token_time = 101.5  # 1.5s TTFT OK
        metrics.complete_time = 107.0  # 7s total > 5s target

        result = evaluator.evaluate_metrics(metrics)

        assert result["passed"] is False
        assert result["score"] < 100
        assert any("Total time too slow" in issue for issue in result["issues"])

    def test_evaluate_with_error(self, evaluator):
        """Test evaluation when there's an error."""
        metrics = StreamingMetrics(query="What is RIA?")
        metrics.error = "Connection timeout"

        result = evaluator.evaluate_metrics(metrics)

        assert result["passed"] is False
        assert result["score"] == 0
        assert any("Error" in issue for issue in result["issues"])

    def test_evaluate_partial_credit_ttft(self, evaluator):
        """Test partial credit for TTFT between 1x and 2x target."""
        metrics = StreamingMetrics(query="What is RIA?")
        metrics.start_time = 100.0
        metrics.first_token_time = 103.0  # 3s = 1.5x target (partial credit)
        metrics.complete_time = 104.0  # 4s total OK

        result = evaluator.evaluate_metrics(metrics)

        # Should get partial credit: 50 * (2 - 3/2) = 50 * 0.5 = 25
        assert result["details"]["first_token"]["score"] == 25

    def test_evaluate_no_credit_very_slow_ttft(self, evaluator):
        """Test no credit for TTFT > 2x target."""
        metrics = StreamingMetrics(query="What is RIA?")
        metrics.start_time = 100.0
        metrics.first_token_time = 105.0  # 5s = 2.5x target (no credit)
        metrics.complete_time = 106.0

        result = evaluator.evaluate_metrics(metrics)

        assert result["details"]["first_token"]["score"] == 0

    def test_evaluate_report_passes(self, evaluator):
        """Test report evaluation with high pass rate."""
        report = PerformanceReport()

        # Add 4 passing, 1 failing (80% pass rate)
        for i in range(4):
            m = StreamingMetrics(query=f"Query {i}")
            m.start_time = 100.0
            m.first_token_time = 101.5
            m.complete_time = 104.0
            report.metrics.append(m)

        # Add one failing
        m_fail = StreamingMetrics(query="Slow query")
        m_fail.start_time = 100.0
        m_fail.first_token_time = 103.5  # Too slow
        m_fail.complete_time = 107.0  # Too slow
        report.metrics.append(m_fail)

        result = evaluator.evaluate_report(report)

        assert result["pass_rate"] == 0.8
        assert result["passed"] is True  # 80% is passing

    def test_evaluate_report_fails(self, evaluator):
        """Test report evaluation with low pass rate."""
        report = PerformanceReport()

        # Add 1 passing, 4 failing (20% pass rate)
        m_pass = StreamingMetrics(query="Fast query")
        m_pass.start_time = 100.0
        m_pass.first_token_time = 101.5
        m_pass.complete_time = 104.0
        report.metrics.append(m_pass)

        for i in range(4):
            m = StreamingMetrics(query=f"Slow query {i}")
            m.start_time = 100.0
            m.first_token_time = 103.5
            m.complete_time = 107.0
            report.metrics.append(m)

        result = evaluator.evaluate_report(report)

        assert result["pass_rate"] == 0.2
        assert result["passed"] is False


class TestSimpleQueryCategories:
    """Test query categorization."""

    def test_simple_faq_queries_defined(self):
        """Test that simple FAQ queries are defined."""
        assert len(SIMPLE_FAQ_QUERIES) > 0
        assert "What is RIA funding?" in SIMPLE_FAQ_QUERIES

    def test_medium_faq_queries_defined(self):
        """Test that medium FAQ queries are defined."""
        assert len(MEDIUM_FAQ_QUERIES) > 0


class TestPerformanceTargets:
    """Test performance target constants."""

    def test_first_token_target_reasonable(self):
        """Test TTFT target is reasonable (1-5 seconds)."""
        assert 1.0 <= TARGET_FIRST_TOKEN_SECONDS <= 5.0

    def test_complete_target_reasonable(self):
        """Test complete target is reasonable (3-15 seconds)."""
        assert 3.0 <= TARGET_COMPLETE_SECONDS <= 15.0

    def test_complete_greater_than_first_token(self):
        """Test complete target is greater than first token target."""
        assert TARGET_COMPLETE_SECONDS > TARGET_FIRST_TOKEN_SECONDS


# ============================================================================
# Mock-Based Unit Tests
# ============================================================================


class TestStreamingMetricsCollection:
    """Test metrics collection from simulated streaming responses."""

    @pytest.mark.asyncio
    async def test_collect_metrics_from_events(self):
        """Test collecting metrics from a sequence of SSE events."""
        # Simulate SSE event sequence
        events = [
            {"type": "status", "message": "Processing..."},
            {"type": "agent_thinking", "content": "Analyzing query..."},
            {"type": "token", "content": "RIA "},
            {"type": "token", "content": "stands "},
            {"type": "token", "content": "for "},
            {"type": "token", "content": "Research "},
            {"type": "token", "content": "and "},
            {"type": "token", "content": "Innovation "},
            {"type": "token", "content": "Action."},
            {"type": "complete", "metadata": {"tools_used": []}},
        ]

        metrics = StreamingMetrics(query="What is RIA?")
        metrics.start_time = time.time()

        first_token_received = False
        for event in events:
            event_type = event.get("type", "")
            metrics.event_count += 1

            if event_type == "token":
                if not first_token_received:
                    metrics.first_token_time = time.time()
                    first_token_received = True
                metrics.token_count += 1

            elif event_type == "complete":
                metrics.complete_time = time.time()

        # Verify metrics were collected
        assert metrics.token_count == 7
        assert metrics.event_count == 10
        assert metrics.first_token_time is not None
        assert metrics.complete_time is not None

    @pytest.mark.asyncio
    async def test_collect_metrics_with_tool_calls(self):
        """Test collecting metrics when tools are used."""
        events = [
            {"type": "status", "message": "Processing..."},
            {"type": "tool_call", "tool": "search_documents", "args": {}},
            {"type": "tool_result", "tool": "search_documents", "result": {"count": 5}},
            {"type": "token", "content": "Based on documents..."},
            {"type": "complete", "metadata": {"tools_used": ["search_documents"]}},
        ]

        metrics = StreamingMetrics(query="What is RIA?")
        metrics.start_time = time.time()

        for event in events:
            event_type = event.get("type", "")
            metrics.event_count += 1

            if event_type == "tool_call":
                tool_name = event.get("tool", "")
                if tool_name and tool_name not in metrics.tools_used:
                    metrics.tools_used.append(tool_name)

            elif event_type == "token":
                if metrics.first_token_time is None:
                    metrics.first_token_time = time.time()
                metrics.token_count += 1

            elif event_type == "complete":
                metrics.complete_time = time.time()

        assert "search_documents" in metrics.tools_used
        assert metrics.token_count == 1


class TestEvaluatorEdgeCases:
    """Test evaluator edge cases."""

    def test_evaluate_no_first_token(self):
        """Test evaluation when no first token received."""
        evaluator = SimpleQuerySpeedEvaluator()
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 104.0
        # No first_token_time

        result = evaluator.evaluate_metrics(metrics)

        assert result["passed"] is False
        assert any("No first token received" in issue for issue in result["issues"])

    def test_evaluate_no_complete_event(self):
        """Test evaluation when no complete event received."""
        evaluator = SimpleQuerySpeedEvaluator()
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.first_token_time = 101.5
        # No complete_time

        result = evaluator.evaluate_metrics(metrics)

        assert result["passed"] is False
        assert any("No complete event received" in issue for issue in result["issues"])

    def test_evaluate_exactly_at_target(self):
        """Test evaluation when times are exactly at target."""
        evaluator = SimpleQuerySpeedEvaluator()
        metrics = StreamingMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.first_token_time = 102.0  # Exactly 2s
        metrics.complete_time = 105.0  # Exactly 5s

        result = evaluator.evaluate_metrics(metrics)

        # At exactly the target should still pass (<=)
        assert result["passed"] is True
        assert result["score"] == 100


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


class TestScenario058LiveAPI:
    """Live API tests for Scenario 058."""

    @live_api
    @pytest.mark.asyncio
    async def test_simple_query_speed_ria(self):
        """
        Test simple query speed for 'What is RIA funding?'

        This is the primary test case from the PRD.
        Target: First token < 2s, complete < 5s
        """
        import random

        import aiohttp

        query = "What is RIA funding?"
        conversation_id = random.randint(1_000_000, 2_000_000_000)
        url = f"http://localhost:8000/api/v3/conversation/{conversation_id}/message/stream"

        metrics = StreamingMetrics(query=query)
        metrics.start_time = time.time()

        try:
            timeout = aiohttp.ClientTimeout(total=30.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url,
                    json={"message": query, "include_context": True},
                    headers={"Content-Type": "application/json"},
                ) as response:
                    assert response.status == 200, f"API returned {response.status}"

                    async for line in response.content:
                        line = line.decode("utf-8").strip()
                        if not line or not line.startswith("data: "):
                            continue

                        event = json.loads(line[6:])
                        event_type = event.get("type", "")
                        metrics.event_count += 1

                        if event_type == "token":
                            if metrics.first_token_time is None:
                                metrics.first_token_time = time.time()
                            metrics.token_count += 1

                        elif event_type == "tool_call":
                            tool_name = event.get("tool", "")
                            if tool_name and tool_name not in metrics.tools_used:
                                metrics.tools_used.append(tool_name)

                        elif event_type == "complete":
                            metrics.complete_time = time.time()

        except Exception as e:
            metrics.error = str(e)

        # Log results
        logger.info(f"Query: {metrics.query}")
        logger.info(f"Time to first token: {metrics.time_to_first_token:.2f}s")
        logger.info(f"Total time: {metrics.total_time:.2f}s")
        logger.info(f"Tools used: {metrics.tools_used}")

        # Evaluate (used for detailed logging if needed)
        evaluator = SimpleQuerySpeedEvaluator()
        _ = evaluator.evaluate_metrics(metrics)

        # Assert performance targets
        assert metrics.error is None, f"Request failed: {metrics.error}"
        assert metrics.meets_first_token_target, (
            f"TTFT {metrics.time_to_first_token:.2f}s > {TARGET_FIRST_TOKEN_SECONDS}s target"
        )
        assert metrics.meets_total_time_target, (
            f"Total {metrics.total_time:.2f}s > {TARGET_COMPLETE_SECONDS}s target"
        )

    @live_api
    @pytest.mark.asyncio
    async def test_multiple_simple_queries_performance(self):
        """
        Test performance across multiple simple FAQ queries.

        At least 80% should meet performance targets.
        """
        import random

        import aiohttp

        report = PerformanceReport()

        for query in SIMPLE_FAQ_QUERIES[:3]:  # Test first 3 queries
            conversation_id = random.randint(1_000_000, 2_000_000_000)
            url = f"http://localhost:8000/api/v3/conversation/{conversation_id}/message/stream"

            metrics = StreamingMetrics(query=query)
            metrics.start_time = time.time()

            try:
                timeout = aiohttp.ClientTimeout(total=30.0)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        url,
                        json={"message": query, "include_context": True},
                        headers={"Content-Type": "application/json"},
                    ) as response:
                        if response.status != 200:
                            metrics.error = f"HTTP {response.status}"
                            report.metrics.append(metrics)
                            continue

                        async for line in response.content:
                            line = line.decode("utf-8").strip()
                            if not line or not line.startswith("data: "):
                                continue

                            event = json.loads(line[6:])
                            event_type = event.get("type", "")
                            metrics.event_count += 1

                            if event_type == "token":
                                if metrics.first_token_time is None:
                                    metrics.first_token_time = time.time()
                                metrics.token_count += 1

                            elif event_type == "complete":
                                metrics.complete_time = time.time()

            except Exception as e:
                metrics.error = str(e)

            report.metrics.append(metrics)

            # Small delay between queries
            await asyncio.sleep(0.5)

        # Evaluate report
        evaluator = SimpleQuerySpeedEvaluator()
        result = evaluator.evaluate_report(report)

        # Log report
        logger.info(f"Performance Report: {json.dumps(result, indent=2, default=str)}")

        # Assert 80% pass rate
        assert result["pass_rate"] >= 0.8, f"Pass rate {result['pass_rate']:.0%} < 80% target"


class TestScenario058Validation:
    """Validation tests for Scenario 058 implementation."""

    def test_scenario_query_is_correct(self):
        """Test that the scenario query matches PRD."""
        assert "What is RIA funding?" in SIMPLE_FAQ_QUERIES

    def test_performance_targets_match_prd(self):
        """Test that performance targets match PRD requirements."""
        # PRD: First token < 2 seconds
        assert TARGET_FIRST_TOKEN_SECONDS == 2.0

        # PRD: Complete < 5 seconds
        assert TARGET_COMPLETE_SECONDS == 5.0

    def test_evaluator_uses_correct_targets(self):
        """Test that evaluator uses PRD targets by default."""
        evaluator = SimpleQuerySpeedEvaluator()
        assert evaluator.first_token_target == TARGET_FIRST_TOKEN_SECONDS
        assert evaluator.total_time_target == TARGET_COMPLETE_SECONDS

    def test_metrics_can_detect_failures(self):
        """Test that metrics correctly detect target failures."""
        # Simulate a slow query
        metrics = StreamingMetrics(query="Slow query")
        metrics.start_time = 0.0
        metrics.first_token_time = 3.0  # 3s > 2s target
        metrics.complete_time = 7.0  # 7s > 5s target

        assert metrics.passes is False
        assert metrics.meets_first_token_target is False
        assert metrics.meets_total_time_target is False


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
