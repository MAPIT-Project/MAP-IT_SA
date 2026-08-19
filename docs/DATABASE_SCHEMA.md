# Database schema and data architecture

**Status:** verified documentation snapshot

**Snapshot date:** 20 July 2026

**Sources:** `migration/schema.sql`, `migration/*.sql`, `webapp-ui/supabase_cli/schema.sql`, the frontend Drizzle migrations and read-only catalog queries against the running local Supabase and Neo4j instances

MAPIT uses PostgreSQL/Supabase for relational data, pgvector for embeddings and Neo4j for relationship-intensive analyses. This document deliberately distinguishes three realities: the Git schema files, the local database at the snapshot date, and the active application code. They are not yet completely equal.

See [DATA_INGESTION.md](guides/DATA_INGESTION.md) for recovery and data bootstrap and [SECURITY_REGISTER.md](../../SECURITY_REGISTER.md) for the security impact of the limited RLS coverage.

## Summary and authority

| Part | Current status |
|---|---|
| PostgreSQL | Local Supabase was running PostgreSQL 15.8 with pgvector 0.8.0. |
| `public` | 35 base tables, 15 views and 17 MAPIT functions in the local snapshot. |
| Schema snapshot | `MAP-IT_SA/migration/schema.sql` is the most fully tracked MAPIT snapshot. `webapp-ui/supabase_cli/schema.sql` is substantively the same pg_dump; the observed diff consists only of whitespace. |
| Migration authority | **Not established.** The repository contains parallel snapshots, backend SQL and frontend Drizzle migrations, but no reliable end-to-end migration ledger. |
| RLS | Only `document_chunks` and `horizon_documents` have RLS on; 33 other `public` tables do not. |
| Real-time | Only `public.message` is in `supabase_realtime`. |
| Embeddings | Active code and local DB use 3072 dimensions; the tracked full schema snapshot still uses 768 for documents, calls and cache. |

`migration/schema.sql` is therefore the **documentation baseline**, not a proven incremental migration. Do not use it as if it were migration 000 without a restore test on an empty Supabase instance: it also contains Supabase management schemes, owners, grants and platform objects.

## Reproducible catalog queries

From `MAP-IT_SA/`, run with the local default URL or an explicit read-only production URL:

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
psql "$DATABASE_URL" -v ON_ERROR_STOP=1
```

### Object and extension counts

```sql
SELECT version();
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

SELECT table_type, count(*)
FROM information_schema.tables
WHERE table_schema = 'public'
GROUP BY table_type ORDER BY table_type;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;

SELECT table_name
FROM information_schema.views
WHERE table_schema = 'public'
ORDER BY table_name;
```

### Exact row counts of all public tables

The `\gexec` below is a `psql` metacommand and outputs a separate exact `count(*)` for each table:

```sql
SELECT format(
  'SELECT %L AS table_name, count(*) AS rows FROM %I.%I;',
  tablename, schemaname, tablename
)
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename
\gexec
```

### Columns, constraints and drift

```sql
SELECT table_name, ordinal_position, column_name, data_type,
       udt_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

SELECT tc.table_name, kcu.column_name,
       ccu.table_name AS references_table,
       ccu.column_name AS references_column,
       rc.delete_rule
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name=kcu.constraint_name
 AND tc.constraint_schema=kcu.constraint_schema
JOIN information_schema.referential_constraints rc
  ON rc.constraint_name=tc.constraint_name
 AND rc.constraint_schema=tc.constraint_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name=rc.unique_constraint_name
 AND ccu.constraint_schema=rc.unique_constraint_schema
WHERE tc.constraint_type='FOREIGN KEY'
  AND tc.table_schema='public'
