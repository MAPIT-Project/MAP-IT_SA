# Task 2: Consortium Patterns Tool

## Overview

**Tool Name:** `get_consortium_patterns`
**Priority:** High (leverages existing Neo4j relationships)
**Data Sources:** Neo4j graph database (organization relationships)
**Estimated Complexity:** Medium

---

## Purpose

Analyze **real consortium compositions** from funded projects to help users understand what successful consortia look like in their domain.

### User Questions It Answers
- "What's the typical consortium composition for Health projects?"
- "How many SMEs are usually in an IA project?"
- "Which countries lead Digital projects?"
- "What's the ideal mix of academia vs industry?"
- "How many countries should be in my consortium?"

---

## Function Signature

```python
def get_consortium_patterns(
    cluster: Optional[str] = None,        # e.g., "CL4", "CL5", "EIC"
    action_type: Optional[str] = None,    # e.g., "RIA", "IA", "CSA"
    topic_keywords: Optional[str] = None, # e.g., "AI", "quantum", "hydrogen"
    min_projects: int = 10                # Minimum projects for reliable patterns
) -> Dict[str, Any]:
    """
    Analyze consortium composition patterns from funded Horizon Europe projects.

    Returns patterns on:
    - Organization type distribution (HES, REC, PRC, SME, etc.)
    - Country distribution and diversity
    - Coordinator profiles
    - Partner role patterns
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
    "projects_analyzed": 127,
    "consortium_size": {
        "min": 4,
        "max": 18,
        "average": 9.2,
        "median": 9,
        "recommended": "8-12 partners"
    },
    "organization_type_distribution": {
        "HES": {
            "percentage": 35,
            "avg_per_project": 3.2,
            "description": "Higher Education Institutions"
        },
        "REC": {
            "percentage": 28,
            "avg_per_project": 2.6,
            "description": "Research Organizations"
        },
        "PRC": {
            "percentage": 22,
            "avg_per_project": 2.0,
            "description": "Private Companies (Large)"
        },
        "SME": {
            "percentage": 15,
            "avg_per_project": 1.4,
            "description": "Small/Medium Enterprises"
        }
    },
    "country_patterns": {
        "top_participating": [
            {"country": "Germany", "participation_rate": 45, "avg_partners": 1.8},
            {"country": "France", "participation_rate": 38, "avg_partners": 1.5},
            {"country": "Italy", "participation_rate": 35, "avg_partners": 1.4},
            {"country": "Spain", "participation_rate": 32, "avg_partners": 1.3},
            {"country": "Netherlands", "participation_rate": 28, "avg_partners": 1.1}
        ],
        "geographic_diversity": {
            "avg_countries": 7.5,
            "min_countries": 3,
            "max_countries": 15
        }
    },
    "coordinator_profile": {
        "by_type": {
            "HES": 42,
            "REC": 35,
            "PRC": 18,
            "SME": 5
        },
        "by_country": {
            "Germany": 22,
            "France": 15,
            "Spain": 12,
            "Italy": 11,
            "Netherlands": 10
        }
    },
    "recommendations": {
        "ideal_composition": [
            "3-4 universities/research institutions (expertise & credibility)",
            "2-3 large companies (exploitation & scale)",
            "2-3 SMEs (innovation & agility)",
            "1-2 additional specialized partners"
        ],
        "country_advice": "Include partners from 6-10 EU member states for good geographic balance",
        "coordinator_advice": "Universities and research organizations coordinate most successfully in RIA"
    },
    "sample_consortia": [
        {
            "project_acronym": "AI4FUTURE",
            "consortium_size": 10,
            "countries": 8,
            "composition": {
                "HES": 4,
                "REC": 2,
                "PRC": 2,
                "SME": 2
            },
            "coordinator": {
                "name": "Technical University of Munich",
                "type": "HES",
                "country": "Germany"
            }
        }
    ]
}
```

---

## Data Sources & Queries

### Neo4j Query: Organization Type Distribution

```cypher
MATCH (p:Project)-[:FUNDED_BY]->(prog:Programme)
WHERE prog.name CONTAINS $cluster
  AND ($action_type IS NULL OR p.action_type = $action_type)
WITH p
MATCH (o:Organisation)-[r:PARTICIPATES_IN]->(p)
WITH p, o.activity_type as org_type, count(*) as type_count
WITH p.id as project_id, collect({type: org_type, count: type_count}) as composition
RETURN
    org_type,
    count(*) as total_participations,
    avg(type_count) as avg_per_project,
    round(100.0 * count(*) / sum(count(*)) OVER (), 2) as percentage
ORDER BY total_participations DESC
```

### Neo4j Query: Country Patterns

