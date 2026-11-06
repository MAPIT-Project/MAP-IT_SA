# Tool scenarios backed by source evidence

The ten question scenarios and their 13 required tool contracts were repaired and
verified with real Codex inference on 2026-11-06. See [the execution report](SCENARIO_VALIDATION_2026-11-06.md)
for results, actual usage and remaining graph/HTTP coverage limits. The optional
embedding profile now runs the real application embedder and existing search RPCs
through read-only SQL. Horizon consortium questions use independently selected
Horizon General Annexes evidence; returned passages, titles and pages are reread
and checked against stored source rows. Other programme anchors remain separate.

The replacement suite separates two questions:

1. Does the registered Python tool return the funding records and calculations
   that independently queried source data says it should return?
2. Does the agent choose suitable tools and carry those facts into its answer?

Direct tool contracts cover all 52 registered tools. A smaller set of agent
questions checks selection and answer grounding. A missing prerequisite is
reported as blocked; it is not an empty-result pass. The runner's model budget
covers direct tools that invoke AI internally as well as agent and helper calls.
It must stop before an inference request exceeds that run-wide allowance.

## Source of truth

`tests/tool_scenarios/oracles.py` contains independent SQL queries. They do not
call MAPIT tool implementations or derive an expectation from a tool's result.
The local PostgreSQL reader uses an argument list and stdin, with a read-only
transaction, ten-second statement timeout, two-second lock timeout, and rollback.
It does not load `.env`, application credentials, authentication files or dumps.
The reader restricts relations to the funding corpus and rejects administrative
functions and private conversation/user/session data.

The source reader preserves SQL column order with `json_agg(row_to_json(...))`.
JSON decimal values retain their exact decimal representation. Embedding values
are never copied into evidence; nearest-neighbour checks compare stored vectors
inside PostgreSQL and return only project identifiers and similarity scores.
Unknown tool query functions/relations are blocked until their read-only purpose
has been reviewed. This limited transport is not a substitute for evaluating a
production PostgreSQL connection or the HTTP API.

Read-only inspection on 2026-11-04 found:

| Source | Observed records |
|---|---:|
| `projects` | 13,865 |
| `organizations` participation rows | 89,348 |
| `funding_calls` | 2,758 |
| `horizon_documents` | 144 |
| `document_chunks` | 38,697 |
| `project_embeddings` with stored vectors | 13,850 |

These are observations, not hardcoded expected totals. Every evaluation captures
fresh source facts and the database date before spending model requests. The
fixed reference identifiers below must exist; an absent anchor is reported
before its scenario starts rather than replaced with whatever a broken tool
happens to find.

## Reference questions and failure conditions

| Family | Example question | Independent evidence and checks |
|---|---|---|
| Project facts and consortium | “What is IMAGHyNE's EU contribution, total cost, coordinator, and consortium size? List its partners.” | Project `101137586`; €19,996,911.75 EU contribution and €200,255,979.99 total cost observed; 42 partners across five countries. Compare current source amounts/counts, coordinator and returned partner rows. Reversed cost/contribution, missing known partners and wrong units fail. |
| Organization portfolio | “How many funded projects does Technische Universitaet Muenchen participate in, and who are its frequent collaborators?” | Exact organization name, distinct project IDs, contribution sum and shared-project counts. The observed portfolio had 219 projects. Compare the current count and named collaborators, not a guessed count or a generic university description. |
| Search filters | “Show me the largest Cluster 5 projects by EU contribution.” | Independently ordered source IDs, topic filter and amounts. Wrong cluster, unsorted amounts and missing known top results fail. |
| Similar projects | “Which projects share IMAGHyNE's topic, and which stored project vectors are nearest?” | Exact shared topic and server-side stored-vector distance. The two similarity modes have different expectations. Keyword fallback must not be presented as a semantic-search pass. |
| Calls and dates | “Is HORIZON-EIC-2026-AIC-01 still open, and what is its budget?” | This source row was labelled open with deadline 2026-02-26. Its effective status on 2026-11-04 is closed. Assert date-based status correction. Unknown budgets remain unknown. |
| Currently open calls | “Which calls can I still apply for?” | Database date, deadline, opening date and source status determine eligibility for inclusion. A source row with a missing budget must not receive an invented amount. |
| Statistics and comparisons | “Compare local Cluster 4 and Cluster 5 project counts and funding; what is Germany's participation?” | Independent counts/sums over projects/participation rows. Distinguish unique projects from organization participations and report which source the tool actually used. |
| Benchmarks and consortium design | “What budgets and consortium sizes are typical for hydrogen projects?” | Independently filtered project count, monetary range/mean/median, distinct organization/country counts, and historical yearly funding. Any hybrid graph/SQL weighting must disclose its source; SQL-only expected values cannot be blindly applied to a different graph population. |
| Geographic coverage | “How well do Cluster 5 consortia cover the defined country groups?” | Source project IDs/country sets with the same explicit Cluster 5, no-WIDERA and minimum-three-partner conditions. Recalculate group presence from those source sets. |
| Programme eligibility | “Can this German university or SME participate in each programme?” | Deterministic organization/country/action inputs and the checked-in programme-rule data used by the tool. Check both permitted and disallowed examples. This validates the implementation's rule contract, not current legal advice. |
| Budget and timeline arithmetic | “Calculate and validate this RIA budget and a 36-month project timeline.” | Supplied totals, contribution rate, category sums, duration, work-package ranges and milestones. The expected arithmetic is computed independently of the tool output. |
| Document grounding | “What does the stored programme guidance say about eligibility or evaluation?” | Independently selected chunk IDs, document titles/pages and short text evidence for the selected programme. Cite only source evidence actually retrieved. Document metadata `total_chunks=0` does not imply an empty corpus; count joined chunk rows. |
| Proposal quality | “Check this deliberately incomplete draft and identify its gaps.” | A controlled input document with explicit missing elements; deterministic quality checks first. Generated scores must have valid ranges and useful content. No extra AI judge is used to certify an answer. |
| Proposal state and writing | “Focus this section, draft it, improve it, then mark it for review.” | A disposable in-memory proposal session with known sections/content/status. Inspect state after each successful mutation. Placeholder draft/evaluation output is a failure, not generated content. Existing user proposals are never modified. |
| Pagination | “Show more projects from those results.” | A disposable cache seeded from independently verified source IDs. Assert the next page, order and exhaustion behavior; no global Redis flush. |

