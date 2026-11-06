# Pydantic AI migration validation

Validated on 2026-11-04 in `feat/pydantic-ai-agent`, based on freshly fetched
`origin/main` commit `f499cb88352c2e54edfc07d3aa6ddaace9f7260f`.
Codex wrote application code and tests. Antigravity (`agy`) executed pytest,
Ruff, the real inference smoke, and an independent source review.

## Ten scenarios repaired on 2026-11-06

All ten latest real model scenarios now pass, following a full run and a targeted
rerun of four affected questions. Antigravity independently rechecked the saved
answers and 13 covered tool contracts against source evidence. Total application
usage was 29 Codex attempts (28 completed, one earlier failed schema-validation
attempt), 895,594 known reported tokens plus that failure's unknown usage, and
eight embedding requests including preflights. The final offline suite passed
2,847 tests with two existing skips; Ruff passed on 19 affected Python files.

The actual production fixes address root JSON-schema references, query-relevant
document excerpts, duplicate ingestions and document filters. The evaluator now
supports explicitly capped embeddings and stricter source/citation checks.
[The detailed report](SCENARIO_VALIDATION_2026-11-06.md) records original failures,
exact final results, usage, artifacts and the SQL/HTTP/graph coverage limitations.

## Public activity summaries

Follow-up: the separate `agent_thinking` completion card with `action=observe`
was removed at the user's request. `tool_result` still carries the completion
summary, and action/review/final-answer activity remains. Antigravity verified
78 relevant offline tests (2.37 seconds), Ruff on the three affected Python
files, and `git diff --check`; all returned exit 0. No live text model run was
needed for this event-only change. The local host API was reloaded.

The shared V3/V4 framework now emits tool-specific public activity through the
existing `agent_thinking` event. Summaries describe validated call scopes, returned
counts, empty/failing calls, result review, validation feedback and final-answer
readiness. Matching tool events share a request-local call ID. These summaries
are constructed from execution metadata; no extra inference request or provider's
private reasoning is used.

Antigravity's initial focused run passed **102 tests**. The first complete run
reported **2,822 passed, 1 failed, 2 skipped**: the new validation-feedback test
found that Pydantic AI also represents retries as `ToolReturnPart(outcome=retried)`.
Detection was corrected to support that representation and `RetryPromptPart`.
The next focused activity run passed **16 tests** in 0.62 seconds.

Final complete verification used:

```bash
.venv/pydantic-agent/bin/python scripts/test_offline.py \
  --timeout=5 --timeout-method=signal --tb=short -p no:cacheprovider \
  --junitxml=.venv/activity-verified.xml \
  > .venv/activity-verified-tests.log 2>&1
```

Result: **2,823 passed, 2 skipped, 0 failures/errors, 416 warnings in 27.13 seconds**.
The existing missing-workflow checks account for the two skips. Tests use mocked
inference, tool outputs and storage; they include the real framework loop,
parallel-call correlation, hidden-thinking exclusion, empty/failed outputs,
no-tool acknowledgements, retry feedback and V3 SSE forwarding. They assert the
same model invocation count, without real model or database calls.
Ruff passed on the six affected Python files (exit 0). The authorized local host
API was restarted with the same Codex model and high reasoning effort to load the
activity update. No conversation was created for validation; the normal server
startup performs its existing short embedding health request.
Antigravity confirmed HTTP 200 for `/api/health/live` and `/api/health/ready`
after the restart, with `alive=true`, `ready=true`, PostgreSQL healthy and Codex
healthy. `git diff --check` returned exit 0. No persisted chat request was used.

## Repair for the reported `Test` response (2026-11-05)

Read-only runtime diagnosis established that the local API still mounted the
original main checkout, defaulted to Gemini, and had Codex disabled. Logs identified
`API_KEY_INVALID` for both reasoning and fallback synthesis. The two "thoughts"
and mechanical answer in the report matched hardcoded legacy fallback strings.
The separate embedding-key check passed after billing credit was added.

The feature branch now stops failed legacy generation, reports V3 failure through
SSE errors or HTTP 503, excludes failed assistant responses from atomic storage,
keeps framework answers without appending raw search hits, and filters unreadable
PDF chunks at retrieval time. Tests reproduce authentication failure, the original
page-number/underscore debris, partial evidence after model failure, short valid
answers, response-synthesis failure and route error contracts. Inference, retrieval
and storage in these tests are mocked; no real application records are modified.

Antigravity ran the full offline package suite:

```bash
.venv/pydantic-agent/bin/python scripts/test_offline.py \
  --timeout=5 --timeout-method=signal --tb=short -p no:cacheprovider \
  --junitxml=.venv/answer-fix-final.xml \
  > .venv/answer-fix-final-tests.log 2>&1
```

Result: **2,798 passed, 2 skipped, 0 failures/errors, 409 warnings in 28.25 seconds**.
The two skips are existing missing-workflow checks. Execution used Python 3.12;
Python 3.11 remains unverified. An earlier focused run passed 89 tests, and an
earlier complete run passed 2,797 tests before the final synthesis regression.
Antigravity checked the 12 affected Python paths with Ruff: **All checks passed,
exit 0**. `git diff --check` also returned exit 0.
An additional Antigravity prose-review session exceeded its 90-second print
timeout without returning findings; that review is not claimed as completed.
The completed test/lint session is recorded separately in
`.venv/antigravity-answer-fix-final.json`.

Antigravity also ran the disposable `.venv/smoke_test_acknowledgement.py` once.
It used the actual framework and all 42 research-tool definitions, real Codex
`gpt-6.1-sol` with high reasoning effort, dummy application settings, disabled
dotenv, disabled persistence and a one-request budget. The exact user input was
`Test`. The answer was:

> Test received. Ready to help with EU funding research and proposal writing.

Result: **passed; 1 completed model request, 0 tool executions, 0 failures**.
Reported usage: **31,018 input + 79 output = 31,097 tokens**. No API-key model,
embedding request, database connection or existing conversation was used. This
checks one acknowledgement through the in-process agent, not production HTTP,
all ten funding scenarios or the currently running Docker service. The full
tool catalog remains a substantial input cost even for a short acknowledgement.

Application code and private environment files in the original checkout were not
edited, and the running local API was not replaced during this repair validation.

## Approved local API switch to Codex

After the user approved replacing the local API, Codex added
`scripts/run_local_api.py` and eight offline launcher tests. Antigravity verified
all eight tests and Ruff for the two new Python paths (exit 0). The launcher keeps
the existing private configuration file intact and applies provider/local-port
settings only to the host API process. API-key providers remain selectable.

Preflight resolved all **20 named text steps to Codex**, selected
`gpt-6.1-sol` with **high** reasoning effort, verified the official CLI's ChatGPT
login, found the reference funding project through read-only SQL and pinged Redis.
The separate Google embedding model remains `gemini-embedding-001`, 3,072 dimensions.

The branch was first staged on loopback port 18001; Antigravity verified HTTP 200
and `alive=true`. The old `map-it_sa-api-1` container was then stopped, and this
branch's host process took over loopback **port 18000**. Data-service containers
were kept running. The temporary staging API was shut down after final verification.

Antigravity's actual HTTP checks on port 18000 returned:

- `/api/health/live`: HTTP 200, `alive=true`.
- `/api/health/ready`: HTTP 200, `ready=true`.
- `/api/health/dependencies`: HTTP 200; PostgreSQL, Neo4j, Redis, Codex,
  embeddings and Supabase all `healthy`; provider `codex`, model `gpt-6.1-sol`.
- Startup log checks: startup complete, embedding test passed, no exception types.

These checks made no new text-generation requests or chat POSTs. They used official
CLI availability/login checks and embedding health requests. Two server startups
and the final dependency probe each performed the existing short embedding check.
No existing conversation, profile, proposal or funding record was modified by
validation. The earlier real Codex acknowledgement smoke remains the inference
evidence; a persisted HTTP conversation was deliberately not created.

The full suite after the launcher addition used:

```bash
.venv/pydantic-agent/bin/python scripts/test_offline.py \
  --timeout=5 --timeout-method=signal --tb=short -p no:cacheprovider \
  --junitxml=.venv/local-api-final.xml \
  > .venv/local-api-final-tests.log 2>&1
```