ORDER BY tc.table_name, kcu.ordinal_position;
```

## Public tables, numbers, RLS and publication

The numbers below are exact from the local database at 20 July 2026. They are observational evidence, not a seed contract. `off` means `relrowsecurity=false`; therefore there are no effective table policies. `message` is the only MAPIT table in the Realtime publication.

| Domain | Table | Target | Rows | RLS | Real-time |
|---|---|---|---:|---|---|
| Calls/documents | `call_document_mappings` | Links a call identifier to a shared document | 67 | off | no |
| Calls/documents | `call_metadata` | Call rules and call-specific metadata | 6 | off | no |
| Citations | `citations` | Registered source references | 12 | from | no |
| Identity | `client` | Application profile; `auth_id` is logically linked to Supabase Auth | 2 | from | no |
| Collaboration | `client_collaboration` | Many-to-many membership and role | 1 | off | no |
| Collaboration | `collaboration` | Shared workspace | 1 | off | no |
| Proposal V4 | `compliance_checks` | Compliance outcomes per proposal | 0 | off | no |
| Conversation | `conversation` | Frontend Conversation Container | 7 | off | no |
| Analytics | `conversation_analytics` | Question, answer, tools, timing and status | 4.885 | off | no |
| Memory | `conversation_facts` | Facts extracted from conversations | 112 | out | no |
| Memory | `conversation_memory` | Long-term memory per call/user | 43 | off | no |
| RAG | `document_chunks` | Text chunks, full text column and vector | 38.697 | **on** | no |
| RAG | `embedding_cache` | Hash-to-vector cache | 0 | off | no |
| Projects | `entity_cards` | Cached organization/entity cards | 1.696 | off | no |
| Calls | `funding_calls` | Multi-program funding calls and vectors | 2.758 | off | no |
| RAG | `horizon_documents` | Source document register | 144 | **on** | no |
| Proposal V4 | `improvement_suggestions` | Improvement suggestions for proposal/section | 0 | off | no |
| Conversation | `message` | Frontend Chat Messages | 16 | off | **ja** |
| Projects | `organizations` | CORDIS participation rules; the same organization can repeat | 89.348 | off | no |
| Projects | `project_embeddings` | Project vectors and embedding status | 13.850 | off | no |
| Projects | `projects` | CORDIS project metadata | 13.865 | off | no |
| Proposal V4 | `proposal_activity_log` | Proposal activities | 0 | out | no |
| Proposal V4 | `proposal_budgets` | Budget rules per proposal/partner | 0 | off | no |
| Proposal V4 | `proposal_consortium` | Concept consortium members | 0 | out | no |
| Proposal V4 | `proposal_examples` | Reusable sample sections | 0 | off | no |
| Proposal V4 | `proposal_sections` | Versions and quality of proposal texts | 32 | off | no |
| Proposal V4 | `proposal_sessions` | Active V4 sessions | 4 | off | no |
| Proposal V4 | `proposals` | Proposal metadata | 2 | off | no |
| Feedback | `response_feedback` | Rating and free feedback on answers | 2 | off | no |
| Schema | `schema_migrations` | Manual application versions; no full ledger | 2 | off | no |
| Proposal V4 | `section_criteria_mapping` | Evaluation criteria per section | 0 | off | no |
| Shared RAG | `shared_document_chunks` | Chunks of shared/call documents | 13.147 | off | no |
| Shared RAG | `shared_documents` | Shared program documents | 54 | off | no |
| Analytics | `tool_combination_analytics` | Tool combinations and success rate | 1 | off | no |
| Analytics | `tool_usage_analytics` | Tool calls, timing and result status | 5.372 | off | no |

### RLS Policies

There are exactly four MAPIT policies:

| Table | Policy | Operation | Predicate |
|---|---|---|---|
| `horizon_documents` | `Public documents are viewable by everyone` | `SELECT` | `status = 'active'` |
| `horizon_documents` | `Service role can manage all documents` | `ALL` | `auth.role() = 'service_role'` |
| `document_chunks` | `Public chunks are viewable by everyone` | `SELECT` | The parent document exists and has `status='active'` |
| `document_chunks` | `Service role can manage all chunks` | `ALL` | `auth.role() = 'service_role'` |

This is minimal coverage. In particular, `client`, collaboration, conversation, message, and proposal tables do not have database-enforced tenant isolation. Views are not included in the table above; their access semantics and grants must be tested separately before being exposed via PostgREST.

### Publications

The catalog contains two publications:

- `supabase_realtime` publishes `INSERT`, `UPDATE`, `DELETE`, and `TRUNCATE` for `public.message` only.
- `supabase_realtime_messages_publication` publishes the same operations for the internal `realtime.messages`.

Control query:

```sql
SELECT p.pubname, n.nspname AS schema_name, c.relname AS table_name
FROM pg_publication p
LEFT JOIN pg_publication_rel pr ON pr.prpubid=p.oid
LEFT JOIN pg_class c ON c.oid=pr.prrelid
LEFT JOIN pg_namespace n ON n.oid=c.relnamespace
ORDER BY p.pubname, schema_name, table_name;
```

## Views

| View | Definition/purpose |
|---|---|
| `active_funding_calls` | `funding_calls` with status `open` or `upcoming`, on deadline |
| `call_document_chunks_view` | Join of call document mapping, shared document and chunks |
| `horizon_europe_calls` | `funding_calls` with `programme='horizon_europe'` |
| `proposal_overview` | Section, partner, country, budget and issue aggregations per proposal |
| `section_quality_summary` | Criteria, scores and open suggestions per current section |
| `session_activity_summary` | Active/completed sessions per day in the last 30 days |
| `v_conversation_analytics_24h` | Usage, confidence, latency and errors over 24 hours |
| `v_embedding_coverage` | Projects with/without project embedding |
| `v_embedding_stats` | Numbers and timestamps per model/status |
| `v_feedback_metrics_7d` | Seven-day rating and feedback aggregates |
| `v_popular_tool_combos` | Top combinations with more than five occurrences |
| `v_question_patterns` | Heuristic question categories about 30 days |
| `v_tool_feedback` | Links feedback to used tools |
| `v_tool_performance_24h` | Tool latency and errors over 24 hours |
| `v_tool_usage_analytics` | Total tool usage and success aggregates |

## Functions, RPCs and Triggers

The full snapshot contains seventeen MAPIT functions in `public`. Ten are directly callable query/business functions; seven are trigger functions.

| Function | Main input | Result/goal |
|---|---|---|
| `calculate_completion_percentage` | `p_proposal_id integer` | Proposal completion percentage |
| `cleanup_expired_sessions` | `expiry_hours integer default 24` | Marks old active proposal sessions as `expired` and returns quantity |
| `get_chunks_for_call` | call identifier, optional text, limit | Shared chunks with relevance score |
| `get_current_sections` | proposal ID | Current sections and quality |
| `get_document_stats` | none | Document/chunk statistics |
| `hybrid_search` | vector, query text, count, vector weight | Vector plus full text score on `document_chunks` |
| `keyword_search` | text, limit, document type, year | Full-text document search results |
| `search_calls_semantic` | vector and filters | Semantic funding call results |
| `search_documents` | vector and filters | Semantic document results |
| `search_funding_calls` | text and program/status/type/cluster/year filters | Full-text call results |

Trigger functions: `calculate_requested_funding`, `calculate_word_count`, `update_funding_calls_timestamp`, `update_project_embeddings_timestamp`, `update_proposal_completion`, `update_proposal_timestamp` and `update_session_activity`.

The corresponding triggers work on `funding_calls`, `project_embeddings`, `proposal_budgets`, `proposal_sections`, `proposal_sessions` and `proposals`. Verify signatures from the catalog instead of guessing client types:

```sql
SELECT p.proname,
       pg_get_function_identity_arguments(p.oid) AS arguments,
       pg_get_function_result(p.oid) AS result
