"""Bounded tool evaluation. Default: inspect source evidence, make zero model calls."""

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.tool_scenarios.environment import isolated_settings, make_agent
from tests.tool_scenarios.oracles import DockerPsqlReader, discover_ground_truth


def checkpoint(args, report, budget):
    report["usage"] = budget.snapshot()
    temporary = args.output.with_suffix(args.output.suffix + ".partial")
    temporary.write_text(json.dumps(report, default=str, indent=2))
    temporary.replace(args.output)


def selected_contracts(cases, scenarios, args):
    if args.case:
        return [case for case in cases if case.id in args.case]
    if args.mode == "questions":
        required = {tool for scenario in scenarios for tool in scenario.expected_tools}
        return [case for case in cases if case.tool in required]
    return cases


def verify_document_sources(reader, result, facts):
    """Resolve returned IDs against stored source rows, not the tool's own prose."""
    if not isinstance(result, dict):
        return
    identifiers = []
    for doc in result.get("documents", []):
        try:
            identifiers.append(str(UUID(str(doc.get("chunk_id")))))
        except (ValueError, TypeError, AttributeError):
            continue
    if not identifiers:
        return
    from tests.tool_scenarios.transport import bind_query

    sql = bind_query(
        """
        SELECT c.id::text AS chunk_id,d.id::text AS document_id,d.title,c.page_number,
          left(c.content,12000) AS content
        FROM document_chunks c JOIN horizon_documents d ON d.id=c.document_id
        WHERE c.id::text = ANY(%s) LIMIT 100
    """,
        [identifiers[:100]],
    )
    rows = reader(sql)
    previous = facts.setdefault("retrieved_document_evidence", [])
    previous.extend(row for row in rows if row not in previous)


def provider_failed(plan):
    """Do not spend the next scenario's allowance after a provider failure."""
    return bool(plan.error and str(plan.error).startswith("Codex"))


def usage_delta(before, after):
    return {
        key: after.get(key, 0) - before.get(key, 0)
        for key in (
            "attempted",
            "completed",
            "failed",
            "cancelled",
            "unknown_usage_requests",
            "reported_tokens",
        )
    }


