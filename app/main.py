"""
Main FastAPI application for CORDIS Research Projects RAG API.

Production-ready application with:
- Comprehensive error handling with MapItError exceptions
- Health monitoring endpoints (Kubernetes ready)
- Request context middleware for tracing
- Circuit breaker support for external services
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
import logging

from .core.config import settings
from .core.dependencies import initialize_cordis_repository, shutdown_cordis_repository
from .api.document_routes import router as document_router
from .api.conversation_routes_v3 import router as conversation_router_v3
from .api.call_document_routes import router as call_document_router
from .api.proposal_routes import router as proposal_router
from .api.health_routes import router as health_router
from .api.error_handlers import register_exception_handlers, register_middleware
from .models.schemas import ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A Retrieval-Augmented Generation (RAG) system for querying European research projects from the CORDIS database.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register global exception handlers and middleware
register_exception_handlers(app)
register_middleware(app)

# Include API routes
# Health routes - Kubernetes readiness/liveness probes
app.include_router(health_router)

app.include_router(document_router)
# V3 conversation routes - simplified agentic architecture (no intent classification)
app.include_router(conversation_router_v3)
# Include call document routes (simple, direct access to call documents)
app.include_router(call_document_router)
# Include proposal writing routes (AI-powered proposal assistance)
app.include_router(proposal_router)

# Include proposal document management routes (Live document editing)
from .api.proposal_document_routes import router as proposal_document_router
app.include_router(proposal_document_router)

# Include feedback routes (user feedback collection and analysis)
from .api.feedback_routes import router as feedback_router
app.include_router(feedback_router)

# V4 Proposal Session routes - unified AI Proposal Writer
from .api.proposal_session_routes import router as proposal_session_router
app.include_router(proposal_session_router)

# Batch operations routes (Priority 4.2)
from .api.batch_routes import router as batch_router
app.include_router(batch_router)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Database enabled: {settings.use_local_db}")
    logger.info(f"Supabase enabled: {settings.use_supabase}")
    logger.info(f"Vector search enabled: {settings.vector_search_enabled}")
    
    # Log available AI providers
    providers = []
    if settings.openai_api_key:
        providers.append("OpenAI")
    if settings.gemini_api_key:
        providers.append("Gemini")
    logger.info(f"Available AI providers: {', '.join(providers) if providers else 'None'}")
    
    # Log embedding configuration
    if settings.google_embedding_api_key:
        logger.info(f"Google Embedding API configured: {settings.embedding_model}")
    
    # Test services if enabled
    if settings.use_supabase:
        try:
            from .services.supabase_client import SupabaseVectorStore
            supabase = SupabaseVectorStore()
            if supabase.test_connection():
                logger.info("✅ Supabase connection successful")
            else:
                logger.warning("⚠️ Supabase connection failed")
        except Exception as e:
            logger.error(f"❌ Supabase initialization error: {e}")
    
    if settings.vector_search_enabled and settings.google_embedding_api_key:
        try:
            from .services.embedding_service import EmbeddingService
            embedder = EmbeddingService()
            if embedder.test_embedding_generation():
                logger.info("✅ Embedding service test successful")
            else:
                logger.warning("⚠️ Embedding service test failed")
        except Exception as e:
            logger.error(f"❌ Embedding service initialization error: {e}")
    
    # Initialize CORDIS repository if configured
    repository = initialize_cordis_repository()
    if repository:
        logger.info(f"📊 CORDIS source configuration: {settings.cordis_source}")
    else:
        logger.info("📊 CORDIS repository not configured (local database disabled)")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info(f"Shutting down {settings.app_name}")
    
    # Shutdown CORDIS repository
    shutdown_cordis_repository()


def create_app() -> FastAPI:
    """Application factory function."""
    return app


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )
