# Testing MAPIT without unbounded model usage

## Offline tests

```bash
make test
make test PYTHON=.venv/pydantic-agent/bin/python \
  PYTEST_ARGS="--timeout=5 --tb=short -p no:cacheprovider"
```

The offline runner supplies dummy settings, disables dotenv, and blocks network,
database and service subprocess access. Model responses are mocked. Running these
application tests makes zero real model requests. Codex/Antigravity used to build
and validate code consume their own separate usage.

The former bulk live suite was removed at the user's request: 942 test functions,
representing 1,014 service-dependent parameterized cases, plus standalone bulk
runners and collection-time API/model probes. Offline tests were retained.
[The retirement inventory](../tests/RETIRED_LIVE_TESTS.md) lists the files.
Generated unit-test reports use temporary directories, leaving recorded inputs intact.

## Source-backed tool checks

```bash
# Inspect the evidence and 52-case/10-question plan. No model calls.
.venv/pydantic-agent/bin/python scripts/evaluate_tools.py --mode plan

# Run actual Python tools against read-only funding records. No model calls.
make test-tools PYTHON=.venv/pydantic-agent/bin/python

# Select a tool contract:
make test-tools PYTHON=.venv/pydantic-agent/bin/python \
  EVAL_ARGS="--case get_project_details --output /tmp/project-contract.json"
```

The default source is the already running local `supabase_db_supabase_cli`
PostgreSQL container. `--container` selects another local container with the same
schema. The default profile uses no application DSN, real `.env`, auth files,
database dump or API keys. Every query is a funding-table SELECT in a read-only transaction with
statement/lock timeouts and rollback. Private user, conversation, profile and
proposal tables are outside the allowed source set.

Independent SQL obtains expected records first. The real tool implementations
and repositories then execute their own SQL through a limited psql/DB-API bridge.
Only the transport changes; tool results are not mocked. Exact identifiers,
amounts, partner rows, counts, deadlines and arithmetic are checked against the
independent evidence. The bridge preserves column order, decimals and native
calendar dates; it is not a full production DB-API compatibility test.

Proposal navigation/status use actual state classes in a disposable in-memory
session. Pagination uses a disposable cache seeded from verified funding records.
No existing conversations, profiles, funding rows or proposals are modified.

## Bounded real model questions

```bash
# Ten question families. Shared maximum: 30 model invocations, including helpers.
make test-live PYTHON=.venv/pydantic-agent/bin/python

# Include the real document scenario using the configured embedding endpoint:
make test-live PYTHON=.venv/pydantic-agent/bin/python \
  EVAL_ARGS="--allow-embeddings --runtime-env-file ../MAP-IT_SA/.env --max-embedding-requests 4"

# Spend less by selecting one scenario and a smaller request allowance:
make test-live PYTHON=.venv/pydantic-agent/bin/python \
  EVAL_ARGS="--scenario project_facts --max-requests 3 --output /tmp/project-answer.json"

# Optional stop after the reported token total reaches this threshold:
make test-live PYTHON=.venv/pydantic-agent/bin/python \
  EVAL_ARGS="--max-reported-tokens 100000"
```

Default generation is the authenticated host Codex CLI with `gpt-6.1-sol`, effort
`high`. The runner isolates settings for its process; it does not change the app's
provider setup. It allows only Codex generation and blocks paid API fallbacks.
`--model` and `--effort` select other explicitly available host CLI settings.
Missing CLI/login/access fails; no alternative provider is selected.

One budget surrounds all scenarios, direct tools and helper calls. It counts
attempts before dispatch across threads/tasks and does not charge nested facade
and transport wrappers twice. It stops before request N+1. Failed and cancelled
attempts count too. Reported token thresholds stop subsequent requests; they
cannot limit unknown usage inside an in-flight request. SDK-internal retries are
not separate application invocations. Failed requests may have unknown usage.
The runner stops after a Codex provider failure rather than trying every remaining
question, and never automatically reruns a failed real-model evaluation.

The full registry/tool descriptions remain available during answer evaluation.
In the first real run these required roughly 31,000 input tokens per model call.
A 30-request ceiling therefore does not imply a small token bill or a known
percentage of subscription allowance. Select a few scenarios and inspect usage
before expanding the run. No AI judge adds hidden grading requests.

Direct checks run first. Question mode checks the 13 tools required by the ten
questions, or the tools required by the selected subset. Contract mode still
checks all 52 registrations by default. An explicit `--case` selection must
include each selected question's required tools, otherwise that question is
blocked rather than bypassing preflight. An agent question is blocked if its required tool or
source prerequisite failed. The answer must use successful tool results and carry
known facts correctly, including amounts bound to their labels and units.
A correct-looking answer cannot conceal empty or wrong tool output.

Graph paths, new embedding generation, document-vector retrieval, and full
proposal writing/compliance backends are explicit prerequisites. The default
safe runner does not connect these services. Stored project-to-project vectors
can be compared without a new embedding request. Missing capabilities are
reported as **blocked**, not passed. `--include-model-tools` explicitly opts into
AI-generating direct contracts under the same request budget; it does not supply
missing graph/embedding/proposal services.

`--allow-embeddings` and `--runtime-env-file` together opt into document embeddings.
The normal dotenv loader consumes the private runtime configuration; only the
dedicated `GOOGLE_EMBEDDING_API_KEY`, embedding model and dimension are retained
inside the isolated evaluation. Generation API keys and arbitrary runtime secrets
are discarded, and the Codex child environment retains its existing minimal
allowlist. The private file is not modified or printed.

`--max-embedding-requests` sets a separate cap (default 8). SDK retries are disabled,
requests have a 20-second timeout, and repeated queries use an in-memory cache
only. An endpoint failure is not retried automatically. Reported embedding token
usage is unknown. The actual application embedder, vector service and existing
search RPCs execute; the RPC transport runs through rolled-back read-only SQL
instead of HTTP. This does not validate the Supabase HTTP transport or enable
graph/proposal backends. Returned document IDs, passages, titles and pages are
checked against independently selected/read stored source rows.

Reports separate tool-contract counts from the ten question outcomes, retain
actual call parameters/results for diagnosis, and include per-question generation
usage plus the embedding allowance totals. The project-search question explicitly
requests `search_projects` so its intended agent tool path is exercised.

This evaluator exercises the real agent loop and tools in-process. It does not
claim HTTP routing, persistent conversation storage, deployment, every tool
variant or every missing backend has been validated.

## Reports and exit codes

The default JSON report is `/tmp/mapit-tool-evaluation.json`; `--output` changes
it. It records independently selected evidence, each tool/scenario outcome,
answer checks, provider/model request counts, known token totals and unknown
usage. Checkpoints preserve completed work if interrupted.

- **0:** all selected checks passed, or evidence-only planning completed.
- **1:** a check failed, an error occurred, or the inference run stopped.
- **2:** selected coverage is incomplete because prerequisites are blocked.

A full 52-tool matrix is a coverage plan, not a claim of 52 functional passes.
Read [the coverage map](TOOL_SCENARIO_COVERAGE.md) and
[actual validation results](PYDANTIC_AI_VALIDATION.md).
