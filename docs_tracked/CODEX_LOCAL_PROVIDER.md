# Local Codex text provider

MAPIT can send text-generation jobs to the official authenticated Codex CLI.
This integration is for personal local development. It uses `codex exec`, not
an OpenAI API-key alias or a direct ChatGPT endpoint. The CLI owns authentication.
See OpenAI's [Codex platform guide](https://developers.openai.com/blog/codex-as-a-platform)
and [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

Install the official CLI on the host running MAPIT and authenticate interactively:

```bash
codex --version
codex login
codex login status
```

The adapter checks for a ChatGPT login and the required `exec` isolation flags.
It was exercised with CLI 0.165.0. It does not read, copy or log login tokens.
Each host process needs access to its own existing CLI login. Docker images do
not install or authenticate Codex automatically; production deployment files
are unchanged. POSIX process groups are required for cancellation cleanup.

Enable all text generation through Codex in your local process environment:

```bash
export CODEX_ENABLED=true
export DEFAULT_AI_PROVIDER=codex
export CODEX_MODEL=gpt-6.1-sol
export CODEX_REASONING_EFFORT=high
export CODEX_TIMEOUT_SECONDS=120
# Optional: export CODEX_CLI_PATH=/absolute/path/to/codex
```

No Gemini/OpenAI/OpenRouter API key is required for Codex text generation.
Database and other application configuration requirements still apply. Codex
remains disabled when settings are omitted; selecting it without `CODEX_ENABLED=true`
raises an error. `.env.example` now contains an active local Codex/Sol/high setup
and preserves the previous API-provider configuration as comments. Comment out
the Codex block and uncomment the saved provider/key/model settings to switch back.
The real `.env` is not changed by editing the example or merging the code.
Restart application/worker processes after changing environment configuration.

For mixed routing, retain your existing global provider and set JSON overrides:

```bash
export DEFAULT_AI_PROVIDER=gemini
export CODEX_ENABLED=true
export AI_STEP_PROVIDERS='{"chat_reasoning":"codex","memory_summary":"gemini"}'
```

Selection precedence is explicit constructor/provider selection, then explicit
request selection, then named-step override, then `DEFAULT_AI_PROVIDER`.
V3 message endpoints accept `ai_provider` with `gemini`, `openai`, `openrouter`,
or `codex`. An omitted field uses normal configuration. A supplied provider
applies throughout that request, including streamed response lifetime and
ancillary generation. Invalid provider names and unknown configured step names
raise validation errors. Other routes retain their existing request schemas.

| Step | Text-generation calls |
| --- | --- |
| `chat_reasoning` | V3/V4 agent reasoning and structured action decisions |
| `chat_response` | Chat introductions, fallback answer synthesis, conversation synthesis |
| `query_preprocessing` | Translation and long-query condensation |
| `memory_summary` | Rolling summaries, facts and entity extraction |
| `conversation_naming` | Conversation title generation |
| `query_planning` | Data-intelligence query plans |
| `call_document_summary` | Call-document answers |
| `call_history` | Historical call keyword expansion |
| `proposal_generation` | Generic proposal AI service calls |
| `call_understanding` | Call requirements and topic analysis |
| `proposal_draft` | Section drafting and improvement |
| `proposal_review` | Comprehensive proposal review passes |
| `proposal_criteria` | Evaluation criteria matching |
| `proposal_quality` | Proposal quality analysis and improvement |
| `proposal_evaluation` | Evaluator simulation |
| `proposal_gaps` | Gap analysis |
| `proposal_examples` | Example extraction/enrichment |
| `proposal_benchmarking` | Semantic proposal benchmarking |
| `proposal_rewrite` | Smart rewriting |
| `proposal_suggestions` | Inline suggestions |

Gemini flash/pro routing applies only when the reasoning provider is Gemini.
It cannot replace an explicit Codex choice. Existing API-provider fallbacks in
the proposal service remain available for API selections. Selecting Codex gives
that service exactly one provider; CLI startup, timeout, login or generation
errors never send its prompts to another provider. Some services retain local
pattern/rule fallbacks when inference fails.

Jobs use stdin prompts and an empty temporary directory outside the repository.
The adapter ignores user configuration and rules, suppresses project/skill
instructions, requests a read-only sandbox, and disables execution, web, browser,
connector and delegation features. It forwards only HOME, PATH, CODEX_HOME and
locale variables. It does not forward API keys, application credentials or
parent Codex runtime state. Cancellation and timeout kill the entire child
process group; temporary output files are removed on success and failure.

CLI feature flags alone do not remove tools mandated by bundled model metadata.
For each job, MAPIT exports the installed CLI's bundled catalog under a temporary,
unauthenticated HOME, preserves its exact model IDs/order/default, and disables
executable model capabilities through the official
[model catalog override](https://learn.chatgpt.com/docs/model-catalogs). A local
`debug prompt-input` dry run must declare an empty tool list or only
`functions.request_user_input`. That inert UI tool cannot execute commands or
access host resources; noninteractive inference does not answer its questions.
Unknown catalog formats, missing configured models, and any other exposed tool
fail before inference. CLI upgrades may require adapter changes. No hook-trust or
sandbox bypass is used.

`CODEX_MODEL` is optional. User CLI configuration is ignored for isolation, so
an omitted model uses the CLI's built-in default. If the CLI does not report its
resolved model, metadata is `null`; MAPIT does not invent a model ID. Temperature
and output-token hints used by API providers are not CLI sampling controls.
The CLI job timeout bounds generation time, and final output is limited to 4 MiB.

`CODEX_REASONING_EFFORT` is optional and is forwarded as the official CLI
`model_reasoning_effort` override in both the capability check and inference job.
Use `high` for the Sol setup above. MAPIT accepts `minimal`, `low`, `medium`,
`high`, `xhigh`, `max`, and `ultra`; the selected model and installed CLI determine
which of those levels they support. Invalid setting values fail MAPIT validation;
Codex jobs retain their no-other-provider fallback policy. Omit the variable to retain the CLI model's
default effort. User CLI configuration is still ignored. See the
[official setting reference](https://learn.chatgpt.com/docs/config-file/config-reference).

Codex streaming yields a completed-message chunk after the job finishes. Existing
SSE `token` and `complete` event shapes remain compatible, but this is not live
token streaming. Structured output uses CLI schemas where supported and validates
the final JSON locally. Open-ended map schemas use prompted JSON with the same
local validation. No external JSON schema references are fetched.

Embeddings are separate. `EmbeddingService` continues using Google
`gemini-embedding-001`, 3072 dimensions, and `GOOGLE_EMBEDDING_API_KEY` (falling
back to `GEMINI_API_KEY`). Codex cannot produce compatible embedding vectors.
Vector search still needs its existing embedding configuration; no database
schema or vector index changes are part of this integration. Local cross-encoder
ranking is also unchanged.

Use the synthetic smoke without database or MAPIT settings loading:

```bash
python scripts/smoke_codex.py --timeout 120
# Pin the model and effort for a synthetic verification:
python scripts/smoke_codex.py --model gpt-6.1-sol --reasoning-effort high --timeout 120
```

Run mocked tests with dummy settings and external-service connections blocked:

```bash
python scripts/test_offline.py tests/test_codex_adapter.py tests/test_codex_chat_wiring.py \
  tests/test_codex_proposal_wiring.py tests/test_codex_service_wiring.py
python scripts/test_offline.py --timeout=5 --timeout-method=signal --tb=short
```

The second command needs pytest-timeout and attempts the full suite. Tests that
require a running API, live databases, or provisioned data can fail offline;
those failures do not constitute successful integration verification.
