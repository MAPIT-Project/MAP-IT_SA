# CORDIS Horizon Europe refresh runbook

This refresh updates Horizon Europe projects, consortium organisations, PostgreSQL
search indexes, Neo4j relationships and project embeddings. It finishes with
source/database/graph/retrieval verification and cache invalidation. Funding calls
and official PDF revisions have [separate workflows](data-refresh.md).

## Prerequisites

Run from the repository root. Start the existing API, PostgreSQL, Neo4j and Redis
services. The API environment needs `DATABASE_URL`, `NEO4J_URI`, `NEO4J_USER`,
`NEO4J_PASSWORD`, `REDIS_URL`, `CORDIS_API_KEY` for downloading, and the configured
Google embedding key (`GOOGLE_EMBEDDING_API_KEY` or `GEMINI_API_KEY`). Recreate the
API container after changing its environment. Keep keys out of command arguments.

Use a **DET JSON outer ZIP**. The November 2026 CSV companion had malformed
quoting and decimal commas; do not repair or loosely parse it. The JSON parser
explicitly validates the observed schema, identifiers, dates, amounts and
consortium relationships before writes. Schema changes stop the run for review.

Allow disk space for the export, PostgreSQL/vector/consortium backup, graph
backup and logs. Embedding refresh uses the configured paid/quota-limited API.
For context, the November run generated 18,189 vectors and kept approximately
430 MB of compressed backups. That is an example, not a future size guarantee.

## 1. Request and download a fresh export

Check the connection and current tasks first:

```bash
docker compose exec -T -e PYTHONPATH=/app api python scripts/cordis_extract.py --check-key
```

Only start an extraction when no other extraction is active. CORDIS can cancel a
previous extraction when a new one is started; the client refuses to create one
when another active/unknown task is listed. Coordinate with other account users.

```bash
docker compose exec -T -e PYTHONPATH=/app api python scripts/cordis_extract.py \
  --start 'contenttype=project AND relations/associations/programme/code=HORIZON' \
  --format json --wait
```

Record the returned `taskID`. `--wait` polls for up to ten minutes; if the result
is still pending, keep checking that **same task**, rather than creating another.
Substitute its integer ID for `TASK_ID` below:

```bash
docker compose exec -T -e PYTHONPATH=/app api python scripts/cordis_extract.py --status TASK_ID
docker compose exec -T -e PYTHONPATH=/app api python scripts/cordis_extract.py \
  --download TASK_ID --output data/cordis_exports/horizon-TASK_ID-json.zip
```

Download only after the task completes. The destination must not already exist.
CORDIS credentials/download tokens are omitted from displayed task summaries.
See [the API details](cordis-api.md) for formats, limits and failure behaviour.

## 2. Validate, then apply

Replace the filename and task ID below with the values from the download:

```bash
# Default: parse and validate; no database changes or embedding requests.
make refresh-cordis CORDIS_ARGS='--export data/cordis_exports/horizon-TASK_ID-json.zip --source-task-id TASK_ID'
```

The command prints a private run directory such as
`/app/data/cordis_runs/20261109T120000-abcd1234`. Inspect its `validate.log`, which
contains the project/participation counts and newest source date. If the export
is suitable, continue that validated run:

```bash
make refresh-cordis CORDIS_ARGS='--resume data/cordis_runs/RUN_DIRECTORY --apply'
```

Alternatively, validate and apply in a single run:

```bash
make refresh-cordis CORDIS_ARGS='--export data/cordis_exports/horizon-TASK_ID-json.zip --source-task-id TASK_ID --apply'
```

`--source-task-id` records provenance; it is optional for an independently supplied
export and is never guessed from its filename. The runner also records the file's
SHA256. The default embedding batch size is 100; use `--batch-size 50` when creating
a new run if smaller batches are needed. A resumed run retains its settings.

Without Make, the equivalent entry point is:

```bash
docker compose exec -T -e PYTHONPATH=/app api python scripts/refresh_cordis.py --help
```

