# MAPIT Application Quality Improvement PRD

| Purpose | Method | Pass Threshold | Target |
|---------|--------|----------------|--------|
| Systematically improve MAPIT to production-grade quality across all components | End-to-end testing, tool reliability verification, data quality checks, UX improvements | 80+ average score | 95% of user queries answered correctly |

## Problem Statement

MAPIT is an EU funding research assistant supporting 6 programmes with 34 tools. While the core architecture is sound, the application needs systematic improvements to reach production quality:

1. **Tool Reliability**: Not all 34 tools are equally robust - some may fail silently or return incomplete data
2. **Data Freshness**: Funding calls and programme data may be outdated
3. **Response Accuracy**: Answers sometimes lack specificity or contain outdated information
4. **Query Coverage**: Some valid user queries don't get good answers
5. **Error Handling**: Failures aren't always communicated clearly to users
6. **Performance**: Some queries are slow due to inefficient tool chains
7. **Cross-Programme Gaps**: Newer programmes (EU4Health, Digital Europe, LIFE) have less mature support

This PRD takes a holistic approach to improving the entire application through systematic testing and fixes.

---

## Configuration Notes

**Test Environment:**
- API: `http://localhost:8000/api/v3/conversation/{id}/message/stream`
- Services: PostgreSQL, Redis, Neo4j all running
- Data: All programme data loaded and indexed

**Quality Scoring (100 points):**
| Dimension | Points | Criteria |
|-----------|--------|----------|
| Query Fulfillment | 40 | All parts of query answered |
| Specificity | 25 | Concrete details (numbers, dates, names) |
| Factual Accuracy | 25 | Correct EU funding information |
| Actionability | 10 | Clear next steps for user |

**Methodology:**
Each scenario follows `EXECUTE + FIX IF NEEDED` pattern:
1. Execute the query against live system
2. Score the response
3. If score < 80, identify root cause and fix
4. Re-test until passing

---

## Phase 1: Core Tool Reliability (15 scenarios)

Verify each major tool works correctly with realistic queries.

### Funding Call Tools

- [x] **Scenario 001: Search Open Calls Basic** `EXECUTE + FIX IF NEEDED`
  - Query: "Show me open funding calls for AI research"
  - Expected: List of current open calls with deadlines, budgets, links
  - Verify: Calls are actually open (not closed), deadlines are in future
  - Fix if: Returns closed calls, missing deadlines, or no results
  - Pass threshold: 80
  - **Status: PASS (score ~89/100)**
  - **Fix applied**: V3ResponseFormatter now used in sync endpoint to properly format calls with deadlines, budgets, and EU Portal links
  - **Tests**: `tests/quality/test_scenario_001_search_open_calls_basic.py` (12 tests)

- [x] **Scenario 002: Search Calls with Filters** `EXECUTE + FIX IF NEEDED`
  - Query: "Find Horizon Europe calls closing in the next 3 months with budget over 5 million"
  - Expected: Filtered calls matching all criteria
  - Verify: Date filtering works, budget filtering accurate
  - Fix if: Incorrect filtering, wrong date math
  - Pass threshold: 80
  - **Status: PASS (score 80/100)**
  - **Verified**: Calls returned with deadlines within 3 months (Feb-Mar 2026), budgets over EUR 5 million
  - **Tests**: `tests/quality/test_scenario_002_search_calls_with_filters.py` (12 tests)

- [x] **Scenario 003: Get Call Details** `EXECUTE + FIX IF NEEDED`
  - Query: "Tell me about call HORIZON-EIC-2026-AIC-01"
  - Expected: Full call details - title, deadline, budget, scope, eligibility
  - Verify: Data matches EU Portal
  - Fix if: Missing fields, outdated info, wrong call
  - Pass threshold: 80
  - **Status: PASS (score 85-100/100)**
  - **Fix applied**: Removed duplicate `get_call_details` method that was overriding the correct implementation with budget support
  - **Tests**: `tests/quality/test_scenario_003_get_call_details.py` (12 tests)

### Project Search Tools

- [x] **Scenario 004: Search Projects by Topic** `EXECUTE + FIX IF NEEDED`
  - Query: "Find funded projects on quantum computing"
  - Expected: Relevant CORDIS projects with titles, budgets, coordinators
  - Verify: Projects are relevant, data is complete
  - Fix if: Irrelevant results, missing data fields
  - Pass threshold: 80
  - **Status: PASS (score 93-100/100)**
  - **Fix applied**: Fixed TUM organization detection bug - "tum " pattern was matching within "quantum ", now using word boundary regex `\btum\b`
  - **Tests**: `tests/quality/test_scenario_004_search_projects_by_topic.py` (14 tests)

