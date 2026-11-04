# Codex provider implementation and verification

Worktree: `/home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA-codex-provider`.
Branch: `feat/codex-ai-provider`. Implementation base: `9c0b36c53811050a548c77e4e549f4ca31b4b3b1`.
Verification was completed before committing. The user subsequently authorized committing and
pushing this feature branch. No deployment, database migration, credential edit, or profile/settings
change was made.

The shared factory routes text generation through request, named-step and global selections.
Twenty identifiers cover chat reasoning/response/preprocessing, memory, naming, planning,
call documents/history, and proposal drafting/review/analysis. See
[setup and exact precedence](CODEX_LOCAL_PROVIDER.md). Google embeddings remain unchanged.
`jsonschema>=4.18.0` is the single new runtime dependency, for local structured-response validation.

The CLI adapter uses stdin, minimum environment variables, isolated temporary directories,
POSIX child-process groups, timeout/cancellation cleanup, and read-only ephemeral jobs.
It disables executable capabilities in a temporary copy of the installed CLI's bundled catalog
without changing model IDs, order or defaults. An auth-free local prompt dry run checks
that no executable tools remain. Unsupported catalog/tool formats fail before inference.
Only the inert `functions.request_user_input` UI function remains in tested CLI 0.165.0.
No hook-trust or sandbox bypass is used.

## Data constraint incident

The first offline runner blocked Python service connections but did not block subprocesses.
Legacy quality tests contain `docker exec map-it_sa-redis-1 redis-cli FLUSHALL`; those subprocesses
could run against the already running Redis container. A subsequent read-only `INFO commandstats`
reported `cmdstat_flushall:calls=50,...,rejected_calls=0,failed_calls=0`. No pre-run count was captured,
so the number attributable to this task and the cleared Redis contents cannot be established.
This violated the user's no-data-changes constraint. No attempt was made to reconstruct or write
Redis data. The runner now rejects external subprocesses, Docker, shells and service CLIs, while
allowing only its generated fake CLI and missing-executable error tests. Guard regression tests
exercise harmless Docker-version and shell commands and verify rejection before execution.

An early chat regression run also produced Google invalid-dummy-key responses: native gRPC bypassed
the original Python socket guard. That runner had cleared inherited credentials and supplied an
explicit dummy key. Google SDK generation/embedding/list methods are now blocked as well.

## Verification

The original venv had application dependencies but no pytest or Ruff. Tests use an isolated
Python 3.12 environment with a read-only import path to that venv's installed packages.
After verification, the isolated test environment was moved into ignored `.venv/codex-tests/`.
Use `.venv/codex-tests/bin/python scripts/test_offline.py ...` to rerun it. Historical commands
below preserve the paths used when the tests ran. The final tool versions are pytest 8.3.2 (repository development pin), pytest-asyncio 0.24.0,
pytest-timeout 2.4.0 and Ruff 0.6.9 (repository development pin).
The runner clears inherited environment variables, supplies explicit dummy settings, disables
dotenv loading, and blocks external services. No real inference is part of the automated tests.
Adapter lifecycle tests launch a generated synthetic CLI to exercise real OS process behavior.

Final focused command:

```bash
.venv-test/bin/python scripts/test_offline.py tests/test_offline_guards.py \
  tests/test_codex_adapter.py tests/test_codex_catalog.py tests/test_codex_chat_wiring.py \
  tests/test_codex_proposal_wiring.py tests/test_codex_service_wiring.py \
  tests/test_conversation_namer.py tests/test_text_provider_status.py --tb=short
```

Result: **148 passed, 64 dependency/fixture deprecation warnings, 4.26 seconds**.
Breakdown: adapter 52, catalog 15, chat 10, proposal 13, service wiring 9,
existing conversation naming 41, API/status 6, offline guards 2.
All inference/storage responses are mocked; subprocess lifecycle cases run a synthetic executable.
Final guarded full-suite command:

```bash
.venv-test/bin/python scripts/test_offline.py --timeout=5 --timeout-method=signal --tb=short
```

Result: **2,519 passed, 769 failed, 352 skipped, 37 errors, 1,145 warnings, 336.38 seconds**.
No Codex/provider-status/conversation-naming tests failed in that run. These are offline results,
not an integration pass. Five guard/schema cases added after full-suite collection are included
in the final 148-case focused pass. The final collection-only command succeeded with 3,682 final
tests present and no collection errors.

Full-suite blockers include unavailable HTTP API/database services, references to deleted
legacy modules, absent workflow/documentation files, quality-result assertions, and agent
fixtures missing pre-existing attributes. No baseline-wide claim is made that every failure is
unrelated to this change; the complete suite remains failing in this unprovisioned environment.
The original full logs were retained in `/tmp/mapit-full-final-guarded.log`, focused logs in
`/tmp/mapit-final-focused-guarded.log`, and the real smoke in `/tmp/mapit-real-smoke-final.log`.
Redis's read-only FLUSHALL counter remained at 50 after the guarded full-suite run.

