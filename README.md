# MAP-IT: Multi-Programme EU Funding Research Assistant

A production-grade Retrieval-Augmented Generation (RAG) system for querying European Union funding programmes. The system implements sophisticated multi-source intelligent search, agentic AI capabilities, and comprehensive tooling for **6 EU funding programmes**: Horizon Europe, Erasmus+, Creative Europe, EU4Health, Digital Europe, and LIFE.

## Features

- **Multi-Programme Support**: Coverage of 6 EU funding programmes with specialized tools
- **Multi-Source Search**: Combines graph search (Neo4j), vector search (pgvector), and full-text search
- **Agentic AI System**: Self-correcting tool orchestrator with ReAct pattern reasoning
- **42 Specialized Tools**: Statistics, comparisons, project discovery, eligibility checks, proposal support
- **Semantic Search**: AI-powered project similarity using 3072-dim embeddings (13,850+ projects)
- **Real-time Streaming**: SSE-based responses with progress updates
- **Conversation Memory**: Short-term and long-term context management

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (via Supabase or local)
- Redis
- Neo4j 5.x

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MAP-IT_SA
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or: venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   make install      # Production dependencies
   make install-dev  # Development dependencies (includes ruff, black, pytest)
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database credentials
   ```

5. **Start services**
   ```bash
   make docker-up
   ```

6. **Run the API**
   ```bash
   make run          # Production
   make run-reload   # Development with hot reload
   ```

The API will be available at `http://localhost:8000`.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `OPENAI_API_KEY` | OpenAI API key (alternative provider) | No |
| `OPENROUTER_API_KEY` | OpenRouter API key (alternative provider) | No |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_KEY` | Supabase service key | Yes |
| `NEO4J_URI` | Neo4j bolt URI | Yes |
| `NEO4J_USER` | Neo4j username | Yes |
| `NEO4J_PASSWORD` | Neo4j password | Yes |
| `REDIS_URL` | Redis connection URL | Yes |
| `GOOGLE_EMBEDDING_API_KEY` | Google Embedding API key | Yes |

## API Endpoints

### V3 Conversation API (Recommended)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v3/conversation/{id}/message/stream` | POST | Streaming response with SSE |
| `/api/v3/conversation/{id}/message` | POST | Non-streaming response |
| `/api/v3/conversation/{id}/context` | GET | Get conversation history |
| `/api/v3/conversation/{id}/context` | DELETE | Clear conversation memory |
| `/api/v3/conversation/health` | GET | Health check |

### V4 Proposal Session API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/proposal/session` | POST | Create proposal writing session |
| `/api/proposal/session/{id}/stream` | POST | Streaming proposal assistance |
| `/api/proposal/session/{id}/state` | GET | Get session state |
| `/api/proposal/session/{id}/export` | GET | Export proposal draft |

### Feedback API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/feedback` | POST | Submit user feedback |
| `/api/feedback/summary` | GET | Get aggregated metrics |
| `/api/feedback/suggestions` | GET | AI-powered improvement suggestions |

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER QUERY                                      │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     TOOL-AWARE AGENT (ReAct Pattern)                        │
│                                                                             │
│  1. THINK: Analyze query, decide which tools to use                        │
│  2. ACT: Call tools (can run multiple in parallel)                         │
│  3. OBSERVE: Review results from tools                                     │
│  4. REPEAT: If more info needed, think again and call more tools           │
│  5. CONCLUDE: Synthesize final answer from all gathered data               │
│                                                                             │
│  • 42 tools available • Up to 5 reasoning iterations • Plan caching        │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Neo4j     │  │  Supabase   │  │   CORDIS    │  │   EU Portal API     │ │
│  │   Graph     │  │  pgvector   │  │  Projects   │  │   (enrichment)      │ │
│  │             │  │             │  │ + Vectors   │  │                     │ │
│  │ Statistics  │  │ Documents   │  │ 13,850+     │  │ Live call data      │ │
│  │ Patterns    │  │ Embeddings  │  │ projects    │  │                     │ │
│  │             │  │             │  │ 3072-dim    │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Available Tools (42)

**Horizon Europe Tools:**
- `get_programme_statistics` - Success rates, funding amounts
- `get_country_statistics` - Participation stats by country
- `analyze_geographic_diversification` - Country group analysis
- `compare_programmes` - Compare programmes side-by-side
- `search_documents` - Search official EU documents
- `search_funding_calls` - Find open/upcoming calls
- `get_call_details` - Get details for a specific call
- `search_projects` - Search CORDIS funded projects (LOCAL-FIRST)
- `get_project_details` - Get project details with partners
- `get_project_partners` - Get full partner list
- `get_organization_stats` - Organization aggregate statistics
- `find_similar_projects` - Find similar by topic/consortium
- `find_semantically_similar_projects` - AI-powered semantic search
- `find_organization_projects` - All projects for an organization
- `get_collaboration_network` - Organization partnerships
- `search_by_cluster` - Find projects by research cluster
- `get_budget_benchmark` - Budget statistics from funded projects
- `get_consortium_patterns` - Consortium composition analysis
- `find_experienced_partners` - Find experienced organizations
- `get_similar_funded_projects` - Semantic similarity for research
- `analyze_call_history` - Historical funding patterns
- `calculate_budget` - Generate detailed budget breakdowns
- `generate_timeline` - Create project timelines with work packages
- `score_proposal_section` - Evaluate proposal section quality
- `score_full_proposal` - Evaluate complete proposal
- `quick_quality_check` - Quick quality assessment
- `validate_budget` - Validate budget against EU rules
- `show_cached_projects` - Show recently viewed projects

