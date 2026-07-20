# Databaseschema en data-architectuur

**Status:** geverifieerde documentatiesnapshot

**Snapshotdatum:** 20 juli 2026

**Bronnen:** `migration/schema.sql`, `migration/*.sql`, `webapp-ui/supabase_cli/schema.sql`, de frontend-Drizzle-migraties en read-only catalogusqueries tegen de draaiende lokale Supabase- en Neo4j-instances

MAPIT gebruikt PostgreSQL/Supabase voor relationele data, pgvector voor embeddings en Neo4j voor relatie-intensieve analyses. Dit document onderscheidt bewust drie werkelijkheden: de Git-schemafiles, de lokale database op de snapshotdatum en de actieve applicatiecode. Die zijn nog niet volledig gelijk.

Zie [DATA_INGESTION.md](guides/DATA_INGESTION.md) voor herstel en data-bootstrap en [SECURITY_REGISTER.md](../../SECURITY_REGISTER.md) voor de beveiligingsimpact van de beperkte RLS-dekking.

## Samenvatting en authority

| Onderdeel | Actuele status |
|---|---|
| PostgreSQL | Lokale Supabase draaide PostgreSQL 15.8 met pgvector 0.8.0. |
| `public` | 35 basistabellen, 15 views en 17 MAPIT-functies in de lokale snapshot. |
| Schema-snapshot | `MAP-IT_SA/migration/schema.sql` is de meest volledige getrackte MAPIT-snapshot. `webapp-ui/supabase_cli/schema.sql` is inhoudelijk dezelfde pg_dump; de waargenomen diff bestaat alleen uit whitespace. |
| Migratie-authority | **Niet vastgesteld.** De repository bevat parallelle snapshots, backend-SQL en frontend-Drizzle-migraties, maar geen betrouwbare end-to-end migration ledger. |
| RLS | Alleen `document_chunks` en `horizon_documents` hebben RLS aan; 33 andere `public`-tabellen niet. |
| Realtime | Alleen `public.message` staat in `supabase_realtime`. |
| Embeddings | Actieve code en lokale DB gebruiken 3072 dimensies; de getrackte volledige schema-snapshot gebruikt nog 768 voor documenten, calls en cache. |

`migration/schema.sql` is daarom de **documentatiebaseline**, niet een bewezen incrementele migratie. Gebruik het niet alsof het migration 000 is zonder een restoretest op een lege Supabase-instance: het bevat ook Supabase-beheerschema's, owners, grants en platformobjecten.

## Reproduceerbare catalogusqueries

