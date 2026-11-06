# Pydantic AI agent migration

Branch `feat/pydantic-ai-agent` was created from freshly fetched `origin/main`
at `f499cb88352c2e54edfc07d3aa6ddaace9f7260f`. The original `main` checkout is
not changed by this worktree. This branch changes the agent engine; the provider
selection settings remain independent.

## Configuration

```bash
AGENT_FRAMEWORK=pydantic
# Explicit rollback to the previous ReAct loop:
# AGENT_FRAMEWORK=legacy

AGENT_MODEL_TIMEOUT_SECONDS=30
AGENT_RUN_TIMEOUT_SECONDS=300
AGENT_TOOL_TIMEOUT_SECONDS=60
AGENT_MAX_TOOL_CALLS=20
AGENT_TOOL_RESULT_MAX_CHARS=20000
```

The framework is the default in this branch. Existing global, named-step, and
request provider overrides still apply. Native agent calls to OpenAI, Gemini and
OpenRouter use their configured API keys. Codex is a development model adapter
implementing the same framework protocol and running the same Python tools.

```bash
# An API-based setup:
DEFAULT_AI_PROVIDER=gemini
# Supply GEMINI_API_KEY privately in the actual runtime environment.

# Or personal local Codex development:
# DEFAULT_AI_PROVIDER=codex
# CODEX_ENABLED=true
# CODEX_MODEL=gpt-6.1-sol
# CODEX_REASONING_EFFORT=high
```

No framework-hosted service, tracing account or additional provider is required.
There is no automatic fallback to another provider if the selected agent model
fails. `AGENT_FRAMEWORK=legacy` is an explicit rollback, not an error fallback.
The real `.env`, credentials, running API and workers are not changed by editing
this branch. Install its requirements and restart processes to run the migration.

## What changes

The common runtime in `app/services/agents/framework/runtime.py` uses Pydantic AI
to choose Python tools, validate their inputs, execute independent calls, return
results to the model, and validate the final answer. Native APIs use function-call
messages rather than extracting and repairing JSON from answer text.

All 42 V3 research tools and 10 V4 proposal tools have strict input schemas.
Unknown keys, invalid types, and configured numeric bounds are rejected before
dispatch. The model gets validation feedback and one correction retry. Optional
arguments are omitted before dispatch so existing tool defaults still apply.
Budget and text-validator tools can receive invalid/empty user data when their
purpose is to report those violations. New registry extensions must provide a
Pydantic `Tool.input_model` or an explicit entry in the schema catalog.

Business tools, SQL/search logic, proposal services, embeddings, storage, and
response formatting remain application responsibilities. The existing dispatcher
continues to handle parameter normalization, result caching and analytics.
Successful plan caches are hints to the new agent, not commands to execute.
The same request limit as the previous agent's `max_iterations` bounds model
round trips, with an additional tool-call count and a wall-clock run timeout.
Tool results retained for API/storage are complete; a bounded preview is returned
to the model for oversized results.

Proposal mutations are sequential. Research-only calls can execute concurrently.
The proposal tool list includes `mark_section_status`, which the old dispatch
classification omitted. Per-request context variables isolate conversation IDs,
proposal session IDs, selected models, and generation metadata on shared agents.

## Provider boundary

`models.py:model_for_step` resolves MAPIT's existing provider selection for each
run. Gemini flash/pro selection still applies only to Gemini. API clients receive
explicit configured keys/endpoints and are closed at the end of the run.

`CodexAgentModel` translates framework message history, tool definitions and
validation feedback to a structured inference request through `CodexTextModel`.
It translates the validated response to the same function-call messages used by
API providers. Python tools execute in MAPIT, never inside the CLI job. The CLI's
read-only isolation, disabled shell/connectors, minimum environment and process
cancellation cleanup are retained. No framework OAuth/Codex backend or direct
token handling is introduced. The rest of the agent is not specific to Codex.

## Response compatibility

V3/V4 retain `agent_thinking`, `tool_call`, `tool_result`, `section_update`,
`agent_complete`, `token`, and `complete` event shapes used by their existing
routes. Progress text describes execution stages, not private model reasoning.
Tool events arrive during execution; final answer text remains completed-message
chunks. The migration does not claim live Codex token streaming.

The shared V3/V4 runtime emits public activity summaries through the existing
`agent_thinking.thought` field. These describe actual execution, not the model's
private reasoning. Examples include looking up a named project, checking a
country's funding statistics, drafting a specified section, and reporting the
number of returned partners or document excerpts. They are derived locally from
validated tool arguments and actual outcomes; they require no extra model calls.

Activity events add `stage`: `reviewing`, `retrying`, `tool_started`,
`answer_ready` or `failed`. Completion stays on `tool_result`; a separate
`agent_thinking` card with `action=observe` is not emitted. Tool-related events include a
request-local `call_id`, also present on the matching `tool_call` and `tool_result`.
The tool call's `reasoning` field contains its public action summary, and the
result adds `activity_summary`. Parallel calls keep separate IDs. Completion
counts describe returned lists, not an inferred total beyond the returned data.
Failed calls and empty outputs are stated explicitly. Retrying describes tool
argument or output-format validation feedback without reproducing that payload.

The same action summaries are stored in the existing reasoning-step fields.
Document bodies and proposal text fields are not copied into activity summaries;
search labels are bounded, reduced to one line and stripped of markup. The final
`answer_ready` event is emitted only after structured answer validation succeeds.
Existing clients that render `agent_thinking.thought` need no event-type changes.

