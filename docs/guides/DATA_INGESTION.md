# Data-ingestie en data-bootstrap

**Status:** actueel runbook, met bekende blockers

**Laatst geverifieerd:** 20 juli 2026

**Werkmap voor alle commando's:** `MAP-IT_SA/`

Dit runbook beschrijft wat vanuit een verse clone wel en niet reproduceerbaar is. Het relationele schema, de documentencollectie, CORDIS-projecten, embeddings en de Neo4j-graaf zijn afzonderlijke datasets. Een geslaagde schema-installatie betekent daarom nog niet dat MAPIT representatieve zoekresultaten kan leveren.

Zie ook [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) voor het actuele schema- en migratiecontract en [START_HERE.md](../../../START_HERE.md) voor het starten van de services.

## Eerst lezen: actuele blockers

| Blocker | Feitelijke situatie | Gevolg |
|---|---|---|
| Geen gedistribueerde PostgreSQL-baseline | De lokaal aanwezige `mapit_dump.dump` is niet Git-tracked. `neo4j_backup/project_embeddings.dump` wordt door `.gitignore` uitgesloten en bevat volgens `pg_restore -l` uitsluitend data voor `public.project_embeddings`. | Een verse clone kan de 13.865 projecten, 89.348 organisatieparticipaties en overige relationele data niet uit de repository herstellen. |
| Geen raw CORDIS-import naar PostgreSQL | Er is alleen `scripts/ingest_cordis_to_neo4j.py`; er is geen script dat `project.csv` en `organization.csv` naar PostgreSQL importeert. | Raw CORDIS-bestanden kunnen de graaf vullen, maar lossen de ontbrekende relationele projectdataset niet op. |
| CORDIS-bronmap ontbreekt | `data/` is Git-ignored en `data/cordis/` ontbreekt. Het Neo4j-script verwacht daar exact `project.csv` en optioneel `organization.csv`. | De raw Neo4j-ingestie stopt direct zonder `project.csv`. |
| Horizon-verwerkingsmappen ontbreken | `process_comprehensive_docs.py` leest `downloads/horizon_europe_comprehensive/`; `ingest_comprehensive_docs.py` leest `processed_docs/horizon_europe/ingestion_ready.jsonl`. Beide mappen ontbreken in een clone. | De scripts zijn geen enkelstaps-ingestie van `newdocs/`. De bronbestanden moeten eerst naar de verwachte structuur worden gestaged en verwerkt. |
| Gedeelde documenten ontbreken in een clone | De vijf lokaal aanwezige PDF's onder `data/shared_documents/` vallen onder de Git-ignore voor `data/`. | `process_shared_documents.py` heeft in een verse clone geen input. De melding in dat script over `download_shared_documents.py` is niet uitvoerbaar: dat downloadscript bestaat niet. |
| 3072-migratie niet geborgd | `migration/002_upgrade_embeddings_to_3072.sql` en de twee `reembed_*.py`-scripts zijn in de onderzochte worktree aanwezig maar niet Git-tracked. | De draaiende lokale database is 3072-dimensionaal, maar een clone van de huidige Git-baseline blijft voor document-, call- en cachevectors op 768 dimensies. |

De huidige ondersteunde overdrachtsroute is daarom: vraag de data-eigenaar om een versieerd, versleuteld PostgreSQL-artifact met manifest, of accepteer expliciet een beperkte omgeving zonder relationele CORDIS-data. Publiceer vóór overdracht minimaal artifactnaam, aanmaakdatum, schema- en dataversie, SHA-256, grootte, bronlicenties en een bevoegde contactpersoon. `Owner: TBD` is op dit moment nog een open blocker.

## Vereisten

1. Start PostgreSQL/Supabase en Neo4j volgens [START_HERE.md](../../../START_HERE.md).
2. Activeer de door `scripts/setup.sh` gemaakte virtualenv:

   ```bash
   source venv/bin/activate
   ```

