# MAPIT V3 Response Formatter Production Readiness PRD

| Purpose | Method | Pass Threshold | Target |
|---------|--------|----------------|--------|
| Make V3ResponseFormatter production-ready with comprehensive tool output formatting for all 34 tools | Add formatters for each tool category, test with quality scoring | 80+ average score across formatted outputs | 95% coverage of tool outputs |

## Problem Statement

The current `V3ResponseFormatter` (`app/services/response/v3_response_formatter.py`) only handles:
- **Funding calls** (`format_funding_calls`)
- **Projects** (`format_projects`)
- **Organization projects** (`format_organization_projects`)

However, the system has **34 tools** that return diverse result types. Most tool outputs are passed directly to the LLM without structured formatting, resulting in:
- Inconsistent response quality across different query types
- Missing actionable guidance for users
- No rich formatting (emojis, links, structured data) for many result types
- Programme-specific details lost in generic responses
- Poor discoverability of next steps and resources

### Current Coverage Gap

| Tool Category | Tools | Currently Formatted | Gap |
|---------------|-------|---------------------|-----|
| Funding Calls | 2 | ✅ Yes | - |
| Projects | 5 | ✅ Yes | - |
| Statistics | 2 | ❌ No | Needs formatter |
| Budget Tools | 4 | ❌ No | Needs formatter |
| Timeline Tools | 1 | ❌ No | Needs formatter |
| Eligibility | 6 | ❌ No | Needs formatter |
| Partner Discovery | 3 | ❌ No | Needs formatter |
| Consortium Tools | 2 | ❌ No | Needs formatter |
| Document Search | 7 | ❌ No | Needs formatter |
| Multi-Programme | 2 | ❌ No | Needs formatter |

---

## Configuration Notes

**Target File:** `app/services/response/v3_response_formatter.py`

**Integration Point:** `app/services/agents/tool_aware_agent.py` - The `format_from_tool_results()` method is called to format tool outputs before LLM synthesis.

**Testing:**
- Quality scoring using `QualityEvaluatorAgent`
- Response pattern validation
- Structured output verification

**Design Principles:**
1. **Programme-Aware**: Different formatting for different EU programmes
2. **Actionable**: Always include clear next steps
3. **Data-Rich**: Include numbers, dates, links, amounts
4. **Consistent**: Same formatting patterns across similar content types
5. **Accessible**: Clear structure, screen-reader friendly

---

## Phase 1: Statistics and Comparison Formatters (6 scenarios)

Add formatters for statistics and comparison tool outputs.

### Statistics Formatter

- [ ] **Scenario 001: Format Programme Statistics** `EXECUTE`
  - Implement `format_programme_statistics(result: dict) -> str`
  - Input: Programme name, success rate, total projects, total funding, country breakdown
  - Output: Rich formatted statistics with visual indicators
  - Expected format:
    ```
    ## Horizon Europe Statistics

    📊 **Overview**
    - **Success Rate:** 15.2% (vs 14.8% EU average)
    - **Total Projects:** 13,865
    - **Total Funding:** €45.6 billion

    🏆 **Top Countries by Participation**
    1. 🇩🇪 Germany - 2,456 projects (€8.2B)
    2. 🇫🇷 France - 1,892 projects (€6.1B)
    ...

    🎯 **Next Steps:**
    • Compare with other programmes using `compare_programmes`
    • Find projects in your research area
    ```
  - Pass threshold: 80

- [ ] **Scenario 002: Format Country Statistics** `EXECUTE + FIX IF NEEDED`
  - Implement `format_country_statistics(result: dict) -> str`
  - Input: Country name, participation stats, success rates, funding received
  - Output: Country-focused statistics card
  - Include: Comparison to EU average, top research areas, coordination rate
  - Pass threshold: 80

### Comparison Formatter

