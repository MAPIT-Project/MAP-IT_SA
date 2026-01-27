# MAPIT Multi-Programme Excellence PRD

| Purpose | Method | Pass Threshold | Target |
|---------|--------|----------------|--------|
| Ensure all 6 EU programmes are comprehensively and equally well-supported | Systematic testing of each programme's tools, cross-programme features, and data quality | 80+ average score across all scenarios | 95% scenario pass rate |

## Problem Statement

MAPIT now supports 6 EU funding programmes:
- **Horizon Europe** (€95.5B) - Research and innovation
- **Erasmus+** (€26.2B) - Education, training, youth, sport
- **Creative Europe** (€2.44B) - Culture, media, cross-sectoral
- **EU4Health** (€5.3B) - Health resilience and crisis response
- **Digital Europe** (€7.5B) - Digital transformation
- **LIFE** (€5.4B) - Environment and climate action

However, the quality of support varies significantly across programmes. Horizon Europe has the most mature implementation with Neo4j graph data, comprehensive vector embeddings, and well-tested tools. The newer programmes (EU4Health, Digital Europe, LIFE) have basic tools but may lack:
- Comprehensive document coverage in vector store
- Graph database integration
- Thorough eligibility rules
- Accurate budget calculation
- Robust error handling

This PRD systematically tests and improves support for all programmes to ensure users receive equally high-quality assistance regardless of which programme they're interested in.

---

## Configuration Notes

**Test Environment:**
- API endpoint: `http://localhost:8000`
- Conversation endpoint: `/api/v3/conversation/{id}/message/stream`
- Required services: PostgreSQL, Redis, Neo4j

**Scoring Dimensions:**
| Dimension | Points | Criteria |
|-----------|--------|----------|
| Query Fulfillment | 40 | All query components addressed completely |
| Specificity | 25 | Contains programme-specific details (amounts, dates, rules) |
| Factual Accuracy | 25 | Information matches official EU sources |
| Actionability | 10 | Clear guidance on next steps |

**Quality Agents:**
- `QualityEvaluatorAgent` for response scoring
- `CrossProgrammeAgent` for programme-specific validation
- `ConversationFlowAgent` for multi-turn testing

---

## Phase 1: Programme-Specific Eligibility Testing (12 scenarios)

Test that each programme's eligibility checker returns accurate, programme-specific information.

### Horizon Europe Eligibility

- [ ] **Scenario 001: Horizon Europe Basic Eligibility** `EXECUTE`
  - Query: "Can a small company from Germany participate in Horizon Europe EIC Accelerator?"
  - Expected: SME definition, EIC Accelerator eligibility, German participation rules, TRL requirements
  - Validate: Mentions equity-free grant + optional blended finance, single SME can apply
  - Pass threshold: 80

- [ ] **Scenario 002: Horizon Europe Consortium Requirements** `EXECUTE + FIX IF NEEDED`
  - Query: "What are the consortium requirements for a Horizon Europe RIA project?"
  - Expected: Minimum 3 entities from 3 different countries, must be independent, at least 1 from EU/Associated
  - Validate: Specific numbers (3 entities, 3 countries), funding rate (100%)
  - Pass threshold: 80

### Erasmus+ Eligibility

- [ ] **Scenario 003: Erasmus+ KA1 Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "Is a vocational training institute from Poland eligible for Erasmus+ mobility projects?"
  - Expected: Yes for KA1, needs Erasmus accreditation or short-term project, VET sector rules
  - Validate: Mentions KA1, accreditation requirement, Poland as EU member state
  - Pass threshold: 80

- [ ] **Scenario 004: Erasmus+ KA2 Partnership Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "What organizations can participate in Erasmus+ Cooperation Partnerships?"
  - Expected: Minimum 3 organizations from 3 different Programme Countries, eligible organization types
  - Validate: Partnership size (3+), country requirements, org types (HEIs, schools, NGOs)
  - Pass threshold: 80

