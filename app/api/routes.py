"""
API route definitions for the CORDIS RAG application.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, Dict, Any
import asyncio
import random
import time
import json
import logging

from ..models.schemas import (
    QuestionRequest, SearchResponse, ErrorResponse, HealthResponse,
    TaskStatusResponse, DatabaseStatusResponse, ProvidersResponse,
    BenchmarkResponse, ProviderConfig
)
from ..core.config import settings
from ..services.enhanced_rag_service import HorizonEuropeRAG

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Try to import Celery tasks
try:
    from ..services.celery_app import (
        process_rag_query, process_rag_query_stream, 
        get_task_result, cancel_task
    )
    CELERY_AVAILABLE = True
    logger.info("✅ Celery integration available for concurrent processing")
except ImportError as e:
    logger.warning(f"⚠️ Celery not available: {e}. Falling back to thread pool.")
    CELERY_AVAILABLE = False


# Health and Status Endpoints
@router.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint - health check."""
    return {
        "message": f"Welcome to {settings.app_name} v{settings.app_version}",
        "status": "healthy",
        "docs": "/docs"
    }


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        # Check AI providers
        available_providers = []
        if settings.openai_api_key:
            available_providers.append("openai")
        if settings.gemini_api_key:
            available_providers.append("gemini")
        
        # Check database connection if enabled
        database_connected = None
        if settings.use_local_db:
            try:
                # Simple connection test
                database_connected = True  # TODO: Implement actual DB check
            except Exception:
                database_connected = False
        
        return HealthResponse(
            status="healthy",
            timestamp=time.time(),
            version=settings.app_version,
            database_connected=database_connected,
            celery_available=CELERY_AVAILABLE,
            ai_providers=available_providers
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


# Main Query Endpoints
@router.post("/api/query", response_model=SearchResponse)
async def query_projects(request: QuestionRequest):
    """
    Main endpoint for querying European research projects.
    Now supports conversation context for follow-up questions.
    """
    try:
        if CELERY_AVAILABLE:
            # Use Celery for async processing
            task = process_rag_query.delay(
                question=request.question,
                max_results=request.max_results or 5,
                ai_provider=request.ai_provider,
                ai_version=request.ai_version or "V9",
                use_local_db=request.use_local_db
            )
            
            # Wait for result (you might want to make this truly async)
            result = task.get(timeout=settings.task_time_limit)
            
            if result.get("success", False):
                return SearchResponse(**result)
            else:
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "Unknown error occurred")
                )
        else:
            # Fallback to direct processing with conversation context
            return await _process_query_direct_with_context(request)
            
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/query/async")
async def query_projects_async(request: QuestionRequest):
    """
    Start an async query and return task ID for polling.
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Async processing not available. Celery is not configured."
        )
    
    try:
        task = process_rag_query.delay(
            question=request.question,
            max_results=request.max_results or 5,
            ai_provider=request.ai_provider,
            ai_version=request.ai_version or "V9",
            use_local_db=request.use_local_db
        )
        
        return {"task_id": task.id, "status": "started"}
        
    except Exception as e:
        logger.error(f"Async query start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/query/stream")
async def query_projects_stream_get(
    question: str,
    max_results: Optional[int] = 5,
    ai_provider: Optional[str] = None,
    ai_version: Optional[str] = "V9"
):
    """
    Streaming endpoint for querying projects via GET request (for frontend compatibility).
    Returns Server-Sent Events (SSE) stream.
    """
    return await _handle_streaming_request(
        question=question,
        max_results=max_results,
        ai_provider=ai_provider,
        ai_version=ai_version
    )


@router.post("/api/query/stream")
async def query_projects_stream_post(request: QuestionRequest):
    """
    Streaming endpoint for querying projects via POST request.
    Returns Server-Sent Events (SSE) stream.
    """
    return await _handle_streaming_request(
        question=request.question,
        max_results=request.max_results or 5,
        ai_provider=request.ai_provider,
        ai_version=request.ai_version or "V9",
        use_local_db=request.use_local_db
    )


async def _handle_streaming_request(
    question: str,
    max_results: int = 5,
    ai_provider: Optional[str] = None,
    ai_version: str = "V9",
    use_local_db: Optional[bool] = None
):
    """Handle streaming requests with Server-Sent Events."""
    
    async def generate_stream():
        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting query processing...'})}\n\n"
            
            if CELERY_AVAILABLE:
                # Use Celery for async processing
                task = process_rag_query_stream.delay(
                    question=question,
                    max_results=max_results,
                    ai_provider=ai_provider,
                    ai_version=ai_version,
                    use_local_db=use_local_db
                )
                
                yield f"data: {json.dumps({'type': 'task_started', 'task_id': task.id})}\n\n"
                
                # Poll for results
                while not task.ready():
                    await asyncio.sleep(1)
                    yield f"data: {json.dumps({'type': 'processing', 'message': 'Processing query...'})}\n\n"
                
                # Get final result
                if task.successful():
                    result = task.result
                    if result.get("success", False):
                        # Extract the answer content properly
                        answer_content = result.get('answer', '')
                        
                        # Handle case where answer_content is a stringified dict
                        if isinstance(answer_content, str):
                            # Check if it looks like a stringified dictionary
                            if answer_content.startswith("{'") and "'answer':" in answer_content:
                                try:
                                    import ast
                                    parsed_result = ast.literal_eval(answer_content)
                                    if isinstance(parsed_result, dict) and 'answer' in parsed_result:
                                        answer_content = parsed_result['answer']
                                except (ValueError, SyntaxError) as e:
                                    logger.warning(f"Failed to parse stringified dict: {e}")
                                    # If parsing fails, use the original string
                                    pass
                        
                        # Ensure answer_content is a string for JSON serialization
                        if not isinstance(answer_content, str):
                            answer_content = str(answer_content)
                        
                        # Send the complete answer
                        yield f"data: {json.dumps({'type': 'answer', 'content': answer_content})}\n\n"
                        
                        # Send metadata
                        metadata = {
                            'type': 'metadata',
                            'ai_provider': result.get('ai_provider'),
                            'ai_version': result.get('ai_version'),
                            'processing_time': result.get('processing_time'),
                            'projects_found': result.get('projects_found', 0),
                            'data_source': result.get('data_source', 'CORDIS API')
                        }
                        yield f"data: {json.dumps(metadata)}\n\n"
                        
                        # Send completion
                        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'error': result.get('error', 'Unknown error')})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'error': 'Task failed', 'details': str(task.result)})}\n\n"
            
            else:
                # Fallback to direct processing with simulated streaming
                yield f"data: {json.dumps({'type': 'status', 'message': 'Processing with direct method...'})}\n\n"
                
                try:
                    # Simulate processing steps
                    steps = [
                        "Analyzing question...",
                        "Extracting search terms...",
                        "Searching CORDIS database...",
                        "Processing results...",
                        "Generating response..."
                    ]
                    
                    for i, step in enumerate(steps):
                        yield f"data: {json.dumps({'type': 'progress', 'step': i+1, 'total': len(steps), 'message': step})}\n\n"
                        await asyncio.sleep(0.5)  # Simulate processing time
                    
                    # Process the actual query
                    result = await _process_query_direct(QuestionRequest(
                        question=question,
                        max_results=max_results,
                        ai_provider=ai_provider,
                        ai_version=ai_version,
                        use_local_db=use_local_db
                    ))
                    
                    # Stream the answer in chunks (simulate streaming)
                    if result.answer:
                        words = result.answer.split()
                        current_chunk = ""
                        
                        for word in words:
                            current_chunk += word + " "
                            if len(current_chunk.split()) % 10 == 0:  # Send every 10 words
                                yield f"data: {json.dumps({'type': 'chunk', 'content': current_chunk.strip()})}\n\n"
                                current_chunk = ""
                                await asyncio.sleep(0.1)
                        
                        # Send remaining chunk
                        if current_chunk.strip():
                            yield f"data: {json.dumps({'type': 'chunk', 'content': current_chunk.strip()})}\n\n"
                    
                    # Send metadata
                    metadata = {
                        'type': 'metadata',
                        'ai_provider': result.ai_provider,
                        'ai_version': result.ai_version,
                        'processing_time': result.processing_time,
                        'projects_found': result.projects_found,
                        'data_source': result.data_source
                    }
                    yield f"data: {json.dumps(metadata)}\n\n"
                    
                    # Send completion
                    yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                    
                except Exception as e:
                    logger.error(f"Direct streaming processing failed: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'error': 'Processing failed', 'details': str(e)})}\n\n"
                    
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': 'Streaming error', 'details': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST",
            "Access-Control-Allow-Headers": "*"
        }
    )


@router.get("/api/query/status/{task_id}", response_model=TaskStatusResponse)
async def get_query_status(task_id: str):
    """Get the status of an async query."""
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Async processing not available. Celery is not configured."
        )
    
    try:
        result = get_task_result(task_id)
        return TaskStatusResponse(**result)
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/query/{task_id}")
async def cancel_query(task_id: str):
    """Cancel a running async query."""
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Async processing not available. Celery is not configured."
        )
    
    try:
        result = cancel_task(task_id)
        return result
    except Exception as e:
        logger.error(f"Task cancellation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Demo and Testing Endpoints
@router.post("/api/demo")
async def demo_endpoint(request: QuestionRequest):
    """
    Demo endpoint that returns simulated responses for UI testing.
    """
    # Simulate processing time
    await asyncio.sleep(random.uniform(2.0, 4.0))
    
    demo_responses = [
        "Based on the European research projects data, there are several notable AI initiatives in healthcare currently being funded through Horizon Europe...",
        "According to the CORDIS database, renewable energy research is being prioritized with significant funding allocated to solar, wind, and battery technologies...",
        "The European Union is investing heavily in quantum computing research, with multiple projects involving leading universities and research institutions..."
    ]
    
    return {
        "answer": random.choice(demo_responses),
        "demo": True,
        "processing_time": f"{random.uniform(2.0, 5.0):.2f} seconds",
        "query": request.question,
        "ai_provider": "demo",
        "ai_version": "demo",
        "projects_found": random.randint(3, 15),
        "success": True
    }


# Information Endpoints
@router.get("/api/providers", response_model=ProvidersResponse)
async def get_available_providers():
    """Get information about available AI providers."""
    available_providers = {}
    
    # Only show current version V9 with available providers
    v9_providers = {}
    
    # Add OpenAI if API key is available
    if settings.openai_api_key:
        v9_providers["openai"] = ProviderConfig(
            model=settings.openai_model,
            is_default=(settings.default_ai_provider == "openai")
        )
    
    # Add Gemini if API key is available  
    if settings.gemini_api_key:
        v9_providers["gemini"] = ProviderConfig(
            model=settings.gemini_model,
            is_default=(settings.default_ai_provider == "gemini")
        )
    
    available_providers["V9"] = v9_providers
    
    return ProvidersResponse(
        available_providers=available_providers,
        default_provider=settings.default_ai_provider
    )


@router.get("/api/database/status", response_model=DatabaseStatusResponse)
async def get_database_status():
    """Get database connection status and statistics."""
    if not settings.use_local_db:
        return DatabaseStatusResponse(
            connected=False,
            total_projects=None,
            last_updated=None
        )
    
    try:
        # TODO: Implement actual database status check
        return DatabaseStatusResponse(
            connected=True,
            total_projects=0,  # Placeholder
            last_updated="N/A",
            connection_pool_status={"status": "healthy"}
        )
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return DatabaseStatusResponse(
            connected=False,
            total_projects=None,
            last_updated=None
        )


# Helper Functions
async def _process_query_direct_with_context(request: QuestionRequest) -> SearchResponse:
    """
    Direct query processing with conversation context support.
    """
    start_time = time.time()
    
    try:
        # Determine AI provider
        provider = request.ai_provider or settings.default_ai_provider
        if provider == "openai" and not settings.openai_api_key:
            provider = "gemini"
        elif provider == "gemini" and not settings.gemini_api_key:
            provider = "openai"
        
        # Create Enhanced RAG instance (vector docs + calls + projects)
        rag_instance = HorizonEuropeRAG()
        
        # Check if this is a conversation context request
        if request.conversation_id:
            try:
                from app.services.conversation_context_service import ConversationContextService
                context_service = ConversationContextService(settings.database_url)
                context = context_service.load_context(request.conversation_id)
                
                # Use context-aware processing
                # Use enhanced RAG entry; it internally routes and can be extended to accept context
                result = rag_instance.answer_question(request.question)
                
                # Update context with new information
                context_service.update_context(
                    request.conversation_id,
                    {'text': request.question, 'sender': 'user'},
                    result
                )
                
            except Exception as context_error:
                logger.warning(f"Context processing failed, falling back to regular processing: {context_error}")
                # Fallback to regular processing
                result = rag_instance.answer_question(request.question)
        else:
            # Regular processing without context
            result = rag_instance.answer_question(request.question)
        
        processing_time = time.time() - start_time
        
        # Format response based on result type
        if isinstance(result, dict):
            return SearchResponse(
                answer=result.get('answer', ''),
                ai_provider=provider,
                ai_version=request.ai_version or "V9",
                model_used=result.get('model_used', settings.openai_model if provider == "openai" else settings.gemini_model),
                data_source=result.get('data_source', 'Horizon Europe RAG'),
                processing_time=round(processing_time, 2),
                projects_found=result.get('projects_found', 0),
                success=result.get('success', True)
            )
        else:
            return SearchResponse(
                answer=str(result),
                ai_provider=provider,
                ai_version=request.ai_version or "V9",
                model_used=settings.openai_model if provider == "openai" else settings.gemini_model,
                data_source="Horizon Europe RAG",
                processing_time=round(processing_time, 2),
                projects_found=0,
                success=True
            )
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Context-aware query processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )

async def _process_query_direct(request: QuestionRequest) -> SearchResponse:
    """
    Legacy direct query processing function (kept for compatibility).
    """
    start_time = time.time()
    
    try:
        # Determine AI provider
        provider = request.ai_provider or settings.default_ai_provider
        if provider == "openai" and not settings.openai_api_key:
            provider = "gemini"
        elif provider == "gemini" and not settings.gemini_api_key:
            provider = "openai"
        
        # Create Enhanced RAG instance (vector docs + calls + projects)
        rag_instance = HorizonEuropeRAG()
        
        # Process query
        result = rag_instance.get_ai_response(
            request.question,
            max_projects_to_process=request.max_results or 5
        )
        
        processing_time = time.time() - start_time
        
        # Format response based on result type
        if isinstance(result, dict) and 'logs' in result:
            return SearchResponse(
                answer=result.get('answer', ''),
                logs=result.get('logs', {}),
                ai_provider=provider,
                ai_version=request.ai_version or "V9",
                model_used=result.get('logs', {}).get('model_used', settings.openai_model if provider == "openai" else settings.gemini_model),
                data_source=result.get('logs', {}).get('data_source', 'CORDIS API'),
                processing_time=round(processing_time, 2),
                projects_found=result.get('logs', {}).get('projects_retrieved', 0),
                success=True
            )
        else:
            return SearchResponse(
                answer=str(result),
                ai_provider=provider,
                ai_version=request.ai_version or "V9",
                model_used=settings.openai_model if provider == "openai" else settings.gemini_model,
                data_source="CORDIS API",
                processing_time=round(processing_time, 2),
                projects_found=0,
                success=True
            )
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Direct query processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )
