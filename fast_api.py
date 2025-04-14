from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import uvicorn
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