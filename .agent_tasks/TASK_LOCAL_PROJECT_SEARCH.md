# Task: Make Project Search 100% Local-First

## Priority: HIGH
## Status: 🔲 Not Started
## Created: December 3, 2024

---

## Problem Statement

The `search_cordis_projects` tool currently uses `CordisRAG` which:
1. **Relies on external CORDIS API** - slow, unreliable, rate-limited
2. **Doesn't leverage local data** - we already have 90,000+ projects in PostgreSQL & Neo4j
3. **No semantic search** - just keyword matching via API
4. **No relationship awareness** - can't find "projects similar to X" or "projects from organizations that worked with Y"

**Evidence of problem:**
```python
# Current implementation in tool_orchestrator.py line 200
rag_service = CordisRAG()
results = rag_service.get_ai_response_with_routing(...)
# This goes to CORDIS API which is slow/unreliable
```

---

## Current Data Assets (Already Available!)

### 1. PostgreSQL Tables (cordis_processed schema)
```
cordis_processed.projects_enriched    -- Full project data
cordis_processed.organizations_enriched -- Participants & coordinators  
cordis_processed.results_enriched     -- Project deliverables
```

**Fields available:**
- `id`, `rcn`, `title`, `acronym`, `objective` (searchable text)
- `startDate`, `endDate`, `status` (temporal filters)
- `totalCost`, `ecMaxContribution` (budget filters)
- `frameworkProgramme`, `fundingScheme`, `topics` (structured filters)
- Organization details: names, countries, SME status, NUTS codes

### 2. Neo4j Graph Database
```cypher
(Project)-[:FUNDED_UNDER]->(Topic)
(Project)-[:TARGETS]->(Cluster)
(Organization)-[:PARTICIPATES_IN]->(Project)
(Organization)-[:COORDINATES]->(Project)
```

**Graph queries enable:**
- Find projects in same topic/cluster
- Find collaborating organizations
- Traverse funding relationships
- Statistical aggregations

### 3. Existing Repository (Unused!)
**File:** `app/services/data/cordis_repository.py`

```python
class CordisProjectRepository:
    """Already implements local search with:
    - Full-text search (PostgreSQL ts_vector)
    - Structured filters (programme, dates, budget, countries)
    - Organization joins
    """
    
    def search_projects(
        self,
        queries: List[str],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> Tuple[List[CordisProjectDTO], int]:
        # Already implemented! Just not connected to the tool!
```

---

## Perfect Solution Architecture

### Phase 1: Multi-Source Local Search (Core)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     LOCAL PROJECT SEARCH SERVICE                            │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  User Query: "AI projects in healthcare from German universities"          │
│                                                                            │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐       │
│  │  STRUCTURED      │   │  SEMANTIC        │   │  GRAPH           │       │
│  │  SEARCH          │   │  SEARCH          │   │  SEARCH          │       │
│  │                  │   │                  │   │                  │       │
│  │  PostgreSQL      │   │  Vector DB       │   │  Neo4j           │       │
│  │  Full-text +     │   │  Embeddings of   │   │  Relationship    │       │
│  │  Filters         │   │  project titles  │   │  traversal       │       │
│  │                  │   │  & objectives    │   │                  │       │
│  └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘       │
│           │                      │                      │                 │
│           └──────────────────────┴──────────────────────┘                 │
│                                  │                                        │
│                         ┌────────▼────────┐                               │
│                         │  RESULT FUSION  │                               │
│                         │  (RRF + Dedup)  │                               │
│                         └────────┬────────┘                               │
│                                  │                                        │
│                         ┌────────▼────────┐                               │
│                         │  RERANKING      │                               │
│                         │  (Cross-encoder │                               │
│                         │   or LLM)       │                               │
│                         └────────┬────────┘                               │
│                                  │                                        │
│                         ┌────────▼────────┐                               │
│                         │  ENRICHMENT     │                               │
│                         │  (Lazy API call │                               │
│                         │   if needed)    │                               │
│                         └────────┬────────┘                               │
│                                  │                                        │
│                                  ▼                                        │
│                          Final Results                                    │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Phase 2: Project Embeddings (Enhanced Semantic Search)

**Create embeddings table for projects:**
```sql
CREATE TABLE IF NOT EXISTS project_embeddings (
    project_id TEXT PRIMARY KEY REFERENCES cordis_processed.projects_enriched(id),
    title_embedding vector(768),
    objective_embedding vector(768),
    combined_embedding vector(768),  -- title + objective + topics
    created_at TIMESTAMP DEFAULT NOW(),
    model_version TEXT DEFAULT 'text-embedding-004'
);
```

**Benefits:**
- "Find projects similar to [project X]" queries
- Semantic search on objectives ("projects about renewable energy integration")
- Better relevance than keyword matching

---

## Implementation Steps

