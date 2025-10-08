# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a sophisticated Retrieval-Augmented Generation (RAG) system for querying European research projects from the CORDIS database and Horizon Europe funding opportunities. The system has evolved from a basic RAG implementation to an advanced context-aware AI system with memory management, enhanced search capabilities, and intelligent conversation handling.

## Common Development Commands

### Setup and Installation
```bash
# Install dependencies
make install
make install-dev

# Setup environment
cp config/env.example .env
# Edit .env with your API keys

# Install git hooks (recommended)
make hooks
```

### Running the Application
```bash
# Development with hot reload
make run-reload

# Production mode
make run

# Docker Compose (includes Redis)
make docker-up
make docker-down
```

### Testing and Quality
```bash
# Run tests
make test

# Lint code
make lint

# Format code
make format

# Run pre-commit checks
make precommit
```

### Specific Test Commands
```bash
# Test system capabilities
python test_system_capabilities.py

# Test AI intent service
python test_ai_intent_service.py

# Test basic functionality
python test_basic_functionality.py

# Test search queries
python test_search_queries.py

# Test v2 system
python test_v2_system.py
```

## Architecture Overview

### High-Level Architecture

The system follows a layered architecture with multiple specialized services:

1. **API Layer** (`app/api/`): FastAPI routes and endpoints
2. **Core Layer** (`app/core/`): Configuration and settings management
3. **Services Layer** (`app/services/`): Business logic and external integrations
4. **Models Layer** (`app/models/`): Data models and schemas
5. **Utils Layer** (`app/utils/`): Helper functions and utilities

### Key Service Components

#### 1. Enhanced RAG System (`app/services/enhanced_rag_service.py`)
- **Purpose**: Main orchestrator for query processing and response generation
- **Features**: Integrated vector search, call-specific functionality, enhanced search capabilities
- **Key Methods**: `answer_question()`, `handle_project_query()`, `handle_call_query()`

#### 2. Memory Management System (`app/services/memory/`)
- **Short-Term Memory**: Redis-based recent conversation turns
- **Long-Term Memory**: PostgreSQL summaries and extracted facts
- **Context Manager**: Optimizes context window usage
- **Rolling Summarizer**: AI-powered conversation summarization

#### 3. Conversation Management (`app/services/conversation/`)
- **Conversation Manager**: Main orchestrator for v2 system
- **Context-Aware Processing**: Maintains conversation flow and entity tracking
- **Professional Context AI**: Advanced response generation

#### 4. Vector Search and Embedding (`app/services/rag/`)
- **Hybrid Search**: Combines vector similarity with keyword search
- **Intelligent Chunking**: Semantic document chunking with overlap
- **Response Generator**: Grounded response generation with citations

#### 5. Intent Detection (`app/services/intent_service.py`, `app/services/ai_intent_service.py`)
- **Multi-Level Intent Detection**: AI-powered with rule-based fallbacks
- **Context-Aware Routing**: Routes queries to appropriate handlers
- **Call-Specific Detection**: Specialized detection for funding calls

#### 6. Call Document System (`app/services/call_document_service.py`)
- **Comprehensive Call Documentation**: Processes and indexes call documents
- **Enhanced Search**: Advanced search with facet analysis
- **Status Tracking**: Real-time call status and deadline tracking

### API Routes Structure

#### Main Routes (`app/api/routes.py`)
- `/api/query` - Main RAG endpoint
- `/api/query/stream` - Streaming SSE endpoint
- `/api/query/async` - Async query processing
- `/api/demo` - Demo endpoint for testing

#### Conversation Routes v2 (`app/api/conversation_routes_v2.py`)
- `/api/v2/conversation/{id}/message` - Context-aware messaging
- `/api/v2/conversation/{id}/message/stream` - Streaming conversation
- `/api/v2/conversation/{id}/memory` - Memory statistics
- `/api/v2/conversation/health` - Health check

#### Document Routes (`app/api/document_routes.py`)
- Document upload and processing endpoints
- Vector search management
- Document indexing operations

#### Call Document Routes (`app/api/call_document_routes.py`)
- Call-specific document retrieval
- Status and deadline information
- Advanced call search

## Configuration Management

