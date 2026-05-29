"""
FastAPI dependency injection for services and repositories.
"""

import logging

from fastapi import HTTPException, status

from ..services.data.cordis_repository import CordisProjectRepository
from .config import settings

logger = logging.getLogger(__name__)

# Global repository instance (singleton pattern)
_cordis_repository: CordisProjectRepository | None = None


def get_cordis_repository() -> CordisProjectRepository:
    """
    Get or create the CORDIS project repository singleton.

    Returns:
        CordisProjectRepository: Initialized repository instance

    Raises:
        HTTPException: If repository cannot be initialized
    """
    global _cordis_repository

    if _cordis_repository is None:
        if not settings.database_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="CORDIS repository not available: DATABASE_URL not configured",
            )

        try:
            _cordis_repository = CordisProjectRepository(database_url=settings.database_url)
            logger.info("✅ CORDIS repository initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CORDIS repository: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to initialize CORDIS repository: {str(e)}",
            ) from e

    return _cordis_repository


def initialize_cordis_repository() -> CordisProjectRepository | None:
    """
    Initialize the CORDIS repository during FastAPI startup.

    Returns:
        CordisProjectRepository or None: Initialized repository or None if initialization fails
    """
    global _cordis_repository

    if not settings.database_url:
        logger.warning("⚠️  DATABASE_URL not configured, skipping CORDIS repository initialization")
        return None

    try:
        _cordis_repository = CordisProjectRepository(database_url=settings.database_url)
        logger.info("✅ CORDIS repository initialized at startup")
        return _cordis_repository
    except Exception as e:
        logger.error(f"❌ Failed to initialize CORDIS repository at startup: {e}")
        return None


def shutdown_cordis_repository():
    """Shutdown the CORDIS repository and close connections."""
    global _cordis_repository

    if _cordis_repository is not None:
        try:
            _cordis_repository.close()
            logger.info("🔒 CORDIS repository connections closed")
        except Exception as e:
            logger.error(f"❌ Error closing CORDIS repository: {e}")
        finally:
            _cordis_repository = None


def get_cordis_source_config() -> dict:
    """
    Get CORDIS data source configuration for telemetry.

    Returns:
        dict: Configuration with local database status
    """
    return {
        "local_database_enabled": bool(settings.database_url),
        "cordis_data_available": bool(settings.database_url),  # CORDIS projects in local DB
    }
