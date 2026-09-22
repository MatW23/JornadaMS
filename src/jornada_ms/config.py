"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, model_validator
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
    refresh_token_expire_seconds: int = Field(default=2_592_000, ge=3_600, le=31_536_000)
    login_rate_limit_attempts: int = Field(default=5, ge=1, le=100)
    login_rate_limit_window_seconds: int = Field(default=60, ge=10, le=3_600)
    jwt_secret: str = Field(
        default="development-only-change-this-jwt-secret-32-chars",
        min_length=32,
    )
    jwt_issuer: str = "jornada-ms"
    jwt_audience: str = "jornada-ms-web"
    correlation_header: str = "X-Correlation-ID"

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        if self.environment.lower() in {"production", "prod"} and self.jwt_secret.startswith(
            "development-only-"
        ):
            raise ValueError("JORNADA_MS_JWT_SECRET must be replaced in production")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
