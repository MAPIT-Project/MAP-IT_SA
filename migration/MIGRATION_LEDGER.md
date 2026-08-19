# MAP-IT migration ledger

**Checked on:** 20 July 2026
**Scope:** the six SQL files now in `migration/`, plus Git history for the missing numbers 003–007.

## Conclusion

The files in this folder form **not a linear, reproducible migration chain**. The numbers indicate a historical order, but:

- `schema.sql` is a wide snapshot of a running Supabase/PostgreSQL database and overlaps the individual migrations;
- `001_init_schema.sql` is a much smaller, alternative bootstrap with conflicting table types;
- `002_upgrade_embeddings_to_3072.sql` is not Git-tracked and is not compatible with `001` without additional columns;
- 003–007 used to exist in Git, but have been removed from the current tree;
- `008` and `009` overlap objects already in `schema.sql`;
- `cleanup_unused_tables.sql` is destructive and is not the same file as the historical `022_cleanup_unused_tables.sql`.

Therefore, do not blindly run these files one after the other. There is currently no CI tested fresh database chain.

## Status definition and evidence limit

In this ledger means:

- **applied:** the exact file version/checksum is recorded in a reliable migration table or deployment registration;
- **unapplied:** reliable registration proves that the migration has not yet been performed;
- **unknown:** objects or effects may be present, but cannot be linked to the exact file version.

None of the current single SQL files meet the first two levels of evidence. That's why their status below is **unknown**. The presence of a table in a snapshot proves the database shape, but not which script created that shape.

Wave 1 recorded that the examined local `public.schema_migrations` contained only `v2.0.1_citations_table` and `022_cleanup_unused_tables` and that the Drizzle ledger contained one hash. The current `cleanup_unused_tables.sql` does not write a ledger record itself and differs substantively from the historical migration 022; so that local record does not prove that this current file was applied.

## Manifest of the current files

The date column is a **source date**, not a proven execution date. The five tracked files have no date header; their current contents came entirely into Git in commit `6d446b0` from 19 May 2026. `002` has no Git provenance or date header.

| No. | File | Source date | SHA-256 | Target | Status | Hard/logical dependencies |
|---:|---|---|---|---|---|---|
| 001 | `001_init_schema.sql` | 2026-05-19 (current Git version) | `6c7a7111218c50ea8c3f189474340a522bb9b9bdc5705fbffda98cfbd99dfc28` | Small backend bootstrap with nine tables for projects, organizations, calls, documents/chunks, shared documents/chunks and embedding cache. | **unknown** | PostgreSQL 14+, `vector`, `uuid-ossp`; intended for an empty database. No dependency on `schema.sql`: this is an alternative baseline path. |
| 002 | `002_upgrade_embeddings_to_3072.sql` | unknown; untracked, no date header | `ffcf6082f0114afe9c7d70cb90167073b03f6e08297bb71cfbbf4b3c87be4ff6` | Drops and recreates the embedding columns of `funding_calls`, `document_chunks` and `embedding_cache` as `vector(3072)`, clears the cache and sets Gemini model defaults. | **unknown** | `vector`; the three tables; additionally `document_chunks.embedding_model` and `embedding_cache.model_version`. The last two columns exist in `schema.sql`, but not in `001`. Existing embeddings must then be regenerated. |
| 008 | `008_tool_analytics.sql` | 2026-05-19 (current Git version) | `5d3e85bf7c2f72a3ae6bbc16777e096738e43c696c5abc45a043057a46b0e60f` | Creates `conversation_analytics`, `tool_usage_analytics` and `tool_combination_analytics` plus basic indexes. | **unknown** | PostgreSQL with array and JSONB support; no foreign key dependency. Logical after a baseline, but not after applying `schema.sql` because the three tables are already there, with partly different column types/constraints. |
| 009 | `009_user_feedback.sql` | 2026-05-19 (current Git version) | `a9efee230989b9caf2ad925a94c002714500cc71572509b9c268c3820bd101ec` | Creates `response_feedback` and `feedback_insights` plus basic indexes. | **unknown** | PostgreSQL with arrays and JSONB; no foreign key dependency. Makes sense after a baseline. After `schema.sql`, `response_feedback` would already exist and `feedback_insights` would be reintroduced despite the later cleanup. |
| — | `cleanup_unused_tables.sql` | 2026-05-19 (current Git version) | `f01f1cf7c4799a80d77cebdaf7056596f8dec4f28c4ac40c3a17b2e1b6e61577` | Drops sixteen tables marked as unused with `CASCADE`, including `feedback_insights` and old document, proposal, analytics and cache tables. | **unknown** | No hard table dependency by `DROP TABLE IF EXISTS`; logical only after the features that created the tables. Destructive, without rollback and without insert in `schema_migrations`. |
| snapshot | `schema.sql` | 2026-05-19 (current Git version); dump date missing | `f0fbb64a4b500eff8eb2fa2a6f3c89b2fb95a016c1f25e4c27c481731a10d6c3` | Schema-only snapshot of PostgreSQL 15.8 with Supabase platform schemas and MAP-IT objects: including 35 public tables and 15 public views, functions, RLS, grants, triggers and indexes. | n/a; this is a snapshot, not an incremental migration | A compatible Supabase/PostgreSQL 15 environment, extensions and roles from the source database. Not demonstrated as generic empty-PostgreSQLbootstrap. |

