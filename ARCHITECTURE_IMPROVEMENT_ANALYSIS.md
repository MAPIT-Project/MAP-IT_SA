# Architecture Improvement Analysis

## Current State Summary

### V3 Architecture (New - Simplified)
**Status:** ✅ Uses LOCAL data only

| Tool | Data Source | API Calls? |
|------|-------------|-----------|
| `search_funding_calls` | `LocalCallSearchService` → PostgreSQL `funding_calls` table | ❌ No |
| `search_projects` | `LocalProjectSearchService` → PostgreSQL + Neo4j | ❌ No |
| `search_documents` | `VectorSearchService` → Supabase pgvector | ❌ No |
| `get_programme_statistics` | `GraphSearchService` → Neo4j | ❌ No |
| `get_country_statistics` | `GraphSearchService` → Neo4j | ❌ No |

**V3 is already 100% local for core functionality.**

---

### V2 Architecture (Old - Complex)
**Status:** ⚠️ Still uses `eu_portal_search` which calls external API

| Tool | Data Source | API Calls? |
|------|-------------|-----------|
| `eu_portal_search` | `ImprovedCallSearchService` → `api.tech.ec.europa.eu` | ✅ YES - External API |
| `search_cordis_projects` | `LocalProjectSearchService` → PostgreSQL + Neo4j | ❌ No |
| `intelligent_search` | `DataIntelligenceService` → Neo4j + Supabase | ❌ No |

---

## Where `eu_portal_search` Is Still Used

### 1. `UnifiedIntentClassifier` (V2 routing)
**File:** `app/services/unified_intent_classifier.py`

```python
# Line 353 - When intent is search_calls
return [{
    'tool_name': 'eu_portal_search',  # ❌ External API
    'parameters': {'query': query, ...}
}]

# Line 454 - Fallback for search_calls
tool_plan=[{
    'tool_name': 'eu_portal_search',  # ❌ External API
    ...
}]
```

### 2. `ToolOrchestrator` (V2 execution)
**File:** `app/services/tools/tool_orchestrator.py`

```python
# Line 961 - Tool implementation
async def eu_portal_search(params, context):
    from ..improved_call_search import ImprovedCallSearchService  # ❌ External API
    search_service = ImprovedCallSearchService()
    results = search_service.search_calls_simple(...)  # Calls api.tech.ec.europa.eu
```

---

## Recommended Changes

### Option 1: Remove `eu_portal_search` Entirely (Recommended)

Since V3 already uses `LocalCallSearchService` which is better:
- ✅ Faster (no network latency)
- ✅ Works offline
- ✅ More consistent
- ✅ No rate limits

**Changes needed:**

1. **Update `UnifiedIntentClassifier`** to use `search_funding_calls` instead of `eu_portal_search`

```python
# Change from:
'tool_name': 'eu_portal_search'

# To:
'tool_name': 'search_funding_calls'
```

2. **Remove `eu_portal_search` from `ToolOrchestrator`** (or keep as fallback)

3. **Remove `ImprovedCallSearchService`** (or keep for enrichment only)

### Option 2: Keep `eu_portal_search` for Enrichment Only

Use local search for discovery, API only for enrichment:

```
User asks for calls → LocalCallSearchService (fast, local)
User asks for specific call details → EU Portal API (fresh data)
```

---

## Other Areas for Significant Improvement

### 1. Remove V2 Intent Classification Entirely

The V2 flow is:
```
User Message → UnifiedIntentClassifier → Complex Routing → Tool Selection → Execution
```

This is redundant when V3 does:
```
User Message → ToolAwareAgent (decides everything)
```

**Recommendation:** Make V3 the default, deprecate V2 routing.

### 2. Consolidate Tool Implementations

Currently there are TWO sets of tools:
- `ToolOrchestrator` tools (V2) - in `app/services/tools/tool_orchestrator.py`
- `ToolAwareAgent` tools (V3) - in `app/services/agents/tool_aware_agent.py`

**Recommendation:** Merge into single tool registry used by both.

### 3. Improve Local Call Search

`LocalCallSearchService` could be enhanced:

```python
# Current: Basic text search
results = call_service.search_calls(query=keywords, num_results=15)

# Could add:
- Vector similarity search on call descriptions
- Semantic understanding of user queries
- Deadline-based filtering (upcoming vs past)
- Budget range filtering
```

### 4. Add Call Enrichment as Separate Tool

Instead of `eu_portal_search`, add `enrich_call_details`:

```python
async def _tool_enrich_call_details(self, params: Dict) -> Dict:
    """
    Enrich a call with fresh data from EU Portal (optional).
    Only called when user needs very latest info.
    """
    call_id = params.get('call_id')

    # First try local
    local_data = await self._tool_get_call_details({'call_id': call_id})

    # If user specifically asks for latest, call API
    if params.get('force_fresh', False):
        api_data = await self._fetch_from_eu_portal(call_id)
        return {**local_data, **api_data, 'source': 'enriched'}

    return local_data
```

### 5. Streaming in V3

V3 `process_message_v3` doesn't support streaming yet. Need to add:

```python
async def process_message_v3(self, ..., streaming: bool = False):
    if streaming:
        async for event in self._stream_v3_response(...):
            yield event
    else:
        return await self._process_v3_sync(...)
```

---

## Files to Modify

| File | Change |
|------|--------|
| `app/services/unified_intent_classifier.py` | Replace `eu_portal_search` with `search_funding_calls` |
| `app/services/tools/tool_orchestrator.py` | Remove or deprecate `eu_portal_search` |
| `app/services/conversation/conversation_manager.py` | Make V3 default, add streaming |
| `app/api/conversation_routes_v2.py` | Add V3 endpoints |

---

## Quick Win: Fix V2 to Use Local Search

If you want a quick fix for V2 without full migration:

```python
# In unified_intent_classifier.py, change:

# FROM:
'tool_name': 'eu_portal_search'

# TO:
'tool_name': 'search_funding_calls'
```

This makes V2 use local data while keeping the rest of the architecture.

---

## Summary

| Architecture | Call Search | API Dependent? | Recommendation |
|--------------|-------------|----------------|----------------|
| V3 (new) | `LocalCallSearchService` | ❌ No | ✅ Use this |
| V2 (old) | `ImprovedCallSearchService` | ✅ Yes (EU Portal API) | ⚠️ Migrate to V3 |

**Bottom line:** V3 is already better. The main work is:
1. Add streaming to V3
2. Create V3 API endpoints
3. Deprecate V2 or update it to use local tools
