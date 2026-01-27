"""
Agent Context and State Management

Tracks the agent's state across iterations of the agentic loop.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentState(Enum):
    """Agent lifecycle states."""

    UNDERSTANDING = "understanding"  # Parsing user intent
    PLANNING = "planning"  # Creating execution plan
    EXECUTING = "executing"  # Running tools/searches
    EVALUATING = "evaluating"  # Checking result quality
    REFLECTING = "reflecting"  # Analyzing what went wrong
    REPLANNING = "replanning"  # Creating new plan
    SYNTHESIZING = "synthesizing"  # Building final response
    COMPLETE = "complete"  # Done
    ERROR = "error"  # Something went wrong


@dataclass
class EvaluationResult:
    """Result of evaluating search results."""

    score: float  # 0.0 - 1.0 quality score
    is_sufficient: bool  # Whether results are good enough
    reasons: list[str] = field(default_factory=list)  # Explanation of score
    suggestions: list[str] = field(default_factory=list)  # How to improve

    def __str__(self) -> str:
        status = "✅ Sufficient" if self.is_sufficient else "❌ Insufficient"
        return f"{status} (Score: {self.score:.2f}) - {', '.join(self.reasons[:2])}"


@dataclass
class ReflectionResult:
    """Result of reflecting on failed search."""

    failure_analysis: str  # What went wrong
    root_cause: str  # Category of failure
    improvement_strategy: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5  # Confidence in the analysis

    # Root cause categories
    ROOT_CAUSES = [
        "query_too_broad",
        "query_too_narrow",
        "wrong_source",
        "missing_context",
        "semantic_mismatch",
        "data_not_available",
        "api_error",
        "unknown",
    ]


@dataclass
class AgentContext:
    """
    Tracks the agent's state across iterations.

    This is the "memory" of the agent within a single query processing.
    """

    # Original query
    user_query: str
    conversation_id: str | None = None

    # Current state
    state: AgentState = AgentState.UNDERSTANDING
    iteration: int = 0
    max_iterations: int = 3
    started_at: datetime = field(default_factory=datetime.now)

    # Understanding phase
    intent: str | None = None
    entities: list[str] = field(default_factory=list)
    query_type: str | None = None  # 'factual', 'exploratory', 'procedural'

    # Planning phase
    current_plan: dict[str, Any] | None = None
    plan_history: list[dict[str, Any]] = field(default_factory=list)

    # Execution phase
    results: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    execution_times: list[float] = field(default_factory=list)

    # Evaluation phase
    result_quality: float = 0.0
    quality_history: list[float] = field(default_factory=list)
    quality_reasons: list[str] = field(default_factory=list)
    is_sufficient: bool = False

    # Reflection phase
    last_reflection: ReflectionResult | None = None
    failure_reasons: list[str] = field(default_factory=list)
    improvement_suggestions: list[str] = field(default_factory=list)

    # Memory of strategies
    successful_strategies: list[str] = field(default_factory=list)
    failed_strategies: list[str] = field(default_factory=list)
    tried_sources: list[str] = field(default_factory=list)
    tried_queries: list[str] = field(default_factory=list)

    # Final output
    final_response: str | None = None
    sources: list[dict[str, Any]] = field(default_factory=list)
    confidence_level: str = "medium"  # 'high', 'medium', 'low'

    # Metadata
    error: str | None = None

    def record_iteration(self, evaluation: EvaluationResult):
        """Record results from an iteration."""
        self.quality_history.append(evaluation.score)
        self.result_quality = evaluation.score
        self.is_sufficient = evaluation.is_sufficient
        self.quality_reasons = evaluation.reasons

    def record_plan(self, plan: dict[str, Any]):
        """Record a plan that was executed."""
        self.current_plan = plan
        self.plan_history.append(plan)

        # Track what we tried
        for step in plan.get("steps", []):
            source = step.get("source", "")
            query = step.get("query", "")
            if source and source not in self.tried_sources:
                self.tried_sources.append(source)
            if query and query not in self.tried_queries:
                self.tried_queries.append(query)

    def record_failure(self, reflection: ReflectionResult):
        """Record a failed attempt."""
        self.last_reflection = reflection
        self.failure_reasons.append(reflection.failure_analysis)

        # Mark current strategy as failed
        strategy_desc = self._describe_current_strategy()
        if strategy_desc not in self.failed_strategies:
            self.failed_strategies.append(strategy_desc)

    def record_success(self):
        """Record a successful attempt."""
        strategy_desc = self._describe_current_strategy()
        if strategy_desc not in self.successful_strategies:
            self.successful_strategies.append(strategy_desc)

    def _describe_current_strategy(self) -> str:
        """Create a string description of current strategy."""
        if not self.current_plan:
            return "unknown"

        sources = [s.get("source", "?") for s in self.current_plan.get("steps", [])]
        return f"sources:{','.join(sources)}"

    def should_continue(self) -> bool:
        """Determine if we should continue iterating."""
        # Already sufficient
        if self.is_sufficient:
            return False

        # Hit max iterations
        if self.iteration >= self.max_iterations:
            return False

        # No improvement in last iteration
        if len(self.quality_history) >= 2:
            improvement = self.quality_history[-1] - self.quality_history[-2]
            if improvement < 0.05:  # Less than 5% improvement
                return False

        return True

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the agent's journey."""
        return {
            "query": self.user_query,
            "iterations": self.iteration,
            "final_quality": self.result_quality,
            "is_sufficient": self.is_sufficient,
            "quality_history": self.quality_history,
            "tried_sources": self.tried_sources,
            "failed_strategies": len(self.failed_strategies),
            "successful_strategies": len(self.successful_strategies),
            "duration_seconds": (datetime.now() - self.started_at).total_seconds(),
            "state": self.state.value,
        }

    def set_confidence_level(self):
        """Set confidence level based on quality score."""
        if self.result_quality >= 0.8:
            self.confidence_level = "high"
        elif self.result_quality >= 0.5:
            self.confidence_level = "medium"
        else:
            self.confidence_level = "low"