FROM pg_proc p
JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public'
ORDER BY p.proname;
```

Note that the SQL functions declare `query_embedding vector` without a dimension type mod. The column dimension used still determines whether distance operations are valid; a 768 vector against a 3072 column fails.

## Embedding transition 768 → 3072

### Observed matrix

| Storage | `migration/schema.sql` | Local DB 20-07-2026 | Code/default | Model/provenance |
|---|---:|---:|---:|---|
| `project_embeddings.title_embedding` | 3072 | 3072 | 3072 | `gemini-embedding-001` |
| `project_embeddings.objective_embedding` | 3072 | 3072 | 3072 | `gemini-embedding-001` |
| `project_embeddings.combined_embedding` | 3072 | 3072 | 3072 | `gemini-embedding-001` |
| `document_chunks.embedding` | **768** | **3072** | 3072 | Local rows still carry `embedding_model='text-embedding-004'`; metadata is therefore inconsistent |
| `funding_calls.embedding` | **768** | **3072** | 3072 | Re-embedding required after column replacement |
| `embedding_cache.embedding` | **768** | **3072** | 3072 | Migration clears cache; local 0 rows |

Active configuration is in `app/core/config.py` and `app/services/embedding_service.py`: `models/gemini-embedding-001` with `output_dimensionality=3072`. `migration/002_upgrade_embeddings_to_3072.sql` drops and recreates the three 768 columns and truncates `embedding_cache`. As a result, existing vectors are lost.

The local database does not have a ANN vector index on `document_chunks`, `funding_calls`, or `project_embeddings` after the transition; the old IVFFlat indexes from `migration/schema.sql` are gone. Searches therefore fall back to exact/sequential distance calculation. `migration/001_init_schema.sql` additionally attempts to create a HNSW index on a `vector(3072)`; standard pgvector indexing with type `vector` supports a maximum of 2.000 dimensions and that bootstrap has therefore not been demonstrated as a working route.

Always check schedule and dates:

```sql
SELECT c.table_name, c.column_name,
       format_type(a.atttypid,a.atttypmod) AS formatted_type
FROM information_schema.columns c
JOIN pg_class t ON t.relname=c.table_name
JOIN pg_namespace n ON n.oid=t.relnamespace
 AND n.nspname=c.table_schema