- [ ] **Scenario 003: Format Programme Comparison** `EXECUTE + FIX IF NEEDED`
  - Implement `format_programme_comparison(result: dict) -> str`
  - Input: Two programme objects with stats
  - Output: Side-by-side comparison table
  - Expected format:
    ```
    ## Comparing EIC Accelerator vs RIA

    | Aspect | EIC Accelerator | RIA |
    |--------|-----------------|-----|
    | Focus | Single SME innovation | Collaborative research |
    | Funding Rate | 70% grant + equity | 100% grant |
    | Success Rate | ~8% | ~15% |
    | Budget Range | €0.5-2.5M | €2-10M |

    💡 **Which to Choose?**
    - Choose **EIC** if: Single SME, market-ready product (TRL 5-8)
    - Choose **RIA** if: Consortium, fundamental research (TRL 2-5)
    ```
  - Pass threshold: 80

- [ ] **Scenario 004: Format Multi-Programme Comparison** `EXECUTE + FIX IF NEEDED`
  - Extend comparison formatter for 3+ programmes
  - Handle Creative Europe vs Erasmus+ vs Horizon Europe
  - Include programme-specific icons and colors
  - Pass threshold: 80

### Integration Test

- [ ] **Scenario 005: Statistics Auto-Detection** `EXECUTE + FIX IF NEEDED`
  - Update `format_from_tool_results()` to detect statistics results
  - Key detection: `success_rate`, `total_projects`, `total_funding` fields
  - Verify routing to correct formatter
  - Pass threshold: 80

- [ ] **Scenario 006: Comparison Auto-Detection** `EXECUTE + FIX IF NEEDED`
  - Update `format_from_tool_results()` to detect comparison results
  - Key detection: `programme_a`, `programme_b`, or `comparison` fields
  - Verify routing to correct formatter
  - Pass threshold: 80

---

## Phase 2: Budget and Timeline Formatters (8 scenarios)

Add formatters for proposal planning tools.

### Budget Formatter

- [ ] **Scenario 007: Format Budget Benchmark** `EXECUTE + FIX IF NEEDED`
  - Implement `format_budget_benchmark(result: dict) -> str`
  - Input: Statistics (min, max, avg, median), recommendations, sample projects
  - Output: Rich budget guidance with benchmarks
  - Expected format:
    ```
    ## Budget Benchmark Analysis

    💰 **Similar Projects Budget Range**
    - Minimum: €1.2M
    - Maximum: €12.5M
    - **Median: €4.8M** (recommended target)
    - Average: €5.2M

    📊 **Budget by Organization Type**
    | Type | Avg Budget Share |
    |------|------------------|
    | Universities (HES) | 35% |
    | Research Orgs (REC) | 28% |
    | Industry (PRC) | 25% |
    | Public Bodies (PUB) | 12% |

    📁 **Reference Projects**
    1. PROJECT_X (€4.5M) - 12 partners
    2. PROJECT_Y (€5.1M) - 15 partners

    🎯 **Recommendation:** Target €4-5M for a consortium of 10-15 partners
    ```
  - Pass threshold: 80

- [ ] **Scenario 008: Format Calculated Budget** `EXECUTE + FIX IF NEEDED`
  - Implement `format_calculated_budget(result: dict) -> str`
  - Input: Total cost, EU contribution, breakdown by category
  - Output: Budget table with category percentages
  - Include: Personnel, equipment, travel, subcontracting, other direct, indirect costs
  - Pass threshold: 80

- [ ] **Scenario 009: Format Erasmus+ Budget** `EXECUTE + FIX IF NEEDED`
  - Extend budget formatter for Erasmus+ lump sum model
  - Include: Unit costs, travel bands, organizational support
  - Programme-specific icons and terminology
  - Pass threshold: 80

- [ ] **Scenario 010: Format Creative Europe Budget** `EXECUTE + FIX IF NEEDED`
  - Extend budget formatter for Creative Europe co-financing
  - Include: Funding rates by strand (60-80%), co-financing requirements
  - MEDIA vs CULTURE vs Cross-sectoral differences
  - Pass threshold: 80

