# EU Funding Domain Knowledge Skill

This skill encodes EU funding programme terminology, structures, and rules to prevent hallucinations and ensure accurate domain-specific responses.

## Programme Overview

| Programme | Focus | Budget (2021-2027) | Main Actions |
|-----------|-------|-------------------|--------------|
| **Horizon Europe** | Research & Innovation | €95.5 billion | RIA, IA, CSA, ERC, MSCA, EIC |
| **Erasmus+** | Education, Training, Youth, Sport | €26.2 billion | KA1, KA2, KA3, Jean Monnet, Sport |
| **Creative Europe** | Culture, Media, Cross-sectoral | €2.44 billion | CULTURE, MEDIA, CROSS-SECTORAL |
| **EU4Health** | Health systems, Crisis preparedness | €5.3 billion | Grants, Joint Actions, Procurement |
| **Digital Europe** | Digital transformation | €7.5 billion | HPC, AI, Cybersecurity, Skills |
| **LIFE** | Environment, Climate action | €5.4 billion | Nature, Circular, Climate mitigation |

---

## Horizon Europe Structure

### Pillars and Clusters

```
PILLAR I - Excellent Science
├── ERC (European Research Council) - Frontier research
├── MSCA (Marie Skłodowska-Curie Actions) - Researcher mobility
└── Research Infrastructures

PILLAR II - Global Challenges & European Industrial Competitiveness
├── CLUSTER-1: Health
├── CLUSTER-2: Culture, Creativity & Inclusive Society
├── CLUSTER-3: Civil Security for Society
├── CLUSTER-4: Digital, Industry & Space
├── CLUSTER-5: Climate, Energy & Mobility
└── CLUSTER-6: Food, Bioeconomy, Natural Resources

PILLAR III - Innovative Europe
├── EIC (European Innovation Council) - Breakthrough innovation
├── EIT (European Institute of Innovation & Technology)
└── European Innovation Ecosystems
```

### Action Types and Funding Rates

| Action Type | Full Name | Funding Rate | Typical Budget | TRL Focus |
|-------------|-----------|--------------|----------------|-----------|
| **RIA** | Research & Innovation Action | 100% | €3-10M | TRL 1-5 |
| **IA** | Innovation Action | 70% (100% non-profit) | €5-20M | TRL 5-8 |
| **CSA** | Coordination & Support Action | 100% | €1-3M | N/A |
| **ERC-STG** | ERC Starting Grant | 100% | €1.5M | TRL 1-3 |
| **ERC-COG** | ERC Consolidator Grant | 100% | €2M | TRL 1-3 |
| **ERC-ADG** | ERC Advanced Grant | 100% | €2.5M | TRL 1-3 |
| **ERC-POC** | ERC Proof of Concept | 100% | €150K | TRL 3-4 |
| **MSCA-PF** | Postdoctoral Fellowship | 100% | €200-300K | N/A |
| **MSCA-DN** | Doctoral Network | 100% | €2-4M | N/A |
| **EIC-Pathfinder** | High-risk breakthrough | 100% | €3-4M | TRL 1-4 |
| **EIC-Transition** | Lab to market | 100% | €0.5-2.5M | TRL 4-6 |
| **EIC-Accelerator** | Scale-up support | 70% grant + equity | €2.5M + €15M | TRL 6-9 |

### TRL (Technology Readiness Level)

| TRL | Description | Horizon Europe Focus |
|-----|-------------|---------------------|
| 1 | Basic principles observed | ERC, RIA |
| 2 | Technology concept formulated | ERC, RIA |
| 3 | Experimental proof of concept | ERC, RIA, EIC-Pathfinder |
| 4 | Technology validated in lab | RIA, EIC-Transition |
| 5 | Technology validated in relevant environment | RIA, IA |
| 6 | Technology demonstrated in relevant environment | IA, EIC-Transition |
| 7 | System prototype demonstration | IA, EIC-Accelerator |
| 8 | System complete and qualified | IA, EIC-Accelerator |
| 9 | Actual system proven | EIC-Accelerator |

### Consortium Requirements

