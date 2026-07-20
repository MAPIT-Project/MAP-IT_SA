# Environment matrix

Deze matrix beschrijft de environment variables die MAPIT daadwerkelijk leest of in de meegeleverde voorbeelden en Docker Compose declareert. De classificatie **vereist** is gebaseerd op de huidige code, niet alleen op de `.env.example`-bestanden.

Laatst geverifieerd: 20 juli 2026.

## Bronnen en leeswijzer

Gecontroleerde bronnen:

- backend: `MAP-IT_SA/.env.example`, `MAP-IT_SA/docker-compose.yml`, `MAP-IT_SA/app/core/config.py` en alle Python-bestanden onder `MAP-IT_SA/`;
- frontend: `webapp-ui/.env.example`, `webapp-ui/drizzle.config.ts`, `process.env`, `import.meta.env` en SvelteKit `$env/*`-gebruik onder `webapp-ui/`;
- test/CI-variabelen zijn apart opgenomen, zodat zij niet per ongeluk als productieconfiguratie worden behandeld.

Betekenis van de kolommen:

- **Vereist**: `Ja` betekent dat de applicatie zonder waarde niet initialiseert of de primaire functie niet werkt; `conditioneel` betekent dat de waarde alleen nodig is voor de genoemde provider/feature.
- **Geheim**: waarden met `Ja` horen uitsluitend in een secret store of server-side environment. Een `PUBLIC_`- of `VITE_`-prefix betekent dat SvelteKit/Vite de waarde aan de browser mag leveren.
- **Omgeving**: `L/S/P` betekent dat local, staging en production ieder een eigen waarde horen te hebben. `S/P` betekent minimaal unieke staging- en productionwaarden. Werkelijke staging- en productionwaarden staan niet in deze repository.
- **Default / voorbeeld**: `code:` is een echte fallback; `voorbeeld:` komt alleen uit een `.env.example` en is geen veilige runtime-default.

## Omgevingsprofielen

| Onderwerp | Local | Staging | Production |
|---|---|---|---|
| Database | Supabase CLI op `localhost:54322`, of de optionele lokale PostgreSQL-container | Eigen niet-productiedatabase | Eigen productiedatabase; TLS volgens providerbeleid |
| Supabase | Local CLI URL (`localhost:54321`) of ontwikkelproject | Afzonderlijk stagingproject | Productieproject |
| Backend-URL vanuit frontend | `http://localhost:18000` | Interne/publieke staging-API-URL | Productie-API-URL |
| Publieke frontend-URL | `http://localhost:5173` | Staging-origin | Canonieke productie-origin |
| Debugging | Kan aan | Bij voorkeur uit | Uit |
| CORS | Lokale origin(s) | Alleen staging-origin(s) | Alleen productie-origin(s); geen `*` |
| Secrets | Lokale ontwikkelwaarden | Unieke staging-secrets | Unieke production-secrets; roteren en centraal beheren |
| Docker hostnames | In Compose: `redis`, `neo4j`, `supabase_db_supabase_cli`, `supabase_kong_supabase_cli` | Deployment-specifiek | Deployment-specifiek |

## Gedeelde en backend-kernconfiguratie

`Settings` in `app/core/config.py` leest veldnamen case-insensitive als hoofdlettervariabelen. Daardoor zijn bijvoorbeeld ook `APP_NAME`, `APP_VERSION` en `OPENROUTER_BASE_URL` geldig, hoewel zij ontbreken in de backend `.env.example`.

