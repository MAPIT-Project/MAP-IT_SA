"""Public activity summaries derived from validated calls and actual tool outcomes.

No model reasoning, document bodies or extra generation requests are used here.
"""

import re

_ACTIONS = {
    "search_documents": ("Searching official documents", ("query",)),
    "search_funding_calls": ("Searching funding calls", ("keywords", "status", "cluster")),
    "get_call_details": ("Checking funding call details", ("call_id",)),
    "search_projects": ("Searching funded projects", ("keywords", "country")),
    "get_project_details": ("Looking up project details", ("project_id",)),
    "get_project_partners": ("Retrieving the project's partners", ("project_id",)),
    "get_organization_stats": ("Checking organization statistics", ("organization_name",)),
    "find_organization_projects": ("Looking up an organization's projects", ("organization_name",)),
    "get_collaboration_network": ("Checking collaboration links", ("organization_name",)),
    "find_similar_projects": ("Finding related funded projects", ("project_id", "similarity_type")),
    "find_semantically_similar_projects": ("Comparing project objectives", ("project_id",)),
    "search_by_cluster": ("Searching projects in the research cluster", ("cluster",)),
    "get_programme_statistics": ("Checking programme statistics", ("programme", "metric")),
    "get_country_statistics": ("Checking country participation and funding", ("country",)),
    "compare_programmes": ("Comparing funding programmes", ("programme_a", "programme_b")),
    "get_budget_benchmark": (
        "Checking budgets of funded projects",
        ("topic_keywords", "cluster", "action_type"),
    ),
    "get_consortium_patterns": (
        "Checking consortium composition patterns",
        ("topic_keywords", "cluster"),
    ),
    "find_experienced_partners": (
        "Searching for experienced partners",
        ("topic_keywords", "country", "organization_type"),
    ),
    "get_similar_funded_projects": (
        "Searching funded projects by semantic similarity",
        ("cluster",),
    ),
    "analyze_call_history": ("Checking historical funding patterns", ("topic_pattern", "cluster")),
    "analyze_geographic_diversification": (
        "Checking the consortium's geographic diversity",
        ("cluster",),
    ),
    "show_cached_projects": ("Retrieving the next page of previously found projects", ()),
    "calculate_budget": ("Calculating the proposal budget", ("action_type", "num_partners")),
    "generate_timeline": ("Building a project timeline", ("duration_months",)),
    "search_all_programmes": ("Searching across funding programmes", ("keywords", "status")),
    "recommend_programmes": (
        "Checking which programmes fit the request",
        ("org_type", "organization_type", "sector"),
    ),
    "get_programme_info": ("Looking up programme guidance", ("programme",)),
    "check_erasmus_eligibility": (
        "Checking Erasmus+ eligibility rules",
        ("country", "org_type", "action_type"),
    ),
    "calculate_erasmus_budget": ("Calculating the Erasmus+ budget", ("action_type",)),
    "search_erasmus_templates": ("Searching Erasmus+ application guidance", ("query",)),
    "check_creative_europe_eligibility": (
        "Checking Creative Europe eligibility rules",
        ("country", "strand"),
    ),
    "calculate_creative_europe_budget": (
        "Calculating the Creative Europe budget",
        ("action_type",),
    ),
    "search_creative_europe_templates": (
        "Searching Creative Europe application guidance",
        ("query",),
    ),
    "check_eu4health_eligibility": (
        "Checking EU4Health eligibility rules",
        ("country", "org_type"),
    ),
    "search_eu4health_templates": ("Searching EU4Health application guidance", ("query",)),
    "check_digital_europe_eligibility": (
        "Checking Digital Europe eligibility rules",
        ("country", "org_type"),
    ),
    "check_life_eligibility": ("Checking LIFE eligibility rules", ("country", "subprogramme")),
    "search_life_templates": ("Searching LIFE application guidance", ("query",)),
    "score_proposal_section": ("Scoring a proposal section", ("section_type",)),
    "score_full_proposal": ("Scoring the proposal against evaluation criteria", ()),
    "quick_quality_check": ("Checking the draft's structure and clarity", ()),
    "validate_budget": ("Checking the budget against funding rules", ("action_type",)),
    "generate_section_draft": ("Drafting the proposal section", ("section_id", "call_id")),
    "improve_section": ("Improving the proposal section", ("section_id",)),
    "rewrite_section": ("Rewriting the proposal section", ("section_id", "style")),
    "evaluate_section": ("Evaluating the proposal section", ("section_id",)),
    "analyze_gaps": ("Checking for missing proposal requirements", ("section_id",)),
    "check_compliance": ("Checking proposal compliance", ("section_id", "check_type")),
    "get_suggestions": ("Preparing section improvement suggestions", ("section_id",)),
    "focus_section": ("Opening the proposal section", ("section_id",)),
    "get_document_overview": ("Checking the proposal's current structure and status", ()),
    "mark_section_status": ("Updating the proposal section's status", ("section_id", "status")),
}

_LISTS = {
    "projects": ("project", "projects"),
    "similar_projects": ("project", "projects"),
    "calls": ("funding call", "funding calls"),
    "documents": ("document excerpt", "document excerpts"),
    "partners": ("partner", "partners"),
    "organizations": ("organization", "organizations"),
    "results": ("result", "results"),
}


def _scope(value):
    if not isinstance(value, str | int | float) or isinstance(value, bool):
        return ""
    # This is a UI label, not Markdown or a place to reproduce arbitrary tool text.
    text = re.sub(r"[^\w\s,./:+%\-]", "", str(value))
    text = " ".join(text.split())
    return text[:96] + ("…" if len(text) > 96 else "")


def tool_activity(name, params, display_name):
    action, keys = _ACTIONS.get(name, (f"Running {display_name}", ()))
    scope = [
        f"{key.replace('_', ' ')}: {text}" for key in keys if (text := _scope(params.get(key)))
    ]
    return action + (f" ({'; '.join(scope)})" if scope else "") + "."


def tool_outcome(display_name, result, success):
    if not success:
        return f"{display_name} failed; no verified result is available from this call."
    if result is None or result == {}:
        return f"{display_name} returned no usable output."
    if isinstance(result, dict):
        counts = []
        for key, (single, plural) in _LISTS.items():
            if isinstance(result.get(key), list):
                count = len(result[key])
                counts.append(f"{count} {single if count == 1 else plural}")
        if counts:
            return f"{display_name} returned " + ", ".join(counts[:3]) + "."
        if "project" in result:
            return f"{display_name} returned " + (
                "one project record." if result["project"] else "no matching project record."
            )
    if isinstance(result, list):
        return f"{display_name} returned {len(result)} result(s)."
    return f"{display_name} completed; its output is available for review."


def review_activity(outcomes):
    if not outcomes:
        return "Reviewing your request before choosing the next step."
    return "Reviewing tool outcomes before choosing the next step: " + " ".join(outcomes[-3:])


def answer_activity(outcomes):
    if not outcomes:
        return "The response is ready. No tool results were used."
    return "The response is ready after reviewing the tool outcomes: " + " ".join(outcomes[-3:])
