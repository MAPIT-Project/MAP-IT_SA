"""
Application configuration settings.
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App Info
    app_name: str = "CORDIS Research Projects RAG API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["*"]
    
    # AI Provider Configuration
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    default_ai_provider: str = "gemini"
    openai_model: str = "gpt-4-turbo"
    gemini_model: str = "gemini-2.0-flash-thinking-exp"
    
    # Database Configuration
    use_local_db: bool = False
    database_url: Optional[str] = None
    db_min_connections: int = 5
    db_max_connections: int = 50
    
    # Celery Configuration
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    redis_url: str = "redis://localhost:6379/0"
    
    # Docker Configuration
    docker_env: bool = False
    
    # Task Limits
    task_time_limit: int = 300  # 5 minutes
    task_soft_time_limit: int = 240  # 4 minutes
    
    @validator("openai_api_key", "gemini_api_key", pre=True)
    def validate_api_keys(cls, v):
        """Validate that at least one AI provider API key is provided."""
        return v
    
    @validator("database_url", pre=True)
    def validate_database_url(cls, v, values):
        """Validate database URL when local DB is enabled."""
        if values.get("use_local_db") and not v:
            raise ValueError("DATABASE_URL is required when use_local_db=True")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables


# Global settings instance
settings = Settings()
