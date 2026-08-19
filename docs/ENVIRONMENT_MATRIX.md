# Environment matrix

This matrix describes the environment variables that MAPIT actually reads or declares in the included examples and Docker Compose. The **required** classification is based on the current code, not only on the `.env.example` files.

Last verified: 20 July 2026.

## Sources and reading guide

Checked sources:

- backend: `MAP-IT_SA/.env.example`, `MAP-IT_SA/docker-compose.yml`, `MAP-IT_SA/app/core/config.py` and all Python files under `MAP-IT_SA/`;
- frontend: `webapp-ui/.env.example`, `webapp-ui/drizzle.config.ts`, `process.env`, `import.meta.env` and SvelteKit `$env/*` usage under `webapp-ui/`;
- test/CI variables are listed separately, so that they are not accidentally treated as production configuration.

Meaning of the columns:

- **Required**: `Yes` means the application does not initialise without a value or the primary function does not work; `conditional` means the value is only needed for the mentioned provider/feature.
- **Secret**: values marked `Yes` belong exclusively in a secret store or server-side environment. A `PUBLIC_` or `VITE_` prefix means SvelteKit/Vite may deliver the value to the browser.
- **Environment**: `L/S/P` means local, staging and production should each have their own value. `S/P` means at minimum unique staging and production values. Actual staging and production values are not in this repository.
- **Default / example**: `code:` is a real fallback; `example:` comes only from a `.env.example` and is not a safe runtime default.

## Environment profiles

| Topic | Local | Staging | Production |
|---|---|---|---|
| Database | Supabase CLI on `localhost:54322`, or the optional local PostgreSQL container | Separate non-production database | Separate production database; TLS per provider policy |
| Supabase | Local CLI URL (`localhost:54321`) or development project | Separate staging project | Production project |
| Backend URL from frontend | `http://localhost:18000` | Internal/public staging API URL | Production API URL |
| Public frontend URL | `http://localhost:5173` | Staging origin | Canonical production origin |
| Debugging | Can be on | Preferably off | Off |
| CORS | Local origin(s) | Staging origin(s) only | Production origin(s) only; no `*` |
| Secrets | Local development values | Unique staging secrets | Unique production secrets; rotate and manage centrally |
| Docker hostnames | In Compose: `redis`, `neo4j`, `supabase_db_supabase_cli`, `supabase_kong_supabase_cli` | Deployment-specific | Deployment-specific |

## Shared and backend core configuration

`Settings` in `app/core/config.py` reads field names case-insensitively as uppercase variables. As a result, for example `APP_NAME`, `APP_VERSION` and `OPENROUTER_BASE_URL` are also valid, even though they are missing from the backend `.env.example`.

