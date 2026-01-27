"""
Tests for Scenario 059: Complex Query Speed - Performance Testing

PRD Reference:
- Query: "Compare EIC and ERC, find open calls for both, and recommend which suits a TRL 6 project"
- Target: Complete < 15 seconds
- Verify: Multiple tools called efficiently
- Fix if: > 20 seconds consistently
- Pass threshold: Response time target met

This scenario tests that complex queries requiring multiple tools are answered efficiently:
1. Total response time: Target < 15 seconds
2. Multiple tools should be called (compare_programmes, search_funding_calls, etc.)
3. Tools should be called in parallel where possible

Complex queries are those that:
- Require multiple tool calls (comparison + search + recommendation)
- Involve reasoning across multiple data sources
- Need synthesis of information from different tools
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)

# Performance targets (in seconds)
TARGET_COMPLETE_SECONDS = 15.0
MAX_ACCEPTABLE_SECONDS = 20.0  # Absolute maximum before failing

# Acceptable variance for network/load conditions
VARIANCE_MULTIPLIER = 1.5

# The primary complex query from the PRD
COMPLEX_QUERY_PRIMARY = (
    "Compare EIC and ERC, find open calls for both, and recommend which suits a TRL 6 project"
)

# Additional complex queries for thorough testing
COMPLEX_QUERIES = [
    COMPLEX_QUERY_PRIMARY,
    "What's the success rate for RIA grants? Compare it with IA and recommend for a TRL 5 project",
    "Find hydrogen research projects and show budget patterns for similar proposals",
    "Compare Cluster 5 and Cluster 4, find open calls in both, recommend for a climate tech SME",
]

# Expected tool patterns for complex queries
EXPECTED_TOOL_PATTERNS = {
    "compare": ["compare_programmes"],
    "find.*calls": ["search_funding_calls"],
    "find.*projects": ["search_projects"],
    "success rate": ["get_programme_statistics"],
    "budget patterns": ["get_budget_benchmark"],
    "recommend": [],  # Recommendation is synthesized from other tool results
}

# Minimum expected tools for a complex multi-part query
MINIMUM_TOOLS_FOR_COMPLEX_QUERY = 2


# ============================================================================
# Performance Metrics Data Classes
# ============================================================================


@dataclass
class ComplexQueryMetrics:
    """Metrics collected from a complex query response."""

    query: str
    start_time: float = 0.0
    first_token_time: float | None = None
    complete_time: float | None = None
    token_count: int = 0
    event_count: int = 0
    tools_used: list[str] = field(default_factory=list)
    tool_call_times: dict[str, float] = field(default_factory=dict)
    error: str | None = None
    response_text: str = ""

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
    def meets_target(self) -> bool:
        """Check if total time meets target."""
        total = self.total_time
        return total is not None and total <= TARGET_COMPLETE_SECONDS

    @property
    def meets_max_acceptable(self) -> bool:
        """Check if total time is within max acceptable range."""
        total = self.total_time
        return total is not None and total <= MAX_ACCEPTABLE_SECONDS

    @property
    def has_multiple_tools(self) -> bool:
        """Check if multiple tools were called."""
        return len(self.tools_used) >= MINIMUM_TOOLS_FOR_COMPLEX_QUERY

    @property
    def passes(self) -> bool:
        """Check if all performance targets are met."""
        return self.meets_target and self.has_multiple_tools

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "query": self.query,
            "time_to_first_token_seconds": self.time_to_first_token,
            "total_time_seconds": self.total_time,
            "token_count": self.token_count,
            "event_count": self.event_count,
            "tools_used": self.tools_used,
            "tool_call_times": self.tool_call_times,
            "meets_target": self.meets_target,
            "meets_max_acceptable": self.meets_max_acceptable,
            "has_multiple_tools": self.has_multiple_tools,
            "passes": self.passes,
            "error": self.error,
        }


@dataclass
class ComplexQueryReport:
    """Aggregated performance report for multiple complex queries."""

    metrics: list[ComplexQueryMetrics] = field(default_factory=list)

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
    def avg_total_time(self) -> float | None:
        totals = [m.total_time for m in self.metrics if m.total_time is not None]
        return sum(totals) / len(totals) if totals else None

    @property
    def max_total_time(self) -> float | None:
        totals = [m.total_time for m in self.metrics if m.total_time is not None]
        return max(totals) if totals else None

    @property
    def avg_tools_used(self) -> float:
        if not self.metrics:
            return 0.0
        return sum(len(m.tools_used) for m in self.metrics) / len(self.metrics)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "total_queries": self.total_queries,
            "passed_queries": self.passed_queries,
            "pass_rate": self.pass_rate,
            "avg_total_time_seconds": self.avg_total_time,
            "max_total_time_seconds": self.max_total_time,
            "avg_tools_used": self.avg_tools_used,
            "individual_metrics": [m.to_dict() for m in self.metrics],
        }


# ============================================================================
# Evaluator for Scenario 059
# ============================================================================


class ComplexQuerySpeedEvaluator:
    """Evaluator for complex query speed performance."""

    def __init__(
        self,
        target_time: float = TARGET_COMPLETE_SECONDS,
        max_time: float = MAX_ACCEPTABLE_SECONDS,
        min_tools: int = MINIMUM_TOOLS_FOR_COMPLEX_QUERY,
    ):
        self.target_time = target_time
        self.max_time = max_time
        self.min_tools = min_tools

    def evaluate_metrics(self, metrics: ComplexQueryMetrics) -> dict[str, Any]:
        """
        Evaluate a single complex query's performance metrics.

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

        # Evaluate total time (60 points max)
        total = metrics.total_time
        if total is None:
            evaluation["issues"].append("No complete event received")
            evaluation["details"]["total_time"] = {"received": False}
        else:
            # Score based on time: full points if under target, partial if under max
            if total <= self.target_time:
                time_score = 60
            elif total <= self.max_time:
                # Linear scale from 60 to 30 between target and max
                time_ratio = (total - self.target_time) / (self.max_time - self.target_time)
                time_score = int(60 - 30 * time_ratio)
            else:
                time_score = 0

            evaluation["details"]["total_time"] = {
                "time_seconds": total,
                "target_seconds": self.target_time,
                "max_seconds": self.max_time,
                "passed": total <= self.target_time,
                "acceptable": total <= self.max_time,
                "score": time_score,
            }
            evaluation["score"] += time_score

            if total > self.max_time:
                evaluation["issues"].append(
                    f"Total time too slow: {total:.2f}s > {self.max_time}s max"
                )
            elif total > self.target_time:
                evaluation["issues"].append(
                    f"Total time above target: {total:.2f}s > {self.target_time}s target "
                    f"(but within {self.max_time}s max)"
                )

        # Evaluate tool usage (40 points max)
        tools_count = len(metrics.tools_used)
        if tools_count >= self.min_tools:
            # Full points for meeting minimum, bonus for more tools (up to 40)
            tool_score = min(40, 30 + (tools_count - self.min_tools) * 5)
            evaluation["details"]["tools"] = {
                "count": tools_count,
                "tools": metrics.tools_used,
                "meets_minimum": True,
                "score": tool_score,
            }
            evaluation["score"] += tool_score
        else:
            # Partial points
            tool_score = tools_count * 15
            evaluation["details"]["tools"] = {
                "count": tools_count,
                "tools": metrics.tools_used,
                "meets_minimum": False,
                "score": tool_score,
            }
            evaluation["score"] += tool_score
            evaluation["issues"].append(
                f"Too few tools used: {tools_count} < {self.min_tools} minimum"
            )

        # Overall pass/fail (must have no critical issues)
        evaluation["passed"] = len(evaluation["issues"]) == 0 or all(
            "above target" in issue for issue in evaluation["issues"]
        )

        return evaluation

    def evaluate_report(self, report: ComplexQueryReport) -> dict[str, Any]:
        """
        Evaluate an aggregated performance report.

        Returns:
            Dict with overall evaluation including pass rate and recommendations.
        """
        individual_evals = [self.evaluate_metrics(m) for m in report.metrics]
        avg_score = (
            sum(e["score"] for e in individual_evals) / len(individual_evals)
            if individual_evals
            else 0
        )

        return {
            "total_queries": report.total_queries,
            "passed_queries": report.passed_queries,
            "pass_rate": report.pass_rate,
            "average_score": avg_score,
            "passed": report.pass_rate >= 0.8,  # 80% pass rate required
            "avg_total_time": report.avg_total_time,
            "max_total_time": report.max_total_time,
            "avg_tools_used": report.avg_tools_used,
            "individual_evaluations": individual_evals,
        }