```cypher
MATCH (p:Project)-[:FUNDED_BY]->(prog:Programme)
WHERE prog.name CONTAINS $cluster
WITH p
MATCH (o:Organisation)-[:PARTICIPATES_IN]->(p)
WITH p, o.country as country
WITH p, collect(DISTINCT country) as countries, count(DISTINCT country) as country_count
UNWIND countries as country
RETURN
    country,
    count(*) as projects_participated,
    round(100.0 * count(*) / (SELECT count(DISTINCT p) FROM projects), 2) as participation_rate
ORDER BY projects_participated DESC
LIMIT 20
```

### Neo4j Query: Coordinator Profile

```cypher
MATCH (o:Organisation)-[r:PARTICIPATES_IN {role: 'coordinator'}]->(p:Project)
WHERE p.framework_programme = 'HORIZON'
  AND ($cluster IS NULL OR p.topics CONTAINS $cluster)
RETURN
    o.activity_type as coordinator_type,
    o.country as coordinator_country,
    count(*) as coordination_count
ORDER BY coordination_count DESC
```

---

## Implementation Steps

### Step 1: Create the Tool Function

**File:** `app/services/tools/consortium_patterns.py`

```python
from typing import Optional, Dict, Any, List
from app.services.graph_service import GraphSearchService
import logging

logger = logging.getLogger(__name__)

class ConsortiumPatternsTool:
    def __init__(self):
        self.graph_service = GraphSearchService()

    async def get_patterns(
        self,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        topic_keywords: Optional[str] = None,
        min_projects: int = 10
    ) -> Dict[str, Any]:
        """Get consortium composition patterns from funded projects."""

        # Query organization type distribution
        org_distribution = await self._get_org_type_distribution(
            cluster, action_type, topic_keywords
        )

        # Query country patterns
        country_patterns = await self._get_country_patterns(
            cluster, action_type, topic_keywords
        )

        # Query coordinator profiles
        coordinator_profile = await self._get_coordinator_profile(
            cluster, action_type, topic_keywords
        )

        # Get sample consortia
        sample_consortia = await self._get_sample_consortia(
            cluster, action_type, topic_keywords
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            org_distribution, country_patterns, coordinator_profile, action_type
        )

        return {
            "query_params": {
                "cluster": cluster,
                "action_type": action_type,
                "topic_keywords": topic_keywords
            },
            "projects_analyzed": org_distribution.get("total_projects", 0),
            "consortium_size": org_distribution.get("consortium_size", {}),
            "organization_type_distribution": org_distribution.get("by_type", {}),
            "country_patterns": country_patterns,
            "coordinator_profile": coordinator_profile,
            "recommendations": recommendations,
            "sample_consortia": sample_consortia
        }

    def _generate_recommendations(
        self,
        org_dist: Dict,
        country_patterns: Dict,
        coordinator: Dict,
        action_type: Optional[str]
    ) -> Dict[str, Any]:
        """Generate actionable recommendations based on patterns."""
        # Implementation with data-driven advice
        pass
```

### Step 2: Add Organization Type Descriptions

```python
ORG_TYPE_DESCRIPTIONS = {
    "HES": "Higher Education Institutions (Universities)",
    "REC": "Research Organizations",
    "PRC": "Private Companies (Large)",
    "SME": "Small and Medium Enterprises",
    "PUB": "Public Bodies",
    "OTH": "Other Organizations"
}
```

### Step 3: Register in Tool Registry

**File:** `app/services/tools/__init__.py`

### Step 4: Add to ToolAwareAgent

**File:** `app/services/agents/tool_aware_agent.py`

```python
{
    "name": "get_consortium_patterns",
    "description": "Analyze consortium composition patterns from funded Horizon Europe projects. Use when users ask about typical consortium composition, partner types, country distribution, or coordinator profiles for specific domains.",
    "parameters": {
        "cluster": "Optional cluster code (CL4, CL5, CL6, EIC, etc.)",
        "action_type": "Optional action type (RIA, IA, CSA)",
        "topic_keywords": "Optional keywords to filter by topic"
    }
}
```

---

## Edge Cases to Handle

1. **Few matching projects**: Warn if <10 projects, suggest broadening criteria
2. **New clusters/topics**: May have limited data, be transparent about sample size
3. **Associated Countries**: Handle non-EU countries (UK, Switzerland, etc.) appropriately
4. **Project duration impact**: Larger projects may have different patterns

---

## Success Criteria

- [ ] Returns accurate organization type breakdown
- [ ] Country participation rates match CORDIS data
- [ ] Coordinator profiles are insightful
- [ ] Recommendations are data-driven (not generic)
- [ ] Sample consortia provide concrete examples
- [ ] Performance: <3s response time

---

## Testing Questions

1. "What's the typical consortium composition for Cluster 4 AI projects?"
2. "How many SMEs should I include in my IA consortium?"
3. "Which countries lead in Health research projects?"
4. "What type of organization usually coordinates RIA projects?"
5. "How many countries should be in a Horizon Europe consortium?"