**Erasmus+ Tools:**
- `check_erasmus_eligibility` - Check eligibility by action/sector
- `calculate_erasmus_budget` - Calculate Erasmus+ budgets
- `search_erasmus_templates` - Search Programme Guide

**Creative Europe Tools:**
- `check_creative_europe_eligibility` - Check eligibility by strand/action
- `calculate_creative_europe_budget` - Calculate Creative Europe budgets
- `search_creative_europe_templates` - Search CulturEU Guide

**EU4Health Tools:**
- `check_eu4health_eligibility` - Check eligibility by action/org type
- `search_eu4health_templates` - Search EU4Health documents

**Digital Europe Tools:**
- `check_digital_europe_eligibility` - Check eligibility across 6 objectives

**LIFE Tools:**
- `check_life_eligibility` - Check eligibility across 4 sub-programmes
- `search_life_templates` - Search LIFE Programme documents

**Cross-Programme Tools:**
- `search_all_programmes` - Search across all 6 programmes
- `recommend_programmes` - Recommend best programmes for project
- `get_programme_info` - Get detailed programme information

## Development

### Commands

```bash
make help         # Show available commands
make install      # Install production dependencies
make install-dev  # Install development dependencies
make run          # Run API server
make run-reload   # Run API with hot reload
make docker-up    # Start Docker services
make docker-down  # Stop Docker services
make lint         # Run ruff linter
make format       # Format code (ruff, isort, black)
make test         # Run tests
make precommit    # Run pre-commit hooks
make hooks        # Install git hooks
make clean        # Clean cache files
```

### Docker Services

The `docker-compose.yml` defines:
- `api` - FastAPI application (port 8000)
- `redis` - Message broker (port 6379)
- `celery-worker` - Regular query processing
- `celery-worker-stream` - Streaming query processing
- `neo4j` - Graph database (ports 7474, 7687)

### Testing

```bash
# Run all tests
make test

# Run specific test files
pytest tests/test_integration_v3.py
pytest tests/test_conversation_scenarios.py
pytest tests/quality/test_scenario_001_search_open_calls_basic.py

# Run with coverage
pytest --cov=app tests/
```

### Code Quality

The project uses:
- **Ruff** - Fast Python linter
- **Black** - Code formatter (100 char line length)
- **isort** - Import sorting
- **Pre-commit** - Git hooks for automated checks

## Project Structure

```
MAP-IT_SA/
├── app/
│   ├── api/                    # API routes
│   │   ├── conversation_routes_v3.py  # V3 Conversation API
│   │   ├── proposal_session_routes.py # V4 Proposal Session API
│   │   └── feedback_routes.py  # Feedback endpoints
│   ├── services/
│   │   ├── agents/             # Agentic AI components
│   │   │   ├── tool_aware_agent.py    # ReAct agent
│   │   │   ├── agentic_manager.py     # Self-correcting loop
│   │   │   └── result_evaluator.py    # Quality scoring
│   │   ├── analytics/          # Tool usage analytics
│   │   ├── cache/              # Query plan caching
│   │   ├── data_intelligence/  # Graph search, query planning
│   │   ├── embedding/          # Incremental embedding updates
│   │   ├── feedback/           # User feedback collection
│   │   ├── conversation/       # Conversation management
│   │   ├── memory/             # Short/long-term memory
│   │   ├── proposal_writing/   # AI proposal assistance
│   │   ├── response/           # Response formatting
│   │   └── tools/              # Tool implementations (42 tools)
│   ├── core/                   # Configuration, dependencies
│   ├── models/                 # Pydantic schemas
│   └── main.py                 # FastAPI entry point
├── data/
│   ├── cordis/                 # CORDIS project data
│   ├── shared_documents/       # Horizon Europe documents
│   └── manual_uploads/         # User-uploaded documents
├── docs/                       # Documentation
│   ├── prd/                    # Product Requirements Documents
│   └── implementation/         # Implementation history
├── docs_tracked/               # Comprehensive documentation (single source of truth)
│   ├── SYSTEM_ARCHITECTURE.md  # Complete system architecture
│   ├── FRONTEND_STREAMING_V3_SPEC.md  # V3 streaming API
│   ├── CONVERSATION_STABILITY_ARCHITECTURE.md  # Race condition prevention
│   └── MANUAL_TEST_SCENARIOS.md  # Testing procedures
├── migration/                  # Database migrations
├── scripts/                    # Helper scripts (43 files)
├── tests/                      # Test files
├── k8s/                        # Kubernetes manifests
├── docker-compose.yml          # Docker configuration
├── Makefile                    # Development commands
├── requirements.txt            # Production dependencies
└── requirements-dev.txt        # Development dependencies
```

