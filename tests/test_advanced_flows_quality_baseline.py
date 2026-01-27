"""
Advanced Flows Quality Baseline Test Suite (Task 051).

This module measures and records quality scores for all advanced conversation
scenarios, establishing a baseline for future regression testing.

Features:
- Runs all advanced scenarios from tests/scenarios/advanced/
- Evaluates quality using QualityEvaluatorAgent with 40/25/25/10 rubric
- Records per-scenario and per-turn quality metrics
- Saves results to tests/quality/results/advanced_flows_quality_baseline.json
- Identifies challenging scenarios for improvement
- Documents quality trends and patterns

Usage:
    # Run quality baseline measurement
    pytest tests/test_advanced_flows_quality_baseline.py -v

    # Run with live API (full measurement)
    TEST_API_URL=http://localhost:8000 pytest tests/test_advanced_flows_quality_baseline.py -v

    # Run specific category
    pytest tests/test_advanced_flows_quality_baseline.py -k "infrastructure" -v
"""

# isort: skip_file
import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.agents import (
    ConversationFlowAgent,
    CrossProgrammeAgent,
    GoalTrackingAgent,
    PersonalizationAgent,
    QualityEvaluatorAgent,
)
from tests.agents.quality_evaluator_agent import ConversationQualityResult

logger = logging.getLogger(__name__)

# Configuration
ADVANCED_SCENARIOS_DIR = Path(__file__).parent / "scenarios" / "advanced"
QUALITY_RESULTS_DIR = Path(__file__).parent / "quality" / "results"
BASELINE_FILE = QUALITY_RESULTS_DIR / "advanced_flows_quality_baseline.json"
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 120.0
PASSING_QUALITY_THRESHOLD = 75


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class TurnQualityMetrics:
    """Quality metrics for a single conversation turn."""

    turn_index: int
    user_message: str
    response_length: int
    quality_score: int
    dimension_scores: dict[str, int] = field(default_factory=dict)
    tools_used: list[str] = field(default_factory=list)
    has_error: bool = False
    error_message: str = ""


@dataclass
class ScenarioQualityResult:
    """Quality evaluation result for a complete scenario."""

    scenario_name: str
    scenario_file: str
    category: str  # Derived from tags or filename
    num_turns: int
    total_quality_score: float
    average_turn_score: float
    min_turn_score: float
    max_turn_score: float
    turn_metrics: list[TurnQualityMetrics] = field(default_factory=list)
    quality_trend: str = "stable"  # improving, stable, degrading
    degradation_detected: bool = False
    degradation_turn: int = -1
    passed: bool = True
    goal_progress: float = 0.0
    profile_completeness: float = 0.0
    programmes_mentioned: list[str] = field(default_factory=list)
    challenging_aspects: list[str] = field(default_factory=list)
    error_message: str = ""
    duration_ms: float = 0.0
    timestamp: str = ""


