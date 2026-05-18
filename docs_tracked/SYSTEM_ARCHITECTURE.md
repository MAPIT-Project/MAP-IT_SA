# MAP-IT System Architecture

> **Last Updated:** May 18, 2026
> **Version:** 3.5 (V3/V4 + All 6 EU Programmes + 42 Tools - Fully Cleaned)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [V3 Simplified Architecture](#v3-simplified-architecture)
3. [Architecture Diagram](#architecture-diagram)
4. [Query Processing Pipeline](#query-processing-pipeline)
5. [Multi-Tool Agent (ReAct)](#multi-tool-agent-react)
6. [Available Tools](#available-tools)
7. [Data Sources](#data-sources)
8. [Key Services](#key-services)
9. [Configuration](#configuration)
10. [Example Flows](#example-flows)

---

## System Overview

MAP-IT is an intelligent research assistant for EU funding programs. It supports **6 EU funding programmes**:

| Programme | Budget | Focus |
|-----------|--------|-------|
| **Horizon Europe** | €95.5B | Research and innovation (EIC, ERC, MSCA, Clusters 1-6) |
| **Erasmus+** | €26.2B | Education, training, youth and sport (KA1, KA2, KA3, Jean Monnet, Sport) |
| **Creative Europe** | €2.44B | Culture, media, and cross-sectoral (CULTURE, MEDIA, CROSS-SECTORAL strands) |
| **EU4Health** | €5.3B | Health policy, crisis preparedness, disease prevention |
| **Digital Europe** | €7.5B | Digital transformation (HPC, AI, Cybersecurity, Skills, Deployment) |
| **LIFE** | €5.4B | Environment and climate action (Nature, Circular Economy, Climate, Clean Energy) |

The system uses a sophisticated **agentic architecture** that can:

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
| **Multi-Programme Search** | Search across all EU programmes |
| **Programme Recommendations** | AI-powered recommendations for best-fit funding programmes |
| **Proposal Quality Scoring** | Evaluate proposal sections using EU evaluation criteria |
| **Geographic Analysis** | Analyze consortium geographic diversification patterns |

---

## V3 Simplified Architecture

**Version 3.0** introduced a simplified architecture that removes all intent classification in favor of a single agentic loop that handles all queries.

> **Note:** As of May 2026, V1 and V2 architectures—including `AgenticManager`, `UnifiedIntentClassifier`, and legacy RAG modules—have been **completely removed** from the codebase. The system now exclusively uses V3 (chat) and V4 (proposal sessions).

### V3 Architecture Highlights

| Aspect | Description |
|--------|-------------|
| **Intent Classification** | None - the agent dynamically decides what tools to use. |
| **Routing** | Single `ToolAwareAgent` handles all queries. |
| **Response Formatting** | Post-processor formats structured data with rich formatting (emojis, links). |
| **API Enrichment** | Automatic on-demand enrichment for missing call data via EU Portal API. |

### V3 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v3/conversation/{id}/message/stream` | POST | Streaming response with SSE events |
| `/api/v3/conversation/{id}/message` | POST | Non-streaming response |
| `/api/v3/conversation/{id}/context` | GET | Get conversation history |
| `/api/v3/conversation/{id}/context` | DELETE | Clear conversation memory |
| `/api/v3/conversation/health` | GET | Health check |

### V4 API Endpoints (Proposal Sessions)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v4/proposal-session/...` | Various | Unified AI Proposal Writer endpoints |

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
- Caches enriched data in PostgreSQL

---

## Architecture Diagram

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER QUERY                                      │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
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
│  • 42 tools available: stats, docs, calls, projects, proposal, all programmes   │
│  • Plan caching: reuses query plans for repeated patterns                  │
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
```

---

## Query Processing Pipeline (V3)

In V3, there is no intent classification. All queries go directly to the `ToolAwareAgent`.

### Phase 1: Query Reception
The query is received via V3 API endpoints and passed directly to the `ToolAwareAgent`.

### Phase 2: Agentic Processing
The `ToolAwareAgent` uses the ReAct pattern (Reasoning + Acting):
1. **THINK**: Analyze query, decide which tools to use.
2. **ACT**: Call tools (can run multiple in parallel).
3. **OBSERVE**: Review results from tools.
4. **REPEAT**: If more info needed, think again and call more tools.
5. **CONCLUDE**: Synthesize final answer from all gathered data.

### Phase 3: Response Generation
Results are synthesized into a final response with:
- Answer text with rich formatting
- Source citations
- Confidence level
- Streaming tokens for real-time UX

---

## Multi-Tool Agent (ReAct)

**File:** `app/services/agents/tool_aware_agent.py`

For **all queries**, the Tool-Aware Agent uses the **ReAct pattern** (Reasoning + Acting) to orchestrate data retrieval.

### How It Works

```text
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
│  🎯 CONCLUDE: Synthesize answer from all gathered data         │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Parallel Execution** | Independent tool calls run simultaneously |
| **Iterative Reasoning** | Up to 5 reasoning iterations |
| **LLM-Driven Decisions** | Gemini decides which tools to call next |

---

## Available Tools

The system has **42 tools** available. For a detailed breakdown of all tools, please refer to the `docs/guides/TOOL_REFERENCE.md` file.

### Tool Categories
- **Statistics Tools**: `get_programme_statistics`, `get_country_statistics`, `get_organization_stats`, etc.
- **Comparison Tools**: `compare_programmes`
- **Document Tools**: `search_documents`, `search_erasmus_templates`, etc.
- **Call Tools**: `search_funding_calls`, `get_call_details`, `search_all_programmes`
- **Project Tools**: `search_projects`, `get_project_details`, `find_similar_projects`, `find_semantically_similar_projects`
- **Proposal Support Tools**: `get_budget_benchmark`, `get_consortium_patterns`, `find_experienced_partners`, `calculate_budget`, `generate_timeline`
- **Eligibility Checkers**: Specific tools for Erasmus+, Creative Europe, EU4Health, Digital Europe, and LIFE.
- **Quality Scorer**: `score_proposal_section`, `score_full_proposal`, `validate_budget`

---

## Data Sources & Hybrid Search

The MAP-IT SA platform relies on a robust **Three-Tier Storage Architecture** to deliver high-precision results:

### 1. Supabase / PostgreSQL (Relational + Vector)
Our primary data hub, containing over **50 tables** and **18 views**.
- **CORDIS Data**: Locally hosted project metadata (~14,000 projects) and organization participation details (~90,000 records).
- **Knowledge Base**: Official EU document chunks (~40,000) for RAG.
- **Vector Search**: High-dimensional embeddings (768-dim and 3072-dim) using `pgvector`.
- **Hybrid Search Logic**: We utilize custom RPC functions like `hybrid_search` which combine:
  - **Vector Similarity**: Cosine distance scoring.
  - **Keyword Search**: PostgreSQL `ts_vector` and `ts_query` with GIN indexing.
  - **Reciprocal Rank Fusion (RRF)**: Merging results from multiple search strategies.

### 2. Neo4j Graph Database
Handles relationship-aware queries that are computationally expensive in traditional SQL.
- **Network Analysis**: Identifying experienced partners based on historical collaboration clusters.
- **Pre-aggregated Statistics**: Fast retrieval of programme-level and country-level funding stats.
- **Geographic Patterns**: Analyzing consortium diversification using graph traversal.

### 3. EU Portal API (Live Sync)
Ensures that time-sensitive data is always accurate.
- **Call Enrichment**: Fetching the latest deadline updates and full call texts on-demand.
- **Live Search**: Fallback for programmes not yet fully ingested into the local knowledge base.

*(For an exhaustive breakdown of all 50+ tables, see the [Database Schema Guide](../docs/DATABASE_SCHEMA.md))*

---

## Key Services

### Core Services

| Service | File | Purpose |
|---------|------|---------|
| `ConversationManager` | `conversation_manager.py` | Main orchestrator (Lean V3 version) |
| `ToolAwareAgent` | `tool_aware_agent.py` | Multi-tool reasoning (Primary logic loop) |
| `ProposalAwareAgent` | `proposal_aware_agent.py` | Specialized agent for V4 proposal sessions |

### Data Services

| Service | File | Purpose |
|---------|------|---------|
| `DataIntelligenceService` | `data_intelligence_service.py` | Graph + Vector search orchestration |
| `VectorSearchService` | `vector_search_service.py` | Semantic document search |
| `GraphSearchService` | `graph_service.py` | Neo4j relationship queries |
| `LocalCallSearchService` | `local_call_search_service.py` | Local and API-enriched call search |
| `LocalProjectSearchService` | `local_project_search_service.py` | Multi-source project search (PostgreSQL + Neo4j + Vector) |

---

## Configuration

### Environment Variables

```bash
# AI Models
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3-flash-preview       # Used by all agentic components
DEFAULT_AI_PROVIDER=gemini

# Database
DATABASE_URL=postgresql://...
SUPABASE_URL=http://localhost:54321
SUPABASE_KEY=your_key

# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### Agentic Configuration

```python
# In tool_aware_agent.py
ToolAwareAgent(
    max_iterations=5         # Max reasoning iterations
)
```

---

## Example Flows

### V3 Call Search with Rich Formatting

```text
User: "Find hydrogen funding calls" (via /api/v3/conversation/{id}/message/stream)

1. No intent classification. Query goes straight to ToolAwareAgent.
2. Agent thinking: "User wants funding calls about hydrogen"
3. Tool call: search_funding_calls(keywords="hydrogen", status="open")
4. Tool result: 15 calls found
5. V3ResponseFormatter formats results:
   - Enriches calls with missing titles via EU Portal API
   - Adds type icons (🔬 RIA, 🚀 IA, etc.)
   - Adds status icons (🟢 Open, 🟡 Upcoming)
   - Generates Apply links
6. Streaming events emitted back to the user.
```

### Partner Discovery (Hybrid Graph+SQL)

```text
User: "Find German SMEs with hydrogen experience"

1. Agent calls: find_experienced_partners(keywords='hydrogen fuel cells', country='Germany', org_type='SME')
2. Graph Service finds partners based on historical clusters and collaborations.
3. SQL Service finds partners using exact keyword matches.
4. Results are fused using Reciprocal Rank Fusion (RRF).
5. Graph-only partners are enriched with SQL project details.
6. Unified, highly relevant list returned to user.
```
