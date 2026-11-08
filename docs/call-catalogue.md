# Funding-call catalogue and search

The call catalogue is a searchable local snapshot, not evidence that every published
funding opportunity exists locally. This distinction must remain visible when data
is stale or a dependency fails.

## What changed

The November 2026 investigation found no 2027 calls in `funding_calls`, no catalogue-refresh job in the
application deployment, an invalid embedding API key, and zero vectors being treated as
successful embeddings. Search defaulted to open calls, excluded announced calls,
and did not expand common domain synonyms. Cross-programme ranking built raw
`to_tsquery` syntax from user punctuation. Speculative results could be reused for
different years/statuses, while oversized tool results could cut off entire calls.

The current path addresses these independently:

1. `CallCatalog.sync()` downloads all pages of official EU Portal open/upcoming
   search results before opening its write transaction. It deduplicates topic
   versions and upserts the six supported programmes. Existing embeddings, IDs,
   budgets, and document attribution are preserved. A failed/empty/truncated
   download never advances the last-success timestamp. Normalized dates correct
   expired labels. Absence from the downloaded snapshot does not automatically
   delete a local topic or declare it cancelled. Previously portal-synced topics
   missing from a complete active snapshot become unverified and are excluded
   from available-call discovery until a later snapshot verifies them again.
2. Search requires each requested concept but allows synonyms within it. Thus
   `AI & Health`, `artificial intelligence healthcare`, and `kunstmatige intelligentie
   en gezondheidszorg` can match the same calls. Short abbreviations use word
   boundaries; AI does not match inside “sustainable”. Queries remain parameterized.
   Explicit years, clusters, actions, and statuses also apply to semantic fallback.
   Old call years are not automatically excluded if the call is still available.
3. Point lookups require the exact official identifier; unrelated/parent search hits
   cannot be cached as the requested topic. Detail caching retains programme/year
   and does not replace a complete scope with an empty value.
4. General discovery includes open and upcoming calls. Explicit open/upcoming/
   closed requests retain their filter. Dates correct stale status labels; a
   two-stage first deadline is not replaced by the later invitation-only stage.
5. Source freshness and limitations accompany both search tools. The agent must
   distinguish an incomplete/unavailable source from verified absence of matches.
   Direct thematic matches rank ahead of broad cross-sector calls.
6. Model context uses structured call summaries when full scopes exceed its
   budget. Identifiers, dates, links, status, and source limitations are retained;
   full results remain available to API formatting and `get_call_details`.
7. Speculative searches retain AI/other short concepts and validate year, cluster,
   and status before cache reuse. Invalid/zero query vectors are rejected.

## Refresh and monitor

No AI or embedding credentials are required for catalogue refresh:

```bash
docker exec map-it_sa-api-1 python /app/scripts/sync_funding_calls.py
docker exec map-it_sa-api-1 python /app/scripts/sync_funding_calls.py --health
```

`GET /api/health/calls` returns indexed count, latest call year, and last successful
refresh. It returns 503 if refresh has never succeeded, data is older than 24 hours,
or the database cannot be checked. It does not call paid providers.

The systemd units in `scripts/systemd/` refresh every six hours, including missed
runs after reboot. After a successful refresh, they backfill up to 500 missing
embeddings for available calls in batches of 20. No embedding request is made when
there are no pending calls. Failed or zero-vector batches are rejected; source
content hashes prevent overwriting concurrently changed calls. Historical calls
are excluded from this automatic backfill. Install them on the Docker host:

```bash
sudo install -m 644 scripts/systemd/mapit-call-catalog.service /etc/systemd/system/
sudo install -m 644 scripts/systemd/mapit-call-catalog.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mapit-call-catalog.timer
systemctl list-timers mapit-call-catalog.timer
journalctl -u mapit-call-catalog.service
```

The service expects the current API container name and a working Docker daemon.
The Dockerfile includes the refresh entrypoint; a source bind mount also supports
it. The refresh uses `settings.database_url`, exactly like the search tools, so it
does not inadvertently populate a different Supabase database.

Visitor roles have no read/write grants on `funding_call_sync_state`; backend roles
retain access. The `funding_call_sync_state` row advances in the same transaction as successful
upserts. HTTP 429/5xx, invalid JSON, incomplete pagination and database failures
produce a failed job and leave the previous snapshot usable. Investigate failed
jobs; do not suppress them or manually advance timestamps. The tool and health
endpoint deliberately report stale data rather than hiding a refresh failure.

## Remaining limitations

- This snapshot covers supported programmes published through the EU Portal,
  not every national/cascade funding opportunity or an unpublished draft topic.
- Some official records omit budgets or have incomplete scope fields. Keep that
  uncertainty visible and verify details on the linked official topic page.
- Existing calls missing from a later snapshot require source verification; they
  are not automatically marked cancelled. Past deadlines are excluded immediately.
- Semantic discovery outside deterministic keyword/synonym matching still needs
  a valid Google embedding key. The initial key was rejected by Google; a new key
  was activated and verified on 8 November 2026. All 456 currently available calls
  then had valid 3,072-dimensional vectors, including 376 newly backfilled calls.
  Zero vectors fail validation and health tests. Future credential changes require
  recreating the API container (`docker compose up -d --no-deps api`), because a
  process restart does not replace Docker-injected environment variables.
- The chat generator and embeddings are separate dependencies. A working Codex
  chat provider does not establish that the Google embedding service works.

## Verification

Offline regressions in `tests/test_call_catalogue_regressions.py` cover multilingual
concept matching, punctuation, source parsing, first/second deadlines, partial and
empty refresh failure, topic deduplication, source failure reporting, context
compression, cache-filter isolation and zero embeddings. Existing search, framework
and speculative-executor regressions should run alongside them using
`scripts/test_offline.py` in an environment with application/test dependencies.

Production read tests on 8 November 2026 found three direct 2027 Health topics:

- `HORIZON-HLTH-2027-02-TOOL-01-TWO-STAGE` — predictive biomarkers using AI;
- `HORIZON-HLTH-2027-03-TOOL-04` — Virtual Human Twins;
- `HORIZON-HLTH-2027-03-TOOL-08` — frontier AI models for healthcare.

`HORIZON-BRIDGING-2027-02-05` is an additional broad opportunity, not a dedicated
AI-health topic. Do not inflate thematic relevance merely because its keyword list
contains both domains. A full agent test returned the three direct calls and
labelled the bridging call separately, with open/upcoming status and official links.

Backfill diagnostics and explicit repair:

```bash
docker exec map-it_sa-api-1 python /app/scripts/reembed_funding_calls.py --dry-run
docker exec map-it_sa-api-1 python /app/scripts/reembed_funding_calls.py --limit 500 --batch-size 20
```

A provider failure stops the job with a nonzero exit status; previously committed
valid batches remain usable and the next run resumes only missing vectors.
