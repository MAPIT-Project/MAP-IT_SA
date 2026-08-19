# MAP-IT SA tool reference

This reference describes the **42 tools that are actually registered** by `ToolRegistryMixin._init_tools()` and routed by `_execute_single_tool()`. The parameter defaults below come from the executor layer; which determines the runtime behavior. The six documentation categories are deliberately simpler than the internal enum: internal `programmes` tools are listed here under **Call**, while `calculate_budget` and `generate_timeline` are listed under **Proposal support** because of their function.

Last verified: 20 July 2026.

## Summary

| Category | Quantity | Tools |
|---|---:|---|
| Statistics | 7 | `get_programme_statistics`, `get_country_statistics`, `get_budget_benchmark`, `get_consortium_patterns`, `analyze_geographic_diversification`, `analyze_call_history`, `get_organization_stats` |
| Comparison | 1 | `compare_programmes` |
| Document | 5 | `search_documents`, `search_erasmus_templates`, `search_creative_europe_templates`, `search_eu4health_templates`, `search_life_templates` |
| Call | 10 | `search_funding_calls`, `get_call_details`, `search_all_programmes`, `recommend_programmes`, `get_programme_info`, `check_erasmus_eligibility`, `check_creative_europe_eligibility`, `check_eu4health_eligibility`, `check_digital_europe_eligibility`, `check_life_eligibility` |
| Project | 11 | `find_experienced_partners`, `get_similar_funded_projects`, `search_projects`, `get_project_details`, `find_similar_projects`, `find_semantically_similar_projects`, `find_organization_projects`, `get_project_partners`, `get_collaboration_network`, `search_by_cluster`, `show_cached_projects` |
| Proposal support | 8 | `calculate_budget`, `generate_timeline`, `score_proposal_section`, `score_full_proposal`, `quick_quality_check`, `validate_budget`, `calculate_erasmus_budget`, `calculate_creative_europe_budget` |
| **Total** | **42** | |

## Reading guide

- `required` means that the tool cannot be meaningfully executed without a substantive value, even if the executor technically enters `""` or `0`.
- `null` means Python `None`: no filter or no specified value.
- “Accepted” indicates a parameter that the executor processes but that is not in the registry description.
- “Ignored” indicates a parameter that is in the registry but is not passed to the implementation.
- **PostgreSQL** is the relational application database. **pgvector** is vector storage/similarity within PostgreSQL/Supabase. **Neo4j** is the graph data store. **External API** means Google embeddings/Gemini, OpenAI or the EU Funding & Tenders Portal, as listed per row.
- “Built-in rules” are versioned tables/heuristics in Python and not a live data store.

## Statistics

| Tool | Input parameters (type and runtime default) | What does the tool do? | Datastore(s) |
|---|---|---|---|
| `get_programme_statistics` | `programme: str` (required)<br>`metric: str \| null = null` (**ignored**) | Returns program or cluster statistics. EIC, ERC and MSCA come from built-in reference values; Pillar 2 clusters are read from the graph. | Neo4j; built-in EC reference values ​​|
| `get_country_statistics` | `country: str` (required; name or ISO-2)<br>`programme: str \| null = null` (**ignored**) | Provides eligibility, top organizations and participation for one country. Try Neo4j first and use PostgreSQL as fallback. | Neo4j; PostgreSQL fallback |
| `get_budget_benchmark` | `cluster: str \| null = null`<br>`action_type: str \| null = null`<br>`topic_keywords: str \| null = null`<br>`year: int \| null = null` | Calculates min/max/average/median of contributions and context such as budget per partner based on funded projects. | PostgreSQL; Neo4j |
| `get_consortium_patterns` | `cluster: str \| null = null`<br>`action_type: str \| null = null`<br>`topic_keywords: str \| null = null`<br>`min_projects: int = 10` (accepted) | Analyzes consortium size, organization types, countries and coordinator profiles from historical projects. | PostgreSQL; Neo4j |
| `analyze_geographic_diversification` | `cluster: str \| null = null`<br>`exclude_widening: bool = true`<br>`min_partners: int = 3`<br>`country_groups: dict[str, list[str]] \| null = null` | Measure per self-selected or standard region what share of consortia contains at least one partner from that region. | PostgreSQL; built-in default country groups |
| `analyze_call_history` | `topic_pattern: str \| null = null`<br>`cluster: str \| null = null`<br>`keywords: str \| null = null`<br>`year_from: int \| null = null`<br>`year_to: int \| null = null`<br>`action_types: list[str] \| null = null`<br>`include_projects: bool = true`<br>`expand_scope: bool = false`<br>`limit: int = 50` (accepted) | Analyzes historical calls, financing trends and example projects. With `expand_scope=true`, a LLM expands the search terms. | PostgreSQL; Neo4j; Gemini API optional for term extension |
| `get_organization_stats` | `organization_name: str` (required) | Returns numbers of projects and coordinations, total funding, and active clusters for an organization. | Neo4j; PostgreSQL fallback |

