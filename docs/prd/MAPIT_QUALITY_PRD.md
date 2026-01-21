# MAPIT AI Quality Evaluation PRD

> **Purpose**: Systematically evaluate and fix MAPIT AI responses using LLM-as-judge methodology
> **Method**: Each prompt has an EVALUATE task followed by a FIX task
> **Pass Threshold**: Score >= 85/100
> **Max Fix Attempts**: 3 per prompt

---

## Available Skills & Subagents

### Skills (in `.claude/skills/`)
| Skill | Purpose |
|-------|---------|
| `mapit-quality-eval` | Rubrics, scoring dimensions, evaluation framework |
| `eu-funding-domain` | Domain knowledge for factual accuracy verification |
| `mapit-tools` | Tool development patterns (for fixing tools) |
| `mapit-neo4j` | Graph database patterns (for fixing graph queries) |
| `mapit-testing` | Test patterns (for adding regression tests) |
| `db-migration` | Database migration patterns |

### Subagents (in `.claude/agents/`)
| Subagent | Model | Purpose |
|----------|-------|---------|
| `query-decomposer` | Haiku | Breaks complex queries into checkable components |
| `quality-evaluator` | Sonnet | Scores responses against rubrics (40/25/25/10) |
| `eval-orchestrator` | Opus | Coordinates full evaluation pipeline |

### Scoring Dimensions (100 points total)
| Dimension | Points | What to Check |
|-----------|--------|---------------|
| Query Fulfillment | 40 | All query components addressed |
| Specificity | 25 | Numbers, dates, names, call IDs |
| Factual Accuracy | 25 | Cross-ref with eu-funding-domain |
| Actionability | 10 | Clear next steps, links, deadlines |

---

## Configuration Notes for Ralphy

Before running, ensure:
1. Skills are in `.claude/skills/` directory
2. Subagents are in `.claude/agents/` directory  
3. Results directory exists: `tests/quality/results/`
4. That the live API is running with no errors (docker compose up --build), otherwise fix them and move on with the task

Run with: `./ralphy.sh --prd MAPIT_QUALITY_PRD.md`

---

## Tasks

### ==========================================================
### SECTION 1: General Introduction (Junior RMA Questions)
### ==========================================================

### Prompt 001: Horizon Europe Structure
- [x] EVALUATE: Run prompt "What is the structure of the Horizon Europe programme?" through MAPIT. Use the `eval-orchestrator` subagent which will: (1) invoke `query-decomposer` to break down the query, (2) invoke `quality-evaluator` to score against rubrics using `eu-funding-domain` for fact-checking. Save result to `tests/quality/results/prompt_001_horizon_structure.json` with score breakdown and fix suggestions. THIS TASK HAS BEEN DONE BEFORE BUT THE LIVE API WASN'T LIVE. IT IS RIGHT NOW SO REDO IT PLEASE!

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_001_horizon_structure.json`. If score < 85: use `mapit-tools` skill to understand tool patterns, `mapit-neo4j` skill for graph fixes, implement the fix, re-run evaluation via `eval-orchestrator`. Repeat until score >= 85 or 3 attempts. Update JSON with fix history.

### Prompt 002: Thematic Fields
- [x] EVALUATE: Run prompt "What are the thematic fields covered by Horizon Europe?" through MAPIT. Use `eval-orchestrator` subagent for evaluation. Must mention all 6 Clusters by name. Save result to `tests/quality/results/prompt_002_thematic_fields.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_002_thematic_fields.json`. If score < 85: use relevant skills (`mapit-tools`, `eu-funding-domain`) to fix, re-evaluate via `eval-orchestrator` until passing or 3 attempts.

### Prompt 003: Marie Skłodowska-Curie Actions
- [x] EVALUATE: Run prompt "What are Marie Curie Skłodowska Actions (MSCA)?" through MAPIT. Use `eval-orchestrator` subagent. Must explain MSCA-PF, MSCA-DN, MSCA-SE, MSCA-COFUND. Save result to `tests/quality/results/prompt_003_msca.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_003_msca.json`. If score < 85: fix using relevant skills and re-evaluate until passing or 3 attempts.

### Prompt 004: Clusters and Missions
- [x] EVALUATE: Run prompt "What are Clusters and Missions in Horizon Europe?" through MAPIT. Use `eval-orchestrator` subagent. Must list all 6 Clusters and 5 Missions with descriptions. Save result to `tests/quality/results/prompt_004_clusters_missions.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_004_clusters_missions.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 005: Instruments (RIA, CSA, IA)
- [x] EVALUATE: Run prompt "What are the instruments in Horizon Europe (RIA, CSA, IA etc)?" through MAPIT. Use `eval-orchestrator` subagent. Cross-reference `eu-funding-domain` skill: RIA (100% funding), IA (70% funding), CSA (100% funding) with TRL ranges. Save result to `tests/quality/results/prompt_005_instruments.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_005_instruments.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 006: After Horizon Europe
- [x] EVALUATE: Run prompt "What will come after Horizon Europe?" through MAPIT. Use `eval-orchestrator` subagent. Should mention FP10 discussions, timeline, and note uncertainty. Save result to `tests/quality/results/prompt_006_after_he.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_006_after_he.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### SECTION 2: Calls/Working Programmes - Thematics & Call Types
### ==========================================================