Voer vanuit `MAP-IT_SA/` uit met de lokale standaard-URL of een expliciete read-only productie-URL:

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
psql "$DATABASE_URL" -v ON_ERROR_STOP=1
```

### Object- en extensiecounts

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

### Exacte row counts van alle public-tabellen

Onderstaande `\gexec` is een `psql`-metacommand en voert voor elke tabel een afzonderlijke exacte `count(*)` uit:

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

### Kolommen, constraints en drift

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

## Public-tabellen, aantallen, RLS en publication

De aantallen hieronder zijn exact uit de lokale database op 20 juli 2026. Ze zijn observatiebewijs, geen seedcontract. `uit` betekent dat `relrowsecurity=false`; daardoor zijn er ook geen effectieve tabelpolicies. `message` is de enige MAPIT-tabel in de Realtime-publication.

| Domein | Tabel | Doel | Rows | RLS | Realtime |
|---|---|---|---:|---|---|
| Calls/documenten | `call_document_mappings` | Koppelt een call-identifier aan een gedeeld document | 67 | uit | nee |
| Calls/documenten | `call_metadata` | Callregels en call-specifieke metadata | 6 | uit | nee |
| Citations | `citations` | Geregistreerde bronverwijzingen | 12 | uit | nee |
| Identiteit | `client` | Applicatieprofiel; `auth_id` is logisch gekoppeld aan Supabase Auth | 2 | uit | nee |
| Collaboration | `client_collaboration` | Many-to-many-lidmaatschap en rol | 1 | uit | nee |
| Collaboration | `collaboration` | Gedeelde workspace | 1 | uit | nee |
| Proposal V4 | `compliance_checks` | Compliance-uitkomsten per voorstel | 0 | uit | nee |
| Conversation | `conversation` | Frontend-conversatiecontainer | 7 | uit | nee |
| Analytics | `conversation_analytics` | Vraag, antwoord, tools, timing en status | 4.885 | uit | nee |
| Memory | `conversation_facts` | Uit gesprekken geëxtraheerde feiten | 112 | uit | nee |
| Memory | `conversation_memory` | Langetermijngeheugen per gesprek/gebruiker | 43 | uit | nee |
| RAG | `document_chunks` | Tekstchunks, full-textkolom en vector | 38.697 | **aan** | nee |
| RAG | `embedding_cache` | Hash-naar-vector-cache | 0 | uit | nee |
| Projects | `entity_cards` | Gecachete organisatie-/entiteitskaarten | 1.696 | uit | nee |
| Calls | `funding_calls` | Multi-programme funding calls en vectors | 2.758 | uit | nee |
| RAG | `horizon_documents` | Brondocumentregister | 144 | **aan** | nee |
| Proposal V4 | `improvement_suggestions` | Verbetersuggesties voor voorstel/sectie | 0 | uit | nee |
| Conversation | `message` | Frontend-chatberichten | 16 | uit | **ja** |
| Projects | `organizations` | CORDIS-participatieregels; dezelfde organisatie kan herhalen | 89.348 | uit | nee |
| Projects | `project_embeddings` | Projectvectors en embeddingstatus | 13.850 | uit | nee |
| Projects | `projects` | CORDIS-projectmetadata | 13.865 | uit | nee |
| Proposal V4 | `proposal_activity_log` | Voorstelactiviteiten | 0 | uit | nee |
| Proposal V4 | `proposal_budgets` | Budgetregels per voorstel/partner | 0 | uit | nee |
| Proposal V4 | `proposal_consortium` | Conceptconsortiumleden | 0 | uit | nee |
| Proposal V4 | `proposal_examples` | Herbruikbare voorbeeldsecties | 0 | uit | nee |
| Proposal V4 | `proposal_sections` | Versies en kwaliteit van voorstelteksten | 32 | uit | nee |
| Proposal V4 | `proposal_sessions` | Actieve V4-sessies | 4 | uit | nee |
| Proposal V4 | `proposals` | Voorstelmetadata | 2 | uit | nee |
| Feedback | `response_feedback` | Rating en vrije feedback op antwoorden | 2 | uit | nee |
| Schema | `schema_migrations` | Handmatige applicatieversies; geen volledige ledger | 2 | uit | nee |
| Proposal V4 | `section_criteria_mapping` | Evaluatiecriteria per sectie | 0 | uit | nee |
| Shared RAG | `shared_document_chunks` | Chunks van gedeelde/call-documenten | 13.147 | uit | nee |
| Shared RAG | `shared_documents` | Gedeelde programmadocumenten | 54 | uit | nee |
| Analytics | `tool_combination_analytics` | Toolcombinaties en succesratio | 1 | uit | nee |
| Analytics | `tool_usage_analytics` | Toolcalls, timing en resultaatstatus | 5.372 | uit | nee |

### RLS-policies

Er bestaan precies vier MAPIT-policies:

| Tabel | Policy | Operatie | Predicate |
|---|---|---|---|
| `horizon_documents` | `Public documents are viewable by everyone` | `SELECT` | `status = 'active'` |
| `horizon_documents` | `Service role can manage all documents` | `ALL` | `auth.role() = 'service_role'` |
| `document_chunks` | `Public chunks are viewable by everyone` | `SELECT` | Het parentdocument bestaat en heeft `status='active'` |
| `document_chunks` | `Service role can manage all chunks` | `ALL` | `auth.role() = 'service_role'` |

Dit is minimale dekking. Vooral `client`, collaboration-, conversation-, message- en proposal-tabellen hebben geen database-afgedwongen tenantisolatie. Views zijn niet in bovenstaande tabel opgenomen; hun toegangssemantiek en grants moeten apart worden getest voordat zij via PostgREST worden blootgesteld.

### Publications

De catalogus bevat twee publications:

- `supabase_realtime` publiceert `INSERT`, `UPDATE`, `DELETE` en `TRUNCATE` voor alleen `public.message`.
- `supabase_realtime_messages_publication` publiceert dezelfde operaties voor het interne `realtime.messages`.

Controlequery:

```sql
SELECT p.pubname, n.nspname AS schema_name, c.relname AS table_name
FROM pg_publication p
LEFT JOIN pg_publication_rel pr ON pr.prpubid=p.oid
LEFT JOIN pg_class c ON c.oid=pr.prrelid
LEFT JOIN pg_namespace n ON n.oid=c.relnamespace
ORDER BY p.pubname, schema_name, table_name;
```

## Views

| View | Definitie/doel |
|---|---|
| `active_funding_calls` | `funding_calls` met status `open` of `upcoming`, op deadline |
| `call_document_chunks_view` | Join van call-documentmapping, gedeeld document en chunks |
| `horizon_europe_calls` | `funding_calls` met `programme='horizon_europe'` |
| `proposal_overview` | Sectie-, partner-, landen-, budget- en issue-aggregaties per proposal |
| `section_quality_summary` | Criteria, scores en open suggesties per actuele sectie |
| `session_activity_summary` | Actieve/completed sessions per dag in de laatste 30 dagen |
| `v_conversation_analytics_24h` | Gebruik, confidence, latency en fouten over 24 uur |
| `v_embedding_coverage` | Projecten met/zonder projectembedding |
| `v_embedding_stats` | Aantallen en timestamps per model/status |
| `v_feedback_metrics_7d` | Rating- en feedbackaggregaten over zeven dagen |
| `v_popular_tool_combos` | Topcombinaties met meer dan vijf voorkomens |
| `v_question_patterns` | Heuristische vraagcategorieën over 30 dagen |
| `v_tool_feedback` | Koppelt feedback aan gebruikte tools |
| `v_tool_performance_24h` | Toollatency en fouten over 24 uur |
| `v_tool_usage_analytics` | Totale toolgebruik- en succesaggregaten |

## Functies, RPC's en triggers

De volledige snapshot bevat zeventien MAPIT-functies in `public`. Tien zijn rechtstreeks aanroepbare query-/businessfuncties; zeven zijn triggerfuncties.

| Functie | Belangrijkste input | Resultaat/doel |
|---|---|---|
| `calculate_completion_percentage` | `p_proposal_id integer` | Percentage proposal completion |
| `cleanup_expired_sessions` | `expiry_hours integer default 24` | Markeert oude actieve proposalsessions als `expired` en retourneert aantal |
| `get_chunks_for_call` | call-identifier, optionele tekst, limiet | Gedeelde chunks met relevance score |
| `get_current_sections` | proposal-ID | Actuele secties en kwaliteit |
| `get_document_stats` | geen | Document/chunk-statistieken |
| `hybrid_search` | vector, querytekst, count, vectorgewicht | Vector- plus full-textscore op `document_chunks` |
| `keyword_search` | tekst, limiet, documenttype, jaar | Full-textdocumentzoekresultaten |
| `search_calls_semantic` | vector en filters | Semantische funding-callresultaten |
| `search_documents` | vector en filters | Semantische documentresultaten |
| `search_funding_calls` | tekst en programma/status/type/cluster/jaarfilters | Full-text callresultaten |

Triggerfuncties: `calculate_requested_funding`, `calculate_word_count`, `update_funding_calls_timestamp`, `update_project_embeddings_timestamp`, `update_proposal_completion`, `update_proposal_timestamp` en `update_session_activity`.

De bijbehorende triggers werken op `funding_calls`, `project_embeddings`, `proposal_budgets`, `proposal_sections`, `proposal_sessions` en `proposals`. Verifieer signatures uit de catalogus in plaats van clienttypes te raden:

```sql
SELECT p.proname,
       pg_get_function_identity_arguments(p.oid) AS arguments,
       pg_get_function_result(p.oid) AS result
