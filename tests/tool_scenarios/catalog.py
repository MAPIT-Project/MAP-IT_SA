"""Bounded tool contracts and user questions built from independently read facts.

The catalog imports no application services. Prerequisites are explicit so a
missing graph, embedding key or proposal fixture becomes BLOCKED, never PASS.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ToolCase:
    id: str
    tool: str
    parameters: dict[str, Any]
    oracle_key: str
    check: str
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnswerAssertion:
    kind: str
    value: Any
    label: str = ""
    tolerance: Decimal = Decimal("0")


@dataclass(frozen=True)
class QuestionScenario:
    id: str
    question: str
    expected_tools: tuple[str, ...]
    assertions: tuple[AnswerAssertion, ...]
    requires: tuple[str, ...] = ()
    oracle_keys: tuple[str, ...] = ()


PROPOSAL_TEXT = (
    "The objective is to demonstrate a renewable hydrogen storage system in three French "
    "industrial sites over 36 months. The consortium will compare a validated baseline "
    "with monthly measurements of energy consumption, uptime and safety incidents. "
    "The target is a 20% reduction in energy use and 95% operational availability. "
    "The methodology includes laboratory verification, independent safety review, "
    "pilot installation and a documented evaluation against the baseline. "
    "Work package 1 manages the project and work package 2 validates the technology. "
    "The expected result is a reproducible technical report with measured performance "
    "and an openly available evaluation protocol. The project does not yet have a "
    "confirmed funding award or partners; those must not be invented."
)


def build_cases(facts: dict[str, list[dict]]) -> list[ToolCase]:
    """One explicit contract for every registered V3/V4 tool, without inference."""
    project = (facts.get("reference_project") or [{}])[0]
    organization = (facts.get("reference_organization") or [{}])[0]
    call = (facts.get("reference_call") or [{}])[0]
    pid = str(project.get("project_id", "101137586"))
    org = organization.get("name", "TECHNISCHE UNIVERSITAET MUENCHEN")
    cid = call.get("topic_code", "HORIZON-EIC-2026-AIC-01")
    section = "excellence.objectives"
    cases: list[ToolCase] = []

    def add(tool, parameters, oracle, check, requires=()):
        cases.append(ToolCase(tool, tool, parameters, oracle, check, requires))

    add(
        "get_programme_statistics",
        {"programme": "Cluster 5"},
        "cluster_statistics",
        "programme_statistics",
        ("graph",),
    )
    add(
        "get_country_statistics", {"country": "Germany"}, "country_statistics", "country_statistics"
    )
    add(
        "get_budget_benchmark",
        {"topic_keywords": "hydrogen", "cluster": "CL5"},
        "hydrogen_benchmark",
        "benchmark",
    )
    add(
        "get_consortium_patterns",
        {"topic_keywords": "hydrogen", "cluster": "CL5", "min_projects": 1},
        "hydrogen_consortia",
        "consortia",
    )
    add(
        "analyze_geographic_diversification",
        {"cluster": "CL5", "min_partners": 3, "exclude_widening": True},
        "geographic_coverage",
        "geography",
    )
    add(
        "find_experienced_partners",
        {"topic_keywords": "hydrogen", "min_projects": 2, "limit": 10},
        "experienced_hydrogen_partners",
        "experienced_partners",
    )
    add(
        "get_similar_funded_projects",
        {"description": project.get("title", "hydrogen storage"), "limit": 5},
        "reference_project",
        "semantic_projects",
        ("embeddings",),
    )
    add(
        "analyze_call_history",
        {"topic_pattern": "CLEANH2", "include_projects": True, "expand_scope": False},
        "hydrogen_history",
        "history",
    )
    add(
        "compare_programmes",
        {"programme_a": "Cluster 4", "programme_b": "Cluster 5"},
        "cluster_statistics",
        "comparison",
        ("graph",),
    )
    add(
        "search_documents",
        {
            "query": "Horizon Europe minimum consortium three independent legal entities Member State associated countries",
            "max_results": 10,
        },
        "horizon_consortium_evidence",
        "documents",
        ("embeddings",),
    )
    add("search_funding_calls", {"status": "open", "keywords": ""}, "open_calls", "open_calls")
    add("get_call_details", {"call_id": cid}, "reference_call", "call_details")
    add(
        "search_projects",
        {"keywords": project.get("acronym", "IMAGHyNE"), "limit": 5},
        "reference_project",
        "project_search",
    )
    add("get_project_details", {"project_id": pid}, "reference_project", "project_details")
    add(
        "find_similar_projects",
        {"project_id": pid, "similarity_type": "topic"},
        "topic_neighbors",
        "topic_neighbors",
        ("graph",),
    )
    add(
        "find_semantically_similar_projects",
        {"project_id": pid, "limit": 5},
        "semantic_neighbors",
        "semantic_neighbors",
        ("stored_embeddings",),
    )
    add(
        "find_organization_projects",
        {"organization_name": org},
        "organization_projects",
        "organization_projects",
        ("graph",),
    )
    add("get_project_partners", {"project_id": pid}, "reference_partners", "project_partners")
    add(
        "get_organization_stats",
        {"organization_name": org},
        "reference_organization",
        "organization_statistics",
    )
    add(
        "get_collaboration_network",
        {"organization_name": org},
        "organization_collaborations",
        "collaborations",
        ("graph",),
    )
    add("search_by_cluster", {"cluster": "CL5"}, "cluster_projects", "cluster_projects", ("graph",))
    add(
        "calculate_budget",
        {"action_type": "RIA", "target_budget": 5000000, "duration_months": 36, "num_partners": 5},
        "",
        "budget_arithmetic",
    )
    add(
        "generate_timeline",
        {
            "action_type": "RIA",
            "duration_months": 36,
            "num_partners": 5,
            "project_title": "Synthetic hydrogen demonstration",
        },
        "",
        "timeline",
    )
    add(
        "search_all_programmes",
        {"keywords": "", "status": "open", "limit": 20},
        "open_calls",
        "all_programme_calls",
    )
    add(
        "recommend_programmes",
        {
            "description": "University research on renewable hydrogen production and technology validation",
            "organization_type": "university",
        },
        "",
        "recommendations",
    )
    add("get_programme_info", {"programme": "horizon_europe"}, "", "programme_info")
    add(
        "score_proposal_section",
        {"content": PROPOSAL_TEXT, "section_type": "excellence"},
        "",
        "section_score",
        ("model",),
    )
    add(
        "score_full_proposal",
        {
            "excellence_content": PROPOSAL_TEXT,
            "impact_content": PROPOSAL_TEXT,
            "implementation_content": PROPOSAL_TEXT,
        },
        "",
        "full_score",
        ("model",),
    )
    add("quick_quality_check", {"text": ""}, "", "empty_quality")
    add(
        "validate_budget",
        {"total_cost": 1000000, "eu_contribution": 1100000, "action_type": "RIA"},
        "",
        "invalid_budget",
    )
    add(
        "check_erasmus_eligibility",
        {"org_type": "HEI", "country": "Germany", "action_type": "KA1-HED", "has_eche": True},
        "",
        "eligible",
    )
    add("calculate_erasmus_budget", {"action_type": "JMO"}, "", "erasmus_budget")
    add(
        "search_erasmus_templates",
        {"query": "cooperation partnership minimum three organisations", "top_k": 10},
        "document_evidence",
        "programme_documents",
        ("embeddings",),
    )
    add(
        "check_creative_europe_eligibility",
        {"org_type": "NGO", "country": "Germany", "action_type": "COOP-SMALL", "strand": "CULTURE"},
        "",
        "eligible",
    )
    add(
        "calculate_creative_europe_budget",
        {"action_type": "COOP-SMALL", "requested_amount": 200000, "num_partners": 3},
        "",
        "creative_budget",
    )
    add(
        "search_creative_europe_templates",
        {"query": "European cooperation projects small scale minimum partners", "top_k": 10},
        "document_evidence",
        "programme_documents",
        ("embeddings",),
    )
    add(
        "check_eu4health_eligibility",
        {"org_type": "NGO", "country": "Germany", "action_type": "AG"},
        "",
        "eligible",
    )
    add(
        "search_eu4health_templates",
        {"query": "action grants eligible entities", "top_k": 10},
        "document_evidence",
        "programme_documents",
        ("embeddings",),
    )
    add(
        "check_digital_europe_eligibility",
        {"org_type": "SME", "country": "Germany", "objective": "AI"},
        "",
        "eligible",
    )
    add(
        "check_life_eligibility",
        {"org_type": "NGO", "country": "Germany", "subprogramme": "ENV"},
        "",
        "eligible",
    )
    add(
        "search_life_templates",
        {"query": "standard action projects eligible entities", "top_k": 10},
        "document_evidence",
        "programme_documents",
        ("embeddings",),
    )
    add("show_cached_projects", {}, "reference_project", "cached_projects", ("cached_projects",))
    add(
        "generate_section_draft",
        {"section_id": section, "call_id": cid, "guidance": PROPOSAL_TEXT, "word_target": 150},
        "",
        "draft",
        ("model", "proposal_session", "call_requirements"),
    )
    add("improve_section", {"section_id": section}, "", "improve", ("model", "proposal_session"))
    add(
        "rewrite_section",
        {"section_id": section, "style": "concise"},
        "",
        "rewrite",
        ("model", "proposal_session"),
    )
    add(
        "evaluate_section",
        {"section_id": section, "evaluation_type": "quick"},
        "",
        "evaluate",
        ("model", "proposal_session"),
    )
    add("analyze_gaps", {"section_id": section}, "", "gaps", ("model", "proposal_session"))
    add(
        "check_compliance",
        {"section_id": section, "check_type": "all"},
        "",
        "compliance",
        ("proposal_session", "call_requirements"),
    )
    add(
        "get_suggestions", {"section_id": section}, "", "suggestions", ("model", "proposal_session")
    )
    add("focus_section", {"section_id": section}, "", "focus", ("proposal_session",))
    add(
        "mark_section_status",
        {"section_id": section, "status": "complete"},
        "",
        "status",
        ("proposal_session",),
    )
    add("get_document_overview", {}, "", "overview", ("proposal_session",))
    return cases


def build_scenarios(facts: dict[str, list[dict]]) -> list[QuestionScenario]:
    """Ten questions, with deterministic evidence assertions instead of an AI judge."""
    p = (facts.get("reference_project") or [{}])[0]
    org = (facts.get("reference_organization") or [{}])[0]
    country = (facts.get("country_statistics") or [{}])[0]
    call = (facts.get("reference_call") or [{}])[0]
    pid = str(p.get("project_id", "101137586"))
    cid = call.get("topic_code", "HORIZON-EIC-2026-AIC-01")
    name = org.get("name", "TECHNISCHE UNIVERSITAET MUENCHEN")
    a = AnswerAssertion
    return [
        QuestionScenario(
            "project_facts",
            f"Look up CORDIS project {pid}. Give its acronym, exact EU contribution in euros, total cost, and coordinator. Keep both amounts distinct and cite CORDIS.",
            ("get_project_details",),
            (
                a("text", p.get("acronym", "IMAGHyNE")),
                a("money", p.get("eu_contribution"), "EU contribution", Decimal("0.01")),
                a("money", p.get("total_cost"), "total cost", Decimal("0.01")),
                a("text", p.get("coordinator_name")),
            ),
            oracle_keys=("reference_project",),
        ),
        QuestionScenario(
            "project_consortium",
            f"For CORDIS project {pid}, list its coordinator and the exact number of consortium organisations and countries. Use the complete partner list, not the first page.",
            ("get_project_partners",),
            (
                a("text", p.get("coordinator_name")),
                a("number", p.get("partner_count"), "partners"),
                a("number", p.get("country_count"), "countries"),
            ),
            oracle_keys=("reference_project", "reference_partners"),
        ),
        QuestionScenario(
            "project_search",
            f"Use search_projects to search the funded-project catalogue for the exact acronym {p.get('acronym', 'IMAGHyNE')}. Report its CORDIS ID, full title and exact EU contribution in euros.",
            ("search_projects",),
            (
                a("identifier", pid),
                a("text", p.get("acronym", "IMAGHyNE")),
                a("text", p.get("title")),
                a("money", p.get("eu_contribution"), "EU contribution", Decimal("1")),
            ),
            oracle_keys=("reference_project",),
        ),
        QuestionScenario(
            "organization_statistics",
            f"What is the recorded Horizon Europe project count, coordination count and total organisation funding for {name}? Give full totals, not just the displayed project list.",
            ("get_organization_stats",),
            (
                a("text", name),
                a("number", org.get("project_count"), "project count"),
                a("number", org.get("coordinations"), "coordinations"),
                a("money", org.get("total_funding"), "organisation funding", Decimal("1")),
            ),
            oracle_keys=("reference_organization",),
        ),
        QuestionScenario(
            "country_statistics",
            "How many distinct funded projects include German organisations in the local CORDIS participation data? Give the total recorded German organisation funding in euros. Distinguish organisation participation from project budgets.",
            ("get_country_statistics",),
            (
                a("number", country.get("project_count"), "project count"),
                a(
                    "money",
                    country.get("total_funding"),
                    "German organisation funding",
                    Decimal("1"),
                ),
            ),
            oracle_keys=("country_statistics",),
        ),
        QuestionScenario(
            "expired_call",
            f"Can I still apply for {cid}? State the recorded deadline and status as of today. If a call-level budget is absent, say it is unavailable; do not infer it from programme budgets.",
            ("get_call_details",),
            (
                a("identifier", cid),
                a("text", call.get("effective_status")),
                a("date", call.get("deadline")),
                *([a("unknown_budget", True)] if call.get("budget_total") is None else []),
            ),
            oracle_keys=("reference_call",),
        ),
        QuestionScenario(
            "open_calls",
            "Use search_funding_calls to list the currently open funding calls in our database with their exact identifiers and deadlines. Exclude expired deadlines even when a stored status says open. State when a budget is unknown.",
            ("search_funding_calls",),
            tuple(a("identifier", r["topic_code"]) for r in facts.get("open_calls", [])),
            oracle_keys=("open_calls",),
        ),
        QuestionScenario(
            "planning_arithmetic",
            "Calculate a 36-month Horizon Europe RIA budget with 5 partners and a target total cost of EUR 5,000,000. Give the EU contribution and funding rate. Then validate a separate RIA with EUR 1,000,000 total cost and EUR 1,100,000 requested EU contribution: explain the violation.",
            ("calculate_budget", "validate_budget"),
            (
                a("money", 5000000, "total cost"),
                a("money", 5000000, "EU contribution"),
                a("money", 1000000),
                a("money", 1100000),
                a("text", "100%"),
                a("regex", r"(?i)(exceed|more than|greater than|over.?fund|invalid)"),
            ),
        ),
        QuestionScenario(
            "programme_eligibility",
            "Check whether a German university with ECHE is eligible for Erasmus+ KA1 higher education mobility, a German NGO for LIFE environment projects, and a German SME for Digital Europe AI. State each result and any conditions, using the eligibility tools.",
            (
                "check_erasmus_eligibility",
                "check_life_eligibility",
                "check_digital_europe_eligibility",
            ),
            (
                a("eligible_programme", "Erasmus"),
                a("eligible_programme", "LIFE"),
                a("eligible_programme", "Digital Europe"),
                a("text", "ECHE"),
            ),
        ),
        QuestionScenario(
            "document_grounding",
            "Use search_documents to find the Horizon Europe General Annexes guidance on minimum consortium requirements for a research and innovation action. Quote a short relevant passage, give its document title and stored page, and distinguish the general rule from call-specific exceptions.",
            ("search_documents",),
            (
                a("regex", r"(?i)(three|3).{0,80}(entit|countr|organis)"),
                a("regex", r"(?i)(page|p\.)\s*\d"),
            ),
            requires=("embeddings",),
            oracle_keys=("horizon_consortium_evidence",),
        ),
    ]
