# Task 4: Similar Funded Projects Tool

## Overview

**Tool Name:** `get_similar_funded_projects`
**Priority:** High (uses existing embeddings infrastructure)
**Data Sources:** PostgreSQL pgvector (project embeddings), Neo4j (relationships)
**Estimated Complexity:** Low-Medium

---

## Purpose

Help users **find funded projects similar to their proposal idea** using semantic similarity. This provides real examples of what got funded, helping users understand the landscape and refine their ideas.

### User Questions It Answers
- "Show me funded projects similar to my AI in healthcare idea"
- "What projects were funded about sustainable agriculture?"
- "Find examples of successful quantum computing projects"
- "Are there funded projects about using blockchain for supply chains?"
- "What Horizon Europe projects address ocean plastic pollution?"

---

## Function Signature

```python
def get_similar_funded_projects(
    description: str,                     # Required: User's project idea/description
    cluster: Optional[str] = None,        # Filter by cluster (CL4, CL5, etc.)
    action_type: Optional[str] = None,    # Filter by RIA, IA, CSA
    min_budget: Optional[int] = None,     # Minimum EU contribution
    max_budget: Optional[int] = None,     # Maximum EU contribution
    year_from: Optional[int] = None,      # Projects starting from year
    limit: int = 10,                      # Number of results
    similarity_threshold: float = 0.5    # Minimum similarity score
) -> Dict[str, Any]:
    """
    Find funded Horizon Europe projects semantically similar to a description.

    Uses 768-dimensional embeddings (Google text-embedding-004) for
    semantic similarity matching against 13,850+ project objectives.
    """
```

---

## Expected Output

```json
{
    "query_description": "AI-powered diagnostic tools for early cancer detection using medical imaging",
    "filters_applied": {
        "cluster": "CL1",
        "action_type": "RIA"
    },
    "projects_searched": 13865,
    "matches_found": 8,
    "similar_projects": [
        {
            "rank": 1,
            "similarity_score": 0.89,
            "acronym": "AI-CANCER-DX",
            "title": "Artificial Intelligence for Cancer Diagnostics",
            "cordis_id": "101057892",
            "cordis_url": "https://cordis.europa.eu/project/id/101057892",
            "objective_summary": "This project develops AI algorithms for analyzing medical imaging data to enable early detection of various cancer types. Using deep learning on CT, MRI, and pathology images...",
            "total_cost": 6500000,
            "eu_contribution": 6500000,
            "start_date": "2023-01-01",
            "end_date": "2026-12-31",
            "status": "active",
            "action_type": "RIA",
            "topics": ["HORIZON-HLTH-2022-DISEASE-06-02"],
            "consortium": {
                "size": 12,
                "coordinator": {
                    "name": "Karolinska Institutet",
                    "country": "Sweden"
                },
                "countries": ["Sweden", "Germany", "Netherlands", "France", "Italy", "Spain", "Belgium", "UK"],
                "composition": {
                    "HES": 5,
                    "REC": 3,
                    "PRC": 2,
                    "SME": 2
                }
            },
            "keywords": ["artificial intelligence", "cancer", "medical imaging", "diagnostics", "deep learning"],
            "relevance_explanation": "Direct match: AI-based cancer diagnosis using medical imaging"
        },
        {
            "rank": 2,
            "similarity_score": 0.82,
            "acronym": "MEDAI-SCREEN",
            "title": "Medical AI for Cancer Screening Programs",
            // ... similar structure
        }
    ],
    "topic_analysis": {
        "most_common_topics": [
            {"topic": "HORIZON-HLTH-2022-DISEASE-06", "count": 3},
            {"topic": "HORIZON-HLTH-2023-CARE-04", "count": 2}
        ],
        "funding_range": {
            "min": 3200000,
            "max": 12000000,
            "average": 6100000
        },
        "typical_duration_months": 48
    },
    "insights": [
        "Strong funding trend in AI-based medical diagnostics",
        "Most projects combine clinical validation with AI development",
        "Typical consortium includes hospitals, AI companies, and research institutions",
        "Consider including patient advocacy organizations (common in health projects)"
    ],
    "related_calls_suggestion": "Look for upcoming calls under HORIZON-HLTH-*-DISEASE-* or HORIZON-HLTH-*-TOOL-*"
}
```

