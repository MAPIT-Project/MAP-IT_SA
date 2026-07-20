# Backend developer setup

**Laatst geverifieerd:** 20 juli 2026
**Repository:** `MAP-IT_SA`

Dit document beschrijft de backendsetup en de werkelijk beschikbare Make-/Dockercommando's. Voor
het full-stackpad, frontendconfiguratie en de servicevolgorde begin je bij
[START_HERE.md](../../START_HERE.md).

> **Databasestatus:** een verse clone heeft nog geen reproduceerbare volledige data- en
> migratiebaseline. Voer `migration/schema.sql`, `migration/001_init_schema.sql`, de Drizzle-files
> en `002_upgrade_embeddings_to_3072.sql` niet blind achter elkaar uit: ze zijn geen consistente
> ordered chain. Zie [databaseschema](../docs/DATABASE_SCHEMA.md) en
> [data-ingestion](../docs/guides/DATA_INGESTION.md).

## 1. Vereisten

- Python 3.11 of hoger. De lokale toolconfig richt zich op 3.11; de Dockerfile gebruikt Python 3.13.
- Docker Engine met de Compose V2-plugin (`docker compose`).
- Supabase CLI en PostgreSQL-clienttools (`psql`, eventueel `pg_restore`).
- Een geldige Gemini API-sleutel voor de standaardprovider en, voor embeddings, een Google
  embedding key of dezelfde Gemini-key.
- De frontendrepo `webapp-ui` naast deze repo als je lokale Supabase gebruikt.

## 2. Pythonomgeving

Vanuit `MAP-IT_SA`:

```bash
./scripts/setup.sh
source venv/bin/activate
make install-dev
```

De virtualenv heet **`venv`**, omdat `scripts/setup.sh` exact die directory maakt. Het script:

1. maakt `venv` als deze nog niet bestaat;
2. activeert de omgeving binnen het script;
3. werkt `pip` bij;
4. installeert alleen `requirements.txt`;
5. kopieert `.env.example` naar `.env` als `.env` ontbreekt.

De activatie uit een subprocess blijft niet in je huidige shell actief; voer daarom daarna zelf
`source venv/bin/activate` uit. `make install-dev` installeert aanvullend
`requirements-dev.txt`.

## 3. Backendconfiguratie

Bewerk `.env`, maar commit het bestand nooit. `app/core/config.py` vereist bij import minimaal een
niet-lege `DATABASE_URL`, `SUPABASE_URL` en `SUPABASE_SERVICE_KEY`. Voor een functionele chat zijn
ook een AI-provider en de bijbehorende modelconfig nodig.

Voor een **lokaal Pythonproces** met Supabase/Redis/Neo4j op de host:

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

Voor de **Compose-API** worden `DATABASE_URL`, `SUPABASE_URL`, `NEO4J_URI`, `REDIS_URL` en de
Redis-host/poort door `docker-compose.yml` overschreven met Docker-servicenamen. Keys, modellen en
embeddinginstellingen komen wel uit `.env`.

Genereer een lokale JWT-secret met:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

De huidige V3/V4-routes gebruiken de aanwezige authdependency niet en vertrouwen nog op standaard-
identiteiten. Deze secret inrichten maakt die routes dus nog niet veilig; dit is vastgelegd in het
[API-contract](../../API_CONTRACT.md) en [securityregister](../../SECURITY_REGISTER.md).

## 4. Supabase en het externe Docker-netwerk

Backend-Compose declareert `supabase_network_supabase_cli` als een **extern** netwerk en maakt dit
niet zelf. Start daarom eerst Supabase vanuit exact deze map:

```bash
cd ../webapp-ui/supabase_cli
supabase start
supabase status
docker network inspect supabase_network_supabase_cli >/dev/null
cd ../../MAP-IT_SA
```

Waarom deze map: de CLI vindt daar `supabase/config.toml` met
`project_id = "supabase_cli"`. De resulterende containernamen zijn onder meer
`supabase_db_supabase_cli` en `supabase_kong_supabase_cli`; precies die namen gebruikt Compose.
Voer niet opnieuw `supabase init` uit.

Lokale hoofdpoorten zijn API `54321`, PostgreSQL `54322` en Studio `54323`.

## 5. Database en data

Gebruik voor een overdrachtsomgeving een versieerde, volledige databasebaseline met checksum. De
repository bevat die op dit moment niet:

- `neo4j_backup/project_embeddings.dump` kan in een bestaande werkmap voorkomen, maar
  `/neo4j_backup/` is Git-ignored;
