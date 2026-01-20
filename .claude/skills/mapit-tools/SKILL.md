# MAPIT Tools Development Skill

This skill provides patterns and templates for creating, modifying, and integrating tools in the MAPIT AI agentic system. The system uses 23+ tools across multiple categories to answer EU funding questions.

## Quick Reference

| Step | Action | Location |
|------|--------|----------|
| 1 | Create tool file | `app/services/tools/my_tool.py` |
| 2 | Export in __init__ | `app/services/tools/__init__.py` |
| 3 | Register tool schema | `app/services/agents/tool_aware_agent.py:_init_tools()` |
| 4 | Add router entry | `app/services/agents/tool_aware_agent.py:_execute_single_tool()` |
| 5 | Add wrapper method | `app/services/agents/tool_aware_agent.py:_tool_my_tool()` |

---

## Tool File Template

### Standard Tool Structure

```python
"""
[Tool Name] Tool for Horizon Europe / Erasmus+ / Creative Europe.

[Brief description of what the tool does]

ARCHITECTURE: [HYBRID|GRAPH|SQL|VECTOR]
- Graph (Neo4j): [What graph does, if applicable]
- SQL (PostgreSQL): [What SQL does, if applicable]
- Vector (pgvector): [What vector search does, if applicable]
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS (if needed)
# ============================================================================

CLUSTER_KEYWORDS = {
    'CLUSTER-1': ['health', 'medical', 'clinical', 'disease', 'pandemic', 'pharmaceutical', 'biomedical'],
    'CLUSTER-2': ['culture', 'heritage', 'democracy', 'migration', 'social', 'inclusive'],
    'CLUSTER-3': ['security', 'cybersecurity', 'border', 'defense', 'civil', 'resilience'],
    'CLUSTER-4': ['digital', 'AI', 'artificial intelligence', 'data', 'cloud', 'computing', 'robotics'],
    'CLUSTER-5': ['climate', 'energy', 'hydrogen', 'solar', 'wind', 'transport', 'mobility', 'battery'],
    'CLUSTER-6': ['food', 'agriculture', 'biodiversity', 'ocean', 'water', 'bioeconomy', 'circular'],
}

CLUSTER_MAP = {
    'CLUSTER1': 'CLUSTER-1', 'CLUSTER-1': 'CLUSTER-1', 'CL1': 'CLUSTER-1', 'HLTH': 'CLUSTER-1', 'HEALTH': 'CLUSTER-1',
    'CLUSTER2': 'CLUSTER-2', 'CLUSTER-2': 'CLUSTER-2', 'CL2': 'CLUSTER-2', 'CULTURE': 'CLUSTER-2',
    'CLUSTER3': 'CLUSTER-3', 'CLUSTER-3': 'CLUSTER-3', 'CL3': 'CLUSTER-3', 'SECURITY': 'CLUSTER-3',
    'CLUSTER4': 'CLUSTER-4', 'CLUSTER-4': 'CLUSTER-4', 'CL4': 'CLUSTER-4', 'DIGITAL': 'CLUSTER-4',
    'CLUSTER5': 'CLUSTER-5', 'CLUSTER-5': 'CLUSTER-5', 'CL5': 'CLUSTER-5', 'CLIMATE': 'CLUSTER-5', 'ENERGY': 'CLUSTER-5',
    'CLUSTER6': 'CLUSTER-6', 'CLUSTER-6': 'CLUSTER-6', 'CL6': 'CLUSTER-6', 'FOOD': 'CLUSTER-6',
}

ORG_TYPE_DESCRIPTIONS = {
    "HES": "Higher Education Institution",
    "REC": "Research Organization",
    "PRC": "Private Company (Large)",
    "SME": "Small/Medium Enterprise",
    "PUB": "Public Body",
    "OTH": "Other Organization"
}


# ============================================================================
# TOOL CLASS
# ============================================================================

class MyNewTool:
    """
    [Tool description - what it does, when to use it]

    HYBRID ARCHITECTURE:
    - Graph: [Describe graph queries]
    - SQL: [Describe SQL queries]
    """

    def __init__(self):
        """Initialize database connections with graceful degradation."""
        self.db_url = os.getenv("DATABASE_URL")

        # Lazy-load graph service with fallback
        self._graph_service = None
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            self._graph_service = GraphSearchService()
            logger.info("Graph service available for MyNewTool")
        except Exception as e:
            logger.warning(f"Graph service not available: {e}")

    def _get_connection(self):
        """Get PostgreSQL database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _normalize_cluster_code(self, cluster: Optional[str]) -> Optional[str]:
        """Normalize cluster code to CLUSTER-X format."""
        if not cluster:
            return None
        cluster_upper = cluster.upper().strip().replace(' ', '-')
        return CLUSTER_MAP.get(cluster_upper)

    def _infer_clusters_from_keywords(self, keywords: str) -> List[str]:
        """Infer Horizon Europe clusters from research keywords."""
        keywords_lower = keywords.lower()
        matched = []
        for cluster_code, kw_list in CLUSTER_KEYWORDS.items():
            if any(kw in keywords_lower for kw in kw_list):
                matched.append(cluster_code)
        return matched if matched else ['CLUSTER-4']  # Default to Digital

    # ---- Main public method ----

    def do_something(
        self,
        required_param: str,
        optional_param: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Main tool method.

        Args:
            required_param: Description of required parameter
            optional_param: Optional parameter description
            limit: Maximum results to return

        Returns:
            Dict with success status, results, and metadata
        """
        try:
            # Your logic here
            results = self._execute_hybrid(required_param, optional_param, limit)

            return {
                "success": True,
                "tool_name": "my_new_tool",
                "query_params": {
                    "required_param": required_param,
                    "optional_param": optional_param,
                    "limit": limit
                },
                "results": results,
                "total_found": len(results),
                "metadata": {
                    "search_type": "hybrid",
                    "sources_used": ["graph", "sql"],
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"MyNewTool error: {e}")
            return {
                "success": False,
                "tool_name": "my_new_tool",
                "error": str(e),
                "message": "Failed to execute tool. Please try again.",
                "suggestions": ["Check your parameters", "Try simpler keywords"]
            }

    # ---- Private helper methods ----

    def _execute_hybrid(self, param1: str, param2: Optional[str], limit: int) -> List[Dict]:
        """Execute hybrid Graph+SQL query."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        graph_results = []
        sql_results = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}

            if self._graph_service:
                futures['graph'] = executor.submit(self._query_graph, param1, limit)
            futures['sql'] = executor.submit(self._query_sql, param1, param2, limit)

            for key, future in futures.items():
                try:
                    result = future.result(timeout=30)
                    if key == 'graph':
                        graph_results = result or []
                    else:
                        sql_results = result or []
                except Exception as e:
                    logger.warning(f"{key} query failed: {e}")

        return self._merge_results(graph_results, sql_results, limit)

    def _query_graph(self, param1: str, limit: int) -> List[Dict]:
        """Query Neo4j graph database."""
        # Implement graph query
        return []

    def _query_sql(self, param1: str, param2: Optional[str], limit: int) -> List[Dict]:
        """Query PostgreSQL database."""
        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            # Your SQL query here
            cursor.execute("SELECT * FROM projects WHERE title ILIKE %s LIMIT %s",
                          (f"%{param1}%", limit))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    def _merge_results(self, graph: List[Dict], sql: List[Dict], limit: int) -> List[Dict]:
        """Merge results using RRF fusion."""
        # See RRF Pattern section below
        return (graph + sql)[:limit]


# ============================================================================
# EXECUTE FUNCTION (Entry point for agent)
# ============================================================================

async def my_new_tool_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute my_new_tool.

    This tool [description].
    Use when users [when to use].
    """
    # Parameter fallback handling (LLM might use different names)
    required_param = (
        params.get('required_param') or
        params.get('param') or
        params.get('keyword') or
        params.get('query')
    )

    if not required_param:
        return {
            "success": False,
            "error": "required_param is required",
            "tool_name": "my_new_tool"
        }

    optional_param = params.get('optional_param')
    limit = params.get('limit', 10)

    tool = MyNewTool()
    return tool.do_something(
        required_param=required_param,
        optional_param=optional_param,
        limit=limit
    )
```

