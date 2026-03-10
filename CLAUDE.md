# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Hard Rules
1. Always go for the best possible working solution that would be production ready, even if that means sacrificing performance.
2. If benefitial, always make use of subagents.

## Project Overview

This is a **production-grade Retrieval-Augmented Generation (RAG) system** for querying European research and education funding programmes. The system implements sophisticated multi-source intelligent search, agentic AI capabilities, and comprehensive tooling for:

- **Horizon Europe**: Research and innovation funding (CORDIS projects, calls, statistics)
- **Erasmus+**: Education, training, youth and sport funding (Programme Guide 2026, AWP 2026, calls)
- **Creative Europe**: Culture, media, and cross-sectoral funding (Work Programmes 2021-2026, CulturEU Guide, calls)

## Key Architecture Components

### Core Services Architecture (V3)
- **Multi-Source Intelligent Search**: Combines graph search (Neo4j), vector search (Supabase), and keyword search
- **Agentic AI System**: ToolAwareAgent with reflection, evaluation, and replanning capabilities
- **Data Intelligence Service**: Query planning, multi-source execution, and result fusion
- **Conversation Management**: Short-term/long-term memory with professional context injection

**Note**: V1 and V2 architectures have been removed. The codebase now uses V3 (conversation) and V4 (proposal sessions) exclusively.

### V3 Architecture
The V3 architecture uses a **single agentic loop** without intent classification:
- **No intent classification** - The agent decides what tools to use based on query and context
- **Single ToolAwareAgent** - Handles all query types with ReAct pattern
- **Rich response formatting** - Post-processor formats calls/projects with emojis, links, structured data
- **API enrichment** - Missing call data (titles, descriptions) fetched from EU Portal API on-demand

**V3 Components:**
- `conversation_routes_v3.py` - V3 API routes at `/api/v3/conversation/...`
- `ToolAwareAgent` - Single agentic loop for all queries
- `V3ResponseFormatter` - Post-processor for rich formatting
- `CallEnrichmentService` - On-demand API enrichment for missing data

### Agentic Architecture (ReAct Pattern)
The system uses a sophisticated **agentic architecture** that can:
- **Self-correct** when initial search results are insufficient
- **Use multiple tools** to gather information from different sources (41 tools available)
- **Reason iteratively** to answer complex comparison and analysis questions
- **Synthesize answers** from graph databases, vector stores, and external APIs
- **Speculatively execute** tools in parallel to reduce latency
- **Cache query plans** for repeated query patterns using Redis

**Key Capabilities:**
- **FAQ Answering**: Answer questions about eligibility, rules, requirements
- **Call Search**: Find open/upcoming funding calls (local-first with API enrichment)
- **Project Search**: Search CORDIS for funded projects (100% local: PostgreSQL + Neo4j + Vector embeddings, no API calls)
- **Semantic Search**: Find projects by meaning, not just keywords (e.g., "renewable energy" finds "solar power" projects)
- **Project Discovery**: Find similar projects, organization collaborations, cluster-based search
- **Statistics**: Get success rates, funding amounts, participation data
- **Comparisons**: Compare programmes, countries, or funding types
- **Document Search**: Search official EU regulations and work programmes

### Service Layer Organization (`app/services/`)
- `agents/` - Agentic AI components with reflection, evaluation, planning
- `analytics/` - Tool usage analytics and performance tracking
- `cache/` - Query plan caching and speculative execution
- `data_intelligence/` - Graph search, query planning, cross-encoder reranking
- `embedding/` - Incremental embedding updates for new projects
- `feedback/` - User feedback collection and analysis
- `rag/` - RAG-specific components (retrievers, chunkers, generators)
- `tools/` - Tool orchestration for multi-step reasoning (41 tools available)
- `call_extractors/` - Funding call document processing
- `conversation/` - Conversation management and memory
- `memory/` - Short/long-term memory systems
- `proposal_writing/` - AI-powered proposal assistance
- `response/` - Response generation utilities and V3 formatter

### API Layer Organization (`app/api/`)
- `conversation_routes_v3.py` - V3 simplified architecture routes (main conversation API)
- `proposal_session_routes.py` - V4 Proposal Session routes (unified AI Proposal Writer)
- `feedback_routes.py` - User feedback API endpoints
- `proposal_routes.py` - Proposal writing API endpoints
- `document_routes.py` - Document management endpoints
- `call_document_routes.py` - Call document access endpoints

### Available Tools (41 Tools)
The system has 41 tools available for the multi-tool agent:

**Statistics Tools:**
- `get_programme_statistics`: Success rates, funding amounts for a programme
- `get_country_statistics`: Participation stats for a country
- `analyze_geographic_diversification`: Analyze geographic diversity of consortium partners by custom country groups (Nordic, CEE, Baltic, etc.)

**Comparison Tools:**
- `compare_programmes`: Compare two programmes side-by-side

**Document Tools:**
- `search_documents`: Search official EU documents

**Call Tools:**
- `search_funding_calls`: Find open/upcoming calls
- `get_call_details`: Get details for a specific call

**Project Tools:**
- `search_projects`: Search CORDIS for funded projects (LOCAL-FIRST: PostgreSQL + Neo4j + Vector, no API calls). Supports `sort_by` parameter: `'relevance'` (default), `'ec_contribution'`, `'total_cost'`, `'start_date'`. Auto-fetches partners when user query mentions partners and limit ≤ 5.
- `get_project_details`: Get details for a project including full partner list
- `get_project_partners`: Get full list of partner organizations for a specific project by ID or acronym. Returns partner names, countries, roles, activity types, and EC contributions.
- `get_organization_stats`: Get aggregate statistics for an organization: total project count, coordinator count, total funding. Uses Neo4j graph with SQL fallback when graph is unavailable.
- `find_similar_projects`: Find projects similar to a given project (by topic, consortium, or cluster)
- `find_semantically_similar_projects`: Find projects semantically similar using AI embeddings (understands objectives)
- `find_organization_projects`: Find all projects an organization participated in. Returns total project count including beyond display limit.
- `get_collaboration_network`: Get collaboration network showing which organizations partner together
- `search_by_cluster`: Find projects in a specific research cluster (e.g., Climate, Health, Digital)

**Proposal Support Tools (Group 2):**
- `get_budget_benchmark`: Get budget statistics from similar funded projects (HYBRID: Graph+SQL with weighted fusion, org type/country breakdowns)
- `get_consortium_patterns`: Analyze consortium composition patterns (HYBRID: Graph+SQL with parallel queries, successful templates, coordinator analysis)
- `find_experienced_partners`: Find organizations with experience in specific research areas (HYBRID: Graph+SQL with RRF fusion)
- `get_similar_funded_projects`: Find semantically similar funded projects using AI embeddings
- `analyze_call_history`: Analyze historical funding patterns for topics/clusters (HYBRID: Graph+SQL with topic evolution, cluster trends, funding trends)

**Proposal Planning Tools:**
- `calculate_budget`: Generate detailed budget breakdown for a proposal (HYBRID: Graph+SQL with cluster context, similar projects, real-data grounded recommendations)
- `generate_timeline`: Create project timeline with work packages, deliverables, and milestones (HYBRID: Graph+SQL with duration patterns, cluster-specific WPs, real project examples)

**Erasmus+ Programme Tools:**
- `check_erasmus_eligibility`: Check organization/participant eligibility for Erasmus+ actions by Key Action (KA1, KA2, KA3, JMO, SPORT) and sector (HED, VET, SCH, ADU, YOU)
- `calculate_erasmus_budget`: Calculate Erasmus+ budgets using lump sum funding model with unit costs, travel bands, and activity-specific rates
- `search_erasmus_templates`: Search Erasmus+ Programme Guide for application guidance, quality criteria, budget rules, and sector-specific information

**Creative Europe Programme Tools:**
- `check_creative_europe_eligibility`: Check organization eligibility for Creative Europe actions by strand (CULTURE, MEDIA, CROSS-SECTORAL) and action type (COOP, DEV, DIST, etc.)
- `calculate_creative_europe_budget`: Calculate Creative Europe budgets based on action type, funding rates, and project scale
- `search_creative_europe_templates`: Search Creative Europe documents (Work Programmes, CulturEU Guide) for application guidance and programme information

**EU4Health Programme Tools:**
- `check_eu4health_eligibility`: Check organization eligibility for EU4Health actions (Action Grants, Joint Actions, Operating Grants, Procurement) by organization type and strand (CRISIS, PREVENTION, HEALTH_SYSTEMS, DIGITAL)
- `search_eu4health_templates`: Search EU4Health documents (Annual Work Programmes, Regulation) for application guidance and programme information

**Digital Europe Programme Tools:**
- `check_digital_europe_eligibility`: Check organization eligibility for Digital Europe funding across 6 objectives (HPC, AI, Cybersecurity, Skills, Deployment/EDIHs, Semiconductors)

**LIFE Programme Tools:**
- `check_life_eligibility`: Check organization eligibility for LIFE Programme across 4 sub-programmes (NAT, ENV, CCA, CET) covering nature, environment, climate, and clean energy
- `search_life_templates`: Search LIFE Programme documents for application guidance, eligibility criteria, and funding rules

**Cross-Programme Tools:**
- `search_all_programmes`: Search for funding opportunities across ALL 6 EU programmes in one query (Horizon Europe, Erasmus+, Creative Europe, EU4Health, Digital Europe, LIFE)
- `recommend_programmes`: Recommend the best EU funding programmes for a given project/organization based on description, org type, and sector
- `get_programme_info`: Get detailed information about a specific EU funding programme (budget, focus areas, action types, eligibility, actionable links)

**Proposal Quality Scoring Tools:**
- `score_proposal_section`: Evaluate a proposal section using EU Horizon Europe evaluation criteria (0-5 score, strengths, weaknesses, suggestions)
- `score_full_proposal`: Evaluate a complete proposal with all three sections (0-15 overall score, funding probability, section breakdown)
- `quick_quality_check`: Quick quality check for draft proposal text without full AI evaluation
- `validate_budget`: Validate a proposal budget against EU Horizon Europe funding rules (compliance score, issues)

### Key Services

**Core Services:**
- `ConversationManager` (`conversation_manager.py`): Main orchestrator
- `AgenticManager` (`agentic_manager.py`): Self-correcting loop
- `ToolAwareAgent` (`tool_aware_agent.py`): Multi-tool reasoning
- `UnifiedIntentClassifier` (`unified_intent_classifier.py`): Intent detection

**Data Services:**
- `DataIntelligenceService` (`data_intelligence_service.py`): Graph + Vector search
- `VectorSearchService` (`vector_search_service.py`): Semantic search
- `GraphSearchService` (`graph_service.py`): Neo4j queries (lazy-imported to avoid neo4j package shadowing)
- `LocalCallSearchService` (`local_call_search_service.py`): Call search
- `LocalProjectSearchService` (`local_project_search_service.py`): Multi-source project search (PostgreSQL + Neo4j + Vector embeddings)
- `CordisProjectRepository` (`data/cordis_repository.py`): PostgreSQL project data access (includes `get_project_partners()` for consortium lookup)
- `org_name_utils` (`data_intelligence/org_name_utils.py`): Organization name expansion utilities — city transliterations (Munich→muenchen) and university abbreviations (TU→technische universitaet). Separated from graph_service.py to avoid neo4j import dependency.

**Support Services:**
- `QueryPlanner` (`query_planner.py`): LLM-based query planning
- `CrossEncoderReranker` (`cross_encoder_reranker.py`): Result reranking
- `CallEnrichmentService` (`call_enrichment_service.py`): API enrichment
- `MemoryService` (`memory_service.py`): Conversation memory

**Performance & Analytics Services:**
- `QueryPlanCache` (`cache/query_plan_cache.py`): Redis-based caching for query plans
- `SpeculativeExecutor` (`cache/speculative_executor.py`): Parallel tool execution for latency reduction
- `ToolAnalyticsService` (`analytics/tool_analytics_service.py`): Track tool usage, performance, and patterns
- `FeedbackService` (`feedback/feedback_service.py`): User feedback collection and quality insights
- `IncrementalEmbeddingService` (`embedding/incremental_embedding_service.py`): Auto-update embeddings for new projects

### Data Management
- `data/cordis/` - CORDIS research project data
- `data/shared_documents/` - Shared Horizon Europe documents
- `data/manual_uploads/` - User-uploaded documents
- `newdocs/` - Horizon Europe work programmes and guidance

## Development Commands

### Makefile Commands
```bash
make install        # Install prod dependencies
make install-dev    # Install dev dependencies (ruff/black/isort/pytest/pre-commit)
make run            # Run API (uvicorn main:app)
make run-reload     # Run API with reload
make docker-up      # Start services via docker-compose
make docker-down    # Stop services
make lint           # Run ruff (lint)
make format         # Run ruff format + isort + black
make test           # Run pytest
make precommit      # Run pre-commit on all files
make hooks          # Install pre-commit git hooks
```

### Docker Services
The `docker-compose.yml` defines these services:
- `api` - FastAPI application
- `redis` - Redis for Celery message broker
- `celery-worker` - Regular RAG query processing
- `celery-worker-stream` - Streaming RAG queries
- `neo4j` - Graph database with APOC and GDS plugins

### Celery Tasks
Available Celery tasks in `app/services/celery_app.py`:
- `process_rag_query` - Process RAG queries asynchronously
- `process_rag_query_stream` - Process streaming RAG queries
- `update_embeddings` - Incremental embedding updates for new/modified projects
- `get_embedding_stats` - Get current embedding coverage statistics
- `health_check` - Worker health check

### Testing
```bash
# Run all tests
make test

# Run specific test files
pytest tests/test_integration_v2.py
pytest tests/test_intent_detection_only.py
pytest tests/test_data_source_verification.py
pytest tests/test_conversation_routing.py

# Run with coverage
pytest --cov=app tests/
```

## Key Configuration Files

### Environment Variables
- `.env.example` - Template for environment variables
- **Required**: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`
- **Optional**: `GOOGLE_EMBEDDING_API_KEY`, `SUPABASE_*`, `NEO4J_*`
- **AI Models**: `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3-flash-preview` (used by all agentic components)
- **Database**: `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY`
- **Neo4j**: `NEO4J_URI=bolt://neo4j:7687`, `NEO4J_USER=neo4j`, `NEO4J_PASSWORD`
- **Redis**: `REDIS_URL=redis://redis:6379` (for caching)

### Agentic Configuration
- **AgenticManager**: `max_iterations=3`, `sufficient_score=0.65`, `enable_multi_tool=True`
- **ToolAwareAgent**: `max_iterations=5` (max reasoning iterations)

### Tool Configuration
- `pyproject.toml` - Project metadata, ruff, black, isort, pytest config
- `.pre-commit-config.yaml` - Pre-commit hooks configuration

## API Architecture

### Main Entry Points
- `app/main.py` - FastAPI application entry point
- `app/api/routes.py` - Primary API routes
- `app/core/config.py` - Configuration settings

### Key Endpoints

**V3 Simplified Architecture (Recommended):**
- `POST /api/v3/conversation/{id}/message/stream` - Streaming with single agentic loop
- `POST /api/v3/conversation/{id}/message` - Non-streaming with single agentic loop
- `GET /api/v3/conversation/{id}/context` - Get conversation history
- `DELETE /api/v3/conversation/{id}/context` - Clear conversation memory
- `GET /api/v3/conversation/health` - Health check

**Legacy V2 Endpoints:**
- `POST /api/query` - Main question answering endpoint (Enhanced RAG)
- `POST /api/query/stream` - Streaming SSE endpoint
- `POST /api/query/async` - Start async query
- `GET /api/query/status/{task_id}` - Check async query status

**Feedback API Endpoints:**
- `POST /api/feedback` - Submit user feedback (rating, comments, tool feedback)
- `GET /api/feedback/summary` - Get aggregated feedback metrics
- `GET /api/feedback/conversation/{id}` - Get feedback for a conversation
- `GET /api/feedback/suggestions` - Get AI-powered improvement suggestions
- `GET /api/feedback/health` - Health check for feedback service

### Enhanced RAG Service
- `app/services/enhanced_rag_service.py` - Core RAG implementation
- `app/services/data_intelligence_service.py` - Multi-source search orchestration
- `app/services/agents/tool_aware_agent.py` - Agentic AI system
- `app/services/response/v3_response_formatter.py` - Rich response formatting for calls/projects

## Data Flow Patterns

### Query Processing Pipeline

**Phase 1: Intent Classification**
The `UnifiedIntentClassifier` analyzes user messages and classifies into:
- `faq`: General questions about EU funding
- `search_calls`: Looking for funding opportunities
- `search_projects`: Looking for funded projects
- `call_specific`: Questions about a specific call
- `proposal_writing`: Help with proposal drafting
- `follow_up`: References previous conversation

**Phase 2: LLM-Driven Complexity Detection**
For `faq` queries, the LLM determines complexity type:
- `simple`: Single source answers (e.g., "What is RIA?")
- `comparison`: Comparing 2+ things (e.g., "Compare EIC vs ERC")
- `analysis`: Explaining WHY (e.g., "Why do some countries succeed more?")
- `multi_source`: Needs multiple info types (e.g., "Eligibility AND success rates")
- `validation`: Verify/confirm (e.g., "Is EIC success rate really 8%?")

**Phase 3: Execution Routing (v2.2)**
- **ALL queries** → Tool-Aware Agent (ReAct) for best results
- Simple queries finish in 1-2 iterations, complex ones use up to 5
- Simple loop is only used as fallback if ToolAwareAgent is unavailable

**Phase 4: Response Generation**
Results are synthesized into final response with:
- Answer text with source citations
- Confidence level indicators (high/medium/low)
- Reasoning trace for complex queries
- Streaming tokens for real-time UX

### Agentic AI Components

**Agentic Manager (Self-Correcting Loop)**
- **File**: `app/services/agents/agentic_manager.py`
- **Purpose**: Handles simpler queries with automatic retry and refinement
- **Max iterations**: 3 self-correction attempts
- **Quality threshold**: 0.65 (sufficient score)

**Tool-Aware Agent (Multi-Tool ReAct)**
- **File**: `app/services/agents/tool_aware_agent.py`
- **Purpose**: Complex queries using ReAct pattern (Reasoning + Acting)
- **Max iterations**: 5 reasoning iterations
- **Features**: Parallel execution, LLM-driven decisions, fallback logic
- **Speculative Execution**: Pre-executes likely tools based on query patterns
- **Plan Caching**: Caches successful query plans in Redis for faster repeat queries
- **Analytics Integration**: Tracks tool usage, latency, and success rates

**Evaluation System (Hybrid Approach)**
- **Rule-based scoring** (fast, free): Result count, relevance, content quality, query coverage, source diversity, freshness
- **LLM evaluation** (accurate, costs tokens): Only for uncertain cases (score 0.4-0.7)
- **Final score**: `(rule_based * 0.3) + (llm_score * 0.7)`
- **Threshold**: Results are sufficient if score ≥ 0.65

**Root Cause Analysis**
When results are insufficient, the system identifies causes:
- `query_too_broad`: Refine with specific terms
- `query_too_narrow`: Broaden the search
- `wrong_source`: Switch data source
- `semantic_mismatch`: Use keyword search instead
- `temporal_mismatch`: Add year filters
- `entity_not_found`: Add entity context

## Data Sources

### 1. Neo4j Graph Database
- **Purpose**: Statistics, patterns, relationships, project discovery
- **Contains**: Programme success rates, country participation data, consortium patterns, funding distributions, organization relationships, project-topic-cluster relationships
- **Queries via**: `GraphSearchService`
- **Project Discovery**: Find similar projects, organization collaborations, cluster-based search

### 2. Supabase (pgvector)
- **Purpose**: Document storage and semantic search
- **Contains**: Horizon Europe regulations, work programmes (2023-2027), guidance documents, call topic descriptions, proposal templates
- **Tables**: `horizon_documents` (document metadata), `document_chunks` (text chunks with embeddings), `funding_calls` (structured call data)
- **Queries via**: `VectorSearchService`

### 3. CORDIS Database (Local PostgreSQL)
- **Purpose**: Funded project information
- **Contains**: All Horizon Europe funded projects (13,865+ projects), project descriptions, objectives, consortium compositions, funding amounts, publications, deliverables
- **Tables**: `projects`, `organizations`, `project_embeddings` (in public schema)
- **Queries via**: `CordisProjectRepository` → `LocalProjectSearchService`
- **Partner Lookup**: `get_project_partners()` queries `organizations` table by project ID to return full consortium with names, countries, roles, activity types, and EC contributions
- **Organization Stats**: `get_organization_stats` tool provides aggregate counts (total projects, coordinator count, total funding) via Neo4j graph with SQL fallback
- **Search**: Full-text search with PostgreSQL tsquery, vector similarity search with pgvector, multi-source fusion with Neo4j using RRF algorithm. Supports sorting by relevance, EC contribution, total cost, or start date.
- **Embeddings**: 13,850 project embeddings (3072-dim vectors via Google gemini-embedding-001) for semantic similarity search. No vector index (pgvector 0.8.0 has 2000-dim limit for HNSW/IVFFlat), uses exact search (~293ms/query).

### 4. EU Portal API
- **Purpose**: Live call data enrichment
- **Used for**: Fetching missing call details, verifying deadlines, getting latest status, enriching local data
- **Queries via**: `CallEnrichmentService`

### 5. Erasmus+ Data Sources
- **Purpose**: Erasmus+ programme guidance and funding calls
- **Contains**:
  - Programme Guide 2026 (537 document chunks with full topic coverage)
  - Annual Work Programme 2026
  - Funding calls (277 calls: 216 closed, 51 open, 10 upcoming)
- **Coverage**: Eligibility, budget/funding rules, quality criteria, mobility, partnerships, deadlines, reporting
- **Key Actions**: KA1 (Learning Mobility), KA2 (Cooperation Partnerships), KA3 (Policy Support), Jean Monnet, Sport
- **Sectors**: Higher Education (HED), VET, Schools (SCH), Adult Education (ADU), Youth (YOU), Sport
- **Funding Model**: Lump sum with unit costs, travel distance bands, and activity-specific rates
- **Queries via**: `VectorSearchService` with `programme="erasmus"` filter

### 6. Creative Europe Data Sources
- **Purpose**: Creative Europe programme guidance and funding calls
- **Contains**:
  - Annual Work Programmes (2021-2026)
  - CulturEU Funding Guide
  - Strand overviews (CULTURE, MEDIA, Cross-sectoral)
  - Green aspects quality assessment guide
  - Funding calls (128 calls synced from EU Portal API)
- **Coverage**: Eligibility, budget/funding rules, evaluation criteria, strand-specific guidance
- **Strands**:
  - CULTURE: European Cooperation Projects (small/medium/large), Networks, Platforms, Literary Translation
  - MEDIA: Development (slate, single, co-dev), Distribution, Training, Festivals, Cinema Networks, Audience Development
  - CROSS-SECTORAL: Creative Innovation Labs, News Media Partnerships, Media Literacy, Music Moves Europe
- **Funding Model**: Lump sum with co-financing requirements (60-80% funding rates)
- **Queries via**: `VectorSearchService` with `programme="creative_europe"` filter
- **Neo4j Graph Data**:
  - `CreativeEuropeStrand` nodes (3): CULTURE, MEDIA, CROSS-SECTORAL
  - `CreativeEuropeAction` nodes (24): All action types with full metadata
  - `CreativeEuropeRegion` nodes (3): Country eligibility by strand
  - Relationships: BELONGS_TO_STRAND, ALLOWS_COORDINATOR_FROM, ALLOWS_PARTNER_FROM, MEMBER_OF

## Hybrid Graph+SQL Architecture

### Partner Discovery Tool (find_experienced_partners)
The Partner Discovery Tool uses a **hybrid Graph+SQL architecture** for optimal results:

**Architecture:**
- **Graph Service (Neo4j)**: Discovers partners through relationship traversal
  - Cluster-based discovery: Organizations active in inferred research clusters
  - 2-hop partner discovery: Partners of partners (extended network)
  - Collaboration network analysis
- **SQL Service (PostgreSQL)**: Keyword-based search with full project details
  - Full-text search on project descriptions and objectives
  - Complete project details (titles, funding, dates)
  - Filtering by country, organization type, role

**Result Fusion (RRF Algorithm):**
- Results from both sources are merged using **Reciprocal Rank Fusion (RRF)**
- RRF constant: `k=60` for balanced ranking
- Score boosts:
  - Partners found in **both sources**: +0.005 (higher confidence)
  - Well-connected **2-hop partners** (5+ shared projects): +0.002
- Deduplication by organization name (normalized)

**SQL Enrichment for Graph-Only Partners:**
- Partners found only via graph lack project details
- Automatic enrichment: fetches project examples from SQL for graph-only partners
- Metadata tracks: `graph_partners_enriched`, `graph_only_count`

**Cluster Inference:**
- Keywords automatically mapped to Horizon Europe clusters (CLUSTER-1 through CLUSTER-6)
- Example: "hydrogen", "solar energy" → CLUSTER-5 (Climate, Energy, Mobility)

