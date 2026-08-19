# Data ingestion and data bootstrap

**Status:** current runbook, with known blockers

**Last verified:** 20 July 2026

**Workbook for all commands:** `MAP-IT_SA/`

This runbook describes what is and is not reproducible from a fresh clone. The relational schema, document collection, CORDIS projects, embeddings, and Neo4j graph are separate datasets. A successful schema installation therefore does not mean that MAPIT can provide representative search results.

See also [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) for the current schedule and migration contract and [START_HERE.md](../../../START_HERE.md) for starting the services.

## First read: current blockers

| Blocker | Actual situation | Consequence |
|---|---|---|
| No distributed PostgreSQL baseline | The local `mapit_dump.dump` is not Git tracked. `neo4j_backup/project_embeddings.dump` is excluded by `.gitignore` and according to `pg_restore -l` only contains data for `public.project_embeddings`. | A fresh clone cannot restore the 13.865 projects, 89.348 organizational participations and other relational data from the repository. |
| No raw CORDIS import to PostgreSQL | There is only `scripts/ingest_cordis_to_neo4j.py`; there is no script that imports `project.csv` and `organization.csv` to PostgreSQL. | Raw CORDIS files can fill the graph, but do not solve the missing relational project dataset. |
| CORDIS source folder is missing | `data/` is Git-ignored and `data/cordis/` is missing. The Neo4j script expects exactly `project.csv` and optionally `organization.csv`. | The raw Neo4j ingestion stops immediately without `project.csv`. |
| Horizon processing folders missing | `process_comprehensive_docs.py` reads `downloads/horizon_europe_comprehensive/`; `ingest_comprehensive_docs.py` reads `processed_docs/horizon_europe/ingestion_ready.jsonl`. Both folders are missing in a clone. | The scripts are not a single-step ingestion of `newdocs/`. The source files must first be staged and processed to the expected structure. |
| Shared documents are missing in a clone | The five locally present PDF's under `data/shared_documents/` fall under the Git-ignore for `data/`. | `process_shared_documents.py` has no input in a fresh clone. The message in that script about `download_shared_documents.py` is not executable: that download script does not exist. |
| 3072 migration not guaranteed | `migration/002_upgrade_embeddings_to_3072.sql` and the two `reembed_*.py` scripts are present in the examined work tree but not Git tracked. | The running local database is 3072 dimensional, but a clone of the current Git baseline remains for document, call, and cache vectors on 768 dimensions. |

The currently supported transfer route is therefore: ask the data owner for a versioned, encrypted PostgreSQL artifact with manifest, or explicitly accept a restricted environment without relational CORDIS data. Before transfer, publish at least artifact name, creation date, schema and data version, SHA-256, size, source licenses, and an authorized contact. `Owner: TBD` is currently still an open blocker.

## Requirements

1. Start PostgreSQL/Supabase and Neo4j according to [START_HERE.md](../../../START_HERE.md).
2. Activate the virtualenv created by `scripts/setup.sh`:

   ```bash
   source venv/bin/activate
   ```

3. Put at least the following variables in `.env` or the shell:

   ```dotenv
   DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
   SUPABASE_URL=http://localhost:54321
   SUPABASE_SERVICE_KEY=<lokale-service-role-key-uit-supabase-start>
   GOOGLE_EMBEDDING_API_KEY=<google-ai-key>
   EMBEDDING_MODEL=models/gemini-embedding-001
   EMBEDDING_DIMENSION=3072
   NEO4J_URI=bolt://localhost:17687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=<zelfde-wachtwoord-als-docker-compose>
   ```

`EmbeddingService` falls back from `GOOGLE_EMBEDDING_API_KEY` to `GEMINI_API_KEY` for the API key. For host processes, Compose uses Neo4j port `17687`; within the Compose network this is `bolt://neo4j:7687`.

4. Check connection and vector dimensions before writing data:

   ```bash
   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c 'select current_database(), version();'
   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "select table_name, column_name, format_type(a.atttypid,a.atttypmod) as type from information_schema.columns c join pg_class t on t.relname=c.table_name join pg_namespace n on n.oid=t.relnamespace and n.nspname=c.table_schema join pg_attribute a on a.attrelid=t.oid and a.attname=c.column_name where c.table_schema='public' and c.column_name='embedding' order by table_name;"
   ```

