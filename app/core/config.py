from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://user:pass@db:5432/anti_leak"
    REDIS_HOST: str = "anti_leak_redis"
    REDIS_PORT: int = 6379

    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 600

    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Anti Leak API"

    VAULT_ADDRESS: str = None
    VAULT_TOKEN: str = None
    VAULT_MOUNT_POINT: str = None

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
