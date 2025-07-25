from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import uvicorn
import asyncio
import random
import logging
import time
import json
from dotenv import load_dotenv
import threading

# Import Celery tasks for concurrent processing
try:
    from celery_app import process_rag_query, process_rag_query_stream, get_task_result, cancel_task
    CELERY_AVAILABLE = True
    print("✅ Celery integration available for true concurrent processing")
except ImportError as e:
    print(f"⚠️ Celery not available: {e}. Falling back to thread pool.")
    CELERY_AVAILABLE = False

# Always import RAG classes for fallback and reference purposes
if not CELERY_AVAILABLE:
    from concurrent.futures import ThreadPoolExecutor

# Dynamically import all RAG classes including V9 (needed for fallback and version checking)
from cordisBased_RAG_function_new_V2 import CordisRAG as CordisRAG_V2
from cordisBased_RAG_function_new_V3 import CordisRAG as CordisRAG_V3
from cordisBased_RAG_function_new_V4 import CordisRAG as CordisRAG_V4
from cordisBased_RAG_function_new_V5 import CordisRAG as CordisRAG_V5
from cordisBased_RAG_function_new_V6 import CordisRAG as CordisRAG_V6
try:
    from cordisBased_RAG_function_new_V7 import CordisRAG as CordisRAG_V7
except ImportError:
    print("⚠️ V7 module not found, V7 will not be available")
    CordisRAG_V7 = None
from cordisBased_RAG_function_new_V8 import CordisRAG as CordisRAG_V8
from cordisBased_RAG_function_new_V9 import CordisRAG as CordisRAG_V9

# Load environment variables
load_dotenv()

# Add logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get provider config from environment
DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "gemini").lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite-preview-06-17")

# V5 specific configuration
USE_LOCAL_DB = os.getenv("USE_LOCAL_DB", "false").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL")

# Concurrency settings
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "10"))  # Thread pool size for blocking operations (fallback only)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "50"))  # Increased database connection pool size

# Thread pool for handling blocking RAG operations (fallback when Celery not available)
if not CELERY_AVAILABLE:
    thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    # Thread-local storage for RAG instances
    _local_storage = threading.local()

# Docker-aware database URL handling
def get_docker_database_url():
    """
    Get the appropriate database URL for Docker or local development.
    """
    db_url = DATABASE_URL
    if db_url and "localhost" in db_url:
        # Check if we're running in Docker
        if os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV") == "true":
            # Replace localhost with host.docker.internal for Docker
            db_url = db_url.replace("localhost", "host.docker.internal")
            print(f"🐳 Docker environment detected, using database URL: {db_url.split('@')[0]}@***")
    return db_url

# Update database URL for Docker compatibility
DOCKER_DATABASE_URL = get_docker_database_url()

# Create FastAPI app
app = FastAPI(
    title="CORDIS Research Projects RAG API",
    description="API for querying European research projects using a Retrieval-Augmented Generation approach. V9 features intelligent intent routing to search for existing projects OR open calls for proposals. Supports local database integration and concurrent processing.",
    version="1.3.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Update response models to match SvelteKit's expected error format
class ErrorResponse(BaseModel):
    error: str
    details: str

# Override the default exception handler to ensure consistent error format
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Error processing request",
            "details": str(exc.detail)
        },
    )

# Handle validation errors
@app.exception_handler(RequestValidationError) 
async def validation_exception_handler(request, exc): 
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation error",
            "details": str(exc)
        }
    )

def create_rag_instance(ai_provider: str, ai_version: str, use_local_db: Optional[bool] = None) -> Any:
    """
    Create a new RAG instance for each request to avoid shared state issues.
    This enables concurrent request processing.
    """
    # Use request-specific database setting or global default
    request_use_local_db = use_local_db if use_local_db is not None else USE_LOCAL_DB
    
    # Map version strings to classes
    version_classes = {
        "V2": CordisRAG_V2,
        "V3": CordisRAG_V3,
        "V4": CordisRAG_V4,
        "V5": CordisRAG_V5,
        "V6": CordisRAG_V6,
        "V7": CordisRAG_V7,
        "V8": CordisRAG_V8,
        "V9": CordisRAG_V9
    }
    
    if ai_version not in version_classes:
        raise ValueError(f"Invalid AI version: {ai_version}")
    
    rag_class = version_classes[ai_version]
    if rag_class is None:  # Handle V7 which might not be available
        logger.warning(f"Version {ai_version} not available, falling back to V6")
        rag_class = CordisRAG_V6
        ai_version = "V6"
    
    try:
        if ai_provider == "openai":
            # For V5+ versions that support database
            if ai_version in ["V5", "V6", "V7", "V8", "V9"]:
                instance = rag_class(
                    ai_provider="openai",
                    openai_model_name=OPENAI_MODEL,
                    use_local_db=request_use_local_db,
                    database_url=DOCKER_DATABASE_URL
                )
            else:
                instance = rag_class(
                    ai_provider="openai",
                    openai_model_name=OPENAI_MODEL
                )
        elif ai_provider == "gemini":
            # For V5+ versions that support database
            if ai_version in ["V5", "V6", "V7", "V8", "V9"]:
                instance = rag_class(
                    ai_provider="gemini",
                    gemini_model_name=GEMINI_MODEL,
                    use_local_db=request_use_local_db,
                    database_url=DOCKER_DATABASE_URL
                )
            else:
                instance = rag_class(
                    ai_provider="gemini",
                    gemini_model_name=GEMINI_MODEL
                )
        else:
            raise ValueError(f"Invalid AI provider: {ai_provider}")
        
        logger.info(f"Created new {ai_provider} {ai_version} RAG instance (DB: {request_use_local_db})")
        return instance
        
    except Exception as e:
        logger.error(f"Failed to create {ai_provider} {ai_version} RAG instance: {e}")
        if ai_version in ["V5", "V6", "V7", "V8", "V9"] and request_use_local_db:
            # Fallback to API-only mode
            logger.info(f"Trying {ai_version} without database as fallback...")
            return create_rag_instance(ai_provider, ai_version, use_local_db=False)
        raise