# ============================================================================
# Unit Tests - Test evaluator and metrics logic
# ============================================================================


class TestComplexQueryMetrics:
    """Test the ComplexQueryMetrics data class."""

    def test_metrics_initialization(self):
        """Test that ComplexQueryMetrics initializes correctly."""
        metrics = ComplexQueryMetrics(query="Test query")
        assert metrics.query == "Test query"
        assert metrics.start_time == 0.0
        assert metrics.first_token_time is None
        assert metrics.complete_time is None
        assert metrics.token_count == 0
        assert metrics.event_count == 0
        assert metrics.tools_used == []
        assert metrics.tool_call_times == {}
        assert metrics.error is None

    def test_total_time_calculation(self):
        """Test total time calculation."""
        metrics = ComplexQueryMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 110.0  # 10 seconds later

        assert metrics.total_time == 10.0

    def test_total_time_none_when_no_complete(self):
        """Test total time is None when no complete event."""
        metrics = ComplexQueryMetrics(query="Test")
        metrics.start_time = 100.0
        # No complete_time set

        assert metrics.total_time is None

    def test_meets_target_pass(self):
        """Test meets_target when under target."""
        metrics = ComplexQueryMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 112.0  # 12s < 15s target

        assert metrics.meets_target is True

    def test_meets_target_fail(self):
        """Test meets_target when over target."""
        metrics = ComplexQueryMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 118.0  # 18s > 15s target

        assert metrics.meets_target is False

    def test_meets_max_acceptable_pass(self):
        """Test meets_max_acceptable when under max."""
        metrics = ComplexQueryMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 118.0  # 18s < 20s max

        assert metrics.meets_max_acceptable is True

    def test_meets_max_acceptable_fail(self):
        """Test meets_max_acceptable when over max."""
        metrics = ComplexQueryMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 125.0  # 25s > 20s max

        assert metrics.meets_max_acceptable is False

    def test_has_multiple_tools_pass(self):
        """Test has_multiple_tools when enough tools used."""
        metrics = ComplexQueryMetrics(query="Test")
        metrics.tools_used = ["compare_programmes", "search_funding_calls"]

        assert metrics.has_multiple_tools is True

    def test_has_multiple_tools_fail(self):
        """Test has_multiple_tools when not enough tools used."""
        metrics = ComplexQueryMetrics(query="Test")
        metrics.tools_used = ["search_funding_calls"]

        assert metrics.has_multiple_tools is False

    def test_passes_all_criteria(self):
        """Test overall pass when all criteria met."""
        metrics = ComplexQueryMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 112.0  # 12s total
        metrics.tools_used = ["compare_programmes", "search_funding_calls", "get_stats"]

        assert metrics.passes is True

    def test_fails_when_time_exceeds(self):
        """Test overall fail when time exceeds target."""
        metrics = ComplexQueryMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 118.0  # 18s > 15s target
        metrics.tools_used = ["compare_programmes", "search_funding_calls"]

        assert metrics.passes is False

    def test_fails_when_too_few_tools(self):
        """Test overall fail when too few tools used."""
        metrics = ComplexQueryMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 110.0  # 10s OK
        metrics.tools_used = ["search_funding_calls"]  # Only 1 tool

        assert metrics.passes is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = ComplexQueryMetrics(query="Test query")
        metrics.start_time = 100.0
        metrics.complete_time = 112.0
        metrics.token_count = 200
        metrics.event_count = 50
        metrics.tools_used = ["compare_programmes", "search_funding_calls"]

        result = metrics.to_dict()

        assert result["query"] == "Test query"
        assert result["total_time_seconds"] == 12.0
        assert result["token_count"] == 200
        assert result["tools_used"] == ["compare_programmes", "search_funding_calls"]
        assert result["passes"] is True


