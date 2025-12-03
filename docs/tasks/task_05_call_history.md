# Task 5: Call History Analysis Tool

## Overview

**Tool Name:** `analyze_call_history`
**Priority:** Medium (valuable but more complex)
**Data Sources:** PostgreSQL (funding_calls, projects), Neo4j (topic relationships)
**Estimated Complexity:** Medium-High

---

## Purpose

Analyze **historical funding patterns** for specific topic areas, showing what got funded, when, and under which calls. Helps users understand the funding landscape and identify trends.

### User Questions It Answers
- "What topics got funded under HORIZON-CL4 in 2023?"
- "Which clusters fund the most AI projects?"
- "What are the funding trends in Cluster 5?"
- "How often do hydrogen calls appear?"
- "What's the funding history for digital health topics?"

---

## Function Signature

```python
def analyze_call_history(
    topic_pattern: Optional[str] = None,  # e.g., "HORIZON-CL4-2023", "hydrogen"
    cluster: Optional[str] = None,        # e.g., "CL4", "CL5", "CL6"
    keywords: Optional[str] = None,       # Keywords in call titles/descriptions
    year_from: Optional[int] = None,      # Starting year
    year_to: Optional[int] = None,        # Ending year
    action_types: Optional[List[str]] = None,  # Filter by RIA, IA, CSA
    include_projects: bool = True         # Include funded project examples
) -> Dict[str, Any]:
    """
    Analyze historical funding patterns for specific topic areas.

    Returns:
    - Call frequency and timing
    - Funding amounts per call
    - Project success patterns
    - Topic evolution over time
    """
```

---

## Expected Output

```json
{
    "query_params": {
        "topic_pattern": "HORIZON-CL4",
        "keywords": "artificial intelligence",
        "year_range": "2021-2024"
    },
    "calls_analyzed": 47,
    "total_funding_allocated": 892000000,
    "projects_funded": 312,
    "timeline": {
        "2021": {
            "calls": 8,
            "total_budget": 180000000,
            "projects_funded": 62,
            "key_topics": [
                {
                    "topic_code": "HORIZON-CL4-2021-HUMAN-01-01",
                    "title": "AI for human-centric solutions",
                    "budget": 45000000,
                    "projects": 15
                }
            ]
        },
        "2022": {
            "calls": 12,
            "total_budget": 220000000,
            "projects_funded": 78,
            "key_topics": [
                // ... topics
            ]
        },
        "2023": {
            "calls": 15,
            "total_budget": 280000000,
            "projects_funded": 98,
            "key_topics": [
                // ... topics
            ]
        },
        "2024": {
            "calls": 12,
            "total_budget": 212000000,
            "projects_funded": 74,
            "key_topics": [
                // ... topics
            ]
        }
    },
    "funding_by_action_type": {
        "RIA": {
            "calls": 28,
            "total_budget": 520000000,
            "avg_budget_per_call": 18571428,
            "projects": 185
        },
        "IA": {
            "calls": 15,
            "total_budget": 312000000,
            "avg_budget_per_call": 20800000,
            "projects": 98
        },
        "CSA": {
            "calls": 4,
            "total_budget": 60000000,
            "avg_budget_per_call": 15000000,
            "projects": 29
        }
    },
    "top_funded_topics": [
        {
            "topic_code": "HORIZON-CL4-2023-DATA-01-01",
            "title": "AI, Data and Robotics for the Green Deal",
            "total_budget": 75000000,
            "projects": 18,
            "avg_project_budget": 4166666
        },
        {
            "topic_code": "HORIZON-CL4-2022-HUMAN-01-02",
            "title": "Trustworthy AI",
            "total_budget": 50000000,
            "projects": 12,
            "avg_project_budget": 4166666
        }
    ],
    "trends": {
        "funding_trend": "increasing",
        "year_over_year_growth": 15.2,
        "emerging_themes": [
            "Generative AI and large language models",
            "AI for sustainability",
            "Edge AI and embedded systems"
        ],
        "declining_themes": [
            "Basic machine learning research (now expected as baseline)"
        ]
    },
    "sample_funded_projects": [
        {
            "acronym": "ELSA-AI",
            "title": "European Lighthouse on Safe and Secure AI",
            "topic": "HORIZON-CL4-2021-HUMAN-01-03",
            "budget": 12000000,
            "partners": 25,
            "coordinator": "Fraunhofer",
            "start": "2022-09"
        }
    ],
    "upcoming_predictions": {
        "note": "Based on work programme patterns, not guaranteed",
        "likely_topics_2025": [
            "AI Act compliance tools",
            "Sustainable AI / Green AI",
            "AI for critical infrastructure"
        ]
    },
    "recommendations": [
        "AI topics appear consistently in CL4 annual work programmes",
        "Budget per project has increased ~10% year-over-year",
        "Consider cross-cluster proposals (AI in Health, AI in Climate)",
        "Two-stage calls more common for large-budget topics"
    ]
}
```