### Creative Europe Eligibility

- [ ] **Scenario 005: Creative Europe CULTURE Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "Can a theater company from Italy apply for Creative Europe Cooperation Projects?"
  - Expected: Yes, CULTURE strand, small/medium/large scale options, partnership requirements
  - Validate: Mentions co-financing rates (60-80%), minimum partners (3-5), Italy eligibility
  - Pass threshold: 80

- [ ] **Scenario 006: Creative Europe MEDIA Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "What are the eligibility requirements for Creative Europe film development funding?"
  - Expected: MEDIA strand, development funding, production company requirements
  - Validate: Company track record requirements, project slate requirements
  - Pass threshold: 80

### EU4Health Eligibility

- [ ] **Scenario 007: EU4Health Basic Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "Can a hospital from Spain participate in EU4Health projects?"
  - Expected: Yes, public/private health entities eligible, specific action types
  - Validate: Spain as EU MS, hospital as eligible entity type, action types available
  - Pass threshold: 80

- [ ] **Scenario 008: EU4Health Organization Types** `EXECUTE + FIX IF NEEDED`
  - Query: "What types of organizations can apply for EU4Health funding?"
  - Expected: Health authorities, NGOs, research bodies, international health organizations
  - Validate: Comprehensive list of eligible org types, specific examples
  - Pass threshold: 80

### Digital Europe Eligibility

- [ ] **Scenario 009: Digital Europe SME Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "Can a tech startup from the Netherlands apply for Digital Europe AI funding?"
  - Expected: Yes for specific objectives, SME participation encouraged, Netherlands eligible
  - Validate: Mentions specific objectives (AI, cybersecurity, etc.), SME definition
  - Pass threshold: 80

- [ ] **Scenario 010: Digital Europe Consortium Rules** `EXECUTE + FIX IF NEEDED`
  - Query: "What are the partnership requirements for Digital Europe projects?"
  - Expected: Varies by call, often requires multiple entities, cross-border component
  - Validate: Specific requirements by objective, country diversity requirements
  - Pass threshold: 80

### LIFE Eligibility

- [ ] **Scenario 011: LIFE Programme Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "Is an environmental NGO from Belgium eligible for LIFE Nature projects?"
  - Expected: Yes, NGOs eligible, Nature and Biodiversity sub-programme, Belgium as EU MS
  - Validate: LIFE sub-programmes mentioned, NGO eligibility confirmed
  - Pass threshold: 80

- [ ] **Scenario 012: LIFE Organization Requirements** `EXECUTE + FIX IF NEEDED`
  - Query: "What organizations can lead a LIFE Climate Action project?"
  - Expected: Public/private bodies registered in EU, co-financing requirements
  - Validate: Lead partner requirements, co-financing rates (55-75%)
  - Pass threshold: 80

---

## Phase 2: Budget Calculation Testing (12 scenarios)

Test that each programme's budget calculator returns accurate funding information.

### Horizon Europe Budget

- [ ] **Scenario 013: Horizon Europe RIA Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "Calculate a budget for a 3-year Horizon Europe RIA project on renewable energy with 8 partners"
  - Expected: Personnel costs breakdown, 100% funding rate, indirect costs (25% flat rate)
  - Validate: Total budget estimate, cost categories, EU contribution equals total
  - Pass threshold: 80

- [ ] **Scenario 014: Horizon Europe IA Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "What budget should I plan for a Horizon Europe Innovation Action with 5 industry partners?"
  - Expected: 70% funding rate for industry, personnel/equipment/subcontracting breakdown
  - Validate: Different rates for different partner types mentioned
  - Pass threshold: 80

### Erasmus+ Budget

- [ ] **Scenario 015: Erasmus+ Mobility Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "Calculate the budget for sending 20 students from France to Spain for 5 months each"
  - Expected: Unit costs for individual support, travel band calculation, organizational support
  - Validate: Specific unit costs per country pair, travel distance band (500-1999km)
  - Pass threshold: 80

