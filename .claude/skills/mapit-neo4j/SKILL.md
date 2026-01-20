# MAPIT Neo4j Graph Database Skill

This skill documents the Neo4j graph schema, Cypher query patterns, and best practices for the MAPIT AI project.

## Connection Configuration

```python
# Environment Variables
NEO4J_URI=bolt://neo4j:7687  # or bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Access in code
from app.core.neo4j_config import neo4j_db
results = neo4j_db.execute_query(query, parameters)
```

---

## Node Types

### Core CORDIS/Horizon Europe Nodes

#### Project
```cypher
(:Project {
    id: "101000001",           // UNIQUE - Project identifier
    acronym: "ACRONYM",
    title: "Project Title",
    objective: "Project objective text...",  // Up to 5000 chars
    startDate: "2024-01-01",
    endDate: "2027-12-31",
    totalCost: 5000000.0,
    ecMaxContribution: 5000000.0,
    status: "Active",          // Active, Completed, Terminated
    legalBasis: "HORIZON-RIA",
    fundingScheme: "RIA"       // RIA, IA, CSA, ERC, MSCA
})
```

#### Organization
```cypher
(:Organization {
    id: "999999999",           // UNIQUE - PIC number
    name: "Organization Name",
    shortName: "SHORT",
    country: "DE",             // ISO code
    city: "Berlin",
    activityType: "HES",       // HES, REC, PRC, PUB, OTH
    sme: false
})
```

#### Topic
```cypher
(:Topic {
    code: "HORIZON-CL5-2025-D3-01",  // UNIQUE
    title: "Topic Title"
})
```

#### Cluster
```cypher
(:Cluster {
    code: "CLUSTER-5",         // UNIQUE (CLUSTER-1 through CLUSTER-6)
    name: "Climate, Energy and Mobility",
    pillar: "Pillar II",
    shortCode: "CL5"
})
```

#### Programme
```cypher
(:Programme {
    code: "ERC",               // UNIQUE
    name: "European Research Council",
    pillar: "Pillar I",
    budget: 16000000000.0,
    budget_formatted: "€16 billion",
    start_year: 2021,
    end_year: 2027
})
```

#### Country
```cypher
(:Country {
    isoCode: "DE",             // UNIQUE
    name: "Germany",
    isEU: true,
    isAssociated: false,
    // Programme-specific flags
    erasmus_programme_country: true,
    creative_europe_eligible: true,
    eu4health_eligible: true,
    digital_europe_eligible: true,
    life_eligible: true
})
```

#### EntityType
```cypher
(:EntityType {
    code: "HES",               // UNIQUE
    name: "Higher Education Institution"
})
// Codes: HES, REC, PRC, PUB, OTH, SME
```

### Erasmus+ Nodes

#### ErasmusAction
```cypher
(:ErasmusAction {
    code: "KA2-COOP-HED",      // UNIQUE
    name: "Cooperation Partnerships - Higher Education",
    key_action: "KA2",
    sector: "HED",
    min_partners: 3,
    min_countries: 3,
    requires_eche: true,
    coordinator_countries: "programme",    // "programme", "worldwide"
    partner_countries: "programme",
    duration_months_min: 12,
    duration_months_max: 36,
    typical_budget_min: 100000,
    typical_budget_max: 400000,
    funding_model: "lump_sum"
})
```

#### ErasmusSector
```cypher
(:ErasmusSector {
    code: "HED",               // UNIQUE
    name: "Higher Education",
    org_types: ["university", "polytechnic", "college"]
})
// Codes: HED, VET, SCH, ADU, YOU, SPORT
```

#### PartnerRegion
```cypher
(:PartnerRegion {
    code: "PROGRAMME",         // UNIQUE
    name: "Programme Countries",
    countries: ["AT", "BE", "BG", "CY", "CZ", ...]  // ISO codes
})
// Codes: PROGRAMME, WORLDWIDE, WESTERN_BALKANS, EASTERN_PARTNERSHIP, etc.
```

