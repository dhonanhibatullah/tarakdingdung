from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TRDD_BE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "tarakdingdung"
    app_version: str = "v0.1.0-dev.1"

    logger_format: Literal["plain", "json"] = "json"
    logger_level: str = "INFO"

    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_username: str = "postgres"
    postgres_password: str = "postgres"
    postgres_database: str = "tarakdingdung"
    postgres_pool_size: int = 20

    http_host: str = "0.0.0.0"
    http_port: int = 8080
    http_cors_allowed_origins: Annotated[list[str], NoDecode] = ["*"]

    token_access_secret: str = "tarakdingdung-access-secret"
    token_refresh_secret: str = "tarakdingdung-refresh-secret"
    token_access_ttl_seconds: int = 900
    token_refresh_ttl_seconds: int = 86400

    password_bcrypt_cost: int = 12

    seed_super_password: str = "changeme12345"
    seed_admin_password: str = "changeme12345"
    seed_user_password: str = "changeme12345"

    tokocrypto_api_key: str = "changemetokocryptoapikey"
    tokocrypto_secret_key: str = "changemetokocryptosecretkey"
    tokocrypto_v3_base_url: str = "https://www.tokocrypto.site"
    indodax_v1_api_key: str = "changemeindodaxv1apikey"
    indodax_v1_secret_key: str = "changemeindodaxv1secretkey"
    indodax_v2_api_key: str = "changemeindodaxv2apikey"
    indodax_v2_secret_key: str = "changemeindodaxv2secretkey"

    exchange_timeout_seconds: float = 15.0

    # Cron cadences. The collector runs faster than the engine so a cycle
    # always decides on data it did not have to wait for.
    cron_enabled: bool = False
    cron_collect_seconds: int = 300
    cron_portfolio_seconds: int = 300
    cron_engine_seconds: int = 3600
    cron_interval: str = "1h"
    # A snapshot older than this is refused rather than sized against: a stale
    # price looks valid and would place a real order at a dead level.
    cron_max_snapshot_age_seconds: int = 7200

    @field_validator("http_cors_allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