- [ ] **Scenario 016: Erasmus+ Partnership Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "What budget can we request for an Erasmus+ Cooperation Partnership with 5 partners?"
  - Expected: Lump sum options (€120k, €250k, €400k), work package structure
  - Validate: Three lump sum tiers mentioned, partnership management component
  - Pass threshold: 80

### Creative Europe Budget

- [ ] **Scenario 017: Creative Europe Cooperation Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "Calculate the budget for a medium-scale Creative Europe Cooperation Project"
  - Expected: €200k-€1M range, 70% co-financing, at least 5 partners
  - Validate: Funding rate (70%), partner requirements, budget range
  - Pass threshold: 80

- [ ] **Scenario 018: Creative Europe MEDIA Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "What funding is available for film distribution through Creative Europe MEDIA?"
  - Expected: Distribution support amounts, territorial eligibility, release requirements
  - Validate: Specific funding ranges for distribution, eligible costs
  - Pass threshold: 80

### EU4Health Budget

- [ ] **Scenario 019: EU4Health Project Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "What budget range should we plan for an EU4Health joint action on cancer?"
  - Expected: Joint action typical budgets, co-financing requirements, eligible costs
  - Validate: Budget ranges for joint actions, EU contribution rates
  - Pass threshold: 80

- [ ] **Scenario 020: EU4Health Grant Calculation** `EXECUTE + FIX IF NEEDED`
  - Query: "Calculate the budget for an EU4Health project on digital health with 6 partners"
  - Expected: Personnel, travel, equipment costs, indirect cost rate
  - Validate: Cost categories, funding rate, realistic total estimate
  - Pass threshold: 80

### Digital Europe Budget

- [ ] **Scenario 021: Digital Europe EDIHs Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "What funding is available for European Digital Innovation Hubs?"
  - Expected: EDIH funding model, matching requirements, typical budget ranges
  - Validate: EDIH-specific information, co-financing rates
  - Pass threshold: 80

- [ ] **Scenario 022: Digital Europe AI Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "Calculate a budget for a Digital Europe AI testing facility project"
  - Expected: Testing and Experimentation Facilities funding, infrastructure costs
  - Validate: TEF-specific requirements, budget components
  - Pass threshold: 80

### LIFE Budget

- [ ] **Scenario 023: LIFE SAP Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "What budget should I plan for a LIFE Standard Action Project on biodiversity?"
  - Expected: SAP budget ranges, 55-60% EU co-financing, eligible costs
  - Validate: Co-financing rate, minimum budget requirements, cost categories
  - Pass threshold: 80

- [ ] **Scenario 024: LIFE SIP Budget** `EXECUTE + FIX IF NEEDED`
  - Query: "Calculate the budget for a LIFE Strategic Integrated Project on climate adaptation"
  - Expected: SIP typical budgets (€10M+), 55% co-financing, implementation period
  - Validate: SIP-specific requirements, long-term implementation, scale
  - Pass threshold: 80

---

## Phase 3: Programme Document Search Testing (12 scenarios)

Test that each programme's template/document search returns relevant guidance.

### Horizon Europe Documents

- [ ] **Scenario 025: Horizon Europe Work Programme Search** `EXECUTE + FIX IF NEEDED`
  - Query: "What does the Horizon Europe Work Programme say about quantum computing funding?"
  - Expected: Cluster 4 Digital topics, specific call references, budget allocations
  - Validate: Work Programme 2024-2025 reference, specific topics mentioned
  - Pass threshold: 80

- [ ] **Scenario 026: Horizon Europe Proposal Template** `EXECUTE + FIX IF NEEDED`
  - Query: "What sections are required in a Horizon Europe proposal?"
  - Expected: Excellence, Impact, Implementation structure, evaluation criteria
  - Validate: Three pillars mentioned, weight of each section
  - Pass threshold: 80