### Creative Europe Nodes

#### CreativeEuropeStrand
```cypher
(:CreativeEuropeStrand {
    code: "CULTURE",           // UNIQUE
    name: "Culture Strand",
    budget_share: 0.33,
    org_types: ["cultural organization", "NGO", "public body"]
})
// Codes: CULTURE, MEDIA, CROSS-SECTORAL
```

#### CreativeEuropeAction
```cypher
(:CreativeEuropeAction {
    code: "COOP-SMALL",        // UNIQUE
    name: "Small-Scale Cooperation Projects",
    strand: "CULTURE",
    min_partners: 3,
    min_countries: 3,
    grant_min: 0,
    grant_max: 200000,
    funding_rate: 0.80,        // 80%
    duration_months_max: 48,
    funding_model: "lump_sum"
})
```

### EU4Health Nodes

#### EU4HealthAction
```cypher
(:EU4HealthAction {
    code: "JA",                // UNIQUE - Joint Action
    name: "Joint Actions",
    funding_rate_min: 0.60,
    funding_rate_max: 0.80,
    country_rule: "member_states_only",  // or "participating"
    org_types: ["public health authority", "research institute"]
})
// Codes: AG (Action Grant), PJ (Project), JA (Joint Action), DG (Direct Grant), OG (Operating Grant)
```

### Digital Europe Nodes

#### DigitalEuropeObjective
```cypher
(:DigitalEuropeObjective {
    code: "AI",                // UNIQUE
    name: "Artificial Intelligence",
    budget: 2100000000.0,
    funding_rate: 0.50,
    priority_areas: ["trustworthy AI", "AI testing facilities", "AI skills"]
})
// Codes: HPC, AI, CYBERSECURITY, SKILLS, DEPLOYMENT, SEMICONDUCTORS
```

### LIFE Programme Nodes

#### LIFESubprogramme
```cypher
(:LIFESubprogramme {
    code: "CET",               // UNIQUE
    name: "Clean Energy Transition",
    funding_rate: 0.95,
    objectives: ["decarbonization", "energy efficiency"]
})
// Codes: NAT (Nature), ENV (Environment), CCA (Climate Adaptation), CET (Clean Energy)
```

---

## Relationships

### Project Relationships

```cypher
// Project funded under a topic
(p:Project)-[:FUNDED_UNDER]->(t:Topic)

// Project targets a cluster or programme
(p:Project)-[:TARGETS]->(c:Cluster)
(p:Project)-[:TARGETS]->(pr:Programme)

// Organization participates in project
(o:Organization)-[:PARTICIPATES_IN {
    role: "coordinator",       // or "participant"
    ecContribution: 500000.0
}]->(p:Project)

// Organizations that partner together
(o1:Organization)-[:PARTNERS_WITH {
    projectCount: 5,
    totalValue: 25000000.0,
    updatedAt: datetime()
}]-(o2:Organization)
```

### Classification Relationships

```cypher
// Organization location
(o:Organization)-[:LOCATED_IN]->(co:Country)

// Organization type
(o:Organization)-[:IS_TYPE]->(et:EntityType)

// Topic belongs to cluster
(t:Topic)-[:BELONGS_TO {project_count: 50}]->(c:Cluster)

// Country membership
(co:Country)-[:MEMBER_OF]->(r:PartnerRegion)
```

### Programme Structure Relationships

