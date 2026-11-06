"""Programme filters shared by funding statistics and budget benchmarks."""

import re


def programme_code(value: str) -> str:
    """Resolve supported names without confusing a pillar with one of its schemes."""
    name = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    aliases = {
        "ria": "RIA",
        "ia": "IA",
        "csa": "CSA",
        "eic": "EIC",
        "eic accelerator": "EIC-ACC",
        "accelerator": "EIC-ACC",
        "eic acc": "EIC-ACC",
        "horizon eic acc": "EIC-ACC",
        "erc": "ERC",
        "european research council": "ERC",
        "erc advanced": "ERC-ADG",
        "erc advanced grant": "ERC-ADG",
        "erc advanced grants": "ERC-ADG",
        "erc adg": "ERC-ADG",
        "horizon erc adg": "ERC-ADG",
        "erc starting grant": "ERC-STG",
        "erc stg": "ERC-STG",
        "erc consolidator grant": "ERC-COG",
        "erc cog": "ERC-COG",
        "erc synergy grant": "ERC-SYG",
        "erc syg": "ERC-SYG",
        "erc proof of concept": "ERC-POC",
        "erc poc": "ERC-POC",
        "msca": "MSCA",
        "marie curie": "MSCA",
        "marie sklodowska curie actions": "MSCA",
    }
    if name not in aliases:
        raise ValueError(f"Unsupported funding programme: {value!r}")
    return aliases[name]


def programme_predicate(value: str) -> tuple[str, list[str]]:
    """Match scheme codes or call topics, including ERC's shared fundingScheme."""
    code = programme_code(value)
    if code.startswith("ERC-"):
        topic = rf"(^|[^A-Z0-9])ERC-[0-9]{{4}}-{code[4:]}([^A-Z0-9]|$)"
    elif code == "EIC-ACC":
        topic = r"(^|[^A-Z0-9])EIC-[0-9]{4}-ACCELERATOR(?:OPEN|CHALLENGES)?([^A-Z0-9]|$)"
    else:
        topic = rf"(^|[^A-Z0-9]){code}([^A-Z0-9]|$)"
    scheme = rf"(^|-){code}(-|$)"
    return '(p."fundingScheme" ~* %s OR p.topics ~* %s)', [scheme, topic]


def year_bounds(year=None, year_from=None, year_to=None):
    """Reject conflicting or invalid filters instead of broadening the cohort."""
    values = [value for value in (year, year_from, year_to) if value is not None]
    if any(type(value) is not int or not 1900 <= value <= 2200 for value in values):
        raise ValueError("Years must be integers between 1900 and 2200")
    if year is not None:
        if any(value is not None and value != year for value in (year_from, year_to)):
            raise ValueError("year conflicts with year_from/year_to")
        return year, year
    if year_from is not None and year_to is not None and year_from > year_to:
        raise ValueError("year_from must not exceed year_to")
    return year_from, year_to
