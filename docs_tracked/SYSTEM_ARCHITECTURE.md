# MAPIT AI - System Architecture

**Version**: 2.0
**Last Updated**: December 2024

## 1. Overview

MAPIT AI is a research funding intelligence platform designed to assist researchers and organizations in discovering, analyzing, and applying for EU funding programs. The system uses a RAG (Retrieval-Augmented Generation) architecture combined with a knowledge graph to provide accurate, context-aware assistance.

### 1.1 Goals
- **Discovery**: Help researchers find relevant EU funding opportunities
- **Analysis**: Provide insights from successful past proposals and projects
- **Generation**: Assist in writing high-quality, compliant proposals
- **Intelligence**: Offer data-driven recommendations for consortium building

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE LAYER                            │
├─────────────────────────────────────────────────────────────────────────────┤
│   Flask Web GUI (src/gui/app.py)    │    REST API (app/api/) [Planned]      │
│        Port 5000/16000              │         Port 8000                      │
└────────────────────┬────────────────┴───────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────────────────┐
│                            APPLICATION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  RAG Pipeline   │  │ Proposal Writer │  │    Data Intelligence        │  │
│  │  - Retriever    │  │ - Draft Gen     │  │    - Query Planner          │  │
│  │  - Chunker      │  │ - Quality       │  │    - Graph Service          │  │
│  │  - Reranker     │  │ - Compliance    │  │    - Cross-Encoder          │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ Memory Service  │  │  Tool Services  │  │     Agent System            │  │
│  │ - Short-term    │  │ - Budget Calc   │  │     - Agentic Manager       │  │
│  │ - Long-term     │  │ - Partner Find  │  │     - Reflector             │  │
│  │ - Context Mgr   │  │ - Timeline Gen  │  │     - Replanner             │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────────────────┐
│                              DATA ACCESS LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │   CordisProjectRepository   │  │        Query Optimizer              │   │
│  │   - Full-text search        │  │        - Index recommendations      │   │
│  │   - Structured filters      │  │        - Query plan analysis        │   │
│  │   - Change tracking         │  │        - Performance tuning         │   │
│  └─────────────────────────────┘  └─────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────────────────┐
│                             DATA STORAGE LAYER                               │
├────────────────────┬────────────────────┬───────────────────────────────────┤
│   PostgreSQL       │     Dgraph         │        Supabase                   │
│   (Supabase)       │   Knowledge Graph  │        pgvector                   │
│   - projects       │   - Relations      │        - Embeddings               │
│   - organizations  │   - Topics         │        - Vector search            │
│   - publications   │   - Keywords       │                                   │
└────────────────────┴────────────────────┴───────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────────────────┐
│                           EXTERNAL SERVICES                                  │
├────────────────────┬────────────────────┬───────────────────────────────────┤
│   LLM Providers    │   Data Sources     │        Infrastructure             │
│   - Mistral AI     │   - CORDIS API     │        - Redis (Celery)           │
│   - OpenAI         │   - EU Publications│        - Docker                   │
│   - Google Gemini  │   - WikiData       │                                   │
│   - OpenRouter     │                    │                                   │
└────────────────────┴────────────────────┴───────────────────────────────────┘
```

## 3. Component Details

### 3.1 User Interface Layer

#### Flask Web GUI (Current)
- **Location**: `src/gui/app.py`
- **Port**: 5000 (Docker) or 16000 (local)
- **Endpoints**:
  - `GET /` - Home page
  - `POST /query` - Execute RAG query

#### REST API (Planned)
- **Location**: `app/api/`
- **Framework**: FastAPI
- **Port**: 8000
- **Status**: Directory reserved, endpoints not implemented

### 3.2 Application Layer

#### RAG Pipeline
- **CORDISRetriever** (`src/retrieve/CORDISRetriever.py`)
  - Loads and chunks PDF documents
  - Encodes text with SentenceTransformer (all-mpnet-base-v2)
  - Retrieves relevant context via cosine similarity
  - Integrates with Mistral AI for response generation

#### Proposal Writing Services
- **Location**: `app/services/proposal_writing/`
- **Components**:
  - `proposal_ai_service.py` - Core AI service
  - `draft_generator.py` - Automated drafts
  - `quality_improver.py` - Quality enhancement
  - `budget_assistant.py` - Budget calculations
  - `compliance_checker.py` - Compliance validation
  - `gap_analysis_service.py` - Gap identification
  - `criteria_matcher.py` - Criteria matching
  - `template_service.py` - Template management
  - `submission_exporter.py` - Export functionality

#### Memory Services
- **Location**: `app/services/memory/`
- **Components**:
  - `short_term_memory.py` - Session-based context
  - `long_term_memory.py` - Persistent storage
  - `context_manager.py` - Context orchestration
  - `rolling_summarizer.py` - Conversation summarization

#### Tool Services
- **Location**: `app/services/tools/`
- **Components**:
  - `budget_calculator.py` - Budget estimation
  - `partner_discovery.py` - Partner identification
  - `similar_projects.py` - Project similarity
  - `consortium_patterns.py` - Consortium analysis
  - `timeline_generator.py` - Timeline creation
  - `call_history.py` - Historical call tracking

### 3.3 Data Access Layer

#### CordisProjectRepository
- **Location**: `app/services/data/cordis_repository.py`
- **Features**:
  - Connection pooling (5-20 connections)
  - Full-text search with PostgreSQL tsquery
  - Structured filtering (programme, dates, budget, countries)
  - Organization enrichment via JOINs
  - Change tracking for incremental sync

#### Query Optimizer
- **Location**: `app/services/data/query_optimizer.py`
- **Features**:
  - SQL query analysis
  - Index recommendations
  - Query plan caching

### 3.4 Data Storage Layer

#### PostgreSQL (via Supabase)
- **Tables**:
  - `projects` - CORDIS project data
  - `organizations` - Project participants
  - `cordis_processed.publications_enriched`
  - `cordis_processed.deliverables_enriched`
  - `cordis_processed.ingestion_batches`
  - `cordis_processed.change_log`

#### Dgraph Knowledge Graph
- **Port**: 9080
- **Schema** (from `src/devops/CORDISProjectSchemaInit.py`):
  - Project entity with 19+ properties
  - Topic-based relations
  - Keyword similarity edges

#### Supabase pgvector
- **Purpose**: Vector embeddings for semantic search
- **Status**: Configured, integration in progress

### 3.5 External Services

#### LLM Providers
| Provider | Model | Usage |
|----------|-------|-------|
| Mistral AI | mistral-large-latest | Primary RAG responses |
| OpenAI | gpt-4-turbo | Proposal writing |
| Google Gemini | gemini-flash-latest | Default provider |
| OpenRouter | grok-4-fast | Fallback |

#### Data Sources
- **CORDIS**: Primary source for EU project data
- **EU Publications**: Call documents and guidelines
- **WikiData**: Entity enrichment (planned)

## 4. Data Flow

### 4.1 Query Processing Flow
```
User Query
    │
    ▼