```cypher
// Erasmus+
(a:ErasmusAction)-[:AVAILABLE_IN]->(s:ErasmusSector)
(a:ErasmusAction)-[:REQUIRES_COORDINATOR_FROM]->(r:PartnerRegion)
(a:ErasmusAction)-[:ALLOWS_PARTNERS_FROM]->(r:PartnerRegion)

// Creative Europe
(a:CreativeEuropeAction)-[:BELONGS_TO_STRAND]->(s:CreativeEuropeStrand)
(a:CreativeEuropeAction)-[:ALLOWS_COORDINATOR_FROM]->(r:CreativeEuropeRegion)
(a:CreativeEuropeAction)-[:ALLOWS_PARTNER_FROM]->(r:CreativeEuropeRegion)

// Digital Europe
(a:DigitalEuropeAction)-[:BELONGS_TO_OBJECTIVE]->(o:DigitalEuropeObjective)

// LIFE
(pt:LIFEProjectType)-[:AVAILABLE_IN]->(s:LIFESubprogramme)

// All programmes
(s:*Strand|*Subprogramme|*Objective)-[:PART_OF]->(p:Programme)
```

---

## Common Cypher Patterns

### Pattern 1: Budget Statistics by Cluster

```cypher
MATCH (p:Project)-[:TARGETS]->(c:Cluster {code: $cluster_code})
WHERE p.fundingScheme CONTAINS $action_type

WITH c,
     COUNT(p) as projectCount,
     SUM(p.ecMaxContribution) as totalFunding,
     AVG(p.ecMaxContribution) as avgBudget,
     MIN(p.ecMaxContribution) as minBudget,
     MAX(p.ecMaxContribution) as maxBudget,
     percentileCont(p.ecMaxContribution, 0.5) as medianBudget

RETURN c.code as clusterCode,
       c.name as clusterName,
       projectCount,
       totalFunding,
       avgBudget,
       minBudget,
       maxBudget,
       medianBudget
```

### Pattern 2: Consortium Patterns

```cypher
MATCH (p:Project)-[:TARGETS]->(c:Cluster {code: $cluster_code})
MATCH (o:Organization)-[r:PARTICIPATES_IN]->(p)
OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)
OPTIONAL MATCH (o)-[:IS_TYPE]->(et:EntityType)

WITH p, c,
     COUNT(DISTINCT o) as partnerCount,
     COUNT(DISTINCT co.isoCode) as countryCount,
     COLLECT(DISTINCT et.code) as entityTypes,
     COLLECT(DISTINCT CASE WHEN r.role = 'coordinator' THEN co.isoCode END) as coordCountries

WHERE partnerCount >= $min_partners

WITH c,
     AVG(partnerCount) as avgPartners,
     AVG(countryCount) as avgCountries,
     COLLECT(coordCountries[0]) as allCoordCountries,
     COUNT(p) as sampleSize

RETURN c.code, avgPartners, avgCountries, sampleSize, allCoordCountries
```

### Pattern 3: Partner Discovery (2-hop)

```cypher
// Find organizations in a cluster
MATCH (o1:Organization)-[:PARTICIPATES_IN]->(p:Project)-[:TARGETS]->(c:Cluster {code: $cluster_code})
WHERE toLower(o1.country) = toLower($country_code) OR $country_code IS NULL

// Find their partners (1-hop)
MATCH (o1)-[:PARTICIPATES_IN]->(p2:Project)<-[:PARTICIPATES_IN]-(o2:Organization)
WHERE o1 <> o2

// Find partners of partners (2-hop)
OPTIONAL MATCH (o2)-[:PARTICIPATES_IN]->(p3:Project)<-[:PARTICIPATES_IN]-(o3:Organization)
WHERE o3 <> o1 AND o3 <> o2

WITH o2, o3,
     COUNT(DISTINCT p2) as directProjects,
     COUNT(DISTINCT p3) as extendedProjects

RETURN o2.name as partner,
       o2.country as country,
       directProjects,
       COLLECT(DISTINCT o3.name)[0..5] as extendedNetwork
ORDER BY directProjects DESC
LIMIT $limit
```

### Pattern 4: Organization Profile

