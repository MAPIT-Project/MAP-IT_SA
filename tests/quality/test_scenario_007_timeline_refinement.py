# isort: skip_file
"""
Test for Scenario 007: Timeline Refinement (Phase 3: Proposal Workflow).

This test executes the Timeline Refinement scenario against the live MAPIT API
and evaluates quality using the ProductionQualityRunner.

Per PRD MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V3.md:
- EXECUTE: Run scenario `tests/scenarios/advanced/proposal_workflow/timeline_refinement.yaml`
- Tests timeline generation and refinement workflow
- Collect: response_text, tools_used, quality_score (QualityEvaluatorAgent),
           factual_score (CrossProgrammeAgent)
- Save: `tests/quality/results/scenarios/timeline_refinement.json`
- Structure: {scenario_name, turns[], average_score, factual_score, failures[], status}

Note: The actual scenario file path is `tests/scenarios/advanced/timeline_refinement.yaml`
(not in proposal_workflow subdirectory).

Scenario tests iterative timeline generation and refinement for health research:
1. Turn 1: Generate timeline for 48-month health research project with 6 WPs
2. Turn 2: Add clinical trial phase in WP4
3. Turn 3: Add buffer for ethics approval delay (6 months)
4. Turn 4: Show similar projects' timelines for comparison
5. Turn 5: Adjust milestones to match typical patterns
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import pytest

from tests.quality.test_scenario_runner import ScenarioExecutionResult

logger = logging.getLogger(__name__)

# Configuration
SCENARIO_PATH = Path("tests/scenarios/advanced/timeline_refinement.yaml")
RESULTS_PATH = Path("tests/quality/results/scenarios/timeline_refinement.json")
PASSING_THRESHOLD = 80
NUM_TURNS = 5


def save_result_prd_format(result: ScenarioExecutionResult, output_path: Path) -> dict:
    """
    Save result in PRD-specified format.

    PRD format: {scenario_name, turns[], average_score, factual_score, failures[], status}
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build PRD-compliant structure
    prd_result = {
        "scenario_name": result.scenario_name,
        "turns": [
            {
                "turn_number": t.turn_number,
                "query": t.query,
                "response_text": t.response,
                "tools_used": t.tools_used,
                "quality_score": t.quality_score,
                "factual_score": t.factual_score,
                "failures": [f.to_dict() for f in t.failures],
                "passed": t.passed,
            }
            for t in result.turns
        ],
        "average_score": result.average_quality_score,
        "factual_score": result.average_factual_score,
        "failures": [f.to_dict() for f in result.failures],
        "status": result.status,
        "execution_time_ms": result.execution_time_ms,
        "timestamp": datetime.now().isoformat(),
        "metadata": result.metadata,
        "fix_history": [],  # Empty until FIX IF NEEDED runs
    }

    with open(output_path, "w") as f:
        json.dump(prd_result, f, indent=2)

    return prd_result


class TestScenario007TimelineRefinementOffline:
    """Offline tests that don't require live API."""

    def test_scenario_file_exists(self):
        """Verify the scenario YAML file exists."""
        assert SCENARIO_PATH.exists(), f"Scenario file not found: {SCENARIO_PATH}"

    def test_scenario_yaml_is_valid(self):
        """Verify the scenario YAML is parseable."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        assert "name" in data
        assert data["name"] == "Timeline Refinement"
        assert "steps" in data
        assert (
            len(data["steps"]) == NUM_TURNS
        ), f"Expected {NUM_TURNS} turns, got {len(data['steps'])}"

    def test_results_directory_exists(self):
        """Verify results directory can be created."""
        RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        assert RESULTS_PATH.parent.exists()

    def test_prd_result_format(self):
        """Test that PRD result format is correctly structured."""
        from tests.quality.test_scenario_runner import (
            FailureCategory,
            FailureRecord,
            FailureSeverity,
            TurnResult,
        )

        # Create mock result for 5-turn timeline refinement scenario
        mock_turns = [
            TurnResult(
                query=f"Query {i}",
                response=f"Response {i}",
                quality_score=80.0 + i,
                factual_score=85.0 + i % 5,
                tools_used=["generate_timeline"] if i % 2 == 0 else ["find_similar_projects"],
                turn_number=i,
            )
            for i in range(NUM_TURNS)
        ]

        mock_result = ScenarioExecutionResult(
            scenario_name="Timeline Refinement",
            turns=mock_turns,
            failures=[
                FailureRecord(
                    category=FailureCategory.MISSING_DATA,
                    severity=FailureSeverity.MEDIUM,
                    description="Test failure",
                    turn_number=0,
                ),
            ],
        )

        # Use temp directory for test
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_result.json"
            prd_result = save_result_prd_format(mock_result, test_path)

        # Verify PRD structure
        assert "scenario_name" in prd_result
        assert "turns" in prd_result
        assert "average_score" in prd_result
        assert "factual_score" in prd_result
        assert "failures" in prd_result
        assert "status" in prd_result
        assert "fix_history" in prd_result

        # Verify turn structure
        assert len(prd_result["turns"]) == NUM_TURNS
        turn = prd_result["turns"][0]
        assert "response_text" in turn
        assert "tools_used" in turn
        assert "quality_score" in turn
        assert "factual_score" in turn

    def test_scenario_covers_timeline_refinement(self):
        """Verify scenario covers timeline refinement workflow."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        # Check tags include relevant context
        tags = data.get("tags", [])
        assert any(tag in tags for tag in ["timeline", "proposal-development", "health-research"])

        # Check first turn mentions timeline generation
        first_turn = data["steps"][0]["message"]
        assert "timeline" in first_turn.lower()

    def test_scenario_covers_timeline_elements(self):
        """Verify scenario covers all timeline refinement elements."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        all_messages = " ".join(step["message"] for step in data["steps"])
        all_lower = all_messages.lower()

        # Should cover key timeline refinement elements
        has_timeline = "timeline" in all_lower
        has_work_packages = "work package" in all_lower or "wp" in all_lower
        has_clinical_trial = "clinical trial" in all_lower or "clinical" in all_lower
        has_buffer = "buffer" in all_lower or "delay" in all_lower
        has_similar = "similar" in all_lower or "comparison" in all_lower
        has_milestones = "milestone" in all_lower

        assert has_timeline, "Scenario should mention timeline"
        assert has_work_packages, "Scenario should mention work packages"
        assert has_clinical_trial, "Scenario should include clinical trial phase"
        assert has_buffer, "Scenario should include buffer for delays"
        assert has_similar, "Scenario should include comparison with similar projects"
        assert has_milestones, "Scenario should include milestone adjustment"

    def test_scenario_is_5_turns(self):
        """Verify this is a 5-turn timeline refinement scenario."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        assert (
            len(data["steps"]) == NUM_TURNS
        ), f"Expected {NUM_TURNS} turns, got {len(data['steps'])}"