| Action Type | Minimum Partners | Country Requirement | Notes |
|-------------|------------------|---------------------|-------|
| RIA | 3 | 3 different EU/Associated | Standard collaborative |
| IA | 3 | 3 different EU/Associated | Same as RIA |
| CSA | 1 | 1 EU/Associated | Single beneficiary allowed |
| ERC | 1 | Host in EU/Associated | Single PI, no consortium |
| MSCA-PF | 1 | Host in EU/Associated | Single researcher |
| MSCA-DN | 3 | 3 different countries | Doctoral training |
| EIC-Pathfinder | 3 | 3 different EU/Associated | For Open calls |
| EIC-Accelerator | 1 | EU/Associated | Single company |

### Budget Calculation Rules

```python
# Direct Costs
PERSONNEL_RATES = {
    'tier1': 8500,  # €/person-month (DE, FR, NL, BE, AT, FI, SE, DK, IE, LU)
    'tier2': 6500,  # €/person-month (ES, IT, PT, CY, MT, SI)
    'tier3': 4500,  # €/person-month (EE, LT, LV, PL, CZ, SK, HU, RO, BG, HR, EL)
}

# Cost Categories (typical ratios for RIA)
COST_RATIOS_RIA = {
    'personnel': 0.55-0.65,      # Largest component
    'subcontracting': 0.05-0.15,
    'equipment': 0.05-0.10,
    'travel': 0.03-0.08,
    'other_direct': 0.05-0.10,
}

# Indirect Costs (Overhead)
INDIRECT_COST_RATE = 0.25  # 25% flat rate on direct costs (excl. subcontracting)

# Total Cost Calculation
total_cost = direct_costs + (direct_costs - subcontracting) * 0.25
eu_contribution = total_cost * funding_rate
```

### Cluster Keywords Mapping

```python
CLUSTER_KEYWORDS = {
    'CLUSTER-1': ['health', 'medical', 'clinical', 'disease', 'pandemic',
                  'pharmaceutical', 'biomedical', 'cancer', 'vaccine', 'diagnostic'],

    'CLUSTER-2': ['culture', 'heritage', 'democracy', 'migration', 'social',
                  'inclusive', 'creative', 'governance', 'European identity'],

    'CLUSTER-3': ['security', 'cybersecurity', 'border', 'defense', 'resilience',
                  'critical infrastructure', 'terrorism', 'disaster', 'forensics'],

    'CLUSTER-4': ['digital', 'AI', 'artificial intelligence', 'data', 'cloud',
                  'robotics', 'HPC', 'quantum', 'semiconductor', 'IoT', '5G/6G'],

    'CLUSTER-5': ['climate', 'energy', 'hydrogen', 'solar', 'wind', 'transport',
                  'mobility', 'battery', 'grid', 'carbon neutral', 'green deal'],

    'CLUSTER-6': ['food', 'agriculture', 'biodiversity', 'ocean', 'water',
                  'bioeconomy', 'circular', 'forestry', 'fisheries', 'soil'],
}
```

---

## Erasmus+ Programme Structure

### Key Actions

```
KA1 - Learning Mobility of Individuals
├── Higher Education (HED) - Student & staff mobility
├── VET - Vocational education mobility
├── School Education (SCH) - Pupil & teacher exchanges
├── Adult Education (ADU) - Staff mobility
└── Youth (YOU) - Youth exchanges, volunteering

KA2 - Cooperation Partnerships
├── Cooperation Partnerships - Strategic projects (all sectors)
├── Small-Scale Partnerships - Smaller organizations
├── Capacity Building - With partner countries
├── Alliances for Innovation - University-business
└── Teacher Academies - Teacher training

KA3 - Policy Support
├── European Youth Together
├── Civil Society Cooperation
└── Policy Experimentation

Jean Monnet Actions
├── Modules - Teaching EU studies
├── Chairs - Research excellence
├── Centres of Excellence
└── Networks

Sport
├── Cooperation Partnerships
├── Small-Scale Partnerships
└── Not-for-Profit Events
```

### Sector Codes

