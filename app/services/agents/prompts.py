"""Prompt constants for ToolAwareAgent reasoning."""

__all__ = ["BUILT_IN_KNOWLEDGE", "REASONING_PROMPT", "KNOWLEDGE_SECTIONS"]

# Built-in knowledge for common questions where documents may be incomplete
BUILT_IN_KNOWLEDGE = """
## Quick Reference: Horizon Europe Facts

### Official Resources (ALWAYS include when explaining programme structure)
When answering questions about Horizon Europe structure, ALWAYS include these actionable links at the end:

🎯 **Getting Started with Horizon Europe:**
• Register on [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)
• Review the [Work Programmes](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON) for your cluster
• Check eligibility via [How to Participate](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/how-to-participate/1)
• Find partners using [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search)
• Browse [Call Calendar](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/calls-calendar)

### Page Limits for Proposals (Part B - Technical Description)
| Action Type | Standard Page Limit | Notes |
|-------------|---------------------|-------|
| **RIA/IA (single-stage)** | **45 pages** | Sections 1-3 combined |
| **RIA/IA (two-stage, full)** | **45 pages** | After passing stage 1 |
| **RIA/IA (two-stage, outline)** | **10 pages** | Stage 1 only |
| **CSA** | **30 pages** | Shorter scope |
| **ERC grants** | **Variable** | Check specific call |
| **MSCA** | **10-15 pages** | Depends on action |
| **EIC Accelerator** | **Variable** | Short proposal + full |

*Page limits are strictly enforced. Excess pages will be blanked and not evaluated.*

### Organisation Type Eligibility
| Organisation Type | Eligible? | Funding Rate (RIA) | Funding Rate (IA) | Special Notes |
|-------------------|-----------|-------------------|-------------------|---------------|
| **Universities/HEIs** | Yes | 100% | 100% | Must have GEP |
| **Research Institutes** | Yes | 100% | 100% | Must have GEP |
| **SMEs** | Yes | 100% | 70% | EIC Accelerator available |
| **Large Companies** | Yes | 100% | 70% | Cannot lead some calls |
| **NGOs** | Yes | 100% | 100% (non-profit) | Often needed for dissemination |
| **Public Bodies** | Yes | 100% | 100% | Must have GEP |
| **International Orgs** | Case-by-case | Varies | Varies | Check specific call |

### Action Types Summary
| Type | TRL Range | Funding Rate | Focus |
|------|-----------|--------------|-------|
| **RIA** | TRL 2-5 | 100% | Research, new knowledge |
| **IA** | TRL 5-8 | 70%/100% | Demonstration, piloting |
| **CSA** | N/A | 100% | Coordination, networking |

### RIA Project Details (Research and Innovation Actions)

When answering questions about RIA project parameters (duration, payment, budget), use these specifics:

#### Project Duration
| Duration Type | Range | Notes |
|--------------|-------|-------|
| **Typical** | **36-48 months** | Standard for most RIA topics |
| **Maximum** | **Up to 60 months** | For complex research requiring longer timelines |
| **Minimum** | **24 months** | Rare, for focused/shorter topics |

*Always check the specific Work Programme topic for "Expected Duration" - it varies by call.*

#### Payment Modality (RIA)
RIA projects use the **Actual Cost** model with **100% reimbursement** and follow this payment schedule:

| Payment Type | Timing | Amount/Details |
|--------------|--------|----------------|
| **Pre-financing** | Within 30 days of grant signature | 40-50% of total EC contribution (advance payment) |
| **Interim Payment(s)** | After periodic reporting periods (typically 18 months) | Based on actual costs reported, minus pre-financing consumed |
| **Final Payment** | After final report approval | Remaining balance (5-10% typically retained until final review) |

**Key Payment Rules:**
- **Reporting periods**: Usually every 18 months or at project midpoint
- **Pre-financing guarantee**: May be required for coordinators with small annual turnover
- **Cost eligibility**: Costs must be incurred during project period, necessary for implementation
- **Indirect costs**: 25% flat rate on direct costs (excluding subcontracting)

#### Budget & Costs (RIA)
| Category | Typical Range/Rate | Notes |
|----------|-------------------|-------|
| **Total budget** | **€3-10 million** | Varies by topic; check Work Programme |
| **Funding rate** | **100%** | Full reimbursement of eligible costs |
| **Indirect costs** | **25% flat rate** | Applied to direct costs minus subcontracting |
| **Personnel costs** | 55-65% of budget | Largest cost category |
| **Subcontracting** | Max 5-15% recommended | No indirect costs on subcontracting |

**Budget Formula:**
```
EU Contribution = Direct Costs + (Direct Costs - Subcontracting) × 25%
```

🎯 **RIA Resources:**
• [Model Grant Agreement](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf) - Complete payment and cost rules
• [Financial Guidelines](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/unit-cost-decision-sme-owners-managers_he_en.pdf) - Cost eligibility details
• [Work Programmes](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON) - Topic-specific parameters

### Consortium Requirements
- **Standard (RIA/IA/CSA)**: 3 independent entities from 3 different EU/AC countries
- **ERC**: Single PI (monobeneficiary)
- **MSCA PF**: Single fellow + host
- **EIC Accelerator**: Single SME or small group

### Typical Consortium Sizes (Based on Funded Project Data)

| Action Type | Avg Partners | Typical Range | Avg Countries | Key Characteristics |
|-------------|--------------|---------------|---------------|---------------------|
| **RIA** | 10-12 | 6-16 | 6-8 | Research focus, strong academic presence, TRL 1-5 |
| **IA** | 14-16 | 10-20 | 8-10 | Demo/scale-up, more industry partners (35-45%), TRL 5-8 |
| **CSA** | 6-9 | 3-12 | 4-6 | Coordination/networking, smaller focused teams, policy focus |

**Key differences in consortium composition:**
- **IA (Innovation Action)**: Larger consortia because demonstration/deployment requires more end-users, pilots, and industry involvement. Higher industry participation (35-45% PRC/SME).
- **CSA (Coordination & Support Action)**: Smaller, agile teams focused on networking, policy support, or standardization. Often led by associations or policy organizations.
- **RIA (Research & Innovation Action)**: Balanced research consortia with strong academic/research institute presence (55-65% HES/REC).

### Budget Limits / Expected EU Contribution per Project
There is NO single fixed budget limit for Innovation Actions (IA) or other action types. Budgets are defined per TOPIC in the Work Programme.

| Action Type | Typical EU Contribution Range | Notes |
|-------------|------------------------------|-------|
| **RIA (standard)** | €3-8 million | Varies by topic complexity |
| **IA (standard)** | €5-15 million | Large-scale demonstrations |
| **IA (flagship/large)** | €15-50 million | Strategic topics only |
| **CSA** | €1-3 million | Coordination activities |
| **ERC Starting** | Up to €1.5 million | 5 years |
| **ERC Consolidator** | Up to €2 million | 5 years |
| **ERC Advanced** | Up to €2.5 million | 5 years |
| **EIC Accelerator** | Up to €2.5M grant + €15M equity | Blended finance |

**How to find actual limits:** Check the specific Call Topic in the Work Programme - it states "Expected EU contribution per project: €X-Y million"

### Getting Started with Proposal Writing
If someone asks "How do I start writing a proposal?" or "Where do I start?", provide this guidance:

1. **Find a relevant call**: Search for open calls on the EU Funding & Tenders Portal that match your research area
2. **Understand the call**: Read the Work Programme topic carefully - understand scope, expected outcomes, and evaluation criteria
3. **Build your consortium**: Most calls require 3+ partners from 3+ different EU/Associated countries
4. **Write the proposal**: Follow the template structure (Excellence, Impact, Implementation)
5. **Use the search tools**: Search for similar funded projects to learn from successful proposals

### Proposal Template Structure (Part B)
Standard RIA/IA proposals have 3 main sections:
- **Section 1: Excellence** - Scientific quality, objectives, methodology, ambition (beyond state-of-art)
- **Section 2: Impact** - Expected outcomes, pathways to impact, dissemination, exploitation
- **Section 3: Implementation** - Work plan, consortium, resources, management

### Evaluation Criteria
| Section | Threshold | Weight | Key aspects |
|---------|-----------|--------|-------------|
| Excellence | 4/5 | ~1/3 | Objectives, methodology, ambition |
| Impact | 4/5 | ~1/3 | Outcomes, dissemination, exploitation |
| Implementation | 3/5 | ~1/3 | Work plan, consortium, resources |
| **Overall** | **10/15** | - | Must pass all thresholds |

### Why Some Countries Have Higher Success Rates (Analytical Knowledge)
When users ask about country success rate disparities, provide this analysis:

**Key Factors Affecting Country Success Rates:**

1. **National R&D Investment**: Countries with higher R&D spending (% of GDP) tend to have stronger research institutions and more competitive proposals. Nordic countries (Sweden, Finland, Denmark) and central European nations (Germany, Netherlands) consistently perform well.

2. **Institutional Experience**: Organizations with extensive EU funding track records understand evaluation criteria better, have established partnerships, and write more competitive proposals. First-time applicants face a steep learning curve.

3. **National Support Systems**: Some countries have dedicated National Contact Points (NCPs), proposal writing support services, and pre-submission review programs that significantly improve proposal quality.

4. **Language Proficiency**: Proposals are evaluated in English. Non-native English speaking countries may face subtle disadvantages in proposal clarity and persuasiveness.

5. **Consortium Networks**: Countries with strong international research networks can more easily build competitive consortiums with complementary partners.

6. **Strategic Focus**: Some countries strategically target calls where they have comparative advantages, rather than spreading efforts across all areas.

7. **Coordination Culture**: Countries with traditions of collaborative research (vs. competitive individual research) adapt better to consortium-based EU funding.

**Typical Success Rates by Country Type:**
- **EU-15 established members**: 12-18% average success rate
- **EU-13 newer members**: 8-12% average success rate (improving with Widening participation actions)
- **Associated Countries**: Varies widely (Switzerland historically ~20%, UK post-Brexit ~15%)

**Note**: Success rates vary significantly by programme. For specific country data, use the get_country_statistics tool with a specific country name.

### Marie Skłodowska-Curie Actions (MSCA) - Complete Overview

MSCA is part of **Pillar I - Excellent Science** in Horizon Europe. It funds researcher mobility, training, and career development with a total budget of **€6.6 billion (2021-2027)**.

#### MSCA Action Types

| Action | Full Name | Budget | Duration | Participants | Funding Rate |
|--------|-----------|--------|----------|--------------|--------------|
| **MSCA-PF** | Postdoctoral Fellowships | €200-300K per fellow | 12-24 months | Single researcher + host | 100% |
| **MSCA-DN** | Doctoral Networks | €2-4M per network | 48 months | 3+ partners, 3+ countries | 100% |
| **MSCA-SE** | Staff Exchanges | €0.5-1.5M | 48 months | 3+ partners, 2+ countries | 100% |
| **MSCA-COFUND** | Co-funding of programmes | €10M max | 60 months | Single organization | 100% of unit costs |

#### MSCA-PF (Postdoctoral Fellowships)
- **Purpose**: Support experienced researchers to conduct independent research abroad
- **Eligibility**: PhD holders or 4+ years research experience
- **Types**:
  - **European Fellowships (EF)**: Research in any EU/Associated Country
  - **Global Fellowships (GF)**: Outgoing phase (12-24m) + mandatory return (12m)
- **Budget**: Living allowance (~€5,080/month) + mobility (~€600/month) + family (~€660/month if applicable) + research/training costs
- **Consortium**: Single fellow + single host institution

#### MSCA-DN (Doctoral Networks)
- **Purpose**: Train doctoral candidates through international, inter-sectoral, and interdisciplinary research
- **Participants**: Early-stage researchers (no PhD, <4 years experience)
- **Duration**: 36-48 months (network), 3-36 months per researcher
- **Budget**: €2.5-4M per network; unit costs per researcher-month
- **Consortium**: Min 3 beneficiaries from 3 different countries
- **Types**: Standard DN, Industrial Doctorates, Joint Doctorates

#### MSCA-SE (Staff Exchanges)
- **Purpose**: Enable international, inter-sectoral secondments for knowledge transfer
- **Eligibility**: Staff at any career stage (researchers, technical, management)
- **Duration**: 1-12 months per secondment
- **Budget**: €100/day (staff) + €2,000/month contribution to host
- **Consortium**: Min 3 participants from 2 countries; must include 2 sectors (academic + non-academic)

#### MSCA-COFUND
- **Purpose**: Co-fund regional, national, or international fellowship or doctoral programmes
- **Eligibility**: Legal entities running existing funding programmes
- **Budget**: Flat rate per researcher-month (up to €10M per project)
- **Duration**: 36-60 months
- **Consortium**: Single beneficiary (programme operator)

#### MSCA Key Resources (ALWAYS include when answering MSCA questions)
🎯 **Getting Started with MSCA:**
• Visit the [MSCA Portal](https://marie-sklodowska-curie-actions.ec.europa.eu/)
• Read the [MSCA Work Programme 2025](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• Search calls on [EU Funding Portal - MSCA](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=null;freeTextSearchKeyword=MSCA;matchWholeText=true;typeCodes=1,0;statusCodes=31094501,31094502;programmePeriod=2021%20-%202027;programCcm2Id=43108390;programDivisionCode=null;focusAreaCode=null;destinationGroup=null;missionGroup=null;geographicalZonesCode=null;programmeDivisionProsp498Code=null;startDateLte=null;startDateGte=null;crossCuttingPriorityCode=null;cpvCode=null;performanceOfDelivery=null;sortQuery=sortStatus;orderBy=asc;onlyTenders=false;topicListKey=topicSearchTablePageState)
• Check eligibility via [MSCA Guide for Applicants](https://rea.ec.europa.eu/funding-and-grants/horizon-europe-marie-sklodowska-curie-actions_en)
• Use [Euraxess](https://euraxess.ec.europa.eu/) for job/fellowship searches

### Horizon Europe Clusters and EU Missions - Complete Overview

Clusters and Missions are key components of **Pillar II: Global Challenges and European Industrial Competitiveness** in Horizon Europe.

#### The 6 Thematic Clusters

Clusters organize collaborative research addressing major societal challenges. Each cluster has its own Work Programme with specific topics and calls.

| Cluster | Name | Focus Areas | Budget (2021-2027) |
|---------|------|-------------|-------------------|
| **Cluster 1** | Health | Disease prevention, treatment, healthcare systems, pandemic preparedness, cancer research, personalized medicine | ~€8.2 billion |
| **Cluster 2** | Culture, Creativity & Inclusive Society | Democracy, governance, cultural heritage, social cohesion, migration, European identity | ~€2.3 billion |
| **Cluster 3** | Civil Security for Society | Cybersecurity, disaster resilience, border security, counter-terrorism, critical infrastructure protection | ~€1.6 billion |
| **Cluster 4** | Digital, Industry & Space | AI, robotics, advanced manufacturing, semiconductors, quantum computing, space technologies | ~€15.3 billion |
| **Cluster 5** | Climate, Energy & Mobility | Clean energy, hydrogen, batteries, smart grids, sustainable transport, climate-neutral solutions | ~€15.1 billion |
| **Cluster 6** | Food, Bioeconomy, Natural Resources, Agriculture & Environment | Sustainable food systems, biodiversity, circular economy, forestry, fisheries, water, soil health | ~€9 billion |

#### The 5 EU Missions

EU Missions are a NEW approach in Horizon Europe: challenge-driven research portfolios with **ambitious, measurable targets** for 2030.

| Mission | Full Name | Target | Key Actions |
|---------|-----------|--------|-------------|
| **Cancer** | Conquering Cancer | Improve lives of 3+ million people through prevention, cure, and better quality of life | Early detection, personalized treatment, patient-centered care |
| **Climate Adaptation** | Adaptation to Climate Change | Support 150+ EU regions to become climate-resilient by 2030 | Climate risk assessment, adaptation pathways, regional transformation |
| **Ocean & Waters** | Restore our Ocean and Waters | Restore health of ocean and waters by 2030 | Marine protected areas, pollution reduction, blue economy |
| **Cities** | Climate-Neutral & Smart Cities | 100 European cities climate-neutral by 2030 | City Climate Contracts, citizen engagement, urban innovation |
| **Soil** | A Soil Deal for Europe | 100 living labs and lighthouses for healthy soils by 2030 | Soil monitoring, sustainable land management, soil carbon |

#### Key Differences: Clusters vs Missions

| Aspect | Clusters | Missions |
|--------|----------|----------|
| **Approach** | Thematic grouping of research topics | Challenge-driven with specific 2030 targets |
| **Structure** | Annual Work Programmes with multiple topics | Mission-specific calls and implementation plans |
| **Goal** | Research excellence and knowledge generation | Measurable societal impact by 2030 |
| **Scope** | Broad research areas | Focused, time-bound objectives |
| **Governance** | REA/CINEA implementation | Mission Boards advising on strategy |

#### Cluster Key Resources (ALWAYS include when answering Cluster/Mission questions)
🎯 **Getting Started with Clusters and Missions:**
• Browse Cluster Work Programmes: [Horizon Europe Work Programmes](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• Find Cluster calls: [EU Funding Portal - Topic Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search)
• Learn about EU Missions: [EU Missions Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe_en)
• Mission implementation: [Mission Implementation Plans](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/mission-implementation_en)

### Searching for Calls by Research Domain - CRITICAL GUIDANCE

When a researcher asks about funding calls for their domain (e.g., "health research", "cancer research", "AI research"), you MUST:

1. **Search the PRIMARY cluster** for their domain using `search_funding_calls` with cluster filter
2. **ALWAYS mention MSCA cross-cutting opportunities** (MSCA is open to ALL research domains)

#### Research Domain → Cluster Mapping

| Research Domain | Primary Cluster | Call ID Pattern | Also Check |
|-----------------|-----------------|-----------------|------------|
| **Health, cancer, medical, clinical, disease, pharmaceutical, biomedical, vaccine, pandemic** | **Cluster 1 (Health)** | `HORIZON-HLTH-*` | EU Mission on Cancer (MISS-CANCER-*) |
| **Digital, AI, robotics, quantum, semiconductors, industry, manufacturing, space** | **Cluster 4 (Digital/Industry/Space)** | `HORIZON-CL4-*` | EIC Pathfinder |
| **Climate, energy, hydrogen, batteries, transport, mobility, green** | **Cluster 5 (Climate/Energy/Mobility)** | `HORIZON-CL5-*` | EU Mission Climate |
| **Food, agriculture, biodiversity, environment, bioeconomy, soil, water, oceans** | **Cluster 6 (Food/Bioeconomy)** | `HORIZON-CL6-*` | EU Mission Soil, EU Mission Ocean |
| **Culture, heritage, democracy, social, creative, digital heritage, museum, archaeology** | **Cluster 2 (Culture/Inclusive)** | `HORIZON-CL2-*` | Creative Europe, Cluster 4 (for digital technologies) |
| **Security, cybersecurity, disaster, border, crime** | **Cluster 3 (Security)** | `HORIZON-CL3-*` | - |

#### CRITICAL: MSCA is Cross-Cutting (ALWAYS mention for research calls)

**Marie Skłodowska-Curie Actions (MSCA)** are **thematic-neutral** and available for researchers in ANY field:

- **MSCA-PF** (Postdoctoral Fellowships): For experienced researchers to conduct research in any domain
- **MSCA-DN** (Doctoral Networks): For PhD training networks in any research area
- **MSCA-SE** (Staff Exchanges): For knowledge transfer in any field

When answering "What calls are available for [domain] research?", ALWAYS include:
1. Cluster-specific calls (e.g., HORIZON-HLTH-* for health)
2. MSCA opportunities (cross-cutting, applicable to ALL domains)
3. Relevant Missions if applicable (e.g., EU Mission on Cancer for cancer research)

#### Example: Health/Cancer Research Calls

For health or cancer researchers, include:
- **Cluster 1 Health calls** (HORIZON-HLTH-2025-*, HORIZON-HLTH-2026-*): Disease prevention, treatment, healthcare systems, pandemic preparedness
- **EU Mission on Cancer** (HORIZON-MISS-2025-CANCER-*, HORIZON-MISS-2026-CANCER-*): Early detection, personalized treatment, quality of life
- **MSCA opportunities**: MSCA-PF-2025 (September deadline), MSCA-DN-2025 for doctoral training
- **ERC grants**: For frontier research in any domain

🎯 **Health Research Resources:**
• Cluster 1 Work Programme: [Health Work Programme](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• EU Mission on Cancer: [Mission Cancer Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/eu-mission-cancer_en)
• MSCA Portal: [MSCA Actions](https://marie-sklodowska-curie-actions.ec.europa.eu/)
• Search Health calls: [EU Portal - Health Cluster](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=null;freeTextSearchKeyword=;matchWholeText=true;typeCodes=1,0;statusCodes=31094501,31094502;programmePeriod=2021%20-%202027;programCcm2Id=43108390;programDivisionCode=43108557)

#### Example: Climate Change Monitoring Research Calls (MULTIDISCIPLINARY)

Climate monitoring research is **inherently multidisciplinary** - it spans MULTIPLE clusters. Include:

**Primary: Cluster 5 - Climate, Energy and Mobility (HORIZON-CL5-*):**
- Climate science and climate services
- Earth system observation
- Climate change mitigation technologies
- Carbon capture and storage
- Sustainable energy systems

**Also Critical: Cluster 6 - Food, Bioeconomy, Natural Resources (HORIZON-CL6-*):**
- Environmental monitoring and biodiversity
- Ocean and water systems monitoring
- Soil health and ecosystem services
- Land use and forestry monitoring
- Circular economy and resource efficiency

**Relevant EU Missions (ALWAYS mention these for climate monitoring):**
- **Mission: Adaptation to Climate Change** (HORIZON-MISS-*-CLIMA-*): Climate-resilient regions, monitoring for adaptation
- **Mission: Restore our Ocean and Waters** (HORIZON-MISS-*-OCEAN-*): Marine monitoring, healthy oceans by 2030
- **Mission: A Soil Deal for Europe** (HORIZON-MISS-*-SOIL-*): Soil health monitoring, 100 living labs

**Cross-Cutting Opportunities:**
- **MSCA**: MSCA-PF and MSCA-DN for climate/environmental researchers
- **EIC Pathfinder**: Breakthrough climate monitoring technologies
- **ERC**: Frontier research on climate science

🎯 **Climate/Environment Research Resources:**
• Cluster 5 Work Programme: [Climate, Energy, Mobility](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• Cluster 6 Work Programme: [Food, Bioeconomy, Natural Resources](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• EU Mission Climate Adaptation: [Climate Mission Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/adaptation-climate-change_en)
• EU Mission Ocean: [Ocean Mission Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/restore-our-ocean-and-waters_en)
• EU Mission Soil: [Soil Mission Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/soil-deal-europe_en)
• European Green Deal: [Green Deal Priorities](https://commission.europa.eu/strategy-and-policy/priorities-2019-2024/european-green-deal_en)
• MSCA Portal: [MSCA Actions](https://marie-sklodowska-curie-actions.ec.europa.eu/)

#### Example: Agriculture/Food Research Calls

Agriculture and food research is covered by **Cluster 6: Food, Bioeconomy, Natural Resources, Agriculture and Environment**. Include:

**Primary: Cluster 6 - Food, Bioeconomy, Natural Resources (HORIZON-CL6-*):**
- Sustainable farming systems and agroecology
- Food systems and nutrition security
- Biodiversity and natural capital
- Circular and bio-based solutions
- Forestry and wood-based industries
- Water, soil, and land management

**Call ID Patterns (Cluster 6):**
- `HORIZON-CL6-*-FARM2FORK-*`: Farm to Fork sustainable food systems
- `HORIZON-CL6-*-BIODIV-*`: Biodiversity and ecosystem services
- `HORIZON-CL6-*-CIRCBIO-*`: Circular bioeconomy
- `HORIZON-CL6-*-ZEROPOL-*`: Zero pollution agriculture
- `HORIZON-CL6-*-GOVERNANCE-*`: Land and resource governance

**Relevant EU Missions (ALWAYS mention for agriculture/food):**
- **Mission: A Soil Deal for Europe** (HORIZON-MISS-*-SOIL-*): Soil health, sustainable land use, 100 living labs by 2030
- **Mission: Restore our Ocean and Waters** (HORIZON-MISS-*-OCEAN-*): Water quality, sustainable aquaculture
- **Mission: Adaptation to Climate Change** (HORIZON-MISS-*-CLIMA-*): Climate-resilient agriculture

**Cross-Cutting Opportunities:**
- **MSCA**: MSCA-PF and MSCA-DN for agricultural/food researchers (ANY domain)
- **EIC Pathfinder**: Breakthrough agritech innovations
- **ERC**: Frontier research in agriculture and food science

🎯 **Agriculture/Food Research Resources:**
• Cluster 6 Work Programme: [Food, Bioeconomy, Natural Resources](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• EU Mission Soil: [Soil Mission Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/soil-deal-europe_en)
• Farm to Fork Strategy: [Farm to Fork](https://food.ec.europa.eu/horizontal-topics/farm-fork-strategy_en)
• EU Bioeconomy: [Bioeconomy Strategy](https://research-and-innovation.ec.europa.eu/research-area/environment/bioeconomy_en)
• MSCA Portal: [MSCA Actions](https://marie-sklodowska-curie-actions.ec.europa.eu/)
• Search Cluster 6 calls: [EU Portal - Cluster 6](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=null;freeTextSearchKeyword=;matchWholeText=true;typeCodes=1,0;statusCodes=31094501,31094502;programmePeriod=2021%20-%202027;programCcm2Id=43108390;programDivisionCode=43108567)

#### Example: Digital Cultural Heritage Research (MULTIDISCIPLINARY)

Digital cultural heritage is inherently **multidisciplinary**, spanning Cluster 2 (Culture) and Cluster 4 (Digital). Include:

**Primary: Cluster 2 - Culture, Creativity and Inclusive Society (HORIZON-CL2-*):**
- Cultural heritage preservation and restoration
- Digitization of cultural assets (3D scanning, semantic modeling)
- Participatory approaches to heritage
- European identity and cultural diversity
- New European Bauhaus initiatives

**Secondary: Cluster 4 - Digital, Industry and Space (HORIZON-CL4-*):**
- Digital twin technologies
- AI and machine learning for cultural applications
- Advanced sensor systems and monitoring
- Immersive technologies (VR/AR for heritage)
- Data management and interoperability

**Call ID Patterns (Cultural Heritage):**
- `HORIZON-CL2-*-HERITAGE-*`: Dedicated heritage preservation topics
- `HORIZON-CL2-*-DEMOCRACY-*`: Heritage in democratic societies
- `HORIZON-CL4-*-TWIN-*`: Digital twin technologies
- `HORIZON-CL4-*-DATA-*`: Data spaces for culture

**Key Reference Projects (for benchmarking):**
| Project | Grant ID | Focus | CORDIS Link |
|---------|----------|-------|-------------|
| **ARIADNE-PLUS** | 823914 | Archaeological data infrastructure | cordis.europa.eu/project/id/823914 |
| **Time Machine** | 820323 | Big data for historical digitization | cordis.europa.eu/project/id/820323 |
| **INCEPTION** | 665220 | 3D semantic modelling for heritage | cordis.europa.eu/project/id/665220 |

**Cross-Cutting Opportunities:**
- **MSCA**: MSCA-PF and MSCA-DN for heritage researchers
- **EIC Pathfinder**: Breakthrough technologies for cultural heritage
- **Creative Europe**: Complementary funding for cultural projects

🎯 **Digital Cultural Heritage Resources:**
• Cluster 2 Work Programme: [Culture, Creativity](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• New European Bauhaus: [NEB Portal](https://new-european-bauhaus.europa.eu/)
• EU Digital Strategy for Culture: [Digital Culture](https://digital-strategy.ec.europa.eu/en/policies/cultural-heritage)
• Europeana: [European Cultural Heritage](https://www.europeana.eu/)
• CORDIS Heritage Projects: [Search CORDIS](https://cordis.europa.eu/search?q=cultural%20heritage)

### Niche Topic Search Keywords (for Project Searches)

When searching for projects at the intersection of multiple specialized topics, use these expanded keyword sets:

#### Industry 4.0/5.0 Keywords (expand searches with these)
| Core Terms | Technology Terms | Application Terms |
|------------|-----------------|-------------------|
| Industry 4.0 | IoT, sensors | smart farming |
| Industry 5.0 | AI, machine learning | precision agriculture |
| digitalization | robotics, automation | digital twin |
| digital transformation | data-driven | smart monitoring |
| cyber-physical systems | edge computing | predictive analytics |
| human-machine collaboration | big data | real-time monitoring |

#### Soil Regeneration Keywords (expand searches with these)
| Core Terms | Scientific Terms | Practice Terms |
|------------|-----------------|----------------|
| soil regeneration | carbon sequestration | regenerative agriculture |
| soil health | soil microbiome | agroecology |
| soil restoration | soil organic matter | no-till farming |
| land degradation | nutrient cycling | cover cropping |
| soil fertility | soil biodiversity | composting |
| soil remediation | erosion control | sustainable farming |

**Example Multi-Search Strategy for "Industry 4.0 + Soil Regeneration":**
```
Search 1: "digital agriculture soil health monitoring" - core intersection
Search 2: "precision farming regenerative soil sensors" - technology + application
Search 3: "smart soil monitoring carbon sequestration" - monitoring focus
Search 4: "AI machine learning soil management agriculture" - AI applications
Search 5: "IoT sensors sustainable farming soil" - IoT applications
```

#### SSH/Cluster 2 Keywords (Culture, Creativity & Inclusive Society)
| Core Terms | Governance Terms | Social Terms | Policy Evaluation Terms |
|------------|-----------------|--------------|------------------------|
| democracy | governance | social cohesion | policy evaluation |
| cultural heritage | policy | inclusive society | impact assessment |
| European identity | citizenship | migration | monitoring indicators |
| humanities | participation | inequality | socioeconomic analysis |
| creative industries | rule of law | gender equality | welfare systems |
| arts and culture | transparency | diversity inclusion | labor market policy |

**SSH/Cluster 2 Search Strategy:**
```
Search 1: "democracy governance society" → Core SSH
Search 2: "cultural heritage European identity" → Heritage focus
Search 3: "social cohesion inclusion migration" → Social science
Search 4: "creative industries culture arts" → Creative/arts focus
Search 5: "policy participation citizenship" → Governance focus
Search 6: "policy evaluation monitoring socioeconomic" → Policy evaluation focus
```

**Top SSH/Cluster 2 Coordinators (Reference):**
Major coordinators in Cluster 2/SSH typically include:
- Utrecht University (UU) - NL - Strong in democracy, governance
- University of Bologna (UNIBO) - IT - Humanities, heritage
- Politecnico di Milano (POLIMI) - IT - Design, creative industries
- KU Leuven - BE - Social sciences, humanities
- University of Amsterdam (UvA) - NL - Culture, media, social sciences
- Leiden University (ULEI) - NL - Humanities, area studies
- University of Barcelona (UB) - ES - Heritage, social sciences
- Lund University - SE - Humanities, social sciences
- University of Helsinki - FI - Social sciences, governance
- Radboud University - NL - Social sciences, humanities

#### Cultural Heritage Keywords (CRITICAL for heritage project searches)
| Core Terms | Technology Terms | Application Terms |
|------------|-----------------|-------------------|
| cultural heritage | digital twin | heritage preservation |
| heritage digitization | 3D scanning | monument restoration |
| cultural preservation | AI preservation | museum digitization |
| archaeological | VR heritage | historic buildings |
| heritage sites | AR cultural | restoration technology |
| cultural assets | semantic modeling | heritage monitoring |

**CRITICAL: Search Strategy for "Digital Cultural Heritage" Projects:**
The search_projects tool uses SIMPLE KEYWORD MATCHING. Use SHORT, SPECIFIC terms:
```
Search 1: "cultural heritage" → Best general term, yields most results
Search 2: "heritage digitization" → Technology focus
Search 3: "archaeological data" → Archaeological projects
Search 4: "heritage preservation digital" → Preservation + digital
Search 5: "3D heritage" → 3D scanning/modeling projects
```

**DO NOT USE:**
- Long complex phrases (e.g., "interdisciplinary project in digital tech preservation of cultural heritage")
- Multiple concepts together (e.g., "digital twining predictive maintenance heritage participatory")

**ALWAYS USE:**
- 2-3 word simple keywords (e.g., "cultural heritage", "heritage digital", "archaeological")
- Run MULTIPLE searches with different simple keywords if first search yields no results
- If first search returns 0 results, immediately try alternative simpler keywords

#### Water/Health/Sanitation Keywords (CRITICAL for water-health project searches)
| Core Terms | Health Terms | Infrastructure Terms |
|------------|-------------|---------------------|
| drinking water | water quality health | sewage systems |
| water sanitation | waterborne disease | wastewater treatment |
| water health | public health water | water infrastructure |
| urban water | environmental health | sanitation systems |
| rural water | health impact water | water pollution |
| aquatic health | epidemiology water | water management |

**CRITICAL: Search Strategy for "Water/Health" Projects:**
Water and health intersection spans MULTIPLE clusters (Cluster 1: Health AND Cluster 6: Environment). Use SHORT, SPECIFIC terms:
```
Search 1: "drinking water health" → Core intersection
Search 2: "water quality sanitation" → Infrastructure focus
Search 3: "waterborne disease" → Health impact focus
Search 4: "urban water health" → Urban context
Search 5: "aquatic health ecosystem" → Environmental health (Cluster 6 projects)
Search 6: "water pollution health" → Pollution + health impact
```

**Key Reference Projects for Water/Health (use as fallback):**
| Project | Grant ID | Focus | Budget | Coordinator |
|---------|----------|-------|--------|-------------|
| **OneAquaHealth** | 101086521 | One Health approach for urban aquatic ecosystems | €4.94M | Universidade de Coimbra (PT) |
| **StopUP** | 101060428 | Protecting aquatic environment from urban runoff pollution | €3.77M | RWTH Aachen (DE) |
| **AquaticPollutants** | 869178 | Contaminants in water resources | €4.0M | INRAE (FR) |
| **PARC** | 101057014 | Chemical risk assessment for human health and environment | €400M | ANSES (FR) |
| **GloFouling** | 774009 | Invasive species via biofouling, ecosystem and health impacts | €3.6M | IMO (UK) |

**Call ID Patterns for Water/Health:**
- `HORIZON-CL6-*-ZEROPOL-*`: Zero pollution in water (Cluster 6)
- `HORIZON-CL6-*-WATER-*`: Sustainable water management (Cluster 6)
- `HORIZON-HLTH-*-ENVHLTH-*`: Environmental determinants of health (Cluster 1)
- `HORIZON-MISS-*-OCEAN-*`: EU Mission: Restore our Ocean and Waters
- `HORIZON-MISS-*-SOIL-*`: EU Mission: Soil (linked to water quality)

#### Example: Water/Health Research Calls (MULTIDISCIPLINARY)

Water and health research is **inherently multidisciplinary** - it spans Cluster 1 (Health), Cluster 6 (Environment), and EU Missions. Include:

**Primary: Cluster 6 - Food, Bioeconomy, Natural Resources (HORIZON-CL6-*) - Water Focus:**
- Zero Pollution destination: Water quality, pollution prevention, wastewater treatment
- Healthy Oceans and Waters: Freshwater ecosystems, drinking water sources
- Sustainable water management and governance
- Nature-based solutions for water treatment

**Secondary: Cluster 1 - Health (HORIZON-HLTH-*) - Health Impact Focus:**
- Destination 4: Environmental determinants of health
- Non-communicable diseases linked to environmental exposure
- Infectious disease prevention (waterborne pathogens)
- Digital health and monitoring systems

**Relevant EU Missions (ALWAYS mention for water/health):**
- **Mission: Restore our Ocean and Waters** (HORIZON-MISS-*-OCEAN-*): Water quality, pollution reduction, healthy aquatic ecosystems
- **Mission: A Soil Deal for Europe** (HORIZON-MISS-*-SOIL-*): Soil health affects water quality, groundwater protection
- **Mission: Adaptation to Climate Change** (HORIZON-MISS-*-CLIMA-*): Water scarcity, drought adaptation

**Cross-Cutting Opportunities:**
- **MSCA**: MSCA-PF and MSCA-DN for water/health researchers (ANY domain)
- **EIC Pathfinder**: Breakthrough water treatment technologies
- **ERC**: Frontier research in environmental health

🎯 **Water/Health Research Resources:**
• Cluster 6 Work Programme (Water): [Food, Bioeconomy, Natural Resources](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• Cluster 1 Work Programme (Health): [Health Cluster](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• EU Mission Ocean & Waters: [Ocean Mission Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/restore-our-ocean-and-waters_en)
• EU Zero Pollution Action Plan: [Zero Pollution](https://environment.ec.europa.eu/strategy/zero-pollution-action-plan_en)
• CORDIS Water Projects: [Search CORDIS](https://cordis.europa.eu/search?q=water%20health)

### Third Country Eligibility and Participation (Non-EU, Non-Associated Countries)

When a researcher asks about eligibility from a **non-EU, non-Associated country** (e.g., Japan, USA, China, South Korea, Australia, Canada, Brazil, India), provide this guidance:

#### Country Classification

| Category | Countries | Horizon Europe Participation |
|----------|-----------|------------------------------|
| **EU Member States (27)** | AT, BE, BG, CY, CZ, DE, DK, EE, EL, ES, FI, FR, HR, HU, IE, IT, LT, LU, LV, MT, NL, PL, PT, RO, SE, SI, SK | ✅ Full eligibility, full funding |
| **Associated Countries** | CH*, IL*, IS, NO, UK*, AL, BA, XK, ME, MK, RS, TR, GE, MD, UA | ✅ Full eligibility (check current status) |
| **Third Countries** | Japan, USA, China, South Korea, Australia, Canada, Brazil, India, etc. | ⚠️ Limited participation, restrictions apply |

*Check association status - some may be pending/suspended (e.g., Switzerland since 2021)*

#### Third Country Participation Rules

**Key Facts:**
- Third country organizations are **NOT automatically eligible** for EU funding
- Participation is possible but with **significant restrictions**
- Must check **specific call text** for third country eligibility conditions
- When allowed, typically must be **self-funded** (no EU contribution to third country partners)
- **Cannot be consortium coordinator** in most collaborative calls
- May need existing **bilateral agreements** or specific topic exceptions

#### Best Pathways for Third Country Researchers

| Pathway | Eligibility | Funding | Description |
|---------|-------------|---------|-------------|
| **MSCA-PF (Postdoctoral Fellowships)** | ✅ **BEST OPTION** | Full EU funding | Move to EU/AC host institution; €200-300K fellowship; 12-24 months |
| **ERC Grants** | ✅ Yes (at EU host) | Full EU funding | Work at EU/AC institution; Starting €1.5M, Consolidator €2M, Advanced €2.5M |
| **Collaborative Projects (partner)** | ⚠️ Check topic | Usually self-funded | Join consortium as partner; check call conditions |
| **Bilateral Programmes** | ✅ Varies | Shared funding | Japan-EU, US-EU joint programmes may offer funded options |

#### MSCA-PF: The Primary Pathway for Third Country Researchers

**MSCA Postdoctoral Fellowships are the MOST accessible option** for researchers from third countries:

1. **Eligibility**: PhD holders (or 4+ years research experience) of ANY nationality
2. **Requirement**: Must move to and conduct research at an EU or Associated Country host institution
3. **Types**:
   - **European Fellowships (EF)**: Research in any EU/AC country (12-24 months)
   - **Global Fellowships (GF)**: Outgoing phase to third country (12-24m) + mandatory return to EU (12m)
4. **Funding**: Full EU funding including living allowance (~€5,080/month), mobility (~€600/month), research costs
5. **Deadline**: Usually September each year (check EU Portal for exact dates)

#### ERC Grants for Third Country Nationals

**ERC grants are open to researchers of any nationality** if they meet these conditions:
- Must conduct research at an **EU or Associated Country host institution**
- Must commit to spend 50%+ of research time at EU/AC host
- Scientific excellence is the only criterion (no nationality restrictions on PI)

| Grant Type | Career Stage | Funding | Duration |
|------------|--------------|---------|----------|
| ERC Starting | 2-7 years post-PhD | Up to €1.5M | 5 years |
| ERC Consolidator | 7-12 years post-PhD | Up to €2M | 5 years |
| ERC Advanced | Track record of 10+ years | Up to €2.5M | 5 years |

#### Collaborative Projects: Checking Third Country Eligibility

For RIA/IA/CSA collaborative calls:

1. **Read the call text carefully** - look for "Eligibility" section
2. **Check for phrases like**:
   - "Entities from third countries may participate"
   - "Third country participation is eligible for funding in exceptional cases"
   - "Organizations from [specific countries] are automatically eligible"
3. **If allowed**:
   - Usually as **partner only** (not coordinator)
   - Typically **self-funded** (bring own funding or co-funding)
   - Must bring essential expertise/infrastructure not available in EU
4. **Some topics have automatic third country eligibility** - check Work Programme

#### Third Country Participation Key Resources

🎯 **For Third Country Researchers:**
• MSCA Portal (primary pathway): [MSCA Actions](https://marie-sklodowska-curie-actions.ec.europa.eu/)
• ERC Opportunities: [ERC Grants](https://erc.europa.eu/funding/starting-grants)
• EU Funding Portal: [Search Open Calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search)
• Check Eligibility: [How to Participate](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/how-to-participate/1)
• Third Country Rules: [Third Country Participation Guide](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf)

**For Japan Specifically:**
• JSPS Brussels Office: [JSPS EU Liaison](https://www.jsps-sto.se/) - Japanese NCP for Horizon Europe
• JST International: [JST International Programmes](https://www.jst.go.jp/inter/english/) - Potential bilateral opportunities

**For Other Third Countries:**
• Check your country's NCP or science agency for bilateral EU programmes
• Many countries have funded joint calls with EU (e.g., NSF-EU, UKRI-EU)

### Strategic Funding Planning (Multi-Year Strategy)

When users ask about funding strategy, multi-year planning, or application sequencing, provide this guidance:

**Strategic Planning Framework:**
1. **Year 1: Build Track Record** - Start with smaller actions (MSCA, Widening, CSA as partner)
2. **Year 2: Expand Portfolio** - Target main RIA/IA calls in your cluster, consider coordinating
3. **Year 3: Lead & Scale** - Coordinate larger projects, leverage track record

**Organization-Specific Recommendations:**
| Org Type | Recommended Starting Points | Primary Pathways |
|----------|----------------------------|------------------|
| **University (HES)** | MSCA, Widening, RIA as partner | Cluster RIA → ERC → Large-scale |
| **Research Institute (REC)** | RIA as partner, CSA coordination | RIA → IA demonstration → ERC |
| **SME** | Eurostars, EIC Pathfinder, IA as partner | EIC Transition → EIC Accelerator |
| **Public Body** | CSA, Missions, Widening | CSA → RIA co-coordinator |

**Application Sequencing Tips:**
• Check the annual work programme calendar (published in May/June for next year)
• Plan for 6-9 months of proposal preparation time
• Build consortium relationships before call opening
• Consider multiple submissions per year across different clusters

🎯 **Getting Started with Strategic Planning:**
• Review the multi-annual [Work Programme structure](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents)
• Identify your 2-3 target clusters based on research focus
• Connect with your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for personalized advice
• Use [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) to find experienced consortium partners
"""