┌─────────────────────┐
│ Flask /query POST   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ CORDISRetriever     │
│   prompting()       │
└──────────┬──────────┘
           │
           ├──────────────────────────────┐
           │                              │
           ▼                              ▼
┌─────────────────────┐    ┌─────────────────────┐
│ get_base_information│    │ get_CORDIS_topic_   │
│ (PDF embeddings)    │    │ info (Graph query)  │
└──────────┬──────────┘    └──────────┬──────────┘
           │                          │
           └──────────────┬───────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │ Context Assembly    │
              │ - Base info         │
              │ - Topic info        │
              │ - Answer history    │
              └──────────┬──────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │ send_to_LLM()       │
              │ (Mistral API)       │
              └──────────┬──────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │ Response to User    │
              └─────────────────────┘
```

### 4.2 ETL Data Flow
```
CORDIS CSV/API
    │
    ▼
┌─────────────────────┐
│ CORDISProjectReader │
│   load_projects()   │
└──────────┬──────────┘
           │
           ├──────────────────────────────┐
           │                              │
           ▼                              ▼
┌─────────────────────┐    ┌─────────────────────┐
│ PostgreSQL          │    │ Dgraph              │
│ (projects table)    │    │ (knowledge graph)   │
└─────────────────────┘    └──────────┬──────────┘
                                      │
                                      ▼
                          ┌─────────────────────┐
                          │ MAPITGraphBuilder   │
                          │ (add relations)     │
                          └─────────────────────┘
```

## 5. Security Considerations

### 5.1 Current Implementation
- API keys stored in `.env` file (gitignored)
- Database connection via environment variables
- Basic input validation on query endpoint

### 5.2 Required Improvements
- [ ] Input sanitization for SQL injection prevention
- [ ] Rate limiting on API endpoints
- [ ] Authentication/authorization layer
- [ ] GDPR compliance for EU users
- [ ] API key rotation mechanism
- [ ] Secure session management

## 6. Performance Considerations

### 6.1 Current Optimizations
- Database connection pooling
- Query plan caching
- Context length management (128k token limit)
- Answer history limited to 10 entries

### 6.2 Required Improvements
- [ ] Embedding caching
- [ ] Response caching
- [ ] Async processing for long operations
- [ ] Batch processing for bulk queries
- [ ] Index optimization for PostgreSQL

## 7. Deployment Architecture

### 7.1 Docker Deployment
```yaml
services:
  flask_app:
    - Port 5000
    - Mounts: src/gui
    - Depends: Dgraph

  dgraph:
    - Port 9080 (gRPC)
    - Volume: dgraph_data
```

### 7.2 Production Considerations
- [ ] WSGI server (Gunicorn) instead of Flask dev server
- [ ] Load balancer for horizontal scaling
- [ ] Health check endpoints
- [ ] Monitoring and alerting
- [ ] Log aggregation

## 8. Integration Points

### 8.1 Current Integrations
- CORDIS API for project data
- Mistral AI API for LLM responses
- Dgraph for graph queries
- PostgreSQL for structured data

### 8.2 Planned Integrations
- OpenAI API (configured, partial use)
- Google Gemini API (configured)
- Neo4j (configured, not active)
- EU Funding Portal API
- WikiData for entity enrichment

## 9. Appendix

### 9.1 Key Environment Variables
See `.env` file for complete list. Critical variables:
- `DATABASE_URL`: PostgreSQL connection
- `DGRAPH_URL`: Graph database endpoint
- `MAPIT_LLM_KEY`: Mistral AI key
- `OPENAI_API_KEY`, `GEMINI_API_KEY`: AI providers

### 9.2 Related Documentation
- `docs/architecture.md` - Original architecture notes
- `docs/deployment.md` - Deployment instructions
- `docs/data-analytics.md` - ETL documentation
- `CLAUDE.md` - Development conventions