---

## Registering Tools in ToolAwareAgent

### Step 1: Export in `__init__.py`

Location: `app/services/tools/__init__.py`

```python
from .my_new_tool import MyNewTool, my_new_tool_execute

__all__ = [
    # ... existing exports ...
    'MyNewTool',
    'my_new_tool_execute',
]
```

### Step 2: Register Tool Schema

Location: `app/services/agents/tool_aware_agent.py` in `_init_tools()` method (~line 614)

```python
def _init_tools(self):
    # ... existing tools ...

    # My New Tool
    self.register_tool(Tool(
        name="my_new_tool",
        description="""[What this tool does - be specific]

**When to use**: [Guidance for LLM]
**Returns**: [What format the results come in]""",
        category=ToolCategory.STATISTICS,  # Choose appropriate category
        parameters={
            "required_param": "Required: Description with examples (e.g., 'hydrogen energy')",
            "optional_param": "Optional: Description (default: None)",
            "limit": "Optional: Max results to return (default: 10)"
        },
        examples=[
            "my_new_tool(required_param='quantum computing')",
            "my_new_tool(required_param='AI healthcare', optional_param='Germany', limit=20)"
        ]
    ))
```

### Step 3: Add Router Entry

Location: `app/services/agents/tool_aware_agent.py` in `_execute_single_tool()` (~line 2488)

