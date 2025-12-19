# MAP-IT Improvement Roadmap

> **Document Purpose:** Comprehensive guide for AI agents to improve MAP-IT to production-ready, premium-grade status
> **Created:** December 19, 2025
> **Target Audience:** AI agents with access only to CLAUDE.md and SYSTEM_ARCHITECTURE.md

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
3. [Priority 1: Critical Fixes](#priority-1-critical-fixes)
4. [Priority 2: Reliability & Robustness](#priority-2-reliability--robustness)
5. [Priority 3: Performance Optimization](#priority-3-performance-optimization)
6. [Priority 4: Feature Completeness](#priority-4-feature-completeness)
7. [Priority 5: Premium Features](#priority-5-premium-features)
8. [Priority 6: Enterprise Readiness](#priority-6-enterprise-readiness)
9. [Implementation Guidelines](#implementation-guidelines)
10. [Success Metrics](#success-metrics)

---

## Executive Summary

MAP-IT is a sophisticated RAG system for EU research funding (Horizon Europe). It currently provides:
- Multi-source intelligent search (Neo4j graph + PostgreSQL + pgvector)
- Agentic AI with 20 tools using ReAct pattern
- Proposal writing assistance with AI evaluation
- V3 conversation API and V4 proposal session API

**Goal:** Transform MAP-IT into a production-ready, premium-grade application that research managers can rely on for all Horizon Europe funding activities.

**Key Areas for Improvement:**
1. **Reliability** - Error handling, fallbacks, monitoring
2. **Performance** - Response times, caching, optimization
3. **Completeness** - Missing features, edge cases, integrations
4. **Premium Features** - Advanced analytics, collaboration, exports
5. **Enterprise** - Security, scalability, compliance

---

## Current State Assessment

### Strengths
- Comprehensive tool ecosystem (20 tools)
- Hybrid Graph+SQL architecture for accurate data
- 13,865 CORDIS projects with 98% embedding coverage
- Sophisticated proposal writing services (30+ modules)
- SSE streaming for real-time responses

### Weaknesses
- No graceful degradation when services fail
- Limited error messages for users
- No comprehensive health monitoring
- Single-server session management
- Missing official EU template exports
- No multi-user collaboration

### Technical Debt
- Some hardcoded timeouts and limits
- Inconsistent error handling patterns
- Missing retry logic for transient failures
- No circuit breaker for external APIs

---

## Priority 1: Critical Fixes

These must be fixed immediately for production readiness.

### 1.1 Comprehensive Error Handling

**Problem:** Errors propagate as generic 500 responses without actionable information.

**Solution:** Implement structured error handling across all services.

**Files to modify:**
- `app/api/conversation_routes_v3.py`
- `app/api/proposal_session_routes.py`
- `app/services/agents/tool_aware_agent.py`
- `app/services/conversation/conversation_manager.py`

**Implementation:**

```python
# Create: app/core/exceptions.py

class MapItError(Exception):
    """Base exception for all MAP-IT errors."""
    def __init__(self, message: str, error_code: str, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

class ServiceUnavailableError(MapItError):
    """External service is unavailable."""
    pass

class DataNotFoundError(MapItError):
    """Requested data not found."""
    pass

class RateLimitError(MapItError):
    """Rate limit exceeded."""
    pass

class ValidationError(MapItError):
    """Input validation failed."""
    pass

class ToolExecutionError(MapItError):
    """Tool failed to execute."""
    pass
```

```python
# Create: app/api/error_handlers.py

from fastapi import Request
from fastapi.responses import JSONResponse

async def mapit_exception_handler(request: Request, exc: MapItError):
    return JSONResponse(
        status_code=get_status_code(exc.error_code),
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "suggestion": get_user_suggestion(exc.error_code)
        }
    )

def get_user_suggestion(error_code: str) -> str:
    suggestions = {
        "NEO4J_UNAVAILABLE": "Graph database is temporarily unavailable. Try again in a few minutes.",
        "EMBEDDING_FAILED": "Could not generate embeddings. Falling back to keyword search.",
        "RATE_LIMITED": "Too many requests. Please wait before trying again.",
        "CALL_NOT_FOUND": "This call ID was not found. Check the ID or search for similar calls.",
    }
    return suggestions.get(error_code, "An unexpected error occurred. Please try again.")
```

**Register in main.py:**
```python
from app.core.exceptions import MapItError
from app.api.error_handlers import mapit_exception_handler

app.add_exception_handler(MapItError, mapit_exception_handler)
```

### 1.2 Service Health Monitoring

**Problem:** No way to know if dependent services are healthy before they fail.

**Solution:** Implement comprehensive health checks with dependency status.

**Create:** `app/api/health_routes.py`

```python
from fastapi import APIRouter
from typing import Dict, Any
import asyncio

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("")
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check for all services."""
    checks = await asyncio.gather(
        check_postgres(),
        check_neo4j(),
        check_redis(),
        check_gemini(),
        check_embedding_service(),
        return_exceptions=True
    )

    services = {
        "postgres": format_check_result(checks[0]),
        "neo4j": format_check_result(checks[1]),
        "redis": format_check_result(checks[2]),
        "gemini": format_check_result(checks[3]),
        "embeddings": format_check_result(checks[4]),
    }

    all_healthy = all(s["status"] == "healthy" for s in services.values())
    critical_healthy = services["postgres"]["status"] == "healthy"

    return {
        "status": "healthy" if all_healthy else ("degraded" if critical_healthy else "unhealthy"),
        "services": services,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.1.0"
    }

@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe - checks if app can serve traffic."""
    # Check critical dependencies only
    postgres_ok = await check_postgres_quick()
    return {"ready": postgres_ok}

@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe - checks if app is alive."""
    return {"alive": True}
```

### 1.3 Graceful Degradation

**Problem:** When Neo4j or Redis fails, the entire request fails.

**Solution:** Implement fallback paths for all non-critical services.

**Modify:** `app/services/conversation/conversation_manager.py`

```python
async def process_message_v3(self, ...):
    """Process with graceful degradation."""

    # Check service availability
    services_status = await self._check_services()

    if not services_status["postgres"]:
        raise ServiceUnavailableError(
            "Database unavailable",
            "POSTGRES_UNAVAILABLE"
        )

    # Proceed with available services
    context = {
        "neo4j_available": services_status["neo4j"],
        "redis_available": services_status["redis"],
        "embeddings_available": services_status["embeddings"],
    }

    # Agent will adapt based on available services
    result = await self.tool_aware_agent.process_query(
        query=user_message,
        context=conversation_context,
        available_services=context  # NEW: Pass service availability
    )
```

**Modify:** `app/services/agents/tool_aware_agent.py`

```python
def _get_available_tools(self, available_services: Dict[str, bool]) -> List[str]:
    """Return only tools that can work with available services."""

    tools = ["search_documents", "search_funding_calls"]  # Always available (PostgreSQL)

    if available_services.get("neo4j"):
        tools.extend([
            "get_programme_statistics",
            "get_country_statistics",
            "compare_programmes",
            "get_collaboration_network",
            "search_by_cluster"
        ])

    if available_services.get("embeddings"):
        tools.extend([
            "find_semantically_similar_projects",
            "get_similar_funded_projects"
        ])

    # Hybrid tools work with degraded functionality
    tools.extend([
        "search_projects",  # Falls back to SQL-only
        "get_budget_benchmark",  # Falls back to SQL-only
        "find_experienced_partners",  # Falls back to SQL-only
    ])

    return tools
```

### 1.4 Input Validation

**Problem:** Invalid inputs can cause cryptic errors deep in the stack.

**Solution:** Validate all inputs at API boundary with clear error messages.

**Create:** `app/api/validators.py`

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List

class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    include_context: bool = True

    @validator('message')
    def message_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty or whitespace only')
        return v.strip()

class SearchCallsRequest(BaseModel):
    keywords: str = Field(..., min_length=2, max_length=500)
    status: Optional[str] = Field(None, pattern="^(open|upcoming|closed|all)$")
    cluster: Optional[str] = Field(None, pattern="^(CL[1-6]|CLUSTER-[1-6])$")
    year: Optional[int] = Field(None, ge=2021, le=2030)
    limit: int = Field(10, ge=1, le=100)

class ProposalSessionRequest(BaseModel):
    call_id: str = Field(..., pattern="^HORIZON-[A-Z0-9-]+$")
    title: str = Field(..., min_length=5, max_length=500)
    proposal_type: str = Field(..., pattern="^(RIA|IA|CSA|COFUND|ERC|MSCA)$")
```

---

## Priority 2: Reliability & Robustness

### 2.1 Retry Logic with Exponential Backoff

**Problem:** Transient failures cause immediate errors.

**Solution:** Implement retry decorator for all external calls.

**Create:** `app/core/retry.py`

```python
import asyncio
from functools import wraps
from typing import Type, Tuple
import logging

logger = logging.getLogger(__name__)

def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Async retry decorator with exponential backoff."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise

                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)

            raise last_exception
        return wrapper
    return decorator

# Usage example:
@async_retry(max_attempts=3, retryable_exceptions=(ConnectionError, TimeoutError))
async def call_external_api(url: str):
    ...
```

### 2.2 Circuit Breaker for External APIs

**Problem:** Failed external services can cause cascading timeouts.

**Solution:** Implement circuit breaker pattern.

**Create:** `app/core/circuit_breaker.py`

```python
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(f"Circuit {self.name} is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        )

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Require 3 successes to close
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"Circuit {self.name} closed")

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self.success_count = 0

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} opened after {self.failure_count} failures")

# Global circuit breakers
eu_portal_circuit = CircuitBreaker("eu_portal", failure_threshold=3, recovery_timeout=120)
neo4j_circuit = CircuitBreaker("neo4j", failure_threshold=5, recovery_timeout=60)
gemini_circuit = CircuitBreaker("gemini", failure_threshold=3, recovery_timeout=30)
```

### 2.3 Request Timeout Management

**Problem:** Long-running requests can hang indefinitely.

**Solution:** Implement consistent timeout handling.

**Create:** `app/core/timeouts.py`

```python
import asyncio
from functools import wraps
from typing import TypeVar, Callable
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class TimeoutConfig:
    """Centralized timeout configuration."""

    # API layer timeouts
    REQUEST_TIMEOUT = 120  # Max time for entire request
    STREAM_TIMEOUT = 300   # Max time for streaming requests

    # Service layer timeouts
    LLM_CALL_TIMEOUT = 60  # Single LLM call
    TOOL_EXECUTION_TIMEOUT = 30  # Single tool execution
    DATABASE_QUERY_TIMEOUT = 10  # Database queries
    EXTERNAL_API_TIMEOUT = 15  # External API calls

    # Agent timeouts
    AGENT_ITERATION_TIMEOUT = 45  # Single agent iteration
    AGENT_TOTAL_TIMEOUT = 180  # Total agent processing time

async def with_timeout(
    coro,
    timeout: float,
    error_message: str = "Operation timed out"
):
    """Execute coroutine with timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Timeout after {timeout}s: {error_message}")
        raise TimeoutError(error_message)

def timeout_decorator(seconds: float, error_message: str = None):
    """Decorator to add timeout to async functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            msg = error_message or f"{func.__name__} timed out after {seconds}s"
            return await with_timeout(func(*args, **kwargs), seconds, msg)
        return wrapper
    return decorator
```

### 2.4 Database Connection Pool Management

**Problem:** Connection exhaustion under load.

**Solution:** Proper connection pool management with monitoring.

**Modify:** `app/core/database.py`

```python
import psycopg2.pool
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class DatabasePool:
    """Managed database connection pool with monitoring."""

    def __init__(
        self,
        dsn: str,
        min_connections: int = 2,
        max_connections: int = 20
    ):
        self.pool = psycopg2.pool.ThreadedConnectionPool(
            min_connections,
            max_connections,
            dsn
        )
        self.active_connections = 0
        self.total_requests = 0
        self.failed_requests = 0

    @contextmanager
    def get_connection(self, timeout: float = 5.0):
        """Get connection from pool with timeout."""
        conn = None
        try:
            conn = self.pool.getconn()
            if conn is None:
                self.failed_requests += 1
                raise ConnectionError("No available connections in pool")

            self.active_connections += 1
            self.total_requests += 1
            yield conn

        except Exception as e:
            self.failed_requests += 1
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.active_connections -= 1
                self.pool.putconn(conn)

    def get_stats(self) -> dict:
        """Get pool statistics for monitoring."""
        return {
            "active_connections": self.active_connections,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "failure_rate": self.failed_requests / max(self.total_requests, 1)
        }
```

---

## Priority 3: Performance Optimization

### 3.1 Response Time Optimization

**Target:** < 3 seconds for simple queries, < 10 seconds for complex queries.

**Strategies:**

#### 3.1.1 Parallel Tool Execution

**Modify:** `app/services/agents/tool_aware_agent.py`

```python
async def _execute_tools_parallel(
    self,
    tool_calls: List[ToolCall],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute independent tools in parallel."""

    # Group tools by dependencies
    independent_tools = []
    dependent_tools = []

    for tool in tool_calls:
        if self._has_dependencies(tool, tool_calls):
            dependent_tools.append(tool)
        else:
            independent_tools.append(tool)

    # Execute independent tools in parallel
    results = {}
    if independent_tools:
        parallel_results = await asyncio.gather(
            *[self._execute_single_tool(t, context) for t in independent_tools],
            return_exceptions=True
        )
        for tool, result in zip(independent_tools, parallel_results):
            if isinstance(result, Exception):
                results[tool.tool_name] = {"error": str(result)}
            else:
                results[tool.tool_name] = result

    # Execute dependent tools sequentially
    for tool in dependent_tools:
        results[tool.tool_name] = await self._execute_single_tool(tool, context)

    return results
```

#### 3.1.2 Query Result Caching

**Create:** `app/services/cache/result_cache.py`

```python
import hashlib
import json
from typing import Any, Optional
from datetime import timedelta
import redis

class ResultCache:
    """Cache for expensive query results."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = timedelta(hours=1)

    def _make_key(self, query_type: str, params: dict) -> str:
        """Generate cache key from query parameters."""
        param_str = json.dumps(params, sort_keys=True)
        hash_val = hashlib.md5(param_str.encode()).hexdigest()[:12]
        return f"result:{query_type}:{hash_val}"

    async def get(self, query_type: str, params: dict) -> Optional[Any]:
        """Get cached result."""
        key = self._make_key(query_type, params)
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def set(
        self,
        query_type: str,
        params: dict,
        result: Any,
        ttl: timedelta = None
    ):
        """Cache result."""
        key = self._make_key(query_type, params)
        ttl = ttl or self.default_ttl
        self.redis.setex(key, ttl, json.dumps(result))

    async def invalidate(self, query_type: str, params: dict):
        """Invalidate cached result."""
        key = self._make_key(query_type, params)
        self.redis.delete(key)

# Cache TTLs by query type
CACHE_TTLS = {
    "programme_statistics": timedelta(hours=24),  # Rarely changes
    "country_statistics": timedelta(hours=24),
    "funding_calls": timedelta(hours=1),  # Deadlines change
    "projects": timedelta(hours=6),
    "budget_benchmark": timedelta(hours=12),
    "consortium_patterns": timedelta(hours=12),
}
```

#### 3.1.3 Database Query Optimization

**Create:** `app/services/data/query_optimizer.py`

```python
class QueryOptimizer:
    """Optimize database queries based on patterns."""

    @staticmethod
    def optimize_project_search(params: dict) -> str:
        """Generate optimized SQL for project search."""

        # Use partial index for status if filtering by status
        if params.get("status"):
            return """
                SELECT p.* FROM projects p
                WHERE p.status = %(status)s
                AND to_tsvector('english', p.title || ' ' || p.objective)
                    @@ plainto_tsquery('english', %(keywords)s)
                ORDER BY ts_rank(
                    to_tsvector('english', p.title || ' ' || p.objective),
                    plainto_tsquery('english', %(keywords)s)
                ) DESC
                LIMIT %(limit)s
            """

        # Use GIN index for full-text search
        return """
            SELECT p.* FROM projects p
            WHERE to_tsvector('english', p.title || ' ' || p.objective)
                @@ plainto_tsquery('english', %(keywords)s)
            ORDER BY ts_rank(...) DESC
            LIMIT %(limit)s
        """

    @staticmethod
    def add_missing_indexes():
        """SQL to add missing indexes for common queries."""
        return """
            -- Partial index for open calls
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_calls_open
            ON funding_calls(deadline)
            WHERE status = 'open';

            -- GIN index for project search
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_fts
            ON projects USING GIN(to_tsvector('english', title || ' ' || objective));

            -- Index for organization lookup
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orgs_name_country
            ON organizations(name, country);

            -- Index for project embeddings lookup
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_project
            ON project_embeddings(project_id);
        """
```

### 3.2 Embedding Generation Optimization

**Problem:** Embedding generation is slow and blocks responses.

**Solution:** Background embedding generation with queue.

**Modify:** `app/services/embedding/incremental_embedding_service.py`

```python
from celery import shared_task
import asyncio

@shared_task(bind=True, max_retries=3)
def generate_embeddings_batch(self, project_ids: List[str]):
    """Background task for batch embedding generation."""
    try:
        service = IncrementalEmbeddingService()
        results = asyncio.run(service.process_batch(project_ids))
        return {"processed": len(results), "success": True}
    except Exception as e:
        self.retry(countdown=60 * (self.request.retries + 1))

class EmbeddingQueue:
    """Queue for background embedding generation."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.queue_key = "embedding:queue"

    def enqueue(self, project_id: str):
        """Add project to embedding queue."""
        self.redis.rpush(self.queue_key, project_id)

    def process_queue(self, batch_size: int = 50):
        """Process queued projects in batches."""
        project_ids = []
        for _ in range(batch_size):
            project_id = self.redis.lpop(self.queue_key)
            if project_id:
                project_ids.append(project_id.decode())
            else:
                break

        if project_ids:
            generate_embeddings_batch.delay(project_ids)
```

### 3.3 Streaming Response Optimization

**Problem:** SSE streaming has overhead per event.

**Solution:** Batch small updates and optimize event formatting.

**Modify:** `app/api/conversation_routes_v3.py`

```python
class StreamBuffer:
    """Buffer for batching small streaming updates."""

    def __init__(self, flush_interval: float = 0.1, max_buffer_size: int = 10):
        self.buffer = []
        self.flush_interval = flush_interval
        self.max_buffer_size = max_buffer_size
        self.last_flush = time.time()

    def add(self, event: dict) -> List[dict]:
        """Add event to buffer, return events to flush."""
        self.buffer.append(event)

        # Flush if buffer full or interval elapsed
        if (len(self.buffer) >= self.max_buffer_size or
            time.time() - self.last_flush > self.flush_interval):
            return self.flush()

        # Always flush important events immediately
        if event.get("type") in ["error", "complete", "tool_result"]:
            return self.flush()

        return []

    def flush(self) -> List[dict]:
        """Flush all buffered events."""
        events = self.buffer
        self.buffer = []
        self.last_flush = time.time()
        return events
```

---

## Priority 4: Feature Completeness

### 4.1 Official EU Template Export

**Problem:** Users cannot export proposals in official EU submission format.

**Solution:** Implement PDF/DOCX export matching EU templates.

**Create:** `app/services/proposal_writing/export_service.py`

```python
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io

class ProposalExportService:
    """Export proposals to official EU formats."""

    def __init__(self):
        self.templates_path = "data/templates/"

    async def export_to_docx(
        self,
        session_id: str,
        template_type: str = "RIA"
    ) -> io.BytesIO:
        """Export proposal to DOCX format matching EU template."""

        # Load session data
        session = await self._get_session(session_id)

        # Load appropriate template
        template = self._load_template(template_type)
        doc = Document(template)

        # Fill in sections
        for section_id, section_data in session.sections.items():
            self._fill_section(doc, section_id, section_data)

        # Add required formatting
        self._apply_eu_formatting(doc)

        # Save to buffer
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    def _apply_eu_formatting(self, doc: Document):
        """Apply EU-required formatting."""
        for section in doc.sections:
            section.page_height = Inches(11.69)  # A4
            section.page_width = Inches(8.27)
            section.left_margin = Inches(0.79)  # 2cm
            section.right_margin = Inches(0.79)
            section.top_margin = Inches(0.59)  # 1.5cm
            section.bottom_margin = Inches(0.59)

        # Set font to required style
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(11)

    async def export_to_pdf(self, session_id: str) -> io.BytesIO:
        """Export to PDF via DOCX conversion."""
        docx_buffer = await self.export_to_docx(session_id)
        # Use libreoffice or similar for conversion
        return await self._convert_to_pdf(docx_buffer)
```

**API Endpoint:**

```python
# Add to proposal_session_routes.py

@router.get("/{session_id}/export")
async def export_proposal(
    session_id: str,
    format: str = Query("docx", pattern="^(docx|pdf)$")
):
    """Export proposal in official EU format."""
    export_service = ProposalExportService()

    if format == "docx":
        buffer = await export_service.export_to_docx(session_id)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=proposal_{session_id}.docx"}
        )
    else:
        buffer = await export_service.export_to_pdf(session_id)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=proposal_{session_id}.pdf"}
        )
```

### 4.2 Batch Operations API

**Problem:** No way to process multiple queries efficiently.

**Solution:** Implement batch API for bulk operations.

**Create:** `app/api/batch_routes.py`

```python
from fastapi import APIRouter, BackgroundTasks
from typing import List
import asyncio

router = APIRouter(prefix="/api/batch", tags=["batch"])

class BatchRequest(BaseModel):
    operations: List[BatchOperation]

class BatchOperation(BaseModel):
    id: str
    type: str  # "search_calls", "search_projects", "get_statistics"
    params: dict

class BatchResponse(BaseModel):
    results: Dict[str, Any]
    completed: int
    failed: int
    processing_time_ms: float

@router.post("/execute")
async def execute_batch(request: BatchRequest) -> BatchResponse:
    """Execute multiple operations in parallel."""
    start_time = time.time()

    # Execute all operations in parallel
    tasks = [
        execute_operation(op)
        for op in request.operations
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Format response
    response_results = {}
    completed = 0
    failed = 0

    for op, result in zip(request.operations, results):
        if isinstance(result, Exception):
            response_results[op.id] = {"error": str(result)}
            failed += 1
        else:
            response_results[op.id] = result
            completed += 1

    return BatchResponse(
        results=response_results,
        completed=completed,
        failed=failed,
        processing_time_ms=(time.time() - start_time) * 1000
    )

@router.post("/async")
async def execute_batch_async(
    request: BatchRequest,
    background_tasks: BackgroundTasks
) -> dict:
    """Execute batch operations asynchronously."""
    batch_id = generate_batch_id()
    background_tasks.add_task(process_batch_background, batch_id, request)
    return {
        "batch_id": batch_id,
        "status": "processing",
        "status_url": f"/api/batch/{batch_id}/status"
    }

@router.get("/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """Get status of async batch operation."""
    status = await get_batch_from_redis(batch_id)
    return status
```

### 4.3 Webhook Notifications

**Problem:** No way to get notified when async operations complete.

**Solution:** Implement webhook support.

**Create:** `app/services/webhooks/webhook_service.py`

```python
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class WebhookService:
    """Service for sending webhook notifications."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send_notification(
        self,
        webhook_url: str,
        event_type: str,
        payload: dict,
        secret: Optional[str] = None
    ) -> bool:
        """Send webhook notification."""
        try:
            headers = {"Content-Type": "application/json"}

            if secret:
                signature = self._generate_signature(payload, secret)
                headers["X-Webhook-Signature"] = signature

            response = await self.client.post(
                webhook_url,
                json={
                    "event": event_type,
                    "payload": payload,
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers=headers
            )

            return response.status_code < 400

        except Exception as e:
            logger.error(f"Webhook failed: {e}")
            return False

    def _generate_signature(self, payload: dict, secret: str) -> str:
        """Generate HMAC signature for webhook."""
        import hmac
        import hashlib

        message = json.dumps(payload, sort_keys=True).encode()
        return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

# Webhook event types
WEBHOOK_EVENTS = {
    "proposal.section.completed": "Section draft completed",
    "proposal.evaluation.completed": "Evaluation completed",
    "batch.completed": "Batch operation completed",
    "call.deadline.approaching": "Call deadline in 7 days",
}
```

### 4.4 Complete Embedding Coverage

**Problem:** Only 98% of projects have embeddings.

**Solution:** Ensure 100% coverage and automatic updates.

**Create migration:** `migration/016_ensure_embedding_coverage.sql`

```sql
-- Find projects without embeddings
CREATE OR REPLACE VIEW projects_needing_embeddings AS
SELECT p.id, p.rcn, p.title
FROM projects p
LEFT JOIN project_embeddings pe ON p.id = pe.project_id
WHERE pe.id IS NULL
   OR pe.embedding IS NULL
   OR pe.updated_at < p.updated_at;

-- Create trigger to queue embeddings on project insert/update
CREATE OR REPLACE FUNCTION queue_embedding_generation()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO embedding_queue (project_id, status, created_at)
    VALUES (NEW.id, 'pending', NOW())
    ON CONFLICT (project_id) DO UPDATE SET status = 'pending', created_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_queue_embedding
AFTER INSERT OR UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION queue_embedding_generation();
```

**Celery periodic task:**

```python
# Add to celery_app.py or create new file

from celery import Celery
from celery.schedules import crontab

app = Celery('mapit')

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Process embedding queue every 5 minutes
    sender.add_periodic_task(
        300.0,
        process_embedding_queue.s(),
        name='process-embedding-queue'
    )

    # Daily full sync check
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        full_embedding_sync.s(),
        name='daily-embedding-sync'
    )

@app.task
def process_embedding_queue():
    """Process pending embeddings from queue."""
    service = IncrementalEmbeddingService()
    return asyncio.run(service.process_queue(batch_size=100))

@app.task
def full_embedding_sync():
    """Ensure all projects have embeddings."""
    service = IncrementalEmbeddingService()
    stats = asyncio.run(service.full_sync())
    return stats
```

---

## Priority 5: Premium Features

### 5.1 Advanced Analytics Dashboard

**Problem:** No visibility into system usage and performance.

**Solution:** Comprehensive analytics API and dashboard data.

**Create:** `app/api/analytics_routes.py`

```python
from fastapi import APIRouter
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/overview")
async def get_analytics_overview(
    days: int = 30
) -> dict:
    """Get system analytics overview."""

    analytics_service = AnalyticsService()

    return {
        "period": {"days": days, "end_date": datetime.utcnow().isoformat()},
        "usage": {
            "total_queries": await analytics_service.get_query_count(days),
            "unique_users": await analytics_service.get_unique_users(days),
            "queries_per_day": await analytics_service.get_queries_per_day(days),
            "peak_hour": await analytics_service.get_peak_usage_hour(days),
        },
        "performance": {
            "avg_response_time_ms": await analytics_service.get_avg_response_time(days),
            "p95_response_time_ms": await analytics_service.get_p95_response_time(days),
            "error_rate": await analytics_service.get_error_rate(days),
            "tool_success_rates": await analytics_service.get_tool_success_rates(days),
        },
        "content": {
            "top_queries": await analytics_service.get_top_queries(days, limit=10),
            "top_tools": await analytics_service.get_top_tools(days, limit=10),
            "popular_clusters": await analytics_service.get_popular_clusters(days),
            "popular_countries": await analytics_service.get_popular_countries(days),
        },
        "proposals": {
            "sessions_created": await analytics_service.get_proposal_sessions(days),
            "sections_generated": await analytics_service.get_sections_generated(days),
            "avg_completion_rate": await analytics_service.get_avg_completion_rate(days),
        },
        "feedback": {
            "avg_rating": await analytics_service.get_avg_feedback_rating(days),
            "rating_distribution": await analytics_service.get_rating_distribution(days),
            "improvement_suggestions": await analytics_service.get_top_suggestions(days),
        }
    }

@router.get("/tools")
async def get_tool_analytics(days: int = 30):
    """Detailed tool usage analytics."""
    return await ToolAnalyticsService().get_detailed_stats(days)

@router.get("/trends")
async def get_trends(
    metric: str,
    granularity: str = "day",  # day, week, month
    days: int = 90
):
    """Get metric trends over time."""
    return await AnalyticsService().get_trends(metric, granularity, days)
```

### 5.2 Saved Searches and Alerts

**Problem:** Users cannot save searches or get notified of new calls.

**Solution:** Implement saved searches with email/webhook alerts.

**Create:** `app/services/alerts/saved_search_service.py`

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class SavedSearch:
    id: str
    user_id: str
    name: str
    query_type: str  # "calls", "projects", "partners"
    parameters: dict
    alert_enabled: bool
    alert_frequency: str  # "daily", "weekly", "immediate"
    webhook_url: Optional[str]
    email: Optional[str]
    created_at: datetime
    last_run: Optional[datetime]

class SavedSearchService:
    """Manage saved searches and alerts."""

    async def create_search(
        self,
        user_id: str,
        name: str,
        query_type: str,
        parameters: dict,
        alert_config: dict = None
    ) -> SavedSearch:
        """Create a saved search."""
        search = SavedSearch(
            id=generate_id(),
            user_id=user_id,
            name=name,
            query_type=query_type,
            parameters=parameters,
            alert_enabled=alert_config.get("enabled", False) if alert_config else False,
            alert_frequency=alert_config.get("frequency", "daily") if alert_config else "daily",
            webhook_url=alert_config.get("webhook_url") if alert_config else None,
            email=alert_config.get("email") if alert_config else None,
            created_at=datetime.utcnow(),
            last_run=None
        )
        await self._save_to_db(search)
        return search

    async def run_saved_search(self, search: SavedSearch) -> dict:
        """Execute a saved search and return results."""

        if search.query_type == "calls":
            service = LocalCallSearchService()
            results = await service.search(**search.parameters)
        elif search.query_type == "projects":
            service = LocalProjectSearchService()
            results = await service.search(**search.parameters)
        elif search.query_type == "partners":
            tool = PartnerDiscoveryTool()
            results = await tool.find_partners(**search.parameters)

        # Update last run time
        search.last_run = datetime.utcnow()
        await self._update_last_run(search.id)

        return results

    async def check_for_new_results(self, search: SavedSearch) -> List[dict]:
        """Check if there are new results since last run."""
        results = await self.run_saved_search(search)

        if not search.last_run:
            return results.get("items", [])

        # Filter to only new items
        new_items = [
            item for item in results.get("items", [])
            if self._is_new(item, search.last_run)
        ]

        return new_items

# Celery task for processing alerts
@app.task
def process_saved_search_alerts():
    """Process all saved searches that need alerts."""
    service = SavedSearchService()
    webhook_service = WebhookService()

    searches = asyncio.run(service.get_due_searches())

    for search in searches:
        new_results = asyncio.run(service.check_for_new_results(search))

        if new_results:
            if search.webhook_url:
                asyncio.run(webhook_service.send_notification(
                    search.webhook_url,
                    f"saved_search.{search.query_type}.new_results",
                    {"search_name": search.name, "new_count": len(new_results), "items": new_results}
                ))

            if search.email:
                send_alert_email(search.email, search.name, new_results)
```

### 5.3 Collaboration Features

**Problem:** No support for team collaboration on proposals.

**Solution:** Implement real-time collaboration with conflict resolution.

**Create:** `app/services/collaboration/collaboration_service.py`

```python
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

@dataclass
class CollaboratorSession:
    user_id: str
    session_id: str
    active_section: Optional[str]
    cursor_position: Optional[int]
    last_activity: datetime

class CollaborationService:
    """Real-time collaboration on proposals."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.active_sessions: Dict[str, List[CollaboratorSession]] = {}

    async def join_session(
        self,
        proposal_session_id: str,
        user_id: str
    ) -> dict:
        """User joins a collaboration session."""

        collaborator = CollaboratorSession(
            user_id=user_id,
            session_id=proposal_session_id,
            active_section=None,
            cursor_position=None,
            last_activity=datetime.utcnow()
        )

        # Register in Redis for distributed tracking
        await self._register_collaborator(proposal_session_id, collaborator)

        # Get current collaborators
        collaborators = await self._get_collaborators(proposal_session_id)

        return {
            "joined": True,
            "collaborators": [c.user_id for c in collaborators],
            "locked_sections": await self._get_locked_sections(proposal_session_id)
        }

    async def update_cursor(
        self,
        proposal_session_id: str,
        user_id: str,
        section: str,
        position: int
    ):
        """Update user's cursor position for real-time collaboration."""
        await self._broadcast_to_session(
            proposal_session_id,
            {
                "type": "cursor_update",
                "user_id": user_id,
                "section": section,
                "position": position
            },
            exclude_user=user_id
        )

    async def lock_section(
        self,
        proposal_session_id: str,
        user_id: str,
        section_id: str
    ) -> bool:
        """Lock a section for editing."""
        lock_key = f"lock:{proposal_session_id}:{section_id}"

        # Try to acquire lock
        acquired = await self.redis.set(
            lock_key,
            user_id,
            nx=True,  # Only if not exists
            ex=300    # 5 minute expiry
        )

        if acquired:
            await self._broadcast_to_session(
                proposal_session_id,
                {"type": "section_locked", "section": section_id, "by": user_id}
            )

        return acquired

    async def apply_edit(
        self,
        proposal_session_id: str,
        user_id: str,
        section_id: str,
        operation: dict  # OT operation
    ) -> dict:
        """Apply an edit operation with conflict resolution."""

        # Get current version
        current_version = await self._get_section_version(proposal_session_id, section_id)

        # Transform operation if needed (OT)
        if operation.get("base_version") != current_version:
            operation = self._transform_operation(
                operation,
                await self._get_pending_operations(proposal_session_id, section_id)
            )

        # Apply operation
        new_content = self._apply_operation(
            await self._get_section_content(proposal_session_id, section_id),
            operation
        )

        # Save and broadcast
        new_version = current_version + 1
        await self._save_section(proposal_session_id, section_id, new_content, new_version)

        await self._broadcast_to_session(
            proposal_session_id,
            {
                "type": "section_updated",
                "section": section_id,
                "operation": operation,
                "version": new_version,
                "by": user_id
            },
            exclude_user=user_id
        )

        return {"version": new_version, "content": new_content}
```

### 5.4 AI-Powered Proposal Reviewer

**Problem:** No comprehensive AI review before submission.

**Solution:** Multi-pass AI review simulating different evaluators.

**Create:** `app/services/proposal_writing/comprehensive_reviewer.py`

```python
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ReviewFinding:
    severity: str  # "critical", "major", "minor", "suggestion"
    category: str  # "excellence", "impact", "implementation", "compliance", "language"
    section: str
    issue: str
    suggestion: str
    confidence: float

class ComprehensiveReviewer:
    """Multi-pass AI review simulating EU evaluators."""

    async def full_review(
        self,
        session_id: str,
        call_id: str
    ) -> Dict[str, Any]:
        """Perform comprehensive proposal review."""

        # Load proposal and call requirements
        proposal = await self._load_proposal(session_id)
        call_requirements = await self._load_call_requirements(call_id)

        # Run multiple review passes
        reviews = await asyncio.gather(
            self._excellence_review(proposal, call_requirements),
            self._impact_review(proposal, call_requirements),
            self._implementation_review(proposal, call_requirements),
            self._compliance_review(proposal, call_requirements),
            self._language_review(proposal),
            self._consistency_review(proposal),
        )

        # Aggregate findings
        all_findings = []
        for review in reviews:
            all_findings.extend(review.get("findings", []))

        # Calculate overall score
        score = self._calculate_overall_score(all_findings)

        # Generate summary
        summary = await self._generate_review_summary(all_findings, score)

        return {
            "overall_score": score,
            "summary": summary,
            "findings": all_findings,
            "findings_by_severity": self._group_by_severity(all_findings),
            "findings_by_section": self._group_by_section(all_findings),
            "recommendation": self._get_recommendation(score, all_findings),
            "estimated_evaluator_score": self._estimate_evaluator_score(score)
        }

    async def _excellence_review(
        self,
        proposal: dict,
        requirements: dict
    ) -> Dict[str, Any]:
        """Review excellence criterion."""

        prompt = f"""You are an expert EU proposal evaluator reviewing the Excellence section.

CALL REQUIREMENTS:
{requirements.get('excellence_criteria', '')}

PROPOSAL EXCELLENCE SECTION:
{proposal.get('excellence', '')}

Evaluate against these criteria:
1. Clarity and pertinence of objectives
2. Soundness of proposed methodology
3. Extent beyond state-of-the-art
4. Quality and credibility of interdisciplinary approach

For each issue found, provide:
- Severity: critical/major/minor/suggestion
- Specific issue description
- Concrete suggestion for improvement

Be thorough but fair. Identify both strengths and weaknesses."""

        response = await self.ai_service.generate(prompt)
        return self._parse_review_response(response, "excellence")

    async def _consistency_review(self, proposal: dict) -> Dict[str, Any]:
        """Check consistency across all sections."""

        prompt = f"""Review this proposal for internal consistency.

Check for:
1. Budget figures matching between sections
2. Timeline consistency with deliverables
3. Partner roles consistent across sections
4. Objectives alignment with methodology
5. Impact claims supported by activities
6. Acronyms and terminology consistency

PROPOSAL:
{json.dumps(proposal, indent=2)}

List any inconsistencies found."""

        response = await self.ai_service.generate(prompt)
        return self._parse_review_response(response, "consistency")

    def _get_recommendation(
        self,
        score: float,
        findings: List[ReviewFinding]
    ) -> str:
        """Get submission recommendation based on review."""

        critical_count = len([f for f in findings if f.severity == "critical"])
        major_count = len([f for f in findings if f.severity == "major"])

        if critical_count > 0:
            return "NOT_READY - Address critical issues before submission"
        elif major_count > 3:
            return "NEEDS_WORK - Address major issues to improve chances"
        elif score >= 4.0:
            return "READY - Proposal is competitive, consider minor improvements"
        elif score >= 3.0:
            return "ACCEPTABLE - Meets threshold but improvements recommended"
        else:
            return "BELOW_THRESHOLD - Significant revision needed"
```

---

## Priority 6: Enterprise Readiness

### 6.1 Authentication and Authorization

**Problem:** No user authentication or access control.

**Solution:** Implement JWT-based authentication with role-based access.

**Create:** `app/core/auth.py`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
from typing import Optional

security = HTTPBearer()

class AuthService:
    """JWT-based authentication service."""

    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(hours=24)

    def create_access_token(
        self,
        user_id: str,
        roles: List[str],
        organization_id: Optional[str] = None
    ) -> str:
        """Create JWT access token."""
        expires = datetime.utcnow() + self.access_token_expire

        payload = {
            "sub": user_id,
            "roles": roles,
            "org_id": organization_id,
            "exp": expires,
            "iat": datetime.utcnow()
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency to get current authenticated user."""
    auth_service = AuthService()
    return auth_service.verify_token(credentials.credentials)

def require_role(required_roles: List[str]):
    """Decorator to require specific roles."""
    async def role_checker(user: dict = Depends(get_current_user)):
        if not any(role in user.get("roles", []) for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    return role_checker

# Usage in routes:
@router.get("/admin/analytics")
async def admin_analytics(user: dict = Depends(require_role(["admin"]))):
    ...
```

### 6.2 Rate Limiting

**Problem:** No protection against abuse or excessive usage.

**Solution:** Implement tiered rate limiting.

**Create:** `app/core/rate_limit.py`

```python
from fastapi import Request, HTTPException
import redis
from datetime import datetime

class RateLimiter:
    """Tiered rate limiting based on user/API key."""

    TIERS = {
        "free": {"requests_per_minute": 10, "requests_per_day": 100},
        "basic": {"requests_per_minute": 60, "requests_per_day": 1000},
        "premium": {"requests_per_minute": 300, "requests_per_day": 10000},
        "enterprise": {"requests_per_minute": 1000, "requests_per_day": 100000},
    }

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        identifier: str,
        tier: str = "free"
    ) -> dict:
        """Check if request is within rate limits."""

        limits = self.TIERS.get(tier, self.TIERS["free"])

        # Check per-minute limit
        minute_key = f"rate:{identifier}:minute:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        minute_count = int(self.redis.get(minute_key) or 0)

        if minute_count >= limits["requests_per_minute"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit of {limits['requests_per_minute']} requests per minute exceeded",
                    "retry_after": 60
                }
            )

        # Check daily limit
        day_key = f"rate:{identifier}:day:{datetime.utcnow().strftime('%Y%m%d')}"
        day_count = int(self.redis.get(day_key) or 0)

        if day_count >= limits["requests_per_day"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "DAILY_LIMIT_EXCEEDED",
                    "message": f"Daily limit of {limits['requests_per_day']} requests exceeded",
                    "retry_after": self._seconds_until_midnight()
                }
            )

        # Increment counters
        pipe = self.redis.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)
        pipe.incr(day_key)
        pipe.expire(day_key, 86400)
        pipe.execute()

        return {
            "remaining_minute": limits["requests_per_minute"] - minute_count - 1,
            "remaining_day": limits["requests_per_day"] - day_count - 1,
            "tier": tier
        }

# Middleware for rate limiting
async def rate_limit_middleware(request: Request, call_next):
    rate_limiter = RateLimiter(get_redis())

    # Get user tier from token or default to free
    user = getattr(request.state, "user", None)
    tier = user.get("tier", "free") if user else "free"
    identifier = user.get("id") if user else request.client.host

    await rate_limiter.check_rate_limit(identifier, tier)

    response = await call_next(request)
    return response
```

### 6.3 Audit Logging

**Problem:** No audit trail for compliance and debugging.

**Solution:** Comprehensive audit logging.

**Create:** `app/services/audit/audit_service.py`

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import json

@dataclass
class AuditEvent:
    event_id: str
    timestamp: datetime
    event_type: str  # "query", "proposal_edit", "export", "login", "admin_action"
    user_id: Optional[str]
    organization_id: Optional[str]
    resource_type: str  # "conversation", "proposal", "document"
    resource_id: str
    action: str  # "create", "read", "update", "delete"
    details: Dict[str, Any]
    ip_address: str
    user_agent: str
    success: bool
    error_message: Optional[str]

class AuditService:
    """Audit logging for compliance and debugging."""

    async def log_event(self, event: AuditEvent):
        """Log an audit event."""

        # Store in database
        await self._store_event(event)

        # Also log to structured logging for SIEM
        logger.info(
            "audit_event",
            extra={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "user_id": event.user_id,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "action": event.action,
                "success": event.success
            }
        )

    async def log_query(
        self,
        user_id: str,
        conversation_id: str,
        query: str,
        tools_used: List[str],
        request: Request
    ):
        """Log a conversation query."""
        await self.log_event(AuditEvent(
            event_id=generate_id(),
            timestamp=datetime.utcnow(),
            event_type="query",
            user_id=user_id,
            organization_id=None,
            resource_type="conversation",
            resource_id=conversation_id,
            action="create",
            details={
                "query_length": len(query),
                "tools_used": tools_used,
                "query_preview": query[:100]
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", ""),
            success=True,
            error_message=None
        ))

    async def get_audit_trail(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get audit trail for a resource."""
        return await self._query_events(
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit
        )
```

### 6.4 Multi-tenancy Support

**Problem:** No isolation between organizations.

**Solution:** Implement organization-based data isolation.

**Create:** `app/core/tenancy.py`

```python
from contextvars import ContextVar
from typing import Optional

# Context variable for current tenant
current_tenant: ContextVar[Optional[str]] = ContextVar('current_tenant', default=None)

class TenantMiddleware:
    """Middleware to set tenant context from JWT."""

    async def __call__(self, request: Request, call_next):
        user = getattr(request.state, "user", None)
        if user and user.get("org_id"):
            current_tenant.set(user["org_id"])

        response = await call_next(request)

        current_tenant.set(None)
        return response

class TenantAwareRepository:
    """Base repository with tenant isolation."""

    def _add_tenant_filter(self, query: str) -> str:
        """Add tenant filter to SQL query."""
        tenant_id = current_tenant.get()
        if tenant_id:
            # Add organization_id filter
            if "WHERE" in query.upper():
                return query.replace("WHERE", f"WHERE organization_id = '{tenant_id}' AND")
            else:
                return f"{query} WHERE organization_id = '{tenant_id}'"
        return query

    async def execute_query(self, query: str, params: dict = None):
        """Execute query with tenant isolation."""
        filtered_query = self._add_tenant_filter(query)
        return await self.db.execute(filtered_query, params)

# Tenant-aware models
class TenantMixin:
    """Mixin for tenant-aware models."""
    organization_id: str = Field(..., description="Owning organization")

    @validator('organization_id', pre=True, always=True)
    def set_organization(cls, v):
        return v or current_tenant.get()
```

### 6.5 Kubernetes Deployment Configuration

**Create:** `k8s/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mapit-api
  labels:
    app: mapit
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mapit
  template:
    metadata:
      labels:
        app: mapit
    spec:
      containers:
      - name: mapit
        image: mapit:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mapit-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: mapit-secrets
              key: redis-url
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: mapit-secrets
              key: gemini-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: mapit-service
spec:
  selector:
    app: mapit
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mapit-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mapit-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## Implementation Guidelines

### For AI Agents Implementing These Improvements

#### Step-by-Step Process

1. **Read Context First**
   - Always read `CLAUDE.md` and `SYSTEM_ARCHITECTURE.md` before starting
   - Understand the V3 architecture (no intent classification, single agentic loop)
   - Know the 20 available tools and their purposes

2. **Check Existing Implementation**
   - Before creating new files, check if similar functionality exists
   - Use `Grep` to find related code
   - Read existing implementations to match patterns

3. **Follow Existing Patterns**
   - Match logging patterns (use `logger = logging.getLogger(__name__)`)
   - Match error handling patterns
   - Match async/await patterns
   - Match Pydantic model patterns for API schemas

4. **Test Changes**
   - Run `python3 -c "from app.main import app"` to verify imports
   - Check for any broken imports or circular dependencies
   - Verify the app starts without critical errors

5. **Update Documentation**
   - Update `CLAUDE.md` if adding new features
   - Update `SYSTEM_ARCHITECTURE.md` for architectural changes
   - Add docstrings to all new functions

#### Code Quality Standards

```python
# DO: Use type hints
async def search_projects(
    keywords: str,
    cluster: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    ...

# DO: Use dataclasses for data structures
@dataclass
class SearchResult:
    id: str
    title: str
    score: float
    metadata: Dict[str, Any]

# DO: Use proper logging
logger.info(f"Processing query: {query[:50]}...")
logger.error(f"Tool execution failed: {e}", exc_info=True)

# DO: Handle errors gracefully
try:
    result = await external_service.call()
except TimeoutError:
    logger.warning("Service timeout, using fallback")
    result = await fallback_service.call()
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise ServiceError("Service unavailable", "SERVICE_ERROR")

# DON'T: Use print statements
# DON'T: Hardcode configuration values
# DON'T: Ignore exceptions silently
# DON'T: Create circular imports
```

#### File Organization

```
app/
├── api/                    # API routes only
│   ├── conversation_routes_v3.py
│   ├── proposal_session_routes.py
│   └── ...
├── core/                   # Core utilities (NEW)
│   ├── auth.py
│   ├── exceptions.py
│   ├── rate_limit.py
│   └── timeouts.py
├── services/               # Business logic
│   ├── agents/             # AI agents
│   ├── tools/              # Tool implementations
│   ├── proposal_writing/   # Proposal services
│   └── ...
└── models/                 # Pydantic models
```

---

## Success Metrics

### Production Readiness Checklist

#### Reliability
- [ ] All API endpoints have proper error handling
- [ ] Health checks for all dependencies
- [ ] Graceful degradation when services fail
- [ ] Retry logic for transient failures
- [ ] Circuit breakers for external APIs
- [ ] Request timeouts configured

#### Performance
- [ ] Average response time < 3s for simple queries
- [ ] P95 response time < 10s for complex queries
- [ ] Query result caching implemented
- [ ] Database queries optimized with indexes
- [ ] Connection pooling properly configured

#### Feature Completeness
- [ ] All 20 tools working reliably
- [ ] Proposal export to EU format
- [ ] 100% embedding coverage
- [ ] Batch operations API
- [ ] Webhook notifications

#### Premium Features
- [ ] Advanced analytics dashboard
- [ ] Saved searches with alerts
- [ ] Collaboration features
- [ ] Comprehensive AI review

#### Enterprise Readiness
- [ ] JWT authentication
- [ ] Role-based access control
- [ ] Tiered rate limiting
- [ ] Audit logging
- [ ] Multi-tenancy support
- [ ] Kubernetes deployment ready

### KPIs to Track

| Metric | Target | Current |
|--------|--------|---------|
| API Uptime | 99.9% | - |
| Avg Response Time | < 3s | - |
| Error Rate | < 1% | - |
| User Satisfaction | > 4.5/5 | - |
| Proposal Completion Rate | > 80% | - |
| Tool Success Rate | > 95% | - |

---

## Conclusion

This roadmap provides a comprehensive path to transform MAP-IT from its current state to a production-ready, premium-grade application. The priorities are ordered by business impact and technical dependency:

1. **Critical Fixes** - Must be done first for stability
2. **Reliability** - Required for production deployment
3. **Performance** - Required for user satisfaction
4. **Feature Completeness** - Required for full functionality
5. **Premium Features** - Differentiators for premium offering
6. **Enterprise** - Required for B2B customers

Each section includes implementation details sufficient for an AI agent to execute without additional context beyond the existing documentation.

---

*Last Updated: December 19, 2025*
*Version: 1.0*