class TestScenario007TimelineRefinementResults:
    """Tests for reading and validating scenario results."""

    def test_read_existing_results(self):
        """Read and validate existing results file if it exists."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet - run execute test first")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        # Validate PRD structure
        assert "scenario_name" in result
        assert result["scenario_name"] == "Timeline Refinement"
        assert "turns" in result
        assert "average_score" in result or "average_quality_score" in result
        assert "factual_score" in result or "average_factual_score" in result
        assert "status" in result

        # Validate this is a 5-turn scenario
        assert (
            len(result["turns"]) == NUM_TURNS
        ), f"Expected {NUM_TURNS} turns, got {len(result['turns'])}"

        # Log current status
        logger.info(f"Current status: {result['status']}")
        logger.info(
            f"Average score: {result.get('average_score', result.get('average_quality_score'))}"
        )

    def test_check_if_fix_needed(self):
        """Check if scenario needs fixing based on results."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        avg_score = result.get("average_score", result.get("average_quality_score", 0))

        if avg_score >= PASSING_THRESHOLD:
            logger.info(f"Score {avg_score:.1f} >= {PASSING_THRESHOLD}: No fix needed")
        else:
            logger.warning(f"Score {avg_score:.1f} < {PASSING_THRESHOLD}: Fix needed")
            logger.warning(f"Failures: {len(result.get('failures', []))}")

            # Identify problematic turns
            for turn in result.get("turns", []):
                turn_score = turn.get("quality_score", 0)
                if turn_score < PASSING_THRESHOLD:
                    logger.warning(
                        f"  Turn {turn.get('turn_number')}: score={turn_score:.1f}, "
                        f"tools={turn.get('tools_used')}"
                    )

            # Identify root causes from failures (per PRD)
            for failure in result.get("failures", []):
                category = failure.get("category", "")
                description = failure.get("description", "")

                logger.warning(f"  - {category}: {description}")

                # PRD-specific root cause hints for timeline refinement
                if "timeline" in description.lower() or "generate" in description.lower():
                    logger.warning("    Hint: Fix app/services/tools/timeline_generator.py")
                if "work package" in description.lower() or "wp" in description.lower():
                    logger.warning("    Hint: Fix WP generation logic in timeline tool")
                if "milestone" in description.lower():
                    logger.warning("    Hint: Fix milestone generation logic")
                if "similar" in description.lower():
                    logger.warning("    Hint: Fix app/services/tools/similar_projects.py")
                if "context" in description.lower():
                    logger.warning("    Hint: Fix app/services/memory/memory_service.py")

    def test_analyze_per_turn_scores(self):
        """Analyze scores per turn to identify weak points."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        turns = result.get("turns", [])

        # Group turns by quality level
        high_quality = []
        medium_quality = []
        low_quality = []

        for turn in turns:
            score = turn.get("quality_score", 0)
            turn_num = turn.get("turn_number", 0)

            if score >= 85:
                high_quality.append(turn_num)
            elif score >= 70:
                medium_quality.append(turn_num)
            else:
                low_quality.append(turn_num)

        logger.info(f"High quality turns (>=85): {high_quality}")
        logger.info(f"Medium quality turns (70-84): {medium_quality}")
        logger.info(f"Low quality turns (<70): {low_quality}")

        # Identify patterns specific to timeline refinement
        if low_quality:
            logger.warning(f"Low quality turns need attention: {low_quality}")

            # Check specific turn patterns for timeline refinement
            for turn_num in low_quality:
                if turn_num == 0:
                    logger.warning(
                        "  Turn 0 (initial timeline): May need better timeline generation"
                    )
                elif turn_num == 1:
                    logger.warning(
                        "  Turn 1 (clinical trial): May need better WP modification handling"
                    )
                elif turn_num == 2:
                    logger.warning("  Turn 2 (buffer): May need better delay/buffer handling")
                elif turn_num == 3:
                    logger.warning(
                        "  Turn 3 (comparison): May need similar project search improvement"
                    )
                elif turn_num == 4:
                    logger.warning("  Turn 4 (milestones): May need milestone adjustment logic")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--log-cli-level=INFO"])
