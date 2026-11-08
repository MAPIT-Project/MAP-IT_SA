# CORDIS Data Extraction Tool connection

MAPIT now has a server-side client for the
[official DET API](https://cordis.europa.eu/about/dataextractions-api), following
its [published OpenAPI contract](https://cordis.europa.eu/dataextractions/api-docs).
The helpdesk approval email confirms access, but does not contain the key.

## Configure and verify

Put the existing key under `CORDIS_API_KEY` in the backend's private `.env`.
Do not put it in frontend environment variables, Git, command arguments or chat.
The setting uses Pydantic `SecretStr`; empty values mean unconfigured. The DET
contract requires the key as a query parameter, so the client avoids URL logging
and hides transport exceptions and response bodies that could echo it.

Run from the repository root:

```bash
docker exec -e PYTHONPATH=/app map-it_sa-api-1 python scripts/cordis_extract.py --check-key
```

This only lists existing extractions. It does not start, cancel or delete one.
If a running API container already has an older `CORDIS_API_KEY` environment
value, recreate it after changing `.env`:

```bash
docker compose up -d --no-deps api
```

`GET /api/health/cordis` reports configuration only. `configured_unverified`
does not mean authentication or a data refresh has succeeded.

## Extract and download

Use the CORDIS expert query syntax. Start with one known project ID from your
local database, substituting its ID below:

```bash
docker exec -e PYTHONPATH=/app map-it_sa-api-1 python scripts/cordis_extract.py \
  --start 'contenttype=project AND /project/id=PROJECT_ID' --format csv
docker exec -e PYTHONPATH=/app map-it_sa-api-1 python scripts/cordis_extract.py --status TASK_ID
docker exec -e PYTHONPATH=/app map-it_sa-api-1 python scripts/cordis_extract.py \
  --download TASK_ID --output data/cordis_exports/TASK_ID.export
```

`--wait` can poll a newly created extraction for up to ten minutes, at 15-second
intervals. Unknown statuses remain pending until checked against a real response.
Live authentication and extraction were verified on 2026-11-08. The full
Horizon Europe JSON export was subsequently validated for project and consortium
refresh; see [the refresh procedure](cordis-refresh.md).

CORDIS allows only one running extraction and a new extraction may cancel the
old one. The client checks the task list and refuses to start when a task is
active or its state is unknown. There is still a server-side race if another
person starts an extraction between that check and creation. A reported
concurrent cancellation stops the workflow. No automatic extraction schedule is
enabled; no cancellation/deletion operation is exposed.

Downloads accept only the CORDIS HTTPS origin and same-origin redirects, have a
250 MB limit, use private files and never replace an existing export. Download
URLs/tokens are omitted from displayed task summaries. Exports are not approved
or imported just because downloading succeeded.

## Import into the existing project database

```bash
docker exec -e PYTHONPATH=/app map-it_sa-api-1 python scripts/import_cordis_projects.py \
  data/cordis_exports/TASK_ID.export
docker exec -e PYTHONPATH=/app map-it_sa-api-1 python scripts/import_cordis_projects.py \
  data/cordis_exports/TASK_ID.export --apply
```

The first command validates without writes. Supported inputs are the canonical
UTF-8 project CSV or a ZIP with one `project.csv`/`projects.csv`. Required columns:
`id`, `title`, `objective`, `contentUpdateDate`. The first live DET export must be
inspected; if DET returns a different layout, the importer fails before writes
and that layout must be mapped explicitly. It never guesses unknown schemas.

The importer upserts only source project fields, skips older source versions,
retains all projects outside the export, and preserves optional blank fields.
A private compressed backup of affected projects and embeddings is made before
updates. All rows commit together; errors roll back the import. Changed title or
objective vectors are cleared and marked pending, avoiding stale semantic
matches. Keyword search remains available. Regenerate project embeddings through
the existing embedding pipeline after inspecting the first import.

The default canonical CSV mode does not refresh organization/consortium records,
Neo4j or existing response caches. The explicit `--det-json` mode imports project
and consortium records together; graph and embedding refreshes are separate
commands documented in [the refresh procedure](cordis-refresh.md). CSV mode
reports `organizations_refreshed=false`.
The validated JSON mapping preserves multiple consortium roles and regional
codes. No unattended sync is enabled.

Live authentication, a single-project extraction, download and import dry run
were verified on 2026-11-08. DET uses a nested `csv.zip` archive, string `"true"`
for creation status, `taskId` in task lists and `s3.cordis.europa.eu` downloads;
these observed formats are supported. No production project records were changed
during that initial single-project check. The later full refresh is recorded
separately in the refresh report. A full unattended synchronization remains to be
configured.

CORDIS projects/results are a separate source from Funding & Tenders calls and
the Commission legal-document register. This key does not grant access to the
missing LIFE main decision or establish dates on undated cost decisions.