### Step 1: Create LocalProjectSearchService

**File:** `app/services/local_project_search_service.py`

```python
"""
Local-first project search service.
Combines PostgreSQL full-text, Neo4j graph, and vector semantic search.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from datetime import date
import logging

from .data.cordis_repository import CordisProjectRepository, CordisProjectDTO
from .data_intelligence.graph_service import GraphSearchService
from .vector_service import VectorSearchService

logger = logging.getLogger(__name__)

@dataclass
class ProjectSearchResult:
    """Unified project result from any source."""
    project_id: str
    rcn: str
    title: str
    acronym: Optional[str]
    objective: str
    start_date: str
    end_date: str
    total_cost: float
    ec_contribution: float
    status: str
    programme: str
    funding_scheme: str
    topics: str
    coordinator_name: Optional[str]
    coordinator_country: Optional[str]
    participant_count: int
    country_count: int
    sme_count: int
    participant_countries: List[str]
    relevance_score: float
    data_source: str  # 'postgresql', 'neo4j', 'vector', 'api'
    cordis_url: str

class LocalProjectSearchService:
    """
    Multi-source local project search.
    
    Search strategy:
    1. Parse query for structured filters (countries, dates, budgets)
    2. Run parallel searches: PostgreSQL, Neo4j, (optional) Vector
    3. Fuse results using Reciprocal Rank Fusion
    4. Deduplicate by project_id
    5. Rerank if needed
    6. Enrich with API only for missing fields (lazy load + cache)
    """
    
    def __init__(self):
        self.postgres_repo = CordisProjectRepository()
        self.graph_service = GraphSearchService()
        self.vector_service = VectorSearchService()  # If embeddings exist
        self._api_cache = {}  # Cache API enrichments
    
    async def search_projects(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        include_semantic: bool = True,
        include_graph: bool = True
    ) -> Dict[str, Any]:
        """
        Main search entry point.
        
        Args:
            query: Natural language search query
            filters: Optional structured filters:
                - programme: str (e.g., "H2020", "HORIZON")
                - countries: List[str] (e.g., ["DE", "FR"])
                - date_range: Dict with 'start' and/or 'end'
                - budget_range: Dict with 'min' and/or 'max'
                - status: str (e.g., "SIGNED", "CLOSED")
            limit: Max results to return
            include_semantic: Use vector embeddings if available
            include_graph: Include Neo4j relationship-based search
            
        Returns:
            Dict with projects, metadata, and statistics
        """
        start_time = time.time()
        
        # 1. Extract any implicit filters from query
        parsed_filters = self._parse_query_for_filters(query, filters)
        search_terms = self._extract_search_terms(query)
        
        # 2. Run searches in parallel
        results_by_source = await self._parallel_search(
            search_terms=search_terms,
            filters=parsed_filters,
            limit=limit * 2,  # Over-fetch for fusion
            include_semantic=include_semantic,
            include_graph=include_graph
        )
        
        # 3. Fuse results using RRF
        fused_results = self._reciprocal_rank_fusion(results_by_source)
        
        # 4. Deduplicate by project_id
        unique_results = self._deduplicate(fused_results)
        
        # 5. Take top N
        final_results = unique_results[:limit]
        
        # 6. Format for response
        elapsed = time.time() - start_time
        
        return {
            'success': True,
            'query': query,
            'projects': [self._format_project(p) for p in final_results],
            'total_found': len(unique_results),
            'returned': len(final_results),
            'filters_applied': parsed_filters,
            'sources_used': list(results_by_source.keys()),
            'processing_time_ms': int(elapsed * 1000)
        }
    
    async def _parallel_search(
        self,
        search_terms: List[str],
        filters: Dict[str, Any],
        limit: int,
        include_semantic: bool,
        include_graph: bool
    ) -> Dict[str, List[CordisProjectDTO]]:
        """Run searches in parallel across sources."""
        import asyncio
        
        tasks = {}
        
        # PostgreSQL full-text search (always)
        tasks['postgresql'] = self._search_postgres(search_terms, filters, limit)
        
        # Neo4j graph search (if enabled and relevant)
        if include_graph:
            tasks['neo4j'] = self._search_graph(search_terms, filters, limit)
        
        # Vector semantic search (if embeddings exist)
        if include_semantic and self._has_project_embeddings():
            tasks['vector'] = self._search_vector(search_terms, limit)
        
        # Execute in parallel
        results = {}
        for source, task in tasks.items():
            try:
                results[source] = await task
            except Exception as e:
                logger.warning(f"Search source {source} failed: {e}")
                results[source] = []
        
        return results
    
    def _reciprocal_rank_fusion(
        self,
        results_by_source: Dict[str, List],
        k: int = 60
    ) -> List[CordisProjectDTO]:
        """
        Combine rankings using RRF.
        RRF score = Σ 1/(k + rank) for each list the item appears in.
        """
        scores = {}
        projects_map = {}
        
        for source, projects in results_by_source.items():
            for rank, project in enumerate(projects, 1):
                pid = project.id
                if pid not in scores:
                    scores[pid] = 0
                    projects_map[pid] = project
                scores[pid] += 1 / (k + rank)
        
        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [projects_map[pid] for pid in sorted_ids]
    
    def _format_project(self, project: CordisProjectDTO) -> Dict[str, Any]:
        """Format project for API response."""
        return {
            'id': project.id,
            'rcn': project.rcn,
            'title': project.title,
            'acronym': project.acronym,
            'objective': project.objective[:500] + '...' if len(project.objective) > 500 else project.objective,
            'start_date': project.start_date,
            'end_date': project.end_date,
            'status': project.status,
            'total_cost': project.total_cost,
            'ec_contribution': project.ec_max_contribution,
            'programme': project.framework_programme,
            'funding_scheme': project.funding_scheme,
            'topics': project.topics,
            'coordinator': {
                'name': project.coordinator_name,
                'country': project.coordinator_country
            },
            'consortium': {
                'participant_count': project.participant_count,
                'country_count': project.country_count,
                'sme_count': project.sme_count,
                'countries': project.participant_countries
            },
            'relevance_score': project.relevance_score,
            'source': project.data_source,
            'cordis_url': f"https://cordis.europa.eu/project/id/{project.id}"
        }
```

