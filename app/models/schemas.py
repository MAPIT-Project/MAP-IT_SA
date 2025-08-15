"""
Pydantic models for request and response schemas.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# Request Models
class QuestionRequest(BaseModel):
    """Request model for RAG queries."""
    question: str = Field(..., description="The question to ask about European research projects")
    max_results: Optional[int] = Field(5, ge=1, le=20, description="Maximum number of projects to retrieve")
    ai_provider: Optional[str] = Field(None, description="AI provider to use (openai or gemini)")
    ai_version: Optional[str] = Field("V9", description="RAG version to use (V2-V9)")
    use_local_db: Optional[bool] = Field(None, description="Override global setting for database usage")


# Project-related Models
class ProjectParticipant(BaseModel):
    """Model for project participant information."""
    name: str
    country: str
    city: Optional[str] = None


class ProjectBudget(BaseModel):
    """Model for project budget information."""
    total_cost: str
    eu_contribution: Optional[str] = None


class Project(BaseModel):
    """Model for a research project."""
    title: str
    objective: str
    keywords: List[str]
    budget: ProjectBudget
    participants: List[ProjectParticipant]
    call: Dict[str, str]


# Response Models
class SearchResponse(BaseModel):
    """Response model for RAG queries."""
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
    
    # Task-related fields for async processing
    task_id: Optional[str] = None
    status: Optional[str] = None  # "pending", "processing", "completed", "failed"
    
    # Additional metadata
    logs: Optional[Dict[str, Any]] = None
    success: Optional[bool] = True


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    details: str


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: float
    version: str
    database_connected: Optional[bool] = None
    celery_available: Optional[bool] = None
    ai_providers: Optional[List[str]] = None


class TaskStatusResponse(BaseModel):
    """Task status response model."""
    task_id: str
    status: str  # "pending", "processing", "completed", "failed", "cancelled"
    result: Optional[SearchResponse] = None
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DatabaseStatusResponse(BaseModel):
    """Database status response model."""
    connected: bool
    total_projects: Optional[int] = None
    last_updated: Optional[str] = None
    connection_pool_status: Optional[Dict[str, Any]] = None


class ProvidersResponse(BaseModel):
    """Available AI providers response model."""
    available_providers: List[str]
    default_provider: str
    models: Dict[str, str]


class BenchmarkResponse(BaseModel):
    """Benchmark test response model."""
    test_name: str
    processing_time: float
    ai_provider: str
    ai_version: str
    success: bool
    error_message: Optional[str] = None
    projects_found: Optional[int] = None
