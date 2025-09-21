# CORDIS Research Projects RAG API

A Retrieval-Augmented Generation (RAG) system for querying European research projects from the CORDIS database.

## Overview

This project implements a specialized RAG system focused on European research projects. It allows users to ask natural language questions about EU-funded research and receive comprehensive answers based on data retrieved from the CORDIS database.

## Key Features

- 🧠 Natural language query processing using GPT-4 and Gemini
- 🔍 Automatic extraction of search terms from user questions
- 🌐 Intelligent search of the CORDIS database
- 📊 Structured data extraction from XML project documentation
- ✨ Answer generation based on retrieved project information
- 🚀 FastAPI interface for easy integration
- ⚡ Async processing with Celery for improved performance
- 🐳 Docker support for easy deployment
- 📋 Demo endpoint for UI testing without making actual CORDIS queries

## Project Structure

```
MAP-IT_SA-1/
├── app/                          # Main application package
│   ├── api/                      # API routes and endpoints
│   │   ├── __init__.py
│   │   └── routes.py             # All API endpoints
│   ├── core/                     # Core configuration
│   │   ├── __init__.py
│   │   └── config.py             # Application settings
│   ├── models/                   # Pydantic models
│   │   ├── __init__.py
│   │   └── schemas.py            # Request/response schemas
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── rag_service.py        # Main RAG implementation
│   │   └── celery_app.py         # Async task processing
│   └── utils/                    # Utility functions
│       └── __init__.py
├── config/                       # Configuration files
│   └── env.example               # Environment variables template
├── docs/                         # Documentation
│   ├── README_CELERY.md
│   ├── schema.ts
│   └── V9_docs.md
├── scripts/                      # Helper scripts
│   ├── setup.sh                  # Environment setup
│   └── start.sh                  # Application startup
├── tests/                        # Test files (to be added)
├── docker-compose.yml            # Docker configuration
├── Dockerfile                    # Docker image definition
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key and/or Gemini API key
- Redis (for Celery, optional)
- PostgreSQL (for local database, optional)

### Quick Setup (Makefile)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd MAP-IT_SA-1
   ```

2. **Configure environment variables:**
   ```bash
   cp config/env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Install dependencies:**
   ```bash
   make install
   make install-dev
   ```

4. **Install git hooks (optional but recommended):**
   ```bash
   make hooks
   ```

5. **Start the application (hot reload):**
   ```bash
   make run-reload
   ```

#### Common Commands
```bash
# Lint and format
make lint
make format

# Run tests
make test

# Start via Docker Compose (includes Redis)
make docker-up
make docker-down
```

### Manual Setup

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp config/env.example .env
   # Edit .env file with your configuration
   ```

4. **Run the application:**
   ```bash
   # Development mode
   uvicorn main:app --reload
   
   # Production mode
   python main.py
   ```

### Docker Deployment

1. **Using Docker Compose (Recommended):**
   ```bash
   # Copy environment template
   cp config/env.example .env
   # Edit .env with your configuration
   
   # Start all services
   docker-compose up -d
   ```

2. **Using Docker only:**
   ```bash
   # Build image
   docker build -t cordis-rag-api .
   
   # Run container
   docker run -p 8000:8000 --env-file .env cordis-rag-api
   ```

## Configuration

### Environment Variables

Key environment variables (see `config/env.example` for full list):

```bash
# AI Provider Configuration
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
DEFAULT_AI_PROVIDER=gemini

# Embedding / Vector Search (optional)
GOOGLE_EMBEDDING_API_KEY=your_google_api_key
EMBEDDING_MODEL=models/text-embedding-004
VECTOR_SEARCH_ENABLED=false

# Database Configuration (optional)
USE_LOCAL_DB=false
DATABASE_URL=postgresql://user:password@localhost:5432/database

# Celery Configuration (optional)
CELERY_BROKER_URL=redis://localhost:6379/0
```

### Pre-commit Hooks
```bash
# Install hooks
make hooks

# Run on all files
make precommit
```

### AI Providers