Results include `agent_framework` and a content-free `agent_error` when the run
fails or reaches its limit. Partial successful tool results remain available for
existing application formatting. Confidence is a model estimate, not a measured
probability or a quality benchmark.

## Generation failures and document debris

The reported `Test` response exposed a failure in the running main checkout:
Gemini rejected generation with `API_KEY_INVALID`, and the legacy loop replaced
model reasoning with a fixed document search and a mechanical answer carrying
0.7 confidence. A working Google embedding key does not validate Gemini generation
credentials. The running service's provider settings are separate from this branch.

This branch stops legacy reasoning failures instead of searching automatically.
Both agent engines return failed generation with zero confidence. V3 sends an
SSE `error` with `stage=generation`, or HTTP 503 for a non-streamed request;
it does not store a failed response as a successful assistant answer or issue a
second synthesis request. Diagnostics identify authentication, quota and timeout
failures without exposing SDK payloads, uploaded text or credentials.

The conversation manager preserves a validated framework answer. It does not append
every raw tool result or regenerate short acknowledgements and plain Markdown.
Legacy response synthesis uses the configured `chat_response` model rather than
forcing `gemini-1.5-flash`; its failures also propagate instead of returning debris.

Document retrieval rejects standalone page numbers, punctuation and form separators
before returning evidence. It removes control characters and long underscore lines,
preserves substantive short funding statements, amounts and tables, and reports the
usable result count. The document tool fetches extra candidates before applying its
display limit and runs blocking retrieval outside the event loop. Existing stored
chunks and 3,072-dimensional embeddings are unchanged. These checks do not establish
semantic relevance for every retained passage or repair the underlying PDF ingestion.

Restarting the original checkout does not activate these changes. The API process
must run this branch with its dependencies installed. For local Codex generation,
use the existing `DEFAULT_AI_PROVIDER=codex`, `CODEX_ENABLED=true`,
`CODEX_MODEL=gpt-6.1-sol`, `CODEX_REASONING_EFFORT=high` and
`AGENT_FRAMEWORK=pydantic` settings. Request and named-step overrides still take
precedence. The official CLI must be installed and authenticated on the host that
runs the API; the current Docker image does not provide that integration.

## Host API with the existing local Docker services

`scripts/run_local_api.py` runs this checkout on the host so the official Codex
CLI can use its existing login. It loads private configuration through the normal
application dotenv loader; it does not copy or rewrite that file. Provider and
connection overrides last only for the launched process.

From this worktree, use the configuration file that belongs to the existing app:

```bash
.venv/pydantic-agent/bin/python scripts/run_local_api.py \
  --env-file ../MAP-IT_SA/.env \
  --provider codex --model gpt-6.1-sol --reasoning-effort high \
  --local-services --port 18000 --check

# Stop the old API container before binding its port. Keep its data services running.
docker stop map-it_sa-api-1
.venv/pydantic-agent/bin/python scripts/run_local_api.py \
  --env-file ../MAP-IT_SA/.env \
  --provider codex --model gpt-6.1-sol --reasoning-effort high \
  --local-services --port 18000
```

`--check` performs no model inference. It checks Codex CLI support/login, one known
funding project in a read-only SQL transaction, and Redis ping. `--local-services`
uses the existing published PostgreSQL 54322, Supabase 54321, Neo4j 17687 and Redis
16379 ports on loopback. Individual `--*-port` arguments support different local
port mappings. Database identity/authentication and the embedding key remain from
the existing runtime configuration; secret values are not printed.

`--provider gemini`, `openai` or `openrouter` selects an API provider instead;
`--model` selects that provider's model. Named-step and request overrides retain
their precedence. No user/profile setting, Docker image, Compose file or operating
system startup setting is changed. The host process must be relaunched after a
reboot. To roll back, stop the host process and run `docker start map-it_sa-api-1`;
starting the original checkout's container restores its original provider setup.

## Dependencies and validation

See [the validation report](PYDANTIC_AI_VALIDATION.md) for exact commands,
Antigravity results, the failed full-suite run and the real Codex smoke.

This branch pins `pydantic-ai-slim[openai,google]==2.66.0`, requiring newer OpenAI,
Google GenAI, and Pydantic packages. Use an isolated environment when evaluating
it. Existing Google embeddings keep their configured model and dimensions.

Codex writes the implementation and test cases. Antigravity (`agy`) executes
the independent tests and review. Only use the offline runner for automated
tests; legacy tests include direct service subprocess commands.

```bash
.venv/pydantic-agent/bin/python scripts/test_offline.py \
  tests/test_pydantic_agent_runtime.py tests/test_pydantic_agent_models.py --tb=short
```

The tests use synthetic model/tool responses and do not prove better funding
answers. Comparing response quality requires a provisioned evaluation with the
same questions, model, and data on both engines.

The synthetic real-Codex round-trip smoke is separate from offline pytest:

```bash
.venv/pydantic-agent/bin/python scripts/smoke_pydantic_agent.py \
  --model gpt-6.1-sol --reasoning-effort high
```

It only adds two integers and retrieves a generated in-memory record ID. It
does not load app settings, read real `.env`, or connect to a database.

References: [Pydantic AI function tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/),
[model interface](https://pydantic.dev/docs/ai/models/overview/).
