"""
Application configuration settings.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App Info
    app_name: str = "CORDIS Research Projects RAG API"
    app_version: str = "1.0.0"
    debug: bool = False

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["*"]

    # AI Provider Configuration
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    openrouter_api_key: str | None = None
    default_ai_provider: str = "gemini"
    openai_model: str = "gpt-4-turbo"
    gemini_model: str = "gemini-3-flash-preview"
    gemini_pro_model: str = "gemini-3.1-pro-preview"
    smart_model_routing: bool = True
    openrouter_model: str = "x-ai/grok-4-fast:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Google Embedding API Configuration (falls back to gemini_api_key)
    google_embedding_api_key: str | None = None
    embedding_model: str = "models/gemini-embedding-001"
    embedding_dimension: int = 3072

    @property
    def effective_embedding_api_key(self) -> str | None:
        """Get embedding API key, falling back to Gemini key if not set."""
        return self.google_embedding_api_key or self.gemini_api_key

    # Database Configuration (Required)
    database_url: str
    db_min_connections: int = 5
    db_max_connections: int = 50

    # Supabase Configuration (Required)
    supabase_url: str
    supabase_anon_key: str | None = None
    supabase_service_key: str

    # EU Portal API Configuration
    eu_portal_base_url: str = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
    eu_portal_topic_details_url: str = (
        "https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails"
    )
    eu_portal_facet_url: str = "https://api.tech.ec.europa.eu/search-api/prod/rest/facet"

    # Call Enrichment Service Configuration
    call_enrichment_max_retries: int = 3
    call_enrichment_base_delay: float = 1.0  # seconds
    call_enrichment_max_delay: float = 30.0  # seconds
    call_enrichment_exponential_base: float = 2.0
    call_enrichment_cache_ttl: int = 3600  # 1 hour in seconds

    # Enhanced Call Search Configuration
    enhanced_call_search_cache_ttl: int = 3600  # 1 hour in seconds

    # Similar Projects Tool Configuration
    embedding_timeout: float = 30.0  # seconds
    vector_search_timeout: float = 10.0  # seconds
    graph_context_timeout: float = 30.0  # seconds

    # Query Processing Configuration
    long_query_threshold: int = 500  # characters
    max_processed_query_length: int = 400  # characters

    # Vector Search Configuration
    vector_search_enabled: bool = False
    chunk_size: int = 1000
    chunk_overlap: int = 300  # Increased from 200 for better context preservation
    max_chunks_per_query: int = 20  # Increased from 5 for comprehensive retrieval
    similarity_threshold: float = 0.45  # Lowered from 0.7 for better recall

    # Celery Configuration
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    redis_url: str = "redis://localhost:6379/0"

    # Docker Configuration
    docker_env: bool = False

    # Task Limits
    task_time_limit: int = 300  # 5 minutes
    task_soft_time_limit: int = 240  # 4 minutes

    # Document Processing Configuration
    max_file_size_mb: int = 50
    supported_file_types: list[str] = [".pdf", ".txt", ".md", ".html"]
    upload_dir: str = "uploads"

    @field_validator("openai_api_key", "gemini_api_key", "openrouter_api_key")
    @classmethod
    def validate_api_keys(cls, v):
        """Validate that at least one AI provider API key is provided."""
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v):
        """Validate database URL (required)."""
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v

    @field_validator("supabase_url", "supabase_service_key")
    @classmethod
    def validate_supabase_config(cls, v):
        """Validate Supabase configuration (required)."""
        if not v:
            if "supabase_url" in str(v).lower():
                raise ValueError("SUPABASE_URL is required")
            else:
                raise ValueError("SUPABASE_SERVICE_KEY is required")
        return v

    @field_validator("google_embedding_api_key")
    @classmethod
    def validate_embedding_api_key(cls, v, info):
        """Validate Google API key when vector search is enabled."""
        if info.data.get("vector_search_enabled") and not v:
            raise ValueError("GOOGLE_EMBEDDING_API_KEY is required when vector_search_enabled=True")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables


# Global settings instance
settings = Settings()
