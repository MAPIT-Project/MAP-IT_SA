# Backend developer setup

**Last verified:** 20 July 2026
**Repository:** `MAP-IT_SA`

This document describes the backend setup and the actual Make/Docker commands available. For
the full stack path, frontend configuration and service order you start with
[START_HERE.md](../../START_HERE.md).

> **Database status:** a fresh clone does not yet have reproducible complete data and
> migrationbaseline. Enter `migration/schema.sql`, `migration/001_init_schema.sql`, the Drizzle files
ZZZPROTECTED0ZZ and `002_upgrade_embeddings_to_3072.sql` do not run blindly one after the other: they are not consistent
> ordered chain. See [database schema](../docs/DATABASE_SCHEMA.md) and
> [data ingestion](../docs/guides/DATA_INGESTION.md).

## 1. Requirements

- Python 3.11 or higher. The local tool config targets 3.11; the Dockerfile uses Python 3.13.
- Docker Engine with the Compose V2 plugin (`docker compose`).
- Supabase CLI and PostgreSQL client tools (`psql`, possibly `pg_restore`).
- A valid Gemini API key for the default provider and, for embeddings, a Google
embedding key or the same Gemini key.
- The frontend repo `webapp-ui` next to this repo if you use local Supabase.

## 2. Python environment

From `MAP-IT_SA`:

```bash
./scripts/setup.sh
source venv/bin/activate
make install-dev
```

The virtualenv is called **`venv`**, because `scripts/setup.sh` creates exactly that directory. The script:

1. creates `venv` if it does not already exist;
2. activates the environment within the script;
3. updates `pip`;
4.  only installs `requirements.txt`;
5. copies `.env.example` to `.env` if `.env` is missing.

The activation from a subprocess does not remain active in your current shell; therefore feed yourself afterwards
`source venv/bin/activate` off. `make install-dev` installs additionally
`requirements-dev.txt`.

## 3. Backend configuration

Edit `.env`, but never commit the file. `app/core/config.py` requires at least one for import
non-empty `DATABASE_URL`, `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`. Being for a functional chat
also need an AI provider and the associated model config.

For a **local Python process** with Supabase/Redis/Neo4j on the host:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=<lokale anon key>
SUPABASE_SERVICE_KEY=<lokale service-role key>
GEMINI_API_KEY=<secret>
GOOGLE_EMBEDDING_API_KEY=<secret>
DEFAULT_AI_PROVIDER=gemini
NEO4J_URI=bolt://localhost:17687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<zelfde waarde als Compose>
REDIS_URL=redis://localhost:16379/0
JWT_SECRET_KEY=<willekeurige gedeelde secret>
```

For the **Compose-API**, `DATABASE_URL`, `SUPABASE_URL`, `NEO4J_URI`, `REDIS_URL` and
Redis host/port overwritten by `docker-compose.yml` with Docker service names. Keys, models and
embedding settings do come from `.env`.

Generate a local JWT-secret with:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

The current V3/V4 routes do not use the existing authdependency and still rely on standard
identities. Setting up this secret does not make those routes safe; this is recorded in it
[API contract](../../API_CONTRACT.md) and [security register](../../SECURITY_REGISTER.md).

## 4. Supabase and the external Docker network

Backend-Compose declares `supabase_network_supabase_cli` as a **external** network and creates this
not yourself. Therefore, first start Supabase from exactly this folder:

```bash
cd ../webapp-ui/supabase_cli
supabase start
supabase status
docker network inspect supabase_network_supabase_cli >/dev/null
cd ../../MAP-IT_SA
```

Why this folder: the CLI finds there `supabase/config.toml` with
`project_id = "supabase_cli"`. The resulting container names include
`supabase_db_supabase_cli` and `supabase_kong_supabase_cli`; Compose uses exactly those names.
Do not run `supabase init` again.

Local main ports are API `54321`, PostgreSQL `54322` and Studio `54323`.

## 5. Database and data

For a transfer environment, use a versioned, full database baseline with checksum. The
repository does not currently contain it:

- `neo4j_backup/project_embeddings.dump` may exist in an existing workbook, but
`/neo4j_backup/` is Git-ignored;
- the checked dump contains only `TABLE DATA public project_embeddings`, no schema,
projects or organizations;
- `data/cordis` is Git-ignored and missing from a fresh clone;
- `migration/schema.sql` and `webapp-ui/supabase_cli/schema.sql` are snapshots of an entire
Supabase database and contain uncommented lines starting with `pg_dump:`;
- `001_init_schema.sql` and the frontend Drizzle migrations contradict each other about types of
`projects` and `organizations`;
- the 768-to-3072 migration is not yet a proven part of a tracked chain.

Therefore, request an approved full dump or use the raw ingestion path. The exact restore,
ingestion and verification steps are in [DATA_INGESTION.md](../docs/guides/DATA_INGESTION.md). The
intended order is Supabase → schema baseline → newer migrations → relational data →
document chunks/calls → embeddings with the correct dimension.

In any case, check after restore:

```bash
export MAPIT_DATABASE_URL='postgresql://postgres:postgres@localhost:54322/postgres'
psql "$MAPIT_DATABASE_URL" -c \
  "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY 1;"