| Naam | Component | Vereist | Geheim | Default / voorbeeld | Omgeving | Beschrijving |
|---|---|---:|---:|---|---|---|
| `APP_NAME` | Backend | Nee | Nee | code: `CORDIS Research Projects RAG API` | Meestal gelijk | Titel van de FastAPI-applicatie. |
| `APP_VERSION` | Backend | Nee | Nee | code: `1.0.0` | Per release | Versie in API- en healthmetadata. |
| `API_HOST` | Backend | Nee | Nee | code/voorbeeld: `0.0.0.0` | Meestal gelijk | Bind-adres van Uvicorn. |
| `API_PORT` | Backend | Nee | Nee | code/voorbeeld: `8000`; Compose publiceert hostpoort `18000` | L/S/P mogelijk | Interne luisterpoort van de backend. |
| `DEBUG` | Beide | Nee | Nee | backend code/voorbeelden: `false`; frontend leest deze waarde niet | S/P: `false` | Backend reload/debugmodus. De gelijknamige frontendvoorbeeldwaarde heeft momenteel geen effect. |
| `CORS_ORIGINS` | Backend | Nee | Nee | code/voorbeeld: `["*"]` | **L/S/P** | Toegestane browser-origins. Beperk staging en productie expliciet. |
| `DATABASE_URL` | Beide | **Ja** (backend en frontend Drizzle CLI) | **Ja** | geen code-default; voorbeeld backend: lokale PostgreSQL-DSN | **L/S/P** | Backend runtime- en scriptverbinding. In de frontend leest uitsluitend `drizzle.config.ts` deze naam voor Drizzle Kit; zie [Database-naamgeving](#database-naamgeving-frontenddrizzle). |
| `DB_MIN_CONNECTIONS` | Backend | Nee | Nee | Settings: `5`; directe proposal-session fallback: `2` | Capaciteitsafhankelijk | Minimumgrootte van de databasepool. |
| `DB_MAX_CONNECTIONS` | Backend | Nee | Nee | Settings: `50`; directe proposal-session fallback: `10` | Capaciteitsafhankelijk | Maximumgrootte van de databasepool. Stem af op de databaseverbindinglimiet. |
| `SUPABASE_URL` | Backend; ongebruikt frontendvoorbeeld | **Ja** voor backend | Nee | geen backend-default; frontendvoorbeeld: `http://localhost:54321`; Compose: `http://supabase_kong_supabase_cli:8000` | **L/S/P** | Server-side Supabase-URL. De frontendcode gebruikt in plaats daarvan `PUBLIC_SUPABASE_URL`. |
| `SUPABASE_ANON_KEY` | Backend | Nee | Nee | geen; placeholder in backendvoorbeeld | **L/S/P** | Publieke/anonymous Supabase-key voor backendcalls die geen service role nodig hebben. |
| `SUPABASE_SERVICE_KEY` | Backend | **Ja** | **Ja** | geen; placeholder in backendvoorbeeld | **L/S/P** | Supabase service-role key voor backendbeheer. Niet aan de browser leveren. |
| `JWT_SECRET_KEY` | Beide | **Ja in S/P** | **Ja** | backend: willekeurig per proces indien afwezig; frontend: `fallback-secret-change-in-production` | **L/S/P** | Ondertekening van JWT's; moet in frontend en backend exact gelijk zijn. De codefallbacks zijn niet geschikt voor gedeelde sessies of productie. |
| `STATIC_API_KEY` | Backend | Nee | **Ja** | geen | **L/S/P** indien gebruikt | Optionele statische sleutel voor eenvoudige API-authenticatie. |
| `DOCKER_ENV` | Backend | Nee | Nee | code: `false`; Compose: `true` | Local/deployment | Geeft aan dat de backend in de Docker Compose-context draait. |

## AI-providers en embeddings

Minimaal de sleutel van de gekozen provider is operationeel nodig. De configuratievalidator dwingt dit niet centraal af; fouten kunnen daarom pas optreden wanneer een AI-functie wordt aangeroepen.

| Naam | Component | Vereist | Geheim | Default / voorbeeld | Omgeving | Beschrijving |
|---|---|---:|---:|---|---|---|
| `DEFAULT_AI_PROVIDER` | Backend | Nee | Nee | code/voorbeeld/Compose: `gemini` | Meestal gelijk | Primaire tekstprovider (`gemini`, `openai` of gedeeltelijk `openrouter`, afhankelijk van de service). |
| `GEMINI_API_KEY` | Backend | Conditioneel | **Ja** | geen; placeholder in voorbeeld | **L/S/P** | Gemini-generatiekey; dient ook als fallback voor embeddings. |
| `GEMINI_MODEL` | Backend | Nee | Nee | meestal `gemini-3-flash-preview`; `comprehensive_reviewer.py` valt zelfstandig terug op `gemini-2.0-flash-exp` | Per release/omgeving | Snel Gemini-model. Leg in S/P expliciet vast om componentafwijkingen te voorkomen. |
| `GEMINI_PRO_MODEL` | Backend | Nee | Nee | `gemini-3.1-pro-preview` | Per release/omgeving | Zwaarder Gemini-model voor slimme routering. |
| `OPENAI_API_KEY` | Backend | Conditioneel | **Ja** | geen; placeholder in voorbeeld | **L/S/P** | OpenAI API-key voor generatie en providerfallback. |
| `OPENAI_MODEL` | Backend | Nee | Nee | `gpt-4-turbo` | Per release/omgeving | OpenAI-modelnaam. |
| `OPENROUTER_API_KEY` | Backend | Conditioneel | **Ja** | geen; placeholder in voorbeeld | **L/S/P** | OpenRouter-key voor ondersteunde generation/memory-paden. |
| `OPENROUTER_MODEL` | Backend | Nee | Nee | `x-ai/grok-4-fast:free` | Per release/omgeving | OpenRouter-modelnaam uit Settings/Compose. |
| `OPENROUTER_BASE_URL` | Backend | Nee | Nee | code: `https://openrouter.ai/api/v1` | Meestal gelijk | Base-URL voor OpenRouter. Ontbreekt in `.env.example`. |
| `SMART_MODEL_ROUTING` | Backend | Nee | Nee | `true` | Meestal gelijk | Routeert complexe taken naar het pro-model. |
| `GOOGLE_EMBEDDING_API_KEY` | Backend | Conditioneel | **Ja** | geen; fallback is `GEMINI_API_KEY` in embeddingservice | **L/S/P** | Google-key voor vector-embeddings. Nodig wanneer vector search/embeddingjobs aanstaan en geen bruikbare Gemini-key beschikbaar is. |
| `GOOGLE_API_KEY` | Backendcode; tevens ongebruikt frontendvoorbeeld | Conditioneel | **Ja** | geen | **L/S/P** | Alternatieve fallback-key in de query planner. De frontend declareert hem, maar leest hem niet. |
| `EMBEDDING_MODEL` | Backend | Nee | Nee | Settings/Compose: `models/gemini-embedding-001`; backendvoorbeeld: `gemini-embedding-001` | Per release | Embeddingmodel. Gebruik bij voorkeur expliciet één vorm, omdat de bronnen van elkaar verschillen. |
| `EMBEDDING_DIMENSION` | Backend | Nee | Nee | `3072` | Gelijk aan DB-schema | Vectorafmeting; moet overeenkomen met pgvector-kolommen en het gekozen model. |

## Backend retrieval-, context- en prestatietuning

De `MAX_CONTEXT_*`, `LLM_TIMEOUT_SECONDS` en conversatievariabelen hieronder stonden niet in de backend `.env.example` maar worden wel direct met `os.getenv` gelezen.

| Naam | Component | Vereist | Geheim | Default | Omgeving | Beschrijving |
|---|---|---:|---:|---|---|---|
| `VECTOR_SEARCH_ENABLED` | Backend | Nee | Nee | Settings: `false`; `.env.example`/Compose: `true` | Per omgeving | Schakelt vector search in. De effectieve default hangt dus af van de startwijze. |
| `CHUNK_SIZE` | Backend | Nee | Nee | `1000` | Meestal gelijk | Doelgrootte van documentchunks. |
| `CHUNK_OVERLAP` | Backend | Nee | Nee | `300` | Meestal gelijk | Overlap tussen opeenvolgende chunks. |
| `MAX_CHUNKS_PER_QUERY` | Backend | Nee | Nee | `20` | Capaciteitsafhankelijk | Maximumaantal vectorresultaten per query. |
| `SIMILARITY_THRESHOLD` | Backend | Nee | Nee | `0.45` | Kwaliteitsafhankelijk | Minimale vectorsimilariteit. |
| `MAX_CONTEXT_CHARS` | Backend | Nee | Nee | `400000` | Capaciteitsafhankelijk | Totale tekenlimiet voor de tool-aware agentcontext. |
| `MAX_TOOL_RESULT_CHARS` | Backend | Nee | Nee | `30000` | Capaciteitsafhankelijk | Tekenlimiet per toolresultaat in agentcontext. |
| `MAX_OBSERVATION_CHARS` | Backend | Nee | Nee | `20000` | Capaciteitsafhankelijk | Tekenlimiet per agentobservatie. |
| `MAX_DOCUMENT_CHARS` | Backend | Nee | Nee | `1000` | Kwaliteitsafhankelijk | Tekenlimiet van documentinhoud die in agentcontext wordt geplaatst. |
| `MAX_RETRIEVAL_CHUNKS` | Backend | Nee | Nee | `4` | Capaciteitsafhankelijk | Maximumaantal retrievalchunks in conversation memory. |
| `MAX_CONTEXT_TOKENS` | Backend | Nee | Nee | `8000` | Modelafhankelijk | Tokenbudget voor conversation memory. Dit staat los van `MAX_CONTEXT_CHARS`. |
| `SUMMARIZE_EVERY_N_TURNS` | Backend | Nee | Nee | `5` | Kwaliteitsafhankelijk | Frequentie waarmee conversaties worden samengevat. |
| `RETRIEVAL_CACHE_TTL` | Backend | Nee | Nee | `3600` s | Omgevings-/data-afhankelijk | Cacheduur voor conversation retrieval. |
| `LLM_TIMEOUT_SECONDS` | Backend | Nee | Nee | `30` s | Capaciteitsafhankelijk | Timeout rond een LLM-aanroep van de tool-aware agent. |
| `EMBEDDING_TIMEOUT` | Backend | Nee | Nee | `30.0` s | Capaciteitsafhankelijk | Timeout voor embeddinggeneratie in similar-project search. |
| `VECTOR_SEARCH_TIMEOUT` | Backend | Nee | Nee | `10.0` s | Capaciteitsafhankelijk | Timeout voor vectorzoekacties. |
| `GRAPH_CONTEXT_TIMEOUT` | Backend | Nee | Nee | `30.0` s | Capaciteitsafhankelijk | Geconfigureerde graph-contexttimeout. |
| `LONG_QUERY_THRESHOLD` | Backend | Nee | Nee | `500` tekens | Meestal gelijk | Drempel waarna query preprocessing de lange-queryroute kiest. |
| `MAX_PROCESSED_QUERY_LENGTH` | Backend | Nee | Nee | `400` tekens | Meestal gelijk | Maximale lengte van een voorbewerkte query. |

## Backend services, documenten en externe API's

| Naam | Component | Vereist | Geheim | Default / voorbeeld | Omgeving | Beschrijving |
|---|---|---:|---:|---|---|---|
| `REDIS_URL` | Backend | Nee (fallback mogelijk) | Mogelijk | Settings/voorbeeld: `redis://localhost:6379/0`; sommige directe codepaden: `redis://localhost:6379`; Compose: `redis://redis:6379/0` | **L/S/P** | Redisverbinding voor rate limiting/cache en beschikbaarheidstests. Voeg credentials/TLS toe indien de provider dat vereist. |
| `REDIS_HOST` | Backend | Nee | Nee | directe code: `localhost`; backendvoorbeeld/Compose: `redis` | **L/S/P** | Host voor short-term memory. Voor niet-Docker local hoort dit doorgaans `localhost` te zijn. |
| `REDIS_PORT` | Backend | Nee | Nee | `6379` | Meestal gelijk | Redispoort voor memoryservices. |
| `CELERY_BROKER_URL` | Backend | Nee | Mogelijk | voorbeeld local: `redis://localhost:6379/0`; Compose: `redis://redis:6379/0` | **L/S/P** | Optionele Celery broker-URL. |
| `CELERY_RESULT_BACKEND` | Backend | Nee | Mogelijk | voorbeeld local: `redis://localhost:6379/0`; Compose: `redis://redis:6379/0` | **L/S/P** | Optionele Celery result-backend. |
| `TASK_TIME_LIMIT` | Backend | Nee | Nee | `300` s | Capaciteitsafhankelijk | Harde taaklimiet uit Settings. |
| `TASK_SOFT_TIME_LIMIT` | Backend | Nee | Nee | `240` s | Capaciteitsafhankelijk | Zachte taaklimiet uit Settings. |
| `NEO4J_URI` | Backend | Nee | Nee | code: `bolt://localhost:7687`; Compose: `bolt://neo4j:7687` | **L/S/P** | Bolt-URL voor graph queries. |
| `NEO4J_USER` | Backend | Nee | Nee | `neo4j` | L/S/P mogelijk | Neo4j-gebruikersnaam. |
| `NEO4J_PASSWORD` | Backend/infra | **Ja in S/P** | **Ja** | code/Composefallback: `mapit_secure_password_2024` | **L/S/P** | Neo4j-wachtwoord. De meegeleverde fallback is alleen voor local development. |
| `MAX_FILE_SIZE_MB` | Backend | Nee | Nee | `50` | Beleidsafhankelijk | Backend uploadlimiet; onafhankelijk van de frontendlimiet. |
| `SUPPORTED_FILE_TYPES` | Backend | Nee | Nee | `[".pdf", ".txt", ".md", ".html"]` | Meestal gelijk | JSON-lijst met geaccepteerde bestandsextensies. |
| `UPLOAD_DIR` | Backend | Nee | Nee | `uploads` | **L/S/P** | Opslagpad voor uploads; maak dit persistent in deployments die lokale opslag gebruiken. |
| `EU_PORTAL_BASE_URL` | Backend | Nee | Nee | `https://api.tech.ec.europa.eu/search-api/prod/rest/search` | Meestal gelijk | EU Funding & Tenders zoekendpoint. |
| `EU_PORTAL_TOPIC_DETAILS_URL` | Backend | Nee | Nee | `https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails` | Meestal gelijk | Basis-URL voor topicdetail-JSON. |
| `EU_PORTAL_FACET_URL` | Backend | Nee | Nee | `https://api.tech.ec.europa.eu/search-api/prod/rest/facet` | Meestal gelijk | EU Portal facetendpoint. |
| `CALL_ENRICHMENT_MAX_RETRIES` | Backend | Nee | Nee | `3` | Capaciteitsafhankelijk | Aantal retries na de eerste enrichmentpoging. |
| `CALL_ENRICHMENT_BASE_DELAY` | Backend | Nee | Nee | `1.0` s | Capaciteitsafhankelijk | Initiële retryvertraging. |
| `CALL_ENRICHMENT_MAX_DELAY` | Backend | Nee | Nee | `30.0` s | Capaciteitsafhankelijk | Maximale retryvertraging. |
| `CALL_ENRICHMENT_EXPONENTIAL_BASE` | Backend | Nee | Nee | `2.0` | Meestal gelijk | Exponentiële backofffactor. |
| `CALL_ENRICHMENT_CACHE_TTL` | Backend | Nee | Nee | `3600` s | Data-afhankelijk | Cacheduur van verrijkte calldetails. |
| `ENHANCED_CALL_SEARCH_CACHE_TTL` | Backend | Nee | Nee | `3600` s | Data-afhankelijk | Cacheduur van enhanced call search. |

## Frontendconfiguratie

| Naam | Component | Vereist | Geheim | Default / voorbeeld | Omgeving | Beschrijving |
|---|---|---:|---:|---|---|---|
| `PRIVATE_DATABASE_URL` | Frontend server runtime | **Ja** | **Ja** | geen code-default; voorbeeld: lokale PostgreSQL-DSN | **L/S/P** | Databaseverbinding voor SvelteKit serverroutes en runtime Drizzle-client. Niet aan clientcode blootstellen. |
| `BACKEND_URL` | Frontend server runtime | Nee | Nee | code/voorbeeld: `http://localhost:18000` | **L/S/P** | Basis-URL waarmee serverroutes verzoeken naar de FastAPI-backend proxyen. |
| `PUBLIC_SUPABASE_URL` | Frontend browser/server | **Ja** | Nee | code: lege string; voorbeeld: project-URL | **L/S/P** | Supabase-URL voor browser- en serverclients. Door `PUBLIC_` zichtbaar in de browserbundle. |
| `PUBLIC_SUPABASE_ANON_KEY` | Frontend browser/server | **Ja** | Nee | code: lege string; placeholder in voorbeeld | **L/S/P** | Supabase anonymous key; publiek ontwerp, maar bescherm data met RLS. |
| `SUPABASE_SERVICE_ROLE_KEY` | Frontend server | Conditioneel | **Ja** | geen; adminroutes vallen terug op anon key | **L/S/P** | Service-role key voor collaboration member/invite-beheer. Alleen server-side instellen. |
| `VITE_SUPABASE_URL` | Frontend legacy/testroute | Conditioneel | Nee | geen code-default; placeholder in voorbeeld | **L/S/P** | Alleen gebruikt door `/api/test_rls`; normale frontendcode gebruikt `PUBLIC_SUPABASE_URL`. |
| `VITE_SUPABASE_ANON_KEY` | Frontend legacy/testroute | Conditioneel | Nee | geen code-default; placeholder in voorbeeld | **L/S/P** | Alleen gebruikt door `/api/test_rls`; door `VITE_` zichtbaar in de clientomgeving. |
| `PUBLIC_APP_NAME` | Frontend browser | Nee | Nee | code/voorbeeld: `Mapit AI Expert` | Branding-afhankelijk | Applicatienaam en SEO-titel. |
| `PUBLIC_APP_URL` | Frontend browser | Nee | Nee | code/voorbeeld: `http://localhost:5173` | **L/S/P** | Canonieke URL voor SEO-links en afbeeldingen. |
| `PUBLIC_APP_ENV` | Frontend browser | Nee | Nee | `development` | **L/S/P** | Applicatieprofiel: `development`, `testing` of `production`. |
| `PUBLIC_ENABLE_DEBUG_TOOLS` | Frontend browser | Nee | Nee | code: aan tenzij `PUBLIC_APP_ENV=production`; voorbeeld: `true` | **L/S/P** | Toont/verbergt frontend debugtools. In productie uitzetten. |
| `PUBLIC_ENABLE_ANALYTICS` | Frontend browser | Nee | Nee | code: aan bij `PUBLIC_APP_ENV=production`; voorbeeld: `false` | **L/S/P** | Frontend feature flag voor analytics. |
| `PUBLIC_API_TIMEOUT_MS` | Frontend browser | Nee | Nee | `30000` ms | Capaciteitsafhankelijk | Geconfigureerde publieke API-timeout. |
| `PUBLIC_MAX_UPLOAD_SIZE_MB` | Frontend browser | Nee | Nee | `10` | Beleidsafhankelijk | Frontend uploadlimiet; houd deze maximaal gelijk aan backend `MAX_FILE_SIZE_MB`. |
| `NODE_ENV` | Frontend/Node platform | Door buildplatform | Nee | geen applicatiedefault | **L/S/P** | `migrations.ts` gebruikt alleen bij exact `development` de hardcoded lokale DB-config; anders `PRIVATE_DATABASE_URL`. |
| `PUBLIC_SUPABASE_SERVICE_KEY` | Alleen frontendvoorbeeld; niet gebruikt | **Nee — niet instellen** | **Ja, maar publiek blootgesteld** | placeholder in voorbeeld | Geen | Onveilige/stale declaratie. Een service-role key mag nooit een `PUBLIC_`-prefix hebben. Gebruik server-side `SUPABASE_SERVICE_ROLE_KEY`. |
| `MAPBOX_API_KEY` | Alleen frontendvoorbeeld; niet gebruikt | Nee | Beperk als publiek token | placeholder in voorbeeld | L/S/P indien later gebruikt | Momenteel geen codeconsumer gevonden. |

## Database-naamgeving frontend/Drizzle

De twee frontendnamen zijn geen alternatieven in de huidige code:

| Proces | Gelezen variabele | Bron |
|---|---|---|
| SvelteKit runtime en serverroutes | `PRIVATE_DATABASE_URL` | `src/lib/server/db/index.ts`, `src/lib/server/db/migrations.ts`, `/api/test` |
| Drizzle Kit CLI (`generate`, `migrate`, enz.) | `DATABASE_URL` | `webapp-ui/drizzle.config.ts` |
| FastAPI backend en Python scripts | `DATABASE_URL` | backend `Settings` en directe `os.getenv`-calls |

De frontend `.env.example` bevat momenteel alleen `PRIVATE_DATABASE_URL`, terwijl `drizzle.config.ts` hard faalt als `DATABASE_URL` ontbreekt. Voor frontendontwikkeling/deployment moeten daarom **beide server-side variabelen** worden gezet, doorgaans op dezelfde PostgreSQL-DSN:

```dotenv
# Alleen server-side; nooit PUBLIC_ of VITE_ maken.
PRIVATE_DATABASE_URL=postgresql://...
DATABASE_URL=postgresql://...
```

Dit document corrigeert de operationele verwarring; de configuratiebestanden zijn bewust niet gewijzigd. Let op dat de backend een eigen procesomgeving heeft: zijn `DATABASE_URL` kan dezelfde database aanwijzen, maar wordt niet automatisch met de frontend gedeeld.

## Test- en CI-only variabelen uit Python

| Naam | Component | Vereist | Geheim | Default | Omgeving | Beschrijving |
|---|---|---:|---:|---|---|---|
| `TEST_API_URL` | Backendtests | Nee | Nee | meestal `http://localhost:8000` | Testomgeving | Dominante base-URL voor live/integratie- en kwaliteitstests. |
| `MAP_IT_API_URL` | Kwaliteitstests | Nee | Nee | `http://localhost:8000` | Testomgeving | Base-URL gebruikt door de `test_prompt_*`-suite. |
| `MAPIT_API_URL` | Eén Neo4j-foutscenario | Nee | Nee | `http://localhost:8000` | Testomgeving | Afwijkende naam zonder underscore; niet uitwisselbaar met `MAP_IT_API_URL`. |
| `API_BASE_URL` | Enkele kwaliteitsscenario's | Nee | Nee | `http://localhost:8000` | Testomgeving | Derde alias voor de test-API-base-URL. |
| `SKIP_LIVE_API_TESTS` | Kwaliteitstests | Nee | Nee | live tests worden alleen overgeslagen bij waarde `1` | CI/test | Zet op `1` om live API-tests over te slaan. |
| `GITHUB_OUTPUT` | GitHub Actions | Door runner | Nee | geen | CI | Runnerbestand waarin `scripts/quality_gate.py` outputs schrijft. |
| `GITHUB_STEP_SUMMARY` | GitHub Actions | Door runner | Nee | geen | CI | Runnerbestand voor de Markdown job summary. |

## Docker Compose- en image-interne variabelen

Deze waarden configureren containers, niet rechtstreeks de MAPIT-processen. De Neo4j-waarden zijn in `docker-compose.yml` hardcoded, met uitzondering van het wachtwoord in `NEO4J_AUTH`.

| Naam | Component | Vereist | Geheim | Default in Compose | Omgeving | Beschrijving |
|---|---|---:|---:|---|---|---|
| `NEO4J_AUTH` | Neo4j-image | Ja | **Ja** | `neo4j/${NEO4J_PASSWORD:-mapit_secure_password_2024}` | **L/S/P** | Neo4j bootstrapcredentials. Configureer indirect via `NEO4J_PASSWORD`. |
| `NEO4J_PLUGINS` | Neo4j-image | Nee | Nee | `["apoc", "graph-data-science"]` | Meestal gelijk | Te installeren Neo4j-plugins. |
| `NEO4J_dbms_security_procedures_unrestricted` | Neo4j-image | Nee | Nee | `apoc.*,gds.*` | S/P review | Procedures met onbeperkte rechten. Beperk waar mogelijk. |
| `NEO4J_dbms_security_procedures_allowlist` | Neo4j-image | Nee | Nee | `apoc.*,gds.*` | S/P review | Allowlist voor APOC/GDS-procedures. |
| `NEO4J_dbms_memory_heap_initial__size` | Neo4j-image | Nee | Nee | `512m` | Capaciteitsafhankelijk | Initiële Java heap. |
| `NEO4J_dbms_memory_heap_max__size` | Neo4j-image | Nee | Nee | `2G` | Capaciteitsafhankelijk | Maximale Java heap. |
| `NEO4J_dbms_memory_pagecache_size` | Neo4j-image | Nee | Nee | `512m` | Capaciteitsafhankelijk | Neo4j page cache. |
| `POSTGRES_USER` | Optionele, uitgecommentarieerde PostgreSQL-service | Conditioneel | Nee | `postgres` | **L/S/P** | Alleen relevant wanneer de fallbackservice in Compose wordt ingeschakeld. |
| `POSTGRES_PASSWORD` | Optionele, uitgecommentarieerde PostgreSQL-service | Conditioneel | **Ja** | voorbeeld: `postgres_secure_password` | **L/S/P** | Bootstrapwachtwoord; vervang de voorbeeldwaarde buiten local. |
| `POSTGRES_DB` | Optionele, uitgecommentarieerde PostgreSQL-service | Conditioneel | Nee | `postgres` | L/S/P mogelijk | Databasenaam van de optionele fallbackservice. |

## Bekende configuratieverschillen en aandachtspunten

1. `DATABASE_URL` en `PRIVATE_DATABASE_URL` hebben verschillende frontendconsumers; zet beide voor Drizzle plus runtime.
2. `PUBLIC_SUPABASE_SERVICE_KEY` is een onveilige, ongebruikte voorbeeldvariabele. Zet hier nooit een echte service-role key in.
3. `VECTOR_SEARCH_ENABLED` is standaard `false` in `Settings`, maar `true` in `.env.example` en Docker Compose.
4. `EMBEDDING_MODEL` is `models/gemini-embedding-001` in code/Compose en `gemini-embedding-001` in `.env.example`.
5. De proposal-sessionpool gebruikt directe fallbacks `2/10`, terwijl centrale Settings en `.env.example` `5/50` gebruiken.
6. `GEMINI_MODEL` heeft in `comprehensive_reviewer.py` een oudere zelfstandige fallback (`gemini-2.0-flash-exp`).
7. `REDIS_HOST=redis` werkt in Compose; voor een lokaal proces buiten Docker gebruikt de codefallback `localhost`.
8. Er bestaan vier test-URL-namen. Nieuwe tests horen bij voorkeur `TEST_API_URL` te gebruiken, maar bestaande aliases blijven hierboven gedocumenteerd.

## Secretbeleid

- Commit nooit echte waarden voor database-DSN's, JWT, service-role keys, providerkeys of wachtwoorden.
- Gebruik unieke secrets per omgeving en roteer production-secrets na overdracht.
- Behandel URLs met embedded credentials als geheim, ook als de variabelenaam geen `KEY` of `PASSWORD` bevat.
- Alles met `PUBLIC_` of `VITE_` kan in browsercode terechtkomen; plaats daar uitsluitend bewust publieke configuratie in.
