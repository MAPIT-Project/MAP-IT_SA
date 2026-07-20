# MAPIT-documentatie-index

**Laatst bijgewerkt:** 20 juli 2026

**Scope:** projectbrede overdrachtsdocumenten, backenddocumentatie en relevante frontenddocumentatie

Begin altijd bij [START_HERE.md](../../START_HERE.md). Dat is het actuele full-stackinstappunt en
verwijst naar de canonieke documenten voor setup, API, data, beveiliging, deployment en beheer.

> **Readiness:** “Current” betekent dat een document de huidige, geverifieerde ingang is; het
> betekent niet dat MAPIT productierijp is. De actuele releaseconclusie is **niet productierijp**.
> Zie [KNOWN_ISSUES_AND_RISKS.md](../../KNOWN_ISSUES_AND_RISKS.md).

## Current

Deze documenten worden als actuele bron gebruikt. Waar een document een beperkte scope of bekende
hiaten heeft, staat dat in de statuskolom.

| Document | Type | Korte beschrijving | Status |
|---|---|---|---|
| [START_HERE.md](../../START_HERE.md) | Onboarding | Full-stack startvolgorde, poorten, data-blockers en smoke tests. | Canoniek; geverifieerd 20-07-2026 |
| [HANDOVER_SUMMARY.md](../../HANDOVER_SUMMARY.md) | Zakelijke overdracht | Beknopte managementsamenvatting van status, risico's en vervolgstappen. | Current |
| [KNOWN_ISSUES_AND_RISKS.md](../../KNOWN_ISSUES_AND_RISKS.md) | Risicoregister | Centrale quality baseline, bekende problemen, workarounds en limits. | Canoniek; owners nog grotendeels `TBD` |
| [API_CONTRACT.md](../../API_CONTRACT.md) | API-contract | V3/V4-routes, SSE-events, frontendproxies, identity en fouten. | Canonieke code-snapshot |
| [SECURITY_REGISTER.md](../../SECURITY_REGISTER.md) | Security | Trust boundaries, bevindingen en releasechecklist. | Canoniek register; fixes blijven open |
| [DEPLOYMENT_RUNBOOK.md](../../DEPLOYMENT_RUNBOOK.md) | Runbook | Ondersteund VPS-deploymentpad, controles en rollback. | Canoniek pad; productie niet gevalideerd |
| [OPERATIONS_RUNBOOK.md](../../OPERATIONS_RUNBOOK.md) | Runbook | Health, logging, alerts, back-up/herstel en incidentrespons. | Procedureel current; inrichting deels voorgesteld |
| [DEPENDENCY_MATRIX.md](../../DEPENDENCY_MATRIX.md) | Referentie | Runtime-, infra-, package- en LLM-versies plus upgradepunten. | Current |
| [ENVIRONMENT_MATRIX.md](ENVIRONMENT_MATRIX.md) | Referentie | Backend- en frontendvariabelen, secrets, defaults en omgevingsverschillen. | Current |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Data-architectuur | PostgreSQL/pgvector/Neo4j-snapshot, drift, RLS en migraties. | Geverifieerde snapshot; geen migration authority |
| [DATA_INGESTION.md](guides/DATA_INGESTION.md) | Runbook | Werkelijke ingestscripts, databronnen, defaults en reproduceerbaarheidsgrenzen. | Current met expliciete data-blockers |
| [TOOL_REFERENCE.md](guides/TOOL_REFERENCE.md) | Referentie | Alle geregistreerde agenttools, parameters, categorieën en datastores. | Gegenereerd/gecontroleerd tegen registry |
| [DEVELOPER_SETUP.md](../docs_tracked/DEVELOPER_SETUP.md) | Backend-onboarding | Backend-venv, Make-targets, Compose en testcommando's. | Current; full-stacksetup blijft in `START_HERE` |
| [SYSTEM_ARCHITECTURE.md](../docs_tracked/SYSTEM_ARCHITECTURE.md) | Architectuur | Uitgebreide V3/V4-backendarchitectuur en services. | Current basis; auth/frontend/deploydetails volgen canonical rootdocs |
| [CONVERSATION_STABILITY_ARCHITECTURE.md](../docs_tracked/CONVERSATION_STABILITY_ARCHITECTURE.md) | Technisch ontwerp | Locks, opslag en stabiliteits-/testontwerp voor gesprekken. | Current ontwerp; runcommands niet als releasebewijs gebruiken |
| [MIGRATION_LEDGER.md](../migration/MIGRATION_LEDGER.md) | Migratieregister | SQL-bestanden, checksums, afhankelijkheden en veilige beslisroute. | Current snapshot; applied-status deels onbekend |
| [Backend tests](../tests/README.md) | Testhandleiding | Collectie, externe services en tijdelijke CI-policy. | Current |
| [Frontend check baseline](../../webapp-ui/CHECK_ISSUES.md) | Testbaseline | Categorisering van de 64 frontenderrors en 76 waarschuwingen. | Current snapshot; fouten niet opgelost |
| [Frontend README](../../webapp-ui/README.md) | Overzicht | Frontenddoel, stack en globale setup. | Beperkt current; gebruik `START_HERE` voor setup |

