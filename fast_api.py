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
# Dynamically import all RAG classes including V8 (which is the latest version)
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
    description="API for querying European research projects using a Retrieval-Augmented Generation approach. V5 supports local database integration for faster performance.",
    version="1.1.0"
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

# Initialize the RAG systems for all versions including V8
rag_systems = {"V2": {}, "V3": {}, "V4": {}, "V5": {}, "V6": {}, "V7": {}, "V8": {}}

# Try to initialize OpenAI-based RAG for all versions
try:
    if os.getenv("OPENAI_API_KEY"):
        rag_systems["V2"]["openai"] = CordisRAG_V2(
            ai_provider="openai", 
            openai_model_name=OPENAI_MODEL
        )
        rag_systems["V3"]["openai"] = CordisRAG_V3(
            ai_provider="openai", 
            openai_model_name=OPENAI_MODEL
        )
        rag_systems["V4"]["openai"] = CordisRAG_V4(
            ai_provider="openai", 
            openai_model_name=OPENAI_MODEL
        )        # V5 with local database support - handle Docker networking
        try:
            rag_systems["V5"]["openai"] = CordisRAG_V5(
                ai_provider="openai", 
                openai_model_name=OPENAI_MODEL,
                use_local_db=USE_LOCAL_DB,
                database_url=DOCKER_DATABASE_URL
            )
            print(f"OpenAI RAG systems initialized for V2, V3, V4, and V5 with model: {OPENAI_MODEL}")
            if USE_LOCAL_DB:
                print(f"V5 configured to use local database: {DOCKER_DATABASE_URL is not None}")
        except Exception as db_e:
            print(f"V5 OpenAI database connection failed: {db_e}")
            # Initialize V5 without database as fallback
            rag_systems["V5"]["openai"] = CordisRAG_V5(
                ai_provider="openai", 
                openai_model_name=OPENAI_MODEL,
                use_local_db=False
            )
            print("V5 OpenAI initialized in API-only mode (no database)")
        
        # V6 with enhanced logging and local database support
        try:
            rag_systems["V6"]["openai"] = CordisRAG_V6(
                ai_provider="openai", 
                openai_model_name=OPENAI_MODEL,
                use_local_db=USE_LOCAL_DB,
                database_url=DOCKER_DATABASE_URL
            )
            print(f"OpenAI V6 RAG system initialized with enhanced logging")
            if USE_LOCAL_DB:
                print(f"V6 configured to use local database: {DOCKER_DATABASE_URL is not None}")
        except Exception as db_e:
            print(f"V6 OpenAI database connection failed: {db_e}")
            # Initialize V6 without database as fallback
            rag_systems["V6"]["openai"] = CordisRAG_V6(
                ai_provider="openai", 
                openai_model_name=OPENAI_MODEL,
                use_local_db=False
            )
            print("V6 OpenAI initialized in API-only mode (no database)")
        
        # V7 with streaming support and enhanced logging
        if CordisRAG_V7 is not None:
            try:
                rag_systems["V7"]["openai"] = CordisRAG_V7(
                    ai_provider="openai", 
                    openai_model_name=OPENAI_MODEL,
                    use_local_db=USE_LOCAL_DB,
                    database_url=DOCKER_DATABASE_URL
                )
                print(f"OpenAI V7 RAG system initialized with streaming support")
                if USE_LOCAL_DB:
                    print(f"V7 configured to use local database: {DOCKER_DATABASE_URL is not None}")
            except Exception as db_e:
                print(f"V7 OpenAI database connection failed: {db_e}")
                # Initialize V7 without database as fallback
                rag_systems["V7"]["openai"] = CordisRAG_V7(
                    ai_provider="openai", 
                    openai_model_name=OPENAI_MODEL,
                    use_local_db=False
                )
                print("V7 OpenAI initialized in API-only mode (no database)")
        else:
            print("V7 module not available, skipping V7 OpenAI initialization")
        
        # V8 with enhanced streaming and performance optimizations
        try:
            rag_systems["V8"]["openai"] = CordisRAG_V8(
                ai_provider="openai", 
                openai_model_name=OPENAI_MODEL,
                use_local_db=USE_LOCAL_DB,
                database_url=DOCKER_DATABASE_URL
            )
            print(f"OpenAI V8 RAG system initialized with enhanced streaming and performance")
            if USE_LOCAL_DB:
                print(f"V8 configured to use local database: {DOCKER_DATABASE_URL is not None}")
        except Exception as db_e:
            print(f"V8 OpenAI database connection failed: {db_e}")
            # Initialize V8 without database as fallback
            rag_systems["V8"]["openai"] = CordisRAG_V8(
                ai_provider="openai", 
                openai_model_name=OPENAI_MODEL,
                use_local_db=False
            )
            print("V8 OpenAI initialized in API-only mode (no database)")
