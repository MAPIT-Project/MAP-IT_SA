# Historical programme statistics

`get_programme_statistics` and `compare_programmes` accept `year`, or inclusive
`year_from` / `year_to`. Use the specific scheme, such as **EIC Accelerator** or
**ERC Advanced Grant**. A broad ERC query must not become Advanced Grant statistics.
`metric` accepts `success_rate`, `avg_funding`, or `participation`; comparison
`metrics` accepts those names. Source context remains in the response.

The application includes reviewed **selection-announcement snapshots** for the
2023–2025 EIC Accelerator and ERC Advanced Grant calls. The records and source URLs
are in `app/services/tools/published_programme_statistics.py`. They are explicitly
dated, have no runtime network dependency, and do not claim automatic refresh.
Unknown years remain unknown; an incomplete requested period has no aggregate.

Every annual rate is selected proposals divided by submitted proposals. EIC uses
full proposals, excluding the short-application stage; repeated submissions can
count separately. ERC uses submitted Advanced Grant proposals. Different stages
and applicant populations mean the percentages are not comparable personal odds.
Period rates use summed counts, not an unweighted mean of annual percentages.

Mean announced support is the sum of rounded published funding totals divided by
the selected count. For EIC this combines grants and equity and includes estimated
or requested investment. It is **not** mean grant funding, signed investment or
cash disbursed. ERC totals are announced grants. Both means are approximate.
Selection announcements may be revised after reserve-list processing or grant
preparation. These records deliberately retain their original announcement cohort.
For example, the April 2024 ERC 2023 release reports 255 selections; a later reserve
list statistics publication reports a different count. Do not combine their totals.

## Sources reviewed on 6 November 2026

| Call year | EIC submitted / selected | Announced support, approximately | ERC submitted / selected | Announced grants, approximately |
|---|---:|---:|---:|---:|
| 2023 | 2,758 / 172 | €1,091 million | 1,829 / 255 | €652 million |
| 2024 | 2,180 / 139 | €798 million | 2,534 / 281 | €721 million |
| 2025 | 1,882 / 101 | €697 million | 3,329 / 319 | €838 million |

EIC 2023 aggregates four cut-offs, 2024 and 2025 aggregate two each. Sources:

- 2023: [January](https://eic.ec.europa.eu/news/european-innovation-council-new-group-deep-tech-start-ups-receive-accelerator-investments-increase-2023-03-29_en),
  [March](https://eic.ec.europa.eu/news/european-innovation-council-accelerator-new-group-deep-tech-start-ups-selected-get-funding-and-2023-06-19_en),
  [June](https://eic.ec.europa.eu/news/european-innovation-council-accelerator-strong-performance-engineering-and-tech-based-companies-2023-10-30_en),
  [November](https://eic.ec.europa.eu/news/eic-accelerator-eur285-million-funding-deep-tech-start-ups-most-competitive-funding-round-2024-02-28_en).
- 2024: [March](https://eic.ec.europa.eu/news/eic-accelerator-68-deep-tech-start-ups-latest-funding-round-2024-07-15_en),
  [October](https://eic.ec.europa.eu/news/eic-accelerator-71-companies-selected-most-competitive-funding-round-so-far-2025-02-17_en).
- 2025: [March selections](https://eic.ec.europa.eu/news/health-space-40-start-ups-secure-eic-support-latest-round-eic-accelerator-2025-06-30_en),
  [March denominator, Spanish national contact point CDTI](https://www.cdti.es/en/noticias/espana-2o-lugar-corte-marzo-2025-eic-horizonte-europa-cdti-innovacion),
  [October denominator](https://eic.ec.europa.eu/news/strong-interest-eic-accelerator-funding-923-companies-applying-final-2025-cut-2025-10-17_en),
  [October selections](https://eic.ec.europa.eu/news/61-start-ups-and-smes-secure-eic-support-latest-round-eic-accelerator-2026-02-17_en).
- ERC: [2023](https://erc.europa.eu/news-events/news/erc-2023-advanced-grants-results),
  [2024](https://erc.europa.eu/news-events/news/erc-2024-advanced-grants-results),
  [2025](https://erc.europa.eu/news-events/news/erc-2025-advanced-grants-results).

To extend coverage, add the dated official publication, application denominator,
selection count, amount definition and all cut-offs for that year. Update the
independent arithmetic tests and this provenance record. Never extend a source's
coverage by copying another year or substituting an award ceiling.

## Local CORDIS benchmarks

`get_budget_benchmark` separately accepts `programme`, `year`, `year_from`, and
`year_to`. Its years mean **project start years**, not call years. Specific schemes
match funding scheme codes or call topics, including ERC records whose scheme is
only `HORIZON-ERC`. Existing `cluster='EIC'` / `cluster='ERC'` calls become programme
filters. Unsupported programme names and conflicting years fail explicitly.

SQL is authoritative. Filtered cohorts do not merge all-year graph aggregates or
auxiliary breakdowns. Projects without organisation rows remain in funding averages;
per-partner averages exclude zero denominators. An empty cohort returns zero projects
with no budget average. A source failure returns an error, never a hardcoded average.
Stored `ecMaxContribution` does not include unrecorded equity. Local funded projects
cannot establish success rates without submitted-application counts.

## Regression commands

Offline tests mock external boundaries and check filters, source failures, missing
years, dispatch, annual arithmetic and weighted period arithmetic:

```bash
.venv/pydantic-agent/bin/python scripts/test_offline.py \
  tests/test_programme_comparison_regressions.py
```

Actual production budget SQL can be checked against independently selected local
source rows with zero model/embedding requests and no private configuration loading:

```bash
.venv/pydantic-agent/bin/python scripts/verify_programme_comparison.py \
  --output .venv/programme-comparison-readonly.json
```

The same script accepts `--live-question` to run the reported comparison question
through the actual agent. It uses Codex `gpt-6.1-sol`, high effort, a cap of four
generation invocations and 180,000 reported tokens, denies API-key generation and
embeddings, and keeps database access read-only. This is an opt-in manual check;
the offline suite does not run it. Review the saved answer against the returned
sources; there is no extra model-as-judge request. Reported token caps are checked
between invocations, so a final invocation may cross the threshold.
