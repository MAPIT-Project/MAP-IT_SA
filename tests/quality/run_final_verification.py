#!/usr/bin/env python3
# isort: skip_file
"""
Final Verification Script for MAPIT Production Quality Validation.

This script runs ALL 42 scenarios against the live API to determine production readiness.
Per PRD Phase 13: All scenarios must score >= 80/100 for production readiness.

Usage:
    python tests/quality/run_final_verification.py

Outputs:
    - tests/quality/results/final_verification_report.json (detailed results)
    - tests/quality/results/FINAL_VERIFICATION_SUMMARY.md (human-readable summary)
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.test_production_quality_validation import (
    ProductionQualityRunner,
    ScenarioExecutionResult,
)

# All 42 scenarios from the PRD, organized by phase
# Base path for scenario files
_BASE = "tests/scenarios/advanced"

SCENARIOS = {
    "Phase 2: Multi-Programme Navigation": [
        ("001", "programme_discovery", f"{_BASE}/programme_discovery.yaml"),
        ("002", "programme_comparison", f"{_BASE}/programme_comparison.yaml"),
        ("003", "programme_recommendation", f"{_BASE}/programme_recommendation.yaml"),
        ("004", "eligibility_routing", f"{_BASE}/eligibility_routing.yaml"),
    ],
    "Phase 3: Proposal Workflow": [
        ("005", "full_proposal_journey", f"{_BASE}/full_proposal_journey.yaml"),
        ("006", "budget_iteration", f"{_BASE}/budget_iteration.yaml"),
        ("007", "timeline_refinement", f"{_BASE}/timeline_refinement.yaml"),
        ("008", "consortium_building", f"{_BASE}/consortium_building.yaml"),
    ],
    "Phase 4: Partner Discovery": [
        ("009", "partner_search_refinement", f"{_BASE}/partner_search_refinement.yaml"),
        ("010", "partner_comparison", f"{_BASE}/partner_comparison.yaml"),
        ("011", "network_exploration", f"{_BASE}/network_exploration.yaml"),
        ("012", "organization_deep_dive", f"{_BASE}/organization_deep_dive.yaml"),
    ],
    "Phase 5: Personalization": [
        ("013", "user_context_learning", f"{_BASE}/user_context_learning.yaml"),
        ("014", "returning_user_context", f"{_BASE}/returning_user_context.yaml"),
        ("015", "progressive_profile", f"{_BASE}/progressive_profile.yaml"),
        ("016", "preference_filtering", f"{_BASE}/preference_filtering.yaml"),
    ],
    "Phase 6: Strategic Planning": [
        ("017", "funding_strategy", f"{_BASE}/funding_strategy.yaml"),
        ("018", "portfolio_planning", f"{_BASE}/portfolio_planning.yaml"),
        ("019", "capacity_building", f"{_BASE}/capacity_building.yaml"),
        ("020", "risk_assessment", f"{_BASE}/risk_assessment.yaml"),
    ],
    "Phase 7: Comparisons": [
        ("021", "funding_type_comparison", f"{_BASE}/funding_type_comparison.yaml"),
        ("022", "success_rate_analysis", f"{_BASE}/success_rate_analysis.yaml"),
        ("023", "budget_comparison", f"{_BASE}/budget_comparison.yaml"),
        ("024", "timeline_comparison", f"{_BASE}/timeline_comparison.yaml"),
    ],
    "Phase 8: Deadline Management": [
        ("025", "urgent_deadline", f"{_BASE}/urgent_deadline.yaml"),
        ("026", "deadline_tracking", f"{_BASE}/deadline_tracking.yaml"),
        ("027", "call_opening_alert", f"{_BASE}/call_opening_alert.yaml"),
        ("028", "multi_call_timeline", f"{_BASE}/multi_call_timeline.yaml"),
    ],
    "Phase 9: Complex Eligibility": [
        ("029", "multi_factor_eligibility", f"{_BASE}/multi_factor_eligibility.yaml"),
        ("030", "sme_eligibility", f"{_BASE}/sme_eligibility.yaml"),
        ("031", "consortium_eligibility", f"{_BASE}/consortium_eligibility.yaml"),
        ("032", "cross_programme_eligibility", f"{_BASE}/cross_programme_eligibility.yaml"),
    ],
    "Phase 10: Erasmus+ Specific": [
        ("033", "erasmus_action_selection", f"{_BASE}/erasmus_action_selection.yaml"),
        ("034", "erasmus_budget_calculation", f"{_BASE}/erasmus_budget_calculation.yaml"),
        ("035", "erasmus_accreditation", f"{_BASE}/erasmus_accreditation.yaml"),
    ],
    "Phase 11: Creative Europe Specific": [
        ("036", "creative_europe_strand", f"{_BASE}/creative_europe_strand.yaml"),
        ("037", "creative_europe_eligibility", f"{_BASE}/creative_europe_eligibility.yaml"),
        ("038", "creative_europe_cooperation", f"{_BASE}/creative_europe_cooperation.yaml"),
    ],
    "Phase 12: Error Handling": [
        ("039", "conflicting_requirements", f"{_BASE}/conflicting_requirements.yaml"),
        ("040", "outdated_information", f"{_BASE}/outdated_information.yaml"),
        ("041", "ambiguous_programme", f"{_BASE}/ambiguous_programme.yaml"),
        ("042", "out_of_scope", f"{_BASE}/out_of_scope.yaml"),
    ],
}

PASS_THRESHOLD = 80
PRODUCTION_READY_THRESHOLD = 0.80  # 80% of scenarios must pass


async def run_single_scenario(
    runner: ProductionQualityRunner,
    scenario_num: str,
    scenario_name: str,
    scenario_path: str,
) -> tuple[str, str, ScenarioExecutionResult | None, str | None]:
    """
    Run a single scenario and return results.

    Returns:
        Tuple of (scenario_num, scenario_name, result, error_message)
    """
    try:
        print(f"  Running {scenario_num}: {scenario_name}...", flush=True)
        result = await runner.run_scenario(scenario_path)

        # Save individual result
        output_path = Path(f"tests/quality/results/scenarios/{scenario_name}.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)

        status = "PASS" if result.passed else "FAIL"
        print(
            f"    [{status}] Score: {result.average_quality_score:.1f}/100, "
            f"Factual: {result.average_factual_score:.1f}%"
        )
        return scenario_num, scenario_name, result, None

    except Exception as e:
        print(f"    [ERROR] {str(e)}")
        return scenario_num, scenario_name, None, str(e)


async def run_all_scenarios() -> dict[str, Any]:
    """
    Run all 42 scenarios and generate the final verification report.

    Returns:
        Complete verification report dictionary
    """
    print("=" * 70)
    print("MAPIT Final Verification - Running ALL 42 Scenarios")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Pass Threshold: {PASS_THRESHOLD}/100")
    print(f"Production Ready Threshold: {PRODUCTION_READY_THRESHOLD * 100}% scenarios must pass")
    print("=" * 70)
    print()

    runner = ProductionQualityRunner(base_url="http://localhost:8000")

    # Track results
    all_results: list[dict[str, Any]] = []
    phase_results: dict[str, dict[str, Any]] = {}
    total_scenarios = 0
    passed_scenarios = 0
    failed_scenarios = 0
    error_scenarios = 0
    total_quality_score = 0.0
    total_factual_score = 0.0

    # Run scenarios by phase
    for phase_name, scenarios in SCENARIOS.items():
        print(f"\n{phase_name}")
        print("-" * len(phase_name))

        phase_passed = 0
        phase_failed = 0
        phase_error = 0
        phase_quality_sum = 0.0
        phase_factual_sum = 0.0

        for scenario_num, scenario_name, scenario_path in scenarios:
            total_scenarios += 1
            num, name, result, error = await run_single_scenario(
                runner, scenario_num, scenario_name, scenario_path
            )

            scenario_data = {
                "scenario_num": num,
                "scenario_name": name,
                "phase": phase_name,
            }

            if error:
                scenario_data["status"] = "ERROR"
                scenario_data["error"] = error
                scenario_data["quality_score"] = 0.0
                scenario_data["factual_score"] = 0.0
                error_scenarios += 1
                phase_error += 1
            elif result:
                scenario_data["status"] = result.status
                scenario_data["quality_score"] = result.average_quality_score
                scenario_data["factual_score"] = result.average_factual_score
                scenario_data["turn_count"] = len(result.turns)
                scenario_data["critical_failures"] = len(
                    [f for f in result.failures if f.severity.value == "CRITICAL"]
                )
                scenario_data["high_failures"] = len(
                    [f for f in result.failures if f.severity.value == "HIGH"]
                )

                if result.passed:
                    passed_scenarios += 1
                    phase_passed += 1
                else:
                    failed_scenarios += 1
                    phase_failed += 1

                total_quality_score += result.average_quality_score
                total_factual_score += result.average_factual_score
                phase_quality_sum += result.average_quality_score
                phase_factual_sum += result.average_factual_score

            all_results.append(scenario_data)

        # Calculate phase summary
        phase_total = len(scenarios)
        phase_results[phase_name] = {
            "total": phase_total,
            "passed": phase_passed,
            "failed": phase_failed,
            "error": phase_error,
            "pass_rate": f"{(phase_passed / phase_total) * 100:.1f}%",
            "avg_quality_score": (
                phase_quality_sum / (phase_passed + phase_failed)
                if (phase_passed + phase_failed) > 0
                else 0.0
            ),
            "avg_factual_score": (
                phase_factual_sum / (phase_passed + phase_failed)
                if (phase_passed + phase_failed) > 0
                else 0.0
            ),
        }

        pass_rate = phase_results[phase_name]["pass_rate"]
        print(f"  Phase Summary: {phase_passed}/{phase_total} passed ({pass_rate})")

    # Calculate overall statistics
    valid_scenarios = passed_scenarios + failed_scenarios
    avg_quality = total_quality_score / valid_scenarios if valid_scenarios > 0 else 0.0
    avg_factual = total_factual_score / valid_scenarios if valid_scenarios > 0 else 0.0
    pass_rate = passed_scenarios / total_scenarios if total_scenarios > 0 else 0.0
    production_ready = pass_rate >= PRODUCTION_READY_THRESHOLD

    # Build final report
    report = {
        "verification_run": {
            "timestamp": datetime.now().isoformat(),
            "pass_threshold": PASS_THRESHOLD,
            "production_ready_threshold": PRODUCTION_READY_THRESHOLD,
        },
        "summary": {
            "total_scenarios": total_scenarios,
            "passed": passed_scenarios,
            "failed": failed_scenarios,
            "errors": error_scenarios,
            "pass_rate": f"{pass_rate * 100:.1f}%",
            "avg_quality_score": round(avg_quality, 1),
            "avg_factual_score": round(avg_factual, 1),
            "production_ready": production_ready,
        },
        "phase_results": phase_results,
        "scenario_results": all_results,
        "failing_scenarios": [
            {
                "scenario_num": r["scenario_num"],
                "scenario_name": r["scenario_name"],
                "quality_score": r.get("quality_score", 0),
                "status": r["status"],
            }
            for r in all_results
            if r["status"] in ("FAIL", "ERROR")
        ],
    }

    return report


def generate_markdown_summary(report: dict[str, Any]) -> str:
    """Generate a human-readable markdown summary."""
    summary = report["summary"]
    timestamp = report["verification_run"]["timestamp"]

    md = [
        "# MAPIT Final Verification Report",
        "",
        f"**Generated**: {timestamp}",
        f"**Pass Threshold**: {report['verification_run']['pass_threshold']}/100",
        "",
        "---",
        "",
        "## Production Readiness Status",
        "",
    ]

    if summary["production_ready"]:
        md.append("### PRODUCTION READY")
        md.append("")
        md.append(f"All criteria met. {summary['pass_rate']} of scenarios pass (required: 80%).")
    else:
        md.append("### NOT PRODUCTION READY")
        md.append("")
        md.append(f"Only {summary['pass_rate']} of scenarios pass (required: 80%).")

    md.extend(
        [
            "",
            "---",
            "",
            "## Summary Statistics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Scenarios | {summary['total_scenarios']} |",
            f"| Passed | {summary['passed']} |",
            f"| Failed | {summary['failed']} |",
            f"| Errors | {summary['errors']} |",
            f"| Pass Rate | {summary['pass_rate']} |",
            f"| Average Quality Score | {summary['avg_quality_score']}/100 |",
            f"| Average Factual Score | {summary['avg_factual_score']}% |",
            "",
            "---",
            "",
            "## Phase Results",
            "",
            "| Phase | Passed | Total | Pass Rate | Avg Quality |",
            "|-------|--------|-------|-----------|-------------|",
        ]
    )

    for phase_name, phase_data in report["phase_results"].items():
        phase_short = phase_name.split(":")[1].strip() if ":" in phase_name else phase_name
        md.append(
            f"| {phase_short} | {phase_data['passed']} | {phase_data['total']} | "
            f"{phase_data['pass_rate']} | {phase_data['avg_quality_score']:.1f} |"
        )

    if report["failing_scenarios"]:
        md.extend(
            [
                "",
                "---",
                "",
                "## Failing Scenarios",
                "",
                "| # | Scenario | Score | Status |",
                "|---|----------|-------|--------|",
            ]
        )
        for scenario in report["failing_scenarios"]:
            md.append(
                f"| {scenario['scenario_num']} | {scenario['scenario_name']} | "
                f"{scenario['quality_score']:.1f} | {scenario['status']} |"
            )

    md.extend(
        [
            "",
            "---",
            "",
            "## All Scenario Results",
            "",
            "| # | Scenario | Score | Factual | Status |",
            "|---|----------|-------|---------|--------|",
        ]
    )

    for r in report["scenario_results"]:
        status_emoji = "" if r["status"] == "PASS" else "" if r["status"] == "FAIL" else ""
        md.append(
            f"| {r['scenario_num']} | {r['scenario_name']} | "
            f"{r.get('quality_score', 0):.1f} | {r.get('factual_score', 0):.1f}% | "
            f"{status_emoji} {r['status']} |"
        )

    return "\n".join(md)


async def main():
    """Main entry point."""
    # Run all scenarios
    report = await run_all_scenarios()

    # Save JSON report
    json_path = Path("tests/quality/results/final_verification_report.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nJSON report saved to: {json_path}")

    # Save markdown summary
    md_path = Path("tests/quality/results/FINAL_VERIFICATION_SUMMARY.md")
    md_content = generate_markdown_summary(report)
    with open(md_path, "w") as f:
        f.write(md_content)
    print(f"Markdown summary saved to: {md_path}")

    # Print final summary
    summary = report["summary"]
    print("\n" + "=" * 70)
    print("FINAL VERIFICATION COMPLETE")
    print("=" * 70)
    print(f"Total Scenarios: {summary['total_scenarios']}")
    print(f"Passed: {summary['passed']} ({summary['pass_rate']})")
    print(f"Failed: {summary['failed']}")
    print(f"Errors: {summary['errors']}")
    print(f"Average Quality Score: {summary['avg_quality_score']}/100")
    print(f"Average Factual Score: {summary['avg_factual_score']}%")
    print()
    if summary["production_ready"]:
        print("PRODUCTION READY")
    else:
        print("NOT PRODUCTION READY")
        if report["failing_scenarios"]:
            print("\nFailing scenarios:")
            for s in report["failing_scenarios"]:
                print(f"  - {s['scenario_num']}: {s['scenario_name']} ({s['quality_score']:.1f})")
    print("=" * 70)

    # Exit with appropriate code
    return 0 if summary["production_ready"] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
