import os
import json
import time
import asyncio
from typing import Dict, Any, Optional, List
from celery import Celery, Task
from celery.result import AsyncResult
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import RAG classes at module level to avoid import issues in worker processes
try:
    from cordisBased_RAG_function_new_V2 import CordisRAG as CordisRAG_V2
    logger.info("Successfully imported CordisRAG_V2")
except ImportError as e:
    logger.warning(f"Could not import V2: {e}")
    CordisRAG_V2 = None

try:
    from cordisBased_RAG_function_new_V3 import CordisRAG as CordisRAG_V3
    logger.info("Successfully imported CordisRAG_V3")
except ImportError as e:
    logger.warning(f"Could not import V3: {e}")
    CordisRAG_V3 = None

try:
    from cordisBased_RAG_function_new_V4 import CordisRAG as CordisRAG_V4
    logger.info("Successfully imported CordisRAG_V4")
except ImportError as e:
    logger.warning(f"Could not import V4: {e}")
    CordisRAG_V4 = None

try:
    from cordisBased_RAG_function_new_V5 import CordisRAG as CordisRAG_V5
    logger.info("Successfully imported CordisRAG_V5")
except ImportError as e:
    logger.warning(f"Could not import V5: {e}")
    CordisRAG_V5 = None

try:
    from cordisBased_RAG_function_new_V6 import CordisRAG as CordisRAG_V6
    logger.info("Successfully imported CordisRAG_V6")
except ImportError as e:
    logger.warning(f"Could not import V6: {e}")
    CordisRAG_V6 = None

try:
    from cordisBased_RAG_function_new_V7 import CordisRAG as CordisRAG_V7
    logger.info("Successfully imported CordisRAG_V7")
except ImportError as e:
    logger.warning(f"Could not import V7: {e}")
    CordisRAG_V7 = None

try:
    from cordisBased_RAG_function_new_V8 import CordisRAG as CordisRAG_V8
    logger.info("Successfully imported CordisRAG_V8")
except ImportError as e:
    logger.warning(f"Could not import V8: {e}")
    CordisRAG_V8 = None

# Celery configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RABBITMQ_URL = os.getenv("CELERY_BROKER_URL", "pyamqp://guest@localhost//")

# Use Redis if available, fallback to RabbitMQ
BROKER_URL = REDIS_URL if "redis://" in REDIS_URL else RABBITMQ_URL

