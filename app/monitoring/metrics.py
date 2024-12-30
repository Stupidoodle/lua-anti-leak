import time
from prometheus_client import Counter, Histogram
from fastapi import Request


REQUEST_COUNT = Counter(
    "http_request_count", "Total HTTP requests", ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"]
)

FAILED_AUTH_ATTEMPTS = Counter(
    "failed_auth_attempts_total",
    "Total failed authentication attempts",
    ["ip_address"],
)

KEY_ROTATIONS = Counter(
    "key_rotations_total", "Total number of key rotations", ["status"]
)


async def metrics_middleware(request: Request, call_next: any) -> any:
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)

    return response
