from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HeritageGuard Core API"
    app_description: str = "AI Preservasi Bahasa Jawa & Madura"
    app_version: str = "1.1.0"
    environment: str = "development"

    database_url: str = Field(
        ...,
        description="SQLAlchemy database URL. Use PostgreSQL in production/development deployment.",
    )
    sql_echo: bool = False

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cors_allow_credentials: bool = False

    storage_dir: Path = Path("/tmp/heritageguard")
    max_upload_bytes: int = 10 * 1024 * 1024
    max_text_chars: int = 5_000

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    translation_cache_enabled: bool = True
    translation_cache_ttl_seconds: int = 3600
    translation_cache_max_items: int = 512

    redis_url: str | None = None

    security_headers_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins")
    @classmethod
    def cors_origins_must_not_be_wildcard(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS tidak boleh berisi '*'")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def output_dir(self) -> Path:
        return self.storage_dir / "outputs"

    def ensure_storage_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
