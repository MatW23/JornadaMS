"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the API and persistence layer."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="JORNADA_MS_",
        extra="ignore",
    )

    app_name: str = "JornadaMS API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    database_url: str = Field(
        default="postgresql+psycopg://jornada_ms:jornada_ms@localhost:5432/jornada_ms",
        description="SQLAlchemy database URL.",
    )
    database_echo: bool = False
    access_token_expire_seconds: int = Field(default=900, ge=60, le=86_400)
    correlation_header: str = "X-Correlation-ID"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