### Timeline Formatter

- [ ] **Scenario 011: Format Generated Timeline** `EXECUTE + FIX IF NEEDED`
  - Implement `format_timeline(result: dict) -> str`
  - Input: Work packages, deliverables, milestones, duration context
  - Output: Visual timeline representation
  - Expected format:
    ```
    ## Project Timeline (36 months)

    📅 **Work Packages**

    **WP1: Project Management** (M1-M36)
    └── Lead: Coordinator | Effort: 24 PM

    **WP2: Research & Development** (M1-M24)
    └── Lead: Partner 2 | Effort: 120 PM
    ├── D2.1: Literature Review (M6)
    └── D2.2: Prototype v1 (M18)

    **WP3: Pilot & Validation** (M18-M36)
    └── Lead: Partner 3 | Effort: 80 PM

    🏁 **Key Milestones**
    - M12: Proof of Concept Complete ✅
    - M24: Pilot Deployment Ready 🔄
    - M36: Final Results Published 🎯

    📊 **Duration Context**
    Your 36-month duration is typical for RIA projects (avg: 41 months)
    ```
  - Pass threshold: 80

- [ ] **Scenario 012: Format Duration Analysis** `EXECUTE + FIX IF NEEDED`
  - Include comparison to similar projects
  - Add cluster-specific duration patterns
  - Visual timeline bar representation
  - Pass threshold: 80

### Integration Test

- [ ] **Scenario 013: Budget Auto-Detection** `EXECUTE + FIX IF NEEDED`
  - Update `format_from_tool_results()` to detect budget results
  - Key detection: `calculated_budget`, `budget_breakdown`, `statistics` with budget fields
  - Handle both benchmark and calculation results
  - Pass threshold: 80

- [ ] **Scenario 014: Timeline Auto-Detection** `EXECUTE + FIX IF NEEDED`
  - Update `format_from_tool_results()` to detect timeline results
  - Key detection: `work_packages`, `deliverables`, `milestones` fields
  - Verify routing to timeline formatter
  - Pass threshold: 80

---

## Phase 3: Eligibility Formatters (8 scenarios)

Add formatters for all 6 programme eligibility tools.

### Programme-Specific Eligibility

- [ ] **Scenario 015: Format Horizon Europe Eligibility** `EXECUTE + FIX IF NEEDED`
  - Implement `format_eligibility_result(result: dict, programme: str) -> str`
  - Input: Eligibility status, requirements, consortium rules
  - Output: Clear eligibility checklist
  - Expected format:
    ```
    ## Eligibility Check: Horizon Europe RIA

    ✅ **You ARE Eligible**

    📋 **Eligibility Requirements**
    - [x] Legal entity in EU Member State or Associated Country
    - [x] Organization type: Higher Education Institution
    - [x] Not excluded from EU funding

    👥 **Consortium Requirements**
    - Minimum: 3 independent entities from 3 different countries
    - At least 1 entity from EU Member State
    - [x] Your organization can be coordinator

    💡 **Important Notes**
    • EIC Accelerator has different rules (single SME can apply)
    • Associated Countries list updated in 2024

    🎯 **Next Steps:**
    • Register in Participant Register (get PIC)
    • Find consortium partners
    • Check specific call conditions
    ```
  - Pass threshold: 80

- [ ] **Scenario 016: Format Erasmus+ Eligibility** `EXECUTE + FIX IF NEEDED`
  - Erasmus+-specific eligibility formatting
  - Include: Key Action (KA1/KA2/KA3), Sector (HED/VET/SCH/ADU/YOU)
  - Accreditation requirements, National Agency info
  - Pass threshold: 80

- [ ] **Scenario 017: Format Creative Europe Eligibility** `EXECUTE + FIX IF NEEDED`
  - Creative Europe-specific formatting
  - Include: Strand (CULTURE/MEDIA/Cross-sectoral), Action type
  - Geographic eligibility, cultural operator requirements
  - Pass threshold: 80

