from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    app_name: str = "Kocaeli News Map API"
    app_version: str = "0.1.0"
    app_env: str = "dev"

    mongo_url: str
    mongo_db: str = "kocaeli_news"
    redis_url: str = "redis://localhost:6379"


settings = Settings()