3. Zet minimaal de volgende variabelen in `.env` of de shell:

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

   `EmbeddingService` valt voor de API-key terug van `GOOGLE_EMBEDDING_API_KEY` op `GEMINI_API_KEY`. Voor hostprocessen gebruikt Compose Neo4j-poort `17687`; binnen het Compose-netwerk is dat `bolt://neo4j:7687`.

4. Controleer verbinding en vectordimensies voordat data wordt geschreven:

   ```bash
   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c 'select current_database(), version();'
   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "select table_name, column_name, format_type(a.atttypid,a.atttypmod) as type from information_schema.columns c join pg_class t on t.relname=c.table_name join pg_namespace n on n.oid=t.relnamespace and n.nspname=c.table_schema join pg_attribute a on a.attrelid=t.oid and a.attname=c.column_name where c.table_schema='public' and c.column_name='embedding' order by table_name;"
   ```

   Ga niet verder wanneer de database `vector(768)` rapporteert terwijl de applicatie `EMBEDDING_DIMENSION=3072` gebruikt.

## Kies een bootstrapmodus

### Modus A — volledige, goedgekeurde PostgreSQL-dump

Dit is de enige route waarmee de relationele CORDIS-baseline nu volledig kan worden gereproduceerd. De dump moet buiten Git door de data-eigenaar worden geleverd. De lokaal aangetroffen dumps zijn geen overdraagbaar artifactcontract.

Controleer vóór herstel:

```bash
export MAPIT_DATA_DUMP=/absoluut/pad/naar/mapit-postgres-<dataversie>.dump
test -r "$MAPIT_DATA_DUMP"
sha256sum "$MAPIT_DATA_DUMP"
pg_restore --list "$MAPIT_DATA_DUMP" | less
```

Maak eerst een backup. Het volgende restorecommando verwijdert objecten uit de doeldatabase en is alleen bedoeld voor een lege, compatibele lokale Supabase-instance:

```bash
pg_dump --format=custom --file="pre-mapit-restore-$(date +%Y%m%d-%H%M%S).dump" "$DATABASE_URL"
pg_restore --clean --if-exists --no-acl --no-owner \
  --exit-on-error --dbname="$DATABASE_URL" "$MAPIT_DATA_DUMP"
```

Een full dump kan Supabase-beheerschema's (`auth`, `storage`, `realtime`) bevatten. Herstel hem niet over een gedeelde of productie-instance zonder een door de eigenaar geteste restoreprocedure. `neo4j_backup/project_embeddings.dump` is geen alternatief: dat artifact bevat alleen `project_embeddings`-rijen en vereist dat de bijbehorende `projects` al bestaan.

Verwachte lokale referentie na een volledige restore, gemeten op 20 juli 2026:

| Dataset | Verwacht aantal | Verificatie |
|---|---:|---|
| `projects` | 13.865 | `SELECT count(*) FROM projects;` |
| `organizations` | 89.348 | `SELECT count(*) FROM organizations;` |
| `project_embeddings` | 13.850, alle 13.850 gevuld | `SELECT count(*), count(combined_embedding) FROM project_embeddings;` |
| `horizon_documents` | 144 | `SELECT count(*) FROM horizon_documents;` |
| `document_chunks` | 38.697, alle 38.697 gevuld | `SELECT count(*), count(embedding) FROM document_chunks;` |
| `shared_documents` / `shared_document_chunks` | 54 / 13.147 | Twee afzonderlijke `count(*)`-queries |
| `funding_calls` | 2.758, alle 2.758 gevuld | `SELECT count(*), count(embedding) FROM funding_calls;` |

Deze aantallen zijn een lokale referentiesnapshot, geen universeel acceptatiecriterium voor toekomstige dataversies. Afwijkingen moeten door het artifactmanifest worden verklaard.

### Modus B — schema plus beperkte data