Result: **2,806 passed, 2 skipped, 0 failures/errors, 409 warnings in 35.10 seconds**.
Tests mock external responses; this remains separate from the real HTTP health
checks and earlier real Codex smoke. Restart and rollback commands are in
[the host API instructions](PYDANTIC_AI_AGENT.md#host-api-with-the-existing-local-docker-services).
The API is a detached host process, not an operating-system startup service;
its PID/log are `.venv/local-api.pid` and `.venv/local-api.log`.

## Compact source-backed suite replacing bulk live tests

The user requested removal of the bulk live-response suite after reviewing its
usage cost. The replacement has 52 explicit tool contracts and 10 representative
question families. The offline tests remain. Retirement removed 942 live test
functions (1,014 parameterized service-dependent cases), 40 collection-time
API/model probes, 35 live-only pytest modules and nine standalone bulk runners.
See [the retirement inventory](../tests/RETIRED_LIVE_TESTS.md).

Antigravity ran the replacement against independently queried funding records:

```bash
.venv/pydantic-agent/bin/python scripts/evaluate_tools.py --mode questions \
  --max-requests 30 --model gpt-6.1-sol --effort high \
  --output /tmp/mapit-tool-live.json > /tmp/mapit-tool-live.log 2>&1
```

Actual result: **31 tool contracts passed, 21 blocked**; **2 answer scenarios
passed, 7 failed, 1 blocked**. Exit 1. This is not a full live-suite pass.
The first two answers correctly gave IMAGHyNE's exact EU contribution, total
cost and coordinator, then its full 42-organization/five-country consortium.
Each used two real Codex requests and successful source-verified Python tools.

All seven subsequent answer failures were Codex CLI exit status 1, with no final
answer. The adapter's bounded diagnostic identifies login/connectivity/model/
sandbox checks; the evidence does not establish which caused these exits.
They are provider failures, not proof that seven underlying tools returned bad
data. No automatic model rerun was performed. The runner was subsequently changed
to stop after the first provider failure and mark later questions unattempted.

Usage: **11 attempted Codex generations**, **4 completed**, **7 failed**. The
completed requests reported **129,636 tokens** (129,154 input, 482 output).
Usage for the seven failures is unknown, so 129,636 is the known reported sum,
not a complete consumption or billing total. No API-key generation or new
embedding endpoint was used. Codex/Antigravity coding and validation orchestration
have their own usage, separate from these application request counts.

The 21 blocked tool contracts comprise graph-dependent paths, new embeddings or
document-vector retrieval, deliberately unselected AI-generating direct tools,
and missing full proposal call-requirement services. Stored project-vector
similarity was tested without generating a new embedding. Proposal navigation
and status used disposable in-memory state; funding SQL was read-only. No
existing conversation, profile, proposal or funding record was modified.

Earlier zero-model runs caught both harness mismatches and application bugs:
the first returned 21 passed/10 failed/21 blocked; the second returned
29 passed/3 failed/20 blocked. Fixes include structured call retrieval remaining
available without an embedding key; date-based filtering of open cross-programme
calls; forwarding `strict_match` in call-history SQL; blank quality inputs scoring
zero; and unavailable compliance checks no longer claiming compliance. The new
checker also caught mismatched SQL scopes and transport date/key normalization
in its own fixtures. Those were corrected against independent queries, not by
changing expectations to arbitrary tool output.

Antigravity's final offline run on 2026-11-05 used:

```bash
.venv/pydantic-agent/bin/python scripts/test_offline.py \
  --timeout=5 --timeout-method=signal --tb=short -p no:cacheprovider \
  --junitxml=/tmp/mapit-compact-final.xml \
  > /tmp/mapit-compact-offline-final.log 2>&1
```

Result: **2,767 passed, 2 skipped, 0 failures/errors, 399 warnings in 30.20
seconds**. JUnit records 2,769 collected cases. The two skips are existing checks
for a removed workflow. No bulk live pytest tests remain to be accidentally
selected. This includes the new budget, source-reader, transport, checker,
counterexample, planning and production regression tests with mocked I/O.

The final changes also add the optional `--max-reported-tokens` stop and prevent
later questions from running after a Codex provider failure. Those changes were
verified offline; no additional model calls were made to retest provider access.
Antigravity checked all changed/new Python paths with Ruff; one import-grouping
finding in `tests/test_tool_scenario_runner.py` was corrected, and its recheck
returned **All checks passed, exit 0**. `git diff --check` passed as well.
Commands and limitations are in [TESTING.md](TESTING.md) and
[TOOL_SCENARIO_COVERAGE.md](TOOL_SCENARIO_COVERAGE.md). This transport evaluates
the real in-process tools and framework, not the deployed HTTP/storage stack.

## Earlier complete offline run after initial test repairs

Antigravity ran the entire repaired inventory with:

```bash
.venv/pydantic-agent/bin/python scripts/test_offline.py \
  --timeout=5 --timeout-method=signal --tb=short -p no:cacheprovider \
  --junitxml=/tmp/mapit-repaired-final.xml \
  > /tmp/mapit-repaired-suite-3.log 2>&1
```

Result: **2641 passed, 1016 skipped, 0 failed, 0 errors, 449 warnings in
33.65 seconds; exit 0**. JUnit records 3657 collected cases, zero failures and
zero errors. This used Python 3.12. Python 3.11 execution remains unverified.

Of the 1016 skips, **693** carry the explicit new `live` marker. The other
**323** are existing prerequisite skips, mostly unavailable live APIs, plus two
legacy checks for a removed workflow. Skipped live checks were not validated.
The original 904 failures/44 errors are not being reported as 948 unchanged
tests now passing: stale architecture tests were replaced and real-service tests
were classified. For example, the old self-correction module had 52 test
functions for the removed evaluator stack; it now has 7 functions parameterized
into 11 cases against current framework behavior and retained live scenarios.

The repairs cover temporary report outputs, current report schemas, moved
documentation/source paths, current preprocessing imports/settings, isolated
agent construction, existing quality rubrics and date-relative deadline fixtures.
Actual timeout bugs were fixed in `country_statistics.py`, `similar_projects.py`
and the async similar-project tool wrapper. Controlled worker tests verify the
wait returns or cancels while a worker is blocked, then release that worker.

`make test` now runs the guarded offline runner; CI uses it as a blocking test
step and uploads JUnit output even on failure. Actual live tests require
`--run-live`, and `make test-live` selects that tier. Five global Redis
`FLUSHALL` subprocesses were removed from live scenarios. No live service/data
operations were performed during these repairs.

Antigravity ran Ruff across every changed/new Python file with
`.venv/pydantic-agent/bin/ruff check --no-cache <changed Python paths>`:
**All checks passed; exit 0**. The exact path list and tool output are retained
in the local ignored `.venv/antigravity-repaired-final.jsonl` log.
Codex's `git diff --check` also passed.

The guard was checked separately:

```bash
.venv/pydantic-agent/bin/python scripts/test_offline.py \
  --run-live tests/test_offline_guards.py --collect-only -p no:cacheprovider
```

It correctly rejected the incompatible selection with
`--run-live cannot be used with scripts/test_offline.py`; **exit 4**.

Earlier repair runs stopped first at one collection syntax error, then at
2 failed/2639 passed/1015 skipped. Those intermediate results were corrected
before the final run above. Remaining live prerequisites and commands are in
[TESTING.md](TESTING.md).

## Initial focused tests

Antigravity ran this command after the final review fixes:

```bash
.venv/pydantic-agent/bin/python scripts/test_offline.py \
  tests/test_pydantic_agent_runtime.py tests/test_pydantic_agent_models.py \
  tests/test_offline_guards.py tests/test_codex_adapter.py \
  tests/test_codex_catalog.py tests/test_codex_chat_wiring.py \
  tests/test_codex_proposal_wiring.py tests/test_codex_service_wiring.py \
  tests/test_conversation_namer.py tests/test_text_provider_status.py \
  --tb=short -p no:cacheprovider
```

Result: **178 passed, 86 warnings in 6.35 seconds; exit 0**. Warnings include
existing Pydantic configuration, Google SDK, PyPDF2 and pytest-asyncio deprecations.
The environment used Python 3.12 and an isolated `.venv/pydantic-agent`.

The new framework tests cover strict argument validation and correction, tools
and final output, run limits, cancellation, request/provider isolation, proposal
events and official guidance, all 52 registered tool schemas, client cleanup,
missing legacy model hints, empty dispatch results, and unchanged dispatch defaults.
OpenAI, OpenRouter and Gemini round trips use the actual framework model adapters
with mocked SDK responses. Codex protocol unit tests also mock inference.
These are offline tests, not paid API or live database validation.

Antigravity also ran:

```bash
.venv/pydantic-agent/bin/ruff check --no-cache \
  app/core/config.py app/services/agents/framework \
  app/services/agents/tool_registry.py app/services/agents/tool_aware_agent.py \
  app/services/agents/proposal_aware_agent.py \
  app/services/conversation/conversation_manager.py scripts/test_offline.py \
  scripts/smoke_pydantic_agent.py tests/test_pydantic_agent_runtime.py \
  tests/test_pydantic_agent_models.py
```

Result: **All checks passed; exit 0**. Codex's `git diff --check` passed too.

## Initial complete suite before repairs

Antigravity ran the complete suite through the guarded runner:

```bash
.venv/pydantic-agent/bin/python scripts/test_offline.py \
  --timeout=3 --timeout-method=signal --tb=line -p no:cacheprovider \
  > /tmp/mapit-pydantic-full-suite.log 2>&1
```

Result: **904 failed, 2409 passed, 352 skipped, 44 errors, 1168 warnings in
326.33 seconds; exit 1**. This is a failed full-suite run. No new framework test
appeared in its failed/error summary. It preceded the final small defensive
guards; the focused run above includes those changes.

Observed failure categories:

- Live PostgreSQL, Redis, HTTP and model access rejected by the offline runner.
  Some dependent tests hit the explicit three-second timeout.
- Fixtures attempting to write `tests/quality/results/...` were rejected by
  Antigravity's read-only sandbox.
- Tests import deleted `app.services.agents.result_evaluator` and
  `app.services.agents.agentic_manager` modules.
- Tests expect absent `docs/CONVERSATION_STABILITY_ARCHITECTURE.md` and
  `.github/workflows/conversation-tests.yml` files.
- Other quality/legacy assertions failed. No equivalent full-suite baseline was
  run on `main`, so this report does not classify every failure as pre-existing.

An earlier collection attempt stopped with 34 missing-`aiohttp` errors. After
installing that test dependency in the isolated environment, the complete run
above reached execution. No live service access was enabled to make tests pass.

## Real Codex smoke

Antigravity executed this separately from mocked pytest:

```bash
.venv/pydantic-agent/bin/python scripts/smoke_pydantic_agent.py \
  --model gpt-6.1-sol --reasoning-effort high
```

Result: **exit 0**, requested provider `codex`, model `gpt-6.1-sol`, effort `high`.
The real framework/CLI round trip invoked both registered Python tools,
`add_numbers` and `synthetic_record`. Validated output contained
`marker=FRAMEWORK_OK`, `total=5`, and the exact unpredictable record ID
`synthetic-3c929b9c-3af3-4661-a3f7-86fc3583eacf` generated by the Python tool.
The smoke used synthetic data and no application settings or funding database.

## Review and limits

Antigravity's source review prompted guards for base-agent proposal context,
an absent legacy model hint, and an empty dispatcher result. Regression tests
cover those paths. Earlier inspection also fixed request-local model selection,
Google HTTP client cleanup, and cancellation finalization.

Two review claims were rejected against code/dependency evidence: `httpx2` is
an explicit Pydantic AI 2.66 dependency, and providers are constructed once per
agent run, not once per model iteration. Strict integer rejection is intentional.

Live API-key inference, Python 3.11 execution, full application deployment,
database-backed proposal mutations, and answer-quality improvement were not
validated. Codex remains dependent on an installed, authenticated host CLI.
Embeddings retain the existing Google configuration and dimensions. Completed
answer chunks retain the current app contract; they are not live token streaming.

## Changed paths

- `app/services/agents/framework/{__init__,models,request_state,runtime,tool_schemas}.py`:
  shared framework runtime, native API/custom Codex models, request state and schemas.
- `app/services/agents/{tool_aware_agent,proposal_aware_agent,tool_registry}.py`:
  V3/V4 integration, rollback, metadata and proposal tools/events.
- `app/services/conversation/conversation_manager.py`: framework/error metadata.
- `app/core/config.py`, `.env.example`: engine selection and execution limits.
- `requirements.txt`, `requirements-dev.txt`: framework and test dependencies.
- `scripts/test_offline.py`, `scripts/smoke_pydantic_agent.py`: transport guards and smoke.
- `tests/test_pydantic_agent_{models,runtime}.py`: synthetic protocol/integration coverage.
- `README.md`, `docs_tracked/PYDANTIC_AI_AGENT.md`, this report: configuration and evidence.

The subsequent repairs also change `Makefile`, `.github/workflows/ci.yml`,
`pyproject.toml`, `app/services/agents/tool_executors.py`,
`app/services/tools/{country_statistics,similar_projects}.py`,
`tests/conftest.py`, `tests/agent_test_support.py`, `tests/quality/conftest.py`,
and affected scenario/unit/report tests. Details are in
[TESTING.md](TESTING.md); no database migrations or real configuration/data files
are changed.

Enable the engine with `AGENT_FRAMEWORK=pydantic`; select an API provider or Codex
using the existing provider settings documented in
[PYDANTIC_AI_AGENT.md](PYDANTIC_AI_AGENT.md). Explicit rollback is
`AGENT_FRAMEWORK=legacy`. No running process configuration was changed.