Initial full collection failed in 33 modules because PyYAML was missing. PyYAML was installed
only in the isolated test environment. An initial unbounded suite attempt was terminated after
waiting in live-service tests. The subsequent bounded run, before the final subprocess guard,
completed with 2,447 passed, 763 failed, 352 skipped and 44 errors in 300.09 seconds; this result
is superseded by the final guarded run above. Full-suite failures include unavailable API/DB
services, deleted legacy modules (`result_evaluator`, `agentic_manager`), existing quality-result
schema assertions, and fixtures that omit attributes used by existing agent code.

A targeted existing regression run with the pinned tools returned 59 passed and 3 failed:
`tests/test_context_window_reset.py::TestContextResetInProcessQuery` (two cases) and
`tests/test_conversation_regression.py::TestTask005ContextWindowReset::test_process_query_resets_context_at_start`.
Their `__new__` fixtures omit `smart_model_routing`; the base implementation already accesses
that attribute unconditionally. Those unrelated fixture failures were left in place.

Ruff 0.6.9 checked all 48 changed Python paths and passed; `git diff --check` passed. Generated quality result files
are restored after full-suite runs. Neither scoped passes nor a synthetic smoke establish that
a provisioned deployment or a real funding database works.

## Real inference smoke

Exact invocation: `.venv-test/bin/python scripts/smoke_codex.py --timeout 120`.
The final adapter used installed official CLI 0.165.0 and its existing ChatGPT login.
It sent only a non-sensitive synthetic marker/tool-list prompt; no funding database was used.
The job exited successfully and returned:

```json
{
  "text": "{\"marker\": \"MAPIT_CODEX_OK\", \"tools\": [\"functions.request_user_input\"]}",
  "model": null,
  "usage": {
    "input_tokens": 1225,
    "cached_input_tokens": 0,
    "cache_write_input_tokens": 0,
    "output_tokens": 27,
    "reasoning_output_tokens": 0
  }
}
```

The CLI did not emit a resolved default model ID; `null` is intentional. No model ID was invented.
The read-only job invoked no tools. The earlier unsanitized smoke exposed executable tool schemas;
it was not accepted as an isolation pass, and the catalog override/dry-run check was added.

## Remaining limits

- Host CLI installation and a ChatGPT login are required. Docker is not configured automatically.
- The adapter requires POSIX process cleanup and a supported installed bundled catalog.
- CLI upgrades or account models absent from that catalog can require adapter updates.
- Streaming emits completed-message chunks after generation, not live token deltas.
- CLI sampling does not implement the API providers' temperature/output-token hints.
- Default model metadata remains null when the CLI does not report a resolved model.
- Google embeddings/vector search still need their existing separate credentials/configuration.
- Full-suite live-service and legacy fixture failures remain; no provisioned app E2E was claimed.

## Changed paths

- `.env.example`
- `README.md`
- `app/api/call_document_routes.py`
- `app/api/conversation_routes_v3.py`
- `app/api/health_routes.py`
- `app/core/ai_routing.py`
- `app/core/config.py`
- `app/main.py`
- `app/models/schemas.py`
- `app/services/agents/proposal_aware_agent.py`
- `app/services/agents/query_preprocessing.py`
- `app/services/agents/tool_aware_agent.py`
- `app/services/agents/tool_executors.py`
- `app/services/ai/__init__.py`
- `app/services/ai/codex.py`
- `app/services/ai/factory.py`
- `app/services/ai/structured.py`
- `app/services/ai/types.py`
- `app/services/conversation/conversation_manager.py`
- `app/services/conversation/conversation_namer.py`
- `app/services/data_intelligence/query_planner.py`
- `app/services/memory/memory_service.py`
- `app/services/memory/rolling_summarizer.py`
- `app/services/proposal_writing/ai_providers/base.py`
- `app/services/proposal_writing/ai_providers/gemini_provider.py`
- `app/services/proposal_writing/ai_providers/multi_provider_service.py`
- `app/services/proposal_writing/ai_providers/text_model_provider.py`
- `app/services/proposal_writing/call_understanding_service.py`
- `app/services/proposal_writing/comprehensive_reviewer.py`
- `app/services/proposal_writing/criteria_matcher.py`
- `app/services/proposal_writing/draft_generator.py`
- `app/services/proposal_writing/evaluator_simulator.py`
- `app/services/proposal_writing/example_extractor.py`
- `app/services/proposal_writing/gap_analysis_service.py`
- `app/services/proposal_writing/inline_suggestions_service.py`
- `app/services/proposal_writing/proposal_ai_service.py`
- `app/services/proposal_writing/quality_improver.py`
- `app/services/proposal_writing/semantic_benchmarking.py`
- `app/services/proposal_writing/smart_rewriter.py`
- `app/services/tools/call_history.py`
- `docs_tracked/CODEX_LOCAL_PROVIDER.md`
- `docs_tracked/CODEX_PROVIDER_VERIFICATION.md`
- `requirements.txt`
- `scripts/smoke_codex.py`
- `scripts/test_offline.py`
- `tests/test_codex_adapter.py`
- `tests/test_codex_catalog.py`
- `tests/test_codex_chat_wiring.py`
- `tests/test_codex_proposal_wiring.py`
- `tests/test_codex_service_wiring.py`
- `tests/test_conversation_namer.py`
- `tests/test_offline_guards.py`
- `tests/test_text_provider_status.py`