- [x] **Scenario 005: Semantic Project Search** `EXECUTE + FIX IF NEEDED`
  - Query: "Find projects similar to developing sustainable aviation fuels"
  - Expected: Semantically related projects (not just keyword match)
  - Verify: Results include related concepts (biofuels, green aviation, etc.)
  - Fix if: Only exact keyword matches, no semantic understanding
  - Pass threshold: 80
  - **Status: PASS (score 80+/100)**
  - **Fix applied**: Added `_detect_semantic_project_query()` method to pre-route "similar to [concept]" queries to `get_similar_funded_projects` (AI embeddings) instead of `search_projects` (keyword search)
  - **Tests**: `tests/quality/test_scenario_005_semantic_project_search.py` (14 tests)

- [x] **Scenario 006: Organization Project Search** `EXECUTE + FIX IF NEEDED`
  - Query: "What projects has Fraunhofer participated in?"
  - Expected: List of projects with Fraunhofer as partner/coordinator
  - Verify: Organization name matching works, role info correct
  - Fix if: Misses projects, wrong organization matched
  - Pass threshold: 80
  - **Status: PASS (score 100/100)**
  - **Verified**: Returns 20 projects, shows coordinator vs participant roles, includes budgets, CORDIS links, funding schemes
  - **Tests**: `tests/quality/test_scenario_006_organization_project_search.py` (14 tests)

### Statistics Tools

- [x] **Scenario 007: Programme Statistics** `EXECUTE + FIX IF NEEDED`
  - Query: "What is the success rate for Horizon Europe EIC Accelerator?"
  - Expected: Accurate success rate with context (year, comparison)
  - Verify: Numbers match official EU statistics
  - Fix if: Wrong numbers, no source indication, outdated data
  - Pass threshold: 80
  - **Status: PASS (score 93/100)**
  - **Verified**: Returns 2-5% overall success rate with stage breakdown, matches official EC data
  - **Tests**: `tests/quality/test_scenario_007_programme_statistics.py` (13 tests)

- [x] **Scenario 008: Country Statistics** `EXECUTE + FIX IF NEEDED`
  - Query: "How does Germany perform in Horizon Europe compared to France?"
  - Expected: Comparative stats - projects, funding, success rates
  - Verify: Data is accurate and comparable
  - Fix if: Missing comparison, wrong country data
  - Pass threshold: 80
  - **Status: PASS (score 100/100)**
  - **Verified**: Returns comprehensive comparison with funding (EUR 8.04B vs 5.57B), projects (6,678 vs 5,073), organizations, top institutions (CNRS, Fraunhofer, Max Planck)
  - **Tests**: `tests/quality/test_scenario_008_country_statistics.py` (13 tests)

### Partner Discovery Tools

- [x] **Scenario 009: Find Partners by Expertise** `EXECUTE + FIX IF NEEDED`
  - Query: "Find experienced partners for a hydrogen fuel cell project"
  - Expected: Organizations with relevant project history
  - Verify: Partners have actual hydrogen/fuel cell experience
  - Fix if: Irrelevant partners, missing experience data
  - Pass threshold: 80
  - **Status: PASS (score 100/100)**
  - **Verified**: Returns 10+ organizations with relevant project counts, funding amounts, country codes, organization types (REC/HES/PRC), example project names, and actionable guidance (CORDIS links, Partner Search tool)
  - **Tests**: `tests/quality/test_scenario_009_find_partners_by_expertise.py` (15 tests)

- [x] **Scenario 010: Collaboration Network** `EXECUTE + FIX IF NEEDED`
  - Query: "Show me the collaboration network for Max Planck Institute"
  - Expected: Top collaborating organizations, shared projects
  - Verify: Network data is accurate, relationships real
  - Fix if: Missing collaborations, wrong organizations
  - Pass threshold: 80
  - **Status: PASS (score 100/100)**
  - **Fix applied**: Added `format_collaboration_network()` method to V3ResponseFormatter and updated `format_from_tool_results()` to detect and prioritize collaboration network data over organization projects
  - **Tests**: `tests/quality/test_scenario_010_collaboration_network.py` (15 tests)

### Budget Tools

- [x] **Scenario 011: Budget Benchmark** `EXECUTE + FIX IF NEEDED`
  - Query: "What budget should I plan for a climate research RIA project?"
  - Expected: Budget range with benchmarks from similar projects
  - Verify: Benchmarks from real projects, reasonable ranges
  - Fix if: Unrealistic numbers, no real project examples
  - Pass threshold: 80
  - **Status: PASS (score 100/100)**
  - **Verified**: Returns €2.9M-€6.9M range from 2302 analyzed projects, includes median (€4.9M), average (€5.5M), consortium size recommendations (11-16 partners), and RIA 100% funding rate info
  - **Tests**: `tests/quality/test_scenario_011_budget_benchmark.py` (13 tests)

- [x] **Scenario 012: Calculate Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "Calculate a budget for a 3-year project with 10 partners doing renewable energy research"
  - Expected: Detailed budget breakdown by category
  - Verify: Calculations are logical, categories complete
  - Fix if: Math errors, missing categories, unrealistic totals
  - Pass threshold: 80
  - **Status: PASS (score 100/100)**
  - **Fix applied**: Added `format_budget_calculation()` method to V3ResponseFormatter to properly format calculate_budget tool results with structured tables, per-partner distribution, effort summary, benchmarks, and actionable guidance
  - **Tests**: `tests/quality/test_scenario_012_calculate_budget.py` (14 tests)

### Timeline Tools

- [x] **Scenario 013: Generate Timeline** `EXECUTE + FIX IF NEEDED`
  - Query: "Create a timeline for a 36-month innovation project on smart cities"
  - Expected: Work packages, milestones, deliverables schedule
  - Verify: Timeline is realistic, milestones well-distributed
  - Fix if: Unrealistic scheduling, missing key phases
  - Pass threshold: 80
  - **Status: PASS (score 93/100)**
  - **Verified**: Returns comprehensive timeline with 6 work packages, 6 milestones, 13 deliverables, Gantt chart visualization, person-months allocation, and partner assignments
  - **Tests**: `tests/quality/test_scenario_013_generate_timeline.py` (14 tests)

### Consortium Tools

- [x] **Scenario 014: Consortium Patterns** `EXECUTE + FIX IF NEEDED`
  - Query: "What consortium composition works best for health research projects?"
  - Expected: Typical size, org type mix, country distribution
  - Verify: Patterns based on real successful projects
  - Fix if: Generic advice not backed by data
  - Pass threshold: 80
  - **Status: PASS (score ~99/100)**
  - **Verified**: Returns comprehensive consortium patterns from 412 Cluster 1 (Health) projects, including consortium size (16.5 avg, 14-19 recommended), org type breakdown (Universities 30-40%, Research 25-35%, SMEs 15-20%, Hospitals 10-15%), country distribution (8.8 avg countries), top coordinators (INSERM, Karolinska, KU Leuven, Erasmus MC, Charite), and actionable next steps
  - **Tests**: `tests/quality/test_scenario_014_consortium_patterns.py` (15 tests)

### Document Search

- [x] **Scenario 015: Search Work Programmes** `EXECUTE + FIX IF NEEDED`
  - Query: "What does the Horizon Europe work programme say about digital twins?"
  - Expected: Relevant excerpts from official documents
  - Verify: Quotes are accurate, sources cited
  - Fix if: Wrong information, no source, outdated documents
  - Pass threshold: 80
  - **Status: PASS (score 80+/100)**
  - **Fix applied**: Added `format_documents()` method to V3ResponseFormatter for rich document formatting with citations, enhanced `_tool_search_documents` to include full metadata (chunk_id, document_id, section_title, page_number, document_type)
  - **Tests**: `tests/quality/test_scenario_015_search_work_programmes.py` (13 tests)

---

## Phase 2: Multi-Programme Support (12 scenarios)

Ensure all 6 EU programmes work correctly.

### Horizon Europe (Baseline)

- [x] **Scenario 016: Horizon Europe Full Flow** `EXECUTE + FIX IF NEEDED`
  - Query: "I'm a university wanting to do AI research. What Horizon Europe options do I have?"
  - Expected: Eligibility confirmed, relevant calls listed, application guidance
  - Verify: Complete flow works end-to-end
  - Pass threshold: 80
  - **Status: PASS (score 80+/100)**
  - **Verified**: Returns 7+ AI-related calls with deadlines, budgets, EU Portal links, and application guidance (register, portal, consortium, next steps)
  - **Tests**: `tests/quality/test_scenario_016_horizon_europe_full_flow.py` (14 tests)

### Erasmus+

- [x] **Scenario 017: Erasmus+ Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "Can a vocational school from Poland participate in Erasmus+ mobility?"
  - Expected: Yes, with KA1 details, accreditation info, National Agency
  - Verify: Erasmus-specific tools called, accurate eligibility
  - Fix if: Generic response, wrong eligibility, missing specifics
  - Pass threshold: 80