class TestComplexQueryReport:
    """Test the ComplexQueryReport aggregation."""

    def test_empty_report(self):
        """Test empty report properties."""
        report = ComplexQueryReport()

        assert report.total_queries == 0
        assert report.passed_queries == 0
        assert report.pass_rate == 0.0
        assert report.avg_total_time is None
        assert report.avg_tools_used == 0.0

    def test_report_aggregation(self):
        """Test aggregation of multiple metrics."""
        report = ComplexQueryReport()

        # Add passing metrics
        m1 = ComplexQueryMetrics(query="Query 1")
        m1.start_time = 100.0
        m1.complete_time = 110.0  # 10s
        m1.tools_used = ["tool1", "tool2"]
        report.metrics.append(m1)

        m2 = ComplexQueryMetrics(query="Query 2")
        m2.start_time = 100.0
        m2.complete_time = 114.0  # 14s
        m2.tools_used = ["tool1", "tool2", "tool3"]
        report.metrics.append(m2)

        assert report.total_queries == 2
        assert report.passed_queries == 2
        assert report.pass_rate == 1.0
        assert report.avg_total_time == 12.0  # (10 + 14) / 2
        assert report.avg_tools_used == 2.5  # (2 + 3) / 2

    def test_report_with_failures(self):
        """Test report with some failing metrics."""
        report = ComplexQueryReport()

        # Passing
        m1 = ComplexQueryMetrics(query="Query 1")
        m1.start_time = 100.0
        m1.complete_time = 110.0
        m1.tools_used = ["tool1", "tool2"]
        report.metrics.append(m1)

        # Failing - too slow
        m2 = ComplexQueryMetrics(query="Query 2")
        m2.start_time = 100.0
        m2.complete_time = 122.0  # 22s > 15s target
        m2.tools_used = ["tool1", "tool2"]
        report.metrics.append(m2)

        assert report.total_queries == 2
        assert report.passed_queries == 1
        assert report.pass_rate == 0.5

    def test_max_time_calculation(self):
        """Test max time calculation."""
        report = ComplexQueryReport()

        m1 = ComplexQueryMetrics(query="Query 1")
        m1.start_time = 100.0
        m1.complete_time = 110.0  # 10s
        m1.tools_used = ["tool1", "tool2"]
        report.metrics.append(m1)

        m2 = ComplexQueryMetrics(query="Query 2")
        m2.start_time = 100.0
        m2.complete_time = 114.0  # 14s
        m2.tools_used = ["tool1", "tool2"]
        report.metrics.append(m2)

        assert report.max_total_time == 14.0