- [ ] **Scenario 018: Format EU4Health Eligibility** `EXECUTE + FIX IF NEEDED`
  - EU4Health-specific formatting
  - Include: Action types (grants, joint actions, procurement)
  - Health entity requirements, public health focus
  - Pass threshold: 80

- [ ] **Scenario 019: Format Digital Europe Eligibility** `EXECUTE + FIX IF NEEDED`
  - Digital Europe-specific formatting
  - Include: Specific Objectives (AI, HPC, Cybersecurity, Skills, Deployment)
  - SME focus, digital capacity requirements
  - Pass threshold: 80

- [ ] **Scenario 020: Format LIFE Eligibility** `EXECUTE + FIX IF NEEDED`
  - LIFE programme-specific formatting
  - Include: Sub-programmes (Nature, Circular Economy, Climate Mitigation, Climate Adaptation)
  - Co-financing requirements, environmental focus
  - Pass threshold: 80

### Eligibility Constants

- [ ] **Scenario 021: Add Programme-Specific Action Types** `EXECUTE + FIX IF NEEDED`
  - Extend `VALID_ACTION_TYPES` for all programmes
  - Add: Erasmus+ (KA1, KA2, KA3, JMO, SPORT)
  - Add: Creative Europe (COOP-S, COOP-M, COOP-L, DEV, DIST)
  - Add: EU4Health, Digital Europe, LIFE action types
  - Pass threshold: 80

- [ ] **Scenario 022: Add Programme-Specific Icons** `EXECUTE + FIX IF NEEDED`
  - Extend `TYPE_ICONS` with programme-specific icons
  - Erasmus+: 🎓 (education), ✈️ (mobility), 🤝 (partnership)
  - Creative Europe: 🎭 (culture), 🎬 (media), 🎨 (arts)
  - EU4Health: 🏥 (health), 💊 (pharma), 🧬 (research)
  - Digital Europe: 💻 (digital), 🔒 (cyber), 🤖 (AI)
  - LIFE: 🌿 (nature), ♻️ (circular), 🌡️ (climate)
  - Pass threshold: 80

---

## Phase 4: Partner and Consortium Formatters (8 scenarios)

Add formatters for partner discovery and consortium tools.

### Partner Discovery Formatter

- [ ] **Scenario 023: Format Partner Discovery Results** `EXECUTE + FIX IF NEEDED`
  - Implement `format_partner_discovery(result: dict) -> str`
  - Input: Partners list with experience, projects, contact info
  - Output: Partner cards with relevance scores
  - Expected format:
    ```
    ## Experienced Partners in Hydrogen Research

    🔍 **Found 15 Potential Partners**

    ### 1. Max Planck Institute (Germany) ⭐⭐⭐⭐⭐
    **Relevance Score:** 95%
    - **Type:** Research Organization (REC)
    - **Experience:** 12 projects in hydrogen/fuel cells
    - **Recent Projects:** HydrogenHub (2024), FuelCell2030 (2023)
    - **Coordinator Experience:** 4 projects
    📧 Contact via CORDIS

    ### 2. TU Delft (Netherlands) ⭐⭐⭐⭐
    **Relevance Score:** 88%
    ...

    📊 **Search Metadata**
    - Sources: Graph (15) + SQL (12) → Merged (20)
    - Clusters searched: CLUSTER-5 (Climate, Energy)

    🎯 **Next Steps:**
    • Contact top partners via CORDIS project pages
    • Send Letter of Intent with project concept
    • Use Partner Search tool on EU Portal
    ```
  - Pass threshold: 80

- [ ] **Scenario 024: Format Collaboration Network** `EXECUTE + FIX IF NEEDED`
  - Implement `format_collaboration_network(result: dict) -> str`
  - Input: Network graph data, top collaborators
  - Output: Network visualization summary
  - Include: Most frequent partners, shared projects count
  - Pass threshold: 80

### Consortium Patterns Formatter

