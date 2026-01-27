"""
Agent Context and State Machine

Tracks the agent's state across iterations of the agentic loop.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


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
class AgentContext:
    """
    Tracks the agent's state across iterations.

    This is the "memory" of the agent within a single query processing session.
    It remembers what was tried, what worked, and what failed.
    """

    # Original query
    user_query: str
    conversation_id: str | None = None

    # Current state
    state: AgentState = AgentState.UNDERSTANDING
    iteration: int = 0
    max_iterations: int = 3
    started_at: datetime = field(default_factory=datetime.now)

    # Understanding phase results
    intent: str | None = None
    entities: list[str] = field(default_factory=list)
    query_type: str | None = None  # 'factual', 'exploratory', 'procedural'
    requires_graph: bool = False
    requires_vector: bool = False

    # Planning
    current_plan: dict | None = None
    plan_history: list[dict] = field(default_factory=list)

    # Execution
    results: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict] = field(default_factory=list)
    execution_times: dict[str, float] = field(default_factory=dict)

    # Evaluation
    result_quality: float = 0.0  # 0-1 score
    quality_history: list[float] = field(default_factory=list)
    quality_reasons: list[str] = field(default_factory=list)
    is_sufficient: bool = False

    # Reflection (stored for replanning)
    last_reflection: dict | None = None
    failure_reasons: list[str] = field(default_factory=list)
    improvement_suggestions: list[str] = field(default_factory=list)

    # Memory of what worked/failed (prevents repeating mistakes)
    successful_strategies: list[str] = field(default_factory=list)
    failed_strategies: list[str] = field(default_factory=list)
    tried_queries: list[str] = field(default_factory=list)
    tried_sources: list[str] = field(default_factory=list)

    # Final output
    final_response: str | None = None
    sources: list[dict] = field(default_factory=list)
    confidence_level: str = "medium"  # 'high', 'medium', 'low'

    # Error tracking
    errors: list[str] = field(default_factory=list)

    def transition_to(self, new_state: AgentState) -> None:
        """Transition to a new state with logging."""
        old_state = self.state
        self.state = new_state
        logger.debug(f"Agent state: {old_state.value} → {new_state.value}")

    def record_plan(self, plan: dict) -> None:
        """Record a new plan and update history."""
        self.current_plan = plan
        self.plan_history.append(
            {"iteration": self.iteration, "plan": plan, "timestamp": datetime.now().isoformat()}
        )

    def record_results(self, results: dict[str, Any], execution_time: float = 0) -> None:
        """Record execution results."""
        self.results = results
        self.execution_times[f"iteration_{self.iteration}"] = execution_time

    def record_evaluation(self, score: float, reasons: list[str], is_sufficient: bool) -> None:
        """Record evaluation results."""
        self.result_quality = score
        self.quality_history.append(score)
        self.quality_reasons = reasons
        self.is_sufficient = is_sufficient

        # Determine confidence level
        if score >= 0.8:
            self.confidence_level = "high"
        elif score >= 0.5:
            self.confidence_level = "medium"
        else:
            self.confidence_level = "low"

    def record_failure(self, reason: str, strategy_description: str) -> None:
        """Record a failed strategy to avoid repeating it."""
        self.failure_reasons.append(reason)
        if strategy_description not in self.failed_strategies:
            self.failed_strategies.append(strategy_description)

    def record_success(self, strategy_description: str) -> None:
        """Record a successful strategy."""
        if strategy_description not in self.successful_strategies:
            self.successful_strategies.append(strategy_description)

    def should_continue(self) -> bool:
        """Determine if we should continue iterating."""
        # Already sufficient
        if self.is_sufficient:
            return False

        # Max iterations reached
        if self.iteration >= self.max_iterations:
            logger.info(f"Max iterations ({self.max_iterations}) reached")
            return False

        # Diminishing returns check
        if len(self.quality_history) >= 2:
            improvement = self.quality_history[-1] - self.quality_history[-2]
            if improvement < 0.05:
                logger.info(f"Diminishing returns (improvement: {improvement:.2f})")
                return False

            return True

    def get_strategy_description(self) -> str:
        """Create a string description of the current strategy."""
        if not self.current_plan:
            return "no_plan"

        steps = self.current_plan.get("steps", [])
        sources = [s.get("source", "unknown") for s in steps]
        queries = [s.get("query", "")[:30] for s in steps]
        return f"sources={sources}, queries={queries}"

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the agent's session."""
        return {
            "query": self.user_query,
            "iterations": self.iteration,
            "final_quality": self.result_quality,
            "confidence": self.confidence_level,
            "is_sufficient": self.is_sufficient,
            "successful_strategies": len(self.successful_strategies),
            "failed_strategies": len(self.failed_strategies),
            "total_time_ms": (datetime.now() - self.started_at).total_seconds() * 1000,
            "state": self.state.value,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_query": self.user_query,
            "conversation_id": self.conversation_id,
            "state": self.state.value,
            "iteration": self.iteration,
            "intent": self.intent,
            "entities": self.entities,
            "result_quality": self.result_quality,
            "quality_history": self.quality_history,
            "is_sufficient": self.is_sufficient,
            "confidence_level": self.confidence_level,
            "failed_strategies": self.failed_strategies,
            "successful_strategies": self.successful_strategies,
            "errors": self.errors,
        }
