"""
Health check endpoints for monitoring and load balancer integration.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    components: Dict[str, Any] = Field(default_factory=dict, description="Component health status")


class ReadinessResponse(BaseModel):
    """Readiness check response model."""
    ready: bool = Field(..., description="Whether the service is ready to accept traffic")
    checks: Dict[str, bool] = Field(default_factory=dict, description="Individual readiness checks")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Basic health check endpoint for monitoring"
)
async def health_check() -> HealthResponse:
    """
    Basic health check.

    Returns basic health status without checking dependencies.
    Use this for simple liveness probes.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        components={}
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Check",
    description="Readiness check with dependency verification"
)
async def readiness_check(response: Response) -> ReadinessResponse:
    """
    Readiness check with dependency verification.

    Checks if all critical dependencies are available.
    Use this for Kubernetes readiness probes.
    """
    settings = get_settings()
    checks = {}
    all_ready = True

    # Check database configuration
    db_configured = bool(settings.database.url) or settings.supabase.enabled
    checks["database_configured"] = db_configured
    if not db_configured:
        all_ready = False

    # Check AI provider configuration
    ai_configured = bool(
        settings.ai.openai_api_key or
        settings.ai.gemini_api_key or
        settings.ai.mistral_api_key or
        settings.ai.openrouter_api_key
    )
    checks["ai_provider_configured"] = ai_configured
    if not ai_configured:
        all_ready = False

    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        ready=all_ready,
        checks=checks
    )


@router.get(
    "/ping",
    response_model=Dict[str, str],
    summary="Ping",
    description="Simple ping endpoint"
)
async def ping() -> Dict[str, str]:
    """Simple ping endpoint for basic connectivity testing."""
    return {"ping": "pong"}