- [ ] **Scenario 025: Format Consortium Patterns** `EXECUTE + FIX IF NEEDED`
  - Implement `format_consortium_patterns(result: dict) -> str`
  - Input: Consortium size stats, org type distribution, templates
  - Output: Consortium composition guidance
  - Expected format:
    ```
    ## Consortium Patterns for Climate Research

    👥 **Typical Consortium Size**
    - Average Partners: 12.5
    - Average Countries: 8.2
    - Coordinator typically from: DE, NL, ES

    📊 **Organization Type Mix**
    | Type | Share | Typical Role |
    |------|-------|--------------|
    | HES (Universities) | 35% | Research lead |
    | REC (Research Orgs) | 28% | Technical WPs |
    | PRC (Industry) | 25% | Exploitation |
    | PUB (Public) | 12% | Policy/Demo |

    🏆 **Successful Templates**
    1. **HydrogenHub** - 15 partners, 8 countries
       - 5 HES, 4 REC, 4 PRC, 2 PUB
    2. **ClimateAction** - 12 partners, 6 countries

    🎯 **Recommendation:**
    Build a consortium with 10-15 partners from 6-8 countries
    ```
  - Pass threshold: 80

- [ ] **Scenario 026: Format Coordinator Analysis** `EXECUTE + FIX IF NEEDED`
  - Include top coordinators section
  - Coordinator success rates
  - Countries with strongest coordination track record
  - Pass threshold: 80

### Similar Projects Formatter

- [ ] **Scenario 027: Format Similar Projects** `EXECUTE + FIX IF NEEDED`
  - Implement `format_similar_projects(result: dict) -> str`
  - Input: Similar projects with similarity scores, graph context
  - Output: Relevance-sorted project cards
  - Include: Similarity score, cluster alignment, consortium insights
  - Pass threshold: 80

- [ ] **Scenario 028: Format Semantic Similarity Results** `EXECUTE + FIX IF NEEDED`
  - Handle vector search results with embeddings
  - Show conceptual alignment explanations
  - Include: Why projects are similar (objectives, methods)
  - Pass threshold: 80

### Integration Test

- [ ] **Scenario 029: Partner Results Auto-Detection** `EXECUTE + FIX IF NEEDED`
  - Update `format_from_tool_results()` for partner results
  - Key detection: `partners`, `experienced_partners`, `collaboration_network`
  - Pass threshold: 80

- [ ] **Scenario 030: Consortium Results Auto-Detection** `EXECUTE + FIX IF NEEDED`
  - Update `format_from_tool_results()` for consortium results
  - Key detection: `consortium_size`, `org_type_distribution`, `successful_templates`
  - Pass threshold: 80

---

## Phase 5: Document Search Formatters (6 scenarios)

Add formatters for document and template search results.

### Document Search Formatter

- [ ] **Scenario 031: Format Document Search Results** `EXECUTE + FIX IF NEEDED`
  - Implement `format_document_search(result: dict) -> str`
  - Input: Document chunks with sources, relevance scores
  - Output: Organized document references
  - Expected format:
    ```
    ## Relevant Documents Found

    📚 **5 Documents Match Your Query**

    ### 1. Horizon Europe Work Programme 2024-2025 (Cluster 5)
    **Relevance:** 95% | **Source:** Official EU Publication
    > "Projects should demonstrate novel approaches to hydrogen
    > production with efficiency targets of 75% or higher..."
    📄 [View Full Document](link)

    ### 2. Annotated Model Grant Agreement
    **Relevance:** 88% | **Source:** EC Guidance
    > "Personnel costs eligible under actual cost model..."
    📄 [View Full Document](link)

    💡 **Key Takeaways:**
    • Efficiency targets for hydrogen: 75%+
    • Personnel costs: Use actual cost model
    ```
  - Pass threshold: 80

