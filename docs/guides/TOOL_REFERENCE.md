# MAP-IT SA toolreferentie

Deze referentie beschrijft de **42 tools die daadwerkelijk worden geregistreerd** door `ToolRegistryMixin._init_tools()` en worden gerouteerd door `_execute_single_tool()`. De parameterdefaults hieronder komen uit de executorlaag; die bepaalt het runtimegedrag. De zes documentatiecategorieën zijn bewust eenvoudiger dan de interne enum: interne `programmes`-tools staan hier onder **Call**, terwijl `calculate_budget` en `generate_timeline` vanwege hun functie onder **Proposal support** staan.

Laatst geverifieerd: 20 juli 2026.

## Samenvatting

| Categorie | Aantal | Tools |
|---|---:|---|
| Statistics | 7 | `get_programme_statistics`, `get_country_statistics`, `get_budget_benchmark`, `get_consortium_patterns`, `analyze_geographic_diversification`, `analyze_call_history`, `get_organization_stats` |
| Comparison | 1 | `compare_programmes` |
| Document | 5 | `search_documents`, `search_erasmus_templates`, `search_creative_europe_templates`, `search_eu4health_templates`, `search_life_templates` |
| Call | 10 | `search_funding_calls`, `get_call_details`, `search_all_programmes`, `recommend_programmes`, `get_programme_info`, `check_erasmus_eligibility`, `check_creative_europe_eligibility`, `check_eu4health_eligibility`, `check_digital_europe_eligibility`, `check_life_eligibility` |
| Project | 11 | `find_experienced_partners`, `get_similar_funded_projects`, `search_projects`, `get_project_details`, `find_similar_projects`, `find_semantically_similar_projects`, `find_organization_projects`, `get_project_partners`, `get_collaboration_network`, `search_by_cluster`, `show_cached_projects` |
| Proposal support | 8 | `calculate_budget`, `generate_timeline`, `score_proposal_section`, `score_full_proposal`, `quick_quality_check`, `validate_budget`, `calculate_erasmus_budget`, `calculate_creative_europe_budget` |
| **Totaal** | **42** | |

## Leeswijzer

- `vereist` betekent dat de tool zonder een inhoudelijke waarde niet zinvol kan uitvoeren, ook als de executor technisch `""` of `0` invult.
- `null` betekent Python `None`: geen filter of geen opgegeven waarde.
- “Geaccepteerd” duidt op een parameter die de executor wel verwerkt maar die niet in de registrybeschrijving staat.
- “Genegeerd” duidt op een parameter die wel in de registry staat maar niet aan de implementatie wordt doorgegeven.
- **PostgreSQL** is de relationele applicatiedatabase. **pgvector** is vectoropslag/-similarity binnen PostgreSQL/Supabase. **Neo4j** is de graph datastore. **Externe API** betekent Google embeddings/Gemini, OpenAI of het EU Funding & Tenders Portal, zoals per rij vermeld.
- “Ingebouwde regels” zijn versiegebonden tabellen/heuristieken in Python en geen live datastore.

## Statistics

| Tool | Inputparameters (type en runtime-default) | Wat doet de tool? | Datastore(s) |
|---|---|---|---|
| `get_programme_statistics` | `programme: str` (vereist)<br>`metric: str \| null = null` (**genegeerd**) | Geeft programma- of clusterstatistieken. EIC, ERC en MSCA komen uit ingebouwde referentiewaarden; Pillar 2-clusters worden uit de graph gelezen. | Neo4j; ingebouwde EC-referentiewaarden |
| `get_country_statistics` | `country: str` (vereist; naam of ISO-2)<br>`programme: str \| null = null` (**genegeerd**) | Geeft eligibility, toporganisaties en participatie voor één land. Probeert Neo4j eerst en gebruikt PostgreSQL als fallback. | Neo4j; PostgreSQL fallback |
| `get_budget_benchmark` | `cluster: str \| null = null`<br>`action_type: str \| null = null`<br>`topic_keywords: str \| null = null`<br>`year: int \| null = null` | Berekent min/max/gemiddelde/mediaan van bijdragen en context zoals budget per partner op basis van gefinancierde projecten. | PostgreSQL; Neo4j |
| `get_consortium_patterns` | `cluster: str \| null = null`<br>`action_type: str \| null = null`<br>`topic_keywords: str \| null = null`<br>`min_projects: int = 10` (geaccepteerd) | Analyseert consortiumgrootte, organisatietypen, landen en coördinatorprofielen uit historische projecten. | PostgreSQL; Neo4j |
| `analyze_geographic_diversification` | `cluster: str \| null = null`<br>`exclude_widening: bool = true`<br>`min_partners: int = 3`<br>`country_groups: dict[str, list[str]] \| null = null` | Meet per zelfgekozen of standaardregio welk aandeel van consortia ten minste één partner uit die regio bevat. | PostgreSQL; ingebouwde standaard-landengroepen |
| `analyze_call_history` | `topic_pattern: str \| null = null`<br>`cluster: str \| null = null`<br>`keywords: str \| null = null`<br>`year_from: int \| null = null`<br>`year_to: int \| null = null`<br>`action_types: list[str] \| null = null`<br>`include_projects: bool = true`<br>`expand_scope: bool = false`<br>`limit: int = 50` (geaccepteerd) | Analyseert historische calls, financieringstrends en voorbeeldprojecten. Met `expand_scope=true` breidt een LLM de zoektermen uit. | PostgreSQL; Neo4j; Gemini API optioneel voor termuitbreiding |
| `get_organization_stats` | `organization_name: str` (vereist) | Geeft aantallen projecten en coördinaties, totale financiering en actieve clusters voor een organisatie. | Neo4j; PostgreSQL fallback |

