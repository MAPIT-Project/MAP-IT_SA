# TASK_13: Consortium Builder Tool

## Metadata
| Field | Value |
|-------|-------|
| **Task ID** | TASK_13 |
| **Day** | 11 |
| **Estimated Time** | 2 hours |
| **Dependencies** | TASK_04, TASK_12 |
| **Blocks** | TASK_15 |
| **Priority** | Medium |

## Objective

Create a `consortium_builder` tool that suggests potential consortium partners based on:
- Track record in relevant topics/clusters
- Geographic diversity (EU country coverage)
- Entity type mix (REC, HES, PRC balance)
- Prior collaboration history

## Implementation

Add to `app/services/data_intelligence/graph_service.py`:

```python
def suggest_consortium_partners(
    self,
    cluster_code: str,
    topic_code: Optional[str] = None,
    coordinator_country: Optional[str] = None,
    target_partner_count: int = 5,
    required_entity_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Suggest potential consortium partners for a project.

    Args:
        cluster_code: Target cluster
        topic_code: Specific topic (optional)
        coordinator_country: Coordinator's country to exclude
        target_partner_count: Number of partners to suggest
        required_entity_types: Required entity types ["HES", "REC", "PRC"]

    Returns:
        Dictionary with suggested partners grouped by role/type
    """
    params = {
        "cluster_code": cluster_code.upper(),
        "limit": target_partner_count * 3  # Get more to filter
    }

    if topic_code:
        params["topic_code"] = topic_code.upper()

    if coordinator_country:
        params["coord_country"] = coordinator_country.upper()

    # Find organizations active in this cluster with good track record
    query = """
    MATCH (o:Organization)-[r:PARTICIPATES_IN]->(p:Project)-[:TARGETS]->(c:Cluster {code: $cluster_code})
    OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)
    OPTIONAL MATCH (o)-[:IS_TYPE]->(et:EntityType)

    // Filter out coordinator country if specified
    WHERE $coord_country IS NULL OR co.isoCode <> $coord_country

    WITH o, co, et,
         COUNT(DISTINCT p) as projectCount,
         COUNT(CASE WHEN r.role = 'coordinator' THEN 1 END) as coordinations,
         SUM(r.ecContribution) as totalFunding

    WHERE projectCount >= 2  // Minimum experience

    RETURN o.id as orgId,
           o.name as name,
           o.shortName as shortName,
           co.isoCode as country,
           co.name as countryName,
           et.code as entityType,
           et.name as entityTypeName,
           projectCount,
           coordinations,
           totalFunding
    ORDER BY projectCount DESC, coordinations DESC
    LIMIT $limit
    """

    try:
        candidates = self.db.execute_query(query, params)

        # Group by entity type
        by_type = {"HES": [], "REC": [], "PRC": [], "PUB": [], "OTH": []}
        countries_seen = set()

        suggestions = []

        for candidate in candidates:
            entity_type = candidate.get("entityType", "OTH")
            country = candidate.get("country")

            # Prioritize geographic diversity
            if country not in countries_seen or len(by_type.get(entity_type, [])) < 2:
                by_type.setdefault(entity_type, []).append(candidate)
                countries_seen.add(country)
                suggestions.append(candidate)

                if len(suggestions) >= target_partner_count:
                    break

        return {
            "cluster": cluster_code,
            "topic": topic_code,
            "suggestions": suggestions[:target_partner_count],
            "by_entity_type": {k: v[:2] for k, v in by_type.items() if v},
            "countries_covered": list(countries_seen)[:10],
            "total_candidates": len(candidates)
        }

    except Exception as e:
        logger.error(f"Error suggesting consortium partners: {e}")
        return {"suggestions": [], "error": str(e)}
```

Register as tool in `tool_orchestrator.py`:

```python
async def consortium_builder(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Build consortium suggestions."""
    from ..data_intelligence.graph_service import GraphSearchService

    service = GraphSearchService()
    result = service.suggest_consortium_partners(
        cluster_code=params.get("cluster_code", ""),
        topic_code=params.get("topic_code"),
        coordinator_country=params.get("coordinator_country"),
        target_partner_count=params.get("target_partners", 5)
    )

    return {
        "success": True,
        "tool_name": "consortium_builder",
        "results": result
    }
```

## Acceptance Criteria

- [ ] Returns diverse partner suggestions
- [ ] Geographic diversity considered
- [ ] Entity type balance maintained
- [ ] Filters by track record