- [ ] **Scenario 032: Format Erasmus+ Template Search** `EXECUTE + FIX IF NEEDED`
  - Erasmus+-specific document formatting
  - Programme Guide sections with action-specific guidance
  - Include: Quality criteria weights, eligible activities
  - Pass threshold: 80

- [ ] **Scenario 033: Format Creative Europe Template Search** `EXECUTE + FIX IF NEEDED`
  - Creative Europe-specific document formatting
  - CulturEU Guide references, Work Programme sections
  - Include: Strand-specific requirements
  - Pass threshold: 80

- [ ] **Scenario 034: Format Multi-Programme Documents** `EXECUTE + FIX IF NEEDED`
  - Handle documents from multiple programmes
  - Group by programme, show cross-references
  - Include: Programme-specific icons
  - Pass threshold: 80

### Call History Formatter

- [ ] **Scenario 035: Format Call History Analysis** `EXECUTE + FIX IF NEEDED`
  - Implement `format_call_history(result: dict) -> str`
  - Input: Timeline data, trends, topic evolution
  - Output: Historical trend analysis
  - Include: Year-over-year changes, funding trends, topic shifts
  - Pass threshold: 80

- [ ] **Scenario 036: Format Topic Evolution** `EXECUTE + FIX IF NEEDED`
  - Visualize how topics have evolved over years
  - Show funding trend direction (increasing/stable/decreasing)
  - Include predictions based on patterns
  - Pass threshold: 80

---

## Phase 6: Multi-Programme Search Formatters (6 scenarios)

Add formatters for cross-programme search and recommendations.

### Multi-Programme Search Formatter

- [ ] **Scenario 037: Format Multi-Programme Search** `EXECUTE + FIX IF NEEDED`
  - Implement `format_multi_programme_search(result: dict) -> str`
  - Input: Results from multiple programmes with scores
  - Output: Programme-grouped results
  - Expected format:
    ```
    ## Funding Opportunities Across All Programmes

    🔍 **Found 28 opportunities for "climate adaptation"**

    ### 🌿 LIFE Programme (8 results)
    1. LIFE-2024-SAP-CLIMA - Climate Adaptation Projects
       - Deadline: 15 Sep 2024 | Budget: €30M
    2. ...

    ### 🔬 Horizon Europe (12 results)
    1. HORIZON-CL5-2024-D1-01 - Climate Services
       - Deadline: 07 Feb 2024 | Budget: €50M
    2. ...

    ### 🏥 EU4Health (3 results)
    1. EU4H-2024-PJ-4 - Climate and Health
    ...

    💡 **Programme Comparison for Your Topic:**
    | Programme | Opportunities | Total Budget | Best For |
    |-----------|--------------|--------------|----------|
    | LIFE | 8 | €30M | Implementation |
    | Horizon | 12 | €150M | Research |
    | EU4Health | 3 | €20M | Health focus |
    ```
  - Pass threshold: 80

- [ ] **Scenario 038: Format Programme Recommendation** `EXECUTE + FIX IF NEEDED`
  - Implement `format_programme_recommendation(result: dict) -> str`
  - Input: Recommended programmes with reasoning
  - Output: Ranked recommendations with rationale
  - Include: Match scores, pros/cons, eligibility fit
  - Pass threshold: 80

- [ ] **Scenario 039: Format Programme Info** `EXECUTE + FIX IF NEEDED`
  - Implement `format_programme_info(result: dict) -> str`
  - Input: Single programme overview
  - Output: Programme fact sheet
  - Include: Budget, managing body, key actions, deadlines
  - Pass threshold: 80

### Cross-Programme Comparison

- [ ] **Scenario 040: Format Cross-Programme Eligibility** `EXECUTE + FIX IF NEEDED`
  - Compare eligibility across programmes for same org
  - Show which programmes org qualifies for
  - Include: Different requirements, restrictions
  - Pass threshold: 80

- [ ] **Scenario 041: Format Funding Strategy** `EXECUTE + FIX IF NEEDED`
  - Suggest optimal funding strategy across programmes
  - Multiple projects/phases across different programmes
  - Include: Timeline, complementarity, synergies
  - Pass threshold: 80