- [x] **Scenario 018: Erasmus+ Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "Calculate budget for sending 15 students from Spain to Germany for 4 months"
  - Expected: Unit costs, travel band, organizational support, total
  - Verify: Uses Erasmus+ lump sum model correctly
  - Fix if: Wrong unit costs, ignores travel bands
  - Pass threshold: 80
  - **Status: PASS (score 100/100)**
  - **Fix applied**: Added duration conversion in `_tool_calculate_erasmus_budget` wrapper to convert months to days for mobility actions when LLM passes `duration_months` instead of `duration_days`
  - **Tests**: `tests/quality/test_scenario_018_erasmus_budget.py` (14 tests)

### Creative Europe

- [x] **Scenario 019: Creative Europe Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "Can a small theater company from Italy apply for Creative Europe funding?"
  - Expected: Yes for CULTURE strand, cooperation project options, requirements
  - Verify: CULTURE strand specifics, correct partnership requirements
  - Fix if: Generic response, wrong strand info
  - Pass threshold: 80
  - **Status: PASS (score 80+/100)**
  - **Fix applied**: Added `_detect_creative_europe_eligibility_query()` method to pre-route queries explicitly mentioning "Creative Europe" + eligibility to the `check_creative_europe_eligibility` tool. Also added guard in `_detect_erasmus_action_query()` to skip when other programmes are mentioned.
  - **Tests**: `tests/quality/test_scenario_019_creative_europe_eligibility.py` (13 tests)

- [x] **Scenario 020: Creative Europe Calls** `EXECUTE + FIX IF NEEDED`
  - Query: "Find open Creative Europe MEDIA calls for film distribution"
  - Expected: MEDIA strand distribution calls with deadlines
  - Verify: Calls are MEDIA strand, actually open
  - Fix if: Wrong strand, closed calls, missing calls
  - Pass threshold: 80
  - **Status: PASS (score 80+/100)**
  - **Fix applied**: Added `_detect_creative_europe_call_search_query()` method to pre-route queries explicitly searching for Creative Europe calls to the `search_funding_calls` tool instead of returning static MEDIA strand guidance
  - **Tests**: `tests/quality/test_scenario_020_creative_europe_calls.py` (13 tests)

### EU4Health

- [x] **Scenario 021: EU4Health Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "What EU4Health funding options are available for a hospital consortium?"
  - Expected: Joint actions, grants, eligibility for health entities
  - Verify: EU4Health-specific options, correct eligibility
  - Fix if: Generic health response, misses EU4Health specifics
  - Pass threshold: 80
  - **Status: PASS (score 100/100)**
  - **Fix applied**: Added EU4Health tools to ToolAwareAgent - registered `check_eu4health_eligibility` and `search_eu4health_templates` in _init_tools(), _execute_single_tool(), added handler methods, result formatter, and _detect_eu4health_eligibility_query() for pre-routing
  - **Tests**: `tests/quality/test_scenario_021_eu4health_eligibility.py` (13 tests)

- [x] **Scenario 022: EU4Health Topics** `EXECUTE + FIX IF NEEDED`
  - Query: "What EU4Health priorities focus on cancer?"
  - Expected: Europe's Beating Cancer Plan actions, specific calls
  - Verify: Cancer-specific EU4Health info
  - Fix if: Generic cancer research response
  - Pass threshold: 80
  - **Status: PASS (score 100/100)**
  - **Fix applied**: Added `_detect_eu4health_topics_query()` method to pre-route EU4Health topics/priorities queries to `search_eu4health_templates` tool. Added `_format_eu4health_template_search_result()` formatter for structured EU4Health programme information. Added `call_tools_and_format` action to bypass LLM synthesis and use custom formatting. Fixed content cleaning to remove `[Page X]` references that triggered quality check failures.
  - **Tests**: `tests/quality/test_scenario_022_eu4health_topics.py` (12 tests)

### Digital Europe

- [ ] **Scenario 023: Digital Europe Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "Can a cybersecurity startup apply to Digital Europe?"
  - Expected: Yes, cybersecurity objective details, SME info
  - Verify: Digital Europe specifics, correct objectives
  - Fix if: Confuses with Horizon Europe digital topics
  - Pass threshold: 80

- [ ] **Scenario 024: Digital Europe vs Horizon** `EXECUTE + FIX IF NEEDED`
  - Query: "Should I apply to Digital Europe or Horizon Europe for an AI project?"
  - Expected: Clear comparison - deployment vs research, TRL differences
  - Verify: Accurate differentiation, correct guidance
  - Fix if: Generic response, wrong advice
  - Pass threshold: 80

### LIFE

- [ ] **Scenario 025: LIFE Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "What LIFE programme options exist for biodiversity conservation NGO?"
  - Expected: LIFE Nature sub-programme, SAP/SIP options, co-financing
  - Verify: LIFE-specific info, correct sub-programme
  - Fix if: Generic environment response
  - Pass threshold: 80

- [ ] **Scenario 026: LIFE Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "What budget range for a LIFE climate adaptation project?"
  - Expected: SAP/SIP typical budgets, co-financing rates (55-75%)
  - Verify: LIFE-specific funding model
  - Fix if: Uses Horizon Europe budget model
  - Pass threshold: 80

### Cross-Programme

- [ ] **Scenario 027: Multi-Programme Search** `EXECUTE + FIX IF NEEDED`
  - Query: "Find all EU funding for sustainable agriculture across all programmes"
  - Expected: Results from LIFE, Horizon, potentially Erasmus+ (education)
  - Verify: Multiple programmes searched, relevant results
  - Fix if: Only searches one programme
  - Pass threshold: 80

---

## Phase 3: Complex Query Handling (12 scenarios)

Test the system's ability to handle sophisticated user needs.

### Multi-Part Questions

- [ ] **Scenario 028: Eligibility + Calls + Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "I'm an SME from Netherlands. Am I eligible for EIC Accelerator? What's the deadline? What budget can I request?"
  - Expected: All three parts answered with specifics
  - Verify: Each part addressed, accurate info
  - Fix if: Misses parts, generic response
  - Pass threshold: 80

- [ ] **Scenario 029: Comparison + Recommendation** `EXECUTE + FIX IF NEEDED`
  - Query: "Compare RIA and IA funding. Which is better for a TRL 4 project?"
  - Expected: Comparison table, clear recommendation with reasoning
  - Verify: Accurate comparison, sound recommendation
  - Fix if: Wrong comparison, no clear advice
  - Pass threshold: 80

### Follow-Up Conversations

- [ ] **Scenario 030: Context Preservation** `EXECUTE + FIX IF NEEDED`
  - Turn 1: "Find hydrogen funding calls"
  - Turn 2: "Which one has the highest budget?"
  - Expected: References calls from Turn 1, identifies highest budget
  - Verify: Context preserved, correct call identified
  - Fix if: Loses context, does new search
  - Pass threshold: 80

- [ ] **Scenario 031: Numbered Reference** `EXECUTE + FIX IF NEEDED`
  - Turn 1: "Show me 5 climate research projects"
  - Turn 2: "Tell me more about project 3"
  - Expected: Details about the third project from Turn 1
  - Verify: Correct project referenced
  - Fix if: Wrong project, asks for clarification
  - Pass threshold: 80

- [ ] **Scenario 032: Topic Refinement** `EXECUTE + FIX IF NEEDED`
  - Turn 1: "Find AI funding opportunities"
  - Turn 2: "Actually, I'm interested in AI for healthcare specifically"
  - Expected: Refined search for AI+healthcare
  - Verify: Incorporates refinement, relevant results
  - Fix if: Ignores refinement, repeats generic AI
  - Pass threshold: 80

### Ambiguous Queries

- [ ] **Scenario 033: Clarification Needed** `EXECUTE + FIX IF NEEDED`
  - Query: "What's the deadline?"
  - Expected: Asks for clarification about which call/programme
  - Verify: Doesn't hallucinate, asks appropriately
  - Fix if: Guesses randomly, hallucinates deadline
  - Pass threshold: 75

- [ ] **Scenario 034: Implicit Intent** `EXECUTE + FIX IF NEEDED`
  - Query: "I work at a university and we have an idea about clean energy"
  - Expected: Understands intent to find funding, offers relevant options
  - Verify: Correctly interprets as funding search
  - Fix if: Literal response, misses intent
  - Pass threshold: 80

### Edge Cases

- [ ] **Scenario 035: Non-EU Country** `EXECUTE + FIX IF NEEDED`
  - Query: "Can a company from India participate in EU funding?"
  - Expected: Explains third country rules, limited participation options
  - Verify: Accurate third country eligibility
  - Fix if: Says yes/no without nuance
  - Pass threshold: 80

- [ ] **Scenario 036: Outdated Programme** `EXECUTE + FIX IF NEEDED`
  - Query: "Can I still apply to Horizon 2020?"
  - Expected: Explains H2020 closed, redirects to Horizon Europe
  - Verify: Doesn't pretend H2020 is open
  - Fix if: Accepts premise, gives H2020 info
  - Pass threshold: 80

