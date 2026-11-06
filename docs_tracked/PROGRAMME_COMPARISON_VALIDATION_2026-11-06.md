# EIC Accelerator / ERC Advanced comparison repair

Codex implemented the changes. Antigravity executed validation. The existing ten
scenario results remain scoped to those questions; this comparison is a separate
regression and was not covered by their earlier pass result.

## Changes

- `app/services/tools/funding_cohorts.py`: explicit programme aliases and SQL
  predicates, including specific ERC schemes encoded in call topics. Year filters
  reject invalid/conflicting input. Existing RIA, IA and CSA names remain supported.
- `app/services/tools/budget_benchmark.py`: programme/year ranges reach SQL;
  filtered queries exclude incompatible graph aggregates and auxiliary breakdowns.
  SQL is authoritative instead of averaging overlapping graph/SQL cohorts. Missing
  organisation rows do not remove funded projects from monetary averages. Source
  failures and empty cohorts have no substituted budget averages. Graph-only
  results no longer invent consortium or per-partner statistics.
- `app/services/tools/published_programme_statistics.py`: cited, dated selection
  snapshots for 2023–2025. Application denominators, selection counts, published
  amounts and source links travel with the result. Approximate announced support
  is distinguished from final grants or payments. Missing years are explicit.
- `app/services/tools/programme_statistics.py`: removes unsourced rate ranges and
  outdated undated funding ceilings. Both statistics entry points use the same
  programme source and period filters. Other schemes cannot infer success rates
  from funded-project counts.
- `app/services/agents/tool_registry.py` and `tool_executors.py`: expose and forward
  the parameters, validate metric names and offload blocking benchmark calls.
- `app/services/agents/framework/runtime.py`: historical questions request explicit
  years and schemes, and retain the distinction between call years, project start
  years, grant amounts and equity support.
- `tests/test_programme_comparison_regressions.py`: external boundaries are mocked;
  assertions cover filters, old action names, empty/unavailable sources, provenance,
  annual/pooled arithmetic and dispatch. These are not real inference tests.
- `scripts/verify_programme_comparison.py`: optional read-only production SQL checks
  and separately capped real question. No existing records are written; failed
  runs retain partial evidence and generation usage.

See [statistics provenance and commands](PROGRAMME_STATISTICS.md).

## Actual checks

Independent SQL over existing local funding rows matched production benchmarks:

| Start-year cohort, 2023–2025 | Projects | Mean stored EU contribution |
|---|---:|---:|
| EIC Accelerator | 291 | €2,363,302.67 |
| ERC Advanced Grant | 523 | €2,495,384.85 |

These are local samples, not complete annual award populations. In particular,
stored EU contributions do not establish the EIC equity component.

The real question ran once:

```bash
.venv/pydantic-agent/bin/python scripts/verify_programme_comparison.py \
  --live-question --output .venv/programme-comparison-live.json
```

Exit 0. Codex `gpt-6.1-sol`, high reasoning effort: **3 completed calls**, no failed
calls, **105,235 reported tokens**, within the four-call / 180,000-token allowance.
This is reported usage, not a billing total or subscription quota percentage.
Antigravity development/validation usage is separate. No extra model graded the answer.

The answer included all three annual rates and approximate means, application
counts, pooled statistics, citations, denominator/financing distinctions and an
EIC recommendation based on programme fit. Antigravity independently reviewed it
against the returned source records. It called `compare_programmes`, attempted
`search_documents` and used `recommend_programmes`.

The check deliberately denied embeddings and paid text APIs. Document retrieval
failed because no embedding key was loaded into this isolated check, and the answer
disclosed that current detailed eligibility had not been verified. This is not a
test of live embedding retrieval, persistent HTTP chat, all other tools or Neo4j.
The real application retains its existing embedding configuration.

The first offline run found two incomplete mock fixtures (missing SQL aggregate
fields). After correcting the fixtures, the full suite passed: **2,866 passed,
2 skipped, 421 warnings in 28.29 seconds** on Python 3.12. Ruff passed on nine Python
paths and `git diff --check` passed. Three additional action-name regressions and
the final refreshed API are checked in the completion report below.

Final run after those additions: **2,869 passed, 2 skipped, 421 warnings in 28.53
seconds**, exit 0. The two skips are existing missing-workflow checks. Ruff passed
on all nine Python paths. The refreshed API returned HTTP 200 from both
`/api/health/live` and `/api/health/ready`, with PostgreSQL and Codex healthy.

Local artifacts:

- `.venv/programme-comparison-live.json`: actual answer, tool events and usage.
- `.venv/antigravity-programme-comparison-live.json`: independent answer review.
- `.venv/programme-comparison-readonly.json`: SQL source facts and benchmark results.
- `.venv/antigravity-programme-comparison-complete.json`: latest full suite, lint and health.

No commits, pushes, database changes, migrations or credential-file edits were made.
The local API refresh uses the existing configuration loader and Codex/high settings.
Startup performs its existing embedding health request, separate from the zero
embedding calls in this evaluation.
