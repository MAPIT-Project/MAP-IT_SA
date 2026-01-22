# isort: skip_file
"""
Production Quality Validation Test Runner.

This module provides comprehensive quality validation for MAPIT conversation scenarios,
implementing the requirements from MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD.md.

Features:
- ScenarioExecutionResult, TurnResult, FailureRecord dataclasses
- ProductionQualityRunner class for scenario execution
- Pattern detection for all 5 failure categories
- Integration with all 6 test agents

Usage:
    runner = ProductionQualityRunner(base_url="http://localhost:8000")
    result = await runner.run_scenario("tests/scenarios/advanced/programme_discovery.yaml")
    report = runner.generate_report([result])
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import pytest

# Import test agents
from tests.agents.context_validator_agent import ContextValidatorAgent
from tests.agents.conversation_flow_agent import (
    ConversationFlowAgent,
    ConversationScenario,
    ConversationTurn,
)
from tests.agents.cross_programme_agent import CrossProgrammeAgent
from tests.agents.goal_tracking_agent import GoalTrackingAgent
from tests.agents.personalization_agent import PersonalizationAgent
from tests.agents.quality_evaluator_agent import QualityEvaluatorAgent

logger = logging.getLogger(__name__)


# =============================================================================
# Failure Categories (per PRD)
# =============================================================================


class FailureCategory(str, Enum):
    """Categories of failures as defined in the PRD."""

    NO_RESULTS = "NO_RESULTS"  # Empty, generic, or deflection response
    INCORRECT_DATA = "INCORRECT_DATA"  # Factually wrong information
    MISSING_DATA = "MISSING_DATA"  # Omits required information
    UNEXPECTED_BEHAVIOR = "UNEXPECTED_BEHAVIOR"  # Erratic or inconsistent behavior
    POOR_QUALITY = "POOR_QUALITY"  # Technically correct but unhelpful


class FailureSeverity(str, Enum):
    """Severity levels for failures."""

    CRITICAL = "CRITICAL"  # Requires immediate fix
    HIGH = "HIGH"  # Requires fix
    MEDIUM = "MEDIUM"  # Requires improvement


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class FailureRecord:
    """Records a single failure detected during scenario execution."""

    category: FailureCategory
    severity: FailureSeverity
    description: str
    turn_number: int
    evidence: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "turn_number": self.turn_number,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TurnResult:
    """Result of evaluating a single turn in a scenario."""

    query: str
    response: str
    quality_score: float
    factual_score: float
    failures: list[FailureRecord] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    processing_time_ms: float = 0.0
    quality_details: dict[str, Any] = field(default_factory=dict)
    turn_number: int = 0

    @property
    def passed(self) -> bool:
        """Check if turn passed quality thresholds."""
        critical_failures = [f for f in self.failures if f.severity == FailureSeverity.CRITICAL]
        return len(critical_failures) == 0 and self.quality_score >= 80

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query": self.query,
            "response": self.response[:500] + "..." if len(self.response) > 500 else self.response,
            "quality_score": self.quality_score,
            "factual_score": self.factual_score,
            "failures": [f.to_dict() for f in self.failures],
            "tools_used": self.tools_used,
            "processing_time_ms": self.processing_time_ms,
            "quality_details": self.quality_details,
            "turn_number": self.turn_number,
            "passed": self.passed,
        }


@dataclass
class ScenarioExecutionResult:
    """Result of executing a complete scenario."""

    scenario_name: str
    turns: list[TurnResult] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    failures: list[FailureRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def average_quality_score(self) -> float:
        """Calculate average quality score across all turns."""
        if not self.turns:
            return 0.0
        return sum(t.quality_score for t in self.turns) / len(self.turns)

    @property
    def average_factual_score(self) -> float:
        """Calculate average factual accuracy score across all turns."""
        if not self.turns:
            return 0.0
        return sum(t.factual_score for t in self.turns) / len(self.turns)

    @property
    def passed(self) -> bool:
        """Check if scenario passed all criteria."""
        critical_failures = [f for f in self.failures if f.severity == FailureSeverity.CRITICAL]
        return (
            len(critical_failures) == 0
            and self.average_quality_score >= 80
            and all(t.passed for t in self.turns)
        )

    @property
    def status(self) -> str:
        """Get the scenario status."""
        return "PASS" if self.passed else "FAIL"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenario_name": self.scenario_name,
            "status": self.status,
            "average_quality_score": self.average_quality_score,
            "average_factual_score": self.average_factual_score,
            "turns": [t.to_dict() for t in self.turns],
            "scores": self.scores,
            "failures": [f.to_dict() for f in self.failures],
            "metadata": self.metadata,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "passed": self.passed,
            "turn_count": len(self.turns),
            "critical_failures": len(
                [f for f in self.failures if f.severity == FailureSeverity.CRITICAL]
            ),
            "high_failures": len([f for f in self.failures if f.severity == FailureSeverity.HIGH]),
            "medium_failures": len(
                [f for f in self.failures if f.severity == FailureSeverity.MEDIUM]
            ),
        }


# =============================================================================
# Failure Detection Patterns (per PRD Appendix)
# =============================================================================


NO_RESULTS_PATTERNS = [
    "I don't have",
    "I cannot find",
    "no information available",
    "I'm not able to",
    "I don't see any",
    "no results found",
    "unable to find",
    "no data available",
    "I couldn't find",
    "there are no",
]

DEFLECTION_PATTERNS = [
    "you might want to",
    "I suggest checking",
    "please visit",
    "for more information",
    "I recommend contacting",
    "you should consult",
]

REQUIRED_FIELDS = {
    "call_search": ["call_id", "title", "deadline", "budget"],
    "project_search": ["project_id", "acronym", "budget", "coordinator"],
    "partner_search": ["organization_name", "country", "project_count"],
    "eligibility_query": ["eligible", "requirements", "exceptions"],
    "budget_calculation": ["total_budget", "breakdown", "funding_rate"],
    "timeline_generation": ["work_packages", "milestones", "duration"],
}

KNOWN_FACTS = {
    "horizon_europe": {
        "budget": (95_000_000_000, 96_000_000_000),
        "duration": "2021-2027",
        "pillars": 3,
        "clusters": 6,
    },
    "erasmus_plus": {
        "budget": (26_000_000_000, 27_000_000_000),
        "duration": "2021-2027",
        "key_actions": ["KA1", "KA2", "KA3", "Jean Monnet", "Sport"],
    },
    "creative_europe": {
        "budget": (2_400_000_000, 2_500_000_000),
        "duration": "2021-2027",
        "strands": ["CULTURE", "MEDIA", "CROSS-SECTORAL"],
    },
}


# =============================================================================
# ProductionQualityRunner
# =============================================================================


class ProductionQualityRunner:
    """
    Main runner for production quality validation.

    Executes scenarios against the live API and evaluates quality using
    multiple test agents.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        passing_threshold: int = 80,
        factual_threshold: float = 0.9,
    ):
        """
        Initialize the production quality runner.

        Args:
            base_url: Base URL of the MAPIT API
            passing_threshold: Minimum quality score to pass (default: 80)
            factual_threshold: Minimum factual accuracy score (default: 0.9)
        """
        self.base_url = base_url
        self.passing_threshold = passing_threshold
        self.factual_threshold = factual_threshold

        # Initialize test agents
        self.quality_evaluator = QualityEvaluatorAgent(passing_threshold=passing_threshold)
        self.cross_programme_agent = CrossProgrammeAgent()
        self.goal_tracking_agent = GoalTrackingAgent()
        self.personalization_agent = PersonalizationAgent()
        self.context_validator = ContextValidatorAgent(api_base_url=base_url)

    async def run_scenario(self, scenario_path: str | Path) -> ScenarioExecutionResult:
        """
        Execute a scenario and evaluate all turns.

        Args:
            scenario_path: Path to the scenario YAML file

        Returns:
            ScenarioExecutionResult with all evaluation data
        """
        scenario_path = Path(scenario_path)
        start_time = datetime.now()

        # Load scenario
        scenario = ConversationScenario.from_yaml(scenario_path)

        # Create conversation flow agent
        flow_agent = ConversationFlowAgent(base_url=self.base_url)

        # Initialize result
        result = ScenarioExecutionResult(
            scenario_name=scenario.name,
            metadata={
                "scenario_path": str(scenario_path),
                "tags": scenario.tags,
                "description": scenario.description,
                "conversation_id": flow_agent.conversation_id,
            },
        )

        # Reset agents for new conversation
        self.cross_programme_agent.reset()
        self.goal_tracking_agent.reset()
        self.personalization_agent.reset()

        # Execute each turn
        for turn_idx, step in enumerate(scenario.steps):
            # Apply delay if specified
            if step.delay_ms > 0:
                await asyncio.sleep(step.delay_ms / 1000.0)

            # Send message
            turn = await flow_agent.send_message(step.message)

            # Evaluate turn
            turn_result = await self.evaluate_turn(
                query=step.message,
                response=turn.response_text,
                turn=turn,
                turn_number=turn_idx,
            )

            result.turns.append(turn_result)
            result.failures.extend(turn_result.failures)

            # Update tracking agents
            self.goal_tracking_agent.add_turn(step.message, turn.response_text)
            self.personalization_agent.add_turn(step.message, turn.response_text)

        # Calculate aggregate scores
        result.scores = {
            "average_quality": result.average_quality_score,
            "average_factual": result.average_factual_score,
            "goal_progress": self.goal_tracking_agent.get_progress(),
            "context_fields": len(self.personalization_agent.get_profile()),
        }

        # Run final context validation
        context_valid = await self._validate_context(flow_agent)
        if not context_valid:
            result.failures.append(
                FailureRecord(
                    category=FailureCategory.UNEXPECTED_BEHAVIOR,
                    severity=FailureSeverity.HIGH,
                    description="Context integrity validation failed",
                    turn_number=-1,
                    evidence={"validation": "context_integrity"},
                )
            )

        result.execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        return result

    async def evaluate_turn(
        self,
        query: str,
        response: str,
        turn: ConversationTurn,
        turn_number: int,
    ) -> TurnResult:
        """
        Evaluate a single turn for quality and detect failures.

        Args:
            query: The user's query
            response: The AI response
            turn: The ConversationTurn object with full details
            turn_number: The turn index in the conversation

        Returns:
            TurnResult with all evaluation data
        """
        failures: list[FailureRecord] = []

        # Quick quality evaluation (rule-based)
        quality_score = self.quality_evaluator.quick_evaluate(
            response=response,
            expected_patterns=[],  # No specific patterns required
            min_length=100,
        )

        # Detect failures
        failures.extend(self.detect_failures(turn, turn_number))

        # Check programme facts if programmes mentioned
        programme_mentions = self.cross_programme_agent.check_programme_mentions(response)
        factual_score = 1.0

        if programme_mentions.programmes_found:
            for programme in programme_mentions.programmes_found:
                facts_result = await self.cross_programme_agent.validate_programme_facts(
                    response, programme
                )
                if not facts_result.passed:
                    failures.append(
                        FailureRecord(
                            category=FailureCategory.INCORRECT_DATA,
                            severity=FailureSeverity.CRITICAL,
                            description=f"Incorrect {programme} facts"[:100],
                            turn_number=turn_number,
                            evidence={
                                "programme": programme,
                                "incorrect_facts": facts_result.facts_incorrect,
                                "score": facts_result.score,
                            },
                        )
                    )
                factual_score = min(factual_score, facts_result.score)

        return TurnResult(
            query=query,
            response=response,
            quality_score=quality_score.total_score,
            factual_score=factual_score * 100,
            failures=failures,
            tools_used=turn.tools_used,
            tool_results=turn.tool_results,
            processing_time_ms=turn.processing_time_ms,
            quality_details={
                "dimension_scores": {k: v.score for k, v in quality_score.dimension_scores.items()},
                "feedback": quality_score.feedback,
            },
            turn_number=turn_number,
        )

    def detect_failures(self, turn: ConversationTurn, turn_number: int) -> list[FailureRecord]:
        """
        Detect failures in a conversation turn.

        Implements detection for all 5 failure categories from the PRD.

        Args:
            turn: The conversation turn to analyze
            turn_number: The turn index

        Returns:
            List of FailureRecord objects for detected failures
        """
        failures: list[FailureRecord] = []

        # Category 1: NO RESULTS
        no_results_failures = self._detect_no_results(turn, turn_number)
        failures.extend(no_results_failures)

        # Category 2: INCORRECT DATA (handled in evaluate_turn via CrossProgrammeAgent)

        # Category 3: MISSING DATA
        missing_data_failures = self._detect_missing_data(turn, turn_number)
        failures.extend(missing_data_failures)

        # Category 4: UNEXPECTED BEHAVIOR
        unexpected_failures = self._detect_unexpected_behavior(turn, turn_number)
        failures.extend(unexpected_failures)

        # Category 5: POOR QUALITY
        poor_quality_failures = self._detect_poor_quality(turn, turn_number)
        failures.extend(poor_quality_failures)

        return failures

    def _detect_no_results(self, turn: ConversationTurn, turn_number: int) -> list[FailureRecord]:
        """Detect NO_RESULTS failures."""
        failures = []
        response = turn.response_text.lower()

        # Check response length
        if len(turn.response_text) < 100:
            failures.append(
                FailureRecord(
                    category=FailureCategory.NO_RESULTS,
                    severity=FailureSeverity.CRITICAL,
                    description=f"Response too short ({len(turn.response_text)} chars < 100)",
                    turn_number=turn_number,
                    evidence={"response_length": len(turn.response_text)},
                )
            )

        # Check for no results patterns
        for pattern in NO_RESULTS_PATTERNS:
            if pattern.lower() in response:
                failures.append(
                    FailureRecord(
                        category=FailureCategory.NO_RESULTS,
                        severity=FailureSeverity.CRITICAL,
                        description=f"Response contains no-results pattern: '{pattern}'",
                        turn_number=turn_number,
                        evidence={"pattern": pattern},
                    )
                )
                break  # Only report first match

        # Check for deflection patterns
        for pattern in DEFLECTION_PATTERNS:
            if pattern.lower() in response:
                failures.append(
                    FailureRecord(
                        category=FailureCategory.NO_RESULTS,
                        severity=FailureSeverity.HIGH,
                        description=f"Response contains deflection pattern: '{pattern}'",
                        turn_number=turn_number,
                        evidence={"pattern": pattern},
                    )
                )
                break

        # Check for empty tool results
        for tool_result in turn.tool_results:
            result_data = tool_result.get("result", {})
            if isinstance(result_data, dict):
                # Check for empty arrays in common result fields
                for key in ["calls", "projects", "partners", "results", "items"]:
                    if key in result_data and result_data[key] == []:
                        failures.append(
                            FailureRecord(
                                category=FailureCategory.NO_RESULTS,
                                severity=FailureSeverity.HIGH,
                                description=f"Tool returned empty {key} array",
                                turn_number=turn_number,
                                evidence={
                                    "tool": tool_result.get("tool"),
                                    "empty_field": key,
                                },
                            )
                        )

        return failures

    def _detect_missing_data(self, turn: ConversationTurn, turn_number: int) -> list[FailureRecord]:
        """Detect MISSING_DATA failures."""
        failures = []

        # Check tool results for required fields based on tool type
        for tool_result in turn.tool_results:
            tool_name = tool_result.get("tool", "")
            result_data = tool_result.get("result", {})

            # Map tool names to required field types
            tool_to_type = {
                "search_funding_calls": "call_search",
                "search_projects": "project_search",
                "find_experienced_partners": "partner_search",
                "calculate_budget": "budget_calculation",
                "generate_timeline": "timeline_generation",
            }

            if tool_name in tool_to_type:
                field_type = tool_to_type[tool_name]
                required_fields = REQUIRED_FIELDS.get(field_type, [])

                missing_fields = []
                if isinstance(result_data, dict):
                    for req_field in required_fields:
                        # Check if field exists in result or in items within result
                        if req_field not in result_data:
                            # Also check in nested items
                            items = result_data.get("calls", []) or result_data.get("projects", [])
                            if items and isinstance(items, list) and len(items) > 0:
                                first_item = items[0]
                                if isinstance(first_item, dict) and req_field not in first_item:
                                    missing_fields.append(req_field)
                            else:
                                missing_fields.append(req_field)

                if missing_fields:
                    failures.append(
                        FailureRecord(
                            category=FailureCategory.MISSING_DATA,
                            severity=FailureSeverity.HIGH,
                            description=(
                                f"Tool {tool_name} missing required fields: {missing_fields}"
                            ),
                            turn_number=turn_number,
                            evidence={
                                "tool": tool_name,
                                "missing_fields": missing_fields,
                                "field_type": field_type,
                            },
                        )
                    )

        return failures

    def _detect_unexpected_behavior(
        self, turn: ConversationTurn, turn_number: int
    ) -> list[FailureRecord]:
        """Detect UNEXPECTED_BEHAVIOR failures."""
        failures = []

        # Check for errors in turn
        if turn.has_error:
            failures.append(
                FailureRecord(
                    category=FailureCategory.UNEXPECTED_BEHAVIOR,
                    severity=FailureSeverity.CRITICAL,
                    description=f"Turn has error: {turn.error}",
                    turn_number=turn_number,
                    evidence={"error": turn.error},
                )
            )

        # Check for error events
        error_events = turn.get_events_by_type("error")
        for event in error_events:
            failures.append(
                FailureRecord(
                    category=FailureCategory.UNEXPECTED_BEHAVIOR,
                    severity=FailureSeverity.CRITICAL,
                    description=f"Error event in SSE stream: {event.get('message', 'Unknown')}",
                    turn_number=turn_number,
                    evidence={"event": event},
                )
            )

        return failures

    def _detect_poor_quality(self, turn: ConversationTurn, turn_number: int) -> list[FailureRecord]:
        """Detect POOR_QUALITY failures."""
        failures = []
        response = turn.response_text

        # Check for wall of text (no structure)
        has_structure = any(
            marker in response for marker in ["1.", "2.", "3.", "-", "•", "*", "##", "**"]
        )
        has_paragraphs = len(response.split("\n\n")) > 1

        if len(response) > 500 and not has_structure and not has_paragraphs:
            failures.append(
                FailureRecord(
                    category=FailureCategory.POOR_QUALITY,
                    severity=FailureSeverity.MEDIUM,
                    description="Response is unstructured wall of text",
                    turn_number=turn_number,
                    evidence={
                        "response_length": len(response),
                        "has_structure": has_structure,
                        "has_paragraphs": has_paragraphs,
                    },
                )
            )

        return failures

    async def _validate_context(self, flow_agent: ConversationFlowAgent) -> bool:
        """Validate context integrity at end of scenario."""
        try:
            context = await flow_agent.get_context()
            return "error" not in context
        except Exception as e:
            logger.warning(f"Context validation failed: {e}")
            return False

    def generate_report(self, results: list[ScenarioExecutionResult]) -> dict[str, Any]:
        """
        Generate a comprehensive report from scenario results.

        Args:
            results: List of scenario execution results

        Returns:
            Dictionary with report data suitable for JSON serialization
        """
        total_scenarios = len(results)
        passed_scenarios = sum(1 for r in results if r.passed)
        failed_scenarios = total_scenarios - passed_scenarios

        all_failures = []
        for r in results:
            all_failures.extend(r.failures)

        critical_failures = [f for f in all_failures if f.severity == FailureSeverity.CRITICAL]
        high_failures = [f for f in all_failures if f.severity == FailureSeverity.HIGH]
        medium_failures = [f for f in all_failures if f.severity == FailureSeverity.MEDIUM]

        # Calculate average scores
        avg_quality = (
            sum(r.average_quality_score for r in results) / len(results) if results else 0.0
        )
        avg_factual = (
            sum(r.average_factual_score for r in results) / len(results) if results else 0.0
        )

        # Group failures by category
        failures_by_category = {}
        for category in FailureCategory:
            count = len([f for f in all_failures if f.category == category])
            failures_by_category[category.value] = count

        report = {
            "summary": {
                "total_scenarios": total_scenarios,
                "passed": passed_scenarios,
                "failed": failed_scenarios,
                "pass_rate": (
                    (passed_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0
                ),
                "average_quality_score": round(avg_quality, 2),
                "average_factual_score": round(avg_factual, 2),
                "critical_failures": len(critical_failures),
                "high_failures": len(high_failures),
                "medium_failures": len(medium_failures),
            },
            "failures_by_category": failures_by_category,
            "scenarios": [r.to_dict() for r in results],
            "timestamp": datetime.now().isoformat(),
            "thresholds": {
                "passing_threshold": self.passing_threshold,
                "factual_threshold": self.factual_threshold,
            },
        }

        return report

    async def save_result(
        self,
        result: ScenarioExecutionResult,
        output_dir: str | Path = "tests/quality/results/scenarios",
    ) -> Path:
        """
        Save a scenario result to JSON file.

        Args:
            result: The scenario execution result
            output_dir: Directory to save results

        Returns:
            Path to the saved file
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create filename from scenario name
        safe_name = result.scenario_name.lower().replace(" ", "_").replace("-", "_")
        filename = f"{safe_name}_result.json"
        output_path = output_dir / filename

        with open(output_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)

        return output_path


# =============================================================================
# Test Fixtures and Configuration
# =============================================================================


@pytest.fixture
def runner():
    """Create a ProductionQualityRunner instance for testing."""
    base_url = os.environ.get("TEST_API_URL", "http://localhost:8000")
    return ProductionQualityRunner(base_url=base_url)


@pytest.fixture
def scenarios_dir():
    """Get the path to advanced scenarios directory."""
    return Path(__file__).parent / "scenarios" / "advanced"


@pytest.fixture
def results_dir():
    """Get the path to results directory."""
    results_path = Path(__file__).parent / "quality" / "results" / "scenarios"
    results_path.mkdir(parents=True, exist_ok=True)
    return results_path


# =============================================================================
# Unit Tests for Infrastructure
# =============================================================================


class TestDataclasses:
    """Tests for dataclass implementations."""

    def test_failure_record_creation(self):
        """Test FailureRecord creation and serialization."""
        failure = FailureRecord(
            category=FailureCategory.NO_RESULTS,
            severity=FailureSeverity.CRITICAL,
            description="Test failure",
            turn_number=0,
            evidence={"test": "data"},
        )

        assert failure.category == FailureCategory.NO_RESULTS
        assert failure.severity == FailureSeverity.CRITICAL

        # Test serialization
        data = failure.to_dict()
        assert data["category"] == "NO_RESULTS"
        assert data["severity"] == "CRITICAL"
        assert data["description"] == "Test failure"
        assert data["evidence"]["test"] == "data"

    def test_turn_result_creation(self):
        """Test TurnResult creation and properties."""
        turn_result = TurnResult(
            query="Test query",
            response="Test response with sufficient length for validation purposes.",
            quality_score=85,
            factual_score=90,
            failures=[],
            tools_used=["search_funding_calls"],
            turn_number=0,
        )

        assert turn_result.passed is True
        assert turn_result.quality_score == 85

        # Test with critical failure
        turn_with_failure = TurnResult(
            query="Test query",
            response="Test response",
            quality_score=85,
            factual_score=90,
            failures=[
                FailureRecord(
                    category=FailureCategory.NO_RESULTS,
                    severity=FailureSeverity.CRITICAL,
                    description="Critical failure",
                    turn_number=0,
                )
            ],
            turn_number=0,
        )
        assert turn_with_failure.passed is False

    def test_scenario_execution_result(self):
        """Test ScenarioExecutionResult creation and properties."""
        result = ScenarioExecutionResult(
            scenario_name="Test Scenario",
            turns=[
                TurnResult(
                    query="Q1",
                    response="R1" * 100,
                    quality_score=85,
                    factual_score=90,
                    turn_number=0,
                ),
                TurnResult(
                    query="Q2",
                    response="R2" * 100,
                    quality_score=90,
                    factual_score=95,
                    turn_number=1,
                ),
            ],
        )

        assert result.average_quality_score == 87.5
        assert result.average_factual_score == 92.5
        assert result.passed is True
        assert result.status == "PASS"


class TestFailureDetection:
    """Tests for failure detection patterns."""

    def test_no_results_pattern_detection(self):
        """Test detection of no-results patterns."""
        runner = ProductionQualityRunner()

        # Create a turn with no-results pattern
        turn = ConversationTurn(
            user_message="Find calls",
            response_text="I don't have any information about that topic.",
        )

        failures = runner._detect_no_results(turn, 0)
        assert len(failures) > 0
        assert any(f.category == FailureCategory.NO_RESULTS for f in failures)

    def test_short_response_detection(self):
        """Test detection of too-short responses."""
        runner = ProductionQualityRunner()

        turn = ConversationTurn(
            user_message="Find calls",
            response_text="No calls found.",  # Less than 100 chars
        )

        failures = runner._detect_no_results(turn, 0)
        assert len(failures) > 0
        assert any("too short" in f.description.lower() for f in failures)

    def test_deflection_pattern_detection(self):
        """Test detection of deflection patterns."""
        runner = ProductionQualityRunner()

        turn = ConversationTurn(
            user_message="What is the budget?",
            response_text=(
                "For more information, you might want to check the official website "
                "for detailed budget information."
            ),
        )

        failures = runner._detect_no_results(turn, 0)
        assert any("deflection" in f.description.lower() for f in failures)

    def test_error_detection(self):
        """Test detection of errors in turns."""
        runner = ProductionQualityRunner()

        turn = ConversationTurn(
            user_message="Find calls",
            response_text="",
            error="Connection timeout",
        )

        failures = runner._detect_unexpected_behavior(turn, 0)
        assert len(failures) > 0
        assert any(f.category == FailureCategory.UNEXPECTED_BEHAVIOR for f in failures)

    def test_wall_of_text_detection(self):
        """Test detection of unstructured wall of text."""
        runner = ProductionQualityRunner()

        # Create a long response with no structure
        long_text = "This is a long response " * 100  # ~2400 chars

        turn = ConversationTurn(
            user_message="Explain funding",
            response_text=long_text,
        )

        failures = runner._detect_poor_quality(turn, 0)
        assert any(f.category == FailureCategory.POOR_QUALITY for f in failures)

    def test_structured_response_passes(self):
        """Test that properly structured responses don't trigger poor quality."""
        runner = ProductionQualityRunner()

        structured_response = """
        Here are the main points:

        1. First point about funding
        2. Second point about eligibility
        3. Third point about deadlines

        **Key Information:**
        - Budget: €95.5 billion
        - Duration: 2021-2027
        """

        turn = ConversationTurn(
            user_message="Explain funding",
            response_text=structured_response,
        )

        failures = runner._detect_poor_quality(turn, 0)
        assert len(failures) == 0


class TestReportGeneration:
    """Tests for report generation."""

    def test_generate_report_empty(self):
        """Test report generation with no results."""
        runner = ProductionQualityRunner()
        report = runner.generate_report([])

        assert report["summary"]["total_scenarios"] == 0
        assert report["summary"]["pass_rate"] == 0

    def test_generate_report_with_results(self):
        """Test report generation with results."""
        runner = ProductionQualityRunner()

        results = [
            ScenarioExecutionResult(
                scenario_name="Scenario 1",
                turns=[
                    TurnResult(
                        query="Q1",
                        response="R1" * 100,
                        quality_score=85,
                        factual_score=90,
                        turn_number=0,
                    )
                ],
            ),
            ScenarioExecutionResult(
                scenario_name="Scenario 2",
                turns=[
                    TurnResult(
                        query="Q2",
                        response="R2" * 100,
                        quality_score=75,
                        factual_score=85,
                        turn_number=0,
                        failures=[
                            FailureRecord(
                                category=FailureCategory.POOR_QUALITY,
                                severity=FailureSeverity.MEDIUM,
                                description="Test",
                                turn_number=0,
                            )
                        ],
                    )
                ],
                failures=[
                    FailureRecord(
                        category=FailureCategory.POOR_QUALITY,
                        severity=FailureSeverity.MEDIUM,
                        description="Test",
                        turn_number=0,
                    )
                ],
            ),
        ]

        report = runner.generate_report(results)

        assert report["summary"]["total_scenarios"] == 2
        assert report["summary"]["passed"] == 1  # Only first passes
        assert report["summary"]["failed"] == 1
        assert report["summary"]["pass_rate"] == 50.0
        assert report["summary"]["medium_failures"] == 1


class TestIntegration:
    """Integration tests that require the API."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("TEST_API_URL") is None,
        reason="TEST_API_URL not set - skipping live API tests",
    )
    async def test_run_single_scenario(self, runner, scenarios_dir, results_dir):
        """Test running a single scenario end-to-end."""
        # Use a simple scenario for testing
        scenario_path = scenarios_dir / "programme_discovery.yaml"

        if not scenario_path.exists():
            pytest.skip(f"Scenario file not found: {scenario_path}")

        result = await runner.run_scenario(scenario_path)

        assert result.scenario_name == "Programme Discovery"
        assert len(result.turns) > 0

        # Save result
        output_path = await runner.save_result(result, results_dir)
        assert output_path.exists()

        # Verify JSON is valid
        with open(output_path) as f:
            saved_data = json.load(f)
        assert saved_data["scenario_name"] == "Programme Discovery"

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("TEST_API_URL") is None,
        reason="TEST_API_URL not set - skipping live API tests",
    )
    async def test_evaluate_turn_with_programme_facts(self, runner):
        """Test turn evaluation with programme fact checking."""
        # Create a mock turn with Horizon Europe information
        turn = ConversationTurn(
            user_message="Tell me about Horizon Europe",
            response_text=(
                "Horizon Europe is the EU's key funding programme for research and innovation "
                "with a budget of €95.5 billion for 2021-2027. It has three pillars: "
                "Excellent Science, Global Challenges and European Industrial Competitiveness, "
                "and Innovative Europe."
            ),
        )

        result = await runner.evaluate_turn(
            query=turn.user_message,
            response=turn.response_text,
            turn=turn,
            turn_number=0,
        )

        assert result.quality_score > 0
        assert result.factual_score > 0


class TestResultsSaving:
    """Tests for saving results to disk."""

    @pytest.mark.asyncio
    async def test_save_result_creates_directory(self, tmp_path):
        """Test that save_result creates output directory."""
        runner = ProductionQualityRunner()

        result = ScenarioExecutionResult(
            scenario_name="Test Scenario",
            turns=[
                TurnResult(
                    query="Q1",
                    response="R1" * 100,
                    quality_score=85,
                    factual_score=90,
                    turn_number=0,
                )
            ],
        )

        output_dir = tmp_path / "new_dir" / "scenarios"
        output_path = await runner.save_result(result, output_dir)

        assert output_dir.exists()
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_save_result_json_format(self, tmp_path):
        """Test that saved results are valid JSON."""
        runner = ProductionQualityRunner()

        result = ScenarioExecutionResult(
            scenario_name="Test Scenario",
            turns=[
                TurnResult(
                    query="Q1",
                    response="R1" * 100,
                    quality_score=85,
                    factual_score=90,
                    turn_number=0,
                    failures=[
                        FailureRecord(
                            category=FailureCategory.NO_RESULTS,
                            severity=FailureSeverity.HIGH,
                            description="Test failure",
                            turn_number=0,
                        )
                    ],
                )
            ],
            failures=[
                FailureRecord(
                    category=FailureCategory.NO_RESULTS,
                    severity=FailureSeverity.HIGH,
                    description="Test failure",
                    turn_number=0,
                )
            ],
        )

        output_path = await runner.save_result(result, tmp_path)

        with open(output_path) as f:
            data = json.load(f)

        assert data["scenario_name"] == "Test Scenario"
        assert len(data["turns"]) == 1
        assert data["turns"][0]["quality_score"] == 85
        assert len(data["failures"]) == 1


# =============================================================================
# CLI Entry Point
# =============================================================================


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run production quality validation")
    parser.add_argument(
        "--scenario",
        type=str,
        help="Path to a specific scenario YAML file",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all scenarios in tests/scenarios/advanced/",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="Base URL of the MAPIT API",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tests/quality/results/scenarios",
        help="Output directory for results",
    )

    args = parser.parse_args()

    async def main():
        runner = ProductionQualityRunner(base_url=args.base_url)
        results = []

        if args.scenario:
            result = await runner.run_scenario(args.scenario)
            results.append(result)
            await runner.save_result(result, args.output)
        elif args.all:
            scenarios_dir = Path("tests/scenarios/advanced")
            for scenario_file in sorted(scenarios_dir.glob("*.yaml")):
                if scenario_file.name.startswith("_"):
                    continue  # Skip validation files
                print(f"Running: {scenario_file.name}")
                result = await runner.run_scenario(scenario_file)
                results.append(result)
                await runner.save_result(result, args.output)

        # Generate and save report
        report = runner.generate_report(results)
        report_path = Path(args.output) / "production_quality_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("PRODUCTION QUALITY VALIDATION REPORT")
        print("=" * 60)
        print(f"Total Scenarios: {report['summary']['total_scenarios']}")
        print(f"Passed: {report['summary']['passed']}")
        print(f"Failed: {report['summary']['failed']}")
        print(f"Pass Rate: {report['summary']['pass_rate']:.1f}%")
        print(f"Average Quality Score: {report['summary']['average_quality_score']}")
        print(f"Critical Failures: {report['summary']['critical_failures']}")
        print("=" * 60)

    asyncio.run(main())