### Integration Test

- [ ] **Scenario 042: Multi-Programme Auto-Detection** `EXECUTE + FIX IF NEEDED`
  - Update `format_from_tool_results()` for multi-programme
  - Key detection: `programmes`, `all_programmes_results`, `recommendation`
  - Handle programme recommendation vs search results
  - Pass threshold: 80

---

## Phase 7: Error Handling and Edge Cases (6 scenarios)

Ensure graceful handling of incomplete or malformed data.

### Empty Results

- [ ] **Scenario 043: Handle Empty Call Results** `EXECUTE + FIX IF NEEDED`
  - Improve empty results messaging
  - Include: Alternative search suggestions, broaden criteria
  - Programme-specific tips
  - Pass threshold: 75

- [ ] **Scenario 044: Handle Empty Project Results** `EXECUTE + FIX IF NEEDED`
  - Better empty project search messages
  - Include: Try different keywords, check spelling
  - Link to CORDIS direct search
  - Pass threshold: 75

### Partial Data

- [ ] **Scenario 045: Handle Missing Fields Gracefully** `EXECUTE + FIX IF NEEDED`
  - Don't crash on missing optional fields
  - Show "Not available" or skip field elegantly
  - Maintain consistent formatting
  - Pass threshold: 80

- [ ] **Scenario 046: Handle Malformed Dates** `EXECUTE + FIX IF NEEDED`
  - Handle various date formats robustly
  - Graceful fallback for unparseable dates
  - Never show raw datetime objects
  - Pass threshold: 80

### Large Results

- [ ] **Scenario 047: Handle Large Result Sets** `EXECUTE + FIX IF NEEDED`
  - Pagination or truncation for >20 results
  - Show "and X more..." with next steps
  - Include total count always
  - Pass threshold: 80

- [ ] **Scenario 048: Handle Long Text Fields** `EXECUTE + FIX IF NEEDED`
  - Truncate descriptions elegantly
  - Never cut mid-word or mid-sentence
  - Include "Read more" links
  - Pass threshold: 80

---

## Summary Table

| Phase | Scenarios | Focus Area | Target Pass Rate |
|-------|-----------|------------|------------------|
| Phase 1 | 001-006 | Statistics & Comparison | 90% |
| Phase 2 | 007-014 | Budget & Timeline | 90% |
| Phase 3 | 015-022 | Eligibility (6 programmes) | 90% |
| Phase 4 | 023-030 | Partner & Consortium | 85% |
| Phase 5 | 031-036 | Document Search | 85% |
| Phase 6 | 037-042 | Multi-Programme | 90% |
| Phase 7 | 043-048 | Error Handling | 80% |
| **Total** | **48** | **All Areas** | **87% average** |

---

## Completion Criteria

### Phase Completion Requirements
- [ ] Phase 1 complete: 6/6 scenarios pass (statistics/comparison formatters)
- [ ] Phase 2 complete: 7/8 scenarios pass (budget/timeline formatters)
- [ ] Phase 3 complete: 7/8 scenarios pass (all eligibility formatters)
- [ ] Phase 4 complete: 7/8 scenarios pass (partner/consortium formatters)
- [ ] Phase 5 complete: 5/6 scenarios pass (document search formatters)
- [ ] Phase 6 complete: 5/6 scenarios pass (multi-programme formatters)
- [ ] Phase 7 complete: 5/6 scenarios pass (error handling)

### Overall Completion Requirements
- [ ] 42/48 scenarios pass (87% overall)
- [ ] All 34 tools have formatted output
- [ ] All 6 programmes have programme-specific formatting
- [ ] `format_from_tool_results()` routes to correct formatter automatically
- [ ] No unformatted raw dict/JSON shown to users
- [ ] All outputs include actionable "Next Steps" section