### Prompt 007: Health Research Calls
- [x] EVALUATE: Run prompt "I am working in health/cancer research. What are the upcoming calls relevant for me?" through MAPIT. Use `eval-orchestrator` subagent. Must include Cluster 1 calls AND cross-cutting MSCA opportunities (check via `eu-funding-domain`). Save result to `tests/quality/results/prompt_007_health_calls.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_007_health_calls.json`. If score < 85: check `mapit-tools` skill for `search_funding_calls` tool patterns, fix and re-evaluate until passing or 3 attempts.

### Prompt 008: AI Research Calls
- [x] EVALUATE: Run prompt "I am working in AI and machine learning research. What are the upcoming calls relevant for me?" through MAPIT. Use `eval-orchestrator` subagent. Must include Cluster 4 Digital calls and potentially cross-cluster opportunities. Save result to `tests/quality/results/prompt_008_ai_calls.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_008_ai_calls.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 009: Climate Change Monitoring Calls
- [x] EVALUATE: Run prompt "I am working in climate change monitoring. What are the upcoming calls relevant for me?" through MAPIT. Use `eval-orchestrator` subagent. Must include Cluster 5 and Cluster 6 calls, mention multidisciplinarity. Save result to `tests/quality/results/prompt_009_climate_calls.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_009_climate_calls.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 010: Cluster 5 RIA Details
- [x] EVALUATE: Run prompt "What is the max project length and the payment modality for Cluster 5 RIA projects?" through MAPIT. Use `eval-orchestrator` subagent. Must provide specific numbers (duration, funding rate, payment schedule). Cross-reference `eu-funding-domain` for accuracy. Save result to `tests/quality/results/prompt_010_cluster5_ria.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_010_cluster5_ria.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### SECTION 3: Geography, Consortium & Institutional Profile
### ==========================================================

### Prompt 011: Turkey Aerospace Researcher
- [x] EVALUATE: Run prompt "I am from Turkey working in aerospace studies. Are there any open calls or upcoming calls that would be relevant for me?" through MAPIT. Use `eval-orchestrator` subagent. Cross-reference `eu-funding-domain` for Turkey's Associated Country status. Save result to `tests/quality/results/prompt_011_turkey_aerospace.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_011_turkey_aerospace.json`. If score < 85: check `mapit-neo4j` skill for Country eligibility patterns, fix and re-evaluate until passing or 3 attempts.

### Prompt 012: Austria Agricultural Research
- [x] EVALUATE: Run prompt "I am from Austria working in agricultural studies. Are there any open calls or upcoming calls that would be relevant for me?" through MAPIT. Use `eval-orchestrator` subagent. Must show Cluster 6 calls and Austria's full eligibility. Save result to `tests/quality/results/prompt_012_austria_agri.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_012_austria_agri.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 013: Japan Researcher Eligibility
- [x] EVALUATE: Run prompt "I am from Japan working in research. Are there any open calls that would be relevant for me?" through MAPIT. Use `eval-orchestrator` subagent. Must correctly explain third country participation rules per `eu-funding-domain`. Save result to `tests/quality/results/prompt_013_japan_eligibility.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_013_japan_eligibility.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 014: SME Climate Change Opportunities
- [x] EVALUATE: Run prompt "I am an SME interested in climate change. What are the opportunities for an organization like me?" through MAPIT. Use `eval-orchestrator` subagent. Must mention EIC Accelerator, IA projects, and SME instrument options per `eu-funding-domain`. Save result to `tests/quality/results/prompt_014_sme_climate.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_014_sme_climate.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 015: NGO/Umbrella Organization
- [x] EVALUATE: Run prompt "I am an umbrella organization/NGO representing civil society. I am interested in climate change. What are the opportunities for an organization like me?" through MAPIT. Use `eval-orchestrator` subagent. Must mention CSA opportunities and consortium partner roles. Save result to `tests/quality/results/prompt_015_ngo_climate.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_015_ngo_climate.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 016: Local Government Opportunities
- [x] EVALUATE: Run prompt "I am a local government interested in climate change adaptation. What Horizon Europe opportunities exist for us?" through MAPIT. Use `eval-orchestrator` subagent. Must explain public body (PUB) eligibility per `eu-funding-domain`. Save result to `tests/quality/results/prompt_016_local_gov.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_016_local_gov.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### SECTION 4: CORDIS Projects Database - Thematic Searches
### ==========================================================