```python
async def _execute_single_tool(self, tool_name: str, params: Dict) -> Any:
    # ... existing tools ...

    elif tool_name == 'my_new_tool':
        return await self._tool_my_new_tool(params)

    # ... rest of tools ...
```

### Step 4: Add Wrapper Method

Location: `app/services/agents/tool_aware_agent.py` (add after other wrapper methods)

```python
async def _tool_my_new_tool(self, params: Dict) -> Dict:
    """Wrapper for my_new_tool execution."""
    try:
        from ..tools.my_new_tool import my_new_tool_execute
        result = await my_new_tool_execute(params, {})
        return result
    except Exception as e:
        logger.error(f"Tool my_new_tool failed: {e}")
        return {"error": str(e), "tool_name": "my_new_tool"}
```

---

## Tool Categories

Use these categories when registering tools:

| Category | Use For | Examples |
|----------|---------|----------|
| `STATISTICS` | Aggregated data, metrics, success rates | `get_programme_statistics`, `get_country_statistics` |
| `DOCUMENTS` | Vector search, text retrieval | `search_documents`, `search_erasmus_templates` |
| `CALLS` | Funding call search | `search_funding_calls`, `get_call_details` |
| `PROJECTS` | CORDIS project search | `search_projects`, `find_similar_projects` |
| `COMPARISON` | Cross-reference, comparisons | `compare_programmes` |
| `VALIDATION` | Fact-checking, verification | Eligibility checks |
| `PROGRAMMES` | Multi-programme discovery | Cross-programme tools |
| `PROPOSAL` | Proposal writing assistance | `calculate_budget`, `generate_timeline` |

---

## Hybrid Architecture Patterns

### Pattern 1: RRF Fusion (Partner Discovery, Project Search)

Use when: Merging ranked lists from different sources

```python
def _merge_results_rrf(self, graph_results: List, sql_results: List, limit: int) -> List:
    """Reciprocal Rank Fusion merger."""
    k = 60  # RRF constant (balanced ranking)

    scores = {}  # name -> score
    items = {}   # name -> item
    sources = {} # name -> set of sources

    # Score graph results
    for rank, item in enumerate(graph_results, 1):
        name = item.get('name', '').lower().strip()
        if not name:
            continue
        scores[name] = scores.get(name, 0) + (1.0 / (k + rank))
        items[name] = item
        sources.setdefault(name, set()).add('graph')

    # Score SQL results
    for rank, item in enumerate(sql_results, 1):
        name = item.get('name', '').lower().strip()
        if not name:
            continue
        scores[name] = scores.get(name, 0) + (1.0 / (k + rank))
        if name not in items:
            items[name] = item
        sources.setdefault(name, set()).add('sql')

    # Boost items found in both sources
    for name in scores:
        if len(sources.get(name, set())) > 1:
            scores[name] += 0.005  # Both-source boost

    # Sort by combined score
    ranked = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    return [items[name] for name in ranked[:limit]]
```

