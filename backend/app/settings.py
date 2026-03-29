from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
        enable_decoding=False,
    )

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    app_name: str = "Kocaeli News Map API"
    app_version: str = "0.1.0"
    app_env: str = "dev"

    mongo_url: str
    mongo_db: str = "kocaeli_news"
    redis_url: str = "redis://localhost:6379"
    scheduler_enabled: bool = True
    scheduler_timezone: str = "Europe/Istanbul"
    scheduler_interval_hours: int = 3
    scheduler_lookback_days: int = 1
    scheduler_max_urls_per_source: int = 10
    scheduler_skip_domains: str = ""
    scrape_trigger_api_key: str | None = None
    scrape_trigger_rate_limit_enabled: bool = True
    scrape_trigger_rate_limit_requests: int = 5
    scrape_trigger_rate_limit_window_seconds: int = 60
    trusted_proxy_cidrs: str = ""
    job_ttl_seconds: int = 86400
    job_claim_idle_seconds: int = 14400
    job_heartbeat_seconds: int = 30
    job_max_attempts: int = 3
    job_retry_backoff_seconds: float = 5.0
    scheduled_job_lock_ttl_seconds: int = 21600

    classifier_semantic_enabled: bool = False
    classifier_semantic_threshold: float = 0.3
    classifier_keyword_only: bool = True

    ner_provider: str = "mock"
    ner_min_score: float = 0.50
    gliner_threshold: float = 0.50
    gliner_model_name: str = "urchade/gliner_multi-v2.1"
    bertturk_model_name: str = "savasy/bert-base-turkish-ner-cased"

    mcp_lease_ttl: int = 300
    mcp_idempotency_ttl: int = 86400
    mcp_queue_size: int = 1000
    mcp_max_retries: int = 3
    mcp_fail_closed: bool = True
    worker_id: str | None = None

    geocoding_provider: str = "mock"
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    nominatim_user_agent: str = "PULSE/1.0 kocaeli-news-platform"
    geocoding_timeout: int = 10
    geocoding_cache_ttl: int = 86400
    geocoding_max_retries: int = 2
    geocoding_min_confidence: float = 0.3
    opencage_api_key: str | None = None

    crawl_api_provider: str = "none"
    playwright_fallback_enabled: bool = False
    crawl_api_fallback_order: str = ""
    crawl_api_timeout: int = 30
    crawl_api_retry_attempts: int = 2
    crawl_api_retry_backoff_seconds: float = 1.5
    crawl_api_rate_limit_backoff_seconds: float = 8.0
    scrapingbee_api_key: str | None = None
    cloudflare_account_id: str | None = None
    cloudflare_api_token: str | None = None
    cloudflare_crawl_max_polls: int = 30
    cloudflare_crawl_poll_interval_seconds: float = 2.0


settings = Settings()
