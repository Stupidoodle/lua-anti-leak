import redis
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.secrets import get_vault_client, TokenManager
from app.database import SessionLocal
from app.models.telemetry import Telemetry
from app.schemas.telemetry import TelemetryPayload

router = APIRouter()
settings = get_settings()
r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_token_manager() -> TokenManager:
    vault_client = get_vault_client()
    return TokenManager(vault_client)


@router.post("/telemetry")
def telemetry_endpoint(
    payload: TelemetryPayload,
    token: str = Query(...),
    db: Session = Depends(get_db),
    token_manager: TokenManager = Depends(get_token_manager),
):
    decoded = token_manager.verify_token(token)
    user_id = decoded["uid"]

    telemetry_entry = Telemetry(
        user_id=user_id, event=payload.event, data=payload.details
    )

    db.add(telemetry_entry)
    db.commit()

    return {"status": "logged"}
