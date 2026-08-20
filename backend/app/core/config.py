# backend/app/core/config.py
"""
Application configuration.

All configuration is loaded from environment variables (see .env.example).
Never hardcode secrets here.
"""
from functools import lru_cache
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings, populated from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    PROJECT_NAME: str = "SmartMarket DZ"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Security
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://smartmarket:smartmarket@postgres:5432/smartmarket"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql+psycopg2://smartmarket:smartmarket@postgres:5432/smartmarket"
    )

    # Redis / Celery
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # File storage
    UPLOAD_DIR: str = "/app/storage/uploads"
    REPORT_DIR: str = "/app/storage/reports"
    MAX_UPLOAD_SIZE_MB: int = 200

    # Rate limiting
    AUTH_RATE_LIMIT_PER_MINUTE: int = 10

    @model_validator(mode="after")
    def _normalize_database_url_schemes(self) -> "Settings":
        """
        Managed Postgres providers (Render, Heroku, Railway...) hand out a plain
        `postgres://` or `postgresql://` connection string with no driver hint.
        SQLAlchemy needs an explicit driver: `+asyncpg` for the async engine,
        `+psycopg2` for Alembic's sync engine. Normalize whatever scheme was
        supplied so the same env var works whether it came from docker-compose
        (already correct) or a managed provider (needs rewriting).
        """
        self.DATABASE_URL = self._with_driver(self.DATABASE_URL, "asyncpg")
        self.DATABASE_URL_SYNC = self._with_driver(self.DATABASE_URL_SYNC, "psycopg2")
        return self

    @staticmethod
    def _with_driver(url: str, driver: str) -> str:
        if "+" in url.split("://", 1)[0]:
            return url  # driver already specified, e.g. "postgresql+asyncpg://..."
        if url.startswith("postgres://"):
            return url.replace("postgres://", f"postgresql+{driver}://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", f"postgresql+{driver}://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (env is read once per process)."""
    return Settings()


settings = get_settings()

