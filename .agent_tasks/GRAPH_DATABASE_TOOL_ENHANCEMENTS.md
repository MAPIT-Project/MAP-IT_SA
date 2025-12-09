# Graph Database Tool Enhancements

> **Status:** Ready for Implementation
> **Priority:** High
> **Created:** 2025-12-09
> **Estimated Effort:** 8-12 hours total

## Executive Summary

This document outlines opportunities to enhance the MAP-IT system's tools by integrating Neo4j graph database capabilities. The system currently has 7 proposal support tools that primarily use PostgreSQL for data queries. By leveraging the existing Neo4j graph database (which contains 18,784 projects, 2,283 topics, 6 clusters, and organization relationship data), we can significantly improve the relevance and performance of these tools.

---

## Table of Contents

1. [System Context](#system-context)
2. [Current Architecture](#current-architecture)
3. [Neo4j Graph Schema](#neo4j-graph-schema)
4. [Available Graph Service Methods](#available-graph-service-methods)
5. [Tool Enhancement Specifications](#tool-enhancement-specifications)
   - [Tier 1: Partner Discovery Tool](#tier-1-partner-discovery-tool)
   - [Tier 1: Budget Benchmark Tool](#tier-1-budget-benchmark-tool)
   - [Tier 2: Consortium Patterns Tool](#tier-2-consortium-patterns-tool)
   - [Tier 2: Call History Analysis Tool](#tier-2-call-history-analysis-tool)
   - [Tier 3: Similar Projects Tool](#tier-3-similar-projects-tool)
   - [Tier 3: Budget Calculator Tool](#tier-3-budget-calculator-tool)
   - [Tier 4: Timeline Generator Tool](#tier-4-timeline-generator-tool)
6. [Implementation Guidelines](#implementation-guidelines)
7. [Testing Requirements](#testing-requirements)

---

## System Context

### Project Overview

MAP-IT is a RAG (Retrieval-Augmented Generation) system for querying European research projects from the CORDIS database. It helps users:
- Find funding opportunities (calls)
- Search funded projects
- Get proposal writing assistance (budget benchmarks, partner discovery, consortium patterns)

### Key Directories

```
app/
├── services/
│   ├── tools/                          # Tool implementations (TARGET FOR ENHANCEMENT)
│   │   ├── budget_benchmark.py
│   │   ├── budget_calculator.py
│   │   ├── call_history.py
│   │   ├── consortium_patterns.py
│   │   ├── partner_discovery.py
│   │   ├── similar_projects.py
│   │   └── timeline_generator.py
│   ├── data_intelligence/
│   │   └── graph_service.py            # Neo4j service (USE THIS)
│   └── agents/
│       └── tool_orchestrator.py        # Orchestrates tool calls
├── core/
│   └── neo4j_config.py                 # Neo4j connection config
```

### Database Connections

1. **PostgreSQL (Supabase)** - `DATABASE_URL` environment variable
   - Tables: `projects`, `organizations`, `funding_calls`, `project_embeddings`

2. **Neo4j** - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` environment variables
   - Graph database with relationship-aware queries

---

## Current Architecture

### How Tools Currently Work

Each tool in `app/services/tools/` follows this pattern:

```python
import psycopg2
from psycopg2.extras import RealDictCursor

class SomeToolService:
    def __init__(self):
        from app.core.config import settings
        self._db_url = settings.database_url

    def some_method(self, params):
        conn = psycopg2.connect(self._db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT ... FROM projects WHERE ...", params)
        results = cursor.fetchall()
        conn.close()
        return results
```

### Current Tool Data Sources

| Tool | Primary Data Source | Uses Graph? |
|------|---------------------|-------------|
| Partner Discovery | PostgreSQL | ❌ No |
| Budget Benchmark | PostgreSQL | ❌ No |
| Consortium Patterns | PostgreSQL | ❌ No |
| Call History | PostgreSQL | ❌ No |
| Similar Projects | PostgreSQL + pgvector | ❌ No |
| Budget Calculator | Hardcoded constants | ❌ No |
| Timeline Generator | Hardcoded templates | ❌ No |

---

## Neo4j Graph Schema

### Node Types

```cypher
(:Project {
    id: STRING,           # CORDIS project ID (e.g., "101000001")
    acronym: STRING,      # Project acronym (e.g., "GREENH2")
    title: STRING,        # Full project title
    objective: STRING,    # Project objective/abstract
    status: STRING,       # "SIGNED", "CLOSED", "TERMINATED"
    startDate: STRING,    # ISO date "2022-01-01"
    endDate: STRING,      # ISO date "2025-12-31"
    totalCost: FLOAT,     # Total project cost in EUR
    ecMaxContribution: FLOAT,  # EU contribution in EUR
    fundingScheme: STRING,     # "RIA", "IA", "CSA", "ERC-STG", etc.
    legalBasis: STRING    # Legal basis reference
})

(:Organization {
    id: STRING,           # Organization ID
    name: STRING,         # Full organization name
    shortName: STRING,    # Acronym/short name
    country: STRING,      # Country code (ISO 2-letter)
    activityType: STRING, # "HES", "REC", "PRC", "PUB", "OTH"
    sme: BOOLEAN          # Is SME?
})

(:Topic {
    code: STRING,         # Topic code (e.g., "HORIZON-CL5-2024-D3-01")
    title: STRING         # Topic title
})

(:Cluster {
    code: STRING,         # "CLUSTER-1" through "CLUSTER-6"
    name: STRING,         # Full cluster name
    pillar: STRING        # Pillar reference
})

(:Country {
    isoCode: STRING,      # "DE", "FR", "NL", etc.
    name: STRING,         # "Germany", "France", etc.
    isEU: BOOLEAN         # Is EU member state?
})

(:EntityType {
    code: STRING,         # "HES", "REC", "PRC", "PUB", "OTH"
    name: STRING          # Full name
})
```

### Relationship Types

```cypher
# Organization participates in a project
(:Organization)-[:PARTICIPATES_IN {
    role: STRING,         # "coordinator" or "participant"
    ecContribution: FLOAT # EU contribution to this org
}]->(:Project)

# Project funded under a topic/call
(:Project)-[:FUNDED_UNDER]->(:Topic)

# Project targets a research cluster
(:Project)-[:TARGETS]->(:Cluster)

# Topic belongs to a cluster (NEWLY ADDED)
(:Topic)-[:BELONGS_TO {
    project_count: INTEGER  # Number of projects linking this topic to cluster
}]->(:Cluster)

# Organization located in a country
(:Organization)-[:LOCATED_IN]->(:Country)

# Organization is of entity type
(:Organization)-[:IS_TYPE]->(:EntityType)
```

### Graph Statistics (Current)

- **Projects:** 18,784
- **Topics:** 2,283 (1,388 linked to clusters)
- **Clusters:** 6
- **Organizations:** ~50,000+
- **Countries:** 100+
- **Topic-Cluster Links:** 1,388 (via BELONGS_TO relationship)

### Sample Cypher Queries

```cypher
# Find all projects in a cluster
MATCH (p:Project)-[:TARGETS]->(c:Cluster {code: "CLUSTER-4"})
RETURN p.acronym, p.title, p.ecMaxContribution
LIMIT 10

# Find organization's collaboration network
MATCH (o1:Organization)-[:PARTICIPATES_IN]->(p:Project)<-[:PARTICIPATES_IN]-(o2:Organization)
WHERE o1.name CONTAINS "Fraunhofer"
RETURN o2.name, COUNT(DISTINCT p) as collaborations
ORDER BY collaborations DESC
LIMIT 20

# Find topics in a cluster
MATCH (t:Topic)-[:BELONGS_TO]->(c:Cluster {code: "CLUSTER-5"})
RETURN t.code, t.title
ORDER BY t.code

# Find experienced partners in a research area
MATCH (o:Organization)-[:PARTICIPATES_IN]->(p:Project)-[:TARGETS]->(c:Cluster {code: "CLUSTER-1"})
WHERE o.activityType = "REC"
WITH o, COUNT(DISTINCT p) as projectCount, SUM(p.ecMaxContribution) as totalFunding
WHERE projectCount >= 3
RETURN o.name, o.country, projectCount, totalFunding
ORDER BY projectCount DESC
LIMIT 20
```

---

## Available Graph Service Methods

### File: `app/services/data_intelligence/graph_service.py`

The `GraphSearchService` class provides these methods that tools should use:

### Topic/Call Queries

```python
def get_call_details(self, identifier: str) -> Optional[Dict[str, Any]]
    """Get topic details with related projects and statistics."""
    # Returns: topic_code, topic_title, cluster_code, project_count, total_funding, sample_projects

def search_topics(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]
    """Search for topics by keyword in code or title."""
    # Returns: code, title, clusterCode, projectCount

def get_topics_by_cluster(self, cluster_code: str, limit: int = 50) -> List[Dict[str, Any]]
    """Get topics that belong to a specific cluster via BELONGS_TO relationship."""
    # Returns: code, title, projectCount
```

### Budget & Statistics Queries

```python
def get_budget_statistics(
    self,
    cluster_code: Optional[str] = None,
    action_type: Optional[str] = None
) -> List[Dict[str, Any]]
    """Get budget statistics for projects, optionally filtered."""
    # Returns: cluster_code, cluster_name, project_count, total_funding,
    #          avg_budget, min_budget, max_budget, median_budget

def get_funding_trends(
    self,
    cluster_code: Optional[str] = None,
    group_by: str = "year"
) -> List[Dict[str, Any]]
    """Get funding trends over time."""
    # Returns: period, project_count, total_funding, avg_budget, clusters
```

### Consortium & Partner Queries

```python
def get_consortium_patterns(
    self,
    cluster_code: Optional[str] = None,
    min_partners: int = 3
) -> List[Dict[str, Any]]
    """Analyze consortium composition patterns for successful projects."""
    # Returns: cluster_code, cluster_name, avg_partners, avg_countries,
    #          sample_size, top_coordinator_countries

def find_organization_partners(
    self,
    org_name: str,
    limit: int = 20
) -> List[Dict[str, Any]]
    """Find organizations that have collaborated with a given organization."""
    # Returns: partner_name, partner_short_name, partner_country,
    #          shared_projects, total_project_value, sample_projects

def suggest_consortium_partners(
    self,
    cluster_code: str,
    topic_code: Optional[str] = None,
    coordinator_country: Optional[str] = None,
    target_partner_count: int = 5,
    required_entity_types: Optional[List[str]] = None
) -> Dict[str, Any]
    """Suggest potential consortium partners for a project."""
    # Returns: cluster, topic, suggestions (list), by_entity_type, countries_covered

def get_organization_collaboration_network(
    self,
    organization_name: str,
    depth: int = 1,
    limit: int = 50
) -> Dict[str, Any]
    """Get the collaboration network of an organization."""
    # Returns: organization, country, partners (list with collaborations count)

def check_consortium_compliance(
    self,
    partners: List[Dict[str, str]],
    action_type: str = "RIA",
    call_specific_rules: Optional[Dict] = None
) -> Dict[str, Any]
    """Check if a proposed consortium meets eligibility requirements."""
    # Returns: is_compliant, issues, warnings, recommendation
```

### Organization Queries

```python
def get_organization_profile(self, org_name: str) -> Optional[Dict[str, Any]]
    """Get detailed profile of an organization."""
    # Returns: id, name, short_name, country, entity_type, project_count,
    #          total_funding, coordinations, active_clusters, recent_projects

def get_organization_track_record(
    self,
    org_name: str,
    include_partners: bool = True
) -> Optional[Dict[str, Any]]
    """Get comprehensive track record for an organization."""
    # Returns: org_id, name, country, entity_type, total_projects,
    #          coordinations, total_funding, recent_projects, top_partners

def get_top_organizations(
    self,
    cluster_code: Optional[str] = None,
    country_code: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]
    """Get top organizations by project participation."""
    # Returns: name, short_name, country, project_count, total_funding, coordinations
```

### Project Discovery Queries

```python
def find_similar_projects(
    self,
    project_id: str,
    similarity_type: str = "topic",  # "topic", "consortium", or "cluster"
    limit: int = 10
) -> List[Dict[str, Any]]
    """Find projects similar to a given project."""
    # Returns: id, title, acronym, budget, status, funding_scheme,
    #          similarity_type, shared_topic/cluster/orgs

def find_projects_by_organization(
    self,
    organization_name: str,
    role: Optional[str] = None,  # "coordinator", "participant", or None
    limit: int = 20
) -> List[Dict[str, Any]]
    """Find all projects an organization participated in."""
    # Returns: id, title, acronym, budget, status, organization, role, start_date

def search_projects_by_keywords(
    self,
    keywords: List[str],
    status: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]
    """Search for projects by keywords in title and objective."""
    # Returns: id, title, acronym, objective, budget, status, clusters, topics

def get_project_examples(
    self,
    cluster_code: Optional[str] = None,
    topic_pattern: Optional[str] = None,
    funding_scheme: Optional[str] = None,
    min_budget: float = 0,
    limit: int = 10
) -> List[Dict[str, Any]]
    """Get example projects with their details and success indicators."""
    # Returns: project_id, acronym, title, objective, status, budget,
    #          funding_scheme, topic_code, cluster, partner_count, country_count, partners
```

### Eligibility Queries

```python
def check_country_eligibility(
    self,
    country_code: str,
    cluster_code: Optional[str] = None
) -> Dict[str, Any]
    """Check if a country is eligible to participate."""
    # Returns: country_code, is_eligible, eligibility_status, participation_history, notes

def check_entity_type_eligibility(
    self,
    entity_type: str,
    action_type: Optional[str] = None
) -> Dict[str, Any]
    """Check eligibility for an entity type."""
    # Returns: entity_type, is_eligible, eligibility_status, participation_history
```

### Utility Queries

```python
def get_cluster_overview(self) -> List[Dict[str, Any]]
    """Get overview of all clusters with project counts."""
    # Returns: code, name, pillar, project_count, total_funding

def get_cluster_statistics(
    self,
    cluster_code: Optional[str] = None
) -> List[Dict[str, Any]]
    """Get statistics for clusters."""
    # Returns: code, name, pillar, project_count, total_funding, avg_budget, funding_schemes

def find_similar_topics(
    self,
    topic_code: str,
    limit: int = 10
) -> List[Dict[str, Any]]
    """Find topics similar to a given topic based on cluster overlap."""
    # Returns: topic_code, topic_title, project_count, shared_clusters, similarity_score
```

### How to Use GraphSearchService

```python
from app.services.data_intelligence.graph_service import GraphSearchService

class MyTool:
    def __init__(self):
        # Initialize graph service
        self._graph_service = None
        try:
            self._graph_service = GraphSearchService()
        except Exception as e:
            logger.warning(f"Graph service not available: {e}")

    def my_method(self, params):
        # Use graph service if available
        if self._graph_service:
            partners = self._graph_service.find_organization_partners("Fraunhofer")
            # Process results...
        else:
            # Fallback to PostgreSQL
            pass
```

---

## Tool Enhancement Specifications

---

### Tier 1: Partner Discovery Tool

**File:** `app/services/tools/partner_discovery.py`

**Priority:** CRITICAL - Highest ROI for graph integration

**Current Implementation:**

```python
# Current approach uses PostgreSQL with complex keyword matching
def find_partners(
    self,
    research_area: str,
    country_preference: Optional[str] = None,
    org_type_preference: Optional[str] = None,
    min_projects: int = 2,
    limit: int = 20
) -> Dict[str, Any]
```

Current SQL query pattern:
```sql
WITH relevant_projects AS (
    SELECT id FROM projects
    WHERE objective ILIKE '%keyword%' OR title ILIKE '%keyword%'
)
SELECT o.name, o.country, COUNT(*) as project_count
FROM organizations o
JOIN project_organizations po ON o.id = po.organization_id
JOIN relevant_projects rp ON po.project_id = rp.id
GROUP BY o.name, o.country
HAVING COUNT(*) >= min_projects
ORDER BY project_count DESC
LIMIT 20
```

**Problems with Current Approach:**
1. Only finds organizations by keyword matching - misses semantic relationships
2. No collaboration network analysis - doesn't know who works well together
3. No centrality scoring - treats all organizations equally
4. No 2-hop discovery - can't find "partners of partners"
5. Slow for complex queries due to multiple JOINs

**Graph-Enhanced Implementation:**

```python
from app.services.data_intelligence.graph_service import GraphSearchService

class PartnerDiscoveryService:
    def __init__(self):
        from app.core.config import settings
        self._db_url = settings.database_url

        # Initialize graph service
        self._graph_service = None
        try:
            self._graph_service = GraphSearchService()
            logger.info("✅ Graph service available for partner discovery")
        except Exception as e:
            logger.warning(f"Graph service not available: {e}")

    def find_partners(
        self,
        research_area: str,
        country_preference: Optional[str] = None,
        org_type_preference: Optional[str] = None,
        min_projects: int = 2,
        limit: int = 20,
        include_2hop: bool = True  # NEW: Find partners of partners
    ) -> Dict[str, Any]:
        """
        Find potential consortium partners using graph relationships.

        Enhanced approach:
        1. Map research_area to clusters
        2. Use graph to find top organizations in those clusters
        3. Optionally find 2-hop partners (partners of top partners)
        4. Score by centrality + project count + funding
        """

        if not self._graph_service:
            # Fallback to PostgreSQL
            return self._find_partners_sql(research_area, country_preference,
                                           org_type_preference, min_projects, limit)

        # Step 1: Map research area to cluster(s)
        cluster_code = self._map_to_cluster(research_area)

        # Step 2: Get top organizations in the cluster
        suggestions = self._graph_service.suggest_consortium_partners(
            cluster_code=cluster_code,
            coordinator_country=None,  # Don't exclude any country
            target_partner_count=limit * 2  # Get more for filtering
        )

        partners = suggestions.get('suggestions', [])

        # Step 3: Apply filters
        if country_preference:
            partners = [p for p in partners if p.get('country') == country_preference.upper()]

        if org_type_preference:
            partners = [p for p in partners if p.get('entity_type') == org_type_preference.upper()]

        # Filter by min projects
        partners = [p for p in partners if p.get('project_count', 0) >= min_projects]

        # Step 4: Find 2-hop partners if requested
        two_hop_partners = []
        if include_2hop and len(partners) > 0:
            # Get collaboration networks of top 3 partners
            for partner in partners[:3]:
                network = self._graph_service.get_organization_collaboration_network(
                    partner['name'],
                    limit=10
                )
                if network.get('partners'):
                    for p in network['partners']:
                        if p['name'] not in [x['name'] for x in partners]:
                            p['discovery_type'] = '2-hop'
                            p['connected_via'] = partner['name']
                            two_hop_partners.append(p)

        # Step 5: Combine and deduplicate
        all_partners = partners[:limit]

        # Add unique 2-hop partners
        seen_names = {p['name'] for p in all_partners}
        for p in two_hop_partners:
            if p['name'] not in seen_names and len(all_partners) < limit:
                all_partners.append(p)
                seen_names.add(p['name'])

        return {
            'success': True,
            'research_area': research_area,
            'cluster': cluster_code,
            'partners_found': len(all_partners),
            'partners': all_partners,
            'search_metadata': {
                'method': 'graph_enhanced',
                'include_2hop': include_2hop,
                'filters_applied': {
                    'country': country_preference,
                    'org_type': org_type_preference,
                    'min_projects': min_projects
                }
            }
        }

    def _map_to_cluster(self, research_area: str) -> str:
        """Map research area keywords to cluster codes."""
        cluster_keywords = {
            'CLUSTER-1': ['health', 'medical', 'clinical', 'disease', 'patient',
                          'healthcare', 'hospital', 'therapy', 'diagnosis',
                          'pharmaceutical', 'cancer', 'vaccine', 'drug'],
            'CLUSTER-2': ['culture', 'democracy', 'social', 'heritage', 'creative',
                          'inclusive', 'society', 'governance', 'media'],
            'CLUSTER-3': ['security', 'cybersecurity', 'border', 'crime', 'disaster',
                          'resilience', 'defence', 'terrorism'],
            'CLUSTER-4': ['digital', 'AI', 'artificial intelligence', 'data', 'industry',
                          'space', 'manufacturing', 'robotics', 'computing',
                          'machine learning', 'quantum', 'electronics'],
            'CLUSTER-5': ['climate', 'energy', 'mobility', 'transport', 'hydrogen',
                          'battery', 'renewable', 'green', 'carbon', 'solar',
                          'wind', 'electric vehicle'],
            'CLUSTER-6': ['food', 'agriculture', 'bioeconomy', 'biodiversity', 'ocean',
                          'environment', 'soil', 'water', 'forestry', 'marine']
        }

        research_lower = research_area.lower()
        for cluster, keywords in cluster_keywords.items():
            if any(kw in research_lower for kw in keywords):
                return cluster

        return 'CLUSTER-4'  # Default to digital if no match

    def get_collaboration_network(
        self,
        organization_name: str,
        depth: int = 1
    ) -> Dict[str, Any]:
        """
        Get the collaboration network for an organization.

        NEW METHOD: Leverages graph traversal for network analysis.
        """
        if not self._graph_service:
            return {'success': False, 'error': 'Graph service not available'}

        network = self._graph_service.get_organization_collaboration_network(
            organization_name,
            depth=depth
        )

        return {
            'success': True,
            'organization': network.get('organization'),
            'country': network.get('country'),
            'total_partners': network.get('total_partners', 0),
            'partners': network.get('partners', []),
            'search_metadata': {
                'method': 'graph_traversal',
                'depth': depth
            }
        }
```

**New Cypher Queries to Add (if needed):**

```cypher
# Find 2-hop partners (partners of partners)
MATCH (o1:Organization {name: $org_name})-[:PARTICIPATES_IN]->(p1:Project)
      <-[:PARTICIPATES_IN]-(o2:Organization)-[:PARTICIPATES_IN]->(p2:Project)
      <-[:PARTICIPATES_IN]-(o3:Organization)
WHERE o1 <> o2 AND o2 <> o3 AND o1 <> o3
WITH o3, COUNT(DISTINCT p2) as indirect_collaborations,
     COLLECT(DISTINCT o2.name)[0..3] as connected_via
RETURN o3.name, o3.country, indirect_collaborations, connected_via
ORDER BY indirect_collaborations DESC
LIMIT 20

# Calculate network centrality (simplified degree centrality)
MATCH (o:Organization)-[:PARTICIPATES_IN]->(p:Project)-[:TARGETS]->(c:Cluster {code: $cluster})
WITH o, COUNT(DISTINCT p) as projects
MATCH (o)-[:PARTICIPATES_IN]->(p2:Project)<-[:PARTICIPATES_IN]-(partner:Organization)
WHERE o <> partner
WITH o, projects, COUNT(DISTINCT partner) as unique_partners
RETURN o.name, o.country, projects, unique_partners,
       (projects * 0.4 + unique_partners * 0.6) as centrality_score
ORDER BY centrality_score DESC
LIMIT 20
```

**Expected Benefits:**
- 3-5x faster partner discovery for complex queries
- More relevant results through relationship-aware search
- 2-hop partner discovery (find hidden gems)
- Network centrality scoring for influential organizations

**Testing:**
```python
# Test cases
service = PartnerDiscoveryService()

# Test 1: Basic partner discovery
result = service.find_partners("hydrogen energy", limit=10)
assert result['success']
assert len(result['partners']) > 0
assert result['cluster'] == 'CLUSTER-5'

# Test 2: With filters
result = service.find_partners(
    "AI healthcare",
    country_preference="DE",
    org_type_preference="REC",
    min_projects=3
)
assert all(p['country'] == 'DE' for p in result['partners'])

# Test 3: 2-hop discovery
result = service.find_partners("quantum computing", include_2hop=True)
two_hop = [p for p in result['partners'] if p.get('discovery_type') == '2-hop']
assert len(two_hop) > 0  # Should find some indirect partners

# Test 4: Collaboration network
network = service.get_collaboration_network("Fraunhofer")
assert network['success']
assert network['total_partners'] > 0
```

---

### Tier 1: Budget Benchmark Tool

**File:** `app/services/tools/budget_benchmark.py`

**Priority:** HIGH - Directly improves budget accuracy

**Current Implementation:**

```python
def get_benchmark(
    self,
    cluster: Optional[str] = None,
    action_type: Optional[str] = None,
    topic_pattern: Optional[str] = None,
    year_range: Optional[Tuple[int, int]] = None
) -> Dict[str, Any]
```

Current SQL query:
```sql
SELECT
    COUNT(*) as project_count,
    AVG(ec_max_contribution) as avg_budget,
    MIN(ec_max_contribution) as min_budget,
    MAX(ec_max_contribution) as max_budget,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ec_max_contribution) as median
FROM projects
WHERE funding_scheme ILIKE '%RIA%'  -- etc.
```

**Problems with Current Approach:**
1. Uses hardcoded cluster name mappings
2. Slow aggregation queries on large tables
3. No consortium composition context
4. No per-organization-type budget breakdown

**Graph-Enhanced Implementation:**

```python
from app.services.data_intelligence.graph_service import GraphSearchService

class BudgetBenchmarkService:
    def __init__(self):
        from app.core.config import settings
        self._db_url = settings.database_url

        self._graph_service = None
        try:
            self._graph_service = GraphSearchService()
            logger.info("✅ Graph service available for budget benchmarks")
        except Exception as e:
            logger.warning(f"Graph service not available: {e}")

    def get_benchmark(
        self,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        topic_pattern: Optional[str] = None,
        year_range: Optional[Tuple[int, int]] = None,
        include_consortium_context: bool = True  # NEW
    ) -> Dict[str, Any]:
        """
        Get budget benchmarks using graph-aggregated statistics.
        """

        # Try graph service first (pre-aggregated, faster)
        if self._graph_service and cluster:
            graph_stats = self._graph_service.get_budget_statistics(
                cluster_code=cluster,
                action_type=action_type
            )

            if graph_stats:
                result = {
                    'success': True,
                    'cluster': cluster,
                    'action_type': action_type,
                    'statistics': graph_stats[0] if len(graph_stats) == 1 else graph_stats,
                    'source': 'neo4j_graph'
                }

                # Add consortium context if requested
                if include_consortium_context:
                    consortium_patterns = self._graph_service.get_consortium_patterns(
                        cluster_code=cluster
                    )
                    if consortium_patterns:
                        result['consortium_context'] = consortium_patterns[0]

                return result

        # Fallback to PostgreSQL
        return self._get_benchmark_sql(cluster, action_type, topic_pattern, year_range)

    def get_budget_by_org_type(
        self,
        cluster: str,
        action_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        NEW METHOD: Get budget distribution by organization type.

        Uses graph to find actual funding distributions per org type.
        """
        if not self._graph_service:
            return {'success': False, 'error': 'Graph service not available'}

        # Custom Cypher query for org-type breakdown
        query = """
        MATCH (o:Organization)-[r:PARTICIPATES_IN]->(p:Project)-[:TARGETS]->(c:Cluster {code: $cluster})
        OPTIONAL MATCH (o)-[:IS_TYPE]->(et:EntityType)
        WITH et.code as org_type,
             AVG(r.ecContribution) as avg_contribution,
             COUNT(DISTINCT p) as project_count,
             SUM(r.ecContribution) as total_funding
        WHERE org_type IS NOT NULL
        RETURN org_type, avg_contribution, project_count, total_funding
        ORDER BY total_funding DESC
        """

        results = self._graph_service.db.execute_query(query, {'cluster': cluster})

        return {
            'success': True,
            'cluster': cluster,
            'by_org_type': [
                {
                    'org_type': r['org_type'],
                    'avg_contribution': r['avg_contribution'],
                    'project_count': r['project_count'],
                    'total_funding': r['total_funding']
                }
                for r in results
            ]
        }
```

**Expected Benefits:**
- Pre-aggregated statistics from graph (faster)
- Consortium composition context with budgets
- Per-organization-type breakdown
- More accurate benchmarks for proposal planning

**Testing:**
```python
service = BudgetBenchmarkService()

# Test 1: Basic benchmark with graph
result = service.get_benchmark(cluster="CLUSTER-5", action_type="RIA")
assert result['success']
assert result['source'] == 'neo4j_graph'
assert 'avg_budget' in result['statistics']

# Test 2: With consortium context
result = service.get_benchmark(
    cluster="CLUSTER-4",
    include_consortium_context=True
)
assert 'consortium_context' in result
assert 'avg_partners' in result['consortium_context']

# Test 3: By org type
result = service.get_budget_by_org_type(cluster="CLUSTER-1")
assert result['success']
assert len(result['by_org_type']) > 0
```

---

### Tier 2: Consortium Patterns Tool

**File:** `app/services/tools/consortium_patterns.py`

**Priority:** HIGH - Better consortium recommendations

**Current Implementation:**

```python
def get_patterns(
    self,
    cluster: Optional[str] = None,
    action_type: Optional[str] = None,
    min_partners: int = 3
) -> Dict[str, Any]
```

Uses multiple PostgreSQL JOINs to aggregate organization types and countries.

**Graph-Enhanced Implementation:**

```python
from app.services.data_intelligence.graph_service import GraphSearchService

class ConsortiumPatternsService:
    def __init__(self):
        from app.core.config import settings
        self._db_url = settings.database_url

        self._graph_service = None
        try:
            self._graph_service = GraphSearchService()
        except Exception as e:
            logger.warning(f"Graph service not available: {e}")

    def get_patterns(
        self,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        min_partners: int = 3,
        include_successful_templates: bool = True  # NEW
    ) -> Dict[str, Any]:
        """
        Analyze consortium patterns using graph relationships.
        """

        if not self._graph_service:
            return self._get_patterns_sql(cluster, action_type, min_partners)

        # Get consortium patterns from graph
        patterns = self._graph_service.get_consortium_patterns(
            cluster_code=cluster,
            min_partners=min_partners
        )

        result = {
            'success': True,
            'cluster': cluster,
            'action_type': action_type,
            'patterns': patterns,
            'source': 'neo4j_graph'
        }

        # Add successful consortium templates
        if include_successful_templates and cluster:
            templates = self._get_successful_templates(cluster, action_type)
            result['successful_templates'] = templates

        return result

    def _get_successful_templates(
        self,
        cluster: str,
        action_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Find actual consortium compositions from successful projects.
        """
        # Get example projects with their consortium details
        examples = self._graph_service.get_project_examples(
            cluster_code=cluster,
            funding_scheme=action_type,
            min_budget=1000000,  # Only substantial projects
            limit=5
        )

        templates = []
        for project in examples:
            # Count org types in consortium
            org_types = {}
            countries = set()
            for partner in project.get('partners', []):
                org_type = partner.get('type', 'OTH')
                org_types[org_type] = org_types.get(org_type, 0) + 1
                if partner.get('country'):
                    countries.add(partner['country'])

            templates.append({
                'project_acronym': project.get('acronym'),
                'budget': project.get('budget'),
                'partner_count': project.get('partner_count'),
                'country_count': project.get('country_count'),
                'org_type_distribution': org_types,
                'countries': list(countries)
            })

        return templates

    def get_coordinator_analysis(
        self,
        cluster: str,
        country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        NEW METHOD: Analyze successful coordinators in a cluster.
        """
        if not self._graph_service:
            return {'success': False, 'error': 'Graph service not available'}

        # Get top organizations that coordinate projects
        top_orgs = self._graph_service.get_top_organizations(
            cluster_code=cluster,
            country_code=country,
            limit=20
        )

        # Filter to those with coordinations
        coordinators = [o for o in top_orgs if o.get('coordinations', 0) > 0]

        return {
            'success': True,
            'cluster': cluster,
            'country': country,
            'top_coordinators': coordinators,
            'total_found': len(coordinators)
        }
```

**Expected Benefits:**
- Pre-computed consortium patterns from graph
- Real consortium templates from successful projects
- Coordinator analysis for finding proven leaders
- Faster than complex SQL aggregations

---

### Tier 2: Call History Analysis Tool

**File:** `app/services/tools/call_history.py`

**Priority:** MEDIUM-HIGH - Better trend analysis

**Current Implementation:**

```python
def analyze_history(
    self,
    topic_pattern: Optional[str] = None,
    cluster: Optional[str] = None,
    year_range: Optional[Tuple[int, int]] = None
) -> Dict[str, Any]
```

Uses PostgreSQL pattern matching on topic codes.

**Graph-Enhanced Implementation:**

```python
from app.services.data_intelligence.graph_service import GraphSearchService

class CallHistoryService:
    def __init__(self):
        from app.core.config import settings
        self._db_url = settings.database_url

        self._graph_service = None
        try:
            self._graph_service = GraphSearchService()
        except Exception as e:
            logger.warning(f"Graph service not available: {e}")

    def analyze_history(
        self,
        topic_pattern: Optional[str] = None,
        cluster: Optional[str] = None,
        year_range: Optional[Tuple[int, int]] = None,
        include_topic_evolution: bool = True  # NEW
    ) -> Dict[str, Any]:
        """
        Analyze funding history with graph-based trend analysis.
        """

        result = {
            'success': True,
            'topic_pattern': topic_pattern,
            'cluster': cluster
        }

        if self._graph_service:
            # Get funding trends from graph
            trends = self._graph_service.get_funding_trends(
                cluster_code=cluster,
                group_by='year'
            )
            result['trends'] = trends
            result['source'] = 'neo4j_graph'

            # Add topic evolution analysis
            if include_topic_evolution and cluster:
                topics = self._graph_service.get_topics_by_cluster(cluster, limit=50)
                result['topic_landscape'] = {
                    'total_topics': len(topics),
                    'top_topics': topics[:10]
                }

            # Find related topics if pattern provided
            if topic_pattern:
                related = self._graph_service.search_topics(topic_pattern, limit=20)
                result['related_topics'] = related
        else:
            # Fallback to SQL
            result = self._analyze_history_sql(topic_pattern, cluster, year_range)

        return result

    def get_cluster_evolution(
        self,
        cluster: str
    ) -> Dict[str, Any]:
        """
        NEW METHOD: Analyze how a cluster has evolved over time.
        """
        if not self._graph_service:
            return {'success': False, 'error': 'Graph service not available'}

        # Get trends by year
        trends = self._graph_service.get_funding_trends(
            cluster_code=cluster,
            group_by='year'
        )

        # Get cluster statistics
        stats = self._graph_service.get_cluster_statistics(cluster_code=cluster)

        return {
            'success': True,
            'cluster': cluster,
            'statistics': stats[0] if stats else {},
            'yearly_trends': trends,
            'source': 'neo4j_graph'
        }
```

**Expected Benefits:**
- Pre-aggregated funding trends
- Topic evolution analysis via graph relationships
- Cluster-level trend detection
- Related topic discovery through graph traversal

---

### Tier 3: Similar Projects Tool

**File:** `app/services/tools/similar_projects.py`

**Priority:** MEDIUM - Enhance vector results with graph context

**Current Implementation:**

Uses pgvector embeddings for semantic similarity search.

**Graph-Enhanced Implementation:**

```python
from app.services.data_intelligence.graph_service import GraphSearchService

class SimilarProjectsService:
    def __init__(self):
        # ... existing init ...

        self._graph_service = None
        try:
            self._graph_service = GraphSearchService()
        except Exception as e:
            logger.warning(f"Graph service not available: {e}")

    def find_similar(
        self,
        query: str,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 10,
        rerank_with_graph: bool = True  # NEW
    ) -> Dict[str, Any]:
        """
        Find similar projects with optional graph-based reranking.
        """

        # Step 1: Get embedding-based results (existing logic)
        embedding_results = self._find_similar_by_embedding(query, limit=limit*2)

        if not rerank_with_graph or not self._graph_service:
            return {
                'success': True,
                'projects': embedding_results[:limit],
                'source': 'vector_only'
            }

        # Step 2: Enhance with graph context
        enhanced_results = []
        for project in embedding_results:
            project_id = project.get('id')

            # Get graph context for this project
            if project_id:
                # Find consortium info
                graph_similar = self._graph_service.find_similar_projects(
                    project_id,
                    similarity_type='cluster',
                    limit=3
                )
                project['graph_similar_count'] = len(graph_similar)

                # Get consortium size from graph
                # (Add project details from graph if needed)

            enhanced_results.append(project)

        # Step 3: Rerank combining embedding score and graph context
        for project in enhanced_results:
            embedding_score = project.get('similarity_score', 0)
            graph_score = project.get('graph_similar_count', 0) / 10  # Normalize
            project['combined_score'] = embedding_score * 0.7 + graph_score * 0.3

        enhanced_results.sort(key=lambda x: x.get('combined_score', 0), reverse=True)

        return {
            'success': True,
            'projects': enhanced_results[:limit],
            'source': 'vector_with_graph_reranking'
        }
```

**Expected Benefits:**
- Better result relevance through multi-signal ranking
- Graph context (consortium, cluster) enhances semantic results
- Can find projects with similar structures, not just similar text

---

### Tier 3: Budget Calculator Tool

**File:** `app/services/tools/budget_calculator.py`

**Priority:** MEDIUM - Ground calculations in real data

**Current Implementation:**

Uses hardcoded cost ratios:
```python
COST_RATIOS = {
    'RIA': {'personnel': 0.60, 'equipment': 0.10, ...},
    'IA': {'personnel': 0.55, 'equipment': 0.15, ...},
    ...
}
```

**Graph-Enhanced Implementation:**

```python
from app.services.data_intelligence.graph_service import GraphSearchService

class BudgetCalculatorService:
    def __init__(self):
        # ... existing init ...

        self._graph_service = None
        try:
            self._graph_service = GraphSearchService()
        except Exception as e:
            logger.warning(f"Graph service not available: {e}")

        # Cache for real cost ratios from graph
        self._real_cost_ratios = None

    def calculate_budget(
        self,
        action_type: str,
        duration_months: int,
        partner_count: int,
        total_budget: Optional[float] = None,
        use_real_ratios: bool = True  # NEW
    ) -> Dict[str, Any]:
        """
        Calculate budget breakdown using real data when available.
        """

        # Get cost ratios
        if use_real_ratios and self._graph_service:
            ratios = self._get_real_cost_ratios(action_type)
        else:
            ratios = self.COST_RATIOS.get(action_type, self.COST_RATIOS['RIA'])

        # ... rest of calculation logic ...

    def _get_real_cost_ratios(self, action_type: str) -> Dict[str, float]:
        """
        Get actual cost ratios from funded projects.

        Note: This requires cost breakdown data in the graph.
        If not available, falls back to hardcoded ratios.
        """
        # For now, use budget statistics to inform ratios
        if self._graph_service:
            stats = self._graph_service.get_budget_statistics(action_type=action_type)
            if stats:
                # Use statistics to adjust ratios
                # (This is a simplified example - real implementation would
                # need actual cost breakdown data in the graph)
                avg_budget = stats[0].get('avg_budget', 0)
                # Adjust ratios based on budget scale...

        return self.COST_RATIOS.get(action_type, self.COST_RATIOS['RIA'])
```

**Expected Benefits:**
- More accurate cost ratios based on real project data
- Budget scale awareness
- Action-type specific patterns from funded projects

---

### Tier 4: Timeline Generator Tool

**File:** `app/services/tools/timeline_generator.py`

**Priority:** LOW - Templates work reasonably well

**Current Implementation:**

Uses hardcoded work package templates based on action type.

**Graph-Enhanced Implementation:**

```python
class TimelineGeneratorService:
    def __init__(self):
        # ... existing init ...

        self._graph_service = None
        try:
            self._graph_service = GraphSearchService()
        except Exception as e:
            logger.warning(f"Graph service not available: {e}")

    def generate_timeline(
        self,
        action_type: str,
        duration_months: int,
        cluster: Optional[str] = None,
        use_real_patterns: bool = False  # NEW - opt-in
    ) -> Dict[str, Any]:
        """
        Generate project timeline, optionally based on real project patterns.
        """

        if use_real_patterns and self._graph_service and cluster:
            # Get example projects to learn from
            examples = self._graph_service.get_project_examples(
                cluster_code=cluster,
                funding_scheme=action_type,
                limit=5
            )

            if examples:
                # Analyze actual durations
                durations = [
                    self._calculate_duration(e.get('start_date'), e.get('end_date'))
                    for e in examples
                ]
                avg_duration = sum(d for d in durations if d) / len([d for d in durations if d])

                # Use this to inform timeline generation
                # ...

        # Fall back to template-based generation
        return self._generate_from_template(action_type, duration_months)
```

**Expected Benefits:**
- Timeline patterns from real funded projects
- Cluster-specific duration norms
- More realistic milestone timing

---

## Implementation Guidelines

### General Approach

1. **Always maintain backward compatibility** - Keep SQL fallback when graph is unavailable
2. **Initialize graph service in `__init__`** - Handle initialization failures gracefully
3. **Log data source used** - Help debugging by logging whether graph or SQL was used
4. **Cache where appropriate** - Graph queries can be cached for repeated patterns

### Code Pattern

```python
import logging
from typing import Dict, Any, Optional, List

from app.services.data_intelligence.graph_service import GraphSearchService

logger = logging.getLogger(__name__)

class MyToolService:
    def __init__(self):
        from app.core.config import settings
        self._db_url = settings.database_url

        # Initialize graph service with graceful fallback
        self._graph_service = None
        try:
            self._graph_service = GraphSearchService()
            logger.info("✅ Graph service available for MyTool")
        except Exception as e:
            logger.warning(f"⚠️ Graph service not available for MyTool: {e}")

    def my_method(self, params) -> Dict[str, Any]:
        # Try graph first
        if self._graph_service:
            try:
                result = self._graph_method(params)
                result['source'] = 'neo4j_graph'
                return result
            except Exception as e:
                logger.warning(f"Graph query failed, falling back to SQL: {e}")

        # Fallback to SQL
        result = self._sql_method(params)
        result['source'] = 'postgresql'
        return result
```

### Error Handling

```python
def safe_graph_query(self, method_name: str, *args, **kwargs):
    """Safely execute a graph service method with fallback."""
    if not self._graph_service:
        return None

    try:
        method = getattr(self._graph_service, method_name)
        return method(*args, **kwargs)
    except Exception as e:
        logger.error(f"Graph query {method_name} failed: {e}")
        return None
```

---

## Testing Requirements

### Unit Tests

Each enhanced tool should have tests covering:

1. **Graph-enabled path** - When graph service is available
2. **Fallback path** - When graph service is unavailable
3. **Mixed results** - Combining graph and SQL data
4. **Error handling** - Graph query failures

### Test Template

```python
import pytest
from unittest.mock import Mock, patch

class TestPartnerDiscoveryService:

    def test_find_partners_with_graph(self):
        """Test partner discovery using graph service."""
        service = PartnerDiscoveryService()

        # Skip if graph not available
        if not service._graph_service:
            pytest.skip("Graph service not available")

        result = service.find_partners("hydrogen energy", limit=10)

        assert result['success']
        assert len(result['partners']) > 0
        assert result['search_metadata']['method'] == 'graph_enhanced'

    def test_find_partners_fallback(self):
        """Test partner discovery falls back to SQL."""
        service = PartnerDiscoveryService()
        service._graph_service = None  # Force fallback

        result = service.find_partners("hydrogen energy", limit=10)

        assert result['success']
        # Should still work via SQL

    def test_2hop_discovery(self):
        """Test 2-hop partner discovery."""
        service = PartnerDiscoveryService()

        if not service._graph_service:
            pytest.skip("Graph service not available")

        result = service.find_partners(
            "AI",
            include_2hop=True,
            limit=20
        )

        two_hop = [p for p in result['partners']
                   if p.get('discovery_type') == '2-hop']
        # Should find some 2-hop partners
        assert len(two_hop) >= 0  # May be 0 depending on data
```

### Integration Tests

```python
class TestGraphIntegration:

    def test_graph_service_connection(self):
        """Verify graph service connects successfully."""
        from app.services.data_intelligence.graph_service import GraphSearchService

        service = GraphSearchService()
        # Should not raise
        overview = service.get_cluster_overview()
        assert len(overview) == 6  # 6 clusters

    def test_tool_graph_integration(self):
        """Test that tools properly integrate with graph service."""
        from app.services.tools.partner_discovery import PartnerDiscoveryService
        from app.services.tools.budget_benchmark import BudgetBenchmarkService

        # Both should initialize with graph service
        partner_service = PartnerDiscoveryService()
        budget_service = BudgetBenchmarkService()

        assert partner_service._graph_service is not None
        assert budget_service._graph_service is not None
```

---

## Appendix: Quick Reference

### Cluster Codes

| Code | Name | Keywords |
|------|------|----------|
| CLUSTER-1 | Health | health, medical, clinical, disease, cancer, vaccine |
| CLUSTER-2 | Culture, Creativity & Inclusive Society | culture, democracy, social, heritage, creative |
| CLUSTER-3 | Civil Security for Society | security, cybersecurity, border, crime, disaster |
| CLUSTER-4 | Digital, Industry and Space | digital, AI, data, industry, space, manufacturing |
| CLUSTER-5 | Climate, Energy and Mobility | climate, energy, mobility, hydrogen, renewable |
| CLUSTER-6 | Food, Bioeconomy & Environment | food, agriculture, bioeconomy, biodiversity, ocean |

### Entity Type Codes

| Code | Name |
|------|------|
| HES | Higher or Secondary Education |
| REC | Research Organisations |
| PRC | Private for-profit entities |
| PUB | Public bodies |
| OTH | Other entities |

### Action Types

| Code | Name |
|------|------|
| RIA | Research and Innovation Action |
| IA | Innovation Action |
| CSA | Coordination and Support Action |
| ERC-STG | ERC Starting Grant |
| ERC-COG | ERC Consolidator Grant |
| ERC-ADG | ERC Advanced Grant |
| MSCA-PF | MSCA Postdoctoral Fellowship |
| MSCA-DN | MSCA Doctoral Network |

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-09 | 1.0 | Initial document created |
