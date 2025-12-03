# Task 1: Budget Benchmarking Tool

## Overview

**Tool Name:** `get_budget_benchmark`
**Priority:** High (simplest to implement, high user value)
**Data Sources:** Neo4j graph database, CORDIS PostgreSQL
**Estimated Complexity:** Low

---

## Purpose

Provide users with **real budget statistics** from funded Horizon Europe projects to help them set realistic budget expectations for their proposals.

### User Questions It Answers
- "What's a typical budget for a Climate RIA?"
- "How much EU contribution should I request for an IA project?"
- "What's the average budget per partner in Cluster 4?"
- "Is €5M realistic for a health AI project?"

---

## Function Signature

```python
def get_budget_benchmark(
    cluster: Optional[str] = None,        # e.g., "CL4", "CL5", "EIC"
    action_type: Optional[str] = None,    # e.g., "RIA", "IA", "CSA"
    topic_keywords: Optional[str] = None, # e.g., "hydrogen", "AI", "quantum"
    year: Optional[int] = None            # Filter by funding year
) -> Dict[str, Any]:
    """
    Get budget benchmarks from funded Horizon Europe projects.

    Returns statistics on:
    - Total EU contribution (min, max, average, median)
    - Budget per partner (average)
    - Consortium sizes
    - Number of projects analyzed
    """
```

---

## Expected Output

```json
{
    "query_params": {
        "cluster": "CL4",
        "action_type": "RIA",
        "topic_keywords": "artificial intelligence"
    },
    "statistics": {
        "projects_analyzed": 127,
        "total_eu_contribution": {
            "min": 2500000,
            "max": 12000000,
            "average": 5850000,
            "median": 5200000,
            "std_dev": 2100000
        },
        "budget_per_partner": {
            "average": 650000,
            "median": 550000
        },
        "consortium_size": {
            "min": 3,
            "max": 21,
            "average": 9,
            "median": 8
        }
    },
    "recommendations": {
        "suggested_budget_range": "€4-7 million",
        "suggested_consortium_size": "8-12 partners",
        "suggested_budget_per_partner": "€500-700k"
    },
    "sample_projects": [
        {
            "acronym": "AI4HEALTH",
            "title": "AI for Personalized Healthcare",
            "total_cost": 6200000,
            "eu_contribution": 6200000,
            "partners": 10
        }
    ]
}
```

---

## Data Sources & Queries

### Neo4j Query (Primary)

```cypher
MATCH (p:Project)-[:FUNDED_BY]->(prog:Programme)
WHERE prog.name CONTAINS $cluster
  AND p.action_type = $action_type
  AND ($keywords IS NULL OR p.objective CONTAINS $keywords)
WITH p
MATCH (p)<-[:PARTICIPATES_IN]-(o:Organisation)
WITH p, count(o) as partner_count
RETURN
    count(p) as project_count,
    avg(p.total_cost) as avg_budget,
    min(p.total_cost) as min_budget,
    max(p.total_cost) as max_budget,
    percentileCont(p.total_cost, 0.5) as median_budget,
    stDev(p.total_cost) as std_dev,
    avg(partner_count) as avg_partners,
    avg(p.total_cost / partner_count) as avg_per_partner
```

### PostgreSQL Query (Fallback)

```sql
SELECT
    COUNT(*) as project_count,
    AVG(ec_max_contribution) as avg_budget,
    MIN(ec_max_contribution) as min_budget,
    MAX(ec_max_contribution) as max_budget,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ec_max_contribution) as median_budget,
    STDDEV(ec_max_contribution) as std_dev
FROM projects
WHERE framework_programme = 'HORIZON'
  AND ($cluster IS NULL OR topics LIKE '%' || $cluster || '%')
  AND ($action_type IS NULL OR funding_scheme LIKE '%' || $action_type || '%')
  AND ($keywords IS NULL OR objective ILIKE '%' || $keywords || '%');
```

---

## Implementation Steps

### Step 1: Create the Tool Function

**File:** `app/services/tools/budget_benchmark.py`

```python
from typing import Optional, Dict, Any
from app.services.graph_service import GraphSearchService
from app.data.cordis_repository import CordisProjectRepository

class BudgetBenchmarkTool:
    def __init__(self):
        self.graph_service = GraphSearchService()
        self.project_repo = CordisProjectRepository()

    async def get_benchmark(
        self,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        topic_keywords: Optional[str] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        # Implementation here
        pass
```

### Step 2: Register in Tool Registry

**File:** `app/services/tools/__init__.py`

Add import and registration for `get_budget_benchmark`.

### Step 3: Add to ToolAwareAgent

**File:** `app/services/agents/tool_aware_agent.py`

Add tool description:
```python
{
    "name": "get_budget_benchmark",
    "description": "Get real budget statistics from funded Horizon Europe projects. Use this when users ask about typical budgets, EU contributions, or budget-per-partner for specific clusters, action types, or topics.",
    "parameters": {
        "cluster": "Optional cluster code (CL4, CL5, EIC, etc.)",
        "action_type": "Optional action type (RIA, IA, CSA)",
        "topic_keywords": "Optional keywords to filter projects",
        "year": "Optional funding year filter"
    }
}
```

### Step 4: Add Integration Test

**File:** `tests/test_budget_benchmark.py`

```python
async def test_budget_benchmark_cluster():
    result = await get_budget_benchmark(cluster="CL4", action_type="RIA")
    assert result["statistics"]["projects_analyzed"] > 0
    assert result["statistics"]["total_eu_contribution"]["average"] > 0
```

---

## Edge Cases to Handle

1. **No matching projects**: Return helpful message suggesting broader criteria
2. **Very few projects (<5)**: Add warning that statistics may not be representative
3. **Invalid cluster/action_type**: Return list of valid options
4. **Outliers**: Consider excluding extreme outliers for more representative stats

---

## Success Criteria

- [ ] Tool returns accurate statistics matching actual CORDIS data
- [ ] Response includes min/max/avg/median for budgets
- [ ] Recommendations are sensible and based on data
- [ ] Works with various combinations of filters
- [ ] Sample projects shown for context
- [ ] Performance: <2s response time

---

## Testing Questions

Run these against the tool to verify quality:

1. "What's a typical budget for a Cluster 4 RIA project?"
2. "How much should I budget for an EIC Accelerator application?"
3. "What's the average consortium size for health projects?"
4. "Is €8 million realistic for a hydrogen IA project?"