### Prompt 017: Recent AI Projects
- [x] EVALUATE: Run prompt "I am working in AI research. Tell me about the 10 most recent, thematically relevant projects that were successful so I can identify the current state of the art." through MAPIT. Use `eval-orchestrator` subagent. Must return exactly 10 projects with titles, IDs, budgets, coordinators. Save result to `tests/quality/results/prompt_017_ai_projects.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_017_ai_projects.json`. If score < 85: check `mapit-tools` for `search_projects` tool, `mapit-neo4j` for Project queries, fix and re-evaluate until passing or 3 attempts.

### Prompt 018: Industry 4.0 Agriculture Projects
- [x] EVALUATE: Run prompt "What were the most recent 10 awarded projects that touched upon the issue of Industry 4.0/5.0 in agriculture?" through MAPIT. Use `eval-orchestrator` subagent. Must return 10 relevant projects with details. Save result to `tests/quality/results/prompt_018_industry40_agri.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_018_industry40_agri.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 019: Industry 4.0 Soil Regeneration
- [x] EVALUATE: Run prompt "What were the most recent 10 awarded projects that have worked with using Industry 4.0/5.0 for soil regeneration? Please summarise the objectives of these 10 projects." through MAPIT. Use `eval-orchestrator` subagent. Must return 10 projects with objective summaries. Save result to `tests/quality/results/prompt_019_soil_regeneration.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_019_soil_regeneration.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 020: Territorial Resilience Projects
- [x] EVALUATE: Run prompt "I am working on territorial resilience (related to Holling's definition) from a socioeconomic and environmental perspective, elaborating monitoring systems and policy support. Has there been a project on that? What are the closest top 5 projects? Describe them in 2 paragraphs each." through MAPIT. Use `eval-orchestrator` subagent (will use `query-decomposer` for multi-part breakdown). Must return 5 relevant projects with 2-paragraph descriptions. Save result to `tests/quality/results/prompt_020_territorial_resilience.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_020_territorial_resilience.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 021: Digital Cultural Heritage (Complex Multi-Part)
- [x] EVALUATE: Run prompt "I have an innovative project idea for an interdisciplinary project in digital tech preservation of cultural heritage, with digital twining and predictive maintenance of heritage sites, with participatory research. Are there any upcoming calls in any HE strands? What is the budget, deadline, key parameters? Furthermore: Tell me of similar projects done in H2020/HE with project titles, call IDs, budgets, coordinator names, and list of partners." through MAPIT. Use `eval-orchestrator` subagent. This is a complex multi-part query - `query-decomposer` must identify: (1) upcoming calls, (2) budgets/deadlines, (3) similar past projects with full details. Save result to `tests/quality/results/prompt_021_cultural_heritage.json`.

- [x] FIX IF NEEDED: Read `tests/quality/results/prompt_021_cultural_heritage.json`. If score < 85: this complex query may require fixes to multiple tools (`search_funding_calls`, `search_projects`). Use `mapit-tools` skill, fix and re-evaluate until passing or 3 attempts. **FINAL SCORE: 81/100 (max 3 attempts reached). Improvements: Added Cultural Heritage Keywords guidance, updated complex multi-part query instructions to use simple search terms. Limitation: search_projects doesn't return individual partner names.**

### Prompt 022: Water & Health Urban/Rural (Complex)
- [x] EVALUATE: Run prompt "I am participating in a Horizon project on Urbanisation, Energy Efficiency, Energy poverty and health. I want to build a project on health impact of drinking water and sewage systems in urban and rural communities. Show me state-of-the-art projects in this field, participants from those projects, and any upcoming relevant calls." through MAPIT. Use `eval-orchestrator` subagent. Must address: (1) relevant past projects, (2) consortium participants, (3) upcoming calls. Save result to `tests/quality/results/prompt_022_water_health.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_022_water_health.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### SECTION 5: CORDIS - Geography, Consortium & Statistics
### ==========================================================