## Comparison

| Tool | Input parameters (type and runtime default) | What does the tool do? | Datastore(s) |
|---|---|---|---|
| `compare_programmes` | `programme_a: str` (required)<br>`programme_b: str` (required)<br>`metrics: list[str] \| null = null` (**ignored**) | Gets for two program/cluster names and display the same cluster statistics side by side. The current implementation does not filter on `metrics`. | Neo4j |

## Document

All five tools use `VectorSearchService`: hybrid full-text and vector searches in Supabase/PostgreSQL with pgvector. For a new query embedding, the Google Embeddings API is used; an error in this can lead to a keyword-only/degraded result.

| Tool | Input parameters (type and runtime default) | What does the tool do? | Datastore(s) |
|---|---|---|---|
| `search_documents` | `query: str` (required)<br>`document_type: str \| null = null`<br>`max_results: int = 15` | Searches indexed official EU documents and returns text plus source, section, page and chunk metadata. Note: the old registry text calls 5, but the executor uses 15. | PostgreSQL/Supabase; pgvector; Google Embeddings API |
| `search_erasmus_templates` | `query: str` (required)<br>`key_action: str \| null = null`<br>`sector: str \| null = null`<br>`document_type: str \| null = null`<br>`top_k: int = 5` | Looking for Erasmus+ Program Guide fragments on eligibility, budget and quality criteria, among others. | PostgreSQL/Supabase; pgvector; Google Embeddings API |
| `search_creative_europe_templates` | `query: str` (required)<br>`strand: str \| null = null`<br>`action_type: str \| null = null`<br>`topic: str \| null = null`<br>`top_k: int = 5` | Searches Creative Europe documents and can query limit to beach, action or subject. | PostgreSQL/Supabase; pgvector; Google Embeddings API |
| `search_eu4health_templates` | `query: str` (required)<br>`strand: str \| null = null`<br>`action_type: str \| null = null`<br>`topic: str \| null = null`<br>`top_k: int = 5` | Searching EU4Health Work Programs and regulations for application, eligibility and program information. | PostgreSQL/Supabase; pgvector; Google Embeddings API |
| `search_life_templates` | `query: str` (required)<br>`subprogramme: str \| null = null`<br>`section: str \| null = null`<br>`top_k: int = 5` | Searches LIFE regulations, guidance and Work Program snippets per subprogram or section. | PostgreSQL/Supabase; pgvector; Google Embeddings API |

`search_digital_europe_templates_execute()` exists in the codebase, but ** is not registered or routed** and is therefore not one of the 42 available agent tools.

## Call

| Tool | Input parameters (type and runtime default) | What does the tool do? | Datastore(s) |
|---|---|---|---|
| `search_funding_calls` | `keywords: str \| list[str]` (required)<br>`status: str = "open"` (`open`, `upcoming`, `closed`, `all`)<br>`year: int \| str \| null = null`<br>`cluster: str \| null = null` (accepted) | Searches calls first structured, then semantic/graph-based and finally in document chunks; Missing status/deadline can be enriched via the EU Portal. | PostgreSQL; Neo4j; pgvector; Google Embeddings API; EU Funding & Tenders Portal API |
| `get_call_details` | `call_id: str` (required) | Retrieves one call via local data, call ID variants and ultimately direct Portal enrichment; can suggest similar calls if nothing is found. | PostgreSQL; pgvector; Google Embeddings API; EU Funding & Tenders Portal API |
| `search_all_programmes` | `keywords: str` (required)<br>`programmes: list[str] \| null = null`<br>`status: str \| null = null`<br>`year: int \| null = null`<br>`action_type: str \| null = null` (accepted)<br>`limit: int = 20` (accepted; per program)<br>`include_closed: bool = false` (accepted) | Searches uniformly in calls for Horizon Europe, Erasmus+, Creative Europe, EU4Health, Digital Europe and LIFE. | PostgreSQL |
| `recommend_programmes` | `description: str` (required)<br>`organization_type: str \| null = null`<br>`sector: str \| null = null` | Ranks appropriate programs with keyword and organization rules and adds availability context. This is not a generative AI call. | Built-in program catalog and rules; PostgreSQL for call counts |
| `get_programme_info` | `programme: str \| null = null` | Provides information and official follow-up links for one supported program, or an overview of all programs. | Built-in program catalog/extractors; PostgreSQL for call counts |
| `check_erasmus_eligibility` | `org_type: str = "HEI"`<br>`country: str = "Germany"`<br>`action_type: str \| null = null`<br>`has_eche: bool = false`<br>`is_coordinator: bool = true` | Tests Erasmus+ eligibility per organization, country, action and ECHE status; graphdata can enrich the fixed rules. | Built-in rules; Neo4j optional |
| `check_creative_europe_eligibility` | `org_type: str = "CULTURAL_ORG"`<br>`country: str = "Germany"`<br>`action_type: str \| null = null`<br>`strand: str \| null = null`<br>`is_coordinator: bool = true` | Tests eligibility for CULTURE, MEDIA and CROSS-SECTORAL; graphdata can enrich the fixed rules. | Built-in rules; Neo4j optional |
| `check_eu4health_eligibility` | `org_type: str = "HEALTHCARE_PROVIDER"`<br>`country: str = "Germany"`<br>`action_type: str \| null = null`<br>`strand: str \| null = null` | Tests EU4Health eligibility for organization, country, action type and beach. | Built-in rules; no runtime data store |
| `check_digital_europe_eligibility` | `org_type: str = "SME"`<br>`country: str = "Germany"`<br>`objective: str \| null = null`<br>`action_type: str \| null = null` | Tests eligibility against the Digital Europe objectives and country/organization type rules. | Built-in rules; no runtime data store |
| `check_life_eligibility` | `org_type: str = "NGO"`<br>`country: str = "Germany"`<br>`subprogramme: str \| null = null`<br>`project_type: str \| null = null` | Tests eligibility for LIFE subprograms and project types. | Built-in rules; no runtime data store |