except Exception as e:
    print(f"Failed to initialize OpenAI RAG system: {e}")

# Try to initialize Gemini-based RAG for all versions
try:
    if os.getenv("GEMINI_API_KEY"):
        rag_systems["V2"]["gemini"] = CordisRAG_V2(
            ai_provider="gemini", 
            gemini_model_name=GEMINI_MODEL
        )
        rag_systems["V3"]["gemini"] = CordisRAG_V3(
            ai_provider="gemini", 
            gemini_model_name=GEMINI_MODEL
        )
        rag_systems["V4"]["gemini"] = CordisRAG_V4(
            ai_provider="gemini", 
            gemini_model_name=GEMINI_MODEL
        )        # V5 with local database support - handle Docker networking
        try:
            rag_systems["V5"]["gemini"] = CordisRAG_V5(
                ai_provider="gemini", 
                gemini_model_name=GEMINI_MODEL,
                use_local_db=USE_LOCAL_DB,
                database_url=DOCKER_DATABASE_URL
            )
            print(f"Gemini RAG systems initialized for V2, V3, V4, and V5 with model: {GEMINI_MODEL}")
            if USE_LOCAL_DB:
                print(f"V5 configured to use local database: {DOCKER_DATABASE_URL is not None}")
        except Exception as db_e:
            print(f"V5 Gemini database connection failed: {db_e}")
            # Initialize V5 without database as fallback
            rag_systems["V5"]["gemini"] = CordisRAG_V5(
                ai_provider="gemini", 
                gemini_model_name=GEMINI_MODEL,
                use_local_db=False
            )
            print("V5 Gemini initialized in API-only mode (no database)")
        
        # V6 with enhanced logging and local database support
        try:
            rag_systems["V6"]["gemini"] = CordisRAG_V6(
                ai_provider="gemini", 
                gemini_model_name=GEMINI_MODEL,
                use_local_db=USE_LOCAL_DB,
                database_url=DOCKER_DATABASE_URL
            )
            print(f"Gemini V6 RAG system initialized with enhanced logging")
            if USE_LOCAL_DB:
                print(f"V6 configured to use local database: {DOCKER_DATABASE_URL is not None}")
        except Exception as db_e:
            print(f"V6 Gemini database connection failed: {db_e}")
            # Initialize V6 without database as fallback
            rag_systems["V6"]["gemini"] = CordisRAG_V6(
                ai_provider="gemini", 
                gemini_model_name=GEMINI_MODEL,
                use_local_db=False
            )
            print("V6 Gemini initialized in API-only mode (no database)")
        
        # V7 with streaming support and enhanced logging
        if CordisRAG_V7 is not None:
            try:
                rag_systems["V7"]["gemini"] = CordisRAG_V7(
                    ai_provider="gemini", 
                    gemini_model_name=GEMINI_MODEL,
                    use_local_db=USE_LOCAL_DB,
                    database_url=DOCKER_DATABASE_URL
                )
                print(f"Gemini V7 RAG system initialized with streaming support")
                if USE_LOCAL_DB:
                    print(f"V7 configured to use local database: {DOCKER_DATABASE_URL is not None}")
            except Exception as db_e:
                print(f"V7 Gemini database connection failed: {db_e}")
                # Initialize V7 without database as fallback
                rag_systems["V7"]["gemini"] = CordisRAG_V7(
                    ai_provider="gemini", 
                    gemini_model_name=GEMINI_MODEL,
                    use_local_db=False
                )
                print("V7 Gemini initialized in API-only mode (no database)")
        else:
            print("V7 module not available, skipping V7 Gemini initialization")
        
        # V8 with enhanced streaming and performance optimizations
        try:
            rag_systems["V8"]["gemini"] = CordisRAG_V8(
                ai_provider="gemini", 
                gemini_model_name=GEMINI_MODEL,
                use_local_db=USE_LOCAL_DB,
                database_url=DOCKER_DATABASE_URL
            )
            print(f"Gemini V8 RAG system initialized with enhanced streaming and performance")
            if USE_LOCAL_DB:
                print(f"V8 configured to use local database: {DOCKER_DATABASE_URL is not None}")
        except Exception as db_e:
            print(f"V8 Gemini database connection failed: {db_e}")
            # Initialize V8 without database as fallback
            rag_systems["V8"]["gemini"] = CordisRAG_V8(
                ai_provider="gemini", 
                gemini_model_name=GEMINI_MODEL,
                use_local_db=False
            )
            print("V8 Gemini initialized in API-only mode (no database)")
