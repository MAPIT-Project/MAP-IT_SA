"""
Tests for Quality Gate Script (Task 027).

This test file validates the quality gate functionality that blocks PRs if:
1. Any scenario test fails
2. Quality score below 75
3. Race condition detected
4. Context integrity check fails

Run with: pytest tests/test_quality_gate.py -v
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.quality_gate import (
    QualityGateResult,
    check_context_integrity,
    check_quality_score,
    check_race_conditions,
    check_scenario_tests,
    evaluate_quality_gate,
    parse_junit_xml,
)


class TestJunitXmlParsing:
    """Tests for JUnit XML parsing functionality."""

    def test_parse_junit_xml_success(self, tmp_path: Path):
        """Test parsing JUnit XML with all passing tests."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="test_suite" tests="3" failures="0" errors="0">
            <testcase classname="TestClass" name="test_one" time="0.1"/>
            <testcase classname="TestClass" name="test_two" time="0.2"/>
            <testcase classname="TestClass" name="test_three" time="0.3"/>
        </testsuite>
        """
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        passed, failed, failed_tests = parse_junit_xml(xml_file)

        assert passed == 3
        assert failed == 0
        assert failed_tests == []

    def test_parse_junit_xml_with_failures(self, tmp_path: Path):
        """Test parsing JUnit XML with failed tests."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="test_suite" tests="3" failures="1" errors="0">
            <testcase classname="TestClass" name="test_one" time="0.1"/>
            <testcase classname="TestClass" name="test_failed" time="0.2">
                <failure message="AssertionError">Test failed</failure>
            </testcase>
            <testcase classname="TestClass" name="test_three" time="0.3"/>
        </testsuite>
        """
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        passed, failed, failed_tests = parse_junit_xml(xml_file)

        assert passed == 2
        assert failed == 1
        assert "TestClass::test_failed" in failed_tests

    def test_parse_junit_xml_with_errors(self, tmp_path: Path):
        """Test parsing JUnit XML with error tests."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="test_suite" tests="2" failures="0" errors="1">
            <testcase classname="TestClass" name="test_one" time="0.1"/>
            <testcase classname="TestClass" name="test_error" time="0.2">
                <error message="RuntimeError">Test error</error>
            </testcase>
        </testsuite>
        """
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        passed, failed, failed_tests = parse_junit_xml(xml_file)

        assert passed == 1
        assert failed == 1
        assert "TestClass::test_error" in failed_tests

    def test_parse_junit_xml_with_skipped(self, tmp_path: Path):
        """Test parsing JUnit XML with skipped tests (should not count as failures)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="test_suite" tests="3" failures="0" errors="0" skipped="1">
            <testcase classname="TestClass" name="test_one" time="0.1"/>
            <testcase classname="TestClass" name="test_skipped" time="0.0">
                <skipped message="Not implemented"/>
            </testcase>
            <testcase classname="TestClass" name="test_three" time="0.3"/>
        </testsuite>
        """
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        passed, failed, failed_tests = parse_junit_xml(xml_file)

        assert passed == 2
        assert failed == 0
        assert failed_tests == []

    def test_parse_junit_xml_missing_file(self, tmp_path: Path):
        """Test parsing non-existent JUnit XML file."""
        xml_file = tmp_path / "nonexistent.xml"

        passed, failed, failed_tests = parse_junit_xml(xml_file)

        assert passed == 0
        assert failed == 0
        assert failed_tests == []

    def test_parse_junit_xml_testsuites_format(self, tmp_path: Path):
        """Test parsing JUnit XML with testsuites root element."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuites>
            <testsuite name="suite1" tests="2" failures="1">
                <testcase classname="TestClass" name="test_pass" time="0.1"/>
                <testcase classname="TestClass" name="test_fail" time="0.2">
                    <failure message="AssertionError">Failed</failure>
                </testcase>
            </testsuite>
            <testsuite name="suite2" tests="1" failures="0">
                <testcase classname="TestClass2" name="test_pass2" time="0.1"/>
            </testsuite>
        </testsuites>
        """
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        passed, failed, failed_tests = parse_junit_xml(xml_file)

        assert passed == 2
        assert failed == 1
        assert "TestClass::test_fail" in failed_tests


class TestScenarioTestsCheck:
    """Tests for scenario test checking."""

    def test_check_scenario_tests_all_pass(self, tmp_path: Path):
        """Test scenario check when all tests pass."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="scenario_tests" tests="5" failures="0">
            <testcase classname="TestBasic" name="test_funding_search" time="1.0"/>
            <testcase classname="TestBasic" name="test_project_search" time="1.0"/>
            <testcase classname="TestBasic" name="test_budget_calc" time="1.0"/>
            <testcase classname="TestBasic" name="test_timeline" time="1.0"/>
            <testcase classname="TestBasic" name="test_follow_up" time="1.0"/>
        </testsuite>
        """
        xml_file = tmp_path / "scenario-tests.xml"
        xml_file.write_text(xml_content)

        all_passed, failed_tests = check_scenario_tests(tmp_path)

        assert all_passed is True
        assert failed_tests == []

    def test_check_scenario_tests_with_failures(self, tmp_path: Path):
        """Test scenario check when some tests fail."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="scenario_tests" tests="5" failures="2">
            <testcase classname="TestBasic" name="test_funding_search" time="1.0"/>
            <testcase classname="TestBasic" name="test_project_search" time="1.0">
                <failure message="AssertionError">Search failed</failure>
            </testcase>
            <testcase classname="TestBasic" name="test_budget_calc" time="1.0"/>
            <testcase classname="TestBasic" name="test_timeline" time="1.0">
                <failure message="AssertionError">Timeline failed</failure>
            </testcase>
            <testcase classname="TestBasic" name="test_follow_up" time="1.0"/>
        </testsuite>
        """
        xml_file = tmp_path / "scenario-tests.xml"
        xml_file.write_text(xml_content)

        all_passed, failed_tests = check_scenario_tests(tmp_path)

        assert all_passed is False
        assert len(failed_tests) == 2
        assert "TestBasic::test_project_search" in failed_tests
        assert "TestBasic::test_timeline" in failed_tests

    def test_check_scenario_tests_empty_directory(self, tmp_path: Path):
        """Test scenario check with empty results directory."""
        all_passed, failed_tests = check_scenario_tests(tmp_path)

        # Empty directory should pass (no test results = nothing failed)
        assert all_passed is True
        assert failed_tests == []


class TestQualityScoreCheck:
    """Tests for quality score checking."""

    def test_check_quality_score_above_threshold(self, tmp_path: Path):
        """Test quality score above threshold."""
        baseline = {"overall_average": 85.5}
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text(json.dumps(baseline))

        passed, score = check_quality_score(baseline_file, threshold=75)

        assert passed is True
        assert score == 85.5

    def test_check_quality_score_below_threshold(self, tmp_path: Path):
        """Test quality score below threshold."""
        baseline = {"overall_average": 65.0}
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text(json.dumps(baseline))

        passed, score = check_quality_score(baseline_file, threshold=75)

        assert passed is False
        assert score == 65.0

    def test_check_quality_score_at_threshold(self, tmp_path: Path):
        """Test quality score exactly at threshold."""
        baseline = {"overall_average": 75.0}
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text(json.dumps(baseline))

        passed, score = check_quality_score(baseline_file, threshold=75)

        assert passed is True
        assert score == 75.0

    def test_check_quality_score_missing_file(self):
        """Test quality score with missing baseline file."""
        passed, score = check_quality_score(Path("/nonexistent/file.json"), threshold=75)

        # Missing file should pass (first run scenario)
        assert passed is True
        assert score is None

    def test_check_quality_score_alternative_format(self, tmp_path: Path):
        """Test quality score with alternative JSON format."""
        baseline = {"average_score": 80.0}
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text(json.dumps(baseline))

        passed, score = check_quality_score(baseline_file, threshold=75)

        assert passed is True
        assert score == 80.0

    def test_check_quality_score_scores_list_format(self, tmp_path: Path):
        """Test quality score with scores list format."""
        baseline = {"scores": [70, 80, 90]}
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text(json.dumps(baseline))

        passed, score = check_quality_score(baseline_file, threshold=75)

        assert passed is True
        assert score == 80.0  # Average of [70, 80, 90]


class TestRaceConditionCheck:
    """Tests for race condition detection."""

    def test_check_race_conditions_none_detected(self, tmp_path: Path):
        """Test race condition check with no issues detected."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="race_tests" tests="3" failures="0">
            <testcase classname="TestRace" name="test_concurrent" time="1.0"/>
            <testcase classname="TestRace" name="test_rapid" time="1.0"/>
            <testcase classname="TestRace" name="test_interleaved" time="1.0"/>
        </testsuite>
        """
        xml_file = tmp_path / "race-condition-tests.xml"
        xml_file.write_text(xml_content)

        passed, details = check_race_conditions(tmp_path)

        assert passed is True
        assert "No race conditions detected" in details

    def test_check_race_conditions_detected_in_failure(self, tmp_path: Path):
        """Test race condition check with race condition in failure message."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="race_tests" tests="1" failures="1">
            <testcase classname="TestRace" name="test_concurrent" time="1.0">
                <failure message="Race condition">
                    Race condition detected: duplicate messages found
                </failure>
            </testcase>
        </testsuite>
        """
        xml_file = tmp_path / "race-condition-tests.xml"
        xml_file.write_text(xml_content)

        passed, details = check_race_conditions(tmp_path)

        assert passed is False
        assert "Race condition" in details or "race condition" in details.lower()

    def test_check_race_conditions_duplicate_messages(self, tmp_path: Path):
        """Test race condition check with duplicate message error."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="tests" tests="1" failures="1">
            <testcase classname="TestConcurrent" name="test_rapid_messages" time="1.0">
                <failure message="AssertionError">
                    Duplicate messages detected in storage
                </failure>
            </testcase>
        </testsuite>
        """
        xml_file = tmp_path / "concurrent-tests.xml"
        xml_file.write_text(xml_content)

        passed, details = check_race_conditions(tmp_path)

        assert passed is False


class TestContextIntegrityCheck:
    """Tests for context integrity checking."""

    def test_check_context_integrity_maintained(self, tmp_path: Path):
        """Test context integrity check when integrity is maintained."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="context_tests" tests="3" failures="0">
            <testcase classname="TestContext" name="test_context_integrity" time="1.0"/>
            <testcase classname="TestContext" name="test_message_storage" time="1.0"/>
            <testcase classname="TestContext" name="test_order_preserved" time="1.0"/>
        </testsuite>
        """
        xml_file = tmp_path / "context-tests.xml"
        xml_file.write_text(xml_content)

        passed, details = check_context_integrity(tmp_path)

        assert passed is True
        assert "maintained" in details.lower()

    def test_check_context_integrity_failed(self, tmp_path: Path):
        """Test context integrity check when integrity fails."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="context_tests" tests="1" failures="1">
            <testcase classname="TestContext" name="test_context_integrity" time="1.0">
                <failure message="Context integrity check failed">
                    DB and Redis are out of sync
                </failure>
            </testcase>
        </testsuite>
        """
        xml_file = tmp_path / "context-tests.xml"
        xml_file.write_text(xml_content)

        passed, details = check_context_integrity(tmp_path)

        assert passed is False


class TestQualityGateEvaluation:
    """Tests for the full quality gate evaluation."""

    def test_evaluate_quality_gate_all_pass(self, tmp_path: Path):
        """Test quality gate evaluation when all criteria pass."""
        # Create passing test results
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="tests" tests="5" failures="0">
            <testcase classname="TestBasic" name="test_one" time="1.0"/>
            <testcase classname="TestBasic" name="test_two" time="1.0"/>
            <testcase classname="TestBasic" name="test_three" time="1.0"/>
            <testcase classname="TestContext" name="test_context_integrity" time="1.0"/>
            <testcase classname="TestRace" name="test_race_condition" time="1.0"/>
        </testsuite>
        """
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        # Create passing quality baseline
        baseline = {"overall_average": 85.0}
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text(json.dumps(baseline))

        result = evaluate_quality_gate(
            results_dir=tmp_path,
            baseline_path=baseline_file,
            threshold=75,
        )

        assert result.passed is True
        assert result.scenario_tests_passed is True
        assert result.quality_score_passed is True
        assert result.race_condition_passed is True
        assert result.context_integrity_passed is True
        assert "All checks passed" in result.summary

    def test_evaluate_quality_gate_scenario_failure(self, tmp_path: Path):
        """Test quality gate evaluation when scenario tests fail."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="tests" tests="5" failures="2">
            <testcase classname="TestBasic" name="test_one" time="1.0">
                <failure message="Failed">Test failed</failure>
            </testcase>
            <testcase classname="TestBasic" name="test_two" time="1.0">
                <failure message="Failed">Test failed</failure>
            </testcase>
            <testcase classname="TestBasic" name="test_three" time="1.0"/>
            <testcase classname="TestContext" name="test_context_integrity" time="1.0"/>
            <testcase classname="TestRace" name="test_race_condition" time="1.0"/>
        </testsuite>
        """
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        baseline = {"overall_average": 85.0}
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text(json.dumps(baseline))

        result = evaluate_quality_gate(
            results_dir=tmp_path,
            baseline_path=baseline_file,
            threshold=75,
        )

        assert result.passed is False
        assert result.scenario_tests_passed is False
        assert len(result.failed_tests) == 2
        assert "scenario test" in result.summary.lower()

    def test_evaluate_quality_gate_quality_failure(self, tmp_path: Path):
        """Test quality gate evaluation when quality score is below threshold."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="tests" tests="3" failures="0">
            <testcase classname="TestBasic" name="test_one" time="1.0"/>
            <testcase classname="TestBasic" name="test_two" time="1.0"/>
            <testcase classname="TestBasic" name="test_three" time="1.0"/>
        </testsuite>
        """
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        baseline = {"overall_average": 60.0}  # Below threshold
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text(json.dumps(baseline))

        result = evaluate_quality_gate(
            results_dir=tmp_path,
            baseline_path=baseline_file,
            threshold=75,
        )

        assert result.passed is False
        assert result.quality_score_passed is False
        assert result.quality_score == 60.0
        assert "quality score" in result.summary.lower()

    def test_evaluate_quality_gate_race_condition_failure(self, tmp_path: Path):
        """Test quality gate evaluation when race condition is detected."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="tests" tests="1" failures="1">
            <testcase classname="TestRace" name="test_concurrent" time="1.0">
                <failure message="Race condition detected">
                    Race condition: duplicate messages
                </failure>
            </testcase>
        </testsuite>
        """
        xml_file = tmp_path / "race-condition-tests.xml"
        xml_file.write_text(xml_content)

        result = evaluate_quality_gate(
            results_dir=tmp_path,
            baseline_path=None,
            threshold=75,
        )

        assert result.passed is False
        assert result.race_condition_passed is False
        assert "race condition" in result.summary.lower()

    def test_evaluate_quality_gate_context_integrity_failure(self, tmp_path: Path):
        """Test quality gate evaluation when context integrity fails."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="tests" tests="1" failures="1">
            <testcase classname="TestContext" name="test_context_integrity" time="1.0">
                <failure message="Integrity check failed">
                    DB and Redis out of sync
                </failure>
            </testcase>
        </testsuite>
        """
        xml_file = tmp_path / "context-tests.xml"
        xml_file.write_text(xml_content)

        result = evaluate_quality_gate(
            results_dir=tmp_path,
            baseline_path=None,
            threshold=75,
        )

        assert result.passed is False
        assert result.context_integrity_passed is False
        assert "context integrity" in result.summary.lower()

    def test_evaluate_quality_gate_multiple_failures(self, tmp_path: Path):
        """Test quality gate evaluation with multiple failure types."""
        # Create failing tests
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="tests" tests="3" failures="2">
            <testcase classname="TestBasic" name="test_one" time="1.0">
                <failure message="Failed">Test failed</failure>
            </testcase>
            <testcase classname="TestContext" name="test_context_integrity" time="1.0">
                <failure message="Integrity failed">DB/Redis mismatch</failure>
            </testcase>
            <testcase classname="TestRace" name="test_race" time="1.0"/>
        </testsuite>
        """
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        # Create failing quality baseline
        baseline = {"overall_average": 50.0}
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text(json.dumps(baseline))

        result = evaluate_quality_gate(
            results_dir=tmp_path,
            baseline_path=baseline_file,
            threshold=75,
        )

        assert result.passed is False
        assert result.scenario_tests_passed is False
        assert result.quality_score_passed is False
        assert result.context_integrity_passed is False
        # Summary should mention multiple issues
        assert ";" in result.summary  # Multiple issues separated by semicolon


class TestQualityGateResult:
    """Tests for QualityGateResult dataclass."""

    def test_quality_gate_result_defaults(self):
        """Test QualityGateResult default values."""
        result = QualityGateResult(
            passed=True,
            scenario_tests_passed=True,
            quality_score_passed=True,
            race_condition_passed=True,
            context_integrity_passed=True,
        )

        assert result.failed_tests == []
        assert result.quality_score is None
        assert result.race_condition_details == ""
        assert result.context_integrity_details == ""
        assert result.summary == ""

    def test_quality_gate_result_with_values(self):
        """Test QualityGateResult with all values set."""
        result = QualityGateResult(
            passed=False,
            scenario_tests_passed=False,
            quality_score_passed=True,
            race_condition_passed=True,
            context_integrity_passed=True,
            quality_score=80.0,
            failed_tests=["test_one", "test_two"],
            race_condition_details="None detected",
            context_integrity_details="Maintained",
            summary="2 tests failed",
        )

        assert result.passed is False
        assert result.quality_score == 80.0
        assert len(result.failed_tests) == 2
        assert result.summary == "2 tests failed"


class TestWorkflowIntegration:
    """Tests for workflow configuration integration."""

    def test_quality_gate_job_in_workflow(self):
        """Test that quality-gate job is properly configured in workflow."""
        import yaml

        workflow_path = (
            Path(__file__).parent.parent / ".github" / "workflows" / "conversation-tests.yml"
        )

        if not workflow_path.exists():
            pytest.skip("Workflow file not found")

        with open(workflow_path) as f:
            config = yaml.safe_load(f)

        # Check quality-gate job exists
        assert "jobs" in config
        jobs = config["jobs"]
        assert "quality-gate" in jobs, "quality-gate job should exist"

        quality_gate_job = jobs["quality-gate"]

        # Check job configuration
        assert "needs" in quality_gate_job
        needs = quality_gate_job["needs"]
        assert "integration-tests" in needs
        assert "race-condition-tests" in needs

        # Check it only runs on PRs
        assert "if" in quality_gate_job
        assert "pull_request" in quality_gate_job["if"]

        # Check steps include quality gate script
        steps = quality_gate_job.get("steps", [])
        quality_gate_step = None
        for step in steps:
            if "Quality Gate" in step.get("name", ""):
                quality_gate_step = step
                break

        assert quality_gate_step is not None, "Should have Quality Gate step"
        assert "run" in quality_gate_step
        assert "quality_gate.py" in quality_gate_step["run"]

    def test_final_status_depends_on_quality_gate(self):
        """Test that final-status job depends on quality-gate."""
        import yaml

        workflow_path = (
            Path(__file__).parent.parent / ".github" / "workflows" / "conversation-tests.yml"
        )

        if not workflow_path.exists():
            pytest.skip("Workflow file not found")

        with open(workflow_path) as f:
            config = yaml.safe_load(f)

        jobs = config["jobs"]
        final_status_job = jobs.get("final-status")

        assert final_status_job is not None
        assert "needs" in final_status_job

        needs = final_status_job["needs"]
        if isinstance(needs, str):
            needs = [needs]

        assert "quality-gate" in needs, "final-status should depend on quality-gate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
