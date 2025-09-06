"""
Main FastAPI application for CORDIS Research Projects RAG API.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
import logging

from .core.config import settings
from .api.routes import router
from .api.document_routes import router as document_router
from .api.enhanced_rag_routes import router as enhanced_rag_router
from .api.conversation_routes import router as conversation_router
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

# Include API routes
app.include_router(router)
app.include_router(document_router)
app.include_router(enhanced_rag_router)
app.include_router(conversation_router)

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Error processing request",
            "details": str(exc.detail)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle request validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid request format",
            "details": str(exc)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "details": "An unexpected error occurred"
        }
    )


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


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info(f"Shutting down {settings.app_name}")


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