### Erasmus+ Documents

- [ ] **Scenario 027: Erasmus+ Programme Guide Search** `EXECUTE + FIX IF NEEDED`
  - Query: "What are the quality criteria for Erasmus+ KA2 partnerships in the Programme Guide?"
  - Expected: Relevance, quality of design, partnership quality, impact criteria
  - Validate: Four main criteria areas, point allocation (max 100)
  - Pass threshold: 80

- [ ] **Scenario 028: Erasmus+ Application Guidance** `EXECUTE + FIX IF NEEDED`
  - Query: "How do I apply for Erasmus+ Jean Monnet funding?"
  - Expected: Application process, National Agency vs EACEA, deadlines, forms
  - Validate: Correct submission route (EACEA), Jean Monnet specifics
  - Pass threshold: 80

### Creative Europe Documents

- [ ] **Scenario 029: Creative Europe Work Programme Search** `EXECUTE + FIX IF NEEDED`
  - Query: "What priorities does the Creative Europe 2024 Work Programme highlight?"
  - Expected: Green transition, digital transformation, gender balance, inclusion
  - Validate: Reference to actual Work Programme priorities
  - Pass threshold: 80

- [ ] **Scenario 030: CulturEU Guide Search** `EXECUTE + FIX IF NEEDED`
  - Query: "What does the CulturEU guide say about first-time applicants?"
  - Expected: Guidance for newcomers, capacity building, smaller organizations
  - Validate: CulturEU guide reference, first-timer advice
  - Pass threshold: 80

### EU4Health Documents

- [ ] **Scenario 031: EU4Health Work Programme Search** `EXECUTE + FIX IF NEEDED`
  - Query: "What are the EU4Health priorities for 2024?"
  - Expected: Cancer plan, mental health, digital health, health crisis preparedness
  - Validate: Reference to annual work programme, specific priorities
  - Pass threshold: 80

- [ ] **Scenario 032: EU4Health Application Requirements** `EXECUTE + FIX IF NEEDED`
  - Query: "What documents are needed for an EU4Health grant application?"
  - Expected: Application form, budget annex, partner declarations, work plan
  - Validate: Required documents listed, submission portal mentioned
  - Pass threshold: 80

### Digital Europe Documents

- [ ] **Scenario 033: Digital Europe Work Programme Search** `EXECUTE + FIX IF NEEDED`
  - Query: "What cybersecurity topics are funded under Digital Europe?"
  - Expected: SOCs, threat intelligence, skills development, certifications
  - Validate: Specific cybersecurity objective references
  - Pass threshold: 80

- [ ] **Scenario 034: Digital Europe Application Guidance** `EXECUTE + FIX IF NEEDED`
  - Query: "How do I apply for Digital Europe funding?"
  - Expected: Funding & Tenders portal, proposal structure, evaluation process
  - Validate: Correct portal mentioned, application steps
  - Pass threshold: 80

### LIFE Documents

- [ ] **Scenario 035: LIFE Programme Priorities** `EXECUTE + FIX IF NEEDED`
  - Query: "What are the priority areas for LIFE Nature and Biodiversity projects?"
  - Expected: Natura 2000, species protection, ecosystem restoration, EU Biodiversity Strategy
  - Validate: LIFE-specific priorities, EU policy alignment
  - Pass threshold: 80

- [ ] **Scenario 036: LIFE Application Process** `EXECUTE + FIX IF NEEDED`
  - Query: "What is the two-stage application process for LIFE projects?"
  - Expected: Concept note stage, full proposal stage, evaluation criteria
  - Validate: Two-stage process described, timeline
  - Pass threshold: 80

---

## Phase 4: Cross-Programme Features (12 scenarios)

Test the multi-programme search and recommendation features.

### Multi-Programme Search

