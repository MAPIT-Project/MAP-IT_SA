"""Deterministic checks for source-backed tool results and model answers.

Checks return failures; missing data, fake success flags, and placeholder service
responses never receive an empty failure list. No model grades another model.
"""

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .catalog import AnswerAssertion, QuestionScenario, ToolCase, build_cases


def _get(value, path):
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _first(value, *paths):
    for path in paths:
        found = _get(value, path)
        if found is not None:
            return found
    return None


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def _equal(errors, label, actual, expected, tolerance=Decimal("0")):
    expected_number = _number(expected)
    actual_number = _number(actual)
    if expected is None:
        errors.append(f"Source evidence has no {label}")
    elif expected_number is not None and actual_number is not None:
        if abs(actual_number - expected_number) > tolerance:
            errors.append(f"{label}: expected {expected}, got {actual}")
    elif str(actual).casefold() != str(expected).casefold():
        errors.append(f"{label}: expected {expected}, got {actual}")


def _records(result, *paths):
    value = _first(result, *paths)
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    return []


def _id(row):
    return str(_first(row, "project_id", "id", "projectID", "topic_code", "call_id") or "")


def _source_ids(rows):
    return {_id(row) for row in rows if _id(row)}


def _nonempty(errors, label, value):
    if value is None or value == "" or value == [] or value == {}:
        errors.append(f"{label} is empty")


def _date(value):
    if isinstance(value, date | datetime):
        return value.date() if isinstance(value, datetime) else value
    if value is None:
        return None
    for pattern in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(
                str(value)[:10] if pattern == "%Y-%m-%d" else str(value), pattern
            ).date()
        except ValueError:
            pass
    return None


def _reject_failure(result):
    if not isinstance(result, dict):
        return ["Tool output must be a structured object"]
    errors = []
    if result.get("error"):
        errors.append("Tool returned an error")
    if result.get("success") is False:
        errors.append("Tool reported failure")
    # Degraded SQL fallback may still provide exact source-backed results. A
    # fabricated/default/AI-unavailable result is never an acceptable substitute.
    serialized = json.dumps(result, default=str).casefold()
    if result.get("fallback") is True or any(
        term in serialized
        for term in (
            "placeholder",
            "service unavailable",
            "assuming compliant",
            "using typical values",
            "no session manager available",
            "rule-based evaluation (ai unavailable)",
        )
    ):
        errors.append("Tool returned a placeholder or unavailable-service fallback")
    return errors


