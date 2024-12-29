from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://user:pass@db:5432/anti_leak"
    REDIS_HOST: str = "anti_leak_redis"
    REDIS_PORT: int = 6379

    JWT_SECRET: str = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 600

    # In production, load from a secure secret manager or encrypted volume:
    PRIVATE_KEY_PATH: str = "./keys/private_key.pem"
    PUBLIC_KEY_PATH: str = "./keys/public_key.pem"

    MASTER_SYM_KEY: str = None

    class Config:
        env_file = ".env"


settings = Settings()