---

## Data Sources & Queries

### PostgreSQL Query: Call History by Topic Pattern

```sql
SELECT
    fc.topic_code,
    fc.title,
    fc.call_identifier,
    fc.budget_total,
    fc.deadline_date,
    fc.action_type,
    EXTRACT(YEAR FROM fc.deadline_date) as call_year,
    COUNT(p.id) as projects_funded,
    SUM(p.ec_max_contribution) as total_project_funding
FROM funding_calls fc
LEFT JOIN projects p ON p.topics LIKE '%' || fc.topic_code || '%'
WHERE ($topic_pattern IS NULL OR fc.topic_code LIKE '%' || $topic_pattern || '%')
  AND ($cluster IS NULL OR fc.topic_code LIKE '%' || $cluster || '%')
  AND ($keywords IS NULL OR fc.title ILIKE '%' || $keywords || '%'
       OR fc.description ILIKE '%' || $keywords || '%')
  AND ($year_from IS NULL OR EXTRACT(YEAR FROM fc.deadline_date) >= $year_from)
  AND ($year_to IS NULL OR EXTRACT(YEAR FROM fc.deadline_date) <= $year_to)
GROUP BY fc.topic_code, fc.title, fc.call_identifier, fc.budget_total,
         fc.deadline_date, fc.action_type
ORDER BY fc.deadline_date DESC;
```

### PostgreSQL Query: Projects per Topic

```sql
SELECT
    p.topics,
    COUNT(*) as project_count,
    SUM(p.ec_max_contribution) as total_funding,
    AVG(p.ec_max_contribution) as avg_funding,
    MIN(p.start_date) as earliest_start,
    MAX(p.start_date) as latest_start
FROM projects p
WHERE p.topics LIKE '%' || $topic_pattern || '%'
  AND p.framework_programme = 'HORIZON'
GROUP BY p.topics
ORDER BY project_count DESC;
```

### Neo4j Query: Topic Relationships and Trends

```cypher
MATCH (t:Topic)<-[:ADDRESSES]-(p:Project)
WHERE t.code CONTAINS $cluster
WITH t, count(p) as project_count,
     collect(p.start_date) as start_dates
RETURN
    t.code as topic_code,
    t.title as topic_title,
    project_count,
    min(start_dates) as first_funded,
    max(start_dates) as last_funded
ORDER BY project_count DESC
LIMIT 20
```

---

## Implementation Steps

### Step 1: Create the Tool Function

**File:** `app/services/tools/call_history.py`

