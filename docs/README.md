# MAPIT documentation index

**Last updated:** 20 July 2026

**Scope:** project-wide handover documents, backend documentation, and relevant frontend documentation

Always start with [START_HERE.md](../../START_HERE.md). It is the current full-stack entry point and
links to the canonical documents for setup, API, data, security, deployment, and operations.

> **Readiness:** “Current” means that a document is the current, verified entry point; it
> does not mean that MAPIT is production-ready. The current release conclusion is **not production-ready**.
> See [KNOWN_ISSUES_AND_RISKS.md](../../KNOWN_ISSUES_AND_RISKS.md).

## Current

These documents are used as the current source. Where a document has a limited scope or known
gaps, this is stated in the status column.

| Document | Type | Brief description | Status |
|---|---|---|---|
| [START_HERE.md](../../START_HERE.md) | Onboarding | Full-stack startup sequence, ports, data blockers, and smoke tests. | Canonical; verified 20-07-2026 |
| [HANDOVER_SUMMARY.md](../../HANDOVER_SUMMARY.md) | Business handover | Concise management summary of status, risks, and next steps. | Current |
| [KNOWN_ISSUES_AND_RISKS.md](../../KNOWN_ISSUES_AND_RISKS.md) | Risk register | Central quality baseline, known issues, workarounds, and limits. | Canonical; owners still largely `TBD` |
| [API_CONTRACT.md](../../API_CONTRACT.md) | API contract | V3/V4 routes, SSE events, frontend proxies, identity, and errors. | Canonical code snapshot |
| [SECURITY_REGISTER.md](../../SECURITY_REGISTER.md) | Security | Trust boundaries, findings, and release checklist. | Canonical register; fixes remain open |
| [DEPLOYMENT_RUNBOOK.md](../../DEPLOYMENT_RUNBOOK.md) | Runbook | Supported VPS deployment path, checks, and rollback. | Canonical path; production not validated |
| [OPERATIONS_RUNBOOK.md](../../OPERATIONS_RUNBOOK.md) | Runbook | Health, logging, alerts, backup/recovery, and incident response. | Procedurally current; setup partly proposed |
| [DEPENDENCY_MATRIX.md](../../DEPENDENCY_MATRIX.md) | Reference | Runtime, infrastructure, package, and LLM versions plus upgrade considerations. | Current |
| [ENVIRONMENT_MATRIX.md](ENVIRONMENT_MATRIX.md) | Reference | Backend and frontend variables, secrets, defaults, and environment differences. | Current |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Data architecture | PostgreSQL/pgvector/Neo4j snapshot, drift, RLS, and migrations. | Verified snapshot; no migration authority |
| [DATA_INGESTION.md](guides/DATA_INGESTION.md) | Runbook | Actual ingestion scripts, data sources, defaults, and reproducibility limits. | Current with explicit data blockers |
| [TOOL_REFERENCE.md](guides/TOOL_REFERENCE.md) | Reference | All registered agent tools, parameters, categories, and data stores. | Generated/checked against registry |
| [DEVELOPER_SETUP.md](../docs_tracked/DEVELOPER_SETUP.md) | Backend onboarding | Backend venv, Make targets, Compose, and test commands. | Current; full-stack setup remains in `START_HERE` |
| [SYSTEM_ARCHITECTURE.md](../docs_tracked/SYSTEM_ARCHITECTURE.md) | Architecture | Extensive V3/V4 backend architecture and services. | Current basis; auth/frontend/deployment details follow canonical root docs |
| [CONVERSATION_STABILITY_ARCHITECTURE.md](../docs_tracked/CONVERSATION_STABILITY_ARCHITECTURE.md) | Technical design | Locks, storage, and stability/test design for conversations. | Current design; do not use run commands as release evidence |
| [MIGRATION_LEDGER.md](../migration/MIGRATION_LEDGER.md) | Migration register | SQL files, checksums, dependencies, and safe decision path. | Current snapshot; applied status partly unknown |
| [Backend tests](../tests/README.md) | Test guide | Collection, external services, and temporary CI policy. | Current |
| [Frontend check baseline](../../webapp-ui/CHECK_ISSUES.md) | Test baseline | Categorization of the 64 frontend errors and 76 warnings. | Current snapshot; errors unresolved |
| [Frontend README](../../webapp-ui/README.md) | Overview | Frontend purpose, stack, and general setup. | Limited current; use `START_HERE` for setup |

## Historical/PRD

These documents remain available for context, traceability, test ideas, or product planning.
Do **not use them as the current technical specification**; if they conflict, the Current documents
and the code take precedence.