- [ ] **Scenario 037: Search All Programmes for Climate** `EXECUTE + FIX IF NEEDED`
  - Query: "Find funding opportunities across all EU programmes for climate adaptation projects"
  - Expected: Results from LIFE, Horizon Europe, possibly Erasmus+ and others
  - Validate: Multiple programmes in results, relevance to climate adaptation
  - Pass threshold: 80

- [ ] **Scenario 038: Search All Programmes for Digital** `EXECUTE + FIX IF NEEDED`
  - Query: "What EU funding is available for AI and machine learning projects?"
  - Expected: Digital Europe, Horizon Europe, Creative Europe MEDIA
  - Validate: Multiple relevant programmes, specific call/action references
  - Pass threshold: 80

- [ ] **Scenario 039: Search All Programmes for Health** `EXECUTE + FIX IF NEEDED`
  - Query: "Find all EU funding programmes supporting mental health initiatives"
  - Expected: EU4Health, Horizon Europe Health cluster, Erasmus+ youth
  - Validate: EU4Health prominently featured, cross-programme opportunities
  - Pass threshold: 80

### Programme Recommendations

- [ ] **Scenario 040: Recommend Programme for University** `EXECUTE + FIX IF NEEDED`
  - Query: "Which EU programme is best for a university wanting to do international student exchanges?"
  - Expected: Erasmus+ strongly recommended, possibly Horizon Europe MSCA
  - Validate: Clear recommendation with rationale, alternatives mentioned
  - Pass threshold: 80

- [ ] **Scenario 041: Recommend Programme for SME** `EXECUTE + FIX IF NEEDED`
  - Query: "Which EU programme should a tech startup apply to for AI product development?"
  - Expected: EIC Accelerator, Digital Europe, or Horizon Europe depending on stage
  - Validate: Multiple options with pros/cons, TRL considerations
  - Pass threshold: 80

- [ ] **Scenario 042: Recommend Programme for NGO** `EXECUTE + FIX IF NEEDED`
  - Query: "What EU funding is best for an environmental NGO doing conservation work?"
  - Expected: LIFE as primary, Horizon Europe Climate cluster as secondary
  - Validate: Clear LIFE recommendation, alternative options
  - Pass threshold: 80

### Cross-Programme Comparison

- [ ] **Scenario 043: Compare Health Funding Options** `EXECUTE + FIX IF NEEDED`
  - Query: "Compare EU4Health and Horizon Europe Health cluster for cancer research funding"
  - Expected: Side-by-side comparison, different focus areas, complementarity
  - Validate: Both programmes' strengths described, guidance on choosing
  - Pass threshold: 80

- [ ] **Scenario 044: Compare Digital Funding Options** `EXECUTE + FIX IF NEEDED`
  - Query: "What's the difference between Digital Europe and Horizon Europe for cybersecurity projects?"
  - Expected: Deployment vs research focus, TRL differences, budget scales
  - Validate: Clear differentiation, use case guidance
  - Pass threshold: 80

- [ ] **Scenario 045: Compare Education Funding Options** `EXECUTE + FIX IF NEEDED`
  - Query: "Should I apply to Erasmus+ or Creative Europe for a music education project?"
  - Expected: Depends on focus - education vs cultural production
  - Validate: Clear criteria for choosing, both options explained
  - Pass threshold: 80

### Programme Information

- [ ] **Scenario 046: Get Programme Overview** `EXECUTE + FIX IF NEEDED`
  - Query: "Give me an overview of the LIFE programme"
  - Expected: Budget, sub-programmes, priorities, managing authority
  - Validate: Accurate facts (€5.4B budget), CINEA management
  - Pass threshold: 80

- [ ] **Scenario 047: Get Programme Statistics** `EXECUTE + FIX IF NEEDED`
  - Query: "What is the success rate for Horizon Europe ERC grants?"
  - Expected: ERC-specific success rates, comparison across grant types
  - Validate: Realistic success rate figures, source indication
  - Pass threshold: 80

