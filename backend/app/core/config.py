"""Application configuration using pydantic-settings."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SEO Autopilot AI"
    app_env: str = "development"
    app_debug: bool = True
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    api_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Database – SQLite by default for zero-deps local run
    database_url: str = "sqlite+aiosqlite:////tmp/seo_autopilot.db"
    database_url_sync: str = "sqlite:////tmp/seo_autopilot.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # AI
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_ai_api_key: str = ""
    default_ai_provider: str = "openai"

    # Crawl safety
    max_pages_per_crawl: int = 50
    max_crawl_depth: int = 4
    crawl_delay_seconds: float = 0.3
    crawl_timeout_seconds: int = 20
    user_agent: str = "SEO-Autopilot-AI/1.0 (+https://seo-autopilot.ai)"

    # Security
    allowed_hosts: str = "localhost,127.0.0.1"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    rate_limit_per_minute: int = 60
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    max_request_body_bytes: int = 1_048_576
    disable_docs_in_production: bool = True

    # Auth cookies (httpOnly – not readable by browser JS)
    cookie_name: str = "seo_access_token"
    cookie_secure: bool = False  # True behind HTTPS in production
    cookie_samesite: str = "lax"  # lax | strict | none
    cookie_max_age_seconds: int = 60 * 60 * 24  # match token TTL

    # Bootstrap admin (server-side only – never exposed to browser)
    admin_email: str = ""
    admin_password: str = ""
    admin_full_name: str = "Platform Admin"

    github_client_id: str = ""
    github_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_hosts_list(self) -> List[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