| Document | Type | Brief description | Status |
|---|---|---|---|
| [DOCUMENTATION_REVIEW.md](../../DOCUMENTATION_REVIEW.md) | Review baseline | Baseline measurement with 37/100 readiness score and original P0/P1 actions. | Historical baseline before Waves 1–3 |
| [DOCUMENTATION_PROGRESS_LOG.md](../../DOCUMENTATION_PROGRESS_LOG.md) | Changelog | Execution and verification of Wave 1. | Historical evidence |
| [WAVE2_PROGRESS_LOG.md](../../WAVE2_PROGRESS_LOG.md) | Changelog | CI, test, and migration work from Wave 2. | Historical evidence |
| [WAVE3_PROGRESS_LOG.md](../../WAVE3_PROGRESS_LOG.md) | Changelog | Execution and verification of this P1 documentation wave. | Historical evidence after completion |
| [Backend README](../README.md) | Project overview | General capabilities and backend quickstart. | Legacy overview; do not use production-grade claim as release evidence |
| [CLAUDE.md](../CLAUDE.md) | AI/developer context | Commands, architecture, and development patterns. | Supporting; canonical docs take precedence |
| [GEMINI.md](../GEMINI.md) | AI agent context | Alternative agent instructions and project context. | Overlapping/legacy |
| [questions.md](../questions.md) | Question catalog | Examples of complex user questions. | Historical input catalog |
| [ROADMAP.md](guides/ROADMAP.md) | Roadmap | Old implementation and production view. | Outdated; “production-ready” is incorrect |
| [Advanced conversation flows PRD](prd/MAPIT_ADVANCED_CONVERSATION_FLOWS_PRD.md) | PRD | Desired advanced conversation scenarios. | Open/historical plan |
| [Application quality improvement PRD](prd/MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md) | PRD | Desired quality improvements, based on 34 tools. | Outdated plan |
| [Conversation stability PRD](prd/MAPIT_CONVERSATION_STABILITY_PRD.md) | PRD | Stability requirements and scenario approach. | Historical plan; no delivery evidence |
| [Multi-programme excellence PRD](prd/MAPIT_MULTI_PROGRAMME_EXCELLENCE_PRD.md) | PRD | Desired equivalent program coverage. | Open plan; do not use as capability evidence |
| [Production quality validation V3](prd/MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V3.md) | PRD | Validation method and fix rounds. | Historical plan; current results are elsewhere |
| [Quality PRD](prd/MAPIT_QUALITY_PRD.md) | Evaluation/PRD | LLM-as-judge prompts and earlier evaluation claims. | Historical evaluation snapshot |
| [V3 response formatter PRD](prd/MAPIT_V3_RESPONSE_FORMATTER_PRD.md) | PRD | Desired formatter coverage, based on 34 tools. | Outdated/open plan |
| [Enhanced Horizon capabilities](../docs_tracked/ENHANCED_HORIZON_QUESTIONS_CAPABILITIES.md) | Delivery note | Examples of claimed Horizon question coverage. | Historical; metrics not traceable |
| [EU programme data downloads](../docs_tracked/EU_PROGRAMME_DATA_DOWNLOADS.md) | Source list | Possible official data sources and download steps. | Legacy source list; no provenance manifest |
| [Frontend integration prompt](../docs_tracked/FRONTEND_INTEGRATION_PROMPT.md) | Integration design | Old frontend integration proposal for 20 tools. | Outdated; use `API_CONTRACT.md` |
| [Improvement roadmap](../docs_tracked/IMPROVEMENT_ROADMAP.md) | Roadmap | Roadmap status from December 2025. | Historical planning |
| [Manual test scenarios](../docs_tracked/MANUAL_TEST_SCENARIOS.md) | Test catalog | Manual questions and expected outcomes. | Historical; not fully executable |
| [Proposal writer frontend integration](../docs_tracked/PROPOSAL_WRITER_FRONTEND_INTEGRATION.md) | Integration design | Extensive V4 proposal UI design. | Reference context; current routes in `API_CONTRACT.md` |
| [Question categories](../docs_tracked/QUESTION_CATEGORIES.md) | Capability matrix | Question types and old 20-tool/768-dimension architecture. | Outdated |
| [Example questions](../docs_tracked/example_questions.md) | Question catalog | Broad collection of example questions. | Historical input catalog |
| [Kubernetes README](../k8s/README.md) | Deployment design | K8s manifests with Celery and metrics assumptions. | Unsupported; use VPS runbook |
| [Final verification summary](../tests/quality/results/FINAL_VERIFICATION_SUMMARY.md) | Test report | Final 42-scenario run with 54.8% pass rate. | Leading historical quality snapshot |
| [Production readiness summary](../tests/quality/results/PRODUCTION_READINESS_SUMMARY.md) | Test report | Earlier 41-scenario run with 61.0% pass rate. | Older snapshot |
| [Advanced scenarios README](../tests/scenarios/advanced/README.md) | Test design | YAML scenario format and validation types. | Supporting; commands require live services |
| [Frontend deployment guide](../../webapp-ui/DEPLOYMENT_GUIDE.md) | Deployment guide | Old frontend/VPS deployment path. | Superseded by root runbook |
| [Frontend troubleshooting](../../webapp-ui/TROUBLESHOOTING.md) | Troubleshooting | Separate historical diagnostic and recovery steps. | Legacy; validate before use |
| [CRUSH.md](../../webapp-ui/CRUSH.md) | Developer context | Frontend development notes and commands. | Legacy; contained outdated test claims |
| [Proposal writer frontend guide](../../webapp-ui/AI_Proposal_Writer_Frontend_Integration_Guide.md) | Integration design | Frontend copy of proposal integration instructions. | Overlapping; current routes in `API_CONTRACT.md` |
| [Proposal editor report](../../webapp-ui/proposal_editor_report.md) | Implementation snapshot | Time-bound progress report for the editor. | Historical snapshot |
| [Citation verification](../../webapp-ui/docs/CITATION_IMPLEMENTATION_VERIFICATION.md) | Test plan | Verification points for citations. | Open/historical test plan |
| [Proposal editor implementation](../../webapp-ui/docs/PROPOSAL_EDITOR_IMPLEMENTATION.md) | Implementation note | Editor components and integration status. | Historical; validate against code |
| [Rate limiting](../../webapp-ui/docs/RATE_LIMITING.md) | Security design | Intended limiter configuration. | Outdated; global limiter is disabled |
| [Supabase local realtime setup](../../webapp-ui/docs/SUPABASE_LOCAL_REALTIME_SETUP.md) | Setup guide | Local realtime setup. | Additional legacy guide; `START_HERE` takes precedence |
| [Supabase realtime setup](../../webapp-ui/docs/SUPABASE_REALTIME_SETUP.md) | Setup/security guide | Realtime and RLS proposals. | Do not use as validated RLS baseline |
| [project_docs.md](../../webapp-ui/docs/project_docs.md) | WIP | Brief, incomplete project documentation. | Stub; do not use as spec |
| [Supabase CLI how-to](../../webapp-ui/supabase_cli/how_to_run.md) | Setup note | Separate Supabase CLI startup instructions. | Supplemental; canonical startup sequence in `START_HERE` |