## All 52 tool registrations

The catalog must contain an explicit case for each name below. Registration or
input-schema existence alone is not functional coverage.

| Category | Tools | Prerequisites beyond local source rows |
|---|---|---|
| Project retrieval | `search_projects`, `get_project_details`, `get_project_partners`, `search_by_cluster` | Actual repository/dispatch; graph-dependent paths must report whether graph was available. |
| Similarity | `find_similar_projects`, `find_semantically_similar_projects`, `get_similar_funded_projects` | Graph for graph-only discovery; stored vectors for project-to-project similarity. Description-to-vector search requires an embedding endpoint and a separate embedding-call allowance. |
| Organizations | `find_organization_projects`, `get_organization_stats`, `get_collaboration_network`, `find_experienced_partners` | SQL and, for graph-only relationships, a functioning graph source. |
| Statistics | `get_programme_statistics`, `get_country_statistics`, `compare_programmes` | A graph source where the tool requires one; do not pretend a mocked graph validates its data. |
| Research planning | `get_budget_benchmark`, `get_consortium_patterns`, `analyze_geographic_diversification`, `analyze_call_history` | Source-specific population checks; AI expansion disabled unless explicitly budgeted. |
| Call retrieval | `search_funding_calls`, `get_call_details`, `search_all_programmes` | Existing local call rows. External enrichment is separately gated and never substitutes for the known local source check. |
| Programme discovery | `recommend_programmes`, `get_programme_info` | Checked-in programme information; model requests if the selected implementation generates text. |
| General calculators | `calculate_budget`, `generate_timeline`, `validate_budget` | Controlled inputs plus optional source benchmarks. |
| Eligibility | `check_erasmus_eligibility`, `check_creative_europe_eligibility`, `check_eu4health_eligibility`, `check_digital_europe_eligibility`, `check_life_eligibility` | Controlled country/organization/action inputs and local programme rules. |
| Programme calculators | `calculate_erasmus_budget`, `calculate_creative_europe_budget` | Fixed arithmetic inputs and local unit-rate/rule tables. |
| Documents | `search_documents`, `search_erasmus_templates`, `search_creative_europe_templates`, `search_eu4health_templates`, `search_life_templates` | Existing chunks; actual vector paths require embedding access. Empty or unrelated chunks fail when independent evidence is present. |
| Proposal quality | `score_proposal_section`, `score_full_proposal`, `quick_quality_check` | Controlled input content; generated scoring consumes the same run-wide model budget. |
| Cache | `show_cached_projects` | Disposable cache seeded from source IDs. |
| Proposal writing | `generate_section_draft`, `improve_section`, `rewrite_section`, `evaluate_section`, `analyze_gaps`, `check_compliance`, `get_suggestions` | Disposable session and actual services. Missing services/placeholder output are blocked or failed; they are never recorded as live coverage. |
| Proposal state | `focus_section`, `mark_section_status`, `get_document_overview` | Disposable session with inspectable state. |

## Result interpretation

For each case retain its question/parameters, source-query key and evidence IDs,
observed tool names, exact assertions, status, duration and content-free usage
totals. Distinguish failed tool contracts from failed answer assertions, missing
source prerequisites, budget exhaustion and unexecuted cases. A known-empty
negative control is useful only alongside a known-present positive control.

This document describes the intended coverage and independently observed source
anchors. Execution results belong in the runner's report. It does not claim all
52 tools, all backend services, or every HTTP event have already passed.