### Step 2: Update Tool Orchestrator

**File:** `app/services/tools/tool_orchestrator.py`

Replace the current `search_cordis_projects` implementation:

```python
@staticmethod
async def search_cordis_projects(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search for research projects using local-first multi-source search.
    
    Sources:
    1. PostgreSQL full-text search (cordis_processed.projects_enriched)
    2. Neo4j graph relationships (project-topic-organization)
    3. Vector embeddings (semantic similarity) - if available
    """
    from ..local_project_search_service import LocalProjectSearchService
    
    # Parameter validation
    schema = {
        'query': {'type': 'string', 'required': True},
        'max_results': {'type': 'integer', 'default': 10, 'min': 1, 'max': 50},
        'programme': {'type': 'string', 'default': None},
        'countries': {'type': 'array', 'default': None},
        'status': {'type': 'string', 'default': None},
        'include_semantic': {'type': 'boolean', 'default': True},
        'include_graph': {'type': 'boolean', 'default': True}
    }
    
    try:
        validated = ToolValidator.validate_parameters(params, schema)
        
        # Build filters from parameters
        filters = {}
        if validated.get('programme'):
            filters['programme'] = validated['programme']
        if validated.get('countries'):
            filters['countries'] = validated['countries']
        if validated.get('status'):
            filters['status'] = validated['status']
        
        # Execute local-first search
        service = LocalProjectSearchService()
        results = await service.search_projects(
            query=validated['query'],
            filters=filters if filters else None,
            limit=validated['max_results'],
            include_semantic=validated['include_semantic'],
            include_graph=validated['include_graph']
        )
        
        return {
            'success': True,
            'tool_name': 'search_cordis_projects',
            'query': validated['query'],
            'projects': results['projects'],
            'total_found': results['total_found'],
            'sources_used': results['sources_used'],
            'processing_time_ms': results['processing_time_ms']
        }
        
    except Exception as e:
        logger.error(f"Project search failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'tool_name': 'search_cordis_projects',
            'query': params.get('query', '')
        }
```

### Step 3: Create Project Embeddings (Optional but Recommended)

**Script:** `scripts/create_project_embeddings.py`

```python
"""
Generate vector embeddings for project semantic search.
Uses the same embedding model as document chunks for consistency.
"""

import os
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai
from supabase import create_client

load_dotenv()

# Initialize clients
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

async def create_embedding(text: str) -> list:
    """Generate embedding using Gemini."""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

async def process_projects():
    """Generate embeddings for all projects."""
    
    # Get projects without embeddings
    response = supabase.rpc(
        'get_projects_needing_embeddings',
        {'batch_size': 100}
    ).execute()
    
    for project in response.data:
        # Combine title + objective for richer embedding
        text = f"{project['title']}. {project['objective'][:2000]}"
        
        embedding = await create_embedding(text)
        
        # Store embedding
        supabase.table('project_embeddings').upsert({
            'project_id': project['id'],
            'combined_embedding': embedding,
            'model_version': 'text-embedding-004'
        }).execute()
        
        print(f"✅ Embedded project {project['id']}")

if __name__ == '__main__':
    asyncio.run(process_projects())
```

### Step 4: Add Graph-Based Project Discovery

**File:** `app/services/data_intelligence/graph_service.py`

Add new methods:

```python
def find_similar_projects(
    self,
    project_id: str,
    similarity_type: str = "topic",  # "topic", "consortium", "cluster"
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Find projects similar to a given project.
    
    Similarity types:
    - topic: Same topic/call
    - consortium: Shared organizations
    - cluster: Same cluster area
    """
    
    if similarity_type == "topic":
        query = """
        MATCH (p1:Project {id: $project_id})-[:FUNDED_UNDER]->(t:Topic)<-[:FUNDED_UNDER]-(p2:Project)
        WHERE p1 <> p2
        RETURN p2.id as id, p2.title as title, p2.acronym as acronym,
               t.code as shared_topic, p2.ecMaxContribution as budget
        LIMIT $limit
        """
    elif similarity_type == "consortium":
        query = """
        MATCH (p1:Project {id: $project_id})<-[:PARTICIPATES_IN]-(o:Organization)-[:PARTICIPATES_IN]->(p2:Project)
        WHERE p1 <> p2
        WITH p2, COUNT(DISTINCT o) as shared_orgs
        RETURN p2.id as id, p2.title as title, p2.acronym as acronym,
               shared_orgs, p2.ecMaxContribution as budget
        ORDER BY shared_orgs DESC
        LIMIT $limit
        """
    elif similarity_type == "cluster":
        query = """
        MATCH (p1:Project {id: $project_id})-[:TARGETS]->(c:Cluster)<-[:TARGETS]-(p2:Project)
        WHERE p1 <> p2
        RETURN p2.id as id, p2.title as title, p2.acronym as acronym,
               c.code as shared_cluster, p2.ecMaxContribution as budget
        LIMIT $limit
        """
    
    return self.db.execute_query(query, {'project_id': project_id, 'limit': limit})

def find_projects_by_organization(
    self,
    organization_name: str,
    role: Optional[str] = None,  # "coordinator", "participant", or None for both
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Find all projects an organization participated in."""
    
    role_filter = ""
    if role == "coordinator":
        role_filter = "AND o.role = 'coordinator'"
    elif role == "participant":
        role_filter = "AND o.role = 'participant'"
    
    query = f"""
    MATCH (o:Organization)-[r:PARTICIPATES_IN|COORDINATES]->(p:Project)
    WHERE toLower(o.name) CONTAINS toLower($org_name)
    {role_filter}
    RETURN p.id as id, p.title as title, p.acronym as acronym,
           p.ecMaxContribution as budget, p.status as status,
           o.name as organization, type(r) as role
    ORDER BY p.startDate DESC
    LIMIT $limit
    """
    
    return self.db.execute_query(query, {'org_name': organization_name, 'limit': limit})
```

---

## Testing Checklist

### Unit Tests
- [ ] `LocalProjectSearchService.search_projects()` returns results
- [ ] PostgreSQL full-text search works with complex queries
- [ ] Neo4j graph search finds related projects
- [ ] RRF fusion correctly combines results
- [ ] Deduplication preserves highest-scored version

### Integration Tests
- [ ] Tool orchestrator correctly routes to local service
- [ ] Multi-source search returns unified results
- [ ] Filters (programme, country, date) work correctly
- [ ] Error handling for unavailable sources

### Performance Tests
- [ ] Search completes in < 2 seconds for typical queries
- [ ] Parallel execution provides speedup
- [ ] Large result sets handled efficiently

### End-to-End Tests
- [ ] "Find AI healthcare projects" returns relevant results
- [ ] "Projects coordinated by TU Munich" works
- [ ] "Projects similar to [project ID]" works
- [ ] "H2020 projects in renewable energy from Germany" works

---

## Success Criteria

1. **No API dependency** - Search works without CORDIS API
2. **< 2 second response time** - Fast local queries
3. **Better relevance** - Semantic + structural + keyword
4. **Rich filtering** - By country, programme, date, budget, status
5. **Relationship awareness** - "Projects like X", "Projects from org Y"
6. **Graceful degradation** - Works even if one source fails

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `app/services/local_project_search_service.py` | CREATE | Main search service |
| `app/services/tools/tool_orchestrator.py` | MODIFY | Update `search_cordis_projects` |
| `app/services/data_intelligence/graph_service.py` | MODIFY | Add project discovery methods |
| `scripts/create_project_embeddings.py` | CREATE | Generate embeddings for semantic search |
| `scripts/create_project_embeddings_table.sql` | CREATE | Schema for embeddings |
| `tests/test_local_project_search.py` | CREATE | Test suite |

---

## Notes

- The `CordisProjectRepository` already exists and works - just need to wire it up!
- Neo4j already has project data - just need to add discovery queries
- Vector embeddings are optional but recommended for best semantic search
- Keep the old `CordisRAG` as fallback during transition

---

## References

- Existing repository: `app/services/data/cordis_repository.py`
- Graph service: `app/services/data_intelligence/graph_service.py`
- Similar implementation: `app/services/local_call_search_service.py` (for calls)