---

## Data Sources & Queries

### PostgreSQL pgvector Query: Semantic Similarity

```sql
-- Get embedding for user query first (via embedding API)
-- Then find similar projects

SELECT
    p.id,
    p.acronym,
    p.title,
    p.objective,
    p.total_cost,
    p.ec_max_contribution,
    p.start_date,
    p.end_date,
    p.status,
    p.funding_scheme,
    p.topics,
    1 - (pe.embedding <=> $query_embedding) as similarity_score
FROM projects p
JOIN project_embeddings pe ON p.id = pe.project_id
WHERE p.framework_programme = 'HORIZON'
  AND ($cluster IS NULL OR p.topics LIKE '%' || $cluster || '%')
  AND ($action_type IS NULL OR p.funding_scheme LIKE '%' || $action_type || '%')
  AND ($min_budget IS NULL OR p.ec_max_contribution >= $min_budget)
  AND ($max_budget IS NULL OR p.ec_max_contribution <= $max_budget)
  AND ($year_from IS NULL OR EXTRACT(YEAR FROM p.start_date) >= $year_from)
  AND 1 - (pe.embedding <=> $query_embedding) >= $similarity_threshold
ORDER BY pe.embedding <=> $query_embedding
LIMIT $limit;
```

### Neo4j Query: Enrich with Consortium Data

```cypher
MATCH (p:Project {cordis_id: $project_id})
OPTIONAL MATCH (o:Organisation)-[r:PARTICIPATES_IN]->(p)
WITH p, collect({
    name: o.name,
    country: o.country,
    type: o.activity_type,
    role: r.role,
    funding: r.ec_contribution
}) as partners
RETURN
    p.acronym as acronym,
    size(partners) as consortium_size,
    [x IN partners WHERE x.role = 'coordinator'][0] as coordinator,
    [x IN partners | x.country] as countries,
    partners
```

---

## Implementation Steps

### Step 1: Create the Tool Function

**File:** `app/services/tools/similar_projects.py`

