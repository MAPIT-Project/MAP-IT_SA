# Celery-Based Concurrent Processing Setup

This setup enables true concurrent processing of RAG queries using Celery workers with Redis as the message broker. The system connects to your **existing Supabase database** that contains the CORDIS project data.

## Architecture Overview

```
User Request → FastAPI → Redis Queue → Celery Workers → Your Supabase Database
                ↑                           ↓
            Redis Results ← ← ← ← ← ← ← ← ← ←
```

## Prerequisites

1. **Supabase Local Development Environment**: You should have Supabase running locally with CORDIS data
   - Supabase should be running on `localhost:54321` (API)
   - PostgreSQL should be accessible on `localhost:54322` (Database)

2. **Docker and Docker Compose**: For running the Celery infrastructure
   ```bash
   docker --version
   docker-compose --version
   ```

3. **Environment Configuration**: Your `.env` file should contain:
   ```env
   OPENAI_API_KEY=your_openai_key
   GEMINI_API_KEY=your_gemini_key
   DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
   USE_LOCAL_DB=true
   ```

## Quick Start

1. **Start your Supabase instance** (if not already running):
   ```bash
   supabase start
   ```

2. **Build and start the Celery services**:
   ```bash
   docker-compose -f docker-compose.celery.yml up --build
   ```

3. **Verify the services**:
   - FastAPI: http://localhost:8000
   - Redis: Running internally on port 6379

## System Components

### 🚀 **FastAPI Application** (Port 8000)
- Main API server that handles user requests
- Automatically detects Celery availability and routes requests to workers
- Falls back to thread pool if Celery is unavailable

### 🔄 **Celery Workers**
- **Regular Workers**: 4 concurrent workers for standard RAG queries
- **Streaming Workers**: 2 concurrent workers for real-time streaming responses
- Each worker runs in a separate process, enabling true parallelism

### 📊 **Redis Message Broker** (Port 6379)
- Handles message queuing between FastAPI and workers
- Stores task results for retrieval
- Provides task status and monitoring capabilities

### 🗄️ **Your Existing Supabase Database**
- Uses your local Supabase PostgreSQL instance (port 54322)
- No additional database setup required
- Leverages existing CORDIS project data and optimizations

## Testing Concurrent Processing

### Quick Test with curl:
```bash
# Send multiple simultaneous requests
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "AI projects in healthcare", "max_results": 3, "ai_provider": "gemini", "ai_version": "V8"}' &

curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "renewable energy projects", "max_results": 3, "ai_provider": "gemini", "ai_version": "V8"}' &

curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "autonomous vehicle research", "max_results": 3, "ai_provider": "gemini", "ai_version": "V8"}' &
```

### Automated Concurrency Test:
```bash
python test_concurrency_celery.py
```

**Expected Results:**
- ✅ Multiple requests start simultaneously
- ✅ Requests overlap in processing time
- ✅ Time spread between starts < 1.0s
- ✅ All requests complete successfully

## Monitoring and Management

### Real-time Logs:
```bash
# View all services
docker-compose -f docker-compose.celery.yml logs -f

# View specific service
docker-compose -f docker-compose.celery.yml logs -f celery-worker
docker-compose -f docker-compose.celery.yml logs -f api
```

### Task Management:
```bash
# Check worker status
docker-compose -f docker-compose.celery.yml exec celery-worker celery -A celery_app inspect active

# Restart workers
docker-compose -f docker-compose.celery.yml restart celery-worker celery-worker-stream
```

## Scaling Workers

### Add More Workers:
```bash
# Scale regular workers to 6
docker-compose -f docker-compose.celery.yml up -d --scale celery-worker=2

# Scale streaming workers to 3
docker-compose -f docker-compose.celery.yml up -d --scale celery-worker-stream=2
```

### Custom Worker Configuration:
Edit `docker-compose.celery.yml` and modify the `--concurrency` parameter:
```yaml
command: celery -A celery_app worker --loglevel=info --concurrency=8 --queues=rag_queries
```

## Performance Optimization

### Database Connection Tuning:
The system automatically optimizes database connections:
- **Min Connections**: 5 per worker
- **Max Connections**: 50 per worker
- **Connection Pooling**: Enabled by default

### Redis Configuration:
For high-throughput scenarios, tune Redis:
```yaml
redis:
  command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
```

### Worker Memory Management:
```yaml
celery-worker:
  deploy:
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 1G
```

## Troubleshooting

### Common Issues:

1. **Cannot connect to Supabase database**:
   ```bash
   # Check if Supabase is running
   supabase status

   # Restart Supabase if needed
   supabase stop && supabase start
   ```

2. **Workers not processing tasks**:
   ```bash
   # Check worker logs
   docker-compose -f docker-compose.celery.yml logs celery-worker

   # Restart workers
   docker-compose -f docker-compose.celery.yml restart celery-worker
   ```

3. **Redis connection errors**:
   ```bash
   # Check Redis status
   docker-compose -f docker-compose.celery.yml logs redis

   # Test Redis connectivity
   docker-compose -f docker-compose.celery.yml exec redis redis-cli ping
   ```

4. **Import errors in workers**:
   ```bash
   # Rebuild containers with latest code
   docker-compose -f docker-compose.celery.yml up --build
   ```

### Health Checks:
```bash
# API health
curl http://localhost:8000/

# Database connectivity test
python -c "import psycopg2; conn = psycopg2.connect('postgresql://postgres:postgres@localhost:54322/postgres'); print('DB OK')"
```

## Development Mode (Without Docker)

If you prefer to run without Docker while still having your Supabase database:

1. **Install dependencies**:
   ```bash
   pip install celery redis
   ```

2. **Start Redis locally**:
   ```bash
   redis-server
   ```

3. **Start Celery worker**:
   ```bash
   celery -A celery_app worker --loglevel=info
   ```

4. **Start FastAPI**:
   ```bash
   uvicorn fast_api:app --reload
   ```

## API Endpoints

### Query Processing:
```bash
POST /api/query
{
  "question": "Your research question",
  "max_results": 5,
  "ai_provider": "gemini|openai",
  "ai_version": "V2|V3|V4|V5|V6|V7|V8"
}
```

### Streaming (if implemented):
```bash
POST /api/query/stream
{
  "question": "Your research question",
  "max_results": 5,
  "ai_provider": "gemini|openai",
  "ai_version": "V8"
}
```

## Environment Variables

### Required:
- `OPENAI_API_KEY`: Your OpenAI API key
- `GEMINI_API_KEY`: Your Google Gemini API key
- `DATABASE_URL`: PostgreSQL connection to your Supabase instance

### Optional:
- `DEFAULT_AI_PROVIDER`: Default provider (gemini|openai)
- `OPENAI_MODEL`: OpenAI model name
- `GEMINI_MODEL`: Gemini model name
- `USE_LOCAL_DB`: Enable local database mode (default: true)

This setup leverages your existing Supabase infrastructure while adding powerful concurrent processing capabilities through Celery workers.