Gebruik deze modus wanneer geen goedgekeurde dump beschikbaar is. Installeer het schema zoals beschreven in [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md). Houd rekening met de daar beschreven migratiedrift: er bestaat nog geen deterministische, volledig geteste migratieketen. Zonder aanvullende import blijven relationele CORDIS-tools leeg; document-RAG en hardcoded programmareferenties kunnen wel afzonderlijk worden gevuld.

## Dataset-runbooks

### 1. CORDIS-projecten en organisaties in PostgreSQL

| Onderdeel | Waarde |
|---|---|
| Bronartifact | Volledige, door de data-eigenaar geleverde PostgreSQL-dump |
| Raw alternatief | Niet geïmplementeerd voor PostgreSQL |
| Vereisten | Schema dat overeenkomt met de dump; `projects.id` en `organizations."projectID"` zijn in de actuele database `integer` |
| Verwacht | Artifactmanifest; lokale referentie 13.865 projecten en 89.348 organisatieparticipaties |
| Idempotentie | Alleen via volledige restore naar een gecontroleerde doelinstance |

Herstel Modus A en voer daarna uit:

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

Stop wanneer `projects_without_title` of `organizations_without_project` onverwacht niet nul is. Er is geen repositoryscript om deze tabellen betrouwbaar opnieuw uit raw CSV op te bouwen.

### 2. CORDIS-graaf in Neo4j

Er zijn twee routes.

#### 2a. Tracked Neo4j-dump herstellen

`neo4j_backup/neo4j.dump` is Git-tracked. De SHA-256 van de op 20 juli 2026 onderzochte versie is `8363cefa4067d2320bf9fbc48cd16447616d9f8e517da59c0e111249bc5db3e2` (63.643.498 bytes). Controleer de checksum na clone.

```bash
sha256sum neo4j_backup/neo4j.dump
docker cp neo4j_backup/neo4j.dump mapit-neo4j:/var/lib/neo4j/import/neo4j.dump
docker compose stop neo4j
docker compose run --entrypoint neo4j-admin --rm neo4j database load \
  --from-path=/var/lib/neo4j/import/ neo4j --overwrite-destination=true
docker compose start neo4j
```

`docker cp` vermijdt hosttoegang tot de bindmount. `neo4j/import/` kan door de container als een andere UID zijn aangemaakt. Bij `Permission denied`: stop de container, inspecteer eerst `ls -ld neo4j neo4j/import`, en laat de eigenaar van de ontwikkelmachine de ACL/eigendom gericht corrigeren. Gebruik geen recursieve `chmod 777`.

De op 20 juli 2026 draaiende lokale graaf bevatte 13.865 `Project`-nodes, 25.096 unieke `Organization`-nodes en 89.263 `PARTICIPATES_IN`-relaties. Verifieer:

```cypher
MATCH (p:Project) RETURN count(p) AS projects;
MATCH (o:Organization) RETURN count(o) AS organizations;
MATCH (:Organization)-[r:PARTICIPATES_IN]->(:Project)
RETURN count(r) AS participations;
```

#### 2b. Raw CORDIS-CSV ingesteren

Download de officiële Horizon Europe CORDIS-export die in [EU_PROGRAMME_DATA_DOWNLOADS.md](../../docs_tracked/EU_PROGRAMME_DATA_DOWNLOADS.md) wordt genoemd en leg bron-URL, downloadtijd, licentie en SHA-256 vast. Pak minimaal deze semikolon-gescheiden UTF-8-bestanden uit:

```text
data/cordis/project.csv       verplicht
data/cordis/organization.csv  optioneel, maar nodig voor partner- en consortiumanalyse
```

Het script gebruikt `on_bad_lines="skip"`; het kan dus ongeldige bronregels overslaan. Vergelijk de logaantallen altijd met `wc -l` en bewaar de foutlog.

```bash
python scripts/ingest_cordis_to_neo4j.py --data-dir data/cordis
```

