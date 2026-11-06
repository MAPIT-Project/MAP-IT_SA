"""Cited selection-announcement snapshots, not live award or payment statistics.

Each row uses the call/cut-off year, not the publication or project start year.
Amounts are rounded announcements. Keep source URLs and qualifications with data.
See docs_tracked/PROGRAMME_STATISTICS.md for provenance and update instructions.
"""

from copy import deepcopy

EIC_NEWS = "https://eic.ec.europa.eu/news/"
ERC_NEWS = "https://erc.europa.eu/news-events/news/"

# year, full/submitted proposals, selected proposals, announced support EUR,
# source URL(s). EIC amounts combine grants and equity; ERC amounts are grants.
SELECTIONS = {
    "EIC-ACC": [
        (
            2023,
            476,
            32,
            196_000_000,
            [
                EIC_NEWS
                + "european-innovation-council-new-group-deep-tech-start-ups-receive-accelerator-investments-increase-2023-03-29_en"
            ],
        ),
        (
            2023,
            551,
            51,
            260_000_000,
            [
                EIC_NEWS
                + "european-innovation-council-accelerator-new-group-deep-tech-start-ups-selected-get-funding-and-2023-06-19_en"
            ],
        ),
        (
            2023,
            648,
            47,
            350_000_000,
            [
                EIC_NEWS
                + "european-innovation-council-accelerator-strong-performance-engineering-and-tech-based-companies-2023-10-30_en"
            ],
        ),
        (
            2023,
            1083,
            42,
            285_000_000,
            [
                EIC_NEWS
                + "eic-accelerator-eur285-million-funding-deep-tech-start-ups-most-competitive-funding-round-2024-02-28_en"
            ],
        ),
        (
            2024,
            969,
            68,
            411_000_000,
            [
                EIC_NEWS
                + "eic-accelerator-68-deep-tech-start-ups-latest-funding-round-2024-07-15_en"
            ],
        ),
        (
            2024,
            1211,
            71,
            387_000_000,
            [
                EIC_NEWS
                + "eic-accelerator-71-companies-selected-most-competitive-funding-round-so-far-2025-02-17_en"
            ],
        ),
        (
            2025,
            959,
            40,
            230_000_000,
            [
                EIC_NEWS
                + "health-space-40-start-ups-secure-eic-support-latest-round-eic-accelerator-2025-06-30_en",
                "https://www.cdti.es/en/noticias/espana-2o-lugar-corte-marzo-2025-eic-horizonte-europa-cdti-innovacion",
            ],
        ),
        (
            2025,
            923,
            61,
            467_000_000,
            [
                EIC_NEWS
                + "strong-interest-eic-accelerator-funding-923-companies-applying-final-2025-cut-2025-10-17_en",
                EIC_NEWS
                + "61-start-ups-and-smes-secure-eic-support-latest-round-eic-accelerator-2026-02-17_en",
            ],
        ),
    ],
    "ERC-ADG": [
        (2023, 1829, 255, 652_000_000, [ERC_NEWS + "erc-2023-advanced-grants-results"]),
        (2024, 2534, 281, 721_000_000, [ERC_NEWS + "erc-2024-advanced-grants-results"]),
        (2025, 3329, 319, 838_000_000, [ERC_NEWS + "erc-2025-advanced-grants-results"]),
    ],
}


def published_statistics(code: str, year_from=None, year_to=None) -> dict:
    """Aggregate the cited cut-offs; never fill missing years from other periods."""
    all_rows = SELECTIONS.get(code, [])
    rows = [
        row
        for row in all_rows
        if (year_from is None or row[0] >= year_from) and (year_to is None or row[0] <= year_to)
    ]

    def summarize(items):
        submitted = sum(row[1] for row in items)
        selected = sum(row[2] for row in items)
        total = sum(row[3] for row in items)
        return {
            "submitted_proposals": submitted,
            "selected_proposals": selected,
            "selection_rate_percent": round(100 * selected / submitted, 4),
            "announced_support_eur_approx": total,
            "mean_announced_support_eur_approx": round(total / selected, 2),
            "sources": list(dict.fromkeys(url for row in items for url in row[4])),
        }

    years = sorted({row[0] for row in rows})
    missing = (
        sorted(set(range(year_from, year_to + 1)) - set(years))
        if year_from is not None and year_to is not None
        else []
    )
    return {
        "source": "cited_selection_announcements",
        "reviewed_on": "2026-11-06",
        "year_basis": "call_or_cutoff_year",
        "available_years": sorted({row[0] for row in all_rows}),
        "missing_years": missing,
        "annual": [
            {"year": year, **summarize([r for r in rows if r[0] == year])} for year in years
        ],
        "period": summarize(rows) if rows and not missing else None,
        "denominator": (
            "submitted full proposals; excludes short-application stage; "
            "repeat submissions may count separately"
            if code == "EIC-ACC"
            else "submitted Advanced Grant proposals"
        ),
        "funding_basis": (
            "announced grant plus equity support, including estimated or "
            "requested investment; not grant-only awards or disbursements"
            if code == "EIC-ACC"
            else "announced grant funding"
        ),
        "limitations": [
            "Selection-announcement snapshots, not final signed awards; later revisions may differ.",
            "Means are derived from rounded published totals, not individual award amounts.",
            "Different applicant populations and selection stages; rates are not comparable odds.",
            "No automatic refresh. Missing years have no inferred rate or funding average.",
        ],
        "rounds": deepcopy(rows),
    }