## 3. What the runner does

| Stage | Action |
|---|---|
| `validate` | Validate the entire bounded JSON export before writes. |
| `import` | Back up affected projects, vectors and consortium rows; update project/consortium records in one transaction. Preserve newer versions, unrelated projects and matching consortium UUIDs. Invalidate vectors when title/objective changes. |
| `indexes` | Build keyword and consortium indexes concurrently; update PostgreSQL statistics. |
| `graph` | Back up graph nodes/relationships; refresh project/topic/cluster and consortium edges; rebuild derived partnerships. |
| `embeddings` | Generate missing/invalidated vectors. Reject missing, zero or malformed vectors and skip concurrent text edits. Commit valid batches. |
| `verify` | Compare source fields, project IDs, consortium pairs and eligible vector coverage; exercise production project lookup, keyword search, semantic search and Dutch partner discovery. |
| `cache` | Invalidate project/partner/statistics results and plan hints. Preserve conversations and sessions. |
| `snapshot` | Save verified source provenance and the actual import timestamp for project/partner answers. |

The runner holds a local exclusive lock and stops at the first failure. Do not
run standalone import/graph/embedding commands concurrently with it. Embeddings
use the configured model; this workflow does not perform a model migration.
The source mapping is intentionally scoped to Horizon Europe.

## 4. Check completion and recover from interruption

Each run keeps `manifest.json`, per-stage logs and `verification.json` under
`data/cordis_runs/`. They are private local artifacts excluded from Git.
Only `manifest.json: status=complete` together with
`verification.json: complete=true` means the workflow completed. A nonzero exit
or a failed/interrupted/running stage needs attention.

After fixing the cause, resume the same run:

```bash
make refresh-cordis CORDIS_ARGS='--resume data/cordis_runs/RUN_DIRECTORY --apply'
```

Completed stages are skipped. The failed/incomplete stage is rerun. Graph writes
are batched, so an interrupted graph stage must finish before claiming graph
consistency. Embeddings resume from pending/missing rows. If the process died
after a commit but before recording success, rerunning the import is safe; it
may create another backup. A changed export digest is refused: start a new run
for a different file. Never edit the manifest to mark a failed stage complete.

Backups live in `data/cordis_backups/`. Import/graph logs record their exact paths.
PostgreSQL/consortium updates roll back together on an import error. A graph
failure does not roll back PostgreSQL; resume graph refresh from the committed
source. For intentional rollback, inspect the backup and restore all affected
stores together; there is no automated cross-store rollback command.

Thirty projects in the November snapshot did not meet the existing title/objective
length threshold for vector generation. Such records remain available through
structured/keyword lookup. The final check requires vectors for every eligible
project, rather than silently claiming every record has enough source text.

No automatic CORDIS schedule is enabled by this runner. This produces a verified
snapshot, not a live guarantee of every EU programme's coverage. The prior
completed run is documented in [the 8 November report](cordis-refresh-2026-11-08.md).

## Individual commands

Use these for diagnosis when the runner is stopped:

```bash
docker compose exec -T -e PYTHONPATH=/app api python scripts/import_cordis_projects.py EXPORT.zip --det-json
docker compose exec -T -e PYTHONPATH=/app api python scripts/import_cordis_projects.py EXPORT.zip --det-json --apply
docker compose exec -T -e PYTHONPATH=/app api python scripts/cordis_refresh_support.py indexes
docker compose exec -T -e PYTHONPATH=/app api python scripts/sync_cordis_graph.py --apply
docker compose exec -T -e PYTHONPATH=/app api python scripts/refresh_project_embeddings.py --batch-size 100
docker compose exec -T -e PYTHONPATH=/app api python scripts/verify_cordis_refresh.py EXPORT.zip --output data/cordis-verification.json
docker compose exec -T -e PYTHONPATH=/app api python scripts/cordis_refresh_support.py cache
```

Inspect verification before cache invalidation; do not treat an intermediate
command's successful exit as proof that the complete refresh succeeded.
