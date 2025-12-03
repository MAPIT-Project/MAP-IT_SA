"""
Application configuration settings.
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import field_validator


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
    openrouter_api_key: Optional[str] = None
    default_ai_provider: str = "gemini"
    openai_model: str = "gpt-4-turbo"
    gemini_model: str = "gemini-flash-lite-latest"
    openrouter_model: str = "x-ai/grok-4-fast:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Google Embedding API Configuration (falls back to gemini_api_key)
    google_embedding_api_key: Optional[str] = None
    embedding_model: str = "models/text-embedding-004"
    embedding_dimension: int = 768
    
    @property
    def effective_embedding_api_key(self) -> Optional[str]:
        """Get embedding API key, falling back to Gemini key if not set."""
        return self.google_embedding_api_key or self.gemini_api_key
    
    # Database Configuration
    use_local_db: bool = False
    database_url: Optional[str] = None
    db_min_connections: int = 5
    db_max_connections: int = 50
    
    # CORDIS Configuration
    cordis_source: str = "local"  # Options: "local", "legacy_api"
    cordis_api_url: str = "https://cordis.europa.eu/api/search/results"
    cordis_api_timeout: int = 30
    
    # Supabase Configuration
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_key: Optional[str] = None
    use_supabase: bool = False
    
    # Vector Search Configuration
    vector_search_enabled: bool = False
    chunk_size: int = 1000
    chunk_overlap: int = 300  # Increased from 200 for better context preservation
    max_chunks_per_query: int = 20  # Increased from 5 for comprehensive retrieval
    similarity_threshold: float = 0.45  # Lowered from 0.7 for better recall
    
    # Celery Configuration
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    redis_url: str = "redis://localhost:6379/0"
    
    # Docker Configuration
    docker_env: bool = False
    
    # Task Limits
    task_time_limit: int = 300  # 5 minutes
    task_soft_time_limit: int = 240  # 4 minutes
    
    # Document Processing Configuration
    max_file_size_mb: int = 50
    supported_file_types: List[str] = [".pdf", ".txt", ".md", ".html"]
    upload_dir: str = "uploads"
    
    @field_validator("openai_api_key", "gemini_api_key", "openrouter_api_key")
    @classmethod
    def validate_api_keys(cls, v):
        """Validate that at least one AI provider API key is provided."""
        return v
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v, info):
        """Validate database URL when local DB is enabled."""
        if info.data.get("use_local_db") and not v:
            raise ValueError("DATABASE_URL is required when use_local_db=True")
        return v
    
    @field_validator("supabase_url", "supabase_service_key")
    @classmethod
    def validate_supabase_config(cls, v, info):
        """Validate Supabase configuration when enabled."""
        if info.data.get("use_supabase") and not v:
            field_name = info.field_name.upper()
            raise ValueError(f"{field_name} is required when use_supabase=True")
        return v
    
    @field_validator("google_embedding_api_key")
    @classmethod
    def validate_embedding_api_key(cls, v, info):
        """Validate Google API key when vector search is enabled."""
        if info.data.get("vector_search_enabled") and not v:
            raise ValueError("GOOGLE_EMBEDDING_API_KEY is required when vector_search_enabled=True")
        return v
    
    @field_validator("cordis_source")
    @classmethod
    def validate_cordis_source(cls, v):
        """Validate CORDIS source configuration."""
        valid_sources = ["local", "legacy_api"]
        if v not in valid_sources:
            raise ValueError(f"cordis_source must be one of: {valid_sources}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables


# Global settings instance
settings = Settings()