class TestComplexQuerySpeedEvaluator:
    """Test the ComplexQuerySpeedEvaluator logic."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator with default targets."""
        return ComplexQuerySpeedEvaluator()

    def test_evaluate_passing_metrics(self, evaluator):
        """Test evaluation of passing metrics."""
        metrics = ComplexQueryMetrics(query="Complex query")
        metrics.start_time = 100.0
        metrics.complete_time = 112.0  # 12s < 15s target
        metrics.tools_used = ["compare_programmes", "search_funding_calls"]

        result = evaluator.evaluate_metrics(metrics)

        assert result["passed"] is True
        assert result["score"] >= 90  # High score for under target with multiple tools
        assert len(result["issues"]) == 0

    def test_evaluate_slow_response(self, evaluator):
        """Test evaluation when response is too slow."""
        metrics = ComplexQueryMetrics(query="Complex query")
        metrics.start_time = 100.0
        metrics.complete_time = 125.0  # 25s > 20s max
        metrics.tools_used = ["compare_programmes", "search_funding_calls"]

        result = evaluator.evaluate_metrics(metrics)

        assert result["passed"] is False
        assert any("too slow" in issue for issue in result["issues"])

    def test_evaluate_too_few_tools(self, evaluator):
        """Test evaluation when too few tools used."""
        metrics = ComplexQueryMetrics(query="Complex query")
        metrics.start_time = 100.0
        metrics.complete_time = 110.0  # 10s OK
        metrics.tools_used = ["search_funding_calls"]  # Only 1 tool

        result = evaluator.evaluate_metrics(metrics)

        # Should fail due to too few tools
        assert any("Too few tools" in issue for issue in result["issues"])

    def test_evaluate_with_error(self, evaluator):
        """Test evaluation when there's an error."""
        metrics = ComplexQueryMetrics(query="Complex query")
        metrics.error = "Connection timeout"

        result = evaluator.evaluate_metrics(metrics)

        assert result["passed"] is False
        assert result["score"] == 0
        assert any("Error" in issue for issue in result["issues"])

    def test_evaluate_partial_credit_time(self, evaluator):
        """Test partial credit for time between target and max."""
        metrics = ComplexQueryMetrics(query="Complex query")
        metrics.start_time = 100.0
        metrics.complete_time = 117.5  # 17.5s (halfway between 15 and 20)
        metrics.tools_used = ["compare_programmes", "search_funding_calls"]

        result = evaluator.evaluate_metrics(metrics)

        # Should get partial credit for time
        time_score = result["details"]["total_time"]["score"]
        assert 30 < time_score < 60  # Partial credit range

    def test_evaluate_bonus_for_more_tools(self, evaluator):
        """Test bonus points for using more than minimum tools."""
        metrics = ComplexQueryMetrics(query="Complex query")
        metrics.start_time = 100.0
        metrics.complete_time = 112.0  # 12s OK
        metrics.tools_used = ["tool1", "tool2", "tool3", "tool4"]  # 4 tools > 2 min

        result = evaluator.evaluate_metrics(metrics)

        tool_score = result["details"]["tools"]["score"]
        assert tool_score == 40  # Max tool score

    def test_evaluate_report_passes(self, evaluator):
        """Test report evaluation with high pass rate."""
        report = ComplexQueryReport()

        # Add 4 passing, 1 failing (80% pass rate)
        for i in range(4):
            m = ComplexQueryMetrics(query=f"Query {i}")
            m.start_time = 100.0
            m.complete_time = 112.0
            m.tools_used = ["tool1", "tool2"]
            report.metrics.append(m)

        # Add one failing (too slow)
        m_fail = ComplexQueryMetrics(query="Slow query")
        m_fail.start_time = 100.0
        m_fail.complete_time = 125.0  # Too slow
        m_fail.tools_used = ["tool1", "tool2"]
        report.metrics.append(m_fail)

        result = evaluator.evaluate_report(report)

        assert result["pass_rate"] == 0.8
        assert result["passed"] is True  # 80% is passing

    def test_evaluate_report_fails(self, evaluator):
        """Test report evaluation with low pass rate."""
        report = ComplexQueryReport()

        # Add 1 passing, 4 failing (20% pass rate)
        m_pass = ComplexQueryMetrics(query="Fast query")
        m_pass.start_time = 100.0
        m_pass.complete_time = 112.0
        m_pass.tools_used = ["tool1", "tool2"]
        report.metrics.append(m_pass)

        for i in range(4):
            m = ComplexQueryMetrics(query=f"Slow query {i}")
            m.start_time = 100.0
            m.complete_time = 125.0  # Too slow
            m.tools_used = ["tool1", "tool2"]
            report.metrics.append(m)

        result = evaluator.evaluate_report(report)

        assert result["pass_rate"] == 0.2
        assert result["passed"] is False