| Code | Sector | Organization Types |
|------|--------|-------------------|
| HED | Higher Education | Universities, HEIs |
| VET | Vocational Education & Training | VET schools, training providers |
| SCH | School Education | Schools, education authorities |
| ADU | Adult Education | Adult learning centers |
| YOU | Youth | Youth organizations, NGOs |
| SPORT | Sport | Sports clubs, federations |

### Erasmus+ Funding Model (Lump Sum)

```python
# Unit Costs - NOT actual cost reimbursement!
ERASMUS_UNIT_COSTS = {
    'individual_support': {
        # Per participant per day (varies by destination)
        'group1': 120,  # DK, FI, IE, IS, LI, LU, NO, SE
        'group2': 105,  # AT, BE, DE, FR, IT, EL, ES, CY, MT, NL, PT
        'group3': 90,   # BG, CZ, EE, HR, HU, LT, LV, PL, RO, RS, SI, SK
    },

    'travel': {
        # By distance band (one-way)
        '10-99km': 23,
        '100-499km': 180,
        '500-1999km': 275,
        '2000-2999km': 360,
        '3000-3999km': 530,
        '4000-7999km': 820,
        '8000+km': 1500,
    },

    'organizational_support': {
        # Per participant
        'mobility': 350-500,  # Depends on activity
    },

    'special_needs': 'Actual costs',  # Exception to lump sum
}
```

### Erasmus+ Consortium Requirements

| Action | Min Partners | Min Countries | Coordinator |
|--------|--------------|---------------|-------------|
| KA2 Cooperation Partnership | 3 | 3 EU/Programme | Programme country |
| KA2 Small-Scale | 2 | 2 EU/Programme | Programme country |
| Capacity Building HED | 2 EU + 2 Partner | 4 total | Programme country |
| Alliances for Innovation | 4 | 4 EU/Programme | Programme country |
| Jean Monnet Module | 1 | 1 | Programme country |

### Programme vs Partner Countries

**Programme Countries** (full participation):
- All 27 EU Member States
- Iceland, Liechtenstein, Norway (EEA)
- North Macedonia, Serbia, Turkey (candidate)

**Partner Countries** (limited participation):
- Western Balkans (Albania, Bosnia, Kosovo, Montenegro)
- Eastern Partnership (Armenia, Azerbaijan, Georgia, Moldova, Ukraine)
- Southern Mediterranean
- Rest of world (for specific actions)

---

## Creative Europe Programme Structure

### Strands

```
CULTURE Strand (33% of budget)
├── European Cooperation Projects
│   ├── Small-scale (€200K, 3 partners)
│   ├── Medium-scale (€1M, 5 partners)
│   └── Large-scale (€2M, 10 partners)
├── European Networks
├── European Platforms
└── Literary Translation

MEDIA Strand (58% of budget)
├── Development
│   ├── Single Project
│   ├── Slate Funding
│   └── Co-development
├── Distribution & Sales
├── Training Programs
├── Film Festivals
├── Cinema Networks
├── European Film Sales
└── Audience Development

CROSS-SECTORAL Strand (9% of budget)
├── Creative Innovation Lab
├── News Media Partnerships
├── Media Literacy
└── Music Moves Europe
```

### Creative Europe Funding Rates

| Action | Funding Rate | Grant Range | Duration |
|--------|-------------|-------------|----------|
| Small-scale Cooperation | 80% | €200K max | 24 months |
| Medium-scale Cooperation | 70% | €1M max | 48 months |
| Large-scale Cooperation | 60% | €2M max | 48 months |
| Networks | 80% | €1.5M/year | 4 years |
| Platforms | 80% | €1.5M/year | 4 years |
| MEDIA Development | 50-70% | Varies | Varies |
| MEDIA Distribution | 50-60% | Varies | Varies |

### Creative Europe Eligibility

**CULTURE Strand:**
- Open to all Creative Europe countries
- Legal entities in cultural/creative sectors
- Min 3 countries (small), 5 (medium), 10 (large)

**MEDIA Strand:**
- Restricted to MEDIA countries (smaller list)
- Audiovisual sector only
- Must be established 12+ months

---

## Country Eligibility Quick Reference

