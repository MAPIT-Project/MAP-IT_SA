# MAP-IT migration ledger

**Gecontroleerd op:** 20 juli 2026
**Scope:** de zes SQL-bestanden die nu in `migration/` staan, plus Git-historie voor de ontbrekende nummers 003–007.

## Conclusie

De bestanden in deze map vormen **geen lineaire, reproduceerbare migratieketen**. De nummers geven een historische volgorde aan, maar:

- `schema.sql` is een brede snapshot van een draaiende Supabase/PostgreSQL-database en overlapt de losse migraties;
- `001_init_schema.sql` is een veel kleinere, alternatieve bootstrap met conflicterende tabeltypen;
- `002_upgrade_embeddings_to_3072.sql` is niet Git-tracked en is niet compatibel met `001` zonder aanvullende kolommen;
- 003–007 hebben in Git bestaan, maar zijn uit de huidige tree verwijderd;
- `008` en `009` overlappen objecten die al in `schema.sql` staan;
- `cleanup_unused_tables.sql` is destructief en is niet hetzelfde bestand als de historische `022_cleanup_unused_tables.sql`.

Voer deze bestanden daarom niet blind op nummer achter elkaar uit. Er is op dit moment geen door CI geteste fresh-databaseketen.

## Statusdefinitie en bewijsgrens

In deze ledger betekent:

- **applied:** de exacte bestandsversie/checksum is in een betrouwbare migratietabel of deploymentregistratie vastgelegd;
- **unapplied:** betrouwbare registratie bewijst dat de migratie nog niet is uitgevoerd;
- **unknown:** objecten of effecten kunnen aanwezig zijn, maar zijn niet aan de exacte bestandsversie te koppelen.

Geen van de huidige losse SQL-bestanden voldoet aan de eerste twee bewijsniveaus. Daarom staat hun status hieronder op **unknown**. Aanwezigheid van een tabel in een snapshot bewijst wel databasevorm, maar niet welk script die vorm heeft gemaakt.

Wave 1 legde vast dat de onderzochte lokale `public.schema_migrations` alleen `v2.0.1_citations_table` en `022_cleanup_unused_tables` bevatte en dat de Drizzle-ledger één hash bevatte. De huidige `cleanup_unused_tables.sql` schrijft zelf geen ledgerrecord en wijkt inhoudelijk af van de historische migratie 022; dat lokale record bewijst dus niet dat dit huidige bestand is toegepast.

## Manifest van de huidige bestanden

De datumkolom is een **brondatum**, geen bewezen uitvoerdatum. De vijf tracked bestanden hebben geen datumheader; hun huidige inhoud kwam volledig in Git in commit `6d446b0` van 19 mei 2026. `002` heeft geen Git-provenance of datumheader.

| Nr. | Bestand | Brondatum | SHA-256 | Doel | Status | Harde/logische dependencies |
|---:|---|---|---|---|---|---|
| 001 | `001_init_schema.sql` | 2026-05-19 (huidige Git-versie) | `6c7a7111218c50ea8c3f189474340a522bb9b9bdc5705fbffda98cfbd99dfc28` | Kleine backendbootstrap met negen tabellen voor projecten, organisaties, calls, documenten/chunks, gedeelde documenten/chunks en embeddingcache. | **unknown** | PostgreSQL 14+, `vector`, `uuid-ossp`; bedoeld voor een lege database. Geen afhankelijkheid van `schema.sql`: dit is een alternatief baselinepad. |
| 002 | `002_upgrade_embeddings_to_3072.sql` | onbekend; untracked, geen datumheader | `ffcf6082f0114afe9c7d70cb90167073b03f6e08297bb71cfbbf4b3c87be4ff6` | Dropt en herschept de embeddingkolommen van `funding_calls`, `document_chunks` en `embedding_cache` als `vector(3072)`, leegt de cache en zet Gemini-modeldefaults. | **unknown** | `vector`; de drie tabellen; bovendien `document_chunks.embedding_model` en `embedding_cache.model_version`. Die laatste twee kolommen bestaan in `schema.sql`, maar niet in `001`. Bestaande embeddings moeten daarna opnieuw worden gegenereerd. |
| 008 | `008_tool_analytics.sql` | 2026-05-19 (huidige Git-versie) | `5d3e85bf7c2f72a3ae6bbc16777e096738e43c696c5abc45a043057a46b0e60f` | Maakt `conversation_analytics`, `tool_usage_analytics` en `tool_combination_analytics` plus basisindexen. | **unknown** | PostgreSQL met array- en JSONB-ondersteuning; geen foreign-keydependency. Logisch na een baseline, maar niet na `schema.sql` toepassen omdat de drie tabellen daar al, met deels andere kolomtypen/constraints, in staan. |
| 009 | `009_user_feedback.sql` | 2026-05-19 (huidige Git-versie) | `a9efee230989b9caf2ad925a94c002714500cc71572509b9c268c3820bd101ec` | Maakt `response_feedback` en `feedback_insights` plus basisindexen. | **unknown** | PostgreSQL met arrays en JSONB; geen foreign-keydependency. Logisch na een baseline. Na `schema.sql` zou `response_feedback` al bestaan en `feedback_insights` opnieuw worden geïntroduceerd ondanks de latere cleanup. |
| — | `cleanup_unused_tables.sql` | 2026-05-19 (huidige Git-versie) | `f01f1cf7c4799a80d77cebdaf7056596f8dec4f28c4ac40c3a17b2e1b6e61577` | Dropt zestien als ongebruikt aangemerkte tabellen met `CASCADE`, waaronder `feedback_insights` en oude document-, proposal-, analytics- en cachetabellen. | **unknown** | Geen harde tabeldependency door `DROP TABLE IF EXISTS`; logisch pas na de features die de tabellen maakten. Destructief, zonder rollback en zonder insert in `schema_migrations`. |
| snapshot | `schema.sql` | 2026-05-19 (huidige Git-versie); dumpdatum ontbreekt | `f0fbb64a4b500eff8eb2fa2a6f3c89b2fb95a016c1f25e4c27c481731a10d6c3` | Schema-only snapshot van PostgreSQL 15.8 met Supabase-platformschema's en MAP-IT-objecten: onder meer 35 public-tabellen en 15 public-views, functies, RLS, grants, triggers en indexes. | n.v.t.; dit is een snapshot, geen incrementele migratie | Een compatibele Supabase/PostgreSQL 15-omgeving, extensions en rollen uit de brondatabase. Niet als generieke lege-PostgreSQLbootstrap aangetoond. |