Do not proceed if the database reports `vector(768)` while the application uses `EMBEDDING_DIMENSION=3072`.

## Choose a bootstrap mode

### Mode A — full, approved PostgreSQL dump

This is the only route that can now fully reproduce the relational CORDIS baseline. The dump must be provided outside of Git by the data owner. The dumps found locally are not a transferable artifact contract.

Before recovery check:

```bash
export MAPIT_DATA_DUMP=/absoluut/pad/naar/mapit-postgres-<dataversie>.dump
test -r "$MAPIT_DATA_DUMP"
sha256sum "$MAPIT_DATA_DUMP"
pg_restore --list "$MAPIT_DATA_DUMP" | less
```

Make a backup first. The following restore command removes objects from the target database and is intended only for an empty, compatible local Supabase instance:

```bash
pg_dump --format=custom --file="pre-mapit-restore-$(date +%Y%m%d-%H%M%S).dump" "$DATABASE_URL"
pg_restore --clean --if-exists --no-acl --no-owner \
  --exit-on-error --dbname="$DATABASE_URL" "$MAPIT_DATA_DUMP"
```

A full dump can contain Supabase control schemes (`auth`, `storage`, `realtime`). Do not restore it across a shared or production instance without an owner-tested restore procedure. `neo4j_backup/project_embeddings.dump` is not an alternative: that artifact contains only `project_embeddings` rows and requires that the corresponding `projects` already exist.

Expected local reference after a full restore, measured at 20 July 2026:

| Dataset | Expected quantity | Verification |
|---|---:|---|
| `projects` | 13.865 | `SELECT count(*) FROM projects;` |
| `organizations` | 89.348 | `SELECT count(*) FROM organizations;` |
| `project_embeddings` | 13.850, all 13.850 filled | `SELECT count(*), count(combined_embedding) FROM project_embeddings;` |
| `horizon_documents` | 144 | `SELECT count(*) FROM horizon_documents;` |
| `document_chunks` | 38.697, all 38.697 filled | `SELECT count(*), count(embedding) FROM document_chunks;` |
| `shared_documents` / `shared_document_chunks` | 54 / 13.147 | Two separate `count(*)` queries |
| `funding_calls` | 2.758, all 2.758 filled | `SELECT count(*), count(embedding) FROM funding_calls;` |

These numbers are a local reference snapshot, not a universal acceptance criterion for future data releases. Deviations must be explained by the artifact manifest.

### Mode B — schedule plus restricted data

Use this mode when an approved dump is not available. Install the scheme as described in [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md). Please take into account the migration drift described there: there is no deterministic, fully tested migration chain yet. Without additional imports, relational CORDIS tools remain empty; document-RAG and hardcoded program references can be entered separately.

## Dataset runbooks

### 1. CORDIS projects and organizations in PostgreSQL

| Part | Value |
|---|---|
| Source Artifact | Complete PostgreSQL dump provided by the data owner |
| Raw alternative | Not implemented for PostgreSQL |
| Requirements | Schema corresponding to the dump; `projects.id` and `organizations."projectID"` are in the current database `integer` |
| Expected | Artifact Manifesto; local reference 13.865 projects and 89.348 organizational participations |
| Idempotency | Only via full restore to a controlled target instance |

Restore Mode A and then run:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
SELECT count(*) AS projects FROM projects;
SELECT count(*) AS organizations FROM organizations;
SELECT count(*) FILTER (WHERE title IS NULL) AS projects_without_title FROM projects;
SELECT count(*) AS organizations_without_project
FROM organizations o
LEFT JOIN projects p ON p.id=o."projectID"
WHERE p.id IS NULL;
SQL
```

Stop when `projects_without_title` or `organizations_without_project` is unexpectedly non-zero. There is no repository script to reliably rebuild these tables from raw CSV.

### 2. CORDIS graph in Neo4j

There are two routes.

#### 2a. Restore tracked Neo4j dump

`neo4j_backup/neo4j.dump` is Git tracked. The SHA-256 of the version examined on 20 July 2026 is `8363cefa4067d2320bf9fbc48cd16447616d9f8e517da59c0e111249bc5db3e2` (63.643.498 bytes). Check the checksum after clone.

```bash
sha256sum neo4j_backup/neo4j.dump
docker cp neo4j_backup/neo4j.dump mapit-neo4j:/var/lib/neo4j/import/neo4j.dump
docker compose stop neo4j
docker compose run --entrypoint neo4j-admin --rm neo4j database load \
  --from-path=/var/lib/neo4j/import/ neo4j --overwrite-destination=true