## Relationship between `schema.sql` and the individual migrations

`schema.sql` is not a successor to `001`. It is an alternative, much more comprehensive baseline generated from a running database. The two files define the same core objects differently. Examples:

- `projects.id` is `varchar(50)` in `001` and `integer` in the snapshot;
- `organizations` has a serial `id` and a `varchar` project reference in `001`, but in the snapshot a UUID `id` and integer `projectID`;
- `funding_calls.id` is serialized in `001` and UUID in the snapshot;
- document and shared document tables differ in columns, keys, and types;
- the snapshot also contains frontend, proposal, collaboration, analytics, feedback and Supabase objects that `001` does not create.

The snapshot already contains the three tables from `008`, but not with exactly the same contract. `CREATE TABLE IF NOT EXISTS` does not migrate an existing table: it leaves the existing, non-standard structure. The same goes for `response_feedback` from `009`. `feedback_insights` is missing as a table in the snapshot, while there are still dump residues with that name, such as a sequence/ACL; the current cleanup script drops just that table.

Moreover, the snapshot has not immediately been proven as a reliable executable script:

- lines 9–12 contain four uncommented `pg_dump:` diagnostic lines and are therefore not valid SQL;
- the file creates and modifies Supabase schemas, extensions, owners, ACLs and event triggers and assumes associated roles;
- it contains no table data;
- it represents a state, not the steps by which that state was reached.

`schema.sql` must therefore first be cleaned as a restore baseline and tested on an empty, compatible Supabase instance before it can serve as an authoritative baseline.

## The hole 003–007

The missing numbers aren't just hypothetical. Git history contains the following deleted files:

| Number | Historical file | First Git record | Current state |
|---:|---|---|---|
| 003 | `003_call_documents_tables.sql` | 2025-10-08, commit `35a92d2` | deleted in `bb90f94` on 2026-05-13 |
| 004 | `004_shared_documents_architecture.sql` | 2025-10-08, commit `35a92d2` | deleted in `bb90f94` on 2026-05-13 |
| 005 | `005_call_metadata_table.sql` | 2025-10-08, commit `35a92d2` | deleted in `bb90f94` on 2026-05-13 |
| 005 | `005_proposal_writing_system.sql` | 2025-10-11, commit `be18822` | deleted in `bb90f94` on 2026-05-13 |
| 006 | `006_citations_table.sql` | 2025-10-16, commit `0f9137f` | deleted in `bb90f94` on 2026-05-13 |
| 007 | `007_add_citations_to_message_table.sql` | 2025-10-16, commit `0f9137f` | deleted in `bb90f94` on 2026-05-13 |