## Relatie tussen `schema.sql` en de losse migraties

`schema.sql` is geen opvolger van `001`. Het is een alternatieve, veel uitgebreidere baseline die uit een draaiende database is gegenereerd. De twee bestanden definiëren dezelfde kernobjecten anders. Voorbeelden:

- `projects.id` is `varchar(50)` in `001` en `integer` in de snapshot;
- `organizations` heeft in `001` een serial `id` en een `varchar` projectreferentie, maar in de snapshot een UUID `id` en integer `projectID`;
- `funding_calls.id` is serial in `001` en UUID in de snapshot;
- document- en shared-documenttabellen verschillen in kolommen, sleutels en typen;
- de snapshot bevat daarnaast frontend-, proposal-, collaboration-, analytics-, feedback- en Supabase-objecten die `001` niet maakt.

De snapshot bevat de drie tabellen uit `008` al, maar niet met exact hetzelfde contract. `CREATE TABLE IF NOT EXISTS` migreert een bestaande tabel niet: het laat de bestaande, afwijkende structuur staan. Hetzelfde geldt voor `response_feedback` uit `009`. `feedback_insights` ontbreekt als tabel in de snapshot, terwijl er nog wel dumpresten met die naam zijn, zoals een sequence/ACL; het huidige cleanupscript dropt juist die tabel.

De snapshot is bovendien niet direct als betrouwbaar uitvoerbaar script bewezen:

- regels 9–12 bevatten vier ongecommentarieerde `pg_dump:`-diagnoseregels en zijn daardoor geen geldige SQL;
- het bestand maakt en wijzigt Supabase-schema's, extensions, owners, ACL's en event triggers en veronderstelt bijbehorende rollen;
- het bevat geen tabeldata;
- het vertegenwoordigt een toestand, niet de stappen waarmee die toestand is bereikt.

`schema.sql` moet daarom eerst als restorebaseline worden geschoond en op een lege, compatibele Supabase-instance worden getest voordat het als authoritative baseline kan gelden.

## Het gat 003–007

De ontbrekende nummers zijn niet alleen hypothetisch. Git-historie bevat de volgende verwijderde bestanden:

| Nummer | Historisch bestand | Eerste Git-record | Huidige toestand |
|---:|---|---|---|
| 003 | `003_call_documents_tables.sql` | 2025-10-08, commit `35a92d2` | verwijderd in `bb90f94` op 2026-05-13 |
| 004 | `004_shared_documents_architecture.sql` | 2025-10-08, commit `35a92d2` | verwijderd in `bb90f94` op 2026-05-13 |
| 005 | `005_call_metadata_table.sql` | 2025-10-08, commit `35a92d2` | verwijderd in `bb90f94` op 2026-05-13 |
| 005 | `005_proposal_writing_system.sql` | 2025-10-11, commit `be18822` | verwijderd in `bb90f94` op 2026-05-13 |
| 006 | `006_citations_table.sql` | 2025-10-16, commit `0f9137f` | verwijderd in `bb90f94` op 2026-05-13 |
| 007 | `007_add_citations_to_message_table.sql` | 2025-10-16, commit `0f9137f` | verwijderd in `bb90f94` op 2026-05-13 |