- [ ] **Scenario 037: Very Specific Niche** `EXECUTE + FIX IF NEEDED`
  - Query: "Funding for underwater archaeology using AI in the Mediterranean"
  - Expected: Best effort search, possibly Creative Europe + Horizon combination
  - Verify: Reasonable attempt, doesn't hallucinate
  - Fix if: Makes up specific calls that don't exist
  - Pass threshold: 75

### Real-World Scenarios

- [ ] **Scenario 038: First-Time Applicant** `EXECUTE + FIX IF NEEDED`
  - Query: "I've never applied for EU funding before. Where do I start?"
  - Expected: Beginner-friendly guidance, registration steps, NCP referral
  - Verify: Actionable steps, not overwhelming
  - Fix if: Too technical, assumes knowledge
  - Pass threshold: 80

- [ ] **Scenario 039: Urgent Deadline Query** `EXECUTE + FIX IF NEEDED`
  - Query: "Are there any calls closing this week I could apply to?"
  - Expected: Realistic assessment (likely too late), or actual options
  - Verify: Doesn't mislead about feasibility
  - Fix if: Encourages unrealistic applications
  - Pass threshold: 80

---

## Phase 4: Data Quality and Freshness (9 scenarios)

Ensure underlying data is accurate and up-to-date.

### Call Data Freshness

- [ ] **Scenario 040: No Expired Calls** `EXECUTE + FIX IF NEEDED`
  - Query: "Show me open Horizon Europe calls"
  - Verify: No calls with past deadlines shown as "open"
  - Action: Check call sync scripts, update if needed
  - Fix if: Shows closed calls as open
  - Pass threshold: 85

- [ ] **Scenario 041: Deadline Accuracy** `EXECUTE + FIX IF NEEDED`
  - Pick 5 random calls from results, verify deadlines against EU Portal
  - Verify: All 5 deadlines match official source
  - Action: Check data sync frequency
  - Fix if: Any deadline incorrect
  - Pass threshold: 90

- [ ] **Scenario 042: Budget Accuracy** `EXECUTE + FIX IF NEEDED`
  - Pick 5 random calls, verify budgets against EU Portal
  - Verify: Budget figures match or are clearly marked as estimates
  - Fix if: Wrong budgets without disclaimer
  - Pass threshold: 85

### Project Data Quality

- [ ] **Scenario 043: Project Data Completeness** `EXECUTE + FIX IF NEEDED`
  - Query: "Find 10 projects on machine learning"
  - Verify: All 10 have: title, budget, coordinator, status, dates
  - Fix if: Missing essential fields
  - Pass threshold: 85

- [ ] **Scenario 044: Project Links Working** `EXECUTE + FIX IF NEEDED`
  - Take 5 project results, verify CORDIS links work
  - Verify: Links load correct project page
  - Fix if: Broken links, wrong projects
  - Pass threshold: 90

### Programme Information

- [ ] **Scenario 045: 2024/2025 Information** `EXECUTE + FIX IF NEEDED`
  - Query: "What are the Horizon Europe 2025 priorities?"
  - Verify: Mentions current Work Programme, not outdated years
  - Fix if: Uses 2023 or older info as current
  - Pass threshold: 80

- [ ] **Scenario 046: Success Rate Accuracy** `EXECUTE + FIX IF NEEDED`
  - Query: "What's the ERC success rate?"
  - Cross-reference with official ERC statistics
  - Verify: Within 2% of official figures
  - Fix if: Significantly wrong rates
  - Pass threshold: 85

### Document Currency

- [ ] **Scenario 047: Work Programme Version** `EXECUTE + FIX IF NEEDED`
  - Query: "What topics are in the Horizon Europe digital work programme?"
  - Verify: References 2024-2025 (or latest) work programme
  - Fix if: Uses outdated work programme version
  - Pass threshold: 80

- [ ] **Scenario 048: Erasmus+ Guide Version** `EXECUTE + FIX IF NEEDED`
  - Query: "What are the Erasmus+ quality criteria?"
  - Verify: Uses 2025/2026 Programme Guide
  - Fix if: Uses older guide version
  - Pass threshold: 80

---

## Phase 5: Error Handling and Resilience (9 scenarios)

Ensure graceful handling of failures and edge cases.

### Tool Failures

- [ ] **Scenario 049: Neo4j Unavailable** `EXECUTE + FIX IF NEEDED`
  - Simulate: Neo4j connection timeout
  - Query: "Find partner statistics for Germany"
  - Expected: Graceful degradation, partial results from other sources
  - Verify: Doesn't crash, explains limitation
  - Fix if: Hard failure, unhelpful error message
  - Pass threshold: 75