## Key Capabilities

### Multi-Programme Search
Search for funding opportunities across all 6 EU programmes in a single query.

```
User: "Find funding opportunities for renewable energy research"
Response: Lists calls from Horizon Europe, LIFE, and Digital Europe
```

### Eligibility Checking
Check organization eligibility for specific programme actions and sectors.

```
User: "Is my SME eligible for Erasmus+ KA2 partnerships?"
Response: Detailed eligibility assessment with requirements
```

### Call Search
Find open and upcoming funding calls with local-first search and API enrichment.

```
User: "Find hydrogen funding calls"
Response: Lists calls with type icons, deadlines, budgets, and apply links
```

### Project Search
Search 13,850+ funded CORDIS projects using full-text, graph, and semantic search.

```
User: "Show me AI healthcare projects from Germany"
Response: Lists matching projects with details, funding amounts, consortia
```

### Comparisons
Compare programmes, countries, or funding types using multi-tool reasoning.

```
User: "Compare EIC Accelerator vs ERC success rates"
Response: Side-by-side comparison with statistics and explanations
```

### Proposal Support
Get budget benchmarks, consortium patterns, and find potential partners.

```
User: "What's the typical budget for a Climate RIA?"
Response: Budget statistics (mean, median, min, max) from funded projects
```

### Proposal Writing
AI-powered proposal drafting with section-by-section assistance.

```
User: "Help me write a Horizon Europe proposal for AI in healthcare"
Response: Structured proposal with excellence, impact, and implementation sections
```

## Data Sources

| Source | Purpose | Data |
|--------|---------|------|
| **Neo4j** | Statistics, patterns, relationships | Success rates, consortium patterns, org networks for all 6 programmes |
| **Supabase (pgvector)** | Document search | Regulations, work programmes, guidance docs for 6 programmes |
| **CORDIS PostgreSQL** | Project data | 13,850+ funded projects with 3072-dim embeddings |
| **EU Portal API** | Live enrichment | Call details, deadlines, status updates for all programmes |

## Streaming Response Format

V3 streaming events (SSE):

```json
{"type": "status", "stage": "processing", "message": "Processing..."}
{"type": "agent_thinking", "content": "Analyzing query: find hydrogen funding calls..."}
{"type": "tool_call", "tool": "search_funding_calls", "args": {"keywords": "hydrogen"}}
{"type": "tool_result", "tool": "search_funding_calls", "result": {"calls_found": 15}}
{"type": "token", "content": "I found **15 funding opportunities**..."}
{"type": "complete", "metadata": {"architecture": "simplified_v3", "tools_used": [...]}}
```

## Configuration

### Agentic Settings

```python
# agentic_manager.py
AgenticManager(
    max_iterations=3,        # Max self-correction attempts
    sufficient_score=0.65,   # Quality threshold (0-1)
    enable_multi_tool=True   # Enable ReAct agent
)

# tool_aware_agent.py
ToolAwareAgent(
    max_iterations=5         # Max reasoning iterations
)
```

### Embedding Settings

| Setting | Value |
|---------|-------|
| Model | Google gemini-embedding-001 |
| Dimensions | 3072 |
| Index | Exact search (no index - exceeds HNSW/IVFFlat limits) |

## Performance Optimizations

- **Query Plan Caching**: Redis-based caching for repeated query patterns
- **Speculative Execution**: Pre-executes likely tools based on query patterns
- **Parallel Tool Calls**: Independent tool calls run simultaneously
- **RRF Fusion**: Reciprocal Rank Fusion combines multi-source results
- **Hybrid Architecture**: Graph+SQL with weighted result fusion

## Documentation

Comprehensive documentation is available in `docs_tracked/` (single source of truth):

| Document | Description |
|----------|-------------|
| `SYSTEM_ARCHITECTURE.md` | Complete system architecture with all 42 tools |
| `FRONTEND_STREAMING_V3_SPEC.md` | V3 streaming API and frontend integration |
| `CONVERSATION_STABILITY_ARCHITECTURE.md` | Race condition prevention and context management |
| `MANUAL_TEST_SCENARIOS.md` | Testing procedures and scenarios |
| `IMPROVEMENT_ROADMAP.md` | Future improvements and planned features |

For developer quick reference, see `CLAUDE.md`.

## Contributing

1. Install development dependencies: `make install-dev`
2. Install git hooks: `make hooks`
3. Create a feature branch
4. Make changes and ensure tests pass: `make test`
5. Format code: `make format`
6. Run linter: `make lint`
7. Submit a pull request

## License

[Specify license here]

## Support

For issues and feature requests, please open an issue on the repository.
