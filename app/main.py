import redis
import structlog
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from starlette.responses import JSONResponse

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.script import router as script_router
from app.api.v1.endpoints.telemetry import router as telemetry_router
from app.middleware.rate_limit import rate_limit_middleware
from app.middleware.validation import validation_middleware
from app.monitoring.health import router as health_router
from app.monitoring.metrics import metrics_middleware
from app.core.config import get_settings
from app.core.secrets import get_vault_client
from app.core.key_management import KeyManager
from app.core.key_rotation_manager import KeyRotationManager
from app.database import SessionLocal, engine

logger = structlog.get_logger()
settings = get_settings()
redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
)
r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)


@asynccontextmanager
async def lifespan(arg_app: FastAPI) -> any:
    try:
        vault_client = get_vault_client()

        key_manager = KeyManager(vault_client)
        key_manager.initialize_if_needed()

        key_rotation_manager = KeyRotationManager(r, key_manager)
        await key_rotation_manager.check_and_rotate_keys()

        engine.dispose()
        engine.pool.dispose()

        engine.pool = engine.pool.recreate(
            size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            timeout=settings.DB_POOL_TIMEOUT,
            recycle=settings.DB_POOL_RECYCLE,
        )

        logger.info(
            "application_startup_complete",
            status="success",
            vault_initialized=True,
            key_rotation_initialized=True,
        )
    except Exception as e:
        logger.error(
            "application_startup_failed",
            status="failed",
            error=str(e),
        )
        raise e
    yield
    try:
        engine.dispose()

        app.state.redis.close()
        redis_pool.disconnect()

        logger.info("application_shutdown_complete", status="success")
    except Exception as e:
        logger.error("application_shutdown_failed", status="failed", error=str(e))
        raise e


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan, version=settings.VERSION)
app.state.redis = r

# noinspection PyTypeChecker
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # TODO: Update this to only allow specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    return response


app.middleware("http")(validation_middleware)
app.middleware("http")(rate_limit_middleware)

if settings.METRICS_ENABLED:
    app.middleware("http")(metrics_middleware)
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(script_router, prefix="/api/v1/script", tags=["script"])
app.include_router(telemetry_router, prefix="/api/v1/telemetry", tags=["telemetry"])
app.include_router(health_router, prefix="/monitoring", tags=["health"])


@app.middleware("http")
async def log_requests(request: Request, call_next: any):
    """Log all incoming requests and their processing time"""
    start_time = time.time()
    request_id = str(uuid.uuid4())

    log = logger.bind(
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        client_ip=request.client.host,
    )

    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000

        log.info(
            "request_processed",
            status_code=response.status_code,
            process_time=process_time,
        )

        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        log.error(
            "request_failed",
            error=str(e),
            status_code=500,
            processing_time=(time.time() - start_time) * 1000,
        )
        raise


@app.exception_handlers(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request.headers.get("X-Request-ID"),
        },
    )


@app.get("/")
async def root():
    """Root endpoint for basic API information"""
    return {
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs_url": "/docs",
        "health_check": "/monitoring/health",
    }
