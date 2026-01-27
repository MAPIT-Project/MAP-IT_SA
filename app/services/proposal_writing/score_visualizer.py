"""
Score Visualization Helpers

Generate visual representations of evaluation scores.
"""

from typing import Any


def generate_score_bar(score: float, max_score: float = 5.0) -> str:
    """Generate a text-based score bar."""
    filled = int((score / max_score) * 10)
    empty = 10 - filled

    bar = "=" * filled + "-" * empty
    percentage = (score / max_score) * 100

    return f"[{bar}] {score:.1f}/{max_score:.0f} ({percentage:.0f}%)"


def generate_score_summary(evaluation_result: dict[str, Any]) -> str:
    """Generate a formatted score summary."""
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("EVALUATION SUMMARY")
    lines.append("=" * 60)
    lines.append("")

    # Total score
    total = evaluation_result.get("total_score", 0)
    threshold = evaluation_result.get("threshold", 10)
    status = "ABOVE THRESHOLD" if total >= threshold else "BELOW THRESHOLD"
    status_marker = "[PASS]" if total >= threshold else "[FAIL]"

    lines.append(f"Total Score: {total:.1f}/15 {status_marker} {status}")
    lines.append(generate_score_bar(total, 15))
    lines.append("")

    # Section scores
    section_scores = evaluation_result.get("section_scores", {})

    lines.append("Section Breakdown:")
    for section, score in section_scores.items():
        status_marker = "[OK]" if score >= 3 else "[!]" if score >= 2 else "[X]"
        lines.append(f"  {status_marker} {section.title()}: {generate_score_bar(score, 5)}")

    lines.append("")

    # Funding probability
    prob = evaluation_result.get("funding_probability", 0)
    prob_bar = "=" * int(prob * 10) + "-" * (10 - int(prob * 10))
    lines.append(f"Funding Probability: [{prob_bar}] {prob*100:.0f}%")

    lines.append("")
    lines.append("-" * 60)

    # Assessment
    lines.append("Assessment:")
    lines.append(evaluation_result.get("overall_assessment", ""))

    lines.append("")
    lines.append("-" * 60)

    # Recommendation
    lines.append("Next Steps:")
    lines.append(f"-> {evaluation_result.get('recommendation', '')}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def generate_criterion_table(criterion_scores: list[dict]) -> str:
    """Generate a table of criterion scores."""
    lines = []
    lines.append("| Criterion | Score | Status |")
    lines.append("|-----------|-------|--------|")

    for cs in criterion_scores:
        score = cs.get("score", 0)
        if score >= 4:
            status = "Strong"
        elif score >= 3:
            status = "Acceptable"
        else:
            status = "Needs Work"

        criterion_text = cs.get("criterion", "")
        criterion_short = criterion_text[:40] + "..." if len(criterion_text) > 40 else criterion_text
        lines.append(f"| {criterion_short} | {score:.1f} | {status} |")

    return "\n".join(lines)


def generate_section_report(evaluation_result: Any) -> str:
    """Generate a detailed report for a single section evaluation."""
    lines = []

    lines.append("=" * 60)
    lines.append(f"SECTION EVALUATION: {evaluation_result.section_type.upper()}")
    lines.append("=" * 60)
    lines.append("")

    # Overall score
    score = evaluation_result.overall_score
    status = evaluation_result.threshold_status.upper()
    lines.append(f"Overall Score: {score:.1f}/5 [{status}]")
    lines.append(generate_score_bar(score, 5))
    lines.append("")

    # ESR Summary
    lines.append("Evaluator Summary (ESR-style):")
    lines.append("-" * 40)
    lines.append(evaluation_result.esr_summary)
    lines.append("")

    # Criterion breakdown
    if evaluation_result.criterion_scores:
        lines.append("Criterion Breakdown:")
        lines.append("-" * 40)
        for cs in evaluation_result.criterion_scores:
            status_marker = "[OK]" if cs.score >= 3 else "[!]"
            lines.append(f"{status_marker} {cs.criterion}")
            lines.append(f"    Score: {cs.score:.1f}/5")
            if cs.justification:
                lines.append(f"    Reason: {cs.justification}")
            if cs.improvement_for_half_point:
                lines.append(f"    To improve: {cs.improvement_for_half_point}")
            lines.append("")

    # Strengths
    if evaluation_result.strengths:
        lines.append("Strengths:")
        for s in evaluation_result.strengths:
            lines.append(f"  + {s}")
        lines.append("")

    # Weaknesses
    if evaluation_result.weaknesses:
        lines.append("Weaknesses:")
        for w in evaluation_result.weaknesses:
            lines.append(f"  - {w}")
        lines.append("")

    # Top improvements
    if evaluation_result.top_improvements:
        lines.append("Top Improvements (ordered by impact):")
        for i, imp in enumerate(evaluation_result.top_improvements, 1):
            improvement_text = imp.get("improvement", str(imp))
            score_increase = imp.get("expected_score_increase", "N/A")
            lines.append(f"  {i}. {improvement_text}")
            if score_increase != "N/A":
                lines.append(f"     Expected score increase: +{score_increase}")
        lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)


def generate_comparison_chart_data(
    current_scores: dict[str, float],
    target_scores: dict[str, float] = None
) -> dict[str, Any]:
    """Generate data for a comparison chart (for frontend visualization)."""
    if target_scores is None:
        target_scores = {k: 4.0 for k in current_scores}

    return {
        "labels": list(current_scores.keys()),
        "datasets": [
            {
                "label": "Current Score",
                "data": list(current_scores.values()),
                "backgroundColor": "rgba(59, 130, 246, 0.5)",
                "borderColor": "rgb(59, 130, 246)",
            },
            {
                "label": "Target Score",
                "data": list(target_scores.values()),
                "backgroundColor": "rgba(16, 185, 129, 0.5)",
                "borderColor": "rgb(16, 185, 129)",
            }
        ]
    }


def generate_funding_probability_gauge(probability: float) -> dict[str, Any]:
    """Generate data for a funding probability gauge (for frontend visualization)."""
    # Determine color based on probability
    if probability >= 0.6:
        color = "#10b981"  # Green
        status = "Good Chance"
    elif probability >= 0.3:
        color = "#f59e0b"  # Yellow/Orange
        status = "Moderate Chance"
    else:
        color = "#ef4444"  # Red
        status = "Low Chance"

    return {
        "value": probability * 100,
        "min": 0,
        "max": 100,
        "color": color,
        "status": status,
        "threshold_marker": 60  # Typical "good chance" threshold
    }


def format_improvement_priority_list(
    improvements: list[dict[str, Any]],
    max_items: int = 5
) -> str:
    """Format improvements as a prioritized list."""
    lines = []
    lines.append("Priority Improvements:")
    lines.append("")

    # Sort by expected score increase
    sorted_improvements = sorted(
        improvements,
        key=lambda x: x.get("expected_score_increase", 0),
        reverse=True
    )[:max_items]

    for i, imp in enumerate(sorted_improvements, 1):
        improvement_text = imp.get("improvement", str(imp))
        score_increase = imp.get("expected_score_increase", 0)

        priority = "HIGH" if score_increase >= 0.5 else "MEDIUM" if score_increase >= 0.25 else "LOW"

        lines.append(f"{i}. [{priority}] {improvement_text}")
        if score_increase:
            lines.append(f"   Expected gain: +{score_increase:.1f} points")
        lines.append("")

    return "\n".join(lines)
