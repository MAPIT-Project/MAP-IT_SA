"""
MAPIT AI - FastAPI Application

Main entry point for the MAPIT AI REST API.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings, validate_settings
from app.api.routes import health_router, projects_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Runs startup and shutdown logic.
    """
    # Startup
    logger.info("Starting MAPIT AI API...")
    settings = get_settings()

    # Validate configuration (warning only, don't fail startup)
    errors = settings.validate()
    if errors:
        for error in errors:
            logger.warning(f"Configuration warning: {error}")

    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API will be available at http://{settings.api_host}:{settings.api_port}")

    yield

    # Shutdown
    logger.info("Shutting down MAPIT AI API...")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    app = FastAPI(
        title="MAPIT AI API",
        description="""
        MAPIT AI - Research Funding Intelligence Platform

        A RAG-based system for discovering EU funding opportunities,
        analyzing successful proposals, and generating high-quality
        funding applications.

        ## Features

        - **Project Search**: Search CORDIS projects with full-text and structured filters
        - **Project Details**: Get detailed information including publications and deliverables
        - **Health Checks**: Monitoring endpoints for load balancers and orchestration

        ## Documentation

        - [GitHub Repository](https://github.com/your-org/mapit-ai)
        - [System Architecture](docs_tracked/SYSTEM_ARCHITECTURE.md)
        """,
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router)
    app.include_router(projects_router, prefix="/api/v1")

    return app


# Create the application instance
app = create_app()


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirecting to API documentation."""
    return {
        "message": "MAPIT AI API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