The application supports multiple AI providers:
- **OpenAI GPT-4** (requires OpenAI API key)
- **Google Gemini** (requires Gemini API key)
- **OpenRouter** (requires OpenRouter API key) - Access to multiple models via a unified API (currently configured for x-ai/grok-4-fast:free)

You can switch between providers per request or set a default provider using the `DEFAULT_AI_PROVIDER` environment variable.

## API Documentation

The API documentation is available at `http://localhost:8000/docs` when the server is running.

### Main Endpoints

- `GET /` - Health check
- `GET /api/health` - Comprehensive health status
- `POST /api/query` - Main question answering endpoint (uses Enhanced RAG)
- `POST /api/query/stream` - Streaming SSE endpoint for questions (uses Enhanced RAG)
- `GET /api/query/stream` - Streaming SSE via GET (frontend convenience)
- `POST /api/query/async` - Start async query
- `GET /api/query/status/{task_id}` - Check async query status
- `POST /api/demo` - Demo endpoint for testing
- `GET /api/providers` - List available AI providers
- `GET /api/database/status` - Database connection status

Note: The separate enhanced router has been removed; its capabilities are integrated into the `/api/query` endpoints.

### Example Usage

#### Basic Query
```bash
curl -X POST "http://localhost:8000/api/query" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What are recent AI projects in healthcare?",
       "max_results": 5,
       "ai_provider": "openrouter"
     }'
```

#### Python Client
```python
import requests

response = requests.post(
    "http://localhost:8000/api/query",
    json={
        "question": "What are the top EU-funded quantum computing projects?",
        "max_results": 10
    }
)

answer = response.json()["answer"]
print(answer)
```

#### JavaScript/TypeScript
```javascript
const response = await fetch('http://localhost:8000/api/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    question: 'What are recent renewable energy projects?',
    max_results: 5
  }),
});

const data = await response.json();
console.log(data.answer);
```

## Features

### Async Processing with Celery

For improved performance, the application supports async processing using Celery:

- Start async queries that don't block the API
- Poll for results using task IDs
- Cancel running tasks
- Automatic scaling with multiple workers

### Database Integration

Optional PostgreSQL integration for:
- Caching CORDIS data locally
- Improved query performance
- Offline operation capabilities

### Multi-Provider AI Support

Switch between different AI providers:
- **OpenAI GPT-4** for high-quality responses
- **Google Gemini** for cost-effective processing
- **OpenRouter** for access to multiple models via a unified API
- Per-request provider selection via the `ai_provider` parameter

## Development

### Project Architecture

The application follows a clean architecture pattern:

- **API Layer** (`app/api/`): FastAPI routes and request handling
- **Core Layer** (`app/core/`): Configuration and settings
- **Models Layer** (`app/models/`): Data models and schemas
- **Services Layer** (`app/services/`): Business logic and external integrations
- **Utils Layer** (`app/utils/`): Helper functions and utilities

### Adding New Features

1. **API Endpoints**: Add new routes in `app/api/routes.py`
2. **Data Models**: Define schemas in `app/models/schemas.py`
3. **Business Logic**: Implement in `app/services/`
4. **Configuration**: Update `app/core/config.py`

### Testing

```bash
# Run tests (when implemented)
pytest tests/

# Run with coverage
pytest tests/ --cov=app
```

## Deployment

### Production Considerations

1. **Security**: 
   - Use strong API keys
   - Configure CORS appropriately
   - Use HTTPS in production

2. **Performance**:
   - Use Redis for Celery
   - Configure database connection pooling
   - Scale workers based on load

3. **Monitoring**:
   - Monitor API response times
   - Track task queue length
   - Monitor database performance

### Scaling

- **Horizontal scaling**: Add more Celery workers
- **Vertical scaling**: Increase worker concurrency
- **Database scaling**: Use read replicas for queries

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure virtual environment is activated
2. **API key errors**: Check environment variables
3. **Database connection**: Verify DATABASE_URL format
4. **Celery not working**: Ensure Redis is running

### Logs

Check application logs for detailed error information:
```bash
# Docker logs
docker-compose logs api

# Direct logs
python main.py  # Logs to console
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or issues:
1. Check the documentation in `docs/`
2. Review existing issues
3. Create a new issue with detailed information