## Project

| Tool | Input parameters (type and runtime default) | What does the tool do? | Datastore(s) |
|---|---|---|---|
| `find_experienced_partners` | `topic_keywords: str` (required; `keywords` is also used accepted)<br>`country: str \| null = null`<br>`organization_type: str \| null = null`<br>`cluster: str \| null = null`<br>`min_projects: int = 2`<br>`role_filter: str \| null = null`<br>`limit: int = 20` (accepted)<br>`programme: str \| null = null` (**ignored**) | Finds organizations with demonstrable project, financing and coordination experience on a topic. | PostgreSQL; Neo4j |
| `get_similar_funded_projects` | `description: str` (required)<br>`cluster: str \| null = null`<br>`action_type: str \| null = null`<br>`min_budget: float \| null = null`<br>`max_budget: float \| null = null`<br>`year_from: int \| null = null`<br>`limit: int = 100` effective minimum<br>`similarity_threshold: float = 0.3` (accepted) | Searching semantically to funded projects based on a concept description and enriched/reranked with graph context. The executor always retrieves at least 100 candidates, despite the registry text “default 10”. | PostgreSQL; pgvector; Neo4j; Google Embeddings API |
| `search_projects` | `keywords: str` (required)<br>`programme: str \| null = null`<br>`country: str \| null = null`<br>`limit: int = 100` effective minimum<br>`sort_by: str \| null = null` (`relevance`, `ec_contribution`, `total_cost`, `start_date`) | Searches local CORDIS projects with full-text and vector retrieval and graph enrichment. Here too, the executor increases any lower `limit` to 100 candidates. | PostgreSQL; pgvector; Neo4j; Google Embeddings API |
| `get_project_details` | `project_id: str` (required; ID or acronym) | Provides project metadata and full partner list; with an unknown ID a search fallback follows by acronym. | PostgreSQL; fallback can use PostgreSQL, pgvector, Neo4j and Google Embeddings API |
| `find_similar_projects` | `project_id: str` (required)<br>`similarity_type: str = "topic"` (`topic`, `consortium`, `cluster`) | Finds up to ten projects through relationships with the reference project. | Neo4j |
| `find_semantically_similar_projects` | `project_id: str` (required)<br>`limit: int = 10` | Compares the already saved embedding of a reference project with other project embeddings. | PostgreSQL; pgvector |
| `find_organization_projects` | `organization_name: str` (required)<br>`role: str \| null = null` (`coordinator` or `participant`) | Lists an organization's projects and calculates total and coordinator counts; maximum 100 project lines. | Neo4j |
| `get_project_partners` | `project_id: str` (required; ID or acronym) | Specifies consortium members, roles, countries, and contributions for a project. | PostgreSQL; search fallback can use PostgreSQL, pgvector, Neo4j and Google Embeddings API |
| `get_collaboration_network` | `organization_name: str` (required) | Indicates direct collaboration partners of an organization, with shared projects. | Neo4j |
| `search_by_cluster` | `cluster: str` (required) | Finds up to fifteen projects through the cluster relationship. | Neo4j; PostgreSQL fallback in the underlying search service |
| `show_cached_projects` | No parameters | Shows the next page of a previous project search and increases the offset; cache entries expire after 30 minutes. | Redis |

## Proposal support