```python
from typing import Optional, Dict, Any, List
from app.services.local_call_search_service import LocalCallSearchService
from app.data.cordis_repository import CordisProjectRepository
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CallHistoryTool:
    def __init__(self):
        self.call_service = LocalCallSearchService()
        self.project_repo = CordisProjectRepository()

    async def analyze_history(
        self,
        topic_pattern: Optional[str] = None,
        cluster: Optional[str] = None,
        keywords: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        action_types: Optional[List[str]] = None,
        include_projects: bool = True
    ) -> Dict[str, Any]:
        """Analyze historical funding patterns."""

        # Get call history
        calls = await self._get_calls_history(
            topic_pattern, cluster, keywords,
            year_from, year_to, action_types
        )

        # Get funded projects
        projects = []
        if include_projects:
            projects = await self._get_funded_projects(
                topic_pattern, cluster, keywords,
                year_from, year_to
            )

        # Build timeline
        timeline = self._build_timeline(calls, projects)

        # Analyze by action type
        by_action_type = self._analyze_by_action_type(calls, projects)

        # Identify top topics
        top_topics = self._identify_top_topics(calls, projects)

        # Detect trends
        trends = self._detect_trends(timeline, calls, projects)

        # Generate recommendations
        recommendations = self._generate_recommendations(trends, top_topics)

        return {
            "query_params": {
                "topic_pattern": topic_pattern,
                "cluster": cluster,
                "keywords": keywords,
                "year_range": f"{year_from or 'start'}-{year_to or 'now'}"
            },
            "calls_analyzed": len(calls),
            "total_funding_allocated": sum(c.get('budget_total', 0) for c in calls),
            "projects_funded": len(projects),
            "timeline": timeline,
            "funding_by_action_type": by_action_type,
            "top_funded_topics": top_topics,
            "trends": trends,
            "sample_funded_projects": projects[:5] if projects else [],
            "recommendations": recommendations
        }

    def _build_timeline(
        self,
        calls: List[Dict],
        projects: List[Dict]
    ) -> Dict[str, Any]:
        """Build year-by-year timeline."""
        timeline = {}
        for call in calls:
            year = call.get('year', datetime.now().year)
            if year not in timeline:
                timeline[year] = {
                    "calls": 0,
                    "total_budget": 0,
                    "projects_funded": 0,
                    "key_topics": []
                }
            timeline[year]["calls"] += 1
            timeline[year]["total_budget"] += call.get('budget_total', 0)
            # ... add key topics
        return dict(sorted(timeline.items()))

    def _detect_trends(
        self,
        timeline: Dict,
        calls: List[Dict],
        projects: List[Dict]
    ) -> Dict[str, Any]:
        """Detect funding trends over time."""
        years = sorted(timeline.keys())
        if len(years) < 2:
            return {"funding_trend": "insufficient_data"}

        # Calculate year-over-year growth
        budgets = [timeline[y]["total_budget"] for y in years]
        growth_rates = []
        for i in range(1, len(budgets)):
            if budgets[i-1] > 0:
                growth = (budgets[i] - budgets[i-1]) / budgets[i-1] * 100
                growth_rates.append(growth)

        avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0

        return {
            "funding_trend": "increasing" if avg_growth > 5 else "stable" if avg_growth > -5 else "decreasing",
            "year_over_year_growth": round(avg_growth, 1),
            "emerging_themes": self._identify_emerging_themes(calls),
            "declining_themes": self._identify_declining_themes(calls)
        }
```

### Step 2: Add Pattern Recognition

```python
def _identify_emerging_themes(self, calls: List[Dict]) -> List[str]:
    """Identify emerging themes from recent calls."""
    # Look at title/description keywords in recent vs older calls
    # Use simple frequency analysis
    pass

def _identify_declining_themes(self, calls: List[Dict]) -> List[str]:
    """Identify themes that appear less frequently over time."""
    pass
```

### Step 3: Register in Tool Registry

### Step 4: Add to ToolAwareAgent

```python
{
    "name": "analyze_call_history",
    "description": "Analyze historical funding patterns for specific topic areas in Horizon Europe. Use when users ask about funding trends, what got funded in the past, topic frequency, or funding evolution over time.",
    "parameters": {
        "topic_pattern": "Optional: Topic code pattern (e.g., HORIZON-CL4-2023)",
        "cluster": "Optional: Cluster code (CL4, CL5, etc.)",
        "keywords": "Optional: Keywords to search in call titles",
        "year_from": "Optional: Starting year",
        "year_to": "Optional: Ending year",
        "include_projects": "Include funded project examples (default: true)"
    }
}
```

---

## Limitations & Caveats

1. **No rejection data**: We only know what got funded, not what was rejected
2. **Call timing**: Deadline dates don't always reflect evaluation timing
3. **Budget vs actual**: Allocated budgets may differ from actual spend
4. **New topics**: Recent topics may have few data points
5. **Work programme changes**: Future calls may differ from historical patterns

---

## Edge Cases to Handle

1. **No matching calls**: Suggest alternative search terms
2. **Very specific pattern**: May return few results
3. **Future year queries**: Note that we only have historical data
4. **Budget inconsistencies**: Some calls may have missing budget data

---

## Success Criteria

- [ ] Timeline accurately reflects call chronology
- [ ] Funding totals match actual CORDIS/EU data
- [ ] Trends are based on data, not speculation
- [ ] Sample projects are relevant to the topic
- [ ] Recommendations are actionable
- [ ] Performance: <5s response time

---

## Testing Questions

1. "What AI topics got funded under Cluster 4 in 2023?"
2. "Show me the funding history for hydrogen projects"
3. "Which clusters have increased AI funding over time?"
4. "What were the biggest calls in Health in 2022?"
5. "How has quantum computing funding evolved in Horizon Europe?"
