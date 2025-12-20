# CLAUDE.md - MAPIT AI Project Conventions

## Project Overview

MAPIT AI is a research funding intelligence platform that helps researchers discover EU funding opportunities, analyze successful proposals, and generate high-quality funding applications. The system uses RAG (Retrieval-Augmented Generation) with a knowledge graph to provide accurate, context-aware assistance for Horizon Europe and other EU funding programs.

## Technology Stack

### Backend
- **Language**: Python 3.12+
- **Web Framework**: Flask (legacy GUI), FastAPI (planned API layer)
- **Database**:
  - PostgreSQL (primary data store via Supabase)
  - Dgraph (knowledge graph for project relations)
  - Neo4j (alternative graph database configured)
- **Vector Search**: Supabase pgvector
- **Task Queue**: Celery with Redis

### AI/ML
- **LLM Providers**:
  - Mistral AI (primary - mistral-large-latest)
  - OpenAI GPT-4-turbo (fallback)
  - Google Gemini (default for proposal writing)
  - OpenRouter (Grok-4 fallback)
- **Embeddings**: SentenceTransformer (all-mpnet-base-v2)
- **RAG**: Custom implementation with hybrid search

### Data Sources
- CORDIS (Community Research and Development Information Service)
- EU Publications Office
- Horizon Europe call documents

## Project Structure

```
MAP-IT_SA/
├── app/                    # Main application code
│   ├── api/               # REST API endpoints (planned)
│   ├── core/              # Core configuration
│   ├── models/            # Data models (planned)
│   └── services/          # Business logic services
│       ├── data/          # Data access layer (cordis_repository, query_optimizer)
│       ├── proposal_writing/  # AI proposal assistance (compiled)
│       ├── rag/           # RAG components (compiled)
│       ├── memory/        # Conversation memory (compiled)
│       └── tools/         # Proposal tools (compiled)
├── src/                   # Legacy/core source code
│   ├── etl/              # Data ingestion pipelines
│   ├── retrieve/         # RAG retrieval logic
│   ├── gui/              # Flask web interface
│   └── devops/           # Infrastructure scripts
├── tests/                 # Test suite
├── docs/                  # Documentation
├── docs_tracked/          # Tracked improvement docs
└── data/                  # Data files (gitignored)
```

## Coding Conventions

### Python Style
- Use type hints for all function signatures
- Use dataclasses or Pydantic models for DTOs
- Follow PEP 8 style guidelines
- Maximum line length: 100 characters
- Use docstrings for public functions (Google style)

### Naming Conventions
- **Classes**: PascalCase (e.g., `CordisProjectRepository`)
- **Functions/Methods**: snake_case (e.g., `search_projects`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DGRAPH_URL`)
- **Files**: snake_case.py or PascalCase.py for classes

### Error Handling
- Use logging module (not print statements)
- Log errors with full context: `logger.error(f"Failed to X: {e}")`
- Return empty collections instead of None where appropriate
- Use specific exceptions, not bare except clauses

### Database Conventions
- Use connection pooling for PostgreSQL
- Always use parameterized queries (prevent SQL injection)
- Close cursors and return connections to pool
- Use DictCursor for readable results

## Environment Configuration

Required environment variables (see `.env`):
- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`, `GEMINI_API_KEY`: AI provider keys
- `DGRAPH_URL`: Graph database URL (default: localhost:9080)
- `MAPIT_LLM_KEY`: Mistral AI API key
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`: Supabase configuration

## Running the Application

### Development
```bash
# Start Flask GUI
cd src/gui && python app.py

# Or via Docker
docker-compose up --build
```

### Testing
```bash
python -m pytest tests/
```

## Key Files

- `src/retrieve/CORDISRetriever.py` - Core RAG retrieval logic
- `app/services/data/cordis_repository.py` - CORDIS data access layer
- `src/etl/CORDISProjectReader.py` - ETL for CORDIS data
- `src/gui/app.py` - Flask web application

## Important Notes

1. **API Keys**: Never commit API keys. Use `.env` file (gitignored)
2. **Compiled Services**: Many services in `app/services/` are only available as `.pyc` files
3. **Graph Database**: System supports both Dgraph and Neo4j - check configuration
4. **Embeddings**: Uses `all-mpnet-base-v2` - requires ~500MB download on first run
5. **Security**: The `.env` file contains sensitive keys - never commit

## Common Tasks

### Adding a new EU Program
1. Add program data to knowledge graph via ETL
2. Update topic_ids_and_titles.py with new topics
3. Add program-specific prompts in proposal writing services

### Updating CORDIS Data
1. Download new data from CORDIS API
2. Run ETL pipeline: `python src/etl/CORDISProjectReader.py`
3. Rebuild graph relations: `python src/etl/MAPITGraphBuilder.py`

### Adding a new API Endpoint
1. Create route in `app/api/`
2. Implement service logic in `app/services/`
3. Add tests in `tests/`