# Section-based knowledge for selective injection
# Keys map to content sections within BUILT_IN_KNOWLEDGE
KNOWLEDGE_SECTIONS = {
    "core": """## Quick Reference: Horizon Europe Facts

### Official Resources (ALWAYS include when explaining programme structure)
When answering questions about Horizon Europe structure, ALWAYS include these actionable links at the end:

🎯 **Getting Started with Horizon Europe:**
• Register on [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)
• Review the [Work Programmes](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON) for your cluster
• Check eligibility via [How to Participate](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/how-to-participate/1)
• Find partners using [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search)
• Browse [Call Calendar](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/calls-calendar)

### Consortium Requirements
- **Standard (RIA/IA/CSA)**: 3 independent entities from 3 different EU/AC countries
- **ERC**: Single PI (monobeneficiary)
- **MSCA PF**: Single fellow + host
- **EIC Accelerator**: Single SME or small group
""",
    "eligibility": """### Organisation Type Eligibility
| Organisation Type | Eligible? | Funding Rate (RIA) | Funding Rate (IA) | Special Notes |
|-------------------|-----------|-------------------|-------------------|---------------|
| **Universities/HEIs** | Yes | 100% | 100% | Must have GEP |
| **Research Institutes** | Yes | 100% | 100% | Must have GEP |
| **SMEs** | Yes | 100% | 70% | EIC Accelerator available |
| **Large Companies** | Yes | 100% | 70% | Cannot lead some calls |
| **NGOs** | Yes | 100% | 100% (non-profit) | Often needed for dissemination |
| **Public Bodies** | Yes | 100% | 100% | Must have GEP |
| **International Orgs** | Case-by-case | Varies | Varies | Check specific call |
""",
    "page_limits": """### Page Limits for Proposals (Part B - Technical Description)
| Action Type | Standard Page Limit | Notes |
|-------------|---------------------|-------|
| **RIA/IA (single-stage)** | **45 pages** | Sections 1-3 combined |
| **RIA/IA (two-stage, full)** | **45 pages** | After passing stage 1 |
| **RIA/IA (two-stage, outline)** | **10 pages** | Stage 1 only |
| **CSA** | **30 pages** | Shorter scope |
| **ERC grants** | **Variable** | Check specific call |
| **MSCA** | **10-15 pages** | Depends on action |
| **EIC Accelerator** | **Variable** | Short proposal + full |

*Page limits are strictly enforced. Excess pages will be blanked and not evaluated.*
""",
    "action_types": """### Action Types Summary
| Type | TRL Range | Funding Rate | Focus |
|------|-----------|--------------|-------|
| **RIA** | TRL 2-5 | 100% | Research, new knowledge |
| **IA** | TRL 5-8 | 70%/100% | Demonstration, piloting |
| **CSA** | N/A | 100% | Coordination, networking |

### Typical Consortium Sizes (Based on Funded Project Data)
| Action Type | Avg Partners | Typical Range | Avg Countries | Key Characteristics |
|-------------|--------------|---------------|---------------|---------------------|
| **RIA** | 10-12 | 6-16 | 6-8 | Research focus, strong academic presence, TRL 1-5 |
| **IA** | 14-16 | 10-20 | 8-10 | Demo/scale-up, more industry partners (35-45%), TRL 5-8 |
| **CSA** | 6-9 | 3-12 | 4-6 | Coordination/networking, smaller focused teams, policy focus |

### Budget Limits / Expected EU Contribution per Project
| Action Type | Typical EU Contribution Range | Notes |
|-------------|------------------------------|-------|
| **RIA (standard)** | €3-8 million | Varies by topic complexity |
| **IA (standard)** | €5-15 million | Large-scale demonstrations |
| **CSA** | €1-3 million | Coordination activities |
| **ERC Starting** | Up to €1.5 million | 5 years |
| **ERC Consolidator** | Up to €2 million | 5 years |
| **ERC Advanced** | Up to €2.5 million | 5 years |
| **EIC Accelerator** | Up to €2.5M grant + €15M equity | Blended finance |
""",
    "clusters": """### Horizon Europe Clusters and EU Missions - Complete Overview

#### The 6 Thematic Clusters
| Cluster | Name | Focus Areas | Budget (2021-2027) |
|---------|------|-------------|-------------------|
| **Cluster 1** | Health | Disease prevention, treatment, healthcare systems | ~€8.2 billion |
| **Cluster 2** | Culture, Creativity & Inclusive Society | Democracy, governance, cultural heritage | ~€2.3 billion |
| **Cluster 3** | Civil Security for Society | Cybersecurity, disaster resilience, border security | ~€1.6 billion |
| **Cluster 4** | Digital, Industry & Space | AI, robotics, advanced manufacturing, quantum | ~€15.3 billion |
| **Cluster 5** | Climate, Energy & Mobility | Clean energy, hydrogen, sustainable transport | ~€15.1 billion |
| **Cluster 6** | Food, Bioeconomy, Natural Resources | Sustainable food, biodiversity, circular economy | ~€9 billion |

#### The 5 EU Missions
| Mission | Target |
|---------|--------|
| **Cancer** | Improve lives of 3+ million people |
| **Climate Adaptation** | 150+ regions climate-resilient by 2030 |
| **Ocean & Waters** | Restore ocean/water health by 2030 |
| **Cities** | 100 cities climate-neutral by 2030 |
| **Soil** | 100 living labs for healthy soils by 2030 |
""",
    "third_countries": """### Third Country Eligibility and Participation
| Category | Countries | Participation |
|----------|-----------|---------------|
| **EU Member States (27)** | AT, BE, BG, CY, CZ, DE, DK, EE, EL, ES, FI, FR, HR, HU, IE, IT, LT, LU, LV, MT, NL, PL, PT, RO, SE, SI, SK | Full eligibility |
| **Associated Countries** | CH*, IL*, IS, NO, UK*, AL, BA, XK, ME, MK, RS, TR, GE, MD, UA | Full eligibility (check status) |
| **Third Countries** | Japan, USA, China, etc. | Limited, restrictions apply |

**Best Pathways for Third Country Researchers:**
- **MSCA-PF**: Best option — full EU funding, move to EU host
- **ERC Grants**: Work at EU institution
- **Collaborative Projects**: Usually self-funded, partner only
""",
    "strategic": """### Getting Started with Proposal Writing
1. **Find a relevant call** on the EU Funding & Tenders Portal
2. **Understand the call**: Read Work Programme topic — scope, outcomes, criteria
3. **Build your consortium**: 3+ partners from 3+ different EU/AC countries
4. **Write the proposal**: Excellence, Impact, Implementation sections
5. **Use search tools**: Find similar funded projects to learn from

### Evaluation Criteria
| Section | Threshold | Weight |
|---------|-----------|--------|
| Excellence | 4/5 | ~1/3 |
| Impact | 4/5 | ~1/3 |
| Implementation | 3/5 | ~1/3 |
| **Overall** | **10/15** | - |

### RIA Project Details
- **Duration**: 36-48 months typical, up to 60 months
- **Budget**: €3-10 million, 100% funding rate
- **Payment**: Pre-financing 40-50%, interim at 18 months, final after review
- **Indirect costs**: 25% flat rate on direct costs minus subcontracting
""",
    "msca": """### Marie Skłodowska-Curie Actions (MSCA)
MSCA is part of Pillar I (Excellent Science), budget €6.6 billion (2021-2027).

| Action | Budget | Duration | Funding |
|--------|--------|----------|---------|
| **MSCA-PF** | €200-300K/fellow | 12-24 months | 100% |
| **MSCA-DN** | €2-4M/network | 48 months | 100% |
| **MSCA-SE** | €0.5-1.5M | 48 months | 100% |
| **MSCA-COFUND** | €10M max | 60 months | 100% |
""",
}


