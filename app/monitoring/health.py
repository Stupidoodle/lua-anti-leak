import jwt
import redis
import structlog
import time
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.core.config import get_settings
from app.core.redis_config import get_redis
from app.core.secrets import get_vault_client
from app.models.auth import AuthorizedUser

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class HealthChecker:
    def __init__(self, db: Session, redis_client: redis.Redis, vault_client: any):
        self.db = db
        self.redis = redis_client
        self.vault_client = vault_client
        self.failed_auth_key = "failed_auth_attempts:"
        self.sussy_baka_ips_key = "suspicious_ips"

    async def check_database(self) -> dict[str, any]:
        """Check database connectivity and basic operations"""
        try:
            start_time = time.time()
            self.db.query(AuthorizedUser).first()
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            return {"status": "healthy", "latency_ms": latency_ms}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def check_redis(self) -> dict[str, any]:
        """Check Redis connectivity and operations"""
        try:
            start_time = time.time()
            self.redis.ping()
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            return {"status": "healthy", "latency_ms": latency_ms}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def check_vault(self) -> dict[str, any]:
        """Check Vault connectivity and seal status"""
        try:
            seal_status = self.vault_client.client.sys.read_seal_status()
            return {
                "status": "healthy" if not seal_status["sealed"] else "sealed",
                "sealed": seal_status["sealed"],
            }
        except Exception as e:
            logger.error("vault_health_check_failed", error=str(e))
            return {"status": "unhealthy", "error": str(e)}

    def record_failed_auth(self, ip_address: str) -> None:
        """Record failed authentication attempts"""
        pipeline = self.redis.pipeline()
        key = f"{self.failed_auth_key}{ip_address}"

        pipeline.incr(key)
        pipeline.expire(key, 3600)  # TODO: Move to settings

        current_count = int(self.redis.get(key) or 0)

        if current_count >= 5:
            pipeline.sadd(self.sussy_baka_ips_key, ip_address)
            logger.warning(
                "suspicious_activity_detected",
                ip_address=ip_address,
                failed_attempts=current_count,
            )

        pipeline.execute()

    def check_suspicious_activity(self, ip_address: str) -> bool:
        """Check if an IP address is suspicious"""
        return bool(self.redis.sismember(self.sussy_baka_ips_key, ip_address))


@router.get("/health")
async def health_check(
    db: Session = Depends(get_db), r: redis.Redis = Depends(get_redis)
):
    """Comprehensive health check endpoint"""
    vault_client = get_vault_client()
    checker = HealthChecker(db, r, vault_client)

    db_health = await checker.check_database()
    redis_health = await checker.check_redis()
    vault_health = await checker.check_vault()

    all_healthy = all(
        check["status"] == "healthy"
        for check in [db_health, redis_health, vault_health]
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": db_health,
            "redis": redis_health,
            "vault": vault_health,
        },
    }
