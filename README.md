# MAP-IT: Intelligent EU Funding Research Assistant

A production-grade Retrieval-Augmented Generation (RAG) system for querying European research projects from the CORDIS database. The system implements sophisticated multi-source intelligent search, agentic AI capabilities, and comprehensive tooling for Horizon Europe research project queries.

## Features

- **Multi-Source Search**: Combines graph search (Neo4j), vector search (pgvector), and full-text search
- **Agentic AI System**: Self-correcting tool orchestrator with ReAct pattern reasoning
- **20 Specialized Tools**: Statistics, comparisons, project discovery, proposal support
- **Semantic Search**: AI-powered project similarity using 768-dim embeddings (13,850+ projects)
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
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |
| `SUPABASE_SERVICE_KEY` | Supabase service key | Yes |
| `NEO4J_URI` | Neo4j bolt URI | Yes |
| `NEO4J_USER` | Neo4j username | Yes |
| `NEO4J_PASSWORD` | Neo4j password | Yes |
| `REDIS_URL` | Redis connection URL | Yes |
| `GOOGLE_EMBEDDING_API_KEY` | Google Embedding API key | No |

## API Endpoints

### V3 API (Recommended)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v3/conversation/{id}/message/stream` | POST | Streaming response with SSE |
| `/api/v3/conversation/{id}/message` | POST | Non-streaming response |
| `/api/v3/conversation/{id}/context` | GET | Get conversation history |
| `/api/v3/conversation/{id}/context` | DELETE | Clear conversation memory |
| `/api/v3/conversation/health` | GET | Health check |

### Legacy V2 API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/query` | POST | Main question answering |
| `/api/query/stream` | POST | Streaming SSE endpoint |
| `/api/query/async` | POST | Start async query |
| `/api/query/status/{task_id}` | GET | Check async query status |

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
│  • 20 tools available • Up to 5 reasoning iterations • Plan caching        │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Neo4j     │  │  Supabase   │  │   CORDIS    │  │   EU Portal API     │ │
│  │   Graph     │  │  pgvector   │  │  Projects   │  │   (enrichment)      │ │
│  │             │  │             │  │ + Vectors   │  │                     │ │
│  │ Statistics  │  │ Documents   │  │ 13,865+     │  │ Live call data      │ │
│  │ Patterns    │  │ Embeddings  │  │ projects    │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Available Tools (20)

**Statistics Tools:**
- `get_programme_statistics` - Success rates, funding amounts for a programme
- `get_country_statistics` - Participation stats for a country

**Comparison Tools:**
- `compare_programmes` - Compare two programmes side-by-side

**Document Tools:**
- `search_documents` - Search official EU documents

**Call Tools:**
- `search_funding_calls` - Find open/upcoming calls
- `get_call_details` - Get details for a specific call

**Project Tools:**
- `search_projects` - Search CORDIS for funded projects
- `get_project_details` - Get details for a project
- `find_similar_projects` - Find similar projects by topic/consortium/cluster
- `find_semantically_similar_projects` - AI-powered semantic similarity search
- `find_organization_projects` - Find all projects for an organization
- `get_collaboration_network` - Get organization collaboration networks
- `search_by_cluster` - Find projects in a research cluster

**Proposal Support Tools:**
- `get_budget_benchmark` - Budget statistics from similar funded projects
- `get_consortium_patterns` - Consortium composition analysis
- `find_experienced_partners` - Find organizations with relevant experience
- `get_similar_funded_projects` - Semantic similarity for proposal research
- `analyze_call_history` - Historical funding pattern analysis

**Proposal Planning Tools:**
- `calculate_budget` - Generate detailed budget breakdowns
- `generate_timeline` - Create project timelines with work packages

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
pytest tests/test_integration_v2.py
pytest tests/test_intent_detection_only.py

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
│   │   ├── routes.py           # Legacy V2 routes
│   │   ├── conversation_routes_v3.py  # V3 API
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
│   │   ├── memory/             # Conversation memory
│   │   ├── rag/                # RAG components
│   │   ├── response/           # Response formatting
│   │   └── tools/              # Tool implementations
│   ├── core/                   # Configuration, dependencies
│   ├── models/                 # Pydantic schemas
│   └── main.py                 # FastAPI entry point
├── data/
│   ├── cordis/                 # CORDIS project data
│   ├── shared_documents/       # Horizon Europe documents
│   └── manual_uploads/         # User-uploaded documents
├── docs/                       # Documentation
├── migration/                  # Database migrations
├── scripts/                    # Helper scripts
├── tests/                      # Test files
├── docker-compose.yml          # Docker configuration
├── Makefile                    # Development commands
├── requirements.txt            # Production dependencies
└── requirements-dev.txt        # Development dependencies
```

## Key Capabilities

### FAQ Answering
Answer questions about eligibility, rules, and requirements for EU funding programmes.

```
User: "Can Switzerland participate in Horizon Europe?"
Response: "Yes, Switzerland can participate as an Associated Country..."
```

### Call Search
Find open and upcoming funding calls with local-first search and API enrichment.

```
User: "Find hydrogen funding calls"
Response: Lists calls with type icons, deadlines, budgets, and apply links
```

### Project Search
Search 13,865+ funded CORDIS projects using full-text, graph, and semantic search.

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

## Data Sources

| Source | Purpose | Data |
|--------|---------|------|
| **Neo4j** | Statistics, patterns, relationships | Success rates, consortium patterns, org networks |
| **Supabase (pgvector)** | Document search | Regulations, work programmes, guidance docs |
| **CORDIS PostgreSQL** | Project data | 13,865+ funded projects with embeddings |
| **EU Portal API** | Live enrichment | Call details, deadlines, status updates |

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
| Model | Google text-embedding-004 |
| Dimensions | 768 |
| Index | IVFFlat (100 lists) |

## Performance Optimizations

- **Query Plan Caching**: Redis-based caching for repeated query patterns
- **Speculative Execution**: Pre-executes likely tools based on query patterns
- **Parallel Tool Calls**: Independent tool calls run simultaneously
- **RRF Fusion**: Reciprocal Rank Fusion combines multi-source results

## Documentation

Detailed documentation is available in the `docs/` directory:
- `SYSTEM_ARCHITECTURE.md` - Full architecture documentation
- `STREAMING_API_GUIDE_FOR_FRONTEND.md` - Frontend integration guide
- `DATABASE_SCHEMA_DOCUMENTATION.md` - Database schema details
- `technical_specification.md` - Technical specifications

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