# System prompt for the reasoning LLM
REASONING_PROMPT = """You are an intelligent EU funding research assistant covering Horizon Europe, Erasmus+, Creative Europe, EU4Health, Digital Europe, and LIFE. You help researchers and organizations find funding, plan proposals, discover partners, and navigate EU programmes.

## Built-in Knowledge
{built_in_knowledge}

## Available Tools
{tools_description}

## Conversation History
{context}

## Current User Message
{query}

## Previous Reasoning Steps
{previous_steps}

## Tool Results So Far
{tool_results}

## Your Task

1. **UNDERSTAND** the user's intent from their message and conversation history. Resolve references to previous results ("the 3rd one", "tell me more about it"). Use accumulated context (org type, country, sector, experience level) to personalize tool parameters and recommendations.
2. **DECIDE** whether to answer from built-in knowledge, call tools, or conclude from existing tool results.
3. **EXECUTE** by calling the right tools with extracted keywords (never pass the full user message as a search query).
4. **CONCLUDE** with a synthesized, well-structured answer when you have sufficient data.

**Tool selection principles:**
- Answer from BUILT-IN KNOWLEDGE when it fully covers the question (eligibility, action types, clusters, MSCA, general guidance) — no tools needed
- Short keyword project/call searches → search_projects or search_funding_calls
- Long descriptions or broad concepts → get_similar_funded_projects (semantic search)
- Specific call/project IDs → get_call_details or get_project_details
- Budget planning → calculate_budget or get_budget_benchmark (NOT search_documents)
- Timeline/WPs/milestones → generate_timeline (NOT search_documents)
- Partner discovery → find_experienced_partners (NOT search_documents)
- Organization stats/projects → get_organization_stats or find_organization_projects
- Collaboration networks → get_collaboration_network
- Statistics → get_programme_statistics or get_country_statistics
- Consortium patterns → get_consortium_patterns
- Comparisons → call relevant tools in parallel, then cross-analyze
- search_documents is ONLY for looking up official rules and regulations
- Context-building statements (no explicit question) → respond proactively with relevant guidance and a follow-up question

## Response Format

Respond ONLY with valid JSON (no other text):
```json
{{
    "thought": "What does the user want? What do I know vs need to look up?",
    "action": "call_tools" | "conclude" | "generate_guidance",
    "tool_calls": [
        {{
            "tool": "tool_name",
            "parameters": {{"param1": "value1"}},
            "reasoning": "Why this tool answers the query"
        }}
    ],
    "needs_more_info": true | false,
    "conclusion": "Final answer in markdown (only when action is 'conclude')",
    "response": "Guidance text (only when action is 'generate_guidance')",
    "confidence": 0.8
}}
```

## Core Rules

1. **Always respond with valid JSON.** No text outside the JSON block.
2. **Extract key terms** from the query — never pass the full user message as a search parameter (e.g., search "consortium eligibility" not "I want to know about consortium eligibility requirements for my project").
3. **Call multiple tools in parallel** when they are independent (e.g., statistics + calls for a comparison query).
4. **Use built-in knowledge** for common questions (eligibility, action types, clusters, MSCA) — no tool needed.
5. **Show ALL relevant results** (up to 10), not just 2-3. Include identifiers (call IDs, grant agreement numbers) so users can reference them.
6. **Stay focused** — only answer what was asked. Do not proactively fetch partners when the user asked for projects, or search calls when they asked for statistics. If iteration 1 returned good results, conclude — do not add unrequested extras in iteration 2.

## When to Conclude

**CONCLUDE IMMEDIATELY** (action: "conclude") when:
- A tool returned structured data that directly answers the query (budget, timeline, statistics, eligibility check)
- 5+ relevant search results found and no cross-referencing is needed
- You can answer fully from built-in knowledge
- A self-sufficient tool succeeded (generate_timeline, calculate_budget, any eligibility checker, any budget calculator, score_proposal_section, score_full_proposal, validate_budget)

**CONTINUE** (needs_more_info: true) ONLY when:
- 0-2 results found and the query clearly needs more data
- A comparison requires results from a different, uncalled tool
- A tool returned an error and you have an alternative approach
- Multi-tool cross-analysis is explicitly needed (e.g., comparing partner lists from two projects)

**NEVER continue when:**
- Good data already exists and just needs formatting into a clear answer
- A single tool already answered the question
- 3+ iterations completed — conclude with what you have
- You want to call search_documents "for completeness" after a specialized tool already succeeded

## Cross-Analysis Pattern

When the query requires comparing or combining data from multiple sources:

**Iteration 1**: Call all necessary tools in parallel (action: "call_tools", needs_more_info: true)
**Iteration 2**: Analyze combined results — find patterns, overlaps, differences — then conclude with a synthesized answer using markdown tables and headings.

Examples:
- "Compare partners of Project A and B" → get_project_partners for both in parallel, then cross-reference
- "Compare RIA vs IA consortium sizes" → get_consortium_patterns for each, then comparison table
- "Find hydrogen calls and check eligibility" → search_funding_calls + relevant eligibility tool in parallel

Key principle: if results from one tool need analysis alongside another tool's results, do NOT conclude after iteration 1. Set needs_more_info=true and wait for all results.

## Response Quality

When concluding:
- **Synthesize** information from tool results into a coherent answer — never copy raw document fragments.
- **Use markdown**: headings, bullet points, tables for readability.
- **Include identifiers**: call IDs, grant agreement numbers, CORDIS links (https://cordis.europa.eu/project/id/PROJECT_ID).
- **For partner discovery**: list at least 5-10 organizations with full details (name, type, projects, funding, expertise).
- **For tool outputs like timelines and budgets**: include the COMPLETE output without truncation — users need full details for proposals.
- **For context-building messages** (user shares info without a question): acknowledge their context, offer relevant guidance, and ask a clarifying follow-up.
- **Cite sources** in your conclusion (tool names, document titles, call IDs).

## Relevance Filtering — CRITICAL

Before writing your conclusion, evaluate EACH tool result against the original user query:

**Ask for each tool result:**
- Does this directly answer what the user asked for?
- If the user asked for "X in Y" (e.g., "SMEs in France"), does this result contain X AND Y?
- Is this result context or the actual answer?

**Include ONLY relevant results:**
- ✅ User: "Find SMEs in France with hydrogen experience"
  - Include: `find_experienced_partners` results filtered to France + SME status
  - Include: Specific project partners that are French SMEs
  - EXCLUDE: General project listings, country statistics, large companies, non-French partners

- ✅ User: "What's the budget for CL5 projects?"
  - Include: `get_programme_statistics` for CL5, `get_budget_benchmark` results
  - EXCLUDE: Partner searches, call listings, project details (unless for budget context)

- ✅ User: "Compare RIA vs IA success rates"
  - Include: Statistics for both action types, comparison table
  - EXCLUDE: Individual projects, partner searches, eligibility rules

**Pattern matching examples:**
- "Find X in Y" → Only show results matching BOTH X and Y
- "How many/What is/Compare" → Statistics and direct answers
- "Find partners with Z experience" → Partner results with Z, not general project lists
- "Tell me more about [specific item]" → Details about that specific item only

If NO tool result directly answers the query, state that clearly and suggest what would help.

**Every response MUST end with actionable next steps:**
```
---
🎯 **Next Steps:**
• [Specific action 1 — e.g., register on EU Funding Portal]
• [Specific action 2 — e.g., download the 2025 Work Programme]
• [Specific action 3 — e.g., contact your National Contact Point]
```

What is your next step? Remember: Output ONLY JSON."""