async def evaluate(args):
    from app.services.agents.framework.runtime import run_agent_loop
    from app.services.agents.framework.tool_schemas import input_model_for
    from app.services.agents.tool_registry import AgentPlan
    from app.services.ai.budget import InferenceBudget, InferenceBudgetError
    from tests.tool_scenarios.catalog import build_cases, build_scenarios
    from tests.tool_scenarios.checks import validate_answer, validate_tool
    from tests.tool_scenarios.embeddings import EmbeddingAllowance, EmbeddingLimitExceeded
    from tests.tool_scenarios.transport import funding_transport

    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "mode": args.mode,
        "provider": "codex",
        "requested_model": args.model,
        "effort": args.effort,
        "transport": "real funding SELECTs over read-only psql; no HTTP/storage/graph/embedding",
        "checks": [],
        "questions": [],
        "prerequisites": {},
    }
    reader = DockerPsqlReader(args.container)
    facts = await asyncio.to_thread(discover_ground_truth, reader)
    report["source_counts"] = facts.get("catalog_counts", [])
    report["evidence"] = facts
    cases, scenarios = build_cases(facts), build_scenarios(facts)
    selected_scenarios = [
        case for case in scenarios if not args.scenario or case.id in args.scenario
    ]
    selected_cases = selected_contracts(cases, selected_scenarios, args)
    report["planned"] = {
        "tool_checks": len(selected_cases),
        "questions": len(selected_scenarios) if args.mode == "questions" else 0,
    }
    known_cases, known_scenarios = {c.id for c in cases}, {c.id for c in scenarios}
    if set(args.case or []) - known_cases or set(args.scenario or []) - known_scenarios:
        raise ValueError("Unknown case/scenario identifier")
    if args.mode == "plan":
        report.update(
            cases=[{"id": c.id, "tool": c.tool, "requires": c.requires} for c in cases],
            scenarios=[
                {
                    "id": c.id,
                    "question": c.question,
                    "tools": c.expected_tools,
                    "requires": c.requires,
                }
                for c in scenarios
            ],
            usage={"attempts": 0},
        )
        return report
    capability = {"proposal_session", "cached_projects"}
    if (facts.get("catalog_counts") or [{}])[0].get("embedded_projects", 0):
        capability.add("stored_embeddings")
    if args.include_model_tools:
        capability.add("model")
    embeddings = EmbeddingAllowance(getattr(args, "max_embedding_requests", 0))
    allow_embeddings = getattr(args, "allow_embeddings", False)
    if allow_embeddings:
        capability.add("embeddings")
        report["transport"] = (
            "real funding SELECTs/search RPCs over read-only psql; capped Google embeddings; no HTTP/storage/graph"
        )
    budget = InferenceBudget(
        max_requests=args.max_requests
        if args.mode == "questions" or args.include_model_tools
        else 0,
        allowed_providers={"codex"},
        max_reported_tokens=args.max_reported_tokens,
    )
    try:
        with (
            budget,
            funding_transport(reader, embedding_allowance=embeddings if allow_embeddings else None),
        ):
            research = make_agent(facts=facts)
            proposal = make_agent(proposal=True, facts=facts)
            registry = set(proposal.tools)
            covered = {case.tool for case in cases}
            if registry != covered:
                raise ValueError(
                    f"Tool coverage mismatch: missing={sorted(registry-covered)}, extra={sorted(covered-registry)}"
                )
            for case in selected_cases:
                entry = {"id": case.id, "tool": case.tool}
                missing = set(case.requires) - capability
                if case.oracle_key and not facts.get(case.oracle_key):
                    missing.add(f"source:{case.oracle_key}")
                if missing:
                    entry.update(status="blocked", missing=sorted(missing))
                else:
                    owner = (
                        proposal if case.tool in proposal._get_proposal_tool_names() else research
                    )
                    try:
                        parameters = (
                            input_model_for(owner.tools[case.tool])
                            .model_validate(case.parameters)
                            .model_dump(exclude_none=True, exclude_unset=True)
                        )
                        if owner is proposal:
                            result = await asyncio.wait_for(
                                owner._execute_proposal_tool(case.tool, parameters), 120
                            )
                        else:
                            result = await asyncio.wait_for(
                                owner._execute_single_tool(case.tool, parameters), 60
                            )
                        budget.raise_if_stopped()
                        embeddings.raise_if_stopped()
                        if case.tool == "search_documents":
                            await asyncio.to_thread(verify_document_sources, reader, result, facts)
                        errors = validate_tool(case, result, facts)
                        if owner is proposal and case.tool == "focus_section":
                            if (
                                owner.session_manager.session.active_section_id
                                != parameters["section_id"]
                            ):
                                errors.append("Actual proposal session focus did not change")
                        if owner is proposal and case.tool == "mark_section_status":
                            section = owner.session_manager.session.document.get_section(
                                parameters["section_id"]
                            )
                            if section is None or section.status.value != parameters["status"]:
                                errors.append("Actual proposal section status did not change")
                        entry.update(status="failed" if errors else "passed", errors=errors)
                        entry["result"] = result
                    except (InferenceBudgetError, EmbeddingLimitExceeded):
                        raise
                    except Exception as exc:
                        entry.update(status="failed", errors=[type(exc).__name__])
                report["checks"].append(entry)
                report["embedding_usage"] = embeddings.snapshot()
                checkpoint(args, report, budget)
            if args.mode == "questions":
                capability.add("model")
                for index, scenario in enumerate(selected_scenarios):
                    entry = {"id": scenario.id, "question": scenario.question}
                    usage_before = budget.snapshot()
                    missing = set(scenario.requires) - capability
                    missing.update(
                        f"source:{key}" for key in scenario.oracle_keys if not facts.get(key)
                    )
                    required_cases = [
                        c for c in report["checks"] if c["tool"] in scenario.expected_tools
                    ]
                    missing.update(
                        f"preflight:{tool}"
                        for tool in scenario.expected_tools
                        if not any(c["tool"] == tool for c in required_cases)
                    )
                    if missing or any(c["status"] != "passed" for c in required_cases):
                        entry.update(
                            status="blocked",
                            missing=sorted(missing),
                            reason="Required direct tool check or capability unavailable",
                        )
                    else:
                        owner = (
                            proposal
                            if any(
                                t in proposal._get_proposal_tool_names()
                                for t in scenario.expected_tools
                            )
                            else research
                        )
                        plan = AgentPlan(scenario.question, "simple", [])
                        try:
                            await run_agent_loop(
                                owner,
                                scenario.question,
                                "",
                                plan,
                                proposal_context=owner._current_proposal_context
                                if owner is proposal
                                else "",
                            )
                            budget.raise_if_stopped()
                            embeddings.raise_if_stopped()
                            calls = [
                                call for step in plan.reasoning_steps for call in step.tool_calls
                            ]
                            for call in calls:
                                if call.tool_name == "search_documents" and call.success:
                                    await asyncio.to_thread(
                                        verify_document_sources, reader, call.result, facts
                                    )
                            errors = validate_answer(
                                scenario, plan.final_answer or "", calls, facts
                            )
                            if plan.error:
                                errors.append(plan.error)
                            entry.update(
                                status="failed" if errors else "passed",
                                errors=errors,
                                answer=plan.final_answer,
                                tools=[c.tool_name for c in calls],
                                tool_calls=[
                                    {
                                        "tool_name": c.tool_name,
                                        "parameters": c.parameters,
                                        "success": c.success,
                                        "result": c.result,
                                    }
                                    for c in calls
                                ],
                            )
                            if provider_failed(plan):
                                entry["failure_kind"] = "provider_unavailable"
                        except (InferenceBudgetError, EmbeddingLimitExceeded) as exc:
                            entry.update(
                                status="blocked",
                                reason=str(exc),
                                tool_calls=[
                                    {
                                        "tool_name": c.tool_name,
                                        "parameters": c.parameters,
                                        "success": c.success,
                                        "result": c.result,
                                    }
                                    for step in plan.reasoning_steps
                                    for c in step.tool_calls
                                ],
                            )
                            report["questions"].append(entry)
                            report["questions"].extend(
                                {
                                    "id": remaining.id,
                                    "status": "blocked",
                                    "reason": "Not attempted after evaluation budget stopped",
                                }
                                for remaining in selected_scenarios[index + 1 :]
                            )
                            raise
                        except Exception as exc:
                            entry.update(status="failed", errors=[type(exc).__name__])
                    entry["usage"] = usage_delta(usage_before, budget.snapshot())
                    report["questions"].append(entry)
                    report["embedding_usage"] = embeddings.snapshot()
                    checkpoint(args, report, budget)
                    if entry.get("failure_kind") == "provider_unavailable":
                        report["stopped"] = (
                            "Provider failed; remaining scenarios were not attempted"
                        )
                        report["questions"].extend(
                            {
                                "id": remaining.id,
                                "question": remaining.question,
                                "status": "blocked",
                                "reason": "Not attempted after provider failure",
                            }
                            for remaining in selected_scenarios[index + 1 :]
                        )
                        break
    except (InferenceBudgetError, EmbeddingLimitExceeded) as exc:
        report["stopped"] = str(exc)
    finally:
        report["usage"] = budget.snapshot()
        report["embedding_usage"] = embeddings.snapshot()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("plan", "contracts", "questions"), default="plan")
    parser.add_argument("--container", default="supabase_db_supabase_cli")
    parser.add_argument("--max-requests", type=int, default=30)
    parser.add_argument("--max-reported-tokens", type=int)
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--case", action="append")
    parser.add_argument("--scenario", action="append")
    parser.add_argument("--include-model-tools", action="store_true")
    parser.add_argument("--allow-embeddings", action="store_true")
    parser.add_argument("--runtime-env-file", type=Path)
    parser.add_argument("--max-embedding-requests", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("/tmp/mapit-tool-evaluation.json"))
    args = parser.parse_args()
    if args.allow_embeddings != bool(args.runtime_env_file):
        parser.error("--allow-embeddings and --runtime-env-file must be supplied together")
    logging.basicConfig(level=logging.ERROR)
    with isolated_settings(args.model, args.effort, embedding_env_file=args.runtime_env_file):
        try:
            report = asyncio.run(evaluate(args))
        except Exception as exc:
            report = {"mode": args.mode, "status": "blocked", "error_type": type(exc).__name__}
    args.output.write_text(json.dumps(report, default=str, indent=2))
    statuses = [c["status"] for c in report.get("checks", []) + report.get("questions", [])]
    print(
        json.dumps(
            {
                "report": str(args.output),
                "passed": statuses.count("passed"),
                "failed": statuses.count("failed"),
                "blocked": statuses.count("blocked"),
                "tool_checks": {
                    status: sum(c["status"] == status for c in report.get("checks", []))
                    for status in ("passed", "failed", "blocked")
                },
                "questions": {
                    status: sum(c["status"] == status for c in report.get("questions", []))
                    for status in ("passed", "failed", "blocked")
                },
                "usage": report.get("usage"),
                "embedding_usage": report.get("embedding_usage"),
                "error_type": report.get("error_type"),
            }
        )
    )
    if report.get("error_type") or report.get("stopped") or "failed" in statuses:
        return 1
    return 2 if "blocked" in statuses else 0


if __name__ == "__main__":
    raise SystemExit(main())