### Pattern 2: Weighted Averaging (Budget Benchmarks, Statistics)

Use when: Combining aggregated statistics from multiple sources

```python
def _merge_statistics_weighted(self, graph_stats: Dict, sql_stats: Dict) -> Dict:
    """Weight results by data reliability (project count)."""
    graph_count = graph_stats.get('project_count', 0)
    sql_count = sql_stats.get('project_count', 0)
    total = graph_count + sql_count

    if total == 0:
        return {}

    graph_weight = graph_count / total
    sql_weight = sql_count / total

    return {
        'project_count': max(graph_count, sql_count),
        'avg_budget': (
            graph_stats.get('avg_budget', 0) * graph_weight +
            sql_stats.get('avg_budget', 0) * sql_weight
        ),
        'median_budget': sql_stats.get('median_budget'),  # SQL more accurate for median
        'min_budget': min(
            graph_stats.get('min_budget', float('inf')),
            sql_stats.get('min_budget', float('inf'))
        ),
        'max_budget': max(
            graph_stats.get('max_budget', 0),
            sql_stats.get('max_budget', 0)
        ),
    }
```

### Pattern 3: Vector + Graph Reranking (Similar Projects)

Use when: Semantic search with graph-based context enhancement

```python
def _rerank_with_graph(self, vector_results: List, graph_context: Dict) -> List:
    """Combine vector similarity with graph signals."""
    for item in vector_results:
        embedding_score = item.get('similarity_score', 0)

        # Get graph signals
        project_id = item.get('id')
        graph_data = graph_context.get(project_id, {})

        # Compute combined score (75% vector, 25% graph signals)
        graph_score = graph_data.get('cluster_relevance', 0) * 0.10
        consortium_score = min(graph_data.get('partner_count', 0) / 20, 1.0) * 0.10
        budget_score = min(graph_data.get('budget', 0) / 10_000_000, 1.0) * 0.05

        item['combined_score'] = (
            embedding_score * 0.75 +
            graph_score +
            consortium_score +
            budget_score
        )

    return sorted(vector_results, key=lambda x: x.get('combined_score', 0), reverse=True)
```

---

## Error Handling Patterns

### Graceful Degradation

```python
def __init__(self):
    # Always attempt to load services, but don't fail if unavailable
    self._graph_service = None
    try:
        from ..data_intelligence.graph_service import GraphSearchService
        self._graph_service = GraphSearchService()
        logger.info("Graph service available")
    except Exception as e:
        logger.warning(f"Graph service unavailable, using SQL-only mode: {e}")
```

### Query Timeout Handling

```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError

with ThreadPoolExecutor(max_workers=4) as executor:
    future = executor.submit(self._query_graph, params)
    try:
        result = future.result(timeout=30)  # 30-second timeout
    except TimeoutError:
        logger.warning("Graph query timed out, using SQL fallback")
        result = None
```

### Database Connection Safety

```python
def _query_sql(self, params) -> List[Dict]:
    conn = self._get_connection()
    if not conn:
        logger.warning("No database connection available")
        return []

    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"SQL query failed: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        conn.close()
```

---

## Response Format Standards

### Success Response

```python
{
    "success": True,
    "tool_name": "my_tool",
    "query_params": {
        "param1": "value1",
        "param2": "value2"
    },
    "results": [...],  # Main data
    "total_found": 25,
    "statistics": {...},  # Optional aggregations
    "recommendations": [...],  # Optional suggestions
    "metadata": {
        "search_type": "hybrid",
        "sources_used": ["graph", "sql"],
        "graph_count": 15,
        "sql_count": 20,
        "inferred_clusters": ["CLUSTER-5"],
        "timestamp": "2026-01-20T10:30:00.000000"
    }
}
```

### Error Response