Het script gebruikt `MERGE` en is grotendeels herhaalbaar. `--clear` voert echter `MATCH (n) DETACH DELETE n` uit en wist de **hele** Neo4j-database, inclusief andere programmadata. Gebruik die flag alleen na een backup en expliciete goedkeuring.

Verwacht bij dezelfde CORDIS-export als de referentiesnapshot 13.865 projecten. Het aantal unieke organisaties is lager dan het aantal regels in `organization.csv`, omdat organisaties over projecten worden gemerged; de lokale referentie is 25.096 unieke nodes en 89.263 participatierelaties.

### 3. Projectembeddings

Actieve codeconfiguratie: `models/gemini-embedding-001`, `output_dimensionality=3072`. Het script combineert titel en objective, kapt op 2.000 tekens af en verwerkt standaard batches van 50. Het slaat alleen projecten op met een bruikbare titel en objective.

Prerequisites: gevulde `projects`, `project_embeddings.combined_embedding vector(3072)`, `DATABASE_URL` en een Google/Gemini embedding-key.

```bash
# Veilige eerste proef: maximaal 10 projecten
python scripts/generate_project_embeddings.py --test --verbose

# Daarna alle ontbrekende/failed/pending projecten
python scripts/generate_project_embeddings.py --batch-size 50
```

Herstarten is bedoeld als resume: bestaande rijen met status `completed` worden overgeslagen; writes gebruiken `ON CONFLICT (project_id) DO UPDATE`.

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

De lokale referentie is 13.850 gevulde embeddings tegenover 13.865 projecten; het verschil is niet automatisch een fout, omdat het script inhoudsfilters toepast.

### 4. Programmadocumenten naar `horizon_documents` en `document_chunks`

De volgende input is wel Git-tracked. Run eerst `--dry-run`; dit doet aantoonbaar geen databasewrites.

