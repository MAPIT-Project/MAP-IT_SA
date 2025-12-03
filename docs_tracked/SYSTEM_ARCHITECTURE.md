# MAP-IT System Architecture

> **Last Updated:** December 3, 2024  
> **Version:** 2.3 (Local-First Project Search + Graph-Enhanced Discovery)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Query Processing Pipeline](#query-processing-pipeline)
4. [Agentic Loop (Self-Correcting)](#agentic-loop-self-correcting)
5. [Multi-Tool Agent (ReAct)](#multi-tool-agent-react)
6. [Available Tools](#available-tools)
7. [Data Sources](#data-sources)
8. [Key Services](#key-services)
9. [Configuration](#configuration)
10. [Example Flows](#example-flows)

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
| **Project Search** | Search CORDIS for funded projects (100% local: PostgreSQL + Neo4j) |
| **Project Discovery** | Find similar projects, organization collaborations, cluster-based search |
| **Statistics** | Get success rates, funding amounts, participation data |
| **Comparisons** | Compare programmes, countries, or funding types |
| **Document Search** | Search official EU regulations and work programmes |

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
│  • 15 tools available: stats, docs, calls, projects, relationships         │
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
│  │             │  │             │  │             │  │                     │ │
│  │ Statistics  │  │ Documents   │  │ Funded      │  │ Call details        │ │
│  │ Patterns    │  │ Embeddings  │  │ Projects    │  │ Live data           │ │
│  │ Relations   │  │ Chunks      │  │ Search      │  │                     │ │
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

The system has **15 tools** available for the multi-tool agent:

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
| `search_specific_topic` | Deep semantic search for a topic | `topic`, `context` |

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
| `search_projects` | Search CORDIS for funded projects (LOCAL-FIRST: PostgreSQL + Neo4j) | `keywords`, `programme`, `country` |
| `get_project_details` | Get details for a project | `project_id` |
| `find_similar_projects` | Find projects similar to a given project | `project_id`, `similarity_type` (topic/consortium/cluster) |
| `find_organization_projects` | Find all projects an organization participated in | `organization_name`, `role` (optional) |
| `get_collaboration_network` | Get collaboration network for an organization | `organization_name` |
| `search_by_cluster` | Find projects in a specific research cluster | `cluster` (name or code) |

**Examples:**
```python
# Local-first project search (no API calls!)
search_projects(keywords='quantum computing', country='Germany')
# Returns: [{ "acronym": "...", "funding": "...", "participants": [...] }]

# Find similar projects
find_similar_projects(project_id='101000000', similarity_type='topic')
# Returns: [{ "id": "...", "title": "...", "similarity_type": "topic", ... }]

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

### Validation Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `verify_eligibility` | Check eligibility for a scenario | `entity_type`, `country`, `programme`, `role` |
| `cross_reference` | Verify info across sources | `claim`, `sources` |

**Example:**
```python
verify_eligibility(entity_type='SME', country='Switzerland', programme='Horizon Europe')
# Returns: { "eligible": true, "conditions": [...], "sources": [...] }
```

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

**Purpose:** Funded project information

**Contains:**
- All Horizon Europe funded projects (13,865+ projects indexed)
- Project descriptions, objectives
- Consortium compositions
- Funding amounts
- Publications, deliverables

**Tables:**
- `projects` - Project metadata (title, objective, status, dates, budget)
- `organizations` - Organization data (name, country, role, SME status)

**Queries via:** `CordisProjectRepository` → `LocalProjectSearchService`

**Search Capabilities:**
- Full-text search with PostgreSQL tsquery
- Country/programme/status filtering
- Multi-source fusion with Neo4j graph data
- **100% local** - No external API calls

### 4. EU Portal API

**Purpose:** Live call data enrichment

**Used for:**
- Fetching missing call details
- Verifying deadlines
- Getting latest status
- Enriching local data

**Queries via:** `CallEnrichmentService`

---

## Key Services

### Core Services

| Service | File | Purpose |
|---------|------|---------|
| `ConversationManager` | `conversation_manager.py` | Main orchestrator |
| `AgenticManager` | `agentic_manager.py` | Self-correcting loop |
| `ToolAwareAgent` | `tool_aware_agent.py` | Multi-tool reasoning |
| `UnifiedIntentClassifier` | `unified_intent_classifier.py` | Intent detection |

### Data Services

| Service | File | Purpose |
|---------|------|---------|
| `DataIntelligenceService` | `data_intelligence_service.py` | Graph + Vector search |
| `VectorSearchService` | `vector_search_service.py` | Semantic search |
| `GraphSearchService` | `graph_service.py` | Neo4j queries |
| `LocalCallSearchService` | `local_call_search_service.py` | Call search |
| `LocalProjectSearchService` | `local_project_search_service.py` | Multi-source project search (PostgreSQL + Neo4j) |
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
- [x] **Multi-tool reasoning:** ReAct agent with 15 tools
- [x] **Local-first project search:** PostgreSQL + Neo4j (no API dependency)
- [x] **Graph-enhanced search:** Relationship-based project discovery (similar projects, org networks, clusters)

## Future Improvements

- [ ] **Phase 3:** Streaming UX improvements in frontend
- [ ] **Phase 4:** Plan caching for repeated query patterns
- [ ] **Phase 4:** Parallel execution within agentic iterations
- [ ] Add more tools (budget calculator, timeline generator)
- [ ] Implement tool usage analytics
- [ ] Add user feedback loop for quality improvement