## Historical/PRD

Deze documenten blijven beschikbaar voor context, traceability, testideeën of productplanning.
Gebruik ze **niet als actuele technische specificatie**; bij tegenspraak gaan de Current-documenten
en de code voor.

| Document | Type | Korte beschrijving | Status |
|---|---|---|---|
| [DOCUMENTATION_REVIEW.md](../../DOCUMENTATION_REVIEW.md) | Reviewbaseline | Nulmeting met 37/100 readinessscore en oorspronkelijke P0/P1-acties. | Historische nulmeting vóór Waves 1–3 |
| [DOCUMENTATION_PROGRESS_LOG.md](../../DOCUMENTATION_PROGRESS_LOG.md) | Changelog | Uitvoering en verificatie van Wave 1. | Historisch bewijs |
| [WAVE2_PROGRESS_LOG.md](../../WAVE2_PROGRESS_LOG.md) | Changelog | CI-, test- en migratiewerk uit Wave 2. | Historisch bewijs |
| [WAVE3_PROGRESS_LOG.md](../../WAVE3_PROGRESS_LOG.md) | Changelog | Uitvoering en verificatie van deze P1-documentatiewave. | Historisch bewijs na afronding |
| [Backend README](../README.md) | Projectoverzicht | Globale capabilities en backendquickstart. | Legacy-overzicht; production-gradeclaim niet als releasebewijs gebruiken |
| [CLAUDE.md](../CLAUDE.md) | AI-/developercontext | Commando's, architectuur en ontwikkelpatronen. | Ondersteunend; canonical docs gaan voor |
| [GEMINI.md](../GEMINI.md) | AI-agentcontext | Alternatieve agentinstructies en projectcontext. | Overlappend/legacy |
| [questions.md](../questions.md) | Vraagcatalogus | Voorbeelden van complexe gebruikersvragen. | Historische inputcatalogus |
| [ROADMAP.md](guides/ROADMAP.md) | Roadmap | Oud implementatie- en productiebeeld. | Verouderd; “production-ready” is onjuist |
| [Advanced conversation flows PRD](prd/MAPIT_ADVANCED_CONVERSATION_FLOWS_PRD.md) | PRD | Gewenste geavanceerde gespreksscenario's. | Open/historisch plan |
| [Application quality improvement PRD](prd/MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md) | PRD | Gewenste kwaliteitsverbeteringen, gebaseerd op 34 tools. | Verouderd plan |
| [Conversation stability PRD](prd/MAPIT_CONVERSATION_STABILITY_PRD.md) | PRD | Stabiliteitsrequirements en scenario-aanpak. | Historisch plan; geen opleverbewijs |
| [Multi-programme excellence PRD](prd/MAPIT_MULTI_PROGRAMME_EXCELLENCE_PRD.md) | PRD | Gewenste gelijkwaardige programmadekking. | Open plan; niet als capabilitybewijs gebruiken |
| [Production quality validation V3](prd/MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V3.md) | PRD | Validatiemethode en fixrondes. | Historisch plan; actuele resultaten staan elders |
| [Quality PRD](prd/MAPIT_QUALITY_PRD.md) | Evaluatie/PRD | LLM-as-judge-prompts en eerdere evaluatieclaims. | Historische evaluatiesnapshot |
| [V3 response formatter PRD](prd/MAPIT_V3_RESPONSE_FORMATTER_PRD.md) | PRD | Gewenste formatterdekking, gebaseerd op 34 tools. | Verouderd/open plan |
| [Enhanced Horizon capabilities](../docs_tracked/ENHANCED_HORIZON_QUESTIONS_CAPABILITIES.md) | Oplevernotitie | Voorbeelden van geclaimde Horizon-vraagdekking. | Historisch; metrics niet herleidbaar |
| [EU programme data downloads](../docs_tracked/EU_PROGRAMME_DATA_DOWNLOADS.md) | Bronlijst | Mogelijke officiële databronnen en downloadstappen. | Legacy bronlijst; geen provenance manifest |
| [Frontend integration prompt](../docs_tracked/FRONTEND_INTEGRATION_PROMPT.md) | Integratieontwerp | Oud frontendintegratievoorstel voor 20 tools. | Verouderd; gebruik `API_CONTRACT.md` |
| [Improvement roadmap](../docs_tracked/IMPROVEMENT_ROADMAP.md) | Roadmap | Roadmapstatus van december 2025. | Historische planning |
| [Manual test scenarios](../docs_tracked/MANUAL_TEST_SCENARIOS.md) | Testcatalogus | Handmatige vragen en verwachte uitkomsten. | Historisch; niet volledig executable |
| [Proposal writer frontend integration](../docs_tracked/PROPOSAL_WRITER_FRONTEND_INTEGRATION.md) | Integratieontwerp | Uitgebreid V4 proposal-UI-ontwerp. | Referentiecontext; actuele routes in `API_CONTRACT.md` |
| [Question categories](../docs_tracked/QUESTION_CATEGORIES.md) | Capabilitymatrix | Vraagtypen en oude 20-tool/768-dimensiearchitectuur. | Verouderd |
| [Example questions](../docs_tracked/example_questions.md) | Vraagcatalogus | Brede verzameling voorbeeldvragen. | Historische inputcatalogus |
| [Kubernetes README](../k8s/README.md) | Deploymentontwerp | K8s-manifests met Celery- en metricsaannames. | Niet ondersteund; gebruik VPS-runbook |
| [Final verification summary](../tests/quality/results/FINAL_VERIFICATION_SUMMARY.md) | Testrapport | Finale 42-scenariorun met 54,8% passrate. | Leidende historische quality snapshot |
| [Production readiness summary](../tests/quality/results/PRODUCTION_READINESS_SUMMARY.md) | Testrapport | Eerdere 41-scenariorun met 61,0% passrate. | Oudere snapshot |
| [Advanced scenarios README](../tests/scenarios/advanced/README.md) | Testontwerp | YAML-scenarioformaat en validation types. | Ondersteunend; commando's vereisen live services |
| [Frontend deployment guide](../../webapp-ui/DEPLOYMENT_GUIDE.md) | Deploymentguide | Oud frontend/VPS-deploymentpad. | Superseded door root-runbook |
| [Frontend troubleshooting](../../webapp-ui/TROUBLESHOOTING.md) | Probleemoplossing | Losse historische diagnose- en herstelstappen. | Legacy; valideer vóór gebruik |
| [CRUSH.md](../../webapp-ui/CRUSH.md) | Developercontext | Frontendontwikkelnotities en commando's. | Legacy; bevatte verouderde testclaims |
| [Proposal writer frontend guide](../../webapp-ui/AI_Proposal_Writer_Frontend_Integration_Guide.md) | Integratieontwerp | Frontendkopie van proposal-integratie-instructies. | Overlappend; actuele routes in `API_CONTRACT.md` |
| [Proposal editor report](../../webapp-ui/proposal_editor_report.md) | Implementatiesnapshot | Tijdgebonden voortgangsrapport van de editor. | Historische snapshot |
| [Citation verification](../../webapp-ui/docs/CITATION_IMPLEMENTATION_VERIFICATION.md) | Testplan | Verificatiepunten voor citations. | Open/historisch testplan |
| [Proposal editor implementation](../../webapp-ui/docs/PROPOSAL_EDITOR_IMPLEMENTATION.md) | Implementatienotitie | Editorcomponenten en integratiestatus. | Historisch; tegen code valideren |
| [Rate limiting](../../webapp-ui/docs/RATE_LIMITING.md) | Securityontwerp | Beoogde limiterconfiguratie. | Verouderd; globale limiter staat uit |
| [Supabase local realtime setup](../../webapp-ui/docs/SUPABASE_LOCAL_REALTIME_SETUP.md) | Setupguide | Lokale realtime-inrichting. | Aanvullende legacyguide; `START_HERE` gaat voor |
| [Supabase realtime setup](../../webapp-ui/docs/SUPABASE_REALTIME_SETUP.md) | Setup/securityguide | Realtime en RLS-voorstellen. | Niet als gevalideerde RLS-baseline gebruiken |
| [project_docs.md](../../webapp-ui/docs/project_docs.md) | WIP | Korte, onvoltooide projectdocumentatie. | Stub; niet gebruiken als spec |
| [Supabase CLI how-to](../../webapp-ui/supabase_cli/how_to_run.md) | Setupnotitie | Losse Supabase CLI-startinstructies. | Aanvullend; canonical startvolgorde in `START_HERE` |