## Comparison

| Tool | Inputparameters (type en runtime-default) | Wat doet de tool? | Datastore(s) |
|---|---|---|---|
| `compare_programmes` | `programme_a: str` (vereist)<br>`programme_b: str` (vereist)<br>`metrics: list[str] \| null = null` (**genegeerd**) | Haalt voor twee programma-/clusternamen dezelfde clusterstatistieken op en zet die naast elkaar. De huidige implementatie filtert niet op `metrics`. | Neo4j |

## Document

Alle vijf tools gebruiken `VectorSearchService`: hybride full-text- en vectorzoekacties in Supabase/PostgreSQL met pgvector. Voor een nieuwe queryembedding wordt de Google Embeddings API gebruikt; een fout daarin kan tot een keyword-only/degraded resultaat leiden.

| Tool | Inputparameters (type en runtime-default) | Wat doet de tool? | Datastore(s) |
|---|---|---|---|
| `search_documents` | `query: str` (vereist)<br>`document_type: str \| null = null`<br>`max_results: int = 15` | Zoekt in geïndexeerde officiële EU-documenten en retourneert tekst plus bron-, sectie-, pagina- en chunkmetadata. Let op: de oude registrytekst noemt 5, maar de executor gebruikt 15. | PostgreSQL/Supabase; pgvector; Google Embeddings API |
| `search_erasmus_templates` | `query: str` (vereist)<br>`key_action: str \| null = null`<br>`sector: str \| null = null`<br>`document_type: str \| null = null`<br>`top_k: int = 5` | Zoekt Erasmus+ Programme Guide-fragmenten over onder meer eligibility, budget en kwaliteitscriteria. | PostgreSQL/Supabase; pgvector; Google Embeddings API |
| `search_creative_europe_templates` | `query: str` (vereist)<br>`strand: str \| null = null`<br>`action_type: str \| null = null`<br>`topic: str \| null = null`<br>`top_k: int = 5` | Zoekt Creative Europe-documenten en kan de query beperken tot strand, actie of onderwerp. | PostgreSQL/Supabase; pgvector; Google Embeddings API |
| `search_eu4health_templates` | `query: str` (vereist)<br>`strand: str \| null = null`<br>`action_type: str \| null = null`<br>`topic: str \| null = null`<br>`top_k: int = 5` | Zoekt EU4Health Work Programmes en regelgeving voor toepassings-, eligibility- en programma-informatie. | PostgreSQL/Supabase; pgvector; Google Embeddings API |
| `search_life_templates` | `query: str` (vereist)<br>`subprogramme: str \| null = null`<br>`section: str \| null = null`<br>`top_k: int = 5` | Zoekt LIFE-regelgeving, guidance en Work Programme-fragmenten per subprogramma of sectie. | PostgreSQL/Supabase; pgvector; Google Embeddings API |

`search_digital_europe_templates_execute()` bestaat wel in de codebase, maar wordt **niet geregistreerd of gerouteerd** en behoort daarom niet tot de 42 beschikbare agenttools.

## Call