FROM pg_proc p
JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public'
ORDER BY p.proname;
```

Let op: de SQL-functies declareren `query_embedding vector` zonder dimensietypmod. De gebruikte kolomdimensie bepaalt alsnog of afstandsoperaties geldig zijn; een 768-vector tegen een 3072-kolom faalt.

## Embeddingtransitie 768 → 3072

### Geobserveerde matrix

| Opslag | `migration/schema.sql` | Lokale DB 20-07-2026 | Code/default | Model/provenance |
|---|---:|---:|---:|---|
| `project_embeddings.title_embedding` | 3072 | 3072 | 3072 | `gemini-embedding-001` |
| `project_embeddings.objective_embedding` | 3072 | 3072 | 3072 | `gemini-embedding-001` |
| `project_embeddings.combined_embedding` | 3072 | 3072 | 3072 | `gemini-embedding-001` |
| `document_chunks.embedding` | **768** | **3072** | 3072 | Lokale rijen dragen nog `embedding_model='text-embedding-004'`; metadata is dus inconsistent |
| `funding_calls.embedding` | **768** | **3072** | 3072 | Re-embedding vereist na kolomvervanging |
| `embedding_cache.embedding` | **768** | **3072** | 3072 | Migratie leegt cache; lokaal 0 rijen |

Actieve configuratie staat in `app/core/config.py` en `app/services/embedding_service.py`: `models/gemini-embedding-001` met `output_dimensionality=3072`. `migration/002_upgrade_embeddings_to_3072.sql` dropt en herschept de drie 768-kolommen en truncateert `embedding_cache`. Daardoor gaan bestaande vectors verloren.

De lokale database heeft na de transitie geen ANN-vectorindex op `document_chunks`, `funding_calls` of `project_embeddings`; de oude IVFFlat-indexen uit `migration/schema.sql` zijn verdwenen. Zoekopdrachten vallen daarmee terug op exacte/sequentiële afstandsberekening. `migration/001_init_schema.sql` probeert bovendien een HNSW-index op een `vector(3072)` te maken; standaard pgvector-indexering met type `vector` ondersteunt maximaal 2.000 dimensies en die bootstrap is daarom niet als werkende route aangetoond.

Controleer altijd schema én data:

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

## Migratieledger en volgorde

### Belangrijk: er is nog geen geldige lineaire keten

De nummers suggereren een volgorde die niet bestaat. `schema.sql` is een volledige snapshot waarin frontend-, proposal-, analytics- en feedbackobjecten al zitten. `001_init_schema.sql` is een kleiner alternatief schema met conflicterende types. `008` en `009` zijn losse additieve scripts, terwijl de frontend parallel eigen Drizzle-migraties heeft. Voer deze bestanden daarom **niet allemaal achter elkaar** uit.

| Logische positie | Bestand | Git-status op 20-07-2026 | Relatie en risico | Na volledige `schema.sql` uitvoeren? |
|---:|---|---|---|---|
| 0 | `webapp-ui/supabase_cli` / `supabase start` | tracked config | Maakt Supabase-platformschema's en services | prerequisite, geen MAPIT-migratie |
| 1A | `migration/schema.sql` | tracked | Volledige pg_dump-snapshot: 35 public-tabellen/15 views plus Supabase-internals; document/call/cachevectors nog 768 | baseline-alternatief |
| 1A' | `webapp-ui/supabase_cli/schema.sql` | tracked | Semantisch duplicaat van 1A; alleen whitespace verschilt | **nee**, kies één snapshot |
| 1B | `migration/001_init_schema.sql` | tracked | Klein alternatief met negen tabellen; mist appdomeinen; gebruikt o.a. `projects.id varchar`, anders dan lokale DB/Drizzle | **nee** |
| 1C | `webapp-ui/src/lib/server/db/migrations/0000…0004` | tracked | Parallel frontendpad voor client/collaboration/conversation/message plus projects/orgs; `0002` bevat handmatige PK-waarschuwing | **nee**, objecten zitten al in snapshot |
| 2 | `migration/008_tool_analytics.sql` | tracked | Maakt drie analyticstabellen; al aanwezig in snapshot | nee |
| 3 | `migration/009_user_feedback.sql` | tracked | Maakt `response_feedback` én `feedback_insights`; snapshot bevat alleen eerste | nee; zou een later verwijderde tabel terugbrengen |
| 4 | `migration/cleanup_unused_tables.sql` | tracked, destructief | Dropt zestien tabellen, waaronder `feedback_insights`; snapshot weerspiegelt deze cleanup grotendeels | nee |
| 5 | `migration/002_upgrade_embeddings_to_3072.sql` | **niet tracked** | Moet logisch na de 768-snapshot; dropt vectors, leegt cache en vereist re-embedding | alleen na review, backup en commit |

De dichtstbijzijnde reconstructie van de lokale staat is dus: een geteste volledige snapshot als baseline, daarna de 3072-migratie, daarna volledige re-embedding. Dit is een beschrijving van de geobserveerde staat, nog geen ondersteund productiecommando.

De tabellen `public.schema_migrations` en `drizzle.__drizzle_migrations` bewijzen geen volledige keten. Lokaal bevatte `public.schema_migrations` alleen `v2.0.1_citations_table` en `022_cleanup_unused_tables`; Drizzle bevatte één hash. De overige huidige objecten zijn daar niet herleidbaar als toegepaste stappen.

### Vereiste remediatie

1. Kies één owner en één schema-authority.
2. Maak een echte `supabase/migrations/<timestamp>_*.sql`-keten vanaf een lege instance.
3. Neem 3072-DDL, RPC-signatures, RLS, publications en grants in die keten op.
4. Leg per migratie checksum, applied-at, rollback/forward-fix en datamigratie vast.
5. Laat CI een lege database migreren en de objectcounts en dimensies vergelijken.

## Tekstuele ERD

Onderstaande pijlen zijn fysieke foreign keys in de lokale catalogus, tenzij expliciet als “logisch” gemarkeerd.

```text
Supabase Auth / gebruikers
  auth.users.id - - - client.auth_id                  (logisch; geen FK)
  client.id - - - conversation.user_id                (logisch; geen actuele FK)
  client.id <----- client_collaboration.client_id
  collaboration.id <----- client_collaboration.collaboration_id
  collaboration.id <----- conversation.collaboration_id
  conversation.id <----- message.conversation_id
  client.id - - - message.user_id                     (logisch; geen actuele FK)