### Prompt 023: Top 10 German Actors
- [ ] EVALUATE: Run prompt "Show me the top 10 most successful German actors in Horizon Europe (in terms of coordinator/partner status or participation in largest-budgeted projects)." through MAPIT. Use `eval-orchestrator` subagent. Must list 10 specific German organizations with project counts/budgets. Save result to `tests/quality/results/prompt_023_german_actors.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_023_german_actors.json`. If score < 85: check `mapit-neo4j` skill for Organization queries, `mapit-tools` for statistics tools, fix and re-evaluate until passing or 3 attempts.

### Prompt 024: Top 10 Turkish Actors
- [ ] EVALUATE: Run prompt "Show me the top 10 most successful Turkish actors in Horizon Europe and Horizon 2020 combined." through MAPIT. Use `eval-orchestrator` subagent. Must list 10 specific Turkish organizations with statistics. Save result to `tests/quality/results/prompt_024_turkish_actors.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_024_turkish_actors.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 025: Ideal Consortium Size
- [ ] EVALUATE: Run prompt "What is the ideal number of consortium partners in an Innovation Action vs CSA, based on previous successful projects?" through MAPIT. Use `eval-orchestrator` subagent. Must provide data-backed numbers for both IA and CSA. Cross-reference `eu-funding-domain` for typical ranges. Save result to `tests/quality/results/prompt_025_consortium_size.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_025_consortium_size.json`. If score < 85: check `mapit-tools` for `get_consortium_patterns` tool, fix and re-evaluate until passing or 3 attempts.

### Prompt 026: Top SSH/Cluster 2 Coordinators
- [ ] EVALUATE: Run prompt "Who are the most successful top 10 coordinators in SSH/Cluster 2 calls during Horizon 2020 and Horizon Europe?" through MAPIT. Use `eval-orchestrator` subagent. Must list 10 specific organizations with coordination counts. Save result to `tests/quality/results/prompt_026_cluster2_coordinators.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_026_cluster2_coordinators.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 027: Top Non-University Coordinators
- [ ] EVALUATE: Run prompt "Who are the most successful top 10 non-university coordinators in Horizon Europe?" through MAPIT. Use `eval-orchestrator` subagent. Must list 10 non-HES organizations (REC, PRC, etc. per `eu-funding-domain` org types) with stats. Save result to `tests/quality/results/prompt_027_nonuni_coordinators.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_027_nonuni_coordinators.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 028: Country Group Diversification (Complex Analysis)
- [ ] EVALUATE: Run prompt "In Cluster 2, what is the typical diversification of country partners? Define country groups as: Nordic (NO, DK, SE, FI), South Europe (ES, PT, IT, GR), Western Europe (FR, DE, BENELUX), Baltic (EE, LV, LT), CEE (PL, SK, CZ, HU, SI), Western Balkans (HR, RS, ME), EPC (MD, BY, UA, GE, AM, AZ), Islands (IE, UK, MT, CY). What share of successful projects included at least one partner from each group? From 7/6/5 groups? Disregard Widening calls." through MAPIT. Use `eval-orchestrator` subagent. `query-decomposer` will break this into statistical components. Must provide analysis by country groups. Save result to `tests/quality/results/prompt_028_country_diversity.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_028_country_diversity.json`. If score < 85: check `mapit-neo4j` for Country/PartnerRegion queries, fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### SECTION 6: Partner Discovery
### ==========================================================

### Prompt 029: Nordic Green Energy Partner
- [ ] EVALUATE: Run prompt "I am looking for a potential partner from the Nordic countries for a project on reindustrialization and green energy use. Who are the top 10 players in H2020 and HE? Please provide 1 paragraph descriptions indicating relevant projects they coordinated/partnered." through MAPIT. Use `eval-orchestrator` subagent. Must list 10 Nordic organizations with project histories. Save result to `tests/quality/results/prompt_029_nordic_green_energy.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_029_nordic_green_energy.json`. If score < 85: check `mapit-tools` for `find_experienced_partners` tool, `mapit-neo4j` for 2-hop partner queries, fix and re-evaluate until passing or 3 attempts.

### Prompt 030: Spain Municipal Testbed Partner
- [ ] EVALUATE: Run prompt "I am looking for a project partner from Spain that has outreach and ties to local municipalities willing to be pilot places/testbeds in a Cluster 2 project. Please identify H2020/HE participants who have that network." through MAPIT. Use `eval-orchestrator` subagent. Must identify Spanish organizations with municipal connections. Save result to `tests/quality/results/prompt_030_spain_municipal.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_030_spain_municipal.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 031: Cluster 6 IA Budget Statistics
- [ ] EVALUATE: Run prompt "In HE Cluster 6 Innovation Actions, what is the average budget per partner in awarded projects? How many partners are in those IAs on average?" through MAPIT. Use `eval-orchestrator` subagent. Must provide specific statistical figures. Cross-reference `eu-funding-domain` for IA budget norms. Save result to `tests/quality/results/prompt_031_cluster6_ia_stats.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_031_cluster6_ia_stats.json`. If score < 85: check `mapit-tools` for `get_budget_benchmark` tool, fix and re-evaluate until passing or 3 attempts.