```cypher
MATCH (o:Organization)
WHERE toLower(o.name) CONTAINS toLower($org_name)
   OR toLower(o.shortName) CONTAINS toLower($org_name)

OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)
OPTIONAL MATCH (o)-[:IS_TYPE]->(et:EntityType)
OPTIONAL MATCH (o)-[r:PARTICIPATES_IN]->(p:Project)
OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)

WITH o, co, et,
     COUNT(DISTINCT p) as projectCount,
     SUM(r.ecContribution) as totalFunding,
     COUNT(CASE WHEN r.role = 'coordinator' THEN 1 END) as coordinations,
     COLLECT(DISTINCT c.code) as clusters,
     COLLECT(DISTINCT p.acronym)[0..5] as recentProjects

RETURN o.id, o.name, o.shortName,
       co.isoCode as country,
       et.code as entityType,
       projectCount, totalFunding, coordinations,
       clusters, recentProjects
ORDER BY projectCount DESC
LIMIT 1
```

### Pattern 5: Collaboration Network

```cypher
MATCH (o1:Organization)
WHERE toLower(o1.name) CONTAINS toLower($org_name)

MATCH (o1)-[:PARTICIPATES_IN]->(p:Project)<-[:PARTICIPATES_IN]-(o2:Organization)
WHERE o1 <> o2

WITH o1, o2,
     COUNT(DISTINCT p) as sharedProjects,
     SUM(p.ecMaxContribution) as totalValue,
     COLLECT(DISTINCT p.acronym)[0..3] as sampleProjects

OPTIONAL MATCH (o2)-[:LOCATED_IN]->(co:Country)

RETURN o2.name as partnerName,
       co.isoCode as partnerCountry,
       sharedProjects,
       totalValue,
       sampleProjects
ORDER BY sharedProjects DESC
LIMIT $limit
```

### Pattern 6: Topic Analysis

```cypher
MATCH (t:Topic {code: $topic_code})
OPTIONAL MATCH (p:Project)-[:FUNDED_UNDER]->(t)
OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)

WITH t,
     COLLECT(DISTINCT p) as projects,
     COLLECT(DISTINCT c)[0] as cluster

RETURN t.code as topicCode,
       t.title as topicTitle,
       cluster.code as clusterCode,
       SIZE(projects) as projectCount,
       REDUCE(s = 0.0, p IN projects | s + COALESCE(p.ecMaxContribution, 0)) as totalFunding,
       [p IN projects[0..5] | {
           acronym: p.acronym,
           title: p.title,
           budget: p.ecMaxContribution
       }] as sampleProjects
```

### Pattern 7: Eligibility Check (Erasmus+)

```cypher
MATCH (a:ErasmusAction {code: $action_code})
OPTIONAL MATCH (a)-[:REQUIRES_COORDINATOR_FROM]->(r:PartnerRegion)
OPTIONAL MATCH (c:Country {isoCode: $country_code})-[:MEMBER_OF]->(r)

RETURN a.code as actionCode,
       a.name as actionName,
       a.key_action as keyAction,
       a.min_partners as minPartners,
       a.min_countries as minCountries,
       a.requires_eche as requiresECHE,
       CASE WHEN c IS NOT NULL THEN true ELSE false END as isEligible
```

### Pattern 8: Programme Synergies

```cypher
MATCH (p1:Programme {code: $programme_code})
OPTIONAL MATCH (p1)-[s:HAS_SYNERGY_WITH]->(p2:Programme)

RETURN p1.code as programme,
       p1.name as name,
       COLLECT({
           related: p2.code,
           description: s.description
       }) as synergies
```

---

## Constraints and Indexes

### Create Constraints (Run Once)

