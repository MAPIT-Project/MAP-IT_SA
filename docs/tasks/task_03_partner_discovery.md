# Task 3: Partner Discovery Tool

## Overview

**Tool Name:** `find_experienced_partners`
**Priority:** High (directly actionable for users)
**Data Sources:** Neo4j graph + PostgreSQL (organization history)
**Estimated Complexity:** Medium-High

---

## Purpose

Help users **find potential consortium partners** based on their track record in relevant Horizon Europe projects. This provides real, verifiable partner suggestions based on actual project participation.

### User Questions It Answers
- "Who are experienced partners for quantum computing projects?"
- "Which German organizations work on renewable energy?"
- "Find SMEs with hydrogen project experience"
- "Which universities have strong AI track records?"
- "Find partners who've coordinated Health projects"

---

## Function Signature

```python
def find_experienced_partners(
    topic_keywords: str,                  # Required: e.g., "quantum computing", "hydrogen"
    country: Optional[str] = None,        # e.g., "Germany", "DE", "France"
    organization_type: Optional[str] = None,  # e.g., "HES", "SME", "REC", "PRC"
    cluster: Optional[str] = None,        # e.g., "CL4", "CL5"
    min_projects: int = 2,                # Minimum projects to be considered experienced
    role_filter: Optional[str] = None,    # "coordinator", "participant", or None for both
    limit: int = 20                       # Max results to return
) -> Dict[str, Any]:
    """
    Find organizations with proven track records in relevant Horizon Europe projects.

    Returns organizations ranked by:
    - Number of relevant projects
    - Coordinator experience
    - Topic relevance
    - Funding amount received
    """
```

---

## Expected Output

```json
{
    "query_params": {
        "topic_keywords": "quantum computing",
        "country": "Germany",
        "organization_type": null,
        "cluster": "CL4"
    },
    "total_found": 45,
    "experienced_partners": [
        {
            "name": "Fraunhofer-Gesellschaft",
            "short_name": "Fraunhofer",
            "country": "Germany",
            "city": "Munich",
            "type": "REC",
            "type_description": "Research Organization",
            "track_record": {
                "total_he_projects": 847,
                "relevant_projects": 12,
                "as_coordinator": 3,
                "as_participant": 9,
                "total_funding_received": 45000000,
                "funding_in_relevant_projects": 8500000
            },
            "relevant_projects": [
                {
                    "acronym": "QUCATS",
                    "title": "Quantum Computing at Scale",
                    "role": "coordinator",
                    "funding": 2100000,
                    "start_date": "2023-01-01",
                    "status": "active"
                },
                {
                    "acronym": "QUANTECH",
                    "title": "Quantum Technologies for Europe",
                    "role": "participant",
                    "funding": 1800000,
                    "start_date": "2022-06-01",
                    "status": "active"
                }
            ],
            "expertise_indicators": [
                "Strong quantum physics expertise",
                "Experience coordinating large consortia",
                "Active in Cluster 4 Digital topics"
            ],
            "collaboration_score": 0.92,
            "contact_hint": "Look for quantum computing division"
        },
        {
            "name": "Technical University of Munich",
            "short_name": "TUM",
            "country": "Germany",
            "city": "Munich",
            "type": "HES",
            "type_description": "Higher Education Institution",
            "track_record": {
                "total_he_projects": 523,
                "relevant_projects": 8,
                "as_coordinator": 2,
                "as_participant": 6,
                "total_funding_received": 32000000,
                "funding_in_relevant_projects": 4200000
            },
            "relevant_projects": [
                // ... project list
            ],
            "expertise_indicators": [
                "Leading quantum information research group",
                "Strong industry connections",
                "Experience with ERC and RIA projects"
            ],
            "collaboration_score": 0.88
        }
    ],
    "aggregated_insights": {
        "most_common_partner_types": ["REC", "HES", "PRC"],
        "top_countries_in_topic": ["Germany", "Netherlands", "France"],
        "typical_partner_project_count": 5,
        "emerging_partners": [
            {
                "name": "Quantum Machines Ltd",
                "note": "Newer player with 2 recent projects, growing fast"
            }
        ]
    },
    "search_tips": [
        "Consider including partners from Netherlands - strong quantum ecosystem",
        "SMEs in this space often focus on specific hardware/software niches",
        "Check for complementary expertise (theory vs. applications)"
    ]
}
```

---

## Data Sources & Queries

### Neo4j Query: Find Organizations by Topic Experience

```cypher
// Find organizations with experience in matching projects
MATCH (o:Organisation)-[r:PARTICIPATES_IN]->(p:Project)
WHERE p.objective CONTAINS $topic_keywords
   OR p.title CONTAINS $topic_keywords
   OR p.topics CONTAINS $topic_keywords
WITH o, p, r

// Apply filters
WHERE ($country IS NULL OR o.country = $country)
  AND ($org_type IS NULL OR o.activity_type = $org_type)
  AND ($cluster IS NULL OR p.topics CONTAINS $cluster)
  AND ($role IS NULL OR r.role = $role)

// Aggregate
WITH o,
     count(DISTINCT p) as project_count,
     sum(CASE WHEN r.role = 'coordinator' THEN 1 ELSE 0 END) as coord_count,
     sum(r.ec_contribution) as total_funding,
     collect(DISTINCT {
         acronym: p.acronym,
         title: p.title,
         role: r.role,
         funding: r.ec_contribution,
         start_date: p.start_date
     }) as projects

WHERE project_count >= $min_projects

RETURN
    o.name as name,
    o.short_name as short_name,
    o.country as country,
    o.city as city,
    o.activity_type as type,
    project_count,
    coord_count,
    total_funding,
    projects[..5] as recent_projects
ORDER BY project_count DESC, coord_count DESC, total_funding DESC
LIMIT $limit
```

### PostgreSQL Query: Get Organization Details

```sql
SELECT
    o.id,
    o.name,
    o.short_name,
    o.country,
    o.city,
    o.activity_type,
    COUNT(DISTINCT po.project_id) as project_count,
    SUM(po.ec_contribution) as total_funding,
    SUM(CASE WHEN po.role = 'coordinator' THEN 1 ELSE 0 END) as coord_count
FROM organizations o
JOIN project_organizations po ON o.id = po.organization_id
JOIN projects p ON po.project_id = p.id
WHERE p.objective ILIKE '%' || $keywords || '%'
  AND ($country IS NULL OR o.country = $country)
  AND ($org_type IS NULL OR o.activity_type = $org_type)
GROUP BY o.id
HAVING COUNT(DISTINCT po.project_id) >= $min_projects
ORDER BY project_count DESC, coord_count DESC
LIMIT $limit;
```

---

## Implementation Steps

### Step 1: Create the Tool Function

**File:** `app/services/tools/partner_discovery.py`