- de gecontroleerde dump bevat alleen `TABLE DATA public project_embeddings`, geen schema,
  projecten of organisaties;
- `data/cordis` is Git-ignored en ontbreekt in een verse clone;
- `migration/schema.sql` en `webapp-ui/supabase_cli/schema.sql` zijn snapshots van een hele
  Supabase-database en bevatten ongecommentarieerde regels die met `pg_dump:` beginnen;
- `001_init_schema.sql` en de frontend Drizzle-migraties spreken elkaar tegen over typen van
  `projects` en `organizations`;
- de 768-naar-3072-migratie is nog geen bewezen onderdeel van een getrackte keten.

Vraag daarom een goedgekeurde full dump aan of gebruik het raw-ingestpad. De exacte restore-,
ingest- en verificatiestappen staan in [DATA_INGESTION.md](../docs/guides/DATA_INGESTION.md). De
bedoelde volgorde is Supabase → schema baseline → nieuwere migraties → relationele data →
documentchunks/calls → embeddings met de juiste dimensie.

Controleer na restore in elk geval:

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

## 6. Redis en Neo4j starten

```bash
docker compose up -d redis neo4j
docker compose ps
```

Hostpoorten zijn Redis `16379`, Neo4j Browser `17474` en Bolt `17687`. Binnen het Compose-netwerk
blijven dat respectievelijk `6379`, `7474` en `7687`.

### Ingecheckte Neo4j-dump laden

`neo4j_backup/neo4j.dump` is wel Git-getrackt. Gebruik `docker cp`, omdat Neo4j de bindmount
`neo4j/import` vaak UID `7474` en modus `0700` geeft, waardoor je hostgebruiker daar geen toegang
meer toe heeft:

```bash
docker cp neo4j_backup/neo4j.dump mapit-neo4j:/var/lib/neo4j/import/neo4j.dump
docker compose stop neo4j
docker compose run --no-deps --rm --entrypoint neo4j-admin neo4j \
  database load --from-path=/var/lib/neo4j/import neo4j --overwrite-destination=true
docker compose start neo4j
docker compose ps
```

Als hosttools of pytest nog `Permission denied` op `neo4j/import` geven, herstel alleen die map:

```bash
sudo chown -R "$(id -u):$(id -g)" neo4j/import
chmod 755 neo4j/import
```

Voer geen brede `chown` op de repository of Docker-volumes uit.

## 7. Wat de Make-targets werkelijk doen

| Target | Exact gedrag | Bereikbaar op |
|---|---|---|
| `make run` | `uvicorn main:app --host 0.0.0.0 --port 8000` in de actieve hostomgeving | `http://localhost:8000` |
| `make run-reload` | hetzelfde met `--reload` | `http://localhost:8000` |
| `make docker-up` | alleen `docker compose up -d`; start Redis, Neo4j én een API-container | API `18000`, Redis `16379`, Neo4j `17474`/`17687` |
| `make docker-down` | `docker compose down` | stopt de Compose-stack; named volumes blijven normaal bestaan |
| `make install` | installeert `requirements.txt` via de actieve `pip` | n.v.t. |
| `make install-dev` | `make install`, daarna `requirements-dev.txt` | n.v.t. |
| `make test` | `pytest -q` | huidige baseline kan al bij collectie falen op `neo4j/import`-permissions |
| `make lint` | `ruff check app tests .` | n.v.t. |

### Ondersteunde startmodi

**Standaard full-stackmodus — alles in Compose:**

```bash
# Supabase en database zijn al gestart/geladen.
docker compose up -d --build
curl -fsS http://localhost:18000/api/health/live
```

Stel de frontend dan in met `BACKEND_URL=http://localhost:18000`.

**Backend-debugmodus — infra in Docker, API op de host:**

```bash
docker compose up -d redis neo4j
source venv/bin/activate
make run-reload
curl -fsS http://localhost:8000/api/health/live
```

Gebruik hierbij de host-URL's uit sectie 3 en zet frontend `BACKEND_URL` op
`http://localhost:8000`. Start in deze modus niet ook de Compose-service `api`.

## 8. Werkelijke V3- en V4-routes

De V3-prefix in `conversation_routes_v3.py` is `/api/v3/conversation`:

