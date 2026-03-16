from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tg_api_id: int | None = None
    tg_api_hash: str | None = None
    tg_phone: str | None = None
    tg_session_path: str = ".secrets/tg_session"

    db_url: str = "sqlite:///./data/tgaggerator.db"

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    ui_api_base: str = "http://127.0.0.1:8000"

    default_bootstrap_limit: int = 200
    ingest_interval_sec: int = 30

    ingest_max_retries: int = 3
    ingest_retry_base_sec: int = 2
    ingest_retry_max_sec: int = 30


settings = Settings()