**Response Metadata:**
```json
{
  "search_type": "hybrid",
  "sources_used": ["graph", "sql"],
  "graph_partners": 15,
  "sql_partners": 12,
  "merged_total": 20,
  "inferred_clusters": ["CLUSTER-5"],
  "two_hop_partners_added": 8,
  "graph_partners_enriched": 5
}
```

### Budget Benchmark Tool (get_budget_benchmark)
The Budget Benchmark Tool uses a **hybrid Graph+SQL architecture** for comprehensive statistics:

**Architecture:**
- **Graph Service (Neo4j)**: Pre-aggregated cluster statistics, consortium patterns
- **SQL Service (PostgreSQL)**: Keyword filtering, detailed breakdowns, sample projects
- **Weighted Fusion**: Results merged using weighted averaging by project count

**Features:**
- **Cluster Inference**: Keywords automatically mapped to Horizon Europe clusters
- **Parallel Queries**: Graph and SQL queries execute in parallel for performance
- **Org Type Breakdown**: Budget distribution by organization type (HES, REC, PRC, PUB, OTH)
- **Country Breakdown**: Top countries by funding with coordination counts
- **Consortium Context**: Average partners, countries, top coordinator countries

**New Parameters:**
- `include_consortium_context`: Include consortium patterns from graph (default: True)
- `include_org_type_breakdown`: Include budget by org type (default: True)
- `include_country_breakdown`: Include budget by country (default: False)

**Response Metadata:**
```json
{
  "statistics": {...},
  "recommendations": {...},
  "metadata": {
    "search_type": "hybrid",
    "sources_used": ["graph", "sql"],
    "graph_project_count": 496,
    "sql_project_count": 408,
    "inferred_clusters": ["CLUSTER-5"]
  },
  "consortium_context": {...},
  "budget_by_org_type": {...},
  "budget_by_country": {...}
}
```

### Consortium Patterns Tool (get_consortium_patterns)
The Consortium Patterns Tool uses a **hybrid Graph+SQL architecture** for comprehensive consortium analysis:

**Architecture:**
- **Graph Service (Neo4j)**: Pre-aggregated consortium patterns, coordinator analysis
  - Cluster-level consortium statistics (avg partners, countries)
  - Top coordinator countries and organizations
  - Successful consortium templates from funded projects
- **SQL Service (PostgreSQL)**: Keyword-based filtering, detailed breakdowns
  - Organization type distribution
  - Country participation patterns
  - Project-level consortium details
- **Parallel Queries**: Graph and SQL queries execute in parallel via ThreadPoolExecutor

**Features:**
- **Cluster Inference**: Keywords automatically mapped to Horizon Europe clusters
- **Successful Templates**: Real consortium compositions from funded projects
- **Coordinator Analysis**: Which organizations and countries successfully coordinate
- **Weighted Fusion**: Consortium size metrics merged with 60% SQL, 40% Graph weighting

**New Parameters:**
- `include_successful_templates`: Include real consortium templates from graph (default: True)
- `include_coordinator_analysis`: Include coordinator statistics (default: True)
- `topic_keywords`: Keywords to infer cluster (alternative to explicit cluster)

**Response Metadata:**
```json
{
  "success": true,
  "consortium_size": {"avg_partners": 12.5, "avg_countries": 8.2},
  "org_type_distribution": {...},
  "country_distribution": {...},
  "successful_templates": [{...}, {...}],
  "coordinator_analysis": {"top_coordinators": [...]},
  "metadata": {
    "search_type": "hybrid",
    "sources_used": ["graph", "sql"],
    "inferred_clusters": ["CLUSTER-5"]
  }
}
```

### Call History Analysis Tool (analyze_call_history)
The Call History Analysis Tool uses a **hybrid Graph+SQL architecture** for comprehensive funding trend analysis:

**Architecture:**
- **Graph Service (Neo4j)**: Pre-aggregated funding trends, topic landscape
  - Yearly funding trends (project count, total funding)
  - Topic landscape by cluster (topics_by_year)
  - Cluster-level statistics and budget statistics
- **SQL Service (PostgreSQL)**: Detailed filtering, timeline aggregates
  - Calls history with keyword filtering
  - Timeline aggregates by year
  - Funded projects with full details
- **Parallel Queries**: Graph and SQL queries execute in parallel via ThreadPoolExecutor

**Features:**
- **Cluster Inference**: Keywords automatically mapped to Horizon Europe clusters
- **Topic Evolution**: Track how topics have evolved over time within a cluster
- **Trend Detection**: Automatic detection of funding trends (increasing/stable/decreasing)
- **Cluster Statistics**: Comprehensive cluster-level statistics from graph

**New Parameters:**
- `include_topic_evolution`: Include topic landscape analysis from graph (default: True)
- `include_cluster_trends`: Include cluster-level trends from graph (default: True)

**New Methods:**
- `get_cluster_evolution(cluster)`: Analyze how a cluster has evolved over time
- `get_topic_history(topic_pattern)`: Get detailed history for a specific topic

**Response Metadata:**
```json
{
  "success": true,
  "calls_analyzed": 50,
  "projects_funded": 1234,
  "timeline": {"2024": {...}, "2023": {...}},
  "trends": {"funding_trend": "strongly_increasing", "year_over_year_funding_growth": 15.2},
  "topic_landscape": {"total_topics": 100, "top_topics": [...]},
  "cluster_statistics": {"total_projects": 5000, "total_funding": 5.6e9},
  "metadata": {
    "search_type": "hybrid",
    "sources_used": ["graph", "sql"],
    "inferred_clusters": ["CLUSTER-4"]
  }
}
```

### Budget Calculator Tool (calculate_budget)
The Budget Calculator Tool uses a **hybrid Graph+SQL architecture** for budget planning:

**Architecture:**
- **Graph Service (Neo4j)**: Cluster-specific budget statistics, consortium patterns
  - Budget benchmarks by cluster and action type
  - Consortium composition patterns (avg partners, countries)
  - Similar project examples with partner counts
- **SQL Service (PostgreSQL)**: Detailed benchmarks with percentile analysis
  - Budget percentiles (p10, p25, p50, p75, p90)
  - Action-type specific sample projects
- **Parallel Queries**: Graph and SQL queries execute in parallel via ThreadPoolExecutor

**Features:**
- **Cluster Inference**: Keywords automatically mapped to Horizon Europe clusters
- **Cluster Context**: Graph-enhanced consortium recommendations
- **Similar Projects**: Real project examples from both graph and SQL
- **Data-Grounded Ratios**: Cost ratios adjusted based on cluster-specific data