## Archived

Deze bestanden hebben bovenaan een archiveerbanner met reden en een link naar het actuele
startpunt. Ze blijven alleen bestaan voor historische traceability.

| Document | Type | Korte beschrijving | Status |
|---|---|---|---|
| [Production quality validation PRD](prd/MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD.md) | PRD | Oud validatieplan, opgevolgd door V3 en quality reports. | Archived 20-07-2026 |
| [Stability PRD](prd/MAPIT_STABILITY_PRD.md) | PRD | Oudere, onafgevinkte duplicaat-PRD. | Archived 20-07-2026 |
| [Frontend streaming V3 spec](../docs_tracked/FRONTEND_STREAMING_V3_SPEC.md) | API-spec | Behandelt verwijderde V2 als current en V3 als pending. | Archived 20-07-2026 |
| [Celery README](../docs_tracked/README_CELERY.md) | Infrastructuurontwerp | Beschrijft een niet-aanwezige Celery-stack. | Archived 20-07-2026 |
| [Frontend session summary](../../webapp-ui/SESSION_SUMMARY.md) | Sessienotitie | Tijdgebonden incident-/deploymentsessie. | Archived 20-07-2026 |
| [Conversational AI architecture](../../webapp-ui/docs/CONVERSATIONAL_AI_ARCHITECTURE.md) | Architectuurvoorstel | Pre-V3-architectuur met niet-actuele services/routes. | Archived 20-07-2026 |
| [Conversation implementation guide](../../webapp-ui/docs/CONVERSATION_IMPLEMENTATION_GUIDE.md) | Implementatieguide | Verwijst naar ontbrekende backendbestanden en oude routes. | Archived 20-07-2026 |
| [Legacy project setup](../../webapp-ui/docs/project_setup.md) | Setupguide | Verouderde en potentieel destructieve handmatige setup. | Archived 20-07-2026 |

## Onderhoudsregels

1. Werk bij technische wijzigingen eerst het relevante Current-document bij.
2. Geef nieuwe plannen het type PRD/proposal; presenteer checklists niet als opleverbewijs.
3. Verplaats een vervangen document naar Archived met datum, reden en link naar de opvolger.
4. Controleer links, commando's, routes, aantallen en environmentvariabelen tegen code/config.
5. Werk bij iedere release het risicoregister, de dependency-/environmentmatrix en de statusdatum bij.
