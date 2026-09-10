from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TRDD_BE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "tarakdingdung"
    app_version: str = "v0.1.0"

    logger_format: str = "json"
    logger_level: str = "INFO"

    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_username: str = "postgres"
    postgres_password: str = "postgres"
    postgres_database: str = "tarakdingdung"
    postgres_pool_size: int = 20

    http_host: str = "0.0.0.0"
    http_port: int = 8080
    http_cors_allowed_origins: str = "*"

    token_access_secret: str = "dev-access-secret"
    token_refresh_secret: str = "dev-refresh-secret"
    token_access_ttl_seconds: int = 900
    token_refresh_ttl_seconds: int = 86400

    password_bcrypt_cost: int = 12

    cron_enabled: bool = False
    engine_interval_seconds: int = 86400

    engine_enabled: bool = False
    engine_mode: str = "paper"
    universe_id: str = "default"
    engine_venue: str = "indodax"
    engine_initial_equity: str = "10000000"

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-pro"

    indodax_api_key: str = ""
    indodax_secret_key: str = ""

    news_sources: str = ""

    seed_super_password: str = "changeme12345"
    seed_admin_password: str = "changeme12345"
    seed_user_password: str = "changeme12345"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )

    @property
    def news_sources_list(self) -> list[str]:
        return [s.strip() for s in self.news_sources.split(",") if s.strip()]
