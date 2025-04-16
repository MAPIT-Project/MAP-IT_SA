from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import uvicorn
import asyncio
import random
from cordisBased_RAG_function_new import CordisRAG

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

# Initialize the RAG system
rag_system = CordisRAG()

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

# Response models
class ProjectParticipant(BaseModel):
    name: str
    country: str
    city: str

class ProjectBudget(BaseModel):
    total_cost: str
    eu_contribution: str

class Project(BaseModel):
    title: str
    objective: str
    keywords: List[str]
    budget: ProjectBudget
    participants: List[ProjectParticipant]
    call: Dict[str, str]

class SearchResponse(BaseModel):
    answer: str
    projects: Optional[List[Project]] = None

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "online", "message": "CORDIS RAG API is running"}

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
    
    Returns:
    - answer: A comprehensive answer to the question
    - projects: The retrieved project data (optional)
    """
    try:
        # Get answer from RAG system
        answer = rag_system.get_ai_response(request.question)
        
        # For now, we don't return the raw project data
        # This could be enhanced to return the structured project data
        return {"answer": answer}
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
    
    return {
        "answer": response,
        "demo": True,
        "processing_time": f"{delay:.2f} seconds",
        "query": request.question
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check endpoint."""
    # Add more comprehensive health checks here if needed
    try:
        # Basic test to ensure the OpenAI client is working
        if not os.getenv("OPENAI_API_KEY"):
            return {
                "status": "warning",
                "message": "API is running but OPENAI_API_KEY is not set"
            }
        
        return {
            "status": "healthy",
            "components": {
                "api": "online",
                "openai": "configured"
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