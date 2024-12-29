import redis
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.secrets import get_vault_client, TokenManager
from app.database import SessionLocal
from app.models.auth import AuthorizedUser
from app.schemas.auth import AuthPayload
from app.services.auth import generate_jwt
from app.utils.crypto_utils import generate_ephemeral_key

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


@router.post("/auth")
def auth_endpoint(
    payload: AuthPayload,
    db: Session = Depends(get_db),
    token_manager: TokenManager = Depends(get_token_manager),
):
    user_entry = (
        db.query(AuthorizedUser)
        .filter(AuthorizedUser.user_id == payload.user_id)
        .first()
    )

    if not user_entry:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if user_entry.username != payload.username:
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = token_manager.create_token(payload.user_id)
    ephemeral_key = generate_ephemeral_key()

    r.setex(f"ephemeral:{token}", settings.JWT_EXPIRATION, ephemeral_key)

    return {
        "session_token": token,
    }