| Tool | Inputparameters (type en runtime-default) | Wat doet de tool? | Datastore(s) |
|---|---|---|---|
| `search_funding_calls` | `keywords: str \| list[str]` (vereist)<br>`status: str = "open"` (`open`, `upcoming`, `closed`, `all`)<br>`year: int \| str \| null = null`<br>`cluster: str \| null = null` (geaccepteerd) | Zoekt calls eerst gestructureerd, daarna semantisch/graph-based en ten slotte in documentchunks; ontbrekende status/deadline kan via het EU Portal worden verrijkt. | PostgreSQL; Neo4j; pgvector; Google Embeddings API; EU Funding & Tenders Portal API |
| `get_call_details` | `call_id: str` (vereist) | Haalt één call op via lokale data, varianten van het call-ID en uiteindelijk directe Portal-verrijking; kan vergelijkbare calls voorstellen als niets wordt gevonden. | PostgreSQL; pgvector; Google Embeddings API; EU Funding & Tenders Portal API |
| `search_all_programmes` | `keywords: str` (vereist)<br>`programmes: list[str] \| null = null`<br>`status: str \| null = null`<br>`year: int \| null = null`<br>`action_type: str \| null = null` (geaccepteerd)<br>`limit: int = 20` (geaccepteerd; per programma)<br>`include_closed: bool = false` (geaccepteerd) | Zoekt uniform in calls voor Horizon Europe, Erasmus+, Creative Europe, EU4Health, Digital Europe en LIFE. | PostgreSQL |
| `recommend_programmes` | `description: str` (vereist)<br>`organization_type: str \| null = null`<br>`sector: str \| null = null` | Rangschikt passende programma's met keyword- en organisatieregels en voegt beschikbaarheidscontext toe. Dit is geen generatieve AI-aanroep. | Ingebouwde programmacatalogus en regels; PostgreSQL voor callaantallen |
| `get_programme_info` | `programme: str \| null = null` | Geeft informatie en officiële vervolglinks voor één ondersteund programma, of een overzicht van alle programma's. | Ingebouwde programmacatalogus/extractors; PostgreSQL voor callaantallen |
| `check_erasmus_eligibility` | `org_type: str = "HEI"`<br>`country: str = "Germany"`<br>`action_type: str \| null = null`<br>`has_eche: bool = false`<br>`is_coordinator: bool = true` | Toetst Erasmus+-eligibility per organisatie, land, actie en ECHE-status; graphdata kan de vaste regels verrijken. | Ingebouwde regels; Neo4j optioneel |
| `check_creative_europe_eligibility` | `org_type: str = "CULTURAL_ORG"`<br>`country: str = "Germany"`<br>`action_type: str \| null = null`<br>`strand: str \| null = null`<br>`is_coordinator: bool = true` | Toetst eligibility voor CULTURE, MEDIA en CROSS-SECTORAL; graphdata kan de vaste regels verrijken. | Ingebouwde regels; Neo4j optioneel |
| `check_eu4health_eligibility` | `org_type: str = "HEALTHCARE_PROVIDER"`<br>`country: str = "Germany"`<br>`action_type: str \| null = null`<br>`strand: str \| null = null` | Toetst EU4Health-eligibility voor organisatie, land, actietype en strand. | Ingebouwde regels; geen runtime datastore |
| `check_digital_europe_eligibility` | `org_type: str = "SME"`<br>`country: str = "Germany"`<br>`objective: str \| null = null`<br>`action_type: str \| null = null` | Toetst eligibility tegen de Digital Europe-doelstellingen en land-/organisatietyperegels. | Ingebouwde regels; geen runtime datastore |
| `check_life_eligibility` | `org_type: str = "NGO"`<br>`country: str = "Germany"`<br>`subprogramme: str \| null = null`<br>`project_type: str \| null = null` | Toetst eligibility voor LIFE-subprogramma's en projecttypen. | Ingebouwde regels; geen runtime datastore |

## Project

