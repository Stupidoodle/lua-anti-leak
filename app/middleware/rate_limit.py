import redis
import structlog
import time
from datetime import timedelta
from fastapi import Request, HTTPException

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class RateLimitExceeded(HTTPException):
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "retry_after": retry_after,
            },
        )


class RateLimiter:
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client
        self.rate_limit = settings.RATE_LIMIT
        self.window = settings.RATE_LIMIT_WINDOW
        self.logger = logger.bind(component="rate_limiter")

    async def _generate_key(self, request: Request) -> str:
        """Generate a unique key for rate limiting based on IP and endpoint"""
        ip = request.client.host
        path = request.url.path
        return f"rate_limit:{ip}:{path}:{int(time.time() // self.window)}"

    async def is_rate_limited(self, request: Request) -> None:
        """Check if the request should be rate limited"""
        key = await self._generate_key(request)

        pipeline = self.redis.pipeline()

        pipeline.incr(key)
        pipeline.expire(key, self.window)

        result = pipeline.execute()
        request_count = result[0]

        if request_count > self.rate_limit:
            retry_after = self.window - (int(time.time()) % self.window)

            self.logger.warning(
                "rate_limit_exceeded",
                ip=request.client.host,
                path=request.url.path,
                count=request_count,
            )

            raise RateLimitExceeded(retry_after=retry_after)

        request.state.rate_limit_remaining = self.rate_limit - request_count
        request.state.rate_limit_reset = self.window - (int(time.time()) % self.window)


async def rate_limit_middleware(request: Request, call_next: any) -> any:
    """Middleware to apply rate limiting to all requests"""
    try:
        if request.url.path == "/health":
            return await call_next(request)

        rate_limiter = RateLimiter(request.app.state.redis)
        await rate_limiter.is_rate_limited(request)

        response = await call_next(request)

        response.headers["X-RateLimit-Remaining"] = str(
            request.state.rate_limit_remaining
        )
        response.headers["X-RateLimit-Reset"] = str(request.state.rate_limit_reset)

        return response
    except RateLimitExceeded as e:
        raise e
    except Exception as e:
        logger.error(
            "rate_limit_error",
            error=str(e),
            path=request.url.path,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