### EU Member States (27)
AT, BE, BG, CY, CZ, DE, DK, EE, EL, ES, FI, FR, HR, HU, IE, IT, LT, LU, LV, MT, NL, PL, PT, RO, SE, SI, SK

### Associated Countries (Horizon Europe)
- **Fully Associated**: CH*, IL*, IS, NO, UK*, AL, BA, XK, ME, MK, RS, TR, GE, MD, UA
- **Partial**: Some restrictions apply

*Note: Check current status - associations may be pending/suspended*

### Third Country Participation

| Programme | Third Country Rules |
|-----------|-------------------|
| Horizon Europe | Automatic eligibility for some; others need bilateral agreement |
| Erasmus+ | Partner country rules; limited actions available |
| Creative Europe | MEDIA strand restricted; CULTURE more open |

---

## Common Terminology

### Funding Terms

| Term | Definition |
|------|------------|
| **Grant Agreement** | Legal contract between EC and beneficiaries |
| **Consortium Agreement** | Internal agreement between partners |
| **Work Programme** | Annual document specifying calls and topics |
| **Call** | Specific funding opportunity under a topic |
| **Topic** | Thematic area within a Work Programme |
| **Lump Sum** | Fixed amount based on activities, not actual costs |
| **Unit Cost** | Predefined cost per unit (person-day, km, etc.) |
| **Actual Cost** | Reimbursement of real incurred costs |
| **Co-financing** | Applicant must cover part of costs |
| **Pre-financing** | Upfront payment from EC |

### Evaluation Criteria

**Horizon Europe (100 points):**
- Excellence: ~50% (scientific quality, methodology)
- Impact: ~30% (societal, economic, policy)
- Implementation: ~20% (work plan, resources, risk)

**Erasmus+ (100 points):**
- Relevance: 25%
- Quality of design: 30%
- Quality of partnership: 20%
- Impact: 25%

### Organization Types

| Code | Type | Description |
|------|------|-------------|
| HES | Higher Education | Universities, polytechnics |
| REC | Research Organization | Research institutes, labs |
| PRC | Private Company | Large enterprises (250+ employees) |
| SME | SME | Small/medium enterprise (<250 employees) |
| PUB | Public Body | Government, agencies |
| OTH | Other | NGOs, associations, foundations |

---

## Common Pitfalls to Avoid

### Eligibility Errors
- Using Swiss organizations in Horizon Europe (check current association status)
- Mixing up Programme/Partner countries in Erasmus+
- Counting consortium members wrong (legal entities, not departments)
- Including third countries without checking eligibility

### Budget Errors
- Applying wrong funding rate (70% vs 100%)
- Forgetting indirect costs (25% flat rate)
- Not adjusting personnel costs by country tier
- Confusing lump sum vs actual costs

### Terminology Confusion
- RIA vs IA: RIA = 100% funding, closer to research; IA = 70%, closer to market
- Call vs Topic: Topic is broader theme; Call is specific deadline
- Grant vs Contract: Grant = cost-sharing; Contract = 100% service fee
- Coordinator vs Lead beneficiary: Same role, different programmes' terms

### Timeline Errors
- Missing that some calls have two-stage submission
- Not accounting for evaluation time (3-5 months)
- Starting activities before grant agreement signature
- Project end date vs reporting deadline confusion

---

## Quick Reference Queries

### "Is [country] eligible for [programme]?"
1. Check if EU Member State → Yes for all
2. Check Associated Country list for programme
3. Check specific action restrictions
4. Verify current association status (can change)

### "What's the funding rate for [action type]?"
1. Identify action type (RIA, IA, CSA, etc.)
2. Check if non-profit exception applies (IA: 100% for non-profit)
3. Consider lump sum vs actual cost model
4. Account for indirect costs (25%)

### "How many partners needed for [call]?"
1. Check action type default requirements
2. Look for call-specific requirements in Work Programme
3. Verify country distribution requirement
4. Check if single-beneficiary allowed

### "What budget should I request?"
1. Check typical range for action type
2. Look at funded projects in same cluster/topic
3. Calculate based on consortium size and effort
4. Ensure within topic budget envelope