| Tool | Inputparameters (type en runtime-default) | Wat doet de tool? | Datastore(s) |
|---|---|---|---|
| `find_experienced_partners` | `topic_keywords: str` (vereist; `keywords` wordt ook geaccepteerd)<br>`country: str \| null = null`<br>`organization_type: str \| null = null`<br>`cluster: str \| null = null`<br>`min_projects: int = 2`<br>`role_filter: str \| null = null`<br>`limit: int = 20` (geaccepteerd)<br>`programme: str \| null = null` (**genegeerd**) | Vindt organisaties met aantoonbare project-, financierings- en coördinatie-ervaring rond een onderwerp. | PostgreSQL; Neo4j |
| `get_similar_funded_projects` | `description: str` (vereist)<br>`cluster: str \| null = null`<br>`action_type: str \| null = null`<br>`min_budget: float \| null = null`<br>`max_budget: float \| null = null`<br>`year_from: int \| null = null`<br>`limit: int = 100` effectief minimum<br>`similarity_threshold: float = 0.3` (geaccepteerd) | Zoekt semantisch naar gefinancierde projecten op basis van een conceptbeschrijving en verrijkt/rerankt met graphcontext. De executor haalt altijd minimaal 100 kandidaten op, ondanks de registrytekst “default 10”. | PostgreSQL; pgvector; Neo4j; Google Embeddings API |
| `search_projects` | `keywords: str` (vereist)<br>`programme: str \| null = null`<br>`country: str \| null = null`<br>`limit: int = 100` effectief minimum<br>`sort_by: str \| null = null` (`relevance`, `ec_contribution`, `total_cost`, `start_date`) | Doorzoekt lokale CORDIS-projecten met full-text en vector retrieval en graphverrijking. Ook hier verhoogt de executor elke lagere `limit` naar 100 kandidaten. | PostgreSQL; pgvector; Neo4j; Google Embeddings API |
| `get_project_details` | `project_id: str` (vereist; ID of acroniem) | Geeft projectmetadata en volledige partnerlijst; bij een onbekend ID volgt een zoekfallback op acroniem. | PostgreSQL; fallback kan PostgreSQL, pgvector, Neo4j en Google Embeddings API gebruiken |
| `find_similar_projects` | `project_id: str` (vereist)<br>`similarity_type: str = "topic"` (`topic`, `consortium`, `cluster`) | Vindt maximaal tien projecten via relaties met het referentieproject. | Neo4j |
| `find_semantically_similar_projects` | `project_id: str` (vereist)<br>`limit: int = 10` | Vergelijkt de reeds opgeslagen embedding van een referentieproject met andere projectembeddings. | PostgreSQL; pgvector |
| `find_organization_projects` | `organization_name: str` (vereist)<br>`role: str \| null = null` (`coordinator` of `participant`) | Lijst projecten van een organisatie en berekent totaal- en coördinatorcount; maximaal 100 projectregels. | Neo4j |
| `get_project_partners` | `project_id: str` (vereist; ID of acroniem) | Geeft consortiumleden, rollen, landen en bijdragen voor een project. | PostgreSQL; zoekfallback kan PostgreSQL, pgvector, Neo4j en Google Embeddings API gebruiken |
| `get_collaboration_network` | `organization_name: str` (vereist) | Geeft directe samenwerkingspartners van een organisatie, met gedeelde projecten. | Neo4j |
| `search_by_cluster` | `cluster: str` (vereist) | Vindt maximaal vijftien projecten via de clusterrelatie. | Neo4j; PostgreSQL fallback in de onderliggende zoekservice |
| `show_cached_projects` | Geen parameters | Toont de volgende pagina van een eerdere projectzoekopdracht en verhoogt de offset; cache-items verlopen na 30 minuten. | Redis |

## Proposal support