**New Parameters:**
- `cluster`: Cluster code for context (e.g., "CL5", "CLUSTER-5")
- `topic_keywords`: Keywords for cluster inference (alternative to cluster)
- `include_cluster_context`: Include cluster-specific context from graph (default: True)
- `include_similar_projects`: Include similar project examples (default: True)

**Response Metadata:**
```json
{
  "success": true,
  "calculated_budget": {"total_cost": 5000000, "eu_contribution": 5000000, "funding_rate": "100%"},
  "breakdown": {"personnel": {...}, "equipment": {...}, ...},
  "cluster_context": {"avg_partners": 15.6, "avg_countries": 7.9, ...},
  "similar_projects": [{"acronym": "...", "budget": 4500000, ...}],
  "metadata": {
    "search_type": "hybrid",
    "sources_used": ["graph", "sql"],
    "cluster_used": "CLUSTER-5",
    "inferred_clusters": ["CLUSTER-5"]
  }
}
```

### Timeline Generator Tool (generate_timeline)
The Timeline Generator Tool uses a **hybrid Graph+SQL architecture** for timeline planning:

**Architecture:**
- **Graph Service (Neo4j)**: Duration patterns, project examples from similar funded projects
  - Budget statistics used as proxy for project scope
  - Project examples with duration information
- **SQL Service (PostgreSQL)**: Detailed duration statistics
  - Average, min, max, median project durations
  - Project examples with actual start/end dates
- **Parallel Queries**: Graph and SQL queries execute in parallel via ThreadPoolExecutor

**Features:**
- **Cluster Inference**: Keywords automatically mapped to Horizon Europe clusters
- **Cluster-Specific WP Customization**: WP titles adjusted for cluster context (e.g., "Clinical Research & Development" for Health)
- **Duration Context**: Real-data comparison of user's duration vs typical
- **Similar Projects**: Real project examples for reference

**New Parameters:**
- `cluster`: Cluster code for context (e.g., "CL5", "CLUSTER-5")
- `topic_keywords`: Keywords for cluster inference
- `use_real_patterns`: Use real project patterns from graph (default: True)
- `include_similar_projects`: Include similar project examples (default: True)

**Cluster-Specific WP Customizations:**
- CLUSTER-1 (Health): "Clinical Research & Development", "Clinical Validation & Trials"
- CLUSTER-4 (Digital): "AI/ML Model Development", "System Integration & Testing"
- CLUSTER-5 (Climate): "Technology Development & Optimization", "Pilot Demonstration & Scale-up"
- CLUSTER-6 (Food/Bio): "Bio-based Development", "Field Trials & Demonstration"

**Response Metadata:**
```json
{
  "success": true,
  "work_packages": [...],
  "deliverables": [...],
  "milestones": [...],
  "duration_context": {"avg_duration": 41, "your_duration_vs_typical": "within typical range"},
  "similar_projects": [{"acronym": "...", "duration_months": 36, ...}],
  "metadata": {
    "search_type": "hybrid",
    "sources_used": ["graph", "sql"],
    "cluster_used": "CLUSTER-5",
    "templates_customized": true
  }
}
```

### Similar Projects Tool (find_similar_projects / get_similar_funded_projects)
The Similar Projects Tool uses a **hybrid Vector+Graph architecture** for semantic similarity search:

**Architecture:**
- **Vector Service (pgvector)**: Primary semantic similarity via 3072-dim embeddings (Google gemini-embedding-001)
- **Graph Service (Neo4j)**: Context enhancement and reranking signals
  - Cluster-based similar project counts
  - Consortium size and structure analysis
  - Cross-project relationship discovery

**Features:**
- **Cluster Inference**: Automatic cluster detection from description keywords
- **Graph Reranking**: Combined scoring using embedding similarity (75%) + graph signals
- **Context Enhancement**: Adds graph-based project metadata (cluster, similar count)
- **Filtering**: Support for cluster, action type, budget range, year filters

**Combined Scoring Formula:**
```python
combined_score = (
    embedding_score * 0.75 +      # Semantic similarity (primary)
    graph_score * 0.10 +          # Similar projects in cluster
    consortium_score * 0.10 +     # Consortium size signal
    budget_score * 0.05           # Budget size signal
)
```

**New Parameters:**
- `rerank_with_graph`: Enable graph-based reranking (default: True)
- `include_graph_context`: Include graph-enhanced details (default: True)

**Response Metadata:**
```json
{
  "success": true,
  "similar_projects": [...],
  "metadata": {
    "search_type": "hybrid",
    "sources_used": ["vector", "graph"],
    "reranked_with_graph": true,
    "inferred_clusters": ["CLUSTER-5"]
  }
}
```

## Database Systems

### PostgreSQL (Supabase)
- Primary relational database for project metadata
- Vector search capabilities via `pgvector` extension
- Configured via `DATABASE_URL` environment variable

