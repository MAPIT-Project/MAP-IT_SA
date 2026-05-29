"""
Pydantic models for request and response schemas.
"""

from typing import Any

from pydantic import BaseModel, Field


# Request Models
class QuestionRequest(BaseModel):
    """Request model for RAG queries."""

    question: str = Field(..., description="The question to ask about European research projects")
    max_results: int | None = Field(
        5, ge=1, le=20, description="Maximum number of projects to retrieve"
    )
    ai_provider: str | None = Field(None, description="AI provider to use (openai or gemini)")
    ai_version: str | None = Field("V9", description="RAG version to use (V2-V9)")
    conversation_id: int | None = Field(
        None, description="Conversation ID for context-aware responses"
    )


# Project-related Models
class ProjectParticipant(BaseModel):
    """Model for project participant information."""

    name: str
    country: str
    city: str | None = None


class ProjectBudget(BaseModel):
    """Model for project budget information."""

    total_cost: str
    eu_contribution: str | None = None


class Project(BaseModel):
    """Model for a research project."""

    title: str
    objective: str
    keywords: list[str]
    budget: ProjectBudget
    participants: list[ProjectParticipant]
    call: dict[str, str]


# Response Models
class SearchResponse(BaseModel):
    """Response model for RAG queries."""

    answer: str | None = None
    ai_provider: str | None = None
    ai_version: str | None = None
    model_used: str | None = None
    data_source: str | None = None  # "Local Database" or "CORDIS API"
    processing_time: float | None = None
    projects_found: int | None = None
    projects: list[Project] | None = None
    error: bool | None = False
    error_message: str | None = None

    # Task-related fields for async processing
    task_id: str | None = None
    status: str | None = None  # "pending", "processing", "completed", "failed"

    # Additional metadata
    logs: dict[str, Any] | None = None
    success: bool | None = True


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    details: str


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: float
    version: str
    database_connected: bool | None = None
    celery_available: bool | None = None
    ai_providers: list[str] | None = None


class TaskStatusResponse(BaseModel):
    """Task status response model."""

    task_id: str
    status: str  # "pending", "processing", "completed", "failed", "cancelled"
    result: SearchResponse | None = None
    progress: dict[str, Any] | None = None
    error: str | None = None


class DatabaseStatusResponse(BaseModel):
    """Database status response model."""

    connected: bool
    total_projects: int | None = None
    last_updated: str | None = None
    connection_pool_status: dict[str, Any] | None = None


class ProviderConfig(BaseModel):
    """Configuration for a specific provider."""

    model: str
    is_default: bool


class ProvidersResponse(BaseModel):
    """Available AI providers response model."""

    available_providers: dict[str, dict[str, ProviderConfig]]
    default_provider: str


class BenchmarkResponse(BaseModel):
    """Benchmark test response model."""

    test_name: str
    processing_time: float
    ai_provider: str
    ai_version: str
    success: bool
    error_message: str | None = None
    projects_found: int | None = None