def validate_tool(case: ToolCase, result: Any, facts: dict[str, list[dict]]) -> list[str]:
    """Compare real tool output with independent source evidence and invariants."""
    errors = _reject_failure(result)
    if not isinstance(result, dict):
        return errors
    rows = facts.get(case.oracle_key, []) if case.oracle_key else []
    if case.oracle_key and not rows:
        return errors + [f"Missing source evidence: {case.oracle_key}"]
    ref = rows[0] if rows else {}
    check = case.check
    if check == "project_details":
        for label, actual, expected in (
            ("project ID", _id(result), ref.get("project_id")),
            ("acronym", result.get("acronym"), ref.get("acronym")),
            ("EU contribution", result.get("ec_contribution"), ref.get("eu_contribution")),
            ("total cost", result.get("total_cost"), ref.get("total_cost")),
            ("coordinator", _get(result, "coordinator.name"), ref.get("coordinator_name")),
        ):
            _equal(errors, label, actual, expected)
        _equal(errors, "country count", result.get("country_count"), ref.get("country_count"))
    elif check == "project_partners":
        partners = _records(result, "partners")
        _equal(errors, "partner count", result.get("partner_count"), len(rows))
        actual = {(r.get("name"), r.get("country"), r.get("role")) for r in partners}
        expected = {(r.get("name"), r.get("country"), r.get("role")) for r in rows}
        if actual != expected:
            errors.append(
                f"Partner rows differ: {len(expected - actual)} missing, {len(actual - expected)} unexpected"
            )
        for partner in partners:
            source = next(
                (
                    r
                    for r in rows
                    if (r.get("name"), r.get("country"), r.get("role"))
                    == (partner.get("name"), partner.get("country"), partner.get("role"))
                ),
                None,
            )
            if source:
                _equal(
                    errors,
                    f"{partner.get('name')} contribution",
                    _first(partner, "ec_contribution", "ecContribution", "contribution"),
                    source.get("contribution") if source.get("contribution") is not None else 0,
                    Decimal("0.01"),
                )
    elif check in {
        "project_search",
        "organization_projects",
        "topic_neighbors",
        "semantic_neighbors",
        "cluster_projects",
        "semantic_projects",
    }:
        projects = _records(result, "projects", "similar_projects")
        _nonempty(errors, "Project results", projects)
        if check in {"project_search", "semantic_projects"} and str(ref.get("project_id")) not in {
            _id(r) for r in projects
        }:
            errors.append("Known source project was absent from the exact-acronym/title search")
        if check == "organization_projects":
            _equal(
                errors,
                "organisation project total",
                result.get("total_project_count"),
                (facts.get("reference_organization") or [{}])[0].get("project_count"),
            )
        if check in {
            "topic_neighbors",
            "semantic_neighbors",
            "cluster_projects",
            "organization_projects",
        }:
            source_ids = _source_ids(rows)
            actual_ids = {_id(r) for r in projects}
            if source_ids and not actual_ids.intersection(source_ids):
                errors.append("No returned project matches the independent expected source set")
            if check == "semantic_neighbors" and actual_ids != source_ids:
                errors.append("Stored-vector nearest neighbours differ from independent SQL")
        if check in {"topic_neighbors", "semantic_neighbors"} and case.parameters.get(
            "project_id"
        ) in {_id(r) for r in projects}:
            errors.append("Similarity results include the reference project itself")
        for project in projects:
            _nonempty(errors, "Project identifier", _id(project))
            _nonempty(errors, "Project title", project.get("title"))
    elif check == "organization_statistics":
        for field, source_field in (
            ("project_count", "project_count"),
            ("coordinator_count", "coordinations"),
            ("total_funding", "total_funding"),
        ):
            _equal(errors, field, result.get(field), ref.get(source_field), Decimal("0.01"))
        _equal(errors, "organisation name", result.get("name"), ref.get("name"))
    elif check == "country_statistics":
        _equal(errors, "country", result.get("country_code"), ref.get("country"))
        _equal(errors, "project count", result.get("project_count"), ref.get("project_count"))
        _equal(
            errors,
            "country organisation funding",
            result.get("total_funding"),
            ref.get("total_funding"),
            Decimal("0.01"),
        )
    elif check == "collaborations":
        partners = _records(result, "partners", "collaborators", "network.partners")
        _nonempty(errors, "Collaboration partners", partners)
        source = {r.get("name"): r for r in rows}
        matches = [r for r in partners if r.get("name") in source]
        _nonempty(errors, "Independently verified collaboration partners", matches)
        for partner in matches:
            _equal(
                errors,
                "shared projects",
                _first(partner, "shared_projects", "project_count"),
                source[partner["name"]].get("shared_projects"),
            )
    elif check == "call_details":
        _equal(errors, "call ID", result.get("call_id"), ref.get("topic_code"))
        _equal(errors, "call title", result.get("title"), ref.get("title"))
        _equal(errors, "effective call status", result.get("status"), ref.get("effective_status"))
        if _date(result.get("deadline")) != _date(ref.get("deadline")):
            errors.append("Call deadline differs from the source record")
        if ref.get("budget_total") is None and result.get("budget") not in (
            None,
            "",
            "N/A",
            "Not specified",
            "Unknown",
        ):
            errors.append("A budget was returned although the source budget is absent")
    elif check in {"open_calls", "all_programme_calls"}:
        calls = _records(result, "calls" if check == "open_calls" else "results")
        _nonempty(errors, "Open calls", calls)
        expected = {r["topic_code"]: r for r in rows}
        actual_ids = {_id(r) for r in calls}
        if not actual_ids.intersection(expected):
            errors.append("Known currently open call is missing")
        today = _date((facts.get("catalog_counts") or [{}])[0].get("database_date")) or date.today()
        for call in calls:
            deadline = _date(call.get("deadline"))
            if deadline is None or deadline < today:
                errors.append(f"Open result {_id(call)} has a missing or expired deadline")
            if call.get("status") != "open":
                errors.append(f"Open result {_id(call)} has status {call.get('status')}")
            source = expected.get(_id(call))
            if source and deadline != _date(source.get("deadline")):
                errors.append(f"Open result {_id(call)} deadline differs from source")
    elif check == "benchmark":
        stats = result.get("statistics", {})
        _equal(
            errors,
            "benchmark project sample",
            stats.get("projects_analyzed"),
            ref.get("project_count"),
        )
        for field, expected in (
            ("min", "min_budget"),
            ("max", "max_budget"),
            ("average", "avg_budget"),
            ("median", "median_budget"),
        ):
            _equal(
                errors,
                f"benchmark {field}",
                _get(stats, f"total_eu_contribution.{field}"),
                ref.get(expected),
                Decimal("1"),
            )
    elif check == "consortia":
        _equal(
            errors, "consortium sample", result.get("projects_analyzed"), ref.get("project_count")
        )
        _equal(
            errors,
            "average consortium size",
            _get(result, "consortium_size.average"),
            ref.get("avg_partners"),
            Decimal("0.11"),
        )
    elif check == "history":
        timeline = _first(result, "timeline", "yearly_trends", "funding_trends")
        if isinstance(timeline, dict):
            timeline = [
                {"year": key, **value} for key, value in timeline.items() if isinstance(value, dict)
            ]
        _nonempty(errors, "Funding history", timeline)
        by_year = {str(r.get("year")): r for r in timeline or [] if isinstance(r, dict)}
        for row in rows:
            actual = by_year.get(str(row["year"]))
            if actual is None:
                errors.append(f"Known funding year {row['year']} missing")
            else:
                _equal(
                    errors,
                    f"{row['year']} project count",
                    _first(actual, "project_count", "projects", "projects_funded"),
                    row.get("project_count"),
                )
                _equal(
                    errors,
                    f"{row['year']} funding",
                    _first(actual, "total_funding", "funding"),
                    row.get("total_funding"),
                    Decimal("1"),
                )
    elif check == "experienced_partners":
        partners = _records(result, "experienced_partners", "partners", "organizations")
        _nonempty(errors, "Experienced partner results", partners)
        expected = {r.get("name"): r for r in rows}
        for partner in partners:
            source = expected.get(partner.get("name"))
            if source is None:
                errors.append(
                    f"Partner {partner.get('name')} is absent from independent source selection"
                )
            elif (
                _number(
                    _first(
                        partner, "track_record.relevant_projects", "project_count", "total_projects"
                    )
                )
                or 0
            ) < 2:
                errors.append("An inexperienced partner passed the minimum-two-project filter")
    elif check in {"documents", "programme_documents"}:
        documents = _records(result, "documents", "results")
        _nonempty(errors, "Retrieved document excerpts", documents)
        source_ids = {str(r.get("document_id")) for r in rows}
        matched = [d for d in documents if str(d.get("document_id")) in source_ids]
        _nonempty(errors, "Source-backed document citation", matched)
        for doc in matched:
            _nonempty(errors, "Citation title", _first(doc, "title", "source", "document_title"))
            _nonempty(errors, "Citation content", doc.get("content"))
            if doc.get("page_number") is None:
                errors.append("Source-backed document has no page citation")
            evidence = facts.get("retrieved_document_evidence") or rows
            matching_source = [
                r
                for r in evidence
                if str(r.get("chunk_id")) == str(doc.get("chunk_id"))
                and str(r.get("document_id")) == str(doc.get("document_id"))
            ]
            passage = " ".join(str(doc.get("content", "")).split()).casefold()
            if not passage or not any(
                passage
                in " ".join(re.sub(r"[_=~]{6,}", " ", str(r.get("content", ""))).split()).casefold()
                for r in matching_source
            ):
                errors.append("Retrieved passage is not present in the independent source excerpt")
            for source in matching_source:
                if doc.get("page_number") != source.get("page_number"):
                    errors.append("Retrieved page differs from the independently stored page")
                if _first(doc, "title", "source", "document_title") != source.get("title"):
                    errors.append("Retrieved title differs from the independently stored title")
    elif check == "budget_arithmetic":
        budget = result.get("calculated_budget", {})
        _equal(
            errors,
            "RIA total cost",
            budget.get("total_cost"),
            case.parameters["target_budget"],
            Decimal("1"),
        )
        _equal(
            errors,
            "RIA EU contribution",
            budget.get("eu_contribution"),
            budget.get("total_cost"),
            Decimal("1"),
        )
        _equal(errors, "RIA funding rate", budget.get("funding_rate"), "100%")
    elif check == "timeline":
        packages = _records(result, "work_packages")
        _nonempty(errors, "Work packages", packages)
        for package in packages:
            start, end = _number(package.get("start_month")), _number(package.get("end_month"))
            if start is None or end is None or not 1 <= start <= end <= 36:
                errors.append("Work package lies outside the requested 36-month project")
        _nonempty(errors, "Timeline milestones", result.get("milestones"))
    elif check == "invalid_budget":
        if result.get("valid") is not False:
            errors.append("Overfunded RIA was incorrectly declared valid")
        issues = _records(result, "issues")
        if not any(i.get("category") == "funding_rate" for i in issues):
            errors.append("Missing funding-rate violation for EU contribution above total cost")
    elif check == "eligible":
        if _get(result, "result.eligible") is not True:
            errors.append("Known eligible German organisation/action was rejected or not evaluated")
        _nonempty(
            errors,
            "Eligibility requirements",
            _first(result, "result.requirements_met", "result.recommendations"),
        )
    elif check == "creative_budget":
        for key, expected in (
            ("eu_grant", 200000),
            ("co_financing", 50000),
            ("total_budget", 250000),
            ("funding_rate_percent", 80),
        ):
            _equal(errors, key, _get(result, f"breakdown.{key}"), expected, Decimal("0.01"))
    elif check == "erasmus_budget":
        _equal(errors, "Jean Monnet module lump sum", _get(result, "breakdown.total"), 30000)
    elif check == "empty_quality":
        if (_number(result.get("quality_estimate")) or 0) > 0:
            errors.append("Empty proposal text received a positive quality score")
        if not result.get("suggestions") and not result.get("error"):
            errors.append("Empty text was not identified as needing content")
    elif check == "recommendations":
        recommendations = _records(result, "recommendations")
        _nonempty(errors, "Programme recommendations", recommendations)
        if not any(
            "horizon" in str(_first(r, "programme", "programme_id", "name")).casefold()
            for r in recommendations
        ):
            errors.append("Horizon Europe missing for a university hydrogen research proposal")
    elif check == "programme_info":
        _equal(errors, "programme", result.get("programme"), "horizon_europe")
        _nonempty(
            errors, "Official programme website", _first(result, "official_website", "info.website")
        )
    elif check in {"section_score", "evaluate"}:
        score = _number(result.get("score"))
        if score is None or not 0 <= score <= 5:
            errors.append("Section score is outside the 0–5 scale")
        _nonempty(errors, "Evaluation criteria", _first(result, "criteria", "criterion_scores"))
    elif check == "full_score":
        scores = [
            _number(result.get(f"{section}_score"))
            for section in ("excellence", "impact", "implementation")
        ]
        if any(s is None or not 0 <= s <= 5 for s in scores):
            errors.append("Full proposal contains missing/out-of-range section scores")
        else:
            _equal(
                errors,
                "overall score sum",
                result.get("overall_score"),
                sum(scores),
                Decimal("0.11"),
            )
        if any(r.get("fallback") for r in result.get("section_scores", []) if isinstance(r, dict)):
            errors.append("Full proposal uses unavailable-model fallback scoring")
    elif check in {"draft", "improve", "rewrite"}:
        content = result.get("content", "")
        _nonempty(errors, "Generated section content", content)
        flag = {"draft": "generated", "improve": "improved", "rewrite": "rewritten"}[check]
        if result.get(flag) is not True:
            errors.append(f"Section operation did not report {flag}")
        if not isinstance(content, str) or len(content.split()) < 30:
            errors.append("Generated proposal section lacks substantive content")
        for term in ("hydrogen", "36", "20%"):
            if term not in str(content).casefold():
                errors.append(f"Proposal operation dropped supplied project constraint: {term}")
    elif check == "gaps":
        if result.get("analyzed") is not True:
            errors.append("Gap analysis did not execute")
        _nonempty(errors, "Gap findings for deliberately incomplete section", result.get("gaps"))
    elif check == "suggestions":
        _nonempty(
            errors, "Suggestions for deliberately incomplete section", result.get("suggestions")
        )
    elif check == "compliance":
        if not isinstance(result.get("compliant"), bool):
            errors.append("Compliance result is missing")
        _nonempty(errors, "Executed compliance checks", result.get("details"))
    elif check == "focus":
        if result.get("focused") is not True:
            errors.append("Section focus was not applied")
        _equal(errors, "focused section", result.get("section_id"), case.parameters["section_id"])
    elif check == "status":
        if result.get("updated") is not True:
            errors.append("Section status was not updated")
        _equal(errors, "section status", result.get("status"), case.parameters["status"])
    elif check == "overview":
        _nonempty(errors, "Document overview", result)
        if not any(key in result for key in ("sections", "sections_by_category", "document")):
            errors.append("Overview contains no document sections")
    elif check == "cached_projects":
        _nonempty(errors, "Cached project page", result.get("rendered_content"))
        if str(ref.get("project_id")) not in str(result.get("rendered_content")):
            errors.append("Cached page omitted the known cached project")
    elif check == "geography":
        _equal(
            errors, "geographic project sample", result.get("total_projects_analyzed"), len(rows)
        )
        groups = result.get("country_groups", {})
        representation = _records(result, "group_representation")
        _nonempty(errors, "Country groups", groups)
        _nonempty(errors, "Country group representation", representation)
        for group in representation:
            countries = set(groups.get(group.get("group"), []))
            count = sum(bool(countries.intersection(row.get("countries", []))) for row in rows)
            _equal(errors, "group project count", group.get("projects_with_partner"), count)
            _equal(
                errors,
                "group share",
                group.get("share_percentage"),
                Decimal(count * 100) / len(rows),
                Decimal("0.11"),
            )
    elif check in {"programme_statistics", "comparison"}:
        source = {r["cluster"]: r for r in rows}
        if check == "comparison":
            entries = result.get("comparison", {})
            _nonempty(errors, "Programme comparison", entries)
            actual = [value for value in entries.values() if isinstance(value, dict)]
        else:
            stats = result.get("statistics", [])
            actual = (
                [{"cluster_code": result.get("cluster_code"), "statistics": row} for row in stats]
                if isinstance(stats, list)
                else []
            )
        expected_codes = {"CL4", "CL5"} if check == "comparison" else {"CL5"}
        seen = set()
        for entry in actual:
            code = str(entry.get("cluster_code", "")).replace("CLUSTER-", "CL")
            ref = source.get(code)
            if ref is None:
                errors.append(f"No independent source scope for cluster {code}")
                continue
            seen.add(code)
            stats = entry.get("statistics") or {}
            _equal(
                errors,
                f"{code} project count",
                stats.get("project_count"),
                ref.get("project_count"),
            )
            _equal(
                errors,
                f"{code} total funding",
                stats.get("total_funding"),
                ref.get("total_funding"),
                Decimal("1"),
            )
        if not expected_codes <= seen:
            errors.append("Expected cluster statistics are missing")
    else:
        errors.append(f"No deterministic validator is implemented for {check}")
    return errors


