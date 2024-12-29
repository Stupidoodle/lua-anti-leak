import redis
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal
from app.models.auth import AuthorizedUser
from app.schemas.auth import AuthPayload
from app.services.auth import generate_jwt
from app.utils.crypto_utils import generate_ephemeral_key

router = APIRouter()
r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/auth")
def auth_endpoint(payload: AuthPayload, db: Session = Depends(get_db)):
    user_entry = (
        db.query(AuthorizedUser)
        .filter(AuthorizedUser.user_id == payload.user_id)
        .first()
    )

    if not user_entry:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if user_entry.username != payload.username:
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = generate_jwt(payload.user_id)
    ephemeral_key = generate_ephemeral_key()

    r.setex(f"ephemeral:{token}", settings.JWT_EXPIRATION, ephemeral_key)

    return {
        "session_token": token,
    }
