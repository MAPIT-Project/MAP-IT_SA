"""Small deterministic safeguards; these do not certify factual correctness."""

EMPTY_COLLECTIONS = {
    "search_documents": "documents",
    "search_funding_calls": "calls",
    "search_all_programmes": "results",
    "search_projects": "projects",
}


def unavailable_evidence(calls):
    if not calls:
        return False
    for call in calls:
        if not call.success:
            continue
        key = EMPTY_COLLECTIONS.get(call.tool_name)
        # An unknown tool contract or a successful detail/statistics call must
        # not be silently treated as an empty search.
        if key is None or not isinstance(call.result, dict):
            return False
        rows = call.result.get(key)
        if not isinstance(rows, list) or rows:
            return False
    return True


def is_dutch_query(query):
    import re

    return bool(
        re.search(
            r"\b(wat|welke|zoek|geef|kan|hoe|waar|wie|wanneer|zijn|heb|een|het|de|voor)\b",
            query,
            re.I,
        )
    )


def evidence_failure_answer(query):
    # The common UI language is Dutch; preserve English for plainly English
    # questions without invoking another model to generate the refusal.
    if not is_dutch_query(query):
        return (
            "Usable source evidence is unavailable for this request. "
            "I therefore cannot verify the requested facts and will not supply "
            "unverified deadlines, amounts or conditions. This does not prove that "
            "the requested call, document or project does not exist."
        )
    return (
        "Ik kon voor deze vraag geen bruikbare brongegevens ophalen. Daarom kan ik "
        "de gevraagde feiten niet verifiëren en geef ik geen onbevestigde deadlines, "
        "bedragen of voorwaarden. Dit bewijst niet dat de gezochte call, het document "
        "of het project niet bestaat."
    )