## Archived

These files have an archive banner at the top with a reason and a link to the current
starting point. They remain only for historical traceability.

| Document | Type | Brief description | Status |
|---|---|---|---|
| [Production quality validation PRD](prd/MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD.md) | PRD | Old validation plan, superseded by V3 and quality reports. | Archived 20-07-2026 |
| [Stability PRD](prd/MAPIT_STABILITY_PRD.md) | PRD | Older, unchecked duplicate PRD. | Archived 20-07-2026 |
| [Frontend streaming V3 spec](../docs_tracked/FRONTEND_STREAMING_V3_SPEC.md) | API spec | Treats removed V2 as current and V3 as pending. | Archived 20-07-2026 |
| [Celery README](../docs_tracked/README_CELERY.md) | Infrastructure design | Describes a nonexistent Celery stack. | Archived 20-07-2026 |
| [Frontend session summary](../../webapp-ui/SESSION_SUMMARY.md) | Session note | Time-bound incident/deployment session. | Archived 20-07-2026 |
| [Conversational AI architecture](../../webapp-ui/docs/CONVERSATIONAL_AI_ARCHITECTURE.md) | Architecture proposal | Pre-V3 architecture with outdated services/routes. | Archived 20-07-2026 |
| [Conversation implementation guide](../../webapp-ui/docs/CONVERSATION_IMPLEMENTATION_GUIDE.md) | Implementation guide | Refers to missing backend files and old routes. | Archived 20-07-2026 |
| [Legacy project setup](../../webapp-ui/docs/project_setup.md) | Setup guide | Outdated and potentially destructive manual setup. | Archived 20-07-2026 |

## Maintenance rules

1. For technical changes, update the relevant Current document first.
2. Give new plans the type PRD/proposal; do not present checklists as delivery evidence.
3. Move a superseded document to Archived with date, reason, and link to its successor.
4. Check links, commands, routes, counts, and environment variables against code/config.
5. Update the risk register, dependency/environment matrix, and status date with every release.
