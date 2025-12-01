# TASK_12: Advanced Graph Queries (F-H)

## Metadata
| Field | Value |
|-------|-------|
| **Task ID** | TASK_12 |
| **Day** | 10 |
| **Estimated Time** | 3 hours |
| **Dependencies** | TASK_04 (Graph Service) |
| **Blocks** | TASK_15 |
| **Priority** | Medium |

## Objective

Extend GraphSearchService with advanced query types:
- **Query Type F**: Project examples with success metrics
- **Query Type G**: Organization history and track record
- **Query Type H**: Trend analysis across time periods

## Implementation

### Add to `app/services/data_intelligence/graph_service.py`:

```python
# ========================================================================
# QUERY TYPE F: Project Examples with Success Metrics
# ========================================================================

def get_project_examples(
    self,
    cluster_code: Optional[str] = None,
    topic_pattern: Optional[str] = None,
    funding_scheme: Optional[str] = None,
    min_budget: float = 0,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get example projects with their details and success indicators.
    
    Args:
        cluster_code: Filter by cluster
        topic_pattern: Topic code pattern to match
        funding_scheme: Filter by RIA, IA, CSA, etc.
        min_budget: Minimum budget threshold
        limit: Maximum results
        
    Returns:
        List of projects with consortium details
    """
    where_clauses = []
    params = {"limit": limit, "min_budget": min_budget}
    
    if cluster_code:
        where_clauses.append("c.code = $cluster_code")
        params["cluster_code"] = cluster_code.upper()
    
    if topic_pattern:
        where_clauses.append("t.code CONTAINS $topic_pattern")
        params["topic_pattern"] = topic_pattern.upper()
    
    if funding_scheme:
        where_clauses.append("p.fundingScheme CONTAINS $funding_scheme")
        params["funding_scheme"] = funding_scheme.upper()
    
    where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    query = f"""
    MATCH (p:Project)-[:FUNDED_UNDER]->(t:Topic)
    OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
    {where_clause}
    
    WHERE p.ecMaxContribution >= $min_budget
    
    // Get consortium info
    OPTIONAL MATCH (o:Organization)-[r:PARTICIPATES_IN]->(p)
    OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)
    
    WITH p, t, c,
         COUNT(DISTINCT o) as partnerCount,
         COUNT(DISTINCT co) as countryCount,
         COLLECT(DISTINCT {{
             name: o.name,
             country: co.isoCode,
             role: r.role
         }})[0..5] as partners
    
    RETURN p.id as projectId,
           p.acronym as acronym,
           p.title as title,
           p.objective as objective,
           p.status as status,
           p.startDate as startDate,
           p.endDate as endDate,
           p.ecMaxContribution as budget,
           p.fundingScheme as fundingScheme,
           t.code as topicCode,
           c.code as clusterCode,
           c.name as clusterName,
           partnerCount,
           countryCount,
           partners
    ORDER BY p.ecMaxContribution DESC
    LIMIT $limit
    """
    
    try:
        return self.db.execute_query(query, params)
    except Exception as e:
        logger.error(f"Error getting project examples: {e}")
        return []

# ========================================================================
# QUERY TYPE G: Organization Track Record
# ========================================================================

def get_organization_track_record(
    self,
    org_name: str,
    include_partners: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive track record for an organization.
    
    Args:
        org_name: Organization name (partial match)
        include_partners: Include top collaboration partners
        
    Returns:
        Organization profile with project history and statistics
    """
    query = """
    MATCH (o:Organization)
    WHERE toLower(o.name) CONTAINS toLower($org_name)
       OR toLower(o.shortName) CONTAINS toLower($org_name)
    
    OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)
    OPTIONAL MATCH (o)-[:IS_TYPE]->(et:EntityType)
    OPTIONAL MATCH (o)-[r:PARTICIPATES_IN]->(p:Project)
    OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
    OPTIONAL MATCH (p)-[:FUNDED_UNDER]->(t:Topic)
    
    WITH o, co, et,
         COLLECT(DISTINCT {
             id: p.id,
             acronym: p.acronym,
             title: p.title,
             budget: p.ecMaxContribution,
             role: r.role,
             status: p.status,
             cluster: c.code,
             topic: t.code
         }) as projects
    
    // Calculate statistics
    WITH o, co, et, projects,
         SIZE(projects) as totalProjects,
         SIZE([p IN projects WHERE p.role = 'coordinator']) as coordinations,
         REDUCE(s = 0.0, p IN projects | s + COALESCE(p.budget, 0)) as totalFunding,
         [c IN COLLECT(DISTINCT [p IN projects | p.cluster]) | c][0] as clusters
    
    RETURN o.id as orgId,
           o.name as name,
           o.shortName as shortName,
           co.isoCode as country,
           co.name as countryName,
           et.code as entityType,
           et.name as entityTypeName,
           totalProjects,
           coordinations,
           totalFunding,
           clusters,
           projects[0..10] as recentProjects
    LIMIT 1
    """
    
    try:
        results = self.db.execute_query(query, {"org_name": org_name})
        
        if not results:
            return None
        
        result = results[0]
        
        # Get top partners if requested
        if include_partners:
            partners = self.find_organization_partners(org_name, limit=5)
            result["topPartners"] = partners
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting organization track record: {e}")
        return None

# ========================================================================
# QUERY TYPE H: Trend Analysis
# ========================================================================

def get_funding_trends(
    self,
    cluster_code: Optional[str] = None,
    group_by: str = "year"  # "year" or "quarter"
) -> List[Dict[str, Any]]:
    """
    Get funding trends over time.
    
    Args:
        cluster_code: Optional cluster filter
        group_by: Time grouping ("year" or "quarter")
        
    Returns:
        List of time periods with funding statistics
    """
    where_clause = ""
    params = {}
    
    if cluster_code:
        where_clause = "WHERE c.code = $cluster_code"
        params["cluster_code"] = cluster_code.upper()
    
    if group_by == "quarter":
        date_extract = "substring(p.startDate, 0, 7)"  # YYYY-MM
    else:
        date_extract = "substring(p.startDate, 0, 4)"  # YYYY
    
    query = f"""
    MATCH (p:Project)
    OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
    {where_clause}
    
    WHERE p.startDate IS NOT NULL
    
    WITH {date_extract} as period, p, c
    
    WITH period,
         COUNT(p) as projectCount,
         SUM(p.ecMaxContribution) as totalFunding,
         AVG(p.ecMaxContribution) as avgBudget,
         COLLECT(DISTINCT c.code) as clusters
    
    RETURN period,
           projectCount,
           totalFunding,
           avgBudget,
           clusters
    ORDER BY period
    """
    
    try:
        return self.db.execute_query(query, params)
    except Exception as e:
        logger.error(f"Error getting funding trends: {e}")
        return []
```

## Acceptance Criteria

- [ ] get_project_examples returns filtered projects
- [ ] get_organization_track_record returns comprehensive data
- [ ] get_funding_trends returns time-series data
- [ ] All methods handle empty results gracefully

## Verification

```bash
python -c "
from app.services.data_intelligence.graph_service import GraphSearchService
service = GraphSearchService()

# Test project examples
projects = service.get_project_examples(cluster_code='CLUSTER-4', limit=3)
print(f'Project examples: {len(projects)}')

# Test org track record
record = service.get_organization_track_record('Fraunhofer')
print(f'Org record: {record is not None}')

# Test trends
trends = service.get_funding_trends()
print(f'Trend periods: {len(trends)}')
"
```