### Environment Variables (Key Settings)
```bash
# AI Provider Configuration
DEFAULT_AI_PROVIDER=gemini
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
OPENROUTER_API_KEY=your_openrouter_key

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/db
USE_LOCAL_DB=true
REDIS_HOST=localhost
REDIS_PORT=6379

# Vector Search Configuration
VECTOR_SEARCH_ENABLED=false
GOOGLE_EMBEDDING_API_KEY=your_google_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_key

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### AI Provider Support
- **OpenAI GPT-4**: High-quality responses
- **Google Gemini**: Cost-effective processing (default)
- **OpenRouter**: Multiple models via unified API (x-ai/grok-4-fast:free)

## Key Features and Capabilities

### 1. Multi-Modal Search
- **Vector Search**: Semantic similarity using embeddings
- **Keyword Search**: Traditional text-based search
- **Hybrid Search**: Combines both approaches with reranking
- **Faceted Search**: Advanced filtering and categorization

### 2. Context-Aware Conversation
- **Memory Management**: Hybrid short-term and long-term memory
- **Entity Tracking**: Maintains context across conversation turns
- **Reference Resolution**: Handles pronouns and contextual references
- **Follow-up Suggestions**: Intelligent next-step recommendations

### 3. Enhanced Call Processing
- **Call-Specific Queries**: Handles specific call identifiers (HORIZON-CL4-2024-DATA-01-01)
- **Status Tracking**: Real-time deadline and status information
- **Enhanced Descriptions**: Rich call descriptions with metadata
- **Portal Integration**: Direct links to EU Funding Portal

### 4. Professional Response Generation
- **Grounded Responses**: All responses based on retrieved context
- **Citation Tracking**: Automatic source attribution
- **Confidence Scoring**: Response quality indicators
- **Hallucination Prevention**: Strict context adherence

## Development Patterns

### Adding New Features
1. **API Endpoints**: Add routes in appropriate `app/api/` module
2. **Business Logic**: Implement in `app/services/`
3. **Data Models**: Define schemas in `app/models/schemas.py`
4. **Configuration**: Update `app/core/config.py`
5. **Tests**: Add comprehensive tests in `tests/` directory

### Error Handling Patterns
- Use structured error responses with proper HTTP status codes
- Implement graceful fallbacks for external service failures
- Log errors with context for debugging
- Provide user-friendly error messages

### Performance Considerations
- Use async processing for long-running operations
- Implement caching for frequently accessed data
- Optimize database queries with proper indexing
- Monitor and optimize response times

## Testing Strategy

### Test Categories
1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Service interaction testing
3. **System Tests**: End-to-end functionality testing
4. **Performance Tests**: Load and timing testing

### Key Test Files
- `test_system_capabilities.py` - Overall system health
- `test_ai_intent_service.py` - Intent detection accuracy
- `test_v2_system.py` - V2 conversation system
- `test_search_queries.py` - Search functionality

## Docker and Deployment

### Docker Compose Services
- **api**: Main FastAPI application
- **redis**: Message broker and caching
- **celery-worker**: Background task processing
- **celery-worker-stream**: Streaming query processing

### Production Considerations
- Use proper secret management for API keys
- Configure database connection pooling
- Implement monitoring and logging
- Set up backup strategies

## Troubleshooting

### Common Issues
1. **Redis Connection**: Check Redis service status
2. **Database Connection**: Verify DATABASE_URL format
3. **API Key Errors**: Validate environment variables
4. **Memory Issues**: Check Redis memory limits
5. **Search Performance**: Optimize vector search configuration

### Debug Commands
```bash
# Check system health
curl http://localhost:8000/api/health

# Test intent service
python debug_intent_service.py

# Test database connection
python -c "from app.core.config import settings; print(settings.database_url)"

# Check Redis connection
redis-cli ping
```

## Migration Notes

### V1 to V2 Migration
The system has migrated from a basic RAG implementation to an advanced context-aware system:
- **Old System**: Simple RAG with limited context
- **New System**: Advanced memory management, enhanced search, professional responses

### Key Changes
- New conversation routes (`/api/v2/conversation/`)
- Enhanced memory system with Redis and PostgreSQL
- Improved intent detection with AI-powered analysis
- Advanced call processing with status tracking

## Future Development

### Planned Enhancements
1. **User Authentication**: Add user-specific memory and preferences
2. **Advanced Analytics**: Conversation insights and usage patterns
3. **Multi-Language Support**: Expand beyond English queries
4. **Enhanced UI**: Improve frontend integration
5. **Performance Optimization**: Further reduce response times

### Scaling Considerations
- Horizontal scaling with multiple Celery workers
- Database read replicas for improved query performance
- CDN integration for static content
- Load balancing for high-traffic scenarios