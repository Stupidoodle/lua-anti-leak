from pydantic import BaseModel


class AuthPayload(BaseModel):
    user_id: int
    username: str