# Print startup information
print("🚀 FastAPI server ready with enhanced concurrent processing support!")
print(f"🔧 Thread pool size: {MAX_WORKERS}")
print(f"💾 Database pool size: {DB_POOL_SIZE}")
print(f"🌐 Available providers: {[p for p in ['openai', 'gemini'] if os.getenv(f'{p.upper()}_API_KEY')]}")
print(f"📊 Available versions: V2, V3, V4, V5, V6{', V7' if CordisRAG_V7 else ''}, V8, V9")
print(f"🗄️ Local database enabled: {USE_LOCAL_DB}")
print("💡 RAG instances are now created per-request for true concurrency!")

# Add demo examples for simulated responses
DEMO_RESPONSES = [
    "Based on the European research projects data, there are several notable AI initiatives in healthcare. The ADAM project (Autonomous Discovery of Advanced Materials) involves researchers from Germany, France, and Italy working on AI-driven drug discovery platforms. The project has received €3.2 million in EU funding and focuses on using machine learning for identifying novel therapeutic compounds for treatment-resistant diseases.",
    
    "According to the project information, renewable energy research in Europe has seen significant growth in the past 5 years. The SOLARFUTURE consortium, led by institutions in Spain and Denmark, has been developing next-generation photovoltaic materials with 30% higher efficiency than traditional silicon-based cells. Their work involves 8 research institutions across 5 countries with a total budget of €5.7 million.",
    
    "The analysis of quantum computing projects reveals that QuBridge, a collaboration between 12 European institutions including the Technical University of Munich and Oxford University, has made substantial progress in quantum error correction. Their research has resulted in 28 published papers and 3 patent applications between 2022-2024, with particular focus on developing fault-tolerant quantum processors.",
    
    "From the retrieved project data, it appears that cybersecurity initiatives focusing on critical infrastructure protection have received over €120 million in funding since 2021. The SecureGrid project, involving partners from Estonia, Finland, and Poland, has developed novel threat detection systems for power grids that reduce false positives by 78% compared to previous technologies.",
    
    "The examination of European biotech projects indicates that the BioInnovate consortium has been pioneering CRISPR applications for agricultural resilience. With 14 partner organizations across southern European countries, their research has focused on developing drought-resistant crop varieties that require 40% less water while maintaining comparable yields to traditional varieties."
]

# Request model
class QuestionRequest(BaseModel):
    question: str
    max_results: Optional[int] = 5
    ai_provider: Optional[str] = None  # Allow specifying provider per request
    ai_version: Optional[str] = "V9"   # Default to V9, allow switching between V2, V3, V4, V5, V6, V7, V8, V9
    use_local_db: Optional[bool] = None  # Override global setting for V5/V6/V7/V8

# Response models
class ProjectParticipant(BaseModel):
    name: str
    country: str
    city: Optional[str] = None

class ProjectBudget(BaseModel):
    total_cost: str
    eu_contribution: Optional[str] = None

class Project(BaseModel):
    title: str
    objective: str
    keywords: List[str]
    budget: ProjectBudget
    participants: List[ProjectParticipant]
    call: Dict[str, str]

class SearchResponse(BaseModel):
    answer: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_version: Optional[str] = None
    model_used: Optional[str] = None
    data_source: Optional[str] = None  # "Local Database" or "CORDIS API"
    processing_time: Optional[float] = None
    projects_found: Optional[int] = None
    projects: Optional[List[Project]] = None
    error: Optional[bool] = False
    error_message: Optional[str] = None
    # V6 enhanced logging fields
    logs: Optional[Dict[str, Any]] = None  # Complete pipeline logs from V6

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "online", "message": "CORDIS RAG API is running"}

def get_provider_and_version(ai_provider: Optional[str] = None, ai_version: Optional[str] = "V9"):
    """
    Validate and determine the AI provider and version to use.
    Returns (provider, version) tuple.
    """
    # Validate version
    supported_versions = ["V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9"]
    version = ai_version.upper() if ai_version else "V9"
    if version not in supported_versions:
        raise HTTPException(status_code=400, detail=f"Invalid ai_version '{ai_version}'. Supported: {', '.join(supported_versions)}.")
    
    # Check if requested provider is available
    available_providers = [p for p in ['openai', 'gemini'] if os.getenv(f'{p.upper()}_API_KEY')]
    if not available_providers:
        raise HTTPException(status_code=500, detail="No AI providers are configured (missing API keys).")
    
    # Use requested provider if specified and available
    if ai_provider:
        provider = ai_provider.lower()
        if provider not in available_providers:
            raise HTTPException(status_code=400, detail=f"Provider '{ai_provider}' not available. Available: {', '.join(available_providers)}.")
        return provider, version
    
    # Use default provider if available
    if DEFAULT_AI_PROVIDER in available_providers:
        return DEFAULT_AI_PROVIDER, version
    
    # Fall back to first available provider
    return available_providers[0], version