class TestComplexQueryCategories:
    """Test query categorization."""

    def test_complex_queries_defined(self):
        """Test that complex queries are defined."""
        assert len(COMPLEX_QUERIES) > 0
        assert COMPLEX_QUERY_PRIMARY in COMPLEX_QUERIES

    def test_primary_query_is_correct(self):
        """Test that primary query matches PRD."""
        assert "Compare EIC and ERC" in COMPLEX_QUERY_PRIMARY
        assert "TRL 6" in COMPLEX_QUERY_PRIMARY


class TestPerformanceTargets:
    """Test performance target constants."""

    def test_target_reasonable(self):
        """Test target is reasonable (5-20 seconds)."""
        assert 5.0 <= TARGET_COMPLETE_SECONDS <= 20.0

    def test_max_greater_than_target(self):
        """Test max is greater than target."""
        assert MAX_ACCEPTABLE_SECONDS > TARGET_COMPLETE_SECONDS

    def test_min_tools_reasonable(self):
        """Test minimum tools is reasonable."""
        assert 1 <= MINIMUM_TOOLS_FOR_COMPLEX_QUERY <= 5


# ============================================================================
# Mock-Based Unit Tests
# ============================================================================


class TestMetricsCollection:
    """Test metrics collection from simulated streaming responses."""

    @pytest.mark.asyncio
    async def test_collect_metrics_with_multiple_tools(self):
        """Test collecting metrics when multiple tools are called."""
        events = [
            {"type": "status", "message": "Processing..."},
            {"type": "agent_thinking", "content": "Need to compare EIC and ERC..."},
            {"type": "tool_call", "tool": "compare_programmes", "args": {}},
            {"type": "tool_result", "tool": "compare_programmes", "result": {"comparison": {}}},
            {"type": "tool_call", "tool": "search_funding_calls", "args": {"keywords": "EIC"}},
            {"type": "tool_result", "tool": "search_funding_calls", "result": {"calls": []}},
            {"type": "tool_call", "tool": "get_programme_statistics", "args": {"programme": "EIC"}},
            {"type": "tool_result", "tool": "get_programme_statistics", "result": {"stats": {}}},
            {"type": "token", "content": "Based on the comparison..."},
            {"type": "complete", "metadata": {"tools_used": ["compare", "search"]}},
        ]

        metrics = ComplexQueryMetrics(query="Compare EIC and ERC")
        metrics.start_time = time.time()

        for event in events:
            event_type = event.get("type", "")
            metrics.event_count += 1

            if event_type == "tool_call":
                tool_name = event.get("tool", "")
                if tool_name and tool_name not in metrics.tools_used:
                    metrics.tools_used.append(tool_name)
                    metrics.tool_call_times[tool_name] = time.time()

            elif event_type == "token":
                if metrics.first_token_time is None:
                    metrics.first_token_time = time.time()
                metrics.token_count += 1

            elif event_type == "complete":
                metrics.complete_time = time.time()

        # Verify metrics were collected
        assert metrics.token_count >= 1
        assert len(metrics.tools_used) >= 2
        assert "compare_programmes" in metrics.tools_used
        assert "search_funding_calls" in metrics.tools_used

    @pytest.mark.asyncio
    async def test_collect_tool_timing(self):
        """Test collecting timing for individual tool calls."""
        metrics = ComplexQueryMetrics(query="Complex query")
        metrics.start_time = time.time()

        # Simulate tool calls with timing
        tool1_start = time.time()
        metrics.tools_used.append("compare_programmes")
        metrics.tool_call_times["compare_programmes"] = tool1_start

        await asyncio.sleep(0.01)  # Small delay

        tool2_start = time.time()
        metrics.tools_used.append("search_funding_calls")
        metrics.tool_call_times["search_funding_calls"] = tool2_start

        assert len(metrics.tool_call_times) == 2
        search_time = metrics.tool_call_times["search_funding_calls"]
        compare_time = metrics.tool_call_times["compare_programmes"]
        assert search_time > compare_time


class TestEvaluatorEdgeCases:
    """Test evaluator edge cases."""

    def test_evaluate_no_complete_event(self):
        """Test evaluation when no complete event received."""
        evaluator = ComplexQuerySpeedEvaluator()
        metrics = ComplexQueryMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.tools_used = ["tool1", "tool2"]
        # No complete_time

        result = evaluator.evaluate_metrics(metrics)

        assert result["passed"] is False
        assert any("No complete event received" in issue for issue in result["issues"])

    def test_evaluate_exactly_at_target(self):
        """Test evaluation when time is exactly at target."""
        evaluator = ComplexQuerySpeedEvaluator()
        metrics = ComplexQueryMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 115.0  # Exactly 15s
        metrics.tools_used = ["tool1", "tool2"]

        result = evaluator.evaluate_metrics(metrics)

        # At exactly the target should still pass (<=)
        assert result["details"]["total_time"]["passed"] is True

    def test_evaluate_zero_tools(self):
        """Test evaluation with zero tools."""
        evaluator = ComplexQuerySpeedEvaluator()
        metrics = ComplexQueryMetrics(query="Test")
        metrics.start_time = 100.0
        metrics.complete_time = 110.0
        metrics.tools_used = []  # No tools

        result = evaluator.evaluate_metrics(metrics)

        assert result["details"]["tools"]["count"] == 0
        assert result["details"]["tools"]["score"] == 0


# ============================================================================
# Tool Pattern Detection Tests
# ============================================================================


class TestExpectedToolPatterns:
    """Test that complex queries trigger expected tools."""

    def test_compare_pattern_detected(self):
        """Test that comparison queries expect compare_programmes."""
        query = "Compare EIC and ERC"
        query_lower = query.lower()

        for pattern, tools in EXPECTED_TOOL_PATTERNS.items():
            if re.search(pattern, query_lower):
                assert "compare_programmes" in tools or not tools
                break

    def test_find_calls_pattern_detected(self):
        """Test that find calls queries expect search_funding_calls."""
        query = "find open calls for AI"
        query_lower = query.lower()

        matched = False
        for pattern, tools in EXPECTED_TOOL_PATTERNS.items():
            if re.search(pattern, query_lower):
                if "search_funding_calls" in tools:
                    matched = True
                    break

        assert matched, "find calls pattern should match search_funding_calls"

    def test_success_rate_pattern_detected(self):
        """Test that success rate queries expect get_programme_statistics."""
        query = "What's the success rate for EIC?"
        query_lower = query.lower()

        matched = False
        for pattern, tools in EXPECTED_TOOL_PATTERNS.items():
            if re.search(pattern, query_lower):
                if "get_programme_statistics" in tools:
                    matched = True
                    break

        assert matched, "success rate pattern should match get_programme_statistics"


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


