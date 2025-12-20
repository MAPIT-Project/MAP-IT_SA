"""
Application configuration management.
Centralizes all environment variable access and validation.
"""

import os
from typing import List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    min_connections: int = field(default_factory=lambda: int(os.getenv("DB_MIN_CONNECTIONS", "5")))
    max_connections: int = field(default_factory=lambda: int(os.getenv("DB_MAX_CONNECTIONS", "20")))
    use_local_db: bool = field(default_factory=lambda: os.getenv("USE_LOCAL_DB", "false").lower() == "true")


@dataclass
class SupabaseConfig:
    """Supabase configuration settings."""
    url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    anon_key: str = field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", ""))
    service_key: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_KEY", ""))
    enabled: bool = field(default_factory=lambda: os.getenv("USE_SUPABASE", "false").lower() == "true")


@dataclass
class AIProviderConfig:
    """AI provider configuration settings."""
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4-turbo"))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-flash-latest"))
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    openrouter_model: str = field(default_factory=lambda: os.getenv("OPENROUTER_MODEL", "x-ai/grok-4-fast:free"))
    mistral_api_key: str = field(default_factory=lambda: os.getenv("MAPIT_LLM_KEY", ""))
    default_provider: str = field(default_factory=lambda: os.getenv("DEFAULT_AI_PROVIDER", "gemini"))


@dataclass
class GraphDBConfig:
    """Graph database configuration settings."""
    dgraph_url: str = field(default_factory=lambda: os.getenv("DGRAPH_URL", "localhost:9080"))
    neo4j_uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", ""))


@dataclass
class CacheConfig:
    """Cache and async configuration settings."""
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    celery_broker_url: str = field(default_factory=lambda: os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    celery_result_backend: str = field(default_factory=lambda: os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"))


@dataclass
class Settings:
    """Main application settings container."""
    # API settings
    api_host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # CORS settings
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

    # Feature flags
    vector_search_enabled: bool = field(default_factory=lambda: os.getenv("VECTOR_SEARCH_ENABLED", "true").lower() == "true")

    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    supabase: SupabaseConfig = field(default_factory=SupabaseConfig)
    ai: AIProviderConfig = field(default_factory=AIProviderConfig)
    graph_db: GraphDBConfig = field(default_factory=GraphDBConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)

    def validate(self) -> List[str]:
        """
        Validate required configuration settings.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.database.url and not self.supabase.enabled:
            errors.append("DATABASE_URL is required when USE_SUPABASE is false")

        if self.supabase.enabled:
            if not self.supabase.url:
                errors.append("SUPABASE_URL is required when USE_SUPABASE is true")
            if not self.supabase.anon_key:
                errors.append("SUPABASE_ANON_KEY is required when USE_SUPABASE is true")

        # At least one AI provider should be configured
        has_ai_provider = any([
            self.ai.openai_api_key,
            self.ai.gemini_api_key,
            self.ai.mistral_api_key,
            self.ai.openrouter_api_key
        ])
        if not has_ai_provider:
            errors.append("At least one AI provider API key is required")

        return errors


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the application settings instance."""
    return settings


def validate_settings() -> None:
    """
    Validate settings on startup and raise if invalid.

    Raises:
        ValueError: If required settings are missing
    """
    errors = settings.validate()
    if errors:
        raise ValueError(f"Configuration errors: {'; '.join(errors)}")
