from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "LittleGankNews"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_CORS_ORIGINS: str = "http://localhost:5173"
    API_AUTH_ENABLED: bool = False

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "littleganknews"
    POSTGRES_USER: str = "littleganknews"
    POSTGRES_PASSWORD: str = "change-me"
    DATABASE_URL: str = "postgresql+asyncpg://littleganknews:change-me@localhost:5432/littleganknews"

    REDIS_URL: str = "redis://localhost:6379/0"

    ARTIFACTS_DIR: str = "./storage/artifacts"
    BROWSER_PROFILES_DIR: str = "./storage/profiles"
    ARTIFACT_RETENTION_DAYS: int = 14

    BROWSER_PROVIDER: str = "cloakbrowser"
    BROWSER_HEADLESS: bool = False
    BROWSER_DEFAULT_TIMEOUT_MS: int = 30000
    BROWSER_PROFILE_LOCK_TTL_SECONDS: int = 300

    WORKER_HEARTBEAT_INTERVAL_SECONDS: int = 10
    WORKER_OFFLINE_AFTER_SECONDS: int = 60
    SCHEDULER_INTERVAL_SECONDS: int = 15
    HEALTH_CHECK_INTERVAL_SECONDS: int = 30
    LISTENER_MAX_PROFILES: int = 1
    DETAIL_WORKER_CONCURRENCY: int = 1
    FALLBACK_POLLER_ENABLED: bool = False

    X_BASE_URL: str = "https://x.com"
    X_LOGIN_CHECK_URL: str = "https://x.com/home"
    X_LISTEN_MODE: str = "list"

    STREAM_PREFIX: str = "lgn"
    STREAM_MAX_RETRIES: int = 5
    STREAM_CONSUMER_BLOCK_MS: int = 5000
    STREAM_CONSUMER_BATCH_SIZE: int = 10
    STREAM_MAXLEN: int = 10000

    SSE_HEARTBEAT_SECONDS: int = 15
    SSE_REPLAY_RECENT_LIMIT: int = 100

    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_DEFAULT_CHAT_ID: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.API_CORS_ORIGINS.split(",")]


settings = Settings()