psql "$MAPIT_DATABASE_URL" -c \
  "SELECT 'projects' AS bron, count(*) FROM projects
   UNION ALL SELECT 'organizations', count(*) FROM organizations
   UNION ALL SELECT 'funding_calls', count(*) FROM funding_calls
   UNION ALL SELECT 'document_chunks', count(*) FROM document_chunks;"
```

## 6. Starting Redis and Neo4j

```bash
docker compose up -d redis neo4j
docker compose ps
```

Host ports are Redis `16379`, Neo4j Browser `17474` and Bolt `17687`. Within the Compose network
remain `6379`, `7474` and `7687` respectively.

### Loading checked Neo4j dump

`neo4j_backup/neo4j.dump` is Git tracked. Use `docker cp`, because Neo4j is the bind mount
`neo4j/import` often gives UID `7474` and mode `0700`, which prevents your host user from accessing them
has more:

```bash
docker cp neo4j_backup/neo4j.dump mapit-neo4j:/var/lib/neo4j/import/neo4j.dump
docker compose stop neo4j
docker compose run --no-deps --rm --entrypoint neo4j-admin neo4j \
  database load --from-path=/var/lib/neo4j/import neo4j --overwrite-destination=true
docker compose start neo4j
docker compose ps
```

If hosttools or pytest still give `Permission denied` on `neo4j/import`, restore only that folder:

```bash
sudo chown -R "$(id -u):$(id -g)" neo4j/import
chmod 755 neo4j/import
```

Do not run wide `chown` on the repository or Docker volumes.

## 7. What the Make targets actually do

| Target | Exact behavior | Accessible on |
|---|---|---|
| `make run` | `uvicorn main:app --host 0.0.0.0 --port 8000` in the active host environment | `http://localhost:8000` |
| `make run-reload` | same with `--reload` | `http://localhost:8000` |
| `make docker-up` | only `docker compose up -d`; start Redis, Neo4j and a API container | API `18000`, Redis `16379`, Neo4j `17474`/`17687` |
| `make docker-down` | `docker compose down` | stops the Compose stack; named volumes persist normally |
| `make install` | installs `requirements.txt` via the active `pip` | n/a. |
| `make install-dev` | `make install`, then `requirements-dev.txt` | n/a. |
| `make test` | `pytest -q` | current baseline can already fail upon collection on `neo4j/import` permissions |
| `make lint` | `ruff check app tests .` | n.a. |

### Supported starting modes

**Standard full stack mode — all in Compose:**

```bash
# Supabase and the database are already started/loaded.
docker compose up -d --build
curl -fsS http://localhost:18000/api/health/live
```

Then set the frontend with `BACKEND_URL=http://localhost:18000`.

**Backend debug mode — infrastructure in Docker, API on the host:**

```bash
docker compose up -d redis neo4j
source venv/bin/activate
make run-reload
curl -fsS http://localhost:8000/api/health/live
```

Use the host URLs from section 3 and set up frontend `BACKEND_URL`
`http://localhost:8000`. Do not also start the Compose service `api` in this mode.

## 8. Actual V3 and V4 routes

The V3 prefix in `conversation_routes_v3.py` is `/api/v3/conversation`:

- `POST /api/v3/conversation/{conversation_id}/message/stream`
- `POST /api/v3/conversation/{conversation_id}/message`
- `GET /api/v3/conversation/{conversation_id}/context`
- `DELETE /api/v3/conversation/{conversation_id}/context`
- `GET /api/v3/conversation/health`
- `GET /api/v3/conversation/analytics/summary`
- `GET /api/v3/conversation/analytics/low-confidence`
- `GET /api/v3/conversation/analytics/search`
- `GET /api/v3/conversation/analytics/export`