So there were even two different migrations with number 005. The current `schema.sql` contains objects from these domains, such as shared documents, call metadata, citations, messages and proposal objects, but that does not prove that every historical file has been run on the examined database. Migrations 010–022 also existed historically and were removed from the workbook in the same cleanup commit. Therefore, retrieving 003–007 from Git would not in itself restore a complete or secure chain.

## Vector transition 768 to 3072

The transition is partially recorded in the baselines and explicitly in `002`:

| Object | `001_init_schema.sql` | `schema.sql` | Effect of `002` |
|---|---:|---:|---|
| `project_embeddings.combined_embedding` | 3072 | 3072 | unchanged; `002` does not touch this table |
| `funding_calls.embedding` | 768 | 768 | drop column and recreate as 3072 |
| `document_chunks.embedding` | 768 | 768 | drop column and recreate it as 3072; model default to `gemini-embedding-001` |
| `embedding_cache.embedding` | 768 | 768 | cache truncate; recreate column as 3072; model default to `gemini-embedding-001` |
| `shared_document_chunks.embedding` | 768 | not present in this snapshot model | unchanged; not treated by `002` |

The operation in `002` is deliberately destructive: existing 768 vectors are lost. After application, calls, document chunks and cache must be rebuilt. The snapshot contains IVFFlat indexes for the 768 dimensional call and chunk columns; after dropping those columns, no equivalent 3072 indexes from `002` remain. Exact/sequential vector searches remain possible, but index strategy and pgvector version must be validated separately.

`001` also creates a HNSW index on `project_embeddings.combined_embedding vector(3072)`. Standard pgvector indexing on type `vector` does not automatically support more than 2.000 dimensions; That is also why `001` has not been proven to be a working fresh bootstrap.

## Order for a fresh database

With only the current files, there exists **no completely correct, directly executable sequence**. The safest reconstruction of the intended broad application state, after explicit DBA review, is:

1. Start a compatible empty Supabase/PostgreSQL 15 instance with the required roles and extensions.
2. Make `schema.sql` a clean, tested baseline and apply only that baseline. The current file should not be run blindly unchanged due to the bare `pg_dump:` rules and environment dependencies.
3. Review and version `002_upgrade_embeddings_to_3072.sql`; apply it afterwards. This is the only current file that logically belongs on top of the 768 snapshot.
4. Load relational data and document/call content, then regenerate all affected embeddings on 3072 dimensions.
5. Validate table contracts, vector dimensions, search functions, indexes, RLS, grants and application smokes.

In this snapshot path, `001`, `008`, `009`, and `cleanup_unused_tables.sql` **not** are executed next:

- `001` is an alternate conflicting baseline path;
- `008` is already included in the snapshot and can only add redundant indexes without correcting anomalous tables;
- `009` overlaps `response_feedback` and would return the cleaned table `feedback_insights`;
- the snapshot largely reflects the cleanup, while redoing with `CASCADE` is unnecessarily destructive.

The alternative `001` path is only a limited backend prototype, not a fresh full MAP-IT database. `002` fails there directly on the missing columns `document_chunks.embedding_model` and `embedding_cache.model_version`; Moreover, the removed intermediate migrations and other app domains are missing. This path is therefore not a recommended production sequence.

## ARecommended sequel, not performed in this wave

1. Choose one schema authority: a cleaned snapshot baseline or a fully reconstructed migration chain, not both.
2. Include each subsequent schema change file Git-tracked with unique version, checksum, date, dependency, forward-fix/rollback policy, and ledger insert.
3. Record the 3072 transition and the mandatory re-embedding as one controlled release procedure.
4. Migrate CI from an empty Supabase instance, then check object contracts and vector dimensions.
5. Archive deleted historical SQL explicitly or document why it was superseded by the chosen baseline; don't blindly restore it to the active chain.