docker compose start neo4j
```

`docker cp` prevents host access to the bindmount. `neo4j/import/` may have been created by the container as another UID. For `Permission denied`: stop the container, first inspect `ls -ld neo4j neo4j/import`, and have the owner of the development machine correct the ACL/property specifically. Do not use recursive `chmod 777`.

The local graph running on 20 July 2026 contained 13.865 `Project` nodes, 25.096 unique `Organization` nodes, and 89.263 `PARTICIPATES_IN` relationships. Verify:

```cypher
MATCH (p:Project) RETURN count(p) AS projects;
MATCH (o:Organization) RETURN count(o) AS organizations;
MATCH (:Organization)-[r:PARTICIPATES_IN]->(:Project)
RETURN count(r) AS participations;
```

#### 2b. Ingest raw CORDIS-CSV

Download the official Horizon Europe CORDIS export named in [EU_PROGRAMME_DATA_DOWNLOADS.md](../../docs_tracked/EU_PROGRAMME_DATA_DOWNLOADS.md) and record source URL, download time, license and SHA-256. Extract at least these semicolon-separated UTF-8 files:

```text
data/cordis/project.csv       required
data/cordis/organization.csv  optional, but required for partner and consortium analysis
```

The script uses `on_bad_lines="skip"`; thus it can skip invalid source lines. Always compare the log numbers with `wc -l` and save the error log.

```bash
python scripts/ingest_cordis_to_neo4j.py --data-dir data/cordis
```

The script uses `MERGE` and is largely repeatable. However, `--clear` runs `MATCH (n) DETACH DELETE n` and erases the **whole** Neo4j database, including other program data. Only use that flag after a backup and explicit approval.

Expect the same CORDIS export as the reference snapshot to see 13.865 projects. The number of unique organizations is lower than the number of lines in `organization.csv`, because organizations are merged across projects; the local reference is 25.096 unique nodes and 89.263 participation relationships.

### 3. Project embeddings

Active code configuration: `models/gemini-embedding-001`, `output_dimensionality=3072`. The script combines title and objective, truncates characters at 2.000 and processes standard batches of 50. It only stores projects with a usable title and objective.

Prerequisites: filled `projects`, `project_embeddings.combined_embedding vector(3072)`, `DATABASE_URL` and a Google/Gemini embedding key.

```bash
# Safe first test: maximum 10 projects
python scripts/generate_project_embeddings.py --test --verbose

# Then all missing/failed/pending projects
python scripts/generate_project_embeddings.py --batch-size 50
```

Restarting is intended as a resume: existing rows with status `completed` are skipped; writes use `ON CONFLICT (project_id) DO UPDATE`.

```sql
SELECT count(*) AS eligible_projects
FROM projects
WHERE title IS NOT NULL AND objective IS NOT NULL
  AND length(title) > 10 AND length(objective) > 50;

SELECT embedding_status, count(*)
FROM project_embeddings
GROUP BY embedding_status ORDER BY embedding_status;

SELECT model_version, count(*), count(combined_embedding)
FROM project_embeddings GROUP BY model_version;
```

The local reference is 13.850 filled embeddings versus 13.865 projects; the difference is not automatically an error, because the script applies content filters.

### 4. Program documents to `horizon_documents` and `document_chunks`

The following input is Git-tracked. First run `--dry-run`; this demonstrably does not do any database writes.

| Dataset | Default source | PDF's in clone on 20-07-2026 | Exact command |
|---|---|---:|---|
| Erasmus+ | `newdocs/erasmus` (only PDF's directly in the folder) | 2 | `python scripts/ingest_erasmus_documents.py --source-dir newdocs/erasmus` |
| Creative Europe | `newdocs/creative_europe` (recursive) | 10 | `python scripts/ingest_creative_europe_documents.py --source-dir newdocs/creative_europe` |
| Digital Europe | `newdocs/digital_europe` (recursive) | 7 | `python scripts/ingest_digital_europe_documents.py --source-dir newdocs/digital_europe` |
| EU4Health | `newdocs/eu4health` (recursive) | 6 | `python scripts/ingest_eu4health_documents.py --source-dir newdocs/eu4health` |
| LIFE | `newdocs/life` (recursive) | 4 | `python scripts/ingest_life_documents.py --source-dir newdocs/life` |

Example:

```bash
python scripts/ingest_creative_europe_documents.py \
  --source-dir newdocs/creative_europe --dry-run
