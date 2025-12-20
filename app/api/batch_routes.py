"""
Batch Operations API for MAP-IT.

Provides endpoints for executing multiple operations in parallel,
supporting both synchronous and asynchronous batch processing.

Implements Priority 4.2 from IMPROVEMENT_ROADMAP.md
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime, timezone
import asyncio
import uuid
import time
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["batch"])


# ============================================================================
# Models
# ============================================================================

class OperationType(str, Enum):
    """Supported batch operation types."""
    SEARCH_CALLS = "search_calls"
    SEARCH_PROJECTS = "search_projects"
    GET_STATISTICS = "get_statistics"
    GET_PROJECT_DETAILS = "get_project_details"
    GET_CALL_DETAILS = "get_call_details"
    FIND_PARTNERS = "find_partners"
    GET_BUDGET_BENCHMARK = "get_budget_benchmark"
    GET_CONSORTIUM_PATTERNS = "get_consortium_patterns"
    FIND_SIMILAR_PROJECTS = "find_similar_projects"


class BatchOperation(BaseModel):
    """Single operation within a batch request."""
    id: str = Field(..., description="Unique identifier for this operation")
    type: OperationType = Field(..., description="Type of operation to execute")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the operation"
    )

    @validator('id')
    def validate_id(cls, v):
        if not v or len(v) > 100:
            raise ValueError('Operation ID must be between 1 and 100 characters')
        return v


class BatchRequest(BaseModel):
    """Request for batch operations."""
    operations: List[BatchOperation] = Field(
        ...,
        min_items=1,
        max_items=50,
        description="List of operations to execute (max 50)"
    )
    fail_fast: bool = Field(
        default=False,
        description="Stop on first failure if True"
    )
    timeout_seconds: int = Field(
        default=60,
        ge=5,
        le=300,
        description="Overall timeout for batch execution (5-300 seconds)"
    )


class OperationResult(BaseModel):
    """Result of a single operation."""
    id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float


class BatchResponse(BaseModel):
    """Response from batch execution."""
    batch_id: str
    results: Dict[str, OperationResult]
    completed: int
    failed: int
    total: int
    processing_time_ms: float
    status: str  # "completed", "partial", "failed"


class AsyncBatchResponse(BaseModel):
    """Response for async batch submission."""
    batch_id: str
    status: str
    total_operations: int
    status_url: str
    created_at: str


class BatchStatus(BaseModel):
    """Status of an async batch operation."""
    batch_id: str
    status: str  # "pending", "processing", "completed", "failed"
    total_operations: int
    completed_operations: int
    failed_operations: int
    progress_percent: float
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    results: Optional[Dict[str, OperationResult]] = None
    error: Optional[str] = None


# ============================================================================
# In-memory batch storage (for development - use Redis in production)
# ============================================================================

_batch_storage: Dict[str, Dict[str, Any]] = {}


async def store_batch_status(batch_id: str, status: Dict[str, Any]):
    """Store batch status (use Redis in production)."""
    _batch_storage[batch_id] = status
    # Clean up old batches (keep last 1000)
    if len(_batch_storage) > 1000:
        oldest_keys = sorted(_batch_storage.keys())[:-1000]
        for key in oldest_keys:
            del _batch_storage[key]


async def get_batch_status(batch_id: str) -> Optional[Dict[str, Any]]:
    """Get batch status (use Redis in production)."""
    return _batch_storage.get(batch_id)


# ============================================================================
# Operation Executors
# ============================================================================

async def execute_operation(operation: BatchOperation) -> OperationResult:
    """Execute a single batch operation."""
    start_time = time.time()

    try:
        result = await _execute_operation_internal(operation)
        execution_time = (time.time() - start_time) * 1000

        return OperationResult(
            id=operation.id,
            success=True,
            result=result,
            error=None,
            execution_time_ms=round(execution_time, 2)
        )
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(f"Batch operation {operation.id} failed: {e}")

        return OperationResult(
            id=operation.id,
            success=False,
            result=None,
            error=str(e),
            execution_time_ms=round(execution_time, 2)
        )


async def _execute_operation_internal(operation: BatchOperation) -> Dict[str, Any]:
    """Execute operation based on type."""

    params = operation.params

    if operation.type == OperationType.SEARCH_CALLS:
        from ..services.calls.local_call_search_service import LocalCallSearchService
        service = LocalCallSearchService()
        result = await service.search(
            keywords=params.get("keywords", ""),
            status=params.get("status"),
            cluster=params.get("cluster"),
            limit=params.get("limit", 10)
        )
        return result

    elif operation.type == OperationType.SEARCH_PROJECTS:
        from ..services.projects.local_project_search_service import LocalProjectSearchService
        service = LocalProjectSearchService()
        result = await service.search(
            keywords=params.get("keywords", ""),
            cluster=params.get("cluster"),
            action_type=params.get("action_type"),
            limit=params.get("limit", 10)
        )
        return result

    elif operation.type == OperationType.GET_STATISTICS:
        from ..services.data_intelligence.graph_service import GraphSearchService
        service = GraphSearchService()
        programme = params.get("programme")
        country = params.get("country")

        if programme:
            result = await service.get_programme_statistics(programme)
        elif country:
            result = await service.get_country_statistics(country)
        else:
            raise ValueError("Either 'programme' or 'country' parameter required")
        return result

    elif operation.type == OperationType.GET_PROJECT_DETAILS:
        from ..services.data.cordis_repository import CordisProjectRepository
        repo = CordisProjectRepository()
        project_id = params.get("project_id") or params.get("rcn")
        if not project_id:
            raise ValueError("'project_id' or 'rcn' parameter required")
        result = repo.get_project_by_rcn(project_id)
        if not result:
            raise ValueError(f"Project not found: {project_id}")
        return result

    elif operation.type == OperationType.GET_CALL_DETAILS:
        from ..services.calls.local_call_search_service import LocalCallSearchService
        service = LocalCallSearchService()
        call_id = params.get("call_id")
        if not call_id:
            raise ValueError("'call_id' parameter required")
        result = await service.get_call_details(call_id)
        return result

    elif operation.type == OperationType.FIND_PARTNERS:
        from ..services.tools.partner_discovery_tool import PartnerDiscoveryTool
        tool = PartnerDiscoveryTool()
        result = await tool.find_partners(
            research_area=params.get("research_area", params.get("keywords", "")),
            country=params.get("country"),
            organization_type=params.get("organization_type"),
            limit=params.get("limit", 10)
        )
        return result

    elif operation.type == OperationType.GET_BUDGET_BENCHMARK:
        from ..services.tools.budget_benchmark_tool import BudgetBenchmarkTool
        tool = BudgetBenchmarkTool()
        result = await tool.get_budget_benchmark(
            action_type=params.get("action_type", "RIA"),
            cluster=params.get("cluster"),
            topic_keywords=params.get("topic_keywords"),
            budget_range=params.get("budget_range")
        )
        return result

    elif operation.type == OperationType.GET_CONSORTIUM_PATTERNS:
        from ..services.tools.consortium_patterns_tool import ConsortiumPatternsTool
        tool = ConsortiumPatternsTool()
        result = await tool.get_consortium_patterns(
            action_type=params.get("action_type", "RIA"),
            cluster=params.get("cluster"),
            topic_keywords=params.get("topic_keywords")
        )
        return result

    elif operation.type == OperationType.FIND_SIMILAR_PROJECTS:
        from ..services.tools.similar_projects_tool import SimilarProjectsTool
        tool = SimilarProjectsTool()
        result = await tool.find_similar(
            description=params.get("description", ""),
            cluster=params.get("cluster"),
            limit=params.get("limit", 10)
        )
        return result

    else:
        raise ValueError(f"Unknown operation type: {operation.type}")


async def process_batch_background(batch_id: str, request: BatchRequest):
    """Process batch operations in background."""
    logger.info(f"Starting background batch processing: {batch_id}")

    try:
        # Update status to processing
        await store_batch_status(batch_id, {
            "batch_id": batch_id,
            "status": "processing",
            "total_operations": len(request.operations),
            "completed_operations": 0,
            "failed_operations": 0,
            "progress_percent": 0.0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "results": {},
            "error": None
        })

        results = {}
        completed = 0
        failed = 0

        # Execute operations with configured concurrency
        for i, operation in enumerate(request.operations):
            try:
                result = await asyncio.wait_for(
                    execute_operation(operation),
                    timeout=30.0  # Per-operation timeout
                )
                results[operation.id] = result.dict()

                if result.success:
                    completed += 1
                else:
                    failed += 1
                    if request.fail_fast:
                        break

            except asyncio.TimeoutError:
                failed += 1
                results[operation.id] = OperationResult(
                    id=operation.id,
                    success=False,
                    error="Operation timed out",
                    execution_time_ms=30000.0
                ).dict()
                if request.fail_fast:
                    break

            # Update progress
            progress = ((i + 1) / len(request.operations)) * 100
            await store_batch_status(batch_id, {
                "batch_id": batch_id,
                "status": "processing",
                "total_operations": len(request.operations),
                "completed_operations": completed,
                "failed_operations": failed,
                "progress_percent": round(progress, 1),
                "started_at": (await get_batch_status(batch_id))["started_at"],
                "completed_at": None,
                "results": results,
                "error": None
            })

        # Mark as completed
        final_status = "completed" if failed == 0 else ("partial" if completed > 0 else "failed")
        await store_batch_status(batch_id, {
            "batch_id": batch_id,
            "status": final_status,
            "total_operations": len(request.operations),
            "completed_operations": completed,
            "failed_operations": failed,
            "progress_percent": 100.0,
            "started_at": (await get_batch_status(batch_id))["started_at"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "results": results,
            "error": None
        })

        logger.info(f"Batch {batch_id} completed: {completed}/{len(request.operations)} succeeded")

    except Exception as e:
        logger.error(f"Batch {batch_id} failed: {e}")
        await store_batch_status(batch_id, {
            "batch_id": batch_id,
            "status": "failed",
            "total_operations": len(request.operations),
            "completed_operations": 0,
            "failed_operations": len(request.operations),
            "progress_percent": 0.0,
            "started_at": (await get_batch_status(batch_id) or {}).get("started_at"),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "results": None,
            "error": str(e)
        })


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/execute", response_model=BatchResponse)
async def execute_batch(request: BatchRequest) -> BatchResponse:
    """
    Execute multiple operations in parallel.

    This endpoint executes all operations concurrently and returns
    when all have completed (or the timeout is reached).

    **Use Cases:**
    - Fetch multiple project details at once
    - Search multiple clusters in parallel
    - Get statistics for multiple countries

    **Example Request:**
    ```json
    {
        "operations": [
            {"id": "stats-eic", "type": "get_statistics", "params": {"programme": "EIC"}},
            {"id": "stats-erc", "type": "get_statistics", "params": {"programme": "ERC"}},
            {"id": "search-hydrogen", "type": "search_projects", "params": {"keywords": "hydrogen"}}
        ],
        "timeout_seconds": 30
    }
    ```
    """
    batch_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info(f"Executing batch {batch_id} with {len(request.operations)} operations")

    try:
        # Execute all operations in parallel with overall timeout
        tasks = [execute_operation(op) for op in request.operations]
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=request.timeout_seconds
        )

        # Process results
        response_results = {}
        completed = 0
        failed = 0

        for operation, result in zip(request.operations, results):
            if isinstance(result, Exception):
                response_results[operation.id] = OperationResult(
                    id=operation.id,
                    success=False,
                    error=str(result),
                    execution_time_ms=0.0
                )
                failed += 1
            else:
                response_results[operation.id] = result
                if result.success:
                    completed += 1
                else:
                    failed += 1

        processing_time = (time.time() - start_time) * 1000
        status = "completed" if failed == 0 else ("partial" if completed > 0 else "failed")

        return BatchResponse(
            batch_id=batch_id,
            results=response_results,
            completed=completed,
            failed=failed,
            total=len(request.operations),
            processing_time_ms=round(processing_time, 2),
            status=status
        )

    except asyncio.TimeoutError:
        processing_time = (time.time() - start_time) * 1000
        logger.warning(f"Batch {batch_id} timed out after {request.timeout_seconds}s")

        raise HTTPException(
            status_code=504,
            detail={
                "error": "BATCH_TIMEOUT",
                "message": f"Batch operation timed out after {request.timeout_seconds} seconds",
                "batch_id": batch_id
            }
        )


@router.post("/async", response_model=AsyncBatchResponse)
async def execute_batch_async(
    request: BatchRequest,
    background_tasks: BackgroundTasks
) -> AsyncBatchResponse:
    """
    Execute batch operations asynchronously.

    Returns immediately with a batch ID that can be used to poll for status.
    Use this for large batches or when you don't need immediate results.

    **Example Request:**
    ```json
    {
        "operations": [
            {"id": "op1", "type": "search_projects", "params": {"keywords": "AI"}},
            {"id": "op2", "type": "search_projects", "params": {"keywords": "ML"}}
        ]
    }
    ```

    **Example Response:**
    ```json
    {
        "batch_id": "abc-123",
        "status": "pending",
        "total_operations": 2,
        "status_url": "/api/batch/abc-123/status"
    }
    ```
    """
    batch_id = str(uuid.uuid4())

    logger.info(f"Starting async batch {batch_id} with {len(request.operations)} operations")

    # Initialize batch status
    await store_batch_status(batch_id, {
        "batch_id": batch_id,
        "status": "pending",
        "total_operations": len(request.operations),
        "completed_operations": 0,
        "failed_operations": 0,
        "progress_percent": 0.0,
        "started_at": None,
        "completed_at": None,
        "results": None,
        "error": None
    })

    # Start background processing
    background_tasks.add_task(process_batch_background, batch_id, request)

    return AsyncBatchResponse(
        batch_id=batch_id,
        status="pending",
        total_operations=len(request.operations),
        status_url=f"/api/batch/{batch_id}/status",
        created_at=datetime.now(timezone.utc).isoformat()
    )


@router.get("/{batch_id}/status", response_model=BatchStatus)
async def get_batch_status_endpoint(batch_id: str) -> BatchStatus:
    """
    Get the status of an async batch operation.

    Poll this endpoint to check progress and retrieve results when complete.

    **Status Values:**
    - `pending`: Batch is queued but not started
    - `processing`: Batch is currently being processed
    - `completed`: All operations completed successfully
    - `partial`: Some operations failed
    - `failed`: All operations failed or batch-level error
    """
    status = await get_batch_status(batch_id)

    if not status:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "BATCH_NOT_FOUND",
                "message": f"Batch {batch_id} not found"
            }
        )

    return BatchStatus(**status)


@router.delete("/{batch_id}")
async def cancel_batch(batch_id: str) -> Dict[str, Any]:
    """
    Cancel a pending or processing batch operation.

    Note: Operations that have already started may still complete.
    """
    status = await get_batch_status(batch_id)

    if not status:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "BATCH_NOT_FOUND",
                "message": f"Batch {batch_id} not found"
            }
        )

    if status["status"] in ["completed", "failed", "partial"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "BATCH_ALREADY_FINISHED",
                "message": f"Batch {batch_id} has already finished with status: {status['status']}"
            }
        )

    # Mark as cancelled
    await store_batch_status(batch_id, {
        **status,
        "status": "cancelled",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "error": "Batch cancelled by user"
    })

    logger.info(f"Batch {batch_id} cancelled by user")

    return {
        "batch_id": batch_id,
        "status": "cancelled",
        "message": "Batch cancellation requested"
    }


@router.get("/types")
async def list_operation_types() -> Dict[str, Any]:
    """
    List all available batch operation types and their parameters.
    """
    return {
        "operation_types": {
            "search_calls": {
                "description": "Search for funding calls",
                "params": {
                    "keywords": {"type": "string", "required": False},
                    "status": {"type": "string", "enum": ["open", "upcoming", "closed"]},
                    "cluster": {"type": "string", "example": "CLUSTER-5"},
                    "limit": {"type": "integer", "default": 10, "max": 100}
                }
            },
            "search_projects": {
                "description": "Search for funded projects",
                "params": {
                    "keywords": {"type": "string", "required": False},
                    "cluster": {"type": "string"},
                    "action_type": {"type": "string", "enum": ["RIA", "IA", "CSA"]},
                    "limit": {"type": "integer", "default": 10}
                }
            },
            "get_statistics": {
                "description": "Get programme or country statistics",
                "params": {
                    "programme": {"type": "string", "example": "EIC"},
                    "country": {"type": "string", "example": "DE"}
                }
            },
            "get_project_details": {
                "description": "Get details for a specific project",
                "params": {
                    "project_id": {"type": "string", "required": True},
                    "rcn": {"type": "string", "alternative_to": "project_id"}
                }
            },
            "get_call_details": {
                "description": "Get details for a specific call",
                "params": {
                    "call_id": {"type": "string", "required": True}
                }
            },
            "find_partners": {
                "description": "Find potential consortium partners",
                "params": {
                    "research_area": {"type": "string"},
                    "country": {"type": "string"},
                    "organization_type": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                }
            },
            "get_budget_benchmark": {
                "description": "Get budget benchmarks for proposals",
                "params": {
                    "action_type": {"type": "string", "default": "RIA"},
                    "cluster": {"type": "string"},
                    "topic_keywords": {"type": "string"}
                }
            },
            "get_consortium_patterns": {
                "description": "Get consortium composition patterns",
                "params": {
                    "action_type": {"type": "string", "default": "RIA"},
                    "cluster": {"type": "string"}
                }
            },
            "find_similar_projects": {
                "description": "Find semantically similar projects",
                "params": {
                    "description": {"type": "string", "required": True},
                    "cluster": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                }
            }
        },
        "limits": {
            "max_operations_per_batch": 50,
            "max_timeout_seconds": 300,
            "default_timeout_seconds": 60
        }
    }
