import os
from dataclasses import field
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://user:pass@db:5432/anti_leak"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    RATE_LIMIT: int = 100
    RATE_LIMIT_WINDOW: int = 60

    MAX_REQUEST_SIZE: int = 1024 * 1024 * 10  # 10 MB
    MAX_JSON_DEPTH: int = 10

    REDIS_HOST: str = "anti_leak_redis"
    REDIS_PORT: int = 6379
    REDIS_MAX_CONNECTIONS: int = 100
    REDIS_SOCKET_TIMEOUT: int = 5

    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 600
    CORS_ORIGINS: list[str] = field(
        default_factory=lambda: ["*"]
    )  # TODO: Update this with the actual frontend URL

    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Anti Leak API"
    VERSION: str = "0.1.0"

    HEALTH_CHECK_INTERVAL: int = 30
    METRICS_ENABLED: bool = True

    VAULT_ADDRESS: str = None
    VAULT_TOKEN: str = None
    VAULT_MOUNT_POINT: str = None

    class Config:
        if os.getenv("ENV", "prod") == "dev":
            env_file = "../../.env.dev"
        else:
            env_file = "../../.env.prod"
        case_sensitive = True

    @property
    def is_development(self) -> bool:
        return self.DEBUG


@lru_cache()
def get_settings() -> Settings:
    return Settings()
