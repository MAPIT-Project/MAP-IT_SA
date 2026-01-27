"""
Entry point for the CORDIS Research Projects RAG API.
This file serves as the main entry point that can be used directly or with uvicorn.
"""

if __name__ == "__main__":
    import uvicorn

    from app.core.config import settings

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info",
    )