The V4 prefix in `proposal_session_routes.py` is **`/api/v4/proposal-session`**, not
`/api/v4/proposals/sessions`:

- `POST /api/v4/proposal-session/create`
- `GET|DELETE /api/v4/proposal-session/{session_id}`
- `POST /api/v4/proposal-session/{session_id}/message`
- `POST /api/v4/proposal-session/{session_id}/message/stream`
- `PATCH /api/v4/proposal-session/{session_id}/section/{section_id}`
- `PATCH /api/v4/proposal-session/{session_id}/section/{section_id}/status`
- `POST /api/v4/proposal-session/{session_id}/section/{section_id}/generate`
- `POST /api/v4/proposal-session/{session_id}/section/{section_id}/evaluate`
- `POST /api/v4/proposal-session/{session_id}/section/{section_id}/analyze-gaps`
- `POST /api/v4/proposal-session/{session_id}/focus/{section_id}`
- `GET /api/v4/proposal-session/health`

`POST .../create` expected `proposal_id`, `call_id`, `title`, optional `proposal_type` and optional
`conversation_id`; `user_id` is currently a query parameter with default `default-user`. See for
schemas, events and examples the [API contract](../../API_CONTRACT.md).

Please note: the declared V4 health route is in the route file **na**
`GET /api/v4/proposal-session/{session_id}`. FastAPI/Starlette route ordering allows `health`
therefore be interpreted as `session_id`. For general process health, use the working one
`/api/health/live` and `/api/health` routes.

## 9. Verification

```bash
curl -fsS http://localhost:18000/api/health/live
curl -sS http://localhost:18000/api/health | python3 -m json.tool
curl -sS http://localhost:18000/openapi.json -o /tmp/mapit-openapi.json
```

For host debug mode, replace `18000` with `8000`. `/api/health/live` just proves that the process
responds; `/api/health` controls PostgreSQL, Neo4j, Redis, Gemini, embeddings and Supabase. A
`degraded` results must be examined per component.

V3 streamsmoke, after creating a user and conversation via the frontend:

```bash
curl -N -X POST \
  'http://localhost:18000/api/v3/conversation/<conversation-id>/message/stream?user_id=1' \
  -H 'Content-Type: application/json' \
  -d '{"message":"Noem passende open Horizon Europe-calls voor digitale gezondheid.","include_context":true}'
```

Expect SSE lines with `data:`, followed by a `complete` event. Without the right data sets or
In terms of embedding dimension, this is only a technical smoke test, not a substantive acceptance test.

## 10. Troubleshooting

### External Supabase network missing

```bash
cd ../webapp-ui/supabase_cli
supabase status || supabase start
docker network inspect supabase_network_supabase_cli
```

Don't manually create an empty network with the same name if you really want the Supabase containers
reaches; Start Supabase so that the correct containers are linked to it.

### API is using the wrong port

- `make run` and `make run-reload`: host port `8000`.
- `make docker-up`/Compose-API: Host port `18000`.
- Within Docker, FastAPI is always listening on `8000`.

Check with `docker compose ps` and adjust frontend `BACKEND_URL` to the selected mode.

### Neo4j remains unhealthy

The health check has a starting period of 60 seconds. Then check out:

```bash
docker compose logs --tail=150 neo4j
curl -I http://localhost:17474
```

Check password consistency and permissions of `neo4j/import` only.

### Vector search fails on dimension

The active code config is 3072 (`gemini-embedding-001`), but older schema snapshots have 768 for
calls/chunks/cache. Check the live type before ingest or re-embedding:

```bash
psql "$MAPIT_DATABASE_URL" -c \
  "SELECT table_name, column_name, format_type(a.atttypid,a.atttypmod)
   FROM information_schema.columns c
   JOIN pg_attribute a ON a.attname=c.column_name
   JOIN pg_class k ON k.oid=a.attrelid AND k.relname=c.table_name
   WHERE c.table_schema='public' AND c.column_name='embedding';"
```

Don't migrate ad hoc: follow the established baseline
[DATABASE_SCHEMA.md](../docs/DATABASE_SCHEMA.md) and then regenerate all affected embeddings.

## Stop

```bash
docker compose down
cd ../webapp-ui/supabase_cli
supabase stop
```

These commands do not normally delete named volumes. A clean/reset action is destructive and
belongs only to a consciously disposable local environment.