def _numbers_in_text(text: str):
    """Read numbers with grouped thousands and optional million/billion units."""
    pattern = r"(?<![\w])(?:\d{1,3}(?:[, .\u00a0]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)(?!\d|[.,]\d)(?:\s*(?:million|billion|[MB])\b)?"
    values = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        raw = match.group().replace("\u00a0", " ")
        multiplier = Decimal(1)
        suffix = re.search(r"\s*(million|billion|M|B)$", raw, re.IGNORECASE)
        if suffix:
            multiplier = Decimal(
                1000000000 if suffix.group(1).casefold() in {"b", "billion"} else 1000000
            )
            raw = raw[: suffix.start()]
        raw = raw.replace(" ", "")
        if "," in raw and "." in raw:
            decimal_mark = "," if raw.rfind(",") > raw.rfind(".") else "."
            raw = raw.replace("." if decimal_mark == "," else ",", "").replace(decimal_mark, ".")
        elif "," in raw:
            raw = (
                raw.replace(",", "")
                if re.fullmatch(r"\d{1,3}(?:,\d{3})+", raw)
                else raw.replace(",", ".")
            )
        elif raw.count(".") > 1:
            raw = raw.replace(".", "")
        value = _number(raw)
        if value is not None:
            values.append(value * multiplier)
    return values


_LABEL_PATTERNS = {
    "EU contribution": r"(?:EU|EC|European).{0,20}(?:contribution|funding|grant)",
    "total cost": r"total.{0,12}(?:cost|budget)",
    "organisation funding": r"(?:funding|contribution|grant)",
    "German organisation funding": r"(?:funding|contribution|grant)",
    "partners": r"(?:partner|organi[sz]ation|consortium)",
    "countries": r"countr",
    "project count": r"project",
    "coordinations": r"coordinat",
}


def _assert_answer(assertion: AnswerAssertion, text: str) -> str | None:
    label = assertion.label or assertion.kind
    if assertion.value is None:
        return f"Missing source value for answer assertion: {label}"
    if assertion.kind in {"text", "identifier"}:
        expected = str(assertion.value)
        pattern = re.escape(expected)
        if assertion.kind == "identifier":
            pattern = r"(?<![\w])" + pattern + r"(?![\w])"
        if not re.search(pattern, text, re.IGNORECASE):
            return f"Answer omitted expected {label}: {expected}"
    elif assertion.kind == "regex":
        if not re.search(str(assertion.value), text):
            return f"Answer did not satisfy {label}"
    elif assertion.kind in {"number", "money"}:
        value = _number(assertion.value)
        candidates = [text]
        if assertion.label:
            pattern = _LABEL_PATTERNS.get(assertion.label, re.escape(assertion.label))
            candidates = [
                line for line in text.splitlines() if re.search(pattern, line, re.IGNORECASE)
            ]
        if value is None or not any(
            abs(n - value) <= assertion.tolerance
            for line in candidates
            for n in _numbers_in_text(line)
        ):
            return f"Answer omitted or changed {label}: {assertion.value}"
    elif assertion.kind == "unknown_budget":
        budget_lines = [line for line in text.splitlines() if "budget" in line.casefold()]
        if not any(
            re.search(
                r"(?i)(unknown|unavailable|not (?:recorded|specified|available)|missing|not provided|not in)",
                line,
            )
            for line in budget_lines
        ):
            return "Answer must explicitly state that the call budget is unavailable"
        if any(
            re.search(r"[€$£]|\bEUR\b|\bmillion\b|\bbillion\b", line, re.IGNORECASE)
            and any(n > 0 for n in _numbers_in_text(line))
            for line in budget_lines
        ):
            return "Answer invented a monetary call budget absent from the source"
    elif assertion.kind == "date":
        value = _date(assertion.value)
        variants = (
            [
                value.isoformat(),
                value.strftime("%d %B %Y"),
                value.strftime("%-d %B %Y"),
                value.strftime("%B %-d, %Y"),
            ]
            if value
            else []
        )
        if not any(v.casefold() in text.casefold() for v in variants):
            return f"Answer omitted or changed {label}: {assertion.value}"
    elif assertion.kind == "eligible_programme":
        lines = text.splitlines()
        programme = str(assertion.value)
        for index, line in enumerate(lines):
            if not re.search(re.escape(programme), line, re.IGNORECASE):
                continue
            # Ignore overview sentences that merely name all three programmes.
            if (
                sum(
                    name.casefold() in line.casefold()
                    for name in ("Erasmus", "LIFE", "Digital Europe")
                )
                > 1
            ):
                continue
            scope = " ".join(lines[index : index + 4])
            outcome = re.search(
                r"(?i)\b(not\s+eligible|ineligible|cannot\s+(?:apply|participate)|eligible|yes|can\s+(?:apply|participate))\b",
                scope,
            )
            if outcome:
                if outcome.group().casefold().startswith(("not", "ineligible", "cannot")):
                    return f"Answer contradicts the eligible {programme} tool result"
                return None
        return f"Answer omitted the eligibility result for {programme}"
    else:
        return f"Unknown answer assertion kind: {assertion.kind}"
    return None