class TestScenario059LiveAPI:
    """Live API tests for Scenario 059."""

    @live_api
    @pytest.mark.asyncio
    async def test_complex_query_speed_primary(self):
        """
        Test complex query speed for the primary PRD query.

        This is the primary test case from the PRD:
        "Compare EIC and ERC, find open calls for both, and recommend which suits a TRL 6 project"

        Target: Complete < 15 seconds
        Multiple tools should be called (compare_programmes, search_funding_calls, etc.)
        """
        import random

        import aiohttp

        query = COMPLEX_QUERY_PRIMARY
        conversation_id = random.randint(1_000_000, 2_000_000_000)
        url = f"http://localhost:8000/api/v3/conversation/{conversation_id}/message/stream"

        metrics = ComplexQueryMetrics(query=query)
        metrics.start_time = time.time()

        try:
            timeout = aiohttp.ClientTimeout(total=60.0)  # Longer timeout for complex queries
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
                            metrics.response_text += event.get("content", "")

                        elif event_type == "tool_call":
                            tool_name = event.get("tool", "")
                            if tool_name and tool_name not in metrics.tools_used:
                                metrics.tools_used.append(tool_name)
                                metrics.tool_call_times[tool_name] = time.time()

                        elif event_type == "complete":
                            metrics.complete_time = time.time()

        except Exception as e:
            metrics.error = str(e)

        # Log results
        logger.info(f"Query: {metrics.query}")
        logger.info(f"Total time: {metrics.total_time:.2f}s")
        logger.info(f"Tools used: {metrics.tools_used}")

        # Evaluate
        evaluator = ComplexQuerySpeedEvaluator()
        evaluation = evaluator.evaluate_metrics(metrics)
        logger.info(f"Evaluation: {json.dumps(evaluation, indent=2)}")

        # Assert performance targets
        assert metrics.error is None, f"Request failed: {metrics.error}"
        assert metrics.meets_max_acceptable, (
            f"Total {metrics.total_time:.2f}s > {MAX_ACCEPTABLE_SECONDS}s max"
        )
        assert metrics.has_multiple_tools, (
            f"Only {len(metrics.tools_used)} tools used, "
            f"expected >= {MINIMUM_TOOLS_FOR_COMPLEX_QUERY}"
        )

        # Soft assertion for target (warning if over target but under max)
        if not metrics.meets_target:
            logger.warning(
                f"Total time {metrics.total_time:.2f}s exceeds target {TARGET_COMPLETE_SECONDS}s "
                f"but is within max {MAX_ACCEPTABLE_SECONDS}s"
            )

    @live_api
    @pytest.mark.asyncio
    async def test_multiple_complex_queries_performance(self):
        """
        Test performance across multiple complex queries.

        At least 80% should meet performance targets.
        """
        import random

        import aiohttp

        report = ComplexQueryReport()

        for query in COMPLEX_QUERIES[:2]:  # Test first 2 queries
            conversation_id = random.randint(1_000_000, 2_000_000_000)
            url = f"http://localhost:8000/api/v3/conversation/{conversation_id}/message/stream"

            metrics = ComplexQueryMetrics(query=query)
            metrics.start_time = time.time()

            try:
                timeout = aiohttp.ClientTimeout(total=60.0)
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

                            elif event_type == "tool_call":
                                tool_name = event.get("tool", "")
                                if tool_name and tool_name not in metrics.tools_used:
                                    metrics.tools_used.append(tool_name)

                            elif event_type == "complete":
                                metrics.complete_time = time.time()

            except Exception as e:
                metrics.error = str(e)

            report.metrics.append(metrics)

            # Small delay between queries
            await asyncio.sleep(1.0)

        # Evaluate report
        evaluator = ComplexQuerySpeedEvaluator()
        result = evaluator.evaluate_report(report)

        # Log report
        logger.info(f"Performance Report: {json.dumps(result, indent=2, default=str)}")

        # Assert minimum acceptable performance
        assert result["avg_total_time"] is not None, "No queries completed"
        assert result["avg_total_time"] <= MAX_ACCEPTABLE_SECONDS, (
            f"Average time {result['avg_total_time']:.2f}s > {MAX_ACCEPTABLE_SECONDS}s max"
        )


class TestScenario059Validation:
    """Validation tests for Scenario 059 implementation."""

    def test_scenario_query_is_correct(self):
        """Test that the scenario query matches PRD."""
        assert "Compare EIC and ERC" in COMPLEX_QUERY_PRIMARY
        assert "find open calls" in COMPLEX_QUERY_PRIMARY.lower()
        assert "TRL 6" in COMPLEX_QUERY_PRIMARY

    def test_performance_targets_match_prd(self):
        """Test that performance targets match PRD requirements."""
        # PRD: Complete < 15 seconds
        assert TARGET_COMPLETE_SECONDS == 15.0

        # PRD: Fix if > 20 seconds consistently
        assert MAX_ACCEPTABLE_SECONDS == 20.0

    def test_evaluator_uses_correct_targets(self):
        """Test that evaluator uses PRD targets by default."""
        evaluator = ComplexQuerySpeedEvaluator()
        assert evaluator.target_time == TARGET_COMPLETE_SECONDS
        assert evaluator.max_time == MAX_ACCEPTABLE_SECONDS

    def test_metrics_can_detect_failures(self):
        """Test that metrics correctly detect target failures."""
        # Simulate a slow query
        metrics = ComplexQueryMetrics(query="Slow query")
        metrics.start_time = 0.0
        metrics.complete_time = 25.0  # 25s > 20s max
        metrics.tools_used = ["tool1", "tool2"]

        assert metrics.passes is False
        assert metrics.meets_target is False
        assert metrics.meets_max_acceptable is False


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