```python
from typing import Optional, Dict, Any, List
from app.services.vector_search_service import VectorSearchService
from app.services.graph_service import GraphSearchService
from app.data.cordis_repository import CordisProjectRepository
from app.core.embeddings import get_embedding
import logging

logger = logging.getLogger(__name__)

class SimilarProjectsTool:
    def __init__(self):
        self.vector_service = VectorSearchService()
        self.graph_service = GraphSearchService()
        self.project_repo = CordisProjectRepository()

    async def find_similar(
        self,
        description: str,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        min_budget: Optional[int] = None,
        max_budget: Optional[int] = None,
        year_from: Optional[int] = None,
        limit: int = 10,
        similarity_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """Find funded projects similar to the given description."""

        # Generate embedding for user's description
        query_embedding = await get_embedding(description)

        # Search similar projects via pgvector
        raw_results = await self.project_repo.search_by_embedding(
            embedding=query_embedding,
            cluster=cluster,
            action_type=action_type,
            min_budget=min_budget,
            max_budget=max_budget,
            year_from=year_from,
            limit=limit * 2,  # Get more, filter by threshold
            threshold=similarity_threshold
        )

        # Enrich with consortium data from Neo4j
        enriched_results = []
        for project in raw_results:
            if project['similarity_score'] >= similarity_threshold:
                consortium = await self._get_consortium_data(project['cordis_id'])
                project['consortium'] = consortium
                project['keywords'] = self._extract_keywords(project['objective'])
                project['relevance_explanation'] = self._explain_relevance(
                    description, project
                )
                enriched_results.append(project)

        # Generate topic analysis
        topic_analysis = self._analyze_topics(enriched_results)

        # Generate insights
        insights = self._generate_insights(enriched_results, description)

        return {
            "query_description": description[:200] + "..." if len(description) > 200 else description,
            "filters_applied": {
                "cluster": cluster,
                "action_type": action_type,
                "budget_range": f"€{min_budget or 0:,} - €{max_budget or 'unlimited':,}" if min_budget or max_budget else None
            },
            "projects_searched": await self.project_repo.count_projects(),
            "matches_found": len(enriched_results),
            "similar_projects": enriched_results[:limit],
            "topic_analysis": topic_analysis,
            "insights": insights
        }

    async def _get_consortium_data(self, cordis_id: str) -> Dict[str, Any]:
        """Get consortium composition from Neo4j."""
        # Query Neo4j for partners
        pass

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key terms from project objective."""
        # Simple keyword extraction
        pass

    def _explain_relevance(self, query: str, project: Dict) -> str:
        """Generate human-readable relevance explanation."""
        # LLM or rule-based explanation
        pass

    def _analyze_topics(self, projects: List[Dict]) -> Dict[str, Any]:
        """Analyze funding topics across matched projects."""
        pass

    def _generate_insights(
        self,
        projects: List[Dict],
        query: str
    ) -> List[str]:
        """Generate actionable insights from results."""
        insights = []

        if not projects:
            return ["No similar projects found. This could be a novel research area or try broader keywords."]

        # Budget insight
        budgets = [p['eu_contribution'] for p in projects if p.get('eu_contribution')]
        if budgets:
            avg_budget = sum(budgets) / len(budgets)
            insights.append(f"Average budget for similar projects: €{avg_budget:,.0f}")

        # Consortium size insight
        sizes = [p['consortium']['size'] for p in projects if p.get('consortium')]
        if sizes:
            avg_size = sum(sizes) / len(sizes)
            insights.append(f"Typical consortium size: {avg_size:.0f} partners")

        # Add more insights...
        return insights
```

### Step 2: Leverage Existing Embedding Infrastructure

The system already has project embeddings. Ensure we're using:
- `app/data/cordis_repository.py` for project data
- `app/services/vector_search_service.py` for vector operations

### Step 3: Register in Tool Registry

### Step 4: Add to ToolAwareAgent

```python
{
    "name": "get_similar_funded_projects",
    "description": "Find funded Horizon Europe projects semantically similar to a project idea or description. Use when users want to see examples of funded projects in their area, understand what got funded, or benchmark their idea against existing projects.",
    "parameters": {
        "description": "Required: Description of the project idea",
        "cluster": "Optional: Filter by cluster (CL1-CL6, EIC, etc.)",
        "action_type": "Optional: Filter by RIA, IA, CSA",
        "min_budget": "Optional: Minimum EU contribution",
        "max_budget": "Optional: Maximum EU contribution",
        "limit": "Number of results (default: 10)"
    }
}
```

---

## Edge Cases to Handle

1. **Very short descriptions**: Request more detail for better matching
2. **No matches found**: Suggest broadening search, different keywords
3. **Very novel topics**: May have few matches, note this honestly
4. **Overly broad descriptions**: May match everything, ask for specificity
5. **Non-English descriptions**: May need translation or note limitation

---

## Success Criteria

- [ ] Semantic similarity matches are relevant (human verification)
- [ ] Similarity scores correlate with actual relevance
- [ ] Consortium data is enriched correctly
- [ ] Budget and topic analysis are accurate
- [ ] Insights are actionable and data-driven
- [ ] Performance: <5s response time (embedding generation is slow)

---

## Testing Questions

1. "Find projects similar to: AI-powered crop monitoring using satellite imagery for precision agriculture"
2. "Show me funded projects about using digital twins for manufacturing"
3. "What Horizon Europe projects address mental health in adolescents?"
4. "Find similar projects to blockchain for food traceability"
5. "Projects like autonomous robots for warehouse logistics"
