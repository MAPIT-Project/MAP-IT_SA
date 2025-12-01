"""
FastAPI dependency injection for services and repositories.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from .config import settings
from ..services.data.cordis_repository import CordisProjectRepository
import logging

logger = logging.getLogger(__name__)

# Global repository instance (singleton pattern)
_cordis_repository: Optional[CordisProjectRepository] = None


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
        if not settings.use_local_db or not settings.database_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="CORDIS repository not available: local database not configured"
            )
        
        try:
            _cordis_repository = CordisProjectRepository(database_url=settings.database_url)
            logger.info("✅ CORDIS repository initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CORDIS repository: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to initialize CORDIS repository: {str(e)}"
            )
    
    return _cordis_repository


def initialize_cordis_repository() -> Optional[CordisProjectRepository]:
    """
    Initialize the CORDIS repository during FastAPI startup.
    
    Returns:
        CordisProjectRepository or None: Initialized repository or None if not configured
    """
    global _cordis_repository
    
    if not settings.use_local_db or not settings.database_url:
        logger.info("ℹ️ CORDIS repository not configured (local database disabled)")
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
    Get CORDIS source configuration for telemetry and decision making.
    
    Returns:
        dict: Configuration with source type and validation status
    """
    return {
        "source": settings.cordis_source,
        "api_url": settings.cordis_api_url,
        "timeout": settings.cordis_api_timeout,
        "local_enabled": settings.use_local_db and bool(settings.database_url),
        "legacy_api_available": bool(settings.cordis_api_url)
    }