@dataclass
class QualityBaseline:
    """Complete quality baseline for all advanced scenarios."""

    total_scenarios: int = 0
    scenarios_passed: int = 0
    scenarios_failed: int = 0
    overall_average_quality: float = 0.0
    quality_by_category: dict[str, float] = field(default_factory=dict)
    scenario_results: list[ScenarioQualityResult] = field(default_factory=list)
    challenging_scenarios: list[dict[str, Any]] = field(default_factory=list)
    improvement_areas: list[str] = field(default_factory=list)
    measurement_timestamp: str = ""
    measurement_duration_ms: float = 0.0

    def add_scenario_result(self, result: ScenarioQualityResult):
        """Add a scenario result and update aggregates."""
        self.scenario_results.append(result)
        self.total_scenarios = len(self.scenario_results)

        if result.passed:
            self.scenarios_passed += 1
        else:
            self.scenarios_failed += 1

        # Update average quality
        scores = [r.total_quality_score for r in self.scenario_results]
        self.overall_average_quality = sum(scores) / len(scores) if scores else 0.0

        # Update quality by category
        category_scores: dict[str, list[float]] = {}
        for r in self.scenario_results:
            if r.category not in category_scores:
                category_scores[r.category] = []
            category_scores[r.category].append(r.total_quality_score)

        self.quality_by_category = {
            cat: sum(scores) / len(scores) for cat, scores in category_scores.items()
        }

        # Identify challenging scenarios (below threshold)
        self.challenging_scenarios = [
            {
                "name": r.scenario_name,
                "score": r.total_quality_score,
                "aspects": r.challenging_aspects,
                "category": r.category,
            }
            for r in self.scenario_results
            if r.total_quality_score < PASSING_QUALITY_THRESHOLD
        ]

    def identify_improvement_areas(self):
        """Identify areas needing improvement based on patterns."""
        improvement_areas = []

        # Check for degradation patterns
        degradation_count = sum(1 for r in self.scenario_results if r.degradation_detected)
        if degradation_count > 0:
            improvement_areas.append(
                f"Quality degradation detected in {degradation_count} scenarios - "
                "review long conversation handling"
            )

        # Check for category-specific issues
        for category, avg_score in self.quality_by_category.items():
            if avg_score < PASSING_QUALITY_THRESHOLD:
                improvement_areas.append(
                    f"Category '{category}' has low average quality ({avg_score:.1f}) - "
                    f"needs targeted improvements"
                )

        # Check for common challenging aspects
        all_aspects: dict[str, int] = {}
        for result in self.scenario_results:
            for aspect in result.challenging_aspects:
                all_aspects[aspect] = all_aspects.get(aspect, 0) + 1

        for aspect, count in sorted(all_aspects.items(), key=lambda x: -x[1])[:5]:
            if count >= 2:
                improvement_areas.append(f"Common challenge: '{aspect}' ({count} scenarios)")

        self.improvement_areas = improvement_areas

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": {
                "total_scenarios": self.total_scenarios,
                "scenarios_passed": self.scenarios_passed,
                "scenarios_failed": self.scenarios_failed,
                "pass_rate": (
                    self.scenarios_passed / self.total_scenarios * 100
                    if self.total_scenarios > 0
                    else 0
                ),
                "overall_average_quality": round(self.overall_average_quality, 2),
                "passing_threshold": PASSING_QUALITY_THRESHOLD,
                "measurement_timestamp": self.measurement_timestamp,
                "measurement_duration_ms": round(self.measurement_duration_ms, 2),
            },
            "quality_by_category": {k: round(v, 2) for k, v in self.quality_by_category.items()},
            "challenging_scenarios": self.challenging_scenarios,
            "improvement_areas": self.improvement_areas,
            "scenario_results": [
                {
                    "name": r.scenario_name,
                    "file": r.scenario_file,
                    "category": r.category,
                    "num_turns": r.num_turns,
                    "quality_score": round(r.total_quality_score, 2),
                    "average_turn_score": round(r.average_turn_score, 2),
                    "min_turn_score": round(r.min_turn_score, 2),
                    "max_turn_score": round(r.max_turn_score, 2),
                    "quality_trend": r.quality_trend,
                    "degradation_detected": r.degradation_detected,
                    "passed": r.passed,
                    "goal_progress": round(r.goal_progress, 2),
                    "profile_completeness": round(r.profile_completeness, 2),
                    "programmes_mentioned": r.programmes_mentioned,
                    "challenging_aspects": r.challenging_aspects,
                    "duration_ms": round(r.duration_ms, 2),
                    "turn_metrics": [
                        {
                            "turn": m.turn_index,
                            "message": (
                                m.user_message[:100] + "..."
                                if len(m.user_message) > 100
                                else m.user_message
                            ),
                            "score": m.quality_score,
                            "dimensions": m.dimension_scores,
                            "tools": m.tools_used,
                            "has_error": m.has_error,
                        }
                        for m in r.turn_metrics
                    ],
                }
                for r in self.scenario_results
            ],
        }


# =============================================================================
# QUALITY BASELINE RUNNER
# =============================================================================