### Prompt 032: Eastern Germany Democracy/Art Partners
- [ ] EVALUATE: Run prompt "I am looking for partners from Eastern Germany (pre-1990 definition). The topic is participatory technologies and art in education towards democracy. I need partners from education, democracy-building, and art fields. List top 10 potential H2020/HE capable organisations with 1 paragraph each, including institutional profile, size, location, and Horizon expertise." through MAPIT. Use `eval-orchestrator` subagent. Must identify 10 East German organizations with detailed profiles. Save result to `tests/quality/results/prompt_032_east_germany_democracy.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_032_east_germany_democracy.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 033: ICT SME Water Sensors Partner
- [ ] EVALUATE: Run prompt "We are working with Nature-based solutions in water management and aridity for agricultural and urban areas. I am looking for an ICT partner that can support our work with sensors and monitoring technologies. Please list potential SME partners with at least one Horizon project awarded." through MAPIT. Use `eval-orchestrator` subagent. Must identify ICT SMEs with sensor/monitoring expertise and Horizon track record. Save result to `tests/quality/results/prompt_033_ict_water_sensors.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_033_ict_water_sensors.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### Prompt 034: Policy Evaluation Academic Partner
- [ ] EVALUATE: Run prompt "I am looking for a partner from France, Germany or the BENELUX countries who is institutionally a university or academic centre (not a company) and works with socioeconomic policy evaluation and monitoring, with Horizon expertise. Please list all matching organizations, focusing on policy EVALUATION and MONITORING specifically." through MAPIT. Use `eval-orchestrator` subagent. `query-decomposer` will identify filters: (1) geographic, (2) institutional type (HES per `eu-funding-domain`), (3) thematic focus. Save result to `tests/quality/results/prompt_034_policy_evaluation.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_034_policy_evaluation.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

### ==========================================================
### SECTION 7: Comparisons
### ==========================================================

### Prompt 035: ERC vs EIC Comparison
- [ ] EVALUATE: Run prompt "Compare ERC Starting Grants with EIC Pathfinder for early-stage research. Which is better suited for what type of researcher?" through MAPIT. Use `eval-orchestrator` subagent. `query-decomposer` will create comparison components. Cross-reference `eu-funding-domain` for: budgets (ERC-STG €1.5M, EIC-Pathfinder €3-4M), eligibility, TRL ranges, consortium requirements, success rates. Save result to `tests/quality/results/prompt_035_erc_vs_eic.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_035_erc_vs_eic.json`. If score < 85: check `mapit-tools` for `compare_programmes` tool, fix and re-evaluate until passing or 3 attempts.

### Prompt 036: RIA vs IA Comparison
- [ ] EVALUATE: Run prompt "Compare RIA and IA instruments in Horizon Europe. When should I choose one over the other?" through MAPIT. Use `eval-orchestrator` subagent. Cross-reference `eu-funding-domain` for: funding rates (RIA=100%, IA=70%), TRL ranges (RIA=1-5, IA=5-8), typical budgets, consortium sizes, use cases. Save result to `tests/quality/results/prompt_036_ria_vs_ia.json`.

- [ ] FIX IF NEEDED: Read `tests/quality/results/prompt_036_ria_vs_ia.json`. If score < 85: fix and re-evaluate until passing or 3 attempts.

---

## Summary

| Section | Prompts | Focus Area |
|---------|---------|------------|
| 1 | 001-006 | General Introduction |
| 2 | 007-010 | Calls & Working Programmes |
| 3 | 011-016 | Geography & Eligibility |
| 4 | 017-022 | CORDIS Thematic Search |
| 5 | 023-028 | CORDIS Statistics |
| 6 | 029-034 | Partner Discovery |
| 7 | 035-036 | Comparisons |

**Total: 36 prompts × 2 tasks = 72 tasks**

---

## Post-Run Actions

After Ralphy completes all tasks:

1. Review `tests/quality/results/` for all JSON files
2. Generate summary report using `eval-orchestrator` batch mode:
   ```
   Evaluate batch results in tests/quality/results/*.json
   Provide summary with pass/fail counts and common issues
   ```
3. Check for any prompts that failed after 3 fix attempts
4. Document patterns in failures for future improvement
5. Consider adding regression tests using `mapit-testing` skill patterns

---

## Skill/Subagent Quick Reference

### When Fixing Failures

| Failure Type | Skill to Consult | What to Fix |
|--------------|------------------|-------------|
| Wrong funding rates | `eu-funding-domain` | Knowledge base or document chunks |
| Missing call details | `mapit-tools` | `search_funding_calls` tool |
| Missing project details | `mapit-tools`, `mapit-neo4j` | `search_projects` tool, graph queries |
| Wrong statistics | `mapit-neo4j` | Aggregation queries |
| Partner discovery gaps | `mapit-neo4j` | 2-hop queries, RRF fusion |
| Response too vague | `mapit-quality-eval` | V3ResponseFormatter |
| Missing comparisons | `mapit-tools` | `compare_programmes` tool |

### Subagent Pipeline

```
User Query
    ↓
[eval-orchestrator] (Opus)
    ├── calls → [query-decomposer] (Haiku) → components JSON
    └── calls → [quality-evaluator] (Sonnet) → scores JSON
    ↓
Evaluation Report (PASS/FAIL/NEEDS_REVIEW)
```