Er waren dus zelfs twee verschillende migraties met nummer 005. De huidige `schema.sql` bevat objecten uit deze domeinen, zoals shared documents, call metadata, citations, messages en proposalobjecten, maar dat bewijst niet dat elk historisch bestand op de onderzochte database is uitgevoerd. Ook migraties 010–022 hebben historisch bestaan en zijn in dezelfde cleanupcommit uit de werkmap verwijderd. Het terughalen van 003–007 uit Git zou op zichzelf daarom nog geen complete of veilige keten herstellen.

## Vectortransitie 768 naar 3072

De overgang is gedeeltelijk in de baselines en expliciet in `002` vastgelegd:

| Object | `001_init_schema.sql` | `schema.sql` | Effect van `002` |
|---|---:|---:|---|
| `project_embeddings.combined_embedding` | 3072 | 3072 | ongewijzigd; `002` raakt deze tabel niet |
| `funding_calls.embedding` | 768 | 768 | kolom droppen en opnieuw maken als 3072 |
| `document_chunks.embedding` | 768 | 768 | kolom droppen en opnieuw maken als 3072; modeldefault naar `gemini-embedding-001` |
| `embedding_cache.embedding` | 768 | 768 | cache truncaten; kolom opnieuw maken als 3072; modeldefault naar `gemini-embedding-001` |
| `shared_document_chunks.embedding` | 768 | niet aanwezig in dit snapshotmodel | ongewijzigd; niet door `002` behandeld |

De bewerking in `002` is opzettelijk destructief: bestaande 768-vectors gaan verloren. Na toepassing moeten calls, documentchunks en cache opnieuw worden opgebouwd. De snapshot bevat IVFFlat-indexen voor de 768-dimensionale call- en chunkkolommen; na het droppen van die kolommen blijven er geen equivalente 3072-indexen uit `002` over. Exacte/sequentiële vectorzoekacties blijven mogelijk, maar indexstrategie en pgvector-versie moeten apart worden gevalideerd.

`001` maakt daarnaast een HNSW-index op `project_embeddings.combined_embedding vector(3072)`. Standaard pgvector-indexering op het type `vector` ondersteunt niet zonder meer meer dan 2.000 dimensies; ook daarom is `001` niet als werkende fresh-bootstrap aangetoond.

## Volgorde voor een verse database

Met alleen de huidige bestanden bestaat er **geen volledig juiste, direct uitvoerbare volgorde**. De veiligste reconstructie van de bedoelde brede applicatiestaat is, na expliciete DBA-review:

1. Start een compatibele lege Supabase/PostgreSQL 15-instance met de vereiste rollen en extensions.
2. Maak van `schema.sql` een geschoonde, geteste baseline en pas uitsluitend die baseline toe. De huidige file mag niet ongewijzigd blind worden uitgevoerd vanwege de kale `pg_dump:`-regels en omgevingsafhankelijkheden.
3. Review en versioneer `002_upgrade_embeddings_to_3072.sql`; pas die daarna toe. Dit is de enige huidige file die logisch boven op de 768-snapshot hoort.
4. Laad relationele data en document-/callinhoud en genereer vervolgens alle getroffen embeddings opnieuw op 3072 dimensies.
5. Valideer tabelcontracten, vectorafmetingen, zoekfuncties, indexes, RLS, grants en applicatiesmokes.

In dit snapshotpad worden `001`, `008`, `009` en `cleanup_unused_tables.sql` **niet** daarna uitgevoerd:

- `001` is een alternatief, conflicterend baselinepad;
- `008` is al in de snapshot verwerkt en kan alleen redundante indexen toevoegen zonder afwijkende tabellen te corrigeren;
- `009` overlapt `response_feedback` en zou de opgeschoonde tabel `feedback_insights` terugbrengen;
- de snapshot weerspiegelt de cleanup grotendeels al, terwijl opnieuw uitvoeren met `CASCADE` onnodig destructief is.

Het alternatieve `001`-pad is alleen een beperkt backendprototype, niet een verse volledige MAP-IT-database. `002` faalt daar rechtstreeks op de ontbrekende kolommen `document_chunks.embedding_model` en `embedding_cache.model_version`; bovendien ontbreken de verwijderde tussenmigraties en overige appdomeinen. Dit pad is daarom geen aanbevolen productievolgorde.

## Aanbevolen vervolg, niet in deze wave uitgevoerd

1. Kies één schema-authority: een geschoonde snapshotbaseline of een volledig gereconstrueerde migratieketen, niet beide.
2. Neem elk volgend schemawijzigingsbestand Git-tracked op met unieke versie, checksum, datum, dependency, forward-fix/rollbackbeleid en ledgerinsert.
3. Leg de 3072-transitie en de verplichte re-embedding als één gecontroleerde releaseprocedure vast.
4. Laat CI vanaf een lege Supabase-instance migreren en controleer daarna objectcontracten en vectorafmetingen.
5. Archiveer verwijderde historische SQL expliciet of documenteer waarom het door de gekozen baseline is gesupersedet; herstel het niet blind naar de actieve keten.
