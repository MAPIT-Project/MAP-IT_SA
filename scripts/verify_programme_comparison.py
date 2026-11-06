"""Read-only comparison regression; optional, separately capped real Codex question."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.tool_scenarios.environment import isolated_settings, make_agent
from tests.tool_scenarios.oracles import DockerPsqlReader

QUESTION = (
    "Compare the EIC Accelerator and ERC Advanced Grant regarding success rates and "
    "average funding amounts over the last 3 years. Based on this data, which one is "
    "more suitable for a high-risk deep-tech startup looking to scale?"
)


async def verify(args):
    from app.services.agents.framework.runtime import run_agent_loop
    from app.services.agents.tool_registry import AgentPlan
    from app.services.ai.budget import InferenceBudget
    from app.services.tools.budget_benchmark import BudgetBenchmarkTool
    from app.services.tools.programme_statistics import compare_programmes_execute
    from tests.tool_scenarios.transport import funding_transport

    reader = DockerPsqlReader()
    report = args.report
    report.update(question=QUESTION, checks=[], model_calls_enabled=args.live_question)
    # Independent SQL uses literal scheme/topic membership, not the application's
    # programme resolver. It includes projects without participation rows.
    cohorts = {
        "EIC Accelerator": """(p."fundingScheme" IN
            ('EIC-ACC', 'HORIZON-EIC-ACC', 'HORIZON-EIC-ACC-BF',
             'HORIZON-EIC-ACC-GO', 'HORIZON-EIC-ACC-EQ')
            OR p.topics LIKE '%EIC-%-ACCELERATOR%')""",
        "ERC Advanced Grant": """(p."fundingScheme" IN ('ERC-ADG', 'HORIZON-ERC-ADG')
            OR p.topics LIKE '%ERC-%-ADG%')""",
    }
    source = {}
    for name, predicate in cohorts.items():
        source[name] = reader(f"""SELECT COUNT(*) AS projects,
            AVG(p."ecMaxContribution") AS mean_eu_contribution
            FROM projects p WHERE p."frameworkProgramme" = 'HORIZON'
            AND {predicate} AND p."ecMaxContribution" > 0
            AND EXTRACT(YEAR FROM p."startDate") BETWEEN 2023 AND 2025""")[0]
    report["source"] = source
    budget = InferenceBudget(
        max_requests=4 if args.live_question else 0,
        allowed_providers={"codex"},
        max_reported_tokens=180000,
    )
    args.budget = budget
    with funding_transport(reader), budget:
        for name, expected in source.items():
            result = await asyncio.to_thread(
                BudgetBenchmarkTool().get_benchmark,
                programme=name,
                year_from=2023,
                year_to=2025,
            )
            assert result["success"], result
            assert result["statistics"]["projects_analyzed"] == int(expected["projects"])
            assert int(expected["projects"]) > 0, f"Missing known {name} cohort"
            actual = result["statistics"]["total_eu_contribution"]["average"]
            assert abs(actual - float(expected["mean_eu_contribution"])) <= 1
            report["checks"].append({"programme": name, "passed": True, "result": result})
        published = await compare_programmes_execute(
            "EIC Accelerator",
            "ERC Advanced Grant",
            year_from=2023,
            year_to=2025,
        )
        assert published["success"]
        report["published"] = published
        if args.live_question:
            owner = make_agent()
            plan = AgentPlan(QUESTION, "complex", [])
            events = []
            report["events"] = events

            async def emit(event):
                if event.get("type") in {"tool_call", "tool_result", "error"}:
                    events.append(event)

            await asyncio.wait_for(run_agent_loop(owner, QUESTION, "", plan, emit), 480)
            report.update(answer=plan.final_answer, error=plan.error, events=events)
            assert not plan.error, plan.error
            assert plan.final_answer
            # Keep evidence review inspectable. No second model grades the answer.
            assert any(
                event.get("tool_name") in {"compare_programmes", "get_programme_statistics"}
                for event in events
                if event.get("type") == "tool_call"
            )
    report["usage"] = budget.snapshot()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-question", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.report = {}
    try:
        with isolated_settings():
            report = asyncio.run(verify(args))
    except Exception as exc:
        args.report["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        raise
    finally:
        if hasattr(args, "budget"):
            args.report["usage"] = args.budget.snapshot()
        args.output.write_text(json.dumps(args.report, indent=2, default=str) + "\n")
    print(json.dumps({"checks": len(report["checks"]), "usage": report["usage"]}))


if __name__ == "__main__":
    main()