### Code Quality Gates
- [ ] All new methods have docstrings
- [ ] Type hints on all function signatures
- [ ] Unit tests for each formatter
- [ ] No hardcoded text longer than 100 chars (use constants)
- [ ] All external links are correct and working

---

## Appendix A: Formatter Method Reference

| Method Name | Tool(s) Covered | Input Type |
|-------------|-----------------|------------|
| `format_funding_calls` | `search_funding_calls` | `{"calls": [...]}` |
| `format_projects` | `search_projects` | `{"projects": [...]}` |
| `format_organization_projects` | `find_organization_projects` | `{"organization": "...", "projects": [...]}` |
| `format_programme_statistics` | `get_programme_statistics` | `{"success_rate": ..., "total_projects": ...}` |
| `format_country_statistics` | `get_country_statistics` | `{"country": "...", "participation": ...}` |
| `format_programme_comparison` | `compare_programmes` | `{"programme_a": {...}, "programme_b": {...}}` |
| `format_budget_benchmark` | `get_budget_benchmark` | `{"statistics": {...}, "recommendations": ...}` |
| `format_calculated_budget` | `calculate_budget` | `{"calculated_budget": {...}, "breakdown": {...}}` |
| `format_timeline` | `generate_timeline` | `{"work_packages": [...], "milestones": [...]}` |
| `format_eligibility_result` | All `check_*_eligibility` tools | `{"eligible": bool, "requirements": [...]}` |
| `format_partner_discovery` | `find_experienced_partners` | `{"partners": [...]}` |
| `format_collaboration_network` | `get_collaboration_network` | `{"network": {...}}` |
| `format_consortium_patterns` | `get_consortium_patterns` | `{"consortium_size": {...}, "templates": [...]}` |
| `format_similar_projects` | `find_similar_projects`, `get_similar_funded_projects` | `{"similar_projects": [...]}` |
| `format_document_search` | `search_documents`, `search_*_templates` | `{"documents": [...]}` |
| `format_call_history` | `analyze_call_history` | `{"timeline": {...}, "trends": {...}}` |
| `format_multi_programme_search` | `search_all_programmes` | `{"programmes": {...}, "results": [...]}` |
| `format_programme_recommendation` | `recommend_programmes` | `{"recommendations": [...]}` |
| `format_programme_info` | `get_programme_info` | `{"programme": {...}}` |

## Appendix B: Programme-Specific Icons

```python
PROGRAMME_ICONS = {
    "horizon_europe": "🔬",
    "erasmus_plus": "🎓",
    "creative_europe": "🎭",
    "eu4health": "🏥",
    "digital_europe": "💻",
    "life": "🌿",
}

ERASMUS_ACTION_ICONS = {
    "KA1": "✈️",  # Learning mobility
    "KA2": "🤝",  # Cooperation partnerships
    "KA3": "📋",  # Policy support
    "JMO": "🎓",  # Jean Monnet
    "SPORT": "⚽",  # Sport actions
}

CREATIVE_EUROPE_ICONS = {
    "CULTURE": "🎭",
    "MEDIA": "🎬",
    "CROSS-SECTORAL": "🔗",
}

LIFE_ICONS = {
    "NATURE": "🦋",
    "CIRCULAR": "♻️",
    "CLIMATE_MITIGATION": "🌡️",
    "CLIMATE_ADAPTATION": "🌊",
}
```

## Appendix C: Test Execution Commands

```bash
# Run formatter-specific tests
pytest tests/test_v3_response_formatter.py -v

# Run specific phase
pytest tests/test_v3_response_formatter.py -k "phase1" -v
pytest tests/test_v3_response_formatter.py -k "statistics" -v

# Run with coverage
pytest tests/test_v3_response_formatter.py --cov=app/services/response -v

# Integration test with live tools
pytest tests/test_formatter_integration.py -v
```

---

*PRD Version: 1.0*
*Created: January 24, 2026*
*Target: Make V3ResponseFormatter production-ready with 100% tool coverage*