```python
{
    "success": False,
    "tool_name": "my_tool",
    "error": "Technical error message",
    "message": "User-friendly explanation",
    "suggestions": [
        "Try using different keywords",
        "Check that the parameter is valid"
    ]
}
```

---

## Budget Calculation Constants

For tools dealing with budgets:

```python
# Funding rates by action type
FUNDING_RATES = {
    'RIA': 1.00,     # 100% funding
    'IA': 0.70,      # 70% funding
    'CSA': 1.00,     # 100% funding
    'ERC': 1.00,     # 100% funding
    'MSCA': 1.00,    # 100% funding
    'EIC': 0.70,     # 70% for grants
}

# Personnel cost per person-month by country tier
PERSONNEL_COSTS = {
    'tier1': 8500,  # High-cost countries (DE, FR, NL, BE, AT, etc.)
    'tier2': 6500,  # Medium-cost countries (ES, IT, PT, etc.)
    'tier3': 4500,  # Lower-cost countries (EE, LT, LV, etc.)
}

# Typical budget ratios
COST_RATIOS = {
    'RIA': {'personnel': 0.60, 'equipment': 0.10, 'travel': 0.08, 'other': 0.15, 'indirect': 0.25},
    'IA': {'personnel': 0.50, 'equipment': 0.15, 'travel': 0.08, 'other': 0.20, 'indirect': 0.25},
    'CSA': {'personnel': 0.70, 'equipment': 0.02, 'travel': 0.12, 'other': 0.10, 'indirect': 0.25},
}
```

---

## Testing Tools

Create test file at `tests/test_my_new_tool.py`:

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.tools.my_new_tool import MyNewTool, my_new_tool_execute


class TestMyNewTool:
    """Tests for MyNewTool."""

    @pytest.fixture
    def tool(self):
        """Create tool instance with mocked services."""
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test'}):
            return MyNewTool()

    def test_normalize_cluster_code(self, tool):
        """Test cluster code normalization."""
        assert tool._normalize_cluster_code('CL5') == 'CLUSTER-5'
        assert tool._normalize_cluster_code('CLIMATE') == 'CLUSTER-5'
        assert tool._normalize_cluster_code('invalid') is None

    def test_infer_clusters(self, tool):
        """Test cluster inference from keywords."""
        clusters = tool._infer_clusters_from_keywords('hydrogen energy storage')
        assert 'CLUSTER-5' in clusters

    @patch.object(MyNewTool, '_get_connection')
    def test_sql_query(self, mock_conn, tool):
        """Test SQL query execution."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'id': 1, 'name': 'test'}]
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = tool._query_sql('test', None, 10)
        assert len(result) == 1


@pytest.mark.asyncio
async def test_execute_function():
    """Test the async execute function."""
    with patch('app.services.tools.my_new_tool.MyNewTool') as MockTool:
        mock_instance = MockTool.return_value
        mock_instance.do_something.return_value = {
            'success': True,
            'results': []
        }

        result = await my_new_tool_execute(
            {'required_param': 'test'},
            {}
        )

        assert result['success'] is True
```

---

## Common Pitfalls

1. **Forgetting parameter fallbacks** - LLMs use inconsistent parameter names
2. **Not handling empty graph service** - Always check `if self._graph_service`
3. **Missing timeout on parallel queries** - Use `timeout=30` in `future.result()`
4. **Not closing database connections** - Always use `finally` block
5. **Hardcoding cluster codes** - Use `_normalize_cluster_code()` helper
6. **Missing tool category** - Every tool needs a `ToolCategory`
7. **Not adding examples** - Examples help LLM understand usage
8. **Forgetting to export** - Add to both `__init__.py` AND `__all__`

---

## Checklist for New Tools

- [ ] Created tool file in `app/services/tools/`
- [ ] Added `async execute` function with parameter fallbacks
- [ ] Implemented graceful degradation for services
- [ ] Added proper error handling with user-friendly messages
- [ ] Exported class and execute function in `__init__.py`
- [ ] Registered tool in `_init_tools()` with schema
- [ ] Added router entry in `_execute_single_tool()`
- [ ] Added wrapper method `_tool_my_tool()`
- [ ] Wrote unit tests
- [ ] Tested manually with sample queries