python scripts/ingest_creative_europe_documents.py \
  --source-dir newdocs/creative_europe
```

Each ingestion creates one document and a data-dependent number of chunks per file. The script summary should show `successful + failed = number of PDFs found`. Duplicates are rejected on file hash and reported as failure; a completely repeated run is therefore not cleanly idempotent. In the case of a partial error, a document row with status `failed` may already exist. Do not delete such rows manually without also checking the dependent chunks and the source hash.

Verification:

```sql
SELECT metadata->>'programme' AS programme,
       count(*) AS documents,
       sum(total_chunks) AS geregistreerde_chunks
FROM horizon_documents
GROUP BY 1 ORDER BY 1;

SELECT status, count(*) FROM horizon_documents GROUP BY status;
SELECT count(*) AS chunks, count(embedding) AS embedded_chunks
FROM document_chunks;
```

The local snapshot contained 2 Erasmus, 8 Creative Europe, 6 Digital Europe, 6 EU4Health and 4 LIFE document records respectively. The fact that Creative Europe is lower than the 10 current source PDF's underlines that source file count and database count should not be automatically assumed to be the same.

### 5. Horizon Europe 2025 work programs

The clone contains 13 PDFs under `newdocs/2025_work_programmes`, but the two-step comprehensive path expects other directories. A minimum staging for exactly this collection is:

```bash
mkdir -p downloads/horizon_europe_comprehensive/{work_programmes,programme_guides,call_pages,additional_resources}
cp newdocs/2025_work_programmes/*.pdf \
  downloads/horizon_europe_comprehensive/work_programmes/
python scripts/process_comprehensive_docs.py
test -s processed_docs/horizon_europe/ingestion_ready.jsonl
wc -l processed_docs/horizon_europe/ingestion_ready.jsonl
python scripts/ingest_comprehensive_docs.py --batch-size 200 --max-concurrent 10
```

The output count is data and chunking dependent; the acceptance criterion is that `processing_stats.json` declares thirteen processed documents, `ingestion_ready.jsonl` is not empty, and all written chunks have a 3072 vector. The flag `--skip-existing` of `ingest_comprehensive_docs.py` does not currently change the implementation; existing documents are always checked via file-path. So don't use that flag as a quality or idempotency guarantee.

### 6. Shared documents

Prerequisites: owner-supplied PDFs in `data/shared_documents/`, a populated `shared_documents`/`shared_document_chunks` schema family and `DATABASE_URL`.

```bash
python scripts/process_shared_documents.py
```

`--force` also reprocesses already known file hashes and is potentially duplicative/destructive to data quality. Without a flag, known hashes are skipped. The local non-transferable reference contains five source PDFs, but the database contained 54 documents and 13.147 chunks; therefore, don't expect 1-on-1 equality with the local directory.

```sql
SELECT count(*) FROM shared_documents;
SELECT count(*) FROM shared_document_chunks;
SELECT count(*) FROM shared_documents d
WHERE NOT EXISTS (
  SELECT 1 FROM shared_document_chunks c WHERE c.document_id=d.id
);
```

### 7. Synchronize and embed funding calls

`sync_topics_from_projects.py` reads unique Horizon topic codes from the existing `projects` table, retrieves missing details from the EU Funding & Tenders topic endpoint and upserts to `topic_code`. There are no CLI flags and no dry run.

```bash
python scripts/sync_topics_from_projects.py
```

Prerequisites: relational CORDIS projects, network access and `DATABASE_URL`. The script commits per topic; after a network error it can be restarted safely because only missing topics are retrieved and existing topics are updated via `ON CONFLICT`.

The current code also contains the untracked `scripts/reembed_funding_calls.py`. Do not use this as a transfer command until it has been reviewed and committed. The production code expects 3072 dimensions; after each approved re-embedding check:

```sql
SELECT programme, count(*) AS calls, count(embedding) AS embedded
FROM funding_calls GROUP BY programme ORDER BY programme;
```

Local reference on 20 July 2026: 2.758 calls, all 2.758 with embedding; Horizon Europe 2.274, Erasmus+ 277, Creative Europe 128, LIFE 35, EU4Health 32 and Digital Europe 12.

### 8. Hardcoded program references in Neo4j

These scripts do not require any external source artifact: actions, strands, regions and rules are contained as Python constants in the scripts. They are therefore reproducible from code, but not automatically up to date with respect to official program rules.

```bash
python scripts/ingest_erasmus_to_neo4j.py
python scripts/ingest_creative_europe_to_neo4j.py
python scripts/ingest_digital_europe_to_neo4j.py
python scripts/ingest_eu4health_to_neo4j.py
python scripts/ingest_life_to_neo4j.py
```

Writes mainly use `MERGE`; redo should update nodes. The `--clear` flags remove nodes with the appropriate program-specific labels; shared `Country` nodes remain. Digital Europe, EU4Health and LIFE also remove their own `Programme` node. Verify the printed counts per script and then:

| Dataset | Source artifact | Expected core nodes from the code |
|---|---|---|
| Erasmus+ | Python constants in `ingest_erasmus_to_neo4j.py` | 22 actions, 6 sectors, 13 partner regions |
| Creative Europe | Python constants in `ingest_creative_europe_to_neo4j.py` | 3 strands, 24 actions, 3 regions |
| Digital Europe | Python constants in `ingest_digital_europe_to_neo4j.py` | 6 objectives, 2 actions, 5 regions and 1 own program node |
| EU4Health | Python constants in `ingest_eu4health_to_neo4j.py` | 4 strands, 7 actions, 4 regions and 1 own program node |
| LIFE | Python constants in `ingest_life_to_neo4j.py` | 4 subprograms, 5 project types, 4 regions and 1 own program node |

The relationship and `Country` counts depend on existing shared nodes; compare the summary of each script instead of enforcing one global static value.

```cypher
MATCH (n)
WHERE n:ErasmusAction OR n:CreativeEuropeAction OR n:DigitalEuropeAction
   OR n:EU4HealthAction OR n:LIFEProjectType
RETURN labels(n) AS labels, count(*) AS aantal
ORDER BY labels;
```

## 768 to 3072 dimensions

| Object | Git snapshot `migration/schema.sql` | Local DB 20-07-2026 | Active application code |
|---|---:|---:|---:|
| `project_embeddings` | 3072 | 3072 | 3072 |
| `document_chunks` | 768 | 3072 | 3072 |
| `funding_calls` | 768 | 3072 | 3072 |
| `embedding_cache` | 768 | 3072 (0 rows) | 3072 |

The local `document_chunks.embedding_model` values ​​still say `text-embedding-004`, despite 3072 dimensional vectors; that provenance is therefore inconsistent. Do not treat the column value as proof of the actual model used. Migration 002 drops the three old embedding columns, empties `embedding_cache` and requires full re-embedding. After the migration, the old IVFFlat indexes are not present in the local database; vector searches there use exact/sequential search. See [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) for details.

## Verification and quality gate

`scripts/quality_gate.py` is a conversation test result gate. The only supported flags are:

```text
--results-dir PATH
--quality-baseline PATH
--threshold INTEGER
--fail-on-missing
```

There are no `--check-embeddings` or `--check-calls` flags. For data quality, use the SQL and Cypher queries in this runbook. A complete final check:

```sql
SELECT 'projects' AS dataset, count(*) AS rows, NULL::bigint AS embedded FROM projects
UNION ALL SELECT 'organizations', count(*), NULL FROM organizations
UNION ALL SELECT 'project_embeddings', count(*), count(combined_embedding) FROM project_embeddings
UNION ALL SELECT 'horizon_documents', count(*), NULL FROM horizon_documents
UNION ALL SELECT 'document_chunks', count(*), count(embedding) FROM document_chunks
UNION ALL SELECT 'shared_documents', count(*), NULL FROM shared_documents
UNION ALL SELECT 'shared_document_chunks', count(*), NULL FROM shared_document_chunks
UNION ALL SELECT 'funding_calls', count(*), count(embedding) FROM funding_calls;
```

On each ingest run, record: Git commit, source URL and license, source date, SHA-256, input count, successful/skipped/failed records, schema and embedding version, execution time and operator. Without this manifesto, the run is not suitable as a new transfer baseline.