| Tool | Inputparameters (type en runtime-default) | Wat doet de tool? | Datastore(s) |
|---|---|---|---|
| `calculate_budget` | `action_type: str = "RIA"`<br>`duration_months: int = 36`<br>`num_partners: int = 8`<br>`total_person_months: int \| null = null`<br>`target_budget: float \| null = null`<br>`countries: list[str] \| null = null`<br>`include_breakdown: bool = true` (geaccepteerd) | Maakt een Horizon Europe-budgetverdeling met historische benchmarks, landkosten en ingebouwde ratio's. | PostgreSQL; Neo4j; ingebouwde rekenregels |
| `generate_timeline` | `action_type: str = "RIA"`<br>`duration_months: int = 36`<br>`num_partners: int = 8`<br>`total_person_months: int = 300`<br>`project_title: str = "Project"`<br>`start_date: str \| null = null` (`YYYY-MM-DD`)<br>`custom_wps: list[dict] \| null = null` (geaccepteerd) | Genereert work packages, deliverables, milestones, afhankelijkheden en Ganttdata met historische duurpatronen waar beschikbaar. | PostgreSQL; Neo4j; ingebouwde templates |
| `score_proposal_section` | `content: str` (vereist; minimaal 50 tekens)<br>`section_type: str = "excellence"`<br>`section_id: str \| null = null`<br>`action_type: str = "RIA"`<br>`call_id: str \| null = null` (geaccepteerd) | Scoort één voorstelonderdeel op 0–5 met criteriumuitsplitsing, sterke/zwakke punten en verbeteracties; gebruikt lokale heuristiek als AI faalt. | Gemini API primair; OpenAI API optionele fallback; ingebouwde fallbackregels |
| `score_full_proposal` | `excellence_content: str` (vereist)<br>`impact_content: str` (vereist)<br>`implementation_content: str` (vereist)<br>`action_type: str = "RIA"`<br>`call_id: str \| null = null` (geaccepteerd) | Scoort de drie hoofddelen en berekent totaalscore (0–15) en indicatieve financieringskans. | Gemini API primair; OpenAI API optionele fallback; ingebouwde fallbackregels |
| `quick_quality_check` | `text: str` (vereist)<br>`context: str = "general"` | Geeft snelle, deterministische indicatoren voor lengte, structuur, kwantificatie en verbetersuggesties; doet geen LLM-call. | Ingebouwde heuristiek; geen runtime datastore |
| `validate_budget` | `total_cost: float` (vereist; executor fallback `0`)<br>`eu_contribution: float` (vereist; executor fallback `0`)<br>`action_type: str = "RIA"`<br>`duration_months: int = 36`<br>`num_partners: int = 3`<br>`cost_breakdown: dict[str, float] \| null = null`<br>`call_budget_cap: float \| null = null`<br>`consortium: list[dict] \| null = null` (geaccepteerd) | Controleert funding rate, indirecte kosten, kostencategorieën, budgetrange, looptijd en consortiumverdeling. | Ingebouwde validatieregels; geen runtime datastore |
| `calculate_erasmus_budget` | `action_type: str = "partnership"`<br>`num_participants: int = 10`<br>`duration_days: int = 14`<br>`duration_months: int = 24`<br>`num_partners: int = 3`<br>`destination_country: str = "Germany"`<br>`origin_country: str = "Spain"`<br>`partnership_type: str = "cooperation"`<br>`distance_band: str = "500-1999km"`<br>`green_travel: bool = false`<br>`target_budget: float \| null = null` | Berekent Erasmus+-mobiliteits-, partnerschaps-, Jean Monnet- of sportbudgetten uit unit costs en lump sums. | Ingebouwde rekentabellen; geen runtime datastore |
| `calculate_creative_europe_budget` | `action_type: str = "COOP-SMALL"`<br>`requested_amount: float \| null = null`<br>`project_scale: str = "medium"`<br>`num_partners: int = 3`<br>`duration_months: int \| null = null`<br>`strand: str \| null = null` | Berekent subsidieplafond, funding rate en indicatieve verdeling voor Creative Europe-acties. | Ingebouwde rekentabellen; geen runtime datastore |

## Bekende registry/executor-afwijkingen

Deze afwijkingen zijn onderdeel van het huidige codegedrag en zijn daarom niet stilzwijgend “gecorrigeerd” in deze documentatie:

1. `metric` bij `get_programme_statistics`, `programme` bij `get_country_statistics`, `metrics` bij `compare_programmes` en `programme` bij `find_experienced_partners` worden geregistreerd maar door de executor genegeerd.
2. Meerdere executors accepteren extra, niet-geregistreerde filters; die zijn hierboven gemarkeerd als “geaccepteerd”. Een LLM ziet deze niet automatisch in de gegenereerde toolprompt.
3. `search_documents` gebruikt runtime-default 15, niet de 5 uit de registrytekst.
4. `search_projects` en `get_similar_funded_projects` halen effectief minimaal 100 kandidaten op, ook wanneer de registry een default van 10 suggereert.
5. `search_digital_europe_templates_execute()` heeft een implementatie, maar zonder registratie en route is het geen beschikbare tool.

## Bronnen van waarheid

- Registratie, naam, interne categorie en zichtbare parameterbeschrijving: `app/services/agents/tool_registry.py`
- Runtime-routing en effectieve defaults: `app/services/agents/tool_executors.py`
- Gedrag en datastores: `app/services/tools/*.py`, `app/services/local_project_search_service.py`, `app/services/local_call_search_service.py`, `app/services/vector_search_service.py`, `app/services/data/cordis_repository.py`
- Proposal-AI providers: `app/services/proposal_writing/proposal_ai_service.py` en `app/services/proposal_writing/ai_providers/multi_provider_service.py`