- `POST /api/v3/conversation/{conversation_id}/message/stream`
- `POST /api/v3/conversation/{conversation_id}/message`
- `GET /api/v3/conversation/{conversation_id}/context`
- `DELETE /api/v3/conversation/{conversation_id}/context`
- `GET /api/v3/conversation/health`
- `GET /api/v3/conversation/analytics/summary`
- `GET /api/v3/conversation/analytics/low-confidence`
- `GET /api/v3/conversation/analytics/search`
- `GET /api/v3/conversation/analytics/export`

De V4-prefix in `proposal_session_routes.py` is **`/api/v4/proposal-session`**, niet
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

`POST .../create` verwacht `proposal_id`, `call_id`, `title`, optioneel `proposal_type` en optioneel
`conversation_id`; `user_id` is momenteel een queryparameter met default `default-user`. Zie voor
schemas, events en voorbeelden het [API-contract](../../API_CONTRACT.md).

Let op: de gedeclareerde V4-healthroute staat in het routebestand **na**
`GET /api/v4/proposal-session/{session_id}`. Door FastAPI/Starlette-routevolgorde kan `health`
daardoor als `session_id` worden geïnterpreteerd. Gebruik voor algemene proceshealth de werkende
`/api/health/live` en `/api/health` routes.

## 9. Verificatie

```bash
curl -fsS http://localhost:18000/api/health/live
curl -sS http://localhost:18000/api/health | python3 -m json.tool
curl -sS http://localhost:18000/openapi.json -o /tmp/mapit-openapi.json
```

Voor host-debugmodus vervang je `18000` door `8000`. `/api/health/live` bewijst alleen dat het proces
reageert; `/api/health` controleert PostgreSQL, Neo4j, Redis, Gemini, embeddings en Supabase. Een
`degraded` resultaat moet je per component onderzoeken.

V3-streamsmoke, na het aanmaken van een gebruiker en conversatie via de frontend:

```bash
curl -N -X POST \
  'http://localhost:18000/api/v3/conversation/<conversation-id>/message/stream?user_id=1' \
  -H 'Content-Type: application/json' \
  -d '{"message":"Noem passende open Horizon Europe-calls voor digitale gezondheid.","include_context":true}'
```

Verwacht SSE-regels met `data:`, gevolgd door een `complete`-event. Zonder de juiste datasets of
embeddingdimensie is dit alleen een technische smoke test, geen inhoudelijke acceptatietest.

## 10. Troubleshooting

### Extern Supabase-netwerk ontbreekt

```bash
cd ../webapp-ui/supabase_cli
supabase status || supabase start
docker network inspect supabase_network_supabase_cli
```

Maak niet handmatig een leeg netwerk met dezelfde naam als je de Supabase-containers werkelijk wilt
bereiken; start Supabase zodat de juiste containers eraan gekoppeld zijn.

### API gebruikt de verkeerde poort

- `make run` en `make run-reload`: hostpoort `8000`.
- `make docker-up`/Compose-API: hostpoort `18000`.
- Binnen Docker luistert FastAPI altijd op `8000`.

Controleer met `docker compose ps` en pas frontend `BACKEND_URL` aan de gekozen modus aan.

### Neo4j blijft unhealthy

De healthcheck heeft een startperiode van 60 seconden. Bekijk daarna:

```bash
docker compose logs --tail=150 neo4j
curl -I http://localhost:17474
```

Controleer wachtwoordconsistentie en de permissions van uitsluitend `neo4j/import`.

### Vectorzoekactie faalt op dimensie

De actieve codeconfig is 3072 (`gemini-embedding-001`), maar oudere schema-snapshots hebben 768 voor
calls/chunks/cache. Controleer het live type vóór ingest of re-embedding:

```bash
psql "$MAPIT_DATABASE_URL" -c \
  "SELECT table_name, column_name, format_type(a.atttypid,a.atttypmod)
   FROM information_schema.columns c
   JOIN pg_attribute a ON a.attname=c.column_name
   JOIN pg_class k ON k.oid=a.attrelid AND k.relname=c.table_name
   WHERE c.table_schema='public' AND c.column_name='embedding';"
```

Migreer niet ad hoc: volg de vastgestelde baseline in
[DATABASE_SCHEMA.md](../docs/DATABASE_SCHEMA.md) en regenereer daarna alle getroffen embeddings.

## Stoppen

```bash
docker compose down
cd ../webapp-ui/supabase_cli
supabase stop
```

Deze commando's verwijderen normaal niet de named volumes. Een clean/resetactie is destructief en
hoort alleen bij een bewust wegwerpbare lokale omgeving.
