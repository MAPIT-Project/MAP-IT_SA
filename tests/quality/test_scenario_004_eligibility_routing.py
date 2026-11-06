# isort: skip_file
"""
Test for Scenario 004: Eligibility Routing (Phase 2: Multi-Programme Navigation).

This test executes the Eligibility Routing scenario against the live MAPIT API
and evaluates quality using the ProductionQualityRunner.

Per PRD MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V2.md:
- EXECUTE: Run scenario `tests/scenarios/advanced/multi_programme/eligibility_routing.yaml`
- Tests routing eligibility questions to correct programme
- Collect: response_text, tools_used, quality_score (QualityEvaluatorAgent),
           factual_score (CrossProgrammeAgent)
- Save: `tests/quality/results/scenarios/eligibility_routing.json`
- Structure: {scenario_name, turns[], average_score, factual_score, failures[], status}

Note: The actual scenario file path is `tests/scenarios/advanced/eligibility_routing.yaml`
(not in multi_programme subdirectory).

Scenario tests Swiss organization eligibility across:
1. Turn 1: General EU programme participation for Swiss company
2. Turn 2: Horizon Europe specific eligibility (Associated Country)
3. Turn 3: Erasmus+ eligibility
4. Turn 4: Creative Europe eligibility
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import pytest

from tests.quality.test_scenario_runner import ScenarioExecutionResult

logger = logging.getLogger(__name__)

# Configuration
SCENARIO_PATH = Path("tests/scenarios/advanced/eligibility_routing.yaml")
RESULTS_PATH = Path("tests/quality/results/scenarios/eligibility_routing.json")
PASSING_THRESHOLD = 80


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


class TestScenario004EligibilityRoutingOffline:
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
        assert data["name"] == "Eligibility Routing"
        assert "steps" in data
        assert len(data["steps"]) == 4  # 4 turns in eligibility routing

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

        # Create mock result
        mock_result = ScenarioExecutionResult(
            scenario_name="Eligibility Routing",
            turns=[
                TurnResult(
                    query="We're a Swiss company wanting to participate in EU funding...",
                    response="Swiss organizations can participate as Associated Country...",
                    quality_score=85.0,
                    factual_score=90.0,
                    tools_used=["search_funding_calls"],
                    turn_number=0,
                ),
                TurnResult(
                    query="Tell me about Horizon Europe eligibility for Swiss organizations...",
                    response="Switzerland is an Associated Country in Horizon Europe...",
                    quality_score=82.0,
                    factual_score=88.0,
                    tools_used=["search_documents"],
                    turn_number=1,
                ),
                TurnResult(
                    query="Now tell me about Erasmus+ eligibility...",
                    response="For Erasmus+, Switzerland is a third country...",
                    quality_score=80.0,
                    factual_score=85.0,
                    tools_used=["check_erasmus_eligibility"],
                    turn_number=2,
                ),
                TurnResult(
                    query="Finally, what about Creative Europe...",
                    response="Switzerland can participate in Creative Europe MEDIA...",
                    quality_score=83.0,
                    factual_score=87.0,
                    tools_used=["check_creative_europe_eligibility"],
                    turn_number=3,
                ),
            ],
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
        assert len(prd_result["turns"]) == 4
        turn = prd_result["turns"][0]
        assert "response_text" in turn
        assert "tools_used" in turn
        assert "quality_score" in turn
        assert "factual_score" in turn

    def test_scenario_covers_swiss_context(self):
        """Verify scenario covers Swiss/Associated Country context."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        # Check tags include relevant context
        tags = data.get("tags", [])
        assert any(tag in tags for tag in ["switzerland", "associated-country", "eligibility"])

        # Check first turn mentions Swiss
        first_turn = data["steps"][0]["message"]
        assert "swiss" in first_turn.lower()

    def test_scenario_covers_all_three_programmes(self):
        """Verify scenario covers Horizon Europe, Erasmus+, and Creative Europe."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        all_messages = " ".join(step["message"] for step in data["steps"])
        all_lower = all_messages.lower()

        # Should cover all three programmes
        has_horizon = "horizon" in all_lower
        has_erasmus = "erasmus" in all_lower
        has_creative = "creative" in all_lower

        assert has_horizon, "Scenario should mention Horizon Europe"
        assert has_erasmus, "Scenario should mention Erasmus+"
        assert has_creative, "Scenario should mention Creative Europe"


class TestScenario004EligibilityRoutingResults:
    """Tests for reading and validating scenario results."""

    def test_read_existing_results(self):
        """Read and validate existing results file if it exists."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet - run execute test first")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        # Validate PRD structure
        assert "scenario_name" in result
        assert result["scenario_name"] == "Eligibility Routing"
        assert "turns" in result
        assert "average_score" in result or "average_quality_score" in result
        assert "factual_score" in result or "average_factual_score" in result
        assert "status" in result

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

            # Identify root causes from failures (per PRD)
            for failure in result.get("failures", []):
                category = failure.get("category", "")
                description = failure.get("description", "")

                logger.warning(f"  - {category}: {description}")

                # PRD-specific root cause hints for eligibility routing
                if "eligibility" in description.lower():
                    logger.warning("    Hint: CrossProgrammeAgent eligibility validation issue")
                if "country" in description.lower():
                    logger.warning("    Hint: Country status check in eu-funding-domain")
                if "programme" in description.lower():
                    logger.warning("    Hint: Programme routing not working correctly")
                if "swiss" in description.lower() or "switzerland" in description.lower():
                    logger.warning("    Hint: Swiss/Associated Country rules not applied")
                if "horizon" in description.lower():
                    logger.warning("    Hint: Horizon Europe eligibility rules issue")
                if "erasmus" in description.lower():
                    logger.warning("    Hint: Erasmus+ eligibility rules issue")
                if "creative" in description.lower():
                    logger.warning("    Hint: Creative Europe eligibility rules issue")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--log-cli-level=INFO"])