| Tool | Input parameters (type and runtime default) | What does the tool do? | Datastore(s) |
|---|---|---|---|
| `calculate_budget` | `action_type: str = "RIA"`<br>`duration_months: int = 36`<br>`num_partners: int = 8`<br>`total_person_months: int \| null = null`<br>`target_budget: float \| null = null`<br>`countries: list[str] \| null = null`<br>`include_breakdown: bool = true` (accepted) | Creates a Horizon Europe budget distribution with historical benchmarks, land costs and built-in ratios. | PostgreSQL; Neo4j; built-in calculation rules |
| `generate_timeline` | `action_type: str = "RIA"`<br>`duration_months: int = 36`<br>`num_partners: int = 8`<br>`total_person_months: int = 300`<br>`project_title: str = "Project"`<br>`start_date: str \| null = null` (`YYYY-MM-DD`)<br>`custom_wps: list[dict] \| null = null` (accepted) | Generates work packages, deliverables, milestones, dependencies and Gantt data with historical duration patterns where available. | PostgreSQL; Neo4j; built-in templates |
| `score_proposal_section` | `content: str` (required; minimum 50 characters)<br>`section_type: str = "excellence"`<br>`section_id: str \| null = null`<br>`action_type: str = "RIA"`<br>`call_id: str \| null = null` (accepted) | Scores one proposal component on 0–5 with criterion breakdown, strengths/weaknesses and improvement actions; uses local heuristics if AI fails. | Gemini API primary; OpenAI API optional fallback; built-in fallback rules |
| `score_full_proposal` | `excellence_content: str` (required)<br>`impact_content: str` (required)<br>`implementation_content: str` (required)<br>`action_type: str = "RIA"`<br>`call_id: str \| null = null` (accepted) | Scores the three main parts and calculates total score (0–15) and indicative financing probability. | Gemini API primary; OpenAI API optional fallback; built-in fallback rules |
| `quick_quality_check` | `text: str` (required)<br>`context: str = "general"` | Provides fast, deterministic indicators for length, structure, quantification and improvement suggestions; does not make a LLM call. | Built-in heuristics; no runtime data store |
| `validate_budget` | `total_cost: float` (required; executor fallback `0`)<br>`eu_contribution: float` (required; executor fallback `0`)<br>`action_type: str = "RIA"`<br>`duration_months: int = 36`<br>`num_partners: int = 3`<br>`cost_breakdown: dict[str, float] \| null = null`<br>`call_budget_cap: float \| null = null`<br>`consortium: list[dict] \| null = null` (accepted) | Checks funding rate, indirect costs, cost categories, budget range, duration and consortium distribution. | Built-in validation rules; no runtime data store |
| `calculate_erasmus_budget` | `action_type: str = "partnership"`<br>`num_participants: int = 10`<br>`duration_days: int = 14`<br>`duration_months: int = 24`<br>`num_partners: int = 3`<br>ZZZPROTECT ED8ZZZ<br>`origin_country: str = "Spain"`<br>`partnership_type: str = "cooperation"`<br>`distance_band: str = "500-1999km"`<br>`green_travel: bool = false`<br>`target_budget: float \| null = null` | Calculates Erasmus+ mobility, partnership, Jean Monnet or sports budgets from unit costs and lump sums. | Built-in calculation tables; no runtime data store |
| `calculate_creative_europe_budget` | `action_type: str = "COOP-SMALL"`<br>`requested_amount: float \| null = null`<br>`project_scale: str = "medium"`<br>`num_partners: int = 3`<br>`duration_months: int \| null = null`<br>`strand: str \| null = null` | Calculates subsidy ceiling, funding rate and indicative distribution for Creative Europe actions. | Built-in calculation tables; no runtime data store |

## Known registry/executor anomalies

These deviations are part of current code behavior and are therefore not tacitly “corrected” in this documentation:

1. `metric` with `get_programme_statistics`, `programme` with `get_country_statistics`, `metrics` with `compare_programmes` and `programme` with `find_experienced_partners` are registered but ignored by the executor.
2. Multiple executors accept additional, unregistered filters; those are marked as “accepted” above. A LLM will not automatically see this in the generated tool prompt.
3. `search_documents` uses runtime default 15, not the 5 from the registry text.
4. `search_projects` and `get_similar_funded_projects` effectively retrieve at least 100 candidates, even when the registry suggests a default of 10.
5. `search_digital_europe_templates_execute()` has an implementation, but without registration and route it is not an available tool.

## Sources of truth

- Registration, name, internal category and visible parameter description: `app/services/agents/tool_registry.py`
- Runtime routing and effective defaults: `app/services/agents/tool_executors.py`
- Behavior and data stores: `app/services/tools/*.py`, `app/services/local_project_search_service.py`, `app/services/local_call_search_service.py`, `app/services/vector_search_service.py`, `app/services/data/cordis_repository.py`
- Proposal AI providers: `app/services/proposal_writing/proposal_ai_service.py` and `app/services/proposal_writing/ai_providers/multi_provider_service.py`