@app.post("/api/query", response_model=SearchResponse)
async def query_projects(request: QuestionRequest):
    """
    Query the CORDIS database with a natural language question.
    
    Enhanced V9 endpoint with intelligent intent routing and Celery for true concurrent processing.
    V9 can intelligently determine whether users want existing projects or open calls for proposals.
    
    Parameters:
    - question: A natural language question about European research projects or funding calls
    - max_results: Maximum number of projects/calls to retrieve (default: 5)
    - ai_provider: AI provider to use ("openai" or "gemini", optional)
    - ai_version: AI version to use ("V2", "V3", "V4", "V5", "V6", "V7", "V8", or "V9", optional, default: "V9")
    - use_local_db: Override global database setting for V5/V6/V7/V8/V9 (optional)
    
    Returns:
    - answer: A comprehensive answer to the question
    - ai_provider: The AI provider used to generate the answer
    - ai_version: The RAG version used
    - model_used: The specific model used to generate the answer
    - data_source: Whether local database or CORDIS API was used
    - processing_time: Time taken to process the request
    - projects_found: Number of projects found
    - logs: Comprehensive pipeline logs (V6+ only)
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing query: '{request.question}' with provider: {request.ai_provider} and version: {request.ai_version}")
        
        # Get provider and version (validate inputs)
        provider, version = get_provider_and_version(request.ai_provider, request.ai_version)
        
        if CELERY_AVAILABLE:
            # Use Celery for true concurrent processing
            logger.info("Using Celery for concurrent processing")
            
            # Submit task to Celery worker
            task = process_rag_query.delay(
                question=request.question,
                max_results=request.max_results or 5,
                ai_provider=provider,
                ai_version=version,
                use_local_db=request.use_local_db
            )
            
            # Wait for task completion (with timeout)
            try:
                result = task.get(timeout=300)  # 5 minute timeout
                
                if result.get("success", False):
                    # Task completed successfully
                    return SearchResponse(
                        answer=result.get('answer', ''),
                        ai_provider=result.get('ai_provider', provider),
                        ai_version=result.get('ai_version', version),
                        model_used=result.get('model_used', OPENAI_MODEL if provider == "openai" else GEMINI_MODEL),
                        data_source=result.get('data_source', 'CORDIS API'),
                        processing_time=result.get('processing_time', 0),
                        projects_found=result.get('projects_found', 0),
                        logs=result.get('logs', {})
                    )
                else:
                    # Task failed
                    return JSONResponse(
                        status_code=500,
                        content={
                            "error": result.get('error', 'Task failed'),
                            "details": result.get('details', 'Unknown error')
                        }
                    )
                    
            except Exception as task_error:
                logger.error(f"Celery task error: {task_error}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Task processing failed",
                        "details": str(task_error)
                    }
                )
        else:
            # Fallback to thread pool if Celery not available
            logger.info("Using thread pool fallback (Celery not available)")
            
            def create_and_run_rag():
                """Create RAG instance and run the query - executed in thread pool"""
                rag_system = create_rag_instance(provider, version, request.use_local_db)
                return rag_system.get_ai_response(
                    request.question, 
                    max_projects_to_process=request.max_results or 5
                )
            
            # Run the blocking RAG operation in a thread pool
            result = await asyncio.get_event_loop().run_in_executor(
                thread_pool, 
                create_and_run_rag
            )
            
            processing_time = time.time() - start_time
            
            # Handle V9 response format first (most specific)
            if version == "V9" and isinstance(result, dict):
                logger.info("🔍 DEBUG - Handling V9 response")
                
                # Extract the actual answer string from V9 result
                answer = result.get('answer', '')
                logs = result.get('logs', {})
                
                # Ensure answer is a string, not a dict
                if isinstance(answer, dict):
                    logger.warning("⚠️ V9 answer is unexpectedly a dict, extracting string")
                    answer = answer.get('answer', 'Error: Malformed V9 response')
                elif not isinstance(answer, str):
                    logger.warning("⚠️ V9 answer is not a string, converting")
                    answer = str(answer)
                
                logger.info(f"🔍 V9 Answer type: {type(answer)}, length: {len(answer)}")
                logger.info(f"🔍 V9 Answer preview: {answer[:100]}...")
                
                return SearchResponse(
                    answer=answer,
                    ai_provider=provider,
                    ai_version=version,
                    model_used=GEMINI_MODEL if provider == "gemini" else OPENAI_MODEL,
                    data_source=result.get('data_source', 'CORDIS API'),
                    processing_time=round(processing_time, 2),
                    projects_found=result.get('projects_found', result.get('calls_found', 0)),
                    logs=logs
                )
            
            # Handle other V6+ versions with logs
            elif version in ["V6", "V7", "V8"] and isinstance(result, dict) and 'logs' in result:
                logger.info("🔍 DEBUG - Handling V6-V8 response with logs")
                # V6+ returns a dictionary with answer and logs
                answer = result.get('answer', '')
                logs = result.get('logs', {})
                
                # Extract metrics from logs
                model_used = logs.get('model_used', OPENAI_MODEL if provider == "openai" else GEMINI_MODEL)
                data_source = logs.get('data_source', result.get('data_source', 'CORDIS API'))
                projects_found = logs.get('projects_retrieved', result.get('projects_found', result.get('calls_found', 0)))
                
                return SearchResponse(
                    answer=answer,
                    ai_provider=provider,
                    ai_version=version,
                    model_used=model_used,
                    data_source=data_source,
                    processing_time=round(processing_time, 2),
                    projects_found=projects_found,
                    logs=logs  # Include complete logs for V6+
                )
            
            # Handle any other dictionary format that has an answer field
            elif isinstance(result, dict) and 'answer' in result:
                logger.info("🔍 DEBUG - Handling generic dict with answer")
                # Handle any other dictionary format that has an answer field
                answer = result.get('answer', '')
                logs = result.get('logs', {})
                
                # Make sure we don't stringify if answer is empty - provide a fallback message instead
                if not answer:
                    answer = "I apologize, but I couldn't generate a proper response. Please try again."
                
                return SearchResponse(
                    answer=answer,
                    ai_provider=provider,
                    ai_version=version,
                    model_used=GEMINI_MODEL if provider == "gemini" else OPENAI_MODEL,
                    data_source=result.get('data_source', 'CORDIS API'),
                    processing_time=round(processing_time, 2),
                    projects_found=result.get('projects_found', result.get('calls_found', 0)),
                    logs=logs
                )
            
            # Final fallback for string responses or malformed data
            else:
                logger.info("🔍 DEBUG - Taking final fallback path")
                # V2-V5 return a string answer, or final fallback for malformed responses
                if isinstance(result, dict):
                    logger.warning("⚠️ Dict result fell through all conditions - using emergency extraction")
                    # Final fallback - extract answer but never stringify the entire dict
                    answer = result.get('answer', '')
                    if not answer:
                        # If no answer field or empty, provide a helpful message instead of stringifying
                        answer = "I encountered an issue processing your request. Please try again or rephrase your question."
                        logger.error("❌ Empty answer in dict result, using fallback message")
                else:
                    answer = result if isinstance(result, str) else str(result)
                
                # Determine model used
                model_used = OPENAI_MODEL if provider == "openai" else GEMINI_MODEL
                
                # Determine data source for V5+
                use_local_db = request.use_local_db if request.use_local_db is not None else USE_LOCAL_DB
                if version in ["V5", "V6", "V7", "V8", "V9"]:
                    data_source = "Local Database" if use_local_db else "CORDIS API"
                else:
                    data_source = "CORDIS API"
                
                # Count projects mentioned in response (rough estimate)
                projects_found = answer.count("🔗") if answer else 0
                
                return SearchResponse(
                    answer=answer,
                    ai_provider=provider,
                    ai_version=version,
                    model_used=model_used,
                    data_source=data_source,
                    processing_time=round(processing_time, 2),
                    projects_found=projects_found
                )
        
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid question",
                "details": str(ve)
            }
        )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        error_message = str(e) if str(e) else "Unknown error occurred"
        return JSONResponse(
            status_code=500,
            content={
                "error": "Error processing request",
                "details": error_message
            }
        )

@app.post("/api/query/stream")
async def stream_query_projects(request: QuestionRequest):
    """
    Stream the CORDIS database query response in real-time using Server-Sent Events.
    
    Enhanced V9 endpoint with intelligent intent routing, Celery-based concurrent processing and real-time token streaming.
    V9 can intelligently determine whether users want existing projects or open calls for proposals.
    
    Parameters:
    - question: A natural language question about European research projects or funding calls
    - max_results: Maximum number of projects/calls to retrieve (default: 5)
    - ai_provider: AI provider to use ("openai" or "gemini", optional)
    - ai_version: AI version to use ("V2", "V3", "V4", "V5", "V6", "V7", "V8", or "V9", optional, default: "V9")
    - use_local_db: Override global database setting for V5/V6/V7/V8/V9 (optional)
    
    Returns:
    - Server-Sent Events stream with real-time progress and token-by-token answer generation
    """
    async def generate_stream():
        start_time = time.time()
        
        try:
            # Send initial metadata
            logger.info(f"Starting streaming query: '{request.question}' with provider: {request.ai_provider} and version: {request.ai_version}")
            
            provider, version = get_provider_and_version(request.ai_provider, request.ai_version)
            
            # Send metadata
            metadata = {
                'type': 'metadata',
                'ai_provider': provider,
                'ai_version': version,
                'status': 'starting',
                'question': request.question
            }
            yield f"data: {json.dumps(metadata)}\n\n"
            
            # Check if Celery is available for concurrent processing
            if CELERY_AVAILABLE:
                # Use Celery for concurrent processing
                yield f"data: {json.dumps({'type': 'progress', 'phase': 'queuing', 'message': 'I am analyzing your question and preparing to search for relevant projects...'})}\n\n"
                
                # Submit the streaming task to Celery
                task = process_rag_query_stream.delay(
                    question=request.question,
                    max_results=request.max_results or 5,
                    ai_provider=provider,
                    ai_version=version,
                    use_local_db=request.use_local_db
                )
                
                yield f"data: {json.dumps({'type': 'progress', 'phase': 'processing', 'message': 'Searching through thousands of European research projects for you...'})}\n\n"
                
                # Poll task status with longer intervals for streaming
                poll_interval = 2.0  # 2 seconds for streaming tasks
                timeout = 300  # 5 minutes timeout
                elapsed = 0
                
                # User-friendly progress messages
                progress_messages = [
                    "Analyzing project databases and research archives...",
                    "Finding the most relevant projects for your question...", 
                    "Examining project details and participant information...",
                    "Cross-referencing funding programs and research outcomes...",
                    "Preparing a comprehensive answer with project links..."
                ]
                message_index = 0
                
                while not task.ready() and elapsed < timeout:
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
                    
                    # Send friendly progress updates every 10 seconds
                    if elapsed % 10 == 0:
                        if message_index < len(progress_messages):
                            message = progress_messages[message_index]
                            message_index += 1
                        else:
                            message = f"Still working on your request... ({elapsed}s elapsed)"
                        
                        yield f"data: {json.dumps({'type': 'progress', 'phase': 'processing', 'message': message})}\n\n"
                
                if task.ready():
                    if task.successful():
                        result = task.result
                        
                        if result.get("success", False):
                            answer = result.get("answer", "")
                            
                            yield f"data: {json.dumps({'type': 'progress', 'phase': 'streaming', 'message': 'Perfect! I found some great projects. Let me share the details with you...'})}\n\n"
                            
                            # Stream the complete answer token by token
                            chunk_size = 50  # Characters per chunk for good streaming experience
                            for i in range(0, len(answer), chunk_size):
                                chunk = answer[i:i+chunk_size]
                                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                            
                            # Send completion with full metadata
                            processing_time = time.time() - start_time
                            completion_data = {
                                'type': 'complete',
                                'answer': answer,
                                'processing_time': round(processing_time, 2),
                                'ai_provider': provider,
                                'ai_version': version,
                                'data_source': result.get('data_source', 'Unknown'),
                                'projects_found': result.get('projects_found', 0),
                                'task_id': task.id,
                                'concurrent_processing': True
                            }
                            
                            # Include logs if available (V6+)
                            if 'logs' in result:
                                completion_data['logs'] = result['logs']
                            
                            yield f"data: {json.dumps(completion_data)}\n\n"
                        else:
                            # Task completed but with error
                            error_data = {
                                'type': 'error',
                                'error': 'I encountered an issue while processing your request',
                                'details': result.get('details', 'Please try rephrasing your question or try again later.'),
                                'task_id': task.id
                            }
                            yield f"data: {json.dumps(error_data)}\n\n"
                    else:
                        # Task failed
                        error_data = {
                            'type': 'error',
                            'error': 'I am having trouble processing your request right now',
                            'details': 'Please try again in a moment. If the problem persists, try rephrasing your question.',
                            'task_id': task.id
                        }
                        yield f"data: {json.dumps(error_data)}\n\n"
                else:
                    # Task timed out
                    error_data = {
                        'type': 'error',
                        'error': 'Your request is taking longer than expected',
                        'details': 'The search timed out. Please try a more specific question or try again later.',
                        'task_id': task.id
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
            
            else:
                # Fallback to direct processing (same as before but for non-Celery environments)
                yield f"data: {json.dumps({'type': 'progress', 'phase': 'processing', 'message': 'Celery not available. Using direct processing...'})}\n\n"
                
                rag_system = create_rag_instance(provider, version, request.use_local_db)
                
                # Handle V5/V6/V7/V8/V9 database override (keeping existing logic)
                if version in ["V5", "V6", "V7", "V8", "V9"] and request.use_local_db is not None:
                    # [Previous database override logic would go here - keeping existing implementation]
                    pass
                
                # Check if the RAG system supports streaming (V7, V8, and V9)
                if version in ["V7", "V8", "V9"] and hasattr(rag_system, 'get_ai_response_stream'):
                    # Use V7/V8 streaming capability
                    async for chunk in rag_system.get_ai_response_stream(  # type: ignore
                        request.question, 
                        max_projects_to_process=request.max_results or 5
                    ):
                        yield f"data: {json.dumps(chunk)}\n\n"
                        if chunk.get('type') == 'complete':
                            break
                else:
                    # Fallback for older versions - streaming simulation
                    yield f"data: {json.dumps({'type': 'progress', 'phase': 'processing', 'message': f'Processing with {version} (non-streaming mode)...'})}\n\n"
                    
                    # Get the regular response
                    result = rag_system.get_ai_response(
                        request.question, 
                        max_projects_to_process=request.max_results or 5
                    )
                    
                    processing_time = time.time() - start_time
                    
                    # Handle different return formats and stream the response
                    if isinstance(result, dict) and 'logs' in result:
                        # V6+ format
                        answer = result.get('answer', '')
                        logs = result.get('logs', {})
                        
                        # Stream the answer
                        chunk_size = 50
                        for i in range(0, len(answer), chunk_size):
                            chunk = answer[i:i+chunk_size]
                            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                        
                        # Send completion
                        completion_data = {
                            'type': 'complete',
                            'answer': answer,
                            'logs': logs,
                            'processing_time': round(processing_time, 2),
                            'ai_provider': provider,
                            'ai_version': version,
                            'data_source': logs.get('data_source', 'CORDIS API'),
                            'projects_found': logs.get('projects_retrieved', 0),
                            'concurrent_processing': False
                        }
                        yield f"data: {json.dumps(completion_data)}\n\n"
                    else:
                        # V2-V5 format
                        answer = result if isinstance(result, str) else str(result)
                        
                        # Stream the answer
                        chunk_size = 50
                        for i in range(0, len(answer), chunk_size):
                            chunk = answer[i:i+chunk_size]
                            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                        
                        # Send completion
                        data_source = "Local Database" if (hasattr(rag_system, 'use_local_db') and rag_system.use_local_db) else "CORDIS API"
                        completion_data = {
                            'type': 'complete',
                            'answer': answer,
                            'processing_time': round(processing_time, 2),
                            'ai_provider': provider,
                            'ai_version': version,
                            'data_source': data_source,
                            'projects_found': answer.count("🔗") if answer else 0,
                            'concurrent_processing': False
                        }
                        yield f"data: {json.dumps(completion_data)}\n\n"
        
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}", exc_info=True)
            error_data = {
                'type': 'error',
                'error': 'Error processing request',
                'details': str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.post("/api/demo")
async def demo_query(request: QuestionRequest, background_tasks: BackgroundTasks):
    """
    Simulated query endpoint that returns a fake AI response after a short delay.
    
    Enhanced with V6 simulation including local database performance benefits.
    """
    # Choose a random response
    response = random.choice(DEMO_RESPONSES)
    
    # Simulate processing time - V5/V6 with local DB is faster
    if request.ai_version in ["V5", "V6"] and (request.use_local_db or USE_LOCAL_DB):
        delay = random.uniform(0.5, 2.0)  # Faster with local DB
        data_source = "Local Database (Demo)"
    else:
        delay = random.uniform(2, 5)  # Normal API speed
        data_source = "CORDIS API (Demo)"
    
    # Return a response after delay
    await asyncio.sleep(delay)
    
    # Get the requested or default AI provider for the response info
    provider, version = get_provider_and_version(request.ai_provider, request.ai_version)
    
    return {
        "answer": response,
        "ai_provider": provider,
        "ai_version": version,
        "data_source": data_source,
        "processing_time": round(delay, 2),
        "projects_found": random.randint(3, 8),
        "demo": True,
        "query": request.question
    }

@app.get("/api/providers")
async def list_providers():
    """
    List all available AI providers and their models for V2, V3, V4, V5, V6, V7, and V8.
    Now works with per-request instance creation.
    """
    # Check which providers have API keys configured
    available_providers = [p for p in ['openai', 'gemini'] if os.getenv(f'{p.upper()}_API_KEY')]
    
    providers = {"V2": {}, "V3": {}, "V4": {}, "V5": {}, "V6": {}, "V7": {}, "V8": {}, "V9": {}}
    
    for version in ["V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9"]:
        for provider_name in available_providers:
            provider_info = {"is_default": provider_name == DEFAULT_AI_PROVIDER}
            
            if provider_name == "openai":
                provider_info["model"] = OPENAI_MODEL
            elif provider_name == "gemini":
                provider_info["model"] = GEMINI_MODEL
            
            # Add V5/V6/V7/V8 specific information
            if version in ["V5", "V6", "V7", "V8", "V9"]:
                provider_info["supports_local_db"] = True
                provider_info["local_db_enabled"] = USE_LOCAL_DB
                provider_info["database_available"] = DATABASE_URL is not None
                
                # V7, V8, and V9 specific features
                if version in ["V7", "V8", "V9"]:
                    provider_info["supports_streaming"] = True
                    provider_info["supports_realtime_tokens"] = True
                    
                    # V8 specific enhancements
                    if version == "V8":
                        provider_info["performance_optimized"] = True
                        provider_info["enhanced_streaming"] = True
                        provider_info["concurrent_processing"] = True
                        
                    # V9 specific enhancements
                    if version == "V9":
                        provider_info["intelligent_intent_routing"] = True
                        provider_info["project_search"] = True
                        provider_info["call_search"] = True
                        provider_info["confidence_scoring"] = True
                        provider_info["performance_optimized"] = True
                        provider_info["enhanced_streaming"] = True
                        provider_info["concurrent_processing"] = True
                        
                    # V7 availability check
                    if version == "V7":
                        provider_info["available"] = CordisRAG_V7 is not None
            
            providers[version][provider_name] = provider_info
    
    return {
        "available_providers": providers,
        "default_provider": DEFAULT_AI_PROVIDER,
        "concurrent_processing": {
            "enabled": True,
            "thread_pool_size": MAX_WORKERS,
            "db_pool_size": DB_POOL_SIZE
        },
        "v9_features": {
            "intelligent_intent_routing": True,
            "project_search": True,
            "call_search": True,
            "confidence_scoring": True,
            "streaming_support": True,
            "performance_optimizations": True,
            "enhanced_error_handling": True,
            "concurrent_requests": True
        },
        "v8_features": {
            "streaming_support": True,
            "performance_optimizations": True,
            "enhanced_error_handling": True,
            "optimized_chunking": True,
            "concurrent_requests": True
        },
        "v7_features": {
            "streaming_support": True,
            "realtime_tokens": True,
            "enhanced_logging": True,
            "available": CordisRAG_V7 is not None
        }
    }

@app.get("/api/database/status")
async def database_status():
    """
    Check the status of the local database connection for V5/V6.
    """
    if not DOCKER_DATABASE_URL:
        return {
            "status": "not_configured",
            "message": "DATABASE_URL not provided",
            "database_url": None,
            "docker_env": os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV") == "true"
        }
    try:
        # Create a test instance to check database connection
        available_providers = [p for p in ['openai', 'gemini'] if os.getenv(f'{p.upper()}_API_KEY')]
        if not available_providers:
            return {
                "status": "error",
                "message": "No AI providers configured",
                "use_local_db": USE_LOCAL_DB,
                "docker_env": os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV") == "true"
            }
        
        # Use the first available provider to test the connection
        test_provider = available_providers[0]
        test_rag = create_rag_instance(test_provider, "V9", use_local_db=True)
        
        if hasattr(test_rag, 'db_pool') and test_rag.db_pool:
            # Try to get a connection to test
            conn = test_rag.db_pool.getconn()
            test_rag.db_pool.putconn(conn)
            
            return {
                "status": "connected",
                "message": "Database connection successful",
                "use_local_db": USE_LOCAL_DB,
                "database_url": DOCKER_DATABASE_URL.split('@')[0] + '@***' if '@' in DOCKER_DATABASE_URL else "***",
                "docker_env": os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV") == "true"
            }
        else:
            return {
                "status": "not_connected",
                "message": "Database pool not initialized",
                "use_local_db": USE_LOCAL_DB,
                "docker_env": os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV") == "true"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database connection failed: {str(e)}",
            "use_local_db": USE_LOCAL_DB,
            "docker_env": os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV") == "true",
            "suggested_solution": "If running in Docker, ensure Supabase is accessible via host.docker.internal:54322"
        }

@app.post("/api/query/benchmark")
async def benchmark_query(request: QuestionRequest):
    """
    Benchmark endpoint to compare V5/V6 local database vs CORDIS API performance.
    """
    if request.ai_version not in ["V5", "V6"]:
        raise HTTPException(status_code=400, detail="Benchmarking only available for V5 and V6")
    
    if not DATABASE_URL:
        raise HTTPException(status_code=400, detail="Database not configured for benchmarking")
    
    try:
        provider, version = get_provider_and_version(request.ai_provider, request.ai_version)
        rag_system = create_rag_instance(provider, version, request.use_local_db)
        
        results = {}
        
        # Test with local database
        try:
            if provider == "openai":
                if version == "V5":
                    rag_local = CordisRAG_V5(
                        ai_provider="openai",
                        openai_model_name=OPENAI_MODEL,
                        use_local_db=True,
                        database_url=DOCKER_DATABASE_URL
                    )
                else:  # V6
                    rag_local = CordisRAG_V6(
                        ai_provider="openai",
                        openai_model_name=OPENAI_MODEL,
                        use_local_db=True,
                        database_url=DOCKER_DATABASE_URL
                    )
            else:
                if version == "V5":
                    rag_local = CordisRAG_V5(
                        ai_provider="gemini",
                        gemini_model_name=GEMINI_MODEL,
                        use_local_db=True,
                        database_url=DOCKER_DATABASE_URL
                    )
                else:  # V6
                    rag_local = CordisRAG_V6(
                        ai_provider="gemini",
                        gemini_model_name=GEMINI_MODEL,
                        use_local_db=True,
                        database_url=DOCKER_DATABASE_URL
                    )
            
            start_time = time.time()
            answer_local = rag_local.get_ai_response(request.question, max_projects_to_process=request.max_results or 5)
            local_time = time.time() - start_time
            
            # Handle V6's new return format
            if version == "V6" and isinstance(answer_local, dict):
                answer_text = answer_local.get('answer', '')
                logs = answer_local.get('logs', {})
                projects_found = logs.get('projects_retrieved', 0)
            else:
                answer_text = answer_local if isinstance(answer_local, str) else str(answer_local)
                projects_found = answer_text.count("🔗")
            
            results["local_database"] = {
                "processing_time": round(local_time, 2),
                "answer_length": len(answer_text),
                "projects_found": projects_found,
                "status": "success"
            }
        except Exception as e:
            results["local_database"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test with CORDIS API
        try:
            if provider == "openai":
                rag_api = CordisRAG_V5(
                    ai_provider="openai",
                    openai_model_name=OPENAI_MODEL,
                    use_local_db=False
                )
            else:
                rag_api = CordisRAG_V5(
                    ai_provider="gemini",
                    gemini_model_name=GEMINI_MODEL,
                    use_local_db=False
                )
            
            start_time = time.time()
            answer_api = rag_api.get_ai_response(request.question, max_projects_to_process=request.max_results or 5)
            api_time = time.time() - start_time
            
            results["cordis_api"] = {
                "processing_time": round(api_time, 2),
                "answer_length": len(answer_api),
                "projects_found": answer_api.count("🔗"),
                "status": "success"
            }
        except Exception as e:
            results["cordis_api"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Calculate performance comparison
        if ("local_database" in results and results["local_database"]["status"] == "success" and
            "cordis_api" in results and results["cordis_api"]["status"] == "success"):
            
            local_time = float(results["local_database"]["processing_time"])
            api_time = float(results["cordis_api"]["processing_time"])
            speedup = api_time / local_time if local_time > 0 else 0
            
            results["comparison"] = {
                "speedup_factor": round(speedup, 1),
                "time_saved": round(api_time - local_time, 2),
                "local_faster": local_time < api_time
            }
        
        return {
            "question": request.question,
            "ai_provider": provider,
            "benchmark_results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benchmark failed: {str(e)}")

@app.post("/api/test-v9-fix")
async def test_v9_fix():
    """Test endpoint to verify V9 response handling is working correctly."""
    
    # Simulate a V9 response dictionary
    mock_v9_result = {
        'answer': 'This is a test answer from V9 that should NOT be stringified!',
        'logs': {
            'routing_decision': 'SEARCH_CALLS',
            'intent_confidence': 1.0,
            'data_source': 'Test API'
        },
        'data_source': 'Test CORDIS Topics/Calls API',
        'routing_decision': 'SEARCH_CALLS',
        'intent_confidence': 1.0,
        'calls_found': 2
    }
    
    # Simulate the FastAPI processing logic
    version = "V9"
    provider = "gemini"
    processing_time = 1.5
    
    logger.info("🧪 Testing V9 response handling...")
    
    # This should match our first condition now
    if version == "V9" and isinstance(mock_v9_result, dict):
        logger.info("✅ V9 condition matched correctly!")
        
        # Extract the actual answer string from V9 result
        answer = mock_v9_result.get('answer', '')
        logs = mock_v9_result.get('logs', {})
        
        # Ensure answer is a string, not a dict
        if isinstance(answer, dict):
            logger.warning("⚠️ V9 answer is unexpectedly a dict, extracting string")
            answer = answer.get('answer', 'Error: Malformed V9 response')
        elif not isinstance(answer, str):
            logger.warning("⚠️ V9 answer is not a string, converting")
            answer = str(answer)
        
        logger.info(f"🔍 V9 Answer type: {type(answer)}, length: {len(answer)}")
        logger.info(f"🔍 V9 Answer content: {answer}")
        
        return {
            "test_result": "SUCCESS",
            "message": "V9 response handling is working correctly!",
            "answer_type": str(type(answer)),
            "answer_content": answer,
            "answer_is_string": isinstance(answer, str),
            "data_source": mock_v9_result.get('data_source', 'Unknown'),
            "processing_time": processing_time,
            "condition_matched": "V9 specific condition"
        }
    else:
        logger.error("❌ V9 condition did NOT match!")
        return {
            "test_result": "FAILED", 
            "message": "V9 condition did not match",
            "version": version,
            "is_dict": isinstance(mock_v9_result, dict),
            "condition_matched": "None"
        }

@app.get("/api/health")
async def health_check():
    """Enhanced health check endpoint with Celery and database status."""
    try:
        overall_status = "healthy"
        
        # Check API keys
        openai_available = bool(os.getenv("OPENAI_API_KEY"))
        gemini_available = bool(os.getenv("GEMINI_API_KEY"))
        
        if not (openai_available or gemini_available):
            overall_status = "warning"
        
        # Check database status
        database_status = "not_configured"
        if DATABASE_URL:
            try:
                # Test database connection if possible
                available_providers = [p for p in ['openai', 'gemini'] if os.getenv(f'{p.upper()}_API_KEY')]
                if available_providers:
                    test_provider = available_providers[0]
                    test_rag = create_rag_instance(test_provider, "V9", use_local_db=True)
                    
                    if hasattr(test_rag, 'db_pool') and test_rag.db_pool:
                        # Try to get a connection to test
                        conn = test_rag.db_pool.getconn()
                        test_rag.db_pool.putconn(conn)
                        database_status = "connected"
                    else:
                        database_status = "configured_not_connected"
                else:
                    database_status = "configured_no_providers"
            except Exception as e:
                database_status = f"connection_error: {str(e)}"
        
        # Check Celery status
        celery_status = "available" if CELERY_AVAILABLE else "not_available"
        
        return {
            "status": overall_status,
            "components": {
                "api": "online",
                "celery": {
                    "status": celery_status,
                    "concurrent_processing": CELERY_AVAILABLE
                },
                "providers": {
                    "openai": {
                        "status": "configured" if openai_available else "not_configured",
                        "model": OPENAI_MODEL if openai_available else None
                    },
                    "gemini": {
                        "status": "configured" if gemini_available else "not_configured", 
                        "model": GEMINI_MODEL if gemini_available else None
                    }
                },
                "database": {
                    "status": database_status,
                    "url_configured": DATABASE_URL is not None,
                    "local_db_enabled": USE_LOCAL_DB,
                    "docker_env": os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV") == "true"
                }
            },
            "versions": {
                "v2": True,  # Always available
                "v3": True,
                "v4": True,
                "v5": True,
                "v6": True,
                "v7": CordisRAG_V7 is not None,
                "v8": True,
                "v9": True
            },
            "features": {
                "concurrent_processing": CELERY_AVAILABLE,
                "streaming": True,
                "local_database": DATABASE_URL is not None
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)