# Create Celery app
celery_app = Celery(
    "cordis_rag_tasks",
    broker=BROKER_URL,
    backend=REDIS_URL if "redis://" in REDIS_URL else "rpc://",
    include=["celery_app"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,  # Ensure fair distribution
    worker_max_tasks_per_child=50,  # Restart workers periodically
    result_expires=3600,  # Keep results for 1 hour
    task_routes={
        "celery_app.process_rag_query": {"queue": "rag_queries"},
        "celery_app.process_rag_query_stream": {"queue": "rag_streams"},
    },
    task_annotations={
        "*": {"rate_limit": "10/s"}  # Overall rate limiting
    }
)

# Custom task class for better error handling
class CallbackTask(Task):
    """Custom task class with better error handling and logging."""
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {task_id} completed successfully")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(f"Task {task_id} retrying: {exc}")

def _process_rag_core(question: str, max_results: int = 5, 
                     ai_provider: Optional[str] = None, ai_version: str = "V8", 
                     use_local_db: Optional[bool] = None, task_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Core RAG processing logic shared between tasks.
    
    Args:
        question: The user's question
        max_results: Maximum number of projects to retrieve
        ai_provider: AI provider to use ("openai" or "gemini")
        ai_version: RAG version to use
        use_local_db: Whether to use local database
        task_id: Optional task ID for logging
    
    Returns:
        Dict containing the response and metadata
    """
    start_time = time.time()
    
    logger.info(f"[Task {task_id}] Starting RAG query: '{question}' (v{ai_version}, {ai_provider})")
    
    try:
        # Version mapping (classes imported at module level)
        version_classes = {
            "V2": CordisRAG_V2,
            "V3": CordisRAG_V3,
            "V4": CordisRAG_V4,
            "V5": CordisRAG_V5,
            "V6": CordisRAG_V6,
            "V7": CordisRAG_V7,
            "V8": CordisRAG_V8
        }
        
        # Validate version
        if ai_version not in version_classes:
            raise ValueError(f"Invalid AI version: {ai_version}")
        
        rag_class = version_classes[ai_version]
        if rag_class is None:
            logger.warning(f"Version {ai_version} not available, falling back to V6")
            rag_class = CordisRAG_V6
            ai_version = "V6"
            if rag_class is None:
                logger.error("V6 is also not available, falling back to V8")
                rag_class = CordisRAG_V8
                ai_version = "V8"
                if rag_class is None:
                    raise ValueError("No RAG versions available - all imports failed")
        
        # Get configuration
        openai_model = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite-preview-06-17")
        default_provider = os.getenv("DEFAULT_AI_PROVIDER", "gemini").lower()
        default_use_local_db = os.getenv("USE_LOCAL_DB", "false").lower() == "true"
        database_url = os.getenv("DATABASE_URL")
        
        # Docker-aware database URL handling
        if database_url and "localhost" in database_url:
            if os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV") == "true":
                database_url = database_url.replace("localhost", "host.docker.internal")
        
        # Determine provider
        available_providers = [p for p in ['openai', 'gemini'] if os.getenv(f'{p.upper()}_API_KEY')]
        if not available_providers:
            raise ValueError("No AI providers configured (missing API keys)")
        
        if ai_provider and ai_provider.lower() in available_providers:
            provider = ai_provider.lower()
        elif default_provider in available_providers:
            provider = default_provider
        else:
            provider = available_providers[0]
        
        # Determine database usage
        request_use_local_db = use_local_db if use_local_db is not None else default_use_local_db
        
        # Create RAG instance
        logger.info(f"[Task {task_id}] Creating {provider} {ai_version} RAG instance (DB: {request_use_local_db})")
        
        if provider == "openai":
            if ai_version in ["V5", "V6", "V7", "V8"]:
                rag_instance = rag_class(
                    ai_provider="openai",
                    openai_model_name=openai_model,
                    use_local_db=request_use_local_db,
                    database_url=database_url
                )
            else:
                rag_instance = rag_class(
                    ai_provider="openai",
                    openai_model_name=openai_model
                )
        elif provider == "gemini":
            if ai_version in ["V5", "V6", "V7", "V8"]:
                rag_instance = rag_class(
                    ai_provider="gemini",
                    gemini_model_name=gemini_model,
                    use_local_db=request_use_local_db,
                    database_url=database_url
                )
            else:
                rag_instance = rag_class(
                    ai_provider="gemini",
                    gemini_model_name=gemini_model
                )
        else:
            raise ValueError(f"Invalid AI provider: {provider}")
        
        # Process the query
        logger.info(f"[Task {task_id}] Processing query with {ai_version}")
        result = rag_instance.get_ai_response(question, max_projects_to_process=max_results)
        
        processing_time = time.time() - start_time
        
        # Handle different return formats
        if ai_version in ["V6", "V7", "V8"] and isinstance(result, dict) and 'logs' in result:
            # V6+ returns a dictionary with answer and logs
            response_data = {
                "answer": result.get('answer', ''),
                "logs": result.get('logs', {}),
                "ai_provider": provider,
                "ai_version": ai_version,
                "model_used": result.get('logs', {}).get('model_used', openai_model if provider == "openai" else gemini_model),
                "data_source": result.get('logs', {}).get('data_source', 'CORDIS API'),
                "processing_time": round(processing_time, 2),
                "projects_found": result.get('logs', {}).get('projects_retrieved', 0),
                "task_id": task_id,
                "success": True
            }
        else:
            # V2-V5 return a string answer
            answer = result if isinstance(result, str) else str(result)
            data_source = "Local Database" if request_use_local_db and ai_version in ["V5", "V6", "V7", "V8"] else "CORDIS API"
            
            response_data = {
                "answer": answer,
                "ai_provider": provider,
                "ai_version": ai_version,
                "model_used": openai_model if provider == "openai" else gemini_model,
                "data_source": data_source,
                "processing_time": round(processing_time, 2),
                "projects_found": answer.count("🔗") if answer else 0,
                "task_id": task_id,
                "success": True
            }
        
        logger.info(f"[Task {task_id}] Completed successfully in {processing_time:.2f}s")
        return response_data
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = str(e)
        logger.error(f"[Task {task_id}] Failed after {processing_time:.2f}s: {error_msg}")
        
        return {
            "success": False,
            "error": "Error processing request",
            "details": error_msg,
            "task_id": task_id,
            "processing_time": round(processing_time, 2)
        }

@celery_app.task(bind=True, base=CallbackTask, name="celery_app.process_rag_query")
def process_rag_query(self, question: str, max_results: int = 5, 
                     ai_provider: Optional[str] = None, ai_version: str = "V8", 
                     use_local_db: Optional[bool] = None) -> Dict[str, Any]:
    """
    Process a RAG query in a Celery worker.
    
    Args:
        question: The user's question
        max_results: Maximum number of projects to retrieve
        ai_provider: AI provider to use ("openai" or "gemini")
        ai_version: RAG version to use
        use_local_db: Whether to use local database
    
    Returns:
        Dict containing the response and metadata
    """
    task_id = self.request.id
    
    # Update task progress
    self.update_state(state="PROCESSING", meta={"message": "RAG instance created, processing query..."})
    
    # Use the shared core processing logic
    return _process_rag_core(question, max_results, ai_provider, ai_version, use_local_db, task_id)

@celery_app.task(bind=True, base=CallbackTask, name="celery_app.process_rag_query_stream")
def process_rag_query_stream(self, question: str, max_results: int = 5, 
                           ai_provider: Optional[str] = None, ai_version: str = "V8", 
                           use_local_db: Optional[bool] = None) -> Dict[str, Any]:
    """
    Process a RAG query for streaming in a Celery worker.
    
    Note: This returns the complete response since true streaming across Celery
    is complex. The FastAPI endpoint will simulate streaming from this result.
    """
    task_id = self.request.id
    
    logger.info(f"[Stream Task {task_id}] Starting RAG stream query: '{question}' (v{ai_version}, {ai_provider})")
    
    try:
        # Use the same core processing logic
        result = _process_rag_core(question, max_results, ai_provider, ai_version, use_local_db, task_id)
        
        # Add streaming metadata
        if result.get("success", False):
            result["stream_mode"] = True
            result["stream_task_id"] = task_id
        else:
            result["stream_mode"] = True
        
        return result
        
    except Exception as e:
        logger.error(f"[Stream Task {task_id}] Failed: {str(e)}")
        
        return {
            "success": False,
            "error": "Error processing stream request",
            "details": str(e),
            "task_id": task_id,
            "stream_mode": True
        }

@celery_app.task(name="celery_app.health_check")
def health_check() -> Dict[str, Any]:
    """Health check task for Celery workers."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "worker_id": os.getpid()
    }

# Utility functions for task management
def get_task_result(task_id: str) -> Dict[str, Any]:
    """Get the result of a Celery task."""
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        if result.ready():
            if result.successful():
                return {
                    "status": "completed",
                    "result": result.result,
                    "task_id": task_id
                }
            else:
                return {
                    "status": "failed",
                    "error": str(result.result),
                    "task_id": task_id
                }
        else:
            return {
                "status": "pending",
                "progress": result.info if result.info else {},
                "task_id": task_id
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "task_id": task_id
        }

def cancel_task(task_id: str) -> Dict[str, Any]:
    """Cancel a Celery task."""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return {
            "status": "cancelled",
            "task_id": task_id
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "task_id": task_id
        }

if __name__ == "__main__":
    # Start Celery worker
    celery_app.start() 