"""Deterministic call retrieval independent of embedding/provider availability."""

import re
from datetime import date, datetime

STOP_WORDS = frozenset(
    "zoek zoeken vind vindt toon laat zien calls call subsidies subsidie funding opportunities "
    "op over voor naar in de het een en met van uit voor mij graag rond ronde "
    "find search show list grants grant about for on in the and with of please "
    "open upcoming closed beschikbare actuele komende geopende gesloten".split()
)
CONCEPTS = {
    "ai": (
        "ai",
        "artificial intelligence",
        "artificial general intelligence",
        "agi",
        "kunstmatige intelligentie",
        "machine learning",
        "deep learning",
        "generative ai",
        "genai",
        "genai4eu",
    ),
    "health": (
        "health",
        "healthcare",
        "health care",
        "gezondheid",
        "gezondheidszorg",
        "zorg",
        "medical",
        "clinical",
        "biomedical",
        "patient",
        "patients",
        "hlth",
    ),
}


def query_groups(query: str) -> list[tuple[str, ...]]:
    """Require every concept, allowing synonyms within a concept (never 'AI' in 'said')."""
    text = query.lower()
    groups = []
    for aliases in CONCEPTS.values():
        pattern = (
            r"(?<!\w)(?:"
            + "|".join(re.escape(alias) for alias in sorted(aliases, key=len, reverse=True))
            + r")(?!\w)"
        )
        if re.search(pattern, text):
            groups.append(aliases)
            text = re.sub(pattern, " ", text)
    for word in re.findall(r"[^\W_]+", text, flags=re.UNICODE):
        if len(word) >= 2 and word not in STOP_WORDS and not re.fullmatch(r"20\d{2}", word):
            if (word,) not in groups:
                groups.append((word,))
    return groups[:12]


def keyword_predicate(query: str, title_only: bool = False) -> tuple[str, list[str]]:
    """Return parameterized SQL; identifiers are fixed, user text is always a parameter."""
    haystack = (
        "concat_ws(' ', topic_code, title)"
        if title_only
        else "concat_ws(' ', topic_code, title, scope, expected_outcome)"
    )
    conditions, params = [], []
    for aliases in query_groups(query):
        alternatives = []
        for alias in aliases:
            alternatives.append(f"{haystack} ~* %s")
            params.append(r"\m" + re.escape(alias) + r"\M")
        conditions.append("(" + " OR ".join(alternatives) + ")")
    return " AND ".join(conditions) or "TRUE", params


def concept_rank(query: str) -> tuple[str, list[str]]:
    """Prefer calls naming the requested concepts over broad cross-sector calls."""
    scores, params = [], []
    for group in query_groups(query):
        predicate, values = keyword_predicate(group[0], title_only=True)
        scores.append(f"CASE WHEN ({predicate}) THEN 1 ELSE 0 END")
        params.extend(values)
    return " + ".join(scores) or "0", params


def query_year(query: str) -> int | None:
    years = set(re.findall(r"\b20\d{2}\b", query))
    return int(next(iter(years))) if len(years) == 1 else None


def as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d %B %Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value.split("T")[0], fmt).date()
            except ValueError:
                continue
    return None


def effective_status(call: dict, today: date | None = None) -> str:
    today = today or date.today()
    deadline, opening = as_date(call.get("deadline")), as_date(call.get("opening_date"))
    stored = str(call.get("status") or "unknown").lower()
    if (deadline and deadline < today) or stored == "closed":
        return "closed"
    if (call.get("metadata") or {}).get("portal_missing_from_snapshot"):
        return "unknown"
    if stored not in {"open", "upcoming"}:
        return stored
    if opening:
        return "upcoming" if opening > today else "open"
    return stored


STATUS_SQL = """CASE
    WHEN deadline < CURRENT_DATE OR lower(status) = 'closed' THEN 'closed'
    WHEN metadata->>'portal_missing_from_snapshot' = 'true' THEN 'unknown'
    WHEN lower(COALESCE(status, 'unknown')) NOT IN ('open', 'upcoming') THEN lower(COALESCE(status, 'unknown'))
    WHEN opening_date > CURRENT_DATE THEN 'upcoming'
    WHEN opening_date <= CURRENT_DATE THEN 'open'
    ELSE lower(COALESCE(status, 'unknown')) END"""
