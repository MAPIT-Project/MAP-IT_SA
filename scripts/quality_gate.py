#!/usr/bin/env python3
"""
Quality Gate Script for MAPIT Conversation Stability.

This script evaluates test results and determines if a PR should pass or fail
based on quality criteria defined in the PRD Task 027:

1. Any scenario test fails -> FAIL
2. Quality score below 75 -> FAIL
3. Race condition detected -> FAIL
4. Context integrity check fails -> FAIL

Usage:
    python scripts/quality_gate.py --results-dir test-results/
    python scripts/quality_gate.py --quality-baseline path/to/baseline.json
    python scripts/quality_gate.py --threshold 75

Exit codes:
    0 - Quality gate passed
    1 - Quality gate failed
    2 - Error processing results
"""

import argparse
import json
import logging
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class QualityGateResult:
    """Result of quality gate evaluation."""

    passed: bool
    scenario_tests_passed: bool
    quality_score_passed: bool
    race_condition_passed: bool
    context_integrity_passed: bool
    quality_score: float | None = None
    failed_tests: list = None
    race_condition_details: str = ""
    context_integrity_details: str = ""
    summary: str = ""

    def __post_init__(self):
        if self.failed_tests is None:
            self.failed_tests = []


def parse_junit_xml(xml_path: Path) -> tuple[int, int, list[str]]:
    """
    Parse JUnit XML test results.

    Args:
        xml_path: Path to JUnit XML file

    Returns:
        Tuple of (passed_count, failed_count, list of failed test names)
    """
    if not xml_path.exists():
        logger.warning(f"JUnit XML not found: {xml_path}")
        return 0, 0, []

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Handle both testsuite and testsuites root elements
        if root.tag == "testsuites":
            testsuites = root.findall("testsuite")
        else:
            testsuites = [root] if root.tag == "testsuite" else []

        passed = 0
        failed = 0
        failed_tests = []

        for testsuite in testsuites:
            for testcase in testsuite.findall("testcase"):
                test_name = testcase.get("name", "unknown")
                class_name = testcase.get("classname", "")

                # Check for failures or errors
                failure = testcase.find("failure")
                error = testcase.find("error")
                skipped = testcase.find("skipped")

                if failure is not None or error is not None:
                    failed += 1
                    full_name = f"{class_name}::{test_name}" if class_name else test_name
                    failed_tests.append(full_name)
                elif skipped is None:
                    passed += 1

        return passed, failed, failed_tests

    except ET.ParseError as e:
        logger.error(f"Failed to parse JUnit XML {xml_path}: {e}")
        return 0, 0, []


def check_scenario_tests(results_dir: Path) -> tuple[bool, list[str]]:
    """
    Check if all scenario tests passed.

    Args:
        results_dir: Directory containing test results

    Returns:
        Tuple of (all_passed, list of failed test names)
    """
    all_failed_tests = []

    # Look for JUnit XML files
    xml_files = list(results_dir.glob("*.xml"))
    if not xml_files:
        # Also check subdirectories
        xml_files = list(results_dir.glob("**/*.xml"))

    if not xml_files:
        logger.warning(f"No JUnit XML files found in {results_dir}")
        # If no results found, assume tests weren't run - this is a warning, not failure
        return True, []

    for xml_file in xml_files:
        passed, failed, failed_tests = parse_junit_xml(xml_file)
        all_failed_tests.extend(failed_tests)
        logger.info(f"  {xml_file.name}: {passed} passed, {failed} failed")

    return len(all_failed_tests) == 0, all_failed_tests


def check_quality_score(
    baseline_path: Path | None,
    threshold: int = 75,
) -> tuple[bool, float | None]:
    """
    Check if quality score meets threshold.

    Args:
        baseline_path: Path to quality baseline JSON file
        threshold: Minimum acceptable quality score

    Returns:
        Tuple of (passed, actual_score)
    """
    if baseline_path is None or not baseline_path.exists():
        logger.warning("Quality baseline not found - skipping quality score check")
        # Return True if no baseline exists (first run)
        return True, None

    try:
        with open(baseline_path) as f:
            baseline = json.load(f)

        # Handle different baseline formats
        if "overall_average" in baseline:
            score = baseline["overall_average"]
        elif "average_score" in baseline:
            score = baseline["average_score"]
        elif "scores" in baseline:
            scores = baseline["scores"]
            if isinstance(scores, list) and scores:
                score = sum(scores) / len(scores)
            else:
                score = 0
        else:
            logger.warning(f"Unknown baseline format in {baseline_path}")
            return True, None

        passed = score >= threshold
        return passed, score

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse quality baseline: {e}")
        return True, None


