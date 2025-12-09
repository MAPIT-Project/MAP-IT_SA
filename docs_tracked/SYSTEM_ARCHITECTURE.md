# MAP-IT System Architecture

> **Last Updated:** December 3, 2025
> **Version:** 3.0 (V3 Simplified Architecture with Rich Response Formatting)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [V3 Simplified Architecture](#v3-simplified-architecture)
3. [Architecture Diagram](#architecture-diagram)
4. [Query Processing Pipeline](#query-processing-pipeline)
5. [Agentic Loop (Self-Correcting)](#agentic-loop-self-correcting)
6. [Multi-Tool Agent (ReAct)](#multi-tool-agent-react)
7. [Available Tools](#available-tools)
8. [Data Sources](#data-sources)
9. [Key Services](#key-services)
10. [Configuration](#configuration)
11. [Example Flows](#example-flows)

---

## System Overview

MAP-IT is an intelligent research assistant for EU funding programs (Horizon Europe, EIC, ERC, MSCA, etc.). It uses a sophisticated **agentic architecture** that can:

- **Self-correct** when initial search results are insufficient
- **Use multiple tools** to gather information from different sources
- **Reason iteratively** to answer complex comparison and analysis questions
- **Synthesize answers** from graph databases, vector stores, and external APIs

### Key Capabilities

| Capability | Description |
|------------|-------------|
| **FAQ Answering** | Answer questions about eligibility, rules, requirements |
| **Call Search** | Find open/upcoming funding calls (local-first with API enrichment) |
| **Project Search** | Search CORDIS for funded projects (100% local: PostgreSQL + Neo4j + Vector) |
| **Semantic Search** | Find projects by meaning using AI embeddings (e.g., "renewable energy" finds "solar power") |
| **Project Discovery** | Find similar projects, organization collaborations, cluster-based search |
| **Statistics** | Get success rates, funding amounts, participation data |
| **Comparisons** | Compare programmes, countries, or funding types |
| **Document Search** | Search official EU regulations and work programmes |

---

## V3 Simplified Architecture

**Version 3.0** introduces a simplified architecture that removes intent classification in favor of a single agentic loop that handles all queries.

### Key Changes from V2

| Aspect | V2 (Legacy) | V3 (Simplified) |
|--------|-------------|-----------------|
| **Intent Classification** | UnifiedIntentClassifier analyzes every query | No classification - agent decides |
| **Routing** | Routes to different handlers based on intent | Single ToolAwareAgent handles all |
| **Response Formatting** | LLM generates formatted response | Post-processor formats structured data |
| **API Enrichment** | Manual enrichment calls | Automatic on-demand enrichment |

### V3 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v3/conversation/{id}/message/stream` | POST | Streaming response with SSE events |
| `/api/v3/conversation/{id}/message` | POST | Non-streaming response |
| `/api/v3/conversation/{id}/context` | GET | Get conversation history |
| `/api/v3/conversation/{id}/context` | DELETE | Clear conversation memory |
| `/api/v3/conversation/health` | GET | Health check |

### V3 Components

**1. conversation_routes_v3.py** - API routes
- Handles streaming and non-streaming requests
- Emits SSE events: `status`, `agent_thinking`, `tool_call`, `tool_result`, `token`, `complete`, `error`

**2. ToolAwareAgent** - Single agentic loop
- ReAct pattern (Reasoning + Acting)
- Decides which tools to use based on query
- Up to 5 iterations for complex queries
- Returns `tool_results` dict for formatter

**3. V3ResponseFormatter** - Rich response formatting
- Post-processor that formats tool results consistently
- `format_funding_calls()` - Formats calls with emojis, structured fields, Apply links
- `format_projects()` - Formats CORDIS projects with details
- Type icons: 🔬 RIA, 🚀 IA, 🤝 CSA, 💱 COFUND, 🎓 ERC, 👨‍🔬 MSCA
- Status icons: 🟢 Open, 🟡 Upcoming, 🔴 Closed

**4. CallEnrichmentService** - On-demand API enrichment
- Fetches missing data from EU Portal API
- Triggers when: `title.length < 20` OR `title == topic_code` OR `description.length < 50`
- Caches enriched data in PostgreSQL
- Works for both structured and vector search results

### V3 Streaming Event Types

```json
{"type": "status", "stage": "processing", "message": "Processing your query..."}
{"type": "agent_thinking", "content": "Analyzing query: find hydrogen funding calls..."}
{"type": "tool_call", "tool": "search_funding_calls", "args": {"keywords": "hydrogen"}}
{"type": "tool_result", "tool": "search_funding_calls", "result": {"calls_found": 15}}
{"type": "token", "content": "I found **15 funding opportunities**..."}
{"type": "complete", "metadata": {"architecture": "simplified_v3", "tools_used": [...]}}
```

### V3 Response Format Example

```markdown
I found **15 funding opportunities** for your query:

**1. Competitiveness, energy security and integration aspects of advanced biofuels**
📋 **Call ID:** HORIZON-CL5-2026-D3-02-01
🔬 **Type:** RIA
🟢 **Status:** Open
⏰ **Deadline:** 05 Feb 2026
🏛️ **Programme:** Cluster 5 - Climate, Energy and Mobility
💰 **Budget:** EUR 20.00 million

**Scope:** This topic focuses on advanced biofuels and renewable fuels...

🔗 **Apply:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/...

---

💡 **How to Apply:**
• **Register** on the EU Funding & Tenders Portal...
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER QUERY                                      │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      UNIFIED INTENT CLASSIFIER                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Classifies into: faq | search_calls | search_projects |            │   │
│  │                   call_specific | proposal_writing | follow_up       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ALL QUERIES → TOOL-AWARE AGENT                          │
│                        (ReAct Multi-Tool Reasoning)                         │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  1. THINK: Analyze query, decide which tools to use                   │ │
│  │  2. ACT: Call tools (can run multiple in parallel)                    │ │
│  │  3. OBSERVE: Review results from tools                                │ │
│  │  4. REPEAT: If more info needed, think again and call more tools     │ │
│  │  5. CONCLUDE: Synthesize final answer from all gathered data          │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  Smart Behavior:                                                            │
│  • Simple queries ("What is RIA?") → 1-2 iterations, fast                  │
│  • Complex queries ("Compare EIC vs ERC") → Up to 5 iterations, thorough   │
│  • 20 tools available: stats, docs, calls, projects, proposal support      │
│  • Speculative execution: pre-runs likely tools for faster responses       │
│  • Plan caching: reuses query plans for repeated patterns                  │
│                                                                             │
│  Fallback: Simple loop only if ToolAwareAgent unavailable                  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Neo4j     │  │  Supabase   │  │   CORDIS    │  │   EU Portal API     │ │
│  │   Graph     │  │  pgvector   │  │  Projects   │  │   (enrichment)      │ │
│  │             │  │             │  │ + Vectors   │  │                     │ │
│  │ Statistics  │  │ Documents   │  │ Funded      │  │ Call details        │ │
│  │ Patterns    │  │ Embeddings  │  │ Projects    │  │ Live data           │ │
│  │ Relations   │  │ Chunks      │  │ Embeddings  │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RESPONSE GENERATOR                                    │
│  - Formats response with citations                                          │
│  - Adds confidence indicators (high/medium/low)                             │
│  - Shows reasoning trace for complex queries                                │
│  - Streams tokens for real-time UX                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Query Processing Pipeline

### Phase 1: Intent Classification

The `UnifiedIntentClassifier` analyzes the user's message and classifies it into one of these intents:

| Intent | Description | Example |
|--------|-------------|---------|
| `faq` | General questions about EU funding | "What are RIA eligibility requirements?" |
| `search_calls` | Looking for funding opportunities | "Find hydrogen funding calls" |
| `search_projects` | Looking for funded projects | "Show me AI healthcare projects" |
| `call_specific` | Questions about a specific call | "What's the deadline for HORIZON-CL5-2025-D3-01?" |
| `proposal_writing` | Help with proposal drafting | "Help me write the excellence section" |
| `follow_up` | References previous conversation | "Can you explain that more?" |

### Phase 2: LLM-Driven Complexity Detection

For `faq` queries, the **LLM determines complexity** (not regex!):

The `UnifiedIntentClassifier` outputs:
```json
{
  "primary_intent": "faq",
  "complexity_type": "comparison|analysis|multi_source|validation|simple",
  "requires_multi_tool": true,
  "suggested_tools": ["compare_programmes", "get_programme_statistics"],
  "complexity_reasoning": "User wants to compare two programmes..."
}
```

**Complexity Types:**
| Type | Description | Example |
|------|-------------|---------|
| `simple` | Single source answers | "What is RIA?" |
| `comparison` | Comparing 2+ things | "Compare EIC vs ERC" |
| `analysis` | Explaining WHY | "Why do some countries succeed more?" |
| `multi_source` | Needs multiple info types | "Eligibility AND success rates" |
| `validation` | Verify/confirm | "Is EIC success rate really 8%?" |

**Routing (v2.2):**
- **ALL queries** → Tool-Aware Agent (ReAct) for best results
- The agent is smart: simple queries finish in 1-2 iterations, complex ones use up to 5
- Simple loop is only used as fallback if ToolAwareAgent is unavailable

### Phase 3: Execution

Depending on complexity, the query is processed by either:

1. **Agentic Manager** - Self-correcting single-source search
2. **Tool-Aware Agent** - Multi-tool ReAct reasoning

### Phase 4: Response Generation

Results are synthesized into a final response with:
- Answer text
- Source citations
- Confidence level
- Reasoning trace (for complex queries)

---

## Agentic Loop (Self-Correcting)

**File:** `app/services/agents/agentic_manager.py`

The Agentic Loop handles simpler queries with **automatic retry and refinement**.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  Query: "What are consortium requirements?"                     │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ITERATION 1                                                    │
│  📖 Understand → intent: faq, type: procedural                 │
│  📋 Plan → vector search + keyword search                      │
│  🔍 Execute → 3 results found                                  │
│  📊 Evaluate → score: 0.45 (below 0.65 threshold) ❌           │
│  🔍 Reflect → "Query too broad, results lack detail"           │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ITERATION 2                                                    │
│  📋 Replan → Add keywords: "eligibility minimum partners"      │
│  🔍 Execute → 8 results found                                  │
│  📊 Evaluate → score: 0.82 (above threshold) ✅                │
│  ✨ Synthesize → Generate final answer                         │
└─────────────────────────────────────────────────────────────────┘
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| `AgentContext` | `agent_context.py` | Tracks state across iterations |
| `ResultEvaluator` | `result_evaluator.py` | Scores results (0-100) |
| `Reflector` | `reflector.py` | Analyzes why results were poor |
| `Replanner` | `replanner.py` | Creates improved search strategy |

### Evaluation Metrics (Hybrid: Rule + LLM)

The `ResultEvaluator` uses a **hybrid approach**:

1. **Rule-based scoring** (fast, free) - always runs first
2. **LLM evaluation** (accurate, costs tokens) - only for uncertain cases (score 0.4-0.7)

**Rule-Based Metrics:**
| Metric | Weight | Description |
|--------|--------|-------------|
| Result Count | 20% | Enough results found? |
| Relevance Score | 25% | Are results semantically relevant? |
| Content Quality | 25% | Do results have detailed content? |
| Query Coverage | 15% | Do results contain query terms? |
| Source Diversity | 10% | Multiple sources used? |
| Freshness | 5% | Recent information? |

**LLM Evaluation (for edge cases):**
- Triggered when rule-based score is 0.4-0.7 (uncertain zone)
- Evaluates: relevance, completeness, accuracy, actionability
- Combined: `final_score = (rule_based * 0.3) + (llm_score * 0.7)`

**Threshold:** Results are **sufficient** if score ≥ 0.65

### Root Cause Analysis

When results are insufficient, the `Reflector` identifies the cause:

| Root Cause | Action Taken |
|------------|--------------|
| `query_too_broad` | Refine with specific terms |
| `query_too_narrow` | Broaden the search |
| `wrong_source` | Switch data source |
| `semantic_mismatch` | Use keyword search instead |
| `temporal_mismatch` | Add year filters |
| `entity_not_found` | Add entity context |

---

## Multi-Tool Agent (ReAct)

**File:** `app/services/agents/tool_aware_agent.py`

For **complex queries** (comparisons, analysis, multi-source), the Tool-Aware Agent uses the **ReAct pattern** (Reasoning + Acting).

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  Query: "Compare EIC Accelerator vs ERC success rates"         │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  🧠 THINK: "I need statistics for both programmes"              │
│  🔧 ACT: Call get_programme_statistics(EIC) ← PARALLEL         │
│          Call get_programme_statistics(ERC) ←                  │
│  👀 OBSERVE: Got stats for both                                │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  🧠 THINK: "Need to compare these directly"                    │
│  🔧 ACT: Call compare_programmes(EIC, ERC)                     │
│  👀 OBSERVE: Got comparison data                               │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  🧠 THINK: "Need context to explain the differences"           │
│  🔧 ACT: Call search_documents("EIC vs ERC differences")       │
│  👀 OBSERVE: Got explanatory text                              │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  🎯 CONCLUDE: Synthesize answer from all gathered data         │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Parallel Execution** | Independent tool calls run simultaneously |
| **Iterative Reasoning** | Up to 5 reasoning iterations |
| **LLM-Driven Decisions** | Gemini decides which tools to call next |
| **Fallback Logic** | Falls back to basic search if reasoning fails |

---

## Available Tools

The system has **18 tools** available for the multi-tool agent:

### Statistics Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_programme_statistics` | Success rates, funding amounts for a programme | `programme`, `metric` (optional) |
| `get_country_statistics` | Participation stats for a country | `country`, `programme` (optional) |

**Example:**
```python
get_programme_statistics(programme='EIC Accelerator', metric='success_rate')
# Returns: { "success_rate": 8.2, "total_funding": "1.2B EUR", ... }
```

### Comparison Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `compare_programmes` | Compare two programmes side-by-side | `programme_a`, `programme_b`, `metrics` |

**Example:**
```python
compare_programmes(programme_a='EIC', programme_b='ERC', metrics=['success_rate', 'avg_funding'])
# Returns: { "EIC": {...}, "ERC": {...}, "comparison": {...} }
```

### Document Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `search_documents` | Search official EU documents | `query`, `document_type` (optional), `max_results` |

**Example:**
```python
search_documents(query='consortium eligibility RIA', document_type='regulation')
# Returns: [{ "content": "...", "source": "Horizon Europe Regulation", ... }]
```

### Call Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `search_funding_calls` | Find open/upcoming calls | `keywords`, `status`, `year` |
| `get_call_details` | Get details for a specific call | `call_id` |

**Example:**
```python
search_funding_calls(keywords='hydrogen energy', status='open', year=2025)
# Returns: [{ "call_id": "HORIZON-CL5-2025-...", "deadline": "2025-04-15", ... }]
```

### Project Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `search_projects` | Search CORDIS for funded projects (LOCAL-FIRST: PostgreSQL + Neo4j + Vector) | `keywords`, `programme`, `country` |
| `get_project_details` | Get details for a project | `project_id` |
| `find_similar_projects` | Find projects similar to a given project (graph-based) | `project_id`, `similarity_type` (topic/consortium/cluster) |
| `find_semantically_similar_projects` | Find projects semantically similar using AI embeddings | `project_id`, `limit` |
| `find_organization_projects` | Find all projects an organization participated in | `organization_name`, `role` (optional) |
| `get_collaboration_network` | Get collaboration network for an organization | `organization_name` |
| `search_by_cluster` | Find projects in a specific research cluster | `cluster` (name or code) |

**Examples:**
```python
# Local-first project search with semantic matching (no API calls!)
search_projects(keywords='quantum computing', country='Germany')
# Returns: [{ "acronym": "...", "funding": "...", "participants": [...] }]
# Note: Uses PostgreSQL full-text + Neo4j graph + Vector semantic search with RRF fusion

# Find similar projects (graph-based: topic, consortium, or cluster)
find_similar_projects(project_id='101000000', similarity_type='topic')
# Returns: [{ "id": "...", "title": "...", "similarity_type": "topic", ... }]

# Find semantically similar projects (AI embeddings - understands meaning)
find_semantically_similar_projects(project_id='101000000', limit=10)
# Returns: [{ "id": "...", "title": "...", "similarity_score": 0.85, ... }]
# Note: Uses 768-dim embeddings to find conceptually similar projects

# Organization projects
find_organization_projects(organization_name='Fraunhofer', role='coordinator')
# Returns: [{ "id": "...", "title": "...", "role": "coordinator", ... }]

# Collaboration network
get_collaboration_network(organization_name='CNRS')
# Returns: { "organization": "CNRS", "partners": [...], "total_partners": 50 }

# Cluster search
search_by_cluster(cluster='Climate')
# Returns: [{ "id": "...", "title": "...", "cluster_name": "Climate", ... }]
```

### Proposal Support Tools (Group 2)

These tools help users improve proposal quality using **real data from 13,865+ funded projects**:

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_budget_benchmark` | Get budget statistics (HYBRID: Graph+SQL with weighted fusion) | `action_type`, `cluster`, `topic_keywords`, `include_org_type_breakdown`, `include_country_breakdown` |
| `get_consortium_patterns` | Analyze consortium composition patterns (HYBRID: Graph+SQL with parallel queries) | `action_type`, `cluster`, `topic_keywords`, `include_successful_templates`, `include_coordinator_analysis` |
| `find_experienced_partners` | Find organizations with track record (HYBRID: Graph+SQL with RRF fusion) | `keywords`, `country` (optional), `org_type` (optional), `limit` |
| `get_similar_funded_projects` | Find semantically similar funded projects using embeddings | `query`, `action_type` (optional), `cluster` (optional), `limit` |
| `analyze_call_history` | Analyze historical funding patterns (HYBRID: Graph+SQL with topic evolution) | `topic_pattern`, `cluster`, `keywords`, `year_from`, `year_to`, `include_topic_evolution`, `include_cluster_trends` |

**Examples:**
```python
# Budget benchmarking - "What's typical for a Climate RIA?" (HYBRID: Graph+SQL)
get_budget_benchmark(action_type='RIA', cluster='CL5', include_org_type_breakdown=True)
# Returns: {
#   "statistics": {
#     "projects_analyzed": 496,
#     "total_eu_contribution": {"min": 1.3M, "max": 20M, "average": 4.9M, "median": 4.5M},
#     "consortium_size": {"average": 13.3, "median": 12}
#   },
#   "metadata": {
#     "search_type": "hybrid",
#     "sources_used": ["graph", "sql"],
#     "graph_project_count": 496,
#     "sql_project_count": 408
#   },
#   "consortium_context": {"avg_partners": 15.6, "avg_countries": 7.9, ...},
#   "budget_by_org_type": [{"org_type": "REC", "percentage_of_total": 34.0, ...}, ...]
# }

# Consortium patterns - "What's the typical makeup of Health IAs?" (HYBRID: Graph+SQL)
get_consortium_patterns(action_type='IA', cluster='HLTH', include_successful_templates=True, include_coordinator_analysis=True)
# Returns: {
#   "success": true,
#   "consortium_size": {"avg_partners": 12.5, "avg_countries": 8.2},
#   "org_type_distribution": {"HES": 35%, "REC": 28%, "PRC": 22%, "OTH": 15%},
#   "country_distribution": {"Germany": 18%, "France": 14%, ...},
#   "successful_templates": [{"project_acronym": "...", "budget": ..., "partner_count": 15, ...}],
#   "coordinator_analysis": {"top_coordinators": [...]},
#   "metadata": {
#     "search_type": "hybrid",
#     "sources_used": ["graph", "sql"],
#     "inferred_clusters": []
#   }
# }

# Partner discovery - "Find German SMEs with hydrogen experience" (HYBRID: Graph+SQL)
find_experienced_partners(keywords='hydrogen fuel cells', country='Germany', org_type='SME', limit=10)
# Returns: {
#   "experienced_partners": [
#     {"name": "...", "country": "DE", "project_count": 5, "experience_score": 0.82,
#      "source": "both", "projects": [...], ...}
#   ],
#   "total_found": 47,
#   "metadata": {
#     "search_type": "hybrid",
#     "sources_used": ["graph", "sql"],
#     "graph_partners": 15,
#     "sql_partners": 12,
#     "inferred_clusters": ["CLUSTER-5"],
#     "two_hop_partners_added": 8
#   }
# }

# Similar projects - "Show funded projects like my AI healthcare idea"
get_similar_funded_projects(query='AI diagnostic imaging for early cancer detection', limit=5)
# Returns: {
#   "similar_projects": [
#     {"acronym": "AISCREEN", "similarity_score": 0.67, "objective": "...", ...}
#   ]
# }

# Call history - "What got funded in Cluster 4 over the years?" (HYBRID: Graph+SQL)
analyze_call_history(cluster='CL4', year_from=2021, year_to=2025, include_topic_evolution=True, include_cluster_trends=True)
# Returns: {
#   "success": true,
#   "calls_analyzed": 50,
#   "projects_funded": 811,
#   "total_funding_allocated": 4.79e9,
#   "timeline": {2024: {"projects_funded": 289, "total_funding": ..., "calls": 15}, ...},
#   "trends": {"funding_trend": "strongly_increasing", "year_over_year_funding_growth": 15.2},
#   "topic_landscape": {"total_topics": 100, "top_topics": [...], "topics_by_year": {...}},
#   "cluster_statistics": {"total_projects": 5000, "total_funding": 5.6e9, "avg_budget": 4.5e6},
#   "metadata": {
#     "search_type": "hybrid",
#     "sources_used": ["graph", "sql"],
#     "graph_trends_available": true,
#     "inferred_clusters": []
#   }
# }

# Call history with keyword inference (auto-detects cluster from keywords)
analyze_call_history(keywords='hydrogen fuel cell', include_topic_evolution=True)
# Returns: {
#   "success": true,
#   "metadata": {
#     "inferred_clusters": ["CLUSTER-5"],  # Auto-inferred from keywords!
#     "sources_used": ["graph", "sql"]
#   },
#   ...
# }
```

**Design Philosophy:**
- All data comes from **funded CORDIS projects** (no fake "AI scores" or success predictions)
- Helps users understand **realistic benchmarks** for their proposals
- Uses **768-dim embeddings** (Google text-embedding-004) for semantic similarity
- Timeline aggregations query **all matching projects** for accurate statistics

**Hybrid Graph+SQL Architecture (Tier 1 & 2 Tools):**
The proposal support tools use a hybrid architecture for optimal results:
- **Graph Service (Neo4j)**: Pre-aggregated statistics, relationship traversal, consortium patterns
- **SQL Service (PostgreSQL)**: Keyword filtering, detailed breakdowns, full project details
- **Parallel Execution**: Graph and SQL queries run in parallel via ThreadPoolExecutor
- **Result Fusion**: RRF (Reciprocal Rank Fusion) or weighted averaging depending on the tool
- **Cluster Inference**: Keywords automatically mapped to Horizon Europe clusters (CLUSTER-1 through CLUSTER-6)
- **SQL Fallback**: Tools gracefully degrade to SQL-only if Neo4j is unavailable

| Tool | Fusion Method | New Features |
|------|---------------|--------------|
| `get_budget_benchmark` | Weighted averaging (by project count) | Org type/country breakdowns, consortium context |
| `find_experienced_partners` | RRF (k=60) | 2-hop discovery, SQL enrichment |
| `get_consortium_patterns` | Weighted (60% SQL, 40% Graph) | Successful templates, coordinator analysis |
| `analyze_call_history` | Merge with max values | Topic evolution, cluster trends, cluster statistics |
| `calculate_budget` | Graph priority with SQL fallback | Cluster context, similar projects, data-grounded ratios |

---

## Data Sources

### 1. Neo4j Graph Database

**Purpose:** Statistics, patterns, relationships, project discovery

**Contains:**
- Programme success rates
- Country participation data
- Consortium patterns
- Funding distributions
- Organization relationships
- Project-topic-cluster relationships
- Organization collaboration networks

**Queries via:** `GraphSearchService`

**Project Discovery:**
- Find similar projects (by topic, consortium, or cluster)
- Organization project lookup
- Collaboration network mapping
- Cluster-based project search

### 2. Supabase (pgvector)

**Purpose:** Document storage and semantic search

**Contains:**
- Horizon Europe regulations
- Work programmes (2023-2027)
- Guidance documents
- Call topic descriptions
- Proposal templates

**Tables:**
- `horizon_documents` - Document metadata
- `document_chunks` - Text chunks with embeddings
- `funding_calls` - Structured call data

**Queries via:** `VectorSearchService`

### 3. CORDIS Database (Local PostgreSQL)

**Purpose:** Funded project information with semantic search

**Contains:**
- All Horizon Europe funded projects (13,865+ projects indexed)
- Project descriptions, objectives
- Consortium compositions
- Funding amounts
- Publications, deliverables
- **Vector embeddings** for semantic similarity (13,850 projects)

**Tables:**
- `projects` - Project metadata (title, objective, status, dates, budget)
- `organizations` - Organization data (name, country, role, SME status)
- `project_embeddings` - Vector embeddings (768-dim) for semantic search

**Queries via:** `CordisProjectRepository` → `LocalProjectSearchService`

**Search Capabilities:**
- Full-text search with PostgreSQL tsquery
- **Semantic vector search** with pgvector (cosine similarity)
- Country/programme/status filtering
- Multi-source fusion with Neo4j graph data using **RRF algorithm**
- **100% local** - No external API calls

**Embedding Details:**
- Model: Google `text-embedding-004` (768 dimensions)
- Content: Title + objective (first 2000 chars)
- Index: IVFFlat with 100 lists for fast approximate search

### 4. EU Portal API

**Purpose:** Live call data enrichment

**Used for:**
- Fetching missing call details
- Verifying deadlines
- Getting latest status
- Enriching local data

**Queries via:** `CallEnrichmentService`

---

## Hybrid Graph+SQL Architecture

### Partner Discovery Tool Enhancement

The `find_experienced_partners` tool uses a **hybrid architecture** that combines Neo4j graph traversal with PostgreSQL keyword search for optimal partner discovery.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PARTNER DISCOVERY REQUEST                             │
│                 keywords: "hydrogen fuel cells"                              │
│                 country: "Germany", org_type: "SME"                          │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CLUSTER INFERENCE                                       │
│  Keywords → Horizon Europe Clusters                                          │
│  "hydrogen" → CLUSTER-5 (Climate, Energy, Mobility)                         │
│  "AI", "machine learning" → CLUSTER-4 (Digital, Industry, Space)            │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────────────────────┐
│     GRAPH SERVICE           │ │           SQL SERVICE                        │
│     (Neo4j)                 │ │           (PostgreSQL)                       │
│                             │ │                                              │
│  • Cluster-based discovery  │ │  • Full-text keyword search                  │
│  • 2-hop partner discovery  │ │  • Complete project details                  │
│  • Relationship traversal   │ │  • Country/type filtering                    │
│  • Collaboration networks   │ │  • Role-based filtering                      │
│                             │ │                                              │
│  Returns: 15 partners       │ │  Returns: 12 partners                        │
│  (may lack project details) │ │  (with full project info)                    │
└─────────────────────────────┘ └─────────────────────────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RRF FUSION (Reciprocal Rank Fusion)                       │
│                                                                              │
│  • Merge results from both sources (k=60)                                   │
│  • Boost partners found in BOTH sources: +0.005                             │
│  • Boost well-connected 2-hop partners: +0.002                              │
│  • Deduplicate by normalized organization name                              │
│                                                                              │
│  Result: 20 unique partners, ranked by combined score                        │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SQL ENRICHMENT (Graph-Only Partners)                      │
│                                                                              │
│  • Partners from graph may lack project details                             │
│  • Fetch project examples from SQL for graph-only partners                  │
│  • Add project titles, funding, dates to enrich results                     │
│                                                                              │
│  Enriched: 5 graph-only partners now have project details                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Cluster Inference** | Maps research keywords to Horizon Europe clusters (CLUSTER-1 to CLUSTER-6) |
| **Graph Discovery** | Neo4j traversal finds organizations through relationships, not just keywords |
| **2-Hop Partners** | Discovers "partners of partners" - extended collaboration network |
| **RRF Fusion** | Combines rankings from Graph and SQL using Reciprocal Rank Fusion |
| **Score Boosting** | Partners in both sources get +0.005; connected 2-hop partners get +0.002 |
| **SQL Enrichment** | Graph-only partners are enriched with SQL project details |

### Cluster Keyword Mapping

```python
CLUSTER_KEYWORDS = {
    'CLUSTER-1': ['health', 'medical', 'clinical', 'disease', 'pandemic', ...],
    'CLUSTER-2': ['culture', 'heritage', 'democracy', 'migration', ...],
    'CLUSTER-3': ['security', 'cybersecurity', 'border', 'defense', ...],
    'CLUSTER-4': ['digital', 'AI', 'artificial intelligence', 'data', 'cloud', ...],
    'CLUSTER-5': ['climate', 'energy', 'hydrogen', 'solar', 'wind', 'transport', ...],
    'CLUSTER-6': ['food', 'agriculture', 'biodiversity', 'ocean', 'water', ...]
}
```

### Response Metadata

The tool returns detailed metadata about the hybrid search:

```json
{
  "experienced_partners": [...],
  "total_found": 20,
  "metadata": {
    "search_type": "hybrid",
    "sources_used": ["graph", "sql"],
    "graph_partners": 15,
    "sql_partners": 12,
    "merged_total": 20,
    "inferred_clusters": ["CLUSTER-5"],
    "two_hop_partners_added": 8,
    "graph_partners_enriched": 5,
    "graph_only_count": 5
  }
}
```

### File Location

- **Implementation:** `app/services/tools/partner_discovery.py`
- **Key Methods:**
  - `_find_partners_hybrid()` - Main hybrid orchestration
  - `_find_partners_graph()` - Neo4j graph-based discovery
  - `_find_partners_sql()` - PostgreSQL keyword search
  - `_find_2hop_partners()` - Partners of partners discovery
  - `_merge_partner_results()` - RRF fusion with boosts
  - `_enrich_graph_partners_with_sql()` - SQL enrichment for graph-only partners
  - `_infer_clusters_from_keywords()` - Keyword to cluster mapping
  - `get_collaboration_network()` - Get organization's collaboration network

---

### Budget Benchmark Tool Enhancement

The `get_budget_benchmark` tool uses a **hybrid architecture** that combines Neo4j pre-aggregated statistics with PostgreSQL keyword filtering for comprehensive budget benchmarks.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BUDGET BENCHMARK REQUEST                              │
│                 cluster: "CLUSTER-5", action_type: "RIA"                     │
│                 topic_keywords: "hydrogen fuel cells"                        │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CLUSTER INFERENCE (if no cluster)                       │
│  topic_keywords → Horizon Europe Clusters                                    │
│  "hydrogen" → CLUSTER-5 (Climate, Energy, Mobility)                         │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┬───────────────┐
              │               │               │               │
              ▼               ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  GRAPH STATS    │ │   SQL STATS     │ │ CONSORTIUM CTX  │ │ ORG TYPE/COUNTRY│
│  (Neo4j)        │ │   (PostgreSQL)  │ │   (Neo4j)       │ │   (PostgreSQL)  │
│                 │ │                 │ │                 │ │                 │
│ Pre-aggregated  │ │ Keyword filter  │ │ Avg partners    │ │ Budget by HES   │
│ cluster stats   │ │ Sample projects │ │ Avg countries   │ │ Budget by REC   │
│ Budget ranges   │ │ Detailed stats  │ │ Top coordinators│ │ Budget by PRC   │
│                 │ │                 │ │                 │ │ Top countries   │
│ Returns: 496    │ │ Returns: 408    │ │                 │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
              │               │               │               │
              └───────────────┼───────────────┴───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WEIGHTED FUSION (by project count)                        │
│                                                                              │
│  • Weight each source by project count                                      │
│  • Weighted average for budget metrics                                      │
│  • Use SQL for median (more accurate with filtering)                        │
│  • Use extreme min/max from either source                                   │
│  • Use max project count for confidence                                     │
│                                                                              │
│  Result: Comprehensive statistics with breakdowns                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Parallel Queries** | Graph, SQL, consortium, and breakdown queries run concurrently |
| **Weighted Fusion** | Merges Graph and SQL stats weighted by project count |
| **Cluster Inference** | Maps research keywords to Horizon Europe clusters automatically |
| **Org Type Breakdown** | Budget distribution by HES, REC, PRC, PUB, OTH |
| **Country Breakdown** | Top 15 countries by funding with coordination counts |
| **Consortium Context** | Average partners, countries, top coordinator countries |

### Response Metadata

```json
{
  "statistics": {
    "projects_analyzed": 496,
    "total_eu_contribution": {"min": 1322523, "max": 19949437, "average": 4856520, "median": 4488616},
    "consortium_size": {"average": 13.3, "median": 12}
  },
  "recommendations": {
    "suggested_budget_range": "€3.4M - €5.5M",
    "suggested_consortium_size": "10-15 partners",
    "confidence": "high"
  },
  "metadata": {
    "search_type": "hybrid",
    "sources_used": ["graph", "sql"],
    "graph_project_count": 496,
    "sql_project_count": 408,
    "inferred_clusters": ["CLUSTER-5"]
  },
  "consortium_context": {
    "avg_partners": 15.6,
    "avg_countries": 7.9,
    "top_coordinator_countries": ["ES", "IT", "EL", "DE", "BE"]
  },
  "budget_by_org_type": {
    "by_org_type": [
      {"org_type": "REC", "percentage_of_total": 34.0, "total_contribution": 669624790},
      {"org_type": "PRC", "percentage_of_total": 33.9, "total_contribution": 667374496},
      {"org_type": "HES", "percentage_of_total": 27.6, "total_contribution": 543128363}
    ]
  }
}
```

### File Location

- **Implementation:** `app/services/tools/budget_benchmark.py`
- **Key Methods:**
  - `get_benchmark()` - Main entry point with all options
  - `_get_benchmark_hybrid()` - Parallel query orchestration
  - `_get_benchmark_graph()` - Neo4j pre-aggregated stats
  - `_get_benchmark_sql()` - PostgreSQL keyword-filtered stats
  - `_merge_benchmark_results()` - Weighted fusion of results
  - `_get_budget_by_org_type()` - Breakdown by organization type
  - `_get_budget_by_country()` - Breakdown by country
  - `_get_consortium_context()` - Consortium patterns from graph
  - `_infer_clusters_from_keywords()` - Keyword to cluster mapping
  - `get_budget_trends()` - Funding trends over time
  - `get_benchmark_comparison()` - Compare benchmarks across clusters

---

## Key Services

### Core Services

| Service | File | Purpose |
|---------|------|---------|
| `ConversationManager` | `conversation_manager.py` | Main orchestrator |
| `AgenticManager` | `agentic_manager.py` | Self-correcting loop (V2) |
| `ToolAwareAgent` | `tool_aware_agent.py` | Multi-tool reasoning (V3 primary) |
| `UnifiedIntentClassifier` | `unified_intent_classifier.py` | Intent detection (V2 only) |
| `V3ResponseFormatter` | `response/v3_response_formatter.py` | Rich formatting for calls/projects (V3) |

### Data Services

| Service | File | Purpose |
|---------|------|---------|
| `DataIntelligenceService` | `data_intelligence_service.py` | Graph + Vector search |
| `VectorSearchService` | `vector_search_service.py` | Semantic search |
| `GraphSearchService` | `graph_service.py` | Neo4j queries |
| `LocalCallSearchService` | `local_call_search_service.py` | Call search |
| `LocalProjectSearchService` | `local_project_search_service.py` | Multi-source project search (PostgreSQL + Neo4j + Vector) |
| `CordisProjectRepository` | `data/cordis_repository.py` | PostgreSQL project data access |

### Support Services

| Service | File | Purpose |
|---------|------|---------|
| `QueryPlanner` | `query_planner.py` | LLM-based query planning |
| `CrossEncoderReranker` | `cross_encoder_reranker.py` | Result reranking |
| `CallEnrichmentService` | `call_enrichment_service.py` | API enrichment |
| `MemoryService` | `memory_service.py` | Conversation memory |

---

## Configuration

### Environment Variables

```bash
# AI Models
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-flash-latest          # Used by all agentic components
DEFAULT_AI_PROVIDER=gemini

# Database
DATABASE_URL=postgresql://...
SUPABASE_URL=http://localhost:54321
SUPABASE_KEY=your_key

# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Redis (for caching)
REDIS_URL=redis://redis:6379
```

### Agentic Configuration

```python
# In agentic_manager.py
AgenticManager(
    max_iterations=3,        # Max self-correction attempts
    sufficient_score=0.65,   # Quality threshold (0-1)
    enable_multi_tool=True   # Enable ReAct agent
)

# In tool_aware_agent.py
ToolAwareAgent(
    max_iterations=5         # Max reasoning iterations
)
```

---

## Example Flows

### Example 1: Simple FAQ

```
User: "Can Switzerland participate in Horizon Europe?"

1. Intent: faq (confidence: 0.95)
2. Route: Agentic Manager (simple query)
3. Iteration 1:
   - Plan: vector search + keyword search
   - Execute: 4 results found
   - Evaluate: score 0.90 ✅ (sufficient)
4. Response: "Yes, Switzerland can participate as an Associated Country..."
```

### Example 2: Complex Comparison

```
User: "Compare EIC Accelerator success rates with regular RIA grants"

1. Intent: faq (confidence: 0.95)
2. Complexity: comparison detected
3. Route: Tool-Aware Agent (multi-tool)
4. Reasoning:
   - Step 1: get_programme_statistics(EIC) + get_programme_statistics(RIA)
   - Step 2: compare_programmes(EIC, RIA)
   - Step 3: search_documents("EIC vs RIA differences")
5. Synthesize from 3 sources
6. Response: "EIC Accelerator has ~8% success rate while RIA grants..."
```

### Example 3: Self-Correcting Search

```
User: "What are the consortium requirements?"

1. Intent: faq
2. Route: Agentic Manager
3. Iteration 1:
   - Execute: 3 results, low relevance
   - Evaluate: score 0.42 ❌
   - Reflect: "Query too broad"
4. Iteration 2:
   - Replan: Add "eligibility minimum partners EU"
   - Execute: 8 results, high relevance
   - Evaluate: score 0.85 ✅
5. Response: "For RIA projects, you need at least 3 independent entities..."
```

### Example 4: V3 Call Search with Rich Formatting

```
User: "Find hydrogen funding calls" (via /api/v3/conversation/{id}/message/stream)

1. No intent classification (V3 simplified)
2. ToolAwareAgent receives query directly
3. Agent thinking: "User wants funding calls about hydrogen"
4. Tool call: search_funding_calls(keywords="hydrogen", status="open")
5. Tool result: 15 calls found
6. V3ResponseFormatter formats results:
   - Enriches calls with missing titles via EU Portal API
   - Adds type icons (🔬 RIA, 🚀 IA, etc.)
   - Adds status icons (🟢 Open, 🟡 Upcoming)
   - Generates Apply links
   - Adds application guidance footer
7. Streaming events:
   - {"type": "agent_thinking", "content": "User wants funding calls..."}
   - {"type": "tool_call", "tool": "search_funding_calls", ...}
   - {"type": "tool_result", "tool": "search_funding_calls", ...}
   - {"type": "token", "content": "I found **15 funding opportunities**..."}
   - {"type": "complete", "metadata": {"architecture": "simplified_v3"}}
```

---

## Streaming Response Format

When using the streaming endpoint, progress updates are sent as SSE:

```json
{"type": "status", "stage": "processing", "message": "Processing..."}
{"type": "progress", "stage": "intent_detected", "message": "AI analyzed intent: faq"}
{"type": "progress", "stage": "agentic_search", "message": "AI is using self-correcting search..."}
{"type": "progress", "stage": "agentic_executing", "message": "Searching data sources..."}
{"type": "progress", "stage": "agentic_search", "message": "Found 8 results", "count": 8}
{"type": "progress", "stage": "agentic_evaluating", "message": "Found good results!"}
{"type": "status", "stage": "generating_response", "message": "Generating response..."}
{"type": "token", "content": "Based on the Horizon Europe regulation..."}
{"type": "token", "content": "..."}
{"type": "complete", "metadata": {"confidence": "high", "iterations": 1}}
```

---

## Completed Improvements

- [x] **Phase 1:** Self-correcting agentic loop
- [x] **Phase 2:** LLM-based complexity detection (replaces regex!)
- [x] **Phase 2:** LLM-based evaluation for edge cases (hybrid approach)
- [x] **Multi-tool reasoning:** ReAct agent with 16 tools
- [x] **Local-first project search:** PostgreSQL + Neo4j (no API dependency)
- [x] **Graph-enhanced search:** Relationship-based project discovery (similar projects, org networks, clusters)
- [x] **Phase 3:** Semantic project search with vector embeddings (13,850 projects embedded)
  - Vector similarity search using Google `text-embedding-004` (768 dimensions)
  - Three-source fusion: PostgreSQL full-text + Neo4j graph + Vector semantic search
  - RRF (Reciprocal Rank Fusion) algorithm for combining results
  - New tool: `find_semantically_similar_projects` for AI-powered similarity
- [x] **V3 Simplified Architecture:**
  - Single agentic loop (no intent classification)
  - V3 API routes at `/api/v3/conversation/...`
  - Rich response formatter (V3ResponseFormatter) with emojis, structured data, Apply links
  - On-demand API enrichment for missing call data (titles, descriptions)
  - SSE streaming events: `agent_thinking`, `tool_call`, `tool_result`, `token`, `complete`
- [x] **Group 2 Proposal Support Tools (5 new tools):**
  - `get_budget_benchmark`: Budget statistics from 13,865+ funded projects by action type/cluster
  - `get_consortium_patterns`: Consortium composition analysis (org types, countries, coordinator profiles)
  - `find_experienced_partners`: Partner discovery with track record scoring and filtering
  - `get_similar_funded_projects`: Semantic project similarity using 768-dim embeddings
  - `analyze_call_history`: Historical funding pattern analysis with timeline aggregation

## Recently Implemented Improvements

> **Latest Update:** December 9, 2025
> **Previous Update:** December 3, 2025

All planned improvements have been implemented. See details below:

| # | Improvement | Status | Files Created |
|---|-------------|--------|---------------|
| 1 | Plan caching for repeated query patterns | ✅ Implemented | `app/services/cache/query_plan_cache.py` |
| 2 | Parallel execution within agentic iterations | ✅ Implemented | `app/services/cache/speculative_executor.py` |
| 3 | Add more tools (budget calculator, timeline generator) | ✅ Implemented | `app/services/tools/budget_calculator.py`, `app/services/tools/timeline_generator.py` |
| 4 | Implement tool usage analytics | ✅ Implemented | `app/services/analytics/tool_analytics_service.py`, `migration/008_tool_analytics.sql` |
| 5 | Add user feedback loop for quality improvement | ✅ Implemented | `app/services/feedback/feedback_service.py`, `app/api/feedback_routes.py`, `migration/009_user_feedback.sql` |
| 6 | Incremental embedding updates for new projects | ✅ Implemented | `app/services/embedding/incremental_embedding_service.py`, Celery tasks in `celery_app.py` |
| 7 | V3 project formatter enhancements (publications, deliverables) | ✅ Implemented | Enhanced `app/services/response/v3_response_formatter.py`, new methods in `cordis_repository.py` |
| 8 | Partner Discovery hybrid Graph+SQL architecture | ✅ Implemented | Enhanced `app/services/tools/partner_discovery.py` |
| 9 | Budget Benchmark hybrid Graph+SQL architecture | ✅ Implemented | Enhanced `app/services/tools/budget_benchmark.py` |

### Implementation Details

**1. Plan Caching (QueryPlanCache)**
- Redis-based caching for query plans
- Pattern extraction: normalizes queries like "find hydrogen calls" → "{topic} calls"
- Cache TTL: configurable, default 1 hour
- Integrated with ToolAwareAgent for automatic plan reuse

**2. Speculative Execution (SpeculativeExecutor)**
- Pre-executes likely tools based on query patterns
- Uses asyncio for parallel I/O operations
- Reduces latency by 30-50% for common query patterns
- Automatic cleanup of unused speculative results

**3. New Tools**
- `calculate_budget`: Generates detailed budget breakdowns (personnel, equipment, travel, subcontracting)
- `generate_timeline`: Creates project timelines with work packages, deliverables, milestones
- Both tools include Horizon Europe-specific benchmarks and recommendations

**4. Tool Analytics**
- Tracks tool usage, latency, success rates
- Database tables: `tool_usage_analytics`, `tool_performance_metrics`, `tool_combination_analytics`
- Buffered writes to minimize database overhead
- Views for 24h performance metrics and popular tool combinations

**5. User Feedback**
- API endpoints at `/api/feedback/*`
- Collects ratings (1-5), comments, and per-tool feedback
- Database tables: `response_feedback`, `feedback_insights`
- AI-powered improvement suggestions based on feedback patterns

**6. Incremental Embeddings**
- Celery task `update_embeddings` for background processing
- Detects new, failed, or changed projects needing embeddings
- Uses Google's text-embedding-004 model (768-dim vectors)
- Processes in batches of 50 with configurable limits

**7. V3 Formatter Enhancements**
- `_format_single_project()` now includes publications, deliverables, impact metrics
- New repository methods: `get_project_publications()`, `get_project_deliverables()`, `get_project_impact_metrics()`
- Rich formatting with 📚 Publications and 📦 Deliverables sections

**8. Partner Discovery Hybrid Graph+SQL Architecture (December 9, 2025)**
- Combines Neo4j graph traversal with PostgreSQL keyword search for optimal results
- **Graph Service**: Cluster-based discovery, 2-hop partners (partners of partners), collaboration networks
- **SQL Service**: Full-text keyword search with complete project details
- **RRF Fusion**: Reciprocal Rank Fusion (k=60) merges results from both sources
- **Score Boosts**: Partners in both sources (+0.005), well-connected 2-hop partners (+0.002)
- **SQL Enrichment**: Graph-only partners automatically enriched with SQL project details
- **Cluster Inference**: Keywords mapped to Horizon Europe clusters (CLUSTER-1 to CLUSTER-6)
- New methods: `_find_partners_hybrid()`, `_find_partners_graph()`, `_find_partners_sql()`, `_find_2hop_partners()`, `_merge_partner_results()`, `_enrich_graph_partners_with_sql()`, `_infer_clusters_from_keywords()`, `get_collaboration_network()`

**9. Budget Benchmark Hybrid Graph+SQL Architecture (December 9, 2025)**
- Combines Neo4j pre-aggregated statistics with PostgreSQL keyword filtering for comprehensive benchmarks
- **Graph Service**: Pre-aggregated cluster statistics, budget ranges, consortium patterns
- **SQL Service**: Keyword filtering, sample projects, detailed breakdowns, org type/country stats
- **Weighted Fusion**: Merges results weighted by project count for accurate statistics
- **Parallel Queries**: Graph, SQL, consortium context, and breakdown queries run concurrently
- **New Breakdowns**: Budget by organization type (HES, REC, PRC, PUB, OTH), budget by country
- **Cluster Inference**: Keywords mapped to Horizon Europe clusters automatically
- New methods: `_get_benchmark_hybrid()`, `_get_benchmark_graph()`, `_get_benchmark_sql()`, `_merge_benchmark_results()`, `_get_budget_by_org_type()`, `_get_budget_by_country()`, `_get_consortium_context()`, `get_budget_trends()`, `get_benchmark_comparison()`

### Tool Count Update

The system now has **20 tools** available (increased from 18):
- Added: `calculate_budget`, `generate_timeline`