def _document_answer_errors(text, calls):
    documents = []
    for call in calls:
        name = call.get("tool_name") if isinstance(call, dict) else getattr(call, "tool_name", None)
        result = call.get("result") if isinstance(call, dict) else getattr(call, "result", None)
        if name == "search_documents" and isinstance(result, dict):
            documents.extend(result.get("documents", []))
    quotes = re.findall(r"(?m)^\s*>\s*(.+)$", text)
    quotes += re.findall(r'[“"]([^“”"\n]{24,})[”"]', text)

    def normalize(value):
        return " ".join(re.sub(r"[*_]", "", value).split()).casefold()

    for quote in quotes:
        parts = [normalize(part) for part in re.split(r"\.{3}|…", quote) if normalize(part)]
        if sum(map(len, parts)) < 24:
            continue
        for doc in documents:
            source = normalize(str(doc.get("content", "")))
            position = 0
            for part in parts:
                found = source.find(part, position)
                if found < 0:
                    break
                position = found + len(part)
            else:
                title = str(_first(doc, "title", "source", "document_title") or "")
                words = {
                    word
                    for word in re.findall(r"[a-z]{3,}", title.casefold())
                    if word not in {"pdf", "the", "and"}
                }
                title_present = (
                    len(words.intersection(set(re.findall(r"[a-z]{3,}", text.casefold()))))
                    >= min(3, len(words))
                    if words
                    else False
                )
                page = doc.get("page_number")
                page_present = page is not None and re.search(
                    rf"(?i)\b(?:pages?|pp?\.)\s*{re.escape(str(page))}\b", text
                )
                if title_present and page_present:
                    return []
    return [
        "Answer must quote a returned source passage and cite that document's title and stored page"
    ]