except Exception as e:
    print(f"Failed to initialize Gemini RAG system: {e}")

# Fallback to default if no systems initialized
if not any(rag_systems.values()):
    print("WARNING: No RAG systems initialized. Using default OpenAI configuration for V6.")
    rag_systems["V6"]["openai"] = CordisRAG_V6(use_local_db=False)  # Default to API mode

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
    ai_version: Optional[str] = "V8"   # Default to V8, allow switching between V2, V3, V4, V5, V6, V7, V8
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

def get_rag_system(ai_provider: Optional[str] = None, ai_version: Optional[str] = "V8"):
    version = ai_version.upper() if ai_version else "V8"
    if version not in rag_systems:
        raise HTTPException(status_code=400, detail=f"Invalid ai_version '{ai_version}'. Supported: V2, V3, V4, V5, V6, V7, V8.")
    # Use requested provider if specified and available
    if ai_provider and ai_provider.lower() in rag_systems[version]:
        return rag_systems[version][ai_provider.lower()], ai_provider.lower(), version
    # Otherwise use default provider if available
    if DEFAULT_AI_PROVIDER in rag_systems[version]:
        return rag_systems[version][DEFAULT_AI_PROVIDER], DEFAULT_AI_PROVIDER, version
    # Fall back to first available provider
    if rag_systems[version]:
        provider = next(iter(rag_systems[version].keys()))
        return rag_systems[version][provider], provider, version
    raise HTTPException(
        status_code=500, 
        detail=f"No AI providers are configured and available for version {version}."
    )