CORDIS / embeddings
  projects.id <----- project_embeddings.project_id    (ON DELETE CASCADE)
  projects.id - - - organizations."projectID"          (logisch; geen actuele FK)

Document-RAG
  horizon_documents.id <----- document_chunks.document_id
  shared_documents.id <----- shared_document_chunks.document_id
  shared_documents.id <----- call_document_mappings.document_id
  funding_calls.call_identifier - - - call_document_mappings.call_identifier
                                                    (logische stringkoppeling)

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
                                                    (logische IDs, geen FK)
```

Belangrijke consequentie: meerdere ownership- en tenantrelaties bestaan alleen als conventie in applicatiecode. De database voorkomt geen orphan rows voor onder andere organization→project, client→conversation en user→message.

## Neo4j-graafschema

### Actuele CORDIS-kern

De draaiende lokale graaf bevatte op 20 juli 2026:

| Label | Nodes |
|---|---:|
| `Project` | 13.865 |
| `Organization` | 25.096 |
| `Topic` | 1.785 |
| `Country` | 166 |
| `Programme` | 9 |
| `Cluster` | 6 |
| `EntityType` | 5 |

| Relatietype | Relaties |
|---|---:|
| `PARTICIPATES_IN` | 89.263 |
| `PARTNERS_WITH` | 74.262 |
| `FUNDED_UNDER` | 13.865 |
| `TARGETS` | 12.823 |
| `LOCATED_IN` | 25.089 |
| `IS_TYPE` | 25.009 |

Kernmodel:

```text
(Organization)-[:PARTICIPATES_IN {role, ecContribution}]->(Project)
(Organization)-[:LOCATED_IN]->(Country)
(Organization)-[:IS_TYPE]->(EntityType)
(Organization)-[:PARTNERS_WITH {projectCount, totalValue, updatedAt}]-(Organization)
(Project)-[:FUNDED_UNDER]->(Topic)
(Project)-[:TARGETS]->(Cluster|Programme)
```

Dit corrigeert de oude documentatieclaim `(Project)-[:BELONGS_TO]->(Topic)`: het actuele CORDIS-ingestscript gebruikt `FUNDED_UNDER`.

### Programmatische referentiegrafen

De scripts voegen daarnaast labels toe voor `ErasmusAction`, `ErasmusSector`, `PartnerRegion`, `CreativeEuropeAction`, `CreativeEuropeStrand`, `CreativeEuropeRegion`, `DigitalEuropeAction`, `DigitalEuropeObjective`, `DigitalEuropeRegion`, `EU4HealthAction`, `EU4HealthStrand`, `EU4HealthRegion`, `LIFEProjectType`, `LIFESubprogramme` en `LIFERegion`. Relaties omvatten onder andere `PART_OF`, `BELONGS_TO_STRAND`, `BELONGS_TO_OBJECTIVE`, `AVAILABLE_IN`, `REQUIRES_COORDINATOR_FROM`, `ALLOWS_PARTNERS_FROM`, `ALLOWS_PARTICIPATION_FROM`, `ALLOWS_COUNTRIES` en `MEMBER_OF`.

Deze nodes ontbraken in de lokale graafsnapshot; de scripts waren daar dus niet aantoonbaar toegepast. Hun inhoud komt uit hardcoded Python-constanten en heeft geen databaseprovenance of geldigheidsdatum.

Reproduceerbare tellingen:

```cypher
MATCH (n)
UNWIND labels(n) AS label
RETURN label, count(*) AS nodes
ORDER BY label;

MATCH ()-[r]->()
RETURN type(r) AS relationship, count(*) AS relationships
ORDER BY relationship;
```

## Snapshotacceptatie

Een database is pas compatibel met de huidige applicatie wanneer minimaal het volgende waar is:

- 35 verwachte public-tabellen en 15 views zijn aanwezig, of een expliciet nieuwere migratieversie verklaart het verschil.
- Alle actieve embeddingkolommen zijn 3072-dimensionaal en queryvectors worden met hetzelfde model/dimensie gemaakt.
- Row counts, embeddingcoverage en bronmanifest zijn vastgelegd; historische aantallen worden niet blind afgedwongen.
- RLS- en publicationstatus zijn bewust beoordeeld. De huidige minimale RLS is een bekend securityrisico, geen gewenste norm.
- De fysieke foreign keys uit de ERD bestaan en logische relaties hebben applicatie- of contracttests.
- PostgreSQL- en Neo4j-dataversies horen bij elkaar; project- en participatiecounts zijn verklaard.
- Een restore op een lege staging-instance en een rollback/forward-fix zijn daadwerkelijk getest.