| Name | Component | Required | Secret | Default / example | Environment | Description |
|---|---|---:|---:|---|---|---|
| `APP_NAME` | Backend | No | No | code: `CORDIS Research Projects RAG API` | Usually the same | Title of the FastAPI application. |
| `APP_VERSION` | Backend | No | No | code: `1.0.0` | Per release | Version in API and health metadata. |
| `API_HOST` | Backend | No | No | code/example: `0.0.0.0` | Usually the same | Uvicorn bind address. |
| `API_PORT` | Backend | No | No | code/example: `8000`; Compose publishes host port `18000` | L/S/P possible | Internal listening port of the backend. |
| `DEBUG` | Both | No | No | backend code/examples: `false`; frontend does not read this value | S/P: `false` | Backend reload/debug mode. The identically named frontend example value currently has no effect. |
| `CORS_ORIGINS` | Backend | No | No | code/example: `["*"]` | **L/S/P** | Allowed browser origins. Restrict staging and production explicitly. |
| `DATABASE_URL` | Both | **Yes** (backend and frontend Drizzle CLI) | **Yes** | no code default; backend example: local PostgreSQL DSN | **L/S/P** | Backend runtime and script connection. In the frontend only `drizzle.config.ts` reads this name for Drizzle Kit; see [Database naming](#database-naming-frontenddrizzle). |
| `DB_MIN_CONNECTIONS` | Backend | No | No | Settings: `5`; direct proposal-session fallback: `2` | Capacity-dependent | Minimum size of the database pool. |
| `DB_MAX_CONNECTIONS` | Backend | No | No | Settings: `50`; direct proposal-session fallback: `10` | Capacity-dependent | Maximum size of the database pool. Align with the database connection limit. |
| `SUPABASE_URL` | Backend; unused frontend example | **Yes** for backend | No | no backend default; frontend example: `http://localhost:54321`; Compose: `http://supabase_kong_supabase_cli:8000` | **L/S/P** | Server-side Supabase URL. The frontend code uses `PUBLIC_SUPABASE_URL` instead. |
| `SUPABASE_ANON_KEY` | Backend | No | No | none; placeholder in backend example | **L/S/P** | Public/anonymous Supabase key for backend calls that do not need the service role. |
| `SUPABASE_SERVICE_KEY` | Backend | **Yes** | **Yes** | none; placeholder in backend example | **L/S/P** | Supabase service-role key for backend administration. Never deliver to the browser. |
| `JWT_SECRET_KEY` | Both | **Yes in S/P** | **Yes** | backend: random per process if absent; frontend: `fallback-secret-change-in-production` | **L/S/P** | Signing of JWTs; must be exactly the same in frontend and backend. The code fallbacks are not suitable for shared sessions or production. |
| `STATIC_API_KEY` | Backend | No | **Yes** | none | **L/S/P** if used | Optional static key for simple API authentication. |
| `DOCKER_ENV` | Backend | No | No | code: `false`; Compose: `true` | Local/deployment | Indicates that the backend is running in the Docker Compose context. |

## AI providers and embeddings

At minimum the key of the chosen provider is operationally required. The configuration validator does not enforce this centrally; errors may therefore only occur when an AI function is called.

| Name | Component | Required | Secret | Default / example | Environment | Description |
|---|---|---:|---:|---|---|---|
| `DEFAULT_AI_PROVIDER` | Backend | No | No | code/example/Compose: `gemini` | Usually the same | Primary text provider (`gemini`, `openai` or partially `openrouter`, depending on the service). |
| `GEMINI_API_KEY` | Backend | Conditional | **Yes** | none; placeholder in example | **L/S/P** | Gemini generation key; also serves as fallback for embeddings. |
| `GEMINI_MODEL` | Backend | No | No | usually `gemini-3-flash-preview`; `comprehensive_reviewer.py` independently falls back to `gemini-2.0-flash-exp` | Per release/environment | Fast Gemini model. Pin explicitly in S/P to prevent component deviations. |
| `GEMINI_PRO_MODEL` | Backend | No | No | `gemini-3.1-pro-preview` | Per release/environment | Heavier Gemini model for smart routing. |
| `OPENAI_API_KEY` | Backend | Conditional | **Yes** | none; placeholder in example | **L/S/P** | OpenAI API key for generation and provider fallback. |
| `OPENAI_MODEL` | Backend | No | No | `gpt-4-turbo` | Per release/environment | OpenAI model name. |
| `OPENROUTER_API_KEY` | Backend | Conditional | **Yes** | none; placeholder in example | **L/S/P** | OpenRouter key for supported generation/memory paths. |
| `OPENROUTER_MODEL` | Backend | No | No | `x-ai/grok-4-fast:free` | Per release/environment | OpenRouter model name from Settings/Compose. |
| `OPENROUTER_BASE_URL` | Backend | No | No | code: `https://openrouter.ai/api/v1` | Usually the same | Base URL for OpenRouter. Missing from `.env.example`. |
| `SMART_MODEL_ROUTING` | Backend | No | No | `true` | Usually the same | Routes complex tasks to the pro model. |
| `GOOGLE_EMBEDDING_API_KEY` | Backend | Conditional | **Yes** | none; fallback is `GEMINI_API_KEY` in the embedding service | **L/S/P** | Google key for vector embeddings. Needed when vector search/embedding jobs are on and no usable Gemini key is available. |
| `GOOGLE_API_KEY` | Backend code; also unused frontend example | Conditional | **Yes** | none | **L/S/P** | Alternative fallback key in the query planner. The frontend declares it, but does not read it. |
| `EMBEDDING_MODEL` | Backend | No | No | Settings/Compose: `models/gemini-embedding-001`; backend example: `gemini-embedding-001` | Per release | Embedding model. Preferably use one form explicitly, because the sources differ from each other. |
| `EMBEDDING_DIMENSION` | Backend | No | No | `3072` | Same as DB schema | Vector dimension; must match pgvector columns and the chosen model. |

## Backend retrieval, context and performance tuning

The `MAX_CONTEXT_*`, `LLM_TIMEOUT_SECONDS` and conversation variables below were not in the backend `.env.example` but are read directly with `os.getenv`.

| Name | Component | Required | Secret | Default | Environment | Description |
|---|---|---:|---:|---|---|---|
| `VECTOR_SEARCH_ENABLED` | Backend | No | No | Settings: `false`; `.env.example`/Compose: `true` | Per environment | Enables vector search. The effective default therefore depends on the start method. |
| `CHUNK_SIZE` | Backend | No | No | `1000` | Usually the same | Target size of document chunks. |
| `CHUNK_OVERLAP` | Backend | No | No | `300` | Usually the same | Overlap between consecutive chunks. |
| `MAX_CHUNKS_PER_QUERY` | Backend | No | No | `20` | Capacity-dependent | Maximum number of vector results per query. |
| `SIMILARITY_THRESHOLD` | Backend | No | No | `0.45` | Quality-dependent | Minimum vector similarity. |
| `MAX_CONTEXT_CHARS` | Backend | No | No | `400000` | Capacity-dependent | Total character limit for the tool-aware agent context. |
| `MAX_TOOL_RESULT_CHARS` | Backend | No | No | `30000` | Capacity-dependent | Character limit per tool result in the agent context. |
| `MAX_OBSERVATION_CHARS` | Backend | No | No | `20000` | Capacity-dependent | Character limit per agent observation. |
| `MAX_DOCUMENT_CHARS` | Backend | No | No | `1000` | Quality-dependent | Character limit of document content placed in the agent context. |
| `MAX_RETRIEVAL_CHUNKS` | Backend | No | No | `4` | Capacity-dependent | Maximum number of retrieval chunks in conversation memory. |
| `MAX_CONTEXT_TOKENS` | Backend | No | No | `8000` | Model-dependent | Token budget for conversation memory. This is separate from `MAX_CONTEXT_CHARS`. |
| `SUMMARIZE_EVERY_N_TURNS` | Backend | No | No | `5` | Quality-dependent | Frequency at which conversations are summarised. |
| `RETRIEVAL_CACHE_TTL` | Backend | No | No | `3600` s | Environment/data-dependent | Cache duration for conversation retrieval. |
| `LLM_TIMEOUT_SECONDS` | Backend | No | No | `30` s | Capacity-dependent | Timeout around an LLM call of the tool-aware agent. |
| `EMBEDDING_TIMEOUT` | Backend | No | No | `30.0` s | Capacity-dependent | Timeout for embedding generation in similar-project search. |
| `VECTOR_SEARCH_TIMEOUT` | Backend | No | No | `10.0` s | Capacity-dependent | Timeout for vector search operations. |
| `GRAPH_CONTEXT_TIMEOUT` | Backend | No | No | `30.0` s | Capacity-dependent | Configured graph context timeout. |
| `LONG_QUERY_THRESHOLD` | Backend | No | No | `500` characters | Usually the same | Threshold after which query preprocessing chooses the long-query route. |
| `MAX_PROCESSED_QUERY_LENGTH` | Backend | No | No | `400` characters | Usually the same | Maximum length of a preprocessed query. |

## Backend services, documents and external APIs

| Name | Component | Required | Secret | Default / example | Environment | Description |
|---|---|---:|---:|---|---|---|
| `REDIS_URL` | Backend | No (fallback possible) | Possibly | Settings/example: `redis://localhost:6379/0`; some direct code paths: `redis://localhost:6379`; Compose: `redis://redis:6379/0` | **L/S/P** | Redis connection for rate limiting/cache and availability tests. Add credentials/TLS if the provider requires it. |
| `REDIS_HOST` | Backend | No | No | direct code: `localhost`; backend example/Compose: `redis` | **L/S/P** | Host for short-term memory. For non-Docker local this should generally be `localhost`. |
| `REDIS_PORT` | Backend | No | No | `6379` | Usually the same | Redis port for memory services. |
| `CELERY_BROKER_URL` | Backend | No | Possibly | local example: `redis://localhost:6379/0`; Compose: `redis://redis:6379/0` | **L/S/P** | Optional Celery broker URL. |
| `CELERY_RESULT_BACKEND` | Backend | No | Possibly | local example: `redis://localhost:6379/0`; Compose: `redis://redis:6379/0` | **L/S/P** | Optional Celery result backend. |
| `TASK_TIME_LIMIT` | Backend | No | No | `300` s | Capacity-dependent | Hard task limit from Settings. |
| `TASK_SOFT_TIME_LIMIT` | Backend | No | No | `240` s | Capacity-dependent | Soft task limit from Settings. |
| `NEO4J_URI` | Backend | No | No | code: `bolt://localhost:7687`; Compose: `bolt://neo4j:7687` | **L/S/P** | Bolt URL for graph queries. |
| `NEO4J_USER` | Backend | No | No | `neo4j` | L/S/P possible | Neo4j username. |
| `NEO4J_PASSWORD` | Backend/infra | **Yes in S/P** | **Yes** | code/Compose fallback: `mapit_secure_password_2024` | **L/S/P** | Neo4j password. The included fallback is for local development only. |
| `MAX_FILE_SIZE_MB` | Backend | No | No | `50` | Policy-dependent | Backend upload limit; independent of the frontend limit. |
| `SUPPORTED_FILE_TYPES` | Backend | No | No | `[".pdf", ".txt", ".md", ".html"]` | Usually the same | JSON list of accepted file extensions. |
| `UPLOAD_DIR` | Backend | No | No | `uploads` | **L/S/P** | Storage path for uploads; make this persistent in deployments that use local storage. |
| `EU_PORTAL_BASE_URL` | Backend | No | No | `https://api.tech.ec.europa.eu/search-api/prod/rest/search` | Usually the same | EU Funding & Tenders search endpoint. |
| `EU_PORTAL_TOPIC_DETAILS_URL` | Backend | No | No | `https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails` | Usually the same | Base URL for topic detail JSON. |
| `EU_PORTAL_FACET_URL` | Backend | No | No | `https://api.tech.ec.europa.eu/search-api/prod/rest/facet` | Usually the same | EU Portal facet endpoint. |
| `CALL_ENRICHMENT_MAX_RETRIES` | Backend | No | No | `3` | Capacity-dependent | Number of retries after the first enrichment attempt. |
| `CALL_ENRICHMENT_BASE_DELAY` | Backend | No | No | `1.0` s | Capacity-dependent | Initial retry delay. |
| `CALL_ENRICHMENT_MAX_DELAY` | Backend | No | No | `30.0` s | Capacity-dependent | Maximum retry delay. |
| `CALL_ENRICHMENT_EXPONENTIAL_BASE` | Backend | No | No | `2.0` | Usually the same | Exponential backoff factor. |
| `CALL_ENRICHMENT_CACHE_TTL` | Backend | No | No | `3600` s | Data-dependent | Cache duration of enriched call details. |
| `ENHANCED_CALL_SEARCH_CACHE_TTL` | Backend | No | No | `3600` s | Data-dependent | Cache duration of enhanced call search. |

## Frontend configuration

| Name | Component | Required | Secret | Default / example | Environment | Description |
|---|---|---:|---:|---|---|---|
| `PRIVATE_DATABASE_URL` | Frontend server runtime | **Yes** | **Yes** | no code default; example: local PostgreSQL DSN | **L/S/P** | Database connection for SvelteKit server routes and the runtime Drizzle client. Never expose to client code. |
| `BACKEND_URL` | Frontend server runtime | No | No | code/example: `http://localhost:18000` | **L/S/P** | Base URL with which server routes proxy requests to the FastAPI backend. |
| `PUBLIC_SUPABASE_URL` | Frontend browser/server | **Yes** | No | code: empty string; example: project URL | **L/S/P** | Supabase URL for browser and server clients. Visible in the browser bundle due to `PUBLIC_`. |
| `PUBLIC_SUPABASE_ANON_KEY` | Frontend browser/server | **Yes** | No | code: empty string; placeholder in example | **L/S/P** | Supabase anonymous key; public by design, but protect data with RLS. |
| `SUPABASE_SERVICE_ROLE_KEY` | Frontend server | Conditional | **Yes** | none; admin routes fall back to the anon key | **L/S/P** | Service-role key for collaboration member/invite management. Set server-side only. |
| `VITE_SUPABASE_URL` | Frontend legacy/test route | Conditional | No | no code default; placeholder in example | **L/S/P** | Only used by `/api/test_rls`; normal frontend code uses `PUBLIC_SUPABASE_URL`. |
| `VITE_SUPABASE_ANON_KEY` | Frontend legacy/test route | Conditional | No | no code default; placeholder in example | **L/S/P** | Only used by `/api/test_rls`; visible in the client environment due to `VITE_`. |
| `PUBLIC_APP_NAME` | Frontend browser | No | No | code/example: `Mapit AI Expert` | Branding-dependent | Application name and SEO title. |
| `PUBLIC_APP_URL` | Frontend browser | No | No | code/example: `http://localhost:5173` | **L/S/P** | Canonical URL for SEO links and images. |
| `PUBLIC_APP_ENV` | Frontend browser | No | No | `development` | **L/S/P** | Application profile: `development`, `testing` or `production`. |
| `PUBLIC_ENABLE_DEBUG_TOOLS` | Frontend browser | No | No | code: on unless `PUBLIC_APP_ENV=production`; example: `true` | **L/S/P** | Shows/hides frontend debug tools. Turn off in production. |
| `PUBLIC_ENABLE_ANALYTICS` | Frontend browser | No | No | code: on with `PUBLIC_APP_ENV=production`; example: `false` | **L/S/P** | Frontend feature flag for analytics. |
| `PUBLIC_API_TIMEOUT_MS` | Frontend browser | No | No | `30000` ms | Capacity-dependent | Configured public API timeout. |
| `PUBLIC_MAX_UPLOAD_SIZE_MB` | Frontend browser | No | No | `10` | Policy-dependent | Frontend upload limit; keep this at most equal to backend `MAX_FILE_SIZE_MB`. |
| `NODE_ENV` | Frontend/Node platform | By build platform | No | no application default | **L/S/P** | `migrations.ts` uses the hardcoded local DB config only when exactly `development`; otherwise `PRIVATE_DATABASE_URL`. |
| `PUBLIC_SUPABASE_SERVICE_KEY` | Frontend example only; not used | **No — do not set** | **Yes, but publicly exposed** | placeholder in example | None | Insecure/stale declaration. A service-role key must never have a `PUBLIC_` prefix. Use server-side `SUPABASE_SERVICE_ROLE_KEY`. |
| `MAPBOX_API_KEY` | Frontend example only; not used | No | Restrict as a public token | placeholder in example | L/S/P if used later | Currently no code consumer found. |

## Database naming frontend/Drizzle

The two frontend names are not alternatives in the current code:

| Process | Variable read | Source |
|---|---|---|
| SvelteKit runtime and server routes | `PRIVATE_DATABASE_URL` | `src/lib/server/db/index.ts`, `src/lib/server/db/migrations.ts`, `/api/test` |
| Drizzle Kit CLI (`generate`, `migrate`, etc.) | `DATABASE_URL` | `webapp-ui/drizzle.config.ts` |
| FastAPI backend and Python scripts | `DATABASE_URL` | backend `Settings` and direct `os.getenv` calls |

The frontend `.env.example` currently contains only `PRIVATE_DATABASE_URL`, while `drizzle.config.ts` hard-fails if `DATABASE_URL` is missing. For frontend development/deployment, **both server-side variables** must therefore be set, usually to the same PostgreSQL DSN:

```dotenv
# Server-side only; never make PUBLIC_ or VITE_.
PRIVATE_DATABASE_URL=postgresql://...
DATABASE_URL=postgresql://...
```

This document corrects the operational confusion; the configuration files have deliberately not been changed. Note that the backend has its own process environment: its `DATABASE_URL` can point to the same database, but is not automatically shared with the frontend.

## Test and CI-only variables from Python

| Name | Component | Required | Secret | Default | Environment | Description |
|---|---|---:|---:|---|---|---|
| `TEST_API_URL` | Backend tests | No | No | usually `http://localhost:8000` | Test environment | Dominant base URL for live/integration and quality tests. |
| `MAP_IT_API_URL` | Quality tests | No | No | `http://localhost:8000` | Test environment | Base URL used by the `test_prompt_*` suite. |
| `MAPIT_API_URL` | One Neo4j error scenario | No | No | `http://localhost:8000` | Test environment | Deviating name without underscore; not interchangeable with `MAP_IT_API_URL`. |
| `API_BASE_URL` | A few quality scenarios | No | No | `http://localhost:8000` | Test environment | Third alias for the test API base URL. |
| `SKIP_LIVE_API_TESTS` | Quality tests | No | No | live tests are only skipped with value `1` | CI/test | Set to `1` to skip live API tests. |
| `GITHUB_OUTPUT` | GitHub Actions | By runner | No | none | CI | Runner file in which `scripts/quality_gate.py` writes outputs. |
| `GITHUB_STEP_SUMMARY` | GitHub Actions | By runner | No | none | CI | Runner file for the Markdown job summary. |

## Docker Compose and image-internal variables

These values configure containers, not the MAPIT processes directly. The Neo4j values are hardcoded in `docker-compose.yml`, with the exception of the password in `NEO4J_AUTH`.

| Name | Component | Required | Secret | Default in Compose | Environment | Description |
|---|---|---:|---:|---|---|---|
| `NEO4J_AUTH` | Neo4j image | Yes | **Yes** | `neo4j/${NEO4J_PASSWORD:-mapit_secure_password_2024}` | **L/S/P** | Neo4j bootstrap credentials. Configure indirectly via `NEO4J_PASSWORD`. |
| `NEO4J_PLUGINS` | Neo4j image | No | No | `["apoc", "graph-data-science"]` | Usually the same | Neo4j plugins to install. |
| `NEO4J_dbms_security_procedures_unrestricted` | Neo4j image | No | No | `apoc.*,gds.*` | S/P review | Procedures with unrestricted rights. Restrict where possible. |
| `NEO4J_dbms_security_procedures_allowlist` | Neo4j image | No | No | `apoc.*,gds.*` | S/P review | Allowlist for APOC/GDS procedures. |
| `NEO4J_dbms_memory_heap_initial__size` | Neo4j image | No | No | `512m` | Capacity-dependent | Initial Java heap. |
| `NEO4J_dbms_memory_heap_max__size` | Neo4j image | No | No | `2G` | Capacity-dependent | Maximum Java heap. |
| `NEO4J_dbms_memory_pagecache_size` | Neo4j image | No | No | `512m` | Capacity-dependent | Neo4j page cache. |
| `POSTGRES_USER` | Optional, commented-out PostgreSQL service | Conditional | No | `postgres` | **L/S/P** | Only relevant when the fallback service in Compose is enabled. |
| `POSTGRES_PASSWORD` | Optional, commented-out PostgreSQL service | Conditional | **Yes** | example: `postgres_secure_password` | **L/S/P** | Bootstrap password; replace the example value outside local. |
| `POSTGRES_DB` | Optional, commented-out PostgreSQL service | Conditional | No | `postgres` | L/S/P possible | Database name of the optional fallback service. |

## Known configuration differences and points of attention

1. `DATABASE_URL` and `PRIVATE_DATABASE_URL` have different frontend consumers; set both for Drizzle plus runtime.
2. `PUBLIC_SUPABASE_SERVICE_KEY` is an insecure, unused example variable. Never put a real service-role key in it.
3. `VECTOR_SEARCH_ENABLED` is `false` by default in `Settings`, but `true` in `.env.example` and Docker Compose.
4. `EMBEDDING_MODEL` is `models/gemini-embedding-001` in code/Compose and `gemini-embedding-001` in `.env.example`.
5. The proposal-session pool uses direct fallbacks `2/10`, while central Settings and `.env.example` use `5/50`.
6. `GEMINI_MODEL` has an older independent fallback (`gemini-2.0-flash-exp`) in `comprehensive_reviewer.py`.
7. `REDIS_HOST=redis` works in Compose; for a local process outside Docker the code fallback uses `localhost`.
8. Four test URL names exist. New tests should preferably use `TEST_API_URL`, but existing aliases remain documented above.

## Secret policy

- Never commit real values for database DSNs, JWTs, service-role keys, provider keys or passwords.
- Use unique secrets per environment and rotate production secrets after handover.
- Treat URLs with embedded credentials as secret, even if the variable name does not contain `KEY` or `PASSWORD`.
- Anything with `PUBLIC_` or `VITE_` can end up in browser code; put only deliberately public configuration there.
