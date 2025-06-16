from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import uvicorn
import asyncio
import random
import logging
from dotenv import load_dotenv
# Dynamically import both V2, V3, and V4 RAG classes
from cordisBased_RAG_function_new_V2 import CordisRAG as CordisRAG_V2
from cordisBased_RAG_function_new_V3 import CordisRAG as CordisRAG_V3
from cordisBased_RAG_function_new_V4 import CordisRAG as CordisRAG_V4

# Load environment variables
load_dotenv()

# Add logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get provider config from environment
DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "gemini").lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

# Create FastAPI app
app = FastAPI(
    title="CORDIS Research Projects RAG API",
    description="API for querying European research projects using a Retrieval-Augmented Generation approach",
    version="1.0.0"
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

# Initialize the RAG systems for both providers and all versions
rag_systems = {"V2": {}, "V3": {}, "V4": {}}

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
        )
        print(f"OpenAI RAG systems initialized for V2, V3, and V4 with model: {OPENAI_MODEL}")
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
        )
        print(f"Gemini RAG systems initialized for V2, V3, and V4 with model: {GEMINI_MODEL}")
except Exception as e:
    print(f"Failed to initialize Gemini RAG system: {e}")

# Fallback to default if no systems initialized
if not rag_systems["V2"] and not rag_systems["V3"] and not rag_systems["V4"]:
    print("WARNING: No RAG systems initialized. Using default OpenAI configuration for V4.")
    rag_systems["V4"]["openai"] = CordisRAG_V4()  # Default to OpenAI V4

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
    ai_version: Optional[str] = "V4"   # Default to V4, allow switching between V2, V3, and V4

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
    model_used: Optional[str] = None
    projects: Optional[List[Project]] = None
    error: Optional[bool] = False
    error_message: Optional[str] = None

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "online", "message": "CORDIS RAG API is running"}

def get_rag_system(ai_provider: Optional[str] = None, ai_version: Optional[str] = "V4"):
    version = ai_version.upper() if ai_version else "V4"
    if version not in rag_systems:
        raise HTTPException(status_code=400, detail=f"Invalid ai_version '{ai_version}'. Supported: V2, V3, V4.")
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
    
    This endpoint uses a RAG (Retrieval-Augmented Generation) system to:
    1. Parse the user's question
    2. Extract relevant search queries
    3. Search the CORDIS database
    4. Generate a comprehensive answer based on the retrieved data
    
    Parameters:    - question: A natural language question about European research projects
    - max_results: Maximum number of projects to retrieve (default: 5)
    - ai_provider: AI provider to use ("openai" or "gemini", optional)
    - ai_version: AI version to use ("V2", "V3", or "V4", optional, default: "V4")
    
    Returns:
    - answer: A comprehensive answer to the question
    - ai_provider: The AI provider used to generate the answer
    - model_used: The specific model used to generate the answer
    - projects: The retrieved project data (optional)
    """
    try:
        logger.info(f"Processing query: '{request.question}' with provider: {request.ai_provider} and version: {request.ai_version}")
        rag_system, provider, version = get_rag_system(request.ai_provider, request.ai_version)
        answer = rag_system.get_ai_response(
            request.question, 
            max_projects_to_process=request.max_results
        )
        model_used = None
        if provider == "openai":
            model_used = getattr(rag_system, "openai_model_name", OPENAI_MODEL)
        elif provider == "gemini":
            model_used = getattr(rag_system, "gemini_model_name", GEMINI_MODEL)
        return SearchResponse(
            answer=answer,
            ai_provider=provider,
            model_used=model_used
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

@app.post("/api/demo")
async def demo_query(request: QuestionRequest, background_tasks: BackgroundTasks):
    """
    Simulated query endpoint that returns a fake AI response after a short delay.
    
    This endpoint is designed for UI testing and development purposes.
    It does not perform actual CORDIS queries but returns predefined responses.
    
    Parameters:
    - question: A natural language question (not actually processed)
    - max_results: Ignored in demo mode
    
    Returns:
    - answer: A simulated AI response
    """
    # Choose a random response
    response = random.choice(DEMO_RESPONSES)
      # Simulate processing time (2-5 seconds)
    delay = random.uniform(2, 5)
    
    # Return a response after delay
    await asyncio.sleep(delay)
    
    # Get the requested or default AI provider for the response info
    _, provider, version = get_rag_system(request.ai_provider, request.ai_version)
    
    return {
        "answer": response,
        "ai_provider": provider,
        "ai_version": version,
        "demo": True,
        "processing_time": f"{delay:.2f} seconds",
        "query": request.question
    }

@app.get("/api/providers")
async def list_providers():
    """
    List all available AI providers and their models for V2, V3, and V4.
    """
    providers = {"V2": {}, "V3": {}, "V4": {}}
    for version in ["V2", "V3", "V4"]:
        for provider_name, rag_system in rag_systems[version].items():
            if provider_name == "openai":
                providers[version][provider_name] = {
                    "model": getattr(rag_system, "openai_model_name", OPENAI_MODEL),
                    "is_default": provider_name == DEFAULT_AI_PROVIDER
                }
            elif provider_name == "gemini":
                providers[version][provider_name] = {
                    "model": getattr(rag_system, "gemini_model_name", GEMINI_MODEL),
                    "is_default": provider_name == DEFAULT_AI_PROVIDER
                }
    return {
        "available_providers": providers,
        "default_provider": DEFAULT_AI_PROVIDER
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check endpoint."""
    # Add more comprehensive health checks here if needed
    try:
        providers_status = {}
        overall_status = "healthy"
        
        # Check OpenAI
        if "openai" in rag_systems:
            providers_status["openai"] = {"status": "configured"}
        elif os.getenv("OPENAI_API_KEY"):
            providers_status["openai"] = {"status": "key_present_not_initialized"}
        else:
            providers_status["openai"] = {"status": "not_configured"}
            overall_status = "warning"
        
        # Check Gemini
        if "gemini" in rag_systems:
            providers_status["gemini"] = {"status": "configured"}
        elif os.getenv("GEMINI_API_KEY"):
            providers_status["gemini"] = {"status": "key_present_not_initialized"}
        else:
            providers_status["gemini"] = {"status": "not_configured"}
        
        # If no providers are properly configured, mark as unhealthy
        if "openai" not in rag_systems and "gemini" not in rag_systems:
            overall_status = "unhealthy" 
        
        return {
            "status": overall_status,
            "components": {
                "api": "online",
                "providers": providers_status
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    # Run the FastAPI app with uvicorn
    uvicorn.run("fast_api:app", host="0.0.0.0", port=8000, reload=True)