class QualityBaselineRunner:
    """
    Runs all advanced scenarios and measures quality baseline.

    Integrates with:
    - QualityEvaluatorAgent for response quality scoring
    - GoalTrackingAgent for goal achievement tracking
    - PersonalizationAgent for context accumulation
    - CrossProgrammeAgent for programme mention tracking
    """

    def __init__(self, base_url: str = DEFAULT_API_URL):
        """Initialize the baseline runner."""
        self.base_url = base_url
        self.conversation_agent: ConversationFlowAgent | None = None
        self.quality_evaluator: QualityEvaluatorAgent | None = None
        self.goal_tracker: GoalTrackingAgent | None = None
        self.personalization_agent: PersonalizationAgent | None = None
        self.cross_programme_agent: CrossProgrammeAgent | None = None

    async def _init_agents(self):
        """Initialize agents for measurement."""
        self.conversation_agent = ConversationFlowAgent(
            base_url=self.base_url,
            timeout=DEFAULT_TIMEOUT,
        )
        self.quality_evaluator = QualityEvaluatorAgent(passing_threshold=PASSING_QUALITY_THRESHOLD)
        self.goal_tracker = GoalTrackingAgent(use_llm=True)
        self.personalization_agent = PersonalizationAgent(use_llm=True)
        self.cross_programme_agent = CrossProgrammeAgent(use_llm=True)

    async def _reset_agents(self):
        """Reset agents for a new scenario."""
        # Create fresh conversation agent for new conversation
        self.conversation_agent = ConversationFlowAgent(
            base_url=self.base_url,
            timeout=DEFAULT_TIMEOUT,
        )
        # Reset tracking agents
        self.goal_tracker = GoalTrackingAgent(use_llm=True)
        self.personalization_agent = PersonalizationAgent(use_llm=True)
        self.cross_programme_agent = CrossProgrammeAgent(use_llm=True)

    def _get_scenario_category(self, scenario_data: dict, filename: str) -> str:
        """Derive category from scenario tags or filename."""
        tags = scenario_data.get("tags", [])

        # Priority categories from tags
        category_mapping = {
            "phase1": "multi-programme",
            "phase2": "proposal-workflows",
            "phase3": "partner-discovery",
            "phase4": "personalization",
            "phase5": "strategic-planning",
            "phase6": "cross-programme",
            "phase7": "deadline-handling",
            "phase8": "eligibility",
            "phase9": "erasmus",
            "phase10": "creative-europe",
            "phase11": "error-handling",
        }

        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in category_mapping:
                return category_mapping[tag_lower]

        # Fall back to filename patterns
        filename_lower = filename.lower()
        if "programme" in filename_lower or "discovery" in filename_lower:
            return "multi-programme"
        if "proposal" in filename_lower or "budget" in filename_lower:
            return "proposal-workflows"
        if "partner" in filename_lower or "consortium" in filename_lower:
            return "partner-discovery"
        if "context" in filename_lower or "profile" in filename_lower:
            return "personalization"
        if "strategy" in filename_lower or "planning" in filename_lower:
            return "strategic-planning"
        if "deadline" in filename_lower or "urgent" in filename_lower:
            return "deadline-handling"
        if "eligibility" in filename_lower or "sme" in filename_lower:
            return "eligibility"
        if "erasmus" in filename_lower:
            return "erasmus"
        if "creative" in filename_lower:
            return "creative-europe"
        if "conflict" in filename_lower or "error" in filename_lower:
            return "error-handling"

        return "general"

    def _identify_challenging_aspects(
        self,
        turn_metrics: list[TurnQualityMetrics],
        quality_result: ConversationQualityResult | None,
    ) -> list[str]:
        """Identify aspects that were challenging in this scenario."""
        aspects = []

        if not turn_metrics:
            aspects.append("no_turns_completed")
            return aspects

        # Check for low scoring dimensions
        dimension_totals: dict[str, list[int]] = {}
        for metric in turn_metrics:
            for dim, score in metric.dimension_scores.items():
                if dim not in dimension_totals:
                    dimension_totals[dim] = []
                dimension_totals[dim].append(score)

        # Identify weak dimensions (below 60% of max)
        dimension_thresholds = {
            "query_fulfillment": 24,  # 60% of 40
            "specificity": 15,  # 60% of 25
            "factual_accuracy": 15,  # 60% of 25
            "actionability": 6,  # 60% of 10
        }

        for dim, scores in dimension_totals.items():
            avg = sum(scores) / len(scores)
            threshold = dimension_thresholds.get(dim, 0)
            if avg < threshold:
                aspects.append(f"weak_{dim}")

        # Check for turns with errors
        error_turns = [m for m in turn_metrics if m.has_error]
        if error_turns:
            aspects.append(f"errors_in_{len(error_turns)}_turns")

        # Check for quality degradation
        if quality_result and quality_result.degradation_detected:
            aspects.append("quality_degradation")

        # Check for very short responses
        short_responses = [m for m in turn_metrics if m.response_length < 100]
        if short_responses:
            aspects.append(f"short_responses_{len(short_responses)}_turns")

        return aspects

    async def measure_scenario_quality(self, scenario_file: Path) -> ScenarioQualityResult:
        """Measure quality for a single scenario."""
        start_time = datetime.now()

        # Load scenario
        with open(scenario_file) as f:
            scenario_data = yaml.safe_load(f)

        scenario_name = scenario_data.get("name", scenario_file.stem)
        category = self._get_scenario_category(scenario_data, scenario_file.name)
        steps = scenario_data.get("steps", [])

        result = ScenarioQualityResult(
            scenario_name=scenario_name,
            scenario_file=scenario_file.name,
            category=category,
            num_turns=len(steps),
            total_quality_score=0.0,
            average_turn_score=0.0,
            min_turn_score=100.0,
            max_turn_score=0.0,
            timestamp=datetime.now().isoformat(),
        )

        if not steps:
            result.passed = False
            result.error_message = "No steps in scenario"
            return result

        # Reset agents for this scenario
        await self._reset_agents()

        turn_scores: list[int] = []
        turns_data: list[dict[str, str]] = []

        try:
            # Execute each turn
            for turn_index, step in enumerate(steps):
                message = step.get("message", "")
                if not message:
                    continue

                # Apply delay if specified
                delay_ms = step.get("delay_ms", 0)
                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000.0)

                try:
                    # Send message
                    turn = await self.conversation_agent.send_message(message)

                    # Quick quality evaluation for this turn
                    expected_patterns = self._extract_expected_patterns(step)
                    quality_score = self.quality_evaluator.quick_evaluate(
                        turn.response_text or "",
                        expected_patterns,
                        min_length=50,
                    )

                    turn_metric = TurnQualityMetrics(
                        turn_index=turn_index,
                        user_message=message,
                        response_length=len(turn.response_text or ""),
                        quality_score=quality_score.total_score,
                        dimension_scores={
                            dim: score.score
                            for dim, score in quality_score.dimension_scores.items()
                        },
                        tools_used=turn.tools_used,
                        has_error=turn.has_error,
                        error_message=turn.error or "",
                    )
                    result.turn_metrics.append(turn_metric)
                    turn_scores.append(quality_score.total_score)

                    # Collect data for full evaluation
                    turns_data.append(
                        {
                            "query": message,
                            "response": turn.response_text or "",
                        }
                    )

                    # Update tracking agents
                    if self.goal_tracker:
                        await self.goal_tracker.evaluate_progress(
                            message, turn.response_text or "", turn.tools_used
                        )
                    if self.personalization_agent:
                        self.personalization_agent.add_turn(message, turn.response_text or "")
                    if self.cross_programme_agent:
                        self.cross_programme_agent.check_programme_mentions(
                            turn.response_text or ""
                        )

                except Exception as e:
                    logger.error(f"Error in turn {turn_index}: {e}")
                    result.turn_metrics.append(
                        TurnQualityMetrics(
                            turn_index=turn_index,
                            user_message=message,
                            response_length=0,
                            quality_score=0,
                            has_error=True,
                            error_message=str(e),
                        )
                    )
                    turn_scores.append(0)

            # Calculate aggregate scores
            if turn_scores:
                result.total_quality_score = sum(turn_scores) / len(turn_scores)
                result.average_turn_score = result.total_quality_score
                result.min_turn_score = min(turn_scores)
                result.max_turn_score = max(turn_scores)

                # Evaluate full conversation if we have turns
                if turns_data:
                    full_eval = await self.quality_evaluator.evaluate_conversation(turns_data)
                    result.quality_trend = full_eval.trend
                    result.degradation_detected = full_eval.degradation_detected
                    result.degradation_turn = full_eval.degradation_turn

                    # Use full evaluation average if available
                    if full_eval.average_score > 0:
                        result.total_quality_score = full_eval.average_score

            # Collect tracking metrics
            if self.goal_tracker:
                status = self.goal_tracker.check_completion()
                result.goal_progress = status.progress

            if self.personalization_agent:
                accumulation = self.personalization_agent.validate_context_accumulation()
                result.profile_completeness = accumulation.profile_completeness

            if self.cross_programme_agent:
                summary = self.cross_programme_agent.get_programme_coverage_summary()
                result.programmes_mentioned = summary.get("programmes_discussed", [])

            # Identify challenging aspects
            full_eval_result = (
                await self.quality_evaluator.evaluate_conversation(turns_data)
                if turns_data
                else None
            )
            result.challenging_aspects = self._identify_challenging_aspects(
                result.turn_metrics, full_eval_result
            )

            # Determine pass/fail
            result.passed = result.total_quality_score >= PASSING_QUALITY_THRESHOLD

        except Exception as e:
            logger.error(f"Error measuring scenario {scenario_name}: {e}")
            result.passed = False
            result.error_message = str(e)

        result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        return result

    def _extract_expected_patterns(self, step: dict) -> list[str]:
        """Extract expected patterns from step validations."""
        patterns = []
        for validation in step.get("validations", []):
            patterns.extend(validation.get("patterns", []))
            patterns.extend(validation.get("expected", []))
            patterns.extend(validation.get("programmes", []))
        return patterns

    async def run_baseline_measurement(self) -> QualityBaseline:
        """Run quality measurement on all advanced scenarios."""
        start_time = datetime.now()
        await self._init_agents()

        baseline = QualityBaseline(
            measurement_timestamp=start_time.isoformat(),
        )

        # Find all scenario files (exclude validation files starting with _)
        scenario_files = [
            f for f in sorted(ADVANCED_SCENARIOS_DIR.glob("*.yaml")) if not f.name.startswith("_")
        ]

        logger.info(f"Found {len(scenario_files)} scenarios to measure")

        for scenario_file in scenario_files:
            logger.info(f"Measuring: {scenario_file.name}")
            try:
                result = await self.measure_scenario_quality(scenario_file)
                baseline.add_scenario_result(result)
                logger.info(
                    f"  Score: {result.total_quality_score:.1f}, "
                    f"Turns: {result.num_turns}, "
                    f"Passed: {result.passed}"
                )
            except Exception as e:
                logger.error(f"Failed to measure {scenario_file.name}: {e}")
                # Add failed result
                baseline.add_scenario_result(
                    ScenarioQualityResult(
                        scenario_name=scenario_file.stem,
                        scenario_file=scenario_file.name,
                        category="unknown",
                        num_turns=0,
                        total_quality_score=0.0,
                        average_turn_score=0.0,
                        min_turn_score=0.0,
                        max_turn_score=0.0,
                        passed=False,
                        error_message=str(e),
                    )
                )

        # Identify improvement areas
        baseline.identify_improvement_areas()
        baseline.measurement_duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        return baseline

    def save_baseline(self, baseline: QualityBaseline, filepath: Path | None = None):
        """Save baseline results to JSON file."""
        filepath = filepath or BASELINE_FILE

        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(baseline.to_dict(), f, indent=2)

        logger.info(f"Baseline saved to {filepath}")


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def api_base_url():
    """Get API base URL from environment or default."""
    return os.environ.get("TEST_API_URL", DEFAULT_API_URL)