- [ ] **Scenario 048: Get Programme Deadlines** `EXECUTE + FIX IF NEEDED`
  - Query: "When are the next deadlines for EU4Health calls?"
  - Expected: Upcoming call deadlines, annual cycle information
  - Validate: Specific dates or "check portal" guidance, current year reference
  - Pass threshold: 80

---

## Phase 5: Error Handling and Edge Cases (6 scenarios)

Test graceful handling of edge cases and invalid inputs.

### Invalid Programme Queries

- [ ] **Scenario 049: Non-Existent Programme** `EXECUTE + FIX IF NEEDED`
  - Query: "Can I apply to the EU Innovation Fund through MAPIT?"
  - Expected: Clarification that Innovation Fund is separate, redirect to supported programmes
  - Validate: Doesn't hallucinate, explains supported programmes
  - Pass threshold: 75

- [ ] **Scenario 050: Ambiguous Programme Reference** `EXECUTE + FIX IF NEEDED`
  - Query: "What funding is available for media projects?"
  - Expected: Clarifies - Creative Europe MEDIA or general media research under Horizon?
  - Validate: Asks for clarification or covers multiple interpretations
  - Pass threshold: 75

### Third Country Eligibility

- [ ] **Scenario 051: Non-EU Country Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "Can organizations from the United States participate in EU funding programmes?"
  - Expected: Varies by programme, often as partner but not coordinator, no EU funding
  - Validate: Accurate third country rules, programme-specific differences
  - Pass threshold: 80

- [ ] **Scenario 052: UK Post-Brexit Eligibility** `EXECUTE + FIX IF NEEDED`
  - Query: "What EU programmes can UK organizations participate in after Brexit?"
  - Expected: Horizon Europe (associated), not Erasmus+ or Creative Europe, special conditions
  - Validate: Accurate post-Brexit status for each programme
  - Pass threshold: 80

### Complex Multi-Programme Queries

- [ ] **Scenario 053: Multi-Objective Organization** `EXECUTE + FIX IF NEEDED`
  - Query: "We're a hospital doing both cancer research and climate-health intersection work. What programmes fit?"
  - Expected: EU4Health, Horizon Europe Health and Climate clusters, possibly LIFE
  - Validate: Multiple relevant programmes identified, complementarity explained
  - Pass threshold: 80

- [ ] **Scenario 054: Small Organization Capacity** `EXECUTE + FIX IF NEEDED`
  - Query: "We're a small NGO with limited capacity. Which EU programmes are most accessible?"
  - Expected: Smaller Creative Europe cooperations, Erasmus+ small partnerships, LIFE with co-applicants
  - Validate: Capacity-appropriate recommendations, lump sum options mentioned
  - Pass threshold: 80

---

## Summary Table

| Phase | Scenarios | Focus Area | Target Pass Rate |
|-------|-----------|------------|------------------|
| Phase 1 | 001-012 | Programme-Specific Eligibility | 90% |
| Phase 2 | 013-024 | Budget Calculation | 85% |
| Phase 3 | 025-036 | Document/Template Search | 85% |
| Phase 4 | 037-048 | Cross-Programme Features | 90% |
| Phase 5 | 049-054 | Error Handling & Edge Cases | 80% |
| **Total** | **54** | **All Areas** | **86% average** |

---

## Completion Criteria

### Phase Completion Requirements
- [ ] Phase 1 complete: 11/12 scenarios pass (90%+ eligibility accuracy)
- [ ] Phase 2 complete: 10/12 scenarios pass (85%+ budget accuracy)
- [ ] Phase 3 complete: 10/12 scenarios pass (85%+ document retrieval)
- [ ] Phase 4 complete: 11/12 scenarios pass (90%+ cross-programme)
- [ ] Phase 5 complete: 5/6 scenarios pass (80%+ edge case handling)

