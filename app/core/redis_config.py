import redis

from app.core.config import get_settings
from app.core.logging_config import configure_logger

logger = configure_logger()
settings = get_settings()
redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
)


def get_redis() -> redis.Redis:
    redis_client = redis.Redis(connection_pool=redis_pool)

    try:
        redis_client.ping()
        return redis_client
    except redis.exceptions.ConnectionError as e:
        logger.error(
            "redis_connection_failed",
            status="failed",
            error=str(e),
        )
        raise e
