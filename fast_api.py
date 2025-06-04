from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import uvicorn
import asyncio
import random
from dotenv import load_dotenv
# Update import to use the new version
from cordisBased_RAG_function_new_V2 import CordisRAG

# Load environment variables
load_dotenv()

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

# Initialize the RAG systems for both providers (if keys are available)
rag_systems = {}

# Try to initialize OpenAI-based RAG
try:
    if os.getenv("OPENAI_API_KEY"):
        rag_systems["openai"] = CordisRAG(
            ai_provider="openai", 
            openai_model_name=OPENAI_MODEL
        )
        print(f"OpenAI RAG system initialized with model: {OPENAI_MODEL}")
except Exception as e:
    print(f"Failed to initialize OpenAI RAG system: {e}")

# Try to initialize Gemini-based RAG
try:
    if os.getenv("GEMINI_API_KEY"):
        rag_systems["gemini"] = CordisRAG(
            ai_provider="gemini", 
            gemini_model_name=GEMINI_MODEL
        )
        print(f"Gemini RAG system initialized with model: {GEMINI_MODEL}")
except Exception as e:
    print(f"Failed to initialize Gemini RAG system: {e}")

# Fallback to default if no systems initialized
if not rag_systems:
    print("WARNING: No RAG systems initialized. Using default OpenAI configuration.")
    rag_systems["openai"] = CordisRAG()  # Default to OpenAI

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
    answer: str
    ai_provider: Optional[str] = None
    model_used: Optional[str] = None
    projects: Optional[List[Project]] = None

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "online", "message": "CORDIS RAG API is running"}

def get_rag_system(ai_provider: Optional[str] = None):
    """
    Get the appropriate RAG system based on the requested provider
    or fall back to the default.
    """
    # Use requested provider if specified and available
    if ai_provider and ai_provider.lower() in rag_systems:
        return rag_systems[ai_provider.lower()], ai_provider.lower()
    
    # Otherwise use default provider if available
    if DEFAULT_AI_PROVIDER in rag_systems:
        return rag_systems[DEFAULT_AI_PROVIDER], DEFAULT_AI_PROVIDER
    
    # Fall back to first available provider
    if rag_systems:
        provider = next(iter(rag_systems.keys()))
        return rag_systems[provider], provider
    
    raise HTTPException(
        status_code=500, 
        detail="No AI providers are configured and available."
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
    
    Parameters:
    - question: A natural language question about European research projects
    - max_results: Maximum number of projects to retrieve (default: 5)
    - ai_provider: AI provider to use ("openai" or "gemini", optional)
    
    Returns:
    - answer: A comprehensive answer to the question
    - ai_provider: The AI provider used to generate the answer
    - model_used: The specific model used to generate the answer
    - projects: The retrieved project data (optional)
    """
    try:
        # Get the appropriate RAG system
        rag_system, provider = get_rag_system(request.ai_provider)
        
        # Get answer from RAG system
        answer = rag_system.get_ai_response(
            request.question, 
            max_projects_to_process=request.max_results
        )
        
        # Get model information
        model_used = None
        if provider == "openai":
            model_used = rag_system.openai_model_name
        elif provider == "gemini":
            model_used = rag_system.gemini_model_name
        
        # For now, we don't return the raw project data
        # This could be enhanced to return the structured project data
        return {
            "answer": answer,
            "ai_provider": provider,
            "model_used": model_used
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

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
    _, provider = get_rag_system(request.ai_provider)
    
    return {
        "answer": response,
        "ai_provider": provider,
        "demo": True,
        "processing_time": f"{delay:.2f} seconds",
        "query": request.question
    }

@app.get("/api/providers")
async def list_providers():
    """
    List all available AI providers and their models.
    """
    providers = {}
    
    for provider_name, rag_system in rag_systems.items():
        if provider_name == "openai":
            providers[provider_name] = {
                "model": rag_system.openai_model_name,
                "is_default": provider_name == DEFAULT_AI_PROVIDER
            }
        elif provider_name == "gemini":
            providers[provider_name] = {
                "model": rag_system.gemini_model_name,
                "is_default": provider_name == DEFAULT_AI_PROVIDER
            }
    
    return {
        "available_providers": providers,
        "default_provider": DEFAULT_AI_PROVIDER if DEFAULT_AI_PROVIDER in rag_systems else None
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