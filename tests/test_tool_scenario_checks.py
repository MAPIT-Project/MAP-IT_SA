"""Synthetic counterexamples prove scenario checks reject wrong facts, without inference."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from tests.tool_scenarios.catalog import (
    AnswerAssertion,
    QuestionScenario,
    ToolCase,
    build_cases,
    build_scenarios,
)
from tests.tool_scenarios.checks import validate_answer, validate_tool


@pytest.fixture
def facts():
    return {
        "catalog_counts": [{"database_date": "2026-11-04"}],
        "reference_project": [
            {
                "project_id": "101137586",
                "acronym": "IMAGHyNE",
                "title": "Synthetic hydrogen valley",
                "eu_contribution": Decimal("19996911.75"),
                "total_cost": Decimal("200255979.99"),
                "coordinator_name": "REGION AUVERGNE RHONE ALPES",
                "country_count": 5,
                "partner_count": 42,
            }
        ],
        "reference_partners": [
            {
                "name": "Synthetic Coordinator",
                "country": "FR",
                "role": "coordinator",
                "contribution": 100,
            }
        ],
        "reference_organization": [
            {
                "name": "TECHNISCHE UNIVERSITAET MUENCHEN",
                "project_count": 219,
                "coordinations": 20,
                "total_funding": 3000000,
            }
        ],
        "country_statistics": [
            {"country": "DE", "project_count": 5193, "total_funding": 6256269845}
        ],
        "reference_call": [
            {
                "topic_code": "HORIZON-EIC-2026-AIC-01",
                "title": "Synthetic call",
                "deadline": "2026-02-26",
                "effective_status": "closed",
                "budget_total": None,
            }
        ],
        "open_calls": [{"topic_code": "HORIZON-EIC-2026-ACCELERATOR-01", "deadline": "2026-12-17"}],
    }


def case(facts, name):
    return next(c for c in build_cases(facts) if c.tool == name)


def project_result(facts):
    source = facts["reference_project"][0]
    return {
        "project_id": source["project_id"],
        "acronym": source["acronym"],
        "ec_contribution": source["eu_contribution"],
        "total_cost": source["total_cost"],
        "coordinator": {"name": source["coordinator_name"]},
        "country_count": 5,
    }


def test_catalog_has_one_contract_for_each_registered_tool(facts):
    # Read only registry definitions: no model or database construction.
    from app.services.agents.proposal_aware_agent import ProposalAwareAgent

    agent = ProposalAwareAgent.__new__(ProposalAwareAgent)
    agent.tools = {}
    agent._init_tools()
    agent._init_proposal_tools()
    cases = build_cases(facts)
    assert len(cases) == 52
    assert len({c.id for c in cases}) == 52
    assert {c.tool for c in cases} == set(agent.tools)
    from app.services.agents.framework.tool_schemas import input_model_for

    for contract in cases:
        input_model_for(agent.tools[contract.tool]).model_validate(contract.parameters)
    assert len(build_scenarios(facts)) == 10


def test_exact_project_result_passes_but_swapped_amounts_fail(facts):
    result = project_result(facts)
    assert validate_tool(case(facts, "get_project_details"), result, facts) == []
    result["total_cost"], result["ec_contribution"] = (
        result["ec_contribution"],
        result["total_cost"],
    )
    failures = validate_tool(case(facts, "get_project_details"), result, facts)
    assert any("EU contribution" in e for e in failures)
    assert any("total cost" in e for e in failures)


@pytest.mark.parametrize(
    "result",
    [
        {},
        {"success": True},
        {"success": False},
        {"error": "missing"},
        {"score": 4, "note": "Placeholder evaluation"},
    ],
)
def test_empty_or_placeholder_results_never_pass(facts, result):
    assert validate_tool(case(facts, "get_project_details"), result, facts)


def test_missing_source_evidence_cannot_pass(facts):
    assert (
        "Missing source evidence"
        in validate_tool(case(facts, "get_project_details"), project_result(facts), {})[0]
    )


def test_expired_call_with_open_status_fails(facts):
    result = {
        "call_id": "HORIZON-EIC-2026-AIC-01",
        "title": "Synthetic call",
        "deadline": "26 February 2026",
        "status": "open",
        "budget": None,
    }
    assert any(
        "effective call status" in error
        for error in validate_tool(case(facts, "get_call_details"), result, facts)
    )
    result["status"] = "closed"
    assert validate_tool(case(facts, "get_call_details"), result, facts) == []
    result["budget"] = "EUR 200 million"
    assert any(
        "budget" in error for error in validate_tool(case(facts, "get_call_details"), result, facts)
    )


def test_incomplete_partner_list_fails_even_with_claimed_total(facts):
    result = {"partners": [], "partner_count": 1}
    assert any(
        "missing" in error
        for error in validate_tool(case(facts, "get_project_partners"), result, facts)
    )


def test_budget_violation_requires_funding_rate_issue(facts):
    budget = case(facts, "validate_budget")
    assert validate_tool(budget, {"valid": True, "issues": []}, facts)
    assert (
        validate_tool(budget, {"valid": False, "issues": [{"category": "funding_rate"}]}, facts)
        == []
    )


def test_creative_cofinancing_arithmetic(facts):
    result = {
        "breakdown": {
            "eu_grant": 200000,
            "co_financing": 50000,
            "total_budget": 250000,
            "funding_rate_percent": 80,
        }
    }
    assert validate_tool(case(facts, "calculate_creative_europe_budget"), result, facts) == []
    result["breakdown"]["co_financing"] = 0
    assert validate_tool(case(facts, "calculate_creative_europe_budget"), result, facts)


def test_correct_answer_cannot_hide_empty_tool_output(facts):
    scenario = build_scenarios(facts)[0]
    answer = "IMAGHyNE\nEU contribution: EUR 19,996,911.75\nTotal cost: EUR 200,255,979.99\nREGION AUVERGNE RHONE ALPES"
    assert validate_answer(
        scenario,
        answer,
        [SimpleNamespace(tool_name="get_project_details", success=True, result={})],
        facts,
    )
    calls = [
        SimpleNamespace(tool_name="get_project_details", success=True, result=project_result(facts))
    ]
    assert validate_answer(scenario, answer, calls, facts) == []
    swapped = (
        answer.replace("19,996,911.75", "SWAP")
        .replace("200,255,979.99", "19,996,911.75")
        .replace("SWAP", "200,255,979.99")
    )
    assert validate_answer(scenario, swapped, calls, facts)


def test_money_assertion_rejects_wrong_units():
    scenario = QuestionScenario(
        "money", "Question", (), (AnswerAssertion("money", 19996911.75, tolerance=Decimal("0.01")),)
    )
    assert validate_answer(scenario, "EU funding: EUR 19.99691175 million", [], {}) == []
    assert validate_answer(scenario, "EU funding: EUR 19.99691175 billion", [], {})


def test_unknown_budget_assertion_rejects_invented_amount():
    scenario = QuestionScenario(
        "unknown", "Question", (), (AnswerAssertion("unknown_budget", True),)
    )
    assert validate_answer(scenario, "The call budget is not recorded.", [], {}) == []
    assert validate_answer(scenario, "The budget is unknown, approximately EUR 10 million.", [], {})


def test_identifier_assertion_has_boundaries():
    scenario = QuestionScenario("id", "Question", (), (AnswerAssertion("identifier", "101137586"),))
    assert validate_answer(scenario, "CORDIS 101137586.", [], {}) == []
    assert validate_answer(scenario, "CORDIS 1011375860.", [], {})


def test_unknown_check_fails_closed():
    unknown = ToolCase("unknown", "unknown", {}, "", "future_check")
    assert validate_tool(unknown, {"success": True}, {}) == [
        "No deterministic validator is implemented for future_check"
    ]


def test_document_citations_must_match_independent_chunk_page_and_title():
    contract = ToolCase("doc", "search_documents", {}, "horizon_consortium_evidence", "documents")
    source = {
        "chunk_id": "chunk-1",
        "document_id": "doc-1",
        "title": "Horizon guidance",
        "page_number": 31,
        "content": "At least three independent legal entities are required.",
    }
    facts = {"horizon_consortium_evidence": [source], "retrieved_document_evidence": [source]}
    result = {"documents": [{**source}]}
    assert validate_tool(contract, result, facts) == []
    result["documents"][0]["page_number"] = 99
    assert any("page differs" in error for error in validate_tool(contract, result, facts))
    result["documents"][0] = {
        **source,
        "content": "Invented eligibility rule with no source support.",
    }
    assert any("not present" in error for error in validate_tool(contract, result, facts))


def test_a_successful_corrected_tool_call_can_recover_from_an_earlier_wrong_result(facts):
    scenario = build_scenarios(facts)[0]
    answer = "IMAGHyNE\nEU contribution: EUR 19,996,911.75\nTotal cost: EUR 200,255,979.99\nREGION AUVERGNE RHONE ALPES"
    calls = [
        SimpleNamespace(tool_name="get_project_details", success=True, result={}),
        SimpleNamespace(
            tool_name="get_project_details", success=True, result=project_result(facts)
        ),
    ]
    assert validate_answer(scenario, answer, calls, facts) == []


def test_programme_names_alone_do_not_prove_correct_eligibility_results():
    scenario = QuestionScenario(
        "eligibility", "Question", (), (AnswerAssertion("eligible_programme", "LIFE"),)
    )
    assert (
        validate_answer(scenario, "LIFE: eligible, subject to the stated call conditions.", [], {})
        == []
    )
    assert validate_answer(scenario, "LIFE: not eligible.", [], {})
    assert validate_answer(scenario, "LIFE programme information.", [], {})


def test_document_answer_requires_a_supported_quote_and_real_page():
    from tests.tool_scenarios.checks import _document_answer_errors

    calls = [
        SimpleNamespace(
            tool_name="search_documents",
            result={
                "documents": [
                    {
                        "content": "At least three independent legal entities are required.",
                        "title": "Horizon Programme General Annexes",
                        "page_number": 12,
                    }
                ]
            },
        )
    ]
    answer = "Horizon Programme General Annexes, page 12.\n> At least three independent legal entities are required."
    assert _document_answer_errors(answer, calls) == []
    assert _document_answer_errors(answer.replace("page 12", "page 99"), calls)
    assert _document_answer_errors(answer.replace("three", "five"), calls)