def validate_answer(
    scenario: QuestionScenario, text: str, tool_calls: list[Any], facts: dict[str, list[dict]]
) -> list[str]:
    """Require successful expected tool calls and independently known answer facts."""
    errors = []
    if not isinstance(text, str) or not text.strip():
        return ["Final answer is empty"]
    for key in scenario.oracle_keys:
        if not facts.get(key):
            errors.append(f"Missing source evidence: {key}")
    successful = set()
    candidate_errors = {}
    contracts = {case.tool: case for case in build_cases(facts)}
    for call in tool_calls:
        if isinstance(call, dict):
            name = call.get("tool_name") or call.get("tool")
            success = call.get("success")
            result = call.get("result")
            parameters = call.get("parameters", {})
        else:
            name, success, result = (
                getattr(call, "tool_name", None),
                getattr(call, "success", False),
                getattr(call, "result", None),
            )
            parameters = getattr(call, "parameters", {})
        if success and not _reject_failure(result):
            if name in scenario.expected_tools and name in contracts:
                failures = validate_tool(contracts[name], result, facts)
                controls = {
                    "validate_budget": ("total_cost", "eu_contribution"),
                    "calculate_budget": ("target_budget",),
                }.get(name, ())
                for field in controls:
                    if _number(parameters.get(field)) != _number(
                        contracts[name].parameters.get(field)
                    ):
                        failures.append(f"Tool did not check the requested {field}")
                if failures:
                    candidate_errors.setdefault(name, []).extend(
                        f"{name}: {failure}" for failure in failures
                    )
                    continue
            successful.add(name)
    for name in scenario.expected_tools:
        if name not in successful:
            errors.append(f"Expected tool {name} did not complete successfully")
            errors.extend(candidate_errors.get(name, []))
    if not scenario.assertions:
        errors.append("Question has no independent answer assertions")
    for assertion in scenario.assertions:
        error = _assert_answer(assertion, text)
        if error:
            errors.append(error)
    if scenario.id == "document_grounding":
        errors.extend(_document_answer_errors(text, tool_calls))
    return errors
