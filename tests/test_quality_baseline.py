"""
Quality Baseline Measurement Tests for Conversation Stability.

This module implements Task 022 from the MAPIT Conversation Stability PRD:
- Run all basic_flows scenarios and record quality scores
- Save baseline to tests/quality/results/conversation_quality_baseline.json
- Create summary of average scores per scenario
- Identify lowest scoring areas

Usage:
    # Run quality baseline measurement (requires API to be running)
    pytest tests/test_quality_baseline.py -v

    # Run with live API
    TEST_API_URL=http://localhost:8000 pytest tests/test_quality_baseline.py -v

    # Run only the baseline measurement test
    pytest tests/test_quality_baseline.py::TestQualityBaseline::test_measure_quality_baseline -v
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from tests.agents.conversation_flow_agent import (
    ConversationFlowAgent,
    ConversationScenario,
)
from tests.agents.quality_evaluator_agent import (
    ConversationQualityResult,
    QualityEvaluatorAgent,
    QualityScore,
)

logger = logging.getLogger(__name__)

# Configuration
SCENARIOS_DIR = Path(__file__).parent / "scenarios"
RESULTS_DIR = Path(__file__).parent / "quality" / "results"
BASELINE_FILE = RESULTS_DIR / "conversation_quality_baseline.json"
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 120.0
PASSING_THRESHOLD = 75  # Minimum quality score to pass


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def api_base_url():
    """Get API base URL from environment or default."""
    return os.environ.get("TEST_API_URL", DEFAULT_API_URL)


@pytest.fixture
def conversation_agent(api_base_url):
    """Create a conversation flow agent."""
    return ConversationFlowAgent(
        base_url=api_base_url,
        timeout=DEFAULT_TIMEOUT,
    )


@pytest.fixture
def quality_evaluator():
    """Create a quality evaluator agent."""
    return QualityEvaluatorAgent(
        passing_threshold=PASSING_THRESHOLD,
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def load_basic_flows_scenarios() -> list[ConversationScenario]:
    """Load all basic_flows scenarios from YAML files."""
    scenarios = []
    basic_flows_dir = SCENARIOS_DIR / "basic_flows"

    if not basic_flows_dir.exists():
        return scenarios

    for yaml_file in basic_flows_dir.glob("*.yaml"):
        try:
            scenario = ConversationScenario.from_yaml(yaml_file)
            scenarios.append(scenario)
        except Exception as e:
            logger.warning(f"Failed to load scenario {yaml_file}: {e}")

    return scenarios


def save_baseline_results(results: dict[str, Any]) -> None:
    """Save baseline results to JSON file."""
    # Ensure results directory exists
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Add metadata
    results["metadata"] = {
        "generated_at": datetime.now().isoformat(),
        "passing_threshold": PASSING_THRESHOLD,
        "api_url": os.environ.get("TEST_API_URL", DEFAULT_API_URL),
    }

    # Write to file
    with open(BASELINE_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"Saved baseline results to {BASELINE_FILE}")


def calculate_summary(scenario_results: dict[str, Any]) -> dict[str, Any]:
    """Calculate summary statistics from scenario results."""
    all_scores = []
    dimension_scores: dict[str, list[float]] = {
        "query_fulfillment": [],
        "specificity": [],
        "factual_accuracy": [],
        "actionability": [],
    }

    for _scenario_name, result in scenario_results.items():
        if "turn_scores" in result:
            for turn_score in result["turn_scores"]:
                all_scores.append(turn_score["total_score"])
                for dim_name, dim_data in turn_score.get("dimension_scores", {}).items():
                    if dim_name in dimension_scores:
                        dimension_scores[dim_name].append(dim_data.get("score", 0))

    summary = {
        "total_scenarios": len(scenario_results),
        "total_turns_evaluated": len(all_scores),
        "overall_average_score": sum(all_scores) / len(all_scores) if all_scores else 0,
        "overall_min_score": min(all_scores) if all_scores else 0,
        "overall_max_score": max(all_scores) if all_scores else 0,
        "dimension_averages": {},
        "lowest_scoring_areas": [],
    }

    # Calculate dimension averages
    for dim_name, scores in dimension_scores.items():
        if scores:
            avg = sum(scores) / len(scores)
            summary["dimension_averages"][dim_name] = round(avg, 2)

    # Identify lowest scoring areas
    if summary["dimension_averages"]:
        sorted_dims = sorted(
            summary["dimension_averages"].items(),
            key=lambda x: x[1],
        )
        summary["lowest_scoring_areas"] = [
            {"dimension": dim, "average_score": score} for dim, score in sorted_dims[:2]
        ]

    # Identify lowest scoring scenarios
    scenario_averages = []
    for scenario_name, result in scenario_results.items():
        if result.get("average_score") is not None:
            scenario_averages.append(
                {
                    "scenario": scenario_name,
                    "average_score": result["average_score"],
                }
            )

    if scenario_averages:
        sorted_scenarios = sorted(
            scenario_averages,
            key=lambda x: x["average_score"],
        )
        summary["lowest_scoring_scenarios"] = sorted_scenarios[:2]

    return summary


def quality_score_to_dict(score: QualityScore) -> dict[str, Any]:
    """Convert QualityScore to dictionary."""
    return {
        "total_score": score.total_score,
        "max_score": score.max_score,
        "percentage": round(score.percentage, 2),
        "passed": score.passed,
        "feedback": score.feedback,
        "evaluation_time_ms": round(score.evaluation_time_ms, 2),
        "dimension_scores": {
            name: {
                "score": dim.score,
                "max_score": dim.max_score,
                "percentage": round(dim.percentage, 2),
                "reasoning": dim.reasoning,
            }
            for name, dim in score.dimension_scores.items()
        },
    }


def quality_result_to_dict(result: ConversationQualityResult) -> dict[str, Any]:
    """Convert ConversationQualityResult to dictionary."""
    return {
        "average_score": round(result.average_score, 2),
        "min_score": result.min_score,
        "max_score": result.max_score,
        "degradation_detected": result.degradation_detected,
        "degradation_turn": result.degradation_turn,
        "degradation_amount": round(result.degradation_amount, 2),
        "trend": result.trend,
        "turn_scores": [quality_score_to_dict(score) for score in result.turn_scores],
    }


# =============================================================================
# QUALITY BASELINE TESTS
# =============================================================================


class TestQualityBaseline:
    """Tests for measuring and recording quality baselines."""

    @pytest.mark.asyncio
    async def test_measure_quality_baseline(
        self,
        api_base_url: str,
        quality_evaluator: QualityEvaluatorAgent,
    ):
        """
        Measure quality baseline for all basic_flows scenarios.

        Task 022: Quality Baseline Measurement
        - Run all basic_flows scenarios and record quality scores
        - Save baseline to tests/quality/results/conversation_quality_baseline.json
        - Create summary of average scores per scenario
        - Identify lowest scoring areas
        """
        # Load basic_flows scenarios
        scenarios = load_basic_flows_scenarios()
        assert len(scenarios) > 0, "No basic_flows scenarios found"

        logger.info(f"Loaded {len(scenarios)} basic_flows scenarios")

        # Results storage
        scenario_results: dict[str, Any] = {}

        # Run each scenario and evaluate quality
        for scenario in scenarios:
            logger.info(f"Running scenario: {scenario.name}")

            # Create fresh agent for each scenario
            agent = ConversationFlowAgent(
                base_url=api_base_url,
                timeout=DEFAULT_TIMEOUT,
            )

            turns_data = []
            scenario_errors = []

            # Execute all steps in the scenario
            for step_index, step in enumerate(scenario.steps):
                try:
                    # Apply delay if specified
                    if step.delay_ms > 0:
                        await asyncio.sleep(step.delay_ms / 1000.0)

                    turn = await agent.send_message(step.message)

                    # Record turn data for quality evaluation
                    turns_data.append(
                        {
                            "query": step.message,
                            "response": turn.response_text or f"Error: {turn.error}",
                            "tools_used": turn.tools_used,
                            "has_error": turn.has_error,
                            "processing_time_ms": turn.processing_time_ms,
                        }
                    )

                    if turn.has_error:
                        scenario_errors.append(
                            {
                                "step": step_index,
                                "error": turn.error,
                            }
                        )
                        logger.warning(f"  Step {step_index + 1} error: {turn.error}")
                    else:
                        logger.info(
                            f"  Step {step_index + 1} completed: "
                            f"{len(turn.response_text)} chars, "
                            f"tools: {turn.tools_used}"
                        )

                except Exception as e:
                    scenario_errors.append(
                        {
                            "step": step_index,
                            "error": str(e),
                        }
                    )
                    turns_data.append(
                        {
                            "query": step.message,
                            "response": f"Exception: {str(e)}",
                            "tools_used": [],
                            "has_error": True,
                        }
                    )

            # Evaluate quality for this scenario
            if turns_data:
                quality_result = await quality_evaluator.evaluate_conversation(turns_data)

                # Store results
                scenario_results[scenario.name] = {
                    **quality_result_to_dict(quality_result),
                    "steps_completed": len(turns_data),
                    "steps_total": len(scenario.steps),
                    "errors": scenario_errors,
                    "turns_data": turns_data,
                }

                logger.info(
                    f"  Quality: avg={quality_result.average_score:.1f}, "
                    f"trend={quality_result.trend}, "
                    f"degradation={quality_result.degradation_detected}"
                )
            else:
                scenario_results[scenario.name] = {
                    "error": "No turns completed",
                    "errors": scenario_errors,
                }

        # Calculate summary statistics
        summary = calculate_summary(scenario_results)

        # Build final results
        baseline_results = {
            "scenarios": scenario_results,
            "summary": summary,
        }

        # Save baseline to file
        save_baseline_results(baseline_results)

        # Log summary
        logger.info("=" * 60)
        logger.info("QUALITY BASELINE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total scenarios: {summary['total_scenarios']}")
        logger.info(f"Total turns evaluated: {summary['total_turns_evaluated']}")
        logger.info(f"Overall average score: {summary['overall_average_score']:.1f}/100")
        min_score = summary["overall_min_score"]
        max_score = summary["overall_max_score"]
        logger.info(f"Score range: {min_score:.0f} - {max_score:.0f}")
        logger.info(f"Dimension averages: {summary['dimension_averages']}")
        logger.info(f"Lowest scoring areas: {summary['lowest_scoring_areas']}")

        if "lowest_scoring_scenarios" in summary:
            logger.info(f"Lowest scoring scenarios: {summary['lowest_scoring_scenarios']}")

        # Assertions
        assert summary["total_scenarios"] > 0, "Should evaluate at least one scenario"
        assert summary["total_turns_evaluated"] > 0, "Should evaluate at least one turn"

        # Assert minimum quality threshold
        assert summary["overall_average_score"] >= 60, (
            f"Overall average quality too low: {summary['overall_average_score']:.1f}/100. "
            f"Expected at least 60/100."
        )

    @pytest.mark.asyncio
    async def test_individual_scenario_quality(
        self,
        api_base_url: str,
        quality_evaluator: QualityEvaluatorAgent,
    ):
        """
        Test quality for each basic_flows scenario individually.

        Ensures each scenario meets minimum quality standards.
        """
        scenarios = load_basic_flows_scenarios()

        for scenario in scenarios:
            logger.info(f"Testing quality for: {scenario.name}")

            agent = ConversationFlowAgent(
                base_url=api_base_url,
                timeout=DEFAULT_TIMEOUT,
            )

            turns_data = []

            for step in scenario.steps:
                if step.delay_ms > 0:
                    await asyncio.sleep(step.delay_ms / 1000.0)

                turn = await agent.send_message(step.message)
                turns_data.append(
                    {
                        "query": step.message,
                        "response": turn.response_text or f"Error: {turn.error}",
                    }
                )

            if turns_data:
                quality_result = await quality_evaluator.evaluate_conversation(turns_data)

                # Each scenario should maintain reasonable quality
                assert quality_result.average_score >= 55, (
                    f"Scenario '{scenario.name}' quality too low: "
                    f"{quality_result.average_score:.1f}/100"
                )

                # No significant degradation
                assert not quality_result.degradation_detected, (
                    f"Scenario '{scenario.name}' has quality degradation at turn "
                    f"{quality_result.degradation_turn}: "
                    f"dropped {quality_result.degradation_amount:.1f} points"
                )


class TestQualityDegradationDetection:
    """
    Tests for quality degradation detection.

    Task 023 (partial): Add quality degradation detection
    - Fails if quality drops more than 15 points during a conversation
    """

    @pytest.mark.asyncio
    async def test_no_degradation_in_basic_flows(
        self,
        api_base_url: str,
        quality_evaluator: QualityEvaluatorAgent,
    ):
        """
        Test that basic_flows scenarios show no quality degradation.

        Quality degradation is defined as a drop of 15+ points from one
        turn to the next.
        """
        scenarios = load_basic_flows_scenarios()

        for scenario in scenarios:
            agent = ConversationFlowAgent(
                base_url=api_base_url,
                timeout=DEFAULT_TIMEOUT,
            )

            turns_data = []

            for step in scenario.steps:
                if step.delay_ms > 0:
                    await asyncio.sleep(step.delay_ms / 1000.0)

                turn = await agent.send_message(step.message)
                turns_data.append(
                    {
                        "query": step.message,
                        "response": turn.response_text or "",
                    }
                )

            if len(turns_data) >= 2:
                quality_result = await quality_evaluator.evaluate_conversation(turns_data)

                # Check for degradation
                assert not quality_result.degradation_detected, (
                    f"Quality degradation detected in '{scenario.name}' "
                    f"at turn {quality_result.degradation_turn}: "
                    f"dropped {quality_result.degradation_amount:.1f} points. "
                    f"Scores: {[s.total_score for s in quality_result.turn_scores]}"
                )

    @pytest.mark.asyncio
    async def test_degradation_detection_mechanism(
        self,
        quality_evaluator: QualityEvaluatorAgent,
    ):
        """
        Test that the degradation detection mechanism works correctly.

        This is a unit test to verify the detection logic.
        """
        from tests.agents.quality_evaluator_agent import (
            ConversationQualityResult,
            DimensionScore,
            QualityScore,
        )

        # Create a result with degradation
        result = ConversationQualityResult()

        # Add scores with a significant drop
        scores = [85, 80, 82, 60, 58]  # 22-point drop from turn 3 to 4

        for score_val in scores:
            score = QualityScore(
                total_score=score_val,
                max_score=100,
                dimension_scores={
                    "query_fulfillment": DimensionScore(
                        name="query_fulfillment",
                        score=int(score_val * 0.4),
                        max_score=40,
                    ),
                    "specificity": DimensionScore(
                        name="specificity",
                        score=int(score_val * 0.25),
                        max_score=25,
                    ),
                    "factual_accuracy": DimensionScore(
                        name="factual_accuracy",
                        score=int(score_val * 0.25),
                        max_score=25,
                    ),
                    "actionability": DimensionScore(
                        name="actionability",
                        score=int(score_val * 0.1),
                        max_score=10,
                    ),
                },
                passed=score_val >= PASSING_THRESHOLD,
            )
            result.add_turn_score(score)

        # Verify degradation was detected
        assert result.degradation_detected, "Should detect degradation"
        assert result.degradation_turn == 3, (
            f"Should detect at turn 3, got {result.degradation_turn}"
        )
        assert result.degradation_amount >= 15, (
            f"Drop should be >= 15, got {result.degradation_amount}"
        )


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    pytest.main(
        [
            __file__,
            "-v",
            "-x",
            "--tb=short",
        ]
    )