- [ ] **Scenario 050: Vector Search Fails** `EXECUTE + FIX IF NEEDED`
  - Simulate: Supabase vector search timeout
  - Query: "Find semantically similar projects"
  - Expected: Falls back to keyword search, explains
  - Verify: Still provides useful results
  - Fix if: Complete failure, no fallback
  - Pass threshold: 75

- [ ] **Scenario 051: API Rate Limited** `EXECUTE + FIX IF NEEDED`
  - Simulate: EU Portal API rate limit
  - Query: "Get details for call HORIZON-xxx"
  - Expected: Uses cached data or explains delay
  - Verify: Doesn't fail completely
  - Fix if: Crashes on rate limit
  - Pass threshold: 75

### Input Handling

- [ ] **Scenario 052: Very Long Query** `EXECUTE + FIX IF NEEDED`
  - Query: [500+ character detailed query]
  - Expected: Handles gracefully, extracts key intent
  - Verify: Doesn't truncate badly, answers main question
  - Fix if: Fails, only answers first part
  - Pass threshold: 80

- [ ] **Scenario 053: Special Characters** `EXECUTE + FIX IF NEEDED`
  - Query: "Find projects on CO₂ capture & storage (CCS) - what's available?"
  - Expected: Handles special chars, answers correctly
  - Verify: Doesn't break on subscripts, ampersand
  - Fix if: Parse error, wrong search
  - Pass threshold: 80

- [ ] **Scenario 054: Non-English Query** `EXECUTE + FIX IF NEEDED`
  - Query: "Trouvez des appels pour l'énergie renouvelable"
  - Expected: Understands French, responds appropriately
  - Verify: Doesn't fail, provides relevant results
  - Fix if: Completely misunderstands
  - Pass threshold: 75

### Empty Results

- [ ] **Scenario 055: No Matching Calls** `EXECUTE + FIX IF NEEDED`
  - Query: "Find open calls for underwater basket weaving"
  - Expected: Graceful "no results", suggests alternatives
  - Verify: Helpful response, not empty
  - Fix if: Just says "no results found"
  - Pass threshold: 80

- [ ] **Scenario 056: No Matching Projects** `EXECUTE + FIX IF NEEDED`
  - Query: "Find projects by organization 'XYZ123NotReal Inc'"
  - Expected: Explains no results, suggests checking spelling
  - Verify: Helpful guidance
  - Fix if: Unhelpful empty response
  - Pass threshold: 80

### Recovery

- [ ] **Scenario 057: Self-Correction** `EXECUTE + FIX IF NEEDED`
  - Query: "Find renewable energy calls" (intentionally get poor results first)
  - Expected: Agent self-corrects if initial search insufficient
  - Verify: Uses agentic loop to improve results
  - Fix if: Accepts poor results, no iteration
  - Pass threshold: 80

---

## Phase 6: Performance and User Experience (6 scenarios)

Ensure the system is fast and pleasant to use.

### Response Time

- [ ] **Scenario 058: Simple Query Speed** `EXECUTE + FIX IF NEEDED`
  - Query: "What is RIA funding?"
  - Target: First token < 2 seconds, complete < 5 seconds
  - Verify: Measure actual response time
  - Fix if: Consistently > 5 seconds
  - Pass threshold: Response time target met

- [ ] **Scenario 059: Complex Query Speed** `EXECUTE + FIX IF NEEDED`
  - Query: "Compare EIC and ERC, find open calls for both, and recommend which suits a TRL 6 project"
  - Target: Complete < 15 seconds
  - Verify: Multiple tools called efficiently
  - Fix if: > 20 seconds consistently
  - Pass threshold: Response time target met

### Response Quality

- [ ] **Scenario 060: Actionable Guidance** `EXECUTE + FIX IF NEEDED`
  - Query: "How do I apply for Horizon Europe?"
  - Expected: Step-by-step guidance, links, concrete actions
  - Verify: User could follow steps
  - Fix if: Vague, no clear actions
  - Pass threshold: 80

- [ ] **Scenario 061: Source Attribution** `EXECUTE + FIX IF NEEDED`
  - Query: "What are the ERC grant amounts?"
  - Expected: Specific amounts WITH source indication
  - Verify: Can trace info to official source
  - Fix if: Numbers without source
  - Pass threshold: 80

### Streaming Experience