| Dataset | Standaardbron | PDF's in clone op 20-07-2026 | Exact commando |
|---|---|---:|---|
| Erasmus+ | `newdocs/erasmus` (alleen PDF's direct in de map) | 2 | `python scripts/ingest_erasmus_documents.py --source-dir newdocs/erasmus` |
| Creative Europe | `newdocs/creative_europe` (recursief) | 10 | `python scripts/ingest_creative_europe_documents.py --source-dir newdocs/creative_europe` |
| Digital Europe | `newdocs/digital_europe` (recursief) | 7 | `python scripts/ingest_digital_europe_documents.py --source-dir newdocs/digital_europe` |
| EU4Health | `newdocs/eu4health` (recursief) | 6 | `python scripts/ingest_eu4health_documents.py --source-dir newdocs/eu4health` |
| LIFE | `newdocs/life` (recursief) | 4 | `python scripts/ingest_life_documents.py --source-dir newdocs/life` |

Voorbeeld:

```bash
python scripts/ingest_creative_europe_documents.py \
  --source-dir newdocs/creative_europe --dry-run
python scripts/ingest_creative_europe_documents.py \
  --source-dir newdocs/creative_europe
```

Elke ingestie maakt per bestand één document en een data-afhankelijk aantal chunks. De script-summary moet `successful + failed = aantal gevonden PDF's` tonen. Duplicaten worden op file-hash geweigerd en als failure gerapporteerd; een volledig herhaalde run is daardoor niet schoon idempotent. Bij een gedeeltelijke fout kan al een documentrij met status `failed` bestaan. Verwijder zulke rijen niet handmatig zonder ook de afhankelijke chunks en de bronhash te controleren.

Verificatie:

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

De lokale snapshot bevatte respectievelijk 2 Erasmus-, 8 Creative Europe-, 6 Digital Europe-, 6 EU4Health- en 4 LIFE-documentrecords. Dat Creative Europe lager is dan de 10 huidige bron-PDF's onderstreept dat bronbestandcount en databasecount niet als vanzelf gelijk mogen worden verondersteld.

### 5. Horizon Europe 2025-work-programmes

De clone bevat 13 PDF's onder `newdocs/2025_work_programmes`, maar het tweestaps comprehensive-pad verwacht andere mappen. Een minimale staging voor precies deze collectie is:

```bash
mkdir -p downloads/horizon_europe_comprehensive/{work_programmes,programme_guides,call_pages,additional_resources}
cp newdocs/2025_work_programmes/*.pdf \
  downloads/horizon_europe_comprehensive/work_programmes/
python scripts/process_comprehensive_docs.py
test -s processed_docs/horizon_europe/ingestion_ready.jsonl
wc -l processed_docs/horizon_europe/ingestion_ready.jsonl
python scripts/ingest_comprehensive_docs.py --batch-size 200 --max-concurrent 10
```

De outputcount is data- en chunkingafhankelijk; het acceptatiecriterium is dat `processing_stats.json` dertien verwerkte documenten verklaart, `ingestion_ready.jsonl` niet leeg is, en alle geschreven chunks een 3072-vector hebben. De flag `--skip-existing` van `ingest_comprehensive_docs.py` verandert de uitvoering momenteel niet; bestaande documenten worden altijd via file-path gecontroleerd. Gebruik die flag dus niet als kwaliteits- of idempotentiegarantie.

### 6. Gedeelde documenten

Prerequisites: door de eigenaar geleverde PDF's in `data/shared_documents/`, een gevulde `shared_documents`/`shared_document_chunks`-schemafamilie en `DATABASE_URL`.

```bash
python scripts/process_shared_documents.py
```

`--force` herverwerkt ook reeds bekende file-hashes en is potentieel duplicerend/destructief voor de datakwaliteit. Zonder flag worden bekende hashes overgeslagen. De lokale niet-overdraagbare referentie bevat vijf bron-PDF's, maar de database bevatte 54 documents en 13.147 chunks; verwacht daarom geen 1-op-1-gelijkheid met de lokale map.

```sql
SELECT count(*) FROM shared_documents;
SELECT count(*) FROM shared_document_chunks;
SELECT count(*) FROM shared_documents d
WHERE NOT EXISTS (
  SELECT 1 FROM shared_document_chunks c WHERE c.document_id=d.id
);
```

### 7. Funding calls synchroniseren en embedden

`sync_topics_from_projects.py` leest unieke Horizon-topiccodes uit de bestaande `projects`-tabel, haalt ontbrekende details op bij het EU Funding & Tenders-topicendpoint en upsert op `topic_code`. Er zijn geen CLI-flags en geen dry-run.

```bash
python scripts/sync_topics_from_projects.py
```

Prerequisites: relationele CORDIS-projecten, netwerktoegang en `DATABASE_URL`. Het script commit per topic; na een netwerkfout kan het veilig opnieuw worden gestart omdat alleen ontbrekende topics worden opgehaald en bestaande topics via `ON CONFLICT` worden bijgewerkt.

De actuele code bevat daarnaast het niet-getrackte `scripts/reembed_funding_calls.py`. Gebruik dit niet als overdrachtscommando zolang het niet is gereviewd en gecommit. De productiecode verwacht 3072 dimensies; controleer na elke goedgekeurde re-embedding:

```sql
SELECT programme, count(*) AS calls, count(embedding) AS embedded
FROM funding_calls GROUP BY programme ORDER BY programme;
```

Lokale referentie op 20 juli 2026: 2.758 calls, alle 2.758 met embedding; Horizon Europe 2.274, Erasmus+ 277, Creative Europe 128, LIFE 35, EU4Health 32 en Digital Europe 12.

### 8. Hardcoded programmareferenties in Neo4j

Deze scripts hebben geen externe bronartifact nodig: actions, strands, regio's en regels staan als Python-constanten in de scripts. Ze zijn daarmee reproduceerbaar uit code, maar niet automatisch actueel ten opzichte van officiële programmaregels.

```bash
python scripts/ingest_erasmus_to_neo4j.py
python scripts/ingest_creative_europe_to_neo4j.py
python scripts/ingest_digital_europe_to_neo4j.py
python scripts/ingest_eu4health_to_neo4j.py
python scripts/ingest_life_to_neo4j.py
```

Writes gebruiken voornamelijk `MERGE`; opnieuw uitvoeren hoort nodes te actualiseren. De `--clear`-flags verwijderen nodes met de betreffende programmaspecifieke labels; gedeelde `Country`-nodes blijven bestaan. Digital Europe, EU4Health en LIFE verwijderen daarbij ook hun eigen `Programme`-node. Verifieer per script de geprinte counts en daarna:

| Dataset | Source artifact | Verwachte kernnodes uit de code |
|---|---|---|
| Erasmus+ | Python-constanten in `ingest_erasmus_to_neo4j.py` | 22 actions, 6 sectors, 13 partner regions |
| Creative Europe | Python-constanten in `ingest_creative_europe_to_neo4j.py` | 3 strands, 24 actions, 3 regions |
| Digital Europe | Python-constanten in `ingest_digital_europe_to_neo4j.py` | 6 objectives, 2 actions, 5 regions en 1 eigen programme-node |
| EU4Health | Python-constanten in `ingest_eu4health_to_neo4j.py` | 4 strands, 7 actions, 4 regions en 1 eigen programme-node |
| LIFE | Python-constanten in `ingest_life_to_neo4j.py` | 4 subprogrammes, 5 project types, 4 regions en 1 eigen programme-node |

De relatie- en `Country`-counts hangen af van reeds aanwezige gedeelde nodes; vergelijk daarvoor de summary van ieder script in plaats van één globale statische waarde af te dwingen.

```cypher
MATCH (n)
WHERE n:ErasmusAction OR n:CreativeEuropeAction OR n:DigitalEuropeAction
   OR n:EU4HealthAction OR n:LIFEProjectType
RETURN labels(n) AS labels, count(*) AS aantal
ORDER BY labels;
```

## 768 naar 3072 dimensies

| Object | Git-snapshot `migration/schema.sql` | Lokale DB 20-07-2026 | Actieve applicatiecode |
|---|---:|---:|---:|
| `project_embeddings` | 3072 | 3072 | 3072 |
| `document_chunks` | 768 | 3072 | 3072 |
| `funding_calls` | 768 | 3072 | 3072 |
| `embedding_cache` | 768 | 3072 (0 rijen) | 3072 |

De lokale `document_chunks.embedding_model`-waarden zeggen nog `text-embedding-004`, ondanks 3072-dimensionale vectors; die provenance is dus inconsistent. Behandel de kolomwaarde niet als bewijs van het werkelijk gebruikte model. Migratie 002 dropt de drie oude embeddingkolommen, leegt `embedding_cache` en vereist volledige re-embedding. Na de migratie zijn de oude IVFFlat-indexen niet aanwezig in de lokale database; vectorzoekopdrachten gebruiken daar exact/sequential search. Zie [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) voor details.

## Verificatie en quality gate

`scripts/quality_gate.py` is een conversation-testresultaatgate. De enige ondersteunde flags zijn:

```text
--results-dir PATH
--quality-baseline PATH
--threshold INTEGER
--fail-on-missing
```

Er bestaan geen `--check-embeddings`- of `--check-calls`-flags. Gebruik voor data quality de SQL- en Cypherqueries in dit runbook. Een volledige eindcontrole:

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

Leg bij elke ingestierun vast: Git-commit, bron-URL en licentie, brondatum, SHA-256, inputcount, succesvolle/overgeslagen/mislukte records, schema- en embeddingversie, uitvoertijd en operator. Zonder dit manifest is de run niet geschikt als nieuwe overdrachtsbaseline.