@app.post("/api/query", response_model=SearchResponse)
async def query_projects(request: QuestionRequest):
    """
    Query the CORDIS database with a natural language question.
    
    Enhanced V8 endpoint with local database support and performance optimizations.
    
    Parameters:
    - question: A natural language question about European research projects
    - max_results: Maximum number of projects to retrieve (default: 5)
    - ai_provider: AI provider to use ("openai" or "gemini", optional)
    - ai_version: AI version to use ("V2", "V3", "V4", "V5", "V6", "V7", or "V8", optional, default: "V8")
    - use_local_db: Override global database setting for V5/V6/V7/V8 (optional)
    
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
        
        rag_system, provider, version = get_rag_system(request.ai_provider, request.ai_version)
        
        # Handle V5/V6/V7/V8 database override
        if version in ["V5", "V6", "V7", "V8"] and request.use_local_db is not None:
            if provider == "openai":
                if version == "V5":
                    rag_system = CordisRAG_V5(
                        ai_provider="openai",
                        openai_model_name=OPENAI_MODEL,
                        use_local_db=request.use_local_db,
                        database_url=DOCKER_DATABASE_URL
                    )
                elif version == "V6":
                    rag_system = CordisRAG_V6(
                        ai_provider="openai",
                        openai_model_name=OPENAI_MODEL,
                        use_local_db=request.use_local_db,
                        database_url=DOCKER_DATABASE_URL
                    )
                elif version == "V7":
                    if CordisRAG_V7 is not None:
                        rag_system = CordisRAG_V7(
                            ai_provider="openai",
                            openai_model_name=OPENAI_MODEL,
                            use_local_db=request.use_local_db,
                            database_url=DOCKER_DATABASE_URL
                        )
                    else:
                        # Fallback to V6 if V7 is not available
                        rag_system = CordisRAG_V6(
                            ai_provider="openai",
                            openai_model_name=OPENAI_MODEL,
                            use_local_db=request.use_local_db,
                            database_url=DOCKER_DATABASE_URL
                        )
                else:  # V8
                    rag_system = CordisRAG_V8(
                        ai_provider="openai",
                        openai_model_name=OPENAI_MODEL,
                        use_local_db=request.use_local_db,
                        database_url=DOCKER_DATABASE_URL
                    )
            elif provider == "gemini":
                if version == "V5":
                    rag_system = CordisRAG_V5(
                        ai_provider="gemini",
                        gemini_model_name=GEMINI_MODEL,
                        use_local_db=request.use_local_db,
                        database_url=DOCKER_DATABASE_URL
                    )
                elif version == "V6":
                    rag_system = CordisRAG_V6(
                        ai_provider="gemini",
                        gemini_model_name=GEMINI_MODEL,
                        use_local_db=request.use_local_db,
                        database_url=DOCKER_DATABASE_URL
                    )
                elif version == "V7":
                    if CordisRAG_V7 is not None:
                        rag_system = CordisRAG_V7(
                            ai_provider="gemini",
                            gemini_model_name=GEMINI_MODEL,
                            use_local_db=request.use_local_db,
                            database_url=DOCKER_DATABASE_URL
                        )
                    else:
                        # Fallback to V6 if V7 is not available
                        rag_system = CordisRAG_V6(
                            ai_provider="gemini",
                            gemini_model_name=GEMINI_MODEL,
                            use_local_db=request.use_local_db,
                            database_url=DOCKER_DATABASE_URL
                        )
                else:  # V8
                    rag_system = CordisRAG_V8(
                        ai_provider="gemini",
                        gemini_model_name=GEMINI_MODEL,
                        use_local_db=request.use_local_db,
                        database_url=DOCKER_DATABASE_URL
                    )
        
        # Get the response
        result = rag_system.get_ai_response(
            request.question, 
            max_projects_to_process=request.max_results or 5
        )
        
        processing_time = time.time() - start_time
        
        # Handle V6's new return format vs older versions
        if version == "V6" and isinstance(result, dict) and 'logs' in result:
            # V6 returns a dictionary with answer and logs
            answer = result.get('answer', '')
            logs = result.get('logs', {})
            
            # Extract metrics from logs
            model_used = logs.get('model_used', getattr(rag_system, "openai_model_name" if provider == "openai" else "gemini_model_name", "Unknown"))
            data_source = logs.get('data_source', 'CORDIS API')
            projects_found = logs.get('projects_retrieved', 0)
            
            return SearchResponse(
                answer=answer,
                ai_provider=provider,
                ai_version=version,
                model_used=model_used,
                data_source=data_source,
                processing_time=round(processing_time, 2),
                projects_found=projects_found,
                logs=logs  # Include complete logs for V6
            )
        else:
            # V2-V5 return a string answer
            answer = result if isinstance(result, str) else str(result)
            
            # Determine model used
            model_used = None
            if provider == "openai":
                model_used = getattr(rag_system, "openai_model_name", OPENAI_MODEL)
            elif provider == "gemini":
                model_used = getattr(rag_system, "gemini_model_name", GEMINI_MODEL)
            
            # Determine data source for V5/V6
            data_source = None
            if version in ["V5", "V6"]:
                if hasattr(rag_system, 'use_local_db'):
                    data_source = "Local Database" if rag_system.use_local_db else "CORDIS API"
                else:
                    data_source = "CORDIS API"  # fallback
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
    
    Enhanced V8 endpoint with real-time token streaming and performance optimizations.
    
    Parameters:
    - question: A natural language question about European research projects
    - max_results: Maximum number of projects to retrieve (default: 5)
    - ai_provider: AI provider to use ("openai" or "gemini", optional)
    - ai_version: AI version to use ("V2", "V3", "V4", "V5", "V6", "V7", or "V8", optional, default: "V8")
    - use_local_db: Override global database setting for V5/V6/V7/V8 (optional)
    
    Returns:
    - Server-Sent Events stream with real-time progress and token-by-token answer generation
    """
    async def generate_stream():
        start_time = time.time()
        
        try:
            # Send initial metadata
            logger.info(f"Starting streaming query: '{request.question}' with provider: {request.ai_provider} and version: {request.ai_version}")
            
            rag_system, provider, version = get_rag_system(request.ai_provider, request.ai_version)
            
            # Send metadata
            metadata = {
                'type': 'metadata',
                'ai_provider': provider,
                'ai_version': version,
                'status': 'starting',
                'question': request.question
            }
            yield f"data: {json.dumps(metadata)}\n\n"
            
            # Handle V5/V6/V7/V8 database override
            if version in ["V5", "V6", "V7", "V8"] and request.use_local_db is not None:
                if provider == "openai":
                    if version == "V5":
                        rag_system = CordisRAG_V5(
                            ai_provider="openai",
                            openai_model_name=OPENAI_MODEL,
                            use_local_db=request.use_local_db,
                            database_url=DOCKER_DATABASE_URL
                        )
                    elif version == "V6":
                        rag_system = CordisRAG_V6(
                            ai_provider="openai",
                            openai_model_name=OPENAI_MODEL,
                            use_local_db=request.use_local_db,
                            database_url=DOCKER_DATABASE_URL
                        )
                    elif version == "V7":
                        if CordisRAG_V7 is not None:
                            rag_system = CordisRAG_V7(
                                ai_provider="openai",
                                openai_model_name=OPENAI_MODEL,
                                use_local_db=request.use_local_db,
                                database_url=DOCKER_DATABASE_URL
                            )
                        else:
                            # Fallback to V6 if V7 is not available
                            rag_system = CordisRAG_V6(
                                ai_provider="openai",
                                openai_model_name=OPENAI_MODEL,
                                use_local_db=request.use_local_db,
                                database_url=DOCKER_DATABASE_URL
                            )
                    else:  # V8
                        rag_system = CordisRAG_V8(
                            ai_provider="openai",
                            openai_model_name=OPENAI_MODEL,
                            use_local_db=request.use_local_db,
                            database_url=DOCKER_DATABASE_URL
                        )
                elif provider == "gemini":
                    if version == "V5":
                        rag_system = CordisRAG_V5(
                            ai_provider="gemini",
                            gemini_model_name=GEMINI_MODEL,
                            use_local_db=request.use_local_db,
                            database_url=DOCKER_DATABASE_URL
                        )
                    elif version == "V6":
                        rag_system = CordisRAG_V6(
                            ai_provider="gemini",
                            gemini_model_name=GEMINI_MODEL,
                            use_local_db=request.use_local_db,
                            database_url=DOCKER_DATABASE_URL
                        )
                    elif version == "V7":
                        if CordisRAG_V7 is not None:
                            rag_system = CordisRAG_V7(
                                ai_provider="gemini",
                                gemini_model_name=GEMINI_MODEL,
                                use_local_db=request.use_local_db,
                                database_url=DOCKER_DATABASE_URL
                            )
                        else:
                            # Fallback to V6 if V7 is not available
                            rag_system = CordisRAG_V6(
                                ai_provider="gemini",
                                gemini_model_name=GEMINI_MODEL,
                                use_local_db=request.use_local_db,
                                database_url=DOCKER_DATABASE_URL
                            )
                    else:  # V8
                        rag_system = CordisRAG_V8(
                            ai_provider="gemini",
                            gemini_model_name=GEMINI_MODEL,
                            use_local_db=request.use_local_db,
                            database_url=DOCKER_DATABASE_URL
                        )
            
            # Check if the RAG system supports streaming (V7 and V8)
            if version in ["V7", "V8"] and hasattr(rag_system, 'get_ai_response_stream'):
                # Use V7/V8 streaming capability
                # type: ignore - hasattr check ensures method exists
                async for chunk in rag_system.get_ai_response_stream(  # type: ignore
                    request.question, 
                    max_projects_to_process=request.max_results or 5
                ):
                    yield f"data: {json.dumps(chunk)}\n\n"
                    if chunk.get('type') == 'complete':
                        break
                    # Remove artificial delay - let natural streaming handle timing
            else:
                # Fallback for older versions - optimized streaming simulation
                yield f"data: {json.dumps({'type': 'progress', 'phase': 'processing', 'message': f'Processing with {version} (non-streaming mode)...'})}\n\n"
                
                # Get the regular response
                result = rag_system.get_ai_response(
                    request.question, 
                    max_projects_to_process=request.max_results or 5
                )
                
                processing_time = time.time() - start_time
                
                # Handle different return formats
                if isinstance(result, dict) and 'logs' in result:
                    # V6+ format
                    answer = result.get('answer', '')
                    logs = result.get('logs', {})
                    
                    # Optimized token streaming by larger chunks
                    chunk_size = 100  # Characters per chunk for faster streaming
                    for i in range(0, len(answer), chunk_size):
                        chunk = answer[i:i+chunk_size]
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                        # Small delay only every few chunks
                        if i % (chunk_size * 5) == 0:
                            await asyncio.sleep(0.01)
                    
                    # Send completion
                    completion_data = {
                        'type': 'complete',
                        'answer': answer,
                        'logs': logs,
                        'processing_time': round(processing_time, 2),
                        'ai_provider': provider,
                        'ai_version': version,
                        'data_source': logs.get('data_source', 'CORDIS API'),
                        'projects_found': logs.get('projects_retrieved', 0)
                    }
                    yield f"data: {json.dumps(completion_data)}\n\n"
                else:
                    # V2-V5 format - optimized chunking
                    answer = result if isinstance(result, str) else str(result)
                    
                    # Stream by larger chunks for better performance
                    chunk_size = 100
                    for i in range(0, len(answer), chunk_size):
                        chunk = answer[i:i+chunk_size]
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                        # Minimal delay only occasionally
                        if i % (chunk_size * 5) == 0:
                            await asyncio.sleep(0.01)
                    
                    # Send completion
                    data_source = "Local Database" if (hasattr(rag_system, 'use_local_db') and rag_system.use_local_db) else "CORDIS API"
                    completion_data = {
                        'type': 'complete',
                        'answer': answer,
                        'processing_time': round(processing_time, 2),
                        'ai_provider': provider,
                        'ai_version': version,
                        'data_source': data_source,
                        'projects_found': answer.count("🔗") if answer else 0
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
        media_type="text/plain",
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
    _, provider, version = get_rag_system(request.ai_provider, request.ai_version)
    
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
    """
    providers = {"V2": {}, "V3": {}, "V4": {}, "V5": {}, "V6": {}, "V7": {}, "V8": {}}
    for version in ["V2", "V3", "V4", "V5", "V6", "V7", "V8"]:
        for provider_name, rag_system in rag_systems[version].items():
            provider_info = {"is_default": provider_name == DEFAULT_AI_PROVIDER}
            
            if provider_name == "openai":
                provider_info["model"] = getattr(rag_system, "openai_model_name", OPENAI_MODEL)
            elif provider_name == "gemini":
                provider_info["model"] = getattr(rag_system, "gemini_model_name", GEMINI_MODEL)
            
            # Add V5/V6/V7/V8 specific information
            if version in ["V5", "V6", "V7", "V8"]:
                provider_info["supports_local_db"] = True
                provider_info["local_db_enabled"] = getattr(rag_system, "use_local_db", False)
                provider_info["database_available"] = DATABASE_URL is not None
                
                # V7 and V8 specific features
                if version in ["V7", "V8"]:
                    provider_info["supports_streaming"] = True
                    provider_info["supports_realtime_tokens"] = True
                    
                    # V8 specific enhancements
                    if version == "V8":
                        provider_info["performance_optimized"] = True
                        provider_info["enhanced_streaming"] = True
            
            providers[version][provider_name] = provider_info
    
    return {
        "available_providers": providers,
        "default_provider": DEFAULT_AI_PROVIDER,
        "v8_features": {
            "streaming_support": True,
            "performance_optimizations": True,
            "enhanced_error_handling": True,
            "optimized_chunking": True
        },
        "v7_features": {
            "streaming_support": True,
            "realtime_tokens": True,
            "enhanced_logging": True
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
        # Test database connection using V5 or V6
        if "openai" in rag_systems["V5"]:
            test_rag = rag_systems["V5"]["openai"]
        elif "gemini" in rag_systems["V5"]:
            test_rag = rag_systems["V5"]["gemini"]
        elif "openai" in rag_systems["V6"]:
            test_rag = rag_systems["V6"]["openai"]
        elif "gemini" in rag_systems["V6"]:
            test_rag = rag_systems["V6"]["gemini"]
        else:
            # Create a test instance
            test_rag = CordisRAG_V5(use_local_db=True, database_url=DOCKER_DATABASE_URL)
        
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
        rag_system, provider, version = get_rag_system(request.ai_provider, request.ai_version)
        
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

@app.get("/api/health")
async def health_check():
    """Enhanced health check endpoint with V5 database status."""
    try:
        providers_status = {}
        overall_status = "healthy"
        
        # Check all versions
        for version in ["V2", "V3", "V4", "V5", "V6", "V7"]:
            version_status = {}
            
            # Check OpenAI
            if "openai" in rag_systems[version]:
                version_status["openai"] = {"status": "configured"}
            elif os.getenv("OPENAI_API_KEY"):
                version_status["openai"] = {"status": "key_present_not_initialized"}
            else:
                version_status["openai"] = {"status": "not_configured"}
            
            # Check Gemini
            if "gemini" in rag_systems[version]:
                version_status["gemini"] = {"status": "configured"}
            elif os.getenv("GEMINI_API_KEY"):
                version_status["gemini"] = {"status": "key_present_not_initialized"}
            else:
                version_status["gemini"] = {"status": "not_configured"}
            
            providers_status[version] = version_status
        
        # Check V5/V6/V7 specific database status
        database_status = "not_configured"
        if DATABASE_URL:
            try:
                # Test with any available V5/V6/V7 instance
                test_rag = None
                for version in ["V7", "V6", "V5"]:  # Check newest first
                    if version in rag_systems and rag_systems[version]:
                        test_rag = next(iter(rag_systems[version].values()))
                        break
                
                if test_rag and hasattr(test_rag, 'db_pool') and test_rag.db_pool:
                    database_status = "connected"
                elif test_rag:
                    database_status = "configured_not_connected"
                else:
                    database_status = "configured_not_initialized"
            except Exception:
                database_status = "connection_error"
        
        # Determine overall status
        v7_available = bool(rag_systems.get("V7"))
        v6_available = bool(rag_systems.get("V6"))
        v5_available = bool(rag_systems.get("V5"))
        if not (v7_available or v6_available or v5_available):
            overall_status = "warning"
        
        return {
            "status": overall_status,
            "components": {
                "api": "online",
                "providers": providers_status,
                "database": {
                    "status": database_status,
                    "url_configured": DATABASE_URL is not None,
                    "local_db_enabled": USE_LOCAL_DB
                }
            },
            "versions": {
                "v2": bool(rag_systems.get("V2")),
                "v3": bool(rag_systems.get("V3")),
                "v4": bool(rag_systems.get("V4")),
                "v5": bool(rag_systems.get("V5")),
                "v6": bool(rag_systems.get("V6")),
                "v7": bool(rag_systems.get("V7"))
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)