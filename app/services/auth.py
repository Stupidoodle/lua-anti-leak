import time
import jwt
from fastapi import HTTPException

from app.core.config import get_settings

settings = get_settings()


def generate_jwt(user_id: int) -> str:
    now = int(time.time())
    payload = {
        "uid": user_id,
        "iat": now,
        "exp": now + settings.JWT_EXPIRATION_TIME,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token


def verify_jwt(token: str) -> dict:
    try:
        decoded = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return decoded
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