```cypher
// Uniqueness constraints
CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT org_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE;
CREATE CONSTRAINT topic_code IF NOT EXISTS FOR (t:Topic) REQUIRE t.code IS UNIQUE;
CREATE CONSTRAINT cluster_code IF NOT EXISTS FOR (c:Cluster) REQUIRE c.code IS UNIQUE;
CREATE CONSTRAINT programme_code IF NOT EXISTS FOR (pr:Programme) REQUIRE pr.code IS UNIQUE;
CREATE CONSTRAINT country_iso IF NOT EXISTS FOR (co:Country) REQUIRE co.isoCode IS UNIQUE;
CREATE CONSTRAINT entity_type_code IF NOT EXISTS FOR (et:EntityType) REQUIRE et.code IS UNIQUE;
CREATE CONSTRAINT erasmus_action_code IF NOT EXISTS FOR (a:ErasmusAction) REQUIRE a.code IS UNIQUE;
CREATE CONSTRAINT erasmus_sector_code IF NOT EXISTS FOR (s:ErasmusSector) REQUIRE s.code IS UNIQUE;
CREATE CONSTRAINT ce_strand_code IF NOT EXISTS FOR (s:CreativeEuropeStrand) REQUIRE s.code IS UNIQUE;
CREATE CONSTRAINT ce_action_code IF NOT EXISTS FOR (a:CreativeEuropeAction) REQUIRE a.code IS UNIQUE;
```

### Create Indexes (Performance)

```cypher
CREATE INDEX project_acronym IF NOT EXISTS FOR (p:Project) ON (p.acronym);
CREATE INDEX project_status IF NOT EXISTS FOR (p:Project) ON (p.status);
CREATE INDEX org_name IF NOT EXISTS FOR (o:Organization) ON (o.name);
CREATE INDEX org_country IF NOT EXISTS FOR (o:Organization) ON (o.country);
CREATE INDEX erasmus_action_key_action IF NOT EXISTS FOR (a:ErasmusAction) ON (a.key_action);
CREATE INDEX erasmus_action_sector IF NOT EXISTS FOR (a:ErasmusAction) ON (a.sector);
```

---

## Best Practices

### Query Optimization

1. **MATCH first, then OPTIONAL MATCH**
   ```cypher
   // Good
   MATCH (p:Project) WHERE p.id = $id
   OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)

   // Bad
   OPTIONAL MATCH (p:Project)-[:TARGETS]->(c:Cluster)
   WHERE p.id = $id
   ```

2. **Limit collections early**
   ```cypher
   COLLECT(DISTINCT p.acronym)[0..5]  // Only keep first 5
   ```

3. **Use parameters, not string concatenation**
   ```cypher
   // Good
   WHERE p.id = $project_id

   // Bad
   WHERE p.id = '101000001'
   ```

4. **Bidirectional relationships don't need direction**
   ```cypher
   (o1)-[:PARTNERS_WITH]-(o2)  // Not -[:PARTNERS_WITH]->
   ```

### Error Handling

```python
try:
    results = neo4j_db.execute_query(query, parameters)
    if not results:
        return []
    return [dict(record) for record in results]
except Exception as e:
    logger.error(f"Neo4j query failed: {e}")
    return []  # Graceful fallback
```

### Aggregation Functions

| Function | Usage |
|----------|-------|
| `COUNT(DISTINCT x)` | Unique count |
| `SUM(x)` | Total |
| `AVG(x)` | Average |
| `MIN(x)`, `MAX(x)` | Range |
| `percentileCont(x, 0.5)` | Median |
| `COLLECT(x)` | Gather into list |
| `REDUCE(s=0, x IN list \| s + x)` | Accumulate |

---

## Data Ingestion Scripts

| Script | Purpose |
|--------|---------|
| `scripts/ingest_cordis_to_neo4j.py` | CORDIS projects, organizations, topics |
| `scripts/ingest_erasmus_to_neo4j.py` | Erasmus+ actions, sectors, regions |
| `scripts/ingest_creative_europe_to_neo4j.py` | Creative Europe strands, actions |
| `scripts/ingest_eu4health_to_neo4j.py` | EU4Health strands, actions |
| `scripts/ingest_digital_europe_to_neo4j.py` | Digital Europe objectives |
| `scripts/ingest_life_to_neo4j.py` | LIFE subprogrammes |

Each script follows the pattern:
1. Create constraints and indexes
2. Load reference data (countries, regions)
3. Load main entities (actions, projects)
4. Create relationships
5. Link to existing entities