### Overall Completion Requirements
- [ ] 46/54 scenarios pass (85% overall)
- [ ] Average quality score across all scenarios: 80+
- [ ] No programme has less than 75% pass rate for its scenarios
- [ ] Cross-programme search returns results from 3+ programmes when relevant
- [ ] All 6 programmes have working eligibility, budget, and document tools

### Quality Gates
- [ ] All Horizon Europe scenarios: 85%+ pass rate
- [ ] All Erasmus+ scenarios: 85%+ pass rate
- [ ] All Creative Europe scenarios: 85%+ pass rate
- [ ] All EU4Health scenarios: 80%+ pass rate
- [ ] All Digital Europe scenarios: 80%+ pass rate
- [ ] All LIFE scenarios: 80%+ pass rate

---

## Appendix A: Programme Quick Reference

| Programme | Budget | Main Focus | Key Tools |
|-----------|--------|------------|-----------|
| Horizon Europe | €95.5B | Research & Innovation | `search_projects`, `get_budget_benchmark`, `find_experienced_partners` |
| Erasmus+ | €26.2B | Education & Mobility | `check_erasmus_eligibility`, `calculate_erasmus_budget`, `search_erasmus_templates` |
| Creative Europe | €2.44B | Culture & Media | `check_creative_europe_eligibility`, `calculate_creative_europe_budget`, `search_creative_europe_templates` |
| EU4Health | €5.3B | Health Systems | `check_eu4health_eligibility`, `search_eu4health_templates` |
| Digital Europe | €7.5B | Digital Skills & Infrastructure | `check_digital_europe_eligibility`, `search_digital_europe_templates` |
| LIFE | €5.4B | Environment & Climate | `check_life_eligibility`, `search_life_templates` |

## Appendix B: Expected Tool Calls by Scenario Type

| Scenario Type | Primary Tool | Secondary Tools |
|---------------|--------------|-----------------|
| Eligibility | `check_*_eligibility` | `get_programme_info` |
| Budget | `calculate_*_budget` | `get_budget_benchmark` |
| Documents | `search_*_templates` | `search_documents` |
| Cross-Programme | `search_all_programmes` | `recommend_programmes`, `get_programme_info` |
| Comparison | `compare_programmes` | Programme-specific tools |

## Appendix C: Common Failure Patterns

| Failure Type | Likely Cause | Fix Strategy |
|--------------|--------------|--------------|
| Missing programme-specific details | Insufficient document coverage | Add more programme documents to vector store |
| Wrong eligibility rules | Outdated or generic responses | Update eligibility tool with 2024/2025 rules |
| Inaccurate budget figures | Hardcoded values instead of tool use | Ensure budget tool uses current unit costs |
| No cross-programme results | Tool not searching all programmes | Check `search_all_programmes` implementation |
| Generic responses | Falling back to LLM knowledge | Ensure tools are being called, add fallbacks |

---

## Appendix D: Test Execution Commands

```bash
# Run all scenarios
pytest tests/test_multi_programme_scenarios.py -v

# Run specific phase
pytest tests/test_multi_programme_scenarios.py -k "phase1" -v
pytest tests/test_multi_programme_scenarios.py -k "phase2" -v

# Run specific programme
pytest tests/test_multi_programme_scenarios.py -k "horizon" -v
pytest tests/test_multi_programme_scenarios.py -k "erasmus" -v
pytest tests/test_multi_programme_scenarios.py -k "creative_europe" -v
pytest tests/test_multi_programme_scenarios.py -k "eu4health" -v
pytest tests/test_multi_programme_scenarios.py -k "digital_europe" -v
pytest tests/test_multi_programme_scenarios.py -k "life" -v

# Run with quality scoring
pytest tests/test_multi_programme_scenarios.py -v --quality-scoring

# Run with coverage
pytest tests/test_multi_programme_scenarios.py --cov=app/services/tools -v
```

---

*PRD Version: 1.0*
*Created: January 24, 2026*
*Target Completion: Systematic improvement of all 6 EU programme support*
