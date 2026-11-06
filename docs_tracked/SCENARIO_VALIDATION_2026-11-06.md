# Ten funding scenarios: verified on 6 November 2026

All ten scenarios pass across the full live run and one targeted rerun. Antigravity
executed the real evaluations, the offline suite and an independent recheck of
every saved latest answer against its own source evidence. Codex wrote the changes.

| Scenario | Result | Checked facts or behavior |
|---|---|---|
| `project_facts` | Passed | IMAGHyNE; €19,996,911.75 EU contribution; €200,255,979.99 total cost; coordinator; CORDIS citation. |
| `project_consortium` | Passed | Complete 42-organisation consortium, five countries and coordinator. |
| `project_search` | Passed after targeted rerun | Actual `search_projects` call; exact acronym, CORDIS ID, full title and EU contribution. |
| `organization_statistics` | Passed | TUM: 219 projects, 88 coordinations and €152,284,911.61 organisation funding. |
| `country_statistics` | Passed | Germany: 5,193 distinct projects and €6,256,269,845.54 organisation participation funding. |
| `expired_call` | Passed | Recorded deadline 26 February 2026; effective status closed; recorded €219 million call budget. |
| `open_calls` | Passed after targeted rerun | Actual `search_funding_calls` call; unexpired 17 December 2026 deadline; unknown budget stated explicitly. |
| `planning_arithmetic` | Passed after targeted rerun | €5 million RIA cost/contribution at 100%; €1.1 million requested on €1 million cost rejected as 110% funding. |
| `programme_eligibility` | Passed | Erasmus+ university with ECHE, LIFE NGO and Digital Europe SME outcomes match the controlled tool inputs and returned conditions. |
| `document_grounding` | Passed after targeted rerun | Actual General Annexes excerpts, document title and stored page 12; general consortium rule distinguished from call-specific exceptions. |

## Fixes

- `app/services/ai/structured.py`: optional-null cleanup retains the root schema
  resolver when validating union branches and follows local definition pointers.
  The old detached branch validator raised `_WrappedReferencingError` on budget calls.
- `app/services/tools/document_search.py` and `app/services/document_content.py`:
  long chunks return a query-relevant contiguous excerpt instead of always the
  first 1,500 characters. Duplicate ingestions no longer fill the result limit;
  identical text with stored page metadata is preferred for citation.
- `app/services/vector_search_service.py`: document-type/year filters use the
  existing filtered semantic RPC. The hybrid RPC omits `document_type`, so filtering
  that absent result field locally discarded every candidate.
- `app/services/ai/codex.py`: CLI failures receive content-free diagnostic categories.
  Earlier CLI exits did not recur in this run; their original cause is not claimed
  to have been established.
- `scripts/evaluate_tools.py` and `tests/tool_scenarios/`: question mode preflights
  its required 13 tools, supports separately capped live document embeddings and
  read-only search RPCs, checks actual passages/titles/pages, records per-question
  usage and preserves partial calls on budget stops. Missing preflights cannot
  silently bypass tool checks.
- The document oracle now selects actual Horizon consortium guidance. The original
  four document anchors covered other programmes. Search questions explicitly name
  their intended tool because exact-acronym lookup and cross-programme search were
  otherwise valid alternative routes that did not exercise the requested coverage.

## Actual runs and usage

The initial live run returned **6 passed, 3 failed, 1 blocked**, with all **13 direct
tool checks passed**. Two answers were correct but used alternate tool paths. One
failed during schema validation. The document question reached the embedding cap.
These failures remain in the original report.

After the fixes, the targeted run returned **4 passed, 0 failed, 0 blocked**, with
all five of its required direct tool checks passed. Successful questions were not
rerun. The independent saved-report recheck then confirmed **10/10 latest answers
and 13/13 direct tool contracts**.

| Usage | Actual total |
|---|---:|
| Codex attempts across both live runs | 29, within the 30-attempt aggregate limit |
| Completed Codex attempts | 28 |
| Earlier failed schema-validation attempt | 1 |
| Known reported tokens | 895,594 |
| Attempts with unknown token usage | 1, the earlier failed attempt |
| Embedding requests including both document preflights | 8 |

895,594 is the reported sum, not a complete billing total or a subscription quota
percentage. Embedding token usage was not reported. Startup of the refreshed local
API performs one additional existing embedding health request. Antigravity/Codex
development and review usage is separate from these application evaluation counts.
No API-key text generation or additional AI grading request ran in the evaluator.

The full run used `--max-requests 30 --max-reported-tokens 1000000` and four embedding
requests. The targeted run used only the remaining nine model attempts and a
reported-token allowance of 356,932. It completed in eight attempts. Each run stopped
on its own budget controls; no automatic model rerun was configured.

Local artifacts:

- `.venv/scenario-ten-live.json`: original full live run and independent source rows.
- `.venv/scenario-four-repaired.json`: actual four-scenario targeted rerun.
- `.venv/scenario-ten-verified.json`: latest results, aggregate usage and links to
  the source run for every answer. Original failed outcomes remain in its run history.
- `.venv/antigravity-scenario-ten-verified.json`: independent recheck and answer review.

## Offline verification and limits

```bash
.venv/pydantic-agent/bin/python scripts/test_offline.py \
  --timeout=5 --timeout-method=signal --tb=short -p no:cacheprovider \
  --junitxml=.venv/scenario-repaired-final.xml \
  > .venv/scenario-repaired-final-tests.log 2>&1
```

**2,847 passed, 2 skipped, 0 failures/errors, 417 warnings in 31.59 seconds; exit 0.**
The skips are existing missing-workflow checks. Ruff passed on all 19 affected Python
paths. Offline tests mock external inference and storage; the real scenario runs
are separate and use actual Codex plus stored funding rows and live Google embeddings.

SQL runs in rolled-back read-only transactions. The graph transport is deliberately
disabled, so applicable statistics tools exercised their SQL fallback. This validates
the 13 covered tools and ten in-process questions, not all 52 tools, graph parity,
Supabase HTTP transport or persistent conversation handling. No existing funding,
profile, conversation or proposal record was modified. Private configuration was
consumed only through the normal loader; its file was neither printed nor changed.

The authorized local API on port 18000 was refreshed with these fixes, preserving
Codex `gpt-6.1-sol`, high reasoning effort and Google 3,072-dimensional embeddings.
Antigravity verified HTTP 200 for liveness and readiness; PostgreSQL and Codex report
healthy. `git diff --check` passed. See [test commands and opt-ins](TESTING.md).