JOIN pg_attribute a ON a.attrelid=t.oid
 AND a.attname=c.column_name
WHERE c.table_schema='public'
  AND (c.column_name='embedding' OR c.column_name LIKE '%_embedding')
ORDER BY c.table_name, c.ordinal_position;

SELECT 'projects' AS corpus, count(*) AS rows,
       count(combined_embedding) AS embedded
FROM project_embeddings
UNION ALL
SELECT 'chunks', count(*), count(embedding) FROM document_chunks
UNION ALL
SELECT 'calls', count(*), count(embedding) FROM funding_calls;

SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname='public'
  AND tablename IN ('project_embeddings','document_chunks','funding_calls')
ORDER BY tablename,indexname;
```

## Migration ledger and sequence

### Important: There is no valid linear chain yet

The numbers suggest an order that does not exist. `schema.sql` is a complete snapshot that already contains frontend, proposal, analytics and feedback objects. `001_init_schema.sql` is a smaller alternative scheme with conflicting types. `008` and `009` are separate additive scripts, while the frontend has its own Drizzle migrations in parallel. Therefore, do not run these files ** all in succession**.

| Logical position | File | Git status at 20-07-2026 | Relationship and risk | After complete `schema.sql` run? |
|---:|---|---|---|---|
| 0 | `webapp-ui/supabase_cli` / `supabase start` | tracked config | Creates Supabase platform schemas and services | prerequisite, no MAPIT migration |
| 1A | `migration/schema.sql` | tracked | Full pg_dump snapshot: 35 public tables/15 views plus Supabase internals; document/call/cache vectors still 768 | baseline alternative |
| 1A' | `webapp-ui/supabase_cli/schema.sql` | tracked | Semantic duplicate of 1A; only whitespace differs | **no**, choose one snapshot |
| 1B | `migration/001_init_schema.sql` | tracked | Small alternative with nine tables; missing app domains; uses, among other things, `projects.id varchar`, other than local DB/Drizzle | **no** |
| 1C | `webapp-ui/src/lib/server/db/migrations/0000…0004` | tracked | Parallel frontend path for client/collaboration/conversation/message plus projects/orgs; `0002` contains manual PK warning | **no**, objects are already in snapshot |
| 2 | `migration/008_tool_analytics.sql` | tracked | Creates three analytics tables; already present in snapshot | no |
| 3 | `migration/009_user_feedback.sql` | tracked | Creates `response_feedback` and `feedback_insights`; snapshot contains only first | no; would bring back a later deleted table |
| 4 | `migration/cleanup_unused_tables.sql` | tracked, destructive | Drops sixteen tables, including `feedback_insights`; snapshot largely reflects this cleanup | no |
| 5 | `migration/002_upgrade_embeddings_to_3072.sql` | **not tracked** | Should make sense after the 768 snapshot; drops vectors, clears cache and requires re-embedding | only after review, backup and commit |

So the closest reconstruction of the local state is: a tested full snapshot as a baseline, then the 3072 migration, then full re-embedding. This is a description of the observed state, not yet a supported production command.

The tables `public.schema_migrations` and `drizzle.__drizzle_migrations` do not prove a complete chain. Locally, `public.schema_migrations` contained only `v2.0.1_citations_table` and `022_cleanup_unused_tables`; Drizzle contained one hash. The other current objects cannot be traced back there as applied steps.

### Required remediation

1. Choose one owner and one schema authority.
2. Create a real `supabase/migrations/<timestamp>_*.sql` chain from an empty instance.
3. Include 3072-DDL, RPC signatures, RLS, publications and grants in that chain.
4. Record checksum, applied-at, rollback/forward-fix and data migration per migration.
5. Let CI migrate an empty database and compare the object counts and dimensions.

## Textual ERD

The arrows below are physical foreign keys in the local catalog, unless explicitly marked as “logical”.

```text
Supabase Auth / users
  auth.users.id - - - client.auth_id                  (logical; no FK)
  client.id - - - conversation.user_id                (logical; no current FK)
  client.id <----- client_collaboration.client_id
  collaboration.id <----- client_collaboration.collaboration_id
  collaboration.id <----- conversation.collaboration_id
  conversation.id <----- message.conversation_id
  client.id - - - message.user_id                     (logical; no current FK)

CORDIS / embeddings
  projects.id <----- project_embeddings.project_id    (ON DELETE CASCADE)
  projects.id - - - organizations."projectID"          (logical; no current FK)

Document-RAG
  horizon_documents.id <----- document_chunks.document_id
  shared_documents.id <----- shared_document_chunks.document_id
  shared_documents.id <----- call_document_mappings.document_id
  funding_calls.call_identifier - - - call_document_mappings.call_identifier
                                                    (logical string link)

Proposal V4
  proposals.id <----- proposal_sessions.proposal_id
  proposals.id <----- proposal_sections.proposal_id
  proposal_sections.id <----- proposal_sections.parent_version_id
  proposals.id <----- proposal_activity_log.proposal_id
  proposals.id <----- proposal_consortium.proposal_id
  proposals.id <----- proposal_budgets.proposal_id
  proposal_consortium.id <----- proposal_budgets.consortium_id
  proposals.id <----- compliance_checks.proposal_id
  proposals.id <----- improvement_suggestions.proposal_id
  proposal_sections.id <----- improvement_suggestions.section_id
  proposal_sections.id <----- section_criteria_mapping.section_id

Analytics / memory
  conversation_analytics.conversation_id - - - conversation.id
  response_feedback.conversation_id - - - conversation.id
  conversation_facts/conversation_memory - - - conversation/user
                                                    (logical IDs, no FK)
```

Important consequence: multiple ownership and tenant relationships only exist as a convention in application code. The database does not prevent orphan rows for organization→project, client→conversation and user→message, among others.

## Neo4j graph scheme

### Current CORDIS core

The running local graph contained on 20 July 2026:

| Label | Nodes |
|---|---:|
| `Project` | 13.865 |
| `Organization` | 25.096 |
| `Topic` | 1.785 |
| `Country` | 166 |
| `Programme` | 9 |
| `Cluster` | 6 |
| `EntityType` | 5 |

| Relationship type | Relationships |
|---|---:|
| `PARTICIPATES_IN` | 89.263 |
| `PARTNERS_WITH` | 74.262 |
| `FUNDED_UNDER` | 13.865 |
| `TARGETS` | 12.823 |
| `LOCATED_IN` | 25.089 |
| `IS_TYPE` | 25.009 |

Core model:

```text
(Organization)-[:PARTICIPATES_IN {role, ecContribution}]->(Project)
(Organization)-[:LOCATED_IN]->(Country)
(Organization)-[:IS_TYPE]->(EntityType)
(Organization)-[:PARTNERS_WITH {projectCount, totalValue, updatedAt}]-(Organization)
(Project)-[:FUNDED_UNDER]->(Topic)
(Project)-[:TARGETS]->(Cluster|Programme)
```

This corrects the old documentation claim `(Project)-[:BELONGS_TO]->(Topic)`: the current CORDIS ingest script uses `FUNDED_UNDER`.

### Programmatic reference graphs

The scripts also add labels for `ErasmusAction`, `ErasmusSector`, `PartnerRegion`, `CreativeEuropeAction`, `CreativeEuropeStrand`, `CreativeEuropeRegion`, `DigitalEuropeAction`, `DigitalEuropeObjective`, `DigitalEuropeRegion`, `EU4HealthAction`, `EU4HealthStrand`, `EU4HealthRegion`, `LIFEProjectType`, `LIFESubprogramme` and `LIFERegion`. Relationships include `PART_OF`, `BELONGS_TO_STRAND`, `BELONGS_TO_OBJECTIVE`, `AVAILABLE_IN`, `REQUIRES_COORDINATOR_FROM`, `ALLOWS_PARTNERS_FROM`, `ALLOWS_PARTICIPATION_FROM`, `ALLOWS_COUNTRIES`, and `MEMBER_OF`.

These nodes were missing from the local graph snapshot; the scripts were therefore not demonstrably applied there. Their content comes from hardcoded Python constants and has no database provenance or validity date.

Reproducible counts:

```cypher
MATCH (n)
UNWIND labels(n) AS label
RETURN label, count(*) AS nodes
ORDER BY label;

MATCH ()-[r]->()
RETURN type(r) AS relationship, count(*) AS relationships
ORDER BY relationship;
```

## Snapshot acceptance

A database is only compatible with the current application when at least the following is true:

- 35 expected public tables and 15 views are present, or an explicitly newer migration version explains the difference.
- All active embedding columns are 3072 dimensional and query vectors are created with the same model/dimension.
- Row counts, embedding coverage and source manifest are recorded; historical numbers are not blindly enforced.
- RLS and publication status have been deliberately assessed. The current minimum RLS is a known security risk, not a desired standard.
- The physical foreign keys from the ERD consist and logical relationships have application or contract tests.
- PostgreSQL and Neo4j data versions belong together; project and participation counts have been explained.
- EA restore on an empty staging instance and a rollback/forward fix have actually been tested.
