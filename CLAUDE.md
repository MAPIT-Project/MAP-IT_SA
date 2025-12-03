# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **production-grade Retrieval-Augmented Generation (RAG) system** for querying European research projects from the CORDIS database. The system implements sophisticated multi-source intelligent search, agentic AI capabilities, and comprehensive tooling for Horizon Europe research project queries.

## Key Architecture Components

### Core Services Architecture
- **Multi-Source Intelligent Search**: Combines graph search (Neo4j), vector search (Supabase), and keyword search
- **Agentic AI System**: Tool orchestrator with reflection, evaluation, and replanning capabilities
- **Intent Detection Pipeline**: Multi-stage classification with LLM-based and rule-based fallbacks
- **Data Intelligence Service**: Query planning, multi-source execution, and result fusion
- **Conversation Management**: Short-term/long-term memory with professional context injection

### V3 Simplified Architecture (Recommended)
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
- **Use multiple tools** to gather information from different sources (16 tools available)
- **Reason iteratively** to answer complex comparison and analysis questions
- **Synthesize answers** from graph databases, vector stores, and external APIs

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
- `data_intelligence/` - Graph search, query planning, cross-encoder reranking
- `rag/` - RAG-specific components (retrievers, chunkers, generators)
- `tools/` - Tool orchestration for multi-step reasoning (18 tools available)
- `call_extractors/` - Funding call document processing
- `conversation/` - Conversation management and memory
- `memory/` - Short/long-term memory systems
- `proposal_writing/` - AI-powered proposal assistance
- `response/` - Response generation utilities and V3 formatter

### API Layer Organization (`app/api/`)
- `routes.py` - Legacy V2 API routes
- `conversation_routes_v3.py` - V3 simplified architecture routes

### Available Tools (18 Tools)
The system has 18 tools available for the multi-tool agent:

**Statistics Tools:**
- `get_programme_statistics`: Success rates, funding amounts for a programme
- `get_country_statistics`: Participation stats for a country

**Comparison Tools:**
- `compare_programmes`: Compare two programmes side-by-side

**Document Tools:**
- `search_documents`: Search official EU documents

**Call Tools:**
- `search_funding_calls`: Find open/upcoming calls
- `get_call_details`: Get details for a specific call

**Project Tools:**
- `search_projects`: Search CORDIS for funded projects (LOCAL-FIRST: PostgreSQL + Neo4j + Vector, no API calls)
- `get_project_details`: Get details for a project
- `find_similar_projects`: Find projects similar to a given project (by topic, consortium, or cluster)
- `find_semantically_similar_projects`: Find projects semantically similar using AI embeddings (understands objectives)
- `find_organization_projects`: Find all projects an organization participated in
- `get_collaboration_network`: Get collaboration network showing which organizations partner together
- `search_by_cluster`: Find projects in a specific research cluster (e.g., Climate, Health, Digital)

**Proposal Support Tools (Group 2):**
- `get_budget_benchmark`: Get budget statistics from similar funded projects (by action type, cluster, year)
- `get_consortium_patterns`: Analyze consortium composition patterns (org types, countries, sizes)
- `find_experienced_partners`: Find organizations with experience in specific research areas
- `get_similar_funded_projects`: Find semantically similar funded projects using AI embeddings
- `analyze_call_history`: Analyze historical funding patterns for topics/clusters (timeline, trends, action types)

### Key Services

**Core Services:**
- `ConversationManager` (`conversation_manager.py`): Main orchestrator
- `AgenticManager` (`agentic_manager.py`): Self-correcting loop
- `ToolAwareAgent` (`tool_aware_agent.py`): Multi-tool reasoning
- `UnifiedIntentClassifier` (`unified_intent_classifier.py`): Intent detection

**Data Services:**
- `DataIntelligenceService` (`data_intelligence_service.py`): Graph + Vector search
- `VectorSearchService` (`vector_search_service.py`): Semantic search
- `GraphSearchService` (`graph_service.py`): Neo4j queries
- `LocalCallSearchService` (`local_call_search_service.py`): Call search
- `LocalProjectSearchService` (`local_project_search_service.py`): Multi-source project search (PostgreSQL + Neo4j + Vector embeddings)
- `CordisProjectRepository` (`data/cordis_repository.py`): PostgreSQL project data access

**Support Services:**
- `QueryPlanner` (`query_planner.py`): LLM-based query planning
- `CrossEncoderReranker` (`cross_encoder_reranker.py`): Result reranking
- `CallEnrichmentService` (`call_enrichment_service.py`): API enrichment
- `MemoryService` (`memory_service.py`): Conversation memory

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
- **AI Models**: `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-flash-latest` (used by all agentic components)
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
- **Search**: Full-text search with PostgreSQL tsquery, vector similarity search with pgvector, multi-source fusion with Neo4j using RRF algorithm
- **Embeddings**: 13,850 project embeddings (768-dim vectors via Google text-embedding-004) for semantic similarity search

### 4. EU Portal API
- **Purpose**: Live call data enrichment
- **Used for**: Fetching missing call details, verifying deadlines, getting latest status, enriching local data
- **Queries via**: `CallEnrichmentService`

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
1. Create tool in `app/services/tools/` directory
2. Register tool in `app/services/tools/__init__.py`
3. Update tool orchestrator in `app/services/agents/tool_aware_agent.py`
4. Add tests for new tool functionality

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

## Documentation
- Comprehensive documentation in `docs/` directory including `docs_tracked/SYSTEM_ARCHITECTURE.md`
- Architecture specifications and technical documentation
- Database schema documentation
- Deployment guides and API integration guides
- System use cases with BPMN diagrams