### Neo4j Graph Database
- Relationship-aware queries for projects, organizations, topics
- APOC and Graph Data Science plugins enabled
- Access via `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

### Redis
- Message broker for Celery task queue
- Result backend for async operations
- Query plan caching for repeated patterns

### Database Migrations
New database tables added for analytics and feedback (in `migration/` directory):
- **008_tool_analytics.sql**: `tool_usage_analytics`, `tool_performance_metrics`, `tool_combination_analytics`
- **009_user_feedback.sql**: `response_feedback`, `feedback_insights`

## Development Patterns

### Code Quality
- **Ruff**: Linting and formatting (configured in `pyproject.toml`)
- **Black**: Code formatting with 100-character line length
- **isort**: Import sorting with black compatibility
- **Pre-commit hooks**: Automatic quality checks on commit

### Testing Strategy
- Integration tests for conversation management and memory systems
- Intent detection and classification tests
- Data source verification tests
- Simplified routing tests
- Enhanced description generation tests

### Data Operations
- `scripts/` directory contains helper scripts for data ingestion and setup
- `migration/` directory for database schema migrations
- `cleanup/` directory for system maintenance scripts

**Erasmus+ Data Scripts:**
- `scripts/ingest_erasmus_documents.py` - Ingest Erasmus+ Programme Guide and Work Programmes
- `scripts/sync_erasmus_calls_from_api.py` - Sync Erasmus+ funding calls from EU Portal API
- `scripts/ingest_erasmus_templates.py` - Ingest Erasmus+ application templates (categorizes by Key Action, Sector, Document Type)
- `scripts/ingest_erasmus_to_neo4j.py` - Populate Neo4j with Erasmus+ reference data (ErasmusAction, ErasmusSector, PartnerRegion nodes)

**Creative Europe Data Scripts:**
- `scripts/ingest_creative_europe_documents.py` - Ingest Creative Europe Work Programmes, CulturEU Guide, strand overviews
- `scripts/sync_creative_europe_calls.py` - Sync Creative Europe funding calls from EU Portal API (CREA-CULT, CREA-MEDIA, CREA-CROSS topics)
- `scripts/ingest_creative_europe_to_neo4j.py` - Populate Neo4j with Creative Europe reference data (CreativeEuropeAction, CreativeEuropeStrand, CreativeEuropeRegion nodes)

## Special Considerations

### Multi-Provider AI Support
The system supports multiple LLM providers:
- **OpenAI GPT-4**: High-quality responses
- **Google Gemini**: Cost-effective processing
- **OpenRouter**: Access to multiple models via unified API
- Provider selection via `ai_provider` parameter or `DEFAULT_AI_PROVIDER` env var

### Streaming vs Async Processing
- **Streaming**: Real-time SSE responses via `/api/query/stream`
- **Async**: Background processing via Celery workers with task status polling
- **Synchronous**: Direct responses via `/api/query`

### Professional Context Management
- Domain-specific knowledge injection for Horizon Europe queries
- Short-term memory (12-turn capacity) and long-term memory (summarized context)
- Tool-aware routing based on conversation state

## Common Development Tasks

### Adding New Tools

**Detailed Guide**: See `.claude/skills/mapit-tools/SKILL.md` for comprehensive patterns, templates, and examples.

**Quick Steps**:
1. Create tool file in `app/services/tools/` (use template from `.claude/skills/mapit-tools/templates/tool_template.py`)
2. Export in `app/services/tools/__init__.py`
3. Register tool schema in `app/services/agents/tool_aware_agent.py:_init_tools()`
4. Add router entry in `_execute_single_tool()`
5. Add wrapper method `_tool_my_tool()`
6. Add tests for new tool functionality

**Key Patterns**:
- Use hybrid Graph+SQL architecture for comprehensive results
- Implement RRF fusion for merging ranked results
- Always handle parameter fallbacks (LLMs use inconsistent names)
- Include graceful degradation when services are unavailable

### Extending Data Sources
1. Add data source connector in `app/services/data_intelligence_service.py`
2. Update query planner to include new source
3. Implement result fusion logic
4. Add data ingestion scripts to `scripts/` directory

### Modifying Intent Detection
1. Update classification logic in `app/services/intent_detection_service.py`
2. Add new intent patterns to rule-based fallback
3. Update routing logic in conversation management
4. Add tests for new intent patterns

### Database Schema Changes
1. Create migration script in `migration/` directory
2. Update schema documentation in `docs/DATABASE_SCHEMA_DOCUMENTATION.md`
3. Test migration with existing data
4. Update data ingestion scripts if needed

## Troubleshooting

### Common Issues
- **Import errors**: Ensure virtual environment is activated and dependencies installed
- **API key errors**: Verify environment variables are set correctly
- **Database connection**: Check `DATABASE_URL` format and database accessibility
- **Celery not working**: Ensure Redis is running and accessible
- **Neo4j connection**: Verify `NEO4J_URI` and authentication credentials

### Logs and Monitoring
- Application logs: Check Docker container logs or console output
- Celery worker logs: Monitor worker output for task processing issues
- Database logs: Check PostgreSQL/Neo4j logs for query performance
- Health endpoints: Use `/api/health` for system status

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

### V3 Streaming Response Format
When using the V3 streaming endpoint (`/api/v3/conversation/{id}/message/stream`), events are sent as SSE:
```json
{"type": "status", "stage": "processing", "message": "Processing your query..."}
{"type": "agent_thinking", "content": "Analyzing query: find hydrogen funding calls..."}
{"type": "tool_call", "tool": "search_funding_calls", "args": {"keywords": "hydrogen", "status": "open"}}
{"type": "tool_result", "tool": "search_funding_calls", "result": {"calls_found": 15, ...}}
{"type": "token", "content": "I found **15 funding opportunities**..."}
{"type": "token", "content": "..."}
{"type": "complete", "metadata": {"architecture": "simplified_v3", "tools_used": ["search_funding_calls"]}}
```

**V3 Event Types:**
- `status` - Processing stages
- `agent_thinking` - Agent's reasoning at each iteration
- `tool_call` - When a tool is being called (tool name, arguments)
- `tool_result` - Tool execution result
- `token` - Streaming response text
- `complete` - Final metadata with `architecture="simplified_v3"`
- `error` - Error information

### Legacy Streaming Response Format
When using the legacy endpoint (`/api/query/stream`), progress updates are sent as SSE:
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

## Conversation Stability Architecture

### Overview
The conversation stability system ensures reliable multi-turn conversations by preventing race conditions, maintaining context integrity, and providing comprehensive automated testing.

### Core Stability Modules (`app/core/`)

**ConversationLockManager** (`conversation_lock.py`)
- Per-conversation async locks to prevent race conditions
- Automatic stale lock cleanup (configurable max age)
- Lock timeout support (default: 60 seconds)
- Usage statistics and debugging info

```python
from app.core import get_conversation_lock

async with get_conversation_lock(conversation_id):
    # Process message safely - only one request at a time
    pass
```

**AtomicMessageStorage** (`atomic_storage.py`)
- Atomic message storage with proper error reporting (no silent failures)
- DB (PostgreSQL) as source of truth, Memory (Redis) as cache
- Transaction support with automatic rollback on failure
- Duplicate detection within 5-second window

```python
from app.core import AtomicMessageStorage

storage = AtomicMessageStorage(db_pool, memory_service)
result = await storage.store_message_pair(
    conversation_id=123,
    user_id=1,
    user_message="Hello",
    assistant_message="Hi there!"
)
if not result.success:
    logger.error(f"Storage failed: {result.error}")
```

### Test Agents (`tests/agents/`)

| Agent | Purpose |
|-------|---------|
| `ConversationFlowAgent` | Simulates multi-turn conversations, collects SSE events, validates responses |
| `ContextValidatorAgent` | Validates DB/Redis consistency, detects race conditions |
| `QualityEvaluatorAgent` | Scores responses using LLM-as-judge with 40/25/25/10 rubric |

**ConversationFlowAgent Usage:**
```python
from tests.agents import ConversationFlowAgent