```python
from typing import Optional, Dict, Any, List
from app.services.graph_service import GraphSearchService
from app.data.cordis_repository import CordisProjectRepository
import logging

logger = logging.getLogger(__name__)

class PartnerDiscoveryTool:
    def __init__(self):
        self.graph_service = GraphSearchService()
        self.project_repo = CordisProjectRepository()

    async def find_partners(
        self,
        topic_keywords: str,
        country: Optional[str] = None,
        organization_type: Optional[str] = None,
        cluster: Optional[str] = None,
        min_projects: int = 2,
        role_filter: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Find experienced partners for consortium building."""

        # Normalize country code
        country = self._normalize_country(country)

        # Search in Neo4j first (richer relationships)
        neo4j_results = await self._search_neo4j(
            topic_keywords, country, organization_type,
            cluster, min_projects, role_filter, limit
        )

        # Enrich with PostgreSQL data if needed
        enriched_results = await self._enrich_organization_data(neo4j_results)

        # Calculate collaboration scores
        scored_results = self._calculate_scores(enriched_results, topic_keywords)

        # Generate insights
        insights = self._generate_insights(scored_results, topic_keywords)

        return {
            "query_params": {
                "topic_keywords": topic_keywords,
                "country": country,
                "organization_type": organization_type,
                "cluster": cluster
            },
            "total_found": len(scored_results),
            "experienced_partners": scored_results[:limit],
            "aggregated_insights": insights,
            "search_tips": self._generate_search_tips(topic_keywords, scored_results)
        }

    def _normalize_country(self, country: Optional[str]) -> Optional[str]:
        """Convert country names/codes to standard format."""
        if not country:
            return None
        country_map = {
            "DE": "Germany", "FR": "France", "IT": "Italy",
            "ES": "Spain", "NL": "Netherlands", "BE": "Belgium",
            # ... full mapping
        }
        return country_map.get(country.upper(), country)

    def _calculate_scores(
        self,
        results: List[Dict],
        keywords: str
    ) -> List[Dict]:
        """Calculate collaboration/expertise scores for ranking."""
        for org in results:
            score = 0.0
            # Project count weight
            score += min(org.get("relevant_projects", 0) / 10, 0.3)
            # Coordinator experience weight
            score += min(org.get("as_coordinator", 0) / 5, 0.3)
            # Funding weight (normalized)
            score += min(org.get("total_funding", 0) / 10000000, 0.2)
            # Recency weight
            # ... calculate based on recent project dates
            org["collaboration_score"] = round(score, 2)
        return sorted(results, key=lambda x: x["collaboration_score"], reverse=True)
```

### Step 2: Add Country/Organization Type Mappings

```python
COUNTRY_CODES = {
    "Germany": "DE", "France": "FR", "Italy": "IT", "Spain": "ES",
    "Netherlands": "NL", "Belgium": "BE", "Austria": "AT", "Sweden": "SE",
    # ... complete list
}

ORG_TYPE_MAP = {
    "university": "HES",
    "research": "REC",
    "company": "PRC",
    "sme": "SME",
    "public": "PUB"
}
```

### Step 3: Register in Tool Registry

### Step 4: Add to ToolAwareAgent

```python
{
    "name": "find_experienced_partners",
    "description": "Find organizations with proven track records in specific Horizon Europe topics. Use when users want to find potential consortium partners, identify experienced coordinators, or discover organizations working in a specific research area.",
    "parameters": {
        "topic_keywords": "Required: Keywords describing the research area",
        "country": "Optional: Country name or code",
        "organization_type": "Optional: HES, REC, PRC, SME",
        "cluster": "Optional: Cluster code (CL4, CL5, etc.)",
        "min_projects": "Minimum projects to be considered (default: 2)",
        "role_filter": "Filter by role: coordinator, participant, or both"
    }
}
```

---

## Edge Cases to Handle

1. **Very specific keywords**: May return few results, suggest broadening
2. **Ambiguous country names**: Handle "UK" vs "United Kingdom", associated countries
3. **Organization name variations**: "Fraunhofer" vs "Fraunhofer-Gesellschaft"
4. **New topics**: May have few experienced partners, note this limitation
5. **Defunct organizations**: Filter or flag organizations that may no longer exist

---

## Success Criteria

- [ ] Returns relevant organizations for given keywords
- [ ] Track record data is accurate (verifiable in CORDIS)
- [ ] Collaboration scores provide meaningful ranking
- [ ] Country/type filters work correctly
- [ ] Sample projects shown for each organization
- [ ] Performance: <4s response time

---

## Testing Questions

1. "Find experienced partners for quantum computing in Germany"
2. "Which SMEs have worked on hydrogen fuel cell projects?"
3. "Find coordinators for AI in healthcare projects"
4. "What universities in France have renewable energy experience?"
5. "Find partners for a Cluster 5 climate adaptation project"