@pytest.fixture
def baseline_runner(api_base_url):
    """Create a quality baseline runner."""
    return QualityBaselineRunner(base_url=api_base_url)


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestQualityBaselineInfrastructure:
    """Tests for the quality baseline infrastructure."""

    def test_scenarios_directory_exists(self):
        """Verify the advanced scenarios directory exists."""
        assert ADVANCED_SCENARIOS_DIR.exists(), (
            f"Advanced scenarios directory not found: {ADVANCED_SCENARIOS_DIR}"
        )

    def test_results_directory_exists(self):
        """Verify the results directory exists or can be created."""
        QUALITY_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        assert QUALITY_RESULTS_DIR.exists()

    def test_scenario_files_available(self):
        """Verify scenario files are available for measurement."""
        scenario_files = [
            f for f in ADVANCED_SCENARIOS_DIR.glob("*.yaml") if not f.name.startswith("_")
        ]
        assert len(scenario_files) > 0, "No scenario files found"
        logger.info(f"Found {len(scenario_files)} scenario files")

    def test_quality_evaluator_initialization(self):
        """Test QualityEvaluatorAgent can be initialized."""
        evaluator = QualityEvaluatorAgent(passing_threshold=75)
        assert evaluator is not None
        assert evaluator.passing_threshold == 75
        assert evaluator.max_total_score == 100

    def test_quick_evaluate_works(self):
        """Test quick evaluation without LLM."""
        evaluator = QualityEvaluatorAgent(passing_threshold=75)
        score = evaluator.quick_evaluate(
            response="Horizon Europe is the EU's research programme with €95.5 billion budget. "
            "You can apply through the Funding & Tenders portal.",
            expected_patterns=["Horizon Europe", "budget", "apply"],
            min_length=50,
        )
        assert score.total_score > 0
        assert score.total_score <= 100
        assert "query_fulfillment" in score.dimension_scores

    def test_scenario_category_detection(self, baseline_runner):
        """Test scenario category detection from tags and filenames."""
        # Test with tags
        scenario_data = {"tags": ["phase1", "multi-programme"]}
        category = baseline_runner._get_scenario_category(scenario_data, "test.yaml")
        assert category == "multi-programme"

        # Test with filename
        scenario_data = {"tags": []}
        category = baseline_runner._get_scenario_category(scenario_data, "eligibility_routing.yaml")
        assert category == "eligibility"

    def test_baseline_data_structure(self):
        """Test baseline data structure serialization."""
        baseline = QualityBaseline(
            measurement_timestamp=datetime.now().isoformat(),
        )

        # Add a sample result
        result = ScenarioQualityResult(
            scenario_name="test_scenario",
            scenario_file="test_scenario.yaml",
            category="general",
            num_turns=3,
            total_quality_score=85.0,
            average_turn_score=85.0,
            min_turn_score=80.0,
            max_turn_score=90.0,
            passed=True,
        )
        baseline.add_scenario_result(result)

        # Test serialization
        data = baseline.to_dict()
        assert "summary" in data
        assert "scenario_results" in data
        assert data["summary"]["total_scenarios"] == 1
        assert data["summary"]["scenarios_passed"] == 1

    def test_challenging_aspects_detection(self, baseline_runner):
        """Test detection of challenging aspects."""
        turn_metrics = [
            TurnQualityMetrics(
                turn_index=0,
                user_message="Test",
                response_length=50,  # Short response
                quality_score=60,
                dimension_scores={
                    "query_fulfillment": 20,  # Below threshold (24)
                    "specificity": 10,  # Below threshold (15)
                    "factual_accuracy": 20,
                    "actionability": 5,
                },
            )
        ]

        aspects = baseline_runner._identify_challenging_aspects(turn_metrics, None)
        assert "weak_query_fulfillment" in aspects
        assert "weak_specificity" in aspects
        assert "short_responses_1_turns" in aspects