agent = ConversationFlowAgent(base_url="http://localhost:8000")
turn = await agent.send_message("Find hydrogen funding calls")
print(turn.response_text)
print(turn.tools_used)
```

**QualityEvaluatorAgent Scoring Dimensions:**
| Dimension | Points | What to Check |
|-----------|--------|---------------|
| Query Fulfillment | 40 | All query components addressed |
| Specificity | 25 | Numbers, dates, names, call IDs |
| Factual Accuracy | 25 | Correct EU funding information |
| Actionability | 10 | Clear next steps, links, deadlines |

### Running Scenario Tests

```bash
# All conversation scenarios
pytest tests/test_conversation_scenarios.py -v

# Basic flows only
pytest tests/test_conversation_scenarios.py -k "basic" -v

# Follow-up tests only
pytest tests/test_conversation_scenarios.py -k "follow_up" -v

# Concurrent tests only
pytest tests/test_conversation_scenarios.py -k "concurrent" -v

# Context preservation tests
pytest tests/test_conversation_scenarios.py -k "context" -v

# Error recovery tests
pytest tests/test_conversation_scenarios.py -k "error" -v

# With coverage
pytest tests/test_conversation_scenarios.py --cov=app/services/conversation -v
```

### Adding New Scenarios

Scenarios are defined as YAML files in `tests/scenarios/`. Create a new scenario:

```yaml
# tests/scenarios/basic_flows/my_scenario.yaml
name: "My Scenario Name"
description: "What this scenario tests"
tags: ["basic", "calls"]
stop_on_error: true

steps:
  - message: "User query here"
    validations:
      - type: "response_contains"
        name: "check_name"
        patterns: ["expected", "patterns"]
      - type: "tools_used"
        name: "check_tools"
        expected: ["search_funding_calls"]
      - type: "no_error"
        name: "no_errors"
    delay_ms: 0

  - message: "Follow-up question"
    validations:
      - type: "follow_up_resolved"
        name: "resolves_reference"
    delay_ms: 500

final_validations:
  - type: "context_integrity"
    name: "context_preserved"
  - type: "quality_non_degradation"
    name: "quality_stable"
```

**Available Validation Types:**
| Type | Description |
|------|-------------|
| `response_contains` | All patterns must appear in response |
| `response_contains_any` | At least one pattern must appear |
| `tools_used` | Specified tools must be called |
| `min_results` | Tool results must have minimum count |
| `follow_up_resolved` | Message references previous results |
| `context_preserved` | Context from previous turn exists |
| `no_error` | No errors in response |
| `context_integrity` | Final: all messages stored properly |
| `quality_non_degradation` | Final: quality doesn't drop > 15 points |

### Scenario Categories

| Category | Location | Tests |
|----------|----------|-------|
| Basic Flows | `tests/scenarios/basic_flows/` | Funding calls, projects, budgets, timelines |
| Follow-Up | `tests/scenarios/follow_up/` | Numbered references, "tell me more", comparisons |
| Context | `tests/scenarios/context/` | Long conversations (10+ turns), topic switching, memory overflow |
| Error Recovery | `tests/scenarios/error_recovery/` | Invalid references, ambiguous queries, tool timeouts |
| Concurrent | `tests/scenarios/concurrent/` | Rapid messages, simultaneous requests |

### Quality Evaluation Process

**LLM-Based Evaluation:**
```python
from tests.agents import QualityEvaluatorAgent

evaluator = QualityEvaluatorAgent(passing_threshold=75)
score = await evaluator.evaluate_response(query, response)
print(f"Total: {score.total_score}/100")
print(f"Passed: {score.passed}")
```

**Rule-Based Quick Evaluation:**
```python
score = evaluator.quick_evaluate(
    response=response_text,
    expected_patterns=["funding", "deadline", "EUR"],
    min_length=100
)
```

**Conversation Quality Tracking:**
```python
result = await evaluator.evaluate_conversation([
    {"query": "Find calls", "response": "..."},
    {"query": "Tell me more", "response": "..."},
])
print(f"Average: {result.average_score}")
print(f"Trend: {result.trend}")  # "improving", "stable", "degrading"
print(f"Degradation: {result.degradation_detected}")
```

### Debugging Failures

| Failure Type | Agent to Use | What to Check |
|--------------|--------------|---------------|
| Message not stored | `ContextValidatorAgent` | `validate_message_stored()` |
| Context lost | `ContextValidatorAgent` | `validate_context_integrity()` |
| Follow-up fails | `ContextValidatorAgent` | `validate_follow_up_context()` |
| Race condition | `ContextValidatorAgent` | `detect_race_condition()` |
| Quality drop | `QualityEvaluatorAgent` | `evaluate_conversation()` |
| Tool not called | `ConversationFlowAgent` | Check `turn.tools_used` |

### CI/CD Integration

**GitHub Actions Workflow** (`.github/workflows/conversation-tests.yml`):
- Service containers (postgres, redis, neo4j)
- API server startup
- Scenario test execution
- Quality baseline comparison
- Artifact upload for results

**Pre-commit Hook**:
- Runs quick smoke tests for changes to `conversation_manager.py` or `memory_service.py`
- Configure in `.pre-commit-config.yaml`

**Quality Gate**:
- Fails PR if any scenario test fails
- Fails PR if quality score below 75
- Fails PR if race condition detected
- Fails PR if context integrity check fails

### Key Files

| File | Purpose |
|------|---------|
| `app/core/conversation_lock.py` | Per-conversation async locks |
| `app/core/atomic_storage.py` | Atomic message storage |
| `tests/agents/conversation_flow_agent.py` | Multi-turn simulation |
| `tests/agents/context_validator_agent.py` | State validation |
| `tests/agents/quality_evaluator_agent.py` | Quality scoring |
| `tests/test_conversation_scenarios.py` | Main scenario test runner |
| `tests/test_conversation_regression.py` | Regression tests for fixes |
| `tests/conftest.py` | Shared fixtures (43 fixtures) |

## Documentation
- Comprehensive documentation in `docs/` directory including `docs_tracked/SYSTEM_ARCHITECTURE.md`
- Architecture specifications and technical documentation
- Database schema documentation
- Deployment guides and API integration guides
- System use cases with BPMN diagrams
