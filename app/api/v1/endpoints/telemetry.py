import redis
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal
from app.models.telemetry import Telemetry
from app.services.auth import verify_jwt
from app.schemas.telemetry import TelemetryPayload

router = APIRouter()
r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/telemetry")
def telemetry_endpoint(
    payload: TelemetryPayload, token: str = Query(...), db: Session = Depends(get_db)
):
    decoded = verify_jwt(token)
    user_id = decoded["uid"]

    telemetry_entry = Telemetry(
        user_id=user_id, event=payload.event, data=payload.details
    )

    db.add(telemetry_entry)
    db.commit()

    return {"status": "logged"}