class TestQualityBaselineMeasurement:
    """Tests for quality baseline measurement (requires API)."""

    @pytest.mark.asyncio
    async def test_single_scenario_measurement(self, baseline_runner):
        """Test measuring quality for a single scenario."""
        # Find first available scenario
        scenario_files = [
            f for f in sorted(ADVANCED_SCENARIOS_DIR.glob("*.yaml")) if not f.name.startswith("_")
        ]
        if not scenario_files:
            pytest.skip("No scenario files available")

        # Use programme_discovery.yaml if available, otherwise first file
        target_file = next(
            (f for f in scenario_files if "programme_discovery" in f.name),
            scenario_files[0],
        )

        result = await baseline_runner.measure_scenario_quality(target_file)

        assert result.scenario_name is not None
        assert result.num_turns > 0
        # Note: Quality score may be 0 if API is not available
        logger.info(
            f"Measured {result.scenario_name}: "
            f"score={result.total_quality_score:.1f}, "
            f"turns={result.num_turns}"
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_baseline_measurement(self, baseline_runner):
        """Test running full baseline measurement on all scenarios."""
        baseline = await baseline_runner.run_baseline_measurement()

        assert baseline.total_scenarios > 0
        logger.info(
            f"Baseline measurement complete:\n"
            f"  Total scenarios: {baseline.total_scenarios}\n"
            f"  Passed: {baseline.scenarios_passed}\n"
            f"  Failed: {baseline.scenarios_failed}\n"
            f"  Average quality: {baseline.overall_average_quality:.1f}\n"
            f"  Duration: {baseline.measurement_duration_ms:.1f}ms"
        )

        # Save baseline
        baseline_runner.save_baseline(baseline)

        # Verify file was created
        assert BASELINE_FILE.exists(), f"Baseline file not created: {BASELINE_FILE}"


class TestQualitySummaryGeneration:
    """Tests for quality summary and documentation generation."""

    def test_improvement_areas_identification(self):
        """Test identification of improvement areas."""
        baseline = QualityBaseline()

        # Add some results with issues
        baseline.add_scenario_result(
            ScenarioQualityResult(
                scenario_name="test1",
                scenario_file="test1.yaml",
                category="eligibility",
                num_turns=3,
                total_quality_score=65.0,  # Below threshold
                average_turn_score=65.0,
                min_turn_score=60.0,
                max_turn_score=70.0,
                passed=False,
                degradation_detected=True,
                challenging_aspects=["weak_specificity"],
            )
        )
        baseline.add_scenario_result(
            ScenarioQualityResult(
                scenario_name="test2",
                scenario_file="test2.yaml",
                category="eligibility",
                num_turns=2,
                total_quality_score=70.0,  # Below threshold
                average_turn_score=70.0,
                min_turn_score=65.0,
                max_turn_score=75.0,
                passed=False,
                challenging_aspects=["weak_specificity"],
            )
        )

        baseline.identify_improvement_areas()

        assert len(baseline.improvement_areas) > 0
        # Should identify degradation
        assert any("degradation" in area.lower() for area in baseline.improvement_areas)
        # Should identify category issue
        assert any("eligibility" in area.lower() for area in baseline.improvement_areas)

    def test_summary_generation(self):
        """Test generation of quality summary."""
        baseline = QualityBaseline(
            measurement_timestamp=datetime.now().isoformat(),
        )

        # Add diverse results
        for i, (category, score) in enumerate(
            [
                ("multi-programme", 85.0),
                ("multi-programme", 90.0),
                ("eligibility", 70.0),
                ("proposal-workflows", 80.0),
            ]
        ):
            baseline.add_scenario_result(
                ScenarioQualityResult(
                    scenario_name=f"test_{i}",
                    scenario_file=f"test_{i}.yaml",
                    category=category,
                    num_turns=3,
                    total_quality_score=score,
                    average_turn_score=score,
                    min_turn_score=score - 5,
                    max_turn_score=score + 5,
                    passed=score >= PASSING_QUALITY_THRESHOLD,
                )
            )

        data = baseline.to_dict()

        # Verify summary structure
        assert data["summary"]["total_scenarios"] == 4
        assert data["summary"]["pass_rate"] == 75.0  # 3 of 4 passed
        assert "multi-programme" in data["quality_by_category"]
        assert len(data["challenging_scenarios"]) == 1  # eligibility scenario


# =============================================================================
# CLI ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    # Allow running baseline measurement from command line
    import sys

    if "--measure" in sys.argv:
        # Run full baseline measurement

        async def main():
            runner = QualityBaselineRunner()
            baseline = await runner.run_baseline_measurement()
            runner.save_baseline(baseline)

            print(f"\n{'=' * 60}")
            print("Quality Baseline Measurement Complete")
            print(f"{'=' * 60}")
            print(f"Total scenarios: {baseline.total_scenarios}")
            print(f"Passed: {baseline.scenarios_passed}")
            print(f"Failed: {baseline.scenarios_failed}")
            print(f"Average quality: {baseline.overall_average_quality:.1f}")
            print(f"\nResults saved to: {BASELINE_FILE}")

            if baseline.challenging_scenarios:
                print(f"\nChallenging scenarios ({len(baseline.challenging_scenarios)}):")
                for cs in baseline.challenging_scenarios:
                    print(f"  - {cs['name']}: {cs['score']:.1f}")

            if baseline.improvement_areas:
                print("\nImprovement areas:")
                for area in baseline.improvement_areas:
                    print(f"  - {area}")

        asyncio.run(main())
    else:
        # Run pytest
        pytest.main([__file__, "-v", "--tb=short"])