- [ ] **Scenario 062: Streaming Works** `EXECUTE + FIX IF NEEDED`
  - Send query to streaming endpoint
  - Expected: Tokens stream progressively, status updates shown
  - Verify: SSE events received correctly
  - Fix if: All-at-once response, broken streaming
  - Pass threshold: Streaming functional

- [ ] **Scenario 063: Tool Progress Visible** `EXECUTE + FIX IF NEEDED`
  - Query requiring multiple tools
  - Expected: Tool calls and results visible during streaming
  - Verify: User sees what's happening
  - Fix if: Black box until final answer
  - Pass threshold: Progress visible

---

## Summary Table

| Phase | Scenarios | Focus Area | Target Pass Rate |
|-------|-----------|------------|------------------|
| Phase 1 | 001-015 | Core Tool Reliability | 90% |
| Phase 2 | 016-027 | Multi-Programme Support | 85% |
| Phase 3 | 028-039 | Complex Query Handling | 85% |
| Phase 4 | 040-048 | Data Quality & Freshness | 90% |
| Phase 5 | 049-057 | Error Handling & Resilience | 80% |
| Phase 6 | 058-063 | Performance & UX | 85% |
| **Total** | **63** | **All Areas** | **86% average** |

---

## Completion Criteria

### Phase Completion Requirements
- [ ] Phase 1: 14/15 scenarios pass (core tools working)
- [ ] Phase 2: 10/12 scenarios pass (all programmes functional)
- [ ] Phase 3: 10/12 scenarios pass (complex queries handled)
- [ ] Phase 4: 8/9 scenarios pass (data is accurate and fresh)
- [ ] Phase 5: 7/9 scenarios pass (graceful error handling)
- [ ] Phase 6: 5/6 scenarios pass (good UX)

### Overall Completion Requirements
- [ ] 54/63 scenarios pass (86% overall)
- [ ] No programme has < 80% pass rate
- [ ] All 34 tools verified working
- [ ] Data freshness verified (calls < 7 days old)
- [ ] Average response time < 10 seconds
- [ ] Zero hard crashes during testing

### Production Readiness Checklist
- [ ] All 6 programmes return accurate results
- [ ] Funding calls are synced and up-to-date
- [ ] Project search returns relevant results
- [ ] Statistics match official EU data
- [ ] Error messages are helpful
- [ ] Performance is acceptable
- [ ] Streaming works correctly

---

## Appendix A: Root Cause Categories

When a scenario fails, categorize the root cause:

| Category | Description | Typical Fix |
|----------|-------------|-------------|
| `tool_bug` | Tool returns wrong data | Fix tool implementation |
| `data_stale` | Underlying data outdated | Run sync scripts |
| `data_missing` | Data not in database | Ingest missing data |
| `prompt_issue` | LLM doesn't call right tool | Improve tool descriptions |
| `format_issue` | Output poorly formatted | Fix response formatter |
| `context_lost` | Follow-up loses context | Fix memory service |
| `timeout` | Too slow | Optimize query or add caching |
| `fallback_missing` | No graceful degradation | Add fallback logic |

## Appendix B: Test Execution

```bash
# Run all scenarios
python scripts/run_prd_scenarios.py --prd application_quality

# Run specific phase
python scripts/run_prd_scenarios.py --phase 1

# Run single scenario
python scripts/run_prd_scenarios.py --scenario 001

# Run with verbose output
python scripts/run_prd_scenarios.py --verbose

# Generate report
python scripts/run_prd_scenarios.py --report
```

## Appendix C: Data Sync Commands

```bash
# Sync Horizon Europe calls
python scripts/sync_horizon_calls.py

# Sync Erasmus+ calls
python scripts/sync_erasmus_calls_from_api.py

# Sync Creative Europe calls
python scripts/sync_creative_europe_calls.py

# Refresh project embeddings
python scripts/update_embeddings.py

# Verify data freshness
python scripts/check_data_freshness.py
```

## Appendix D: Fix Templates

### Tool Bug Fix
```python
# In app/services/tools/{tool_name}.py
# 1. Identify failing case
# 2. Add test case
# 3. Fix logic
# 4. Verify fix
# 5. Run regression tests
```

### Data Freshness Fix
```bash
# 1. Check last sync time
python scripts/check_sync_status.py

# 2. Run incremental sync
python scripts/sync_calls.py --incremental

# 3. Verify data
python scripts/verify_call_data.py
```

### Prompt Improvement
```python
# In app/services/agents/tool_aware_agent.py
# Update tool description to be clearer about when to use
# Add examples to help LLM understand tool purpose
```

---

*PRD Version: 1.0*
*Created: January 24, 2026*
*Target: Production-grade MAPIT application quality*