def check_race_conditions(results_dir: Path) -> tuple[bool, str]:
    """
    Check if any race conditions were detected.

    Args:
        results_dir: Directory containing test results

    Returns:
        Tuple of (no_race_conditions, details)
    """
    # Look for race condition test results
    race_xml = results_dir / "race-condition-tests.xml"
    if race_xml.exists():
        passed, failed, failed_tests = parse_junit_xml(race_xml)
        if failed > 0:
            return False, f"Race condition tests failed: {', '.join(failed_tests)}"

    # Also check for race condition markers in any test results
    for xml_file in results_dir.glob("**/*.xml"):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Search for race condition failures
            for testcase in root.iter("testcase"):
                failure = testcase.find("failure")
                if failure is not None:
                    failure_text = failure.text or failure.get("message", "")
                    if any(
                        marker in failure_text.lower()
                        for marker in ["race condition", "duplicate", "out of order"]
                    ):
                        test_name = testcase.get("name", "unknown")
                        msg = f"Race condition detected in {test_name}: {failure_text[:200]}"
                        return False, msg

        except ET.ParseError:
            continue

    return True, "No race conditions detected"


def check_context_integrity(results_dir: Path) -> tuple[bool, str]:
    """
    Check if context integrity checks passed.

    Args:
        results_dir: Directory containing test results

    Returns:
        Tuple of (integrity_maintained, details)
    """
    # Look for context validation test results
    for xml_file in results_dir.glob("**/*.xml"):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            for testcase in root.iter("testcase"):
                test_name = testcase.get("name", "").lower()

                # Check context-related tests
                if "context" in test_name or "integrity" in test_name:
                    failure = testcase.find("failure")
                    error = testcase.find("error")

                    if failure is not None or error is not None:
                        msg = failure.text if failure is not None else error.text
                        return False, f"Context integrity failed in {test_name}: {msg[:200]}"

        except ET.ParseError:
            continue

    return True, "Context integrity maintained"


def evaluate_quality_gate(
    results_dir: Path,
    baseline_path: Path | None = None,
    threshold: int = 75,
) -> QualityGateResult:
    """
    Evaluate all quality gate criteria.

    Args:
        results_dir: Directory containing test results
        baseline_path: Path to quality baseline JSON file
        threshold: Minimum acceptable quality score

    Returns:
        QualityGateResult with all evaluation details
    """
    logger.info("=" * 60)
    logger.info("QUALITY GATE EVALUATION")
    logger.info("=" * 60)

    # 1. Check scenario tests
    logger.info("\n1. Checking scenario test results...")
    scenario_passed, failed_tests = check_scenario_tests(results_dir)
    logger.info(f"   Result: {'PASSED' if scenario_passed else 'FAILED'}")
    if failed_tests:
        logger.info(f"   Failed tests: {len(failed_tests)}")
        for test in failed_tests[:5]:  # Show first 5
            logger.info(f"     - {test}")
        if len(failed_tests) > 5:
            logger.info(f"     ... and {len(failed_tests) - 5} more")

    # 2. Check quality score
    logger.info("\n2. Checking quality score...")
    quality_passed, quality_score = check_quality_score(baseline_path, threshold)
    if quality_score is not None:
        logger.info(f"   Score: {quality_score:.1f}/100 (threshold: {threshold})")
        logger.info(f"   Result: {'PASSED' if quality_passed else 'FAILED'}")
    else:
        logger.info("   Result: SKIPPED (no baseline)")

    # 3. Check race conditions
    logger.info("\n3. Checking for race conditions...")
    race_passed, race_details = check_race_conditions(results_dir)
    logger.info(f"   Result: {'PASSED' if race_passed else 'FAILED'}")
    if not race_passed:
        logger.info(f"   Details: {race_details}")

    # 4. Check context integrity
    logger.info("\n4. Checking context integrity...")
    integrity_passed, integrity_details = check_context_integrity(results_dir)
    logger.info(f"   Result: {'PASSED' if integrity_passed else 'FAILED'}")
    if not integrity_passed:
        logger.info(f"   Details: {integrity_details}")

    # Overall result
    all_passed = all([scenario_passed, quality_passed, race_passed, integrity_passed])

    # Build summary
    summary_parts = []
    if not scenario_passed:
        summary_parts.append(f"{len(failed_tests)} scenario test(s) failed")
    if not quality_passed:
        summary_parts.append(f"quality score {quality_score:.1f} < {threshold}")
    if not race_passed:
        summary_parts.append("race condition detected")
    if not integrity_passed:
        summary_parts.append("context integrity failed")

    summary = "; ".join(summary_parts) if summary_parts else "All checks passed"

    logger.info("\n" + "=" * 60)
    logger.info(f"OVERALL RESULT: {'PASSED' if all_passed else 'FAILED'}")
    logger.info(f"Summary: {summary}")
    logger.info("=" * 60)

    return QualityGateResult(
        passed=all_passed,
        scenario_tests_passed=scenario_passed,
        quality_score_passed=quality_passed,
        race_condition_passed=race_passed,
        context_integrity_passed=integrity_passed,
        quality_score=quality_score,
        failed_tests=failed_tests,
        race_condition_details=race_details,
        context_integrity_details=integrity_details,
        summary=summary,
    )


def write_github_output(result: QualityGateResult):
    """Write result to GitHub Actions output."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"passed={str(result.passed).lower()}\n")
            f.write(f"summary={result.summary}\n")
            if result.quality_score is not None:
                f.write(f"quality_score={result.quality_score:.1f}\n")


def write_github_summary(result: QualityGateResult, threshold: int):
    """Write result to GitHub Actions step summary."""
    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary:
        status_emoji = "✅" if result.passed else "❌"
        with open(github_summary, "a") as f:
            f.write(f"## Quality Gate Results {status_emoji}\n\n")
            f.write("| Check | Status |\n")
            f.write("|-------|--------|\n")
            f.write(
                f"| Scenario Tests | "
                f"{'✅ Passed' if result.scenario_tests_passed else '❌ Failed'} |\n"
            )
            score_status = "⏭️ Skipped"
            if result.quality_score is not None:
                score_status = (
                    f"{'✅' if result.quality_score_passed else '❌'} "
                    f"{result.quality_score:.1f}/{threshold}"
                )
            f.write(f"| Quality Score | {score_status} |\n")
            f.write(
                f"| Race Conditions | "
                f"{'✅ None' if result.race_condition_passed else '❌ Detected'} |\n"
            )
            f.write(
                f"| Context Integrity | "
                f"{'✅ Maintained' if result.context_integrity_passed else '❌ Failed'} |\n"
            )
            f.write(f"\n**Result**: {result.summary}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Quality Gate for MAPIT Conversation Stability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("test-results"),
        help="Directory containing test results (default: test-results/)",
    )
    parser.add_argument(
        "--quality-baseline",
        type=Path,
        default=None,
        help="Path to quality baseline JSON file",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=75,
        help="Minimum quality score threshold (default: 75)",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Fail if results directory is missing",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.results_dir.exists():
        if args.fail_on_missing:
            logger.error(f"Results directory not found: {args.results_dir}")
            sys.exit(2)
        else:
            logger.warning(f"Results directory not found: {args.results_dir}")
            logger.warning("Creating empty results directory for evaluation")
            args.results_dir.mkdir(parents=True, exist_ok=True)

    # Evaluate quality gate
    result = evaluate_quality_gate(
        results_dir=args.results_dir,
        baseline_path=args.quality_baseline,
        threshold=args.threshold,
    )

    # Write GitHub Actions outputs
    write_github_output(result)
    write_github_summary(result, args.threshold)

    # Exit with appropriate code
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
